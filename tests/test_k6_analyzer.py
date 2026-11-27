#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tests/test_k6_analyzer.py — Unit tests for k6 performance results analyzer (tools/perf/k6_analyzer.py)
"""

import os
import subprocess
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
            self.assertEqual(metrics["dropped_iterations"], 0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_k6_http_reqs_count_arrival_rate_and_recovery_sla_pass(self):
        """Positive: Reads http_reqs.count, arrival rate, dropped_iterations, and recovery probe."""
        payload = {
            "metrics": {
                "http_req_duration": {"values": {"avg": 90.0, "min": 10.0, "med": 80.0, "max": 300.0, "p(90)": 150.0, "p(95)": 210.0, "p(99)": 280.0}},
                "http_req_duration{scenario:recovery_probe}": {"values": {"p(95)": 140.0}},
                "http_req_failed": {"values": {"rate": 0.002, "passes": 2395, "fails": 5}},
                "http_reqs": {"values": {"count": 2400, "rate": 20.5}},
                "iterations": {"values": {"count": 1200, "rate": 20.5}},
                "dropped_iterations": {"values": {"count": 0}},
            }
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump(payload, tf)
            tmp_path = tf.name
        try:
            metrics = k6_analyzer.parse_k6_summary(tmp_path)
            self.assertEqual(metrics["total_requests"], 2400)
            self.assertEqual(metrics["achieved_arrival_rate"], 20.5)
            self.assertEqual(metrics["dropped_iterations"], 0)
            self.assertEqual(metrics["recovery_p95_ms"], 140.0)
            self.assertEqual(metrics["telemetry_kind"], "http_load")
            passed, violations = k6_analyzer.evaluate_sla(
                metrics,
                sla_p95=500.0,
                max_error_rate=1.0,
                min_arrival_rate=20.0,
                max_dropped_iterations=0,
                require_recovery=True,
                max_recovery_p95=500.0,
            )
            self.assertTrue(passed, f"Unexpected violations: {violations}")
            self.assertEqual(violations, [])
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_k6_rejects_underload_dropped_zero_samples_and_missing_recovery(self):
        """Negative: Underload, dropped iterations, no samples, missing/breached recovery fail SLA."""
        base = {
            "total_requests": 1000,
            "failed_requests": 1,
            "error_rate_pct": 0.1,
            "latency_p95": 200.0,
            "latency_p99": 400.0,
            "latency_avg": 90.0,
            "achieved_arrival_rate": 20.0,
            "dropped_iterations": 0,
            "recovery_p95_ms": 150.0,
            "telemetry_kind": "http_load",
        }
        cases = [
            {**base, "achieved_arrival_rate": 12.0},
            {**base, "dropped_iterations": 2},
            {**base, "total_requests": 0},
            {**base, "recovery_p95_ms": None},
            {**base, "recovery_p95_ms": 620.0},
            {**base, "telemetry_kind": "hub_cpu_microbenchmark"},
        ]
        for case in cases:
            passed, violations = k6_analyzer.evaluate_sla(
                case,
                sla_p95=500.0,
                max_error_rate=1.0,
                min_arrival_rate=20.0,
                max_dropped_iterations=0,
                require_recovery=True,
                max_recovery_p95=500.0,
            )
            self.assertFalse(passed, f"Case should fail SLA: {case}")
            self.assertTrue(len(violations) >= 1)

    def test_k6_rejects_synthetic_cpu_microbenchmark_and_checks_script_contract(self):
        """Boundary: Synthetic CPU telemetry is labeled hub_cpu_microbenchmark and k6 script includes cleanup + recovery."""
        self.assertEqual(k6_analyzer.classify_k6_telemetry({"url": "local://benchmark/x"}), "hub_cpu_microbenchmark")
        self.assertEqual(k6_analyzer.classify_k6_telemetry({"label": "LOCAL_CPU_JSON_SERIALIZE"}), "hub_cpu_microbenchmark")
        self.assertEqual(k6_analyzer.classify_k6_telemetry({"url": "https://staging.example.com"}), "http_load")

        # Missing counts and omitted dropped_iterations default cleanly to 0
        empty_counts = k6_analyzer._extract_from_metrics_dict({"metrics": {"http_reqs": {"values": {}}, "dropped_iterations": {}}})
        self.assertEqual(empty_counts["total_requests"], 0)
        self.assertEqual(empty_counts["dropped_iterations"], 0)

        stream_mix = (
            '{"metric": "http_req_duration", "data": {"value": 100.0}}\n'
            '{"metric": "vus", "data": {"value": 5}}\n'
            '{"metric": "http_req_failed", "data": {"value": 1}}\n'
            '{"metric": "http_req_failed", "data": {"value": 0}}\n'
        )
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as sf:
            sf.write(stream_mix)
            sf_path = sf.name
        try:
            sm = k6_analyzer.parse_k6_summary(sf_path)
            self.assertEqual(sm["total_requests"], 2)
            self.assertEqual(sm["failed_requests"], 1)
            self.assertEqual(sm["error_rate_pct"], 50.0)
        finally:
            if os.path.exists(sf_path):
                os.remove(sf_path)
        empty_iter = k6_analyzer._extract_from_metrics_dict({"metrics": {"iterations": {"values": {}}}})
        self.assertEqual(empty_iter["total_requests"], 0)
        ok_default, _ = k6_analyzer.evaluate_sla({"total_requests": 1, "latency_p95": 100.0, "latency_p99": 200.0, "error_rate_pct": 0.0})
        self.assertTrue(ok_default)
        fail_missing_reqs, _ = k6_analyzer.evaluate_sla({"latency_p95": 100.0, "latency_p99": 200.0, "error_rate_pct": 0.0})
        self.assertFalse(fail_missing_reqs)

        synthetic = {
            "telemetry_source": "local://benchmark/json_serde",
            "label": "LOCAL_CPU_JSON_SERIALIZE",
            "metrics": {
                "http_req_duration": {"values": {"p(95)": 1.0, "p(99)": 2.0, "avg": 0.5}},
                "http_req_failed": {"values": {"rate": 0.0}},
                "http_reqs": {"values": {"count": 100}},
            },
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump(synthetic, tf)
            tmp_path = tf.name
        try:
            metrics = k6_analyzer.parse_k6_summary(tmp_path)
            self.assertEqual(metrics["telemetry_kind"], "hub_cpu_microbenchmark")
            passed, violations = k6_analyzer.evaluate_sla(metrics)
            self.assertFalse(passed)
            self.assertTrue(any("synthetic" in v.lower() or "hub" in v.lower() for v in violations))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        k6_js = os.path.join(PROJECT_ROOT, "examples", "perf-backend-suite", "k6", "k6_load_test.js")
        with open(k6_js, "r", encoding="utf-8") as fp:
            js_src = fp.read()
        self.assertIn("recovery_probe", js_src)
        self.assertIn("teardown", js_src)
        self.assertIn("http.del", js_src)

        node_harness = (
            "const fs=require('fs'),vm=require('vm');"
            "let src=fs.readFileSync(process.env.K6_JS,'utf8')"
            ".replace(/^import\\s+.*$/gm,'')"
            ".replace(/^export\\s+const\\s+/gm,'const ')"
            ".replace(/^export\\s+default\\s+function\\s*/gm,'function _default')"
            ".replace(/^export\\s+function\\s+/gm,'function ');"
            "const posts=[],dels=[];"
            "const http={post:(u,p,o)=>posts.push({u,p}),del:(u,p,o)=>dels.push(u),get:()=>({status:200})};"
            "class SharedArray{constructor(_n,fn){return fn();}}"
            "const origRandom=Math.random;"
            "Math.random=()=>0.1;"
            "const ctx={http,check:()=>true,sleep:()=>{},SharedArray,__ENV:{},__VU:1,__ITER:0,Math,Date,JSON};"
            "const res=vm.runInNewContext(src+'\\n;({setup:setup(),runTeardown:teardown});',ctx);"
            "Math.random=origRandom;"
            "res.runTeardown(res.setup);"
            "const delAfterValid=dels.length;"
            "res.runTeardown(undefined);"
            "console.log(JSON.stringify({seedId:res.setup.syntheticIds[0],posts:posts.length,delAfterValid,delAfterUndef:dels.length}));"
        )
        node_proc = subprocess.run(
            ["node", "-e", node_harness],
            capture_output=True,
            text=True,
            env={**os.environ, "K6_JS": k6_js},
            timeout=15,
        )
        self.assertEqual(node_proc.returncode, 0, node_proc.stderr)
        js_exec = json.loads(node_proc.stdout)
        self.assertEqual(js_exec["seedId"], 190000)
        self.assertEqual(js_exec["posts"], 1)
        self.assertEqual(js_exec["delAfterValid"], 1)
        self.assertEqual(js_exec["delAfterUndef"], 1)

    def test_k6_analyzer_cli_fails_on_dropped_iterations(self):
        """CLI & Resilience: k6_analyzer CLI exits nonzero when dropped_iterations > 0."""
        payload = {
            "metrics": {
                "http_req_duration": {"values": {"p(95)": 100.0, "p(99)": 200.0, "avg": 50.0}},
                "http_req_failed": {"values": {"rate": 0.0}},
                "http_reqs": {"values": {"count": 500, "rate": 20.0}},
                "dropped_iterations": {"values": {"count": 4}},
            }
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump(payload, tf)
            tmp_path = tf.name
        try:
            proc = subprocess.run(
                [sys.executable, os.path.join(PROJECT_ROOT, "tools", "perf", "k6_analyzer.py"), tmp_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 1)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
