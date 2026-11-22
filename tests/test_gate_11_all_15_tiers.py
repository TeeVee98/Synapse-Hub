#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_gate_11_all_15_tiers.py — Verification of Gate 11 across all 15 Tiers
--------------------------------------------------------------------------------
Validates that Gate 11 verifies all 15 token reduction and intelligence tiers:
  - Tiers 1-10: Baseline Token Reduction Architecture
  - Tier 11: Repo Speculative Decoding & Prompt Lookup
  - Tier 12: Kolmogorov-Minimal Symbolic Micro-DSL
  - Tier 13: Logprob-Triggered Prefix Branching
  - Tier 14: Boundary Counterfactual Few-Shot Distiller
  - Tier 15: Neuro-Symbolic Constraint Offloading
"""

import os
import unittest
from tools.core.gates.base import LAST_GATE_METRICS
from tools.core.gates.gate_11_token_reduction import Gate11TokenReduction, gate_11_token_reduction


class TestGate11All15Tiers(unittest.TestCase):
    """Test Suite verifying Gate 11 checks all 15 Tiers."""

    def setUp(self) -> None:
        self.repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_gate_11_verifies_all_15_tiers(self) -> None:
        passed = gate_11_token_reduction(self.repo_root)
        self.assertTrue(passed, "Gate 11 must pass for all 15 tiers in Hub repo")

        metrics = LAST_GATE_METRICS.get("gate_11_token_reduction", {})
        self.assertEqual(metrics.get("status"), "PASS")
        self.assertEqual(metrics.get("checks_passed"), 15)
        self.assertEqual(metrics.get("total_checks"), 15)
        self.assertEqual(len(metrics.get("details", [])), 15)

        # Check that Tiers 11 to 15 are explicitly reported in details
        details_text = " ".join(metrics.get("details", []))
        self.assertIn("Tier 11: Repo Speculative Decoding", details_text)
        self.assertIn("Tier 12: Kolmogorov-Minimal Symbolic Micro-DSL", details_text)
        self.assertIn("Tier 13: Logprob-Triggered Prefix Branching", details_text)
        self.assertIn("Tier 14: Boundary Counterfactual Few-Shot Distiller", details_text)
        self.assertIn("Tier 15: Neuro-Symbolic Constraint Offloading", details_text)

    def test_gate_11_class_interface(self) -> None:
        gate_obj = Gate11TokenReduction()
        self.assertEqual(gate_obj.gate_id, 11)
        res = gate_obj.run(self.repo_root)
        self.assertTrue(res)


if __name__ == "__main__":
    unittest.main()
