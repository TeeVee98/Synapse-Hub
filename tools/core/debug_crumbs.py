#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/core/debug_crumbs.py — Ephemeral Debug Crumbs Engine
----------------------------------------------------------
Inspired by Trigger.dev agentcrumbs pattern.
Enables agents and engineers to insert ephemeral debug probes (# @crumbs, // @crumbs,
/* @crumbs */, and # region @crumbs blocks) during multi-turn debugging sessions, while
providing deterministic scanning (--check) and automated pre-merge stripping (--strip)
to guarantee zero debug residue enters production commits.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

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

# Crumb marker patterns
_RE_REGION_START = re.compile(r"^\s*(?:#|//|/\*|<!--)\s*#?region\s+@?crumbs\b", re.IGNORECASE)
_RE_REGION_END = re.compile(r"^\s*(?:#|//|/\*|<!--)\s*#?endregion\s+@?crumbs\b", re.IGNORECASE)
_RE_SINGLE_CRUMB = re.compile(r"(?:#|//|/\*|<!--)\s*(?:@crumbs|\[crumbs\]|@crumb\b)", re.IGNORECASE)

# Ignored files (e.g. self-definitions in tool and test suites, or documentation explaining the feature)
_IGNORED_FILES = {
    "debug_crumbs.py",
    "test_debug_crumbs.py",
    "test_reference_enhancements_e2e.py",
    "TOOLS_RUNBOOK.md",
    "INVARIANTS.md",
    "AGENTS.md",
    "CLAUDE.md",
    "top_10_agent_repos_deep_dive.md",
}

# Ignored directories during tree traversal
_IGNORED_DIRS = {
    ".git",
    "node_modules",
    "reference_repos",
    "build",
    "dist",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".gradle",
    "reports",
    ".agents",
    "scratch",
    "claude-ecosystem-repos",
    "external_repos",
}

# Supported file extensions for crumb scanning
_SCANNABLE_EXTENSIONS = {
    ".py",
    ".ts",
    ".js",
    ".jsx",
    ".tsx",
    ".json",
    ".md",
    ".groovy",
    ".java",
    ".yaml",
    ".yml",
    ".sh",
    ".html",
    ".css",
    ".sql",
}


def scan_file_for_crumbs(file_path: str) -> List[Dict[str, Any]]:
    """
    Scans a single file for single-line crumbs and region crumb blocks.
    Returns list of crumb location dicts: [{"file": ..., "line": ..., "crumb": ...}].
    """
    crumbs: List[Dict[str, Any]] = []
    if not os.path.isfile(file_path):
        return crumbs

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return crumbs

    in_region = False
    for line_idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if _RE_REGION_START.search(stripped):
            in_region = True
            crumbs.append({"file": file_path, "line": line_idx, "crumb": stripped})
            continue

        if in_region:
            crumbs.append({"file": file_path, "line": line_idx, "crumb": stripped})
            if _RE_REGION_END.search(stripped):
                in_region = False
            continue

        if _RE_SINGLE_CRUMB.search(stripped):
            crumbs.append({"file": file_path, "line": line_idx, "crumb": stripped})

    return crumbs


def strip_crumbs_from_file(file_path: str) -> int:
    """
    Strips all crumb lines and crumb regions from a file in-place.
    Returns count of stripped crumb lines.
    """
    if not os.path.isfile(file_path):
        return 0

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return 0

    clean_lines: List[str] = []
    in_region = False
    stripped_count = 0

    for line in lines:
        stripped = line.strip()
        if _RE_REGION_START.search(stripped):
            in_region = True
            stripped_count += 1
            continue

        if in_region:
            stripped_count += 1
            if _RE_REGION_END.search(stripped):
                in_region = False
            continue

        if _RE_SINGLE_CRUMB.search(stripped):
            stripped_count += 1
            continue

        clean_lines.append(line)

    if stripped_count > 0:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(clean_lines)

    return stripped_count


def process_crumbs(
    target_path: str = ".",
    check: bool = False,
    strip: bool = False,
) -> Tuple[Dict[str, Any], int]:
    """
    Scans or strips crumbs across target_path.
    Returns (report_dict, exit_code).
    """
    files_to_scan: List[str] = []

    if os.path.isfile(target_path):
        files_to_scan.append(target_path)
    elif os.path.isdir(target_path):
        _ignored_dirs_lower = {x.lower() for x in _IGNORED_DIRS}
        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d.lower() not in _ignored_dirs_lower and not d.startswith(".")]
            for f in files:
                if f not in _IGNORED_FILES:
                    _, ext = os.path.splitext(f)
                    if ext.lower() in _SCANNABLE_EXTENSIONS:
                        files_to_scan.append(os.path.join(root, f))
    else:
        return {
            "status": "CLEAN",
            "files_scanned": 0,
            "crumbs_count": 0,
            "locations": [],
            "message": f"Target path does not exist: {target_path}",
        }, 1

    all_crumbs: List[Dict[str, Any]] = []
    files_scanned = len(files_to_scan)

    for f_path in files_to_scan:
        file_crumbs = scan_file_for_crumbs(f_path)
        if file_crumbs:
            all_crumbs.extend(file_crumbs)

    total_crumbs = len(all_crumbs)

    if strip and total_crumbs > 0:
        stripped_total = 0
        modified_files = set()
        for f_path in files_to_scan:
            count = strip_crumbs_from_file(f_path)
            if count > 0:
                stripped_total += count
                modified_files.add(f_path)

        return {
            "status": "CRUMBS_STRIPPED",
            "files_scanned": files_scanned,
            "crumbs_count": stripped_total,
            "modified_files": sorted(list(modified_files)),
            "locations": all_crumbs,
            "message": f"Successfully stripped {stripped_total} crumb line(s) across {len(modified_files)} file(s).",
        }, 0

    status = "CLEAN" if total_crumbs == 0 else "CRUMBS_DETECTED"
    exit_code = 1 if (check and total_crumbs > 0) else 0

    return {
        "status": status,
        "files_scanned": files_scanned,
        "crumbs_count": total_crumbs,
        "locations": all_crumbs,
        "message": (
            "No debug crumbs detected."
            if total_crumbs == 0
            else f"Detected {total_crumbs} ephemeral debug crumb(s). Run with --strip to remove."
        ),
    }, exit_code


