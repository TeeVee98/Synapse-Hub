#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Unit tests for tools/synapse_observer.py
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from tools.synapse_observer import SynapseObserver, format_observer_output


class TestSynapseObserver(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.memory_file = Path(self.temp_dir.name) / "test_memory.json"
        self.observer = SynapseObserver(memory_path=self.memory_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_clean_diff_returns_learn_none(self):
        diff = "+    LoginPage.submitForm()\n+    DashboardPage.verifyHeader()"
        alert = self.observer.evaluate_diff(diff)
        self.assertIsNone(alert)
        self.assertEqual(format_observer_output(alert), "learn: none")

    def test_raw_locator_triggers_heads_up(self):
        diff = "+    driver.findElement(By.xpath('//div[@id=\"btn\"]')).click()"
        alert = self.observer.evaluate_diff(diff)
        self.assertIsNotNone(alert)
        self.assertEqual(alert.tag, "Heads up")
        self.assertEqual(alert.topic_key, "clean_pom_raw_locator")
        self.assertIn("Clean POM", alert.explanation[0])

    def test_page_class_locators_do_not_trigger_heads_up(self):
        diff = (
            "diff --git a/pages/LoginPage.groovy b/pages/LoginPage.groovy\n"
            "--- a/pages/LoginPage.groovy\n"
            "+++ b/pages/LoginPage.groovy\n"
            "@@ -10,3 +10,4 @@\n"
            "+    static final TestObject BTN_LOGIN = By.xpath('//button[@id=\"login\"]')\n"
        )
        alert = self.observer.evaluate_diff(diff)
        self.assertIsNone(alert, "Page Classes must be immune from Clean POM raw locator alerts")

    def test_test_script_locators_trigger_heads_up(self):
        diff = (
            "diff --git a/tests/test_checkout.py b/tests/test_checkout.py\n"
            "--- a/tests/test_checkout.py\n"
            "+++ b/tests/test_checkout.py\n"
            "@@ -25,3 +25,4 @@\n"
            "+    page.locator('//button[@id=\"checkout\"]').click()\n"
        )
        alert = self.observer.evaluate_diff(diff)
        self.assertIsNotNone(alert)
        self.assertEqual(alert.tag, "Heads up")
        self.assertTrue(alert.topic_key.startswith("clean_pom_raw_locator"))

    def test_static_sleep_triggers_heads_up(self):
        diff = "+    Thread.sleep(3000)"
        alert = self.observer.evaluate_diff(diff)
        self.assertIsNotNone(alert)
        self.assertEqual(alert.tag, "Heads up")
        self.assertEqual(alert.topic_key, "static_sleep_flakiness")

    def test_playwright_wait_for_timeout_triggers_heads_up(self):
        diff = "+    page.wait_for_timeout(5000)"
        alert = self.observer.evaluate_diff(diff)
        self.assertIsNotNone(alert)
        self.assertEqual(alert.tag, "Heads up")
        self.assertEqual(alert.topic_key, "static_sleep_flakiness")

    def test_katalon_webui_delay_triggers_heads_up(self):
        diff = "+    WebUI.delay(10)"
        alert = self.observer.evaluate_diff(diff)
        self.assertIsNotNone(alert)
        self.assertEqual(alert.tag, "Heads up")
        self.assertEqual(alert.topic_key, "static_sleep_flakiness")

    def test_python_list_insert_does_not_trigger_false_positive(self):
        diff = (
            "+    items.insert(0, new_item)\n"
            "+    record_list.insert(idx, value)\n"
        )
        alert = self.observer.evaluate_diff(diff)
        self.assertIsNone(alert, "Python list.insert operations must not trigger missing teardown cleanup")

    def test_unpaired_creation_triggers_you_should_know(self):
        diff = "+    POST /api/users to createEntity('user_123')"
        alert = self.observer.evaluate_diff(diff)
        self.assertIsNotNone(alert)
        self.assertEqual(alert.tag, "You should know")
        self.assertEqual(alert.topic_key, "missing_teardown_cleanup")

    def test_dropdown_word_does_not_mask_missing_teardown(self):
        diff = (
            "+    POST /api/users to createEntity('user_123')\n"
            "+    select.select_by_text('drop-down option')\n"
        )
        alert = self.observer.evaluate_diff(diff)
        self.assertIsNotNone(alert, "drop-down must not be confused with database drop/teardown")
        self.assertEqual(alert.topic_key, "missing_teardown_cleanup")

    def test_creation_paired_with_teardown_returns_none(self):
        diff = (
            "+    POST /api/users to createEntity('user_123')\n"
            "+    teardown: deleteEntity('user_123')\n"
        )
        alert = self.observer.evaluate_diff(diff)
        self.assertIsNone(alert)

    def test_shortcut_triggers_you_should_know(self):
        diff = "+    // shortcut: Skip regex validation for speed, upgrade when scaling"
        alert = self.observer.evaluate_diff(diff)
        self.assertIsNotNone(alert)
        self.assertEqual(alert.tag, "You should know")
        self.assertTrue(alert.topic_key.startswith("shortcut_"))

    def test_unique_shortcut_slugs(self):
        diff1 = "+    // shortcut: temporary sleep in tests"
        diff2 = "+    // shortcut: hardcoded api token"
        alert1 = self.observer.evaluate_diff(diff1)
        alert2 = self.observer.evaluate_diff(diff2)
        self.assertIsNotNone(alert1)
        self.assertIsNotNone(alert2)
        self.assertNotEqual(alert1.topic_key, alert2.topic_key)

    def test_anti_nagging_memory_suppresses_acknowledged_topic(self):
        diff = "+    Thread.sleep(3000)"
        # 1. Before ack
        alert = self.observer.evaluate_diff(diff)
        self.assertIsNotNone(alert)

        # 2. Ack topic
        self.observer.acknowledge_topic("static_sleep_flakiness")

        # 3. After ack
        alert_after = self.observer.evaluate_diff(diff)
        self.assertIsNone(alert_after)

    def test_cli_reset_and_unack(self):
        self.observer.acknowledge_topic("topic_a")
        self.observer.acknowledge_topic("topic_b")
        self.assertIn("topic_a", self.observer.acknowledged_topics)

        # Unack topic_a
        removed = self.observer.unacknowledge_topic("topic_a")
        self.assertTrue(removed)
        self.assertNotIn("topic_a", self.observer.acknowledged_topics)
        self.assertIn("topic_b", self.observer.acknowledged_topics)

        # Reset memory
        self.observer.reset_memory()
        self.assertEqual(len(self.observer.acknowledged_topics), 0)

    def test_corrupted_memory_file_graceful_fallback(self):
        self.memory_file.write_text("NOT_VALID_JSON{", encoding="utf-8")
        observer = SynapseObserver(memory_path=self.memory_file)
        self.assertEqual(observer.acknowledged_topics, set())

    def test_evaluate_diff_return_all(self):
        diff = (
            "+    driver.findElement(By.xpath('//btn')).click()\n"
            "+    Thread.sleep(1000)\n"
        )
        alerts = self.observer.evaluate_diff(diff, return_all=True)
        self.assertIsInstance(alerts, list)
        self.assertGreaterEqual(len(alerts), 2)

    def test_cli_json_and_strict_modes(self):
        script_path = Path(__file__).parent.parent / "tools" / "synapse_observer.py"

        # 1. Strict mode with text alert -> exit code 1
        res = subprocess.run(
            [sys.executable, str(script_path), "--text", "+ Thread.sleep(2000)", "--strict", "--json", "--memory-file", str(self.memory_file)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertEqual(data.get("tag"), "Heads up")

        # 2. Strict mode with clean text -> exit code 0
        res_clean = subprocess.run(
            [sys.executable, str(script_path), "--text", "+ cleanFunction()", "--strict", "--json", "--memory-file", str(self.memory_file)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(res_clean.returncode, 0)
        data_clean = json.loads(res_clean.stdout)
        self.assertEqual(data_clean.get("learn"), "none")


if __name__ == "__main__":
    unittest.main()
