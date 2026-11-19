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
from typing import List

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
    print("[PASS] Temporary file blacklist is clean.")
    return True


class Gate05Blacklist(BaseGate):
    """Gate 5: Temporary Files Blacklist Sentinel."""

    gate_id = 5
    name = "Gate 5: Temporary Files Blacklist"
    key = "gate_5_cleanup_blacklist"

    def run(self, repo_root: str, mode: str = "AUTO", **kwargs) -> bool:
        return gate_5_cleanup_blacklist(repo_root, mode=mode)
