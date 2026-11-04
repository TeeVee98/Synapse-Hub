---
trigger: always_on
description: Skill Resolution Precedence, Inter-Skill Coordination, and Anti-Collision Protocol enforcing Workspace-Local skills over external generic plugin skills.
---

# Skill Resolution Precedence & Anti-Collision Protocol

> **Purpose:** Resolve overlapping trigger scopes between Project-Local Skills and External Plugins, eliminating context contagion, token bloat, and conflicting instructions.

---

## 1. Non-Negotiable 3-Tier Precedence Order
`[Tier 1: Project-Local Skills] (.agents/skills/*)` > `[Tier 2: Core Rules] (.agents/rules/*)` > `[Tier 3: External Plugins] (generic plugins)`.
Whenever a Tier 1 local skill exists, the external plugin skill is **strictly suppressed**.

---

## 2. External Plugin Suppression Rules (Tier 1 overrides Tier 3)
- **POM & Test Authoring:** Use `clean-pom-crafter` / `lam-script-generator`. Suppress generic QA/test plugins. Flat Clean POM only; no raw XPaths in test scripts.
- **Code Review:** Use `senior-code-review` (6 pillars against git diff). Suppress generic PR reviewers.
- **Locator Healing:** Use `self-healing-locator` / `failure-autopsy-and-healing` (AOM diffing). Suppress generic locator healers.
- **Flaky Test Triage:** Use `flaky-test-sentinel-and-quarantine` (episodic SQLite memory + JUnit parsing).
- **Live Probing:** Use `playwright-live-interaction` (CDP idle 0 under 200ms). Suppress generic smart locators.
- **Accessibility:** Use `wcag-audit-patterns` for WCAG 2.2 A/AA criteria; use Chrome DevTools MCP strictly for low-level node inspection.

---

## 3. Internal Inter-Skill Coordination & Boundaries
- **Code Authoring:** `lean-code-ladder` decides *what* to build (7-rung ladder); `surgical-coding-principles` restricts *where* to touch (surgical git diff).
- **Technical Debt:** `technical-debt-harvester` tracks `shortcut:` markers; `code-refactoring-refactor-clean` executes refactoring.
- **Quality Review:** `senior-code-review` audits source diffs; `review-spec` audits requirements/stories (0-context stress test).
- **System Audit:** `tools/analyze_project.py` gathers facts (AST, env, gates); `repo-quality-audit` prioritizes "Fix #1 first".
- **API Testing:** `api-spec-to-e2e-matrix` compiles test matrices; `api-network-mocking-interception` stubs routes and chaos faults.
- **Failure Analysis:** `self-healing-locator` heals individual locators; `failure-autopsy-and-healing` triages suite-wide crashes.
- **DoD Gatekeeper:** `verification-before-completion` checks fresh command evidence; `antigravity-test-sentinel` enforces all 10 gates.

---

## 4. Strict Prohibitions
1. **Zero Generic Boilerplate:** Never generate legacy Selenium, Cucumber, or `findTestObject` code.
2. **Zero Raw HTML Dumps:** Extract compact AOM subtrees (< 500 tokens); never dump raw HTML trees.
3. **Zero Unverified Assertions:** Never complete tasks without running fresh verification via `tools/verify_all.py`.
