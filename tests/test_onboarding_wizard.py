# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Unit Test Suite for Synapse Hub Onboarding Wizard (tools.core.onboarding_wizard)
--------------------------------------------------------------------------------
Validates role-based configuration synthesis, environment diagnostics, and JSON output.
"""

import os
import sys
import json
import unittest
from unittest.mock import patch
import io

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.core import onboarding_wizard


class TestOnboardingWizard(unittest.TestCase):
    def test_probe_environment_keys(self):
        env_info = onboarding_wizard.probe_environment()
        self.assertIn("python", env_info)
        self.assertIn("node", env_info)
        self.assertIn("git", env_info)
        self.assertIn("chrome_installed", env_info)
        self.assertIn("playwright_ready", env_info)
        self.assertIsInstance(env_info["python"], str)

    def test_run_onboarding_all_roles_json(self):
        for role in ["manual", "starter", "sdet", "architect"]:
            captured = io.StringIO()
            with patch("sys.stdout", captured):
                ret = onboarding_wizard.run_onboarding(role_key=role, as_json=True, interactive=False)
            self.assertEqual(ret, 0)
            data = json.loads(captured.getvalue())
            self.assertEqual(data["role"], role)
            self.assertIn("title", data)
            self.assertIn("description", data)
            self.assertIn("skills", data)
            self.assertIn("environment", data)
            self.assertGreaterEqual(len(data["recommendations"]), 1)

    def test_run_onboarding_fallback_invalid_role(self):
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            ret = onboarding_wizard.run_onboarding(role_key="non_existent_role", as_json=True, interactive=False)
        self.assertEqual(ret, 0)
        data = json.loads(captured.getvalue())
        self.assertEqual(data["role"], "starter")

    def test_run_onboarding_human_readable_vietnamese(self):
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            ret = onboarding_wizard.run_onboarding(role_key="sdet", lang="vi", as_json=False, interactive=False)
        self.assertEqual(ret, 0)
        out = captured.getvalue()
        self.assertIn("CHÀO MỪNG BẠN ĐẾN VỚI SYNAPSE HUB", out)
        self.assertIn("SDET", out)
        self.assertIn("BƯỚC BẮT ĐẦU NHANH NHẤT", out)

    def test_run_onboarding_human_readable_english(self):
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            ret = onboarding_wizard.run_onboarding(role_key="manual", lang="en", as_json=False, interactive=False)
        self.assertEqual(ret, 0)
        out = captured.getvalue()
        self.assertIn("CHÀO MỪNG BẠN ĐẾN VỚI SYNAPSE HUB", out)
        self.assertIn("MANUAL", out)


if __name__ == "__main__":
    unittest.main()
