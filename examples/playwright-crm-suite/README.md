# 🎭 Playwright TypeScript Reference Suite (Clean POM & Synapse Guardrails)

This directory provides a production-grade **Playwright Test (TypeScript)** reference suite demonstrating the Clean Page Object Model (POM) and Flat Architecture standards enforced by **Synapse Hub**.

---

## 🌟 Key Architectural Patterns Demonstrated

1. **Clean POM & Flat Architecture:**
   - Test scripts (`tests/auth.spec.ts`, `tests/customers.spec.ts`) contain **zero raw XPaths or CSS selectors**.
   - All locator strategies and interaction logic are cleanly encapsulated within Page Classes (`pages/LoginPage.ts`, `pages/CustomerPage.ts`).
2. **Tier 1 ARIA Semantic Locators:**
   - Elements are targeted using resilient accessible roles (`page.getByRole('button', { name: 'Đăng nhập' })`) and labels (`page.getByLabel('Mật khẩu')`).
3. **Idempotent Test Data & Teardown Cleanup:**
   - Uses `BasePage.uniqueCode('CUST_')` with timestamps to prevent database primary key collisions during parallel execution.
   - `test.afterEach` guarantees that created test entities are safely deleted.
4. **Smart Waits & Zero Static Sleeps:**
   - Employs dynamic wait conditions (`waitForSpinnerToDisappear`, `waitForLoadState('networkidle')`) instead of flaky `Thread.sleep` or `waitForTimeout`.

---

## 🚀 How to Run & Verify

### 1. Run the Synapse Quality Linter (0-Token AST Check)
Verify that test scripts are free from fake passes, unawaited assertions, and swallowed exceptions:
```bash
npx synapse-hub lint ./tests
```
*(Expected output: `100% CLEAN — Zero defects detected`)*.

### 2. Verify 9 Quality Gates DoD
```bash
npx synapse-hub verify
```

### 3. Run Headless Playwright Tests
```bash
npm install
npx playwright test
```
