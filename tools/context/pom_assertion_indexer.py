#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
"""
Cross-File Page Object & Fixture Assertion Symbol Indexer.

Indexes Page Object classes, test fixtures, and helper modules across
TypeScript, JavaScript, Python, Java, and Groovy to determine which methods
directly or transitively execute real (non-tautological) assertions up to a
bounded call depth. Preserves Synapse Hub's zero-mandatory-dependency core
while optionally upgrading AST parsing via `tree-sitter-language-pack`.
"""

from __future__ import annotations

import argparse
import ast
import json
import logging
import os
import re
import sys
import textwrap
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from tools.context.polyglot_ast_parser import (
        detect_language,
        strip_comments_and_strings,
    )
except ImportError:  # pragma: no cover - standalone fallback
    from polyglot_ast_parser import (  # type: ignore[no-redef]
        detect_language,
        strip_comments_and_strings,
    )


SUPPORTED_EXTENSIONS: Tuple[str, ...] = (
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".py",
    ".java",
    ".groovy",
)

IGNORED_DIRS: Set[str] = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "reports",
    "htmlcov",
    "claude-ecosystem-repos",
}

EXCLUDED_METHOD_NAMES: Set[str] = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "else",
    "try",
    "finally",
    "return",
    "new",
    "throw",
    "constructor",
    "__init__",
    "__new__",
    "__repr__",
    "__str__",
    "setUp",
    "tearDown",
    "beforeEach",
    "afterEach",
    "beforeAll",
    "afterAll",
    "describe",
    "context",
    "suite",
    "test",
    "it",
    "class",
    "function",
    "async",
    "await",
}

TREE_SITTER_LANG_MAP: Dict[str, str] = {
    ".ts": "typescript",
    "ts": "typescript",
    "typescript": "typescript",
    ".tsx": "tsx",
    "tsx": "tsx",
    ".js": "javascript",
    "js": "javascript",
    "javascript": "javascript",
    ".jsx": "javascript",
    "jsx": "javascript",
    ".java": "java",
    "java": "java",
    ".groovy": "groovy",
    "groovy": "groovy",
    ".cs": "c_sharp",
    "cs": "c_sharp",
    "c_sharp": "c_sharp",
    "csharp": "c_sharp",
    ".py": "python",
    "py": "python",
    "python": "python",
}

_PARSER_CACHE_LOCK = threading.RLock()
_PARSER_CACHE: Dict[str, Optional[Any]] = {}

# Tautological assertion patterns that must NEVER count as real assertions
_TAUTOLOGY_RE = re.compile(
    r"(?:expect(?:\.soft|\.poll)?\s*\(\s*(?:true|false|1|0|null|undefined)\s*\)"
    r"\s*\.\s*(?:toBe|toEqual|toBeTruthy|toBeFalsy|toBeNull|toBeUndefined)\s*\(\s*(?:true|false|1|0|null|undefined)?\s*\)"
    r"|expect(?:\.soft|\.poll)?\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*\.\s*(?:toBe|toEqual)\s*\(\s*\1\s*\)"
    r"|\bassert\s+(?:True|true|1\s*==\s*1)\b"
    r"|\bassert\s+([A-Za-z_][A-Za-z0-9_\.]*)\s*==\s*\2\b"
    r"|assertEquals\s*\(\s*(?:true|1|null)\s*,\s*(?:true|1|null)\s*\)"
    r"|assertTrue\s*\(\s*(?:true|1)\s*\))",
    re.IGNORECASE | re.DOTALL,
)

# Real non-expect assertion patterns (Java, Groovy, Cypress, Python, Katalon, Chai)
_DIRECT_ASSERT_RE = re.compile(
    r"(?:\bassert(?:Equals|NotEquals|True|False|Null|NotNull|That|Throws|Same|NotSame|ArrayEquals|IterableEquals|All)\s*\("
    r"|\b(?:Assert|Assertions)\.[A-Za-z_][A-Za-z0-9_]*\s*\("
    r"|\b(?:WebUI|WS|Mobile)\.verify[A-Za-z0-9_]*\s*\("
    r"|\bKeywordUtil\.markFailed(?:AndStop)?\s*\("
    r"|\bassert\.(?:equal|strictEqual|deepEqual|deepStrictEqual|ok|isTrue|isFalse|throws|rejects|match|include)\s*\("
    r"|\bpytest\.raises\s*\("
    r"|\bself\.assert[A-Za-z0-9_]*\s*\("
    r"|\bassert\s+[^\s;]"
    r"|\.(?:should|and)\s*\()",
    re.MULTILINE,
)

