#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tests/test_k6_analyzer.py — Unit tests for k6 performance results analyzer (tools/perf/k6_analyzer.py)
"""

import os
import sys
import json
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, PROJECT_ROOT)

from tools.perf import k6_analyzer


class TestK6Analyzer(unittest.TestCase):
    """Test suite for k6 output parsing and SLA evaluation."""

    def test_parse_k6_summary_json(self):
        sample_summary = {
            "metrics": {
                "http_req_duration": {
                    "avg": 150.25,
                    "min": 20.0,
                    "med": 120.0,
                    "max": 480.0,
                    "p(90)": 210.0,
                    "p(95)": 290.0,
                    "p(99)": 410.0,
                },
                "http_req_failed": {
                    "passes": 3,
                    "fails": 997,
                    "value": 0.003,
                },
                "iterations": {
                    "count": 1000,
                },
            }
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            json.dump(sample_summary, tf)
            tmp_path = tf.name

        try:
            metrics = k6_analyzer.parse_k6_summary(tmp_path)
            self.assertEqual(metrics["total_requests"], 1000)
            self.assertEqual(metrics["error_rate_pct"], 0.3)
            self.assertEqual(metrics["latency_p95"], 290.0)
            self.assertEqual(metrics["latency_p99"], 410.0)
            self.assertEqual(metrics["latency_avg"], 150.25)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_evaluate_sla_pass(self):
        metrics = {
            "total_requests": 500,
            "failed_requests": 1,
            "error_rate_pct": 0.2,
            "latency_p95": 350.0,
            "latency_p99": 650.0,
            "latency_avg": 120.0,
        }
        passed, violations = k6_analyzer.evaluate_sla(
            metrics, sla_p95=500.0, sla_p99=1000.0, max_error_rate=1.0
        )
        self.assertTrue(passed)
        self.assertEqual(len(violations), 0)

    def test_evaluate_sla_fail(self):
        metrics = {
            "total_requests": 500,
            "failed_requests": 25,
            "error_rate_pct": 5.0,
            "latency_p95": 650.0,
            "latency_p99": 1200.0,
            "latency_avg": 220.0,
        }
        passed, violations = k6_analyzer.evaluate_sla(
            metrics, sla_p95=500.0, sla_p99=1000.0, max_error_rate=1.0
        )
        self.assertFalse(passed)
        self.assertEqual(len(violations), 3)

    def test_parse_line_delimited_json_stream(self):
        stream_data = (
            '{"metric": "http_req_duration", "data": {"value": 100.0}}\n'
            '{"metric": "http_req_duration", "data": {"value": 200.0}}\n'
            '{"metric": "http_req_duration", "data": {"value": 300.0}}\n'
            '{"metric": "http_req_failed", "data": {"value": 0}}\n'
            '{"metric": "http_req_failed", "data": {"value": 0}}\n'
            '{"metric": "http_req_failed", "data": {"value": 0}}\n'
        )
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            tf.write(stream_data)
            tmp_path = tf.name

        try:
            metrics = k6_analyzer.parse_k6_summary(tmp_path)
            self.assertEqual(metrics["total_requests"], 3)
            self.assertEqual(metrics["error_rate_pct"], 0.0)
            self.assertEqual(metrics["latency_avg"], 200.0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
