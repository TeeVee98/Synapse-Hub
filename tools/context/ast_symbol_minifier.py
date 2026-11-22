#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tools/context/ast_symbol_minifier.py — Tier 8 Reversible AST Symbol Aliasing & Minification
------------------------------------------------------------------------------------------
Optimizes prompt token consumption by minifying Python source code via:
  1. AST Symbol Aliasing: Maps long identifiers to short aliases (v1, v2, f1, p1, c1...)
     paired with a reversible alias dictionary.
  2. Reversible Patch De-Aliasing: Restores 100% of original identifiers from code
     patches / search-and-replace blocks before disk commits.
  3. Whitespace & Comment Stripping: Compresses indentation (4 spaces -> 1 tab) and
     removes non-essential comments while strictly preserving Author Attribution headers,
     shebangs, and compiler directives (# noqa, # type: ignore, # pragma:, # pylint:).
  4. Activation Threshold: Automatically activates only for files > 300 LOC (with force option).
"""

from __future__ import annotations

import argparse
import ast
import builtins
import io
import json
import os
import re
import sys
import tokenize
from typing import Any, Dict, List, Optional, Set, Tuple

# Enforce UTF-8 stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Optional Token Estimator integration
try:
    from tools.core.token_estimator import count_tokens
except ImportError:
    def count_tokens(text: str) -> int:
        return max(1, len(text) // 4)


class _ASTSymbolVisitor(ast.NodeVisitor):
    """AST Visitor that semantically discovers functions, classes, params, and variables."""

    def __init__(self, denylist: Set[str], min_len: int = 4):
        self.denylist = set(denylist)
        self.min_len = min_len
        self.functions: List[str] = []
        self.classes: List[str] = []
        self.params: List[str] = []
        self.variables: List[str] = []

    def _is_eligible(self, name: str) -> bool:
        if not name or len(name) < self.min_len:
            return False
        if name.startswith("__") and name.endswith("__"):
            return False
        if name in self.denylist or name in ("self", "cls", "main"):
            return False
        return True

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self.denylist.add(name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            name = alias.asname or alias.name
            self.denylist.add(name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if self._is_eligible(node.name):
            self.functions.append(node.name)
        self._extract_args(node.args)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if self._is_eligible(node.name):
            self.functions.append(node.name)
        self._extract_args(node.args)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if self._is_eligible(node.name):
            self.classes.append(node.name)
        self.generic_visit(node)

    def _extract_args(self, args_node: ast.arguments) -> None:
        all_args = list(args_node.posonlyargs) + list(args_node.args) + list(args_node.kwonlyargs)
        if args_node.vararg:
            all_args.append(args_node.vararg)
        if args_node.kwarg:
            all_args.append(args_node.kwarg)
        for a in all_args:
            if self._is_eligible(a.arg):
                self.params.append(a.arg)

    def _extract_target(self, target: Any) -> None:
        if isinstance(target, ast.Name):
            if self._is_eligible(target.id):
                self.variables.append(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._extract_target(elt)

    def visit_Assign(self, node: ast.Assign) -> None:
        for t in node.targets:
            self._extract_target(t)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._extract_target(node.target)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._extract_target(node.target)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._extract_target(node.target)
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._extract_target(node.target)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            if item.optional_vars:
                self._extract_target(item.optional_vars)
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        for item in node.items:
            if item.optional_vars:
                self._extract_target(item.optional_vars)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name and self._is_eligible(node.name):
            self.variables.append(node.name)
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self._extract_target(node.target)
        self.generic_visit(node)


class ASTSymbolMinifier:
    """Tier 8 Tokenizer-Level AST Compression & Reversible Aliasing Engine."""

    ACTIVATION_THRESHOLD_LOC: int = 300
    MIN_IDENTIFIER_LEN: int = 4

    BUILTIN_DENYLIST: Set[str] = {
        "print", "len", "range", "enumerate", "zip", "open", "type", "isinstance",
        "issubclass", "super", "hasattr", "getattr", "setattr", "delattr", "iter",
        "next", "min", "max", "sum", "abs", "round", "repr", "id", "hash", "sorted",
        "reversed", "slice", "classmethod", "staticmethod", "property", "object",
        "int", "float", "str", "bool", "list", "dict", "set", "tuple", "bytes",
        "bytearray", "memoryview", "complex", "frozenset", "map", "filter", "all",
        "any", "ascii", "bin", "callable", "chr", "compile", "dir", "divmod", "eval",
        "exec", "format", "globals", "help", "hex", "input", "locals", "oct", "ord",
        "pow", "vars",
        "Exception", "BaseException", "ValueError", "TypeError", "KeyError", "IndexError",
        "AttributeError", "RuntimeError", "ImportError", "OSError", "FileNotFoundError",
        "SyntaxError", "StopIteration", "ZeroDivisionError", "AssertionError", "NameError",
        "NotImplementedError", "KeyboardInterrupt", "SystemExit", "TimeoutError",
        "True", "False", "None", "self", "cls", "main"
    } | set(dir(builtins))

    ESSENTIAL_COMMENT_KEYWORDS: Tuple[str, ...] = (
        "spdx", "thế vị", "teevee98", "copyright", "license",
        "noqa", "type: ignore", "pragma:", "pylint:", "synapse-ignore"
    )

    @classmethod
    def should_activate(
        cls, source_code: str, force: bool = False, threshold: Optional[int] = None
    ) -> bool:
        """Checks if file meets the LOC threshold rule (> 300 LOC or force=True)."""
        if force:
            return True
        loc_limit = threshold if threshold is not None else cls.ACTIVATION_THRESHOLD_LOC
        return len(source_code.splitlines()) > loc_limit

    @classmethod
    def is_essential_comment(cls, comment_text: str) -> bool:
        """Determines if a comment contains license, author, or compiler directives."""
        if not comment_text:
            return False
        if comment_text.startswith("#!"):
            return True
        lowered = comment_text.lower()
        return any(kw in lowered for kw in cls.ESSENTIAL_COMMENT_KEYWORDS)

    @classmethod
    def strip_non_essential_comments(cls, source_code: str) -> str:
        """Strips explanatory comments while strictly preserving license headers and directives."""
        if not source_code:
            return ""
        lines = source_code.splitlines(keepends=True)
        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(source_code).readline))
        except Exception:
            return source_code

        line_comments: Dict[int, tokenize.TokenInfo] = {}
        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                if not cls.is_essential_comment(tok.string):
                    line_comments[tok.start[0]] = tok

        result_lines: List[str] = []
        for idx, line in enumerate(lines, start=1):
            if idx in line_comments:
                tok = line_comments[idx]
                col = tok.start[1]
                code_part = line[:col].rstrip()
                if code_part:
                    newline = "\n" if line.endswith("\n") else ""
                    result_lines.append(code_part + newline)
                else:
                    # Full line was an explanatory comment; omit
                    pass
            else:
                result_lines.append(line)

        return "".join(result_lines)

    @classmethod
    def spaces_to_tabs(cls, source_code: str) -> str:
        """Converts leading 4 spaces to 1 tab (\t)."""
        if not source_code:
            return ""
        result: List[str] = []
        for line in source_code.splitlines(keepends=True):
            stripped = line.lstrip(" ")
            space_count = len(line) - len(stripped)
            if space_count > 0:
                tabs = space_count // 4
                rem_spaces = space_count % 4
                result.append("\t" * tabs + " " * rem_spaces + stripped)
            else:
                result.append(line)
        return "".join(result)

    @classmethod
    def tabs_to_spaces(cls, source_code: str) -> str:
        """Restores leading tabs (\t) to standard 4 spaces."""
        if not source_code:
            return ""
        result: List[str] = []
        for line in source_code.splitlines(keepends=True):
            stripped = line.lstrip("\t")
            tab_count = len(line) - len(stripped)
            if tab_count > 0:
                result.append("    " * tab_count + stripped)
            else:
                result.append(line)
        return "".join(result)

    @classmethod
    def extract_symbols(
        cls, source_code: str, min_len: Optional[int] = None
    ) -> Tuple[List[str], List[str], List[str], List[str]]:
        """Parses AST to identify functions, classes, parameters, and local variables."""
        if not source_code or not source_code.strip():
            return [], [], [], []

        effective_min_len = min_len if min_len is not None else cls.MIN_IDENTIFIER_LEN

        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return [], [], [], []

        extractor = _ASTSymbolVisitor(
            denylist=cls.BUILTIN_DENYLIST, min_len=effective_min_len
        )
        extractor.visit(tree)

        funcs = list(dict.fromkeys(extractor.functions))
        classes = [c for c in list(dict.fromkeys(extractor.classes)) if c not in funcs]
        params = [
            p for p in list(dict.fromkeys(extractor.params))
            if p not in funcs and p not in classes
        ]
        variables = [
            v for v in list(dict.fromkeys(extractor.variables))
            if v not in funcs and v not in classes and v not in params
        ]

        return funcs, classes, params, variables

    @classmethod
    def build_alias_map(
        cls,
        functions: List[str],
        classes: List[str],
        params: List[str],
        variables: List[str],
        existing_identifiers: Optional[Set[str]] = None,
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Maps functions to f1, classes to c1, params to p1, variables to v1."""
        alias_map: Dict[str, str] = {}
        reverse_map: Dict[str, str] = {}
        used_aliases: Set[str] = set(existing_identifiers or set())

        def _get_next_alias(prefix: str, start_idx: int) -> Tuple[str, int]:
            idx = start_idx
            while True:
                candidate = f"{prefix}{idx}"
                idx += 1
                if candidate not in used_aliases and candidate not in reverse_map:
                    used_aliases.add(candidate)
                    return candidate, idx

        f_idx = 1
        for func in functions:
            if func not in alias_map:
                alias, f_idx = _get_next_alias("f", f_idx)
                alias_map[func] = alias
                reverse_map[alias] = func

        c_idx = 1
        for cls_name in classes:
            if cls_name not in alias_map:
                alias, c_idx = _get_next_alias("c", c_idx)
                alias_map[cls_name] = alias
                reverse_map[alias] = cls_name

        p_idx = 1
        for param in params:
            if param not in alias_map:
                alias, p_idx = _get_next_alias("p", p_idx)
                alias_map[param] = alias
                reverse_map[alias] = param

        v_idx = 1
        for var in variables:
            if var not in alias_map:
                alias, v_idx = _get_next_alias("v", v_idx)
                alias_map[var] = alias
                reverse_map[alias] = var

        return alias_map, reverse_map

    @classmethod
    def minify(
        cls,
        source_code: str,
        file_path: Optional[str] = None,
        force: bool = False,
        threshold: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Executes full Tier 8 minification pipeline.
        Returns:
            {
                "activated": bool,
                "original_chars": int,
                "minified_chars": int,
                "saved_tokens": int,
                "alias_map": Dict[str, str],
                "reverse_map": Dict[str, str],
                "minified_code": str
            }
        """
        orig_chars = len(source_code)
        if not source_code or not source_code.strip():
            return {
                "activated": False,
                "original_chars": orig_chars,
                "minified_chars": orig_chars,
                "saved_tokens": 0,
                "alias_map": {},
                "reverse_map": {},
                "minified_code": source_code,
            }

        if not cls.should_activate(source_code, force=force, threshold=threshold):
            return {
                "activated": False,
                "original_chars": orig_chars,
                "minified_chars": orig_chars,
                "saved_tokens": 0,
                "alias_map": {},
                "reverse_map": {},
                "minified_code": source_code,
            }

        try:
            ast.parse(source_code)
        except SyntaxError:
            return {
                "activated": False,
                "original_chars": orig_chars,
                "minified_chars": orig_chars,
                "saved_tokens": 0,
                "alias_map": {},
                "reverse_map": {},
                "minified_code": source_code,
            }

        cleaned = cls.strip_non_essential_comments(source_code)
        funcs, classes, params, variables = cls.extract_symbols(cleaned)

        existing_tokens: Set[str] = set()
        try:
            tokens_for_scan = list(tokenize.generate_tokens(io.StringIO(cleaned).readline))
            existing_tokens = {tok.string for tok in tokens_for_scan if tok.type == tokenize.NAME}
        except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
            existing_tokens = set()

        alias_map, reverse_map = cls.build_alias_map(
            funcs, classes, params, variables, existing_identifiers=existing_tokens
        )

        if not alias_map:
            tabbed = cls.spaces_to_tabs(cleaned)
            minified_chars = len(tabbed)
            orig_toks = count_tokens(source_code)
            mini_toks = count_tokens(tabbed)
            saved = max(0, orig_toks - mini_toks)
            return {
                "activated": True,
                "original_chars": orig_chars,
                "minified_chars": minified_chars,
                "saved_tokens": saved,
                "alias_map": {},
                "reverse_map": {},
                "minified_code": tabbed,
            }

        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(cleaned).readline))
            new_tokens = []
            prev_tok: Optional[tokenize.TokenInfo] = None
            prev_prev_tok: Optional[tokenize.TokenInfo] = None

            for tok in tokens:
                if tok.type == tokenize.NAME and tok.string in alias_map:
                    if prev_tok and prev_tok.string == ".":
                        if prev_prev_tok and prev_prev_tok.string in ("self", "cls"):
                            new_tokens.append(
                                tokenize.TokenInfo(
                                    tok.type, alias_map[tok.string], tok.start, tok.end, tok.line
                                )
                            )
                        else:
                            new_tokens.append(tok)
                    else:
                        new_tokens.append(
                            tokenize.TokenInfo(
                                tok.type, alias_map[tok.string], tok.start, tok.end, tok.line
                            )
                        )
                else:
                    new_tokens.append(tok)

                if tok.type not in (tokenize.NL, tokenize.COMMENT):
                    prev_prev_tok = prev_tok
                    prev_tok = tok

            untokenized = tokenize.untokenize(new_tokens)
        except Exception:
            sorted_keys = sorted(alias_map.keys(), key=len, reverse=True)
            pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted_keys) + r")\b")
            untokenized = pattern.sub(lambda m: alias_map[m.group(1)], cleaned)

        minified_code = cls.spaces_to_tabs(untokenized)
        minified_chars = len(minified_code)

        orig_toks = count_tokens(source_code)
        mini_toks = count_tokens(minified_code)
        saved_tokens = max(0, orig_toks - mini_toks)

        return {
            "activated": True,
            "original_chars": orig_chars,
            "minified_chars": minified_chars,
            "saved_tokens": saved_tokens,
            "alias_map": alias_map,
            "reverse_map": reverse_map,
            "minified_code": minified_code,
        }

    @classmethod
    def restore(cls, minified_patch_or_code: str, reverse_map: Dict[str, str]) -> str:
        """
        Restores 100% of original identifiers and expands tabs to standard 4 spaces.
        Supports full source code as well as search/replace diff blocks.
        """
        if not minified_patch_or_code:
            return ""

        expanded = cls.tabs_to_spaces(minified_patch_or_code)

        if not reverse_map:
            return expanded

        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(expanded).readline))
            new_tokens = []
            for tok in tokens:
                if tok.type == tokenize.NAME and tok.string in reverse_map:
                    new_tokens.append(
                        tokenize.TokenInfo(
                            tok.type, reverse_map[tok.string], tok.start, tok.end, tok.line
                        )
                    )
                else:
                    new_tokens.append(tok)
            return tokenize.untokenize(new_tokens)
        except Exception:
            sorted_aliases = sorted(reverse_map.keys(), key=len, reverse=True)
            pattern = re.compile(
                r"\b(" + "|".join(re.escape(k) for k in sorted_aliases) + r")\b"
            )
            return pattern.sub(lambda m: reverse_map[m.group(1)], expanded)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tier 8 Reversible AST Symbol Aliasing & Minification Engine"
    )
    parser.add_argument(
        "--file", "-f", type=str, help="Path to input Python source file or patch"
    )
    parser.add_argument(
        "--minify", action="store_true", help="Minify source code"
    )
    parser.add_argument(
        "--restore", action="store_true", help="Restore minified code or patch"
    )
    parser.add_argument(
        "--alias-map", "-m", type=str, help="Path to JSON file or JSON string containing alias_map or reverse_map"
    )
    parser.add_argument(
        "--threshold", type=int, default=300, help="LOC activation threshold (default: 300)"
    )
    parser.add_argument(
        "--force", action="store_true", help="Force minification regardless of LOC threshold"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output result as JSON"
    )

    args = parser.parse_args()

    content = ""
    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8") as fh:
            content = fh.read()
    elif not sys.stdin.isatty():
        content = sys.stdin.read()
    else:
        parser.print_help()
        sys.exit(0)

    if args.restore:
        rev_map: Dict[str, str] = {}
        if args.alias_map:
            if os.path.exists(args.alias_map):
                with open(args.alias_map, "r", encoding="utf-8") as fh:
                    raw_data = json.load(fh)
            else:
                try:
                    raw_data = json.loads(args.alias_map)
                except Exception as e:
                    print(f"Error parsing --alias-map JSON: {e}", file=sys.stderr)
                    sys.exit(1)

            if isinstance(raw_data, dict):
                if "reverse_map" in raw_data and isinstance(raw_data["reverse_map"], dict):
                    rev_map = raw_data["reverse_map"]
                elif "alias_map" in raw_data and isinstance(raw_data["alias_map"], dict):
                    rev_map = {v: k for k, v in raw_data["alias_map"].items()}
                else:
                    sample_k = next(iter(raw_data.keys()), "")
                    if re.match(r"^[fcpv]\d+$", sample_k):
                        rev_map = raw_data
                    else:
                        rev_map = {v: k for k, v in raw_data.items()}

        restored = ASTSymbolMinifier.restore(content, rev_map)
        if args.json:
            print(json.dumps({"status": "SUCCESS", "restored_code": restored}, indent=2))
        else:
            sys.stdout.write(restored)
        sys.exit(0)

    # Minify action (default)
    result = ASTSymbolMinifier.minify(
        content,
        file_path=args.file,
        force=args.force,
        threshold=args.threshold,
    )

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["activated"]:
            sys.stdout.write(result["minified_code"])
        else:
            print(
                f"[ASTSymbolMinifier] File below threshold ({len(content.splitlines())} <= {args.threshold} LOC). "
                "Use --force to minify.",
                file=sys.stderr,
            )
            sys.stdout.write(content)


if __name__ == "__main__":
    main()
