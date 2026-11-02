#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Golden Unit Tests for tools/sync_agent_rules.py (AI Bridge Rule Synchronizer)
----------------------------------------------------------------------------
Validates:
  1. Bridge generators for Claude, Cursor, Windsurf, Copilot
  2. Mandatory Author Attribution & MIT License guard preservation
  3. Single source of truth invariants (Clean POM, Zero Hard Sleeps, Truth Anchor)
  4. Non-drift check mode (sync_all --check)
  5. Completeness of TARGET_GENERATORS registry (8 bridge paths)
"""

import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import sync_agent_rules as sar


class TestSyncAgentRules(unittest.TestCase):

    def test_target_generators_registry(self):
        self.assertEqual(len(sar.TARGET_GENERATORS), 8)
        paths = [rel_path for rel_path, _ in sar.TARGET_GENERATORS]
        self.assertIn("CLAUDE.md", paths)
        self.assertIn(".cursorrules", paths)
        self.assertIn(".windsurfrules", paths)
        self.assertIn(".cursor/rules/synapse-qa.mdc", paths)
        self.assertIn("templates/ai_bridges/CLAUDE.md", paths)
        self.assertIn("templates/ai_bridges/copilot-instructions.md", paths)

    def test_generate_claude_md(self):
        content = sar.generate_claude_md()
        self.assertIn("Thế Vị (@TeeVee998)", content)
        self.assertIn("MIT License", content)
        self.assertIn("Clean Page Object Model (POM)", content)
        self.assertIn("Truth Anchor", content)
        self.assertIn("Smart Waits", content)

    def test_generate_cursorrules(self):
        content = sar.generate_cursorrules()
        self.assertIn("Thế Vị (@TeeVee998)", content)
        self.assertIn("Clean POM Flat Architecture", content)

    def test_generate_windsurfrules(self):
        content = sar.generate_windsurfrules()
        self.assertIn("Thế Vị (@TeeVee998)", content)
        self.assertIn("Clean Page Object Model (POM)", content)

    def test_generate_cursor_mdc(self):
        content = sar.generate_cursor_mdc()
        self.assertTrue(content.startswith("---"))
        self.assertIn("Thế Vị (@TeeVee998)", content)
        self.assertIn("description:", content)

    def test_generate_copilot_instructions(self):
        content = sar.generate_copilot_instructions()
        self.assertIn("Thế Vị (@TeeVee998)", content)
        self.assertIn("GitHub Copilot", content)

    def test_sync_all_check_clean(self):
        exit_code = sar.sync_all(check_only=True)
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
