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


if __name__ == "__main__":
    unittest.main()
