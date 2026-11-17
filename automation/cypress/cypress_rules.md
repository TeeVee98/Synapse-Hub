---
trigger: on_demand
description: Enterprise Cypress automation standards, zero static waits, network aliasing with cy.intercept, data-cy locators, and clean custom commands.
profiles: [cypress, full]
---

# Enterprise Cypress Automation Standards & Rules

> **Scope:** Applies whenever designing, executing, or refactoring Cypress E2E automation suites (`*.cy.ts`, `*.cy.js`, `cypress.config.*`).  
> Enforces enterprise reliability, deterministic network synchronization, Clean POM Flat Architecture, and zero static sleeps.

---

## 1. Zero Static Delays & Dynamic Network Aliasing
1. **Strict Prohibition of Static Sleep (Universal Invariant):** Hardcoded numeric delays such as `cy.wait(5000)` or `cy.wait(ms)` are strictly prohibited in test scripts. Static sleeps introduce flakiness, degrade CI pipeline speed, and violate Synapse Hub Invariant 1.3.
2. **Mandatory Network Aliasing:** Always declare `cy.intercept(...).as('aliasName')` prior to user interactions that trigger asynchronous HTTP requests.
3. **Dynamic Response Synchronization:** Synchronize on network requests using `cy.wait('@aliasName')` or chain assertions directly on intercept properties:
   ```javascript
   cy.wait('@submitOrder').its('response.statusCode').should('eq', 200);
   ```
4. **Deterministic Route Mocking:** Use `cy.intercept()` stubs and fixtures for isolating flaky third-party APIs and simulating downstream failure states.

---

## 2. Locator Hierarchy & Priority Standards
1. **Priority 1 (Primary):** Dedicated Cypress test attributes: `[data-cy="..."]` (highest resilience against styling changes).
2. **Priority 2:** Standard test identifiers: `[data-testid="..."]` or `[data-test="..."]`.
3. **Priority 3:** Semantic text matchers (`cy.contains(...)`) or accessible form labels.
4. **Priority 4:** Resilient, semantic CSS selectors (`button[type="submit"]`).
5. **Strictly Forbidden:** Fragile raw XPath selectors, automatically generated dynamic CSS classes (`.css-1a2b3c`), and brittle deep DOM traversal chains (`div > div:nth-child(2) > span`).

---

## 3. Clean Page Object Model (POM) & App Actions
1. **Clean Script Separation:** Spec files (`cypress/e2e/**/*.cy.{ts,js}`) must contain ONLY business workflow method calls on Page Classes or App Action functions, followed by assertions.
2. **Encapsulation:** All DOM selectors (`cy.get()`, `cy.find()`) and user interactions belong exclusively inside Page Classes extending `BasePage` (or modular App Action helpers).
3. **Flat Inheritance:** Keep Page Object inheritance shallow (maximum 1 level of inheritance from `BasePage`).
4. **Custom Commands (`Cypress.Commands.add`):** Reserve custom commands strictly for cross-cutting workflows (e.g., authentication, session state initialization, API seeding). Never wrap simple single-element getters in custom commands.

---

## 4. Idempotent Test Data & Truth Anchor
1. **Dynamic Entity Prefixes:** Always randomize test entity codes with dynamic timestamps: `BasePage.uniqueCode("AUTO_CY_")` or `AUTO_CY_${Date.now()}`.
2. **Automated Teardown:** Every entity creation must be paired with automated cleanup (`afterEach()` hook or API cleanup) to prevent database key collisions.
3. **Zero Fake Passes (Truth Anchor):** Never suppress AUT application crashes or unhandled promise rejections using blanket `Cypress.on('uncaught:exception', () => false)`. Any exception suppression must be narrowly scoped to documented, benign third-party analytics scripts with exact error message matching.
4. **Explicit Assertions:** Every test must validate real application state using native Cypress assertions (`should('be.visible')`, `should('have.text', ...)`). Tests with zero assertions are strictly rejected by Gate 7.
