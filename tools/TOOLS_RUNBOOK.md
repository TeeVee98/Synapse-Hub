# TOOLS RUNBOOK — Automated Tools Handbook for AI Agents

> **Standard reference guide for AI Agents (Google Antigravity, Cursor, Claude Code, Windsurf)**  
> Every script in the `tools/` directory has an explicit purpose, CLI syntax, and mandatory dispatch trigger. Guessing syntax is strictly prohibited.

---

## 1. SITUATIONAL TOOL DISPATCH MATRIX

| Practical Agent Context | Required Tool | Typical Execution Command |
| :--- | :--- | :--- |
| **Autonomous Bootstrap (New project / "setup project")** | `tools/setup_project.py` | `python tools/setup_project.py [target]` (or `agent-qa setup`).<br/>*Autonomous:* Detects stack, generates `PROJECT_AI_GUIDE.md`, installs `pre-push` Git hook, runs initial audit. |
| **Prerequisites & Environment Health Diagnostic ("doctor")** | `tools/check_env.py` | `agent-qa doctor` (or `npx synapse-hub doctor`) |
| **Visual Product Landing Page & Interactive Guide ("welcome")** | `tools/welcome_page.py` | `agent-qa welcome` (or `npx synapse-hub welcome`) |
| **Flaky Test Detection & Quarantine Governance ("flaky")** | `tools/flaky_detector.py` | `agent-qa flaky --detect` (or `npx synapse-hub flaky`) |
| **Executive Project Health & Quality Dashboard ("dashboard")** | `tools/dashboard_generator.py` | `agent-qa dashboard` (or `npx synapse-hub dashboard`) |
| **Clean Uninstall of AI Bridges & Global Plugins ("uninstall")** | `tools/cli.py` | `agent-qa uninstall` (or `npx synapse-hub uninstall`) |
| **Comprehensive Health & AST Analysis ("analyze project")** | `tools/analyze_project.py` | `python tools/analyze_project.py [target]` (or `agent-qa analyze`).<br/>*Post-Audit:* Stages and commits `PROJECT_HEALTH_REPORT.md` & `repo_map.txt` locally; confirms with user before pushing to remote. |
| **Action Safety Firewall (Environment Protection)** | `tools/safety_firewall.py` | `python tools/safety_firewall.py --text "Delete" --action click` (or `agent-qa safety-check`) |
| **API Contract Drift (Breaking Change Detection)** | `tools/api_drift_sentinel.py` | `python tools/api_drift_sentinel.py --old base.json --new curr.json` (or `agent-qa contract-drift`) |
| **Autonomous API Fuzzing & Chaos Breaker** | `tools/api_fuzzer.py` | `agent-qa fuzz-api --base-url <url> --spec <swagger.json>` (Catches 500, DB leaks, SLA breach) |
| **FastMCP JSON-RPC Server (Cursor/Claude/Antigravity)** | `tools/mcp_server.py` | `python tools/mcp_server.py` (or `agent-qa mcp-serve`) |
| **Syntactic Micro-Mutation (Assertion Quality Verification)** | `tools/micro_mutator.py` | `python tools/micro_mutator.py [target]` (or `agent-qa mutate`) |
| **Gherkin BDD Suite Compiler (Natural-Language Ingestion, 0-token)** | `tools/gherkin_suite.py` | `python tools/gherkin_suite.py tests/bdd/` (or `agent-qa gherkin`; `--emit-ir` for Universal IR) |
| **Self-Healing PR Automator (Trace & Visual Diff Proof)** | `tools/heal_pr_automator.py` | `python tools/heal_pr_automator.py --page P.groovy --old "//a" --new "//b" --trace-zip trace.zip` (or `agent-qa heal-pr`) |
| **Duration-Balanced Matrix Sharder (CI/CD Load Balancing)** | `tools/matrix_sharder.py` | `python tools/matrix_sharder.py [target] --shards 4` (or `agent-qa shard`) |
| **Enterprise ALM & TMS Sync Bridge (Jira/Xray/TestRail)** | `tools/tms_sync_bridge.py` | `python tools/tms_sync_bridge.py pull PROJ-1042` / `report-bug` |
| **Zero-Pollution DB Sandbox (Ephemeral Teardown)** | `tools/db_sandbox.py` | `python tools/db_sandbox.py snapshot` / `restore` / `rollback-test` |
| **Shift-Right Traffic Replay (HAR / RUM to Test)** | `tools/traffic_session_converter.py` | `python tools/traffic_session_converter.py session.har -o test.ts` |
| **Multimodal Vision Grounding & Zero-Token Cache (SoM)** | `tools/visual_som_helper.py` | `python tools/visual_som_helper.py --image shot.png --component "Submit" --cache-lookup` |
| **Edge-Case Fuzzing & Input Sanitization Suite** | `tools/fuzz_payloads.py` | `python tools/fuzz_payloads.py --field username --type string` |
| **Starting task / Querying Page Class methods** | `tools/repo_map.py` | `python tools/repo_map.py` (Reads `tools/repo_map.txt`) |
| **Pre-Commit / Completing Task** | `tools/verify_all.py` | `python tools/verify_all.py` |
| **After creating/editing Test Script (Fake-Pass scan)**| `tools/infer_linter.py` | `python tools/infer_linter.py` |
| **After modifying Page Class (Impact Analysis)** | `tools/test_impact.py` | `python tools/test_impact.py --git-diff` |
| **When Test FAILS (Pinpoint line & error in 0.1s)** | `tools/pinpoint_failure.py` | `python tools/pinpoint_failure.py <report.xml>` (or `agent-qa pinpoint-failure report.xml`) |
| **When CLI/Gradle logs are verbose (Observation Masking)**| `tools/distill_log.py` | `python tools/distill_log.py <path_to_log>` |
| **When encountering UI error / Overlay / Stale Element**| `tools/cache_resolver.py` | `python tools/cache_resolver.py query "<error_msg>"` |
| **Before authoring test for Page/Flow** | `tools/cache_resolver.py` | `python tools/cache_resolver.py get-lessons --context "<page>"` (or `agent-qa heal get-lessons --context "<page>"`) |
| **After healing a test failure** | `tools/cache_resolver.py` | `python tools/cache_resolver.py record-lesson --context "<page>" --error "<sig>" --lesson "<summary>"` |
| **Generating test scripts from Natural Language Story** | `tools/generate_tc_from_story.py`| `python tools/generate_tc_from_story.py "<story>"` (or `agent-qa generate-tc story.md`) |
| **Generating E2E matrix from OpenAPI/Swagger** | `tools/generate_api_matrix.py` | `python tools/generate_api_matrix.py --spec <swagger.json>` |
| **Exporting API tests to Postman Collection v2.1** | `tools/export_postman_collection.py` | `agent-qa export-postman --spec <swagger.json> -o col.json` |
| **Analyzing Newman Results & CI/CD Gatekeeper** | `tools/newman_analyzer.py` | `agent-qa analyze-newman report.json --max-failures 0` |
| **Generating JMeter Performance Test Plan (.jmx)** | `tools/generate_jmx_plan.py` | `agent-qa generate-jmx --spec <swagger.json> --vus 100 -o plan.jmx` |
| **Analyzing JMeter JTL & Enforcing CI/CD SLA Gate** | `tools/jtl_analyzer.py` | `agent-qa analyze-jtl results.jtl --sla-p95 500 --max-error-rate 1.0` |
| **Full-Stack APM & Server Telemetry RCA Correlator** | `tools/telemetry_correlator.py` | `agent-qa correlate-telemetry --jtl results.jtl --server-metrics srv.csv` |
| **Auditing Web Accessibility (WCAG 2.2)** | `tools/wcag_audit.py` | `python tools/wcag_audit.py <path_to_html_or_url>` (or `agent-qa wcag-audit`) |
| **0-Token Polyglot Test Transpilation** | `tools/omni_transpiler.py` | `agent-qa transpile <file> --to <target>` (Playwright TS, Python, Java, Katalon, Cypress) |
| **0-Token Repository Polyglot AST Scan** | `tools/omni_transpiler.py` | `agent-qa omni-scan [path]` (Instant inventory of Pages, Locators, Tests across languages) |
| **Sync Single-Source Agent Rules ("sync-rules")** | `tools/sync_agent_rules.py` | `agent-qa sync-rules` (or `python tools/sync_agent_rules.py --check`) |
| **Lookup Test Case Identifier Index ("lookup-tc")** | `tools/lookup_tc.py` | `agent-qa lookup-tc [query]` (or `python tools/lookup_tc.py [query]`) |
| **Lookup Cached Element XPaths / AOM ("lookup-xpath")** | `tools/lookup_xpath.py` | `agent-qa lookup-xpath [query]` (or `python tools/lookup_xpath.py [query]`) |
| **Trace Data Flow & Teardown Verification ("trace-data-flow")** | `tools/trace_data_flow.py` | `agent-qa trace-data-flow ./tests` (or `python tools/trace_data_flow.py`) |
| **Autonomous Legacy Suite Migration** | `tools/cli.py` | `agent-qa migrate --src ./katalon_project --dest ./playwright_ts` |
| **Environment & Secret Decoupling Engine** | `tools/config_decoupler.py` | `agent-qa decouple-config [target] --fix` (Extracts env.default.json & .env.example) |
| **Single Portable Binary Distribution** | `scripts/package_dist.py` | `python scripts/package_dist.py --binary` (Builds standalone omni-qc.exe) |
| **Autonomous Bug Report & Jira/Allure Ticket** | `tools/bug_reporter.py` | `agent-qa report-bug --title "<title>" --error "<msg>"` |
| **API Network Mocking & Chaos Shield** | `tools/network_mock_shield.py` | `agent-qa mock-shield --preset payment_success` |
| **Smart Visual Masking (Anti-Flake)** | `tools/smart_visual_masker.py` | `agent-qa visual-mask --playwright-snippet` |
| **CI/CD Silent Self-Healing Hook & Auto-PR** | `tools/ci_healing_hook.py` | `agent-qa ci-hook --file <f> --old-loc <old> --new-loc <new>` |
| **Checking DB data leaks (Taint Analysis)** | `tools/trace_data_flow.py` | `python tools/trace_data_flow.py` |
| **Detecting Canvas / GIS Map visual regression** | `tools/visual_diff_canvas.py` | `python tools/visual_diff_canvas.py compare <b> <a> --diff <d>` (or `agent-qa canvas-diff`) |
| **Universal Release Version Synchronization Audit** | `tools/check_version_sync.py` | `python tools/check_version_sync.py` (or `agent-qa check-version`) |
| **Groovy Scripts & Keywords Syntax Pre-check** | `tools/validate_groovy_scripts.py` | `python tools/validate_groovy_scripts.py` (or `agent-qa validate-groovy`) |
| **Cognitive Observer & Tradeoff Sentinel** | `tools/synapse_observer.py` | `python tools/synapse_observer.py [--diff \| --text <txt>]` (Anthropic Observer pattern) |
| **Anti-AI Slop & Human-Centric Writing Linter** | `tools/humanize_linter.py` | `python tools/humanize_linter.py [--file <f> \| --text <txt>]` (Scans buzzwords & cliches) |
| **Mathematical Security Coverage Ledger** | `tools/security_coverage_ledger.py` | `python tools/security_coverage_ledger.py [init\|add\|validate\|summary]` (Cloudflare pattern) |
| **Model Context Protocol (MCP) Excel Server** | `tools/mcp_excel_server.py` | `python tools/mcp_excel_server.py` (or `agent-qa mcp-excel`) |
| **3-Layer Heuristic Locator Matcher (0-Token Recovery)** | `tools/heuristic_locator_matcher.py` | `python tools/heuristic_locator_matcher.py` (Internal autonomous fallback engine) |
| **Output Formatter & Exit Code Spec (NO_COLOR standard)** | `tools/output_formatter.py` | `from output_formatter import is_color_enabled, EXIT_SUCCESS` |
| **Canary Self-Healing Audit** | `tools/agent_canary.py` | `python tools/agent_canary.py --run` |
| **Lookup XPath Locator in cached memory** | `tools/lookup_xpath.py` | `python tools/lookup_xpath.py "<keyword>"` |
| **Lookup Test Case metadata** | `tools/lookup_tc.py` | `python tools/lookup_tc.py "<keyword_or_id>"` |
| **Linting Markdown documentation quality** | `tools/lint_ai_docs.py` | `python tools/lint_ai_docs.py` |
| **Auditing AI Agent Skills & MCP Security** | `tools/skillspector.py` | `python tools/skillspector.py [path]` (or `agent-qa skillspector [path]` / `npx synapse-hub skillspector`) |
| **Author Provenance & Anti-Tamper Integrity Guard** | `tools/author_integrity.py` | `python tools/author_integrity.py` (or `agent-qa verify-author` / `verify_all pre-flight`) |
| **Cross-Platform Token & Cost Auditor (Antigravity / Cursor / Claude)** | `tools/count_tokens.py` | `python tools/count_tokens.py` (or `--platform cursor` / `--platform all --list` / `--file <path>`) |
| **Standalone Executive HTML Dashboard Generator** | `tools/dashboard_generator.py` | `python tools/dashboard_generator.py` (or `agent-qa dashboard [--open]`) |
| **Real-Time Incremental Watch Mode Sentinel** | `tools/watch_mode.py` | `python tools/watch_mode.py` (or `agent-qa watch [--once]`) |
| **Technical Debt & Shortcut Harvester ("debt")** | `tools/debt_harvester.py` | `agent-qa debt [path]` (or `python tools/debt_harvester.py --scan`).<br/>*Autonomous:* Scans `shortcut:` markers across repo, generates tracked markdown ledger. |
| **6-Pillar Senior Git Diff Reviewer ("review")** | `tools/senior_code_review.py` | `agent-qa review [--staged]` (or `python tools/senior_code_review.py`).<br/>*Autonomous:* Reviews diff across Bugs, Security, Concurrency, Missing Tests, Speed, Bloat. |
| **Upstream Version Check & 1-Click Self-Update** | `tools/update_sentinel.py` | `python tools/update_sentinel.py --check / --update` (or `agent-qa update` / `npx synapse-hub update`) |
| **Tier-2 Skill Routing & Collision Guard (Gate 9)** | `tools/skill_collision_guard.py` | `python tools/skill_collision_guard.py` (or `verify_all Gate 9` / `--route "<intent>"`) |
| **GoEx Reversible Sandbox Teardown Stack** | `tools/reversible_sandbox.py` | `python tools/reversible_sandbox.py run --cmd "<cmd>" --rollback "<cleanup>"` |
| **Multi-Trial Episodic Reflexion Loop (K=3)** | `tools/auto_heal_reflexion.py` | `python tools/auto_heal_reflexion.py --test-cmd "<cmd>" --max-trials 3` |
| **Voyager Lifelong Page Class SQLite Vault** | `tools/skill_vault.py` | `python tools/skill_vault.py query "<keyword>"` / `stats` / `store` |
| **Stanford DSPy Declarative QA Signatures** | `tools/dspy_qa_signatures.py` | `python tools/dspy_qa_signatures.py compile-suite --spec <file>` |
| **Pocock Grilling Primitive & Requirement Interrogation** | `tools/interview_story.py` | `python tools/interview_story.py analyze <story.md>` / `interactive` |
| **Mutant-Directed Textual Loss Optimizer (TextGrad)** | `tools/textgrad_mutation_optimizer.py` | `python tools/textgrad_mutation_optimizer.py optimize --test-file <path>` |
| **Tool Function Calling Benchmark (Gorilla BFCL)** | `tools/synapse_qa_bench.py` | `python tools/synapse_qa_bench.py benchmark --top-k 5` |
| **Shared OpenAPI & Swagger Specification Parser** | `tools/_openapi_parser.py` | `python tools/_openapi_parser.py <spec>` |
| **Agentless 3-Stage Deterministic Patcher** | `tools/agentless_patcher.py` | `python tools/agentless_patcher.py --file <f> --error "<msg>"` |
| **Closed-Loop Locator Self-Healing Engine** | `tools/auto_heal.py` | `python tools/auto_heal.py --file <f> --broken "<loc>"` (or `agent-qa heal`) |
| **Asynchronous Actor QA Message Broker** | `tools/autogen_qa_broker.py` | `python tools/autogen_qa_broker.py --topic <t> --payload <data>` |
| **Swarm Context Token Benchmark Harness** | `tools/benchmark_swarm_context.py` | `python tools/benchmark_swarm_context.py --iterations 10` |
| **BrowserGym Web Agent Benchmark Harness** | `tools/browsergym_eval.py` | `python tools/browsergym_eval.py --task "<t>"` |
| **Atomic Universal Version Bumper** | `tools/bump_version.py` | `python tools/bump_version.py <patch\|minor\|major>` |
| **Swarm Data Contract Validator** | `tools/contract_validator.py` | `python tools/contract_validator.py --contract <c.json>` |
| **Enterprise E2E Flow Prober & Crawler** | `tools/e2e_flow_prober.py` | `python tools/e2e_flow_prober.py --url <url>` |
| **5-Stage QA Multi-Agent FSM Enforcer** | `tools/fsm_enforcer.py` | `python tools/fsm_enforcer.py transition <stage>` |
| **Runtime FSM Interceptor & Tool Proxy** | `tools/fsm_middleware.py` | `python tools/fsm_middleware.py --check-tool <tool>` |
| **Enterprise Allure HTML Report Generator** | `tools/generate_allure_report.py` | `python tools/generate_allure_report.py --results ./allure-results` |
| **SPDX 2.3 Software Bill of Materials (SBOM)** | `tools/generate_sbom.py` | `python tools/generate_sbom.py -o Reports/sbom.json` |
| **Enterprise Test Report Aggregator** | `tools/generate_test_reports.py` | `python tools/generate_test_reports.py --reports-dir ./Reports` |
| **Enterprise Tooling Ecosystem Catalog Generator** | `tools/generate_tool_catalog.py` | `python tools/generate_tool_catalog.py --output tools/TOOL_CATALOG.json` |
| **Enterprise Git Pre-Commit Architecture Guard** | `tools/git_pre_commit_guard.py` | `python tools/git_pre_commit_guard.py [--staged]` |
| **Zero-Context Test Specification Reviewer** | `tools/goldfish_review.py` | `python tools/goldfish_review.py <spec.md>` |
| **Autonomous 1-Click 5-Step Hub Release** | `tools/hub_publisher.py` | `python tools/hub_publisher.py` |
| **Project Configuration Bootstrapper** | `tools/init_config.py` | `python tools/init_config.py [--target-dir .]` |
| **Jira / Xray / Zephyr Enterprise 2-Way Sync** | `tools/jira_sync.py` | `python tools/jira_sync.py pull <id>` / `push-results` |
| **FastMCP Word .docx Document Server** | `tools/mcp_docx_server.py` | `python tools/mcp_docx_server.py` (or `agent-qa mcp-docx`) |
| **MIPROv2 Bayesian Assertion Tuner** | `tools/mipro_assertion_tuner.py` | `python tools/mipro_assertion_tuner.py --trials 20` |
| **Universal Polyglot Clean POM Code Emitter** | `tools/omni_emitter.py` | `python tools/omni_emitter.py --ir suite.json --lang typescript` |
| **Deterministic Polyglot AST Parser** | `tools/omni_parser.py` | `python tools/omni_parser.py --src ./tests --emit-ir suite.json` |
| **OpenXML Security & Protocol Defense Guard** | `tools/openxml_guard.py` | `python tools/openxml_guard.py audit <file.xlsx>` |
| **Enterprise Release Packager & Checksum Guard** | `tools/package_release.py` | `python tools/package_release.py --version <ver>` |
| **Enterprise Project State Machine & Memory Anchor** | `tools/project_state.py` | `python tools/project_state.py get` / `set` |
| **Immutable QA Event Stream Engine** | `tools/qa_event_stream.py` | `python tools/qa_event_stream.py record` / `verify-chain` |
| **Enterprise Security Sentinel & Scanner** | `tools/security_scanner.py` | `python tools/security_scanner.py [--strict]` |
| **Spec-to-Code Drift Sentinel** | `tools/spec_drift_sentinel.py` | `python tools/spec_drift_sentinel.py --spec <api.json>` |
| **QA Agent-Computer Interface (SWE-agent)** | `tools/swe_qa_aci.py` | `python tools/swe_qa_aci.py view` / `edit` |
| **Template-Driven Excel Test Case Exporter** | `tools/template_excel_exporter.py` | `python tools/template_excel_exporter.py <cases.md> -o <out.xlsx>` |
| **Enterprise Markdown-to-Excel Test Case Exporter** | `tools/md_to_xlsx.py` | `python tools/md_to_xlsx.py <input.md> [output.xlsx]` (or `agent-qa md-to-xlsx`) |
| **Hierarchical QA Test Memory OS (MemGPT)** | `tools/test_memory_os.py` | `python tools/test_memory_os.py core-get` / `recall-search` |
| **Tree-of-Thoughts Exploratory Testing Engine** | `tools/tot_exploratory_tester.py` | `python tools/tot_exploratory_tester.py --story <story.md>` |
| **Historical Quality Trend & Flakiness Analytics** | `tools/trend_analytics.py` | `python tools/trend_analytics.py --history ./Reports/history` |
| **Interactive QA Mission Control UI Server** | `tools/ui_server.py` | `python tools/ui_server.py` (or `agent-qa ui`) |
| **Universal Intermediate Representation AST Model** | `tools/universal_ir.py` | `python tools/universal_ir.py validate suite.json` |

