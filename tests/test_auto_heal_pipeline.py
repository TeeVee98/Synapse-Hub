#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_auto_heal_pipeline.py — Unit tests for Closed-Loop Auto-Healing Pipeline
----------------------------------------------------------------------------------
Verifies that heal_and_record_instinct:
  1. Validates proposed fix via Fact-Forcing Gate.
  2. Records and reinforces healed locators in QAInstinctVault.
  3. Triggers promotion upon repeated verified success.
"""

import os
import tempfile
import unittest
from tools.orchestration.auto_heal_pipeline import heal_and_record_instinct


class TestAutoHealPipeline(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_pipeline.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_heal_and_record_instinct(self):
        res1 = heal_and_record_instinct(
            project_dir="/workspace/sample_app",
            target_page_path="pages/login_page.py",
            broken_locator="button#submit",
            healed_locator="button[type='submit']",
            vault_db_path=self.db_path,
        )
        self.assertEqual(res1["status"], "HEALED_AND_LEARNED")
        self.assertEqual(res1["occurrences"], 1)

        # Second heal of the same locator triggers confidence reinforcement and promotion
        res2 = heal_and_record_instinct(
            project_dir="/workspace/sample_app",
            target_page_path="pages/login_page.py",
            broken_locator="button#submit",
            healed_locator="button[type='submit']",
            vault_db_path=self.db_path,
        )
        self.assertEqual(res2["status"], "HEALED_AND_LEARNED")
        self.assertEqual(res2["occurrences"], 2)
        self.assertGreater(res2["promoted_count"], 0)


if __name__ == "__main__":
    unittest.main()
