#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_rules_router.py — Tests for Progressive Rules Router & Context Optimizer (Boost B2)
Verifies multi-stack detection (Playwright, Cypress, Katalon, Pytest-API, Selenium, Mobile, Monorepo),
confidence scoring, and dual-tier token hydration.
"""

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
        config_path = os.path.join(self.workspace, "playwright.config.ts")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("export default {};")

        res = detect_workspace_stacks(self.workspace)
        self.assertIn("playwright", res["detected_stacks"])
        self.assertEqual(res["confidence"]["playwright"], 1.0)

    def test_detect_katalon_stack(self):
        prj_path = os.path.join(self.workspace, "my_katalon.prj")
        with open(prj_path, "w", encoding="utf-8") as f:
            f.write("<Project></Project>")
        os.makedirs(os.path.join(self.workspace, "Keywords"), exist_ok=True)

        res = detect_workspace_stacks(self.workspace)
        self.assertIn("katalon", res["detected_stacks"])
        self.assertEqual(res["confidence"]["katalon"], 1.0)

    def test_detect_pytest_api_stack(self):
        req_path = os.path.join(self.workspace, "requirements.txt")
        with open(req_path, "w", encoding="utf-8") as f:
            f.write("pytest>=7.4.0\nrequests>=2.31.0\n")
        conf_path = os.path.join(self.workspace, "conftest.py")
        with open(conf_path, "w", encoding="utf-8") as f:
            f.write("import requests\ndef api_client(): pass\n")

        res = detect_workspace_stacks(self.workspace)
        self.assertIn("api", res["detected_stacks"])
        self.assertGreaterEqual(res["confidence"]["api"], 0.75)

    def test_detect_selenium_stack(self):
        req_path = os.path.join(self.workspace, "requirements.txt")
        with open(req_path, "w", encoding="utf-8") as f:
            f.write("selenium>=4.15.0\npytest-selenium>=4.0.0\n")

        res = detect_workspace_stacks(self.workspace)
        self.assertIn("selenium", res["detected_stacks"])
        self.assertGreaterEqual(res["confidence"]["selenium"], 0.85)

    def test_detect_mobile_appium_stack(self):
        caps_path = os.path.join(self.workspace, "caps.json")
        with open(caps_path, "w", encoding="utf-8") as f:
            f.write('{"platformName": "Android"}')

        res = detect_workspace_stacks(self.workspace)
        self.assertIn("mobile", res["detected_stacks"])
        self.assertGreaterEqual(res["confidence"]["mobile"], 0.90)

    def test_detect_performance_stack(self):
        jmx_path = os.path.join(self.workspace, "load_test.jmx")
        with open(jmx_path, "w", encoding="utf-8") as f:
            f.write("<jmeterTestPlan></jmeterTestPlan>")

        res = detect_workspace_stacks(self.workspace)
        self.assertIn("performance", res["detected_stacks"])

    def test_detect_monorepo_subpackages(self):
        # Create pnpm-workspace.yaml at root
        pnpm_cfg = os.path.join(self.workspace, "pnpm-workspace.yaml")
        with open(pnpm_cfg, "w", encoding="utf-8") as f:
            f.write("packages:\n  - 'packages/*'\n")

        # Create packages/frontend with playwright
        fe_dir = os.path.join(self.workspace, "packages", "frontend")
        os.makedirs(fe_dir, exist_ok=True)
        with open(os.path.join(fe_dir, "playwright.config.ts"), "w", encoding="utf-8") as f:
            f.write("export default {};")

        # Create packages/api with fastapi/requests
        api_dir = os.path.join(self.workspace, "packages", "backend")
        os.makedirs(api_dir, exist_ok=True)
        with open(os.path.join(api_dir, "requirements.txt"), "w", encoding="utf-8") as f:
            f.write("fastapi>=0.100.0\nrequests>=2.31.0\n")

        res = detect_workspace_stacks(self.workspace)
        self.assertTrue(res["is_monorepo"])
        self.assertIn("playwright", res["detected_stacks"])
        self.assertIn("api", res["detected_stacks"])

    def test_unclassified_workspace_truth_anchor(self):
        # Empty workspace should NOT claim fake 86% savings
        routed = route_rules(self.workspace)
        self.assertEqual(routed["status"], "UNCLASSIFIED_WORKSPACE")
        self.assertEqual(routed["token_metrics"]["tokens_saved"], 0)
        self.assertEqual(routed["token_metrics"]["reduction_percentage"], 0.0)

    def test_classified_token_hydration_metrics(self):
        # Mock Playwright config
        config_path = os.path.join(self.workspace, "playwright.config.ts")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("export default {};")

        routed = route_rules(self.workspace)
        self.assertEqual(routed["status"], "CLASSIFIED")
        self.assertIn("playwright", routed["detected_stacks"])
        self.assertIn("hydration_contracts", routed)

        cat = routed["hydration_contracts"]["catalog_summary"]
        hyd = routed["hydration_contracts"]["full_hydration"]
        rf = routed["hydration_contracts"]["retrieval_footprint"]

        # Invariant: Baseline must be strictly >= routed payload
        self.assertGreaterEqual(cat["baseline_tokens"], cat["routed_tokens"])
        self.assertGreaterEqual(hyd["baseline_tokens"], hyd["routed_tokens"])
        self.assertGreaterEqual(rf["full_catalog_bytes"], rf["routed_catalog_bytes"])

        # Ground-truth mathematical savings
        self.assertEqual(cat["tokens_saved"], cat["baseline_tokens"] - cat["routed_tokens"])
        self.assertEqual(hyd["tokens_saved"], hyd["baseline_tokens"] - hyd["routed_tokens"])
        self.assertGreater(hyd["reduction_pct"], 60.0)
        self.assertGreater(cat["reduction_pct"], 50.0)

    def test_full_baseline_enumerates_all_53_skills(self):
        from tools.core.token_estimator import get_full_unrouted_baseline, get_estimator_info
        from tools.rules_router import _find_repo_root

        repo_root = _find_repo_root()
        b = get_full_unrouted_baseline(repo_root)

        # Truth Anchor: verify exact physical file counts in hub
        self.assertEqual(b["skill_count"], 53, "Must discover and count all 53 skills")
        self.assertEqual(b["rule_count"], 13, "Must discover and count all 13 rules")
        self.assertGreater(b["total_full_baseline"], 50000, "Full baseline must reflect real bodies")
        self.assertGreater(b["total_full_baseline"], b["total_summary_baseline"])

        info = get_estimator_info()
        self.assertEqual(info["encoding"], "cl100k_base")

    def test_format_routing_report_json_and_text(self):
        routed = route_rules(self.workspace)
        text_rep = format_routing_report(routed, fmt="text")
        self.assertIn("SYNAPSE HUB — PROGRESSIVE RULES ROUTER", text_rep)

        json_rep = format_routing_report(routed, fmt="json")
        parsed = json.loads(json_rep)
        self.assertEqual(parsed["workspace"], os.path.abspath(self.workspace))


if __name__ == "__main__":
    unittest.main()
