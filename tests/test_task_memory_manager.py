#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
tests/test_task_memory_manager.py — Unit tests for Compaction-Resilient Working Memory Manager
"""

import io
import json
import os
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch

from tools.task_memory_manager import (
    DEFAULT_MEMORY_DIR,
    TaskMemoryManager,
    compute_file_sha256,
    compute_sha256,
    main,
)


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

    def test_update_task_plan(self):
        self.mgr.init_memory()
        new_plan = "# Updated Plan\n\nNew requirements."
        sha = self.mgr.update_task_plan(new_plan)
        self.assertEqual(sha, compute_sha256(new_plan))

        with open(self.mgr.plan_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, new_plan)

        valid, details = self.mgr.verify_integrity()
        self.assertTrue(valid)
        self.assertEqual(details["task_plan.md"]["actual_sha256"], sha)

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

    def test_compute_file_sha256_missing_file(self):
        self.assertIsNone(compute_file_sha256("/non/existent/file.md"))

    def test_markdown_table_and_progress_sanitization(self):
        self.mgr.init_memory()
        # Record finding with pipes, newlines, carriage returns across title, category, and details
        malicious_title = "Header | Pipe | Split \r\n Newline in Title"
        malicious_cat = "DEFECT | CRITICAL \r\n ATTACK"
        malicious_details = "First line\r\nSecond line | with pipe"

        self.mgr.record_finding(malicious_title, malicious_details, category=malicious_cat)

        with open(self.mgr.findings_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        table_rows = [line for line in lines if line.startswith("| `")]
        self.assertGreaterEqual(len(table_rows), 1)

        for row in table_rows:
            # Markdown table with 4 columns must have exactly 5 pipe delimiters (| col1 | col2 | col3 | col4 |)
            self.assertEqual(row.count("|"), 5, f"Corrupted table row: {row}")
            self.assertNotIn("\r", row, "Carriage return found in table row")
            self.assertTrue(row.endswith("|\n"), f"Row does not terminate with pipe newline: {row}")

        # Also test record_progress sanitization
        self.mgr.record_progress("Multi\r\nline step", status="PASS\r\n")
        with open(self.mgr.progress_path, "r", encoding="utf-8") as f:
            p_lines = f.readlines()

        matching = [l for l in p_lines if "Multi  line step" in l]
        self.assertEqual(len(matching), 1)
        self.assertNotIn("\r", matching[0])

    def test_atomic_checksum_writing(self):
        self.mgr.init_memory()
        checksums = {"task_plan.md": "abc123", "findings.md": "def456"}
        with patch("os.replace", wraps=os.replace) as mock_replace:
            self.mgr._write_checksums(checksums)
            self.assertTrue(mock_replace.called)
            src, dst = mock_replace.call_args[0]
            self.assertIn(".tmp", src)
            self.assertEqual(dst, self.mgr.checksums_path)
            self.assertEqual(self.mgr._read_checksums(), checksums)

    def test_concurrent_reads_during_writes(self):
        self.mgr.init_memory()
        errors = []

        def reader():
            for _ in range(30):
                c = self.mgr._read_checksums()
                if "task_plan.md" not in c:
                    errors.append("task_plan.md missing during concurrent read")

        def writer():
            for i in range(30):
                self.mgr._update_file_checksum("findings.md", f"content_iteration_{i}")

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=writer),
            threading.Thread(target=reader),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Detected concurrent read truncation: {errors}")

    def test_main_cli_operations(self):
        # 1. init
        with patch("sys.argv", ["task_memory_manager.py", "init", "--dir", self.test_dir, "--title", "CLI Plan"]):
            self.assertEqual(main(), 0)

        # 2. finding
        with patch("sys.argv", ["task_memory_manager.py", "finding", "CLI Finding", "Some details", "--dir", self.test_dir, "--cat", "BUG"]):
            self.assertEqual(main(), 0)

        # 3. progress
        with patch("sys.argv", ["task_memory_manager.py", "progress", "CLI Step", "--dir", self.test_dir, "--status", "PASS"]):
            self.assertEqual(main(), 0)

        # 4. verify valid
        with patch("sys.argv", ["task_memory_manager.py", "verify", "--dir", self.test_dir]), patch("sys.stdout", new=io.StringIO()) as out:
            self.assertEqual(main(), 0)
            self.assertIn("VALID", out.getvalue())

        # 5. verify invalid (tamper)
        with open(self.mgr.plan_path, "a", encoding="utf-8") as f:
            f.write("corrupted content")
        with patch("sys.argv", ["task_memory_manager.py", "verify", "--dir", self.test_dir]), patch("sys.stdout", new=io.StringIO()) as out:
            self.assertEqual(main(), 1)
            self.assertIn("COMPROMISED", out.getvalue())


if __name__ == "__main__":
    unittest.main()
