#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tests/test_jmeter_compatibility.py — Red-Green-Purple Test Suite for Apache JMeter 5.6.3 Compatibility & Upgrades
Covers Positive, Negative, Boundary, and Concurrency/CLI Scenarios.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.contrib import generate_jmx_plan
from tools.perf import jtl_analyzer
from tools.report import telemetry_correlator


class TestJMeterCompatibilityAndUpgrades(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="synapse_jmeter_test_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # 1. POSITIVE: JMX XML Validity, __P() Syntax, & Groovy Runtime Safety
    # ------------------------------------------------------------------

    def test_generated_jmx_parameterized_and_valid_xml(self):
        """Generated JMX uses clean __P(key,default) without leading space and valid XML escaping."""
        samplers = [
            {"name": "List Orders", "path": "/api/v1/orders", "method": "GET", "body": "", "expected_status": 200},
            {"name": "Create Order", "path": "/api/v1/orders", "method": "POST", "body": '{"item": "A"}', "expected_status": 201},
        ]
        xml_str = generate_jmx_plan.build_jmx_xml(
            plan_name='Acme & "Partner" Load <Test>',
            base_host="staging.api.local",
            protocol="https",
            port="443",
            vus=20,
            ramp_up=10,
            duration=60,
            loop_count=-1,
            sla_p95=500,
            samplers=samplers,
            workload_profile="step",
            jsr223_hmac=True,
            think_time_min=1000,
            think_time_max=3000,
            target_rps=25.0,
        )
        root = ET.fromstring(xml_str)
        self.assertEqual(root.attrib.get("jmeter"), "5.6.3")

        # No leading whitespace after comma in ${__P(...)} functions
        p_calls = re.findall(r"\$\{__P\([^}]+\)\}", xml_str)
        self.assertTrue(len(p_calls) >= 4)
        for p_call in p_calls:
            self.assertNotRegex(p_call, r"\$\{__P\([^,]+,\s+", f"Leading whitespace in JMeter __P default: {p_call}")

        # Host, protocol, and port are overridable via -Jhost / -Jprotocol / -Jport
        self.assertIn("${__P(host,staging.api.local)}", xml_str)
        self.assertIn("${__P(protocol,https)}", xml_str)
        self.assertIn("${__P(port,443)}", xml_str)
        self.assertIn("${__P(max_latency,3000)}", xml_str)

        # Open arrival-rate pacing via ConstantThroughputTimer
        self.assertIn("<ConstantThroughputTimer", xml_str)
        self.assertIn("1500.0", xml_str)  # 25.0 RPS * 60 = 1500.0 samples/min

        # Verify sla_p95 * 2 ceiling and sub-1 RPS pacing (0.5 RPS = 30.0 samples/min)
        sub_rps_xml = generate_jmx_plan.build_jmx_xml(
            plan_name="SubRPS",
            base_host="localhost",
            protocol="http",
            port="8080",
            vus=5,
            ramp_up=1,
            duration=10,
            loop_count=1,
            sla_p95=2000,
            samplers=samplers,
            target_rps=0.5,
        )
        self.assertIn("${__P(max_latency,4000)}", sub_rps_xml)
        self.assertIn("30.0", sub_rps_xml)

        no_rps_xml = generate_jmx_plan.build_jmx_xml(
            plan_name="NoRPS",
            base_host="localhost",
            protocol="http",
            port="8080",
            vus=5,
            ramp_up=1,
            duration=10,
            loop_count=1,
            sla_p95=500,
            samplers=samplers,
            target_rps=0.0,
        )
        self.assertNotIn("<ConstantThroughputTimer", no_rps_xml)

        # Plan-level ResultCollector does not double-write alongside -l results.jtl
        collectors = root.findall(".//ResultCollector[@testclass='ResultCollector']")
        self.assertEqual(len(collectors), 1)
        self.assertEqual(collectors[0].attrib.get("enabled"), "false")

    def test_jsr223_groovy_scripts_use_valid_jmeter_apis(self):
        """AutoStop assertion uses shared AtomicLong in props; HMAC preprocessor avoids SampleResult & header leaks."""
        samplers = [{"name": "Get", "path": "/api/items", "method": "GET", "body": "", "expected_status": 200}]
        xml_str = generate_jmx_plan.build_jmx_xml(
            plan_name="Groovy Check",
            base_host="localhost",
            protocol="http",
            port="8080",
            vus=10,
            ramp_up=5,
            duration=30,
            loop_count=-1,
            sla_p95=500,
            samplers=samplers,
            jsr223_hmac=True,
            abort_on_fail=True,
        )
        root = ET.fromstring(xml_str)

        # Check AutoStop JSR223Assertion uses props + AtomicLong (not thread-local vars)
        autostop = root.find(".//JSR223Assertion[@testname='JSR223 - AutoStop Circuit Breaker']")
        self.assertIsNotNone(autostop)
        autostop_script = autostop.findtext("stringProp[@name='script']") or ""
        self.assertIn("AtomicLong", autostop_script)
        self.assertIn("props.", autostop_script)
        self.assertNotIn('vars.getObject("TOTAL_REQUESTS")', autostop_script)

        # Check HMAC JSR223PreProcessor does NOT reference invalid SampleResult binding,
        # checks getArgumentCount() > 0, and removes stale headers before adding.
        hmac_pp = root.find(".//JSR223PreProcessor[@testname='JSR223 - HMAC Payload Signer']")
        self.assertIsNotNone(hmac_pp)
        hmac_script = hmac_pp.findtext("stringProp[@name='script']") or ""
        self.assertNotIn("SampleResult.setStopTest", hmac_script)
        self.assertIn("ctx.getEngine()", hmac_script)
        self.assertIn("getArgumentCount()", hmac_script)
        self.assertIn("removeHeaderNamed", hmac_script)

    def test_openapi_query_params_and_negative_status_assertion(self):
        """OpenAPI query parameters are mapped to JMeter paths and negative status codes do not falsely pass on 200."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Query & Status Test"},
            "servers": [{"url": "https://staging.example.com"}],
            "paths": {
                "/api/v1/items/{itemId}": {
                    "parameters": [
                        {"name": "tenant", "in": "query", "schema": {"type": "string", "example": "acme"}},
                        {"name": "", "in": "query", "schema": {"type": "string"}},
                    ],
                    "get": {
                        "summary": "Get Item",
                        "parameters": [
                            {"name": "tenant", "in": "query", "schema": {"type": "string", "example": "override"}},
                            {"name": "page", "in": "query", "schema": {"type": "integer", "example": 1}},
                            {"name": "expand", "in": "query", "schema": {"type": "boolean"}},
                        ],
                        "responses": {"200": {"description": "OK"}},
                    },
                },
                "/api/v1/forbidden": {
                    "get": {
                        "summary": "Expect 403",
                        "responses": {"403": {"description": "Forbidden"}},
                    }
                },
            },
        }
        _, _, _, _, samplers = generate_jmx_plan.parse_openapi_for_jmeter(spec)
        get_item = next(s for s in samplers if s["name"] == "Get Item")
        self.assertIn("tenant=acme", get_item["path"])
        self.assertEqual(get_item["path"].count("tenant="), 1)
        self.assertNotIn("?=", get_item["path"])
        self.assertNotIn("&=", get_item["path"])
        self.assertIn("page=1", get_item["path"])
        self.assertIn("expand=true", get_item["path"])

        xml_str = generate_jmx_plan.build_jmx_xml(
            plan_name="Status Test",
            base_host="staging.example.com",
            protocol="https",
            port="443",
            vus=5,
            ramp_up=5,
            duration=30,
            loop_count=1,
            sla_p95=500,
            samplers=samplers,
        )
        root = ET.fromstring(xml_str)
        forbidden_assertion = root.find(".//ResponseAssertion[@testname='Assert Status (403)']")
        self.assertIsNotNone(forbidden_assertion)
        codes = [el.text for el in forbidden_assertion.findall(".//stringProp") if el.attrib.get("name") in ("403", "200", "201")]
        self.assertEqual(codes, ["403"])

    # ------------------------------------------------------------------
    # 2. NEGATIVE & BOUNDARY: Production Host Guard & CLI Think-Time Default
    # ------------------------------------------------------------------

    def test_production_url_blocked_without_allow_prod(self):
        """Host safety guard classifies prod vs non-prod accurately and blocks prod CLI targets without --allow-prod."""
        self.assertFalse(generate_jmx_plan._is_production_host(""))
        self.assertFalse(generate_jmx_plan._is_production_host("localhost:8080"))
        self.assertFalse(generate_jmx_plan._is_production_host("api.staging.example.com:443"))
        self.assertTrue(generate_jmx_plan._is_production_host("prod.example.com:8443"))
        self.assertTrue(generate_jmx_plan._is_production_host("api.prod.example.com"))
        self.assertTrue(generate_jmx_plan._is_production_host("production.example.com"))
        self.assertTrue(generate_jmx_plan._is_production_host("checkout.bank.com"))

        out_jmx = os.path.join(self.temp_dir, "prod_blocked.jmx")
        proc = subprocess.run(
            [
                sys.executable,
                os.path.join(_REPO_ROOT, "tools", "contrib", "generate_jmx_plan.py"),
                "--sample",
                "--base-url",
                "https://api.production.bank.com",
                "-o",
                out_jmx,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(os.path.exists(out_jmx))

    def test_cli_defaults_include_realistic_think_time(self):
        """Default CLI execution injects UniformRandomTimer (1000-3000ms) instead of 0ms socket hammer."""
        out_jmx = os.path.join(self.temp_dir, "default_think.jmx")
        proc = subprocess.run(
            [
                sys.executable,
                os.path.join(_REPO_ROOT, "tools", "contrib", "generate_jmx_plan.py"),
                "--sample",
                "--base-url",
                "http://localhost:8080",
                "-o",
                out_jmx,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(out_jmx, "r", encoding="utf-8") as f:
            xml_str = f.read()
        self.assertIn("<UniformRandomTimer", xml_str)
        self.assertIn('<stringProp name="ConstantTimer.delay">1000</stringProp>', xml_str)

    # ------------------------------------------------------------------
    # 3. JTL ANALYZER: XML Dedup, ISO Timestamps, & Steady-State Windowing
    # ------------------------------------------------------------------

    def test_jtl_analyzer_xml_no_double_count_and_steady_state_window(self):
        """XML JTL ignores nested subresults under TransactionController sample and supports warmup/cooldown filtering."""
        xml_jtl = os.path.join(self.temp_dir, "nested.jtl")
        with open(xml_jtl, "w", encoding="utf-8") as f:
            f.write(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<testResults version="1.2">\n'
                '  <sample t="500" lt="0" ts="1700000000000" s="true" lb="Checkout Flow" rc="200" by="1000">\n'
                '    <httpSample t="200" lt="190" ts="1700000000000" s="true" lb="/login" rc="200" by="400"/>\n'
                '    <httpSample t="300" lt="290" ts="1700000000200" s="true" lb="/pay" rc="200" by="600"/>\n'
                '  </sample>\n'
                '  <httpSample t="150" lt="140" ts="1700000015000" s="true" lb="Browse" rc="200" by="500"/>\n'
                '  <httpSample t="900" lt="880" ts="1700000035000" s="true" lb="Browse" rc="200" by="500"/>\n'
                '</testResults>\n'
            )

        per_sampler, agg = jtl_analyzer.parse_xml_jtl(xml_jtl)
        agg_stats = agg.compute()
        # Exactly 3 top-level samples (1 Transaction sample + 2 httpSample), NOT 5!
        self.assertEqual(agg_stats["samples"], 3)
        self.assertIn("Checkout Flow", per_sampler)
        self.assertNotIn("/login", per_sampler)

        # Steady-state filter: exclude first 10s (ts=0) and last 10s (ts=35s) -> only ts=15s (150ms) remains
        _, steady_agg = jtl_analyzer.parse_jtl(xml_jtl, warmup_sec=10.0, cooldown_sec=10.0)
        steady_stats = steady_agg.compute()
        self.assertEqual(steady_stats["samples"], 1)
        self.assertEqual(steady_stats["avg_ms"], 150.0)

    def test_jtl_analyzer_iso_timestamp_csv(self):
        """CSV JTL and parse_jtl_timestamp handle epoch sec/ms, empty/None, and ISO/JMeter date strings."""
        self.assertEqual(jtl_analyzer.parse_jtl_timestamp(None), 0)
        self.assertEqual(jtl_analyzer.parse_jtl_timestamp(""), 0)
        self.assertEqual(jtl_analyzer.parse_jtl_timestamp("   "), 0)
        self.assertEqual(jtl_analyzer.parse_jtl_timestamp(0), 0)
        self.assertEqual(jtl_analyzer.parse_jtl_timestamp(0.0), 0)
        self.assertEqual(jtl_analyzer.parse_jtl_timestamp(1700000000), 1700000000000)
        self.assertEqual(jtl_analyzer.parse_jtl_timestamp(1700000000.0), 1700000000000)
        self.assertEqual(jtl_analyzer.parse_jtl_timestamp("1700000000"), 1700000000000)
        self.assertEqual(jtl_analyzer.parse_jtl_timestamp(1700000000123), 1700000000123)
        self.assertEqual(jtl_analyzer.parse_jtl_timestamp("1700000000123"), 1700000000123)

        ts_utc = jtl_analyzer.parse_jtl_timestamp("2026-11-25T10:00:00Z")
        ts_naive = jtl_analyzer.parse_jtl_timestamp("2026-11-25T10:00:00")
        self.assertEqual(ts_naive, ts_utc)
        self.assertGreater(ts_utc, 1_000_000_000_000)
        ts_slash = jtl_analyzer.parse_jtl_timestamp("2026/11/25 10:00:00.100")
        self.assertEqual(ts_slash, ts_utc + 100)

        csv_jtl = os.path.join(self.temp_dir, "iso_ts.jtl")
        with open(csv_jtl, "w", encoding="utf-8") as f:
            f.write("timeStamp,elapsed,label,responseCode,success,bytes\n")
            f.write("2026/11/25 10:00:00.100,120,GET /items,200,true,512\n")
            f.write("2026-11-25T10:00:05.200Z,180,GET /items,200,true,512\n")

        per_sampler, agg = jtl_analyzer.parse_csv_jtl(csv_jtl)
        self.assertEqual(agg.compute()["samples"], 2)
        self.assertEqual(per_sampler["GET /items"].compute()["avg_ms"], 150.0)

    # ------------------------------------------------------------------
    # 4. TELEMETRY CORRELATOR: XML JTL + Lag-Compensated Cross-Correlation
    # ------------------------------------------------------------------

    def test_telemetry_correlator_handles_clock_skew_lag_and_xml_jtl(self):
        """Clock skew (+5s shift) still surfaces strong CPU correlation via lag-compensated cross-correlation."""
        xml_jtl = os.path.join(self.temp_dir, "corr.jtl")
        with open(xml_jtl, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<testResults version="1.2">\n')
            for idx, lat in enumerate([100, 110, 500, 900, 950, 120]):
                ts = 1700000000000 + idx * 5000
                f.write(f'  <httpSample t="{lat}" ts="{ts}" s="true" lb="API" rc="200" by="100"/>\n')
            f.write("</testResults>\n")

        jtl_buckets = telemetry_correlator.parse_jtl_time_series(xml_jtl, bucket_sec=5)
        self.assertEqual(len(jtl_buckets), 6)

        # Server metrics shifted +5s ahead (1 bucket lag) due to NTP drift
        server_series = {
            "cpu_pct": {
                1700000005: 20.0,
                1700000010: 22.0,
                1700000015: 60.0,
                1700000020: 92.0,
                1700000025: 95.0,
                1700000030: 25.0,
            },
            "memory_pct": {1700000000 + i * 5: 40.0 for i in range(7)},
            "db_pool_pct": {1700000000 + i * 5: 20.0 for i in range(7)},
            "disk_iops": {1700000000 + i * 5: 50.0 for i in range(7)},
        }

        analysis = telemetry_correlator.run_correlation_analysis(jtl_buckets, server_series, max_lag_buckets=2)
        self.assertIn("lag_compensated_correlations", analysis)
        self.assertGreater(analysis["lag_compensated_correlations"]["cpu_correlation"]["r"], 0.9)
        self.assertEqual(analysis["lag_compensated_correlations"]["cpu_correlation"]["lag_sec"], 5)
        self.assertTrue(any(rc["component"] == "Server CPU Compute" for rc in analysis["root_causes"]))

        # Boundary max_lag_buckets=1 must still include +1 lag (+5s)
        one_lag = telemetry_correlator.run_correlation_analysis(jtl_buckets, server_series, max_lag_buckets=1)
        self.assertEqual(one_lag["lag_compensated_correlations"]["cpu_correlation"]["lag_sec"], 5)
        self.assertGreater(one_lag["lag_compensated_correlations"]["cpu_correlation"]["r"], 0.9)

        # Missing bucket fallback must use 0.0 (not 1.0): y=[0.0, 1.0] gives r=1.0 vs y=[1.0, 1.0] giving r=0.0
        missing_bucket_res = telemetry_correlator.run_correlation_analysis(
            {1700000000: [100.0], 1700000005: [200.0]},
            {"cpu_pct": {1700000005: 1.0}, "memory_pct": {}, "db_pool_pct": {}, "disk_iops": {}},
            max_lag_buckets=0,
        )
        self.assertAlmostEqual(missing_bucket_res["lag_compensated_correlations"]["cpu_correlation"]["r"], 1.0, places=4)

        # Zero lag_buckets disables lag search; synchronous r stays lower than lag-compensated r
        no_lag = telemetry_correlator.run_correlation_analysis(jtl_buckets, server_series, max_lag_buckets=0)
        self.assertEqual(no_lag["lag_compensated_correlations"]["cpu_correlation"]["lag_sec"], 0)
        self.assertLess(
            no_lag["lag_compensated_correlations"]["cpu_correlation"]["r"],
            analysis["lag_compensated_correlations"]["cpu_correlation"]["r"],
        )

        # Also test tab-delimited CSV JTL and XML fallback attributes (missing ts/t)
        tsv_jtl = os.path.join(self.temp_dir, "corr.tsv")
        with open(tsv_jtl, "w", encoding="utf-8") as f:
            f.write("timeStamp\telapsed\tlabel\tresponseCode\tsuccess\n")
            f.write("1700000000000\t120\tGET /a\t200\ttrue\n")
            f.write("\t\tGET /empty\t200\ttrue\n")
        tsv_buckets = telemetry_correlator.parse_jtl_time_series(tsv_jtl, bucket_sec=5)
        self.assertEqual(tsv_buckets[1700000000], [120.0])
        self.assertEqual(tsv_buckets[0], [0.0])

        fallback_xml = os.path.join(self.temp_dir, "fallback.jtl")
        with open(fallback_xml, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<testResults>\n  <httpSample lb="Missing" s="true"/>\n</testResults>\n')
        fb_buckets = telemetry_correlator.parse_jtl_time_series(fallback_xml, bucket_sec=5)
        self.assertEqual(fb_buckets[0], [0.0])

    # ------------------------------------------------------------------
    # 5. EXAMPLES & DISTRIBUTED DOCKER COMPOSE ALIGNMENT
    # ------------------------------------------------------------------

    def test_example_jmx_files_and_docker_compose_compatible(self):
        """All repo .jmx suites use Asserion.test_strings (no Asserter typo), clean __P(), and 5.6.3 Docker image."""
        jmx_files = [
            os.path.join(_REPO_ROOT, "examples", "perf-backend-suite", "jmeter", "jmeter_api_load_suite.jmx"),
            os.path.join(_REPO_ROOT, "examples", "perf-backend-suite", "jmeter", "customer_api_plan.jmx"),
        ]
        for path in jmx_files:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
            ET.fromstring(raw)
            self.assertNotIn("Asserter.test_strings", raw, f"Broken JMeter Assertion property in {path}")
            self.assertIn("Asserion.test_strings", raw, f"Missing Asserion.test_strings in {path}")
            for p_call in re.findall(r"\$\{__P\([^}]+\)\}", raw):
                self.assertNotRegex(p_call, r"\$\{__P\([^,]+,\s+", f"Leading space in __P() default in {path}: {p_call}")

        compose_path = os.path.join(_REPO_ROOT, "tools", "templates", "jmeter-distributed", "docker-compose.yml")
        with open(compose_path, "r", encoding="utf-8") as f:
            compose_raw = f.read()
        self.assertIn("5.6.3", compose_raw)
        self.assertNotIn("justb4/jmeter:5.5", compose_raw)


if __name__ == "__main__":
    unittest.main()
