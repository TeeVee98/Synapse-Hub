# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""Four-scenario test suite for tools/manual/manual_pipeline_adapter.py (M1)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import importlib
import json
import os
from pathlib import Path
import sys
from typing import Any

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _load_adapter() -> Any:
    return importlib.import_module("tools.manual.manual_pipeline_adapter")


SAMPLE_BRD = """# Feature: User Checkout Authentication

## Actor & Preconditions
- As a registered customer with an active account
- Precondition: User has at least 1 item in cart and email/password credentials registered.

## Business Rules & Acceptance Criteria
- AC-01: User submits registered email and matching password; system returns HTTP 200 and issues session token.
- AC-02: System must reject malformed email format or password shorter than 8 characters with HTTP 400 validation error.
- AC-03: System must reject invalid or expired OTP code and lock login after 5 failed attempts with HTTP 429.
- AC-04: Standard user must be denied access to another user's order checkout via RBAC/IDOR check returning HTTP 403; double-submit checkout must remain idempotent.
"""


COMPLIANT_TEST_CASES = """<!-- synapse-linter-profile: auth-payment -->
# Manual Test Suite: Checkout Authentication

| TC ID | REQ ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| TC-01 | AC-01 | Auth | High | Login with registered email and password | Active customer account seeded in staging DB | 1. Open login page 2. Enter email and password 3. Click Sign In | HTTP 200 returned, session cookie set, user redirected to /checkout | P0 | `user_01@example.com` / `Str0ng!Pass9` | Yes | UI+API | @smoke @happy @req-ac-01 |
| TC-02 | AC-01 | Auth | Medium | Verify OTP confirmation completes checkout login | User passed step 1 and received 6-digit OTP | 1. Enter 6-digit OTP within 60s 2. Click Confirm | HTTP 200 returned and checkout summary displays order total | P0 | `otp=482910` | Yes | API | @happy @req-ac-01 |
| TC-03 | AC-02 | Auth | High | Reject empty email and null password boundary | User is on /login page unauthenticated | 1. Leave email empty and password empty 2. Click Sign In | HTTP 400 returned with explicit message "Email and password are required" | P0 | `email=""`, `password=""` | Yes | API | @negative @boundary @req-ac-02 |
| TC-04 | AC-02 | Auth | High | Reject malformed email and 7-char password boundary | User is on /login page unauthenticated | 1. Enter invalid email format and 7-char password 2. Click Sign In | HTTP 400 returned stating email format invalid and min length is 8 | P1 | `bad-email`, `Abc123!` | Yes | API | @negative @boundary @req-ac-02 |
| TC-05 | AC-02 | Auth | Medium | Reject 255+ char Unicode IME email input | User is on /login page unauthenticated | 1. Paste 260-char Unicode NFC/NFD string with emoji into email 2. Submit | HTTP 400 validation error returned without truncation crash or 500 | P1 | 260-char Unicode IME payload | Yes | API | @negative @boundary @unicode @req-ac-02 |
| TC-06 | AC-03 | Auth | Critical | Reject expired OTP and trigger 5-attempt lockout | Account exists with expired OTP timestamp | 1. Submit wrong OTP 5 consecutive times 2. Attempt 6th login | HTTP 429 Too Many Requests returned and account locked for 15 minutes | P0 | `otp=000000` x5 | Yes | API | @negative @security @req-ac-03 |
| TC-07 | AC-04 | Security | Critical | Block IDOR cross-user checkout access via RBAC | User A logged in with valid JWT; User B owns order ORD-99 | 1. Send GET /api/v1/checkout/ORD-99 with User A token | HTTP 403 Forbidden returned and User B order data is absent from body | P0 | `order_id=ORD-99`, `role=customer` | Yes | API | @security @rbac @idor @req-ac-04 |
| TC-08 | AC-04 | Security | Critical | Guard double-submit checkout race condition | User A on final checkout step with idempotency key | 1. Click Pay twice within 100ms using same idempotency key | Single order created, second request returns HTTP 409 Conflict with zero duplicate charge | P0 | `idempotency_key=idem-1001` | Yes | API | @security @resilience @race @req-ac-04 |
| TC-09 | AC-02 | Security | High | Block SQL injection payload in password and email | User is on /login page unauthenticated | 1. Enter SQLi payload in email field 2. Click Sign In | HTTP 400 invalid email returned, query parameterized, zero DB error leaked | P1 | `' OR 1=1 --` | Yes | API | @security @req-ac-02 |
"""


