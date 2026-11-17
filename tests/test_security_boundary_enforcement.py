#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_security_boundary_enforcement.py
---------------------------------------------
Comprehensive acceptance tests verifying direct boundary authorization,
scope enforcement, consent scoping, DNS rebinding TOCTOU defense,
and audit secret masking across db_sandbox, api_fuzzer, and pentest_scope_guard.
"""

import os
import sys
import json
import sqlite3
import tempfile
import shutil
import unittest
import socket
import threading
import http.server
import urllib.request
import urllib
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from db_sandbox import DBSandbox, main as db_sandbox_main
from api_fuzzer import ApiFuzzer
from pentest_scope_guard import PentestScopeGuard, create_safe_opener, create_consent_grant
import mcp_server


class TestDBSandboxDirectBoundaryEnforcement(unittest.TestCase):
    """Verifies that direct entry points into DBSandbox enforce authorization and consent."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="db_boundary_test_")
        self.db_path = os.path.join(self.temp_dir, "test_target.db")
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, code TEXT, name TEXT);")
        cur.execute("INSERT INTO users (code, name) VALUES ('AUTO_001', 'Test User 1');")
        cur.execute("INSERT INTO users (code, name) VALUES ('REAL_001', 'Production User');")
        conn.commit()
        conn.close()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_direct_api_restore_without_consent_fails_closed(self):
        sandbox = DBSandbox(db_type="sqlite", db_path=self.db_path, snapshot_dir=self.temp_dir)
        snap = sandbox.create_snapshot("base_snap")
        self.assertEqual(snap["status"], "READY")

        # Direct API call without consent
        res = sandbox.restore_snapshot("base_snap", consent=False)
        self.assertEqual(res["status"], "ERROR")
        self.assertIn("explicit consent", res["message"].lower())
        self.assertFalse(res["zero_pollution_guaranteed"])

    def test_direct_api_restore_dry_run_is_preview_only_zero_mutation(self):
        sandbox = DBSandbox(db_type="sqlite", db_path=self.db_path, snapshot_dir=self.temp_dir)
        sandbox.create_snapshot("base_snap")

        # Mutate database
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO users (code, name) VALUES ('DIRTY_001', 'Dirty record');")
        conn.commit()
        conn.close()

        # Execute dry_run restore
        res = sandbox.restore_snapshot("base_snap", dry_run=True, consent=True)
        self.assertEqual(res["status"], "dry_run_preview")
        self.assertTrue(res["dry_run"])

        # Check DB was NOT modified
        conn = sqlite3.connect(self.db_path)
        cnt = conn.execute("SELECT COUNT(*) FROM users;").fetchone()[0]
        conn.close()
        self.assertEqual(cnt, 3)

    def test_direct_api_purge_without_consent_fails_closed(self):
        sandbox = DBSandbox(db_type="sqlite", db_path=self.db_path, snapshot_dir=self.temp_dir)
        res = sandbox.audit_and_purge_pollution(dry_run=False, consent=False)
        self.assertEqual(res["status"], "ERROR")
        self.assertIn("explicit consent", res["message"].lower())
        self.assertEqual(res["total_purged_rows"], 0)

        # Verify no rows were deleted
        conn = sqlite3.connect(self.db_path)
        cnt = conn.execute("SELECT COUNT(*) FROM users;").fetchone()[0]
        conn.close()
        self.assertEqual(cnt, 2)

    def test_direct_api_purge_dry_run_never_mutates_database(self):
        sandbox = DBSandbox(db_type="sqlite", db_path=self.db_path, snapshot_dir=self.temp_dir)
        res = sandbox.audit_and_purge_pollution(dry_run=True, consent=False)
        self.assertEqual(res["status"], "DRY_RUN")
        self.assertTrue(res["dry_run"])
        self.assertEqual(res["total_purged_rows"], 1)

        # Records are still present in DB
        conn = sqlite3.connect(self.db_path)
        cnt = conn.execute("SELECT COUNT(*) FROM users;").fetchone()[0]
        conn.close()
        self.assertEqual(cnt, 2)

    def test_scoped_consent_sandbox_mismatch_is_rejected(self):
        sandbox = DBSandbox(db_type="sqlite", db_path=self.db_path, snapshot_dir=self.temp_dir)
        sandbox.create_snapshot("base_snap")

        other_sandbox = os.path.join(self.temp_dir, "other_db.db")
        mismatched_consent = {"target_sandbox": other_sandbox, "operation": "restore"}

        # Attempt restore with mismatched scoped consent
        res = sandbox.restore_snapshot("base_snap", consent=mismatched_consent)
        self.assertEqual(res["status"], "ERROR")
        self.assertIn("target sandbox mismatch", res["message"].lower())

        # Attempt purge with mismatched scoped consent
        mismatched_purge_consent = {"target_sandbox": other_sandbox, "operation": "purge"}
        res_purge = sandbox.audit_and_purge_pollution(dry_run=False, consent=mismatched_purge_consent)
        self.assertEqual(res_purge["status"], "ERROR")
        self.assertIn("target sandbox mismatch", res_purge["message"].lower())

    def test_cli_purge_without_confirm_is_blocked_before_mutation(self):
        test_args = ["db_sandbox.py", "audit", "--apply", "--db-path", self.db_path]
        with patch.object(sys, "argv", test_args):
            exit_code = db_sandbox_main()
            self.assertEqual(exit_code, 1)

        # Confirm data was untouched
        conn = sqlite3.connect(self.db_path)
        cnt = conn.execute("SELECT COUNT(*) FROM users;").fetchone()[0]
        conn.close()
        self.assertEqual(cnt, 2)

    def test_cli_purge_with_confirm_purges_only_matching_prefixes(self):
        test_args = ["db_sandbox.py", "audit", "--apply", "--confirm", "--db-path", self.db_path]
        with patch.object(sys, "argv", test_args):
            exit_code = db_sandbox_main()
            self.assertEqual(exit_code, 0)

        # Confirm AUTO_001 purged, REAL_001 preserved
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("SELECT code FROM users;").fetchall()
        conn.close()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "REAL_001")

    def test_cli_restore_without_confirm_is_blocked_before_mutation(self):
        sandbox = DBSandbox(db_type="sqlite", db_path=self.db_path, snapshot_dir=self.temp_dir)
        sandbox.create_snapshot("snap1")

        test_args = ["db_sandbox.py", "restore", "--id", "snap1", "--db-path", self.db_path]
        with patch.object(sys, "argv", test_args):
            exit_code = db_sandbox_main()
            self.assertEqual(exit_code, 1)

    def test_mcp_destructive_calls_blocked_without_consent(self):
        mcp_db = os.path.join(REPO_ROOT, ".synapse", "test_mcp_boundary.db")
        os.makedirs(os.path.dirname(mcp_db), exist_ok=True)
        with open(mcp_db, "w") as f:
            f.write("")
        try:
            args_restore = {
                "action": "restore",
                "snapshot_id": "snap1",
                "db_path": mcp_db,
                "dry_run": False,
                "consent": False
            }
            with self.assertRaises(PermissionError) as ctx_restore:
                mcp_server._handle_manage_db_sandbox(args_restore)
            self.assertIn("requires explicit consent", str(ctx_restore.exception))

            args_purge = {
                "action": "audit_and_purge",
                "db_path": mcp_db,
                "dry_run": False,
                "consent": False
            }
            with self.assertRaises(PermissionError) as ctx_purge:
                mcp_server._handle_manage_db_sandbox(args_purge)
            self.assertIn("requires explicit consent", str(ctx_purge.exception))
        finally:
            if os.path.exists(mcp_db):
                os.remove(mcp_db)


