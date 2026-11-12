# Synapse Hub Architecture & Design Principles

[🇻🇳 Tiếng Việt](ARCHITECTURE.md) | [🇬🇧 English Edition](ARCHITECTURE.en.md)

> **Scope:** Enterprise Multi-Agent QA Hub  
> **Version:** `3.8.3` | **Status:** Active / Production Standard

---

## 1. Hub & Spoke Operating Model

The `Synapse-Hub` repository functions as a centralized **Intelligence Core (Hub)** decoupled from target test repositories (**Spokes**). 

```mermaid
flowchart TD
    subgraph Hub["Synapse Hub (Intelligence Core)"]
        Catalog["53 Standardized Skills (.agents/skills)"]
        Rules["Core Architectural Rules (.agents/rules)"]
        Tools["Zero-Token Python Engine (tools/)"]
        Swarm["9 Specialized Subagents (.agents/agents)"]
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
3. **Intellectual Property Isolation by Architecture:** Because `Synapse-Hub` is a decoupled, standalone repository, target projects remain 100% clean without requiring complex dual-remote mirroring or `smart_push` scripts. Developers and agents push directly to company SCM for target projects, and to the central hub for skills.

---

## 2. Four-Tier Skill Stratification

The 53 skills in the hub are structured into four progressive operational tiers:


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

## 4. The 11 Quality Gates Definition-of-Done (DoD)

All automated test code authored, modified, or refactored by AI agents must pass through the deterministic 11 Quality Gates pipeline (`tools/verify_all.py`) prior to committing or merging:

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
| **Gate 9** | **Tier-2 Skill Routing & Collision Guard** | `skill_collision_guard.py` | Audits skill trigger descriptions and vectors; blocks ambiguous activation with semantic overlap $\ge 0.75$. |
| **Gate 10** | **Performance & SLA Sentinel** | `verify_all.py` / `jtl_analyzer.py` | Enforces SLA limits (P95 $\le$ 500ms, Error Rate $\le$ 1.0%); automatically SKIPPED/PASS when no load tests exist. |

---

## 5. Architectural Boundaries & Non-Goals

To maintain a lightweight, deterministic, and highly portable architecture, Synapse Hub establishes explicit boundaries:
- **No Proprietary Test Runner:** Does not implement a replacement runner engine. Bridges natively with standard runners (Playwright, Pytest, Katalon/Gradle, Newman, JMeter).
- **Zero AUT Source Code Modifications:** Operates exclusively within test specifications, Page Object models, mock definitions, and verification gates.
- **Decoupled Stateless Hub:** Never writes persistent user credentials or proprietary corporate data to git.
- **Target Language Agnostic:** Leverages Universal Intermediate Representation (Universal IR) to bridge TypeScript, Python, Groovy, and Java seamlessly.

The Hub equips 9 specialized subagents with scoped tool and skill permissions:

| Subagent Role | Primary Focus | Allowed Skills | Execution Tools |
| :--- | :--- | :--- | :--- |
| **`orchestrator`** | Task decomposition & governance | `agent-orchestration-multi-agent-optimize`, `graphify-impact-analyzer`, `architecture-decision-records`, `token-and-context-optimizer`, `actor-qa-swarm`, `event-stream-qa-orchestrator`, `qa-memory-os`, `tot-exploratory-testing`, `review-spec` | `verify_all.py`, `test_impact.py`, `setup_project.py`, `interview_story.py`, `dspy_qa_signatures.py`, `autogen_qa_broker.py`, `qa_event_stream.py`, `test_memory_os.py`, `tot_exploratory_tester.py`, `watch_mode.py`, `dashboard_generator.py` |
| **`test-designer`** | Spec audit, risk-based manual test design & Excel export | `rbt-manual-testing`, `review-spec`, `tot-exploratory-testing`, `gherkin-to-suite`, `synthetic-test-data-generator`, `file-and-report-validator` | `template_excel_exporter.py`, `interview_story.py`, `tot_exploratory_tester.py`, `goldfish_review.py`, `gherkin_suite.py`, `mcp_excel_server.py`, `lookup_tc.py` |
| **`pom-crafter`** | Clean POM Web UI design & test generation | `clean-pom-crafter`, `lam-script-generator`, `synthetic-test-data-generator`, `gherkin-to-suite`, `mipro-prompt-compiler`, `qa-aci-interface` | `lookup_xpath.py`, `repo_map.py`, `generate_tc_from_story.py`, `skill_vault.py`, `gherkin_suite.py`, `swe_qa_aci.py`, `mipro_assertion_tuner.py`, `universal_ir.py`, `omni_emitter.py`, `omni_parser.py`, `omni_transpiler.py` |
| **`api-engineer`** | OpenAPI test matrices, CDC contract testing & Newman | `api-spec-to-e2e-matrix`, `consumer-driven-contract-testing`, `api-network-mocking-interception`, `synthetic-test-data-generator`, `security-dast-sentinel` | `generate_api_matrix.py`, `api_drift_sentinel.py`, `newman_analyzer.py`, `network_mock_shield.py`, `export_postman_collection.py`, `traffic_session_converter.py`, `fuzz_payloads.py` |
| **`live-explorer`** | Live DOM & AOM exploration (<200ms) | `playwright-live-interaction`, `self-healing-locator`, `visual-regression-sentinel`, `api-network-mocking-interception` | `browser_helpers.js`, `e2e_flow_prober.py`, `safety_firewall.py` |
| **`test-runner`** | Headless CLI functional test execution & CI | `katalon-cli-runner`, `e2e-testing-patterns`, `flaky-test-sentinel-and-quarantine`, `bats-testing-patterns`, `github-actions-templates` | `matrix_sharder.py`, `distill_log.py`, `pinpoint_failure.py`, `flaky_detector.py`, `reversible_sandbox.py`, `db_sandbox.py`, `generate_allure_report.py`, `generate_test_reports.py` |
| **`perf-engineer`** | Performance, load testing (k6/JMeter/Locust) & APM telemetry profiling | `backend-load-and-stress-patterns`, `web-vitals-and-performance-profiler`, `synthetic-test-data-generator`, `db-state-verifier-and-seeder`, `debug-optimize-lcp`, `memory-leak-debugging` | `generate_jmx_plan.py`, `jtl_analyzer.py`, `telemetry_correlator.py`, `distill_log.py`, `safety_firewall.py`, `reversible_sandbox.py` |
| **`failure-analyst`**| Visual & XML error autopsy | `failure-autopsy-and-healing`, `self-healing-locator`, `file-and-report-validator`, `systematic-debugging`, `agentless-qa-repair` | `auto_heal.py`, `heal_pr_automator.py`, `pinpoint_failure.py`, `cache_resolver.py`, `auto_heal_reflexion.py`, `agentless_patcher.py`, `heuristic_locator_matcher.py`, `telemetry_correlator.py` |
| **`quality-gatekeeper`**| 11 Gates DoD & Fake-Pass Sentinel | `antigravity-test-sentinel`, `code-refactoring-refactor-clean`, `wcag-audit-patterns`, `web-vitals-and-performance-profiler`, `security-dast-sentinel`, `lean-impact-scoreboard`, `web-agent-gym-benchmarking` | `verify_all.py`, `infer_linter.py`, `micro_mutator.py`, `trace_data_flow.py`, `skill_collision_guard.py`, `textgrad_mutation_optimizer.py`, `skillspector.py`, `author_integrity.py`, `browsergym_eval.py` |

### 5.1 Standalone CLI Utilities & Hub Infrastructure Tools (Non-Persona Scoped)

The remaining 7 tools serve as global repository entry points and offline infrastructure services, callable directly without subagent persona routing:
- `cli.py`: Central Agent-QA / Synapse CLI command router and entrypoint (`npx synapse-hub` / `agent-qa`).
- `output_formatter.py`: ANSI terminal color styling, status badges, and table formatting utility.
- `welcome_page.py`: Visual HTML onboarding and landing page generator (`agent-qa welcome`).
- `bump_version.py`: Atomic polyglot semantic version bumper for releases (`agent-qa bump`).
- `sync_agent_rules.py`: Universal AI bridge synchronization engine (Cursor, Claude Code, Copilot, Windsurf).
- `md_to_xlsx.py`: Standalone Markdown to Excel converter utility (`agent-qa md-to-xlsx`).
- `mcp_excel_server.py`: Model Context Protocol (MCP) offline Excel spreadsheet server.

---

## 6. Nomenclature & Package Architecture

To ensure consistency across various distribution registries and developer interfaces:
- **Ecosystem / Project Name:** Synapse Hub (`Synapse-Hub` on GitHub)
- **NPM Package & Antigravity Plugin:** `synapse-hub` (distributed on NPM Registry and Antigravity Marketplace)
- **Python Package & Universal CLI:** `agent-qa` (PEP 621 package on PyPI providing the `agent-qa` CLI binary)
- **MCP Server Protocol Services:** `enterprise-agent-qa` (Core QA MCP server) and `synapse-mcp-excel` (Excel tool server)
- **Skill Catalog Manifest:** `enterprise-agent-skills-hub` (internal catalog schema identifier in `skills_manifest.json`) and `agentskills.json` (AgentSkills v1 open standard)

---

## 7. Autonomous Agent Self-Evolution & Training Subsystems

To elevate AI testing beyond static prompt engineering, Synapse Hub incorporates 6 advanced agent training, compilation, and self-evolution mechanisms synthesized from modern agentic architectures:

```mermaid
flowchart TD
    subgraph SelfEvolution["Autonomous Agent Self-Evolution Subsystem"]
        Vault["<b>Voyager Lifelong Vault</b><br/>(skill_vault.py)<br/>• Verified PageClass SQLite memory<br/>• Zero repetitive prompt re-synthesis"]
        Reflexion["<b>Episodic Reflexion Loop</b><br/>(auto_heal_reflexion.py)<br/>• K=3 trial-feedback learning<br/>• Self-healing without git pollution"]
        DSPy["<b>DSPy Declarative QA Engine</b><br/>(dspy_qa_signatures.py)<br/>• Typed QA signatures<br/>• Eliminates brittle prompt hacking"]
        TextGrad["<b>TextGrad Mutation Loss</b><br/>(textgrad_mutation_optimizer.py)<br/>• AST mutants as loss function<br/>• Optimizes assertions to score &ge; 80%"]
        Reversible["<b>GoEx Reversible Sandbox</b><br/>(reversible_sandbox.py)<br/>• LIFO undo execution stack<br/>• Zero leftover test debris"]
        Bench["<b>Gorilla BFCL Benchmark</b><br/>(synapse_qa_bench.py)<br/>• Evaluates function calling fidelity<br/>• Prevents agent regression"]
    end

    Vault --> DSPy --> TextGrad --> Reversible --> Reflexion --> Bench