def _write_sample_workspace(tmp_path: Path, brd_text: str = SAMPLE_BRD, tc_text: str = COMPLIANT_TEST_CASES) -> tuple[Path, Path]:
    (tmp_path / ".git").mkdir(exist_ok=True)
    spec_file = tmp_path / "docs" / "checkout_brd.md"
    spec_file.parent.mkdir(parents=True, exist_ok=True)
    spec_file.write_text(brd_text, encoding="utf-8")

    tc_file = tmp_path / "docs" / "checkout_testcases.md"
    tc_file.write_text(tc_text, encoding="utf-8")
    return spec_file, tc_file


def test_manual_adapter_positive_full_loop(tmp_path: Path) -> None:
    """Positive: BRD inventory, HMAC Red lock, Green linter+RTM, Spec-Mutation >= 80%, and Review pass."""
    adapter = _load_adapter()
    spec_file, tc_file = _write_sample_workspace(tmp_path)

    inv = adapter.extract_manual_spec_inventory(str(spec_file), repo_root=str(tmp_path))
    assert inv.goldfish_passed is True
    assert inv.goldfish_score >= 60.0
    assert set(inv.requirement_ids) == {"AC-01", "AC-02", "AC-03", "AC-04"}
    assert "email" in inv.detected_fields
    assert "password" in inv.detected_fields
    assert "otp" in inv.detected_fields
    assert len(inv.spec_hash) == 64

    red = adapter.certify_manual_red_phase(
        spec_path=str(spec_file),
        milestone_id="M1",
        repo_root=str(tmp_path),
        plan_slug="checkout-manual",
    )
    assert red.status == "CERTIFIED_RED"
    assert red.profile == "manual"
    assert red.spec_hash == inv.spec_hash
    assert len(red.receipt_hmac) == 64

    green = adapter.verify_manual_green_phase(
        spec_path=str(spec_file),
        tc_files=(str(tc_file),),
        milestone_id="M1",
        repo_root=str(tmp_path),
    )
    assert green.passed is True
    assert green.linter_passed is True
    assert green.uncovered_req_ids == ()
    assert green.orphan_tc_ids == ()
    assert set(green.covered_req_ids) == {"AC-01", "AC-02", "AC-03", "AC-04"}

    mut = adapter.run_spec_mutation_audit(
        spec_path=str(spec_file),
        tc_files=(str(tc_file),),
        threshold=80.0,
        repo_root=str(tmp_path),
        milestone_id="M1",
    )
    assert mut.passed is True
    assert mut.total_mutants >= 4
    assert mut.kill_score >= 80.0
    assert len(mut.receipt_hmac) == 64

    review = adapter.audit_manual_delivery(
        repo_root=str(tmp_path),
        plan_path=None,
        changed_files=("docs/checkout_testcases.md",),
        milestone_id="M1",
        strict_solo=True,
        spec_path=str(spec_file),
    )
    assert review.passed is True
    assert review.receipt_verified is True
    assert review.profile == "manual"

    # Immutability contracts for all 5 frozen DTOs
    with pytest.raises(FrozenInstanceError):
        inv.goldfish_score = 0.0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        red.status = "MUTATED"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        green.passed = False  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        mut.kill_score = 0.0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        review.passed = False  # type: ignore[misc]

    # Alias-based field detection & path normalization
    alias_spec = tmp_path / "docs" / "alias_brd.md"
    alias_spec.write_text("# Feature: FX\n- AC-01: Validate exchange_rate and passkey token.\n", encoding="utf-8")
    inv_alias = adapter.extract_manual_spec_inventory(str(alias_spec), repo_root=str(tmp_path))
    assert inv_alias.spec_path == "docs/alias_brd.md"
    assert "currency" in inv_alias.detected_fields
    assert "biometric" in inv_alias.detected_fields

    # Profile detection contract
    assert adapter.detect_plan_profile("Profile: manual\n# Plan", "auto") == "manual"
    assert adapter.detect_plan_profile("# Normal Code Plan\nNo profile header", "auto") == "code"
    assert adapter.detect_plan_profile("", "auto") == "code"
    assert adapter.detect_plan_profile("# Code Plan", "manual") == "manual"
    assert adapter.detect_plan_profile("Profile: manual", "code") == "code"
    assert adapter.detect_plan_profile("Profile: manual", "") == "manual"

    # HMAC sensitivity to requirement_ids and ttl_seconds
    base_payload = {
        "milestone_id": "M1",
        "profile": "manual",
        "status": "CERTIFIED_RED",
        "spec_path": "docs/checkout_brd.md",
        "spec_hash": inv.spec_hash,
        "requirement_ids": ["AC-01"],
        "certified_at": "2026-11-27T00:00:00+00:00",
        "ttl_seconds": 900,
    }
    sig_base = adapter.compute_manual_red_hmac(base_payload, key=b"secret-key")
    sig_diff_req = adapter.compute_manual_red_hmac({**base_payload, "requirement_ids": ["AC-02"]}, key=b"secret-key")
    sig_diff_ttl = adapter.compute_manual_red_hmac({**base_payload, "ttl_seconds": 1800}, key=b"secret-key")
    assert sig_base != sig_diff_req
    assert sig_base != sig_diff_ttl
    assert adapter.verify_manual_red_hmac({"receipt_hmac": 12345}, key=b"secret-key") is False


