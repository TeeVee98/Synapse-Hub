<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0029: Manual QA Pipeline Profile (`--profile manual`) for `/super-plan`, `/solo`, and `/review`

- **Status:** Accepted
- **Date:** 2026-11-27
- **Author:** Thế Vị (@TeeVee98)
- **Scope:** `tools/manual/manual_pipeline_adapter.py`, `tools/lint/plan_schema_sentinel.py`, `tools/design/super_plan_engine.py`, `tools/orchestration/solo_runner.py`, `tools/orchestration/plan_dag_bridge.py`, `tools/orchestration/plan_review_auditor.py`, `tools/orchestration/senior_code_review.py`

## Context

The closed-loop `/super-plan` -> `/solo` -> `/review` control plane was originally coupled exclusively to source-code artifacts (`.py`, `.ts`, `.js`, `.groovy`, `.java`), Python AST DTO checks, `pytest` / JS test runners, and syntactic code mutation (`micro_mutator.py`). Running these commands directly on Manual QA workflows (BRD analysis, ISO/IEC/IEEE 29119-3 Markdown/Excel test suites, RTM traceability) produced false-positive rejections (`FAKE_RED_REJECTED`, `UNVERIFIABLE_MATRIX_ROW`, `MISSING_SOLO_RECEIPTS`).

Meanwhile, Synapse Hub already ships deterministic Manual QA sensors:
- `tools/lint/manual_tc_linter.py` (12/13-column ISO 29119-3 structure, vague oracle blacklist, Golden Ratio 40/40/20)
- `tools/orchestration/goldfish_review.py` (`--mode brd` zero-context specification review)
- `tools/manual/checklist_query.py` (25 canonical input field validation rules & resilience invariants)

## Decision

Introduce an additive, backward-compatible `--profile manual` mode across `/super-plan`, `/solo`, and `/review`, routed through a single **leaf adapter module** (`tools/manual/manual_pipeline_adapter.py`):

1. **Strict Leaf Acyclicity:** `tools/manual/manual_pipeline_adapter.py` composes only leaf sensors (`manual_tc_linter`, `goldfish_review`, `checklist_query`, `solo_contracts`) and never imports `solo_runner`, `plan_review_auditor`, `senior_code_review`, or `super_plan_engine`.
2. **Backward-Compatible Defaults:** All generators/runners default to `profile="code"` and all validators/reviewers default to `profile="auto"` (resolving to `"code"` unless `Profile: manual` is explicitly declared in the plan). Existing callers (`fan_in=61`) require zero changes.
3. **Manual Red -> Green -> Spec-Mutation Receipts:**
   - **Red Phase (`--profile manual --red --spec <brd.md>`):** Computes SHA-256 `spec_hash` and locks extracted `AC-`/`REQ-` IDs in an HMAC-signed receipt so requirements cannot be silently dropped.
   - **Green Phase (`--profile manual --green`):** Verifies `manual_tc_linter.py` pass status, 100% requirement RTM linkage, zero orphan TCs, and 25-field negative/boundary coverage.
   - **Purple / Mutation Phase (`--profile manual --mutation`):** Runs deterministic fault-injection **Spec-Mutation** (omission, boundary inversion, RBAC/IDOR bypass, OTP lockout bypass, double-submit race, field chaos) with bilingual English and ASCII-folded Vietnamese token matching, enforcing a kill score `>= 80.0%` with HMAC-signed receipt.
4. **Zero-Trust Manual Review (`/review --profile manual`):** Reconciles write sets, AC coverage, linter defects, read-only HMAC provenance (`get_receipt_hmac_key_readonly()`), and Spec-Mutation score into a signed `reports/code_review_receipt.json`.

## Consequences

- **Positive:** Manual QA teams gain the same closed-loop rigor, ambiguity gating, anti-tamper receipts, and independent `/review` governance as automation engineers without creating a fragmented second CLI.
- **Trade-off:** Static Spec-Mutation evaluates deterministic keyword/rule coverage over Markdown tables; deep domain logic edge cases should still be paired with `review-spec` and `tot-exploratory-testing`.
