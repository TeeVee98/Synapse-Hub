#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Unit Tests for Auto-Fix and Mentorship Diagnostic capabilities
in Synapse Hub (tools/lint/auto_fixer.py, infer_linter.py, health_scorecard.py).
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

from tools.lint.auto_fixer import (
    fix_hard_delays,
    fix_unawaited_expect,
    fix_swallowed_exceptions,
    fix_dangling_expects,
    generate_fixes_for_code,
    apply_file_fix
)
from tools.lint.infer_linter import format_mentorship_card
from tools.report.health_scorecard import generate_html_scorecard


class TestAutoFixer(unittest.TestCase):
    """Verifies all auto-fix transformations and dry-run safety."""

    def test_fix_hard_delays_ts_playwright(self):
        """Replaces static waitForTimeout with dynamic waitForLoadState."""
        code = "    await page.waitForTimeout(5000);"
        updated, fixes = fix_hard_delays(code, ".ts")
        self.assertIn("page.waitForLoadState('domcontentloaded');", updated)
        self.assertTrue(len(fixes) > 0)

    def test_fix_hard_delays_python_playwright(self):
        """Replaces page.wait_for_timeout with wait_for_load_state."""
        code = "    page.wait_for_timeout(3000)"
        updated, fixes = fix_hard_delays(code, ".py")
        self.assertIn("page.wait_for_load_state('domcontentloaded')", updated)
        self.assertTrue(len(fixes) > 0)

    def test_fix_unawaited_expect_ts(self):
        """Prepends missing 'await ' to Playwright async assertions."""
        code = "    expect(page.locator('#dashboard')).toBeVisible();"
        updated, fixes = fix_unawaited_expect(code, ".ts")
        self.assertIn("await expect(page.locator('#dashboard')).toBeVisible();", updated)
        self.assertTrue(len(fixes) > 0)

    def test_fix_swallowed_exception_ts(self):
        """Converts empty catch block into explicit rethrow."""
        code = "    try { await doSomething(); } catch (err) {}"
        updated, fixes = fix_swallowed_exceptions(code, ".ts")
        self.assertIn("catch (err) {\n    throw err;\n  }", updated)
        self.assertTrue(len(fixes) > 0)

    def test_fix_swallowed_exception_python(self):
        """Converts except: pass into raise err."""
        code = "    try:\n        do_something()\n    except:\n        pass"
        updated, fixes = fix_swallowed_exceptions(code, ".py")
        self.assertIn("raise err", updated)
        self.assertTrue(len(fixes) > 0)

    def test_fix_dangling_expect_ts(self):
        """Appends .toBeVisible() to dangling expect() call."""
        code = "    expect(page.locator('#btn'));"
        updated, fixes = fix_dangling_expects(code, ".ts")
        self.assertIn("expect(page.locator('#btn')).toBeVisible();", updated)
        self.assertTrue(len(fixes) > 0)

    def test_generate_fixes_for_code_multi_violation(self):
        """generate_fixes_for_code applies multiple fixes and returns unified diff."""
        code = "expect(btn);\npage.waitForTimeout(1000);"
        new_code, fixes, diff_str = generate_fixes_for_code(code, "test.spec.ts")
        self.assertIn("expect(btn).toBeVisible();", new_code)
        self.assertIn("waitForLoadState", new_code)
        self.assertEqual(len(fixes), 2)
        self.assertTrue(len(diff_str) > 0)

    def test_dry_run_does_not_modify_file(self):
        """Dry-run must return diff without touching file on disk."""
        sample_code = "await page.waitForTimeout(5000);"
        with tempfile.NamedTemporaryFile("w", suffix=".spec.ts", delete=False, encoding="utf-8") as f:
            f.write(sample_code)
            tmp_path = f.name

        try:
            res = apply_file_fix(tmp_path, dry_run=True)
            self.assertTrue(res["fixed"])
            self.assertTrue(res["dry_run"])
            self.assertIn("waitForLoadState", res["diff"])

            # Verify file content is unchanged
            with open(tmp_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertEqual(content, sample_code)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_apply_fix_modifies_file_and_creates_backup(self):
        """Normal fix must modify file and create .bak backup."""
        sample_code = "await page.waitForTimeout(5000);"
        with tempfile.NamedTemporaryFile("w", suffix=".spec.ts", delete=False, encoding="utf-8") as f:
            f.write(sample_code)
            tmp_path = f.name

        try:
            res = apply_file_fix(tmp_path, dry_run=False, create_backup=True)
            self.assertTrue(res["fixed"])
            self.assertFalse(res["dry_run"])

            # Verify backup exists
            bak_path = tmp_path + ".bak"
            self.assertTrue(os.path.exists(bak_path))
            with open(bak_path, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), sample_code)

            # Verify target file is updated
            with open(tmp_path, "r", encoding="utf-8") as f:
                new_content = f.read()
            self.assertIn("waitForLoadState", new_content)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if os.path.exists(tmp_path + ".bak"):
                os.remove(tmp_path + ".bak")


class TestMentorshipAndScorecard(unittest.TestCase):
    """Verifies UX/TX reporting and diagnostic cards."""

    def test_format_mentorship_card_bilingual(self):
        """Mentorship card contains both Vietnamese and English explanations."""
        defect = {
            "type": "EXCESSIVE_HARD_DELAY",
            "severity": "CRITICAL",
            "line": 42,
            "message": "Static sleep of 5000ms found."
        }
        card = format_mentorship_card(defect, "tests/auth.spec.ts")
        self.assertIn("EXCESSIVE_HARD_DELAY", card)
        self.assertIn("tests/auth.spec.ts:42", card)
        self.assertIn("Hard sleep làm test chạy chậm", card)
        self.assertIn("Static sleep causes slow test", card)
        self.assertIn("waitForLoadState", card)

    def test_generate_html_scorecard_offline_validity(self):
        """HTML scorecard contains SVG radar, KPI metrics, and zero external script tags."""
        report_data = {
            "timestamp": "2026-11-20T10:00:00",
            "total_scripts": 10,
            "clean_scripts": 9,
            "critical_defects": 1,
            "warnings": 0,
            "health_score_pct": 90.0,
            "all_defects": [
                {
                    "file": "tests/login.spec.ts",
                    "line": 15,
                    "type": "SWALLOWED_EXCEPTION",
                    "severity": "CRITICAL",
                    "message": "Empty catch block hides errors."
                }
            ]
        }
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
            tmp_html = f.name

        try:
            html = generate_html_scorecard(report_data, tmp_html)
            self.assertIn("Synapse Hub — Executive Test Quality Scorecard", html)
            self.assertIn("<svg", html)
            self.assertIn("polygon", html)
            self.assertIn("90.0%", html)
            self.assertIn("tests/login.spec.ts:15", html)
            self.assertNotIn("<script src=\"http", html)  # Must be 100% offline
        finally:
            if os.path.exists(tmp_html):
                os.remove(tmp_html)


if __name__ == "__main__":
    unittest.main()