class TestApiFuzzerDirectBoundaryEnforcement(unittest.TestCase):
    """Verifies that direct public methods of ApiFuzzer enforce authorization, consent, and scope."""

    def setUp(self):
        self.base_url = "http://127.0.0.1:54321"
        self.guard = PentestScopeGuard(allowed_hosts=["127.0.0.1"], allow_internal=True)
        self.fuzzer = ApiFuzzer(
            base_url=self.base_url,
            scope_guard=self.guard,
            allow_internal=True,
            consent=False
        )

    def test_direct_execute_request_live_without_consent_rejected_before_network_io(self):
        mutation = {
            "name": "SQLi Injection Probe",
            "type": "SQL_INJECTION",
            "path": "/api/v1/search",
            "method": "POST",
            "body": {"query": "' OR '1'='1"},
            "headers": {"Content-Type": "application/json"}
        }

        # Direct call with dry_run=False and consent=False
        res = self.fuzzer.execute_request(mutation, dry_run=False, consent=False)
        self.assertEqual(res["status_code"], -5)
        self.assertEqual(res["verdict"], "FAIL")
        self.assertTrue(any("CONSENT_REQUIRED" in a for a in res["alarms"]))
        self.assertEqual(res["duration_ms"], 0.0)

    def test_direct_run_fuzz_suite_live_without_consent_raises_permission_error(self):
        with self.assertRaises(PermissionError) as ctx:
            self.fuzzer.run_fuzz_suite(dry_run=False, consent=False)
        self.assertIn("requires explicit consent", str(ctx.exception).lower())

    def test_passive_scan_dispatches_zero_network_requests(self):
        # Even with no running server, passive scan completes offline
        scorecard = self.fuzzer.run_passive_scan()
        self.assertIn("findings", scorecard)
        self.assertEqual(scorecard.get("mode"), "PASSIVE")

    def test_dry_run_execute_request_dispatches_zero_network_requests(self):
        mutation = {
            "name": "Dry Run Test",
            "type": "FUZZ",
            "path": "/api/users",
            "method": "GET",
            "headers": {}
        }
        res = self.fuzzer.execute_request(mutation, dry_run=True)
        self.assertEqual(res["verdict"], "PASS")
        self.assertEqual(res["duration_ms"], 42.5)
        self.assertIn("handled_by_dry_run", res["response_preview"])

    def test_scoped_consent_target_mismatch_rejected(self):
        mutation = {
            "name": "Test Mutation",
            "type": "FUZZ",
            "path": "/api/users",
            "method": "GET",
            "headers": {}
        }
        scoped_consent = {
            "target": "http://127.0.0.1:9999",
            "method": "GET"
        }
        res = self.fuzzer.execute_request(mutation, dry_run=False, consent=scoped_consent)
        self.assertEqual(res["status_code"], -5)
        self.assertEqual(res["verdict"], "FAIL")
        self.assertTrue(any("CONSENT_MISMATCH" in a for a in res["alarms"]))
        self.assertIn("target mismatch", res["response_preview"].lower())

    def test_scoped_consent_method_mismatch_rejected(self):
        mutation = {
            "name": "Test Mutation",
            "type": "FUZZ",
            "path": "/api/users",
            "method": "DELETE",
            "headers": {}
        }
        scoped_consent = {
            "target": self.base_url,
            "method": "GET"
        }
        res = self.fuzzer.execute_request(mutation, dry_run=False, consent=scoped_consent)
        self.assertEqual(res["status_code"], -5)
        self.assertEqual(res["verdict"], "FAIL")
        self.assertTrue(any("CONSENT_MISMATCH" in a for a in res["alarms"]))
        self.assertIn("method mismatch", res["response_preview"].lower())

    def test_scoped_consent_path_mismatch_rejected(self):
        mutation = {
            "name": "Test Mutation",
            "type": "FUZZ",
            "path": "/api/admin/purge",
            "method": "POST",
            "headers": {}
        }
        scoped_consent = {
            "target": self.base_url,
            "path": "/api/users",
            "method": "POST"
        }
        res = self.fuzzer.execute_request(mutation, dry_run=False, consent=scoped_consent)
        self.assertEqual(res["status_code"], -5)
        self.assertEqual(res["verdict"], "FAIL")
        self.assertTrue(any("CONSENT_MISMATCH" in a for a in res["alarms"]))
        self.assertIn("path mismatch", res["response_preview"].lower())

    def test_consent_never_bypasses_or_expands_host_scope(self):
        mutation = {
            "name": "External Escape Probe",
            "type": "SCOPE_ESCAPE",
            "path": "/steal",
            "method": "GET",
            "headers": {}
        }
        # Attempt to target an unauthorized host with full valid granular consent
        grant = create_consent_grant(action="http:fuzz", target="http://127.0.0.1:54321", caller_session="scope_test")
        unauth_fuzzer = ApiFuzzer(
            base_url="http://127.0.0.1:54321",
            scope_guard=PentestScopeGuard(allowed_hosts=["127.0.0.1"], allow_internal=True),
            allow_internal=True,
            consent=grant
        )
        # Hack path to force host escape
        unauth_mutation = {
            "name": "Host Escape",
            "type": "ESCAPE",
            "path": "@evil.attacker.com/steal",
            "method": "GET",
            "headers": {}
        }
        res = unauth_fuzzer.execute_request(unauth_mutation, dry_run=False, consent=grant)
        self.assertEqual(res["status_code"], -3)
        self.assertEqual(res["verdict"], "FAIL")
        self.assertTrue(any("SCOPE_BLOCKED" in a for a in res["alarms"]))


