# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""Four-scenario test suite for /super-plan --profile manual (M2)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.design.super_plan_engine import (
    calculate_risk_routing,
    check_ambiguities,
    scaffold_super_plan,
)
from tools.lint.plan_schema_sentinel import validate_plan_content


SAMPLE_SPEC = """# Feature: Checkout Payment & OTP

## Actor & Preconditions
- As a registered customer
- Precondition: Active cart with items and valid email/password credentials.

## Business Rules & Acceptance Criteria
- AC-01: Customer logs in with email and password and receives HTTP 200.
- AC-02: Invalid email or short password rejected with HTTP 400.
- AC-03: Expired OTP locked after 5 failed attempts with HTTP 429.
"""


def test_super_plan_manual_positive_scaffold_and_validate(tmp_path: Path) -> None:
    """Positive: Manual profile scaffolds spec-grounded plan and passes sentinel auto/manual validation."""
    spec_file = tmp_path / "docs" / "checkout_brd.md"
    spec_file.parent.mkdir(parents=True, exist_ok=True)
    spec_file.write_text(SAMPLE_SPEC, encoding="utf-8")

    plan_md = scaffold_super_plan(
        task="Design Manual QA test suite for checkout payment and OTP",
        target_files=["docs/checkout_brd.md", "docs/checkout_testcases.md"],
        profile="manual",
        repo_root=str(tmp_path),
    )
    assert "Profile:" in plan_md and "manual" in plan_md.lower()
    assert "AC-01" in plan_md and "AC-02" in plan_md and "AC-03" in plan_md
    assert "manual_tc_linter.py" in plan_md
    assert "Golden Ratio" in plan_md
    assert "src/target_module.py" not in plan_md

    passed_auto, issues_auto, details_auto = validate_plan_content(
        plan_md, filename="manual_plan.md", mode="super", profile="auto"
    )
    assert passed_auto is True, f"Unexpected auto-manual validation issues: {issues_auto}"
    assert details_auto["profile"] == "manual"

    passed_explicit, issues_explicit, details_explicit = validate_plan_content(
        plan_md, filename="manual_plan.md", mode="super", profile="manual"
    )
    assert passed_explicit is True, f"Unexpected explicit-manual issues: {issues_explicit}"
    assert details_explicit["profile"] == "manual"

    amb = check_ambiguities("Checkout payment with OTP and currency pricing rounding", profile="manual")
    assert len(amb) >= 1
    assert any(q.get("category") in ("manual_pricing_rounding", "manual_otp_lockout", "manual_rbac_roles") for q in amb)

    tier, metric = calculate_risk_routing(
        "Manual QA for checkout payment and OTP",
        ["docs/checkout_brd.md", "docs/checkout_testcases.md"],
        repo_root=str(tmp_path),
        profile="manual",
    )
    assert metric.risk_score >= 0.0
    assert tier is not None


def test_super_plan_manual_negative_rejects_vague_or_incomplete_manual_plan(tmp_path: Path) -> None:
    """Negative: Vague manual plan missing AC IDs, Golden Ratio, or manual linter Pass Gate fails."""
    vague_manual_plan = """# Manual QA Plan
> **Profile:** `manual`

## 1. Affected Files & Blast Radius
| `[CREATE]` | `docs/test_cases.md` (New) | Test cases |

## 2. Data Flow & Interface Signatures
Coverage plan without concrete requirements.

## 3. Atomic Milestones (Execution DAG)
### Milestone 1: Write Cases
- **Node ID:** `M1`
- **depends_on:** `[]`
- **Compute Tier:** `[Model: Flash | Thinking: Medium]`
- **Write Set:** `['docs/test_cases.md']`
- **Circuit Breaker:** `max_fix_attempts: 2`
- **Rollback Hook:** `git checkout -- docs/test_cases.md`
- **Pass Gate:** `manually test feature`

## 4. Verification Matrix
| TC-01 | Positive | manually test feature | looks fine | TBD |

## 5. Tri-Vulnerability Self-Critique
- race condition, boundary, backward compatibility
"""
    passed, issues, details = validate_plan_content(
        vague_manual_plan, filename="vague_manual.md", mode="super", profile="manual"
    )
    assert passed is False
    assert details["profile"] == "manual"
    joined = "\n".join(issues).lower()
    assert "golden ratio" in joined or "requirement" in joined or "ac-" in joined
    assert "manually test feature" in joined or "verification" in joined

    with pytest.raises(ValueError):
        scaffold_super_plan("Bad profile task", profile="invalid_prof", repo_root=str(tmp_path))


