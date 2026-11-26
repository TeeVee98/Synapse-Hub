<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0025: AI Cognitive Reasoning, Skill Routing & Tool-Calling Precision Upgrade

- **Status:** Accepted & Implemented
- **Date:** 2026-11-26
- **Author:** Thế Vị (@TeeVee98)
- **Execution Mode:** Single-Agent Sequential (`/solo` v2.0 — `M1 -> M2 -> M3 -> M4 -> M5 -> M6`)
- **Reference Plan:** `implementation_plan.md` (`Tier 2: DEEP_SUPER_PLAN`, `RiskScore = 0.78`)

---

## 1. Context & Empirical Baseline Deficiencies

Empirical auditing across Synapse Hub's AI Cognitive Engines (`8.8/10`), Skill Routing (`7.6/10`), and Tool Catalog / BFCL Tool-Calling Parity (`8.3/10`) identified 9 concrete precision blindspots:

1. **Bilingual EN/VI Cognitive Parity Gap:** Vietnamese prompts describing distributed concurrency, double-click payment races, DB locks, auth token refresh, or load saturation failed to trigger `DISTRIBUTED_CONCURRENCY`, `MOD_CONCURRENCY_RACE_MODELING`, `PRO_REASONING`, or `PlanningTier.TIER_2_DEEP` because keyword/regex matchers were ASCII-English-only.
2. **Vietnamese Negation Blindspot in Ambiguity Gate:** `super_plan_engine.check_ambiguities()` only recognized English negation prefixes (`without`, `avoid`, `no`), missing Vietnamese negations (`không dùng redis`, `tránh dùng`).
3. **Turn-1 File-Less Skill Routing Gap:** `skill_router.evaluate_skill_first_trigger()` returned `recommended_skill=None` when `target_files=[]` even on explicit domain actions (`"Generate boundary API test matrix from OpenAPI spec"`).
4. **Incomplete Action Verb Taxonomy & Local Skill Indexing:** `ACTION_PATTERNS` omitted `generate`, `design`, `mock`, `heal`, `transpile`, and `export`, and `.agent/skills/*` (`solo`, `super-plan`) were not dynamically unified with `skills_index.json` for `/slash` lookup.
5. **False `destructive` Tagging (`s-kill` Substring Bug):** `generate_tool_catalog.py` matched `"kill" in lower_name`, falsely labeling `*skill*.py` tools (e.g., `skill_vault.py`, `distill_skill.py`, `skill_collision_guard.py`) as `destructive`.
6. **Generic Catalog Metadata & Banner Docstrings:** Unregistered catalog tools defaulted to `inputs=["CLI options"]`, `category="Auxiliary Utilities"`, and separator-banner first lines (`"==========..."` in `check_env.py`).
7. **MetaToolEngine Registry Coverage & Numeric Domain Prefix Hijacking:** `MetaToolEngine` only loaded the 81 entries from `tools_schema.min.json` (hiding 85+ tools in `TOOL_CATALOG.json`), missed `.agent/skills/*`, lacked bilingual query normalization, and indexed `"11-ai-and-prompting"` verbatim so bare `"11"` hijacked BM25 ranking.
8. **BFCL Sibling Disambiguation Failure (`TC-BENCH-07`):** `SynapseQABench` selected `omni_parser.py` instead of `omni_transpiler.py` (`95.0%` overall score, `90.0%` tool selection accuracy) due to missing verb-to-agent-noun alignment (`transpile -> transpiler`).
9. **Dishonest `args_valid` Attribution on Wrong Tool Selection:** `SynapseQABench.run_benchmark()` validated `valid_args` against `expected_tool` rather than `selected_tool`, masking flag mismatches when the wrong sibling tool was chosen.

---

## 2. Architectural Decision (Tournament Ruling)

| Criterion | Branch A: Ad-Hoc Regex Patches | Branch B: Unified Stdlib Bilingual Lexicon & Dual-Registry Bridge | Branch C: External Dense Embedding Sidecar |
|---|---|---|---|
| **Blast Radius** | Fragmented across 6 duplicated tables | Modular (`1` shared normalizer + surgical adapters across `8` modules) | Invasive (`+400MB` ML runtime, violates Stdlib-first) |
| **Determinism & Latency** | Medium (drift across modules) | **100% deterministic offline `< 5ms`, zero external deps** | Non-deterministic threshold drift |
| **Score & Verdict** | 6.45 — Rejected | **9.35 — Selected (Recommended)** | 5.80 — Rejected |

**Ruling:** Selected **Branch B** (`tools/core/bilingual_intent_normalizer.py` + Turn-1 global 59-skill scorer + AST-enriched catalog & `TOOL_CATALOG.json` bridge + action-role disambiguator).

---

## 3. Implemented Architecture & Write Set

