<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Spec-Driven Implementation Plan: 3 Mechanical Rigor Sentinels

> **Reference Protocol:** [AGENTS.md §5](AGENTS.md), [standards/qa-process/plan-protocol.md](standards/qa-process/plan-protocol.md)
> **Ambiguity Gate Status:** Resolved (Architectural direction locked: Zero prose-only rules, 100% mechanical gates)
> 📝 **Plan Changelog (v1.0):**
> - Initial super-plan drafted to eradicate Completion Reflex, Silent Drift, and Scope Creep via 3 deterministic sensors.

---

## 1. Affected Files & Blast Radius

### Target Files & Structural Anchors
| Action | File Path & Structural Anchor | Scope & Responsibility |
|---|---|---|
| `[MODIFY]` | `tools/lint/invariant_checker.py` [AST: check_rule_16_english_codebase] | Invariant 16: Mechanical English-Only Codebase & Rule Linter |
| `[MODIFY]` | `tools/lint/cli_schema_sentinel.py` [AST: validate_schema_parity] | Hard-fail gate for unregistered CLI tools in `tools/` |
| `[MODIFY]` | `tools/design/dag_self_healer.py` [AST: check_scope_guard_violation] | Physical Scope Guard comparing `git diff` against milestone `write_set` |
| `[CREATE]` | `tests/test_agent_rigor_sentinels.py` (New) | Comprehensive 4-scenario battery testing all 3 rigor sentinels |

### Blast Radius & Downstream Dependencies
- **Direct Callers:** `tools/core/verify_all.py` (Gate 1, Gate 4, Gate 7), Git Pre-commit hooks.
- **Downstream Tests:** `tests/test_invariant_checker.py`, `tests/test_cli_schema_sentinel.py`.
- **Regression Risk:** Zero. All new checks enforce existing standards with backward compatibility for whitelisted authors and existing registered tools.

---

## 2. Data Flow & Interface Signatures

> **Anti-Full-Code Invariant:** Define ONLY DTOs, schemas, and function signatures with type contracts. Full implementation body is strictly deferred to the execution phase.

```python
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Set

@dataclass(frozen=True)
class InvariantViolationDTO:
    rule: int
    name: str
    file: str
    line: Optional[int]
    message: str

@dataclass(frozen=True)
class ScopeGuardResultDTO:
    is_valid: bool
    node_id: str
    declared_write_set: List[str]
    unauthorized_files: List[str]

def check_rule_16_english_codebase(repo_root: str) -> List[Dict[str, Any]]:
    """Invariant 16: Scans codebase and rule files for non-English diacritics.
    Exemptions: Author attribution (Thế Vị / @TeeVee98).
    """
    ...

def check_scope_guard_violation(
    write_set: List[str],
    repo_root: str
) -> ScopeGuardResultDTO:
    """Verifies that actual git-modified files do not exceed declared milestone write_set.
    Raises: ScopeViolation if unauthorized files were mutated.
    """
    ...
```

---

## 3. Atomic Milestones (Execution DAG)

### Milestone 1: English-Only Codebase Linter (Invariant 16) [PARALLEL_OK]
- **Node ID:** `M1` | **depends_on:** `[]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 2):** `tools/lint/invariant_checker.py`
- **Write Set:** `['tools/lint/invariant_checker.py']`
- **Typed Interface Manifest:**
  - **consumes:** `[]`
  - **produces:** `[{"contract": "InvariantViolationDTO", "fields": {"rule": "int", "name": "str"}}]`
  - **invariants:** `["zero_false_positives_for_author_the_vi", "100_percent_utf8_scan"]`
- **Goal:** Implement `check_rule_16_english_codebase` detecting non-whitelisted Vietnamese text in code/rules and wire into `CHECKERS[16]`.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if out-of-scope files touched | Rollback: `git checkout -- tools/lint/invariant_checker.py`
- **Rollback Hook:** `git checkout -- tools/lint/invariant_checker.py`
- **Pass Gate:** `python3 -m py_compile tools/lint/invariant_checker.py`

### Milestone 2: Unregistered Tool Hard-Fail Gate & Physical Scope Guard
- **Node ID:** `M2` | **depends_on:** `[M1]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 2):** `tools/lint/cli_schema_sentinel.py,tools/design/dag_self_healer.py`
- **Write Set:** `['tools/lint/cli_schema_sentinel.py', 'tools/design/dag_self_healer.py']`
- **Typed Interface Manifest:**
  - **consumes:** `[{"contract": "InvariantViolationDTO"}]`
  - **produces:** `[{"contract": "ScopeGuardResultDTO", "fields": {"is_valid": "bool"}}]`
  - **invariants:** `["unregistered_tool_exit_code_1", "scope_violation_triggers_revert"]`
