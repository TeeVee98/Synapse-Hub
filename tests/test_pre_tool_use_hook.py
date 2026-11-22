#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

import json
import os
import subprocess
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HOOK_SCRIPT = os.path.join(REPO_ROOT, "ai-agents", "hooks", "pre_tool_use.py")


class TestPreToolUseHook(unittest.TestCase):
    """Verifies that the PreToolUse hook executes and enforces security policies fail-closed."""

    def setUp(self):
        self.assertTrue(os.path.isfile(HOOK_SCRIPT), f"{HOOK_SCRIPT} must exist")

    def test_benign_command_allowed(self):
        res = subprocess.run(
            [sys.executable, HOOK_SCRIPT, "pytest tests/ -q"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10.0,
            cwd=REPO_ROOT,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["hookEventName"], "PreToolUse")
        self.assertEqual(data["permissionDecision"], "allow")
        self.assertEqual(data["command"], "pytest tests/ -q")

    def test_destructive_test_deletion_blocked(self):
        res = subprocess.run(
            [sys.executable, HOOK_SCRIPT, "rm -rf tests/"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10.0,
            cwd=REPO_ROOT,
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertEqual(data["hookEventName"], "PreToolUse")
        self.assertEqual(data["permissionDecision"], "deny")
        self.assertIn("HUMAN_CONFIRMATION_REQUIRED", data["permissionDecisionReason"])

    def test_stdin_json_interception_denied(self):
        stdin_payload = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "npm install malicious-pkg"},
        })
        res = subprocess.run(
            [sys.executable, HOOK_SCRIPT],
            input=stdin_payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10.0,
            cwd=REPO_ROOT,
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertEqual(data["permissionDecision"], "deny")
        self.assertIn("Rule 9 (Ask First)", data["permissionDecisionReason"])

    def test_empty_tool_input_allowed_as_benign(self):
        res = subprocess.run(
            [sys.executable, HOOK_SCRIPT],
            input="",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10.0,
            cwd=REPO_ROOT,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["permissionDecision"], "allow")


if __name__ == "__main__":
    unittest.main()
