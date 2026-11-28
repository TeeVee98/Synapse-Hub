#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Serena-style Semantic Symbol Navigation & Atomic Code Editing Engine.

Provides symbol-level inspection (`get_symbols_overview`, `find_symbol`,
`find_referencing_symbols`) and atomic syntax-verified refactoring
(`replace_symbol_body`, `insert_before_symbol`, `insert_after_symbol`,
`rename_symbol`) backed by Python AST with strict realpath containment.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass
import io
import json
import os
import sys
import tokenize
from typing import Any, Dict, List, Literal, Optional, Sequence

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass

SymbolEditOp = Literal["replace_body", "insert_before", "insert_after", "rename"]


@dataclass(frozen=True)
class SymbolMatchDTO:
    file_path: str
    name_path: str
    symbol_kind: str
    start_line: int
    end_line: int
    body: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SymbolEditReceiptDTO:
    file_path: str
    name_path: str
    operation: SymbolEditOp
    applied: bool
    syntax_valid: bool
    rolled_back: bool
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NamePathMatcher:
    """Serena-style hierarchical symbol name-path matcher (`Class/method`, `/TopLevel`)."""

    def __init__(self, pattern: str) -> None:
        if not isinstance(pattern, str) or not pattern.strip():
            raise ValueError("Name-path pattern must be a non-empty string.")
        cleaned = pattern.strip()
        self.absolute = cleaned.startswith("/")
        self.parts = [p for p in cleaned.strip("/").split("/") if p]
        if not self.parts:
            raise ValueError("Name-path pattern must contain at least one symbol segment.")

    def matches(self, candidate_path: str) -> bool:
        cand_parts = [p for p in str(candidate_path).strip("/").split("/") if p]
        if not cand_parts:
            return False
        if self.absolute:
            return cand_parts == self.parts
        if len(self.parts) > len(cand_parts):
            return False
        return cand_parts[-len(self.parts) :] == self.parts


