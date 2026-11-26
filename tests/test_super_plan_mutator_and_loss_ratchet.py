#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tests/test_super_plan_mutator_and_loss_ratchet.py
-------------------------------------------------
4-Scenario verification suite for M1 & M2:
  - Non-vacuous 12-mutant plan mutation auditing & applicable_mutants denominator
  - Untyped `: Any` DTO contract-widening detection in plan_schema_sentinel
  - Markdown plan-domain loss engine (tools/lint/plan_quality_loss.py)
  - Grounded super_plan_engine coupling_memory risk routing, negation-aware ambiguity gate,
    and N-file TDD milestone scaffolding (expanded in M2)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from tools.lint.plan_mutator import (
    mutant_parallel_writeset_collision,
    mutant_type_widening,
    run_plan_mutation_audit,
)
from tools.lint.plan_quality_loss import (
    PlanQualityGradientDTO,
    PlanQualityLossDTO,
    evaluate_plan_markdown_loss,
)
from tools.lint.plan_schema_sentinel import validate_plan_content


FULL_SUPER_PLAN_FIXTURE = """<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Spec-Driven Implementation Plan: Order Pipeline Ratchet

> **Reference Protocol:** [AGENTS.md §5](AGENTS.md)
> **Ambiguity Gate Status:** Resolved
> **Execution Mode:** Single-Agent Sequential (`/solo`)

## 1. Affected Files & Blast Radius
| Action | File Path & Structural Anchor | Scope & Responsibility |
|---|---|---|
| `[MODIFY]` | `tools/lint/plan_schema_sentinel.py` (AST: validate_plan_content) | Schema enforcement |
| `[CREATE]` | `tests/test_order_pipeline_ratchet.py` (New) | Verification suite |

## 2. Data Flow & Interface Signatures
```python
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass(frozen=True)
class OrderPayloadDTO:
    order_id: str
    amount: float
    metadata: Dict[str, str]
    notes: Optional[str] = None

def validate_order(payload: OrderPayloadDTO) -> bool:
    ...
```

## 3. Atomic Milestones (Execution DAG)
### Milestone 1: Contract Lock & Sentinel Update
- **Node ID:** `M1` | **depends_on:** `[]`
- **Compute Tier:** `[Model: Pro / Reasoning | Thinking: High | Best-of-3]`
- **Files Modified (Max 2):** `tools/lint/plan_schema_sentinel.py`
- **Write Set:** `['tools/lint/plan_schema_sentinel.py']`
- **Typed Interface Manifest:**
  - **consumes:** `[]`
  - **produces:** `[{'contract': 'OrderPayloadDTO', 'fields': {'order_id': 'str'}}]`
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt on out-of-scope edits | Rollback: `git checkout -- tools/lint/plan_schema_sentinel.py`
- **Rollback Hook:** `git checkout -- tools/lint/plan_schema_sentinel.py`
- **Pass Gate:** `python3 -m pytest tests/test_plan_schema_sentinel.py -q`

### Milestone 2: Verification Suite
- **Node ID:** `M2` | **depends_on:** `[M1]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 2):** `tests/test_order_pipeline_ratchet.py`
- **Write Set:** `['tests/test_order_pipeline_ratchet.py']`
- **Typed Interface Manifest:**
  - **consumes:** `[{'contract': 'OrderPayloadDTO'}]`
  - **produces:** `[{'contract': 'OrderVerificationReceiptDTO', 'fields': {'passed': 'bool'}}]`
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt on failure | Rollback: `git checkout -- tests/test_order_pipeline_ratchet.py`
- **Rollback Hook:** `git checkout -- tests/test_order_pipeline_ratchet.py`
- **Pass Gate:** `python3 -m pytest tests/test_order_pipeline_ratchet.py -q`

## 4. Verification Matrix
| ID | Scenario | Input | Expected Output | Verification Command |
|---|---|---|---|---|
| TC-01 | Positive | Valid OrderPayloadDTO | Returns True | `pytest tests/test_order_pipeline_ratchet.py` |
| TC-02 | Boundary | Empty order_id | Raises ValueError | `pytest tests/test_order_pipeline_ratchet.py` |
| TC-03 | Timeout | Downstream timeout | Fallback triggered | `pytest tests/test_order_pipeline_ratchet.py` |

## 5. Tri-Vulnerability Self-Critique & Mitigations
1. Concurrency / Race Condition: Idempotent lock on order_id; never use time.sleep() or waitForTimeout() in tests.
2. Resource Extremes / Boundary / Timeout: Bounded 5s timeout guard.
3. Blast Radius / Backward Compatibility: Preserves existing call signatures.
"""


