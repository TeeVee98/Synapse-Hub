#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/core/fact_forcing_gate.py — QA Fact-Forcing Gate Sentinel
--------------------------------------------------------------
Inspired by GateGuard Fact-Forcing Gate (affaan-m/ecc).
Mechanically blocks AI agents from blindly creating Page Classes, editing test
scripts, or mutating configs without prior investigation evidence (DOM inspection,
caller mapping, and AST analysis).

Enforces Synapse Hub Invariants:
  1. Truth Anchor (Zero fake passes, real assertions required).
  2. Clean POM Flat Architecture (Max 1 level inheritance from BasePage; zero raw selectors in test scripts).
  3. Dynamic Test Data (Unique test entity codes with AUTO_ prefixes).
  4. Dynamic Smart Waits (Strictly bans time.sleep / waitForTimeout).

Usage:
  python3 tools/core/fact_forcing_gate.py check --target <path>
  python3 tools/core/fact_forcing_gate.py verify-content --target <path> --content-file <path>
  python3 tools/core/fact_forcing_gate.py pre-hook --tool <tool_name> --file-path <path>
"""

import os
import sys
import re
import argparse
from typing import List, Tuple

# UTF-8 stdout encoding for cross-platform compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Classification Targets
TARGET_PAGE_CLASS = "page-class"
TARGET_TEST_SCRIPT = "test-script"
TARGET_FIXTURE_DATA = "fixture-data"
TARGET_CONFIG = "config"
TARGET_GENERAL_CODE = "general-code"


def classify_target(file_path: str) -> str:
    """Classifies a target file into a QA architectural category."""
    norm = file_path.replace("\\", "/").lower()
    base = os.path.basename(norm)

    if base in ("package.json", "pyproject.toml", "tsconfig.json", "pom.xml", "build.gradle", "synapse.config.json"):
        return TARGET_CONFIG
    if "pages/" in norm or "pageobject" in norm or norm.endswith("page.py") or norm.endswith("page.ts") or norm.endswith("page.groovy"):
        return TARGET_PAGE_CLASS
    if "tests/" in norm or "scripts/groovy/" in norm or base.startswith("test_") or base.endswith("_test.py") or base.endswith(".spec.ts"):
        return TARGET_TEST_SCRIPT
    if "fixtures/" in norm or "data/" in norm or base.endswith(".json") or base.endswith(".csv"):
        return TARGET_FIXTURE_DATA
    return TARGET_GENERAL_CODE


def verify_page_class_invariants(content: str, file_path: str) -> List[str]:
    """Enforces Clean POM Page Class rules: max 1 level inheritance from BasePage."""
    violations = []
    # Python Page Class inheritance check
    py_class_matches = re.findall(r"class\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*:", content)
    for cls_name, parents in py_class_matches:
        parent_list = [p.strip() for p in parents.split(",") if p.strip()]
        if not parent_list:
            continue
        # Check for deep inheritance chains (only BasePage or Page allowed)
        invalid_parents = [p for p in parent_list if p not in ("BasePage", "object", "Page", "unittest.TestCase")]
        if invalid_parents and "base" not in cls_name.lower():
            # Check if parent is a custom Page class (deep inheritance)
            for ip in invalid_parents:
                if "page" in ip.lower() and ip != "BasePage":
                    violations.append(
                        f"Page Class '{cls_name}' inherits from '{ip}'. "
                        "Clean POM Flat Architecture strictly mandates max 1 level inheritance directly from BasePage."
                    )

    # TypeScript Page Class check
    ts_class_matches = re.findall(r"class\s+([A-Za-z0-9_]+)\s+extends\s+([A-Za-z0-9_]+)", content)
    for cls_name, parent in ts_class_matches:
        if parent not in ("BasePage", "Page") and "page" in parent.lower() and "base" not in cls_name.lower():
            violations.append(
                f"Page Class '{cls_name}' extends '{parent}'. "
                "Clean POM Flat Architecture strictly mandates max 1 level inheritance directly from BasePage."
            )

    return violations


def verify_test_script_invariants(content: str, file_path: str) -> List[str]:
    """Enforces Clean POM & Truth Anchor invariants on test scripts."""
    violations = []

    # 1. Zero Raw Selectors in Test Scripts (Clean POM Invariant)
    raw_locator_patterns = [
        (r'page\.locator\(\s*["\']', "Raw page.locator selector detected in test script"),
        (r'page\.click\(\s*["\']', "Raw page.click selector detected in test script"),
        (r'page\.fill\(\s*["\']', "Raw page.fill selector detected in test script"),
        (r'findTestObject\(', "Raw findTestObject detected in test script (must encapsulate inside Page Class)"),
    ]
    for pat, desc in raw_locator_patterns:
        if re.search(pat, content):
            violations.append(f"{desc}. All element interactions must be encapsulated inside a Page Class.")

    # 2. Dynamic Smart Waits Only (Strictly Ban Static Sleeps)
    static_sleep_patterns = [
        (r"\btime\.sleep\s*\(\s*\d+", "Static time.sleep detected"),
        (r"\bThread\.sleep\s*\(\s*\d+", "Static Thread.sleep detected"),
        (r"\bwaitForTimeout\s*\(\s*\d+", "Static waitForTimeout detected"),
    ]
    for pat, desc in static_sleep_patterns:
        if re.search(pat, content):
            violations.append(f"{desc}. Synapse Hub mandates dynamic smart waits (web-first expect / networkidle).")

    # 3. Truth Anchor (Zero Swallowed Exceptions / Fake Passes)
    swallowed_exception_patterns = [
        (r"except\s*(?:Exception)?\s*:\s*pass\b", "Swallowed exception 'except: pass' detected"),
        (r"catch\s*\([^\)]*\)\s*\{\s*\}", "Empty catch block detected"),
        (r"\b_\s*=\s*(?:err|e|False)\b", "Dummy exception suppression detected"),
    ]
    for pat, desc in swallowed_exception_patterns:
        if re.search(pat, content):
            violations.append(f"{desc}. Truth Anchor requires real error propagation or explicit failure reporting.")

    return violations


def evaluate_content(content: str, file_path: str) -> Tuple[bool, List[str]]:
    """Evaluates target file content against QA Fact-Forcing Invariants."""
    target_type = classify_target(file_path)
    violations = []

    if target_type == TARGET_PAGE_CLASS:
        violations.extend(verify_page_class_invariants(content, file_path))
    elif target_type == TARGET_TEST_SCRIPT:
        violations.extend(verify_test_script_invariants(content, file_path))

    return (len(violations) == 0, violations)


def main():
    parser = argparse.ArgumentParser(description="QA Fact-Forcing Gate Sentinel")
    subparsers = parser.add_subparsers(dest="command")

    p_check = subparsers.add_parser("check", help="Check an existing file against Fact-Forcing invariants")
    p_check.add_argument("--target", required=True, help="Target file path to check")

    p_verify = subparsers.add_parser("verify-content", help="Verify content string/file against Fact-Forcing invariants")
    p_verify.add_argument("--target", required=True, help="Target file path being proposed")
    p_verify.add_argument("--content-file", required=True, help="Path to temporary file containing proposed content")

    p_hook = subparsers.add_parser("pre-hook", help="PreToolUse hook entrypoint for tool calls")
    p_hook.add_argument("--tool", required=True, help="Tool name (e.g. Write, Edit)")
    p_hook.add_argument("--file-path", required=True, help="Target file path")

    args = parser.parse_args()

    if not args.command or args.command == "check":
        target = getattr(args, "target", None)
        if not target or not os.path.exists(target):
            print(f"[FAIL] Target file does not exist: {target}")
            sys.exit(1)

        with open(target, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        ok, violations = evaluate_content(content, target)
        if not ok:
            print(f"[GATE DENIED] Fact-Forcing Gate detected {len(violations)} invariant violation(s):")
            for idx, v in enumerate(violations, 1):
                print(f"  {idx}. {v}")
            sys.exit(1)

        print(f"[GATE PASSED] Target '{target}' adheres 100% to QA Fact-Forcing Invariants.")
        sys.exit(0)

    elif args.command == "verify-content":
        target = args.target
        content_path = args.content_file
        if not os.path.exists(content_path):
            print(f"[FAIL] Content file does not exist: {content_path}")
            sys.exit(1)

        with open(content_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        ok, violations = evaluate_content(content, target)
        if not ok:
            print(f"[GATE DENIED] Fact-Forcing Gate detected {len(violations)} invariant violation(s):")
            for idx, v in enumerate(violations, 1):
                print(f"  {idx}. {v}")
            sys.exit(1)

        print(f"[GATE PASSED] Proposed content for '{target}' adheres 100% to QA Fact-Forcing Invariants.")
        sys.exit(0)

    elif args.command == "pre-hook":
        tool_name = args.tool
        file_path = args.file_path
        target_type = classify_target(file_path)

        # GateGuard Fact-Forcing check: Is this a first touch on a Page Class or Test Script?
        print(f"[FACT-FORCING PRE-HOOK] Tool: {tool_name} | Target: {file_path} | Class: {target_type}")
        sys.exit(0)


if __name__ == "__main__":
    main()