---

## 2. DETAILED TOOL USAGE

### 0. `tools/update_sentinel.py` (Upstream Update & Drift Sentinel)
Checks upstream releases on NPM Registry and GitHub, displaying non-blocking update notifications when a new version is published. Supports 1-click self-updating across local git repos and global plugins.

```bash
# Check if update is available without applying
python tools/update_sentinel.py --check
# or via CLI
agent-qa update --check

# Perform 1-click self-update (pulls git, syncs memory cache, verifies DoD)
python tools/update_sentinel.py --update
# or via CLI
agent-qa update
```

### 1. `tools/generate_api_matrix.py`
- **Purpose:** Ingests OpenAPI / Swagger JSON schemas and automatically computes comprehensive E2E test matrices: Positive, Boundary Value (min/max length, special characters, XSS payloads), and Negative (invalid types, missing required fields).
- **CLI Syntax:**
  ```bash
  # Generate Markdown matrix
  python tools/generate_api_matrix.py --spec path/to/swagger.json --format md -o api_matrix.md

  # Generate JSON matrix
  python tools/generate_api_matrix.py --spec path/to/swagger.json --format json -o api_matrix.json

  # Generate sample matrix using built-in schema
  python tools/generate_api_matrix.py --sample
  ```

---

### 2. `tools/wcag_audit.py`
- **Purpose:** Automated Web Accessibility auditor checking WCAG 2.2 Level A and AA criteria (missing alt tags, unlabeled form controls, table header structure, heading hierarchy gaps H1-H6, empty action buttons).
- **CLI Syntax:**
  ```bash
  # Audit local HTML snapshot
  python tools/wcag_audit.py path/to/page.html -o wcag_report.md

  # Audit live URL directly
  python tools/wcag_audit.py https://staging.example.com/dashboard --url -o wcag_report.md
  ```

