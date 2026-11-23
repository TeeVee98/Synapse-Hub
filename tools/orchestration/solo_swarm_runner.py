#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/orchestration/solo_swarm_runner.py — Automated Solo-Swarm 4-Weapon Orchestrator

Integrates the 4 weapons of single-agent engineering rigor into an automated, deterministic pipeline:
  - Weapon 1: Test-First Inversion (Red-First Invariant with Forensic Red Receipt & Anti-Cheat Tautology Sentinel)
  - Weapon 2: 3-Phase Cognitive Persona Shifting (Red QA -> Blue Dev -> Purple Auditor)
  - Weapon 3: Live Dynamic Mutation Sentinel (micro_mutator with Diff-Scoped Targeting & >= 80% Threshold)
  - Weapon 4: Zero-Sum Prover-Verifier Debate (Nash Equilibrium extraction of 4 Contrarian Adversarial Perspectives)
"""

import os
import re
import sys
import json
import hashlib
import argparse
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass

from tools.reasoning.prover_verifier_games import ProverVerifierGame
from tools.lint.micro_mutator import evaluate_target

DEFAULT_RECEIPT_PATH = os.path.join(_REPO_ROOT, "reports", "tdd_red_receipt.json")
DEFAULT_MUTATION_THRESHOLD = 80.0

CONTRARIAN_PERSPECTIVES = [
    "Vulnerability 1 (Chaos & Network): Simulate downstream service timeout, 503 transient drop, and retry backoff.",
    "Vulnerability 2 (Concurrency & Race): Simulate 50ms rapid double-action, duplicate idempotency key, and dirty state reads.",
    "Vulnerability 3 (Boundary & Malformed): Empty payload, null byte, max integer overflow, and schema drift violation.",
    "Vulnerability 4 (Blast Radius & Migration): Backward compatibility with legacy callers and state migration safety.",
]


def is_literal_constant(expr: str) -> bool:
    """Returns True if expr is a literal constant (numbers, bools, strings, None) with no variables or calls."""
    expr = expr.strip()
    if expr in ("True", "False", "None", "true", "false", "null"):
        return True
    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", expr):
        return True
    if (expr.startswith('"') and expr.endswith('"') and len(expr) >= 2) or (
        expr.startswith("'") and expr.endswith("'") and len(expr) >= 2
    ):
        return True
    return False


def is_tautological_assertion(stmt: str) -> Tuple[bool, Optional[str]]:
    """
    Checks if an assertion statement is purely tautological (assert False, assert 0, assert 1 == 2, assert 'a' == 'b').
    """
    stmt = stmt.strip()
    # Check bare assert False, assert 0, assert None, assert not True
    m_bare = re.match(r"^assert\s+(False|0|None|not\s+True)\b(?:\s*,\s*.*)?$", stmt, re.IGNORECASE)
    if m_bare:
        return True, f"Literal constant assertion: 'assert {m_bare.group(1)}'"

    # Check comparison: assert left op right where BOTH operands are literal constants
    m_cmp = re.match(r"^assert\s+(.+?)\s*(==|!=|<|>|<=|>=|is|is\s+not)\s*(.+?)(?:\s*,\s*.*)?$", stmt)
    if m_cmp:
        left, op, right = m_cmp.group(1).strip(), m_cmp.group(2).strip(), m_cmp.group(3).strip()
        if is_literal_constant(left) and is_literal_constant(right):
            return True, f"Literal constant comparison: 'assert {left} {op} {right}'"

    # Check pytest.fail with literal reason or empty
    if re.match(r"^(?:pytest\.)?fail\s*\(", stmt):
        return True, "Forced failure via pytest.fail() call without domain assertion"

    return False, None


def detect_tautological_red(failure_output: str, test_cmd: str = "") -> Tuple[bool, Optional[str]]:
    """
    Milestone 2 Anti-Cheat: Analyzes failure traceback and test command to detect literal tautological failures.
    Catches cheats like 'assert False', 'assert 1 == 2', 'assert 0 == 1', or 'pytest.fail()'.
    Distinguishes between Pytest source code lines ('> assert ...') and runtime evaluation lines ('E assert ...')
    to prevent false positives on dynamic assertions like 'assert resp.status_code == 200' where the failure
    excerpt contains 'E assert 404 == 200'.
    """
    # 1. Check test_cmd itself for forced failures (e.g. python -c "assert False")
    if test_cmd:
        m_cmd = re.search(r'-c\s+["\'](.*?)["\']', test_cmd)
        target_stmts = [m_cmd.group(1)] if m_cmd else [test_cmd]
        for s in target_stmts:
            for sub_s in s.split(";"):
                sub_s = sub_s.strip()
                is_cheat, reason = is_tautological_assertion(sub_s)
                if is_cheat:
                    return True, f"Tautological Red Violation: {reason} in test command."
            if re.search(r"\bassert\s+(?:False|0|None)\b", s, re.IGNORECASE):
                return True, "Tautological Red Violation: literal 'assert False' or 'assert 0' in test command."

    # 2. Check failure_output: focus strictly on source lines (prefixed with '>') or standard traceback source lines
    if failure_output:
        lines = failure_output.splitlines()
        for idx, line in enumerate(lines):
            line_s = line.strip()
            # Pytest source line indicator
            if line_s.startswith(">"):
                src_stmt = line_s.lstrip(">").strip()
                is_cheat, reason = is_tautological_assertion(src_stmt)
                if is_cheat:
                    return True, f"Tautological Red Violation: {reason} in test source."
            # Standard Python traceback line immediately preceding AssertionError
            if line_s == "AssertionError" or line_s.startswith("AssertionError:"):
                if idx > 0:
                    prev_line = lines[idx - 1].strip()
                    is_cheat, reason = is_tautological_assertion(prev_line)
                    if is_cheat:
                        return True, f"Tautological Red Violation: {reason} in traceback."

    return False, None


def resolve_auto_targets(repo_root: Optional[str] = None) -> List[str]:
    """
    Milestone 3 Anti-Shrinking: Scans git diff and untracked files to automatically discover all modified source files.
    Excludes test files, reports, and documentation.
    """
    root = repo_root or _REPO_ROOT
    files: Set[str] = set()
    try:
        # 1. Tracked changes against HEAD (both staged and uncommitted)
        proc1 = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
            errors="replace",
        )
        if proc1.returncode == 0:
            files.update(proc1.stdout.splitlines())

        # 2. Unstaged changes in working tree
        proc2 = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
            errors="replace",
        )
        if proc2.returncode == 0:
            files.update(proc2.stdout.splitlines())

        # 3. Untracked new files (excluding .gitignore entries)
        proc3 = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
            errors="replace",
        )
        if proc3.returncode == 0:
            files.update(proc3.stdout.splitlines())

        valid_exts = {".py", ".groovy", ".ts", ".js", ".java"}
        source_files = []
        for f in sorted(files):
            norm_f = f.strip().replace("\\", "/")
            if any(norm_f.endswith(ext) for ext in valid_exts):
                if (
                    not norm_f.startswith("tests/")
                    and "/tests/" not in norm_f
                    and not norm_f.startswith("reports/")
                    and not norm_f.startswith("docs/")
                ):
                    full_p = os.path.join(root, norm_f)
                    if os.path.isfile(full_p):
                        source_files.append(norm_f)
        return source_files
    except Exception:
        return []


def run_debate(
    proposal: str,
    context: Optional[str] = None,
    rounds: int = 3,
    judge_mode: str = "strict",
    repo_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Weapon 4: Run Prover-Verifier debate with 4 Contrarian Perspectives and extract adversarial test cases.
    """
    root = repo_root or _REPO_ROOT

    # Milestone 3: Enrich context with Contrarian Adversarial Perspectives
    adversarial_context = (context or "") + "\n\nAdversarial Evaluation Directives:\n" + "\n".join(f"- {p}" for p in CONTRARIAN_PERSPECTIVES)

    game = ProverVerifierGame(repo_root=root)
    result = game.run_debate(proposal=proposal, context=adversarial_context, rounds=rounds, judge_mode=judge_mode)

    # Automatically extract counter_examples into structured test scenarios
    counter_examples = []
    for item in result.get("transcript", []):
        vc = item.get("verifier_counter", {})
        for ce in vc.get("counter_examples", []):
            if ce not in counter_examples:
                counter_examples.append(ce)

    structured_test_scenarios = []
    for idx, ce in enumerate(counter_examples, 1):
        clean_name = ce.replace("Counter-example: ", "").strip()
        structured_test_scenarios.append({
            "id": f"TC-ADV-{idx:02d}",
            "description": clean_name,
            "category": "adversarial_boundary",
            "required_assert": "Explicit boundary validation preventing unhandled crash / silent pass",
        })

    return {
        "status": "COMPLETED",
        "proposal": proposal,
        "winner": result.get("winner"),
        "nash_equilibrium_score": result.get("nash_equilibrium_score"),
        "rounds_completed": result.get("rounds_completed"),
        "counter_examples_count": len(counter_examples),
        "counter_examples": counter_examples,
        "unresolved_vulnerabilities": result.get("unresolved_vulnerabilities", []),
        "structured_test_scenarios": structured_test_scenarios,
        "contrarian_perspectives_injected": len(CONTRARIAN_PERSPECTIVES),
        "debate_raw": result,
    }


