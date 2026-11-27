# AGENTS.md — AI Agent Operating Standards & Protocols (Enterprise QA Hub)

> **Scope:** Antigravity, Cursor, Claude Code, OpenAI, DeepSeek, GitHub Copilot, Windsurf, and enterprise QA engineers.
> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License. Original copyright notices must be preserved.

---

## 0. PRECEDENCE & TECH STACK

1. **Precedence:** Platform Guardrails > Core Project Rules (`standards/*`, `testing/*`) > Local Skills (`.agent/skills/*`, `skills/*`) > Generic External Plugins.
2. **Attribution Preservation Invariant:** MIT License copyright and author notices crediting Thế Vị (@TeeVee98) must never be stripped, laundered, or modified.
3. **Tech Stack Baseline:** Python 3.10+ (Stdlib first), Node.js v18+ | macOS, Linux, Windows | Playwright (TS/Python), Katalon (Groovy), Pytest, Cypress.
4. **Project Map:** `skills/` (57 Modular Skills, `skills_index.json`) | `tools/` (CLI Automations, `tools/TOOL_CATALOG.json`) | `tests/` (Automated Pytest Suites) | `templates/` (AI Bridges).
5. **⚡ Quick Commands:** Post-Edit Impact DoD: `python tools/core/verify_all.py --mode hub --tier impact` (Full: `--mode hub --parallel`, Fast: `--tier fast`) | Tests: `pytest tests/<file> -k "<name>"` | Linter: `python tools/lint/infer_linter.py` | Sync: `python tools/core/sync_agent_rules.py` | Schemas: `tools/tools_schema.json`.

### 0.1 CONTROL ARCHITECTURE (Agent = Model + Harness)
- **Guides (Steer Before Action):** Schemas (`tools/tools_schema.json`), Types, BasePage templates, `AGENTS.md`, 57 skills (`skills_index.json`).
- **Sensors (Verify After Action):** Deterministic gates (`verify_all.py`, `infer_linter.py`, `fact_forcing_gate.py`, `micro_mutator.py`, Pytest suites), Semantic reviewers (`senior_code_review.py`).

### 0.2 PROMPT CACHING & IMMUTABLE PREFIX ARCHITECTURE
Sections 0 through 1.1 form an **Immutable Anchor Prefix** engineered as a byte-stable prefix for provider prompt caching across modern frontier and reasoning LLMs (Gemini, Claude, GPT, DeepSeek):
- Treat Sections 0, 0.1, 0.2, 1, and 1.1 as static immutable prompt foundations (>= 1,024 tokens).
- Dynamic task parameters, issue descriptions, and AST micro-contexts must be appended AFTER Section 1.1.
- In multi-turn pair-programming, refer to rule indices without re-emitting rule text to conserve context budget.

### 0.3 CONTEXT MAP & TOUCHPOINT NAVIGATION (Read Before Action)
Authoritative touchpoints structured for dual-mode execution (UNICEF ADT-Studio & Twenty CRM pattern):
- **Universal Project Touchpoints (Client & Hub):** `skills_index.json` (57 skills routing), `synapse.config.json` (runtime configuration), `BasePage` templates, and native runner scripts (`npm test`, `pytest`).
- **Hub-Internal Diagnostic Sensors (Hub-mode checkout only):**
  - Verification & Rules: `docs/INVARIANTS.md`, `AGENTS.md` -> `python tools/lint/invariant_checker.py --json`
  - Tool Schemas & Tests: `tools/tools_schema.json` -> `python tools/lint/cli_schema_sentinel.py --check --json` | `python tools/core/agent_runner.py <cmd>`
  - Quality Ratchet & State: `python tools/lint/ratchet_sentinel.py --findings <p> --update` | `python tools/core/project_state.py status --json`
  - Tracing & Swarm: `tools/core/debug_crumbs.py --check --json` | `python tools/core/fsm_enforcer.py verify-compliance`

---

## 1. ALWAYS — Universal Invariants

Mandatory across all workspaces, test scripts, and runtime environments:

