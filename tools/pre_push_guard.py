#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Pre-Push Quality & Anti-Hallucination Guard (Multi-Session Audit)
---------------------------------------------------------------
Automatically intercepts git push events to perform multi-stage verification:
  Stage 1: Multi-Session Transcript Audit (Audits the 3 most recent Antigravity sessions).
  Stage 2: Adversarial Injection & Prompt Security Scan across recent session logs.
  Stage 3: Repository Definition-of-Done Quality Gates (Zero BOM, Credential Leaks).
  Stage 4: Automated Regression Test Execution (Pytest Exit Code 0).

Usage:
  python tools/pre_push_guard.py [--sessions 3] [--strict] [--install-hook] [--skip-tests]
"""

import os
import sys
import glob
import subprocess
import argparse
from typing import Dict, Any, List, Tuple, Optional

# Enforce UTF-8 stdout encoding
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'):
        try:
            stream.reconfigure(encoding='utf-8', line_buffering=True)
        except Exception:
            pass

try:
    from tools.ai_eval_sentinel import audit_agent_transcript, detect_adversarial_injection
    from tools.verify_all import gate_1_bom_check, gate_6_credential_security
except ImportError:
    # Handle direct script execution vs package import
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tools.ai_eval_sentinel import audit_agent_transcript, detect_adversarial_injection
    from tools.verify_all import gate_1_bom_check, gate_6_credential_security


def resolve_brain_directory() -> str:
    """Locate the Antigravity brain storage directory cross-platform."""
    candidates = [
        os.path.expanduser("~/.gemini/antigravity/brain"),
        os.path.join(os.environ.get("USERPROFILE", ""), ".gemini", "antigravity", "brain"),
        os.path.join(os.environ.get("HOME", ""), ".gemini", "antigravity", "brain"),
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate) and os.path.isdir(candidate):
            return os.path.abspath(candidate)
    return candidates[0]


def find_recent_sessions(limit: int = 3, brain_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """Discover the N most recent Antigravity conversation sessions containing transcripts."""
    target_dir = brain_dir or resolve_brain_directory()
    if not os.path.exists(target_dir):
        return []

    sessions = []
    for item in glob.glob(os.path.join(target_dir, "*")):
        if not os.path.isdir(item):
            continue
        transcript_path = os.path.join(item, ".system_generated", "logs", "transcript.jsonl")
        if os.path.exists(transcript_path) and os.path.getsize(transcript_path) > 0:
            mtime = os.path.getmtime(transcript_path)
            sessions.append({
                "conversation_id": os.path.basename(item),
                "directory": item,
                "transcript_path": transcript_path,
                "modified_time": mtime,
            })

    # Sort descending by modification time
    sessions.sort(key=lambda s: s["modified_time"], reverse=True)
    return sessions[:limit]


def audit_recent_sessions(
    sessions: List[Dict[str, Any]],
    strict: bool = False,
    min_faithfulness: float = 20.0
) -> Dict[str, Any]:
    """Audit the selected sessions for hallucinations, prompt injections, and evidence grounding."""
    results = []
    passed = True
    total_injections = 0

    for s in sessions:
        audit_res = audit_agent_transcript(s["transcript_path"])
        f_rate = audit_res.get("overall_faithfulness_rate", 0.0)
        turns = audit_res.get("total_conversation_turns", 0)

        # Check for adversarial prompt injection in user turns
        injections_found = 0
        for turn in audit_res.get("turns_evaluation", []):
            prompt = turn.get("query_summary", "")
            is_injected, _ = detect_adversarial_injection(prompt)
            if is_injected:
                injections_found += 1

        total_injections += injections_found
        session_passed = True
        reasons = []

        if injections_found > 0:
            session_passed = False
            reasons.append(f"{injections_found} adversarial prompt injection(s) detected")

        if strict and f_rate < min_faithfulness:
            session_passed = False
            reasons.append(f"Faithfulness rate {f_rate:.1f}% below strict threshold {min_faithfulness}%")

        if not session_passed:
            passed = False

        results.append({
            "conversation_id": s["conversation_id"],
            "turns": turns,
            "faithfulness_rate": f_rate,
            "injections": injections_found,
            "passed": session_passed,
            "reasons": reasons,
            "transcript_path": s["transcript_path"],
        })

    return {
        "audited_count": len(sessions),
        "all_passed": passed,
        "total_injections": total_injections,
        "sessions": results,
    }


def verify_quality_gates(repo_root: Optional[str] = None) -> Tuple[bool, List[str]]:
    """Execute Gate 1 (Zero BOM) and Gate 6 (Secret Scan) using canonical Synapse DoD verifiers."""
    root = repo_root or os.getcwd()
    issues = []

    try:
        g1_pass = gate_1_bom_check(root)
        if not g1_pass:
            issues.append("Gate 1 (Zero BOM) FAILED: Found BOM or encoding defects in repository.")
    except Exception as e:
        issues.append(f"Gate 1 check error: {e}")

    try:
        g6_pass = gate_6_credential_security(root, mode="hub")
        if not g6_pass:
            issues.append("Gate 6 (Credential Security) FAILED: Potential plaintext secrets detected.")
    except Exception as e:
        issues.append(f"Gate 6 check error: {e}")

    return len(issues) == 0, issues


def run_regression_tests(repo_root: Optional[str] = None) -> Tuple[bool, str]:
    """Execute pytest regression test suite."""
    root = repo_root or os.getcwd()
    cmd = [sys.executable, "-m", "pytest", "tests/test_cvss_calculator.py",
           "tests/test_asvs_auditor.py", "tests/test_vpat_exporter.py",
           "tests/test_regulatory_compliance.py", "tests/test_cldr_l10n_verifier.py",
           "tests/test_ai_eval_sentinel.py", "tests/test_etl_data_reconciler.py",
           "tests/test_tmmi_auditor.py", "tests/test_pre_push_guard.py", "-q"]
    try:
        proc = subprocess.run(
            cmd,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return proc.returncode == 0, proc.stdout or proc.stderr
    except Exception as e:
        return False, str(e)


def install_git_pre_push_hook(repo_root: Optional[str] = None, session_count: int = 3) -> Tuple[bool, str]:
    """Install the pre-push hook script into .git/hooks/pre-push."""
    root = repo_root or os.getcwd()
    hooks_dir = os.path.join(root, ".git", "hooks")
    if not os.path.exists(hooks_dir):
        return False, f"Not a git repository or .git/hooks missing at: {hooks_dir}"

    hook_path = os.path.join(hooks_dir, "pre-push")
    hook_content = f"""#!/bin/sh
