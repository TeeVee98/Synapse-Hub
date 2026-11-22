#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_tier13_logprob_branching.py — Test Suite for Tier 13 Logprob Prefix Branching
----------------------------------------------------------------------------------------
Enforces 4-Scenario Testing: Positive, Negative, Boundary, and CLI invocation.
"""

import json
import subprocess
import sys
import unittest
from tools.reasoning.logprob_branching_engine import (
    LogprobStreamAnalyzer,
    PrefixBranchingEngine,
    run_benchmark,
)


class TestTier13LogprobBranching(unittest.TestCase):
    """Test Suite for Tier 13 Logprob-Triggered Prefix Branching Engine."""

    def setUp(self) -> None:
        self.engine = PrefixBranchingEngine(threshold=0.60, default_branches=3)

    # 1. Positive Scenario
    def test_positive_bifurcation_and_branching(self) -> None:
        prefix_stream = [
            ("def ", -0.01),
            ("login", -0.02),
            ("(", -0.01),
            ("username", -0.01),
            ("):\n", -0.01),
            ("    if not username:\n", -0.02),
            ("        return False\n", -0.01),
            ("    # critical auth\n", -0.05),
            ("    return ", -0.80),  # Logprob -0.80 -> conf ~0.449 < 0.60
        ]
        branches = [
            [("validate_credentials(username)\n", -0.10)],
            [("check_db_direct(username)\n", -0.30)],
            [("True\n", -0.50)],
        ]
        decision = self.engine.execute_prefix_branching(prefix_stream, branches)
        self.assertEqual(decision.bifurcation_token_index, 8)
        self.assertEqual(decision.bifurcation_token, "    return ")
        self.assertLess(decision.bifurcation_confidence, 0.60)
        self.assertGreater(decision.token_savings_pct, 30.0)
        self.assertEqual(decision.selected_branch_id, 0)
        self.assertIn("validate_credentials", decision.winning_text)

    def test_top_k_distribution_shannon_entropy(self) -> None:
        analyzer = LogprobStreamAnalyzer(uncertainty_threshold=0.60, entropy_threshold=1.0)
        # Token with high distribution spread across 3 options (high entropy)
        token_with_distribution = [
            ("branch", -0.70, {"branch_a": -0.70, "branch_b": -0.80, "branch_c": -1.20})
        ]
        analyzed = analyzer.analyze_stream(token_with_distribution)
        self.assertEqual(len(analyzed), 1)
        self.assertGreater(analyzed[0].entropy, 1.0)
        self.assertTrue(analyzed[0].is_uncertain)

    # 2. Negative Scenario
    def test_negative_all_high_confidence(self) -> None:
        # All tokens are above threshold: zero branching needed
        high_conf_stream = [
            ("print", -0.01),
            ("('hello')", -0.01),
        ]
        decision = self.engine.execute_prefix_branching(high_conf_stream, [])
        self.assertEqual(decision.bifurcation_token_index, -1)
        self.assertEqual(decision.branches_forked, 1)
        self.assertEqual(decision.token_savings_pct, 0.0)
        self.assertEqual(decision.winning_text, "print('hello')")

    # 3. Boundary Scenario
    def test_boundary_empty_and_extreme(self) -> None:
        # Empty stream
        analyzer = LogprobStreamAnalyzer(uncertainty_threshold=0.60)
        self.assertEqual(analyzer.analyze_stream([]), [])
        self.assertIsNone(analyzer.find_first_bifurcation([]))

        # Extreme logprobs (e.g. -99.0 or 0.0)
        extreme_stream = [("a", 0.0), ("b", -99.0)]
        analyzed = analyzer.analyze_stream(extreme_stream)
        self.assertAlmostEqual(analyzed[0].confidence, 1.0, places=3)
        self.assertAlmostEqual(analyzed[1].confidence, 0.0, places=3)
        self.assertTrue(analyzed[1].is_uncertain)

    # 4. CLI & Gate Scenario
    def test_cli_and_gate_execution(self) -> None:
        bench = run_benchmark()
        self.assertEqual(bench["status"], "PASS")

        # Subprocess CLI run
        proc = subprocess.run(
            [sys.executable, "tools/reasoning/logprob_branching_engine.py", "--benchmark", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(proc.stdout)
        self.assertEqual(data["status"], "PASS")

        # Subprocess Gate run
        gate_proc = subprocess.run(
            [sys.executable, "tools/reasoning/logprob_branching_engine.py", "--gate"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("[PASS]", gate_proc.stdout)


if __name__ == "__main__":
    unittest.main()
