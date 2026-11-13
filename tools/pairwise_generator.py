#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/pairwise_generator.py — Pairwise (2-Way) Combinatorial Test Case Generator
Inspired by Composio / pypict combinatorial testing patterns.
Generates minimal test execution matrices covering 100% of 2-way parameter pairs,
reducing test case bloat by 80-90% while guaranteeing pairwise boundary coverage.
100% UTF-8 No BOM.
"""

import sys
import json
import argparse
from typing import Dict, List, Any, Set, Tuple

# Enforce UTF-8 stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def generate_all_pairs(parameters: Dict[str, List[Any]]) -> Set[Tuple[Tuple[str, Any], Tuple[str, Any]]]:
    """Generates all 2-way parameter value pairs."""
    param_keys = sorted(parameters.keys())
    all_pairs: Set[Tuple[Tuple[str, Any], Tuple[str, Any]]] = set()

    for i in range(len(param_keys)):
        for j in range(i + 1, len(param_keys)):
            p1 = param_keys[i]
            p2 = param_keys[j]
            for v1 in parameters[p1]:
                for v2 in parameters[p2]:
                    # Canonical ordered pair
                    pair = ((p1, v1), (p2, v2))
                    all_pairs.add(pair)
    return all_pairs

def score_candidate(candidate: Dict[str, Any], uncovered_pairs: Set[Tuple[Tuple[str, Any], Tuple[str, Any]]]) -> int:
    """Calculates how many uncovered pairs a complete candidate test case satisfies."""
    keys = sorted(candidate.keys())
    count = 0
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            p1, p2 = keys[i], keys[j]
            pair = ((p1, candidate[p1]), (p2, candidate[p2]))
            if pair in uncovered_pairs:
                count += 1
    return count

def generate_pairwise(parameters: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    """
    Greedy Pairwise (IPOG-inspired) test suite generation.
    Guarantees 100% pairwise coverage of parameter combinations.
    """
    if not parameters or any(len(v) == 0 for v in parameters.values()):
        return []

    param_keys = sorted(parameters.keys())
    if len(param_keys) == 1:
        # Single parameter: return each value
        p = param_keys[0]
        return [{p: v} for v in parameters[p]]

    uncovered_pairs = generate_all_pairs(parameters)
    total_pairs = len(uncovered_pairs)
    test_cases: List[Dict[str, Any]] = []

    # Sort parameters by domain size descending for faster coverage
    sorted_keys = sorted(param_keys, key=lambda k: len(parameters[k]), reverse=True)

    while uncovered_pairs:
        # Pick the pair with highest priority
        target_pair = next(iter(uncovered_pairs))
        p1, v1 = target_pair[0]
        p2, v2 = target_pair[1]

        # Initialize candidate with this pair
        candidate: Dict[str, Any] = {p1: v1, p2: v2}

        # Greedily assign remaining parameters to maximize pair coverage
        for key in sorted_keys:
            if key in candidate:
                continue

            best_val = parameters[key][0]
            best_score = -1

            for val in parameters[key]:
                temp_cand = dict(candidate)
                temp_cand[key] = val
                # Count pairs this assignment would cover with already-fixed params
                score = 0
                for fixed_key, fixed_val in candidate.items():
                    p_a, v_a = (key, val) if key < fixed_key else (fixed_key, fixed_val)
                    p_b, v_b = (fixed_key, fixed_val) if key < fixed_key else (key, val)
                    if ((p_a, v_a), (p_b, v_b)) in uncovered_pairs:
                        score += 1
                if score > best_score:
                    best_score = score
                    best_val = val

            candidate[key] = best_val

        # Ensure all keys are populated
        for key in param_keys:
            if key not in candidate:
                candidate[key] = parameters[key][0]

        # Remove covered pairs from uncovered set
        for i in range(len(param_keys)):
            for j in range(i + 1, len(param_keys)):
                k1, k2 = param_keys[i], param_keys[j]
                pair = ((k1, candidate[k1]), (k2, candidate[k2]))
                uncovered_pairs.discard(pair)

        test_cases.append(candidate)

    return test_cases

def main():
    parser = argparse.ArgumentParser(description="Generate pairwise (2-way) combinatorial test suites.")
    parser.add_argument("--params", "-p", help="JSON string or file path containing parameter domains.")
    parser.add_argument("--json", action="store_true", help="Output JSON format.")
    args = parser.parse_args()

    if not args.params:
        # Default sample parameters
        sample_params = {
            "browser": ["chromium", "firefox", "webkit"],
            "viewport": ["desktop_1920x1080", "mobile_390x844"],
            "user_role": ["admin", "editor", "viewer"],
            "auth_state": ["logged_in", "anonymous"]
        }
        params = sample_params
    else:
        try:
            if args.params.startswith("{"):
                params = json.loads(args.params)
            else:
                with open(args.params, "r", encoding="utf-8") as f:
                    params = json.load(f)
        except Exception as e:
            print(f"Error parsing parameters: {e}", file=sys.stderr)
            sys.exit(1)

    all_pairs = generate_all_pairs(params)
    cases = generate_pairwise(params)
    full_combinations = 1 if params else 0
    for k, v in params.items():
        full_combinations *= len(v)

    reduction = round((1.0 - len(cases) / full_combinations) * 100, 1) if full_combinations > 0 else 0.0

    if args.json:
        print(json.dumps({
            "total_full_permutations": full_combinations,
            "pairwise_test_count": len(cases),
            "total_2way_pairs": len(all_pairs),
            "reduction_pct": reduction,
            "test_cases": cases
        }, indent=2))
    else:
        print(f"[PAIRWISE GENERATOR] Parameters: {len(params)} | Total Permutations: {full_combinations}")
        print(f"  Optimized Pairwise Cases: {len(cases)} (Covering {len(all_pairs)} 2-way interactions)")
        print(f"  Reduction: {reduction}% test case reduction!")
        print("\nGenerated Test Matrix:")
        for idx, tc in enumerate(cases, 1):
            formatted = ", ".join(f"{k}={v}" for k, v in tc.items())
            print(f"  TC-{idx:02d}: {formatted}")

if __name__ == "__main__":
    main()
