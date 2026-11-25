# CLAUDE.md — Synapse-Hub Guidelines for Claude Code

> **Author & Creator:** Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
> **License:** MIT License (Mandatory Attribution Preservation)

<!-- ============================================================================== -->
<!-- AUTO-GENERATED FROM AGENTS.md — DO NOT EDIT DIRECTLY.                          -->
<!-- Run: python3 tools/core/sync_agent_rules.py                                     -->
<!-- [CACHE-ANCHOR: ROOT-PREFIX-v4.8]                                               -->
<!-- ============================================================================== -->


> **Author Attribution:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License. Attribution notices must be preserved in Synapse-Hub copies.

---

## 0. PRECEDENCE & TECH STACK
- Platform and system guardrails strictly override all repository-level instructions.
- Precedence: System Guardrails > Core Project Rules (`standards/*`, `testing/*`) > Local Skills > Generic Plugins.
- **Tech Stack Baseline:** Python 3.10+ (Standard Library first), Node.js v18+ | macOS, Linux, Windows.
- **Target Frameworks:** Playwright (TS/Python), Katalon (Groovy), Pytest, Cypress.
- **Project Map:** `skills/` (57 Modular Skills, `skills_index.json`) | `tools/` (CLI Automations, `tools/TOOL_CATALOG.json`) | `tests/` (Automated Pytest Suites) | `templates/` (AI Bridges).

### 0.2 PROMPT CACHING & IMMUTABLE PREFIX ARCHITECTURE
Sections 0 through 1.1 constitute an immutable anchor prefix engineered for >= 95% LLM KV prompt-cache hit rates across modern frontier and reasoning LLMs with context caching (Gemini, Claude, GPT, DeepSeek). Append dynamic task details after Section 1.1.

---

