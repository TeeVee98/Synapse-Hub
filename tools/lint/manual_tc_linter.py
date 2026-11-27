#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Manual QA Test Case Linter & Completeness Guard (Filter 1 of Zero-Review Engine)
--------------------------------------------------------------------------------
Enforces ISO/IEC/IEEE 29119-3 12-column table standard, eliminates speculative
branching ("HOẶC", "tùy backend", "an toàn"), validates Precondition completeness,
and audits the Golden Ratio (40% Happy / 40% Negative / 20% Security & Resilience).

Usage:
  python tools/lint/manual_tc_linter.py path/to/test_cases.md
  python tools/lint/manual_tc_linter.py --audit-all
"""

import os
import sys
import re
import argparse
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# UTF-8 terminal encoding
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 12 Standard Columns defined by ISO/IEC/IEEE 29119-3 & Synapse-Hub
STANDARD_12_COLUMNS = [
    "TC ID", "Module", "Risk Level", "Test Title", "Pre-Condition",
    "Test Steps", "Expected Result", "Priority", "Test Data",
    "Automatable", "Auto Type", "Tags"
]

STANDARD_13_COLUMNS = [
    "TC ID", "REQ ID", *STANDARD_12_COLUMNS[1:]
]

# Context-Aware Golden Ratio Profiles (ISO/IEC/IEEE 29119-3 & Synapse-Hub)
LINTER_PROFILES: Dict[str, Dict[str, Any]] = {
    "default": {
        "name": "Standard Business Feature",
        "description": "Standard business workflows (40% Happy / 40% Negative / 20% Security & Resilience)",
        "happy_min": 30.0,
        "happy_max": 50.0,
        "happy_target": 40.0,
        "neg_min": 30.0,
        "neg_max": 50.0,
        "neg_target": 40.0,
        "sec_min": 15.0,
        "sec_target": 20.0,
    },
    "crud": {
        "name": "CRUD / Internal Administration",
        "description": "Low attack surface internal admin & master data management",
        "happy_min": 35.0,
        "happy_max": 55.0,
        "happy_target": 45.0,
        "neg_min": 35.0,
        "neg_max": 55.0,
        "neg_target": 45.0,
        "sec_min": 10.0,
        "sec_target": 10.0,
    },
    "auth-payment": {
        "name": "Auth, MFA, RBAC & Payment Transactions",
        "description": "High security, financial checkout, and authentication flows",
        "happy_min": 20.0,
        "happy_max": 35.0,
        "happy_target": 25.0,
        "neg_min": 35.0,
        "neg_max": 50.0,
        "neg_target": 45.0,
        "sec_min": 30.0,
        "sec_target": 30.0,
    },
    "api-integration": {
        "name": "API, Webhook & Async Queue Integration",
        "description": "Third-party APIs, webhooks, asynchronous workers and sync pipelines",
        "happy_min": 25.0,
        "happy_max": 40.0,
        "happy_target": 30.0,
        "neg_min": 35.0,
        "neg_max": 45.0,
        "neg_target": 40.0,
        "sec_min": 25.0,
        "sec_target": 30.0,
    },
    "ui-readonly": {
        "name": "Dashboard & Read-Only Search/Reports",
        "description": "Read-only analytics, dashboards, and basic search/filter views",
        "happy_min": 45.0,
        "happy_max": 65.0,
        "happy_target": 55.0,
        "neg_min": 25.0,
        "neg_max": 45.0,
        "neg_target": 35.0,
        "sec_min": 5.0,
        "sec_target": 10.0,
    },
}

INLINE_PROFILE_PATTERN = re.compile(
    r"<!--\s*synapse-linter-profile:\s*([a-zA-Z0-9_\-]+)\s*-->",
    re.IGNORECASE
)

FIELD_ALIASES = {
    "case_id": ["case id", "tc id", "tc_id", "testcase_id", "test case id", "id", "mã test case", "mã tc"],
    "req_id": ["req_id", "req id", "requirement id", "requirement", "mã req", "mã yêu cầu"],
    "module": ["module / screen", "module", "screen", "chức năng", "màn hình"],
    "title": ["test title & objective", "test title", "title", "scenario / title", "scenario", "tên testcase", "tên test case", "tiêu đề", "mục tiêu"],
    "precondition": ["pre-condition", "pre-conditions", "precondition", "preconditions", "tiền điều kiện", "điều kiện tiên quyết"],
    "steps": ["test steps (1-1)", "test steps", "steps", "các bước thực hiện", "bước thực hiện"],
    "data": ["test data", "data test", "data", "dữ liệu kiểm thử", "dữ liệu"],
    "expected": ["expected result", "expected", "kết quả mong đợi", "kết quả kỳ vọng", "kết quả"],
    "priority": ["priority / severity", "priority", "severity", "độ ưu tiên", "mức độ ưu tiên"],
    "risk_score": ["risk score (rpn)", "risk score", "rpn", "risk level", "risk tier", "mức rủi ro", "điểm rủi ro", "mức độ nghiêm trọng lỗi"],
    "automatable_type": ["automatable / type", "automatable", "auto type", "automatable / auto type", "loại tự động hóa"],
    "tags": ["automation tags", "tags", "tag", "nhãn"],
}


def _extract_field_by_aliases(row: Dict[str, Any], aliases: List[str]) -> str:
    for a in aliases:
        if a in row and row[a] is not None:
            return str(row[a]).strip()
    row_lower = {k.lower().strip(): v for k, v in row.items()}
    for a in aliases:
        if a.lower() in row_lower and row_lower[a.lower()] is not None:
            return str(row_lower[a.lower()]).strip()
    return ""


def _extract_canonical_field(row: Dict[str, Any], field_key: str) -> str:
    aliases = FIELD_ALIASES.get(field_key, [field_key])
    return _extract_field_by_aliases(row, aliases)


def check_quick_exit_criteria(
    rows: List[Dict[str, Any]],
    require_rtm: bool = True,
) -> Dict[str, Any]:
    """Evaluates QUICK-Mode minimum coverage exit criteria (Happy + Negative + Boundary + RTM linkage)."""
    if not rows:
        return {
            "has_happy_path": False,
            "has_negative_path": False,
            "has_boundary_case": False,
            "rtm_coverage_pct": 0.0,
            "missing_criteria": ["empty_suite"],
            "passed": False,
        }

    has_happy = False
    has_neg = False
    has_bound = False
    rtm_linked = 0

    bound_tokens = ("@boundary", "@bva", "@edge", "boundary", "bva", "whitespace", "trim", "min-1", "max+1", "empty")
    neg_tokens = ("@negative", "@neg", "negative", "invalid", "error", "400", "401", "403", "404", "409", "422", "reject", "denied")

    for row in rows:
        title = _extract_canonical_field(row, "title").lower()
        expected = _extract_canonical_field(row, "expected").lower()
        tags = _extract_canonical_field(row, "tags").lower()
        req_id = _extract_canonical_field(row, "req_id").strip()
        combined = f"{title} {expected} {tags}"

        if req_id or re.search(r"@?req[-_]\w+", tags, re.IGNORECASE):
            rtm_linked += 1

        is_b = any(tok in combined for tok in bound_tokens)
        is_n = any(tok in combined for tok in neg_tokens)
        if is_b:
            has_bound = True
        if is_n:
            has_neg = True
        if not is_b and not is_n:
            has_happy = True
        elif any(ht in combined for ht in ("@smoke", "@happy", "happy", "valid login")):
            has_happy = True

    rtm_pct = round((rtm_linked / len(rows)) * 100.0, 2)
    missing: List[str] = []
    if not has_happy:
        missing.append("happy_path")
    if not has_neg:
        missing.append("negative_path")
    if not has_bound:
        missing.append("boundary_case")
    if require_rtm and rtm_pct < 100.0:
        missing.append("rtm_traceability")

    return {
        "has_happy_path": has_happy,
        "has_negative_path": has_neg,
        "has_boundary_case": has_bound,
        "rtm_coverage_pct": rtm_pct,
        "missing_criteria": missing,
        "passed": len(missing) == 0,
    }


# Blacklist terms scanning across ALL table cells
# Blacklist terms: "hợp lệ", "đẹp", "bình thường", "như mong đợi", "valid data", "works properly",
# plus existing speculative phrases ("hoặc", "tùy backend", "xử lý an toàn", "phù hợp", "as expected").
BLACKLIST_TERMS = [
    (re.compile(r"\bhợp\s+lệ\b", re.IGNORECASE), "hợp lệ"),
    (re.compile(r"(?<!tốt\s)\bđẹp\b", re.IGNORECASE), "đẹp"),
    (re.compile(r"\bbình\s+thường\b", re.IGNORECASE), "bình thường"),
    (re.compile(r"\bnhư\s+mong\s+đợi\b", re.IGNORECASE), "như mong đợi"),
    (re.compile(r"\bvalid\s+data\b", re.IGNORECASE), "valid data"),
    (re.compile(r"\bworks?\s+properly\b", re.IGNORECASE), "works properly"),
    (re.compile(r"\bas\s+expected\b", re.IGNORECASE), "as expected"),
    (re.compile(r"\bhoặc\b", re.IGNORECASE), "hoặc"),
    (re.compile(r"\btùy\s+(?:backend|quy\s+tắc|server|hệ\s+thống)\b", re.IGNORECASE), "tùy backend/quy tắc"),
    (re.compile(r"\bcó\s+thể\s+(?:tự\s+động|chấp\s+nhận|từ\s+chối)\b", re.IGNORECASE), "có thể tự động/chấp nhận/từ chối"),
    (re.compile(r"\bxử\s+lý\s+an\s+toàn\b(?!\s*:\s*(?:chặn|báo\s+lỗi|từ\s+chối))", re.IGNORECASE), "xử lý an toàn"),
    (re.compile(r"\bphù\s+hợp\b", re.IGNORECASE), "phù hợp"),
]

AMBIGUITY_LOG_PATTERN = re.compile(
    r"^##\s+.*ambiguity(?:\s*(?:&|and)?\s*assumptions?)?\s*log",
    re.IGNORECASE | re.MULTILINE
)


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculates semantic text similarity using normalized sequence matching."""
    t1 = re.sub(r"[^\w\s]", "", str(text1 or "").lower()).strip()
    t2 = re.sub(r"[^\w\s]", "", str(text2 or "").lower()).strip()
    if not t1 or not t2:
        return 0.0
    return SequenceMatcher(None, t1, t2).ratio()


