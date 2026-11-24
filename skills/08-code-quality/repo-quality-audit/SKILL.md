---
name: repo-quality-audit
description: "Comprehensive codebase quality audit covering bugs, security, bottlenecks, and bloat. Use when auditing an entire project, evaluating repository health, or prioritizing technical debt."
category: architecture_and_analysis
version: "1.0.0"
policies:
  network: none
  shell: read-only
  filesystem: read-only
---
# Repo Quality Audit — Comprehensive Repository Health & Risk Audit

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Comprehensive codebase quality audit covering bugs, security, bottlenecks, and bloat. Use when auditing an entire project, evaluating repository health, or prioritizing technical debt.
- **Activation Scope:** Domain workflows for `08-code-quality` involving `repo-quality-audit`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT produce superficial line-count summaries without evaluating architectural health.
- Do NOT perform full-corpus reading of monolithic files into LLM context window.
- Do NOT report quality violations without referencing exact file paths and line spans.
- **Sibling Skill Boundaries:**
  - senior-code-review evaluates pull request diffs; repo-quality-audit inspects holistic codebase architecture across 6 dimensions.

---

## 3. Ordered Execution Workflow

Audit an entire repository like the senior engineer who just inherited it and will be paged when it breaks.
Prioritize: **Correctness -> Safety -> Scale -> Tests -> Speed -> Lean**.
Always rank issues and provide a clear **"Fix this first"** verdict.

---

### Mapping the Codebase First

Before diagnosing defects:
1. **Entry Points & Architecture:** Inspect entry points (CLI commands, route handlers, test runners, background workers) and dependency manifests (`package.json`, `pyproject.toml`, `pom.xml`, `build.gradle`).
2. **Expected Load:** Determine whether the system is a local utility, a parallel CI suite, or a high-throughput microservice.
3. **Data Flow Tracing:** Trace critical business flows end-to-end:
   - External inputs and request payloads
   - Authentication & authorization checks
   - Database mutations and state persistence
   - Teardown and cleanup lifecycles

---

### Six Audit Dimensions

| Dimension | Inspection Focus | Red Flags |
|---|---|---|
| **1. Bugs & Logic** | Edge cases, return type mismatches, error handling | Swallowed exceptions, null dereferences, broken callers |
| **2. Security & Data** | Trust boundaries, authentication, secrets | Hardcoded tokens, SQLi/RCE risks, missing input sanitization |
| **3. Concurrency & Scale** | Resource contention, memory lifecycle | Race conditions, static sleeps, unbounded caches, unclosed connections |
| **4. Test Deficit** | Untested business-critical logic | Complex branches or parsers with zero test assertions |
| **5. Performance** | Hot paths, loop overhead | Unindexed queries, redundant network calls, $O(n^2)$ iterations |
| **6. Bloat & Dead Code** | Code that should not exist | Unused dependencies, duplicate helper functions, single-impl interfaces |

---

### Reporting Structure

1. **Overview & Assumptions:**
   - What this codebase does
   - The operational load assumed
2. **Ranked Findings (Max 20, ordered by severity):**
   - **Must fix (Blockers):** Bugs causing data loss, security CVEs, unhandled crashes.
   - **Should fix (Reliability):** Concurrency races, missing regression tests, flaky waits.
   - **Nice to have (Hygiene):** Dead code removal, dependency pruning, code deduplication.
3. **Verdict & Lean Metric:**
   - **Verdict:** "Fix #1 first: [Summary of top priority issue]"
   - **Lean Savings Potential:** Potential reduction in lines of code (`-N lines`) and unused dependencies (`-M dependencies`).
   - **Not Checked:** Explicitly state any submodules or third-party assets omitted.

#### Audit Finding Format Template

<!-- classification: illustrative -->
```markdown
### [MUST FIX] Critical: Swallowed Database Connection Pool Exception
- **Location:** `src/db/connection_pool.ts:42-48`
- **Impact:** Unhandled pool exhaustion silently freezes test worker threads.
- **Evidence:** `catch (err) { /* silent pass */ }` violates Zero Fake Passes rule.
- **Remediation:** Propagate `PoolExhaustionError` with bounded timeout or retry policy.
```

---

### Complementary Hub Tools

- `python3 tools/core/analyze_project.py` — 5-in-1 automated health audit and AST repo map.
- `python3 tools/core/verify_all.py` — 10 Quality Gates DoD gatekeeper.
- `python3 tools/core/debt_harvester.py` — Scan repository for unaddressed shortcut debt.

---

### Attribution

Adapted from **ponytail-audit** (https://github.com/DietrichGebert/ponytail) — MIT License, Copyright (c) 2026 DietrichGebert. Re-architected for Enterprise QA and Synapse Hub Standards.

---

## 4. Verification Points & DoD

1. Codebase mapped via AST / repo_map before auditing.
2. Audit covers architecture, Clean POM separation, test coverage, security, and technical debt.
3. Findings prioritized by severity with actionable remediation steps.

---

## 5. Handoff Protocol

- **Deliverables:** Comprehensive repository quality audit report (`PROJECT_HEALTH_REPORT.md`) and debt catalog.
- **Next Subagent:** orchestrator
- **Output Format:** Clean POM code, structured JSON telemetry, or validated markdown handoff.
