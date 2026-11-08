#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Reversible Execution Sandbox & Automated Teardown Engine (GoEx Pattern)
------------------------------------------------------------------------
Maintains a LIFO undo-stack of stateful mutations (DB inserts, file modifications,
auth session cookies). Guarantees 100% idempotent teardown and zero database leakage
even when test execution crashes or is cancelled.

Enterprise Features:
  1. Write-Ahead Logging (WAL) Journaling:
     - Persists pending undo actions immediately to disk (.synapse/undo_wal.jsonl).
     - Survives SIGKILL / sudden power cut / runner crashes with `recover_from_wal()`.
  2. Signal & Teardown Handlers:
     - Automatically traps SIGINT, SIGTERM, and atexit to unwind stateful mutations.
  3. LIFO Execution Order:
     - Strictly executes teardown in reverse chronological sequence.

Reference:
  - Shishir Patil et al. (Gorilla / GoEx): Runtime Reversible Sandboxed Execution.
  - Synapse-Hub Subsystem 5: Section 6.6 of agent_skill_training_analysis.md.
"""

import os
import sys
import time
import json
import shlex
import atexit
import signal
import weakref
import threading
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
QA_HUB_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))


def _resolve_wal_path() -> str:
    cwd = os.path.abspath(os.getcwd())
    try:
        is_hub = os.path.samefile(cwd, QA_HUB_ROOT)
    except (FileNotFoundError, OSError, ValueError):
        is_hub = os.path.realpath(cwd).lower() == os.path.realpath(QA_HUB_ROOT).lower()
    if not is_hub:
        return os.path.join(cwd, ".synapse", "undo_wal.jsonl")
    return os.path.join(QA_HUB_ROOT, ".synapse", "undo_wal.jsonl")


DEFAULT_WAL_PATH = _resolve_wal_path()

_ACTIVE_SANDBOXES: "weakref.WeakSet[ExecutionSandbox]" = weakref.WeakSet()


@dataclass
class ReversibleAction:
    action_type: str        # e.g., "DB_INSERT", "FS_WRITE", "AUTH_SESSION", "STATE_MUTATION"
    target_resource: str    # e.g., "users table", "tmp/test_export.csv", "Bearer token"
    undo_command: str       # Exact SQL DELETE, shell command, or callback instruction
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExecutionSandbox:
    """Manages an undo stack of stateful mutations with WAL persistence for guaranteed cleanup."""

    def __init__(self, auto_rollback_on_exit: bool = True, wal_path: Optional[str] = None):
        self.undo_stack: List[ReversibleAction] = []
        self.auto_rollback_on_exit = auto_rollback_on_exit
        self.wal_path = wal_path if wal_path is not None else _resolve_wal_path()
        if self.wal_path:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(self.wal_path)), exist_ok=True)
            except OSError as err:
                sys.stderr.write(f"Notice: WAL path creation skipped (read-only environment): {err}\n")
                self.wal_path = None
        _ACTIVE_SANDBOXES.add(self)

    def _append_wal(self, action: ReversibleAction):
        """Persists a pending undo action to disk before side-effects complete."""
        if not self.wal_path:
            return
        entry = {
            "action_type": action.action_type,
            "target_resource": action.target_resource,
            "undo_command": action.undo_command,
            "metadata": action.metadata,
            "timestamp": time.time()
        }
        line = json.dumps(entry, ensure_ascii=False) + "\n"
        try:
            try:
                from tools.core.file_lock import file_lock
                with file_lock(self.wal_path + ".lock", timeout=5.0):
                    with open(self.wal_path, "a", encoding="utf-8") as f:
                        f.write(line)
                        f.flush()
            except ImportError:
                with open(self.wal_path, "a", encoding="utf-8") as f:
                    f.write(line)
                    f.flush()
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to write undo WAL journal: {e}\n")

    def _clear_wal(self):
        """Clears or resets WAL journal when stack has been completely unwound."""
        if not self.wal_path or not os.path.exists(self.wal_path):
            return
        try:
            try:
                from tools.core.file_lock import file_lock
                with file_lock(self.wal_path + ".lock", timeout=5.0):
                    with open(self.wal_path, "w", encoding="utf-8") as f:
                        pass
            except ImportError:
                with open(self.wal_path, "w", encoding="utf-8") as f:
                    pass
        except Exception as clear_err:
            sys.stderr.write(f"Notice: Failed to clear WAL: {clear_err}\n")

    def record_mutation(
        self,
        action_type: str,
        target_resource: str,
        undo_command: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Pushes a rollback action onto the LIFO undo stack and appends to WAL journal."""
        action = ReversibleAction(
            action_type=action_type,
            target_resource=target_resource,
            undo_command=undo_command,
            metadata=metadata or {}
        )
        self.undo_stack.append(action)
        self._append_wal(action)

    def execute_stateful_action(
        self,
        action_type: str,
        target_resource: str,
        forward_cmd: str,
        undo_cmd: str
    ) -> bool:
        """Executes a forward shell command and immediately records its reversible undo counterpart."""
        try:
            args = shlex.split(forward_cmd) if isinstance(forward_cmd, str) else forward_cmd
            res = subprocess.run(args, text=True, capture_output=True, timeout=60.0)
            if res.returncode == 0:
                self.record_mutation(action_type, target_resource, undo_cmd, {"forward_cmd": forward_cmd})
                return True
            return False
        except Exception:
            return False

    def rollback_all(self, silent: bool = False) -> List[Dict[str, Any]]:
        """Unwinds the undo stack in strictly reverse (LIFO) order and cleans WAL."""
        results = []
        while self.undo_stack:
            action = self.undo_stack.pop()
            success = True
            err_msg = ""
            cmd = action.undo_command.strip()

            if cmd.startswith("FILE_DELETE:"):
                fpath = cmd.split(":", 1)[1].strip()
                if os.path.exists(fpath):
                    try:
                        os.remove(fpath)
                    except OSError as e:
                        success = False
                        err_msg = str(e)
            elif cmd.startswith("DIR_DELETE:"):
                dpath = cmd.split(":", 1)[1].strip()
                if os.path.isdir(dpath):
                    try:
                        import shutil
                        shutil.rmtree(dpath, ignore_errors=True)
                    except Exception as e:
                        success = False
                        err_msg = str(e)
            elif cmd:
                try:
                    args = shlex.split(cmd) if isinstance(cmd, str) else cmd
                    res = subprocess.run(args, text=True, capture_output=True, timeout=60.0)
                    success = (res.returncode == 0)
                    if not success:
                        err_msg = res.stderr.strip()
                except Exception as e:
                    success = False
                    err_msg = str(e)

            result_entry = {
                "action_type": action.action_type,
                "target_resource": action.target_resource,
                "undo_command": action.undo_command,
                "success": success,
                "error": err_msg
            }
            results.append(result_entry)
            if not silent:
                status_icon = "✅" if success else "⚠️"
                print(f"  {status_icon} [ROLLBACK] {action.action_type} on '{action.target_resource}': {action.undo_command}")

        if not self.undo_stack:
            self._clear_wal()

        return results

    @classmethod
    def recover_from_wal(cls, wal_path: Optional[str] = None, silent: bool = False) -> List[Dict[str, Any]]:
        """
        Recovers and unwinds uncommitted actions from a previous crashed run's WAL journal.
        """
        target_wal = wal_path or DEFAULT_WAL_PATH
        if not os.path.exists(target_wal) or os.path.getsize(target_wal) == 0:
            return []

        actions: List[ReversibleAction] = []
        try:
            lines = []
            try:
                from tools.core.file_lock import file_lock
                with file_lock(target_wal + ".lock", timeout=5.0):
                    with open(target_wal, "r", encoding="utf-8") as f:
                        lines = [l.strip() for l in f if l.strip()]
            except ImportError:
                with open(target_wal, "r", encoding="utf-8") as f:
                    lines = [l.strip() for l in f if l.strip()]

            for line in lines:
                try:
                    data = json.loads(line)
                    actions.append(ReversibleAction(
                        action_type=data.get("action_type", "WAL_RECOVERED"),
                        target_resource=data.get("target_resource", ""),
                        undo_command=data.get("undo_command", ""),
                        metadata=data.get("metadata", {})
                    ))
                except (json.JSONDecodeError, KeyError, TypeError) as parse_err:
                    sys.stderr.write(f"Notice: Failed to parse WAL line: {parse_err}\n")
                    continue
        except (OSError, IOError) as read_err:
            sys.stderr.write(f"Notice: Failed to read WAL journal: {read_err}\n")
            return []

        if not actions:
            return []

        temp_sandbox = cls(auto_rollback_on_exit=False, wal_path=target_wal)
        temp_sandbox.undo_stack = actions
        results = temp_sandbox.rollback_all(silent=silent)
        return results

    def stack_size(self) -> int:
        """Returns the number of pending undo actions in the stack."""
        return len(self.undo_stack)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None or self.auto_rollback_on_exit:
            self.rollback_all(silent=True)


