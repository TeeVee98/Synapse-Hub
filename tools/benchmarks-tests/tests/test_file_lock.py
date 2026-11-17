#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

import os
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, PROJECT_ROOT)

from tools.core.file_lock import (
    FileLock,
    FileLockTimeoutError,
    locked_read,
    locked_write,
    locked_json_read,
    locked_json_write,
    _win32_lock,
    _win32_unlock,
    LOCKFILE_FAIL_IMMEDIATELY,
    LOCKFILE_EXCLUSIVE_LOCK,
)


class TestFileLock(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = os.path.join(self.temp_dir.name, "shared_state.txt")
        self.test_json = os.path.join(self.temp_dir.name, "shared_state.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_basic_acquire_and_release(self):
        lock = FileLock(self.test_file, timeout=2.0)
        lock.acquire()
        self.assertTrue(os.path.exists(self.test_file + ".lock"))
        lock.release()

    def test_context_manager(self):
        with FileLock(self.test_file, timeout=2.0):
            with open(self.test_file, "w", encoding="utf-8") as f:
                f.write("hello locked file")

        with open(self.test_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, "hello locked file")

    def test_locked_write_and_read(self):
        import unittest.mock as mock
        with mock.patch("os.replace", wraps=os.replace) as mock_replace:
            locked_write(self.test_file, "atomic content test", timeout=2.0, atomic=True)
            mock_replace.assert_called()
        content = locked_read(self.test_file, timeout=2.0)
        self.assertEqual(content, "atomic content test")

        with mock.patch("os.replace", wraps=os.replace) as mock_replace_non_atomic:
            locked_write(self.test_file, "non-atomic update", timeout=2.0, atomic=False)
            mock_replace_non_atomic.assert_not_called()
        self.assertEqual(locked_read(self.test_file, timeout=2.0), "non-atomic update")

    def test_locked_json_write_and_read(self):
        data = {"name": "Synapse", "count": 42, "items": ["a", "b"]}
        locked_json_write(self.test_json, data, timeout=2.0)
        read_back = locked_json_read(self.test_json, timeout=2.0)
        self.assertEqual(read_back, data)

    def test_contention_timeout(self):
        # Hold an exclusive lock in one context, attempt another exclusive lock with short timeout
        lock1 = FileLock(self.test_file, timeout=2.0, shared=False)
        self.assertFalse(lock1.shared)
        lock1.acquire()
        try:
            lock2 = FileLock(self.test_file, timeout=0.2, shared=False, poll_interval=0.02)
            self.assertFalse(lock2.shared)
            with self.assertRaises(FileLockTimeoutError):
                lock2.acquire()
        finally:
            lock1.release()

    def test_multiprocess_concurrency(self):
        import subprocess
        # Spawn multiple parallel Python processes concurrently writing to test_file
        worker_code = """
import sys
from tools.core.file_lock import locked_write, locked_read
w_id, f_path = sys.argv[1], sys.argv[2]
for step in range(8):
    locked_write(f_path, f"worker_{w_id}_step_{step}", timeout=5.0)
    data = locked_read(f_path, timeout=5.0)
    assert data.startswith("worker_"), f"Corrupt data: {data}"
"""
        procs = [
            subprocess.Popen([sys.executable, "-c", worker_code, str(i), self.test_file])
            for i in range(3)
        ]
        retcodes = [p.wait(timeout=10.0) for p in procs]
        self.assertEqual(retcodes, [0, 0, 0])
        final_content = locked_read(self.test_file, timeout=2.0)
        self.assertTrue(final_content.startswith("worker_"))

    def test_win32_lock_ctypes_shared_and_exclusive(self):
        """Boost B1: Test Win32 LockFileEx and UnlockFileEx via ctypes with genuine shared/exclusive flags."""
        import unittest.mock as mock

        mock_kernel32 = mock.MagicMock()
        mock_kernel32.LockFileEx.return_value = 1
        mock_kernel32.UnlockFileEx.return_value = 1

        mock_windll = mock.MagicMock()
        mock_windll.kernel32 = mock_kernel32

        mock_msvcrt = mock.MagicMock()
        mock_msvcrt.get_osfhandle.return_value = 9999

        class MockCUlong:
            def __init__(self, val=0):
                self.value = val

        mock_ctypes = mock.MagicMock()
        mock_ctypes.windll = mock_windll
        mock_ctypes.c_ulong = MockCUlong
        mock_ctypes.c_void_p = int
        mock_ctypes.sizeof.return_value = 32
        mock_ctypes.byref.side_effect = lambda x: x

        with mock.patch("tools.core.file_lock._HAS_CTYPES", True), \
             mock.patch("tools.core.file_lock.ctypes", mock_ctypes), \
             mock.patch.dict(sys.modules, {"msvcrt": mock_msvcrt}):

            # 1. Shared lock -> LOCKFILE_FAIL_IMMEDIATELY (0x01)
            res_sh = _win32_lock(100, shared=True)
            self.assertTrue(res_sh)
            mock_kernel32.LockFileEx.assert_called_once()
            args_sh = mock_kernel32.LockFileEx.call_args[0]
            # args: handle, flags, reserved, low, high, overlapped
            self.assertEqual(args_sh[1].value, LOCKFILE_FAIL_IMMEDIATELY)

            # 2. Exclusive lock -> LOCKFILE_FAIL_IMMEDIATELY | LOCKFILE_EXCLUSIVE_LOCK (0x03)
            mock_kernel32.LockFileEx.reset_mock()
            res_ex = _win32_lock(100, shared=False)
            self.assertTrue(res_ex)
            mock_kernel32.LockFileEx.assert_called_once()
            args_ex = mock_kernel32.LockFileEx.call_args[0]
            self.assertEqual(args_ex[1].value, LOCKFILE_FAIL_IMMEDIATELY | LOCKFILE_EXCLUSIVE_LOCK)

            # 3. Unlock -> UnlockFileEx
            res_un = _win32_unlock(100)
            self.assertTrue(res_un)
            mock_kernel32.UnlockFileEx.assert_called_once()

    def test_win32_lock_failure_raises_oserror(self):
        """Boost B1: Win32 LockFileEx failure properly raises OSError across all contention error codes."""
        import unittest.mock as mock

        mock_kernel32 = mock.MagicMock()
        mock_kernel32.LockFileEx.return_value = 0  # Failed
        mock_windll = mock.MagicMock()
        mock_windll.kernel32 = mock_kernel32

        mock_msvcrt = mock.MagicMock()
        mock_msvcrt.get_osfhandle.return_value = 9999

        class MockCUlong:
            def __init__(self, val=0):
                self.value = val

        mock_ctypes = mock.MagicMock()
        mock_ctypes.windll = mock_windll
        mock_ctypes.c_ulong = MockCUlong
        mock_ctypes.c_void_p = int
        mock_ctypes.sizeof.return_value = 32
        mock_ctypes.byref.side_effect = lambda x: x

        for err_code in [33, 167, 32]:  # ERROR_LOCK_VIOLATION, ERROR_LOCK_FAILED, ERROR_SHARING_VIOLATION
            mock_ctypes.GetLastError.return_value = err_code
            with mock.patch("tools.core.file_lock._HAS_CTYPES", True), \
                 mock.patch("tools.core.file_lock.ctypes", mock_ctypes), \
                 mock.patch.dict(sys.modules, {"msvcrt": mock_msvcrt}):

                with self.assertRaises(OSError) as ctx:
                    _win32_lock(100, shared=False)
                self.assertIn(f"LockFileEx failed with error code {err_code}", str(ctx.exception))
                self.assertEqual(ctx.exception.errno, err_code)
                args = mock_kernel32.LockFileEx.call_args[0]
                self.assertEqual(args[1].value, LOCKFILE_FAIL_IMMEDIATELY | LOCKFILE_EXCLUSIVE_LOCK)

    def test_win32_lock_fallback_to_msvcrt(self):
        """Boost B1: Graceful fallback to msvcrt.locking when ctypes kernel32 is unavailable."""
        import unittest.mock as mock

        mock_msvcrt = mock.MagicMock()
        mock_msvcrt.LK_NBLCK = 1
        mock_msvcrt.LK_UNLCK = 2

        with mock.patch("tools.core.file_lock._HAS_CTYPES", False), \
             mock.patch.dict(sys.modules, {"msvcrt": mock_msvcrt}), \
             mock.patch("os.lseek"):

            # Lock fallback
            res = _win32_lock(100, shared=False)
            self.assertTrue(res)
            mock_msvcrt.locking.assert_called_once_with(100, mock_msvcrt.LK_NBLCK, 1)

            # Unlock fallback
            mock_msvcrt.locking.reset_mock()
            res_un = _win32_unlock(100)
            self.assertTrue(res_un)
            mock_msvcrt.locking.assert_called_once_with(100, mock_msvcrt.LK_UNLCK, 1)

    def test_stale_lock_auto_reclamation(self):
        """Verifies that an abandoned lockfile with a dead PID is automatically reclaimed."""
        target_file = os.path.join(self.temp_dir.name, "stale_target.txt")
        lock_file = target_file + ".lock"
        # Write dead PID 99999999 into lockfile
        with open(lock_file, "w", encoding="utf-8") as f:
            f.write("99999999:1234567890\n")

        # Acquire with a short timeout; it should detect dead PID and reclaim lock
        with FileLock(target_file, timeout=0.2, poll_interval=0.02) as lock:
            self.assertIsNotNone(lock._fd)


if __name__ == "__main__":
    unittest.main()
