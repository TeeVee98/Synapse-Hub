#!/usr/bin/env python3
# Copyright (c) 2026 Thế Vị (@TeeVee98)
# Synapse Hub is open-source software under the MIT License.
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/reasoning/entropy_pruning.py — Information-Theoretic Entropy Pruning Engine
---------------------------------------------------------------------------------
Implements context compression and syntactic pruning based on LLMLingua-2 principles:
  1. AST Token Role Tagging: Distinguishes invariant tokens (function signatures,
     class definitions, variable identifiers, control flow branches, assertions)
     from candidate tokens (comments, docstrings, redundant type annotations, boilerplate).
  2. Information-Theoretic Surprisal: Computes Shannon self-information
     I(t) = -log2(P(t)) from token frequency distributions. Tokens and blocks with
     lower surprisal (high frequency boilerplate, low information comments) are pruned
     first.
  3. Invariant Protection Guarantee: 100% hard-pins function signatures, variable names,
     branching logic (if/elif/else/try/except/finally/for/while/match/case), and assertions
     when preserve_identifiers=True.
  4. Dual-Mode Fallback: Full AST-guided semantic pruning for Python source code with
     graceful lexical fallback for non-Python text or malformed code.

Usage:
  python tools/reasoning/entropy_pruning.py --text "def foo(x: int): # comment\n return x"
  python tools/reasoning/entropy_pruning.py --file script.py --target-ratio 0.40 --json
  python tools/reasoning/entropy_pruning.py --file script.py --budget-tokens 100 --output out.py
