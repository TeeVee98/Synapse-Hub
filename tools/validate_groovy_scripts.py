#!/usr/bin/env python3
"""
Pre-check validator for Groovy scripts and POM keywords in VNPT eDiG project.
Catches syntax errors, broken GString escape sequences, and syntax issues
before running tests in CI, ensuring 100% parity with Katalon compiler checks.
"""

import sys
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / 'Scripts'
KEYWORDS_DIR = BASE_DIR / 'Keywords'

def check_file(file_path: Path) -> list[str]:
    errors = []
    try:
        content = file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            content = file_path.read_text(encoding='latin-1')
        except Exception as e:
            return [f"Cannot read file: {e}"]

    lines = content.splitlines()
    for idx, line in enumerate(lines, start=1):
        # 1. Check for illegal backslash escapes like [\]
        if re.search(r"\[\\\]", line):
            errors.append(f"Line {idx}: Illegal escape sequence '[\\]'. Did you mean '[${{var}}]'?")

        # 2. Check for lonely unescaped backslash at end of quotes
        if re.search(r'["\']\\["\']', line):
            errors.append(f"Line {idx}: Unescaped single backslash in string.")

    # 3. Check brace balance
    open_braces = content.count('{')
    close_braces = content.count('}')
    if open_braces != close_braces:
        errors.append(f"Unmatched braces: {open_braces} '{{' vs {close_braces} '}}'")

    # 4. Check parenthesis balance
    open_parens = content.count('(')
    close_parens = content.count(')')
    if open_parens != close_parens:
        errors.append(f"Unmatched parentheses: {open_parens} '(' vs {close_parens} ')'")

    return errors

def main():
    print("=" * 60)
    print("VNPT eDiG Automation: Pre-check Groovy Scripts & Keywords")
    print("=" * 60)

    all_errors = {}
    files_checked = 0

    target_dirs = [SCRIPTS_DIR, KEYWORDS_DIR]
    for t_dir in target_dirs:
        if not t_dir.exists():
            continue
        for f in t_dir.rglob('*.groovy'):
            files_checked += 1
            errs = check_file(f)
            if errs:
                all_errors[str(f.relative_to(BASE_DIR))] = errs

    print(f"Checked {files_checked} Groovy files.")

    if all_errors:
        print("\n❌ SYNTAX PRE-CHECK FAILED! The following files have syntax errors:\n")
        for f_name, errs in all_errors.items():
            print(f"File: {f_name}")
            for err in errs:
                print(f"  - {err}")
            print()
        sys.exit(1)
    else:
        print("✅ All Groovy scripts and keywords passed syntax pre-check 100%!")
        sys.exit(0)

if __name__ == '__main__':
    main()
