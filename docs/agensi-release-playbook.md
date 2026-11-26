<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Agensi.io 6-Pack Standalone Release & Pricing Playbook

> **Author & MIT License Attribution:** All 6 standalone skill packages are distributed from **Synapse Hub** under the MIT License by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>).

---

## 1. Launch Catalog & Pricing Strategy

Build all 6 verified `.zip` bundles under `dist/agensi/` with:

```bash
python scripts/package_agensi_skills.py --build-all --verify-isolated --json
```

| # | Slug & ZIP Artifact | Tier | Suggested Price | Bundled Scripts | External Pip Deps |
| :---: | :--- | :---: | :---: | :--- | :---: |
| **1** | `review-spec` (`dist/agensi/review-spec.zip`) | Free Funnel | **$0** | `goldfish_review.py` | None (stdlib) |
| **2** | `skillspector-security-guard` (`dist/agensi/skillspector-security-guard.zip`) | Entry Paid | **$7 – $9.99** | `skillspector.py` | None (optional `pathspec`) |
| **3** | `rbt-manual-testing-excel` (`dist/agensi/rbt-manual-testing-excel.zip`) | Entry Paid | **$7 – $9.99** | `template_excel_exporter.py`, `md_to_xlsx.py`, `checklist_query.py`, `manual_tc_linter.py` | `openpyxl>=3.1.0` |
| **4** | `wcag-a11y-audit` (`dist/agensi/wcag-a11y-audit.zip`) | Entry Paid | **$5 – $7** | `wcag_audit.py` | None (stdlib) |
| **5** | `api-contract-and-fuzzer` (`dist/agensi/api-contract-and-fuzzer.zip`) | Pro Suite | **$9.99 – $15** | `generate_api_matrix.py`, `api_drift_sentinel.py`, `api_fuzzer.py`, `pentest_scope_guard.py`, `fuzz_payloads.py` | None (stdlib) |
| **6** | `anti-fake-pass-mutation` (`dist/agensi/anti-fake-pass-mutation.zip`) | Pro Suite | **$9.99 – $14.99** | `micro_mutator.py`, `equivalent_mutant_filter.py`, `test_impact.py` | None (stdlib) |

*(Note: `playwright-live-interaction.zip` serves as the first Free funnel listing alongside `review-spec`.)*

---

## 2. Ready-to-Paste Agensi.io Listing Copy

### 2.1 `review-spec` (Free Funnel — `$0`)
- **Title:** `Review Spec — Zero-Context Specification Stress-Tester`
- **Short Summary:** `Stress-test PRDs, BRDs, user stories, and BDD feature files with zero-context Goldfish rigor before writing code — includes standalone Python scorer.`
- **Agensi Tools:** Leave empty (`None yet`).
- **About Footer:** `Open-source MIT skill from Synapse Hub by Thế Vị (@TeeVee98): https://github.com/TeeVee98/Synapse-Hub`

### 2.2 `skillspector-security-guard` (`$7 – $9.99`)
- **Title:** `SkillSpector Security Guard — AI Agent & MCP Security Scanner`
- **Short Summary:** `Audit SKILL.md files, agent prompts, scripts, and MCP configs against 71 vulnerability patterns (prompt injection, exfiltration, tool poisoning, AST sinks) with JSON/SARIF output.`
- **Agensi Tools:** Leave empty (`None yet`).
- **Agensi Security Reviewer Note:** `scripts/skillspector.py` is a defensive static security scanner inspired by NVIDIA/SkillSpector (Apache 2.0). It embeds static regex pattern definitions (for detecting prompt injection, shell pipes, and credential paths) strictly as read-only match signatures; it performs zero network calls, zero command execution, and zero file mutations.

### 2.3 `rbt-manual-testing-excel` (`$7 – $9.99`)
- **Title:** `RBT Manual Testing & Excel Exporter (ISO 29119-3)`
- **Short Summary:** `Design ISO 29119-3 Risk-Based manual test suites, query 25 field-level validation checklists on demand, lint completeness, and export formatted Excel (.xlsx) workbooks.`
- **Agensi Tools:** Leave empty (`None yet`).
- **Buyer Prerequisite Note:** Python 3.10+ (`pip install -r requirements.txt` for `openpyxl` Excel export; `checklist_query.py` and `manual_tc_linter.py` run on Python stdlib with zero installs).

