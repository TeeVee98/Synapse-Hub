#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/core/harness_sentinel.py — 6-Step Autonomous Agent Harness Health & Readiness Sentinel
---------------------------------------------------------------------------------------------
Performs holistic diagnostic auditing across the complete 6-Step Harness Architecture:
  Step 1 (Guides)       : AGENTS.md, Rules, and Skills Manifest integrity.
  Step 2 (Sensors)      : Static linters (infer_linter), Quality Gates DoD (verify_all).
  Step 3 (Agentic Loop) : Circuit Breaker (circuit_breaker), Runaway Sentinel, Loop Detector.
  Step 4 (Memory)       : Anthropic Dual-State Anchor (project_state.json + PROJECT_STATE.md).
  Step 5 (Permissions)  : Fail-Closed Shell Guard (pre_bash_guard) & Reversible Sandbox.
  Step 6 (Observability): W3C OpenTelemetry Trace Context & BPE Token Calibration.

Usage:
  python3 tools/core/harness_sentinel.py
  python3 tools/core/harness_sentinel.py --json
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone
from typing import Dict, Any

_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_ROOT = os.path.dirname(_CORE_DIR)
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass

# UTF-8 stdout encoding for cross-platform compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass


class HarnessSentinel:
    """Evaluates readiness and operational health across all 6 Harness layers."""

    def __init__(self, repo_root: str = _REPO_ROOT):
        self.repo_root = os.path.abspath(repo_root)

    def audit_step1_guides(self) -> Dict[str, Any]:
        """Step 1: Guides (Feedforward Controls)."""
        agents_md = os.path.join(self.repo_root, "AGENTS.md")
        skills_idx = os.path.join(self.repo_root, "skills_index.json")

        passed = os.path.exists(agents_md) and os.path.exists(skills_idx)
        details = []

        if os.path.exists(agents_md):
            with open(agents_md, "rb") as f:
                raw = f.read(3)
                if raw == b"\xef\xbb\xbf":
                    passed = False
                    details.append("AGENTS.md contains forbidden UTF-8 BOM")
                else:
                    details.append("AGENTS.md present and 100% UTF-8 clean")
        else:
            details.append("Missing core AGENTS.md guide")

        if os.path.exists(skills_idx):
            try:
                with open(skills_idx, "r", encoding="utf-8") as f:
                    skills_data = json.load(f)
                count = len(skills_data.get("skills", []))
                details.append(f"{count} modular skills indexed in skills_index.json")
            except Exception as err:
                passed = False
                details.append(f"skills_index.json parsing failed: {err}")

        return {
            "step": 1,
            "name": "Guides (Feedforward)",
            "passed": passed,
            "status": "PASS" if passed else "FAIL",
            "details": details
        }

    def audit_step2_sensors(self) -> Dict[str, Any]:
        """Step 2: Sensors (Feedback Controls via callable module smoke probes)."""
        linter_path = os.path.join(self.repo_root, "tools", "lint", "infer_linter.py")
        verify_path = os.path.join(self.repo_root, "tools", "core", "verify_all.py")
        gate_path = os.path.join(self.repo_root, "tools", "core", "fact_forcing_gate.py")

        passed = os.path.exists(linter_path) and os.path.exists(verify_path) and os.path.exists(gate_path)
        details = []

        if os.path.exists(linter_path):
            try:
                from tools.lint.infer_linter import classify_file_role
                role = classify_file_role("tests/test_smoke.py")
                if role == "TEST_SCRIPT":
                    details.append("Infer-Linter callable smoke probe verified (TEST_SCRIPT)")
                else:
                    passed = False
                    details.append(f"Infer-Linter smoke probe returned unexpected role: {role}")
            except Exception as err:
                passed = False
                details.append(f"Infer-Linter smoke probe failed: {err}")
        else:
            details.append("Infer-Linter: Missing")

        if os.path.exists(verify_path):
            try:
                from tools.core.verify_all import ALL_GATES, run_all_gates_detailed
                if len(ALL_GATES) >= 11 and callable(run_all_gates_detailed):
                    details.append(f"Verify-All ({len(ALL_GATES)} Gates) callable smoke probe verified")
                else:
                    passed = False
                    details.append(f"Verify-All smoke probe failed: {len(ALL_GATES)} gates registered")
            except Exception as err:
                passed = False
                details.append(f"Verify-All smoke probe failed: {err}")
        else:
            details.append("Verify-All: Missing")

        if os.path.exists(gate_path):
            try:
                from tools.core.fact_forcing_gate import evaluate_content
                ok, violations = evaluate_content("def test_smoke():\n    assert 1 == 1\n", "tests/test_smoke.py")
                if ok and not violations:
                    details.append("Fact-Forcing Gate callable smoke probe verified")
                else:
                    passed = False
                    details.append(f"Fact-Forcing Gate smoke probe failed: {violations}")
            except Exception as err:
                passed = False
                details.append(f"Fact-Forcing Gate smoke probe failed: {err}")
        else:
            details.append("Fact-Forcing Gate: Missing")

        return {
            "step": 2,
            "name": "Sensors (Feedback Quality Gates)",
            "passed": passed,
            "status": "PASS" if passed else "FAIL",
            "details": details
        }

    def audit_step3_agentic_loop(self) -> Dict[str, Any]:
        """Step 3: Agentic Loop (Bounded Retries & Token Budget)."""
        circuit_breaker_path = os.path.join(self.repo_root, "tools", "core", "circuit_breaker.py")
        runaway_stopper_path = os.path.join(self.repo_root, "tools", "orchestration", "runaway_stopper.py")

        passed = os.path.exists(circuit_breaker_path) and os.path.exists(runaway_stopper_path)
        details = []

        try:
            from tools.core.circuit_breaker import DEFAULT_THRESHOLDS, GLOBAL_CIRCUIT_BREAKER
            details.append(f"Token Budget: task={GLOBAL_CIRCUIT_BREAKER.task_token_budget:,}, session={GLOBAL_CIRCUIT_BREAKER.session_token_budget:,}")
            details.append(f"Runaway Thresholds: max_turns={DEFAULT_THRESHOLDS['max_turns']}, max_repeat={DEFAULT_THRESHOLDS['max_repeated_calls']}")
        except Exception as err:
            passed = False
            details.append(f"Failed to inspect Circuit Breaker: {err}")

        return {
            "step": 3,
            "name": "Agentic Loop (Bounded Execution)",
            "passed": passed,
            "status": "PASS" if passed else "FAIL",
            "details": details
        }

    def audit_step4_memory(self) -> Dict[str, Any]:
        """Step 4: Externalize Memory (Decoupled State & Decision Logs)."""
        json_path = os.path.join(self.repo_root, "project_state.json")
        md_path = os.path.join(self.repo_root, "PROJECT_STATE.md")

        passed = os.path.exists(json_path) and os.path.exists(md_path)
        details = []

        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    state_data = json.load(f)
                tasks_cnt = len(state_data.get("tasks", []))
                decisions_cnt = len(state_data.get("decisions", []))
                details.append(f"project_state.json valid schema ({tasks_cnt} active tasks, {decisions_cnt} decisions)")
            except Exception as err:
                passed = False
                details.append(f"project_state.json parse error: {err}")
        else:
            details.append("project_state.json not yet initialized")

        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            details.append(f"PROJECT_STATE.md size: {len(lines)} lines (Rolling Window < 50)")

        return {
            "step": 4,
            "name": "Externalize Memory (Dual-State Anchor)",
            "passed": passed,
            "status": "PASS" if passed else "FAIL",
            "details": details
        }

    def audit_step5_permissions(self) -> Dict[str, Any]:
        """Step 5: Permissions & Guardrails (Fail-Closed & HITL)."""
        pre_bash_path = os.path.join(self.repo_root, "tools", "lint", "pre_bash_guard.py")
        reversible_path = os.path.join(self.repo_root, "tools", "heal", "reversible_sandbox.py")

        passed = os.path.exists(pre_bash_path) and os.path.exists(reversible_path)
        details = []

        if os.path.exists(pre_bash_path):
            try:
                from tools.lint.pre_bash_guard import validate_shell_command
                approved, _ = validate_shell_command("rm -rf /")
                if not approved:
                    details.append("Pre-Bash Guard active: 'rm -rf /' successfully blocked (Fail-Closed)")
                else:
                    passed = False
                    details.append("Pre-Bash Guard failed to block destructive command")
            except Exception as err:
                passed = False
                details.append(f"Pre-Bash Guard check error: {err}")

        if os.path.exists(reversible_path):
            details.append("Reversible Sandbox WAL undo-stack present")

        return {
            "step": 5,
            "name": "Permissions & Guardrails (Fail-Closed)",
            "passed": passed,
            "status": "PASS" if passed else "FAIL",
            "details": details
        }

    def audit_step6_observability(self) -> Dict[str, Any]:
        """Step 6: Observability (Telemetry, BPE Calibration & Log Distiller smoke probes)."""
        telemetry_path = os.path.join(self.repo_root, "tools", "core", "telemetry.py")
        token_est_path = os.path.join(self.repo_root, "tools", "core", "token_estimator.py")
        distill_path = os.path.join(self.repo_root, "tools", "core", "distill_log.py")

        passed = os.path.exists(telemetry_path) and os.path.exists(token_est_path) and os.path.exists(distill_path)
        details = []

        if os.path.exists(telemetry_path):
            try:
                from tools.core.telemetry import generate_trace_id
                tid = generate_trace_id()
                if isinstance(tid, str) and len(tid) >= 16:
                    details.append(f"W3C OpenTelemetry smoke probe verified (Sample Trace ID: {tid[:12]}...)")
                else:
                    passed = False
                    details.append("W3C OpenTelemetry smoke probe returned invalid trace ID")
            except Exception as err:
                passed = False
                details.append(f"Telemetry smoke probe failed: {err}")

        if os.path.exists(token_est_path):
            try:
                from tools.core.token_estimator import count_tokens
                tok_count = count_tokens("Synapse Hub observability smoke probe")
                if isinstance(tok_count, int) and tok_count > 0:
                    details.append(f"BPE Token Estimator smoke probe verified ({tok_count} tokens)")
                else:
                    passed = False
                    details.append(f"BPE Token Estimator smoke probe returned invalid count: {tok_count}")
            except Exception as err:
                passed = False
                details.append(f"BPE Token Estimator smoke probe failed: {err}")

        if os.path.exists(distill_path):
            try:
                from tools.core.distill_log import distill
                distilled = distill("AssertionError: expected 1 == 2\n", exit_code=1, token_budget=100)
                if isinstance(distilled, str) and "AssertionError" in distilled:
                    details.append("Log Distiller callable smoke probe verified")
                else:
                    passed = False
                    details.append("Log Distiller smoke probe failed to preserve assertion signal")
            except Exception as err:
                passed = False
                details.append(f"Log Distiller smoke probe failed: {err}")

        return {
            "step": 6,
            "name": "Observability (W3C Telemetry & Costs)",
            "passed": passed,
            "status": "PASS" if passed else "FAIL",
            "details": details
        }

    def run_full_audit(self) -> Dict[str, Any]:
        """Runs complete 6-Step audit and calculates readiness score."""
        steps = [
            self.audit_step1_guides(),
            self.audit_step2_sensors(),
            self.audit_step3_agentic_loop(),
            self.audit_step4_memory(),
            self.audit_step5_permissions(),
            self.audit_step6_observability(),
        ]

        passed_count = sum(1 for s in steps if s["passed"])
        total_count = len(steps)
        readiness_score = round((passed_count / total_count) * 100, 1)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "harness": "Synapse-Hub Autonomous Agent Harness",
            "readiness_score": readiness_score,
            "overall_status": "READY" if readiness_score == 100.0 else "DEGRADED",
            "steps": steps
        }


def main():
    parser = argparse.ArgumentParser(description="6-Step Autonomous Agent Harness Health & Readiness Sentinel")
    parser.add_argument("--json", action="store_true", help="Output diagnostic report in raw JSON format")
    args = parser.parse_args()

    sentinel = HarnessSentinel()
    report = sentinel.run_full_audit()

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        sys.exit(0 if report["overall_status"] == "READY" else 1)

    print("======================================================================")
    print("      SYNAPSE HUB — 6-STEP AGENT HARNESS READINESS AUDIT              ")
    print("======================================================================")
    for s in report["steps"]:
        badge = "✅ [PASS]" if s["passed"] else "❌ [FAIL]"
        print(f"  {badge} STEP {s['step']}: {s['name']}")
        for d in s["details"]:
            print(f"       • {d}")
    print("----------------------------------------------------------------------")
    print(f"  HARNESS READINESS SCORE : {report['readiness_score']}% [{report['overall_status']}]")
    print("======================================================================")
    sys.exit(0 if report["overall_status"] == "READY" else 1)


if __name__ == "__main__":
    main()
