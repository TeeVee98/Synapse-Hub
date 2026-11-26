#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

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

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass


import os
import sys
import re
import json
import glob
import ast
import html as html_lib
import argparse
import logging
from datetime import datetime

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
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

try:
    from tools.lint.auto_fixer import apply_file_fix, colorize_diff
except ImportError:
    try:
        from auto_fixer import apply_file_fix, colorize_diff
    except ImportError:
        apply_file_fix = None
        colorize_diff = None

try:
    from tools.report.health_scorecard import generate_html_scorecard
except ImportError:
    try:
        from health_scorecard import generate_html_scorecard
    except ImportError:
        generate_html_scorecard = None


def get_git_changed_files(repo_root):
    """Discovers modified, staged, and untracked files using standard git command."""
    import subprocess
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        if res.returncode == 0:
            changed = set()
            for line in res.stdout.splitlines():
                if len(line) > 3:
                    f = line[3:].strip()
                    if " -> " in f:
                        f = f.split(" -> ")[1].strip()
                    changed.add(os.path.abspath(os.path.join(repo_root, f)))
            return changed
    except (subprocess.SubprocessError, OSError) as err:
        sys.stderr.write(f"[DEBUG] Git status check unavailable: {err}\n")
    return None


def format_mentorship_card(defect, file_rel):
    """
    Renders a bilingual, empathetic, actionable Mentorship Diagnostic card.
    """
    d_type = defect.get("type", "UNKNOWN_DEFECT")
    severity = defect.get("severity", "WARNING")
    line = defect.get("line", 1)
    msg = defect.get("message", "")

    color = RED if severity == "CRITICAL" else YELLOW

    guidance = {
        "EXCESSIVE_HARD_DELAY": {
            "why_vi": "Hard sleep làm test chạy chậm lãng phí và dễ gãy trên CI khi mạng hoặc CPU tải cao.",
            "why_en": "Static sleep causes slow test execution and non-deterministic flaky failures on CI.",
            "fix_diff": "- await page.waitForTimeout(5000);\n+ await page.waitForLoadState('domcontentloaded'); // or expect(locator).toBeVisible()"
        },
        "HARD_DELAY_ANTI_PATTERN": {
            "why_vi": "Sleep cố định tạo ra nợ kỹ thuật và làm giảm độ tin cậy của test suite.",
            "why_en": "Fixed delay anti-pattern introduces flakiness and slows down execution.",
            "fix_diff": "- time.sleep(2)\n+ page.wait_for_load_state('domcontentloaded') # or dynamic assertion"
        },
        "UNAWAITED_ASYNC_ASSERTION": {
            "why_vi": "Thiếu 'await' khiến assertion trả về Promise Pending mà không kiểm tra, dẫn đến test luôn pass ảo (false green).",
            "why_en": "Missing 'await' returns an unvalidated pending Promise, causing false-positive passes.",
            "fix_diff": "- expect(locator).toBeVisible();\n+ await expect(locator).toBeVisible();"
        },
        "SWALLOWED_EXCEPTION": {
            "why_vi": "Nuốt lỗi try-catch rỗng che giấu bug thật của hệ thống, khiến test xanh giả tạo.",
            "why_en": "Empty catch block silently swallows exceptions, hiding genuine application defects.",
            "fix_diff": "- catch (e) {}\n+ catch (e) { throw e; }"
        },
        "DANGLING_ASSERTION_NO_MATCHER": {
            "why_vi": "expect() không có matcher (.toBeVisible, .toHaveText) không thực hiện bất kỳ kiểm tra nào.",
            "why_en": "expect() without a chained matcher does not evaluate system state.",
            "fix_diff": "- expect(locator);\n+ expect(locator).toBeVisible();"
        },
        "TAUTOLOGICAL_ASSERTION": {
            "why_vi": "Assert luôn đúng (1==1, true==true) không kiểm tra logic thực tế, là biểu hiện của test rác.",
            "why_en": "Tautological assertion always evaluates to True without testing actual system behavior.",
            "fix_diff": "- expect(true).toBe(true);\n+ await expect(page.locator('#success')).toBeVisible();"
        },
        "FAKE_PASS_NO_ASSERTION": {
            "why_vi": "Test script chỉ tương tác nhưng không có câu lệnh assert xác minh kết quả mong đợi.",
            "why_en": "Test script interacts with AUT but lacks assertions to verify expected outcome.",
            "fix_diff": "+ await expect(page.locator('#dashboard')).toBeVisible();"
        }
    }

    info = guidance.get(d_type, {
        "why_vi": "Vi phạm tiêu chuẩn chất lượng kiểm thử trong AGENTS.md.",
        "why_en": "Violates test quality standards defined in AGENTS.md.",
        "fix_diff": f"# Vui lòng kiểm tra và sửa lỗi: {msg}"
    })

    card = []
    card.append(f"  {BOLD}╭─ {color}⚠️  [{severity}] {d_type}{RESET} ──────────────────────────────────────────{RESET}")
    card.append(f"  │ 📍 {BOLD}{file_rel}:{line}{RESET}")
    card.append(f"  │ ❌ {BOLD}Vấn đề / Problem:{RESET} {msg}")
    card.append(f"  │ 💡 {BOLD}Tại sao cần sửa / Why it matters:{RESET}")
    card.append(f"  │    🇻🇳 {info['why_vi']}")
    card.append(f"  │    🇬🇧 {info['why_en']}")
    card.append(f"  │ 🛠️  {BOLD}Gợi ý sửa nhanh / Suggested Fix:{RESET}")
    for diff_line in info['fix_diff'].splitlines():
        if diff_line.startswith("+"):
            card.append(f"  │    {GREEN}{diff_line}{RESET}")
        elif diff_line.startswith("-"):
            card.append(f"  │    {RED}{diff_line}{RESET}")
        else:
            card.append(f"  │    {CYAN}{diff_line}{RESET}")
    card.append(f"  {BOLD}╰──────────────────────────────────────────────────────────────────────────{RESET}\n")
    return "\n".join(card)

try:
    from tools.context.pom_assertion_indexer import (
        CrossFileAssertionMapDTO,
        build_pom_assertion_index,
        load_optional_tree_sitter_parser,
    )
except ImportError:
    try:
        from context.pom_assertion_indexer import (
            CrossFileAssertionMapDTO,
            build_pom_assertion_index,
            load_optional_tree_sitter_parser,
        )
    except ImportError:
        CrossFileAssertionMapDTO = None
        build_pom_assertion_index = None
        load_optional_tree_sitter_parser = None

def parse_with_tree_sitter(file_path, content):
    """
    Optional compiler-grade AST parsing via tree-sitter-language-pack when installed.
    Extracts syntactic AST trees for TypeScript, JavaScript, Java, Groovy, and C#.
    Returns None cleanly if tree-sitter-language-pack is unavailable or grammar is unsupported.
    """
    if load_optional_tree_sitter_parser is None:
        return None
    try:
        ext = os.path.splitext(file_path)[1].lower()
        parser = load_optional_tree_sitter_parser(ext)
        if parser is None:
            return None
        return parser.parse(bytes(content, "utf-8"))
    except Exception:
        return None


