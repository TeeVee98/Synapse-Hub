---
name: self-healing-locator
description: "Heal broken locators using semantic AOM diffing with Role, Label, and TestId hierarchy. Use when locators break and automated healing strategies are needed."
category: verification_and_resilience
version: "2.1.0"
policies:
  network: none
  shell: workspace-sandbox
  filesystem: workspace-sandbox
---
# Self-Healing Locator Skill — Compact AOM Diffing

> **Canonical Delegation:** Consolidated under [`failure-autopsy-and-healing`](../failure-autopsy-and-healing/SKILL.md). Failure triage and full healing loops live in `failure-autopsy-and-healing`, and the 6-Tier Locator Ranking Hierarchy lives in `skills/01-web-automation/clean-pom-crafter/SKILL.md`; this skill strictly owns **AOM subtree diffing** when selector drift is confirmed.
>
> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Heal broken locators using semantic AOM diffing with Role, Label, and TestId hierarchy. Use when locators break and automated healing strategies are needed.
- **Activation Scope:** Domain workflows for `06-healing-and-resilience` repairing confirmed broken selectors.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
  - Do NOT dump raw full-page HTML (>50k tokens) into agent prompts; extract compact AOM subtrees (`<= 500` tokens).
  - Do NOT fall back to brittle positional XPaths or leak repaired selectors directly into test scripts.
  - Do NOT silently patch locators without logging confidence score and drift rationale.
- **Sibling Skill Boundaries:**
  - `failure-autopsy-and-healing`: owns stack-trace RCA before confirming locator drift.
  - `clean-pom-crafter`: owns the canonical 6-Tier Locator Hierarchy (`Role > Label > TestId > Form > Text > Scoped CSS/XPath`).

---

## 3. Ordered Execution Workflow

1. **Extract Compact AOM Subtree (`<= 500` tokens):**
   Run a bounded DOM/AOM probe around the active container (`.p-dialog, .modal-content, form` or `document.body`) returning `{tag, role, name, label, testId}` attributes, or run `tools/heal/heuristic_locator_matcher.py` offline.
2. **Rank & Verify Live Uniqueness:**
   Evaluate replacement candidates via `clean-pom-crafter`'s 6-Tier Locator Hierarchy (prefer ARIA Role/Label and `data-testid`) and assert `count === 1` via `playwright-live-interaction`.
3. **Patch Page Class Only:**
   Update the encapsulated locator inside the target Page Class (`BasePage` subclass) — never in test scripts — and re-verify execution.

---

## 4. Verification Points & DoD

1. Healed selector matches the single target element with $\ge 80\%$ confidence.
2. Locator update strictly preserves Clean POM encapsulation inside Page Classes.
3. Verification run passes cleanly using dynamic smart waits.

---

## 5. Handoff Protocol

- **Deliverables:** Updated Page Class locator definitions, healing confidence telemetry, and passing verification output.
- **Next Subagent:** `failure-analyst` / `pom-crafter`
- **Output Format:** Clean POM diff, structured JSON telemetry, or validated markdown handoff.
