<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0024: Synapse Hub v5.1 Apex Architecture Overhaul — Zero-Python Native Node.js Linter, Semantic POM Inheritance/Fixture Graph, 145+ Module Strict Typing & Zero-Ceremony Client Mode

- **Status:** Accepted & Certified
- **Date:** 2026-11-26
- **Deciders:** Synapse Hub Core Architecture (`/solo` Tier-2 Deep Super-Plan Execution)
- **Author Attribution:** Thế Vị (@TeeVee98) under MIT License (`tools/core/author_integrity.py` untouched)

---

## 1. Context & Problem Statement

Following the v5.0 polyglot AST & LSP overhaul (`ADR-0023`), enterprise adoption across Frontend monorepos, Docker Node-only CI images (`node:20-alpine`), Windows workstations, and strict static-analysis audits revealed four structural gaps:

1. **Zero-Python Execution Gap:** `bin/agent-qa.js` failed immediately on environments without Python >= 3.10 installed, preventing Frontend and Node-only CI runners from running `lint`, `fix`, `doctor`, `version`, or `help`.
2. **Deep TypeScript Monorepo POM Patterns:** Cross-file POM assertion indexing did not propagate inherited assertion methods down multi-level `extends` chains (`BasePage -> MidCheckoutPage -> VipCheckoutPage`), resolve Playwright `test.extend<Fixtures>` destructured bindings, or trace barrel `index.ts` re-export aliases (`export { VipCheckoutPage as VipPO }`).
3. **Hidden Static Type & Runtime Bugs Across Core Packages:** Global `[tool.mypy]` disabled `arg-type`, `attr-defined`, and `return` across ~97% of the repository, masking real runtime crash hazards in `mcp_excel_server.py` (`list.get`), `codeact_engine.py` (POSIX-only `os.killpg` on Windows), and `benchmark_perf_runner.py` (`sum` over `int | str`), plus ~90 type errors across `tools/lint/*`, `tools/core/*`, and `tools/context/*`.
4. **Spoke Onboarding Ceremony & Simulation Disclosure:** Starter Spoke workspaces inherited Hub-heavy verification ceremony, and offline research heuristic commands (`cove`, `ai-eval`, `tot-exploratory`, `assertion-optimizer`) needed explicit `[Offline Heuristic]` CLI labeling and Gate 11 count breakdowns (`production_active: 9`, `offline_heuristic_simulation: 6`).

---

## 2. Governing Architectural Rulings

- **Ruling 1 (Zero-Python Native Node.js Linter & Auto-Fixer Engine):** Implemented zero-dependency `bin/native-linter.js` (Node.js >= 18 stdlib `fs`/`path`/`os`) with comment/backtick lexical stripping, cross-file POM assertion indexing, 6 core defect detectors + Clean POM raw XPath detection, idempotent atomic `--fix`, `--json`/`--sarif` output, and `doctor`/`version`/`help`. Wired `--engine {auto,python,native-js}` into `bin/agent-qa.js` with automatic fallback when Python >= 3.10 is absent, verified 1:1 against `tools/lint/infer_linter.py`.
- **Ruling 2 (145+ Module Core Production Strict Mypy Ratchet + Runtime Crash Remediation + Simulation Labeling):** Eliminated all `arg-type`, `attr-defined`, and `return` errors across all 6 core production packages (`tools/core.*`, `tools/lint.*`, `tools/context.*`, `tools/mcp.*`, `tools/alm.*`, `tools/transpiler.*`) plus `tools/runtime/codeact_engine.py` and `tools/perf/benchmark_perf_runner.py`, locked them permanently in `pyproject.toml`, raised global coverage floor `fail_under` from `65` to `70`, added `tier_classification.counts` (`production_active: 9`, `offline_heuristic_simulation: 6`) to Gate 11, and prefixed offline research lab descriptions in `tools/core/cli_specs.json` with `[Offline Heuristic]`.
- **Ruling 3 (Semantic POM Inheritance/Fixture/Barrel Graph + Zero-Ceremony Client Profile):** Upgraded `tools/context/pom_assertion_indexer.py` & `tools/lint/infer_linter.py` with cycle-safe multi-level inheritance propagation (`max_inheritance_depth=5`), Playwright `test.extend<Fixtures>` extraction, barrel `index.ts` alias tracking, and an mtime-keyed graph cache (`P95 < 50ms`). Added `ceremony_level: "minimal"` + `gate_11_token_reduction: False` in `tools/core/init_config.py` and `--profile {starter,standard,enterprise}` in `tools/core/sync_agent_rules.py` emitting a `< 35`-line Zero-Ceremony client bridge with `0` Hub path leaks.

