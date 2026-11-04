#!/usr/bin/env python3
"""
Unit tests for tools/telemetry_correlator.py
"""

import os
import tempfile
import unittest

from tools.telemetry_correlator import (
    calculate_pearson_correlation,
    parse_jtl_time_series,
    parse_server_metrics,
    run_correlation_analysis,
    format_rca_markdown,
)


class TestTelemetryCorrelator(unittest.TestCase):
    def test_pearson_correlation_identical_series(self):
        x = [10.0, 20.0, 30.0, 40.0, 50.0]
        y = [10.0, 20.0, 30.0, 40.0, 50.0]
        r = calculate_pearson_correlation(x, y)
        self.assertAlmostEqual(r, 1.0, places=4)

    def test_pearson_correlation_inverse_series(self):
        x = [10.0, 20.0, 30.0, 40.0, 50.0]
        y = [50.0, 40.0, 30.0, 20.0, 10.0]
        r = calculate_pearson_correlation(x, y)
        self.assertAlmostEqual(r, -1.0, places=4)

    def test_pearson_correlation_insufficient_points(self):
        self.assertEqual(calculate_pearson_correlation([1.0], [2.0]), 0.0)
        self.assertEqual(calculate_pearson_correlation([], []), 0.0)

    def test_pearson_correlation_zero_variance(self):
        x = [5.0, 5.0, 5.0]
        y = [1.0, 2.0, 3.0]
        self.assertEqual(calculate_pearson_correlation(x, y), 0.0)

    def test_parse_jtl_time_series(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jtl", delete=False, encoding="utf-8") as f:
            f.write("timeStamp,elapsed,label,responseCode,responseMessage,threadName,dataType,success\n")
            f.write("1700000000000,120,Login,200,OK,Thread-1,text,true\n")
            f.write("1700000002000,150,Login,200,OK,Thread-1,text,true\n")
            f.write("1700000006000,320,Checkout,200,OK,Thread-1,text,true\n")
            jtl_path = f.name

        try:
            buckets = parse_jtl_time_series(jtl_path, bucket_sec=5)
            self.assertIn(1700000000, buckets)
            self.assertEqual(len(buckets[1700000000]), 2)
            self.assertIn(1700000005, buckets)
            self.assertEqual(buckets[1700000005], [320.0])
        finally:
            if os.path.exists(jtl_path):
                os.remove(jtl_path)

    def test_parse_server_metrics(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("timestamp,cpu_pct,memory_pct,db_pool_pct,disk_iops\n")
            f.write("1700000000,45.2,60.5,30.0,120\n")
            f.write("1700000005,88.4,62.1,85.0,450\n")
            metrics_path = f.name

        try:
            series = parse_server_metrics(metrics_path, bucket_sec=5)
            self.assertIn("cpu_pct", series)
            self.assertIn(1700000000, series["cpu_pct"])
            self.assertEqual(series["cpu_pct"][1700000000], 45.2)
            self.assertEqual(series["disk_iops"][1700000005], 450.0)
        finally:
            if os.path.exists(metrics_path):
                os.remove(metrics_path)

    def test_correlate_telemetry_and_rca(self):
        client_data = {
            1700000000: [100.0, 110.0],
            1700000005: [500.0, 600.0],
            1700000010: [900.0, 950.0],
        }
        server_series = {
            "cpu_pct": {1700000000: 30.0, 1700000005: 85.0, 1700000010: 95.0},
            "memory_pct": {1700000000: 40.0, 1700000005: 42.0, 1700000010: 44.0},
            "db_pool_pct": {1700000000: 20.0, 1700000005: 25.0, 1700000010: 28.0},
            "disk_iops": {1700000000: 50.0, 1700000005: 60.0, 1700000010: 70.0},
        }

        result = run_correlation_analysis(client_data, server_series)
        self.assertIn("correlations", result)
        self.assertIn("cpu_correlation", result["correlations"])
        self.assertGreater(result["correlations"]["cpu_correlation"], 0.9)
        self.assertIn("root_causes", result)

        md = format_rca_markdown(result)
        self.assertIn("Performance Telemetry Correlation", md)
        self.assertIn("CPU Utilization", md)


if __name__ == "__main__":
    unittest.main()
