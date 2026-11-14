#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/validate_skills_schema.py — Standalone Skill Schema & Policy Validator
Validates all skills against the Agent Skills Frontmatter & Policies Specification.
"""

import os
import sys
import re
import json
import argparse
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

ALLOWED_CATEGORIES = {
    "test_automation_and_execution",
    "architecture_and_analysis",
    "verification_and_resilience",
    "context_and_optimization",
}

ALLOWED_POLICIES = {
    "network": {"none", "localhost-only", "sandbox-only"},
    "shell": {"none", "read-only", "workspace-sandbox"},
    "filesystem": {"read-only", "workspace-sandbox"},
}

SEMVER_REGEX = re.compile(r"^\d+\.\d+\.\d+$")
SKILL_NAME_REGEX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MD_LINK_REGEX = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def parse_yaml_frontmatter(content: str) -> Tuple[Optional[Dict[str, Any]], str, List[str]]:
    """
    Extracts and parses YAML frontmatter without external pyyaml dependency.
    Falls back to yaml.safe_load if pyyaml is installed.
    """
    errors: List[str] = []
    if not content.startswith("---"):
        return None, "", ["File does not start with '---' delimiter on line 1"]

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        return None, "", ["Frontmatter missing closing '---' delimiter"]

    fm_text = match.group(1)
    body = match.group(2)

    # If PyYAML is available, use it directly
    if importlib.util.find_spec("yaml") is not None:
        import yaml
        try:
            data = yaml.safe_load(fm_text)
            if isinstance(data, dict):
                return data, body, []
            errors.append("PyYAML failed to parse frontmatter as a dictionary")
            return None, "", errors
        except yaml.YAMLError as y_err:
            errors.append(f"PyYAML syntax error: {y_err}")
            return None, "", errors

    # Pure Python stdlib parser for frontmatter
    data: Dict[str, Any] = {}
    current_section: Optional[str] = None

    for line_no, raw_line in enumerate(fm_text.splitlines(), 1):
        line = raw_line.rstrip()
        if not line or line.strip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        if indent == 0:
            if ":" not in stripped:
                errors.append(f"Line {line_no}: Invalid YAML key-value syntax: '{stripped}'")
                continue
            key, val = stripped.split(":", 1)
            key, val = key.strip(), val.strip()
            if not val:
                current_section = key
                data[current_section] = {}
            else:
                current_section = None
                data[key] = val.strip("\"'")
        elif indent >= 2 and current_section:
            if ":" not in stripped:
                errors.append(f"Line {line_no}: Invalid child YAML syntax in '{current_section}': '{stripped}'")
                continue
            ckey, cval = stripped.split(":", 1)
            ckey, cval = ckey.strip(), cval.strip().strip("\"'")
            if isinstance(data.get(current_section), dict):
                data[current_section][ckey] = cval

    return data, body, errors


def validate_skill(skill_md_path: Path, check_links: bool = True) -> List[str]:
    """Validates a single SKILL.md file against the specification."""
    errors: List[str] = []
    try:
        content = skill_md_path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"Cannot read file: {e}"]

    fm, body, parse_errors = parse_yaml_frontmatter(content)
    if parse_errors:
        return parse_errors
    if fm is None:
        return ["Failed to parse frontmatter"]

    expected_name = skill_md_path.parent.name
    actual_name = fm.get("name")

    # 1. Name check
    if not actual_name:
        errors.append("Missing required field: 'name'")
    elif actual_name != expected_name:
        errors.append(f"Field 'name' ('{actual_name}') does not match directory name ('{expected_name}')")
    elif len(actual_name) > 64 or not SKILL_NAME_REGEX.match(actual_name):
        errors.append(f"Invalid 'name' format: '{actual_name}' (must be lowercase alphanumeric + hyphens, <= 64 chars)")

    # 2. Description check
    desc = fm.get("description")
    if not desc or not str(desc).strip():
        errors.append("Missing required field: 'description'")
    else:
        desc_str = str(desc).strip()
        if len(desc_str) > 1024:
            errors.append(f"Description length ({len(desc_str)}) exceeds 1024 characters")
        if "use when" not in desc_str.lower():
            errors.append("Description missing mandatory activation trigger clause ('Use when...')")

    # 3. Category check
    category = fm.get("category")
    if not category:
        errors.append("Missing required field: 'category'")
    elif category not in ALLOWED_CATEGORIES:
        errors.append(f"Invalid category '{category}'. Must be one of: {sorted(ALLOWED_CATEGORIES)}")

    # 4. Version check
    version = fm.get("version")
    if not version:
        errors.append("Missing required field: 'version'")
    elif not SEMVER_REGEX.match(str(version).strip("\"'")):
        errors.append(f"Invalid version format '{version}'. Must conform to SemVer (e.g. '1.0.0')")

    # 5. Policies check
    policies = fm.get("policies")
    if policies is None:
        errors.append("Missing required field: 'policies'")
    elif not isinstance(policies, dict):
        errors.append(f"'policies' must be a dictionary object, got {type(policies).__name__}")
    else:
        for pol_key, allowed_vals in ALLOWED_POLICIES.items():
            val = policies.get(pol_key)
            if not val:
                errors.append(f"Missing required policy: 'policies.{pol_key}'")
            elif val not in allowed_vals:
                errors.append(f"Invalid value '{val}' for 'policies.{pol_key}'. Must be one of: {sorted(allowed_vals)}")

    # 6. Relative links check
    if check_links:
        for match in MD_LINK_REGEX.finditer(body):
            target = match.group(2).strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            clean_target = target.split("#")[0].split("?")[0].strip()
            if not clean_target:
                continue
            resolved = (skill_md_path.parent / clean_target).resolve()
            if not resolved.exists():
                errors.append(f"Broken relative link: '{target}' (resolved to non-existent path: {resolved})")

    # 7. Examples directory check
    examples_dir = skill_md_path.parent / "examples"
    if not examples_dir.is_dir():
        errors.append("Missing mandatory 'examples/' directory")
    elif not list(examples_dir.iterdir()):
        errors.append("'examples/' directory is empty")

    return errors


def run_validation(skills_dir: Path, check_links: bool = True) -> Tuple[int, Dict[str, List[str]]]:
    """Scans all skills under skills_dir and validates each SKILL.md."""
    results: Dict[str, List[str]] = {}
    skill_files = sorted(skills_dir.glob("*/*/SKILL.md"))
    for sf in skill_files:
        rel_path = sf.as_posix()
        errs = validate_skill(sf, check_links=check_links)
        if errs:
            results[rel_path] = errs
    return len(skill_files), results


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Agent Skills frontmatter schema and policies.")
    parser.add_argument(
        "--skills-dir",
        type=str,
        default=".agents/skills",
        help="Path to the .agents/skills directory (default: .agents/skills)",
    )
    parser.add_argument(
        "--check-links",
        action="store_true",
        default=False,
        help="Verify existence of relative markdown resource links",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output results in JSON format",
    )

    args = parser.parse_args()
    skills_path = Path(args.skills_dir).resolve()

    if not skills_path.exists():
        print(f"Error: Skills directory not found at {skills_path}", file=sys.stderr)
        return 1

    total_scanned, failures = run_validation(skills_path, check_links=args.check_links)

    if args.json:
        output_payload = {
            "total_skills": total_scanned,
            "valid_skills": total_scanned - len(failures),
            "failed_skills": len(failures),
            "passed": len(failures) == 0,
            "failures": failures,
        }
        print(json.dumps(output_payload, indent=2))
        return 0 if len(failures) == 0 else 1

    print(f"\n🔍 Validating {total_scanned} skills in {skills_path}...")
    if args.check_links:
        print("🔗 Checking relative markdown links...")

    if not failures:
        print(f"✅ 100% Verified: All {total_scanned} skills conform to Frontmatter Schema & Policies.")
        return 0

    print(f"❌ Validation failed: {len(failures)}/{total_scanned} skills have schema or link errors:\n")
    for file_path, err_list in failures.items():
        print(f"  • {file_path}:")
        for err in err_list:
            print(f"      - {err}")
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
