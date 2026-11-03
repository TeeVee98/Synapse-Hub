# Agent-Skills Architecture & Design Principles

> **Scope:** Enterprise Multi-Agent QA Hub  
> **Version:** `2.4.3` | **Status:** Active / Production Standard

---

## 1. Hub & Spoke Operating Model

The `agent-skills` repository functions as a centralized **Intelligence Core (Hub)** decoupled from target test repositories (**Spokes**). 

```mermaid
flowchart TD
    subgraph Hub["Agent-Skills Hub (Intelligence Core)"]
        Catalog["42 Standardized Skills (.agents/skills)"]
        Rules["Core Architectural Rules (.agents/rules)"]
        Tools["Zero-Token Python Engine (tools/)"]
        Swarm["6 Specialized Subagents (.agents/agents)"]
    end

    subgraph Spokes["Target Repositories (Test Suites)"]
        Repo1["Project A (Playwright / TS)"]
        Repo2["Project B (Katalon / Groovy)"]
        Repo3["Project C (Python / Pytest)"]
    end

    Hub -->|Mounted as Skill Provider| Repo1
    Hub -->|Mounted as Skill Provider| Repo2
    Hub -->|Mounted as Skill Provider| Repo3
```

### Architectural Benefits:
1. **Zero Context Contagion:** Target project repositories stay clean and focused strictly on test cases and Page Classes, without polluting git trees with heavy AI agent instructions.
2. **Instant Upgradability:** Improvements to self-healing algorithms, token compressors, and lint rules propagate globally to all target projects instantly.
3. **Intellectual Property Isolation by Architecture:** Because `agent-skills` is a decoupled, standalone repository, target projects remain 100% clean without requiring complex dual-remote mirroring or `smart_push` scripts. Developers and agents push directly to company SCM for target projects, and to the central hub for skills.

---

## 2. Four-Tier Skill Stratification

The 42 skills in the hub are structured into four progressive operational tiers:

```mermaid
flowchart LR
    T1["Tier 1: Core Automation<br/>POM, Live Probing, Repair"] --> T2["Tier 2: Enterprise Quality<br/>WCAG, Visual, Vitals"]
    T2 --> T3["Tier 3: Context & AI Performance<br/>Token Optimization, Graphify"]
    T3 --> T4["Tier 4: Architecture & CI/CD<br/>ADR, Sharding, GitHub Actions"]
```

1. **Tier 1 — Core Automation & Self-Healing:**
   - Script generation, Clean POM flat architecture, live DOM probing via Playwright MCP, and in-place locator healing.
2. **Tier 2 — Enterprise Quality Sentinel:**
   - Accessibility audits (WCAG 2.2), Core Web Vitals profiling, visual regression comparisons, and synthetic data generation.
3. **Tier 3 — AI Context Engineering & Diagnostics:**
   - Attention-pattern protection, context degradation countermeasures, token optimization, and AST knowledge graph navigation.
4. **Tier 4 — Architecture, CI/CD & Delivery:**
   - Architecture Decision Records (ADRs), code refactoring and technical debt remediation, and containerized GitHub Actions CI/CD pipelines.

---

## 3. Flat Clean POM Architecture Pattern

Test automation scripts orchestrated through this Hub enforce strict Clean POM boundaries:

- **Rule 1 — Zero Selectors in Scripts:** Test scripts (`Scripts/` or `tests/`) must NEVER contain raw XPaths, CSS selectors, or `findTestObject` calls.
- **Rule 2 — Single Inheritance:** All Page Classes inherit from `BasePage`, which standardizes smart waits, dynamic identifiers, and synthetic event dispatchers.
- **Rule 3 — Dynamic Test Data Idempotency:** Every data entity must use dynamic prefixes generated via `BasePage.uniqueCode("PREFIX_")` to eliminate database key collisions during parallel execution.
- **Rule 4 — In-Place Self-Healing:** If an element changes or breaks, only the affected Page Class is updated; test scripts remain untouched.

---

## 4. The 9 Quality Gates Definition-of-Done (DoD)

All automated test code authored, modified, or refactored by AI agents must pass through the deterministic 9 Quality Gates pipeline (`tools/verify_all.py`) prior to committing or merging:

