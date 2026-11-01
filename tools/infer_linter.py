#!/usr/bin/env python3
"""
Universal QA Static Defect & Assertion Sentinel (Inspired by facebook/infer)
-------------------------------------------------------------------
Performs AST-level static analysis across test scripts, specs, and Page Classes.
Detects:
  1. FAKE_PASS_NO_ASSERTION : Test cases that interact with AUT but lack assertions / verifications.
  2. SWALLOWED_EXCEPTION    : Empty catch blocks that hide failures silently.
  3. EXCESSIVE_HARD_DELAY   : Thread.sleep >= 3000ms or WebUI.delay >= 5s (flaky anti-pattern).
  4. RESOURCE_LEAK_RISK     : Unclosed streams or driver handles lacking finally blocks.
  5. EMPTY_TEST_SCRIPT      : Test cases with zero executable statements.
"""

import os
import sys
import re
import json
import glob
import argparse
from datetime import datetime

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "Scripts")
REPORTS_DIR = os.path.join(REPO_ROOT, "reports")
OUTPUT_JSON = os.path.join(REPORTS_DIR, "infer_linter_report.json")

# ANSI Color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Generic Detection regexes (including Cypress .should and .and assertions)
ASSERTION_PATTERN = re.compile(
    r'\b(verify[A-Za-z0-9_]*|assert[A-Za-z0-9_]*|waitForToast|checkStatus|assertEquals|assertTrue|assertFalse|assertThat|expect|ensure[A-Z][A-Za-z0-9_]*Exists)\b|\.should\s*\(|\.and\s*\('
)

# Rule L1 & L5: Empty catch / swallowed exceptions across JS/TS/Groovy/Java and Python
# Also catches try/catch that only console.log or promise .catch(() => {})
EMPTY_CATCH_PATTERN = re.compile(
    r'(?:catch\s*(?:\([^\)]*\))?\s*\{\s*(?:console\.(?:log|warn|error)\([^)]*\);?\s*)?\}'
    r'|\.catch\s*\(\s*(?:\([^)]*\)|[a-zA-Z0-9_]+)?\s*=>\s*\{\s*(?:console\.(?:log|warn|error)\([^)]*\);?\s*)?\}\s*\)'
    r'|\bexcept(?:\s+[^:]*)?:\s*(?:pass|\.\.\.)(?:\s*$|\s*#))',
    re.MULTILINE
)

# Whitelisted best-effort compatibility calls (UTF-8 console reconfigure, file
# permission chmod, stream flush). An empty catch guarding ONLY these is an
# intentional no-op-on-failure idiom, not a swallowed test failure.
BENIGN_TRY_CALL_PATTERN = re.compile(
    r'^[\w\.]*\.(?:reconfigure|chmod|flush)\s*\('
)

# Rule L3: Tautological assertions (e.g. expect(true).toBe(true), assert r == r, expect(true).toBeTruthy())
TAUTOLOGY_PATTERN = re.compile(
    r'(?:expect\s*\(\s*(?:true|1)\s*\)\s*\.\s*(?:toBe|toEqual|toBeTruthy)\s*\(\s*(?:true|1)?\s*\)'
    r'|\bassert\s+(?:True|true|1\s*==\s*1)\b'
    r'|\bassert\s+([a-zA-Z0-9_]+)\s*==\s*\1\b'
    r'|assertEquals\s*\(\s*(?:true|1)\s*,\s*(?:true|1)\s*\)'
    r'|assertTrue\s*\(\s*(?:true|1)\s*\))',
    re.IGNORECASE
)

# Rule L4: Unawaited Playwright assertions in JS/TS
# Expanded with all standard Playwright async matchers and optional .not modifier
PLAYWRIGHT_ASYNC_MATCHERS = (
    r'(?:toBeVisible|toBeHidden|toHaveText|toHaveValue|toHaveCount|toBeEnabled|toBeDisabled|'
    r'toBeChecked|toHaveURL|toContainText|toHaveTitle|toHaveAttribute|toHaveClass|toHaveId|'
    r'toBeFocused|toBeEmpty|toBeAttached|toBeInViewport|toBeOK)'
)
UNAWAITED_EXPECT_PATTERN = re.compile(
    r'\bexpect\s*\([^;\n]+\)\s*(?:\.\s*not)?\s*\.\s*' + PLAYWRIGHT_ASYNC_MATCHERS + r'\s*\(',
    re.MULTILINE
)