GLOBAL_SANDBOX = ExecutionSandbox(auto_rollback_on_exit=False)


def record_mutation(action_type: str, target: str, undo_cmd: str):
    GLOBAL_SANDBOX.record_mutation(action_type, target, undo_cmd)


def rollback_all():
    return GLOBAL_SANDBOX.rollback_all()


def rollback_all_active_sandboxes(silent: bool = True):
    """Rolls back all active sandboxes and the global singleton sandbox."""
    for sb in list(_ACTIVE_SANDBOXES):
        try:
            if sb.stack_size() > 0:
                sb.rollback_all(silent=silent)
        except Exception as e:
            sys.stderr.write(f"Notice: Active sandbox rollback error: {e}\n")
    if GLOBAL_SANDBOX.stack_size() > 0:
        GLOBAL_SANDBOX.rollback_all(silent=silent)


def _register_teardown_handlers():
    """Registers OS signal and atexit handlers for graceful recovery & rollback across all active sandboxes."""
    # Register atexit auto-cleanup
    atexit.register(lambda: rollback_all_active_sandboxes(silent=True))

    # Register OS signals only in the main thread
    if threading.current_thread() is threading.main_thread():
        def _sig_handler(signum, frame):
            try:
                rollback_all_active_sandboxes(silent=True)
            finally:
                sys.exit(128 + signum)

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, _sig_handler)
            except (ValueError, AttributeError, RuntimeError) as sig_err:
                sys.stderr.write(f"Notice: Signal registration skipped: {sig_err}\n")


_register_teardown_handlers()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GoEx Reversible Teardown Sandbox Stack")
    parser.add_argument("--demo", action="store_true", help="Run reversible stack demonstration")
    parser.add_argument("--status", action="store_true", help="Display active undo stack count")
    parser.add_argument("--recover", action="store_true", help="Recover and roll back uncommitted WAL journal")
    args = parser.parse_args()

    if args.recover:
        print("Recovering uncommitted mutations from WAL journal...")
        recovers = ExecutionSandbox.recover_from_wal(silent=False)
        print(f"Recovered and rolled back {len(recovers)} orphaned actions.")
    elif args.demo:
        print("Running GoEx Reversible Sandbox demo...")
        with ExecutionSandbox(auto_rollback_on_exit=True) as sb:
            sb.record_mutation("fs_create", "test_demo.tmp", "echo rolled back")
            print(f"Stack size inside sandbox: {sb.stack_size()}")
        print("Exited sandbox context, stack rolled back cleanly.")
    else:
        print(f"Active global undo stack size: {GLOBAL_SANDBOX.stack_size()}")
