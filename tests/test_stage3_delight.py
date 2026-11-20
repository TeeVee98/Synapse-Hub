#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Unit tests for Stage 3 capabilities:
1. Interactive Failure Autopsy Report Generator (tools/report/failure_autopsy.py).
2. Manual QC-to-Automation Transpiler (tools/design/testcase_transpiler.py).
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

from tools.report.failure_autopsy import classify_failure, generate_failure_autopsy_html, read_code_frame
from tools.design.testcase_transpiler import (
    parse_markdown_testcase,
    transpile_to_playwright_ts,
    transpile_file
)


class TestFailureAutopsy(unittest.TestCase):
    """Verifies Root Cause Analysis and HTML Autopsy generation."""

    def test_classify_failure_assertion(self):
        res = classify_failure("AssertionError: expect(received).toBe(expected)")
        self.assertEqual(res["category"], "ASSERTION_MISMATCH")
        self.assertIn("Kỳ vọng kiểm thử không khớp", res["rca_vi"])

    def test_classify_failure_timeout(self):
        res = classify_failure("TimeoutError: locator.waitFor: Timeout 5000ms exceeded")
        self.assertEqual(res["category"], "LOCATOR_TIMEOUT")
        self.assertIn("Hết thời gian chờ", res["rca_vi"])

    def test_classify_failure_click_intercepted(self):
        res = classify_failure("Element <button> is not clickable at point (100, 200). Another element obscures it")
        self.assertEqual(res["category"], "CLICK_INTERCEPTED")
        self.assertIn("bị chặn bởi phần tử khác", res["rca_vi"])

    def test_generate_failure_autopsy_html_offline(self):
        failures = [
            {
                "tc": "TC_LOGIN_001",
                "time": "1.2s",
                "reason": "AssertionError: expect(locator).toBeVisible() failed",
                "failed_at": ["tests/login.spec.ts:42"],
                "file": "tests/login.spec.ts",
                "line": "42"
            }
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
            tmp_path = f.name

        try:
            html = generate_failure_autopsy_html(failures, "reports/junit.xml", tmp_path)
            self.assertIn("Failure Autopsy & RCA", html)
            self.assertIn("TC_LOGIN_001", html)
            self.assertIn("ASSERTION_MISMATCH", html)
            self.assertNotIn("<script src=\"http", html)  # 100% offline
            self.assertTrue(os.path.isfile(tmp_path))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_read_code_frame(self):
        with tempfile.NamedTemporaryFile("w", suffix=".ts", delete=False, encoding="utf-8") as f:
            f.write("line 1\nline 2\nline 3\nline 4\nline 5\n")
            tmp_ts = f.name
        try:
            frames = read_code_frame(tmp_ts, "3", window=1)
            self.assertIsNotNone(frames)
            self.assertEqual(len(frames), 3)
            self.assertTrue(any(fr["line"] == 3 and fr["is_target"] for fr in frames))
        finally:
            if os.path.exists(tmp_ts):
                os.remove(tmp_ts)


class TestTestCaseTranspiler(unittest.TestCase):
    """Verifies Manual QC Markdown to Clean POM code synthesis."""

    def test_parse_markdown_testcase(self):
        md = """# User Login Workflow
**Precondition:** Mở trang đăng nhập /login

## Các bước thực hiện:
1. Nhập username "standard_user" vào ô username
2. Nhập password "secret_sauce" vào ô password
3. Nhấp vào nút "Đăng nhập"

## Kết quả mong đợi:
- Dashboard hiển thị thành công
"""
        tc = parse_markdown_testcase(md)
        self.assertEqual(tc["title"], "User Login Workflow")
        self.assertEqual(len(tc["steps"]), 3)
        self.assertEqual(len(tc["expectations"]), 1)

    def test_transpile_to_playwright_ts_clean_pom(self):
        tc = {
            "title": "Checkout Payment Flow",
            "steps": [
                'Nhập "admin" vào ô username',
                'Nhấp vào nút "Checkout"'
            ],
            "expectations": [
                'Invoice is displayed'
            ]
        }
        page_code, page_name, spec_code, spec_name = transpile_to_playwright_ts(tc)

        self.assertEqual(page_name, "CheckoutPaymentFlowPage.ts")
        self.assertEqual(spec_name, "checkoutpaymentflow.spec.ts")

        # Page Object assertions
        self.assertIn("export class CheckoutPaymentFlowPage", page_code)
        self.assertIn("async enterUsername", page_code)
        self.assertIn("async clickButton2", page_code)
        self.assertIn("async verifyInvoice", page_code)

        # Spec assertions: Flat architecture, no raw selectors
        self.assertIn("import { CheckoutPaymentFlowPage }", spec_code)
        self.assertIn("checkoutpaymentflowpage.enterUsername(\"admin\");", spec_code)
        self.assertIn("checkoutpaymentflowpage.verifyInvoice();", spec_code)
        self.assertNotIn('page.locator("//', spec_code)  # No raw XPath in test script
        self.assertNotIn('xpath=', spec_code)

    def test_transpile_file_creates_files_on_disk(self):
        md = """# Password Reset Flow

## Steps:
1. Fill "user@example.com" in email field
2. Click "Send Reset Link" button

## Expected:
- Success banner is visible
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_md = os.path.join(tmp_dir, "testcase.md")
            with open(input_md, "w", encoding="utf-8") as f:
                f.write(md)

            res = transpile_file(input_md, tmp_dir)
            self.assertTrue(os.path.isfile(res["page_path"]))
            self.assertTrue(os.path.isfile(res["spec_path"]))
            with open(res["spec_path"], "r", encoding="utf-8") as f:
                spec_content = f.read()
            self.assertIn("PasswordResetFlowPage", spec_content)


if __name__ == "__main__":
    unittest.main()
