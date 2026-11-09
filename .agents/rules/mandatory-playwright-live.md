---
trigger: always_on
description: Mandatory rules for Autonomous Multi-Agent Swarm, Pure Headless Playwright Live interaction (1920x1080), and Zero-Second Auth.
---

# Mandatory Playwright Live Interaction & Swarm Protocols

1. **Autonomous Swarm FSM (5 Stages):**
   - Main AI acts as **Lead QA Orchestrator**, coordinating specialized subagents:
     * **`test-designer`:** Transforms requirements into risk-based test matrices (AI-RBT), 15-field validation checklists, and 12-column Excel test suites.
     * **`live-explorer`:** Probes live DOM/AOM via Playwright MCP (`browser_run_code_unsafe`).
     * **`pom-crafter`:** Generates Page Classes and test scripts (Clean POM Flat Architecture).
     * **`api-engineer`:** Compiles OpenAPI test matrices, verifies CDC contracts (Pact), and executes Newman CLI suites.
     * **`test-runner`:** Dispatches headless tests via CLI (Playwright, Katalon, Gradle, Pytest).
     * **`perf-engineer`:** Orchestrates JMeter, k6, Locust load profiles, real-time telemetry streaming, and APM bottleneck correlation.
     * **`failure-analyst`:** Diagnoses crashes via logs, `Screenshots/FAILED_*.png`, and Allure reports.
     * **`quality-gatekeeper`:** Sentinel enforcing 11 Quality Gates DoD, 100% UTF-8 No BOM, and zero bypasses.
2. **Anti-Redundancy Protocol:**
   - Single sign-on via Zero-Second Auth (`session.json`); never re-enter login forms.
   - Live Explorer emits JSON Data Contract -> Code Crafter consumes to codify. Zero redundant DOM rescanning.
   - Targeted re-tests only on failed cases; never re-run entire suites for single-case bug fixes.
   - Deep RCA only on actual FAILED cases; immediately accept PASSED runs.
3. **Mandatory Pure Headless Mode:**
   - All flow discovery, live probing, and bug fixing **MUST RUN IN PURE HEADLESS MODE** (`viewport: { width: 1920, height: 1080 }`). Never open GUI browser windows to steal user focus.
4. **5 Superpowers:** Zero-Second Auth, Direct API Seeding, Accessibility Tree (AOM), Multi-Context Dual Role, Route Mocking.