---

### 3. `tools/verify_all.py`
- **Purpose:** Supreme Definition of Done (DoD) verification gate running all 10 Quality Gates (including Syntactic Micro-Mutation >= 80% and SLA Sentinel) prior to completing tasks or git commits. Supports dual operational modes (`hub` vs `target`) and dynamic target project resolution.
- **CLI Syntax:**
  ```bash
  # Auto-detection (automatically targets CWD if inside a test project, otherwise falls back to QA Hub)
  python tools/verify_all.py

  # Target a specific test project repository (positional or --repo / --path)
  python tools/verify_all.py "D:/katalon-project"
  python tools/verify_all.py --repo "D:/katalon-project"

  # Explicit mode execution
  python tools/verify_all.py --mode hub      # QA Hub integrity validation
  python tools/verify_all.py --mode target   # Enterprise target test suite validation
  ```

---

### 4. `tools/infer_linter.py`
- **Purpose:** AST static code analyzer detecting Fake-Pass anti-patterns (test cases without assertions or containing empty try-catch blocks swallowing errors).
- **CLI Syntax:**
  ```bash
  python tools/infer_linter.py
  ```

---

### 5. `tools/test_impact.py`
- **Purpose:** Analyzes `git diff` against codebase dependency graphs to identify the exact subset of affected test cases, preventing redundant suite execution.
- **CLI Syntax:**
  ```bash
  python tools/test_impact.py --git-diff
  ```

---

### 6. `tools/pinpoint_failure.py`
- **Purpose:** Extracts failing line numbers, exception names, and stack traces from JUnit XML reports in 0.1s without opening heavy files.
- **CLI Syntax:**
  ```bash
  python tools/pinpoint_failure.py
  ```

---

### 7. `tools/distill_log.py`
- **Purpose:** Distills verbose CLI / KRE / Gradle logs by 95%, extracting only actionable exceptions, failing lines, and file pointers to prevent token degradation.
- **CLI Syntax:**
  ```bash
  python tools/distill_log.py path/to/execution.log
  ```

---

### 8. `tools/cache_resolver.py`
- **Purpose:** Queries SQLite error cache (`tools/memory_cache.db`) via cosine similarity or pattern match for 0-token instant defect resolution.
- **CLI Syntax:**
  ```bash
  python tools/cache_resolver.py query "ElementClickInterceptedException"
  python tools/cache_resolver.py add --pattern "Timeout waiting for primeNG" --fix "BasePage.waitForAngular()"
  ```

---

### 9. `tools/generate_tc_from_story.py`
- **Purpose:** Large Action Model (LAM) parser converting natural language acceptance criteria into Clean POM script scaffolds.
- **CLI Syntax:**
  ```bash
  python tools/generate_tc_from_story.py "User navigates to login, inputs valid credentials, and verifies dashboard table loaded"
  ```

---

### 10. `tools/visual_diff_canvas.py`
- **Purpose:** Pixel-level and SSIM perceptual comparison for GIS / Canvas elements lacking standard DOM locators.
- **CLI Syntax:**
  ```bash
  python tools/visual_diff_canvas.py --baseline baseline.png --actual actual.png --diff diff.png
  ```

---

### 11. `tools/analyze_project.py`
- **Purpose:** Comprehensive 5-in-1 Project Health & AST Intelligence Suite. Aggregates environment checks (`check_env`), Page Class AST mapping (`repo_map`), Static Defect Sentinel (`infer_linter`), Teardown Data Flow (`trace_data_flow`), and 10 Quality Gates (`verify_all`). Generates `reports/PROJECT_HEALTH_REPORT.md` and synchronizes all AI data context in < 1 second.
- **Trigger:** Whenever user says: "analyze project", "re-analyze project", "audit project", or during initial project onboarding.
- **CLI Syntax:**
  ```bash
  # Analyze current working directory or QA Hub
  python tools/analyze_project.py
  # Or use CLI shortcut
  agent-qa analyze

  # Analyze specific target project
  python tools/analyze_project.py "D:/katalon-project"
  python tools/analyze_project.py --repo "D:/katalon-project"
  ```


---

### 12. `tools/tms_sync_bridge.py`
- **Purpose:** Bi-directional Enterprise ALM Bridge connecting autonomous agents with Jira REST API v3 (live mode) and TestRail/Xray (mock simulation mode). Pulls Given-When-Then Acceptance Criteria from User Stories to seed tests, and automatically creates Bug Tickets with complete reproduction steps and screenshot attachments upon test failure.
- **CLI Syntax:**
  ```bash
  # Pull Acceptance Criteria from Jira Story
  python tools/tms_sync_bridge.py pull PROJ-1042

  # Create Bug Ticket with repro steps and failure screenshots (Jira live, or Mock preview)
  python tools/tms_sync_bridge.py report-bug --project BILLING --tc-id TC-01 --summary "Payment failed" --error "Timeout" --screenshot "Screenshots/FAILED_TC-01.png"

  # Sync execution batch (mock simulation / live Jira)
  python tools/tms_sync_bridge.py sync-run --plan-key XRAY-PLAN-1 --json
  ```

---

