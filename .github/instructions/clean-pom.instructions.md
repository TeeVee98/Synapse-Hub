---
applyTo: "**/*Page.*,**/*.spec.*,**/*.test.*,**/TC-*.groovy,**/Keywords/**/*.groovy,**/Scripts/**/*.groovy"
description: "Enforces Clean Page Object Model (POM), Flat Architecture, Zero Raw Locators in test scripts, and Smart Dynamic Waits across all test files."
---

<!-- ============================================================================== -->
<!-- AUTO-GENERATED FROM AGENTS.md — DO NOT EDIT DIRECTLY.                          -->
<!-- Run: python3 tools/core/sync_agent_rules.py                                     -->
<!-- [CACHE-ANCHOR: ROOT-PREFIX-v4.8]                                               -->
<!-- ============================================================================== -->


# Clean Page Object Model (POM) & Flat Architecture Standards

> **Scope:** Applied automatically by GitHub Copilot to all Page Classes, Test Scripts, and Keyword files.
> **Rule Invariant:** Test scripts must contain ONLY business workflow method calls on Page Classes.

## 0. PRECEDENCE & SAFETY INVARIANT
Platform and system guardrails strictly supersede all repository instructions.

## 1. ALWAYS — Universal Invariants
1. **Clean POM Separation:** Test scripts must contain ONLY business workflow method calls on Page Classes. (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
2. **Zero Raw Locators in Scripts:** Strictly prohibited from putting raw XPaths, CSS selectors, or inline element lookups inside test scripts.
3. **Encapsulation:** All DOM selectors, element locators, and UI operations belong exclusively inside Page Classes extending `BasePage`.
4. **Dynamic Smart Waits (Zero Static Sleep):** Prohibit `Thread.sleep(...)` and `time.sleep(...)`. Use dynamic smart waits (`waitForLoadState('networkidle')`). (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
5. **Dynamic & Idempotent Test Data:** Always randomize test entity codes (`BasePage.uniqueCode("AUTO_")`). Pair creation with automated Teardown.
6. **Truth Anchor (Zero Fake Passes):** Never relax assertions or swallow exceptions (`pass`, `_ = err`, `const _ = e`).

## 2. RECOMMENDED — Best Practices
- Flat Architecture: Keep Page Object inheritance shallow (maximum 1 level of inheritance from `BasePage`).
- Lean Senior Dev: Minimal necessary lines; mark shortcuts with `shortcut: <limit>, <upgrade>`.
- 100% UTF-8 No BOM across all test and source files.
