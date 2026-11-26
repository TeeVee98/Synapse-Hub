#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
"""4-scenario test suite for benchmarks/real_world_fpr_runner.py."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# 1. POSITIVE SCENARIOS
# ---------------------------------------------------------------------------


def test_positive_real_world_repo_benchmark_passes_fpr_recall_and_latency() -> None:
    """Running FPR benchmark across Synapse Hub's 8 examples/ suites + Clean POM corpus meets all SLAs."""
    from benchmarks.real_world_fpr_runner import (
        RealWorldBenchmarkReceiptDTO,
        run_fpr_benchmark,
    )

    receipt = run_fpr_benchmark(str(REPO_ROOT), max_fpr_pct=5.0, max_p95_ms=50.0)
    assert isinstance(receipt, RealWorldBenchmarkReceiptDTO)
    assert receipt.total_cases >= 10
    assert receipt.true_positives >= 5
    assert receipt.false_positive_rate_pct <= 5.0
    assert receipt.recall_pct >= 95.0
    assert receipt.p95_scan_ms <= 50.0
    assert receipt.passed is True

    with pytest.raises(FrozenInstanceError):
        receipt.passed = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 2. NEGATIVE SCENARIOS
# ---------------------------------------------------------------------------


def test_negative_corrupted_fixture_and_impossible_threshold_handled_safely(tmp_path: Path) -> None:
    """Corrupted binary/syntax fixtures do not crash runner; strict impossible threshold fails cleanly."""
    from benchmarks.real_world_fpr_runner import run_fpr_benchmark

    ex_dir = tmp_path / "examples" / "broken-suite" / "tests"
    ex_dir.mkdir(parents=True)
    # Write a clean file plus a syntax-corrupted file
    (ex_dir / "valid.spec.ts").write_text(
        "test('ok', async ({ page }) => { await expect(page.locator('#x')).toBeVisible(); });\n",
        encoding="utf-8",
    )
    (ex_dir / "corrupt.py").write_bytes(b"\xff\xfe\x00def broken(:\n    assert True\n")

    receipt = run_fpr_benchmark(str(tmp_path), max_fpr_pct=0.0, max_p95_ms=50.0, include_adversarial_corpus=False)
    assert receipt.total_cases >= 1
    assert receipt.false_positives >= 1
    assert receipt.passed is False


# ---------------------------------------------------------------------------
# 3. BOUNDARY SCENARIOS
# ---------------------------------------------------------------------------


def test_boundary_empty_corpus_and_missing_root(tmp_path: Path) -> None:
    """Empty workspace and non-existent root with adversarial corpus disabled return 0 cases safely."""
    from benchmarks.real_world_fpr_runner import run_fpr_benchmark

    empty_receipt = run_fpr_benchmark(str(tmp_path), include_adversarial_corpus=False)
    assert empty_receipt.total_cases == 0
    assert empty_receipt.false_positives == 0
    assert empty_receipt.false_positive_rate_pct == 0.0
    assert empty_receipt.passed is True

    missing_receipt = run_fpr_benchmark(str(tmp_path / "nonexistent"), include_adversarial_corpus=False)
    assert missing_receipt.total_cases == 0
    assert missing_receipt.passed is True


# ---------------------------------------------------------------------------
# 4. CLI FLAGS & JSON/MARKDOWN RECEIPT SCENARIOS
# ---------------------------------------------------------------------------


def test_cli_flags_json_max_fpr_and_markdown_export(tmp_path: Path) -> None:
    """CLI supports --root, --max-fpr, --max-p95-ms, --json, and --out receipt export."""
    script = REPO_ROOT / "benchmarks" / "real_world_fpr_runner.py"
    md_out = tmp_path / "fpr_report.md"
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--root",
            str(REPO_ROOT),
            "--max-fpr",
            "5.0",
            "--max-p95-ms",
            "50.0",
            "--out",
            str(md_out),
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
    data = json.loads(proc.stdout)
    assert data["passed"] is True
    assert data["false_positive_rate_pct"] <= 5.0
    assert data["recall_pct"] >= 95.0
    assert md_out.is_file()
    assert "False-Positive Rate" in md_out.read_text(encoding="utf-8")
