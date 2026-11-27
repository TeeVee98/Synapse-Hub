# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""Four-scenario regression tests for CLI schema parity, ADR-0029, and code backward compatibility (M5)."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.manual.manual_pipeline_adapter import detect_plan_profile


def test_cli_schema_and_code_compat_positive() -> None:
    """Positive: tools_schema.json declares --profile/--spec and ADR-0029 exists."""
    schema_path = os.path.join(REPO_ROOT, "tools", "tools_schema.json")
    data = json.loads(open(schema_path, "r", encoding="utf-8").read())
    tools_map = data["tools"]

    for tool_name in ("plan_schema_sentinel", "super_plan_engine", "solo_runner", "senior_code_review"):
        assert "--profile" in tools_map[tool_name]["args"], f"Missing --profile in tools_schema.json::{tool_name}"
    assert "--spec" in tools_map["solo_runner"]["args"], "Missing --spec in tools_schema.json::solo_runner"

    adr_path = os.path.join(REPO_ROOT, "docs", "adr", "ADR-0029-manual-qa-pipeline-profile.md")
    assert os.path.isfile(adr_path), "Missing ADR-0029-manual-qa-pipeline-profile.md"
    adr_text = open(adr_path, "r", encoding="utf-8").read()
    assert "--profile manual" in adr_text
    assert "manual_pipeline_adapter.py" in adr_text


def test_cli_schema_and_code_compat_negative() -> None:
    """Negative: Unsupported --profile values fail closed with non-zero exit code."""
    for script in (
        os.path.join(REPO_ROOT, "tools", "lint", "plan_schema_sentinel.py"),
        os.path.join(REPO_ROOT, "tools", "orchestration", "senior_code_review.py"),
    ):
        proc = subprocess.run(
            [sys.executable, script, "--profile", "unsupported_profile"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        assert proc.returncode != 0


def test_cli_schema_and_code_compat_boundary() -> None:
    """Boundary: Empty or default profile inputs always resolve cleanly to backward-compatible 'code'."""
    assert detect_plan_profile("", "auto") == "code"
    assert detect_plan_profile("   ", "") == "code"
    assert detect_plan_profile("# Standard Plan\nNo manual tag", "auto") == "code"


def test_cli_schema_and_code_compat_resilience_leaf_acyclicity() -> None:
    """Resilience/CLI: Leaf adapter has zero orchestrator imports and cli_schema_sentinel passes."""
    adapter_path = os.path.join(REPO_ROOT, "tools", "manual", "manual_pipeline_adapter.py")
    tree = ast.parse(open(adapter_path, "r", encoding="utf-8").read(), filename=adapter_path)
    forbidden = {"solo_runner", "plan_review_auditor", "senior_code_review", "super_plan_engine"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(f in alias.name for f in forbidden)
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not any(f in node.module for f in forbidden)

    proc = subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "tools", "lint", "cli_schema_sentinel.py"), "--check", "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