def test_manual_adapter_negative_drift_uncovered_and_vague(tmp_path: Path) -> None:
    """Negative: Spec drift after Red, uncovered AC-03, vague oracle, and tampered HMAC fail closed."""
    adapter = _load_adapter()
    weak_tc = """<!-- synapse-linter-profile: default -->
| TC ID | REQ ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| TC-01 | AC-01 | Auth | Low | Basic login | User exists | 1. Login | System works properly as expected | P1 | valid data | No | Manual | @happy |
| TC-02 | AC-99 | Auth | Low | Unmapped feature | User exists | 1. Click | Returns 200 | P2 | sample | No | Manual | @happy |
"""
    spec_file, tc_file = _write_sample_workspace(tmp_path, tc_text=weak_tc)

    adapter.certify_manual_red_phase(
        spec_path=str(spec_file),
        milestone_id="M1",
        repo_root=str(tmp_path),
    )
    # Tamper spec content after Red lock
    spec_file.write_text(SAMPLE_BRD + "\n- AC-05: Sneaky uncertified requirement.\n", encoding="utf-8")

    green = adapter.verify_manual_green_phase(
        spec_path=str(spec_file),
        tc_files=(str(tc_file),),
        milestone_id="M1",
        repo_root=str(tmp_path),
    )
    assert green.passed is False
    assert "AC-03" in green.uncovered_req_ids
    assert "TC-02" in green.orphan_tc_ids
    assert green.linter_passed is False
    assert len(green.linter_defects) >= 1

    mut = adapter.run_spec_mutation_audit(
        spec_path=str(spec_file),
        tc_files=(str(tc_file),),
        threshold=80.0,
        repo_root=str(tmp_path),
        milestone_id="M1",
    )
    assert mut.passed is False
    assert mut.kill_score < 80.0
    assert len(mut.survived_mutants) >= 1

    review = adapter.audit_manual_delivery(
        repo_root=str(tmp_path),
        plan_path=None,
        changed_files=("docs/checkout_testcases.md",),
        milestone_id="M1",
        strict_solo=True,
        spec_path=str(spec_file),
    )
    assert review.passed is False
    codes = {f.get("code") for f in review.findings}
    assert "SPEC_DRIFT_AFTER_RED" in codes


