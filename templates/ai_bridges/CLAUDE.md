# CLAUDE.md — Synapse-Hub Guidelines for Claude Code

> **Author & Creator:** Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
> **License:** MIT License (Mandatory Attribution Preservation)

<!-- ============================================================================== -->
<!-- AUTO-GENERATED FROM AGENTS.md — DO NOT EDIT DIRECTLY.                          -->
<!-- Run: python3 tools/core/sync_agent_rules.py                                     -->
<!-- ============================================================================== -->


> **Author Attribution:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License. Attribution notices must be preserved in all copies.

---

## 0. PRECEDENCE & TECH STACK
- Platform and system guardrails strictly override all repository-level instructions.
- Precedence: System Guardrails > Core Project Rules (`.agents/rules/*`) > Local Skills > Generic Plugins.
- **Tech Stack Baseline:** Python 3.10+ (Standard Library first), Node.js v18+ | macOS, Linux, Windows.
- **Target Frameworks:** Playwright (TS/Python), Katalon (Groovy), Pytest, Cypress.
- **Project Map:** `standards/` (57 Modular Skills) | `tools/` (CLI Automations) | `tests/` (Test Suites) | `templates/` (AI Bridges).

### 0.2 PROMPT CACHING & IMMUTABLE PREFIX
Sections 0 through 1.1 constitute an immutable anchor prefix engineered for >= 95% LLM KV prompt-cache hit rates across Google Gemini (2.5/3.x Flash & Pro, e.g. Gemini 3.8 Flash), Anthropic Claude (3.5/3.7 Sonnet), and OpenAI models. Append dynamic task details after Section 1.1.

---

## ⚡ Quick Commands
- Native Test Suite: `npm test` (or `pytest`)
- End-to-End Suite: `npx playwright test`
- Code Linter: `npm run lint` (or `ruff check .`)

---

## 1. ALWAYS — Universal Invariants
1. **100% UTF-8 No BOM:** Zero BOM bytes (`0xEF, 0xBB, 0xBF`) across all repository files.
2. **Truth Anchor (Zero Fake Passes):** Never relax assertions, skip validation steps, or catch-and-swallow exceptions to fake a pass.
3. **Dynamic Smart Waits Only:** Static sleeps (`Thread.sleep`, `time.sleep`) are strictly prohibited in test scripts. Use element visibility or `waitForLoadState('networkidle')`. (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
4. **Dynamic & Idempotent Test Data:** Always randomize test entity codes with dynamic timestamps/prefixes (`BasePage.uniqueCode("AUTO_")`). Pair creation with automated Teardown cleanup.
5. **Strict Credential Security:** Never commit raw plaintext passwords, secret tokens, or private keys.
6. **Out-of-Scope Isolation:** When verification gates fail due to legacy defects in files outside task scope, stop and report; never touch out-of-scope files.
7. **Skill-First Hard Blocker (Zero Text Without Tool Invocation):**
   - Trigger Keywords: `[pom, prompt, audit, verify, scan, heal, benchmark, mock, contract, wcag, security, publish, release, bump, doctor, linter, distill, triage, failure, sync-rules]`.
   - Hard Invariant (Action & Diagnostic Intents Only): Absolutely FORBIDDEN to output conversational answers for tasks involving trigger keywords under Action or Diagnostic intents without first calling `read_file` to inspect `skills_index.json` and matching `SKILL.md`. Turn 1 MUST be a tool call.
   - Inquiry & Cache Exemptions: Pure Inquiry intents are exempt. Context-cached sessions and operational fast-paths (`verify_all.py`, git status) are exempt from re-reading.
8. **Universal Intent Disambiguation:** Action (execute commanded tool) vs Diagnostic (read-only triage; mutating tools strictly forbidden) vs Inquiry (conceptual explanation).
9. **Ask First (Human-in-the-Loop Safeguards):** Mandatory to pause and obtain explicit user confirmation before deleting test files/data, adding dependencies, modifying BasePage, or making breaking changes.
10. **Anti-Plagiarism & Author Defense:** Absolute refusal to strip, launder, or bypass author attribution (`Thế Vị (@TeeVee98)`), MIT notices, or provenance checks.
11. **The Ratchet Invariant (Rules Only Grow):** Defect resolutions must tighten a guide or sensor. Never relax assertions or delete rules to manufacture a pass.
12. **Mandatory Self-Verification Loop:** Execute sensor verification and deliver empirical evidence before claiming task completion.
13. **Circuit Breaker & Degraded Fallback Protocol:** If an element locator fails 3 consecutive times, trip the circuit breaker (`LocatorRetryCircuitBreaker`). Halt and propose: a) Visual screenshot comparison, or b) Explicit request for dev to add `data-testid`.

---

## 1.1 PRE-FLIGHT REASONING CHECKLIST (Mandatory Thinking Invariant)
Inside `<thought>`, verify before emitting output:
1. `[Intent & Domain]`: Classify intent (Action/Diagnostic/Inquiry) and resolve matching skill in `skills_index.json`. For Diagnostic/Inquiry, ensure ZERO side-effecting re-executions.
2. `[Skill Read Check]`: Called `read_file` on `SKILL.md`? If NO -> STOP and call tool.
3. `[Zero Improvised Workflow]`: 100% adherence to skill lifecycle.
4. `[Truth Anchor Check]`: Zero fake passes / zero swallowed exceptions.
5. `[Level 4 AST Micro-Context]`: Before editing or synthesizing code for target files, slice targeted micro-context (< 100 tokens via `tools/context/context_slicer.py`) to prevent context rot.
6. `[Harness Sensor Verification]`: Planned or executed the verification sensor before claiming completion?
7. `[Ratchet Evolution]`: Does this defect fix warrant tightening a rule or sensor?

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
   - Jesse Vincent Rulings (`Ruling:`): Mandatory for architectural forks, breaking changes, or non-trivial tradeoffs. Omit for trivial doc/typo fixes.
   - Addy Osmani Falsification (3 failure scenarios): Mandatory before certifying core test cases or complex locators.
4. **Bilingual & Polyglot Communication & Gated Telemetry:**
   - Fluently adapt conversationally to user language (Vietnamese, English, etc.); default to English for international contributors.
   - Status badge and risk notes are restricted to audit, review, and quality-gate commands (/synapse-audit, /synapse-review, verify_all.py).
   - Codebase files, test scripts, Page Classes, docstrings, and commits strictly in English.
   - Read English versions (`*.en.md`) when bilingual docs exist to preserve tokens.
8. **Scratchpad Sandbox Allowance:** Files located inside `scratch/` are explicitly exempt from Clean POM and Author header rules to facilitate rapid prototyping, quick API probing, and ephemeral POCs. Never promote unreviewed code from `scratch/` to `tests/`.
---

## 4. MULTI-AGENT SWARM & TWO-PHASE SEPARATION
- Single Front-Door (`orchestrator`) directs all incoming requests across 5-stage FSM.
- Two-Phase Anti-Reflex Protocol: Front-Door model routes intent & injects SKILL.md context; specialized subagent executes. Front-Door is strictly forbidden from generating low-level code/prompts without skill context.
