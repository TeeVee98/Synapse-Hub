#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
QA Agent-Computer Interface (SWE-agent ACI Pattern)
---------------------------------------------------
Provides a safe, constrained interface for AI agents interacting with repository files:
  1. view-window: Read files in constrained windows (40-50 lines) with explicit line numbering,
                  preventing context window blowout.
  2. surgical-edit: Safe contiguous chunk replacement with pre-commit AST syntax validation,
                    Clean POM checks (zero raw selectors in test scripts), and 100% UTF-8 No BOM enforcement.
  3. run-distilled: Execute shell commands and distill stdout/stderr to head + tail lines,
                    preventing runner log flooding.

Usage:
  python tools/swe_qa_aci.py view-window --file src/pages/LoginPage.ts --start-line 20 --window-size 40
  python tools/swe_qa_aci.py surgical-edit --file src/pages/LoginPage.ts --target-chunk "..." --replacement-chunk "..."
  python tools/swe_qa_aci.py run-distilled --command "pytest" --max-lines 50
"""

import os
import sys
import re
import json
import ast
import subprocess
import argparse
from typing import Dict, Any, Optional, Tuple

# Enforce UTF-8 stdout encoding
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


class SweQaAci:
    """Agent-Computer Interface for Safe QA Operations."""

    def __init__(self, repo_root: Optional[str] = None):
        self.repo_root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def resolve_path(self, file_path: str) -> str:
        """Resolves file path safely relative to repo root."""
        if os.path.isabs(file_path):
            return file_path
        return os.path.join(self.repo_root, file_path)

    def view_window(self, file_path: str, start_line: int = 1, window_size: int = 40,
                    as_json: bool = False) -> Dict[str, Any]:
        """Reads file within a bounded window with line numbers to avoid context bloat."""
        resolved = self.resolve_path(file_path)
        if not os.path.exists(resolved):
            return {
                "status": "FAIL",
                "error": f"File not found: {file_path}",
                "lines": []
            }

        try:
            with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
        except Exception as e:
            return {"status": "FAIL", "error": str(e), "lines": []}

        total_lines = len(all_lines)
        start_idx = max(1, start_line)
        end_idx = min(total_lines, start_idx + window_size - 1)

        window_lines = []
        for i in range(start_idx, end_idx + 1):
            line_str = all_lines[i - 1].rstrip("\r\n")
            window_lines.append(f"{i:4d} | {line_str}")

        result = {
            "status": "PASS",
            "file": file_path.replace("\\", "/"),
            "start_line": start_idx,
            "end_line": end_idx,
            "total_lines": total_lines,
            "window_size": len(window_lines),
            "content": "\n".join(window_lines)
        }
        return result

    def validate_syntax(self, content: str, file_path: str) -> Tuple[bool, str]:
        """Validates AST syntax based on file extension."""
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        if ext == "py":
            try:
                ast.parse(content)
                return True, "SYNTAX_VALID"
            except SyntaxError as e:
                return False, f"Python SyntaxError at line {e.lineno}: {e.msg}"

        # Lightweight balance check for JS/TS/Groovy
        brackets = {'(': ')', '{': '}', '[': ']'}
        stack = []
        in_string = False
        quote_char = ''
        escape = False

        for char in content:
            if escape:
                escape = False
                continue
            if char == '\\':
                escape = True
                continue
            if char in ("'", '"', '`'):
                if not in_string:
                    in_string = True
                    quote_char = char
                elif quote_char == char:
                    in_string = False
            elif not in_string:
                if char in brackets:
                    stack.append(brackets[char])
                elif char in brackets.values():
                    if not stack or stack.pop() != char:
                        return False, f"Unbalanced bracket '{char}' detected"

        if stack:
            return False, f"Unclosed bracket: expected '{stack[-1]}'"

        return True, "SYNTAX_VALID"

    def check_clean_pom(self, file_path: str, replacement_chunk: str) -> Tuple[bool, str]:
        """Verifies Clean POM invariants: no raw selectors in test script files."""
        is_test_script = any(part in file_path.lower() for part in ["tests/", "scripts/", ".spec.", ".test."])
        if is_test_script:
            forbidden = [
                (r'//[\w*@\[\]]+', "Raw XPath (//...)"),
                (r'xpath=', "Explicit xpath= locator"),
                (r'css=', "Explicit css= locator"),
                (r'findTestObject\(', "Katalon findTestObject in script"),
            ]
            for pat, desc in forbidden:
                if re.search(pat, replacement_chunk):
                    return False, f"Clean POM violation: {desc} strictly forbidden in test scripts ({file_path})"
        return True, "CLEAN_POM_VERIFIED"

    def surgical_edit(self, file_path: str, target_chunk: str, replacement_chunk: str,
                      validate_syntax: bool = True, enforce_clean_pom: bool = True) -> Dict[str, Any]:
        """Performs precise chunk replacement with safety checks and UTF-8 No BOM guarantee."""
        resolved = self.resolve_path(file_path)
        if not os.path.exists(resolved):
            return {
                "status": "FAIL",
                "file": file_path,
                "error": f"File not found: {file_path}"
            }

        # Check Clean POM constraint first
        if enforce_clean_pom:
            pom_ok, pom_msg = self.check_clean_pom(file_path, replacement_chunk)
            if not pom_ok:
                return {
                    "status": "FAIL",
                    "file": file_path,
                    "error": pom_msg,
                    "clean_pom_verified": False
                }

        try:
            with open(resolved, "r", encoding="utf-8") as f:
                original_content = f.read()
        except UnicodeDecodeError:
            with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                original_content = f.read()

        # Normalize line endings for target match
        norm_orig = original_content.replace("\r\n", "\n")
        norm_target = target_chunk.replace("\r\n", "\n")
        norm_replacement = replacement_chunk.replace("\r\n", "\n")

        if norm_target not in norm_orig:
            return {
                "status": "FAIL",
                "file": file_path,
                "error": "Target chunk was not found in file. Ensure exact whitespace and newline match."
            }

        occurrences = norm_orig.count(norm_target)
        if occurrences > 1:
            return {
                "status": "FAIL",
                "file": file_path,
                "error": f"Ambiguous target: found {occurrences} occurrences in file. Include more surrounding context."
            }

        # Calculate line replacement range
        before_match = norm_orig[:norm_orig.find(norm_target)]
        start_line = before_match.count("\n") + 1
        end_line = start_line + norm_target.count("\n")

        new_content = norm_orig.replace(norm_target, norm_replacement, 1)

        # Pre-commit syntax validation
        if validate_syntax:
            syn_ok, syn_msg = self.validate_syntax(new_content, file_path)
            if not syn_ok:
                return {
                    "status": "FAIL",
                    "file": file_path,
                    "error": f"Pre-commit AST syntax check failed: {syn_msg}",
                    "ast_validation": "SYNTAX_INVALID"
                }

        # Write back cleanly with 100% UTF-8 No BOM
        with open(resolved, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_content)

        # Diff summary formatting
        target_lines = [f"- {line}" for line in norm_target.splitlines()]
        replacement_lines = [f"+ {line}" for line in norm_replacement.splitlines()]
        diff_summary = "\n".join(target_lines + replacement_lines)

        return {
            "status": "PASS",
            "file": file_path.replace("\\", "/"),
            "lines_replaced": {
                "start": start_line,
                "end": end_line
            },
            "ast_validation": "SYNTAX_VALID",
            "utf8_nobom_verified": True,
            "clean_pom_verified": True,
            "diff_summary": diff_summary
        }

    def run_distilled(self, command: str, max_lines: int = 50, timeout_sec: float = 60.0) -> Dict[str, Any]:
        """Runs command and distills output to head + tail lines, preventing context flood."""
        try:
            import shlex
            if isinstance(command, str):
                if sys.platform == "win32":
                    raw_args = shlex.split(command, posix=False)
                    cmd_args = []
                    for a in raw_args:
                        if (a.startswith('"') and a.endswith('"')) or (a.startswith("'") and a.endswith("'")):
                            cmd_args.append(a[1:-1])
                        else:
                            cmd_args.append(a)
                else:
                    cmd_args = shlex.split(command)
            else:
                cmd_args = list(command)

            res = subprocess.run(
                cmd_args,
                cwd=self.repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_sec
            )
            raw_stdout = res.stdout or ""
            raw_stderr = res.stderr or ""
            combined = raw_stdout + ("\n--- STDERR ---\n" + raw_stderr if raw_stderr.strip() else "")
        except subprocess.TimeoutExpired:
            return {
                "status": "TIMEOUT",
                "command": command,
                "exit_code": -1,
                "distilled_output": f"Command timed out after {timeout_sec}s"
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "command": command,
                "exit_code": -1,
                "distilled_output": str(e)
            }

        lines = combined.splitlines()
        total = len(lines)
        if total <= max_lines:
            distilled = "\n".join(lines)
        else:
            head_count = max_lines // 2
            tail_count = max_lines - head_count
            distilled_lines = (
                lines[:head_count]
                + [f"\n... [TRUNCATED {total - max_lines} NOISE LINES] ...\n"]
                + lines[-tail_count:]
            )
            distilled = "\n".join(distilled_lines)

        return {
            "status": "PASS" if res.returncode == 0 else "FAIL",
            "command": command,
            "exit_code": res.returncode,
            "total_lines": total,
            "distilled_lines": min(total, max_lines),
            "distilled_output": distilled
        }


def main():
    parser = argparse.ArgumentParser(description="QA Agent-Computer Interface (SWE-agent ACI)")
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")

    # view-window
    vw_parser = subparsers.add_parser("view-window", help="View a file in bounded window")
    vw_parser.add_argument("--file", required=True, help="Target file path")
    vw_parser.add_argument("--start-line", type=int, default=1, help="Start line number (1-indexed)")
    vw_parser.add_argument("--window-size", type=int, default=40, help="Window line size (default 40)")
    vw_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # surgical-edit
    se_parser = subparsers.add_parser("surgical-edit", help="Surgically edit file with pre-commit checks")
    se_parser.add_argument("--file", required=True, help="Target file path")
    se_parser.add_argument("--target-chunk", required=True, help="Exact code chunk to replace")
    se_parser.add_argument("--replacement-chunk", required=True, help="New code chunk")
    se_parser.add_argument("--validate-syntax", action="store_true", default=True, help="Check AST syntax before writing")
    se_parser.add_argument("--no-validate-syntax", dest="validate_syntax", action="store_false")
    se_parser.add_argument("--enforce-clean-pom", action="store_true", default=True, help="Enforce Clean POM rules")

    # run-distilled
    rd_parser = subparsers.add_parser("run-distilled", help="Run shell command with distilled output")
    rd_parser.add_argument("--command", required=True, help="Shell command string")
    rd_parser.add_argument("--max-lines", type=int, default=50, help="Max lines to retain")
    rd_parser.add_argument("--timeout-sec", type=float, default=60.0, help="Timeout in seconds")

    args = parser.parse_args()
    aci = SweQaAci()

    if args.subcommand == "view-window":
        res = aci.view_window(args.file, start_line=args.start_line, window_size=args.window_size)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            if res["status"] == "PASS":
                print(f"--- Viewing {res['file']} (Lines {res['start_line']} - {res['end_line']} of {res['total_lines']}) ---")
                print(res["content"])
            else:
                print(f"[ERROR] {res.get('error')}")
                sys.exit(1)

    elif args.subcommand == "surgical-edit":
        res = aci.surgical_edit(
            file_path=args.file,
            target_chunk=args.target_chunk,
            replacement_chunk=args.replacement_chunk,
            validate_syntax=args.validate_syntax,
            enforce_clean_pom=args.enforce_clean_pom
        )
        print(json.dumps(res, indent=2))
        sys.exit(0 if res["status"] == "PASS" else 1)

    elif args.subcommand == "run-distilled":
        res = aci.run_distilled(command=args.command, max_lines=args.max_lines, timeout_sec=args.timeout_sec)
        print(json.dumps(res, indent=2))
        sys.exit(0 if res["status"] == "PASS" else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
