#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tests/test_super_plan_10_blueprint.py — Test Battery for Super-Plan 10.0 Architecture
--------------------------------------------------------------------------------------
Validates the 4 Breakthrough Pillars:
  1. Risk-Routing (Tier 0 Fast-Track vs Tier 1 Standard vs Tier 2 Deep-Track).
  2. AST Structural Anchors & Parallel Collision Guard in Plan Schema Sentinel.
  3. Plan Mutation Testing Sentinel (Plan Kill Score >= 90%).
  4. Self-Healing DAG Execution (Forensic Snapshot, Compensating Rollback, Cascading Cancellation, JIT Read).
  5. Semantic Contract Drift in Plan Harvester.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.design.super_plan_engine import (
    calculate_risk_routing, PlanningTier, check_ambiguities, scaffold_super_plan
)
from tools.lint.plan_schema_sentinel import (
    validate_plan_content,
    rollback_path_scoped,
)
from tools.lint.plan_mutator import run_plan_mutation_audit
from tools.design.dag_self_healer import (
    SelfHealingDAGExecutor, DAGNode, NodeStatus, FailureClass
)
from tools.design.plan_harvester import calibrate_plan_against_git


VALID_SUPER_PLAN_10 = """<!--
# Author: Thế Vị (@TeeVee98) | MIT License
-->
# Spec-Driven Implementation Plan: Payment Gateway Redesign

> Reference: standards/qa-process/plan-protocol.md
> Ambiguity Gate Status: Resolved
> 📝 Plan Changelog (v1.0): Initial 10/10 blueprint.

## 1. Affected Files & Blast Radius
| Action | File Path & Structural Anchor | Scope & Responsibility |
|---|---|---|
| `[MODIFY]` | `tools/core/agent_runner.py` (AST: run_command | L10-L45) | Core runner |
| `[CREATE]` | `tests/test_payment_gateway.py` (New) | Payment test suite |

Direct Callers: Runner
Regression Risk: Low

## 2. Data Flow & Interface Signatures
```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ChargeInputDTO:
    tx_id: str
    amount: int
    error_code: Optional[str] = None

def charge(data: ChargeInputDTO) -> bool:
    ...
```

## 3. Atomic Milestones (Execution DAG)
### Milestone 1: Interfaces & Harness [PARALLEL_OK]
- Node ID: `M1` | depends_on: `[]`
- Compute Tier: [Model: Flash | Thinking: Off | Temp: 0.1]
- Files Modified (Max 2): `tools/core/agent_runner.py`
- Write Set: `['tools/core/agent_runner.py']`
- Circuit Breaker: Max Fix Attempts: 2 | Scope Guard: Halt on failure | Rollback: git checkout -- tools/core/agent_runner.py
- Rollback Hook: git checkout -- tools/core/agent_runner.py
- Pass Gate: `pytest tests/test_payment_gateway.py`

### Milestone 2: Caller Integration
- Node ID: `M2` | depends_on: `[M1]`
- Compute Tier: [Model: Pro / Reasoning | Thinking: High | Best-of-3]
- Files Modified (Max 2): `tests/test_payment_gateway.py`
- Write Set: `['tests/test_payment_gateway.py']`
- Circuit Breaker: Max Fix Attempts: 2 | Scope Guard: Halt on failure | Rollback: git checkout -- tests/test_payment_gateway.py
- Rollback Hook: git checkout -- tests/test_payment_gateway.py
- Pass Gate: `pytest tests/test_payment_gateway.py`

## 4. Verification Matrix
| ID | Scenario | Input | Expected Output | Command |
|---|---|---|---|---|
| TC-01 | Happy Path | `ChargeInputDTO(tx_id="1", amount=100)` | `True` | `pytest tests/test_payment_gateway.py` |
| TC-02 | Boundary Empty ID | `ChargeInputDTO(tx_id="", amount=0)` | Handled gracefully without crash | `pytest tests/test_payment_gateway.py` |
| TC-03 | Timeout Error | Gateway times out | Fallback triggered, error_code set | `pytest tests/test_payment_gateway.py` |

## 5. Tri-Vulnerability Self-Critique & Mitigations
1. Concurrency / Race Condition: Idempotency token validation on tx_id.
2. Resource Extremes / Timeout: 5s timeout on payment adapter.
3. Blast Radius / Backward Compatibility: Adapter preserves old signature.

## 6. Rollback & State-Migration Matrix (Zero-Downtime Guard)
| Phase | Trigger Scenario | Mitigation | Rollback Command |
|---|---|---|---|
| State Migration | Failure | Atomic checkpoint with dual-write | `alembic downgrade -1` |
"""


