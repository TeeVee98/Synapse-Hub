---
name: wcag-audit-patterns
description: "Audit WCAG 2.2 accessibility (A/AA), keyboard navigation, and ARIA roles. Use when auditing accessibility against WCAG 2.2 A/AA criteria."
category: architecture_and_analysis
version: "2.0.0"
policies:
  network: localhost-only
  shell: read-only
  filesystem: workspace-sandbox
---
# WCAG 2.2 Accessibility Audit Patterns

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Audit WCAG 2.2 accessibility (A/AA), keyboard navigation, and ARIA roles. Use when auditing accessibility against WCAG 2.2 A/AA criteria.
- **Activation Scope:** Domain workflows for `05-security-and-compliance` involving `wcag-audit-patterns`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT rely exclusively on automated axe-core scans (automated tools catch only ~30-40% of WCAG criteria).
- Do NOT ignore keyboard navigation, screen reader flow, or focus management.
- Do NOT bypass color contrast checks across dark and light UI themes.
- **Sibling Skill Boundaries:**
  - playwright-live-interaction probes DOM selectors; wcag-audit-patterns evaluates accessibility compliance against WCAG 2.2 A/AA criteria.

---

## 3. Ordered Execution Workflow

Engineering standards for automated, continuous Web Content Accessibility Guidelines (WCAG 2.2 Level A and AA) auditing across enterprise web applications.

---

### Core WCAG 2.2 Success Criteria Matrix

| Criterion | Rule Code | Level | Requirement & Automated Assertion |
| :--- | :--- | :--- | :--- |
| **Non-text Content** | WCAG 1.1.1 | Level A | Informative `<img>` tags must possess descriptive `alt` text; decorative images must use null/empty `alt=""` (W3C Technique H67), `role="presentation"`, or `aria-hidden="true"`. |
| **Info and Relationships**| WCAG 1.3.1 | Level A | Form controls `<input>`, `<select>` must link to `<label>` via `id/for` or `aria-label`. |
| **Heading Structure** | WCAG 1.3.1 | Level A | Headings should follow logical hierarchy without skipping levels (advisory best practice per W3C Technique G141). |
| **Contrast (Minimum)** | WCAG 1.4.3 | Level AA | Normal text contrast ratio $\ge 4.5:1$; Large text ($\ge 18\text{pt}$ or bold $14\text{pt}$) $\ge 3:1$. |
| **Keyboard Navigable** | WCAG 2.1.1 | Level A | All interactive elements must be focusable via `Tab` with visible focus indicators. |
| **No Keyboard Trap** | WCAG 2.1.2 | Level A | Focus must not become trapped; modal dialogs must provide a standard keyboard exit (e.g. `Esc` key, reachable close button). |
| **Focus Not Obscured** | WCAG 2.4.11 | Level AA | Focused element must not be completely hidden by sticky banners, footers, or overlays (WCAG 2.2). |
| **Target Size (Minimum)**| WCAG 2.5.8 | Level AA | Interactive targets must meet $24 \times 24\text{px}$ or sufficient spacing/offset (WCAG 2.2; exceptions: inline text links, essential UI). |
| **Consistent Help** | WCAG 3.2.6 | Level A | Help options (chat, FAQ, phone) must reside in identical relative layout order across pages (WCAG 2.2). |
| **Redundant Entry** | WCAG 3.3.7 | Level A | Multi-step workflows must auto-populate or allow selection of previously entered data (WCAG 2.2). |
| **Accessible Auth** | WCAG 3.3.8 | Level AA | Login must support password managers / paste / passkeys without cognitive puzzles (WCAG 2.2). |

---

### Playwright Automated Accessibility Testing Patterns

### Pattern A: Integrating `@axe-core/playwright` for Comprehensive Audits
<!-- classification: illustrative -->
```typescript
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('verify WCAG 2.2 Level AA compliance on dashboard', async ({ page }) => {
  await page.goto('/dashboard');
  await page.waitForLoadState('networkidle');

  const accessibilityScanResults = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .exclude('.legacy-third-party-widget') // Explicitly scoped exclusion
    .analyze();

  expect(accessibilityScanResults.violations).toEqual([]);
});
```

