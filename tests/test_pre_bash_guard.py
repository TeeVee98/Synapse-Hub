#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_pre_bash_guard.py — Unit Tests for Active Pre-Tool Shell Guard
"""

import os
import sys
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from pre_bash_guard import validate_shell_command, main


class TestPreBashGuard(unittest.TestCase):
    """Verifies security and scope invariants of pre_bash_guard."""

    def test_benign_commands_approved(self):
        """Verifies harmless development commands are allowed."""
        cmds = [
            "git status",
            "git diff",
            "python tools/verify_all.py --mode hub",
            "ruff check .",
            "pytest tests/test_tools.py -q",
        ]
        for c in cmds:
            ok, reason = validate_shell_command(c, cwd=REPO_ROOT)
            self.assertTrue(ok, f"Command should be approved: {c} ({reason})")

    def test_destructive_rm_rf_blocked(self):
        """Verifies destructive rm -rf commands are blocked."""
        bad_cmds = [
            "rm -rf /",
            "rm -rf ~",
            "rm -rf *",
            "rm -fr /",
            "Remove-Item -Recurse -Force C:\\",
            "rmdir /s /q C:\\",
        ]
        for c in bad_cmds:
            ok, reason = validate_shell_command(c)
            self.assertFalse(ok, f"Destructive command must be blocked: {c}")
            self.assertIn("SECURITY_VIOLATION", reason)

    def test_force_push_protected_branches_blocked(self):
        """Verifies git force push to main/master/develop is blocked."""
        bad_pushes = [
            "git push -f origin main",
            "git push --force origin master",
            "git push -f origin develop",
            "git push --force-with-lease origin main",
        ]
        for c in bad_pushes:
            ok, reason = validate_shell_command(c)
            self.assertFalse(ok, f"Force push must be blocked: {c}")
            self.assertIn("SAFETY_VIOLATION", reason)

    def test_hub_scope_isolation_blocked(self):
        """Lesson Learned #7 & #8: Target test runners executed in Hub root must be blocked."""
        hub_bad_cmds = [
            "playwright test",
            "npx playwright test",
            "cypress run",
            "npx cypress open",
            "mvn test",
            "gradle test",
        ]
        for c in hub_bad_cmds:
            ok, reason = validate_shell_command(c, cwd=REPO_ROOT)
            self.assertFalse(ok, f"Target runner in Hub root must be blocked: {c}")
            self.assertIn("SCOPE_VIOLATION", reason)

        # Same command in external target project must be allowed
        target_dir = os.path.join(REPO_ROOT, "..", "external_target_project")
        ok_ext, _ = validate_shell_command("playwright test", cwd=target_dir)
        self.assertTrue(ok_ext, "Target runner in client project workspace should be allowed")

    def test_cli_execution_text_and_json(self):
        """Verifies CLI return codes and formats."""
        with patch.object(sys, "argv", ["pre_bash_guard.py", "git status"]):
            code = main()
            self.assertEqual(code, 0)

        with patch.object(sys, "argv", ["pre_bash_guard.py", "rm -rf /"]):
            code = main()
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
