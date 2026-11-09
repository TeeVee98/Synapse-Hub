---
trigger: always_on
description: Skill Resolution Precedence, Inter-Skill Coordination, and Anti-Collision Protocol enforcing Workspace-Local skills over external generic plugin skills.
---

# Skill Resolution Precedence & Anti-Collision Protocol

## 1. Non-Negotiable 3-Tier Precedence
`[Tier 1: Project-Local Skills] (.agents/skills/*)` > `[Tier 2: Core Rules] (.agents/rules/*)` > `[Tier 3: External Plugins] (generic plugins)`.
When a Tier 1 local skill exists, external generic plugin skills are **strictly suppressed**.

## 2. Suppression Rules (Tier 1 overrides Tier 3)
- **POM & Test Authoring:** Use `clean-pom-crafter` / `lam-script-generator`. Suppress generic QA/test plugins. Clean POM only; no raw XPaths in test scripts.
- **Code Review:** Use `senior-code-review` (6 pillars against git diff). Suppress generic PR reviewers.
- **Locator Healing:** Use `self-healing-locator` / `failure-autopsy-and-healing` (AOM diffing). Suppress generic locator healers.
- **Flaky Tests:** Use `flaky-test-sentinel-and-quarantine` (episodic SQLite memory + JUnit parsing).
- **Live Probing:** Use `playwright-live-interaction` (CDP idle 0 under 200ms). Suppress generic smart locators.
- **Accessibility:** Use `wcag-audit-patterns` (WCAG 2.2 A/AA); use Chrome DevTools MCP strictly for low-level node inspection.

## 3. Inter-Skill Coordination
- **Code Authoring:** `lean-code-ladder` decides *what* to build; `surgical-coding-principles` restricts *where* to touch.
- **Technical Debt:** `technical-debt-harvester` tracks `shortcut:` markers; `code-refactoring-refactor-clean` executes refactoring.
- **API Testing:** `api-spec-to-e2e-matrix` compiles test matrices; `api-network-mocking-interception` stubs routes/chaos faults.
- **DoD Gatekeeper:** `verification-before-completion` checks command evidence; `antigravity-test-sentinel` enforces 11 Gates.

## 4. Strict Prohibitions
1. **Zero Generic Boilerplate:** Never generate legacy Selenium, Cucumber, or `findTestObject` code.
2. **Zero Raw HTML Dumps:** Extract compact AOM subtrees (< 500 tokens); never dump raw HTML trees.
3. **Zero Unverified Assertions:** Never complete tasks without running fresh verification via `tools/verify_all.py`.
