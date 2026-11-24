# Synapse Hub — Tooling Ecosystem Catalog & Runbook

> **Audience:** QA Engineers, Autonomous AI Agents (Lead Orchestrator, POM-Crafter, Test-Runner, Failure-Analyst, Quality-Gatekeeper).
> **Total Tools Cataloged:** `166` | **Stable:** `164` | **Experimental:** `2`

## 1. Primary Enterprise CLI Tools

| Command | Category | Owner Role | Status | Risk Level | Description |
|---|---|:---:|:---:|:---:|---|
| `python tools/api/_openapi_parser.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/api/_openapi_parser.py — Shared OpenAPI & Swagger Specification Parser |
| `python tools/core/adapters.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/core/adapters.py — Unified Memory Bus Bridges & Adapters |
| `python tools/lint/agent_canary.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | ENTERPRISE AUTONOMOUS AGENT Canary & Mutation Testing Arena |
| `python tools/heal/agentless_patcher.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `modifying` | Agentless 3-Stage Deterministic Patcher (OpenAutoCoder Agentless Pattern) |
| `python tools/lint/ai_eval_sentinel.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/lint/ai_eval_sentinel.py — Enterprise RAG & LLM Evaluation Sentinel (NIST AI RMF & ISO 42001) |
| `python tools/core/analyze_project.py` | **Quality Gates** | `quality-gatekeeper` | 🟢 Stable | `read_only` | Comprehensive health audit analyzing environment, POM structure, and Quality Gates. |
| `python tools/api/api_drift_sentinel.py` | **API & Contract Testing** | `api-engineer` | 🟢 Stable | `read_only` | Detects contract drift and breaking schema mutations against OpenAPI specifications. |
| `python tools/api/api_fuzzer.py` | **Testing & Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Autonomous API Fuzzing & Chaos Breaker |
| `python tools/heal/assertion_optimizer.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/heal/assertion_optimizer.py — Unified Assertion Optimization & Tuning Suite |
| `python tools/heal/ast_assertion_optimizer.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | AST-Directed Assertion Optimizer (Syntactic Mutation Feedback Loop) |
| `python tools/context/ast_cache.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/context/ast_cache.py — AST Dataflow Pre-Validation Cache (Boost B3) |
| `python tools/security/asvs_auditor.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/security/asvs_auditor.py — OWASP Application Security Verification Standard (ASVS 4.0.3) Engine |
| `python tools/core/author_integrity.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/core/author_integrity.py — Author Attribution & Repository Provenance Guard |
| `python tools/heal/auto_heal.py` | **Failure Autopsy & Healing** | `failure-analyst` | 🟢 Stable | `modifying` | Closed-loop locator self-healing engine matching broken selectors against DOM/AOM. |
| `python tools/heal/auto_heal_reflexion.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `modifying` | Multi-Trial Episodic Reflexion Loop for Autonomous Healing (Noah Shinn / Reflexion Pattern) |
| `python tools/orchestration/autogen_qa_broker.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Asynchronous Actor QA Message Broker (Microsoft AutoGen v0.4+ Pattern) |
| `python tools/perf/benchmark_perf_runner.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/perf/benchmark_perf_runner.py — Synthetic Local Performance Benchmark Runner |
| `python tools/context/benchmark_swarm_context.py` | **Benchmarking** | `orchestrator` | 🟢 Stable | `read_only` | Empirical context token reduction benchmark harness proving >= 40% savings. |
| `python tools/core/bm25_retriever.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/core/bm25_retriever.py — Zero-Dependency Pure Python BM25 Knowledge Retriever |
| `python tools/design/break_ui_generator.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/design/break_ui_generator.py — Edge-Case UI Stress Testing Data Generator |
| `python tools/orchestration/browsergym_eval.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | BrowserGym Web Agent Benchmark Harness (BrowserGym / WebArena Pattern) |
| `python tools/report/bug_reporter.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Auto-Bug Reporter & Root Cause Analysis (RCA) Ticket Generator |
| `python tools/core/bump_version.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `modifying` | tools/core/bump_version.py — Atomic Universal Version Bumper for Synapse Hub |
| `python tools/core/cache_resolver.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Universal Local Semantic Memory Cache & Self-Healing Resolver |
| `python tools/perf/chaos_resilience_probe.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/perf/chaos_resilience_probe.py — Enterprise Chaos Engineering & Reliability Sentinel |
| `python tools/core/check_env.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | ============================================================================== |
| `python tools/core/check_version_sync.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `modifying` | tools/core/check_version_sync.py — Version Synchronization Sentinel for Synapse Hub |
| `python tools/heal/ci_healing_hook.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `modifying` | CI/CD Silent Self-Healing Pipeline Hook |
| `python tools/core/circuit_breaker.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Synapse Hub — In-Flight Token Circuit Breaker & Model Cascade Engine |
| `python tools/contrib/cldr_l10n_verifier.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/contrib/cldr_l10n_verifier.py — Enterprise Unicode CLDR & L10n/I18n Verification Engine |
| `python tools/core/cli.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Agent-QA CLI Entrypoint |
| `python tools/core/cli_runtime.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Shared CLI Runtime Utilities for Synapse-Hub Tools |
| `python tools/core/codemod_tool_imports.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/core/codemod_tool_imports.py |
| `python tools/core/config_decoupler.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Environment & Secret Decoupling Engine |
| `python tools/context/context_slicer.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/context/context_slicer.py — Tier 3 AST-Aware Micro-Context & Skeleton Slicer |
| `python tools/api/contract_validator.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Swarm Data Contract Validator (Single Front-Door Integrity Guard) |
| `python tools/core/count_tokens.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Cross-Platform Token & Cost Auditor (Synapse-Hub) |
| `python tools/report/coverage_reporter.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/report/coverage_reporter.py — Standardized Coverage Metrics & Roadmap Evaluator |
| `python tools/security/cvss_calculator.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/security/cvss_calculator.py — Enterprise Common Vulnerability Scoring System Engine |
| `python tools/contrib/dashboard_generator.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/contrib/dashboard_generator.py — Standalone One-Page Enterprise QA HTML Dashboard |
| `python tools/core/db_sandbox.py` | **Sandboxing & Isolation** | `failure-analyst` | 🟢 Stable | `modifying` | Database state isolation sentinel with granular consent-governed snapshot and purge capabilities. |
| `python tools/core/debt_harvester.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/core/debt_harvester.py — Technical Debt & Shortcut Harvester |
| `python tools/contrib/diagram_architect.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/contrib/diagram_architect.py — Standalone Self-Contained SVG & HTML Diagram Builder |
| `python tools/core/distill_log.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/core/distill_log.py — Enterprise Multi-Framework Log Distiller (Token & Failure Sentinel) |
| `python tools/core/distill_skill.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `destructive` | tools/core/distill_skill.py — Dual-Skill Distillation Engine |
| `python tools/orchestration/dspy_qa_signatures.py` | **Auxiliary Utilities** | `orchestrator` | 🟡 Exp | `read_only` | Deprecated compatibility shim. |
| `python tools/api/e2e_flow_prober.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise E2E Flow Prober & XPath Crawler Dispatcher (Cross-Platform) |
| `python tools/contrib/etl_data_reconciler.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/contrib/etl_data_reconciler.py — Enterprise Data Quality & ETL Reconciliation Engine |
| `python tools/contrib/export_postman_collection.py` | **API & Contract Testing** | `api-engineer` | 🟢 Stable | `read_only` | Exports API test matrices into runnable Postman Collections with pre-request scripts. |
| `python tools/core/file_lock.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Cross-Platform Advisory File Locking (tools.core.file_lock) |
| `python tools/lint/flaky_detector.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Flaky Test Detector & Quarantine Sentinel |
| `python tools/core/fsm_enforcer.py` | **Orchestration** | `orchestrator` | 🟢 Stable | `modifying` | 5-Stage QA Multi-Agent Finite State Machine enforcer with cryptographic proof tokens. |
| `python tools/core/fsm_middleware.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Runtime FSM Interceptor & Tool Proxy Middleware |
| `python tools/api/fuzz_payloads.py` | **Testing & Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Edge-Case Fuzzing & Input Sanitization Payload Catalog |
| `python tools/report/generate_allure_report.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Allure HTML Report Generator (Cross-Platform) |
| `python tools/api/generate_api_matrix.py` | **API & Contract Testing** | `api-engineer` | 🟢 Stable | `read_only` | Converts OpenAPI/Swagger specs into automated positive, boundary, and negative test matrices. |
| `python tools/contrib/generate_jmx_plan.py` | **Performance Testing** | `perf-engineer` | 🟢 Stable | `read_only` | Enterprise Apache JMeter 5.x & Locust test plan generator from OpenAPI/Postman/HAR specs. |
| `python tools/report/generate_sbom.py` | **Security** | `orchestrator` | 🟢 Stable | `read_only` | Standard SPDX 2.3 JSON Software Bill of Materials (SBOM) generator for software supply chain security. |
| `python tools/contrib/generate_tc_from_story.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/contrib/generate_tc_from_story.py — Large Action Model (LAM) Script Generator |
| `python tools/report/generate_test_reports.py` | **Testing & Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Test Report Aggregator & summaryTemp Generator (Cross-Platform) |
| `python tools/report/generate_tool_catalog.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/report/generate_tool_catalog.py — Enterprise Tooling Ecosystem Catalog Generator |
| `python tools/transpiler/gherkin_suite.py` | **Manual Testing & Design** | `test-designer` | 🟢 Stable | `read_only` | Compiles Gherkin .feature specs into expanded test matrices and coverage reports. |
| `python tools/lint/git_pre_commit_guard.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Git Pre-Commit Architecture & Discipline Guard |
| `python tools/core/git_worktree_manager.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/core/git_worktree_manager.py — Ephemeral Git Worktree Manager for Subagents |
| `python tools/orchestration/goldfish_review.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/orchestration/goldfish_review.py — Zero-Context Test Specification Reviewer |
| `python tools/heal/heal_pr_automator.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `modifying` | Enterprise Self-Healing Confidence Scorer & PR Automator |
| `python tools/perf/heap_leak_analyzer.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/perf/heap_leak_analyzer.py — Client-Side Memory Leak Sentinel & Heap Analyzer |
| `python tools/heal/heuristic_locator_matcher.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | 3-Layer Heuristic Locator Matcher (0-Token Autonomous Recovery) |
| `python tools/core/hub_publisher.py` | **CI/CD & Packaging** | `orchestrator` | 🟢 Stable | `modifying` | Autonomous 1-click 5-step release pipeline for Synapse Hub. |
| `python tools/lint/humanize_linter.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Humanize & Anti-AI Slop Linter (Enterprise QA Hub) |
| `python tools/core/i18n.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Synapse Hub — Bilingual Internationalization Engine (tools.core.i18n) |
| `python tools/lint/infer_linter.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Universal QA Static Defect & Assertion Sentinel (Inspired by facebook/infer) |
| `python tools/core/init_config.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/core/init_config.py — Standardized Project Configuration Bootstrapper |
| `python tools/contrib/interview_story.py` | **Manual Testing & Design** | `test-designer` | 🟢 Stable | `read_only` | Interactive requirement interrogation engine surfacing hidden assumptions and ambiguous acceptance criteria. |
| `python tools/contrib/jira_sync.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `modifying` | tools/contrib/jira_sync.py — Jira / Xray / Zephyr Enterprise 2-Way Synchronization Engine |
| `python tools/perf/jtl_analyzer.py` | **Performance Testing** | `perf-engineer` | 🟢 Stable | `read_only` | Sub-0.1s Apache JMeter JTL results analyzer enforcing automated CI/CD SLA quality gates. |
| `python tools/lint/lint_ai_docs.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise AI Documentation & Artifact Linter (Anti-Drift Guard v2.0) |
| `python tools/heal/live_visual_healer.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `modifying` | Live Visual Healer & Playwright Grounding Bridge |
| `python tools/context/lookup_tc.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise QA: Fast Test Case Metadata Lookup (lookup_tc.py) |
| `python tools/heal/lookup_xpath.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise QA: Fast XPath / Selector Lookup (lookup_xpath.py) |
| `python tools/orchestration/matrix_sharder.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Duration-Balanced Test Matrix Sharder |
| `python tools/mcp/mcp_docx_server.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Cross-Platform MCP Docx Server (Zero-Dependency) |
| `python tools/mcp/mcp_excel_server.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Cross-Platform MCP Excel Server (Zero-Dependency) |
| `python tools/mcp/mcp_server.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Model Context Protocol (MCP) Standard Server |
| `python tools/contrib/md_to_xlsx.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Markdown to Excel (.xlsx) Enterprise Converter |
| `python tools/design/mechanical_ui_gate.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/design/mechanical_ui_gate.py — Headless Chrome Mechanical Layout & Contrast Gate |
| `python tools/core/memory_bus.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/core/memory_bus.py — Unified QA Memory Bus Architecture |
| `python tools/lint/micro_mutator.py` | **Quality Gates** | `quality-gatekeeper` | 🟢 Stable | `read_only` | Syntactic micro-mutation sentinel eliminating tautological tests and measuring assertion sensitivity. |
| `python tools/lint/mipro_assertion_tuner.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | MIPROv2 Prompt Assertion Tuner (Bayesian Instruction & TPE Pattern) |
| `python tools/perf/mobile_resilience_sentinel.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/perf/mobile_resilience_sentinel.py — Mobile Hardware Interrupts, MASVS & HIG Sentinel |
| `python tools/api/network_mock_shield.py` | **API & Contract Testing** | `api-engineer` | 🟢 Stable | `modifying` | Network interception shield stubbing external routes and injecting chaos network faults. |
| `python tools/perf/newman_analyzer.py` | **API & Contract Testing** | `api-engineer` | 🟢 Stable | `read_only` | Sub-0.1s Postman/Newman JSON test report analyzer enforcing CI/CD quality gates. |
| `python tools/perf/observability_tester.py` | **Testing & Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/perf/observability_tester.py — OpenTelemetry Trace & Log Hygiene Verification Sentinel |
| `python tools/transpiler/omni_emitter.py` | **Code Generation & AST** | `pom-crafter` | 🟢 Stable | `read_only` | Universal polyglot code generator emitting Clean POM Flat Architecture scripts. |
| `python tools/transpiler/omni_parser.py` | **Code Generation & AST** | `pom-crafter` | 🟢 Stable | `read_only` | Deterministic 0-token polyglot AST parser extracting Page Classes and test workflows. |
| `python tools/transpiler/omni_transpiler.py` | **Code Generation & AST** | `pom-crafter` | 🟢 Stable | `modifying` | Instant 0-token transpiler between Playwright, Selenium, and Katalon. |
| `python tools/contrib/openxml_guard.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | OpenXML Security & Protocol Defense Guard |
| `python tools/report/output_formatter.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Standardized Output Formatter & Exit Code Specification |
| `python tools/core/package_release.py` | **CI/CD & Packaging** | `orchestrator` | 🟢 Stable | `modifying` | Enterprise release packager preserving .github/workflows and generating SHA-256 provenance. |
| `python tools/api/pairwise_generator.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/api/pairwise_generator.py — Pairwise (2-Way) Combinatorial Test Case Generator |
| `python tools/contrib/payment_interop_simulator.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/contrib/payment_interop_simulator.py — ISO 8583 & Financial Gateway Interoperability Sentinel |
| `python tools/security/pentest_scope_guard.py` | **Testing & Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/security/pentest_scope_guard.py — Enterprise Pentest Scope & DAST Runtime Guard |
| `python tools/report/pinpoint_failure.py` | **Failure Autopsy & Healing** | `failure-analyst` | 🟢 Stable | `read_only` | Sub-0.1s JUnit XML autopsy parser diagnosing test crashes without LLM token waste. |
| `python tools/lint/pre_bash_guard.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/lint/pre_bash_guard.py — Active Pre-Tool Shell Guard (Inspired by Oven Bun pre-bash-guard) |
| `python tools/lint/pre_push_guard.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `modifying` | Pre-Push Quality & Anti-Hallucination Guard (Multi-Session Audit) |
| `python tools/core/process_supervisor.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `modifying` | Reusable Process Group Supervisor & Zombie Process Reaper (tools.core.process_supervisor) |
| `python tools/core/project_state.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Project State Machine & Token-Capped Memory Anchor |
| `python tools/core/provider_usage_adapter.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/core/provider_usage_adapter.py — Standardized Provider Usage Ingestion & Context Splitter |
| `python tools/orchestration/qa_event_stream.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Immutable QA Event Stream Engine (OpenHands EventStream Pattern) |
| `python tools/security/regulatory_compliance.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/security/regulatory_compliance.py — Enterprise Regulatory & Compliance Audit Sentinel |
| `python tools/core/repo_map.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Repository Map Compressor (Inspired by Aider-AI/aider) |
| `python tools/heal/reversible_sandbox.py` | **Sandboxing & Isolation** | `failure-analyst` | 🟢 Stable | `modifying` | Two-phase commit write-ahead logging (WAL) execution sandbox providing crash-resilient rollback guarantees. |
| `python tools/core/rule_harvester.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/core/rule_harvester.py — Dynamic Rule & Episodic Learning Harvester (Level 4 Adaptive Hub) |
| `python tools/core/rules_router.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/core/rules_router.py — Progressive Rules Router & Context Optimizer (Boost B2) |
| `python tools/orchestration/runaway_stopper.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/orchestration/runaway_stopper.py — Agent Runaway & Token Loop Sentinel (Stub / Re-export) |
| `python tools/security/safety_firewall.py` | **Security** | `quality-gatekeeper` | 🟢 Stable | `read_only` | Non-bypassable safety firewall blocking destructive operations (drop database, git push force, rm -rf). |
| `python tools/security/security_coverage_ledger.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Mathematical Security Coverage Ledger & Audit Tracker |
| `python tools/security/security_scanner.py` | **Security** | `quality-gatekeeper` | 🟢 Stable | `read_only` | Comprehensive enterprise security sentinel auditing Python & NPM dependencies and threat-model defense. |
| `python tools/orchestration/senior_code_review.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/orchestration/senior_code_review.py — Senior Developer Quality & Lean Diff Reviewer |
| `python tools/core/session_vault.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Session State & Authentication Vault (Zero-Second Auth Bridge) |
| `python tools/core/setup_project.py` | **Setup & Onboarding** | `orchestrator` | 🟢 Stable | `modifying` | Zero-command automated project bootstrap tailoring AI agent rules to the target stack. |
| `python tools/core/skill_canonical_digest.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `destructive` | tools/core/skill_canonical_digest.py — Single Source of Truth for Skill Canonical Digest & Lockfile Integrity |
| `python tools/lint/skill_collision_guard.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `destructive` | Tier-2 Skill Routing & Collision Guard (Addy Osmani Pattern) |
| `python tools/core/skill_profiles.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `destructive` | tools/core/skill_profiles.py — Skill Catalog Capability Profile Manager |
| `python tools/core/skill_vault.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `destructive` | SkillVault Lifelong Page Object Model & Interaction Library (MineDojo / Voyager Pattern) |
| `python tools/core/skillspector.py` | **Security** | `quality-gatekeeper` | 🟢 Stable | `read_only` | Security scanner detecting prompt injection, Unicode obfuscation, and dangerous CLI tools. |
| `python tools/contrib/slide_deck_exporter.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/contrib/slide_deck_exporter.py — Pure HTML/CSS 16:9 Vector Slide Deck Exporter |
| `python tools/perf/slow_test_profiler.py` | **Testing & Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/perf/slow_test_profiler.py — Slowest Test Execution Profiler (JUnit XML) |
| `python tools/design/smart_visual_masker.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Smart Visual Masker & Anti-Flake Visual Engine |
| `python tools/api/spec_drift_sentinel.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/api/spec_drift_sentinel.py — Spec-to-Code Drift Sentinel |
| `python tools/orchestration/swe_qa_aci.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | QA Agent-Computer Interface (SWE-agent ACI Pattern) |
| `python tools/orchestration/synapse_doctor.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/orchestration/synapse_doctor.py — Autonomous Environment Diagnostic Suite (`agent-qa doctor`) |
| `python tools/orchestration/synapse_observer.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Synapse Cognitive Observer & Tradeoff Sentinel |
| `python tools/orchestration/synapse_qa_bench.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Synapse-QA-Bench: Tool Function Calling Benchmark (Gorilla BFCL Pattern) |
| `python tools/core/sync_agent_rules.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `modifying` | tools/core/sync_agent_rules.py — Synchronizes AGENTS.md single-source rules to all AI bridges |
| `python tools/core/sync_skills_manifest.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `destructive` | tools/core/sync_skills_manifest.py — Synchronize Skill Policies & Frontmatter into Manifest |
| `python tools/core/task_memory_manager.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/core/task_memory_manager.py — Compaction-Resilient Working Memory Manager |
| `python tools/core/telemetry.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Synapse Hub — Structured Observability & OpenTelemetry W3C Trace Context |
| `python tools/report/telemetry_correlator.py` | **Performance Testing** | `perf-engineer` | 🟢 Stable | `read_only` | Full-stack APM & server telemetry performance correlator linking client latencies with server hardware. |
| `python tools/contrib/template_excel_exporter.py` | **Manual Testing & Design** | `test-designer` | 🟢 Stable | `modifying` | Enterprise template-driven Excel test case exporter with dropdown Data Validation. |
| `python tools/core/test_impact.py` | **Testing & Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Universal Test Impact Analyzer (Graphify AST-Powered) |
| `python tools/core/test_memory_os.py` | **Testing & Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Hierarchical QA Test Memory OS (Letta / MemGPT Pattern) |
| `python tools/heal/textgrad_mutation_optimizer.py` | **Auxiliary Utilities** | `orchestrator` | 🟡 Exp | `read_only` | Deprecated compatibility shim. |
| `python tools/contrib/tmmi_auditor.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/contrib/tmmi_auditor.py — Enterprise TMMi (Test Maturity Model integration) Assessment Sentinel |
| `python tools/contrib/tms_sync_bridge.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `modifying` | Enterprise ALM & TMS Sync Bridge (Jira / Xray / Zephyr / TestRail) |
| `python tools/core/token_estimator.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/core/token_estimator.py — Unified Polyglot BPE Token Estimator |
| `python tools/context/token_telemetry.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/context/token_telemetry.py — Live LLM Token & MTTR Telemetry Engine |
| `python tools/orchestration/tot_exploratory_tester.py` | **Manual Testing & Design** | `test-designer` | 🟢 Stable | `read_only` | Tree-of-Thoughts exploratory scenario generator with risk scoring and boundary decomposition. |
| `python tools/context/trace_data_flow.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Universal Data Flow & Teardown Tracer (Taint Analysis) |
| `python tools/transpiler/traffic_session_converter.py` | **API & Contract Testing** | `api-engineer` | 🟢 Stable | `read_only` | Converts recorded HAR traffic sessions into executable API automation test cases. |
| `python tools/report/trend_analytics.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/report/trend_analytics.py — Historical Quality Trend & Flakiness Analytics Engine |
| `python tools/orchestration/typed_prompt_signatures.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Declarative Typed QA Signatures & Instruction Optimization Engine |
| `python tools/contrib/ui_server.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/contrib/ui_server.py — Synapse Hub Interactive QA Mission Control Web Server |
| `python tools/transpiler/universal_ir.py` | **Code Generation & AST** | `pom-crafter` | 🟢 Stable | `read_only` | Language-agnostic and framework-agnostic AST data model for automated test suites. |
| `python tools/lint/update_sentinel.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Synapse-Hub Auto-Update & Version Drift Sentinel |
| `python tools/lint/validate_groovy_scripts.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Pre-check validator for Groovy scripts and POM keywords in enterprise test suites. |
| `python tools/core/validate_host_interop.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/core/validate_host_interop.py — Multi-Host AI Agent Interoperability Sentinel |
| `python tools/lint/validate_skills_schema.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `destructive` | tools/lint/validate_skills_schema.py — Standalone Skill Schema & Policy Validator |
| `python tools/api/vcr_cassette_guard.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/api/vcr_cassette_guard.py — Deterministic Network VCR Shield & Cassette Linter |
| `python tools/core/verify_all.py` | **Quality Gates** | `quality-gatekeeper` | 🟢 Stable | `read_only` | One-command 10 Quality Gates Definition of Done (DoD) verification sentinel. |
| `python tools/design/visual_diff_canvas.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Canvas Visual Diff & Regression Checker |
| `python tools/heal/visual_som_helper.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | Enterprise Vision-Grounded Fallback & Set-of-Marks (SoM) Engine |
| `python tools/contrib/vpat_exporter.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/contrib/vpat_exporter.py — Enterprise Section 508 & EN 301 549 VPAT Report Generator |
| `python tools/core/watch_mode.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/core/watch_mode.py — Incremental Watch Mode & Real-Time Test Engineering HUD |
| `python tools/contrib/wcag_audit.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/contrib/wcag_audit.py - Automated Accessibility (WCAG 2.2) Linter & Auditor |
| `python tools/contrib/welcome_page.py` | **Auxiliary Utilities** | `orchestrator` | 🟢 Stable | `read_only` | tools/contrib/welcome_page.py — Interactive Visual Landing Page for Synapse Hub |

## 2. Risk & Operational Classification

- `read_only`: Diagnostic, linting, AST inspection, reporting (zero side effects on workspace or git).
- `modifying`: Generates files, updates Page Classes, or writes test suites.
- `network`: Queries external APIs, monitors npm registry, or checks live URLs.
- `destructive`: High-impact actions guarded by `safety_firewall.py` (e.g. drop database, hard resets).

*Catalog generated: `2026-11-24T13:24:36.226640+00:00` by `tools/report/generate_tool_catalog.py`*