#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Unit tests for tools/safety_firewall.py
"""

import unittest
from tools.safety_firewall import (
    is_action_dangerous,
    inspect_and_authorize,
    detect_action_loop,
)


class TestSafetyFirewallExtended(unittest.TestCase):
    def test_is_action_dangerous_destructive_keywords(self):
        dangerous_texts = [
            "Delete All Accounts",
            "Drop Database",
            "Purge Logs",
            "Wipe All Records",
            "Destroy Infrastructure",
            "Pay $5000 Now",
        ]
        for t in dangerous_texts:
            is_dang, reason = is_action_dangerous("click", text=t)
            self.assertTrue(is_dang, f"Expected '{t}' to be marked dangerous, but got: {reason}")

    def test_is_action_dangerous_safe_texts(self):
        safe_texts = [
            "Save Changes",
            "Next Page",
            "Filter Invoices",
            "Search Products",
            "Submit Form",
        ]
        for t in safe_texts:
            is_dang, _ = is_action_dangerous("click", text=t)
            self.assertFalse(is_dang, f"Expected '{t}' to be safe")

    def test_inspect_and_authorize_modes(self):
        blocked = inspect_and_authorize("click", text="Drop Database", force=False)
        self.assertFalse(blocked["authorized"])
        self.assertFalse(blocked["bypass_granted"])

        bypassed = inspect_and_authorize("click", text="Drop Database", force=True)
        self.assertTrue(bypassed["authorized"])
        self.assertTrue(bypassed["bypass_granted"])

    def test_detect_action_loop_consecutive(self):
        actions = ["click", "click", "click", "click", "click"]
        res = detect_action_loop(actions, repeat_threshold=4)
        self.assertTrue(res["loop_detected"])
        self.assertEqual(res["type"], "consecutive_repeat")

    def test_detect_action_loop_cycle_2(self):
        actions = ["fill_username", "fill_password", "fill_username", "fill_password"]
        res = detect_action_loop(actions)
        self.assertTrue(res["loop_detected"])
        self.assertEqual(res["type"], "cycle_2")

    def test_detect_action_loop_cycle_3(self):
        actions = ["step_a", "step_b", "step_c", "step_a", "step_b", "step_c"]
        res = detect_action_loop(actions)
        self.assertTrue(res["loop_detected"])
        self.assertEqual(res["type"], "cycle_3")

    def test_detect_action_loop_no_loop(self):
        actions = ["navigate", "fill", "click", "assert_visible"]
        res = detect_action_loop(actions)
        self.assertFalse(res["loop_detected"])


if __name__ == "__main__":
    unittest.main()
