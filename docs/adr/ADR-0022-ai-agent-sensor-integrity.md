<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0022: AI & Agent Evaluation Sensor Integrity Hardening

- **Status:** Accepted
- **Date:** 2026-11-25
- **Deciders:** Thế Vị (@TeeVee98), Enterprise QA Architecture Review

## 1. Context & Problem Statement

An end-to-end audit of Synapse Hub's five AI and Agent evaluation sensors (`verify_all.py`, `harness_sentinel.py`, `eval_runner.py`, `agent_canary.py`, `ai_eval_sentinel.py`, and `synapse_qa_bench.py`) revealed critical Truth-Anchor (Invariant 2) and isolation defects:
1. **Silent Fallback & File-Race Defects in Harness Scoring:** `EvalRunner.run_harness_readiness()` invoked a non-existent `HarnessSentinel.audit_all()` method and caught the resulting exception by returning a synthetic `100.0` score. `EvalRunner.run_quality_gates()` re-read the global `reports/verify_all_report.json` file on disk instead of receiving gate outputs in memory, creating concurrency races, while `compute_composite_score()` applied a hardcoded `95.58` mutation fallback and a `0.0` cliff for `s_tests` in `--tier fast`.
2. **Shallow File-Existence Probes:** `HarnessSentinel` Steps 2 and 6 checked only `os.path.exists()` for `infer_linter.py`, `fact_forcing_gate.py`, `token_estimator.py`, and `distill_log.py` rather than executing callable smoke probes.
3. **Subpackage Path Drift & Simulated Checks in Agent Canary:** `agent_canary.py` referenced legacy flat paths (`browser_helpers.js`, `verify_all.py`, `.agents/skills/clean-pom-crafter/SKILL.md`) and `import cache_resolver`, stalling at `75.0%` (`Level 4.5`) while leaving `V6_PATH_LEAK` and `V7_CLEAN_POM` as string-only simulations.
4. **Vacuous Zero-Turn & Fail-Open Transcript Auditing:** `ai_eval_sentinel.audit_agent_transcript()` returned `100.0%` (`is_trustworthy = True`) on zero-turn transcripts, allowed prompt injections to pass `is_trustworthy` when faithfulness was high, ignored `SYSTEM_MESSAGE` and `transcript_full.jsonl` hydration on `truncated_fields`, left system envelope tags in `USER_INPUT`, and flagged intermediate `tool_calls` progress turns as `FAIL_IRRELEVANT`.
5. **Closed-Set 3-Tool Toy Resolution:** `synapse_qa_bench.py` scored only 3 candidate tools per case with unweighted token overlap and lacked out-of-domain abstention test cases.

## 2. Considered Options & Rulings

1. **Ruling 1 — Full 5-Sensor Remediation & Open-Pool Retrieval:**
   - Remediated all five evaluation sensors plus `verify_all.py`, upgrading `HarnessSentinel` Steps 2 and 6 to callable smoke probes, fixing `agent_canary.py` subpackage paths and Clean-CI SQLite seeding, converting `V6_PATH_LEAK` and `V7_CLEAN_POM` to real temporary-file sanitization checks (`Level 5.0`), and expanding `synapse_qa_bench.py` to IDF-weighted retrieval with out-of-domain abstention across the full catalog/schema pool (`>= 205` tools).
2. **Ruling 2 — In-Memory Gate DTO & Proportional Fast-Tier Proxy:**
   - Added `verify_all.run_all_gates_detailed(..., report_path=None) -> Tuple[int, Dict[str, Any]]` while keeping `run_all_gates() -> int` 100% compatible across all `91` callers.
   - Wired `EvalRunner` to consume the in-memory bundle, invoke `HarnessSentinel.run_full_audit()` with fail-closed `0.0` error handling, compute `s_tests` proportionally from `s_gates` with explicit `tests_measurement_mode="static_fast_proxy"` under `--tier fast`, remove the `95.58` magic fallback (fail closed to `0.0`), and render dynamic `11/11` gate counts.
3. **Ruling 3 — Fail-Closed Multi-Turn Transcript Auditing:**
   - Hardened `ai_eval_sentinel.py` with `sanitize_user_query_envelope()`, line-streaming `load_full_transcript_steps()` (capped at `16 KB` per `step_index`), `SYSTEM_MESSAGE` ingestion, intermediate `tool_calls` progress-turn relevance exemption, `INCONCLUSIVE` (`is_trustworthy = False`) on zero turns, and fail-closed `is_trustworthy = False` plus CLI `--gate-safety` exit `1` on security injection or hallucination verdicts.

## 3. Consequences

- **Positive:** Eliminates silent fake passes across all five AI/Agent evaluation sensors, prevents `verify_all_report.json` concurrency races, raises `agent_canary.py` to verified `Level 5.0` (`8/8`, `100%` DoD compliant), and enforces realistic open-pool function-calling and abstention rigor.
- **Trade-offs:** Transcripts with zero spoken planner turns or ungrounded numeric claims without matching `transcript_full.jsonl` hydration now fail closed as `INCONCLUSIVE` / `FAIL`, and fast-tier `EvalRunner` runs explicitly surface `static_fast_proxy` telemetry rather than asserting full Pytest execution.
