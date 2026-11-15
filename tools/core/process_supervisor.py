#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Reusable Process Group Supervisor & Zombie Process Reaper (tools.core.process_supervisor)
------------------------------------------------------------------------------------------
Guarantees hermetic lifecycle supervision of external test runners and headless browsers.
Prevents orphaned zombie processes (chromedriver, chromium, node, java) from exhausting
system file descriptors and RAM on CI runners and local developer workstations.

Key Mechanisms:
  1. Process Group Isolation:
     - On POSIX: `start_new_session=True` assigns a distinct process group ID (`pgid = proc.pid`).
     - On Windows: `CREATE_NEW_PROCESS_GROUP` isolates the process hierarchy.
  2. Two-Stage Cascading Reap:
     - Stage 1: Graceful termination via SIGTERM / SIGBREAK with bounded grace period.
     - Stage 2: Forceful termination via SIGKILL / taskkill /F to eradicate descendants.
  3. Optional psutil Integration:
     - If psutil is present in environment, scans and kills recursive child trees directly.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SupervisedResult:
    """Outcome of a supervised subprocess execution."""
    cmd: List[str]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    duration_sec: float = 0.0

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out


def kill_process_tree(pid: int, timeout: float = 2.0) -> bool:
    """
    Terminates a process and all of its descendant child/grandchild processes.
    Cross-platform: uses process groups on POSIX, taskkill on Windows, or psutil if available.
    """
    if pid <= 0:
        return False

    # 1. Try psutil if installed
    try:
        import psutil  # type: ignore
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            for child in children:
                try:
                    child.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            parent.terminate()

            gone, alive = psutil.wait_procs(children + [parent], timeout=timeout)
            for p in alive:
                try:
                    p.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return True
    except ImportError as err:
        import logging
        logging.getLogger("process_supervisor").debug("psutil import error: %s", err)

    # 2. Platform-native fallback
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=5.0
            )
            return True
        except Exception:
            return False
    else:
        # POSIX: use process group if PID is group leader, combined with recursive descendant tracking
        descendant_pids: List[int] = []
        to_check = [pid]
        while to_check:
            curr = to_check.pop(0)
            try:
                out = subprocess.run(
                    ["pgrep", "-P", str(curr)],
                    capture_output=True,
                    text=True,
                    timeout=1.0,
                    check=False
                )
                if out.returncode == 0:
                    for line in out.stdout.splitlines():
                        c_str = line.strip()
                        if c_str.isdigit():
                            cp = int(c_str)
                            if cp not in descendant_pids and cp != pid:
                                descendant_pids.append(cp)
                                to_check.append(cp)
            except Exception as err:
                import logging
                logging.getLogger("process_supervisor").debug("Process tree inspection error: %s", err)
                continue

        try:
            caller_pgrp = os.getpgrp() if hasattr(os, "getpgrp") else None
            candidate_pgid = os.getpgid(pid)
            # Only signal process group if target process is its own group leader
            # AND it is not the supervisor/caller's own process group
            if candidate_pgid == pid and (caller_pgrp is None or candidate_pgid != caller_pgrp):
                pgid = candidate_pgid
            else:
                pgid = None
        except OSError as err:
            import logging
            logging.getLogger("process_supervisor").debug("getpgid failed: %s", err)
            pgid = None

        sig_term = getattr(signal, "SIGTERM", 15)
        sig_kill = getattr(signal, "SIGKILL", 9)

        # Stage 1: Graceful SIGTERM to process group and individual descendants
        if pgid is not None:
            try:
                os.killpg(pgid, sig_term)
            except OSError as err:
                import logging
                logging.getLogger("process_supervisor").debug("SIGTERM to pgid %s failed: %s", pgid, err)
        for p in [pid] + descendant_pids:
            try:
                os.kill(p, sig_term)
            except OSError:
                continue

        # Bounded polling wait before force kill
        start = time.time()
        while time.time() - start < timeout:
            alive = False
            if pgid is not None:
                try:
                    os.killpg(pgid, 0)
                    alive = True
                except OSError as err:
                    import logging
                    logging.getLogger("process_supervisor").debug("killpg 0 probe failed: %s", err)
            for p in [pid] + descendant_pids:
                try:
                    os.kill(p, 0)
                    alive = True
                except OSError as err:
                    import logging
                    logging.getLogger("process_supervisor").debug("killpg 0 probe failed: %s", err)
            if not alive:
                return True
            time.sleep(0.05)  # synapse-ignore: HARD_DELAY_ANTI_PATTERN

        # Stage 2: Forceful SIGKILL to eradicate all remaining processes
        for p in descendant_pids + [pid]:
            try:
                os.kill(p, sig_kill)
            except OSError:
                continue
        if pgid is not None:
            try:
                os.killpg(pgid, sig_kill)
            except OSError as err:
                import logging
                logging.getLogger("process_supervisor").debug("SIGKILL to pgid %s failed: %s", pgid, err)
        try:
            subprocess.run(["pkill", "-KILL", "-P", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2.0)
        except Exception as err:
            import logging
            logging.getLogger("process_supervisor").debug("pkill subprocess failed: %s", err)
        return True


def reap_orphan_processes(
    target_names: Optional[Tuple[str, ...]] = None,
    allow_system_wide: bool = False,
    tracked_pids: Optional[List[int]] = None
) -> int:
    """
    Safeguard reaper for orphaned runner and browser processes.
    Defaults to known test drivers: chromedriver, chromium, node, java.

    Safety Invariants:
    1. Only reaps genuine orphaned processes whose parent process has died (on Windows:
       not psutil.pid_exists(ppid); on POSIX: ppid == 1 or not psutil.pid_exists(ppid)),
       or processes explicitly matching tracked_pids.
    2. Blind OS-wide 'taskkill /IM' and 'pkill -f' are eliminated by default to prevent
       killing the developer's active desktop browsers. System-wide fallback requires
       explicit allow_system_wide=True opt-in.
    """
    targets = target_names or ("chromedriver", "geckodriver", "chromium", "playwright")
    reaped = 0

    try:
        import psutil  # type: ignore
        current_pid = os.getpid()
        for proc in psutil.process_iter(attrs=["pid", "name", "ppid"]):
            try:
                pname = (proc.info.get("name") or "").lower()
                pid = proc.info.get("pid")
                ppid = proc.info.get("ppid")
                if not pid or pid == current_pid:
                    continue

                if not any(t in pname for t in targets):
                    continue

                is_tracked = bool(tracked_pids and pid in tracked_pids)
                is_orphan = False
                if ppid is not None:
                    if sys.platform == "win32":
                        is_orphan = not psutil.pid_exists(ppid)
                    else:
                        is_orphan = (ppid == 1) or (not psutil.pid_exists(ppid))

                if is_tracked or is_orphan or allow_system_wide:
                    proc.kill()
                    reaped += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return reaped
    except ImportError:
        _psutil_available = False

    # Native CLI fallbacks ONLY if explicitly requested via allow_system_wide
    if not allow_system_wide:
        return 0

    if sys.platform == "win32":
        for target in targets:
            im_name = target if target.endswith(".exe") else f"{target}.exe"
            try:
                res = subprocess.run(
                    ["taskkill", "/F", "/IM", im_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5.0
                )
                if res.returncode == 0:
                    reaped += 1
            except Exception:
                continue
    else:
        for target in targets:
            try:
                res = subprocess.run(
                    ["pkill", "-f", target],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5.0
                )
                if res.returncode == 0:
                    reaped += 1
            except Exception:
                continue
    return reaped


class ProcessSupervisor:
    """
    Supervises external process lifecycles with guaranteed group cleanup.
    """

    def __init__(self, default_timeout: float = 60.0):
        self.default_timeout = default_timeout
        self._active_pids: List[int] = []

    def run(
        self,
        cmd: List[str],
        timeout: Optional[float] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        capture_output: bool = True,
        text: bool = True,
        input_data: Optional[str] = None,
    ) -> SupervisedResult:
        """
        Executes cmd in an isolated session/process-group, ensuring all descendants
        are reaped upon timeout or unexpected failure.
        """
        t_limit = timeout if timeout is not None else self.default_timeout
        if t_limit is not None and t_limit <= 0:
            t_limit = 0.001
        start_time = time.perf_counter()

        def _to_str(val: Any) -> str:
            if isinstance(val, bytes):
                return val.decode("utf-8", errors="replace")
            return val or ""

        # Process group configuration
        popen_kwargs: Dict[str, Any] = {
            "cwd": cwd,
            "env": env,
        }

        if capture_output:
            popen_kwargs["stdout"] = subprocess.PIPE
            popen_kwargs["stderr"] = subprocess.PIPE
        if input_data is not None:
            popen_kwargs["stdin"] = subprocess.PIPE

        if sys.platform == "win32":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True

        proc = subprocess.Popen(cmd, text=text, **popen_kwargs)
        self._active_pids.append(proc.pid)

        stdout_data, stderr_data = "", ""
        timed_out = False

        try:
            stdout_raw, stderr_raw = proc.communicate(input=input_data, timeout=t_limit)
            stdout_data = _to_str(stdout_raw)
            stderr_data = _to_str(stderr_raw)
            returncode = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            kill_process_tree(proc.pid)
            try:
                stdout_raw, stderr_raw = proc.communicate(timeout=1.0)
                stdout_data = _to_str(stdout_raw)
                stderr_data = _to_str(stderr_raw)
            except Exception as comm_err:
                import logging
                logging.getLogger("process_supervisor").debug("Process communicate error: %s", comm_err)
            returncode = 124
        except Exception as exc:
            kill_process_tree(proc.pid)
            returncode = 1
            stderr_data = str(exc)
        finally:
            if proc.pid in self._active_pids:
                self._active_pids.remove(proc.pid)

        elapsed = time.perf_counter() - start_time
        return SupervisedResult(
            cmd=cmd,
            returncode=returncode,
            stdout=stdout_data,
            stderr=stderr_data,
            timed_out=timed_out,
            duration_sec=elapsed
        )

    def cleanup_all(self):
        """Emergency cleanup of any active process groups tracked by this supervisor."""
        for pid in list(self._active_pids):
            kill_process_tree(pid)
        self._active_pids.clear()

    def __enter__(self) -> ProcessSupervisor:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_all()


def run_supervised(
    cmd: List[str],
    timeout: float = 60.0,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    capture_output: bool = True,
    text: bool = True,
    input_data: Optional[str] = None,
) -> SupervisedResult:
    """
    Convenience function to execute a command under a governed ProcessSupervisor session.
    Guarantees strict execution timeout, process group isolation, and zombie process cleanup (Boost B4).
    """
    with ProcessSupervisor(default_timeout=timeout) as supervisor:
        return supervisor.run(
            cmd=cmd,
            timeout=timeout,
            cwd=cwd,
            env=env,
            capture_output=capture_output,
            text=text,
            input_data=input_data,
        )