def test_manual_adapter_boundary_empty_missing_and_zero_requirements(tmp_path: Path) -> None:
    """Boundary: Empty spec, missing file, and zero-AC spec fail closed without crashes."""
    adapter = _load_adapter()
    (tmp_path / ".git").mkdir(exist_ok=True)
    empty_spec = tmp_path / "docs" / "empty.md"
    empty_spec.parent.mkdir(parents=True, exist_ok=True)
    empty_spec.write_text("", encoding="utf-8")

    inv_empty = adapter.extract_manual_spec_inventory(str(empty_spec), repo_root=str(tmp_path))
    assert inv_empty.goldfish_passed is False
    assert inv_empty.requirement_ids == ()
    assert len(inv_empty.findings) >= 1

    missing_spec = tmp_path / "docs" / "does_not_exist.md"
    inv_missing = adapter.extract_manual_spec_inventory(str(missing_spec), repo_root=str(tmp_path))
    assert inv_missing.goldfish_passed is False
    assert inv_missing.spec_hash == ""

    mut_zero = adapter.run_spec_mutation_audit(
        spec_path=str(empty_spec),
        tc_files=(),
        threshold=80.0,
        repo_root=str(tmp_path),
    )
    assert mut_zero.total_mutants == 0
    assert mut_zero.kill_score == 0.0
    assert mut_zero.passed is False


def test_manual_adapter_resilience_readonly_key_and_tampered_hmac(tmp_path: Path) -> None:
    """Resilience/CLI: Read-only audit never creates key file; tampered receipt HMAC is rejected."""
    adapter = _load_adapter()
    spec_file, tc_file = _write_sample_workspace(tmp_path)
    key_file = tmp_path / ".git" / "synapse_receipt_hmac.key"

    # Read-only review before any key exists must not create key file
    review_no_key = adapter.audit_manual_delivery(
        repo_root=str(tmp_path),
        plan_path=None,
        changed_files=("docs/checkout_testcases.md",),
        milestone_id="M1",
        strict_solo=True,
        spec_path=str(spec_file),
    )
    assert review_no_key.passed is False
    assert review_no_key.receipt_verified is False
    assert not key_file.exists()

    # Certify Red then tamper the HMAC on disk
    adapter.certify_manual_red_phase(
        spec_path=str(spec_file),
        milestone_id="M1",
        repo_root=str(tmp_path),
    )
    receipt_file = tmp_path / "reports" / "solo_receipts" / "M1_red.json"
    assert receipt_file.is_file()
    data = json.loads(receipt_file.read_text(encoding="utf-8"))
    data["receipt_hmac"] = "0" * 64
    receipt_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    review_tampered = adapter.audit_manual_delivery(
        repo_root=str(tmp_path),
        plan_path=None,
        changed_files=("docs/checkout_testcases.md",),
        milestone_id="M1",
        strict_solo=True,
        spec_path=str(spec_file),
    )
    assert review_tampered.passed is False
    assert review_tampered.receipt_verified is False
    codes = {f.get("code") for f in review_tampered.findings}
    assert "TAMPERED_MANUAL_RED_RECEIPT" in codes

    # Expired TTL Red receipt must fail closed even with a valid HMAC signature
    adapter.certify_manual_red_phase(
        spec_path=str(spec_file),
        milestone_id="M2",
        repo_root=str(tmp_path),
        ttl_seconds=60,
    )
    exp_file = tmp_path / "reports" / "solo_receipts" / "M2_red.json"
    exp_data = json.loads(exp_file.read_text(encoding="utf-8"))
    exp_data["certified_at"] = "2020-01-01T00:00:00+00:00"
    exp_data["receipt_hmac"] = adapter.compute_manual_red_hmac(exp_data, repo_root=str(tmp_path))
    exp_file.write_text(json.dumps(exp_data, indent=2), encoding="utf-8")

    review_expired = adapter.audit_manual_delivery(
        repo_root=str(tmp_path),
        plan_path=None,
        changed_files=("docs/checkout_testcases.md",),
        milestone_id="M2",
        strict_solo=True,
        spec_path=str(spec_file),
    )
    assert review_expired.passed is False
    assert review_expired.receipt_verified is False
    assert "EXPIRED_MANUAL_RED_RECEIPT" in {f.get("code") for f in review_expired.findings}


