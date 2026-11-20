---
name: clean-pom-crafter
description: "Build and refactor Clean POM Page Classes adhering to Flat Architecture standards. Use when designing Clean POM page classes or enforcing zero-locator discipline in scripts."
category: test_automation_and_execution
version: "2.0.0"
policies:
  network: none
  shell: workspace-sandbox
  filesystem: workspace-sandbox
---
# Clean POM Crafter — Enterprise Clean POM Architecture Standards

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Use when creating, refactoring, or standardizing test automation Page Classes, enforcing Clean Page Object Model (POM) separation, or applying the 6-tier locator hierarchy.
- **Activation Scope:**
  - Page Classes across supported stacks: Playwright (`pages/**/*.ts`), Cypress (`cypress/pages/**/*.ts`), Pytest (`pages/**/test_*_page.py`), and Katalon (`Keywords/<namespace>/pages/*.groovy`).
  - Elimination of raw XPaths, CSS selectors, and inline element lookups from test scripts (`tests/`, `cypress/e2e/`, `Scripts/`).
  - BasePage inheritance and dynamic smart wait encapsulation.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
  - Do NOT place raw XPaths, CSS selectors, or framework-specific lookup calls (`findTestObject`, `page.locator()`, `cy.get()`) inside test scripts.
  - Do NOT create deep Page Object inheritance hierarchies; keep inheritance flat (max 1 level from `BasePage`).
  - Do NOT use absolute positional XPaths (`//tbody/tr[1]/td[6]/button[2]`) or dynamic hash classes (`.p-element-1n2xyz`).
  - Do NOT read monolithic Page Class files (> 100KB) into LLM context; use line-range reads or `tools/heal/lookup_xpath.py`.
- **Sibling Skill Boundaries:**
  - `clean-pom-crafter` (this skill): Focuses on the **Page Class Layer** — designing `BasePage` subclasses, enforcing locator hierarchy, and encapsulating UI selectors.
  - `lam-script-generator`: Focuses on the **Test Script Workflow Layer** — transforming User Stories into business workflow test scripts (`TC-xxx`) calling Page Classes.
  - `playwright-live-interaction`: Probes live DOM/AOM to discover verified selector contracts.

---

## 3. Ordered Execution Workflow

### Phase 1: Core Architectural Principles

1. **Stack-Differentiated Architecture:**
   - **Katalon:** Flat structure in `Keywords/<namespace>/pages/*.groovy` and `Scripts/**` required by Katalon engine.
   - **Playwright / Cypress / Pytest:** Support domain/feature subdirectories (`pages/auth/*.page.ts`, `tests/auth/*.spec.ts`).
   - **Naming:** `TC-<Number>_<FeatureName>` (e.g. `TC-101_CreateUser.groovy`, `tc-101-create-user.spec.ts`).
2. **Unified Inheritance:** All Page Classes inherit directly from `BasePage` (max 1 level inheritance).
3. **Zero Raw Locators in Scripts (ISO/IEC/IEEE 29119-5):** Scripts only orchestrate business workflows; all locators are encapsulated in Page Classes.
4. **Clean POM vs Screenplay:** Clean POM is the default standard for LLM token economy; Screenplay is supported as an opt-in pattern when required by project design. For Clean POM, enforce shallow 1-level inheritance from `BasePage`.
5. **Mandatory 100% UTF-8 No BOM:** Zero BOM bytes (`0xEF, 0xBB, 0xBF`) across all test files.

### Phase 2: Master Locator Priority Map (6 Tiers)

All Page Classes across frameworks **MUST** follow this standardized 6-tier locator hierarchy:
1. **Tier 1 — User-Facing Accessible Semantics & ARIA:** `getByRole('button', { name: 'Submit' })`, `getByLabel('Username')`, `[role][aria-label]`.
2. **Tier 2 — Dedicated Test Attributes:** `[data-testid]`, `[data-test]`, `[data-cy]`, `getByTestId('btn-submit')`.
3. **Tier 3 — Form Semantics & Field Controls:** `input[name]`, `[formcontrolname]`, `getByPlaceholder('Search')`.
4. **Tier 4 — Stable Visual Text & Anchors:** `getByText('Confirm')`, `button:has-text("Xác nhận")`.
5. **Tier 5 — Scoped Resilient Structural CSS:** `.modal-card input.search`, `.form-group .item-input`.
6. **Tier 6 — Scoped Relative XPath (Last Resort):** `//div[contains(@class, 'card')]//button[contains(., 'Confirm')]` (absolute positional XPaths strictly forbidden).

### Phase 3: Universal Page Object Model Reference

| No. | Page Class Role | Functional Module | Typical Test Scope | Core Methods & Responsibilities |
|:---:|---|---|:---:|---|
| 1 | `BasePage` | Core Engine, Driver, JS Helpers, Smart Wait | Global | `openUrl()`, `smartWait()`, `clickSafe()`, `uniqueCode()` |
| 2 | `LoginPage` | Authentication & User Profile | Auth & Session | `login()`, `logout()`, `verifyUserProfile()` |
| 3 | `UserAdminPage` | System Administration & Users | Admin / RBAC | `createUser()`, `assignRole()`, `filterUsers()` |
| 4 | `CommonCategoryPage` | Common Categories & System Catalogs | Catalogs & Lookups | `addCategory()`, `editCategory()`, `verifyCatalog()` |
| 5 | `DataManagementPage` | Enterprise CRUD & Search Tables | Master Data | `searchRecord()`, `editRecord()`, `deleteRecord()` |

### Phase 4: Multi-Stack Architecture & Directory Mapping