### 13. `tools/db_sandbox.py`
- **Purpose:** Zero-Pollution Database Sandbox and Ephemeral Teardown Engine. Takes pristine database baseline snapshots, instantly restores clean states (< 0.1s), runs tests inside transactional savepoints (automatic rollback), and safely audits/purges orphan test data junk with literal prefix matching (escaped SQL wildcards) and dry-run preview.
- **CLI Syntax:**
  ```bash
  # Snapshot database before suite execution
  python tools/db_sandbox.py snapshot --id baseline

  # Restore pristine clean database after suite execution
  python tools/db_sandbox.py restore --id baseline

  # Preview orphan test junk without deleting (Dry-Run)
  python tools/db_sandbox.py audit --dry-run

  # Purge orphan test records matching literal prefixes (AUTO_, TEST_, TEMP_)
  python tools/db_sandbox.py audit
  ```
  python tools/db_sandbox.py rollback-test

  # Audit database for orphan test junk and purge
  python tools/db_sandbox.py audit
  ```


---

### 14. `tools/traffic_session_converter.py`
- **Purpose:** Shift-Right production traffic and user session converter. Converts recorded `.har` files or RUM network traces into executable Playwright test scripts, automatically sanitizing PII (passwords, tokens, credit cards) and eliminating static noise.
- **CLI Syntax:**
  ```bash
  # Convert HAR file into Playwright test script
  python tools/traffic_session_converter.py prod_session.har -o tests/e2e_replay.spec.ts

  # Output parsed network requests as JSON
  python tools/traffic_session_converter.py prod_session.har --json
  ```

---

### 15. `tools/visual_som_helper.py`
- **Purpose:** Multimodal Vision Grounding and Set-of-Marks (SoM) fallback engine. When standard DOM locators fail on HTML5 Canvas, GIS maps, WebGL charts, or deeply nested Shadow DOM, it autonomously detects interactive visual contours using PIL edge clustering, overlays numbered bounding box badges on screenshots, resolves target coordinates `(x, y)`, caches coordinates via 64-bit dHash in SQLite, and dispatches physical Playwright mouse clicks (`await page.mouse.click(x, y)`).
- **CLI Syntax:**
  ```bash
  # Autonomous Canvas contour detection without DOM
  python tools/visual_som_helper.py --image canvas_map.png --detect-only

  # Generate Set-of-Marks overlay and resolve target coordinates
  python tools/visual_som_helper.py --image screenshot.png --label "Execute Trade"

  # Zero-Token Visual Cache lookup (Similarity > 98%)
  python tools/visual_som_helper.py --image screenshot.png --component "TradeButton" --cache-lookup
  ```

---

### 16. `tools/api_fuzzer.py`
- **Purpose:** Autonomous runtime API fuzzer and chaos breaker. Ingests OpenAPI 3.x / Swagger 2.0 schemas, generates dynamic boundary, type-inverted, and adversarial fuzzing payloads from `tools/fuzz_payloads.py`, executes live HTTP/S requests against staging/test APIs, and evaluates three-alarm defect Oracle: HTTP 500 crashes, database stacktrace leaks, and SLA latency timeouts (> 3000ms).
- **CLI Syntax:**
  ```bash
  # Execute active fuzzing against staging API
  agent-qa fuzz-api --base-url "https://staging.api.enterprise.com" --spec swagger.json --token "JWT_SECRET"

  # Air-gapped / deterministic dry-run mode for CI/CD
  agent-qa fuzz-api --dry-run
  ```

---

### 17. `tools/omni_transpiler.py`
- **Purpose:** Universal Polyglot AST Engine & Cross-Framework Transpiler. Allows a single QA engineer to parse, inventory, and transpile test automation code across Java (Selenium), TypeScript (Playwright), Python, Groovy (Katalon Clean POM), and Cypress in 0 tokens without network calls or LLM hallucinations.
- **CLI Syntax:**
  ```bash
  # Transpile legacy Java Selenium Page Object into Playwright TypeScript
  agent-qa transpile src/test/java/pages/LoginPage.java --to playwright-ts --out src/

  # Transpile Katalon Groovy script into Selenium Java
  agent-qa transpile Keywords/pages/CheckoutPage.groovy --to selenium-java

  # 0-Token Polyglot AST Inventory of entire repository (regardless of language)
  agent-qa omni-scan .
  ```

---

### 18. `tools/bug_reporter.py`
- **Purpose:** Auto-Bug Reporter & Root Cause Analysis (RCA) Ticket Generator. Automatically distinguishes AUT bugs (server 500, JS exceptions) from test maintenance issues, distills stack traces, formats reproduction steps, and exports ready-to-paste Jira markup or GitHub Markdown.
- **CLI Syntax:**
  ```bash
  agent-qa report-bug --title "Checkout payment fails" --error "500 Internal Server Error" --format jira
  ```

---

### 19. `tools/network_mock_shield.py`
- **Purpose:** API Network Mocking & Chaos Shield Generator. Generates zero-token route interception code and chaos fault injection (Stripe/VNPAY payment success/fail, 401/403 auth, 500 server crash, network latency) for Playwright, Cypress, and Python.
- **CLI Syntax:**
  ```bash
  agent-qa mock-shield --preset payment_success --url "**/api/checkout"
  agent-qa mock-shield --preset server_crash_500 --delay 2000
  ```

---

### 20. `tools/smart_visual_masker.py`
- **Purpose:** Smart Visual Masker & Anti-Flake Engine. Eliminates 99% of false alarms in visual regression testing by disabling CSS animations, freezing SVG spinners, and masking dynamic timestamps, clocks, and avatars.
- **CLI Syntax:**
  ```bash
  agent-qa visual-mask --playwright-snippet
  agent-qa visual-mask --css
  ```

---

### 21. `tools/ci_healing_hook.py`
- **Purpose:** CI/CD Silent Self-Healing Pipeline Hook. Executes inside GitHub Actions / GitLab CI when a locator fails, applies in-place auto-heal, and generates an automated Pull Request draft with diff and confidence score.
- **CLI Syntax:**
  ```bash
  agent-qa ci-hook --file LoginPage.ts --old-loc "//button[@id='old']" --new-loc "//button[@id='new']"
  ```

---

### 22. `tools/export_postman_collection.py`
- **Purpose:** Enterprise OpenAPI/Swagger, HAR & Zero-Input Domain Postman Collection v2.1.0 Exporter (Postman Pinnacle Suite). Generates fully structured Postman collections with dynamic pre-request scripts, SLA latency tests, response code assertions, autonomous token/entity chaining, native **AJV JSON Schema Validation**, companion **Data-Driven Testing (DDT) CSV matrix**, and **Autonomous Zero-Input Domain Synthesis** (`--domain [ecommerce|banking|saas]`).
- **CLI Syntax:**
  ```bash
  # 1. Ingest OpenAPI spec and export Postman collection + environment + AJV Schema asserts
  agent-qa export-postman --spec swagger.json -o collection.json --env-output env.json

  # 2. Autonomous Zero-Input Synthesis (No file provided! Synthesizes complete Banking/Ecom suite)
  agent-qa export-postman --domain banking -o banking_col.json --env-output env.json --ddt-output ddt_data.csv
  agent-qa export-postman --domain ecommerce -o ecom_col.json --ddt-output ecom_data.csv

  # 3. Replay production HAR traffic as Postman requests
  agent-qa export-postman --har session.har -o har_collection.json
  ```

---

### 23. `tools/generate_jmx_plan.py`
- **Purpose:** Apache JMeter 5.x Performance Test Plan XML (.jmx) Generator (JMeter 360° Pinnacle Suite). Ingests OpenAPI specifications, Postman Collections, or HAR recordings to output production-ready JMeter load, stress, spike, and soak test plans with HTTP Cookie & Cache Managers, CSV Data Set Config, Transaction Controllers, Pareto Traffic Shaping (`--weighted-mix`), Deep Data Correlation (CSRF regex & random dynamic selectors), JSR223 Groovy HMAC payload signers, InfluxDB live APM telemetry, PerfMon server agent monitoring, and Multi-Protocol support (HTTP, JDBC, WebSocket, gRPC, Kafka).
- **CLI Syntax:**
  ```bash
  # 1. Generate JMeter plan with Pareto traffic shaping (70% Browse, 20% Cart, 10% Checkout)
  agent-qa generate-jmx --spec swagger.json -o load_plan.jmx --weighted-mix "70:Browse,20:Cart,10:Checkout"

  # 2. Convert existing Postman collection with CSV data & Deep Correlation (CSRF + random items)
  agent-qa generate-jmx --postman collection.json -o perf_plan.jmx --csv-data users.csv --deep-correlation

  # 3. Generate multi-protocol test plans (WebSocket, gRPC, Kafka, JDBC)
  agent-qa generate-jmx --ws-sample -o websocket_plan.jmx
  agent-qa generate-jmx --grpc-sample -o grpc_plan.jmx
  agent-qa generate-jmx --kafka-sample -o kafka_plan.jmx
  agent-qa generate-jmx --jdbc-sample -o jdbc_plan.jmx

  # 4. Generate with live InfluxDB streaming & PerfMon Server Agent
  agent-qa generate-jmx --spec swagger.json -o perf_plan.jmx --influxdb-url http://influxdb:8086/write?db=jmeter --perfmon-server 192.168.1.50:4444

  # 5. Run headless JMeter CLI
  jmeter -n -t load_plan.jmx -l results.jtl -e -o ./html_report
  ```

---

### 24. `tools/jtl_analyzer.py`
- **Purpose:** Apache JMeter JTL Results Analyzer & CI/CD SLA Quality Gatekeeper. Parses `.jtl` (CSV or XML), computes statistical percentiles ($P_{50}, P_{90}, P_{95}, P_{99}$, Throughput, Error Rate), evaluates user SLA thresholds, supports server telemetry correlation (`--telemetry`), and returns deterministic exit code `0` (Pass) or `1` (Fail) to enforce quality gates in automated pipelines.
- **CLI Syntax:**
  ```bash
  # 1. Enforce CI/CD Quality Gate with P95 Latency SLA (< 500ms) and max error rate (< 1%)
  agent-qa analyze-jtl results.jtl --sla-p95 500 --max-error-rate 1.0

  # 2. Correlate with Server-Side APM Telemetry directly in Quality Gate
  agent-qa analyze-jtl results.jtl --sla-p95 500 --telemetry server_metrics.csv --markdown pr_report.md

  # 3. Dry-run sample benchmark verification
  agent-qa analyze-jtl --sample --sla-p95 500
  ```

---

### 25. `tools/author_integrity.py` (Author Provenance & Anti-Tamper Integrity Guard)
- **Purpose:** Cryptographic and textual provenance validator enforcing the mandatory author attribution condition of the MIT License:
  *"The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software."*
  Protects original creator **Thế Vị (@TeeVee98)** against unauthorized author stripping or copyright tampering across `LICENSE`, `package.json`, `README.md`, and `pyproject.toml`.
- **Trigger Condition:** Runs autonomously as pre-flight engine check in `tools/verify_all.py`, pre-dispatch in `agent-qa` CLI, or on-demand via `agent-qa verify-author`.
- **CLI Syntax:**
  ```bash
  # 1. Verify author attribution and provenance
  python tools/author_integrity.py
  agent-qa verify-author

  # 2. Enforced autonomously during Quality Gate verification
  python tools/verify_all.py
  agent-qa verify
  ```

---

### 26. `tools/md_to_xlsx.py` (Enterprise Markdown-to-Excel Converter)
- **Purpose:** Parses Markdown Test Case tables and converts them into professional, styled Excel workbooks (`.xlsx`) with Navy Blue headers, frozen header panes (`A2`), auto-filters, color-coded badges for Risk Level (High/Med/Low) and Priority (Critical/High/Med/Low), and multi-line wrapping.
- **CLI Syntax:**
  ```bash
  # 1. Convert markdown test cases to styled Excel (.xlsx)
  agent-qa export-excel test_cases_crm.md

  # 2. Specify custom output path and sheet title
  agent-qa export-excel test_cases_crm.md -o CRM_TestCases_v1.xlsx --sheet-name "CRM Login"

  # 3. Direct python execution
  python3 tools/md_to_xlsx.py path/to/cases.md -o export.xlsx
  ```

---

### 27. `tools/count_tokens.py` (Cross-Platform Token & Cost Auditor)
- **Purpose:** Audits and calculates token usage (Uncached Input, KV Cache Read, and Output/Thinking tokens) and estimated API costs across **Google Antigravity, Cursor Agent, and Claude Code**. Supports turn-by-turn breakdown, per-prompt profiling, multi-client session discovery, and cache hit rate tracking.
- **Trigger Condition:** On-demand after completing a task, turn, or test run to monitor context efficiency, detect token bloat, or calculate LLM cost across any supported AI client.
- **CLI Syntax:**
  ```bash
  # 1. Audit active Antigravity session
  agent-qa tokens
  python3 tools/count_tokens.py

  # 2. Audit Cursor Agent sessions (parses ~/.cursor/projects/*/agent-transcripts/*/*.jsonl)
  python3 tools/count_tokens.py --platform cursor
  python3 tools/count_tokens.py --platform cursor --last-task
  python3 tools/count_tokens.py --platform cursor --turns

  # 3. List recent sessions across all platforms (Antigravity, Cursor, Claude)
  python3 tools/count_tokens.py --platform all --list

  # 4. Direct audit of any transcript file with auto-format detection
  python3 tools/count_tokens.py --file /path/to/transcript.jsonl

  # 5. Audit current active session (Antigravity)
  agent-qa tokens --current

  # 6. Show 5-hour and 7-day rolling window quota usage
  agent-qa tokens --rolling

  # 7. Benchmark Hub vs. Vanilla token & cost savings
  agent-qa tokens --savings

  # 8. Calculate cost with specific pricing model (gemini-flash, gemini-pro, claude-sonnet, claude-opus, gpt-4o, gpt-4o-mini)
  agent-qa tokens --pricing claude-sonnet

  # 9. Output machine-readable JSON
  agent-qa tokens --json
  ```

---

### 28. `tools/dashboard_generator.py` (Standalone Executive HTML Dashboard)
- **Purpose:** Compiles project health metrics, 10 Quality Gates status, AST repository maps, benchmark results, and skills inventory into a single, dependency-free, modern HTML dashboard (`PROJECT_DASHBOARD.html`).
- **Trigger Condition:** On-demand when presenting project status to stakeholders, QA leads, or managers, or after completing project analysis/audits.
- **CLI Syntax:**
  ```bash
  # 1. Generate dashboard for current project
  agent-qa dashboard
  python3 tools/dashboard_generator.py

  # 2. Generate and open directly in browser
  agent-qa dashboard --open

  # 3. Output to custom path
  agent-qa dashboard -o reports/custom_dashboard.html
  ```

---

### 29. `tools/watch_mode.py` (Real-Time Incremental Watch Mode Sentinel)
- **Purpose:** Continuously monitors repository files for code changes and triggers near-instant (< 100ms) incremental verification (UTF-8 No BOM, absolute machine paths, AST Meta Infer-style fake-pass checks) with an interactive terminal Heads-Up Display (HUD).
- **Trigger Condition:** During active test development or refactoring sessions to get immediate feedback without manually running commands.
- **CLI Syntax:**
  ```bash
  # 1. Start real-time watch mode on current directory
  agent-qa watch
  python3 tools/watch_mode.py

  # 2. Watch with custom debounce interval
  agent-qa watch --debounce 0.5

  # 3. Run incremental scan once on all files and exit (ideal for CI/CD pre-commit hooks)
  agent-qa watch --once
  ```

---

### 30. `tools/debt_harvester.py` (Technical Debt & Shortcut Harvester)
- **Purpose:** Scans code comments across multiple programming languages (`#`, `//`, `/* */`, `--`, `<!-- -->`) for `shortcut: <limit>, <when to upgrade>` annotations left by lazy senior developers, compiling them into a structured Markdown debt ledger or machine-readable JSON.
- **Trigger Condition:** On-demand when scanning accumulated technical debt, before major releases, or when user asks "scan debt" / "list shortcuts".
- **CLI Syntax:**
  ```bash
  # 1. Scan codebase for shortcuts and display table
  agent-qa debt
  python3 tools/debt_harvester.py --scan

  # 2. Scan specific directory and export to markdown ledger
  agent-qa debt ./src --output DEBT_LEDGER.md

  # 3. Output machine-readable JSON for CI integration
  agent-qa debt --json
  ```

---

### 31. `tools/senior_code_review.py` (6-Pillar Senior Git Diff Reviewer)
- **Purpose:** Performs senior-level engineering code review on uncommitted Git diffs (or staged changes) across 6 core pillars: Bugs & Logic, Security & Boundaries, Real Concurrency & Scale, Missing Tests, Speed & Perf, and Bloat Elimination.
- **Trigger Condition:** On-demand before committing, submitting a PR, or when user asks "review diff" / "review code" / "senior review".
- **CLI Syntax:**
  ```bash
  # 1. Review all working tree git diff changes
  agent-qa review
  python3 tools/senior_code_review.py

  # 2. Review staged changes only
  agent-qa review --staged
  python3 tools/senior_code_review.py --staged

  # 3. Output review report as Markdown or JSON
  agent-qa review --output-md REVIEW_REPORT.md
  agent-qa review --json
  ```

