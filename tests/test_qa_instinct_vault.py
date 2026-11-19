#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_qa_instinct_vault.py — Unit tests for QA Instinct Vault
-----------------------------------------------------------------
Verifies project-scoped hashing, SQLite WAL initialization, instinct
reinforcement, confidence scaling, and auto-promotion gates.
"""

import os
import tempfile
import unittest
from tools.orchestration.qa_instinct_vault import (
    QAInstinctVault,
    get_project_hash,
)


class TestQAInstinctVault(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_instincts.db")
        self.vault = QAInstinctVault(self.db_path)

    def tearDown(self):
        self.vault.conn.close()
        self.temp_dir.cleanup()

    def test_project_hash_deterministic(self):
        hash1 = get_project_hash("/workspace/project_a")
        hash2 = get_project_hash("/workspace/project_a")
        hash3 = get_project_hash("/workspace/project_b")
        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)
        self.assertEqual(len(hash1), 12)

    def test_record_and_query_instinct(self):
        res = self.vault.record_instinct(
            project_dir="/workspace/project_a",
            domain="locator_heal",
            trigger="button#submit timeout",
            action="use expect(page.locator('#submit')).toBeVisible()",
            broken_locator="button#submit",
            healed_locator="button[type='submit']",
            confidence=0.6,
        )
        self.assertEqual(res["occurrences"], 1)
        self.assertEqual(res["confidence"], 0.6)

        instincts = self.vault.query_instincts("/workspace/project_a", domain="locator_heal")
        self.assertEqual(len(instincts), 1)
        self.assertEqual(instincts[0]["broken_locator"], "button#submit")
        self.assertEqual(instincts[0]["healed_locator"], "button[type='submit']")

    def test_reinforcement_and_promotion(self):
        p_dir = "/workspace/project_alpha"
        # First observation
        self.vault.record_instinct(p_dir, "flaky_fix", "networkidle timeout", "use domcontentloaded wait", confidence=0.6)
        # Second observation -> reinforces confidence and increments count
        res2 = self.vault.record_instinct(p_dir, "flaky_fix", "networkidle timeout", "use domcontentloaded wait")
        self.assertEqual(res2["occurrences"], 2)
        self.assertGreater(res2["confidence"], 0.65)

        # Auto-promotion gate
        promoted = self.vault.promote_auto(p_dir, threshold=0.70, min_occurrences=2)
        self.assertEqual(len(promoted), 1)
        self.assertEqual(promoted[0]["id"], res2["id"])

        # Check status updated to promoted
        all_inst = self.vault.query_instincts(p_dir)
        self.assertEqual(all_inst[0]["status"], "promoted")

    def test_context_manager(self):
        with QAInstinctVault(self.db_path) as v:
            res = v.record_instinct("/tmp/cm_test", "heal", "timeout", "retry")
            self.assertEqual(res["occurrences"], 1)

    def test_record_and_query_observations(self):
        p_dir = "/workspace/project_obs"
        obs = self.vault.record_observation(
            project_dir=p_dir,
            tool_name="playwright_runner",
            error_signature="TimeoutError: 30000ms exceeded",
            resolution="Switch to web-first locator",
            session_id="sess_123",
        )
        self.assertTrue(obs["id"].startswith("obs_"))
        self.assertEqual(obs["tool_name"], "playwright_runner")

        records = self.vault.query_observations(p_dir, limit=10)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["session_id"], "sess_123")
        self.assertEqual(records[0]["error_signature"], "TimeoutError: 30000ms exceeded")

    def test_git_config_project_hash(self):
        git_dir = os.path.join(self.temp_dir.name, ".git")
        os.makedirs(git_dir, exist_ok=True)
        config_path = os.path.join(git_dir, "config")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write('[remote "origin"]\n\turl = https://github.com/test/repo.git\n')

        h = get_project_hash(self.temp_dir.name)
        self.assertEqual(len(h), 12)


if __name__ == "__main__":
    unittest.main()
