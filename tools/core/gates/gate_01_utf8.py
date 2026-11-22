#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Gate 1: UTF-8 No BOM & Clean Encoding Integrity Sentinel.
Verifies 100% UTF-8 encoding with zero Byte Order Mark (BOM) bytes and zero corrupted control characters.
"""

import os
from typing import List

from tools.core.gates.base import (
    BaseGate,
    BOM_EXTENSIONS,
    MOJIBAKE_INDICATORS,
    get_scoped_git_files,
)


def gate_1_bom_check(repo_root: str, mode: str = "AUTO", fast: bool = False) -> bool:
    """Gate 1: Verifies 100% UTF-8 encoding with zero Byte Order Mark (BOM) bytes and zero corrupted control characters."""
    print("\n[GATE 1] Scanning UTF-8 No BOM and Encoding Integrity across repository...")
    ignored_dirs = {
        ".git", ".gradle", "node_modules", "allure-results", "graphify-out",
        "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache",
        "build", "dist", "claude-ecosystem-repos", "external_repos", "reference_repos",
        "teamwork", ".synapse", ".sandbox_snapshots", "agent_qa.egg-info", "synapse_hub.egg-info"
    }
    ignored_files = {"verify_all.py", "test_tools.py", "base.py"}
    bom_violations: List[str] = []
    mojibake_violations: List[str] = []

    files_to_check = None
    if fast:
        scoped = get_scoped_git_files(repo_root, staged_only=True)
        if scoped is not None:
            files_to_check = scoped
            if not files_to_check:
                print("[PASS] [FAST MODE] Zero staged/changed files detected. Gate 1 instant pass.")
                return True

    if files_to_check is not None:
        # Fast path: only iterate scoped git files (zero os.walk)
        for rel_path in files_to_check:
            parts = rel_path.split("/")
            if any(p in ignored_dirs or p.endswith(".egg-info") or p.startswith(("synapse_hub-", "synapse-hub-", ".temp-")) for p in parts[:-1]):
                continue
            filename = parts[-1]
            if filename in ignored_files or not filename.endswith(BOM_EXTENSIONS):
                continue
            full_path = os.path.join(repo_root, *parts)
            if not os.path.isfile(full_path):
                continue
            try:
                with open(full_path, "rb") as fp:
                    raw = fp.read()
                    if raw[:3] == b"\xef\xbb\xbf":
                        bom_violations.append(rel_path)
                try:
                    text = raw.decode("utf-8")
                    if any(ind in text for ind in MOJIBAKE_INDICATORS):
                        mojibake_violations.append(rel_path)
                    bad_ctrl = [c for c in text if ord(c) < 32 and c not in ("\n", "\r", "\t")]
                    if bad_ctrl:
                        mojibake_violations.append(f"{rel_path} (Contains {len(bad_ctrl)} corrupted control char(s) e.g. {repr(bad_ctrl[0])})")
                except UnicodeDecodeError:
                    mojibake_violations.append(f"{rel_path} (Invalid UTF-8 decode)")
            except (OSError, PermissionError):
                continue
    else:
        # Full repository scan via os.walk
        for root, dirs, files in os.walk(repo_root):
            dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.endswith(".egg-info") and not d.startswith(("synapse_hub-", "synapse-hub-", ".temp-"))]
            for f in files:
                if f.endswith(BOM_EXTENSIONS):
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, repo_root)
                    if f in ignored_files:
                        continue
                    try:
                        with open(full_path, "rb") as fp:
                            raw = fp.read()
                            if raw[:3] == b"\xef\xbb\xbf":
                                bom_violations.append(rel_path)
                        try:
                            text = raw.decode("utf-8")
                            if any(ind in text for ind in MOJIBAKE_INDICATORS):
                                mojibake_violations.append(rel_path)
                            bad_ctrl = [c for c in text if ord(c) < 32 and c not in ("\n", "\r", "\t")]
                            if bad_ctrl:
                                mojibake_violations.append(f"{rel_path} (Contains {len(bad_ctrl)} corrupted control char(s) e.g. {repr(bad_ctrl[0])})")
                        except UnicodeDecodeError:
                            mojibake_violations.append(f"{rel_path} (Invalid UTF-8 decode)")
                    except (OSError, PermissionError):
                        continue

    failed = False
    if bom_violations:
        print(f"[FAIL] {len(bom_violations)} files contain UTF-8 BOM bytes:")
        for v in bom_violations:
            print(f"   - {v}")
        failed = True
    if mojibake_violations:
        print(f"[FAIL] {len(mojibake_violations)} files contain Mojibake / Corrupted Encoding:")
        for v in mojibake_violations:
            print(f"   - {v}")
        failed = True

    if failed:
        return False

    if fast and files_to_check is not None:
        print(f"[PASS] [FAST MODE] 100% UTF-8 No BOM & Clean Encoding verified across {len(files_to_check)} scoped file(s).")
    else:
        print("[PASS] 100% UTF-8 No BOM & Clean Encoding verified across all source files.")
    return True


class Gate01UTF8(BaseGate):
    """Gate 1: UTF-8 No BOM & Clean Encoding Sentinel."""

    gate_id = 1
    name = "Gate 1: UTF-8 No BOM"
    key = "gate_1_bom_check"

    def run(self, repo_root: str, mode: str = "AUTO", **kwargs) -> bool:
        fast = kwargs.get("fast", False)
        return gate_1_bom_check(repo_root, mode=mode, fast=fast)
