<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

---
name: super-plan
description: Deep Spec-Driven Planning Pipeline: AST Recon & Pre-flight -> Ambiguity Gate & Tournament -> Execution DAG with Compute Tiers -> Tri-Vulnerability & Rollback -> Calibration & Clean Handoff.
trigger: /super-plan
---

# Workflow: /super-plan (Deep Spec-Driven Planning & Execution Pipeline)

> **Core Objective:** Transform `/plan` from a drift-prone prose intent description into a **Deterministic Mechanical Control System**.
> **5-Phase Closed Loop:** AST Recon & Pre-flight $\rightarrow$ Ambiguity Gate & Tournament $\rightarrow$ Execution DAG + Compute Tiers $\rightarrow$ Tri-Vulnerability Red-Teaming & Rollback $\rightarrow$ Calibration & Clean Handoff.

---

## ⚡ Stage 1: AST Reconnaissance & Pre-flight Verification (Strict Grounding)

> **Governing Invariant:** *"Read First – Plan Later"* (AGENTS.md §5.1). Strictly forbid guessing code structure or inventing interfaces without physical inspection.

1. **Touchpoint Identification & AST Slicing:**
   - Inspect user prompts and explicit `@file` anchors. Use `tools/context/context_slicer.py` to target directly relevant modules.
   - Micro-Context Slicing (< 100–300 tokens/file): Read only Class/Function signatures, input/output types, docstrings, and exact line coordinates (`file.py:L45-L60`).
   - Forbid ingesting full file contents of large files to prevent context window bloat.
2. **Blast-Radius Risk Routing & AST Symbol Anchors:**
   - Compute deterministic RiskScore:
     $$\text{RiskScore} = 0.35 \cdot \log_2(1 + \text{BlastRadius}) + 0.25 \cdot \text{CrossBoundary} + 0.25 \cdot \text{StateMutation} + 0.15 \cdot \text{HistoryDrift}$$
   - Any modification touching critical paths (`auth`, `security`, `schema`, `database`, `core`, `runner`, `base_page`) escalates automatically to Tier 1 or Tier 2 regardless of file count.
   - Lock target files using **AST Symbol Anchors** (`module::Class.method`) instead of brittle line numbers (`file.py:L45-L60`) to prevent drift across parallel worktrees.
3. **AST Pre-flight Sensor:**
   - Execute mechanical verification matching every referenced file and symbol against physical disk paths (exempting files marked `(New)` or `[CREATE]`). Halt immediately on hallucinated files or phantom signatures.

---

## 🛑 Stage 2: Ambiguity Gate & Orthogonal Tournament (Clarify Before Drafting)

> **Hallucination Circuit Breaker & Architecture Arena:** Halt to resolve architectural forks before generating any plan lines.

1. **Hard Stop Trigger Conditions:**
   - $\ge 2$ plausible architectural paths exist (e.g., REST vs GraphQL, In-Memory vs Redis, Sync vs Async Worker, Backward Compatibility vs Breaking API change).
   - Critical business constraints are missing (idempotency rules, timeout handling, latency vs consistency trade-offs).
2. **Dual-Mode Ambiguity Gate:**
   - **Interactive Mode:** Halt and ask up to **3 concise multiple-choice questions** via `ask_question`, placing technical risks directly under `(Recommended)` to prevent rubber-stamping.
   - **Headless Mode (`--auto-recommend`):** Automatically selects default `(Recommended)` options and logs explicit assumptions in the plan changelog for unattended CI pipelines.
3. **Orthogonal Architectural Tournament (3-Way Branching):**
   - When `--tournament` is passed or for core architectural tasks, construct a **Trade-off Matrix** comparing 3 opposing branches:
     - *Branch A (Minimalist):* Smallest diff, zero new files, lowest regression risk.
     - *Branch B (Clean Architecture):* Decoupled interfaces, repository/adapter pattern, high extensibility.
     - *Branch C (High Performance):* Sub-millisecond latency, zero-copy, cached hot-path, non-blocking I/O.

