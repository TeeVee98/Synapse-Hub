#!/usr/bin/env python3
"""
Unit Tests for infer_linter.py verifying the 8 Golden Test Cases (L1 - L8)
from Enterprise QA Hub roadmap.
"""

import os
import sys
import tempfile
import unittest

# Ensure tools directory is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import infer_linter


class TestInferLinter8Cases(unittest.TestCase):
    """Verifies all 8 Test Cases from sheet 'Ca kiểm thử linter'."""

    def _analyze_code(self, code: str, extension: str = ".ts"):
        with tempfile.NamedTemporaryFile("w", suffix=extension, delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp_path = f.name
        try:
            res = infer_linter.analyze_script(tmp_path)
            return res
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_l1_empty_catch_ts_and_groovy(self):
        """L1: Empty catch {} in TS and Groovy must be caught as CRITICAL."""
        ts_code = """
        try {
            await page.click('#submit');
        } catch (e) {
        }
        """
        res_ts = self._analyze_code(ts_code, ".ts")
        swallowed = [d for d in res_ts["defects"] if d["type"] == "SWALLOWED_EXCEPTION"]
        self.assertTrue(len(swallowed) > 0, "L1 TS: Empty catch must be caught")
        self.assertEqual(swallowed[0]["severity"], "CRITICAL")

        groovy_code = """
        try {
            WebUI.click(findTestObject('btn_submit'))
        } catch (Exception e) {
        }
        """
        res_gr = self._analyze_code(groovy_code, ".groovy")
        swallowed_gr = [d for d in res_gr["defects"] if d["type"] == "SWALLOWED_EXCEPTION"]
        self.assertTrue(len(swallowed_gr) > 0, "L1 Groovy: Empty catch must be caught")
        self.assertEqual(swallowed_gr[0]["severity"], "CRITICAL")

    def test_l2_groovy_interaction_without_verify(self):
        """L2: Script Groovy with interaction but missing assertion must trigger WARNING."""
        code = """
        CustomKeywords.'com.example.Helper.login'("user", "pass")
        WebUI.click(findTestObject('btn_save'))
        """
        res = self._analyze_code(code, ".groovy")
        warn = [d for d in res["defects"] if d["type"] == "FAKE_PASS_NO_ASSERTION"]
        self.assertTrue(len(warn) > 0, "L2: Interaction without assertion must be warned")
        self.assertEqual(warn[0]["severity"], "WARNING")

    def test_l3_tautological_assertions(self):
        """L3: expect(true).toBe(true), assert True, assert true, assert 1 == 1 caught as CRITICAL."""
        cases = [
            ("expect(true).toBe(true);", ".ts"),
            ("assert True", ".py"),
            ("assert true", ".groovy"),
            ("assert 1 == 1", ".py")
        ]
        for snippet, ext in cases:
            res = self._analyze_code(snippet, ext)
            taut = [d for d in res["defects"] if d["type"] == "TAUTOLOGICAL_ASSERTION"]
            self.assertTrue(len(taut) > 0, f"L3: Tautology '{snippet}' must be detected as CRITICAL")
            self.assertEqual(taut[0]["severity"], "CRITICAL")

    def test_l4_unawaited_playwright_assertion(self):
        """L4: expect(locator).toBeVisible() without await in TS/JS caught as CRITICAL."""
        code = """
        import { test, expect } from '@playwright/test';
        test('example', async ({ page }) => {
            expect(page.locator('#banner')).toBeVisible();
        });
        """
        res = self._analyze_code(code, ".ts")
        unawaited = [d for d in res["defects"] if d["type"] == "UNAWAITED_ASYNC_ASSERTION"]
        self.assertTrue(len(unawaited) > 0, "L4: Unawaited Playwright assertion must be caught")
        self.assertEqual(unawaited[0]["severity"], "CRITICAL")

    def test_l5_python_swallowed_exception(self):
        """L5: except Exception: pass or except: pass caught as CRITICAL."""
        py_code = """
        try:
            perform_login()
        except Exception:
            pass
        """
        res = self._analyze_code(py_code, ".py")
        swallowed = [d for d in res["defects"] if d["type"] == "SWALLOWED_EXCEPTION"]
        self.assertTrue(len(swallowed) > 0, "L5: Python except: pass must be caught")
        self.assertEqual(swallowed[0]["severity"], "CRITICAL")

    def test_l6_test_without_assertions(self):
        """L6: Test Python/TS with logic but no assertions must report WARNING."""
        code = """
        def test_order_flow():
            client = APIClient()
            client.authenticate()
        """
        res = self._analyze_code(code, "test_order.py")
        no_assert = [d for d in res["defects"] if "ASSERTION" in d["type"]]
        self.assertTrue(len(no_assert) > 0, "L6: Test file without assert must trigger warning")

    def test_l7_valid_short_groovy_script(self):
        """L7: Valid 1-2 line Groovy script with assertion must NOT be flagged as empty."""
        code = """
        CustomKeywords.'com.example.Helper.login'("user", "pass")
        assert WebUI.verifyElementPresent(findTestObject('dashboard'), 10)
        """
        res = self._analyze_code(code, ".groovy")
        empty = [d for d in res["defects"] if d["type"] == "EMPTY_TEST_SCRIPT"]
        self.assertEqual(len(empty), 0, "L7: Valid short script must not be flagged as empty")
        self.assertTrue(res["is_clean"], "L7: Script with assert and action should be clean")

    def test_l8_codebase_health_score_bounded(self):
        """L8: Codebase health score must always be bounded in [0.0, 100.0]."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create multiple failing scripts
            for i in range(5):
                fpath = os.path.join(tmp_dir, f"test_fail_{i}.py")
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write("try:\n    pass\nexcept:\n    pass\nassert True\n")
            
            # Run infer_linter on directory
            exit_code = infer_linter.run_infer_linter(tmp_dir)
            with open(infer_linter.OUTPUT_JSON, "r", encoding="utf-8") as rf:
                import json
                summary = json.load(rf)
            score = summary.get("health_score_pct", 0.0)
            self.assertGreaterEqual(score, 0.0, "L8: Health score cannot be negative")
            self.assertLessEqual(score, 100.0, "L8: Health score cannot exceed 100%")


    def test_l9_benign_best_effort_guard_not_flagged(self):
        """L9: Empty catch guarding only best-effort compatibility calls
        (reconfigure/chmod) is an accepted idiom, not a swallowed exception."""
        py_code = """
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8')
                sys.stderr.reconfigure(encoding='utf-8')
            except Exception:
                pass
        try:
            os.chmod(sh_path, 0o755)
        except Exception:
            pass
        """
        res = self._analyze_code(py_code, ".py")
        swallowed = [d for d in res["defects"] if d["type"] == "SWALLOWED_EXCEPTION"]
        self.assertEqual(len(swallowed), 0, "L9: Best-effort reconfigure/chmod guard must not be flagged")

    def test_l10_mixed_try_body_still_flagged(self):
        """L10: Empty catch whose try body mixes benign calls with real logic
        must still be reported as CRITICAL (whitelist must not over-reach)."""
        py_code = """
        try:
            save_report(results)
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
        """
        res = self._analyze_code(py_code, ".py")
        swallowed = [d for d in res["defects"] if d["type"] == "SWALLOWED_EXCEPTION"]
        self.assertTrue(len(swallowed) > 0, "L10: Mixed try body must still be caught")
        self.assertEqual(swallowed[0]["severity"], "CRITICAL")

    def test_l11_page_objects_without_assert_not_flagged(self):
        """L11: Page Objects perform UI interactions but contain zero assertions by Clean POM design.
        Must NOT be flagged as missing assertions."""
        po_code = """
        export class LoginPage extends BasePage {
            async login(u: string, p: string) {
                await this.page.fill('#user', u);
                await this.page.fill('#pass', p);
                await this.page.click('#submit');
            }
        }
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            pages_dir = os.path.join(tmp_dir, "pages")
            os.makedirs(pages_dir, exist_ok=True)
            po_file = os.path.join(pages_dir, "LoginPage.ts")
            with open(po_file, "w", encoding="utf-8") as f:
                f.write(po_code)
            res = infer_linter.analyze_script(po_file)
            self.assertEqual(res["role"], "PAGE_OBJECT")
            self.assertTrue(res["is_clean"], "Page Object with interactions and zero assertions must be clean")
            self.assertEqual(len(res["defects"]), 0)

    def test_l12_config_files_not_flagged(self):
        """L12: Test config files (playwright.config.ts, conftest.py) must be recognized as CONFIG and clean."""
        cfg_code = """
        import { defineConfig } from '@playwright/test';
        export default defineConfig({ timeout: 30000 });
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg_file = os.path.join(tmp_dir, "playwright.config.ts")
            with open(cfg_file, "w", encoding="utf-8") as f:
                f.write(cfg_code)
            res = infer_linter.analyze_script(cfg_file)
            self.assertEqual(res["role"], "CONFIG")
            self.assertTrue(res["is_clean"], "Config file must be clean")

    def test_l13_health_score_reflects_warning_ratio(self):
        """L13: When only 2 out of 6 scripts are clean (e.g. 4 warnings), health score must NOT be 100%."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 2 clean test files with valid dynamic assertions
            for i in range(2):
                fpath = os.path.join(tmp_dir, f"test_clean_{i}.py")
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write("def test_ok():\n    status = 200\n    assert status == 200\n")
            # 4 test files with missing assertions (WARNING)
            for i in range(4):
                fpath = os.path.join(tmp_dir, f"test_warn_{i}.py")
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write("def test_action():\n    client.click('#btn')\n")

            infer_linter.run_infer_linter(tmp_dir)
            with open(infer_linter.OUTPUT_JSON, "r", encoding="utf-8") as rf:
                import json
                summary = json.load(rf)
            score = summary.get("health_score_pct", 0.0)
            self.assertLess(score, 50.0, "Health score must be < 50% when only 2/6 scripts are clean")
            self.assertGreater(score, 0.0, "Health score should be non-zero when some scripts are clean")

    def test_l14_polyglot_hard_delays_detected(self):
        """L14: Detect hard sleep across Playwright (waitForTimeout/wait_for_timeout), Pytest (time.sleep), Cypress (cy.wait), Katalon (WebUI.delay)."""
        cases = [
            ("await page.waitForTimeout(5000);", ".ts", True),
            ("page.wait_for_timeout(4000)", ".py", True),
            ("time.sleep(5)", ".py", True),
            ("time.sleep(3.5)", ".py", True),
            ("cy.wait(5000);", ".js", True),
            ("WebUI.delay(5)", ".groovy", True),
            ("Thread.sleep(3000)", ".java", True),
            # Negative cases: short sleep (< 3s / 3000ms) or Cypress aliased wait
            ("await page.waitForTimeout(500);", ".ts", False),
            ("time.sleep(1)", ".py", False),
            ("cy.wait('@getUsers');", ".js", False),
        ]
        for snippet, ext, should_detect in cases:
            res = self._analyze_code(f"// action\n{snippet}\nassert true", ext)
            delays = [d for d in res["defects"] if d["type"] == "EXCESSIVE_HARD_DELAY"]
            if should_detect:
                self.assertTrue(len(delays) > 0, f"Expected EXCESSIVE_HARD_DELAY for: {snippet}")
                self.assertEqual(delays[0]["severity"], "WARNING")
            else:
                self.assertEqual(len(delays), 0, f"Did NOT expect EXCESSIVE_HARD_DELAY for: {snippet}")

    def test_l15_undistorted_error_messages(self):
        """L15: Defect messages must display raw code with original strings intact, not space-padded."""
        code = """
        import { test, expect } from '@playwright/test';
        test('unawaited', async ({ page }) => {
            expect(page.locator('#submit-button')).toBeVisible();
        });
        """
        res = self._analyze_code(code, ".ts")
        unawaited = [d for d in res["defects"] if d["type"] == "UNAWAITED_ASYNC_ASSERTION"]
        self.assertTrue(len(unawaited) > 0)
        self.assertIn("#submit-button", unawaited[0]["message"], "String literal inside locator must not be blanked out")

    def test_l16_benchmark_role_classification_and_catch_continue(self):
        """L16: Benchmark scripts classified as HELPER; explicit loop continue in catch is not swallowed."""
        # 1. Classification
        self.assertEqual(infer_linter.classify_file_role("benchmarks/qa_eval/build_dataset.py"), "HELPER")
        self.assertEqual(infer_linter.classify_file_role("benchmarks/eval_runner.py"), "HELPER")
        
        # 2. Loop continue in catch is deliberate flow control, not empty catch
        js_code = """
        for (const cmd of candidates) {
            try {
                exec(cmd);
            } catch {
                continue;
            }
        }
        """
        res = self._analyze_code(js_code, ".js")
        swallowed = [d for d in res["defects"] if d["type"] == "SWALLOWED_EXCEPTION"]
        self.assertEqual(len(swallowed), 0, "Loop continue in catch must not be flagged as swallowed exception")


if __name__ == "__main__":
    unittest.main()
