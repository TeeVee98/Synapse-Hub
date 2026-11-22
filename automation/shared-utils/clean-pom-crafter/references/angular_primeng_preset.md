# Angular & PrimeNG Component Preset Guide

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Angular Reactive Forms & Change Detection

In enterprise web applications built with Angular (v12+), form inputs typically rely on reactive form controls rather than plain HTML inputs. Standard synthetic events like `.value = ...` will not trigger Angular Change Detection unless explicit dispatching occurs.

### Key Locator Strategies for Angular Forms

| Target Element | Recommended Locator | Fallback / Attribute |
| :--- | :--- | :--- |
| **Reactive Form Input** | `input[formcontrolname="userName"]` | `[formcontrolname="userName"]` |
| **Form Group Container** | `form[formgroupname="billing"]` | `[formgroupname="billing"]` |
| **Validation Error State** | `input.ng-invalid.ng-touched` | `input[formcontrolname="..."][aria-invalid="true"]` |
| **Valid / Pristine State** | `input.ng-valid.ng-dirty` | `.ng-valid:not(.ng-pristine)` |

### Safe Angular Input Dispatch Pattern
When automation drivers interact with custom Angular inputs, ensure `input`, `change`, and `blur` events are dispatched:

```javascript
// Browser JavaScript evaluation:
function setAngularInputValue(element, value) {
  element.value = value;
  element.dispatchEvent(new Event('input', { bubbles: true }));
  element.dispatchEvent(new Event('change', { bubbles: true }));
  element.dispatchEvent(new Event('blur', { bubbles: true }));
}
```

### 1.1 Modern Angular Testing Paradigm (angular/angular Standard)
In modern Angular (v17+ zoneless and standalone architecture):
- **Zoneless & Async-First Pattern:** Always adhere to `Act -> await fixture.whenStable() -> Assert`. Manual spamming of `fixture.detectChanges()` is prohibited as it masks asynchronous state settle errors.
- **Mock Clock Acceleration:** In component tests with timers or debounce observables, use `useAutoTick()` or fakeAsync micro-advancements instead of real-time sleeps.
- **Standalone Components:** Strictly forbid generating or requiring legacy `NgModule` wrappers; use standalone component imports directly.

---

## 2. PrimeNG Component Preset Catalog

PrimeNG components generate structured markup often detached from raw HTML `<select>` or `<dialog>` elements. Below are the standard, battle-tested selector patterns for PrimeNG widgets.

### 2.1 `p-dropdown` (Single Selection)
PrimeNG renders dropdown triggers inline and renders the option list panel at `body` level when `appendTo="body"` is configured.

- **Trigger Container:** `p-dropdown[formcontrolname="category"]` or `p-dropdown[data-testid="category-select"]`
- **Clickable Chevron:** `p-dropdown[formcontrolname="category"] .p-dropdown-trigger`
- **Selected Value Label:** `p-dropdown[formcontrolname="category"] .p-dropdown-label`
- **Dropdown Overlay Panel:** `div.p-dropdown-panel:not(.p-hidden)`
- **Item Option Selector:** `li.p-dropdown-item:has-text("Option Name")` or `//li[contains(@class, 'p-dropdown-item') and contains(., 'Option Name')]`

```typescript
// Playwright Example:
async function selectPrimeDropdown(page: Page, formControl: string, optionText: string) {
  const trigger = page.locator(`p-dropdown[formcontrolname="${formControl}"] .p-dropdown-trigger`);
  await trigger.click();
  const panel = page.locator('.p-dropdown-panel:visible');
  await panel.locator(`.p-dropdown-item:has-text("${optionText}")`).click();
}
```

---

### 2.2 `p-table` (Enterprise Data Tables)
PrimeNG tables feature server-side sorting, pagination, multi-select checkboxes, and action toolbars.

