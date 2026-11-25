#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for Gate 7: Static Defect & AST Integrity Sentinel."""

import os
import shutil
import tempfile
import unittest

from unittest.mock import MagicMock, patch

from tools.core.gates.gate_07_infer_linter import Gate07InferLinter, gate_7_infer_linter, resolve_impact_test_files
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

    def test_resolve_impact_maps_examples_templates_and_smoke_fallback(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        ex_tests = resolve_impact_test_files(repo_root, ["examples/playwright-python-suite/tests/test_login.py"])
        self.assertIn("tests/test_e2e_three_stacks.py", ex_tests)
        self.assertIn("tests/test_infer_linter.py", ex_tests)

        tpl_tests = resolve_impact_test_files(repo_root, ["templates/PROJECT_AI_GUIDE_TEMPLATE.md"])
        self.assertIn("tests/test_scaffold.py", tpl_tests)
        self.assertIn("tests/test_lint_ai_docs.py", tpl_tests)

        bin_tests = resolve_impact_test_files(repo_root, ["bin/agent-qa.js"])
        self.assertIn("tests/test_cli_contracts.py", bin_tests)
        self.assertIn("tests/test_docker_integration.py", bin_tests)

        # Unmapped non-empty diff must still fall back to core smoke tests
        unmapped_tests = resolve_impact_test_files(repo_root, ["README.md"])
        self.assertTrue(len(unmapped_tests) >= 1)
        self.assertEqual(resolve_impact_test_files(repo_root, ["README.md"], include_smoke_fallback=False), [])
        self.assertEqual(resolve_impact_test_files(repo_root, []), [])

    def test_gate_07_impact_smoke_env_executes_when_diff_empty(self):
        from tools.core.gates.base import LAST_GATE_METRICS
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        mock_git = MagicMock(returncode=0, stdout="", stderr="")
        mock_pytest = MagicMock(returncode=0, stdout="3 passed in 0.50s\n", stderr="")

        with patch.dict(os.environ, {"SYNAPSE_VERIFY_TIER": "impact", "SYNAPSE_IMPACT_SMOKE": "1"}, clear=False), \
             patch("tools.core.gates.gate_07_infer_linter.subprocess.run") as mock_run:
            def _side_effect(cmd, *args, **kwargs):
                if cmd and cmd[0] == "git":
                    return mock_git
                return mock_pytest

            mock_run.side_effect = _side_effect
            orig_pytest_env = os.environ.pop("PYTEST_CURRENT_TEST", None)
            orig_g7_env = os.environ.pop("SYNAPSE_GATE7_TESTING", None)
            try:
                ok = gate_7_infer_linter(repo_root, mode="HUB", fast=False)
            finally:
                if orig_pytest_env is not None:
                    os.environ["PYTEST_CURRENT_TEST"] = orig_pytest_env
                if orig_g7_env is not None:
                    os.environ["SYNAPSE_GATE7_TESTING"] = orig_g7_env

            self.assertTrue(ok)
            pytest_calls = [c[0][0] for c in mock_run.call_args_list if c[0][0] and "-m" in c[0][0] and "pytest" in c[0][0]]
            self.assertTrue(len(pytest_calls) >= 1, "SYNAPSE_IMPACT_SMOKE=1 must invoke minimal smoke pytest even when git diff is empty")

        # When diff ALREADY matches a test, SYNAPSE_IMPACT_SMOKE=1 must preserve the matched test rather than replacing it
        mock_git_changed = MagicMock(returncode=0, stdout="tests/test_infer_linter.py\n", stderr="")
        with patch.dict(os.environ, {"SYNAPSE_VERIFY_TIER": "impact", "SYNAPSE_IMPACT_SMOKE": "1"}, clear=False), \
             patch("tools.core.gates.gate_07_infer_linter.subprocess.run") as mock_run:
            mock_run.side_effect = lambda cmd, *a, **kw: mock_git_changed if (cmd and cmd[0] == "git") else mock_pytest
            orig_pytest_env = os.environ.pop("PYTEST_CURRENT_TEST", None)
            orig_g7_env = os.environ.pop("SYNAPSE_GATE7_TESTING", None)
            try:
                ok = gate_7_infer_linter(repo_root, mode="HUB", fast=False)
            finally:
                if orig_pytest_env is not None:
                    os.environ["PYTEST_CURRENT_TEST"] = orig_pytest_env
                if orig_g7_env is not None:
                    os.environ["SYNAPSE_GATE7_TESTING"] = orig_g7_env
            self.assertTrue(ok)
            pytest_calls = [c[0][0] for c in mock_run.call_args_list if c[0][0] and "-m" in c[0][0] and "pytest" in c[0][0]]
            self.assertTrue(any("tests/test_infer_linter.py" in call for call in pytest_calls))
            self.assertFalse(any("tests/test_dod_receipt.py" in call for call in pytest_calls))

        # Clean tree without SYNAPSE_IMPACT_SMOKE prints skip banner and reports passed=0 honestly
        with patch.dict(os.environ, {"SYNAPSE_VERIFY_TIER": "impact", "SYNAPSE_IMPACT_SMOKE": "0"}, clear=False), \
             patch("tools.core.gates.gate_07_infer_linter.safe_print") as mock_print, \
             patch("tools.core.gates.gate_07_infer_linter.subprocess.run") as mock_run:
            mock_run.side_effect = lambda cmd, *a, **kw: mock_git if (cmd and cmd[0] == "git") else mock_pytest
            orig_pytest_env = os.environ.pop("PYTEST_CURRENT_TEST", None)
            orig_g7_env = os.environ.pop("SYNAPSE_GATE7_TESTING", None)
            try:
                ok = gate_7_infer_linter(repo_root, mode="HUB", fast=False)
            finally:
                if orig_pytest_env is not None:
                    os.environ["PYTEST_CURRENT_TEST"] = orig_pytest_env
                if orig_g7_env is not None:
                    os.environ["SYNAPSE_GATE7_TESTING"] = orig_g7_env
            self.assertTrue(ok)
            self.assertEqual(LAST_GATE_METRICS["gate_7"]["passed"], 0)
            printed = "\n".join(str(c[0][0]) for c in mock_print.call_args_list if c[0])
            self.assertIn("Zero test files affected in git diff", printed)

        # Multiple impacted test files (>= 4) leverage xdist (-n) when installed and >= 300s timeout
        many_git = MagicMock(
            returncode=0,
            stdout="\n".join([
                "tests/test_infer_linter.py",
                "tests/test_cli_contracts.py",
                "tests/test_scaffold.py",
                "tests/test_skills_schema.py",
            ]),
            stderr="",
        )
        with patch.dict(os.environ, {"SYNAPSE_VERIFY_TIER": "impact"}, clear=False), \
             patch("tools.core.gates.gate_07_infer_linter.importlib.util.find_spec", return_value=object()), \
             patch("tools.core.gates.gate_07_infer_linter.subprocess.run") as mock_run:
            mock_run.side_effect = lambda cmd, *a, **kw: many_git if (cmd and cmd[0] == "git") else mock_pytest
            orig_pytest_env = os.environ.pop("PYTEST_CURRENT_TEST", None)
            orig_g7_env = os.environ.pop("SYNAPSE_GATE7_TESTING", None)
            try:
                ok = gate_7_infer_linter(repo_root, mode="HUB", fast=False)
            finally:
                if orig_pytest_env is not None:
                    os.environ["PYTEST_CURRENT_TEST"] = orig_pytest_env
                if orig_g7_env is not None:
                    os.environ["SYNAPSE_GATE7_TESTING"] = orig_g7_env
            self.assertTrue(ok)
            pytest_calls = [c for c in mock_run.call_args_list if c[0][0] and "pytest" in c[0][0]]
            self.assertTrue(len(pytest_calls) >= 1)
            self.assertIn("-n", pytest_calls[0][0][0])
            self.assertGreaterEqual(pytest_calls[0][1].get("timeout", 0), 300.0)


if __name__ == "__main__":
    unittest.main()