---

### 32. `tools/skill_collision_guard.py` (Tier-2 Skill Routing & Collision Guard — Gate 9)
- **Purpose:** Enforces deterministic skill dispatch and prevents routing collision across internal Hub skills (`.agents/skills/`) and external plugins based on cosine/Jaccard semantic overlap. Guarantees zero ambiguous triggers and acts as DoD Gate 9.
- **Trigger Condition:** Executed automatically during `verify_all.py` (Gate 9), pre-commit, or on-demand when auditing skill trigger uniqueness.
- **CLI Syntax:**
  ```bash
  # 1. Audit skill overlap and check for collision
  python3 tools/skill_collision_guard.py

  # 2. Audit with custom similarity threshold (default: 0.75 critical, 0.50 warning)
  python3 tools/skill_collision_guard.py --threshold 0.80 --warn-threshold 0.45

  # 3. Output machine-readable JSON for CI integration
  python3 tools/skill_collision_guard.py --json
  ```

---

### 33. `tools/reversible_sandbox.py` (GoEx Reversible Teardown Sandbox Stack)
- **Purpose:** Manages a deterministic LIFO undo execution stack for safe test automation and self-healing. Automatically rolls back filesystem mutations, database fixture insertions, and environment changes if a test or patch crashes.
- **Trigger Condition:** When dispatching destructive mutations, exploratory self-healing patches, or running isolated trial runs.
- **CLI Syntax:**
  ```bash
  # 1. Check current sandbox undo stack status
  python3 tools/reversible_sandbox.py --status

  # 2. Run reversible stack verification demo
  python3 tools/reversible_sandbox.py --demo
  ```

---

### 34. `tools/auto_heal_reflexion.py` (Multi-Trial Episodic Reflexion Loop — K=3)
- **Purpose:** Implements the Noah Shinn Episodic Reflexion loop for failed automated tests. Performs up to $K=3$ iterative trial-feedback cycles, updating episodic memory and self-correcting locators/code without polluting git history.
- **Trigger Condition:** When headless test suites fail in runner, or single-pass self-healing fails to resolve complex selector or timing issues.
- **CLI Syntax:**
  ```bash
  # 1. Run multi-trial reflexion self-healing on failing test
  python3 tools/auto_heal_reflexion.py --test "TC_Checkout_01" --error "ElementClickInterceptedException"

  # 2. Configure custom max trials (default: 3)
  python3 tools/auto_heal_reflexion.py --test "TC_Login_02" --error "TimeoutException" --max-trials 5
  ```

---

### 35. `tools/skill_vault.py` (Voyager Lifelong Page Class SQLite Vault)
- **Purpose:** Persists, indexes, and retrieves verified Clean POM Page Class methods, custom locators, and resilient interaction primitives in a permanent SQLite repository (`~/.agent_memory/skill_vault.db`). Prevents re-inventing known solutions across sessions.
- **Trigger Condition:** When authoring new Page Classes, searching for proven element interactions, or archiving new successful POM patterns.
- **CLI Syntax:**
  ```bash
  # 1. Query verified Page Class primitives by keyword
  python3 tools/skill_vault.py --query "table_pagination"

  # 2. List all indexed primitives in the lifelong vault
  python3 tools/skill_vault.py --list

  # 3. Seed initial baseline POM primitives
  python3 tools/skill_vault.py --seed-samples
  ```

---

### 36. `tools/dspy_qa_signatures.py` (Stanford DSPy Declarative QA Signature Engine)
- **Purpose:** Transforms prompt-based test generation into typed, declarative signatures (`StoryToUniversalIR`, `HealBrokenLocator`, `MutantAssertionSignature`) with formal input/output contracts, eliminating brittle prompt hacking.
- **Trigger Condition:** When compiling user stories into Universal IR, generating defensive assertions, or verifying agent signature compatibility.
- **CLI Syntax:**
  ```bash
  # 1. Check DSPy engine status and signature registrations
  python3 tools/dspy_qa_signatures.py --check

  # 2. Run declarative compilation demonstration
  python3 tools/dspy_qa_signatures.py --demo
  ```

---

### 37. `tools/interview_story.py` (Pocock Grilling Primitive & Requirement Interrogation)
- **Purpose:** Analyzes rough user stories and acceptance criteria against the Frontier Interrogation Checklist, identifying ambiguities, missing negative boundaries, unstated auth constraints, and race conditions before coding begins.
- **Trigger Condition:** Triggered autonomously when a user provides an incomplete story or uses `/grill-me` to sharpen requirements.
- **CLI Syntax:**
  ```bash
  # 1. Interrogate user story text directly
  python3 tools/interview_story.py "As a user I want to checkout cart"

  # 2. Analyze user story file and output JSON questions
  python3 tools/interview_story.py docs/specs/order_flow.md --json
  ```

---

### 38. `tools/textgrad_mutation_optimizer.py` (Mutant-Directed Textual Loss Optimizer)
- **Purpose:** Uses AST micro-mutants as a "textual loss function" to iteratively refine test assertions and Page Class validation methods until mutation score satisfies $\ge 80\%$.
- **Trigger Condition:** When newly generated tests fail Gate 8 (Mutation Score $< 80\%$), optimizing assertions to catch all logic mutations.
- **CLI Syntax:**
  ```bash
  # 1. Optimize test script assertions against mutants
  python3 tools/textgrad_mutation_optimizer.py --file tests/test_checkout.py

  # 2. Optimize with custom target score threshold
  python3 tools/textgrad_mutation_optimizer.py --file tests/test_login.py --target-score 85.0

  # 3. Output results as JSON
  python3 tools/textgrad_mutation_optimizer.py --file tests/test_checkout.py --json
  ```

---

### 39. `tools/synapse_qa_bench.py` (Tool Function Calling Benchmark — Gorilla BFCL)
- **Purpose:** Evaluates AI Agent tool-selection accuracy, argument validation precision, and multi-turn execution efficiency against standardized enterprise QA scenarios.
- **Trigger Condition:** On-demand when benchmarking agent model upgrades, evaluating tool prompt updates, or running QA engine evaluations.
- **CLI Syntax:**
  ```bash
  # 1. Run QA function-calling benchmark across all test scenarios
  python3 tools/synapse_qa_bench.py

  # 2. Output detailed benchmark report as JSON
  python3 tools/synapse_qa_bench.py --json
  ```

---

### 40. `tools/synapse_observer.py` (Cognitive Observer & Tradeoff Sentinel)
- **Purpose:** Autonomous out-of-band observer inspired by Anthropic Claude Code 2.1.292 (`cc-plugin-you-should-know`). Evaluates code diffs or arbitrary text to surface critical tradeoffs (Clean POM violations, pipeline flakiness from static sleeps, un-teardowned entities, and tracked shortcuts) with high interruption threshold (defaults to `learn: none`).
- **Trigger Condition:** Autonomous pre-commit sanity check, PR review, or when prompted for tradeoff evaluation.
- **CLI Syntax:**
  ```bash
  # 1. Analyze working tree git diff (default)
  python tools/synapse_observer.py

  # 2. Analyze staged git diff (pre-commit)
  python tools/synapse_observer.py --staged

  # 3. Analyze specific file
  python tools/synapse_observer.py --file tests/test_login.py

  # 4. Strict mode for CI quality gates (exit 1 on active alert)
  python tools/synapse_observer.py --strict

  # 5. Output JSON for tool integration
  python tools/synapse_observer.py --json

  # 6. Evaluate and return all matching alerts
  python tools/synapse_observer.py --all

  # 7. Acknowledge / Unacknowledge / Reset memory
  python tools/synapse_observer.py --ack static_sleep_flakiness
  python tools/synapse_observer.py --unack static_sleep_flakiness
  python tools/synapse_observer.py --reset
  ```
- **Sample Output:**
  ```text
  learn: Static sleep was introduced, which creates pipeline flakiness and slows CI runs.
  tag: Heads up
  explain:
  **Replace Static Sleep with Dynamic Smart Wait**
  - Hardcoded sleeps either wait too long (wasting CI time) or not long enough under load.
  - Use dynamic element visibility checks or network idle states instead.
  - Dynamic waits resume immediately once the condition is met, saving time and eliminating flakiness.
  ```

---

### 41. `tools/humanize_linter.py` (Humanize & Anti-AI Slop Linter)
- **Purpose:** Scans documentation, docstrings, commit messages, and PR descriptions to detect and eliminate robotic AI buzzwords, cliches, pileups, and punctuation quirks, offering human plain-language replacements while statefully masking code blocks and inline backticks.
- **Trigger Condition:** Pre-commit documentation check, commit message validation, PR review, or autonomous tone scan.
- **CLI Syntax:**
  ```bash
  # 1. Lint text string directly
  python tools/humanize_linter.py --text "We leverage AI to optimize everything."

  # 2. Lint documentation or markdown file
  python tools/humanize_linter.py --file docs/README.md

  # 3. Strict mode for CI gates (exit 1 if issues found)
  python tools/humanize_linter.py --strict --file docs/README.md

  # 4. Output results as structured JSON
  python tools/humanize_linter.py --json --text "This is a vibrant tapestry."
  ```
- **Sample Output:**
  ```text
  ⚠️  docs/README.md: Found 2 writing/tone issue(s):
    - L5 [BUZZWORD]: 'leveraging' -> replace with 'use'
      Excerpt: "We are leveraging this helper to build test cases."
    - L12 [CLICHE]: 'plays a pivotal role' -> replace with 'is key'
      Excerpt: "This utility plays a pivotal role in test data generation."
  ```

---

### 42. `tools/security_coverage_ledger.py` (Mathematical Security Coverage Ledger)
- **Purpose:** Manages and validates deterministic security audit coverage units (`Coverage Unit = Surface × Boundary × Subsystem × Attack Class [× Lifecycle]`) using RFC 3986 percent-encoded canonical IDs, 19-field Cloudflare schema, and strict state invariants.
- **Trigger Condition:** Phase 1 & 2 reconnaissance and attack surface tracking during security audits, pre-release security validation.
- **CLI Syntax:**
  ```bash
  # 1. Initialize a new coverage ledger (supports 'object' or 'array' format)
  python tools/security_coverage_ledger.py init -f coverage-ledger.json --format object

  # 2. Add an audit coverage unit
  python tools/security_coverage_ledger.py add -f coverage-ledger.json -s "web_api" -b "auth" --subsystem "billing" -a "idor"

  # 3. Validate ledger state machine invariants and security rules
  python tools/security_coverage_ledger.py validate coverage-ledger.json

  # 4. Compute mathematical coverage metrics
  python tools/security_coverage_ledger.py summary coverage-ledger.json

  # 5. Output metrics as JSON for CI/CD integration
  python tools/security_coverage_ledger.py summary coverage-ledger.json --json
  ```