GENERIC_COLLISION_METHOD_NAMES = frozenset({
    "validate", "check", "verify", "ensure", "run", "execute", "process", "handle", "test", "init", "setup",
})

_JS_NEW_RE = re.compile(
    r"\b(?:const|let|var|final)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*[A-Za-z_][A-Za-z0-9_<>]*\s*)?=\s*new\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("
)
_JAVA_NEW_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*new\s+[A-Za-z_][A-Za-z0-9_]*\s*\("
)
_PY_CALL_NEW_RE = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([A-Z][A-Za-z0-9_]*)\s*\("
)
_RECEIVER_TYPE_ANNOT_RE = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Z][A-Za-z0-9_]*)\b"
)


_IMPORT_AS_ALIAS_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9_]*)\s+as\s+([A-Z][A-Za-z0-9_]*)\b"
)


def _resolve_import_alias(class_name, alias_map):
    current = class_name
    visited = set()
    for _ in range(5):
        if current in visited or current not in alias_map:
            break
        visited.add(current)
        current = alias_map[current]
    return current


def _extract_receiver_class_bindings(clean_code, fixture_bindings=None, barrel_aliases=None):
    """Infers local/fixture variable -> ClassName bindings from instantiations, type annotations, fixtures, and aliased imports."""
    alias_map = dict(barrel_aliases or {})
    if clean_code:
        for m in _IMPORT_AS_ALIAS_RE.finditer(clean_code):
            alias_map[m.group(2)] = m.group(1)

    bindings = {}
    if fixture_bindings:
        for fname, cls_name in fixture_bindings.items():
            bindings[fname] = _resolve_import_alias(cls_name, alias_map)

    if not clean_code:
        return bindings
    for m in _RECEIVER_TYPE_ANNOT_RE.finditer(clean_code):
        bindings[m.group(1)] = _resolve_import_alias(m.group(2), alias_map)
    for m in _JS_NEW_RE.finditer(clean_code):
        bindings[m.group(1)] = _resolve_import_alias(m.group(2), alias_map)
    for m in _JAVA_NEW_RE.finditer(clean_code):
        bindings[m.group(2)] = _resolve_import_alias(m.group(1), alias_map)
    for m in _PY_CALL_NEW_RE.finditer(clean_code):
        bindings[m.group(1)] = _resolve_import_alias(m.group(2), alias_map)
    return bindings


def _receiver_matches_class_stem(receiver, class_name):
    """True when `receiver` (e.g. `orderPage`, `my_order_page`) matches `class_name` (`OrderPage`)."""
    r_norm = receiver.replace("_", "").lower()
    c_norm = class_name.replace("_", "").lower()
    return bool(c_norm) and r_norm.endswith(c_norm)


def extract_tree_sitter_test_spans(ts_tree, source_bytes):
    """
    Walks a Tree-Sitter CST/AST tree to extract `(start_line_1_based, block_text)`
    for top-level/nested `test(...)`, `it(...)`, and `@Test` method declarations.
    """
    if ts_tree is None:
        return []
    root = getattr(ts_tree, "root_node", None)
    if root is None or bool(getattr(root, "has_error", False)):
        return []

    spans = []
    seen = set()

    def _slice(node):
        return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

    def _walk(node):
        ntype = getattr(node, "type", "")
        if ntype == "call_expression":
            child_by_field = getattr(node, "child_by_field_name", None)
            fn_node = child_by_field("function") if callable(child_by_field) else None
            if fn_node is not None:
                fn_txt = _slice(fn_node).strip()
                if fn_txt in ("test", "it", "test.only", "it.only", "test.skip", "it.skip"):
                    sp = getattr(node, "start_point", None)
                    line_1 = (int(sp[0]) + 1) if (isinstance(sp, tuple) and len(sp) >= 1) else (
                        source_bytes[: int(getattr(node, "start_byte", 0))].count(b"\n") + 1
                    )
                    key = (line_1, int(getattr(node, "start_byte", 0)))
                    if key not in seen:
                        seen.add(key)
                        spans.append((line_1, _slice(node)))
                    return
        elif ntype == "method_declaration":
            txt = _slice(node)
            if "@Test" in txt or re.search(r"\b(?:void|def)\s+test[A-Za-z0-9_]*\s*\(", txt):
                sp = getattr(node, "start_point", None)
                line_1 = (int(sp[0]) + 1) if (isinstance(sp, tuple) and len(sp) >= 1) else (
                    source_bytes[: int(getattr(node, "start_byte", 0))].count(b"\n") + 1
                )
                key = (line_1, int(getattr(node, "start_byte", 0)))
                if key not in seen:
                    seen.add(key)
                    spans.append((line_1, txt))
                return

        for child in getattr(node, "children", None) or ():
            _walk(child)

    _walk(root)
    return spans


def _match_cross_file_assertions(clean_code, assertion_map, file_clean_code=None):
    """
    Counts invocations of verified cross-file Page Object assertion helpers in `clean_code`
    with receiver-class disambiguation to prevent unqualified method collisions.
    """
    if not assertion_map or not getattr(assertion_map, "assertion_methods", None):
        return 0
    methods = assertion_map.assertion_methods
    if not methods:
        return 0
    qualified_map = getattr(assertion_map, "qualified_class_methods", None) or {}
    unqualified_set = getattr(assertion_map, "unqualified_assertion_methods", None)
    fixture_bindings = getattr(assertion_map, "fixture_class_bindings", None)
    barrel_aliases = getattr(assertion_map, "barrel_aliases", None)
    bindings = _extract_receiver_class_bindings(
        file_clean_code if file_clean_code is not None else clean_code,
        fixture_bindings=fixture_bindings,
        barrel_aliases=barrel_aliases,
    )

    hits = 0
    call_re = re.compile(r'(?:(\b[A-Za-z_][A-Za-z0-9_]*)\s*\.\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\(')
    for m in call_re.finditer(clean_code):
        receiver = m.group(1)
        callee = m.group(2)
        if callee not in methods:
            continue

        if not qualified_map:
            hits += 1
            continue

        owning_classes = [cls_name for cls_name, cls_methods in qualified_map.items() if callee in cls_methods]

        if not receiver:
            if unqualified_set is not None and callee in unqualified_set:
                hits += 1
            elif not owning_classes and callee not in GENERIC_COLLISION_METHOD_NAMES:
                hits += 1
            continue

        if receiver in ("this", "self", "super"):
            hits += 1
            continue

        bound_cls = bindings.get(receiver)
        if bound_cls:
            if callee in qualified_map.get(bound_cls, set()):
                hits += 1
            continue

        if any(_receiver_matches_class_stem(receiver, cls_name) for cls_name in owning_classes):
            hits += 1
            continue

        if callee not in GENERIC_COLLISION_METHOD_NAMES and owning_classes:
            hits += 1

    return hits


def _discover_lazy_assertion_map(file_path):
    """Lazily builds a small local POM assertion index for standalone analyze_script() calls."""
    if build_pom_assertion_index is None:
        return None
    import tempfile
    abs_file = os.path.abspath(file_path)
    parent = os.path.dirname(abs_file)
    sys_tmp = os.path.abspath(tempfile.gettempdir())
    if not parent or parent == sys_tmp or parent == os.path.dirname(parent) or parent == REPO_ROOT:
        return None
    base_name = os.path.basename(parent).lower()
    candidate_root = parent
    if base_name in ("tests", "test", "e2e", "specs", "spec", "cypress", "scripts"):
        grandparent = os.path.dirname(parent)
        if grandparent and grandparent != sys_tmp and grandparent != REPO_ROOT and grandparent != os.path.dirname(grandparent):
            candidate_root = grandparent
    return build_pom_assertion_index(candidate_root, max_depth=3, max_files=200)

