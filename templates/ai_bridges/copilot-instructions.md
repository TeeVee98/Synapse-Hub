# GitHub Copilot Custom Instructions for Synapse-Hub

<!-- ============================================================================== -->
<!-- SYNAPSE-HUB CLIENT AI BRIDGE TEMPLATE (Client Mode)                            -->
<!-- Update via: npx @teevee98/synapse-hub setup                                     -->
<!-- [CACHE-ANCHOR: CLIENT-PREFIX-v5.0]                                             -->
<!-- ============================================================================== -->


> **Project:** Synapse-Hub Enterprise QA Automation
> **Author:** Thế Vị (@TeeVee98) — MIT License

## 0. PRECEDENCE & SAFETY INVARIANT
- Platform and system guardrails strictly override all repository-level instructions.
- Runtime Baseline: Python 3.10+ (stdlib-first), Node.js v18+ | Target: Playwright, Katalon, Pytest.
- Prompt Caching Invariant: Sections 0 through 1.1 form an immutable anchor prefix for >= 95% KV cache hits across modern frontier and reasoning LLMs with context caching (Gemini, Claude, GPT, DeepSeek).

## 1. ALWAYS — Universal Invariants
- **100% UTF-8 No BOM:** Zero BOM bytes (`0xEF, 0xBB, 0xBF`) across all repo/test files (`.groovy`, `.java`, `.ts`, `.py`, `.json`, `.md`).
- **Truth Anchor (Zero Fake Passes):** Never relax assertions, skip validation steps, write empty tests (0 asserts), or catch-and-swallow exceptions (`pass`, dummy suppression `_ = err` or `_ = False`, `const _ = e`). Report AUT defects honestly.
- **Dynamic Smart Waits Only:** Static sleeps (`Thread.sleep`, `time.sleep`, `waitForTimeout`) strictly prohibited in test scripts. Use web-first assertions (`expect(locator).toBeVisible()`). For page navigation and asynchronous hydration, use bounded explicit event waits (`waitForURL`, `waitForResponse`); avoid unconditional `waitForLoadState('networkidle')`. *(Automation code only; exempt for Manual QA specs)*.
- **Dynamic & Idempotent Test Data:** Always randomize test entity codes with dynamic timestamps/prefixes (`BasePage.uniqueCode("AUTO_")`, `DataGenerator`) to eliminate DB collisions. Pair creation with automated Teardown cleanup.
- **Strict Credential Security:** Never commit raw plaintext passwords, secret tokens, private keys, or cloud credentials. Inject secrets via environment variables or fixtures.
- **Out-of-Scope Isolation & Stop-and-Report:** When verification gates fail due to legacy defects in files outside task scope, never modify those files or write bypasses. Stop, report with evidence, and ask user.
- **Skill-First Context Routing:** Before modifying test code or running audits, read `PROJECT_AI_GUIDE.md` and applicable local QA skill standards first. Pure conceptual inquiries and single-line micro-fixes are exempt.
- **Universal Intent Disambiguation:** Action (execute commanded tool) vs Diagnostic (read-only inspection; zero mutating tools) vs Inquiry (conceptual explanation).
- **Ask First (Human-in-the-Loop Safeguards):** Pause and obtain user confirmation before deleting test scripts/data, changing dependencies (`package.json`/`pyproject.toml`), modifying shared `BasePage`, or breaking schemas.
- **License & Provenance Respect:** Preserve Synapse-Hub MIT License attribution in Synapse-Hub template/plugin files (`Thế Vị (@TeeVee98)`), and never alter your organization's existing license or copyright headers.
- **The Ratchet Invariant (Monotonic Quality Ratchet):** Every defect resolution or post-mortem should tighten a test assertion, lint rule, or guard. Relaxing assertions to manufacture a pass is strictly prohibited.
- **Mandatory Self-Verification Loop (Empirical Verification Principle):** Before marking any task complete, execute the project's native test runner (`npm test`, `npx playwright test`, `pytest`) or `npx @teevee98/synapse-hub verify` and provide fresh empirical output.
- **Circuit Breaker & Path-Scoped Rollback Hygiene Protocol:** If a locator, test action, or command fails 2 consecutive times on the same target (`synapse.config.json::circuit_breaker.max_fix_attempts`), stop blind retry loops, revert only touched files (`git checkout -- <target_files>`), never run `git reset --hard`, and report the root cause.
- **Anti-Premature Done & 4-Scenario Battery:** Do not claim completion without terminal proof covering: a) Positive path, b) Negative/error handling, c) Boundary/empty inputs, d) Integration or CLI/API contract checks.
- **Test-First Verification (Red -> Green -> Audit):** For non-trivial runtime logic changes (`> 2` files), confirm new tests fail before the fix (Red), pass after the fix (Green), and pass the project's lint/quality checks.
- **English-Only Codebase & Rules:** Keep code, test scripts, Page Classes, docstrings, and commit messages in clear English while conversing in the user's preferred language.
- **Mandatory Adversarial Self-Audit:** Before declaring non-trivial changes complete, review your own diff critically for null/None/KeyError edge cases, logic boundary slips, tautological assertions, and broken callers.

---

## 1.1 PRE-FLIGHT REASONING CHECKLIST
Verify before emitting your final response:
- **Context & Grounding:** Read `PROJECT_AI_GUIDE.md` and target files before editing; use real assertions only.
- **Empirical Verification:** Execute native test runners (`npm test`, `pytest`, `npx playwright test`) or `npx @teevee98/synapse-hub verify` and share fresh terminal evidence.
- **Adversarial Safety & Hygiene:** Audit edge cases (nulls, boundaries, error paths) and confirm clean `git status` with no broken edits left behind.

## 2. RECOMMENDED — Best Practices
- Enforce Clean Page Object Model (POM) with Flat Architecture. (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
- Zero XPaths or CSS selectors inside test scripts. Encapsulate all element locators inside Page Classes.
- Lean Senior Dev: Solve the whole task with the least new code (7-rung ladder); mark shortcuts with `shortcut: <limit>, <upgrade>`.
- Condition autonomous ceremonies (rulings, 3-scenario falsification) on task complexity.
- Converse with the user in Vietnamese; output all code, Page Classes, and comments in English.
- Execution Mode (`/solo` vs `/teamwork`): Default to sequential Single-Agent `/solo` in one session; strictly FORBIDDEN to spawn `swarm` workers or parallel subagents unless `/teamwork` or parallel workers are explicitly requested.
- Spec-Driven Planning (/plan & /super-plan): Read target files before proposing edits, split work into atomic milestones (<= 3 files), verify with concrete test commands, and default handoffs to `/solo`.
- Test-First Verification: Certify Red -> Green transitions and perform an adversarial edge-case self-audit before completion.
- Scratchpad Sandbox: Files inside scratch/ are exempt from Clean POM and Author header checks for rapid prototyping.
