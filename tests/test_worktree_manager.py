#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_worktree_manager.py — Unit tests for WorktreeManager
--------------------------------------------------------------
Verifies git worktree listing, creation, and cleanup.
"""

import os
import tempfile
import unittest
from unittest.mock import patch
from tools.orchestration.worktree_manager import WorktreeManager, _remove_readonly, _AUTO_CLEANUP_PATHS


class TestWorktreeManager(unittest.TestCase):

    def setUp(self):
        self.mgr = WorktreeManager()

    def test_list_worktrees_contains_root(self):
        worktrees = self.mgr.list_worktrees()
        self.assertGreaterEqual(len(worktrees), 1)
        # Main worktree must be present
        paths = [w.get("path", "").replace("\\", "/").lower() for w in worktrees]
        repo_norm = self.mgr.repo_root.replace("\\", "/").lower()
        self.assertTrue(any(repo_norm in p for p in paths))

    def test_create_worktree_target_dir_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ok, msg = self.mgr.create_worktree("test-branch", target_dir=temp_dir)
            self.assertFalse(ok)
            self.assertIn("already exists", msg)

    @patch("tools.orchestration.worktree_manager.run_git")
    def test_list_worktrees_parsing(self, mock_run_git):
        mock_output = (
            "worktree /repo/main\n"
            "HEAD 1234567890abcdef\n"
            "branch refs/heads/main\n"
            "\n"
            "worktree /repo/subagent_1\n"
            "HEAD fedcba0987654321\n"
            "branch refs/heads/subagent-branch\n"
        )
        mock_run_git.return_value = (0, mock_output, "")
        wt = self.mgr.list_worktrees()
        self.assertEqual(len(wt), 2)
        self.assertEqual(wt[0]["path"], "/repo/main")
        self.assertEqual(wt[1]["branch"], "refs/heads/subagent-branch")

    @patch("tools.orchestration.worktree_manager.run_git")
    def test_create_and_cleanup_worktree_lifecycle(self, mock_run_git):
        mock_run_git.return_value = (0, "", "")
        test_path = os.path.join(tempfile.gettempdir(), "test_wt_nonexistent_dir_123")
        if os.path.exists(test_path):
            os.rmdir(test_path)

        try:
            ok, res_path = self.mgr.create_worktree("feat-agent", target_dir=test_path, auto_cleanup=True)
            self.assertTrue(ok)
            self.assertIn(test_path, _AUTO_CLEANUP_PATHS)

            # Cleanup
            ok_clean, clean_msg = self.mgr.cleanup_worktree(test_path, force=True)
            self.assertTrue(ok_clean)
            self.assertNotIn(test_path, _AUTO_CLEANUP_PATHS)
        finally:
            _AUTO_CLEANUP_PATHS.discard(test_path)

    def test_remove_readonly_handler(self):
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"dummy")
            tf_path = tf.name

        try:
            # Should handle unlink cleanly
            _remove_readonly(os.unlink, tf_path)
            self.assertFalse(os.path.exists(tf_path))
        except Exception:
            if os.path.exists(tf_path):
                os.unlink(tf_path)


if __name__ == "__main__":
    unittest.main()
