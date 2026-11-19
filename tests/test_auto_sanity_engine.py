#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Unit Tests for Phase 3: Auto-Sanity Headless Playwright Verification Engine
(tools/design/auto_sanity_engine.py)
"""

import os
import sys
import subprocess
import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.design.auto_sanity_engine import AutoSanityEngine, DOMElement, DOMParser, ActionStep, main


@pytest.fixture
def sample_html_content():
    return """<!DOCTYPE html>
<html>
<head><title>Test App</title></head>
<body>
  <form id="login-form">
    <label for="usr">Tên đăng nhập</label>
    <input type="text" id="usr" name="username" placeholder="Nhập username...">

    <label for="pwd">Mật khẩu</label>
    <input type="password" id="pwd" name="password">

    <label for="role">Vai trò</label>
    <select id="role" name="role">
      <option value="admin">Quản trị viên</option>
      <option value="user">Người dùng</option>
    </select>

    <button type="submit" id="btn-login">Đăng nhập</button>
    <button type="button" id="btn-disabled" disabled>Nút bị khoá</button>
    <div id="hidden-box" hidden>Hộp ẩn</div>
  </form>
</body>
</html>
"""


def test_action_step_parsing():
    raw_steps = (
        "1. Truy cập trang /login<br>"
        "2. Nhập 'admin' vào ô 'Tên đăng nhập'<br>"
        "3. Nhập 'secret123' vào ô 'Mật khẩu'<br>"
        "4. Chọn 'admin' trong dropdown 'Vai trò'<br>"
        "5. Nhấp nút 'Đăng nhập'<br>"
        "6. Kiểm tra hiển thị thông báo 'Chào mừng admin'"
    )

    steps = AutoSanityEngine.parse_test_steps(raw_steps)
    assert len(steps) == 6

    assert steps[0].action == "NAVIGATE"
    assert steps[0].value == "/login"

    assert steps[1].action == "FILL"
    assert steps[1].value == "admin"
    assert steps[1].target == "Tên đăng nhập"

    assert steps[2].action == "FILL"
    assert steps[2].value == "secret123"

    assert steps[3].action == "SELECT"
    assert steps[3].value == "admin"

    assert steps[4].action == "CLICK"
    assert steps[4].target == "Đăng nhập"

    assert steps[5].action == "ASSERT_VISIBLE"
    assert "Chào mừng" in steps[5].target


def test_dom_parser_extracts_elements(sample_html_content):
    parser = DOMParser()
    parser.feed(sample_html_content)
    parser.finalize()

    assert len(parser.elements) >= 5

    # Check that labels are properly linked
    usr_elem = next(e for e in parser.elements if e.id == "usr")
    assert usr_elem.label_text == "Tên đăng nhập"
    assert usr_elem.placeholder == "Nhập username..."

    btn_elem = next(e for e in parser.elements if e.id == "btn-login")
    assert btn_elem.inner_text == "Đăng nhập"
    assert not btn_elem.is_disabled

    dis_elem = next(e for e in parser.elements if e.id == "btn-disabled")
    assert dis_elem.is_disabled is True


def test_dom_element_semantic_matching():
    elem = DOMElement("input", {"id": "company_name", "placeholder": "Enter company name"})
    elem.label_text = "Tên công ty"

    assert elem.matches_target("company_name") is True
    assert elem.matches_target("Tên công ty") is True
    assert elem.matches_target("Enter company name") is True
    assert elem.matches_target("NonExistent") is False


def test_dom_contract_verification_detects_drift_and_blocked(sample_html_content):
    engine = AutoSanityEngine(sample_html_content)

    steps = [
        # 1. Valid button click
        AutoSanityEngine.parse_test_steps("1. Nhấp nút 'Đăng nhập'")[0],
        # 2. Blocked interaction (disabled button)
        AutoSanityEngine.parse_test_steps("1. Nhấp nút 'Nút bị khoá'")[0],
        # 3. Locator drift (phantom button)
        AutoSanityEngine.parse_test_steps("1. Nhấp nút 'Nút ảo không có thật'")[0],
    ]

    verified_steps, stats = engine.verify_steps_against_dom(steps)

    assert stats["passed"] == 1
    assert stats["blocked"] == 1
    assert stats["locator_drift"] == 1

    assert verified_steps[0].status == "PASSED"
    assert verified_steps[1].status == "INTERACTION_BLOCKED"
    assert verified_steps[2].status == "LOCATOR_DRIFT"


def test_generate_playwright_clean_pom_spec():
    engine = AutoSanityEngine()
    test_cases = [
        {
            "TC ID": "TC_001",
            "Test Title": "Login Success",
            "Test Steps": "1. Truy cập trang /login<br>2. Nhập 'admin' vào ô 'Username'<br>3. Nhấp nút 'Login'"
        }
    ]

    spec = engine.generate_playwright_clean_pom_spec(test_cases, "LoginSanitySuite")

    assert 'import { test, expect } from "@playwright/test";' in spec
    assert 'test.describe("LoginSanitySuite"' in spec
    assert 'await page.goto("/login");' in spec
    assert 'await page.getByLabel("Username")' in spec
    assert 'await page.getByRole("button", { name: "Login" })' in spec


def test_generate_auto_sanity_report_md():
    engine = AutoSanityEngine()
    mock_results = [
        {
            "tc_id": "TC_001",
            "title": "Valid Flow",
            "overall_status": "VERIFIED",
            "summary": "Tương thích 100% với DOM.",
            "steps": [
                {"step_num": 1, "action": "NAVIGATE", "target": "/login", "value": "", "status": "PASSED", "error_detail": None}
            ]
        },
        {
            "tc_id": "TC_002",
            "title": "Broken Flow",
            "overall_status": "DRIFT_DETECTED",
            "summary": "Phát hiện 1 lỗi drift.",
            "steps": [
                {"step_num": 1, "action": "CLICK", "target": "GhostButton", "value": "", "status": "LOCATOR_DRIFT", "error_detail": "Không tồn tại"}
            ]
        }
    ]

    report = engine.generate_auto_sanity_report_md(mock_results)

    assert "# BÁO CÁO THẨM ĐỊNH TỰ ĐỘNG THỰC THI" in report
    assert "TỔNG QUAN CHỈ SỐ THỰC THI" in report
    assert "MA TRẬN KẾT QUẢ THẨM ĐỊNH" in report
    assert "TC_001" in report
    assert "TC_002" in report
    assert "LOCATOR_DRIFT" in report


def test_auto_sanity_cli_execution(tmp_path):
    tc_path = tmp_path / "test_manual.md"
    tc_path.write_text("""# Test Suite
