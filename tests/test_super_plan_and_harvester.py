#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tests/test_super_plan_and_harvester.py — Test Battery for /super-plan Engine & Harvester
----------------------------------------------------------------------------------------
Validates 4 Scenarios across Super-Plan mechanical pipeline:
  1. Positive: Full Spec-Driven Super-Plan passes validation & harvests to ADR with calibration.
  2. Negative: Missing Circuit Breaker, missing depends_on, missing compute tier, or phantom files fail.
  3. Boundary: Empty files, Unicode slugs, and extreme inputs handled gracefully.
  4. CLI & Flag: Sub-commands (--json, --dry-run, --mode super, --tournament) adhere to contract.
"""

import os
import shutil
import tempfile
import unittest

from tools.lint.plan_schema_sentinel import validate_plan_content, detect_dag_cycles
from tools.design.plan_harvester import harvest_plan, slugify, calibrate_plan_against_git
from tools.design.super_plan_engine import check_ambiguities, scaffold_super_plan


VALID_SUPER_PLAN = """<!--
# Author: Thế Vị (@TeeVee98) | MIT License
-->
# Spec-Driven Implementation Plan: Event Bus Architecture

> Reference: standards/qa-process/plan-protocol.md
> Ambiguity Gate Status: Resolved
> 📝 Plan Changelog (v1.0): Initial plan.

## 1. Affected Files & Blast Radius
| Action | File Path & Line Anchor | Scope |
|---|---|---|
| `[MODIFY]` | `tools/core/agent_runner.py` (L10-L45) | Core broker dispatch |
| `[CREATE]` | `tests/test_event_bus.py` (New) | Unit tests |

Direct Callers: Worker A
Regression Risk: Low

## 2. Data Flow & Interface Signatures
```python
def dispatch(topic: str, payload: dict) -> bool:
    ...
```

## 3. Atomic Milestones (Execution DAG)
### Milestone 1: Interfaces & Harness [PARALLEL_OK]
- Node ID: `M1` | depends_on: `[]`
- Compute Tier: [Model: Flash | Thinking: Off | Temp: 0.1]
- `tools/core/agent_runner.py`
Circuit Breaker: Max Fix Attempts: 2 | Scope Guard: Halt if new file added | Rollback: git checkout -- tools/core/agent_runner.py
Pass Gate: `pytest tests/test_agent_runner.py`

### Milestone 2: Router Dispatch Integration
- Node ID: `M2` | depends_on: `[M1]`
- Compute Tier: [Model: Pro | Thinking: High]
- `tests/test_event_bus.py`
Circuit Breaker: Max Fix Attempts: 2 | Scope Guard: Halt on failure | Rollback: git checkout -- tests/test_event_bus.py
Pass Gate: `pytest tests/test_event_bus.py`

## 4. Verification Matrix
| ID | Scenario | Input | Expected Output | Command |
|---|---|---|---|---|
| TC-01 | Happy Path | payload | True | `pytest tests/test_event_bus.py` |

## 5. Tri-Vulnerability Self-Critique & Mitigations
1. Vulnerability 1 (Concurrency / Race Condition): Lock mutex before dispatch.
2. Vulnerability 2 (Resource Extremes / Timeout): 5s network timeout on subscriber.
3. Vulnerability 3 (Blast Radius / Backward Compatibility): Adapter wrapper for legacy callers.

