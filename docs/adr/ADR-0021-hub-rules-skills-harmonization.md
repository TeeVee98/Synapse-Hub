<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0021: Comprehensive Harmonization of Core Rules, IDE Bridges, and Domain Skills

- **Status:** Accepted
- **Date:** 2026-11-25
- **Deciders:** Thế Vị (@TeeVee98), Enterprise QA Architecture Review

## 1. Context & Problem Statement

A full-spectrum repository audit across Core Rules, Manual QA, Automation/Resilience, Security/Compliance, and Performance/Load surfaced five structural friction points:
1. **Static Rule Sync Drift:** `tools/core/sync_agent_rules.py` maintained a hardcoded `CANONICAL_INVARIANTS_MD` string rather than parsing `AGENTS.md`, allowing bridge files (`CLAUDE.md`, `.cursorrules`, `synapse-qa.mdc`) to drift silently on Invariant 16 and 17 updates while reporting `100% in sync`.
2. **Manual QA 12-Column Conflict:** `.cursor/rules/manual-qa.mdc` specified a 12-column schema incompatible with `rbt-manual-testing/SKILL.md`, `tools/lint/manual_tc_linter.py`, `spec_reconciler.py`, and `md_to_xlsx.py`.
3. **Wait & Clean POM Anti-Patterns in Docs:** `.cursor/rules/playwright.mdc` recommended `waitForLoadState('networkidle')` contradicting Invariant 3, and canonical skill code blocks (`web-vitals-and-performance-profiler`, `wcag-audit-patterns`) contained `waitForTimeout(500)` and `networkidle` shielded by `<!-- classification: illustrative -->`.
4. **Security & SLA Gate Edge Cases:** `ai-agents/hooks/pre_tool_use.py` failed open on malformed JSON or missing `pre_bash_guard`; `tools/security/safety_firewall.py` blocked single-entity `AUTO_` teardowns and staging checkout flows equally with bulk-destructive `Delete All`/`Purge`; `gate_10_perf_sla.py` triggered local CPU microbenchmarks even in `CLIENT` mode.
5. **Taxonomy & Bilingual Rule Drift:** `lean-impact-scoreboard` resided under `04-performance-and-load` (`perf` trigger), `testing/**/*.md` contained untranslated Vietnamese sections outside `invariant_checker.py` Rule 16 scope, and `gherkin_suite.py` ignored `# language: vi`.

## 2. Considered Options & Rulings

1. **Ruling 1 — Canonical 12-Column Schema + `@REQ-xxx` Tags + Optional 13th `REQ ID` Column:**
   - Standardized `.cursor/rules/manual-qa.mdc` onto `STANDARD_12_COLUMNS` (`TC ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags`), tracking `@REQ-xxx` tags in `Tags` and accepting optional 13-column (`REQ ID`) tables in `manual_tc_linter.py` (`rtm_linked_cases` metric).
   - *Rationale:* Zero breaking impact on existing 12-column test suites and Excel exporters while preserving full RTM requirement traceability.
2. **Ruling 2 — Mode-Split Gate 10 SLA & Risk-Tiered Safety Firewall:**
   - Scoped `auto_benchmark_fallback` in `gate_10_perf_sla.py` strictly to `HUB` mode; `CLIENT`/`TARGET` modes fail closed on missing or stale load test reports.
   - Converted `pre_tool_use.py` to strict fail-closed (`deny`, exit `1`) on malformed non-empty payloads or missing `pre_bash_guard`, and partitioned `safety_firewall.py` into unconditional catastrophic bulk blocks vs context-aware single-entity actions on `localhost`/`staging` or `AUTO_` test data.
3. **Ruling 3 — AST/Markdown Rule Extraction, Skill Relocation & Bilingual Gherkin:**
   - Implemented `extract_agents_md_sections()` in `sync_agent_rules.py`, `check_skill_code_fences()` in `lint_ai_docs.py`, expanded Rule 16 scanning in `invariant_checker.py` across `standards/` and `testing/`, relocated `lean-impact-scoreboard` to `skills/08-code-quality/`, and added `# language: vi` support in `gherkin_suite.py`.

## 3. Consequences

- **Positive:** Eliminates silent rule-bridge drift, enforces Clean POM and Dynamic Smart Waits inside skill documentation itself, closes fail-open hook edge cases, prevents synthetic SLA false positives in client repos, and enables native Vietnamese BDD `.feature` compilation with zero LLM tokens.
- **Trade-offs:** Client repositories enabling Gate 10 must supply genuine `.jtl` or `k6` artifacts within `max_artifact_age_hours` (or explicitly disable `gate_10_performance_sla` for non-perf pipelines).
