#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Unit tests for tools/reversible_sandbox.py
"""

import os
import tempfile
import unittest

from tools.reversible_sandbox import (
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


if __name__ == "__main__":
    unittest.main()
