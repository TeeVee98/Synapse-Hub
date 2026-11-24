<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

---
name: super-plan
description: Deep Spec-Driven Planning Pipeline: Risk Routing & AST Recon -> Ambiguity Gate & Tournament -> Execution DAG with Typed Manifests -> Mechanical Mutation Red-Teaming -> Self-Healing DAG & Semantic Harvesting.
---

# /super-plan (Deep Spec-Driven Planning & Execution Pipeline — 10.0 Blueprint)

> **Core Objective:** Transform `/plan` from a drift-prone prose intent description into a **Deterministic Mechanical Control System**.
> **5-Phase Closed Loop:** Risk-Routing & AST Recon $\rightarrow$ Ambiguity Gate & Anti-Rubber-Stamping $\rightarrow$ Execution DAG + Typed Manifests $\rightarrow$ Mechanical Mutation Testing $\rightarrow$ Self-Healing DAG & Semantic Harvesting.

---

## ⚡ Stage 1: Dynamic Risk-Routing & AST Structural Recon (Strict Grounding)

> **Governing Invariant:** *"Read First – Plan Later"* (AGENTS.md §5.1). Strictly forbid guessing code structure or inventing interfaces without physical inspection.

1. **Deterministic Risk-Based Routing (`RiskScore`):**
   - Automatically route planning depth using whole-word token matching and bounded math (0 LLM tokens):
     $$\text{Blast} = \min\left(1.0, \frac{\log_2(1 + \text{BlastRadius})}{\log_2(1 + \text{FAN\_CAP})}\right), \quad \text{FAN\_CAP}=32$$
     $$\text{RiskScore} = 0.35 \cdot \text{Blast} + 0.25 \cdot \text{CrossBoundary} + 0.25 \cdot \text{StateMutation} + 0.15 \cdot \text{HistoryDrift}$$
   - **Tier 0 (Fast-Track, `RiskScore < 0.35`, $\le 2$ files):** Skip Ambiguity Gate and Tournament; generate 1-shot Micro-Plan (< 10s).
   - **Tier 1 (Standard, `0.35 \le RiskScore < 0.70`):** Single architectural branch + Typed Manifest + condensed Rollback Matrix.
   - **Tier 2 (Deep-Track, `RiskScore \ge 0.70`):** Activate full 5-stage closed loop + Orthogonal Tournament + Continuous Mutation Testing.
2. **AST Structural Anchors & JIT Read:**
   - Lock target files using **Unified AST Structural Anchors** (`path::Symbol#ordinal` with optional body hash `[AST: Symbol | Lxx-Lyy]`).
   - Micro-Context Slicing (< 100–300 tokens/file) for initial recon, with bounded **Just-In-Time (JIT) Full Body Read** ($\le 2$ files) triggered only during failure triage.
3. **AST Pre-flight Sensor:**
   - Execute mechanical verification matching every referenced file and symbol against physical disk paths (`tools/lint/plan_schema_sentinel.py`).
   - Flag phantom signatures and require explicit `(Overwrite)` on `[CREATE]` targeting existing files. Halt immediately on hallucinated files or phantom signatures.

---

## 🛑 Stage 2: Ambiguity Gate & Anti-Rubber-Stamping Tournament (Clarify Before Drafting)

> **Hallucination Circuit Breaker & Architecture Arena:** Halt to resolve architectural forks before generating any plan lines.

1. **Hard Stop Trigger Conditions:**
   - $\ge 2$ plausible architectural paths exist (e.g., In-Memory vs Redis, Sync vs Async, Backward Compatibility vs Breaking API change).
   - Critical business constraints are missing (idempotency rules, timeout handling, latency vs consistency trade-offs).
2. **Anti-Rubber-Stamping Safeguard & Fail-Closed Headless Mode:**
   - Ask up to **3 concise multiple-choice questions** via `ask_question` or structured format.
   - **Mandatory Counter-Argument:** Display the primary technical risk/trade-off directly under the `(Recommended)` option to prevent developers from unthinkingly rubber-stamping default choices.
   - **Headless Mode (`--auto-recommend`):** If active task invariants cannot resolve an architectural fork, exit with status code 3 (`UNRESOLVED_FORK`) and emit `[DRAFT-BLOCKED]`, preventing rubber-stamped invalid architectures in unattended CI.
