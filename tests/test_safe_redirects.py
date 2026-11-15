#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_safe_redirects.py — Hermetic regression suite for SafeRedirectHandler
and SSRF redirect containment across PentestScopeGuard and ApiFuzzer.
"""

import os
import sys
import json
import threading
import unittest
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools")))
from pentest_scope_guard import PentestScopeGuard, PentestScopeError
from api_fuzzer import ApiFuzzer


class RedirectMockHandler(BaseHTTPRequestHandler):
    """Hermetic local server providing controlled 302 redirects."""

    def do_GET(self):
        if self.path == "/safe_target":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "safe_ok"}')
        elif self.path == "/safe_spec":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            spec = {
                "paths": {
                    "/api/test": {"get": {"summary": "test route"}}
                }
            }
            self.wfile.write(json.dumps(spec).encode("utf-8"))
        elif self.path == "/redirect_to_safe":
            self.send_response(302)
            self.send_header("Location", "/safe_target")
            self.end_headers()
        elif self.path == "/redirect_to_spec":
            self.send_response(302)
            self.send_header("Location", "/safe_spec")
            self.end_headers()
        elif self.path == "/redirect_to_metadata":
            self.send_response(302)
            self.send_header("Location", "http://169.254.169.254/latest/meta-data")
            self.end_headers()
        elif self.path == "/redirect_to_evil":
            self.send_response(302)
            self.send_header("Location", "https://unauthorized-evil.com/leak")
            self.end_headers()
        elif self.path == "/redirect_to_sensitive_port":
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:22/ssh")
            self.end_headers()
        elif self.path == "/redirect_loop":
            self.send_response(302)
            self.send_header("Location", "/redirect_loop")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        self.do_GET()

    def log_message(self, *args):
        # Silence HTTP server logging during test runs
        pass


class TestSafeRedirects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), RedirectMockHandler)
        cls.port = cls.server.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_safe_redirect_followed_within_scope(self):
        guard = PentestScopeGuard(allowed_hosts=["127.0.0.1"], allow_internal=True)
        opener = guard.create_safe_opener()
        req = urllib.request.Request(f"{self.base_url}/redirect_to_safe")
        with opener.open(req, timeout=5.0) as resp:
            self.assertEqual(resp.getcode(), 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "safe_ok")

    def test_redirect_to_cloud_metadata_blocked(self):
        guard = PentestScopeGuard(allowed_hosts=["127.0.0.1"], allow_internal=True)
        opener = guard.create_safe_opener()
        req = urllib.request.Request(f"{self.base_url}/redirect_to_metadata")
        with self.assertRaises(PentestScopeError) as ctx:
            opener.open(req, timeout=5.0)
        self.assertIn("DANGEROUS_REDIRECT_BLOCKED", str(ctx.exception))
        self.assertIn("169.254.169.254", str(ctx.exception))

    def test_redirect_to_unauthorized_host_blocked(self):
        guard = PentestScopeGuard(allowed_hosts=["127.0.0.1"], allow_internal=True)
        opener = guard.create_safe_opener()
        req = urllib.request.Request(f"{self.base_url}/redirect_to_evil")
        with self.assertRaises(PentestScopeError) as ctx:
            opener.open(req, timeout=5.0)
        self.assertIn("DANGEROUS_REDIRECT_BLOCKED", str(ctx.exception))
        self.assertIn("unauthorized-evil.com", str(ctx.exception))

    def test_redirect_to_sensitive_port_blocked(self):
        guard = PentestScopeGuard(allowed_hosts=["127.0.0.1"], allow_internal=True)
        opener = guard.create_safe_opener()
        req = urllib.request.Request(f"{self.base_url}/redirect_to_sensitive_port")
        with self.assertRaises(PentestScopeError) as ctx:
            opener.open(req, timeout=5.0)
        self.assertIn("DANGEROUS_REDIRECT_BLOCKED", str(ctx.exception))
        self.assertIn("DISALLOWED PORT", str(ctx.exception))

    def test_redirect_loop_exhausts_max_redirects(self):
        guard = PentestScopeGuard(allowed_hosts=["127.0.0.1"], allow_internal=True)
        opener = guard.create_safe_opener(max_redirects=3)
        req = urllib.request.Request(f"{self.base_url}/redirect_loop")
        with self.assertRaises(PentestScopeError) as ctx:
            opener.open(req, timeout=5.0)
        self.assertIn("MAX_REDIRECTS_EXCEEDED", str(ctx.exception))

    def test_api_fuzzer_load_spec_redirect_to_metadata_fails(self):
        fuzzer = ApiFuzzer(
            base_url=self.base_url,
            spec_path_or_url=f"{self.base_url}/redirect_to_metadata",
            allow_internal=True,
        )
        with self.assertRaises(PermissionError) as ctx:
            fuzzer.load_spec()
        self.assertIn("Redirect blocked during load_spec", str(ctx.exception))

    def test_api_fuzzer_load_spec_safe_redirect_succeeds(self):
        fuzzer = ApiFuzzer(
            base_url=self.base_url,
            spec_path_or_url=f"{self.base_url}/redirect_to_spec",
            allow_internal=True,
        )
        spec = fuzzer.load_spec()
        self.assertIn("/api/test", spec.get("paths", {}))

    def test_api_fuzzer_execute_request_detects_dangerous_redirect(self):
        fuzzer = ApiFuzzer(base_url=self.base_url, allow_internal=True)
        mutation = {
            "name": "redirect_attack_probe",
            "type": "SSRF_REDIRECT",
            "path": "/redirect_to_metadata",
            "method": "GET",
            "headers": {},
        }
        res = fuzzer.execute_request(mutation, dry_run=False)
        self.assertEqual(res["verdict"], "FAIL")
        self.assertEqual(res["severity"], "CRITICAL")
        self.assertTrue(any("DANGEROUS_REDIRECT_BLOCKED" in a for a in res["alarms"]))

    def test_consecutive_redirects_do_not_accumulate_state(self):
        """
        Regression test: Verify that an OpenerDirector reusing a single SafeRedirectHandler
        can process 10 consecutive requests each with a 302 redirect without state leakage
        accumulating toward MAX_REDIRECTS_EXCEEDED.
        """
        guard = PentestScopeGuard(allowed_hosts=["127.0.0.1"], allow_internal=True)
        opener = guard.create_safe_opener(max_redirects=5)
        for i in range(10):
            req = urllib.request.Request(f"{self.base_url}/redirect_to_safe")
            with opener.open(req, timeout=5.0) as resp:
                self.assertEqual(resp.getcode(), 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(data.get("status"), "safe_ok")

    def test_api_fuzzer_consecutive_requests_with_redirect_succeed(self):
        """
        Verify that ApiFuzzer reusing a single OpenerDirector can execute >= 10 sequential
        requests that redirect without triggering false-positive MAX_REDIRECTS_EXCEEDED alarms.
        """
        fuzzer = ApiFuzzer(base_url=self.base_url, allow_internal=True)
        mutation = {
            "name": "benign_redirect_test",
            "type": "NORMAL",
            "path": "/redirect_to_safe",
            "method": "GET",
            "headers": {},
        }
        for i in range(10):
            res = fuzzer.execute_request(mutation, dry_run=False)
            self.assertEqual(res["verdict"], "PASS")
            self.assertEqual(res["alarms"], [])

    def test_dns_rebinding_secondary_ip_blocked_when_mocked(self):
        """
        Verify that multi-IP DNS resolution (anti-rebinding) checks secondary IPs
        returned by socket.getaddrinfo even when resolvers are mocked.
        """
        import socket
        from unittest.mock import patch

        guard = PentestScopeGuard(allowed_hosts=["rebind.example.com"], allow_internal=False)
        with patch("socket.gethostbyname", return_value="93.184.216.34"), \
             patch("socket.getaddrinfo", return_value=[
                 (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80)),
                 (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 80)),
             ]):
            ok, msg = guard.validate_target("http://rebind.example.com")
            self.assertFalse(ok)
            self.assertIn("169.254.169.254", msg)
            self.assertIn("IP SAFETY REJECTED", msg)

    def test_dns_rebinding_secondary_public_ips_allowed(self):
        """Verify that benign multi-IP DNS resolution passes validation."""
        import socket
        from unittest.mock import patch

        guard = PentestScopeGuard(allowed_hosts=["multi.example.com"], allow_internal=False)
        with patch("socket.gethostbyname", return_value="93.184.216.34"), \
             patch("socket.getaddrinfo", return_value=[
                 (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80)),
                 (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.35", 80)),
             ]):
            ok, msg = guard.validate_target("http://multi.example.com")
            self.assertTrue(ok)
            self.assertIn("authorized", msg.lower())


if __name__ == "__main__":
    unittest.main()
