#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from tools.slow_test_profiler import (
    format_markdown_report,
    parse_junit_report,
    profile_slowest_tests,
)


class TestSlowTestProfiler(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="slow_test_")
        self.xml_path = os.path.join(self.temp_dir, "junit.xml")
        xml_content = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="4" time="12.5">
    <testcase classname="tests.test_auth" name="test_login_fast" time="0.050" />
    <testcase classname="tests.test_auth" name="test_login_moderate" time="1.850" />
    <testcase classname="tests.test_e2e" name="test_checkout_slow" time="6.200" />
    <testcase classname="tests.test_api" name="test_fail_case" time="4.400">
      <failure message="assertion error" />
    </testcase>
  </testsuite>
</testsuites>
"""
        with open(self.xml_path, "w", encoding="utf-8") as f:
            f.write(xml_content)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_parse_junit_report(self):
        records = parse_junit_report(self.xml_path)
        self.assertEqual(len(records), 4)
        self.assertEqual(records[0]["duration_sec"], 0.05)
        self.assertEqual(records[0]["status"], "PASSED")
        self.assertEqual(records[3]["duration_sec"], 4.4)
        self.assertEqual(records[3]["status"], "FAILED")

    def test_profile_slowest_tests(self):
        profile = profile_slowest_tests(
            self.xml_path,
            top_n=2,
            slow_threshold_sec=5.0,
            moderate_threshold_sec=1.0,
        )

        self.assertEqual(profile["total_tests"], 4)
        self.assertEqual(profile["slow_count"], 1)  # 6.2s
        self.assertEqual(profile["moderate_count"], 2)  # 1.85s, 4.4s
        self.assertEqual(profile["fast_count"], 1)  # 0.05s
        self.assertEqual(len(profile["top_slowest"]), 2)
        self.assertEqual(profile["top_slowest"][0]["name"], "test_checkout_slow")
        self.assertEqual(profile["top_slowest"][1]["name"], "test_fail_case")

    def test_format_markdown_report(self):
        profile = profile_slowest_tests(self.xml_path, top_n=3)
        md = format_markdown_report(profile)
        self.assertIn("# Test Execution Performance & Bottleneck Profile", md)
        self.assertIn("| Rank | Duration (s) | Status | Test Identifier |", md)
        self.assertIn("test_checkout_slow", md)

    def test_cli_execution(self):
        script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "slow_test_profiler.py")
        res = subprocess.run(
            [sys.executable, script, "--report", self.xml_path, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["total_tests"], 4)


if __name__ == "__main__":
    unittest.main()