class TestSuperPlan10Blueprint(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # Pillar 1: Risk Router & Anti-Rubber-Stamping Ambiguity Gate
    # -------------------------------------------------------------------------
    def test_risk_router_tier_0_fast_track(self):
        tier, metric = calculate_risk_routing("fix typo in docstring", ["tests/test_isolated_helper.py"])
        self.assertEqual(tier, PlanningTier.TIER_0_FAST)
        self.assertLess(metric.risk_score, 0.35)

    def test_risk_router_tier_2_deep_track(self):
        tier, metric = calculate_risk_routing("migrate db ledger with async auth api", ["tools/core/agent_runner.py"])
        self.assertEqual(tier, PlanningTier.TIER_2_DEEP)
        self.assertGreaterEqual(metric.risk_score, 0.70)
        self.assertTrue(metric.cross_boundary)
        self.assertTrue(metric.state_mutation)

    def test_ambiguity_gate_counter_arguments(self):
        questions = check_ambiguities("thiết kế cache và database")
        self.assertTrue(len(questions) >= 1)
        q = questions[0]
        self.assertIn("counter_arguments", q)
        rec_opt = q["recommended"]
        self.assertIn(rec_opt, q["counter_arguments"])
        self.assertTrue(len(q["counter_arguments"][rec_opt]) > 10)

    def test_scaffold_auto_routes_tier_0_micro_plan(self):
        micro_plan = scaffold_super_plan("fix typo in test helper", ["tests/test_typo_helper.py"])
        self.assertIn("# Fast-Track Micro-Plan", micro_plan)
        self.assertNotIn("Orthogonal Architectural Tournament", micro_plan)
        passed, issues, details = validate_plan_content(micro_plan, mode="standard")
        self.assertTrue(passed, f"Fast-track plan failed validation: {issues}")

    def test_scaffold_auto_routes_tier_2_deep_plan(self):
        deep_plan = scaffold_super_plan(
            "migrate db schema ledger and auth api with distributed lock",
            ["tools/core/agent_runner.py", "tests/test_payment_gateway.py"]
        )
        self.assertIn("# Spec-Driven Implementation Plan", deep_plan)
        self.assertIn("Orthogonal Architectural Tournament", deep_plan)
        self.assertIn("Typed Interface Manifest", deep_plan)
        passed, issues, details = validate_plan_content(deep_plan, mode="super")
        self.assertTrue(passed, f"Deep plan failed validation: {issues}")

    # -------------------------------------------------------------------------
    # Pillar 2: AST Structural Anchors & Parallel Collision Guard
    # -------------------------------------------------------------------------
    def test_ast_structural_anchors_accepted(self):
        passed, issues, details = validate_plan_content(VALID_SUPER_PLAN_10, mode="super")
        self.assertTrue(passed, f"Plan with AST Structural Anchors failed: {issues}")
        self.assertGreaterEqual(details["line_anchors_detected"], 1)

    def test_parallel_collision_guard_detects_shared_write_set(self):
        colliding_plan = VALID_SUPER_PLAN_10.replace(
            "### Milestone 2: Caller Integration",
            "### Milestone 2: Caller Integration [PARALLEL_OK]"
        ).replace(
            "`[M1]`",
            "`[]`"
        ).replace(
            "Write Set: `['tests/test_payment_gateway.py']`",
            "Write Set: `['tools/core/agent_runner.py']`"  # Collides with M1!
        )
        passed, issues, _ = validate_plan_content(colliding_plan, mode="super")
        self.assertFalse(passed)
        self.assertTrue(any("Parallel Collision detected" in iss for iss in issues))

    def test_formal_contract_verification_detects_disconnect(self):
        plan_with_manifest = VALID_SUPER_PLAN_10.replace(
            "Write Set: `['tools/core/agent_runner.py']`",
            "Write Set: `['tools/core/agent_runner.py']`\n- Typed Interface Manifest:\n  - consumes: `[]`\n  - produces: `[{\"contract\": \"ExistingDTO\"}]`"
        ).replace(
            "Write Set: `['tests/test_payment_gateway.py']`",
            "Write Set: `['tests/test_payment_gateway.py']`\n- Typed Interface Manifest:\n  - consumes: `[{\"contract\": \"MissingUnproducedDTO\"}]`\n  - produces: `[]`"
        )
        passed, issues, _ = validate_plan_content(plan_with_manifest, mode="super")
        self.assertFalse(passed)
        self.assertTrue(any("Contract Disconnect" in iss for iss in issues))
        self.assertTrue(any("MissingUnproducedDTO" in iss for iss in issues))

    # -------------------------------------------------------------------------
    # Pillar 3: Plan Mutation Testing Sentinel (Plan Kill Score >= 90%)
    # -------------------------------------------------------------------------
    def test_plan_mutation_passes_compliant_plan(self):
        report = run_plan_mutation_audit(VALID_SUPER_PLAN_10, threshold=90.0)
        self.assertTrue(report.passed)
        self.assertEqual(report.kill_score, 100.0)
        self.assertEqual(len(report.survived_mutations), 0)

    def test_plan_mutation_survives_when_boundary_fallback_missing(self):
        flawed_plan = VALID_SUPER_PLAN_10.replace("TC-02", "TC-02-Unused").replace("TC-03", "TC-03-Unused")
        flawed_plan = flawed_plan.replace("gracefully", "normal").replace("Timeout Error", "Normal Flow")
        flawed_plan = flawed_plan.replace("Fallback", "Normal").replace("Optional", "str")
        report = run_plan_mutation_audit(flawed_plan, threshold=90.0)
        # Should detect survived mutant 1
        self.assertIn("Mutant 1: Contract Field Drop / Type Widening", report.details)

    # -------------------------------------------------------------------------
    # Pillar 4: Self-Healing DAG Execution & Compensating Rollback
    # -------------------------------------------------------------------------
    def test_dag_self_healing_execution(self):
        executor = SelfHealingDAGExecutor()
        node_a = DAGNode(node_id="A", depends_on=[], write_set=["a.py"], shared_assumptions=["v1"])
        node_b = DAGNode(node_id="B", depends_on=["A"], write_set=["b.py"], shared_assumptions=["v1"])
        node_c = DAGNode(node_id="C", depends_on=["B"], write_set=["c.py"])
        executor.add_node(node_a)
        executor.add_node(node_b)
        executor.add_node(node_c)

        node_a.status = NodeStatus.SUCCESS
        trace = 'File "b.py", line 12, in process\nInterface Mismatch: Method signature changed'
        snapshot = executor.capture_failure_snapshot(node_b, "diff_b", trace)

        self.assertEqual(snapshot.failure_class, FailureClass.ARCHITECTURAL_VIOLATION)
        self.assertEqual(snapshot.node_id, "B")

        rollback_res = executor.safe_rollback(node_b)
        self.assertTrue(rollback_res["git_revert_run"])

        cancelled = executor.cancel_descendants_and_siblings(node_b)
        self.assertIn("C", cancelled)

        deep_context = executor.read_full_bodies_jit(snapshot.involved_symbols, max_files=2)
        replanned = executor.replan_subgraph(node_b, cancelled, deep_context, snapshot)

        self.assertEqual(len(replanned), 1)
        self.assertEqual(replanned[0].node_id, "B_reanchored")
        # Check node C now depends on B_reanchored
        self.assertIn("B_reanchored", executor.nodes["C"].depends_on)
        self.assertEqual(executor.nodes["C"].status, NodeStatus.PENDING)

    # -------------------------------------------------------------------------
    # Pillar 5: Semantic Contract Drift in Plan Harvester
    # -------------------------------------------------------------------------
    def test_semantic_contract_drift_detection(self):
        calib = calibrate_plan_against_git(VALID_SUPER_PLAN_10)
        self.assertIn("semantic_drift_ratio", calib)
        self.assertIn("semantic_accuracy_score", calib)
        self.assertIn("composite_accuracy_score", calib)
        self.assertIsInstance(calib["semantic_accuracy_score"], float)

    # -------------------------------------------------------------------------
    # M1 (P0.1): Physical Transactional safe_rollback & Fail-Closed Scope Guard
    # -------------------------------------------------------------------------
    def _init_temp_git_repo(self):
        repo_dir = tempfile.mkdtemp(dir=self.temp_dir)
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, capture_output=True, check=True)
        return repo_dir

    @staticmethod
    def _sha256_file(path: str) -> str:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()

    def test_m1_positive_physical_safe_rollback_restores_write_set_and_runs_hook(self):
        """TC-01 (Positive): Physical safe_rollback restores tracked file, removes created file, runs hook, preserves out-of-scope file."""
        repo_dir = self._init_temp_git_repo()
        tracked = os.path.join(repo_dir, "tracked.py")
        unrelated = os.path.join(repo_dir, "unrelated.py")
        with open(tracked, "w", encoding="utf-8") as fh:
            fh.write("VALUE = 1\n")
        with open(unrelated, "w", encoding="utf-8") as fh:
            fh.write("KEEP = 'base'\n")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "baseline"], cwd=repo_dir, capture_output=True, check=True)

        baseline_hash = self._sha256_file(tracked)

        # Mutate tracked file, create untracked file in write_set, and mutate unrelated out-of-scope file
        with open(tracked, "w", encoding="utf-8") as fh:
            fh.write("VALUE = 999\n")
        mutated_hash = self._sha256_file(tracked)
        self.assertNotEqual(baseline_hash, mutated_hash)

        created = os.path.join(repo_dir, "created_in_scope.py")
        with open(created, "w", encoding="utf-8") as fh:
            fh.write("TEMP = True\n")
        created_hash = self._sha256_file(created)

        with open(unrelated, "w", encoding="utf-8") as fh:
            fh.write("KEEP = 'modified_out_of_scope'\n")
        unrelated_modified_hash = self._sha256_file(unrelated)

        marker_path = os.path.join(repo_dir, "hook_ran.marker")
        hook_cmd = f"{sys.executable} -c \"open(r'{marker_path}', 'w', encoding='utf-8').write('ok')\""

        executor = SelfHealingDAGExecutor(repo_root=repo_dir)
        node = DAGNode(
            node_id="M1_tx",
            write_set=["tracked.py", "created_in_scope.py"],
            rollback_hook=hook_cmd,
        )
        res = executor.safe_rollback(node, run_compensating_tx=True)

        # Verify physical compensating hook actually executed
        self.assertTrue(res["compensating_hook_run"])
        self.assertEqual(res["compensating_hook_exit_code"], 0)
        self.assertTrue(os.path.isfile(marker_path))

        # Verify physical file restoration & hashes
        self.assertTrue(res["git_revert_run"])
        self.assertTrue(res["verified_clean"], f"Unexpected rollback errors: {res.get('errors')}")
        self.assertEqual(res["errors"], [])
        self.assertEqual(self._sha256_file(tracked), baseline_hash)
        self.assertFalse(os.path.exists(created))
        self.assertIn("tracked.py", res["reverted_files"])
        self.assertIn("created_in_scope.py", res["removed_created_files"])
        self.assertEqual(res["pre_hashes"]["tracked.py"], mutated_hash)
        self.assertEqual(res["post_hashes"]["tracked.py"], baseline_hash)
        self.assertEqual(res["pre_hashes"]["created_in_scope.py"], created_hash)

        # Verify out-of-scope file was NOT touched
        self.assertEqual(self._sha256_file(unrelated), unrelated_modified_hash)
        self.assertEqual(node.status, NodeStatus.FAILED)

    def test_m1_negative_scope_guard_fail_closed_on_exception_and_git_error(self):
        """TC-02 (Negative): check_scope_guard_violation fails closed on git errors, exceptions, and invalid write_set."""
        executor = SelfHealingDAGExecutor(repo_root=self.temp_dir)
        node = DAGNode(node_id="M1_err", write_set=["allowed.py"])

        # Non-git directory -> non-zero git exit code must fail closed
        is_valid, reasons = executor.check_scope_guard_violation(node)
        self.assertFalse(is_valid)
        self.assertTrue(any(r.startswith("SCOPE_GUARD_UNVERIFIABLE:") for r in reasons), f"Got: {reasons}")

        # Subprocess exception must fail closed
        with patch("tools.design.dag_self_healer.subprocess.run", side_effect=OSError("git binary missing")):
            is_valid_exc, reasons_exc = executor.check_scope_guard_violation(node)
        self.assertFalse(is_valid_exc)
        self.assertTrue(any("SCOPE_GUARD_UNVERIFIABLE:" in r and "OSError" in r for r in reasons_exc))

        # Unreadable/invalid write_set must fail closed
        bad_node = DAGNode(node_id="M1_bad", write_set=None)  # type: ignore[arg-type]
        is_valid_bad, reasons_bad = executor.check_scope_guard_violation(bad_node)
        self.assertFalse(is_valid_bad)
        self.assertTrue(any("SCOPE_GUARD_UNVERIFIABLE:" in r for r in reasons_bad))

    def test_m1_negative_compensating_hook_failure_and_timeout(self):
        """Negative: Unsafe, failing, and timed-out compensating hooks mark verified_clean=False with captured evidence."""
        repo_dir = self._init_temp_git_repo()
        f_tracked = os.path.join(repo_dir, "a.py")
        with open(f_tracked, "w", encoding="utf-8") as fh:
            fh.write("X = 1\n")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, capture_output=True, check=True)

        executor = SelfHealingDAGExecutor(repo_root=repo_dir)

        # 1. Unsafe hook rejected
        node_unsafe = DAGNode(node_id="M_unsafe", write_set=["a.py"], rollback_hook="git reset --hard HEAD")
        res_unsafe = executor.safe_rollback(node_unsafe, run_compensating_tx=True)
        self.assertFalse(res_unsafe["compensating_hook_run"])
        self.assertIsNone(res_unsafe["compensating_hook_exit_code"])
        self.assertFalse(res_unsafe["verified_clean"])
        self.assertTrue(len(res_unsafe["errors"]) >= 1)

        # 2. Failing hook captures non-zero exit code
        node_fail = DAGNode(
            node_id="M_fail",
            write_set=["a.py"],
            rollback_hook=f"{sys.executable} -c \"import sys; sys.exit(7)\"",
        )
        res_fail = executor.safe_rollback(node_fail, run_compensating_tx=True)
        self.assertTrue(res_fail["compensating_hook_run"])
        self.assertEqual(res_fail["compensating_hook_exit_code"], 7)
        self.assertFalse(res_fail["verified_clean"])

        # 3. Timed-out hook returns 124 and marks verified_clean=False
        node_timeout = DAGNode(
            node_id="M_timeout",
            write_set=["a.py"],
            rollback_hook=f"{sys.executable} -c \"print('slow')\"",
        )
        real_run = subprocess.run

        def _timeout_only_for_hook(cmd, *args, **kwargs):
            if isinstance(cmd, list) and cmd and cmd[0] == sys.executable:
                raise subprocess.TimeoutExpired(cmd=cmd, timeout=0.1)
            return real_run(cmd, *args, **kwargs)

        with patch("tools.design.dag_self_healer.subprocess.run", side_effect=_timeout_only_for_hook):
            res_to = executor.safe_rollback(node_timeout, run_compensating_tx=True)
        self.assertTrue(res_to["compensating_hook_run"])
        self.assertEqual(res_to["compensating_hook_exit_code"], 124)
        self.assertFalse(res_to["verified_clean"])
        self.assertTrue(any("timed out" in e.lower() for e in res_to["errors"]))

    def test_m1_boundary_path_traversal_refused_and_idempotent_rollback(self):
        """Boundary & Idempotency: Path traversal outside repo_root is blocked; repeated safe_rollback is idempotent."""
        repo_dir = self._init_temp_git_repo()
        outside_file = os.path.join(self.temp_dir, "outside_secret.txt")
        with open(outside_file, "w", encoding="utf-8") as fh:
            fh.write("DO_NOT_DELETE")

        success, msg = rollback_path_scoped(
            created_files=["../outside_secret.txt"],
            repo_root=repo_dir,
        )
        self.assertFalse(success)
        self.assertIn("outside", msg.lower())
        self.assertTrue(os.path.isfile(outside_file))

        # Idempotent double rollback on clean tracked file
        tracked = os.path.join(repo_dir, "idem.py")
        with open(tracked, "w", encoding="utf-8") as fh:
            fh.write("OK = 1\n")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, capture_output=True, check=True)
        base_hash = self._sha256_file(tracked)

        with open(tracked, "w", encoding="utf-8") as fh:
            fh.write("OK = 2\n")

        executor = SelfHealingDAGExecutor(repo_root=repo_dir)
        node = DAGNode(node_id="M_idem", write_set=["idem.py"])
        r1 = executor.safe_rollback(node)
        r2 = executor.safe_rollback(node)
        self.assertTrue(r1["verified_clean"])
        self.assertTrue(r2["verified_clean"])
        self.assertEqual(self._sha256_file(tracked), base_hash)


if __name__ == "__main__":
    unittest.main()
