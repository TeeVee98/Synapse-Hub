#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Enterprise Model Context Protocol (MCP) Standard Server
-------------------------------------------------------
Exposes centralized tools/ capabilities as standardized JSON-RPC 2.0 MCP Tools
compatible with Google Antigravity, Cursor, Claude Desktop, Windsurf, and any MCP client.
Communicates via standard JSON-RPC stdio.
"""
import os
import sys
import io
import json
import logging
import re
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Set

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

logger = logging.getLogger("synapse.mcp_server")

# Enforce UTF-8 stdio encoding
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
        sys.stdin.reconfigure(encoding='utf-8')
    except (AttributeError, io.UnsupportedOperation) as exc:
        logger.debug("Failed to reconfigure stdio encoding: %s", exc)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HUB_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
sys.path.insert(0, SCRIPT_DIR)

from tools.core import verify_all
from tools.core import analyze_project
from tools.core import setup_project
from tools.heal import auto_heal
from tools.security import safety_firewall
from tools.api import api_drift_sentinel
from tools.core import cache_resolver
from tools.core import distill_log
from tools.lint import micro_mutator
from tools.heal import heal_pr_automator
from tools.orchestration import matrix_sharder
from tools.contrib import tms_sync_bridge
from tools.core import db_sandbox
from tools.transpiler import traffic_session_converter
from tools.heal import visual_som_helper
from tools.transpiler import gherkin_suite
from tools.api import api_fuzzer

SERVER_NAME = "enterprise-agent-qa"
SERVER_VERSION = "4.11.0"

MCP_TOOLS = [
    {
        "name": "synapse_lint",
        "description": "Runs Meta Infer-style static defect sentinel and AST analyzer catching fake passes, 0-assertion tests, static sleeps, and swallowed exceptions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_path": {"type": "string", "description": "Target file or directory to lint (defaults to project root)."}
            }
        }
    },
    {
        "name": "synapse_verify",
        "description": "Validates the 11 Definition-of-Done (DoD) Quality Gates (UTF-8, paths, Clean POM, AI docs, blacklist, credentials, infer linter, mutation, collisions, SLA, author provenance).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Absolute or relative path to target repository. Defaults to CWD."}
            }
        }
    },
    {
        "name": "synapse_lsp_health",
        "description": "Runs diagnostic health check on the Universal QA Language Server (LSP 3.17 stdio) and returns protocol version and latency telemetry.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Workspace root directory for cross-file POM indexing. Defaults to CWD."}
            }
        }
    },
    {
        "name": "synapse_mutate",
        "description": "Executes AST micro-mutation testing against test suites to ensure assertions are sensitive and kill injected mutants.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "test_file": {"type": "string", "description": "Target test file or directory to mutate."},
                "sample_rate": {"type": "number", "description": "Mutation sample rate (0.0 - 1.0, default: 0.2)."}
            }
        }
    },
    {
        "name": "synapse_distill_logs",
        "description": "Distills large noisy test execution logs (>500 lines) into a concise, token-efficient summary highlighting errors and stack traces.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "log_path": {"type": "string", "description": "Path to test log or console output file."}
            },
            "required": ["log_path"]
        }
    },
    {
        "name": "synapse_security_scan",
        "description": "Scans project dependencies, credentials, and API tokens for CVE vulnerabilities and security leaks in fail-closed mode.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to project to scan. Defaults to CWD."},
                "strict": {"type": "boolean", "description": "Fail-closed strict mode (default: true)."}
            }
        }
    },
    {
        "name": "verify_all_gates",
        "description": "Validates the 11 Quality Gates Definition of Done (UTF-8, paths, Clean POM, AI docs, blacklist, security, infer linter, micro-mutator, skill collision, performance SLA, author provenance) with pre-flight integrity check.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Absolute or relative path to the target repository. Defaults to CWD."}
            }
        }
    },
    {
        "name": "analyze_project",
        "description": "Executes 5-in-1 project health and AST intelligence analysis, creating PROJECT_HEALTH_REPORT.md and repo_map.txt.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Target project repository directory to audit."}
            }
        }
    },
    {
        "name": "setup_project",
        "description": "Autonomous 1-click bootstrap of any test project: detects stack, generates PROJECT_AI_GUIDE.md, installs Git hook, and maps AST.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to target project to bootstrap."},
                "dry_run": {"type": "boolean", "description": "Preview setup without modifying filesystem (default: false)."},
                "no_global": {"type": "boolean", "description": "Local-only mode: do not touch ~/.gemini (default: true)."}
            }
        }
    },
    {
        "name": "auto_heal_failure",
        "description": "Diagnoses test failures in 0.1s from JUnit XML and queries semantic memory cache for proven patches.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_dir": {"type": "string", "description": "Target project root directory."},
                "junit_xml_path": {"type": "string", "description": "Optional direct path to failing JUnit XML report."}
            }
        }
    },
    {
        "name": "check_action_safety",
        "description": "Action Safety Firewall: verifies whether an intended UI action (click, fill) touches destructive elements (Delete, Pay, Drop).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_type": {"type": "string", "description": "Action type (e.g. click, fill, submit)."},
                "element_text": {"type": "string", "description": "Text or label of target DOM element."},
                "selector": {"type": "string", "description": "CSS or XPath selector of element."}
            }
        }
    },
    {
        "name": "check_contract_drift",
        "description": "Compares two OpenAPI / Swagger specifications and detects breaking changes (removed endpoints, changed types, newly required params).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "old_spec_path": {"type": "string", "description": "Path to baseline OpenAPI JSON file."},
                "new_spec_path": {"type": "string", "description": "Path to current OpenAPI JSON file."}
            },
            "required": ["old_spec_path", "new_spec_path"]
        }
    },
    {
        "name": "query_memory_cache",
        "description": "Queries the 0-token SQLite semantic memory cache for known UI exceptions and proven repair patches.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "error_signature": {"type": "string", "description": "Exception trace or error message to lookup."}
            },
            "required": ["error_signature"]
        }
    },
    {
        "name": "distill_log",
        "description": "Filters verbose CLI or Gradle build logs, retaining only actionable stacktraces and pointers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "raw_log_text": {"type": "string", "description": "Raw terminal log output to compress."}
            },
            "required": ["raw_log_text"]
        }
    },
    {
        "name": "run_micro_mutation",
        "description": "Injects syntactic micro-mutants (flipping operators, booleans) to verify that AI-generated test assertions are robust.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_path": {"type": "string", "description": "Path to test script or directory to mutate."}
            }
        }
    },
    {
        "name": "plan_healing_pr",
        "description": "Calculates composite confidence score for healed locators and formats an automated Pull Request draft.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page_file": {"type": "string", "description": "Page Class path."},
                "old_locator": {"type": "string", "description": "Original stale selector."},
                "new_locator": {"type": "string", "description": "Healed replacement selector."},
                "aom_score": {"type": "number", "description": "AOM match score 0.0-1.0."},
                "spatial_score": {"type": "number", "description": "Spatial score 0.0-1.0."},
                "visual_score": {"type": "number", "description": "Visual SSIM score 0.0-1.0."}
            },
            "required": ["page_file", "old_locator", "new_locator"]
        }
    },
    {
        "name": "shard_test_matrix",
        "description": "Distributes test cases evenly across N parallel CI/CD runners using Duration-Balanced Bin-Packing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_dir": {"type": "string", "description": "Target project root directory."},
                "num_shards": {"type": "integer", "description": "Number of parallel workers (default 4)."}
            }
        }
    },
    {
        "name": "pull_alm_story",
        "description": "Pulls User Story and Acceptance Criteria (Given-When-Then) from Jira REST API v3 (or mock simulation) for test generation context.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_key": {"type": "string", "description": "ALM Issue Key (e.g. PROJ-1042)."}
            },
            "required": ["issue_key"]
        }
    },
    {
        "name": "report_alm_defect",
        "description": "Creates an automated Bug Ticket in Jira/TMS with full diagnostic reproduction steps, stack trace, and screenshot attachments.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_key": {"type": "string", "description": "Target project key (e.g. PROJ)."},
                "test_case_id": {"type": "string", "description": "Failing test case ID."},
                "summary": {"type": "string", "description": "Defect summary."},
                "error_message": {"type": "string", "description": "Exact failure error message."},
                "stack_trace": {"type": "string", "description": "Exception stack trace."},
                "screenshot_path": {"type": "string", "description": "Path to FAILED screenshot image."}
            },
            "required": ["project_key", "test_case_id", "summary", "error_message"]
        }
    },
    {
        "name": "manage_db_sandbox",
        "description": "Zero-pollution ephemeral database manager: creates baseline snapshot, restores pristine DB state, or executes transaction savepoints.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["snapshot", "restore", "audit_and_purge"], "description": "Sandbox operation to execute."},
                "db_path": {"type": "string", "description": "Path to database file (optional for SQLite)."},
                "snapshot_id": {"type": "string", "description": "Snapshot identifier (default: pristine_baseline)."},
                "dry_run": {"type": "boolean", "default": True, "description": "For restore and audit_and_purge: preview actions without modifying database (default: true)."},
                "consent": {"type": "boolean", "default": False, "description": "Explicit consent acknowledgement for destructive state modification when dry_run=False."}
            },
            "required": ["action"]
        }
    },
    {
        "name": "convert_traffic_session",
        "description": "Shift-Right Replay: Transforms recorded HTTP Archive (.har) or RUM session into PII-sanitized Playwright test suite.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string", "description": "Path to .har or JSON network session file."},
                "test_name": {"type": "string", "description": "Generated test suite name."}
            },
            "required": ["input_file"]
        }
    },
    {
        "name": "resolve_visual_som_coordinates",
        "description": "Multimodal Vision Grounding: Resolves click coordinates (x, y) on HTML5 Canvas or Shadow DOM using Set-of-Marks (SoM).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "Path to screenshot image."},
                "target_label": {"type": "string", "description": "Target element label or text."},
                "mark_id": {"type": "integer", "description": "Specific Mark ID to click."}
            }
        }
    },
    {
        "name": "compile_gherkin_suite",
        "description": "Compiles Gherkin .feature files into an expanded test matrix, hub Universal IR and a proven-vs-owed coverage-gap report (0 LLM tokens).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "A .feature file or directory containing .feature files."}
            },
            "required": ["target"]
        }
    },
    {
        "name": "fuzz_api",
        "description": "Autonomous API fuzzing (active, dry-run by default for safety) or offline passive spec audit with ZAP-style severity taxonomy.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_url": {"type": "string", "description": "Base URL of target API (non-production allowlist enforced)."},
                "spec_path": {"type": "string", "description": "Path or URL to OpenAPI/Swagger JSON spec."},
                "mode": {"type": "string", "enum": ["active", "passive"], "default": "passive", "description": "active fuzzing or passive offline spec audit (default: passive)."},
                "dry_run": {"type": "boolean", "default": True, "description": "Deterministic offline mock (default true for safety)."},
                "consent": {"type": "boolean", "default": False, "description": "Explicit consent acknowledgement for active mutations when mode=active and dry_run=False."}
            },
            "required": ["base_url"]
        }
    },
    {
        "name": "symbol_overview",
        "description": "Returns hierarchical AST symbol overview (classes, methods, functions) for a repository file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Repository root path."},
                "file_path": {"type": "string", "description": "Target file path."},
                "depth": {"type": "integer", "default": 2, "description": "Maximum nesting depth."}
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "find_symbol",
        "description": "Finds matching symbols by Serena-style name path (e.g., ClassName/method_name).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Repository root path."},
                "name_path": {"type": "string", "description": "Symbol name path pattern."},
                "file_path": {"type": "string", "description": "Optional target file filter."},
                "include_body": {"type": "boolean", "default": False}
            },
            "required": ["name_path"]
        }
    },
    {
        "name": "find_referencing_symbols",
        "description": "Finds AST symbol references across a file or repository.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Repository root path."},
                "symbol_name": {"type": "string", "description": "Target symbol name."},
                "file_path": {"type": "string", "description": "Optional target file filter."}
            },
            "required": ["symbol_name"]
        }
    },
    {
        "name": "replace_symbol_body",
        "description": "Atomically replaces a target symbol body with AST syntax verification and automatic rollback on failure.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Repository root path."},
                "file_path": {"type": "string", "description": "Target file path."},
                "name_path": {"type": "string", "description": "Target symbol name path."},
                "new_body": {"type": "string", "description": "Replacement symbol body."}
            },
            "required": ["file_path", "name_path", "new_body"]
        }
    },
    {
        "name": "temporal_graph_add_episode",
        "description": "Ingests a bi-temporal episode with facts into TemporalContextGraph and invalidates conflicting edges.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "db_path": {"type": "string", "description": "SQLite DB path."},
                "source": {"type": "string", "description": "Episode source label."},
                "content": {"type": "string", "description": "Episode description."},
                "reference_time": {"type": "string", "description": "ISO-8601 event timestamp."},
                "facts": {"type": "array", "description": "List of [source_id, relation, target_id, fact] tuples."}
            },
            "required": ["source", "content", "reference_time"]
        }
    },
    {
        "name": "temporal_graph_query",
        "description": "Queries bi-temporal facts and community summaries at a specific point-in-time (local/global/hybrid).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "db_path": {"type": "string", "description": "SQLite DB path."},
                "query": {"type": "string", "description": "Query string."},
                "as_of": {"type": "string", "description": "Optional ISO-8601 point-in-time timestamp."},
                "mode": {"type": "string", "enum": ["local", "global", "hybrid"], "default": "hybrid"},
                "limit": {"type": "integer", "default": 20}
            },
            "required": ["query"]
        }
    },
    {
        "name": "sequential_think",
        "description": "Records a structured sequential thought step with revision, branching, and bounded thought-size validation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "thought": {"type": "string", "description": "Current reasoning step content."},
                "thought_number": {"type": "integer", "default": 1},
                "total_thoughts": {"type": "integer", "default": 1},
                "session_id": {"type": "string", "default": "default"},
                "branch_id": {"type": "string"}
            },
            "required": ["thought"]
        }
    },
    {
        "name": "challenge_assumption",
        "description": "Anti-sycophancy reasoning guard that flags agreement bias and generates counter-hypotheses and evidence prompts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "claim": {"type": "string", "description": "Claim or proposal to critically challenge."}
            },
            "required": ["claim"]
        }
    },
    {
        "name": "elicitation_pick",
        "description": "Progressive-disclosure 6-direction elicitation method picker (wrong, missing, premise, future, other-side, simplify).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["wrong", "missing", "premise", "future", "other-side", "simplify"]},
                "tier": {"type": "string", "enum": ["core", "more"], "default": "core"},
                "count": {"type": "integer", "default": 3},
                "spread": {"type": "boolean", "default": True}
            }
        }
    },
    {
        "name": "task_graph_ready",
        "description": "Queries the persistent SQLite TaskGraphMemory for unblocked open tasks (ready frontier).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "db_path": {"type": "string", "description": "Repo-local path to .synapse/task_graph.db."}
            }
        }
    },
    {
        "name": "memory_graph_query",
        "description": "Queries Synapse Hub's AssociativeMemory knowledge graph for related nodes and failure lessons.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keyword or node key to search in associative graph memory."},
                "limit": {"type": "integer", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "assess_idea_gate",
        "description": "Evaluates an idea across 6 explicit criteria and returns a go / needs-clarification / kill verdict.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string", "description": "Short kebab-case identifier."},
                "criteria": {"type": "object", "description": "Map of 6 criteria to strong|adequate|weak|unknown."},
                "concept_shaped": {"type": "boolean", "default": True}
            },
            "required": ["slug", "criteria"]
        }
    }
]


def _validate_safe_path(filepath: str, allowed_root: Optional[str] = None, allowed_exts: Optional[Set[str]] = None) -> str:
    """
    Validates that a path is safe and does not access restricted system paths or traverse outside the project root.
    Resolves symlinks via Path.resolve() and enforces cross-platform boundaries (Windows, macOS, Linux).
    """
    if not filepath or not isinstance(filepath, str):
        raise ValueError("File path must be a non-empty string")

    # Reject null bytes and Windows UNC network share paths
    if "\0" in filepath or filepath.startswith("\\\\"):
        raise PermissionError(f"Access denied: invalid or UNC path '{filepath}'")

    from tools.core.cli_runtime import get_repo_root
    effective_root = allowed_root or os.environ.get("SYNAPSE_PROJECT_ROOT") or get_repo_root()
    try:
        root_path = Path(effective_root).resolve()
        target_path = Path(filepath).resolve()
    except Exception as e:
        raise PermissionError(f"Access denied: cannot resolve path '{filepath}': {e}")

    # Case-insensitive path comparison across OS filesystems
    root_norm = os.path.normcase(str(root_path))
    target_norm = os.path.normcase(str(target_path))

    # Path must reside within the allowed root OR within the OS temporary directory
    temp_dir_norm = os.path.normcase(str(Path(tempfile.gettempdir()).resolve()))
    is_temp_path = target_norm == temp_dir_norm or target_norm.startswith(temp_dir_norm + os.sep)
    is_in_root = (target_norm == root_norm or target_norm.startswith(root_norm + os.sep))

    if not is_in_root and not is_temp_path:
        raise PermissionError(f"Access denied: path '{filepath}' resolves outside allowed project root '{root_path}'")

    # Reject explicit sensitive configuration / secret files and private keys
    base_name = target_path.name.lower()
    sensitive_exact = {
        ".env", ".env.local", ".env.production", ".env.staging", ".npmrc", ".netrc", ".git-credentials",
        "id_rsa", "id_ecdsa", "id_ed25519", "id_dsa", "credentials.json", "service-account.json"
    }
    sensitive_exts = {".pem", ".key", ".p12", ".pfx", ".pkcs12"}
    if base_name in sensitive_exact or base_name.startswith(".env.") or target_path.suffix.lower() in sensitive_exts:
        raise PermissionError(f"Access denied: path references sensitive credentials or secret file '{target_path.name}'")

    # Cross-platform sensitive system prefixes
    try:
        user_home = Path.home().resolve()
    except Exception:
        user_home = Path(os.path.expanduser("~")).resolve()

    sensitive_prefixes = [
        Path("/etc"), Path("/var/run"), Path("/proc"), Path("/sys"), Path("/dev"), Path("/root"), Path("/private/etc"),
        user_home / ".ssh",
        user_home / ".aws",
        user_home / ".gnupg",
        user_home / ".kube",
        user_home / ".docker",
        user_home / ".config" / "gh",
        user_home / "Library" / "Keychains",
    ]
    if sys.platform == "win32":
        for env_win in ("SystemRoot", "WINDIR", "APPDATA", "LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"):
            win_val = os.environ.get(env_win)
            if win_val:
                try:
                    sensitive_prefixes.append(Path(win_val).resolve())
                except OSError:
                    sensitive_prefixes.append(Path(win_val))

    temp_dir_norm = os.path.normcase(str(Path(tempfile.gettempdir()).resolve()))
    is_temp_path = target_norm == temp_dir_norm or target_norm.startswith(temp_dir_norm + os.sep)

    for sp in sensitive_prefixes:
        sp_norm = os.path.normcase(str(sp))
        if is_temp_path and sys.platform == "win32" and sp_norm in (
            os.path.normcase(os.environ.get("LOCALAPPDATA", "")),
            os.path.normcase(os.environ.get("APPDATA", "")),
        ):
            continue
        if target_norm == sp_norm or target_norm.startswith(sp_norm + os.sep):
            raise PermissionError(f"Access denied: path references restricted system directory '{sp}'")

    if allowed_exts:
        ext = target_path.suffix.lower()
        if ext not in allowed_exts and not target_path.is_dir():
            raise PermissionError(f"Access denied: file extension '{ext}' is not permitted")

    return str(target_path)


def _handle_verify_all_gates(arguments: Dict[str, Any]) -> str:
    repo = _validate_safe_path(arguments.get("repo_path") or os.getcwd())
    mode = verify_all.detect_repo_mode(repo)
    if not verify_all.verify_engine_preflight(repo, mode=mode, silent=True):
        return "[DoD BLOCKED] Pre-flight Engine Integrity Guard failed: Author Attribution / MIT License Violated."
    passed = True
    gates = [
        ("Gate 1: UTF-8 No BOM", verify_all.gate_1_bom_check),
        ("Gate 2: Path Portability", verify_all.gate_2_path_portability),
        ("Gate 3: Clean POM", verify_all.gate_3_clean_pom),
        ("Gate 4: AI Docs Linter", verify_all.gate_4_ai_docs_lint),
        ("Gate 5: Temp Blacklist", verify_all.gate_5_cleanup_blacklist),
        ("Gate 6: Credential Security", verify_all.gate_6_credential_security),
        ("Gate 7: Infer Linter", verify_all.gate_7_infer_linter),
        ("Gate 8: AST Mutation Sentinel", verify_all.gate_8_micro_mutator),
        ("Gate 9: Skill Collision Guard", verify_all.gate_9_skill_collision),
        ("Gate 10: Performance & SLA Sentinel", verify_all.gate_10_performance_sla),
    ]
    results = []
    for g_name, g_fn in gates:
        res = g_fn(repo, mode=mode)
        results.append(f"{g_name}: {'PASS' if res else 'FAIL'}")
        if not res:
            passed = False
    summary = "100% ALL 10 GATES PASSED" if passed else "VERIFICATION FAILED"
    return f"[{summary}]\n" + "\n".join(results)


def _handle_analyze_project(arguments: Dict[str, Any]) -> str:
    repo = _validate_safe_path(arguments.get("repo_path") or os.getcwd())
    code = analyze_project.run_full_analysis(repo)
    return f"Project Analysis finished with exit code {code}. Report saved at {os.path.join(repo, 'PROJECT_HEALTH_REPORT.md')}."


def _handle_setup_project(arguments: Dict[str, Any]) -> str:
    repo = _validate_safe_path(arguments.get("repo_path") or os.getcwd())
    dry_run = bool(arguments.get("dry_run", False))
    no_global = bool(arguments.get("no_global", True))
    code = setup_project.run_setup(
        repo,
        dry_run=dry_run,
        no_global=no_global,
        no_git_hook=True,
        no_browser=True,
        open_browser=False
    )
    mode_label = " (DRY-RUN)" if dry_run else ""
    return f"Project Setup finished with exit code {code}{mode_label}."


def _handle_auto_heal_failure(arguments: Dict[str, Any]) -> str:
    target = _validate_safe_path(arguments.get("target_dir") or os.getcwd())
    xml = _validate_safe_path(arguments["junit_xml_path"]) if arguments.get("junit_xml_path") else None
    plan = auto_heal.diagnose_and_plan_heal(target, xml)
    return json.dumps(plan, indent=2)


def _handle_check_action_safety(arguments: Dict[str, Any]) -> str:
    auth = safety_firewall.inspect_and_authorize(
        action_type=arguments.get("action_type", "click"),
        text=arguments.get("element_text", ""),
        selector=arguments.get("selector", ""),
        force=False
    )
    return json.dumps(auth, indent=2)


def _handle_check_contract_drift(arguments: Dict[str, Any]) -> str:
    old_path = _validate_safe_path(arguments["old_spec_path"])
    new_path = _validate_safe_path(arguments["new_spec_path"])
    old_data = api_drift_sentinel.load_spec(old_path)
    new_data = api_drift_sentinel.load_spec(new_path)
    analysis = api_drift_sentinel.compare_specs(old_data, new_data)
    return api_drift_sentinel.generate_markdown_report(analysis, old_path, new_path)


def _handle_query_memory_cache(arguments: Dict[str, Any]) -> str:
    res = cache_resolver.query_solution(arguments["error_signature"])
    return json.dumps(res, indent=2) if res else "No matching solution found in memory cache."


def _handle_distill_log(arguments: Dict[str, Any]) -> str:
    return distill_log.distill_log_content(arguments["raw_log_text"])


def _handle_run_micro_mutation(arguments: Dict[str, Any]) -> str:
    target = _validate_safe_path(
        arguments.get("target_path") or os.getcwd(),
        allowed_exts={".py", ".ts", ".js", ".groovy", ".java"}
    )
    if os.path.isdir(target):
        mutants = micro_mutator.scan_directory_for_mutants(target)
    else:
        with open(target, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        mutants = micro_mutator.generate_mutants_for_code(content, target)

    sanitized_samples = []
    for m in mutants[:5]:
        sanitized_samples.append({
            "id": m.get("id"),
            "file": m.get("file"),
            "line": m.get("line"),
            "operator": m.get("description", "mutation"),
            "original_snippet": m.get("original_snippet", ""),
            "mutated_snippet": m.get("mutated_snippet", ""),
            "status": m.get("status", "PENDING")
        })
    return json.dumps({"total_mutants": len(mutants), "sample_mutants": sanitized_samples}, indent=2)


def _handle_plan_healing_pr(arguments: Dict[str, Any]) -> str:
    page_file = _validate_safe_path(arguments["page_file"])
    conf = heal_pr_automator.calculate_healing_confidence(
        arguments.get("aom_score", 0.95),
        arguments.get("spatial_score", 0.90),
        arguments.get("visual_score", 0.92)
    )
    pr = heal_pr_automator.generate_pr_draft(page_file, arguments["old_locator"], arguments["new_locator"], conf)
    return json.dumps({"confidence": conf, "pr": pr}, indent=2)


def _handle_shard_test_matrix(arguments: Dict[str, Any]) -> str:
    target = _validate_safe_path(arguments.get("target_dir") or os.getcwd())
    num_shards = arguments.get("num_shards", 4)
    files = matrix_sharder.find_test_files(target)
    shards = matrix_sharder.shard_tests_lpt(files, target, num_shards)
    return json.dumps({"total_tests": len(files), "shards": shards}, indent=2)


def _handle_pull_alm_story(arguments: Dict[str, Any]) -> str:
    bridge = tms_sync_bridge.TMSBridge()
    story = bridge.pull_story_acceptance_criteria(arguments["issue_key"])
    return json.dumps(story, indent=2)


def _handle_report_alm_defect(arguments: Dict[str, Any]) -> str:
    bridge = tms_sync_bridge.TMSBridge()
    raw_screenshot = arguments.get("screenshot_path", "")
    safe_screenshot = _validate_safe_path(raw_screenshot) if raw_screenshot else ""
    ticket = bridge.report_defect(
        project_key=arguments["project_key"],
        test_case_id=arguments["test_case_id"],
        summary=arguments["summary"],
        error_message=arguments["error_message"],
        stack_trace=arguments.get("stack_trace", ""),
        screenshot_path=safe_screenshot
    )
    return json.dumps(ticket, indent=2)


def _handle_manage_db_sandbox(arguments: Dict[str, Any]) -> str:
    action = arguments["action"]
    raw_db = arguments.get("db_path", "")
    safe_db = _validate_safe_path(raw_db) if raw_db else ""
    raw_id = arguments.get("snapshot_id", "pristine_baseline")
    safe_id = re.sub(r'[^a-zA-Z0-9_\-]', '', raw_id) or "pristine_baseline"
    consent = bool(arguments.get("consent", False)) or (os.environ.get("PENTEST_CONSENT_ACKNOWLEDGED", "").strip().lower() in ("1", "true", "yes"))

    sandbox = db_sandbox.DBSandbox(db_path=safe_db)
    if action == "snapshot":
        res = sandbox.create_snapshot(safe_id)
    elif action == "restore":
        dry_run = bool(arguments.get("dry_run", True))
        if dry_run:
            res = {
                "status": "dry_run_preview",
                "action": "restore",
                "snapshot_id": safe_id,
                "db_path": safe_db or sandbox.db_path,
                "dry_run": True,
                "impact_summary": f"DRY-RUN PREVIEW: Would restore database snapshot '{safe_id}' to '{safe_db or sandbox.db_path}'. Pass dry_run=False and consent=True to execute."
            }
        else:
            if not consent:
                raise PermissionError(
                    f"Active restore operation on database '{safe_db or sandbox.db_path}' requires explicit consent. "
                    f"Pass consent=True to confirm state modification."
                )
            from pentest_scope_guard import create_consent_grant, ConsentGrant
            grant = consent if isinstance(consent, (ConsentGrant, dict)) and not isinstance(consent, bool) else create_consent_grant(
                action="db:restore",
                target=safe_db or sandbox.db_path,
                caller_session=f"mcp_{os.getpid()}",
                db_identity=safe_db or sandbox.db_path,
                ttl_seconds=300
            )
            res = sandbox.restore_snapshot(safe_id, consent=grant, dry_run=dry_run)
    elif action == "audit_and_purge":
        dry_run = bool(arguments.get("dry_run", True))
        if not dry_run and not consent:
            raise PermissionError(
                f"Active purge operation on database '{safe_db or sandbox.db_path}' requires explicit consent. "
                f"Pass consent=True to confirm record deletion."
            )
        from pentest_scope_guard import create_consent_grant, ConsentGrant
        grant = None
        if not dry_run:
            grant = consent if isinstance(consent, (ConsentGrant, dict)) and not isinstance(consent, bool) else create_consent_grant(
                action="db:purge",
                target=safe_db or sandbox.db_path,
                caller_session=f"mcp_{os.getpid()}",
                db_identity=safe_db or sandbox.db_path,
                ttl_seconds=300
            )
        res = sandbox.audit_and_purge_pollution(dry_run=dry_run, consent=grant)
    else:
        raise ValueError(f"Unknown sandbox action: {action}")
    return json.dumps(res, indent=2)


def _handle_convert_traffic_session(arguments: Dict[str, Any]) -> str:
    input_file = _validate_safe_path(arguments["input_file"])
    test_name = arguments.get("test_name", "ProductionTrafficReplay")
    with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
        data = json.load(f)
    converter = traffic_session_converter.TrafficConverter(sanitize_pii=True)
    requests = converter.parse_har(data)
    test_code = converter.generate_playwright_test(requests, test_name=test_name)
    return json.dumps({"total_requests": len(requests), "generated_test": test_code}, indent=2)


def _handle_resolve_visual_som_coordinates(arguments: Dict[str, Any]) -> str:
    helper = visual_som_helper.VisualSoMHelper()
    raw_img = arguments.get("image_path", "screenshot.png")
    img = _validate_safe_path(raw_img)
    lbl = arguments.get("target_label")
    mid = arguments.get("mark_id")
    marked_img, marks_map = helper.generate_som_overlay(img, [])
    resolved = helper.resolve_mark_coordinates(marks_map, target_mark_id=mid, target_label=lbl)
    return json.dumps({"marked_image": marked_img, "resolved_target": resolved}, indent=2)


def _handle_compile_gherkin_suite(arguments: Dict[str, Any]) -> str:
    target = _validate_safe_path(arguments["target"])
    res = gherkin_suite.compile_feature(target) if os.path.isfile(target) else gherkin_suite.run(target)
    if isinstance(res, int):
        return json.dumps({"exit_code": res, "detail": "see reports/gherkin_suite_report.json"}, indent=2)
    persist = {k: v for k, v in res.items() if not k.startswith("_")}
    return json.dumps({
        "feature": persist.get("feature"),
        "totals": persist.get("totals"),
        "errors": persist.get("errors"),
        "gaps": persist.get("gaps"),
        "health_score_pct": persist.get("health_score_pct"),
    }, indent=2)


def _handle_fuzz_api(arguments: Dict[str, Any]) -> str:
    mode = arguments.get("mode", "passive")
    dry_run = bool(arguments.get("dry_run", True))
    consent = bool(arguments.get("consent", False)) or (os.environ.get("PENTEST_CONSENT_ACKNOWLEDGED", "").strip().lower() in ("1", "true", "yes"))
    spec_path = arguments.get("spec_path")
    base_url = arguments.get("base_url", "")

    from pentest_scope_guard import PentestScopeGuard
    guard = PentestScopeGuard(allow_internal=True)
    ok, reason = guard.validate_target(base_url, actor="mcp_server.fuzz_api")
    if not ok:
        raise PermissionError(f"[PENTEST SCOPE GUARD - REJECTED] Target base_url '{base_url}' blocked: {reason}")

    if spec_path:
        if spec_path.startswith(("http://", "https://")):
            spec_ok, spec_reason = guard.validate_target(spec_path, actor="mcp_server.fuzz_api.spec_url")
            if not spec_ok:
                raise PermissionError(f"[PENTEST SCOPE GUARD - REJECTED] spec_path URL '{spec_path}' blocked: {spec_reason}")
        else:
            spec_path = _validate_safe_path(spec_path)

    grant = None
    if mode == "active" and not dry_run:
        if not consent:
            raise PermissionError(
                "Active API fuzzing (dry_run=False) requires explicit consent. Set consent=True or run with dry_run=True / mode=passive."
            )
        from pentest_scope_guard import create_consent_grant, ConsentGrant
        grant = consent if isinstance(consent, (ConsentGrant, dict)) and not isinstance(consent, bool) else create_consent_grant(
            action="http:fuzz",
            target=base_url,
            caller_session=f"mcp_{os.getpid()}",
            ttl_seconds=300
        )

    fuzzer = api_fuzzer.ApiFuzzer(
        base_url=base_url,
        spec_path_or_url=spec_path,
        scope_guard=guard,
        dry_run=dry_run,
        consent=grant
    )
    if mode == "passive":
        scorecard = fuzzer.run_passive_scan()
        return json.dumps({
            "mode": scorecard["mode"],
            "total_findings": scorecard["total_findings"],
            "severity_summary": scorecard["severity_summary"],
            "findings": scorecard["findings"],
        }, indent=2)
    scorecard = fuzzer.run_fuzz_suite(dry_run=dry_run, consent=grant)
    return json.dumps({
        "mode": scorecard["mode"],
        "total_mutations": scorecard["total_mutations"],
        "passed": scorecard["passed"],
        "failed": scorecard["failed"],
        "severity_summary": scorecard["severity_summary"],
        "dry_run": scorecard["dry_run"],
    }, indent=2)


def _handle_synapse_lint(arguments: Dict[str, Any]) -> str:
    target = _validate_safe_path(arguments.get("target_path") or os.getcwd())
    try:
        from tools.lint.ast_engine import ASTAnalyzer
        analyzer = ASTAnalyzer()
        findings = analyzer.analyze_file(target) if os.path.isfile(target) else []
        return json.dumps({
            "target": target,
            "total_findings": len(findings),
            "findings": [f.to_dict() for f in findings],
        }, indent=2, ensure_ascii=False)
    except Exception as exc:
        return f"[SYNAPSE_LINT ERROR] {exc}"


def _handle_synapse_security_scan(arguments: Dict[str, Any]) -> str:
    repo = _validate_safe_path(arguments.get("repo_path") or os.getcwd())
    strict = bool(arguments.get("strict", True))
    try:
        from tools.security.security_scanner import audit_python_dependencies, audit_npm_dependencies
        py_ok, py_findings = audit_python_dependencies(repo, strict=strict)
        npm_ok, npm_findings = audit_npm_dependencies(repo, strict=strict)
        status = "PASS" if (py_ok and npm_ok) else "FAIL"
        return json.dumps({
            "status": status,
            "python_audit": {"ok": py_ok, "findings": py_findings},
            "npm_audit": {"ok": npm_ok, "findings": npm_findings},
        }, indent=2)
    except Exception as exc:
        return f"[SECURITY_SCAN ERROR] {exc}"


def _handle_synapse_lsp_health(arguments: Dict[str, Any]) -> str:
    repo = _validate_safe_path(arguments.get("repo_path") or os.getcwd())
    try:
        from tools.mcp.qa_lsp_server import check_lsp_health
        return json.dumps(check_lsp_health(repo), indent=2, sort_keys=True)
    except Exception as exc:
        return f"[LSP_HEALTH ERROR] {exc}"


def _handle_symbol_overview(arguments: Dict[str, Any]) -> str:
    repo = _validate_safe_path(arguments.get("repo_path") or os.getcwd())
    target = _validate_safe_path(arguments["file_path"], allowed_root=repo)
    depth = int(arguments.get("depth", 2))
    from tools.context.symbol_code_editor import SymbolCodeEditor
    editor = SymbolCodeEditor(repo_root=repo)
    syms = editor.get_symbols_overview(target, depth=depth)
    return json.dumps({"status": "ok", "symbols": [s.to_dict() for s in syms]}, indent=2)


def _handle_find_symbol(arguments: Dict[str, Any]) -> str:
    repo = _validate_safe_path(arguments.get("repo_path") or os.getcwd())
    target = _validate_safe_path(arguments["file_path"], allowed_root=repo) if arguments.get("file_path") else None
    from tools.context.symbol_code_editor import SymbolCodeEditor
    editor = SymbolCodeEditor(repo_root=repo)
    syms = editor.find_symbol(
        name_path=str(arguments["name_path"]),
        file_path=target,
        include_body=bool(arguments.get("include_body", False)),
    )
    return json.dumps({"status": "ok", "symbols": [s.to_dict() for s in syms]}, indent=2)


def _handle_find_referencing_symbols(arguments: Dict[str, Any]) -> str:
    repo = _validate_safe_path(arguments.get("repo_path") or os.getcwd())
    target = _validate_safe_path(arguments["file_path"], allowed_root=repo) if arguments.get("file_path") else None
    from tools.context.symbol_code_editor import SymbolCodeEditor
    editor = SymbolCodeEditor(repo_root=repo)
    refs = editor.find_referencing_symbols(symbol_name=str(arguments["symbol_name"]), file_path=target)
    return json.dumps({"status": "ok", "references": refs}, indent=2)


def _handle_replace_symbol_body(arguments: Dict[str, Any]) -> str:
    repo = _validate_safe_path(arguments.get("repo_path") or os.getcwd())
    target = _validate_safe_path(arguments["file_path"], allowed_root=repo)
    from tools.context.symbol_code_editor import SymbolCodeEditor
    editor = SymbolCodeEditor(repo_root=repo)
    rec = editor.replace_symbol_body(target, str(arguments["name_path"]), str(arguments["new_body"]))
    return json.dumps(rec.to_dict(), indent=2)


def _handle_temporal_graph_add_episode(arguments: Dict[str, Any]) -> str:
    db_path = _validate_safe_path(arguments.get("db_path") or os.path.join(os.getcwd(), ".synapse", "temporal_context_graph.db"))
    from tools.reasoning.temporal_context_graph import TemporalContextGraph
    facts = [tuple(item) for item in (arguments.get("facts") or [])]
    with TemporalContextGraph(db_path=db_path) as graph:
        ep = graph.add_episode(
            source=str(arguments["source"]),
            content=str(arguments["content"]),
            reference_time=str(arguments["reference_time"]),
            facts=facts,
        )
    return json.dumps({"status": "ok", "episode": ep.to_dict()}, indent=2)


def _handle_temporal_graph_query(arguments: Dict[str, Any]) -> str:
    db_path = _validate_safe_path(arguments.get("db_path") or os.path.join(os.getcwd(), ".synapse", "temporal_context_graph.db"))
    from tools.reasoning.temporal_context_graph import TemporalContextGraph
    with TemporalContextGraph(db_path=db_path) as graph:
        res = graph.query_as_of(
            query=str(arguments.get("query", "")),
            as_of=arguments.get("as_of"),
            mode=arguments.get("mode", "hybrid"),
            limit=int(arguments.get("limit", 20)),
        )
    return json.dumps(res, indent=2)


def _handle_sequential_think(arguments: Dict[str, Any]) -> str:
    from tools.reasoning.sequential_thinking_engine import SequentialThinkingSession

    sess = SequentialThinkingSession(session_id=str(arguments.get("session_id") or "default"))
    step = sess.record_thought(
        thought_number=int(arguments.get("thought_number", 1)),
        total_thoughts=int(arguments.get("total_thoughts", 1)),
        content=str(arguments.get("thought", "")),
        next_thought_needed=int(arguments.get("thought_number", 1)) < int(arguments.get("total_thoughts", 1)),
        branch_id=arguments.get("branch_id"),
    )
    return json.dumps(step.to_dict(), indent=2)


def _handle_challenge_assumption(arguments: Dict[str, Any]) -> str:
    from tools.reasoning.structured_reasoning_engine import StructuredReasoningEngine

    eng = StructuredReasoningEngine()
    report = eng.challenge_claim(str(arguments.get("claim", "")))
    return json.dumps(report.to_dict(), indent=2)


def _handle_elicitation_pick(arguments: Dict[str, Any]) -> str:
    from tools.reasoning.structured_reasoning_engine import StructuredReasoningEngine

    eng = StructuredReasoningEngine()
    methods = eng.pick_elicitation_methods(
        count=int(arguments.get("count", 3)),
        direction=arguments.get("direction"),
        tier=arguments.get("tier", "core"),
        spread=bool(arguments.get("spread", True)),
    )
    return json.dumps({"count": len(methods), "methods": methods}, indent=2)


def _handle_task_graph_ready(arguments: Dict[str, Any]) -> str:
    from tools.core.task_graph_memory import TaskGraphMemory

    raw_db = str(arguments.get("db_path") or os.path.join(os.getcwd(), ".synapse", "task_graph.db"))
    safe_db = _validate_safe_path(raw_db)
    with TaskGraphMemory(db_path=safe_db) as mem:
        ready = mem.get_ready_tasks()
        return json.dumps({"ready_count": len(ready), "tasks": [t.to_dict() for t in ready]}, indent=2)


def _handle_memory_graph_query(arguments: Dict[str, Any]) -> str:
    from tools.reasoning.associative_memory import AssociativeMemory

    query = str(arguments.get("query", "")).strip()
    limit = max(1, int(arguments.get("limit", 5)))
    mem = AssociativeMemory()
    try:
        matches = mem.query_associations(query, limit=limit) if query else []
        stats = mem.get_stats()
        return json.dumps({"query": query, "matches": matches, "stats": stats}, indent=2, default=str)
    finally:
        mem.close()


def _handle_assess_idea_gate(arguments: Dict[str, Any]) -> str:
    from tools.design.super_plan_engine import assess_idea_gate

    verdict = assess_idea_gate(
        slug=str(arguments.get("slug", "")),
        criteria=dict(arguments.get("criteria") or {}),
        concept_shaped=bool(arguments.get("concept_shaped", True)),
    )
    return json.dumps(verdict.to_dict(), indent=2)


TOOL_DISPATCH_TABLE: Dict[str, Any] = {
    "synapse_lint": _handle_synapse_lint,
    "synapse_verify": _handle_verify_all_gates,
    "synapse_lsp_health": _handle_synapse_lsp_health,
    "synapse_mutate": _handle_run_micro_mutation,
    "synapse_distill_logs": _handle_distill_log,
    "synapse_security_scan": _handle_synapse_security_scan,
    "verify_all_gates": _handle_verify_all_gates,
    "analyze_project": _handle_analyze_project,
    "setup_project": _handle_setup_project,
    "auto_heal_failure": _handle_auto_heal_failure,
    "check_action_safety": _handle_check_action_safety,
    "check_contract_drift": _handle_check_contract_drift,
    "query_memory_cache": _handle_query_memory_cache,
    "distill_log": _handle_distill_log,
    "run_micro_mutation": _handle_run_micro_mutation,
    "plan_healing_pr": _handle_plan_healing_pr,
    "shard_test_matrix": _handle_shard_test_matrix,
    "pull_alm_story": _handle_pull_alm_story,
    "report_alm_defect": _handle_report_alm_defect,
    "manage_db_sandbox": _handle_manage_db_sandbox,
    "convert_traffic_session": _handle_convert_traffic_session,
    "resolve_visual_som_coordinates": _handle_resolve_visual_som_coordinates,
    "compile_gherkin_suite": _handle_compile_gherkin_suite,
    "fuzz_api": _handle_fuzz_api,
    "symbol_overview": _handle_symbol_overview,
    "find_symbol": _handle_find_symbol,
    "find_referencing_symbols": _handle_find_referencing_symbols,
    "replace_symbol_body": _handle_replace_symbol_body,
    "temporal_graph_add_episode": _handle_temporal_graph_add_episode,
    "temporal_graph_query": _handle_temporal_graph_query,
    "sequential_think": _handle_sequential_think,
    "challenge_assumption": _handle_challenge_assumption,
    "elicitation_pick": _handle_elicitation_pick,
    "task_graph_ready": _handle_task_graph_ready,
    "memory_graph_query": _handle_memory_graph_query,
    "assess_idea_gate": _handle_assess_idea_gate,
}


def handle_tool_call(name: str, arguments: Dict[str, Any]) -> str:
    """Executes the corresponding internal tool function via dispatch table."""
    handler = TOOL_DISPATCH_TABLE.get(name)
    if not handler:
        raise ValueError(f"Unknown MCP tool: {name}")
    return handler(arguments)


def process_message(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Processes an incoming JSON-RPC 2.0 message."""
    method = msg.get("method")
    msg_id = msg.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION
                }
            }
        }

    elif method in ("notifications/initialized", "initialized"):
        return None  # No response needed for notification

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": MCP_TOOLS
            }
        }

    elif method == "tools/call":
        params = msg.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        try:
            output_text = handle_tool_call(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": output_text
                        }
                    ],
                    "isError": False
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error executing {tool_name}: {type(e).__name__}: {str(e)}"
                        }
                    ],
                    "isError": True
                }
            }

    elif method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}"
        }
    }


def run_stdio_server():
    """Runs the MCP server over standard input/output."""
    try:
        setup_project.auto_sync_codex_skills_if_stale()
    except Exception as exc:
        logger.debug("Auto-sync Codex skills skipped on MCP startup: %s", exc)
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            msg = json.loads(line)
            response = process_message(msg)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except KeyboardInterrupt:
            break
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(e)}"
                }
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    if any(arg in sys.argv[1:] for arg in ("--help", "-h", "-v", "--version")):
        print("Synapse Hub Enterprise Model Context Protocol (FastMCP) JSON-RPC Stdio Server.")
        print("Usage: python tools/mcp_server.py (Accepts JSON-RPC 2.0 frames over stdin/stdout)")
        sys.exit(0)
    run_stdio_server()
