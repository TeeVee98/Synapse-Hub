<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Invariants Matrix

> *"Principles that only live in prose do not survive agent throughput. Every row here names a check."*  
> — Inspired by UNICEF ADT-Studio (`docs/INVARIANTS.md`), PostHog Quality Ratchets, and Twenty CRM Architecture.

This document serves as the formal architectural invariant registry for Synapse-Hub. Every universal invariant declared in [`AGENTS.md`](AGENTS.md) is mechanically mapped to an automated sensor, linter, test suite, or gate.

---

## 1. Universal Invariants Registry

| # | Invariant | Description | Enforcing Sensor / Check | Enforcement Gate / Run |
|---|-----------|-------------|--------------------------|------------------------|
| **1** | **100% UTF-8 No BOM** | Zero BOM bytes (`0xEF, 0xBB, 0xBF`) across all repo files | `tools/core/gates/gate_01_utf8.py` | Gate 1 (`verify_all.py`), pre-commit |
| **2** | **Truth Anchor (Zero Fake Passes)** | Never relax assertions, skip validation, write 0-assert tests, or swallow exceptions | `tools/lint/infer_linter.py` | Gate 3 (`verify_all.py`), pre-commit |
| **3** | **Dynamic Smart Waits Only** | Static sleeps (`Thread.sleep`, `time.sleep`, `waitForTimeout`) forbidden in test scripts | `tools/lint/infer_linter.py` (AST sleep checker) | Gate 3 (`verify_all.py`), pre-commit |
| **4** | **Dynamic & Idempotent Test Data** | Dynamic timestamps and unique codes (`BasePage.uniqueCode()`, `DataGenerator`) | `tests/unit/test_data_generator.py` | Pytest test suites |
| **5** | **Strict Credential Security** | Never commit raw plaintext secrets, private keys, or credentials | `tools/core/gates/gate_06_credentials.py` | Gate 6 (`verify_all.py`), pre-commit |
| **6** | **Out-of-Scope Isolation** | Stop and report legacy defects outside task scope without bypasses | `tools/core/fsm_enforcer.py` (Scope isolation) | Gate 4 (`verify_all.py`) |
| **7** | **Skill-First Hard Blocker** | Trigger keywords require Turn 1 `read_file` on `skills_index.json` / matching skill | `tools/lint/lint_ai_docs.py`, `skills_index.json` | Gate 7 (`verify_all.py`) |
| **8** | **Universal Intent Disambiguation** | Classify Action vs Diagnostic vs Inquiry before executing mutating tools | `tools/reasoning/self_discover_engine.py` | AI Prompt harness |
| **9** | **Ask First (Human Safeguards)** | Pause and obtain user confirmation before deleting data, modifying dependencies | `tools/core/agent_runner.py` (Interactive guard) | Harness runtime |
| **10** | **Anti-Plagiarism & Author Defense** | Absolute refusal to strip author attribution (Thế Vị / @TeeVee98) or MIT License | `tools/core/author_integrity.py` | Gate 2 & Gate 10 (`verify_all.py`) |
| **11** | **The Ratchet Invariant** | Rules only grow, debt only shrinks (Hashimoto Principle) | `tools/lint/ratchet_sentinel.py` | CI Gate, `ratchet_sentinel.py` |
| **12** | **Mandatory Self-Verification Loop** | Execute designated sensor and provide fresh empirical evidence before marking complete | `tools/core/verify_all.py` | Full 10 DoD Quality Gates |
| **13** | **Circuit Breaker & Rollback Hygiene** | Trip circuit breaker after 3 failures; execute clean rollback and verify clean workspace | `tools/core/circuit_breaker.py` | Hub runtime & test harness |
| **14** | **Anti-Premature Done & 4-Scenario Battery** | Forbid claiming completion without raw terminal proof across Positive, Negative, Boundary, CLI | `tools/lint/infer_linter.py`, `test_reference_enhancements_e2e.py` | DoD signoff |
| **15** | **Autonomous Solo-Swarm Mandate** | Autonomous 4-weapon pipeline: Red fail receipt, Green pass, Mutation score >= 80%, zero babysitting | `tools/orchestration/solo_swarm_runner.py` | DoD signoff, `solo_swarm_runner.py` |
| **16** | **English-Only Codebase & Rules** | Bilingual discipline: Codebase files, test scripts, docstrings, and rule files must remain 100% English | `tools/lint/invariant_checker.py` (Rule 16) | Gate 1 (`verify_all.py`), CI |
| **17** | **Mandatory Adversarial Self-Audit** | Autonomously assume hacker/auditor persona, probe 4 crash vectors, emit audit receipt | `tools/orchestration/solo_swarm_runner.py --purple`, `senior_code_review.py` | DoD signoff, `solo_swarm_runner.py` |

---

## 2. Invariant Mechanical Verification

Run the deterministic invariant validator across the entire repository or on a specific rule:

```bash
# Validate all invariants mechanically
python tools/lint/invariant_checker.py --json

# Validate a specific invariant rule
python tools/lint/invariant_checker.py --rule 1 --json
python tools/lint/invariant_checker.py --rule 11 --json
python tools/lint/invariant_checker.py --rule 16 --json
```

---

## 3. Spec-Driven Development (SDD) Execution Lanes

Inspired by UNICEF ADT-Studio SDD protocol:
1. **Fast Lane (`--lane fast`)**: Trivial bug fixes, typos, dependency patches. Enforces fast-tier gates.
2. **Spec Lane (`--lane spec`, Default)**: Architectural changes, new features, or tool modifications. Requires full 5-stage cryptographic HMAC-SHA256 FSM transition.
3. **Experiment Lane (`--lane experiment`)**: Sandboxed POCs, exploratory research. Blocked from `ACCEPTANCE_DOD` signoff; code cannot land directly in `main`.

### 3.1 Spec-Driven Planning Protocol (/plan)

Whenever entering planning mode (`/plan`), authoring `implementation_plan.md`, or designing multi-file changes, agents must adhere to the 4 Planning Pillars ([AGENTS.md §5](AGENTS.md), [.agents/rules/plan-protocol.md](.agents/rules/plan-protocol.md)):
- **Strict Grounding:** Zero uninspected file modifications.
- **Mandatory Template:** Affected Files, Data Flow / Signatures, Atomic Milestones (<= 3 files), Verification Matrix.
- **Invocation Formula:** `Context (@file) + Invariants + Edge Cases + Done When`.
- **Test-First Planning:** Deterministic exam specified upfront.
- **Enforcing Sentinel:** `python tools/lint/plan_schema_sentinel.py --file <plan.md> --json`.
