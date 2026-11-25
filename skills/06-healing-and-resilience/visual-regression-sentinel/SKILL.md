---
name: visual-regression-sentinel
description: "Run pixel and layout shift visual regression checks with anti-flake masking. Use when comparing screenshots for visual regressions with anti-flake masking."
category: verification_and_resilience
version: "2.0.0"
policies:
  network: localhost-only
  shell: workspace-sandbox
  filesystem: workspace-sandbox
---
# Visual Regression Sentinel Skill

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Run pixel and layout shift visual regression checks with anti-flake masking. Use when comparing screenshots for visual regressions with anti-flake masking.
- **Activation Scope:** Domain workflows for `06-healing-and-resilience` involving `visual-regression-sentinel`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT capture visual baselines with dynamic animated content unpaused or dynamic timestamps visible.
- Do NOT use arbitrary pixel threshold tolerances without masking expected variable regions.
- Do NOT overwrite visual golden baselines without explicit human review and approval.
- **Sibling Skill Boundaries:**
  - wcag-audit-patterns tests accessibility; visual-regression-sentinel detects unexpected pixel drift and visual layout regressions.

---

## 3. Ordered Execution Workflow

> **Target:** Catch unintended UI rendering defects, CSS breakages, alignment shifts, and missing visual assets across viewports without manual visual inspection.

---

### Core Principles

1. **Anti-Flakiness Masking:**
   - Always mask dynamic elements (timers, timestamps, random avatars, ads, blinking carets) before capturing baselines.
2. **Perceptual Diffing over Strict Pixel Match:**
   - Use SSIM (Structural Similarity Index) or perceptual threshold (`threshold: 0.2`) to tolerate minor antialiasing discrepancies between GPU rendering pipelines.
3. **Deterministic Viewports:**
   - Standardize viewport dimensions (`1920x1080` for Desktop, `390x844` for Mobile) and disable animations (`animations: 'disabled'`).

---

### Standard Playwright Visual Assertion Patterns

### Pattern A: Full-Page Screenshot with Dynamic Masking
<!-- classification: illustrative -->
```typescript
await expect(page).toHaveScreenshot('landing-page.png', {
  fullPage: true,
  animations: 'disabled',
  mask: [
    page.locator('.dynamic-timestamp'),
    page.locator('.live-ticker-banner'),
    page.locator('[data-testid="unique-id-badge"]')
  ],
  maxDiffPixelRatio: 0.02 // Allow 2% tolerance
});
```

### Pattern B: Component-Level Snapshot
<!-- classification: illustrative -->
```typescript
// Isolate critical component to avoid cascade failures from header/footer changes
const dataTable = page.locator('.custom-data-table');
await expect(dataTable).toHaveScreenshot('table-component-default.png', {
  threshold: 0.1
});
```

### Pattern C: Color Mode / Responsive Variations
<!-- classification: illustrative -->
```typescript
// Test Dark Mode
await page.emulateMedia({ colorScheme: 'dark' });
await expect(page).toHaveScreenshot('dashboard-dark.png');
```

---

### Visual Failure Autopsy Protocol
When visual regression fails:
1. Review generated diff image: `*-diff.png`.
2. Determine if it is a **Real Regression** (CSS bug, broken layout) or **Intentional Redesign**.
3. If intentional redesign: update baseline snapshots via `npx playwright test --update-snapshots`.
4. If bug: file bug report with side-by-side artifact comparison.

---

### Assert on Extracted Data, Not on the Model's Claim

> *Borrowed and adapted from the Midscene.js prompting model (MIT license, web-infra-dev/midscene).*

When an AI/vision agent reports a step as "done", that claim is **not evidence**:

1. **Extract the visible state first** — pull structured data from what is
   actually rendered (accessibility tree text, OCR'd region, or `aiQuery`-style
   structured extraction), never the model's self-report.
2. **Assert on the extracted values** — pair every extraction with a real
   assertion (`expect(...)`/`verify...`) against the expected value; a vision
   model can read a screen, but only an assertion can *prove* it.
3. **Vision sees pixels, not DOM internals** — assertions on tab counts,
   network state, or hidden attributes are invisible to the model; assert on
   what is rendered.
4. **Only then run the visual diff** — feed the §3 autopsy protocol; a green
   extraction plus a clean diff is proven, everything else is owed.

---

## 4. Verification Points & DoD

1. Dynamic elements (spinners, timestamps, animations) masked before screenshot capture.
2. Visual diff score stays within acceptable tolerance thresholds ($\le 0.1\%$).
3. Visual failure autopsy highlights exact pixel drift bounding box.

---

## 5. Handoff Protocol

- **Deliverables:** Visual snapshot baselines, diff highlight images, and visual regression autopsy report.
- **Next Subagent:** quality-gatekeeper
- **Output Format:** Playwright `toHaveScreenshot` diffs, anti-flake dynamic region masks, and pixel delta metrics.
