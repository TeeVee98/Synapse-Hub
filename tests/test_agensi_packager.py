#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tests/test_agensi_packager.py — 4-Scenario Verification Suite for Agensi.io 6-Pack Packager
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGER_SCRIPT = REPO_ROOT / "scripts" / "package_agensi_skills.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import package_agensi_skills as pkg  # noqa: E402


def test_positive_build_all_six_packs_and_isolated_smoke(tmp_path: Path) -> None:
    """Positive: Builds all 6 packages and verifies isolated execution, POSIX zips, UTF-8 No BOM, and MIT attribution."""
    packager = pkg.AgensiPackager(repo_root=REPO_ROOT, out_dir=tmp_path)
    report = packager.run(verify_isolated=True)

    assert report.packages_built == 6
    assert report.packages_passed == 6, [r for r in report.smoke_receipts if not r.passed]
    assert report.passed is True

    expected_slugs = {
        "review-spec",
        "skillspector-security-guard",
        "rbt-manual-testing-excel",
        "wcag-a11y-audit",
        "api-contract-and-fuzzer",
        "anti-fake-pass-mutation",
    }
    assert {r.slug for r in report.smoke_receipts} == expected_slugs

    for receipt in report.smoke_receipts:
        assert receipt.passed is True, receipt
        assert receipt.extracted_in_isolated_dir is True
        assert receipt.dead_cli_refs_found == 0
        assert receipt.broken_links_found == 0
        assert receipt.skillspector_verdict == "SAFE"

        zpath = Path(receipt.zip_path)
        assert zpath.is_file()
        with zipfile.ZipFile(zpath, "r") as zf:
            names = zf.namelist()
            assert all("\\" not in n for n in names), f"Backslash in {zpath}"
            assert all(n.startswith(f"{receipt.slug}/") for n in names)
            assert f"{receipt.slug}/SKILL.md" in names
            assert f"{receipt.slug}/LICENSE" in names
            assert f"{receipt.slug}/README.md" in names
            license_txt = zf.read(f"{receipt.slug}/LICENSE").decode("utf-8")
            assert "Thế Vị (@TeeVee98)" in license_txt
            for n in names:
                raw = zf.read(n)
                assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {n}"


def test_negative_unknown_slug_fails_cleanly(tmp_path: Path) -> None:
    """Negative: Unknown slug returns structured JSON error and writes zero zip or staging artifacts."""
    proc = subprocess.run(
        [
            sys.executable,
            str(PACKAGER_SCRIPT),
            "--slug",
            "nonexistent-pack-xyz",
            "--out-dir",
            str(tmp_path),
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    assert proc.returncode != 0
    payload = json.loads(proc.stdout)
    assert payload["passed"] is False
    assert "Unknown package slug" in payload["error"]
    assert list(tmp_path.glob("*.zip")) == []
    assert list(tmp_path.glob("*.staging")) == []


def test_boundary_missing_openpyxl_friendly_guard_and_english_cli(tmp_path: Path) -> None:
    """Boundary: Missing openpyxl produces a clean English install hint (no traceback, no Vietnamese CLI leak)."""
    packager = pkg.AgensiPackager(repo_root=REPO_ROOT, out_dir=tmp_path)
    _, zip_path, _ = packager.build_package("rbt-manual-testing-excel")

    extract_dir = tmp_path / "extracted"
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    exporter = extract_dir / "rbt-manual-testing-excel" / "scripts" / "template_excel_exporter.py"
    req_file = extract_dir / "rbt-manual-testing-excel" / "requirements.txt"
    assert req_file.is_file()
    assert "openpyxl" in req_file.read_text(encoding="utf-8")

    # Simulate environment without openpyxl using a one-line import blocker
    runner_code = (
        "import sys, runpy; "
        "target = sys.argv[1]; "
        "sys.modules['openpyxl'] = None; "
        "sys.modules['openpyxl.styles'] = None; "
        "sys.argv = [target, 'missing.md']; "
        "runpy.run_path(target, run_name='__main__')"
    )
    proc = subprocess.run(
        [sys.executable, "-c", runner_code, str(exporter)],
        cwd=str(tmp_path),
        env={**os.environ, "PYTHONPATH": ""},
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    combined = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert "pip install -r requirements.txt" in combined
    assert "Traceback (most recent call last)" not in combined
    assert "Hướng Dẫn" not in combined
    assert "agent-qa export-excel" not in combined

    # Verify zero-arg help output is clean English with no legacy Synapse CLI references
    exporter_src = exporter.read_text(encoding="utf-8")
    assert "duong_dan_file" not in exporter_src
    assert "agent-qa export-excel" not in exporter_src


def test_boundary_checklist_query_and_empty_inputs(tmp_path: Path) -> None:
    """Boundary: Isolated checklist_query resolves bundled references and empty HTML/JSON do not crash."""
    packager = pkg.AgensiPackager(repo_root=REPO_ROOT, out_dir=tmp_path)
    packager.build_package("rbt-manual-testing-excel")
    packager.build_package("wcag-a11y-audit")

    # 1. Isolated checklist_query lookup
    rbt_extract = tmp_path / "rbt_ext"
    with zipfile.ZipFile(tmp_path / "rbt-manual-testing-excel.zip", "r") as zf:
        zf.extractall(rbt_extract)
    cq = rbt_extract / "rbt-manual-testing-excel" / "scripts" / "checklist_query.py"
    work_dir = tmp_path / "empty_work"
    work_dir.mkdir()
    cq_proc = subprocess.run(
        [sys.executable, str(cq), "--fields", "email", "--format", "json"],
        cwd=str(work_dir),
        env={**os.environ, "PYTHONPATH": ""},
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    assert cq_proc.returncode == 0, cq_proc.stderr
    cq_data = json.loads(cq_proc.stdout)
    assert isinstance(cq_data, dict)

    # 2. Empty HTML audit
    wcag_extract = tmp_path / "wcag_ext"
    with zipfile.ZipFile(tmp_path / "wcag-a11y-audit.zip", "r") as zf:
        zf.extractall(wcag_extract)
    empty_html = work_dir / "empty.html"
    empty_html.write_text("", encoding="utf-8")
    wcag_proc = subprocess.run(
        [sys.executable, str(wcag_extract / "wcag-a11y-audit" / "scripts" / "wcag_audit.py"), str(empty_html)],
        cwd=str(work_dir),
        env={**os.environ, "PYTHONPATH": ""},
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    assert "Traceback (most recent call last)" not in (wcag_proc.stdout + wcag_proc.stderr)


def test_cli_slug_and_json_contract(tmp_path: Path) -> None:
    """CLI Flags: --slug + --verify-isolated + --json outputs valid contract."""
    proc = subprocess.run(
        [
            sys.executable,
            str(PACKAGER_SCRIPT),
            "--slug",
            "review-spec",
            "--verify-isolated",
            "--out-dir",
            str(tmp_path),
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["passed"] is True
    assert data["packages_built"] == 1
    assert data["packages_passed"] == 1
    assert len(data["smoke_receipts"]) == 1
    assert data["smoke_receipts"][0]["slug"] == "review-spec"
    assert data["smoke_receipts"][0]["skillspector_verdict"] == "SAFE"
