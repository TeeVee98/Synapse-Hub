#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

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
from tools.contrib import ui_server
import setup_project
import omni_emitter
import omni_parser
from tools.contrib import generate_tc_from_story
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
        self.assertFalse(plan_a["macro_cache_match"])
        self.assertIsNone(plan_a["macro_repair"])

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

    def test_auto_heal_tier10_macro_cache_syntax_and_schema_drift(self):
        """Verifies diagnose_and_plan_heal checks Tier 10 MacroCacheEngine on SyntaxError and schema drift."""
        # 1. Empty / no failure preserves NO_FAILURE_DETECTED
        empty_plan = auto_heal.diagnose_and_plan_heal(target_dir=self.temp_dir)
        self.assertEqual(empty_plan, {"status": "NO_FAILURE_DETECTED"})

        # 2. SyntaxError failure uses zero-token MacroCacheEngine repair before reflexion escalation
        broken_file = os.path.join(self.temp_dir, "broken_sample.py")
        broken_code = "def check_login_ready()\n    return True\n"
        with open(broken_file, "w", encoding="utf-8") as f:
            f.write(broken_code)

        syntax_failure = {
            "tc": "TC_Syntax_BrokenHeader",
            "type": "SyntaxError",
            "reason": "expected ':' (SyntaxError)",
            "file": broken_file,
            "line": 1,
        }
        syntax_plan = auto_heal.diagnose_and_plan_heal(target_dir=self.temp_dir, failure_info=syntax_failure)
        self.assertEqual(syntax_plan["status"], "HEALING_PLAN_READY")
        self.assertTrue(syntax_plan["macro_cache_match"])
        self.assertIsInstance(syntax_plan["macro_repair"], dict)
        self.assertTrue(syntax_plan["macro_repair"]["repaired"])
        self.assertEqual(syntax_plan["macro_repair"]["tokens_consumed"], 0)
        self.assertIn("def check_login_ready():", syntax_plan["macro_repair"]["output"])
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, ".synapse", "macro_cache.db")))

        # Inline context takes precedence even when failing_file points to another file
        inline_syntax = {
            "tc": "TC_Syntax_Inline",
            "category": "syntax",
            "reason": "missing colon",
            "context": "def inline_fn()\n    return 1\n",
            "file": broken_file,
            "line": "?",
        }
        inline_plan = auto_heal.diagnose_and_plan_heal(target_dir=self.temp_dir, failure_info=inline_syntax)
        self.assertTrue(inline_plan["macro_cache_match"])
        self.assertIsNone(inline_plan["verbal_reflection"])
        self.assertIn("def inline_fn():", inline_plan["macro_repair"]["output"])
        self.assertNotIn("check_login_ready", inline_plan["macro_repair"]["output"])
        for required_key in (
            "test_name",
            "failing_file",
            "line",
            "error_signature",
            "cache_match",
            "heuristic_match",
            "recommended_patch",
            "verbal_reflection",
            "episodic_lessons",
            "aom_snapshot_captured",
        ):
            self.assertIn(required_key, syntax_plan)

        # 3. Schema-drift failure triggers MacroCacheEngine zero-token repair
        payload = {"filepath": "config/settings.json", "mode": "strict"}
        drift_failure = {
            "tc": "TC_SchemaDrift_ReadFile",
            "category": "schema_drift",
            "tool_name": "read_file",
            "reason": "SchemaDriftError: unexpected param 'filepath', expected 'file_path'",
            "given_args": payload,
            "expected_schema": {"properties": {"file_path": {"type": "string"}, "mode": {"type": "string"}}},
            "file": "tools/runtime/meta_tool_engine.py",
            "line": 150,
        }
        drift_plan = auto_heal.diagnose_and_plan_heal(target_dir=self.temp_dir, failure_info=drift_failure)
        self.assertEqual(drift_plan["status"], "HEALING_PLAN_READY")
        self.assertTrue(drift_plan["macro_cache_match"])
        self.assertIsInstance(drift_plan["macro_repair"], dict)
        self.assertTrue(drift_plan["macro_repair"]["repaired"])
        self.assertEqual(drift_plan["macro_repair"]["tokens_consumed"], 0)
        self.assertEqual(drift_plan["macro_repair"]["output"]["file_path"], "config/settings.json")
        self.assertNotIn("filepath", drift_plan["macro_repair"]["output"])

        # 4. MacroCacheEngine exception degrades gracefully without crashing diagnose_and_plan_heal
        from unittest.mock import patch
        with patch.object(auto_heal, "MacroCacheEngine", side_effect=RuntimeError("db locked")):
            err_plan = auto_heal.diagnose_and_plan_heal(target_dir=self.temp_dir, failure_info=inline_syntax)
        self.assertEqual(err_plan["status"], "HEALING_PLAN_READY")
        self.assertFalse(err_plan["macro_cache_match"])
        self.assertFalse(err_plan["macro_repair"]["repaired"])
        self.assertEqual(err_plan["macro_repair"]["tokens_consumed"], 0)
        self.assertIn("db locked", err_plan["macro_repair"]["error"])

    def test_auto_heal_entropy_pruner_long_and_short_signatures(self):
        """Verifies EntropyPruner compresses >400-char err_sig while preserving <=400-char signatures."""
        long_err = (
            "======================================================================\n"
            "# Verbose test runner banner boilerplate\n"
            "# Extra diagnostic noise line 1\n"
            "TimeoutError: locator('#checkout-submit-btn') timed out after 5000ms.\n"
            + ("# repeated diagnostic comment padding line for entropy pruning\n" * 8)
            + "at CheckoutPage.submit (/app/pages/CheckoutPage.ts:88:12)"
        )
        self.assertGreater(len(long_err), 400)

        long_plan = auto_heal.diagnose_and_plan_heal(
            target_dir=self.temp_dir,
            failure_info={"tc": "TC_LongErr", "reason": long_err, "file": "CheckoutPage.ts", "line": 88},
        )
        self.assertEqual(long_plan["status"], "HEALING_PLAN_READY")
        self.assertEqual(long_plan["error_signature"], long_err)
        self.assertIn("pruned_error_signature", long_plan)
        self.assertIn("pruned_chars_saved", long_plan)
        self.assertIsInstance(long_plan["pruned_error_signature"], str)
        self.assertTrue(bool(long_plan["pruned_error_signature"].strip()))
        self.assertLessEqual(len(long_plan["pruned_error_signature"]), 400)
        self.assertLess(len(long_plan["pruned_error_signature"]), len(long_err))
        self.assertEqual(long_plan["pruned_chars_saved"], len(long_err) - len(long_plan["pruned_error_signature"]))
        self.assertGreater(long_plan["pruned_chars_saved"], 0)

        # Boundary: 401-char single-line signature is bounded and reports saved >= 1
        err_401 = "Error: " + ("x" * 394)
        self.assertEqual(len(err_401), 401)
        plan_401 = auto_heal.diagnose_and_plan_heal(
            target_dir=self.temp_dir,
            failure_info={"tc": "TC_Boundary401", "reason": err_401, "file": "Boundary.ts", "line": 10},
        )
        self.assertTrue(bool(plan_401["pruned_error_signature"].strip()))
        self.assertLessEqual(len(plan_401["pruned_error_signature"]), 400)
        self.assertGreaterEqual(plan_401["pruned_chars_saved"], 1)

        # Boundary: exact 400-char and short signatures are left unpruned
        exact_400 = "E" * 400
        plan_400 = auto_heal.diagnose_and_plan_heal(
            target_dir=self.temp_dir,
            failure_info={"tc": "TC_Boundary400", "reason": exact_400, "file": "Boundary.ts", "line": 11},
        )
        self.assertEqual(plan_400["pruned_error_signature"], exact_400)
        self.assertEqual(plan_400["pruned_chars_saved"], 0)

        short_err = "Element #login-btn not visible"
        short_plan = auto_heal.diagnose_and_plan_heal(
            target_dir=self.temp_dir,
            failure_info={"tc": "TC_ShortErr", "reason": short_err, "file": "LoginPage.ts", "line": 15},
        )
        self.assertEqual(short_plan["pruned_error_signature"], short_err)
        self.assertEqual(short_plan["pruned_chars_saved"], 0)

    def test_auto_heal_associative_memory_record_and_query(self):
        """Verifies record_heal_lesson persists associative edges and diagnose_and_plan_heal surfaces matches."""
        from unittest.mock import patch

        err_msg = "Timeout waiting for locator('#pay-now-btn') on CheckoutPage"
        fix_code = "await page.getByRole('button', { name: 'Pay Now' }).click()"
        summary = "Use role-based locator for Pay Now button"

        with patch.object(auto_heal.cache_resolver, "record_lesson", return_value=True) as mock_rec:
            ok = auto_heal.record_heal_lesson(
                page_context="CheckoutPage.ts",
                error_signature=err_msg,
                root_cause="Dynamic ID changed",
                failed_attempt="page.click('#pay-now-btn')",
                successful_fix=fix_code,
                lesson_summary=summary,
                target_dir=self.temp_dir,
            )
        self.assertTrue(ok)
        mock_rec.assert_called_once()

        assoc_db = os.path.join(self.temp_dir, ".synapse", "associative_memory.db")
        self.assertTrue(os.path.isfile(assoc_db))

        # Verify context-manager closure on query and matching associative resolution
        orig_cls = auto_heal.AssociativeMemory
        exit_calls = []

        class TrackingAssocMem(orig_cls):
            def __exit__(self, exc_type, exc_val, exc_tb):
                exit_calls.append(True)
                return super().__exit__(exc_type, exc_val, exc_tb)

        with patch.object(auto_heal, "AssociativeMemory", TrackingAssocMem):
            plan = auto_heal.diagnose_and_plan_heal(
                target_dir=self.temp_dir,
                failure_info={"tc": "TC_Checkout_Pay", "reason": err_msg, "file": "CheckoutPage.ts", "line": 42},
            )
        self.assertGreaterEqual(len(exit_calls), 1)
        self.assertEqual(plan["status"], "HEALING_PLAN_READY")
        self.assertIn("associative_matches", plan)
        self.assertIsInstance(plan["associative_matches"], list)
        self.assertGreaterEqual(len(plan["associative_matches"]), 1)
        match = plan["associative_matches"][0]
        self.assertEqual(match["successful_fix"], fix_code)
        self.assertEqual(match["lesson_summary"], summary)
        self.assertEqual(match["page_context"], "CheckoutPage.ts")
        self.assertEqual(match["relation"], "resolved_by")
        self.assertGreater(match["weight"], 0.0)

        # Unrelated failure returns empty associative_matches without breaking contract
        unrelated_plan = auto_heal.diagnose_and_plan_heal(
            target_dir=self.temp_dir,
            failure_info={"tc": "TC_Other", "reason": "Completely different network error 503", "file": "Api.ts", "line": 5},
        )
        self.assertEqual(unrelated_plan["associative_matches"], [])
        self.assertEqual(auto_heal.diagnose_and_plan_heal(target_dir=self.temp_dir), {"status": "NO_FAILURE_DETECTED"})

    def test_auto_heal_cognitive_graceful_degradation(self):
        """Verifies EntropyPruner or AssociativeMemory errors and read-only DB dirs degrade gracefully."""
        from unittest.mock import patch

        long_err = "TimeoutError: " + ("stack frame detail " * 30)
        failure = {"tc": "TC_Resilience", "reason": long_err, "file": "Resilience.ts", "line": 9}

        # 1. EntropyPruner failure degrades gracefully
        with patch.object(auto_heal.EntropyPruner, "compress", side_effect=RuntimeError("entropy failure")):
            plan_ep = auto_heal.diagnose_and_plan_heal(target_dir=self.temp_dir, failure_info=failure)
        self.assertEqual(plan_ep["status"], "HEALING_PLAN_READY")
        self.assertTrue(bool(plan_ep["pruned_error_signature"].strip()))
        self.assertLessEqual(len(plan_ep["pruned_error_signature"]), 400)
        self.assertGreaterEqual(plan_ep["pruned_chars_saved"], 0)

        # 2. AssociativeMemory failure degrades gracefully in diagnose_and_plan_heal and record_heal_lesson
        with patch.object(auto_heal, "AssociativeMemory", side_effect=PermissionError("read-only db")):
            plan_am = auto_heal.diagnose_and_plan_heal(target_dir=self.temp_dir, failure_info=failure)
            with patch.object(auto_heal.cache_resolver, "record_lesson", return_value=True):
                ok = auto_heal.record_heal_lesson(
                    "Resilience.ts",
                    "TimeoutError",
                    "cause",
                    "attempt",
                    "fix",
                    "summary",
                    target_dir=self.temp_dir,
                )
        self.assertTrue(ok)
        self.assertEqual(plan_am["status"], "HEALING_PLAN_READY")
        self.assertEqual(plan_am["associative_matches"], [])

        # 3. Read-only directory does not crash diagnose_and_plan_heal
        ro_dir = os.path.join(self.temp_dir, "readonly_project")
        os.makedirs(ro_dir, exist_ok=True)
        os.chmod(ro_dir, 0o555)
        try:
            ro_plan = auto_heal.diagnose_and_plan_heal(target_dir=ro_dir, failure_info=failure)
            self.assertEqual(ro_plan["status"], "HEALING_PLAN_READY")
            self.assertIsInstance(ro_plan["associative_matches"], list)
        finally:
            os.chmod(ro_dir, 0o755)

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
        """Verifies setup_project creates canonical synapse.config.json when missing in Spoke."""
        spoke_dir = os.path.join(self.temp_dir, "new_spoke_project")
        os.makedirs(spoke_dir, exist_ok=True)
        config_path = os.path.join(spoke_dir, "synapse.config.json")

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
    at LoginPage.click (/var/workspace/Agent Skill/tests/login.spec.ts:42:10)
    at foo (C:\\Users\\User Name\\project\\tests\\checkout.spec.ts:15:5)
    at /var/workspace/Agent Skill/tests/test_ui.tsx:20:1
  File "/var/workspace/Agent Skill/tests/test_foo.py", line 99"""
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
        from tools.contrib.ui_server import JOB_MANAGER, SynapseUiHandler, ThreadingHTTPServer

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

    def test_repo_map_ast_python_parsing(self):
        """Verifies Python AST parser extracts direct methods, ignores local functions, and handles multiple classes."""
        import repo_map
        py_code = """
