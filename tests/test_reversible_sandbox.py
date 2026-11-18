#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Unit tests for tools/reversible_sandbox.py
"""

import os
import shutil
import tempfile
import unittest

from tools.heal.reversible_sandbox import (
    ExecutionSandbox,
    record_mutation,
    rollback_all,
    GLOBAL_SANDBOX,
)


class TestReversibleSandbox(unittest.TestCase):
    def test_record_mutation_and_stack_size(self):
        sandbox = ExecutionSandbox(auto_rollback_on_exit=False)
        self.assertEqual(sandbox.stack_size(), 0)

        sandbox.record_mutation("DB_INSERT", "orders table", "DELETE FROM orders WHERE id=99")
        self.assertEqual(sandbox.stack_size(), 1)

    def test_file_delete_rollback(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write("temporary file content")
            tpath = f.name

        self.assertTrue(os.path.exists(tpath))

        sandbox = ExecutionSandbox(auto_rollback_on_exit=False)
        sandbox.record_mutation("FS_WRITE", tpath, f"FILE_DELETE:{tpath}")
        results = sandbox.rollback_all(silent=True)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["success"])
        self.assertFalse(os.path.exists(tpath))

    def test_dir_delete_rollback(self):
        tdir = tempfile.mkdtemp(prefix="sandbox_test_")
        self.assertTrue(os.path.isdir(tdir))

        sandbox = ExecutionSandbox(auto_rollback_on_exit=False)
        sandbox.record_mutation("FS_MKDIR", tdir, f"DIR_DELETE:{tdir}")
        results = sandbox.rollback_all(silent=True)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["success"])
        self.assertFalse(os.path.exists(tdir))

    def test_context_manager_auto_rollback(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write("data")
            tpath = f.name

        with ExecutionSandbox(auto_rollback_on_exit=True) as sb:
            sb.record_mutation("FS_WRITE", tpath, f"FILE_DELETE:{tpath}")
            self.assertEqual(sb.stack_size(), 1)

        self.assertFalse(os.path.exists(tpath))

    def test_global_helpers(self):
        GLOBAL_SANDBOX.undo_stack.clear()
        record_mutation("AUTH", "cookie", "CLEAR_SESSION")
        self.assertEqual(GLOBAL_SANDBOX.stack_size(), 1)
        res = rollback_all()
        self.assertEqual(len(res), 1)
        self.assertEqual(GLOBAL_SANDBOX.stack_size(), 0)

    def test_file_delete_outside_sandbox_root_rejected(self):
        root_dir = tempfile.mkdtemp(prefix="sb_root_")
        outside_dir = tempfile.mkdtemp(prefix="sb_out_")
        target_file = os.path.join(outside_dir, "outside.txt")
        with open(target_file, "w") as f:
            f.write("sensitive data")

        try:
            sandbox = ExecutionSandbox(auto_rollback_on_exit=False, sandbox_root=root_dir)
            sandbox.record_mutation("FS_WRITE", target_file, f"FILE_DELETE:{target_file}")
            results = sandbox.rollback_all(silent=True)

            self.assertEqual(len(results), 1)
            self.assertFalse(results[0]["success"])
            self.assertIn("containment", results[0]["error"].lower())
            self.assertTrue(os.path.exists(target_file))
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)
            shutil.rmtree(outside_dir, ignore_errors=True)

    def test_dir_delete_outside_sandbox_root_rejected(self):
        root_dir = tempfile.mkdtemp(prefix="sb_root_")
        outside_dir = tempfile.mkdtemp(prefix="sb_out_")
        target_sub = os.path.join(outside_dir, "subdir")
        os.makedirs(target_sub, exist_ok=True)

        try:
            sandbox = ExecutionSandbox(auto_rollback_on_exit=False, sandbox_root=root_dir)
            sandbox.record_mutation("FS_MKDIR", target_sub, f"DIR_DELETE:{target_sub}")
            results = sandbox.rollback_all(silent=True)

            self.assertEqual(len(results), 1)
            self.assertFalse(results[0]["success"])
            self.assertIn("containment", results[0]["error"].lower())
            self.assertTrue(os.path.isdir(target_sub))
        finally:
            shutil.rmtree(root_dir, ignore_errors=True)
            shutil.rmtree(outside_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
