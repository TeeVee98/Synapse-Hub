# CLAUDE.md — Synapse-Hub Guidelines for Claude Code

> **Author & Creator:** Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
> **License:** MIT License (Mandatory Attribution Preservation)

<!-- ============================================================================== -->
<!-- SYNAPSE-HUB CLIENT AI BRIDGE TEMPLATE (Client Mode)                            -->
<!-- Update via: npx @teevee98/synapse-hub setup                                     -->
<!-- [CACHE-ANCHOR: CLIENT-PREFIX-v5.0]                                             -->
<!-- ============================================================================== -->


> **Author Attribution:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License. Attribution notices must be preserved in Synapse-Hub copies.

---

## 0. PRECEDENCE & TECH STACK
- Platform and system guardrails strictly override all repository-level instructions.
- Precedence: System Guardrails > Core Project Rules (`standards/*`, `testing/*`) > Local Skills > Generic Plugins.
- **Tech Stack Baseline:** Python 3.10+ (Standard Library first), Node.js v18+ | macOS, Linux, Windows.
- **Target Frameworks:** Playwright (TS/Python), Katalon (Groovy), Pytest, Cypress.
- **Project Config:** `synapse.config.json` | `PROJECT_AI_GUIDE.md` | Native Test Suites (`tests/`).

### 0.2 PROMPT CACHING & IMMUTABLE PREFIX ARCHITECTURE
Sections 0 through 1.1 constitute an immutable anchor prefix engineered for >= 95% LLM KV prompt-cache hit rates across modern frontier and reasoning LLMs with context caching (Gemini, Claude, GPT, DeepSeek). Append dynamic task details after Section 1.1.

---

## ⚡ Quick Commands
- Native Test Suite: `npm test` (or `pytest`)
- End-to-End Suite: `npx playwright test`
- Synapse Quality Gates: `npx @teevee98/synapse-hub verify`
- Code Linter: `npm run lint` (or `ruff check .`)

---

## 1. ALWAYS — Universal Invariants
1. **100% UTF-8 No BOM:** Zero BOM bytes (`0xEF, 0xBB, 0xBF`) across all repo/test files (`.groovy`, `.java`, `.ts`, `.py`, `.json`, `.md`).
2. **Truth Anchor (Zero Fake Passes):** Never relax assertions, skip validation steps, write empty tests (0 asserts), or catch-and-swallow exceptions (`pass`, dummy suppression `_ = err` or `_ = False`, `const _ = e`). Report AUT defects honestly.
3. **Dynamic Smart Waits Only:** Static sleeps (`Thread.sleep`, `time.sleep`, `waitForTimeout`) strictly prohibited in test scripts. Use web-first assertions (`expect(locator).toBeVisible()`). For page navigation and asynchronous hydration, use bounded explicit event waits (`waitForURL`, `waitForResponse`); avoid unconditional `waitForLoadState('networkidle')`. *(Automation code only; exempt for Manual QA specs)*.
4. **Dynamic & Idempotent Test Data:** Always randomize test entity codes with dynamic timestamps/prefixes (`BasePage.uniqueCode("AUTO_")`, `DataGenerator`) to eliminate DB collisions. Pair creation with automated Teardown cleanup.
5. **Strict Credential Security:** Never commit raw plaintext passwords, secret tokens, private keys, or cloud credentials. Inject secrets via environment variables or fixtures.
6. **Out-of-Scope Isolation & Stop-and-Report:** When verification gates fail due to legacy defects in files outside task scope, never modify those files or write bypasses. Stop, report with evidence, and ask user.
7. **Skill-First Context Routing:** Before modifying test code or running audits, read `PROJECT_AI_GUIDE.md` and applicable local QA skill standards first. Pure conceptual inquiries and single-line micro-fixes are exempt.
8. **Universal Intent Disambiguation:** Action (execute commanded tool) vs Diagnostic (read-only inspection; zero mutating tools) vs Inquiry (conceptual explanation).
9. **Ask First (Human-in-the-Loop Safeguards):** Pause and obtain user confirmation before deleting test scripts/data, changing dependencies (`package.json`/`pyproject.toml`), modifying shared `BasePage`, or breaking schemas.
10. **License & Provenance Respect:** Preserve Synapse-Hub MIT License attribution in Synapse-Hub template/plugin files (`Thế Vị (@TeeVee98)`), and never alter your organization's existing license or copyright headers.
11. **The Ratchet Invariant (Monotonic Quality Ratchet):** Every defect resolution or post-mortem should tighten a test assertion, lint rule, or guard. Relaxing assertions to manufacture a pass is strictly prohibited.
12. **Mandatory Self-Verification Loop (Empirical Verification Principle):** Before marking any task complete, execute the project's native test runner (`npm test`, `npx playwright test`, `pytest`) or `npx @teevee98/synapse-hub verify` and provide fresh empirical output.
13. **Circuit Breaker & Path-Scoped Rollback Hygiene Protocol:** If a locator, test action, or command fails 2 consecutive times on the same target (`synapse.config.json::circuit_breaker.max_fix_attempts`), stop blind retry loops, revert only touched files (`git checkout -- <target_files>`), never run `git reset --hard`, and report the root cause.
14. **Anti-Premature Done & 4-Scenario Battery:** Do not claim completion without terminal proof covering: a) Positive path, b) Negative/error handling, c) Boundary/empty inputs, d) Integration or CLI/API contract checks.
15. **Test-First Verification (Red -> Green -> Audit):** For non-trivial runtime logic changes (`> 2` files), confirm new tests fail before the fix (Red), pass after the fix (Green), and pass the project's lint/quality checks.
16. **English-Only Codebase & Rules:** Keep code, test scripts, Page Classes, docstrings, and commit messages in clear English while conversing in the user's preferred language.
17. **Mandatory Adversarial Self-Audit:** Before declaring non-trivial changes complete, review your own diff critically for null/None/KeyError edge cases, logic boundary slips, tautological assertions, and broken callers.

