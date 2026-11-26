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

> **Core Objective:** Transform `/plan` from a drift-prone prose intent description into a **Deterministic Closed-Loop Mechanical Control System** that compiles directly into `/solo` verification (`agent-qa solo --from-plan implementation_plan.md`).
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
     - Reads `project_state.json::coupling_memory` and computes 2-hop transitive dependents via `call_graph_indexer.py` to boost `blast_radius` accurately.
     - **Tier 0 (Fast-Track, `RiskScore < 0.35`, `<= 2` files):** Skip Ambiguity Gate and Tournament; generate 1-shot Micro-Plan.
     - **Tier 1 (Standard, `0.35 <= RiskScore < 0.70`):** Single architectural branch + Typed Manifest + condensed Rollback Matrix.
     - **Tier 2 (Deep-Track, `RiskScore >= 0.70`):** Activate full 5-stage closed loop + Orthogonal Tournament + Non-Vacuous 12-Mutant Red-Teaming.
2. **AST Structural Anchors & Pre-flight Sensor:**
   - Lock target files using **Unified AST Structural Anchors** (`path::Symbol` or `(AST: Symbol)`).
   - Validate via `agent-qa lint-plan --file implementation_plan.md --mode super --json`: flags phantom symbols, missing files, unannotated `[CREATE]` collisions, untyped Section 2 `: Any` contract widening, and non-executable milestone `Pass Gate` commands.

---

## 🛑 Stage 2: Negation-Aware Ambiguity Gate & Orthogonal Tournament

1. **Negation-Aware Fork Resolution (`agent-qa super-plan ambiguity-check --task "<task>" --json`):**
   - Recognizes explicit exclusions (e.g., `"in-memory cache, no redis"` excludes `redis` and recommends `in_memory`).
   - Displays a mandatory **Counter-Argument** under the `(Recommended)` option to prevent rubber-stamping.
   - **Fail-Closed Headless Mode (`--non-interactive` / `--auto-recommend`):** Exits with code `3` (`UNRESOLVED_FORK`) if active invariants cannot resolve a fork.
2. **Orthogonal Architectural Tournament (3-Way Branching):**
   - Compares *Branch A (Minimalist)*, *Branch B (Clean Architecture)*, and *Branch C (High Performance)* using dynamic risk/task criteria weights.

---

## 🏗️ Stage 3: N-File Execution DAG & Typed Interface Manifests

1. **Dynamic N-File Partitioning & Execution Modes:**
   - `agent-qa super-plan scaffold` partitions all `N` target files into `ceil(N / 2)` TDD-aligned milestones (`<= 3` files per milestone), each with bold/backtick `Node ID`, `depends_on`, `Compute Tier`, `Write Set`, `Typed Interface Manifest` (`consumes`/`produces`), `Circuit Breaker`, `Rollback Hook`, and executable `Pass Gate`.
   - **Default Execution Mode — Single-Agent `/solo` (Sequential):** Plans MUST default to sequential Single-Agent `/solo` execution in **one session** on one primary recommended model/thinking level (`M1 -> M2 -> ...`) with **NO `swarm` workers or parallel subagents**. Do NOT emit `[PARALLEL_OK]` unless the user explicitly requested `/teamwork`.
   - **Opt-In Multi-Agent Mode — `/teamwork`:** Emit `[PARALLEL_OK]` ONLY when the user explicitly requests `/teamwork` AND write-sets are strictly disjoint.
2. **Typed Interface Manifests (Anti-Full-Code):**
   - Seal DTOs, dataclasses, schemas, and typed signatures in Section 2; bare untyped `: Any` field/parameter annotations are rejected in Super Mode (parameterized `Dict[str, Any]` remains allowed).

---

## 🔍 Stage 4: Non-Vacuous 12-Mutant Plan Audit & Plan-Domain Loss Gate

1. **Non-Vacuous 12-Mutant Battery (`agent-qa plan-mutate --file implementation_plan.md --threshold 90.0 --json`):**
   - Executes 12 structural mutants with an `applicable_mutants` denominator (zero free kills for missing constructs, genuine sentinel-verified `: Any` widening mutant, generic parallel write-set collision injection).
   - **Gating Sensor:** Plan must achieve **Plan Kill Score `>= 90.0%`** over applicable mutants (`applicable_mutants >= 1`).
2. **Plan-Domain Markdown Quality Loss (`tools/lint/plan_quality_loss.py`):**
   - Evaluates Markdown plan quality (`evaluate_plan_markdown_loss`) inside `agent-qa super-plan calibrate --file implementation_plan.md --json` without false positives on prose anti-pattern mentions.
3. **Path-Scoped Rollback Sentinel (`rollback_path_scoped_detailed`):**
   - Strictly prohibits catastrophic commands (`git reset --hard`, `git clean -f`, `git push --force`, recursive `rm -r`).

---

## 🚀 Stage 5: Closed-Loop `/solo --from-plan` Handoff, Self-Healing & Harvesting

1. **Mandatory Disk Export & Execution Model Recommendation:**
   - Write the finalized plan to `implementation_plan.md` at the repository root (unless the user explicitly requests an alternate filename).
   - Display a **`Recommended Execution Model & Thinking Level`** block recommending one Primary Executor model/thinking level for the single `/solo` session (with optional escalation notes only for `/teamwork`).
   - Provide the ready-to-use closed-loop handoff command:
     ```bash
     # Interactive single-agent handoff:
     # "Read implementation_plan.md and execute sequentially via /solo (single-agent mode, no swarm workers)"
     # Mechanical closed-loop verification runner:
     agent-qa solo --from-plan implementation_plan.md --json
     ```
2. **Self-Healing DAG & Live Scope Guard (`tools/design/dag_self_healer.py`):**
   - Parses bold/backtick plan keys accurately and enforces fail-closed `check_scope_guard_violation` before and after milestone pass gates, emitting structured `replan_diagnostics`.
3. **Semantic Plan Harvesting & Per-Milestone Drift (`agent-qa harvest-plan` / `tools/design/plan_harvester.py`):**
   - Calibrates file drift, semantic AST contract drift, and per-milestone `milestone_drift`, applies `0.9` exponential decay to `project_state.json::coupling_memory`, and indexes High-Impact ADRs in `docs/adr/README.md`.
