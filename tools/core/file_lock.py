#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Cross-Platform Advisory File Locking (tools.core.file_lock)
-----------------------------------------------------------
Eliminates race condition truncations and concurrent read/write corruptions
under multi-agent swarms (actor-qa-swarm, parallel subagents).

Key Mechanisms:
  1. POSIX: Uses stdlib `fcntl.flock` with shared (LOCK_SH) and exclusive (LOCK_EX) modes.
  2. Windows: Uses stdlib `msvcrt.locking` with non-blocking polling fallback.
  3. Non-blocking polling timeout: Prevents indefinite deadlocks if another process stalls.
  4. Atomic safe write: Staged writes to .tmp with fsync and atomic rename (os.replace).
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Optional

# POSIX vs Windows native locking imports
if sys.platform != "win32":
    import fcntl
else:
    import msvcrt  # type: ignore

# Win32 Native Locking Constants (Boost B1)
LOCKFILE_FAIL_IMMEDIATELY = 0x00000001
LOCKFILE_EXCLUSIVE_LOCK = 0x00000002

try:
    import ctypes
    from ctypes import wintypes
    _HAS_CTYPES = True
except ImportError:
    ctypes = None  # type: ignore
    wintypes = None  # type: ignore
    _HAS_CTYPES = False

if _HAS_CTYPES:
    class _OVERLAPPED(ctypes.Structure):
        _fields_ = [
            ("Internal", getattr(wintypes, "ULONG_PTR", ctypes.c_size_t)),
            ("InternalHigh", getattr(wintypes, "ULONG_PTR", ctypes.c_size_t)),
            ("Offset", getattr(wintypes, "DWORD", ctypes.c_ulong)),
            ("OffsetHigh", getattr(wintypes, "DWORD", ctypes.c_ulong)),
            ("hEvent", getattr(wintypes, "HANDLE", ctypes.c_void_p)),
        ]
else:
    _OVERLAPPED = None  # type: ignore


def _win32_lock(fd: int, shared: bool = False) -> bool:
    """
    Acquires an advisory file lock on Windows using native Win32 LockFileEx via ctypes.
    Provides genuine shared (LOCKFILE_FAIL_IMMEDIATELY) and exclusive
    (LOCKFILE_EXCLUSIVE_LOCK | LOCKFILE_FAIL_IMMEDIATELY) locks with an OVERLAPPED structure.
    Gracefully falls back to msvcrt.locking if ctypes or LockFileEx is unavailable.
    """
    msvcrt_mod = sys.modules.get("msvcrt")
    use_ctypes = _HAS_CTYPES and hasattr(ctypes, "windll") and hasattr(ctypes.windll, "kernel32")
    if use_ctypes:
        try:
            handle = msvcrt_mod.get_osfhandle(fd) if msvcrt_mod and hasattr(msvcrt_mod, "get_osfhandle") else fd
            flags = LOCKFILE_FAIL_IMMEDIATELY
            if not shared:
                flags |= LOCKFILE_EXCLUSIVE_LOCK
            overlapped = _OVERLAPPED()
            res = ctypes.windll.kernel32.LockFileEx(
                ctypes.c_void_p(handle),
                ctypes.c_ulong(flags),
                ctypes.c_ulong(0),
                ctypes.c_ulong(1),
                ctypes.c_ulong(0),
                ctypes.byref(overlapped),
            )
            if not res:
                get_last_error = getattr(ctypes, "GetLastError", lambda: 0)
                err = get_last_error()
                raise OSError(err, f"LockFileEx failed with error code {err}")
            return True
        except (AttributeError, TypeError, ValueError) as exc:
            # Fall through to msvcrt fallback if ctypes kernel32 LockFileEx is missing or incompatible
            _ = exc

    # Graceful fallback to msvcrt.locking (exclusive lock only)
    if msvcrt_mod is not None:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt_mod.locking(fd, msvcrt_mod.LK_NBLCK, 1)
        return True
    raise OSError("Neither Win32 ctypes nor msvcrt is available for file locking.")


