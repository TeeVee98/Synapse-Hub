<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Historical v4 Implementation Plans Archive

This archive merges the completed v4.x engineering implementation plans relocated from the repository root (`tests/test_super_plan_and_harvester.py` uses a self-contained inline 6-node fixture instead of a root plan file).

---

## 1. `implementation_plan_audit_remediation.md` (Archived)

- **Scope:** Audit Remediation — Hermetic Skill Isolation & KV-Cache Telemetry Sentinel (`Tier 1`, `RiskScore = 0.473`).
- **Governing Rulings:**
  1. Preserved `tools/core/skillspector.py` rule `AS3` without regex relaxation (Invariant 11), rewording `skills/08-code-quality/surgical-coding-principles/SKILL.md` to reference `/solo` conceptually and updating `skills-lock.json` SHA-256 digests.
  2. Wired `--check-latest` / `--strict` in `tools/core/kv_cache_sentinel.py` and normalized `audit_transcript_file` prompt token denominators.
  3. Certified with 4-scenario `tests/test_audit_skills_and_kv_sentinel.py`.

## 2. `implementation_plan_qc_readiness.md` (Archived)

- **Scope:** QC Team Readiness Upgrade (`v4.9.1` Prep, `DEEP_SUPER_PLAN`, `RiskScore = 0.40`).
- **Governing Rulings:**
  1. Normalized Windows `python3` / `WindowsApps` stub resolution in `tools/orchestration/solo_runner.py` (`BaseTestAdapter.execute`).
  2. Certified Windows NTFS junction compatibility in `tests/test_architectural_hardening.py` and Gate 6 Telegram bot token detection.
  3. Delivered bilingual 1-pager `docs/QC_QUICKSTART.md` & `docs/QC_QUICKSTART.en.md` and aligned onboarding install instructions.

## 3. `implementation_plan_ai_agent_eval.md` (Archived)

- **Scope:** AI & Agent Evaluation Sensor Integrity Hardening (`P0 + P1 + P2`, `Tier 2`, `RiskScore = 0.70`, `ADR-0022`).
- **Governing Rulings:**
  1. Hardened all 5 AI/Agent evaluation sensors (`eval_runner.py`, `agent_canary.py`, `ai_eval_sentinel.py`, `synapse_qa_bench.py`, `harness_sentinel.py`), raising `agent_canary.py` to `100.0%` (`Level 5.0`) and enabling open-pool CLI retrieval.
  2. Introduced in-memory gate DTO handoffs from `verify_all.py`, removing shared JSON file races and synthetic `95.58` mutation fallbacks.
  3. Enforced fail-closed multi-turn transcript auditing (`is_trustworthy = False` on zero turns, hallucination, or prompt injection).

## 4. `implementation_plan_phase2_wiring.md` (Archived)

- **Scope:** Phase 2 Adapter & CLI Wiring (`DEEP_SUPER_PLAN`, `RiskScore = 0.749`, `FanIn = 72`, Milestones `M1`–`M6`).
- **Governing Rulings:**
  1. Wired `BM25Index`, `ActionBundler`, and `CodeActEngine` into `MetaToolEngine` / `SynapseMetaMCPServer` while preserving `< 350`-token MCP schemas.
  2. Wired `SchemaMinifier`, `kv_cache_sentinel`, `ContextCachingProxy`, `ChainOfVerificationEngine`, `OutputDiffSentinel`, `QAMemoryOS`, `FederatedKnowledgeLake`, `SelfHealingDAGExecutor`, `plan_harvester`, and `TextGradOptimizer` into live Hub entrypoints and `cli_specs.json`.
  3. Replaced the root file dependency in `tests/test_super_plan_and_harvester.py` with a self-contained inline 6-node fixture before removing the root file.
