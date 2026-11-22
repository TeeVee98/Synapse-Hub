#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/lint/plan_schema_sentinel.py — Spec-Driven Planning & Implementation Plan Linter
-------------------------------------------------------------------------------------
Mechanically enforces the 4 Planning Pillars declared in AGENTS.md §5 & .agents/rules/plan-protocol.md:
  1. Strict Grounding: Repository context surveyed before planning.
  2. Mandatory 4-Part Structure:
     - Affected Files & Blast Radius
     - Data Flow & Interface Signatures
     - Atomic Milestones (Budget: <= 3 files per milestone)
     - Verification Matrix ("Define the Exam in the Plan")
  3. Non-Generic Assertions: Zero vague statements like "write unit tests".
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Enforce UTF-8 stdout/stderr encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REQUIRED_SECTIONS = [
    ("affected_files", re.compile(r"#+\s*(?:1[.\s]*)?Affected\s+Files", re.IGNORECASE)),
    ("data_flow", re.compile(r"#+\s*(?:2[.\s]*)?Data\s+Flow|Interface\s+Signatures", re.IGNORECASE)),
    ("atomic_milestones", re.compile(r"#+\s*(?:3[.\s]*)?Atomic\s+Milestones|Milestones", re.IGNORECASE)),
    ("verification_matrix", re.compile(r"#+\s*(?:4[.\s]*)?Verification\s+Matrix|Verification\s+Plan", re.IGNORECASE)),
]

FORBIDDEN_GENERIC_PATTERNS = [
    re.compile(r"\bwrite\s+(?:some\s+)?unit\s+tests?\s+to\s+verify\b", re.IGNORECASE),
    re.compile(r"\bviết\s+(?:các\s+)?unit\s+tests?\s+để\s+kiểm\s+tra\b", re.IGNORECASE),
    re.compile(r"\btest\s+xem\s+có\s+lỗi\s+không\b", re.IGNORECASE),
    re.compile(r"\bmanually\s+test\s+feature\b", re.IGNORECASE),
]

TEST_COMMAND_PATTERNS = [
    re.compile(r"`(?:pytest|npm test|npx playwright test|mvn test|python3?|ruff|jest|vitest)[^`]*`"),
    re.compile(r"\b(?:pytest|playwright|mvn test|npm test)\b"),
]


def validate_plan_content(content: str, filename: str = "plan.md") -> Tuple[bool, List[str], Dict[str, Any]]:
    """Validates markdown content against the 4 Spec-Driven Planning pillars.

    Returns:
        (passed, issues, details)
    """
    issues: List[str] = []
    details: Dict[str, Any] = {
        "file": filename,
        "sections_present": {},
        "milestones_checked": 0,
        "has_verification_commands": False,
        "forbidden_phrases_detected": [],
    }

    # Pillar 1 & 2: Check required sections
    for section_key, pattern in REQUIRED_SECTIONS:
        found = bool(pattern.search(content))
        details["sections_present"][section_key] = found
        if not found:
            issues.append(f"Missing mandatory section header matching '{section_key}' in {filename}")

    # Pillar 3: Atomic Milestones Budget Check (Max 3 files per milestone)
    milestone_blocks = re.findall(
        r"(?:###?\s*(?:Milestone\s*\d+|Chặng\s*\d+)[^\n]*)(.*?)(?=(?:###?\s*(?:Milestone\s*\d+|Chặng\s*\d+))|\Z)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    details["milestones_checked"] = len(milestone_blocks)
    for idx, block in enumerate(milestone_blocks, 1):
        # Look for explicit file mentions in the milestone block (e.g. `path/to/file.ext` or file paths)
        raw_files = re.findall(r"`([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]{1,6})`", block)
        # Deduplicate
        unique_files = list(set(raw_files))
        # Filter out common command names or tools
        source_files = [f for f in unique_files if not f.startswith("pytest") and not f.startswith("python")]
        if len(source_files) > 3:
            issues.append(
                f"Milestone {idx} violates Atomic Milestone budget: modifies {len(source_files)} files "
                f"(max allowed is 3): {source_files}"
            )

    # Pillar 4: Verification Matrix Determinism
    has_command = any(p.search(content) for p in TEST_COMMAND_PATTERNS)
    details["has_verification_commands"] = has_command
    if not has_command:
        issues.append(
            f"Verification Matrix in {filename} lacks concrete executable test commands (`pytest`, `npx playwright test`, etc.)"
        )

    # Check for forbidden generic assertions
    for pattern in FORBIDDEN_GENERIC_PATTERNS:
        match = pattern.search(content)
        if match:
            phrase = match.group(0)
            details["forbidden_phrases_detected"].append(phrase)
            issues.append(f"Forbidden generic test description detected in {filename}: '{phrase}'. Specify concrete input/output.")

    passed = len(issues) == 0
    return passed, issues, details


def lint_plan_file(filepath: str) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Lints a specific plan file from disk."""
    if not os.path.isfile(filepath):
        return False, [f"File does not exist: {filepath}"], {"file": filepath, "exists": False}
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return validate_plan_content(content, filename=filepath)
    except Exception as e:
        return False, [f"Error reading {filepath}: {e}"], {"file": filepath, "error": str(e)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Spec-Driven Planning Sentinel (AGENTS.md §5 / plan-protocol.md)")
    parser.add_argument("--file", help="Path to markdown plan to validate")
    parser.add_argument("--check-templates", action="store_true", help="Validates built-in templates")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    target_files: List[str] = []
    if args.check_templates:
        tmpl = os.path.join(_REPO_ROOT, "templates", "test-plan", "spec-driven-plan-template.md")
        if os.path.isfile(tmpl):
            target_files.append(tmpl)

    if args.file:
        target_files.append(args.file)

    if not target_files:
        # Default: check template if no file specified
        tmpl = os.path.join(_REPO_ROOT, "templates", "test-plan", "spec-driven-plan-template.md")
        if os.path.isfile(tmpl):
            target_files.append(tmpl)
        else:
            parser.print_help()
            return 1

    all_passed = True
    results: List[Dict[str, Any]] = []

    for fpath in target_files:
        passed, issues, details = lint_plan_file(fpath)
        if not passed:
            all_passed = False
        results.append({
            "file": fpath,
            "passed": passed,
            "issues": issues,
            "details": details,
        })

    if args.json:
        print(json.dumps({"passed": all_passed, "results": results}, indent=2))
        return 0 if all_passed else 1

    for res in results:
        status_str = "PASS" if res["passed"] else "FAIL"
        print(f"[{status_str}] {os.path.basename(res['file'])}")
        if not res["passed"]:
            for issue in res["issues"]:
                print(f"  - [X] {issue}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