- **Goal:** Add `--enforce-registration` hard-fail to `cli_schema_sentinel.py` and implement `check_scope_guard_violation` in `dag_self_healer.py`.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if new dependency introduced | Rollback: `git checkout -- tools/lint/cli_schema_sentinel.py tools/design/dag_self_healer.py`
- **Rollback Hook:** `git checkout -- tools/lint/cli_schema_sentinel.py tools/design/dag_self_healer.py`
- **Pass Gate:** `python3 -m py_compile tools/lint/cli_schema_sentinel.py tools/design/dag_self_healer.py`

### Milestone 3: Test Battery & DoD Certification
- **Node ID:** `M3` | **depends_on:** `[M2]`
- **Compute Tier:** `[Model: Pro / Reasoning | Thinking: High | Best-of-3]`
- **Files Modified (Max 2):** `tests/test_agent_rigor_sentinels.py`
- **Write Set:** `['tests/test_agent_rigor_sentinels.py']`
- **Typed Interface Manifest:**
  - **consumes:** `[{"contract": "ScopeGuardResultDTO"}]`
  - **produces:** `[{"contract": "TestVerificationDTO", "fields": {"passed": "bool"}}]`
  - **invariants:** `["kill_score_ge_80", "zero_flaky_tests"]`
- **Goal:** Author 4-scenario battery verifying all 3 sentinels under positive, negative, boundary, and CLI flags; verify full 11 Quality Gates pass.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if out-of-scope files touched | Rollback: `git checkout -- tests/test_agent_rigor_sentinels.py`
- **Rollback Hook:** `git checkout -- tests/test_agent_rigor_sentinels.py`
- **Pass Gate:** `python3 -m pytest tests/test_agent_rigor_sentinels.py`

---

## 4. Verification Matrix ("Define the Exam in the Plan")

| ID | Test Scenario | Input / Precondition | Expected Output / Assertion | Verification Command |
|---|---|---|---|---|
| **TC-01** | English Linter (Positive) | English code with author `Thế Vị` | 0 violations returned | `python3 -m pytest tests/test_agent_rigor_sentinels.py -k "test_positive_english"` |
| **TC-02** | English Linter (Negative) | File containing `lên kế hoạch` | Violation flagged with rule=16 and line number | `python3 -m pytest tests/test_agent_rigor_sentinels.py -k "test_negative_vietnamese"` |
| **TC-03** | Unregistered Tool (Negative) | New script in `tools/` with argparse not in schema | `cli_schema_sentinel.py` returns exit code 1 with `UNREGISTERED_TOOL` | `python3 -m pytest tests/test_agent_rigor_sentinels.py -k "test_negative_unregistered"` |
| **TC-04** | Scope Guard (Negative) | File modified outside milestone write_set | `check_scope_guard_violation` returns `is_valid=False` | `python3 -m pytest tests/test_agent_rigor_sentinels.py -k "test_negative_scope_creep"` |
| **TC-05** | Scope Guard (Positive) | Only files within write_set modified | `check_scope_guard_violation` returns `is_valid=True` | `python3 -m pytest tests/test_agent_rigor_sentinels.py -k "test_positive_scope_clean"` |
| **TC-06** | Full DoD Gates | Fast verification suite | All 11 Quality Gates pass 100% | `python3 tools/core/verify_all.py --mode hub --tier fast` |

---

## 5. Tri-Vulnerability Self-Critique & Mitigations

1. **Vulnerability 1 (Concurrency / Race Condition):**
   - *Risk:* Multiple git commands checking `status` concurrently causing false scope creep flags.
   - *Mitigation:* Scope guard inspects clean snapshot arrays without mutating working directory state.
2. **Vulnerability 2 (Resource Extremes / Timeout):**
   - *Risk:* Scanning all codebase files for non-English characters exceeding 1s budget.
   - *Mitigation:* Whitelist file extensions (`.py`, `.ts`, `.md`), skip ignored dirs (`.git`, `node_modules`, `build`), and use fast regex pre-filter.
3. **Vulnerability 3 (Blast Radius / Backward Compatibility):**
   - *Risk:* False positives on valid author attributions or legitimate test strings containing international symbols.
   - *Mitigation:* Exact regex substitution allowing `Thế Vị` and `@TeeVee98` author signatures.

---

## 6. Rollback & State-Migration Matrix (Zero-Downtime Guard)

| Phase | Trigger Scenario | Mitigation / Dual-mode | Rollback Command |
|---|---|---|---|
| Invariant Check | False positives blocking CI | Revert `tools/lint/invariant_checker.py` | `git checkout -- tools/lint/invariant_checker.py` |
| Schema Sentinel | Valid internal tools blocked | Exemption whitelist in schema | `git checkout -- tools/lint/cli_schema_sentinel.py` |

---

## 7. Execution Transition & Plan Harvesting
- **Clean Context Handoff:** Pass this plan directly to `/solo-swarm` execution upon user command `"Làm đi"`.
- **Plan Harvesting Hook:** Upon passing all 11 DoD Quality Gates, harvest decisions into `docs/adr/ADR-0005-agent-rigor-mechanical-sentinels.md`.
