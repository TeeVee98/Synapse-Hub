#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Master Opaque-Box E2E Test Suite for Synapse-Hub Reference Enhancements.
-----------------------------------------------------------------------
Verifies interface contracts and behaviors across all 4 tiers:
  Tier 1: Core Feature Coverage (Happy Path CLI & Interface Contracts)
  Tier 2: Boundary, Adversarial & Error Conditions
  Tier 3: Cross-Feature Contract Interactions
  Tier 4: Real-World Autonomous Agent Workloads

Adheres strictly to:
  - 100% UTF-8 No BOM
  - Zero Fake Passes (real assertions, no swallowed exceptions)
  - Dynamic & Idempotent isolation (tmp_path sandboxes, unique run tokens)
  - Progressive testability (milestone-aware dependency resolution)
"""

import os
import sys
import json
import time
import uuid
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

import pytest

# Repository root discovery
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Test Helpers & Fixtures
# ---------------------------------------------------------------------------

def require_tool(rel_path: str) -> Path:
    """
    Validates that a tool script exists in the repository.
    If absent, marks the test as SKIPPED to support progressive milestone delivery.
    """
    tool_path = REPO_ROOT / rel_path
    if not tool_path.exists():
        pytest.skip(f"Tool '{rel_path}' is not yet implemented (scheduled for milestone delivery)")
    return tool_path


def run_cli(
    cmd: List[str],
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: float = 30.0
) -> subprocess.CompletedProcess:
    """Executes a subprocess CLI command with explicit timeout and environment propagation."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=full_env,
        timeout=timeout
    )


def unique_code(prefix: str = "E2E_") -> str:
    """Generates an idempotent dynamic unique test token with timestamp."""
    return f"{prefix}{int(time.time())}_{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# TIER 1: Core Feature Coverage (Happy Path Contracts)
# ---------------------------------------------------------------------------

def test_tier1_agent_runner_success(tmp_path):
    """
    T1.1: agent_runner executes a successful command with context shielding.
    Asserts exit code 0, status 'PASSED', valid log generation, concise summary (<60 tokens),
    and empty failure excerpt.
    """
    tool = require_tool("tools/core/agent_runner.py")
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    marker_text = f"RUNNER_SUCCESS_{unique_code()}"
    cmd = [
        sys.executable, str(tool),
        "--log-dir", str(log_dir),
        "--json",
        sys.executable, "-c", f"print('{marker_text}')"
    ]
    res = run_cli(cmd)
    assert res.returncode == 0, f"agent_runner failed: {res.stderr}\n{res.stdout}"

    data = json.loads(res.stdout.strip())
    assert data["status"] == "PASSED"
    assert data["exit_code"] == 0
    assert data["duration_sec"] >= 0.0
    assert "log_path" in data and os.path.isfile(data["log_path"])
    assert data["failure_excerpt"] == []

    # Verify log content on disk
    with open(data["log_path"], "r", encoding="utf-8") as f:
        log_content = f.read()
    assert marker_text in log_content

    # Verify context shield summary constraint (< 60 words/tokens)
    summary_words = data["summary"].split()
    assert len(summary_words) < 60, f"Summary exceeds 60 tokens: {len(summary_words)} words"


def test_tier1_ratchet_sentinel_pass(tmp_path):
    """
    T1.2: ratchet_sentinel passes when current findings match baseline defects.
    Asserts exit code 0, status 'PASS', delta 0, and ratcheted False.
    """
    tool = require_tool("tools/lint/ratchet_sentinel.py")

    baseline_file = tmp_path / "baseline.json"
    findings_file = tmp_path / "findings.json"

    payload = {"total": 3, "defects": [{"id": "D1"}, {"id": "D2"}, {"id": "D3"}]}
    baseline_file.write_text(json.dumps(payload), encoding="utf-8")
    findings_file.write_text(json.dumps(payload), encoding="utf-8")

    cmd = [
        sys.executable, str(tool),
        "--findings", str(findings_file),
        "--baseline", str(baseline_file),
        "--metric", "defects",
        "--json"
    ]
    res = run_cli(cmd)
    assert res.returncode == 0, f"ratchet_sentinel failed: {res.stderr}\n{res.stdout}"

    data = json.loads(res.stdout.strip())
    assert data["status"] == "PASS"
    assert data["baseline_total"] == 3
    assert data["current_total"] == 3
    assert data["delta"] == 0
    assert data["ratcheted"] is False


