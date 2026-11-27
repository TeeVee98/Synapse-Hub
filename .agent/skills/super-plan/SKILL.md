<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

---
name: super-plan
version: 2.0.0
category: architecture_and_analysis
description: Deep Spec-Driven Planning Pipeline (v2.0): Transitive Risk Routing & AST Recon -> Negation-Aware Ambiguity Gate & Tournament -> N-File Execution DAG with Typed Manifests -> Non-Vacuous 12-Mutant Red-Teaming & Plan-Domain Loss -> Closed-Loop /solo Handoff & Semantic Harvesting.
policies:
  network: none
  shell: workspace-sandbox
  filesystem: workspace-sandbox
---

# /super-plan (Deep Spec-Driven Planning & Control Plane — v2.0 Blueprint)

> **Core Objective:** Transform `/plan` from a drift-prone text intent description into a **Deterministic Closed-Loop Mechanical Control System** that compiles directly into `/solo` verification (`agent-qa solo --from-plan <plan_path>`).
> **Unified CLI Entrypoints:** `agent-qa super-plan` (`tools/design/super_plan_engine.py`) | `agent-qa lint-plan` (`tools/lint/plan_schema_sentinel.py`) | `agent-qa plan-mutate` (`tools/lint/plan_mutator.py`) | `tools/lint/plan_quality_loss.py`
> **5-Phase Closed Loop:** Risk-Routing & AST Recon $\rightarrow$ Negation-Aware Ambiguity Gate & Tournament $\rightarrow$ Execution DAG + Typed Manifests $\rightarrow$ Non-Vacuous 12-Mutant & Plan Loss Gate $\rightarrow$ Closed-Loop `/solo --from-plan` Handoff & Semantic Harvesting.

---

## ⚡ Stage 1: Dynamic Risk-Routing, Coupling Memory & AST Structural Recon

> **Governing Invariant:** *"Read First – Plan Later"* (AGENTS.md §5). Strictly forbid guessing code structure or inventing interfaces without physical inspection.

0. **Pre-Plan Model & Thinking Fit Gate (`assess_pre_plan_model_fit`):**
   - Evaluate the prompt's scope/risk against the active model and thinking level (`UNDER_PROVISIONED` / `RIGHT_SIZED` / `OVER_PROVISIONED`):
     - **Under-provisioned** (e.g., Tier 1/2 architectural `/super-plan` on `Flash` or `Hydrogen Low/Medium`): Advise upgrading to `Gemini 4 Neon (High)` (or `Hydrogen High` for Tier 1) before drafting.
     - **Right-sized**: Proceed directly to Risk-Routing & AST Recon.
     - **Over-provisioned** (e.g., Tier 0 `<= 2`-file micro-plan on `Neon High` / `Carbon`): Propose stepping down to `Gemini 4 Hydrogen (Medium)` to conserve tokens.
1. **Deterministic Risk-Based Routing (`RiskScore` + 2-Hop Transitive Fan-In + `coupling_memory`):**
   - Execute `agent-qa super-plan route --task "<task>" --files <files...> --json` (0 LLM tokens):
     - Reads `project_state.json::coupling_memory`, computes 2-hop transitive dependents via `call_graph_indexer.py`, returns a collision-free `suggested_plan_path` (`.synapse/plans/<slug>.md`), and inspects `concurrency_status` (`CLEAN` vs `CONCURRENT_SESSION_DETECTED`).
     - If `concurrency_status == "CONCURRENT_SESSION_DETECTED"` (another active plan or uncommitted diff exists in the workspace) and the session will edit code, automatically isolate into a dedicated worktree first via `agent-qa worktree create --agent-id <slug> --plan <plan_path>` (printed in `recommended_worktree_cmd`) before writing code.
     - **Tier 0 (Fast-Track, `RiskScore < 0.35`, `<= 2` files):** Skip Ambiguity Gate and Tournament; generate 1-shot Micro-Plan.
     - **Tier 1 (Standard, `0.35 <= RiskScore < 0.70`):** Single architectural branch + Typed Manifest + condensed Rollback Matrix.
     - **Tier 2 (Deep-Track, `RiskScore >= 0.70`):** Activate full 5-stage closed loop + Orthogonal Tournament + Non-Vacuous 12-Mutant Red-Teaming.
