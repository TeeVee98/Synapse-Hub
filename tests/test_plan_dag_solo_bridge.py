#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tests/test_plan_dag_solo_bridge.py
----------------------------------
4-Scenario test battery for M3, M4, and M5:
  - M3: Milestone-scoped HMAC receipts, recertification lineage, AST-grounded debate,
        P0 bold-Markdown DAG parsing, and live Scope Guard in SelfHealingDAGExecutor.
  - M4/M5: compile_plan_to_solo_specs, execute_plan_via_solo, solo_runner --from-plan,
           --milestone, --require-four-scenarios, --recertify-red, auto-target --purple,
           and decisions.tsv strict audit trail.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from tools.design.dag_self_healer import DAGNode, SelfHealingDAGExecutor, parse_plan_to_dag
from tools.orchestration.solo_contracts import (
    ScopedRedReceiptDTO,
    _verify_red_receipt_hmac,
    compute_red_receipt_hmac,
    recertify_red_receipt_payload,
    resolve_red_receipt_path,
    resolve_red_receipt_ttl,
)
from tools.reasoning.prover_verifier_games import ProverVerifierGame


BOLD_SUPER_PLAN = """# Spec-Driven Implementation Plan: Bold Key Parsing

## 3. Atomic Milestones (Execution DAG)

### Milestone 1: Scoped Receipts
- **Node ID:** `M1` | **depends_on:** `[]`
- **Compute Tier:** `[Model: Pro / Reasoning | Thinking: High | Best-of-3]`
- **Write Set:** `['alpha.py', 'beta.py']`
- **Rollback Hook:** `git checkout -- alpha.py beta.py`
- **Pass Gate:** `python3 -m pytest tests/test_alpha.py -q`

### Milestone 2: Integration
- **Node ID:** `M2` | **depends_on:** `[M1]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Write Set:** `['gamma.py']`
- **Rollback Hook:** `git checkout -- gamma.py`
- **Pass Gate:** `python3 -m pytest tests/test_gamma.py -q`
"""