class LoginPage:
    def __init__(self, driver=None):
        self.driver = driver

    def login(self, username: str, password: str) -> bool:
        def inner_helper():
            return True
        return inner_helper()

    def is_logged_in(self) -> bool:
        return True

class DashboardPage(LoginPage):
    def get_summary(self) -> dict:
        return {}
"""
        test_file = os.path.join(self.temp_dir, "pages.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(py_code)

        classes = repo_map.extract_class_info(test_file, repo_root=self.temp_dir)
        self.assertEqual(len(classes), 2)

        cls_login = classes[0]
        self.assertEqual(cls_login["class_name"], "LoginPage")
        method_names = [m["name"] for m in cls_login["methods"]]
        self.assertIn("login", method_names)
        self.assertIn("is_logged_in", method_names)
        self.assertNotIn("__init__", method_names)
        self.assertNotIn("inner_helper", method_names)

        cls_dash = classes[1]
        self.assertEqual(cls_dash["class_name"], "DashboardPage")
        self.assertEqual(cls_dash["extends"], "LoginPage")
        self.assertEqual([m["name"] for m in cls_dash["methods"]], ["get_summary"])

    def test_repo_map_brace_depth_ts_js_groovy(self):
        """Verifies TS/JS/Groovy brace depth parser captures depth 1 methods and ignores inner calls."""
        import repo_map
        ts_code = """
