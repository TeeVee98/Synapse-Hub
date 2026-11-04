#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tools/spec_drift_sentinel.py — Spec-to-Code Drift Sentinel
---------------------------------------------------------
Inspired by Google's Elephant-Goldfish Model (egm-drift-report).
Audits whether the actual test automation code accurately implements the approved
specification, detecting Deficit Drift (missing assertions) and Scope Drift (unauthorized bloat).

Metrics:
  - Deficit Drift: Requirements / Criteria present in spec but missing in test code.
  - Scope Drift: Test actions / workflows in code that have no grounding in the spec.
  - Alignment Score: Percentage of spec criteria satisfied minus scope drift penalty.

Usage:
  python tools/spec_drift_sentinel.py --spec <spec_file> --code <test_file_or_dir>
  python tools/spec_drift_sentinel.py --spec <spec_file> --code <test_file> --markdown SPEC_DRIFT_REPORT.md
  python tools/spec_drift_sentinel.py --spec <spec_file> --code <test_file> --json
"""

import os
import sys
import re
import json
import argparse
from typing import List, Dict, Any, Tuple

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


def extract_spec_criteria(spec_text: str) -> List[Dict[str, Any]]:
    """
    Extracts individual criteria, scenarios, or acceptance points from Markdown or Gherkin.
    """
    criteria = []
    lines = spec_text.splitlines()

    current_section = "General"
    idx = 1

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Header detection
        if stripped.startswith("#"):
            current_section = stripped.lstrip("#").strip()
            continue

        # Gherkin Scenario
        if re.match(r'^(Scenario|Scenario Outline):\s*(.+)', stripped, re.IGNORECASE):
            match = re.match(r'^(Scenario|Scenario Outline):\s*(.+)', stripped, re.IGNORECASE)
            criteria.append({
                "id": f"AC-{idx:02d}",
                "type": "scenario",
                "section": current_section,
                "text": match.group(2).strip(),
                "raw": stripped
            })
            idx += 1
            continue

        # Acceptance criteria checklist: - [ ] or - [x] or * [ ]
        if re.match(r'^[-*]\s*\[[ xX]\]\s*(.+)', stripped):
            match = re.match(r'^[-*]\s*\[[ xX]\]\s*(.+)', stripped)
            criteria.append({
                "id": f"AC-{idx:02d}",
                "type": "checklist",
                "section": current_section,
                "text": match.group(1).strip(),
                "raw": stripped
            })
            idx += 1
            continue

        # Bullet criteria: - Criterion or 1. Criterion with keywords
        if re.match(r'^(\d+\.|\-|\*)\s+(should|must|verify|assert|expect|khi|phải|kiểm tra)\s+(.+)', stripped, re.IGNORECASE):
            criteria.append({
                "id": f"AC-{idx:02d}",
                "type": "bullet",
                "section": current_section,
                "text": stripped,
                "raw": stripped
            })
            idx += 1
            continue

        # Gherkin Then / And assert steps
        if re.match(r'^(Then|And)\s+(the\s+)?(system|page|user|message|response|status|button|element)\s+(should|must|will|is|displays?|returns?)\s+(.+)', stripped, re.IGNORECASE):
            criteria.append({
                "id": f"AC-{idx:02d}",
                "type": "gherkin_then",
                "section": current_section,
                "text": stripped,
                "raw": stripped
            })
            idx += 1
            continue

    # Fallback if no structured AC was found: split into paragraphs with assertions
    if not criteria:
        for line in lines:
            stripped = line.strip()
            if any(k in stripped.lower() for k in ["assert", "expect", "verify", "mong đợi", "kiểm tra", "kết quả"]):
                criteria.append({
                    "id": f"AC-{idx:02d}",
                    "type": "heuristic",
                    "section": current_section,
                    "text": stripped,
                    "raw": stripped
                })
                idx += 1

    return criteria


def extract_code_tokens_and_assertions(code_text: str) -> Tuple[List[str], List[str]]:
    """
    Extracts keywords, method calls, and assertion statements from test script code.
    """
    assertions = []
    actions = []

    # Assertion lines regex (Groovy, TS, Python, Java)
    assert_regex = re.compile(
        r'(\bassert\b.*|\bexpect\(.*|\.should\(.*|WebUI\.verify.*|assertThat.*|assertEquals.*|assertTrue.*)',
        re.IGNORECASE
    )

    action_regex = re.compile(
        r'(\b\w+Page\.\w+\(.*\)|WebUI\.click.*|WebUI\.setText.*|await\s+\w+\.\w+\(.*\)|page\.\w+\(.*\))',
        re.IGNORECASE
    )

    for line in code_text.splitlines():
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("//") or line_clean.startswith("#"):
            continue

        if assert_regex.search(line_clean):
            assertions.append(line_clean)
        elif action_regex.search(line_clean):
            actions.append(line_clean)

    return assertions, actions


def split_camel_case(text: str) -> str:
    """Splits camelCase and PascalCase identifiers into space-separated words."""
    return re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', text)


def normalize_stem(word: str) -> str:
    """Simple heuristic stemmer for English suffixes to match singular/plural and verb tenses."""
    w = word.lower()
    if len(w) > 4:
        if w.endswith("ing"):
            return w[:-3]
        if w.endswith("ies"):
            return w[:-3] + "y"
        if w.endswith("es"):
            return w[:-2]
        if w.endswith("ed"):
            return w[:-2]
        if w.endswith("s") and not w.endswith("ss"):
            return w[:-1]
    return w


def tokenize_text(text: str) -> set:
    """Extracts meaningful normalized words from text with camelCase splitting."""
    expanded = split_camel_case(text)
    words = re.findall(r'[a-zA-Z0-9_\u00C0-\u1EF9]+', expanded.lower())
    stop_words = {
        "the", "a", "an", "is", "are", "in", "on", "at", "to", "for", "with",
        "and", "or", "then", "when", "given", "should", "must", "be", "của",
        "và", "là", "khi", "thì", "được", "có", "trong", "trên", "cho", "user"
    }
    tokens = set()
    for w in words:
        if w not in stop_words and len(w) > 2:
            tokens.add(normalize_stem(w))
    return tokens


def compute_drift(spec_criteria: List[Dict[str, Any]], code_files: List[Tuple[str, str]]) -> Dict[str, Any]:
    """
    Computes Deficit Drift, Scope Drift, and Alignment Score.
    """
    all_code_assertions = []
    all_code_actions = []
    combined_code = ""

    for file_path, content in code_files:
        assertions, actions = extract_code_tokens_and_assertions(content)
        all_code_assertions.extend([(file_path, a) for a in assertions])
        all_code_actions.extend([(file_path, a) for a in actions])
        combined_code += "\n" + content

    code_tokens = tokenize_text(combined_code)

    covered_criteria = []
    deficit_drift = []

    for crit in spec_criteria:
        crit_tokens = tokenize_text(crit["text"])
        if not crit_tokens:
            continue

        matched_tokens = crit_tokens.intersection(code_tokens)
        overlap_ratio = len(matched_tokens) / len(crit_tokens)

        # Check if any assertion matches keywords
        has_assertion_anchor = any(
            len(crit_tokens.intersection(tokenize_text(a[1]))) >= 1
            for a in all_code_assertions
        )

        if overlap_ratio >= 0.4 or has_assertion_anchor:
            covered_criteria.append({
                "criterion": crit,
                "matched_tokens": list(matched_tokens),
                "overlap_ratio": round(overlap_ratio, 2)
            })
        else:
            deficit_drift.append({
                "criterion": crit,
                "missing_tokens": list(crit_tokens - matched_tokens),
                "overlap_ratio": round(overlap_ratio, 2)
            })

    # Scope drift: identify code actions that don't match any spec keywords
    scope_drift = []
    all_spec_tokens = set()
    for crit in spec_criteria:
        all_spec_tokens.update(tokenize_text(crit["text"]))

    for file_path, action in all_code_actions:
        action_tokens = tokenize_text(action)
        if not action_tokens:
            continue
        spec_overlap = action_tokens.intersection(all_spec_tokens)
        # Action is considered scope creep if it introduces totally unrelated verbs
        if len(spec_overlap) == 0 and not any(w in action.lower() for w in ["navigateto", "open", "close", "wait", "delay", "sleep"]):
            scope_drift.append({
                "file": file_path,
                "action": action,
                "reason": "Action method not grounded in any specification criterion."
            })

    total_spec = len(spec_criteria)
    if total_spec == 0:
        alignment_score = 100.0 if not code_files else 0.0
    else:
        coverage_pct = (len(covered_criteria) / total_spec) * 100.0
        penalty = min(20.0, len(scope_drift) * 3.0)
        alignment_score = max(0.0, round(coverage_pct - penalty, 2))

    passed = (len(deficit_drift) == 0) and (alignment_score >= 80.0)

    return {
        "total_criteria": total_spec,
        "covered_count": len(covered_criteria),
        "deficit_drift_count": len(deficit_drift),
        "scope_drift_count": len(scope_drift),
        "alignment_score": alignment_score,
        "passed": passed,
        "status": "ALIGNED" if passed else "DRIFT_DETECTED",
        "covered_criteria": covered_criteria,
        "deficit_drift": deficit_drift,
        "scope_drift": scope_drift,
        "assertion_count": len(all_code_assertions)
    }


def generate_markdown_report(result: Dict[str, Any], spec_file: str, code_path: str) -> str:
    md = []
    md.append("# SPEC-TO-CODE DRIFT REPORT")
    md.append("> Generated autonomously by Synapse-Hub `tools/spec_drift_sentinel.py`  ")
    md.append(f"> **Specification:** `{spec_file}` | **Code Target:** `{code_path}`  \n")
    md.append("---")

    status_icon = "✅" if result["passed"] else "❌"
    md.append(f"## 📊 Executive Summary: {status_icon} [{result['status']}]")
    md.append(f"- **Alignment Score:** `{result['alignment_score']}%` (Pass threshold: >= 80% & zero Deficit Drift)")
    md.append(f"- **Total Spec Criteria:** {result['total_criteria']}")
    md.append(f"- **Covered Criteria:** {result['covered_count']}")
    md.append(f"- **Deficit Drift (Missing in Code):** {result['deficit_drift_count']}")
    md.append(f"- **Scope Drift (Extraneous in Code):** {result['scope_drift_count']}")
    md.append(f"- **Extracted Code Assertions:** {result['assertion_count']}\n")

    md.append("---")
    md.append("## 🔍 Deficit Drift Analysis (Unsatisfied Requirements)")
    if result["deficit_drift"]:
        md.append("| ID | Section | Criterion Text | Status |")
        md.append("| :--- | :--- | :--- | :--- |")
        for item in result["deficit_drift"]:
            crit = item["criterion"]
            md.append(f"| `{crit['id']}` | {crit['section']} | {crit['text']} | ❌ **MISSING IN CODE** |")
    else:
        md.append("✅ **Zero Deficit Drift detected.** 100% of specification criteria are grounded in test code.")

    md.append("\n---")
    md.append("## ⚠️ Scope Drift Analysis (Extraneous Code Actions)")
    if result["scope_drift"]:
        md.append("| File | Extraneous Action | Reason |")
        md.append("| :--- | :--- | :--- |")
        for s in result["scope_drift"][:10]:
            md.append(f"| `{os.path.basename(s['file'])}` | `{s['action'][:60]}` | {s['reason']} |")
    else:
        md.append("✅ **Zero Scope Drift detected.** No ungrounded code bloat found.")

    return "\n".join(md)


def print_cli_report(result: Dict[str, Any], spec_file: str, code_path: str):
    print("=" * 70)
    print("  SPEC-TO-CODE DRIFT SENTINEL — ALIGNMENT & FIDELITY AUDIT")
    print("  Inspired by Google Elephant-Goldfish Model (EGM)")
    print("=" * 70)
    print(f"Spec File       : {spec_file}")
    print(f"Code Target     : {code_path}")
    print(f"Alignment Score : {result['alignment_score']}%")
    status_icon = "✅" if result["passed"] else "❌"
    print(f"Verdict         : {status_icon} [{result['status']}] (DoD Requirement: Zero Deficit Drift)")
    print("-" * 70)
    print(f"  • Criteria Evaluated : {result['total_criteria']}")
    print(f"  • Criteria Satisfied : {result['covered_count']}/{result['total_criteria']}")
    print(f"  • Deficit Drift      : {result['deficit_drift_count']} missing item(s)")
    print(f"  • Scope Drift        : {result['scope_drift_count']} extraneous action(s)")
    print(f"  • Code Assertions    : {result['assertion_count']} detected")
    print("-" * 70)

    if result["total_criteria"] == 0:
        print("⚠️ Warning: No testable acceptance criteria, scenarios, or assertions were discovered in spec.")
    elif result["deficit_drift"]:
        print("❌ Deficit Drift Items (Requirements missing assertions in code):")
        for item in result["deficit_drift"]:
            crit = item["criterion"]
            print(f"  • [{crit['id']}] ({crit['section']}): {crit['text']}")
    else:
        print("✅ Zero Deficit Drift. All spec criteria are reflected in code.")

    if result["scope_drift"]:
        print(f"\n⚠️ Scope Drift Detected ({len(result['scope_drift'])} actions with no spec anchor):")
        for s in result["scope_drift"][:5]:
            print(f"  • {os.path.basename(s['file'])}: {s['action'][:60]}")
    print("=" * 70)


def collect_code_files(code_path: str) -> List[Tuple[str, str]]:
    files = []
    valid_exts = {".groovy", ".ts", ".js", ".py", ".java"}

    if os.path.isfile(code_path):
        try:
            with open(code_path, "r", encoding="utf-8", errors="replace") as f:
                files.append((code_path, f.read()))
        except Exception as e:
            print(f"Warning: Could not read code file {code_path}: {e}", file=sys.stderr)
    elif os.path.isdir(code_path):
        for root, _, filenames in os.walk(code_path):
            if any(p in root for p in [".git", "node_modules", "Reports", "build", "dist"]):
                continue
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in valid_exts:
                    full_p = os.path.join(root, fname)
                    try:
                        with open(full_p, "r", encoding="utf-8", errors="replace") as f:
                            files.append((full_p, f.read()))
                    except (OSError, UnicodeDecodeError) as err:
                        sys.stderr.write(f"Warning: skipped {fname}: {err}\n")
    return files


def main():
    parser = argparse.ArgumentParser(
        description="Spec-to-Code Drift Sentinel — Audits code alignment against test specifications."
    )
    parser.add_argument("--spec", required=True, help="Path to specification file (Markdown or Gherkin .feature)")
    parser.add_argument("--code", required=True, help="Path to test script or directory of test scripts")
    parser.add_argument("--markdown", "-m", help="Path to export Markdown drift report (e.g. SPEC_DRIFT_REPORT.md)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON format")

    args = parser.parse_args()

    if not os.path.isfile(args.spec):
        print(f"Error: Specification file not found: {args.spec}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.spec, "r", encoding="utf-8", errors="replace") as f:
            spec_text = f.read()
    except Exception as e:
        print(f"Error reading spec file {args.spec}: {e}", file=sys.stderr)
        sys.exit(1)

    spec_criteria = extract_spec_criteria(spec_text)
    code_files = collect_code_files(args.code)

    if not code_files:
        print(f"Error: No valid test code files found at {args.code}", file=sys.stderr)
        sys.exit(1)

    result = compute_drift(spec_criteria, code_files)

    if args.markdown:
        md_content = generate_markdown_report(result, args.spec, args.code)
        try:
            out_dir = os.path.dirname(os.path.abspath(args.markdown))
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(args.markdown, "w", encoding="utf-8") as f:
                f.write(md_content)
            print(f"📝 Markdown drift report exported to: {args.markdown}")
        except OSError as e:
            print(f"Warning: Could not write markdown report: {e}", file=sys.stderr)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_cli_report(result, args.spec, args.code)

    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