_EXPECT_CALL_RE = re.compile(r"\bexpect(?:\.soft|\.poll)?\s*\(")
_CALL_INVOCATION_RE = re.compile(r"(?:\b(?:this|self|super|[A-Za-z_][A-Za-z0-9_]*)\s*\.\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_TEST_BLOCK_RE = re.compile(
    r"(?m)^[ \t]*(?:(?:test|it)(?:\.(?:only|skip))?\s*\(|def\s+test_[A-Za-z0-9_]+\s*\(|(?:@Test\s+)?(?:public\s+)?(?:void|def)\s+test[A-Za-z0-9_]*\s*\()"
)
_CLASS_DECL_RE = re.compile(
    r"\b(?:export\s+)?(?:default\s+)?(?:abstract\s+)?(?:public\s+|private\s+|protected\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)\b"
)
_BRACE_METHOD_RE = re.compile(
    r"(?m)^[ \t]*(?:(?:export|public|private|protected|static|async|override|final|synchronized|abstract|default)\s+)*"
    r"(?:(?:function|def|void|[A-Za-z_][A-Za-z0-9_<>\[\],\s\?]*?)\s+)?"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:<[^>{};]*>)?\s*\([^)]*\)\s*(?::\s*[^{;=]+?)?\s*\{"
)
_ARROW_FUNC_RE = re.compile(
    r"(?m)^[ \t]*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*(?::\s*[^=]+?)?\s*=>\s*\{"
)


@dataclass(frozen=True)
class CrossFileAssertionMapDTO:
    """Immutable cross-file POM assertion map produced by the indexer."""

    repo_root: str
    indexed_files_count: int
    assertion_methods: Set[str]
    qualified_class_methods: Dict[str, Set[str]]
    max_call_depth: int
    used_tree_sitter: bool
    unqualified_assertion_methods: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the DTO deterministically with sorted keys and lists."""
        return {
            "repo_root": self.repo_root,
            "indexed_files_count": self.indexed_files_count,
            "assertion_methods": sorted(self.assertion_methods),
            "qualified_class_methods": {
                cls_name: sorted(methods)
                for cls_name, methods in sorted(self.qualified_class_methods.items())
            },
            "unqualified_assertion_methods": sorted(self.unqualified_assertion_methods),
            "max_call_depth": self.max_call_depth,
            "used_tree_sitter": self.used_tree_sitter,
        }


@dataclass(frozen=True)
class PolyglotAstTreeResultDTO:
    """Summary of polyglot syntax parsing for a single source or test file."""

    file_path: str
    language: str
    backend: str
    test_blocks_count: int
    syntax_valid: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "language": self.language,
            "backend": self.backend,
            "test_blocks_count": self.test_blocks_count,
            "syntax_valid": self.syntax_valid,
        }


@dataclass(frozen=True)
class MethodAssertionNode:
    """Internal representation of an indexed method or helper function."""

    key: str
    name: str
    class_name: Optional[str]
    file_path: str
    direct_assert: bool
    calls: Tuple[str, ...]


def clear_parser_cache() -> None:
    """Clears the cached optional Tree-Sitter parser instances."""
    with _PARSER_CACHE_LOCK:
        _PARSER_CACHE.clear()


def load_optional_tree_sitter_parser(language: str) -> Optional[Any]:
    """
    Resolves a Tree-Sitter parser from `tree-sitter-language-pack` when installed,
    or returns `None` cleanly without raising if unavailable or unsupported.
    """
    if not language:
        return None
    normalized = TREE_SITTER_LANG_MAP.get(language.strip().lower())
    if not normalized:
        return None

    with _PARSER_CACHE_LOCK:
        if normalized in _PARSER_CACHE:
            return _PARSER_CACHE[normalized]

    parser: Optional[Any] = None
    try:
        from tree_sitter_language_pack import get_parser  # type: ignore[import-not-found]

        parser = get_parser(normalized)
    except (ImportError, KeyError, ValueError, RuntimeError, OSError):
        parser = None

    with _PARSER_CACHE_LOCK:
        _PARSER_CACHE[normalized] = parser
    return parser


def _has_balanced_delimiters(clean_code: str) -> bool:
    """Checks basic brace/paren balance on comment- and string-stripped code."""
    stack: List[str] = []
    pairs = {")": "(", "}": "{", "]": "["}
    for ch in clean_code:
        if ch in "({[":
            stack.append(ch)
        elif ch in ")}]":
            if not stack or stack[-1] != pairs[ch]:
                return False
            stack.pop()
    return len(stack) == 0


def parse_polyglot_ast_summary(
    file_path: str,
    content: str,
    prefer_tree_sitter: bool = True,
) -> PolyglotAstTreeResultDTO:
    """
    Parses a polyglot file using Python stdlib `ast`, optional `tree-sitter-language-pack`,
    or the zero-dependency stdlib state-machine fallback.
    """
    lang = detect_language(file_path)
    if lang == "python":
        try:
            try:
                tree = ast.parse(content)
            except IndentationError:
                tree = ast.parse(textwrap.dedent(content))
            test_count = sum(
                1
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and (node.name.startswith("test_") or node.name.endswith("_test"))
            )
            return PolyglotAstTreeResultDTO(
                file_path=file_path,
                language=lang,
                backend="python_ast",
                test_blocks_count=test_count,
                syntax_valid=True,
            )
        except SyntaxError:
            return PolyglotAstTreeResultDTO(
                file_path=file_path,
                language=lang,
                backend="python_ast",
                test_blocks_count=0,
                syntax_valid=False,
            )

    clean = strip_comments_and_strings(content, lang)
    test_count = len(_TEST_BLOCK_RE.findall(clean))

    if prefer_tree_sitter:
        parser = load_optional_tree_sitter_parser(lang)
        if parser is not None:
            try:
                ts_tree = parser.parse(content.encode("utf-8"))
                root = getattr(ts_tree, "root_node", None)
                syntax_ok = not bool(getattr(root, "has_error", False)) if root is not None else True
                return PolyglotAstTreeResultDTO(
                    file_path=file_path,
                    language=lang,
                    backend="tree_sitter",
                    test_blocks_count=test_count,
                    syntax_valid=syntax_ok,
                )
            except (TypeError, ValueError, RuntimeError) as exc:
                logging.getLogger("pom_assertion_indexer").debug(
                    "Tree-sitter parse fallback for %s: %s", file_path, exc
                )

    return PolyglotAstTreeResultDTO(
        file_path=file_path,
        language=lang,
        backend="stdlib_state_machine",
        test_blocks_count=test_count,
        syntax_valid=_has_balanced_delimiters(clean),
    )


def _has_chained_expect_matcher(clean_body: str) -> bool:
    """
    Returns True if `clean_body` contains at least one `expect(...)` call
    followed by a chained matcher (e.g. `.toBeVisible()`, `.not.toHaveText()`,
    `.resolves.toEqual()`, including multiline chains).
    """
    n = len(clean_body)
    for match in _EXPECT_CALL_RE.finditer(clean_body):
        idx = match.end()
        depth = 1
        while idx < n and depth > 0:
            ch = clean_body[idx]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            idx += 1
        if depth != 0:
            continue
        # Skip whitespace/newlines between closing ')' and chained '.'
        while idx < n and clean_body[idx] in " \t\r\n":
            idx += 1
        if idx < n and clean_body[idx] == ".":
            remainder = clean_body[idx + 1 : idx + 64]
            if re.match(r"^(?:not|resolves|rejects|to[A-Z_][A-Za-z0-9_]*|[a-z][A-Za-z0-9_]*)\b", remainder):
                return True
    return False


def _body_has_real_assertion(clean_body: str, lang: str) -> bool:
    """Determines whether a comment/string-stripped method body executes a real assertion."""
    if not clean_body.strip():
        return False
    without_tautologies = _TAUTOLOGY_RE.sub(" ", clean_body)
    if _has_chained_expect_matcher(without_tautologies):
        return True
    if _DIRECT_ASSERT_RE.search(without_tautologies):
        return True
    if lang == "python" and re.search(r"\bexpect\s*\(", without_tautologies):
        return _has_chained_expect_matcher(without_tautologies)
    return False


def _find_matching_brace(text: str, open_idx: int) -> int:
    """Finds the index of the matching '}' for '{' at `open_idx`, or -1 if unbalanced."""
    depth = 0
    n = len(text)
    for idx in range(open_idx, n):
        ch = text[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return idx
    return -1


def _extract_calls_from_body(clean_body: str, self_name: str) -> Tuple[str, ...]:
    """Extracts unique callee names invoked inside a brace-language method body."""
    found: List[str] = []
    seen: Set[str] = set()
    for match in _CALL_INVOCATION_RE.finditer(clean_body):
        callee = match.group(1)
        if callee in EXCLUDED_METHOD_NAMES or callee == self_name:
            continue
        if callee not in seen:
            seen.add(callee)
            found.append(callee)
    return tuple(found)


def _extract_python_nodes(file_path: str, content: str) -> List[MethodAssertionNode]:
    """Extracts class methods and top-level helper functions from Python via stdlib ast."""
    try:
        try:
            tree = ast.parse(content)
        except IndentationError:
            tree = ast.parse(textwrap.dedent(content))
    except SyntaxError:
        return []

    nodes: List[MethodAssertionNode] = []

    def _analyze_func(fn: ast.FunctionDef | ast.AsyncFunctionDef, class_name: Optional[str]) -> None:
        name = fn.name
        if name in EXCLUDED_METHOD_NAMES or name.startswith("test_") or name.endswith("_test"):
            return

        has_real_assert = False
        calls: List[str] = []
        seen_calls: Set[str] = set()

        for child in ast.walk(fn):
            if isinstance(child, ast.Assert):
                test_node = child.test
                is_taut = False
                if isinstance(test_node, ast.Constant) and bool(test_node.value) is True:
                    is_taut = True
                elif isinstance(test_node, ast.Compare) and len(test_node.ops) == 1 and isinstance(test_node.ops[0], ast.Eq):
                    if ast.dump(test_node.left) == ast.dump(test_node.comparators[0]):
                        is_taut = True
                if not is_taut:
                    has_real_assert = True
            elif isinstance(child, ast.Call):
                callee_name = ""
                if isinstance(child.func, ast.Name):
                    callee_name = child.func.id
                elif isinstance(child.func, ast.Attribute):
                    callee_name = child.func.attr
                    if callee_name.startswith("assert") or callee_name == "raises":
                        has_real_assert = True
                    elif callee_name.startswith("to_") and isinstance(child.func.value, ast.Call):
                        inner = child.func.value.func
                        if isinstance(inner, ast.Name) and inner.id == "expect":
                            has_real_assert = True
                if callee_name and callee_name not in EXCLUDED_METHOD_NAMES and callee_name != name:
                    if callee_name not in seen_calls:
                        seen_calls.add(callee_name)
                        calls.append(callee_name)

        key = f"{class_name}.{name}" if class_name else name
        nodes.append(
            MethodAssertionNode(
                key=key,
                name=name,
                class_name=class_name,
                file_path=file_path,
                direct_assert=has_real_assert,
                calls=tuple(calls),
            )
        )

    for stmt in tree.body:
        if isinstance(stmt, ast.ClassDef):
            for item in stmt.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    _analyze_func(item, stmt.name)
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _analyze_func(stmt, None)

    return nodes


def _find_class_spans(clean_code: str) -> List[Tuple[str, int, int]]:
    """Finds `(class_name, open_brace_idx, close_brace_idx)` spans in brace-delimited code."""
    spans: List[Tuple[str, int, int]] = []
    for match in _CLASS_DECL_RE.finditer(clean_code):
        cls_name = match.group(1)
        brace_idx = clean_code.find("{", match.end())
        if brace_idx == -1:
            continue
        end_idx = _find_matching_brace(clean_code, brace_idx)
        if end_idx != -1:
            spans.append((cls_name, brace_idx, end_idx))
    return spans


_TS_CLASS_NODE_TYPES: Set[str] = {
    "class_declaration",
    "abstract_class_declaration",
    "interface_declaration",
}
_TS_METHOD_NODE_TYPES: Set[str] = {
    "method_definition",
    "method_declaration",
    "function_declaration",
}
_TS_CALL_NODE_TYPES: Set[str] = {
    "call_expression",
    "method_invocation",
}


def _ts_node_text(node: Any, source_bytes: bytes) -> str:
    s_b = max(0, int(getattr(node, "start_byte", 0)))
    e_b = max(s_b, int(getattr(node, "end_byte", s_b)))
    return source_bytes[s_b:e_b].decode("utf-8", errors="replace")


def _iter_ts_node_children(node: Any) -> List[Any]:
    out: List[Any] = []
    seen_ids: Set[int] = set()
    for ch in getattr(node, "children", None) or ():
        if id(ch) not in seen_ids:
            seen_ids.add(id(ch))
            out.append(ch)
    cbf = getattr(node, "child_by_field_name", None)
    if callable(cbf):
        for fname in ("name", "body", "function", "property", "field", "object", "value", "declarator"):
            fc = cbf(fname)
            if fc is not None and id(fc) not in seen_ids:
                seen_ids.add(id(fc))
                out.append(fc)
    return out


def _extract_ts_calls_recursive(node: Any, source_bytes: bytes, self_name: str, acc: List[str], seen: Set[str]) -> None:
    ntype = getattr(node, "type", "")
    if ntype in _TS_CALL_NODE_TYPES:
        cbf = getattr(node, "child_by_field_name", None)
        callee_txt = ""
        if callable(cbf):
            fn_node = cbf("function") or cbf("name")
            if fn_node is not None:
                fn_type = getattr(fn_node, "type", "")
                if fn_type in ("member_expression", "field_access", "scoped_identifier"):
                    fn_cbf = getattr(fn_node, "child_by_field_name", None)
                    prop = fn_cbf("property") or fn_cbf("field") if callable(fn_cbf) else None
                    if prop is not None:
                        callee_txt = _ts_node_text(prop, source_bytes).strip()
                else:
                    raw_fn = _ts_node_text(fn_node, source_bytes).strip()
                    callee_txt = raw_fn.split(".")[-1].strip() if "." in raw_fn else raw_fn
        if callee_txt and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", callee_txt):
            if callee_txt not in EXCLUDED_METHOD_NAMES and callee_txt != self_name and callee_txt not in seen:
                seen.add(callee_txt)
                acc.append(callee_txt)
    for child in _iter_ts_node_children(node):
        _extract_ts_calls_recursive(child, source_bytes, self_name, acc, seen)


def extract_tree_sitter_method_nodes(
    root_node: Any,
    source_bytes: bytes,
    file_path: str,
    lang: str,
) -> List[MethodAssertionNode]:
    """
    Traverses a Tree-Sitter CST/AST `root_node` to extract class methods,
    standalone functions, arrow-function helpers, direct assertions, and call edges.
    """
    if root_node is None or getattr(root_node, "has_error", False):
        return []

    extracted: List[MethodAssertionNode] = []
    seen_keys: Set[Tuple[str, int]] = set()

    def _visit(node: Any, enclosing_cls: Optional[str]) -> None:
        ntype = getattr(node, "type", "")
        cbf = getattr(node, "child_by_field_name", None)

        if ntype in _TS_CLASS_NODE_TYPES:
            cls_name_node = cbf("name") if callable(cbf) else None
            cls_name = _ts_node_text(cls_name_node, source_bytes).strip() if cls_name_node is not None else enclosing_cls
            for ch in _iter_ts_node_children(node):
                if ch is not cls_name_node:
                    _visit(ch, cls_name or enclosing_cls)
            return

        method_name = ""
        body_node: Optional[Any] = None
        if ntype in _TS_METHOD_NODE_TYPES:
            name_node = cbf("name") if callable(cbf) else None
            body_node = cbf("body") if callable(cbf) else None
            if name_node is not None:
                method_name = _ts_node_text(name_node, source_bytes).strip()
        elif ntype == "variable_declarator":
            name_node = cbf("name") if callable(cbf) else None
            val_node = cbf("value") if callable(cbf) else None
            if name_node is not None and val_node is not None and getattr(val_node, "type", "") in (
                "arrow_function",
                "function_expression",
                "function",
            ):
                method_name = _ts_node_text(name_node, source_bytes).strip()
                val_cbf = getattr(val_node, "child_by_field_name", None)
                body_node = val_cbf("body") if callable(val_cbf) else val_node

        if method_name and body_node is not None:
            if method_name not in EXCLUDED_METHOD_NAMES and not method_name.startswith("test_"):
                dedup_id = (method_name, int(getattr(node, "start_byte", 0)))
                if dedup_id not in seen_keys:
                    seen_keys.add(dedup_id)
                    raw_body = _ts_node_text(body_node, source_bytes)
                    clean_body = strip_comments_and_strings(raw_body, lang)
                    ast_calls: List[str] = []
                    ast_seen: Set[str] = set()
                    _extract_ts_calls_recursive(body_node, source_bytes, method_name, ast_calls, ast_seen)
                    for lex_call in _extract_calls_from_body(clean_body, method_name):
                        if lex_call not in ast_seen:
                            ast_seen.add(lex_call)
                            ast_calls.append(lex_call)
                    key = f"{enclosing_cls}.{method_name}" if enclosing_cls else method_name
                    extracted.append(
                        MethodAssertionNode(
                            key=key,
                            name=method_name,
                            class_name=enclosing_cls,
                            file_path=file_path,
                            direct_assert=_body_has_real_assertion(clean_body, lang),
                            calls=tuple(ast_calls),
                        )
                    )

        for ch in _iter_ts_node_children(node):
            _visit(ch, enclosing_cls)

    _visit(root_node, None)
    return extracted


def _extract_brace_lang_nodes(
    file_path: str,
    content: str,
    lang: str,
    prefer_tree_sitter: bool = True,
) -> Tuple[List[MethodAssertionNode], bool]:
    """
    Extracts class methods and top-level helpers from TS/JS/Java/Groovy files.
    Walks the compiler-grade Tree-Sitter CST when available and merges any
    DSL-specific constructs from the zero-dependency stdlib brace scanner.
    """
    used_ts = False
    ts_nodes: List[MethodAssertionNode] = []
    if prefer_tree_sitter:
        parser = load_optional_tree_sitter_parser(lang)
        if parser is not None:
            try:
                src_bytes = content.encode("utf-8")
                ts_tree = parser.parse(src_bytes)
                root_node = getattr(ts_tree, "root_node", None)
                if root_node is not None and not getattr(root_node, "has_error", False):
                    ts_nodes = extract_tree_sitter_method_nodes(root_node, src_bytes, file_path, lang)
                    used_ts = True
            except (TypeError, ValueError, RuntimeError):
                used_ts = False
                ts_nodes = []

    clean = strip_comments_and_strings(content, lang)
    class_spans = _find_class_spans(clean)
    nodes: List[MethodAssertionNode] = list(ts_nodes)
    existing_node_keys: Set[str] = {n.key for n in nodes}
    seen_keys: Set[Tuple[str, int]] = set()

    def _enclosing_class(pos: int) -> Optional[str]:
        best: Optional[Tuple[str, int]] = None
        for cls_name, start_b, end_b in class_spans:
            if start_b < pos < end_b:
                span_len = end_b - start_b
                if best is None or span_len < best[1]:
                    best = (cls_name, span_len)
        return best[0] if best else None

    for regex in (_BRACE_METHOD_RE, _ARROW_FUNC_RE):
        for match in regex.finditer(clean):
            name = match.group(1)
            if name in EXCLUDED_METHOD_NAMES or name.startswith("test_"):
                continue
            open_brace = clean.rfind("{", match.start(), match.end())
            if open_brace == -1:
                continue
            if (name, open_brace) in seen_keys:
                continue
            end_brace = _find_matching_brace(clean, open_brace)
            if end_brace == -1:
                continue
            seen_keys.add((name, open_brace))

            body = clean[open_brace + 1 : end_brace]
            cls_name = _enclosing_class(match.start())
            key = f"{cls_name}.{name}" if cls_name else name
            if key in existing_node_keys:
                continue
            existing_node_keys.add(key)
            nodes.append(
                MethodAssertionNode(
                    key=key,
                    name=name,
                    class_name=cls_name,
                    file_path=file_path,
                    direct_assert=_body_has_real_assertion(body, lang),
                    calls=_extract_calls_from_body(body, name),
                )
            )

    return nodes, used_ts


def resolve_transitive_assertions(
    nodes: Iterable[MethodAssertionNode],
    max_depth: int = 3,
) -> Tuple[Set[str], Dict[str, Set[str]]]:
    """
    Cycle-safe reverse BFS propagating direct assertions to callers up to `max_depth`.
    Guaranteed O(V + E) termination even on mutually recursive POM call graphs.
    """
    bounded_depth = max(0, int(max_depth))
    node_list = list(nodes)
    if not node_list:
        return set(), {}

    by_key: Dict[str, MethodAssertionNode] = {}
    keys_by_name: Dict[str, List[str]] = {}
    for node in node_list:
        unique_key = node.key
        if unique_key in by_key:
            # Merge duplicate method definitions deterministically
            existing = by_key[unique_key]
            merged_calls = tuple(dict.fromkeys(existing.calls + node.calls))
            by_key[unique_key] = MethodAssertionNode(
                key=unique_key,
                name=node.name,
                class_name=node.class_name,
                file_path=existing.file_path,
                direct_assert=existing.direct_assert or node.direct_assert,
                calls=merged_calls,
            )
        else:
            by_key[unique_key] = node
            keys_by_name.setdefault(node.name, []).append(unique_key)

    # Build reverse call graph: callee_key -> set of caller_keys
    reverse_edges: Dict[str, Set[str]] = {k: set() for k in by_key}
    for caller_key, caller_node in by_key.items():
        for callee_name in caller_node.calls:
            # Prioritize same-class helper, then any indexed method with matching name
            candidates: List[str] = []
            if caller_node.class_name:
                same_cls_key = f"{caller_node.class_name}.{callee_name}"
                if same_cls_key in by_key:
                    candidates.append(same_cls_key)
            for candidate_key in keys_by_name.get(callee_name, ()):
                if candidate_key not in candidates:
                    candidates.append(candidate_key)
            for callee_key in candidates:
                if callee_key != caller_key:
                    reverse_edges[callee_key].add(caller_key)

    # Reverse BFS from direct assertion nodes
    min_depth: Dict[str, int] = {}
    queue: deque[Tuple[str, int]] = deque()
    for key, node in by_key.items():
        if node.direct_assert:
            min_depth[key] = 0
            queue.append((key, 0))

    while queue:
        current_key, depth = queue.popleft()
        if depth >= bounded_depth:
            continue
        next_depth = depth + 1
        for caller_key in reverse_edges.get(current_key, ()):
            if caller_key not in min_depth or next_depth < min_depth[caller_key]:
                min_depth[caller_key] = next_depth
                queue.append((caller_key, next_depth))

    assertion_methods: Set[str] = set()
    qualified_class_methods: Dict[str, Set[str]] = {}
    for key in min_depth:
        node = by_key[key]
        assertion_methods.add(node.name)
        if node.class_name:
            qualified_class_methods.setdefault(node.class_name, set()).add(node.name)

    return assertion_methods, qualified_class_methods


def _discover_candidate_files(repo_root: str, max_files: int) -> List[str]:
    """Deterministically discovers supported source/POM files up to `max_files`."""
    if not repo_root or not os.path.isdir(repo_root) or max_files <= 0:
        return []
    found: List[str] = []
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS and not d.startswith("."))
        for fname in sorted(files):
            if os.path.splitext(fname)[1].lower() in SUPPORTED_EXTENSIONS:
                found.append(os.path.join(root, fname))
                if len(found) >= max_files:
                    return found
    return found


def build_pom_assertion_index(
    repo_root: str,
    max_depth: int = 3,
    prefer_tree_sitter: bool = True,
    max_files: int = 2000,
) -> CrossFileAssertionMapDTO:
    """
    Indexes Page Object and fixture methods across `repo_root` that directly
    or transitively execute real assertions up to `max_depth` call hops.
    """
    abs_root = os.path.abspath(repo_root) if repo_root else ""
    files = _discover_candidate_files(abs_root, max_files=max_files)
    if not files:
        return CrossFileAssertionMapDTO(
            repo_root=abs_root,
            indexed_files_count=0,
            assertion_methods=set(),
            qualified_class_methods={},
            max_call_depth=max(0, int(max_depth)),
            used_tree_sitter=False,
        )

    all_nodes: List[MethodAssertionNode] = []
    any_tree_sitter = False
    indexed_count = 0

    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            continue
        indexed_count += 1
        if not content.strip():
            continue
        lang = detect_language(fpath)
        if lang == "python":
            all_nodes.extend(_extract_python_nodes(fpath, content))
        elif lang in ("typescript", "javascript", "java", "groovy"):
            file_nodes, used_ts = _extract_brace_lang_nodes(
                fpath, content, lang, prefer_tree_sitter=prefer_tree_sitter
            )
            all_nodes.extend(file_nodes)
            if used_ts:
                any_tree_sitter = True

    assertion_methods, qualified_class_methods = resolve_transitive_assertions(
        all_nodes, max_depth=max_depth
    )
    class_owned_names: Set[str] = set()
    for cls_methods in qualified_class_methods.values():
        class_owned_names.update(cls_methods)
    top_level_names = {n.name for n in all_nodes if not n.class_name}
    unqualified_assertion_methods = (assertion_methods & top_level_names) | (assertion_methods - class_owned_names)

    return CrossFileAssertionMapDTO(
        repo_root=abs_root,
        indexed_files_count=indexed_count,
        assertion_methods=assertion_methods,
        qualified_class_methods=qualified_class_methods,
        max_call_depth=max(0, int(max_depth)),
        used_tree_sitter=any_tree_sitter,
        unqualified_assertion_methods=unqualified_assertion_methods,
    )


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint for Cross-File POM Assertion Indexer."""
    parser = argparse.ArgumentParser(
        description="Cross-File Page Object & Fixture Assertion Symbol Indexer"
    )
    parser.add_argument("--root", default=".", help="Workspace root directory to index")
    parser.add_argument("--max-depth", type=int, default=3, help="Max transitive call depth")
    parser.add_argument(
        "--max-files", type=int, default=2000, help="Maximum source files to scan"
    )
    parser.add_argument(
        "--no-tree-sitter",
        action="store_true",
        help="Force deterministic stdlib parser even if tree-sitter-language-pack is installed",
    )
    parser.add_argument(
        "--check-file",
        default=None,
        help="Optional single file path to emit PolyglotAstTreeResultDTO summary",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args(argv)

    if args.check_file:
        try:
            with open(args.check_file, "r", encoding="utf-8", errors="replace") as f:
                src = f.read()
        except OSError as exc:
            err_payload = {"error": str(exc), "file_path": args.check_file}
            print(json.dumps(err_payload, indent=2, sort_keys=True))
            return 1
        summary = parse_polyglot_ast_summary(
            args.check_file, src, prefer_tree_sitter=not args.no_tree_sitter
        )
        if args.json:
            print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
        else:
            print(
                f"[AST] {summary.file_path} | lang={summary.language} "
                f"backend={summary.backend} tests={summary.test_blocks_count} valid={summary.syntax_valid}"
            )
        return 0

    dto = build_pom_assertion_index(
        repo_root=args.root,
        max_depth=args.max_depth,
        prefer_tree_sitter=not args.no_tree_sitter,
        max_files=args.max_files,
    )
    if args.json:
        print(json.dumps(dto.to_dict(), indent=2, sort_keys=True))
    else:
        print(
            f"[POM-INDEX] files={dto.indexed_files_count} "
            f"assertion_methods={len(dto.assertion_methods)} "
            f"classes={len(dto.qualified_class_methods)} "
            f"tree_sitter={dto.used_tree_sitter}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
