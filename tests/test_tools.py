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
        self.assertEqual(len(manifest_skills), 30, "Manifest must declare exactly 30 skills")

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
            self.assertIn("30 Standardized Skills", output)
        finally:
            sys.stdout = old_stdout


if __name__ == "__main__":
    unittest.main()
