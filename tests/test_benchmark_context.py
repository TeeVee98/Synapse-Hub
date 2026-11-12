#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_benchmark_context.py — Unit Tests for Swarm Context Reduction Benchmark
"""

import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

import benchmark_swarm_context


class TestBenchmarkContext(unittest.TestCase):
    """Verifies that the empirical token reduction benchmark executes and proves >= 40% reduction."""

    def test_estimate_tokens(self):
        text = "Hello world! This is a test."
        tokens = benchmark_swarm_context.estimate_tokens(text)
        self.assertGreater(tokens, 0)
        self.assertEqual(benchmark_swarm_context.estimate_tokens(""), 0)

    def test_run_benchmark_exceeds_threshold(self):
        bench = benchmark_swarm_context.run_benchmark()
        self.assertIn("net_savings_pct", bench)
        self.assertGreaterEqual(bench["net_savings_pct"], 40.0, "Empirical token reduction must be >= 40%")
        self.assertTrue(bench["verified_claim_ge_40_pct"])
        self.assertEqual(len(bench["scenarios"]), 4)

        for s in bench["scenarios"]:
            self.assertGreater(s["baseline_tokens"], s["synapse_tokens"])
            self.assertGreater(s["savings_pct"], 50.0)

    def test_format_markdown_report(self):
        bench = benchmark_swarm_context.run_benchmark()
        md = benchmark_swarm_context.format_markdown_report(bench)
        self.assertIn("# Empirical Context & Token Reduction Benchmark", md)
        self.assertIn("SCN-01-AUTH", md)
        self.assertIn("✅ PASS", md)

    def test_load_workload_scenarios_from_external_dataset(self):
        """Verifies that scenarios can be loaded from the external standardized fixture dataset."""
        dataset_dir = os.path.join(REPO_ROOT, "tests", "fixtures", "benchmarks", "context_tokens")
        scenarios = benchmark_swarm_context.load_workload_scenarios(dataset_dir)
        self.assertGreaterEqual(len(scenarios), 4)
        for scn in scenarios:
            self.assertIn("id", scn)
            self.assertIn("name", scn)
            self.assertIn("baseline_payload", scn)
            self.assertIn("synapse_payload", scn)
            self.assertGreater(len(scn["baseline_payload"]), 0)
            self.assertGreater(len(scn["synapse_payload"]), 0)


if __name__ == "__main__":
    unittest.main()