def parse_markdown_tables(content: str) -> List[Dict[str, Any]]:
    """Extracts markdown tables and parses their rows into structured dictionaries."""
    lines = content.splitlines()
    tables = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if not (line.startswith("|") and line.endswith("|")):
            i += 1
            continue
        headers = [c.strip() for c in line.split("|")[1:-1]]
        if len(headers) < 3 or i + 1 >= len(lines):
            i += 1
            continue
        sep_line = lines[i + 1].strip()
        if not (sep_line.startswith("|") and "---" in sep_line):
            i += 1
            continue

        header_line = i + 1
        rows = []
        i += 2
        while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
            cols = [c.strip() for c in lines[i].strip().split("|")[1:-1]]
            if len(cols) == len(headers):
                row_dict = {headers[k]: cols[k] for k in range(len(headers))}
                row_dict["__line_number__"] = i + 1
                rows.append(row_dict)
            i += 1

        is_test_table = any(
            "tc id" in h.lower()
            or "case id" in h.lower()
            or "tc_id" in h.lower()
            or "test title" in h.lower()
            or "mã tc" in h.lower()
            or "mã test case" in h.lower()
            for h in headers
        )
        tables.append({
            "headers": headers,
            "rows": rows,
            "header_line": header_line,
            "is_test_table": is_test_table
        })

    return tables


