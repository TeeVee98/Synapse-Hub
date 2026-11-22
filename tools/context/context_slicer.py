#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/context/context_slicer.py — Tier 3 AST-Aware Micro-Context & Skeleton Slicer
---------------------------------------------------------------------------------
Performs precision AST parsing and structural skeleton extraction across Python,
TypeScript/JavaScript, and Groovy/Java.
Outputs:
  1. Targeted domain micro-rules (< 60 tokens).
  2. AST Code Skeleton (Class, Method signatures, parameter types, LineRange L<start>-L<end>).

Eliminates full-file reading by enabling targeted 20-50 line slice reads.

Usage:
  python3 tools/context/context_slicer.py tools/core/verify_all.py
  python3 tools/context/context_slicer.py pages/LoginPage.ts
  python3 tools/context/context_slicer.py --diff
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
from typing import Dict, List

# Enforce UTF-8 stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))


class ASTSkeletonExtractor:
    """Extracts compact structural skeletons with exact line-range spans."""

    @classmethod
    def parse_python_ast(cls, source_code: str) -> List[str]:
        """Parses Python code using stdlib ast module."""
        lines = []
        try:
            tree = ast.parse(source_code)
        except Exception as e:
            return [f"# AST Parse Error: {e}"]

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                base_names = [ast.unparse(b) for b in node.bases]
                bases_str = f"({', '.join(base_names)})" if base_names else ""
                end_line = getattr(node, "end_lineno", node.lineno)
                lines.append(f"class {node.name}{bases_str} [L{node.lineno}-L{end_line}]:")

                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        is_async = "async " if isinstance(item, ast.AsyncFunctionDef) else ""
                        args = [a.arg for a in item.args.args if a.arg != "self"]
                        ret_annot = f" -> {ast.unparse(item.returns)}" if item.returns else ""
                        item_end = getattr(item, "end_lineno", item.lineno)
                        lines.append(f"    {is_async}def {item.name}({', '.join(args)}){ret_annot} [L{item.lineno}-L{item_end}]")

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                is_async = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                args = [a.arg for a in node.args.args]
                ret_annot = f" -> {ast.unparse(node.returns)}" if node.returns else ""
                end_line = getattr(node, "end_lineno", node.lineno)
                lines.append(f"{is_async}def {node.name}({', '.join(args)}){ret_annot} [L{node.lineno}-L{end_line}]")

        return lines

    @classmethod
    def parse_ts_js_groovy(cls, source_code: str) -> List[str]:
        """Parses TypeScript/JavaScript/Groovy using token-aware regex scanner."""
        lines = []
        raw_lines = source_code.splitlines()

        class_pat = re.compile(
            r'^(?:export\s+|public\s+|default\s+|abstract\s+)*class\s+([A-Za-z0-9_]+)(?:\s+extends\s+([A-Za-z0-9_]+))?'
        )
        method_pat = re.compile(
            r'^\s*(?:(?:export|public|private|protected|async|static|override)\s+)*(?:def\s+)?([A-Za-z0-9_]+)\s*\(([^)]*)\)(?:\s*:\s*([A-Za-z0-9_<>\[\]]+))?'
        )

        current_class = None
        current_indent = 0

        for idx, line in enumerate(raw_lines, start=1):
            sline = line.strip()
            if not sline or sline.startswith(("//", "/*", "*", "#")):
                continue

            c_match = class_pat.match(sline)
            if c_match:
                c_name = c_match.group(1)
                c_ext = f" extends {c_match.group(2)}" if c_match.group(2) else ""
                lines.append(f"class {c_name}{c_ext} [Start: L{idx}]:")
                current_class = c_name
                continue

            m_match = method_pat.match(line)
            if m_match:
                m_name = m_match.group(1)
                if m_name in ("if", "for", "while", "switch", "catch", "function", "return", "super", "this", "throw", "import", "export", "new", "typeof", "delete"):
                    continue
                m_params = m_match.group(2).strip()
                m_ret = f": {m_match.group(3)}" if m_match.group(3) else ""
                # Simplify parameter string
                p_summary = ", ".join([p.split(":")[0].strip() for p in m_params.split(",") if p.strip()])
                indent = "    " if current_class else ""
                lines.append(f"{indent}{m_name}({p_summary}){m_ret} [L{idx}]")

        return lines

    @classmethod
    def extract_skeleton(cls, file_path: str) -> str:
        """Extracts code skeleton with line numbers from target file."""
        if not os.path.exists(file_path):
            return f"# File not found on disk: {file_path}"

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return f"# Read error: {e}"

        norm = file_path.lower()
        if norm.endswith(".py"):
            skeleton_lines = cls.parse_python_ast(content)
        else:
            skeleton_lines = cls.parse_ts_js_groovy(content)

        if not skeleton_lines:
            total_lines = len(content.splitlines())
            return f"# [No top-level class/function signatures detected. Total lines: {total_lines}]"

        return "\n".join(skeleton_lines)


