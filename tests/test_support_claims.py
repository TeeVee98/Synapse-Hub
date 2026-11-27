#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_support_claims.py
Validates that published support claims in docs/CLIENT_SUPPORT_MATRIX.md and
TEST_INFRA.md reference valid repository paths, evidence-backed versions/dates/runs,
and executable smoke commands in an isolated clean temporary directory.
"""

from pathlib import Path
import re
import shutil
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
_PATH_TOKEN_RE = re.compile(r"`((?:tests|tools|docs)/[A-Za-z0-9_./-]+\.(?:py|md))`")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_doc_paths(doc_text: str, repo_root: Path) -> list[str]:
    """Returns any missing repository paths cited in markdown backticks."""
    missing: list[str] = []
    for match in _PATH_TOKEN_RE.findall(doc_text):
        target = repo_root / match
        if not target.exists():
            missing.append(match)
    return sorted(set(missing))


def validate_support_matrix_claims(matrix_text: str, repo_root: Path) -> list[str]:
    """Verifies every row marked Verified includes non-empty Version, ISO Date, existing Run Reference, and Scope."""
    errors: list[str] = []
    table_rows = 0
    for raw_line in matrix_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 6 or cells[0].startswith(":---") or "Client Host" in cells[0]:
            continue
        table_rows += 1
        host = cells[0].strip("* ")
        state = cells[1].strip("* ").lower()
        version = cells[2].strip("` ")
        ev_date = cells[3].strip("` ")
        run_ref = cells[4].strip()
        scope = cells[5].strip()
        if state == "verified":
            if not version or version.upper() == "N/A":
                errors.append(f"{host}: Verified row missing explicit version")
            if not _DATE_RE.match(ev_date):
                errors.append(f"{host}: Verified row missing ISO date YYYY-MM-DD ({ev_date!r})")
            ref_paths = re.findall(r"`([^`]+)`", run_ref)
            if not ref_paths:
                errors.append(f"{host}: Verified row lacks concrete run reference path")
            for rp in ref_paths:
                if not (repo_root / rp).exists():
                    errors.append(f"{host}: Verified run reference path missing: {rp}")
            if len(scope) < 10:
                errors.append(f"{host}: Verified row lacks explicit scope description")
    if table_rows == 0:
        errors.append("Support matrix contains zero host rows")
    return errors


def test_docs_paths_and_evidence_backed_support_matrix_pass(tmp_path):
    """Positive: TEST_INFRA.md paths exist, Verified rows carry version/date/run/scope, and smoke setup works."""
    infra_text = (REPO_ROOT / "TEST_INFRA.md").read_text(encoding="utf-8")
    matrix_text = (REPO_ROOT / "docs" / "CLIENT_SUPPORT_MATRIX.md").read_text(encoding="utf-8")

    assert validate_doc_paths(infra_text, REPO_ROOT) == []
    assert validate_support_matrix_claims(matrix_text, REPO_ROOT) == []
    assert "test_autonomous_reasoning_e2e.py" not in infra_text

    # Run documented smoke & setup commands against a clean temporary client directory
    node_bin = shutil.which("node")
    assert node_bin is not None
    help_res = subprocess.run(
        [node_bin, str(REPO_ROOT / "bin" / "agent-qa.js"), "--help"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert help_res.returncode == 0, help_res.stderr

    setup_res = subprocess.run(
        [node_bin, str(REPO_ROOT / "bin" / "agent-qa.js"), "setup", "--ide", "codex", "--target", str(tmp_path)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert setup_res.returncode == 0, setup_res.stderr
    assert (tmp_path / "AGENTS.md").is_file()
    assert (tmp_path / ".codex" / "config.toml").is_file()

    py_help = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "core" / "cli.py"), "--help"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert py_help.returncode == 0, py_help.stderr


def test_negative_dead_path_config_only_verified_and_missing_command():
    """Negative: Dead path, config-only Verified row, and missing command each fail validation."""
    dead_errors = validate_doc_paths("Run `tests/e2e/test_autonomous_reasoning_e2e.py`.", REPO_ROOT)
    assert dead_errors == ["tests/e2e/test_autonomous_reasoning_e2e.py"]

    fake_matrix = (
        "| Client Host | Support State | Version | Evidence Date | Run Reference | Verified Scope & Caveats |\n"
        "| :--- | :---: | :--- | :---: | :--- | :--- |\n"
        "| **ExampleIDE** | **Verified** | `` | `N/A` | `.example_config` | Config file only |\n"
    )
    claim_errors = validate_support_matrix_claims(fake_matrix, REPO_ROOT)
    assert len(claim_errors) >= 3

    assert shutil.which("nonexistent-synapse-cmd-xyz") is None
    with open(REPO_ROOT / "package.json", "r", encoding="utf-8") as fh:
        assert fh.read()  # sanity anchor alongside failed lookup
    proc_exc = None
    try:
        subprocess.run(["nonexistent-synapse-cmd-xyz"], capture_output=True, text=True, timeout=5)
    except FileNotFoundError as exc:
        proc_exc = exc
    assert proc_exc is not None


def test_boundary_empty_matrix_and_pending_rows():
    """Boundary: Empty matrix fails while explicit Pending/Config-Only rows pass without fake Verified status."""
    assert validate_support_matrix_claims("# Empty\n", REPO_ROOT) == ["Support matrix contains zero host rows"]

    pending_matrix = (
        "| Client Host | Support State | Version | Evidence Date | Run Reference | Verified Scope & Caveats |\n"
        "| :--- | :---: | :--- | :---: | :--- | :--- |\n"
        "| **FutureHost** | **Pending** | `4.10.0` | `2026-11-27` | `N/A` | Awaiting live receipt |\n"
    )
    assert validate_support_matrix_claims(pending_matrix, REPO_ROOT) == []
