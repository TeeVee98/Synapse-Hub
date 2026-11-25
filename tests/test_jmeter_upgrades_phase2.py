#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tests/test_jmeter_upgrades_phase2.py — Red-Green-Purple Test Suite for Deep JMeter & Perf Upgrades
Covers:
  1. Method-aware --weighted-mix Pareto partitioning
  2. Real Kafka JSR223Sampler vs --jms-sample + plugin search_paths in Docker Compose
  3. Gate 10 warmup/cooldown config & Tiered Per-Sampler SLA evaluation
  4. Live Prometheus HTTP query_range & OTLP HTTP push in telemetry_correlator
  5. JMeter/k6 performance log parsing in distill_log
  6. skills_index.json jmeter trigger & SHA-pinned CI templates
"""

import json
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
from io import BytesIO
from unittest.mock import patch

import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.contrib import generate_jmx_plan
from tools.core import distill_log
from tools.core.gates import gate_10_perf_sla
from tools.perf import jtl_analyzer
from tools.report import telemetry_correlator


class _FakeHTTPResponse:
    def __init__(self, payload: bytes, status: int = 200):
        self._buf = BytesIO(payload)
        self.status = status

    def read(self) -> bytes:
        return self._buf.read()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestJMeterDeepUpgrades(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="synapse_jmeter_upg_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # 1. Method-Aware Pareto --weighted-mix Partitioning
    # ------------------------------------------------------------------

    def test_weighted_mix_groups_reads_before_mutations(self):
        """Pareto 70,20,10 routes GET read endpoints into 70% bucket even when input list starts with POST."""
        samplers = [
            {"name": "Create Order", "path": "/api/v1/orders", "method": "POST", "body": "{}", "expected_status": 201},
            {"name": "Update Order", "path": "/api/v1/orders/1", "method": "PUT", "body": "{}", "expected_status": 200},
            {"name": "List Catalog", "path": "/api/v1/catalog", "method": "GET", "body": "", "expected_status": 200},
            {"name": "Get Item", "path": "/api/v1/items/1", "method": "GET", "body": "", "expected_status": 200},
            {"name": "Heavy Report", "path": "/api/v1/reports/sales", "method": "GET", "body": "", "expected_status": 200},
        ]
        xml_str = generate_jmx_plan.build_jmx_xml(
            plan_name="Pareto Test",
            base_host="staging.local",
            protocol="https",
            port="443",
            vus=20,
            ramp_up=5,
            duration=60,
            loop_count=-1,
            sla_p95=500,
            samplers=samplers,
            weighted_mix="70:Read,20:Write,10:Heavy",
        )
        root = ET.fromstring(xml_str)
        controllers = root.findall(".//ThroughputController")
        self.assertEqual(len(controllers), 3)

        # Inspect sibling hashTree of first (70% Read) controller -> must contain GET /catalog, NOT POST /orders
        plan_ht = root.find("./hashTree/hashTree")
        plan_children = list(plan_ht)
        tg_idx = next(i for i, el in enumerate(plan_children) if el.tag == "ThreadGroup")
        children = list(plan_children[tg_idx + 1])
        tc0_idx = children.index(controllers[0])
        tc0_ht = children[tc0_idx + 1]
        tc0_samplers = [el.attrib["testname"] for el in tc0_ht.findall("./HTTPSamplerProxy")]
        self.assertTrue(all(name.startswith("[GET]") for name in tc0_samplers), f"Non-GET in 70% Read bucket: {tc0_samplers}")
        self.assertIn("[GET] List Catalog", tc0_samplers)

        # Second (20% Write) controller must contain POST/PUT mutations
        tc1_idx = children.index(controllers[1])
        tc1_ht = children[tc1_idx + 1]
        tc1_samplers = [el.attrib["testname"] for el in tc1_ht.findall("./HTTPSamplerProxy")]
        self.assertIn("[POST] Create Order", tc1_samplers)
        self.assertIn("[PUT] Update Order", tc1_samplers)

        # Third (10% Heavy) controller must contain Heavy Report
        tc2_idx = children.index(controllers[2])
        tc2_ht = children[tc2_idx + 1]
        tc2_samplers = [el.attrib["testname"] for el in tc2_ht.findall("./HTTPSamplerProxy")]
        self.assertEqual(tc2_samplers, ["[GET] Heavy Report"])

        # Two-bucket Pareto mix merges reads + heavy into bucket 0 and writes into bucket 1
        two_buckets = generate_jmx_plan._partition_samplers_by_weights(
            samplers, [(70.0, "Read"), (30.0, "Write")]
        )
        self.assertEqual([s["name"] for s in two_buckets[0]], ["List Catalog", "Get Item", "Heavy Report"])
        self.assertEqual([s["name"] for s in two_buckets[1]], ["Create Order", "Update Order"])

        # Homogeneous single-class list falls back to sequential chunking
        only_gets = [s for s in samplers if s["method"] == "GET"][:2]
        seq_buckets = generate_jmx_plan._partition_samplers_by_weights(only_gets, [(50.0, "A"), (50.0, "B")])
        self.assertEqual([s["name"] for s in seq_buckets[0]], ["List Catalog"])
        self.assertEqual([s["name"] for s in seq_buckets[1]], ["Get Item"])

    # ------------------------------------------------------------------
    # 2. Real Kafka JSR223Sampler, JMS Separation, & Docker Plugin Mount
    # ------------------------------------------------------------------

    def test_kafka_sample_uses_native_kafka_producer_not_jms(self):
        """Kafka plan emits JSR223Sampler with KafkaProducer; JMS remains distinct via jms_config."""
        kafka_xml = generate_jmx_plan.build_jmx_xml(
            plan_name="Kafka Stream",
            base_host="localhost",
            protocol="kafka",
            port="9092",
            vus=10,
            ramp_up=5,
            duration=30,
            loop_count=-1,
            sla_p95=500,
            samplers=[],
            kafka_config={"brokers": "kafka-1:9092", "topic": "orders.events"},
        )
        root = ET.fromstring(kafka_xml)
        self.assertIsNone(root.find(".//org.apache.jmeter.protocol.jms.sampler.PublisherSampler"))
        kafka_sampler = root.find(".//JSR223Sampler[@testname='[Kafka] Stream Message Producer']")
        self.assertIsNotNone(kafka_sampler)
        script = kafka_sampler.findtext("stringProp[@name='script']") or ""
        self.assertIn("KafkaProducer", script)
        self.assertIn("ProducerRecord", script)
        self.assertIn("orders.events", script)

        jms_xml = generate_jmx_plan.build_jmx_xml(
            plan_name="JMS Queue",
            base_host="localhost",
            protocol="jms",
            port="61616",
            vus=5,
            ramp_up=2,
            duration=20,
            loop_count=1,
            sla_p95=500,
            samplers=[],
            jms_config={"provider_url": "tcp://localhost:61616", "destination": "orders.queue"},
        )
        jms_root = ET.fromstring(jms_xml)
        self.assertIsNotNone(jms_root.find(".//org.apache.jmeter.protocol.jms.sampler.PublisherSampler"))

        compose_path = os.path.join(_REPO_ROOT, "tools", "templates", "jmeter-distributed", "docker-compose.yml")
        with open(compose_path, "r", encoding="utf-8") as f:
            compose_raw = f.read()
        self.assertIn("/jmeter/plugins", compose_raw)
        self.assertIn("search_paths", compose_raw)

    # ------------------------------------------------------------------
    # 3. Tiered Per-Sampler SLA & Gate 10 Config Integration
    # ------------------------------------------------------------------

    def test_tiered_sampler_sla_and_gate10_warmup_config(self):
        """Tiered SLA catches slow Read endpoint even when aggregate P95 passes; Gate 10 honors warmup_sec."""
        per_sampler_data = [
            {"label": "[GET] /api/v1/catalog", "samples": 100, "errors": 0, "error_rate_pct": 0.0, "p95_ms": 320.0},
            {"label": "[POST] /api/v1/checkout", "samples": 20, "errors": 0, "error_rate_pct": 0.0, "p95_ms": 750.0},
        ]
        passed, violations = jtl_analyzer.evaluate_tiered_sampler_sla(per_sampler_data)
        self.assertFalse(passed)
        self.assertTrue(any("[GET] /api/v1/catalog" in v and "200" in v for v in violations))
        self.assertFalse(any("[POST] /api/v1/checkout" in v for v in violations))

        # Gate 10 honoring warmup_sec: warmup sample at ts=0 has 2000ms (breaches 500ms), steady-state at ts=20s has 100ms
        perf_dir = os.path.join(self.temp_dir, "reports", "perf")
        os.makedirs(perf_dir, exist_ok=True)
        jtl_path = os.path.join(perf_dir, "results.jtl")
        with open(jtl_path, "w", encoding="utf-8") as f:
            f.write("timeStamp,elapsed,label,responseCode,success,bytes\n")
            f.write("1795600000000,2000,[GET] /api/v1/catalog,200,true,100\n")
            f.write("1795600020000,100,[GET] /api/v1/catalog,200,true,100\n")
            f.write("1795600025000,120,[GET] /api/v1/catalog,200,true,100\n")

        cfg = {
            "version": "4.8.4",
            "quality_gates": {"mutation_min_score": 80, "gates": {}},
            "performance": {
                "sla": {
                    "p95_ms": 500.0,
                    "p99_ms": 1000.0,
                    "max_error_rate_pct": 1.0,
                    "warmup_sec": 10.0,
                    "cooldown_sec": 0.0,
                    "require_fresh": False,
                },
                "client_auto_benchmark_fallback": False,
            },
        }
        with open(os.path.join(self.temp_dir, "synapse.config.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f)

        self.assertTrue(gate_10_perf_sla.gate_10_performance_sla(self.temp_dir, mode="CLIENT"))

        # Now write a slow Read JTL (320ms > 200ms Read tier, < 500ms global SLA) to verify tiered_sla toggle
        with open(jtl_path, "w", encoding="utf-8") as f:
            f.write("timeStamp,elapsed,label,responseCode,success,bytes\n")
            f.write("1795600020000,320,[GET] /api/v1/catalog,200,true,100\n")

        # Without tiered_sla, aggregate 320ms <= 500ms passes
        self.assertTrue(gate_10_perf_sla.gate_10_performance_sla(self.temp_dir, mode="CLIENT"))

        # With tiered_sla=True, 320ms > 200ms Read tier fails Gate 10
        cfg["performance"]["sla"]["tiered_sla"] = True
        with open(os.path.join(self.temp_dir, "synapse.config.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        self.assertFalse(gate_10_perf_sla.gate_10_performance_sla(self.temp_dir, mode="CLIENT"))

        # With custom tiered_rules raising read_p95_ms to 400ms, passes again
        cfg["performance"]["sla"]["tiered_rules"] = {"read_p95_ms": 400.0}
        with open(os.path.join(self.temp_dir, "synapse.config.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        self.assertTrue(gate_10_perf_sla.gate_10_performance_sla(self.temp_dir, mode="CLIENT"))

    # ------------------------------------------------------------------
    # 4. Live Prometheus Query & OTLP HTTP Push
    # ------------------------------------------------------------------

    def test_prometheus_query_range_and_otlp_push(self):
        """fetch_prometheus_metrics parses Prometheus matrix JSON; push_otlp_metrics POSTs OTLP payload."""
        prom_cpu = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [{"metric": {}, "values": [[1700000000, "45.5"], [1700000005, "88.2"]]}],
            },
        }
        prom_empty = {"status": "success", "data": {"resultType": "matrix", "result": []}}

        def _mock_urlopen(req, timeout=5.0):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if "api/v1/query_range" in url and "cpu" in url:
                return _FakeHTTPResponse(json.dumps(prom_cpu).encode("utf-8"), 200)
            if "api/v1/query_range" in url:
                return _FakeHTTPResponse(json.dumps(prom_empty).encode("utf-8"), 200)
            if "v1/metrics" in url:
                return _FakeHTTPResponse(b'{"partialSuccess":{}}', 200)
            raise AssertionError(f"Unexpected URL: {url}")

        with patch("urllib.request.urlopen", side_effect=_mock_urlopen):
            # Custom query key not in default series
            custom_series = telemetry_correlator.fetch_prometheus_metrics(
                "http://prometheus.local:9090",
                start_epoch=1700000000,
                end_epoch=1700000010,
                bucket_sec=5,
                queries={"cpu_pct": "node_cpu_pct", "custom_queue": "queue_depth"},
            )
            self.assertEqual(custom_series["cpu_pct"][1700000000], 45.5)
            self.assertEqual(custom_series["cpu_pct"][1700000005], 88.2)
            self.assertIn("custom_queue", custom_series)

            # Default PromQL queries (queries=None)
            default_series = telemetry_correlator.fetch_prometheus_metrics(
                "http://prometheus.local:9090",
                start_epoch=1700000000,
                end_epoch=1700000010,
                bucket_sec=5,
            )
            self.assertEqual(default_series["cpu_pct"][1700000000], 45.5)

            empty_otel = telemetry_correlator.build_otel_payload({})
            empty_metrics = empty_otel["resourceMetrics"][0]["scopeMetrics"][0]["metrics"]
            self.assertEqual([m["gauge"]["dataPoints"][0]["asDouble"] for m in empty_metrics], [0.0, 0.0, 0.0])

            payload = telemetry_correlator.build_otel_payload(
                {"metrics_summary": {"max_p95_ms": 250.0, "max_cpu_pct": 88.2, "max_memory_pct": 60.0}}
            )
            ok, detail = telemetry_correlator.push_otlp_metrics("http://otel.local:4318/v1/metrics", payload)
            self.assertTrue(ok, detail)

    # ------------------------------------------------------------------
    # 5. JMeter & k6 Performance Log Support in distill_log
    # ------------------------------------------------------------------

    def test_distill_log_handles_jmeter_zero_err_vs_nonzero_err(self):
        """JMeter Err: 0 (0.00%) is not flagged as failure; Err: > 0 and k6 crossed thresholds are caught."""
        clean_jmeter_log = (
            "Creating summariser <summary>\n"
            "summary +   1500 in 00:00:10 =  150.0/s Avg:   120 Min:    15 Max:   450 Err:     0 (0.00%) Active: 50 Started: 50 Finished: 0\n"
            "summary =   3000 in 00:00:20 =  150.0/s Avg:   125 Min:    15 Max:   480 Err:     0 (0.00%) Active: 0 Started: 50 Finished: 50\n"
            "... end of run\n"
        )
        res_clean = distill_log.distill(clean_jmeter_log, exit_code=0)
        self.assertIn("ALL TESTS PASSED (Exit Code: 0)", res_clean)
        self.assertIn("--- Performance Telemetry Summary ---", res_clean)
        self.assertIn("summary =", res_clean)
        self.assertNotIn("CONFLICTING_SIGNALS", res_clean)

        # Boundary: exact Err: 1 must trigger failure (kills > 0 vs > 1 mutant)
        one_err_log = (
            "summary =   3000 in 00:00:20 =  150.0/s Avg:   220 Min:    15 Max:   900 Err:     1 (0.03%) Active: 0 Started: 50 Finished: 50\n"
        )
        res_one_err = distill_log.distill(one_err_log, exit_code=1)
        self.assertIn("FAILURES", res_one_err)
        self.assertIn("Err:     1 (0.03%)", res_one_err)

        # k6 summary telemetry preserved on clean pass
        clean_k6_log = (
            "     ✓ status is 200\n"
            "     http_req_duration..............: avg=45.2ms min=12ms med=41ms max=190ms p(90)=85ms p(95)=110ms\n"
        )
        res_k6 = distill_log.distill(clean_k6_log, exit_code=0)
        self.assertIn("ALL TESTS PASSED (Exit Code: 0)", res_k6)
        self.assertIn("http_req_duration", res_k6)

    # ------------------------------------------------------------------
    # 6. skills_index.json jmeter Trigger & CI Templates
    # ------------------------------------------------------------------

    def test_skills_index_includes_jmeter_and_ci_templates_exist(self):
        """skills_index.json routes 'jmeter' to backend-load-and-stress-patterns and CI JMeter templates exist."""
        with open(os.path.join(_REPO_ROOT, "skills_index.json"), "r", encoding="utf-8") as f:
            idx = json.load(f)
        perf_skill = next(s for s in idx["skills"] if s["id"] == "backend-load-and-stress-patterns")
        self.assertIn("jmeter", perf_skill["stack_triggers"])

        gha_tmpl = os.path.join(
            _REPO_ROOT, "skills", "09-ci-and-devops", "github-actions-templates", "examples", "jmeter_perf_pipeline.yml"
        )
        gl_tmpl = os.path.join(
            _REPO_ROOT, "skills", "09-ci-and-devops", "gitlab-ci-templates", "examples", "jmeter_gitlab_ci.yml"
        )
        self.assertTrue(os.path.isfile(gha_tmpl))
        self.assertTrue(os.path.isfile(gl_tmpl))
        with open(gha_tmpl, "r", encoding="utf-8") as f:
            gha_raw = f.read()
        self.assertIn("alpine/jmeter:5.6.3", gha_raw)
        self.assertIn("analyze-jtl", gha_raw)


if __name__ == "__main__":
    unittest.main()
