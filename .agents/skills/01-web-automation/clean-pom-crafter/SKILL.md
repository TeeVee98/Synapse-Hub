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
  - Page Classes in `pages/*.ts`, `pages/*.py`, or `Keywords/<namespace>/pages/*.groovy`.
  - Elimination of raw XPaths and CSS selectors from test scripts (`tests/`, `Scripts/`).
  - BasePage inheritance and smart wait encapsulation.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
  - Do NOT place raw XPaths, CSS selectors, or `findTestObject` calls inside test scripts.
  - Do NOT create deep Page Object inheritance hierarchies; keep inheritance flat (maximum 1 level from `BasePage`).
  - Do NOT use absolute positional XPaths (`//tbody/tr[1]/td[6]/button[2]`) or dynamic hash classes (`.p-element-1n2xyz`).
  - Do NOT read monolithic Page Class files (> 100KB) into LLM context; use line-range targeted reads or `tools/lookup_xpath.py`.
- **Sibling Skill Boundaries:**
  - `clean-pom-crafter` (this skill): Focuses on the **Page Class Layer** — designing `BasePage` subclasses, enforcing locator hierarchy, and encapsulating UI selectors.
  - `lam-script-generator`: Focuses on the **Test Script Workflow Layer** — transforming User Stories into business workflow test scripts (`TC-xxx`) calling Page Classes.
  - `playwright-live-interaction`: Probes live DOM/AOM to discover verified selector contracts.

---

## 3. Ordered Execution Workflow

### Phase 1: Core Architectural Principles

1. **Flat Architecture:**
   - All test cases and scripts reside directly in their parent directory (no nested module subfolders).
   - Naming convention: `TC-<Number>_<FeatureName>` (e.g. `TC-101_CreateUserAccount.groovy` or `tc-101-create-user.spec.ts`).
2. **Unified Inheritance from `BasePage`:**
   - All Page Classes inherit from `BasePage`.
3. **Zero Raw Locators in Scripts (ISO/IEC/IEEE 29119-5 Keyword-Driven Separation):**
   - Scripts only orchestrate business workflows. All locators and UI interactions are encapsulated in Page Classes, strictly adhering to ISO/IEC/IEEE 29119-5 Keyword-Driven separation of business logic from technical implementation.
4. **Clean POM Flat vs Screenplay Pattern Rationale:**
   - Enforce Clean POM Flat Architecture (max 1-level shallow inheritance from `BasePage`).
   - Screenplay Pattern (Actor/Task/Interaction/Ability micro-class fragmentation) is intentionally prohibited to prevent LLM Context Blowout and token waste.
5. **Mandatory 100% UTF-8 No BOM:**
   - Zero BOM bytes (`0xEF, 0xBB, 0xBF`) across all test files.

### Phase 2: Master Locator Priority Map (6 Tiers)

All Page Classes **MUST** follow this strict locator hierarchy:
1. **Tier 1 — Angular Semantic / ARIA:** `[formcontrolname="..."]`, `[aria-label="..."]`, `[role="..."]`.
2. **Tier 2 — Dedicated Test Attributes:** `[data-testid="..."]`, `[data-test="..."]`.
3. **Tier 3 — HTML Identifier:** `id`, `name`.
4. **Tier 4 — PrimeNG Business Attributes:** `p-dropdown[formcontrolname="..."]`, `button[icon*="pencil"]`.
5. **Tier 5 — Resilient CSS Selectors:** `.card.popup-data input.p-inputtext`.
6. **Tier 6 — Relative XPath (Last Resort):** `//div[contains(@class, 'card')]//button[contains(., 'Confirm')]`.

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
| **Katalon (`katalon`)** | `Keywords/<namespace>/pages/*.groovy` | `Scripts/**` | `JUnit_Report.xml`, `Screenshots/FAILED_*.png` |
| **Playwright TS (`playwright`)** | `src/pages/*.page.ts` or `pages/*.ts` | `tests/**/*.spec.ts` | `playwright-report/`, `test-results/` |
| **Cypress (`cypress`)** | `cypress/pages/*.page.ts` | `cypress/e2e/**/*.cy.(ts \| js)` | `cypress/reports/`, `cypress/screenshots/` |
| **Pytest (`pytest`)** | `pages/*_page.py` | `tests/**/test_*.py` | `reports/junit.xml`, `screenshots/` |
| **Appium Mobile (`mobile-appium`)** | `screens/*_screen.(ts \| py)` + `locators/(ios \| android)/` | `tests/**` | `reports/`, `screenshots/` |