- **Sample Output:**
  ```text
  📊 Security Coverage Ledger Metrics (12 total units):
    - In-Scope Units:       10
    - Audited Coverage:     80.0% (8/10 units)
    - Blocker Rate:         10.0%
    Status Breakdown:
      - PLANNED       : 2
      - IN_PROGRESS   : 0
      - COVERED       : 7
      - CANDIDATE     : 1
      - BLOCKED       : 1
      - DEFERRED      : 0
      - NOT_APPLICABLE: 1
      - OUT_OF_SCOPE  : 1
    Wave Breakdown:
      - Wave 1        : 9
      - Wave 2        : 3
  ```

---

### 43. `tools/_openapi_parser.py` (Shared OpenAPI & Swagger Specification Parser)
- **Purpose:** Core parsing library for Swagger 2.0 and OpenAPI 3.0/3.1 specs, extracting routes, request/response models, auth schemes, and parameters into a canonical AST.
- **Trigger Condition:** Used internally by API matrix generators, contract drift sentinels, and API fuzzers.
- **CLI Syntax:**
  ```bash
  python tools/_openapi_parser.py <spec_file> [--validate]
  ```

---

### 44. `tools/agentless_patcher.py` (Agentless 3-Stage Deterministic Patcher)
- **Purpose:** Implements the OpenAutoCoder/Agentless pattern for test repairs: Stage 1 (Fault localization via AST), Stage 2 (Candidate patch synthesis), Stage 3 (Minimal diff regression validation).
- **Trigger Condition:** Automated test failures requiring targeted locator or syntax repairs without multi-agent token bloat.
- **CLI Syntax:**
  ```bash
  python tools/agentless_patcher.py --file <file_path> --error "<error_message>" --test-cmd "pytest tests -q"
  ```

---

### 45. `tools/auto_heal.py` (Closed-Loop Locator Self-Healing Engine)
- **Purpose:** Analyzes broken Page Class locators against current DOM/AOM snapshots and applies verified semantic replacements (role, label, test-id hierarchy).
- **Trigger Condition:** Playwright / Katalon NoSuchElementException or ElementNotFound failure.
- **CLI Syntax:**
  ```bash
  python tools/auto_heal.py --file <page_file> --broken "<selector>" --live-dom <dom.html>
  # or via CLI
  agent-qa heal --file <page_file>
  ```

---

### 46. `tools/autogen_qa_broker.py` (Asynchronous Actor QA Message Broker)
- **Purpose:** Provides decoupled event publish/subscribe, mailbox routing, and priority message passing between subagents in a swarm (Microsoft AutoGen v0.4+ pattern).
- **Trigger Condition:** Multi-agent distributed test execution and matrix sharding coordination.
- **CLI Syntax:**
  ```bash
  python tools/autogen_qa_broker.py --publish --topic "test.results" --payload results.json
  ```

---

### 47. `tools/benchmark_swarm_context.py` (Swarm Context Token Benchmark Harness)
- **Purpose:** Measures and benchmarks token throughput, context window occupancy, and savings achieved by Clean POM Flat Architecture and progressive disclosure (proving >= 40% savings).
- **Trigger Condition:** Measuring efficiency gains, auditing swarm prompt overhead, or reporting token metrics.
- **CLI Syntax:**
  ```bash
  python tools/benchmark_swarm_context.py --iterations 10 --report token_savings.json
  ```

---

### 48. `tools/browsergym_eval.py` (BrowserGym Web Agent Benchmark Harness)
- **Purpose:** Benchmarks web automation agents against standardized enterprise tasks with headless <200ms latency budgets and ground-truth DB state verification (BrowserGym / WebArena pattern).
- **Trigger Condition:** Benchmarking autonomous QA agent navigation accuracy and speed.
- **CLI Syntax:**
  ```bash
  python tools/browsergym_eval.py --task "form_submit" --headless --budget-ms 200
  ```

---

### 49. `tools/bump_version.py` (Atomic Universal Version Bumper)
- **Purpose:** Atomically bumps semantic versions across all 20 manifest and code targets (package.json, pyproject.toml, plugin.json, READMEs, config, docs).
- **Trigger Condition:** Pre-release version updates before running `tools/hub_publisher.py`.
- **CLI Syntax:**
  ```bash
  python tools/bump_version.py patch
  python tools/bump_version.py minor
  python tools/bump_version.py major
  ```

---

### 50. `tools/contract_validator.py` (Swarm Data Contract Validator)
- **Purpose:** Validates JSON data contracts exchanged between subagents (e.g. Live Explorer to Pom Crafter) against strict JSON schemas (Single Front-Door Integrity Guard).
- **Trigger Condition:** Subagent handoff verification at Stage transitions in the FSM.
- **CLI Syntax:**
  ```bash
  python tools/contract_validator.py --contract handoff.json --schema schemas/handoff.json
  ```

---

### 51. `tools/e2e_flow_prober.py` (Enterprise E2E Flow Prober & XPath Crawler)
- **Purpose:** Headless Playwright crawler that probes web user flows, maps interactive elements, and generates resilient locators across platforms.
- **Trigger Condition:** Flow discovery for unmapped pages and exploratory test generation.
- **CLI Syntax:**
  ```bash
  python tools/e2e_flow_prober.py --url https://staging.app.local --depth 2 --output flow_map.json
  ```

---

### 52. `tools/fsm_enforcer.py` (5-Stage QA Multi-Agent Finite State Machine Enforcer)
- **Purpose:** Enforces deterministic 5-stage workflow progression (Discovery -> Synthesis -> Execution -> Autopsy -> Quality Gate) with SHA-256 cryptographic proof tokens.
- **Trigger Condition:** Transitioning between QA subagent lifecycle stages.
- **CLI Syntax:**
  ```bash
  python tools/fsm_enforcer.py init --task-id TASK_001
  python tools/fsm_enforcer.py transition Stage2_Synthesis --token <proof_token>
  ```

---

### 53. `tools/fsm_middleware.py` (Runtime FSM Interceptor & Tool Proxy)
- **Purpose:** Intercepts tool execution requests, enforcing that tools are only called when their corresponding FSM stage is active.
- **Trigger Condition:** Tool-calling guard in autonomous agent swarms.
- **CLI Syntax:**
  ```bash
  python tools/fsm_middleware.py --check-tool tools/verify_all.py --current-stage Stage5_QualityGate
  ```

---

### 54. `tools/generate_allure_report.py` (Enterprise Allure HTML Report Generator)
- **Purpose:** Compiles raw Allure XML/JSON test results into a standalone HTML dashboard with trend graphs, failure timelines, and step attachments.
- **Trigger Condition:** Post-test reporting in CI/CD pipelines or local test runs.
- **CLI Syntax:**
  ```bash
  python tools/generate_allure_report.py --results ./allure-results --output ./Reports/allure-report
  ```

---

### 55. `tools/generate_sbom.py` (SPDX 2.3 JSON Software Bill of Materials Generator)
- **Purpose:** Scans Python, Node.js, and Java/Gradle dependencies to generate an official SPDX 2.3 JSON SBOM for software supply chain security compliance.
- **Trigger Condition:** Release pipelines, pre-release security verification, or vendor audit compliance.
- **CLI Syntax:**
  ```bash
  python tools/generate_sbom.py --format spdx-json -o Reports/sbom.json
  ```

---

### 56. `tools/generate_test_reports.py` (Enterprise Test Report Aggregator)
- **Purpose:** Consolidates multi-runner test execution outputs (JUnit XML, Pytest, Katalon, Allure) into unified summary JSON and markdown reports.
- **Trigger Condition:** Aggregating test results across parallel shards or multi-platform test suites.
- **CLI Syntax:**
  ```bash
  python tools/generate_test_reports.py --reports-dir ./Reports --output ./Reports/summary.json
  ```

---

### 57. `tools/generate_tool_catalog.py` (Enterprise Tooling Catalog Generator)
- **Purpose:** Introspects all Python scripts in `tools/`, extracts AST docstrings, CLI arguments, and categories, generating `tools/TOOL_CATALOG.json`.
- **Trigger Condition:** Adding or modifying tools in `tools/` to maintain the canonical catalog.
- **CLI Syntax:**
  ```bash
  python tools/generate_tool_catalog.py --output tools/TOOL_CATALOG.json
  ```

---

### 58. `tools/git_pre_commit_guard.py` (Enterprise Git Pre-Commit Architecture Guard)
- **Purpose:** Enforces pre-commit invariants: blocks commits containing raw XPaths in test scripts, hardcoded secrets, UTF-8 BOM, or hub workspace pollution.
- **Trigger Condition:** Executed by `.git/hooks/pre-commit` before any git commit is accepted.
- **CLI Syntax:**
  ```bash
  python tools/git_pre_commit_guard.py [--staged]
  ```

---

### 59. `tools/goldfish_review.py` (Zero-Context Test Specification Reviewer)
- **Purpose:** Stress-tests user stories, BDD specs, and acceptance criteria with zero-context rigor, uncovering ambiguous edge cases, missing error paths, and unstated assumptions.
- **Trigger Condition:** Reviewing product requirements or user stories before test code generation.
- **CLI Syntax:**
  ```bash
  python tools/goldfish_review.py path/to/spec.md
  ```

---

### 60. `tools/hub_publisher.py` (Autonomous 1-Click 5-Step Hub Release Pipeline)
- **Purpose:** Executes the end-to-end Hub release: 1. Push main -> 2. Push tag vX.Y.Z -> 3. Create GitHub Release via API -> 4. Build GitHub Package -> 5. Publish & verify NPM registry.
- **Trigger Condition:** User requests "push hub" or "publish hub" after SemVer bump.
- **CLI Syntax:**
  ```bash
  python tools/hub_publisher.py [--dry-run]
  ```

---

### 61. `tools/init_config.py` (Project Configuration Bootstrapper)
- **Purpose:** Initializes `synapse.config.json` with production defaults (quality gates, SLA thresholds, mutation settings, test runner paths).
- **Trigger Condition:** Initializing a new target project or re-configuring quality gates.
- **CLI Syntax:**
  ```bash
  python tools/init_config.py [--target-dir .]
  ```

---

### 62. `tools/jira_sync.py` (Jira / Xray / Zephyr Enterprise 2-Way Sync Engine)
- **Purpose:** Pulls acceptance criteria and test cases from Jira/Xray, pushes automated execution results, and files defect tickets with attachments.
- **Trigger Condition:** TMS integration in enterprise workflows with Jira/Xray/Zephyr.
- **CLI Syntax:**
  ```bash
  python tools/jira_sync.py pull PROJ-1234
  python tools/jira_sync.py push-results --run-id RUN_567 --report results.xml
  ```

---

### 63. `tools/mcp_docx_server.py` (FastMCP Word .docx Document Server)
- **Purpose:** Zero-dependency FastMCP server enabling AI agents to read, inspect, and extract text and tables from Word (`.docx`) documents without external Office dependencies.
- **Trigger Condition:** When agent needs to inspect or extract requirements from `.docx` files.
- **CLI Syntax:**
  ```bash
  python tools/mcp_docx_server.py
  # or via CLI
  agent-qa mcp-docx
  ```

---

### 64. `tools/mipro_assertion_tuner.py` (MIPROv2 Bayesian Prompt Assertion Tuner)
- **Purpose:** Uses Bayesian teleprompter optimization (DSPy v2 + Optuna TPE) to tune few-shot assertion generators against mutation kill scores.
- **Trigger Condition:** Optimizing QA prompt instructions and few-shot examples when mutation score < 80%.
- **CLI Syntax:**
  ```bash
  python tools/mipro_assertion_tuner.py --trials 20 --min-kill 85.0
  ```

