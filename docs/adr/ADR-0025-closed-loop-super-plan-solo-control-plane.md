<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0025: Unified Closed-Loop Control Plane for /super-plan and /solo (v2.0 Upgrade)

- **Status:** Accepted (DoD Certified)
- **Date:** 2026-11-26
- **Source Plan:** `super_plan_solo_upgrade_plan.md`
- **Deciders:** Synapse Hub Autonomous Agent Core & Engineering Team (`/solo` Sequential Tier-2 Execution)
- **Author Attribution:** Thế Vị (@TeeVee98) under MIT License (`tools/core/author_integrity.py` preserved)

---

## 1. Context & Problem Statement

Following the 10.0 Blueprint rollout of `/super-plan` and `/solo`, an empirical architectural audit across `tools/design/`, `tools/lint/`, `tools/orchestration/`, `tools/reasoning/`, and `tools/core/` (`FanIn = 41`, `BlastRadius = 46`) exposed five structural disconnects:

1. **Open-Loop Plan-to-Solo Chasm & Bold-Markdown Parser Bug:** `solo_runner.py` could not directly compile or execute a validated `implementation_plan.md` DAG; `dag_self_healer.py::parse_plan_to_dag` misparsed bolded Markdown keys (`**Pass Gate:**`, `**Write Set:**`, `**Compute Tier:**`), causing `pass_gate` to resolve as `"**"` and `write_set` to fall back to prose scraping; and `run_dag_live` did not enforce `check_scope_guard_violation`.
2. **Vacuous Plan Mutation Passes & Domain-Mismatched Plan Loss:** `plan_mutator.py::mutant_type_widening` returned `True` without invoking `plan_schema_sentinel.py`; missing plan blocks (`produces:`, `(AST: ...)`) earned free kills; `mutant_parallel_writeset_collision` hardcoded a single filename; and `super_plan_engine.py::calibrate_and_refine_plan` fed Markdown plans into Python/POM test-code `TextGradOptimizer`.
3. **Unwired Risk Signals & 2-File Scaffold Cap:** `coupling_memory` persisted by `plan_harvester.py` was never consumed by `calculate_risk_routing`, 2-hop transitive dependents were uncounted, `check_ambiguities` did not handle negated exclusions (`"in-memory cache, no redis"`), and `scaffold_super_plan` ignored `target_files[2:]`.
4. **Solo Runner CLI Wiring Friction & Strict Mypy Shadowing:** `--require-four-scenarios` was unexposed in CLI, `--purple` skipped Neuro-Symbolic and Call-Graph checks when `--target` was omitted, global `tdd_red_receipt.json` collided across sequential milestones, strict `mypy` variable shadowing remained in `plan_harvester.py` and `solo_runner.py`, and `ProverVerifierGame` emitted irrelevant HTTP/UI strings on offline Python modules.
5. **CLI & Multi-IDE Surface Disconnects:** `super-plan`, `solo`, `lint-plan`, and `plan-mutate` were unregistered in `cli_specs.json`, `.agent/skills/{super-plan,solo}` were absent from `skill_router.py`, and `.claude/commands/` / `.windsurf/workflows/` were not synchronized by `sync_agent_rules.py`.

---

## 2. Governing Architectural Rulings

- **Ruling 1 (Branch B — Unified Mechanical Control Plane):** Built `tools/orchestration/plan_dag_bridge.py` (`MilestoneExecutionSpecDTO`, `PlanExecutionSummaryDTO`, `compile_plan_to_solo_specs`, `execute_plan_via_solo`) and wired `solo_runner.py --from-plan` so validated Super-Plan DAGs execute sequentially through `Scope Guard -> Red/Green -> Live Mutation -> Purple Audit -> DecisionLog` with `O(1)` memory flushing and zero `swarm` worker spawning.
- **Ruling 2 (Non-Vacuous Plan Sensors & Native Markdown Loss):** Created `tools/lint/plan_quality_loss.py` (`PlanQualityLossDTO`, `evaluate_plan_markdown_loss`), added Section 2 untyped `: Any` contract-widening detection and milestone `Pass Gate` binding checks to `tools/lint/plan_schema_sentinel.py`, and replaced vacuous `return True` branches in `tools/lint/plan_mutator.py` with a 3-state `applicable_mutants` denominator (`zero free kills`) and generic parallel collision injection.
- **Ruling 3 (Milestone-Scoped HMAC Receipts & Commit Progression):** Extended `tools/orchestration/solo_contracts.py` (`ScopedRedReceiptDTO`, `resolve_red_receipt_path`, `resolve_red_receipt_ttl`, `recertify_red_receipt_payload`) to isolate receipts under `reports/solo_receipts/<milestone>_red.json`, cryptographically chain `--recertify-red` lineage (`recertified_from_hmac`), and allow ancestor commit progression in milestone-scoped mode whenever `test_tree_hash` remains intact — while preserving 100% backward compatibility with legacy global receipts.
- **Ruling 4 (Grounded Risk Routing, AST Debate & Multi-IDE Sync):** Wired `project_state.json::coupling_memory`, 2-hop transitive fan-in, Pre-Plan Model Fit Gate, negation-aware ambiguity resolution, and `ceil(N / 2)` TDD milestone scaffolding into `tools/design/super_plan_engine.py`; grounded `ProverVerifierGame` in real Python AST symbols with `[AST-Heuristic]` / `[External-Oracle]` provenance labels; fixed P0 bold-Markdown parsing and live Scope Guard enforcement in `tools/design/dag_self_healer.py`; registered `super-plan`, `solo`, `lint-plan`, and `plan-mutate` in `tools/core/cli_specs.json`; routed `/super-plan` & `/solo` in `tools/core/skill_router.py`; and synchronized `.claude/commands/` and `.windsurf/workflows/` via `tools/core/sync_agent_rules.py` without bloating the `< 35`-line `starter` client profile.