def _scan_blacklist_defects(
    spec_cells: List[tuple],
    line_no: int,
    tc_id: str,
) -> List[Dict[str, Any]]:
    """Scans table cells for speculative or ambiguous blacklist terms."""
    found: List[Dict[str, Any]] = []
    for col_name, cell_val in spec_cells:
        if not cell_val:
            continue
        for pat, _label in BLACKLIST_TERMS:
            m = pat.search(cell_val)
            if not m:
                continue
            matched_term = m.group(0)
            found.append({
                "line": line_no,
                "tc_id": tc_id,
                "type": "SPECULATIVE_ORACLE",
                "matched": matched_term,
                "cell": col_name,
                "message": (
                    f"Ambiguous or speculative blacklist term '{matched_term}' detected in {col_name}: '{cell_val}'. "
                    f"Expected results and specifications must be single-valued deterministic."
                ),
            })
            break
    return found


_COMPOUND_TITLE_PATTERNS = (
    (re.compile(r"\bvs\.?\b", re.IGNORECASE), "comparative 'vs' scenario bundling"),
    (re.compile(r"\b(?:approve|accept)\s+and\s+(?:reject|deny)\b", re.IGNORECASE), "dual approve-and-reject bundling"),
    (re.compile(r"\b(?:create|add)\s+and\s+(?:delete|remove)\b", re.IGNORECASE), "dual create-and-delete bundling"),
    (re.compile(r"\b(?:valid|pass)\s+and\s+(?:invalid|fail)\b", re.IGNORECASE), "dual valid-and-invalid bundling"),
    (re.compile(r"(?:đồng\s+ý|duyệt)\s+và\s+(?:từ\s+chối|trả\s+lại)", re.IGNORECASE), "dual Vietnamese approve-and-reject bundling"),
    (re.compile(r"(?:hàng\s+loạt.*và.*đơn\s+lẻ|đơn\s+lẻ.*và.*hàng\s+loạt)", re.IGNORECASE), "dual batch-and-single bundling"),
    (re.compile(r"(?:trong\s+hạn.*và.*quá\s+hạn|quá\s+hạn.*và.*trong\s+hạn)", re.IGNORECASE), "dual in-limit-and-expired bundling"),
)
_COMPOUND_STEPS_RE = re.compile(r"\b(?:case|th|kịch\s+bản)\s*[-_#]?\s*[1-9]\b", re.IGNORECASE)
_XLSX_TC_HEADER_TOKENS = ("tc id", "case id", "tc_id", "testcase_id", "test case id", "mã tc", "mã test case")
_XLSX_QA_SHEET_TOKENS = ("q&a", "qa", "question", "ambiguity", "assumption")


def _detect_compound_test_case(title: str, steps: str) -> Optional[str]:
    """Detects bundled multi-scenario test cases that violate 1-condition = 1-TC atomicity."""
    title_str = str(title or "").strip()
    for pat, reason in _COMPOUND_TITLE_PATTERNS:
        if pat.search(title_str):
            return reason
    step_markers = _COMPOUND_STEPS_RE.findall(str(steps or ""))
    if len(set(m.lower() for m in step_markers)) >= 2:
        return "multiple sub-cases bundled in Test Steps"
    return None