2. **AST Structural Anchors & Pre-flight Sensor:**
   - Lock target files using **Unified AST Structural Anchors** (`path::Symbol` or `(AST: Symbol)`).
   - Validate via `agent-qa lint-plan --file <plan_path> --mode super --json`: flags phantom symbols, missing files, unannotated `[CREATE]` collisions, untyped Section 2 `: Any` contract widening, and non-executable milestone `Pass Gate` commands.
3. **Manual QA Profile (`--profile manual`):**
   - For Manual QA workflows (BRD/Story analysis, ISO/IEC/IEEE 29119-3 test suites, RTM coverage), pass `--profile manual` on `route`, `ambiguity-check`, `scaffold`, `validate`, and `run-pipeline` (default remains `--profile code`).
   - Composes `goldfish_review.py --mode brd`, `checklist_query.py` (25-field surface), and `manual_tc_linter.py` Pass Gates via `tools/manual/manual_pipeline_adapter.py`, enforcing structured `AC-`/`REQ-`/`YC-` Coverage Contracts and Golden Ratio commitments instead of Python AST/pytest gates.
   - **Atomic Spec Decomposition Protocol (Anti-Compression Rule):** When ingesting multi-screen BRD/SRS/HDSD documents (Markdown, `.docx`, `.pdf`, `.xlsx`, or UI screenshots), NEVER compress an entire screen or module into a single coarse requirement ID. Decompose every screen, popup, and workflow into atomic sub-requirements (`AC-xx`/`REQ-xx`/`YC-xx`) spanning 7 mandatory dimensions: (1) UI/Navigation & Element Visibility, (2) Happy Path & Post-Action State Transitions (including ownership transfer & permission revocation), (3) Per-Field Validation (empty, format, max-length, duplicate email/ID), (4) Exact Boundary Pairs (`N` vs `N+1`, `23:59:59` vs `00:00:01`), (5) Negative Flows & Cancel/Reset actions, (6) RBAC/IDOR/Data Isolation & Parameter Tampering (UI + direct API), and (7) Concurrency/Double-Submit & Security Hygiene (XSS/SQLi/Unicode IME).
   - **Spec-vs-UI Mismatch & Dev/BA Q&A Protocol:** Log every conflict between written text and UI screenshots or missing rules in a structured `Q&A_Dev_BA` / `## Ambiguity & Assumptions Log` table (`QA-01..QA-N`), state a single deterministic temporary assumption per item, and tag affected test cases with `@qa-xx` so QA is never blocked while waiting on Dev/BA replies.

---

## 🛑 Stage 2: Negation-Aware Ambiguity Gate & Orthogonal Tournament

1. **Negation-Aware Fork Resolution (`agent-qa super-plan ambiguity-check --task "<task>" --json`):**
   - Recognizes explicit exclusions and positive anchors (e.g., `"in-memory cache, no redis"` positively selects `in_memory` and excludes `redis` -> `resolved_by_invariant=true`; whereas `"add a cache, no redis"` excludes `redis` but still leaves `in_memory` vs `sqlite` -> exits `3` (`UNRESOLVED_FORK`) in fail-closed mode until confirmed).
   - Displays a mandatory **Counter-Argument** under the `(Recommended)` option to prevent rubber-stamping.
   - **Decision Injection & Fail-Closed Pipeline:** Pass confirmed choices directly into `scaffold` or `run-pipeline` via `--decisions storage=in_memory,resilience_retry=sync_backoff` (JSON or `k=v` pairs). `run-pipeline` defaults to fail-closed (`UNRESOLVED_FORK` / `AMBIGUITY_BLOCKED`) until forks are resolved by invariants or `--decisions`.
2. **Orthogonal Architectural Tournament (Heuristic Trade-off Baseline):**
   - Compares *Branch A (Minimalist)*, *Branch B (Clean Architecture)*, and *Branch C (High Performance)* using dynamic risk/task criteria weights driven by genuine blast-radius, architectural, and performance signals (without unconditional Tier 2 branch bias).

---

## 🏗️ Stage 3: N-File Execution DAG & Typed Interface Manifests

