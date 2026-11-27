#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
Regression and Hardening Suite for /super-plan -> /solo -> /review (v2.2):
  - M1: Cumulative ancestor Scope Guard (prevents M2+ from destroying M1 work) + path-boundary matching.
  - M2: Task-grounded Super-Plan scaffold (DTOs, callers, real risk/ambiguity, --decisions, TDD milestones,
        unbiased tournament, stop-word AST anchors) + boilerplate/sentinel rejection in lint & loss gates.
  - M3: /review Layer 3 directory-scoped `-k` verification, UNVERIFIABLE_MATRIX_ROW, cross-drive `_safe_relpath`,
        `--baseline-files`, `--no-receipt`, and plan-slug-scoped Red receipt paths.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def _git(repo: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )


def _init_git_repo(repo: str) -> None:
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "qa@synapse.local")
    _git(repo, "config", "user.name", "Synapse QA")
    with open(os.path.join(repo, ".gitignore"), "w", encoding="utf-8") as fh:
        fh.write(".synapse/\ndecisions.tsv\ndecisions.tsv.lock\nreports/\nscratch/\n__pycache__/\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")


class TestSuperPlanSoloReviewHardening(unittest.TestCase):
    """4-scenario hardening suite for M1 (Scope Guard), M2 (Super-Plan), and M3 (Review & Receipts)."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="synapse_v22_harden_")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # =========================================================================
    # M1: Cumulative Scope Guard & Path-Boundary Safety
    # =========================================================================

    def test_m1_positive_cumulative_scope_guard_preserves_m1(self) -> None:
        """Positive (TC-01): Uncommitted M1 edits remain authorized during M2 execution and are NOT rolled back."""
        from tools.orchestration.plan_dag_bridge import execute_plan_via_solo

        repo = os.path.join(self.temp_dir, "m1_pos_repo")
        os.makedirs(os.path.join(repo, "src"), exist_ok=True)
        os.makedirs(os.path.join(repo, "tests"), exist_ok=True)

        calc_path = os.path.join(repo, "src", "calc.py")
        test_path = os.path.join(repo, "tests", "test_calc.py")
        with open(calc_path, "w", encoding="utf-8") as fh:
            fh.write("def add(a: int, b: int) -> int:\n    return 0\n")
        with open(test_path, "w", encoding="utf-8") as fh:
            fh.write(
                "import os, sys\n"
                "sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))\n"
                "from src.calc import add\n\n"
                "def test_positive_add():\n    assert add(2, 3) == 5\n"
                "def test_negative_add():\n    assert add(-2, -3) == -5\n"
                "def test_boundary_zero():\n    assert add(0, 0) == 0\n"
                "def test_resilience_idempotent():\n    assert add(1, 2) == add(1, 2)\n"
            )
        _init_git_repo(repo)

        plan_dir = os.path.join(repo, ".synapse", "plans")
        os.makedirs(plan_dir, exist_ok=True)
        plan_path = os.path.join(plan_dir, "calc_upgrade.md")
        with open(plan_path, "w", encoding="utf-8") as fh:
            fh.write(
                "# Spec-Driven Implementation Plan: Calc Upgrade\n\n"
                "## 3. Atomic Milestones (Execution DAG)\n\n"
                "### Milestone 1: Core Calculator\n"
                "- **Node ID:** `M1` | **depends_on:** `[]`\n"
                "- **Write Set:** `['src/calc.py']`\n"
                "- **Rollback Hook:** `git checkout -- src/calc.py`\n"
                f"- **Pass Gate:** `{sys.executable} -m py_compile src/calc.py`\n\n"
                "### Milestone 2: Calculator Verification\n"
                "- **Node ID:** `M2` | **depends_on:** `[M1]`\n"
                "- **Write Set:** `['tests/test_calc.py']`\n"
                "- **Rollback Hook:** `git checkout -- tests/test_calc.py`\n"
                f"- **Pass Gate:** `{sys.executable} -m pytest tests/test_calc.py -q`\n"
            )

        # Agent implements M1 without committing yet, then runs --from-plan
        with open(calc_path, "w", encoding="utf-8") as fh:
            fh.write("def add(a: int, b: int) -> int:\n    return a + b\n")

        summary = execute_plan_via_solo(
            plan_path=plan_path,
            repo_root=repo,
            run_mutation=False,
            run_purple=False,
            auto_review=False,
            sandbox_mode="host",
        )
        self.assertTrue(summary.passed, f"M2 must accept completed M1 files: {summary.to_dict()}")
        self.assertEqual(summary.milestones_passed, 2)
        self.assertIsNone(summary.halted_at_node)
        with open(calc_path, "r", encoding="utf-8") as fh:
            self.assertIn("return a + b", fh.read())

        # Single-milestone filter on M2 also honors ancestor M1's write_set
        m2_only = execute_plan_via_solo(
            plan_path=plan_path,
            repo_root=repo,
            milestone_filter="M2",
            run_mutation=False,
            run_purple=False,
            auto_review=False,
            sandbox_mode="host",
        )
        self.assertTrue(m2_only.passed, f"Filtered M2 should honor ancestor M1 write_set: {m2_only.to_dict()}")

    def test_m1_negative_suffix_boundary_rejects_sibling_file(self) -> None:
        """Negative (TC-02): Scope guard enforces '/' path boundary so 'data.py' never matches declared 'a.py'."""
        from tools.design.dag_self_healer import (
            DAGNode,
            SelfHealingDAGExecutor,
            _path_matches_declared,
        )

        self.assertFalse(_path_matches_declared("data.py", "a.py"))
        self.assertFalse(_path_matches_declared("src/data.py", "a.py"))
        self.assertFalse(_path_matches_declared("", "a.py"))
        self.assertFalse(_path_matches_declared("a.py", ""))
        self.assertFalse(_path_matches_declared("", ""))
        self.assertTrue(_path_matches_declared("src/a.py", "a.py"))
        self.assertTrue(_path_matches_declared("src/a.py", "src/a.py"))

        repo = os.path.join(self.temp_dir, "m1_neg_repo")
        os.makedirs(os.path.join(repo, "src"), exist_ok=True)
        with open(os.path.join(repo, "a.py"), "w", encoding="utf-8") as fh:
            fh.write("x = 1\n")
        with open(os.path.join(repo, "src", "a.py"), "w", encoding="utf-8") as fh:
            fh.write("x = 1\n")
        with open(os.path.join(repo, "data.py"), "w", encoding="utf-8") as fh:
            fh.write("y = 1\n")
        _init_git_repo(repo)

        # Nested src/a.py matches declared basename a.py via '/' boundary
        with open(os.path.join(repo, "src", "a.py"), "w", encoding="utf-8") as fh:
            fh.write("x = 2\n")
        node = DAGNode(node_id="M1", title="Edit a", write_set=["a.py"])
        executor = SelfHealingDAGExecutor(nodes={"M1": node}, repo_root=repo)
        ok_nested, unauth_nested = executor.check_scope_guard_violation(
            node, allowed_extra_files=["   ", ""]
        )
        self.assertTrue(ok_nested, f"src/a.py should match declared a.py: {unauth_nested}")
        self.assertEqual(unauth_nested, [])

        # Sibling data.py must NOT match declared a.py (and whitespace extra must NOT allow it)
        with open(os.path.join(repo, "data.py"), "w", encoding="utf-8") as fh:
            fh.write("y = 2  # unauthorized sibling edit\n")
        ok, unauthorized = executor.check_scope_guard_violation(
            node, allowed_extra_files=["   ", ""]
        )
        self.assertFalse(ok)
        self.assertEqual(unauthorized, ["data.py"])

        # run_dag_live preserves cumulative completed_write_set across pass_gate=None & live pass_gate milestones
        live_repo = os.path.join(self.temp_dir, "m1_live_dag_repo")
        os.makedirs(live_repo, exist_ok=True)
        with open(os.path.join(live_repo, "m1.py"), "w", encoding="utf-8") as fh:
            fh.write("A = 1\n")
        with open(os.path.join(live_repo, "m2.py"), "w", encoding="utf-8") as fh:
            fh.write("B = 1\n")
        _init_git_repo(live_repo)
        with open(os.path.join(live_repo, "m1.py"), "w", encoding="utf-8") as fh:
            fh.write("A = 2\n")

        # Case 1: M1 has pass_gate=None (skipped/dry), M2 has live pass_gate -> M2 must allow M1's write_set
        n1_skip = DAGNode(node_id="M1", title="Prep", write_set=["m1.py"], pass_gate=None)
        n2_live = DAGNode(
            node_id="M2",
            title="Check",
            depends_on=["M1"],
            write_set=["m2.py"],
            pass_gate=f"{sys.executable} -m py_compile m2.py",
        )
        dag_skip = SelfHealingDAGExecutor(nodes={"M1": n1_skip, "M2": n2_live}, repo_root=live_repo)
        res_skip = dag_skip.run_dag_live(dry_run=False, enforce_scope_guard=True)
        self.assertTrue(res_skip["all_success"], f"run_dag_live failed after pass_gate=None M1: {res_skip}")

        # Case 2: Both M1 and M2 have live pass_gate -> M2 must allow M1's write_set
        n1_live = DAGNode(
            node_id="M1",
            title="Compile M1",
            write_set=["m1.py"],
            pass_gate=f"{sys.executable} -m py_compile m1.py",
        )
        n2_live2 = DAGNode(
            node_id="M2",
            title="Compile M2",
            depends_on=["M1"],
            write_set=["m2.py"],
            pass_gate=f"{sys.executable} -m py_compile m2.py",
        )
        dag_live = SelfHealingDAGExecutor(nodes={"M1": n1_live, "M2": n2_live2}, repo_root=live_repo)
        res_live = dag_live.run_dag_live(dry_run=False, enforce_scope_guard=True)
        self.assertTrue(res_live["all_success"], f"run_dag_live failed after live M1: {res_live}")

    def test_m1_boundary_empty_extra_files_and_unauth_preserves_m1(self) -> None:
        """Boundary: Empty allowed_extra_files works; unauthorized edit in M2 rolls back only unauthorized file, keeping M1."""
        from tools.design.dag_self_healer import DAGNode, SelfHealingDAGExecutor
        from tools.orchestration.plan_dag_bridge import execute_plan_via_solo

        repo = os.path.join(self.temp_dir, "m1_bnd_repo")
        os.makedirs(os.path.join(repo, "src"), exist_ok=True)
        os.makedirs(os.path.join(repo, "tests"), exist_ok=True)
        calc_path = os.path.join(repo, "src", "calc.py")
        evil_path = os.path.join(repo, "src", "evil.py")
        test_path = os.path.join(repo, "tests", "test_calc.py")
        with open(calc_path, "w", encoding="utf-8") as fh:
            fh.write("def add(a, b): return a + b\n")
        with open(evil_path, "w", encoding="utf-8") as fh:
            fh.write("SAFE = True\n")
        with open(test_path, "w", encoding="utf-8") as fh:
            fh.write("def test_ok(): assert 1 + 1 == 2\n")
        _init_git_repo(repo)

        node = DAGNode(node_id="M1", title="Calc", write_set=["src/calc.py"])
        ok, unauth = SelfHealingDAGExecutor(repo_root=repo).check_scope_guard_violation(
            node, allowed_extra_files=[]
        )
        self.assertTrue(ok)
        self.assertEqual(unauth, [])

        # Confirm M1 + M2 with unauthorized file fails M1 before touching calc
        plan_path = os.path.join(repo, ".synapse", "plans", "bnd.md")
        os.makedirs(os.path.dirname(plan_path), exist_ok=True)
        with open(plan_path, "w", encoding="utf-8") as fh:
            fh.write(
                "## 3. Atomic Milestones\n\n"
                "### Milestone 1: Calc\n"
                "- **Node ID:** `M1` | **depends_on:** `[]`\n"
                "- **Write Set:** `['src/calc.py']`\n"
                "- **Rollback Hook:** `git checkout -- src/calc.py`\n"
                f"- **Pass Gate:** `{sys.executable} -m py_compile src/calc.py`\n\n"
                "### Milestone 2: Tests\n"
                "- **Node ID:** `M2` | **depends_on:** `[M1]`\n"
                "- **Write Set:** `['tests/test_calc.py']`\n"
                "- **Rollback Hook:** `git checkout -- tests/test_calc.py`\n"
                f"- **Pass Gate:** `{sys.executable} -m pytest tests/test_calc.py -q`\n"
            )
        with open(evil_path, "w", encoding="utf-8") as fh:
            fh.write("SAFE = False\n")
        res = execute_plan_via_solo(
            plan_path=plan_path,
            repo_root=repo,
            run_mutation=False,
            run_purple=False,
            auto_review=False,
            sandbox_mode="host",
        )
        self.assertFalse(res.passed)
        self.assertEqual(res.halted_at_node, "M1")
        with open(evil_path, "r", encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "SAFE = True\n")

    # =========================================================================
    # M2: Grounded Super-Plan Scaffold, Decisions & Boilerplate/Placeholder Gates
    # =========================================================================

    def test_m2_positive_grounded_scaffold_with_decisions_and_tdd_milestones(self) -> None:
        """Positive (TC-03a): Scaffold emits task-specific DTOs, real callers/risk, decisions, TDD order & passes gates."""
        from tools.design.super_plan_engine import (
            PlanningTier,
            check_ambiguities,
            scaffold_super_plan,
        )
        from tools.lint.plan_mutator import run_plan_mutation_audit
        from tools.lint.plan_quality_loss import evaluate_plan_markdown_loss
        from tools.lint.plan_schema_sentinel import validate_plan_content

        # New resilience_retry ambiguity category catches retry/backoff tasks
        qs = check_ambiguities("Add retry with exponential backoff to plan harvester ADR writer")
        cats = {q["category"] for q in qs}
        self.assertIn("resilience_retry", cats)

        # Decisions resolve ambiguity cleanly and appear in plan output
        plan = scaffold_super_plan(
            "Add retry with exponential backoff to plan harvester ADR writer",
            ["tools/design/plan_harvester.py", "tests/test_super_plan_and_harvester.py"],
            tournament=True,
            tier=PlanningTier.TIER_2_DEEP,
            decisions={"resilience_retry": "sync_backoff"},
        )
        # Task-grounded contracts instead of generic boilerplate
        self.assertNotIn("class ExecutionInputDTO", plan)
        self.assertNotIn("def execute_operation(", plan)
        self.assertNotIn('pytest tests/ -k "test_happy_path"', plan)
        self.assertIn("sync_backoff", plan)
        self.assertIn("Files Modified (Max 3)", plan)
        self.assertIn("tests/test_super_plan_and_harvester.py", plan)
        # Regression risk must not blindly hardcode Low for high-fan-in Tier 2
        self.assertNotIn("Regression Risk:** Low", plan)

        # Stop-word filtering avoids matching unrelated 'add_task' for verb 'Add'
        plan_ps = scaffold_super_plan(
            "Add retry backoff to ADR writer",
            ["tools/core/project_state.py"],
            tier=PlanningTier.TIER_1_STANDARD,
        )
        self.assertNotIn("(AST: add_task)", plan_ps)

        # Tier 0 includes ALL target_files (source + test) in Write Set
        tier0 = scaffold_super_plan(
            "Fix minor comment",
            ["tools/core/project_state.py", "tests/test_super_plan_and_harvester.py"],
            tier=PlanningTier.TIER_0_FAST,
        )
        self.assertIn("'tests/test_super_plan_and_harvester.py'", tier0)

        passed, issues, _ = validate_plan_content(plan, mode="super")
        self.assertTrue(passed, f"Grounded scaffold failed validation: {issues}")
        report = run_plan_mutation_audit(plan, threshold=90.0)
        self.assertEqual(report.total_mutants, 12)
        self.assertTrue(report.passed, f"Grounded scaffold failed mutation audit: {report.survived_mutations}")
        loss = evaluate_plan_markdown_loss(plan)
        self.assertEqual(loss.loss, 0.0, f"Unexpected loss gradients: {loss.gradients}")

    def test_m2_negative_sentinel_and_loss_reject_boilerplate_and_placeholders(self) -> None:
        """Negative (TC-03b): Unedited generic boilerplate and <<FILL:...>> placeholders fail lint & quality loss."""
        from tools.lint.plan_quality_loss import evaluate_plan_markdown_loss
        from tools.lint.plan_schema_sentinel import (
            detect_unfilled_placeholders_or_boilerplate,
            validate_plan_content,
        )

        boilerplate_plan = """# Spec-Driven Implementation Plan: Retry ADR Writer
