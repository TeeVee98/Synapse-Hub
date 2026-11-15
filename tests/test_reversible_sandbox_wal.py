#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Unit tests for Write-Ahead Logging (WAL) and crash recovery in tools/reversible_sandbox.py
"""

import os
import json
import shutil
import tempfile
import unittest
from tools.reversible_sandbox import (
    ExecutionSandbox,
)


class TestReversibleSandboxWAL(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="wal_test_")
        self.wal_path = os.path.join(self.temp_dir, "undo_wal.jsonl")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_record_mutation_persists_to_wal(self):
        sb = ExecutionSandbox(auto_rollback_on_exit=False, wal_path=self.wal_path)
        sb.record_mutation("DB_INSERT", "test_table", "DELETE FROM test_table WHERE id=1")
        sb.record_mutation("FS_WRITE", "test_file.txt", "FILE_DELETE:test_file.txt")

        self.assertTrue(os.path.exists(self.wal_path))
        with open(self.wal_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        self.assertEqual(len(lines), 2)
        entry1 = json.loads(lines[0])
        self.assertEqual(entry1["action_type"], "DB_INSERT")
        self.assertEqual(entry1["undo_command"], "DELETE FROM test_table WHERE id=1")

    def test_rollback_all_clears_wal(self):
        sb = ExecutionSandbox(auto_rollback_on_exit=False, wal_path=self.wal_path)
        sb.record_mutation("STATE", "key", "NOOP")
        self.assertEqual(sb.stack_size(), 1)
        self.assertTrue(os.path.getsize(self.wal_path) > 0)

        sb.rollback_all(silent=True)
        self.assertEqual(sb.stack_size(), 0)
        # WAL file should be truncated to 0
        self.assertEqual(os.path.getsize(self.wal_path), 0)

    def test_recover_from_wal_after_crash(self):
        # Simulate a crash where the process died leaving unrolled actions in WAL
        tfile = os.path.join(self.temp_dir, "orphan_file.txt")
        with open(tfile, "w", encoding="utf-8") as f:
            f.write("orphan content")
        self.assertTrue(os.path.exists(tfile))

        # Write WAL entry directly simulating crashed process
        with open(self.wal_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "action_type": "FS_WRITE",
                "target_resource": tfile,
                "undo_command": f"FILE_DELETE:{tfile}",
                "metadata": {}
            }) + "\n")

        # Run recovery
        recovered = ExecutionSandbox.recover_from_wal(wal_path=self.wal_path, silent=True)
        self.assertEqual(len(recovered), 1)
        self.assertTrue(recovered[0]["success"])
        # File must be deleted by rollback
        self.assertFalse(os.path.exists(tfile))
        # WAL must be cleared
        self.assertEqual(os.path.getsize(self.wal_path), 0)

    def test_recover_empty_wal(self):
        res = ExecutionSandbox.recover_from_wal(wal_path=self.wal_path, silent=True)
        self.assertEqual(res, [])

    def test_active_sandboxes_tracked_and_rolled_back(self):
        from tools.reversible_sandbox import rollback_all_active_sandboxes
        tfile = os.path.join(self.temp_dir, "multi_instance.tmp")
        with open(tfile, "w") as f:
            f.write("content")

        sb = ExecutionSandbox(auto_rollback_on_exit=False, wal_path=self.wal_path)
        sb.record_mutation("FS_WRITE", tfile, f"FILE_DELETE:{tfile}")
        self.assertEqual(sb.stack_size(), 1)

        # Trigger rollback across all active sandboxes
        rollback_all_active_sandboxes(silent=True)
        self.assertEqual(sb.stack_size(), 0)
        self.assertFalse(os.path.exists(tfile))


if __name__ == "__main__":
    unittest.main()