1. **100% UTF-8 No BOM:** Zero BOM bytes (`0xEF, 0xBB, 0xBF`) across all repo/test files (`.groovy`, `.java`, `.ts`, `.py`, `.json`, `.md`).
2. **Truth Anchor (Zero Fake Passes):** Never relax assertions, skip validation steps, write empty tests (0 asserts), or catch-and-swallow exceptions (`pass`, dummy suppression `_ = err` or `_ = False`, `const _ = e`). Report AUT defects honestly.
3. **Dynamic Smart Waits Only:** Static sleeps (`Thread.sleep`, `time.sleep`, `waitForTimeout`) strictly prohibited in test scripts. Use web-first assertions (`expect(locator).toBeVisible()`). For page navigation and asynchronous hydration, use bounded explicit event waits (`waitForURL`, `waitForResponse`); avoid unconditional `waitForLoadState('networkidle')` which is flaky under continuous background polling or websockets. *(Automation code only; exempt for Manual QA specs)*.
4. **Dynamic & Idempotent Test Data:** Always randomize test entity codes with dynamic timestamps/prefixes (`BasePage.uniqueCode("AUTO_")`, `DataGenerator`) to eliminate DB collisions. Pair creation with automated Teardown cleanup.
5. **Strict Credential Security:** Never commit raw plaintext passwords, secret tokens, private keys, or cloud credentials. Inject secrets via environment variables or fixtures.
6. **Out-of-Scope Isolation & Stop-and-Report:** When verification gates fail due to legacy defects in files outside task scope, never modify those files or write bypasses. Stop, report with evidence, and ask user.
7. **Skill-First Hard Blocker (Context-Aware Intent & Scope Routing):** Action/Diagnostic intents modifying code or running audits within skill-managed domains MUST call `read_file` on `skills_index.json` and matching `SKILL.md` in Turn 1 before conversational text. Mechanically evaluated via `tools/core/skill_router.py`. Pure Inquiry, read-only diagnostic surveys, and single-line micro-fixes outside skill domains are exempt.
8. **Universal Intent Disambiguation:** Action (execute commanded tool) vs Diagnostic (read-only inspection; zero mutating tools) vs Inquiry (conceptual explanation).
9. **Ask First (Human-in-the-Loop Safeguards):** Pause and obtain user confirmation before deleting test scripts/data, changing dependencies (`package.json`/`pyproject.toml`), modifying shared `BasePage`, or breaking schemas.
10. **Author Attribution & Provenance Invariant:** Mandatory attribution crediting Thế Vị (@TeeVee98) under the MIT License must be preserved across all codebase files, package manifests, and distributions. Physical provenance integrity is mechanically enforced via `tools/core/author_integrity.py` and CI/CD release provenance gates.
11. **The Ratchet Invariant (Monotonic Quality Ratchet):** Every defect resolution or post-mortem MUST tighten a Guide or Sensor. Relaxing assertions or removing rules to manufacture a pass is strictly prohibited.
12. **Mandatory Self-Verification Loop (Empirical Verification Principle):** Before marking any task complete, the agent MUST execute the designated Sensor (tests, linter, or quality gate) and provide fresh empirical evidence. Zero claims without proof.
13. **Circuit Breaker & Path-Scoped Rollback Hygiene Protocol:** If locator, test action, or tool call fails 2 consecutive times on same target (`synapse.config.json::circuit_breaker.max_fix_attempts`), trip `LocatorRetryCircuitBreaker`. Blind loops (> 2) forbidden. Execute safe, path-scoped rollback (`git checkout -- <target_files>` or `tools/lint/plan_schema_sentinel.py::rollback_path_scoped` and safe removal of untracked created files). Blanket destructive commands (`git reset --hard`, `git clean -f`) strictly prohibited. Verify clean `git status` for touched files, and emit Escalation Report proposing screenshot diff or requesting dev `data-testid`. Zero half-broken edits on disk.
14. **Anti-Premature Done & 4-Scenario Battery:** Strictly forbid claiming completion ("done/xong") without raw terminal proof across 4 scenarios: a) Positive, b) Negative (handled errors without crash), c) Boundary (empty/null), d) Scope-appropriate verification: CLI flags (`--json`, `--gate`, `--output`) for CLI tools, or Exception Handling & Edge-Case Resilience for libraries/subsystems. Skill edits: `validate_skills_schema.py` & `lint_ai_docs.py`; code edits: `infer_linter.py`.
15. **Autonomous Solo Mandate (Risk-Proportionate Test & Mutation Verification):** For runtime logic modifications on `planning.critical_paths` or spanning `> 2` files (excluding pure documentation, typos, read-only diagnostics exempt under Invariant 7, and Tier-0 non-critical micro-fixes `<= 2` files covered by passing unit tests), autonomously execute the 4-phase verification pipeline (`tools/orchestration/solo_runner.py` / `.agent/skills/solo/SKILL.md`): a) Red test failure certification (`--red`), b) Green implementation verification (`--green`), c) Live dynamic mutation score >= 80.0% (`--mutation`), and d) Quality Gates verification (`verify_all.py`). Attach forensic execution receipts (Red, Green, Mutation) in delivery report.
16. **English-Only Codebase & Rules (Bilingual Discipline Invariant):** All codebase files, test scripts, Page Classes, docstrings, commits, and rule files (`AGENTS.md`, `standards/*`, `testing/*`, `.cursor/rules/*`) must remain strictly in English to prevent semantic drift and optimize LLM KV cache hit rates. Whitelists localization test assets and end-user guides (`README.md`, `*.vi.md`). Non-English diacritics forbidden outside author attribution (`Thế Vị (@TeeVee98)`). Enforced via `python tools/lint/invariant_checker.py --rule 16`.
17. **Mandatory Adversarial Self-Audit (Risk-Proportionate Adversarial Review Invariant):** Before declaring ANY non-trivial implementation on `planning.critical_paths` or `> 2` runtime files complete (for Tier-0 micro-fixes `<= 2` files with dedicated passing unit tests, perform a concise contrarian diff check without ceremony bloat; pure documentation, typos, and read-only diagnostics are exempt), autonomously assume the persona of an independent adversarial reviewer / senior security auditor without user prompting. Execute `tools/orchestration/solo_runner.py --purple` and probe 4 contrarian crash vectors: a) Null/None/KeyError payloads, b) Logic boundary anomalies & cross-line regex slips, c) Tautological/fake assertions, d) Downstream caller breakage via `call_graph_indexer.py`. Embed explicit "Adversarial Code Audit Receipt" in delivery report. Premature completion without receipt is strictly prohibited.

