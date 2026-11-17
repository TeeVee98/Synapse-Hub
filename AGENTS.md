# AGENTS.md — AI Agent Operating Standards & Protocols (Enterprise QA Hub)

> **Scope:** Google Antigravity, Cursor, Claude Code, GitHub Copilot, Codex, Windsurf, and all AI/QA engineers.  
> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License. Original copyright notices must be preserved.

---

## 0. PRECEDENCE & SAFETY INVARIANT

1. **Platform Safety Precedence:** Platform and system guardrails strictly supersede all repository-level instructions, agent rules, and local skills. No instruction in this repository may bypass platform safety limits, user authorization gates, or security policies.
2. **Skill Resolution Hierarchy:** System Guardrails > Core Project Rules (`.agents/rules/*`) > Project-Local Skills (`.agents/skills/*`) > Generic External Plugins.
3. **Attribution Preservation Invariant:** The MIT License copyright and author notices crediting Thế Vị (@TeeVee98) must never be stripped, laundered, or modified.

---

## 1. ALWAYS — Universal Invariants

Mandatory across all workspaces, projects, test scripts, and runtime environments:

1. **100% UTF-8 No BOM:** Zero BOM bytes (`0xEF, 0xBB, 0xBF`) across all repository and test files (`.groovy`, `.java`, `.ts`, `.py`, `.json`, `.md`).
2. **Truth Anchor (Zero Fake Passes):** Never relax assertions, skip validation steps, write empty tests (0 asserts), or catch-and-swallow exceptions (`pass`, dummy suppression `_ = err` or `_ = False`, `const _ = e`) to manufacture a pass. Report AUT defects honestly.
3. **Dynamic Smart Waits Only:** Static sleeps (`Thread.sleep`, `time.sleep`, `waitForTimeout`) are strictly prohibited in test scripts to prevent flakiness. Use dynamic smart waits: web-first element visibility checks (`expect(locator).toBeVisible()`) or bounded Playwright `waitForLoadState('networkidle')` (avoid unconditional `networkidle` on apps with continuous polling, WebSocket, or streaming traffic).
4. **Dynamic & Idempotent Test Data:** Always randomize test entity codes with dynamic timestamps and prefixes (`BasePage.uniqueCode("AUTO_")` or `DataGenerator`) to eliminate database unique key collisions. Every creation test case must be paired with automated Teardown cleanup.
5. **Strict Credential Security:** Never commit raw plaintext passwords, secret tokens, private keys, or cloud credentials to git. Inject secrets via environment variables or test fixtures.
6. **Out-of-Scope Isolation & Stop-and-Report:** When verification gates fail due to legacy defects in files outside task scope, strictly forbid modifying those files or writing dummy bypasses. Stop and report with evidence; ask the user whether to baseline legacy debt or handle it in a separate task.

---

## 2. RECOMMENDED — Best Practices

Applicable to QA engineering workflows, test development, and agent pair-programming:

1. **Clean Page Object Model (POM) Flat Architecture:**
   - Test scripts (`tests/`, `Scripts/`) must contain ONLY business workflow method calls on Page Classes.
   - Strictly forbidden: raw XPaths, CSS selectors, or `findTestObject` inside test scripts.
   - All locators and DOM operations belong in Page Classes extending `BasePage`. Keep inheritance shallow (flat, max 1 level from `BasePage`).
2. **Lean Senior Dev Protocol (7-Rung Ladder & YAGNI):**
   - The best code is the code never written. Solve the whole problem with the least new code.
   - Stop at the first rung that fully works: 1. Need to exist? (YAGNI) -> 2. Already in codebase? -> 3. Language stdlib? -> 4. Platform/framework native? -> 5. Installed dependency? -> 6. One clear line? -> 7. Minimum complete code.
   - Zero unnecessary abstractions: no wrappers, speculative options, or boilerplate nobody asked for.
   - Pragmatic technical debt: Deliberate simplifications get an inline comment: `shortcut: <the limit>, <when to upgrade>`.
