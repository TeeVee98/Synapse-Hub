#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""Unit tests for tools/core/decision_log.py (4-Scenario Battery)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.core.decision_log import (
    DecisionRowDTO,
    append_decision_row,
    audit_decision_log,
    sanitize_tsv_cell,
)


def test_append_and_audit_positive(tmp_path: Path) -> None:
    """Positive: appending valid rows writes header once and passes audit."""
    log_file = tmp_path / "decisions.tsv"
    row1 = DecisionRowDTO(
        ts="2026-11-25T12:00:00Z",
        phase="M1",
        decision="Use stdlib csv/tsv writer",
        why="Zero external dependencies",
        evidence="tools/core/decision_log.py:L1",
        result="tests green",
    )
    row2 = DecisionRowDTO(
        ts="2026-11-25T12:05:00Z",
        phase="M1",
        decision="Add formula guard",
        why="Prevent CSV/TSV injection",
        evidence="tools/core/decision_log.py:L40",
        result="tests green",
    )
    assert append_decision_row(str(log_file), row1) is True
    assert append_decision_row(str(log_file), row2) is True
    assert log_file.is_file()

    # Verify frozen dataclass immutability
    with pytest.raises(Exception):
        row1.phase = "M2"  # type: ignore[misc]

    audit = audit_decision_log(str(log_file))
    assert audit["exists"] is True
    assert audit["valid"] is True
    assert audit["row_count"] == 2
    assert audit["issues"] == []


def test_negative_empty_required_fields_and_missing_log(tmp_path: Path) -> None:
    """Negative: empty/whitespace phase or decision raises ValueError; missing/empty/bad-header fail audit."""
    log_file = tmp_path / "missing.tsv"
    audit = audit_decision_log(str(log_file))
    assert audit["exists"] is False
    assert audit["valid"] is False
    assert audit["row_count"] == 0

    empty_file = tmp_path / "empty.tsv"
    empty_file.write_text("", encoding="utf-8")
    empty_audit = audit_decision_log(str(empty_file))
    assert empty_audit["exists"] is True
    assert empty_audit["valid"] is False

    bad_header = tmp_path / "bad_header.tsv"
    bad_header.write_text("a\tb\tc\td\te\tf\n1\t2\t3\t4\t5\t6\n", encoding="utf-8")
    assert audit_decision_log(str(bad_header))["valid"] is False

    for bad_phase, bad_dec in [("", "ok"), ("   ", "ok"), ("M1", ""), ("M1", "   ")]:
        bad_row = DecisionRowDTO(
            ts="2026-11-25T12:00:00Z",
            phase=bad_phase,
            decision=bad_dec,
            why="Reason",
            evidence="ref",
            result="open",
        )
        with pytest.raises(ValueError):
            append_decision_row(str(log_file), bad_row)


def test_boundary_sanitize_tsv_cell_and_malformed_row(tmp_path: Path) -> None:
    """Boundary: strips tabs/newlines and neutralizes spreadsheet formula prefixes."""
    assert sanitize_tsv_cell("hello\tworld\nline2\r") == "hello world line2"
    assert sanitize_tsv_cell("=CMD('calc')") == "'=CMD('calc')"
    assert sanitize_tsv_cell("+1+1") == "'+1+1"
    assert sanitize_tsv_cell("-rf") == "'-rf"
    assert sanitize_tsv_cell("@mention") == "'@mention"
    assert sanitize_tsv_cell("") == ""

    bad_log = tmp_path / "bad.tsv"
    bad_log.write_text("ts\tphase\tdecision\twhy\tevidence\tresult\nonly_two\tcols\n", encoding="utf-8")
    audit = audit_decision_log(str(bad_log))
    assert audit["valid"] is False
    assert len(audit["issues"]) == 1


