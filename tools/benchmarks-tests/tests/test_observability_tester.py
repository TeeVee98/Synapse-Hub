#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-

"""
Unit tests for tools/observability_tester.py
Validates OpenTelemetry distributed trace continuity, span attribute checks, and log hygiene leaks.
"""

import unittest
from tools.observability_tester import OpenTelemetryTraceVerifier, LogHygieneSentinel


class TestObservabilityTester(unittest.TestCase):
    def test_trace_continuity_pass(self):
        """Verifies clean multi-tier trace propagation passes continuity check."""
        trace_id = "test_trace_12345"
        spans = [
            {"trace_id": trace_id, "span_id": "s1", "parent_span_id": None, "service_name": "frontend"},
            {"trace_id": trace_id, "span_id": "s2", "parent_span_id": "s1", "service_name": "backend"},
            {"trace_id": trace_id, "span_id": "s3", "parent_span_id": "s2", "service_name": "database"},
        ]
        res = OpenTelemetryTraceVerifier.verify_trace_continuity(trace_id, spans, ["frontend", "backend", "database"])
        self.assertTrue(res["continuity_passed"])
        self.assertEqual(res["status"], "PASSED")
        self.assertEqual(len(res["missing_services"]), 0)
        self.assertEqual(len(res["orphaned_spans"]), 0)

    def test_trace_continuity_missing_service(self):
        """Verifies failure when an intermediate microservice fails to emit spans."""
        trace_id = "test_trace_broken"
        spans = [
            {"trace_id": trace_id, "span_id": "s1", "parent_span_id": None, "service_name": "frontend"},
            {"trace_id": trace_id, "span_id": "s2", "parent_span_id": "s1", "service_name": "database"},
        ]
        res = OpenTelemetryTraceVerifier.verify_trace_continuity(trace_id, spans, ["frontend", "backend", "database"])
        self.assertFalse(res["continuity_passed"])
        self.assertEqual(res["status"], "FAILED")
        self.assertIn("backend", res["missing_services"])

    def test_span_attributes_verification(self):
        """Verifies semantic attributes verification."""
        span = {
            "span_id": "s1",
            "attributes": {"http.status_code": 200, "http.method": "GET"}
        }
        passed, missing = OpenTelemetryTraceVerifier.verify_span_attributes(span, ["http.status_code", "http.method"])
        self.assertTrue(passed)
        self.assertEqual(len(missing), 0)

        passed_fail, missing_fail = OpenTelemetryTraceVerifier.verify_span_attributes(span, ["http.status_code", "db.statement"])
        self.assertFalse(passed_fail)
        self.assertIn("db.statement", missing_fail)

    def test_log_hygiene_clean_log(self):
        """Clean logs should pass with 0 leaks."""
        log = "2026-11-17 INFO User logged in successfully with user_id=USR_1001"
        res = LogHygieneSentinel.scan_log_content(log)
        self.assertEqual(res["status"], "PASSED")
        self.assertEqual(res["leaks_detected"], 0)

    def test_log_hygiene_pan_and_cvv_leak(self):
        """Exposed credit card numbers and CVVs must be flagged as CRITICAL."""
        log = "DEBUG Authorization payload: card=4111111111111111, cvv=123"
        res = LogHygieneSentinel.scan_log_content(log)
        self.assertEqual(res["status"], "FAILED")
        self.assertEqual(res["leaks_detected"], 2)
        types = [l["type"] for l in res["leaks"]]
        self.assertIn("PAYMENT_PAN_LEAK", types)
        self.assertIn("PAYMENT_CVV_LEAK", types)

    def test_log_hygiene_bearer_token_and_password_leak(self):
        """Exposed Bearer tokens and passwords must be flagged."""
        log = "ERROR Authorization failed: header=Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-IDN secretly password=MySecret123"
        res = LogHygieneSentinel.scan_log_content(log)
        self.assertEqual(res["status"], "FAILED")
        types = [l["type"] for l in res["leaks"]]
        self.assertIn("CREDENTIAL_TOKEN_LEAK", types)
        self.assertIn("PLAINTEXT_PASSWORD_LEAK", types)


if __name__ == "__main__":
    unittest.main()