def test_super_plan_manual_boundary_empty_inputs(tmp_path: Path) -> None:
    """Boundary: Empty target_files in manual scaffold and empty content in validator handled safely."""
    plan_md = scaffold_super_plan(
        task="Manual QA baseline",
        target_files=[],
        profile="manual",
        repo_root=str(tmp_path),
    )
    assert "Profile:" in plan_md and "manual" in plan_md.lower()
    assert "src/target_module.py" not in plan_md
    assert "manual_tc_linter.py" in plan_md

    passed, issues, _ = validate_plan_content("", filename="empty.md", mode="super", profile="manual")
    assert passed is False
    assert len(issues) >= 1


def test_super_plan_manual_resilience_cli_and_code_compat(tmp_path: Path) -> None:
    """Resilience/CLI: CLI --profile manual works end-to-end and default code profile stays intact."""
    spec_file = tmp_path / "docs" / "checkout_brd.md"
    spec_file.parent.mkdir(parents=True, exist_ok=True)
    spec_file.write_text(SAMPLE_SPEC, encoding="utf-8")
    out_plan = tmp_path / "manual_plan.md"

    scaff_proc = subprocess.run(
        [
            sys.executable,
            os.path.join(REPO_ROOT, "tools", "design", "super_plan_engine.py"),
            "scaffold",
            "--task",
            "Manual QA for checkout payment",
            "--profile",
            "manual",
            "--files",
            "docs/checkout_brd.md",
            "docs/checkout_tc.md",
            "--repo-root",
            str(tmp_path),
            "--output",
            str(out_plan),
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert scaff_proc.returncode == 0, scaff_proc.stderr
    scaff_data = json.loads(scaff_proc.stdout)
    assert scaff_data["profile"] == "manual"
    assert out_plan.is_file()

    lint_proc = subprocess.run(
        [
            sys.executable,
            os.path.join(REPO_ROOT, "tools", "lint", "plan_schema_sentinel.py"),
            "--file",
            str(out_plan),
            "--mode",
            "super",
            "--profile",
            "manual",
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert lint_proc.returncode == 0, lint_proc.stdout + lint_proc.stderr
    lint_data = json.loads(lint_proc.stdout)
    assert lint_data["passed"] is True
    assert lint_data["results"][0]["details"]["profile"] == "manual"

    # Backward compatibility: default code profile still emits pytest verification
    code_plan = scaffold_super_plan(
        task="Implement rate limiter",
        target_files=["tools/core/agent_runner.py", "tests/test_agent_runner.py"],
        repo_root=REPO_ROOT,
    )
    assert "pytest" in code_plan
    assert "**Profile:** `manual`" not in code_plan


def test_super_plan_manual_run_pipeline_forwards_profile(tmp_path: Path) -> None:
    """Regression: run-pipeline --profile manual forwards profile through all stages instead of falling back to code."""
    spec_file = tmp_path / "docs" / "catalog_brd.md"
    spec_file.parent.mkdir(parents=True, exist_ok=True)
    spec_file.write_text(
        "# Feature: Catalog Search\n## Actor\n- As a customer\n- Precondition: Catalog indexed\n## Acceptance Criteria\n- AC-01: Search returns matching items.\n- AC-02: Empty query returns HTTP 400.\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "pipeline_out"
    proc = subprocess.run(
        [
            sys.executable,
            os.path.join(REPO_ROOT, "tools", "design", "super_plan_engine.py"),
            "run-pipeline",
            "--task",
            "Design Manual QA for catalog search",
            "--profile",
            "manual",
            "--files",
            "docs/catalog_brd.md",
            "docs/catalog_tc.md",
            "--repo-root",
            str(tmp_path),
            "--output",
            str(out_dir),
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    manifest = json.loads(proc.stdout)
    assert manifest["profile"] == "manual"
    assert manifest["passed"] is True
    plan_text = Path(manifest["plan_path"]).read_text(encoding="utf-8")
    assert "**Profile:** `manual`" in plan_text
    assert "manual_tc_linter.py" in plan_text
