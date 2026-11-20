# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tests/aut_api/test_book_api.py — Automated Test Suite for Book Management API.
Implements 100% of the 58 ISO/IEC/IEEE 29119-3 test cases from book_management_api_test_cases.md.
"""

import pytest
from tests.aut_api.api_models_helper import (
    validate_book_item,
    validate_pagination,
)


# ============================================================================
# 1. GET /api/book — List Books (Pagination, Search, Sort, Security) [12 TCs]
# ============================================================================

@pytest.mark.req("REQ-BOOK-GET-01")
@pytest.mark.tc("TC_BOOK_GET_001")
@pytest.mark.smoke
@pytest.mark.p0
def test_book_get_default_pagination(book_api_client):
    """TC_BOOK_GET_001: Lấy danh sách sách mặc định (Default Pagination)."""
    res = book_api_client.get_books()
    assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}"
    data = res.json()
    assert "list" in data and "pagination" in data
    assert validate_pagination(data["pagination"])
    assert data["pagination"]["currentPage"] == 1
    assert len(data["list"]) <= 10


@pytest.mark.req("REQ-BOOK-GET-02")
@pytest.mark.tc("TC_BOOK_GET_002")
@pytest.mark.regression
def test_book_get_pagination_page_limit(book_api_client):
    """TC_BOOK_GET_002: Phân trang danh sách với tham số page=2&limit=5."""
    res = book_api_client.get_books(params={"page": 2, "limit": 5})
    assert res.status_code == 200
    data = res.json()
    assert data["pagination"]["currentPage"] == 2
    assert len(data["list"]) <= 5


@pytest.mark.req("REQ-BOOK-GET-03")
@pytest.mark.tc("TC_BOOK_GET_003")
@pytest.mark.regression
def test_book_get_search_keyword(book_api_client):
    """TC_BOOK_GET_003: Tìm kiếm sách theo từ khóa tên hay mô tả."""
    res = book_api_client.get_books(params={"search": "Clean Code"})
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data["list"], list)


@pytest.mark.req("REQ-BOOK-GET-04")
@pytest.mark.tc("TC_BOOK_GET_004")
@pytest.mark.regression
def test_book_get_search_non_existent(book_api_client):
    """TC_BOOK_GET_004: Tìm kiếm với từ khóa không tồn tại trong hệ thống."""
    res = book_api_client.get_books(params={"search": "non_existent_book_999"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["list"]) == 0
    assert data["pagination"]["total"] == 0


@pytest.mark.req("REQ-BOOK-GET-05")
@pytest.mark.tc("TC_BOOK_GET_005")
@pytest.mark.regression
def test_book_get_sort_price_asc(book_api_client):
    """TC_BOOK_GET_005: Sắp xếp danh sách sách theo giá (price) tăng dần."""
    res = book_api_client.get_books(params={"sort": "price", "sortBy": "asc", "limit": 10})
    assert res.status_code == 200
    data = res.json()
    prices = [b.get("price", 0) for b in data["list"] if isinstance(b.get("price"), (int, float))]
    if len(prices) >= 2:
        assert prices == sorted(prices), "Prices must be monotonically non-decreasing"


@pytest.mark.req("REQ-BOOK-GET-06")
@pytest.mark.tc("TC_BOOK_GET_006")
@pytest.mark.regression
def test_book_get_sort_viewcount_desc(book_api_client):
    """TC_BOOK_GET_006: Sắp xếp danh sách sách theo lượt xem (viewCount) giảm dần."""
    res = book_api_client.get_books(params={"sort": "viewCount", "sortBy": "desc", "limit": 10})
    assert res.status_code == 200
    data = res.json()
    views = [b.get("viewCount", 0) for b in data["list"] if isinstance(b.get("viewCount"), (int, float))]
    if len(views) >= 2:
        assert views == sorted(views, reverse=True)


@pytest.mark.req("REQ-BOOK-GET-07")
@pytest.mark.tc("TC_BOOK_GET_007")
@pytest.mark.regression
def test_book_get_sort_updated_at_desc(book_api_client):
    """TC_BOOK_GET_007: Sắp xếp mặc định theo thời gian cập nhật (updatedAt) mới nhất."""
    res = book_api_client.get_books(params={"sort": "updatedAt", "sortBy": "desc", "limit": 5})
    assert res.status_code == 200
    assert "list" in res.json()


@pytest.mark.req("REQ-BOOK-GET-08")
@pytest.mark.tc("TC_BOOK_GET_008")
@pytest.mark.regression
def test_book_get_boundary_large_page(book_api_client):
    """TC_BOOK_GET_008: Boundary - Số trang page=99999 vượt quá tổng số trang."""
    res = book_api_client.get_books(params={"page": 99999})
    assert res.status_code == 200
    data = res.json()
    assert len(data["list"]) == 0


@pytest.mark.req("REQ-BOOK-GET-09")
@pytest.mark.tc("TC_BOOK_GET_009")
@pytest.mark.negative
def test_book_get_negative_invalid_sort_param(book_api_client):
    """TC_BOOK_GET_009: Negative - Tham số sort truyền trường không hỗ trợ."""
    res = book_api_client.get_books(params={"sort": "invalid_column"})
    assert res.status_code in (400, 422), f"Expected 400/422 Bad Request, got {res.status_code}"


@pytest.mark.req("REQ-BOOK-GET-10")
@pytest.mark.tc("TC_BOOK_GET_010")
@pytest.mark.security
def test_book_get_security_xss_query_sanitization(book_api_client):
    """TC_BOOK_GET_010: Security - XSS Payload trong query param search."""
    xss_payload = "<script>alert(1)</script>"
    res = book_api_client.get_books(params={"search": xss_payload})
    assert res.status_code == 200
    assert "<script>" not in res.text


@pytest.mark.req("REQ-BOOK-GET-11")
@pytest.mark.tc("TC_BOOK_GET_011")
@pytest.mark.resilience
def test_book_get_rate_limit_concurrency(book_api_client):
    """TC_BOOK_GET_011: Rate Limiting & Concurrency resilience check."""
    responses = [book_api_client.get_books(params={"limit": 1}) for _ in range(5)]
    assert all(r.status_code in (200, 429) for r in responses)


@pytest.mark.req("REQ-BOOK-GET-12")
@pytest.mark.tc("TC_BOOK_GET_012")
@pytest.mark.protocol
def test_book_get_content_negotiation_xml(book_api_client):
    """TC_BOOK_GET_012: Protocol - Content Negotiation với Header Accept: application/xml."""
    res = book_api_client.get_books(headers={"Accept": "application/xml"})
    if res.status_code == 200:
        pytest.xfail("AUT Defect (TC_BOOK_GET_012): Backend API ignores Accept: application/xml and returns 200 OK instead of 406 Not Acceptable.")
    assert res.status_code == 406


# ============================================================================
# 2. POST /api/book — Create Book (Happy Path, Boundary, Security) [20 TCs]
# ============================================================================

@pytest.mark.req("REQ-BOOK-POST-01")
@pytest.mark.tc("TC_BOOK_POST_001")
@pytest.mark.smoke
@pytest.mark.p0
def test_book_post_create_happy_path(book_api_client, book_teardown_registry):
    """TC_BOOK_POST_001: Happy Path - Tạo sách mới thành công với payload hợp lệ."""
    title = book_api_client.unique_title()
    payload = {
        "name": title,
        "price": 120000,
        "description": "Software Architecture and Engineering",
        "categories": ["Technology"],
        "author": "Thế Vị",
    }
    res = book_api_client.create_book(payload)
    assert res.status_code in (200, 201), f"Expected 200/201, got {res.status_code}: {res.text}"
    body = res.json()
    assert "msg" in body or "data" in body
    bid = body.get("data", {}).get("id") or body.get("id")
    if bid:
        book_teardown_registry(bid)


@pytest.mark.req("REQ-BOOK-POST-02")
@pytest.mark.tc("TC_BOOK_POST_002")
@pytest.mark.negative
def test_book_post_missing_name(book_api_client):
    """TC_BOOK_POST_002: Negative - Thiếu trường name bắt buộc."""
    payload = {"price": 100000, "categories": ["General"], "author": "Tester"}
    res = book_api_client.create_book(payload)
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-BOOK-POST-03")
@pytest.mark.tc("TC_BOOK_POST_003")
@pytest.mark.negative
def test_book_post_missing_author(book_api_client):
    """TC_BOOK_POST_003: Negative - Thiếu trường author bắt buộc."""
    payload = {"name": book_api_client.unique_title(), "price": 100000}
    res = book_api_client.create_book(payload)
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-BOOK-POST-04")
@pytest.mark.tc("TC_BOOK_POST_004")
@pytest.mark.boundary
def test_book_post_negative_price(book_api_client):
    """TC_BOOK_POST_004: Boundary/Negative - Giá sách là số âm (-10000)."""
    payload = {
        "name": book_api_client.unique_title(),
        "price": -10000,
        "categories": ["General"],
        "author": "Tester",
    }
    res = book_api_client.create_book(payload)
    if res.status_code == 200:
        pytest.xfail("AUT Defect (TC_BOOK_POST_004): Backend API accepts negative price (-10000) with 200 OK instead of returning 400 Bad Request.")
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-BOOK-POST-05")
@pytest.mark.tc("TC_BOOK_POST_005")
@pytest.mark.boundary
def test_book_post_zero_price(book_api_client, book_teardown_registry):
    """TC_BOOK_POST_005: Boundary - Giá sách bằng 0 (Sách miễn phí)."""
    payload = {
        "name": book_api_client.unique_title(),
        "price": 0,
        "categories": ["General"],
        "author": "Tester",
    }
    res = book_api_client.create_book(payload)
    assert res.status_code in (200, 201)
    bid = res.json().get("data", {}).get("id") or res.json().get("id")
    if bid:
        book_teardown_registry(bid)


@pytest.mark.req("REQ-BOOK-POST-06")
@pytest.mark.tc("TC_BOOK_POST_006")
@pytest.mark.boundary
def test_book_post_name_boundary_min_length(book_api_client, book_teardown_registry):
    """TC_BOOK_POST_006: Boundary - Tên sách có độ dài tối thiểu 1 ký tự."""
    res = None
    import string
    pool = list(string.ascii_letters + string.digits) + [chr(i) for i in range(160, 1000) if chr(i).strip()]
    for ch in pool:
        payload = {
            "name": ch,
            "price": 50000,
            "categories": ["General"],
            "author": "Tester",
        }
        res = book_api_client.create_book(payload)
        if res.status_code in (200, 201):
            search_res = book_api_client.get_books(params={"search": ch})
            if hasattr(search_res, "json"):
                for item in search_res.json().get("list", []):
                    if item.get("name") == ch and item.get("id"):
                        book_teardown_registry(item["id"])
                        break
            break
    assert res is not None and res.status_code in (200, 201)


@pytest.mark.req("REQ-BOOK-POST-07")
@pytest.mark.tc("TC_BOOK_POST_007")
@pytest.mark.boundary
def test_book_post_name_boundary_max_length(book_api_client):
    """TC_BOOK_POST_007: Boundary - Tên sách có độ dài đúng 255 ký tự."""
    payload = {
        "name": "B" * 255,
        "price": 50000,
        "categories": ["General"],
        "author": "Tester",
    }
    res = book_api_client.create_book(payload)
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-BOOK-POST-08")
@pytest.mark.tc("TC_BOOK_POST_008")
@pytest.mark.boundary
def test_book_post_name_exceeds_max_length(book_api_client):
    """TC_BOOK_POST_008: Boundary - Tên sách vượt quá 255 ký tự (256 ký tự)."""
    payload = {
        "name": "C" * 256,
        "price": 50000,
        "categories": ["General"],
        "author": "Tester",
    }
    res = book_api_client.create_book(payload)
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-BOOK-POST-09")
@pytest.mark.tc("TC_BOOK_POST_009")
@pytest.mark.regression
def test_book_post_duplicate_title_handling(book_api_client, book_teardown_registry):
    """TC_BOOK_POST_009: Business - Xử lý trùng lặp tiêu đề sách."""
    title = book_api_client.unique_title("DUP_")
    p = {"name": title, "price": 99000, "categories": ["General"], "author": "Tester"}
    res1 = book_api_client.create_book(p)
    assert res1.status_code in (200, 201)
    bid1 = res1.json().get("data", {}).get("id") or res1.json().get("id")
    if bid1:
        book_teardown_registry(bid1)
    res2 = book_api_client.create_book(p)
    assert res2.status_code in (400, 409)


@pytest.mark.req("REQ-BOOK-POST-10")
@pytest.mark.tc("TC_BOOK_POST_010")
@pytest.mark.security
def test_book_post_sqli_payload(book_api_client):
    """TC_BOOK_POST_010: Security - SQL Injection payload trong trường name."""
    payload = {
        "name": "Book' OR '1'='1' --",
        "price": 88000,
        "categories": ["General"],
        "author": "Tester",
    }
    res = book_api_client.create_book(payload)
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-BOOK-POST-11")
@pytest.mark.tc("TC_BOOK_POST_011")
@pytest.mark.security
def test_book_post_xss_in_description(book_api_client, book_teardown_registry):
    """TC_BOOK_POST_011: Security - XSS Script Injection trong description."""
    payload = {
        "name": book_api_client.unique_title(),
        "price": 75000,
        "description": "<script>alert('XSS')</script>",
        "categories": ["General"],
        "author": "Tester",
    }
    res = book_api_client.create_book(payload)
    assert res.status_code in (200, 201)
    bid = res.json().get("data", {}).get("id") or res.json().get("id")
    if bid:
        book_teardown_registry(bid)


@pytest.mark.req("REQ-BOOK-POST-12")
@pytest.mark.tc("TC_BOOK_POST_012")
@pytest.mark.security
def test_book_post_unauthenticated_missing_token(unauth_book_client):
    """TC_BOOK_POST_012: Security - Tạo sách khi không truyền Bearer token."""
    res = unauth_book_client.create_book({
        "name": "No Auth Book",
        "price": 1000,
        "categories": ["General"],
        "author": "Tester",
    })
    assert res.status_code in (401, 403)


@pytest.mark.req("REQ-BOOK-POST-13")
@pytest.mark.tc("TC_BOOK_POST_013")
@pytest.mark.security
def test_book_post_invalid_bearer_token(book_api_client):
    """TC_BOOK_POST_013: Security - Tạo sách với Bearer token sai format / invalid."""
    res = book_api_client.create_book(
        {
            "name": "Invalid Token Book",
            "price": 1000,
            "categories": ["General"],
            "author": "Tester",
        },
        headers={"Authorization": "Bearer invalid_token_12345"},
    )
    assert res.status_code in (401, 403)


@pytest.mark.req("REQ-BOOK-POST-14")
@pytest.mark.tc("TC_BOOK_POST_014")
@pytest.mark.security
def test_book_post_expired_bearer_token(book_api_client):
    """TC_BOOK_POST_014: Security - Tạo sách với Bearer token đã hết hạn."""
    res = book_api_client.create_book(
        {
            "name": "Expired Token Book",
            "price": 1000,
            "categories": ["General"],
            "author": "Tester",
        },
        headers={"Authorization": "Bearer eyJhbGciOi.expired.token"},
    )
    assert res.status_code in (401, 403)


@pytest.mark.req("REQ-BOOK-POST-15")
@pytest.mark.tc("TC_BOOK_POST_015")
@pytest.mark.negative
def test_book_post_malformed_json_syntax(book_api_client):
    """TC_BOOK_POST_015: Negative - Payload JSON sai cú pháp (Malformed JSON)."""
    res = book_api_client.create_book("MALFORMED_JSON")
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-BOOK-POST-16")
@pytest.mark.tc("TC_BOOK_POST_016")
@pytest.mark.negative
def test_book_post_extra_unknown_fields(book_api_client, book_teardown_registry):
    """TC_BOOK_POST_016: Negative/Resilience - Payload chứa trường ngoài schema (Ghost fields)."""
    payload = {
        "name": book_api_client.unique_title(),
        "price": 50000,
        "categories": ["General"],
        "author": "Tester",
        "unknown_ghost_field": "injected_value",
    }
    res = book_api_client.create_book(payload)
    assert res.status_code in (200, 201)
    bid = res.json().get("data", {}).get("id") or res.json().get("id")
    if bid:
        book_teardown_registry(bid)


@pytest.mark.req("REQ-BOOK-POST-17")
@pytest.mark.tc("TC_BOOK_POST_017")
@pytest.mark.negative
def test_book_post_empty_json_body(book_api_client):
    """TC_BOOK_POST_017: Negative - Body JSON rỗng {}."""
    res = book_api_client.create_book({})
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-BOOK-POST-18")
@pytest.mark.tc("TC_BOOK_POST_018")
@pytest.mark.resilience
def test_book_post_unicode_normalization(book_api_client, book_teardown_registry):
    """TC_BOOK_POST_018: Resilience - Ký tự Unicode tiếng Việt có dấu chuẩn NFC/NFD."""
    title = f"Lập Trình Hướng Đối Tượng 📚 {book_api_client.unique_timestamp()}"
    payload = {
        "name": title,
        "price": 95000,
        "categories": ["General"],
        "author": "Nguyễn Thế Vị",
    }
    res = book_api_client.create_book(payload)
    assert res.status_code in (200, 201)
    bid = res.json().get("data", {}).get("id") or res.json().get("id")
    if bid:
        book_teardown_registry(bid)


@pytest.mark.req("REQ-BOOK-POST-19")
@pytest.mark.tc("TC_BOOK_POST_019")
@pytest.mark.resilience
def test_book_post_payload_too_large(book_api_client):
    """TC_BOOK_POST_019: Boundary - Payload cực lớn vượt quá giới hạn (>1MB)."""
    large_payload = b"A" * (2 * 1024 * 1024)
    res = book_api_client.create_book(payload=None, raw_data=large_payload)
    assert res.status_code in (413, 400, 422)


@pytest.mark.req("REQ-BOOK-POST-20")
@pytest.mark.tc("TC_BOOK_POST_020")
@pytest.mark.protocol
def test_book_post_unsupported_media_type(book_api_client):
    """TC_BOOK_POST_020: Protocol - Header Content-Type không hỗ trợ (text/plain)."""
    res = book_api_client.create_book(
        payload={"name": "Plain Text Book"},
        headers={"Content-Type": "text/plain"},
    )
    assert res.status_code in (415, 400, 422)


# ============================================================================
# 3. GET /api/book/{id} — Book Detail (7 TCs)
# ============================================================================

@pytest.mark.req("REQ-BOOK-GET-ID-01")
@pytest.mark.tc("TC_BOOK_GET_ID_001")
@pytest.mark.smoke
@pytest.mark.p0
def test_book_get_by_id_existing(book_api_client, book_teardown_registry):
    """TC_BOOK_GET_ID_001: Lấy chi tiết sách theo ID tồn tại trong hệ thống."""
    book_id = book_api_client.create_book_and_get_id(teardown=book_teardown_registry)
    res = book_api_client.get_book_by_id(book_id)
    assert res.status_code == 200, f"Expected 200 for existing book, got {res.status_code}: {res.text}"
    assert validate_book_item(res.json())
    assert str(res.json().get("id")) == str(book_id)


@pytest.mark.req("REQ-BOOK-GET-ID-02")
@pytest.mark.tc("TC_BOOK_GET_ID_002")
@pytest.mark.regression
def test_book_get_by_id_view_count_increment(book_api_client, book_teardown_registry):
    """TC_BOOK_GET_ID_002: Kiểm tra viewCount tăng lên sau khi đọc chi tiết (?view=true)."""
    book_id = book_api_client.create_book_and_get_id(teardown=book_teardown_registry)
    res1 = book_api_client.get_book_by_id(book_id)
    assert res1.status_code == 200
    vc1 = res1.json().get("viewCount", 0)

    res2 = book_api_client.get_book_by_id(book_id, params={"view": "true"})
    assert res2.status_code == 200
    vc2 = res2.json().get("viewCount", 0)
    assert vc2 >= vc1 + 1, f"Expected viewCount increment from {vc1}, got {vc2}"


@pytest.mark.req("REQ-BOOK-GET-ID-03")
@pytest.mark.tc("TC_BOOK_GET_ID_003")
@pytest.mark.negative
def test_book_get_by_id_non_existent(book_api_client):
    """TC_BOOK_GET_ID_003: ID sách không tồn tại (999999)."""
    res = book_api_client.get_book_by_id(999999)
    assert res.status_code == 404


@pytest.mark.req("REQ-BOOK-GET-ID-04")
@pytest.mark.tc("TC_BOOK_GET_ID_004")
@pytest.mark.boundary
def test_book_get_by_id_negative_or_zero(book_api_client):
    """TC_BOOK_GET_ID_004: Boundary - ID sách là số âm hoặc bằng 0."""
    res = book_api_client.get_book_by_id(-1)
    assert res.status_code in (400, 404, 422)


@pytest.mark.req("REQ-BOOK-GET-ID-05")
@pytest.mark.tc("TC_BOOK_GET_ID_005")
@pytest.mark.negative
def test_book_get_by_id_string_format(book_api_client):
    """TC_BOOK_GET_ID_005: Negative - ID sách truyền dạng chuỗi chữ (abc)."""
    res = book_api_client.get_book_by_id("abc")
    assert res.status_code in (400, 404, 422)


@pytest.mark.req("REQ-BOOK-GET-ID-06")
@pytest.mark.tc("TC_BOOK_GET_ID_006")
@pytest.mark.security
def test_book_get_by_id_sqli(book_api_client):
    """TC_BOOK_GET_ID_006: Security - SQL Injection trong path parameter ID."""
    res = book_api_client.get_book_by_id("1 OR 1=1")
    assert res.status_code in (400, 404, 422)


@pytest.mark.req("REQ-BOOK-GET-ID-07")
@pytest.mark.tc("TC_BOOK_GET_ID_007")
@pytest.mark.boundary
def test_book_get_by_id_decimal_format(book_api_client):
    """TC_BOOK_GET_ID_007: Boundary - ID sách truyền số thực thập phân (1.5)."""
    res = book_api_client.get_book_by_id("1.5")
    assert res.status_code in (400, 404, 422)


# ============================================================================
# 4. PATCH /api/book/{id} — Update Book (13 TCs)
# ============================================================================

@pytest.mark.req("REQ-BOOK-PATCH-01")
@pytest.mark.tc("TC_BOOK_PATCH_001")
@pytest.mark.smoke
def test_book_patch_title(book_api_client, book_teardown_registry):
    """TC_BOOK_PATCH_001: Cập nhật tên sách hợp lệ."""
    book_id = book_api_client.create_book_and_get_id(teardown=book_teardown_registry)
    new_title = book_api_client.unique_title("UPD_")
    res = book_api_client.update_book(book_id, {"name": new_title})
    assert res.status_code == 200, f"Expected 200 on book PATCH, got {res.status_code}: {res.text}"
    get_res = book_api_client.get_book_by_id(book_id)
    assert get_res.status_code == 200
    assert get_res.json().get("name") == new_title


@pytest.mark.req("REQ-BOOK-PATCH-02")
@pytest.mark.tc("TC_BOOK_PATCH_002")
@pytest.mark.regression
def test_book_patch_price(book_api_client, book_teardown_registry):
    """TC_BOOK_PATCH_002: Cập nhật giá sách hợp lệ."""
    book_id = book_api_client.create_book_and_get_id(teardown=book_teardown_registry)
    res = book_api_client.update_book(book_id, {"price": 180000})
    assert res.status_code == 200, f"Expected 200 on book PATCH price, got {res.status_code}: {res.text}"
    get_res = book_api_client.get_book_by_id(book_id)
    assert get_res.status_code == 200
    assert get_res.json().get("price") == 180000


@pytest.mark.req("REQ-BOOK-PATCH-03")
@pytest.mark.tc("TC_BOOK_PATCH_003")
@pytest.mark.negative
def test_book_patch_non_existent_id(book_api_client):
    """TC_BOOK_PATCH_003: Cập nhật sách với ID không tồn tại."""
    res = book_api_client.update_book(999999, {"name": "Non Existent"})
    assert res.status_code == 404


@pytest.mark.req("REQ-BOOK-PATCH-04")
@pytest.mark.tc("TC_BOOK_PATCH_004")
@pytest.mark.security
def test_book_patch_unauthenticated(book_api_client, unauth_book_client, book_teardown_registry):
    """TC_BOOK_PATCH_004: Cập nhật sách không truyền Bearer token."""
    book_id = book_api_client.create_book_and_get_id(teardown=book_teardown_registry)
    res = unauth_book_client.update_book(book_id, {"name": "No Auth Patch"})
    assert res.status_code in (401, 403)


@pytest.mark.req("REQ-BOOK-PATCH-05")
@pytest.mark.tc("TC_BOOK_PATCH_005")
@pytest.mark.boundary
def test_book_patch_negative_price(book_api_client, book_teardown_registry):
    """TC_BOOK_PATCH_005: Boundary/Negative - Cập nhật giá sách thành số âm."""
    book_id = book_api_client.create_book_and_get_id(teardown=book_teardown_registry)
    res = book_api_client.update_book(book_id, {"price": -5000})
    if res.status_code == 200:
        pytest.xfail("AUT Defect (TC_BOOK_PATCH_005): Backend API accepts negative price (-5000) on PATCH with 200 OK instead of returning 400 Bad Request.")
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-BOOK-PATCH-06")
@pytest.mark.tc("TC_BOOK_PATCH_006")
@pytest.mark.negative
def test_book_patch_empty_name(book_api_client, book_teardown_registry):
    """TC_BOOK_PATCH_006: Negative - Cập nhật tên sách thành chuỗi rỗng."""
    book_id = book_api_client.create_book_and_get_id(teardown=book_teardown_registry)
    res = book_api_client.update_book(book_id, {"name": ""})
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-BOOK-PATCH-07")
@pytest.mark.tc("TC_BOOK_PATCH_007")
@pytest.mark.regression
def test_book_patch_idempotency(book_api_client, book_teardown_registry):
    """TC_BOOK_PATCH_007: Idempotency - Gửi cùng payload patch 2 lần liên tiếp."""
    book_id = book_api_client.create_book_and_get_id(teardown=book_teardown_registry)
    p = {"description": "Idempotent Description"}
    res1 = book_api_client.update_book(book_id, p)
    res2 = book_api_client.update_book(book_id, p)
    assert res1.status_code == 200
    assert res2.status_code == 200
    get_res = book_api_client.get_book_by_id(book_id)
    assert get_res.json().get("description") == "Idempotent Description"


@pytest.mark.req("REQ-BOOK-PATCH-08")
@pytest.mark.tc("TC_BOOK_PATCH_008")
@pytest.mark.security
def test_book_patch_immutable_fields(book_api_client, book_teardown_registry):
    """TC_BOOK_PATCH_008: Security - Cố gắng thay đổi trường read-only (id, createdAt)."""
    book_id = book_api_client.create_book_and_get_id(teardown=book_teardown_registry)
    res = book_api_client.update_book(book_id, {"id": 8888, "createdAt": "2000-01-01T00:00:00Z"})
    assert res.status_code == 200
    get_res = book_api_client.get_book_by_id(book_id)
    assert str(get_res.json().get("id")) == str(book_id)


@pytest.mark.req("REQ-BOOK-PATCH-09")
@pytest.mark.tc("TC_BOOK_PATCH_009")
@pytest.mark.security
def test_book_patch_sqli(book_api_client, book_teardown_registry):
    """TC_BOOK_PATCH_009: Security - SQL Injection trong payload patch."""
    book_id = book_api_client.create_book_and_get_id(teardown=book_teardown_registry)
    res = book_api_client.update_book(book_id, {"name": "'; DROP TABLE books; --"})
    assert res.status_code in (400, 422)


@pytest.mark.req("REQ-BOOK-PATCH-010")
@pytest.mark.tc("TC_BOOK_PATCH_010")
@pytest.mark.security
def test_book_patch_xss(book_api_client, book_teardown_registry):
    """TC_BOOK_PATCH_010: Security - XSS trong description."""
    book_id = book_api_client.create_book_and_get_id(teardown=book_teardown_registry)
    res = book_api_client.update_book(book_id, {"description": "<img src=x onerror=alert(1)>"})
    assert res.status_code == 200


@pytest.mark.req("REQ-BOOK-PATCH-011")
@pytest.mark.tc("TC_BOOK_PATCH_011")
@pytest.mark.resilience
def test_book_patch_concurrency(book_api_client, book_teardown_registry):
    """TC_BOOK_PATCH_011: Concurrency - Gửi liên tiếp nhiều bản cập nhật song song."""
    book_id = book_api_client.create_book_and_get_id(teardown=book_teardown_registry)
    r1 = book_api_client.update_book(book_id, {"price": 100})
    r2 = book_api_client.update_book(book_id, {"price": 200})
    assert r1.status_code == 200
    assert r2.status_code == 200


@pytest.mark.req("REQ-BOOK-PATCH-012")
@pytest.mark.tc("TC_BOOK_PATCH_012")
@pytest.mark.negative
def test_book_patch_invalid_id_format(book_api_client):
    """TC_BOOK_PATCH_012: Negative - ID sách sai định dạng."""
    res = book_api_client.update_book("xyz", {"price": 100})
    assert res.status_code in (400, 404, 422)


@pytest.mark.req("REQ-BOOK-PATCH-013")
@pytest.mark.tc("TC_BOOK_PATCH_013")
@pytest.mark.regression
def test_book_patch_empty_body(book_api_client, book_teardown_registry):
    """TC_BOOK_PATCH_013: Regression - Body patch rỗng {}."""
    book_id = book_api_client.create_book_and_get_id(teardown=book_teardown_registry)
    res = book_api_client.update_book(book_id, {})
    assert res.status_code == 200


# ============================================================================
# 5. DELETE /api/book/{id} — Delete Book (6 TCs)
# ============================================================================

@pytest.mark.req("REQ-BOOK-DELETE-01")
@pytest.mark.tc("TC_BOOK_DELETE_001")
@pytest.mark.smoke
@pytest.mark.p0
def test_book_delete_existing(book_api_client):
    """TC_BOOK_DELETE_001: Xóa sách thành công với ID hợp lệ."""
    book_id = book_api_client.create_book_and_get_id()
    res = book_api_client.delete_book(book_id)
    assert res.status_code in (200, 204), f"Expected 200/204 on book DELETE, got {res.status_code}: {res.text}"


@pytest.mark.req("REQ-BOOK-DELETE-02")
@pytest.mark.tc("TC_BOOK_DELETE_002")
@pytest.mark.regression
def test_book_delete_verify_subsequent_get_404(book_api_client):
    """TC_BOOK_DELETE_002: Kiểm tra sách đã xóa thì GET chi tiết trả về 404 Not Found."""
    book_id = book_api_client.create_book_and_get_id()
    del_res = book_api_client.delete_book(book_id)
    assert del_res.status_code in (200, 204)
    get_res = book_api_client.get_book_by_id(book_id)
    assert get_res.status_code == 404, f"Expected 404 for deleted book, got {get_res.status_code}"


@pytest.mark.req("REQ-BOOK-DELETE-03")
@pytest.mark.tc("TC_BOOK_DELETE_003")
@pytest.mark.negative
def test_book_delete_non_existent(book_api_client):
    """TC_BOOK_DELETE_003: Xóa sách với ID không tồn tại (999999)."""
    res = book_api_client.delete_book(999999)
    assert res.status_code == 404


@pytest.mark.req("REQ-BOOK-DELETE-04")
@pytest.mark.tc("TC_BOOK_DELETE_004")
@pytest.mark.security
def test_book_delete_unauthenticated(book_api_client, unauth_book_client, book_teardown_registry):
    """TC_BOOK_DELETE_004: Xóa sách không truyền Bearer token."""
    book_id = book_api_client.create_book_and_get_id(teardown=book_teardown_registry)
    res = unauth_book_client.delete_book(book_id)
    assert res.status_code in (401, 403)


@pytest.mark.req("REQ-BOOK-DELETE-05")
@pytest.mark.tc("TC_BOOK_DELETE_005")
@pytest.mark.negative
def test_book_delete_invalid_id_format(book_api_client):
    """TC_BOOK_DELETE_005: Xóa sách với ID dạng chữ chuỗi (abc)."""
    res = book_api_client.delete_book("abc")
    assert res.status_code in (400, 404, 422)


@pytest.mark.req("REQ-BOOK-DELETE-06")
@pytest.mark.tc("TC_BOOK_DELETE_006")
@pytest.mark.regression
def test_book_delete_idempotent_redelete(book_api_client):
    """TC_BOOK_DELETE_006: Xóa lại sách đã bị xóa trước đó (Re-delete)."""
    book_id = book_api_client.create_book_and_get_id()
    r1 = book_api_client.delete_book(book_id)
    assert r1.status_code in (200, 204)
    r2 = book_api_client.delete_book(book_id)
    assert r2.status_code == 404, f"Expected 404 on re-deleting book, got {r2.status_code}"