# Generic Detection regexes (including Cypress .should and .and assertions)
# Note: Standalone expect(...) without chained matcher is caught as DANGLING_ASSERTION_NO_MATCHER.
ASSERTION_PATTERN = re.compile(
    r'\b(verify[A-Za-z0-9_]*|assert[A-Za-z0-9_]*|waitForToast|checkStatus|assertEquals|assertTrue|assertFalse|assertThat|expect|ensure[A-Z][A-Za-z0-9_]*Exists|check)\b'
    r'|\.should\s*\('
    r'|\.and\s*\('
    r'|\.(?:failure|success)\s*\(',
    re.MULTILINE
)

# Rule L1 & L5: Empty catch / swallowed exceptions across JS/TS/Groovy/Java and Python
# Also catches try/catch that only console.log/logger.error, promise .catch(() => {}),
# or dummy assignment bypasses like `_ = err`, `_ = e`, `_ = False`, `const _ = err;`
EMPTY_CATCH_PATTERN = re.compile(
    r'(?:catch\s*(?:\([^\)]*\))?\s*\{\s*(?:(?:console|logger|log)\.(?:log|warn|error|info)\([^)]*\);?\s*|(?:const|let|var|def)?\s*_\s*=\s*[^;]+;?\s*)?\}'
    r'|\.catch\s*\(\s*(?:\([^)]*\)|[a-zA-Z0-9_]+)?\s*=>\s*\{\s*(?:(?:console|logger|log)\.(?:log|warn|error|info)\([^)]*\);?\s*|(?:const|let|var|def)?\s*_\s*=\s*[^;]+;?\s*)?\}\s*\)'
    r'|\bexcept(?:\s+[^:]*)?:\s*(?:pass|\.\.\.|_\s*=\s*[^#\n;]+)(?:\s*$|\s*#))',
    re.MULTILINE
)

# Whitelisted best-effort compatibility calls (UTF-8 console reconfigure, file
# permission chmod, stream flush, stream set_blocking). An empty catch guarding ONLY these is an
# intentional no-op-on-failure idiom, not a swallowed test failure.
BENIGN_TRY_CALL_PATTERN = re.compile(
    r'^[\w\.]*\.(?:reconfigure|chmod|flush|set_blocking)\s*\('
)

# Rule L3: Tautological assertions (e.g. expect(true).toBe(true), assert r == r, assert f() == f(), assert len(x) >= 0)
TAUTOLOGY_PATTERN = re.compile(
    r'(?:expect(?:\.soft|\.poll)?\s*\(\s*(?:true|1|null|undefined)\s*\)\s*\.\s*(?:toBe|toEqual|toBeTruthy|toBeNull|toBeUndefined)\s*\(\s*(?:true|1|null|undefined)?\s*\)'
    r'|expect(?:\.soft|\.poll)?\s*\(\s*([a-zA-Z0-9_]+)\s*\)\s*\.\s*(?:toBe|toEqual)\s*\(\s*\1\s*\)'
    r'|\bassert\s+(?:True|true|1\s*==\s*1)\b'
    r'|\bassert\s+([a-zA-Z0-9_\.]+(?:\([^)]*\))?)\s*==\s*\1\b'
    r'|\bassert\s+(?:len\s*\([^)]*\)|[a-zA-Z0-9_\.]+\.(?:length|size\(\)))\s*(?:>=\s*0|>\s*-(?:1|0))\b'
    r'|assertEquals\s*\(\s*(?:true|1|null)\s*,\s*(?:true|1|null)\s*\)'
    r'|assertTrue\s*\(\s*(?:true|1)\s*\))',
    re.IGNORECASE
)


def find_dangling_expects(clean_code, raw_lines):
    """
    Detects dangling expect(...) calls lacking chained matchers (e.g. expect(page) without .toBeVisible()).
    Correctly handles nested parentheses and multiline expect(...) chains.
    """
    dangling = []
    pattern = re.compile(r'(?:await\s+)?\bexpect(?:\.soft|\.poll)?\s*\(')
    for m in pattern.finditer(clean_code):
        start_idx = m.end()
        depth = 1
        pos = start_idx
        max_scan = min(len(clean_code), start_idx + 1200)
        while pos < max_scan and depth > 0:
            ch = clean_code[pos]
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif ch == ';' and depth > 0:
                # Malformed unclosed expect terminated by statement semicolon
                break
            pos += 1
        if depth == 0:
            rest = clean_code[pos:].lstrip()
            if not rest.startswith('.'):
                line_no = clean_code[:m.start()].count("\n") + 1
                raw_line = raw_lines[line_no - 1].strip() if line_no <= len(raw_lines) else ""
                dangling.append((line_no, raw_line))
    return dangling

# Rule L4: Unawaited Playwright assertions in JS/TS
# Expanded with all standard Playwright async matchers, optional .not modifier, and multiline chains
PLAYWRIGHT_ASYNC_MATCHERS = (
    r'(?:toBeVisible|toBeHidden|toHaveText|toHaveValue|toHaveCount|toBeEnabled|toBeDisabled|'
    r'toBeChecked|toHaveURL|toContainText|toHaveTitle|toHaveAttribute|toHaveClass|toHaveId|'
    r'toBeFocused|toBeEmpty|toBeAttached|toBeInViewport|toBeOK)'
)
UNAWAITED_EXPECT_PATTERN = re.compile(
    r'\bexpect(?:\.soft|\.poll)?\s*\([^;]{1,300}?\)\s*(?:\.\s*not)?\s*\.\s*' + PLAYWRIGHT_ASYNC_MATCHERS + r'\s*\(',
    re.MULTILINE | re.DOTALL
)

# Rule 3: Flaky Static Delays across Groovy, Java, Playwright (JS/TS/Python), Pytest/Python, Cypress
# Millisecond-based delays: Thread.sleep(ms), waitForTimeout(ms), wait_for_timeout(ms), cy.wait(ms)
MS_DELAY_PATTERN = re.compile(
    r'\b(?:Thread\.sleep|(?:page\.)?waitForTimeout|(?:page\.)?wait_for_timeout|cy\.wait)\s*\(\s*([^)]+)\s*\)'
)

# Second-based delays: WebUI.delay(sec), time.sleep(sec), asyncio.sleep(sec)
SEC_DELAY_PATTERN = re.compile(
    r'\b(?:WebUI\.delay|time\.sleep|asyncio\.sleep)\s*\(\s*([^)]+)\s*\)'
)

# Backward-compatibility alias
THREAD_SLEEP_PATTERN = MS_DELAY_PATTERN


_HASH_COMMENT_EXTS = frozenset({".py", ".sh", ".bash", ".zsh", ".yaml", ".yml", ".rb", ".r", ".toml"})
_JS_TS_EXTS = frozenset({".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"})