export class BasePage {
    constructor(page: any) {
        this.page = page;
    }

    async waitForNetworkIdle(timeout?: number): Promise<void> {
        await this.page.waitForLoadState('networkidle', timeout !== undefined ? { timeout } : undefined);
        const delBtn = this.page.getByRole('button', { name: 'Xóa' });
        const firstElem = target.first();
        const stamp = Date.now();
    }
}

export class OrderPage extends BasePage {
    async submitOrder(orderId: string): Promise<void> {
        await this.page.click('#submit');
    }
}
"""
        test_file = os.path.join(self.temp_dir, "Pages.ts")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(ts_code)

        classes = repo_map.extract_class_info(test_file, repo_root=self.temp_dir)
        self.assertEqual(len(classes), 2)

        cls_base = classes[0]
        self.assertEqual(cls_base["class_name"], "BasePage")
        method_names = [m["name"] for m in cls_base["methods"]]
        self.assertEqual(method_names, ["waitForNetworkIdle"])
        self.assertNotIn("constructor", method_names)
        self.assertNotIn("waitForLoadState", method_names)
        self.assertNotIn("getByRole", method_names)
        self.assertNotIn("first", method_names)
        self.assertNotIn("now", method_names)

        cls_order = classes[1]
        self.assertEqual(cls_order["class_name"], "OrderPage")
        self.assertEqual(cls_order["extends"], "BasePage")
        self.assertEqual([m["name"] for m in cls_order["methods"]], ["submitOrder"])

    def test_repo_map_budget_under_500_tokens(self):
        """Verifies repo_map text budget is strictly under 500 tokens and indexes all reference suites."""
        import repo_map
        stats = repo_map.build_repo_map()
        self.assertLess(stats["estimated_tokens"], 500, f"Token budget exceeded: {stats['estimated_tokens']} >= 500")

        map_file = os.path.join(repo_map.HUB_ROOT, "tools", "repo_map.txt")
        self.assertTrue(os.path.exists(map_file))
        with open(map_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertLess(len(content) // 4, 500)
        self.assertIn("UserApiClient", content, "pytest-api-suite must not be censored from repo_map")

    def test_repo_map_multiline_and_annotations(self):
        """Verifies multiline method signatures, multiline class definitions, and annotations."""
        import repo_map
        ts_code = """
