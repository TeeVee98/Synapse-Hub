#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
tools/runaway_stopper.py — Agent Runaway & Token Loop Sentinel (Stub / Re-export)
Inspired by Garry Tan's gstack (R70/R91 runaway stopper) adapted for Synapse Hub.
Prevents runaway subagent threads, context window blowout, and infinite loops.
Re-exports RunawaySentinel and DEFAULT_THRESHOLDS from tools.core.circuit_breaker.
100% UTF-8 No BOM.
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


import sys
import os
import json
import argparse

__all__ = ["DEFAULT_THRESHOLDS", "RunawaySentinel", "main"]

# Enforce UTF-8 stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Safe import from tools.core.circuit_breaker
try:
    from tools.core.circuit_breaker import DEFAULT_THRESHOLDS, RunawaySentinel
except ImportError:
    try:
        from core.circuit_breaker import DEFAULT_THRESHOLDS, RunawaySentinel
    except ImportError:
        _parent_dir = os.path.dirname(os.path.abspath(__file__))
        _repo_root = os.path.dirname(_parent_dir)
        if _repo_root not in sys.path:
            sys.path.insert(0, _repo_root)
        if _parent_dir not in sys.path:
            sys.path.insert(0, _parent_dir)
        from tools.core.circuit_breaker import DEFAULT_THRESHOLDS, RunawaySentinel


def main():
    parser = argparse.ArgumentParser(description="Evaluate agent sessions for runaway token consumption and loops.")
    parser.add_argument("--transcript", "-t", help="Path to JSON file containing turn list.")
    parser.add_argument("--turns", type=int, default=0, help="Direct turn count to evaluate.")
    parser.add_argument("--tokens", type=int, default=0, help="Direct token estimate to evaluate.")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format.")
    args = parser.parse_args()

    sentinel = RunawaySentinel()

    if args.transcript and os.path.exists(args.transcript):
        with open(args.transcript, "r", encoding="utf-8") as f:
            turns = json.load(f)
    elif args.turns > 0 or args.tokens > 0:
        if args.turns == 0 and args.tokens > 0:
            turns = [{"turn_index": 0, "tokens_est": args.tokens}]
        else:
            turn_count = max(1, args.turns)
            per_turn_tokens = args.tokens // turn_count
            turns = [{"turn_index": i, "tokens_est": per_turn_tokens} for i in range(turn_count)]
    else:
        # Default mock evaluation
        turns = []

    result = sentinel.evaluate_transcript(turns)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"[RUNAWAY STOPPER] Verdict: {result['verdict']}")
        print(f"  Turns Evaluated: {result['turn_count']}")
        print(f"  Estimated Tokens: {result['total_tokens_est']:,}")
        if result["flags"]:
            print("  Flags Detected:")
            for flag in result["flags"]:
                print(f"    - [{flag['severity']}] {flag['type']}: {flag['message']}")
        else:
            print("  Status: Clean - zero loops or budget overruns detected.")

    if result["is_runaway"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
