<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0032. Fail-Closed Release Acceptance Hardening for v4.11.0

**Status:** Accepted. **Date:** 2026-11-28. **Extends:** [ADR-0031](ADR-0031-release-readiness-evidence.md). **Decision owners:** Hub maintainer and QA lead.

## Context

Following the baseline evidence architecture established in `ADR-0031`, the v4.11.0 release readiness audit uncovered six fail-open or silent-degradation loopholes across packaging, traceability reporting, CI acceptance gates, pilot scorecards, held-out model evaluation, and support-matrix versioning:

1. **Packaged Model Catalog Drift:** `package.json` omitted `models_manifest.json`, `pyproject.toml` and `MANIFEST.in` omitted `models_manifest.json` and `synapse.config.json`, and `ModelRegistry` resolved only `_REPO_ROOT`. Clean client installations silently degraded from 18 canonical models to an 11-model built-in fallback. In addition, `.github/workflows/publish_npm.yml` lowered `--cov-fail-under=65` below `pyproject.toml`'s canonical `fail_under = 70`.
2. **Coarse Excel RTM Reconciliation:** `compare_workbook_semantics` verified disposition counts but did not reconcile all five `_WRITTEN_TRACE_ROLES` (`requirement_id`, `document_version`, `source_anchor`, `disposition`, `candidate_build`) cell-by-cell on reopen or flag formula-blocked trace writes.
3. **Fail-Open Release-Candidate Manifest & Static Claims:** `validate_candidate_manifest` skipped producer checks whenever `producers` was omitted (`None`), `rc-evidence-lane` emitted a producer-less manifest, shard matching ignored relative artifact directories, and `ci_summary_generator.py` printed static `"100% verified"` invariant claims even on empty artifact directories.
4. **Synthetic Pilot Checksums & Baseline Ambiguity:** `release_pilot.py` accepted arbitrary non-empty strings (such as `"r1"`) as `receipt_sha256` without verifying 64-hex format or on-disk artifact bytes, and surfaced only `achieved_total` (`67/100` on an empty manifest) without distinguishing `verified_total` (`0/100`).
5. **ID-Only Evaluation Digest:** `benchmarks/qa_eval/live_evaluation.py::compute_dataset_digest` hashed only bare `task_ids`, allowing prompt text or rubric edits without altering `dataset_digest`, and lacked per-category (`plan`, `code`, `review`) rollups.
6. **Stale Verified Support Claims:** `docs/CLIENT_SUPPORT_MATRIX.md` lagged at `4.10.0` because `check_version_sync.py` did not audit `Verified` package rows.

## Decision

Adopt Branch B (**Clean Fail-Closed Evidence Contracts**) with zero external runtime dependencies:

1. **Packaging & Registry Parity:** Ship `models_manifest.json` and `synapse.config.json` across npm (`package.json`), wheel (`pyproject.toml`), and sdist (`MANIFEST.in`), resolve packaged resources deterministically via `resolve_packaged_resource_path` (`explicit_path` -> `_REPO_ROOT` -> `_TOOLS_ROOT` -> `importlib.resources`), enforce 18-model parity across source, npm `.tgz`, and `.whl` clean installs in `tests/test_packaging_parity.py`, and remove the `--cov-fail-under=65` override from `publish_npm.yml`.
2. **Cell-by-Cell Excel Reconciliation:** Reconcile every mapped column in `_WRITTEN_TRACE_ROLES` per `case_id` in `compare_workbook_semantics`, emitting structured `cell_mismatches` records (`{sheet, cell, row, case_id, role, expected, actual}`) and failing `reconciled`/`passed` whenever any cell or formula-blocked trace write drifts.
3. **Fail-Closed RC Manifest & CI Summary:** Require a non-empty `producers` mapping covering all `REQUIRED_RC_PRODUCERS` with live (non-`offline`) modes and matching build/run identifiers in `release-candidate` lane; match relative shard directory paths with `--expected-shards`; populate bound staging producers in `ci_quality_gates.yml`; and render honest `"Unverified"` / `"Not configured (unverified)"` invariant lines whenever static gate artifacts or expected shards are absent.
4. **Physical Artifact SHA-256 & Verified Score Separation:** Enforce 64-character lowercase hex SHA-256 digests in `release_pilot.py`, stream-hash referenced on-disk `artifact_path` files (`65536`-byte chunks) to reject 1-byte tampering or missing files (`--verify-artifacts`), and report `verified_total` separately from `audit_total` and `achieved_total`.
5. **Content-Addressed Evaluation Digest:** Hash canonical structured `tasks` (`task_id`, `category`, `prompt`, `expected_criteria`) and `rubric` payloads in `compute_dataset_digest` and `compute_rubric_digest`, reject manifest digest drift (`manifest_digest_mismatch`), and emit per-category (`plan`, `code`, `review`) metrics.
6. **Support Matrix Version Guard:** Synchronize `Verified` CLI package rows in `docs/CLIENT_SUPPORT_MATRIX.md` to `4.11.0`, keep IDE and screen-reader rows honestly `Configuration Only` / `Pending` until live human receipts exist, and enforce `Verified` row version parity in `tools/core/check_version_sync.py`.

## Alternatives and Consequences

- **Minimalist Patch (Rejected):** Fixing only `package.json` and truthy `producers` leaves wheel installs, Excel cell traceability, physical pilot checksums, and prompt/rubric drift unguarded.
- **External Attestation Service (Rejected):** Violates the stdlib-first air-gapped design constraint (`AGENTS.md` §0.3).
- **Consequence:** All software, packaging, and validation gaps are closed offline with deterministic unit and mutation gates, while live operational ceremonies (staging `workflow_dispatch`, live Codex host transcript, supervised VoiceOver/NVDA sign-off, and live multi-provider LLM eval runs) remain explicit operator actions that cannot be fabricated offline.

## Adoption and Reversal

All new optional keyword arguments (`expected_case_traces`, `require_producers`, `base_dir`, `verify_artifacts`, `rubric`) preserve backward compatibility for existing callers. New CLI flags (`--expected-shards`, `--verify-artifacts`) are synchronized in `tools/tools_schema.json`. Each milestone can be reverted independently using its path-scoped rollback hook without disturbing unrelated domains.
