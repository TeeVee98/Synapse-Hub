#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Gate 3: Clean POM & Flat Architecture Sentinel.
Enforces Clean Page Object Model by rejecting raw selectors in test scripts.
"""

import glob
import os
import re
import sys
from typing import List, Tuple

_GATES_DIR = os.path.dirname(os.path.abspath(__file__))
_CORE_DIR = os.path.dirname(_GATES_DIR)
_TOOLS_ROOT = os.path.dirname(_CORE_DIR)
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)

for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.core.gates.base import (
    BaseGate,
    detect_repo_mode,
    is_page_class_path,
)


def gate_3_clean_pom(repo_root: str, mode: str = "AUTO") -> bool:
    """Gate 3: Enforces Clean Page Object Model by rejecting raw selectors in test scripts."""
    print("\n[GATE 3] Checking Clean POM & Flat Architecture in Test Scripts...")
    effective_mode = (detect_repo_mode(repo_root) if mode.upper() == "AUTO" else mode).upper()
    if effective_mode == "HUB":
        examples_dir = os.path.join(repo_root, "examples")
        if os.path.isdir(examples_dir):
            print("[HUB MODE] Verifying Clean POM across reference example suites (examples/)...")
            test_dirs = ["examples"]
        else:
            print("[N/A] Hub Mode: Not Applicable (Clean POM rules apply to target test suites in Spokes).")
            return True
    else:
        test_dirs = ["Scripts", "tests", "test", "e2e", "specs", "cypress"]

    test_files: List[str] = []
    for td in test_dirs:
        d = os.path.join(repo_root, td)
        if os.path.isdir(d):
            for ext in ("*.groovy", "*.ts", "*.js", "*.py", "*.java"):
                test_files.extend(glob.glob(os.path.join(d, "**", ext), recursive=True))

    if not test_files:
        print("[N/A] No test scripts present in candidate directories (Scripts/, tests/, e2e/).")
        return True

    locator_call_pattern = re.compile(
        r'(?:\.(?:click|dblclick|fill|type|press|check|locator|waitForSelector|hover|selectOption)|cy\.(?:get|find)|driver\.find[A-Za-z]*|WebUI\.[a-zA-Z]+)\s*\(\s*[\x22\x27`](?P<sel>[^\x22\x27`]+)[\x22\x27`]'
    )
    raw_xpath_pattern = re.compile(r'[\x22\x27`](?:xpath=|\/{2}[a-zA-Z*@\[])[^\x22\x27`]*[\x22\x27`]')
    semantic_locator_pattern = re.compile(
        r'(?:page|frame)\.(?:getByRole|getByLabel|getByPlaceholder|getByText|getByTestId|getByAltText|getByTitle)\s*\('
    )

    allow_semantic_locators = os.environ.get("SYNAPSE_ALLOW_SEMANTIC_LOCATORS", "0").lower() in ("1", "true", "yes")

    violations: List[Tuple[str, int, str]] = []
    for full_path in sorted(set(test_files)):
        rel_path = os.path.relpath(full_path, repo_root)
        parts = rel_path.replace("\\", "/").split("/")
        if any(p in ("node_modules", ".git", "playwright-report", "dist", "build", ".gradle", "test-results") for p in parts):
            continue
        if is_page_class_path(rel_path):
            continue
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                for line_no, line in enumerate(fp, 1):
                    stripped = line.strip()
                    if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("#"):
                        continue
                    # Inline escape hatch: honor gate3-allow-inline comment
                    if "gate3-allow-inline" in stripped:
                        continue
                    # Ignore standard navigation statements to prevent false-positive XPath violations on URLs
                    if re.search(r'\.(?:goto|get|open|navigate)\s*\(\s*[\x22\x27]https?:\/\/', stripped):
                        continue
                    if "findTestObject" in line:
                        violations.append((rel_path, line_no, "Raw findTestObject"))
                        continue
                    # Check Playwright semantic locators in test script (unless opt-in configuration enabled)
                    if not allow_semantic_locators and semantic_locator_pattern.search(stripped):
                        violations.append((rel_path, line_no, f"Raw Playwright semantic locator in Test Script: '{stripped}'"))
                        continue
                    # Check locator calls taking raw CSS/XPath selectors
                    m = locator_call_pattern.search(stripped)
                    if m:
                        sel = m.group("sel").strip()
                        matched_call = m.group(0)
                        is_explicit_locator = any(k in matched_call for k in ('.locator', 'cy.get', 'cy.find', 'driver.find', 'waitForSelector'))
                        is_selector = any(sel.startswith(p) for p in ('.', '#', '//', 'xpath=', '[')) or ' > ' in sel or ', ' in sel or bool(re.match(r'^(?:a|div|span|button|input|li|ul|ol|table|tr|td|th|select|p|h[1-6])[\.#:\[\s,]', sel))
                        if is_explicit_locator or is_selector:
                            violations.append((rel_path, line_no, f"Raw CSS/XPath Selector in Test Script: '{sel}'"))
                            continue
                    if raw_xpath_pattern.search(stripped):
                        violations.append((rel_path, line_no, "Raw XPath literal in Test Script"))
        except (OSError, PermissionError):
            continue

    if violations:
        print(f"[FAIL] {len(violations)} Clean POM violations in test scripts:")
        for rel_path, line_no, reason in violations:
            print(f"   - {rel_path}:{line_no} ({reason})")
        return False
    print("[PASS] 100% Clean POM compliance (all locators encapsulated in Page Classes).")
    return True


class Gate03CleanPOM(BaseGate):
    """Gate 3: Clean POM & Flat Architecture Sentinel."""

    gate_id = 3
    name = "Gate 3: Clean POM & Flat Architecture"
    key = "gate_3_clean_pom"

    def run(self, repo_root: str, mode: str = "AUTO", **kwargs) -> bool:
        return gate_3_clean_pom(repo_root, mode=mode)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Gate 3: Clean POM Sentinel")
    parser.add_argument("--mode", default="hub", choices=["hub", "target", "AUTO"])
    parser.add_argument("repo_root", nargs="?", default=_REPO_ROOT)
    args = parser.parse_args()
    ok = gate_3_clean_pom(args.repo_root, mode=args.mode)
    sys.exit(0 if ok else 1)
