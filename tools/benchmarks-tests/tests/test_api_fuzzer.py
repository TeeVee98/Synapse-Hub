#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_api_fuzzer.py — Comprehensive Unit & Boundary Tests for tools/api_fuzzer.py
-------------------------------------------------------------------------------------
Verifies:
  1. Dry-run safety: Zero live DNS queries and zero network socket dispatch in __init__, load_spec, and execute_request.
  2. Granular ConsentGrant enforcement: Rejection of generic boolean consent (consent=True) and environment variables.
  3. Replay attack rejection: Nonce consumption defense.
  4. Expiry rejection: Expired grants fail closed.
  5. Scoped mismatch rejection: Method, target, and path pattern containment.
"""

import os
import sys
import time
import socket
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools")))
from api_fuzzer import ApiFuzzer
from pentest_scope_guard import (
    PentestScopeGuard,
    ConsentGrant,
    create_consent_grant,
    clear_consumed_nonces,
)


class TestApiFuzzerDryRunSafety(unittest.TestCase):
    """Verifies that dry_run=True operates 100% offline with zero network side effects."""

    def test_init_dry_run_skips_live_dns(self):
        """In dry_run mode, __init__ must not perform DNS lookups on unresolvable target URLs."""
        with patch.object(socket, "gethostbyname", side_effect=socket.gaierror("DNS lookup blocked in dry-run")):
            fuzzer = ApiFuzzer(
                base_url="http://completely-unresolvable-domain-123456.local:8080",
                dry_run=True,
                allow_internal=True
            )
            self.assertTrue(fuzzer.dry_run)

    def test_load_spec_remote_url_dry_run_skips_network_and_dns(self):
        """In dry_run mode, remote spec URLs must not trigger network requests or DNS resolution."""
        with patch("urllib.request.OpenerDirector.open") as mock_open:
            with patch.object(socket, "gethostbyname", side_effect=AssertionError("DNS resolution attempted in dry_run!")):
                fuzzer = ApiFuzzer(
                    base_url="http://127.0.0.1:8080",
                    spec_path_or_url="http://remote.invalid/openapi.json",
                    dry_run=True,
                    allow_internal=True
                )
                spec = fuzzer.load_spec()
                mock_open.assert_not_called()
                self.assertIn("paths", spec)
                self.assertIn("/api/v1/dry_run_endpoint", spec["paths"])

    def test_execute_request_dry_run_zero_network_io(self):
        """In dry_run mode, execute_request produces offline mock without opening sockets."""
        with patch("urllib.request.OpenerDirector.open") as mock_open:
            fuzzer = ApiFuzzer(base_url="http://127.0.0.1:8080", dry_run=True, allow_internal=True)
            mutation = {
                "name": "Dry Run Mutation Test",
                "type": "SQL_INJECTION",
                "path": "/api/users",
                "method": "POST",
                "body": {"id": "' OR 1=1 --"},
                "headers": {"Content-Type": "application/json"}
            }
            res = fuzzer.execute_request(mutation, dry_run=True)
            mock_open.assert_not_called()
            self.assertEqual(res["verdict"], "PASS")
            self.assertEqual(res["duration_ms"], 42.5)
            self.assertIn("handled_by_dry_run", res["response_preview"])

    def test_run_fuzz_suite_dry_run_requires_no_consent(self):
        """In dry_run mode, running full fuzz suite completes safely without requiring consent."""
        fuzzer = ApiFuzzer(base_url="http://127.0.0.1:8080", dry_run=True, allow_internal=True)
        scorecard = fuzzer.run_fuzz_suite(dry_run=True)
        self.assertTrue(scorecard.get("dry_run"))
        self.assertGreater(scorecard.get("total_mutations", 0), 0)


class TestApiFuzzerGranularConsent(unittest.TestCase):
    """Verifies that active execution strictly requires a cryptographic ConsentGrant."""

    def setUp(self):
        clear_consumed_nonces()
        self.base_url = "http://127.0.0.1:8080"
        self.guard = PentestScopeGuard(allowed_hosts=["127.0.0.1"], allow_internal=True)
        self.fuzzer = ApiFuzzer(base_url=self.base_url, scope_guard=self.guard, allow_internal=True)
        self.sample_mutation = {
            "name": "SQLi Probe",
            "type": "SQL_INJECTION",
            "path": "/api/v1/search",
            "method": "POST",
            "body": {"q": "' OR '1'='1"},
            "headers": {"Content-Type": "application/json"}
        }

    def test_generic_boolean_consent_true_is_rejected(self):
        """Eliminate generic boolean consent: consent=True must fail closed with CONSENT_REQUIRED."""
        res = self.fuzzer.execute_request(self.sample_mutation, dry_run=False, consent=True)
        self.assertEqual(res["status_code"], -5)
        self.assertEqual(res["verdict"], "FAIL")
        self.assertTrue(any("CONSENT_REQUIRED" in a for a in res["alarms"]))
        self.assertIn("missing consent", res["response_preview"].lower())

    def test_unauthenticated_env_var_is_rejected(self):
        """Eliminate shared environment variables: PENTEST_CONSENT_ACKNOWLEDGED=1 must not grant live execution."""
        with patch.dict(os.environ, {"PENTEST_CONSENT_ACKNOWLEDGED": "1"}):
            res = self.fuzzer.execute_request(self.sample_mutation, dry_run=False, consent=False)
            self.assertEqual(res["status_code"], -5)
            self.assertEqual(res["verdict"], "FAIL")
            self.assertTrue(any("CONSENT_REQUIRED" in a for a in res["alarms"]))

    def test_expired_grant_is_rejected(self):
        """Expired ConsentGrant must fail closed before socket creation."""
        expired_grant = ConsentGrant(
            action="http:fuzz",
            target=self.base_url,
            caller_session="test_sess",
            nonce="nonce_expired",
            expiry=time.time() - 60.0
        )
        res = self.fuzzer.execute_request(self.sample_mutation, dry_run=False, consent=expired_grant)
        self.assertEqual(res["status_code"], -5)
        self.assertEqual(res["verdict"], "FAIL")
        self.assertTrue(any("CONSENT_EXPIRED" in a for a in res["alarms"]))
        self.assertIn("consent expired", res["response_preview"].lower())

    def test_replayed_nonce_is_rejected(self):
        """Replaying a single-use consent nonce must fail closed on second use."""
        replayed_grant = create_consent_grant(
            action="http:fuzz",
            target=self.base_url,
            caller_session="test_sess",
            nonce="unique_nonce_abc123"
        )
        with patch("urllib.request.OpenerDirector.open") as mock_open:
            mock_resp = MagicMock()
            mock_resp.getcode.return_value = 200
            mock_resp.read.return_value = b'{"status": "ok"}'
            mock_resp.headers = {}
            mock_open.return_value.__enter__.return_value = mock_resp

            # First execution consumes nonce
            res1 = self.fuzzer.execute_request(self.sample_mutation, dry_run=False, consent=replayed_grant)
            self.assertEqual(res1["status_code"], 200)

            # Replay with same grant and nonce fails closed
            res2 = self.fuzzer.execute_request(self.sample_mutation, dry_run=False, consent=replayed_grant)
            self.assertEqual(res2["status_code"], -5)
            self.assertEqual(res2["verdict"], "FAIL")
            self.assertTrue(any("CONSENT_REPLAYED" in a for a in res2["alarms"]))
            self.assertIn("consent replayed", res2["response_preview"].lower())

    def test_target_mismatch_is_rejected(self):
        """Consent granted for URL A cannot be reused to target URL B."""
        mismatched_grant = create_consent_grant(
            action="http:fuzz",
            target="http://127.0.0.1:9999",
            caller_session="test_sess"
        )
        res = self.fuzzer.execute_request(self.sample_mutation, dry_run=False, consent=mismatched_grant)
        self.assertEqual(res["status_code"], -5)
        self.assertEqual(res["verdict"], "FAIL")
        self.assertTrue(any("CONSENT_MISMATCH" in a for a in res["alarms"]))
        self.assertIn("target mismatch", res["response_preview"].lower())

    def test_method_mismatch_is_rejected(self):
        """Consent granted for GET cannot be reused for mutating POST."""
        mismatched_grant = create_consent_grant(
            action="http:fuzz",
            target=self.base_url,
            caller_session="test_sess",
            method="GET"
        )
        res = self.fuzzer.execute_request(self.sample_mutation, dry_run=False, consent=mismatched_grant)
        self.assertEqual(res["status_code"], -5)
        self.assertEqual(res["verdict"], "FAIL")
        self.assertTrue(any("CONSENT_MISMATCH" in a for a in res["alarms"]))
        self.assertIn("method mismatch", res["response_preview"].lower())

    def test_path_mismatch_is_rejected(self):
        """Consent granted for /api/v1/users cannot be reused for /api/v1/search."""
        mismatched_grant = create_consent_grant(
            action="http:fuzz",
            target=self.base_url,
            caller_session="test_sess",
            path_pattern="/api/v1/users"
        )
        res = self.fuzzer.execute_request(self.sample_mutation, dry_run=False, consent=mismatched_grant)
        self.assertEqual(res["status_code"], -5)
        self.assertEqual(res["verdict"], "FAIL")
        self.assertTrue(any("CONSENT_MISMATCH" in a for a in res["alarms"]))
        self.assertIn("path mismatch", res["response_preview"].lower())

    def test_valid_granular_grant_executes_successfully(self):
        """A valid, matching ConsentGrant permits network execution."""
        valid_grant = create_consent_grant(
            action="http:fuzz",
            target=self.base_url,
            caller_session="test_sess",
            method="POST",
            path_pattern="/api/v1/*"
        )
        with patch("urllib.request.OpenerDirector.open") as mock_open:
            mock_resp = MagicMock()
            mock_resp.getcode.return_value = 200
            mock_resp.read.return_value = b'{"status": "ok"}'
            mock_resp.headers = {}
            mock_open.return_value.__enter__.return_value = mock_resp

            res = self.fuzzer.execute_request(self.sample_mutation, dry_run=False, consent=valid_grant)
            self.assertEqual(res["status_code"], 200)
            self.assertEqual(res["verdict"], "PASS")

    def test_run_fuzz_suite_live_batch_executes_without_self_replay(self):
        """Batch fuzz suite execution across multiple mutations does not suffer from self-replay."""
        grant = create_consent_grant(
            action="http:fuzz",
            target=self.base_url,
            caller_session="batch_sess",
            ttl_seconds=300
        )
        fuzzer = ApiFuzzer(base_url=self.base_url, scope_guard=self.guard, allow_internal=True, max_requests=5)

        def mock_open_handler(req, *args, **kwargs):
            mock_resp = MagicMock()
            has_auth = "Authorization" in req.headers or "authorization" in req.headers
            mock_resp.getcode.return_value = 200 if has_auth else 401
            mock_resp.read.return_value = b'{"status": "ok", "user": "test"}'
            mock_resp.headers = {}
            mock_ctx = MagicMock()
            mock_ctx.__enter__.return_value = mock_resp
            mock_ctx.__exit__.return_value = False
            return mock_ctx

        with patch("urllib.request.OpenerDirector.open", side_effect=mock_open_handler):
            scorecard = fuzzer.run_fuzz_suite(dry_run=False, consent=grant)
            self.assertGreater(scorecard["total_mutations"], 1, "Must execute multiple mutations in suite")
            self.assertEqual(scorecard["failed"], 0, f"No mutations should fail under valid grant: {scorecard}")
            self.assertEqual(scorecard["passed"], scorecard["total_mutations"])
            self.assertEqual(scorecard["severity_summary"]["CRITICAL"], 0)

            # Assert zero CONSENT_REPLAYED alarms across all mutation results
            for result in scorecard["results"]:
                self.assertEqual(result["verdict"], "PASS")
                alarms = result.get("alarms", [])
                self.assertFalse(any("CONSENT_REPLAYED" in a for a in alarms))

    def test_run_fuzz_suite_session_grant_cannot_be_reused_across_suites(self):
        """Once a fuzz suite completes, the session grant nonce is consumed and cannot be reused for a second suite."""
        grant = create_consent_grant(
            action="http:fuzz",
            target=self.base_url,
            caller_session="single_suite_sess",
            ttl_seconds=300
        )
        fuzzer = ApiFuzzer(base_url=self.base_url, scope_guard=self.guard, allow_internal=True, max_requests=3)

        def mock_open_handler(req, *args, **kwargs):
            mock_resp = MagicMock()
            has_auth = "Authorization" in req.headers or "authorization" in req.headers
            mock_resp.getcode.return_value = 200 if has_auth else 401
            mock_resp.read.return_value = b'{"status": "ok"}'
            mock_resp.headers = {}
            mock_ctx = MagicMock()
            mock_ctx.__enter__.return_value = mock_resp
            mock_ctx.__exit__.return_value = False
            return mock_ctx

        with patch("urllib.request.OpenerDirector.open", side_effect=mock_open_handler):
            # First suite succeeds
            scorecard = fuzzer.run_fuzz_suite(dry_run=False, consent=grant)
            self.assertEqual(scorecard["failed"], 0)

            # Second suite using same session grant must raise PermissionError (nonce consumed)
            with self.assertRaises(PermissionError):
                fuzzer.run_fuzz_suite(dry_run=False, consent=grant)

    def test_execute_request_rejects_incomplete_dict_grants(self):
        """execute_request rejects dictionary grants lacking mandatory fields (target, nonce, expiry, session)."""
        # Bare action without target
        res1 = self.fuzzer.execute_request(self.sample_mutation, dry_run=False, consent={"action": "http:fuzz"})
        self.assertEqual(res1["status_code"], -5)
        self.assertEqual(res1["verdict"], "FAIL")
        self.assertTrue(any("CONSENT_REQUIRED" in a for a in res1["alarms"]))

        # Missing nonce and expiry
        res2 = self.fuzzer.execute_request(
            self.sample_mutation,
            dry_run=False,
            consent={"action": "http:fuzz", "target": self.base_url}
        )
        self.assertEqual(res2["status_code"], -5)
        self.assertEqual(res2["verdict"], "FAIL")
        self.assertTrue(any("CONSENT_REQUIRED" in a for a in res2["alarms"]))


if __name__ == "__main__":
    unittest.main()
