#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Golden Unit Tests for tools/spec_drift_sentinel.py (Spec-to-Code Drift Sentinel)
--------------------------------------------------------------------------------
Validates:
  1. Spec criteria extraction (Gherkin, Markdown checklists, bullet requirements)
  2. Test code assertion & action extraction
  3. CamelCase normalization and stemming tokenization
  4. Deficit Drift & Scope Drift calculation
  5. Alignment scoring and report generation
"""

import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import spec_drift_sentinel as sds


class TestSpecDriftSentinel(unittest.TestCase):

    def setUp(self):
        self.sample_spec = """
# Feature: User Authentication & Profile
Customers log in and update their personal account profile.

## Acceptance Criteria:
- [ ] User enters valid email and password to log in
- [ ] System must display welcome dashboard with username
- [ ] User navigates to profile settings and updates phone number
- [ ] Then the system displays notification "Profile Updated Successfully"

### Security Requirements:
1. System must reject invalid password with error message
"""

        self.sample_code = """
import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { ProfilePage } from '../pages/ProfilePage';

test('User logs in and updates profile phone', async ({ page }) => {
    const loginPage = new LoginPage(page);
    const profilePage = new ProfilePage(page);

    await loginPage.navigate();
    await loginPage.login('user@example.com', 'ValidPass123');
    await expect(page.locator('.welcome-banner')).toContainText('welcome dashboard');

    await profilePage.openSettings();
    await profilePage.updatePhone('0901234567');
    await expect(page.locator('.toast')).toHaveText('Profile Updated Successfully');
});
"""

    def test_extract_spec_criteria_checklist(self):
        criteria = sds.extract_spec_criteria(self.sample_spec)
        self.assertGreaterEqual(len(criteria), 4)
        checklist_items = [c for c in criteria if c["type"] == "checklist"]
        self.assertTrue(any("email and password" in c["text"] for c in checklist_items))

    def test_extract_spec_criteria_gherkin(self):
        gherkin_text = """
Feature: Payment Processing
  Scenario: Checkout with credit card
    When user submits payment
    Then the response status should be 200
"""
        criteria = sds.extract_spec_criteria(gherkin_text)
        scenarios = [c for c in criteria if c["type"] == "scenario"]
        self.assertEqual(len(scenarios), 1)
        self.assertEqual(scenarios[0]["text"], "Checkout with credit card")

    def test_extract_code_tokens_and_assertions(self):
        assertions, actions = sds.extract_code_tokens_and_assertions(self.sample_code)
        self.assertGreaterEqual(len(assertions), 2)
        self.assertTrue(any("toContainText" in a or "expect" in a for a in assertions))
        self.assertTrue(any("loginPage.login" in a or "profilePage.openSettings" in a for a in actions))

    def test_split_camel_case_and_stem(self):
        expanded = sds.split_camel_case("LoginPage")
        self.assertEqual(expanded, "Login Page")

        self.assertEqual(sds.normalize_stem("updating"), "updat")
        self.assertEqual(sds.normalize_stem("categories"), "category")
        self.assertEqual(sds.normalize_stem("validated"), "validat")

    def test_tokenize_text(self):
        tokens = sds.tokenize_text("The user should enter ValidEmail and submitForm")
        self.assertIn("valid", tokens)
        self.assertIn("email", tokens)
        self.assertIn("submit", tokens)
        self.assertIn("form", tokens)
        self.assertNotIn("the", tokens)

    def test_compute_drift_aligned(self):
        criteria = sds.extract_spec_criteria(self.sample_spec)
        drift_result = sds.compute_drift(criteria, [("test_auth.ts", self.sample_code)])

        self.assertIn("alignment_score", drift_result)
        self.assertIn("covered_criteria", drift_result)
        self.assertIn("deficit_drift", drift_result)
        self.assertGreater(drift_result["alignment_score"], 40.0)

    def test_compute_drift_deficit_detected(self):
        unimplemented_spec = """
# Feature: Order Refund
- [ ] User requests full refund for cancelled order
- [ ] System calculates tax adjustment and issues bank refund receipt
"""
        criteria = sds.extract_spec_criteria(unimplemented_spec)
        drift_result = sds.compute_drift(criteria, [("test_auth.ts", self.sample_code)])

        self.assertGreater(len(drift_result["deficit_drift"]), 0)
        self.assertLess(drift_result["alignment_score"], 30.0)

    def test_generate_markdown_report(self):
        criteria = sds.extract_spec_criteria(self.sample_spec)
        drift_result = sds.compute_drift(criteria, [("test_auth.ts", self.sample_code)])
        md = sds.generate_markdown_report(drift_result, "spec.md", ["test_auth.ts"])

        self.assertIn("SPEC-TO-CODE DRIFT REPORT", md)
        self.assertIn("Alignment Score", md)


if __name__ == "__main__":
    unittest.main()