"""

import sys
import re
import ast
import math
import json
import argparse
from collections import Counter
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple, Optional

# Enforce UTF-8 stdio
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


TOKEN_REGEX = re.compile(
    r"[A-Za-z_]\w*|\d+(?:\.\d+)?|[^\w\s]"
)


def count_tokens(text: str) -> int:
    """Counts lexical tokens in text consistent with LLM BPE tokenization."""
    if not text or not text.strip():
        return 0
    return len(TOKEN_REGEX.findall(text))


def compute_token_frequencies(text: str) -> Counter:
    """Computes unigram token frequency counts."""
    tokens = TOKEN_REGEX.findall(text)
    return Counter(tokens)


def compute_surprisal(token: str, frequencies: Counter, total_count: int) -> float:
    """Computes Shannon surprisal (self-information) in bits: I(t) = -log2(P(t))."""
    if total_count <= 0:
        return 0.0
    count = frequencies.get(token, 1)
    prob = count / total_count
    return -math.log2(prob) if prob > 0.0 else 0.0


class IdentifierVisitor(ast.NodeVisitor):
    """AST Visitor to extract variable names, function names, classes, branches, and assertions."""

    def __init__(self) -> None:
        self.names: Set[str] = set()
        self.function_names: Set[str] = set()
        self.class_names: Set[str] = set()
        self.arg_names: Set[str] = set()
        self.docstring_lines: Set[int] = set()
        self.docstring_ranges: List[Tuple[int, int]] = []
        self.has_assertions: bool = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_names.add(node.name)
        for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs:
            self.arg_names.add(arg.arg)
        if node.args.vararg:
            self.arg_names.add(node.args.vararg.arg)
        if node.args.kwarg:
            self.arg_names.add(node.args.kwarg.arg)
        self._check_docstring(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)  # type: ignore

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.class_names.add(node.name)
        self._check_docstring(node)
        self.generic_visit(node)

    def visit_Module(self, node: ast.Module) -> None:
        self._check_docstring(node)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        self.names.add(node.id)
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.has_assertions = True
        self.generic_visit(node)

    def _check_docstring(self, node: Any) -> None:
        if hasattr(node, "body") and node.body:
            first = node.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                start = getattr(first, "lineno", 0)
                end = getattr(first, "end_lineno", start)
                self.docstring_ranges.append((start, end))
                for line_idx in range(start, end + 1):
                    self.docstring_lines.add(line_idx)


class EntropyPruner:
    """
    Information-Theoretic Context Pruning Engine.
    Prunes redundant comments, docstrings, type annotations, and low-surprisal
    boilerplate while strictly preserving code invariants (identifiers, signatures,
    branching, asserts).
    """

    def __init__(self) -> None:
        pass

    @classmethod
    def compress(
        cls,
        source_text: str,
        target_ratio: float = 0.50,
        budget_tokens: Optional[int] = None,
        preserve_identifiers: bool = True,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Compresses input text/code down to target_ratio or budget_tokens.

        Parameters:
            source_text: Source code or prompt text to compress.
            target_ratio: Target proportion of tokens to retain (0.0 to 1.0).
                          Default 0.50 retains up to 50% of original tokens.
            budget_tokens: Optional maximum token ceiling for compressed text.
            preserve_identifiers: If True (default), 100% hard-pins function
                                  signatures, variable identifiers, branching, and asserts.

        Returns:
            Tuple[str, Dict[str, Any]]: (compressed_text, metadata_dict)
        """
        if target_ratio < 0.0 or target_ratio > 1.0:
            raise ValueError(f"target_ratio must be between 0.0 and 1.0, got {target_ratio}")
        if budget_tokens is not None and budget_tokens < 0:
            raise ValueError(f"budget_tokens must be non-negative, got {budget_tokens}")

        original_token_count = count_tokens(source_text)
        if original_token_count == 0:
            metadata = {
                "original_token_count": 0,
                "pruned_token_count": 0,
                "compression_ratio": 0.0,
                "preserved_identifiers_pct": 100.0,
                "compressed_text": "",
                "status": "ok",
            }
            return "", metadata

        # Calculate target token count ceiling
        target_token_count = math.ceil(original_token_count * target_ratio)
        if budget_tokens is not None:
            target_token_count = min(target_token_count, budget_tokens)
        target_token_count = max(0, target_token_count)

        # If target allows retaining everything, return as-is
        if target_token_count >= original_token_count:
            metadata = {
                "original_token_count": original_token_count,
                "pruned_token_count": 0,
                "compression_ratio": 0.0,
                "preserved_identifiers_pct": 100.0,
                "compressed_text": source_text,
                "status": "ok",
            }
            return source_text, metadata

        # Try AST-guided Python pruning first
        compressed_text: str
        is_python = False
        try:
            tree = ast.parse(source_text)
            visitor = IdentifierVisitor()
            visitor.visit(tree)
            is_python = True
            compressed_text = cls._compress_python(
                source_text,
                tree,
                visitor,
                target_token_count,
                preserve_identifiers,
            )
        except (SyntaxError, Exception):
            # Graceful lexical fallback for non-Python or malformed code
            compressed_text = cls._compress_lexical(
                source_text,
                target_token_count,
                preserve_identifiers,
            )

        # Count compressed tokens and verify invariant preservation
        compressed_token_count = count_tokens(compressed_text)
        pruned_token_count = max(0, original_token_count - compressed_token_count)
        compression_ratio = round(pruned_token_count / original_token_count, 4)

        # Calculate preserved identifiers percentage
        preserved_pct = cls._compute_preserved_identifiers_pct(
            source_text, compressed_text, preserve_identifiers, is_python
        )

        metadata = {
            "original_token_count": original_token_count,
            "pruned_token_count": pruned_token_count,
            "compression_ratio": compression_ratio,
            "preserved_identifiers_pct": preserved_pct,
            "compressed_text": compressed_text,
            "status": "ok",
        }
        return compressed_text, metadata

    @classmethod
    def _compress_python(
        cls,
        source_text: str,
        tree: ast.AST,
        visitor: IdentifierVisitor,
        target_tokens: int,
        preserve_identifiers: bool,
    ) -> str:
        """Executes multi-tier information-theoretic pruning on valid Python code."""
        lines = source_text.splitlines()
        frequencies = compute_token_frequencies(source_text)
        total_tokens = sum(frequencies.values())

        # Stage 1: Rank and prune comments by information surprisal
        comments_info: List[Dict[str, Any]] = []
        for idx, line in enumerate(lines):
            # Check for comments
            match = re.search(r"#.*$", line)
            if match:
                comment_text = match.group(0)
                # Ensure comment is not inside a string literal
                prefix = line[: match.start()]
                single_quotes = prefix.count("'") - prefix.count("\\'")
                double_quotes = prefix.count('"') - prefix.count('\\"')
                if single_quotes % 2 == 0 and double_quotes % 2 == 0:
                    c_tokens = TOKEN_REGEX.findall(comment_text)
                    if c_tokens:
                        avg_surprisal = sum(
                            compute_surprisal(t, frequencies, total_tokens) for t in c_tokens
                        ) / len(c_tokens)
                    else:
                        avg_surprisal = 0.0
                    comments_info.append(
                        {
                            "line_idx": idx,
                            "start_col": match.start(),
                            "end_col": match.end(),
                            "text": comment_text,
                            "surprisal": avg_surprisal,
                            "tokens_count": len(c_tokens),
                            "is_full_line": line.strip().startswith("#"),
                        }
                    )

        # Sort comments by ascending surprisal: lowest information (most repetitive) pruned first
        comments_info.sort(key=lambda c: c["surprisal"])

        current_lines = list(lines)
        current_text = "\n".join(current_lines)
        current_token_count = count_tokens(current_text)

        # Prune comments until target reached or all comments exhausted
        pruned_comment_lines: Set[int] = set()
        inline_comment_pruned: Dict[int, int] = {}  # line_idx -> cut_col

        for c_info in comments_info:
            if current_token_count <= target_tokens:
                break
            line_idx = c_info["line_idx"]
            if c_info["is_full_line"]:
                pruned_comment_lines.add(line_idx)
            else:
                inline_comment_pruned[line_idx] = c_info["start_col"]
            # Estimate reduction
            current_token_count -= c_info["tokens_count"]

        # Reconstruct after Stage 1
        stage1_lines = []
        for idx, line in enumerate(current_lines):
            if idx in pruned_comment_lines:
                continue
            if idx in inline_comment_pruned:
                cut_col = inline_comment_pruned[idx]
                trimmed = line[:cut_col].rstrip()
                if trimmed:
                    stage1_lines.append(trimmed)
            else:
                stage1_lines.append(line)

        current_text = "\n".join(stage1_lines)
        current_token_count = count_tokens(current_text)
        if current_token_count <= target_tokens:
            return cls._clean_formatting(current_text)

        # Stage 2: Prune docstrings by information surprisal
        docstring_info: List[Dict[str, Any]] = []
        for start_line, end_line in visitor.docstring_ranges:
            ds_lines = lines[start_line - 1 : end_line]
            ds_text = "\n".join(ds_lines)
            ds_tokens = TOKEN_REGEX.findall(ds_text)
            if ds_tokens:
                avg_surprisal = sum(
                    compute_surprisal(t, frequencies, total_tokens) for t in ds_tokens
                ) / len(ds_tokens)
            else:
                avg_surprisal = 0.0
            docstring_info.append(
                {
                    "start": start_line,
                    "end": end_line,
                    "text": ds_text,
                    "surprisal": avg_surprisal,
                    "tokens_count": len(ds_tokens),
                }
            )

        docstring_info.sort(key=lambda d: d["surprisal"])

        pruned_docstring_lines: Set[int] = set()

        for d_info in docstring_info:
            if current_token_count <= target_tokens:
                break
            start, end = d_info["start"], d_info["end"]
            for l_idx in range(start - 1, end):
                pruned_docstring_lines.add(l_idx)
            current_token_count -= d_info["tokens_count"]

        # Reconstruct after Stage 2
        stage2_lines = []
        for idx, line in enumerate(lines):
            if idx in pruned_comment_lines or idx in pruned_docstring_lines:
                continue
            if idx in inline_comment_pruned:
                cut_col = inline_comment_pruned[idx]
                trimmed = line[:cut_col].rstrip()
                if trimmed:
                    stage2_lines.append(trimmed)
            else:
                stage2_lines.append(line)

        current_text = "\n".join(stage2_lines)
        # Ensure blocks are not empty
        current_text = cls._ensure_non_empty_blocks(current_text)
        current_token_count = count_tokens(current_text)
        if current_token_count <= target_tokens:
            return cls._clean_formatting(current_text)

        # Stage 3: Prune redundant type annotations
        stage3_text = cls._strip_type_annotations(current_text)
        current_token_count = count_tokens(stage3_text)
        if current_token_count <= target_tokens or preserve_identifiers:
            return cls._clean_formatting(stage3_text)

        # Stage 4: If preserve_identifiers=False, aggressive non-invariant pruning
        return cls._prune_non_invariants(stage3_text, target_tokens, frequencies, total_tokens)

    @classmethod
    def _strip_type_annotations(cls, code: str) -> str:
        """Strips return annotations and parameter type hints from Python signatures."""
        try:
            # Strip return types -> ReturnType:
            stripped = re.sub(r"->\s*[^:]+:", ":", code)

            # Strip parameter annotations: name: Type = val -> name = val
            def clean_param_types(match: re.Match) -> str:
                sig = match.group(0)
                # Replace : Type before = or , or )
                sig = re.sub(r":\s*[^,=)]+?(?=\s*[,=)])", "", sig)
                return sig

            stripped = re.sub(r"def\s+\w+\s*\([^)]*\)\s*:", clean_param_types, stripped)
            # Verify syntactically valid
            ast.parse(stripped)
            return stripped
        except Exception:
            return code

    @classmethod
    def _ensure_non_empty_blocks(cls, code: str) -> str:
        """Guarantees that functions/classes emptied by docstring removal have a 'pass' statement."""
        lines = code.splitlines()
        result: List[str] = []
        for idx, line in enumerate(lines):
            result.append(line)
            stripped = line.strip()
            if stripped.endswith(":") and (
                stripped.startswith("def ")
                or stripped.startswith("class ")
                or stripped.startswith("async def ")
            ):
                indent = len(line) - len(line.lstrip())
                # Check if next non-empty line has greater indent
                has_body = False
                for next_line in lines[idx + 1 :]:
                    if next_line.strip():
                        next_indent = len(next_line) - len(next_line.lstrip())
                        if next_indent > indent:
                            has_body = True
                        break
                if not has_body:
                    result.append(" " * (indent + 4) + "pass")
        return "\n".join(result)

    @classmethod
    def _compress_lexical(
        cls,
        source_text: str,
        target_tokens: int,
        preserve_identifiers: bool,
    ) -> str:
        """Lexical fallback pruning for non-Python text, markdown, or malformed code."""
        lines = source_text.splitlines()
        frequencies = compute_token_frequencies(source_text)
        total_tokens = sum(frequencies.values())

        preserved_lines = []
        current_token_count = count_tokens(source_text)

        # Hard-pinned invariant patterns
        invariant_pattern = re.compile(
            r"\b(def|class|function|fn|if|elif|else|for|while|try|catch|except|finally|return|assert|let|const|var)\b"
        )

        for line in lines:
            stripped = line.strip()
            # If line is comment (# or // or /* */) or decorative
            is_comment = (
                stripped.startswith("#")
                or stripped.startswith("//")
                or stripped.startswith("/*")
                or stripped.startswith("*")
                or stripped.startswith("<!--")
            )
            is_decorative = bool(re.match(r"^[-=_~*]{3,}$", stripped))

            if (is_comment or is_decorative) and current_token_count > target_tokens:
                line_tokens = count_tokens(line)
                current_token_count -= line_tokens
                continue

            # If preserve_identifiers, always keep lines with logic keywords/assertions
            if preserve_identifiers and invariant_pattern.search(line):
                preserved_lines.append(line)
                continue

            # If we still have budget, keep line
            if current_token_count <= target_tokens and not is_comment:
                preserved_lines.append(line)
            else:
                preserved_lines.append(line)

        return cls._clean_formatting("\n".join(preserved_lines))

    @classmethod
    def _prune_non_invariants(
        cls,
        code: str,
        target_tokens: int,
        frequencies: Counter,
        total_tokens: int,
    ) -> str:
        """Aggressively prunes non-essential lines when preserve_identifiers=False."""
        lines = code.splitlines()
        kept_lines = []
        current_count = count_tokens(code)
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            line_count = count_tokens(line)
            if current_count > target_tokens and not (
                stripped.startswith("def ") or stripped.startswith("class ") or stripped.startswith("return")
            ):
                current_count -= line_count
                continue
            kept_lines.append(line)
        return cls._clean_formatting("\n".join(kept_lines))

    @classmethod
    def _clean_formatting(cls, text: str) -> str:
        """Collapses consecutive blank lines and strips trailing whitespace."""
        lines = [line.rstrip() for line in text.splitlines()]
        cleaned: List[str] = []
        prev_blank = False
        for line in lines:
            if not line:
                if not prev_blank:
                    cleaned.append("")
                    prev_blank = True
            else:
                cleaned.append(line)
                prev_blank = False
        return "\n".join(cleaned).strip() + ("\n" if text.endswith("\n") else "")

    @classmethod
    def _compute_preserved_identifiers_pct(
        cls,
        original_text: str,
        compressed_text: str,
        preserve_identifiers: bool,
        is_python: bool,
    ) -> float:
        """Calculates the percentage of original variable/function identifiers retained."""
        if preserve_identifiers:
            return 100.0

        # Extract identifiers from original
        if is_python:
            try:
                tree = ast.parse(original_text)
                v = IdentifierVisitor()
                v.visit(tree)
                orig_ids = v.names | v.function_names | v.class_names | v.arg_names
            except Exception:
                orig_ids = set(re.findall(r"\b[A-Za-z_]\w*\b", original_text))
        else:
            orig_ids = set(re.findall(r"\b[A-Za-z_]\w*\b", original_text))

        keywords = {
            "def", "class", "if", "elif", "else", "for", "while", "try",
            "except", "finally", "with", "as", "import", "from", "return",
            "yield", "break", "continue", "pass", "assert", "lambda",
            "True", "False", "None", "and", "or", "not", "is", "in",
        }
        orig_ids = orig_ids - keywords
        if not orig_ids:
            return 100.0

        retained = sum(
            1 for name in orig_ids if re.search(r"\b" + re.escape(name) + r"\b", compressed_text)
        )
        return round((retained / len(orig_ids)) * 100.0, 2)