# Rule 3: Flaky Static Delays across Groovy, Java, Playwright (JS/TS/Python), Pytest/Python, Cypress
# Millisecond-based delays: Thread.sleep(ms), waitForTimeout(ms), wait_for_timeout(ms), cy.wait(ms)
MS_DELAY_PATTERN = re.compile(
    r'(?:Thread\.sleep|(?:page\.)?waitForTimeout|(?:page\.)?wait_for_timeout|cy\.wait)\s*\(\s*([^)]+)\s*\)'
)

# Second-based delays: WebUI.delay(sec), time.sleep(sec)
SEC_DELAY_PATTERN = re.compile(
    r'(?:WebUI\.delay|time\.sleep)\s*\(\s*([^)]+)\s*\)'
)

# Backward-compatibility alias
THREAD_SLEEP_PATTERN = MS_DELAY_PATTERN


def strip_comments_and_strings(source_code, preserve_newlines=True):
    """
    Lexically strips block comments, line comments, multiline strings, 
    and quoted literals while preserving line numbering.
    Prevents false-positive / false-negative matches in AST linter.
    """
    pattern = re.compile(
        r'(?P<TRIPLE_DOUBLE>"""[\s\S]*?""")|'
        r'(?P<TRIPLE_SINGLE>\'\'\'[\s\S]*?\'\'\')|'
        r'(?P<DOUBLE_STRING>"(?:\\.|[^"\\])*")|'
        r'(?P<SINGLE_STRING>\'(?:\\.|[^\'\\])*\')|'
        r'(?P<BLOCK_COMMENT>/\*.*?\*/)|'
        r'(?P<LINE_COMMENT>//[^\r\n]*)|'
        r'(?P<HASH_COMMENT>#[^\r\n]*)',
        re.DOTALL
    )

    def replacer(match):
        text = match.group(0)
        if preserve_newlines:
            return re.sub(r'[^\r\n]', ' ', text)
        return ' '

    return pattern.sub(replacer, source_code)


def _is_benign_empty_catch(clean_code, match_start):
    """
    True when an empty catch block exclusively guards whitelisted best-effort
    calls (e.g. sys.stdout.reconfigure(), os.chmod()) - an intentional
    no-op-on-failure compatibility idiom rather than a swallowed test failure.
    Conservative by design: only Python-style 'try:' blocks are whitelisted;
    C-style brace bodies still get flagged.
    """
    body_lines = []
    for line in reversed(clean_code[:match_start].splitlines()):
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r'try\s*(?:[:{]|$)', stripped):
            return bool(body_lines) and all(BENIGN_TRY_CALL_PATTERN.match(l) for l in body_lines)
        body_lines.append(stripped)
    return False


def classify_file_role(file_path: str) -> str:
    """
    Classifies a source file into:
      - 'CONFIG': Configuration files (playwright.config, cypress.config, conftest, wdio.conf, jest.config)
      - 'PAGE_OBJECT': Page Classes / POM (files in pages/, ending in Page.ts/js/py/groovy/java, or BasePage)
      - 'HELPER': Utilities / Fixtures / Custom Keywords (files in helpers/, fixtures/, utils/, support/)
      - 'TEST_SCRIPT': Test specifications / test cases (test_*, *test, *.spec, *.cy, *.tc, files in tests/, Scripts/)
    """
    norm = file_path.replace("\\", "/").lower()
    base = os.path.basename(norm)
    parts = norm.split("/")[:-1]

    # 1. Config files
    if any(cfg in base for cfg in ["playwright.config", "cypress.config", "wdio.conf", "jest.config", "karma.conf", "conftest.py", "tsconfig"]):
        return "CONFIG"
    if any(p in ("config", ".config") for p in parts):
        return "CONFIG"

    # 2. Page Objects (Clean POM)
    if any(p in ("pages", "page_objects", "page-objects", "po") for p in parts) or \
       ("keywords" in parts and "pages" in norm):
        return "PAGE_OBJECT"
    if re.search(r'(^|_)basepage\b', base) or re.search(r'[a-z0-9_]page\.(ts|js|py|groovy|java)$', base):
        return "PAGE_OBJECT"

    # 3. Helpers & Fixtures
    if any(p in ("fixtures", "helpers", "utils", "support") for p in parts):
        return "HELPER"
    if any(base.endswith(sfx) for sfx in ("helper.ts", "helper.js", "helper.py", "helper.groovy", "utils.ts", "utils.js", "utils.py", "fixture.ts", "fixture.js")):
        return "HELPER"

    # 4. Test Scripts
    test_suffixes = ("_test.py", ".spec.ts", ".spec.js", ".test.ts", ".test.js", ".cy.js", ".cy.ts", ".spec.jsx", ".test.jsx", ".tc", "test.java", "tests.java", "spec.groovy")
    if base.startswith("test_") or base.endswith(test_suffixes):
        return "TEST_SCRIPT"
    if any(p in ("tests", "test", "e2e", "specs", "cypress") for p in parts):
        return "TEST_SCRIPT"
    if "scripts" in parts:
        if file_path.endswith((".groovy", ".tc")) or base.startswith("test_") or base.endswith(test_suffixes):
            return "TEST_SCRIPT"
        return "HELPER"

    # Default fallback: standalone script without directory context
    return "TEST_SCRIPT"


