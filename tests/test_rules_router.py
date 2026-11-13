#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

import json
import os
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, PROJECT_ROOT)

from tools.rules_router import (
    detect_workspace_stacks,
    route_rules,
    format_routing_report,
)


class TestRulesRouter(unittest.TestCase):
    """Verifies Progressive Rules Router & Context Optimizer (Boost B2)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_detect_playwright_stack(self):
        # Create a mock playwright.config.ts
        config_path = os.path.join(self.workspace, "playwright.config.ts")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("export default {};")

        res = detect_workspace_stacks(self.workspace)
        self.assertIn("playwright", res["detected_stacks"])
        self.assertTrue(any("playwright.config.ts" in ev for ev in res["evidence"]["playwright"]))

    def test_detect_mobile_appium_stack(self):
        caps_path = os.path.join(self.workspace, "caps.json")
        with open(caps_path, "w", encoding="utf-8") as f:
            f.write('{"platformName": "Android"}')

        res = detect_workspace_stacks(self.workspace)
        self.assertIn("mobile", res["detected_stacks"])
        self.assertTrue(any("caps.json" in ev for ev in res["evidence"]["mobile"]))

    def test_detect_performance_stack(self):
        jmx_path = os.path.join(self.workspace, "load_test.jmx")
        with open(jmx_path, "w", encoding="utf-8") as f:
            f.write("<jmeterTestPlan></jmeterTestPlan>")

        res = detect_workspace_stacks(self.workspace)
        self.assertIn("performance", res["detected_stacks"])

    def test_detect_security_stack(self):
        semgrep_path = os.path.join(self.workspace, "semgrep.yml")
        with open(semgrep_path, "w", encoding="utf-8") as f:
            f.write("rules: []")

        res = detect_workspace_stacks(self.workspace)
        self.assertIn("security", res["detected_stacks"])

    def test_detect_polyglot_python_requirements_playwright(self):
        req_path = os.path.join(self.workspace, "requirements.txt")
        with open(req_path, "w", encoding="utf-8") as f:
            f.write("pytest-playwright>=0.4.0\nplaywright==1.40.0\n")

        res = detect_workspace_stacks(self.workspace)
        self.assertIn("playwright", res["detected_stacks"])
        self.assertTrue(any("requirements.txt" in ev for ev in res["evidence"]["playwright"]))

    def test_detect_polyglot_gradle_mobile(self):
        gradle_path = os.path.join(self.workspace, "build.gradle")
        with open(gradle_path, "w", encoding="utf-8") as f:
            f.write("dependencies { implementation 'io.appium:java-client:8.5.1' }")

        res = detect_workspace_stacks(self.workspace)
        self.assertIn("mobile", res["detected_stacks"])
        self.assertTrue(any("build.gradle" in ev for ev in res["evidence"]["mobile"]))

    def test_detect_polyglot_pyproject_locust_perf(self):
        pyproj_path = os.path.join(self.workspace, "pyproject.toml")
        with open(pyproj_path, "w", encoding="utf-8") as f:
            f.write("[project]\ndependencies = ['locust>=2.15.0']\n")

        res = detect_workspace_stacks(self.workspace)
        self.assertIn("performance", res["detected_stacks"])
        self.assertTrue(any("pyproject.toml" in ev for ev in res["evidence"]["performance"]))

    def test_route_rules_token_savings(self):
        # Empty workspace should yield base rules and substantial token savings
        routed = route_rules(self.workspace)
        self.assertIn("recommended_rules", routed)
        self.assertIn("recommended_skills", routed)
        self.assertIn("token_metrics", routed)

        metrics = routed["token_metrics"]
        self.assertGreater(metrics["tokens_saved"], 3000, "Must save at least 3,000 tokens on base stacks")
        self.assertGreater(metrics["reduction_percentage"], 50.0)

    def test_format_routing_report_json_and_text(self):
        routed = route_rules(self.workspace)
        text_rep = format_routing_report(routed, fmt="text")
        self.assertIn("SYNAPSE HUB — PROGRESSIVE RULES ROUTER", text_rep)
        self.assertIn("Tokens Saved/Turn", text_rep)

        json_rep = format_routing_report(routed, fmt="json")
        parsed = json.loads(json_rep)
        self.assertEqual(parsed["workspace"], os.path.abspath(self.workspace))


if __name__ == "__main__":
    unittest.main()
