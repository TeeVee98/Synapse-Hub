#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_level4_adaptive.py — Unit tests for Level 4 Adaptive Hub Tools
------------------------------------------------------------------------
Validates:
  1. rule_harvester.py: harvest logic, shortcut detection, rule recommendation synthesis
  2. context_slicer.py: AST file classification, micro-context generation, diff slicing
"""

import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import rule_harvester
import context_slicer


class TestLevel4Adaptive(unittest.TestCase):

    def test_rule_harvester_basic(self):
        harvester = rule_harvester.DynamicRuleHarvester(repo_root=REPO_ROOT)
        report = harvester.generate_report()
        self.assertIn("timestamp", report)
        self.assertEqual(report["level"], "LEVEL_4_ADAPTIVE")
        self.assertIsInstance(report["adaptive_suggestions"], list)
        self.assertGreater(len(report["adaptive_suggestions"]), 0)

    def test_rule_harvester_shortcuts(self):
        harvester = rule_harvester.DynamicRuleHarvester(repo_root=REPO_ROOT)
        shortcuts = harvester.harvest_shortcut_debt()
        self.assertIsInstance(shortcuts, list)

    def test_rule_harvester_lessons_learned(self):
        harvester = rule_harvester.DynamicRuleHarvester(repo_root=REPO_ROOT)
        lessons = harvester.harvest_lessons_learned()
        self.assertIsInstance(lessons, list)

    def test_rule_harvester_apply_dry_run(self):
        harvester = rule_harvester.DynamicRuleHarvester(repo_root=REPO_ROOT)
        res = harvester.apply_rules(suggestions=[{
            "type": "TEST_ADAPTIVE_RULE",
            "trigger": "Unit Test Validation",
            "rule": "Verify adaptive rule application pipeline."
        }])
        self.assertTrue(res)

    def test_context_slicer_classification(self):
        self.assertEqual(context_slicer.ContextSlicer.classify_file("pages/LoginPage.ts"), "PAGE_CLASS")
        self.assertEqual(context_slicer.ContextSlicer.classify_file("tests/e2e/test_auth.spec.ts"), "TEST_SCRIPT")
        self.assertEqual(context_slicer.ContextSlicer.classify_file("api/v1/users_contract.py"), "API_CONTRACT")
        self.assertEqual(context_slicer.ContextSlicer.classify_file("tools/util.py"), "GENERAL_CODE")

    def test_context_slicer_output(self):
        ctx_page = context_slicer.ContextSlicer.slice_context("pages/DashboardPage.ts")
        self.assertIn("Clean POM Page Class", ctx_page)
        self.assertIn("6-Tier Locator Hierarchy", ctx_page)

        ctx_test = context_slicer.ContextSlicer.slice_context("tests/login.spec.ts")
        self.assertIn("Clean Test Script", ctx_test)
        self.assertIn("Truth Anchor", ctx_test)

    def test_context_slicer_git_diff(self):
        res = context_slicer.ContextSlicer.slice_git_diff(repo_root=REPO_ROOT)
        self.assertIsInstance(res, dict)


if __name__ == "__main__":
    unittest.main()