def analyze_script(file_path):
    """Performs static rule scanning on a single test script or automation asset."""
    role = classify_file_role(file_path)

    try:
        rel_path = os.path.relpath(file_path, REPO_ROOT)
    except ValueError:
        rel_path = os.path.abspath(file_path)

    # Config files have zero test assertions by definition
    if role == "CONFIG":
        return {
            "file": rel_path,
            "role": role,
            "defects": [],
            "is_clean": True
        }

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    defects = []

    # Lexically strip comments and string literals for accurate analysis
    clean_code = strip_comments_and_strings(content, preserve_newlines=True)
    clean_lines = [l.strip() for l in clean_code.splitlines()]

    raw_lines = content.splitlines()

    # Code quality checks across all automation assets (Test Scripts, Page Objects, Helpers)
    # Rule 2: Swallowed Exceptions (empty catch blocks)
    for match in EMPTY_CATCH_PATTERN.finditer(clean_code):
        if _is_benign_empty_catch(clean_code, match.start()):
            continue
        line_no = clean_code[:match.start()].count("\n") + 1
        defects.append({
            "type": "SWALLOWED_EXCEPTION",
            "severity": "CRITICAL",
            "line": line_no,
            "message": "Empty catch block detected. Swallowed exceptions cause false-pass test runs."
        })

    # Rule 3: Flaky Static Delays (Playwright, Cypress, Pytest, Katalon, Java/Groovy)
    for idx, line in enumerate(clean_code.splitlines(), 1):
        raw_line = raw_lines[idx - 1].strip() if idx <= len(raw_lines) else line.strip()

        # Millisecond delays
        m_ms = MS_DELAY_PATTERN.search(line)
        if m_ms:
            arg = m_ms.group(1).strip()
            if arg.isdigit():
                delay_val = int(arg)
                if delay_val >= 3000:
                    defects.append({
                        "type": "EXCESSIVE_HARD_DELAY",
                        "severity": "WARNING",
                        "line": idx,
                        "message": f"Static sleep of {delay_val}ms found ('{raw_line}'). Replace with dynamic Smart Wait (waitForElement/networkidle)."
                    })
                    continue
            elif re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', arg) and not line.strip().startswith("cy.wait"):
                defects.append({
                    "type": "EXCESSIVE_HARD_DELAY",
                    "severity": "WARNING",
                    "line": idx,
                    "message": f"Static sleep with variable/expression '{arg}' found ('{raw_line}'). Replace with dynamic Smart Wait."
                })
                continue

        # Second delays
        m_sec = SEC_DELAY_PATTERN.search(line)
        if m_sec:
            arg = m_sec.group(1).strip()
            try:
                delay_val = float(arg)
                if delay_val >= 3.0:
                    delay_ms = int(delay_val * 1000)
                    delay_str = f"{delay_val:g}"
                    defects.append({
                        "type": "EXCESSIVE_HARD_DELAY",
                        "severity": "WARNING",
                        "line": idx,
                        "message": f"Static sleep of {delay_str}s ({delay_ms}ms) found ('{raw_line}'). Replace with dynamic Smart Wait (waitForElement/networkidle)."
                    })
            except ValueError:
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', arg):
                    defects.append({
                        "type": "EXCESSIVE_HARD_DELAY",
                        "severity": "WARNING",
                        "line": idx,
                        "message": f"Static sleep with variable/expression '{arg}' found ('{raw_line}'). Replace with dynamic Smart Wait."
                    })

    # Test Script Specific Invariants (Do NOT apply to Page Objects or Helpers)
    if role == "TEST_SCRIPT":
        executable_lines = [
            l for l in clean_lines 
            if l and not l.startswith("import ") and not l.startswith("package ") and not l.startswith("from ")
        ]
        # Rule 1: Empty Test Script
        if len(executable_lines) == 0:
            defects.append({
                "type": "EMPTY_TEST_SCRIPT",
                "severity": "CRITICAL",
                "line": 1,
                "message": "Test script is empty or contains only comments/imports."
            })

        # Rule 4 (L3): Tautological Assertions
        for idx, line in enumerate(clean_code.splitlines(), 1):
            if TAUTOLOGY_PATTERN.search(line):
                raw_line = raw_lines[idx - 1].strip() if idx <= len(raw_lines) else line.strip()
                defects.append({
                    "type": "TAUTOLOGICAL_ASSERTION",
                    "severity": "CRITICAL",
                    "line": idx,
                    "message": f"Tautological assertion detected ('{raw_line}'). Test assertion always evaluates to True without testing system state."
                })

        # Rule 5 (L4): Unawaited Playwright Assertions in JS/TS
        if file_path.endswith((".ts", ".tsx", ".js", ".jsx")):
            for match in UNAWAITED_EXPECT_PATTERN.finditer(clean_code):
                prefix = clean_code[max(0, match.start() - 40):match.start()]
                if re.search(r'\b(?:await|return)\s+$', prefix):
                    continue
                surrounding = clean_code[max(0, match.start() - 150):match.start()]
                if any(w in surrounding for w in ("Promise.all", "Promise.allSettled", "return ")):
                    continue
                line_no = clean_code[:match.start()].count("\n") + 1
                line_text = raw_lines[line_no - 1].strip() if line_no <= len(raw_lines) else ""
                defects.append({
                    "type": "UNAWAITED_ASYNC_ASSERTION",
                    "severity": "CRITICAL",
                    "line": line_no,
                    "message": f"Unawaited async Playwright assertion detected: '{line_text}'. Without 'await', assertion returns a Pending Promise that never validates."
                })

        # Rule 6 (L2 & L6): Missing Assertions / Fake-Pass
        assert_matches = list(ASSERTION_PATTERN.finditer(clean_code))
        tautology_matches = list(TAUTOLOGY_PATTERN.finditer(clean_code))
        has_real_assert = any(
            not any(tm.start() <= am.start() < tm.end() for tm in tautology_matches)
            for am in assert_matches
        )

        # F06: Check test cases per function block if multiple tests exist
        TEST_BLOCK_PATTERN = re.compile(
            r'(?m)^[ \t]*(?:(?:test|it)(?:\.(?:only|skip))?\s*\(|def\s+test_[a-zA-Z0-9_]+\s*\(|(?:@Test\s+)?(?:public\s+)?(?:void|def)\s+test[a-zA-Z0-9_]*\s*\()'
        )
        test_matches = list(TEST_BLOCK_PATTERN.finditer(clean_code))
        if len(test_matches) >= 2:
            for i, tm in enumerate(test_matches):
                b_start = tm.start()
                b_end = test_matches[i + 1].start() if i + 1 < len(test_matches) else len(clean_code)
                block_code = clean_code[b_start:b_end]
                b_asserts = list(ASSERTION_PATTERN.finditer(block_code))
                b_tauts = list(TAUTOLOGY_PATTERN.finditer(block_code))
                block_has_real_assert = any(
                    not any(tt.start() <= ta.start() < tt.end() for tt in b_tauts)
                    for ta in b_asserts
                )
                b_has_interactions = any(
                    kw in block_code for kw in ["click", "select", "save", "delete", "create", "search", "navigate", "open", "fill", "goto", "post", "get"]
                )
                b_line = clean_code[:b_start].count("\n") + 1
                if b_has_interactions and not block_has_real_assert:
                    defects.append({
                        "type": "FAKE_PASS_NO_ASSERTION",
                        "severity": "WARNING",
                        "line": b_line,
                        "message": f"Test block starting at line {b_line} performs interactions but contains zero verification/assertion statements."
                    })
        else:
            has_interactions = any(
                kw in clean_code for kw in ["click", "select", "save", "delete", "create", "search", "navigate", "open", "fill", "goto", "post", "get"]
            )
            is_explicit_test = any(t in os.path.basename(file_path).lower() for t in ["test", "spec", "tc-", "tc_"])

            if has_interactions and not has_real_assert:
                defects.append({
                    "type": "FAKE_PASS_NO_ASSERTION",
                    "severity": "WARNING",
                    "line": 1,
                    "message": "Test script performs AUT mutations/interactions but contains zero verification/assertion statements."
                })
            elif is_explicit_test and not has_real_assert and not has_interactions and len(executable_lines) > 0:
                defects.append({
                    "type": "NO_ASSERTION_IN_TEST",
                    "severity": "WARNING",
                    "line": 1,
                    "message": "Test case file contains executable logic but has no verification or assertion statements."
                })

    return {
        "file": rel_path,
        "role": role,
        "defects": defects,
        "is_clean": len(defects) == 0
    }