### 2.4 `wcag-a11y-audit` (`$5 – $7`)
- **Title:** `WCAG 2.2 Accessibility Audit & Automated HTML Linter`
- **Short Summary:** `Audit HTML files and localhost pages against WCAG 2.2 Level A/AA criteria with a zero-dependency Python linter plus Playwright axe-core and keyboard focus-trap playbooks.`
- **Agensi Tools:** Leave empty (`None yet`).

### 2.5 `api-contract-and-fuzzer` (`$9.99 – $15`)
- **Title:** `API Contract Matrix, Schema Drift & Autonomous Fuzzer Suite`
- **Short Summary:** `Generate positive/boundary/negative test matrices from OpenAPI specs, detect breaking contract drift, and run scope-guarded API fuzzing — 100% Python stdlib.`
- **Agensi Tools:** Leave empty (`None yet`).

### 2.6 `anti-fake-pass-mutation` (`$9.99 – $14.99`)
- **Title:** `Anti-Fake-Pass Mutation Sentinel & Verification-First TDD`
- **Short Summary:** `Catch tautological AI-generated tests and fake passes with syntactic micro-mutation testing (Python/TS/JS/Groovy) and strict Red-Green-Refactor verification discipline.`
- **Agensi Tools:** Leave empty (`None yet`).

---

## 3. Affiliate & Distribution Checklist
1. Generate your personal Agensi affiliate link for each paid listing to capture **90% revenue share** on referred buyers (plus **20%** on their other marketplace purchases for 6 months).
2. Link the Free funnel skills (`playwright-live-interaction`, `review-spec`) from GitHub README, LinkedIn, and blog walkthroughs to drive qualified traffic to paid suites.
3. Preserve `LICENSE` and MIT copyright attribution (`Thế Vị (@TeeVee98)`) inside every uploaded `.zip`.

---

## 4. Buyer Troubleshooting Reference
- **Zero-pollution guarantee:** All bundled scripts anchor outputs (`reports/`, audit logs, exported files) to the buyer's current working directory (`cwd`) and never modify the installed skill directory.
- **Missing `openpyxl` on `rbt-manual-testing-excel`:** Run `pip install -r requirements.txt`. Scripts print an explicit English remediation message instead of a traceback.
- **Windows terminal encoding:** All scripts automatically reconfigure `stdout`/`stderr` to UTF-8.

---

## 5. Empirical Build & Certification Receipt

Built and verified via `python scripts/package_agensi_skills.py --build-all --verify-isolated`:

| Package Slug | Isolated CLI Smoke Tests | Dead CLI / Broken Links | UTF-8 No BOM | SkillSpector Verdict | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `review-spec` | `goldfish_review.py` (`--help`, `--mode brd --json`) | `0 / 0` | PASS | `SAFE` | **PASS** |
| `skillspector-security-guard` | `skillspector.py` (`--help`, `--format json`) | `0 / 0` | PASS | `SAFE` | **PASS** |
| `rbt-manual-testing-excel` | `template_excel_exporter.py`, `checklist_query.py`, `manual_tc_linter.py` | `0 / 0` | PASS | `SAFE` | **PASS** |
| `wcag-a11y-audit` | `wcag_audit.py` (`--help`, sample HTML) | `0 / 0` | PASS | `SAFE` | **PASS** |
| `api-contract-and-fuzzer` | `generate_api_matrix.py`, `api_drift_sentinel.py`, `api_fuzzer.py --dry-run` | `0 / 0` | PASS | `SAFE` | **PASS** |
| `anti-fake-pass-mutation` | `micro_mutator.py` (`--help`, `--dry-run --json`) | `0 / 0` | PASS | `SAFE` | **PASS** |

- **Zero-Pollution Verified:** Isolated runs executed in an out-of-repo temp directory (`PYTHONPATH=""`) produced zero stray files inside the extracted skill directories.
- **Hub Schema & Rule 16:** `cli_schema_sentinel.py --check` (`drift_count: 0`, `unregistered_public: []`) and `invariant_checker.py --rule 16` (`violations_count: 0`) both passed.