def test_tier1_cli_schema_sentinel_check():
    """
    T1.3: cli_schema_sentinel executes schema parity check without errors.
    Asserts valid JSON output containing status, tools_checked, and drifts list.
    """
    tool = require_tool("tools/lint/cli_schema_sentinel.py")

    cmd = [sys.executable, str(tool), "--check", "--json"]
    res = run_cli(cmd)
    assert res.returncode in (0, 1), f"Unexpected crash in cli_schema_sentinel: {res.stderr}"

    data = json.loads(res.stdout.strip())
    assert data["status"] in ("PASS", "DRIFT_DETECTED")
    assert "tools_checked" in data and data["tools_checked"] >= 1
    assert "drift_count" in data and isinstance(data["drift_count"], int)
    assert "drifts" in data and isinstance(data["drifts"], list)


def test_tier1_debug_crumbs_clean_and_detect(tmp_path):
    """
    T1.4: debug_crumbs returns 'CLEAN' on clean workspace, detects crumbs when added.
    Asserts status transitions: CLEAN (exit 0) -> CRUMBS_DETECTED (exit 1).
    """
    tool = require_tool("tools/core/debug_crumbs.py")

    src_file = tmp_path / "service.py"
    src_file.write_text("def compute():\n    return 42\n", encoding="utf-8")

    # Step A: Clean check
    cmd_clean = [sys.executable, str(tool), "--dir", str(tmp_path), "--check", "--json"]
    res_clean = run_cli(cmd_clean)
    assert res_clean.returncode == 0, f"Expected clean check to exit 0: {res_clean.stderr}"
    data_clean = json.loads(res_clean.stdout.strip())
    assert data_clean["status"] == "CLEAN"
    assert data_clean["crumbs_count"] == 0

    # Step B: Inject ephemeral crumb
    crumb_token = unique_code("@crumbs")
    src_file.write_text(f"def compute():\n    print('debug')  # {crumb_token}\n    return 42\n", encoding="utf-8")

    cmd_detect = [sys.executable, str(tool), "--dir", str(tmp_path), "--check", "--json"]
    res_detect = run_cli(cmd_detect)
    assert res_detect.returncode != 0, "Expected non-zero exit code when crumbs are detected"
    data_detect = json.loads(res_detect.stdout.strip())
    assert data_detect["status"] == "CRUMBS_DETECTED"
    assert data_detect["crumbs_count"] >= 1
    assert len(data_detect["locations"]) >= 1


def test_tier1_debug_crumbs_strip(tmp_path):
    """
    T1.5: debug_crumbs --strip cleanly removes instrumentation markers and retains UTF-8 No BOM.
    Asserts status 'CRUMBS_STRIPPED', marker removed on disk, and zero BOM bytes.
    """
    tool = require_tool("tools/core/debug_crumbs.py")

    code_file = tmp_path / "worker.py"
    code_file.write_text(
        "def work():\n"
        "    x = 10\n"
        "    print('debug x:', x)  # @crumbs\n"
        "    return x * 2\n",
        encoding="utf-8"
    )

    cmd_strip = [sys.executable, str(tool), "--dir", str(tmp_path), "--strip", "--json"]
    res_strip = run_cli(cmd_strip)
    assert res_strip.returncode == 0, f"Strip failed: {res_strip.stderr}\n{res_strip.stdout}"

    data = json.loads(res_strip.stdout.strip())
    assert data["status"] == "CRUMBS_STRIPPED"
    assert data["crumbs_count"] >= 1

    # Verify file content on disk has no crumb marker
    content = code_file.read_text(encoding="utf-8")
    assert "@crumbs" not in content
    assert "return x * 2" in content

    # Verify UTF-8 No BOM invariant
    raw_bytes = code_file.read_bytes()
    assert not raw_bytes.startswith(b"\xef\xbb\xbf"), "BOM detected in stripped file!"


