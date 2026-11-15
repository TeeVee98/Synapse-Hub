#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
tests/test_task_memory_manager.py — Unit tests for Compaction-Resilient Working Memory Manager
"""

import os
import shutil
import tempfile
import unittest

from tools.task_memory_manager import TaskMemoryManager, compute_sha256


class TestTaskMemoryManager(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_memory_")
        self.mgr = TaskMemoryManager(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_init_memory_creates_files_and_checksums(self):
        checksums = self.mgr.init_memory(title="E2E Checkout Test Plan")
        self.assertTrue(os.path.isfile(self.mgr.plan_path))
        self.assertTrue(os.path.isfile(self.mgr.findings_path))
        self.assertTrue(os.path.isfile(self.mgr.progress_path))
        self.assertTrue(os.path.isfile(self.mgr.checksums_path))

        self.assertIn("task_plan.md", checksums)
        self.assertIn("findings.md", checksums)
        self.assertIn("progress.md", checksums)

        valid, details = self.mgr.verify_integrity()
        self.assertTrue(valid)
        self.assertTrue(details["task_plan.md"]["valid"])

    def test_record_finding_and_progress(self):
        self.mgr.init_memory()
        self.mgr.record_finding("Flaky Modal", "Modal failed to close after 500ms", category="DEFECT")
        self.mgr.record_progress("Investigated modal locator", status="PASS")

        with open(self.mgr.findings_path, "r", encoding="utf-8") as f:
            findings_text = f.read()
        self.assertIn("Flaky Modal", findings_text)
        self.assertIn("`DEFECT`", findings_text)

        with open(self.mgr.progress_path, "r", encoding="utf-8") as f:
            progress_text = f.read()
        self.assertIn("Investigated modal locator", progress_text)

        # Integrity should still be valid because records update checksums
        valid, _ = self.mgr.verify_integrity()
        self.assertTrue(valid)

    def test_tamper_detection(self):
        self.mgr.init_memory()
        valid, _ = self.mgr.verify_integrity()
        self.assertTrue(valid)

        # External tamper without updating checksums
        with open(self.mgr.plan_path, "a", encoding="utf-8") as f:
            f.write("\nTampered content outside memory manager\n")

        valid, details = self.mgr.verify_integrity()
        self.assertFalse(valid)
        self.assertFalse(details["task_plan.md"]["valid"])


if __name__ == "__main__":
    unittest.main()