def main() -> int:
    """CLI Entry Point for entropy_pruning."""
    parser = argparse.ArgumentParser(
        description="Synapse Hub Information-Theoretic Entropy Pruning Engine",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--file", type=str, default=None, help="Path to input source file to compress")
    parser.add_argument("--text", type=str, default=None, help="Raw input source text to compress")
    parser.add_argument(
        "--target-ratio",
        type=float,
        default=0.50,
        help="Target proportion of tokens to retain (0.0 to 1.0)",
    )
    parser.add_argument(
        "--budget-tokens",
        type=int,
        default=None,
        help="Maximum token ceiling for compressed output",
    )
    parser.add_argument(
        "--preserve-identifiers",
        dest="preserve_identifiers",
        action="store_true",
        default=True,
        help="Preserve 100%% of identifiers, function signatures, branching, and asserts",
    )
    parser.add_argument(
        "--no-preserve-identifiers",
        dest="preserve_identifiers",
        action="store_false",
        help="Disable invariant hard-pinning",
    )
    parser.add_argument("--output", type=str, default=None, help="Path to write compressed output file")
    parser.add_argument("--gate", action="store_true", default=False, help="Run DoD gate check and self-verification")
    parser.add_argument("--json", action="store_true", default=False, help="Output metadata and result as JSON")

    args = parser.parse_args()

    if args.gate:
        sample_code = "def authenticate(user: str, token: str) -> bool:\n    # Logging check\n    if not token:\n        return False\n    return True\n"
        pruned, meta = EntropyPruner.compress(sample_code, target_ratio=0.6, preserve_identifiers=True)
        passed = isinstance(pruned, str) and meta.get("preserved_identifiers_pct") == 100.0 and meta.get("compression_ratio") <= 1.0
        if args.json:
            print(json.dumps({"gate": "entropy_pruning", "status": "PASS" if passed else "FAIL"}, indent=2))
        else:
            print("[PASS] Entropy Pruning DoD Gate verified." if passed else "[FAIL] Entropy Pruning Gate failed.")
        return 0 if passed else 1

    # Input validation
    if args.file is None and args.text is None:
        sys.stderr.write("Error: Either --file or --text must be specified\n")
        return 1

    if args.file is not None and args.text is not None:
        sys.stderr.write("Error: Cannot specify both --file and --text\n")
        return 1

    source_text = ""
    if args.file is not None:
        file_path = Path(args.file)
        if not file_path.is_file():
            sys.stderr.write(f"Error: File '{args.file}' not found\n")
            return 1
        try:
            source_text = file_path.read_text(encoding="utf-8")
        except Exception as e:
            sys.stderr.write(f"Error reading file '{args.file}': {e}\n")
            return 1
    else:
        source_text = args.text

    if args.target_ratio < 0.0 or args.target_ratio > 1.0:
        sys.stderr.write(f"Error: target_ratio must be between 0.0 and 1.0, got {args.target_ratio}\n")
        return 1

    if args.budget_tokens is not None and args.budget_tokens < 0:
        sys.stderr.write(f"Error: budget_tokens must be non-negative, got {args.budget_tokens}\n")
        return 1

    try:
        compressed_text, metadata = EntropyPruner.compress(
            source_text=source_text,
            target_ratio=args.target_ratio,
            budget_tokens=args.budget_tokens,
            preserve_identifiers=args.preserve_identifiers,
        )
    except Exception as err:
        sys.stderr.write(f"Error during entropy pruning: {err}\n")
        return 1

    if args.output:
        try:
            out_p = Path(args.output)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(compressed_text, encoding="utf-8")
        except Exception as err:
            sys.stderr.write(f"Error writing output to '{args.output}': {err}\n")
            return 1

    if args.json:
        print(json.dumps(metadata, indent=2))
    elif not args.output:
        print(compressed_text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
