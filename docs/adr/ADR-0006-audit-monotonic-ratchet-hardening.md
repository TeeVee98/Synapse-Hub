<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0006: Synapse Hub Audit Remediation & Monotonic Ratchet Hardening

- **Status:** Accepted (DoD Certified)
- **Date:** 2026-11-24
- **Source Plan:** [implementation_plan.md](../../implementation_plan.md)
- **Audit Baseline:** Commit `8060843beafc41c74a51699d99222f93384f24e8`
- **Deciders:** Synapse Hub Autonomous Agent Core & Engineering Team

---

## Context & Problem Statement

A comprehensive architectural audit of Synapse Hub identified mechanical enforcement and telemetry honesty gaps across five pillars (arithmetic mean `67.6/100`), spanning:
1. Rollback and scope-guard fail-open edge cases (`P0.1`).
2. Unsigned / unverified TDD Red receipts and missing retry circuit breaker integration (`P0.2`).
3. Absence of an isolated execution sandbox for tests and mutants (`P0.3`).
4. Red scenario coverage gaps, silent diff-only fallback to full-file mutation, disconnected `super-plan` lifecycle stages, fail-open FSM/semantic entropy guards, and shallow CLI schema drift checks (`P1.1`–`P1.5`).
5. Stale "10 Gates" terminology, hardcoded `/ 3.8` character heuristics, unmeasured schema compression claims, unbounded `ContextSlicer` payloads, and missing pre-prune checksum checks (`P2.1`–`P2.5`).

---

## Decision Drivers & Invariants

- **Fail-Closed Verification Invariant:** Any unverifiable git state, tampered receipt, failed analysis, or unrecognized workflow action must fail closed rather than pass silently.
- **Cryptographic Binding & Isolation Invariant:** Verification receipts bind to exact commit, command, and test snapshots; tests/mutants execute in ephemeral sandboxes before artifact promotion.
- **Scientific Honesty Invariant:** Separate measured disk/heuristic telemetry (`provider_observed=false`) from provider-reported billing usage (`provider_observed=true`), and separate `production_active` tiers from `research_simulation` modules.
- **Stdlib-First Baseline (`AGENTS.md §0.3`):** Zero mandatory external runtime dependencies for local execution, with opt-in hardening where available.

---

## Architectural Rulings

### 1. Pluggable Ephemeral Sandbox (`WorktreeSandbox` Default + Opt-In `DockerSandbox`)
- Selected stdlib `WorktreeSandbox` (ephemeral copy / `git worktree` with scrubbed `HOME`/`TMPDIR`/`SYNAPSE_SANDBOX=1` and post-pass artifact promotion) as the default backend, with opt-in `DockerSandbox` (`--sandbox worktree|docker|host`) for strict container isolation.
- Preserves zero-dependency local/CI ergonomics while eliminating reliance on `chmod 0o444` as a security boundary.

### 2. Cryptographically Signed Red Receipts & Circuit Breaker Guardrails
- `certify_red_phase()` signs canonical `{status, certified_at, commit_hash, normalized_cmd, executed_tests, test_tree_hash, failure_sha256, ttl_seconds}` via HMAC-SHA256.
- `certify_green_phase()` rejects tampered, expired, or wrong-commit receipts and enforces strict command matching, wired to `LocatorRetryCircuitBreaker` (tripping after 2 consecutive strikes).

### 3. Fail-Closed FSM Middleware & Semantic Entropy Guard
- `FsmMiddleware.check_precondition()` rejects unrecognized actions (`UNKNOWN_ACTION_BLOCKED`) whenever an active controlled FSM workflow is in progress, while keeping uninitialized/uncontrolled mode backward-compatible.
- `SemanticEntropyEngine` exceptions fail closed (`semantic_entropy=None`, `uncertainty_status="ERROR_REVIEW_REQUIRED"`, `code_write_permission=False`).

### 4. Deep CLI Schema Sentinel & 157-Helper Classification
- `tools/lint/cli_schema_sentinel.py::validate_schema_drift()` verifies field-level parity (`type`, `required`, `default`, `choices`) against AST code truth and supports `excluded_internal_tools` metadata in `tools/tools_schema.json`.
- `--fail-unregistered` deterministically rejects any unclassified public CLI tool while cleanly excluding the 157 inventoried internal helpers.

### 5. Honest Hybrid Token Telemetry & Hard-Capped Context Slicing
- Replaced hardcoded `/ 3.8` character heuristics in `CachePrefixEnforcer` and `gate_11_token_reduction.py` with `tools/core/token_estimator.py::count_tokens` + `get_estimator_info()` (optional `tiktoken cl100k_base` with calibrated `3.85`/`1.80` polyglot fallback) tagged `provider_observed=False`.
- Gate 11 directly measures `tools/tools_schema.json` vs `tools/tools_schema.min.json` compression on disk and reports `production_active` (`9/9`) separately from `research_simulation` (`6/6`).
- `ContextSlicer.slice_context()` enforces optional `max_tokens` hard ceilings (closing fenced code blocks cleanly before truncation markers), and `TaskMemoryManager.check_compaction_trigger()` requires pre-prune SHA-256 disk integrity verification (`verify_integrity()`) before allowing context pruning.
- Aligned all `verify_all.py`, `tools_schema.json`, and `.github/workflows/ci_quality_gates.yml` references to **11 Quality Gates** and added the `audit-ratchet-verification` CI job.

---

## Consequences

- **Positive:** Eliminates silent fallbacks and stale heuristics across schema validation, token telemetry, context slicing, and compaction safety; enforces ratchet checks in CI via `audit-ratchet-verification`.
- **Trade-offs / Notes:** Synthetic test fixtures calibrated to `/ 3.8` character ratios must account for exact `cl100k_base` BPE token counts when `tiktoken` is installed; `tools/tools_schema.json` requires `--sync` or `excluded_internal_tools` updates whenever new argparse CLIs are added under `tools/`.
