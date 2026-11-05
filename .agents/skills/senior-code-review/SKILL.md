---
name: senior-code-review
description: "Review code changes across logic, security, concurrency, and test coverage. Use when conducting pull request reviews, diff inspections, or auditing commit changes before merge."
category: architecture_and_analysis
version: "1.1.0"
---

# Senior Code Review — Enterprise Quality & Lean Diff Review

Review code changes like the senior engineer who will be paged at 2 AM when it breaks.
Order of importance: **Correctness -> Safety -> Scale -> Tests -> Speed -> Lean**.
Lean still matters: every extra line must be read, tested, and fixed later.

---

## 1. Understand First

- **Target Scoping:** Review what the user requests: uncommitted or staged changes, a branch, a PR link, or specific files. If unspecified: uncommitted changes (or last commit if clean).
- **Read Beyond the Diff:** Read the diff, then read the code it touches:
  - Callers of every changed function or Page Class method.
  - Functions and services called by the diff.
  - Associated unit/E2E tests and fixtures.
- **Trace the Real Flow:** Where does user input arrive? What is validated? Where is state persisted? What is emitted?
- **Expected Scale:** Identify the expected operational load (single script execution vs concurrent CI runners or thousands of users). Judge scale against that.

---

## 2. Six Core Review Pillars

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
- **Writing & Tone Hygiene:** Audit commit text, PR descriptions, and code docstrings using `tools/humanize_linter.py` to eradicate robotic AI buzzwords (`leverage`, `plethora`, `delve`, `vibrant tapestry`) and em-dash misuse.

---

## 3. The 4-Angle Cleanup Model (`simplify`)

> Adapted from the Claude Codex `simplify` plugin. Evaluate every diff through four independent cleanup lenses before accepting changes:

| Angle | Focus Question | Review Directive |
| :--- | :--- | :--- |
| **1. Reuse** | *Does this helper or pattern already exist?* | Flag new code that re-implements something the codebase already has. Grep shared helpers, `BasePage`, and adjacent Page Classes; call the existing function instead of adding a new one. |
| **2. Simplification** | *Can this be expressed in fewer moving parts?* | Flag unnecessary complexity added by the diff: redundant or derivable state, copy-paste with slight variation, deep nesting, dead code left behind. Name the simpler form that does the exact same job. |
| **3. Efficiency** | *Is work wasted or memory retained?* | Flag redundant computation, repeated I/O, independent operations run sequentially, and blocking delays added to hot paths. Flag long-lived closures that capture large outer scopes (closure memory leak); prefer classes/structs with only necessary fields. |
| **4. Altitude** | *Is the change made at the right architectural depth?* | Check that each change is implemented at the root cause, not as a fragile surface bandaid. Special cases layered on shared infrastructure indicate a fix that isn't deep enough; generalize the underlying mechanism rather than adding conditional special cases. |

---

## 4. Concrete Reporting Format

Every finding **must** have a concrete, reproducible failure scenario:

```markdown
#### [Severity: Must fix | Should fix | Nice to have] <Finding Title> (`<file>:<line>`)
- **What this is:** <One concise sentence describing the touched code>
- **Problem:** <Specific input or scenario that leads to the defect or failure>
- **Fix:** <Smallest complete diff or code change to resolve the issue>
- **If we skip it:** <What goes wrong in production or CI pipeline>
```

---

## 5. Automation CLI

Run the automated senior review tool on your current working tree:
```bash
python3 tools/senior_code_review.py            # Review uncommitted changes
python3 tools/senior_code_review.py --staged   # Review staged git changes
python3 tools/senior_code_review.py --branch main  # Compare against main branch
python3 tools/senior_code_review.py --output-md REVIEW_REPORT.md  # Export to markdown report
```

---

## 6. Attribution

Adapted from **ponytail-review** (https://github.com/DietrichGebert/ponytail) — MIT License, Copyright (c) 2026 DietrichGebert, and **claude-codex-settings / simplify** (Apache-2.0 / MIT). Re-architected for Enterprise QA, Clean POM, and Synapse Hub Quality Gates.