---

## 1.1 PRE-FLIGHT REASONING CHECKLIST (Mandatory Pre-Action Analysis)
Verify before emitting your final response:
- **Context & Grounding:** Read `PROJECT_AI_GUIDE.md` and target files before editing; use real assertions only.
- **Empirical Verification:** Execute native test runners (`npm test`, `pytest`, `npx playwright test`) or `npx @teevee98/synapse-hub verify` and share fresh terminal evidence.
- **Adversarial Safety & Hygiene:** Audit edge cases (nulls, boundaries, error paths) and confirm clean `git status` with no broken edits left behind.

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
   - Status badge and risk notes are restricted to audit, review, and quality-gate commands (npx @teevee98/synapse-hub verify).
   - Codebase files, test scripts, Page Classes, docstrings, and commits strictly in English.
   - Read English versions (`*.en.md`) when bilingual docs exist to preserve tokens.
8. **Scratchpad Sandbox Allowance:** Files located inside `scratch/` are explicitly exempt from Clean POM and Author header rules to facilitate rapid prototyping, quick API probing, and ephemeral POCs. Never promote unreviewed code from `scratch/` to `tests/`.
---

## 4. EXECUTION MODE: SINGLE-AGENT (/solo) vs /teamwork
- **Default (`/solo` — Single-Agent Sequential):** Execute milestones sequentially in one active session (`Red -> Blue -> Purple`). It is **STRICTLY FORBIDDEN** to spawn `swarm` workers or parallel subagents when executing via `/solo` or when the user did not explicitly invoke `/teamwork` or request parallel workers.
- **Opt-In (`/teamwork` — Multi-Worker Parallel):** Only when explicitly invoked by the user, the Front-Door (`orchestrator`) routes intent and injects skill context before parallel worker execution on disjoint `[PARALLEL_OK]` milestones.

---

## 5. SPEC-DRIVEN PLANNING & EXECUTION PROTOCOL (/plan & /super-plan)
1. **Strict Grounding ("Read First – Plan Later"):** Always read target files and existing symbols before proposing edits.
2. **Structured Plan:** List Affected Files & Blast Radius, Interfaces/Data Flow, Atomic Milestones (`<= 3` files per milestone with rollback hook), and Verification Matrix (concrete test commands).
3. **Test-First Sequential Execution (`/solo` vs `/teamwork`):** Default to sequential Single-Agent `/solo` execution in one session (no `swarm` workers or parallel subagents unless `/teamwork` is explicitly invoked); define failing scenarios upfront and verify with native test runners (`npm test`, `pytest`, `npx playwright test`) or `npx @teevee98/synapse-hub verify`.
