#!/usr/bin/env python3
"""
Enterprise Model Context Protocol (MCP) Standard Server
-------------------------------------------------------
Exposes centralized tools/ capabilities as standardized JSON-RPC 2.0 MCP Tools
compatible with Google Antigravity, Cursor, Claude Desktop, Windsurf, and any MCP client.
Communicates via standard JSON-RPC stdio.
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, Set

# Enforce UTF-8 stdio encoding
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
        sys.stdin.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HUB_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, SCRIPT_DIR)

import verify_all
import analyze_project
import setup_project
import auto_heal
import safety_firewall
import api_drift_sentinel
import cache_resolver
import distill_log
import micro_mutator
import heal_pr_automator
import matrix_sharder
import tms_sync_bridge
import db_sandbox
import traffic_session_converter
import visual_som_helper
import gherkin_suite
import api_fuzzer

SERVER_NAME = "enterprise-agent-qa"
SERVER_VERSION = "3.0.0"

MCP_TOOLS = [
    {
        "name": "verify_all_gates",
        "description": "Validates the 9 Quality Gates Definition of Done (author attribution, UTF-8, paths, Clean POM, AI docs, blacklist, security, infer linter, micro-mutator).",
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
        "description": "Filters verbose CLI or Gradle build logs by 95%, retaining only actionable stacktraces and pointers.",
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
                "dry_run": {"type": "boolean", "description": "For audit_and_purge: preview records to purge without deleting."}
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
                "mode": {"type": "string", "enum": ["active", "passive"], "description": "active fuzzing or passive offline spec audit."},
                "dry_run": {"type": "boolean", "description": "Deterministic offline mock (default true for safety)."}
            },
            "required": ["base_url"]
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

    effective_root = allowed_root or os.environ.get("SYNAPSE_PROJECT_ROOT") or os.getcwd()
    try:
        root_path = Path(effective_root).resolve()
        target_path = Path(filepath).resolve()
    except Exception as e:
        raise PermissionError(f"Access denied: cannot resolve path '{filepath}': {e}")

    # Case-insensitive path comparison across OS filesystems
    root_norm = os.path.normcase(str(root_path))
    target_norm = os.path.normcase(str(target_path))

    # Path must reside within the allowed root
    if target_norm != root_norm and not target_norm.startswith(root_norm + os.sep):
        raise PermissionError(f"Access denied: path '{filepath}' resolves outside allowed project root '{root_path}'")

    # Reject explicit sensitive configuration / secret files
    base_name = target_path.name.lower()
    if base_name in {".env", ".env.local", ".env.production", ".env.staging", ".npmrc", ".netrc", ".git-credentials"}:
        raise PermissionError(f"Access denied: path references sensitive configuration file '{target_path.name}'")

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

    for sp in sensitive_prefixes:
        sp_norm = os.path.normcase(str(sp))
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
    passed = True
    gates = [
        ("Gate 0: Author Integrity", verify_all.gate_0_author_integrity),
        ("Gate 1: UTF-8 No BOM", verify_all.gate_1_bom_check),
        ("Gate 2: Path Portability", verify_all.gate_2_path_portability),
        ("Gate 3: Clean POM", verify_all.gate_3_clean_pom),
        ("Gate 4: AI Docs Linter", verify_all.gate_4_ai_docs_lint),
        ("Gate 5: Temp Blacklist", verify_all.gate_5_cleanup_blacklist),
        ("Gate 6: Credential Security", verify_all.gate_6_credential_security),
        ("Gate 7: Infer Linter", verify_all.gate_7_infer_linter),
        ("Gate 8: AST Mutation Sentinel", verify_all.gate_8_micro_mutator),
    ]
    results = []
    for g_name, g_fn in gates:
        res = g_fn(repo, mode=mode)
        results.append(f"{g_name}: {'PASS' if res else 'FAIL'}")
        if not res:
            passed = False
    summary = "100% ALL 9 GATES PASSED" if passed else "VERIFICATION FAILED"
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

    sandbox = db_sandbox.DBSandbox(db_path=safe_db)
    if action == "snapshot":
        res = sandbox.create_snapshot(safe_id)
    elif action == "restore":
        res = sandbox.restore_snapshot(safe_id)
    elif action == "audit_and_purge":
        dry_run = bool(arguments.get("dry_run", False))
        res = sandbox.audit_and_purge_pollution(dry_run=dry_run)
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
    mode = arguments.get("mode", "active")
    dry_run = arguments.get("dry_run", True)
    spec_path = arguments.get("spec_path")
    if spec_path and not (spec_path.startswith("http://") or spec_path.startswith("https://")):
        spec_path = _validate_safe_path(spec_path)
    fuzzer = api_fuzzer.ApiFuzzer(
        base_url=arguments["base_url"],
        spec_path_or_url=spec_path,
    )
    if mode == "passive":
        scorecard = fuzzer.run_passive_scan()
        return json.dumps({
            "mode": scorecard["mode"],
            "total_findings": scorecard["total_findings"],
            "severity_summary": scorecard["severity_summary"],
            "findings": scorecard["findings"],
        }, indent=2)
    scorecard = fuzzer.run_fuzz_suite(dry_run=dry_run)
    return json.dumps({
        "mode": scorecard["mode"],
        "total_mutations": scorecard["total_mutations"],
        "passed": scorecard["passed"],
        "failed": scorecard["failed"],
        "severity_summary": scorecard["severity_summary"],
    }, indent=2)


TOOL_DISPATCH_TABLE: Dict[str, Any] = {
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
    run_stdio_server()