---

## 3. Empirical Certification Receipts (M1 -> M7 Sequential `/solo`)

| Milestone / Gate | Verification Command | Empirical Result |
|---|---|---|
| **M1 (Plan Sentinel, Mutator & Loss)** | `pytest tests/test_super_plan_mutator_and_loss_ratchet.py tests/test_plan_schema_sentinel.py tests/test_super_plan_10_blueprint.py` + `plan_mutator.py --self-test` + `solo_runner.py --mutation --target tools/lint/plan_quality_loss.py` | **CERTIFIED** — `80/80` tests pass, `100.0%` self-test (`8/8` applicable, `0` vacuous kills), **`93.75%`** live mutation score (`15/16` killed), `0` mypy issues |
| **M2 (Super-Plan Engine & Harvester)** | `pytest tests/test_super_plan_mutator_and_loss_ratchet.py tests/test_super_plan_10_perfection.py tests/test_super_plan_and_harvester.py` + strict `mypy` | **CERTIFIED** — `79/79` tests pass, `coupling_memory` + 2-hop fan-in + negation + `ceil(N/2)` scaffolding verified, `0` mypy errors |
| **M3 (Scoped Receipts, AST Debate & DAG Parser)** | `pytest tests/test_plan_dag_solo_bridge.py tests/test_solo_runner.py tests/test_super_plan_10_blueprint.py tests/test_prover_verifier_games.py` + strict `mypy` | **CERTIFIED** — `120/120` tests pass, bold Markdown `pass_gate`/`write_set` fixed, live Scope Guard halts unauthorized edits, `0` mypy errors |
| **M4–M5 (Plan-DAG Bridge & Solo Wiring)** | `pytest tests/test_solo_runner.py tests/test_plan_dag_solo_bridge.py` + `solo_runner.py --mutation --target tools/orchestration/plan_dag_bridge.py` + `solo_runner.py --purple --json` | **CERTIFIED** — `71/71` + `10/10` tests pass, **`90.0%`** live mutation score (`18/20` killed), auto-target `--purple` executes Neuro-Symbolic + Call-Graph |
| **M6 (CLI, Router & IDE Sync)** | `cli_schema_sentinel.py --check --json`, `sync_agent_rules.py --check`, `pytest tests/test_sync_agent_rules.py tests/test_zero_ceremony_client_profile.py tests/test_cli_smoke.py` | **CERTIFIED** — `0` schema drifts across `81` tools, `28/28` tests pass, `/super-plan` & `/solo` routed cleanly, `starter` `< 35` lines & `0` Hub leaks |
| **M7 (Skills v2.0, ADR-0025 & DoD Gates)** | `invariant_checker.py --json`, `validate_skills_schema.py`, `lint_ai_docs.py`, `infer_linter.py`, `verify_all.py --mode hub --tier impact`, `decision_log.py --audit --strict --json` | **CERTIFIED** — Verified at delivery handoff |

---

## 4. Consequences & Rollback Boundaries

- **Positive:** Closed-loop `/super-plan -> /solo --from-plan` execution eliminates manual JSON handoff friction; plan mutation auditing is non-vacuous; milestone-scoped HMAC receipts eliminate cross-milestone collisions and support audited `--recertify-red` workflows; unified `agent-qa` CLI and Claude/Windsurf slash bridges keep every IDE synchronized.
- **Trade-Offs:** Adding flags to `solo_runner.py` requires running `tools/lint/cli_schema_sentinel.py --sync` to keep `tools/tools_schema.json` synchronized (mechanically enforced by CI).
- **Rollback:** All 7 milestones carry path-scoped rollback hooks via `tools/lint/plan_schema_sentinel.py::rollback_path_scoped_detailed`; legacy `reports/tdd_red_receipt.json` remains supported when `--milestone` is omitted.
