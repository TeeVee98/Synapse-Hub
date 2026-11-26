<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

---
name: review
version: 2.0.0
category: verification_and_resilience
description: Closed-Loop Post-Code Adversarial Reviewer (v2.0) reconciling /solo code, AST diffs, downstream callers, and HMAC receipts against /super-plan contracts with 4-Angle simplify cleanup lenses.
policies:
  network: none
  shell: read-only
  filesystem: read-only
---

# /review (Closed-Loop Post-Code Adversarial Reviewer & Plan-vs-Solo Auditor — v2.0)

> **Core Objective:** Act as an independent, zero-trust senior engineer auditing `/solo` implementation diffs and forensic receipts against `/super-plan` contracts before merge or handoff.
> **Unified CLI:** `agent-qa review` (`python3 tools/orchestration/senior_code_review.py`) | **Auditor Engine:** `tools/orchestration/plan_review_auditor.py`

---

## Strict Read-Only Diagnostic Boundary

- **Zero Auto-Edits:** `/review` operates in strict **DIAGNOSTIC (read-only)** mode. NEVER modify user source code, tests, or plans during `/review`.
- **Zero-Trust Verification:** Always re-verify cryptographic HMAC signatures, post-Red SHA-256 `test_tree_hash` snapshots, AST DTO/function signatures, and downstream callers directly from disk truth. Never trust self-reported agent prose.
- **Collision-Free Scope:** `/review` audits post-implementation code diffs, PRs, and `/solo` deliveries. Specification, BRD, and Gherkin `.feature` stress-testing remains owned by `review-spec` (`skills/02-test-design/review-spec/SKILL.md`).

---

## 7-Layer Closed-Loop Audit Protocol

When `/review` is invoked, run the deterministic auditor first, then synthesize findings with exact `file:line`, failure scenario, and minimal fix:

```bash
# Formal closed-loop audit reconciling /solo against /super-plan
agent-qa review --plan implementation_plan.md --strict-solo --json

# Single-milestone audit
agent-qa review --plan implementation_plan.md --milestone M1 --strict --json

# Ad-hoc uncommitted, staged, or branch diff review
agent-qa review --staged
agent-qa review --branch main --output-md reports/code_review.md --verify-cove
```

| Layer | Input Artifacts | Mechanical Checks | Severity Mapping |
|---|---|---|---|
| **1. Plan Scope & Write Set** | `--plan <plan.md>` Section 1 & 3 vs git diff / disk | Missing `[CREATE]`/`[MODIFY]` files, undeleted `[DELETE]` files, unplanned scope creep | Missing/Undeleted: `Must fix`; Unplanned: `Should fix` (`Must fix` under `--strict`) |
| **2. DTO & Signature Drift** | `--plan` Section 2 vs Python AST | Missing classes/DTOs/functions, parameter arity/name drift, bare `Any` widening, unfrozen DTOs | Missing/Arity/`Any`: `Must fix`; Unfrozen DTO: `Should fix` |
| **3. Verification Matrix** | `--plan` Section 4 (`TC-01..TC-NN`) vs `tests/` AST | Missing test files or `-k` test functions, empty tests (0 asserts), tautologies (`AstTautologyAnalyzer`) | Missing/Tautological/Empty: `Must fix` |
| **4. `/solo` Forensic Provenance** | `reports/solo_receipts/*`, `decisions.tsv` | Constant-time HMAC-SHA256 Red receipts, post-Red `test_tree_hash` tamper check, mutation score `>= 80%`, strict `decisions.tsv` audit | Tampered HMAC / Post-Red test edit / Mutation fail: `Must fix`; Invalid log: `Should fix` (`Must fix` under `--strict-solo`) |
| **5. Beyond-the-Diff Callers & Cycles** | Diff signature deltas + `CallGraphIndexer` + `DependencyCycleSolver` | Broken downstream call sites (`file:line`), circular module imports, high `fan_in >= 15` without caller tests | Broken caller / Cycle: `Must fix`; High fan-in untested: `Should fix` |
| **6. 6-Pillar AST + 4-Angle `simplify`** | Unified git diff + touched file AST | Multi-line swallowed exceptions, mutable defaults, `shell=True`/`eval`/`exec`, static sleeps, non-monotonic `time.time()` timeouts, deep nesting (`> 4`), `OutputDiffSentinel` rewrites, `HumanizeLinter` AI slop | Security/Swallowed/Mutable/Fake test: `Must fix`; Flaky/Nesting/Clock: `Should fix`; Dead comments/Slop: `Nice to have` |
| **7. Signed Review Receipt** | Aggregated verdict + local HMAC key | Atomic write of HMAC-signed `reports/code_review_receipt.json` (`--receipt-out`) | `APPROVED` (`0`), `APPROVED_WITH_NOTES` (`0`, or `1` under `--strict`), `CHANGES_REQUESTED` (`1`) |

---

## 4-Angle `simplify` Cleanup Lenses

Every `/review` pass checks whether the diff can be made smaller and clearer without changing behavior:
1. **Reuse First:** Flag duplicate helpers that re-implement existing `tools/` or stdlib utilities.
2. **Structural Clarity:** Flag functions nested `> 4` control-flow levels deep and recommend early-return guard clauses.
3. **Lean Diff & Anti-Bloat:** Flag commented-out dead code, unused variables, and monolithic full-file rewrites (`OutputDiffSentinel`).
4. **Human Technical Prose:** Flag stock AI buzzwords and filler cliches in added Markdown (`HumanizeLinter`).

---

## Verdict & Handoff Protocol

- **`APPROVED` (Exit `0`):** Zero `Must fix`, `Should fix`, or `Nice to have` findings; Plan alignment and `/solo` provenance verified. Ready to harvest (`agent-qa harvest-plan`) or merge.
- **`APPROVED_WITH_NOTES` (Exit `0`; Exit `1` under `--strict`):** Zero `Must fix` blockers; advisory `Should fix` or `Nice to have` items documented with concrete minimal fixes.
- **`CHANGES_REQUESTED` (Exit `1`):** One or more `Must fix` blockers (or `Should fix` under `--strict`). Hand findings back to `/solo` for targeted fixes and re-run `/review` until certified.
