#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tests/test_tool_catalog.py — Unit Tests for Enterprise Tooling Catalog Integrity
"""

import os
import sys
import json
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
sys.path.insert(0, TOOLS_DIR)

import generate_tool_catalog


class TestToolCatalog(unittest.TestCase):
    """Verifies that all tools are cataloged with owner, status, risk, and input/output contracts."""

    def test_catalog_builds_and_all_files_exist(self):
        catalog = generate_tool_catalog.build_catalog()
        self.assertGreaterEqual(catalog["total_tools"], 50)
        self.assertGreaterEqual(catalog["stable_count"], 15)

        for tool in catalog["tools"]:
            self.assertIn("file", tool)
            self.assertIn("command", tool)
            self.assertIn("category", tool)
            self.assertIn("owner_role", tool)
            self.assertIn("status", tool)
            self.assertIn("risk_level", tool)
            self.assertIn(tool["status"], ["stable", "experimental"])
            self.assertIn(tool["risk_level"], ["read_only", "modifying", "network", "destructive"])

            # Verify file exists on disk
            full_path = os.path.join(REPO_ROOT, tool["file"])
            self.assertTrue(os.path.isfile(full_path), f"Cataloged tool file not found: {tool['file']}")

    def test_tool_catalog_json_file_is_valid(self):
        json_path = os.path.join(TOOLS_DIR, "TOOL_CATALOG.json")
        self.assertTrue(os.path.isfile(json_path), "TOOL_CATALOG.json must exist")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("tools", data)
        self.assertGreaterEqual(len(data["tools"]), 50)

    def test_tool_catalog_md_file_is_valid(self):
        md_path = os.path.join(REPO_ROOT, "docs", "TOOL_CATALOG.md")
        self.assertTrue(os.path.isfile(md_path), "TOOL_CATALOG.md must exist")
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("# Synapse Hub — Tooling Ecosystem Catalog & Runbook", content)
        self.assertIn("verify_all.py", content)
        self.assertIn("fsm_enforcer.py", content)


if __name__ == "__main__":
    unittest.main()
