#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/skill_profiles.py — Skill Catalog Capability Profile Manager

Provides filtering, listing, and inspection of the 53 standardized AI Agent skills
partitioned across the 4 core capability profiles:
  1. core-web-qa     (Web E2E, POM, Playwright, live probing, locators, visual regression)
  2. perf-and-load   (JMeter, k6, Locust, backend load, CWV, APM telemetry)
  3. api-security    (OpenAPI, CDC Pact, DAST sentinel, network mocking, fuzzing)
  4. enterprise-rbt  (AI-RBT manual testing, Gherkin, risk matrices, 12-column Excel suites, WCAG, a11y)

Usage:
  python3 tools/skill_profiles.py --list-profiles
  python3 tools/skill_profiles.py --profile core-web-qa
  python3 tools/skill_profiles.py --profile perf-and-load --format json
  python3 tools/skill_profiles.py --query "playwright"
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, List, Optional

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_MANIFEST = os.path.join(REPO_ROOT, "skills_manifest.json")


def resolve_manifest_path(repo_root: Optional[str] = None) -> Optional[str]:
    """
    Fallback manifest resolution:
      1. REPO_ROOT/skills_manifest.json
      2. tools/skills_manifest.json
      3. importlib.resources.files("tools").joinpath("skills_manifest.json")
    """
    root = repo_root or REPO_ROOT
    # 1. Check REPO_ROOT/skills_manifest.json
    candidate1 = os.path.join(root, "skills_manifest.json")
    if os.path.isfile(candidate1):
        return candidate1

    # 2. Check tools/skills_manifest.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidate2 = os.path.join(script_dir, "skills_manifest.json")
    if os.path.isfile(candidate2):
        return candidate2
    candidate2_alt = os.path.join(root, "tools", "skills_manifest.json")
    if os.path.isfile(candidate2_alt):
        return candidate2_alt

    # 3. Check importlib.resources.files("tools").joinpath("skills_manifest.json")
    try:
        import importlib.resources as pkg_resources
        resource = pkg_resources.files("tools").joinpath("skills_manifest.json")
        if resource.is_file():
            try:
                r_str = str(resource)
                if os.path.isfile(r_str):
                    return r_str
            except (TypeError, ValueError) as str_err:
                res_str_err = str(str_err)
            with pkg_resources.as_file(resource) as p:
                return str(p)
    except (ImportError, AttributeError, TypeError) as res_err:
        res_load_err = str(res_err)

    return None


