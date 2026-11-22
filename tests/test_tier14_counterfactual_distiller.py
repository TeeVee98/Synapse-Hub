#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_tier14_counterfactual_distiller.py — Test Suite for Tier 14 Counterfactual Distiller
-----------------------------------------------------------------------------------------------
Enforces 4-Scenario Testing: Positive, Negative, Boundary, and CLI invocation.
"""

import json
import subprocess
import sys
import unittest
from tools.context.counterfactual_distiller import (
    CURATED_PAIRS,
    CounterfactualDistiller,
    run_benchmark,
)


class TestTier14CounterfactualDistiller(unittest.TestCase):
    """Test Suite for Tier 14 Boundary Counterfactual Few-Shot Distiller."""

    def setUp(self) -> None:
        self.distiller = CounterfactualDistiller()

    # 1. Positive Scenario
    def test_positive_distillation(self) -> None:
        pairs = self.distiller.distill("race condition with mutex lock in threading", domain_hint="concurrency", exact_k=2)
        self.assertEqual(len(pairs), 2)
        self.assertEqual(pairs[0].domain, "concurrency")
        self.assertIn("lock", pairs[0].keywords)

        # Formatted prompt verification
        prompt = CounterfactualDistiller.format_distilled_prompt(pairs)
        self.assertIn("BOUNDARY COUNTERFACTUAL PAIRS", prompt)
        self.assertIn("Near-Miss (FLAW)", prompt)
        self.assertIn("Surgical Fix", prompt)

        # Token savings verification
        savings = CounterfactualDistiller.calculate_token_savings(pairs)
        self.assertGreaterEqual(savings["token_reduction_pct"], 70.0)

    def test_security_injection_domain(self) -> None:
        pairs = self.distiller.distill("prevent SQL injection in database query", domain_hint="security_injection", exact_k=2)
        self.assertEqual(len(pairs), 2)
        self.assertEqual(pairs[0].domain, "security_injection")
        self.assertEqual(pairs[0].pair_id, "SEC_001")

    # 2. Negative Scenario
    def test_negative_unknown_domain(self) -> None:
        # Unknown domain falls back cleanly to best token matching or default pairs
        pairs = self.distiller.distill("some unknown domain with no direct keywords", domain_hint="non_existent_domain", exact_k=2)
        self.assertEqual(len(pairs), 2)
        self.assertTrue(all(p in CURATED_PAIRS for p in pairs))

    # 3. Boundary Scenario
    def test_boundary_empty_and_zero(self) -> None:
        # Empty string
        pairs = self.distiller.distill("", exact_k=2)
        self.assertEqual(len(pairs), 2)

        # Requesting 1 or more than available
        pair_single = self.distiller.distill("concurrency", exact_k=1)
        self.assertEqual(len(pair_single), 1)

        empty_prompt = CounterfactualDistiller.format_distilled_prompt([])
        self.assertIn("BOUNDARY COUNTERFACTUAL PAIRS", empty_prompt)

    # 4. CLI & Gate Scenario
    def test_cli_and_gate_execution(self) -> None:
        bench = run_benchmark()
        self.assertEqual(bench["status"], "PASS")

        # Subprocess CLI run
        proc = subprocess.run(
            [sys.executable, "tools/context/counterfactual_distiller.py", "--benchmark", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(proc.stdout)
        self.assertEqual(data["status"], "PASS")

        # Subprocess Gate run
        gate_proc = subprocess.run(
            [sys.executable, "tools/context/counterfactual_distiller.py", "--gate"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("[PASS]", gate_proc.stdout)


if __name__ == "__main__":
    unittest.main()
