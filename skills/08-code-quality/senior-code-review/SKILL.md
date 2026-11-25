---
name: senior-code-review
description: "Review code changes across logic, security, concurrency, and test coverage. Use when conducting pull request reviews, diff inspections, or auditing commit changes before merge."
category: architecture_and_analysis
version: "1.1.0"
policies:
  network: none
  shell: read-only
  filesystem: read-only
---
# Senior Code Review — Enterprise Quality & Lean Diff Review

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Review code changes across logic, security, concurrency, and test coverage. Use when conducting pull request reviews, diff inspections, or auditing commit changes before merge.
- **Activation Scope:** Domain workflows for `08-code-quality` involving `senior-code-review`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT approve code containing fake passes, swallowed exceptions, or static sleeps.
- Do NOT nitpick subjective formatting preferences that automated linters already handle.
- Do NOT review diffs without inspecting callers and impact blast radius.
- **Sibling Skill Boundaries:**
  - repo-quality-audit audits entire repos; senior-code-review performs 6-pillar inspection on active git diffs and PRs.

---

## 3. Ordered Execution Workflow

Review code changes like the senior engineer who will be paged at 2 AM when it breaks.
Order of importance: **Correctness -> Safety -> Scale -> Tests -> Speed -> Lean**.
Lean still matters: every extra line must be read, tested, and fixed later.

---

### Understand First

- **Target Scoping:** Review what the user requests: uncommitted or staged changes, a branch, a PR link, or specific files. If unspecified: uncommitted changes (or last commit if clean).
- **Read Beyond the Diff:** Read the diff, then read the code it touches:
  - Callers of every changed function or Page Class method.
  - Functions and services called by the diff.
  - Associated unit/E2E tests and fixtures.
- **Trace the Real Flow:** Where does user input arrive? What is validated? Where is state persisted? What is emitted?
- **Expected Scale:** Identify the expected operational load (single script execution vs concurrent CI runners or thousands of users). Judge scale against that.

---

### Six Core Review Pillars

### 1. Bug & Edge Cases
- Wrong calculation, crash, or unhandled edge cases (empty collections, zero values, timezone drift, string encoding).
- Callers broken by changed method signatures or altered return types.
- A bug fixed in one caller while the shared function/keyword remains broken for others.

### 2. Risk & Security
- Injection vulnerabilities (SQL, Shell, Command, Path traversal).
- Hardcoded secrets, plain tokens, or private keys.
- Missing input validation at trust boundaries.
- Data loss risks: swallowed errors, unhandled promise rejections, missing DB transactions.

### 3. Scale & Concurrency
- Race conditions (check-then-act without locking).
- Memory or cache leaks (unbounded collections that only grow).
- $O(n^2)$ iterations or N+1 queries on variable-sized data.
- Static delays (`Thread.sleep`, `time.sleep`) that block event loops or fail under variable network latency.

### 4. Missing Tests
- New non-trivial logic (branch, loop, parser, auth check, payment/money path) lacking a test that fails when broken.
- Every bug fix must include a regression test proving the fix.

### 5. Speed & Latency
- Bottlenecks in hot paths and repeated iterations.
- Unnecessary synchronous I/O or redundant API re-fetching.

### 6. Lean & Anti-Bloat
- **Delete:** Dead code, commented-out code, unused options, speculative configuration.
- **Reuse:** Leverage existing Page Classes, BasePage helpers, or utility functions.
- **Stdlib / Native:** Use platform features instead of adding external dependencies.
- **YAGNI:** Remove single-use abstractions, single-impl interfaces, and passthrough wrappers.

### 7. Anti-Junk Tests & Writing Hygiene (test-audit & humanize)
- **Anti-Junk Tests:** Flag tests asserting mock data, testing private implementation details, or introducing test-only seams in Page Classes.
- **Writing & Tone Hygiene:** Audit commit text, PR descriptions, and code docstrings using `tools/lint/humanize_linter.py` to eradicate robotic AI buzzwords (`leverage`, `plethora`, `delve`, `vibrant tapestry`) and em-dash misuse.