export class OrderPage
    extends BasePage
{
    async submitOrder(
        orderId: string,
        quantity: number
    ): Promise<void> {
        await this.page.click('#submit');
    }
}
"""
        test_file = os.path.join(self.temp_dir, "OrderPage.ts")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(ts_code)

        classes = repo_map.extract_class_info(test_file, repo_root=self.temp_dir)
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0]["class_name"], "OrderPage")
        self.assertEqual(classes[0]["extends"], "BasePage")
        self.assertEqual(len(classes[0]["methods"]), 1)
        self.assertEqual(classes[0]["methods"][0]["name"], "submitOrder")
        self.assertEqual(classes[0]["methods"][0]["params"], "orderId, quantity")

        groovy_code = """
class LoginPage extends BasePage {
    @Keyword(keywordObject = 'sample')
    def login(String username) {
        return true
    }
}
"""
        groovy_file = os.path.join(self.temp_dir, "LoginPage.groovy")
        with open(groovy_file, "w", encoding="utf-8") as f:
            f.write(groovy_code)

        g_classes = repo_map.extract_class_info(groovy_file, repo_root=self.temp_dir)
        self.assertEqual(len(g_classes), 1)
        g_methods = [m["name"] for m in g_classes[0]["methods"]]
        self.assertIn("login", g_methods)
        self.assertNotIn("Keyword", g_methods, "Annotations must never be extracted as methods")

    def test_repo_map_python_posonlyargs(self):
        """Verifies Python AST parser correctly strips 'self' with positional-only arguments."""
        import repo_map
        py_code = """
