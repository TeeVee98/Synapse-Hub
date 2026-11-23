<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Spec-Driven Implementation Plan: [Feature / Bug Name]

> **Reference Protocol:** [AGENTS.md §5](AGENTS.md), [standards/qa-process/plan-protocol.md](standards/qa-process/plan-protocol.md), [ai-agents/workflows/super-plan.md](ai-agents/workflows/super-plan.md)
> **Grounding Verification:** Inspected files: `[path/to/inspected_file_1]`, `[path/to/inspected_file_2]`
> **Ambiguity Gate Status:** Resolved (All architectural forks and business constraints confirmed upfront)
> 📝 **Plan Changelog (v1.0):**
> - Initial spec-driven super-plan drafted and certified.

---

## 1. Affected Files & Blast Radius

### Target Files & Line Anchors
| Action | File Path & Line Anchor | Scope & Responsibility |
|---|---|---|
| `[MODIFY]` | `src/modules/target_module.py` (L120-L155) | Implementation of new logic or fix |
| `[CREATE]` | `tests/unit/test_target_module.py` (New) | Unit test suite covering deterministic exam |
| `[DELETE]` | `obsolete/path.py` (if any) | Obsolete wrapper / dead code |

### Blast Radius & Downstream Dependencies
- **Direct Callers:** `[Module A]`, `[Module B]`
- **Downstream Tests:** `pytest tests/unit/test_caller.py`
- **Regression Risk:** Low / Medium / High
- **Mitigation Strategy:** [e.g., Backward compatible adapter; parameter defaults preserved]

---

## 2. Data Flow & Interface Signatures

> **Anti-Full-Code Invariant:** Define ONLY DTOs, schemas, and function signatures with type contracts. Full implementation body is strictly deferred to the execution phase.

### Schemas & DTO Types
```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class TargetInputDTO:
    id: str
    payload: dict
    dry_run: bool = False

@dataclass(frozen=True)
class TargetResultDTO:
    success: bool
    message: str
    error_code: Optional[str] = None
```

### Function & Class Signatures
```python
def execute_target_flow(input_data: TargetInputDTO) -> TargetResultDTO:
    """Executes target business workflow idempotently.
    
    Guarantees:
      - Validates schema before mutation.
      - Never mutates shared state on failure.
    Raises:
      - ValueError: when input_data.id is empty or invalid.
    """
    ...
```

---

## 3. Atomic Milestones (Execution DAG)

### Milestone 1: Schemas, Types, and Contract Lock [PARALLEL_OK]
- **Node ID:** `M1` | **depends_on:** `[]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 2):** `src/target_types.py`, `tests/test_target_types.py`
- **Goal:** Define data models, interfaces, and compile verification.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if files outside budget touched | Rollback: `git checkout -- src/target_types.py tests/test_target_types.py`
- **Pass Gate:** `python3 -m py_compile src/target_types.py`

### Milestone 2: Core Business Logic & Unit Tests
- **Node ID:** `M2` | **depends_on:** `[M1]`
- **Compute Tier:** `[Model: Pro / Claude Sonnet | Thinking: High | Best-of-3]`
- **Files Modified (Max 2):** `src/target_module.py`, `tests/test_target_module.py`
- **Goal:** Implement the logic satisfying the Verification Matrix below.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if new file added | Rollback: `git checkout -- src/target_module.py tests/test_target_module.py`
- **Pass Gate:** `pytest tests/test_target_module.py`

### Milestone 3: Caller Integration & Quality Gates
- **Node ID:** `M3` | **depends_on:** `[M2]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 2):** `src/caller.py`, `tools/core/verify_all.py`
- **Goal:** Connect caller, verify end-to-end flow, run DoD gates.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt on out-of-scope failures | Rollback: `git checkout -- src/caller.py`
- **Pass Gate:** `python3 tools/core/verify_all.py --mode hub --tier fast`

---

## 4. Verification Matrix ("Define the Exam in the Plan")

| ID | Test Scenario | Input / Precondition | Expected Output / Assertion | Verification Command |
|---|---|---|---|---|
| **TC-01** | Happy Path | `TargetInputDTO(id="ID_01", payload={"key": "val"})` | `TargetResultDTO.success == True` and `error_code is None` | `pytest tests/test_target_module.py -k "test_happy_path"` |
| **TC-02** | Boundary (Empty Input) | `TargetInputDTO(id="", payload={})` | Raises `ValueError("id must not be empty")` | `pytest tests/test_target_module.py -k "test_empty_id"` |
| **TC-03** | Boundary (Extreme Size) | `TargetInputDTO(id="ID_02", payload={"large": "A"*10000})` | Handled gracefully without OOM or truncation | `pytest tests/test_target_module.py -k "test_large_payload"` |
| **TC-04** | Error / Timeout | Downstream dependency raises `TimeoutError` | Caught and wrapped as `TargetResultDTO(success=False, error_code="TIMEOUT")` | `pytest tests/test_target_module.py -k "test_timeout_fallback"` |
| **TC-05** | CLI / Gate | Execute with `--json` flag | Valid JSON output matching schema, exit code 0 | `python3 src/target_module.py --json` |

> **Invariant Check:** Zero generic descriptions allowed. All assertions above define deterministic states.

---

## 5. Tri-Vulnerability Self-Critique & Mitigations

1. **Vulnerability 1 (Concurrency / Race Condition):**
   - *Risk:* Concurrent callers could trigger duplicate ledger updates if idempotency token is not checked.
   - *Mitigation:* Enforce atomic check-and-set on `input_data.id` before executing state transition.
2. **Vulnerability 2 (Resource Extremes / Timeout):**
   - *Risk:* Downstream service timeout causing hanging thread and unhandled connection leak.
   - *Mitigation:* Bound all network requests to strict 5s timeout with deterministic circuit-breaker fallback.
3. **Vulnerability 3 (Blast Radius / Backward Compatibility):**
   - *Risk:* Existing callers expecting legacy return schema might break.
   - *Mitigation:* Preserve default parameter values and provide a backward-compatible adapter wrapper.

---

## 6. Rollback & State-Migration Matrix (Zero-Downtime Guard)

| Phase | Trigger Scenario | Mitigation / Dual-mode | Rollback Command |
|---|---|---|---|
| Schema / State Migration | Add column fails or locks | Default column value, zero table lock | `git checkout -- <file>` |
| Contract Cutover | Legacy caller failure | Backward-compatible adapter fallback | Revert commit or flag `USE_NEW_CONTRACT=0` |

---

## 7. Execution Transition & Plan Harvesting
- **Clean Context Handoff:** Execute this plan in a clean context or dispatch to subagents passing only this document + AST micro-slices.
- **Surgical Patch Protocol:** When updating plan upon review, edit only the targeted section using `edit_file` and append to the Changelog header. Do not overwrite the entire plan.
- **Plan Harvesting Hook:** Upon passing all quality gates, harvest architectural decisions (`Ruling:`) and schemas into `docs/adr/`.
