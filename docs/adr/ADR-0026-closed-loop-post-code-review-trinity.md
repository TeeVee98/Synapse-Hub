<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0026: Closed-Loop Post-Code `/review` Adversarial Auditor (`/super-plan -> /solo -> /review` Control Plane)

- **Status:** Accepted (DoD Certified)
- **Date:** 2026-11-26
- **Source Plan:** `review_super_plan.md`
- **Deciders:** Synapse Hub Autonomous Agent Core & Engineering Team

---

## Context & Problem Statement

Synapse Hub previously provided `/super-plan` (spec-driven architectural planning with typed manifests, DAG write sets, and verification matrices) and `/solo` (single-agent Red -> Blue -> Mutation -> Purple execution with HMAC-signed receipts). However, post-implementation code review lacked a deterministic, zero-trust reconciler capable of verifying that `/solo` code diffs, AST contracts, downstream callers, and cryptographic receipts actually match the approved `/super-plan` contract.

Without an independent auditor:
- Missing `[CREATE]` files, undeleted `[DELETE]` files, or silent scope creep outside planned write sets could slip past ad-hoc diff reviews.
- Section 2 DTO/function contracts could drift in parameter arity, lose `@dataclass(frozen=True)`, or widen concrete types to bare `Any`.
- Test files could be edited or weakened after Red certification (`test_tree_hash` drift) or carry tautological assertions.
- Modified function signatures could silently break downstream call sites outside the immediate diff or introduce circular imports.

---

## Decision Drivers & Invariants

1. **Zero-Trust Independence:** Re-verify HMAC-SHA256 receipts, SHA-256 `test_tree_hash` snapshots, AST contracts, and downstream callers directly from disk truth rather than trusting self-reported agent prose.
2. **Strict Acyclic Layering:** `solo_runner.py` already imports `senior_code_review.py`; therefore `senior_code_review.py` and `plan_review_auditor.py` MUST NOT import `solo_runner.py` (relying strictly on leaf modules `solo_contracts.py`, `call_graph_indexer.py`, `neuro_symbolic_solver.py`, `dag_self_healer.py`, and `decision_log.py`).
3. **100% Backward-Compatible CLI & Mock Parity:** Preserve all 13 existing `TestSeniorCodeReview` tests (including exact `main -> run_review` keyword forwarding) and keep ad-hoc `agent-qa review` clean on repositories with unrelated historical receipts.
4. **Strict Read-Only Diagnostic Persona:** `/review` (`.agent/skills/review/SKILL.md`) operates strictly in read-only DIAGNOSTIC mode and never collides with specification stress-testing (`review-spec`).

---

## Architectural Decision (Selected Branch B)

Establish `/review` as the third pillar of the closed-loop engineering control plane (`/super-plan -> /solo -> /review`):

1. **Modular Reconciliation Engine (`tools/orchestration/plan_review_auditor.py`):**
   - Exposes immutable frozen DTOs (`PlanReconciliationDTO`, `SoloProvenanceAuditDTO`, `CallerCompatibilityDTO`, `UnifiedReviewReceiptDTO`) and `audit_plan_and_solo_execution(...)`.
   - Reconciles Section 1 & 3 Write Sets, Section 2 Python AST DTO/function contracts, Section 4 Verification Matrix test functions (via `AstTautologyAnalyzer`), `/solo` HMAC-SHA256 Red & Mutation receipts (including post-Red `test_tree_hash` tamper detection and `decisions.tsv` strict auditing), and downstream callers (`CallGraphIndexer` capped at `<= 50` files + `DependencyCycleSolver` import acyclicity).
   - Signs `reports/code_review_receipt.json` atomically (`tempfile.mkstemp` + `os.replace`) with constant-time HMAC-SHA256 verification.
2. **Upgraded Canonical Reviewer (`tools/orchestration/senior_code_review.py`):**
   - Adds AST-backed multi-line swallowed exception detection, mutable default argument checks, `shell=True`/`eval`/`exec` security checks, non-monotonic `time.time()` timeout checks, tautological test detection, 4-Angle `simplify` deep-nesting (`> 4`) checks, and bounded `HumanizeLinter` prose checks.
   - Adds `--plan`, `--milestone`, `--strict`, `--strict-solo`, and `--receipt-out` CLI flags using conditional `extra_kwargs` forwarding in `main()`.
3. **Unified CLI, Schema, Skill Router & Multi-IDE Sync:**
   - Exposes all new flags on `agent-qa review` (`tools/core/cli_specs.json`) and promotes `senior_code_review.py` into `tools/tools_schema.json` with zero schema drift.
   - Publishes `.agent/skills/review/SKILL.md`, registers collision-free `/review` routing in `tools/core/skill_router.py`, and extends `tools/core/sync_agent_rules.py` to synchronize `.claude/commands/review.md` and `.windsurf/workflows/review.md` while keeping the `starter` client profile under 35 lines.

---

## Vulnerability Mitigations

1. **Atomic Receipt I/O & Acyclic Graph:** Atomic temp-file + `os.replace` writes prevent partial-JSON race conditions; corrupt receipts produce structured `CORRUPT_SOLO_RECEIPT` findings instead of crashing; zero imports of `solo_runner.py` guarantee acyclicity.
2. **Bounded AST & Call-Graph Latency:** Reuses `.cache/call_graph_index.json` (`< 5ms`), caps caller AST scanning to `<= 50` direct dependents of functions with changed signatures, and converts `SyntaxError` into explicit `Must fix` findings.
3. **Zero Regression & Collision Guard:** Conditional keyword forwarding preserves legacy `main()` mocks; `_REVIEW_SPEC_GUARD_RE` prevents `/review-spec`, BRD, and `.feature` prompts from colliding with `/review`.

---

## Consequences & Guarantees

- **Positive:** Complete closed-loop determinism across planning (`/super-plan`), execution (`/solo`), and independent auditing (`/review`); `100.0%` live mutation kill score across both `plan_review_auditor.py` (`20/20`) and `senior_code_review.py` (`20/20`).
- **Constraints:** Changes to `senior_code_review.py` CLI flags must remain synchronized with `tools/core/cli_specs.json` and `tools/tools_schema.json` (enforced by `cli_schema_sentinel.py`), and `plan_review_auditor.py` must never import `solo_runner.py`.
