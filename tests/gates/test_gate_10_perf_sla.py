#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for Gate 10: Performance & SLA Sentinel."""

import json
import os
import shutil
import tempfile
import time
import unittest

from tools.core.gates.gate_10_perf_sla import Gate10PerfSLA, gate_10_performance_sla


class TestGate10PerfSLA(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="synapse_test_gate10_")
        self.perf_dir = os.path.join(self.temp_dir, "Reports", "perf")
        os.makedirs(self.perf_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_gate_10_class_wrapper(self):
        gate = Gate10PerfSLA()
        self.assertEqual(gate.gate_id, 10)
        self.assertEqual(gate.name, "Gate 10: Performance & SLA Sentinel")
        self.assertEqual(gate.key, "gate_10_performance_sla")

    def test_gate_10_compliant_k6_summary(self):
        k6_path = os.path.join(self.perf_dir, "k6_summary.json")
        data = {
            "metrics": {
                "http_req_duration": {"values": {"p(95)": 150.0, "p(99)": 280.0}},
                "http_req_failed": {"values": {"rate": 0.005}}
            },
            "metadata": {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        }
        with open(k6_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        gate = Gate10PerfSLA()
        res = gate.execute(self.temp_dir, mode="TARGET")
        self.assertTrue(res.passed)

    def test_gate_10_breached_k6_summary(self):
        k6_path = os.path.join(self.perf_dir, "k6_summary.json")
        # SLA breach: P95 = 1200ms (> 500ms default)
        data = {
            "metrics": {
                "http_req_duration": {"values": {"p(95)": 1200.0, "p(99)": 2400.0}},
                "http_req_failed": {"values": {"rate": 0.05}}
            },
            "metadata": {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        }
        with open(k6_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        self.assertFalse(gate_10_performance_sla(self.temp_dir, mode="TARGET"))


if __name__ == "__main__":
    unittest.main()
