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


    def test_empirical_reference_projects_benchmark(self):
        """Verifies Track 2 empirical measurements on repository reference projects."""
        bench = benchmark_swarm_context.run_benchmark()
        self.assertIn("empirical_track", bench)
        emp = bench["empirical_track"]
        self.assertGreaterEqual(emp["projects_count"], 4)
        for p in emp["results"]:
            self.assertIn("project_name", p)
            self.assertIn("detected_stacks", p)
            self.assertGreater(p["catalog_saved_tokens"], 0)
            self.assertGreater(p["hydrated_saved_tokens"], 0)

    def test_benchmark_report_drift_sentinel(self):
        """Quality Gate: Ensures benchmarks/CONTEXT_TOKEN_BENCHMARK.md is synchronized with live run_benchmark()."""
        md_path = os.path.join(REPO_ROOT, "benchmarks", "CONTEXT_TOKEN_BENCHMARK.md")
        self.assertTrue(os.path.exists(md_path), "CONTEXT_TOKEN_BENCHMARK.md must exist on disk")

        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        bench = benchmark_swarm_context.run_benchmark()
        expected_reduction = f"{bench['net_savings_pct']}% reduction"
        self.assertIn(expected_reduction, content, f"Benchmark report drift detected! Expected '{expected_reduction}' in report.")
        self.assertIn("cl100k_base", content)


if __name__ == "__main__":
    unittest.main()
