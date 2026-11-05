---
trigger: always_on
description: Mandatory rules for Autonomous Multi-Agent Swarm, Pure Headless Playwright Live interaction (1920x1080), and Zero-Second Auth.
---

# Mandatory Rules: Autonomous Multi-Agent Swarm, Live Playwright & Failure Analysis

Mandatory for all test automation tasks in enterprise web test suites:

1. **Autonomous Swarm Orchestration:**
   - Main AI acts as **Lead QA Orchestrator**, executing directions from **Project Lead / QA Director** and coordinating 5 specialized subagents in a 5-Stage FSM:
     * **Live Interaction Explorer (live-explorer):** Probe live DOM/AOM via Playwright MCP (browser_run_code_unsafe).
     * **Automation Code Crafter (pom-crafter):** Generate Page Classes and test scripts adhering to Clean POM Flat Architecture.
     * **Test Execution Runner (test-runner):** Dispatch headless automated tests via CLI (Playwright, Katalon, Gradle, Pytest).
     * **Failure Analyst (failure-analyst):** Diagnose test crashes via logs, FAILED_*.png, and Allure reports; coordinate healing.
     * **Quality Gatekeeper (quality-gatekeeper):** Air-gap sentinel enforcing 10 Quality Gates DoD, 100% UTF-8 No BOM, and zero bypass logic.
2. **Anti-Redundancy Protocol:**
   - Single sign-on via Zero-Second Auth (session.json); never re-enter login forms.
   - Live Explorer emits JSON Data Contract -> Code Crafter consumes to codify; Orchestrator charts workflows. Zero redundant DOM rescanning.
   - Targeted re-tests only on failed cases; never re-run entire batches for single-case bug fixes.
   - Failure Analyst conducts deep RCA only on actual FAILED cases; immediately accept PASSED runs.
3. **Playwright Live Interaction & Mandatory Headless:**
   - All flow discovery, live probing, and bug fixing **MUST RUN IN PURE HEADLESS MODE**.
   - Do not open browser GUI windows to avoid stealing user desktop focus.
   - Maintain standard virtual Full HD `1920x1080` (`viewport: { width: 1920, height: 1080 }`).
4. **5 Superpowers & 5 AI Paradigms:**
   - Zero-Second Auth, Direct API Seeding, Accessibility Tree (AOM), Multi-Context Dual Role, Route Mocking.
   - Self-Healing Selectors, Multimodal Visual Assertions, Autonomous Fuzzing, CDP Deep Profiling, Multi-Agent Swarm.
5. **Reference Documentation:** Follow [SKILL.md](.agents/skills/playwright-live-interaction/SKILL.md) and [swarm_orchestration.md](.agents/skills/playwright-live-interaction/references/swarm_orchestration.md).
