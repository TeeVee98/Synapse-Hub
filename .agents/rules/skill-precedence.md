---
trigger: always_on
description: Skill Resolution Precedence, Inter-Skill Coordination, and Anti-Collision Protocol enforcing Workspace-Local skills over external generic plugin skills.
---

# Skill Resolution Precedence & Anti-Collision Protocol

> **Purpose:** Resolve overlapping trigger scopes between Project-Local Skills and External Plugins, as well as distinct operational boundaries among internal skills — eliminating context contagion, token bloat, and conflicting instructions.

---

## 1. Non-Negotiable Precedence Order

When executing tasks within automated testing repositories, all AI Agents must strictly apply the following 3-tier hierarchy:

```text
[Tier 1: Project-Local Skills] (.agents/skills/*) 
       v (Highest priority — Specialized, Context-Aware & Clean POM Enforced)
[Tier 2: Core Project Rules] (.agents/rules/*)
       v (Mandatory operating invariants & behavioral guardrails)
[Tier 3: External Plugin Skills] (antigravity-testing-kit, chrome-devtools-plugin, generic plugins)
       v (Suppressed whenever a Tier 1 skill exists)
```

---

## 2. External Plugin Suppression Matrix (Tier 1 vs Tier 3)

When an external plugin offers a capability that overlaps with a specialized Synapse Hub skill, the external skill is **strictly suppressed**:

| Task Domain | REQUIRED Skill (Tier 1) | SUPPRESSED Skill (Tier 3) | Architectural Reason |
|---|---|---|---|
| **POM & Test Authoring** | `clean-pom-crafter`<br/>`lam-script-generator` | `QA Automation Engineer`, `Test Generator` | Generic plugins generate raw XPaths and Selenium boilerplate; Hub strictly enforces Flat Architecture and zero raw locators in scripts. |
| **Code Change Review** | `senior-code-review` | `Generic PR Reviewer`, `Code Reviewer` | Evaluates 6 pillars (Bugs, Security, Concurrency, Missing Tests, Speed, Bloat) specifically against Git Diff. |
| **Locator Healing & Diffing** | `self-healing-locator`<br/>`failure-autopsy-and-healing` | `Locator Healer Agent` | Uses token-efficient semantic AOM diffing (Role > Label > TestId) instead of dumping thousands of raw HTML lines. |
| **Flaky Test Triage & RCA** | `failure-autopsy-and-healing`<br/>`flaky-test-sentinel-and-quarantine` | `Flaky Test Analyzer` | Triage occurs via 0-token JUnit XML parsing, screenshot autopsy, and SQLite episodic memory cache (`global_cache.db`). |
| **Live Probing & Inspection** | `playwright-live-interaction` | `Smart Locator Agent` | Direct CDP network idle 0, dynamic overlay detachment, and in-browser helper integration under 200ms. |
| **Accessibility (WCAG)** | `wcag-audit-patterns` *(Guideline)* | `a11y-debugging` *(Tooling Only)* | `wcag-audit-patterns` enforces WCAG 2.2 A/AA criteria; Chrome DevTools MCP is used strictly for low-level node inspection. |

---

## 3. Internal Inter-Skill Coordination & Boundary Separation

To prevent decision paralysis among internal skills in `.agents/skills/`, agents must strictly adhere to the following boundary matrix:

| Functional Area | Primary Skill | Sibling Skill | Distinct Responsibility & Hand-Off |
|---|---|---|---|
| **Code Creation** | `lean-code-ladder` | `surgical-coding-principles` | • `lean-code-ladder` governs **what to build** (descends 7-rung ladder, selects smallest working solution).<br/>• `surgical-coding-principles` governs **where to touch** (keeps git diff surgical, no unrelated file edits). |
| **Technical Debt** | `technical-debt-harvester` | `code-refactoring-refactor-clean` | • `technical-debt-harvester` is the **accountant** (scans and tracks `shortcut:` comments in Markdown ledgers).<br/>• `code-refactoring-refactor-clean` is the **surgeon** (executes SOLID refactoring and code smell remediation). |
| **Quality Review** | `senior-code-review` | `review-spec` (`goldfish_review`) | • `senior-code-review` audits **Source Code Diffs** (uncommitted / staged git changes).<br/>• `review-spec` audits **Requirements & User Stories** in a 0-context stress-test (Elephant-Goldfish model). |
| **System Audit** | `repo-quality-audit` | `analyze_project` (`tools/`) | • `analyze_project.py` produces **deterministic facts** (AST map, env check, data flow, 9 gates DoD).<br/>• `repo-quality-audit` applies **senior engineering judgment** (evaluates real load, ranks *"Fix #1 first"*). |
| **API Testing** | `api-spec-to-e2e-matrix` | `api-network-mocking-interception` | • `api-spec-to-e2e-matrix` compiles **test matrices** from OpenAPI specs.<br/>• `api-network-mocking-interception` stubs routes and injects **chaos network faults** during UI/API test runs. |
| **Failure Analysis** | `self-healing-locator` | `failure-autopsy-and-healing` | • `self-healing-locator` fixes **individual broken Page Class selectors**.<br/>• `failure-autopsy-and-healing` triages **suite-wide run crashes**, JUnit XML reports, and logs. |
| **DoD Verification** | `verification-before-completion` | `antigravity-test-sentinel` | • `verification-before-completion` enforces the **evidence protocol** (fresh command output required in session).<br/>• `antigravity-test-sentinel` is the **hard gatekeeper** (blocks task completion until all 9 Quality Gates pass). |

---

## 4. Strict Prohibitions

1. **Zero Generic Test Boilerplate:** Never generate legacy Selenium, Cucumber, or Object Repository (`findTestObject`) code from external plugins.
2. **Zero Raw HTML Dumps:** Never dump full HTML trees into context for locator healing; always extract compact AOM subtrees (< 500 tokens).
3. **Zero Unverified Assertions:** Never complete a code or test task without executing fresh verification via `tools/verify_all.py`.
