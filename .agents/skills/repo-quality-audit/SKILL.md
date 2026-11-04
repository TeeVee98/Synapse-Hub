---
name: repo-quality-audit
description: "Comprehensive codebase quality audit covering bugs, security, bottlenecks, and bloat. Use when auditing an entire project, evaluating repository health, or prioritizing technical debt."
category: architecture_and_analysis
version: "1.0.0"
---

# Repo Quality Audit — Comprehensive Repository Health & Risk Audit

Audit an entire repository like the senior engineer who just inherited it and will be paged when it breaks.
Prioritize: **Correctness -> Safety -> Scale -> Tests -> Speed -> Lean**.
Always rank issues and provide a clear **"Fix this first"** verdict.

---

## 1. Mapping the Codebase First

Before diagnosing defects:
1. **Entry Points & Architecture:** Inspect entry points (CLI commands, route handlers, test runners, background workers) and dependency manifests (`package.json`, `pyproject.toml`, `pom.xml`, `build.gradle`).
2. **Expected Load:** Determine whether the system is a local utility, a parallel CI suite, or a high-throughput microservice.
3. **Data Flow Tracing:** Trace critical business flows end-to-end:
   - External inputs and request payloads
   - Authentication & authorization checks
   - Database mutations and state persistence
   - Teardown and cleanup lifecycles

---

## 2. Six Audit Dimensions

| Dimension | Inspection Focus | Red Flags |
|---|---|---|
| **1. Bugs & Logic** | Edge cases, return type mismatches, error handling | Swallowed exceptions, null dereferences, broken callers |
| **2. Security & Data** | Trust boundaries, authentication, secrets | Hardcoded tokens, SQLi/RCE risks, missing input sanitization |
| **3. Concurrency & Scale** | Resource contention, memory lifecycle | Race conditions, static sleeps, unbounded caches, unclosed connections |
| **4. Test Deficit** | Untested business-critical logic | Complex branches or parsers with zero test assertions |
| **5. Performance** | Hot paths, loop overhead | Unindexed queries, redundant network calls, $O(n^2)$ iterations |
| **6. Bloat & Dead Code** | Code that should not exist | Unused dependencies, duplicate helper functions, single-impl interfaces |

---

## 3. Reporting Structure

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

---

## 4. Complementary Hub Tools

- `python3 tools/analyze_project.py` — 5-in-1 automated health audit and AST repo map.
- `python3 tools/verify_all.py` — 9 Quality Gates DoD gatekeeper.
- `python3 tools/debt_harvester.py` — Scan repository for unaddressed shortcut debt.

---

## 5. Attribution

Adapted from **ponytail-audit** (https://github.com/DietrichGebert/ponytail) — MIT License, Copyright (c) 2026 DietrichGebert. Re-architected for Enterprise QA and Synapse Hub Standards.
