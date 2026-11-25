# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

# P0.4: Subagent Principle of Least Privilege (PoLP) Tool Hardening
#
# This rule file defines the mandatory tool confinement constraints for all
# subagent roles in the 5-Stage QA FSM. Adapted from ECC (affaan-m/ecc, Apache 2.0).
# Attribution: Thế Vị (@TeeVee98) + Affaan Mustafa (@affaan-m)

---
name: subagent-polp
version: 1.0.0
description: >
  Principle of Least Privilege (PoLP) tool boundaries for each subagent persona
  in the Synapse Hub 5-Stage QA FSM. Enforces Two-Phase Execution Separation:
  Phase 1 (orchestrator) is strictly read-only routing. Phase 2 workers receive
  only the minimal tool set required for their specialization.

invariants:
  - Zero raw selectors in test scripts (Clean POM enforcement).
  - Zero swallowed exceptions (Truth Anchor).
  - Zero external secret commits (Credential Security).
  - orchestrator NEVER authors code, test scripts, or Page Classes directly.

---

## Subagent Tool Boundaries

### orchestrator (Phase 1 — Traffic Controller)

**Role:** Single front-door routing agent. Maps user intent to skills in
`skills_index.json`, reads matching `SKILL.md`, and injects skill boundaries
before handoff to Phase 2 workers.

**ALLOWED tools (read-only):**
- `Read` — read files and skill documents
- `Grep` — search repository for context
- `Glob` — enumerate project structure
- `LS` — list directory contents

**FORBIDDEN tools (Phase 1 invariant — NEVER grant to orchestrator):**
- `Write` — forbidden; orchestrator must not author any code
- `Edit` — forbidden; no mutation in Phase 1
- `Bash` — forbidden; no shell execution in Phase 1
- `MultiEdit` — forbidden
- `NotebookEdit` — forbidden

**Rationale:** The Two-Phase Anti-Generation Reflex Protocol (AGENTS.md §4) mandates
that the orchestrator acts strictly as a router. Any code generation or file mutation
in Phase 1 is a constitutional violation.

---

### live-explorer (Stage 1 — Discovery)

**Role:** Explores the AUT (Application Under Test), discovers UI states, page flows,
and testable scenarios without writing production test scripts.

**ALLOWED tools:**
- `Read`, `Grep`, `Glob`, `LS`
- `Bash` (scoped: `npx playwright codegen`, `curl`, read-only AUT inspection only)

**FORBIDDEN tools:**
- `Write` — discovery agents do not persist artifacts
- `Edit`, `MultiEdit`

---

### test-designer (Stage 1 — Discovery)

**Role:** Designs test case specifications, scenarios, and BDD acceptance criteria
based on live-explorer findings.

**ALLOWED tools:**
- `Read`, `Grep`, `Glob`, `LS`
- `Write` (scoped: test spec `.md` files in `docs/test-specs/` ONLY)

**FORBIDDEN tools:**
- `Bash` — no execution during design phase
- `Edit` — no editing of existing test scripts

---

### pom-crafter (Stage 2 — Code Synthesis)

**Role:** Implements Page Object Model (POM) classes extending `BasePage` and
business-workflow test scripts following Clean POM flat architecture.

**ALLOWED tools:**
- `Read`, `Grep`, `Glob`, `LS`
- `Write` (scoped: `Pages/`, `tests/`, `Scripts/` only)
- `Edit`, `MultiEdit` (scoped: same directories)
- `Bash` (scoped: `npx tsc --noEmit`, `python -m py_compile`, syntax checks only)

**FORBIDDEN tools:**
- `Bash` with arbitrary shell commands (must be syntax-check-only)
- Writing raw selectors in test script files (Truth Anchor violation)

---

### api-engineer (Stage 2 — Code Synthesis)

**Role:** Implements API test suites, contract tests, and integration schemas.

