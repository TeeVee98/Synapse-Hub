#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Gate 5: Cleanup Blacklist Sentinel.
Scans for prohibited temporary files, heap dumps, and local cache artifacts.
"""

import glob
import os
import subprocess
import sys
from typing import List

_GATES_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_GATES_DIR, "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.core.gates.base import BaseGate


def gate_5_cleanup_blacklist(repo_root: str, mode: str = "AUTO") -> bool:
    """Gate 5: Scans for prohibited temporary files, heap dumps, and local cache artifacts."""
    print("\n[GATE 5] Checking Temporary File Blacklist...")
    blacklist_patterns = [
        os.path.join(repo_root, "Reports", "batch*.properties"),
        os.path.join(repo_root, "*_debug.txt"),
        os.path.join(repo_root, "debug_output.txt"),
        os.path.join(repo_root, "*.tmp"),
        os.path.join(repo_root, ".temp-*"),
        os.path.join(repo_root, "*_tmp.db"),
        os.path.join(repo_root, "temp_*.db"),
        os.path.join(repo_root, "nonexistent_*.db"),
        os.path.join(repo_root, "*.heapsnapshot"),
        os.path.join(repo_root, "*.hprof"),
    ]
    # Allowed test artifact directories exempted from heap dump cleanups
    exempt_prefixes = (
        os.path.normpath(os.path.join(repo_root, "Reports", "perf")),
        os.path.normpath(os.path.join(repo_root, ".synapse", "heapsnapshots")),
    )
    found: List[str] = []
    for pattern in blacklist_patterns:
        for f in glob.glob(pattern):
            norm_f = os.path.normpath(f)
            if any(norm_f.startswith(prefix) for prefix in exempt_prefixes):
                continue
            if os.path.isfile(f):
                found.append(os.path.relpath(f, repo_root))

    if found:
        print(f"[FAIL] {len(found)} blacklisted temporary files found on disk:")
        for f in found:
            print(f"   - {f}")
        return False

    # Check for ephemeral debug breadcrumbs (@crumbs) in source files
    debug_crumbs_script = os.path.join(repo_root, "tools", "core", "debug_crumbs.py")
    if os.path.isfile(debug_crumbs_script):
        try:
            res_crumbs = subprocess.run(
                [sys.executable, debug_crumbs_script, "--check", "--json"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=15.0,
            )
            if res_crumbs.returncode != 0:
                print("[FAIL] Ephemeral debug breadcrumbs (@crumbs) detected in source code!")
                print("   Run 'python3 tools/core/debug_crumbs.py --strip' to clean them before committing.")
                return False
        except Exception as crumbs_err:
            sys.stderr.write(f"Warning running debug crumbs check: {crumbs_err}\n")

    print("[PASS] Temporary file blacklist is clean.")
    return True


def clean_blacklisted_files(repo_root: str) -> int:
    """Purges all blacklisted temporary files on disk (OpenAI Codex Entropy Sweeper)."""
    blacklist_patterns = [
        os.path.join(repo_root, "Reports", "batch*.properties"),
        os.path.join(repo_root, "*_debug.txt"),
        os.path.join(repo_root, "debug_output.txt"),
        os.path.join(repo_root, "*.tmp"),
        os.path.join(repo_root, ".temp-*"),
        os.path.join(repo_root, "*_tmp.db"),
        os.path.join(repo_root, "temp_*.db"),
        os.path.join(repo_root, "nonexistent_*.db"),
        os.path.join(repo_root, "*.heapsnapshot"),
        os.path.join(repo_root, "*.hprof"),
    ]
    exempt_prefixes = (
        os.path.normpath(os.path.join(repo_root, "Reports", "perf")),
        os.path.normpath(os.path.join(repo_root, ".synapse", "heapsnapshots")),
    )
    removed_count = 0
    for pattern in blacklist_patterns:
        for f in glob.glob(pattern):
            norm_f = os.path.normpath(f)
            if any(norm_f.startswith(prefix) for prefix in exempt_prefixes):
                continue
            if os.path.isfile(f):
                try:
                    os.remove(f)
                    removed_count += 1
                    print(f"   [PURGED] {os.path.relpath(f, repo_root)}")
                except OSError:  # synapse-ignore: SWALLOWED_EXCEPTION
                    pass
    return removed_count


class Gate05Blacklist(BaseGate):
    """Gate 5: Temporary Files Blacklist Sentinel."""

    gate_id = 5
    name = "Gate 5: Temporary Files Blacklist"
    key = "gate_5_cleanup_blacklist"

    def run(self, repo_root: str, mode: str = "AUTO", **kwargs) -> bool:
        return gate_5_cleanup_blacklist(repo_root, mode=mode)


if __name__ == "__main__":
    import sys
    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    if "--clean" in sys.argv:
        count = clean_blacklisted_files(_root)
        print(f"🧹 Purged {count} temporary entropy file(s).")
        sys.exit(0)
    success = gate_5_cleanup_blacklist(_root)
    sys.exit(0 if success else 1)
