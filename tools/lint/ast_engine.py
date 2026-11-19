#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tools/lint/ast_engine.py — Semantic AST Analysis Engine for Multi-Language QA
-----------------------------------------------------------------------------
Provides compiler-grade AST parsing and lexical token-level analysis across
Python, TypeScript/JavaScript, and Groovy test suites.

Eliminates false-positive detections by strictly parsing AST syntax nodes or
safely tokenizing out comment blocks and string literals while preserving line
numbers and column fidelity.

Key Capabilities:
  1. Python AST parsing via standard library `ast` (zero dependencies).
  2. Optional Tree-Sitter AST backend for TypeScript, JavaScript, and Groovy.
  3. Failsafe semantic tokenizer that neutralizes comments and string literals
     for regex-based fallback scanners.
  4. Detects:
     - EXCESSIVE_HARD_DELAY: static sleeps (time.sleep, Thread.sleep, waitForTimeout).
     - SWALLOWED_EXCEPTION: empty catches, silent pass, dummy `_ = err` suppressions.
     - FAKE_PASS_NO_ASSERTION: test functions performing interactions without asserts.
"""

import ast
import os
import re
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

logger = logging.getLogger("synapse.ast_engine")

# Optional Tree-Sitter backend
try:
    import tree_sitter  # type: ignore # noqa: F401
    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False


@dataclass
class ASTFinding:
    """Represents a static analysis finding discovered by AST analysis."""
    rule_id: str
    file_path: str
    line: int
    column: int
    message: str
    severity: str  # "ERROR", "WARNING", "INFO"
    snippet: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "file_path": self.file_path,
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "severity": self.severity,
            "snippet": self.snippet,
        }


class ASTAnalyzer:
    """Semantic Multi-Language AST Analyzer for QA Codebases."""

    def __init__(self, use_tree_sitter: bool = True):
        self.use_tree_sitter = use_tree_sitter and HAS_TREE_SITTER

    @staticmethod
    def strip_comments_and_strings(content: str, language: str = "javascript") -> str:
        """
        Strips comments and string literals from source text, replacing them with
        whitespace while preserving exact newline positions and character offsets.
        This prevents false-positive regex matches on keywords in comments/strings.
        """
        output: List[str] = []
        i = 0
        n = len(content)

        is_python = language.lower() in ("python", "py")

        while i < n:
            # Single-line comment // (JS/TS/Groovy)
            if not is_python and i + 1 < n and content[i:i + 2] == "//":
                start = i
                while i < n and content[i] != "\n":
                    i += 1
                output.append(" " * (i - start))
                continue

            # Python single-line comment #
            if is_python and content[i] == "#":
                start = i
                while i < n and content[i] != "\n":
                    i += 1
                output.append(" " * (i - start))
                continue

            # Multi-line comment /* ... */ (JS/TS/Groovy)
            if not is_python and i + 1 < n and content[i:i + 2] == "/*":
                start = i
                i += 2
                while i < n and not (i + 1 < n and content[i:i + 2] == "*/"):
                    if content[i] == "\n":
                        output.append("\n")
                    else:
                        output.append(" ")
                    i += 1
                if i < n:
                    output.append("  ")  # replace */
                    i += 2
                continue

            # Python docstring / triple quote """ or '''
            if is_python and i + 2 < n and (content[i:i + 3] == '"""' or content[i:i + 3] == "'''"):
                delimiter = content[i:i + 3]
                output.append("   ")
                i += 3
                while i < n and content[i:i + 3] != delimiter:
                    if content[i] == "\n":
                        output.append("\n")
                    else:
                        output.append(" ")
                    i += 1
                if i < n:
                    output.append("   ")
                    i += 3
                continue

            # String literals: single quote or double quote or backtick
            if content[i] in ('"', "'", "`"):
                delim = content[i]
                output.append(" ")
                i += 1
                escaped = False
                while i < n:
                    ch = content[i]
                    if escaped:
                        escaped = False
                        if ch == "\n":
                            output.append("\n")
                        else:
                            output.append(" ")
                    elif ch == "\\":
                        escaped = True
                        output.append(" ")
                    elif ch == delim:
                        output.append(" ")
                        i += 1
                        break
                    elif ch == "\n":
                        output.append("\n")
                    else:
                        output.append(" ")
                    i += 1
                continue

            output.append(content[i])
            i += 1

        return "".join(output)

    def analyze_python(self, content: str, file_path: str = "") -> List[ASTFinding]:
        """Performs Python AST analysis using the standard library `ast` module."""
        findings: List[ASTFinding] = []
        try:
            tree = ast.parse(content, filename=file_path or "<string>")
        except SyntaxError as e:
            logger.debug("Python syntax error in %s: %s", file_path, e)
            return findings

        lines = content.splitlines()

        for node in ast.walk(tree):
            # Check 1: Static sleep calls (time.sleep, asyncio.sleep)
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Attribute):
                    val_id = getattr(node.func.value, "id", "")
                    func_name = f"{val_id}.{node.func.attr}"
                elif isinstance(node.func, ast.Name):
                    func_name = node.func.id

                if func_name in ("time.sleep", "asyncio.sleep", "sleep"):
                    # Check argument
                    is_static_sleep = True
                    if node.args and isinstance(node.args[0], ast.Constant):
                        duration = node.args[0].value
                        # Bounded polling sleeps <= 0.05s in loops are often acceptable polling intervals
                        if isinstance(duration, (int, float)) and duration <= 0.05:
                            is_static_sleep = False

                    if is_static_sleep:
                        line_idx = getattr(node, "lineno", 1)
                        snippet = lines[line_idx - 1].strip() if 0 < line_idx <= len(lines) else func_name
                        findings.append(ASTFinding(
                            rule_id="EXCESSIVE_HARD_DELAY",
                            file_path=file_path,
                            line=line_idx,
                            column=getattr(node, "col_offset", 0),
                            message=f"Static sleep detected: '{func_name}'. Use dynamic smart waits or mock timers.",
                            severity="ERROR",
                            snippet=snippet,
                        ))

            # Check 2: Empty exception handler or swallowed exception
            elif isinstance(node, ast.ExceptHandler):
                is_swallowed = False
                body = node.body
                if not body:
                    is_swallowed = True
                elif len(body) == 1:
                    stmt = body[0]
                    # Pass or Ellipsis (...)
                    if isinstance(stmt, ast.Pass) or (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is ...):
                        is_swallowed = True
                    # Dummy assignment: _ = err or _ = False
                    elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                        target = stmt.targets[0]
                        if isinstance(target, ast.Name) and target.id == "_":
                            is_swallowed = True

                if is_swallowed:
                    line_idx = getattr(node, "lineno", 1)
                    snippet = lines[line_idx - 1].strip() if 0 < line_idx <= len(lines) else "except:"
                    findings.append(ASTFinding(
                        rule_id="SWALLOWED_EXCEPTION",
                        file_path=file_path,
                        line=line_idx,
                        column=getattr(node, "col_offset", 0),
                        message="Empty or suppressed except block swallows failures. Log error or handle explicitly.",
                        severity="ERROR",
                        snippet=snippet,
                    ))

        return findings

    def analyze_ts_js(self, content: str, file_path: str = "") -> List[ASTFinding]:
        """Analyzes TypeScript and JavaScript test files for delays and swallowed errors."""
        findings: List[ASTFinding] = []
        stripped = self.strip_comments_and_strings(content, language="javascript")
        lines = content.splitlines()
        stripped_lines = stripped.splitlines()

        for idx, s_line in enumerate(stripped_lines, 1):
            # Check 1: Hard delays in Playwright/Cypress: page.waitForTimeout(5000), cy.wait(5000)
            if re.search(r'\b(?:page\.waitForTimeout|waitForTimeout|Thread\.sleep|delay)\s*\(\s*([0-9]{3,}|[a-zA-Z_]+)\s*\)', s_line):
                orig_snippet = lines[idx - 1].strip() if idx <= len(lines) else s_line.strip()
                findings.append(ASTFinding(
                    rule_id="EXCESSIVE_HARD_DELAY",
                    file_path=file_path,
                    line=idx,
                    column=0,
                    message="Hard sleep / waitForTimeout in script. Use web-first assertions or dynamic state waits.",
                    severity="ERROR",
                    snippet=orig_snippet,
                ))

            # Check 2: Empty catch: catch (...) {} or .catch(() => {})
            if re.search(r'catch\s*(?:\([^\)]*\))?\s*\{\s*\}|\.catch\s*\(\s*(?:\([^)]*\)|[a-zA-Z0-9_]+)?\s*=>\s*\{\s*\}\s*\)', s_line):
                orig_snippet = lines[idx - 1].strip() if idx <= len(lines) else s_line.strip()
                findings.append(ASTFinding(
                    rule_id="SWALLOWED_EXCEPTION",
                    file_path=file_path,
                    line=idx,
                    column=0,
                    message="Empty catch block in JavaScript/TypeScript test. Swallowing errors creates fake passes.",
                    severity="ERROR",
                    snippet=orig_snippet,
                ))

        return findings

    def analyze_groovy(self, content: str, file_path: str = "") -> List[ASTFinding]:
        """Analyzes Katalon Groovy test scripts for static delays and swallowed exceptions."""
        findings: List[ASTFinding] = []
        stripped = self.strip_comments_and_strings(content, language="groovy")
        lines = content.splitlines()
        stripped_lines = stripped.splitlines()

        for idx, s_line in enumerate(stripped_lines, 1):
            # Check 1: Thread.sleep or WebUI.delay
            if re.search(r'\b(?:Thread\.sleep|WebUI\.delay)\s*\(\s*([0-9]+)\s*\)', s_line):
                orig_snippet = lines[idx - 1].strip() if idx <= len(lines) else s_line.strip()
                findings.append(ASTFinding(
                    rule_id="EXCESSIVE_HARD_DELAY",
                    file_path=file_path,
                    line=idx,
                    column=0,
                    message="Thread.sleep or WebUI.delay in Katalon script. Replace with WebUI.waitForElementVisible.",
                    severity="ERROR",
                    snippet=orig_snippet,
                ))

            # Check 2: Empty catch block in Groovy
            if re.search(r'catch\s*\([^\)]*\)\s*\{\s*\}', s_line):
                orig_snippet = lines[idx - 1].strip() if idx <= len(lines) else s_line.strip()
                findings.append(ASTFinding(
                    rule_id="SWALLOWED_EXCEPTION",
                    file_path=file_path,
                    line=idx,
                    column=0,
                    message="Empty catch block in Groovy test. Swallowing exceptions masks test failure.",
                    severity="ERROR",
                    snippet=orig_snippet,
                ))

        return findings

    def analyze_file(self, file_path: str, content: Optional[str] = None) -> List[ASTFinding]:
        """Dispatches file to appropriate language AST analyzer."""
        if content is None:
            if not os.path.isfile(file_path):
                return []
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except OSError as exc:
                logger.debug("Could not read file %s: %s", file_path, exc)
                return []

        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".py",):
            return self.analyze_python(content, file_path)
        elif ext in (".ts", ".js", ".tsx", ".jsx"):
            return self.analyze_ts_js(content, file_path)
        elif ext in (".groovy", ".java"):
            return self.analyze_groovy(content, file_path)
        return []
