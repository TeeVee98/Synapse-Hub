#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from tools.heap_leak_analyzer import (
    analyze_memory_delta,
    inspect_heap_snapshot,
    parse_metric_value,
)


class TestHeapLeakAnalyzer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="heap_test_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_metric_value(self):
        self.assertEqual(parse_metric_value(1024), 1024.0)
        self.assertEqual(parse_metric_value("1,048,576"), 1048576.0)
        self.assertEqual(parse_metric_value("invalid"), 0.0)
        self.assertEqual(parse_metric_value(None), 0.0)

    def test_analyze_memory_delta_healthy_stable(self):
        t0 = {"JSHeapUsedSize": 10_000_000, "DetachedDOMNodes": 0}
        t1 = {"JSHeapUsedSize": 10_500_000, "DetachedDOMNodes": 0}  # +5% growth
        res = analyze_memory_delta(t0, t1, threshold_pct=15.0)

        self.assertFalse(res["is_leak_detected"])
        self.assertEqual(res["heap_growth_pct"], 5.0)
        self.assertEqual(len(res["violations"]), 0)
        self.assertEqual(len(res["remediation"]), 0)

    def test_analyze_memory_delta_heap_leak(self):
        t0 = {"JSHeapUsedSize": 10_000_000, "DetachedDOMNodes": 0}
        t1 = {"JSHeapUsedSize": 12_500_000, "DetachedDOMNodes": 0}  # +25% growth
        res = analyze_memory_delta(t0, t1, threshold_pct=15.0)

        self.assertTrue(res["is_leak_detected"])
        self.assertEqual(res["heap_growth_pct"], 25.0)
        self.assertGreater(len(res["violations"]), 0)
        self.assertIn("exceeding threshold of 15.0%", res["violations"][0])
        self.assertGreater(len(res["remediation"]), 0)

    def test_analyze_memory_delta_detached_dom_leak(self):
        t0 = {"JSHeapUsedSize": 10_000_000, "DetachedDOMNodes": 0}
        t1 = {"JSHeapUsedSize": 10_200_000, "DetachedDOMNodes": 12}
        res = analyze_memory_delta(t0, t1, threshold_pct=15.0, max_detached_nodes=0)

        self.assertTrue(res["is_leak_detected"])
        self.assertEqual(res["detached_t1"], 12)
        self.assertTrue(any("detached DOM nodes" in v for v in res["violations"]))

    def test_inspect_heap_snapshot_parsing(self):
        snapshot_file = os.path.join(self.temp_dir, "sample.heapsnapshot")
        sample_data = {
            "snapshot": {
                "meta": {
                    "node_fields": ["type", "name", "id", "self_size", "edge_count", "trace_node_id"],
                    "node_types": [["hidden", "array", "string", "object", "code", "closure", "regexp", "number"]],
                }
            },
            "nodes": [3, 1, 101, 32, 2, 0, 3, 2, 102, 64, 4, 0],
        }
        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(sample_data, f)

        info = inspect_heap_snapshot(snapshot_file)
        self.assertEqual(info["total_nodes"], 2)  # 12 elements with stride 6 -> 2 nodes
        self.assertEqual(len(info["node_types"]), 8)

    def test_cli_execution(self):
        script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "heap_leak_analyzer.py")
        t0 = json.dumps({"JSHeapUsedSize": 1000, "DetachedDOMNodes": 0})
        t1 = json.dumps({"JSHeapUsedSize": 1050, "DetachedDOMNodes": 0})

        res = subprocess.run(
            [sys.executable, script, "--t0", t0, "--t1", t1, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertFalse(data["is_leak_detected"])


if __name__ == "__main__":
    unittest.main()