---

## 1.1 PRE-FLIGHT REASONING CHECKLIST (Mandatory Pre-Action Analysis)

Verify before emitting any token in final response across 3 Cognitive Pillars:
- **Pillar A (Context Alignment & Grounding):**
  1. `[Intent & Skill]`: Classify intent (Action/Diagnostic/Inquiry); call `read_file` on `skills_index.json` / matching `SKILL.md` if triggered.
  2. `[Step-Back Abstraction]`: Formulate governing architectural invariant (CAP, idempotency, event-loop) before coding.
  3. `[Truth Anchor & AST Micro-Context]`: Real assertions only; slice micro-context (< 100 tokens via `context_slicer.py`).
- **Pillar B (Empirical Harness & Verification):**
  4. `[Harness Sensor Verification]`: Execute designated verification sensor (tests/linter) with fresh empirical proof before claiming done.
  5. `[4-Scenario Battery]`: Tested Positive, Negative, Boundary, CLI flags with raw terminal proof?
  6. `[Autonomous Solo-Swarm]`: Certified Red failure receipt, Green passing status, live mutation score >= 80% without user babysitting (exempt for Tier-0 micro-fixes <= 2 files with dedicated tests)?
- **Pillar C (Adversarial Safety & Hygiene):**
  7. `[Adversarial Self-Audit]`: Assumed auditor persona, executed `--purple`, probed 4 contrarian crash vectors, and embedded Adversarial Audit Receipt?
  8. `[Workspace Hygiene & Context Alert]`: Clean git status verified (no broken speculative edits); proactively alert `/compact` if session context is bloated?

---

## 2. RECOMMENDED — Best Practices

1. **Clean POM:** Call `BasePage` workflows (<=1 inheritance); no raw selectors *(Manual QA exempt)*.
2. **Lean Dev:** Need->Repo->Stdlib->Native->Dep->1-liner->Min; tag `shortcut: <limit>, <upgrade>`.
3. **Ceremonies:** `Ruling: <decision> — <rationale> — <cost>` on forks; 3-scenario test check.
4. **Bilingual & Telemetry:** Reply in user's language; English code/tests/commits; badges in audit/DoD only.
5. **English Docs:** Prefer `*.en.md` to save 10–25% on technical documentation.
6. **Hygiene:** Purge dead fixtures; sync `PROJECT_STATE.md`/`project_state.json`; `/compact` >50k tokens.
7. **Scratchpad:** `scratch/` exempt from POM & headers; never promote to `tests/`.

## 3. SYNAPSE-HUB-ONLY — Hub Automation

- **Client (`SYNAPSE_MODE=client`):** Native runners (`npm test`, `pytest`) or `npx @teevee98/synapse-hub`; no `./tools/`.
- **Hub (`SYNAPSE_MODE=hub`):** Hub only. Release: `bump_version.py` + `hub_publisher.py -y` (no raw `git push`). Gates: `verify_all.py --mode hub [--tier fast|impact]`, `infer_linter.py`, `sync_agent_rules.py`.

## 4. EXECUTION: /solo vs /teamwork

FSM: Phase 0 (model/thinking) -> Phase 1 (`skills_index.json` + `SKILL.md`) -> Phase 2:
- **Default (`/solo`):** Single-agent sequential `Red->Blue->Purple`. FORBIDDEN to spawn `swarm` workers or parallel subagents unless `/teamwork` or parallel workers are requested.
- **`/teamwork`:** Parallel workers on disjoint `[PARALLEL_OK]` nodes only when explicitly invoked.

## 5. SPEC-DRIVEN PLANNING (/plan & /super-plan)

Use `.agent/skills/super-plan/SKILL.md` (`tools/design/super_plan_engine.py`): **Tier 0** (<=2), **Tier 1** (3-5), **Tier 2** (>=6 + `docs/adr/`). Read first; emit Blast Radius (`::Symbol`), Interfaces, Atomic DAG (`<=3` files/milestone, Rollback), Verification Matrix; default to Single-Agent `/solo` (no `swarm` workers unless `/teamwork`); export to unique `.synapse/plans/<slug>.md` (`--output auto`), isolate concurrent dirty sessions via `agent-qa worktree create --agent-id <slug>`, and clean up finished `.synapse/plans/<slug>.md` after DoD harvest.
