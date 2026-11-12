# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

import os
import sys
import tempfile
import unittest

# Add tools directory to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "tools"))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import pinpoint_failure


class TestPinpointFailure(unittest.TestCase):
    """Unit tests verifying pinpoint_failure report parsing and fail-closed behaviors."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_find_latest_report_multi_directory(self):
        """Verifies report discovery across test-results, reports, and legacy Reports."""
        tr_dir = os.path.join(self.root, "test-results")
        os.makedirs(tr_dir, exist_ok=True)
        xml_file = os.path.join(tr_dir, "junit.xml")
        with open(xml_file, "w", encoding="utf-8") as f:
            f.write("<testsuites></testsuites>")

        found = pinpoint_failure.find_latest_report(search_dir=self.root)
        self.assertIsNotNone(found)
        self.assertEqual(os.path.normpath(found), os.path.normpath(xml_file))

    def test_parse_failures_extracts_root_cause(self):
        """Verifies extraction of failed test case names and root causes."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="Suite1" tests="2" failures="1" errors="0" time="1.5">
    <testcase name="test_login_success" time="0.5"/>
    <testcase name="test_login_failure" time="1.0">
        <failure message="AssertionError: Expected 'Welcome' but got 'Login'">
File "tests/test_auth.py", line 42, in test_login_failure
    assert "Welcome" in title
        </failure>
    </testcase>
</testsuite>
"""
        report_path = os.path.join(self.root, "report.xml")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(xml_content)

        failures = pinpoint_failure.parse_failures(report_path)
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["tc"], "test_login_failure")
        self.assertIn("AssertionError", failures[0]["reason"])
        self.assertIn("tests/test_auth.py:42", failures[0]["failed_at"])

    def test_parse_failures_clean_pass(self):
        """Verifies zero failures returned for passing test suite."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="SuitePass" tests="1" failures="0" errors="0" time="0.2">
    <testcase name="test_ok" time="0.2"/>
</testsuite>
"""
        report_path = os.path.join(self.root, "pass_report.xml")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(xml_content)

        failures = pinpoint_failure.parse_failures(report_path)
        self.assertEqual(len(failures), 0)


if __name__ == "__main__":
    unittest.main()
