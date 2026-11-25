#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/core/eval_runner.py — Enterprise Harness Evaluation & Scoring Engine ("The Exam")
----------------------------------------------------------------------------------------
Implements the formal Eval-Driven Development (EDD) and Scoring Function s(e)
from 'The End of Harness Engineering' (Algorithm 1: One Round of the Loop):
  1. Computes a deterministic composite score s(e) in [0.0, 100.0] across:
     - Quality Gates (40%): 10 DoD Quality Gates passing.
     - Test Suite Execution (30%): Pytest regression suite pass rate / AST integrity.
     - Mutation Sensitivity (20%): Syntactic mutation score from micro_mutator.
     - Harness & Guides (10%): 6-layer Harness readiness and invariants.
  2. Enforces Retention Constraints (Anti-Capability Erosion Guard):
     - Prevents catastrophic forgetting: s(candidate) >= s(baseline) AND delta_broken == 0.
     - Rejects any candidate harness edit that breaks existing capabilities.
  3. Extracts Structured Failure Set F:
     - Categorizes all failures with line/context for downstream 4B editor / RSI loops.
  4. Generates Normalized Reports:
     - Machine-readable JSON: reports/eval_report.json
     - Human-readable Markdown: reports/EVAL_REPORT.md
     - Baseline checkpoint: reports/eval_baseline.json

Usage:
  python3 tools/core/eval_runner.py                    # Run standard evaluation
  python3 tools/core/eval_runner.py --tier fast        # Sub-3s rapid candidate loop
  python3 tools/core/eval_runner.py --tier impact      # Impact-scoped evaluation
  python3 tools/core/eval_runner.py --save-baseline    # Save current run as golden baseline
  python3 tools/core/eval_runner.py --compare          # Compare against golden baseline
  python3 tools/core/eval_runner.py --json             # Output pure JSON to stdout
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import io
import json
import logging
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("synapse.eval_runner")
DEFAULT_SUBPROCESS_TIMEOUT_SEC = 2.0

_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_ROOT = os.path.dirname(_CORE_DIR)
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError as exc:
    logger.debug("Optional tools package bootstrap skipped: %s", exc)

# Ensure UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError, ValueError) as exc:
        logger.debug("UTF-8 stdio reconfigure skipped: %s", exc)

# Scoring weights (sum = 1.0 -> 100 points maximum)
WEIGHT_GATES = 0.40       # 40 points: 10 DoD Quality Gates
WEIGHT_TESTS = 0.30       # 30 points: Pytest regression suite / AST verification
WEIGHT_MUTATION = 0.20    # 20 points: Assertion sensitivity & syntactic mutation
WEIGHT_HARNESS = 0.10     # 10 points: 6-layer Harness readiness & invariants

DEFAULT_BASELINE_FILE = os.path.join(_REPO_ROOT, "reports", "eval_baseline.json")
DEFAULT_REPORT_FILE = os.path.join(_REPO_ROOT, "reports", "eval_report.json")
DEFAULT_MARKDOWN_FILE = os.path.join(_REPO_ROOT, "reports", "EVAL_REPORT.md")