### Phase 5: Implementation References

- [**Standard Clean POM Methods (`pom_patterns.groovy`)**](references/pom_patterns.groovy): Full implementation of `searchRecord`, `editRecord`, `deleteRecord`, `setCalendarDate`, `selectMultiOptions`.
- [**Standard Test Script Template (`standard_test_case.groovy`)**](examples/standard_test_case.groovy): 7-step complete script template from Login -> Create -> Search -> Edit -> Delete.
- **Zero-Token XPath Lookup (`tools/lookup_xpath.py`):** Targeted locator retrieval in under 200 tokens.
- **Browser Runtime Helper (`tools/browser_helpers.js`):** In-browser validation engine for form audits, safe clicks, and batch verification.

### Phase 6: Concurrency & Race Condition Automation Patterns

When `Concurrency Gate = ON`:

#### Pattern 1: Playwright Multi-Context Isolated Concurrency
<!-- classification: illustrative -->
```typescript
test('Verify stock contention: exactly 1 purchase succeeds and 1 receives 409 conflict', async ({ browser }) => {
  // Spawn 2 completely isolated browser contexts (different sessions & storage states)
  const contextA = await browser.newContext();
  const contextB = await browser.newContext();
  const pageA = await contextA.newPage();
  const pageB = await contextB.newPage();

  const checkoutA = new CheckoutPage(pageA);
  const checkoutB = new CheckoutPage(pageB);

  await Promise.all([
    checkoutA.navigateToItem('ITEM_LAST_STOCK_01'),
    checkoutB.navigateToItem('ITEM_LAST_STOCK_01')
  ]);

  // Execute simultaneous checkout click in parallel (< 50ms window)
  const [resA, resB] = await Promise.all([
    checkoutA.confirmOrder(),
    checkoutB.confirmOrder()
  ]);

  // Assert exactly 1 succeeds and 1 encounters conflict without negative stock
  const statuses = [resA.status, resB.status];
  expect(statuses).toContain(200);
  expect(statuses).toContain(409);

  await contextA.close();
  await contextB.close();
});
```

#### Pattern 2: Katalon Studio Parallel Suite / GPars Execution
<!-- classification: illustrative -->
```groovy
// In Custom Keyword: ConcurrencyKeyword.groovy
import groovyx.gpars.GParsPool
import com.kms.katalon.core.annotation.Keyword

public class ConcurrencyKeyword {
    @Keyword
    static def executeConcurrentRequests(List<Closure> actions) {
        def results = []
        GParsPool.withPool {
            results = actions.collectParallel { action ->
                action.call()
            }
        }
        return results
    }
}
```

### Phase 7: Anti-Junk Test Protocol & Authoring Gate

Before authoring or modifying any automated test script or Page Class, pass this **4-Question Authoring Gate**:
1. **Observable Contract:** Does this test protect an observable user/business behavior, invariant, or independent contract?
2. **Credible Regression:** Is there a credible, realistic regression scenario that causes this test to fail?
3. **Primary Boundary:** Why does existing proof miss it? Every contract belongs to one primary owner at the strongest boundary.
4. **Zero Test-Only Seams:** Does this test require synthetic flags, wrappers, or public methods in Page Classes that have no real production caller?

---

## 4. Verification Points & DoD

1. **Zero Raw Locators:** 0 occurrences of XPaths or CSS selectors inside test scripts (`tests/`, `Scripts/`).
2. **Inheritance Depth:** Page Classes extend `BasePage` directly with inheritance depth $\le 1$.
3. **Encoding:** 100% UTF-8 No BOM across all generated Page Classes and scripts.
4. **Smart Waits:** 0 static sleeps (`Thread.sleep`, `time.sleep`).

---

## 5. Handoff Protocol

- **Deliverables:** Clean POM Page Classes extending `BasePage` with encapsulated locators and business methods.
- **Next Subagent:** Pass to `lam-script-generator` for test script authoring or `test-runner` for execution.
- **Output Format:** Clean Page Class source file (`.ts`, `.groovy`, `.py`) with complete method docstrings.