def test_tier1_invariant_checker_rule():
    """
    T1.6: invariant_checker deterministically evaluates AGENTS.md invariants.
    Asserts valid JSON output and rules_checked count.
    """
    tool = require_tool("tools/lint/invariant_checker.py")

    cmd = [sys.executable, str(tool), "--rule", "1", "--json"]
    res = run_cli(cmd)
    assert res.returncode in (0, 1), f"Unexpected crash in invariant_checker: {res.stderr}"

    data = json.loads(res.stdout.strip())
    assert data["status"] in ("PASS", "VIOLATIONS_DETECTED")
    assert "rules_checked" in data and data["rules_checked"] >= 1
    assert "violations" in data and isinstance(data["violations"], list)


def test_tier1_fsm_enforcer_lane_transitions(tmp_path):
    """
    T1.7: fsm_enforcer initializes a session and advances with cryptographic proof tokens.
    Asserts stage advance returns status 'PASS' and valid proof_v2 token.
    """
    tool = require_tool("tools/core/fsm_enforcer.py")
    from tools.core.fsm_enforcer import FsmEnforcer

    state_file = tmp_path / "fsm_session.json"
    enforcer = FsmEnforcer(state_file=str(state_file))

    session_id = unique_code("SESS_")
    start_res = enforcer.start_session(session_id=session_id)
    assert start_res["status"] == "PASS"
    assert start_res["session_id"] == session_id

    # Advance DISCOVERY
    evidence = {
        "target_url": "https://example.com/login",
        "selectors": ["#username", "#password", "#submit"]
    }
    adv_res = enforcer.advance_stage(stage="DISCOVERY", actor="live-explorer", evidence=evidence)
    assert adv_res["status"] == "PASS"
    assert adv_res["proof_token"].startswith("proof_v2_discovery_")
    assert adv_res["next_required_stage"] == "CODE_SYNTHESIS"


# ---------------------------------------------------------------------------
# TIER 2: Boundary, Adversarial & Error Conditions
# ---------------------------------------------------------------------------

def test_tier2_agent_runner_timeout(tmp_path):
    """
    T2.1: agent_runner aborts and terminates process when execution exceeds --timeout.
    Asserts status 'TIMEOUT', non-zero exit code, and bounded duration.
    """
    tool = require_tool("tools/core/agent_runner.py")
    log_dir = tmp_path / "timeout_logs"

    cmd = [
        sys.executable, str(tool),
        "--timeout", "1",
        "--log-dir", str(log_dir),
        "--json",
        sys.executable, "-c", "import time; time.sleep(10)  # synapse-ignore: STATIC_SLEEP"
    ]
    start_t = time.time()
    res = run_cli(cmd, timeout=15)
    elapsed = time.time() - start_t

    assert res.returncode != 0
    data = json.loads(res.stdout.strip())
    assert data["status"] == "TIMEOUT"
    assert elapsed < 8.0, f"Process took {elapsed}s, did not terminate on timeout!"


def test_tier2_agent_runner_watch_mode_blocked(tmp_path):
    """
    T2.2: agent_runner blocks watch-mode and interactive flags by default.
    Asserts immediate rejection without execution unless --allow-watch is passed.
    """
    tool = require_tool("tools/core/agent_runner.py")

    watch_cmd = [
        sys.executable, str(tool),
        "--json",
        "pytest", "-f", "tests/"
    ]
    res_blocked = run_cli(watch_cmd)
    assert res_blocked.returncode != 0
    data_blocked = json.loads(res_blocked.stdout.strip())
    assert data_blocked["status"] in ("FAILED", "BLOCKED")
    assert "watch" in data_blocked.get("summary", "").lower() or "watch" in str(data_blocked).lower()


def test_tier2_agent_runner_failure_excerpt(tmp_path):
    """
    T2.3: agent_runner strictly bounds failure excerpts to max lines to shield context.
    Asserts failure_excerpt length <= max_excerpt (default 20, or specified N).
    """
    tool = require_tool("tools/core/agent_runner.py")
    log_dir = tmp_path / "failure_logs"

    max_n = 7
    fail_script = (
        "import sys\n"
        "for i in range(50):\n"
        "    print(f'ERROR_TRACE_LINE_{i}')\n"
        "sys.exit(2)\n"
    )
    cmd = [
        sys.executable, str(tool),
        "--max-excerpt", str(max_n),
        "--log-dir", str(log_dir),
        "--json",
        sys.executable, "-c", fail_script
    ]
    res = run_cli(cmd)
    assert res.returncode != 0

    data = json.loads(res.stdout.strip())
    assert data["status"] == "FAILED"
    assert data["exit_code"] == 2
    assert len(data["failure_excerpt"]) <= max_n
    # Assert excerpt captures tail of logs
    assert any("ERROR_TRACE_LINE_49" in line for line in data["failure_excerpt"])