class ContextSlicer:
    """Slices domain-specific micro-contexts and AST skeletons."""

    SLICES = {
        "PAGE_CLASS": (
            "## Micro-Context: Clean POM Page Class\n"
            "- Inherit from `BasePage` (max 1 level inheritance).\n"
            "- 6-Tier Locator Hierarchy: Role > Label > Text > TestID > Semantic CSS > XPath (last resort).\n"
            "- Encapsulate all locators and element actions. Zero raw locators in test scripts.\n"
            "- Dynamic smart waits: `expect(locator).toBeVisible()` (prohibit static sleep)."
        ),
        "TEST_SCRIPT": (
            "## Micro-Context: Clean Test Script\n"
            "- Scripts call ONLY business workflow methods on Page Classes.\n"
            "- Zero raw XPaths, CSS selectors, or `findTestObject` in scripts.\n"
            "- Truth Anchor: real assertions, no swallowed exceptions, no fake passes.\n"
            "- Dynamic test data: randomized codes with `AUTO_` + automated teardown."
        ),
        "API_CONTRACT": (
            "## Micro-Context: API & Contract Testing\n"
            "- Validate request/response payloads against OpenAPI / JSON schemas.\n"
            "- Assert exact HTTP status codes and contract boundaries.\n"
            "- Randomize test payloads to eliminate database state collisions."
        ),
        "GENERAL_CODE": (
            "## Micro-Context: Lean Senior Dev\n"
            "- Solve problem with minimal code (7-rung ladder & YAGNI).\n"
            "- 100% UTF-8 No BOM across all source and test files.\n"
            "- Mark deliberate simplifications: `shortcut: <limit>, <when to upgrade>`."
        )
    }

    @classmethod
    def classify_file(cls, file_path: str) -> str:
        """Determines the appropriate micro-context domain for a file."""
        norm = file_path.lower().replace("\\", "/")
        if "page" in norm or norm.startswith("pages/") or "/pages/" in norm:
            return "PAGE_CLASS"
        elif any(k in norm for k in ["spec.", "test.", "tc-", "scripts/"]):
            return "TEST_SCRIPT"
        elif any(k in norm for k in ["api", "contract", "endpoint", "swagger", "openapi"]):
            return "API_CONTRACT"
        return "GENERAL_CODE"

    @classmethod
    def slice_context(cls, file_path: str, include_skeleton: bool = True) -> str:
        """Returns the micro-context string along with AST skeleton for the target file."""
        domain = cls.classify_file(file_path)
        rule_text = cls.SLICES.get(domain, cls.SLICES["GENERAL_CODE"])

        if not include_skeleton:
            return rule_text

        skeleton = ASTSkeletonExtractor.extract_skeleton(file_path)
        return (
            f"{rule_text}\n\n"
            f"### AST Structural Skeleton & Line Spans (`{os.path.basename(file_path)}`):\n"
            f"```text\n{skeleton}\n```\n"
            f"> [TIP] Use StartLine/EndLine with read_file to inspect only the targeted function slice."
        )

    @classmethod
    def slice_git_diff(cls, repo_root: str = REPO_ROOT) -> Dict[str, str]:
        """Slices micro-contexts for all currently modified files in git."""
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=True
            )
            modified_files = []
            for line in res.stdout.strip().splitlines():
                parts = line.strip().split(maxsplit=1)
                if len(parts) == 2:
                    modified_files.append(parts[1])

            return {f: cls.slice_context(f, include_skeleton=True) for f in modified_files}
        except Exception:
            return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Tier 3 AST-Aware Micro-Context & Skeleton Slicer")
    parser.add_argument("target", nargs="?", help="Target file path to slice context for")
    parser.add_argument("--diff", action="store_true", help="Slice micro-contexts for current git diff")
    parser.add_argument("--skeleton-only", action="store_true", help="Print only AST skeleton")
    args = parser.parse_args()

    if args.diff:
        diff_contexts = ContextSlicer.slice_git_diff()
        if not diff_contexts:
            print("Working tree clean. No modified files to slice context for.")
            return 0
        for f, ctx in diff_contexts.items():
            print(f"=== [Target: {f}] ===")
            print(ctx)
        return 0

    if not args.target:
        print("Usage: python3 tools/context/context_slicer.py <file_path> | --diff")
        return 1

    if args.skeleton_only:
        print(ASTSkeletonExtractor.extract_skeleton(args.target))
    else:
        print(ContextSlicer.slice_context(args.target))
    return 0


if __name__ == "__main__":
    sys.exit(main())
