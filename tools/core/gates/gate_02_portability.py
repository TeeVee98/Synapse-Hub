#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Gate 2: Path Portability Sentinel.
Scans for and rejects machine-specific absolute filepaths in code.
"""

import os
from typing import List, Tuple

from tools.core.gates.base import (
    BaseGate,
    FORBIDDEN_PATH_PATTERNS,
    get_scoped_git_files,
)


def gate_2_path_portability(repo_root: str, mode: str = "AUTO", fast: bool = False) -> bool:
    """Gate 2: Scans for and rejects machine-specific absolute filepaths in code."""
    print("\n[GATE 2] Checking Path Portability (Zero absolute machine paths in repo sources)...")
    ignored_dirs = {
        ".git", ".gradle", "node_modules", "allure-results", "Screenshots",
        "Reports", "reports", "TestReports", "testreports", "Libs", ".settings", "graphify-out",
        "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".cache", "agent_qa.egg-info", "synapse_hub.egg-info",
        "dist", "build", "claude-ecosystem-repos", "external_repos", "reference_repos", "teamwork", ".synapse", ".sandbox_snapshots"
    }
    ignored_files = {
        ".project", ".classpath", ".DS_Store", "memory_cache.db",
        "verify_all.py", "git_pre_commit_guard.py", "agent_canary.py", "repo_map.txt", "repo_map.json",
        "PROJECT_HEALTH_REPORT.md", "PROJECT_STATE.md", "AUDIT_REPORT.md"
    }
    violations: List[Tuple[str, int, str]] = []

    files_to_check = None
    if fast:
        scoped = get_scoped_git_files(repo_root, staged_only=True)
        if scoped is not None:
            files_to_check = scoped
            if not files_to_check:
                print("[PASS] [FAST MODE] Zero staged/changed files detected. Gate 2 instant pass.")
                return True

    if files_to_check is not None:
        # Fast path: only iterate scoped git files (zero os.walk)
        for rel_path in files_to_check:
            parts = rel_path.split("/")
            if any(p in ignored_dirs or p.endswith(".egg-info") or p.startswith(("synapse_hub-", "synapse-hub-", ".temp-")) for p in parts[:-1]):
                continue
            filename = parts[-1]
            if filename.startswith(".temp-") or filename in ignored_files or filename.endswith(
                (".pyc", ".db", ".png", ".jpg", ".zip", ".tar", ".gz", ".xlsx", ".class", ".prefs", ".synapse_mutator_bak", ".bak")
            ):
                continue
            if "FINAL_REPORT.md" in rel_path or ".gitignore" in rel_path or ".coverage" in rel_path:
                continue
            full_path = os.path.join(repo_root, *parts)
            if not os.path.isfile(full_path):
                continue
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                    for line_no, line in enumerate(fp, 1):
                        for pattern, desc in FORBIDDEN_PATH_PATTERNS:
                            if pattern.search(line):
                                violations.append((rel_path, line_no, desc))
            except (OSError, PermissionError):
                continue
    else:
        # Full scan via os.walk
        for root, dirs, files in os.walk(repo_root):
            dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.endswith(".egg-info") and not d.startswith(("synapse_hub-", "synapse-hub-", ".temp-"))]
            for f in files:
                if f.startswith(".temp-") or f in ignored_files or f.endswith(
                    (".pyc", ".db", ".png", ".jpg", ".zip", ".tar", ".gz", ".xlsx", ".class", ".prefs", ".synapse_mutator_bak", ".bak")
                ):
                    continue
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, repo_root)

                # Skip historical documentation, gitignore, or temporary coverage files
                if "FINAL_REPORT.md" in rel_path or ".gitignore" in rel_path or ".coverage" in rel_path:
                    continue

                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                        for line_no, line in enumerate(fp, 1):
                            for pattern, desc in FORBIDDEN_PATH_PATTERNS:
                                if pattern.search(line):
                                    violations.append((rel_path, line_no, desc))
                except (OSError, PermissionError):
                    continue

    if violations:
        print(f"[FAIL] {len(violations)} forbidden machine paths found:")
        for rel_path, line_no, term in violations:
            print(f"   - {rel_path}:{line_no} contains '{term}'")
        return False
    if fast and files_to_check is not None:
        print(f"[PASS] [FAST MODE] Zero machine-specific absolute paths detected across {len(files_to_check)} scoped file(s).")
    else:
        print("[PASS] Zero machine-specific absolute paths detected in source files.")
    return True


class Gate02Portability(BaseGate):
    """Gate 2: Path Portability Sentinel."""

    gate_id = 2
    name = "Gate 2: Path Portability"
    key = "gate_2_path_portability"

    def run(self, repo_root: str, mode: str = "AUTO", **kwargs) -> bool:
        fast = kwargs.get("fast", False)
        return gate_2_path_portability(repo_root, mode=mode, fast=fast)
