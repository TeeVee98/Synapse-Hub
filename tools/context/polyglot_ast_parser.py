#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
"""
Polyglot AST & Structural Symbol Parser (Zero-Dependency)
Part of Synapse Hub — Created by Thế Vị (@TeeVee98) under MIT License.

Extracts top-level and member structural signatures (classes, interfaces, methods, functions)
and formats them with AST Structural Anchors:
  [AST: SymbolName | L<start>-L<end>]

Supports:
  - Python (.py)
  - TypeScript (.ts, .tsx)
  - JavaScript (.js, .jsx, .mjs, .cjs)
  - Java (.java)
  - Groovy (.groovy)

Zero external dependencies: uses Python standard library ast and robust state-machine tokenization
with comment and string literal sanitization to prevent false positives.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


def detect_language(filepath: str) -> str:
    """Infers programming or configuration language from file extension or basename."""
    ext = os.path.splitext(filepath)[1].lower()
    base = os.path.basename(filepath).lower()
    if ext == ".py":
        return "python"
    elif ext in (".ts", ".tsx"):
        return "typescript"
    elif ext in (".js", ".jsx", ".mjs", ".cjs"):
        return "javascript"
    elif ext == ".java":
        return "java"
    elif ext in (".groovy", ".gvy"):
        return "groovy"
    elif ext == ".json":
        return "json"
    elif ext in (".yml", ".yaml"):
        return "yaml"
    elif ext in (".sh", ".bash", ".zsh"):
        return "shell"
    elif base.startswith("dockerfile"):
        return "dockerfile"
    return "unknown"


def strip_comments_and_strings(source: str, lang: str) -> str:
    """
    Sanitizes code by replacing comments and string literals with spaces,
    preserving exact newline positions so line numbers remain 100% synchronized.
    """
    chars: List[str] = []
    i = 0
    n = len(source)
    state = "NORMAL"

    is_c_like = lang in ("typescript", "javascript", "java", "groovy")
    is_hash_comment = lang in ("python", "groovy")

    while i < n:
        c = source[i]
        nxt = source[i + 1] if i + 1 < n else ""

        if state == "NORMAL":
            if is_c_like and c == "/" and nxt == "/":
                state = "LINE_COMMENT"
                chars.append("  ")
                i += 2
                continue
            elif is_c_like and c == "/" and nxt == "*":
                state = "BLOCK_COMMENT"
                chars.append("  ")
                i += 2
                continue
            elif is_hash_comment and c == "#":
                state = "LINE_COMMENT"
                chars.append(" ")
                i += 1
                continue
            elif c == '"':
                state = "DOUBLE_QUOTE"
                chars.append(" ")
                i += 1
                continue
            elif c == "'":
                state = "SINGLE_QUOTE"
                chars.append(" ")
                i += 1
                continue
            elif c == "`" and lang in ("typescript", "javascript"):
                state = "BACKTICK"
                chars.append(" ")
                i += 1
                continue
            else:
                chars.append(c)
                i += 1
        elif state == "LINE_COMMENT":
            if c == "\n":
                state = "NORMAL"
                chars.append("\n")
            else:
                chars.append(" ")
            i += 1
        elif state == "BLOCK_COMMENT":
            if c == "*" and nxt == "/":
                state = "NORMAL"
                chars.append("  ")
                i += 2
                continue
            else:
                chars.append("\n" if c == "\n" else " ")
                i += 1
        elif state == "DOUBLE_QUOTE":
            if c == "\\":
                chars.append("  ")
                i += 2
                continue
            elif c == '"':
                state = "NORMAL"
                chars.append(" ")
            else:
                chars.append("\n" if c == "\n" else " ")
            i += 1
        elif state == "SINGLE_QUOTE":
            if c == "\\":
                chars.append("  ")
                i += 2
                continue
            elif c == "'":
                state = "NORMAL"
                chars.append(" ")
            else:
                chars.append("\n" if c == "\n" else " ")
            i += 1
        elif state == "BACKTICK":
            if c == "\\":
                chars.append("  ")
                i += 2
                continue
            elif c == "`":
                state = "NORMAL"
                chars.append(" ")
            else:
                chars.append("\n" if c == "\n" else " ")
            i += 1

    return "".join(chars)


def _find_block_end(lines: List[str], start_idx: int) -> int:
    """Finds the ending line number (1-based) by matching curly braces."""
    depth = 0
    started = False
    for i in range(start_idx, len(lines)):
        line = lines[i]
        for ch in line:
            if ch == "{":
                depth += 1
                started = True
            elif ch == "}":
                depth -= 1
                if started and depth <= 0:
                    return i + 1
    return min(len(lines), start_idx + 10)


def parse_python_ast(source: str, filepath: str) -> List[Dict[str, Any]]:
    """Extracts symbols from Python source using standard ast module with rich type annotations."""
    try:
        tree = ast.parse(source, filename=filepath)
    except IndentationError:
        import textwrap
        tree = ast.parse(textwrap.dedent(source), filename=filepath)
    symbols: List[Dict[str, Any]] = []

    def _format_py_args(args_node: ast.arguments) -> str:
        parts = []
        for a in args_node.args:
            if getattr(a, "annotation", None):
                try:
                    parts.append(f"{a.arg}: {ast.unparse(a.annotation)}")
                except Exception:
                    parts.append(a.arg)
            else:
                parts.append(a.arg)
        return ", ".join(parts)

    def _format_py_return(returns_node: Optional[ast.AST]) -> str:
        if returns_node:
            try:
                return f" -> {ast.unparse(returns_node)}"
            except Exception:
                return ""
        return ""

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            line = node.lineno
            end_line = getattr(node, "end_lineno", line + 10)
            arg_str = _format_py_args(node.args)
            ret_str = _format_py_return(node.returns)
            sig_text = f"{prefix} {node.name}({arg_str}){ret_str}"
            symbols.append({
                "name": node.name,
                "kind": "function",
                "signature": sig_text,
                "line": line,
                "end_line": end_line,
                "anchor": f"[AST: {node.name} | L{line}-L{end_line}]",
                "formatted": f"{sig_text} [AST: {node.name} | L{line}-L{end_line}]"
            })
        elif isinstance(node, ast.ClassDef):
            line = node.lineno
            end_line = getattr(node, "end_lineno", line + 20)
            sig_text = f"class {node.name}"
            symbols.append({
                "name": node.name,
                "kind": "class",
                "signature": sig_text,
                "line": line,
                "end_line": end_line,
                "anchor": f"[AST: {node.name} | L{line}-L{end_line}]",
                "formatted": f"{sig_text} [AST: {node.name} | L{line}-L{end_line}]"
            })
            for subnode in node.body:
                if isinstance(subnode, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    m_prefix = "async def" if isinstance(subnode, ast.AsyncFunctionDef) else "def"
                    m_line = subnode.lineno
                    m_end = getattr(subnode, "end_lineno", m_line + 5)
                    m_args = _format_py_args(subnode.args)
                    m_ret = _format_py_return(subnode.returns)
                    m_sig = f"{node.name}::{subnode.name}({m_args}){m_ret}"
                    symbols.append({
                        "name": f"{node.name}.{subnode.name}",
                        "kind": "method",
                        "signature": m_sig,
                        "line": m_line,
                        "end_line": m_end,
                        "anchor": f"[AST: {node.name}::{subnode.name} | L{m_line}-L{m_end}]",
                        "formatted": f"{m_sig} [AST: {node.name}::{subnode.name} | L{m_line}-L{m_end}]"
                    })

    return symbols


def parse_c_like_symbols(source: str, filepath: str, lang: str) -> List[Dict[str, Any]]:
    """Extracts symbols from TypeScript, JavaScript, Java, Groovy sources."""
    sanitized = strip_comments_and_strings(source, lang)
    lines = sanitized.splitlines()
    orig_lines = source.splitlines()
    symbols: List[Dict[str, Any]] = []

    # Patterns by language with annotation/decorator resilience
    if lang in ("typescript", "javascript"):
        type_pat = re.compile(
            r"^\s*(?:@[A-Za-z0-9_$]+(?:\([^)]*\))?\s*)*(?:export\s+(?:default\s+)?)?(?:class|interface|type|enum)\s+([A-Za-z0-9_$]+)",
            re.M
        )
        fn_pat = re.compile(
            r"^\s*(?:@[A-Za-z0-9_$]+(?:\([^)]*\))?\s*)*(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s*([A-Za-z0-9_$]+)?\s*\(([^)]*)\)",
            re.M
        )
        arrow_pat = re.compile(
            r"^\s*(?:@[A-Za-z0-9_$]+(?:\([^)]*\))?\s*)*(?:export\s+)?(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z0-9_$]+)?\s*=>",
            re.M
        )
        method_pat = re.compile(
            r"^\s*(?:@[A-Za-z0-9_$]+(?:\([^)]*\))?\s*)*(?:public|private|protected|static|async|\s)*\s*([A-Za-z0-9_$]+)\s*\(([^)]*)\)\s*(?::\s*[^;{]+)?\s*\{",
            re.M
        )
    elif lang == "java":
        type_pat = re.compile(
            r"^\s*(?:@[A-Za-z0-9_]+(?:\([^)]*\))?\s*)*(?:public|protected|private|abstract|static|final|\s)*\s*(?:class|interface|enum|record)\s+([A-Za-z0-9_]+)",
            re.M
        )
        fn_pat = None
        arrow_pat = None
        method_pat = re.compile(
            r"^\s*(?:@[A-Za-z0-9_]+(?:\([^)]*\))?\s*)*(?:public|protected|private|static|final|abstract|synchronized|\s)*\s*([A-Za-z0-9_<>[\]]+)\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*(?:throws\s+[^{]+)?\s*\{",
            re.M
        )
    elif lang == "groovy":
        type_pat = re.compile(
            r"^\s*(?:@[A-Za-z0-9_]+(?:\([^)]*\))?\s*)*(?:public|protected|private|abstract|static|final|\s)*\s*(?:class|interface|trait|enum)\s+([A-Za-z0-9_]+)",
            re.M
        )
        fn_pat = None
        arrow_pat = None
        method_pat = re.compile(
            r"^\s*(?:@[A-Za-z0-9_]+(?:\([^)]*\))?\s*)*(?:def|void|[A-Za-z0-9_<>[\]]+)\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*\{",
            re.M
        )
    else:
        return symbols

    # Line by line scanning
    control_keywords = {
        "if", "for", "while", "switch", "catch", "finally", "try",
        "do", "else", "new", "return", "throw", "super", "this"
    }

    seen_anchors = set()

    for idx, line_str in enumerate(lines):
        line_num = idx + 1
        trimmed = line_str.strip()
        if not trimmed:
            continue

        # 1. Classes / Interfaces / Types
        if type_pat:
            m = type_pat.search(line_str)
            if m:
                name = m.group(1)
                if name not in control_keywords and name not in seen_anchors:
                    seen_anchors.add(name)
                    end_line = _find_block_end(lines, idx)
                    orig_first = orig_lines[idx].strip() if idx < len(orig_lines) else trimmed
                    kind = "class" if "class" in line_str else "interface" if "interface" in line_str else "type"
                    sig = orig_first.split("{")[0].strip()
                    symbols.append({
                        "name": name,
                        "kind": kind,
                        "signature": sig,
                        "line": line_num,
                        "end_line": end_line,
                        "anchor": f"[AST: {name} | L{line_num}-L{end_line}]",
                        "formatted": f"{sig} [AST: {name} | L{line_num}-L{end_line}]"
                    })
                    continue

        # 2. Named Functions
        if fn_pat:
            m = fn_pat.search(line_str)
            if m and m.group(1):
                name = m.group(1)
                if name not in control_keywords and name not in seen_anchors:
                    seen_anchors.add(name)
                    end_line = _find_block_end(lines, idx)
                    orig_first = orig_lines[idx].strip() if idx < len(orig_lines) else trimmed
                    sig = orig_first.split("{")[0].strip()
                    symbols.append({
                        "name": name,
                        "kind": "function",
                        "signature": sig,
                        "line": line_num,
                        "end_line": end_line,
                        "anchor": f"[AST: {name} | L{line_num}-L{end_line}]",
                        "formatted": f"{sig} [AST: {name} | L{line_num}-L{end_line}]"
                    })
                    continue

        # 3. Arrow / Assigned Functions
        if arrow_pat:
            m = arrow_pat.search(line_str)
            if m:
                name = m.group(1)
                if name not in control_keywords and name not in seen_anchors:
                    seen_anchors.add(name)
                    end_line = _find_block_end(lines, idx)
                    orig_first = orig_lines[idx].strip() if idx < len(orig_lines) else trimmed
                    sig = orig_first.split("{")[0].strip()
                    symbols.append({
                        "name": name,
                        "kind": "function",
                        "signature": sig,
                        "line": line_num,
                        "end_line": end_line,
                        "anchor": f"[AST: {name} | L{line_num}-L{end_line}]",
                        "formatted": f"{sig} [AST: {name} | L{line_num}-L{end_line}]"
                    })
                    continue

        # 4. Methods
        if method_pat:
            m = method_pat.search(line_str)
            if m:
                if lang == "java":
                    name = m.group(2)
                else:
                    name = m.group(1)
                if name not in control_keywords and name not in seen_anchors:
                    seen_anchors.add(name)
                    end_line = _find_block_end(lines, idx)
                    orig_first = orig_lines[idx].strip() if idx < len(orig_lines) else trimmed
                    sig = orig_first.split("{")[0].strip()
                    symbols.append({
                        "name": name,
                        "kind": "method",
                        "signature": sig,
                        "line": line_num,
                        "end_line": end_line,
                        "anchor": f"[AST: {name} | L{line_num}-L{end_line}]",
                        "formatted": f"{sig} [AST: {name} | L{line_num}-L{end_line}]"
                    })

    return symbols


def parse_json_structural_anchors(source: str, filepath: str) -> List[Dict[str, Any]]:
    """Extracts Hierarchical Key-Path Structural Anchors from JSON configurations."""
    symbols: List[Dict[str, Any]] = []
    lines = source.splitlines()
    key_stack: List[Tuple[int, str]] = []

    for idx, line in enumerate(lines):
        line_num = idx + 1
        m = re.match(r'^(\s*)"([^"]+)"\s*:\s*(.*)$', line)
        if m:
            indent = len(m.group(1))
            key = m.group(2)
            val = m.group(3).strip()
            while key_stack and key_stack[-1][0] >= indent:
                key_stack.pop()
            key_stack.append((indent, key))

            full_path = ".".join(k for _, k in key_stack)
            sig = f'"{full_path}": {val[:40]}'
            symbols.append({
                "name": full_path,
                "kind": "keypath",
                "signature": sig,
                "line": line_num,
                "end_line": line_num,
                "anchor": f"[AST: {full_path} | L{line_num}-L{line_num}]",
                "formatted": f"{sig} [AST: {full_path} | L{line_num}-L{line_num}]"
            })
    return symbols


def parse_yaml_structural_anchors(source: str, filepath: str) -> List[Dict[str, Any]]:
    """Extracts Hierarchical Key-Path Structural Anchors from YAML configurations."""
    symbols: List[Dict[str, Any]] = []
    lines = source.splitlines()
    key_stack: List[Tuple[int, str]] = []

    for idx, line in enumerate(lines):
        line_num = idx + 1
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = re.match(r"^(\s*)([A-Za-z0-9_\-\.]+)\s*:\s*(.*)$", line)
        if m:
            indent = len(m.group(1))
            key = m.group(2)
            val = m.group(3).strip()
            while key_stack and key_stack[-1][0] >= indent:
                key_stack.pop()
            key_stack.append((indent, key))

            full_path = ".".join(k for _, k in key_stack)
            sig = f"{full_path}: {val[:40]}"
            symbols.append({
                "name": full_path,
                "kind": "keypath",
                "signature": sig,
                "line": line_num,
                "end_line": line_num,
                "anchor": f"[AST: {full_path} | L{line_num}-L{line_num}]",
                "formatted": f"{sig} [AST: {full_path} | L{line_num}-L{line_num}]"
            })
    return symbols


def parse_dockerfile_structural_anchors(source: str, filepath: str) -> List[Dict[str, Any]]:
    """Extracts Stage and Directive Structural Anchors from Dockerfiles."""
    symbols: List[Dict[str, Any]] = []
    lines = source.splitlines()
    current_stage = "root"

    for idx, line in enumerate(lines):
        line_num = idx + 1
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m_from = re.match(r"^FROM\s+.*?\s+AS\s+([A-Za-z0-9_\-]+)", stripped, re.IGNORECASE)
        if m_from:
            current_stage = m_from.group(1)
            sym_name = f"STAGE:{current_stage}"
            symbols.append({
                "name": sym_name,
                "kind": "stage",
                "signature": stripped[:60],
                "line": line_num,
                "end_line": line_num,
                "anchor": f"[AST: {sym_name} | L{line_num}-L{line_num}]",
                "formatted": f"{stripped[:60]} [AST: {sym_name} | L{line_num}-L{line_num}]"
            })
            continue

        m_dir = re.match(r"^(RUN|CMD|ENTRYPOINT|EXPOSE|ENV|WORKDIR)\s+(.*)$", stripped, re.IGNORECASE)
        if m_dir:
            d_type = m_dir.group(1).upper()
            d_val = m_dir.group(2).strip()[:30].replace(" ", "_")
            sym_name = f"{current_stage}.{d_type}:{d_val}"
            symbols.append({
                "name": sym_name,
                "kind": "directive",
                "signature": stripped[:60],
                "line": line_num,
                "end_line": line_num,
                "anchor": f"[AST: {sym_name} | L{line_num}-L{line_num}]",
                "formatted": f"{stripped[:60]} [AST: {sym_name} | L{line_num}-L{line_num}]"
            })
    return symbols


def parse_shell_structural_anchors(source: str, filepath: str) -> List[Dict[str, Any]]:
    """Extracts Function Structural Anchors from Shell scripts."""
    symbols: List[Dict[str, Any]] = []
    lines = source.splitlines()

    for idx, line in enumerate(lines):
        line_num = idx + 1
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = re.match(r"^(?:function\s+)?([A-Za-z0-9_\-]+)\s*\(\)\s*\{?", stripped, re.IGNORECASE)
        if m:
            fn_name = m.group(1)
            sym_name = f"function:{fn_name}"
            symbols.append({
                "name": sym_name,
                "kind": "function",
                "signature": stripped[:60],
                "line": line_num,
                "end_line": line_num,
                "anchor": f"[AST: {sym_name} | L{line_num}-L{line_num}]",
                "formatted": f"{stripped[:60]} [AST: {sym_name} | L{line_num}-L{line_num}]"
            })
    return symbols


def parse_polyglot_signatures(filepath: str, repo_root: Optional[str] = None) -> Dict[str, Any]:
    """
    Parses a file in any supported language and extracts AST Structural Anchors.
    Zero external dependencies.
    """
    if repo_root and not os.path.isabs(filepath):
        abs_path = os.path.join(repo_root, filepath)
    else:
        abs_path = os.path.abspath(filepath)

    if not os.path.isfile(abs_path):
        return {
            "exists": False,
            "filepath": filepath,
            "language": "unknown",
            "signatures": [],
            "symbols": []
        }

    lang = detect_language(abs_path)
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()

        if lang == "python":
            symbols = parse_python_ast(source, abs_path)
        elif lang in ("typescript", "javascript", "java", "groovy"):
            symbols = parse_c_like_symbols(source, abs_path, lang)
        elif lang == "json":
            symbols = parse_json_structural_anchors(source, abs_path)
        elif lang == "yaml":
            symbols = parse_yaml_structural_anchors(source, abs_path)
        elif lang == "dockerfile":
            symbols = parse_dockerfile_structural_anchors(source, abs_path)
        elif lang == "shell":
            symbols = parse_shell_structural_anchors(source, abs_path)
        else:
            symbols = []

        formatted_sigs = [s["formatted"] for s in symbols]
        return {
            "exists": True,
            "filepath": filepath,
            "language": lang,
            "signatures": formatted_sigs,
            "symbols": symbols
        }
    except Exception as e:
        return {
            "exists": True,
            "filepath": filepath,
            "language": lang,
            "error": str(e),
            "signatures": [],
            "symbols": []
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Zero-Dependency Polyglot AST Parser")
    parser.add_argument("--file", "-f", required=True, help="Target source file")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    result = parse_polyglot_signatures(args.file)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"File: {result.get('filepath')} ({result.get('language')})")
        if not result.get("exists"):
            print("File not found.")
            return 1
        for sig in result.get("signatures", []):
            print(f"  {sig}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