---

## 3. Verification & Empirical Certification Receipts

| Verification Gate | Target / Command | Measured Empirical Result |
| :--- | :--- | :--- |
| **Zero-Python Native JS Parity (M1–M2)** | `pytest tests/test_native_js_python_parity.py -v` & `node bin/agent-qa.js lint examples/playwright-crm-suite --engine native-js --json` | **PASSED** — `5/5` parity/fallback/boundary/SARIF tests pass (`1:1` defect-code match with Python); CRM reference suite scans in **`38.9ms`** (`< 50ms`), Python-less `PATH` verified |
| **Semantic POM Graph (M3)** | `pytest tests/test_semantic_pom_inheritance_fixtures.py tests/test_pom_assertion_indexer.py tests/test_infer_linter.py` | **CERTIFIED (`RED -> GREEN -> MUTATION`)** — 3-tier `extends`, `test.extend<Fixtures>`, barrel aliases, cycle safety & colliding non-asserting fixture verified; `39/39` passed |
| **Dynamic Mutation Sentinel (Pillar 3)** | `solo_runner.py --mutation --target tools/context/pom_assertion_indexer.py` | **CERTIFIED_MUTATION** — **`90.0%`** kill score (`18/20` killed, threshold `>= 80.0%`) |
| **Dynamic Mutation Sentinel (Pillar 3)** | `solo_runner.py --mutation --target tools/core/sync_agent_rules.py` | **CERTIFIED_MUTATION** — **`100.0%`** kill score (`20/20` killed, threshold `>= 80.0%`) |
| **Neuro-Symbolic Acyclicity Proof** | `solo_runner.py --neuro-symbolic --target tools/context/pom_assertion_indexer.py` | **NEURO_SYMBOLIC_CERTIFIED** — `has_cycle = false` across `15` dependency edges |
| **Permanent 149-Module Strict `mypy` Lock (M4–M11)** | `python3 -m mypy tools/core tools/lint tools/context tools/mcp tools/alm tools/transpiler tools/runtime/codeact_engine.py tools/perf/benchmark_perf_runner.py` | **PASSED** — `Success: no issues found in 149 source files` (`0` errors across `arg-type`, `attr-defined`, `return`) |
| **Coverage Ratchet & Win32 Guards (M11)** | `pytest tests/test_core_type_safety_and_win32_guards.py tests/test_gate_11_all_15_tiers.py tests/test_quality_gates_metrics.py` | **PASSED** — `46/46` passed; `fail_under = 70`; simulated Win32 `codeact_engine` timeout & `mcp_excel_server` list-row normalization verified |
| **Zero-Ceremony Client Profile (M10)** | `pytest tests/test_zero_ceremony_client_profile.py tests/test_sync_agent_rules.py` & `sync_agent_rules.py --check` | **CERTIFIED (`RED -> GREEN -> MUTATION`)** — `starter` bridge `< 35` lines, `0` Hub path leaks, `sync_agent_rules.py --check` 100% clean |
| **Adversarial Self-Audit (`--purple`)** | `solo_runner.py --purple --json` | **CERTIFIED_PURPLE** — `26` files analyzed, `0` must-fix defects |
| **Schema Sentinel, Rule 16, Docs & Full 11/11 Hub DoD** | `cli_schema_sentinel.py --check --json`, `invariant_checker.py --rule 16 --json`, `lint_ai_docs.py`, `verify_all.py --mode hub --parallel` | **VERIFIED** — `drift_count == 0`, `0` Rule 16 violations, `11/11` Hub Quality Gates pass |

---

## 4. Consequences & Rollback Boundaries

- **Positive:** Frontend and Docker Node-only pipelines run Synapse linting and auto-fixing in `< 50ms` with zero Python installation; enterprise TS monorepos gain multi-level inheritance, fixture, and barrel resolution; 149 core Python modules are permanently guarded against type regressions; starter Spoke adopters receive a lightweight `< 35`-line client bridge; and offline heuristic commands are transparently labeled.
- **Trade-Offs:** `bin/native-linter.js` must remain synchronized with `tools/lint/infer_linter.py` (enforced mechanically in CI by `tests/test_native_js_python_parity.py`).
- **Rollback:** All 12 milestones carry deterministic path-scoped rollback commands via `tools/lint/plan_schema_sentinel.py::rollback_path_scoped_detailed`.