class TestM3ReceiptsDebateAndDagHealer(unittest.TestCase):
    """4-Scenario verification for M3 contracts."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # 1. Positive
    def test_m3_positive_scoped_receipt_path_hmac_and_recertification(self) -> None:
        key = b"unit-test-hmac-secret-key"
        scoped_path = resolve_red_receipt_path(self.temp_dir, milestone_id="M3")
        self.assertTrue(scoped_path.endswith(os.path.join("reports", "solo_receipts", "M3_red.json")))
        legacy_path = resolve_red_receipt_path(self.temp_dir)
        self.assertTrue(legacy_path.endswith(os.path.join("reports", "tdd_red_receipt.json")))
        self.assertEqual(resolve_red_receipt_ttl(ttl_seconds=1800), 1800)

        base_payload = {
            "milestone_id": "M3",
            "status": "CERTIFIED_RED",
            "certified_at": "2026-11-26T12:00:00+00:00",
            "commit_hash": "abc123",
            "normalized_cmd": "python -m pytest tests/test_a.py",
            "executed_tests": ["tests/test_a.py"],
            "test_tree_hash": "tree_hash_1",
            "failure_sha256": "fail_hash_1",
            "ttl_seconds": 1800,
        }
        base_payload["receipt_hmac"] = compute_red_receipt_hmac(base_payload, key=key)
        self.assertTrue(_verify_red_receipt_hmac(base_payload, key=key))

        # Recertification binds previous HMAC cryptographically
        next_payload = dict(base_payload, test_tree_hash="tree_hash_2", failure_sha256="fail_hash_2")
        next_payload.pop("receipt_hmac", None)
        recertified = recertify_red_receipt_payload(base_payload, next_payload, key=key)
        self.assertEqual(recertified["recertified_from_hmac"], base_payload["receipt_hmac"])
        self.assertTrue(_verify_red_receipt_hmac(recertified, key=key))

        dto = ScopedRedReceiptDTO(
            milestone_id="M3",
            status=recertified["status"],
            certified_at=recertified["certified_at"],
            commit_hash=recertified["commit_hash"],
            normalized_cmd=recertified["normalized_cmd"],
            test_tree_hash=recertified["test_tree_hash"],
            failure_sha256=recertified["failure_sha256"],
            ttl_seconds=recertified["ttl_seconds"],
            recertified_from_hmac=recertified["recertified_from_hmac"],
            receipt_hmac=recertified["receipt_hmac"],
        )
        self.assertEqual(dto.milestone_id, "M3")

    def test_m3_positive_parse_plan_to_dag_bold_markdown_keys(self) -> None:
        executor = parse_plan_to_dag(BOLD_SUPER_PLAN)
        self.assertIn("M1", executor.nodes)
        self.assertIn("M2", executor.nodes)
        m1 = executor.nodes["M1"]
        self.assertEqual(m1.depends_on, [])
        self.assertEqual(m1.write_set, ["alpha.py", "beta.py"])
        self.assertEqual(m1.pass_gate, "python3 -m pytest tests/test_alpha.py -q")
        self.assertEqual(m1.rollback_hook, "git checkout -- alpha.py beta.py")
        self.assertIn("Pro / Reasoning", m1.compute_tier)
        self.assertEqual(executor.nodes["M2"].depends_on, ["M1"])

    def test_m3_positive_ast_grounded_offline_python_debate(self) -> None:
        py_module = (
            "import json\n"
            "import os\n\n"
            "def compute_checksum(payload: str, salt: str) -> str:\n"
            "    return payload + salt\n"
        )
        game = ProverVerifierGame()
        res = game.run_debate(
            proposal="Harden compute_checksum to validate encoding deterministically.",
            context=py_module,
            rounds=2,
        )
        self.assertEqual(res["provenance_tag"], "[AST-Heuristic]")
        self.assertIn("compute_checksum", res["ast_grounded_symbols"])
        all_counters = " ".join(
            " ".join(r["verifier_counter"]["counter_examples"]) for r in res["transcript"]
        )
        self.assertIn("compute_checksum", all_counters)
        self.assertNotIn("HTTP 503", all_counters)
        self.assertNotIn("double-click", all_counters)

    # 2. Negative
    def test_m3_negative_tampered_milestone_or_lineage_fails_hmac_and_live_scope_guard_halts(self) -> None:
        key = b"unit-test-hmac-secret-key"
        payload = {
            "milestone_id": "M1",
            "status": "CERTIFIED_RED",
            "certified_at": "2026-11-26T12:00:00+00:00",
            "commit_hash": "abc123",
            "normalized_cmd": "python -m pytest tests/test_a.py",
            "executed_tests": ["tests/test_a.py"],
            "test_tree_hash": "tree_hash_1",
            "failure_sha256": "fail_hash_1",
            "ttl_seconds": 900,
        }
        payload["receipt_hmac"] = compute_red_receipt_hmac(payload, key=key)
        tampered = dict(payload, milestone_id="M2")
        self.assertFalse(_verify_red_receipt_hmac(tampered, key=key))

        # Live Scope Guard inside run_dag_live halts on unauthorized modified file
        repo_dir = tempfile.mkdtemp(dir=self.temp_dir)
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo_dir, capture_output=True, check=True)
        with open(os.path.join(repo_dir, "a.py"), "w", encoding="utf-8") as fh:
            fh.write("A = 1\n")
        with open(os.path.join(repo_dir, "b.py"), "w", encoding="utf-8") as fh:
            fh.write("B = 1\n")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, capture_output=True, check=True)

        # Unauthorized edit to b.py while M1 write_set only allows a.py
        with open(os.path.join(repo_dir, "b.py"), "w", encoding="utf-8") as fh:
            fh.write("B = 999\n")

        executor = SelfHealingDAGExecutor(repo_root=repo_dir)
        executor.add_node(
            DAGNode(
                node_id="M1",
                depends_on=[],
                write_set=["a.py"],
                pass_gate=f"{sys.executable} -c 'print(1)'",
            )
        )
        res = executor.run_dag_live(dry_run=False)
        self.assertFalse(res["all_success"])
        self.assertTrue(len(res.get("scope_guard_violations", [])) >= 1)
        self.assertEqual(res["final_status"]["M1"], "FAILED")

    # 3. Boundary
    def test_m3_boundary_empty_milestone_and_invalid_ttl_fallback(self) -> None:
        self.assertEqual(resolve_red_receipt_ttl(ttl_seconds=0, default_ttl=900), 900)
        self.assertEqual(resolve_red_receipt_ttl(ttl_seconds=-5, default_ttl=600), 600)
        empty_exec = parse_plan_to_dag("")
        self.assertEqual(len(empty_exec.nodes), 0)

    # 4. CLI / Provenance flag resilience
    def test_m3_cli_prover_verifier_json_includes_provenance_tag(self) -> None:
        import json

        proc = subprocess.run(
            [
                sys.executable,
                "tools/reasoning/prover_verifier_games.py",
                "--proposal",
                "Validate JSON schema deterministically",
                "--rounds",
                "1",
                "--json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, f"CLI failed: {proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertIn("provenance_tag", data)
        self.assertEqual(data["provenance_tag"], "[AST-Heuristic]")


class TestPlanDagSoloBridge(unittest.TestCase):
    """M5 4-Scenario Verification Suite for tools/orchestration/plan_dag_bridge.py & solo_runner.py."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _init_git_repo(self) -> str:
        repo_dir = tempfile.mkdtemp(dir=self.temp_dir)
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=repo_dir, capture_output=True, check=True)
        return repo_dir

    def _create_two_milestone_repo(self) -> tuple[str, str]:
        repo_dir = self._init_git_repo()
        os.makedirs(os.path.join(repo_dir, "tests"), exist_ok=True)
        with open(os.path.join(repo_dir, "mod_a.py"), "w", encoding="utf-8") as fh:
            fh.write(
                "def add_positive(x: int, y: int) -> int:\n"
                "    if x < 0 or y < 0:\n"
                "        raise ValueError('negative')\n"
                "    return x + y\n"
            )
        with open(os.path.join(repo_dir, "tests", "test_mod_a.py"), "w", encoding="utf-8") as fh:
            fh.write(
                "import pytest\n"
                "from mod_a import add_positive\n\n"
                "def test_positive_add():\n"
                "    assert add_positive(2, 3) == 5\n\n"
                "def test_negative_raises():\n"
                "    with pytest.raises(ValueError):\n"
                "        add_positive(-1, 2)\n"
                "    with pytest.raises(ValueError):\n"
                "        add_positive(2, -1)\n\n"
                "def test_boundary_zero():\n"
                "    assert add_positive(0, 0) == 0\n\n"
                "def test_resilience_idempotent():\n"
                "    assert add_positive(4, 6) == 10\n"
            )
        with open(os.path.join(repo_dir, "mod_b.py"), "w", encoding="utf-8") as fh:
            fh.write(
                "from mod_a import add_positive\n\n"
                "def double_sum(x: int, y: int) -> int:\n"
                "    return add_positive(x, y) * 2\n"
            )
        with open(os.path.join(repo_dir, "tests", "test_mod_b.py"), "w", encoding="utf-8") as fh:
            fh.write(
                "from mod_b import double_sum\n\n"
                "def test_positive_double_sum():\n"
                "    assert double_sum(2, 3) == 10\n\n"
                "def test_negative_invalid():\n"
                "    try:\n"
                "        double_sum(-1, 1)\n"
                "        assert False\n"
                "    except ValueError:\n"
                "        assert True\n\n"
                "def test_boundary_zero():\n"
                "    assert double_sum(0, 0) == 0\n\n"
                "def test_resilience_repeat():\n"
                "    assert double_sum(1, 2) == 6\n"
            )
        plan_path = os.path.join(repo_dir, "plan_closed_loop.md")
        with open(plan_path, "w", encoding="utf-8") as fh:
            fh.write(
                "# Spec-Driven Implementation Plan: Two-Milestone Math Bridge\n\n"
                "## 3. Atomic Milestones (Execution DAG)\n\n"
                "### Milestone 1: Core Math Module\n"
                "- **Node ID:** `M1` | **depends_on:** `[]`\n"
                "- **Compute Tier:** `[Model: Pro / Reasoning | Thinking: High]`\n"
                "- **Write Set:** `['mod_a.py', 'tests/test_mod_a.py']`\n"
                "- **Rollback Hook:** `git checkout -- mod_a.py tests/test_mod_a.py`\n"
                f"- **Pass Gate:** `{sys.executable} -m pytest tests/test_mod_a.py -q`\n\n"
                "### Milestone 2: Wrapper Integration\n"
                "- **Node ID:** `M2` | **depends_on:** `[M1]`\n"
                "- **Compute Tier:** `[Model: Flash | Thinking: Off]`\n"
                "- **Write Set:** `['mod_b.py', 'tests/test_mod_b.py']`\n"
                "- **Rollback Hook:** `git checkout -- mod_b.py tests/test_mod_b.py`\n"
                f"- **Pass Gate:** `{sys.executable} -m pytest tests/test_mod_b.py -q`\n"
            )
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "baseline"], cwd=repo_dir, capture_output=True, check=True)
        return repo_dir, plan_path

    # 1. POSITIVE SCENARIO (TC-01)
    def test_positive_closed_loop_from_plan(self) -> None:
        """TC-01: Compiles M1 -> M2, executes Red/Green/Mutation/Purple per node, writes 2 strict rows to decisions.tsv."""
        from dataclasses import FrozenInstanceError
        from tools.core.decision_log import audit_decision_log
        from tools.orchestration.plan_dag_bridge import (
            PlanExecutionSummaryDTO,
            compile_plan_to_solo_specs,
            execute_plan_via_solo,
        )

        repo_dir, plan_path = self._create_two_milestone_repo()
        specs = compile_plan_to_solo_specs(plan_path, repo_root=repo_dir)
        self.assertEqual([s.node_id for s in specs], ["M1", "M2"])
        self.assertEqual(specs[0].target_source_files, ("mod_a.py",))
        self.assertEqual(specs[1].depends_on, ("M1",))
        self.assertTrue(specs[0].require_four_scenarios)
        self.assertIsInstance(specs[0].to_dict(), dict)
        with self.assertRaises(FrozenInstanceError):
            specs[0].node_id = "MUTATED"  # type: ignore[misc]

        log_path = os.path.join(repo_dir, "decisions.tsv")
        summary = execute_plan_via_solo(
            plan_path=plan_path,
            repo_root=repo_dir,
            decision_log_path=log_path,
            sandbox_mode="host",
        )
        self.assertIsInstance(summary, PlanExecutionSummaryDTO)
        self.assertTrue(summary.passed, f"Summary failed: {summary.to_dict()}")
        self.assertEqual(summary.milestones_total, 2)
        self.assertEqual(summary.milestones_passed, 2)
        self.assertIsNone(summary.halted_at_node)
        self.assertGreaterEqual(len(summary.receipt_paths), 2)
        with self.assertRaises(FrozenInstanceError):
            summary.passed = False  # type: ignore[misc]

        audit = audit_decision_log(log_path, strict=True)
        self.assertTrue(audit["valid"], f"Decision log audit failed: {audit}")
        self.assertEqual(audit["row_count"], 2)

        # Single-milestone filter check
        filtered = execute_plan_via_solo(
            plan_path=plan_path,
            repo_root=repo_dir,
            milestone_filter="M1",
            decision_log_path=os.path.join(repo_dir, "m1_only.tsv"),
            sandbox_mode="host",
        )
        self.assertTrue(filtered.passed)
        self.assertEqual(filtered.milestones_total, 1)

    # 2. NEGATIVE SCENARIO (TC-03)
    def test_negative_scope_guard_halts_and_rolls_back(self) -> None:
        """TC-03: Modifying b.py outside M1 write_set halts execution, rolls back to clean git status, logs failure."""
        from tools.core.decision_log import audit_decision_log
        from tools.orchestration.plan_dag_bridge import execute_plan_via_solo

        repo_dir, plan_path = self._create_two_milestone_repo()

        # Unauthorized modification to mod_b.py while running M1 (write_set=['mod_a.py', 'tests/test_mod_a.py'])
        mod_b_path = os.path.join(repo_dir, "mod_b.py")
        with open(mod_b_path, "r", encoding="utf-8") as fh:
            original_mod_b = fh.read()
        with open(mod_b_path, "w", encoding="utf-8") as fh:
            fh.write("# unauthorized edit outside M1\n")

        log_path = os.path.join(repo_dir, "scope_decisions.tsv")
        summary = execute_plan_via_solo(
            plan_path=plan_path,
            repo_root=repo_dir,
            decision_log_path=log_path,
            sandbox_mode="host",
        )
        self.assertFalse(summary.passed)
        self.assertEqual(summary.halted_at_node, "M1")
        self.assertEqual(summary.milestones_passed, 0)

        # Verify path-scoped rollback restored mod_b.py and git status is clean (ignoring decision log)
        with open(mod_b_path, "r", encoding="utf-8") as fh:
            self.assertEqual(fh.read(), original_mod_b)
        st = subprocess.run(
            ["git", "status", "--porcelain", "--", "mod_a.py", "mod_b.py"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(st.stdout.strip(), "")
        audit = audit_decision_log(log_path, strict=True)
        self.assertTrue(audit["valid"])
        self.assertEqual(audit["row_count"], 1)

    # 3. BOUNDARY SCENARIOS (TC-04)
    def test_boundary_empty_corrupt_and_cyclic_plan_rejection(self) -> None:
        """Boundary: Empty plan, missing plan, zero milestones, cyclic DAG, and unknown milestone raise cleanly."""
        from tools.orchestration.plan_dag_bridge import compile_plan_to_solo_specs, execute_plan_via_solo

        with self.assertRaises(ValueError):
            compile_plan_to_solo_specs("   ", repo_root=self.temp_dir)

        with self.assertRaises(FileNotFoundError):
            compile_plan_to_solo_specs(os.path.join(self.temp_dir, "missing.md"), repo_root=self.temp_dir)

        empty_plan = os.path.join(self.temp_dir, "empty.md")
        with open(empty_plan, "w", encoding="utf-8") as fh:
            fh.write("   \n")
        with self.assertRaises(ValueError):
            compile_plan_to_solo_specs(empty_plan, repo_root=self.temp_dir)

        no_nodes_plan = os.path.join(self.temp_dir, "no_nodes.md")
        with open(no_nodes_plan, "w", encoding="utf-8") as fh:
            fh.write("# Plan Without Milestones\nJust prose.\n")
        with self.assertRaises(ValueError):
            compile_plan_to_solo_specs(no_nodes_plan, repo_root=self.temp_dir)

        cyclic_plan = os.path.join(self.temp_dir, "cyclic.md")
        with open(cyclic_plan, "w", encoding="utf-8") as fh:
            fh.write(
                "### Milestone 1: A\n- **Node ID:** `M1` | **depends_on:** `[M2]`\n- **Write Set:** `['a.py']`\n"
                "### Milestone 2: B\n- **Node ID:** `M2` | **depends_on:** `[M1]`\n- **Write Set:** `['b.py']`\n"
            )
        with self.assertRaises(ValueError):
            compile_plan_to_solo_specs(cyclic_plan, repo_root=self.temp_dir)

        # Tier-0 plan sets require_four_scenarios=False and synthesizes pytest cmd from test write_set
        tier0_plan = os.path.join(self.temp_dir, "tier0.md")
        with open(tier0_plan, "w", encoding="utf-8") as fh:
            fh.write(
                "# Fast-Track Micro-Plan: Quick Fix\n"
                "### Milestone 1: Quick\n- **Node ID:** `M1` | **depends_on:** `[]`\n"
                "- **Write Set:** `['helper.py', 'tests/test_helper.py']`\n"
            )
        # Relative plan path resolution (kills isabs/isfile mutation) + synthesized pass_gate + title
        tier0_specs = compile_plan_to_solo_specs("tier0.md", repo_root=self.temp_dir)
        six_plan = os.path.join(self.temp_dir, "six_milestones.md")
        with open(six_plan, "w", encoding="utf-8") as fh:
            fh.write(
                "# Tier-2 Super-Plan: Six Milestones\n"
                + "".join(
                    f"### Milestone {i}: Step {i}\n"
                    f"- **Node ID:** `M{i}` | **depends_on:** `[{'' if i == 1 else f'M{i-1}'}]`\n"
                    f"- **Write Set:** `['mod_{i}.py', 'tests/test_mod_{i}.py']`\n"
                    for i in range(1, 7)
                )
            )
        self.assertEqual(len(compile_plan_to_solo_specs("six_milestones.md", repo_root=self.temp_dir)), 6)
        self.assertFalse(tier0_specs[0].require_four_scenarios)
        self.assertIn("pytest", tier0_specs[0].test_cmd)
        self.assertEqual(tier0_specs[0].pass_gate, tier0_specs[0].test_cmd)
        self.assertEqual(tier0_specs[0].title, "Milestone 1: Quick")

        # Default DTO flag + _is_test_path classification across all test path patterns + rollback guard
        from tools.orchestration.plan_dag_bridge import (
            MilestoneExecutionSpecDTO,
            _is_test_path,
            _rollback_unauthorized_files,
        )

        default_spec = MilestoneExecutionSpecDTO(
            node_id="M0",
            title="Default",
            depends_on=(),
            write_set=(),
            target_source_files=(),
            test_cmd="",
            pass_gate="",
            rollback_hook="",
        )
        self.assertTrue(default_spec.require_four_scenarios)
        self.assertTrue(_is_test_path("pkg/tests/helper.py"))
        self.assertTrue(_is_test_path("src/test_unit.py"))
        self.assertTrue(_is_test_path("src/unit_test.py"))
        self.assertTrue(_is_test_path("e2e/login.spec.ts"))
        self.assertTrue(_is_test_path("e2e/login.test.js"))
        self.assertFalse(_is_test_path("tools/core/helper.py"))

        rb_noop = _rollback_unauthorized_files(["", "SCOPE_GUARD_UNVERIFIABLE: err"], self.temp_dir)
        self.assertTrue(rb_noop["success"])
        self.assertEqual(rb_noop["reverted_files"], [])

        # Unknown milestone filter raises ValueError
        with self.assertRaises(ValueError):
            execute_plan_via_solo(tier0_plan, repo_root=self.temp_dir, milestone_filter="M999")

    # 4. CLI & SOLO RUNNER WIRING SCENARIOS (TC-05)
    def test_cli_solo_runner_flags_milestone_recertify_four_scenarios_and_commit_progression(self) -> None:
        """TC-05: Verifies --milestone, --require-four-scenarios, --recertify-red, commit progression, and CLI --from-plan."""
        import json
        from tools.orchestration.solo_runner import certify_green_phase, certify_red_phase

        repo_dir = self._init_git_repo()
        os.makedirs(os.path.join(repo_dir, "tests"), exist_ok=True)
        src_p = os.path.join(repo_dir, "calc.py")
        test_p = os.path.join(repo_dir, "tests", "test_calc.py")
        with open(src_p, "w", encoding="utf-8") as fh:
            fh.write("def triple(x: int) -> int:\n    return x\n")
        with open(test_p, "w", encoding="utf-8") as fh:
            fh.write("from calc import triple\ndef test_only_one():\n    assert triple(3) == 9\n")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_dir, capture_output=True, check=True)

        test_cmd = f"{sys.executable} -m pytest tests/test_calc.py -q"

        # 1. require_four_scenarios=True rejects 1-test file
        red_reject = certify_red_phase(
            test_cmd=test_cmd,
            cwd=repo_dir,
            require_four_scenarios=True,
            milestone_id="M1",
        )
        self.assertFalse(red_reject["passed"])
        self.assertEqual(red_reject["status"], "MISSING_SCENARIO_COVERAGE_REJECTED")

        # 2. Expand to 4 scenarios -> CERTIFIED_RED in milestone-scoped receipt
        with open(test_p, "w", encoding="utf-8") as fh:
            fh.write(
                "from calc import triple\n"
                "def test_positive_triple(): assert triple(3) == 9\n"
                "def test_negative_invalid(): assert triple(-2) == -6\n"
                "def test_boundary_zero(): assert triple(0) == 0\n"
                "def test_resilience_idempotent(): assert triple(1) == 3\n"
            )
        red_ok = certify_red_phase(
            test_cmd=test_cmd,
            cwd=repo_dir,
            require_four_scenarios=True,
            milestone_id="M1",
            ttl_seconds=1200,
        )
        self.assertTrue(red_ok["passed"], f"Red failed: {red_ok}")
        self.assertTrue(red_ok["receipt_file"].endswith(os.path.join("reports", "solo_receipts", "M1_red.json")))
        first_hmac = red_ok["receipt_hmac"]

        # 3. Audited --recertify-red chains recertified_from_hmac
        recert = certify_red_phase(
            test_cmd=test_cmd,
            cwd=repo_dir,
            require_four_scenarios=True,
            milestone_id="M1",
            recertify_red=True,
        )
        self.assertTrue(recert["passed"])
        self.assertEqual(recert["recertified_from_hmac"], first_hmac)

        # 4. Commit the Red test AND implement fix in next commit -> commit progression allowed when test_tree_hash intact
        subprocess.run(["git", "add", "tests/test_calc.py"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "commit red tests"], cwd=repo_dir, capture_output=True, check=True)
        with open(src_p, "w", encoding="utf-8") as fh:
            fh.write("def triple(x: int) -> int:\n    return x * 3\n")
        green_ok = certify_green_phase(
            test_cmd=test_cmd,
            cwd=repo_dir,
            milestone_id="M1",
            sandbox_mode="host",
        )
        self.assertTrue(green_ok["passed"], f"Green failed after commit progression: {green_ok}")
        self.assertTrue(green_ok["commit_progressed"])

        # 5. CLI --from-plan error handling returns exit code 1 cleanly with JSON
        cli_err = subprocess.run(
            [
                sys.executable,
                "tools/orchestration/solo_runner.py",
                "--from-plan",
                os.path.join(self.temp_dir, "does_not_exist.md"),
                "--json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(cli_err.returncode, 1)
        err_payload = json.loads(cli_err.stdout)
        self.assertFalse(err_payload["plan_execution"]["passed"])

    def test_strict_red_rejects_missing_red_receipt_and_diff_only_mutation_default(self) -> None:
        """Positive + Negative: --strict-red blocks replay without Red receipt; diff_only_mutation=True scopes by diff."""
        from tools.orchestration.plan_dag_bridge import execute_plan_via_solo
        from tools.orchestration.solo_runner import certify_red_phase

        repo_dir, plan_path = self._create_two_milestone_repo()

        # 1. Negative: strict_red=True rejects when M1_red.json is missing even though tests pass
        strict_fail = execute_plan_via_solo(
            plan_path=plan_path,
            repo_root=repo_dir,
            milestone_filter="M1",
            decision_log_path=os.path.join(self.temp_dir, "strict_fail.tsv"),
            sandbox_mode="host",
            strict_red=True,
        )
        self.assertFalse(strict_fail.passed)
        self.assertEqual(strict_fail.halted_at_node, "M1")
        green_phase = strict_fail.milestone_results[0]["phases"]["green"]
        self.assertEqual(green_phase["status"], "MISSING_RED_RECEIPT")

        # 2. Positive: after certifying Red for M1 (break -> certify red -> restore), strict_red=True succeeds
        mod_a_path = os.path.join(repo_dir, "mod_a.py")
        with open(mod_a_path, "r", encoding="utf-8") as fh:
            good_mod_a = fh.read()
        with open(mod_a_path, "w", encoding="utf-8") as fh:
            fh.write("def add_positive(x: int, y: int) -> int:\n    return 0\n")
        red_res = certify_red_phase(
            test_cmd=f"{sys.executable} -m pytest tests/test_mod_a.py -q",
            cwd=repo_dir,
            milestone_id="M1",
            require_four_scenarios=True,
        )
        self.assertTrue(red_res["passed"])
        with open(mod_a_path, "w", encoding="utf-8") as fh:
            fh.write(good_mod_a)

        strict_pass = execute_plan_via_solo(
            plan_path=plan_path,
            repo_root=repo_dir,
            milestone_filter="M1",
            decision_log_path=os.path.join(self.temp_dir, "strict_pass.tsv"),
            sandbox_mode="host",
            strict_red=True,
        )
        self.assertTrue(strict_pass.passed, f"Strict red pass failed: {strict_pass.to_dict()}")
        mut_details = strict_pass.milestone_results[0]["phases"]["mutation"]["targets"]["mod_a.py"]
        self.assertEqual(mut_details["scope_requested"], "diff_only")

    def test_purple_and_bridge_audit_all_target_source_files(self) -> None:
        """Negative + Positive: Multi-file milestone Purple audit catches cycle in 2nd target file, not just index 0."""
        from tools.orchestration.plan_dag_bridge import execute_plan_via_solo
        from tools.orchestration.solo_runner import certify_purple_phase

        repo_dir = self._init_git_repo()
        os.makedirs(os.path.join(repo_dir, "tests"), exist_ok=True)
        with open(os.path.join(repo_dir, "clean_mod.py"), "w", encoding="utf-8") as fh:
            fh.write("def ok(x: int) -> int:\n    return x + 1\n")
        with open(os.path.join(repo_dir, "cycle_b.py"), "w", encoding="utf-8") as fh:
            fh.write("import cycle_c\ndef fb() -> int:\n    return 1\n")
        with open(os.path.join(repo_dir, "cycle_c.py"), "w", encoding="utf-8") as fh:
            fh.write("import cycle_b\ndef fc() -> int:\n    return 2\n")
        with open(os.path.join(repo_dir, "tests", "test_multi.py"), "w", encoding="utf-8") as fh:
            fh.write(
                "from clean_mod import ok\n"
                "def test_positive_ok(): assert ok(1) == 2\n"
                "def test_negative_ok(): assert ok(-1) == 0\n"
                "def test_boundary_ok(): assert ok(0) == 1\n"
                "def test_resilience_ok(): assert ok(2) == 3\n"
            )
        plan_path = os.path.join(repo_dir, "multi_target_plan.md")
        with open(plan_path, "w", encoding="utf-8") as fh:
            fh.write(
                "# Spec-Driven Implementation Plan: Multi-Target Purple\n\n"
                "## 3. Atomic Milestones (Execution DAG)\n\n"
                "### Milestone 1: Multi-File Node\n"
                "- **Node ID:** `M1` | **depends_on:** `[]`\n"
                "- **Compute Tier:** `[Model: Pro | Thinking: High]`\n"
                "- **Write Set:** `['clean_mod.py', 'cycle_b.py', 'tests/test_multi.py']`\n"
                "- **Rollback Hook:** `git checkout -- clean_mod.py cycle_b.py tests/test_multi.py`\n"
                f"- **Pass Gate:** `{sys.executable} -m pytest tests/test_multi.py -q`\n"
            )
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "baseline"], cwd=repo_dir, capture_output=True, check=True)

        purple_res = certify_purple_phase(
            target="uncommitted",
            target_files=["clean_mod.py", "cycle_b.py"],
            receipt_path=os.path.join(repo_dir, "purple.json"),
            repo_root=repo_dir,
        )
        self.assertFalse(purple_res["passed"])
        self.assertEqual(purple_res["targets_audited"], ["clean_mod.py", "cycle_b.py"])
        self.assertIn("cycle_b.py", purple_res["neuro_symbolic_reviews"])
        self.assertFalse(purple_res["neuro_symbolic_reviews"]["cycle_b.py"]["passed"])

        bridge_res = execute_plan_via_solo(
            plan_path=plan_path,
            repo_root=repo_dir,
            decision_log_path=os.path.join(repo_dir, "multi.tsv"),
            sandbox_mode="host",
            run_mutation=False,
            run_purple=True,
        )
        self.assertFalse(bridge_res.passed)
        self.assertEqual(bridge_res.halted_at_node, "M1")

    def test_auto_review_runs_automatically_after_from_plan_and_blocks_on_drift(self) -> None:
        """Positive + Negative + Opt-out: execute_plan_via_solo auto-runs /review, emits signed receipt, and blocks on Must-fix drift."""
        import json
        from tools.orchestration.plan_dag_bridge import execute_plan_via_solo
        from tools.orchestration.plan_review_auditor import verify_review_receipt_hmac
        from tools.orchestration.solo_contracts import _get_receipt_hmac_key

        repo_dir, plan_path = self._create_two_milestone_repo()

        # 1. Positive: auto_review=True (default) populates review_result and signs code_review_receipt.json
        res_ok = execute_plan_via_solo(
            plan_path=plan_path,
            repo_root=repo_dir,
            decision_log_path=os.path.join(repo_dir, "decisions.tsv"),
            sandbox_mode="host",
        )
        self.assertTrue(res_ok.passed, f"Expected pass: {res_ok.to_dict()}")
        self.assertIsNotNone(res_ok.review_result)
        assert res_ok.review_result is not None
        self.assertEqual(res_ok.review_result["verdict"], "APPROVED")
        self.assertTrue(res_ok.review_result["passed"])
        receipt_p = os.path.join(repo_dir, "reports", "code_review_receipt.json")
        self.assertTrue(os.path.isfile(receipt_p))
        self.assertIn(receipt_p, res_ok.receipt_paths)
        loaded_rcpt = json.loads(open(receipt_p, encoding="utf-8").read())
        self.assertTrue(verify_review_receipt_hmac(loaded_rcpt, key=_get_receipt_hmac_key(repo_dir)))

        # 2. Boundary / Opt-out: auto_review=False skips automatic /review
        res_skip = execute_plan_via_solo(
            plan_path=plan_path,
            repo_root=repo_dir,
            decision_log_path=os.path.join(self.temp_dir, "auto_skip.tsv"),
            sandbox_mode="host",
            auto_review=False,
        )
        self.assertTrue(res_skip.passed)
        self.assertIsNone(res_skip.review_result)

        # 3. Negative: Plan declares Section 1 [CREATE] missing_artifact.py -> milestones pass but auto /review blocks!
        drift_plan = os.path.join(self.temp_dir, "plan_with_drift.md")
        with open(drift_plan, "w", encoding="utf-8") as fh:
            fh.write(
                "# Spec-Driven Implementation Plan: Auto-Review Drift Gate\n\n"
                "## 1. Affected Files & Blast Radius\n\n"
                "| Action | File Path & Structural Anchor | Scope & Responsibility |\n"
                "|---|---|---|\n"
                "| `[CREATE]` | `mod_a.py` (New) | Core math |\n"
                "| `[CREATE]` | `missing_artifact.py` (New) | Planned but never created |\n\n"
                "## 3. Atomic Milestones (Execution DAG)\n\n"
                "### Milestone 1: Core Math Module\n"
                "- **Node ID:** `M1` | **depends_on:** `[]`\n"
                "- **Write Set:** `['mod_a.py', 'tests/test_mod_a.py']`\n"
                f"- **Pass Gate:** `{sys.executable} -m pytest tests/test_mod_a.py -q`\n"
            )
        res_blocked = execute_plan_via_solo(
            plan_path=drift_plan,
            repo_root=repo_dir,
            decision_log_path=os.path.join(self.temp_dir, "auto_block.tsv"),
            sandbox_mode="host",
            auto_review=True,
        )
        self.assertFalse(res_blocked.passed)
        self.assertEqual(res_blocked.halted_at_node, "REVIEW")
        self.assertIsNotNone(res_blocked.review_result)
        assert res_blocked.review_result is not None
        self.assertFalse(res_blocked.review_result["passed"])
        self.assertEqual(res_blocked.review_result["verdict"], "CHANGES_REQUESTED")

        # 4. CLI --from-plan --no-review --json runs strictly in isolated repo_dir and emits single valid JSON
        repo_root_real = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        solo_script = os.path.join(repo_root_real, "tools", "orchestration", "solo_runner.py")
        cli_proc = subprocess.run(
            [
                sys.executable,
                solo_script,
                "--from-plan",
                os.path.join(self.temp_dir, "does_not_exist.md"),
                "--no-review",
                "--json",
            ],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(cli_proc.returncode, 2, f"Unexpected argparse error: {cli_proc.stderr}")
        cli_payload = json.loads(cli_proc.stdout)
        self.assertFalse(cli_payload["plan_execution"]["passed"])

        # 5. Bulk dirty-tree safety guard aborts rollback instead of wiping >10 unrelated files
        from tools.orchestration.plan_dag_bridge import _rollback_unauthorized_files

        many_files = [f"unrelated_{i}.py" for i in range(12)]
        rb_bulk = _rollback_unauthorized_files(many_files, repo_dir)
        self.assertFalse(rb_bulk["success"])
        self.assertTrue(rb_bulk["aborted_bulk_rollback"])


if __name__ == "__main__":
    unittest.main()