def test_tier2_ratchet_sentinel_regression(tmp_path):
    """
    T2.4: ratchet_sentinel detects defect regression (current > baseline) and fails.
    Asserts non-zero exit code, status 'FAIL_REGRESSION', and positive delta.
    """
    tool = require_tool("tools/lint/ratchet_sentinel.py")

    baseline_file = tmp_path / "baseline.json"
    findings_file = tmp_path / "findings.json"

    baseline_file.write_text(json.dumps({"total": 2, "defects": [{"id": "D1"}, {"id": "D2"}]}), encoding="utf-8")
    findings_file.write_text(json.dumps({"total": 5, "defects": [{"id": f"D{i}"} for i in range(1, 6)]}), encoding="utf-8")

    cmd = [
        sys.executable, str(tool),
        "--findings", str(findings_file),
        "--baseline", str(baseline_file),
        "--metric", "defects",
        "--json"
    ]
    res = run_cli(cmd)
    assert res.returncode != 0, "Expected non-zero exit on defect regression"

    data = json.loads(res.stdout.strip())
    assert data["status"] == "FAIL_REGRESSION"
    assert data["delta"] == 3
    assert data["ratcheted"] is False


def test_tier2_ratchet_sentinel_stale_baseline_without_update(tmp_path):
    """
    T2.5: ratchet_sentinel enforces two-sided ratchet: fails on stale baseline if code improved without --update.
    Asserts non-zero exit code, status 'FAIL_STALE_BASELINE', and negative delta.
    """
    tool = require_tool("tools/lint/ratchet_sentinel.py")

    baseline_file = tmp_path / "baseline.json"
    findings_file = tmp_path / "findings.json"

    baseline_file.write_text(json.dumps({"total": 5, "defects": [{"id": f"D{i}"} for i in range(5)]}), encoding="utf-8")
    findings_file.write_text(json.dumps({"total": 2, "defects": [{"id": "D0"}, {"id": "D1"}]}), encoding="utf-8")

    cmd = [
        sys.executable, str(tool),
        "--findings", str(findings_file),
        "--baseline", str(baseline_file),
        "--metric", "defects",
        "--json"
    ]
    res = run_cli(cmd)
    assert res.returncode != 0, "Expected non-zero exit when baseline is stale and --update is missing"

    data = json.loads(res.stdout.strip())
    assert data["status"] == "FAIL_STALE_BASELINE"
    assert data["delta"] == -3
    assert data["ratcheted"] is False

    # Baseline on disk must NOT have been silently updated
    b_data = json.loads(baseline_file.read_text(encoding="utf-8"))
    assert b_data["total"] == 5


def test_tier2_ratchet_sentinel_update_locks_new_baseline(tmp_path):
    """
    T2.6: ratchet_sentinel --update locks in new lower defect count into baseline.
    Asserts exit code 0, status 'PASS', ratcheted True, and baseline file updated on disk.
    """
    tool = require_tool("tools/lint/ratchet_sentinel.py")

    baseline_file = tmp_path / "baseline.json"
    findings_file = tmp_path / "findings.json"

    baseline_file.write_text(json.dumps({"total": 6, "defects": [{"id": f"D{i}"} for i in range(6)]}), encoding="utf-8")
    findings_file.write_text(json.dumps({"total": 3, "defects": [{"id": f"D{i}"} for i in range(3)]}), encoding="utf-8")

    cmd = [
        sys.executable, str(tool),
        "--findings", str(findings_file),
        "--baseline", str(baseline_file),
        "--metric", "defects",
        "--update",
        "--json"
    ]
    res = run_cli(cmd)
    assert res.returncode == 0, f"Expected success with --update: {res.stderr}\n{res.stdout}"

    data = json.loads(res.stdout.strip())
    assert data["status"] == "PASS"
    assert data["ratcheted"] is True

    # Baseline file on disk must now reflect the new lower total (3)
    updated_baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
    assert updated_baseline["total"] == 3


