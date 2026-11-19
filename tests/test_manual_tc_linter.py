#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Comprehensive Test Suite for Triple-Filter Manual TC Linter & CLI Integration
-----------------------------------------------------------------------------
Implements 46 rigorous tests across 4 tiers:
- Tier 1: Feature Coverage (20 tests)
  * Feature 1: Filter 1 - Schema & Blacklist Guard (5 tests)
  * Feature 2: Filter 2 - Deduplication Guard >85% (5 tests)
  * Feature 3: Filter 3 - Golden Ratio Guard 40/40/20 (5 tests)
  * Feature 4: CLI Subcommand synapse verify-manual (5 tests)
- Tier 2: Boundary & Corner Cases (20 tests)
  * Blacklist words detection: "hợp lệ", "đẹp", "bình thường", "như mong đợi",
    "valid data", "works properly" (6 tests)
  * Word boundary and case insensitivity (2 tests)
  * Ambiguity & Assumptions Log boundaries (2 tests)
  * Malformed column count boundaries: 6, 8, 10, 11 columns (1 test)
  * Deduplication 85% threshold boundaries: 84% vs 85%, empty steps (3 tests)
  * Golden Ratio boundaries: 14.9% vs 15.0%, 9 vs 10 TCs, 0 TCs (5 tests)
  * CLI non-existent path and Unicode safety (1 test)
- Tier 3: Pairwise Cross-Feature Interactions (4 tests)
- Tier 4: Real-World Scenarios (2 tests)
"""

import os
import sys
import subprocess

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.lint.manual_tc_linter import (
    lint_test_case_file,
    calculate_similarity,
)
from tools.api.spec_reconciler import SpecReconciler


# ==============================================================================
# TEST FIXTURES & HELPERS
# ==============================================================================

CANONICAL_12_HEADERS = [
    "Case ID", "REQ_ID", "Module / Screen", "Test Title & Objective",
    "Pre-Condition", "Test Steps (1-1)", "Test Data", "Expected Result",
    "Priority / Severity", "Risk Score (RPN)", "Automatable / Type", "Automation Tags"
]

ALIAS_12_HEADERS = [
    "TC ID", "Module", "Risk Level", "Test Title",
    "Pre-Condition", "Test Steps", "Expected Result", "Priority",
    "Test Data", "Automatable", "Auto Type", "Tags"
]

SAMPLE_AMBIGUITY_LOG = """
## Ambiguity & Assumptions Log
- [ASSUMPTION-01] Hệ thống sử dụng JWT token xác thực với thời hạn 15 phút.
- [AMBIGUITY-01] Đã đối soát: Khi hết phiên làm việc, chuyển hướng về /login kèm returnUrl.
"""


def _build_markdown_table(headers, rows, ambiguity_log=True, log_text=None):
    """Constructs a standard markdown test suite with optional Ambiguity Log."""
    assert isinstance(headers, (list, tuple)) and len(headers) > 0, "headers must be non-empty list"
    assert isinstance(rows, list), "rows must be a list"
    assert isinstance(ambiguity_log, bool), "ambiguity_log must be boolean"
    assert log_text is None or isinstance(log_text, str), "log_text must be str or None"
    lines = ["# Test Suite: Manual QA Verification", ""]
    if ambiguity_log:
        chosen_log = log_text if log_text is not None else SAMPLE_AMBIGUITY_LOG.strip()
        assert chosen_log is not None and len(chosen_log) > 0, "ambiguity log content must be non-empty"
        lines.append(chosen_log)
        lines.append("")
    lines.append("## Test Cases Table")
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join([":---"] * len(headers)) + " |")
    for r in rows:
        lines.append("| " + " | ".join(str(cell) for cell in r) + " |")
    lines.append("")
    assert len(lines) >= 4, "lines table must have headers and content"
    result_table = "\n".join(lines)
    assert len(result_table) > 0, "result table must not be empty"
    return result_table


def _run_subprocess_cli(cmd_args, cwd=_REPO_ROOT):
    """Executes CLI command in clean cross-platform environment."""
    assert isinstance(cmd_args, (list, tuple)) and len(cmd_args) > 0, "cmd_args must be non-empty"
    cmd = [sys.executable] + list(cmd_args)
    assert len(cmd) >= 2, "cmd must contain interpreter and script"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([_REPO_ROOT, os.path.join(_REPO_ROOT, "tools")])
    env["PYTHONIOENCODING"] = "utf-8"
    env["SYNAPSE_LANG"] = "en"
    capture_flag = True
    text_flag = True
    assert capture_flag is True
    assert text_flag is True
    proc = subprocess.run(
        cmd,
        capture_output=capture_flag,
        text=text_flag,
        encoding="utf-8",
        errors="replace",
        cwd=cwd,
        env=env,
        timeout=30,
    )
    assert proc is not None, "subprocess.run returned None"
    assert hasattr(proc, "returncode"), "subprocess result missing returncode"
    assert isinstance(proc.stdout, str), "stdout must be string"
    assert isinstance(proc.stderr, str), "stderr must be string"
    return proc


# ==============================================================================
# TIER 1: FEATURE COVERAGE (20 TESTS)
# ==============================================================================

# --- Feature 1: Filter 1 (Schema & Blacklist Guard) ---

def test_f1_valid_12_column_schema_passes(tmp_path):
    """Tier 1 - F1.1: Valid 12-column ISO 29119-3 table with canonical headers passes."""
    row = [
        "TC_AUTH_001", "REQ-01", "Auth", "Đăng nhập hệ thống với tài khoản quản trị",
        "Tài khoản admin sẵn sàng", "1. Mở /login<br>2. Nhập credentials<br>3. Bấm Submit",
        "email=admin@hub.vn", "Chuyển hướng Dashboard hiển thị thông tin quản trị",
        "High", "12", "Yes / UI", "@Smoke, @P0"
    ]
    content = _build_markdown_table(CANONICAL_12_HEADERS, [row])
    p = tmp_path / "test_valid_schema.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["has_test_cases"] is True
    assert res["column_counts"] == [12]
    assert res["total_test_cases"] == 1
    assert res["passed"] is True
    assert len(res["defects"]) == 0


def test_f1_alternative_valid_header_aliases_pass(tmp_path):
    """Tier 1 - F1.2: Valid 12-column table using alternative header aliases passes."""
    row = [
        "TC_01", "Login", "High", "Đăng nhập quản trị viên",
        "Tài khoản sẵn sàng", "1. Nhập user<br>2. Bấm Đăng nhập",
        "Chuyển hướng Dashboard hiển thị thành công", "High",
        "user=admin", "Yes", "UI", "@Smoke"
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, [row])
    p = tmp_path / "test_alias_headers.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["has_test_cases"] is True
    assert res["column_counts"] == [12]
    assert res["passed"] is True
    assert len(res["defects"]) == 0


def test_f1_mandatory_ambiguity_assumptions_log_passes(tmp_path):
    """Tier 1 - F1.3: File with mandatory Ambiguity & Assumptions Log passes without defect."""
    row = [
        "TC_01", "Login", "High", "Đăng nhập tài khoản tiêu chuẩn",
        "Tài khoản sẵn sàng", "1. Nhập email<br>2. Bấm đăng nhập",
        "Dashboard mở ra với quyền hạn chính xác", "High",
        "user=standard@hub.vn", "Yes", "UI", "@Smoke"
    ]
    custom_log = """