def build_parser() -> argparse.ArgumentParser:
    """Builds CLI parser for debug_crumbs."""
    parser = argparse.ArgumentParser(
        description="Ephemeral Debug Crumbs Engine (Trigger.dev agentcrumbs pattern)"
    )
    parser.add_argument(
        "--dir",
        type=str,
        default=".",
        help="Directory or file path to scan for debug crumbs (default: .)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify zero crumbs exist; exit 1 if crumbs are detected",
    )
    parser.add_argument(
        "--strip",
        action="store_true",
        help="Cleanly remove all crumb lines and regions in-place",
    )
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON to stdout")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    report, exit_code = process_crumbs(
        target_path=args.dir,
        check=args.check,
        strip=args.strip,
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        status = report["status"]
        if status == "CLEAN":
            print(f"[CLEAN] Scanned {report['files_scanned']} file(s). Zero debug crumbs found.")
        elif status == "CRUMBS_STRIPPED":
            print(f"[STRIPPED] {report['message']}")
        else:
            print(f"[CRUMBS DETECTED] Found {report['crumbs_count']} ephemeral debug crumb(s):")
            for loc in report["locations"][:20]:
                print(f"  {loc['file']}:{loc['line']} -> {loc['crumb']}")
            if len(report["locations"]) > 20:
                print(f"  ... and {len(report['locations']) - 20} more.")
            print("Run with --strip to automatically remove all crumbs.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