def test_cli_append_and_audit_json(tmp_path: Path) -> None:
    """CLI: supports --json for both append and --audit modes."""
    log_file = tmp_path / "cli_decisions.tsv"
    append_proc = subprocess.run(
        [
            sys.executable,
            "tools/core/decision_log.py",
            "--log", str(log_file),
            "--phase", "frame",
            "--decision", "Picked TSV format",
            "--why", "Easy terminal diff",
            "--evidence", "commit abc123",
            "--result", "tests green",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert append_proc.returncode == 0
    append_payload = json.loads(append_proc.stdout)
    assert append_payload["appended"] is True

    audit_proc = subprocess.run(
        [
            sys.executable,
            "tools/core/decision_log.py",
            "--log", str(log_file),
            "--audit",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert audit_proc.returncode == 0
    audit_payload = json.loads(audit_proc.stdout)
    assert audit_payload["valid"] is True
    assert audit_payload["row_count"] == 1


def test_audit_rejects_empty_required_cells_and_strict_checks_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Audit flags empty required cells (ts/phase/decision/result) and --strict flags missing why/evidence."""
    from tools.core import decision_log

    empty_ts = tmp_path / "empty_ts.tsv"
    empty_ts.write_text(
        "ts\tphase\tdecision\twhy\tevidence\tresult\n"
        "\tM1\tKeep gate\treason\tref\tok\n",
        encoding="utf-8",
    )
    res_ts = audit_decision_log(str(empty_ts))
    assert res_ts["valid"] is False
    assert any("'ts'" in issue for issue in res_ts["issues"])

    empty_phase = tmp_path / "empty_phase.tsv"
    empty_phase.write_text(
        "ts\tphase\tdecision\twhy\tevidence\tresult\n"
        "2026-11-25T12:00:00Z\t\tKeep gate\treason\tref\tok\n",
        encoding="utf-8",
    )
    res_phase = audit_decision_log(str(empty_phase))
    assert res_phase["valid"] is False
    assert any("'phase'" in issue for issue in res_phase["issues"])

    # Appending to a pre-existing 0-byte file must still write the header
    precreated = tmp_path / "precreated_empty.tsv"
    precreated.write_text("", encoding="utf-8")
    append_decision_row(
        str(precreated),
        DecisionRowDTO(
            ts="2026-11-25T12:08:00Z",
            phase="M1",
            decision="Header on empty file",
            why="Pre-created file check",
            evidence="test_decision_log.py",
            result="ok",
        ),
    )
    assert audit_decision_log(str(precreated))["valid"] is True

    missing_evidence = tmp_path / "missing_evidence.tsv"
    append_decision_row(
        str(missing_evidence),
        DecisionRowDTO(
            ts="2026-11-25T12:10:00Z",
            phase="M2",
            decision="Adopt strict mode",
            why="",
            evidence="",
            result="open",
        ),
    )
    assert audit_decision_log(str(missing_evidence))["valid"] is True
    strict_res = audit_decision_log(str(missing_evidence), strict=True)
    assert strict_res["valid"] is False
    assert any("evidence" in issue.lower() for issue in strict_res["issues"])

    monkeypatch.setattr(
        "sys.argv",
        ["decision_log.py", "--log", str(missing_evidence), "--audit", "--strict", "--json"],
    )
    assert decision_log.main() == 1
    assert json.loads(capsys.readouterr().out)["valid"] is False


def test_concurrent_appends_preserve_single_header_and_all_rows(tmp_path: Path) -> None:
    """Concurrency: parallel writers do not duplicate headers or corrupt TSV lines."""
    from concurrent.futures import ThreadPoolExecutor

    log_file = tmp_path / "concurrent.tsv"

    def _write(idx: int) -> bool:
        return append_decision_row(
            str(log_file),
            DecisionRowDTO(
                ts="2026-11-25T12:15:00Z",
                phase=f"P{idx}",
                decision=f"Decision {idx}",
                why="Concurrency test",
                evidence=f"row-{idx}",
                result="ok",
            ),
        )

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(_write, range(12)))
    assert all(results)

    audit = audit_decision_log(str(log_file), strict=True)
    assert audit["valid"] is True
    assert audit["row_count"] == 12
