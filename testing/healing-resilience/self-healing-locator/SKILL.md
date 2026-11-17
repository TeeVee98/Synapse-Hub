---
name: self-healing-locator
description: "Heal broken locators using semantic AOM diffing with Role, Label, and TestId hierarchy. Use when locators break and automated healing strategies are needed."
category: verification_and_resilience
version: "2.0.0"
policies:
  network: none
  shell: workspace-sandbox
  filesystem: workspace-sandbox
---
# Self-Healing Locator Skill — Token-Efficient AOM Diffing

> 💡 **Canonical Delegation Notice:** This skill is canonicalized under `failure-autopsy-and-healing` (`testing/healing-resilience/failure-autopsy-and-healing/SKILL.md`). For unified root cause failure analysis and locator self-healing, prefer delegating directly to `failure-autopsy-and-healing`.
>
> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Heal broken locators using semantic AOM diffing with Role, Label, and TestId hierarchy. Use when locators break and automated healing strategies are needed.
- **Activation Scope:** Domain workflows for `06-healing-and-resilience` involving `self-healing-locator`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT fall back to brittle positional XPaths when primary locators fail.
- Do NOT hardcode healed locators in test scripts; encapsulate updates inside Page Classes.
- Do NOT silently update locators without logging the drift and confidence score.
- **Sibling Skill Boundaries:**
  - failure-autopsy-and-healing handles full failure autopsies; self-healing-locator focuses specifically on runtime and static selector recovery using AOM diffing.

---

## 3. Ordered Execution Workflow

This skill provides an automated, token-conservative mechanism to diagnose, diff, and repair broken web element locators across web applications without overwhelming the LLM context window with raw HTML dumps.

---

### The Token Conservation Principle

- **Raw HTML DOM Problem:** Dumping a complete HTML webpage into the prompt can consume 50,000 to 150,000 tokens, degrading AI reasoning and triggering context rot.
- **AOM Subtree Solution:** Extract exclusively the **Accessibility Object Model (AOM)** tree or a 2-hop semantic DOM subtree surrounding the target element, consuming under **500 tokens**.

```mermaid
flowchart LR
    Broken["Broken Locator Encountered"] --> Probe["Extract Compact AOM Tree (500 tokens)"]
    Probe --> Rank["Apply Hierarchy: Role > Label > TestId"]
    Rank --> Test["Verify Uniqueness on Live DOM"]
    Test --> Patch["Patch Page Class Method"]
```

---

### Master Locator Ranking Hierarchy

When searching for a replacement locator, evaluate candidates in this strict priority order:

1. **Tier 1 — ARIA Role & Accessible Name:**
   - Playwright: `page.getByRole('button', { name: 'Thêm mới' })`
   - CSS: `[role="button"][aria-label="Thêm mới"]`
2. **Tier 2 — Form Control & Business Semantics:**
   - `input[formcontrolname="code"]`
   - `p-dropdown[formcontrolname="categoryId"]`
3. **Tier 3 — Dedicated Test Identifiers:**
   - `[data-testid="btn-create"]`
   - `[data-test="submit"]`
4. **Tier 4 — Stable Visual Text:**
   - `button:has-text("Xác nhận")`
5. **Tier 5 — Scoped Resilient Relative CSS:**
   - `.card.popup-data input.p-inputtext`

---

### In-Browser AOM Probing Snippet

Execute this compact JavaScript probe via Playwright or Chrome DevTools to locate the target node without dumping HTML:

<!-- classification: illustrative -->
```javascript
// Extract interactive elements tree scoped to active modal or container
() => {
  const container = document.querySelector('.p-dialog, .modal-content, form') || document.body;
  const elements = container.querySelectorAll('button, input, select, textarea, p-dropdown, [role="button"]');
  return Array.from(elements).map(el => ({
    tag: el.tagName.toLowerCase(),
    role: el.getAttribute('role') || el.type,
    name: el.getAttribute('name') || el.getAttribute('formcontrolname') || el.id,
    label: el.innerText?.trim() || el.getAttribute('aria-label') || el.placeholder,
    testId: el.getAttribute('data-testid')
  }));
}
```

---

### Healing Execution Checklist

1. **Verify Uniqueness:** Ensure the candidate locator matches exactly 1 element on the live DOM.
2. **Encapsulate in Page Class:** Update the locator constant or private selector inside the relevant Page Class (e.g. `BasePage` or domain Page Class).
3. **Never Leak to Test Scripts:** Test scripts must remain 100% clean of raw selectors.

---

### Boundary vs `failure-autopsy-and-healing`

- **This skill** = a locator-repair cascade (cache → testid → text-semantic →
  geometric relative match), used when the diagnosis "stale/broken locator"
  is ALREADY established. It takes a broken selector plus a DOM snapshot and
  returns healed candidates with confidence scores.
- **`failure-autopsy-and-healing`** = the upstream diagnosis that decides WHEN
  this skill is needed (it also handles every non-locator failure class this
  skill does not touch).
- Chain of custody: autopsy RCA → "locator drift" verdict → this skill repairs
  → autopsy re-runs the healed test to close the loop.

---

## 4. Verification Points & DoD

1. Healed selector matches target element with $\ge 80\%$ confidence.
2. Locator update strictly preserves Clean POM encapsulation in Page Classes.
3. Verification run confirms successful element interaction with healed selector.

---

## 5. Handoff Protocol

- **Deliverables:** Updated Page Class selector definitions, healing confidence log, and test verification output.
- **Next Subagent:** failure-analyst / pom-crafter
- **Output Format:** Clean POM code, structured JSON telemetry, or validated markdown handoff.