## ⚡ Quick Commands
- Full 11 Quality Gates: `python tools/core/verify_all.py --mode hub`
- Fast Dev-Loop (< 3s): `python tools/core/verify_all.py --mode hub --tier fast`
- Impact-Scoped Tests (< 8s): `python tools/core/verify_all.py --mode hub --tier impact`
- Run Single Test Suite: `pytest tests/<file> -k "<name>"`
- Project Health Audit: `python tools/core/analyze_project.py`
- Code Linter & Fake-Pass Sentinel: `python tools/lint/infer_linter.py`
- Client Verification: `npx @teevee98/synapse-hub verify`
- Circuit Breaker Status: `python tools/core/circuit_breaker.py --status`
- CLI Tool Schemas: `tools/tools_schema.json`
- Multi-Bridge Sync: `python tools/core/sync_agent_rules.py`

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
1. **Clean Page Object Model (POM) Flat Architecture:**
   - Test scripts (`tests/`, `Scripts/`) must contain ONLY business workflow method calls on Page Classes extending `BasePage` (max 1 level inheritance). (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
   - Strictly forbidden: Raw selectors (CSS, XPaths) or inline element lookups inside test scripts.
   ```typescript
   // ✅ Clean POM: await loginPage.loginWithCredentials("admin", "secret");
   // ❌ Anti-pattern: await page.locator("//input[@id='username']").fill("admin");
   ```
2. **Lean Senior Dev Protocol (7-Rung Ladder & YAGNI):**
   - The best code is the code never written. Solve the whole problem with the least new code.
   - Descend the 7-rung ladder: 1. Need to exist? 2. Already in codebase? 3. Standard library? 4. Platform native? 5. Installed dependency? 6. One clear line? 7. Minimum working code.
   - Deliberate simplifications get an inline comment: `shortcut: <the limit>, <when to upgrade>`.
3. **Risk-Conditioned Autonomous Ceremonies:**
   - Explicit Architectural Rulings (`Ruling: <decision> — <rationale> — <cost if wrong>`): Mandatory for architectural forks, breaking changes, or non-trivial tradeoffs. Omit for trivial doc/typo fixes.
   - Three-Scenario Empirical Falsification (Nominal, Degradation, Boundary): Mandatory before certifying core test cases or complex locators.
4. **Bilingual & Polyglot Communication & Gated Telemetry:**
   - Fluently adapt conversationally to user language (Vietnamese, English, etc.); default to English for international contributors.
   - Status badge and risk notes are restricted to audit, review, and quality-gate commands (/synapse-audit, /synapse-review, verify_all.py).
   - Codebase files, test scripts, Page Classes, docstrings, and commits strictly in English.
   - Read English versions (`*.en.md`) when bilingual docs exist to preserve tokens.
8. **Scratchpad Sandbox Allowance:** Files located inside `scratch/` are explicitly exempt from Clean POM and Author header rules to facilitate rapid prototyping, quick API probing, and ephemeral POCs. Never promote unreviewed code from `scratch/` to `tests/`.
---

## 3. SYNAPSE-HUB-ONLY — Repository-Specific Automation
⚠️ The following CLI tools exist ONLY in the Synapse-Hub repository checkout:
- Quality Gates DoD: `python tools/core/verify_all.py --mode hub` (Fast: `--tier fast`, Impact: `--tier impact`)
- Release Publisher: `python tools/core/bump_version.py patch` + `python tools/core/hub_publisher.py -y` (Active push commands only; diagnostic queries triage errors, never re-push)
- Circuit Breaker: `python tools/core/circuit_breaker.py --status` | `--reset`
- Rule Synchronizer: `python tools/core/sync_agent_rules.py`
- Level 4 Harvester & Slicer: `python tools/core/rule_harvester.py` | `python tools/context/context_slicer.py`
- Target external projects must use native runners (`npm test`, `pytest`, `mvn test`).

---

## 4. EXECUTION MODE: SINGLE-AGENT (/solo) vs /teamwork
- **Default (`/solo` — Single-Agent Sequential):** Execute milestones sequentially in one active session (`Red -> Blue -> Purple`). It is **STRICTLY FORBIDDEN** to spawn `swarm` workers or parallel subagents when executing via `/solo` or when the user did not explicitly invoke `/teamwork` or request parallel workers.
- **Opt-In (`/teamwork` — Multi-Worker Parallel):** Only when explicitly invoked by the user, the Front-Door (`orchestrator`) routes intent and injects skill context before parallel worker execution on disjoint `[PARALLEL_OK]` milestones.

---

## 5. SPEC-DRIVEN PLANNING & EXECUTION PROTOCOL (/plan & /super-plan)
> **Mandatory Planning Guardrail (Autonomous Super-Plan Routing):** Whenever planning, roadmapping, architectural design, or `/plan` or `/super-plan` is invoked, automatically activate the **Spec-Driven Super-Plan Pipeline** (`.agent/skills/super-plan/SKILL.md` / `tools/design/super_plan_engine.py`). Depth adapts via **Dynamic Risk-Routing** (RiskScore):
> - **Tier 0 (Fast-Track Micro-Plan, <= 2 files):** Instant < 10s turnaround, single DAG milestone with AST anchors, zero MCQ interruptions.
> - **Tier 1 (Standard Plan, 3-5 files):** Execution DAG, concrete interfaces, typed manifests, and standard verification matrix.
> - **Tier 2 (Deep Architectural Super-Plan, >= 6 files):** Full 5-stage closed loop: AST Recon -> Ambiguity Gate (<= 3 MCQs with Counter-Arguments) -> Execution DAG + Typed Manifests -> Mechanical Mutation Sentinel -> Self-Healing DAG & Plan Harvesting to `docs/adr/`.

1. **Strict Grounding ("Read First – Plan Later"):** Strictly FORBIDDEN to propose modifying any file without first reading its current contents or inspecting symbols (`read_file`, `context_slicer.py`, `polyglot_ast_parser.py`). Zero blind guessing.
2. **Mandatory 4-Section Plan Template:** Every plan must strictly contain: Affected Files & Blast Radius (`[MODIFY]`/`[CREATE]`/`[DELETE]` with structural anchors `::Symbol`), Data Flow & Interfaces, Atomic Milestones (Execution DAG <= 3 files/milestone, `depends_on`, Circuit Breaker, Rollback Hook), and Verification Matrix (concrete test commands). Full specification template in `.agent/skills/super-plan/SKILL.md`.
3. **Formula ("Invariants + Constraints"):** Trigger `/plan` or `/super-plan` using: Context, Invariants, Edge cases, Done when. (See `.agent/skills/super-plan/SKILL.md`).
4. **Test-First Planning & Single-Agent `/solo` Default:** Verification Matrix explicitly enumerates deterministic test scenarios (`Input X -> Expect Error Y`). Default plan execution and handoffs to sequential Single-Agent `/solo` (`.agent/skills/solo/SKILL.md`, NO `swarm` workers or parallel subagents); only emit or parallelize `[PARALLEL_OK]` milestones when the user explicitly invokes `/teamwork`.