def _win32_unlock(fd: int) -> bool:
    """
    Releases an advisory file lock on Windows using native Win32 UnlockFileEx via ctypes.
    Falls back to msvcrt.locking with LK_UNLCK if ctypes is unavailable.
    """
    msvcrt_mod = sys.modules.get("msvcrt")
    use_ctypes = _HAS_CTYPES and hasattr(ctypes, "windll") and hasattr(ctypes.windll, "kernel32")
    if use_ctypes:
        try:
            handle = msvcrt_mod.get_osfhandle(fd) if msvcrt_mod and hasattr(msvcrt_mod, "get_osfhandle") else fd
            overlapped = _OVERLAPPED()
            res = ctypes.windll.kernel32.UnlockFileEx(
                ctypes.c_void_p(handle),
                ctypes.c_ulong(0),
                ctypes.c_ulong(1),
                ctypes.c_ulong(0),
                ctypes.byref(overlapped),
            )
            return bool(res)
        except (AttributeError, TypeError, ValueError) as exc:
            _ = exc

    # Graceful fallback to msvcrt.locking
    if msvcrt_mod is not None:
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt_mod.locking(fd, msvcrt_mod.LK_UNLCK, 1)
            return True
        except OSError:
            return False
    return False


class FileLockTimeoutError(TimeoutError):
    """Raised when acquiring a file lock exceeds the allocated timeout."""
    pass


class FileLock:
    """
    Cross-platform advisory file lock context manager.
    """

    def __init__(
        self,
        target_path: str,
        timeout: float = 10.0,
        shared: bool = False,
        poll_interval: float = 0.05,
    ):
        self.target_path = os.path.abspath(target_path)
        self.lock_path = self.target_path + ".lock"
        self.timeout = timeout
        self.shared = shared
        self.poll_interval = poll_interval
        self._fd: Optional[int] = None

    def acquire(self) -> FileLock:
        """Acquires the advisory lock, polling until timeout."""
        os.makedirs(os.path.dirname(self.lock_path), exist_ok=True)
        start = time.time()
        while True:
            try:
                if self._fd is None:
                    # Open without O_TRUNC to prevent metadata race conditions
                    self._fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o666)
                if sys.platform != "win32":
                    mode = fcntl.LOCK_SH if self.shared else fcntl.LOCK_EX
                    fcntl.flock(self._fd, mode | fcntl.LOCK_NB)
                else:
                    # Ensure at least 1 byte exists to lock on Windows
                    try:
                        if os.fstat(self._fd).st_size == 0:
                            os.write(self._fd, b"\x00")
                    except (OSError, PermissionError) as err:
                        _ = err
                    os.lseek(self._fd, 0, os.SEEK_SET)
                    _win32_lock(self._fd, shared=self.shared)
                return self
            except (BlockingIOError, OSError, PermissionError):
                if self._fd is not None:
                    try:
                        os.close(self._fd)
                    except OSError as err:
                        _ = err
                    self._fd = None
                if time.time() - start >= self.timeout:
                    raise FileLockTimeoutError(
                        f"Timed out after {self.timeout}s waiting for lock on {self.lock_path}"
                    )
                time.sleep(self.poll_interval)

    def release(self):
        """Releases the advisory lock and closes the descriptor."""
        if self._fd is not None:
            try:
                if sys.platform != "win32":
                    fcntl.flock(self._fd, fcntl.LOCK_UN)
                else:
                    _win32_unlock(self._fd)
                os.close(self._fd)
            except OSError as err:
                _ = err
            finally:
                self._fd = None

    def __enter__(self) -> FileLock:
        return self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


def locked_read(file_path: str, timeout: float = 10.0) -> str:
    """Safely reads a file while holding a shared advisory lock."""
    with FileLock(file_path, timeout=timeout, shared=True):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()


def locked_write(file_path: str, content: str, timeout: float = 10.0, atomic: bool = True) -> None:
    """
    Safely writes content to a file while holding an exclusive lock.
    When atomic=True, writes to a temporary file first, then atomically replaces.
    """
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    with FileLock(file_path, timeout=timeout, shared=False):
        if atomic:
            temp_path = f"{file_path}.tmp.{os.getpid()}.{time.time_ns()}"
            try:
                with open(temp_path, "w", encoding="utf-8") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp_path, file_path)
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError as err:
                        _ = err
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)


def locked_json_read(file_path: str, timeout: float = 10.0) -> Any:
    """Reads JSON content while holding a shared lock."""
    text = locked_read(file_path, timeout=timeout)
    return json.loads(text)


def locked_json_write(
    file_path: str, data: Any, indent: int = 2, timeout: float = 10.0, atomic: bool = True
) -> None:
    """Writes formatted JSON content while holding an exclusive lock."""
    content = json.dumps(data, indent=indent, ensure_ascii=False)
    locked_write(file_path, content, timeout=timeout, atomic=atomic)
