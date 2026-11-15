#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_distill_log.py — Regression & Quality Gate Suite for Log Distiller 2.0
Verifies zero false passes, robust case-insensitive parsing, exit-code invariants,
budget constraints, and UUID/assertion diff preservation.
"""

import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from distill_log import distill, shrink_tokens
from tools.core.token_estimator import count_tokens


class TestDistillLog(unittest.TestCase):
    """Test suite for Log Distiller 2.0."""

    def test_reproduce_pdf_lowercase_failed(self):
        """Regression test for the bug cited in the Token Assessment PDF: lowercase 'failed'."""
        raw_log = "test_login.py::test_auth failed\nassert response.status_code == 401\n"
        result = distill(raw_log)

        # Must NOT report "ALL TESTS PASSED"
        self.assertNotIn("ALL TESTS PASSED", result)
        # Must detect failure
        self.assertIn("FAILURES", result)
        self.assertIn("assert response.status_code == 401", result)
        self.assertIn("test_login.py::test_auth", result)

    def test_exit_code_zero_clean_pass(self):
        """When exit_code == 0 and no failure patterns exist, report clean pass."""
        raw_log = "Running test suite...\nStep 1 complete\nStep 2 complete\nDone.\n"
        result = distill(raw_log, exit_code=0)

        self.assertIn("ALL TESTS PASSED (Exit Code: 0)", result)
        self.assertNotIn("FAILURES", result)

    def test_exit_code_nonzero_with_no_regex_keywords(self):
        """Truth Anchor: If exit_code != 0, distiller NEVER returns 'ALL TESTS PASSED'."""
        raw_log = "Starting container...\nKilled\n"
        result = distill(raw_log, exit_code=137)

        self.assertNotIn("ALL TESTS PASSED", result)
        self.assertIn("RUNNER_NONZERO_EXIT", result)
        self.assertIn("137", result)

    def test_exit_code_none_unverified_fallback(self):
        """When exit_code is None and no failure keywords match, do NOT assume pass."""
        raw_log = "Build completed without obvious failure keywords.\n"
        result = distill(raw_log, exit_code=None)

        self.assertNotIn("ALL TESTS PASSED", result)
        self.assertIn("NO_FAILURE_SIGNATURE_DETECTED", result)

    def test_playwright_timeout_and_expect_failure(self):
        """Verifies Playwright expect mismatch and timeout extraction."""
        raw_log = (
            "1) [chromium] › tests/login.spec.ts:18:5 › should login successfully\n"
            "   Error: expect(received).toBe(expected) // Object.is equality\n"
            "   Expected: 200\n"
            "   Received: 500\n"
            "   at LoginPage.submit (tests/pages/LoginPage.ts:42:15)\n"
        )
        result = distill(raw_log, exit_code=1)

        self.assertIn("FAILURES DETECTED", result)
        self.assertIn("LoginPage.ts:42", result)
        self.assertIn("Expected: 200", result)
        self.assertIn("Received: 500", result)

    def test_katalon_tc_failure_and_cause(self):
        """Verifies Katalon KRE TC failure and Caused by exception."""
        raw_log = (
            "2026-11-12 10:00:00.123 [INFO] Starting test execution\n"
            "TC-104_CreateCustomer FAILED.\n"
            "Caused by: com.kms.katalon.core.exception.StepFailedException: Unable to click on object\n"
            "at Enterprise.Script104.run(Script104.groovy:35)\n"
        )
        result = distill(raw_log, exit_code=1)

        self.assertIn("Targeted TCs: TC-104_CreateCustomer", result)
        self.assertIn("Script104.groovy:35", result)
        self.assertIn("StepFailedException", result)

    def test_line_budget_enforcement(self):
        """Verifies max_lines budget prevents runaway output."""
        verbose_failures = "\n".join([f"FAILED test_case_{i}: AssertionError on line {i}" for i in range(100)])
        result = distill(verbose_failures, max_lines=25)
        lines = result.splitlines()

        # Output should respect max_lines constraint
        self.assertLessEqual(len(lines), 35)
        self.assertIn("DISTILLER METRICS", result)

    def test_info_log_with_assert_does_not_trigger_failure(self):
        """Verifies informational log statements containing assert/== do not trigger false failures."""
        raw_log = (
            "2026-11-13 10:00:00 [INFO] Starting test suite verification\n"
            "[INFO] expected assert response.status_code == 200 in docs\n"
            "[DEBUG] assert connection pool size == 10\n"
            "Execution completed cleanly.\n"
        )
        result = distill(raw_log, exit_code=0)

        # Must report clean pass, NOT false failure
        self.assertIn("ALL TESTS PASSED (Exit Code: 0)", result)
        self.assertNotIn("FAILURES", result)
        self.assertNotIn("CONFLICTING_SIGNALS", result)

    def test_conflicting_signals_reported_when_exit_zero_has_failures(self):
        """When exit_code == 0 but log contains actual test failure, report CONFLICTING_SIGNALS."""
        raw_log = (
            "test_login.py::test_auth FAILED\n"
            "E   assert 404 == 200\n"
        )
        result = distill(raw_log, exit_code=0)

        self.assertNotIn("ALL TESTS PASSED", result)
        self.assertIn("CONFLICTING_SIGNALS [Exit Code: 0]", result)
        self.assertIn("test_login.py::test_auth", result)

    def test_token_budget_enforcement(self):
        """Verifies token_budget constraint actively truncates large failure payloads and enforces hard cap."""
        verbose_failures = "\n".join([f"FAILED test_case_{i}: AssertionError on line {i} with payload details" for i in range(50)])
        result = distill(verbose_failures, exit_code=1, token_budget=60)

        self.assertIn("constrained by token_budget=60 tokens", result)
        self.assertIn("Truncated: True", result)
        self.assertLessEqual(count_tokens(result), 60, "Entire distilled result must strictly respect token_budget=60")

    def test_token_budget_hard_cap_invariants(self):
        """Audit Hard Invariant: count_tokens(result) <= token_budget across 0, 1, 20, 60, 100, 800 tokens."""
        raw_fail_log = (
            "test_orders.py::test_create_order FAILED\n"
            "E   AssertionError: assert 500 == 200\n"
            "File /app/tests/test_orders.py line 85\n"
            "Stack trace verbose line 1\n"
            "Stack trace verbose line 2\n"
            "Stack trace verbose line 3\n"
            "Stack trace verbose line 4\n"
        )
        raw_clean_log = "Starting suite...\nStep 1 PASS\nStep 2 PASS\nFinished.\n"
        raw_nonzero_log = "Starting container...\nProcess killed by OOM killer\n"
        raw_conflict_log = "test_login.py::test_auth FAILED\nE assert 500 == 200\n"
        raw_pointer = "/tmp/raw_test_failure.log"

        budgets = [0, 1, 10, 20, 35, 60, 100, 250, 800]

        for b in budgets:
            # 1. Failure log with raw pointer
            res_fail = distill(raw_fail_log, exit_code=1, raw_log_path=raw_pointer, token_budget=b)
            tokens_fail = count_tokens(res_fail)
            self.assertLessEqual(tokens_fail, b, f"Failure branch exceeded budget: b={b}, got {tokens_fail}")

            # 2. Clean pass log
            res_clean = distill(raw_clean_log, exit_code=0, raw_log_path=raw_pointer, token_budget=b)
            tokens_clean = count_tokens(res_clean)
            self.assertLessEqual(tokens_clean, b, f"Clean branch exceeded budget: b={b}, got {tokens_clean}")

            # 3. Nonzero exit log with no keyword
            res_nonzero = distill(raw_nonzero_log, exit_code=137, raw_log_path=raw_pointer, token_budget=b)
            tokens_nonzero = count_tokens(res_nonzero)
            self.assertLessEqual(tokens_nonzero, b, f"Nonzero branch exceeded budget: b={b}, got {tokens_nonzero}")

            # 4. Conflicting signals log
            res_conflict = distill(raw_conflict_log, exit_code=0, raw_log_path=raw_pointer, token_budget=b)
            tokens_conflict = count_tokens(res_conflict)
            self.assertLessEqual(tokens_conflict, b, f"Conflict branch exceeded budget: b={b}, got {tokens_conflict}")

            if b == 0:
                self.assertEqual(res_fail, "")
                self.assertEqual(res_clean, "")
                self.assertEqual(res_nonzero, "")
                self.assertEqual(res_conflict, "")

    def test_shrink_tokens_preserves_uuid_and_diff(self):
        """Verifies shrink_tokens does not corrupt UUIDs or assertion diffs."""
        sample = (
            "E   assert 404 == 200\n"
            "Correlation-ID: a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d\n"
            "Internal trace: at node:internal/modules/cjs/loader.js:1234567890abcdef1234567890abcdef\n"
        )
        shrunk = shrink_tokens(sample)

        # UUID must be preserved
        self.assertIn("a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d", shrunk)
        # Assertion diff must be preserved
        self.assertIn("E   assert 404 == 200", shrunk)
        # Long hex internal hash must be replaced with <hash>
        self.assertIn("<hash>", shrunk)

    def test_negative_token_budget_rejected(self):
        """Verifies negative or non-integer token budgets are immediately rejected with ValueError."""
        raw_log = "test_login.py::test_auth FAILED\nE assert 500 == 200\n"

        with self.assertRaises(ValueError) as ctx:
            distill(raw_log, token_budget=-1)
        self.assertIn("token_budget must be a non-negative integer", str(ctx.exception))

        with self.assertRaises(ValueError):
            distill(raw_log, token_budget=-500)

        with self.assertRaises(ValueError):
            distill("Clean log\n", exit_code=0, token_budget=-1)

        with self.assertRaises(ValueError):
            distill("Killed\n", exit_code=137, token_budget=-1)

        with self.assertRaises(ValueError):
            distill(raw_log, token_budget=True)  # type: ignore

    def test_cli_negative_token_budget_rejected(self):
        """Verifies CLI rejects negative token-budget via argparse validation."""
        import subprocess

        cmd = [sys.executable, os.path.join(REPO_ROOT, "tools", "distill_log.py"), "--token-budget", "-1"]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("token-budget must be a non-negative integer (>= 0)", proc.stderr)


if __name__ == "__main__":
    unittest.main()