# Synapse Hub Automated Pre-Push Guard (Multi-Session Audit)
# Auto-generated by tools/pre_push_guard.py

echo "=========================================================================="
echo "  🛡️ SYNAPSE HUB — PRE-PUSH QUALITY GATE & AUDIT ({session_count} RECENT SESSIONS)"
echo "=========================================================================="

python tools/pre_push_guard.py --sessions {session_count}
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ [PRE-PUSH REJECTED] Automated verification failed! Push blocked."
    echo "   Please review the errors above and fix before pushing."
    exit 1
fi

echo ""
echo "✅ [PRE-PUSH APPROVED] All {session_count} sessions audited & Quality Gates passed!"
exit 0
"""
    try:
        with open(hook_path, "w", encoding="utf-8", newline="\n") as fp:
            fp.write(hook_content)

        # On POSIX / Git Bash, make it executable
        try:
            os.chmod(hook_path, 0o755)
        except Exception:
            pass

        return True, hook_path
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description="Synapse Hub Pre-Push Multi-Session Audit & Quality Gate")
    parser.add_argument("--sessions", "-n", type=int, default=3, help="Number of recent Antigravity sessions to audit (default: 3)")
    parser.add_argument("--strict", action="store_true", help="Enforce strict faithfulness score thresholds")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running pytest regression suite")
    parser.add_argument("--install-hook", action="store_true", help="Install this guard as the git pre-push hook")
    args = parser.parse_args()

    if args.install_hook:
        ok, msg = install_git_pre_push_hook(session_count=args.sessions)
        if ok:
            print(f"✅ Git pre-push hook successfully installed at: {msg}")
            sys.exit(0)
        else:
            print(f"❌ Failed to install git pre-push hook: {msg}", file=sys.stderr)
            sys.exit(1)

    print("=" * 74)
    print("  🛡️ SYNAPSE HUB — PRE-PUSH MULTI-SESSION AUDIT & QUALITY GATE")
    print("=" * 74)

    # Stage 1 & 2: Audit Recent Sessions
    print(f"\n[Stage 1/3] Discovering & Auditing {args.sessions} Most Recent Sessions...")
    sessions = find_recent_sessions(limit=args.sessions)
    if not sessions:
        print("  ⚠️ No Antigravity conversation sessions found. Proceeding with quality gates.")
    else:
        print(f"  Found {len(sessions)} session(s):")
        audit_res = audit_recent_sessions(sessions, strict=args.strict)
        for idx, s in enumerate(audit_res["sessions"], 1):
            short_id = s["conversation_id"][:12] + "..."
            status = "✅ PASS" if s["passed"] else "⚠️ FLAGGED"
            print(f"  {idx}. Session [{short_id}] | Turns: {s['turns']} | Faithfulness: {s['faithfulness_rate']:.1f}% | Injections: {s['injections']} | {status}")
            if s["reasons"]:
                for r in s["reasons"]:
                    print(f"     -> {r}")

        if not audit_res["all_passed"]:
            print(f"\n❌ [PRE-PUSH REJECTED] Session audit failed: {audit_res['total_injections']} injection(s) detected.", file=sys.stderr)
            sys.exit(1)

    # Stage 3: Quality Gates (Zero BOM, Credentials)
    print("\n[Stage 2/3] Verifying Definition-of-Done Quality Gates...")
    qg_ok, qg_issues = verify_quality_gates()
    if not qg_ok:
        for issue in qg_issues:
            print(f"  ❌ {issue}", file=sys.stderr)
        print("\n❌ [PRE-PUSH REJECTED] Definition-of-Done Quality Gate violation.", file=sys.stderr)
        sys.exit(1)
    print("  ✅ Gate 1 (Zero BOM): PASS")
    print("  ✅ Gate 6 (Credential Security): PASS")

    # Stage 4: Automated Regression Tests
    if not args.skip_tests:
        print("\n[Stage 3/3] Running Automated Regression Test Suite...")
        tests_ok, test_out = run_regression_tests()
        if not tests_ok:
            print(f"  ❌ Regression tests failed:\n{test_out}", file=sys.stderr)
            print("\n❌ [PRE-PUSH REJECTED] Test failures detected.", file=sys.stderr)
            sys.exit(1)
        print(f"  ✅ Regression Suite: PASS ({test_out.strip()})")
    else:
        print("\n[Stage 3/3] Regression Test Suite: SKIPPED (--skip-tests)")

    print("\n" + "=" * 74)
    print(f"  ✅ [PRE-PUSH APPROVED] All {len(sessions)} sessions & Quality Gates certified!")
    print("=" * 74)
    sys.exit(0)


if __name__ == "__main__":
    main()