def test_tier2_cli_schema_drift_detection(tmp_path):
    """
    T2.7: cli_schema_sentinel detects argument drift between CLI AST and declared schema.
    Asserts status 'DRIFT_DETECTED' and drift details populated.
    """
    tool = require_tool("tools/lint/cli_schema_sentinel.py")

    mock_tool = tmp_path / "mock_cli.py"
    mock_tool.write_text(
        "import argparse\n"
        "parser = argparse.ArgumentParser()\n"
        "parser.add_argument('--known-arg', help='Known')\n"
        "parser.add_argument('--new-rogue-flag', action='store_true', help='Undocumented')\n"
        "args = parser.parse_args()\n",
        encoding="utf-8"
    )

    mock_schema = tmp_path / "schema.json"
    mock_schema.write_text(
        json.dumps({
            "tools": {
                "mock_cli": {
                    "path": str(mock_tool),
                    "args": ["--known-arg"]
                }
            }
        }),
        encoding="utf-8"
    )

    cmd = [
        sys.executable, str(tool),
        "--schema", str(mock_schema),
        "--tools-dir", str(tmp_path),
        "--tool", "mock_cli",
        "--check",
        "--json"
    ]
    res = run_cli(cmd)
    data = json.loads(res.stdout.strip())
    assert data["status"] == "DRIFT_DETECTED"
    assert data["drift_count"] >= 1


def test_tier2_debug_crumbs_multi_syntax(tmp_path):
    """
    T2.8: debug_crumbs detects crumbs across multiple language comment syntaxes (#, //, /* */).
    Asserts scanner detects crumbs in Python, TypeScript, Groovy, and shell scripts.
    """
    tool = require_tool("tools/core/debug_crumbs.py")

    (tmp_path / "script.py").write_text("x = 1 # @crumbs python\n", encoding="utf-8")
    (tmp_path / "service.ts").write_text("const y = 2; // @crumbs typescript\n", encoding="utf-8")
    (tmp_path / "build.groovy").write_text("/* @crumbs groovy block */\ndef x = 3\n", encoding="utf-8")
    (tmp_path / "deploy.sh").write_text("#!/bin/bash\necho 1 # @crumbs bash\n", encoding="utf-8")

    cmd = [sys.executable, str(tool), "--dir", str(tmp_path), "--check", "--json"]
    res = run_cli(cmd)
    assert res.returncode != 0

    data = json.loads(res.stdout.strip())
    assert data["status"] == "CRUMBS_DETECTED"
    assert data["crumbs_count"] >= 4


def test_tier2_fsm_enforcer_experiment_lane_blocks_dod(tmp_path):
    """
    T2.9: fsm_enforcer in experiment lane is strictly blocked from ACCEPTANCE_DOD signoff.
    Asserts advance or verify-compliance rejects closing DoD when in experiment lane.
    """
    tool = require_tool("tools/core/fsm_enforcer.py")
    # Verify if --lane is supported in CLI / implementation
    check_lane = run_cli([sys.executable, str(tool), "start", "--help"])
    if "--lane" not in check_lane.stdout:
        pytest.skip("fsm_enforcer --lane extension not yet implemented (scheduled for M3)")

    state_file = tmp_path / "fsm_experiment.json"
    start_cmd = [
        sys.executable, str(tool),
        "start",
        "--session-id", unique_code("EXP_"),
        "--lane", "experiment"
    ]
    run_cli(start_cmd, env={"FSM_STATE_FILE": str(state_file)})

    # Advance directly or attempt ACCEPTANCE_DOD
    dod_cmd = [
        sys.executable, str(tool),
        "advance",
        "--stage", "ACCEPTANCE_DOD",
        "--actor", "quality-gatekeeper",
        "--evidence", '{"gates_passed": 10}'
    ]
    res_dod = run_cli(dod_cmd, env={"FSM_STATE_FILE": str(state_file)})
    assert res_dod.returncode != 0
    data = json.loads(res_dod.stdout.strip())
    assert data["status"] == "REJECTED"
    assert "experiment" in data.get("error", "").lower()


