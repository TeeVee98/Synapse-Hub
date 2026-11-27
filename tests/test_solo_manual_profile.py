# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""Four-scenario test suite for /solo --profile manual and plan_dag_bridge (M3)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.design.super_plan_engine import scaffold_super_plan
from tools.manual.manual_pipeline_adapter import certify_manual_red_phase
from tools.orchestration.plan_dag_bridge import (
    compile_plan_to_solo_specs,
    execute_plan_via_solo,
)


SAMPLE_BRD = """# Feature: User Checkout Authentication

## Actor & Preconditions
- As a registered customer
- Precondition: Active account with email/password credentials and cart items.

## Business Rules & Acceptance Criteria
- AC-01: Customer logs in with registered email and password; returns HTTP 200.
- AC-02: System rejects malformed email or password shorter than 8 characters with HTTP 400.
- AC-03: System rejects expired OTP and locks account after 5 failed attempts with HTTP 429.
- AC-04: System blocks IDOR cross-user access via RBAC with HTTP 403 and guards double-submit race conditions.
"""

COMPLIANT_TCS = """<!-- synapse-linter-profile: auth-payment -->
# Manual Test Suite

| TC ID | REQ ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| TC-01 | AC-01 | Auth | High | Login with registered email and password | Active account seeded | 1. Open /login 2. Submit credentials | HTTP 200 returned and session token set | P0 | `u1@example.com` / `Str0ng!99` | Yes | API | @smoke @happy @req-ac-01 |
| TC-02 | AC-01 | Auth | Medium | Confirm OTP completes checkout | Valid OTP sent | 1. Enter 6-digit OTP 2. Submit | HTTP 200 returned and order summary displayed | P0 | `otp=123456` | Yes | API | @happy @req-ac-01 |
| TC-03 | AC-02 | Auth | High | Reject empty email and null password boundary | Unauthenticated user on /login | 1. Submit empty email and empty password | HTTP 400 validation error returned | P0 | `email=""`, `password=""` | Yes | API | @negative @boundary @req-ac-02 |
| TC-04 | AC-02 | Auth | High | Reject malformed email and 7-char password | Unauthenticated user on /login | 1. Submit invalid email and 7-char password | HTTP 400 returned stating min length 8 | P1 | `bad-email`, `Abc123!` | Yes | API | @negative @boundary @req-ac-02 |
| TC-05 | AC-02 | Auth | Medium | Reject 260-char Unicode IME email | Unauthenticated user on /login | 1. Paste 260-char Unicode IME string 2. Submit | HTTP 400 validation error returned safely | P1 | 260-char Unicode payload | Yes | API | @negative @boundary @unicode @req-ac-02 |
| TC-06 | AC-03 | Auth | Critical | Reject expired OTP and lock after 5 attempts | Expired OTP seeded | 1. Submit wrong OTP 5 times 2. Retry | HTTP 429 Too Many Requests and 15m lockout | P0 | `otp=000000` x5 | Yes | API | @negative @security @req-ac-03 |
| TC-07 | AC-04 | Security | Critical | Block IDOR cross-user access via RBAC | User A logged in; User B owns ORD-99 | 1. GET /api/v1/checkout/ORD-99 with User A token | HTTP 403 Forbidden with zero User B data | P0 | `order_id=ORD-99` | Yes | API | @security @rbac @idor @req-ac-04 |
| TC-08 | AC-04 | Security | Critical | Guard double-submit checkout race condition | User A on checkout confirm | 1. Click Pay twice within 100ms with same key | Single order created; 2nd returns HTTP 409 | P0 | `idem=k1` | Yes | API | @security @resilience @race @req-ac-04 |
| TC-09 | AC-02 | Security | High | Block SQL injection in password and email | Unauthenticated user on /login | 1. Submit SQLi string in email | HTTP 400 invalid email returned, zero DB leak | P1 | `' OR 1=1 --` | Yes | API | @security @req-ac-02 |
"""


