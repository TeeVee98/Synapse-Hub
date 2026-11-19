#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for Gate 7: Static Defect & AST Integrity Sentinel."""

import os
import shutil
import tempfile
import unittest

from tools.core.gates.gate_07_infer_linter import Gate07InferLinter
from tools.core.gates.base import check_python_ast_integrity


class TestGate07InferLinter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="synapse_test_gate7_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_clean_python_ast_passes(self):
        py_file = os.path.join(self.temp_dir, "valid.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write("def calculate(a: int, b: int) -> int:\n    return a + b\n")

        viols = check_python_ast_integrity(self.temp_dir)
        self.assertEqual(len(viols), 0)

    def test_syntax_error_fails_ast_check(self):
        py_file = os.path.join(self.temp_dir, "broken_syntax.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write("def invalid_syntax(\n")

        viols = check_python_ast_integrity(self.temp_dir)
        self.assertTrue(len(viols) > 0)
        self.assertIn("SyntaxError", viols[0][2])

    def test_undefined_name_fails_ast_check(self):
        py_file = os.path.join(self.temp_dir, "undefined_name.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write("def bad_func():\n    return undefined_variable_12345 + 1\n")

        viols = check_python_ast_integrity(self.temp_dir)
        self.assertTrue(len(viols) > 0)
        self.assertIn("Undefined name", viols[0][2])

    def test_gate_07_class_wrapper(self):
        gate = Gate07InferLinter()
        self.assertEqual(gate.gate_id, 7)
        self.assertEqual(gate.name, "Gate 7: Static Defect Sentinel")
        self.assertEqual(gate.key, "gate_7_infer_linter")


if __name__ == "__main__":
    unittest.main()