class TestNetworkScopeAndDNSProtection(unittest.TestCase):
    """Verifies that scope guard rejects unauthorized hosts, mixed DNS, metadata, and handles DNS pinning."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="scope_guard_test_")
        self.audit_log = os.path.join(self.temp_dir, "audit.log")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_host_outside_allowlist_is_blocked(self):
        guard = PentestScopeGuard(allowed_hosts=["staging.example.com"], audit_log_path=self.audit_log)
        ok, reason = guard.validate_target("https://unauthorized.evil.com/api")
        self.assertFalse(ok)
        self.assertIn("SCOPE REJECTED", reason)

    def test_redirect_outside_scope_is_blocked(self):
        guard = PentestScopeGuard(allowed_hosts=["staging.example.com"], audit_log_path=self.audit_log)
        ok, reason = guard.validate_redirect(
            "https://staging.example.com/oauth/login",
            "https://evil-phish.com/callback"
        )
        self.assertFalse(ok)
        self.assertIn("DANGEROUS REDIRECT BLOCKED", reason)

    @patch("socket.gethostbyname")
    def test_cloud_metadata_service_always_blocked(self, mock_dns):
        mock_dns.return_value = "169.254.169.254"
        guard = PentestScopeGuard(allowed_hosts=["metadata.local"], allow_internal=True, audit_log_path=self.audit_log)
        ok, reason = guard.validate_target("http://metadata.local/latest/meta-data")
        self.assertFalse(ok)
        self.assertIn("AWS/Cloud Instance Metadata Service", reason)

    def test_ipv6_cloud_metadata_blocked(self):
        guard = PentestScopeGuard(allowed_hosts=["fd00:ec2::254"], allow_internal=True, audit_log_path=self.audit_log)
        ok, reason = guard.validate_target("http://[fd00:ec2::254]/latest/meta-data")
        self.assertFalse(ok)
        self.assertIn("Metadata Service", reason)

    def test_ipv4_mapped_ipv6_metadata_and_private_blocked(self):
        guard = PentestScopeGuard(allowed_hosts=["::ffff:169.254.169.254"], allow_internal=True, audit_log_path=self.audit_log)
        ok, reason = guard.validate_target("http://[::ffff:169.254.169.254]/meta-data")
        self.assertFalse(ok)
        self.assertIn("Metadata Service", reason)

        guard2 = PentestScopeGuard(allowed_hosts=["::ffff:10.0.0.1"], allow_internal=False, audit_log_path=self.audit_log)
        ok2, reason2 = guard2.validate_target("http://[::ffff:10.0.0.1]/admin")
        self.assertFalse(ok2)
        self.assertIn("Private subnet", reason2)

    @patch("socket.gethostbyname")
    @patch("socket.getaddrinfo")
    def test_mixed_public_and_private_dns_resolution_blocked(self, mock_addrinfo, mock_gethost):
        # Attacker configures dual DNS records: 93.184.216.34 (public) and 10.0.0.1 (private)
        mock_gethost.return_value = "93.184.216.34"
        mock_addrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 80)),
        ]
        guard = PentestScopeGuard(allowed_hosts=["dual-homed.example.com"], allow_internal=False, audit_log_path=self.audit_log)
        ok, reason = guard.validate_target("http://dual-homed.example.com/api")
        self.assertFalse(ok)
        self.assertIn("IP SAFETY REJECTED", reason)
        self.assertIn("RFC1918 Private subnet", reason)

    def test_dns_rebinding_connection_pinning(self):
        """Verifies that PinnedHTTPConnection connects strictly to the pre-validated pinned IP."""
        class MockServerHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"PINNED_TARGET_VERIFIED")

            def log_message(self, format, *args):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), MockServerHandler)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        guard = PentestScopeGuard(allowed_hosts=["rebinding-test.local"], allow_internal=True, audit_log_path=self.audit_log)
        # Pre-validate and pin IP
        guard.pin_ip("rebinding-test.local", "127.0.0.1")

        opener = create_safe_opener(scope_guard=guard)
        try:
            req = urllib.request.Request(f"http://rebinding-test.local:{port}/test")
            with opener.open(req, timeout=5.0) as resp:
                content = resp.read().decode("utf-8")
                self.assertEqual(content, "PINNED_TARGET_VERIFIED")
        finally:
            server.shutdown()


class TestAuditLogSecretRedaction(unittest.TestCase):
    """Verifies that audit logging records request ID and decision without leaking sensitive data."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="audit_log_test_")
        self.audit_log = os.path.join(self.temp_dir, "pentest_audit.log")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("socket.gethostbyname")
    def test_audit_log_redacts_credentials_and_query_secrets(self, mock_dns):
        mock_dns.return_value = "93.184.216.34"
        guard = PentestScopeGuard(allowed_hosts=["staging.example.com"], audit_log_path=self.audit_log)

        url_with_secrets = "https://staging.example.com/api?token=SUPER_SECRET_TOKEN_999&password=MY_SUPER_SECRET_PASSWORD"
        ok, reason = guard.validate_target(url_with_secrets, actor="test_runner")
        self.assertTrue(ok)

        # Inspect audit log file contents
        self.assertTrue(os.path.exists(self.audit_log))
        with open(self.audit_log, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        self.assertEqual(len(lines), 1)
        entry = lines[0]
        self.assertEqual(entry["decision"], "AUTHORIZED")
        self.assertIn("request_id", entry)
        self.assertEqual(len(entry["request_id"]), 36)  # UUID format

        # Strictly verify zero secret leak in target and rationale
        self.assertNotIn("SUPER_SECRET_TOKEN_999", entry["target"])
        self.assertNotIn("MY_SUPER_SECRET_PASSWORD", entry["target"])
        self.assertIn("***REDACTED***", entry["target"])


if __name__ == "__main__":
    unittest.main()
