# Synapse Hub — Tooling Ecosystem Catalog & Runbook

> **Audience:** QA Engineers, Autonomous AI Agents (Lead Orchestrator, POM-Crafter, Test-Runner, Failure-Analyst, Quality-Gatekeeper).
> **Total Tools Cataloged:** `111` | **Stable:** `111` | **Experimental:** `0`

## 1. Primary Enterprise CLI Tools

| Command | Category | Owner Role | Status | Risk Level | Description |
|---|---|:---:|:---:|:---:|---|
| `python tools/_openapi_parser.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/_openapi_parser.py — Shared OpenAPI & Swagger Specification Parser |
| `python tools/agent_canary.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | ENTERPRISE AUTONOMOUS AGENT Canary & Mutation Testing Arena |
| `python tools/agentless_patcher.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Agentless 3-Stage Deterministic Patcher (OpenAutoCoder Agentless Pattern) |
| `python tools/analyze_project.py` | **Quality Gates** | `quality-gatekeeper` | 🟢 Stable | `read_only` | Comprehensive health audit analyzing environment, POM structure, and Quality Gates. |
| `python tools/api_drift_sentinel.py` | **API & Contract Testing** | `api-engineer` | 🟢 Stable | `read_only` | Detects contract drift and breaking schema mutations against OpenAPI specifications. |
| `python tools/api_fuzzer.py` | **Testing & Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Autonomous API Fuzzing & Chaos Breaker |
| `python tools/author_integrity.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/author_integrity.py — Author Attribution & MIT License Compliance Guard |
| `python tools/auto_heal.py` | **Failure Autopsy & Healing** | `failure-analyst` | 🟢 Stable | `modifying` | Closed-loop locator self-healing engine matching broken selectors against DOM/AOM. |
| `python tools/auto_heal_reflexion.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Multi-Trial Episodic Reflexion Loop for Autonomous Healing (Noah Shinn / Reflexion Pattern) |
| `python tools/autogen_qa_broker.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Asynchronous Actor QA Message Broker (Microsoft AutoGen v0.4+ Pattern) |
| `python tools/benchmark_swarm_context.py` | **Benchmarking** | `orchestrator` | 🟢 Stable | `read_only` | Empirical context token reduction benchmark harness proving >= 40% savings. |
| `python tools/browsergym_eval.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | BrowserGym Web Agent Benchmark Harness (BrowserGym / WebArena Pattern) |
| `python tools/bug_reporter.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Auto-Bug Reporter & Root Cause Analysis (RCA) Ticket Generator |
| `python tools/bump_version.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/bump_version.py — Atomic Universal Version Bumper for Synapse Hub |
| `python tools/cache_resolver.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Universal Local Semantic Memory Cache & Self-Healing Resolver |
| `python tools/check_env.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | ============================================================================== |
| `python tools/check_version_sync.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/check_version_sync.py — Version Synchronization Sentinel for Synapse Hub |
| `python tools/ci_healing_hook.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | CI/CD Silent Self-Healing Pipeline Hook |
| `python tools/cli.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Agent-QA CLI Entrypoint |
| `python tools/config_decoupler.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Environment & Secret Decoupling Engine |
| `python tools/contract_validator.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Swarm Data Contract Validator (Single Front-Door Integrity Guard) |
| `python tools/count_tokens.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Cross-Platform Token & Cost Auditor (Synapse-Hub) |
| `python tools/create_mock_docx.py` | **Testing & Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Generates a lightweight valid mock DOCX fixture (< 20 KB) for OpenXML Guard / Word reader tests. |
| `python tools/dashboard_generator.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/dashboard_generator.py — Standalone One-Page Enterprise QA HTML Dashboard |
| `python tools/db_sandbox.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Zero-Pollution Database Sandbox & Ephemeral Teardown Engine |
| `python tools/debt_harvester.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/debt_harvester.py — Technical Debt & Shortcut Harvester |
| `python tools/distill_log.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/distill_log.py — Cross-Platform Log Distiller for Katalon KRE, Gradle, and Playwright |
| `python tools/dspy_qa_signatures.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Declarative QA Signature Compilation Engine (Stanford DSPy Pattern) |
| `python tools/e2e_flow_prober.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise E2E Flow Prober & XPath Crawler Dispatcher (Cross-Platform) |
| `python tools/export_postman_collection.py` | **API & Contract Testing** | `api-engineer` | 🟢 Stable | `read_only` | Exports API test matrices into runnable Postman Collections with pre-request scripts. |
| `python tools/flaky_detector.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Flaky Test Detector & Quarantine Sentinel |
| `python tools/fsm_enforcer.py` | **Orchestration** | `orchestrator` | 🟢 Stable | `modifying` | 5-Stage QA Multi-Agent Finite State Machine enforcer with cryptographic proof tokens. |
| `python tools/fsm_middleware.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Runtime FSM Interceptor & Tool Proxy Middleware |
| `python tools/fuzz_payloads.py` | **Testing & Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Edge-Case Fuzzing & Input Sanitization Payload Catalog |
| `python tools/generate_allure_report.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Allure HTML Report Generator (Cross-Platform) |
| `python tools/generate_api_matrix.py` | **API & Contract Testing** | `api-engineer` | 🟢 Stable | `read_only` | Converts OpenAPI/Swagger specs into automated positive, boundary, and negative test matrices. |
| `python tools/generate_jmx_plan.py` | **Performance Testing** | `perf-engineer` | 🟢 Stable | `read_only` | Enterprise Apache JMeter 5.x & Locust test plan generator from OpenAPI/Postman/HAR specs. |
| `python tools/generate_sbom.py` | **Security** | `orchestrator` | 🟢 Stable | `read_only` | Standard SPDX 2.3 JSON Software Bill of Materials (SBOM) generator for software supply chain security. |
| `python tools/generate_tc_from_story.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/generate_tc_from_story.py — Large Action Model (LAM) Script Generator |
| `python tools/generate_test_reports.py` | **Testing & Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Test Report Aggregator & summaryTemp Generator (Cross-Platform) |
| `python tools/generate_tool_catalog.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/generate_tool_catalog.py — Enterprise Tooling Ecosystem Catalog Generator |
| `python tools/gherkin_suite.py` | **Manual Testing & Design** | `test-designer` | 🟢 Stable | `read_only` | Compiles Gherkin .feature specs into expanded test matrices and coverage reports. |
| `python tools/git_pre_commit_guard.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Git Pre-Commit Architecture & Discipline Guard |
| `python tools/goldfish_review.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/goldfish_review.py — Zero-Context Test Specification Reviewer |
| `python tools/heal_pr_automator.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Self-Healing Confidence Scorer & PR Automator |
| `python tools/heuristic_locator_matcher.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | 3-Layer Heuristic Locator Matcher (0-Token Autonomous Recovery) |
| `python tools/hub_publisher.py` | **CI/CD & Packaging** | `orchestrator` | 🟢 Stable | `modifying` | Autonomous 1-click 5-step release pipeline for Synapse Hub. |
| `python tools/humanize_linter.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Humanize & Anti-AI Slop Linter (Enterprise QA Hub) |
| `python tools/infer_linter.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Universal QA Static Defect & Assertion Sentinel (Inspired by facebook/infer) |
| `python tools/init_config.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/init_config.py — Standardized Project Configuration Bootstrapper |
| `python tools/interview_story.py` | **Manual Testing & Design** | `test-designer` | 🟢 Stable | `read_only` | Interactive requirement interrogation engine surfacing hidden assumptions and ambiguous acceptance criteria. |
| `python tools/jira_sync.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/jira_sync.py — Jira / Xray / Zephyr Enterprise 2-Way Synchronization Engine |
| `python tools/jtl_analyzer.py` | **Performance Testing** | `perf-engineer` | 🟢 Stable | `read_only` | Sub-0.1s Apache JMeter JTL results analyzer enforcing automated CI/CD SLA quality gates. |
| `python tools/lint_ai_docs.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise AI Documentation & Artifact Linter (Anti-Drift Guard v2.0) |
| `python tools/lookup_tc.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise QA: Fast Test Case Metadata Lookup (lookup_tc.py) |
| `python tools/lookup_xpath.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise QA: Fast XPath / Selector Lookup (lookup_xpath.py) |
| `python tools/matrix_sharder.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Duration-Balanced Test Matrix Sharder |
| `python tools/mcp_docx_server.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Cross-Platform MCP Docx Server (Zero-Dependency) |
| `python tools/mcp_excel_server.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Cross-Platform MCP Excel Server (Zero-Dependency) |
| `python tools/mcp_server.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Model Context Protocol (MCP) Standard Server |
| `python tools/md_to_xlsx.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Markdown to Excel (.xlsx) Enterprise Converter |
| `python tools/micro_mutator.py` | **Quality Gates** | `quality-gatekeeper` | 🟢 Stable | `read_only` | Syntactic micro-mutation sentinel eliminating tautological tests and measuring assertion sensitivity. |
| `python tools/mipro_assertion_tuner.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | MIPROv2 Prompt Assertion Tuner (Stanford DSPy v2 & Optuna TPE Pattern) |
| `python tools/network_mock_shield.py` | **API & Contract Testing** | `api-engineer` | 🟢 Stable | `modifying` | Network interception shield stubbing external routes and injecting chaos network faults. |
| `python tools/newman_analyzer.py` | **API & Contract Testing** | `api-engineer` | 🟢 Stable | `read_only` | Sub-0.1s Postman/Newman JSON test report analyzer enforcing CI/CD quality gates. |
| `python tools/omni_emitter.py` | **Code Generation & AST** | `pom-crafter` | 🟢 Stable | `read_only` | Universal polyglot code generator emitting Clean POM Flat Architecture scripts. |
| `python tools/omni_parser.py` | **Code Generation & AST** | `pom-crafter` | 🟢 Stable | `read_only` | Deterministic 0-token polyglot AST parser extracting Page Classes and test workflows. |
| `python tools/omni_transpiler.py` | **Code Generation & AST** | `pom-crafter` | 🟢 Stable | `modifying` | Instant 0-token transpiler between Playwright, Selenium, and Katalon. |
| `python tools/openxml_guard.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | OpenXML Security & Protocol Defense Guard |
| `python tools/output_formatter.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Standardized Output Formatter & Exit Code Specification |
| `python tools/package_release.py` | **CI/CD & Packaging** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise release packager preserving .github/workflows and generating SHA-256 provenance. |
| `python tools/pinpoint_failure.py` | **Failure Autopsy & Healing** | `failure-analyst` | 🟢 Stable | `read_only` | Sub-0.1s JUnit XML autopsy parser diagnosing test crashes without LLM token waste. |
| `python tools/project_state.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Project State Machine & Token-Capped Memory Anchor |
| `python tools/qa_event_stream.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Immutable QA Event Stream Engine (OpenHands EventStream Pattern) |
| `python tools/repo_map.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Repository Map Compressor (Inspired by Aider-AI/aider) |
| `python tools/reversible_sandbox.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Reversible Execution Sandbox & Automated Teardown Engine (GoEx Pattern) |
| `python tools/safety_firewall.py` | **Security** | `quality-gatekeeper` | 🟢 Stable | `read_only` | Non-bypassable safety firewall blocking destructive operations (drop database, git push force, rm -rf). |
| `python tools/security_coverage_ledger.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Mathematical Security Coverage Ledger & Audit Tracker |
| `python tools/security_scanner.py` | **Security** | `quality-gatekeeper` | 🟢 Stable | `read_only` | Comprehensive enterprise security sentinel auditing Python & NPM dependencies and threat-model defense. |
| `python tools/senior_code_review.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/senior_code_review.py — Senior Developer Quality & Lean Diff Reviewer |
| `python tools/setup_project.py` | **Setup & Onboarding** | `orchestrator` | 🟢 Stable | `modifying` | Zero-command automated project bootstrap tailoring AI agent rules to the target stack. |
| `python tools/skill_collision_guard.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Tier-2 Skill Routing & Collision Guard (Addy Osmani Pattern) |
| `python tools/skill_profiles.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/skill_profiles.py — Skill Catalog Capability Profile Manager |
| `python tools/skill_vault.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | SkillVault Lifelong Page Object Model & Interaction Library (MineDojo / Voyager Pattern) |
| `python tools/skillspector.py` | **Security** | `quality-gatekeeper` | 🟢 Stable | `read_only` | Security scanner detecting prompt injection, Unicode obfuscation, and dangerous CLI tools. |
| `python tools/smart_visual_masker.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Smart Visual Masker & Anti-Flake Visual Engine |
| `python tools/spec_drift_sentinel.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/spec_drift_sentinel.py — Spec-to-Code Drift Sentinel |
| `python tools/swe_qa_aci.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | QA Agent-Computer Interface (SWE-agent ACI Pattern) |
| `python tools/synapse_observer.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Synapse Cognitive Observer & Tradeoff Sentinel |
| `python tools/synapse_qa_bench.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Synapse-QA-Bench: Tool Function Calling Benchmark (Gorilla BFCL Pattern) |
| `python tools/sync_agent_rules.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/sync_agent_rules.py — Synchronizes AGENTS.md single-source rules to all AI bridges |
| `python tools/telemetry_correlator.py` | **Performance Testing** | `perf-engineer` | 🟢 Stable | `read_only` | Full-stack APM & server telemetry performance correlator linking client latencies with server hardware. |
| `python tools/template_excel_exporter.py` | **Manual Testing & Design** | `test-designer` | 🟢 Stable | `modifying` | Enterprise template-driven Excel test case exporter with dropdown Data Validation. |
| `python tools/test_impact.py` | **Testing & Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Universal Test Impact Analyzer (Graphify AST-Powered) |
| `python tools/test_memory_os.py` | **Testing & Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Hierarchical QA Test Memory OS (Letta / MemGPT Pattern) |
| `python tools/textgrad_mutation_optimizer.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Mutant-Directed Textual Loss Optimizer (Deterministic TextGrad-Style Heuristic) |
| `python tools/tms_sync_bridge.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise ALM & TMS Sync Bridge (Jira / Xray / Zephyr / TestRail) |
| `python tools/tot_exploratory_tester.py` | **Manual Testing & Design** | `test-designer` | 🟢 Stable | `read_only` | Tree-of-Thoughts exploratory scenario generator with risk scoring and boundary decomposition. |
| `python tools/trace_data_flow.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Universal Data Flow & Teardown Tracer (Taint Analysis) |
| `python tools/traffic_session_converter.py` | **API & Contract Testing** | `api-engineer` | 🟢 Stable | `read_only` | Converts recorded HAR traffic sessions into executable API automation test cases. |
| `python tools/trend_analytics.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/trend_analytics.py — Historical Quality Trend & Flakiness Analytics Engine |
| `python tools/ui_server.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/ui_server.py — Synapse Hub Interactive QA Mission Control Web Server |
| `python tools/universal_ir.py` | **Code Generation & AST** | `pom-crafter` | 🟢 Stable | `read_only` | Language-agnostic and framework-agnostic AST data model for automated test suites. |
| `python tools/update_sentinel.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Synapse-Hub Auto-Update & Version Drift Sentinel |
| `python tools/validate_groovy_scripts.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Pre-check validator for Groovy scripts and POM keywords in enterprise test suites. |
| `python tools/verify_all.py` | **Quality Gates** | `quality-gatekeeper` | 🟢 Stable | `read_only` | One-command 10 Quality Gates Definition of Done (DoD) verification sentinel. |
| `python tools/visual_diff_canvas.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Canvas Visual Diff & Regression Checker |
| `python tools/visual_som_helper.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Vision-Grounded Fallback & Set-of-Marks (SoM) Engine |
| `python tools/watch_mode.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/watch_mode.py — Incremental Watch Mode & Real-Time Test Engineering HUD |
| `python tools/wcag_audit.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/wcag_audit.py - Automated Accessibility (WCAG 2.2) Linter & Auditor |
| `python tools/welcome_page.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/welcome_page.py — Interactive Visual Landing Page for Synapse Hub |

## 2. Risk & Operational Classification

- `read_only`: Diagnostic, linting, AST inspection, reporting (zero side effects on workspace or git).
- `modifying`: Generates files, updates Page Classes, or writes test suites.
- `network`: Queries external APIs, monitors npm registry, or checks live URLs.
- `destructive`: High-impact actions guarded by `safety_firewall.py` (e.g. drop database, hard resets).

*Catalog generated: `2026-11-12T08:56:38.327652+00:00` by `tools/generate_tool_catalog.py`*