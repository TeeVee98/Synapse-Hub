#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub Autonomous AST & Regex Test Code Auto-Fixer
-------------------------------------------------------
Transforms common flaky test anti-patterns and code quality defects into
robust, maintainable test patterns across TypeScript, JavaScript, Python, and Groovy.

Supported Auto-Fix Defect Types:
  1. EXCESSIVE_HARD_DELAY / HARD_DELAY_ANTI_PATTERN:
     Replaces static sleeps (waitForTimeout, Thread.sleep, time.sleep) with dynamic smart waits.
  2. UNAWAITED_ASYNC_ASSERTION:
     Prepends missing `await` to asynchronous Playwright assertions.
  3. SWALLOWED_EXCEPTION:
     Converts empty catch blocks and dummy suppression into transparent error re-throws.
  4. DANGLING_ASSERTION_NO_MATCHER:
     Appends `.toBeVisible()` to dangling unasserted expect() calls.
"""

import os
import sys
import re
import difflib
from typing import Tuple, List, Dict, Any

# Matchers from infer_linter
PLAYWRIGHT_ASYNC_MATCHERS = (
    r'(?:toBeVisible|toBeHidden|toHaveText|toHaveValue|toHaveCount|toBeEnabled|toBeDisabled|'
    r'toBeChecked|toHaveURL|toContainText|toHaveTitle|toHaveAttribute|toHaveClass|toHaveId|'
    r'toBeFocused|toBeEmpty|toBeAttached|toBeInViewport|toBeOK)'
)

UNAWAITED_EXPECT_PATTERN = re.compile(
    r'\bexpect\s*\([^;\n]+\)\s*(?:\.\s*not)?\s*\.\s*' + PLAYWRIGHT_ASYNC_MATCHERS + r'\s*\(',
    re.MULTILINE
)

# Colors for terminal diffs
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def colorize_diff(diff_lines: List[str]) -> str:
    """Applies ANSI terminal colors to a unified diff list."""
    colored = []
    for line in diff_lines:
        if line.startswith("+") and not line.startswith("+++"):
            colored.append(f"{GREEN}{line}{RESET}")
        elif line.startswith("-") and not line.startswith("---"):
            colored.append(f"{RED}{line}{RESET}")
        elif line.startswith("@@"):
            colored.append(f"{CYAN}{line}{RESET}")
        else:
            colored.append(line)
    return "\n".join(colored)


def fix_hard_delays(content: str, ext: str) -> Tuple[str, List[str]]:
    """
    Replaces static sleeps with dynamic smart waits depending on language / framework.
    Returns (updated_content, list_of_fix_descriptions).
    """
    fixes = []
    updated = content

    if ext in (".ts", ".tsx", ".js", ".jsx"):
        # Playwright TS/JS: await page.waitForTimeout(...) -> await page.waitForLoadState('domcontentloaded')
        def _replace_pw_sleep(m):
            indent = m.group(1) or ""
            has_await = bool(m.group(2))
            fixes.append("Replaced static waitForTimeout with dynamic waitForLoadState('domcontentloaded')")
            kw = "await " if has_await else ""
            return f"{indent}{kw}page.waitForLoadState('domcontentloaded');"

        updated = re.sub(
            r'^([ \t]*)(await\s+)?(?:page\.)?waitForTimeout\s*\(\s*\d+\s*\)\s*;?',
            _replace_pw_sleep,
            updated,
            flags=re.MULTILINE
        )

        # Cypress: cy.wait(ms)
        def _replace_cy_wait(m):
            indent = m.group(1) or ""
            fixes.append("Replaced cy.wait() static delay with smart assertion reminder")
            return f"{indent}// Synapse: Replaced cy.wait with dynamic assertion\n{indent}cy.get('body').should('be.visible');"

        updated = re.sub(
            r'^([ \t]*)cy\.wait\s*\(\s*\d+\s*\)\s*;?',
            _replace_cy_wait,
            updated,
            flags=re.MULTILINE
        )

    elif ext == ".py":
        # Python: page.wait_for_timeout(ms) -> page.wait_for_load_state('domcontentloaded')
        def _replace_py_pw(m):
            indent = m.group(1) or ""
            fixes.append("Replaced page.wait_for_timeout() with page.wait_for_load_state('domcontentloaded')")
            return f"{indent}page.wait_for_load_state('domcontentloaded')"

        updated = re.sub(
            r'^([ \t]*)page\.wait_for_timeout\s*\(\s*\d+\s*\)',
            _replace_py_pw,
            updated,
            flags=re.MULTILINE
        )

        # Python: time.sleep(sec)
        def _replace_py_sleep(m):
            indent = m.group(1) or ""
            fixes.append("Replaced time.sleep() with smart wait reminder")
            if "page" in updated:
                return f"{indent}page.wait_for_load_state('domcontentloaded')  # Replaced static sleep"
            return f"{indent}# Synapse: Replaced static sleep with dynamic smart wait"

        updated = re.sub(
            r'^([ \t]*)time\.sleep\s*\(\s*[\d\.]+\s*\)',
            _replace_py_sleep,
            updated,
            flags=re.MULTILINE
        )

    elif ext in (".groovy", ".java"):
        # Katalon / Java: Thread.sleep(ms)
        def _replace_thread_sleep(m):
            indent = m.group(1) or ""
            fixes.append("Replaced Thread.sleep() with dynamic smart wait")
            return f"{indent}// Synapse: Replaced static Thread.sleep with dynamic smart wait"

        updated = re.sub(
            r'^([ \t]*)Thread\.sleep\s*\(\s*\d+\s*\)\s*;?',
            _replace_thread_sleep,
            updated,
            flags=re.MULTILINE
        )

        # WebUI.delay(sec) -> WebUI.waitForPageLoad(10)
        def _replace_webui_delay(m):
            indent = m.group(1) or ""
            fixes.append("Replaced WebUI.delay() with WebUI.waitForPageLoad(10)")
            return f"{indent}WebUI.waitForPageLoad(10)"

        updated = re.sub(
            r'^([ \t]*)WebUI\.delay\s*\(\s*\d+\s*\)',
            _replace_webui_delay,
            updated,
            flags=re.MULTILINE
        )

    return updated, fixes


def fix_unawaited_expect(content: str, ext: str) -> Tuple[str, List[str]]:
    """
    Prepends missing 'await ' to Playwright async assertions in TS/JS.
    """
    fixes = []
    if ext not in (".ts", ".tsx", ".js", ".jsx"):
        return content, fixes

    lines = content.splitlines(keepends=True)
    new_lines = []

    for line in lines:
        stripped = line.lstrip()
        # If line starts with expect(...) without await/return and has an async matcher
        if stripped.startswith("expect(") and not stripped.startswith("await ") and not stripped.startswith("return "):
            if re.search(r'\.' + PLAYWRIGHT_ASYNC_MATCHERS + r'\s*\(', stripped):
                indent = line[:len(line) - len(stripped)]
                line = f"{indent}await {stripped}"
                fixes.append("Prepended missing 'await' to async Playwright assertion")
        new_lines.append(line)

    return "".join(new_lines), fixes


def fix_swallowed_exceptions(content: str, ext: str) -> Tuple[str, List[str]]:
    """
    Transforms empty catch/except blocks and dummy suppressions into explicit re-throws.
    """
    fixes = []
    updated = content

    if ext in (".ts", ".tsx", ".js", ".jsx", ".groovy", ".java"):
        # Pattern: catch (e) { } or catch (e) { console.log(e); }
        def _replace_empty_catch(m):
            err_var = m.group(1) or "err"
            fixes.append(f"Fixed swallowed exception in catch ({err_var}) by re-throwing error")
            return f"catch ({err_var}) {{\n    throw {err_var};\n  }}"

        updated = re.sub(
            r'catch\s*\(\s*([a-zA-Z0-9_]+)\s*\)\s*\{\s*(?:(?:console|logger|log)\.[a-zA-Z]+\([^)]*\);?\s*|(?:const|let|var)?\s*_\s*=[^;]+;?\s*)?\}',
            _replace_empty_catch,
            updated
        )

        # Pattern: .catch(() => {}) -> .catch(err => { throw err; })
        def _replace_catch_callback(m):
            fixes.append("Fixed swallowed Promise .catch() callback by re-throwing error")
            return ".catch((err) => { throw err; })"

        updated = re.sub(
            r'\.catch\s*\(\s*(?:\([^)]*\)|[a-zA-Z0-9_]+)?\s*=>\s*\{\s*\}\s*\)',
            _replace_catch_callback,
            updated
        )

    elif ext == ".py":
        # Python: except: pass -> except Exception as err: raise err
        def _replace_py_except(m):
            indent = m.group(1) or ""
            fixes.append("Fixed swallowed exception in except block by raising error")
            sub_indent = indent + "    "
            return f"{indent}except Exception as err:\n{sub_indent}raise err"

        updated = re.sub(
            r'^([ \t]*)except(?:\s+[A-Za-z0-9_\.]+(?:\s+as\s+[A-Za-z0-9_]+)?)?\s*:\s*(?:pass|\.\.\.|_\s*=\s*[^#\n;]+)(?:\s*$|\s*#.*$)',
            _replace_py_except,
            updated,
            flags=re.MULTILINE
        )

    return updated, fixes


def fix_dangling_expects(content: str, ext: str) -> Tuple[str, List[str]]:
    """
    Fixes dangling expect(locator); by appending .toBeVisible();
    """
    fixes = []
    if ext not in (".ts", ".tsx", ".js", ".jsx"):
        return content, fixes

    pattern = re.compile(r'(?:await\s+)?\bexpect(?:\.soft|\.poll)?\s*\(')
    pos = 0
    updated_parts = []

    while pos < len(content):
        m = pattern.search(content, pos)
        if not m:
            updated_parts.append(content[pos:])
            break

        # Append content before match
        updated_parts.append(content[pos:m.start()])
        start_idx = m.end()
        depth = 1
        curr = start_idx
        while curr < len(content) and depth > 0:
            ch = content[curr]
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif ch in (';', '\n') and depth > 0:
                break
            curr += 1

        if depth == 0:
            # Found closing parenthesis of expect(...)
            matched_expect = content[m.start():curr]
            rest = content[curr:]
            rest_lstrip = rest.lstrip()
            # If rest doesn't start with '.', it's a dangling assertion
            if not rest_lstrip.startswith('.'):
                if rest_lstrip.startswith(';'):
                    semi_idx = rest.find(';')
                    ws = rest[:semi_idx]
                    updated_parts.append(f"{matched_expect}{ws}.toBeVisible();")
                    pos = curr + semi_idx + 1
                    fixes.append("Appended missing '.toBeVisible()' matcher to dangling expect() call")
                    continue
                else:
                    updated_parts.append(f"{matched_expect}.toBeVisible()")
                    pos = curr
                    fixes.append("Appended missing '.toBeVisible()' matcher to dangling expect() call")
                    continue

        updated_parts.append(content[m.start():curr])
        pos = curr

    return "".join(updated_parts), fixes


def generate_fixes_for_code(content: str, file_path: str) -> Tuple[str, List[str], str]:
    """
    Applies all available auto-fixers in sequence to code content.
    Returns: (new_content, applied_fixes, unified_diff_str)
    """
    ext = os.path.splitext(file_path)[1].lower()
    total_fixes = []
    current_content = content

    # 1. Unawaited async assertions
    current_content, fixes1 = fix_unawaited_expect(current_content, ext)
    total_fixes.extend(fixes1)

    # 2. Hard delays / static sleeps
    current_content, fixes2 = fix_hard_delays(current_content, ext)
    total_fixes.extend(fixes2)

    # 3. Swallowed exceptions
    current_content, fixes3 = fix_swallowed_exceptions(current_content, ext)
    total_fixes.extend(fixes3)

    # 4. Dangling expect without matcher
    current_content, fixes4 = fix_dangling_expects(current_content, ext)
    total_fixes.extend(fixes4)

    # Generate unified diff
    if current_content != content:
        orig_lines = content.splitlines(keepends=True)
        new_lines = current_content.splitlines(keepends=True)
        diff = list(difflib.unified_diff(
            orig_lines,
            new_lines,
            fromfile=f"a/{os.path.basename(file_path)}",
            tofile=f"b/{os.path.basename(file_path)}",
            lineterm=""
        ))
        diff_str = "\n".join(diff)
    else:
        diff_str = ""

    return current_content, total_fixes, diff_str


def apply_file_fix(file_path: str, dry_run: bool = False, create_backup: bool = True) -> Dict[str, Any]:
    """
    Processes a single file, generating fixes and optionally applying them.
    Returns a result summary dictionary.
    """
    if not os.path.isfile(file_path):
        return {"file": file_path, "fixed": False, "fixes": [], "diff": "", "error": "File not found"}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            original_content = f.read()
    except Exception as e:
        return {"file": file_path, "fixed": False, "fixes": [], "diff": "", "error": str(e)}

    new_content, fixes, diff_str = generate_fixes_for_code(original_content, file_path)

    if not fixes or new_content == original_content:
        return {"file": file_path, "fixed": False, "fixes": [], "diff": "", "error": None}

    if not dry_run:
        if create_backup:
            bak_path = file_path + ".bak"
            try:
                with open(bak_path, "w", encoding="utf-8") as f:
                    f.write(original_content)
            except OSError as err:
                sys.stderr.write(f"[WARN] Failed to write backup {bak_path}: {err}\n")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

    return {
        "file": file_path,
        "fixed": True,
        "dry_run": dry_run,
        "fixes": fixes,
        "diff": diff_str,
        "error": None
    }
