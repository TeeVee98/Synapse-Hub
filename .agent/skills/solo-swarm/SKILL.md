<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

---
name: solo-swarm
description: Single-Agent Swarm with 4-Pillar Verification: Test-First Inversion, 3-Phase Cognitive Persona Shifting (Red QA -> Blue Dev -> Purple Auditor), Mutation Testing Sentinel (micro_mutator), and Prover-Verifier Debate.
---

# /solo-swarm (Single-Agent Swarm with 4 Verification Pillars)

> **Core Objective:** Give a single AI Agent the multi-perspective rigor, adversarial testing depth, and quality consistency of a full engineering team while preserving context coherence, zero Git conflicts, and optimal token efficiency.
> **Orchestrator:** `python tools/orchestration/solo_swarm_runner.py`

---

## ⚡ Ordered Execution Workflow

When `/solo-swarm` is invoked for a task or feature, execute these 4 phases sequentially:

### 🛑 Phase 0: Architecture Prover-Verifier Debate (Pillar 4)
*If the task involves architectural forks or high-risk design decisions:*
1. Run the Prover-Verifier debate engine to extract adversarial scenarios:
   ```bash
   python tools/orchestration/solo_swarm_runner.py --proposal "<task_proposal>" --rounds 3 --json
   ```
2. Lock down the winning consensus and include extracted `structured_test_scenarios` (`TC-ADV-xx`) into the test plan.

---

### 🔴 Phase 1: Red Team — Adversarial QA & Specification Sentinel (Pillar 1 & 2)
1. **Strict Invariant:** Do NOT write any functional implementation code.
2. Draft comprehensive unit/integration test suites covering **4 mandatory scenarios** (Happy, Negative, Boundary, Concurrency).
3. Certify the Red Phase mechanically (generates forensic failure receipt):
   ```bash
   python tools/orchestration/solo_swarm_runner.py --red --test-cmd "pytest tests/<target_test>.py"
   ```
4. **Mandatory Red Check:** Verify `status: CERTIFIED_RED` in `reports/tdd_red_receipt.json`.

---

### 🔵 Phase 2: Blue Team — Senior Developer Persona (Pillar 2)
1. **Strict Invariant:** Do NOT modify or relax the test assertions authored in Phase 1.
2. Implement the minimum complete code (Lean Senior Dev / 7-Rung Ladder & Clean POM).
3. Certify the Green Phase mechanically:
   ```bash
   python tools/orchestration/solo_swarm_runner.py --green --test-cmd "pytest tests/<target_test>.py"
   ```
4. **Mandatory Green Check:** Verify `status: CERTIFIED_GREEN` with exit code 0.

---

### 🟣 Phase 3: Purple Team — Tech Lead & Mutation Auditor (Pillar 3)
1. **Live Dynamic Mutation Testing (Pillar 3):**
   Run the mutation testing sentinel targeting the **source file** to ensure assertion sensitivity $\ge 80.0\%$:
   ```bash
   python tools/orchestration/solo_swarm_runner.py --mutation --target <source_file.py> --test-cmd "pytest tests/<test_file>.py" --threshold 80.0
   ```
   *If score < 80.0%, strengthen test assertions until all mutants are killed.*
2. **Quality Gates & Invariant Verification:**
   Run static linter, neuro-symbolic acyclicity proof, and fast DoD gates:
   ```bash
   python tools/orchestration/solo_swarm_runner.py --neuro-symbolic --target <source_file.py>
   python tools/lint/infer_linter.py
   python tools/core/verify_all.py --mode hub --tier fast
   ```
3. **Massive Distributed Execution (Multi-Service / Large Repos):**
   When executing across multiple services, run the State-Flushing DAG Pipeline to prevent context explosion:
   ```bash
   python tools/orchestration/solo_swarm_runner.py --batch-queue <batch_plan.json>
   ```
4. Deliver the completed, battle-tested solution with verified terminal proof.
