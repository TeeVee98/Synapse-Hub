#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for Gate 8: Assertion Sensitivity & Syntactic Mutation Sentinel."""

import tempfile
import unittest
from unittest.mock import patch, MagicMock

from tools.core.gates.gate_08_mutation import Gate08Mutation, gate_8_micro_mutator
from tools.core.gates.base import LAST_GATE_METRICS


class TestGate08Mutation(unittest.TestCase):
    def test_gate_08_class_wrapper(self):
        gate = Gate08Mutation()
        self.assertEqual(gate.gate_id, 8)
        self.assertEqual(gate.name, "Gate 8: Assertion Sensitivity & Syntactic Mutation Sentinel")
        self.assertEqual(gate.key, "gate_8_micro_mutator")

    def test_gate_8_hub_mode_no_modified_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.stdout = "README.md\ndocs/test.md\n"
                mock_run.return_value.returncode = 0

                res = gate_8_micro_mutator(tmpdir, mode="HUB", changed_only=True)
                self.assertTrue(res)
                self.assertEqual(LAST_GATE_METRICS.get("gate_8", {}).get("mode"), "DYNAMIC_SCOPED")

    @patch("tools.core.gates.gate_08_mutation.resolve_tool_path")
    @patch("subprocess.run")
    def test_gate_8_target_mode_execution(self, mock_run, mock_resolve):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_resolve.return_value = "/mock/tools/micro_mutator.py"
            with patch("os.path.exists", return_value=True), patch("os.path.isdir", return_value=True):
                mock_proc = MagicMock()
                mock_proc.returncode = 0
                mock_proc.stdout = '{"mutation_score": 85.0, "killed": 17, "total_mutants": 20}'
                mock_proc.stderr = ""
                mock_run.return_value = mock_proc

                gate = Gate08Mutation()
                res = gate.execute(tmpdir, mode="TARGET")
                self.assertTrue(res.passed)


if __name__ == "__main__":
    unittest.main()
