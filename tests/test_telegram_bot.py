#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_telegram_bot.py — Unit Tests for Mobile Command, Control & Notification Adapter
"""

import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "core"))

from datetime import datetime, timezone
from telegram_bot import TelegramAdapter, send_telegram_notification, format_timestamp


class TestTelegramAdapter(unittest.TestCase):
    """Tests TelegramAdapter command routing, RBAC authorization, and state checks."""

    def setUp(self):
        self.adapter = TelegramAdapter(
            token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            allowed_chat_id="999888777",
            repo_root=REPO_ROOT,
        )

    def test_configuration_detection(self):
        """Detects whether bot token and chat ID are configured."""
        self.assertTrue(self.adapter.is_configured())

        empty_adapter = TelegramAdapter(token="", allowed_chat_id="")
        self.assertFalse(empty_adapter.is_configured())

    def test_rbac_authorization_guard(self):
        """Permits authorized chat IDs and strictly rejects unknown senders."""
        self.assertTrue(self.adapter.is_authorized("999888777"))
        self.assertFalse(self.adapter.is_authorized("111222333"))
        self.assertFalse(self.adapter.is_authorized(""))

    def test_unauthorized_command_rejection(self):
        """Unauthorized sender receives access denied notice."""
        reply = self.adapter.handle_command("/status", sender_id="111222333")
        self.assertIn("Truy cập bị từ chối", reply)
        self.assertIn("111222333", reply)

    def test_authorized_command_routing(self):
        """Authorized sender executes command and receives formatted reply."""
        # /help
        help_reply = self.adapter.handle_command("/help", sender_id="999888777")
        self.assertIn("BẢNG ĐIỀU KHIỂN TỪ XA", help_reply)
        self.assertIn("/verify", help_reply)
        self.assertIn("/exam", help_reply)
        self.assertIn("/evolve", help_reply)

        # /status
        status_reply = self.adapter.handle_command("/status", sender_id="999888777")
        self.assertIn("TRẠNG THÁI HỆ THỐNG", status_reply)
        self.assertIn("Git Commit", status_reply)

        # /tokens
        tokens_reply = self.adapter.handle_command("/tokens", sender_id="999888777")
        self.assertIn("THỐNG KÊ TOKEN", tokens_reply)
        self.assertIn("KV Cache Hit Rate", tokens_reply)

        # Unknown command
        unknown_reply = self.adapter.handle_command("/foo_bar", sender_id="999888777")
        self.assertIn("Lệnh không xác định", unknown_reply)

    def test_send_notification_unconfigured(self):
        """Notification helper returns False cleanly when unconfigured."""
        res = send_telegram_notification("Test alert", token="", chat_id="")
        self.assertFalse(res)

    def test_send_ci_notification_unconfigured(self):
        """CI notification returns False cleanly when adapter is unconfigured."""
        unconf_adapter = TelegramAdapter(token="", allowed_chat_id="")
        res = unconf_adapter.send_ci_notification(status="success")
        self.assertFalse(res.get("ok", True))

    def test_format_timestamp_default_vn_timezone(self):
        """Timestamp formatter converts UTC to GMT+7 Vietnam timezone by default."""
        dt_utc = datetime(2026, 11, 23, 0, 39, 14, tzinfo=timezone.utc)
        formatted = format_timestamp(dt_utc)
        self.assertEqual(formatted, "2026-11-23 07:39:14 (GMT+7)")

    def test_format_timestamp_custom_environment(self):
        """Custom SYNAPSE_TZ_OFFSET and SYNAPSE_TZ_NAME are respected."""
        dt_utc = datetime(2026, 11, 23, 0, 39, 14, tzinfo=timezone.utc)

        # Test offset 0 (UTC)
        orig_offset = os.environ.get("SYNAPSE_TZ_OFFSET")
        orig_name = os.environ.get("SYNAPSE_TZ_NAME")
        try:
            os.environ["SYNAPSE_TZ_OFFSET"] = "0"
            os.environ.pop("SYNAPSE_TZ_NAME", None)
            formatted_utc = format_timestamp(dt_utc)
            self.assertEqual(formatted_utc, "2026-11-23 00:39:14 (UTC)")

            # Test offset 9 with custom name
            os.environ["SYNAPSE_TZ_OFFSET"] = "9"
            os.environ["SYNAPSE_TZ_NAME"] = "JST"
            formatted_jst = format_timestamp(dt_utc)
            self.assertEqual(formatted_jst, "2026-11-23 09:39:14 (JST)")
        finally:
            if orig_offset is not None:
                os.environ["SYNAPSE_TZ_OFFSET"] = orig_offset
            else:
                os.environ.pop("SYNAPSE_TZ_OFFSET", None)
            if orig_name is not None:
                os.environ["SYNAPSE_TZ_NAME"] = orig_name
            else:
                os.environ.pop("SYNAPSE_TZ_NAME", None)

    def test_build_ci_message_contains_gmt7_and_structure(self):
        """CI/CD message contains GMT+7 timestamp, DoD badge, and commit info."""
        msg = self.adapter.build_ci_message(status="success")
        self.assertIn("GITHUB ACTIONS CI/CD BÁO CÁO", msg)
        self.assertIn("10/10 QUALITY GATES PASSED", msg)
        self.assertIn("(GMT+7)", msg)

        fail_msg = self.adapter.build_ci_message(status="failure")
        self.assertIn("GATES FAILED", fail_msg)
        self.assertIn("(GMT+7)", fail_msg)

    def test_status_command_contains_gmt7(self):
        """The /status command formats time in GMT+7."""
        status_reply = self.adapter.handle_command("/status", sender_id="999888777")
        self.assertIn("(GMT+7)", status_reply)

    def test_ci_command_routing(self):
        """The /ci command routes to build_ci_message."""
        ci_reply = self.adapter.handle_command("/ci", sender_id="999888777")
        self.assertIn("GITHUB ACTIONS CI/CD BÁO CÁO", ci_reply)
        self.assertIn("(GMT+7)", ci_reply)


if __name__ == "__main__":
    unittest.main()
