#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tests/test_jira_sync.py
-----------------------
Unit and integration tests for Jira / Xray / Zephyr synchronization engine:
1. JiraConfig resolution and auth header construction.
2. Markdown testcase extraction.
3. JUnit XML metrics parser.
4. Mock Jira REST API integration (pull, push, create-bug, import-exec).
5. Attachment upload via multipart/form-data.
"""

import os
import sys
import json
import time
import socket
import unittest
import tempfile
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from jira_sync import (
    JiraConfig,
    JiraClient,
    parse_markdown_testcases,
    parse_junit_xml,
    pull_story,
    push_tests_from_file,
    create_bug_report,
    import_junit_execution
)


class MockJiraHandler(BaseHTTPRequestHandler):
    """Mock HTTP server simulating Jira Cloud/Server REST API endpoints."""

    def log_message(self, format, *args):
        pass

    def send_json(self, status: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/rest/api/2/myself":
            self.send_json(200, {
                "name": "qa_tester",
                "displayName": "QA Tester",
                "emailAddress": "qa@example.com"
            })
            return

        if self.path.startswith("/rest/api/2/issue/KAN-1"):
            self.send_json(200, {
                "key": "KAN-1",
                "fields": {
                    "summary": "Forgot Password Feature",
                    "description": "User clicks forgot password and receives email.",
                    "issuetype": {"name": "Story"},
                    "status": {"name": "To Do"},
                    "priority": {"name": "High"}
                }
            })
            return

        self.send_error(404, "Endpoint not found")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        if self.path == "/rest/api/2/issue":
            payload = json.loads(body.decode("utf-8")) if body else {}
            summary = payload.get("fields", {}).get("summary", "New Issue")
            self.send_json(201, {
                "id": "10001",
                "key": "KAN-99",
                "self": f"http://127.0.0.1/rest/api/2/issue/KAN-99"
            })
            return

        if "/attachments" in self.path:
            # Multipart upload endpoint
            self.send_json(200, [{
                "id": "20001",
                "filename": "screenshot.png",
                "size": length
            }])
            return

        self.send_error(404, "Endpoint not found")


class ThreadingServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class TestJiraSync(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Bind ephemeral port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        cls.port = s.getsockname()[1]
        s.close()

        cls.server = ThreadingServer(("127.0.0.1", cls.port), MockJiraHandler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.mock_url = f"http://127.0.0.1:{cls.port}"
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_jira_config_auth_headers(self):
        """Verifies Basic Auth (Cloud) and Bearer (PAT) header construction."""
        cfg_basic = JiraConfig(
            base_url="https://test.atlassian.net",
            email="user@test.com",
            api_token="secret_token"
        )
        headers_basic = cfg_basic.get_auth_headers()
        self.assertIn("Authorization", headers_basic)
        self.assertTrue(headers_basic["Authorization"].startswith("Basic "))

        cfg_pat = JiraConfig(
            base_url="https://jira.enterprise.local",
            pat="pat_token_123"
        )
        headers_pat = cfg_pat.get_auth_headers()
        self.assertEqual(headers_pat["Authorization"], "Bearer pat_token_123")

    def test_parse_markdown_testcases(self):
        """Tests table-based test case parsing from Markdown."""
        sample_md = """
# Test Specification
| Test ID | Summary | Steps | Expected |
|---|---|---|---|
| TC-01 | Login with valid credentials | 1. Enter email, 2. Enter pass | Dashboard shown |
| TC-02 | Login with wrong password | 1. Enter email, 2. Enter wrong pass | Error shown |
"""
        cases = parse_markdown_testcases(sample_md)
        self.assertEqual(len(cases), 2)
        self.assertEqual(cases[0]["id"], "TC-01")
        self.assertEqual(cases[0]["summary"], "Login with valid credentials")
        self.assertEqual(cases[1]["id"], "TC-02")

    def test_parse_junit_xml(self):
        """Tests parsing JUnit XML reports into structured metrics."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="E2E_Suite" tests="2" failures="1" errors="0" time="4.5">
  <testcase classname="auth.spec" name="test_login_success" time="1.2"/>
  <testcase classname="auth.spec" name="test_login_fail" time="3.3">
    <failure message="Timeout waiting for selector">Error: Timeout</failure>
  </testcase>
</testsuite>
"""
        with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-8") as f:
            f.write(xml_content)
            temp_xml = f.name

        try:
            metrics = parse_junit_xml(temp_xml)
            self.assertEqual(metrics["tests"], 2)
            self.assertEqual(metrics["failures"], 1)
            self.assertEqual(metrics["time"], 4.5)
            self.assertEqual(len(metrics["cases"]), 2)
            self.assertEqual(metrics["cases"][0]["status"], "PASSED")
            self.assertEqual(metrics["cases"][1]["status"], "FAILED")
        finally:
            if os.path.exists(temp_xml):
                os.remove(temp_xml)

    def test_client_test_connection_live_mock(self):
        """Tests test_connection() against mock Jira server."""
        cfg = JiraConfig(base_url=self.mock_url, email="test@ex.com", api_token="tok")
        client = JiraClient(cfg)
        res = client.test_connection()
        self.assertEqual(res.get("name"), "qa_tester")

    def test_pull_story_mock(self):
        """Tests pulling story requirement into Markdown file."""
        cfg = JiraConfig(base_url=self.mock_url, email="test@ex.com", api_token="tok")
        client = JiraClient(cfg)

        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = pull_story(client, "KAN-1", out_dir=tmpdir)
            self.assertTrue(os.path.isfile(md_path))
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("Forgot Password Feature", content)
            self.assertIn("KAN-1", content)

    def test_push_tests_and_create_bug(self):
        """Tests push_tests_from_file and create_bug_report with mock server."""
        cfg = JiraConfig(base_url=self.mock_url, email="test@ex.com", api_token="tok", project_key="KAN")
        client = JiraClient(cfg)

        sample_md = """
| ID | Summary | Expected |
|---|---|---|
| TC-10 | Check reset link | Link valid |
"""
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(sample_md)
            temp_md = f.name

        with tempfile.NamedTemporaryFile("w", suffix=".png", delete=False) as f:
            f.write("fake-png-content")
            temp_png = f.name

        try:
            # 1. Push test
            created = push_tests_from_file(client, temp_md, story_key="KAN-1")
            self.assertEqual(len(created), 1)
            self.assertEqual(created[0].get("key"), "KAN-99")

            # 2. Create bug
            bug_res = create_bug_report(
                client,
                summary="Null pointer on submit",
                trace="NullPointerException at line 42",
                screenshot_path=temp_png,
                suite_name="AuthSuite"
            )
            self.assertEqual(bug_res.get("key"), "KAN-99")
        finally:
            if os.path.exists(temp_md):
                os.remove(temp_md)
            if os.path.exists(temp_png):
                os.remove(temp_png)

    def test_dry_run_guarantee(self):
        """Verifies dry-run never makes real HTTP requests."""
        cfg = JiraConfig(base_url="http://invalid-non-existent-domain-12345.xyz")
        client = JiraClient(cfg, dry_run=True)

        res = client.create_issue("Test Summary", "Test Desc", "Bug")
        self.assertEqual(res.get("key"), "QA-DRYRUN")
        self.assertTrue(res.get("dry_run"))


if __name__ == "__main__":
    unittest.main()
