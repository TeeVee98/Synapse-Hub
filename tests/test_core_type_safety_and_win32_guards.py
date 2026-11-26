#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
4-Scenario Verification Suite for M4-M9 & M11:
  - Permanent 145+ module strict `mypy` lock across core packages (`arg-type`, `attr-defined`, `return`)
  - Global coverage floor ratchet (`fail_under >= 70`) in `pyproject.toml`
  - Transparent Gate 11 `tier_classification` (`production_active: 9`, `offline_heuristic_simulation: 6`)
  - Runtime type-safety guards: `mcp_excel_server.normalize_template_rows`, Windows-safe `codeact_engine`
    subprocess timeout kill, and `benchmark_perf_runner` numeric latency aggregation.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from tools.core.gates.base import LAST_GATE_METRICS
from tools.core.gates.gate_11_token_reduction import gate_11_token_reduction
from tools.mcp.mcp_excel_server import normalize_template_rows
from tools.perf.benchmark_perf_runner import run_benchmark
from tools.runtime.codeact_engine import CodeActEngine

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 1. POSITIVE: Coverage floor >= 70, mypy overrides locked, Gate 11 transparency
# ---------------------------------------------------------------------------


def test_positive_pyproject_ratchet_and_gate11_simulation_classification() -> None:
    pyproject_text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    cov_match = re.search(
        r"\[tool\.coverage\.report\][^\[]*?fail_under\s*=\s*(\d+)",
        pyproject_text,
        re.DOTALL,
    )
    assert cov_match is not None, "Missing [tool.coverage.report] fail_under in pyproject.toml"
    assert int(cov_match.group(1)) >= 70

    for pkg in (
        "tools.core.*",
        "tools.lint.*",
        "tools.context.*",
        "tools.mcp.*",
        "tools.alm.*",
        "tools.transpiler.*",
        "tools.runtime.codeact_engine",
        "tools.perf.benchmark_perf_runner",
    ):
        assert pkg in pyproject_text, f"Missing strict mypy override for {pkg} in pyproject.toml"

    assert gate_11_token_reduction(str(REPO_ROOT), mode="HUB", fast=True) is True
    metrics = LAST_GATE_METRICS.get("gate_11", {})
    tc = metrics.get("tier_classification", {})
    assert len(tc.get("production_active", [])) == 9
    assert len(tc.get("offline_heuristic_simulation", [])) == 6
    assert tc.get("counts", {}).get("production_active") == 9
    assert tc.get("counts", {}).get("offline_heuristic_simulation") == 6


# ---------------------------------------------------------------------------
# 2. NEGATIVE: Simulated Windows timeout without os.killpg & malformed row payloads
# ---------------------------------------------------------------------------


def test_negative_codeact_win32_timeout_without_killpg_and_excel_malformed_rows(tmp_path: Path) -> None:
    engine = CodeActEngine()

    # Simulate Windows environment where os.killpg/os.getpgid are absent
    with patch.object(sys, "platform", "win32"), patch.object(os, "killpg", None, create=True):
        res = engine.execute_script("import time\ntime.sleep(5)\n", timeout=0.5)

    assert res["timed_out"] is True
    assert res["exit_code"] == 124
    assert "AttributeError" not in res["stderr"]
    assert "timed out" in res["stderr"].lower()

    # Non-list / malformed payloads do not raise AttributeError
    assert normalize_template_rows(None) == []
    assert normalize_template_rows("invalid-string") == []
    assert normalize_template_rows([123, None]) == []


# ---------------------------------------------------------------------------
# 3. BOUNDARY: mcp_excel_server list[list[str]] vs dict rows & benchmark_perf_runner
# ---------------------------------------------------------------------------


def test_boundary_excel_row_normalization_and_perf_benchmark_numeric_sum(tmp_path: Path) -> None:
    list_rows = [
        ["TC-001", "Verify login", "Pass"],
        ["TC-002", "Verify logout", "Pass"],
    ]
    norm_list = normalize_template_rows(list_rows)
    assert len(norm_list) == 2
    assert all(isinstance(r, dict) and r.get("type") == "case" for r in norm_list)
    assert norm_list[0]["testcase_id"] == "TC-001"
    assert norm_list[0]["col_1"] == "Verify login"

    dict_rows = [{"type": "section", "text": "Auth"}, {"type": "case", "testcase_id": "TC-010"}]
    norm_dict = normalize_template_rows(dict_rows)
    assert len(norm_dict) == 2
    assert len([r for r in norm_dict if r.get("type") == "case"]) == 1

    # Boundary: empty rows
    assert normalize_template_rows([]) == []

    # Benchmark runner numeric latency aggregation
    perf_res = run_benchmark(output_dir=str(tmp_path / "perf"), iterations=10, concurrency=2)
    assert perf_res["iterations"] == 10
    assert isinstance(perf_res["avg_ms"], (int, float))
    assert perf_res["avg_ms"] >= 0
    assert Path(perf_res["jtl_file"]).is_file()
    assert Path(perf_res["k6_file"]).is_file()


# ---------------------------------------------------------------------------
# 4. CLI CONTRACT: Permanent mypy zero-error check across all 6 core packages
# ---------------------------------------------------------------------------


def test_cli_mypy_zero_errors_across_all_six_core_packages() -> None:
    cmd = [
        sys.executable,
        "-m",
        "mypy",
        "--follow-imports=silent",
        "tools/core",
        "tools/lint",
        "tools/context",
        "tools/mcp",
        "tools/alm",
        "tools/transpiler",
        "tools/runtime/codeact_engine.py",
        "tools/perf/benchmark_perf_runner.py",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert proc.returncode == 0, f"Strict mypy failed across core packages:\n{proc.stdout}\n{proc.stderr}"
    assert "Success: no issues found" in proc.stdout