> **Ambiguity Gate Status:** Resolved

## 1. Affected Files & Blast Radius
| Action | File Path & Structural Anchor | Scope |
|---|---|---|
| `[MODIFY]` | `tools/design/plan_harvester.py` (AST: harvest_plan) | Core |

## 2. Data Flow & Interface Signatures
```python
@dataclass(frozen=True)
class ExecutionInputDTO:
    task_id: str

@dataclass(frozen=True)
class ExecutionResultDTO:
    success: bool

def execute_operation(input_data: ExecutionInputDTO) -> ExecutionResultDTO:
    ...
```

## 3. Atomic Milestones (Execution DAG)
### Milestone 1: Impl
- **Node ID:** `M1` | **depends_on:** `[]`
- **Compute Tier:** `[Model: Flash | Thinking: Off]`
- **Write Set:** `['tools/design/plan_harvester.py']`
- **Circuit Breaker:** Max Fix Attempts: 2 | Rollback: `git checkout -- tools/design/plan_harvester.py`
- **Rollback Hook:** `git checkout -- tools/design/plan_harvester.py`
- **Pass Gate:** `python -m pytest tests/test_super_plan_and_harvester.py -q`

## 4. Verification Matrix
| ID | Scenario | Input | Expected | Command |
|---|---|---|---|---|
| **TC-01** | Happy Path | ok | pass | `pytest tests/ -k "test_happy_path"` |
| **TC-02** | Empty | empty | err | `pytest tests/ -k "test_empty_input"` |
| **TC-03** | Timeout | fail | fallback | `pytest tests/ -k "test_timeout_fallback"` |

