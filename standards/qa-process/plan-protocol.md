<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Rule: Spec-Driven Planning & Execution Protocol (/plan)

> **Scope:** Applied whenever entering Planning mode (`/plan`), generating `implementation_plan.md`, or formulating architectural changes across all AI agents and IDEs (Antigravity, Cursor, Claude Code, Windsurf, Copilot).
> **Core Objective:** Eliminate planning hallucinations, untested logic, out-of-control blast radiuses, and vague task descriptions by enforcing strict grounding, atomic milestones, and deterministic test specifications before execution.

---

## 1. Grounding Invariant: "Read First – Plan Later" (Strict Grounding)

1. **Zero Uninspected Mutations:** It is STRICTLY FORBIDDEN to propose modifying or creating any file in a plan without having first inspected the file's current contents, types, or AST signatures (`read_file`, `context_slicer.py`) in the active conversation session.
2. **Survey Before Synthesis:** Turn 1 of any planning task must perform read-only reconnaissance on relevant files. Never guess signatures, file paths, or interfaces from memory.
3. **Anchor Tagging:** When receiving `@file` references from the user, prioritize inspecting those exact files before traversing secondary dependencies.

---

## 2. Mandatory Plan Template

Every plan output or `implementation_plan.md` artifact MUST follow this exact 4-part structure:

### I. Affected Files & Blast Radius
- **Target Files:**
  - `[MODIFY]` `path/to/existing_file.py` — Exact purpose of changes.
  - `[CREATE]` `path/to/new_file.py` — Role and responsibility of new component.
  - `[DELETE]` `path/to/obsolete_file.py` — Reason for deletion (if any).
- **Blast Radius Analysis:**
  - Downstream modules, classes, and APIs directly or indirectly consuming modified symbols.
  - Regression risk level: Low / Medium / High with explicit mitigations.

### II. Data Flow & Interface Signatures
- **Type Definitions & Data Models:**
  - Define input/output DTOs, schemas, or type annotations prior to implementation.
- **Function / Class Signatures:**
  ```python
  # Example: Explicit signature declaration before implementation
  def process_transaction(order_id: str, amount: Decimal, dry_run: bool = False) -> TransactionResult:
      """Processes transaction with idempotent ledger update."""
      ...
  ```
- **Boundary Contracts:** State explicitly what guarantees the interface provides and what errors it raises.

### III. Atomic Milestones
Break down the implementation into independent, sequential phases:
- **Milestone Budget:** Each milestone must modify at most **2–3 files**.
- **Compilation & Passing Invariant:** Each milestone must be self-contained and compile/pass its designated tests before moving to the next milestone. Never bundle multi-file changes into one giant untestable step.
  - **Milestone 1:** Types, Schemas, and Interface definitions (compile check).
  - **Milestone 2:** Core business logic implementation in target module (unit tests pass).
  - **Milestone 3:** Integration with caller / UI / CLI and end-to-end verification.

### IV. Verification Matrix ("Define the Exam in the Plan")
Never defer testing until after coding. Define concrete test cases with inputs and expected outputs upfront:
- **Deterministic Test Scenarios:**
  | ID | Test Scenario | Input / Precondition | Expected Output / Assertion | Verification Command |
  |---|---|---|---|---|
  | **TC-01** | Happy Path | Valid input payload with standard values | Return `Status.SUCCESS` with valid ID | `pytest tests/unit/test_feature.py -k "test_success"` |
  | **TC-02** | Boundary Case | Empty string / Zero / Max threshold | Handled gracefully without crash | `pytest tests/unit/test_feature.py -k "test_boundary"` |
  | **TC-03** | Negative Case | Invalid token or missing header | Raises `ValidationError(400)` | `pytest tests/unit/test_feature.py -k "test_invalid"` |
  | **TC-04** | Error Handling | Network timeout or downstream failure | Fallback triggered, error logged | `pytest tests/unit/test_feature.py -k "test_timeout"` |
- **Rule Against Generic Assertions:** Generic descriptions like *"Write unit tests to verify feature"* or *"Check for unexpected errors"* are strictly prohibited. Every test must name the specific expected state, HTTP code, or exception.

---

## 3. Invocation Formula: "Invariants + Constraints"

When invoking `/plan`, use this concise 4-bullet structure:

```text
/plan [Feature Name / Bug Description]
- Context: @[related_file_1] @[related_file_2]
- Invariants: [e.g., Do not alter existing DB schema; preserve backward compatibility for legacy APIs; zero new third-party dependencies]
- Edge cases to handle: [e.g., Network timeout, empty input, concurrent requests / race conditions]
- Done when: [e.g., All new unit tests pass and `pytest tests/...` green 100%]
```

- **Context Optimization Tip:** Tagging core interface files with `@file` anchors them directly into the LLM context, eliminating blind searches and cutting hallucinated imports by over 80%.

### 3.1 Graceful Fallback for Incomplete Prompts (Interception Protocol)
If the user forgets the 4-bullet formula or is a newcomer (e.g., just types `"/plan fix login timeout"`):
1. **Never Reject, Never Guess Blindly:** The agent MUST NOT abort or produce an unconstrained plan with hallucinated dependencies.
2. **Autonomous Reconnaissance:** The agent immediately searches repository context (`grep`, `glob`, `read_file`) to identify candidate interface files.
3. **Interactive Scaffolding (Reverse-Prompting):** The agent auto-generates an inferred 4-bullet draft and asks for user confirmation:
   ```text
   I surveyed the repository and drafted the constraints for this plan:
   - Context: @[inferred_file_1] @[inferred_file_2]
   - Invariants: Preserve existing DB schema; zero new third-party packages.
   - Edge cases: Network timeout, invalid token.
   - Done when: `pytest tests/...` passes 100%.
   Would you like to adjust any of these constraints before I generate the full plan?
   ```
