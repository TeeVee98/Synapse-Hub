# AGENTS.md — AI Agent Operating Standards & Protocols (Enterprise QA Hub)

> **Scope:** Google Antigravity, Cursor, Claude Code, GitHub Copilot, Codex, Windsurf, and all AI/QA engineers working with automated testing suites.  
> All rules below are **MANDATORY** and must be consistently enforced across all projects linking to this Hub.

---

## 0. MANDATORY PRE-FLIGHT CONFIRMATION BLOCK

Before generating code, editing test scripts, or refactoring files, AI Agent **MUST** read the target project guide (`PROJECT_AI_GUIDE.md`) and **open every response with the standardized confirmation block:**

```text
> [OK] Loaded Skill Hub (agent-skills) & Project Guide (PROJECT_AI_GUIDE.md)
> [OK] Test Architecture: Clean POM — 100% locators encapsulated in Page Classes
> [OK] Mandatory Technique: Playwright Live Interaction (Survey real DOM/AOM before codifying)
> [OK] Operating Discipline: Truth Anchor (No Fake Pass) + Zero-Token Memory Cache
> [OK] Execution Plan: <1-3 concise bullet points outlining immediate actions>
```

---

## 1. CORE ARCHITECTURE & CODE STANDARDS

1. **Clean Page Object Model (POM):**
   - Test scripts (`Scripts/` or `tests/`) must contain only business workflow method calls from Page Classes.
   - **Strictly forbidden:** Raw XPaths, CSS selectors, or `findTestObject` calls inside test scripts.
   - All locators and DOM operations must be encapsulated in Page Classes extending `BasePage`.

2. **100% UTF-8 No BOM:**
   - All files (`.groovy`, `.java`, `.ts`, `.py`, `.json`, `.md`, `.ps1`, `.sh`) **must not** contain UTF-8 BOM (`0xEF, 0xBB, 0xBF`).

3. **Dynamic & Idempotent Test Data:**
   - Always use randomized identifiers with timestamps/prefixes (e.g., `BasePage.uniqueCode("AUTO_")` or `DataGenerator`) to eliminate DB unique key collisions during parallel runs.
   - Every creation test case must be paired with automated Teardown Cleanup.

4. **Synchronization & Smart Wait:**
   - Static sleeps (`Thread.sleep`) are strictly prohibited to prevent pipeline flakiness.
   - Use dynamic smart waits: element visibility checks, Angular `zone.isStable()`, or Playwright `waitForLoadState('networkidle')`.

---

## 2. PLAYWRIGHT LIVE INTERACTION PROTOCOL

1. **Mandatory 3-Stage Lifecycle:**
   - **Stage 1 (Discovery):** Survey live DOM/AOM using headless browser. Never guess URLs or selector attributes.
   - **Stage 2 (Script Creation):** Verify selectors on the live browser (100% hit rate under 200ms) before committing to Page Classes.
   - **Stage 3 (In-Place Self-Healing):** When a test fails, pause the browser at the failure point to inspect and heal the locator; do not re-run from scratch.
2. **Standard Configuration:** Pure headless mode, Full HD resolution `1920x1080`.

---

## 3. TRUTH ANCHOR & ZERO-HALLUCINATION DISCIPLINE

1. **Truth Anchor (No Fake Pass):**
   - If a test fails due to an application bug (AUT Bug), report the defect honestly. **Never relax assertion conditions, skip validation steps, or alter expected results to manufacture a fake pass.**
2. **No Lazy Truncation:**
   - Always output complete, directly executable code. Never use `// ... existing code ...` or `// TODO` in scripts.
3. **Strict Credential Security:**
   - Never commit raw plaintext passwords, secret tokens, or private keys to git. Always use environment variables or encrypted profiles.

---

## 4. MULTI-AGENT SWARM SYSTEM (AGENT ROLES)

This repository defines specialized multi-agent profiles:

1. **Lead QA Orchestrator (`orchestrator`):**
   - Ingests requirements, scopes tasks, decomposes work items, and coordinates specialized subagents.
2. **Live Interaction Explorer (`live-explorer`):**
   - Utilizes Playwright / browser tools to explore live DOM/AOM and extract durable selectors.
3. **Clean POM Crafter (`pom-crafter`):**
   - Designs Page Classes, encapsulates UI interaction methods, and generates Clean POM scripts.
4. **Test Execution Runner (`test-runner`):**
   - Dispatches headless test suites via CLI (KRE, Playwright, Gradle) and monitors execution.
5. **Failure Autopsy Analyst (`failure-analyst`):**
   - Conducts root-cause analysis (RCA) using `FAILED_*.png` screenshots and Allure reports.
6. **Quality Gatekeeper & Sentinel (`quality-gatekeeper`):**
   - Enforces 7 Quality Gates via `verify_all.py`, scans for fake passes via `infer_linter.py`, ensuring zero code smells before handoff.

---

## 5. CENTRALIZED TOOLS RUNBOOK

All quality control and audit tasks are dispatched via scripts in `tools/` (Refer to `tools/TOOLS_RUNBOOK.md`):

```bash
# 1. Run 7 Quality Gates Verification
python tools/verify_all.py

# 2. Run AST linter for fake passes and empty catches
python tools/infer_linter.py

# 3. Analyze code change impact
python tools/test_impact.py --git-diff

# 4. Filter and distill verbose CLI logs by 95%
python tools/distill_log.py <path_to_log>

# 5. Query zero-token error memory cache
python tools/cache_resolver.py query "<error_message>"
```
