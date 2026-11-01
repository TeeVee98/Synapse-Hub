#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tests/test_orphan_tools.py
--------------------------
Unit and functional test suite for previously unreferenced Hub tools (Finding F36):
  1. agent_canary.py
  2. export_postman_collection.py
  3. generate_tc_from_story.py
  4. git_pre_commit_guard.py
  5. jtl_analyzer.py
  6. newman_analyzer.py
  7. pinpoint_failure.py
  8. telemetry_correlator.py
"""

import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import agent_canary
import export_postman_collection
import generate_tc_from_story
import git_pre_commit_guard
import jtl_analyzer
import newman_analyzer
import pinpoint_failure
import telemetry_correlator


class TestOrphanToolsUnit(unittest.TestCase):

    def test_agent_canary_vectors_and_arena(self):
        """Validates agent_canary Arena loads all 8 failure vectors."""
        arena = agent_canary.CanaryArena()
        self.assertEqual(len(arena.vectors), 8)
        names = [v.name for v in arena.vectors]
        self.assertIn("UTF-8 Byte Order Mark Contamination", names)
        self.assertIn("Stale Element & Locator Drift", names)

    def test_export_postman_collection_scripts_and_env(self):
        """Validates export_postman_collection script generation and environment structure."""
        script = export_postman_collection.build_test_script(200, 500)
        self.assertTrue(any("Status code is 200" in line for line in script))
        self.assertTrue(any("500" in line for line in script))

        env = export_postman_collection.generate_postman_environment(name="TestEnv", base_url="https://api.example.com")
        self.assertIn("values", env)
        self.assertEqual(env["name"], "TestEnv")
        self.assertTrue(any(v.get("key") == "baseUrl" for v in env["values"]))

    def test_generate_tc_from_story_package_and_script(self):
        """Validates generate_tc_from_story package detection and script generation."""
        pkg = generate_tc_from_story.detect_project_package()
        self.assertIsInstance(pkg, str)
        self.assertTrue(len(pkg) > 0)

        mock_classes = {"LoginPage": ["login", "open"]}
        script = generate_tc_from_story.generate_script("TC-01", "User Login", "Login successfully", mock_classes, pkg)
        self.assertIn("TC-01", script)
        self.assertIn("LoginPage", script)

    def test_git_pre_commit_guard_checks(self):
        """Validates git_pre_commit_guard checks BOM, paths, and clean POM."""
        with tempfile.NamedTemporaryFile("wb", delete=False) as f:
            f.write(b"\xef\xbb\xbfimport pages.LoginPage")
            bom_path = f.name
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write("import pages.LoginPage\nloginPage.login()")
            clean_path = f.name
        try:
            bom_results = git_pre_commit_guard.check_bom([bom_path, clean_path])
            self.assertIn(bom_path, bom_results)
            self.assertNotIn(clean_path, bom_results)

            clean_pom_viols = git_pre_commit_guard.check_scripts_clean_pom([clean_path])
            self.assertEqual(len(clean_pom_viols), 0)
        finally:
            if os.path.exists(bom_path):
                os.remove(bom_path)
            if os.path.exists(clean_path):
                os.remove(clean_path)

    def test_jtl_analyzer_percentiles_and_sla(self):
        """Validates jtl_analyzer percentile calculation and SLA evaluation."""
        latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        p50 = jtl_analyzer.calculate_percentile(latencies, 50)
        p90 = jtl_analyzer.calculate_percentile(latencies, 90)
        p99 = jtl_analyzer.calculate_percentile(latencies, 99)
        self.assertAlmostEqual(p50, 55.0, delta=5.0)
        self.assertGreater(p90, p50)
        self.assertGreaterEqual(p99, p90)

        # evaluate_sla
        stats = jtl_analyzer.SamplerStats(label="GET /users")
        for lat in latencies:
            stats.add_sample(elapsed=lat, success=True, timestamp=1600000000, bytes_recv=1024, response_code="200")
        agg_stats = {
            "p95_ms": 95.0,
            "p99_ms": 99.0,
            "avg_ms": 55.0,
            "error_rate_pct": 0.0
        }
        compliant, viols = jtl_analyzer.evaluate_sla(agg_stats, sla_p95=200.0, max_error_rate=1.0)
        self.assertTrue(compliant)
        self.assertEqual(len(viols), 0)

    def test_newman_analyzer_sla_and_report(self):
        """Validates newman_analyzer SLA evaluation and report formatting."""
        mock_summary = {
            "collection_name": "Production Smoke Test",
            "total_requests": 25,
            "failed_requests": 0,
            "total_assertions": 50,
            "failed_assertions": 0,
            "assertion_pass_ratio_pct": 100.0,
            "latency": {
                "avg_ms": 145.2,
                "min_ms": 50.0,
                "max_ms": 280.0,
                "p95_ms": 250.0,
            },
            "error_rate_pct": 0.0,
            "failures": [],
            "requests": []
        }
        passed, viols = newman_analyzer.evaluate_newman_sla(mock_summary, max_failures=0, sla_avg=200.0)
        self.assertTrue(passed)
        self.assertEqual(len(viols), 0)

        md = newman_analyzer.generate_markdown_report(mock_summary, passed=True, violations=[])
        self.assertIn("Postman / Newman API Automated Test Report", md)
        self.assertIn("PASSED", md)

    def test_pinpoint_failure_junit_parser(self):
        """Validates pinpoint_failure parses JUnit XML test failures."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="TS_Auth" tests="2" failures="1" errors="0">
    <testcase name="TC_01_ValidLogin" classname="Auth" time="1.5" />
    <testcase name="TC_02_InvalidPassword" classname="Auth" time="2.1">
      <failure message="Reason: Expected error banner not displayed">
        Stacktrace: Enterprise.pages.LoginPage.groovy:48
      </failure>
    </testcase>
  </testsuite>
</testsuites>"""
        with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False) as f:
            f.write(xml_content)
            xml_file = f.name
        try:
            failures = pinpoint_failure.parse_failures(xml_file)
            self.assertEqual(len(failures), 1)
            self.assertEqual(failures[0]["tc"], "TC_02_InvalidPassword")
            self.assertIn("Expected error banner not displayed", failures[0]["reason"])
            self.assertIn("Enterprise.pages.LoginPage.groovy:48", failures[0]["failed_at"])
        finally:
            if os.path.exists(xml_file):
                os.remove(xml_file)

    def test_telemetry_correlator_pearson_and_rca(self):
        """Validates telemetry_correlator Pearson correlation and RCA markdown output."""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        r = telemetry_correlator.calculate_pearson_correlation(x, y)
        self.assertAlmostEqual(r, 1.0, places=4)

        x_inv = [1.0, 2.0, 3.0, 4.0, 5.0]
        y_inv = [10.0, 8.0, 6.0, 4.0, 2.0]
        r_inv = telemetry_correlator.calculate_pearson_correlation(x_inv, y_inv)
        self.assertAlmostEqual(r_inv, -1.0, places=4)


if __name__ == "__main__":
    unittest.main()
