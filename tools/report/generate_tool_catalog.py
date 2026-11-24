#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/generate_tool_catalog.py — Enterprise Tooling Ecosystem Catalog Generator
--------------------------------------------------------------------------------
Inventories, classifies, and documents all CLI tools in Synapse Hub:
  - Command invocation & primary executable file
  - Responsible Agent Role (Single Front-Door Orchestrator, Live-Explorer, POM-Crafter, Test-Runner, Failure-Analyst, Quality-Gatekeeper)
  - Functional Category (Quality Gates, Orchestration, Healing, Code Generation, Security, Testing, Release)
  - Maturity Tier: 'stable' (Production ready & tested) vs 'experimental' (Active R&D)
  - Risk Level: 'read_only', 'modifying', 'network', 'destructive'
  - Input arguments, Outputs & artifacts

Generates:
  - tools/TOOL_CATALOG.json (Machine-readable manifest)
  - docs/TOOL_CATALOG.md    (Human-readable comprehensive runbook)
"""
import os
import sys

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass


import os
import sys
import json
import ast
import re
from datetime import datetime, timezone
from typing import Dict, Any

# Enforce UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")

# Well-defined tool metadata overrides & classifications
TOOL_REGISTRY_METADATA = {
    "verify_all.py": {
        "command": "python tools/core/verify_all.py",
        "category": "Quality Gates",
        "owner_role": "quality-gatekeeper",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--mode auto|hub|target", "--test-cmd", "--format text|json|junit"],
        "outputs": ["Console report", "Exit code 0/1", "reports/PROJECT_HEALTH_REPORT.md"],
        "description": "One-command 10 Quality Gates Definition of Done (DoD) verification sentinel."
    },
    "hub_publisher.py": {
        "command": "python tools/core/hub_publisher.py",
        "category": "CI/CD & Packaging",
        "owner_role": "orchestrator",
        "status": "stable",
        "risk_level": "modifying",
        "inputs": ["--message", "--skip-verify", "--dry-run", "--no-wait", "--timeout"],
        "outputs": ["Git main push", "Git tag", "GitHub Release", "NPM publication"],
        "description": "Autonomous 1-click 5-step release pipeline for Synapse Hub."
    },
    "package_release.py": {
        "command": "python tools/core/package_release.py",
        "category": "CI/CD & Packaging",
        "owner_role": "orchestrator",
        "status": "stable",
        "risk_level": "modifying",
        "inputs": ["--output-dir", "--format zip|tar.gz|both", "--verify-archive"],
        "outputs": ["dist/synapse-hub-vX.Y.Z.zip", "dist/*-checksums.sha256"],
        "description": "Enterprise release packager preserving .github/workflows and generating SHA-256 provenance."
    },
    "db_sandbox.py": {
        "command": "python tools/core/db_sandbox.py",
        "category": "Sandboxing & Isolation",
        "owner_role": "failure-analyst",
        "status": "stable",
        "risk_level": "modifying",
        "inputs": ["--mode audit|purge|restore", "--db-path", "--consent"],
        "outputs": ["Database snapshots", "Purge audit logs"],
        "description": "Database state isolation sentinel with granular consent-governed snapshot and purge capabilities."
    },
    "reversible_sandbox.py": {
        "command": "python tools/heal/reversible_sandbox.py",
        "category": "Sandboxing & Isolation",
        "owner_role": "failure-analyst",
        "status": "stable",
        "risk_level": "modifying",
        "inputs": ["--execute-stateful", "--rollback", "--recover-wal"],
        "outputs": [".agent_memory/undo_wal.jsonl", "Reversible execution rollbacks"],
        "description": "Two-phase commit write-ahead logging (WAL) execution sandbox providing crash-resilient rollback guarantees."
    },
    "fsm_enforcer.py": {
        "command": "python tools/core/fsm_enforcer.py",
        "category": "Orchestration",
        "owner_role": "orchestrator",
        "status": "stable",
        "risk_level": "modifying",
        "inputs": ["start --session-id", "advance --stage --actor --evidence", "verify-compliance", "status"],
        "outputs": [".agent_memory/fsm_session.json", "Cryptographic HMAC proof tokens"],
        "description": "5-Stage QA Multi-Agent Finite State Machine enforcer with cryptographic proof tokens."
    },
    "micro_mutator.py": {
        "command": "python tools/lint/micro_mutator.py",
        "category": "Quality Gates",
        "owner_role": "quality-gatekeeper",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["target", "--min-score", "--test-cmd", "--dry-run", "--json", "--allow-empty"],
        "outputs": ["Mutation score report", "SARIF output", "JUnit XML output"],
        "description": "Syntactic micro-mutation sentinel eliminating tautological tests and measuring assertion sensitivity."
    },
    "benchmark_swarm_context.py": {
        "command": "python tools/context/benchmark_swarm_context.py",
        "category": "Benchmarking",
        "owner_role": "orchestrator",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--verify-min-savings", "--json"],
        "outputs": ["benchmarks/CONTEXT_TOKEN_BENCHMARK.md", "reports/context_benchmark.json"],
        "description": "Empirical context token reduction benchmark harness proving >= 40% savings."
    },
    "universal_ir.py": {
        "command": "python tools/transpiler/universal_ir.py",
        "category": "Code Generation & AST",
        "owner_role": "pom-crafter",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["Python dataclasses / JSON schema v1.0.0"],
        "outputs": ["ProjectIR AST", "Hermetic test fixtures"],
        "description": "Language-agnostic and framework-agnostic AST data model for automated test suites."
    },
    "omni_emitter.py": {
        "command": "python tools/transpiler/omni_emitter.py",
        "category": "Code Generation & AST",
        "owner_role": "pom-crafter",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["ProjectIR instance", "target_framework"],
        "outputs": ["Generated Playwright TS/Python, Selenium Java, Katalon Groovy code"],
        "description": "Universal polyglot code generator emitting Clean POM Flat Architecture scripts."
    },
    "omni_parser.py": {
        "command": "python tools/transpiler/omni_parser.py",
        "category": "Code Generation & AST",
        "owner_role": "pom-crafter",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["source_file_path"],
        "outputs": ["ProjectIR AST"],
        "description": "Deterministic 0-token polyglot AST parser extracting Page Classes and test workflows."
    },
    "omni_transpiler.py": {
        "command": "python tools/transpiler/omni_transpiler.py",
        "category": "Code Generation & AST",
        "owner_role": "pom-crafter",
        "status": "stable",
        "risk_level": "modifying",
        "inputs": ["--source", "--target-framework", "--output-dir"],
        "outputs": ["Transpiled target framework files"],
        "description": "Instant 0-token transpiler between Playwright, Selenium, and Katalon."
    },
    "pinpoint_failure.py": {
        "command": "python tools/report/pinpoint_failure.py",
        "category": "Failure Autopsy & Healing",
        "owner_role": "failure-analyst",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["path_to_junit_xml", "--json"],
        "outputs": ["Triage report", "Failing line & locator signature"],
        "description": "Sub-0.1s JUnit XML autopsy parser diagnosing test crashes without LLM token waste."
    },
    "auto_heal.py": {
        "command": "python tools/heal/auto_heal.py",
        "category": "Failure Autopsy & Healing",
        "owner_role": "failure-analyst",
        "status": "stable",
        "risk_level": "modifying",
        "inputs": ["--report", "--interactive", "--apply"],
        "outputs": ["Patched Page Class locator", "Healing ledger record"],
        "description": "Closed-loop locator self-healing engine matching broken selectors against DOM/AOM."
    },
    "setup_project.py": {
        "command": "python tools/core/setup_project.py",
        "category": "Setup & Onboarding",
        "owner_role": "orchestrator",
        "status": "stable",
        "risk_level": "modifying",
        "inputs": ["target_dir", "--profile", "--apply", "--uninstall"],
        "outputs": ["PROJECT_AI_GUIDE.md", "Universal IDE AI rules", "Pre-push hooks"],
        "description": "Zero-command automated project bootstrap tailoring AI agent rules to the target stack."
    },
    "analyze_project.py": {
        "command": "python tools/core/analyze_project.py",
        "category": "Quality Gates",
        "owner_role": "quality-gatekeeper",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["target_dir", "--json", "--mode"],
        "outputs": ["reports/PROJECT_HEALTH_REPORT.md", "AST repo map"],
        "description": "Comprehensive health audit analyzing environment, POM structure, and Quality Gates."
    },
    "safety_firewall.py": {
        "command": "python tools/security/safety_firewall.py",
        "category": "Security",
        "owner_role": "quality-gatekeeper",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--check-command <cmd>", "--inspect-path <path>"],
        "outputs": ["Authorization verdict PASS/BLOCKED"],
        "description": "Non-bypassable safety firewall blocking destructive operations (drop database, git push force, rm -rf)."
    },
    "skillspector.py": {
        "command": "python tools/core/skillspector.py",
        "category": "Security",
        "owner_role": "quality-gatekeeper",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["target_dir_or_skill", "--strict"],
        "outputs": ["Vulnerability audit report", "Zero-day prompt injection alerts"],
        "description": "Security scanner detecting prompt injection, Unicode obfuscation, and dangerous CLI tools."
    },
    "security_scanner.py": {
        "command": "python tools/security/security_scanner.py",
        "category": "Security",
        "owner_role": "quality-gatekeeper",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--json", "--strict"],
        "outputs": ["Security audit report", "Dependency vulnerability alerts"],
        "description": "Comprehensive enterprise security sentinel auditing Python & NPM dependencies and threat-model defense."
    },
    "generate_sbom.py": {
        "command": "python tools/report/generate_sbom.py",
        "category": "Security",
        "owner_role": "orchestrator",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--output", "--repo-root"],
        "outputs": ["reports/synapse_hub_sbom.spdx.json"],
        "description": "Standard SPDX 2.3 JSON Software Bill of Materials (SBOM) generator for software supply chain security."
    },
    "generate_jmx_plan.py": {
        "command": "python tools/contrib/generate_jmx_plan.py",
        "category": "Performance Testing",
        "owner_role": "perf-engineer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--spec", "--postman", "--har", "--vus", "--duration", "--sla-p95", "--output", "--emit-locust"],
        "outputs": ["JMeter .jmx test plan XML", "Locust locustfile.py"],
        "description": "Enterprise Apache JMeter 5.x & Locust test plan generator from OpenAPI/Postman/HAR specs."
    },
    "jtl_analyzer.py": {
        "command": "python tools/perf/jtl_analyzer.py",
        "category": "Performance Testing",
        "owner_role": "perf-engineer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["jtl_file", "--sla-p95", "--sla-p99", "--max-error-rate", "--markdown", "--json"],
        "outputs": ["Performance SLA Quality Gate report", "Structured JSON metrics"],
        "description": "Sub-0.1s Apache JMeter JTL results analyzer enforcing automated CI/CD SLA quality gates."
    },
    "telemetry_correlator.py": {
        "command": "python tools/report/telemetry_correlator.py",
        "category": "Performance Testing",
        "owner_role": "perf-engineer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--jtl", "--server-metrics", "--markdown", "--json", "--otel"],
        "outputs": ["Markdown RCA report", "JSON diagnostics", "OpenTelemetry metrics payload"],
        "description": "Full-stack APM & server telemetry performance correlator linking client latencies with server hardware."
    },
    "template_excel_exporter.py": {
        "command": "python tools/contrib/template_excel_exporter.py",
        "category": "Manual Testing & Design",
        "owner_role": "test-designer",
        "status": "stable",
        "risk_level": "modifying",
        "inputs": ["input_file", "-o", "-t", "--module-code", "--module-name", "--author", "--tester"],
        "outputs": ["Standardized 12-column Excel test suite (.xlsx)"],
        "description": "Enterprise template-driven Excel test case exporter with dropdown Data Validation."
    },
    "interview_story.py": {
        "command": "python tools/contrib/interview_story.py",
        "category": "Manual Testing & Design",
        "owner_role": "test-designer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--story", "--auto-clarify", "--export-md"],
        "outputs": ["Ambiguity audit report", "Clarified Acceptance Criteria"],
        "description": "Interactive requirement interrogation engine surfacing hidden assumptions and ambiguous acceptance criteria."
    },
    "tot_exploratory_tester.py": {
        "command": "python tools/orchestration/tot_exploratory_tester.py",
        "category": "Manual Testing & Design",
        "owner_role": "test-designer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--story", "--max-depth", "--beam-width"],
        "outputs": ["Exploratory testing tree (Happy, Boundary, Chaos)", "Risk scores"],
        "description": "Tree-of-Thoughts exploratory scenario generator with risk scoring and boundary decomposition."
    },
    "gherkin_suite.py": {
        "command": "python tools/transpiler/gherkin_suite.py",
        "category": "Manual Testing & Design",
        "owner_role": "test-designer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--features", "--audit-coverage"],
        "outputs": ["Compiled test matrix", "Proven-vs-owed coverage gap report"],
        "description": "Compiles Gherkin .feature specs into expanded test matrices and coverage reports."
    },
    "generate_api_matrix.py": {
        "command": "python tools/api/generate_api_matrix.py",
        "category": "API & Contract Testing",
        "owner_role": "api-engineer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--spec", "--output", "--include-boundary"],
        "outputs": ["E2E API test matrix (.md / .json)"],
        "description": "Converts OpenAPI/Swagger specs into automated positive, boundary, and negative test matrices."
    },
    "api_drift_sentinel.py": {
        "command": "python tools/api/api_drift_sentinel.py",
        "category": "API & Contract Testing",
        "owner_role": "api-engineer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--spec", "--actual-payload", "--fail-on-drift"],
        "outputs": ["Schema drift analysis report"],
        "description": "Detects contract drift and breaking schema mutations against OpenAPI specifications."
    },
    "newman_analyzer.py": {
        "command": "python tools/perf/newman_analyzer.py",
        "category": "API & Contract Testing",
        "owner_role": "api-engineer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["newman_report.json", "--sla-p95", "--max-failures"],
        "outputs": ["API execution metrics & CI/CD SLA quality gate status"],
        "description": "Sub-0.1s Postman/Newman JSON test report analyzer enforcing CI/CD quality gates."
    },
    "network_mock_shield.py": {
        "command": "python tools/api/network_mock_shield.py",
        "category": "API & Contract Testing",
        "owner_role": "api-engineer",
        "status": "stable",
        "risk_level": "modifying",
        "inputs": ["--route", "--status", "--body", "--delay-ms"],
        "outputs": ["Stubbed HTTP/GraphQL response mocks"],
        "description": "Network interception shield stubbing external routes and injecting chaos network faults."
    },
    "export_postman_collection.py": {
        "command": "python tools/contrib/export_postman_collection.py",
        "category": "API & Contract Testing",
        "owner_role": "api-engineer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--matrix", "--output"],
        "outputs": ["Postman Collection v2.1.0 (.json)"],
        "description": "Exports API test matrices into runnable Postman Collections with pre-request scripts."
    },
    "traffic_session_converter.py": {
        "command": "python tools/transpiler/traffic_session_converter.py",
        "category": "API & Contract Testing",
        "owner_role": "api-engineer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--har", "--output"],
        "outputs": ["Executable API test scripts"],
        "description": "Converts recorded HAR traffic sessions into executable API automation test cases."
    }
}


CANONICAL_TOOL_FILES = {
    "tools/api/_openapi_parser.py",
    "tools/api/api_drift_sentinel.py",
    "tools/api/api_fuzzer.py",
    "tools/api/contract_validator.py",
    "tools/api/e2e_flow_prober.py",
    "tools/api/fuzz_payloads.py",
    "tools/api/generate_api_matrix.py",
    "tools/api/network_mock_shield.py",
    "tools/api/pairwise_generator.py",
    "tools/api/spec_drift_sentinel.py",
    "tools/api/vcr_cassette_guard.py",
    "tools/context/ast_cache.py",
    "tools/context/benchmark_swarm_context.py",
    "tools/context/context_slicer.py",
    "tools/context/lookup_tc.py",
    "tools/context/token_telemetry.py",
    "tools/context/trace_data_flow.py",
    "tools/contrib/cldr_l10n_verifier.py",
    "tools/contrib/dashboard_generator.py",
    "tools/contrib/diagram_architect.py",
    "tools/contrib/etl_data_reconciler.py",
    "tools/contrib/export_postman_collection.py",
    "tools/contrib/generate_jmx_plan.py",
    "tools/contrib/generate_tc_from_story.py",
    "tools/contrib/interview_story.py",
    "tools/contrib/jira_sync.py",
    "tools/contrib/md_to_xlsx.py",
    "tools/contrib/openxml_guard.py",
    "tools/contrib/payment_interop_simulator.py",
    "tools/contrib/slide_deck_exporter.py",
    "tools/contrib/template_excel_exporter.py",
    "tools/contrib/tmmi_auditor.py",
    "tools/contrib/tms_sync_bridge.py",
    "tools/contrib/ui_server.py",
    "tools/contrib/vpat_exporter.py",
    "tools/contrib/wcag_audit.py",
    "tools/contrib/welcome_page.py",
    "tools/core/adapters.py",
    "tools/core/analyze_project.py",
    "tools/core/author_integrity.py",
    "tools/core/bm25_retriever.py",
    "tools/core/bump_version.py",
    "tools/core/cache_resolver.py",
    "tools/core/check_env.py",
    "tools/core/check_version_sync.py",
    "tools/core/circuit_breaker.py",
    "tools/core/cli.py",
    "tools/core/cli_runtime.py",
    "tools/core/codemod_tool_imports.py",
    "tools/core/config_decoupler.py",
    "tools/core/count_tokens.py",
    "tools/core/db_sandbox.py",
    "tools/core/debt_harvester.py",
    "tools/core/distill_log.py",
    "tools/core/distill_skill.py",
    "tools/core/file_lock.py",
    "tools/core/fsm_enforcer.py",
    "tools/core/fsm_middleware.py",
    "tools/core/git_worktree_manager.py",
    "tools/core/hub_publisher.py",
    "tools/core/i18n.py",
    "tools/core/init_config.py",
    "tools/core/memory_bus.py",
    "tools/core/package_release.py",
    "tools/core/process_supervisor.py",
    "tools/core/project_state.py",
    "tools/core/provider_usage_adapter.py",
    "tools/core/repo_map.py",
    "tools/core/rule_harvester.py",
    "tools/core/rules_router.py",
    "tools/core/session_vault.py",
    "tools/core/setup_project.py",
    "tools/core/skill_canonical_digest.py",
    "tools/core/skill_profiles.py",
    "tools/core/skill_vault.py",
    "tools/core/skillspector.py",
    "tools/core/sync_agent_rules.py",
    "tools/core/sync_skills_manifest.py",
    "tools/core/task_memory_manager.py",
    "tools/core/telemetry.py",
    "tools/core/test_impact.py",
    "tools/core/test_memory_os.py",
    "tools/core/token_estimator.py",
    "tools/core/validate_host_interop.py",
    "tools/core/verify_all.py",
    "tools/core/watch_mode.py",
    "tools/design/break_ui_generator.py",
    "tools/design/mechanical_ui_gate.py",
    "tools/design/smart_visual_masker.py",
    "tools/design/visual_diff_canvas.py",
    "tools/heal/agentless_patcher.py",
    "tools/heal/assertion_optimizer.py",
    "tools/heal/ast_assertion_optimizer.py",
    "tools/heal/auto_heal.py",
    "tools/heal/auto_heal_reflexion.py",
    "tools/heal/ci_healing_hook.py",
    "tools/heal/heal_pr_automator.py",
    "tools/heal/heuristic_locator_matcher.py",
    "tools/heal/live_visual_healer.py",
    "tools/heal/lookup_xpath.py",
    "tools/heal/reversible_sandbox.py",
    "tools/heal/textgrad_mutation_optimizer.py",
    "tools/heal/visual_som_helper.py",
    "tools/lint/agent_canary.py",
    "tools/lint/ai_eval_sentinel.py",
    "tools/lint/flaky_detector.py",
    "tools/lint/git_pre_commit_guard.py",
    "tools/lint/humanize_linter.py",
    "tools/lint/infer_linter.py",
    "tools/lint/lint_ai_docs.py",
    "tools/lint/micro_mutator.py",
    "tools/lint/mipro_assertion_tuner.py",
    "tools/lint/pre_bash_guard.py",
    "tools/lint/pre_push_guard.py",
    "tools/lint/skill_collision_guard.py",
    "tools/lint/update_sentinel.py",
    "tools/lint/validate_groovy_scripts.py",
    "tools/lint/validate_skills_schema.py",
    "tools/mcp/mcp_docx_server.py",
    "tools/mcp/mcp_excel_server.py",
    "tools/mcp/mcp_server.py",
    "tools/orchestration/autogen_qa_broker.py",
    "tools/orchestration/browsergym_eval.py",
    "tools/orchestration/dspy_qa_signatures.py",
    "tools/orchestration/goldfish_review.py",
    "tools/orchestration/matrix_sharder.py",
    "tools/orchestration/qa_event_stream.py",
    "tools/orchestration/runaway_stopper.py",
    "tools/orchestration/senior_code_review.py",
    "tools/orchestration/swe_qa_aci.py",
    "tools/orchestration/synapse_doctor.py",
    "tools/orchestration/synapse_observer.py",
    "tools/orchestration/synapse_qa_bench.py",
    "tools/orchestration/tot_exploratory_tester.py",
    "tools/orchestration/typed_prompt_signatures.py",
    "tools/perf/benchmark_perf_runner.py",
    "tools/perf/chaos_resilience_probe.py",
    "tools/perf/heap_leak_analyzer.py",
    "tools/perf/jtl_analyzer.py",
    "tools/perf/mobile_resilience_sentinel.py",
    "tools/perf/newman_analyzer.py",
    "tools/perf/observability_tester.py",
    "tools/perf/slow_test_profiler.py",
    "tools/report/bug_reporter.py",
    "tools/report/coverage_reporter.py",
    "tools/report/generate_allure_report.py",
    "tools/report/generate_sbom.py",
    "tools/report/generate_test_reports.py",
    "tools/report/generate_tool_catalog.py",
    "tools/report/output_formatter.py",
    "tools/report/pinpoint_failure.py",
    "tools/report/telemetry_correlator.py",
    "tools/report/trend_analytics.py",
    "tools/security/asvs_auditor.py",
    "tools/security/cvss_calculator.py",
    "tools/security/pentest_scope_guard.py",
    "tools/security/regulatory_compliance.py",
    "tools/security/safety_firewall.py",
    "tools/security/security_coverage_ledger.py",
    "tools/security/security_scanner.py",
    "tools/transpiler/gherkin_suite.py",
    "tools/transpiler/omni_emitter.py",
    "tools/transpiler/omni_parser.py",
    "tools/transpiler/omni_transpiler.py",
    "tools/transpiler/traffic_session_converter.py",
    "tools/transpiler/universal_ir.py",
}

def build_catalog() -> Dict[str, Any]:
    """Scans all Python scripts in tools/ and builds a comprehensive catalog."""
    catalog = {
        "schema_version": "1.0.0",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_tools": 0,
        "stable_count": 0,
        "experimental_count": 0,
        "tools": []
    }

    all_tool_entries = []
    for root, dirs, files in os.walk(TOOLS_DIR):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
        for f in sorted(files):
            if f.endswith(".py") and not f.startswith("__"):
                rel_path = os.path.relpath(os.path.join(root, f), REPO_ROOT).replace("\\", "/")
                if rel_path in CANONICAL_TOOL_FILES:
                    all_tool_entries.append((f, rel_path, os.path.join(root, f)))
    all_tool_entries.sort(key=lambda x: x[0])

    for fname, rel_file, full_path in all_tool_entries:
        meta = TOOL_REGISTRY_METADATA.get(fname)

        # Fallback docstring extraction
        doc_summary = ""
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read(), fname)
                doc = ast.get_docstring(tree)
                if doc:
                    doc_summary = doc.strip().split("\n")[0].strip("- ")
                    doc_summary = re.sub(r"^tools/[a-zA-Z0-9_\-/]+\.(?:py|sh|ps1|bat|js)", rel_file, doc_summary)
        except Exception:
            doc_summary = fname

        if meta:
            cmd = meta["command"].replace("tools/", f"tools/{rel_file.split('/')[1]}/") if "tools/" in meta["command"] and "/" not in meta["command"].split("tools/")[1] else meta["command"]
            entry = {
                "file": rel_file,
                "command": cmd,
                "category": meta["category"],
                "owner_role": meta["owner_role"],
                "status": meta["status"],
                "risk_level": meta["risk_level"],
                "inputs": meta["inputs"],
                "outputs": meta["outputs"],
                "description": meta["description"]
            }
        else:
            # Auto-inferred metadata for auxiliary tools
            is_test_tool = "test" in fname or "fuzz" in fname or "mock" in fname
            lower_name = fname.lower()
            if any(k in lower_name for k in ("purge", "delete", "destroy", "kill")):
                inferred_risk = "destructive"
            elif any(k in lower_name for k in ("network", "http", "curl", "fetch", "download")):
                inferred_risk = "network"
            elif any(k in lower_name for k in ("mutate", "heal", "patch", "sandbox", "supervisor", "exec", "publish", "deploy", "release", "push", "upload", "write", "sync", "bump", "rollback", "revert", "clean")):
                inferred_risk = "modifying"
            else:
                inferred_risk = "read_only"

            entry = {
                "file": rel_file,
                "command": f"python {rel_file}",
                "category": "Testing & Utilities" if is_test_tool else "Auxiliary Utilities",
                "owner_role": "orchestrator",
                "status": "stable" if os.path.getsize(full_path) > 1000 else "experimental",
                "risk_level": inferred_risk,
                "inputs": ["CLI options"],
                "outputs": ["Artifacts / Telemetry"],
                "description": doc_summary or f"Synapse Hub utility module: {fname}"
            }

        catalog["tools"].append(entry)

    catalog["total_tools"] = len(catalog["tools"])
    catalog["stable_count"] = sum(1 for t in catalog["tools"] if t["status"] == "stable")
    catalog["experimental_count"] = sum(1 for t in catalog["tools"] if t["status"] == "experimental")

    return catalog


def format_markdown_catalog(catalog: Dict[str, Any]) -> str:
    """Renders catalog into an enterprise markdown runbook."""
    md = [
        "# Synapse Hub — Tooling Ecosystem Catalog & Runbook",
        "",
        "> **Audience:** QA Engineers, Autonomous AI Agents (Lead Orchestrator, POM-Crafter, Test-Runner, Failure-Analyst, Quality-Gatekeeper).",
        f"> **Total Tools Cataloged:** `{catalog['total_tools']}` | **Stable:** `{catalog['stable_count']}` | **Experimental:** `{catalog['experimental_count']}`",
        "",
        "## 1. Primary Enterprise CLI Tools",
        "",
        "| Command | Category | Owner Role | Status | Risk Level | Description |",
        "|---|---|:---:|:---:|:---:|---|"
    ]

    for t in catalog["tools"]:
        status_badge = "🟢 Stable" if t["status"] == "stable" else "🟡 Exp"
        risk_badge = f"`{t['risk_level']}`"
        md.append(f"| `{t['command']}` | **{t['category']}** | `{t['owner_role']}` | {status_badge} | {risk_badge} | {t['description']} |")

    md.extend([
        "",
        "## 2. Risk & Operational Classification",
        "",
        "- `read_only`: Diagnostic, linting, AST inspection, reporting (zero side effects on workspace or git).",
        "- `modifying`: Generates files, updates Page Classes, or writes test suites.",
        "- `network`: Queries external APIs, monitors npm registry, or checks live URLs.",
        "- `destructive`: High-impact actions guarded by `safety_firewall.py` (e.g. drop database, hard resets).",
        "",
        f"*Catalog generated: `{catalog['updated_at']}` by `tools/report/generate_tool_catalog.py`*"
    ])

    return "\n".join(md)


def generate_tool_index(catalog: Dict[str, Any]) -> Dict[str, Any]:
    """Generates Tier-1 lightweight tool index grouped by owner_role (< 12 KB)."""
    import re
    personas = [
        "core-profile", "orchestrator", "live-explorer", "pom-crafter", "test-runner",
        "failure-analyst", "quality-gatekeeper", "api-engineer",
        "perf-engineer", "test-designer"
    ]
    by_role: Dict[str, Any] = {p: {} for p in personas}
    by_role["core-profile"] = {"catalog": "tools/TOOL_CORE_PROFILE.json", "count": 18}
    for t in catalog["tools"]:
        role = t.get("owner_role", "orchestrator")
        if role not in by_role:
            by_role[role] = {}
        desc = t.get("description", "").strip()
        if "—" in desc:
            desc = desc.split("—", 1)[1].strip()
        desc = re.sub(r"\s+", " ", desc)
        if len(desc) > 26:
            desc = desc[:24] + ".."
        cmd = t.get("command", "")
        by_role[role][cmd] = desc
    return by_role


def shard_catalogs(catalog: Dict[str, Any], catalogs_dir: str) -> int:
    """Shards full schemas into per-category Tier-2 catalogs."""
    import re
    os.makedirs(catalogs_dir, exist_ok=True)
    by_category: Dict[str, list] = {}
    for t in catalog["tools"]:
        cat = t.get("category", "Auxiliary Utilities")
        by_category.setdefault(cat, []).append(t)

    for cat, tools in by_category.items():
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", cat.strip()).lower().strip("_")
        cat_file = os.path.join(catalogs_dir, f"{slug}.json")
        payload = {
            "category": cat,
            "total_tools": len(tools),
            "tools": tools
        }
        with open(cat_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    return len(by_category)


def sync_minified_schema(repo_root: str = REPO_ROOT) -> Dict[str, Any]:
    """Synchronizes tools/tools_schema.min.json from tools/tools_schema.json via SchemaMinifier."""
    tools_dir = os.path.join(repo_root, "tools")
    schema_path = os.path.join(tools_dir, "tools_schema.json")
    min_path = os.path.join(tools_dir, "tools_schema.min.json")
    if not os.path.isfile(schema_path):
        return {
            "synced": False,
            "reason": "missing_tools_schema",
            "min_path": None,
            "tools_count": 0,
            "original_size": 0,
            "minified_size": 0,
            "savings_pct": 0.0,
        }

    try:
        from tools.core.schema_minifier import SchemaMinifier

        minified_tools, original_size, _ = SchemaMinifier.minify_schema_file(schema_path)
        payload_text = json.dumps({"tools": minified_tools}, separators=(",", ":"), ensure_ascii=False)
        with open(min_path, "w", encoding="utf-8") as f:
            f.write(payload_text)
        written_size = len(payload_text)
        savings_pct = round((1.0 - (written_size / original_size)) * 100.0, 2) if original_size > 0 else 0.0
        return {
            "synced": True,
            "min_path": min_path,
            "tools_count": len(minified_tools),
            "original_size": original_size,
            "minified_size": written_size,
            "savings_pct": savings_pct,
        }
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {
            "synced": False,
            "reason": str(exc),
            "min_path": None,
            "tools_count": 0,
            "original_size": 0,
            "minified_size": 0,
            "savings_pct": 0.0,
        }


def main() -> int:
    catalog = build_catalog()

    # Write Tier-2 Full JSON catalog
    json_path = os.path.join(TOOLS_DIR, "TOOL_CATALOG.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    # Write Tier-1 Lightweight JSON index
    index_path = os.path.join(TOOLS_DIR, "TOOL_INDEX.json")
    tool_index = generate_tool_index(catalog)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(tool_index, f, separators=(',', ':'), ensure_ascii=False)

    # Write Tier-2 Per-Category Sharded catalogs
    catalogs_dir = os.path.join(TOOLS_DIR, "catalogs")
    sharded_count = shard_catalogs(catalog, catalogs_dir)

    # Write Markdown catalog
    docs_dir = os.path.join(REPO_ROOT, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    md_path = os.path.join(docs_dir, "TOOL_CATALOG.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(format_markdown_catalog(catalog))

    # Refresh Tier-2 Minified Schema when tools/tools_schema.json exists
    min_schema_res = sync_minified_schema(REPO_ROOT)

    print("=" * 68)
    print("    SYNAPSE HUB — TOOLING ECOSYSTEM CATALOG GENERATOR")
    print("=" * 68)
    print(f"  Indexed Tools      : {catalog['total_tools']} tools")
    print(f"  Stable Tools       : {catalog['stable_count']} (Production Ready)")
    print(f"  Experimental Tools : {catalog['experimental_count']}")
    print(f"  JSON Catalog (T2)  : {os.path.relpath(json_path, REPO_ROOT)}")
    print(f"  JSON Index (T1)    : {os.path.relpath(index_path, REPO_ROOT)}")
    print(f"  Sharded Catalogs   : {sharded_count} files in {os.path.relpath(catalogs_dir, REPO_ROOT)}")
    print(f"  Markdown Runbook   : {os.path.relpath(md_path, REPO_ROOT)}")
    if min_schema_res.get("synced") and min_schema_res.get("min_path"):
        print(
            f"  Minified Schema    : {os.path.relpath(min_schema_res['min_path'], REPO_ROOT)} "
            f"({min_schema_res['savings_pct']}% saved)"
        )
    print("=" * 68)
    print("✅ Tool catalog synchronized successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