def test_tier2_fsm_enforcer_tampered_proof_token(tmp_path):
    """
    T2.10: fsm_enforcer detects tampering with session evidence payload on disk.
    Asserts verify_compliance rejects tampered proof token with status 'BLOCKED'.
    """
    require_tool("tools/core/fsm_enforcer.py")
    from tools.core.fsm_enforcer import FsmEnforcer

    state_file = tmp_path / "tampered_session.json"
    enforcer = FsmEnforcer(state_file=str(state_file))

    session_id = unique_code("SESS_TAMPER_")
    enforcer.start_session(session_id=session_id)

    # Legitimate advance through all 5 stages
    enforcer.advance_stage("DISCOVERY", "live-explorer", {"target_url": "https://synapse.dev", "selectors": [".button"]})
    enforcer.advance_stage("CODE_SYNTHESIS", "pom-crafter", {"files": ["tests/e2e/test_reference_enhancements_e2e.py"]})
    enforcer.advance_stage("HEADLESS_EXEC", "test-runner", {"exit_code": 0})
    enforcer.advance_stage("AUTOPSY_HEAL", "failure-analyst", {"status": "PASSED"})
    enforcer.advance_stage("ACCEPTANCE_DOD", "quality-gatekeeper", {"gates_passed": 10})

    # Tamper with recorded evidence on disk directly
    raw_state = json.loads(state_file.read_text(encoding="utf-8"))
    raw_state["completed_stages"]["DISCOVERY"]["evidence"]["target_url"] = "https://forged.dev"
    state_file.write_text(json.dumps(raw_state), encoding="utf-8")

    # Re-instantiate and verify
    tampered_enforcer = FsmEnforcer(state_file=str(state_file))
    check = tampered_enforcer.verify_compliance()
    assert check["status"] == "BLOCKED"
    assert "DISCOVERY" in check.get("tampered_stages", [])


# ---------------------------------------------------------------------------
# TIER 3: Cross-Feature Contract Interactions
# ---------------------------------------------------------------------------

def test_tier3_agent_runner_executes_ratchet_sentinel(tmp_path):
    """
    T3.1: agent_runner wraps and executes ratchet_sentinel in a shielded process.
    Asserts runner captures ratchet sentinel JSON output in log file and returns exit code 0.
    """
    runner_tool = require_tool("tools/core/agent_runner.py")
    ratchet_tool = require_tool("tools/lint/ratchet_sentinel.py")

    baseline_file = tmp_path / "base.json"
    findings_file = tmp_path / "find.json"
    payload = {"total": 1, "defects": [{"id": "D1"}]}
    baseline_file.write_text(json.dumps(payload), encoding="utf-8")
    findings_file.write_text(json.dumps(payload), encoding="utf-8")

    log_dir = tmp_path / "runner_logs"
    cmd = [
        sys.executable, str(runner_tool),
        "--log-dir", str(log_dir),
        "--json",
        sys.executable, str(ratchet_tool),
        "--findings", str(findings_file),
        "--baseline", str(baseline_file),
        "--metric", "defects",
        "--json"
    ]
    res = run_cli(cmd)
    assert res.returncode == 0

    data = json.loads(res.stdout.strip())
    assert data["status"] == "PASSED"
    assert data["exit_code"] == 0

    # Verify redirected log contains ratchet output
    with open(data["log_path"], "r", encoding="utf-8") as f:
        inner_log = f.read()
    inner_data = json.loads(inner_log.strip())
    assert inner_data["status"] == "PASS"
    assert inner_data["delta"] == 0


def test_tier3_agent_runner_executes_debug_crumbs_strip(tmp_path):
    """
    T3.2: agent_runner wraps debug_crumbs --strip to sanitize files through harness.
    Asserts crumbs are stripped on disk and runner log contains sanitization evidence.
    """
    runner_tool = require_tool("tools/core/agent_runner.py")
    crumbs_tool = require_tool("tools/core/debug_crumbs.py")

    target_file = tmp_path / "instrumented.py"
    target_file.write_text("x = 100\nprint(x) # @crumbs trace\n", encoding="utf-8")

    log_dir = tmp_path / "crumbs_runner_logs"
    cmd = [
        sys.executable, str(runner_tool),
        "--log-dir", str(log_dir),
        "--json",
        sys.executable, str(crumbs_tool),
        "--dir", str(tmp_path),
        "--strip",
        "--json"
    ]
    res = run_cli(cmd)
    assert res.returncode == 0

    # Assert crumbs stripped on disk
    assert "@crumbs" not in target_file.read_text(encoding="utf-8")

    # Assert runner captured crumbs JSON in log
    runner_data = json.loads(res.stdout.strip())
    with open(runner_data["log_path"], "r", encoding="utf-8") as f:
        crumbs_log = json.loads(f.read().strip())
    assert crumbs_log["status"] == "CRUMBS_STRIPPED"


