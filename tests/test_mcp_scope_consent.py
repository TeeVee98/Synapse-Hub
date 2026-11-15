#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_mcp_scope_consent.py — Regression tests for MCP State Modification,
Sandbox Safety, and Pentest Scope Guard / Consent enforcement.
"""

import os
import sys
import json
import sqlite3
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools")))
import mcp_server


class TestMCPScopeAndConsent(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_project_root = os.environ.get("SYNAPSE_PROJECT_ROOT")
        os.environ["SYNAPSE_PROJECT_ROOT"] = self.temp_dir.name

        self.db_path = os.path.join(self.temp_dir.name, "sandbox_test.db")
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        cur.execute("INSERT INTO users (name) VALUES ('AUTO_user_1')")
        conn.commit()
        conn.close()

    def tearDown(self):
        if self.old_project_root is not None:
            os.environ["SYNAPSE_PROJECT_ROOT"] = self.old_project_root
        else:
            os.environ.pop("SYNAPSE_PROJECT_ROOT", None)
        self.temp_dir.cleanup()

    # ------------------------------------------------------------------
    # 1. MCP Tools Schema Declarations
    # ------------------------------------------------------------------

    def test_manage_db_sandbox_schema_has_consent_and_dry_run_default(self):
        tool = next((t for t in mcp_server.MCP_TOOLS if t["name"] == "manage_db_sandbox"), None)
        self.assertIsNotNone(tool)
        props = tool["inputSchema"]["properties"]
        self.assertIn("consent", props)
        self.assertTrue(props["dry_run"]["default"])

    def test_fuzz_api_schema_has_consent_and_safe_defaults(self):
        tool = next((t for t in mcp_server.MCP_TOOLS if t["name"] == "fuzz_api"), None)
        self.assertIsNotNone(tool)
        props = tool["inputSchema"]["properties"]
        self.assertIn("consent", props)
        self.assertEqual(props["mode"]["default"], "passive")
        self.assertTrue(props["dry_run"]["default"])

    # ------------------------------------------------------------------
    # 2. manage_db_sandbox State Modification Safety
    # ------------------------------------------------------------------

    def test_db_sandbox_restore_defaults_to_dry_run_preview(self):
        # Create snapshot first
        snap_res = mcp_server.process_message({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "manage_db_sandbox", "arguments": {
                "action": "snapshot", "db_path": self.db_path, "snapshot_id": "snap1"
            }}
        })
        self.assertFalse(snap_res["result"].get("isError", False))

        # Restore without dry_run argument -> defaults to dry_run=True (preview only)
        restore_res = mcp_server.process_message({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "manage_db_sandbox", "arguments": {
                "action": "restore", "db_path": self.db_path, "snapshot_id": "snap1"
            }}
        })
        content = json.loads(restore_res["result"]["content"][0]["text"])
        self.assertEqual(content["status"], "dry_run_preview")
        self.assertTrue(content["dry_run"])
        self.assertIn("DRY-RUN PREVIEW", content["impact_summary"])

    def test_db_sandbox_restore_active_requires_consent(self):
        # Restore with dry_run=False but consent omitted -> raises PermissionError
        restore_res = mcp_server.process_message({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "manage_db_sandbox", "arguments": {
                "action": "restore", "db_path": self.db_path, "snapshot_id": "snap1", "dry_run": False
            }}
        })
        self.assertTrue(restore_res["result"].get("isError", False))
        error_text = restore_res["result"]["content"][0]["text"]
        self.assertIn("requires explicit consent", error_text)

    def test_db_sandbox_restore_active_with_consent_executes(self):
        # Take snapshot
        mcp_server.process_message({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "manage_db_sandbox", "arguments": {
                "action": "snapshot", "db_path": self.db_path, "snapshot_id": "snap2"
            }}
        })
        # Active restore with consent=True
        restore_res = mcp_server.process_message({
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {"name": "manage_db_sandbox", "arguments": {
                "action": "restore", "db_path": self.db_path, "snapshot_id": "snap2",
                "dry_run": False, "consent": True
            }}
        })
        self.assertFalse(restore_res["result"].get("isError", False))
        content = json.loads(restore_res["result"]["content"][0]["text"])
        self.assertEqual(content.get("status"), "RESTORED")
        self.assertTrue(content.get("zero_pollution_guaranteed", False))

    def test_db_sandbox_audit_and_purge_defaults_to_dry_run(self):
        purge_res = mcp_server.process_message({
            "jsonrpc": "2.0", "id": 6, "method": "tools/call",
            "params": {"name": "manage_db_sandbox", "arguments": {
                "action": "audit_and_purge", "db_path": self.db_path
            }}
        })
        self.assertFalse(purge_res["result"].get("isError", False))
        content = json.loads(purge_res["result"]["content"][0]["text"])
        self.assertTrue(content["dry_run"])

    def test_db_sandbox_audit_and_purge_active_requires_consent(self):
        purge_res = mcp_server.process_message({
            "jsonrpc": "2.0", "id": 7, "method": "tools/call",
            "params": {"name": "manage_db_sandbox", "arguments": {
                "action": "audit_and_purge", "db_path": self.db_path, "dry_run": False
            }}
        })
        self.assertTrue(purge_res["result"].get("isError", False))
        error_text = purge_res["result"]["content"][0]["text"]
        self.assertIn("requires explicit consent", error_text)

    def test_db_sandbox_rejects_path_traversal(self):
        bad_res = mcp_server.process_message({
            "jsonrpc": "2.0", "id": 8, "method": "tools/call",
            "params": {"name": "manage_db_sandbox", "arguments": {
                "action": "restore", "db_path": "/etc/passwd"
            }}
        })
        self.assertTrue(bad_res["result"].get("isError", False))
        self.assertIn("Access denied", bad_res["result"]["content"][0]["text"])

    # ------------------------------------------------------------------
    # 3. fuzz_api Scope Guard & Consent Enforcement
    # ------------------------------------------------------------------

    def test_fuzz_api_blocks_unauthorized_host(self):
        call = mcp_server.process_message({
            "jsonrpc": "2.0", "id": 9, "method": "tools/call",
            "params": {"name": "fuzz_api", "arguments": {
                "base_url": "https://attacker.com"
            }}
        })
        self.assertTrue(call["result"].get("isError", False))
        error_text = call["result"]["content"][0]["text"]
        self.assertIn("PENTEST SCOPE GUARD - REJECTED", error_text)

    def test_fuzz_api_blocks_disallowed_subdomain_heuristic(self):
        # Public domain with test/dev subdomain must NOT pass
        call = mcp_server.process_message({
            "jsonrpc": "2.0", "id": 10, "method": "tools/call",
            "params": {"name": "fuzz_api", "arguments": {
                "base_url": "https://test.unauthorized-domain.com"
            }}
        })
        self.assertTrue(call["result"].get("isError", False))
        error_text = call["result"]["content"][0]["text"]
        self.assertIn("PENTEST SCOPE GUARD - REJECTED", error_text)

    def test_fuzz_api_blocks_cloud_metadata_spec_url(self):
        call = mcp_server.process_message({
            "jsonrpc": "2.0", "id": 11, "method": "tools/call",
            "params": {"name": "fuzz_api", "arguments": {
                "base_url": "http://localhost:8080",
                "spec_path": "http://169.254.169.254/latest/meta-data"
            }}
        })
        self.assertTrue(call["result"].get("isError", False))
        error_text = call["result"]["content"][0]["text"]
        self.assertIn("PENTEST SCOPE GUARD - REJECTED", error_text)

    def test_fuzz_api_active_without_consent_fails(self):
        call = mcp_server.process_message({
            "jsonrpc": "2.0", "id": 12, "method": "tools/call",
            "params": {"name": "fuzz_api", "arguments": {
                "base_url": "http://localhost:8080",
                "mode": "active",
                "dry_run": False
            }}
        })
        self.assertTrue(call["result"].get("isError", False))
        error_text = call["result"]["content"][0]["text"]
        self.assertIn("requires explicit consent", error_text)

    def test_fuzz_api_passive_mode_succeeds_without_traffic(self):
        call = mcp_server.process_message({
            "jsonrpc": "2.0", "id": 13, "method": "tools/call",
            "params": {"name": "fuzz_api", "arguments": {
                "base_url": "http://localhost:8080",
                "mode": "passive"
            }}
        })
        self.assertFalse(call["result"].get("isError", False))
        data = json.loads(call["result"]["content"][0]["text"])
        self.assertEqual(data["mode"], "PASSIVE")
        self.assertIn("total_findings", data)

    def test_fuzz_api_active_dry_run_succeeds(self):
        call = mcp_server.process_message({
            "jsonrpc": "2.0", "id": 14, "method": "tools/call",
            "params": {"name": "fuzz_api", "arguments": {
                "base_url": "http://localhost:8080",
                "mode": "active",
                "dry_run": True
            }}
        })
        self.assertFalse(call["result"].get("isError", False))
        data = json.loads(call["result"]["content"][0]["text"])
        self.assertEqual(data["mode"], "ACTIVE")
        self.assertTrue(data["dry_run"])


if __name__ == "__main__":
    unittest.main()