| Gate | Title | Verifier Tool | Strict Acceptance Criteria |
| :---: | :--- | :--- | :--- |
| **Gate 0** | **Author Attribution & MIT Provenance** | `author_integrity.py` | Validates immutable MIT license and attribution to original author Thế Vị (@TeeVee998). |
| **Gate 1** | **UTF-8 No BOM Clean Encoding** | `verify_all.py` | Scans 100% of repository files; zero BOM bytes (`0xEF, 0xBB, 0xBF`) and zero mojibake errors. |
| **Gate 2** | **Path Portability** | `verify_all.py` | Rejects workstation-specific absolute paths (`/Users/...`, `C:\...`); mandates root-relative resolution. |
| **Gate 3** | **Clean POM Flat Architecture** | `verify_all.py` | Enforces 100% locator encapsulation in Page Classes; strictly prohibits raw XPaths in test scripts. |
| **Gate 4** | **AI Docs Anti-Drift** | `lint_ai_docs.py` | Reconciles real AST classes against `PROJECT_AI_GUIDE.md`; eliminates hallucinated PageClasses. |
| **Gate 5** | **Temporary File Blacklist** | `verify_all.py` | Ensures zero build debris, memory dumps, or temporary sandbox databases leak into version control. |
| **Gate 6** | **Credential Security** | `verify_all.py` | AST regex scan blocking hardcoded passwords, private keys, and secret tokens in code. |
| **Gate 7** | **Static Defect & Fake-Pass Sentinel** | `infer_linter.py` | Detects 0-assertion tests, swallowed exception blocks (`except: pass`), hard sleeps, and unawaited promises. |
| **Gate 8** | **Assertion Sensitivity Sentinel** | `micro_mutator.py` | Syntactic micro-mutations linked via variable dataflow; requires Sensitivity Score $\ge 80\%$. |

---

## 5. Architectural Boundaries & Non-Goals

To maintain a lightweight, deterministic, and highly portable architecture, Synapse Hub establishes explicit boundaries:
- **No Proprietary Test Runner:** Does not implement a replacement runner engine. Bridges natively with standard runners (Playwright, Pytest, Katalon/Gradle, Newman, JMeter).
- **Zero AUT Source Code Modifications:** Operates exclusively within test specifications, Page Object models, mock definitions, and verification gates.
- **Decoupled Stateless Hub:** Never writes persistent user credentials or proprietary corporate data to git.
- **Target Language Agnostic:** Leverages Universal Intermediate Representation (Universal IR) to bridge TypeScript, Python, Groovy, and Java seamlessly.

The Hub equips 6 specialized subagents with scoped tool and skill permissions:

| Subagent Role | Primary Focus | Allowed Skills | Execution Tools |
| :--- | :--- | :--- | :--- |
| **`orchestrator`** | Task decomposition & governance | `agent-orchestration-multi-agent-optimize`, `graphify-impact-analyzer`, `architecture-decision-records`, `token-and-context-optimizer` | `verify_all.py`, `test_impact.py`, `setup_project.py` |
| **`pom-crafter`** | Clean POM design & test generation | `clean-pom-crafter`, `lam-script-generator`, `synthetic-test-data-generator`, `api-spec-to-e2e-matrix` | `lookup_xpath.py`, `repo_map.py`, `generate_tc_from_story.py` |
| **`live-explorer`** | Live DOM & AOM exploration (<200ms) | `playwright-live-interaction`, `self-healing-locator`, `visual-regression-sentinel`, `api-network-mocking-interception` | `browser_helpers.js`, `e2e_flow_prober.ps1`, `safety_firewall.py` |
| **`test-runner`** | Headless CLI test execution & CI | `katalon-cli-runner`, `e2e-testing-patterns`, `flaky-test-sentinel-and-quarantine`, `backend-load-and-stress-patterns`, `github-actions-templates` | `matrix_sharder.py`, `distill_log.py`, `pinpoint_failure.py`, `flaky_detector.py` |
| **`failure-analyst`**| Visual & XML error autopsy | `failure-autopsy-and-healing`, `self-healing-locator`, `file-and-report-validator` | `auto_heal.py`, `heal_pr_automator.py`, `pinpoint_failure.py`, `cache_resolver.py` |
| **`quality-gatekeeper`**| 9 Gates DoD & Fake-Pass Sentinel | `antigravity-test-sentinel`, `code-refactoring-refactor-clean`, `wcag-audit-patterns`, `web-vitals-and-performance-profiler`, `security-dast-sentinel` | `verify_all.py`, `infer_linter.py`, `micro_mutator.py`, `trace_data_flow.py` |

---

## 6. Nomenclature & Package Architecture

To ensure consistency across various distribution registries and developer interfaces:
- **Ecosystem / Project Name:** Synapse Hub (`Synapse-Hub` on GitHub)
- **NPM Package & Antigravity Plugin:** `synapse-hub` (distributed on NPM Registry and Antigravity Marketplace)
- **Python Package & Universal CLI:** `agent-qa` (PEP 621 package on PyPI providing the `agent-qa` CLI binary)
- **MCP Server Protocol Services:** `enterprise-agent-qa` (Core QA MCP server) and `synapse-mcp-excel` (Excel tool server)
- **Skill Catalog Manifest:** `enterprise-agent-skills-hub` (internal catalog schema identifier in `skills_manifest.json`)
