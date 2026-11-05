#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

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
                    if os.path.getsize(self.lock_path) == 0:
                        os.write(self._fd, b"\x00")
                    os.lseek(self._fd, 0, os.SEEK_SET)
                    msvcrt.locking(self._fd, msvcrt.LK_NBLCK, 1)
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
                    try:
                        os.lseek(self._fd, 0, os.SEEK_SET)
                        msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
                    except OSError as err:
                        _ = err
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
