# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub — Enterprise AI Agent Quality Engineering & Automated Testing Tooling Suite.
========================================================================================
Author: Thế Vị (@TeeVee98)
Repository: https://github.com/TeeVee98/Synapse-Hub
License: MIT

Domain Packages:
- tools.core: Execution engines, 10 DoD Quality Gates, setup, CLI, AST maps.
- tools.lint: Static code defect, encoding, author integrity, and AI doc sentinels.
- tools.heal: Locator healing, episodic Reflexion memory, and agentless patching.
- tools.context: AI Context engineering, token economy, log distillation, AST slicing.
- tools.security: OWASP ASVS auditing, CVSS scoring, DAST, and compliance guards.
- tools.api: OpenAPI matrix generation, contract drift, traffic recording, and mocking.
- tools.perf: Flakiness detection, JMeter plans, BFCL benchmarks, and matrix sharding.
- tools.report: HTML dashboards, spreadsheets, telemetry correlation, and metrics.
- tools.design: Gherkin suites, pairwise generation, and test story analysis.
- tools.transpiler: Universal Intermediate Representation (IR) cross-language compiler.
- tools.orchestration: Multi-Agent FSM enforcers, event stream, and memory systems.
- tools.mcp: Model Context Protocol servers (core QA, Excel, and Word manipulation).
- tools.contrib: Specialized auxiliary extension tools and integrations.
"""

__version__ = "4.5.1"
__author__ = "Thế Vị (@TeeVee98)"

import os
import sys
import importlib
import importlib.util
from importlib.abc import MetaPathFinder, Loader

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
_DOMAINS = ["core", "lint", "heal", "context", "security", "api", "perf", "design", "report", "transpiler", "orchestration", "mcp", "contrib"]

# Canonical Tool-to-Domain Registry (165 Tools)
_TOOL_DOMAIN_MAP = {
    "adapters": "core",
    "analyze_project": "core",
    "author_integrity": "core",
    "bm25_retriever": "core",
    "bump_version": "core",
    "cache_resolver": "core",
    "check_env": "core",
    "check_version_sync": "core",
    "circuit_breaker": "core",
    "cli": "core",
    "cli_runtime": "core",
    "codemod_tool_imports": "core",
    "config_decoupler": "core",
    "count_tokens": "core",
    "db_sandbox": "core",
    "debt_harvester": "core",
    "distill_log": "core",
    "distill_skill": "core",
    "file_lock": "core",
    "fsm_enforcer": "core",
    "fsm_middleware": "core",
    "git_worktree_manager": "core",
    "hub_publisher": "core",
    "i18n": "core",
    "init_config": "core",
    "memory_bus": "core",
    "package_release": "core",
    "process_supervisor": "core",
    "project_state": "core",
    "provider_usage_adapter": "core",
    "repo_map": "core",
    "rules_router": "core",
    "rule_harvester": "core",
    "session_vault": "core",
    "setup_project": "core",
    "skillspector": "core",
    "skill_canonical_digest": "core",
    "skill_profiles": "core",
    "skill_vault": "core",
    "sync_agent_rules": "core",
    "sync_skills_manifest": "core",
    "task_memory_manager": "core",
    "telemetry": "core",
    "test_impact": "core",
    "test_memory_os": "core",
    "token_estimator": "core",
    "validate_host_interop": "core",
    "verify_all": "core",
    "watch_mode": "core",
    "agent_canary": "lint",
    "ai_eval_sentinel": "lint",
    "flaky_detector": "lint",
    "git_pre_commit_guard": "lint",
    "humanize_linter": "lint",
    "infer_linter": "lint",
    "lint_ai_docs": "lint",
    "micro_mutator": "lint",
    "mipro_assertion_tuner": "lint",
    "pre_bash_guard": "lint",
    "pre_push_guard": "lint",
    "skill_collision_guard": "lint",
    "update_sentinel": "lint",
    "validate_groovy_scripts": "lint",
    "validate_skills_schema": "lint",
    "agentless_patcher": "heal",
    "assertion_optimizer": "heal",
    "ast_assertion_optimizer": "heal",
    "auto_heal": "heal",
    "auto_heal_reflexion": "heal",
    "ci_healing_hook": "heal",
    "heal_pr_automator": "heal",
    "heuristic_locator_matcher": "heal",
    "live_visual_healer": "heal",
    "lookup_xpath": "heal",
    "reversible_sandbox": "heal",
    "textgrad_mutation_optimizer": "heal",
    "visual_som_helper": "heal",
    "ast_cache": "context",
    "benchmark_swarm_context": "context",
    "context_slicer": "context",
    "lookup_tc": "context",
    "token_telemetry": "context",
    "trace_data_flow": "context",
    "asvs_auditor": "security",
    "cvss_calculator": "security",
    "pentest_scope_guard": "security",
    "regulatory_compliance": "security",
    "safety_firewall": "security",
    "security_coverage_ledger": "security",
    "security_scanner": "security",
    "api_drift_sentinel": "api",
    "api_fuzzer": "api",
    "contract_validator": "api",
    "e2e_flow_prober": "api",
    "fuzz_payloads": "api",
    "generate_api_matrix": "api",
    "network_mock_shield": "api",
    "pairwise_generator": "api",
    "spec_drift_sentinel": "api",
    "vcr_cassette_guard": "api",
    "_openapi_parser": "api",
    "benchmark_perf_runner": "perf",
    "chaos_resilience_probe": "perf",
    "heap_leak_analyzer": "perf",
    "jtl_analyzer": "perf",
    "mobile_resilience_sentinel": "perf",
    "newman_analyzer": "perf",
    "observability_tester": "perf",
    "slow_test_profiler": "perf",
    "break_ui_generator": "design",
    "mechanical_ui_gate": "design",
    "smart_visual_masker": "design",
    "visual_diff_canvas": "design",
    "bug_reporter": "report",
    "coverage_reporter": "report",
    "generate_allure_report": "report",
    "generate_sbom": "report",
    "generate_test_reports": "report",
    "generate_tool_catalog": "report",
    "output_formatter": "report",
    "pinpoint_failure": "report",
    "telemetry_correlator": "report",
    "trend_analytics": "report",
    "gherkin_suite": "transpiler",
    "omni_emitter": "transpiler",
    "omni_parser": "transpiler",
    "omni_transpiler": "transpiler",
    "traffic_session_converter": "transpiler",
    "universal_ir": "transpiler",
    "autogen_qa_broker": "orchestration",
    "browsergym_eval": "orchestration",
    "dspy_qa_signatures": "orchestration",
    "goldfish_review": "orchestration",
    "matrix_sharder": "orchestration",
    "qa_event_stream": "orchestration",
    "runaway_stopper": "orchestration",
    "senior_code_review": "orchestration",
    "swe_qa_aci": "orchestration",
    "synapse_doctor": "orchestration",
    "synapse_observer": "orchestration",
    "synapse_qa_bench": "orchestration",
    "tot_exploratory_tester": "orchestration",
    "typed_prompt_signatures": "orchestration",
    "mcp_docx_server": "mcp",
    "mcp_excel_server": "mcp",
    "mcp_server": "mcp",
    "cldr_l10n_verifier": "contrib",
    "dashboard_generator": "contrib",
    "diagram_architect": "contrib",
    "etl_data_reconciler": "contrib",
    "export_postman_collection": "contrib",
    "generate_jmx_plan": "contrib",
    "generate_tc_from_story": "contrib",
    "interview_story": "contrib",
    "jira_sync": "contrib",
    "md_to_xlsx": "contrib",
    "openxml_guard": "contrib",
    "payment_interop_simulator": "contrib",
    "slide_deck_exporter": "contrib",
    "template_excel_exporter": "contrib",
    "tmmi_auditor": "contrib",
    "tms_sync_bridge": "contrib",
    "ui_server": "contrib",
    "vpat_exporter": "contrib",
    "wcag_audit": "contrib",
    "welcome_page": "contrib"
}

# Bootstrap all domain packages into sys.path
for _d in _DOMAINS:
    _dp = os.path.join(_TOOLS_DIR, _d)
    if _dp not in sys.path:
        sys.path.insert(0, _dp)

if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

def resolve_tool_path(name: str, domain: str = "") -> str:
    """Resolves the canonical filesystem path for any tool script across 13 domains."""
    clean_name = name[:-3] if name.endswith(".py") else name
    d = domain or _TOOL_DOMAIN_MAP.get(clean_name, "")
    if d:
        p = os.path.join(_TOOLS_DIR, d, f"{clean_name}.py")
        if os.path.exists(p):
            return p
    p_direct = os.path.join(_TOOLS_DIR, f"{clean_name}.py")
    if os.path.exists(p_direct):
        return p_direct
    return os.path.join(_TOOLS_DIR, d, f"{clean_name}.py") if d else p_direct


class _AliasLoader(Loader):
    def __init__(self, target_module):
        self.target_module = target_module

    def create_module(self, spec):
        return self.target_module

    def exec_module(self, module):
        pass


class _ToolsDomainRedirectFinder(MetaPathFinder):
    """Dynamic MetaPathFinder providing seamless transparent redirection from tools.<tool> to tools.<domain>.<tool>."""
    def find_spec(self, fullname, path, target=None):
        if fullname.startswith("tools."):
            parts = fullname.split(".")
            if len(parts) == 2:
                tool_name = parts[1]
                if tool_name in _TOOL_DOMAIN_MAP and tool_name not in _DOMAINS:
                    domain = _TOOL_DOMAIN_MAP[tool_name]
                    target_name = f"tools.{domain}.{tool_name}"
                    try:
                        target_module = importlib.import_module(target_name)
                        tools_mod = sys.modules.get("tools")
                        if tools_mod is not None:
                            setattr(tools_mod, tool_name, target_module)
                        return importlib.util.spec_from_loader(fullname, _AliasLoader(target_module))
                    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                        return None
        return None


if not any(isinstance(finder, _ToolsDomainRedirectFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, _ToolsDomainRedirectFinder())


def __getattr__(name: str):
    """Dynamic attribute resolver for bare tools.<name> access."""
    if name in _TOOL_DOMAIN_MAP:
        domain = _TOOL_DOMAIN_MAP[name]
        mod = importlib.import_module(f"tools.{domain}.{name}")
        globals()[name] = mod
        return mod
    raise AttributeError(f"module 'tools' has no attribute '{name}'")


def __dir__():
    return sorted(list(globals().keys()) + list(_TOOL_DOMAIN_MAP.keys()) + _DOMAINS)

# Expose domain packages
from tools import (  # noqa: F401
    api,
    context,
    contrib,
    core,
    design,
    heal,
    lint,
    mcp,
    orchestration,
    perf,
    report,
    security,
    transpiler,
)

__all__ = _DOMAINS + list(_TOOL_DOMAIN_MAP.keys()) + ["resolve_tool_path"]