---

### The 4-Angle Cleanup Model (`simplify`)

> Adapted from the Claude Codex `simplify` plugin. Evaluate every diff through four independent cleanup lenses before accepting changes:

| Angle | Focus Question | Review Directive |
| :--- | :--- | :--- |
| **1. Reuse** | *Does this helper or pattern already exist?* | Flag new code that re-implements something the codebase already has. Grep shared helpers, `BasePage`, and adjacent Page Classes; call the existing function instead of adding a new one. |
| **2. Simplification** | *Can this be expressed in fewer moving parts?* | Flag unnecessary complexity added by the diff: redundant or derivable state, copy-paste with slight variation, deep nesting, dead code left behind. Name the simpler form that does the exact same job. |
| **3. Efficiency** | *Is work wasted or memory retained?* | Flag redundant computation, repeated I/O, independent operations run sequentially, and blocking delays added to hot paths. Flag long-lived closures that capture large outer scopes (closure memory leak); prefer classes/structs with only necessary fields. |
| **4. Altitude** | *Is the change made at the right architectural depth?* | Check that each change is implemented at the root cause, not as a fragile surface bandaid. Special cases layered on shared infrastructure indicate a fix that isn't deep enough; generalize the underlying mechanism rather than adding conditional special cases. |

---

### Concrete Reporting Format

Every finding **must** have a concrete, reproducible failure scenario:

<!-- classification: illustrative -->
```markdown
#### [Severity: Must fix | Should fix | Nice to have] <Finding Title> (`<file>:<line>`)
- **What this is:** <One concise sentence describing the touched code>
- **Problem:** <Specific input or scenario that leads to the defect or failure>
- **Fix:** <Smallest complete diff or code change to resolve the issue>
- **If we skip it:** <What goes wrong in production or CI pipeline>
```

---

### Onboarding Explainer & 4-Tier Lead Verdict (How + Critique Mode)

When reviewing an unfamiliar subsystem or synthesizing multi-model critique findings:
1. **Explain First (5-Section Onboarding Brief):** Before critiquing architecture, produce **Overview**, **Key Concepts**, **How It Works** (prose trace referencing real files/functions), **Where Things Live**, and **Gotchas**.
2. **4-Tier Lead Verdict:** Classify every architectural finding pragmatically rather than aggregating uncritically:
   - **Act on:** Concrete architectural defect worth fixing now.
   - **Consider:** Real concern whose cost/benefit needs explicit tradeoff review.
   - **Noted:** Valid observation, low priority for current scope.
   - **Dismissed:** Incorrect, missing context, or pure style preference.

---

### Automation CLI

Run the automated senior review tool on your current working tree:
<!-- classification: illustrative -->
```bash
python3 tools/orchestration/senior_code_review.py            # Review uncommitted changes
python3 tools/orchestration/senior_code_review.py --staged   # Review staged git changes
python3 tools/orchestration/senior_code_review.py --branch main  # Compare against main branch
python3 tools/orchestration/senior_code_review.py --output-md REVIEW_REPORT.md  # Export to markdown report
```

---

### Attribution

Adapted from **ponytail-review** (https://github.com/DietrichGebert/ponytail) — MIT License, Copyright (c) 2026 DietrichGebert, and **claude-codex-settings / simplify** (Apache-2.0 / MIT). Re-architected for Enterprise QA, Clean POM, and Synapse Hub Quality Gates.

---

## 4. Verification Points & DoD

1. Code diff evaluated across 6 pillars (Architecture, Clean POM, Tests, Security, Performance, Lean Dev).
2. Zero raw locators in test scripts and zero secret leaks confirmed.
3. Review verdict issued with constructive, actionable pair-programming feedback.

---

## 5. Handoff Protocol

- **Deliverables:** Senior code review assessment report with line-specific recommendations.
- **Next Subagent:** quality-gatekeeper
- **Output Format:** Clean POM code, structured JSON telemetry, or validated markdown handoff.
