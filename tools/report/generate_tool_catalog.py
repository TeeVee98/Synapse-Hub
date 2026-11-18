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
        "command": "python tools/verify_all.py",
        "category": "Quality Gates",
        "owner_role": "quality-gatekeeper",
        "status": "stable",
        "risk_level": "read_only",
        "inputs": ["--mode auto|hub|target", "--test-cmd", "--format text|json|junit"],
        "outputs": ["Console report", "Exit code 0/1", "reports/PROJECT_HEALTH_REPORT.md"],
        "description": "One-command 10 Quality Gates Definition of Done (DoD) verification sentinel."
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
        "risk_level": "modifying",
        "inputs": ["--output-dir", "--format zip|tar.gz|both", "--verify-archive"],
        "outputs": ["dist/synapse-hub-vX.Y.Z.zip", "dist/*-checksums.sha256"],
        "description": "Enterprise release packager preserving .github/workflows and generating SHA-256 provenance."
    },
    "db_sandbox.py": {
        "command": "python tools/db_sandbox.py",
        "category": "Sandboxing & Isolation",
        "owner_role": "failure-analyst",
        "status": "stable",
        "risk_level": "modifying",
        "inputs": ["--mode audit|purge|restore", "--db-path", "--consent"],
        "outputs": ["Database snapshots", "Purge audit logs"],
        "description": "Database state isolation sentinel with granular consent-governed snapshot and purge capabilities."
    },
    "reversible_sandbox.py": {
        "command": "python tools/reversible_sandbox.py",
        "category": "Sandboxing & Isolation",
        "owner_role": "failure-analyst",
        "status": "stable",
        "risk_level": "modifying",
        "inputs": ["--execute-stateful", "--rollback", "--recover-wal"],
        "outputs": [".agent_memory/undo_wal.jsonl", "Reversible execution rollbacks"],
        "description": "Two-phase commit write-ahead logging (WAL) execution sandbox providing crash-resilient rollback guarantees."
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

    all_tool_entries = []
    for root, dirs, files in os.walk(TOOLS_DIR):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
        for f in sorted(files):
            if f.endswith(".py") and not f.startswith("__"):
                rel_path = os.path.relpath(os.path.join(root, f), REPO_ROOT).replace("\\", "/")
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
        f"*Catalog generated: `{catalog['updated_at']}` by `tools/generate_tool_catalog.py`*"
    ])

    return "\n".join(md)


def generate_tool_index(catalog: Dict[str, Any]) -> Dict[str, Any]:
    """Generates Tier-1 lightweight tool index grouped by owner_role (< 12 KB)."""
    import re
    personas = [
        "orchestrator", "live-explorer", "pom-crafter", "test-runner",
        "failure-analyst", "quality-gatekeeper", "api-engineer",
        "perf-engineer", "test-designer"
    ]
    by_role: Dict[str, Dict[str, str]] = {p: {} for p in personas}
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
    print("=" * 68)
    print("✅ Tool catalog synchronized successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
