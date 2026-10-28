---
name: clean-pom-crafter
description: >-
  Standardized Clean Page Object Model (POM) development and Flat Architecture enforcement across enterprise automation test suites.
  Ensures 100% UTF-8 No BOM, zero hardcoded XPaths in scripts, dynamic test data generation via uniqueCode,
  and standardized two-phase search, edit, calendar, multiselect, and deletion behaviors.
---

# Clean POM Crafter â€” Enterprise Clean POM Architecture Standards

Specialized skill for creating, refactoring, and standardizing test automation scripts using **Clean Page Object Model (POM)** and **Flat Architecture** across enterprise test suites.

---

## 1. Core Architectural Principles

1. **Flat Architecture:**
   - All `Test Cases/`, `Scripts/`, and `Test Suites/` reside directly in their parent directory (no module subfolders).
   - Naming convention: `TC-<Number>_<FeatureName>`, e.g. `TC-123_TimKiemCumCongNghiep.groovy`.
2. **Unified Inheritance from `BasePage`:**
   - All 10 Page Classes in `Keywords/dmit/pages/` inherit from `BasePage`.
3. **Zero Raw XPaths in Test Scripts:**
   - Scripts (`Scripts/TC-xxx_*.groovy`) only orchestrate business workflows. All locators and UI interactions are encapsulated in Page Classes.
4. **Mandatory 100% UTF-8 No BOM:**
   - All `.groovy`, `.tc`, `.ts` files must NEVER contain UTF-8 BOM bytes (`0xEF, 0xBB, 0xBF`).
5. **Context Window Protection (Zero-Token Economy):**
   - ðŸš« **NEVER read the entire `DataMiningPage.groovy` (230KB) into LLM context.**
   - Always use `python3 tools/lookup_xpath.py <keyword>` or line-range targeted reads (`read_file` with `StartLine`/`EndLine`) to find selectors and methods. Reading this entire file will consume context and degrade AI reasoning.

---

## 2. Master Locator Priority Map (6 Tiers)

All Page Classes **MUST** follow this strict locator hierarchy:
1. **Tier 1 â€” Angular Semantic / ARIA:** `[formcontrolname="..."]`, `[aria-label="..."]`, `[role="..."]`.
2. **Tier 2 â€” Dedicated Test Attributes:** `[data-testid="..."]`, `[data-test="..."]`.
3. **Tier 3 â€” HTML Identifier:** `id`, `name`.
4. **Tier 4 â€” PrimeNG Business Attributes:** `p-dropdown[formcontrolname="..."]`, `button[icon*="pencil"]`.
5. **Tier 5 â€” Resilient CSS Selectors:** `.card.popup-data input.p-inputtext`.
6. **Tier 6 â€” Relative XPath (Last Resort):** `//div[contains(@class, 'card')]//button[contains(., 'XÃ¡c nháº­n')]`.

> ðŸš« **FORBIDDEN:** Absolute positional XPaths (`//tbody/tr[1]/td[6]/button[2]`) and dynamic hash classes (`.p-element-1n2xyz`).

---

## 3. Test Data Management & Cross-Module Data Chain

- **Supporting Field:** Generate dynamically using `BasePage.uniqueCode(prefix)` (e.g. `BasePage.uniqueCode("CCN_")`).
- **Dimension Field:** Fixed category values selected from dropdowns (`"Äang hoáº¡t Ä‘á»™ng"`, `"HÃ  Ná»™i"`).
- **Reference Field:** Pass output records from prior TCs into subsequent TCs (Create -> Edit -> Delete).
- **Computed Field:** Auto-calculated system metrics; assert 100% exact match.

---

## 4. Registry of 10 Page Classes Inheriting `BasePage`

| No. | Page Class | Functional Module | Test Case Range | Source File |
|:---:|---|---|:---:|---|
| 1 | `BasePage` | Core Engine, Driver, JS Helpers, Smart Wait | Global | `Keywords/dmit/pages/BasePage.groovy` |
| 2 | `TargetPlanPage` | Target Planning | `TC-1` to `TC-7` | `Keywords/dmit/pages/TargetPlanPage.groovy` |
| 3 | `LoginPage` | Authentication & User Profile | `TC-8` to `TC-12` | `Keywords/dmit/pages/LoginPage.groovy` |
| 4 | `UserAdminPage` | System Administration & Users | `TC-13` to `TC-16` | `Keywords/dmit/pages/UserAdminPage.groovy` |
| 5 | `CommonCategoryPage` | Common Categories | `TC-17` to `TC-28` | `Keywords/dmit/pages/CommonCategoryPage.groovy` |
| 6 | `IndustryCategoryPage` | 16 Industry Categories | `TC-29` to `TC-92` | `Keywords/dmit/pages/IndustryCategoryPage.groovy` |
| 7 | `PlanningPage` | Sector Planning & Approvals | `TC-93` to `TC-122` | `Keywords/dmit/pages/PlanningPage.groovy` |
| 8 | `DataMiningPage` | Data Mining & GIS Maps | `TC-123` to `TC-247` | `Keywords/dmit/pages/DataMiningPage.groovy` |
| 9 | `ReportPage` | Statistical Reporting | `TC-248` to `TC-249` | `Keywords/dmit/pages/ReportPage.groovy` |
| 10 | `TokenMgmtPage` | Data Sharing & API Tokens | `TC-250` to `TC-259` | `Keywords/dmit/pages/TokenMgmtPage.groovy` |

---

## 5. Implementation References & Examples

- [**Standard Clean POM Methods (`pom_patterns.groovy`)**](references/pom_patterns.groovy): Full implementation of `searchRecord`, `editRecord`, `deleteRecord`, `setCalendarDate`, `selectMultiOptions`, `verifyRecordExists`, `verifyRecordNotExists`, `jsSetInput`.
- [**Standard Test Script Template (`standard_test_case.groovy`)**](examples/standard_test_case.groovy): 7-step complete script template from Login -> Create -> Search -> Edit -> Delete.
- [**Zero-Token XPath Lookup (`tools/lookup_xpath.py`)**](tools/lookup_xpath.py): Command `python3 tools/lookup_xpath.py <PageClass>` returns exact locators in <200 tokens without parsing 169KB JSON.
- [**Browser Runtime Helper (`tools/dmit_browser_helpers.js`)**](tools/dmit_browser_helpers.js): In-browser validation engine for form audits, safe clicks, and batch verification.
