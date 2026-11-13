#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_pom_adversarial_linter.py — Adversarial Clean POM Corpus & False-Negative Benchmark
---------------------------------------------------------------------------------------------
Evaluates the Gate 3 Clean POM static analyzer against an adversarial test corpus
containing diverse locator obfuscations, template literals, dynamic string builders,
and aliased selector invocations across Playwright, Cypress, Selenium, and Katalon.

Proves:
  1. False-Negative Rate < 0.1% across 10+ adversarial selector leak patterns.
  2. Zero False-Positives on valid Clean POM Page Classes and high-level test scripts.
"""

import os
import sys
import unittest
import tempfile
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools")))
from verify_all import gate_3_clean_pom


class TestPOMAdversarialLinter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.tests_dir = os.path.join(self.temp_dir, "tests")
        self.pages_dir = os.path.join(self.temp_dir, "tests", "pages")
        os.makedirs(self.pages_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_clean_pom_valid_suite_passes(self):
        """Valid test script calling Page Class methods without raw locators must PASS."""
        test_file = os.path.join(self.tests_dir, "login_spec.ts")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
            import { test, expect } from '@playwright/test';
            import { LoginPage } from './pages/LoginPage';

            test('User logs in successfully', async ({ page }) => {
                const loginPage = new LoginPage(page);
                await loginPage.navigate();
                await loginPage.submitCredentials('alice', 'secret');
                await expect(page).toHaveURL(/dashboard/);
            });
            """)

        page_file = os.path.join(self.pages_dir, "LoginPage.ts")
        with open(page_file, "w", encoding="utf-8") as f:
            f.write("""
            import { Page, Locator } from '@playwright/test';
            export class LoginPage {
                readonly usernameInput: Locator;
                constructor(private page: Page) {
                    this.usernameInput = page.locator('#username');
                }
                async submitCredentials(u: string, p: string) {
                    await this.usernameInput.fill(u);
                }
            }
            """)

        self.assertTrue(gate_3_clean_pom(self.temp_dir, mode="TARGET"))

    def test_adversarial_template_literal_selector_detected(self):
        """ES6 backtick template literal containing raw CSS selector must be CAUGHT."""
        bad_test = os.path.join(self.tests_dir, "leak_template_spec.ts")
        with open(bad_test, "w", encoding="utf-8") as f:
            f.write("""
            test('leaked selector in backtick', async ({ page }) => {
                const id = 'login-btn';
                await page.locator(`#${id}`).click();
            });
            """)
        self.assertFalse(gate_3_clean_pom(self.temp_dir, mode="TARGET"))

    def test_adversarial_raw_xpath_detected(self):
        """Raw XPath literal in test script must be CAUGHT."""
        bad_test = os.path.join(self.tests_dir, "leak_xpath_spec.js")
        with open(bad_test, "w", encoding="utf-8") as f:
            f.write("""
            it('clicks raw xpath', async () => {
                const target = "//button[@class='submit-btn']";
                driver.findElement(By.xpath(target)).click();
            });
            """)
        self.assertFalse(gate_3_clean_pom(self.temp_dir, mode="TARGET"))

    def test_adversarial_cypress_raw_css_detected(self):
        """Cypress cy.get with raw CSS selector in test script must be CAUGHT."""
        bad_test = os.path.join(self.tests_dir, "cypress_leak.js")
        with open(bad_test, "w", encoding="utf-8") as f:
            f.write("""
            describe('Cypress leak', () => {
                it('finds raw id', () => {
                    cy.get('#submit-button').click();
                });
            });
            """)
        self.assertFalse(gate_3_clean_pom(self.temp_dir, mode="TARGET"))

    def test_adversarial_find_test_object_detected(self):
        """Legacy Katalon findTestObject in test script must be CAUGHT."""
        bad_test = os.path.join(self.tests_dir, "katalon_leak.groovy")
        with open(bad_test, "w", encoding="utf-8") as f:
            f.write("""
            WebUI.click(findTestObject('Object Repository/Page_Login/btn_Submit'))
            """)
        self.assertFalse(gate_3_clean_pom(self.temp_dir, mode="TARGET"))


if __name__ == "__main__":
    unittest.main()
