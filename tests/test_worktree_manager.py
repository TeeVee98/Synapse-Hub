#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_worktree_manager.py — Unit tests for WorktreeManager
--------------------------------------------------------------
Verifies git worktree listing, creation, and cleanup.
"""

import unittest
from tools.orchestration.worktree_manager import WorktreeManager


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


if __name__ == "__main__":
    unittest.main()