def _run_solo_cli(cwd: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "tools", "orchestration", "solo_runner.py"), *extra_args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _setup_manual_repo(tmp_path: Path, brd: str = SAMPLE_BRD, tcs: str = COMPLIANT_TCS) -> tuple[Path, Path]:
    (tmp_path / ".git").mkdir(exist_ok=True)
    docs = tmp_path / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    spec_f = docs / "checkout_brd.md"
    tc_f = docs / "checkout_testcases.md"
    spec_f.write_text(brd, encoding="utf-8")
    tc_f.write_text(tcs, encoding="utf-8")
    return spec_f, tc_f


def test_solo_manual_positive_cli_loop(tmp_path: Path) -> None:
    """Positive: /solo --profile manual runs Red Spec-Hash, Green Linter+RTM, Spec-Mutation, and Purple."""
    spec_f, tc_f = _setup_manual_repo(tmp_path)

    red_proc = _run_solo_cli(
        tmp_path,
        "--profile", "manual",
        "--red",
        "--spec", str(spec_f),
        "--milestone", "M1",
        "--json",
    )
    assert red_proc.returncode == 0, red_proc.stdout + red_proc.stderr
    red_data = json.loads(red_proc.stdout)["red_phase"]
    assert red_data["status"] == "CERTIFIED_RED"
    assert red_data["profile"] == "manual"
    assert len(red_data["receipt_hmac"]) == 64

    green_proc = _run_solo_cli(
        tmp_path,
        "--profile", "manual",
        "--green",
        "--spec", str(spec_f),
        "--target", str(tc_f),
        "--milestone", "M1",
        "--json",
    )
    assert green_proc.returncode == 0, green_proc.stdout + green_proc.stderr
    green_data = json.loads(green_proc.stdout)["green_phase"]
    assert green_data["status"] == "CERTIFIED_GREEN"
    assert green_data["passed"] is True
    assert green_data["uncovered_req_ids"] == []

    mut_proc = _run_solo_cli(
        tmp_path,
        "--profile", "manual",
        "--mutation",
        "--spec", str(spec_f),
        "--target", str(tc_f),
        "--milestone", "M1",
        "--threshold", "80.0",
        "--json",
    )
    assert mut_proc.returncode == 0, mut_proc.stdout + mut_proc.stderr
    mut_data = json.loads(mut_proc.stdout)["mutation_phase"]
    assert mut_data["passed"] is True
    assert mut_data["mutation_score"] >= 80.0

    purple_proc = _run_solo_cli(
        tmp_path,
        "--profile", "manual",
        "--purple",
        "--spec", str(spec_f),
        "--target", str(tc_f),
        "--milestone", "M1",
        "--no-review",
        "--json",
    )
    assert purple_proc.returncode == 0, purple_proc.stdout + purple_proc.stderr
    purple_data = json.loads(purple_proc.stdout)["purple_phase"]
    assert purple_data["passed"] is True
    assert purple_data["profile"] == "manual"


def test_solo_manual_negative_weak_tcs_and_missing_spec(tmp_path: Path) -> None:
    """Negative: Weak test cases fail Green and Spec-Mutation; missing --spec fails Red cleanly."""
    weak_tcs = """<!-- synapse-linter-profile: default -->
| TC ID | REQ ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| TC-01 | AC-01 | Auth | Low | Basic login | User exists | 1. Login | Works properly as expected | P1 | valid data | No | Manual | @happy |
"""
    spec_f, tc_f = _setup_manual_repo(tmp_path, tcs=weak_tcs)

    no_spec = _run_solo_cli(tmp_path, "--profile", "manual", "--red", "--milestone", "M1", "--json")
    assert no_spec.returncode == 1
    assert json.loads(no_spec.stdout)["red_phase"]["passed"] is False

    bad_green = _run_solo_cli(
        tmp_path, "--profile", "manual", "--green", "--spec", str(spec_f), "--target", str(tc_f), "--milestone", "M1", "--json"
    )
    assert bad_green.returncode == 1
    assert json.loads(bad_green.stdout)["green_phase"]["passed"] is False

    bad_mut = _run_solo_cli(
        tmp_path, "--profile", "manual", "--mutation", "--spec", str(spec_f), "--target", str(tc_f), "--milestone", "M1", "--threshold", "80.0", "--json"
    )
    assert bad_mut.returncode == 1
    assert json.loads(bad_mut.stdout)["mutation_phase"]["passed"] is False


