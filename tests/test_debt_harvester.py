#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

import os
import sys
import tempfile
import unittest

# Ensure tools directory is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "tools")
sys.path.insert(0, TOOLS_DIR)

from debt_harvester import scan_directory, ShortcutEntry, format_markdown


class TestDebtHarvester(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.test_dir.cleanup()

    def test_shortcut_parsing_with_trigger(self):
        entry = ShortcutEntry("app.py", 10, "max 50 users in memory, upgrade: switch to Redis when user count > 50")
        self.assertTrue(entry.has_trigger)
        self.assertEqual(entry.file_path, "app.py")
        self.assertEqual(entry.line_no, 10)
        self.assertIn("switch to Redis", entry.upgrade_trigger)

    def test_shortcut_parsing_without_trigger(self):
        entry = ShortcutEntry("calc.py", 42, "hardcoded tax rate 10%")
        self.assertFalse(entry.has_trigger)
        self.assertEqual(entry.description, "hardcoded tax rate 10%")

    def test_scan_multiple_languages(self):
        root = self.test_dir.name
        # Python
        with open(os.path.join(root, "service.py"), "w", encoding="utf-8") as f:
            f.write("# shortcut: simple dict cache, ceiling: 100 items, upgrade: migrate to Redis when OOM\n")
            f.write("def run(): pass\n")

        # JavaScript
        with open(os.path.join(root, "client.js"), "w", encoding="utf-8") as f:
            f.write("// shortcut: skip token refresh, when: auth fails 401\n")
            f.write("const a = 1;\n")

        # SQL
        with open(os.path.join(root, "query.sql"), "w", encoding="utf-8") as f:
            f.write("-- shortcut: unindexed scan, ceiling: 500 rows, upgrade: add index on created_at\n")

        entries = scan_directory(root)
        self.assertEqual(len(entries), 3)
        self.assertTrue(all(e.has_trigger for e in entries))

    def test_format_markdown_clean_ledger(self):
        md = format_markdown([], self.test_dir.name)
        self.assertIn("Clean ledger", md)
        self.assertIn("**Total Shortcuts:** `0`", md)


if __name__ == "__main__":
    unittest.main()
