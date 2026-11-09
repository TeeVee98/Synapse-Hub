#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tests/test_bump_version.py — Unit Tests for Atomic Universal Version Bumper
"""

import os
import sys
import unittest
import tempfile
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

import bump_version


class TestBumpVersion(unittest.TestCase):
    """Tests semantic versioning and atomic rollback in bump_version."""

    def test_parse_semver_valid(self):
        self.assertEqual(bump_version.parse_semver("1.2.3"), (1, 2, 3, ""))
        self.assertEqual(bump_version.parse_semver("3.4.0-rc1"), (3, 4, 0, "-rc1"))

    def test_parse_semver_invalid(self):
        with self.assertRaises(ValueError):
            bump_version.parse_semver("invalid-version")
        with self.assertRaises(ValueError):
            bump_version.parse_semver("1.2")

    def test_calculate_next_version(self):
        self.assertEqual(bump_version.calculate_next_version("3.4.0", "patch"), "3.4.1")
        self.assertEqual(bump_version.calculate_next_version("3.4.0", "minor"), "3.5.0")
        self.assertEqual(bump_version.calculate_next_version("3.4.0", "major"), "4.0.0")
        self.assertEqual(bump_version.calculate_next_version("3.4.0", "3.4.5"), "3.4.5")

    def test_rollback_mechanism(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("ORIGINAL_CONTENT")

            # Setup snapshot
            bump_version.ORIGINAL_SNAPSHOTS[test_file] = "ORIGINAL_CONTENT"

            # Mutate file
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("MUTATED_CONTENT")
            self.assertEqual(open(test_file, "r", encoding="utf-8").read(), "MUTATED_CONTENT")

            # Rollback
            bump_version.rollback_all_files()
            self.assertEqual(open(test_file, "r", encoding="utf-8").read(), "ORIGINAL_CONTENT")

            # Clean snapshot dict
            bump_version.ORIGINAL_SNAPSHOTS.clear()

    @patch("subprocess.run")
    def test_run_tests_success(self, mock_run):
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_run.return_value = mock_res
        self.assertTrue(bump_version.run_tests())

    @patch("subprocess.run")
    def test_run_tests_failure(self, mock_run):
        mock_res = MagicMock()
        mock_res.returncode = 1
        mock_run.return_value = mock_res
        self.assertFalse(bump_version.run_tests())

    @patch("subprocess.run")
    def test_git_commit_and_tag_tag_exists_reuses_cleanly(self, mock_run):
        # 1. git status (clean)
        res_status = MagicMock(returncode=0, stdout="")
        # 2. git add -u
        res_add = MagicMock(returncode=0)
        # 3. git commit
        res_commit = MagicMock(returncode=0)
        # 4. git tag -l returning existing tag
        res_tag_l = MagicMock(returncode=0, stdout="v3.5.0\n")

        mock_run.side_effect = [res_status, res_add, res_commit, res_tag_l]

        bump_version.git_commit_and_tag("3.5.0", push=False)
        # Verify git tag creation was NOT called (4 calls total)
        self.assertEqual(mock_run.call_count, 4)


if __name__ == "__main__":
    unittest.main()
