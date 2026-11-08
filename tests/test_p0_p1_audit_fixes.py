#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tests/test_p0_p1_audit_fixes.py
--------------------------------
Comprehensive unit tests verifying P0/P1 audit fixes:
1. auto_heal.py dual data contract schema support and location extraction.
2. pinpoint_failure.py multi-language stack trace extraction (Python, TS, JS, Groovy).
3. ui_server.py target directory scope isolation.
4. setup_project.py default .synapse.json auto-generation.
5. omni_emitter.py Clean POM compliance (zero findTestObject in Scripts).
6. omni_parser.py identifier sanitization (e.g. auth.spec.ts -> AuthPage).
7. generate_tc_from_story.py login intent detection (no duplicate imports or modal opens).
8. infer_linter.py report scoping to target project reports folder.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import auto_heal
import pinpoint_failure
import ui_server
import setup_project
import omni_emitter
import omni_parser
import generate_tc_from_story
import infer_linter
from universal_ir import ProjectIR, PageClassIR, TestCaseIR, StepIR, ActionType


class TestP0P1AuditFixes(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 1. auto_heal & pinpoint_failure
    # -------------------------------------------------------------------------
    def test_auto_heal_dual_schema_contract(self):
        """Verifies auto_heal.py correctly handles both pinpoint_failure schema and legacy schema."""
        # Schema A (from pinpoint_failure: tc, reason, failed_at)
        failure_a = {
            "tc": "TC_01_AuthFailure",
            "reason": "Element #submit not clickable",
            "failed_at": ["src/pages/LoginPage.ts:42"]
        }
        plan_a = auto_heal.diagnose_and_plan_heal(failure_info=failure_a)
        self.assertEqual(plan_a["test_name"], "TC_01_AuthFailure")
        self.assertEqual(plan_a["failing_file"], "src/pages/LoginPage.ts")
        self.assertEqual(str(plan_a["line"]), "42")
        self.assertIn("Element #submit not clickable", plan_a["error_signature"])

        # Schema B (legacy / emitter format: name, message, file, line)
        failure_b = {
            "name": "TC_02_LegacyFormat",
            "message": "Timed out waiting for element",
            "file": "tests/test_cart.py",
            "line": 88
        }
        plan_b = auto_heal.diagnose_and_plan_heal(failure_info=failure_b)
        self.assertEqual(plan_b["test_name"], "TC_02_LegacyFormat")
        self.assertEqual(plan_b["failing_file"], "tests/test_cart.py")
        self.assertEqual(plan_b["line"], 88)
        self.assertIn("Timed out waiting for element", plan_b["error_signature"])

    def test_pinpoint_failure_multilanguage_stacktraces(self):
        """Verifies multi-language stack trace extraction across Python, TS, JS, and Groovy."""
        # 1. Playwright / TS stack frame
        ts_trace = """Error: locator.click: Timeout 5000ms exceeded.
Call log:
  - waiting for locator('#btn-login')
    at LoginPage.clickLogin (/workspace/src/pages/LoginPage.ts:55:12)
    at /workspace/tests/auth.spec.ts:24:9"""
        locs_ts = pinpoint_failure.extract_failed_locations(ts_trace)
        self.assertTrue(any("LoginPage.ts:55" in loc for loc in locs_ts))

        # 2. Python traceback
        py_trace = """Traceback (most recent call last):
  File "/workspace/tests/test_checkout.py", line 42, in test_payment
    assert payment.is_success() is True
AssertionError"""
        locs_py = pinpoint_failure.extract_failed_locations(py_trace)
        self.assertTrue(any("test_checkout.py:42" in loc for loc in locs_py))

        # 3. Groovy Enterprise Katalon line
        groovy_trace = "Stacktrace:\nEnterprise.pages.DashboardPage.groovy:99\nScript12345.groovy:15"
        locs_gr = pinpoint_failure.extract_failed_locations(groovy_trace)
        self.assertIn("Enterprise.pages.DashboardPage.groovy:99", locs_gr)

    # -------------------------------------------------------------------------
    # 2. ui_server target directory scope isolation
    # -------------------------------------------------------------------------
    def test_ui_server_scope_isolation(self):
        """Verifies ui_server scopes execution commands and working directory to target project."""
        dummy_project = os.path.join(self.temp_dir, "spoke_app")
        os.makedirs(dummy_project, exist_ok=True)

        verify_cmd = ui_server.get_command_for_target("verify", dummy_project)
        self.assertIn("--mode", verify_cmd)
        self.assertIn("target", verify_cmd)
        self.assertIn(dummy_project, verify_cmd)

        lint_cmd = ui_server.get_command_for_target("lint", dummy_project)
        self.assertIn(dummy_project, lint_cmd)

        # Hub mode fallback
        hub_verify = ui_server.get_command_for_target("verify", REPO_ROOT)
        self.assertIn("hub", hub_verify)

    # -------------------------------------------------------------------------
    # 3. setup_project auto-generates .synapse.json
    # -------------------------------------------------------------------------
    def test_setup_project_auto_generates_synapse_config(self):
        """Verifies setup_project creates default .synapse.json when missing in Spoke."""
        spoke_dir = os.path.join(self.temp_dir, "new_spoke_project")
        os.makedirs(spoke_dir, exist_ok=True)
        config_path = os.path.join(spoke_dir, ".synapse.json")

        self.assertFalse(os.path.exists(config_path))
        result = setup_project.ensure_synapse_config(spoke_dir)
        self.assertTrue(result)
        self.assertTrue(os.path.isfile(config_path))

        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertIn("project", cfg)
        self.assertEqual(cfg["project"]["name"], "new_spoke_project")

    # -------------------------------------------------------------------------
    # 4. omni_emitter Clean POM compliance (zero findTestObject)
    # -------------------------------------------------------------------------
    def test_omni_emitter_katalon_clean_pom_no_findtestobject(self):
        """Verifies omni_emitter Katalon generator produces clean Page Class assertions without findTestObject."""
        p_ir = ProjectIR(name="AuthModule", source_language="groovy", source_framework="katalon")
        page = PageClassIR(name="LoginPage", base_class="BasePage")
        p_ir.pages.append(page)

        step_goto = StepIR(action=ActionType.GOTO, value="https://example.com")
        step_assert = StepIR(action=ActionType.ASSERT, target="isLoaded")
        tc = TestCaseIR(id="TC_01", title="Login Flow", steps=[step_goto, step_assert])
        p_ir.test_cases.append(tc)

        files = omni_emitter.OmniEmitter.emit(p_ir, "katalon-groovy")
        script_key = [k for k in files if k.startswith("Scripts/")][0]
        script_code = files[script_key]

        # Must not contain raw findTestObject in test script
        self.assertNotIn("findTestObject", script_code)
        self.assertIn("assert LoginPage.isPageLoaded()", script_code)

    # -------------------------------------------------------------------------
    # 5. omni_parser identifier sanitization
    # -------------------------------------------------------------------------
    def test_omni_parser_sanitizes_spec_class_name(self):
        """Verifies omni_parser sanitizes file stems like auth.spec.ts into valid identifier AuthPage."""
        ts_code = """import { test, expect } from '@playwright/test';
test('basic test', async ({ page }) => {
  await page.goto('https://example.com');
});"""
        p_ir = omni_parser.OmniParser.parse_code(ts_code, "auth.spec.ts")
        self.assertEqual(p_ir.name, "Auth")
        self.assertEqual(len(p_ir.pages), 1)
        self.assertEqual(p_ir.pages[0].name, "AuthPage")
        self.assertNotIn(".", p_ir.pages[0].name)

    # -------------------------------------------------------------------------
    # 6. generate_tc_from_story login story intent
    # -------------------------------------------------------------------------
    def test_generate_tc_from_story_login_intent(self):
        """Verifies login story intent avoids duplicate imports, modal opens, and undefined teardown."""
        story = "Người dùng đăng nhập thành công vào hệ thống với thông tin hợp lệ"
        script = generate_tc_from_story.generate_script(story, module_name="LoginPage", tc_name="TC_LoginSuccess")

        # Must only import LoginPage once
        self.assertEqual(script.count("import pages.LoginPage"), 1)
        # Must not contain openCreateModal
        self.assertNotIn("openCreateModal", script)
        self.assertNotIn("fillCreateForm", script)
        # Must contain login authentication calls
        self.assertIn("LoginPage.enterCredentials", script)
        self.assertIn("LoginPage.submitLogin", script)
        self.assertIn("LoginPage.verifyLoginSuccess", script)
        # Must not contain teardown(uniqueCode) because uniqueCode is not defined in login
        self.assertNotIn("uniqueCode", script)

    # -------------------------------------------------------------------------
    # 7. infer_linter report saved in target project
    # -------------------------------------------------------------------------
    def test_infer_linter_target_report_scoping(self):
        """Verifies infer_linter saves reports in target project reports folder when target is specified."""
        target_dir = os.path.join(self.temp_dir, "spoke_target")
        scripts_dir = os.path.join(target_dir, "Scripts")
        os.makedirs(scripts_dir, exist_ok=True)

        clean_script = os.path.join(scripts_dir, "TC_Sample.groovy")
        with open(clean_script, "w", encoding="utf-8") as f:
            f.write("import pages.BasePage\nassert BasePage.isLoaded()\n")

        # Run infer_linter on target_dir
        exit_code = infer_linter.run_infer_linter(target_dir=target_dir, strict=False)
        self.assertEqual(exit_code, 0)

        # Expected report must exist in target_dir/reports
        target_report = os.path.join(target_dir, "reports", "infer_linter_report.json")
        self.assertTrue(os.path.isfile(target_report), f"Target report missing at {target_report}")

    def test_infer_linter_single_script_scoping(self):
        """Verifies linting a single script file in a Spoke project saves report to project reports/ folder."""
        target_dir = os.path.join(self.temp_dir, "single_spoke")
        scripts_dir = os.path.join(target_dir, "Scripts")
        os.makedirs(scripts_dir, exist_ok=True)
        script_file = os.path.join(scripts_dir, "TC_01.groovy")
        with open(script_file, "w", encoding="utf-8") as f:
            f.write("import pages.BasePage\nassert BasePage.isLoaded()\n")

        infer_linter.run_infer_linter(target_dir=script_file, strict=False)
        target_report = os.path.join(target_dir, "reports", "infer_linter_report.json")
        self.assertTrue(os.path.isfile(target_report))

    # -------------------------------------------------------------------------
    # 8. Edge cases: Spaces in paths, empty time, leading digits, and UI server reports
    # -------------------------------------------------------------------------
    def test_pinpoint_failure_paths_with_spaces_and_windows_drives(self):
        """Verifies extract_failed_locations parses file paths with spaces and Windows drives."""
        trace = """Error: Timeout
    at LoginPage.click (/Users/phungcao/Downloads/Agent Skill/tests/login.spec.ts:42:10)
    at foo (C:\\Users\\User Name\\project\\tests\\checkout.spec.ts:15:5)
    at /Users/phungcao/Downloads/Agent Skill/tests/test_ui.tsx:20:1
  File "/Users/phungcao/Downloads/Agent Skill/tests/test_foo.py", line 99"""
        locs = pinpoint_failure.extract_failed_locations(trace)
        self.assertTrue(any("Agent Skill/tests/login.spec.ts:42" in loc for loc in locs))
        self.assertTrue(any("User Name\\project\\tests\\checkout.spec.ts:15" in loc for loc in locs))
        self.assertTrue(any("Agent Skill/tests/test_ui.tsx:20" in loc for loc in locs))
        self.assertTrue(any("Agent Skill/tests/test_foo.py:99" in loc for loc in locs))

    def test_pinpoint_failure_empty_time_and_corrupt_xml(self):
        """Verifies parse_failures handles empty time and corrupt XML gracefully without crashing."""
        xml_path = os.path.join(self.temp_dir, "empty_time.xml")
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write("""<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="Suite">
    <testcase name="TC_EmptyTime" time="">
      <failure message="Something went wrong">at LoginPage.click (/app/test.ts:10)</failure>
    </testcase>
  </testsuite>
</testsuites>""")
        failures = pinpoint_failure.parse_failures(xml_path)
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["tc"], "TC_EmptyTime")
        self.assertEqual(failures[0]["time"], "0.0s")

        # Corrupt XML handling
        corrupt_path = os.path.join(self.temp_dir, "corrupt.xml")
        with open(corrupt_path, "w", encoding="utf-8") as f:
            f.write("<not closed")
        corrupt_res = pinpoint_failure.parse_failures(corrupt_path)
        self.assertEqual(corrupt_res, [])

    def test_omni_parser_leading_digits_and_e2e_suffixes(self):
        """Verifies omni_parser handles files starting with digits and e2e-spec suffixes without syntax errors."""
        ts_code = "import { test } from '@playwright/test'; test('x', () => {});"
        # 1. Leading digits
        p1 = omni_parser.OmniParser.parse_code(ts_code, "01_login.spec.ts")
        self.assertFalse(p1.pages[0].name[0].isdigit(), f"Page name must not start with digit: {p1.pages[0].name}")
        self.assertTrue(p1.pages[0].name.isidentifier(), f"Page name must be valid identifier: {p1.pages[0].name}")

        # 2. e2e-spec suffix
        p2 = omni_parser.OmniParser.parse_code(ts_code, "cart.e2e-spec.ts")
        self.assertEqual(p2.pages[0].name, "CartPage")

    def test_ui_server_serves_target_reports(self):
        """Verifies UI server serves static reports directly from target project reports folder."""
        import urllib.request
        from ui_server import JOB_MANAGER, SynapseUiHandler, ThreadingHTTPServer

        target_proj = os.path.join(self.temp_dir, "target_ui_proj")
        reports_dir = os.path.join(target_proj, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        report_file = os.path.join(reports_dir, "target_report.html")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("<h1>Target Project Custom Report</h1>")

        old_target = JOB_MANAGER.target_dir
        JOB_MANAGER.target_dir = target_proj
        server = ThreadingHTTPServer(("127.0.0.1", 0), SynapseUiHandler)
        port = server.server_address[1]
        import threading
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        try:
            req = urllib.request.urlopen(f"http://127.0.0.1:{port}/reports/target_report.html")
            body = req.read().decode("utf-8")
            self.assertEqual(req.status, 200)
            self.assertIn("Target Project Custom Report", body)
        finally:
            server.shutdown()
            server.server_close()
            JOB_MANAGER.target_dir = old_target


if __name__ == "__main__":
    unittest.main()