_LEXER_HASH_PATTERN = re.compile(
    r'(?P<TRIPLE_DOUBLE>"""[\s\S]*?""")|'
    r'(?P<TRIPLE_SINGLE>\'\'\'[\s\S]*?\'\'\')|'
    r'(?P<DOUBLE_STRING>"(?:\\.|[^"\\])*")|'
    r'(?P<SINGLE_STRING>\'(?:\\.|[^\'\\])*\')|'
    r'(?P<HASH_COMMENT>#[^\r\n]*)',
    re.DOTALL,
)

_LEXER_JS_PATTERN = re.compile(
    r'(?P<TEMPLATE_LITERAL>`(?:\\.|[^`\\])*`)|'
    r'(?P<DOUBLE_STRING>"(?:\\.|[^"\\])*")|'
    r'(?P<SINGLE_STRING>\'(?:\\.|[^\'\\])*\')|'
    r'(?P<BLOCK_COMMENT>/\*.*?\*/)|'
    r'(?P<LINE_COMMENT>//[^\r\n]*)',
    re.DOTALL,
)

_LEXER_CSTYLE_PATTERN = re.compile(
    r'(?P<TRIPLE_DOUBLE>"""[\s\S]*?""")|'
    r'(?P<TRIPLE_SINGLE>\'\'\'[\s\S]*?\'\'\')|'
    r'(?P<DOUBLE_STRING>"(?:\\.|[^"\\])*")|'
    r'(?P<SINGLE_STRING>\'(?:\\.|[^\'\\])*\')|'
    r'(?P<BLOCK_COMMENT>/\*.*?\*/)|'
    r'(?P<LINE_COMMENT>//[^\r\n]*)',
    re.DOTALL,
)


def strip_comments_and_strings(source_code, preserve_newlines=True, file_ext=".py"):
    """
    Lexically strips block comments, line comments, multiline strings,
    and quoted literals scoped by file extension while preserving line numbering.
    Supports JS/TS backtick template literals and avoids treating '#' inside
    JS/TS/Java/Groovy selectors as hash comments.
    """
    ext = (file_ext or ".py").lower()
    if ext in _JS_TS_EXTS:
        pattern = _LEXER_JS_PATTERN
    elif ext in _HASH_COMMENT_EXTS:
        pattern = _LEXER_HASH_PATTERN
    else:
        pattern = _LEXER_CSTYLE_PATTERN

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
            return bool(body_lines) and all(BENIGN_TRY_CALL_PATTERN.match(bl) for bl in body_lines)
        body_lines.append(stripped)
    return False


def load_config(repo_root=None, config_path=None):
    """Loads configuration from synapse.config.json if present."""
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as err:
            logging.getLogger("infer_linter").debug("Failed to read config from %s: %s", config_path, err)

    root = repo_root or REPO_ROOT
    candidates = [
        os.path.join(root, "synapse.config.json"),
        os.path.join(root, ".synapse.json"),
        os.path.join(os.getcwd(), "synapse.config.json"),
        os.path.join(os.getcwd(), ".synapse.json")
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                with open(c, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
    return {}


def load_baseline(baseline_path):
    """Loads existing baseline findings to suppress known technical debt."""
    if not baseline_path or not os.path.exists(baseline_path):
        return set()
    try:
        with open(baseline_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            items = data.get("defects", data) if isinstance(data, dict) else data
            signatures = set()
            for it in items:
                f_path = it.get("file", "").replace("\\", "/")
                d_type = it.get("type", "").upper()
                d_line = it.get("line")
                if d_line is not None:
                    try:
                        signatures.add((f_path, d_type, int(d_line)))
                    except (ValueError, TypeError):
                        signatures.add((f_path, d_type, d_line))
            return signatures
    except (OSError, json.JSONDecodeError):
        return set()


def save_baseline(baseline_path, all_defects):
    """Saves current findings into a baseline JSON file."""
    os.makedirs(os.path.dirname(os.path.abspath(baseline_path)), exist_ok=True)
    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "total_defects": len(all_defects),
            "defects": all_defects
        }, f, indent=2, ensure_ascii=False)


def format_sarif(report_data):
    """Formats findings in standard SARIF 2.1.0 JSON format for GitHub Code Scanning."""
    results = []
    rules_dict = {}
    for d in report_data.get("all_defects", []):
        rule_id = d.get("type", "STATIC_DEFECT")
        if rule_id not in rules_dict:
            rules_dict[rule_id] = {
                "id": rule_id,
                "shortDescription": {"text": d.get("message", rule_id)},
                "defaultConfiguration": {
                    "level": "error" if d.get("severity") == "CRITICAL" else "warning"
                }
            }
        results.append({
            "ruleId": rule_id,
            "level": "error" if d.get("severity") == "CRITICAL" else "warning",
            "message": {"text": d.get("message", "")},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": d.get("file", "")},
                    "region": {"startLine": max(1, d.get("line", 1))}
                }
            }]
        })
    sarif_doc = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "synapse-infer-linter",
                    "version": "2.3.0",
                    "rules": list(rules_dict.values())
                }
            },
            "results": results
        }]
    }
    return json.dumps(sarif_doc, indent=2, ensure_ascii=False)


def format_junit(report_data):
    """Formats findings in standard JUnit XML format."""
    total = max(1, report_data.get("total_scripts", 0))
    defects = report_data.get("all_defects", [])
    failures = len([d for d in defects if d.get("severity") == "CRITICAL"])
    warnings = len([d for d in defects if d.get("severity") != "CRITICAL"])
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        f'<testsuite name="synapse-infer-linter" tests="{max(total, len(defects))}" failures="{failures}" errors="{warnings}">'
    ]
    for d in defects:
        cname = d.get("file", "").replace("/", ".").replace("\\", ".")
        tname = f"{d.get('type')}_L{d.get('line', 1)}"
        msg = html_lib.escape(d.get("message", ""))
        tag = "failure" if d.get("severity") == "CRITICAL" else "error"
        lines.append(f'  <testcase classname="{cname}" name="{tname}">')
        lines.append(f'    <{tag} message="{msg}" type="{d.get("type")}">Line {d.get("line", 1)}: {msg}</{tag}>')
        lines.append('  </testcase>')
    if not defects:
        lines.append('  <testcase classname="synapse.linter" name="clean_run"/>')
    lines.append('</testsuite>')
    return "\n".join(lines)


def classify_file_role(file_path: str, content: str = "") -> str:
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
    if content and (re.search(r'\bclass\s+[A-Za-z0-9_]*Page\b', content) or re.search(r'\bextends\s+BasePage\b', content)):
        return "PAGE_OBJECT"

    # 3. Helpers & Fixtures / Tools & Utilities / Benchmarks
    if any(p in ("fixtures", "helpers", "utils", "support", "tools", "bin", "benchmarks", "benchmark") for p in parts):
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