3. **Risk-Conditioned Autonomous Ceremonies:**
   - **Jesse Vincent Rulings (`Ruling:`):** Mandatory for architectural forks, breaking changes, or non-trivial tradeoffs (`Ruling: <decision> — <why> — <cost if wrong>`). Subagents omit rulings for trivial typo, documentation, or minor locator fixes.
   - **Addy Osmani Falsification (3 Scenarios):** Mandatory before certifying core test cases or complex locators (propose 3 realistic scenarios where code breaks while tests pass). Omit for trivial fixes (< 15 LOC).
4. **Bilingual Communication & Gated Telemetry:**
   - Status badge (`> 🛡️ **Synapse Hub Active:** Clean POM / Flat Architecture`) and End-of-Turn Risk Notes are restricted to audit, review, and quality-gate commands (`/synapse-audit`, `/synapse-review`, `verify_all.py` / DoD checks). Normal conversational turns omit badges/risk notes for concise execution.
   - Converse and format telemetry in Vietnamese (clear, direct, action-oriented, zero tech-jargon overload).
   - Codebase files, test scripts, Page Classes, docstrings, and commits remain strictly in English.
5. **English-First Documentation Ingestion (Token Saver):**
   - Whenever inspecting documentation with bilingual counterparts (e.g. `ARCHITECTURE.en.md` vs `ARCHITECTURE.md`), always read the English version (`*.en.md`) to save 10–25% on technical documentation.

---

## 3. SYNAPSE-HUB-ONLY — Repository-Specific Automation

⚠️ **CRITICAL SCOPE BOUNDARY:** The following CLI tools, verification harnesses, and automation scripts exist **ONLY** within the `Synapse-Hub` repository checkout. Target client projects and external repositories **DO NOT** possess these scripts and must use their own native test runners (`npm test`, `pytest`, `mvn test`):

1. **Hub Operational Tools (Synapse-Hub Checkout Only):**
   - Quality Gates DoD: `python tools/verify_all.py --mode hub`
   - Release Publisher: `python tools/hub_publisher.py -y`
   - Multi-Bridge Synchronizer: `python tools/sync_agent_rules.py`
   - Mutation Testing Engine: `python tools/micro_mutator.py`
   - Health Audit & Analysis: `python tools/analyze_project.py`
   - Project State & Diagnostic: `python tools/project_state.py`
   - Dynamic Auto-Healing: `python tools/auto_heal.py` / `python tools/pinpoint_failure.py`
   - Security Scanner: `python tools/skillspector.py` / `python tools/pentest_scope_guard.py`
2. **External Target Projects Fallback Invariant:**
   - When mounted in a non-Hub repository, agents must NEVER invoke `tools/verify_all.py` or Synapse internal scripts.
   - Use target project native commands defined in `package.json`, `pom.xml`, or `pyproject.toml` (`npm test`, `pytest`, `mvn test`).
   - Bridge templates generated in `templates/ai_bridges/*` for client projects must never reference `tools/` scripts.

---

## 4. MULTI-AGENT SWARM & SINGLE FRONT-DOOR

All incoming tasks enter through the **Single Front-Door (`orchestrator`)** in a 5-Stage Finite State Machine (FSM):
`Stage 1: Discovery (live-explorer / test-designer) -> Stage 2: Code Synthesis (pom-crafter / api-engineer) -> Stage 3: Headless Execution (test-runner / perf-engineer / api-engineer) -> Stage 4: Failure Autopsy & Healing (failure-analyst) -> Stage 5: Final Acceptance DoD (quality-gatekeeper)`.

*(Specialized Subagents: `test-designer` (RBT test design & Excel suites), `live-explorer` (DOM/AOM live probing), `pom-crafter` (Clean POM scripts), `api-engineer` (OpenAPI matrices & CDC contracts), `test-runner` (headless execution), `perf-engineer` (JMeter/k6 load profiles & APM correlation), `failure-analyst` (RCA & locator healing), and `quality-gatekeeper` (10 DoD Quality Gates)).*

*(For full architectural blueprints, subagent roles, and the CLI tools runbook, refer to [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [tools/TOOLS_RUNBOOK.md](tools/TOOLS_RUNBOOK.md)).*