| TC ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| TC_CLI_01 | General | Low | Verify Home | Ready | 1. Truy cập trang /home | Thành công | Low | - | Yes | E2E | @Smoke |
""", encoding="utf-8")

    out_rep = tmp_path / "out_sanity_report.md"
    out_spec = tmp_path / "out_spec.spec.ts"

    cmd = [
        sys.executable,
        os.path.join(_REPO_ROOT, "tools", "design", "auto_sanity_engine.py"),
        str(tc_path),
        "-o", str(out_rep),
        "--export-spec", str(out_spec)
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert out_rep.exists()
    assert out_spec.exists()
    assert "AUTO-SANITY HEADLESS PLAYWRIGHT" in res.stdout


def test_live_playwright_execution_against_crm_app():
    """Verify live headless Playwright execution against local HTML fixture."""
    html_file = os.path.join(_REPO_ROOT, "examples", "practices", "contracts", "customer_crm_app.html")
    assert os.path.exists(html_file)

    engine = AutoSanityEngine(html_file)
    steps = [
        ActionStep(1, "Truy cập form", "NAVIGATE", target=html_file, value=html_file),
        ActionStep(2, "Nhập tên công ty", "FILL", target="company", value="Synapse Hub Corp"),
        ActionStep(3, "Bấm lưu", "CLICK", target="btn-submit", value="")
    ]

    res = engine.run_live_playwright_test(steps, html_file)
    assert res.get("success") is True
    assert res.get("steps_executed") == 3


def test_generate_annotated_test_cases_md():
    """Verify annotation of 12-column table with @Live-Verified and @Drift-Detected tags."""
    raw_table = """# Suite
