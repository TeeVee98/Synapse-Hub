#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/core/token_estimator.py — Unified Polyglot BPE Token Estimator
-------------------------------------------------------------------
Provides deterministic, calibrated token counting across codebases, markdown rules,
and system prompts. Standardizes token estimation across rules_router, distill_log,
benchmark_swarm_context, and count_tokens.

Key Capabilities:
  1. High-accuracy fallback heuristic:
     - English / ASCII code: ~3.85 characters/token (calibrated against cl100k_base / o200k_base).
     - Non-ASCII / Vietnamese diacritics / Unicode: ~1.8 characters/token.
  2. Optional native BPE tokenization if tiktoken is available in runtime.
  3. Structured token breakdown (Rules, Catalog Metadata, Full Skill Bodies, System Prefix).
"""

from __future__ import annotations

import os
import re
import sys
from typing import Any, Dict, List, Optional

# Attempt native BPE import if available
_TIKTOKEN_ENCODER = None
try:
    import tiktoken  # type: ignore

    try:
        _TIKTOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")
    except Exception:
        _TIKTOKEN_ENCODER = None
except ImportError:
    _TIKTOKEN_ENCODER = None


def count_tokens(text: str, model_hint: str = "cl100k") -> int:
    """
    Counts or estimates tokens for arbitrary polyglot text or code.
    If tiktoken is installed, calculates exact cl100k_base tokens.
    Otherwise, applies calibrated polyglot heuristic:
      - ASCII / Latin / Code: ~3.85 chars/token.
      - Non-ASCII / Diacritics: ~1.8 chars/token.
    """
    if not text:
        return 0

    if _TIKTOKEN_ENCODER is not None:
        try:
            return len(_TIKTOKEN_ENCODER.encode(text, disallowed_special=()))
        except Exception as err:
            _ = err

    # Heuristic calibrated against standard LLM subword tokenizers
    non_ascii_chars = len([c for c in text if ord(c) > 127])
    ascii_chars = len(text) - non_ascii_chars

    # Token density weights
    ascii_tokens = ascii_chars / 3.85
    unicode_tokens = non_ascii_chars / 1.80

    total_est = int(ascii_tokens + unicode_tokens)
    # Lower bound: words + punctuation count to prevent underestimation on short texts
    word_tokens = len(re.findall(r"\w+|[^\w\s]", text, re.UNICODE))

    return max(1, max(total_est, int(word_tokens * 1.05)))


def count_file_tokens(file_path: str) -> int:
    """Reads a file from disk and returns its exact/estimated token count."""
    if not os.path.isfile(file_path):
        return 0
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return count_tokens(content)
    except OSError:
        return 0


def calculate_hydration_payload(
    repo_root: str,
    rules: List[str],
    skills: List[str],
) -> Dict[str, Any]:
    """
    Computes precise dual-tier token metrics for a set of selected rules and skills:
      1. summary: Catalog metadata only (name + summary description ~120 tokens/skill).
      2. full: Complete SKILL.md body hydrated into context.
    """
    rules_dir = os.path.join(repo_root, ".agents", "rules")
    skills_root = os.path.join(repo_root, ".agents", "skills")

    rule_tokens = 0
    rule_bytes = 0
    for r in rules:
        p = os.path.join(rules_dir, r)
        if os.path.isfile(p):
            rule_tokens += count_file_tokens(p)
            rule_bytes += os.path.getsize(p)
        else:
            rule_tokens += 500  # Default estimate for virtual rule
            rule_bytes += 2000

    catalog_skill_tokens = len(skills) * 120
    full_skill_tokens = 0
    full_skill_bytes = 0

    # Locate each skill directory in .agents/skills
    for skill_name in skills:
        skill_file = _find_skill_file(skills_root, skill_name)
        if skill_file and os.path.isfile(skill_file):
            tokens = count_file_tokens(skill_file)
            size = os.path.getsize(skill_file)
            full_skill_tokens += tokens
            full_skill_bytes += size
        else:
            # Fallback average skill size (~1,800 tokens, 7.5 KB)
            full_skill_tokens += 1800
            full_skill_bytes += 7500

    return {
        "rule_tokens": rule_tokens,
        "rule_bytes": rule_bytes,
        "skill_catalog_tokens": catalog_skill_tokens,
        "skill_full_body_tokens": full_skill_tokens,
        "skill_full_bytes": full_skill_bytes,
        "total_summary_tokens": rule_tokens + catalog_skill_tokens,
        "total_hydrated_tokens": rule_tokens + full_skill_tokens,
        "total_hydrated_bytes": rule_bytes + full_skill_bytes,
    }


def _find_skill_file(skills_root: str, skill_name: str) -> Optional[str]:
    """Finds SKILL.md for a given skill name across tiered category folders."""
    if not os.path.isdir(skills_root):
        return None
    for root, dirs, files in os.walk(skills_root):
        if os.path.basename(root) == skill_name and "SKILL.md" in files:
            return os.path.join(root, "SKILL.md")
    return None
