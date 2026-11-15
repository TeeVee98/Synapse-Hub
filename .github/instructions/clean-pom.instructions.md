---
applyTo: "**/*Page.*,**/*.spec.*,**/*.test.*,**/TC-*.groovy,**/Keywords/**/*.groovy,**/Scripts/**/*.groovy"
description: "Enforces Clean Page Object Model (POM), Flat Architecture, Zero Raw Locators in test scripts, and Smart Dynamic Waits across all test files."
---

# Clean Page Object Model (POM) & Flat Architecture Standards

> **Scope:** Applied automatically by GitHub Copilot to all Page Classes, Test Scripts, and Keyword files.  
> **Rule Invariant:** Test scripts must contain ONLY business workflow method calls on Page Classes.

## 1. Clean POM Separation Invariants
- **Zero Raw Locators in Scripts:** Strictly prohibited from putting raw XPaths, CSS selectors, or `findTestObject(...)` inside test scripts (`tests/`, `Scripts/`, `*.spec.*`).
- **Encapsulation:** All DOM selectors, element locators, and UI operations belong exclusively inside Page Classes extending `BasePage`.
- **Flat Architecture:** Keep Page Object inheritance shallow (maximum 1 level of inheritance from `BasePage`). Avoid deep inheritance chains.

## 2. Dynamic Smart Waits (Zero Static Sleep)
- **Strictly Prohibited:** `Thread.sleep(...)`, `time.sleep(...)`, or arbitrary static timeouts.
- **Mandatory Alternative:** Use dynamic smart waits:
  - Playwright: Auto-waiting and `page.waitForLoadState('networkidle')`.
  - Cypress: Web-first assertions with automatic retry (`cy.get(...).should('be.visible')`).
  - Selenium / Katalon: ExpectedConditions checking visibility/clickable states (`waitForElementVisible`).

## 3. Dynamic & Idempotent Test Data
- Always randomize test entity codes with timestamps and prefixes (`BasePage.uniqueCode("AUTO_")` or `DataGenerator.uniqueId()`) to eliminate database primary key collisions.
- Every data creation test case must be paired with automated Teardown cleanup.

## 4. Truth Anchor (Zero Fake Passes)
- Never relax assertions, skip validation steps, or catch-and-swallow exceptions (`pass`, `_ = err`, `const _ = e`).
- Non-trivial logic must leave explicit assertions before completion.
