---
name: lam-script-generator
description: "Transform user stories and acceptance criteria into Clean POM automation scripts. Use when the user provides a user story, acceptance criteria, or requirement document that must become a runnable script."
category: test_automation_and_execution
version: "2.1.0"
policies:
  network: none
  shell: none
  filesystem: workspace-sandbox
---
# LAM Script Generator — User Story to Clean POM Bridge

> **Canonical Delegation:** Consolidated under [`clean-pom-crafter`](../clean-pom-crafter/SKILL.md). Page Class design, 6-tier locator priority, and code emission standards live in `clean-pom-crafter`; this skill strictly owns the **User Story -> Action Plan -> Proven-vs-Owed** translation layer.
>
> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Transform user stories and acceptance criteria into Clean POM automation scripts. Use when the user provides a user story, acceptance criteria, or requirement document that must become a runnable script.
- **Activation Scope:** Domain workflows for `01-web-automation` bridging NL requirements to Page Class calls.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
  - Do NOT inline raw XPaths, CSS selectors, or `findTestObject` in generated scripts (delegate selector encapsulation to `clean-pom-crafter`).
  - Do NOT hallucinate non-existent Page Classes; inspect existing AST symbols via `project_state.json` first.
  - Do NOT generate scripts that call an LLM at runtime during CI/CD replays.
- **Sibling Skill Boundaries:**
  - `clean-pom-crafter`: owns Page Classes, BasePage helpers, and 6-tier locator selection.
  - `gherkin-to-suite`: compiles existing `.feature` files deterministically into Universal IR before synthesis.

---

## 3. Ordered Execution Workflow

1. **World Model (Requirements -> Action Sequence):**
   - Extract atomic steps from User Stories / Acceptance Criteria (`Login -> Navigate -> Mutate Dynamic Entity -> Assert -> Teardown`).
   - Attach the AC identifier (`AC-xx`) to every generated test case.
2. **Action Engine (Zero-Selector Delegation to `clean-pom-crafter`):**
   - Map steps strictly to existing Page Class business methods (`LoginPage.login()`, `DomainPage.createRecord()`).
   - Inject dynamic timestamps (`BasePage.uniqueCode("AUTO_")`) and automated teardown cleanup.
3. **Proven-vs-Owed Traceability Check:**
   - Every AC must map to at least one passing test (`Proven`); unmapped criteria remain `Owed` until covered.
   - Reconcile stale scripts whenever acceptance criteria change.

---

## 4. Verification Points & DoD

1. Generated scripts call strictly Page Class methods (zero raw locators).
2. Test entities use dynamic timestamped codes (`BasePage.uniqueCode()`) with teardown cleanup.
3. Every Acceptance Criterion is traced as `Proven` and runs deterministically offline.

---

## 5. Handoff Protocol

- **Deliverables:** Clean POM test scripts (`TC-xxx.groovy`, `*.spec.ts`, `test_*.py`) mapped to AC IDs.
- **Next Subagent:** `pom-crafter` / `test-runner`
- **Output Format:** Clean POM code, Proven-vs-Owed traceability summary, or validated markdown handoff.