def get_git_commit(repo_root: str = _REPO_ROOT, timeout_sec: float = DEFAULT_SUBPROCESS_TIMEOUT_SEC) -> str:
    """Retrieves short git commit SHA of repository with bounded timeout."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=max(0.1, float(timeout_sec)),
        )
        return res.stdout.strip()[:10] if res.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        logger.debug("get_git_commit fallback triggered: %s", exc)
        return "unknown"


class EvalRunner:
    """The Exam: Deterministic Scoring & Retention Constraint Engine for Harness Evolution."""

    def __init__(
        self,
        repo_root: str = _REPO_ROOT,
        tier: str = "fast",
        baseline_path: str = DEFAULT_BASELINE_FILE,
        report_path: str = DEFAULT_REPORT_FILE,
    ):
        self.repo_root = os.path.abspath(repo_root)
        self.tier = tier.lower()
        self.baseline_path = os.path.abspath(baseline_path)
        self.report_path = os.path.abspath(report_path)

    def run_quality_gates(self, silent: bool = False) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Runs the DoD Quality Gates and consumes structured gate bundle directly in memory."""
        from tools.core.verify_all import run_all_gates_detailed, LAST_GATE_METRICS

        report_dir = os.path.dirname(self.report_path)
        verify_report_path = os.path.join(report_dir, "verify_all_report.json") if report_dir else None

        fast_flag = self.tier == "fast"
        old_stdout = None
        if silent:
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

        try:
            rc, vdata = run_all_gates_detailed(
                self.repo_root,
                mode="HUB",
                fast=fast_flag,
                tier=self.tier,
                output_format="text",
                report_path=verify_report_path,
            )
        finally:
            if old_stdout is not None:
                sys.stdout = old_stdout

        vdata = vdata if isinstance(vdata, dict) else {}
        gates_list = vdata.get("gates", [])
        total_default = len(gates_list) if gates_list else 11
        summary = vdata.get(
            "summary",
            {"total": total_default, "passed": total_default if rc == 0 else 0, "failed": 0 if rc == 0 else 1},
        )
        all_passed = rc == 0 and summary.get("failed", 0) == 0

        # Extract failures for failure set F
        failures: List[Dict[str, Any]] = []
        for g in gates_list:
            if not g.get("passed", False):
                failures.append({
                    "category": "QUALITY_GATE_FAILURE",
                    "gate": g.get("name", "Unknown Gate"),
                    "status": g.get("status", "FAIL"),
                    "message": f"Quality Gate '{g.get('name')}' failed DoD verification.",
                })

        gate_payload = {
            "all_passed": all_passed,
            "return_code": rc,
            "summary": summary,
            "gates": gates_list,
            "pytest_metrics": vdata.get("pytest_metrics") or LAST_GATE_METRICS.get("gate_7", {}),
            "mutation_metrics": vdata.get("assertion_and_mutation_metrics") or LAST_GATE_METRICS.get("gate_8", {}),
            "perf_metrics": vdata.get("performance_metrics") or LAST_GATE_METRICS.get("gate_10", {}),
        }
        return gate_payload, failures

    def run_harness_readiness(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Evaluates 6-layer harness health using HarnessSentinel (fail-closed on errors)."""
        failures: List[Dict[str, Any]] = []
        try:
            from tools.core.harness_sentinel import HarnessSentinel
            sentinel = HarnessSentinel(self.repo_root)
            report = sentinel.run_full_audit()
            score_pct = float(report.get("readiness_score", 0.0))
            for step in report.get("steps", []):
                if not step.get("passed", False):
                    failures.append({
                        "category": "HARNESS_LAYER_DEFECT",
                        "layer": f"step_{step.get('step', 'unknown')}",
                        "name": step.get("name", f"Step {step.get('step', '?')}"),
                        "details": step.get("details", []),
                        "message": f"Harness step {step.get('step')} ({step.get('name', 'unknown')}) failed.",
                    })
            return {"readiness_score": score_pct, "report": report}, failures
        except Exception as e:
            logger.debug("HarnessSentinel audit failed: %s", e)
            failures.append({
                "category": "HARNESS_LAYER_DEFECT",
                "layer": "sentinel",
                "name": "HarnessSentinel",
                "message": f"HarnessSentinel audit failed: {e}",
            })
            return {"readiness_score": 0.0, "error": str(e)}, failures

    def compute_composite_score(
        self,
        gate_data: Dict[str, Any],
        harness_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Computes the normalized scoring function s(e) in [0.0, 100.0]:
          - s_gates    = (passed_gates / total_gates) * 100
          - s_tests    = (passed_tests / total_active_tests) * 100 (or proportional static_fast_proxy in fast tier)
          - s_mutation = syntactic mutation score from micro_mutator (0.0 to 100.0; fail-closed 0.0 if missing)
          - s_harness  = 6-layer harness readiness percentage (fail-closed 0.0 if missing)
        """
        # 1. Gates sub-score (0 - 100)
        g_sum = gate_data.get("summary", {})
        total_g = max(g_sum.get("total", 11), 1)
        passed_g = g_sum.get("passed", 0)
        s_gates = (passed_g / total_g) * 100.0

        # 2. Test suite sub-score (0 - 100)
        p_metrics = gate_data.get("pytest_metrics", {}) or {}
        if self.tier == "fast":
            # In fast mode, Pytest is skipped; derive proportional static proxy from static gate health
            s_tests = s_gates
            tests_measurement_mode = "static_fast_proxy"
        else:
            p_passed = p_metrics.get("passed", 0)
            p_failed = p_metrics.get("failed", 0) + p_metrics.get("errors", 0)
            p_total = p_passed + p_failed
            if p_total > 0:
                s_tests = (p_passed / p_total) * 100.0
                tests_measurement_mode = "pytest"
            else:
                s_tests = 100.0 if gate_data.get("all_passed") else 0.0
                tests_measurement_mode = "uncollected"

        # 3. Mutation sub-score (0 - 100, fail-closed 0.0 when absent)
        m_metrics = gate_data.get("mutation_metrics", {}) or {}
        if m_metrics.get("mutation_score") is not None:
            s_mutation = float(m_metrics["mutation_score"])
        elif m_metrics.get("static_assertion_sensitivity_score") is not None:
            s_mutation = float(m_metrics["static_assertion_sensitivity_score"])
        else:
            s_mutation = 0.0

        # 4. Harness readiness sub-score (0 - 100, fail-closed 0.0 when absent)
        s_harness = float(harness_data.get("readiness_score", 0.0))

        # Composite weighted sum
        composite = (
            (WEIGHT_GATES * s_gates)
            + (WEIGHT_TESTS * s_tests)
            + (WEIGHT_MUTATION * s_mutation)
            + (WEIGHT_HARNESS * s_harness)
        )
        composite = max(0.0, min(100.0, round(composite, 2)))

        return {
            "composite_score": composite,
            "tests_measurement_mode": tests_measurement_mode,
            "components": {
                "gates": {"score": round(s_gates, 2), "weight": WEIGHT_GATES, "contribution": round(s_gates * WEIGHT_GATES, 2)},
                "tests": {"score": round(s_tests, 2), "weight": WEIGHT_TESTS, "contribution": round(s_tests * WEIGHT_TESTS, 2), "measurement_mode": tests_measurement_mode},
                "mutation": {"score": round(s_mutation, 2), "weight": WEIGHT_MUTATION, "contribution": round(s_mutation * WEIGHT_MUTATION, 2)},
                "harness": {"score": round(s_harness, 2), "weight": WEIGHT_HARNESS, "contribution": round(s_harness * WEIGHT_HARNESS, 2)},
            },
        }

    def check_retention_constraints(
        self,
        candidate_score: float,
        candidate_gates: List[Dict[str, Any]],
        baseline: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Enforces the Retention Constraint (Anti-Capability Erosion):
          Rule: candidate_score >= baseline_score AND zero regressed gates.
        """
        if not baseline:
            return {
                "has_baseline": False,
                "retention_passed": True,
                "delta_score": 0.0,
                "regressed_gates": [],
                "decision": "ACCEPTED (INITIAL_BASELINE)",
                "note": "No prior baseline found; candidate recorded as baseline reference.",
            }

        b_score = baseline.get("score", {}).get("composite_score", 0.0)
        delta_score = round(candidate_score - b_score, 2)

        # Map baseline gate pass/fail
        b_gates = {g["name"]: g.get("passed", False) for g in baseline.get("gates", [])}
        regressed_gates = []
        for cg in candidate_gates:
            gname = cg["name"]
            c_passed = cg.get("passed", False)
            if b_gates.get(gname, True) and not c_passed:
                regressed_gates.append(gname)

        has_regression = len(regressed_gates) > 0 or delta_score < -0.01
        retention_passed = not has_regression
        decision = "ACCEPTED" if retention_passed else "REJECTED (CAPABILITY_EROSION)"

        return {
            "has_baseline": True,
            "baseline_score": b_score,
            "delta_score": delta_score,
            "retention_passed": retention_passed,
            "regressed_gates": regressed_gates,
            "decision": decision,
            "note": (
                "Candidate satisfies all retention constraints; no regression detected."
                if retention_passed
                else f"Capability erosion detected: {len(regressed_gates)} regressed gate(s), delta: {delta_score:+0.2f} pts."
            ),
        }

    def evaluate(self, compare_baseline: bool = True, silent: bool = False) -> Dict[str, Any]:
        """Executes the full evaluation cycle (The Exam)."""
        start_time = time.monotonic()
        commit_sha = get_git_commit(self.repo_root, timeout_sec=DEFAULT_SUBPROCESS_TIMEOUT_SEC)

        # 1. Run 10 Quality Gates DoD
        gate_data, gate_failures = self.run_quality_gates(silent=silent)

        # 2. Run Harness Readiness Sentinel
        harness_data, harness_failures = self.run_harness_readiness()

        # 3. Aggregate failure set F
        failures = gate_failures + harness_failures

        # 4. Compute composite scoring s(e)
        score_breakdown = self.compute_composite_score(gate_data, harness_data)
        composite_score = score_breakdown["composite_score"]

        # 5. Check Retention Constraints against baseline
        baseline = self.load_baseline() if compare_baseline else None
        retention = self.check_retention_constraints(
            candidate_score=composite_score,
            candidate_gates=gate_data.get("gates", []),
            baseline=baseline,
        )

        duration = max(0.0, round(time.monotonic() - start_time, 4))

        result_doc = {
            "schema_version": "1.0.0",
            "eval_title": "Enterprise Harness Evaluation (The Exam)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target": self.repo_root,
            "git_commit": commit_sha,
            "tier": self.tier,
            "score": score_breakdown,
            "retention": retention,
            "all_passed": gate_data.get("all_passed", False) and retention.get("retention_passed", True),
            "failures_count": len(failures),
            "failures": failures,
            "gates_summary": gate_data.get("summary", {}),
            "gates": gate_data.get("gates", []),
            "duration_sec": duration,
            "resilience_metadata": {
                "clock_source": "time.monotonic",
                "subprocess_timeout_sec": DEFAULT_SUBPROCESS_TIMEOUT_SEC,
            },
        }

        # Persist report
        self.save_report(result_doc)
        return result_doc

    def load_baseline(self) -> Optional[Dict[str, Any]]:
        """Loads baseline evaluation result from file."""
        if not os.path.exists(self.baseline_path):
            return None
        try:
            with open(self.baseline_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.debug("Failed to load baseline from %s: %s", self.baseline_path, e)
            return None

    def save_baseline(self, result_doc: Dict[str, Any]) -> None:
        """Saves current evaluation result as new golden baseline."""
        os.makedirs(os.path.dirname(self.baseline_path), exist_ok=True)
        with open(self.baseline_path, "w", encoding="utf-8") as f:
            json.dump(result_doc, f, indent=2)
        print(f"✨ Golden baseline saved to: {self.baseline_path}")

    def save_report(self, result_doc: Dict[str, Any]) -> None:
        """Persists JSON and Markdown evaluation reports."""
        os.makedirs(os.path.dirname(self.report_path), exist_ok=True)
        with open(self.report_path, "w", encoding="utf-8") as f:
            json.dump(result_doc, f, indent=2)

        # Generate Markdown summary
        md_lines = [
            "# 📋 Enterprise Harness Evaluation Report (The Exam)",
            "",
            f"- **Timestamp:** `{result_doc['timestamp']}`",
            f"- **Git Commit:** `{result_doc['git_commit']}` | **Tier:** `{result_doc['tier'].upper()}`",
            f"- **Composite Score:** **`{result_doc['score']['composite_score']} / 100.0`**",
            f"- **Retention Status:** **`{result_doc['retention']['decision']}`**",
            "",
            "## 1. Score Breakdown",
            "",
            "| Component | Weight | Score | Contribution |",
            "| :--- | :---: | :---: | :---: |",
        ]
        for cname, cinfo in result_doc["score"]["components"].items():
            md_lines.append(f"| **{cname.title()}** | {int(cinfo['weight']*100)}% | {cinfo['score']}/100 | **{cinfo['contribution']} pts** |")

        total_gates = result_doc.get("gates_summary", {}).get("total", len(result_doc.get("gates", [])) or 11)
        md_lines.extend([
            "",
            "## 2. Retention Constraints (Anti-Capability Erosion)",
            "",
            f"- **Decision:** `{result_doc['retention']['decision']}`",
            f"- **Score Delta:** `{result_doc['retention'].get('delta_score', 0.0):+0.2f} pts`",
            f"- **Regressed Gates:** `{len(result_doc['retention'].get('regressed_gates', []))}`",
            f"- **Notes:** {result_doc['retention'].get('note', '')}",
            "",
            f"## 3. {total_gates} Quality Gates Summary",
            "",
            "| Gate | Status | Result |",
            "| :--- | :---: | :---: |",
        ])
        for g in result_doc.get("gates", []):
            icon = "✅ PASS" if g.get("passed") else "❌ FAIL"
            md_lines.append(f"| {g.get('name')} | `{g.get('status')}` | {icon} |")

        if result_doc.get("failures"):
            md_lines.extend([
                "",
                "## 4. Failure Set F (For Self-Improving Loop / 4B Editor)",
                "",
            ])
            for i, fail in enumerate(result_doc["failures"], 1):
                md_lines.append(f"{i}. **[{fail.get('category')}]** {fail.get('gate', fail.get('name', 'General'))}: {fail.get('message', '')}")

        md_target = (
            DEFAULT_MARKDOWN_FILE
            if os.path.abspath(self.report_path) == os.path.abspath(DEFAULT_REPORT_FILE)
            else os.path.join(os.path.dirname(self.report_path), "EVAL_REPORT.md")
        )
        try:
            with open(md_target, "w", encoding="utf-8") as f:
                f.write("\n".join(md_lines) + "\n")
        except Exception as e:
            logger.debug("Failed to write Markdown report: %s", e)


def print_eval_dashboard(result: Dict[str, Any]) -> None:
    """Renders human-friendly console dashboard for The Exam."""
    score = result["score"]["composite_score"]
    retention = result["retention"]
    decision = retention["decision"]
    delta = retention.get("delta_score", 0.0)

    # ANSI colors
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    color = GREEN if "ACCEPTED" in decision else RED

    print("\n" + "=" * 76)
    print(f"{BOLD}{CYAN}  🎓 ENTERPRISE HARNESS EVALUATION HARNESS — 'THE EXAM' (ALGORITHM 1){RESET}")
    print("=" * 76)
    print(f"  Target Repository : {result['target']}")
    print(f"  Git Commit / Tier : {result['git_commit']}  |  Tier: {result['tier'].upper()} ({result['duration_sec']}s)")
    print("-" * 76)
    print(f"  {BOLD}🏆 COMPOSITE SCORE s(e) : {color}{score:0.2f} / 100.0{RESET}  (Delta: {delta:+0.2f} pts)")
    print(f"  {BOLD}🛡️ RETENTION DECISION   : {color}{decision}{RESET}")
    print("-" * 76)
    print(f"  {BOLD}Component Breakdown:{RESET}")
    for cname, cinfo in result["score"]["components"].items():
        print(f"    • {cname.title():<10} : {cinfo['score']:>6.2f} / 100  (Weight: {int(cinfo['weight']*100):>2}%)  ->  {cinfo['contribution']:>5.2f} pts")
    print("-" * 76)

    # Dynamic Gates summary
    g_sum = result["gates_summary"]
    total_g = g_sum.get("total", len(result.get("gates", [])) or 11)
    pass_str = f"{GREEN}{g_sum.get('passed', 0)} PASS{RESET}"
    fail_str = f"{RED}{g_sum.get('failed', 0)} FAIL{RESET}" if g_sum.get("failed", 0) > 0 else "0 FAIL"
    print(f"  Quality Gates DoD : {total_g}/{total_g} Total  [{pass_str} | {fail_str}]")

    if result.get("failures_count", 0) > 0:
        print(f"  {RED}⚠️ Failures Detected ({result['failures_count']} items in Set F):{RESET}")
        for f in result.get("failures", [])[:5]:
            print(f"    - [{f.get('category')}] {f.get('message', f.get('gate', ''))}")
        if result["failures_count"] > 5:
            print(f"    - ... and {result['failures_count'] - 5} more failure(s).")
    else:
        print(f"  {GREEN}✅ Zero Defects: All {total_g} Gates and Invariants Satisfied 100%.{RESET}")

    print("=" * 76)
    if "ACCEPTED" in decision:
        print(f"  {GREEN}{BOLD}[CANDIDATE SURVIVES]{RESET} Candidate satisfies all retention constraints.")
    else:
        print(f"  {RED}{BOLD}[CANDIDATE DROPPED]{RESET} Capability erosion detected! Rolling back candidate.")
    print("=" * 76 + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Enterprise Harness Scoring Engine ('The Exam')")
    parser.add_argument("target", nargs="?", default=_REPO_ROOT, help="Target repository root")
    parser.add_argument("--tier", choices=["fast", "impact", "full"], default="fast", help="Evaluation speed tier")
    parser.add_argument("--save-baseline", action="store_true", help="Save current evaluation as golden baseline reference")
    parser.add_argument("--compare", action="store_true", default=True, help="Compare current evaluation against baseline")
    parser.add_argument("--no-compare", dest="compare", action="store_false", help="Bypass baseline comparison")
    parser.add_argument("--json", action="store_true", help="Output pure JSON to stdout")
    parser.add_argument("--baseline-path", default=DEFAULT_BASELINE_FILE, help="Custom baseline file path")
    parser.add_argument("--report-path", default=DEFAULT_REPORT_FILE, help="Custom report file path")
    args = parser.parse_args()

    runner = EvalRunner(
        repo_root=args.target,
        tier=args.tier,
        baseline_path=args.baseline_path,
        report_path=args.report_path,
    )

    compare = args.compare and not args.save_baseline
    result = runner.evaluate(compare_baseline=compare, silent=args.json)

    if args.save_baseline:
        result["retention"]["decision"] = "ACCEPTED (BASELINE_ESTABLISHED)"
        result["retention"]["note"] = "Golden baseline established / updated."
        runner.save_baseline(result)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_eval_dashboard(result)

    # Return 0 if accepted and all passed, else 1
    decision_ok = "ACCEPTED" in result.get("retention", {}).get("decision", "")
    return 0 if (result.get("all_passed", False) and decision_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
