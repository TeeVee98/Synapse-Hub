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

from telegram_bot import TelegramAdapter, send_telegram_notification


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


if __name__ == "__main__":
    unittest.main()
