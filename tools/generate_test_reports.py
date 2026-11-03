#!/usr/bin/env python3
"""
Enterprise Test Report Aggregator & summaryTemp Generator (Cross-Platform)
-------------------------------------------------------------------------
Parses JUnit XML and Allure test reports across target directories
and exports standardized summaryTemp.txt for CI/CD dashboards.
Replaces PowerShell-only script with a zero-dependency, cross-platform engine.
"""

import os
import sys
import glob
import argparse
import xml.etree.ElementTree as ET

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))


def find_latest_junit_report(search_dirs):
    """Finds the most recent JUnit XML file across the given search directories."""
    candidates = []
    for d in search_dirs:
        if os.path.exists(d):
            for pattern in ["**/*junit*.xml", "**/*test*.xml", "**/TEST-*.xml", "**/*.xml"]:
                for p in glob.glob(os.path.join(d, pattern), recursive=True):
                    try:
                        mtime = os.path.getmtime(p)
                        candidates.append((mtime, p))
                    except OSError as err:
                        sys.stderr.write(f"Notice: getmtime skipped: {err}\n")
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def parse_junit_xml(xml_path):
    """Parses a JUnit XML file and returns (passed, failures, errors, skipped)."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"[WARN] Failed to parse XML file {xml_path}: {e}")
        return 0, 0, 0, 0

    total_tests = 0
    failures = 0
    errors = 0
    skipped = 0

    if root.tag == "testsuites":
        total_tests = int(root.attrib.get("tests", 0))
        failures = int(root.attrib.get("failures", 0))
        errors = int(root.attrib.get("errors", 0))
        skipped = int(root.attrib.get("skipped", 0))
        passed_attr = root.attrib.get("passed")
        if passed_attr is not None:
            return int(passed_attr), failures, errors, skipped
    elif root.tag == "testsuite":
        total_tests = int(root.attrib.get("tests", 0))
        failures = int(root.attrib.get("failures", 0))
        errors = int(root.attrib.get("errors", 0))
        skipped = int(root.attrib.get("skipped", 0))
    else:
        # Count testcase elements
        for tc in root.iter("testcase"):
            total_tests += 1
            if tc.find("failure") is not None:
                failures += 1
            elif tc.find("error") is not None:
                errors += 1
            elif tc.find("skipped") is not None:
                skipped += 1

    passed = max(0, total_tests - (failures + errors + skipped))
    return passed, failures, errors, skipped


def generate_reports(target_dir=None, project_name="Enterprise-Automation"):
    """Aggregates reports and outputs summaryTemp.txt."""
    root_dir = target_dir or PROJECT_ROOT
    reports_dir = os.path.join(root_dir, "Reports")
    test_reports_dir = os.path.join(root_dir, "TestReports")

    os.makedirs(test_reports_dir, exist_ok=True)
    summary_file = os.path.join(test_reports_dir, "summaryTemp.txt")

    # Check if summary already exists
    for check_dir in [reports_dir, test_reports_dir]:
        existing = os.path.join(check_dir, "summaryTemp.txt")
        if os.path.exists(existing):
            try:
                with open(existing, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if "Passed" in content:
                    print(f"[+] Found existing summary file: {existing}")
                    return 0
            except OSError as err:
                sys.stderr.write(f"Notice: Read summaryTemp skipped: {err}\n")

    latest_xml = find_latest_junit_report([reports_dir, test_reports_dir, root_dir])
    if latest_xml:
        print(f"[+] Parsing latest JUnit XML report: {latest_xml}")
        passed, failures, errors, skipped = parse_junit_xml(latest_xml)
    else:
        print("[!] No JUnit XML report found on disk. Initializing zero-baseline.")
        passed, failures, errors, skipped = 0, 0, 0, 0

    summary_text = (
        f"Summary: {passed} Passed - {failures} Failures - {errors} Errors - {skipped} Skipped\n"
        f"Project: {project_name}\n"
    )

    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary_text)

    print(f"[+] Summary report saved to: {summary_file}")
    print(f"    {summary_text.strip()}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Aggregate test reports and generate summaryTemp.txt")
    parser.add_argument("target", nargs="?", default=None, help="Target project root directory")
    parser.add_argument("--project-name", default="Enterprise-Automation", help="Project label for summary")
    args = parser.parse_args()

    sys.exit(generate_reports(args.target, project_name=args.project_name))


if __name__ == "__main__":
    main()