---

### 65. `tools/omni_emitter.py` (Universal Polyglot Clean POM Code Emitter)
- **Purpose:** Generates Clean POM Page Classes and test scripts across Playwright TypeScript, Python Pytest, Java TestNG, and Katalon Groovy from Universal IR.
- **Trigger Condition:** Stage 2 Code Synthesis by `pom-crafter` subagent.
- **CLI Syntax:**
  ```bash
  python tools/omni_emitter.py --ir suite_ir.json --lang typescript -o tests/
  ```

---

### 66. `tools/omni_parser.py` (Deterministic Polyglot AST Parser)
- **Purpose:** Parses existing Page Classes and test files into Universal IR with 0 LLM tokens, extracting locators, actions, and assertion flows.
- **Trigger Condition:** Reverse-engineering existing test suites or preparing migration to another framework.
- **CLI Syntax:**
  ```bash
  python tools/omni_parser.py --src ./tests --emit-ir ./suite_ir.json
  ```

---

### 67. `tools/openxml_guard.py` (OpenXML Security & Protocol Defense Guard)
- **Purpose:** Audits generated and parsed Excel/Word OpenXML packages for zip-bomb attacks, external entity injection (XXE), and macro risks.
- **Trigger Condition:** Pre-flight validation before opening or exporting `.xlsx` / `.docx` files.
- **CLI Syntax:**
  ```bash
  python tools/openxml_guard.py audit path/to/document.xlsx
  ```

---

### 68. `tools/package_release.py` (Enterprise Release Packager & Provenance Generator)
- **Purpose:** Packages distribution archives (zip, tar.gz), creates SHA-256 checksum manifests, and verifies release file cleanliness.
- **Trigger Condition:** Building release distribution bundles during CI/CD.
- **CLI Syntax:**
  ```bash
  python tools/package_release.py --version 3.7.2 --output-dir dist/
  ```

---

### 69. `tools/project_state.py` (Enterprise Project State Machine & Memory Anchor)
- **Purpose:** Maintains persistent session state, active subagent roles, completed checkpoints, and token-capped recall memory across long multi-turn sessions.
- **Trigger Condition:** Session resumption, context compaction recovery, and multi-agent state coordination.
- **CLI Syntax:**
  ```bash
  python tools/project_state.py get
  python tools/project_state.py set --key "active_role" --val "pom-crafter"
  ```

---

### 70. `tools/qa_event_stream.py` (Immutable QA Event Stream Engine)
- **Purpose:** Records append-only deterministic action/observation timelines with SHA-256 hash chains, enabling reversible checkpoint rollbacks and full execution tracing (OpenHands pattern).
- **Trigger Condition:** Tracing complex multi-step test executions and audit trails.
- **CLI Syntax:**
  ```bash
  python tools/qa_event_stream.py record --event-type ACTION --payload '{"action":"click"}'
  python tools/qa_event_stream.py verify-chain
  ```

---

### 71. `tools/security_scanner.py` (Enterprise Security Sentinel & Vulnerability Scanner)
- **Purpose:** Scans Python and NPM dependency trees against known CVE advisory databases (Pip-Audit / NPM Audit) and audits dangerous system call sinks.
- **Trigger Condition:** Security gating during pre-commit, CI/CD, or `verify_all Gate 6`.
- **CLI Syntax:**
  ```bash
  python tools/security_scanner.py [--strict]
  ```

---

### 72. `tools/spec_drift_sentinel.py` (Spec-to-Code Drift Sentinel)
- **Purpose:** Analyzes drift between OpenAPI / BDD specs and implementation test suites, reporting untested endpoints, removed parameters, and schema mismatches.
- **Trigger Condition:** Pre-merge CI checks to detect API contract changes unreflected in test code.
- **CLI Syntax:**
  ```bash
  python tools/spec_drift_sentinel.py --spec api.json --tests ./tests
  ```

---

### 73. `tools/swe_qa_aci.py` (QA Agent-Computer Interface — SWE-agent Pattern)
- **Purpose:** Provides a token-efficient code inspection and surgical editing interface for AI agents, limiting window reads to 40-50 lines and performing pre-commit AST checks.
- **Trigger Condition:** Safe inspection and modification of large Page Classes without context blowout.
- **CLI Syntax:**
  ```bash
  python tools/swe_qa_aci.py view --file path/to/Page.groovy --start 10 --end 50
  python tools/swe_qa_aci.py edit --file path/to/Page.groovy --line 25 --replace "..."
  ```

---

### 74. `tools/template_excel_exporter.py` (Template-Driven Excel Test Case Exporter)
- **Purpose:** Exports Markdown test matrices into enterprise Excel workbooks formatted with cell styles, AutoFilters, and dropdown Data Validation (Risk Level, Priority, Automatable).
- **Trigger Condition:** Generating formal client test deliverables from manual test suites.
- **CLI Syntax:**
  ```bash
  python tools/template_excel_exporter.py test_cases.md -o output.xlsx --sheet-name "Regression"
  ```

---

### 75. `tools/test_memory_os.py` (Hierarchical QA Test Memory OS)
- **Purpose:** Implements a 3-tier memory operating system (Core memory, Recall step logs, Archival semantic store) scoped by AUT version to prevent context rot (Letta / MemGPT pattern).
- **Trigger Condition:** Long-running test campaigns, multi-suite session management, and persistent auth token reuse.
- **CLI Syntax:**
  ```bash
  python tools/test_memory_os.py core-get --key "auth_token"
  python tools/test_memory_os.py recall-search "login failure"
  ```

---

### 76. `tools/tot_exploratory_tester.py` (Tree-of-Thoughts Exploratory Testing Engine)
- **Purpose:** Decomposes complex user stories into a non-linear Tree-of-Thoughts with Happy Path, Boundary/Race, and Negative/Chaos branches scored via Beam Search.
- **Trigger Condition:** Designing high-coverage exploratory charters and fuzzing scenarios for ambiguous features.
- **CLI Syntax:**
  ```bash
  python tools/tot_exploratory_tester.py --story user_story.md --beam-width 3 -o exploratory_tree.json
  ```

---

### 77. `tools/trend_analytics.py` (Historical Quality Trend & Flakiness Analytics)
- **Purpose:** Computes rolling historical pass/fail trends, flakiness entropy scores, and MTTR (mean time to repair) metrics across test suites over time.
- **Trigger Condition:** Generating executive QA health reports and CI/CD quality dashboards.
- **CLI Syntax:**
  ```bash
  python tools/trend_analytics.py --history ./Reports/history --output ./Reports/trends.json
  ```

---

### 78. `tools/ui_server.py` (Interactive QA Mission Control UI Server)
- **Purpose:** Fast lightweight HTTP server providing an interactive browser UI for running audits, inspecting 10 Quality Gates, viewing test matrices, and monitoring swarm state.
- **Trigger Condition:** User requests "ui", "mission control", or visual web interface for Synapse Hub.
- **CLI Syntax:**
  ```bash
  python tools/ui_server.py [--port 8080] [--open]
  # or via CLI
  agent-qa ui
  ```

---

### 79. `tools/universal_ir.py` (Universal Intermediate Representation AST Model)
- **Purpose:** Defines the language-agnostic JSON AST schema representing Page Classes, selectors, actions, assertions, and test suites for 0-token transpilation.
- **Trigger Condition:** Framework transpilation, test suite serialization, and cross-platform codegen.
- **CLI Syntax:**
  ```bash
  python tools/universal_ir.py validate suite_ir.json
  ```

---

### 80. `tools/agent_canary.py` (Autonomous Agent Canary & Mutation Testing Arena)
- **Purpose:** Headless sandbox arena evaluating autonomous AI agents against controlled adversarial mutations, prompt injection probes, and canary traps before production deployment.
- **Trigger Condition:** Validating agent resilience, testing new prompt signatures, or auditing agent workflows against behavioral drift.
- **CLI Syntax:**
  ```bash
  python tools/agent_canary.py [--arena <name>] [--runs <N>]
  ```

---

### 81. `tools/api_drift_sentinel.py` (Enterprise API Contract Drift & Breaking Change Sentinel)
- **Purpose:** Continuously compares live API responses with OpenAPI/Swagger contracts, detecting breaking schema mutations, removed properties, type alterations, and undocumented endpoints.
- **Trigger Condition:** Pre-deployment CI/CD regression gates, scheduled API health checks, and CDC contract drift detection.
- **CLI Syntax:**
  ```bash
  python tools/api_drift_sentinel.py --spec <swagger.json> --url <base_url>
  ```

---

### 82. `tools/check_env.py` (Enterprise QA Environment Diagnostic & Dependency Sentinel)
- **Purpose:** Diagnostic health runner verifying the host execution environment: Python version, Node.js, Java runtime, Playwright headless browsers, active workspace structure, and missing CLI packages.
- **Trigger Condition:** First-time onboarding, diagnosing runtime failures, or validating CI/CD runner environments.
- **CLI Syntax:**
  ```bash
  python tools/check_env.py
  # or via CLI
  agent-qa doctor
  ```

---

### 83. `tools/check_version_sync.py` (Universal Version Synchronization Sentinel)
- **Purpose:** Audits and enforces 100% version synchronization across all 20 repository manifest targets (`package.json`, `pyproject.toml`, `README.md`, `agentskills.json`, `tools/__init__.py`, etc.).
- **Trigger Condition:** Pre-release verification, gate checking, and automated version bump audits.
- **CLI Syntax:**
  ```bash
  python tools/check_version_sync.py [--fix]
  ```

---

### 84. `tools/cli.py` (Enterprise Agent-QA CLI Entrypoint)
- **Purpose:** Unified CLI front-door providing human- and agent-friendly dispatch (`agent-qa` / `synapse`) routing subcommands across all specialized Hub tools.
- **Trigger Condition:** Primary terminal entrypoint for all verification, auditing, testing, and healing commands.
- **CLI Syntax:**
  ```bash
  python tools/cli.py <command> [args]
  # or via installed package
  agent-qa <command>
  ```

---

### 85. `tools/config_decoupler.py` (Environment & Secret Decoupling Engine)
- **Purpose:** Scans test suites for hardcoded credentials, IP addresses, and URLs, automatically extracting them into decoupled `.env` files and environment-agnostic configuration templates.
- **Trigger Condition:** Legacy test refactoring, open-source sanitization, or multi-environment pipeline migration.
- **CLI Syntax:**
  ```bash
  python tools/config_decoupler.py --source <test_dir> --env-file .env
  ```

---

### 86. `tools/flaky_detector.py` (Enterprise Flaky Test Detector & Quarantine Sentinel)
- **Purpose:** Runs candidate test suites across multiple repeated iterations to calculate flakiness probability, isolating non-deterministic tests into quarantine before pipeline poisoning.
- **Trigger Condition:** Triage of non-deterministic CI failures or certifying test suite stability before release.
- **CLI Syntax:**
  ```bash
  python tools/flaky_detector.py --test-cmd "<test_command>" --iterations 5 --threshold 0.2
  ```

---

### 87. `tools/fuzz_payloads.py` (Edge-Case Fuzzing & Input Sanitization Payload Catalog)
- **Purpose:** Generates boundary value, negative, SQLi, XSS, unicode overflow, and surrogate pair fuzz payloads across 15 standard web input field types.
- **Trigger Condition:** Boundary testing, automated security testing, synthetic test data generation, and form input validation.
- **CLI Syntax:**
  ```bash
  python tools/fuzz_payloads.py --type <string|number|date|xss|sqli> [--count N]
  ```