def test_manual_adapter_vietnamese_bilingual_spec_mutation(tmp_path: Path) -> None:
    """Vietnamese-only BRD and TC suite must trigger and kill Spec-Mutation faults accurately."""
    adapter = _load_adapter()
    (tmp_path / ".git").mkdir(exist_ok=True)
    vi_brd = (
        "# Chức năng: Thanh toán chuyển khoản nội bộ\n\n"
        "## Bối cảnh & Tiền điều kiện\n"
        "- Vai trò: Người dùng đã đăng nhập và có tài khoản ngân hàng hoạt động.\n"
        "- Tiền điều kiện: Số dư khả dụng lớn hơn 100.000 VND.\n\n"
        "## Quy tắc nghiệp vụ & Tiêu chí chấp nhận\n"
        "- YC-01: Người dùng nhập số tiền và mật khẩu chính xác để thực hiện chuyển khoản thành công.\n"
        "- YC-02: Hệ thống từ chối khi bỏ trống mật khẩu hoặc nhập sai định dạng số điện thoại vượt quá độ dài tối đa.\n"
        "- YC-03: Hệ thống khóa tài khoản khi nhập sai mã xác thực quá 5 lần hoặc mã xác thực hết hạn.\n"
        "- YC-04: Hệ thống cấm truy cập trái phép vào giao dịch của người dùng khác và chống nhấn đúp gửi trùng giao dịch đồng thời.\n"
    )
    vi_tc = (
        "<!-- synapse-linter-profile: auth-payment -->\n"
        "# Bộ Test Case: Thanh toán chuyển khoản\n\n"
        "| Mã TC | Mã REQ | Chức năng | Mức rủi ro | Tiêu đề | Tiền điều kiện | Các bước thực hiện | Kết quả mong đợi | Độ ưu tiên | Dữ liệu | Tự động hóa | Loại | Nhãn |\n"
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        "| TC-01 | YC-01 | Chuyển khoản | Cao | Chuyển khoản thành công khi nhập đúng số tiền và mật khẩu | Tài khoản có số dư 500.000 VND | 1. Mở màn hình chuyển khoản 2. Nhập số tiền 100.000 và mật khẩu 3. Xác nhận | Giao dịch hoàn tất, số dư còn 400.000 VND và hiện biên lai mã GD-01 | P0 | `so_tien=100000`, `mat_khau=Abc@1234` | Yes | UI+API | @happy @smoke @yc-01 |\n"
        "| TC-02 | YC-01 | Chuyển khoản | Trung bình | Xác nhận chuyển khoản bằng mã xác thực trong hạn 60 giây | Đã qua bước nhập số tiền | 1. Nhập đúng mã xác thực 6 chữ số 2. Nhấn xác nhận | Hiển thị thông báo chuyển khoản thành công và lưu lịch sử giao dịch | P0 | `ma_xac_thuc=654321` | Yes | API | @happy @yc-01 |\n"
        "| TC-03 | YC-02 | Chuyển khoản | Cao | Từ chối khi bỏ trống mật khẩu và số tiền bằng 0 | Người dùng đang ở màn hình chuyển khoản | 1. Để trống mật khẩu và nhập số tiền 0 2. Nhấn xác nhận | Hệ thống từ chối và báo lỗi bắt buộc nhập mật khẩu và số tiền lớn hơn 0 | P0 | `mat_khau=""`, `so_tien=0` | Yes | API | @negative @boundary @yc-02 |\n"
        "| TC-04 | YC-02 | Chuyển khoản | Cao | Từ chối số điện thoại sai định dạng vượt quá độ dài tối đa 15 ký tự | Người dùng đang ở màn hình chuyển khoản | 1. Nhập số điện thoại 20 chữ số sai định dạng 2. Nhấn xác nhận | Hệ thống từ chối và báo lỗi sai định dạng số điện thoại vượt quá độ dài tối đa | P1 | `sdt=09876543210987654321` | Yes | API | @negative @boundary @yc-02 |\n"
        "| TC-05 | YC-02 | Chuyển khoản | Trung bình | Từ chối số tiền vượt quá hạn mức tối đa 500 triệu | Người dùng đang ở màn hình chuyển khoản | 1. Nhập số tiền 600.000.000 2. Nhấn xác nhận | Hệ thống từ chối và báo lỗi vượt quá hạn mức giao dịch tối đa | P1 | `so_tien=600000000` | Yes | API | @negative @boundary @yc-02 |\n"
        "| TC-06 | YC-03 | Bảo mật | Nghiêm trọng | Khóa tài khoản khi nhập sai mã xác thực 5 lần liên tiếp | Tài khoản có phiên chuyển khoản đang chờ xác thực | 1. Nhập sai mã xác thực 5 lần liên tiếp 2. Thử xác nhận lần thứ 6 | Hệ thống từ chối mã xác thực hết hạn và tạm khóa tài khoản 15 phút | P0 | `ma_xac_thuc=000000` x5 | Yes | API | @negative @security @yc-03 |\n"
        "| TC-07 | YC-04 | Bảo mật | Nghiêm trọng | Chặn truy cập trái phép vào lịch sử giao dịch của người dùng khác | Đã đăng nhập tài khoản A; giao dịch GD-99 thuộc tài khoản B | 1. Gửi yêu cầu xem chi tiết giao dịch GD-99 bằng phiên của tài khoản A | Hệ thống cấm truy cập vì không có quyền xem dữ liệu người dùng khác | P0 | `gd=GD-99`, `vai_tro=user_a` | Yes | API | @security @yc-04 |\n"
        "| TC-08 | YC-04 | Bảo mật | Nghiêm trọng | Chống nhấn đúp nút chuyển khoản gửi trùng giao dịch đồng thời | Tài khoản có số dư 500.000 VND tại bước xác nhận cuối | 1. Nhấn đúp nút xác nhận chuyển khoản hai lần liên tiếp trong 100ms | Chỉ tạo đúng 1 giao dịch, yêu cầu trùng lặp bị từ chối và không trừ tiền 2 lần | P0 | `khoa_chong_trung=tx-001` | Yes | API | @security @resilience @yc-04 |\n"
        "| TC-09 | YC-02 | Bảo mật | Cao | Chặn chuỗi ký tự đặc biệt độc hại ở trường mật khẩu và số điện thoại | Người dùng đang ở màn hình chuyển khoản | 1. Nhập ký tự đặc biệt SQLi vào ô số điện thoại và mật khẩu 2. Gửi biểu mẫu | Hệ thống từ chối do sai định dạng và không rò rỉ thông báo lỗi cơ sở dữ liệu | P1 | `' OR 1=1 --` | Yes | API | @security @yc-02 |\n"
    )
    spec_file = tmp_path / "docs" / "chuyen_khoan_brd.md"
    spec_file.parent.mkdir(parents=True, exist_ok=True)
    spec_file.write_text(vi_brd, encoding="utf-8")
    tc_file = tmp_path / "docs" / "chuyen_khoan_tc.md"
    tc_file.write_text(vi_tc, encoding="utf-8")

    inv = adapter.extract_manual_spec_inventory(str(spec_file), repo_root=str(tmp_path))
    assert inv.goldfish_passed is True
    assert set(inv.requirement_ids) == {"YC-01", "YC-02", "YC-03", "YC-04"}
    assert "password" in inv.detected_fields
    assert "phone" in inv.detected_fields
    assert "otp" in inv.detected_fields
    assert "number" in inv.detected_fields

    red = adapter.certify_manual_red_phase(str(spec_file), milestone_id="M1", repo_root=str(tmp_path))
    assert red.status == "CERTIFIED_RED"

    green = adapter.verify_manual_green_phase(
        spec_path=str(spec_file),
        tc_files=(str(tc_file),),
        milestone_id="M1",
        repo_root=str(tmp_path),
    )
    assert green.passed is True
    assert green.field_checklist_gaps == ()

    mut = adapter.run_spec_mutation_audit(
        spec_path=str(spec_file),
        tc_files=(str(tc_file),),
        threshold=80.0,
        repo_root=str(tmp_path),
        milestone_id="M1",
    )
    # Must generate boundary, lockout, rbac, race, and field mutants for Vietnamese BRD
    assert mut.total_mutants >= 11
    assert mut.passed is True
    assert mut.kill_score == 100.0

    # Negative: Vietnamese vague oracle must NOT kill M_REQ_OMIT
    vague_vi_tc = (
        "<!-- synapse-linter-profile: default -->\n"
        "| Mã TC | Mã REQ | Chức năng | Mức rủi ro | Tiêu đề | Tiền điều kiện | Các bước thực hiện | Kết quả mong đợi | Độ ưu tiên | Dữ liệu | Tự động hóa | Loại | Nhãn |\n"
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        "| TC-01 | YC-01 | Chuyển khoản | Thấp | Kiểm tra nhanh | Có tài khoản | 1. Mở trang | Hệ thống hoạt động bình thường như mong đợi | P1 | mẫu | No | Manual | @happy |\n"
    )
    vague_file = tmp_path / "docs" / "vague_vi_tc.md"
    vague_file.write_text(vague_vi_tc, encoding="utf-8")
    mut_vague = adapter.run_spec_mutation_audit(
        spec_path=str(spec_file),
        tc_files=(str(vague_file),),
        threshold=80.0,
        repo_root=str(tmp_path),
        milestone_id="M1",
    )
    assert mut_vague.passed is False
    assert "M_REQ_OMIT::YC-01" in mut_vague.survived_mutants
    assert "M_BOUNDARY_INVERT::YC-02" in mut_vague.survived_mutants
    assert "M_LOCKOUT_BYPASS::YC-03" in mut_vague.survived_mutants
    assert "M_RBAC_BYPASS::YC-04" in mut_vague.survived_mutants
    assert "M_RACE_DOUBLE_SUBMIT::YC-04" in mut_vague.survived_mutants

    # Regression guard: reports/ stage plans with generic ID tables must not be mistaken for TC suites
    stage_plan = tmp_path / "reports" / "plan_stages" / "03_implementation_plan.md"
    stage_plan.parent.mkdir(parents=True, exist_ok=True)
    stage_plan.write_text(
        "| ID | Target | Notes |\n| :--- | :--- | :--- |\n| **TC-01** | Demo | Matrix row |\n",
        encoding="utf-8",
    )
    rev_clean = adapter.audit_manual_delivery(
        repo_root=str(tmp_path),
        plan_path=None,
        changed_files=("docs/chuyen_khoan_tc.md", "reports/plan_stages/03_implementation_plan.md"),
        milestone_id="M1",
        strict_solo=True,
        spec_path=str(spec_file),
    )
    assert rev_clean.passed is True
    assert rev_clean.coverage_audit.orphan_tc_ids == ()


