---
trigger: on_demand
description: Rules for Autonomous Multi-Agent Swarm, Pure Headless Playwright Live interaction (1920x1080), Web-First Assertions, and Zero-Second Auth. Activated strictly when Web Playwright or browser automation suites are mounted.
---

# Mandatory Playwright Live Interaction & Swarm Protocols

> ⚠️ **Contextual Activation Scope:** This rule is activated ONLY when `playwright.config.*` exists or when running Web / Browser E2E automation. For pure API, Mobile Appium, or Performance tests, strictly adhere to their respective rules (`stack-auto-router.md`, `mobile_appium_rules.md`, `performance_testing_rules.md`) and do not apply browser session/viewport constraints.

1. **Autonomous Swarm FSM (5 Stages):**
   - Main AI acts as **Lead QA Orchestrator**, coordinating specialized subagents:
     * **`test-designer`:** Transforms requirements into risk-based test matrices (AI-RBT), 15-field validation checklists, and 12-column Excel test suites.
     * **`live-explorer`:** Probes live DOM/AOM via Playwright MCP (`browser_run_code_unsafe`).
     * **`pom-crafter`:** Generates Page Classes and test scripts (Clean POM Flat Architecture).
     * **`api-engineer`:** Compiles OpenAPI test matrices, verifies CDC contracts (Pact), and executes Newman CLI suites.
     * **`test-runner`:** Dispatches headless tests via CLI (Playwright, Katalon, Gradle, Pytest).
     * **`perf-engineer`:** Orchestrates JMeter, k6, Locust load profiles, real-time telemetry streaming, and APM bottleneck correlation.
     * **`failure-analyst`:** Diagnoses crashes via logs, `Screenshots/FAILED_*.png`, and Allure reports.
     * **`quality-gatekeeper`:** Sentinel enforcing 10 Quality Gates DoD, 100% UTF-8 No BOM, and zero bypasses.

2. **Anti-Redundancy Protocol:**
   - Single sign-on via Zero-Second Auth (`session.json` / `storageState`); never re-enter login forms.
   - Live Explorer emits JSON Data Contract -> Code Crafter consumes to codify. Zero redundant DOM rescanning.
   - Targeted re-tests only on failed cases; never re-run entire suites for single-case bug fixes.
   - Deep RCA only on actual FAILED cases; immediately accept PASSED runs.

3. **Mandatory Pure Headless Mode & Resolution Standard:**
   - All flow discovery, live probing, and bug fixing **MUST RUN IN PURE HEADLESS MODE** (`viewport: { width: 1920, height: 1080 }`). Never open GUI browser windows to steal user focus.

4. **Native Playwright Assertions & Zero-Sleep Standard:**
   - **Web-First Assertions Only:** Always utilize native auto-retrying matchers: `await expect(locator).toBeVisible()`, `await expect(locator).toBeEnabled()`, `await expect(locator).toHaveText(...)`.
   - **Zero Static Sleeps (AGENTS.md Rule 1.4):** Static delays (`page.waitForTimeout`, `time.sleep`, `Thread.sleep`) are strictly prohibited in test scripts. Synchronize via locator auto-waiting or `page.waitForLoadState('networkidle')`.
   - **Clean POM Locator Hierarchy:** Page Classes must prioritize semantic locators:
     1. User-facing ARIA role (`page.getByRole(...)`)
     2. Semantic test identifier (`page.getByTestId(...)`)
     3. Form label / placeholder (`page.getByLabel(...)`, `page.getByPlaceholder(...)`)
     4. Text content (`page.getByText(...)`)
     5. Resilient CSS selector
     6. Raw XPath (strictly encapsulated in Page Class; never in test scripts).

5. **5 Superpowers:** Zero-Second Auth (`storageState`), Direct API Seeding, Accessibility Tree (AOM), Multi-Context Dual Role, Route Mocking (`page.route`).