1. **Dynamic N-File Partitioning & Execution Modes:**
   - `agent-qa super-plan scaffold` pairs matching source/test targets into TDD-aligned milestones (`<= 3` files per milestone), each with bold/backtick `Node ID`, `depends_on`, `Compute Tier`, `Write Set`, `Typed Interface Manifest` (`consumes`/`produces`), `Circuit Breaker`, `Rollback Hook`, and executable `Pass Gate`.
   - Scaffolded plans use task-grounded DTO/function names, real CallGraph direct callers and dynamic regression risk, honest Ambiguity Gate status, and a 4-scenario Verification Matrix bound to target test files. Unfilled `<<FILL:...>>` sentinels or unedited legacy generic boilerplate (`ExecutionInputDTO`/`execute_operation`/`test_happy_path`) are mechanically rejected by `lint-plan --mode super` and `plan_quality_loss.py`.
   - **Default Execution Mode — Single-Agent `/solo` (Sequential):** Plans MUST default to sequential Single-Agent `/solo` execution in **one session** on one primary recommended model/thinking level (`M1 -> M2 -> ...`) with **NO `swarm` workers or parallel subagents**. Do NOT emit `[PARALLEL_OK]` unless the user explicitly requested `/teamwork`.
   - **Opt-In Multi-Agent Mode — `/teamwork`:** Emit `[PARALLEL_OK]` ONLY when the user explicitly requests `/teamwork` AND write-sets are strictly disjoint.
2. **Typed Interface Manifests (Anti-Full-Code):**
   - Seal DTOs, dataclasses, schemas, and typed signatures in Section 2; bare untyped `: Any` field/parameter annotations are rejected in Super Mode (parameterized `Dict[str, Any]` remains allowed).

---

## 🔍 Stage 4: Non-Vacuous 12-Mutant Plan Audit & Plan-Domain Loss Gate

1. **Non-Vacuous 12-Mutant Battery (`agent-qa plan-mutate --file <plan_path> --threshold 90.0 --json`):**
   - Executes 12 structural mutants with an `applicable_mutants` denominator (zero free kills for missing constructs, genuine sentinel-verified `: Any` widening mutant, generic parallel write-set collision injection).
   - **Gating Sensor:** Plan must achieve **Plan Kill Score `>= 90.0%`** over applicable mutants (`applicable_mutants >= 1`).
2. **Plan-Domain Markdown Quality Loss (`tools/lint/plan_quality_loss.py`):**
   - Evaluates Markdown plan quality (`evaluate_plan_markdown_loss`) inside `agent-qa super-plan calibrate --file <plan_path> --json` without false positives on text anti-pattern mentions.
3. **Path-Scoped Rollback Sentinel (`rollback_path_scoped_detailed`):**
   - Strictly prohibits catastrophic commands (`git reset --hard`, `git clean -f`, `git push --force`, recursive `rm -r`).

---

## 🚀 Stage 5: Closed-Loop `/solo --from-plan` Handoff, Self-Healing & Harvesting

1. **Mandatory Disk Export & Execution Model Recommendation:**
   - Write the finalized plan to the unique gitignored path `.synapse/plans/<slug>.md` returned by `route` (or `agent-qa super-plan scaffold --output auto`; auto-increments `-2`, `-3` on collision so concurrent sessions never overwrite each other) unless the user explicitly specifies another filename.
   - Display a **`Recommended Execution Model & Thinking Level`** block recommending one Primary Executor model/thinking level for the single `/solo` session (with optional escalation notes only for `/teamwork`).
   - Provide the ready-to-use closed-loop handoff command referencing the exact exported `<plan_path>`:
     ```bash
     # Interactive single-agent handoff:
     # "Read <plan_path> and execute sequentially via /solo (single-agent mode, no swarm workers)"
     # Mechanical closed-loop verification runner:
     agent-qa solo --from-plan <plan_path> --json
     ```
2. **Self-Healing DAG & Live Scope Guard (`tools/design/dag_self_healer.py`):**
   - Parses bold/backtick plan keys accurately and enforces fail-closed `check_scope_guard_violation` before and after milestone pass gates, emitting structured `replan_diagnostics`.
3. **Semantic Plan Harvesting & Auto-Cleanup (`agent-qa harvest-plan` / `tools/design/plan_harvester.py`):**
   - Calibrates file drift, semantic AST contract drift, and per-milestone `milestone_drift`, applies `0.9` exponential decay to `project_state.json::coupling_memory`, and indexes High-Impact ADRs in `docs/adr/README.md`.
   - After DoD verification passes, automatically remove the completed `.synapse/plans/<slug>.md` draft (and remove any ephemeral worktree via `agent-qa worktree remove --path <worktree_path>` once merged).