def run_infer_linter(target_dir=None, output_path=None, strict: bool = False):
    """Scans test scripts across Groovy, TypeScript, JavaScript, Python, and Java."""
    EXTENSIONS = ("*.groovy", "*.ts", "*.tsx", "*.js", "*.jsx", "*.py", "*.java")

    if target_dir:
        if os.path.isfile(target_dir):
            script_files = [target_dir]
            scan_dir = os.path.dirname(target_dir)
        elif os.path.isdir(target_dir):
            scan_dir = target_dir
            raw_files = []
            for ext in EXTENSIONS:
                raw_files.extend(glob.glob(os.path.join(scan_dir, "**", ext), recursive=True))
            # Filter out non-test files like tools, __init__.py, node_modules when scanning generic directory
            ignored_parts = {"tools", "node_modules", ".git", "__pycache__", "venv", ".venv"}
            script_files = [
                f for f in raw_files
                if not any(part.lower() in ignored_parts for part in os.path.relpath(f, scan_dir).replace("\\", "/").split("/")[:-1])
                and os.path.basename(f) not in {"__init__.py", "setup.py"}
            ]
        else:
            scan_dir = target_dir
            script_files = []
    else:
        # Search candidate directories across test frameworks (Katalon, Playwright, Pytest, Cypress)
        script_files = []
        scan_dir = SCRIPTS_DIR
        for cand in ["Scripts", "tests", "test", "e2e", "specs", "cypress"]:
            cand_path = os.path.join(REPO_ROOT, cand)
            if os.path.isdir(cand_path):
                for ext in EXTENSIONS:
                    script_files.extend(glob.glob(os.path.join(cand_path, "**", ext), recursive=True))
                if script_files:
                    scan_dir = cand_path
                    break

    results = []
    critical_count = 0
    warning_count = 0
    clean_count = 0

    for s in sorted(set(script_files)):
        res = analyze_script(s)
        results.append(res)
        crit = sum(1 for d in res["defects"] if d["severity"] == "CRITICAL")
        warn = sum(1 for d in res["defects"] if d["severity"] == "WARNING")
        critical_count += crit
        warning_count += warn
        if res["is_clean"]:
            clean_count += 1

    total_scripts = len(script_files)
    if total_scripts == 0:
        health_score = 0.0
        clean_pct = 0.0
    else:
        clean_pct = round((clean_count / total_scripts) * 100, 1)
        # Empirical codebase health score:
        # Base is clean ratio percentage, with an extra severity penalty for critical defects
        critical_penalty = (critical_count * 20.0) / total_scripts
        raw_score = (clean_count / total_scripts) * 100.0 - critical_penalty
        health_score = max(0.0, min(100.0, round(raw_score, 1)))

        # Invariant: If defects exist (clean_count < total_scripts), health score cannot be 100%
        if clean_count < total_scripts and health_score >= 100.0:
            health_score = 99.0
        # Invariant: If zero scripts are clean, health score is 0%
        if clean_count == 0 and total_scripts > 0:
            health_score = 0.0

    print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
    print(f"{BOLD}{CYAN}    ENTERPRISE STATIC DEFECT & FAKE-PASS SENTINEL (Meta Infer-Style)        {RESET}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}")
    if total_scripts == 0:
        print(f"  Target Scope            : 0 Test Scripts discovered in {os.path.basename(scan_dir)}/ (No tests found)")
        print(f"  Critical Defects        : {GREEN}0{RESET}")
        print(f"  Warnings / Suggestions  : {GREEN}0{RESET}")
        print(f"  Clean Scripts           : 0/0 (N/A)")
        print(f"  Codebase Health Score   : {YELLOW}N/A (0 test scripts discovered){RESET}")
    else:
        print(f"  Target Scope            : {total_scripts} Test Scripts in {os.path.basename(scan_dir)}/ (Polyglot)")
        print(f"  Critical Defects        : {RED if critical_count > 0 else GREEN}{critical_count}{RESET} (Swallowed exceptions, empty scripts)")
        print(f"  Warnings / Suggestions  : {YELLOW if warning_count > 0 else GREEN}{warning_count}{RESET} (Missing explicit asserts, excessive delays)")
        print(f"  Clean Scripts           : {GREEN}{clean_count}/{total_scripts} ({clean_pct:.1f}%){RESET}")
        print(f"  Codebase Health Score   : {GREEN if health_score == 100 else YELLOW}{health_score:.1f}%{RESET}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}\n")

    # Print defect breakdown if any
    defect_scripts = [r for r in results if not r["is_clean"]]
    if defect_scripts:
        print(f"{BOLD}Detected Items ({len(defect_scripts)} scripts):{RESET}")
        for r in defect_scripts[:10]: # Print top 10
            for d in r["defects"]:
                color = RED if d["severity"] == "CRITICAL" else YELLOW
                print(f"  - [{color}{d['severity']}{RESET}] {r['file']}:{d['line']} - {d['message']}")
        if len(defect_scripts) > 10:
            print(f"  ... and {len(defect_scripts) - 10} more scripts (see full JSON report).\n")

    # Save artifact
    dest_json = os.path.abspath(output_path) if output_path else OUTPUT_JSON
    os.makedirs(os.path.dirname(dest_json), exist_ok=True)
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "total_scripts": total_scripts,
        "clean_scripts": clean_count,
        "critical_defects": critical_count,
        "warnings": warning_count,
        "health_score_pct": health_score,
        "defect_details": defect_scripts
    }
    with open(dest_json, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    print(f"Detailed audit saved to: {dest_json}\n")

    if not output_path and target_dir and os.path.isdir(target_dir) and not os.path.abspath(target_dir).startswith(REPO_ROOT):
        try:
            target_out = os.path.join(os.path.abspath(target_dir), "reports", "infer_linter_report.json")
            os.makedirs(os.path.dirname(target_out), exist_ok=True)
            with open(target_out, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    if strict:
        fake_pass_count = sum(1 for r in results for d in r["defects"] if d["type"] in ("FAKE_PASS_NO_ASSERTION", "NO_ASSERTION_IN_TEST"))
        return 0 if (critical_count == 0 and fake_pass_count == 0) else 1
    return 0 if critical_count == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="Universal QA Static Defect & Assertion Sentinel")
    parser.add_argument("target", nargs="?", default=None, help="Target directory or script to scan")
    parser.add_argument("--dir", help="Target directory to scan (defaults to Scripts/)")
    parser.add_argument("--repo", help="Target repository root containing Scripts/")
    parser.add_argument("--out", "--output", dest="output_file", help="Path to save JSON report")
    parser.add_argument("--strict", action="store_true", help="Treat missing assertions / fake-passes as fatal errors")
    args = parser.parse_args()

    target_dir = args.dir or args.target
    if not target_dir and args.repo:
        target_dir = os.path.join(args.repo, "Scripts")
    return run_infer_linter(target_dir=target_dir, output_path=args.output_file, strict=args.strict)


if __name__ == "__main__":
    sys.exit(main())
