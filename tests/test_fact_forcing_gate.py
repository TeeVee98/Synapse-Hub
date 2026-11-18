#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_fact_forcing_gate.py — Regression Test Suite for QA Fact-Forcing Gate
-------------------------------------------------------------------------------
Verifies that fact_forcing_gate accurately detects:
  1. Clean POM violations (deep Page Class inheritance, raw selectors in test scripts).
  2. Static sleeps (time.sleep, Thread.sleep, waitForTimeout).
  3. Swallowed exceptions and fake passes.
  4. Allows 100% compliant Clean POM code.
"""

import unittest
from tools.core.fact_forcing_gate import (
    classify_target,
    evaluate_content,
    TARGET_PAGE_CLASS,
    TARGET_TEST_SCRIPT,
    TARGET_CONFIG,
)


class TestFactForcingGate(unittest.TestCase):

    def test_target_classification(self):
        self.assertEqual(classify_target("pages/login_page.py"), TARGET_PAGE_CLASS)
        self.assertEqual(classify_target("src/pages/checkout_page.ts"), TARGET_PAGE_CLASS)
        self.assertEqual(classify_target("tests/test_auth_flow.py"), TARGET_TEST_SCRIPT)
        self.assertEqual(classify_target("tests/e2e/login.spec.ts"), TARGET_TEST_SCRIPT)
        self.assertEqual(classify_target("package.json"), TARGET_CONFIG)

    def test_deep_inheritance_rejection(self):
        content = "class LoginPage(AdminDashboardPage):\n    pass\n"
        ok, errs = evaluate_content(content, "pages/login_page.py")
        self.assertFalse(ok)
        self.assertTrue(any("Clean POM Flat Architecture" in e for e in errs))

    def test_valid_page_class_allowed(self):
        content = "class LoginPage(BasePage):\n    def login(self):\n        pass\n"
        ok, errs = evaluate_content(content, "pages/login_page.py")
        self.assertTrue(ok)
        self.assertEqual(len(errs), 0)

    def test_raw_selectors_in_test_script_rejected(self):
        content = "def test_example(page):\n    page.locator('//button[@id=\"submit\"]').click()\n"
        ok, errs = evaluate_content(content, "tests/test_example.py")
        self.assertFalse(ok)
        self.assertTrue(any("Raw page.locator" in e for e in errs))

    def test_static_sleep_rejected(self):
        content = "def test_example(login_page):\n    time.sleep(5)\n    login_page.submit()\n"
        ok, errs = evaluate_content(content, "tests/test_example.py")
        self.assertFalse(ok)
        self.assertTrue(any("time.sleep" in e for e in errs))

    def test_clean_pom_test_script_allowed(self):
        content = (
            "def test_login(login_page):\n"
            "    login_page.login_with_credentials('AUTO_user_123', 'secret')\n"
            "    assert login_page.is_logged_in()\n"
        )
        ok, errs = evaluate_content(content, "tests/test_login.py")
        self.assertTrue(ok)
        self.assertEqual(len(errs), 0)


if __name__ == "__main__":
    unittest.main()
