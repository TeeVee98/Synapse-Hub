#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tests/test_ast_engine.py — Unit Tests for Multi-Language AST Analysis Engine
----------------------------------------------------------------------------
Validates AST parsing, comment/string stripping fidelity, and false-positive
rejection across Python, TypeScript/JavaScript, and Groovy test suites.
"""

import unittest
from tools.lint.ast_engine import ASTAnalyzer


class TestASTEngine(unittest.TestCase):

    def setUp(self):
        self.analyzer = ASTAnalyzer()

    def test_strip_comments_and_strings_preserves_lines(self):
        code = (
            "// Line 1: Single line comment with sleep(5000)\n"
            "const x = 'hello sleep(1000) world';\n"
            "/* Line 3: Multi\n"
            "   Line 4: comment */\n"
            "const y = 42;\n"
        )
        stripped = ASTAnalyzer.strip_comments_and_strings(code, language="javascript")
        self.assertEqual(len(code.splitlines()), len(stripped.splitlines()))
        self.assertNotIn("sleep(5000)", stripped)
        self.assertNotIn("hello sleep(1000) world", stripped)
        self.assertIn("const x =", stripped)
        self.assertIn("const y = 42;", stripped)

    def test_python_ast_static_sleep_detection(self):
        code = (
            "import time\n"
            "def test_flaky():\n"
            "    time.sleep(5)\n"
        )
        findings = self.analyzer.analyze_python(code, "test_sample.py")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "EXCESSIVE_HARD_DELAY")
        self.assertEqual(findings[0].line, 3)

    def test_python_ast_bounded_poll_allowed(self):
        code = (
            "import time\n"
            "for _ in range(10):\n"
            "    time.sleep(0.01)\n"
        )
        findings = self.analyzer.analyze_python(code, "test_poll.py")
        self.assertEqual(len(findings), 0)

    def test_python_ast_swallowed_exception(self):
        code = (
            "try:\n"
            "    do_something()\n"
            "except Exception:\n"
            "    pass\n"
        )
        findings = self.analyzer.analyze_python(code, "test_swallow.py")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "SWALLOWED_EXCEPTION")

    def test_python_ast_dummy_assignment_swallowed(self):
        code = (
            "try:\n"
            "    do_something()\n"
            "except OSError as err:\n"
            "    _ = err\n"
        )
        findings = self.analyzer.analyze_python(code, "test_dummy.py")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "SWALLOWED_EXCEPTION")

    def test_python_ast_false_positive_rejection_in_comments_and_strings(self):
        code = (
            "# Rule: Never use time.sleep(10) in tests!\n"
            "message = 'Please avoid time.sleep(5) and except: pass'\n"
            "'''\n"
            "Documentation:\n"
            "except Exception: pass is bad\n"
            "'''\n"
            "def test_clean():\n"
            "    assert 1 == 1\n"
        )
        findings = self.analyzer.analyze_python(code, "test_clean.py")
        self.assertEqual(len(findings), 0)

    def test_ts_js_wait_for_timeout_detection(self):
        code = (
            "test('login', async ({ page }) => {\n"
            "    await page.goto('/login');\n"
            "    await page.waitForTimeout(5000);\n"
            "});\n"
        )
        findings = self.analyzer.analyze_ts_js(code, "login.spec.ts")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "EXCESSIVE_HARD_DELAY")
        self.assertEqual(findings[0].line, 3)

    def test_ts_js_false_positive_in_comments_and_strings(self):
        code = (
            "// DO NOT USE: await page.waitForTimeout(5000);\n"
            "const info = 'Example: await page.waitForTimeout(3000) is banned';\n"
            "/*\n"
            "  Legacy code was: catch (e) {}\n"
            "*/\n"
            "test('clean', async ({ page }) => {\n"
            "    await expect(page.locator('#submit')).toBeVisible();\n"
            "});\n"
        )
        findings = self.analyzer.analyze_ts_js(code, "clean.spec.ts")
        self.assertEqual(len(findings), 0)

    def test_ts_js_empty_catch(self):
        code = (
            "try {\n"
            "    runStep();\n"
            "} catch (e) {}\n"
        )
        findings = self.analyzer.analyze_ts_js(code, "catch.spec.js")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "SWALLOWED_EXCEPTION")

    def test_groovy_delays_and_catches(self):
        code = (
            "WebUI.openBrowser('')\n"
            "WebUI.delay(5)\n"
            "try {\n"
            "    CustomKeywords.'MyKeyword.action'()\n"
            "} catch (Exception e) {}\n"
        )
        findings = self.analyzer.analyze_groovy(code, "Script123.groovy")
        self.assertEqual(len(findings), 2)
        rule_ids = {f.rule_id for f in findings}
        self.assertIn("EXCESSIVE_HARD_DELAY", rule_ids)
        self.assertIn("SWALLOWED_EXCEPTION", rule_ids)

    def test_analyze_file_dispatch(self):
        py_code = "import time\ntime.sleep(2)\n"
        findings = self.analyzer.analyze_file("sample.py", content=py_code)
        self.assertEqual(len(findings), 1)

        ts_code = "await page.waitForTimeout(3000);"
        findings = self.analyzer.analyze_file("sample.ts", content=ts_code)
        self.assertEqual(len(findings), 1)


if __name__ == "__main__":
    unittest.main()
