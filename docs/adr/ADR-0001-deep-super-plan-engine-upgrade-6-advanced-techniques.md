<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0001: Deep Super-Plan Engine Upgrade (6 Advanced Techniques)

- **Status:** Accepted (DoD Certified)
- **Date:** 2026-11-23
- **Source Plan:** `implementation_plan.md`
- **Deciders:** Synapse Hub Autonomous Agent Core & Engineering Team

---

## Context & Problem Statement
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

---

## Decision Drivers & Invariants
- Grounding Principle: "Read First – Plan Later" (AGENTS.md §5).
- Zero Fake-Passes Invariant & Deterministic Verification Matrix.
- Execution DAG with Milestone Circuit Breakers & Clean Context Handoff.

---

## Considered Options & Architectural Decision
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

---

## Vulnerability Self-Critique & Mitigation Strategies
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

---

## Consequences & Guarantees
- **Positive:** Sealed interface contracts, zero-regression blast radius, idempotent execution.
- **Negative / Constraints:** Strict adherence to atomic milestone budget (<= 3 files) and type contracts.
---

## Plan Calibration & Drift Analysis
- **Plan Accuracy Score:** 46.7%
- **Plan Drift Ratio:** 0.533
- **Unplanned Files (8):** `AGENTS.md`, `project_state.json`, `tests/test_telegram_bot.py`, `tools/core/telegram_bot.py`, `tools/tools_schema.json`, `.agent/`, `.agents/workflows/`, `ai-agents/workflows/super-plan.md`