4. Once confirmed or adjusted, the agent generates the full 4-part implementation plan.

### 3.2 Deep Autonomous Planning Pipeline (`/super-plan` — 10.0 Blueprint)
For complex features, cross-module refactors, or high-risk changes, invoke `/super-plan` (defined in `.agent/skills/super-plan/SKILL.md`). It mechanically enforces the 5-phase closed loop:
1. **Dynamic Risk-Routing & AST Structural Recon:** Compute deterministic `RiskScore` (0 LLM token) using whole-word token matching and bounded math ($\text{FAN\_CAP}=32$) to route into Tier 0 (Fast-Track), Tier 1 (Standard), or Tier 2 (Deep-Track); lock target files using unified AST Structural Anchors (`path::Symbol#ordinal`) and verify via AST Pre-flight Sensor with overwrite collision detection (`(Overwrite)` required on `[CREATE]` for existing files).
2. **Ambiguity Gate & Anti-Rubber-Stamping:** Halt if $\ge 2$ paths exist; ask $\le 3$ MCQs; display mandatory technical Counter-Arguments under `(Recommended)` options; in headless mode (`--auto-recommend`), fail closed with exit code 3 (`UNRESOLVED_FORK`) if invariants cannot resolve forks; trigger 3-way Orthogonal Tournament (Minimalist vs Clean vs Performance) with Trade-off Matrix.
3. **Execution DAG & Typed Interface Manifests:** Structured as a dependency DAG (`depends_on`), enforce strict Parallel Collision Guard (disjoint write-set verification $\text{write\_set}(M_a) \cap \text{write\_set}(M_b) = \emptyset$ for `[PARALLEL_OK]`), Anti-Full-Code typed manifests (`consumes`, `produces`), Compute Tier annotations (`[Model: Flash]` vs `[Model: Pro]`), and compensating rollback hooks.
4. **12-Mutant Plan Mutation Testing & Path-Scoped Rollback:** Run mechanical plan mutation testing (`tools/lint/plan_mutator.py` threshold $\ge 90.0\%$) executing 12 structural mutants (contract field drop, type widening, edge inversion, DAG cycles, scenario drop, phantom symbols, consumed contract tampering, overwrite collision, write-set collision, dangerous rollback, missing hook, invalid compute tier). Enforce path-scoped atomic rollback (`rollback_path_scoped`) strictly forbidding catastrophic `git reset --hard` or `git clean -fdx`.
5. **Clean Context Handoff & Deep Semantic Harvesting:** Execute via `dag_self_healer.py` with failure snapshot preservation; post-execution Semantic Contract Drift measurement via AST interface signature hashing, temporal memory decay (0.9 factor) in `project_state.json`, and selective ADR publication gated strictly to High Architectural Impact.

### 3.3 Surgical Patch & Changelog Protocol (Anti-Regenerate Reflex)
- **Zero Full-File Overwrite:** When receiving review feedback or comments on an approved plan artifact, the agent is STRICTLY FORBIDDEN from regenerating the entire file.
- **Block-Level Modification:** Only edit the specific lines/sections addressed by the feedback via surgical tool calls (`edit_file`).
- **Mandatory Plan Changelog:** Prepend a 3-line `Changelog (v1 -> v2)` header at the top of the plan recording exact modifications and preserved invariants.

### 3.4 Solo-Swarm Protocol & The 4 Verification Pillars for Single-Agent Rigor (`/solo-swarm`)
When executing as a single agent, prevent confirmation bias and superficial testing by applying the 4 Verification Pillars (defined in `standards/qa-process/solo-swarm-protocol.md` and `.agents/skills/solo-swarm/SKILL.md`):
1. **Pillar 1 (Test-First Inversion):** Draft tests covering 4 scenarios (Positive, Negative, Boundary, Concurrency); verify tests **FAIL** before writing any implementation code.
2. **Pillar 2 (3-Phase Cognitive Persona Shifting):** Sequentially assume Red Team (Adversarial QA) $\rightarrow$ Blue Team (Senior Dev) $\rightarrow$ Purple Team (Tech Lead Auditor).
3. **Pillar 3 (Syntactic Micro-Mutation Sentinel):** Run `python tools/lint/micro_mutator.py <target> --threshold 80.0` to verify tests kill injected mutants.
4. **Pillar 4 (Prover-Verifier Zero-Sum Debate):** Run `python tools/reasoning/prover_verifier_games.py --proposal "<choice>" --rounds 3 --judge-mode strict` to lock architectural decisions.

---

## 4. Execution Transition Invariant, Calibration & Clean Handoff

- **Clean Context Handoff:** Once the Plan is approved, do not continue in a bloated exploration context. Execute in a clean context session or dispatch to specialized subagent workers, passing only `implementation_plan.md` + AST micro-slices (saves 60-70% input tokens).
- **Milestone Discipline:** The execution phase MUST strictly follow the Atomic Milestones:
  1. Write / update the test scenario from the Verification Matrix.
  2. Implement the minimum complete code (Lean Senior Dev / 7-Rung Ladder).
  3. Run the exact test command from the matrix.
  4. Only proceed to the next milestone when the test passes with zero fake passes.
- **Plan Calibration Loop & Harvesting:** Upon passing all 11 DoD Quality Gates, execute `tools/design/plan_harvester.py`:
  1. Compare planned files vs actual `git diff --name-only` to compute Plan Drift Ratio and Accuracy Score.
  2. Record hidden module couplings into `project_state.json`.
  3. Harvest architectural decisions (`Ruling:`) and interface contracts to `docs/adr/ADR-xxxx-[title].md` for continuous self-evolution.