def analyze_script(file_path, baseline_set=None, disabled_rules=None, assertion_map=None, source_content=None):
    """Performs static rule scanning on a single test script or automation asset (on-disk or in-memory)."""
    try:
        rel_path = os.path.relpath(file_path, REPO_ROOT)
    except ValueError:
        rel_path = os.path.abspath(file_path)

    if source_content is not None:
        content = source_content
    else:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

    role = classify_file_role(file_path, content=content)

    # Config files have zero test assertions by definition
    if role == "CONFIG":
        return {
            "file": rel_path,
            "role": role,
            "defects": [],
            "is_clean": True,
            "ast_backend": "none",
            "cross_file_assertions_resolved": 0,
        }

    defects = []

    # Lexically strip comments and string literals scoped by file extension
    file_ext = os.path.splitext(file_path)[1].lower() or ".py"
    clean_code = strip_comments_and_strings(content, preserve_newlines=True, file_ext=file_ext)
    clean_lines = [line.strip() for line in clean_code.splitlines()]

    raw_lines = content.splitlines()

        # Optional Tree-Sitter AST pass for non-Python polyglot languages
    ast_backend = "python_ast" if file_ext == ".py" else "stdlib_state_machine"
    ts_tree = None
    if file_ext in (".ts", ".tsx", ".js", ".jsx", ".java", ".groovy", ".cs"):
        ts_tree = parse_with_tree_sitter(file_path, content)
        if ts_tree is not None:
            ast_backend = "tree_sitter"

    cross_file_resolved = 0

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
            "message": "Empty catch block or dummy suppression (_ = err) detected. Swallowed exceptions cause false-pass test runs."
        })

    # Rule 3: Flaky Static Delays (Playwright, Cypress, Pytest, Katalon, Java/Groovy)
    for idx, line in enumerate(clean_code.splitlines(), 1):
        raw_line = raw_lines[idx - 1].strip() if idx <= len(raw_lines) else line.strip()

        # Millisecond delays
        m_ms = MS_DELAY_PATTERN.search(line)
        if m_ms:
            arg = m_ms.group(1).strip()
            # F08: Ignore Cypress route alias waits like cy.wait('@getUsers')
            if arg.startswith(("@", "'@", '"@')):
                pass
            elif arg.isdigit():
                delay_val = int(arg)
                if delay_val > 0:
                    is_excessive = delay_val >= 3000
                    d_type = "EXCESSIVE_HARD_DELAY" if is_excessive else "HARD_DELAY_ANTI_PATTERN"
                    sev = "CRITICAL" if (is_excessive and role == "TEST_SCRIPT") else "WARNING"
                    defects.append({
                        "type": d_type,
                        "severity": sev,
                        "line": idx,
                        "message": f"Static sleep of {delay_val}ms found ('{raw_line}'). {'Prohibited in test scripts by AGENTS.md Rule 1.4. ' if is_excessive else ''}Replace with dynamic Smart Wait (waitForElement/networkidle)."
                    })
                    continue
            elif re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', arg) and not line.strip().startswith("cy.wait"):
                defects.append({
                    "type": "HARD_DELAY_ANTI_PATTERN",
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
                if delay_val > 0:
                    delay_ms = int(delay_val * 1000)
                    delay_str = f"{delay_val:g}"
                    is_excessive = delay_ms >= 3000
                    d_type = "EXCESSIVE_HARD_DELAY" if is_excessive else "HARD_DELAY_ANTI_PATTERN"
                    sev = "CRITICAL" if (is_excessive and role == "TEST_SCRIPT") else "WARNING"
                    defects.append({
                        "type": d_type,
                        "severity": sev,
                        "line": idx,
                        "message": f"Static sleep of {delay_str}s ({delay_ms}ms) found ('{raw_line}'). {'Prohibited in test scripts by AGENTS.md Rule 1.4. ' if is_excessive else ''}Replace with dynamic Smart Wait (waitForElement/networkidle)."
                    })
            except ValueError:
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', arg):
                    defects.append({
                        "type": "HARD_DELAY_ANTI_PATTERN",
                        "severity": "WARNING",
                        "line": idx,
                        "message": f"Static sleep with variable/expression '{arg}' found ('{raw_line}'). Replace with dynamic Smart Wait."
                    })

    # Test Script Specific Invariants (Do NOT apply to Page Objects or Helpers)
    if role == "TEST_SCRIPT":
        executable_lines = [
            line for line in clean_lines
            if line and not line.startswith("import ") and not line.startswith("package ") and not line.startswith("from ")
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

        # Rule 4.1: Dangling expect(...) calls without chained matcher
        for d_line, d_raw in find_dangling_expects(clean_code, raw_lines):
            defects.append({
                "type": "DANGLING_ASSERTION_NO_MATCHER",
                "severity": "CRITICAL",
                "line": d_line,
                "message": f"Dangling expect() call without matcher detected ('{d_raw}'). expect() returns an expectation object and does not perform any assertion without a matcher (e.g. .toBeVisible(), .toHaveText())."
            })

        # Rule 4.2: Python AST Compiler-Grade Verification for .py Test Scripts
        if file_path.endswith(".py"):
            try:
                try:
                    tree = ast.parse(content, filename=file_path)
                except IndentationError:
                    import textwrap
                    tree = ast.parse(textwrap.dedent(content), filename=file_path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assert):
                        if isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
                            op = node.test.ops[0]
                            right = node.test.comparators[0]
                            if isinstance(op, ast.Eq):
                                if ast.dump(node.test.left) == ast.dump(right):
                                    line_no = getattr(node, "lineno", 1)
                                    raw_line = raw_lines[line_no - 1].strip() if line_no <= len(raw_lines) else ""
                                    defects.append({
                                        "type": "TAUTOLOGICAL_ASSERTION",
                                        "severity": "CRITICAL",
                                        "line": line_no,
                                        "message": f"Tautological assertion detected via AST ('{raw_line}'). Both sides of comparison evaluate to identical AST expressions."
                                    })
                            elif isinstance(op, (ast.GtE, ast.Gt)):
                                if isinstance(node.test.left, ast.Call) and getattr(node.test.left.func, 'id', None) == 'len':
                                    if isinstance(right, ast.Constant):
                                        if (isinstance(op, ast.GtE) and right.value == 0) or (isinstance(op, ast.Gt) and right.value < 0):
                                            line_no = getattr(node, "lineno", 1)
                                            raw_line = raw_lines[line_no - 1].strip() if line_no <= len(raw_lines) else ""
                                            defects.append({
                                                "type": "TAUTOLOGICAL_ASSERTION",
                                                "severity": "CRITICAL",
                                                "line": line_no,
                                                "message": f"Tautological assertion detected via AST ('{raw_line}'). len() is non-negative by definition."
                                            })
                        elif isinstance(node.test, ast.Constant) and node.test.value is True:
                            line_no = getattr(node, "lineno", 1)
                            raw_line = raw_lines[line_no - 1].strip() if line_no <= len(raw_lines) else ""
                            defects.append({
                                "type": "TAUTOLOGICAL_ASSERTION",
                                "severity": "CRITICAL",
                                "line": line_no,
                                "message": f"Tautological assertion detected via AST ('{raw_line}'). Constant True assertion."
                            })
                    elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                        if getattr(node.value.func, 'id', None) == 'expect':
                            line_no = getattr(node, "lineno", 1)
                            raw_line = raw_lines[line_no - 1].strip() if line_no <= len(raw_lines) else ""
                            defects.append({
                                "type": "DANGLING_ASSERTION_NO_MATCHER",
                                "severity": "CRITICAL",
                                "line": line_no,
                                "message": f"Dangling expect() call without matcher detected via AST ('{raw_line}')."
                            })

                # Rule 4.3: Unpaired Dynamic Data Creation without Teardown Cleanup (AGENTS.md Rule 1.3)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if node.name.startswith("test_") or node.name.endswith("_test"):
                            has_creation = False
                            creation_node = None
                            has_teardown = False
                            for child in ast.walk(node):
                                if isinstance(child, ast.Call):
                                    func_name = ""
                                    if isinstance(child.func, ast.Name):
                                        func_name = child.func.id
                                    elif isinstance(child.func, ast.Attribute):
                                        func_name = child.func.attr
                                    if re.search(r'^(?:create_entity|insert_entity|seed_data|generate_user|create_customer)\b', func_name, re.IGNORECASE) or func_name in ("uniqueCode", "DataGenerator"):
                                        has_creation = True
                                        if not creation_node:
                                            creation_node = child
                                    if re.search(r'^(?:delete|teardown|cleanup|drop|purge|remove)\w*', func_name, re.IGNORECASE) or func_name in ("addCleanup", "cleanup"):
                                        has_teardown = True
                                elif isinstance(child, ast.Try) and child.finalbody:
                                    has_teardown = True
                            if has_creation and not has_teardown:
                                line_no = getattr(creation_node, "lineno", node.lineno)
                                raw_line = raw_lines[line_no - 1].strip() if line_no <= len(raw_lines) else ""
                                defects.append({
                                    "type": "ORPHAN_DATA_RISK",
                                    "severity": "WARNING",
                                    "line": line_no,
                                    "message": f"Test data creation detected without paired teardown cleanup ('{raw_line}'). Risk of DB state pollution per AGENTS.md Rule 1.3."
                                })
            except (SyntaxError, ValueError) as err:
                logging.getLogger("infer_linter").debug("AST parse skipped due to syntax error: %s", err)

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

        # Rule 6 (L2 & L6): Missing Assertions / Fake-Pass (with Cross-File POM Assertion Indexer)
        assert_matches = list(ASSERTION_PATTERN.finditer(clean_code))
        tautology_matches = list(TAUTOLOGY_PATTERN.finditer(clean_code))
        has_real_assert = any(
            not any(tm.start() <= am.start() < tm.end() for tm in tautology_matches)
            for am in assert_matches
        )

        resolved_map = assertion_map
        if not has_real_assert and resolved_map is None:
            resolved_map = _discover_lazy_assertion_map(file_path)
        if resolved_map is not None:
            file_pom_hits = _match_cross_file_assertions(clean_code, resolved_map, file_clean_code=clean_code)
            if file_pom_hits > 0:
                cross_file_resolved += file_pom_hits
                has_real_assert = True

        # F06: Check test cases per function block if multiple tests exist (Tree-Sitter CST spans preferred)
        ts_block_spans = (
            extract_tree_sitter_test_spans(ts_tree, content.encode("utf-8"))
            if ts_tree is not None
            else []
        )
        TEST_BLOCK_PATTERN = re.compile(
            r'(?m)^[ \t]*(?:(?:test|it)(?:\.(?:only|skip))?\s*\(|def\s+test_[a-zA-Z0-9_]+\s*\(|(?:@Test\s+)?(?:public\s+)?(?:void|def)\s+test[a-zA-Z0-9_]*\s*\()'
        )
        if len(ts_block_spans) >= 2:
            block_entries = [
                (b_line, strip_comments_and_strings(b_raw, preserve_newlines=True, file_ext=file_ext))
                for b_line, b_raw in ts_block_spans
            ]
        else:
            test_matches = list(TEST_BLOCK_PATTERN.finditer(clean_code))
            block_entries = [
                (
                    clean_code[: tm.start()].count("\n") + 1,
                    clean_code[tm.start() : (test_matches[i + 1].start() if i + 1 < len(test_matches) else len(clean_code))],
                )
                for i, tm in enumerate(test_matches)
            ] if len(test_matches) >= 2 else []

        if len(block_entries) >= 2:
            for b_line, block_code in block_entries:
                b_asserts = list(ASSERTION_PATTERN.finditer(block_code))
                b_tauts = list(TAUTOLOGY_PATTERN.finditer(block_code))
                block_has_real_assert = any(
                    not any(tt.start() <= ta.start() < tt.end() for tt in b_tauts)
                    for ta in b_asserts
                )
                if not block_has_real_assert:
                    if resolved_map is None:
                        resolved_map = _discover_lazy_assertion_map(file_path)
                    if resolved_map is not None:
                        b_pom_hits = _match_cross_file_assertions(
                            block_code, resolved_map, file_clean_code=clean_code
                        )
                        if b_pom_hits > 0:
                            cross_file_resolved += b_pom_hits
                            block_has_real_assert = True
                b_has_interactions = any(
                    kw in block_code for kw in ["click", "select", "save", "delete", "create", "search", "navigate", "open", "fill", "goto", "post", "get"]
                )
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

    seen_keys = set()
    deduped = []
    for d in defects:
        k = (d.get("type"), d.get("line"))
        if k not in seen_keys:
            seen_keys.add(k)
            deduped.append(d)
    defects = deduped

    active_defects = []
    disabled = {r.upper() for r in (disabled_rules or [])}
    norm_rel = rel_path.replace("\\", "/")

    for d in defects:
        d_type = d.get("type", "").upper()
        if d_type in disabled:
            continue
        line_idx = d.get("line", 1)

        # Check suppression comment (# synapse-ignore or // synapse-ignore)
        suppressed = False
        candidates = []
        if 1 <= line_idx <= len(raw_lines):
            candidates.append(raw_lines[line_idx - 1])
        if line_idx > 1 and line_idx - 1 <= len(raw_lines):
            candidates.append(raw_lines[line_idx - 2])
        for c in candidates:
            if "synapse-ignore" in c.lower():
                m = re.search(r'synapse-ignore:\s*([A-Za-z0-9_,\s\*\-]+)', c, re.IGNORECASE)
                if m:
                    rules = [r.strip().upper() for r in m.group(1).split(",") if r.strip()]
                    if "*" in rules or "ALL" in rules or d_type in rules:
                        suppressed = True
                        break
        if suppressed:
            continue

        # Check baseline suppression
        if baseline_set:
            norm_abs = os.path.abspath(file_path).replace("\\", "/")
            if (norm_rel, d_type, line_idx) in baseline_set or (norm_abs, d_type, line_idx) in baseline_set:
                continue

        active_defects.append(d)

    defects = active_defects

    return {
        "file": rel_path,
        "role": role,
        "defects": defects,
        "is_clean": len(defects) == 0,
        "ast_backend": ast_backend,
        "cross_file_assertions_resolved": cross_file_resolved,
    }


def _filter_script_paths(raw_files, scan_dir, extra_ignored):
    """Filters out tool/build/artifact directories and non-test setup files."""
    ignored_parts = {
        "tools", "bin", "node_modules", ".git", "__pycache__", "venv", ".venv",
        "claude-ecosystem-repos", "dist", "build", ".idea", ".vscode", "editors",
        ".mypy_cache", ".pytest_cache", ".ruff_cache", ".sandbox_snapshots",
        "graphify-out", "test-results", "playwright-report", "allure-results"
    } | extra_ignored
    return [
        f for f in raw_files
        if not any(part.lower() in ignored_parts for part in os.path.relpath(f, scan_dir).replace("\\", "/").split("/")[:-1])
        and os.path.basename(f) not in {"__init__.py", "setup.py"}
    ]


def run_infer_linter(target_dir=None, output_path=None, strict: bool = False,
                     output_format="text", baseline_path=None, generate_baseline_path=None, config_path=None,
                     fix: bool = False, dry_run: bool = False, changed_only: bool = False,
                     html_report=None, repo_root=None):
    """Scans test scripts across Groovy, TypeScript, JavaScript, Python, and Java with baseline, auto-fix, and SARIF support."""
    EXTENSIONS = ("*.groovy", "*.ts", "*.tsx", "*.js", "*.jsx", "*.py", "*.java")
    base_root = repo_root or REPO_ROOT

    cfg = load_config(config_path=config_path)
    linter_cfg = cfg.get("infer_linter", {})
    extra_ignored = set(linter_cfg.get("exclude_paths", []))
    disabled_rules = set(linter_cfg.get("disabled_rules", []))
    baseline_set = load_baseline(baseline_path)

    if linter_cfg.get("strict") is not None and not strict:
        strict = bool(linter_cfg.get("strict"))

    if target_dir:
        if os.path.isfile(target_dir):
            script_files = [target_dir]
            scan_dir = os.path.dirname(target_dir)
        elif os.path.isdir(target_dir):
            scan_dir = target_dir
            raw_files = []
            for ext in EXTENSIONS:
                raw_files.extend(glob.glob(os.path.join(scan_dir, "**", ext), recursive=True))
            script_files = _filter_script_paths(raw_files, scan_dir, extra_ignored)
        else:
            scan_dir = target_dir
            script_files = []
    else:
        # Search candidate test directories (skip case-folded lowercase packaging scripts/ on Windows)
        script_files = []
        scan_dir = os.path.join(base_root, "Scripts")
        is_hub = os.path.isfile(os.path.join(base_root, "tools", "core", "verify_all.py"))
        candidates = ["examples", "tests", "test", "e2e", "specs", "cypress"] if is_hub else ["Scripts", "tests", "test", "e2e", "specs", "cypress"]
        root_entries = set(os.listdir(base_root)) if os.path.isdir(base_root) else set()
        for cand in candidates:
            if cand == "Scripts" and cand not in root_entries:
                continue
            cand_path = os.path.join(base_root, cand)
            if os.path.isdir(cand_path):
                raw_files = []
                for ext in EXTENSIONS:
                    raw_files.extend(glob.glob(os.path.join(cand_path, "**", ext), recursive=True))
                filtered = _filter_script_paths(raw_files, cand_path, extra_ignored)
                if filtered:
                    script_files = filtered
                    scan_dir = cand_path
                    break

    if changed_only:
        changed_files = get_git_changed_files(REPO_ROOT)
        if changed_files is not None:
            script_files = [f for f in script_files if os.path.abspath(f) in changed_files]

    # Auto-Fix execution if requested
    if (fix or dry_run) and apply_file_fix:
        print(f"\n{BOLD}{CYAN}⚡ Synapse Autonomous Test Code Auto-Fixer {'(DRY RUN)' if dry_run else ''}{RESET}")
        print(f"{CYAN}──────────────────────────────────────────────────────────────────────{RESET}")
        fixed_files_count = 0
        total_fixes_count = 0

        for s in sorted(set(script_files)):
            fix_res = apply_file_fix(s, dry_run=dry_run)
            if fix_res.get("fixed"):
                fixed_files_count += 1
                total_fixes_count += len(fix_res["fixes"])
                rel = os.path.relpath(s, scan_dir)
                print(f"  {BOLD}📄 {rel}:{RESET}")
                for fix_msg in fix_res["fixes"]:
                    print(f"     {GREEN}✔ {fix_msg}{RESET}")
                if fix_res["diff"]:
                    print(colorize_diff(fix_res["diff"].splitlines()))
                print()

        mode_str = "Previewed (Dry-run)" if dry_run else "Successfully applied"
        print(f"{GREEN}✨ {mode_str} {total_fixes_count} fix(es) across {fixed_files_count} file(s).{RESET}\n")

    # Build cross-file POM assertion map once for the scan root
    assertion_map = None
    if build_pom_assertion_index is not None and script_files and os.path.isdir(scan_dir):
        index_root = scan_dir
        if os.path.basename(os.path.abspath(scan_dir)).lower() in ("tests", "test", "e2e", "specs", "spec", "cypress", "scripts"):
            parent_dir = os.path.dirname(os.path.abspath(scan_dir))
            if parent_dir and parent_dir != os.path.dirname(parent_dir) and parent_dir != REPO_ROOT:
                index_root = parent_dir
        assertion_map = build_pom_assertion_index(index_root, max_depth=3)

    results = []
    critical_count = 0
    warning_count = 0
    clean_count = 0
    total_cross_file_resolved = 0
    all_defects = []

    for s in sorted(set(script_files)):
        res = analyze_script(s, baseline_set=baseline_set, disabled_rules=disabled_rules, assertion_map=assertion_map)
        results.append(res)
        total_cross_file_resolved += int(res.get("cross_file_assertions_resolved", 0))
        crit = sum(1 for d in res["defects"] if d["severity"] == "CRITICAL")
        warn = sum(1 for d in res["defects"] if d["severity"] == "WARNING")
        critical_count += crit
        warning_count += warn
        if res["is_clean"]:
            clean_count += 1
        for d in res["defects"]:
            all_defects.append({
                "file": res["file"],
                "role": res["role"],
                "type": d["type"],
                "severity": d["severity"],
                "line": d["line"],
                "message": d["message"]
            })

    # If requested to generate a baseline file, save and exit
    if generate_baseline_path:
        save_baseline(generate_baseline_path, all_defects)
        print(f"✅ Generated baseline file with {len(all_defects)} defects at: {generate_baseline_path}")
        return 0

    total_scripts = len(script_files)
    if total_scripts == 0:
        health_score = 0.0
        clean_pct = 0.0
    else:
        clean_pct = round((clean_count / total_scripts) * 100, 1)
        critical_penalty = (critical_count * 20.0) / total_scripts
        raw_score = (clean_count / total_scripts) * 100.0 - critical_penalty
        health_score = max(0.0, min(100.0, round(raw_score, 1)))

        if clean_count < total_scripts and health_score >= 100.0:
            health_score = 99.0
        if clean_count == 0 and total_scripts > 0:
            health_score = 0.0

    defect_scripts = [r for r in results if not r["is_clean"]]
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "total_scripts": total_scripts,
        "clean_scripts": clean_count,
        "critical_defects": critical_count,
        "warnings": warning_count,
        "health_score_pct": health_score,
        "cross_file_assertions_resolved": total_cross_file_resolved,
        "defect_details": defect_scripts,
        "all_defects": all_defects
    }

    # Handle specialized output formats
    if output_format == "sarif":
        sarif_out = format_sarif(report_data)
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(sarif_out)
            print(f"SARIF 2.1.0 report saved to: {output_path}")
        else:
            print(sarif_out)
        return 1 if critical_count > 0 else 0

    if output_format == "junit":
        junit_out = format_junit(report_data)
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(junit_out)
            print(f"JUnit XML report saved to: {output_path}")
        else:
            print(junit_out)
        return 1 if critical_count > 0 else 0

    if output_format == "json":
        json_out = json.dumps(report_data, indent=2, ensure_ascii=False)
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json_out)
            print(f"JSON report saved to: {output_path}")
        else:
            print(json_out)
        return 1 if critical_count > 0 else 0

    if (html_report or output_format == "html") and generate_html_scorecard:
        if isinstance(html_report, str) and html_report not in ("True", "true", "1"):
            target_html = os.path.abspath(html_report)
        elif output_format == "html" and output_path:
            target_html = os.path.abspath(output_path)
        else:
            target_html = os.path.join(REPO_ROOT, "reports", "synapse_health_scorecard.html")
        generate_html_scorecard(report_data, target_html)
        print(f"✨ Executive Quality Scorecard saved to: {target_html}")
        if output_format == "html":
            return 1 if critical_count > 0 else 0

    # Default: Text output with ANSI banner
    print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
    print(f"{BOLD}{CYAN}    ENTERPRISE STATIC DEFECT & FAKE-PASS SENTINEL (Meta Infer-Style)        {RESET}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}")
    if total_scripts == 0:
        print(f"  Target Scope            : 0 Test Scripts discovered in {os.path.basename(scan_dir)}/ (No tests found)")
        print(f"  Critical Defects        : {GREEN}0{RESET}")
        print(f"  Warnings / Suggestions  : {GREEN}0{RESET}")
        print("  Clean Scripts           : 0/0 (N/A)")
        print(f"  Codebase Health Score   : {YELLOW}N/A (0 test scripts discovered){RESET}")
    else:
        print(f"  Target Scope            : {total_scripts} Test Scripts in {os.path.basename(scan_dir)}/ (Polyglot)")
        if baseline_set:
            print(f"  Baseline Filter         : {CYAN}ACTIVE ({len(baseline_set)} known debt items suppressed){RESET}")
        print(f"  Critical Defects        : {RED if critical_count > 0 else GREEN}{critical_count}{RESET} (Swallowed exceptions, empty scripts)")
        print(f"  Warnings / Suggestions  : {YELLOW if warning_count > 0 else GREEN}{warning_count}{RESET} (Missing explicit asserts, excessive delays)")
        print(f"  Clean Scripts           : {GREEN}{clean_count}/{total_scripts} ({clean_pct:.1f}%){RESET}")
        print(f"  Codebase Health Score   : {GREEN if health_score == 100 else YELLOW}{health_score:.1f}%{RESET}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}\n")

    if defect_scripts:
        print(f"{BOLD}Detected Items ({len(defect_scripts)} scripts):{RESET}\n")
        for r in defect_scripts[:10]:
            for d in r["defects"]:
                print(format_mentorship_card(d, r["file"]))
        if len(defect_scripts) > 10:
            print(f"  ... and {len(defect_scripts) - 10} more scripts (see full JSON report).\n")
        print(f"  {BOLD}💡 Mẹo thực thi / Pro Tip:{RESET} Chạy {CYAN}python tools/lint/infer_linter.py <target> --fix{RESET} (hoặc {CYAN}synapse fix{RESET}) để tự động sửa các lỗi phổ biến!\n")

    if output_path:
        dest_json = os.path.abspath(output_path)
    elif target_dir and not os.path.abspath(target_dir).startswith(REPO_ROOT):
        # Resolve target project root when scanning a file or subfolder (e.g. Scripts/, tests/)
        abs_target = os.path.abspath(target_dir)
        cur = abs_target if os.path.isdir(abs_target) else os.path.dirname(abs_target)
        proj_root = cur
        user_home = os.path.abspath(os.path.expanduser("~"))
        while cur and cur != os.path.dirname(cur) and cur != REPO_ROOT and cur != user_home:
            if os.path.isfile(os.path.join(cur, ".synapse.json")) or os.path.isdir(os.path.join(cur, ".git")):
                proj_root = cur
                break
            if os.path.basename(cur) in ("Scripts", "tests", "test", "e2e", "specs", "cypress"):
                proj_root = os.path.dirname(cur)
                break
            cur = os.path.dirname(cur)
        dest_json = os.path.join(proj_root, "reports", "infer_linter_report.json")
    else:
        dest_json = OUTPUT_JSON

    os.makedirs(os.path.dirname(dest_json), exist_ok=True)
    with open(dest_json, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    print(f"Detailed audit saved to: {dest_json}\n")

    if strict:
        anti_pattern_count = sum(1 for r in results for d in r["defects"] if d["type"] in (
            "FAKE_PASS_NO_ASSERTION", "NO_ASSERTION_IN_TEST", "DANGLING_ASSERTION_NO_MATCHER",
            "HARD_DELAY_ANTI_PATTERN", "EXCESSIVE_HARD_DELAY"
        ))
        return 0 if (critical_count == 0 and anti_pattern_count == 0) else 1
    return 0 if critical_count == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="Universal QA Static Defect & Assertion Sentinel")
    parser.add_argument("target", nargs="?", default=None, help="Target directory or script to scan")
    parser.add_argument("--dir", help="Target directory to scan (defaults to Scripts/)")
    parser.add_argument("--repo", help="Target repository root containing Scripts/")
    parser.add_argument("--out", "--output", dest="output_file", help="Path to save report")
    parser.add_argument("--format", choices=["text", "json", "sarif", "junit", "html"], default="text", help="Output format (default: text)")
    parser.add_argument("--html", nargs="?", const=True, default=False, help="Generate interactive single-file HTML health scorecard (optional destination path)")
    parser.add_argument("--baseline", help="Path to baseline JSON file to ignore known technical debt")
    parser.add_argument("--generate-baseline", dest="generate_baseline", help="Generate a baseline JSON file from current findings")
    parser.add_argument("--config", help="Path to synapse.config.json")
    parser.add_argument("--strict", action="store_true", default=True, help="Treat missing assertions / fake-passes as fatal errors (default: True)")
    parser.add_argument("--no-strict", "--lenient", action="store_false", dest="strict", help="Allow missing assertions with warning only")
    parser.add_argument("--fix", action="store_true", help="Automatically fix supported test defects (sleeps, unawaited expect, swallowed catch)")
    parser.add_argument("--dry-run", action="store_true", help="Preview fixes as a diff without modifying files on disk")
    parser.add_argument("--changed-only", action="store_true", help="Only scan files modified in Git working tree")
    args = parser.parse_args()

    target_dir = args.dir or args.target
    if not target_dir and args.repo:
        for cand in ["tests", "e2e", "cypress/e2e", "cypress", "Scripts", "test"]:
            cpath = os.path.join(args.repo, cand)
            if os.path.isdir(cpath):
                target_dir = cpath
                break
        if not target_dir:
            target_dir = args.repo

    return run_infer_linter(
        target_dir=target_dir,
        output_path=args.output_file,
        strict=args.strict,
        output_format=args.format,
        baseline_path=args.baseline,
        generate_baseline_path=args.generate_baseline,
        config_path=args.config,
        fix=args.fix,
        dry_run=args.dry_run,
        changed_only=args.changed_only,
        html_report=args.html
    )


if __name__ == "__main__":
    sys.exit(main())
