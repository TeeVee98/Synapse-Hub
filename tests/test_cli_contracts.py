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

    def test_npm_launcher_allowlist_parity_with_cli_parser(self):
        """P0-4: bin/agent-qa.js ALLOWLIST_SUBCOMMANDS must stay 1:1 synchronized with cli.py."""
        import re
        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)
        from tools.core import cli

        parser = cli.build_parser("en")
        cmds = cli.get_registered_commands(parser, "en")
        cli_names = {c["name"] for c in cmds}
        for c in cmds:
            cli_names.update(c.get("aliases", []))

        js_path = os.path.join(PROJECT_ROOT, "bin", "agent-qa.js")
        with open(js_path, "r", encoding="utf-8") as jf:
            js_text = jf.read()
        match = re.search(r"ALLOWLIST_SUBCOMMANDS\s*=\s*new Set\(\[(.*?)\]\);", js_text, re.S)
        self.assertIsNotNone(match, "ALLOWLIST_SUBCOMMANDS not found in bin/agent-qa.js")
        js_names = set(re.findall(r"'([^']+)'", match.group(1)))

        missing_in_js = sorted(cli_names - js_names)
        phantom_in_js = sorted(js_names - cli_names)
        self.assertEqual(missing_in_js, [], f"CLI commands missing in bin/agent-qa.js: {missing_in_js}")
        self.assertEqual(phantom_in_js, [], f"Dead commands in bin/agent-qa.js missing from cli.py: {phantom_in_js}")

    def test_cli_specs_registry_uses_canonical_module_paths(self):
        """P2-3: Every module path in tools/core/cli_specs.json must use canonical tools.<domain>.<mod>."""
        import importlib.util

        specs_path = os.path.join(PROJECT_ROOT, "tools", "core", "cli_specs.json")
        with open(specs_path, "r", encoding="utf-8") as sf:
            specs = json.load(sf)

        registry = specs.get("registry", {})
        self.assertGreaterEqual(len(registry), 100)
        non_canonical = [k for k, v in registry.items() if not str(v[0]).startswith("tools.")]
        self.assertEqual(non_canonical, [], f"Non-canonical registry module paths found: {non_canonical[:10]}")

        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)
        for cmd_key, target in registry.items():
            mod_name = target[0]
            spec = importlib.util.find_spec(mod_name)
            self.assertIsNotNone(spec, f"Canonical module '{mod_name}' for '{cmd_key}' cannot be resolved")


if __name__ == "__main__":
    unittest.main()