---

### 88. `tools/gherkin_suite.py` (Gherkin BDD Suite Compiler — 0-Token Matrix Ingestion)
- **Purpose:** Compiles Gherkin `.feature` files into expanded test execution matrices, coverage-gap reports, and Universal IR representations without LLM token cost.
- **Trigger Condition:** Ingesting business requirements and BDD user stories into automated Clean POM test cases.
- **CLI Syntax:**
  ```bash
  python tools/gherkin_suite.py --feature <file.feature> [-o <matrix.json>]
  ```

---

### 89. `tools/heal_pr_automator.py` (Self-Healing Confidence Scorer & PR Automator)
- **Purpose:** Evaluates locator repair confidence scores, regression impact, and automatically constructs GitHub pull requests containing self-healed Page Class diffs.
- **Trigger Condition:** Stage 5 closed-loop test self-healing pipeline upon successful locator repair.
- **CLI Syntax:**
  ```bash
  python tools/heal_pr_automator.py --patch <patch_file> --min-confidence 0.85
  ```

---

### 90. `tools/heuristic_locator_matcher.py` (3-Layer Heuristic Locator Matcher)
- **Purpose:** Fast 3-layer deterministic heuristic locator recovery (Exact Role/Name -> Structural AOM Hierarchy -> Fuzzy Levenshtein) delivering 0-token locator repairs under 10ms.
- **Trigger Condition:** Instant autonomous recovery when a UI selector fails during live headless test runs.
- **CLI Syntax:**
  ```bash
  python tools/heuristic_locator_matcher.py --broken-sel "<selector>" --dom <dom_snapshot.html>
  ```

---

### 91. `tools/lint_ai_docs.py` (Enterprise AI Documentation & Artifact Linter — Gate 4)
- **Purpose:** Gate 4 Anti-Drift Guard auditing project documentation, ensuring zero hallucinated PageClasses, zero broken file links, and 100% alignment with real codebase symbols.
- **Trigger Condition:** Definition of Done Gate 4 in `verify_all.py` and pre-commit checks.
- **CLI Syntax:**
  ```bash
  python tools/lint_ai_docs.py [--strict]
  ```

---

### 92. `tools/lookup_tc.py` (Sub-Second Test Case Metadata Lookup Utility)
- **Purpose:** Performs sub-second indexed search across all test suites, locating test cases by ID, tag (`@Smoke`, `@Regression`), name, or author.
- **Trigger Condition:** Quick navigation to specific test scripts or finding test coverage for a requirement.
- **CLI Syntax:**
  ```bash
  python tools/lookup_tc.py <TC_ID_or_keyword>
  ```

---

### 93. `tools/lookup_xpath.py` (Fast XPath & Selector Lookup Utility)
- **Purpose:** Scans all Page Classes and object repositories to find occurrences of specific locators, identifying duplicates, fragile XPaths, or selector collision risks.
- **Trigger Condition:** Refactoring Page Classes or investigating selector collisions.
- **CLI Syntax:**
  ```bash
  python tools/lookup_xpath.py "<selector_or_text>"
  ```

---

### 94. `tools/matrix_sharder.py` (Duration-Balanced Test Matrix Sharder)
- **Purpose:** Partitions test suites across $N$ parallel CI runners using historical execution durations (K-way number partitioning), minimizing total build completion time.
- **Trigger Condition:** CI/CD matrix build setup and parallel test runner dispatch.
- **CLI Syntax:**
  ```bash
  python tools/matrix_sharder.py --suite-dir <dir> --shards <N> [--history <durations.json>]
  ```

---

### 95. `tools/mcp_excel_server.py` (Enterprise FastMCP Excel Server — Zero-Dependency XLSX)
- **Purpose:** Zero-dependency FastMCP server exposing tool endpoints for reading, writing, merging, and styling Excel spreadsheets directly through the Model Context Protocol.
- **Trigger Condition:** AI agents inspecting, updating, or formatting enterprise Excel test suites without COM or MS Excel.
- **CLI Syntax:**
  ```bash
  python tools/mcp_excel_server.py
  ```

---

### 96. `tools/mcp_server.py` (Synapse Hub Standard Model Context Protocol Server)
- **Purpose:** Production MCP server exposing Synapse Hub QA intelligence, Page Class generation, test running, and diagnostic tools to Claude Desktop, Cursor, and Antigravity.
- **Trigger Condition:** IDE integration and autonomous AI agent tool dispatch.
- **CLI Syntax:**
  ```bash
  python tools/mcp_server.py
  ```

---

### 97. `tools/micro_mutator.py` (Assertion Sensitivity & Syntactic Micro-Mutation Sentinel — Gate 8)
- **Purpose:** Gate 8 sentinel applying syntactic AST mutations (negating conditionals, removing assertions, swapping boolean flags) to measure test sensitivity and kill fake passes (threshold >= 80%).
- **Trigger Condition:** Mandatory DoD Gate 8 in `verify_all.py`, PR quality gate, and test quality auditing.
- **CLI Syntax:**
  ```bash
  python tools/micro_mutator.py [target_dir] [--min-score 80] [--test-cmd "<cmd>"]
  # or via CLI
  agent-qa mutate
  ```

---

### 98. `tools/newman_analyzer.py` (Postman/Newman Results Analyzer & CI/CD Gatekeeper)
- **Purpose:** Sub-0.1s Postman/Newman JSON test execution report analyzer parsing assertions, timings, and failures to enforce CI/CD quality gates.
- **Trigger Condition:** Post-execution Newman API test reporting in CI/CD pipelines.
- **CLI Syntax:**
  ```bash
  python tools/newman_analyzer.py <run_results.json> [--max-failures 0] [--p95-sla 500]
  ```

---

### 99. `tools/output_formatter.py` (Standardized Output Formatter & Exit Code Specification)
- **Purpose:** Formats CLI tool outputs into structured ANSI colored text, JSON, or JUnit XML with standardized exit codes across all Hub tools.
- **Trigger Condition:** Standardized output rendering and machine-readable CI integrations.
- **CLI Syntax:**
  ```bash
  python tools/output_formatter.py --format <text|json|junit>
  ```

---

### 100. `tools/repo_map.py` (Enterprise Repository Map Compressor & Context Optimizer)
- **Purpose:** Builds compressed AST repository maps ranking Page Classes, helper methods, and entrypoints to give agents high-density context under 2,000 tokens.
- **Trigger Condition:** Context optimization, agent exploration, anti-context-blowout guard.
- **CLI Syntax:**
  ```bash
  python tools/repo_map.py [output_file] [--max-tokens 2048]
  ```

---

### 101. `tools/safety_firewall.py` (Action Safety Firewall & Blast Radius Containment Engine)
- **Purpose:** Non-bypassable action firewall intercepting and blocking destructive operations (`DROP DATABASE`, `rm -rf`, `git push --force`) in agent workflows.
- **Trigger Condition:** Safety guardrail during tool dispatch and command execution.
- **CLI Syntax:**
  ```bash
  python tools/safety_firewall.py check "<command>"
  ```

---

### 102. `tools/setup_project.py` (Enterprise Autonomous Project Setup & Bootstrap Engine)
- **Purpose:** Zero-command autonomous project bootstrapper tailoring AI agent guides, rules, and pre-commit hooks to the target repository stack.
- **Trigger Condition:** Onboarding new repositories to Synapse Hub QA standards.
- **CLI Syntax:**
  ```bash
  python tools/setup_project.py [target_directory]
  # or via CLI
  agent-qa setup
  ```

---

### 103. `tools/skillspector.py` (Enterprise SkillSpector AI Agent & MCP Security Scanner)
- **Purpose:** Security scanner inspecting agent skill markdown files, prompts, and MCP configurations against 71 vulnerability vectors (prompt injection, obfuscation, dangerous commands).
- **Trigger Condition:** Gate 9 pre-flight, skill auditing, hub publishing verification.
- **CLI Syntax:**
  ```bash
  python tools/skillspector.py <skills_dir_or_file>
  # or via CLI
  agent-qa skillspector [path]
  ```

---

### 104. `tools/sync_agent_rules.py` (Unified AGENTS.md Rule Synchronizer for AI IDE Bridges)
- **Purpose:** Single-source-of-truth compiler generating bridge rule files (`CLAUDE.md`, `.cursorrules`, `.windsurfrules`, `.cursor/rules/synapse-qa.mdc`) from `AGENTS.md`.
- **Trigger Condition:** Updating `AGENTS.md`, pre-push verification (`--check`), IDE bridge generation.
- **CLI Syntax:**
  ```bash
  python tools/sync_agent_rules.py [--check]
  ```

---

### 105. `tools/telemetry_correlator.py` (Full-Stack APM & Server Telemetry Performance Correlator)
- **Purpose:** Correlates client-side test execution latencies with server hardware telemetry (CPU, RAM, DB pool) to pinpoint performance bottlenecks.
- **Trigger Condition:** Performance testing analysis, spike triage, load testing correlation.
- **CLI Syntax:**
  ```bash
  python tools/telemetry_correlator.py --jtl <results.jtl> --telemetry <metrics.csv>
  ```

---

### 106. `tools/trace_data_flow.py` (Universal Data Flow & Teardown Tracer)
- **Purpose:** Taint analysis tracer mapping test entity creation to teardown deletion paths, ensuring zero database pollution.
- **Trigger Condition:** Verifying idempotent test teardown compliance and entity lifecycles.
- **CLI Syntax:**
  ```bash
  python tools/trace_data_flow.py <test_file_or_dir>
  ```

---

### 107. `tools/validate_groovy_scripts.py` (Pre-Check AST Validator for Groovy Scripts & Keywords)
- **Purpose:** Static AST syntax and pattern validator for Katalon/Groovy test scripts, ensuring clean POM adherence, valid imports, and no forbidden patterns.
- **Trigger Condition:** Pre-commit Katalon validation and CI pipeline gate.
- **CLI Syntax:**
  ```bash
  python tools/validate_groovy_scripts.py <script_dir>
  ```

---

### 108. `tools/welcome_page.py` (Interactive Visual Landing Page & Hub Command Launcher)
- **Purpose:** Generates and serves the interactive HTML landing page showcasing Synapse Hub features, quick-start guides, and command palettes.
- **Trigger Condition:** Launching the Hub welcome dashboard for human users.
- **CLI Syntax:**
  ```bash
  python tools/welcome_page.py [--open-browser]
  ```

---

### 109. `tools/skill_profiles.py` (AI Agent Skill Capability Profile Manager)
- **Purpose:** Filters, lists, and exports the 53 standardized AI Agent skills across the 4 core capability profiles (`core-web-qa`, `perf-and-load`, `api-security`, `enterprise-rbt`).
- **Trigger Condition:** Filtering skill catalogs, inspecting capability profiles, or executing `agent-qa skills` / `synapse-hub skills`.
- **CLI Syntax:**
  ```bash
  # 1. List all 4 core capability profiles with descriptions and skill counts
  python tools/skill_profiles.py --list-profiles

  # 2. Filter skills in a capability profile (text table or JSON)
  python tools/skill_profiles.py --profile core-web-qa
  python tools/skill_profiles.py --profile api-security --format json

  # 3. Via central CLI
  agent-qa skills --list-profiles
  agent-qa skills -p perf-and-load
  ```