- **Table Container:** `p-table[data-testid="user-table"] table` or `p-table`
- **Data Rows:** `p-table table tbody tr:not(.p-datatable-emptymessage)`
- **First Data Row:** `p-table table tbody tr:first-child`
- **Cell by Column Index:** `p-table table tbody tr:first-child td:nth-child(2)`
- **Row by Unique Code:** `p-table table tbody tr:has-text("AUTO_12345")`
- **Row Action Buttons:**
  - Edit: `tr:has-text("AUTO_12345") button[icon*="pencil"], tr button[icon*="edit"]`
  - Delete: `tr:has-text("AUTO_12345") button.p-button-danger, tr button[icon*="trash"]`
- **Paginator Controls:**
  - Next Page: `.p-paginator-next:not(.p-disabled)`
  - Page Number: `.p-paginator-page:has-text("2")`

---

### 2.3 `p-dialog` & `p-confirmdialog` (Modals & Overlays)
Modals render in an overlay layer with backdrop masking (`.p-component-overlay`).

- **Dialog Container:** `div.p-dialog:visible`
- **Dialog Header:** `div.p-dialog-header .p-dialog-title`
- **Dialog Content:** `div.p-dialog-content`
- **Confirm Dialog Accept Button:** `button.p-confirm-dialog-accept, div.p-dialog-footer button:has-text("Confirm"), div.p-dialog-footer button:has-text("Xác nhận")`
- **Confirm Dialog Reject Button:** `button.p-confirm-dialog-reject, div.p-dialog-footer button:has-text("Cancel"), div.p-dialog-footer button:has-text("Hủy")`
- **Close Icon:** `button.p-dialog-header-close`

---

### 2.4 `p-calendar` (Date & Time Picker)
- **Input Field:** `p-calendar[formcontrolname="birthDate"] input.p-inputtext`
- **Datepicker Panel:** `div.p-datepicker:visible`
- **Selected Date Cell:** `td:not(.p-datepicker-other-month) > span:has-text("15")`
- **Today Button:** `button.p-datepicker-today`
- **Clear Button:** `button.p-datepicker-clear`

*Best Practice:* For reliable CI automation, inject the date string via Page Class helper dispatching `input` and `change` events rather than clicking through multi-year date picker grids.

---

### 2.5 `p-multiselect` (Multi-Option Select)
- **MultiSelect Trigger:** `p-multiselect[formcontrolname="roleIds"]`
- **Panel Container:** `div.p-multiselect-panel:visible`
- **Select-All Checkbox:** `div.p-multiselect-header .p-checkbox`
- **Option Checkbox:** `li.p-multiselect-item:has-text("Administrator") .p-checkbox`
- **Close Button:** `button.p-multiselect-close`

---

### 2.6 `p-toast` & `p-messages` (Feedback & Notifications)
- **Toast Container:** `div.p-toast`
- **Success Toast:** `div.p-toast-message-success`
- **Error Toast:** `div.p-toast-message-error`
- **Toast Summary / Detail:** `div.p-toast-detail, div.p-toast-summary`

---

## 3. Clean POM Encapsulation Discipline

1. **Zero PrimeNG Selectors in Test Scripts:**
   - Test scripts MUST only call business methods (e.g., `userPage.selectRole("Admin")`, `orderPage.deleteRecord("ORD_001")`).
   - PrimeNG widget classes (`.p-dropdown-panel`, `.p-confirmdialog`) remain completely encapsulated within Page Classes.
2. **Handle Detached Overlays Gracefully:**
   - Because panels render at the `body` level with `appendTo="body"`, scope overlay lookups to `:visible` panels (e.g., `.p-dropdown-panel:visible`) to avoid matching hidden or stale DOM nodes from previously closed dialogs.
3. **Cross-Reference:**
   - See [**pom_patterns.groovy**](pom_patterns.groovy) for Groovy/Selenium implementation of PrimeNG table, calendar, and modal helpers.
   - See **SKILL.md** for the universal 6-tier locator hierarchy.