def test_solo_manual_boundary_empty_spec(tmp_path: Path) -> None:
    """Boundary: Empty BRD spec is rejected cleanly during --profile manual --red."""
    spec_f, _ = _setup_manual_repo(tmp_path, brd="")
    empty_red = _run_solo_cli(
        tmp_path, "--profile", "manual", "--red", "--spec", str(spec_f), "--milestone", "M1", "--json"
    )
    assert empty_red.returncode == 1
    payload = json.loads(empty_red.stdout)["red_phase"]
    assert payload["passed"] is False
    assert payload["status"] == "REJECTED_INVALID_SPEC"


def test_solo_manual_resilience_from_plan_bridge(tmp_path: Path) -> None:
    """Resilience/CLI: plan_dag_bridge auto-detects manual plans, enforces strict_red, and writes decisions.tsv."""
    spec_f, tc_f = _setup_manual_repo(tmp_path)
    plan_md = scaffold_super_plan(
        task="Checkout Manual QA",
        target_files=["docs/checkout_brd.md", "docs/checkout_testcases.md"],
        profile="manual",
        repo_root=str(tmp_path),
    )
    plan_file = tmp_path / "manual_plan.md"
    plan_file.write_text(plan_md, encoding="utf-8")

    specs = compile_plan_to_solo_specs(str(plan_file), repo_root=str(tmp_path), profile="auto")
    assert len(specs) >= 1

    # strict_red without prior Red receipt fails closed
    fail_summary = execute_plan_via_solo(
        plan_path=str(plan_file),
        repo_root=str(tmp_path),
        enforce_scope_guard=False,
        strict_red=True,
        auto_review=False,
        profile="auto",
    )
    assert fail_summary.passed is False

    # Certify Red for M1 and M2, then execute manual DAG bridge
    certify_manual_red_phase(str(spec_f), milestone_id="M1", repo_root=str(tmp_path))
    certify_manual_red_phase(str(spec_f), milestone_id="M2", repo_root=str(tmp_path))
    pass_summary = execute_plan_via_solo(
        plan_path=str(plan_file),
        repo_root=str(tmp_path),
        enforce_scope_guard=False,
        strict_red=True,
        auto_review=False,
        profile="auto",
    )
    assert pass_summary.passed is True
    assert pass_summary.milestones_passed == pass_summary.milestones_total
    assert (tmp_path / "decisions.tsv").is_file()


def test_solo_manual_purple_auto_review_uses_manual_profile_and_cwd_repo(tmp_path: Path) -> None:
    """Regression: standalone --profile manual --purple without --no-review runs manual /review on cwd repo."""
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.email", "qa@example.com"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.name", "QA Bot"], cwd=str(tmp_path), check=True)
    spec_f, tc_f = _setup_manual_repo(tmp_path)
    subprocess.run(["git", "add", "docs/checkout_brd.md"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init brd"], cwd=str(tmp_path), check=True)

    red_p = _run_solo_cli(tmp_path, "--profile", "manual", "--red", "--spec", str(spec_f), "--milestone", "M1", "--json")
    assert red_p.returncode == 0, red_p.stdout + red_p.stderr
    mut_p = _run_solo_cli(
        tmp_path, "--profile", "manual", "--mutation", "--spec", str(spec_f), "--target", str(tc_f), "--milestone", "M1", "--json"
    )
    assert mut_p.returncode == 0, mut_p.stdout + mut_p.stderr

    # Invoke --purple WITHOUT --no-review and WITHOUT an active plan file
    purple_p = _run_solo_cli(
        tmp_path, "--profile", "manual", "--purple", "--spec", str(spec_f), "--target", str(tc_f), "--milestone", "M1", "--json"
    )
    assert purple_p.returncode == 0, purple_p.stdout + purple_p.stderr
    out = json.loads(purple_p.stdout)
    assert out["purple_phase"]["passed"] is True
    assert out["auto_review"]["passed"] is True
    assert out["auto_review"]["profile"] == "manual"
    assert str(tmp_path) in str(out["auto_review"]["receipt_path"])
    assert out["auto_review"]["verdict"] in ("APPROVED", "APPROVED_WITH_NOTES")
