#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for DoD Quality Gates Base Architecture and Models."""

import unittest
from tools.core.gates.base import BaseGate, GateResult
from tools.core.gates import ALL_GATES


class DummyPassingGate(BaseGate):
    gate_id = 99
    name = "Gate 99: Dummy Pass"
    key = "gate_99_dummy_pass"

    def run(self, repo_root: str, mode: str = "AUTO", **kwargs) -> bool:
        return True


class DummyFailingGate(BaseGate):
    gate_id = 98
    name = "Gate 98: Dummy Fail"
    key = "gate_98_dummy_fail"

    def run(self, repo_root: str, mode: str = "AUTO", **kwargs) -> bool:
        return False


class DummyCrashingGate(BaseGate):
    gate_id = 97
    name = "Gate 97: Dummy Crash"
    key = "gate_97_dummy_crash"

    def run(self, repo_root: str, mode: str = "AUTO", **kwargs) -> bool:
        raise RuntimeError("Gate execution exploded intentionally")


class TestGatesArchitecture(unittest.TestCase):
    """Verifies BaseGate abstractions and GateResult contract."""

    def test_gate_result_dataclass(self):
        res = GateResult(gate_id=1, name="Test Gate", passed=True)
        self.assertEqual(res.gate_id, 1)
        self.assertEqual(res.name, "Test Gate")
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "PASS")
        self.assertEqual(res.errors, [])
        self.assertGreaterEqual(res.duration_sec, 0.0)

    def test_base_gate_execute_pass(self):
        gate = DummyPassingGate()
        res = gate.execute("/mock/repo", mode="HUB")
        self.assertIsInstance(res, GateResult)
        self.assertEqual(res.gate_id, 99)
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "PASS")
        self.assertEqual(res.errors, [])

    def test_base_gate_execute_fail(self):
        gate = DummyFailingGate()
        res = gate.execute("/mock/repo", mode="HUB")
        self.assertIsInstance(res, GateResult)
        self.assertEqual(res.gate_id, 98)
        self.assertFalse(res.passed)
        self.assertEqual(res.status, "FAIL")
        self.assertTrue(len(res.errors) > 0)

    def test_base_gate_execute_crash_handled(self):
        gate = DummyCrashingGate()
        res = gate.execute("/mock/repo", mode="HUB")
        self.assertIsInstance(res, GateResult)
        self.assertEqual(res.gate_id, 97)
        self.assertFalse(res.passed)
        self.assertEqual(res.status, "FAIL")
        self.assertIn("Gate execution exploded intentionally", res.errors[0])

    def test_all_gates_registry(self):
        self.assertEqual(len(ALL_GATES), 10)
        gate_ids = [g.gate_id for g in ALL_GATES]
        self.assertEqual(gate_ids, list(range(1, 11)))
        keys = [g.key for g in ALL_GATES]
        self.assertEqual(len(set(keys)), 10)


if __name__ == "__main__":
    unittest.main()
