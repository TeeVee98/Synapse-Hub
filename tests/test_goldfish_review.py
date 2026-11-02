#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

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


if __name__ == "__main__":
    unittest.main()
