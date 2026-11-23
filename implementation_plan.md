<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Spec-Driven Implementation Plan: Deep Super-Plan Engine Upgrade (6 Advanced Techniques)

> **Reference Protocol:** [AGENTS.md §5](AGENTS.md), [standards/qa-process/plan-protocol.md](standards/qa-process/plan-protocol.md), [ai-agents/workflows/super-plan.md](ai-agents/workflows/super-plan.md)
> **Grounding Verification:** Inspected files: `tools/lint/plan_schema_sentinel.py`, `tools/design/plan_harvester.py`, `tools/design/super_plan_engine.py`
> **Ambiguity Gate Status:** Resolved
>   - Decision 1 (AST Pre-flight): Auto-activate in `mode='super'`, emit Warning in `mode='standard'`.
>   - Decision 2 (Tournament Planning): Trigger via `--tournament` flag or when $\ge 2$ architectural forks exist.
>   - Decision 3 (Calibration Loop): Measure Drift Ratio, log unplanned files into ADR, and update `project_state.json`.

---

## 1. Affected Files & Blast Radius

### Target Files & Line Anchors
| Action | File Path & Line Anchor | Scope & Responsibility |
|---|---|---|
| `[MODIFY]` | `tools/lint/plan_schema_sentinel.py` (L103-L241) | Add AST Pre-flight validation (`--check-ast`) and Compute Tier verification |
| `[MODIFY]` | `tools/design/plan_harvester.py` (L209-L243) | Add Plan Calibration Loop (git diff check, drift ratio calculation, ADR logging) |
| `[MODIFY]` | `tools/design/super_plan_engine.py` (L113-L243) | Support `--tournament` scaffolding with 3 orthogonal branches & Rollback matrix |
| `[MODIFY]` | `templates/test-plan/spec-driven-plan-template.md` (L70-L126) | Incorporate Compute Tier tags, Rollback matrix, and Surgical Patch Changelog header |
| `[MODIFY]` | `standards/qa-process/plan-protocol.md` (L90-L125) | Institutionalize 6 advanced techniques and surgical patch rules |
| `[MODIFY]` | `tests/test_super_plan_and_harvester.py` (L50-L180) | Extend test coverage across 4 scenarios for all 6 new capabilities |

### Blast Radius & Downstream Dependencies
- **Direct Callers:** `/super-plan` workflow, `/plan` workflow, `verify_all.py` (Gate 4 & Gate 9).
- **Regression Risk:** Low. All additions preserve backward compatibility for standard mode.
- **Mitigation:** Fallback warnings in standard mode; AST pre-flight handles missing files gracefully.

---

## 2. Data Flow & Interface Signatures

> **Anti-Full-Code Invariant:** Define ONLY DTOs, schemas, and function signatures with type contracts. Full implementation body is strictly deferred to the execution phase.

```python
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

@dataclass(frozen=True)
class AstPreflightResultDTO:
    is_valid: bool
    missing_files: List[str]
    missing_symbols: List[str]
    checked_files: int
    checked_symbols: int

@dataclass(frozen=True)
class PlanCalibrationResultDTO:
    planned_files: List[str]
    actual_files: List[str]
    unplanned_files: List[str]
    drift_ratio: float
    accuracy_score: float

def verify_plan_ast_grounding(plan_content: str, repo_root: str) -> AstPreflightResultDTO:
    """Verifies that all files, classes, and functions referenced in plan physically exist."""
    ...

def calibrate_plan_against_git(plan_content: str, repo_root: str) -> PlanCalibrationResultDTO:
    """Compares planned target files against actual git diff --name-only to compute drift ratio."""
    ...

def scaffold_orthogonal_tournament(task: str, branches: List[str]) -> str:
    """Scaffolds a 3-way tournament plan comparing Minimalist vs Clean vs Performance branches."""
    ...
```

---

## 3. Atomic Milestones (Execution DAG)

### Milestone 1: AST Pre-flight Validation & Compute-Annotated DAG [PARALLEL_OK]
- **Node ID:** `M1` | **depends_on:** `[]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 2):** `tools/lint/plan_schema_sentinel.py`, `templates/test-plan/spec-driven-plan-template.md`
- **Goal:** Add AST pre-flight verification to linter (rejecting hallucinated files/symbols) and validate `Compute Tier:` tags.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if files outside budget touched | Rollback: `git checkout -- tools/lint/plan_schema_sentinel.py templates/test-plan/spec-driven-plan-template.md`
- **Pass Gate:** `pytest tests/test_plan_schema_sentinel.py`

### Milestone 2: Plan Calibration Loop & ADR Drift Ingestion
- **Node ID:** `M2` | **depends_on:** `[M1]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 2):** `tools/design/plan_harvester.py`, `standards/qa-process/plan-protocol.md`
- **Goal:** Implement `calibrate_plan_against_git`, update ADR harvesting with Drift Ratio, and document Surgical Patch rule.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if external network invoked | Rollback: `git checkout -- tools/design/plan_harvester.py standards/qa-process/plan-protocol.md`
- **Pass Gate:** `python tools/design/plan_harvester.py --file templates/test-plan/spec-driven-plan-template.md --dry-run`

