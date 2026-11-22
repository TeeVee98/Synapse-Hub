#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Gate 4: AI Documentation & Artifact Linter.
Reconciles PROJECT_AI_GUIDE.md against physical AST to prevent hallucinated classes.
"""

import os
import subprocess
import sys

from tools.core.gates.base import (
    BaseGate,
    resolve_tool_path,
    safe_print,
)


def gate_4_ai_docs_lint(repo_root: str, mode: str = "AUTO") -> bool:
    """Gate 4: Reconciles PROJECT_AI_GUIDE.md against physical AST to prevent hallucinated classes."""
    print("\n[GATE 4] Running AI Documentation & Artifact Linter...")
    linter_script = resolve_tool_path(repo_root, "lint_ai_docs.py", "lint")
    if not os.path.exists(linter_script):
        print("[FAIL] lint_ai_docs.py not found in tools/!")
        return False

    try:
        res = subprocess.run(
            [sys.executable, linter_script, repo_root],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60.0,
        )
    except subprocess.TimeoutExpired:
        print("[FAIL] lint_ai_docs.py timed out after 60s!")
        return False

    if res.returncode != 0:
        safe_print(res.stdout)
        safe_print(res.stderr)
        return False

    # Check for Schema-First Zero Drift (Hub mode)
    schema_syncer = resolve_tool_path(repo_root, "sync_schemas.py", "core")
    if os.path.exists(schema_syncer):
        try:
            s_res = subprocess.run(
                [sys.executable, schema_syncer, "--check"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15.0,
            )
            if s_res.returncode != 0:
                print("[FAIL] Schema drift detected across JSON Schema, Python models, or TypeScript definitions!")
                safe_print(s_res.stdout)
                safe_print(s_res.stderr)
                return False
        except subprocess.TimeoutExpired:
            print("[FAIL] sync_schemas.py timed out!")
            return False

    print("[PASS] Zero documentation drift & Zero schema drift verified.")
    return True


class Gate04AIDocs(BaseGate):
    """Gate 4: AI Documentation & Artifact Linter."""

    gate_id = 4
    name = "Gate 4: AI Documentation Linter"
    key = "gate_4_ai_docs_lint"

    def run(self, repo_root: str, mode: str = "AUTO", **kwargs) -> bool:
        return gate_4_ai_docs_lint(repo_root, mode=mode)
