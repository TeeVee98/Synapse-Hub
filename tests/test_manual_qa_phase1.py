#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Unit Tests for Phase 1 Manual QA Upgrade:
- Validates 25 Field Types in field_validation_checklist.md
- Validates 9 Resilience Protocols (Unicode NFC/NFD, Emojis, Multi-Tab, etc.)
- Validates manual_tc_linter.py detection of 9-column tables and speculative words
"""

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.lint.manual_tc_linter import lint_test_case_file


def test_field_validation_checklist_has_25_fields():
    checklist_path = os.path.join(
        _REPO_ROOT,
        "skills", "02-test-design", "rbt-manual-testing", "references", "field_validation_checklist.md"
    )
    assert os.path.isfile(checklist_path), f"Checklist not found at {checklist_path}"

    with open(checklist_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check that all 25 field numbers are present in the table
    for i in range(1, 26):
        assert f"**{i}**" in content or f"| **{i}. " in content or f"| **{i}** |" in content, f"Field #{i} missing from 25-field checklist!"

    # Verify modern field names
    expected_fields = [
        "Advanced WYSIWYG & Table Editor",
        "Geo Location & Address Autocomplete",
        "Digital Signature Pad (Canvas)",
        "Biometric Authentication Token",
        "Camera / Barcode / QR Code Scanner",
        "Multi-Currency & Exchange Rate Formatter",
        "Auto-reading SMS / OTP Input",
        "Color Picker / Hex Code",
        "Tag & Tokenized Chip Input",
        "Cron Expression & Recurring Schedule"
    ]
    for field_name in expected_fields:
        assert field_name in content, f"Field '{field_name}' not found in checklist!"


def test_field_validation_checklist_has_9_resilience_protocols():
    checklist_path = os.path.join(
        _REPO_ROOT,
        "skills", "02-test-design", "rbt-manual-testing", "references", "field_validation_checklist.md"
    )
    with open(checklist_path, "r", encoding="utf-8") as f:
        content = f.read()

    protocols = [
        "Unicode Normalization & IME Vietnamese Composing",
        "NFC (Precomposed) vs NFD (Decomposed)",
        "4-Byte Surrogate Pairs UTF-8 & Emoji Safety",
        "utf8mb4",
        "Clipboard Paste Special & Invisible Control Characters",
        "Multi-Tab State Drift & Stepper Navigation",
        "Permission / RBAC Resilience",
        "Out-of-Order Webhook / Delayed IPN",
        "Device & Viewport Distortion (Mobile Virtual Keyboard)",
        "Data Lifecycle & Soft-Delete Cascading",
        "Edge Proxy 502/503/504 Handling"
    ]
    for p in protocols:
        assert p in content, f"Resilience protocol '{p}' missing from checklist!"


def test_manual_tc_linter_detects_column_deficit(tmp_path):
    # Create sample 9-column table
    bad_table_md = """# Test Table
| TC ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| TC_01 | Login | High | Test Title | Logged in | 1. Click button | Button clicked | High | N/A |
"""
    p = tmp_path / "sample_9col.md"
    p.write_text(bad_table_md, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["passed"] is False
    assert any(d["type"] == "COLUMN_COUNT_VIOLATION" for d in res["defects"])


def test_manual_tc_linter_detects_speculative_oracle(tmp_path):
    bad_oracle_md = """# Test Table
| TC ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| TC_01 | Login | High | Boundary test | Logged in | 1. Enter max text | Hệ thống có thể tự động cắt chuỗi HOẶC báo lỗi tùy backend | High | N/A | Yes | UI | @Smoke |
"""
    p = tmp_path / "sample_speculative.md"
    p.write_text(bad_oracle_md, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["passed"] is False
    assert any(d["type"] == "SPECULATIVE_ORACLE" for d in res["defects"])


def test_manual_tc_linter_passes_valid_iso_table(tmp_path):
    valid_md = """# Test Table
| TC ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| TC_01 | Login | High | Login Success | Tài khoản tồn tại | 1. Nhập user<br>2. Bấm Login | Chuyển hướng Dashboard hiển thị tiêu đề | High | user='admin' | Yes | UI | @Smoke |
"""
    p = tmp_path / "sample_valid.md"
    p.write_text(valid_md, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["passed"] is True
    assert len(res["defects"]) == 0


def test_manual_tc_linter_detects_semantic_duplication_bloat(tmp_path):
    """Verify Filter 2 detects duplicate test cases with > 85% similarity."""
    dupe_table_md = """# Duplicate Test Cases Table
| TC ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| TC_01 | Login | High | Đăng nhập tài khoản admin | Sẵn sàng | 1. Nhập username 'admin'<br>2. Nhập password '123'<br>3. Bấm Đăng nhập | Đăng nhập thành công | High | N/A | Yes | E2E | @Smoke |
| TC_02 | Login | High | Đăng nhập tài khoản admin | Sẵn sàng | 1. Nhập username 'admin'<br>2. Nhập password '123'<br>3. Bấm Đăng nhập | Đăng nhập thành công | High | N/A | Yes | E2E | @Regression |
"""
    p = tmp_path / "sample_dupe.md"
    p.write_text(dupe_table_md, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert any(w["type"] == "SEMANTIC_DUPLICATION_BLOAT" for w in res["warnings"])
    assert res["metrics"]["duplicate_cases"] >= 1