3. **Orthogonal Architectural Tournament (3-Way Branching):**
   - When `--tournament` is passed or for Tier 2 tasks, construct a **Trade-off Matrix** comparing:
     - *Branch A (Minimalist):* Smallest diff, zero new files, lowest regression risk.
     - *Branch B (Clean Architecture):* Decoupled interfaces, repository/adapter pattern, high extensibility.
     - *Branch C (High Performance):* Sub-millisecond latency, zero-copy, cached hot-path, non-blocking I/O.

---

## 🏗️ Stage 3: Execution DAG & Typed Interface Manifests (Lock the Skeleton)

> **Principle:** Lock data contracts, construct a dependency DAG with disjoint write-set verification, and attach milestone-level circuit breakers.

1. **Structure Plan as an Execution DAG:**
   - Divide milestones into a dependency tree using `depends_on: [...]`.
   - **Parallel Collision Guard:** Label branches with `[PARALLEL_OK]` ONLY when their write-sets are strictly disjoint ($\text{write\_set}(M_a) \cap \text{write\_set}(M_b) = \emptyset$). If write sets intersect, force sequential dependencies.
2. **Assign Model Compute Tiers (Compute-Annotated DAG):**
   - `Compute Tier: [Model: Flash | Thinking: Off | Temp: 0.1]` for boilerplate, configuration, and test wiring.
   - `Compute Tier: [Model: Pro / Reasoning | Thinking: High | Best-of-3]` for core algorithmic or concurrency nodes.
3. **Typed Interface Manifests (Anti-Full-Code):**
   - Seal DTOs, Dataclasses, Schemas, and Function Signatures with AST Structural Anchors (`module::Symbol`).
   - Define explicit `consumes`, `produces`, and `rollback_hook` (Compensating Transactions for non-git mutations like DB/Cache/Queue).
   - Forbid full function body implementations in the plan to save 70% of tokens and prevent execution drift.
4. **Milestone Circuit Breakers:**
   - Stop conditions: `Max Fix Attempts: 2` | `Scope Guard` | `Rollback Hook`.

---

## 🔍 Stage 4: 12-Mutant Continuous Plan Mutation Testing & Safe Rollback

> **Mechanical Red-Teaming (Plan Kill Score $\ge 90.0\%$):** Transform Red-Teaming from LLM self-monologue into deterministic mechanical stress testing on the plan itself before coding:

1. **Mechanical 12-Mutant Battery (`tools/lint/plan_mutator.py`):**
   - Executes 12 structural mutants: Contract Field Drop, Type Widening, Edge Inversion, DAG Cycle Injection, Verification Matrix Scenario Drop, Phantom Symbol Injection, Consumed Contract Tampering, Overwrite Collision, Parallel Write-Set Collision, Dangerous Rollback Hook, Missing Rollback Hook, Invalid Compute Tier.
   - Keyword-stuffed plans fail baseline schema check immediately (0% kill score).
   - **Gating Sensor:** Plan must achieve **Plan Kill Score $\ge 90.0\%$** to advance to execution.
2. **Path-Scoped Rollback Sentinel (`rollback_path_scoped`):**
   - Strictly prohibit catastrophic commands: `git reset --hard`, `git clean -fdx`, `git push --force`, `rm -r`, shell pipes (`curl | bash`).
   - Enforce path-scoped restoration restoring modified files via `git restore` and deleting created files.

---

## 🚀 Stage 5: Clean Context Handoff, Self-Healing Execution & Semantic Harvesting

1. **Clean Context Handoff & Surgical Patch Protocol:**
   - Pass only `implementation_plan.md` + AST structural anchors to Executor (saves 60–70% input tokens).
   - Never regenerate the entire plan upon feedback; edit targeted blocks via `edit_file` and append to the Changelog header.
2. **Dynamic DAG Rescheduling & Self-Healing (`tools/design/dag_self_healer.py`):**
   - Capture failure snapshots (diff + runtime trace) before rollback.
   - Classify root causes: `LOCAL_IMPL` (escalate compute tier Flash $\to$ Pro) vs `ARCHITECTURAL_VIOLATION` (cancel cascading descendants and resplice replacement sub-DAG).
3. **Semantic Plan Calibration & Organizational Memory:**
   - Execute `tools/design/plan_harvester.py`:
     - Measure **Semantic Contract Drift Score** via AST interface hashing (`sha256`) in addition to file list diff.
     - Apply **0.9 Exponential Temporal Memory Decay** to coupling memory in `project_state.json`, pruning stale associations (< 0.1).
     - Harvest architectural rulings into permanent records in `docs/adr/ADR-xxxx-[title].md` strictly gated to High Architectural Impact.
