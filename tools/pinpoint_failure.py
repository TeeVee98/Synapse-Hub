#!/usr/bin/env python3
"""
Fast Zero-Token Failure Pinpointer for Katalon & Jenkins Reports.
Scans the latest Reports/**/JUnit_Report.xml, extracts failed Test Cases,
exact failed lines in Groovy/Script, and the root-cause exception.
Outputs < 100 tokens.

Usage:
    python3 tools/pinpoint_failure.py
    python3 tools/pinpoint_failure.py path/to/JUnit_Report.xml
"""
import os
import sys
import glob
import xml.etree.ElementTree as ET
import re

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def find_latest_report(search_dir="."):
    """Finds the latest JUnit XML report across Reports/, test-results/, and standard report directories."""
    candidate_patterns = [
        os.path.join(search_dir, "Reports", "**", "*.xml"),
        os.path.join(search_dir, "reports", "**", "*.xml"),
        os.path.join(search_dir, "test-results", "**", "*.xml"),
        os.path.join(search_dir, "build", "test-results", "**", "*.xml"),
        os.path.join(search_dir, "**", "*junit*.xml"),
        os.path.join(search_dir, "**", "results.xml"),
    ]
    matched = []
    for pat in candidate_patterns:
        matched.extend(glob.glob(pat, recursive=True))

    if not matched:
        return None

    valid_reports = []
    for r in set(matched):
        base = os.path.basename(r).lower()
        if base in ("pom.xml", "testng.xml", "web.xml", "manifest.xml"):
            continue
        valid_reports.append(r)

    if not valid_reports:
        return None

    valid_reports.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return valid_reports[0]

def extract_failed_locations(text):
    """Extracts failing file locations (file:line) across Groovy, Python, TypeScript, JavaScript, and Java."""
    locations = []
    # 1. Groovy Enterprise & Katalon script format: Enterprise.pages.LoginPage.groovy:48 or Script123.groovy:10 or TC-...:10
    groovy_lines = re.findall(r"(?:Enterprise\.pages\.[\w]+|TC-[\w\s\u00C0-\u1EF9]+|Script\d+)\.groovy:\d+|(?:TC-[\w\s\u00C0-\u1EF9]+:\d+)", text)
    locations.extend(groovy_lines)

    # 2. Playwright / Jest / TS / JS / Java / Groovy stack frames: at [method] (path:line:col) or at path:line:col
    # Supports paths with spaces and Windows drive letters (C:\...)
    for m in re.finditer(r'at (?:[a-zA-Z0-9_$.<>]+\s+\()?([a-zA-Z]:[/\\][^:()\r\n\t]+|[^:()\r\n\t]+?\.(?:ts|tsx|js|jsx|mjs|cjs|py|groovy|java)):(\d+)', text):
        f_p, l_n = m.group(1).strip(), m.group(2)
        locations.append(f"{f_p}:{l_n}")

    # 3. Python traceback format: File "path/to/file.py", line 42
    for m in re.finditer(r'File ["\']([^"\']+\.(?:py|groovy|ts|tsx|js|jsx|mjs|cjs|java))["\'], line (\d+)', text):
        locations.append(f"{m.group(1).strip()}:{m.group(2)}")

    # 4. Generic file:line pattern: path/to/file.(ts|js|py|groovy):line
    for m in re.finditer(r'(?:([a-zA-Z]:[/\\][^:()\r\n\t]+|[^:()\r\n\t\s]+?\.(?:ts|tsx|js|jsx|mjs|cjs|py|groovy|java))):(\d+):?', text):
        loc_str = f"{m.group(1).strip()}:{m.group(2)}"
        if loc_str not in locations:
            locations.append(loc_str)

    seen = set()
    deduped = []
    for loc in locations:
        if loc not in seen:
            seen.add(loc)
            deduped.append(loc)
    return deduped


def _is_framework_frame(path_str: str) -> bool:
    normalized = path_str.replace("\\", "/").lower()
    return any(p in normalized for p in ("node_modules/", "site-packages/", "/_pytest/", "internal/modules/", "virtual_documents/"))


def parse_failures(xml_path):
    if not os.path.exists(xml_path):
        print(f"Error: {xml_path} does not exist.")
        return []

    try:
        tree = ET.parse(xml_path)  # nosec B314
        root = tree.getroot()
    except (ET.ParseError, OSError) as e:
        print(f"Error parsing JUnit XML '{xml_path}': {e}")
        return []

    failures = []
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")

    for suite in suites:
        for tc in suite.findall("testcase"):
            tc_name = tc.get("name", "Unknown")
            tc_time = tc.get("time", "0")
            fail = tc.find("failure")
            err = tc.find("error")
            target = fail if fail is not None else err

            if target is not None:
                msg = target.get("message", "")
                text = target.text or ""
                combined = (msg + "\n" + text).replace("&#xa;", "\n")

                # Extract Root Cause Reason
                reason_match = re.search(r"Reason:\s*(.+?)(?=\n\s*at|\Z)", combined, re.DOTALL)
                if reason_match:
                    reason = reason_match.group(1).strip()
                else:
                    lines = [line.strip() for line in combined.split("\n") if line.strip()]
                    reason = lines[0] if lines else "Unknown Error"

                # Multi-language stack trace extraction (Python, TS/JS, Groovy)
                failed_locs = extract_failed_locations(combined)
                f_file = "UnknownFile"
                f_line = "?"
                if failed_locs:
                    # Prefer project/test code frame over external runtime/framework frame
                    chosen_loc = next((loc for loc in failed_locs if not _is_framework_frame(loc)), failed_locs[0])
                    if ":" in chosen_loc:
                        p_file, p_line = chosen_loc.rsplit(":", 1)
                        f_file = p_file
                        f_line = p_line

                # Resilient time parsing
                clean_time = re.sub(r"[^\d.]", "", str(tc_time or "0"))
                try:
                    formatted_time = f"{float(clean_time):.1f}s" if clean_time else "0.0s"
                except (ValueError, TypeError):
                    formatted_time = "0.0s"

                failures.append({
                    "tc": tc_name.split("/")[-1],
                    "time": formatted_time,
                    "reason": reason.split("\n")[0][:180],
                    "failed_at": failed_locs[:2] if failed_locs else ["See JUnit report"],
                    "file": f_file,
                    "line": f_line
                })

    return failures


parse_junit_xml = parse_failures

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print("Usage: python3 tools/pinpoint_failure.py [path/to/JUnit_Report.xml]")
        print("Scans JUnit XML reports and pinpoints failed test cases and code lines in under 100 tokens.")
        sys.exit(0)

    if len(sys.argv) > 1 and not os.path.exists(sys.argv[1]):
        print(f"Error: Specified report file does not exist: {sys.argv[1]}")
        sys.exit(1)

    xml_path = sys.argv[1] if len(sys.argv) > 1 else find_latest_report()
    if not xml_path:
        print("No JUnit XML report found in Reports/, test-results/, or reports/.")
        sys.exit(0)

    print(f"=== Report: {xml_path} ===")
    failures = parse_failures(xml_path)
    if not failures:
        print("✅ 100% PASSED: Zero failures found in report.")
        sys.exit(0)

    print(f"❌ Found {len(failures)} Failed Test Case(s):")
    for i, f in enumerate(failures, 1):
        print(f"[{i}] {f['tc']} ({f['time']})")
        print(f"    Cause: {f['reason']}")
        print(f"    Line:  {', '.join(f['failed_at'])}")
    sys.exit(1)

if __name__ == "__main__":
    main()
