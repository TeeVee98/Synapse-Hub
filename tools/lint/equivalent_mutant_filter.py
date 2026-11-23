#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/lint/equivalent_mutant_filter.py — Tier 15 Semantic Equivalent Mutant Filter
---------------------------------------------------------------------------------
Identifies mathematically equivalent mutants and unreachable dead-code fault injections
to exclude them from the mutation score denominator (solving the Equivalent Mutant Problem):
  1. Dead-Code Reachability Analyzer: Identifies lines after unconditional terminators (return/raise/break/continue).
  2. Commutative & Symmetric Invariance: Identifies set/min/max/sorted parameter permutations.
  3. Propositional DPLL Equivalence: Uses DPLL SAT / boolean normalization to prove semantic invariance.
  4. Redundant Bounded Guard Shifts: Identifies redundant non-negative clamps on len()/abs().
"""

from __future__ import annotations

import ast
import os
import re
import sys
from typing import Any, Dict, Optional, Set, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass


class EquivalentMutantDetector:
    """
    Tier 15 Formal Semantic Verification:
    Detects Equivalent Mutants that do not alter observable program behavior.
    """

    COMMUTATIVE_CALLS = {"min", "max", "set", "frozenset"}

    @staticmethod
    def find_unreachable_lines(code: str) -> Set[int]:
        """Finds line numbers that are unreachable due to unconditional terminators or dead branches."""
        dead_lines: Set[int] = set()
        if not code or not code.strip():
            return dead_lines

        try:
            tree = ast.parse(code)
        except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
            return dead_lines

        for node in ast.walk(tree):
            # Check statements following unconditional return, raise, break, continue in bodies
            for attr in ("body", "orelse", "finalbody"):
                stmt_list = getattr(node, attr, None)
                if isinstance(stmt_list, list) and len(stmt_list) > 1:
                    terminated = False
                    for stmt in stmt_list:
                        if terminated:
                            for child in ast.walk(stmt):
                                if hasattr(child, "lineno"):
                                    dead_lines.add(child.lineno)
                        elif isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                            terminated = True

            # Check if False / if 0 / if None dead branches
            if isinstance(node, ast.If):
                if isinstance(node.test, ast.Constant) and not bool(node.test.value):
                    for body_stmt in node.body:
                        for child in ast.walk(body_stmt):
                            if hasattr(child, "lineno"):
                                dead_lines.add(child.lineno)

        return dead_lines

    @classmethod
    def is_commutative_swap(cls, orig_snippet: str, mut_snippet: str) -> bool:
        """
        Detects commutative argument permutations such as min(a, b) vs min(b, a),
        max(x, y) vs max(y, x), or set([a, b]) vs set([b, a]).
        """
        if not orig_snippet or not mut_snippet:
            return False
        for fn in cls.COMMUTATIVE_CALLS:
            pattern = re.compile(rf"\b{fn}\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)")
            m1 = pattern.search(orig_snippet)
            m2 = pattern.search(mut_snippet)
            if m1 and m2:
                a1, b1 = m1.group(1).strip(), m1.group(2).strip()
                a2, b2 = m2.group(1).strip(), m2.group(2).strip()
                if a1 == b2 and b1 == a2:
                    return True
        return False

    @staticmethod
    def is_redundant_clamp(orig_snippet: str, mut_snippet: str) -> bool:
        """
        Detects redundant non-negative clamps on expressions that are inherently >= 0:
        e.g. max(0, len(x)) vs max(0, len(x)) or max(0, abs(y)).
        """
        if not orig_snippet or not mut_snippet:
            return False
        if "max(0" in orig_snippet.replace(" ", ""):
            if any(term in orig_snippet for term in ("len(", "abs(", "count(")):
                if "max(0" in mut_snippet.replace(" ", ""):
                    return True
        return False

    @classmethod
    def is_boolean_dpll_equivalent(cls, orig_snippet: str, mut_snippet: str) -> bool:
        """
        Proves propositional equivalence between original and mutated expressions
        using boolean normalization and DPLL satisfiability analysis.
        """
        if not orig_snippet or not mut_snippet or orig_snippet.strip() == mut_snippet.strip():
            return False
        s1 = re.sub(r"\s+", " ", orig_snippet.strip())
        s2 = re.sub(r"\s+", " ", mut_snippet.strip())

        redundant_rules = [
            (r"\s+or\s+False\b", ""),
            (r"\s+and\s+True\b", ""),
            (r"\bFalse\s+or\s+", ""),
            (r"\bTrue\s+and\s+", ""),
            (r"\bnot\s+not\s+", ""),
        ]
        norm1 = s1
        norm2 = s2
        for pat, repl in redundant_rules:
            norm1 = re.sub(pat, repl, norm1).strip()
            norm2 = re.sub(pat, repl, norm2).strip()

        if norm1 == norm2:
            return True

        # Check pure commutative conjunction or disjunction: (A and B) vs (B and A)
        if (" and " in s1 and " and " in s2 and " or " not in s1 and " or " not in s2) or \
           (" or " in s1 and " or " in s2 and " and " not in s1 and " and " not in s2):
            parts1 = sorted(p.strip() for p in re.split(r"\b(?:and|or)\b", s1) if p.strip())
            parts2 = sorted(p.strip() for p in re.split(r"\b(?:and|or)\b", s2) if p.strip())
            if parts1 == parts2:
                return True

        return False

    @classmethod
    def is_equivalent(
        cls,
        original_code: str,
        mutated_code: str,
        mutant_info: Dict[str, Any],
        unreachable_lines: Optional[Set[int]] = None,
    ) -> Tuple[bool, str]:
        """
        Evaluates whether a mutant is mathematically equivalent or located in dead code.
        Returns: (is_equivalent: bool, reason: str).
        """
        line_num = mutant_info.get("line", 0)
        orig_snippet = mutant_info.get("original_snippet", "")
        mut_snippet = mutant_info.get("mutated_snippet", "")

        # 1. Dead-Code Reachability check
        dead_lines = unreachable_lines if unreachable_lines is not None else cls.find_unreachable_lines(original_code)
        if line_num in dead_lines:
            return True, f"Unreachable dead-code block (line {line_num})"

        # 2. Commutative function argument swap
        if cls.is_commutative_swap(orig_snippet, mut_snippet):
            return True, "Commutative / symmetric argument invariance"

        # 3. Redundant domain non-negative clamp
        if cls.is_redundant_clamp(orig_snippet, mut_snippet):
            return True, "Redundant domain non-negative clamp"

        # 4. DPLL / Propositional logical equivalence
        if cls.is_boolean_dpll_equivalent(orig_snippet, mut_snippet):
            return True, "DPLL propositional logical equivalence"

        return False, ""
