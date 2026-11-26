#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Unit Tests for infer_linter.py verifying the 8 Golden Test Cases (L1 - L8)
from Enterprise QA Hub roadmap.
"""

import json
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
            infer_linter.run_infer_linter(tmp_dir)
            report_file = os.path.join(tmp_dir, "reports", "infer_linter_report.json")
            with open(report_file, "r", encoding="utf-8") as rf:
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
            report_file = os.path.join(tmp_dir, "reports", "infer_linter_report.json")
            with open(report_file, "r", encoding="utf-8") as rf:
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
                self.assertEqual(delays[0]["severity"], "CRITICAL")
            else:
                self.assertEqual(len(delays), 0, f"Did NOT expect EXCESSIVE_HARD_DELAY for: {snippet}")

    def test_l17_dangling_expect_and_tautology_cases(self):
        """L17: Verify the 3 critical flaw cases:
        1. expect(page) with no matcher is caught as DANGLING_ASSERTION_NO_MATCHER.
        2. assert len(x) >= 0 is caught as TAUTOLOGICAL_ASSERTION.
        3. assert f() == f() is caught as TAUTOLOGICAL_ASSERTION.
        4. sleep < 3000ms is caught as HARD_DELAY_ANTI_PATTERN with WARNING."""
        # 1. expect(page) with no matcher in TS and Python
        res_dangling_ts = self._analyze_code("expect(page);\n", ".ts")
        dangling_ts = [d for d in res_dangling_ts["defects"] if d["type"] == "DANGLING_ASSERTION_NO_MATCHER"]
        self.assertTrue(len(dangling_ts) > 0, "Dangling expect(page) in TS must be caught")
        self.assertEqual(dangling_ts[0]["severity"], "CRITICAL")

        res_dangling_py = self._analyze_code("expect(page)\n", ".py")
        dangling_py = [d for d in res_dangling_py["defects"] if d["type"] == "DANGLING_ASSERTION_NO_MATCHER"]
        self.assertTrue(len(dangling_py) > 0, "Dangling expect(page) in Python must be caught via AST")
        self.assertEqual(dangling_py[0]["severity"], "CRITICAL")

        # 2. assert len(x) >= 0 in Python
        res_len = self._analyze_code("assert len(x) >= 0\n", ".py")
        taut_len = [d for d in res_len["defects"] if d["type"] == "TAUTOLOGICAL_ASSERTION"]
        self.assertTrue(len(taut_len) > 0, "assert len(x) >= 0 must be caught as TAUTOLOGICAL_ASSERTION")

        # 3. assert f() == f() in Python and TS/JS
        res_func_py = self._analyze_code("assert f() == f()\n", ".py")
        taut_func_py = [d for d in res_func_py["defects"] if d["type"] == "TAUTOLOGICAL_ASSERTION"]
        self.assertTrue(len(taut_func_py) > 0, "assert f() == f() must be caught as TAUTOLOGICAL_ASSERTION")

        # 4. Short sleep (< 3000ms) triggers HARD_DELAY_ANTI_PATTERN with WARNING
        res_short = self._analyze_code("time." + "sleep(1)\nassert 1 == 2\n", ".py")
        short_delays = [d for d in res_short["defects"] if d["type"] == "HARD_DELAY_ANTI_PATTERN"]
        self.assertTrue(len(short_delays) > 0, "Sleep < 3000ms must be flagged as HARD_DELAY_ANTI_PATTERN")
        self.assertEqual(short_delays[0]["severity"], "WARNING")

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

    def test_l17_unpaired_data_creation_detected(self):
        """L17: Test data creation without paired teardown cleanup must be flagged as ORPHAN_DATA_RISK."""
        unpaired_code = """
        def test_order_creation():
            uid = uniqueCode("ORD_")
            create_customer({"name": "VIP", "id": uid})
            assert uid is not None
        """
        res_bad = self._analyze_code(unpaired_code, ".py")
        orphan_defects = [d for d in res_bad["defects"] if d["type"] == "ORPHAN_DATA_RISK"]
        self.assertTrue(len(orphan_defects) > 0, "Unpaired data creation without teardown must be flagged")

        paired_code = """
        def test_order_creation_clean():
            uid = uniqueCode("ORD_")
            try:
                create_customer({"name": "VIP", "id": uid})
                assert uid is not None
            finally:
                delete_customer(uid)
        """
        res_good = self._analyze_code(paired_code, ".py")
        orphan_good = [d for d in res_good["defects"] if d["type"] == "ORPHAN_DATA_RISK"]
        self.assertEqual(len(orphan_good), 0, "Paired data creation with finally/teardown must not be flagged")

    def test_l18_asyncio_sleep_and_playwright_wait_for_timeout(self):
        """L18 / Boost B6: Catches asyncio.sleep and page.waitForTimeout as static delays."""
        # 1. asyncio.sleep in python test script
        py_code = """
        import asyncio
        async def test_async_flow():
            await asyncio.sleep(5)
            assert True
        """
        res_py = self._analyze_code(py_code, ".py")
        delays_py = [d for d in res_py["defects"] if "DELAY" in d["type"]]
        self.assertTrue(len(delays_py) > 0, "asyncio.sleep must be caught as hard delay")

        # 2. page.waitForTimeout in Playwright TypeScript test script
        ts_code = """
        import { test, expect } from '@playwright/test';
        test('static wait violation', async ({ page }) => {
            await page.waitForTimeout(4000);
            await expect(page.locator('#btn')).toBeVisible();
        });
        """
        res_ts = self._analyze_code(ts_code, ".ts")
        delays_ts = [d for d in res_ts["defects"] if "DELAY" in d["type"]]
        self.assertTrue(len(delays_ts) > 0, "page.waitForTimeout must be caught as hard delay")

    def test_l19_dummy_variable_swallowed_exception(self):
        """L19: Catches dummy variable suppressions like `_ = err`, `_ = e`, `_ = False`, `const _ = err;` as CRITICAL."""
        # 1. Python dummy suppression with except Exception as err: _ = err
        py_code_err = """
        try:
            do_risky_task()
        except Exception as err:
            _ = err
        """
        res_py = self._analyze_code(py_code_err, ".py")
        swallowed = [d for d in res_py["defects"] if d["type"] == "SWALLOWED_EXCEPTION"]
        self.assertTrue(len(swallowed) > 0, "Python `_ = err` must be caught as SWALLOWED_EXCEPTION")
        self.assertEqual(swallowed[0]["severity"], "CRITICAL")

        # 2. Python dummy suppression with except Exception: _ = False
        py_code_false = """
        try:
            do_risky_task()
        except Exception:
            _ = False
        """
        res_py_false = self._analyze_code(py_code_false, ".py")
        swallowed_false = [d for d in res_py_false["defects"] if d["type"] == "SWALLOWED_EXCEPTION"]
        self.assertTrue(len(swallowed_false) > 0, "Python `_ = False` in except must be caught as SWALLOWED_EXCEPTION")

        # 3. TS dummy suppression with const _ = e;
        ts_code = """
        try {
            await page.click('#submit');
        } catch (e) {
            const _ = e;
        }
        """
        res_ts = self._analyze_code(ts_code, ".ts")
        swallowed_ts = [d for d in res_ts["defects"] if d["type"] == "SWALLOWED_EXCEPTION"]
        self.assertTrue(len(swallowed_ts) > 0, "TS `const _ = e;` must be caught as SWALLOWED_EXCEPTION")
        self.assertEqual(swallowed_ts[0]["severity"], "CRITICAL")

        # 4. Legitimate exception handling (logging or re-raise or returning fallback) is NOT flagged
        good_py = """
        try:
            val = parse_json()
        except ValueError:
            return None
        """
        res_good = self._analyze_code(good_py, ".py")
        swallowed_good = [d for d in res_good["defects"] if d["type"] == "SWALLOWED_EXCEPTION"]
        self.assertEqual(len(swallowed_good), 0, "Legitimate return in except block must NOT be flagged")

    def test_strict_mode_rejects_sub_3000ms_static_sleep(self):
        """Verifies that infer_linter with strict=True rejects sub-3000ms sleeps (HARD_DELAY_ANTI_PATTERN)."""
        with tempfile.TemporaryDirectory() as td:
            test_file = os.path.join(td, "test_sleep.py")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("import time\ndef test_sleep():\n    time.sleep(1)\n    assert True\n")
            exit_code = infer_linter.run_infer_linter(target_dir=td, strict=True)
            self.assertEqual(exit_code, 1, "infer_linter in strict mode must reject static sleeps with exit code 1")

    def test_baseline_line_specific_suppression_prevents_carte_blanche(self):
        """Verifies that baseline suppression is line-specific and does not give whole-file carte blanche."""
        with tempfile.TemporaryDirectory() as td:
            test_file = os.path.join(td, "target.py")
            code = (
                "def func1():\n"
                "    try: pass\n"
                "    except Exception: pass\n"
                "\n"
                "def func2():\n"
                "    try: pass\n"
                "    except Exception:\n"
                "        _ = False\n"
            )
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(code)

            baseline_path = os.path.join(td, "baseline.json")
            with open(baseline_path, "w", encoding="utf-8") as f:
                json.dump({
                    "defects": [
                        {"file": test_file, "type": "SWALLOWED_EXCEPTION", "line": 3}
                    ]
                }, f)

            baseline_set = infer_linter.load_baseline(baseline_path)
            res = infer_linter.analyze_script(test_file, baseline_set=baseline_set)

            active_lines = [d["line"] for d in res["defects"]]
            self.assertNotIn(3, active_lines, "Line 3 must be suppressed by baseline")
            self.assertIn(7, active_lines, "Line 7 must NOT be suppressed by whole-file immunity")

    def test_js_ts_backtick_hash_selector_unawaited_expect_caught(self):
        """Regression (P0-4): JS/TS template literal containing '#id' must not be truncated as a hash comment."""
        code = (
            "import { test, expect } from '@playwright/test';\n"
            "test('checkout submit', async ({ page }) => {\n"
            "    expect(page.locator(`#submit-btn`)).toBeVisible();\n"
            "});\n"
        )
        res = self._analyze_code(code, ".ts")
        unawaited = [d for d in res["defects"] if d["type"] == "UNAWAITED_ASYNC_ASSERTION"]
        self.assertEqual(len(unawaited), 1, f"Expected unawaited assertion on backtick #id selector, got: {res['defects']}")
        self.assertEqual(unawaited[0]["line"], 3)

    def test_js_ts_backtick_hash_selector_dangling_expect_caught(self):
        """Regression (P0-4): Dangling expect(page.locator(`#id`)); must be caught in .ts."""
        code = (
            "import { test, expect } from '@playwright/test';\n"
            "test('dangling backtick', async ({ page }) => {\n"
            "    expect(page.locator(`#submit-btn`));\n"
            "});\n"
        )
        res = self._analyze_code(code, ".ts")
        dangling = [d for d in res["defects"] if d["type"] == "DANGLING_ASSERTION_NO_MATCHER"]
        self.assertEqual(len(dangling), 1, f"Expected DANGLING_ASSERTION_NO_MATCHER, got: {res['defects']}")

    def test_js_ts_backtick_apostrophe_preserves_subsequent_code(self):
        """Regression (P0-4): Apostrophe inside template literal (`User's cart`) must not swallow following lines."""
        code = (
            "import { test, expect } from '@playwright/test';\n"
            "test('apostrophe template', async ({ page }) => {\n"
            "    const label = `User's cart #42`;\n"
            "    expect(page.locator('#checkout-btn')).toBeVisible();\n"
            "});\n"
        )
        clean = infer_linter.strip_comments_and_strings(code, preserve_newlines=True, file_ext=".ts")
        self.assertEqual(len(clean.splitlines()), len(code.splitlines()))
        res = self._analyze_code(code, ".ts")
        unawaited = [d for d in res["defects"] if d["type"] == "UNAWAITED_ASYNC_ASSERTION"]
        self.assertEqual(len(unawaited), 1, f"Expected unawaited assertion after apostrophe template, got: {res['defects']}")
        self.assertEqual(unawaited[0]["line"], 4)

    def test_default_discovery_skips_packaging_scripts_and_artifact_dirs(self):
        """P1-4: Default discovery avoids Hub packaging scripts/ and ignores test-results/playwright-report."""
        with tempfile.TemporaryDirectory() as td:
            # Lowercase packaging scripts/ should not be treated as Katalon Scripts/
            pkg_scripts = os.path.join(td, "scripts")
            os.makedirs(pkg_scripts, exist_ok=True)
            with open(os.path.join(pkg_scripts, "build_dist.py"), "w", encoding="utf-8") as f:
                f.write("print('build')\n")

            hub_core = os.path.join(td, "tools", "core")
            os.makedirs(hub_core, exist_ok=True)
            with open(os.path.join(hub_core, "verify_all.py"), "w", encoding="utf-8") as f:
                f.write("# hub marker\n")

            ex_suite = os.path.join(td, "examples", "crm", "tests")
            os.makedirs(ex_suite, exist_ok=True)
            with open(os.path.join(ex_suite, "auth.spec.ts"), "w", encoding="utf-8") as f:
                f.write("import { test, expect } from '@playwright/test';\ntest('ok', async ({ page }) => { await expect(page).toHaveURL(/dash/); });\n")

            junk_dir = os.path.join(td, "examples", "crm", "test-results")
            os.makedirs(junk_dir, exist_ok=True)
            with open(os.path.join(junk_dir, "bad.spec.ts"), "w", encoding="utf-8") as f:
                f.write("expect(true).toBe(true);\n")

            report_out = os.path.join(td, "lint_out.json")
            rc = infer_linter.run_infer_linter(output_path=report_out, repo_root=td)
            self.assertEqual(rc, 0)
            with open(report_out, "r", encoding="utf-8") as rf:
                data = json.load(rf)
            self.assertEqual(data["total_scripts"], 1)
            self.assertEqual(data["clean_scripts"], 1)
            self.assertEqual(data["critical_defects"], 0)
            self.assertEqual(data["defect_details"], [])

            # Negative: Client repo with lowercase scripts/ + tests/ ignores scripts/ and scans tests/
            client_td = os.path.join(td, "client_repo")
            os.makedirs(os.path.join(client_td, "scripts"), exist_ok=True)
            os.makedirs(os.path.join(client_td, "tests"), exist_ok=True)
            with open(os.path.join(client_td, "scripts", "helper.py"), "w", encoding="utf-8") as f:
                f.write("print('helper')\n")
            with open(os.path.join(client_td, "tests", "test_bad.py"), "w", encoding="utf-8") as f:
                f.write("def test_fail():\n    try:\n        run_step()\n    except Exception:\n        pass\n")
            client_out = os.path.join(td, "client_out.json")
            client_rc = infer_linter.run_infer_linter(output_path=client_out, repo_root=client_td)
            self.assertEqual(client_rc, 1)
            with open(client_out, "r", encoding="utf-8") as cf:
                cdata = json.load(cf)
            self.assertEqual(cdata["total_scripts"], 1)
            self.assertEqual(cdata["critical_defects"], 1)

    def test_v5_cross_file_ts_and_java_pom_assertions_zero_false_positives(self):
        """M3: Cross-file TS & Java POM assertion helpers yield 0 false positives while action-only calls still fail."""
        with tempfile.TemporaryDirectory() as td:
            pages_dir = os.path.join(td, "pages")
            tests_dir = os.path.join(td, "tests")
            os.makedirs(pages_dir, exist_ok=True)
            os.makedirs(tests_dir, exist_ok=True)

            # TS Page Object with non-verify-prefixed assertion method + action-only method
            with open(os.path.join(pages_dir, "CheckoutPage.ts"), "w", encoding="utf-8") as f:
                f.write(
                    "import { expect, Page } from '@playwright/test';\n"
                    "export class CheckoutPage {\n"
                    "  constructor(private page: Page) {}\n"
                    "  async confirmOrderComplete() {\n"
                    "    await expect(this.page.locator('#receipt')).toBeVisible();\n"
                    "  }\n"
                    "  async clickSubmit() {\n"
                    "    await this.page.click('#submit');\n"
                    "  }\n"
                    "}\n"
                )

            # Clean TS spec calling POM assertion helper (non-verify name)
            clean_ts = os.path.join(tests_dir, "checkout_ok.spec.ts")
            with open(clean_ts, "w", encoding="utf-8") as f:
                f.write(
                    "import { test } from '@playwright/test';\n"
                    "import { CheckoutPage } from '../pages/CheckoutPage';\n"
                    "test('order succeeds', async ({ page }) => {\n"
                    "  const checkoutPage = new CheckoutPage(page);\n"
                    "  await checkoutPage.clickSubmit();\n"
                    "  await checkoutPage.confirmOrderComplete();\n"
                    "});\n"
                )

            # Fake-pass TS spec calling ONLY action helper
            fake_ts = os.path.join(tests_dir, "checkout_fake.spec.ts")
            with open(fake_ts, "w", encoding="utf-8") as f:
                f.write(
                    "import { test } from '@playwright/test';\n"
                    "import { CheckoutPage } from '../pages/CheckoutPage';\n"
                    "test('fake pass', async ({ page }) => {\n"
                    "  const checkoutPage = new CheckoutPage(page);\n"
                    "  await checkoutPage.clickSubmit();\n"
                    "});\n"
                )

            # Java Page Object + Test
            with open(os.path.join(pages_dir, "DashboardPage.java"), "w", encoding="utf-8") as f:
                f.write(
                    "import static org.junit.jupiter.api.Assertions.assertTrue;\n"
                    "public class DashboardPage {\n"
                    "  public void ensureHeaderReady() {\n"
                    "    assertTrue(isVisible());\n"
                    "  }\n"
                    "}\n"
                )
            java_test = os.path.join(tests_dir, "DashboardTest.java")
            with open(java_test, "w", encoding="utf-8") as f:
                f.write(
                    "public class DashboardTest {\n"
                    "  @Test public void testDashboard() {\n"
                    "    dashboardPage.open();\n"
                    "    dashboardPage.ensureHeaderReady();\n"
                    "  }\n"
                    "}\n"
                )

            res_clean = infer_linter.analyze_script(clean_ts)
            self.assertTrue(res_clean["is_clean"], f"Expected 0 false positives, got: {res_clean['defects']}")
            self.assertGreaterEqual(res_clean["cross_file_assertions_resolved"], 1)

            res_fake = infer_linter.analyze_script(fake_ts)
            fake_types = [d["type"] for d in res_fake["defects"]]
            self.assertIn("FAKE_PASS_NO_ASSERTION", fake_types)

            res_java = infer_linter.analyze_script(java_test)
            self.assertTrue(res_java["is_clean"], f"Expected Java POM test clean, got: {res_java['defects']}")

    def test_v5_multiline_expect_chains_and_defects(self):
        """M3: Multiline awaited expect chains are clean; multiline unawaited or dangling expects are caught."""
        valid_multiline = (
            "import { test, expect } from '@playwright/test';\n"
            "test('multiline valid', async ({ page }) => {\n"
            "  await page.click('#calc');\n"
            "  await expect(\n"
            "    page.locator('#total')\n"
            "  )\n"
            "    .toHaveText('$42.00');\n"
            "});\n"
        )
        res_ok = self._analyze_code(valid_multiline, ".ts")
        self.assertTrue(res_ok["is_clean"], f"Multiline awaited expect should be clean: {res_ok['defects']}")

        unawaited_multiline = (
            "import { test, expect } from '@playwright/test';\n"
            "test('multiline unawaited', async ({ page }) => {\n"
            "  expect(\n"
            "    page.locator('#banner')\n"
            "  ).toBeVisible();\n"
            "});\n"
        )
        res_unawaited = self._analyze_code(unawaited_multiline, ".ts")
        self.assertIn("UNAWAITED_ASYNC_ASSERTION", [d["type"] for d in res_unawaited["defects"]])

        dangling_multiline = (
            "import { test, expect } from '@playwright/test';\n"
            "test('multiline dangling', async ({ page }) => {\n"
            "  expect(\n"
            "    page.locator('#banner')\n"
            "  );\n"
            "});\n"
        )
        res_dangling = self._analyze_code(dangling_multiline, ".ts")
        self.assertIn("DANGLING_ASSERTION_NO_MATCHER", [d["type"] for d in res_dangling["defects"]])


if __name__ == "__main__":
    unittest.main()