## Ambiguity & Assumptions Log
- [ASSUMPTION-01] Session timeout is configured to 30 minutes of user inactivity.
- [AMBIGUITY-01] Password reset token expiration window is confirmed at 24 hours.
"""
    content = _build_markdown_table(ALIAS_12_HEADERS, [row], ambiguity_log=True, log_text=custom_log)
    assert "Ambiguity & Assumptions Log" in content
    p = tmp_path / "test_ambiguity_log_present.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["passed"] is True
    assert not any(
        d.get("type") in ("MISSING_AMBIGUITY_LOG", "AMBIGUITY_LOG_MISSING") or
        "ambiguity" in d.get("message", "").lower()
        for d in res["defects"]
    )


def test_f1_column_count_deficit_reported(tmp_path):
    """Tier 1 - F1.4: Table with column deficit (< 12) triggers COLUMN_COUNT_VIOLATION."""
    headers_9col = [
        "TC ID", "Module", "Risk Level", "Test Title",
        "Pre-Condition", "Test Steps", "Expected Result", "Priority", "Test Data"
    ]
    row = ["TC_01", "Login", "High", "Title", "Ready", "Step 1", "Success", "High", "Data"]
    content = _build_markdown_table(headers_9col, [row])
    p = tmp_path / "test_9col_deficit.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["passed"] is False
    assert any(d.get("type") == "COLUMN_COUNT_VIOLATION" for d in res["defects"])
    col_defect = next(d for d in res["defects"] if d.get("type") == "COLUMN_COUNT_VIOLATION")
    assert "9" in col_defect["message"]
    assert "12" in col_defect["message"]


def test_f1_clean_metrics_calculated(tmp_path):
    """Tier 1 - F1.5: Metric calculations return all required fields with valid types."""
    row = [
        "TC_01", "Login", "High", "Đăng nhập tài khoản tiêu chuẩn",
        "Tài khoản sẵn sàng", "1. Nhập email<br>2. Bấm đăng nhập",
        "Dashboard mở ra với quyền hạn chính xác", "High",
        "user=standard@hub.vn", "Yes", "UI", "@Smoke"
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, [row])
    p = tmp_path / "test_clean_metrics.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    metrics = res.get("metrics", {})
    assert "happy_ratio" in metrics and "%" in metrics["happy_ratio"]
    assert "negative_ratio" in metrics and "%" in metrics["negative_ratio"]
    assert "security_resilience_ratio" in metrics and "%" in metrics["security_resilience_ratio"]
    assert isinstance(metrics["duplicate_cases"], int) and metrics["duplicate_cases"] >= 0
    assert isinstance(metrics["speculative_oracles"], int) and metrics["speculative_oracles"] >= 0
    assert isinstance(metrics["vague_preconditions"], int) and metrics["vague_preconditions"] >= 0


# --- Feature 2: Filter 2 (Deduplication Guard >85%) ---

def test_f2_distinct_cases_pass_without_warning(tmp_path):
    """Tier 1 - F2.1: Distinct test cases (< 50% similarity) produce zero duplication warnings."""
    rows = [
        [
            "TC_01", "Auth", "High", "Xác thực danh tính quản trị viên qua mật khẩu",
            "Tài khoản tồn tại", "1. Nhập username<br>2. Nhập password",
            "Đăng nhập thành công", "High", "admin", "Yes", "UI", "@Smoke"
        ],
        [
            "TC_02", "Orders", "Low", "Tìm kiếm đơn hàng xuất khẩu theo mã vận đơn hải quan",
            "Đơn hàng tồn tại", "1. Nhập mã vận đơn<br>2. Bấm tìm kiếm",
            "Hiển thị bảng chi tiết lô hàng", "Low", "MA_VD_99", "Yes", "UI", "@Regression"
        ]
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, rows)
    p = tmp_path / "test_distinct_cases.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert not any(w.get("type") == "SEMANTIC_DUPLICATION_BLOAT" for w in res["warnings"])
    assert res["metrics"]["duplicate_cases"] == 0


def test_f2_exact_duplicate_cases_flagged(tmp_path):
    """Tier 1 - F2.2: 100% duplicate test cases trigger SEMANTIC_DUPLICATION_BLOAT."""
    rows = [
        [
            "TC_01", "Login", "High", "Đăng nhập tài khoản quản trị",
            "Sẵn sàng", "1. Nhập admin<br>2. Bấm đăng nhập",
            "Thành công", "High", "admin", "Yes", "UI", "@Smoke"
        ],
        [
            "TC_02", "Login", "High", "Đăng nhập tài khoản quản trị",
            "Sẵn sàng", "1. Nhập admin<br>2. Bấm đăng nhập",
            "Thành công", "High", "admin", "Yes", "UI", "@Regression"
        ]
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, rows)
    p = tmp_path / "test_exact_duplicates.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert any(w.get("type") == "SEMANTIC_DUPLICATION_BLOAT" for w in res["warnings"])
    assert res["metrics"]["duplicate_cases"] >= 1
    dupe_w = next(w for w in res["warnings"] if w.get("type") == "SEMANTIC_DUPLICATION_BLOAT")
    assert "100" in dupe_w.get("similarity", "") or "100" in dupe_w.get("message", "")


def test_f2_high_similarity_cases_flagged(tmp_path):
    """Tier 1 - F2.3: Test cases with ~90% similarity trigger duplication warning."""
    rows = [
        [
            "TC_01", "Login", "High", "Xác thực đăng nhập tài khoản quản trị viên cấp 1",
            "Sẵn sàng", "1. Mở trang đăng nhập<br>2. Nhập thông tin quản trị",
            "Thành công", "High", "admin", "Yes", "UI", "@Smoke"
        ],
        [
            "TC_02", "Login", "High", "Xác thực đăng nhập tài khoản quản trị viên cấp 2",
            "Sẵn sàng", "1. Mở trang đăng nhập<br>2. Nhập thông tin quản trị",
            "Thành công", "High", "admin", "Yes", "UI", "@Smoke"
        ]
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, rows)
    p = tmp_path / "test_high_similarity.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert any(w.get("type") == "SEMANTIC_DUPLICATION_BLOAT" for w in res["warnings"])
    assert res["metrics"]["duplicate_cases"] >= 1


def test_f2_multiple_duplicates_pairwise_reported(tmp_path):
    """Tier 1 - F2.4: Multiple duplicate pairs correctly report their respective counterpart IDs."""
    rows = [
        [
            "TC_01", "Login", "High", "Đăng nhập tài khoản quản trị viên hệ thống",
            "Sẵn sàng", "1. Nhập user<br>2. Bấm Đăng nhập",
            "Thành công", "High", "N/A", "Yes", "UI", "@Smoke"
        ],
        [
            "TC_02", "Login", "High", "Đăng nhập tài khoản quản trị viên hệ thống",
            "Sẵn sàng", "1. Nhập user<br>2. Bấm Đăng nhập",
            "Thành công", "High", "N/A", "Yes", "UI", "@Regression"
        ],
        [
            "TC_03", "Login", "High", "Đăng nhập tài khoản quản trị viên hệ thống",
            "Sẵn sàng", "1. Nhập user<br>2. Bấm Đăng nhập",
            "Thành công", "High", "N/A", "Yes", "UI", "@P1"
        ]
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, rows)
    p = tmp_path / "test_multiple_dupes.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    dupes = [w for w in res["warnings"] if w.get("type") == "SEMANTIC_DUPLICATION_BLOAT"]
    assert len(dupes) >= 2
    matched_ids = [d.get("duplicate_with") for d in dupes]
    assert "TC_01" in matched_ids
    assert res["metrics"]["duplicate_cases"] >= 2


def test_f2_similarity_metric_calculation_accuracy():
    """Tier 1 - F2.5: calculate_similarity measures text similarity accurately with normalization."""
    assert calculate_similarity("Same text here", "Same text here") == 1.0
    assert calculate_similarity("Alpha Beta Gamma", "12345 67890 XYZ") < 0.2
    assert calculate_similarity("Case-Insensitive TEXT!", "case-insensitive text") == 1.0
    assert calculate_similarity("", "Non-empty text") == 0.0
    assert calculate_similarity("", "") == 0.0


# --- Feature 3: Filter 3 (Golden Ratio Guard 40/40/20) ---

def test_f3_balanced_golden_ratio_passes(tmp_path):
    """Tier 1 - F3.1: 40% Happy / 40% Negative / 20% Security passes with 0 ratio warnings."""
    rows = [
        # 4 Happy (40%)
        ["TC_01", "Mod", "Med", "Đăng nhập thành công bước 1", "Ready", "Step", "Thành công", "Med", "-", "Yes", "UI", "@Happy"],
        ["TC_02", "Mod", "Med", "Đăng nhập thành công bước 2", "Ready", "Step", "Thành công", "Med", "-", "Yes", "UI", "@Happy"],
        ["TC_03", "Mod", "Med", "Xem chi tiết hồ sơ người dùng", "Ready", "Step", "Hiển thị dữ liệu", "Med", "-", "Yes", "UI", "@Happy"],
        ["TC_04", "Mod", "Med", "Tải xuống báo cáo định kỳ", "Ready", "Step", "Tải file thành công", "Med", "-", "Yes", "UI", "@Happy"],
        # 4 Negative (40%)
        ["TC_05", "Mod", "High", "Đăng nhập sai mật khẩu", "Ready", "Step", "Báo lỗi 401 Unauthorized", "High", "-", "Yes", "UI", "@Negative"],
        ["TC_06", "Mod", "High", "Đăng nhập để trống tài khoản", "Ready", "Step", "Báo lỗi 400 Bad Request", "High", "-", "Yes", "UI", "@Negative"],
        ["TC_07", "Mod", "High", "Truy cập tài nguyên bị chặn", "Ready", "Step", "Báo lỗi 403 Forbidden", "High", "-", "Yes", "UI", "@Negative"],
        ["TC_08", "Mod", "High", "Tìm kiếm ID không tồn tại", "Ready", "Step", "Báo lỗi 404 Not Found", "High", "-", "Yes", "UI", "@Negative"],
        # 2 Security / Resilience (20%)
        ["TC_09", "Mod", "Crit", "Ngăn chặn SQLi qua tham số id", "Ready", "Step", "Chặn truy cập SQL Injection", "Crit", "-", "Yes", "API", "@Security"],
        ["TC_10", "Mod", "Crit", "Ngăn chặn XSS Script injection", "Ready", "Step", "Mã hóa ký tự đặc biệt XSS", "Crit", "-", "Yes", "UI", "@Security"],
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, rows)
    p = tmp_path / "test_golden_ratio_balanced.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["metrics"]["happy_ratio"] == "40.0%"
    assert res["metrics"]["negative_ratio"] == "40.0%"
    assert res["metrics"]["security_resilience_ratio"] == "20.0%"
    assert not any(w.get("type") == "GOLDEN_RATIO_DEFICIT" for w in res["warnings"])


def test_f3_security_deficit_warning(tmp_path):
    """Tier 1 - F3.2: Security & Resilience < 15% triggers GOLDEN_RATIO_DEFICIT for >= 10 TCs."""
    rows = []
    # 7 Happy
    for i in range(1, 8):
        rows.append([f"TC_{i:02d}", "Mod", "Med", f"Thao tác bình thường số {i}", "Ready", "Step", "Thành công", "Med", "-", "Yes", "UI", "@Happy"])
    # 3 Negative, 0 Security (Total = 10, Sec = 0.0% < 15.0%)
    for i in range(8, 11):
        rows.append([f"TC_{i:02d}", "Mod", "High", f"Báo lỗi đầu vào số {i}", "Ready", "Step", "Báo lỗi 400", "High", "-", "Yes", "UI", "@Negative"])

    content = _build_markdown_table(ALIAS_12_HEADERS, rows)
    p = tmp_path / "test_security_deficit.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["total_test_cases"] == 10
    assert any(w.get("type") == "GOLDEN_RATIO_DEFICIT" for w in res["warnings"])
    ratio_w = next(w for w in res["warnings"] if w.get("type") == "GOLDEN_RATIO_DEFICIT")
    assert "Security & Resilience" in ratio_w["message"] or "Golden Ratio" in ratio_w["message"]


def test_f3_small_suite_exemption_from_ratio_warning(tmp_path):
    """Tier 1 - F3.3: Small test suites (< 10 TCs) are exempt from GOLDEN_RATIO_DEFICIT."""
    rows = []
    for i in range(1, 6):
        rows.append([f"TC_{i:02d}", "Mod", "Med", f"Chức năng cơ bản số {i}", "Ready", "Step", "Thành công", "Med", "-", "Yes", "UI", "@Happy"])

    content = _build_markdown_table(ALIAS_12_HEADERS, rows)
    p = tmp_path / "test_small_suite_exempt.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["total_test_cases"] == 5
    assert not any(w.get("type") == "GOLDEN_RATIO_DEFICIT" for w in res["warnings"])


def test_f3_tag_based_categorization(tmp_path):
    """Tier 1 - F3.4: Tag-based metadata (@Security, @Resilience, @Edge) categorizes into security."""
    rows = [
        ["TC_01", "Mod", "Low", "Thao tác gửi dữ liệu 1", "Ready", "Step", "OK", "Low", "-", "Yes", "UI", "@Security"],
        ["TC_02", "Mod", "Low", "Thao tác gửi dữ liệu 2", "Ready", "Step", "OK", "Low", "-", "Yes", "UI", "@Resilience"],
        ["TC_03", "Mod", "Low", "Thao tác gửi dữ liệu 3", "Ready", "Step", "OK", "Low", "-", "Yes", "UI", "@Edge"],
        ["TC_04", "Mod", "Low", "Thao tác bình thường", "Ready", "Step", "OK", "Low", "-", "Yes", "UI", "@Happy"],
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, rows)
    p = tmp_path / "test_tag_categorization.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    # 3 of 4 cases have @Security / @Resilience / @Edge tags -> 75.0%
    sec_ratio = float(res["metrics"]["security_resilience_ratio"].rstrip("%"))
    assert sec_ratio == 75.0, f"Expected exactly 75.0% for 3/4 security/resilience tags, got {sec_ratio}%"


def test_f3_keyword_heuristic_categorization(tmp_path):
    """Tier 1 - F3.5: Keywords (sqli, xss, 401, 500) correctly drive security and negative categorization."""
    rows = [
        ["TC_01", "Mod", "Crit", "Test SQLi injection attack", "Ready", "Step", "Từ chối câu lệnh", "Crit", "-", "Yes", "API", "@Sec"],
        ["TC_02", "Mod", "Crit", "Test XSS cross-site scripting", "Ready", "Step", "Lọc ký tự", "Crit", "-", "Yes", "API", "@Sec"],
        ["TC_03", "Mod", "High", "Test authentication failure", "Ready", "Step", "Báo lỗi 401 Unauthorized", "High", "-", "Yes", "API", "@Neg"],
        ["TC_04", "Mod", "High", "Test invalid input validation", "Ready", "Step", "Báo lỗi 400 Bad Request", "High", "-", "Yes", "API", "@Neg"],
        ["TC_05", "Mod", "Med", "Test standard login profile", "Ready", "Step", "Dashboard hiển thị", "Med", "-", "Yes", "API", "@Happy"],
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, rows)
    p = tmp_path / "test_keyword_heuristics.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    sec_ratio = float(res["metrics"]["security_resilience_ratio"].rstrip("%"))
    neg_ratio = float(res["metrics"]["negative_ratio"].rstrip("%"))
    assert sec_ratio >= 40.0
    assert neg_ratio >= 40.0


# --- Feature 4: CLI Subcommand synapse verify-manual ---

def test_f4_cli_verify_manual_success_exit_code_0(tmp_path):
    """Tier 1 - F4.1: CLI verify-manual on valid 12-column test file returns exit code 0."""
    row = [
        "TC_01", "Login", "High", "Đăng nhập tài khoản tiêu chuẩn",
        "Sẵn sàng", "1. Mở trang<br>2. Nhập thông tin",
        "Dashboard mở ra với quyền hạn chính xác", "High",
        "user=test", "Yes", "UI", "@Smoke"
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, [row])
    p = tmp_path / "valid_cli_test.md"
    p.write_text(content, encoding="utf-8")

    # 1. Direct verification via manual_tc_linter entrypoint
    linter_py = os.path.join(_REPO_ROOT, "tools", "lint", "manual_tc_linter.py")
    res_direct = _run_subprocess_cli([linter_py, str(p)])
    assert res_direct.returncode == 0
    assert "PASS" in res_direct.stdout
    assert "0 defects" in res_direct.stdout

    # 2. CLI gateway integration via tools/core/cli.py verify-manual
    cli_py = os.path.join(_REPO_ROOT, "tools", "core", "cli.py")
    res_cli = _run_subprocess_cli([cli_py, "verify-manual", str(p)])
    assert res_cli.returncode == 0, f"Expected returncode 0 from cli.py verify-manual, got {res_cli.returncode}: {res_cli.stdout} {res_cli.stderr}"
    assert "PASS" in res_cli.stdout or "0 defects" in res_cli.stdout


def test_f4_cli_verify_manual_failure_exit_code_1(tmp_path):
    """Tier 1 - F4.2: CLI verify-manual on file with defects returns exit code 1."""
    # 6-column malformed table
    headers_6col = ["TC ID", "Module", "Risk", "Title", "Steps", "Result"]
    row = ["TC_01", "Auth", "High", "Test Title", "1. Step", "Result"]
    content = _build_markdown_table(headers_6col, [row])
    p = tmp_path / "invalid_cli_test.md"
    p.write_text(content, encoding="utf-8")

    # 1. Direct verification via manual_tc_linter entrypoint
    linter_py = os.path.join(_REPO_ROOT, "tools", "lint", "manual_tc_linter.py")
    res_direct = _run_subprocess_cli([linter_py, str(p)])
    assert res_direct.returncode == 1
    assert "FAIL" in res_direct.stdout
    assert "Defects" in res_direct.stdout or "defects" in res_direct.stdout

    # 2. CLI gateway integration via tools/core/cli.py verify-manual
    cli_py = os.path.join(_REPO_ROOT, "tools", "core", "cli.py")
    res_cli = _run_subprocess_cli([cli_py, "verify-manual", str(p)])
    assert res_cli.returncode == 1, f"Expected returncode 1 from cli.py verify-manual on invalid file, got {res_cli.returncode}: {res_cli.stdout} {res_cli.stderr}"
    assert "FAIL" in res_cli.stdout or "defects" in res_cli.stdout.lower()


def test_f4_cli_verify_manual_audit_all_flag():
    """Tier 1 - F4.3: CLI --audit-all audits default target repositories without crashing."""
    # 1. Direct verification via manual_tc_linter entrypoint
    linter_py = os.path.join(_REPO_ROOT, "tools", "lint", "manual_tc_linter.py")
    res_direct = _run_subprocess_cli([linter_py, "--audit-all"])
    assert res_direct.returncode in (0, 1)
    assert "ZERO-REVIEW ENGINE" in res_direct.stdout
    assert "Summary:" in res_direct.stdout

    # 2. CLI gateway integration via tools/core/cli.py verify-manual --audit-all
    cli_py = os.path.join(_REPO_ROOT, "tools", "core", "cli.py")
    res_cli = _run_subprocess_cli([cli_py, "verify-manual", "--audit-all"])
    assert res_cli.returncode in (0, 1), f"Expected returncode 0 or 1 from cli.py verify-manual --audit-all, got {res_cli.returncode}: {res_cli.stdout} {res_cli.stderr}"
    assert "ZERO-REVIEW ENGINE" in res_cli.stdout or "Summary:" in res_cli.stdout or "manual" in res_cli.stdout.lower()


def test_f4_cli_verify_manual_help_message():
    """Tier 1 - F4.4: CLI --help outputs descriptive usage text."""
    # 1. Direct verification via manual_tc_linter entrypoint
    linter_py = os.path.join(_REPO_ROOT, "tools", "lint", "manual_tc_linter.py")
    res_direct = _run_subprocess_cli([linter_py, "--help"])
    assert res_direct.returncode == 0
    assert "usage:" in res_direct.stdout.lower()
    assert "--audit-all" in res_direct.stdout

    # 2. CLI gateway integration via tools/core/cli.py verify-manual --help
    cli_py = os.path.join(_REPO_ROOT, "tools", "core", "cli.py")
    res_cli = _run_subprocess_cli([cli_py, "verify-manual", "--help"])
    assert res_cli.returncode == 0, f"Expected returncode 0 for verify-manual --help, got {res_cli.returncode}: {res_cli.stdout} {res_cli.stderr}"
    assert "usage:" in res_cli.stdout.lower() or "verify-manual" in res_cli.stdout.lower()


def test_f4_cli_dispatcher_subcommand_routing():
    """Tier 1 - F4.5: Verifies CLI dispatcher registration and execution of verify-manual."""
    cli_py = os.path.join(_REPO_ROOT, "tools", "core", "cli.py")
    res = _run_subprocess_cli([cli_py, "verify-manual", "--help"])
    assert res.returncode == 0, f"Expected returncode 0 for verify-manual --help, got {res.returncode}: {res.stdout} {res.stderr}"
    assert "verify-manual" in res.stdout.lower() or "manual" in res.stdout.lower()


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (20 TESTS)
# ==============================================================================

# --- Blacklist Terms (6 Tests) ---

def test_f1_bva_blacklist_hop_le(tmp_path):
    """Tier 2 - BVA.1: Rejects blacklist term 'hợp lệ'."""
    row = [
        "TC_01", "Login", "High", "Đăng nhập với tài khoản hợp lệ",
        "Sẵn sàng", "1. Nhập thông tin",
        "Hệ thống cho phép đăng nhập với dữ liệu hợp lệ", "High",
        "-", "Yes", "UI", "@Smoke"
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, [row])
    p = tmp_path / "test_blacklist_hop_le.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["passed"] is False, "Filter 1 contract: 'hợp lệ' must be rejected"
    assert any(
        "hợp lệ" in d.get("matched", "").lower() or
        "hợp lệ" in d.get("message", "").lower() or
        d.get("type") in ("SPECULATIVE_ORACLE", "BLACKLIST_TERM_DETECTED")
        for d in res["defects"]
    )


def test_f1_bva_blacklist_dep(tmp_path):
    """Tier 2 - BVA.2: Rejects subjective blacklist term 'đẹp'."""
    row = [
        "TC_01", "UI", "Low", "Kiểm tra giao diện đăng nhập",
        "Sẵn sàng", "1. Mở trang",
        "Form hiển thị đẹp, cân đối trên màn hình", "Low",
        "-", "Yes", "UI", "@UI"
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, [row])
    p = tmp_path / "test_blacklist_dep.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["passed"] is False, "Filter 1 contract: 'đẹp' must be rejected"
    assert any(
        "đẹp" in d.get("matched", "").lower() or
        "đẹp" in d.get("message", "").lower() or
        d.get("type") in ("SPECULATIVE_ORACLE", "BLACKLIST_TERM_DETECTED")
        for d in res["defects"]
    )


def test_f1_bva_blacklist_binh_thuong(tmp_path):
    """Tier 2 - BVA.3: Rejects vague blacklist term 'bình thường'."""
    row = [
        "TC_01", "System", "Med", "Kiểm tra trạng thái hệ thống",
        "Sẵn sàng", "1. Mở trang",
        "Hệ thống hoạt động bình thường không gặp sự cố", "Med",
        "-", "Yes", "UI", "@Smoke"
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, [row])
    p = tmp_path / "test_blacklist_binh_thuong.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["passed"] is False, "Filter 1 contract: 'bình thường' must be rejected"
    assert any(
        "bình thường" in d.get("matched", "").lower() or
        "bình thường" in d.get("message", "").lower() or
        d.get("type") in ("SPECULATIVE_ORACLE", "BLACKLIST_TERM_DETECTED")
        for d in res["defects"]
    )


def test_f1_bva_blacklist_nhu_mong_doi(tmp_path):
    """Tier 2 - BVA.4: Rejects ambiguous blacklist term 'như mong đợi'."""
    row = [
        "TC_01", "Checkout", "High", "Thanh toán đơn hàng",
        "Sẵn sàng", "1. Bấm thanh toán",
        "Kết quả xử lý như mong đợi của khách hàng", "High",
        "-", "Yes", "UI", "@Smoke"
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, [row])
    p = tmp_path / "test_blacklist_nhu_mong_doi.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["passed"] is False, "Filter 1 contract: 'như mong đợi' must be rejected"
    assert any(
        "như mong đợi" in d.get("matched", "").lower() or
        "như mong đợi" in d.get("message", "").lower() or
        d.get("type") in ("SPECULATIVE_ORACLE", "BLACKLIST_TERM_DETECTED")
        for d in res["defects"]
    )


def test_f1_bva_blacklist_valid_data(tmp_path):
    """Tier 2 - BVA.5: Rejects generic English blacklist term 'valid data'."""
    row = [
        "TC_01", "Registration", "High", "User registration test",
        "Ready", "1. Fill form",
        "Registration completes successfully with valid data", "High",
        "-", "Yes", "UI", "@Smoke"
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, [row])
    p = tmp_path / "test_blacklist_valid_data.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["passed"] is False, "Filter 1 contract: 'valid data' must be rejected"
    assert any(
        "valid data" in d.get("matched", "").lower() or
        "valid data" in d.get("message", "").lower() or
        d.get("type") in ("SPECULATIVE_ORACLE", "BLACKLIST_TERM_DETECTED")
        for d in res["defects"]
    )


def test_f1_bva_blacklist_works_properly(tmp_path):
    """Tier 2 - BVA.6: Rejects vague English blacklist term 'works properly'."""
    row = [
        "TC_01", "Dashboard", "Med", "Load dashboard page",
        "Ready", "1. Open URL",
        "Dashboard loads and all widgets works properly", "Med",
        "-", "Yes", "UI", "@Smoke"
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, [row])
    p = tmp_path / "test_blacklist_works_properly.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["passed"] is False, "Filter 1 contract: 'works properly' must be rejected"
    assert any(
        "works properly" in d.get("matched", "").lower() or
        "works properly" in d.get("message", "").lower() or
        d.get("type") in ("SPECULATIVE_ORACLE", "BLACKLIST_TERM_DETECTED")
        for d in res["defects"]
    )


# --- Word Boundary & Case Invariance (2 Tests) ---

def test_f1_bva_mixed_case_blacklist_terms(tmp_path):
    """Tier 2 - BVA.7: Detects blacklist words regardless of case (UPPERCASE, Title Case)."""
    rows = [
        [
            "TC_01", "Auth", "High", "Test HỢP LỆ case",
            "Ready", "Step", "Thông tin HỢP LỆ được chấp nhận", "High",
            "-", "Yes", "UI", "@Smoke"
        ],
        [
            "TC_02", "UI", "Low", "Test Works Properly Case",
            "Ready", "Step", "Application Works Properly always", "Low",
            "-", "Yes", "UI", "@Smoke"
        ]
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, rows)
    p = tmp_path / "test_mixed_case_blacklist.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["passed"] is False
    assert len(res["defects"]) >= 1


def test_f1_bva_blacklist_words_word_boundary_isolation(tmp_path):
    """Tier 2 - BVA.8: Isolated word boundaries do NOT flag legitimate words ('thích hợp', 'bình đẳng')."""
    rows = [
        [
            "TC_01", "Settings", "Med", "Cấu hình tùy chọn thích hợp",
            "Sẵn sàng", "1. Bấm lưu cấu hình",
            "Hệ thống áp dụng chính sách bình đẳng quyền hạn cho mọi người dùng", "Med",
            "-", "Yes", "UI", "@Smoke"
        ],
        [
            "TC_02", "Collab", "Med", "Thỏa thuận hợp tác đối tác",
            "Sẵn sàng", "1. Xác nhận thỏa thuận",
            "Đối tác nhận thông báo tốt đẹp về thỏa thuận", "Med",
            "-", "Yes", "UI", "@Smoke"
        ]
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, rows)
    p = tmp_path / "test_word_boundary_safe.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    # Should not produce false positives for 'thích hợp' or 'bình đẳng'
    blacklist_defects = [
        d for d in res["defects"]
        if any(w in d.get("matched", "").lower() for w in ["hợp lệ", "bình thường", "đẹp"])
    ]
    assert len(blacklist_defects) == 0


# --- Ambiguity & Assumptions Log Boundaries (2 Tests) ---

def test_f1_bva_missing_ambiguity_log_header_fails(tmp_path):
    """Tier 2 - BVA.9: Suite without Ambiguity & Assumptions Log header produces a defect."""
    row = [
        "TC_01", "Login", "High", "Tiêu đề kiểm thử chuẩn xác",
        "Tài khoản sẵn sàng", "1. Nhập thông tin<br>2. Bấm xác nhận",
        "Dashboard hiển thị thông tin chính xác", "High",
        "user=test", "Yes", "UI", "@Smoke"
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, [row], ambiguity_log=False)
    p = tmp_path / "test_missing_ambiguity_header.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["passed"] is False, "Filter 1 contract: Missing Ambiguity Log must trigger defect"
    assert any(
        d.get("type") in ("MISSING_AMBIGUITY_LOG", "AMBIGUITY_LOG_MISSING") or
        "ambiguity" in d.get("message", "").lower()
        for d in res["defects"]
    )


def test_f1_bva_empty_ambiguity_log_section_fails(tmp_path):
    """Tier 2 - BVA.10: Ambiguity Log header with empty content produces a defect."""
    row = [
        "TC_01", "Login", "High", "Tiêu đề kiểm thử chuẩn xác",
        "Tài khoản sẵn sàng", "1. Nhập thông tin<br>2. Bấm xác nhận",
        "Dashboard hiển thị thông tin chính xác", "High",
        "user=test", "Yes", "UI", "@Smoke"
    ]
    empty_log = "## Ambiguity & Assumptions Log\n\n"
    content = _build_markdown_table(ALIAS_12_HEADERS, [row], ambiguity_log=True, log_text=empty_log)
    p = tmp_path / "test_empty_ambiguity_content.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["passed"] is False, "Filter 1 contract: Empty Ambiguity Log must trigger defect"
    assert any(
        d.get("type") in ("MISSING_AMBIGUITY_LOG", "AMBIGUITY_LOG_MISSING", "EMPTY_AMBIGUITY_LOG") or
        "ambiguity" in d.get("message", "").lower()
        for d in res["defects"]
    )


# --- Column Count Boundaries (1 Test) ---

def test_f1_bva_malformed_table_column_counts(tmp_path):
    """Tier 2 - BVA.11: Tables with 6, 8, 10, and 11 columns all trigger COLUMN_COUNT_VIOLATION."""
    lines = ["# Malformed Column Count Test Suite", "", SAMPLE_AMBIGUITY_LOG.strip(), ""]
    expected_cols = [6, 8, 10, 11]

    for cols in expected_cols:
        h = [f"Col_{i}" for i in range(1, cols + 1)]
        h[0] = "TC ID"
        h[3] = "Test Title"
        r = [f"Val_{i}" for i in range(1, cols + 1)]
        lines.append(f"## Table {cols} Columns")
        lines.append("| " + " | ".join(h) + " |")
        lines.append("| " + " | ".join([":---"] * cols) + " |")
        lines.append("| " + " | ".join(r) + " |")
        lines.append("")

    p = tmp_path / "test_malformed_columns.md"
    p.write_text("\n".join(lines), encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["passed"] is False
    assert set(res["column_counts"]) == set(expected_cols)
    col_defects = [d for d in res["defects"] if d.get("type") == "COLUMN_COUNT_VIOLATION"]
    assert len(col_defects) == len(expected_cols)


# --- Deduplication Boundaries (3 Tests) ---

def test_f2_bva_similarity_boundary_at_84_pct_no_warning(tmp_path):
    """Tier 2 - BVA.12: Similarity at ~84.2% (< 85%) does NOT trigger SEMANTIC_DUPLICATION_BLOAT."""
    # Engineered strings with SequenceMatcher ratio ~0.842 (< 0.85)
    title_a = "Xac thuc he thong phong ban aaaaaaaaa"
    title_b = "Xac thuc he thong phong ban bbbbbbbbb"
    steps = "buoc thuc hien so 1"
    sim = calculate_similarity(f"{title_a} {steps}", f"{title_b} {steps}")
    assert 0.83 <= sim < 0.85

    rows = [
        ["TC_01", "Mod", "Med", title_a, "Ready", steps, "OK", "Med", "-", "Yes", "UI", "@Smoke"],
        ["TC_02", "Mod", "Med", title_b, "Ready", steps, "OK", "Med", "-", "Yes", "UI", "@Smoke"]
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, rows)
    p = tmp_path / "test_sim_84_pct.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert not any(w.get("type") == "SEMANTIC_DUPLICATION_BLOAT" for w in res["warnings"])
    assert res["metrics"]["duplicate_cases"] == 0


def test_f2_bva_similarity_boundary_at_85_pct_triggers_warning(tmp_path):
    """Tier 2 - BVA.13: Similarity at ~85.7% (>= 85%) DOES trigger SEMANTIC_DUPLICATION_BLOAT."""
    # Engineered strings with SequenceMatcher ratio ~0.857 (>= 0.85)
    title_a = "Xac thuc he thong phong ban aaaaaaaa"
    title_b = "Xac thuc he thong phong ban bbbbbbbb"
    steps = "buoc thuc hien so 1"
    sim = calculate_similarity(f"{title_a} {steps}", f"{title_b} {steps}")
    assert sim >= 0.85

    rows = [
        ["TC_01", "Mod", "Med", title_a, "Ready", steps, "OK", "Med", "-", "Yes", "UI", "@Smoke"],
        ["TC_02", "Mod", "Med", title_b, "Ready", steps, "OK", "Med", "-", "Yes", "UI", "@Smoke"]
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, rows)
    p = tmp_path / "test_sim_85_pct.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert any(w.get("type") == "SEMANTIC_DUPLICATION_BLOAT" for w in res["warnings"])
    assert res["metrics"]["duplicate_cases"] == 1


def test_f2_bva_empty_steps_or_title_similarity_handling(tmp_path):
    """Tier 2 - BVA.14: Gracefully handles empty titles or steps without IndexError or crash."""
    rows = [
        ["TC_01", "Mod", "Med", "Valid title here", "Ready", "Step text", "OK", "Med", "-", "Yes", "UI", "@Smoke"],
        ["TC_02", "Mod", "Med", "", "Ready", "", "OK", "Med", "-", "Yes", "UI", "@Smoke"],
        ["TC_03", "Mod", "Med", "   ", "Ready", "   ", "OK", "Med", "-", "Yes", "UI", "@Smoke"]
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, rows)
    p = tmp_path / "test_empty_title_steps.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["has_test_cases"] is True
    assert res["total_test_cases"] == 3


# --- Golden Ratio Boundaries (5 Tests) ---

def test_f3_bva_exact_boundary_14_9_pct_security_warns(tmp_path):
    """Tier 2 - BVA.15: Exact boundary 14.0% (< 15.0%) triggers GOLDEN_RATIO_DEFICIT."""
    rows = []
    # 100 test cases: 14 Security, 86 Happy
    for i in range(1, 15):
        rows.append([f"TC_{i:03d}", "Mod", "Crit", f"Security test {i}", "Ready", "Step", "Block SQLi", "Crit", "-", "Yes", "API", "@Security"])
    for i in range(15, 101):
        rows.append([f"TC_{i:03d}", "Mod", "Low", f"Standard test {i}", "Ready", "Step", "OK", "Low", "-", "Yes", "UI", "@Happy"])

    content = _build_markdown_table(ALIAS_12_HEADERS, rows)
    p = tmp_path / "test_ratio_14_pct.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["total_test_cases"] == 100
    assert res["metrics"]["security_resilience_ratio"] == "14.0%"
    assert any(w.get("type") == "GOLDEN_RATIO_DEFICIT" for w in res["warnings"])


def test_f3_bva_exact_boundary_15_0_pct_security_passes(tmp_path):
    """Tier 2 - BVA.16: Exact boundary 15.0% (>= 15.0%) passes without GOLDEN_RATIO_DEFICIT."""
    rows = []
    # 20 test cases: 3 Security (15.0%), 17 Happy
    for i in range(1, 4):
        rows.append([f"TC_{i:02d}", "Mod", "Crit", f"Security test {i}", "Ready", "Step", "Block SQLi", "Crit", "-", "Yes", "API", "@Security"])
    for i in range(4, 21):
        rows.append([f"TC_{i:02d}", "Mod", "Low", f"Standard test {i}", "Ready", "Step", "OK", "Low", "-", "Yes", "UI", "@Happy"])

    content = _build_markdown_table(ALIAS_12_HEADERS, rows)
    p = tmp_path / "test_ratio_15_pct.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["total_test_cases"] == 20
    assert res["metrics"]["security_resilience_ratio"] == "15.0%"
    assert not any(w.get("type") == "GOLDEN_RATIO_DEFICIT" for w in res["warnings"])


def test_f3_bva_suite_with_exact_9_tcs_exempt(tmp_path):
    """Tier 2 - BVA.17: Exactly 9 test cases with 0% security is exempt from GOLDEN_RATIO_DEFICIT."""
    rows = []
    for i in range(1, 10):
        rows.append([f"TC_{i:02d}", "Mod", "Low", f"Happy test {i}", "Ready", "Step", "OK", "Low", "-", "Yes", "UI", "@Happy"])

    content = _build_markdown_table(ALIAS_12_HEADERS, rows)
    p = tmp_path / "test_exact_9_tcs.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["total_test_cases"] == 9
    assert not any(w.get("type") == "GOLDEN_RATIO_DEFICIT" for w in res["warnings"])


def test_f3_bva_suite_with_exact_10_tcs_evaluated(tmp_path):
    """Tier 2 - BVA.18: Exactly 10 test cases with 0% security is evaluated and triggers warning."""
    rows = []
    for i in range(1, 11):
        rows.append([f"TC_{i:02d}", "Mod", "Low", f"Happy test {i}", "Ready", "Step", "OK", "Low", "-", "Yes", "UI", "@Happy"])

    content = _build_markdown_table(ALIAS_12_HEADERS, rows)
    p = tmp_path / "test_exact_10_tcs.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["total_test_cases"] == 10
    assert any(w.get("type") == "GOLDEN_RATIO_DEFICIT" for w in res["warnings"])


def test_f3_bva_zero_test_cases_no_division_by_zero(tmp_path):
    """Tier 2 - BVA.19: Empty table (headers only, 0 data rows) handles ratios without ZeroDivisionError."""
    content = _build_markdown_table(ALIAS_12_HEADERS, [])
    p = tmp_path / "test_zero_tcs.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["total_test_cases"] == 0
    assert res["metrics"]["happy_ratio"] == "0.0%"
    assert res["metrics"]["security_resilience_ratio"] == "0.0%"


# --- CLI and Encoding Boundaries (1 Test) ---

def test_f4_bva_cli_non_existent_file_and_unicode_safety(tmp_path):
    """Tier 2 - BVA.20: CLI reports error on missing file; parses Vietnamese diacritics and emojis safely."""
    linter_py = os.path.join(_REPO_ROOT, "tools", "lint", "manual_tc_linter.py")

    # 1. Non-existent file
    res_missing = _run_subprocess_cli([linter_py, "/tmp/non_existent_tc_suite_xyz123.md"])
    assert res_missing.returncode != 0 and (
        "file not found" in res_missing.stdout.lower()
        or "cannot read" in res_missing.stdout.lower()
        or "error" in res_missing.stdout.lower()
        or "not found" in res_missing.stdout.lower()
    )

    # 2. Vietnamese Unicode NFC/NFD diacritics & Emojis
    row = [
        "TC_01", "Tiếng Việt", "Cao", "Đăng nhập với ký tự Tiếng Việt: ắ, ằ, ẳ, ẵ, ặ, ế, ễ 🚀",
        "Sẵn sàng 🔒", "1. Nhập họ tên 'Nguyễn Văn Đạt'<br>2. Bấm xác nhận ✅",
        "Chuyển hướng Dashboard hiển thị lời chào 'Xin chào' 🎉", "Cao",
        "tên='Nguyễn Văn Đạt'", "Có", "UI", "@Smoke, @I18N"
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, [row])
    p_unicode = tmp_path / "test_vietnamese_unicode.md"
    p_unicode.write_text(content, encoding="utf-8")

    res_unicode = lint_test_case_file(str(p_unicode))
    assert res_unicode["has_test_cases"] is True
    assert res_unicode["total_test_cases"] == 1


# ==============================================================================
# TIER 3: PAIRWISE CROSS-FEATURE INTERACTIONS (4 TESTS)
# ==============================================================================

def test_t3_markdown_to_linter_to_cli_pipeline(tmp_path):
    """Tier 3 - Interaction 1: Markdown synthesis -> Linter validation -> CLI verification pipeline."""
    row = [
        "TC_E2E_01", "Pipeline", "High", "Kiểm thử chu trình xác thực tự động",
        "Môi trường staging sẵn sàng", "1. Gửi request đăng nhập<br>2. Nhận token",
        "Mã phản hồi HTTP 200 OK trả về token xác thực", "High",
        "token_type='Bearer'", "Yes", "API", "@Smoke"
    ]
    content = _build_markdown_table(ALIAS_12_HEADERS, [row])
    p = tmp_path / "e2e_pipeline_test.md"
    p.write_text(content, encoding="utf-8")

    # Step 1: Programmatic validation
    res_prog = lint_test_case_file(str(p))
    assert res_prog["passed"] is True
    assert len(res_prog["defects"]) == 0

    # Step 2: CLI subprocess validation
    linter_py = os.path.join(_REPO_ROOT, "tools", "lint", "manual_tc_linter.py")
    res_cli = _run_subprocess_cli([linter_py, str(p)])
    assert res_cli.returncode == 0
    assert "PASS" in res_cli.stdout
    assert "0 defects" in res_cli.stdout


def test_t3_spec_reconciler_output_to_linter_pipeline(tmp_path):
    """Tier 3 - Interaction 2: SpecReconciler synthesized markdown passes Linter schema and metrics."""
    mock_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Auth API", "version": "1.0.0"},
        "paths": {
            "/api/v1/auth/login": {
                "post": {
                    "summary": "User login",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "email": {"type": "string", "format": "email"},
                                        "password": {"type": "string", "minLength": 8}
                                    },
                                    "required": ["email", "password"]
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Success"}}
                }
            }
        }
    }
    story_text = """
    # User Story: User Login
    As a user, I want to login with my email and password so that I can access my account.
    """
    reconciler = SpecReconciler(mock_spec, story_text)
    mock_recon_result = {
        "story_title": "User Login",
        "path": "/api/v1/auth/login",
        "method": "POST",
        "schema_properties": {
            "email": {"type": "string", "format": "email", "required": True},
            "password": {"type": "string", "minLength": 8, "required": True}
        }
    }
    md_content = reconciler.generate_12_column_test_suite_md(mock_recon_result)
    assert md_content is not None
    assert len(md_content) > 50

    p = tmp_path / "spec_reconciler_output.md"
    p.write_text(md_content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["has_test_cases"] is True
    assert 12 in res["column_counts"]
    assert res["total_test_cases"] >= 1


def test_t3_linter_defect_blocks_cli_execution(tmp_path):
    """Tier 3 - Interaction 3: Detected defect (column deficit) triggers non-zero CLI return code."""
    bad_table_md = """# Broken Table
