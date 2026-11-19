#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for Gate 4: AI Documentation & Artifact Linter."""

import tempfile
import unittest
from unittest.mock import patch, MagicMock

from tools.core.gates.gate_04_ai_docs import Gate04AIDocs, gate_4_ai_docs_lint


class TestGate04AIDocs(unittest.TestCase):
    def test_gate_04_wrapper(self):
        gate = Gate04AIDocs()
        self.assertEqual(gate.gate_id, 4)
        self.assertEqual(gate.name, "Gate 4: AI Documentation Linter")
        self.assertEqual(gate.key, "gate_4_ai_docs_lint")

    @patch("tools.core.gates.gate_04_ai_docs.resolve_tool_path")
    @patch("subprocess.run")
    def test_gate_04_subprocess_pass(self, mock_run, mock_resolve):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_resolve.return_value = "/mock/tools/lint_ai_docs.py"
            with patch("os.path.exists", return_value=True):
                mock_proc = MagicMock()
                mock_proc.returncode = 0
                mock_proc.stdout = "OK"
                mock_proc.stderr = ""
                mock_run.return_value = mock_proc

                self.assertTrue(gate_4_ai_docs_lint(tmpdir, mode="TARGET"))
                gate = Gate04AIDocs()
                res = gate.execute(tmpdir, mode="TARGET")
                self.assertTrue(res.passed)

    @patch("tools.core.gates.gate_04_ai_docs.resolve_tool_path")
    @patch("subprocess.run")
    def test_gate_04_subprocess_fail(self, mock_run, mock_resolve):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_resolve.return_value = "/mock/tools/lint_ai_docs.py"
            with patch("os.path.exists", return_value=True):
                mock_proc = MagicMock()
                mock_proc.returncode = 1
                mock_proc.stdout = "Drift detected"
                mock_proc.stderr = "Error"
                mock_run.return_value = mock_proc

                self.assertFalse(gate_4_ai_docs_lint(tmpdir, mode="TARGET"))


if __name__ == "__main__":
    unittest.main()
