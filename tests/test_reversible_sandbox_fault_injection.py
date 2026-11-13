#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Fault Injection & Resiliency Test Suite for Reversible Sandbox (Boost B1)
-------------------------------------------------------------------------
Validates Two-Phase Commit WAL journaling under execution failures:
  1. Failed rollback commands (exit code 1) preserve WAL on disk with FAILED status.
  2. Incremental WAL updates record step-by-step unrolling without losing failed actions.
  3. WAL is cleared if and only if 100% of actions succeed without error.
  4. recover_from_wal() reconstructs pending/failed actions after simulated crashes.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, PROJECT_ROOT)

from tools.reversible_sandbox import ExecutionSandbox


class TestReversibleSandboxFaultInjection(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="wal_fault_injection_")
        self.wal_path = os.path.join(self.temp_dir, "undo_wal.jsonl")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_failed_command_preserves_wal_with_failure_status(self):
        """Simulates an undo command exiting with status code 1 and verifies WAL is preserved."""
        fail_script = os.path.join(self.temp_dir, "fail_step.py")
        with open(fail_script, "w", encoding="utf-8") as f:
            f.write("import sys\nsys.stderr.write('DB connection reset')\nsys.exit(1)\n")

        sb = ExecutionSandbox(auto_rollback_on_exit=False, wal_path=self.wal_path)
        fail_cmd = f'"{sys.executable}" "{fail_script}"'
        sb.record_mutation("DB_MUTATION", "orders_table", fail_cmd)

        self.assertEqual(sb.stack_size(), 1)
        self.assertTrue(os.path.exists(self.wal_path))

        results = sb.rollback_all(silent=True)
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]["success"])
        self.assertIn("DB connection reset", results[0]["error"])

        # Crucial: WAL must NOT be wiped when an action fails
        self.assertTrue(os.path.exists(self.wal_path))
        self.assertGreater(os.path.getsize(self.wal_path), 0)

        # Inspect WAL content
        with open(self.wal_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertEqual(entry["status"], "FAILED")
        self.assertIn("DB connection reset", entry["error"])
        self.assertEqual(len(sb.failed_actions), 1)

    def test_multi_action_incremental_wal_updates(self):
        """Validates that successful actions are removed from WAL while failed actions are preserved."""
        test_file1 = os.path.join(self.temp_dir, "f1.txt")
        with open(test_file1, "w") as f:
            f.write("data1")

        test_file2 = os.path.join(self.temp_dir, "f2.txt")
        with open(test_file2, "w") as f:
            f.write("data2")

        fail_script = os.path.join(self.temp_dir, "fail_custom.py")
        with open(fail_script, "w", encoding="utf-8") as f:
            f.write("import sys\nsys.exit(42)\n")

        sb = ExecutionSandbox(auto_rollback_on_exit=False, wal_path=self.wal_path)
        # Action 1: succeeds
        sb.record_mutation("FS_WRITE", test_file1, f"FILE_DELETE:{test_file1}")
        # Action 2: fails
        fail_cmd = f'"{sys.executable}" "{fail_script}"'
        sb.record_mutation("CUSTOM_STEP", "api_session", fail_cmd)
        # Action 3: succeeds
        sb.record_mutation("FS_WRITE", test_file2, f"FILE_DELETE:{test_file2}")

        self.assertEqual(sb.stack_size(), 3)

        results = sb.rollback_all(silent=True)
        self.assertEqual(len(results), 3)

        # Action 3 executed first (LIFO) -> success
        self.assertTrue(results[0]["success"])
        self.assertFalse(os.path.exists(test_file2))

        # Action 2 executed second -> failure
        self.assertFalse(results[1]["success"])

        # Action 1 executed third -> success
        self.assertTrue(results[2]["success"])
        self.assertFalse(os.path.exists(test_file1))

        # WAL on disk must preserve Action 2 with status FAILED
        with open(self.wal_path, "r", encoding="utf-8") as f:
            remaining = [json.loads(l) for l in f if l.strip()]
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["action_type"], "CUSTOM_STEP")
        self.assertEqual(remaining[0]["status"], "FAILED")

    def test_recover_from_wal_preserves_unresolved_entries(self):
        """Verifies that recover_from_wal correctly recovers actions and keeps unresolvable ones."""
        fail_script = os.path.join(self.temp_dir, "fail_recover.py")
        with open(fail_script, "w", encoding="utf-8") as f:
            f.write("import sys\nsys.exit(1)\n")

        # Pre-seed WAL with a failing command
        fail_cmd = f'"{sys.executable}" "{fail_script}"'
        with open(self.wal_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "action_type": "ORPHAN_TASK",
                "target_resource": "job_queue",
                "undo_command": fail_cmd,
                "metadata": {}
            }) + "\n")

        recovered = ExecutionSandbox.recover_from_wal(wal_path=self.wal_path, silent=True)
        self.assertEqual(len(recovered), 1)
        self.assertFalse(recovered[0]["success"])

        # WAL must still exist and record the failure
        self.assertGreater(os.path.getsize(self.wal_path), 0)


if __name__ == "__main__":
    unittest.main()
