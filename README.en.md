# 🧠 Synapse Hub — AI Test Quality Linter & Guardrails for Automated Testing
### *Zero-Dependency Quality Linter, Fake-Pass Sentinel & Guardrails for AI-Generated Tests*

[🇻🇳 Tiếng Việt](README.md) | [🇬🇧 English Edition](README.en.md)

> **Core Mission:** A standalone, zero-dependency Linter & Guardrail engine (zero external dependencies for core engine & DoD gates) protecting test suite integrity in the era of AI code generation — Catching tautological "fake-pass" tests, eliminating hard sleeps, distilling 95% CI log noise, and enforcing Clean POM architecture. Specialized tools (Excel export, Canvas visual diff) leverage standard optional extras (`openpyxl`, `Pillow`).  
> **Extended Ecosystem:** Bundled with 37 production QA skills, 6 specialized AI roles, and 9 DoD Quality Gates supporting Playwright, Cypress, Pytest, and Katalon.  
> **Author:** Thế Vị ([@TeeVee998](https://github.com/TeeVee998))  
> **Hub Version:** `v2.3.0` | **Scope:** 37 Standardized Skills, 6 Specialized AI Agents, 60+ Python Tools and Utilities, 9 DoD Quality Gates.

[![npm version](https://img.shields.io/npm/v/synapse-hub.svg?style=flat-square&color=blue)](https://www.npmjs.com/package/synapse-hub)
[![node version](https://img.shields.io/badge/node-%3E%3D16.0.0-brightgreen.svg?style=flat-square)](https://nodejs.org)
[![license](https://img.shields.io/badge/license-MIT-green.svg?style=flat-square)](https://github.com/TeeVee998/Synapse-Hub/blob/main/LICENSE)
[![Ecosystem](https://img.shields.io/badge/AI%20Ecosystem-Antigravity%20%7C%20Cursor%20%7C%20Claude%20%7C%20Copilot%20%7C%20Windsurf-orange.svg?style=flat-square)](#)

---

## ⚡ 1. The 60-Second "Wow" (3 Hero Features 🦸‍♂️)

No need to read dozens of documents or configure complex frameworks. You can immediately solve three daily QA pain points:

### 🔍 1. Catch "Fake-Pass", Static Sleeps & Swallowed Exceptions
```bash
npx synapse-hub lint ./tests
```
* **The Problem:** AI-generated tests frequently pass unconditionally without testing anything (zero assertions), rely on flaky hardcoded sleeps (`Thread.sleep`), or hide exceptions in empty `try-catch` blocks.
* **The Solution:** Polyglot heuristic & static AST linter (Playwright TypeScript/JavaScript, Pytest Python, Cypress, Groovy/Katalon) flags defects in 0.1s without LLM tokens.

### 📊 2. Convert Requirements Into Standard 12-Column Excel
```bash
npx synapse-hub export-excel
```
* **The Problem:** QA engineers spend tedious hours manually formatting Excel sheets from user stories or Markdown scenarios.
* **The Solution:** Compiles test scenarios directly into formatted 12-column `.xlsx` spreadsheets with calculated P × I risk scoring, ready for PMs and stakeholders.

### 🧹 3. Distill 95% CI Log Bloat Down to Root Cause
```bash
npx synapse-hub distill path/to/ci.log
```
* **The Problem:** CI/CD build logs containing 20,000+ lines overwhelm LLM context windows and human eyes.
* **The Solution:** Filters out 95% repetitive noise and extracts ~30 lines containing the exact failing line, exception stacktrace, and HTTP status.

### 💻 Real-World Terminal Output (Catching Defects in 0.1s Zero-Token):
```bash
$ npx synapse-hub lint ./tests

======================================================================
    ENTERPRISE STATIC DEFECT & FAKE-PASS SENTINEL
======================================================================
  Target Scope       : 6 Test Scripts (Polyglot TS/Python/Groovy)
  Detected Items:
    - [CRITICAL] tests/checkout.spec.ts:42 - Fake-pass risk: Test contains 0 assertions!
    - [CRITICAL] tests/login.spec.ts:14 - Hardcoded sleep (5000ms) detected. Replace with dynamic wait.
======================================================================
Result: 2 anti-patterns flagged in 0.12s (Zero LLM tokens used).
```

---

## 🚀 2. Fast & Non-Intrusive Onboarding

Synapse Hub respects your workspace privacy and system boundaries. You have complete control over disk writes:

```bash
# 🩺 Diagnose your local environment in 1 second (Node, Python, Chrome, Git):
npx synapse-hub doctor

# 💡 Pro Tip: Install globally to run commands directly without npx:
npm install -g synapse-hub
synapse-hub doctor

# 🔹 Option 1: Project-local configuration only (Safest, does not touch ~/.gemini)
npx synapse-hub setup --local-only

# 🔹 Option 2: Dry-run simulation (Preview actions without writing any file to disk)
npx synapse-hub setup --dry-run

# 🔹 Option 3: Full setup (Generates PROJECT_AI_GUIDE.md, AI bridges and Antigravity plugin)
npx synapse-hub setup

# 🔹 Completely revert and uninstall at any time:
npx synapse-hub uninstall
```

### Run Quality DoD Gates:
```bash
npx synapse-hub verify         # Execute 9 Quality Gates DoD (Gate 0–8)
npx synapse-hub analyze        # Comprehensive 5-in-1 project health audit
```

### 🔄 3-Line CI/CD Integration (GitHub Actions / GitLab CI):
Drop this step into your CI pipeline to automatically reject sub-par test code before merging:
```yaml
- name: Run Synapse Hub Quality Gates
  run: npx synapse-hub verify
```
*(See full templates and parameters in [docs/CI_CD_INTEGRATION.md](docs/CI_CD_INTEGRATION.md)).*

| Gate | Gate Name | Practical Verification Objective |
| :---: | :--- | :--- |
| **Gate 0** | **Author Attribution & MIT** | Canonical author attribution invariant preserving author Thế Vị (@TeeVee998) MIT notice. |
| **Gate 1** | **UTF-8 No BOM Clean Encoding** | Scans 100% of repository files for illegal BOM bytes and mojibake corruption. |
| **Gate 2** | **Path Portability** | Prohibits local workstation paths (`/Users/...`, `C:\...`) in source code. |
| **Gate 3** | **Clean POM Flat Architecture** | Enforces 100% locator encapsulation in Page Classes; zero raw XPaths in test scripts. |
| **Gate 4** | **AI Docs Anti-Drift** | Verifies AST truth against `PROJECT_AI_GUIDE.md`, eliminating hallucinated PageClasses. |
| **Gate 5** | **Temp File Blacklist** | Prevents temporary build debris (`*.tmp`, memory dumps, stale artifacts) from leaking. |
| **Gate 6** | **Credential Security** | Blocks hardcoded plaintext passwords, private keys, and secret tokens in code. |
| **Gate 7** | **Static Defect & Fake-Pass Sentinel** | Static heuristic analysis catching 0-assertion tests, empty catch blocks, hardcoded/variable sleeps (≥ 3000ms), and unawaited promises. |
| **Gate 8** | **Assertion Sensitivity Sentinel** | Injects syntactic micro-mutations linked via dataflow (requires Score ≥ 80%). |

---

## 🎯 3. Level-Based Roadmap

| Level | What You Want | Synapse Hub Entry Point |
| :--- | :--- | :--- |
| **Fresher / Junior** | Learn fast, deliver immediately, understand weak asserts | • `npx synapse-hub export-excel`: Generate standard test cases.<br/>• `npx synapse-hub lint ./tests`: Understand why assertions are tautological.<br/>• Inspect Clean POM examples in `examples/practices/`. |
| **Mid-Level** | Reduce flakiness, cut locator maintenance | • `npx synapse-hub flaky scan ./tests`: Detect flaky tests and quarantine them.<br/>• `npx synapse-hub heal`: Semantic locator healing via AOM diffing.<br/>• Add linter to pre-commit git hooks. |
| **Senior / Lead** | Control, measurement, CI/CD safety gates | • `npx synapse-hub verify`: 9 Automated DoD Gates in CI.<br/>• `npx synapse-hub mutate ./tests`: Heuristic assertion sensitivity analysis before merge.<br/>• Standard Markdown/JSON telemetry for PR review bots. |

> *Pro Tip: If installed globally (`npm i -g synapse-hub`), you can use the shorter syntax `synapse-hub <cmd>` or equivalent aliases `synapse`, `agent-qa`.*

---

## 💎 4. Core Architecture & Engineering Pillars

```mermaid
flowchart TD
    subgraph Hub["🧠 Synapse Hub (Core v2.3.0)"]
        Skills[".agents/skills/ (37 Skills)"]
        Agents[".agents/agents/ (6 Specialized Roles)"]
        Rules[".agents/rules/ (11 Core Rules)"]
        Tools["tools/ (60+ Universal Python Tools)"]
        Workflows[".agents/workflows/ (10 Workflows)"]
    end

    subgraph ChatSession["💬 AI Agent Workspace / IDE"]
        Hub -->|Mount / Plugins| ChatSession
    end

    subgraph Projects["📁 Target Test Projects"]
        ProjectA["Playwright (TS/JS)"]
        ProjectB["Pytest (Python)"]
        ProjectC["Cypress / Katalon"]
    end

    ProjectA -->|Verify & Lint| ChatSession
    ProjectB -->|Verify & Lint| ChatSession
    ProjectC -->|Verify & Lint| ChatSession
```

### 🧠 Pillar 1: Fake-Pass Prevention & Assertion Sensitivity (Heuristic)
- **Static Defect Sentinel (`tools/infer_linter.py`):** Scans for anti-patterns: unasserted tests, swallowed catch blocks, hardcoded sleeps, and unawaited Playwright assertions.
- **Assertion Sensitivity Sentinel (`tools/micro_mutator.py`):** Injects lightweight syntactic micro-mutations (equality, relational, boundary inversions) to verify whether downstream assertions catch logic flaws. Enforces Sensitivity Score ≥ 80% to pass Gate 8.

### ⚡ Pillar 2: Context Optimization & Token Conservation
- **Log Distillation (`tools/distill_log.py`):** Truncates verbose terminal output to keep AI prompts concise.
- **AST Method Mapping (`tools/repo_map.py`):** Maps class methods into a compressed < 600 token index; no reading large monolithic files whole.
- **Episodic SQLite Memory (`tools/cache_resolver.py`):** Offline solution store at `~/.agent_memory/global_cache.db` (zero token queries).

---

## ⚖️ 5. Transparent Engineering & Known Limitations

To uphold our strict **Truth Anchor** standard, we openly disclose known system boundaries:

1. **Assertion Sensitivity is a Syntactic Heuristic, not Compiler-Grade Mutation Testing:**  
   `tools/micro_mutator.py` uses lexical AST pattern evaluation to test downstream assertion coverage in sub-second speed. It **does not replace** full dynamic runtime mutation testing frameworks (such as Stryker for JS/TS or mutmut for Python) when bytecode-level mutant kill-rate is mandated.
2. **Internal Benchmark Dataset:**  
   Benchmark figures are measured against the Hub's internal sample corpus to verify rule enforcement. Real-world results vary by target architecture, test framework, and code complexity.
3. **First-Class Modern Ecosystem Focus:**  
   Synapse Hub prioritizes standard modern ecosystems: **Playwright, Pytest, Cypress, Selenium**. Legacy enterprise frameworks such as Katalon Studio / Groovy are supported via dedicated adapters.
4. **Headless Browser Requirement:**  
   Live DOM inspection and locator self-healing require a headless browser environment (e.g., Playwright Chromium) to extract the Accessibility Object Model (AOM).

---

## 👥 6. Multi-Agent Swarm System (6 Specialized Roles)

| Subagent Role | Core Responsibilities | Key Skills | Included Tools |
| :--- | :--- | :--- | :--- |
| **`orchestrator`** | Workflow director, project bootstrapper, health auditor, state anchor. | `agent-orchestration`, `graphify`, `architecture-decision-records` | `setup_project.py`, `analyze_project.py`, `repo_map.py` |
| **`live-explorer`** | Live DOM/AOM probing via headless Playwright, destructive action firewall. | `playwright-live-interaction`, `self-healing-locator`, `visual-regression-sentinel` | `safety_firewall.py`, `browser_helpers.js` |
| **`pom-crafter`** | Clean POM engineer, API breaking change sentinel, story-to-script generator. | `clean-pom-crafter`, `lam-script-generator`, `synthetic-test-data-generator` | `generate_tc_from_story.py`, `api_drift_sentinel.py` |
| **`test-runner`** | Headless CLI suite dispatcher, parallel matrix sharder, log distiller. | `katalon-cli-runner`, `e2e-testing-patterns`, `flaky-test-sentinel-and-quarantine` | `matrix_sharder.py`, `distill_log.py`, `pinpoint_failure.py` |
| **`failure-analyst`** | Root cause autopsy, failing line isolation, automated bug ticket synthesis. | `failure-autopsy-and-healing`, `token-and-context-optimizer` | `auto_heal.py`, `bug_reporter.py`, `cache_resolver.py` |
| **`quality-gatekeeper`**| Sentinel guardian enforcing 9 DoD Quality Gates and assertion sensitivity. | `antigravity-test-sentinel`, `wcag-audit-patterns`, `security-dast-sentinel` | `verify_all.py`, `micro_mutator.py`, `infer_linter.py` |

---

## 📦 7. Standardized Skill Catalog (37 Skills in .agents/skills/)

<details open>
<summary><b>📦 Click to expand: 37 Standardized Skills</b></summary>

| # | Skill ID | Practical Capability |
|:---:|---|---|
| 1 | `clean-pom-crafter` | Clean POM & Flat Architecture page class design (zero raw selectors in test scripts). |
| 2 | `playwright-live-interaction` | Live DOM/AOM exploration and < 200ms selector verification via headless Playwright. |
| 3 | `failure-autopsy-and-healing` | Failure triage from JUnit XML/screenshots and automated broken locator repair. |
| 4 | `infer_linter` / `antigravity-test-sentinel` | Quality gatekeeper enforcing zero fake-passes and 9 DoD quality gates. |
| 5 | `token-and-context-optimizer` | Prompt context optimization, log distillation, and Context Rot prevention. |
| 6 | `flaky-test-sentinel-and-quarantine` | Non-deterministic test detection, flakiness scoring, and quarantine management. |
| 7 | `api-spec-to-e2e-matrix` | Convert OpenAPI/Swagger specifications into E2E testing matrices. |
| 8 | `api-network-mocking-interception` | HTTP/GraphQL traffic stubbing, route mocking, and chaos network failure simulation. |
| 9 | `synthetic-test-data-generator` | Generate idempotent, collision-free synthetic test data with timestamps. |
| 10 | `db-state-verifier-and-seeder` | Seed isolated test fixtures and assert database state across SQL and NoSQL. |
| 11 | `visual-regression-sentinel` | Screenshot layout comparison with dynamic anti-flake element masking. |
| 12 | `wcag-audit-patterns` | Accessibility auditing against WCAG 2.2 A/AA and semantic ARIA roles. |
| 13 | `security-dast-sentinel` | Dynamic security analysis: OWASP Top 10, security headers, token leaks, and IDOR. |
| 14 | `web-vitals-and-performance-profiler` | Core Web Vitals (LCP, CLS, INP) measurement and network waterfalls via CDP. |
| 15 | `backend-load-and-stress-patterns` | Orchestrate k6, Locust, and Apache JMeter backend load and SLA endurance test suites. |
| 16 | `auth-session-and-cookie-manager` | Browser session `storageState`, JWT token management, and multi-role states. |
| 17 | `file-and-report-validator` | Tabular integrity and schema validation for downloaded/uploaded files (Excel, CSV, PDF). |
| 18 | `e2e-testing-patterns` | Multi-browser E2E test architectures, parallel sharding, and retry governance. |
| 19 | `lam-script-generator` | Transform user stories and acceptance criteria into runnable Clean POM test scripts. |
| 20 | `katalon-cli-runner` | Headless test execution for Katalon and Gradle suites with automatic driver cleanup. |
| 21 | `bats-testing-patterns` | Automated testing for bash/sh scripts, CLI tools, and CI/CD pipelines with Bats. |
| 22 | `code-refactoring-refactor-clean` | Technical debt remediation and test refactoring using SOLID and Clean Code patterns. |
| 23 | `agent-orchestration-multi-agent-optimize` | Profile and optimize multi-agent swarm workloads and token throughput. |
| 24 | `architecture-decision-records` | Author and maintain technical Architecture Decision Records (ADRs). |
| 25 | `github-actions-templates` | Production-ready GitHub Actions workflow templates for automated test pipelines. |
| 26 | `graphify-impact-analyzer` | Code change blast radius analysis and impacted test scoping via AST graphs. |
| 27 | `skillspector-security-guard` | Audit AI agent skills and MCP configurations against prompt injection vectors. |
| 28 | `gherkin-to-suite` | Compile Gherkin `.feature` BDD files into an expanded test matrix, Universal IR, and coverage-gap report. |
| 29 | `rbt-manual-testing` | 6-stage Risk-Based Testing (AI-RBT) manual test case synthesis, 12-column matrix, and input checklist. |
| 30 | `agy-customizations` | Antigravity Customization System guide for skills, rules, hooks, and MCP servers. |
| 31 | `persistent-planning-files` | Persist plans, findings, and progress to three markdown files so multi-phase work survives context resets. |
| 32 | `surgical-coding-principles` | Four disciplined-change principles: state assumptions, minimal diffs, every line traces to the request. |
| 33 | `lean-code-ladder` | 7-rung reuse-first ladder: pick the smallest complete solution before writing new code. |
| 34 | `playwright-webapp-testing` | Managed server lifecycle (start/ready/teardown) for local Playwright webapp test runs. |
| 35 | `test-driven-development` | RED-GREEN-REFACTOR discipline: no production code before a watched failing test. |
| 36 | `systematic-debugging` | Four-phase root-cause investigation before any fix; 3 failed fixes signal an architecture question. |
| 37 | `verification-before-completion` | Evidence protocol: every pass/done claim requires fresh command output from the current session. |

> **Open source & credits:** Skills 31-37 are adapted from open-source projects (andrej-karpathy-skills, ponytail, planning-with-files, anthropics/skills, superpowers, wshobson/agents) — full license and author details in `NOTICE` (entries 16-21); companion external-tool guide in `docs/adopted-ecosystem-tools.md`.

</details>

---

## 🛠️ 8. CLI Tooling Arsenal (tools/)

Synapse Hub includes over 60 utility tools implemented entirely in the **Python Standard Library** (zero external dependencies):

```bash
# 1. Diagnose local environment (Node, Python, Chrome, Git)
npx synapse-hub doctor

# 2. Run 9 Quality Gates DoD Verification
npx synapse-hub verify

# 3. Scan for fake-passes, tautologies, and empty catch blocks
npx synapse-hub lint ./tests

# 4. Distill verbose CI/CD logs down to root causes
npx synapse-hub distill path/to/ci.log

# 5. Export test cases to formatted Excel .xlsx
npx synapse-hub export-excel

# 6. Verify assertion sensitivity via syntactic micro-mutations
npx synapse-hub mutate ./tests

# 7. Detect and quarantine flaky tests
npx synapse-hub flaky scan ./tests
```

*(See [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) and [tools/TOOLS_RUNBOOK.md](tools/TOOLS_RUNBOOK.md) for parameter details).*

> 💡 **Equivalent Command Aliases:** When installed globally (`npm i -g synapse-hub`), you can interchangeably use `synapse-hub`, `synapse`, or `agent-qa` (e.g., `synapse verify`, `agent-qa lint ./tests`).

---

## 📄 Provenance & Attribution (MIT License)

This software was created and designed by **Thế Vị ([@TeeVee998](https://github.com/TeeVee998))** under the open-source [MIT License](LICENSE).  
You are free to use, modify, and distribute this software, provided that the **original author attribution and copyright notice are preserved**.
