#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tests/test_hub_publisher.py — Unit Tests for Autonomous 1-Click Hub Publisher
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add repo root and tools to path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

import hub_publisher


class TestHubPublisher(unittest.TestCase):
    """Tests core capabilities of hub_publisher pipeline."""

    def test_get_current_version(self):
        version = hub_publisher.get_current_version()
        self.assertRegex(version, r"^\d+\.\d+\.\d+", "Version must follow semantic versioning")

    def test_get_remote_repo_info(self):
        owner, repo = hub_publisher.get_remote_repo_info()
        self.assertEqual(owner, "TeeVee998")
        self.assertEqual(repo, "Synapse-Hub")

    @patch("subprocess.run")
    def test_step_1_push_main_dry_run(self, mock_run):
        mock_res = MagicMock()
        mock_res.stdout = "main\n"
        mock_run.return_value = mock_res
        success = hub_publisher.step_1_push_main(dry_run=True)
        self.assertTrue(success)
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_step_2_create_and_push_tag_dry_run(self, mock_run):
        mock_res = MagicMock()
        mock_res.stdout = ""
        mock_run.return_value = mock_res
        success = hub_publisher.step_2_create_and_push_tag("9.9.9", dry_run=True)
        self.assertTrue(success)

    def test_generate_release_notes(self):
        notes = hub_publisher.generate_release_notes("3.1.2")
        self.assertIn("## Release v3.1.2", notes)
        self.assertIn("Universal Synchronization", notes)

    @patch("hub_publisher.run_preflight_verification", return_value=True)
    @patch("hub_publisher.stage_and_commit_changes", return_value=True)
    @patch("hub_publisher.step_1_push_main", return_value=True)
    @patch("hub_publisher.step_2_create_and_push_tag", return_value=True)
    @patch("hub_publisher.step_3_create_github_release", return_value="https://github.com/TeeVee998/Synapse-Hub/releases/tag/v3.1.2")
    @patch("hub_publisher.step_4_and_5_monitor_packages_and_npm")
    def test_main_fails_when_npm_unverified_without_no_wait(self, mock_monitor, *mocks):
        """Validates that main() returns non-zero code (1) when NPM publication is not verified."""
        mock_monitor.return_value = False
        with patch.object(sys, "argv", ["hub_publisher.py"]):
            exit_code = hub_publisher.main()
            self.assertEqual(exit_code, 1, "Must fail with exit code 1 when NPM verification returns False")

    @patch("hub_publisher.run_preflight_verification", return_value=True)
    @patch("hub_publisher.stage_and_commit_changes", return_value=True)
    @patch("hub_publisher.step_1_push_main", return_value=True)
    @patch("hub_publisher.step_2_create_and_push_tag", return_value=True)
    @patch("hub_publisher.step_3_create_github_release", return_value="https://github.com/TeeVee998/Synapse-Hub/releases/tag/v3.1.2")
    @patch("hub_publisher.step_4_and_5_monitor_packages_and_npm")
    def test_main_succeeds_when_npm_verified(self, mock_monitor, *mocks):
        """Validates that main() returns 0 when NPM publication is verified."""
        mock_monitor.return_value = True
        with patch.object(sys, "argv", ["hub_publisher.py"]):
            exit_code = hub_publisher.main()
            self.assertEqual(exit_code, 0, "Must succeed with exit code 0 when NPM verification returns True")

    @patch("hub_publisher.run_preflight_verification", return_value=True)
    @patch("hub_publisher.stage_and_commit_changes", return_value=True)
    @patch("hub_publisher.step_1_push_main", return_value=True)
    @patch("hub_publisher.step_2_create_and_push_tag", return_value=True)
    @patch("hub_publisher.step_3_create_github_release", return_value="https://github.com/TeeVee998/Synapse-Hub/releases/tag/v3.1.2")
    def test_main_succeeds_with_no_wait(self, *mocks):
        """Validates that main() returns 0 when --no-wait is passed."""
        with patch.object(sys, "argv", ["hub_publisher.py", "--no-wait"]):
            exit_code = hub_publisher.main()
            self.assertEqual(exit_code, 0, "Must succeed with exit code 0 when --no-wait is passed")


if __name__ == "__main__":
    unittest.main()
