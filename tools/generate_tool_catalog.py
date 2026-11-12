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
import json
import ast
from datetime import datetime, timezone
from typing import Dict, Any

# Enforce UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")

# Well-defined tool metadata overrides & classifications
TOOL_REGISTRY_METADATA = {
    "verify_all.py": {
        "command": "python tools/verify_all.py",
        "category": "Quality Gates",
        "owner_role": "quality-gatekeeper",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--mode auto|hub|target", "--test-cmd", "--format text|json|junit"],
        "outputs": ["Console report", "Exit code 0/1", "reports/PROJECT_HEALTH_REPORT.md"],
        "description": "One-command 11 Quality Gates Definition of Done (DoD) verification sentinel."
    },
    "hub_publisher.py": {
        "command": "python tools/hub_publisher.py",
        "category": "CI/CD & Packaging",
        "owner_role": "orchestrator",
        "status": "stable",
        "risk_level": "modifying",
        "inputs": ["--message", "--skip-verify", "--dry-run", "--no-wait", "--timeout"],
        "outputs": ["Git main push", "Git tag", "GitHub Release", "NPM publication"],
        "description": "Autonomous 1-click 5-step release pipeline for Synapse Hub."
    },
    "package_release.py": {
        "command": "python tools/package_release.py",
        "category": "CI/CD & Packaging",
        "owner_role": "orchestrator",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--output-dir", "--format zip|tar.gz|both", "--verify-archive"],
        "outputs": ["dist/synapse-hub-vX.Y.Z.zip", "dist/*-checksums.sha256"],
        "description": "Enterprise release packager preserving .github/workflows and generating SHA-256 provenance."
    },
    "fsm_enforcer.py": {
        "command": "python tools/fsm_enforcer.py",
        "category": "Orchestration",
        "owner_role": "orchestrator",
        "status": "stable",
        "risk_level": "modifying",
        "inputs": ["start --session-id", "advance --stage --actor --evidence", "verify-compliance", "status"],
        "outputs": [".agent_memory/fsm_session.json", "Cryptographic HMAC proof tokens"],
        "description": "5-Stage QA Multi-Agent Finite State Machine enforcer with cryptographic proof tokens."
    },
    "micro_mutator.py": {
        "command": "python tools/micro_mutator.py",
        "category": "Quality Gates",
        "owner_role": "quality-gatekeeper",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["target", "--min-score", "--test-cmd", "--dry-run", "--json", "--allow-empty"],
        "outputs": ["Mutation score report", "SARIF output", "JUnit XML output"],
        "description": "Syntactic micro-mutation sentinel eliminating tautological tests and measuring assertion sensitivity."
    },
    "benchmark_swarm_context.py": {
        "command": "python tools/benchmark_swarm_context.py",
        "category": "Benchmarking",
        "owner_role": "orchestrator",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--verify-min-savings", "--json"],
        "outputs": ["benchmarks/CONTEXT_TOKEN_BENCHMARK.md", "reports/context_benchmark.json"],
        "description": "Empirical context token reduction benchmark harness proving >= 40% savings."
    },
    "universal_ir.py": {
        "command": "python tools/universal_ir.py",
        "category": "Code Generation & AST",
        "owner_role": "pom-crafter",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["Python dataclasses / JSON schema v1.0.0"],
        "outputs": ["ProjectIR AST", "Hermetic test fixtures"],
        "description": "Language-agnostic and framework-agnostic AST data model for automated test suites."
    },
    "omni_emitter.py": {
        "command": "python tools/omni_emitter.py",
        "category": "Code Generation & AST",
        "owner_role": "pom-crafter",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["ProjectIR instance", "target_framework"],
        "outputs": ["Generated Playwright TS/Python, Selenium Java, Katalon Groovy code"],
        "description": "Universal polyglot code generator emitting Clean POM Flat Architecture scripts."
    },
    "omni_parser.py": {
        "command": "python tools/omni_parser.py",
        "category": "Code Generation & AST",
        "owner_role": "pom-crafter",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["source_file_path"],
        "outputs": ["ProjectIR AST"],
        "description": "Deterministic 0-token polyglot AST parser extracting Page Classes and test workflows."
    },
    "omni_transpiler.py": {
        "command": "python tools/omni_transpiler.py",
        "category": "Code Generation & AST",
        "owner_role": "pom-crafter",
        "status": "stable",
        "risk_level": "modifying",
        "inputs": ["--source", "--target-framework", "--output-dir"],
        "outputs": ["Transpiled target framework files"],
        "description": "Instant 0-token transpiler between Playwright, Selenium, and Katalon."
    },
    "pinpoint_failure.py": {
        "command": "python tools/pinpoint_failure.py",
        "category": "Failure Autopsy & Healing",
        "owner_role": "failure-analyst",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["path_to_junit_xml", "--json"],
        "outputs": ["Triage report", "Failing line & locator signature"],
        "description": "Sub-0.1s JUnit XML autopsy parser diagnosing test crashes without LLM token waste."
    },
    "auto_heal.py": {
        "command": "python tools/auto_heal.py",
        "category": "Failure Autopsy & Healing",
        "owner_role": "failure-analyst",
        "status": "stable",
        "risk_level": "modifying",
        "inputs": ["--report", "--interactive", "--apply"],
        "outputs": ["Patched Page Class locator", "Healing ledger record"],
        "description": "Closed-loop locator self-healing engine matching broken selectors against DOM/AOM."
    },
    "setup_project.py": {
        "command": "python tools/setup_project.py",
        "category": "Setup & Onboarding",
        "owner_role": "orchestrator",
        "status": "stable",
        "risk_level": "modifying",
        "inputs": ["target_dir", "--profile", "--apply", "--uninstall"],
        "outputs": ["PROJECT_AI_GUIDE.md", "Universal IDE AI rules", "Pre-push hooks"],
        "description": "Zero-command automated project bootstrap tailoring AI agent rules to the target stack."
    },
    "analyze_project.py": {
        "command": "python tools/analyze_project.py",
        "category": "Quality Gates",
        "owner_role": "quality-gatekeeper",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["target_dir", "--json", "--mode"],
        "outputs": ["reports/PROJECT_HEALTH_REPORT.md", "AST repo map"],
        "description": "Comprehensive health audit analyzing environment, POM structure, and Quality Gates."
    },
    "safety_firewall.py": {
        "command": "python tools/safety_firewall.py",
        "category": "Security",
        "owner_role": "quality-gatekeeper",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--check-command <cmd>", "--inspect-path <path>"],
        "outputs": ["Authorization verdict PASS/BLOCKED"],
        "description": "Non-bypassable safety firewall blocking destructive operations (drop database, git push force, rm -rf)."
    },
    "skillspector.py": {
        "command": "python tools/skillspector.py",
        "category": "Security",
        "owner_role": "quality-gatekeeper",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["target_dir_or_skill", "--strict"],
        "outputs": ["Vulnerability audit report", "Zero-day prompt injection alerts"],
        "description": "Security scanner detecting prompt injection, Unicode obfuscation, and dangerous CLI tools."
    },
    "security_scanner.py": {
        "command": "python tools/security_scanner.py",
        "category": "Security",
        "owner_role": "quality-gatekeeper",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--json", "--strict"],
        "outputs": ["Security audit report", "Dependency vulnerability alerts"],
        "description": "Comprehensive enterprise security sentinel auditing Python & NPM dependencies and threat-model defense."
    },
    "generate_sbom.py": {
        "command": "python tools/generate_sbom.py",
        "category": "Security",
        "owner_role": "orchestrator",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--output", "--repo-root"],
        "outputs": ["reports/synapse_hub_sbom.spdx.json"],
        "description": "Standard SPDX 2.3 JSON Software Bill of Materials (SBOM) generator for software supply chain security."
    },
    "generate_jmx_plan.py": {
        "command": "python tools/generate_jmx_plan.py",
        "category": "Performance Testing",
        "owner_role": "perf-engineer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--spec", "--postman", "--har", "--vus", "--duration", "--sla-p95", "--output", "--emit-locust"],
        "outputs": ["JMeter .jmx test plan XML", "Locust locustfile.py"],
        "description": "Enterprise Apache JMeter 5.x & Locust test plan generator from OpenAPI/Postman/HAR specs."
    },
    "jtl_analyzer.py": {
        "command": "python tools/jtl_analyzer.py",
        "category": "Performance Testing",
        "owner_role": "perf-engineer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["jtl_file", "--sla-p95", "--sla-p99", "--max-error-rate", "--markdown", "--json"],
        "outputs": ["Performance SLA Quality Gate report", "Structured JSON metrics"],
        "description": "Sub-0.1s Apache JMeter JTL results analyzer enforcing automated CI/CD SLA quality gates."
    },
    "telemetry_correlator.py": {
        "command": "python tools/telemetry_correlator.py",
        "category": "Performance Testing",
        "owner_role": "perf-engineer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--jtl", "--server-metrics", "--markdown", "--json", "--otel"],
        "outputs": ["Markdown RCA report", "JSON diagnostics", "OpenTelemetry metrics payload"],
        "description": "Full-stack APM & server telemetry performance correlator linking client latencies with server hardware."
    },
    "template_excel_exporter.py": {
        "command": "python tools/template_excel_exporter.py",
        "category": "Manual Testing & Design",
        "owner_role": "test-designer",
        "status": "stable",
        "risk_level": "modifying",
        "inputs": ["input_file", "-o", "-t", "--module-code", "--module-name", "--author", "--tester"],
        "outputs": ["Standardized 12-column Excel test suite (.xlsx)"],
        "description": "Enterprise template-driven Excel test case exporter with dropdown Data Validation."
    },
    "interview_story.py": {
        "command": "python tools/interview_story.py",
        "category": "Manual Testing & Design",
        "owner_role": "test-designer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--story", "--auto-clarify", "--export-md"],
        "outputs": ["Ambiguity audit report", "Clarified Acceptance Criteria"],
        "description": "Interactive requirement interrogation engine surfacing hidden assumptions and ambiguous acceptance criteria."
    },
    "tot_exploratory_tester.py": {
        "command": "python tools/tot_exploratory_tester.py",
        "category": "Manual Testing & Design",
        "owner_role": "test-designer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--story", "--max-depth", "--beam-width"],
        "outputs": ["Exploratory testing tree (Happy, Boundary, Chaos)", "Risk scores"],
        "description": "Tree-of-Thoughts exploratory scenario generator with risk scoring and boundary decomposition."
    },
    "gherkin_suite.py": {
        "command": "python tools/gherkin_suite.py",
        "category": "Manual Testing & Design",
        "owner_role": "test-designer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--features", "--audit-coverage"],
        "outputs": ["Compiled test matrix", "Proven-vs-owed coverage gap report"],
        "description": "Compiles Gherkin .feature specs into expanded test matrices and coverage reports."
    },
    "generate_api_matrix.py": {
        "command": "python tools/generate_api_matrix.py",
        "category": "API & Contract Testing",
        "owner_role": "api-engineer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--spec", "--output", "--include-boundary"],
        "outputs": ["E2E API test matrix (.md / .json)"],
        "description": "Converts OpenAPI/Swagger specs into automated positive, boundary, and negative test matrices."
    },
    "api_drift_sentinel.py": {
        "command": "python tools/api_drift_sentinel.py",
        "category": "API & Contract Testing",
        "owner_role": "api-engineer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--spec", "--actual-payload", "--fail-on-drift"],
        "outputs": ["Schema drift analysis report"],
        "description": "Detects contract drift and breaking schema mutations against OpenAPI specifications."
    },
    "newman_analyzer.py": {
        "command": "python tools/newman_analyzer.py",
        "category": "API & Contract Testing",
        "owner_role": "api-engineer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["newman_report.json", "--sla-p95", "--max-failures"],
        "outputs": ["API execution metrics & CI/CD SLA quality gate status"],
        "description": "Sub-0.1s Postman/Newman JSON test report analyzer enforcing CI/CD quality gates."
    },
    "network_mock_shield.py": {
        "command": "python tools/network_mock_shield.py",
        "category": "API & Contract Testing",
        "owner_role": "api-engineer",
        "status": "stable",
        "risk_level": "modifying",
        "inputs": ["--route", "--status", "--body", "--delay-ms"],
        "outputs": ["Stubbed HTTP/GraphQL response mocks"],
        "description": "Network interception shield stubbing external routes and injecting chaos network faults."
    },
    "export_postman_collection.py": {
        "command": "python tools/export_postman_collection.py",
        "category": "API & Contract Testing",
        "owner_role": "api-engineer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--matrix", "--output"],
        "outputs": ["Postman Collection v2.1.0 (.json)"],
        "description": "Exports API test matrices into runnable Postman Collections with pre-request scripts."
    },
    "traffic_session_converter.py": {
        "command": "python tools/traffic_session_converter.py",
        "category": "API & Contract Testing",
        "owner_role": "api-engineer",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--har", "--output"],
        "outputs": ["Executable API test scripts"],
        "description": "Converts recorded HAR traffic sessions into executable API automation test cases."
    }
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

    all_py_files = sorted([f for f in os.listdir(TOOLS_DIR) if f.endswith(".py") and not f.startswith("__")])

    for fname in all_py_files:
        meta = TOOL_REGISTRY_METADATA.get(fname)
        full_path = os.path.join(TOOLS_DIR, fname)

        # Fallback docstring extraction
        doc_summary = ""
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read(), fname)
                doc = ast.get_docstring(tree)
                if doc:
                    doc_summary = doc.strip().split("\n")[0].strip("- ")
        except Exception:
            doc_summary = fname

        if meta:
            entry = {
                "file": f"tools/{fname}",
                "command": meta["command"],
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
            entry = {
                "file": f"tools/{fname}",
                "command": f"python tools/{fname}",
                "category": "Testing & Utilities" if is_test_tool else "Auxiliary Utilities",
                "owner_role": "orchestrator",
                "status": "stable" if os.path.getsize(full_path) > 1000 else "experimental",
                "risk_level": "read_only",
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
        f"*Catalog generated: `{catalog['updated_at']}` by `tools/generate_tool_catalog.py`*"
    ])

    return "\n".join(md)


def main() -> int:
    catalog = build_catalog()

    # Write JSON catalog
    json_path = os.path.join(TOOLS_DIR, "TOOL_CATALOG.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    # Write Markdown catalog
    docs_dir = os.path.join(REPO_ROOT, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    md_path = os.path.join(docs_dir, "TOOL_CATALOG.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(format_markdown_catalog(catalog))

    print("=" * 68)
    print("    SYNAPSE HUB — TOOLING ECOSYSTEM CATALOG GENERATOR")
    print("=" * 68)
    print(f"  Indexed Tools      : {catalog['total_tools']} tools")
    print(f"  Stable Tools       : {catalog['stable_count']} (Production Ready)")
    print(f"  Experimental Tools : {catalog['experimental_count']}")
    print(f"  JSON Catalog       : {os.path.relpath(json_path, REPO_ROOT)}")
    print(f"  Markdown Runbook   : {os.path.relpath(md_path, REPO_ROOT)}")
    print("=" * 68)
    print("✅ Tool catalog synchronized successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
