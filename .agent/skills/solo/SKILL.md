<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

---
name: solo
version: 2.0.0
category: verification_and_resilience
description: Single-Agent Verification Loop (v2.0) with 4 Pillars & Closed-Loop Plan Bridge: Milestone-Scoped HMAC Red/Green Receipts (--milestone, --recertify-red, --require-four-scenarios), Auto-Target Purple Audit, Live Mutation Sentinel (>= 80%), AST-Grounded Prover-Verifier Debate, and --from-plan DAG Execution.
policies:
  network: none
  shell: workspace-sandbox
  filesystem: workspace-sandbox
---

# /solo (Single-Agent Verification Loop & Closed-Loop Plan Executor — v2.0)

> **Core Objective:** Give a single AI Agent the multi-perspective rigor, adversarial testing depth, and quality consistency of a full engineering team while preserving context coherence, zero Git conflicts, and optimal token efficiency.
> **Unified CLI:** `agent-qa solo` (`python3 tools/orchestration/solo_runner.py`) | **Plan Bridge:** `tools/orchestration/plan_dag_bridge.py`

## 🚫 Strict Single-Agent Execution Boundary

- **One Session, One Agent:** `/solo` executes **exclusively within the single active agent session**, running milestones and verification phases sequentially (`Red -> Blue -> Purple`).
- **No Worker Spawning:** It is **STRICTLY FORBIDDEN** to spawn `swarm` workers (`swarm` tool `action: "add"`), launch parallel subagents, or fan out worktrees across agents when executing via `/solo` (or whenever the user did not invoke `/teamwork` or explicitly request parallel workers).
- **3-Phase Cognitive Persona Shifting:** Multi-perspective rigor comes from **sequential persona shifting** inside one agent via `agent-qa solo` / `tools/orchestration/solo_runner.py` — never multi-agent parallelism. Multi-worker parallel execution belongs strictly to `/teamwork`.
- **Sequential Milestones Only:** Even if an implementation plan marks nodes `[PARALLEL_OK]` (metadata for `/teamwork` write-set safety), `/solo` MUST execute those milestones sequentially in topological dependency order within this single session.

---

## ⚡ Ordered Execution Workflow

When `/solo` is invoked for a task or a validated Super-Plan (`.synapse/plans/<slug>.md` or legacy `implementation_plan.md`), execute these steps sequentially:
- **Concurrent Session Isolation:** If another active plan or uncommitted diff from another task exists in the current workspace, isolate into a dedicated git worktree first (`agent-qa worktree create --agent-id <slug>`) before editing files.

### 🎯 Pre-Execution 3-Line Contract (In Your Own Words)
Before creating Red tests or editing files, state in 3 concise lines:
- **Goal:** What is being built/fixed and the smallest complete change.
- **Won't Do:** Explicit out-of-scope boundaries and untouched files/APIs.
- **Done When:** Exact test/gate command and observable outcome proving completion.

### 🛑 Phase 0: AST-Grounded Prover-Verifier Debate (Pillar 4)
*If the task involves architectural forks or high-risk design decisions:*
1. Run the AST-grounded Prover-Verifier debate engine (labels `[AST-Heuristic]` vs `[External-Oracle]`):
   ```bash
   agent-qa solo --proposal "<task_proposal>" --rounds 3 --json
   ```
2. Lock down the winning consensus and include extracted `structured_test_scenarios` (`TC-ADV-xx`) into the test plan.

---

### 🔴 Phase 1: Red Team — Adversarial QA & Specification Sentinel (Pillar 1 & 2)
1. **Strict Invariant:** Do NOT write any functional implementation code.
2. Draft full unit/integration test suites covering **4 mandatory scenarios** (Positive, Negative, Boundary, CLI/Resilience).
3. Certify the Red Phase mechanically with milestone-scoped HMAC receipts (`reports/solo_receipts/<milestone>_red.json`):
   ```bash
   agent-qa solo --red --milestone M1 --require-four-scenarios --ttl 1800 \
     --test-cmd "python3 -m pytest tests/<target_test>.py" --json
   ```
4. **Audited Red Recertification (`--recertify-red`):** If a Red test must be refined before implementation, re-certify with cryptographic lineage (`recertified_from_hmac`):
   ```bash
   agent-qa solo --red --milestone M1 --require-four-scenarios --recertify-red \
     --test-cmd "python3 -m pytest tests/<target_test>.py" --json
   ```
5. **Mandatory Red Check:** Verify `status: CERTIFIED_RED` in the signed receipt.

---

