---
name: playwright-webapp-testing
description: "Drive Playwright test runs against a local web application with a managed server lifecycle: start, wait for readiness, run automation, and guarantee teardown. Use when verifying frontend functionality or debugging UI behavior of a dynamic webapp that must be started before testing."
category: test_automation_and_execution
version: "1.1.0"
policies:
  network: localhost-only
  shell: workspace-sandbox
  filesystem: workspace-sandbox
---
# Playwright Webapp Testing — Managed Server Lifecycle

> **Canonical Delegation:** Consolidated under [`e2e-testing-patterns`](../e2e-testing-patterns/SKILL.md). Browser configuration, Smart Waits, sharding, and Clean POM rules live in `e2e-testing-patterns` and `clean-pom-crafter`; this skill strictly owns the **local dev-server lifecycle wrapper**.
>
> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Drive Playwright test runs against a local web application with a managed server lifecycle: start, wait for readiness, run automation, and guarantee teardown. Use when verifying frontend functionality or debugging UI behavior of a dynamic webapp that must be started before testing.
- **Activation Scope:** Local dynamic web applications requiring subprocess startup/health-polling before Playwright execution.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
  - Do NOT leave dangling dev server processes after test completion or failure.
  - Do NOT hardcode colliding fixed ports across parallel CI jobs.
  - Do NOT use `time.sleep()`, `Thread.sleep()`, `waitForTimeout()`, or unconditional `networkidle` waits.
- **Sibling Skill Boundaries:**
  - `e2e-testing-patterns`: owns headless `1920x1080` config, Clean POM patterns, retries, and CI sharding.
  - `playwright-live-interaction`: owns interactive live DOM/AOM probing.

---

## 3. Ordered Execution Workflow

1. **Decision Tree:** If the target is static HTML, inspect HTML directly; if dynamic and already running, probe via `playwright-live-interaction`; otherwise run the lifecycle contract below.
2. **Server Lifecycle Contract:**
   - **Spawn:** Launch frontend/backend commands using dynamically allocated ports (or isolated checkout worktree state so parallel runs never fight shared user-data dirs).
   - **Doctor Preflight:** Run a read-only check before driving (`process up`, expected build/version, port owned by this run, auth valid) so stale bundles never produce false evidence.
   - **Readiness Poll:** Poll health endpoints/TCP ports until ready (`domcontentloaded` + targeted selector / `wait_for_url` in the test).
   - **Execute:** Run headless Playwright tests following `e2e-testing-patterns` & `clean-pom-crafter` (Reference: [server_lifecycle_playwright.py](examples/server_lifecycle_playwright.py)). For user-POV feature coverage, map journeys using `templates/verification/FEATURE_MAP_TEMPLATE.md` (`Sub-features`, `How to get to it (user POV)`, `Driving it`, `Gotchas`).
   - **Unconditional Evidence-Preserving Cleanup:** Terminate server process groups inside `finally` even on failure (kill only PIDs started by this run, never by global process name), and preserve proof artifacts (traces, screenshots, logs) outside scratch cleanup paths.
3. **Failure Triage:** Distill verbose console/network logs with `tools/core/distill_log.py` before reporting.

### Attribution

Adapted from **webapp-testing** in anthropics/skills (https://github.com/anthropics/skills) — Apache License 2.0, Copyright 2026 Anthropic, PBC, rescoped to Synapse Hub standards.

---

## 4. Verification Points & DoD

1. Local server readiness verified before browser launch and terminated in `finally`.
2. Headless `1920x1080` Playwright run completes with trace/screenshot capture on failure and exit code 0.
3. Zero static sleeps; prohibit unconditional `networkidle` calls in lifecycle or test code.

---

## 5. Handoff Protocol

- **Deliverables:** Managed lifecycle runner, Playwright config (`playwright.config.ts` / `pytest.ini`), and distilled execution report.
- **Next Subagent:** `test-runner`
- **Output Format:** Lifecycle wrapper script, structured JSON telemetry, or validated markdown handoff.