def test_tier3_cli_schema_sentinel_validates_new_tools():
    """
    T3.3: cli_schema_sentinel validates AST argument extraction on new repository tools.
    Asserts schema validator parses tool files without unhandled exceptions.
    """
    schema_tool = require_tool("tools/lint/cli_schema_sentinel.py")

    cmd = [sys.executable, str(schema_tool), "--check", "--json"]
    res = run_cli(cmd)
    assert res.returncode in (0, 1)
    data = json.loads(res.stdout.strip())
    assert "tools_checked" in data
    assert data["tools_checked"] >= 1


def test_tier3_fsm_enforcer_records_artifact_hashes_from_runner(tmp_path):
    """
    T3.4: fsm_enforcer records SHA-256 digests for artifacts generated during execution.
    Asserts artifact tampering on disk causes verify_compliance to fail.
    """
    require_tool("tools/core/fsm_enforcer.py")
    from tools.core.fsm_enforcer import FsmEnforcer

    state_file = tmp_path / "artifact_session.json"
    artifact_file = tmp_path / "LoginPage.ts"
    artifact_file.write_text("export class LoginPage { path = '/login'; }", encoding="utf-8")

    enforcer = FsmEnforcer(state_file=str(state_file))
    enforcer.start_session(session_id=unique_code("SESS_ART_"))

    # Stage 1: DISCOVERY
    enforcer.advance_stage("DISCOVERY", "live-explorer", {"target_url": "https://test.dev"})

    # Stage 2: CODE_SYNTHESIS referencing physical artifact
    res_code = enforcer.advance_stage(
        "CODE_SYNTHESIS",
        "pom-crafter",
        {"files": [str(artifact_file)]}
    )
    assert res_code["status"] == "PASS"

    # Advance remaining stages to complete workflow
    enforcer.advance_stage("HEADLESS_EXEC", "test-runner", {"exit_code": 0})
    enforcer.advance_stage("AUTOPSY_HEAL", "failure-analyst", {"status": "PASSED"})
    enforcer.advance_stage("ACCEPTANCE_DOD", "quality-gatekeeper", {"gates_passed": 10})

    # Verify initial compliance is PASS
    clean_check = enforcer.verify_compliance()
    assert clean_check["status"] == "PASS"
    assert clean_check["compliant"] is True

    # Tamper with the artifact on disk
    artifact_file.write_text("export class LoginPage { path = '/hacked'; }", encoding="utf-8")

    # Verification must flag the discrepancy
    check = enforcer.verify_compliance()
    assert check["status"] == "BLOCKED"
    assert any("tampered" in v.lower() for v in check.get("artifact_violations", []))


# ---------------------------------------------------------------------------
# TIER 4: Real-World Autonomous Agent Workloads
# ---------------------------------------------------------------------------

