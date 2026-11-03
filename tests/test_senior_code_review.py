#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "tools")
sys.path.insert(0, TOOLS_DIR)

from senior_code_review import parse_diff, analyze_diff, format_report


class TestSeniorCodeReview(unittest.TestCase):

    def test_parse_diff_added_lines(self):
        sample_diff = """diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -10,2 +10,4 @@
 def handle():
+    token = "secret_12345678"
+    Thread.sleep(5000)
     return True
"""
        files = parse_diff(sample_diff)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["path"], "src/app.py")
        self.assertEqual(len(files[0]["added_lines"]), 2)

    def test_analyze_diff_catches_secret_and_sleep(self):
        sample_diff = """diff --git a/src/auth.py b/src/auth.py
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,1 +1,4 @@
+api_key = "my_secret_token_abcdef123"
+time.sleep(5000)
+try:
+    pass
+except Exception: pass
"""
        files = parse_diff(sample_diff)
        findings, cuttable = analyze_diff(files, ".")
        severities = [f.severity for f in findings]
        self.assertIn("Must fix", severities)
        self.assertIn("Should fix", severities)

    def test_format_report_clean(self):
        report = format_report([], [], 0)
        self.assertIn("No changes found", report)


if __name__ == "__main__":
    unittest.main()
