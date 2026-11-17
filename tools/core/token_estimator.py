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

from datetime import datetime, timezone
import glob
import hashlib
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

try:
    from tools.core.provider_usage_adapter import get_repo_version_and_commit
except ImportError:
    try:
        from core.provider_usage_adapter import get_repo_version_and_commit
    except ImportError:
        def get_repo_version_and_commit(repo_root=None):
            return "1.0.0", "unversioned"

# Cache mapping canonical manifest_path -> (mtime, parsed_manifest)
_SKILLS_MANIFEST_CACHE: Dict[str, Any] = {}


def clear_skills_manifest_cache() -> None:
    """Clears the in-memory skills manifest cache."""
    global _SKILLS_MANIFEST_CACHE
    _SKILLS_MANIFEST_CACHE.clear()


def get_estimator_info() -> Dict[str, Any]:
    """Returns active tokenizer engine metadata, exactness status, and model hint."""
    pkg_version = None
    if _TIKTOKEN_ENCODER is not None:
        try:
            pkg_version = getattr(tiktoken, "__version__", None)
        except Exception:
            pkg_version = None

    return {
        "engine": "cl100k_base" if _TIKTOKEN_ENCODER is not None else "heuristic_polyglot",
        "is_exact": _TIKTOKEN_ENCODER is not None,
        "encoding": "cl100k_base",
        "package_version": pkg_version,
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
            import sys
            sys.stderr.write(f"Warning: tiktoken encoding error, fallback to heuristic: {err}\n")

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
    """
    Loads and caches skills_manifest.json mapping skill_id to metadata.
    Cache is keyed by the canonical realpath of the manifest file and validated
    against file mtime_ns, size, and content SHA-256 digest to guarantee that
    mutations are detected even if file modification time remains identical.
    """
    global _SKILLS_MANIFEST_CACHE
    manifest_path = os.path.realpath(os.path.join(repo_root, "skills_manifest.json"))

    if not os.path.isfile(manifest_path):
        _SKILLS_MANIFEST_CACHE.pop(manifest_path, None)
        return {}

    try:
        st = os.stat(manifest_path)
        current_mtime_ns = st.st_mtime_ns
        current_size = st.st_size
    except OSError:
        _SKILLS_MANIFEST_CACHE.pop(manifest_path, None)
        return {}

    try:
        with open(manifest_path, "rb") as f:
            raw_bytes = f.read()
        current_digest = hashlib.sha256(raw_bytes).digest()
    except OSError:
        _SKILLS_MANIFEST_CACHE.pop(manifest_path, None)
        return {}

    if manifest_path in _SKILLS_MANIFEST_CACHE:
        cached_entry = _SKILLS_MANIFEST_CACHE[manifest_path]
        if len(cached_entry) == 4:
            cached_mtime_ns, cached_size, cached_digest, cached_data = cached_entry
            if cached_digest == current_digest:
                return cached_data
        elif len(cached_entry) == 2:
            cached_mtime, cached_data = cached_entry
            if cached_mtime == st.st_mtime:
                return cached_data

    manifest_data: Dict[str, Dict[str, Any]] = {}
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
        for s in data.get("skills", []):
            sid = s.get("id")
            if sid:
                manifest_data[sid] = s
        _SKILLS_MANIFEST_CACHE[manifest_path] = (current_mtime_ns, current_size, current_digest, manifest_data)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        import sys
        sys.stderr.write(f"Warning: Failed to load manifest at {manifest_path}: {err}\n")
        _SKILLS_MANIFEST_CACHE.pop(manifest_path, None)

    return manifest_data


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
        if not os.path.isfile(p):
            for sub in [
                os.path.join("standards", "coding-standards"),
                os.path.join("standards", "qa-process"),
                os.path.join("standards", "quality-gates"),
                os.path.join("standards", "context-ai"),
                os.path.join("automation", "cypress"),
                os.path.join("automation", "mobile"),
                os.path.join("automation", "playwright"),
                os.path.join("testing", "performance"),
                os.path.join("testing", "security-a11y"),
            ]:
                cand = os.path.join(repo_root, sub, r)
                if os.path.isfile(cand):
                    p = cand
                    break
        if os.path.isfile(p):
            rule_tokens += count_file_tokens(p)
            rule_bytes += os.path.getsize(p)
        else:
            rule_tokens += 500  # Default estimate for virtual rule
            rule_bytes += 2000

    catalog_lines = []
    full_skill_tokens = 0
    full_skill_bytes = 0

    # Locate each skill directory in .agents/skills or manifest path
    for skill_name in skills:
        meta = manifest.get(skill_name)
        catalog_lines.append(serialize_skill_summary(skill_name, meta))

        skill_file = _find_skill_file(skills_root, skill_name)
        if (not skill_file or not os.path.isfile(skill_file)) and meta and "path" in meta:
            cand = os.path.join(repo_root, meta["path"])
            if os.path.isfile(cand):
                skill_file = cand
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

    info = get_estimator_info()
    version, commit_sha = get_repo_version_and_commit(repo_root)
    input_str = f"rules:{','.join(sorted(rules))};skills:{','.join(sorted(skills))}"
    input_hash = hashlib.sha256(input_str.encode("utf-8")).hexdigest()
    now_iso = datetime.now(timezone.utc).isoformat()
    is_fallback = not info.get("is_exact", False)
    encoding = info.get("encoding", "cl100k_base")

    return {
        "measurement_kind": "static_estimate",
        "static_estimated_tokens": rule_tokens + full_skill_tokens,
        "commit_sha": commit_sha,
        "timestamp": now_iso,
        "input_hash": input_hash,
        "is_fallback": is_fallback,
        "encoding": encoding,
        "tokenizer_engine": info.get("engine", "heuristic_polyglot"),
        "provider_reported_input_tokens": None,
        "provider_reported_output_tokens": None,
        "provider_cached_tokens": None,
        "avoided_disk_bytes": 0,
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
    if all_rule_files:
        for rf in all_rule_files:
            p = os.path.join(rules_dir, rf)
            total_rule_tokens += count_file_tokens(p)
            total_rule_bytes += os.path.getsize(p)
    else:
        rule_candidates = [
            os.path.join("standards", "coding-standards", "author-integrity-guard.md"),
            os.path.join("standards", "coding-standards", "communication-style.md"),
            os.path.join("standards", "coding-standards", "git-push-protocol.md"),
            os.path.join("standards", "context-ai", "context-engineering.md"),
            os.path.join("standards", "qa-process", "graphify.md"),
            os.path.join("standards", "qa-process", "lessons-learned.md"),
            os.path.join("standards", "qa-process", "skill-precedence.md"),
            os.path.join("standards", "qa-process", "stack-auto-router.md"),
            os.path.join("standards", "quality-gates", "systematic-debugging.md"),
            os.path.join("automation", "cypress", "cypress_rules.md"),
            os.path.join("automation", "mobile", "mobile_appium_rules.md"),
            os.path.join("automation", "playwright", "mandatory-playwright-live.md"),
            os.path.join("testing", "performance", "performance_testing_rules.md"),
            os.path.join("testing", "security-a11y", "security_testing_rules.md"),
        ]
        all_rule_paths = [os.path.join(repo_root, p) for p in rule_candidates if os.path.isfile(os.path.join(repo_root, p))]
        all_rule_files = [os.path.basename(p) for p in all_rule_paths]
        total_rule_tokens = sum(count_file_tokens(p) for p in all_rule_paths)
        total_rule_bytes = sum(os.path.getsize(p) for p in all_rule_paths)

    # 2. Enumerate all SKILL.md files
    skill_files = sorted(glob.glob(os.path.join(skills_root, "*", "*", "SKILL.md")))
    if not skill_files and manifest:
        for sid, s in manifest.items():
            sp = os.path.join(repo_root, s.get("path", ""))
            if os.path.isfile(sp):
                skill_files.append(sp)

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

    info = get_estimator_info()
    version, commit_sha = get_repo_version_and_commit(repo_root)
    input_str = f"rules:{','.join(sorted(all_rule_files))};skills:{','.join(sorted(all_skill_ids))}"
    input_hash = hashlib.sha256(input_str.encode("utf-8")).hexdigest()
    now_iso = datetime.now(timezone.utc).isoformat()
    is_fallback = not info.get("is_exact", False)
    encoding = info.get("encoding", "cl100k_base")

    return {
        "measurement_kind": "static_estimate",
        "static_estimated_tokens": total_rule_tokens + total_skill_tokens,
        "commit_sha": commit_sha,
        "timestamp": now_iso,
        "input_hash": input_hash,
        "is_fallback": is_fallback,
        "encoding": encoding,
        "tokenizer_engine": info.get("engine", "heuristic_polyglot"),
        "provider_reported_input_tokens": None,
        "provider_reported_output_tokens": None,
        "provider_cached_tokens": None,
        "avoided_disk_bytes": 0,
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
        "estimator_info": info,
    }


def _find_skill_file(skills_root: str, skill_name: str) -> Optional[str]:
    """Finds SKILL.md for a given skill name across tiered category folders."""
    if not os.path.isdir(skills_root):
        return None
    for root, dirs, files in os.walk(skills_root):
        if os.path.basename(root) == skill_name and "SKILL.md" in files:
            return os.path.join(root, "SKILL.md")
    return None