class TestSuperPlanMutatorAndLossRatchet(unittest.TestCase):
    """4-Scenario test battery for M1 (plan_quality_loss, plan_schema_sentinel, plan_mutator)."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 1. POSITIVE SCENARIOS
    # -------------------------------------------------------------------------
    def test_positive_full_plan_passes_loss_sentinel_and_all_12_mutants(self) -> None:
        from dataclasses import FrozenInstanceError

        loss_dto = evaluate_plan_markdown_loss(FULL_SUPER_PLAN_FIXTURE, filename="full_plan.md")
        self.assertIsInstance(loss_dto, PlanQualityLossDTO)
        self.assertEqual(loss_dto.loss, 0.0)
        self.assertEqual(loss_dto.quality_score, 10.0)
        self.assertTrue(loss_dto.passed)
        self.assertEqual(loss_dto.gradients, ())

        # Verify frozen immutability of DTO contracts
        with self.assertRaises(FrozenInstanceError):
            loss_dto.passed = False  # type: ignore[misc]
        grad = PlanQualityGradientDTO(
            section="2. Data Flow",
            line=10,
            category="CONTRACT_WIDENING",
            severity=0.3,
            critique="c",
            remediation="r",
        )
        with self.assertRaises(FrozenInstanceError):
            grad.severity = 0.0  # type: ignore[misc]

        passed, issues, details = validate_plan_content(FULL_SUPER_PLAN_FIXTURE, mode="super")
        self.assertTrue(passed, f"Expected full super plan to pass, got issues: {issues}")
        self.assertEqual(details.get("type_widening_detected", []), [])

        report = run_plan_mutation_audit(FULL_SUPER_PLAN_FIXTURE, threshold=90.0)
        self.assertTrue(report.passed, f"Survived: {report.survived_mutations}")
        self.assertEqual(report.total_mutants, 12)
        self.assertEqual(report.applicable_mutants, 12)
        self.assertEqual(report.killed_mutants, 12)
        self.assertEqual(report.kill_score, 100.0)

    def test_positive_parameterized_dict_any_allowed_in_section_2(self) -> None:
        plan_with_dict_any = FULL_SUPER_PLAN_FIXTURE.replace(
            "from typing import Dict, List, Optional",
            "from typing import Any, Dict, List, Optional",
        ).replace(
            "metadata: Dict[str, str]",
            "metadata: Dict[str, Any]",
        )
        passed, issues, _ = validate_plan_content(plan_with_dict_any, mode="super")
        self.assertTrue(passed, f"Parameterized Dict[str, Any] should be allowed, got: {issues}")
        loss_dto = evaluate_plan_markdown_loss(plan_with_dict_any)
        self.assertEqual(loss_dto.loss, 0.0)

    # -------------------------------------------------------------------------
    # 2. NEGATIVE SCENARIOS
    # -------------------------------------------------------------------------
    def test_negative_any_widening_and_mutants(self) -> None:
        widened_plan = FULL_SUPER_PLAN_FIXTURE.replace("amount: float", "amount: Any")
        passed, issues, details = validate_plan_content(widened_plan, mode="super")
        self.assertFalse(passed)
        self.assertTrue(
            any("Type Widening" in iss for iss in issues),
            f"Expected Type Widening issue, got: {issues}",
        )
        self.assertIn("amount", details.get("type_widening_detected", []))

        # Mutant 2 must genuinely invoke sentinel and kill widening
        killed, verdict = mutant_type_widening(FULL_SUPER_PLAN_FIXTURE)
        self.assertTrue(killed)
        self.assertIn("KILLED", verdict)

        # Mutant 9 must work generically on arbitrary write-sets without hardcoded filenames
        killed_m9, verdict_m9 = mutant_parallel_writeset_collision(FULL_SUPER_PLAN_FIXTURE)
        self.assertTrue(killed_m9, f"Mutant 9 failed on generic plan: {verdict_m9}")
        self.assertIn("KILLED", verdict_m9)

        # Markdown loss must detect fenced code sleep & widened Any & vague verification
        flawed = (
            FULL_SUPER_PLAN_FIXTURE.replace("amount: float", "amount: Any")
            + "\n```python\ntime.sleep(3)\n```\n"
        )
        loss_dto = evaluate_plan_markdown_loss(flawed, filename="flawed.md")
        self.assertFalse(loss_dto.passed)
        self.assertGreater(loss_dto.loss, 0.0)
        self.assertLess(loss_dto.quality_score, 10.0)
        categories = {g.category for g in loss_dto.gradients}
        self.assertIn("FLAKINESS_INVARIANT", categories)
        self.assertIn("CONTRACT_WIDENING", categories)
        for g in loss_dto.gradients:
            self.assertIsInstance(g, PlanQualityGradientDTO)

    def test_negative_invalid_pass_gate_rejected_in_super_mode(self) -> None:
        bad_gate_plan = FULL_SUPER_PLAN_FIXTURE.replace(
            "`python3 -m pytest tests/test_plan_schema_sentinel.py -q`",
            "TBD manual check",
        )
        passed, issues, _ = validate_plan_content(bad_gate_plan, mode="super")
        self.assertFalse(passed)
        self.assertTrue(
            any("Verification Command" in iss or "Pass Gate" in iss for iss in issues),
            f"Expected invalid Pass Gate rejection, got: {issues}",
        )

    def test_negative_non_applicable_mutants_do_not_earn_free_kills(self) -> None:
        # Remove Typed Interface Manifest (produces/consumes) so Mutants 1 & 7 are NOT_APPLICABLE
        no_contracts = FULL_SUPER_PLAN_FIXTURE.replace(
            "- **Typed Interface Manifest:**\n  - **consumes:** `[]`\n  - **produces:** `[{'contract': 'OrderPayloadDTO', 'fields': {'order_id': 'str'}}]`\n",
            "",
        ).replace(
            "- **Typed Interface Manifest:**\n  - **consumes:** `[{'contract': 'OrderPayloadDTO'}]`\n  - **produces:** `[{'contract': 'OrderVerificationReceiptDTO', 'fields': {'passed': 'bool'}}]`\n",
            "",
        )
        report = run_plan_mutation_audit(no_contracts, threshold=90.0)
        self.assertTrue(report.passed, f"Expected pass on applicable subset, got: {report.survived_mutations}")
        self.assertEqual(report.total_mutants, 12)
        self.assertEqual(report.applicable_mutants, 10)
        self.assertEqual(report.not_applicable_mutants, 2)
        self.assertEqual(report.killed_mutants, 10)
        self.assertEqual(report.kill_score, 100.0)
        self.assertEqual(report.details["Mutant 1: Contract Field Drop"]["status"], "NOT_APPLICABLE")
        self.assertEqual(report.details["Mutant 7: Consumed Contract Tampering"]["status"], "NOT_APPLICABLE")

    # -------------------------------------------------------------------------
    # 3. BOUNDARY SCENARIOS
    # -------------------------------------------------------------------------
    def test_boundary_empty_plan_and_prose_anti_pattern_mentions(self) -> None:
        empty_loss = evaluate_plan_markdown_loss("   \n\t  ", filename="empty.md")
        self.assertEqual(empty_loss.loss, 0.0)
        self.assertEqual(empty_loss.quality_score, 10.0)
        self.assertTrue(empty_loss.passed)

        # Prose mentions of time.sleep / waitForTimeout outside code fences must NOT trigger loss
        prose_plan = (
            "# Plan: Smart Waits\n"
            "Rule: Never use time.sleep(5) or Thread.sleep(100) or waitForTimeout(500) in Playwright.\n"
        )
        prose_loss = evaluate_plan_markdown_loss(prose_plan, filename="prose.md")
        self.assertEqual(prose_loss.loss, 0.0)
        self.assertEqual(prose_loss.quality_score, 10.0)
        self.assertTrue(prose_loss.passed)

        # Two separate short Section 2 code fences (15 lines each) must NOT merge into >25 lines
        body_15 = "\n".join(f"    v_{i} = {i}" for i in range(15))
        two_short_blocks = (
            "## 2. Data Flow & Interface Signatures\n"
            "```python\n"
            "def part_one(x: int) -> int:\n"
            f"{body_15}\n"
            "    return x\n"
            "```\n"
            "Separator prose.\n"
            "```python\n"
            "def part_two(y: int) -> int:\n"
            f"{body_15}\n"
            "    return y\n"
            "```\n"
            "## 5. Notes\n"
            "```python\n"
            "example_outside_sec2: Any = 1\n"
            "```\n"
        )
        short_loss = evaluate_plan_markdown_loss(two_short_blocks, filename="two_short.md")
        self.assertEqual(short_loss.loss, 0.0, f"Unexpected gradients: {short_loss.gradients}")

        # Single >25-line function in Section 2 MUST trigger ANTI_FULL_CODE_VIOLATION
        body_28 = "\n".join(f"    step_{i} = {i}" for i in range(28))
        long_block = (
            "## 2. Data Flow & Interface Signatures\n"
            "```python\n"
            "def bloated_impl(x: int) -> int:\n"
            f"{body_28}\n"
            "    return x\n"
            "```\n"
        )
        long_loss = evaluate_plan_markdown_loss(long_block, filename="bloated.md")
        self.assertFalse(long_loss.passed)
        self.assertTrue(any(g.category == "ANTI_FULL_CODE_VIOLATION" for g in long_loss.gradients))
        self.assertEqual(long_loss.gradients[0].section, "2. Data Flow & Interface Signatures")

        # Vague verification, dangerous rollback, missing verification command, and missing AST anchors
        bad_struct = (
            "## 1. Affected Files & Blast Radius\n"
            "| `[MODIFY]` | `tools/lint/plan_mutator.py` | No anchor |\n"
            "## 3. Atomic Milestones\n"
            "- **Rollback Hook:** `git reset --hard HEAD`\n"
            "## 4. Verification Matrix\n"
            "We will write unit tests later.\n"
        )
        bad_loss = evaluate_plan_markdown_loss(bad_struct, filename="bad_struct.md")
        cats = {g.category for g in bad_loss.gradients}
        self.assertIn("VAGUE_VERIFICATION", cats)
        self.assertIn("DANGEROUS_ROLLBACK", cats)
        self.assertIn("VERIFICATION_MATRIX_GAP", cats)
        self.assertIn("MISSING_AST_ANCHORS", cats)

    # -------------------------------------------------------------------------
    # 4. CLI SCENARIOS
    # -------------------------------------------------------------------------
    def test_cli_plan_quality_loss_json_output(self) -> None:
        plan_file = os.path.join(self.temp_dir, "sample_plan.md")
        with open(plan_file, "w", encoding="utf-8") as fh:
            fh.write(FULL_SUPER_PLAN_FIXTURE)

        proc = subprocess.run(
            [sys.executable, "tools/lint/plan_quality_loss.py", "--file", plan_file, "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, f"CLI failed: {proc.stdout}\n{proc.stderr}")
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["loss"], 0.0)
        self.assertEqual(payload["quality_score"], 10.0)

    # -------------------------------------------------------------------------
    # M2 TESTS: Super-Plan Engine (Coupling Memory, Transitive Fan-In, Negation,
    #           N-file TDD Scaffolding, Plan Loss Calibration & Harvester Drift)
    # -------------------------------------------------------------------------
    def test_boundary_negation_and_markdown_loss(self) -> None:
        """TC-04: Negated ambiguity ('in-memory cache, no redis') and prose anti-pattern loss == 0.0."""
        from tools.design.super_plan_engine import check_ambiguities

        q_mem = check_ambiguities("Build an in-memory cache, no redis")
        storage_q = [q for q in q_mem if q["category"] == "storage"]
        self.assertTrue(storage_q, f"Expected storage question, got: {q_mem}")
        self.assertIn("In-Memory", storage_q[0]["recommended"])
        self.assertTrue(storage_q[0]["resolved_by_invariant"])

        # Negation on the first option ('no in-memory') with positive 'redis' must pick Redis
        q_redis = check_ambiguities("Build cache with redis, no in-memory")
        storage_r = [q for q in q_redis if q["category"] == "storage"]
        self.assertTrue(storage_r)
        self.assertIn("Redis", storage_r[0]["recommended"])
        self.assertTrue(storage_r[0]["resolved_by_invariant"])

        # Negated redis alone without positive match must not recommend redis
        q_no_redis = check_ambiguities("Design cache layer, avoid redis")
        storage_nr = [q for q in q_no_redis if q["category"] == "storage"]
        self.assertTrue(storage_nr)
        self.assertNotIn("Redis", storage_nr[0]["recommended"])

        # Prose mentions of anti-patterns must produce 0.0 plan markdown loss
        prose_doc = (
            "# Spec-Driven Implementation Plan: Smart Wait Hygiene\n"
            "Do not use time.sleep(5) or waitForTimeout(1000) anywhere in test suites.\n"
        )
        loss_dto = evaluate_plan_markdown_loss(prose_doc, filename="smart_waits.md")
        self.assertEqual(loss_dto.loss, 0.0)
        self.assertEqual(loss_dto.quality_score, 10.0)
        self.assertTrue(loss_dto.passed)

    def test_m2_coupling_memory_and_transitive_fan_in_risk_routing(self) -> None:
        """M2 Positive: coupling_memory + 2-hop transitive fan-in + Pre-Plan Model Fit Gate."""
        from tools.design.super_plan_engine import (
            PlanningTier,
            assess_pre_plan_model_fit,
            calculate_risk_routing,
        )

        # Build isolated 3-file chain: leaf_mod.py <- mid_mod.py <- top_caller.py
        with open(os.path.join(self.temp_dir, "leaf_mod.py"), "w", encoding="utf-8") as fh:
            fh.write("def core_fn():\n    return 1\n")
        with open(os.path.join(self.temp_dir, "mid_mod.py"), "w", encoding="utf-8") as fh:
            fh.write("from leaf_mod import core_fn\ndef mid_fn():\n    return core_fn()\n")
        with open(os.path.join(self.temp_dir, "top_caller.py"), "w", encoding="utf-8") as fh:
            fh.write("from mid_mod import mid_fn\ndef run():\n    return mid_fn()\n")

        # Baseline without coupling_memory
        _, metric_base = calculate_risk_routing("update helper", ["leaf_mod.py"], repo_root=self.temp_dir)
        self.assertEqual(metric_base.fan_in, 1)
        self.assertGreaterEqual(metric_base.transitive_fan_in, 1)
        self.assertEqual(metric_base.coupling_memory_penalty, 0.0)

        # Add coupling_memory entry for leaf_mod.py in project_state.json
        with open(os.path.join(self.temp_dir, "project_state.json"), "w", encoding="utf-8") as fh:
            json.dump({"coupling_memory": {"leaf_mod.py": 0.9}}, fh)

        _, metric_coupled = calculate_risk_routing("update helper", ["leaf_mod.py"], repo_root=self.temp_dir)
        self.assertGreater(metric_coupled.coupling_memory_penalty, 0.0)
        self.assertGreater(metric_coupled.blast_radius, metric_base.blast_radius)
        self.assertGreater(metric_coupled.risk_score, metric_base.risk_score)
        self.assertTrue(bool(metric_coupled.recommended_model))

        # Pre-Plan Model Fit Gate checks
        under = assess_pre_plan_model_fit(PlanningTier.TIER_2_DEEP, active_model="Gemini 3.8 Flash")
        self.assertEqual(under["fit_status"], "UNDER_PROVISIONED")
        right = assess_pre_plan_model_fit(PlanningTier.TIER_2_DEEP, active_model="Gemini 4 Neon (High)")
        self.assertEqual(right["fit_status"], "RIGHT_SIZED")
        over = assess_pre_plan_model_fit(PlanningTier.TIER_0_FAST, active_model="Gemini 4 Carbon (High)")
        self.assertEqual(over["fit_status"], "OVER_PROVISIONED")

    def test_m2_scaffold_partitions_all_n_target_files_into_tdd_milestones(self) -> None:
        """M2 Positive: scaffold_super_plan partitions 5 files into ceil(5/2)=3 <=2-file milestones."""
        from tools.design.super_plan_engine import PlanningTier, scaffold_super_plan

        five_files = [
            "tools/lint/plan_quality_loss.py",
            "tools/lint/plan_schema_sentinel.py",
            "tools/lint/plan_mutator.py",
            "tools/design/super_plan_engine.py",
            "tools/design/plan_harvester.py",
        ]
        plan_md = scaffold_super_plan(
            "Upgrade super-plan validation pipeline",
            target_files=five_files,
            tier=PlanningTier.TIER_2_DEEP,
            execution_mode="solo",
        )
        for fp in five_files:
            self.assertIn(fp, plan_md, f"Target file '{fp}' dropped from scaffolded milestones!")
        self.assertIn("### Milestone 1:", plan_md)
        self.assertIn("### Milestone 2:", plan_md)
        self.assertIn("### Milestone 3:", plan_md)
        self.assertIn("Pre-Plan Model Fit Gate", plan_md)

        passed, issues, details = validate_plan_content(plan_md, mode="super")
        self.assertTrue(passed, f"5-file scaffold failed validation: {issues}")
        self.assertEqual(details["dag_nodes"], ["M1", "M2", "M3"])

        report = run_plan_mutation_audit(plan_md, threshold=90.0)
        self.assertTrue(report.passed, f"5-file scaffold failed mutation audit: {report.survived_mutations}")

    def test_m2_calibrate_uses_plan_quality_loss_and_harvester_milestone_drift(self) -> None:
        """M2 Positive: calibrate_and_refine_plan uses plan_quality_loss and harvester tracks milestone_drift."""
        from tools.design.plan_harvester import calibrate_plan_against_git
        from tools.design.super_plan_engine import CalibratedSuperPlanDTO, calibrate_and_refine_plan

        plan_file = os.path.join(self.temp_dir, "calibrated_plan.md")
        with open(plan_file, "w", encoding="utf-8") as fh:
            fh.write(FULL_SUPER_PLAN_FIXTURE)

        res = calibrate_and_refine_plan(plan_file, repo_root=self.temp_dir)
        self.assertEqual(res["status"], "CALIBRATED")
        self.assertEqual(res["loss_engine"], "plan_quality_loss")
        self.assertEqual(res["textgrad_loss"], 0.0)
        self.assertEqual(res["textgrad_quality_score"], 10.0)

        dto = CalibratedSuperPlanDTO(
            plan_path=plan_file,
            risk_score=0.7,
            textgrad_loss=res["textgrad_loss"],
            quality_score=res["textgrad_quality_score"],
            status=res["status"],
        )
        self.assertEqual(dto.textgrad_loss, 0.0)

        calib = calibrate_plan_against_git(FULL_SUPER_PLAN_FIXTURE, repo_root=self.temp_dir)
        self.assertIn("milestone_drift", calib)
        self.assertIn("M1", calib["milestone_drift"])
        self.assertIn("M2", calib["milestone_drift"])


if __name__ == "__main__":
    unittest.main()
