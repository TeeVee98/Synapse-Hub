#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tests/test_cli_contracts.py — Automated Contract Testing for Core CLI Tools
Validates that all tools registered in tools/tools_schema.json:
  1. Have valid existing executable Python script paths.
  2. Successfully respond to --help with exit code 0.
  3. Emit clean output with zero ModuleNotFoundError or unhandled tracebacks.
"""

import json
import os
import subprocess
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))


class TestCLIContracts(unittest.TestCase):
    """Test suite ensuring zero CLI breakage or missing module imports across core tools."""

    @classmethod
    def setUpClass(cls):
        schema_path = os.path.join(PROJECT_ROOT, "tools", "tools_schema.json")
        cls.assertTrue(os.path.isfile(schema_path), f"tools_schema.json missing at {schema_path}")
        with open(schema_path, "r", encoding="utf-8") as f:
            cls.schema = json.load(f)

    def test_tools_schema_structure(self):
        """Validates JSON schema structure and metadata."""
        self.assertIn("version", self.schema)
        self.assertIn("tools", self.schema)
        self.assertGreaterEqual(len(self.schema["tools"]), 10)

    def test_all_tools_exist_and_respond_to_help(self):
        """Verifies each registered tool responds to --help cleanly."""
        tools = self.schema["tools"]
        for tool_name, tool_info in tools.items():
            rel_path = tool_info.get("path")
            self.assertIsNotNone(rel_path, f"Tool {tool_name} missing 'path'")
            abs_path = os.path.join(PROJECT_ROOT, rel_path)
            self.assertTrue(os.path.isfile(abs_path), f"Tool {tool_name} script not found: {abs_path}")

            # Execute python <script> --help
            res = subprocess.run(
                [sys.executable, abs_path, "--help"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=15.0
            )

            self.assertEqual(
                res.returncode, 0,
                f"Tool '{tool_name}' failed --help with exit code {res.returncode}.\nStderr: {res.stderr}\nStdout: {res.stdout}"
            )
            combined = (res.stdout or "") + (res.stderr or "")
            self.assertNotIn(
                "ModuleNotFoundError", combined,
                f"Tool '{tool_name}' crashed with ModuleNotFoundError:\n{combined}"
            )
            self.assertNotIn(
                "Traceback (most recent call last):", combined,
                f"Tool '{tool_name}' crashed with unhandled exception:\n{combined}"
            )


if __name__ == "__main__":
    unittest.main()