def test_tier4_full_agent_workflow_simulation(tmp_path):
    """
    T4.1: Comprehensive simulated multi-agent enterprise workflow:
      1. Initialize FSM session.
      2. Discovery phase with element specifications.
      3. Code synthesis with temporary # @crumbs instrumentation.
      4. Headless execution under agent_runner with context shielding.
      5. Pre-commit check fails via debug_crumbs --check.
      6. Code sanitized via debug_crumbs --strip.
      7. Ratchet sentinel enforces zero defect regressions with --update.
      8. FSM completion and cryptographic verification pass.
    """
    fsm_tool = require_tool("tools/core/fsm_enforcer.py")
    runner_tool = require_tool("tools/core/agent_runner.py")
    crumbs_tool = require_tool("tools/core/debug_crumbs.py")
    ratchet_tool = require_tool("tools/lint/ratchet_sentinel.py")
    from tools.core.fsm_enforcer import FsmEnforcer

    state_file = tmp_path / "e2e_fsm_session.json"
    enforcer = FsmEnforcer(state_file=str(state_file))

    # 1. Start FSM Session
    session_id = unique_code("WF_E2E_")
    enforcer.start_session(session_id=session_id)

    # 2. Stage 1: DISCOVERY
    adv_disc = enforcer.advance_stage(
        stage="DISCOVERY",
        actor="live-explorer",
        evidence={"target_url": "https://synapse.internal", "selectors": ["#app", "#nav"]}
    )
    assert adv_disc["status"] == "PASS"

    # 3. Stage 2: CODE_SYNTHESIS (Agent writes page class with temporary debug crumb)
    page_file = tmp_path / "DashboardPage.py"
    page_file.write_text(
        "class DashboardPage:\n"
        "    def load(self):\n"
        "        print('Loading dashboard')  # @crumbs\n"
        "        return True\n",
        encoding="utf-8"
    )
    adv_synth = enforcer.advance_stage(
        stage="CODE_SYNTHESIS",
        actor="pom-crafter",
        evidence={"files": [str(page_file)]}
    )
    assert adv_synth["status"] == "PASS"

    # 4. Stage 3: HEADLESS_EXEC (Test executed through agent_runner context harness)
    log_dir = tmp_path / "exec_logs"
    runner_cmd = [
        sys.executable, str(runner_tool),
        "--log-dir", str(log_dir),
        "--json",
        sys.executable, "-c", "import sys; print('TEST_SUITE_PASS'); sys.exit(0)"
    ]
    runner_res = run_cli(runner_cmd)
    assert runner_res.returncode == 0
    adv_exec = enforcer.advance_stage(
        stage="HEADLESS_EXEC",
        actor="test-runner",
        evidence={"exit_code": 0, "log_dir": str(log_dir)}
    )
    assert adv_exec["status"] == "PASS"

    # 5. Pre-commit check catches debug crumbs
    crumb_check = run_cli([sys.executable, str(crumbs_tool), "--dir", str(tmp_path), "--check", "--json"])
    assert crumb_check.returncode != 0
    assert json.loads(crumb_check.stdout.strip())["status"] == "CRUMBS_DETECTED"

    # 6. Sanitize codebase: strip debug crumbs
    crumb_strip = run_cli([sys.executable, str(crumbs_tool), "--dir", str(tmp_path), "--strip", "--json"])
    assert crumb_strip.returncode == 0
    assert "@crumbs" not in page_file.read_text(encoding="utf-8")

    # Re-verify artifact hash update for FSM integrity
    enforcer.advance_stage(
        stage="CODE_SYNTHESIS",
        actor="pom-crafter",
        evidence={"files": [str(page_file)]}
    )

    # 7. Quality ratchet validation: ensure monotonic zero regressions
    baseline_file = tmp_path / "ratchet_base.json"
    findings_file = tmp_path / "ratchet_find.json"
    baseline_file.write_text(json.dumps({"total": 1, "defects": [{"id": "D1"}]}), encoding="utf-8")
    findings_file.write_text(json.dumps({"total": 0, "defects": []}), encoding="utf-8")

    ratchet_res = run_cli([
        sys.executable, str(ratchet_tool),
        "--findings", str(findings_file),
        "--baseline", str(baseline_file),
        "--metric", "defects",
        "--update",
        "--json"
    ])
    assert ratchet_res.returncode == 0
    assert json.loads(ratchet_res.stdout.strip())["status"] == "PASS"

    # 8. Stage 4: AUTOPSY_HEAL (No healing needed, waiver provided)
    adv_heal = enforcer.advance_stage(
        stage="AUTOPSY_HEAL",
        actor="failure-analyst",
        evidence={"status": "PASSED", "verdict": "NO_HEAL_NEEDED"}
    )
    assert adv_heal["status"] == "PASS"

    # 9. Stage 5: ACCEPTANCE_DOD
    adv_dod = enforcer.advance_stage(
        stage="ACCEPTANCE_DOD",
        actor="quality-gatekeeper",
        evidence={"gates_passed": 10, "verify_all_passed": True}
    )
    assert adv_dod["status"] == "PASS"
    assert adv_dod["workflow_completed"] is True

    # 10. Audit compliance
    compliance = enforcer.verify_compliance()
    assert compliance["status"] == "PASS"
    assert compliance["compliant"] is True
    assert len(compliance["proof_tokens"]) == 5