### Milestone 3: Orthogonal Tournament Scaffolding & 4-Scenario Battery
- **Node ID:** `M3` | **depends_on:** `[M2]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.2]`
- **Files Modified (Max 2):** `tools/design/super_plan_engine.py`, `tests/test_super_plan_and_harvester.py`
- **Goal:** Implement `--tournament` flag in `super_plan_engine.py` and extend 4-scenario battery in tests.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt on failure | Rollback: `git checkout -- tools/design/super_plan_engine.py tests/test_super_plan_and_harvester.py`
- **Pass Gate:** `pytest tests/test_super_plan_and_harvester.py`

---

## 4. Verification Matrix ("Define the Exam in the Plan")

| ID | Test Scenario | Input / Precondition | Expected Output / Assertion | Verification Command |
|---|---|---|---|---|
| **TC-01** | AST Preflight Valid | Plan referencing existing `tools/core/agent_runner.py` | `is_valid == True`, missing lists empty | `pytest tests/test_super_plan_and_harvester.py -k "test_ast_preflight_valid"` |
| **TC-02** | AST Preflight Hallucination | Plan referencing fake `src/phantom_service.py` | `is_valid == False`, missing_files contains phantom | `pytest tests/test_super_plan_and_harvester.py -k "test_ast_preflight_detects_phantom"` |
| **TC-03** | Calibration Loop Drift | Planned `[f1.py]`, git diff `[f1.py, f2.py]` | `unplanned_files == ['f2.py']`, `drift_ratio == 0.5` | `pytest tests/test_super_plan_and_harvester.py -k "test_calibration_drift"` |
| **TC-04** | Tournament Scaffold | `scaffold --task "Cache" --tournament` | Generates 3 branches with Trade-off Matrix | `python tools/design/super_plan_engine.py scaffold --task "Cache" --tournament` |
| **TC-05** | Full DoD Gates | Run all 11 Quality Gates | 100% DoD Compliant | `python tools/core/verify_all.py --mode hub --tier fast` |

---

## 5. Tri-Vulnerability Self-Critique & Mitigations

1. **Vulnerability 1 (Concurrency / Race Condition):**
   - *Risk:* Git calibration running while uncommitted files are in flight causing inaccurate drift ratio.
   - *Mitigation:* `calibrate_plan_against_git` explicitly inspects both staged and unstaged working tree diffs cleanly.
2. **Vulnerability 2 (Resource Extremes / Timeout):**
   - *Risk:* AST parsing hundreds of files referenced in massive plans causing linter timeout.
   - *Mitigation:* Bound AST pre-flight to at most 10 distinct source files per plan with a 2-second timeout cache.
3. **Vulnerability 3 (Blast Radius / Backward Compatibility):**
   - *Risk:* Strict AST pre-flight failing on planned `[CREATE]` new files that don't exist yet.
   - *Mitigation:* Explicitly whitelist files marked with `(New)` or `[CREATE]` from physical existence check.

---

## 6. Rollback & State-Migration Matrix (Zero-Downtime Guard)

| Pha thay đổi | Kịch bản lỗi (Trigger) | Cơ chế chuyển đổi (Dual-mode / Flag) | Lệnh Rollback an toàn |
|---|---|---|---|
| AST Pre-flight Check | Phân tích file lạ bị lỗi cú pháp | Catch `SyntaxError` và hạ cấp thành Warning | `plan_schema_sentinel.py --mode standard` |
| ADR Calibration Ingestion | `project_state.json` bị khóa ghi | Ghi fallback ra stdout và file tạm | `git checkout -- project_state.json` |
| Tournament Scaffolding | Prompt không nhận diện được | Fallback về standard single-branch plan | `super_plan_engine.py scaffold --task "..."` |

---

## 7. Execution Transition & Plan Harvesting
- **Clean Context Handoff:** Execute this plan through atomic milestones, keeping edits minimal and focused.
- **Plan Harvesting Hook:** Upon completing all 3 milestones and passing all 11 gates, harvest this plan into `docs/adr/ADR-0001-super-plan-deep-mechanical-pipeline.md`.