### Pattern B: Modal Keyboard Focus Trap and Escape Verification
<!-- classification: illustrative -->
```typescript
test('modal dialog traps keyboard focus and closes on Escape', async ({ page }) => {
  await page.goto('/settings');
  await page.getByRole('button', { name: 'Edit Profile' }).click();

  const modal = page.getByRole('dialog', { name: 'Edit Profile' });
  await expect(modal).toBeVisible();

  // Verify focus shifts into modal
  await expect(modal.getByRole('textbox', { name: 'Username' })).toBeFocused();

  // Press Escape and verify focus returns to trigger
  await page.keyboard.press('Escape');
  await expect(modal).toBeHidden();
  await expect(page.getByRole('button', { name: 'Edit Profile' })).toBeFocused();
});
```

### Pattern C: WCAG 2.5.8 Target Size ($24 \times 24\text{px}$) Assertion
> **WCAG 2.5.8 Exceptions:** Targets under $24 \times 24\text{px}$ pass if sufficient spacing (offset) ensures a 24px diameter circle centered on the target does not intersect another target/circle, or if the target is inline within a block of text, user-agent controlled, or essential.
<!-- classification: illustrative -->
```typescript
test('all interactive buttons satisfy WCAG 2.5.8 24x24px target size', async ({ page }) => {
  await page.goto('/checkout');
  const buttons = page.locator('button, a.btn, input[type="submit"]');
  const count = await buttons.count();

  for (let i = 0; i < count; i++) {
    const btn = buttons.nth(i);
    if (await btn.isVisible()) {
      const box = await btn.boundingBox();
      expect(box, `Button #${i} must have layout box`).not.toBeNull();
      if (box) {
        expect(box.width, `Button #${i} width ${box.width}px < 24px`).toBeGreaterThanOrEqual(24);
        expect(box.height, `Button #${i} height ${box.height}px < 24px`).toBeGreaterThanOrEqual(24);
      }
    }
  }
});
```

### Pattern D: Playwright Native Accessibility Object Model (AOM) Snapshot
<!-- classification: illustrative -->
```python
# Python Playwright AOM Snapshot Assertion
def test_accessible_tree_structure(page):
    page.goto("/login")
    snapshot = page.accessibility.snapshot()
    assert snapshot is not None
    # Ensure form role with named fields exists
    assert any(node.get("role") == "button" and "Sign In" in node.get("name", "") for node in snapshot.get("children", []))
```

---

### Automated CLI Auditing via Tooling

Synapse Hub provides automated accessibility auditing via `tools/wcag_audit.py`:

<!-- classification: illustrative -->
```bash
# Audit a local HTML snapshot or directory
python tools/wcag_audit.py path/to/page.html -o docs/wcag_audit_report.md

# Audit a live application URL directly via CDP/Playwright
python tools/wcag_audit.py https://staging.example.com --url -o docs/wcag_audit_report.md

# CLI integration via agent-qa
agent-qa wcag-audit path/to/page.html

# Export standardized Section 508 & EN 301 549 VPAT 2.5 Report
agent-qa vpat --url https://staging.example.com --out-md docs/VPAT_REPORT.md
```

---

## 4. Verification Points & DoD

1. Automated accessibility scans run via axe-core / Playwright with 0 Level A/AA violations.
2. Manual check protocol verifies keyboard tab order, focus rings, and skip links.
3. Audit report maps violations to specific WCAG 2.2 criteria with remediation code and exports Section 508 / EN 301 549 VPAT 2.5 reports (`tools/vpat_exporter.py`).

---

## 5. Handoff Protocol

- **Deliverables:** WCAG 2.2 accessibility audit report, violation element selectors, and CSS/HTML remediation snippets.
- **Next Subagent:** quality-gatekeeper
- **Output Format:** Clean POM code, structured JSON telemetry, or validated markdown handoff.