## 5. Tri-Vulnerability Self-Critique
1. Concurrency race condition idempotent check.
2. Boundary timeout extreme resource guard.
3. Backward compatibility blast radius caller check.
"""
        findings = detect_unfilled_placeholders_or_boilerplate(boilerplate_plan, is_super=True)
        self.assertTrue(any("boilerplate" in f.lower() for f in findings), findings)

        passed, issues, details = validate_plan_content(boilerplate_plan, mode="super")
        self.assertFalse(passed)
        self.assertTrue(any("boilerplate" in iss.lower() for iss in issues), issues)
        self.assertTrue(len(details.get("placeholder_or_boilerplate_issues", [])) >= 1)

        loss = evaluate_plan_markdown_loss(boilerplate_plan)
        self.assertGreater(loss.loss, 0.0)
        bp_grads = [g for g in loss.gradients if g.category == "PLACEHOLDER_OR_BOILERPLATE"]
        self.assertEqual(len(bp_grads), 1)
        self.assertAlmostEqual(bp_grads[0].severity, 0.40, places=2)
        self.assertIn("boilerplate", bp_grads[0].critique.lower())

        # Partial boilerplate (only ExecutionInputDTO without execute_operation/test_happy_path) must NOT false-positive
        partial_ok_plan = boilerplate_plan.replace("def execute_operation", "def run_retry_worker")
        partial_ok_plan = partial_ok_plan.replace("test_happy_path", "test_retry_positive")
        partial_loss = evaluate_plan_markdown_loss(partial_ok_plan)
        self.assertEqual(
            [g for g in partial_loss.gradients if g.category == "PLACEHOLDER_OR_BOILERPLATE"],
            [],
        )

        # Unfilled <<FILL:...>> sentinel also rejected by both sentinel and plan_quality_loss (with accurate line & critique)
        fill_plan = boilerplate_plan.replace("class ExecutionInputDTO", "class RetryInputDTO")
        fill_plan = fill_plan.replace("def execute_operation", "def run_retry")
        fill_plan = fill_plan.replace("test_happy_path", "<<FILL:test_name>>")
        passed_fill, issues_fill, _ = validate_plan_content(fill_plan, mode="super")
        self.assertFalse(passed_fill)
        self.assertTrue(any("placeholder" in iss.lower() or "<<FILL:" in iss for iss in issues_fill), issues_fill)
        fill_loss = evaluate_plan_markdown_loss(fill_plan)
        fill_grads = [g for g in fill_loss.gradients if g.category == "PLACEHOLDER_OR_BOILERPLATE"]
        self.assertEqual(len(fill_grads), 1)
        self.assertIn("Unfilled sentinel placeholder", fill_grads[0].critique)
        self.assertGreater(fill_grads[0].line, 1)

        # Ambiguity Gate Pending User Confirmation emits AMBIGUITY_PENDING gradient with exact line & severity
        pending_amb_plan = partial_ok_plan.replace(
            "> **Ambiguity Gate Status:** Resolved",
            "> **Ambiguity Gate Status:** Pending User Confirmation (1 open fork)",
        )
        amb_loss = evaluate_plan_markdown_loss(pending_amb_plan)
        amb_grads = [g for g in amb_loss.gradients if g.category == "AMBIGUITY_PENDING"]
        self.assertEqual(len(amb_grads), 1)
        self.assertAlmostEqual(amb_grads[0].severity, 0.20, places=2)
        self.assertEqual(amb_grads[0].line, 2)

    def test_m2_boundary_tournament_no_unconditional_tier2_bias_and_cli_decisions(self) -> None:
        """Boundary & CLI (TC-03c): Tournament is not unconditionally biased to Branch B on Tier 2; CLI accepts --decisions."""
        from tools.design.super_plan_engine import (
            PlanningTier,
            RiskMetricDTO,
            evaluate_orthogonal_tournament,
        )

        # Tier 2 perf-focused task without cross_boundary/arch_hits can select Branch C
        perf_deep_metric = RiskMetricDTO(
            fan_in=8, cross_boundary=False, state_mutation=False, history_drift=0.10
        )
        res = evaluate_orthogonal_tournament(
            "Optimize async cache latency and throughput batch pipeline",
            perf_deep_metric,
            PlanningTier.TIER_2_DEEP,
        )
        self.assertEqual(res["selected_branch"], "Branch C: High Performance")

        # CLI scaffold --decisions embeds confirmed decision and resolves ambiguity
        proc = subprocess.run(
            [
                sys.executable,
                "tools/design/super_plan_engine.py",
                "scaffold",
                "--task",
                "Add a cache layer for call graph",
                "--files",
                "tools/design/super_plan_engine.py",
                "--decisions",
                "storage=in_memory",
                "--json",
            ],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertIn("in_memory", payload["plan_markdown"])
        self.assertIn("Ambiguity Gate Status:** Resolved", payload["plan_markdown"])

    # =========================================================================
    # M3: /review Layer 3 Dir -k, Cross-Drive Safety, Baseline, --no-receipt, Slug Receipts
    # =========================================================================

    def test_m3_positive_and_negative_review_dir_k_and_unverifiable_row(self) -> None:
        """Positive & Negative (TC-04a): Layer 3 audits directory-scoped `pytest tests/ -k` and flags unverifiable TC rows."""
        from tools.orchestration.plan_review_auditor import audit_plan_and_solo_execution

        repo = os.path.join(self.temp_dir, "m3_matrix_repo")
        os.makedirs(os.path.join(repo, "src"), exist_ok=True)
        os.makedirs(os.path.join(repo, "tests"), exist_ok=True)
        with open(os.path.join(repo, "src", "retry.py"), "w", encoding="utf-8") as fh:
            fh.write("def run_retry(attempts: int) -> bool:\n    return attempts > 0\n")
        with open(os.path.join(repo, "tests", "test_retry.py"), "w", encoding="utf-8") as fh:
            fh.write(
                "from src.retry import run_retry\n\n"
                "def test_retry_ok():\n    assert run_retry(2) is True\n"
                "def test_retry_taut():\n    assert True\n"
            )
        _init_git_repo(repo)

        plan_path = os.path.join(repo, "plan.md")
        with open(plan_path, "w", encoding="utf-8") as fh:
            fh.write(
                "# Plan\n"
                "## 1. Affected Files\n"
                "| Action | File | Scope |\n|---|---|---|\n"
                "| `[MODIFY]` | `src/retry.py` (AST: run_retry) | Retry |\n"
                "| `[MODIFY]` | `tests/test_retry.py` (AST: test_retry_ok) | Tests |\n\n"
                "## 2. Data Flow\n```python\ndef run_retry(attempts: int) -> bool:\n    ...\n```\n\n"
                "## 3. Atomic Milestones\n### Milestone 1: Retry\n"
                "- **Node ID:** `M1` | **depends_on:** `[]`\n"
                "- **Write Set:** `['src/retry.py', 'tests/test_retry.py']`\n\n"
                "## 4. Verification Matrix\n"
                "| ID | Scenario | Input | Expected | Command |\n|---|---|---|---|---|\n"
                '| **TC-01** | Existing dir -k | ok | pass | `pytest tests/ -k "test_retry_ok"` |\n'
                '| **TC-02** | Missing dir -k | none | fail | `pytest tests/ -k "test_ghost_nonexistent"` |\n'
                '| **TC-03** | Tautological dir -k | taut | fail | `pytest tests/ -k "test_retry_taut"` |\n'
                "| **TC-04** | Unverifiable row | manual | check | `echo manual ok` |\n"
            )

        plan_dto, _, _, findings = audit_plan_and_solo_execution(
            repo_root=repo,
            changed_files=["src/retry.py", "tests/test_retry.py"],
            diff_text="",
            plan_path=plan_path,
            strict_solo=False,
        )
        self.assertIsNotNone(plan_dto)
        codes = [f["code"] for f in findings]
        titles = " | ".join(f["title"] for f in findings)
        self.assertIn("UNVERIFIED_MATRIX_SCENARIOS", codes)
        self.assertIn("test_ghost_nonexistent", titles)
        self.assertIn("test_retry_taut", titles)
        self.assertIn("UNVERIFIABLE_MATRIX_ROW", codes)
        self.assertNotIn("test_retry_ok", titles)

    def test_m3_boundary_cross_drive_safe_relpath_baseline_no_receipt_and_slug(self) -> None:
        """Boundary & CLI (TC-04b): _safe_relpath survives ValueError, --baseline-files filters dirty files, --no-receipt writes zero files, plan_slug scopes Red receipts."""
        from unittest.mock import patch
        from tools.orchestration.plan_review_auditor import _safe_relpath
        from tools.orchestration.senior_code_review import evaluate_review
        from tools.orchestration.solo_contracts import resolve_red_receipt_path

        # 1. Cross-drive safe relpath fallback (simulates C: vs D: on Windows)
        with patch("os.path.relpath", side_effect=ValueError("path is on mount 'C:', start on mount 'D:'")):
            res_rel = _safe_relpath(r"C:\tmp\plan.md", r"D:\Synapse Hub")
            self.assertIn("plan.md", res_rel)
            self.assertNotIn("\\", res_rel)

        # 2. Plan-slug-scoped Red receipt path + end-to-end solo_runner -> plan_dag_bridge -> plan_review_auditor wiring
        from tools.orchestration.plan_dag_bridge import execute_plan_via_solo
        from tools.orchestration.plan_review_auditor import audit_plan_and_solo_execution
        from tools.orchestration.solo_runner import certify_red_phase

        legacy_p = resolve_red_receipt_path(self.temp_dir, milestone_id="M1")
        slugged_p = resolve_red_receipt_path(self.temp_dir, milestone_id="M1", plan_slug="oauth-login")
        self.assertTrue(legacy_p.replace("\\", "/").endswith("reports/solo_receipts/M1_red.json"))
        self.assertTrue(slugged_p.replace("\\", "/").endswith("reports/solo_receipts/oauth-login__M1_red.json"))

        slug_repo = os.path.join(self.temp_dir, "m3_slug_e2e")
        os.makedirs(os.path.join(slug_repo, "src"), exist_ok=True)
        os.makedirs(os.path.join(slug_repo, "tests"), exist_ok=True)
        with open(os.path.join(slug_repo, "src", "auth.py"), "w", encoding="utf-8") as fh:
            fh.write("def login(user: str) -> bool:\n    return False\n")
        with open(os.path.join(slug_repo, "tests", "test_auth.py"), "w", encoding="utf-8") as fh:
            fh.write(
                "import os, sys\n"
                "sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))\n"
                "from src.auth import login\n\n"
                "def test_positive_login():\n    assert login('alice') is True\n"
            )
        _init_git_repo(slug_repo)
        red_res = certify_red_phase(
            test_cmd=f"{sys.executable} -m pytest tests/test_auth.py -q",
            cwd=slug_repo,
            milestone_id="M1",
            plan_slug="oauth-login",
        )
        self.assertTrue(red_res["passed"], red_res)
        self.assertTrue(
            os.path.isfile(os.path.join(slug_repo, "reports", "solo_receipts", "oauth-login__M1_red.json"))
        )
        # Implement fix so M1 turns green
        with open(os.path.join(slug_repo, "src", "auth.py"), "w", encoding="utf-8") as fh:
            fh.write("def login(user: str) -> bool:\n    return bool(user)\n")
        slug_plan = os.path.join(slug_repo, ".synapse", "plans", "oauth-login.md")
        os.makedirs(os.path.dirname(slug_plan), exist_ok=True)
        with open(slug_plan, "w", encoding="utf-8") as fh:
            fh.write(
                "# Plan\n## 1. Affected Files\n| Action | File | Scope |\n|---|---|---|\n"
                "| `[MODIFY]` | `src/auth.py` (AST: login) | Auth |\n"
                "| `[MODIFY]` | `tests/test_auth.py` (AST: test_positive_login) | Tests |\n"
                "## 2. Data Flow\n```python\ndef login(user: str) -> bool:\n    ...\n```\n"
                "## 3. Atomic Milestones\n### Milestone 1: Auth\n"
                "- **Node ID:** `M1` | **depends_on:** `[]`\n"
                "- **Write Set:** `['src/auth.py', 'tests/test_auth.py']`\n"
                "- **Rollback Hook:** `git checkout -- src/auth.py tests/test_auth.py`\n"
                f"- **Pass Gate:** `{sys.executable} -m pytest tests/test_auth.py -q`\n"
                "## 4. Verification Matrix\n"
            )
        slug_summary = execute_plan_via_solo(
            plan_path=slug_plan,
            repo_root=slug_repo,
            strict_red=True,
            run_mutation=False,
            run_purple=False,
            auto_review=False,
            sandbox_mode="host",
        )
        self.assertTrue(slug_summary.passed, slug_summary.to_dict())
        _, solo_dto, _, _ = audit_plan_and_solo_execution(
            repo_root=slug_repo,
            changed_files=["src/auth.py"],
            diff_text="",
            plan_path=slug_plan,
            milestone_id="M1",
            strict_solo=False,
        )
        self.assertIsNotNone(solo_dto)
        assert solo_dto is not None
        self.assertTrue(any("oauth-login__M1_red.json" in p for p in solo_dto.valid_red_receipts))

        # 3. Baseline dirty-file filtering + --no-receipt zero-write diagnostic
        repo = os.path.join(self.temp_dir, "m3_baseline_repo")
        os.makedirs(os.path.join(repo, "src"), exist_ok=True)
        with open(os.path.join(repo, "src", "planned.py"), "w", encoding="utf-8") as fh:
            fh.write("def greet(name: str) -> str:\n    return name\n")
        with open(os.path.join(repo, "src", "dirty_unrelated.py"), "w", encoding="utf-8") as fh:
            fh.write("VAL = 1\n")
        _init_git_repo(repo)

        with open(os.path.join(repo, "src", "planned.py"), "w", encoding="utf-8") as fh:
            fh.write("def greet(name: str) -> str:\n    return f'hi {name}'\n")
        with open(os.path.join(repo, "src", "dirty_unrelated.py"), "w", encoding="utf-8") as fh:
            fh.write("VAL = 2\n")

        plan_path = os.path.join(repo, ".synapse", "plans", "greet.md")
        os.makedirs(os.path.dirname(plan_path), exist_ok=True)
        with open(plan_path, "w", encoding="utf-8") as fh:
            fh.write(
                "# Plan\n## 1. Affected Files\n"
                "| Action | File | Scope |\n|---|---|---|\n"
                "| `[MODIFY]` | `src/planned.py` (AST: greet) | Greet |\n"
                "## 2. Data Flow\n```python\ndef greet(name: str) -> str:\n    ...\n```\n"
                "## 3. Atomic Milestones\n### Milestone 1: Greet\n"
                "- **Node ID:** `M1` | **depends_on:** `[]`\n"
                "- **Write Set:** `['src/planned.py']`\n"
                "## 4. Verification Matrix\n"
            )

        exit_code, payload, _, receipt = evaluate_review(
            repo_dir=repo,
            target="uncommitted",
            plan_path=plan_path,
            baseline_files=["src/dirty_unrelated.py"],
            write_receipt=False,
        )
        self.assertEqual(exit_code, 0, payload)
        self.assertEqual(list(payload["plan_reconciliation"]["unplanned_modified_files"]), [])
        self.assertIsNone(receipt)
        self.assertFalse(os.path.exists(os.path.join(repo, "reports", "code_review_receipt.json")))

        # 4. CLI --baseline-files and --no-receipt flags work cleanly
        proc = subprocess.run(
            [
                sys.executable,
                "tools/orchestration/senior_code_review.py",
                repo,
                "--plan",
                plan_path,
                "--baseline-files",
                "src/dirty_unrelated.py",
                "--no-receipt",
                "--json",
            ],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        cli_data = json.loads(proc.stdout)
        self.assertEqual(cli_data["verdict"], "APPROVED")
        self.assertFalse(os.path.exists(os.path.join(repo, "reports", "code_review_receipt.json")))


if __name__ == "__main__":
    unittest.main()