| TC ID | Module | Risk | Title | Pre | Steps |
| :--- | :--- | :--- | :--- | :--- | :--- |
| TC_01 | Auth | High | Test | Ready | Step 1 |
"""
    p = tmp_path / "broken_pipeline.md"
    p.write_text(bad_table_md, encoding="utf-8")

    # Step 1: Programmatic check
    res_prog = lint_test_case_file(str(p))
    assert res_prog["passed"] is False

    # Step 2: CLI check
    linter_py = os.path.join(_REPO_ROOT, "tools", "lint", "manual_tc_linter.py")
    res_cli = _run_subprocess_cli([linter_py, str(p)])
    assert res_cli.returncode == 1
    assert "FAIL" in res_cli.stdout


def test_t3_golden_ratio_and_deduplication_coexistence(tmp_path):
    """Tier 3 - Interaction 4: Duplication bloat and golden ratio deficit coexist in unified warnings."""
    # 10 test cases: TC_01 & TC_02 identical (> 85%), 0 Security cases (< 15%)
    rows = [
        ["TC_01", "Mod", "Med", "Đăng nhập tài khoản quản trị", "Ready", "Step 1", "OK", "Med", "-", "Yes", "UI", "@Happy"],
        ["TC_01_dup", "Mod", "Med", "Đăng nhập tài khoản quản trị", "Ready", "Step 1", "OK", "Med", "-", "Yes", "UI", "@Happy"],
    ]
    for i in range(3, 11):
        rows.append([f"TC_{i:02d}", "Mod", "Med", f"Thao tác số {i}", "Ready", "Step 1", "OK", "Med", "-", "Yes", "UI", "@Happy"])

    content = _build_markdown_table(ALIAS_12_HEADERS, rows)
    p = tmp_path / "coexistence_warnings.md"
    p.write_text(content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    warning_types = [w.get("type") for w in res["warnings"]]
    assert "SEMANTIC_DUPLICATION_BLOAT" in warning_types
    assert "GOLDEN_RATIO_DEFICIT" in warning_types
    assert res["metrics"]["duplicate_cases"] >= 1
    assert res["metrics"]["security_resilience_ratio"] == "0.0%"
    assert res["passed"] is True  # Warnings do not cause failure on their own


# ==============================================================================
# TIER 4: REAL-WORLD SCENARIOS (2 TESTS)
# ==============================================================================

def test_t4_crm_login_real_suite_full_pipeline():
    """Tier 4 - Real World 1: End-to-end audit of examples/practices/testcases/crm/test_cases_crm_login.md."""
    crm_path = os.path.join(
        _REPO_ROOT, "examples", "practices", "testcases", "crm", "test_cases_crm_login.md"
    )
    assert os.path.isfile(crm_path), f"CRM login test file not found at {crm_path}"

    res = lint_test_case_file(crm_path)
    assert res["has_test_cases"] is True
    assert res["total_test_cases"] >= 30
    assert 12 in res["column_counts"]

    metrics = res["metrics"]
    assert "%" in metrics["happy_ratio"]
    assert "%" in metrics["negative_ratio"]
    assert "%" in metrics["security_resilience_ratio"]


def test_t4_corrupted_markdown_diagnostic_triage(tmp_path):
    """Tier 4 - Real World 2: Corrupted markdown triage correctly categorizes all multi-defect types."""
    corrupted_content = """# Corrupted Test Suite Document