| Stack / Profile | Page / Screen Directory | Test Script Directory | Default Reports & Artifacts |
| :--- | :--- | :--- | :--- |
| **Katalon (`katalon`)** | `Keywords/<namespace>/pages/*.groovy` (flat) | `Scripts/**` (flat) | `JUnit_Report.xml`, `Screenshots/FAILED_*.png` |
| **Playwright TS (`playwright`)** | `src/pages/**/*.page.ts` or `pages/**/*.ts` | `tests/**/*.spec.ts` | `playwright-report/`, `test-results/` |
| **Cypress (`cypress`)** | `cypress/pages/**/*.page.ts` | `cypress/e2e/**/*.cy.(ts \| js)` | `cypress/reports/`, `cypress/screenshots/` |
| **Pytest (`pytest`)** | `pages/**/test_*_page.py` or `pages/*_page.py` | `tests/**/test_*.py` | `reports/junit.xml`, `screenshots/` |
| **Appium Mobile (`mobile-appium`)** | `screens/*_screen.(ts \| py)` + `locators/(ios \| android)/` | `tests/**` | `reports/`, `screenshots/` |

### Phase 5: Implementation References

- [**Katalon POM Reference Guide (`references/katalon_pom.md`)**](references/katalon_pom.md): Groovy Page Classes, `BasePage` extension, `uniqueCode`, and GPars concurrency.
- [**Angular & PrimeNG Preset Guide (`references/angular_primeng_preset.md`)**](references/angular_primeng_preset.md): Angular reactive forms and PrimeNG widget locators (`p-dropdown`, `p-table`, `p-dialog`, `p-calendar`, `p-multiselect`).
- [**Standard Clean POM Groovy Methods (`references/pom_patterns.groovy`)**](references/pom_patterns.groovy): Reusable implementations of search, edit, delete, calendar, and multiselect.
- [**Standard Test Script Template (`examples/standard_test_case.groovy`)**](examples/standard_test_case.groovy): 7-step complete script template from Login -> Create -> Search -> Edit -> Delete.
- **Zero-Token XPath Lookup (`tools/heal/lookup_xpath.py`):** Targeted locator retrieval in under 200 tokens.
- **Browser Runtime Helper (`tools/browser_helpers.js`):** In-browser validation engine for form audits, safe clicks, and batch verification.

### Phase 6: Concurrency & Race Condition Automation Patterns

When `Concurrency Gate = ON`:

#### Pattern 1: Playwright Multi-Context Isolated Concurrency
<!-- classification: illustrative -->
```typescript
test('Verify stock contention: exactly 1 purchase succeeds and 1 receives 409', async ({ browser }) => {
  const [ctxA, ctxB] = await Promise.all([browser.newContext(), browser.newContext()]);
  const [pageA, pageB] = await Promise.all([ctxA.newPage(), ctxB.newPage()]);
  const [resA, resB] = await Promise.all([new CheckoutPage(pageA).order(), new CheckoutPage(pageB).order()]);
  expect([resA.status, resB.status]).toContain(200);
  expect([resA.status, resB.status]).toContain(409);
  await Promise.all([ctxA.close(), ctxB.close()]);
});
```

#### Pattern 2: Multi-Context / Multi-Tab Concurrency Pattern
<!-- classification: illustrative -->
```typescript
const [ctxA, ctxB] = await Promise.all([browser.newContext(), browser.newContext()]);
const [resA, resB] = await Promise.all([task(ctxA), task(ctxB)]);
await Promise.all([ctxA.close(), ctxB.close()]);
```
*(For Katalon Studio Groovy GPars parallel execution, refer to [**Katalon POM Reference Guide**](references/katalon_pom.md).)*

### Phase 7: Anti-Junk Test Protocol & Authoring Gate

Before authoring tests or Page Classes, verify the **4-Question Gate**:
1. **Observable Contract:** Protects an observable business behavior or invariant?
2. **Credible Regression:** Has a realistic regression failure scenario?
3. **Primary Boundary:** Owned by primary contract boundary without duplicate tests?
4. **Zero Test-Only Seams:** No synthetic flags or test-only wrappers in Page Classes?

### Phase 8: Story-to-Script LAM Generation (Integrated from lam-script-generator)

When transforming user stories into runnable tests:
1. **World Model Decomposition:** Parse requirements into atomic user action sequences.
2. **Action Engine Mapping:** Map actions to methods in existing Clean POM Page Classes (`LoginPage`).
3. **Dynamic Idempotency:** Inject dynamic timestamps/unique codes (`BasePage.uniqueCode("AUTO_")` or `AUTO_${Date.now()}`) with mandatory teardown.
4. **Pure Script Synthesis:** Synthesize test scripts calling Page Class methods exclusively (0 raw selectors).

---

## 4. Verification Points & DoD

1. **Zero Raw Locators:** 0 occurrences of XPaths, CSS selectors, or inline element lookups inside test scripts (`tests/`, `cypress/`, `Scripts/`).
2. **Inheritance Depth:** Page Classes extend `BasePage` directly with inheritance depth $\le 1$.
3. **Encoding:** 100% UTF-8 No BOM across all generated Page Classes and scripts.
4. **Smart Waits:** 0 static sleeps (`Thread.sleep`, `time.sleep`, `waitForTimeout`).

---

## 5. Handoff Protocol

- **Deliverables:** Clean POM Page Classes extending `BasePage` with encapsulated locators and business methods.
- **Next Subagent:** Pass to `lam-script-generator` for test script authoring or `test-runner` for execution.
- **Output Format:** Clean Page Class source file (`.ts`, `.groovy`, `.py`) with complete method docstrings.
