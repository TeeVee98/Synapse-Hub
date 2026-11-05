#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

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
        locked_write(self.test_file, "atomic content test", timeout=2.0, atomic=True)
        content = locked_read(self.test_file, timeout=2.0)
        self.assertEqual(content, "atomic content test")

    def test_locked_json_write_and_read(self):
        data = {"name": "Synapse", "count": 42, "items": ["a", "b"]}
        locked_json_write(self.test_json, data, timeout=2.0)
        read_back = locked_json_read(self.test_json, timeout=2.0)
        self.assertEqual(read_back, data)

    def test_contention_timeout(self):
        # Hold an exclusive lock in one context, attempt another exclusive lock with short timeout
        lock1 = FileLock(self.test_file, timeout=2.0, shared=False)
        lock1.acquire()
        try:
            lock2 = FileLock(self.test_file, timeout=0.2, shared=False, poll_interval=0.02)
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


if __name__ == "__main__":
    unittest.main()