class UserPage:
    def get_user(self, user_id: int, /, active_only: bool = True):
        pass
"""
        test_file = os.path.join(self.temp_dir, "UserPage.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(py_code)

        classes = repo_map.extract_class_info(test_file, repo_root=self.temp_dir)
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0]["methods"][0]["name"], "get_user")
        self.assertNotIn("self", classes[0]["methods"][0]["params"])

    def test_distill_log_strip_ascii_art(self):
        """Verifies distill_log strips heavy ASCII banners while preserving failure triage."""
        import distill_log
        noisy_log = """
[INFO] Starting execution
TC-001 LoginPage FAILED
java.lang.NullPointerException: Element not found
    at Script100.groovy:15
======================================================================
"""
        distilled = distill_log.distill(noisy_log)
        self.assertNotIn("======================================================================", distilled)
        self.assertIn("FAILURES DETECTED", distilled)
        self.assertIn("TC-001", distilled)
        self.assertIn("NullPointerException", distilled)
        self.assertIn("Script100.groovy:15", distilled)

    def test_count_tokens_output_savings(self):
        """Verifies count_tokens calculate_hub_savings incorporates output token savings from Lean Badge."""
        import count_tokens
        savings = count_tokens.calculate_hub_savings(1000, 200, 500, turns_count=5)
        # 5 turns * 180 = 900 saved output tokens -> non_hub_output = 500 + 900 = 1400
        self.assertEqual(savings["non_hub_total"] - (1000 * 3.5 + 200 * 0.82 + 200 * 0.18), 1400)
        self.assertGreater(savings["tokens_saved"], 0)

    def test_agents_md_alignment(self):
        """Verifies AGENTS.md §0.3 token claim and §3.4 project_state.py entry."""
        agents_path = os.path.join(REPO_ROOT, "AGENTS.md")
        with open(agents_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("tools/core/project_state.py", content)
        self.assertIn("10–25% on technical documentation", content)

    # -------------------------------------------------------------------------
    # 9. P0/P1 Audit Improvements Verification
    # -------------------------------------------------------------------------
    def test_package_scoping_no_unscoped_npx(self):
        """Verifies package scoping: @teevee98/synapse-hub is used in docs and tools."""
        # 1. tools/update_sentinel.py queries @teevee98/synapse-hub
        sentinel_path = os.path.join(REPO_ROOT, "tools", "lint", "update_sentinel.py")
        with open(sentinel_path, "r", encoding="utf-8") as f:
            sentinel_code = f.read()
        self.assertIn("https://registry.npmjs.org/@teevee98/synapse-hub/latest", sentinel_code)
        self.assertNotIn("https://registry.npmjs.org/synapse-hub/latest", sentinel_code)
        self.assertIn("@teevee98/synapse-hub@latest", sentinel_code)

        # 2. README.md & README.en.md quickstart commands
        for readme_name in ("README.md", "README.en.md"):
            with open(os.path.join(REPO_ROOT, readme_name), "r", encoding="utf-8") as f:
                readme_text = f.read()
            self.assertIn("npx @teevee98/synapse-hub doctor", readme_text)
            self.assertIn("npx @teevee98/synapse-hub verify", readme_text)
            self.assertNotIn("npx synapse-hub verify", readme_text)

        # 3. CLAUDE.md quick commands
        with open(os.path.join(REPO_ROOT, "CLAUDE.md"), "r", encoding="utf-8") as f:
            claude_text = f.read()
        self.assertIn("npx @teevee98/synapse-hub verify", claude_text)
        self.assertNotIn("npx synapse-hub verify", claude_text)

    def test_skills_manifest_descriptions_fully_populated(self):
        """Verifies all skills in skills_manifest.json have non-empty description fields synced with SKILL.md."""
        import re
        manifest_path = os.path.join(REPO_ROOT, "skills_manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        skills = manifest.get("skills", [])
        self.assertEqual(len(skills), 57)
        for s in skills:
            desc = s.get("description", "")
            self.assertTrue(bool(desc and desc.strip()), f"Skill '{s.get('id')}' is missing description")
            self.assertGreater(len(desc), 20, f"Skill '{s.get('id')}' description is too short")

            skill_md = os.path.join(REPO_ROOT, s["path"]) if "path" in s else os.path.join(REPO_ROOT, ".agents", "skills", s["domain"], s["id"], "SKILL.md")
            if not os.path.exists(skill_md):
                skill_md = os.path.join(REPO_ROOT, ".agents", "skills", s["domain"], s["id"], "SKILL.md")
            self.assertTrue(os.path.exists(skill_md), f"Missing {skill_md}")
            with open(skill_md, "r", encoding="utf-8") as f_md:
                content = f_md.read()
            fm_match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
            self.assertIsNotNone(fm_match, f"No frontmatter in {skill_md}")
            desc_match = re.search(r"^description:\s*(.*?)(?=\n[a-z_]+:|\Z)", fm_match.group(1), re.DOTALL | re.MULTILINE)
            self.assertIsNotNone(desc_match, f"No description in {skill_md}")
            fm_desc = re.sub(r"\s+", " ", desc_match.group(1).strip().strip("\"'"))
            manifest_desc = re.sub(r"\s+", " ", desc)
            self.assertEqual(fm_desc, manifest_desc, f"Mismatch for skill '{s['id']}' between SKILL.md and manifest")

    def test_skill_precedence_hierarchy_reframe(self):
        """Verifies skill-precedence.md frames guardrails and core rules above skills."""
        precedence_path = os.path.join(REPO_ROOT, "standards", "qa-process", "skill-precedence.md")
        if not os.path.exists(precedence_path):
            precedence_path = os.path.join(REPO_ROOT, ".agents", "rules", "skill-precedence.md")
        with open(precedence_path, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Platform / System Guardrails", text)
        self.assertIn("Core Project Rules", text)
        self.assertIn("Project-Local Skills", text)
        self.assertIn("External Plugins", text)
        pos_guardrails = text.index("Platform / System Guardrails")
        pos_rules = text.index("Core Project Rules")
        pos_skills = text.index("Project-Local Skills")
        pos_ext = text.index("External Plugins")
        self.assertTrue(pos_guardrails < pos_rules < pos_skills < pos_ext)

    def test_author_integrity_mit_license_separation(self):
        """Verifies author-integrity-guard.md separates legal MIT notice retention from AI ethical policy."""
        guard_path = os.path.join(REPO_ROOT, "standards", "coding-standards", "author-integrity-guard.md")
        if not os.path.exists(guard_path):
            guard_path = os.path.join(REPO_ROOT, ".agents", "rules", "author-integrity-guard.md")
        with open(guard_path, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Legal Licensing Requirements (MIT License)", text)
        self.assertIn("Project Ethical Attribution Policy", text)
        self.assertIn("Permitted Modifications", text)
        self.assertNotIn("Re-license or re-brand this codebase while stripping", text)

    def test_hub_publisher_confirm_release(self):
        """Verifies hub_publisher confirmation prompt: dry-run, --yes, interactive prompt, and non-interactive rejection."""
        import hub_publisher
        from unittest.mock import patch

        # 1. dry-run bypasses confirmation
        self.assertTrue(hub_publisher.confirm_release("9.9.9", "owner", "repo", dry_run=True))

        # 2. --yes flag bypasses confirmation
        self.assertTrue(hub_publisher.confirm_release("9.9.9", "owner", "repo", yes=True))

        # 3. Interactive prompt - user confirms 'y'
        with patch("sys.stdin.isatty", return_value=True), \
             patch("builtins.input", return_value="y"), \
             patch.dict(os.environ, {"CI": "", "SYNAPSE_NON_INTERACTIVE": ""}, clear=False):
            self.assertTrue(hub_publisher.confirm_release("9.9.9", "owner", "repo", yes=False))

        # 4. Interactive prompt - user cancels 'n'
        with patch("sys.stdin.isatty", return_value=True), \
             patch("builtins.input", return_value="n"), \
             patch.dict(os.environ, {"CI": "", "SYNAPSE_NON_INTERACTIVE": ""}, clear=False):
            self.assertFalse(hub_publisher.confirm_release("9.9.9", "owner", "repo", yes=False))

        # 5. Non-interactive without --yes returns False
        with patch("sys.stdin.isatty", return_value=False), \
             patch.dict(os.environ, {"CI": "1"}, clear=False):
            self.assertFalse(hub_publisher.confirm_release("9.9.9", "owner", "repo", yes=False))

    def test_gate_count_sync_and_repo_map_clarification(self):
        """Verifies verification-before-completion references 10 gates and repo_map generation command."""
        vbc_candidates = [
            os.path.join("skills", "06-healing-and-resilience", "verification-before-completion", "SKILL.md"),
            os.path.join("testing", "healing-resilience", "verification-before-completion", "SKILL.md"),
            os.path.join("standards", "quality-gates", "verification-before-completion", "SKILL.md"),
            os.path.join(".agents", "skills", "06-healing-and-resilience", "verification-before-completion", "SKILL.md"),
        ]
        vbc_path = next((p for p in vbc_candidates if os.path.exists(os.path.join(REPO_ROOT, p))), None)
        self.assertIsNotNone(vbc_path)
        with open(os.path.join(REPO_ROOT, vbc_path), "r", encoding="utf-8") as f:
            vbc_text = f.read()
        self.assertIn("10-gate acceptance command", vbc_text)
        self.assertNotIn("9-gate acceptance command", vbc_text)

        # repo_map.txt generated via python tools/repo_map.py
        for candidate_paths in [
            (
                os.path.join("skills", "11-ai-and-prompting", "token-and-context-optimizer", "SKILL.md"),
                os.path.join("standards", "context-ai", "token-and-context-optimizer", "SKILL.md"),
                os.path.join(".agents", "skills", "11-ai-and-prompting", "token-and-context-optimizer", "SKILL.md"),
            ),
            (
                os.path.join("skills", "06-healing-and-resilience", "agentless-qa-repair", "SKILL.md"),
                os.path.join("testing", "healing-resilience", "agentless-qa-repair", "SKILL.md"),
                os.path.join("automation", "healing", "agentless-qa-repair", "SKILL.md"),
                os.path.join(".agents", "skills", "06-healing-and-resilience", "agentless-qa-repair", "SKILL.md"),
            ),
        ]:
            found_path = next((p for p in candidate_paths if os.path.exists(os.path.join(REPO_ROOT, p))), None)
            self.assertIsNotNone(found_path, f"Skill file not found: {candidate_paths}")
            with open(os.path.join(REPO_ROOT, found_path), "r", encoding="utf-8") as f:
                skill_text = f.read()
            self.assertTrue("tools/repo_map.py" in skill_text or "tools/core/repo_map.py" in skill_text)

    def test_session_and_credential_hygiene_guidelines(self):
        """Verifies session hygiene in qa-memory-os and auth-session-and-cookie-manager."""
        mem_candidates = [
            os.path.join("skills", "10-agent-orchestration", "qa-memory-os", "SKILL.md"),
            os.path.join("ai-agents", "orchestration", "qa-memory-os", "SKILL.md"),
            os.path.join("ai-agents", "memory", "qa-memory-os", "SKILL.md"),
            os.path.join(".agents", "skills", "10-agent-orchestration", "qa-memory-os", "SKILL.md"),
        ]
        mem_path = next((p for p in mem_candidates if os.path.exists(os.path.join(REPO_ROOT, p))), None)
        self.assertIsNotNone(mem_path)
        with open(os.path.join(REPO_ROOT, mem_path), "r", encoding="utf-8") as f:
            mem_text = f.read()
        self.assertIn("non-sensitive session metadata", mem_text)
        self.assertIn("token hash reference", mem_text)
        self.assertIn("Session Lifecycle & Teardown Protocol", mem_text)

        auth_candidates = [
            os.path.join("skills", "01-web-automation", "auth-session-and-cookie-manager", "SKILL.md"),
            os.path.join("automation", "shared-utils", "auth-session-and-cookie-manager", "SKILL.md"),
            os.path.join("automation", "playwright", "auth-session-and-cookie-manager", "SKILL.md"),
            os.path.join(".agents", "skills", "01-web-automation", "auth-session-and-cookie-manager", "SKILL.md"),
        ]
        auth_path = next((p for p in auth_candidates if os.path.exists(os.path.join(REPO_ROOT, p))), None)
        self.assertIsNotNone(auth_path)
        with open(os.path.join(REPO_ROOT, auth_path), "r", encoding="utf-8") as f:
            auth_text = f.read()
        self.assertIn("No Plaintext Tokens in Logs", auth_text)
        self.assertIn("SHA-256 hash reference", auth_text)
        self.assertIn("Automated Session Teardown & Invalidation", auth_text)


if __name__ == "__main__":
    unittest.main()