### 🔵 Phase 2: Blue Team — Senior Developer Persona (Pillar 2)
1. **Strict Invariant:** Do NOT modify or relax the test assertions authored in Phase 1 (`test_tree_hash` is cryptographically verified; milestone-scoped mode allows ancestor commit progression as long as `test_tree_hash` remains intact).
2. Implement the minimum complete code (Lean Senior Dev / 7-Rung Ladder & Clean POM).
3. Certify the Green Phase mechanically:
   ```bash
   agent-qa solo --green --milestone M1 \
     --test-cmd "python3 -m pytest tests/<target_test>.py" --json
   ```
4. **Mandatory Green Check:** Verify `status: CERTIFIED_GREEN` with exit code `0`.

---

### 🟣 Phase 3: Purple Team — Tech Lead & Mutation Auditor (Pillar 3)
1. **Live Dynamic Mutation Testing (Pillar 3):**
   Run the mutation testing sentinel targeting the **source file** to ensure assertion sensitivity `>= 80.0%`:
   ```bash
   agent-qa solo --mutation --target <source_file.py> \
     --test-cmd "python3 -m pytest tests/<test_file>.py" --threshold 80.0 --json
   ```
   *If score `< 80.0%`, strengthen test assertions until mutants are killed.*
2. **Auto-Target Purple Audit & Quality Gates:**
   `--purple` automatically resolves changed source targets via `resolve_auto_targets()` when `--target` is omitted so Neuro-Symbolic acyclicity and Call-Graph blast-radius checks always run, and in standalone CLI mode automatically triggers `/review --strict-solo` (pass `--milestone <ID>` for milestone-scoped receipts, or `--no-review` to opt out):
   ```bash
   agent-qa solo --purple --json
   # Or with milestone-scoped standalone receipt:
   agent-qa solo --purple --milestone M1 --json
   python3 tools/lint/infer_linter.py
   python3 tools/core/verify_all.py --mode hub --tier impact
   ```
3. **Closed-Loop Plan Verification Bridge (`--from-plan`):**
   `agent-qa solo --from-plan` is a **deterministic milestone verifier & gate orchestrator** (it does not synthesize code; the agent writes Red tests and implementation per milestone, then invokes `--from-plan` to verify). It compiles a validated Super-Plan Markdown DAG sequentially across milestones with **cumulative ancestor Scope Guard** enforcement (preserving completed earlier milestone edits across M1 -> M2 -> ... while enforcing `/` path-segment boundary matching and path-scoped rollback on unauthorized edits), O(1) memory flushing, strict `decisions.tsv` audit logging, and **automatic post-`/solo` `/review` verification**:
   ```bash
   # Recommended per-milestone loop: write Red tests -> certify --red -> implement -> verify milestone:
   agent-qa solo --from-plan <plan_path> --milestone M1 --strict-red --json
   # Verify full DAG sequentially (cumulative Scope Guard preserves completed M1..Mk edits across milestones):
   agent-qa solo --from-plan <plan_path> --strict-red --json
   # Audit the decision trail strictly before handoff:
   python3 tools/core/decision_log.py --log decisions.tsv --audit --strict --json
   ```

---

### 🔍 Phase 4: Automatic Closed-Loop `/review` Handoff (Mandatory Post-`/solo` Gate)
1. **Automatic Post-`/solo` Invocation:** Immediately after `/solo` finishes all milestones (or after Phase 3 in standalone single-target mode), **automatically run `/review` in strict read-only DIAGNOSTIC mode** before claiming completion:
   - Plan-driven `/solo`: `agent-qa solo --from-plan <plan.md>` automatically invokes `evaluate_review(..., strict_solo=strict_red)` at the end of the DAG (unless `--no-review` is explicitly passed). In agent-driven execution, also run:
     ```bash
     agent-qa review --plan <plan.md> --strict-solo --json
     ```
   - Standalone `/solo` (no plan): `agent-qa solo --purple` automatically invokes `evaluate_review(..., strict_solo=True)` (pass `--milestone <ID>` when using milestone receipts, or `--no-review` at CLI to opt out). When running `/review` directly in standalone mode, enforce `--strict-solo`:
     ```bash
     agent-qa review --strict-solo --json
     # Or scope to a milestone receipt / staged diff:
     agent-qa review --milestone <ID> --strict-solo --json
     agent-qa review --staged --strict-solo --json
     ```
2. **Closed-Loop Verdict Handling:**
   - If `/review` returns `APPROVED` or `APPROVED_WITH_NOTES` (zero `Must fix` blockers) with signed `reports/code_review_receipt.json`, deliver the completed solution with verified terminal proof and Adversarial Code Audit Receipt.
   - If `/review` returns `CHANGES_REQUESTED`, fix the reported `Must fix` findings in `/solo` and re-run `/review` until zero blockers remain.