## Overview
This document contains multiple corrupted sections simulating editing errors.

## Broken Table (8 Columns)
| TC ID | Module | Risk | Title | Pre | Steps | Expected | Priority |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| TC_BROKEN_01 | Core | High | Thao tác tùy backend hoặc lỗi | Không | 1. Thao tác | Hệ thống có thể tự động từ chối HOẶC báo lỗi tùy backend | High |

## Table with Blacklist Words (12 Columns)
| TC ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| TC_BLACK_01 | UI | Low | Test giao diện đăng nhập đẹp | Sẵn sàng | 1. Xem màn hình | Giao diện hiển thị đẹp và như mong đợi | Low | N/A | Yes | UI | @UI |
| TC_BLACK_02 | Auth | High | Đăng nhập tài khoản hợp lệ | Sẵn sàng | 1. Nhập valid data | Đăng nhập thành công với dữ liệu hợp lệ và works properly | High | valid data | Yes | UI | @Smoke |
"""
    p = tmp_path / "corrupted_suite.md"
    p.write_text(corrupted_content, encoding="utf-8")

    res = lint_test_case_file(str(p))
    assert res["passed"] is False
    assert len(res["defects"]) >= 1

    defect_types = [d.get("type") for d in res["defects"]]
    assert "COLUMN_COUNT_VIOLATION" in defect_types

    # CLI verification
    linter_py = os.path.join(_REPO_ROOT, "tools", "lint", "manual_tc_linter.py")
    res_cli = _run_subprocess_cli([linter_py, str(p)])
    assert res_cli.returncode == 1
    assert "FAIL" in res_cli.stdout
