#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tools/lint/lint_cache_prefix.py — Tier 1 Prefix Immutability Linter
-------------------------------------------------------------------
Verifies that AGENTS.md and agent rule files maintain strict Byte-Level Immutability
in their static prefix sections (Sections 0 through 1.1).

Checks:
  1. Prefix Token Volume: Ensures static prefix >= 1,024 tokens to trigger provider caching.
  2. Zero Volatility: Confirms no timestamps, session IDs, or non-deterministic macros exist in prefix.
  3. Stable Anchor: Verifies Section 0 through 1.1 delimiters exist and match expected structure.
"""

from __future__ import annotations

import argparse
import os
import sys

# Ensure repository root is on sys.path
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.core.cache_prefix_enforcer import CachePrefixEnforcer


def run_prefix_lint(target_file: str) -> tuple[bool, list[str]]:
    """Runs strict immutability linting against the target file."""
    issues = []
    if not os.path.exists(target_file):
        return False, [f"Target file does not exist: {target_file}"]

    with open(target_file, "r", encoding="utf-8") as f:
        content = f.read()

    partition = CachePrefixEnforcer.partition_prompt(content, auto_isolate_volatile=False)

    # Check 1: Token volume
    if partition["prefix_tokens"] < CachePrefixEnforcer.MIN_CACHE_TOKENS:
        issues.append(
            f"Prefix token count ({partition['prefix_tokens']}) is below minimum caching threshold "
            f"({CachePrefixEnforcer.MIN_CACHE_TOKENS} tokens). Context Caching will NOT be triggered."
        )

    # Check 2: Volatile elements
    volatiles = CachePrefixEnforcer.detect_volatile_elements(partition["prefix"])
    if volatiles:
        issues.append(
            f"Found {len(volatiles)} volatile/non-deterministic elements in static prefix: {volatiles}. "
            "These will cause 100% KV-Cache misses across turns!"
        )

    # Check 3: Section 0.2 Immutable Prefix statement
    if "0.2 PROMPT CACHING & IMMUTABLE PREFIX ARCHITECTURE" not in partition["prefix"]:
        issues.append("Missing Section 0.2 Immutable Prefix declaration in prompt header.")

    return len(issues) == 0, issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Tier 1 Prefix Immutability Linter")
    parser.add_argument("target", nargs="?", default=os.path.join(_REPO_ROOT, "AGENTS.md"), help="File to lint")
    args = parser.parse_args()

    passed, issues = run_prefix_lint(args.target)
    if passed:
        print(f"PASS: {os.path.basename(args.target)} strictly satisfies Tier 1 KV-Cache Prefix Invariant.")
        return 0

    print(f"FAIL: {os.path.basename(args.target)} violates Tier 1 KV-Cache Prefix Invariants:", file=sys.stderr)
    for issue in issues:
        print(f"  - [X] {issue}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
