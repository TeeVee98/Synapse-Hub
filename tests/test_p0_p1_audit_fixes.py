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
        self.assertIn("tools/project_state.py", content)
        self.assertIn("10–25% on technical documentation", content)

    # -------------------------------------------------------------------------
    # 9. P0/P1 Audit Improvements Verification
    # -------------------------------------------------------------------------
    def test_package_scoping_no_unscoped_npx(self):
        """Verifies package scoping: @teevee98/synapse-hub is used in docs and tools."""
        # 1. tools/update_sentinel.py queries @teevee98/synapse-hub
        sentinel_path = os.path.join(REPO_ROOT, "tools", "update_sentinel.py")
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
        """Verifies all 53 skills in skills_manifest.json have non-empty description fields synced with SKILL.md."""
        import re
        manifest_path = os.path.join(REPO_ROOT, "skills_manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        skills = manifest.get("skills", [])
        self.assertEqual(len(skills), 53)
        for s in skills:
            desc = s.get("description", "")
            self.assertTrue(bool(desc and desc.strip()), f"Skill '{s.get('id')}' is missing description")
            self.assertGreater(len(desc), 20, f"Skill '{s.get('id')}' description is too short")

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
        precedence_path = os.path.join(REPO_ROOT, ".agents", "rules", "skill-precedence.md")
        with open(precedence_path, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Platform / System Guardrails", text)
        self.assertIn("Core Project Rules (.agents/rules/*)", text)
        self.assertIn("Project-Local Skills (.agents/skills/*)", text)
        self.assertIn("External Plugins", text)
        pos_guardrails = text.index("Platform / System Guardrails")
        pos_rules = text.index("Core Project Rules (.agents/rules/*)")
        pos_skills = text.index("Project-Local Skills (.agents/skills/*)")
        pos_ext = text.index("External Plugins")
        self.assertTrue(pos_guardrails < pos_rules < pos_skills < pos_ext)

    def test_author_integrity_mit_license_separation(self):
        """Verifies author-integrity-guard.md separates legal MIT notice retention from AI ethical policy."""
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
        vbc_path = os.path.join(REPO_ROOT, ".agents", "skills", "06-healing-and-resilience", "verification-before-completion", "SKILL.md")
        with open(vbc_path, "r", encoding="utf-8") as f:
            vbc_text = f.read()
        self.assertIn("10-gate acceptance command", vbc_text)
        self.assertNotIn("9-gate acceptance command", vbc_text)

        # repo_map.txt generated via python tools/repo_map.py
        for skill_rel in (
            os.path.join(".agents", "skills", "11-ai-and-prompting", "token-and-context-optimizer", "SKILL.md"),
            os.path.join(".agents", "skills", "06-healing-and-resilience", "agentless-qa-repair", "SKILL.md"),
        ):
            with open(os.path.join(REPO_ROOT, skill_rel), "r", encoding="utf-8") as f:
                skill_text = f.read()
            self.assertIn("tools/repo_map.py", skill_text)

    def test_session_and_credential_hygiene_guidelines(self):
        """Verifies session hygiene in qa-memory-os and auth-session-and-cookie-manager."""
        mem_path = os.path.join(REPO_ROOT, ".agents", "skills", "10-agent-orchestration", "qa-memory-os", "SKILL.md")
        with open(mem_path, "r", encoding="utf-8") as f:
            mem_text = f.read()
        self.assertIn("non-sensitive session metadata", mem_text)
        self.assertIn("token hash reference", mem_text)
        self.assertIn("Session Lifecycle & Teardown Protocol", mem_text)

        auth_path = os.path.join(REPO_ROOT, ".agents", "skills", "01-web-automation", "auth-session-and-cookie-manager", "SKILL.md")
        with open(auth_path, "r", encoding="utf-8") as f:
            auth_text = f.read()
        self.assertIn("No Plaintext Tokens in Logs", auth_text)
        self.assertIn("SHA-256 hash reference", auth_text)
        self.assertIn("Automated Session Teardown & Invalidation", auth_text)


if __name__ == "__main__":
    unittest.main()