def certify_red_phase(
    test_cmd: str,
    receipt_path: Optional[str] = None,
    cwd: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Weapon 1: Physically execute test_cmd and certify that tests FAIL (Red Phase).
    Enforces Anti-Cheat Tautology checks to reject 'assert False' or 'assert 1 == 2'.
    Saves forensic failure receipt to receipt_path.
    """
    if not test_cmd or not test_cmd.strip():
        return {
            "status": "ERROR",
            "passed": False,
            "error": "Missing test command. Provide a non-empty test command via --test-cmd.",
        }

    working_dir = cwd or _REPO_ROOT
    target_receipt = receipt_path or DEFAULT_RECEIPT_PATH
    os.makedirs(os.path.dirname(os.path.abspath(target_receipt)), exist_ok=True)

    # Execute test command
    start_time = datetime.now(timezone.utc)
    try:
        proc = subprocess.run(
            test_cmd,
            shell=True,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
            encoding="utf-8",
            errors="replace",
        )
        exit_code = proc.returncode
        output = proc.stdout
    except Exception as e:
        exit_code = 1
        output = f"Execution exception: {e}"

    duration_sec = (datetime.now(timezone.utc) - start_time).total_seconds()

    # Red-First Invariant: Test MUST fail initially!
    if exit_code == 0:
        return {
            "status": "FAKE_RED_REJECTED",
            "passed": False,
            "test_cmd": test_cmd,
            "exit_code": exit_code,
            "error": "Fake Red Violation: Test passed on initial run. Test MUST fail before implementation to verify Red Phase.",
            "duration_sec": duration_sec,
        }

    # Milestone 2 Anti-Cheat: Reject literal tautological failures
    is_tautological, violation_msg = detect_tautological_red(output, test_cmd=test_cmd)
    if is_tautological:
        return {
            "status": "TAUTOLOGICAL_RED_REJECTED",
            "passed": False,
            "test_cmd": test_cmd,
            "exit_code": exit_code,
            "error": violation_msg,
            "duration_sec": duration_sec,
        }

    # Extract failure excerpt (last 30 lines)
    output_lines = output.splitlines()
    excerpt = output_lines[-30:] if len(output_lines) > 30 else output_lines
    excerpt_text = "\n".join(excerpt)
    sha_hash = hashlib.sha256(output.encode("utf-8", errors="replace")).hexdigest()

    receipt_payload = {
        "status": "CERTIFIED_RED",
        "certified_at": datetime.now(timezone.utc).isoformat(),
        "test_cmd": test_cmd,
        "exit_code": exit_code,
        "duration_sec": duration_sec,
        "failure_sha256": sha_hash,
        "failure_excerpt": excerpt_text,
    }

    with open(target_receipt, "w", encoding="utf-8") as f:
        json.dump(receipt_payload, f, indent=2)

    return {
        "status": "CERTIFIED_RED",
        "passed": True,
        "test_cmd": test_cmd,
        "exit_code": exit_code,
        "duration_sec": duration_sec,
        "receipt_file": target_receipt,
        "failure_sha256": sha_hash,
        "message": "✅ Red Phase Certified: Tests failed as expected. Physical Red Receipt recorded.",
    }


def certify_green_phase(
    test_cmd: str,
    receipt_path: Optional[str] = None,
    cwd: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Weapon 2: Execute test_cmd and verify that tests now PASS (Green Phase).
    Requires a valid prior Red Receipt to prevent skipping the Red Phase.
    """
    if not test_cmd or not test_cmd.strip():
        return {
            "status": "ERROR",
            "passed": False,
            "error": "Missing test command. Provide a non-empty test command via --test-cmd.",
        }

    working_dir = cwd or _REPO_ROOT
    target_receipt = receipt_path or DEFAULT_RECEIPT_PATH

    # Verify prior Red Receipt existence
    if not os.path.exists(target_receipt):
        return {
            "status": "MISSING_RED_RECEIPT",
            "passed": False,
            "test_cmd": test_cmd,
            "error": f"Cannot certify Green Phase without a prior Red Receipt at '{target_receipt}'. Run --red first!",
        }

    try:
        with open(target_receipt, "r", encoding="utf-8") as f:
            red_data = json.load(f)
        if red_data.get("status") != "CERTIFIED_RED":
            return {
                "status": "INVALID_RED_RECEIPT",
                "passed": False,
                "error": f"Prior receipt does not have 'CERTIFIED_RED' status: found {red_data.get('status')}",
            }
    except Exception as e:
        return {
            "status": "CORRUPT_RED_RECEIPT",
            "passed": False,
            "error": f"Failed to read Red Receipt: {e}",
        }

    # Execute test command
    start_time = datetime.now(timezone.utc)
    try:
        proc = subprocess.run(
            test_cmd,
            shell=True,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
            encoding="utf-8",
            errors="replace",
        )
        exit_code = proc.returncode
        output = proc.stdout
    except Exception as e:
        exit_code = 1
        output = f"Execution exception: {e}"

    duration_sec = (datetime.now(timezone.utc) - start_time).total_seconds()

    if exit_code != 0:
        return {
            "status": "GREEN_FAILED",
            "passed": False,
            "test_cmd": test_cmd,
            "exit_code": exit_code,
            "error": "Tests are still failing. Blue implementer must fix logic until exit code is 0.",
            "duration_sec": duration_sec,
            "failure_excerpt": "\n".join(output.splitlines()[-20:]),
        }

    return {
        "status": "CERTIFIED_GREEN",
        "passed": True,
        "test_cmd": test_cmd,
        "exit_code": 0,
        "duration_sec": duration_sec,
        "red_certified_at": red_data.get("certified_at"),
        "message": "✅ Green Phase Certified: All tests pass with zero exceptions.",
    }


def certify_mutation_phase(
    target_file: str = "",
    test_cmd: str = "",
    threshold: float = DEFAULT_MUTATION_THRESHOLD,
    timeout: float = 60.0,
    diff_only: bool = True,
    repo_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Weapon 3: Run live dynamic mutation testing against target_file using test_cmd.
    If target_file is omitted, automatically resolves all modified source files from git diff and untracked files.
    By default scopes mutations to git diff line ranges (diff_only=True) to cut execution time by 95%.
    """
    root = repo_root or _REPO_ROOT

    # Milestone 3: Auto-target discovery if target_file is empty
    auto_targeted = False
    targets = [target_file] if target_file else []
    if target_file:
        abs_explicit = os.path.abspath(target_file) if os.path.isabs(target_file) else os.path.join(root, target_file)
        if not os.path.exists(abs_explicit):
            return {
                "status": "ERROR",
                "passed": False,
                "error": f"Target source file not found at '{abs_explicit}'",
            }
    else:
        targets = resolve_auto_targets(repo_root=root)
        auto_targeted = True
        if not targets:
            return {
                "status": "ERROR",
                "passed": False,
                "error": "No target file specified and no modified source files detected in git diff or untracked state. Provide a target via --target.",
            }

    if not test_cmd or not test_cmd.strip():
        return {
            "status": "ERROR",
            "passed": False,
            "error": "Missing test command for mutation verification. Pass --test-cmd '<command>'.",
        }

    target_results: Dict[str, Any] = {}
    total_mutants_sum = 0
    killed_sum = 0
    survived_sum = 0
    all_passed = True

    for t in targets:
        abs_target = os.path.abspath(t) if os.path.isabs(t) else os.path.join(root, t)
        if not os.path.exists(abs_target):
            continue

        res = evaluate_target(
            target_path=abs_target,
            min_score=threshold,
            test_cmd=test_cmd,
            timeout=timeout,
            diff_only=diff_only,
        )
        target_results[t] = res
        t_total = res.get("total_mutants", 0)
        t_killed = res.get("killed", 0)
        t_survived = res.get("survived", 0)
        total_mutants_sum += t_total
        killed_sum += t_killed
        survived_sum += t_survived
        if not res.get("passed", False):
            all_passed = False

    if not target_results:
        return {
            "status": "ERROR",
            "passed": False,
            "error": "No valid target source files found to evaluate.",
        }

    overall_score = (killed_sum / total_mutants_sum * 100.0) if total_mutants_sum > 0 else 0.0
    passed = all_passed and (overall_score >= threshold)

    effective_target = targets[0] if len(targets) == 1 else f"{len(targets)} targets ({', '.join(targets[:3])}{'...' if len(targets) > 3 else ''})"

    return {
        "status": "CERTIFIED_MUTATION" if passed else "MUTATION_REJECTED",
        "passed": passed,
        "target_file": effective_target,
        "targets_evaluated": list(target_results.keys()),
        "auto_targeted": auto_targeted,
        "diff_only": diff_only,
        "test_cmd": test_cmd,
        "mutation_score": overall_score,
        "required_threshold": threshold,
        "total_mutants": total_mutants_sum,
        "killed": killed_sum,
        "survived": survived_sum,
        "target_details": target_results,
        "message": (
            f"✅ Mutation Phase Certified: Assertion sensitivity {overall_score:.1f}% >= {threshold}% (Killed {killed_sum}/{total_mutants_sum} mutants across {len(target_results)} files)."
            if passed
            else f"❌ Mutation Phase Rejected: Sensitivity {overall_score:.1f}% < {threshold}% or survivor detected. Strengthen test assertions."
        ),
    }


def get_status(receipt_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns current Solo-Swarm verification status.
    """
    target_receipt = receipt_path or DEFAULT_RECEIPT_PATH
    has_red = os.path.exists(target_receipt)
    red_data = None
    if has_red:
        try:
            with open(target_receipt, "r", encoding="utf-8") as f:
                red_data = json.load(f)
        except Exception:
            red_data = {"status": "CORRUPTED"}

    return {
        "red_receipt_exists": has_red,
        "receipt_file": target_receipt,
        "red_details": red_data,
        "protocol": "Solo-Swarm 4-Weapon Orchestrator",
        "standards_reference": "standards/qa-process/solo-swarm-protocol.md",
        "contrarian_perspectives_count": len(CONTRARIAN_PERSPECTIVES),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="solo_swarm_runner.py",
        description="Solo-Swarm 4-Weapon Orchestrator: Automated Test-First, Cognitive Shift, Mutation & Debate Runner.",
    )
    group = parser.add_argument_group("Solo-Swarm Action Modes")
    group.add_argument("--proposal", type=str, help="Weapon 4: Run Prover-Verifier debate on architectural/test proposal")
    group.add_argument("--red", action="store_true", help="Weapon 1: Verify and certify Red Phase (test must fail)")
    group.add_argument("--green", action="store_true", help="Weapon 2: Verify and certify Green Phase (test must pass)")
    group.add_argument("--mutation", action="store_true", help="Weapon 3: Run live dynamic mutation testing")
    group.add_argument("--status", action="store_true", help="Display current Solo-Swarm verification state")

    parser.add_argument("--test-cmd", type=str, default="", help="Dynamic test command (e.g. 'pytest tests/test_target.py')")
    parser.add_argument("--target", type=str, default="", help="Target source file for mutation testing (auto-resolved from git diff if omitted)")
    parser.add_argument("--rounds", type=int, default=3, help="Debate rounds for Weapon 4 (default: 3)")
    parser.add_argument("--judge-mode", choices=["strict", "evidence_weighted", "consensus"], default="strict", help="Debate judge mode")
    parser.add_argument("--threshold", type=float, default=DEFAULT_MUTATION_THRESHOLD, help="Minimum mutation score threshold (default: 80.0)")
    parser.add_argument("--timeout", type=float, default=60.0, help="Per-mutant test execution timeout in seconds")
    parser.add_argument("--receipt-path", type=str, default=DEFAULT_RECEIPT_PATH, help="Path to TDD Red Receipt file")
    parser.add_argument("--diff-only", action="store_true", default=True, help="Scope mutations strictly to line ranges modified in git diff (default: True)")
    parser.add_argument("--full-file", action="store_true", help="Force mutation testing across full file instead of diff-scoped lines")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # Default action if no flag is provided
    if not (args.proposal or args.red or args.green or args.mutation or args.status):
        parser.print_help()
        return 0

    results: Dict[str, Any] = {}
    exit_code = 0

    if args.status:
        results = get_status(args.receipt_path)
        if not args.json:
            print("\n======================================================================")
            print("   SOLO-SWARM VERIFICATION STATUS")
            print("======================================================================")
            print(f"  Protocol Reference : {results['standards_reference']}")
            print(f"  Red Receipt File   : {results['receipt_file']}")
            print(f"  Red Receipt Exists : {results['red_receipt_exists']}")
            if results["red_details"]:
                print(f"  Red Certified At   : {results['red_details'].get('certified_at', 'N/A')}")
                print(f"  Test Command       : {results['red_details'].get('test_cmd', 'N/A')}")
            print("======================================================================\n")
            return 0

    if args.proposal:
        debate_res = run_debate(proposal=args.proposal, rounds=args.rounds, judge_mode=args.judge_mode)
        results["debate"] = debate_res
        if not args.json:
            print("\n======================================================================")
            print("   WEAPON 4: PROVER-VERIFIER DEBATE & ADVERSARIAL EXTRACTION")
            print("======================================================================")
            print(f"  Proposal : {args.proposal}")
            print(f"  Winner   : {debate_res['winner'].upper()}")
            print(f"  Nash Eq. : {debate_res['nash_equilibrium_score']:.4f}")
            print(f"  Extracted Edge Cases : {debate_res['counter_examples_count']}")
            for sc in debate_res["structured_test_scenarios"]:
                print(f"    • [{sc['id']}]: {sc['description']}")
            print("======================================================================\n")

    if args.red:
        red_res = certify_red_phase(test_cmd=args.test_cmd, receipt_path=args.receipt_path)
        results["red_phase"] = red_res
        if not red_res.get("passed", False):
            exit_code = 1
        if not args.json:
            print("\n======================================================================")
            print("   WEAPON 1: RED PHASE CERTIFICATION (RED-FIRST INVARIANT)")
            print("======================================================================")
            print(f"  Status       : {red_res['status']}")
            print(f"  Test Command : {red_res.get('test_cmd', 'N/A')}")
            if red_res.get("passed", False):
                print(f"  Receipt File : {red_res.get('receipt_file')}")
                print(f"  Message      : {red_res.get('message')}")
            else:
                print(f"  Error        : {red_res.get('error')}")
            print("======================================================================\n")

    if args.green:
        green_res = certify_green_phase(test_cmd=args.test_cmd, receipt_path=args.receipt_path)
        results["green_phase"] = green_res
        if not green_res.get("passed", False):
            exit_code = 1
        if not args.json:
            print("\n======================================================================")
            print("   WEAPON 2: GREEN PHASE CERTIFICATION (BLUE IMPLEMENTER)")
            print("======================================================================")
            print(f"  Status       : {green_res['status']}")
            print(f"  Test Command : {green_res.get('test_cmd', 'N/A')}")
            if green_res.get("passed", False):
                print(f"  Message      : {green_res.get('message')}")
            else:
                print(f"  Error        : {green_res.get('error')}")
            print("======================================================================\n")

    if args.mutation:
        diff_only = not args.full_file
        mut_res = certify_mutation_phase(
            target_file=args.target,
            test_cmd=args.test_cmd,
            threshold=args.threshold,
            timeout=args.timeout,
            diff_only=diff_only,
        )
        results["mutation_phase"] = mut_res
        if not mut_res.get("passed", False):
            exit_code = 1
        if not args.json:
            print("\n======================================================================")
            print("   WEAPON 3: LIVE DYNAMIC MUTATION SENTINEL")
            print("======================================================================")
            print(f"  Status       : {mut_res['status']}")
            print(f"  Target File  : {mut_res.get('target_file', 'N/A')} {'(Auto-detected from git diff)' if mut_res.get('auto_targeted') else ''}")
            print(f"  Diff-Scoped  : {mut_res.get('diff_only', False)}")
            print(f"  Score        : {mut_res.get('mutation_score', 0.0):.1f}% (Required: >={mut_res.get('required_threshold', 80.0)}%)")
            print(f"  Mutants      : Total {mut_res.get('total_mutants', 0)} | Killed: {mut_res.get('killed', 0)} | Survived: {mut_res.get('survived', 0)}")
            print(f"  Message      : {mut_res.get('message')}")
            print("======================================================================\n")

    if args.json:
        print(json.dumps(results, indent=2))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
