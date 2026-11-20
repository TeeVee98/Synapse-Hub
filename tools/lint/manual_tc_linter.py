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
from typing import List, Dict, Any

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

FIELD_ALIASES = {
    "case_id": ["case id", "tc id", "tc_id", "id", "mã test case", "mã tc"],
    "req_id": ["req_id", "req id", "requirement id", "requirement", "mã req", "mã yêu cầu"],
    "module": ["module / screen", "module", "screen", "chức năng", "màn hình"],
    "title": ["test title & objective", "test title", "title", "scenario / title", "scenario", "tiêu đề", "mục tiêu"],
    "precondition": ["pre-condition", "pre-conditions", "precondition", "preconditions", "tiền điều kiện", "điều kiện tiên quyết"],
    "steps": ["test steps (1-1)", "test steps", "steps", "các bước thực hiện", "bước thực hiện"],
    "data": ["test data", "data", "dữ liệu kiểm thử", "dữ liệu"],
    "expected": ["expected result", "expected", "kết quả mong đợi", "kết quả kỳ vọng", "kết quả"],
    "priority": ["priority / severity", "priority", "severity", "độ ưu tiên", "mức độ ưu tiên"],
    "risk_score": ["risk score (rpn)", "risk score", "rpn", "risk level", "risk tier", "mức rủi ro", "điểm rủi ro"],
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
        if line.startswith("|") and line.endswith("|"):
            # Potential table header
            headers = [c.strip() for c in line.split("|")[1:-1]]
            if len(headers) >= 3 and i + 1 < len(lines):
                sep_line = lines[i + 1].strip()
                if sep_line.startswith("|") and "---" in sep_line:
                    # Confirmed markdown table
                    header_line = i + 1
                    rows = []
                    i += 2
                    while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                        row_line = lines[i].strip()
                        cols = [c.strip() for c in row_line.split("|")[1:-1]]
                        if len(cols) == len(headers):
                            row_dict = {headers[k]: cols[k] for k in range(len(headers))}
                            row_dict["__line_number__"] = i + 1
                            rows.append(row_dict)
                        i += 1

                    is_test_table = any(
                        "tc id" in h.lower() or "case id" in h.lower() or "tc_id" in h.lower() or "test title" in h.lower()
                        for h in headers
                    )
                    tables.append({
                        "headers": headers,
                        "rows": rows,
                        "header_line": header_line,
                        "is_test_table": is_test_table
                    })
                    continue
        i += 1

    return tables


def lint_test_case_file(file_path: str) -> Dict[str, Any]:
    """Lints a markdown test case file against ISO 29119-3 and Synapse-Hub invariants."""
    empty_metrics = {
        "happy_ratio": "0.0%",
        "negative_ratio": "0.0%",
        "security_resilience_ratio": "0.0%",
        "duplicate_cases": 0,
        "speculative_oracles": 0,
        "vague_preconditions": 0
    }

    if not os.path.isfile(file_path):
        return {
            "file": file_path,
            "has_test_cases": False,
            "column_counts": [],
            "total_test_cases": 0,
            "passed": False,
            "defects": [{"line": 0, "type": "FILE_NOT_FOUND", "message": f"File not found: {file_path}"}],
            "warnings": [],
            "metrics": empty_metrics,
            "error": "File not found"
        }

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return {
            "file": file_path,
            "has_test_cases": False,
            "column_counts": [],
            "total_test_cases": 0,
            "passed": False,
            "defects": [{"line": 0, "type": "READ_ERROR", "message": f"Cannot read file: {e}"}],
            "warnings": [],
            "metrics": empty_metrics,
            "error": f"Cannot read file: {e}"
        }

    tables = parse_markdown_tables(content)
    test_tables = []
    for t in tables:
        h_lower = [h.lower() for h in t["headers"]]
        if any("tc id" in h or "case id" in h or "tc_id" in h or "test title" in h for h in h_lower):
            test_tables.append(t)

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

    category_counts = {
        "happy": 0,
        "negative": 0,
        "security_resilience": 0
    }

    # Ambiguity & Assumptions Log Check
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
            # Check if the section is non-empty
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

    for t_idx, t in enumerate(test_tables):
        headers = t["headers"]
        col_count = len(headers)
        column_counts.append(col_count)

        # Check ISO 29119-3 12-column standard
        if col_count < 12:
            defects.append({
                "line": t["header_line"],
                "type": "COLUMN_COUNT_VIOLATION",
                "message": f"Table has {col_count} columns (Expected 12 columns per ISO 29119-3 standard). Missing: {12 - col_count} columns."
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
                if any(ex in col_lower for ex in ["actual", "status", "tested by", "execution date"]):
                    continue
                if not any(sc[0] == col_name for sc in spec_cells):
                    spec_cells.append((col_name, cell_val))

            for col_name, cell_val in spec_cells:
                if not cell_val:
                    continue
                for pat, label in BLACKLIST_TERMS:
                    m = pat.search(cell_val)
                    if m:
                        speculative_oracle_count += 1
                        matched_term = m.group(0)
                        defects.append({
                            "line": line_no,
                            "tc_id": tc_id,
                            "type": "SPECULATIVE_ORACLE",
                            "matched": matched_term,
                            "cell": col_name,
                            "message": (
                                f"Ambiguous or speculative blacklist term '{matched_term}' detected in {col_name}: '{cell_val}'. "
                                f"Expected results and specifications must be single-valued deterministic."
                            )
                        })
                        break  # one defect per cell is sufficient

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

    # Golden Ratio Warning (Target: 40% Happy / 40% Neg / 20% Sec)
    if total_test_cases >= 10 and sec_pct < 15.0:
        warnings.append({
            "line": 0,
            "type": "GOLDEN_RATIO_DEFICIT",
            "message": f"Security & Resilience coverage ({sec_pct}%) is below the Golden Ratio minimum (15.0%). Found {category_counts['security_resilience']}/{total_test_cases} TCs."
        })

    passed = len(defects) == 0

    return {
        "file": file_path,
        "has_test_cases": True,
        "total_test_cases": total_test_cases,
        "column_counts": column_counts,
        "passed": passed,
        "defects": defects,
        "warnings": warnings,
        "metrics": {
            "happy_ratio": f"{happy_pct}%",
            "negative_ratio": f"{neg_pct}%",
            "security_resilience_ratio": f"{sec_pct}%",
            "duplicate_cases": len(duplicate_pairs),
            "speculative_oracles": speculative_oracle_count,
            "vague_preconditions": missing_precondition_count
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Manual QA Test Case Linter & Completeness Guard")
    parser.add_argument("paths", nargs="*", help="Path to markdown test case files")
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
        result = lint_test_case_file(fpath)

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

        print(f"\n[{status}] {rel_path} ({result['total_test_cases']} TCs)")
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
