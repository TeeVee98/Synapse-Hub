#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Unit tests for tools/tms_sync_bridge.py (Jira, Xray, TestRail Enterprise REST Adapters)
"""

import sys
import json
import base64
import unittest
import subprocess
from io import BytesIO
from unittest.mock import patch, MagicMock

from tools.tms_sync_bridge import (
    TMSBridge,
    build_jira_v3_adf_description,
    text_to_adf,
    adf_to_text,
)


class TestTMSSyncBridge(unittest.TestCase):
    def setUp(self):
        self.bridge = TMSBridge(provider="jira", base_url="", api_token="", user_email="tester@test.local")

    def test_mock_initialization(self):
        self.assertTrue(self.bridge.is_mock)
        self.assertEqual(self.bridge.provider, "jira")
        self.assertEqual(self.bridge.base_url, "https://mock-alm.enterprise.local")

    def test_pull_story_acceptance_criteria(self):
        story = self.bridge.pull_story_acceptance_criteria("PROJ-999")
        self.assertEqual(story["issue_key"], "PROJ-999")
        self.assertEqual(story["issue_type"], "Story")
        self.assertIn("acceptance_criteria", story)
        self.assertGreater(len(story["acceptance_criteria"]), 0)
        self.assertIn("gherkin_feature", story)

    def test_report_defect(self):
        defect = self.bridge.report_defect(
            project_key="BILLING",
            test_case_id="TC_PAYMENT_01",
            summary="Payment gateway timeout",
            error_message="Gateway timeout 504",
            stack_trace="Traceback: line 42",
            screenshot_path="Screenshots/FAILED_payment.png",
            severity="Critical",
        )
        self.assertEqual(defect["project"], "BILLING")
        self.assertEqual(defect["severity"], "Critical")
        self.assertEqual(defect["test_case_id"], "TC_PAYMENT_01")
        self.assertIn("ticket_key", defect)
        self.assertIn("reproduction_steps", defect)

    def test_sync_execution_results(self):
        results = [
            {"test_key": "TC-01", "status": "PASS", "duration_sec": 1.2},
            {"test_key": "TC-02", "status": "PASS", "duration_sec": 0.8},
            {"test_key": "TC-03", "status": "FAIL", "duration_sec": 2.5},
        ]
        sync_report = self.bridge.sync_execution_results("PLAN-101", results)
        self.assertEqual(sync_report["test_plan_key"], "PLAN-101")
        self.assertEqual(sync_report["total_synced"], 3)
        self.assertEqual(sync_report["passed"], 2)
        self.assertEqual(sync_report["failed"], 1)
        self.assertAlmostEqual(sync_report["pass_rate_pct"], 66.67, places=1)
        self.assertEqual(sync_report["sync_status"], "SUCCESS")

    def test_auth_headers_bearer_and_basic(self):
        # Basic Auth
        b_basic = TMSBridge(
            provider="jira",
            base_url="https://jira.enterprise.local",
            api_token="mypassword",
            user_email="agent@enterprise.local",
            auth_type="basic",
        )
        self.assertFalse(b_basic.is_mock)
        headers = b_basic.get_auth_headers()
        self.assertIn("Authorization", headers)
        self.assertTrue(headers["Authorization"].startswith("Basic "))
        decoded = base64.b64decode(headers["Authorization"].split()[1]).decode("utf-8")
        self.assertEqual(decoded, "agent@enterprise.local:mypassword")

        # Bearer Auth
        b_bearer = TMSBridge(
            provider="xray",
            base_url="https://xray.cloud.getxray.app",
            api_token="my_jwt_bearer_token",
            auth_type="bearer",
        )
        headers_b = b_bearer.get_auth_headers()
        self.assertEqual(headers_b["Authorization"], "Bearer my_jwt_bearer_token")

        # OAuth2 token header
        b_oauth = TMSBridge(
            provider="testrail",
            base_url="https://testrail.enterprise.local",
            api_token="Bearer my_oauth_token",
            auth_type="oauth2",
        )
        headers_o = b_oauth.get_auth_headers()
        self.assertEqual(headers_o["Authorization"], "Bearer my_oauth_token")

    def test_testrail_v2_adapters(self):
        tr = TMSBridge(provider="testrail", base_url="", api_token="")
        self.assertTrue(tr.is_mock)
        self.assertEqual(tr.provider, "testrail")

        # testrail_get_tests
        tests = tr.testrail_get_tests(run_id=42)
        self.assertIsInstance(tests, list)
        self.assertGreater(len(tests), 0)
        self.assertEqual(tests[0]["case_id"], 101)

        # testrail_get_case
        case = tr.testrail_get_case(case_id=101)
        self.assertEqual(case["id"], 101)
        self.assertIn("title", case)

        # testrail_add_result_for_case
        res = tr.testrail_add_result_for_case(run_id=42, case_id=101, status_id=1, comment="Unit test passed")
        self.assertEqual(res["status_id"], 1)
        self.assertEqual(res["comment"], "Unit test passed")

        # pull_story_acceptance_criteria with TestRail case
        story = tr.pull_story_acceptance_criteria("C1042")
        self.assertEqual(story["issue_key"], "C1042")
        self.assertEqual(story["issue_type"], "Story")

        # report_defect with TestRail provider
        defect = tr.report_defect(
            project_key="TR",
            test_case_id="TC-205",
            summary="Payment crashed",
            error_message="500 Server Error"
        )
        self.assertEqual(defect["project"], "TR")
        self.assertEqual(defect["test_case_id"], "TC-205")

    def test_xray_adapters(self):
        xray = TMSBridge(provider="xray", base_url="", api_token="")
        self.assertTrue(xray.is_mock)
        self.assertEqual(xray.provider, "xray")

        # xray_import_execution
        tests_data = [
            {"testKey": "PROJ-1", "status": "PASSED"},
            {"testKey": "PROJ-2", "status": "FAILED"},
        ]
        res = xray.xray_import_execution(test_execution_key="EXEC-100", tests=tests_data)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["imported_tests_count"], 2)

        # xray_authenticate
        tok = xray.xray_authenticate(client_id="client_123", client_secret="secret_abc")
        self.assertIn("jwt", tok)

        # sync_execution_results with Xray
        sync_res = xray.sync_execution_results("EXEC-100", tests_data)
        self.assertEqual(sync_res["total_synced"], 2)
        self.assertEqual(sync_res["provider"], "xray")

    @patch("urllib.request.urlopen")
    def test_live_rest_request_mocking(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"key": "PROJ-123", "fields": {"summary": "Live Story"}}).encode("utf-8")
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        live_bridge = TMSBridge(
            provider="jira",
            base_url="https://live-jira.company.com",
            api_token="secret_token",
            user_email="dev@company.com",
        )
        self.assertFalse(live_bridge.is_mock)

        # Pull story
        story = live_bridge.pull_story_acceptance_criteria("PROJ-123")
        self.assertEqual(story["issue_key"], "PROJ-123")
        self.assertEqual(story["summary"], "Live Story")

        # Report defect
        mock_response.read.return_value = json.dumps({"key": "PROJ-BUG-999"}).encode("utf-8")
        defect = live_bridge.report_defect(
            project_key="PROJ",
            test_case_id="TC-99",
            summary="Critical crash",
            error_message="Exception thrown",
        )
        self.assertEqual(defect["ticket_key"], "PROJ-BUG-999")
        self.assertEqual(defect["status"], "Submitted")

    def test_adf_builder_and_text_conversion(self):
        adf = build_jira_v3_adf_description(
            test_case_id="TC-LOGIN-01",
            error_message="AssertionError: 401 != 200",
            reproduction_steps=["1. Go to /login", "2. Submit bad creds"],
            stack_trace="Traceback: line 99",
        )
        self.assertEqual(adf["type"], "doc")
        self.assertEqual(adf["version"], 1)
        self.assertIsInstance(adf["content"], list)
        self.assertGreater(len(adf["content"]), 3)

        # Verify round-trip extraction via adf_to_text
        text = adf_to_text(adf)
        self.assertIn("TC-LOGIN-01", text)
        self.assertIn("AssertionError", text)
        self.assertIn("Traceback", text)

        # Verify text_to_adf
        adf_from_text = text_to_adf("First paragraph.\n\nSecond paragraph.")
        self.assertEqual(adf_from_text["type"], "doc")
        self.assertEqual(len(adf_from_text["content"]), 2)

    def test_adf_empty_fields_sanitized(self):
        adf = build_jira_v3_adf_description(
            test_case_id="",
            error_message="",
            reproduction_steps=["", "   "],
            stack_trace="   "
        )
        self.assertEqual(adf["type"], "doc")

        def _check_no_empty_text(node):
            if isinstance(node, dict):
                if node.get("type") == "text":
                    self.assertTrue(len(node.get("text", "")) > 0, "Found empty text node in ADF")
                for child in node.get("content", []):
                    _check_no_empty_text(child)
            elif isinstance(node, list):
                for item in node:
                    _check_no_empty_text(item)

        _check_no_empty_text(adf)

    def test_adf_hardbreak_handling(self):
        sample_adf = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Line 1"},
                        {"type": "hardBreak"},
                        {"type": "text", "text": "Line 2"},
                    ]
                }
            ]
        }
        res_text = adf_to_text(sample_adf)
        self.assertIn("Line 1\nLine 2", res_text)

    def test_cli_pull_command(self):
        res = subprocess.run(
            [sys.executable, "tools/tms_sync_bridge.py", "pull", "PROJ-123", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("PROJ-123", res.stdout)

    def test_cli_report_bug_command(self):
        res = subprocess.run(
            [sys.executable, "tools/tms_sync_bridge.py", "report-bug", "--tc-id", "TC-01", "--summary", "Bug title", "--error", "NullPointer", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("TC-01", res.stdout)

    def test_cli_sync_run_command_with_providers(self):
        for prov in ("jira", "testrail", "xray"):
            res = subprocess.run(
                [sys.executable, "tools/tms_sync_bridge.py", "--provider", prov, "sync-run", "--plan-key", f"RUN-{prov.upper()}", "--json"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0, f"CLI sync-run failed for provider {prov}: {res.stderr}")
            self.assertIn("RUN-", res.stdout)

    def test_testrail_report_defect_non_numeric_case_id_no_fallthrough(self):
        # When test_case_id has no digits, TestRail mode should not fall through to Jira REST API
        bridge = TMSBridge(
            provider="testrail",
            base_url="https://company.testrail.io",
            api_token="valid_secret_token",
            user_email="tester@company.com",
            auth_type="basic",
        )
        defect = bridge.report_defect(
            project_key="QA",
            test_case_id="TC_LOGIN_NO_DIGITS",
            summary="Login failed",
            error_message="Invalid credentials",
        )
        self.assertEqual(defect["status"], "Drafted (Offline Fallback)")
        self.assertIn("numeric Case ID", defect["live_error"])
        # Must not have called Jira API endpoint
        self.assertNotIn("404", defect.get("live_error", ""))

    def test_testrail_and_xray_url_normalization(self):
        # TestRail trailing index.php or /api/v2 stripping
        tr1 = TMSBridge(provider="testrail", base_url="https://tr.example.com", api_token="tok")
        self.assertEqual(tr1._testrail_url("get_tests/1"), "https://tr.example.com/index.php?/api/v2/get_tests/1")

        tr2 = TMSBridge(provider="testrail", base_url="https://tr.example.com/index.php", api_token="tok")
        self.assertEqual(tr2._testrail_url("get_tests/1"), "https://tr.example.com/index.php?/api/v2/get_tests/1")

        # Xray Cloud vs Server URL normalization
        xr_cloud = TMSBridge(provider="xray", base_url="https://xray.cloud.getxray.app/api/v2", api_token="tok")
        self.assertEqual(xr_cloud._xray_url("import/execution"), "https://xray.cloud.getxray.app/api/v2/import/execution")

        xr_server = TMSBridge(provider="xray", base_url="https://jira.internal.local/rest/raven/1.0", api_token="tok")
        self.assertEqual(xr_server._xray_url("import/execution"), "https://jira.internal.local/rest/raven/1.0/import/execution")


if __name__ == "__main__":
    unittest.main()
