#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Golden Unit Tests for tools/goldfish_review.py (Zero-Context Spec Auditor)
--------------------------------------------------------------------------
Validates:
  1. Empty or whitespace-only specification rejection
  2. Vague assertion penalty ("works properly", "hệ thống hoạt động bình thường")
  3. Dynamic data and teardown requirement verification
  4. Boundary and negative scenario coverage
  5. Implementation target detection (Page Classes, endpoints)
  6. Comprehensive spec passing readiness threshold (>= 80%)
"""

import os
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import goldfish_review as gr


class TestGoldfishReview(unittest.TestCase):

    def test_empty_content_rejected(self):
        result = gr.evaluate_spec_content("", "empty.md")
        self.assertEqual(result["score"], 0)
        self.assertFalse(result["passed"])
        self.assertEqual(result["status"], "REJECTED")
        self.assertGreaterEqual(result["findings_count"], 1)

    def test_vague_assertions_penalty(self):
        vague_spec = """
# Feature: User Login
As a user, I want to login.
When I enter credentials, everything works fine and page opens as expected.
"""
        result = gr.evaluate_spec_content(vague_spec, "vague.md")
        self.assertFalse(result["passed"])
        rigor_findings = [f for f in result["findings"] if f["vector"] == "Assertion Rigor"]
        self.assertTrue(len(rigor_findings) > 0)
        self.assertTrue(any("vague assertion phrase" in f["message"].lower() for f in rigor_findings))

    def test_hardcoded_data_warning(self):
        hardcoded_spec = """
# Feature: Order Creation
Preconditions: Given user is logged in as "demo1" with id: "12345"
When user creates an invoice
Then invoice is created.
"""
        result = gr.evaluate_spec_content(hardcoded_spec, "hardcoded.md")
        data_findings = [f for f in result["findings"] if f["vector"] == "Data Independence"]
        self.assertTrue(any("detected static/hardcoded credentials" in f["message"].lower() for f in data_findings))

    def test_comprehensive_spec_passed(self):
        robust_spec = """
# Feature: Organization Unit Management
As an Administrator, I need to create and manage organization units.

## Preconditions:
- Given an active Administrator user session.

## Happy Path Scenario:
- Generate uniqueCode with timestamp prefix AUTO_ORG_
- Navigate to OrganizationManagementPage
- Fill organization name with dyn_name and submit form
- Then the system displays notification "Tạo thành công"
- Verify status code is 201
- Assert created organization appears in OrganizationTable

## Boundary & Negative Scenarios:
- Attempt to create organization with empty name -> Verify error "Bắt buộc nhập"
- Attempt duplicate organization code -> Verify rejected with 409 Conflict

## Teardown Cleanup:
- Execute teardown deletion hook after test execution to purge AUTO_ORG_ test fixtures.
"""
        result = gr.evaluate_spec_content(robust_spec, "robust.md")
        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["score"], 80)
        self.assertEqual(result["status"], "APPROVED")

    def test_review_file_not_found(self):
        result = gr.review_file("non_existent_file_xyz.md")
        self.assertEqual(result["status"], "ERROR")
        self.assertFalse(result["passed"])

    def test_review_file_success(self):
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".md", delete=False) as tf:
            tf.write("# Feature: Temporary Test\nPreconditions: Given user\nWhen user navigates to LoginPage\nThen assert status equals 200\nTeardown cleanup afterEach.")
            tmp_path = tf.name

        try:
            result = gr.review_file(tmp_path)
            self.assertEqual(result["file"], tmp_path)
            self.assertIn("score", result)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_brd_mode_passes_without_teardown_or_dom_selectors(self):
        """BRD mode passes clean business specs without requiring teardown hooks or DOM selectors."""
        brd_spec = """
# Feature: Customer Loan Application
As a Retail Customer, I want to apply for a personal loan online so that I can receive funds.

## Preconditions:
- Given the customer has an active verified KYC account and credit score >= 650.

## Business Rules & Acceptance Criteria:
- BR-01: Loan amount must be between 10,000,000 VND and 100,000,000 VND.
- BR-02: Interest rate is fixed at 12% per year for 12 months tenure.
- Acceptance Criteria:
  - When valid application submitted, system verifies applicant eligibility and displays status "Đơn vay đã được phê duyệt thành công".
  - System verifies approval confirmation code contains valid sequence.
  - Assert notification displays "Đã tạo hồ sơ".

## Boundary & Exception Flows:
- If applicant requests loan amount < 10,000,000 VND, system rejects and displays error message "Số tiền vay tối thiểu là 10.000.000 VND".
- If credit score < 650, system rejects with error status "Hồ sơ không đủ điều kiện tín dụng".
"""
        # Under default mode, lacks teardown and PageClass -> penalized
        res_auto = gr.evaluate_spec_content(brd_spec, "loan_brd.md", mode="automation-ready")
        self.assertIn("Implementation Target", res_auto["vector_scores"])

        # Under BRD mode -> exempt from teardown/DOM, evaluates Business Rules & Actor
        res_brd = gr.evaluate_spec_content(brd_spec, "loan_brd.md", mode="brd")
        self.assertEqual(res_brd["mode"], "brd")
        self.assertIn("Business Rules", res_brd["vector_scores"])
        self.assertNotIn("Implementation Target", res_brd["vector_scores"])
        self.assertTrue(res_brd["passed"])
        self.assertGreaterEqual(res_brd["score"], 80)
        self.assertEqual(res_brd["status"], "APPROVED")

    def test_brd_mode_missing_business_rules_finding(self):
        """BRD mode flags missing Business Rules as high severity."""
        sparse_brd = """
# Feature: Simple Screen
Preconditions: Given user is logged in
When user opens dashboard
Then assert visible notification
Boundary: error 404 not found
"""
        res = gr.evaluate_spec_content(sparse_brd, "sparse.md", mode="brd")
        br_findings = [f for f in res["findings"] if f["vector"] == "Business Rules"]
        self.assertTrue(len(br_findings) > 0)


if __name__ == "__main__":
    unittest.main()
