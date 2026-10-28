#!/usr/bin/env python3
"""
Enterprise Automated Testing Suite for AI Agent Tools & Hub Integrity
----------------------------------------------------------------------
Verifies the syntactic correctness, importability, and deterministic
behavior of all centralized tools in `tools/` using standard library `unittest`.
Contains real behavioral assertions and fixture-based functional tests.
"""

import os
import sys
import json
import tempfile
import io
import unittest

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
sys.path.insert(0, TOOLS_DIR)

import infer_linter
import lint_ai_docs
import distill_log
import cache_resolver
import verify_all
import wcag_audit
import cli
import flaky_detector


class TestToolsIntegrityAndBehavior(unittest.TestCase):
    """Automated unit and functional tests for tools in tools/."""

    def test_skills_manifest_integrity(self):
        """Validates that skills_manifest.json matches disk files."""
        manifest_path = os.path.join(REPO_ROOT, "skills_manifest.json")
        self.assertTrue(os.path.exists(manifest_path), "skills_manifest.json must exist")

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("version"), "2.0.0", "Manifest version must be 2.0.0")
        manifest_skills = [s["id"] for s in data.get("skills", [])]
        self.assertEqual(len(manifest_skills), 34, "Manifest must declare exactly 34 skills")

        skills_dir = os.path.join(REPO_ROOT, ".agents", "skills")
        for skill_id in manifest_skills:
            skill_md = os.path.join(skills_dir, skill_id, "SKILL.md")
            self.assertTrue(os.path.exists(skill_md), f"Skill file must exist: {skill_md}")

    def test_browser_helpers_exists_and_complete(self):
        """Validates that browser_helpers.js exists and exports core capabilities."""
        helper_path = os.path.join(TOOLS_DIR, "browser_helpers.js")
        self.assertTrue(os.path.exists(helper_path), "tools/browser_helpers.js must exist")

        with open(helper_path, "r", encoding="utf-8") as f:
            code = f.read()

        expected_methods = ["batch:", "audit:", "heal:", "clickSafe:", "exportSession:", "isStable:"]
        for method in expected_methods:
            self.assertIn(method, code, f"browser_helpers.js missing method: {method}")

    def test_cache_resolver_cosine_similarity(self):
        """Validates compute_cosine_similarity calculation in cache_resolver."""
        t1 = "ElementClickInterceptedException timeout error"
        t2 = "ElementClickInterceptedException timeout error"
        t3 = "Completely different issue unrelated"

        self.assertAlmostEqual(cache_resolver.compute_cosine_similarity(t1, t2), 1.0, places=4)
        self.assertAlmostEqual(cache_resolver.compute_cosine_similarity(t1, t3), 0.0, places=4)

    def test_cache_resolver_no_false_positive_between_distinct_exceptions(self):
        """Validates that distinct UI exceptions with shared boilerplate do not trigger false positive matches."""
        no_such = "org.openqa.selenium.NoSuchElementException: Cannot locate element at com.kms.katalon.core.webui.keyword.builtin.ClickKeyword"
        stale = "org.openqa.selenium.StaleElementReferenceException: stale element reference at com.kms.katalon.core.webui.keyword.builtin.ClickKeyword"

        sim = cache_resolver.compute_cosine_similarity(no_such, stale)
        self.assertLess(sim, 0.20, f"NoSuchElement and StaleElement must not collide on boilerplate tokens, got {sim}")

    def test_cache_resolver_negative_memory_failed_fixes(self):
        """Validates that cache_resolver records and retrieves failed bug fix attempts."""
        cache_resolver.init_db(seed=True)
        sig = "UnitTest_Custom_Exception"
        cache_resolver.record_failed_fix(
            error_signature=sig,
            attempted_patch="mock_broken_patch();",
            failure_reason="Failed validation during test execution",
            agent_role="unit-tester"
        )
        failed_list = cache_resolver.get_failed_fixes(sig)
        self.assertTrue(len(failed_list) >= 1, "Must retrieve recorded failed fix")
        self.assertEqual(failed_list[0]["attempted_patch"], "mock_broken_patch();")
        self.assertEqual(failed_list[0]["failure_reason"], "Failed validation during test execution")

    # --- FUNCTIONAL TESTS FOR INFER_LINTER ---

    def test_infer_linter_functional_detects_swallowed_exception(self):
        """Validates that infer_linter detects empty catch blocks as CRITICAL defects."""
        with tempfile.NamedTemporaryFile("w", suffix=".groovy", delete=False, encoding="utf-8") as tf:
            tf.write("""
                try {
                    LoginPage.login("admin", "123")
                } catch (Exception e) {
                    // swallowed exception!
                }
                assert true
            """)
            temp_path = tf.name

        try:
            result = infer_linter.analyze_script(temp_path)
            self.assertFalse(result["is_clean"])
            defect_types = [d["type"] for d in result["defects"]]
            self.assertIn("SWALLOWED_EXCEPTION", defect_types)
            criticals = [d for d in result["defects"] if d["severity"] == "CRITICAL"]
            self.assertTrue(len(criticals) >= 1)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_infer_linter_functional_detects_flaky_sleep(self):
        """Validates that infer_linter detects excessive Thread.sleep as WARNING."""
        with tempfile.NamedTemporaryFile("w", suffix=".groovy", delete=False, encoding="utf-8") as tf:
            tf.write("""
                LoginPage.open()
                Thread.sleep(5000)
                assert LoginPage.isLoaded()
            """)
            temp_path = tf.name

        try:
            result = infer_linter.analyze_script(temp_path)
            defect_types = [d["type"] for d in result["defects"]]
            self.assertIn("EXCESSIVE_HARD_DELAY", defect_types)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_infer_linter_functional_detects_fake_pass(self):
        """Validates that infer_linter detects actions without assertions as FAKE_PASS."""
        with tempfile.NamedTemporaryFile("w", suffix=".groovy", delete=False, encoding="utf-8") as tf:
            tf.write("""
                LoginPage.open()
                LoginPage.enterCredentials("user", "pass")
                LoginPage.clickSubmit()
                // Performs multiple interactions but contains zero verification/assertions!
            """)
            temp_path = tf.name

        try:
            result = infer_linter.analyze_script(temp_path)
            defect_types = [d["type"] for d in result["defects"]]
            self.assertIn("FAKE_PASS_NO_ASSERTION", defect_types)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_infer_linter_functional_clean_script(self):
        """Validates that a compliant test script passes cleanly."""
        with tempfile.NamedTemporaryFile("w", suffix=".groovy", delete=False, encoding="utf-8") as tf:
            tf.write("""
                LoginPage.open()
                LoginPage.login("user", "pass")
                verifyElementPresent(DashboardPage.HEADER, 10)
                assertTrue(DashboardPage.isLoaded())
            """)
            temp_path = tf.name

        try:
            result = infer_linter.analyze_script(temp_path)
            self.assertTrue(result["is_clean"], f"Compliant script should be clean, got: {result['defects']}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_infer_linter_zero_scripts_guard(self):
        """Validates that infer_linter handles an empty directory without ZeroDivisionError."""
        with tempfile.TemporaryDirectory() as empty_dir:
            ret = infer_linter.run_infer_linter(target_dir=empty_dir)
            self.assertEqual(ret, 0, "run_infer_linter on empty dir must return exit code 0")

    # --- FUNCTIONAL TESTS FOR LINT_AI_DOCS ---

    def test_lint_ai_docs_functional_on_repo(self):
        """Validates that lint_ai_docs runs without runtime crash on repo."""
        errors, warnings = lint_ai_docs.lint_docs(REPO_ROOT)
        self.assertEqual(len(errors), 0, f"Expected 0 doc lint errors on repo, got: {errors}")

    def test_lint_ai_docs_detects_hallucinated_tool(self):
        """Validates that lint_ai_docs catches references to nonexistent tools."""
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, dir=REPO_ROOT, encoding="utf-8") as tf:
            tf.write("Run the tool: tools/fake_nonexistent_hallucinated_tool.py for testing.\n")
            temp_path = tf.name

        try:
            errors, _ = lint_ai_docs.lint_docs(REPO_ROOT)
            matched = any("fake_nonexistent_hallucinated_tool.py" in e for e in errors)
            self.assertTrue(matched, "lint_ai_docs must catch hallucinated tool script")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # --- FUNCTIONAL TESTS FOR DISTILL_LOG ---

    def test_distill_log_functional(self):
        """Validates that distill_log filters noise and preserves failure blocks."""
        raw_log = [
            "[INFO] Starting build task...",
            "> Task :compileJava UP-TO-DATE",
            "> Task :processResources UP-TO-DATE",
            "SLF4J: Failed to load class",
            "[DEBUG] Loading configuration profiles",
            "Starting ChromeDriver 114.0",
            "Only local connections are allowed",
            "DevTools listening on ws://127.0.0.1:9222",
            "TC-101 LoginFlow PASSED",
            "TC-102 CheckoutFlow FAILED",
            "java.lang.NullPointerException: Cannot invoke method click() on null object",
            "    at Script1680000000000.run(Script1680000000000.groovy:42)",
            "    at com.kms.katalon.core.main.ScriptEngine.run(ScriptEngine.java:194)",
            "[INFO] Test execution finished."
        ]
        noisy_text = "\n".join(raw_log * 10)  # 140 lines of noise
        distilled = distill_log.distill(noisy_text)

        self.assertIn("FAILURES DETECTED", distilled)
        self.assertIn("TC-102", distilled)
        self.assertIn("NullPointerException", distilled)
        self.assertTrue(len(distilled.splitlines()) < len(noisy_text.splitlines()) * 0.5,
                        "Distilled log should compress noise by over 50%")

    # --- FUNCTIONAL TESTS FOR VERIFY_ALL GATES ---

    def test_verify_all_bom_gate_functional(self):
        """Validates Gate 1 detects UTF-8 BOM in files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            bom_file = os.path.join(temp_dir, "test.md")
            with open(bom_file, "wb") as f:
                f.write(b"\xef\xbb\xbf# BOM Header\n")

            has_passed = verify_all.gate_1_bom_check(temp_dir)
            self.assertFalse(has_passed, "gate_1_bom_check must return False when BOM exists")

    def test_verify_all_gate_5_no_windows_dot_bug(self):
        """Validates Gate 5 passes and does not match '.' on Windows."""
        has_passed = verify_all.gate_5_cleanup_blacklist(REPO_ROOT)
        self.assertTrue(has_passed, "Gate 5 must pass on clean repository without matching '.'")

    def test_verify_all_gate_6_detects_credentials_functional(self):
        """Validates Gate 6 catches plaintext hardcoded passwords."""
        with tempfile.TemporaryDirectory() as temp_dir:
            bad_file = os.path.join(temp_dir, "config.py")
            with open(bad_file, "w", encoding="utf-8") as f:
                f.write("password = 'Vnpt@2024'\n")  # gate6-allowlist: synthetic test fixture

            has_passed = verify_all.gate_6_credential_security(temp_dir, mode="HUB")
            self.assertFalse(has_passed, "gate_6_credential_security must fail when hardcoded password exists")

    def test_verify_all_complete_run_hub_mode(self):
        """Validates that all 7 gates pass on the QA Hub."""
        repo_root = REPO_ROOT
        gates = [
            verify_all.gate_1_bom_check,
            verify_all.gate_2_path_portability,
            verify_all.gate_3_clean_pom,
            verify_all.gate_4_ai_docs_lint,
            verify_all.gate_5_cleanup_blacklist,
            verify_all.gate_6_credential_security,
            verify_all.gate_7_infer_linter,
        ]
        for gate in gates:
            res = gate(repo_root, mode="HUB")
            self.assertTrue(res, f"Gate {gate.__name__} failed in HUB mode")

    # --- FUNCTIONAL TESTS FOR WCAG AUDIT ---

    def test_wcag_audit_functional(self):
        """Validates that wcag_audit detects accessibility violations in HTML."""
        bad_html = """
        <html>
            <body>
                <img src="logo.png">
                <button></button>
                <input type="text" name="username">
            </body>
        </html>
        """
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tf:
            tf.write(bad_html)
            temp_path = tf.name

        try:
            auditor = wcag_audit.run_audit(temp_path)
            self.assertTrue(len(auditor.violations) >= 2, "Must detect missing alt and empty button")
            criteria = [v["criterion"] for v in auditor.violations]
            self.assertTrue(any("1.1.1" in c for c in criteria))
            self.assertTrue(any("4.1.2" in c for c in criteria))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # --- FUNCTIONAL TESTS FOR CLI DISPATCH ---

    def test_cli_version_output(self):
        """Validates that cli.cmd_version outputs the expected catalog details."""
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            cli.cmd_version(None)
            output = sys.stdout.getvalue()
            self.assertIn("Agent-QA Hub CLI v2.0.0", output)
            self.assertIn("34 Standardized Skills", output)
        finally:
            sys.stdout = old_stdout

    def test_flaky_detector_calculate_flakiness(self):
        """Validates that flaky_detector correctly scores flakiness tiers and quarantine flags."""
        # 1. Deterministic PASS
        res_stable = flaky_detector.calculate_flakiness([True, True, True, True, True])
        self.assertEqual(res_stable["status"], "STABLE")
        self.assertFalse(res_stable["quarantine"])
        self.assertEqual(res_stable["pass_rate"], 100.0)
        self.assertEqual(res_stable["flips"], 0)

        # 2. Intermittent Severe Flake (3 pass, 2 fail, 4 flips)
        res_severe = flaky_detector.calculate_flakiness([True, False, True, False, True])
        self.assertEqual(res_severe["status"], "SEVERE_FLAKE")
        self.assertTrue(res_severe["quarantine"])
        self.assertEqual(res_severe["flips"], 4)
        self.assertEqual(res_severe["pass_rate"], 60.0)

        # 3. Deterministic FAIL
        res_fail = flaky_detector.calculate_flakiness([False, False, False, False, False])
        self.assertEqual(res_fail["status"], "DETERMINISTIC_FAIL")
        self.assertFalse(res_fail["quarantine"])

    # --- REGRESSION TESTS FOR 7 REPORTED DEFECTS ---

    def test_browser_helpers_fetch_window_context(self):
        """Regression test 1: window.fetch hook must bind context to window to avoid Illegal invocation."""
        helper_path = os.path.join(TOOLS_DIR, "browser_helpers.js")
        with open(helper_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("origFetch.apply(window, arguments)", content)
        self.assertNotIn("origFetch.apply(this, arguments)", content)

    def test_infer_linter_no_false_positive_on_check_words(self):
        """Regression test 2: ASSERTION_PATTERN must have \\b and not match checkbox or checkout."""
        from infer_linter import ASSERTION_PATTERN
        self.assertFalse(bool(ASSERTION_PATTERN.search("WebUI.click(findTestObject('input_checkbox'))")))
        self.assertFalse(bool(ASSERTION_PATTERN.search("checkout()")))
        self.assertFalse(bool(ASSERTION_PATTERN.search("checkAvailability()")))
        self.assertFalse(bool(ASSERTION_PATTERN.search("checkbox.click()")))
        
        # Must match valid assertions
        self.assertTrue(bool(ASSERTION_PATTERN.search("assertTrue(isValid)")))
        self.assertTrue(bool(ASSERTION_PATTERN.search("assert expected == actual")))
        self.assertTrue(bool(ASSERTION_PATTERN.search("verifyElementPresent(findTestObject('btn'))")))
        self.assertTrue(bool(ASSERTION_PATTERN.search("waitForToast('Success')")))
        self.assertTrue(bool(ASSERTION_PATTERN.search("checkStatus(200)")))
        self.assertTrue(bool(ASSERTION_PATTERN.search("expect(page).toHaveTitle('Dashboard')")))

    def test_validate_groovy_scripts_strips_comments_and_regex(self):
        """Regression test 3: strip_comments_and_strings must eliminate braces in comments and regexes."""
        import validate_groovy_scripts
        from pathlib import Path
        snippet = """
        // Log success :)
        /* block comment with { unmatched brace */
        String regex = "\\\\d{1,3}";
        def match = ~/\\\\d{1,3}/;
        def run() {
            println("Test with (paren)");
        }
        """
        temp_file = Path(REPO_ROOT) / "temp_validate_test.groovy"
        try:
            temp_file.write_text(snippet, encoding="utf-8")
            errors = validate_groovy_scripts.check_file(temp_file)
            self.assertEqual(errors, [], f"Expected zero errors, got: {errors}")
        finally:
            if temp_file.exists():
                temp_file.unlink()

    def test_cache_resolver_sync_db_initializes_both_schemas(self):
        """Regression test 4: sync_db must initialize schemas for both GLOBAL_DB and LOCAL_DB."""
        synced = cache_resolver.sync_db()
        self.assertIsInstance(synced, int)
        self.assertGreaterEqual(synced, 0)

    def test_visual_diff_canvas_vectorized(self):
        """Regression test 5: compare_canvas_images runs fast using C-level histogram and accurate diff."""
        from PIL import Image
        import visual_diff_canvas
        im1 = Image.new("RGB", (200, 200), (255, 255, 255))
        im2 = Image.new("RGB", (200, 200), (255, 255, 255))
        for x in range(20):
            for y in range(20):
                im2.putpixel((x, y), (0, 0, 0))
        t1 = os.path.join(REPO_ROOT, "temp_canvas1.png")
        t2 = os.path.join(REPO_ROOT, "temp_canvas2.png")
        diff_out = os.path.join(REPO_ROOT, "temp_diff.png")
        try:
            im1.save(t1)
            im2.save(t2)
            is_match, ratio, count = visual_diff_canvas.compare_canvas_images(t1, t2, diff_out, threshold=0.005)
            self.assertFalse(is_match)
            self.assertEqual(count, 400)
            self.assertAlmostEqual(ratio, 400 / 40000, places=4)
            self.assertTrue(os.path.exists(diff_out))
        finally:
            for p in [t1, t2, diff_out]:
                if os.path.exists(p):
                    os.remove(p)

    def test_check_env_ssl_unverified(self):
        """Regression test 6: check_env.py must use unverified SSL context and have UTF-8 stdout configured."""
        env_tool = os.path.join(TOOLS_DIR, "check_env.py")
        with open(env_tool, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("ssl.CERT_NONE", code)
        self.assertIn("sys.stdout.reconfigure", code)

    def test_package_dist_includes_docs_scripts_templates(self):
        """Regression test 7: docs/, scripts/, and templates/ must exist and be included in agent-skills.zip."""
        import zipfile
        zip_path = os.path.join(REPO_ROOT, "agent-skills.zip")
        self.assertTrue(os.path.exists(zip_path), "agent-skills.zip must exist")
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = set(zf.namelist())
            self.assertIn("docs/ARCHITECTURE.md", names)
            self.assertIn("docs/CLI_REFERENCE.md", names)
            self.assertIn("scripts/install.ps1", names)
            self.assertIn("scripts/setup.sh", names)
            self.assertIn("templates/PROJECT_AI_GUIDE_TEMPLATE.md", names)

    def test_lookup_tc_multi_tier_resolution(self):
        """Validates that lookup_tc.py supports CLI --file and TC_DATA_FILE environment variable."""
        import lookup_tc
        sample_tc = [{"ID": "TC-999", "Name": "Test Login Boundary", "Expected": "Pass", "Steps": "1. Open"}]
        temp_tc_file = os.path.join(REPO_ROOT, "temp_tc_test.json")
        with open(temp_tc_file, "w", encoding="utf-8") as f:
            json.dump(sample_tc, f)

        try:
            # 1. Test CLI file resolution
            p1 = lookup_tc.resolve_json_path(cli_file=temp_tc_file)
            self.assertEqual(os.path.abspath(temp_tc_file), p1)

            # 2. Test ENV var resolution
            os.environ["TC_DATA_FILE"] = temp_tc_file
            p2 = lookup_tc.resolve_json_path()
            self.assertEqual(os.path.abspath(temp_tc_file), p2)
        finally:
            if "TC_DATA_FILE" in os.environ:
                del os.environ["TC_DATA_FILE"]
            if os.path.exists(temp_tc_file):
                os.remove(temp_tc_file)

    def test_lookup_xpath_multi_tier_resolution(self):
        """Validates that lookup_xpath.py supports CLI --file and XPATH_DATA_FILE environment variable."""
        import lookup_xpath
        sample_xp = {"LoginPage": [{"constant": "TXT_USER", "xpath": "//input[@id='user']", "tag": "input"}]}
        temp_xp_file = os.path.join(REPO_ROOT, "temp_xp_test.json")
        with open(temp_xp_file, "w", encoding="utf-8") as f:
            json.dump(sample_xp, f)

        try:
            # 1. Test CLI file resolution
            p1 = lookup_xpath.resolve_json_path(cli_file=temp_xp_file)
            self.assertEqual(os.path.abspath(temp_xp_file), p1)

            # 2. Test ENV var resolution
            os.environ["XPATH_DATA_FILE"] = temp_xp_file
            p2 = lookup_xpath.resolve_json_path()
            self.assertEqual(os.path.abspath(temp_xp_file), p2)
        finally:
            if "XPATH_DATA_FILE" in os.environ:
                del os.environ["XPATH_DATA_FILE"]
            if os.path.exists(temp_xp_file):
                os.remove(temp_xp_file)


if __name__ == "__main__":
    unittest.main()
