#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Golden Unit Tests for tools/sync_agent_rules.py (AI Bridge Rule Synchronizer)
----------------------------------------------------------------------------
Validates:
  1. Bridge generators for Claude, Cursor, Windsurf, Copilot
  2. Mandatory Author Attribution & MIT License guard preservation
  3. Single source of truth invariants (Clean POM, Zero Hard Sleeps, Truth Anchor)
  4. Non-drift check mode (sync_all --check)
  5. Completeness of TARGET_GENERATORS registry (10 bridge paths)
  6. Template scope cleanliness: zero occurrences of tools/verify_all.py in templates/ai_bridges/*
  7. Conformance to 3-tier policy structure (ALWAYS, RECOMMENDED, SYNAPSE-HUB-ONLY)
"""

import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
CORE_DIR = os.path.join(TOOLS_DIR, "core")
for p in (REPO_ROOT, TOOLS_DIR, CORE_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    import tools.core.sync_agent_rules as sar
except ImportError:
    import sync_agent_rules as sar


class TestSyncAgentRules(unittest.TestCase):

    def test_target_generators_registry(self):
        """Verifies TARGET_GENERATORS contains all 10 canonical bridge paths."""
        self.assertEqual(len(sar.TARGET_GENERATORS), 10)
        paths = [rel_path for rel_path, _ in sar.TARGET_GENERATORS]
        self.assertIn("CLAUDE.md", paths)
        self.assertIn(".cursorrules", paths)
        self.assertIn(".windsurfrules", paths)
        self.assertIn(".cursor/rules/synapse-qa.mdc", paths)
        self.assertIn(".github/copilot-instructions.md", paths)
        self.assertIn(".github/instructions/clean-pom.instructions.md", paths)
        self.assertIn("templates/ai_bridges/CLAUDE.md", paths)
        self.assertIn("templates/ai_bridges/cursor_synapse_qa.mdc", paths)
        self.assertIn("templates/ai_bridges/windsurfrules", paths)
        self.assertIn("templates/ai_bridges/copilot-instructions.md", paths)

    def test_generate_claude_md(self):
        content = sar.generate_claude_md(is_template=False)
        self.assertIn("Thế Vị (@TeeVee98)", content)
        self.assertIn("MIT License", content)
        self.assertIn("Clean Page Object Model (POM)", content)
        self.assertIn("Truth Anchor", content)
        self.assertIn("Dynamic Smart Waits Only", content)
        self.assertIn("ALWAYS", content)
        self.assertIn("RECOMMENDED", content)
        self.assertIn("SYNAPSE-HUB-ONLY", content)

    def test_generate_cursorrules(self):
        content = sar.generate_cursorrules()
        self.assertIn("Thế Vị (@TeeVee98)", content)
        self.assertIn("Clean POM Flat Architecture", content)
        self.assertIn("ALWAYS", content)
        self.assertIn("RECOMMENDED", content)

    def test_generate_windsurfrules(self):
        content = sar.generate_windsurfrules(is_template=False)
        self.assertIn("Thế Vị (@TeeVee98)", content)
        self.assertIn("Clean Page Object Model (POM)", content)
        self.assertIn("ALWAYS", content)
        self.assertIn("RECOMMENDED", content)

    def test_generate_cursor_mdc(self):
        content = sar.generate_cursor_mdc(is_template=False)
        self.assertTrue(content.startswith("---"))
        self.assertIn("Thế Vị (@TeeVee98)", content)
        self.assertIn("description:", content)
        self.assertIn("ALWAYS", content)
        self.assertIn("RECOMMENDED", content)

    def test_generate_copilot_instructions(self):
        content = sar.generate_copilot_instructions(is_template=False)
        self.assertIn("Thế Vị (@TeeVee98)", content)
        self.assertIn("GitHub Copilot", content)
        self.assertIn("ALWAYS", content)
        self.assertIn("RECOMMENDED", content)

    def test_generate_clean_pom_instructions(self):
        content = sar.generate_clean_pom_instructions()
        self.assertTrue(content.startswith("---"))
        self.assertIn("Clean Page Object Model (POM)", content)
        self.assertIn("ALWAYS", content)
        self.assertIn("RECOMMENDED", content)

    def test_template_bridges_cleanliness_contract(self):
        """Contract: templates/ai_bridges/* must NEVER reference tools/verify_all.py or SYNAPSE-HUB-ONLY."""
        template_paths = [
            os.path.join(REPO_ROOT, "templates", "ai_bridges", "CLAUDE.md"),
            os.path.join(REPO_ROOT, "templates", "ai_bridges", "cursor_synapse_qa.mdc"),
            os.path.join(REPO_ROOT, "templates", "ai_bridges", "windsurfrules"),
            os.path.join(REPO_ROOT, "templates", "ai_bridges", "copilot-instructions.md"),
        ]
        for t_path in template_paths:
            self.assertTrue(os.path.isfile(t_path), f"Template bridge file missing: {t_path}")
            with open(t_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn(
                "tools/core/verify_all.py",
                content,
                f"Template {t_path} leaked Hub-specific 'tools/core/verify_all.py' into target project scope!"
            )
            self.assertNotIn(
                "SYNAPSE-HUB-ONLY",
                content,
                f"Template {t_path} leaked SYNAPSE-HUB-ONLY section into target project scope!"
            )
            self.assertIn("MIT License", content, f"Template {t_path} missing mandatory MIT license attribution")

    def test_sync_all_check_clean(self):
        exit_code = sar.sync_all(check_only=True)
        self.assertEqual(exit_code, 0)

    def test_stack_specific_rules_protected(self):
        """Verifies PROTECTED_STACK_RULES exist on disk and are strictly excluded from TARGET_GENERATORS."""
        self.assertTrue(hasattr(sar, "PROTECTED_STACK_RULES"), "sar missing PROTECTED_STACK_RULES constant")
        self.assertGreaterEqual(len(sar.PROTECTED_STACK_RULES), 5)
        for rule_path in sar.PROTECTED_STACK_RULES:
            full_path = os.path.join(REPO_ROOT, rule_path)
            self.assertTrue(os.path.isfile(full_path), f"Protected stack rule missing on disk: {rule_path}")

        target_paths = [rel_path for rel_path, _ in sar.TARGET_GENERATORS]
        for rule_path in sar.PROTECTED_STACK_RULES:
            self.assertNotIn(rule_path, target_paths, f"Protected rule {rule_path} found in TARGET_GENERATORS!")


if __name__ == "__main__":
    unittest.main()
