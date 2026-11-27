<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

---
name: review
version: 2.1.0
category: verification_and_resilience
description: Closed-Loop Post-Code Adversarial Reviewer (v2.1) reconciling /solo code, AST diffs, downstream callers, and HMAC receipts against /super-plan contracts with 4-Angle simplify cleanup lenses.
policies:
  network: none
  shell: read-only
  filesystem: read-only
---

# /review (Closed-Loop Post-Code Adversarial Reviewer & Plan-vs-Solo Auditor - v2.1)

> **Core Objective:** Act as an independent, zero-trust senior engineer auditing `/solo` implementation diffs and forensic receipts against `/super-plan` contracts before merge or handoff.
> **Unified CLI:** `agent-qa review` (`python3 tools/orchestration/senior_code_review.py`) | **Auditor Engine:** `tools/orchestration/plan_review_auditor.py`

---

## Strict Read-Only Diagnostic Boundary

- **Zero Auto-Edits:** `/review` operates in strict **DIAGNOSTIC (read-only)** mode. NEVER modify user source code, tests, or plans during `/review`.
- **Read-Only Key Lookup & Optional Zero-Write Mode:** HMAC verification uses `get_receipt_hmac_key_readonly()` so `/review` never generates `.git/synapse_receipt_hmac.key` on disk during read-only inspection. Signed review receipts (`reports/code_review_receipt.json`) are written when `--plan`, `--strict-solo`, or `--receipt-out` is passed; pass `--no-receipt` for strict zero-write diagnostics, and `--baseline-files <files...>` to exclude known pre-existing dirty files from unplanned scope-creep findings.
- **Zero-Trust Verification:** Re-verify cryptographic HMAC signatures, post-Red SHA-256 `test_tree_hash` snapshots, AST DTO/class-method/return signatures, directory-scoped `-k` Verification Matrix commands (zero silent row skips), cross-drive plan paths, untracked `[CREATE]` files, and downstream callers directly from disk truth. Never trust self-reported agent text.
- **Collision-Free Scope:** `/review` audits post-implementation code diffs, PRs, and `/solo` deliveries. Specification, BRD, and Gherkin `.feature` stress-testing remains owned by `review-spec` (`skills/02-test-design/review-spec/SKILL.md`).

---

## 7-Layer Closed-Loop Audit Protocol

When `/review` is invoked, run the deterministic auditor first, then synthesize findings with exact `file:line`, failure scenario, and minimal fix:

```bash
# Formal closed-loop audit reconciling /solo against /super-plan (.synapse/plans/<slug>.md or implementation_plan.md)
agent-qa review --plan <plan_path> --strict-solo --json

# Single-milestone audit
agent-qa review --plan <plan_path> --milestone M1 --strict --json

# Ad-hoc uncommitted, staged, or branch diff review
agent-qa review --staged
agent-qa review --branch main --output-md reports/code_review.md --verify-cove
```

| Layer | Input Artifacts | Mechanical Checks | Severity Mapping |
|---|---|---|---|
| **1. Plan Scope & Write Set** | `--plan <plan.md>` Section 1 & 3 vs git diff (`HEAD` + untracked) / disk | Missing `[CREATE]`/`[MODIFY]` files, undeleted `[DELETE]` files, unplanned scope creep (including untracked files) | Missing/Undeleted: `Must fix`, Unplanned: `Should fix` (`Must fix` under `--strict`) |
| **2. DTO & Signature Drift** | `--plan` Section 2 vs Python AST | Missing classes/DTOs/methods/functions, parameter arity/name drift, bare `Any` param/return widening, unfrozen DTOs, milestone-scoped checks | Missing/Arity/`Any`: `Must fix`, Unfrozen DTO: `Should fix` |
| **3. Verification Matrix** | `--plan` Section 4 (`TC-01..TC-NN`) vs `tests/` & `.spec.ts`/`.test.js` | Missing test/spec files, boolean `and`/`or` `-k` test matching, empty tests (0 asserts), false & true tautologies (`assert True`, `assert False`) | Missing/Tautological/Empty: `Must fix` |
| **4. `/solo` Forensic Provenance** | `reports/solo_receipts/*`, `decisions.tsv` | Constant-time HMAC Red & Mutation receipts, `CERTIFIED_RED` + non-empty `test_tree_hash` check, bounded `AST_CONTRACT_VERIFIED` (`total_generated == 0`), missing mutation/decision log under `--strict-solo` | Tampered HMAC / Post-Red drift / Missing or failed mutation / Missing log: `Must fix` |
| **5. Beyond-the-Diff Callers & Cycles** | Multi-line `def` AST + `HEAD` + `CallGraphIndexer` + `DependencyCycleSolver` | Multi-line `def` signature breaks on imported receivers (`file:line`), `.py` & `pkg/__init__.py` circular imports, `fan_in >= 15` untested | Broken caller / Cycle: `Must fix`, High fan-in untested: `Should fix`, Scan cap note: `Nice to have` |
| **6. 6-Pillar AST + 4-Angle `simplify`** | Unified diff (tracked + untracked) + touched file AST | Multi-line swallowed exceptions, mutable defaults, `shell=True`/`eval`/`exec`, static sleeps, `time.time()` timeouts, body-edited nesting (`> 4`), unused imports, `OutputDiffSentinel` scoped to `target`, factual `--verify-cove` claim-vs-disk check | Security/Swallowed/Mutable/Fake pass: `Must fix`, Flaky/Nesting/Clock: `Should fix`, Unused import/Dead comments/Slop: `Nice to have` |
| **7. Signed Review Receipt** | Aggregated verdict + local HMAC key | Atomic write of HMAC-signed `reports/code_review_receipt.json` (`--receipt-out`) | `APPROVED` (`0`), `APPROVED_WITH_NOTES` (`0`, or `1` under `--strict`), `CHANGES_REQUESTED` (`1`) |

---

## 4-Angle `simplify` Cleanup Lenses

Every `/review` pass checks whether the diff can be made smaller and clearer without changing behavior:
1. **Reuse First:** Flag duplicate helpers that re-implement existing `tools/` or stdlib utilities.
2. **Structural Clarity:** Flag functions nested `> 4` control-flow levels deep and recommend early-return guard clauses.
3. **Lean Diff & Anti-Bloat:** Flag commented-out dead code, unused variables, and monolithic full-file rewrites (`OutputDiffSentinel`).
4. **Human Technical Writing:** Flag stock AI buzzwords and filler cliches in added Markdown (`HumanizeLinter`).

---

## Verdict & Handoff Protocol

- **`APPROVED` (Exit `0`):** Zero `Must fix`, `Should fix`, or `Nice to have` findings, with Plan alignment and `/solo` provenance verified. Ready to harvest (`agent-qa harvest-plan`) or merge.
- **`APPROVED_WITH_NOTES` (Exit `0`, or Exit `1` under `--strict`):** Zero `Must fix` blockers. Advisory `Should fix` or `Nice to have` items documented with concrete minimal fixes.
- **`CHANGES_REQUESTED` (Exit `1`):** One or more `Must fix` blockers (or `Should fix` under `--strict`). Hand findings back to `/solo` for targeted fixes and re-run `/review` until certified.
