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
  4. Real dynamic baseline calculation enumerating 100% of skills & rules without static estimates.
"""

from __future__ import annotations

import glob
import json
import os
import re
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

_SKILLS_MANIFEST_CACHE: Optional[Dict[str, Dict[str, Any]]] = None


def get_estimator_info() -> Dict[str, Any]:
    """Returns active tokenizer engine metadata, exactness status, and model hint."""
    return {
        "engine": "cl100k_base" if _TIKTOKEN_ENCODER is not None else "heuristic_polyglot",
        "is_exact": _TIKTOKEN_ENCODER is not None,
        "encoding": "cl100k_base",
        "calibrated_ratios": {
            "ascii_chars_per_token": 3.85,
            "non_ascii_chars_per_token": 1.80,
        },
    }


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


def _get_skills_manifest(repo_root: str) -> Dict[str, Dict[str, Any]]:
    """Loads and caches skills_manifest.json mapping skill_id to metadata."""
    global _SKILLS_MANIFEST_CACHE
    if _SKILLS_MANIFEST_CACHE is not None:
        return _SKILLS_MANIFEST_CACHE

    manifest_path = os.path.join(repo_root, "skills_manifest.json")
    _SKILLS_MANIFEST_CACHE = {}
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for s in data.get("skills", []):
                    sid = s.get("id")
                    if sid:
                        _SKILLS_MANIFEST_CACHE[sid] = s
        except (OSError, json.JSONDecodeError) as err:
            _ = err
    return _SKILLS_MANIFEST_CACHE


def serialize_skill_summary(skill_name: str, meta: Optional[Dict[str, Any]] = None) -> str:
    """Formats a concise catalog summary line for a skill."""
    if meta:
        name = meta.get("name", skill_name)
        domain = meta.get("domain", "")
        desc = meta.get("description") or meta.get("summary", "")
        domain_str = f" [{domain}]" if domain else ""
        return f"- {name} ({skill_name}){domain_str}: {desc}"
    return f"- {skill_name}: Enterprise QA Automation Skill"


def calculate_hydration_payload(
    repo_root: str,
    rules: List[str],
    skills: List[str],
) -> Dict[str, Any]:
    """
    Computes precise dual-tier token metrics for a set of selected rules and skills:
      1. summary: Catalog metadata only (serialized name + domain + description).
      2. full: Complete SKILL.md body hydrated into context.
    """
    rules_dir = os.path.join(repo_root, ".agents", "rules")
    skills_root = os.path.join(repo_root, ".agents", "skills")
    manifest = _get_skills_manifest(repo_root)

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

    catalog_lines = []
    full_skill_tokens = 0
    full_skill_bytes = 0

    # Locate each skill directory in .agents/skills
    for skill_name in skills:
        meta = manifest.get(skill_name)
        catalog_lines.append(serialize_skill_summary(skill_name, meta))

        skill_file = _find_skill_file(skills_root, skill_name)
        if skill_file and os.path.isfile(skill_file):
            tokens = count_file_tokens(skill_file)
            size = os.path.getsize(skill_file)
            full_skill_tokens += tokens
            full_skill_bytes += size
        else:
            # Fallback average skill size if file missing
            full_skill_tokens += 1200
            full_skill_bytes += 4500

    catalog_skill_tokens = count_tokens("\n".join(catalog_lines)) if catalog_lines else 0

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


def get_full_unrouted_baseline(repo_root: str) -> Dict[str, Any]:
    """
    Enumerates and calculates actual token and byte counts for 100% of all rules in .agents/rules
    and 100% of all skills in .agents/skills.
    Guarantees zero static assumptions (replaces 53 * 1800 and 53 * 120 with exact file token counts).
    """
    rules_dir = os.path.join(repo_root, ".agents", "rules")
    skills_root = os.path.join(repo_root, ".agents", "skills")
    manifest = _get_skills_manifest(repo_root)

    # 1. Enumerate all rule files
    all_rule_files: List[str] = []
    if os.path.isdir(rules_dir):
        all_rule_files = sorted([f for f in os.listdir(rules_dir) if f.endswith(".md")])

    total_rule_tokens = 0
    total_rule_bytes = 0
    for rf in all_rule_files:
        p = os.path.join(rules_dir, rf)
        total_rule_tokens += count_file_tokens(p)
        total_rule_bytes += os.path.getsize(p)

    # 2. Enumerate all 53 SKILL.md files
    skill_files = sorted(glob.glob(os.path.join(skills_root, "*", "*", "SKILL.md")))
    total_skill_tokens = 0
    total_skill_bytes = 0
    all_skill_ids: List[str] = []

    for sf in skill_files:
        total_skill_tokens += count_file_tokens(sf)
        total_skill_bytes += os.path.getsize(sf)
        skill_id = os.path.basename(os.path.dirname(sf))
        all_skill_ids.append(skill_id)

    # 3. Dynamic Catalog Summary tokens across all skills
    catalog_lines = []
    for sid in all_skill_ids:
        meta = manifest.get(sid)
        catalog_lines.append(serialize_skill_summary(sid, meta))

    total_cat_tokens = count_tokens("\n".join(catalog_lines)) if catalog_lines else 0

    return {
        "rule_count": len(all_rule_files),
        "rule_tokens": total_rule_tokens,
        "rule_bytes": total_rule_bytes,
        "skill_count": len(skill_files),
        "skill_full_body_tokens": total_skill_tokens,
        "skill_full_bytes": total_skill_bytes,
        "skill_catalog_tokens": total_cat_tokens,
        "total_summary_baseline": total_rule_tokens + total_cat_tokens,
        "total_full_baseline": total_rule_tokens + total_skill_tokens,
        "total_full_bytes": total_rule_bytes + total_skill_bytes,
        "all_rules": all_rule_files,
        "all_skills": all_skill_ids,
        "estimator_info": get_estimator_info(),
    }


def _find_skill_file(skills_root: str, skill_name: str) -> Optional[str]:
    """Finds SKILL.md for a given skill name across tiered category folders."""
    if not os.path.isdir(skills_root):
        return None
    for root, dirs, files in os.walk(skills_root):
        if os.path.basename(root) == skill_name and "SKILL.md" in files:
            return os.path.join(root, "SKILL.md")
    return None
