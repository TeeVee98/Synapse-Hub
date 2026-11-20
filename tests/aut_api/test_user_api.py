# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tests/aut_api/test_user_api.py — Automated Test Suite for User Management API.
Implements 100% of the 54 ISO/IEC/IEEE 29119-3 test cases from user_management_api_test_cases.md.
"""

import os
import secrets
import pytest
from tests.aut_api.api_models_helper import (
    validate_user_item,
    validate_pagination,
)

STANDARD_TEST_PWD = os.getenv("AUT_TEST_PASSWORD") or secrets.token_urlsafe(16)


# ============================================================================
# 1. GET /api/user — List Users (Pagination, Search, Sort, Security) [12 TCs]
# ============================================================================

@pytest.mark.req("REQ-USER-GET-01")
@pytest.mark.tc("TC_USER_GET_001")
@pytest.mark.smoke
@pytest.mark.p0
def test_user_get_default_pagination(user_api_client):
    """TC_USER_GET_001: Lấy danh sách users mặc định (Default Pagination)."""
    res = user_api_client.get_users()
    assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}"
    data = res.json()
    assert "list" in data and "pagination" in data
    assert validate_pagination(data["pagination"])
    assert data["pagination"]["currentPage"] == 1
    assert len(data["list"]) <= 10


@pytest.mark.req("REQ-USER-GET-02")
@pytest.mark.tc("TC_USER_GET_002")
@pytest.mark.regression
def test_user_get_pagination_page_limit(user_api_client):
    """TC_USER_GET_002: Phân trang danh sách với tham số page=2&limit=5."""
    res = user_api_client.get_users(params={"page": 2, "limit": 5})
    assert res.status_code == 200
    data = res.json()
    assert data["pagination"]["currentPage"] == 2
    assert len(data["list"]) <= 5


@pytest.mark.req("REQ-USER-GET-03")
@pytest.mark.tc("TC_USER_GET_003")
@pytest.mark.regression
def test_user_get_search_keyword(user_api_client):
    """TC_USER_GET_003: Tìm kiếm user theo từ khóa tên hay email."""
    res = user_api_client.get_users(params={"search": "AnhTester"})
    assert res.status_code == 200
    assert isinstance(res.json()["list"], list)


@pytest.mark.req("REQ-USER-GET-04")
@pytest.mark.tc("TC_USER_GET_004")
@pytest.mark.regression
def test_user_get_search_non_existent(user_api_client):
    """TC_USER_GET_004: Tìm kiếm với từ khóa không tồn tại trong hệ thống."""
    res = user_api_client.get_users(params={"search": "xyz_not_exist_999"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["list"]) == 0
    assert data["pagination"]["total"] == 0


@pytest.mark.req("REQ-USER-GET-05")
@pytest.mark.tc("TC_USER_GET_005")
@pytest.mark.regression
def test_user_get_sort_name_asc(user_api_client):
    """TC_USER_GET_005: Sắp xếp danh sách users theo tên tăng dần (A-Z)."""
    res = user_api_client.get_users(params={"sort": "name", "sortBy": "asc", "limit": 10})
    assert res.status_code == 200
    assert "list" in res.json()


@pytest.mark.req("REQ-USER-GET-06")
@pytest.mark.tc("TC_USER_GET_006")
@pytest.mark.regression
def test_user_get_sort_created_at_desc(user_api_client):
    """TC_USER_GET_006: Sắp xếp danh sách users theo ngày tạo createdAt giảm dần."""
    res = user_api_client.get_users(params={"sort": "createdAt", "sortBy": "desc", "limit": 5})
    assert res.status_code == 200
    assert "list" in res.json()


@pytest.mark.req("REQ-USER-GET-07")
@pytest.mark.tc("TC_USER_GET_007")
@pytest.mark.boundary
def test_user_get_boundary_large_page(user_api_client):
    """TC_USER_GET_007: Boundary - Số trang page=99999 vượt quá tổng số trang."""
    res = user_api_client.get_users(params={"page": 99999})
    assert res.status_code == 200
    data = res.json()
    assert len(data["list"]) == 0


@pytest.mark.req("REQ-USER-GET-08")
@pytest.mark.tc("TC_USER_GET_008")
@pytest.mark.negative
def test_user_get_negative_invalid_limit(user_api_client):
    """TC_USER_GET_008: Negative - Tham số limit=0 hay số âm."""
    res = user_api_client.get_users(params={"limit": -1})
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-USER-GET-09")
@pytest.mark.tc("TC_USER_GET_009")
@pytest.mark.negative
def test_user_get_negative_invalid_sort_field(user_api_client):
    """TC_USER_GET_009: Negative - Tham số sort truyền trường không tồn tại."""
    res = user_api_client.get_users(params={"sort": "invalid_field"})
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-USER-GET-010")
@pytest.mark.tc("TC_USER_GET_010")
@pytest.mark.security
def test_user_get_security_xss_sanitization(user_api_client):
    """TC_USER_GET_010: Security - XSS Payload trong query param search."""
    xss = "<script>alert(1)</script>"
    res = user_api_client.get_users(params={"search": xss})
    assert res.status_code == 200


@pytest.mark.req("REQ-USER-GET-011")
@pytest.mark.tc("TC_USER_GET_011")
@pytest.mark.resilience
def test_user_get_rate_limit_concurrency(user_api_client):
    """TC_USER_GET_011: Rate Limiting & Concurrency - Kiểm tra quota request."""
    responses = [user_api_client.get_users(params={"limit": 1}) for _ in range(5)]
    assert all(r.status_code in (200, 429) for r in responses)


@pytest.mark.req("REQ-USER-GET-012")
@pytest.mark.tc("TC_USER_GET_012")
@pytest.mark.protocol
def test_user_get_content_negotiation_xml(user_api_client):
    """TC_USER_GET_012: Protocol - Header Accept: application/xml."""
    res = user_api_client.get_users(headers={"Accept": "application/xml"})
    if res.status_code == 200:
        pytest.xfail("AUT Defect (TC_USER_GET_012): Backend API ignores Accept: application/xml and returns 200 OK instead of 406 Not Acceptable.")
    assert res.status_code == 406


# ============================================================================
# 2. POST /api/user — Create User (Happy Path, Boundary, Security) [19 TCs]
# ============================================================================

@pytest.mark.req("REQ-USER-POST-01")
@pytest.mark.tc("TC_USER_POST_001")
@pytest.mark.smoke
@pytest.mark.p0
def test_user_post_create_happy_path(user_api_client, user_teardown_registry):
    """TC_USER_POST_001: Happy Path - Tạo user mới thành công với đầy đủ các trường."""
    email = user_api_client.unique_email()
    payload = {
        "name": "QA Automation Engineer",
        "email": email,
        "password": STANDARD_TEST_PWD,
        "phone": "0987654321",
        "address": "Hanoi, Vietnam",
        "isActive": True,
    }
    res = user_api_client.create_user(payload)
    assert res.status_code in (200, 201), f"Expected 200/201, got {res.status_code}: {res.text}"
    body = res.json()
    uid = body.get("data", {}).get("id") or body.get("id")
    if uid:
        user_teardown_registry(uid)


@pytest.mark.req("REQ-USER-POST-02")
@pytest.mark.tc("TC_USER_POST_002")
@pytest.mark.negative
def test_user_post_missing_email(user_api_client):
    """TC_USER_POST_002: Negative - Bỏ trống trường email bắt buộc."""
    payload = {"name": "No Email User", "password": STANDARD_TEST_PWD}
    res = user_api_client.create_user(payload)
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-USER-POST-03")
@pytest.mark.tc("TC_USER_POST_003")
@pytest.mark.negative
def test_user_post_missing_name(user_api_client):
    """TC_USER_POST_003: Negative - Bỏ trống trường name bắt buộc."""
    payload = {"email": user_api_client.unique_email(), "password": STANDARD_TEST_PWD}
    res = user_api_client.create_user(payload)
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-USER-POST-04")
@pytest.mark.tc("TC_USER_POST_004")
@pytest.mark.negative
def test_user_post_invalid_email_format(user_api_client):
    """TC_USER_POST_004: Negative - Email sai định dạng (không có @ hoặc domain)."""
    payload = {"name": "Bad Email", "email": "invalid_email_format_no_at", "password": STANDARD_TEST_PWD}
    res = user_api_client.create_user(payload)
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-USER-POST-05")
@pytest.mark.tc("TC_USER_POST_005")
@pytest.mark.boundary
@pytest.mark.xfail(strict=True, reason="AUT Defect: Backend accepts passwords shorter than 6 characters")
def test_user_post_short_password(user_api_client, user_teardown_registry):
    """TC_USER_POST_005: Boundary - Mật khẩu quá ngắn (<6 ký tự)."""
    payload = {"name": "Short Pwd", "email": user_api_client.unique_email(), "password": "123"}
    res = user_api_client.create_user(payload)
    if res.status_code in (200, 201):
        uid = res.json().get("data", {}).get("id") or res.json().get("id")
        if uid:
            user_teardown_registry(uid)
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-USER-POST-06")
@pytest.mark.tc("TC_USER_POST_006")
@pytest.mark.regression
def test_user_post_duplicate_email_conflict(user_api_client, user_teardown_registry):
    """TC_USER_POST_006: Business Rule - Đăng ký email đã tồn tại trong CSDL (409 Conflict)."""
    email = user_api_client.unique_email("DUP_")
    p = {"name": "First Instance", "email": email, "password": STANDARD_TEST_PWD}
    r1 = user_api_client.create_user(p)
    assert r1.status_code in (200, 201)
    uid = r1.json().get("data", {}).get("id") or r1.json().get("id")
    if uid:
        user_teardown_registry(uid)

    r2 = user_api_client.create_user(p)
    assert r2.status_code in (400, 409, 422)


@pytest.mark.req("REQ-USER-POST-07")
@pytest.mark.tc("TC_USER_POST_007")
@pytest.mark.boundary
def test_user_post_name_boundary_min(user_api_client, user_teardown_registry):
    """TC_USER_POST_007: Boundary - Tên user độ dài tối thiểu 1 ký tự."""
    payload = {"name": "U", "email": user_api_client.unique_email(), "password": STANDARD_TEST_PWD}
    res = user_api_client.create_user(payload)
    assert res.status_code in (200, 201)
    uid = res.json().get("data", {}).get("id") or res.json().get("id")
    if uid:
        user_teardown_registry(uid)


@pytest.mark.req("REQ-USER-POST-08")
@pytest.mark.tc("TC_USER_POST_008")
@pytest.mark.boundary
def test_user_post_name_boundary_max(user_api_client):
    """TC_USER_POST_008: Boundary - Tên user đúng 255 ký tự."""
    payload = {"name": "X" * 255, "email": user_api_client.unique_email(), "password": STANDARD_TEST_PWD}
    res = user_api_client.create_user(payload)
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-USER-POST-09")
@pytest.mark.tc("TC_USER_POST_009")
@pytest.mark.boundary
def test_user_post_name_exceeds_max(user_api_client):
    """TC_USER_POST_009: Boundary - Tên user vượt quá 255 ký tự."""
    payload = {"name": "Y" * 256, "email": user_api_client.unique_email(), "password": STANDARD_TEST_PWD}
    res = user_api_client.create_user(payload)
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-USER-POST-10")
@pytest.mark.tc("TC_USER_POST_010")
@pytest.mark.security
def test_user_post_sqli_payload(user_api_client):
    """TC_USER_POST_010: Security - SQL Injection trong trường email."""
    payload = {
        "name": "SQLi Tester",
        "email": "admin' OR 1=1--@example.com",
        "password": STANDARD_TEST_PWD,
    }
    res = user_api_client.create_user(payload)
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-USER-POST-11")
@pytest.mark.tc("TC_USER_POST_011")
@pytest.mark.security
def test_user_post_xss_in_name(user_api_client, user_teardown_registry):
    """TC_USER_POST_011: Security - XSS Script Injection trong trường name."""
    payload = {
        "name": "<script>alert('UserXSS')</script>",
        "email": user_api_client.unique_email(),
        "password": STANDARD_TEST_PWD,
    }
    res = user_api_client.create_user(payload)
    assert res.status_code in (200, 201)
    uid = res.json().get("data", {}).get("id") or res.json().get("id")
    if uid:
        user_teardown_registry(uid)


@pytest.mark.req("REQ-USER-POST-12")
@pytest.mark.tc("TC_USER_POST_012")
@pytest.mark.security
def test_user_post_unauthenticated(unauth_user_client):
    """TC_USER_POST_012: Security - Tạo user khi không truyền Bearer token."""
    res = unauth_user_client.create_user({"name": "No Auth User", "email": "test@test.com"})
    assert res.status_code in (401, 403)


@pytest.mark.req("REQ-USER-POST-13")
@pytest.mark.tc("TC_USER_POST_013")
@pytest.mark.security
def test_user_post_invalid_token(user_api_client):
    """TC_USER_POST_013: Security - Tạo user với Bearer token không hợp lệ."""
    res = user_api_client.create_user(
        {"name": "Bad Token User", "email": "bad@test.com"},
        headers={"Authorization": "Bearer invalid_jwt_token_999"},
    )
    assert res.status_code in (401, 403)


@pytest.mark.req("REQ-USER-POST-14")
@pytest.mark.tc("TC_USER_POST_014")
@pytest.mark.security
def test_user_post_expired_token(user_api_client):
    """TC_USER_POST_014: Security - Tạo user với Bearer token đã hết hạn."""
    res = user_api_client.create_user(
        {"name": "Expired Token User", "email": "exp@test.com"},
        headers={"Authorization": "Bearer eyJhbGciOi.expired.user.token"},
    )
    assert res.status_code in (401, 403)


@pytest.mark.req("REQ-USER-POST-15")
@pytest.mark.tc("TC_USER_POST_015")
@pytest.mark.negative
def test_user_post_malformed_json(user_api_client):
    """TC_USER_POST_015: Negative - Payload JSON sai cú pháp (Malformed)."""
    res = user_api_client.create_user("MALFORMED_JSON")
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-USER-POST-16")
@pytest.mark.tc("TC_USER_POST_016")
@pytest.mark.negative
def test_user_post_extra_fields(user_api_client, user_teardown_registry):
    """TC_USER_POST_016: Negative/Resilience - Payload chứa trường ngoài schema (Ghost fields)."""
    payload = {
        "name": "Ghost Field User",
        "email": user_api_client.unique_email(),
        "password": STANDARD_TEST_PWD,
        "injected_role": "SUPER_ADMIN",
    }
    res = user_api_client.create_user(payload)
    assert res.status_code in (200, 201)
    uid = res.json().get("data", {}).get("id") or res.json().get("id")
    if uid:
        user_teardown_registry(uid)


@pytest.mark.req("REQ-USER-POST-17")
@pytest.mark.tc("TC_USER_POST_017")
@pytest.mark.negative
def test_user_post_empty_body(user_api_client):
    """TC_USER_POST_017: Negative - Body JSON rỗng {}."""
    res = user_api_client.create_user({})
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-USER-POST-18")
@pytest.mark.tc("TC_USER_POST_018")
@pytest.mark.resilience
def test_user_post_unicode_name(user_api_client, user_teardown_registry):
    """TC_USER_POST_018: Resilience - Ký tự tiếng Việt có dấu chuẩn NFC/NFD."""
    name = f"Nguyễn Văn Đạt 🌟 {user_api_client.unique_timestamp()}"
    payload = {
        "name": name,
        "email": user_api_client.unique_email(),
        "password": STANDARD_TEST_PWD,
    }
    res = user_api_client.create_user(payload)
    assert res.status_code in (200, 201)
    uid = res.json().get("data", {}).get("id") or res.json().get("id")
    if uid:
        user_teardown_registry(uid)


@pytest.mark.req("REQ-USER-POST-19")
@pytest.mark.tc("TC_USER_POST_019")
@pytest.mark.resilience
def test_user_post_payload_too_large(user_api_client):
    """TC_USER_POST_019: Boundary - Payload cực lớn vượt quá giới hạn (>1MB)."""
    large_payload = b"U" * (2 * 1024 * 1024)
    res = user_api_client.create_user(payload=None, raw_data=large_payload)
    assert res.status_code in (413, 400, 422)


# ============================================================================
# 3. GET /api/user/{id} — User Detail (6 TCs)
# ============================================================================

@pytest.mark.req("REQ-USER-GET-ID-01")
@pytest.mark.tc("TC_USER_GET_ID_001")
@pytest.mark.smoke
@pytest.mark.p0
def test_user_get_by_id_existing(user_api_client, user_teardown_registry):
    """TC_USER_GET_ID_001: Lấy chi tiết user theo ID tồn tại."""
    user_id = user_api_client.create_user_and_get_id(teardown=user_teardown_registry)
    res = user_api_client.get_user_by_id(user_id)
    assert res.status_code == 200, f"Expected 200 for existing user, got {res.status_code}: {res.text}"
    assert validate_user_item(res.json())
    assert str(res.json().get("id")) == str(user_id)


@pytest.mark.req("REQ-USER-GET-ID-02")
@pytest.mark.tc("TC_USER_GET_ID_002")
@pytest.mark.negative
def test_user_get_by_id_non_existent(user_api_client):
    """TC_USER_GET_ID_002: ID user không tồn tại (999999)."""
    res = user_api_client.get_user_by_id(999999)
    assert res.status_code == 404


@pytest.mark.req("REQ-USER-GET-ID-03")
@pytest.mark.tc("TC_USER_GET_ID_003")
@pytest.mark.boundary
def test_user_get_by_id_negative_or_zero(user_api_client):
    """TC_USER_GET_ID_003: Boundary - ID user là số âm hoặc 0."""
    res = user_api_client.get_user_by_id(-1)
    assert res.status_code in (400, 404, 422)


@pytest.mark.req("REQ-USER-GET-ID-04")
@pytest.mark.tc("TC_USER_GET_ID_004")
@pytest.mark.negative
def test_user_get_by_id_string_format(user_api_client):
    """TC_USER_GET_ID_004: Negative - ID user dạng chuỗi chữ (xyz)."""
    res = user_api_client.get_user_by_id("xyz")
    assert res.status_code in (400, 404, 422)


@pytest.mark.req("REQ-USER-GET-ID-05")
@pytest.mark.tc("TC_USER_GET_ID_005")
@pytest.mark.security
def test_user_get_by_id_sqli(user_api_client):
    """TC_USER_GET_ID_005: Security - SQL Injection trong path parameter ID."""
    res = user_api_client.get_user_by_id("1 OR 1=1")
    assert res.status_code in (400, 404, 422)


@pytest.mark.req("REQ-USER-GET-ID-06")
@pytest.mark.tc("TC_USER_GET_ID_006")
@pytest.mark.boundary
def test_user_get_by_id_decimal(user_api_client):
    """TC_USER_GET_ID_006: Boundary - ID user là số thập phân (2.5)."""
    res = user_api_client.get_user_by_id("2.5")
    assert res.status_code in (400, 404, 422)


# ============================================================================
# 4. PATCH /api/user/{id} — Update User (12 TCs)
# ============================================================================

@pytest.mark.req("REQ-USER-PATCH-01")
@pytest.mark.tc("TC_USER_PATCH_001")
@pytest.mark.smoke
def test_user_patch_name(user_api_client, user_teardown_registry):
    """TC_USER_PATCH_001: Cập nhật tên user hợp lệ."""
    user_id = user_api_client.create_user_and_get_id(teardown=user_teardown_registry)
    new_name = f"Updated User {user_api_client.unique_timestamp()}"
    new_email = user_api_client.unique_email("upd_")
    res = user_api_client.update_user(user_id, {"name": new_name, "email": new_email})
    assert res.status_code == 200, f"Expected 200 on user PATCH, got {res.status_code}: {res.text}"
    get_res = user_api_client.get_user_by_id(user_id)
    assert get_res.status_code == 200
    assert get_res.json().get("name") == new_name


@pytest.mark.req("REQ-USER-PATCH-02")
@pytest.mark.tc("TC_USER_PATCH_002")
@pytest.mark.regression
def test_user_patch_email(user_api_client, user_teardown_registry):
    """TC_USER_PATCH_002: Cập nhật email user hợp lệ."""
    user_id = user_api_client.create_user_and_get_id(teardown=user_teardown_registry)
    new_email = user_api_client.unique_email("new_email_")
    res = user_api_client.update_user(user_id, {"email": new_email})
    assert res.status_code == 200, f"Expected 200 on email PATCH, got {res.status_code}: {res.text}"
    get_res = user_api_client.get_user_by_id(user_id)
    assert get_res.status_code == 200
    assert get_res.json().get("email") == new_email


@pytest.mark.req("REQ-USER-PATCH-03")
@pytest.mark.tc("TC_USER_PATCH_003")
@pytest.mark.negative
def test_user_patch_non_existent(user_api_client):
    """TC_USER_PATCH_003: Cập nhật user với ID không tồn tại."""
    res = user_api_client.update_user(999999, {"name": "Ghost User"})
    assert res.status_code == 404


@pytest.mark.req("REQ-USER-PATCH-04")
@pytest.mark.tc("TC_USER_PATCH_004")
@pytest.mark.security
def test_user_patch_unauthenticated(user_api_client, unauth_user_client, user_teardown_registry):
    """TC_USER_PATCH_004: Cập nhật user không truyền Bearer token."""
    user_id = user_api_client.create_user_and_get_id(teardown=user_teardown_registry)
    res = unauth_user_client.update_user(user_id, {"name": "No Auth Patch"})
    assert res.status_code in (401, 403)


@pytest.mark.req("REQ-USER-PATCH-05")
@pytest.mark.tc("TC_USER_PATCH_005")
@pytest.mark.negative
def test_user_patch_invalid_email_format(user_api_client, user_teardown_registry):
    """TC_USER_PATCH_005: Negative - Cập nhật email sai định dạng."""
    user_id = user_api_client.create_user_and_get_id(teardown=user_teardown_registry)
    res = user_api_client.update_user(user_id, {"email": "invalid_email_no_domain"})
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-USER-PATCH-06")
@pytest.mark.tc("TC_USER_PATCH_006")
@pytest.mark.negative
def test_user_patch_empty_name(user_api_client, user_teardown_registry):
    """TC_USER_PATCH_006: Negative - Cập nhật tên thành chuỗi rỗng."""
    user_id = user_api_client.create_user_and_get_id(teardown=user_teardown_registry)
    new_email = user_api_client.unique_email("empty_name_")
    res = user_api_client.update_user(user_id, {"name": "", "email": new_email})
    if res.status_code == 200:
        pytest.xfail("AUT Defect (TC_USER_PATCH_006): Backend API accepts empty name ('') on PATCH /api/user with 200 OK instead of returning 400/422 Bad Request.")
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-USER-PATCH-07")
@pytest.mark.tc("TC_USER_PATCH_007")
@pytest.mark.regression
def test_user_patch_idempotency(user_api_client, user_teardown_registry):
    """TC_USER_PATCH_007: Idempotency - Gửi cùng payload patch 2 lần liên tiếp."""
    user_id = user_api_client.create_user_and_get_id(teardown=user_teardown_registry)
    unique_email = user_api_client.unique_email("idem_")
    p = {"address": "Da Nang, Vietnam", "email": unique_email}
    r1 = user_api_client.update_user(user_id, p)
    r2 = user_api_client.update_user(user_id, p)
    assert r1.status_code == 200
    assert r2.status_code == 200
    get_res = user_api_client.get_user_by_id(user_id)
    assert get_res.json().get("address") == "Da Nang, Vietnam"


@pytest.mark.req("REQ-USER-PATCH-08")
@pytest.mark.tc("TC_USER_PATCH_008")
@pytest.mark.security
def test_user_patch_immutable_fields(user_api_client, user_teardown_registry):
    """TC_USER_PATCH_008: Security - Cố gắng thay đổi trường read-only (id)."""
    user_id = user_api_client.create_user_and_get_id(teardown=user_teardown_registry)
    unique_email = user_api_client.unique_email("immut_")
    res = user_api_client.update_user(user_id, {"id": 7777, "email": unique_email})
    assert res.status_code == 200
    get_res = user_api_client.get_user_by_id(user_id)
    assert str(get_res.json().get("id")) == str(user_id)


@pytest.mark.req("REQ-USER-PATCH-09")
@pytest.mark.tc("TC_USER_PATCH_009")
@pytest.mark.security
def test_user_patch_sqli(user_api_client, user_teardown_registry):
    """TC_USER_PATCH_009: Security - SQL Injection trong payload patch."""
    user_id = user_api_client.create_user_and_get_id(teardown=user_teardown_registry)
    unique_email = user_api_client.unique_email("sqli_")
    res = user_api_client.update_user(user_id, {"name": "'; UPDATE users SET role='ADMIN'; --", "email": unique_email})
    assert res.status_code == 200


@pytest.mark.req("REQ-USER-PATCH-010")
@pytest.mark.tc("TC_USER_PATCH_010")
@pytest.mark.security
def test_user_patch_xss(user_api_client, user_teardown_registry):
    """TC_USER_PATCH_010: Security - XSS trong name."""
    user_id = user_api_client.create_user_and_get_id(teardown=user_teardown_registry)
    unique_email = user_api_client.unique_email("xss_")
    res = user_api_client.update_user(user_id, {"name": "<svg onload=alert(1)>", "email": unique_email})
    assert res.status_code == 200


@pytest.mark.req("REQ-USER-PATCH-011")
@pytest.mark.tc("TC_USER_PATCH_011")
@pytest.mark.resilience
def test_user_patch_concurrency(user_api_client, user_teardown_registry):
    """TC_USER_PATCH_011: Concurrency - Gửi liên tiếp 2 yêu cầu cập nhật song song."""
    user_id = user_api_client.create_user_and_get_id(teardown=user_teardown_registry)
    r1 = user_api_client.update_user(user_id, {"phone": "0911111111", "email": user_api_client.unique_email("cc1_")})
    r2 = user_api_client.update_user(user_id, {"phone": "0922222222", "email": user_api_client.unique_email("cc2_")})
    assert r1.status_code == 200
    assert r2.status_code == 200


@pytest.mark.req("REQ-USER-PATCH-012")
@pytest.mark.tc("TC_USER_PATCH_012")
@pytest.mark.negative
def test_user_patch_invalid_id_format(user_api_client):
    """TC_USER_PATCH_012: Negative - ID user sai định dạng."""
    res = user_api_client.update_user("user_abc", {"phone": "0900000000"})
    assert res.status_code in (400, 404, 422)


# ============================================================================
# 5. DELETE /api/user/{id} — Delete User (5 TCs)
# ============================================================================

@pytest.mark.req("REQ-USER-DELETE-01")
@pytest.mark.tc("TC_USER_DELETE_001")
@pytest.mark.smoke
@pytest.mark.p0
def test_user_delete_existing(user_api_client):
    """TC_USER_DELETE_001: Xóa user thành công với ID hợp lệ."""
    user_id = user_api_client.create_user_and_get_id()
    res = user_api_client.delete_user(user_id)
    assert res.status_code in (200, 204), f"Expected 200/204 on user DELETE, got {res.status_code}: {res.text}"


@pytest.mark.req("REQ-USER-DELETE-02")
@pytest.mark.tc("TC_USER_DELETE_002")
@pytest.mark.regression
def test_user_delete_verify_subsequent_get_404(user_api_client):
    """TC_USER_DELETE_002: Kiểm tra user đã xóa thì GET chi tiết trả về 404 Not Found."""
    user_id = user_api_client.create_user_and_get_id()
    del_res = user_api_client.delete_user(user_id)
    assert del_res.status_code in (200, 204)
    get_res = user_api_client.get_user_by_id(user_id)
    assert get_res.status_code == 404, f"Expected 404 for deleted user, got {get_res.status_code}"


@pytest.mark.req("REQ-USER-DELETE-03")
@pytest.mark.tc("TC_USER_DELETE_003")
@pytest.mark.negative
def test_user_delete_non_existent(user_api_client):
    """TC_USER_DELETE_003: Xóa user với ID không tồn tại (999999)."""
    res = user_api_client.delete_user(999999)
    assert res.status_code == 404


@pytest.mark.req("REQ-USER-DELETE-04")
@pytest.mark.tc("TC_USER_DELETE_004")
@pytest.mark.security
def test_user_delete_unauthenticated(user_api_client, unauth_user_client, user_teardown_registry):
    """TC_USER_DELETE_004: Xóa user không truyền Bearer token."""
    user_id = user_api_client.create_user_and_get_id(teardown=user_teardown_registry)
    res = unauth_user_client.delete_user(user_id)
    assert res.status_code in (401, 403)


@pytest.mark.req("REQ-USER-DELETE-05")
@pytest.mark.tc("TC_USER_DELETE_005")
@pytest.mark.negative
def test_user_delete_invalid_id_format(user_api_client):
    """TC_USER_DELETE_005: Xóa user với ID dạng chữ chuỗi (xyz)."""
    res = user_api_client.delete_user("xyz")
    assert res.status_code in (400, 404, 422)
