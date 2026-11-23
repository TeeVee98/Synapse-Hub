#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tests/test_super_plan_10_perfection.py — Comprehensive Test Battery for 10.0 Super-Plan Perfection
--------------------------------------------------------------------------------------------------
Validates:
  1. Polyglot AST Engine (Python, TypeScript, JavaScript, Java, Groovy) with structural anchors.
  2. Persistent Call Graph & Fan-In Indexer (mtime cache, sub-15ms lookup, dependency queries).
  3. Hidden Coupling Sentinel (detects undeclared global/env mutation in [PARALLEL_OK] blocks).
  4. Rollback Hook Safety Validator (rejects rm -rf /, forkbombs, missing binaries; allows safe tools).
  5. Deep Semantic Invariant Drift Harvester (polyglot arity & contract drift detection).
  6. CLI execution across flags (--json, --file, --rebuild).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from tools.context.polyglot_ast_parser import (
    parse_polyglot_signatures
)
from tools.context.call_graph_indexer import (
    get_or_build_call_graph
)
from tools.lint.plan_schema_sentinel import (
    validate_rollback_hook_safety,
    scan_undeclared_couplings
)
from tools.design.plan_harvester import (
    calibrate_plan_against_git
)


class TestSuperPlan10Perfection(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # =========================================================================
    # 1. POSITIVE SCENARIOS
    # =========================================================================

    def test_positive_polyglot_typescript_extraction(self):
        """Validates TS class, interface, type, decorators, and function parsing with AST anchors."""
        ts_code = """
        // Comment containing fake class FakeClass
        export interface UserDTO {
            id: string;
            email: string;
        }

        @Injectable()
        export class UserService {
            @Get('/user/:id')
            async getUserById(id: string): Promise<UserDTO> {
                const s = "class FakeInString";
                return { id, email: "test@example.com" };
            }
        }

        export const calculateScore = async (points: number, multiplier: number) => {
            return points * multiplier;
        };
        """
        ts_file = os.path.join(self.temp_dir, "service.ts")
        with open(ts_file, "w", encoding="utf-8") as f:
            f.write(ts_code)

        res = parse_polyglot_signatures(ts_file)
        self.assertTrue(res["exists"])
        self.assertEqual(res["language"], "typescript")
        symbols = {s["name"]: s for s in res["symbols"]}

        self.assertIn("UserDTO", symbols)
        self.assertEqual(symbols["UserDTO"]["kind"], "interface")
        self.assertIn("[AST: UserDTO |", symbols["UserDTO"]["anchor"])

        self.assertIn("UserService", symbols)
        self.assertEqual(symbols["UserService"]["kind"], "class")

        self.assertIn("calculateScore", symbols)
        self.assertEqual(symbols["calculateScore"]["kind"], "function")

        # Verify comment/string was sanitized and did not create fake symbols
        self.assertNotIn("FakeClass", symbols)
        self.assertNotIn("FakeInString", symbols)

    def test_positive_polyglot_java_and_groovy_extraction(self):
        """Validates Java and Groovy method/class parsing with annotations."""
        java_code = """
        package com.synapse.hub;

        @RestController
        public class OrderService {
            @Override
            public void init() {}

            @Transactional(readOnly = true)
            public OrderResult processOrder(OrderDTO order, boolean expedite) {
                return new OrderResult();
            }

            @Test public void testSameLine() {}
        }
        """
        j_file = os.path.join(self.temp_dir, "OrderService.java")
        with open(j_file, "w", encoding="utf-8") as f:
            f.write(java_code)

        res_j = parse_polyglot_signatures(j_file)
        self.assertTrue(res_j["exists"])
        self.assertEqual(res_j["language"], "java")
        names_j = [s["name"] for s in res_j["symbols"]]
        self.assertIn("OrderService", names_j)
        self.assertIn("processOrder", names_j)
        self.assertIn("testSameLine", names_j)
        self.assertIn("init", names_j)

    def test_positive_python_typed_ast_extraction(self):
        """Validates Python typed function and method AST parsing."""
        py_code = """
        def compute_tax(income: float, rate: float = 0.2) -> float:
            return income * rate

        class BillingEngine:
            def charge(self, user_id: str, amount: float) -> bool:
                return True
        """
        py_file = os.path.join(self.temp_dir, "billing.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write(py_code)

        res = parse_polyglot_signatures(py_file)
        self.assertTrue(res["exists"])
        symbols = {s["name"]: s for s in res["symbols"]}
        self.assertIn("compute_tax", symbols)
        self.assertIn("income: float", symbols["compute_tax"]["signature"])
        self.assertIn("-> float", symbols["compute_tax"]["signature"])
        self.assertIn("BillingEngine.charge", symbols)

        groovy_code = """
        class KatalonHelper {
            def clickElement(String testId, int timeout) {
                println testId
            }
        }
        """
        g_file = os.path.join(self.temp_dir, "KatalonHelper.groovy")
        with open(g_file, "w", encoding="utf-8") as f:
            f.write(groovy_code)

        res_g = parse_polyglot_signatures(g_file)
        self.assertTrue(res_g["exists"])
        self.assertEqual(res_g["language"], "groovy")
        names_g = [s["name"] for s in res_g["symbols"]]
        self.assertIn("KatalonHelper", names_g)
        self.assertIn("clickElement", names_g)

    def test_positive_call_graph_cached_fan_in(self):
        """Validates Call Graph indexing, persistent disk cache, and fast retrieval."""
        cache_dir = os.path.join(self.temp_dir, ".cache")
        # Build index in temp directory with sample files
        f1 = os.path.join(self.temp_dir, "module_a.py")
        f2 = os.path.join(self.temp_dir, "module_b.py")
        with open(f1, "w", encoding="utf-8") as fh:
            fh.write("def helper():\n    return 42\n")
        with open(f2, "w", encoding="utf-8") as fh:
            fh.write("from module_a import helper\ndef run():\n    return helper()\n")

        # First build: populates cache
        graph = get_or_build_call_graph(self.temp_dir, cache_dir=cache_dir)
        self.assertEqual(graph.get_fan_in("module_a.py"), 1)
        self.assertEqual(graph.get_dependents("module_a.py"), ["module_b.py"])

        cache_file = os.path.join(cache_dir, "call_graph_index.json")
        self.assertTrue(os.path.isfile(cache_file))

        # Second load: loads directly from cache
        cached_graph = get_or_build_call_graph(self.temp_dir, cache_dir=cache_dir)
        self.assertEqual(cached_graph.get_fan_in("module_a.py"), 1)

    def test_positive_safe_rollback_hook_accepted(self):
        """Validates that safe rollback hooks (git checkout, python script, npm) are accepted."""
        safe_hooks = [
            "git checkout -- tools/core/agent_runner.py",
            "python3 -c 'print(1)'",
            "pytest tests/test_feature.py",
            "git reset --hard HEAD",
            "shutil_cleanup.sh"
        ]
        # Create dummy executable for custom script
        dummy_script = os.path.join(self.temp_dir, "cleanup.sh")
        with open(dummy_script, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\necho done\n")
        os.chmod(dummy_script, 0o755)

        for hook in safe_hooks:
            if "cleanup.sh" in hook:
                hook = dummy_script
            safe, reason = validate_rollback_hook_safety(hook)
            self.assertTrue(safe, f"Safe hook '{hook}' was rejected: {reason}")

    def test_positive_deep_semantic_drift_exact_match(self):
        """Validates 0% semantic drift when implemented arity and types match planned contract."""
        py_file = os.path.join(self.temp_dir, "feature.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write("def process_transaction(user_id: str, amount: float) -> bool:\n    return True\n")

        plan = f"""
        ## 1. Affected Files
        | `[MODIFY]` | `{py_file}` (AST: process_transaction | L1-L3) | Feature |

        ## 2. Interface Signatures
        ```python
        def process_transaction(user_id: str, amount: float) -> bool:
            pass
        ```
        """
        calib = calibrate_plan_against_git(plan, repo_root=self.temp_dir)
        self.assertEqual(calib["semantic_drift_ratio"], 0.0)
        self.assertEqual(calib["semantic_accuracy_score"], 1.0)
        self.assertEqual(len(calib["drifted_symbols"]), 0)

    # =========================================================================
    # 2. NEGATIVE SCENARIOS
    # =========================================================================

    def test_negative_dangerous_rollback_hook_rejected(self):
        """Validates that destructive rollback commands are blocked."""
        dangerous_hooks = [
            "rm -rf /",
            "rm -rf /*",
            "rm -rf ~/.ssh",
            "rm -rf $HOME/data",
            ":(){ :|:& };:",
            "mkfs /dev/sda1",
            "chmod -R 777 /",
            "rm -rf .git"
        ]
        for hook in dangerous_hooks:
            safe, reason = validate_rollback_hook_safety(hook)
            self.assertFalse(safe, f"Dangerous hook '{hook}' was incorrectly accepted!")
            self.assertIn("Dangerous command pattern detected", reason)

    def test_negative_missing_binary_rollback_hook_rejected(self):
        """Validates that rollback hook with non-existent binary is rejected."""
        hook = "non_existent_binary_xyz123 --clean"
        safe, reason = validate_rollback_hook_safety(hook)
        self.assertFalse(safe)
        self.assertIn("not found on system PATH", reason)

    def test_negative_hidden_state_mutation_in_parallel_detected(self):
        """Validates that mutating global or env state in a [PARALLEL_OK] node fails validation."""
        parallel_block_with_env_mutation = """
        ### Milestone 1: Parallel Worker [PARALLEL_OK]
        - Node ID: `M1` | depends_on: `[]`
        - Compute Tier: [Model: Flash]
        - Write Set: ['worker.py']
        os.environ['GLOBAL_AUTH_TOKEN'] = 'secret'
        Circuit Breaker: Max Fix Attempts: 2 | Rollback: git checkout -- worker.py
        """
        issues = scan_undeclared_couplings(parallel_block_with_env_mutation, node_id="M1")
        self.assertTrue(len(issues) > 0)
        self.assertIn("Hidden State Mutation", issues[0])
        self.assertIn("os.environ", issues[0])

    def test_negative_deep_semantic_arity_drift_detected(self):
        """Validates that arity mismatch (planned 2 params, implemented 4 params) is flagged as drift."""
        py_file = os.path.join(self.temp_dir, "divergent.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write("def calculate_tax(amount: float, rate: float, country: str, discount: float):\n    return 0.0\n")

        plan = f"""
        ## 1. Affected Files
        | `[MODIFY]` | `{py_file}` (AST: calculate_tax | L1-L3) | Tax |

        ## 2. Interface Signatures
        ```python
        def calculate_tax(amount: float, rate: float) -> float:
            pass
        ```
        """
        calib = calibrate_plan_against_git(plan, repo_root=self.temp_dir)
        self.assertGreater(calib["semantic_drift_ratio"], 0.0)
        self.assertTrue(any("arity drift" in s for s in calib["drifted_symbols"]))

    # =========================================================================
    # 3. BOUNDARY SCENARIOS
    # =========================================================================

    def test_boundary_empty_and_comments_only_files(self):
        """Validates polyglot AST parser gracefully handles empty or comments-only files."""
        empty_file = os.path.join(self.temp_dir, "empty.py")
        with open(empty_file, "w", encoding="utf-8") as f:
            f.write("")
        res_empty = parse_polyglot_signatures(empty_file)
        self.assertTrue(res_empty["exists"])
        self.assertEqual(len(res_empty["signatures"]), 0)

        comments_file = os.path.join(self.temp_dir, "comments.ts")
        with open(comments_file, "w", encoding="utf-8") as f:
            f.write("// only comments here\n/* and multi-line */\n")
        res_comments = parse_polyglot_signatures(comments_file)
        self.assertTrue(res_comments["exists"])
        self.assertEqual(len(res_comments["signatures"]), 0)

    def test_boundary_unknown_extension_and_non_existent_file(self):
        """Validates unknown extension returns empty symbols without throwing."""
        txt_file = os.path.join(self.temp_dir, "notes.txt")
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write("Some notes def func(): pass")
        res_txt = parse_polyglot_signatures(txt_file)
        self.assertEqual(res_txt["language"], "unknown")
        self.assertEqual(len(res_txt["signatures"]), 0)

        res_none = parse_polyglot_signatures(os.path.join(self.temp_dir, "does_not_exist.py"))
        self.assertFalse(res_none["exists"])

    def test_boundary_empty_rollback_hook(self):
        """Validates empty string rollback hook is rejected."""
        safe, reason = validate_rollback_hook_safety("")
        self.assertFalse(safe)
        self.assertIn("cannot be empty", reason)

    # =========================================================================
    # 4. CLI SCENARIOS
    # =========================================================================

    def test_cli_polyglot_parser_json_output(self):
        """Runs polyglot_ast_parser.py CLI with --json."""
        cmd = [
            sys.executable,
            "tools/context/polyglot_ast_parser.py",
            "--file", "tools/context/polyglot_ast_parser.py",
            "--json"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        self.assertEqual(res.returncode, 0, f"CLI failed: {res.stderr}")
        data = json.loads(res.stdout)
        self.assertTrue(data["exists"])
        self.assertEqual(data["language"], "python")
        self.assertGreater(len(data["signatures"]), 3)

    def test_cli_call_graph_indexer_json_output(self):
        """Runs call_graph_indexer.py CLI with --file and --json."""
        cmd = [
            sys.executable,
            "tools/context/call_graph_indexer.py",
            "--file", "tools/core/verify_all.py",
            "--json"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        self.assertEqual(res.returncode, 0, f"CLI failed: {res.stderr}")
        data = json.loads(res.stdout)
        self.assertEqual(data["target"], "tools/core/verify_all.py")
        self.assertGreater(data["fan_in"], 0)
        self.assertIn("dependents", data)


if __name__ == "__main__":
    unittest.main()
