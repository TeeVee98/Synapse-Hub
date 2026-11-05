#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Unit tests for tools/humanize_linter.py
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from tools.humanize_linter import HumanizeLinter


class TestHumanizeLinter(unittest.TestCase):
    def setUp(self):
        self.linter = HumanizeLinter(check_pileup=True)

    def test_clean_text_produces_no_issues(self):
        text = "This test verifies that the login button redirects to the dashboard."
        issues = self.linter.lint_text(text)
        self.assertEqual(len(issues), 0)

    def test_buzzwords_detected(self):
        text = "We leverage the helper to optimize execution."
        issues = self.linter.lint_text(text)
        self.assertTrue(any(i.matched_text.lower() == "leverage" for i in issues))
        self.assertTrue(any(i.matched_text.lower() == "optimize" for i in issues))

    def test_cliche_phrases_detected(self):
        text = "In conclusion, this is a testament to the fast-paced world."
        issues = self.linter.lint_text(text)
        issue_texts = [i.matched_text.lower() for i in issues]
        self.assertIn("in conclusion", issue_texts)
        self.assertIn("a testament to", issue_texts)
        self.assertIn("fast-paced world", issue_texts)

    def test_em_dash_detected(self):
        text = "Fast execution—without flakiness—is required."
        issues = self.linter.lint_text(text)
        self.assertTrue(any(i.issue_type == "punctuation" for i in issues))

    def test_pileup_detection(self):
        text = "It is crucial to verify. This crucial step is essential. Another crucial check."
        issues = self.linter.lint_text(text)
        self.assertTrue(any(i.issue_type == "pileup" and i.matched_text == "crucial" for i in issues))

    def test_fenced_code_blocks_are_masked(self):
        # Code fence contains words like 'optimize', 'leverage', 'enhance'
        text = (
            "Here is the configuration:\n"
            "```json\n"
            "{\n"
            '  "optimize": true,\n'
            '  "leverage_cache": "always"\n'
            "}\n"
            "```\n"
            "The configuration is now set up."
        )
        issues = self.linter.lint_text(text)
        self.assertEqual(len(issues), 0, "Keywords inside fenced code blocks must be masked and ignored")

    def test_inline_backticks_are_masked(self):
        text = "Call `optimize()` or `utilize()` helper to run tests."
        issues = self.linter.lint_text(text)
        self.assertEqual(len(issues), 0, "Keywords inside inline backtick spans must be masked and ignored")

    def test_inflected_verb_forms_detected(self):
        text = "We are leveraging this class and streamlining the tests after optimizing the flow."
        issues = self.linter.lint_text(text)
        matched = [i.matched_text.lower() for i in issues]
        self.assertIn("leveraging", matched)
        self.assertIn("streamlining", matched)
        self.assertIn("optimizing", matched)

    def test_semicolons_in_prose_detected(self):
        text = "The suite completed successfully; all assertions passed."
        issues = self.linter.lint_text(text)
        self.assertTrue(any(i.issue_type == "punctuation" and i.matched_text == ";" for i in issues))

    def test_semicolons_inside_code_fence_not_flagged(self):
        text = (
            "Below is a Groovy snippet:\n"
            "```groovy\n"
            "int x = 10;\n"
            'String s = "hello";\n'
            "```\n"
            "All done."
        )
        issues = self.linter.lint_text(text)
        self.assertEqual(len(issues), 0, "Semicolons inside code fences must not trigger punctuation warnings")

    def test_new_buzzwords_and_cliches(self):
        text = "This stands as a robust solution that plays a pivotal role in today's ever-evolving landscape."
        issues = self.linter.lint_text(text)
        matched = [i.matched_text.lower() for i in issues]
        self.assertTrue(any("robust" in m for m in matched))
        self.assertTrue(any("pivotal" in m for m in matched))
        self.assertTrue(any("stands as" in m for m in matched))
        self.assertTrue(any("ever-evolving" in m for m in matched))

    def test_lint_file_execution(self):
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".md", encoding="utf-8") as tmp:
            tmp.write("# Audit Guide\nWe delve into the intricate interplay of components.\n")
            tmp_path = Path(tmp.name)
        try:
            issues = self.linter.lint_file(tmp_path)
            self.assertGreaterEqual(len(issues), 2)
            matched = [i.matched_text.lower() for i in issues]
            self.assertIn("delve", matched)
            self.assertIn("intricate", matched)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_cli_strict_and_json_modes(self):
        script_path = Path(__file__).parent.parent / "tools" / "humanize_linter.py"

        # 1. Text with AI slop -> exit code 1 with --strict
        res_fail = subprocess.run(
            [sys.executable, str(script_path), "--text", "We leverage AI to optimize everything.", "--strict", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(res_fail.returncode, 1)
        data_fail = json.loads(res_fail.stdout)
        self.assertFalse(data_fail["clean"])
        self.assertGreater(data_fail["issue_count"], 0)

        # 2. Clean text -> exit code 0 with --strict
        res_pass = subprocess.run(
            [sys.executable, str(script_path), "--text", "We use standard tools to improve speed.", "--strict", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(res_pass.returncode, 0)
        data_pass = json.loads(res_pass.stdout)
        self.assertTrue(data_pass["clean"])
        self.assertEqual(data_pass["issue_count"], 0)


if __name__ == "__main__":
    unittest.main()
