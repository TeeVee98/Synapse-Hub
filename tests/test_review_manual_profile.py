# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""Four-scenario test suite for /review --profile manual (M4)."""

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
from tools.manual.manual_pipeline_adapter import certify_manual_red_phase, run_spec_mutation_audit
from tools.orchestration.plan_review_auditor import (
    audit_plan_and_solo_execution,
    verify_review_receipt_hmac,
)
from tools.orchestration.senior_code_review import evaluate_review


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


def _init_git_manual_repo(tmp_path: Path, brd: str = SAMPLE_BRD, tcs: str = COMPLIANT_TCS) -> tuple[Path, Path, Path]:
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.email", "qa@example.com"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.name", "QA Bot"], cwd=str(tmp_path), check=True)

    docs = tmp_path / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    spec_f = docs / "checkout_brd.md"
    spec_f.write_text(brd, encoding="utf-8")
    subprocess.run(["git", "add", "docs/checkout_brd.md"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init brd"], cwd=str(tmp_path), check=True)

    tc_f = docs / "checkout_testcases.md"
    tc_f.write_text(tcs, encoding="utf-8")

    plan_md = scaffold_super_plan(
        task="Checkout Manual QA",
        target_files=["docs/checkout_brd.md", "docs/checkout_testcases.md"],
        profile="manual",
        repo_root=str(tmp_path),
    )
    plan_f = tmp_path / "manual_plan.md"
    plan_f.write_text(plan_md, encoding="utf-8")
    return spec_f, tc_f, plan_f


def test_review_manual_positive_approved_with_signed_receipt(tmp_path: Path) -> None:
    """Positive: Compliant manual delivery passes /review --profile manual --strict-solo with valid HMAC receipt."""
    spec_f, tc_f, plan_f = _init_git_manual_repo(tmp_path)
    certify_manual_red_phase(str(spec_f), milestone_id="M1", repo_root=str(tmp_path))
    run_spec_mutation_audit(str(spec_f), (str(tc_f),), threshold=80.0, repo_root=str(tmp_path), milestone_id="M1")

    receipt_out = tmp_path / "reports" / "code_review_receipt.json"
    exit_code, payload, _, _ = evaluate_review(
        repo_dir=str(tmp_path),
        target="uncommitted",
        plan_path=str(plan_f),
        milestone_id="M1",
        strict_solo=True,
        receipt_out=str(receipt_out),
        profile="manual",
    )
    assert exit_code == 0, payload.get("findings")
    assert payload["passed"] is True
    assert payload["profile"] == "manual"
    assert payload["verdict"] in ("APPROVED", "APPROVED_WITH_NOTES")
    assert receipt_out.is_file()
    rcpt = json.loads(receipt_out.read_text(encoding="utf-8"))
    from tools.orchestration.solo_contracts import get_receipt_hmac_key_readonly

    key = get_receipt_hmac_key_readonly(str(tmp_path))
    assert key is not None
    assert verify_review_receipt_hmac(rcpt, key=key) is True


def test_review_manual_negative_blocks_on_missing_receipt_and_uncovered_ac(tmp_path: Path) -> None:
    """Negative: Missing Red receipt or uncovered AC returns CHANGES_REQUESTED (exit 1)."""
    weak_tcs = """<!-- synapse-linter-profile: default -->
| TC ID | REQ ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| TC-01 | AC-01 | Auth | Low | Login | User exists | 1. Login | Works properly as expected | P1 | valid data | No | Manual | @happy |
"""
    _, _, plan_f = _init_git_manual_repo(tmp_path, tcs=weak_tcs)

    exit_code, payload, _, _ = evaluate_review(
        repo_dir=str(tmp_path),
        target="uncommitted",
        plan_path=str(plan_f),
        milestone_id="M1",
        strict_solo=True,
        write_receipt=False,
        profile="auto",
    )
    assert exit_code == 1
    assert payload["passed"] is False
    assert payload["verdict"] == "CHANGES_REQUESTED"
    assert payload["profile"] == "manual"
    assert not (tmp_path / ".git" / "synapse_receipt_hmac.key").exists()


def test_review_manual_boundary_no_plan_and_empty_diff(tmp_path: Path) -> None:
    """Boundary: Manual audit with no changed files and no plan fails closed under strict_solo without crash."""
    (tmp_path / ".git").mkdir(exist_ok=True)
    plan_dto, solo_dto, caller_dto, findings = audit_plan_and_solo_execution(
        repo_root=str(tmp_path),
        changed_files=[],
        diff_text="",
        plan_path=None,
        strict_solo=True,
        profile="manual",
    )
    assert plan_dto is None
    assert solo_dto is not None
    assert solo_dto.passed is False
    assert caller_dto.passed is True
    assert len(findings) >= 1


def test_review_manual_resilience_cli_json(tmp_path: Path) -> None:
    """Resilience/CLI: senior_code_review.py --profile manual --plan ... --strict-solo --json works end-to-end."""
    spec_f, tc_f, plan_f = _init_git_manual_repo(tmp_path)
    certify_manual_red_phase(str(spec_f), milestone_id="M1", repo_root=str(tmp_path))
    run_spec_mutation_audit(str(spec_f), (str(tc_f),), threshold=80.0, repo_root=str(tmp_path), milestone_id="M1")

    proc = subprocess.run(
        [
            sys.executable,
            os.path.join(REPO_ROOT, "tools", "orchestration", "senior_code_review.py"),
            str(tmp_path),
            "--profile",
            "manual",
            "--plan",
            str(plan_f),
            "--milestone",
            "M1",
            "--strict-solo",
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    data = json.loads(proc.stdout)
    assert data["profile"] == "manual"
    assert data["passed"] is True
    assert data["verdict"] in ("APPROVED", "APPROVED_WITH_NOTES")


def test_review_manual_scope_creep_missing_plan_and_committed_tcs(tmp_path: Path) -> None:
    """Regression: Emits UNPLANNED_SCOPE_CREEP, PLAN_FILE_NOT_FOUND, and audits committed TC suites."""
    spec_f, tc_f, plan_f = _init_git_manual_repo(tmp_path)
    certify_manual_red_phase(str(spec_f), milestone_id="M1", repo_root=str(tmp_path))
    run_spec_mutation_audit(str(spec_f), (str(tc_f),), threshold=80.0, repo_root=str(tmp_path), milestone_id="M1")

    # 1. Missing --plan file emits PLAN_FILE_NOT_FOUND Must fix
    missing_exit, missing_payload, _, _ = evaluate_review(
        repo_dir=str(tmp_path),
        target="uncommitted",
        plan_path=str(tmp_path / "nonexistent_plan.md"),
        milestone_id="M1",
        strict_solo=False,
        write_receipt=False,
        profile="manual",
    )
    assert missing_exit == 1
    assert any("not found" in f["title"].lower() for f in missing_payload["findings"])

    # 2. Unplanned file outside write set emits UNPLANNED_SCOPE_CREEP (blocks under --strict)
    rogue = tmp_path / "docs" / "unplanned_notes.md"
    rogue.write_text("# Unplanned notes\n", encoding="utf-8")
    strict_exit, strict_payload, _, _ = evaluate_review(
        repo_dir=str(tmp_path),
        target="uncommitted",
        plan_path=str(plan_f),
        milestone_id="M1",
        strict=True,
        strict_solo=True,
        write_receipt=False,
        profile="manual",
    )
    assert strict_exit == 1
    assert any("unplanned" in f["title"].lower() for f in strict_payload["findings"])
    rogue.unlink()

    # 3. Already-committed test cases are still reconciled from planned_files when diff is clean
    # Also verify canonical 6-column decisions.tsv passes strict manual audit (key 'valid' not 'passed')
    decisions_f = tmp_path / "decisions.tsv"
    decisions_f.write_text(
        "ts\tphase\tdecision\twhy\tevidence\tresult\n"
        "2026-11-27T06:00:00Z\tM1\tKEEP\tVerified 100% AC coverage\treports/solo_receipts/M1_red.json\tPASSED\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "docs/checkout_testcases.md"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "commit tcs"], cwd=str(tmp_path), check=True)
    clean_exit, clean_payload, _, _ = evaluate_review(
        repo_dir=str(tmp_path),
        target="uncommitted",
        plan_path=str(plan_f),
        milestone_id="M1",
        strict_solo=True,
        write_receipt=False,
        profile="manual",
    )
    assert clean_exit == 0, clean_payload.get("findings")
    assert clean_payload["passed"] is True
    assert list(clean_payload["solo_provenance"]["valid_red_receipts"]) == ["reports/solo_receipts/M1_red.json"]
