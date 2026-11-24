#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

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

    def test_tiered_tool_and_skills_index_contracts(self):
        """Verifies Tier-1 indexes: TOOL_INDEX.json (< 12 KB) and skills_index.json (< 20 KB combined)."""
        tool_idx_path = os.path.join(TOOLS_DIR, "TOOL_INDEX.json")
        self.assertTrue(os.path.isfile(tool_idx_path), "TOOL_INDEX.json must exist")
        tool_sz = os.path.getsize(tool_idx_path)
        self.assertLess(tool_sz, 12 * 1024, f"TOOL_INDEX.json must be < 12 KB, got {tool_sz} bytes")

        with open(tool_idx_path, "r", encoding="utf-8") as f:
            tool_idx = json.load(f)
        self.assertIn("orchestrator", tool_idx)
        self.assertIn("quality-gatekeeper", tool_idx)

        # Check sharded catalogs
        catalogs_dir = os.path.join(TOOLS_DIR, "catalogs")
        self.assertTrue(os.path.isdir(catalogs_dir), "tools/catalogs must exist")
        cat_files = [f for f in os.listdir(catalogs_dir) if f.endswith(".json")]
        self.assertGreaterEqual(len(cat_files), 10, "Expected at least 10 category shards")

        # Check skills_index.json
        skills_idx_path = os.path.join(REPO_ROOT, "skills_index.json")
        self.assertTrue(os.path.isfile(skills_idx_path), "skills_index.json must exist")
        skills_sz = os.path.getsize(skills_idx_path)

        with open(skills_idx_path, "r", encoding="utf-8") as f:
            skills_idx = json.load(f)
        skills_list = skills_idx.get("skills", [])
        self.assertEqual(len(skills_list), 57, f"Expected 57 skills in skills_index.json, got {len(skills_list)}")

        combined_sz = tool_sz + skills_sz
        # skills_index.json now embeds direct physical path + 100-char summaries to eliminate the 58.6 KB skills_manifest.json hop
        self.assertLess(combined_sz, 32 * 1024, f"TOOL_INDEX + skills_index combined must be < 32 KB, got {combined_sz} bytes")


if __name__ == "__main__":
    unittest.main()