---

## 🏗️ Stage 3: Execution DAG & Compute-Annotated Tiers (Lock the Skeleton)

> **Principle:** Lock data contracts, construct a dependency DAG for parallel execution, assign model compute tiers, and attach milestone-level circuit breakers.

1. **Structure Plan as an Execution DAG:**
   - Divide milestones into a dependency tree using `depends_on: [...]`.
   - Label independent branches with `[PARALLEL_OK]` for concurrent dispatch across separate Git worktrees (`workspace: "share"`).
2. **Assign Model Compute Tiers (Compute-Annotated DAG):**
   - Annotate each milestone with its resource allocation:
     - `Compute Tier: [Model: Flash | Thinking: Off | Temp: 0.1]` for boilerplate, configuration, and test wiring.
     - `Compute Tier: [Model: Pro / Reasoning | Thinking: High | Best-of-3]` for core algorithmic or concurrency nodes.
3. **Type Contracts & AST Symbol Anchors (Anti-Full-Code):**
   - Seal DTOs, Dataclasses, Schemas, and Function Signatures with AST Symbol Anchors (`module::Class.method`).
   - Forbid full function body implementations in the plan to save 70% of tokens and prevent execution drift.
4. **Milestone Circuit Breakers:**
   - Each milestone enforces strict stop conditions:
     - `Max Fix Attempts: 2`: Halt immediately if tests fail after 2 attempts (unified single source threshold).
     - `Scope Guard`: Halt if unapproved files are touched.
     - `Rollback Action`: `git checkout -- <files>` reverting to pre-milestone state upon trip.

---

## 🔍 Stage 4: Tri-Vulnerability Red-Teaming & Rollback Matrix (Self-Critique & Safe Revert)

> **Prover-Verifier & Zero-Downtime:** Act as Red Team to expose 3 mandatory failure modes and design a safe fallback matrix:

1. **Mandatory Tri-Vulnerability Self-Critique:**
   - *Vulnerability 1 — Race Conditions, Concurrency & State Inconsistency:* Idempotency token validation under concurrent requests.
   - *Vulnerability 2 — Resource Extremes, Boundary & Timeout:* Handling empty payloads, payload spikes, and downstream service timeouts.
   - *Vulnerability 3 — Blast Radius & Backward Compatibility:* Preventing breakages of legacy callers and schema drift.
2. **Rollback & State-Migration Matrix:**
   - For any task touching Database schemas, Caches, or API Contracts, mandate a Zero-Downtime Guard detailing dual-write strategies, feature flags, and safe sequential rollback commands.

---

## 🚀 Stage 5: Publication, Clean Context Handoff, Calibration & Plan Harvesting

1. **Publication & Surgical Patch Protocol:**
   - Save `implementation_plan.md` compliant with `tools/lint/plan_schema_sentinel.py --mode super`.
   - **Surgical Patch + Changelog:** When receiving review feedback, never regenerate the entire plan file; perform surgical edits via `edit_file` and append to the 3-line `Changelog (v1 -> v2)` header.
2. **Clean Context Handoff:**
   - Transition execution to a clean session or isolated Subagent Worker ingesting only `implementation_plan.md` + AST micro-slices (saves 60–70% input tokens).
3. **Plan Calibration Loop & Selective ADR Harvesting:**
   - Upon achieving 100% on all 11 Quality Gates, execute `tools/design/plan_harvester.py`:
     - Compare planned files against actual `git diff --name-only` to compute **Plan Drift Ratio** and **Accuracy Score**, recording metrics into `project_state.json`.
     - **ADR Gating Filter:** Harvest architectural decisions (`Ruling:`) and Type Contracts into `docs/adr/ADR-xxxx-[title].md` ONLY when tagged with `Architectural-Impact: High` (one-way doors); minor refactorings record calibration metrics without polluting ADR inventory.
