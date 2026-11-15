#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

import os
import sys
import unittest
import tempfile
import json
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools")))
from perf.benchmark_perf_runner import run_benchmark
from verify_all import gate_10_performance_sla


class TestPerformanceSLA(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.perf_dir = os.path.join(self.temp_dir, "Reports", "perf")
        os.makedirs(self.perf_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_run_benchmark_generates_valid_artifacts(self):
        res = run_benchmark(iterations=30, output_dir=self.perf_dir)
        self.assertTrue(os.path.exists(res["jtl_file"]))
        self.assertTrue(os.path.exists(res["k6_file"]))
        self.assertLess(res["p95_ms"], 500.0)
        self.assertLessEqual(res["error_rate_pct"], 1.0)
        self.assertTrue(res["sla_pass"])

        # Check k6 JSON schema
        with open(res["k6_file"], "r", encoding="utf-8") as f:
            k6_data = json.load(f)
        self.assertIn("metrics", k6_data)
        self.assertIn("http_req_duration", k6_data["metrics"])
        self.assertIn("http_req_failed", k6_data["metrics"])

    def test_gate_10_evaluation(self):
        run_benchmark(iterations=40, output_dir=self.perf_dir)
        passed = gate_10_performance_sla(self.temp_dir)
        self.assertTrue(passed)


if __name__ == "__main__":
    unittest.main()