def _find_xlsx_header_row(ws_rows: List[tuple]) -> Optional[tuple]:
    """Finds (row_idx_1based, cleaned_headers) for a worksheet test-case table within first 25 rows."""
    for row_idx, raw_row in enumerate(ws_rows[:25], start=1):
        cells = [str(c).strip() if c is not None else "" for c in raw_row]
        non_empty = [c for c in cells if c]
        if len(non_empty) < 3:
            continue
        if any(any(tok in c.lower() for tok in _XLSX_TC_HEADER_TOKENS) for c in non_empty):
            return row_idx, cells
    return None


def parse_xlsx_test_tables(file_path: str) -> tuple:
    """Parses multi-sheet enterprise .xlsx workbooks into normalized test tables + has_qa_sheet flag."""
    try:
        import openpyxl  # type: ignore[import-untyped]
    except ImportError:
        return [], False

    wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
    tables: List[Dict[str, Any]] = []
    has_qa_sheet = False
    try:
        for sheet_name in wb.sheetnames:
            sname_low = sheet_name.strip().lower()
            if any(tok in sname_low for tok in _XLSX_QA_SHEET_TOKENS):
                has_qa_sheet = True
            ws = wb[sheet_name]
            ws_rows = list(ws.iter_rows(values_only=True))
            found = _find_xlsx_header_row(ws_rows)
            if not found:
                continue
            header_idx, raw_headers = found
            active_cols = [(idx, h) for idx, h in enumerate(raw_headers) if h]
            headers = [h for _, h in active_cols]
            rows: List[Dict[str, Any]] = []
            for r_offset, raw_row in enumerate(ws_rows[header_idx:], start=header_idx + 1):
                row_dict: Dict[str, Any] = {}
                for col_idx, col_name in active_cols:
                    val = raw_row[col_idx] if col_idx < len(raw_row) else None
                    row_dict[col_name] = "" if val is None else str(val).strip()
                case_id = _extract_canonical_field(row_dict, "case_id")
                title_val = _extract_canonical_field(row_dict, "title")
                if not case_id or not title_val:
                    continue
                row_dict["__line_number__"] = r_offset
                row_dict["__sheet_name__"] = sheet_name
                rows.append(row_dict)
            if rows:
                tables.append({
                    "headers": headers,
                    "rows": rows,
                    "header_line": header_idx,
                    "sheet_name": sheet_name,
                    "is_test_table": True,
                })
    finally:
        wb.close()
    return tables, has_qa_sheet


SEMANTIC_S1_KEYWORDS = [
    "double-click", "double click", "double-submit", "double submit",
    "idempotency", "disable button", "khóa nút", "bấm 2 lần",
    "nhấn liên tiếp", "trùng giao dịch"
]

SEMANTIC_S2_KEYWORDS = [
    "slow 3g", "latency", "timeout", "back", "refresh", "f5",
    "độ trễ", "mạng chậm", "đóng tab", "pending", "reconcile"
]

SEMANTIC_S3_KEYWORDS = [
    "whitespace", "space", "khoảng trắng", "dấu cách", "trim",
    "toàn dấu cách", "\u00a0", "\u200b"
]


