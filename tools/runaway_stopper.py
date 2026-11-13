#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/runaway_stopper.py — Agent Runaway & Token Loop Sentinel
Inspired by Garry Tan's gstack (R70/R91 runaway stopper) adapted for Synapse Hub.
Prevents runaway subagent threads, context window blowout, and infinite loops.
100% UTF-8 No BOM.
"""

import sys
import os
import json
import argparse
from typing import Dict, List, Any, Optional

# Enforce UTF-8 stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEFAULT_THRESHOLDS = {
    "max_turns": 30,
    "warn_turns": 20,
    "max_tokens": 150000,
    "warn_tokens": 100000,
    "max_repeated_calls": 3,
    "empty_turn_threshold": 4,
}

class RunawaySentinel:
    def __init__(self, thresholds: Optional[Dict[str, int]] = None):
        self.thresholds = dict(DEFAULT_THRESHOLDS)
        if thresholds:
            self.thresholds.update(thresholds)

    def evaluate_transcript(self, turns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluates a list of turn records:
        turn = {
            "turn_index": int,
            "tool_name": str,
            "command": str,
            "tokens_est": int,
            "has_error": bool,
            "output_length": int
        }
        """
        turn_count = len(turns)
        total_tokens = sum(t.get("tokens_est", 0) for t in turns)
        flags = []
        verdict = "OK"

        # 1. Turn budget check
        if turn_count >= self.thresholds["max_turns"]:
            flags.append({
                "severity": "CRITICAL",
                "type": "TURN_LIMIT_EXCEEDED",
                "message": f"Turn count ({turn_count}) exceeded maximum threshold ({self.thresholds['max_turns']})."
            })
            verdict = "STOP"
        elif turn_count >= self.thresholds["warn_turns"]:
            flags.append({
                "severity": "WARNING",
                "type": "TURN_LIMIT_WARNING",
                "message": f"Turn count ({turn_count}) approached warning threshold ({self.thresholds['warn_turns']})."
            })
            if verdict == "OK":
                verdict = "WARN"

        # 2. Token budget check
        if total_tokens >= self.thresholds["max_tokens"]:
            flags.append({
                "severity": "CRITICAL",
                "type": "TOKEN_BUDGET_EXCEEDED",
                "message": f"Estimated token usage ({total_tokens:,}) exceeded budget ({self.thresholds['max_tokens']:,})."
            })
            verdict = "STOP"
        elif total_tokens >= self.thresholds["warn_tokens"]:
            flags.append({
                "severity": "WARNING",
                "type": "TOKEN_BUDGET_WARNING",
                "message": f"Estimated token usage ({total_tokens:,}) reached warning limit ({self.thresholds['warn_tokens']:,})."
            })
            if verdict == "OK":
                verdict = "WARN"

        # 3. Repeated identical tool call loop detection
        recent_commands = [
            (t.get("command") or t.get("tool_name") or t.get("tool") or t.get("name") or "")
            for t in turns
            if (t.get("command") or t.get("tool_name") or t.get("tool") or t.get("name"))
        ]
        if len(recent_commands) >= self.thresholds["max_repeated_calls"]:
            last_cmd = recent_commands[-1]
            repeat_count = 1
            for cmd in reversed(recent_commands[:-1]):
                if cmd == last_cmd and last_cmd:
                    repeat_count += 1
                else:
                    break
            if repeat_count >= self.thresholds["max_repeated_calls"]:
                flags.append({
                    "severity": "CRITICAL",
                    "type": "TOOL_LOOP_DETECTED",
                    "message": f"Command repeated {repeat_count} consecutive times: '{last_cmd[:60]}...'"
                })
                verdict = "STOP"

        # 4. Consecutive empty turns detection
        empty_turns = 0
        for t in reversed(turns):
            if t.get("output_length", 1) == 0 and not t.get("tool_name"):
                empty_turns += 1
            else:
                break
        if empty_turns >= self.thresholds["empty_turn_threshold"]:
            flags.append({
                "severity": "CRITICAL",
                "type": "EMPTY_TURNS_LOOP",
                "message": f"Detected {empty_turns} consecutive empty turns without progress."
            })
            verdict = "STOP"

        return {
            "verdict": verdict,
            "turn_count": turn_count,
            "total_tokens_est": total_tokens,
            "flags": flags,
            "is_runaway": verdict == "STOP",
        }

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
