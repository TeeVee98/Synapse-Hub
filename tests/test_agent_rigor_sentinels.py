#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tests/test_agent_rigor_sentinels.py — Comprehensive Test Battery for 3 Rigor Sentinels
--------------------------------------------------------------------------------------
Validates:
  1. Invariant 16: English-Only Codebase & Rules Linter (Rule 2.4).
  2. Unregistered Tool Hard-Fail Gate in cli_schema_sentinel.py.
  3. Physical Scope Guard comparing git modifications against milestone write_set.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from tools.lint.invariant_checker import check_rule_16_english_codebase, evaluate_invariants
from tools.lint.cli_schema_sentinel import validate_schema_drift
from tools.design.dag_self_healer import DAGNode, check_scope_guard_violation, SelfHealingDAGExecutor


class TestAgentRigorSentinels(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # =========================================================================
    # 1. POSITIVE SCENARIOS
    # =========================================================================

    def test_positive_english_codebase_with_author_attribution(self):
        """Validates that English rule files with author Thế Vị (@TeeVee98) pass with zero violations."""
        agents_md = os.path.join(self.temp_dir, "AGENTS.md")
        with open(agents_md, "w", encoding="utf-8") as f:
            f.write("# AGENTS.md — Author: Thế Vị (@TeeVee98)\n## Rules\nAll code must be English.\n")

        violations = check_rule_16_english_codebase(self.temp_dir)
        self.assertEqual(len(violations), 0, f"Expected 0 violations but got: {violations}")

    def test_positive_registered_tool_schema_parity(self):
        """Validates that a correctly registered tool passes schema validation with 0 drift."""
        schema_path = os.path.join(self.temp_dir, "schema.json")
        tool_script = os.path.join(self.temp_dir, "my_tool.py")
        with open(tool_script, "w", encoding="utf-8") as f:
            f.write("""
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--target", required=True)
parser.add_argument("--json", action="store_true")
""")

        schema_data = {
            "tools": {
                "my_tool": {
                    "path": tool_script,
                    "command": f"python3 {tool_script}",
                    "args": {
                        "--target": {"type": "string", "required": True},
                        "--json": {"type": "boolean", "default": False}
                    }
                }
            }
        }
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(schema_data, f)

        report, exit_code = validate_schema_drift(
            schema_path=schema_path,
            tools_dir=self.temp_dir,
            tool_scope="my_tool",
            fail_unregistered=True
        )
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["drift_count"], 0)

    def test_positive_scope_clean_execution(self):
        """Validates that when modified files are strictly within write_set, scope guard passes."""
        # Initialize temp git repository
        subprocess.run(["git", "init"], cwd=self.temp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=self.temp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.temp_dir, capture_output=True, check=True)

        f1 = os.path.join(self.temp_dir, "allowed.py")
        with open(f1, "w", encoding="utf-8") as f:
            f.write("# initial\n")
        subprocess.run(["git", "add", "allowed.py"], cwd=self.temp_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.temp_dir, capture_output=True, check=True)

        # Mutate allowed file
        with open(f1, "a", encoding="utf-8") as f:
            f.write("# modified\n")

        node = DAGNode(node_id="M1", write_set=["allowed.py"])
        is_valid, unauthorized = check_scope_guard_violation(node, repo_root=self.temp_dir)
        self.assertTrue(is_valid)
        self.assertEqual(len(unauthorized), 0)

    # =========================================================================
    # 2. NEGATIVE SCENARIOS
    # =========================================================================

    def test_negative_vietnamese_text_flagged(self):
        """Validates that Vietnamese diacritics in rule files are caught under Invariant 16."""
        agents_md = os.path.join(self.temp_dir, "AGENTS.md")
        with open(agents_md, "w", encoding="utf-8") as f:
            f.write("# Plan Protocol\nWhenever you plan, lên kế hoạch cho tao.\n")

        violations = check_rule_16_english_codebase(self.temp_dir)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["rule"], 16)
        self.assertIn("Non-English text detected", violations[0]["message"])
        self.assertEqual(violations[0]["line"], 2)

    def test_negative_unregistered_tool_fails_with_exit_code_1(self):
        """Validates that an unregistered CLI tool causes exit code 1 under --fail-unregistered."""
        schema_path = os.path.join(self.temp_dir, "schema.json")
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump({"tools": {}}, f)

        # Create unregistered CLI tool in tools dir
        unreg_tool = os.path.join(self.temp_dir, "unregistered_tool.py")
        with open(unreg_tool, "w", encoding="utf-8") as f:
            f.write("""
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--demo")
""")

        report, exit_code = validate_schema_drift(
            schema_path=schema_path,
            tools_dir=self.temp_dir,
            fail_unregistered=True
        )
        self.assertEqual(exit_code, 1)
        self.assertEqual(report["status"], "DRIFT_DETECTED")
        self.assertTrue(any("UNREGISTERED_TOOL" in str(d) for d in report["drifts"]))

    def test_negative_scope_creep_detected(self):
        """Validates that modifying an unauthorized file outside write_set triggers Scope Violation."""
        subprocess.run(["git", "init"], cwd=self.temp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=self.temp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.temp_dir, capture_output=True, check=True)

        f1 = os.path.join(self.temp_dir, "allowed.py")
        f2 = os.path.join(self.temp_dir, "rogue_out_of_scope.py")
        with open(f1, "w", encoding="utf-8") as f:
            f.write("# initial\n")
        with open(f2, "w", encoding="utf-8") as f:
            f.write("# initial\n")
        subprocess.run(["git", "add", "."], cwd=self.temp_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.temp_dir, capture_output=True, check=True)

        # Mutate BOTH files
        with open(f1, "a", encoding="utf-8") as f:
            f.write("# allowed mod\n")
        with open(f2, "a", encoding="utf-8") as f:
            f.write("# rogue mod\n")

        # Milestone only declared allowed.py
        node = DAGNode(node_id="M1", write_set=["allowed.py"])
        is_valid, unauthorized = check_scope_guard_violation(node, repo_root=self.temp_dir)
        self.assertFalse(is_valid)
        self.assertIn("rogue_out_of_scope.py", unauthorized)

    # =========================================================================
    # 3. BOUNDARY SCENARIOS
    # =========================================================================

    def test_boundary_vietnamese_exemption_marker(self):
        """Validates that lines with synapse-ignore: VIETNAMESE are exempted."""
        agents_md = os.path.join(self.temp_dir, "AGENTS.md")
        with open(agents_md, "w", encoding="utf-8") as f:
            f.write("# Example test phrase: 'lên kế hoạch'  # synapse-ignore: VIETNAMESE\n")

        violations = check_rule_16_english_codebase(self.temp_dir)
        self.assertEqual(len(violations), 0)

    def test_boundary_node_with_empty_write_set_passes(self):
        """Validates that a read-only milestone with empty write_set does not raise errors."""
        node = DAGNode(node_id="M_READONLY", write_set=[])
        is_valid, unauthorized = check_scope_guard_violation(node, repo_root=self.temp_dir)
        self.assertTrue(is_valid)
        self.assertEqual(len(unauthorized), 0)

    # =========================================================================
    # 4. CLI SCENARIOS
    # =========================================================================

    def test_cli_invariant_checker_rule_16(self):
        """Runs invariant_checker.py CLI with --rule 16 --json."""
        cmd = [
            sys.executable,
            "tools/lint/invariant_checker.py",
            "--rule", "16",
            "--json"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        self.assertEqual(res.returncode, 0, f"CLI error: {res.stderr}")
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["violations_count"], 0)

    def test_cli_schema_sentinel_check(self):
        """Runs cli_schema_sentinel.py CLI with --check --json."""
        cmd = [
            sys.executable,
            "tools/lint/cli_schema_sentinel.py",
            "--check",
            "--json"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        self.assertEqual(res.returncode, 0, f"CLI error: {res.stderr}")
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["drift_count"], 0)


if __name__ == "__main__":
    unittest.main()
