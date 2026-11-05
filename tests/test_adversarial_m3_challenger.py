#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Adversarial Stress Test Suite for Synapse Observer & Humanize Linter
Empirical Challenger 1 - Milestone 3
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from tools.synapse_observer import (
    SynapseObserver,
    is_page_class_file,
)
from tools.humanize_linter import (
    HumanizeLinter,
)


class TestSynapseObserverAdversarial(unittest.TestCase):
    """Stress testing edge cases, boundary conditions, and memory corruption in tools/synapse_observer.py"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.memory_file = Path(self.temp_dir.name) / "observer_mem.json"
        self.observer = SynapseObserver(memory_path=self.memory_file)
        self.script_path = ROOT / "tools" / "synapse_observer.py"

    def tearDown(self):
        self.temp_dir.cleanup()

    # --- Category 1: Deep Nested Page Paths & File Recognition ---

    def test_deeply_nested_page_paths_recognized(self):
        """Valid Page Classes in deep directory hierarchies must be recognized."""
        paths = [
            "src/main/groovy/com/enterprise/deeply/nested/modules/order/pages/CheckoutPage.groovy",
            "frontend/src/views/page_objects/billing/InvoiceTablePage.ts",
            "katalon/Object Repository/subfolder/nested/LoginPage.groovy",
            "e2e/pages/admin/user_management_page.py",
            "tests/e2e/pages/base/ModalPage.ts",
        ]
        for p in paths:
            with self.subTest(path=p):
                self.assertTrue(is_page_class_file(p), f"Should recognize Page Class path: {p}")

    def test_bug_test_files_with_page_in_name_misclassified_as_page_class(self):
        """BUG: Test scripts matching 'test_*_page.py' are erroneously treated as Page Classes due to '_page.' check."""
        test_script_paths = [
            "tests/test_login_page.py",
            "tests/e2e/test_checkout_page.py",
            "specs/admin_user_page.spec.ts",
        ]
        for p in test_script_paths:
            with self.subTest(path=p):
                # Test scripts MUST NOT be classified as Page Classes
                self.assertFalse(is_page_class_file(p), f"Test script erroneously treated as Page Class: {p}")

    def test_bug_raw_locator_bypass_in_test_login_page(self):
        """BUG: A test script named 'test_login_page.py' allows raw locators through without triggering Clean POM alert."""
        diff = (
            "diff --git a/tests/test_login_page.py b/tests/test_login_page.py\n"
            "--- a/tests/test_login_page.py\n"
            "+++ b/tests/test_login_page.py\n"
            "@@ -10,3 +10,4 @@\n"
            "+    driver.findElement(By.xpath('//button[@id=\"submit\"]')).click()\n"
        )
        alert = self.observer.evaluate_diff(diff)
        self.assertIsNotNone(alert, "Raw locator in test_login_page.py should trigger Clean POM alert")
        self.assertEqual(alert.tag, "Heads up")

    # --- Category 2: Comments Containing Locators ---

    def test_pure_single_line_comments_ignored(self):
        """Pure single line comments should never trigger locator alerts."""
        diff = (
            "+    // By.xpath('//div')\n"
            "+    # driver.findElement(By.cssSelector('.btn'))\n"
            "+    /* By.xpath('//button') */\n"
            "+    * page.locator('//span')\n"
        )
        alert = self.observer.evaluate_diff(diff)
        self.assertIsNone(alert)

    def test_inline_comments_with_locators(self):
        """Inline trailing comments with locators are currently captured as code lines."""
        diff = (
            "diff --git a/tests/test_cart.py b/tests/test_cart.py\n"
            "--- a/tests/test_cart.py\n"
            "+++ b/tests/test_cart.py\n"
            "@@ -10,3 +10,4 @@\n"
            "+    total = calculate_cart() # By.xpath('//span') was old way\n"
        )
        alert = self.observer.evaluate_diff(diff)
        # Note: trailing comments currently flag the line
        self.assertIsNotNone(alert)

    # --- Category 3: Sleeps and Smart Waits ---

    def test_static_sleep_detected_standard(self):
        """Standard static sleeps must trigger alerts."""
        for pattern in ["Thread.sleep(1000)", "time.sleep(5)", "page.wait_for_timeout(3000)", "WebUI.delay(2)"]:
            diff = f"+    {pattern}"
            alert = self.observer.evaluate_diff(diff)
            self.assertIsNotNone(alert, f"Failed to detect: {pattern}")
            self.assertEqual(alert.topic_key, "static_sleep_flakiness")

    def test_bug_sleep_with_spaces_inside_parentheses_missed(self):
        """BUG: sleep( 5000 ) with whitespace inside parentheses is missed by sleep(\\d+ regex."""
        diff = "+    sleep( 5000 )"
        alert = self.observer.evaluate_diff(diff)
        self.assertIsNotNone(alert, "sleep( 5000 ) with internal whitespace should trigger static sleep alert")

    # --- Category 4: List Insert vs DB Mutations ---

    def test_python_list_insert_immunity(self):
        """List insert operations must not trigger DB creation alerts."""
        diff = (
            "+    items.insert(0, new_item)\n"
            "+    cache_data.insert(1, val)\n"
        )
        alert = self.observer.evaluate_diff(diff)
        self.assertIsNone(alert)

    def test_db_insert_without_teardown_detected(self):
        """Real DB mutations without cleanup must trigger alert."""
        diff = "+    db.insert({'user': 'alice'})"
        alert = self.observer.evaluate_diff(diff)
        self.assertIsNotNone(alert)
        self.assertEqual(alert.topic_key, "missing_teardown_cleanup")

    # --- Category 5: Memory Corruption Resilience ---

    def test_bug_corrupted_memory_json_array_crashes(self):
        """BUG: Memory file containing valid JSON array raises uncaught AttributeError in _load_acknowledged_topics."""
        self.memory_file.write_text('["topic1", "topic2"]', encoding="utf-8")
        obs = SynapseObserver(memory_path=self.memory_file)
        self.assertEqual(obs.acknowledged_topics, set())

    def test_bug_corrupted_memory_json_number_crashes(self):
        """BUG: Memory file containing valid JSON number raises uncaught AttributeError."""
        self.memory_file.write_text("42", encoding="utf-8")
        obs = SynapseObserver(memory_path=self.memory_file)
        self.assertEqual(obs.acknowledged_topics, set())

    def test_bug_corrupted_memory_json_null_crashes(self):
        """BUG: Memory file containing valid JSON null raises uncaught AttributeError."""
        self.memory_file.write_text("null", encoding="utf-8")
        obs = SynapseObserver(memory_path=self.memory_file)
        self.assertEqual(obs.acknowledged_topics, set())

    def test_bug_cli_file_pointing_to_directory_crashes(self):
        """BUG: synapse_observer.py --file <directory> crashes with PermissionError instead of clean error exit."""
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--file", str(ROOT / "tools")],
            capture_output=True,
            text=True,
        )
        # Should gracefully exit with code 2, not crash with traceback (code 1)
        self.assertEqual(res.returncode, 2)
        self.assertNotIn("Traceback", res.stderr)


class TestHumanizeLinterAdversarial(unittest.TestCase):
    """Stress testing markdown parsing, punctuation, and edge cases in tools/humanize_linter.py"""

    def setUp(self):
        self.linter = HumanizeLinter(check_pileup=True)
        self.script_path = ROOT / "tools" / "humanize_linter.py"

    # --- Category 6: Markdown Masking & Code Fences ---

    def test_unclosed_code_fence_extends_to_eof(self):
        """Unclosed code fence at EOF masks all subsequent text per CommonMark."""
        text = (
            "Intro text.\n"
            "```python\n"
            "def leverage_everything():\n"
            "    return optimize()\n"
        )
        issues = self.linter.lint_text(text)
        self.assertEqual(len(issues), 0, "Keywords inside unclosed fence should be masked")

    def test_nested_backtick_spans(self):
        """Double backtick inline code spans are masked correctly."""
        text = "Use the double-backtick `` `leverage` `` pattern for quoting."
        issues = self.linter.lint_text(text)
        self.assertEqual(len(issues), 0)

    def test_bug_italicized_buzzwords_with_underscores_missed(self):
        """BUG: Buzzwords italicized with markdown underscores like '_optimize_' or '_leverage_' bypass \\b boundary."""
        text = "We need to _optimize_ the test execution."
        issues = self.linter.lint_text(text)
        self.assertTrue(any("optimize" in i.matched_text.lower() for i in issues), "Failed to detect _optimize_")

    def test_bug_semicolon_in_html_entities_flagged_as_prose(self):
        """BUG: Common HTML entities like '&nbsp;' and '&quot;' trigger false positive 'semicolon in prose'."""
        text = "Use a non-breaking&nbsp;space and clean formatting."
        issues = self.linter.lint_text(text)
        semi_issues = [i for i in issues if i.matched_text == ";"]
        self.assertEqual(len(semi_issues), 0, "HTML entity semicolons should not be flagged as prose semicolons")

    def test_bug_buzzwords_in_markdown_headers_skipped(self):
        """BUG: Markdown headers starting with '#' are unconditionally skipped, ignoring buzzwords."""
        text = "# A Comprehensive Guide to Leveraging Automated Testing\nProse content."
        issues = self.linter.lint_text(text)
        self.assertTrue(any("leverag" in i.matched_text.lower() for i in issues), "Buzzwords in headers should not be skipped")

    def test_buzzwords_in_markdown_table_detected(self):
        """Buzzwords inside markdown tables are detected."""
        text = (
            "| Step | Action | Outcome |\n"
            "| --- | --- | --- |\n"
            "| 1 | Leverage existing helper | Streamlined run |\n"
        )
        issues = self.linter.lint_text(text)
        matched = [i.matched_text.lower() for i in issues]
        self.assertTrue(any("leverage" in m for m in matched))
        self.assertTrue(any("streamlined" in m for m in matched))

    # --- Category 7: CLI Error Handling ---

    def test_bug_nonexistent_file_exits_0_reporting_clean(self):
        """BUG: humanize_linter.py --file <nonexistent> reports 'Clean!' with exit code 0 instead of error."""
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--file", "nonexistent_file_xyz.md"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(res.returncode, 0, "Non-existent file should exit with non-zero error code")
        self.assertNotIn("Clean!", res.stdout)

    def test_bug_directory_as_file_exits_0_reporting_clean(self):
        """BUG: humanize_linter.py --file <dir> reports 'Clean!' with exit code 0 instead of error."""
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--file", str(ROOT / "tools")],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(res.returncode, 0, "Directory passed as file should exit with error code")
        self.assertNotIn("Clean!", res.stdout)

    def test_large_document_performance(self):
        """200k character document should lint without timeout or stack overflow."""
        paragraph = "We use standard methods to improve speed and verify components.\n" * 1000
        text = paragraph + "Finally, we leverage one tool; all done.\n"
        issues = self.linter.lint_text(text)
        self.assertGreaterEqual(len(issues), 1)


if __name__ == "__main__":
    unittest.main()