- **M1 — `tools/core/bilingual_intent_normalizer.py`:** Zero-dependency `O(N)` stdlib normalizer exporting immutable `NormalizedIntentDTO`, `normalize_bilingual_intent()`, `normalize_bilingual_text()`, `strip_vietnamese_diacritics()`, and `extract_slash_skill()`. Bounded to `8,192` chars with `MappingProxyType` lexicons and CLI `--json` output.
- **M2 — `tools/reasoning/step_back_engine.py`, `self_discover_engine.py`, `qa_model_router.py`:** Wired `normalize_bilingual_intent` / `normalize_bilingual_text` so Vietnamese concurrency/auth/performance/RCA prompts match English principles, atomic modules, and `PRO_REASONING` routing while keeping lightweight Vietnamese triage at `FLASH_LITE`.
- **M3 — `tools/design/super_plan_engine.py`, `tools/core/skill_router.py`:** Upgraded `tokenize_text`, `calculate_risk_routing`, and negation-aware `check_ambiguities` for EN/VI parity; expanded `skill_router` action verbs, unified 59-skill indexing (57 `skills_index.json` + `.agent/skills/*`), `/slash` command resolution, and Turn-1 file-less ranking gated by `MIN_FILELESS_CONFIDENCE_SCORE = 4`.
- **M4 — `tools/report/generate_tool_catalog.py`, `tools/runtime/meta_tool_engine.py`:** Replaced substring risk inference with delimited word-token matching (`re.split(r"[_\-.]+", lower_stem)`), added AST `add_argument` flag extraction, subdirectory category mapping, and banner docstring sanitization (`infer_tool_risk_and_cli_metadata`, `CatalogRiskAuditDTO`). Merged `TOOL_CATALOG.json` (`166+` tools), `.agent/skills/*`, bilingual query normalization, and numeric domain-prefix stripping in `MetaToolEngine`.
- **M5 — `tools/orchestration/synapse_qa_bench.py`:** Added `score_action_aligned_tool_candidates()` with verb-to-agent-noun bonus (`transpile -> transpiler`, `emit -> emitter`, `parse -> parser`) and bilingual clean-token extraction; fixed `run_benchmark()` and `_validate_args_ast()` to validate requested flags honestly against `selected_tool`.

---

## 4. Empirical Before / After Verification Metrics

| Verification Metric | Before Upgrade | After Upgrade | Evidence Sensor |
|---|---|---|---|
| **BFCL Overall Score (`synapse_qa_bench.py --json`)** | `95.0%` (`90.0%` selection; TC-BENCH-07 mismatch) | **`100.0%` (`100.0%` selection, `100.0%` AST args, `100.0%` irrelevance)** | `python3 tools/orchestration/synapse_qa_bench.py --json` |
| **False `destructive` Tags on `*skill*.py`** | `> 0` (`s-kill` substring bug) | **`0` across 166 cataloged tools** | `tests/test_tool_catalog_and_bfcl_precision.py` |
| **MetaToolEngine Tool Coverage** | `81` schema tools | **`>= 166` unified tools + 59 skills (`.agent/skills/*` included)** | `MetaToolEngine._tools_catalog` & `_skills_catalog` |
| **Live Dynamic Mutation Score (`bilingual_intent_normalizer.py`)** | N/A (new module) | **`94.1%` (16/17 killed >= 80.0%)** | `solo_runner.py --mutation` (`CERTIFIED_MUTATION`) |
| **Live Dynamic Mutation Score (`synapse_qa_bench.py`)** | Baseline | **`100.0%` (20/20 killed >= 80.0%)** | `solo_runner.py --mutation` (`CERTIFIED_MUTATION`) |
| **Purple Adversarial Self-Audit** | Pending | **`CERTIFIED_PURPLE` (`59` files analyzed, `0` critical findings, `0` cuttable lines)** | `solo_runner.py --purple --json` |
| **Regression & New 4-Scenario Suites** | Baseline | **`178/178` passed (`0` regressions)** | `pytest` across 12 targeted suites |
| **DoD Quality Gates (`verify_all.py --tier fast` + `invariant_checker.py`)** | N/A | **`PASS` (`9/9` invariants clean, `0` critical defects, `15/15` token tiers verified)** | `verify_all.py --mode hub --tier fast` & `invariant_checker.py --json` |

---

## 5. Consequences, Risks & Rollback Guard

- **Positive:** 100% backward-compatible with all existing CLI/JSON contracts and English workflows; zero new third-party dependencies; sub-5ms deterministic execution; strict adherence to `AGENTS.md` Invariants 1–17.
- **Maintenance Trade-off:** Curated bilingual QA synonym table in `tools/core/bilingual_intent_normalizer.py` requires incremental updates only when new domain vocabularies are introduced.
- **Rollback Hooks:** Path-scoped rollback commands per milestone remain documented in `implementation_plan.md §3 & §6` (`git checkout -- <milestone_files>`).
