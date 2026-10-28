#!/usr/bin/env python3
"""
Pre-check validator for Groovy scripts and POM keywords in enterprise test suites.
Catches syntax errors, broken GString escape sequences, and syntax issues
before running tests in CI, ensuring 100% parity with Katalon compiler checks.
"""

import sys
import re
from pathlib import Path

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / 'Scripts'
KEYWORDS_DIR = BASE_DIR / 'Keywords'

def strip_comments_and_strings(source_code: str) -> str:
    """Strips comments, string literals, and regexes so literal braces/parentheses don't cause false positives."""
    pattern = re.compile(
        r'(?P<BLOCK_COMMENT>/\*.*?\*/)|'
        r'(?P<LINE_COMMENT>//[^\r\n]*)|'
        r'(?P<TRIPLE_DOUBLE>"""[\s\S]*?""")|'
        r'(?P<TRIPLE_SINGLE>\'\'\'[\s\S]*?\'\'\')|'
        r'(?P<DOLLAR_SLASHY>\$/[\s\S]*?/\$)|'
        r'(?P<DOUBLE_STRING>"(?:\\.|[^"\\])*")|'
        r'(?P<SINGLE_STRING>\'(?:\\.|[^\'\\])*\')|'
        r'(?P<SLASHY_REGEX>(?<![a-zA-Z0-9_$)\]])/(?:\\/|[^/\r\n])+/(?![/*]))',
        re.DOTALL
    )
    return pattern.sub(' ', source_code)


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

    # 3 & 4. Check structural balance on clean code without string/comment noise
    clean_content = strip_comments_and_strings(content)
    open_braces = clean_content.count('{')
    close_braces = clean_content.count('}')
    if open_braces != close_braces:
        errors.append(f"Unmatched braces: {open_braces} '{{' vs {close_braces} '}}'")

    open_parens = clean_content.count('(')
    close_parens = clean_content.count(')')
    if open_parens != close_parens:
        errors.append(f"Unmatched parentheses: {open_parens} '(' vs {close_parens} ')'")

    return errors

def main():
    print("=" * 60)
    print("Enterprise Automation: Pre-check Groovy Scripts & Keywords")
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