| TC ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| TC_01 | General | Low | Title 1 | Ready | 1. Step 1 | Pass | Low | - | Yes | E2E | @Smoke |
| TC_02 | General | High | Title 2 | Ready | 1. Step 1 | Pass | High | - | Yes | E2E | @Regression |
"""
    results = [
        {"tc_id": "TC_01", "overall_status": "VERIFIED"},
        {"tc_id": "TC_02", "overall_status": "DRIFT_DETECTED"}
    ]

    annotated = AutoSanityEngine.generate_annotated_test_cases_md(raw_table, results)
    assert "@Live-Verified" in annotated
    assert "@Drift-Detected" in annotated


def test_action_step_select_and_assertion():
    """Verify parsing and POM generation for SELECT and ASSERT actions."""
    engine = AutoSanityEngine()
    step_text = """
    1. Chọn 'Quản trị viên' trong dropdown 'role'
    2. Xác nhận 'Bảng điều khiển' hiển thị trên màn hình
    3. Thao tác không rõ ràng ngẫu nhiên
    """
    steps = engine.parse_test_steps(step_text)
    assert len(steps) == 3
    assert steps[0].action == "SELECT"
    assert steps[0].target == "role"
    assert steps[0].value == "Quản trị viên"
    assert "selectOption" in steps[0].generate_pom_locator_ts()

    assert steps[1].action == "ASSERT_VISIBLE"
    assert "toBeVisible" in steps[1].generate_pom_locator_ts()

    assert steps[2].action == "UNKNOWN"
    assert "// Warning: Mục tiêu UI không được xác định rõ" in steps[2].generate_pom_locator_ts()


def test_dom_contract_hidden_and_readonly():
    """Verify DOM verification correctly identifies hidden and readonly inputs as blocked."""
    html = """
    <div hidden><button id="btn-secret">Secret</button></div>
    <input type="text" id="readonly-token" readonly value="ABC-123">
    <div style="display: none"><input type="text" id="hidden-field"></div>
    """
    engine = AutoSanityEngine(html)
    steps = [
        ActionStep(1, "Click secret", "CLICK", target="btn-secret"),
        ActionStep(2, "Fill token", "FILL", target="readonly-token", value="NEW-TOKEN"),
        ActionStep(3, "Fill hidden", "FILL", target="hidden-field", value="TEST")
    ]
    verified, stats = engine.verify_steps_against_dom(steps)
    assert stats["blocked"] == 3
    assert all(s.status == "INTERACTION_BLOCKED" for s in verified)


def test_matches_target_length_guard():
    """Verify short words (<3 chars) do not accidentally match longer elements unless exact."""
    elem = DOMElement("button", {"id": "action-button", "name": "btn_action"}, "Action Button")
    assert elem.matches_target("btn_action") is True
    assert elem.matches_target("action-button") is True
    # 2-letter substring 'ac' should not match 'action-button' spuriously
    assert elem.matches_target("ac") is False


def test_auto_sanity_main_direct_execution(tmp_path, monkeypatch):
    """Verify main() CLI execution in-process with live html and spec export."""
    tc_path = tmp_path / "inprocess_tc.md"
    html_path = tmp_path / "inprocess_app.html"
    out_rep = tmp_path / "inprocess_report.md"
    out_spec = tmp_path / "inprocess_spec.spec.ts"
    out_ann = tmp_path / "inprocess_ann.md"

    html_path.write_text("""<!DOCTYPE html>
    <html><body>
      <label for="u">User</label><input type="text" id="u" name="user">
      <button id="btn-save">Lưu</button>
    </body></html>""", encoding="utf-8")

    tc_table = (
        "# Suite\n"
        "| TC ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags |\n"
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        "| TC_INP_01 | Module | Low | Test Inprocess | Ready | 1. Nhập 'admin' vào ô 'user'<br>2. Nhấp nút 'Lưu' | Success | Low | - | Yes | E2E | @Smoke |\n"
    )
    tc_path.write_text(tc_table, encoding="utf-8")

    test_args = [
        "auto_sanity_engine.py",
        str(tc_path),
        "--html", str(html_path),
        "-o", str(out_rep),
        "--export-spec", str(out_spec),
        "--annotated-output", str(out_ann)
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    ret = main()
    assert ret == 0
    assert out_rep.exists()
    assert out_spec.exists()
    assert out_ann.exists()

    ann_content = out_ann.read_text(encoding="utf-8")
    assert "@Live-Verified" in ann_content



