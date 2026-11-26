<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0027: Closed-Loop `/review` v2.1 Hardening (Untracked Diff, True-Tautology Guard, Strict Solo & Multi-Line AST)

- **Status:** Accepted (DoD Certified)
- **Date:** 2026-11-26
- **Source Plan:** `implementation_plan.md`
- **Deciders:** Synapse Hub Autonomous Agent Core & Engineering Team

---

## Context & Problem Statement

Following ADR-0026 (`/review` v2.0), a deep audit of the closed-loop reviewer revealed concrete blind spots across diff ingestion, AST checks, `/solo` provenance enforcement, and Verification Matrix reconciliation:

1. `get_git_diff(..., "uncommitted")` used `git diff HEAD`, omitting newly created untracked `[CREATE]` files from AST inspection, scope-creep checks, and syntax/cycle auditing. `OutputDiffSentinel.audit_git_diff` also ignored `--staged` and `--branch` targets.
2. `AstTautologyAnalyzer` only flagged static `False` assertions (for `--red` anti-cheat), letting fake-pass assertions (`assert True`, `assert 1 == 1`) pass `/review` and Section 4 matrix checks undetected.
3. `--strict-solo` did not require a valid Mutation receipt or `decisions.tsv` when `M*_red.json` existed, accepted unsigned mutation receipts or unverified `AST_CONTRACT_VERIFIED` waivers with `total_generated > 0`, and `plan_dag_bridge.py` overwrote `M*_mutation.json` on multi-file milestones.
4. Layer 2 & 5 missed class methods, return-type widening, multi-line `def` signatures, `pkg/__init__.py` import cycles, and receiver-scoped call-site matching.
5. `--verify-cove` audited exported Markdown review reports against themselves via code/test CoVe rules instead of verifying cited `file:line`, verdict, and finding-count claims against disk truth.

---

## Decision Drivers & Invariants

1. **Zero Regression & Acyclic Layering:** Preserve `plan_review_auditor.py` isolation from `solo_runner.py` and keep all existing `cli_specs.json` / `tools_schema.json` flags zero-drift.
2. **True Read-Only Key Lookup:** Read existing HMAC keys via `get_receipt_hmac_key_readonly()` during `/review` without minting new `.git/synapse_receipt_hmac.key` files.
3. **Backward-Compatible Strictness:** Default `AstTautologyAnalyzer(flag_true_tautologies=False)` for `--red` anti-cheat, while `/review` and `plan_review_auditor` enable `flag_true_tautologies=True` (exempting `except` blocks). Standalone `solo_runner.py --purple` preserves existing `--red -> --purple` compatibility via `require_mutation_receipt=False`.

---

## Architectural Decisions (v2.1)

1. **Leaf Forensic & Diff Contracts (`solo_contracts.py`, `output_diff_sentinel.py`):**
   - Add `flag_true_tautologies`, `get_receipt_hmac_key_readonly`, `compute_mutation_receipt_hmac`, and `verify_mutation_receipt_hmac`.
   - Parameterize `OutputDiffSentinel.audit_git_diff(repo_root, target=...)` across `uncommitted`, `staged`, and branch refs.
2. **Core Diff, AST Simplify & Factual CoVe (`senior_code_review.py`):**
   - Synthesize bounded unified diffs for untracked files (`build_untracked_file_diff`), fix `\ No newline at end of file` line offsets and quoted paths in `parse_diff`, check body-edited functions for nesting `> 4`, flag unused top-level imports, guard dead-code comment checks to code files, and verify exported Markdown report claims against disk truth (`verify_review_markdown_claims`).
3. **Zero-Trust Reconciliation (`plan_review_auditor.py`):**
   - Audit class methods, `(file, symbol)` keys, return-type widening, and milestone-scoped Section 2 contracts.
   - Support polyglot test paths (`.spec.ts`/`.test.js`) and boolean `and`/`or` `-k` expressions in Section 4.
   - Enforce `MISSING_MUTATION_RECEIPT`, `MISSING_DECISION_LOG`, `TAMPERED_MUTATION_RECEIPT`, `INVALID_RED_RECEIPT`, and bounded `AST_CONTRACT_VERIFIED` (`total_generated == 0`) under `--strict-solo`.
   - Parse multi-line `def` signatures (`HEAD` AST + paren-balanced diff parser), resolve `pkg/__init__.py` cycles, and scope call-site checks to imported receivers.
4. **Bridge Aggregation & Mutation Signing (`plan_dag_bridge.py`, `solo_runner.py`):**
   - Aggregate multi-file milestone mutation results via `_aggregate_milestone_mutation_results` into a single HMAC-signed `M*_mutation.json` receipt (`AggregatedMutationReceiptDTO`), and sign standalone `certify_mutation_phase` receipts.

---

## Verification & Guarantees

- `tests/test_senior_code_review.py`, `tests/test_review_plan_solo_reconciliation.py`, `tests/test_plan_dag_solo_bridge.py`, and `tests/test_solo_runner.py` verify positive, negative, boundary, and CLI/resilience scenarios.
- Live dynamic mutation testing achieves `>= 80.0%` across `senior_code_review.py`, `plan_review_auditor.py`, and `plan_dag_bridge.py`.
