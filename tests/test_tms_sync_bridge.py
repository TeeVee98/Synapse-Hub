#!/usr/bin/env python3
"""
Unit tests for tools/tms_sync_bridge.py
"""

import unittest
from tools.tms_sync_bridge import TMSBridge


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

    def test_cli_pull_command(self):
        import subprocess
        import sys
        res = subprocess.run(
            [sys.executable, "tools/tms_sync_bridge.py", "pull", "PROJ-123", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("PROJ-123", res.stdout)

    def test_cli_report_bug_command(self):
        import subprocess
        import sys
        res = subprocess.run(
            [sys.executable, "tools/tms_sync_bridge.py", "report-bug", "--tc-id", "TC-01", "--summary", "Bug title", "--error", "NullPointer", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("TC-01", res.stdout)


if __name__ == "__main__":
    unittest.main()
