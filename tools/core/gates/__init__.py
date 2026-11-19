#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Modular Definition of Done (DoD) Quality Gates package for Synapse Hub.
"""

from tools.core.gates.base import (
    BOM_EXTENSIONS,
    FORBIDDEN_PATH_PATTERNS,
    GATES_DIR,
    LAST_GATE_METRICS,
    MOJIBAKE_INDICATORS,
    PARALLEL_STATIC_GATE_KEYS,
    REPO_ROOT,
    SCRIPT_DIR,
    BaseGate,
    GateResult,
    check_python_ast_integrity,
    detect_repo_mode,
    gate_0_author_integrity,
    get_git_commit_sha,
    get_scoped_git_files,
    has_python_sources,
    is_page_class_path,
    load_synapse_config,
    parse_pytest_metrics,
    parse_pytest_output,
    print_header,
    resolve_target_repo,
    resolve_tool_path,
    safe_print,
    verify_engine_preflight,
)
from tools.core.gates.gate_01_utf8 import Gate01UTF8, gate_1_bom_check
from tools.core.gates.gate_02_portability import Gate02Portability, gate_2_path_portability
from tools.core.gates.gate_03_clean_pom import Gate03CleanPOM, gate_3_clean_pom
from tools.core.gates.gate_04_ai_docs import Gate04AIDocs, gate_4_ai_docs_lint
from tools.core.gates.gate_05_blacklist import Gate05Blacklist, gate_5_cleanup_blacklist
from tools.core.gates.gate_06_credentials import Gate06Credentials, gate_6_credential_security
from tools.core.gates.gate_07_infer_linter import Gate07InferLinter, gate_7_infer_linter
from tools.core.gates.gate_08_mutation import Gate08Mutation, gate_8_micro_mutator
from tools.core.gates.gate_09_collisions import Gate09Collisions, gate_9_skill_collision
from tools.core.gates.gate_10_perf_sla import Gate10PerfSLA, gate_10_performance_sla

ALL_GATES = [
    Gate01UTF8(),
    Gate02Portability(),
    Gate03CleanPOM(),
    Gate04AIDocs(),
    Gate05Blacklist(),
    Gate06Credentials(),
    Gate07InferLinter(),
    Gate08Mutation(),
    Gate09Collisions(),
    Gate10PerfSLA(),
]

__all__ = [
    "BaseGate",
    "GateResult",
    "ALL_GATES",
    "BOM_EXTENSIONS",
    "FORBIDDEN_PATH_PATTERNS",
    "GATES_DIR",
    "LAST_GATE_METRICS",
    "MOJIBAKE_INDICATORS",
    "PARALLEL_STATIC_GATE_KEYS",
    "REPO_ROOT",
    "SCRIPT_DIR",
    "check_python_ast_integrity",
    "detect_repo_mode",
    "gate_0_author_integrity",
    "get_git_commit_sha",
    "get_scoped_git_files",
    "has_python_sources",
    "is_page_class_path",
    "load_synapse_config",
    "parse_pytest_metrics",
    "parse_pytest_output",
    "print_header",
    "resolve_target_repo",
    "resolve_tool_path",
    "safe_print",
    "verify_engine_preflight",
    "gate_1_bom_check",
    "Gate01UTF8",
    "gate_2_path_portability",
    "Gate02Portability",
    "gate_3_clean_pom",
    "Gate03CleanPOM",
    "gate_4_ai_docs_lint",
    "Gate04AIDocs",
    "gate_5_cleanup_blacklist",
    "Gate05Blacklist",
    "gate_6_credential_security",
    "Gate06Credentials",
    "gate_7_infer_linter",
    "Gate07InferLinter",
    "gate_8_micro_mutator",
    "Gate08Mutation",
    "gate_9_skill_collision",
    "Gate09Collisions",
    "gate_10_performance_sla",
    "Gate10PerfSLA",
]