**ALLOWED tools:**
- `Read`, `Grep`, `Glob`, `LS`
- `Write` (scoped: `tests/api/`, `schemas/` only)
- `Edit`, `MultiEdit`
- `Bash` (scoped: `curl` for API probing, `python -m pytest -k api` only)

**FORBIDDEN tools:**
- Write access outside `tests/api/` and `schemas/`
- Production code mutation

---

### test-runner (Stage 3 — Headless Execution)

**Role:** Executes headless test suites (Playwright, Pytest, Katalon) and captures
raw JUnit XML / HTML reports. Does NOT modify test code.

**ALLOWED tools:**
- `Read`, `Grep`, `Glob`, `LS`
- `Bash` (scoped: `npx playwright test`, `pytest`, `mvn test`, `katalonc` only)
- `Write` (scoped: `Reports/` only — test artifacts)

**FORBIDDEN tools:**
- `Edit`, `MultiEdit` — runner must NEVER modify test scripts during execution
- Writing outside `Reports/`

---

### perf-engineer (Stage 3 — Headless Execution)

**Role:** Executes load and performance test suites (k6, JMeter) and captures SLA reports.

**ALLOWED tools:**
- `Read`, `Grep`, `Glob`, `LS`
- `Bash` (scoped: `k6 run`, `jmeter -n -t`, performance tooling only)
- `Write` (scoped: `reports/perf/` only)

**FORBIDDEN tools:**
- `Edit`, `MultiEdit`
- Writing outside `reports/perf/`

---

### failure-analyst (Stage 4 — Failure Autopsy & Healing)

**Role:** Triages JUnit XML failures, performs root cause analysis via
`tools/report/pinpoint_failure.py`, proposes minimal surgical fixes,
and routes healed scripts back to Stage 2 for re-synthesis.

**ALLOWED tools:**
- `Read`, `Grep`, `Glob`, `LS`
- `Bash` (scoped: `python tools/report/pinpoint_failure.py`, `python tools/core/distill_log.py` only)
- `Write` (scoped: `Reports/` autopsy notes only)
- `Edit` (scoped: test script bug fixes — requires fact-forcing gate approval)

**FORBIDDEN tools:**
- Modifying `BasePage` or shared fixtures without explicit user confirmation (AGENTS.md §1 Rule 9)
- Catch-and-swallow exceptions (`pass`, `_ = err`) — Truth Anchor violation

---

### quality-gatekeeper (Stage 5 — Final Acceptance DoD)

**Role:** Runs `python tools/core/verify_all.py --mode hub` and certifies the
11-gate Definition-of-Done (DoD). Blocks release on any gate failure.

**ALLOWED tools:**
- `Read`, `Grep`, `Glob`, `LS`
- `Bash` (scoped: `python tools/core/verify_all.py --mode hub` ONLY)

**FORBIDDEN tools:**
- `Write`, `Edit`, `MultiEdit` — gatekeeper is strictly read-and-verify; no mutations
- Relaxing assertions or skipping gates (Truth Anchor violation)

---

## Enforcement Mechanism

The FSM enforcer (`tools/core/fsm_enforcer.py`) validates stage transitions and
calls `tools/lint/infer_linter.py` to detect PoLP violations in test scripts.
The fact-forcing gate (`tools/core/fact_forcing_gate.py`) classifies every target
artifact before any edit, blocking forbidden mutation patterns at the tool level.

## Anti-Pattern Examples (Strictly Forbidden)

```typescript
// ❌ FORBIDDEN: orchestrator authoring code (Phase 1 violation)
// orchestrator writes: await page.locator("//input[@id='user']").fill("admin");

// ✅ CORRECT: orchestrator routes to pom-crafter
// orchestrator -> skill_index -> pom-crafter -> loginPage.loginWithCredentials("admin", pw)
```

```python
# ❌ FORBIDDEN: test-runner modifying test scripts during execution
# test-runner writes: test_login.py -> assert True  # fake pass

# ✅ CORRECT: test-runner records failure, routes to failure-analyst for autopsy
```