class SymbolCodeEditor:
    """AST-backed symbol navigator and atomic syntax-checked code editor."""

    def __init__(self, repo_root: str) -> None:
        if not isinstance(repo_root, str) or not repo_root.strip():
            raise ValueError("repo_root must be a non-empty directory path.")
        self.repo_root = os.path.realpath(repo_root)

    def _resolve_safe_file(self, file_path: str) -> str:
        if not isinstance(file_path, str) or not file_path.strip():
            raise ValueError("file_path must be a non-empty string.")
        raw = file_path if os.path.isabs(file_path) else os.path.join(self.repo_root, file_path)
        resolved = os.path.realpath(raw)
        root_norm = os.path.normcase(self.repo_root)
        target_norm = os.path.normcase(resolved)
        if target_norm != root_norm and not target_norm.startswith(root_norm + os.sep):
            raise ValueError(f"Path '{file_path}' resolves outside repo_root '{self.repo_root}'.")
        if not os.path.isfile(resolved):
            raise FileNotFoundError(f"Target file not found: {file_path}")
        return resolved

    def _rel_path(self, abs_path: str) -> str:
        return os.path.relpath(abs_path, self.repo_root).replace("\\", "/")

    def _collect_python_symbols(
        self,
        source: str,
        rel_path: str,
        max_depth: int,
        include_body: bool,
    ) -> List[SymbolMatchDTO]:
        if not source.strip():
            return []
        tree = ast.parse(source)
        lines = source.splitlines()
        results: List[SymbolMatchDTO] = []

        def _visit(nodes: Sequence[ast.stmt], prefix: List[str], cur_depth: int) -> None:
            if cur_depth > max_depth:
                return
            for node in nodes:
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    kind = "class" if isinstance(node, ast.ClassDef) else ("method" if prefix else "function")
                    name_path = "/".join(prefix + [node.name])
                    start = int(getattr(node, "lineno", 1))
                    if getattr(node, "decorator_list", None):
                        dec_lines = [int(getattr(d, "lineno", start)) for d in node.decorator_list]
                        start = min(start, min(dec_lines))
                    end = int(getattr(node, "end_lineno", start))
                    body_text = "\n".join(lines[start - 1 : end]) if include_body else None
                    results.append(
                        SymbolMatchDTO(
                            file_path=rel_path,
                            name_path=name_path,
                            symbol_kind=kind,
                            start_line=start,
                            end_line=end,
                            body=body_text,
                        )
                    )
                    if isinstance(node, ast.ClassDef) and cur_depth < max_depth:
                        _visit(node.body, prefix + [node.name], cur_depth + 1)

        _visit(tree.body, [], 1)
        return results

    def _read_text(self, abs_path: str, errors: str = "strict") -> str:
        with open(abs_path, "r", encoding="utf-8", errors=errors) as fh:
            return fh.read()

    def _iter_target_python_files(self, file_path: Optional[str]) -> List[str]:
        if file_path:
            return [self._resolve_safe_file(file_path)]
        targets: List[str] = []
        for root_dir, dirs, files in os.walk(self.repo_root):
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".venv", "node_modules", ".synapse")]
            for fn in sorted(files):
                if fn.endswith(".py"):
                    targets.append(os.path.join(root_dir, fn))
        return targets

    def get_symbols_overview(self, file_path: str, depth: int = 2) -> List[SymbolMatchDTO]:
        resolved = self._resolve_safe_file(file_path)
        source = self._read_text(resolved)
        return self._collect_python_symbols(source, self._rel_path(resolved), max_depth=max(1, int(depth)), include_body=False)

    def find_symbol(
        self,
        name_path: str,
        file_path: Optional[str] = None,
        include_body: bool = False,
    ) -> List[SymbolMatchDTO]:
        matcher = NamePathMatcher(name_path)
        matches: List[SymbolMatchDTO] = []
        for path in self._iter_target_python_files(file_path):
            source = self._read_text(path, errors="replace")
            try:
                syms = self._collect_python_symbols(source, self._rel_path(path), max_depth=6, include_body=include_body)
            except SyntaxError:
                continue
            matches.extend(sym for sym in syms if matcher.matches(sym.name_path))
        return matches

    def _collect_scope_references(
        self,
        node: ast.AST,
        scope: str,
        target_name: str,
        rel_path: str,
        lines: Sequence[str],
    ) -> List[Dict[str, Any]]:
        hits: List[Dict[str, Any]] = []
        for child in ast.walk(node):
            matched = (isinstance(child, ast.Name) and child.id == target_name) or (
                isinstance(child, ast.Attribute) and child.attr == target_name
            )
            if not matched:
                continue
            ln = int(getattr(child, "lineno", 1))
            hits.append(
                {
                    "file_path": rel_path,
                    "caller_symbol": scope,
                    "line": ln,
                    "snippet": lines[ln - 1].strip() if 0 < ln <= len(lines) else "",
                }
            )
        return hits

    def _iter_scope_nodes(self, tree: ast.Module) -> List[tuple[ast.AST, str]]:
        scopes: List[tuple[ast.AST, str]] = []
        fn_types = (ast.FunctionDef, ast.AsyncFunctionDef)
        for top in tree.body:
            if isinstance(top, fn_types):
                scopes.append((top, top.name))
            elif isinstance(top, ast.ClassDef):
                scopes.extend((sub, f"{top.name}/{sub.name}") for sub in top.body if isinstance(sub, fn_types))
        return scopes

    def _collect_file_references(self, path: str, target_name: str) -> List[Dict[str, Any]]:
        source = self._read_text(path, errors="replace")
        if not source.strip():
            return []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        rel = self._rel_path(path)
        lines = source.splitlines()
        refs: List[Dict[str, Any]] = []
        for node, scope in self._iter_scope_nodes(tree):
            refs.extend(self._collect_scope_references(node, scope, target_name, rel, lines))
        return refs

    def find_referencing_symbols(
        self,
        symbol_name: str,
        file_path: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not isinstance(symbol_name, str) or not symbol_name.strip():
            raise ValueError("symbol_name must be a non-empty string.")
        target_name = symbol_name.strip().split("/")[-1]
        refs: List[Dict[str, Any]] = []
        for path in self._iter_target_python_files(file_path):
            refs.extend(self._collect_file_references(path, target_name))
        return refs

    def _apply_atomic_edit(
        self,
        resolved: str,
        rel_path: str,
        name_path: str,
        operation: SymbolEditOp,
        original_text: str,
        updated_text: str,
    ) -> SymbolEditReceiptDTO:
        with open(resolved, "w", encoding="utf-8") as fh:
            fh.write(updated_text)
        try:
            ast.parse(updated_text)
        except SyntaxError as exc:
            with open(resolved, "w", encoding="utf-8") as fh:
                fh.write(original_text)
            return SymbolEditReceiptDTO(
                file_path=rel_path,
                name_path=name_path,
                operation=operation,
                applied=False,
                syntax_valid=False,
                rolled_back=True,
                error=f"SyntaxError at line {exc.lineno}: {exc.msg}",
            )
        return SymbolEditReceiptDTO(
            file_path=rel_path,
            name_path=name_path,
            operation=operation,
            applied=True,
            syntax_valid=True,
            rolled_back=False,
        )

    def replace_symbol_body(self, file_path: str, name_path: str, new_body: str) -> SymbolEditReceiptDTO:
        resolved = self._resolve_safe_file(file_path)
        rel_path = self._rel_path(resolved)
        original = self._read_text(resolved)
        matches = self.find_symbol(name_path, file_path=resolved, include_body=False)
        if not matches:
            return SymbolEditReceiptDTO(
                file_path=rel_path,
                name_path=name_path,
                operation="replace_body",
                applied=False,
                syntax_valid=True,
                rolled_back=False,
                error=f"Symbol '{name_path}' not found in '{rel_path}'.",
            )
        target = matches[0]
        lines = original.splitlines()
        new_lines = lines[: target.start_line - 1] + new_body.splitlines() + lines[target.end_line :]
        updated = "\n".join(new_lines) + ("\n" if original.endswith("\n") else "")
        return self._apply_atomic_edit(resolved, rel_path, name_path, "replace_body", original, updated)

    def insert_before_symbol(self, file_path: str, name_path: str, snippet: str) -> SymbolEditReceiptDTO:
        resolved = self._resolve_safe_file(file_path)
        rel_path = self._rel_path(resolved)
        original = self._read_text(resolved)
        matches = self.find_symbol(name_path, file_path=resolved, include_body=False)
        if not matches:
            return SymbolEditReceiptDTO(
                file_path=rel_path,
                name_path=name_path,
                operation="insert_before",
                applied=False,
                syntax_valid=True,
                rolled_back=False,
                error=f"Symbol '{name_path}' not found in '{rel_path}'.",
            )
        target = matches[0]
        lines = original.splitlines()
        new_lines = lines[: target.start_line - 1] + snippet.splitlines() + lines[target.start_line - 1 :]
        updated = "\n".join(new_lines) + ("\n" if original.endswith("\n") else "")
        return self._apply_atomic_edit(resolved, rel_path, name_path, "insert_before", original, updated)

    def insert_after_symbol(self, file_path: str, name_path: str, snippet: str) -> SymbolEditReceiptDTO:
        resolved = self._resolve_safe_file(file_path)
        rel_path = self._rel_path(resolved)
        original = self._read_text(resolved)
        matches = self.find_symbol(name_path, file_path=resolved, include_body=False)
        if not matches:
            return SymbolEditReceiptDTO(
                file_path=rel_path,
                name_path=name_path,
                operation="insert_after",
                applied=False,
                syntax_valid=True,
                rolled_back=False,
                error=f"Symbol '{name_path}' not found in '{rel_path}'.",
            )
        target = matches[0]
        lines = original.splitlines()
        new_lines = lines[: target.end_line] + snippet.splitlines() + lines[target.end_line :]
        updated = "\n".join(new_lines) + ("\n" if original.endswith("\n") else "")
        return self._apply_atomic_edit(resolved, rel_path, name_path, "insert_after", original, updated)

    def _replace_identifier_tokens(self, source: str, old_name: str, new_name: str) -> str:
        """Replaces only Python NAME tokens matching old_name, preserving strings and comments."""
        lines = source.splitlines(keepends=True)
        offsets: List[int] = []
        pos = 0
        for ln in lines:
            offsets.append(pos)
            pos += len(ln)
        spans: List[tuple[int, int]] = []
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.NAME and tok.string == old_name:
                start_abs = offsets[tok.start[0] - 1] + tok.start[1]
                end_abs = offsets[tok.end[0] - 1] + tok.end[1]
                spans.append((start_abs, end_abs))
        out = source
        for start_abs, end_abs in reversed(spans):
            out = out[:start_abs] + new_name + out[end_abs:]
        return out

    def rename_symbol(self, file_path: str, name_path: str, new_name: str) -> SymbolEditReceiptDTO:
        resolved = self._resolve_safe_file(file_path)
        rel_path = self._rel_path(resolved)
        if not isinstance(new_name, str) or not new_name.isidentifier():
            return SymbolEditReceiptDTO(
                file_path=rel_path,
                name_path=name_path,
                operation="rename",
                applied=False,
                syntax_valid=True,
                rolled_back=False,
                error=f"Invalid Python identifier for rename: '{new_name}'.",
            )
        original = self._read_text(resolved)
        matches = self.find_symbol(name_path, file_path=resolved, include_body=False)
        if not matches:
            return SymbolEditReceiptDTO(
                file_path=rel_path,
                name_path=name_path,
                operation="rename",
                applied=False,
                syntax_valid=True,
                rolled_back=False,
                error=f"Symbol '{name_path}' not found in '{rel_path}'.",
            )
        old_name = matches[0].name_path.split("/")[-1]
        updated = self._replace_identifier_tokens(original, old_name, new_name)
        return self._apply_atomic_edit(resolved, rel_path, name_path, "rename", original, updated)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Synapse Hub Serena-Style Semantic Symbol Code Editor")
    parser.add_argument("--repo-root", default=os.getcwd())
    sub = parser.add_subparsers(dest="command")

    p_ov = sub.add_parser("overview")
    p_ov.add_argument("--file", required=True)
    p_ov.add_argument("--depth", type=int, default=2)
    p_ov.add_argument("--json", action="store_true")

    p_fn = sub.add_parser("find")
    p_fn.add_argument("--name-path", required=True)
    p_fn.add_argument("--file", default=None)
    p_fn.add_argument("--include-body", action="store_true")
    p_fn.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    editor = SymbolCodeEditor(repo_root=args.repo_root)
    if args.command == "overview":
        syms = editor.get_symbols_overview(args.file, depth=args.depth)
        payload = {"status": "ok", "symbols": [s.to_dict() for s in syms]}
    else:
        syms = editor.find_symbol(args.name_path, file_path=args.file, include_body=args.include_body)
        payload = {"status": "ok", "symbols": [s.to_dict() for s in syms]}

    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2))
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