```

1. **Lifelong Skill Memory (`skill_vault.py`):** Inspired by Voyager, stores verified POM methods and complex interaction patterns in permanent SQLite memory, growing the agent's capability with every run.
2. **Episodic Trial-Feedback (`auto_heal_reflexion.py`):** Implements Noah Shinn's Reflexion framework, enabling agents to evaluate test failure traces across $K=3$ iterations, generating textual self-reflection to correct locator strategies.
3. **Declarative Signature Compilation (`dspy_qa_signatures.py`):** Adheres to Stanford DSPy principles, compiling prompt templates into structured, typed input-output signatures.
4. **Mutant-Directed Loss Optimization (`textgrad_mutation_optimizer.py`):** Treats surviving AST mutants as a loss function (TextGrad), iteratively refining assertion logic until all mutants are killed.
5. **Reversible Execution Teardown (`reversible_sandbox.py`):** Implements GoEx-style reversible rollback stacks for filesystem and database mutations during automated exploratory runs.
6. **Tool Function Calling Benchmark (`synapse_qa_bench.py`):** Implements Berkeley Function-Calling Leaderboard (BFCL) standards for enterprise QA tools, benchmarking tool selection precision and multi-turn execution accuracy.

---

## 8. Comparative Analysis & Industry Positioning

| Evaluation Criteria / Solution | ESLint Plugin (Playwright) | Stryker Mutator | Allure Report | Healenium | Synapse Hub 🧠 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Language & Framework Scope** | Only JS / TS | JS / TS, C#, Scala | Any language (XML ingest) | Java / Python / C# (Selenium) | **Polyglot** (TS/JS, Python, Groovy, Java) |
| **Deep Agent Context Integration** | ❌ (CLI/IDE lint only) | ❌ (Standalone tool) | ❌ (Post-test visualizer) | ❌ (JVM proxy server) | ✅ **Native** (Rules, MCP, AST Map, 9 Subagents) |
| **AI Fake-Pass Elimination** | ⚠️ Syntax lint only | ❌ (App code mutations only) | ❌ | ❌ | ✅ **Specialized** (0-assert detection, swallowed exceptions, tautology) |
| **Mutation Testing Speed** | N/A | ⏱️ Minutes to hours | N/A | N/A | ⚡ **Ultra-fast (~0.1s)** static heuristic assertion sensitivity scan |
| **Locator Self-Healing** | ❌ | ❌ | ❌ | ⚠️ Requires JVM server + Docker | ⚡ **Lightweight (< 500 tokens)** AOM diffing inside agent loop |
| **Token & Log Distillation** | ❌ | ❌ | ❌ | ❌ | ✅ **Reduces 95%** log noise (`distill_log.py`, `repo_map.py`) |
| **Clean POM Architectural Guard** | ❌ | ❌ | ❌ | ❌ | ✅ **Strict enforcement**, Clean POM Flat Architecture |

---

## 9. Known Technical Limitations & Empirical Benchmarks

To maintain strict engineering rigor (**Truth Anchor**), Synapse Hub discloses all known technical boundaries:

1. **Static Heuristic Mutation Testing vs Runtime Mutation Testing:**  
   `tools/micro_mutator.py` in static mode performs fast heuristic assertion reachability analysis (~0.1s) to detect unasserted branches and weak assertions. This is a lexical reachability and dataflow heuristic, **not** a compiler-grade runtime mutation testing engine (such as Stryker or mutmut). To avoid inflated assertion scores and obtain ground-truth mutation kill rates, execute in Dynamic mode (`--test-cmd`) against real test runners.
2. **Empirical Benchmarks (Self-Reported Baseline):**  
   The metrics (25/25 challenges resolved, 76.2 tokens/bug) reflect author-measured internal baselines on curated challenges (`benchmarks/qa_eval`) rather than independent third-party double-blind audits. Metrics may vary on real-world enterprise suites depending on architectural complexity and test coverage.
3. **Hub-Spoke Version Pinning (Blast-Radius Isolation):**  
   When mounting or referencing Synapse Hub in downstream Spoke projects, downstream repositories should pin a specific Git Submodule commit or release tag (`git checkout v3.0.0`) rather than tracking unpinned `main` HEAD, preventing upstream Hub changes from unexpectedly breaking downstream CI/CD pipelines.
4. **Supported Runners:**  
   First-class runner adapters for **Playwright, Pytest, Katalon Studio/Groovy, and Cypress**. Selenium WebDriver is supported via Clean POM architecture patterns, smart-wait primitives, and Universal IR transpilation.
5. **Environment Prerequisites:**  
   - Node.js >= 18.0.0 (Node.js 20 or 22 LTS recommended).
   - Python >= 3.10 (fully tested on 3.10, 3.11, 3.12, 3.13, 3.15).
   - Headless browser: Playwright Chromium required for live DOM/AOM probing and self-healing locators.
