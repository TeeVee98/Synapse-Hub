# AGENTS.md — Synapse-Hub Enterprise QA Guidelines for OpenAI Codex

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
- Precedence: System Guardrails > Core Project Rules (`PROJECT_AI_GUIDE.md`) > Local Skills (`.agents/skills/`) > Generic Plugins.
- **Tech Stack Baseline:** Python 3.10+ (Standard Library first), Node.js v18+ | macOS, Linux, Windows.
- **Target Frameworks:** Playwright (TS/Python), Katalon (Groovy), Pytest, Cypress, Selenium, k6/Locust.
- **Project Config:** `synapse.config.json` | `PROJECT_AI_GUIDE.md` | Native Test Suites (`tests/`).

### 0.2 PROMPT CACHING & IMMUTABLE PREFIX ARCHITECTURE
Sections 0 through 1.1 constitute an immutable anchor prefix engineered for >= 95% LLM KV prompt-cache hit rates across frontier reasoning models (GPT/Codex, Gemini, Claude, DeepSeek). Append dynamic task details after Section 1.1.

---

## ⚡ Quick Commands & Codex MCP Integration
- **Native Test Suite:** `npm test` (or `pytest`, `npx playwright test`)
- **Synapse Quality Gates (11 DoD Gates):** `npx @teevee98/synapse-hub verify`
- **AST Fake-Pass & Sleep Linter:** `npx @teevee98/synapse-hub lint ./tests`
- **Spec-Driven Planning & Single-Agent Loop:** `npx @teevee98/synapse-hub super-plan` | `npx @teevee98/synapse-hub solo` | `npx @teevee98/synapse-hub review`
- **Codex MCP Server (`.codex/config.toml`):** Prefer invoking the connected `synapse-hub` MCP tools directly when available:
  - `synapse_lint`, `synapse_verify`, `synapse_mutate`, `synapse_distill_logs`, `synapse_security_scan`
  - `analyze_project`, `auto_heal_failure`, `check_action_safety`, `check_contract_drift`, `query_memory_cache`
- **Codex Native Skills (`.agents/skills/`):** Before editing tests, Page Classes, API contracts, or security checks, read `PROJECT_AI_GUIDE.md` and the matching `.agents/skills/<skill-name>/SKILL.md` workflow first.

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
2. **Lean Senior Dev Protocol (7-Rung Ladder & YAGNI):**
   - Solve the whole problem with the smallest complete change; mark deliberate simplifications with `shortcut: <limit>, <when to upgrade>`.
3. **Risk-Conditioned Ceremonies:**
   - Emit `Ruling: <decision> — <rationale> — <cost if wrong>` on architectural forks and verify Nominal, Degradation, and Boundary scenarios.
4. **Bilingual & Gated Telemetry:**
   - Converse in the user's language; keep code, Page Classes, docstrings, and commits strictly in English.
   - Restrict status badges and risk notes to audit/DoD runs (`npx @teevee98/synapse-hub verify`).
5. **Scratchpad Sandbox:** Files inside `scratch/` are exempt from Clean POM and Author headers for rapid prototyping; never promote unreviewed code from `scratch/` to `tests/`.

---

## 4. EXECUTION MODE: SINGLE-AGENT (/solo) vs /teamwork
- **Default (`/solo` — Single-Agent Sequential):** Execute milestones sequentially in one active session (`Red -> Blue -> Purple`). It is **STRICTLY FORBIDDEN** to spawn `swarm` workers or parallel subagents unless `/teamwork` or parallel workers are explicitly requested.
- **Opt-In (`/teamwork` — Multi-Worker Parallel):** Only when explicitly invoked by the user, partition work onto disjoint `[PARALLEL_OK]` milestones.

---

## 5. SPEC-DRIVEN PLANNING & EXECUTION PROTOCOL (/plan & /super-plan)
1. **Strict Grounding ("Read First – Plan Later"):** Always read target files and existing symbols before proposing edits.
2. **Structured Plan:** List Affected Files & Blast Radius, Interfaces/Data Flow, Atomic Milestones (`<= 3` files per milestone with rollback hook), and Verification Matrix (concrete test commands).
3. **Test-First Sequential Execution (`/solo` vs `/teamwork`):** Default to sequential Single-Agent `/solo` execution in one session (no `swarm` workers or parallel subagents unless `/teamwork` is explicitly invoked); define failing scenarios upfront and verify with native test runners (`npm test`, `pytest`, `npx playwright test`) or `npx @teevee98/synapse-hub verify`.
