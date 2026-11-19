#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tests/test_mcp_unified_server.py — Unit Tests for Standardized Synapse MCP Server
---------------------------------------------------------------------------------
Validates that the standardized MCP Server entrypoint properly exposes the 5
core tools for AI coding assistants (Cursor, Claude Code, Windsurf, Antigravity)
and processes JSON-RPC 2.0 messages correctly.
"""

import json
import unittest
from tools.mcp.mcp_server import process_message, TOOL_DISPATCH_TABLE


class TestMCPUnifiedServer(unittest.TestCase):

    def test_mcp_initialize(self):
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }
        resp = process_message(req)
        self.assertIsNotNone(resp)
        self.assertEqual(resp["result"]["serverInfo"]["name"], "enterprise-agent-qa")
        self.assertEqual(resp["result"]["serverInfo"]["version"], "4.6.1")

    def test_mcp_tools_list_contains_core_five_tools(self):
        req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        resp = process_message(req)
        self.assertIsNotNone(resp)
        tools = resp["result"]["tools"]
        tool_names = {t["name"] for t in tools}

        expected_five = {
            "synapse_lint",
            "synapse_verify",
            "synapse_mutate",
            "synapse_distill_logs",
            "synapse_security_scan",
        }
        self.assertTrue(expected_five.issubset(tool_names), f"Missing tools from {expected_five - tool_names}")

    def test_mcp_dispatch_table_contains_all_tools(self):
        for tool in ("synapse_lint", "synapse_verify", "synapse_mutate", "synapse_distill_logs", "synapse_security_scan"):
            self.assertIn(tool, TOOL_DISPATCH_TABLE)

    def test_call_synapse_lint_tool(self):
        req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "synapse_lint",
                "arguments": {"target_path": "tools/lint/ast_engine.py"}
            }
        }
        resp = process_message(req)
        self.assertIsNotNone(resp)
        self.assertFalse(resp["result"]["isError"])
        content_text = resp["result"]["content"][0]["text"]
        data = json.loads(content_text)
        self.assertEqual(data["total_findings"], 0)

    def test_call_unknown_tool_returns_error(self):
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "non_existent_tool_xyz",
                "arguments": {}
            }
        }
        resp = process_message(req)
        self.assertIsNotNone(resp)
        self.assertTrue(resp["result"]["isError"])
        self.assertIn("Unknown MCP tool", resp["result"]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
