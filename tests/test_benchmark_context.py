#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

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


if __name__ == "__main__":
    unittest.main()
