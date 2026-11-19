#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for Gate 3: Clean POM & Flat Architecture Sentinel."""

import os
import shutil
import tempfile
import unittest

from tools.core.gates.gate_03_clean_pom import Gate03CleanPOM, gate_3_clean_pom


class TestGate03CleanPOM(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="synapse_test_gate3_")
        self.tests_dir = os.path.join(self.temp_dir, "tests")
        os.makedirs(self.tests_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_clean_pom_script_passes(self):
        script_path = os.path.join(self.tests_dir, "login_test.spec.ts")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write("""
            test("user can log in", async ({ page }) => {
                const loginPage = new LoginPage(page);
                await loginPage.navigate();
                await loginPage.loginWithCredentials("admin", "secret");
            });
            """)

        self.assertTrue(gate_3_clean_pom(self.temp_dir, mode="TARGET"))
        gate = Gate03CleanPOM()
        res = gate.execute(self.temp_dir, mode="TARGET")
        self.assertTrue(res.passed)

    def test_raw_xpath_in_script_fails(self):
        script_path = os.path.join(self.tests_dir, "dirty_test.spec.ts")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write("""
            test("dirty test with xpath", async ({ page }) => {
                await page.locator("//button[@id='submit']").click();
            });
            """)

        self.assertFalse(gate_3_clean_pom(self.temp_dir, mode="TARGET"))
        gate = Gate03CleanPOM()
        res = gate.execute(self.temp_dir, mode="TARGET")
        self.assertFalse(res.passed)

    def test_find_test_object_fails(self):
        script_path = os.path.join(self.tests_dir, "dirty_katalon.groovy")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write("""
            WebUI.click(findTestObject('Object Repository/btn_Login'))
            """)

        self.assertFalse(gate_3_clean_pom(self.temp_dir, mode="TARGET"))


if __name__ == "__main__":
    unittest.main()
