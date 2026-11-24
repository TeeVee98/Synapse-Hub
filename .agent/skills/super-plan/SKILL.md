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

0. **Pre-Plan Model & Thinking Fit Gate (Before Planning):**
   - Assess the prompt's estimated scope/risk against the user's currently active model and thinking level:
     - **Under-provisioned** (e.g., Tier 1/2 architectural `/super-plan` on `3.8 Flash` or `Hydrogen Low/Medium`): Advise upgrading to `Gemini 4 Neon (High)` (or `Hydrogen High` for Tier 1) before drafting.
     - **Right-sized**: Proceed directly to Risk-Routing & AST Recon.
     - **Over-provisioned** (e.g., Tier 0 <= 2-file micro-plan on `Neon High` / `Carbon`): Propose stepping down to `Gemini 4 Hydrogen (Medium/High)` or `Neon (Medium)` to conserve tokens.
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

1. **Structure Plan as an Execution DAG & Separate Execution Modes:**
   - Divide milestones into a dependency tree using `depends_on: [...]`.
   - **Default Execution Mode — Single-Agent `/solo` (Sequential):** Plans MUST default to sequential Single-Agent `/solo` execution: **one session**, **one primary recommended model/thinking level**, executing milestones sequentially (`M1 -> M2 -> ...`) with **NO `swarm` workers or parallel subagents**. Do NOT emit `[PARALLEL_OK]` unless the user explicitly requested `/teamwork`.
   - **Opt-In Multi-Agent Mode — `/teamwork` (Parallel Workers):** Label branches with `[PARALLEL_OK]` ONLY when the user explicitly requests `/teamwork` AND their write-sets are strictly disjoint ($\text{write\_set}(M_a) \cap \text{write\_set}(M_b) = \emptyset$). If write sets intersect or mode is `/solo`, enforce sequential dependencies.
2. **Annotate Complexity Metadata (Compute Tiers):**
   - `Compute Tier: [Model: Flash | Thinking: Off | Temp: 0.1]` for boilerplate, configuration, and test wiring.
   - `Compute Tier: [Model: Pro / Reasoning | Thinking: High | Best-of-3]` for core algorithmic or concurrency nodes.
   - *Execution Binding:* Under default `/solo`, these serve as complexity hints while **one session** runs all milestones at the single `Recommended Execution Model & Thinking Level` from Stage 5. Per-node worker routing applies only under explicit `/teamwork`.
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

1. **Mandatory Disk Export (`implementation_plan.md`) & User Handoff Notification:**
   - Upon completing `/plan` or `/super-plan`, the agent MUST write the finalized plan to `implementation_plan.md` at the repository root (unless the user explicitly specifies an alternate path) — never leave the plan only in chat prose or in a conversation-private artifact directory.
   - Immediately after writing `implementation_plan.md`, notify the user that the plan has been exported to `implementation_plan.md`, summarize its key milestones/blast radius, and default the ready-to-use handoff instruction to **sequential Single-Agent `/solo`** execution in a fresh chat (e.g., `"Read implementation_plan.md and execute sequentially via /solo"`). Only suggest `/teamwork` if the user explicitly requested multi-worker parallel execution.
   - **Mandatory Execution Model & Thinking Level Recommendation (Always Display):** Both at the end of `implementation_plan.md` and in the final completion message to the user, you MUST evaluate the plan as a whole (RiskScore, blast radius, concurrency/security complexity, and milestone Compute Tiers) and display a clear **`Recommended Execution Model & Thinking Level`** block recommending:
     - **Primary Executor Model & Thinking Level (Single-Session Default):** One single model and thinking level for the `/solo` session (e.g., `Gemini 4 Hydrogen (Medium)` for Tier 0/boilerplate, `Gemini 4 Hydrogen (High)` for standard/multi-file `/solo` execution, or `Gemini 4 Neon (Medium)` / `Gemini 4 Neon (High)` for high-risk core logic/concurrency/security).
     - **Milestone Escalation Overrides (Optional / `/teamwork` Only):** Explicitly note that `/solo` runs all milestones sequentially in one session on the Primary Executor; list milestone overrides only if the user chooses to escalate manually or explicitly invokes `/teamwork` workers.
     - **Rationale** (1–2 concise lines explaining the speed/token-cost vs. accuracy trade-off for this specific plan).
2. **Clean Context Handoff & Surgical Patch Protocol:**
   - Pass only `implementation_plan.md` + AST structural anchors to the single `/solo` executor session (saves 60–70% input tokens). Do NOT spawn `swarm` workers or parallel subagents unless `/teamwork` was explicitly invoked.
   - Never regenerate the entire plan upon feedback; edit targeted blocks via `edit_file` and append to the Changelog header.
3. **Dynamic DAG Rescheduling & Self-Healing (`tools/design/dag_self_healer.py`):**
   - Capture failure snapshots (diff + runtime trace) before rollback.
   - Classify root causes: `LOCAL_IMPL` (escalate compute tier Flash $\to$ Pro) vs `ARCHITECTURAL_VIOLATION` (cancel cascading descendants and resplice replacement sub-DAG).
4. **Semantic Plan Calibration & Organizational Memory:**
   - Execute `tools/design/plan_harvester.py`:
     - Measure **Semantic Contract Drift Score** via AST interface hashing (`sha256`) in addition to file list diff.
     - Apply **0.9 Exponential Temporal Memory Decay** to coupling memory in `project_state.json`, pruning stale associations (< 0.1).
     - Harvest architectural rulings into permanent records in `docs/adr/ADR-xxxx-[title].md` strictly gated to High Architectural Impact.
