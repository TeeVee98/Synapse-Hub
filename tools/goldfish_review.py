#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/goldfish_review.py — Zero-Context Test Specification Reviewer
-------------------------------------------------------------------
Inspired by Google's Elephant-Goldfish Model (EGM).
Acts as a stateless, zero-context 'Goldfish' reviewer to stress-test test specifications,
BDD Gherkin feature files, and Acceptance Criteria BEFORE code synthesis begins.

5 Verification Vectors:
  1. Comprehension & System Boundaries (20%): Actor, Preconditions, Clear Target Scope.
  2. Dynamic Data & Idempotent Teardown (20%): Dynamic IDs (uniqueCode), No hardcoded collisions, Teardown hook.
  3. Assertion Rigor (25%): Unambiguous expected results, Anti-Fake Pass, explicit state checks.
  4. Boundary & Negative Scenarios (20%): Negative flows, invalid inputs, edge cases covered.
  5. Implementation Target (15%): Concrete Page Class mapping, API endpoints, or UI targets specified.

Usage:
  python tools/goldfish_review.py <path_to_spec.md_or_.feature>
  python tools/goldfish_review.py --json <path_to_spec>
"""

import os
import sys
import re
import json
import argparse

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


VAGUE_ASSERTION_PATTERNS = [
    re.compile(r'\b(works? fine|works? properly|works? as expected)\b', re.IGNORECASE),
    re.compile(r'\b(system works|page opens|everything is ok|no errors?)\b', re.IGNORECASE),
    re.compile(r'\b(hệ thống hoạt động bình thường|thành công mà không có lỗi|hiển thị đúng)\b', re.IGNORECASE),
    re.compile(r'\b(should succeed|should pass)\b(?!\s+(with|and assert|expecting))', re.IGNORECASE),
]

PRECISE_ASSERTION_PATTERNS = [
    re.compile(r'\b(assert|expect|verify|check)\b', re.IGNORECASE),
    re.compile(r'\b(status code|http \d{3}|returns? \d{3})\b', re.IGNORECASE),
    re.compile(r'\b(contains?|equals?|matches?|visible|hidden|disabled|enabled)\b', re.IGNORECASE),
    re.compile(r'\b(then\s+the\s+.*\s+(should|must|will))\b', re.IGNORECASE),
    re.compile(r'\b(thông báo|thành công|thất bại|mã lỗi|kết quả mong đợi)\b', re.IGNORECASE),
]

DYNAMIC_DATA_PATTERNS = [
    re.compile(r'\b(uniquecode|timestamp|random|uuid|generator|autogen|dyn_)\b', re.IGNORECASE),
    re.compile(r'\b(auto_\w+|test_\$\w+|faker)\b', re.IGNORECASE),
    re.compile(r'\b(dữ liệu động|ngẫu nhiên|mã tự sinh)\b', re.IGNORECASE),
]

HARDCODED_DATA_PATTERNS = [
    re.compile(r'["\'](user\d+|admin\d+|testuser|demo\d+|pass\d+)["\']', re.IGNORECASE),
    re.compile(r'id\s*[:=]\s*["\']\d+["\']', re.IGNORECASE),
]

TEARDOWN_PATTERNS = [
    re.compile(r'\b(teardown|cleanup|delete after|roll back|xóa dữ liệu|dọn dẹp|aftereach|afterall)\b', re.IGNORECASE),
]

BOUNDARY_NEGATIVE_PATTERNS = [
    re.compile(r'\b(negative|invalid|boundary|error|fail|reject|unauthorized|forbidden|400|401|403|404|500)\b', re.IGNORECASE),
    re.compile(r'\b(trường hợp lỗi|không hợp lệ|quá độ dài|để trống|bỏ trống|sai định dạng)\b', re.IGNORECASE),
    re.compile(r'\b(double submit|race condition|timeout|network lag)\b', re.IGNORECASE),
]

IMPLEMENTATION_TARGET_PATTERNS = [
    re.compile(r'\b([A-Z][a-zA-Z0-9]+(Page|Screen|View|Modal|Dialog|Api|Client|Service))\b'),
    re.compile(r'\b(page class|endpoint|url|route|table|input|button|form)\b', re.IGNORECASE),
    re.compile(r'(/api/v\d+/[\w/]+)', re.IGNORECASE),
]


def evaluate_spec_content(content: str, filename: str = "") -> dict:
    """
    Evaluates a test specification content through the 5 Goldfish vectors.
    Returns a structured dictionary with scores, findings, and overall readiness.
    """
    if not content or not content.strip():
        return {
            "file": filename,
            "score": 0,
            "passed": False,
            "status": "REJECTED",
            "vector_scores": {
                "Comprehension": 0,
                "Data Independence": 0,
                "Assertion Rigor": 0,
                "Boundary Coverage": 0,
                "Implementation Target": 0
            },
            "findings_count": 1,
            "findings": [{
                "vector": "Comprehension",
                "severity": "CRITICAL",
                "message": "Specification content is completely empty or whitespace only."
            }]
        }

    findings = []
    vector_scores = {}

    [line.strip() for line in content.splitlines() if line.strip()]
    content.lower()

    # -------------------------------------------------------------
    # Vector 1: Comprehension & System Boundaries (Weight: 20)
    # -------------------------------------------------------------
    v1_score = 0
    has_title = bool(re.search(r'^(#|feature:|title:|user story:)', content, re.MULTILINE | re.IGNORECASE))
    has_preconditions = bool(re.search(r'\b(precondition|given|context|tiền điều kiện|bối cảnh|trước khi)\b', content, re.IGNORECASE))
    has_actor = bool(re.search(r'\b(as a|actor|user|admin|role|người dùng|vai trò)\b', content, re.IGNORECASE))

    if has_title:
        v1_score += 8
    else:
        findings.append({
            "vector": "Comprehension",
            "severity": "MEDIUM",
            "message": "Missing explicit Title or Feature declaration (# Title / Feature: ...)."
        })

    if has_preconditions:
        v1_score += 7
    else:
        findings.append({
            "vector": "Comprehension",
            "severity": "HIGH",
            "message": "Missing Preconditions / Given setup context. Zero-context agents cannot deduce start state."
        })

    if has_actor:
        v1_score += 5
    else:
        findings.append({
            "vector": "Comprehension",
            "severity": "LOW",
            "message": "Missing explicit Actor/Role definition ('As a ...' / 'Actor: ...')."
        })
    vector_scores["Comprehension"] = v1_score

    # -------------------------------------------------------------
    # Vector 2: Dynamic Data & Idempotent Teardown (Weight: 20)
    # -------------------------------------------------------------
    v2_score = 0
    has_dynamic_data = any(p.search(content) for p in DYNAMIC_DATA_PATTERNS)
    has_hardcoded_data = any(p.search(content) for p in HARDCODED_DATA_PATTERNS)
    has_teardown = any(p.search(content) for p in TEARDOWN_PATTERNS)

    is_creation_test = bool(re.search(r'\b(create|add|insert|register|post|tạo mới|thêm mới|đăng ký)\b', content, re.IGNORECASE))

    if has_dynamic_data:
        v2_score += 10
    elif not is_creation_test:
        v2_score += 7  # Read-only or navigation spec
    else:
        findings.append({
            "vector": "Data Independence",
            "severity": "HIGH",
            "message": "Creation spec lacks dynamic test data generation (uniqueCode, timestamp). High risk of DB collisions."
        })

    if has_teardown:
        v2_score += 10
    elif not is_creation_test:
        v2_score += 10
    else:
        findings.append({
            "vector": "Data Independence",
            "severity": "HIGH",
            "message": "Creation spec lacks explicit automated Teardown / Cleanup step. Violates DB hygiene discipline."
        })

    if has_hardcoded_data:
        v2_score = max(0, v2_score - 5)
        findings.append({
            "vector": "Data Independence",
            "severity": "MEDIUM",
            "message": "Detected static/hardcoded credentials or entity IDs. Must parameterize via environment or dynamic generator."
        })
    vector_scores["Data Independence"] = v2_score

    # -------------------------------------------------------------
    # Vector 3: Assertion Rigor & Truth Anchor (Weight: 25)
    # -------------------------------------------------------------
    v3_score = 0
    precise_matches = sum(len(p.findall(content)) for p in PRECISE_ASSERTION_PATTERNS)
    vague_matches = sum(len(p.findall(content)) for p in VAGUE_ASSERTION_PATTERNS)

    if precise_matches >= 3:
        v3_score += 25
    elif precise_matches >= 1:
        v3_score += 15
        findings.append({
            "vector": "Assertion Rigor",
            "severity": "MEDIUM",
            "message": f"Low assertion density (found {precise_matches} precise check(s)). Spec needs more concrete expected values."
        })
    else:
        findings.append({
            "vector": "Assertion Rigor",
            "severity": "CRITICAL",
            "message": "Zero concrete assertions or expected outcomes detected in spec. Violates Truth Anchor."
        })

    if vague_matches > 0:
        v3_score = max(0, v3_score - (vague_matches * 5))
        findings.append({
            "vector": "Assertion Rigor",
            "severity": "HIGH",
            "message": f"Found {vague_matches} vague assertion phrase(s) ('works fine', 'hoạt động bình thường'). Replace with concrete verification criteria."
        })
    vector_scores["Assertion Rigor"] = v3_score

    # -------------------------------------------------------------
    # Vector 4: Boundary & Negative Scenarios (Weight: 20)
    # -------------------------------------------------------------
    v4_score = 0
    has_boundary = any(p.search(content) for p in BOUNDARY_NEGATIVE_PATTERNS)

    if has_boundary:
        v4_score = 20
    else:
        findings.append({
            "vector": "Boundary Coverage",
            "severity": "MEDIUM",
            "message": "No negative, boundary, or invalid input scenarios specified. Spec only tests the happy path."
        })
        v4_score = 5
    vector_scores["Boundary Coverage"] = v4_score

    # -------------------------------------------------------------
    # Vector 5: Implementation Target & Technical Mapping (Weight: 15)
    # -------------------------------------------------------------
    v5_score = 0
    has_target = any(p.search(content) for p in IMPLEMENTATION_TARGET_PATTERNS)

    if has_target:
        v5_score = 15
    else:
        findings.append({
            "vector": "Implementation Target",
            "severity": "LOW",
            "message": "No target PageClass, API endpoint, or concrete UI selector category referenced. Engineers must guess technical anchors."
        })
        v5_score = 5
    vector_scores["Implementation Target"] = v5_score

    # Total score calculation
    total_score = sum(vector_scores.values())
    total_score = max(0, min(100, total_score))

    passed = total_score >= 80 and not any(f["severity"] == "CRITICAL" for f in findings)

    return {
        "file": filename,
        "score": total_score,
        "passed": passed,
        "status": "APPROVED" if passed else "REJECTED",
        "vector_scores": vector_scores,
        "findings_count": len(findings),
        "findings": findings
    }


def review_file(filepath: str) -> dict:
    if not os.path.isfile(filepath):
        return {
            "file": filepath,
            "score": 0,
            "passed": False,
            "status": "ERROR",
            "vector_scores": {},
            "findings_count": 1,
            "findings": [{"vector": "File System", "severity": "CRITICAL", "message": f"File not found: {filepath}"}]
        }

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, "r", encoding="latin-1") as f:
                content = f.read()
        except Exception as e:
            return {
                "file": filepath,
                "score": 0,
                "passed": False,
                "status": "ERROR",
                "vector_scores": {},
                "findings_count": 1,
                "findings": [{"vector": "Encoding", "severity": "CRITICAL", "message": f"Could not read file: {e}"}]
            }

    return evaluate_spec_content(content, filename=filepath)


def print_cli_report(result: dict):
    print("=" * 70)
    print("  GOLDFISH SPECIFICATION AUDITOR — ZERO-CONTEXT VERIFICATION")
    print("  Inspired by Google Elephant-Goldfish Model (EGM)")
    print("=" * 70)
    print(f"Target Specification : {result['file'] or 'Direct Input'}")
    print(f"Readiness Score      : {result['score']}/100")
    status_icon = "✅" if result['passed'] else "❌"
    print(f"Audit Verdict        : {status_icon} [{result['status']}] (Threshold: >= 80%)")
    print("-" * 70)
    print("Vector Breakdown:")
    for vec, score in result.get("vector_scores", {}).items():
        max_v = 25 if vec == "Assertion Rigor" else (15 if vec == "Implementation Target" else 20)
        filled = int(score / max_v * 10) if max_v > 0 else 0
        filled = max(0, min(10, filled))
        bar = "#" * filled + "-" * (10 - filled)
        print(f"  • {vec:<24}: {score:>2}/{max_v:>2} [{bar}]")

    print("-" * 70)
    if result["findings"]:
        print(f"Discovered Unstated Assumptions & Gaps ({len(result['findings'])}):")
        for i, item in enumerate(result["findings"], 1):
            sev = item["severity"]
            sev_badge = f"[{sev}]"
            print(f"  {i}. {sev_badge:<10} ({item['vector']}) {item['message']}")
    else:
        print("✅ Zero unstated assumptions detected. Specification is 100% implementation-ready.")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Goldfish Spec Reviewer — Zero-context stress-test for specifications and user stories."
    )
    parser.add_argument("spec_file", nargs="?", default="", help="Path to specification Markdown or Gherkin .feature file (use '-' for stdin)")
    parser.add_argument("--stdin", action="store_true", help="Read specification from standard input (stdin)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON format")
    parser.add_argument("--min-score", type=int, default=80, help="Minimum readiness score threshold (default: 80)")

    args = parser.parse_args()

    if args.spec_file == "-" or getattr(args, "stdin", False):
        content = sys.stdin.read()
        result = evaluate_spec_content(content, filename="<stdin>")
    elif not args.spec_file:
        parser.print_help()
        sys.exit(1)
    else:
        result = review_file(args.spec_file)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_cli_report(result)

    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