def get_skills_dir(repo_root: Optional[str] = None) -> Optional[str]:
    """Resolves local skills directory or returns None with actionable guidance."""
    root = repo_root or REPO_ROOT
    candidates = [
        os.path.join(root, ".agents", "skills"),
        os.path.join(root, "skills"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "skills"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return None


def load_manifest(manifest_path: Optional[str] = None) -> Dict[str, Any]:
    """Loads and validates skills_manifest.json with fallback resolution."""
    path = manifest_path or resolve_manifest_path()
    if not path or not os.path.isfile(path):
        searched = [
            os.path.join(REPO_ROOT, "skills_manifest.json"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "skills_manifest.json"),
            "importlib.resources.files('tools').joinpath('skills_manifest.json')",
        ]
        searched_desc = "\n".join(f"  • {s}" for s in searched)
        raise FileNotFoundError(
            f"Skills manifest could not be located. Searched locations:\n{searched_desc}\n"
            "Ensure Synapse Hub was installed with package data, or specify --manifest <path>."
        )
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to read skills manifest at '{path}': {e}") from e


def list_profiles(manifest: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """Returns available profiles with metadata and resolved skill count."""
    mf = manifest or load_manifest()
    profiles_raw = mf.get("profiles", {})
    all_skills = mf.get("skills", [])
    total_count = len(all_skills)

    result = {}
    for key, pdata in profiles_raw.items():
        skills_val = pdata.get("skills", [])
        if skills_val == "all":
            skill_list = [s.get("id") for s in all_skills]
        elif isinstance(skills_val, list):
            skill_list = list(skills_val)
        else:
            skill_list = []

        result[key] = {
            "key": key,
            "name": pdata.get("name", key),
            "description": pdata.get("description", ""),
            "skill_count": len(skill_list),
            "skills": skill_list
        }
    return result


def get_profile(profile_key: str, manifest: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Returns a specific capability profile by key."""
    profiles = list_profiles(manifest)
    normalized = profile_key.strip().lower()
    return profiles.get(normalized)


def filter_skills(
    profile_key: Optional[str] = None,
    category: Optional[str] = None,
    query: Optional[str] = None,
    manifest: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Filters skills by profile key, category, and/or search query."""
    mf = manifest or load_manifest()
    all_skills = mf.get("skills", [])

    # Profile filtering
    allowed_ids = None
    if profile_key:
        prof = get_profile(profile_key, mf)
        if prof is None:
            available = ", ".join(list_profiles(mf).keys())
            raise ValueError(f"Unknown profile '{profile_key}'. Available profiles: {available}")
        allowed_ids = set(prof["skills"])

    matched = []
    q_lower = query.strip().lower() if query else None
    cat_lower = category.strip().lower() if category else None

    for skill in all_skills:
        sid = skill.get("id", "")
        if allowed_ids is not None and sid not in allowed_ids:
            continue

        if cat_lower and skill.get("category", "").lower() != cat_lower:
            continue

        if q_lower:
            s_name = skill.get("name", "").lower()
            s_summary = skill.get("summary", "").lower()
            s_desc = skill.get("description", "").lower()
            if q_lower not in sid.lower() and q_lower not in s_name and q_lower not in s_summary and q_lower not in s_desc:
                continue

        matched.append(skill)

    return matched


def format_profiles_text(profiles: Dict[str, Dict[str, Any]]) -> str:
    """Formats profiles dictionary into a clean CLI table."""
    lines = [
        "==========================================================================================",
        "             SYNAPSE HUB — 4 CORE CAPABILITY PROFILES & CATALOG MODULES                  ",
        "==========================================================================================",
        f"{'KEY':<18} {'NAME':<36} {'SKILLS':<8} {'DESCRIPTION'}",
        "-" * 90
    ]
    core_keys = ["core-web-qa", "perf-and-load", "api-security", "enterprise-rbt"]
    # Print core 4 first, then others
    ordered_keys = [k for k in core_keys if k in profiles] + [k for k in profiles if k not in core_keys]

    for key in ordered_keys:
        p = profiles[key]
        desc = p["description"]
        if len(desc) > 55:
            desc = desc[:52] + "..."
        lines.append(f"{p['key']:<18} {p['name']:<36} {p['skill_count']:<8} {desc}")
    lines.append("=" * 90)
    lines.append("💡 Tip: Use 'agent-qa skills --profile <key>' to view skills in a specific profile.")
    return "\n".join(lines)


def format_skills_text(skills: List[Dict[str, Any]], profile_key: Optional[str] = None) -> str:
    """Formats a list of skills into a clean CLI table."""
    header_title = f"SKILLS IN PROFILE: {profile_key.upper()}" if profile_key else "STANDARDIZED AI AGENT SKILLS"
    lines = [
        "==========================================================================================",
        f"  {header_title} (Total: {len(skills)})",
        "==========================================================================================",
        f"{'ID':<36} {'CATEGORY':<28} {'SUMMARY'}",
        "-" * 90
    ]
    for s in sorted(skills, key=lambda x: x.get("id", "")):
        sid = s.get("id", "")
        cat = s.get("category", "")
        summary = s.get("summary", "")
        if len(summary) > 65:
            summary = summary[:62] + "..."
        lines.append(f"{sid:<36} {cat:<28} {summary}")
    lines.append("=" * 90)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Synapse Hub AI Agent Skill Capability Profile Manager")
    parser.add_argument("--profile", "-p", help="Filter skills by capability profile (e.g. core-web-qa, perf-and-load, api-security, enterprise-rbt)")
    parser.add_argument("--list-profiles", "-l", action="store_true", help="List all available capability profiles")
    parser.add_argument("--category", "-c", help="Filter skills by category")
    parser.add_argument("--query", "-q", help="Search skills by keyword")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format (default: text)")
    parser.add_argument("--manifest", help="Optional path to skills_manifest.json", default=None)

    args = parser.parse_args()

    try:
        manifest = load_manifest(args.manifest)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error loading manifest: {e}", file=sys.stderr)
        return 1

    if args.list_profiles or (not args.profile and not args.category and not args.query):
        profiles = list_profiles(manifest)
        if args.format == "json":
            print(json.dumps(profiles, indent=2, ensure_ascii=False))
        else:
            print(format_profiles_text(profiles))
        return 0

    try:
        skills = filter_skills(
            profile_key=args.profile,
            category=args.category,
            query=args.query,
            manifest=manifest
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(skills, indent=2, ensure_ascii=False))
    else:
        print(format_skills_text(skills, profile_key=args.profile))

    return 0


if __name__ == "__main__":
    sys.exit(main())