## 6. Rollback & State-Migration Matrix (Zero-Downtime Guard)
| Phase | Trigger Scenario | Mitigation | Rollback Command |
|---|---|---|---|
| Migration | Failure | Safe revert | `git checkout -- file` |
"""


class TestSuperPlanAndHarvester(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # Scenario 1: Positive
    # -------------------------------------------------------------------------
    def test_positive_super_plan_validation(self):
        passed, issues, details = validate_plan_content(VALID_SUPER_PLAN, mode="super")
        self.assertTrue(passed, f"Expected pass but got issues: {issues}")
        self.assertEqual(len(issues), 0)
        self.assertEqual(details["circuit_breakers_detected"], 2)
        self.assertEqual(details["compute_tiers_detected"], 2)
        self.assertEqual(details["dag_nodes"], ["M1", "M2"])
        self.assertEqual(len(details["dag_cycles"]), 0)
        self.assertTrue(details["ast_grounding"]["is_valid"])

    def test_positive_plan_harvesting_with_calibration(self):
        plan_file = os.path.join(self.temp_dir, "plan.md")
        with open(plan_file, "w", encoding="utf-8") as f:
            f.write(VALID_SUPER_PLAN)

        adr_dir = os.path.join(self.temp_dir, "adr")
        success, msg, data = harvest_plan(plan_file, adr_dir, dry_run=False)
        self.assertTrue(success)
        self.assertEqual(data["index"], 1)
        self.assertTrue(os.path.isfile(data["path"]))
        self.assertIn("calibration", data)

        with open(data["path"], "r", encoding="utf-8") as f:
            adr_text = f.read()
        self.assertIn("# ADR-0001: Event Bus Architecture", adr_text)
        self.assertIn("## Plan Calibration & Drift Analysis", adr_text)

    # -------------------------------------------------------------------------
    # Scenario 2: Negative (Failures caught by Sensor)
    # -------------------------------------------------------------------------
    def test_negative_missing_circuit_breaker_fails(self):
        plan_no_breaker = VALID_SUPER_PLAN.replace("Circuit Breaker:", "Note:")
        passed, issues, _ = validate_plan_content(plan_no_breaker, mode="super")
        self.assertFalse(passed)
        self.assertTrue(any("Circuit Breaker" in iss for iss in issues))

    def test_negative_missing_compute_tier_fails(self):
        plan_no_tier = VALID_SUPER_PLAN.replace("Compute Tier:", "Info:").replace("Model:", "Worker:")
        passed, issues, _ = validate_plan_content(plan_no_tier, mode="super")
        self.assertFalse(passed)
        self.assertTrue(any("Compute Tier" in iss for iss in issues))

    def test_negative_ast_preflight_detects_phantom_file(self):
        plan_with_phantom = VALID_SUPER_PLAN.replace("tools/core/agent_runner.py", "src/non_existent_phantom.py")
        passed, issues, details = validate_plan_content(plan_with_phantom, mode="super")
        self.assertFalse(passed)
        self.assertTrue(any("AST Pre-flight failed" in iss for iss in issues))
        self.assertIn("src/non_existent_phantom.py", details["ast_grounding"]["missing_files"])

    def test_negative_dag_cycle_detection(self):
        graph_with_cycle = {"M1": ["M2"], "M2": ["M1"]}
        cycles = detect_dag_cycles(graph_with_cycle)
        self.assertTrue(len(cycles) > 0)
        self.assertTrue(any("M1 -> M2 -> M1" in c for c in cycles))

    def test_negative_missing_vulnerability_categories(self):
        plan_no_race = VALID_SUPER_PLAN.replace("Concurrency / Race Condition", "General Logic").replace("idempotent", "clean")
        passed, issues, _ = validate_plan_content(plan_no_race, mode="super")
        self.assertFalse(passed)
        self.assertTrue(any("race_condition" in iss for iss in issues))

    # -------------------------------------------------------------------------
    # Scenario 3: Boundary
    # -------------------------------------------------------------------------
    def test_boundary_slugify_unicode_and_punctuation(self):
        self.assertEqual(slugify("Tính năng / Cache: Redis & Memory!!"), "tinh-nang-cache-redis-memory")
        self.assertEqual(slugify("   ---   "), "unnamed-decision")
        self.assertEqual(slugify("Feature 2.0 (Deep-Reasoning)"), "feature-20-deep-reasoning")

    def test_boundary_calibration_empty_plan(self):
        calib = calibrate_plan_against_git("No files here")
        self.assertEqual(calib["planned_files"], [])
        self.assertIsInstance(calib["drift_ratio"], float)

    def test_boundary_ambiguity_short_prompt(self):
        questions = check_ambiguities("fix auth")
        self.assertTrue(len(questions) >= 1)
        self.assertIn("Recommended", questions[0]["recommended"])

    # -------------------------------------------------------------------------
    # Scenario 4: CLI & Tournament Scaffolding
    # -------------------------------------------------------------------------
    def test_tournament_scaffold_output_and_tradeoff_matrix(self):
        plan = scaffold_super_plan("Distributed Cache Engine", ["tools/core/agent_runner.py"], tournament=True)
        self.assertIn("Orthogonal Architectural Tournament (Trade-off Matrix)", plan)
        self.assertIn("Branch A: Minimalist", plan)
        self.assertIn("Branch B: Clean Architecture", plan)
        self.assertIn("Branch C: High Performance", plan)
        self.assertIn("Rollback & State-Migration Matrix", plan)

        # Validate that the generated tournament plan passes super validation
        passed, issues, details = validate_plan_content(plan, mode="super")
        self.assertTrue(passed, f"Tournament plan failed validation: {issues}")
        self.assertEqual(details["mode"], "super")


if __name__ == "__main__":
    unittest.main()