def lint_test_case_file(file_path: str, profile: Optional[str] = None, strict_semantic: bool = False) -> Dict[str, Any]:
    """Lints a markdown test case file against ISO 29119-3 and Synapse-Hub invariants."""
    empty_metrics = {
        "profile": profile or "default",
        "happy_ratio": "0.0%",
        "negative_ratio": "0.0%",
        "security_resilience_ratio": "0.0%",
        "duplicate_cases": 0,
        "speculative_oracles": 0,
        "vague_preconditions": 0,
        "rtm_linked_cases": 0,
        "compound_cases": 0,
    }

    if not os.path.isfile(file_path):
        # Graceful fallback for checkout example naming variants
        if file_path.endswith("checkout_rbt_manual_testcases.md"):
            alt_path = file_path.replace("checkout_rbt_manual_testcases.md", "checkout_rbt_manual_suite.md")
            if os.path.isfile(alt_path):
                file_path = alt_path
            else:
                return {
                    "file": file_path,
                    "profile": profile or "default",
                    "has_test_cases": False,
                    "column_counts": [],
                    "total_test_cases": 0,
                    "passed": False,
                    "defects": [{"line": 0, "type": "FILE_NOT_FOUND", "message": f"File not found: {file_path}"}],
                    "warnings": [],
                    "metrics": empty_metrics,
                    "error": "File not found"
                }
        else:
            return {
                "file": file_path,
                "profile": profile or "default",
                "has_test_cases": False,
                "column_counts": [],
                "total_test_cases": 0,
                "passed": False,
                "defects": [{"line": 0, "type": "FILE_NOT_FOUND", "message": f"File not found: {file_path}"}],
                "warnings": [],
                "metrics": empty_metrics,
                "error": "File not found"
            }

    is_xlsx = file_path.lower().endswith(".xlsx")
    content = ""
    has_qa_sheet = False
    if is_xlsx:
        try:
            test_tables, has_qa_sheet = parse_xlsx_test_tables(file_path)
        except Exception as e:
            return {
                "file": file_path,
                "profile": profile or "default",
                "has_test_cases": False,
                "column_counts": [],
                "total_test_cases": 0,
                "passed": False,
                "defects": [{"line": 0, "type": "READ_ERROR", "message": f"Cannot read Excel workbook: {e}"}],
                "warnings": [],
                "metrics": empty_metrics,
                "error": f"Cannot read Excel workbook: {e}"
            }
        chosen_profile = (profile.strip().lower() if profile else None) or "default"
    else:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return {
                "file": file_path,
                "profile": profile or "default",
                "has_test_cases": False,
                "column_counts": [],
                "total_test_cases": 0,
                "passed": False,
                "defects": [{"line": 0, "type": "READ_ERROR", "message": f"Cannot read file: {e}"}],
                "warnings": [],
                "metrics": empty_metrics,
                "error": f"Cannot read file: {e}"
            }

        # Profile resolution precedence: CLI flag > inline comment > default
        m_profile = INLINE_PROFILE_PATTERN.search(content)
        inline_profile = m_profile.group(1).strip().lower() if m_profile else None
        chosen_profile = (profile.strip().lower() if profile else None) or inline_profile or "default"
        tables = parse_markdown_tables(content)
        test_tables = [t for t in tables if t.get("is_test_table")]

    if chosen_profile not in LINTER_PROFILES:
        chosen_profile = "default"
    prof_cfg = LINTER_PROFILES[chosen_profile]

    if not test_tables:
        return {
            "file": file_path,
            "has_test_cases": False,
            "column_counts": [],
            "total_test_cases": 0,
            "passed": True,
            "defects": [],
            "warnings": [],
            "metrics": empty_metrics,
            "message": "No test case tables found."
        }

    defects = []
    warnings = []
    total_test_cases = 0
    column_counts = []
    speculative_oracle_count = 0
    missing_precondition_count = 0
    rtm_linked_count = 0
    compound_case_count = 0

    category_counts = {
        "happy": 0,
        "negative": 0,
        "security_resilience": 0
    }

    # Ambiguity & Assumptions Log Check (Markdown sections or Q&A sheet for Excel)
    if not is_xlsx:
        has_h2_sections = bool(re.search(r"^##\s+", content, re.MULTILINE))
        m_ambig = AMBIGUITY_LOG_PATTERN.search(content)
        if has_h2_sections or m_ambig:
            if not m_ambig:
                defects.append({
                    "line": 1,
                    "type": "MISSING_AMBIGUITY_LOG",
                    "message": "Missing mandatory '## Ambiguity & Assumptions Log' section per RBT Manual Testing standards."
                })
            else:
                after_header = content[m_ambig.end():]
                next_heading = re.search(r"^#{1,6}\s+", after_header, re.MULTILINE)
                section_body = after_header[:next_heading.start()] if next_heading else after_header
                cleaned_body = re.sub(r"[\s\-_*`#]+", "", section_body)
                if not cleaned_body:
                    header_line = content[:m_ambig.start()].count("\n") + 1
                    defects.append({
                        "line": header_line,
                        "type": "MISSING_AMBIGUITY_LOG",
                        "message": "Mandatory '## Ambiguity & Assumptions Log' section is present but empty. Please document assumptions or confirmed ambiguities."
                    })
    elif not has_qa_sheet:
        warnings.append({
            "line": 0,
            "type": "MISSING_QA_SHEET",
            "message": "Excel workbook has no Q&A / Ambiguity worksheet for Dev/BA clarifications."
        })

    for t_idx, t in enumerate(test_tables):
        headers = t["headers"]
        col_count = len(headers)
        column_counts.append(col_count)

        # Check ISO 29119-3 12-column standard (relaxed to warning for corporate .xlsx templates)
        if not is_xlsx and col_count < 12:
            defects.append({
                "line": t["header_line"],
                "type": "COLUMN_COUNT_VIOLATION",
                "message": f"Table has {col_count} columns (Expected 12 columns per ISO 29119-3 standard). Missing: {12 - col_count} columns."
            })
        elif is_xlsx and col_count < 12:
            warnings.append({
                "line": t["header_line"],
                "type": "CORPORATE_COLUMN_LAYOUT",
                "message": f"Excel sheet '{t.get('sheet_name', '')}' uses {col_count}-column corporate template (< 12 ISO columns)."
            })

        for row in t["rows"]:
            total_test_cases += 1
            line_no = row.get("__line_number__", 0)

            # Resolve canonical attributes
            tc_id = _extract_canonical_field(row, "case_id") or f"ROW_{line_no}"
            test_title = _extract_canonical_field(row, "title")
            expected = _extract_canonical_field(row, "expected")
            precond = _extract_canonical_field(row, "precondition")
            priority = _extract_canonical_field(row, "priority")
            risk_level = _extract_canonical_field(row, "risk_score")
            tags = _extract_canonical_field(row, "tags")
            steps = _extract_canonical_field(row, "steps")
            req_id_val = _extract_canonical_field(row, "req_id")
            if req_id_val or re.search(r"@?req[-_]\w+", tags, re.IGNORECASE):
                rtm_linked_count += 1

            # Check 1: Blacklist Terms Scanning across table cells (title, precondition, steps, data, expected)
            spec_cells = [
                ("Test Title", test_title),
                ("Pre-Condition", precond),
                ("Test Steps", steps),
                ("Test Data", _extract_canonical_field(row, "data")),
                ("Expected Result", expected),
            ]
            for col_name, cell_val in row.items():
                if col_name.startswith("__") or not isinstance(cell_val, str):
                    continue
                col_lower = col_name.lower()
                if any(ex in col_lower for ex in ["actual", "status", "tested by", "execution date", "bug id", "người test", "ngày test", "lần 1", "lần 2", "notes", "môi trường"]):
                    continue
                if not any(sc[0] == col_name for sc in spec_cells):
                    spec_cells.append((col_name, cell_val))

            cell_defects = _scan_blacklist_defects(spec_cells, line_no, tc_id)
            speculative_oracle_count += len(cell_defects)
            defects.extend(cell_defects)

            # Check 1b: Atomicity Guard (1 condition = 1 TC; warn on compound bundling, block under strict_semantic)
            compound_reason = _detect_compound_test_case(test_title, steps)
            if compound_reason:
                compound_case_count += 1
                compound_item = {
                    "line": line_no,
                    "tc_id": tc_id,
                    "type": "COMPOUND_TEST_CASE",
                    "message": f"Compound test case detected ({compound_reason}) in '{test_title}'. Split into atomic single-condition TCs.",
                }
                if strict_semantic:
                    defects.append(compound_item)
                else:
                    warnings.append(compound_item)

            # Check 2: Vague Preconditions for Privileged/Mutation Actions
            if re.search(r"\b(?:tạo|xóa|sửa|chỉnh\s+sửa|phê\s+duyệt|delete|update|create|edit)\b", test_title, re.IGNORECASE):
                if precond.strip().lower() in ["không", "n/a", "none", "-", ""]:
                    missing_precondition_count += 1
                    warnings.append({
                        "line": line_no,
                        "tc_id": tc_id,
                        "type": "VAGUE_PRECONDITION",
                        "message": f"Data mutation / privileged test title '{test_title}' has vague/empty Pre-condition: '{precond}'."
                    })

            # Golden Ratio Categorization
            tags_lower = tags.lower()
            title_lower = test_title.lower()
            expected_lower = expected.lower()
            combined_all = f"{test_title} {expected} {risk_level} {priority} {tags} {steps} {precond}".lower()

            sec_tags = ["@security", "@resilience", "@edge", "@sec", "@owasp", "@concurrency", "@race", "@boundary", "@bva"]
            sec_keywords = [
                "security", "resilience", "edge", "sqli", "xss", "csrf", "injection",
                "boundary", "bva", "concurrency", "race", "timeout", "limit",
                "cực đại", "vượt giới hạn", "double submit", "double-click", "brute",
                "500", "502", "504", "idor", "multi-tab", "atomicity", "unicode"
            ]

            neg_tags = ["@negative", "@neg"]
            neg_keywords = [
                "từ chối", "chặn", "báo lỗi", "thất bại", "không hợp lệ", "sai quy cách",
                "mã lỗi", "400", "401", "403", "404", "409", "422", "sai định dạng",
                "để trống", "vượt quá", "thiếu", "negative", "invalid", "unauthorized",
                "forbidden", "bad request"
            ]

            # 1. Security & Resilience (takes precedence)
            if any(t in tags_lower for t in sec_tags) or any(k in combined_all for k in sec_keywords):
                category_counts["security_resilience"] += 1
            # 2. Negative
            elif any(t in tags_lower for t in neg_tags) or any(k in expected_lower for k in neg_keywords) or any(k in title_lower for k in ["sai định dạng", "để trống", "vượt quá", "thiếu", "không hợp lệ", "negative", "invalid"]):
                category_counts["negative"] += 1
            # 3. Happy
            else:
                category_counts["happy"] += 1

    # Filter 2: Deduplication & Semantic Pruning (> 85% similarity threshold)
    all_rows = []
    for t in test_tables:
        all_rows.extend(t["rows"])

    duplicate_pairs = []
    for idx_a in range(len(all_rows)):
        for idx_b in range(idx_a + 1, len(all_rows)):
            row_a = all_rows[idx_a]
            row_b = all_rows[idx_b]
            id_a = _extract_canonical_field(row_a, "case_id") or f"ROW_{idx_a}"
            id_b = _extract_canonical_field(row_b, "case_id") or f"ROW_{idx_b}"

            title_a = _extract_canonical_field(row_a, "title")
            steps_a = _extract_canonical_field(row_a, "steps")
            title_b = _extract_canonical_field(row_b, "title")
            steps_b = _extract_canonical_field(row_b, "steps")

            text_a = f"{title_a} {steps_a}".strip()
            text_b = f"{title_b} {steps_b}".strip()

            sim = calculate_similarity(text_a, text_b)
            if sim >= 0.85:
                pct = round(sim * 100, 1)
                duplicate_pairs.append((id_a, id_b, pct))
                warnings.append({
                    "line": row_b.get("__line_number__", 0),
                    "tc_id": id_b,
                    "type": "SEMANTIC_DUPLICATION_BLOAT",
                    "similarity": f"{pct}%",
                    "duplicate_with": id_a,
                    "message": f"Phát hiện trùng lặp ngữ nghĩa ({pct}% >= 85%) giữa '{id_b}' và '{id_a}'. Đề xuất gộp hoặc loại bỏ để tránh phình bộ test (Test Bloat)."
                })

    # Ratio Calculation
    if total_test_cases == 0:
        happy_pct = 0.0
        neg_pct = 0.0
        sec_pct = 0.0
    else:
        happy_pct = round((category_counts["happy"] / total_test_cases) * 100, 1)
        neg_pct = round((category_counts["negative"] / total_test_cases) * 100, 1)
        sec_pct = round((category_counts["security_resilience"] / total_test_cases) * 100, 1)

    # Golden Ratio Warning conditioned on active profile
    sec_min_threshold = prof_cfg["sec_min"]
    if total_test_cases >= 10 and sec_pct < sec_min_threshold:
        warnings.append({
            "line": 0,
            "type": "GOLDEN_RATIO_DEFICIT",
            "profile": chosen_profile,
            "message": (
                f"Security & Resilience coverage ({sec_pct}%) is below the {chosen_profile} "
                f"profile minimum ({sec_min_threshold}%). Found {category_counts['security_resilience']}/{total_test_cases} TCs."
            )
        })

    if total_test_cases >= 10 and chosen_profile != "default":
        if happy_pct < prof_cfg["happy_min"] or happy_pct > prof_cfg["happy_max"]:
            warnings.append({
                "line": 0,
                "type": "GOLDEN_RATIO_IMBALANCE",
                "profile": chosen_profile,
                "message": (
                    f"Happy path coverage ({happy_pct}%) outside {chosen_profile} "
                    f"target range ({prof_cfg['happy_min']}% - {prof_cfg['happy_max']}%)."
                )
            })
        if neg_pct < prof_cfg["neg_min"] or neg_pct > prof_cfg["neg_max"]:
            warnings.append({
                "line": 0,
                "type": "GOLDEN_RATIO_IMBALANCE",
                "profile": chosen_profile,
                "message": (
                    f"Negative/Boundary coverage ({neg_pct}%) outside {chosen_profile} "
                    f"target range ({prof_cfg['neg_min']}% - {prof_cfg['neg_max']}%)."
                )
            })

    # Filter 4: Mandatory Semantic Rules (S1 - S3)
    if total_test_cases > 0:
        all_row_texts = [
            " ".join(str(v) for k, v in r.items() if not k.startswith("__")).lower()
            for r in all_rows
        ]
        has_input_fields = any(
            len(_extract_canonical_field(r, "data")) > 0 or
            any(k in txt for k in ["nhập", "fill", "type", "enter", "input", "form", "data", "text", "email", "address", "coupon", "card", "ghi chú"])
            for r, txt in zip(all_rows, all_row_texts)
        )

        has_s1 = any(any(k in txt for k in SEMANTIC_S1_KEYWORDS) for txt in all_row_texts)
        has_s2 = any(any(k in txt for k in SEMANTIC_S2_KEYWORDS) for txt in all_row_texts)
        has_s3 = any(any(k in txt for k in SEMANTIC_S3_KEYWORDS) for txt in all_row_texts)

        # Rule S1 — Mandatory Double-Click / Double-Submit / Idempotency (auth-payment)
        if chosen_profile == "auth-payment" and not has_s1:
            s1_finding = {
                "line": 0,
                "type": "SEMANTIC_S1",
                "rule": "S1",
                "message": (
                    "[SEMANTIC_S1] Missing mandatory Double-Click / Double-Submit / Idempotency scenario for 'auth-payment'. "
                    "Add at least one test case verifying rapid button disable, Idempotency-Key, or duplicate transaction blocking."
                )
            }
            if strict_semantic:
                defects.append(s1_finding)
            else:
                warnings.append(s1_finding)

        # Rule S2 — Mandatory UI Latency / Timeout / Browser Interrupt (auth-payment)
        if chosen_profile == "auth-payment" and not has_s2:
            s2_finding = {
                "line": 0,
                "type": "SEMANTIC_S2",
                "rule": "S2",
                "message": (
                    "[SEMANTIC_S2] Missing mandatory UI Latency / Timeout / Browser Interrupt scenario for 'auth-payment'. "
                    "Add at least one test case verifying Slow 3G network latency, payment timeout, or browser Back/F5/Close Tab redirect interrupt."
                )
            }
            if strict_semantic:
                defects.append(s2_finding)
            else:
                warnings.append(s2_finding)

        # Rule S3 — Mandatory Whitespace / Trim Validation (crud & auth-payment)
        if chosen_profile in ["crud", "auth-payment"] and has_input_fields and not has_s3:
            s3_finding = {
                "line": 0,
                "type": "SEMANTIC_S3",
                "rule": "S3",
                "message": (
                    f"[SEMANTIC_S3] Missing mandatory Whitespace / Trim Validation scenario for '{chosen_profile}'. "
                    "Add at least one test case verifying whitespace-only string ('   ') rejection and leading/trailing whitespace trim() handling."
                )
            }
            if strict_semantic:
                defects.append(s3_finding)
            else:
                warnings.append(s3_finding)

    passed = len(defects) == 0

    return {
        "file": file_path,
        "profile": chosen_profile,
        "strict_semantic": strict_semantic,
        "has_test_cases": True,
        "total_test_cases": total_test_cases,
        "column_counts": column_counts,
        "passed": passed,
        "defects": defects,
        "warnings": warnings,
        "metrics": {
            "profile": chosen_profile,
            "happy_ratio": f"{happy_pct}%",
            "negative_ratio": f"{neg_pct}%",
            "security_resilience_ratio": f"{sec_pct}%",
            "duplicate_cases": len(duplicate_pairs),
            "speculative_oracles": speculative_oracle_count,
            "vague_preconditions": missing_precondition_count,
            "rtm_linked_cases": rtm_linked_count,
            "compound_cases": compound_case_count,
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Manual QA Test Case Linter & Completeness Guard")
    parser.add_argument("paths", nargs="*", help="Path to markdown test case files")
    parser.add_argument("--profile", "-p", choices=list(LINTER_PROFILES.keys()), default=None, help="Golden Ratio context profile (default, crud, auth-payment, api-integration, ui-readonly)")
    parser.add_argument("--strict-semantic", action="store_true", default=False, help="Enforce semantic business rules S1-S3 as blocking errors")
    parser.add_argument("--audit-all", action="store_true", help="Audit all markdown test files in examples/ and test-design/")
    args = parser.parse_args()

    raw_files = list(args.paths)
    files = []
    if args.audit_all or not raw_files:
        target_dirs = [
            os.path.join(_REPO_ROOT, "examples", "practices", "testcases"),
            os.path.join(_REPO_ROOT, "test-design")
        ]
        for td in target_dirs:
            if os.path.isdir(td):
                for root, _, fs in os.walk(td):
                    for f in fs:
                        if f.endswith(".md") and not f.endswith("SKILL.md"):
                            files.append(os.path.join(root, f))
    else:
        for p in raw_files:
            if os.path.isdir(p):
                for root, _, fs in os.walk(p):
                    for f in fs:
                        if f.endswith(".md") and not f.endswith("SKILL.md"):
                            files.append(os.path.join(root, f))
            else:
                files.append(p)

    if not files:
        print("No markdown test case files specified.")
        return 0

    print("\n" + "=" * 76)
    print("   ZERO-REVIEW ENGINE: TRIPLE-FILTER VERIFICATION GATE (FILTERS 1, 2 & 3)")
    print("=" * 76)

    total_files = 0
    passed_files = 0
    total_defects = 0
    total_warnings = 0

    for fpath in files:
        try:
            rel_path = os.path.relpath(fpath, _REPO_ROOT)
        except ValueError:
            rel_path = os.path.abspath(fpath)
        result = lint_test_case_file(fpath, profile=args.profile, strict_semantic=args.strict_semantic)

        if result.get("error"):
            total_files += 1
            total_defects += len(result.get("defects", [])) or 1
            print(f"\n[❌ ERROR] {rel_path}: {result['error']}")
            for d in result.get("defects", []):
                print(f"        - L{d['line']}: {d['message']}")
            continue

        if not result.get("has_test_cases"):
            continue

        total_files += 1
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        if result["passed"]:
            passed_files += 1

        prof_label = result.get("profile", "default")
        print(f"\n[{status}] {rel_path} ({result['total_test_cases']} TCs | Profile: {prof_label})")
        metrics = result["metrics"]
        print(f"      Ratio: Happy {metrics['happy_ratio']} | Negative {metrics['negative_ratio']} | Security/Resilience {metrics['security_resilience_ratio']}")

        if result["defects"]:
            total_defects += len(result["defects"])
            print("      🚨 Defects:")
            for d in result["defects"]:
                tc = f"[{d.get('tc_id')}] " if d.get("tc_id") else ""
                print(f"        - L{d['line']}: {tc}{d['message']}")

        if result["warnings"]:
            total_warnings += len(result["warnings"])
            print("      ⚠️ Warnings:")
            for w in result["warnings"]:
                tc = f"[{w.get('tc_id')}] " if w.get("tc_id") else ""
                print(f"        - L{w['line']}: {tc}{w['message']}")

    print("\n" + "=" * 76)
    print(f"  Summary: {passed_files}/{total_files} files passed ({total_defects} defects, {total_warnings} warnings)")
    print("=" * 76 + "\n")

    return 0 if total_defects == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
