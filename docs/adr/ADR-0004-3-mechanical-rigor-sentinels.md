<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0004: 3 Mechanical Rigor Sentinels

- **Status:** Accepted (DoD Certified)
- **Date:** 2026-11-23
- **Source Plan:** `implementation_plan.md`
- **Deciders:** Synapse Hub Autonomous Agent Core & Engineering Team

---

## Context & Problem Statement
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

---

## Vulnerability Self-Critique & Mitigation Strategies
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

---

## Consequences & Guarantees
- **Positive:** Sealed interface contracts, zero-regression blast radius, idempotent execution.
- **Negative / Constraints:** Strict adherence to atomic milestone budget (<= 3 files) and type contracts.
---

## Plan Calibration & Drift Analysis
- **Plan File Accuracy Score:** 10.9%
- **Plan File Drift Ratio:** 0.891
- **Semantic Contract Accuracy Score:** 50.0%
- **Semantic Contract Drift Ratio:** 0.5
- **Composite Plan Accuracy Score:** 30.4%
- **Unplanned Files (41):** `.agent/skills/super-plan/SKILL.md`, `AGENTS.md`, `project_state.json`, `standards/qa-process/plan-protocol.md`, `templates/test-plan/spec-driven-plan-template.md`, `tests/test_a2a_qa_server.py`, `tests/test_ast_command_guard.py`, `tests/test_dashboard_chat.py`, `tests/test_docker_sandbox_runner.py`, `tests/test_micro_mutator.py`, `tests/test_output_offloader.py`, `tests/test_qa_model_router.py`, `tests/test_qa_task_scheduler.py`, `tests/test_solo_swarm_runner.py`, `tests/test_sop_enforcer.py`, `tools/api/a2a_qa_server.py`, `tools/context/output_offloader.py`, `tools/core/gates/gate_02_portability.py`, `tools/core/sop_schema.py`, `tools/design/plan_harvester.py`, `tools/design/super_plan_engine.py`, `tools/lint/micro_mutator.py`, `tools/lint/plan_schema_sentinel.py`, `tools/orchestration/qa_task_scheduler.py`, `tools/orchestration/solo_swarm_runner.py`, `tools/reasoning/qa_model_router.py`, `tools/runtime/ast_command_guard.py`, `tools/runtime/docker_sandbox_runner.py`, `tools/tools_schema.json`, `tests/test_cross_service_contract_graph.py`, `tests/test_deterministic_race_scheduler.py`, `tests/test_formal_contract_verifier.py`, `tests/test_super_plan_10_blueprint.py`, `tests/test_super_plan_10_perfection.py`, `tools/api/cross_service_contract_graph.py`, `tools/context/call_graph_indexer.py`, `tools/context/polyglot_ast_parser.py`, `tools/lint/equivalent_mutant_filter.py`, `tools/lint/plan_mutator.py`, `tools/orchestration/deterministic_race_scheduler.py`, `tools/reasoning/formal_contract_verifier.py`

