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

# Vague / Speculative keywords that violate Single-Valued Deterministic Test Oracle
SPECULATIVE_KEYWORDS = [
    r"\bhoặc\b",
    r"\btùy\s+(?:backend|quy\s+tắc|server|hệ\s+thống)\b",
    r"\bcó\s+thể\s+(?:tự\s+động|chấp\s+nhận|từ\s+chối)\b",
    r"\bxử\s+lý\s+an\s+toàn\b(?!\s*:\s*(?:chặn|báo\s+lỗi|từ\s+chối))",
    r"\bphù\s+hợp\b",
    r"\bhoạt\s+động\s+bình\s+thường\b(?!\s*\(|\s*:)",
]

SPECULATIVE_PATTERN = re.compile("|".join(SPECULATIVE_KEYWORDS), re.IGNORECASE)


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculates semantic text similarity using normalized sequence matching."""
    t1 = re.sub(r"[^\w\s]", "", text1.lower()).strip()
    t2 = re.sub(r"[^\w\s]", "", text2.lower()).strip()
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
                    tables.append({
                        "headers": headers,
                        "rows": rows,
                        "header_line": i - len(rows) - 1
                    })
                    continue
        i += 1

    return tables


def lint_test_case_file(file_path: str) -> Dict[str, Any]:
    """Lints a markdown test case file against ISO 29119-3 and Synapse-Hub invariants."""
    if not os.path.isfile(file_path):
        return {"file": file_path, "error": "File not found", "passed": False}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return {"file": file_path, "error": f"Cannot read file: {e}", "passed": False}

    tables = parse_markdown_tables(content)
    test_tables = []
    for t in tables:
        h_lower = [h.lower() for h in t["headers"]]
        if any("tc id" in h or "tc_id" in h or "test title" in h for h in h_lower):
            test_tables.append(t)

    if not test_tables:
        return {
            "file": file_path,
            "has_test_cases": False,
            "passed": True,
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
            tc_id = row.get("TC ID") or row.get("TC_ID") or f"ROW_{line_no}"
            test_title = row.get("Test Title") or row.get("Scenario / Title") or ""
            expected = row.get("Expected Result") or ""
            precond = row.get("Pre-Condition") or row.get("Pre-Conditions") or ""
            priority = row.get("Priority") or ""
            risk_level = row.get("Risk Level") or row.get("Risk Tier") or ""

            # Check 1: Speculative Oracle Language
            m = SPECULATIVE_PATTERN.search(expected)
            if m:
                speculative_oracle_count += 1
                defects.append({
                    "line": line_no,
                    "tc_id": tc_id,
                    "type": "SPECULATIVE_ORACLE",
                    "matched": m.group(0),
                    "message": f"Non-deterministic oracle in Expected Result: '{m.group(0)}'. Expected results must be single-valued deterministic."
                })

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

            # Categorize for Golden Ratio
            combined_text = f"{test_title} {expected} {risk_level} {priority}".lower()
            if any(k in combined_text for k in ["xss", "sqli", "injection", "race", "concurrency", "double submit", "double-click", "csrf", "brute", "500", "502", "504", "timeout", "idor", "multi-tab", "resilience", "atomicity", "unicode"]):
                category_counts["security_resilience"] += 1
            elif any(k in expected.lower() for k in ["từ chối", "chặn", "báo lỗi", "thất bại", "không hợp lệ", "mã lỗi", "400", "401", "403", "404", "409", "422"]) or any(k in test_title.lower() for k in ["sai định dạng", "để trống", "vượt quá", "thiếu", "không hợp lệ", "negative", "invalid"]):
                category_counts["negative"] += 1
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
            id_a = row_a.get("TC ID") or row_a.get("TC_ID") or f"ROW_{idx_a}"
            id_b = row_b.get("TC ID") or row_b.get("TC_ID") or f"ROW_{idx_b}"

            # Compare normalized title + steps
            text_a = f"{row_a.get('Test Title', '')} {row_a.get('Test Steps', '')}".strip()
            text_b = f"{row_b.get('Test Title', '')} {row_b.get('Test Steps', '')}".strip()

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
    happy_pct = round((category_counts["happy"] / max(1, total_test_cases)) * 100, 1)
    neg_pct = round((category_counts["negative"] / max(1, total_test_cases)) * 100, 1)
    sec_pct = round((category_counts["security_resilience"] / max(1, total_test_cases)) * 100, 1)

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

    files = list(args.paths)
    if args.audit_all or not files:
        target_dirs = [
            os.path.join(_REPO_ROOT, "examples", "practices", "testcases"),
            os.path.join(_REPO_ROOT, "test-design")
        ]
        for td in target_dirs:
            if os.path.isdir(td):
                for root, _, fs in os.walk(td):
                    for f in fs:
                        if f.endswith(".md"):
                            files.append(os.path.join(root, f))

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
        rel_path = os.path.relpath(fpath, _REPO_ROOT)
        result = lint_test_case_file(fpath)
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
