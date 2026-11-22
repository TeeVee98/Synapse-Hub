#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/reasoning/constrained_decoding.py — Two-Phase Unconstrained-to-Constrained Decoding Engine
------------------------------------------------------------------------------------------------
Phase 1 (Free-form Thinking): Extracts unstructured reasoning streams (<thought> tags, markdown
scratchpads, and exploratory text) without constraining creative problem-solving.
Phase 2 (FSM Grammar-Guided Projection): Pushdown automaton enforcing strict syntactic structure
projecting thoughts into syntactically valid JSON structures, Python Abstract Syntax Trees (AST),
or unified patch diffs with 100% syntactic precision and automated syntax error self-repair.

Usage:
  python tools/reasoning/constrained_decoding.py --text "<thought>...</thought> {\"key\": 1}" --mode json --json
  python tools/reasoning/constrained_decoding.py --input thought.log --mode patch --output fix.patch
  python tools/reasoning/constrained_decoding.py --text "def add(a, b): return a + b" --mode ast --json
"""

import os
import sys

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import re
import json
import ast
import difflib
import enum
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Enforce UTF-8 stdio
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass


class FSMState(enum.Enum):
    """FSM states for Pushdown Automaton."""
    IDLE = "IDLE"
    IN_OBJECT = "IN_OBJECT"
    IN_ARRAY = "IN_ARRAY"
    IN_STRING = "IN_STRING"
    ESCAPE = "ESCAPE"
    AWAIT_KEY = "AWAIT_KEY"
    AWAIT_COLON = "AWAIT_COLON"
    AWAIT_VALUE = "AWAIT_VALUE"
    AWAIT_COMMA_OR_CLOSE = "AWAIT_COMMA_OR_CLOSE"


class JsonGrammarFSM:
    """
    Pushdown Automaton (PDA) and Syntax Repair Engine for JSON.
    Auto-repairs common LLM generation slip-ups:
      - Unterminated strings
      - Single quotes converted to standard JSON double quotes
      - Missing commas between key-value pairs or array items
      - Trailing commas before closing braces/brackets
      - Unquoted object keys
      - Unmatched or missing closing braces and brackets
      - Python literals (True, False, None) mapped to JSON primitives
      - Stripping surrounding comments (// and #)
    """

    @staticmethod
    def strip_comments(text: str) -> Tuple[str, bool]:
        """Strips single-line (//, #) and block (/* ... */) comments outside string literals."""
        repaired = False
        result_chars = []
        i = 0
        n = len(text)
        in_double = False
        in_single = False
        escape = False

        while i < n:
            ch = text[i]
            if in_double:
                result_chars.append(ch)
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    in_double = False
                i += 1
            elif in_single:
                result_chars.append(ch)
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == "'":
                    in_single = False
                i += 1
            else:
                if ch == '"':
                    in_double = True
                    result_chars.append(ch)
                    i += 1
                elif ch == "'":
                    in_single = True
                    result_chars.append(ch)
                    i += 1
                elif ch == '/' and i + 1 < n and text[i + 1] == '/':
                    repaired = True
                    i += 2
                    while i < n and text[i] != '\n':
                        i += 1
                elif ch == '/' and i + 1 < n and text[i + 1] == '*':
                    repaired = True
                    i += 2
                    while i + 1 < n and not (text[i] == '*' and text[i + 1] == '/'):
                        i += 1
                    i = min(i + 2, n)
                elif ch == '#' and (i == 0 or text[i - 1] in ' \t\n,'):
                    repaired = True
                    i += 1
                    while i < n and text[i] != '\n':
                        i += 1
                else:
                    result_chars.append(ch)
                    i += 1

        return "".join(result_chars), repaired

    @staticmethod
    def normalize_python_literals(text: str) -> Tuple[str, bool]:
        """Normalizes True, False, None outside of string literals to true, false, null."""
        repaired = False
        result_chars = []
        i = 0
        n = len(text)
        in_str = False
        escape = False

        while i < n:
            ch = text[i]
            if in_str:
                result_chars.append(ch)
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    in_str = False
                i += 1
            else:
                if ch == '"':
                    in_str = True
                    result_chars.append(ch)
                    i += 1
                else:
                    remaining = text[i:]
                    m_true = re.match(r"^True\b", remaining)
                    m_false = re.match(r"^False\b", remaining)
                    m_none = re.match(r"^None\b", remaining)
                    if m_true:
                        result_chars.append("true")
                        i += 4
                        repaired = True
                    elif m_false:
                        result_chars.append("false")
                        i += 5
                        repaired = True
                    elif m_none:
                        result_chars.append("null")
                        i += 4
                        repaired = True
                    else:
                        result_chars.append(ch)
                        i += 1

        return "".join(result_chars), repaired

    @classmethod
    def mask_and_normalize_strings(cls, text: str) -> Tuple[str, Dict[str, str], List[str]]:
        """
        Scans and isolates string literals (double-quoted and single-quoted).
        Converts single-quoted keys/values to standard double-quoted JSON strings.
        Protects all string contents against modification by replacing them with unique placeholders.
        Repairs unterminated strings before newlines or at EOF.
        """
        repairs: List[str] = []
        string_table: Dict[str, str] = {}
        result_chars: List[str] = []
        i = 0
        n = len(text)
        str_counter = 0
        had_single_quotes = False

        while i < n:
            ch = text[i]
            if ch == '"':
                # Double-quoted string: preserve content verbatim
                i += 1
                str_chars = ['"']
                escape = False
                terminated = False

                while i < n:
                    c = text[i]
                    if escape:
                        str_chars.append(c)
                        escape = False
                        i += 1
                    elif c == '\\':
                        str_chars.append(c)
                        escape = True
                        i += 1
                    elif c == '"':
                        str_chars.append(c)
                        i += 1
                        terminated = True
                        break
                    elif c == '\n':
                        # Unterminated string before newline
                        str_chars.append('"')
                        terminated = True
                        repairs.append("Repaired unterminated string literal before newline")
                        break
                    else:
                        str_chars.append(c)
                        i += 1

                if not terminated:
                    str_chars.append('"')
                    repairs.append("Repaired unclosed string literal at end of input")

                normalized_str = "".join(str_chars)
                placeholder = f'"\x00SYNAPSE_STR_{str_counter}\x00"'
                str_counter += 1
                string_table[placeholder] = normalized_str
                result_chars.append(placeholder)

            elif ch == "'":
                # Single-quoted string acting as string delimiter
                had_single_quotes = True
                i += 1
                inner_chars: List[str] = []
                escape = False
                terminated = False

                while i < n:
                    c = text[i]
                    if escape:
                        if c == "'":
                            inner_chars.append("'")
                        elif c == '"':
                            inner_chars.append(r'\"')
                        else:
                            inner_chars.append('\\' + c)
                        escape = False
                        i += 1
                    elif c == '\\':
                        escape = True
                        i += 1
                    elif c == "'":
                        i += 1
                        terminated = True
                        break
                    elif c == '\n':
                        terminated = True
                        repairs.append("Repaired unterminated string literal before newline")
                        break
                    elif c == '"':
                        inner_chars.append(r'\"')
                        i += 1
                    else:
                        inner_chars.append(c)
                        i += 1

                if not terminated:
                    repairs.append("Repaired unclosed string literal at end of input")

                normalized_str = '"' + "".join(inner_chars) + '"'
                placeholder = f'"\x00SYNAPSE_STR_{str_counter}\x00"'
                str_counter += 1
                string_table[placeholder] = normalized_str
                result_chars.append(placeholder)

            else:
                result_chars.append(ch)
                i += 1

        if had_single_quotes:
            repairs.append("Normalized single quotes to standard double quotes")

        return "".join(result_chars), string_table, repairs

    @classmethod
    def repair_json_string(cls, raw: str) -> Tuple[str, List[str]]:
        """
        Applies multi-stage FSM and pushdown automaton rules to repair malformed JSON.
        Returns the sanitized JSON string and list of repairs made.
        """
        repairs: List[str] = []
        text = raw.strip()

        # Step 1: Strip surrounding markdown code fences if any
        code_fence_pattern = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```$", re.DOTALL | re.IGNORECASE)
        m_fence = code_fence_pattern.search(text)
        if m_fence:
            text = m_fence.group(1).strip()
            repairs.append("Stripped markdown code fence wrapper")

        # Step 2: Strip comments (//, #, /* ... */)
        text, had_comments = cls.strip_comments(text)
        if had_comments:
            repairs.append("Stripped non-standard comment lines")

        # Step 3: Mask string literals and normalize single quotes (protects all string contents)
        masked_text, string_table, str_repairs = cls.mask_and_normalize_strings(text)
        repairs.extend(str_repairs)

        # Step 4: Normalize Python literals (True, False, None) on masked text
        masked_text, had_py_literals = cls.normalize_python_literals(masked_text)
        if had_py_literals:
            repairs.append("Replaced Python literals (True/False/None) with JSON primitives")

        # Step 5: Fix unquoted keys on masked text
        unquoted_key_pat = re.compile(r'([\{\,]\s*|^\s*)([a-zA-Z_][a-zA-Z0-9_\-]*)\s*:', re.MULTILINE)
        if unquoted_key_pat.search(masked_text):
            masked_text = unquoted_key_pat.sub(r'\g<1>"\g<2>":', masked_text)
            repairs.append("Enclosed unquoted object keys in double quotes")

        # Step 6: Fix missing commas between key-value pairs or array elements
        missing_comma_obj = re.compile(
            r'((?:true|false|null|-?\d+(?:\.\d+)?|"[^"\\]*(?:\\.[^"\\]*)*"|\]|\}))\s*\n\s*("(?:\w+|\x00SYNAPSE_STR_\d+\x00)":|[a-zA-Z_][a-zA-Z0-9_\-]*\s*:)',
            re.MULTILINE
        )
        had_obj_comma = False
        while missing_comma_obj.search(masked_text):
            masked_text = missing_comma_obj.sub(r'\1,\n \2', masked_text)
            had_obj_comma = True
        if had_obj_comma:
            repairs.append("Inserted missing comma delimiter between object entries")

        missing_comma_arr = re.compile(
            r'((?:true|false|null|-?\d+(?:\.\d+)?|"[^"\\]*(?:\\.[^"\\]*)*"|\]|\}))\s*\n\s*("[^"\\]*(?:\\.[^"\\]*)*"|\{|\[|-?\d+|true|false|null)',
            re.MULTILINE
        )
        had_arr_comma = False
        while missing_comma_arr.search(masked_text):
            masked_text = missing_comma_arr.sub(r'\1,\n \2', masked_text)
            had_arr_comma = True
        if had_arr_comma:
            repairs.append("Inserted missing comma delimiter between array elements")

        # Step 7: Remove trailing commas before closing braces/brackets
        trailing_comma_pat = re.compile(r',\s*([\}\]])')
        if trailing_comma_pat.search(masked_text):
            masked_text = trailing_comma_pat.sub(r'\1', masked_text)
            repairs.append("Removed trailing commas before closing braces/brackets")

        # Step 8: Pushdown Automaton pass for balanced braces/brackets
        stack: List[str] = []
        i = 0
        n_m = len(masked_text)
        repaired_chars: List[str] = []
        in_p_string = False

        while i < n_m:
            ch = masked_text[i]
            if in_p_string:
                repaired_chars.append(ch)
                if ch == '"':
                    in_p_string = False
                i += 1
            else:
                if ch == '"':
                    in_p_string = True
                    repaired_chars.append(ch)
                elif ch == '{':
                    stack.append('}')
                    repaired_chars.append(ch)
                elif ch == '[':
                    stack.append(']')
                    repaired_chars.append(ch)
                elif ch == '}':
                    if stack and stack[-1] == '}':
                        stack.pop()
                    repaired_chars.append(ch)
                elif ch == ']':
                    if stack and stack[-1] == ']':
                        stack.pop()
                    repaired_chars.append(ch)
                else:
                    repaired_chars.append(ch)
                i += 1

        # If stack still has unclosed containers
        if stack:
            while stack:
                closing_token = stack.pop()
                repaired_chars.append(closing_token)
            repairs.append("Closed unmatched opening braces/brackets via pushdown stack")

        balanced_masked_text = "".join(repaired_chars).strip()
        if trailing_comma_pat.search(balanced_masked_text):
            balanced_masked_text = trailing_comma_pat.sub(r"\g<1>", balanced_masked_text)

        # Step 9: Restore protected string literals
        final_text = balanced_masked_text
        for placeholder, original_or_normalized_str in string_table.items():
            final_text = final_text.replace(placeholder, original_or_normalized_str)

        return final_text, repairs


class PatchGrammarFSM:
    """
    Grammar projection and validation engine for Unified Diff Patches.
    Guarantees mathematically exact hunk headers (@@ -start,count +start,count @@)
    and verifies standard diff formatting suitable for `git apply` or `patch`.
    """

    @classmethod
    def repair_and_validate(cls, raw_diff: str, target_file: Optional[str] = None) -> Tuple[str, List[str]]:
        repairs: List[str] = []
        lines = raw_diff.splitlines()

        # Step 1: Strip code fences
        clean_lines: List[str] = []
        in_diff_fence = False
        for line in lines:
            if line.startswith("```"):
                if "diff" in line.lower() or "patch" in line.lower():
                    in_diff_fence = True
                    repairs.append("Stripped markdown diff code fence")
                    continue
                elif in_diff_fence:
                    in_diff_fence = False
                    continue
            clean_lines.append(line)

        # Step 2: Segment lines into per-file diff blocks
        # Identify file header boundaries: 'diff --git ' or ('--- ' followed by '+++ ')
        file_boundary_indices: List[int] = []
        i = 0
        n_lines = len(clean_lines)

        while i < n_lines:
            line = clean_lines[i]
            if line.startswith("diff --git "):
                file_boundary_indices.append(i)
                i += 1
            elif line.startswith("--- "):
                # Check if followed by +++ line (possibly with index line in between)
                is_header = False
                if i + 1 < n_lines and clean_lines[i + 1].startswith("+++ "):
                    is_header = True
                elif i + 2 < n_lines and clean_lines[i + 2].startswith("+++ "):
                    is_header = True

                if is_header:
                    # If this --- is not already part of a diff --git section right before it
                    if not file_boundary_indices or i - 1 != file_boundary_indices[-1] or not clean_lines[file_boundary_indices[-1]].startswith("diff --git "):
                        file_boundary_indices.append(i)
                i += 1
            else:
                i += 1

        # If no file headers found at all, create a single file section with injected headers
        if not file_boundary_indices:
            file_path = target_file if target_file else "target_file.py"
            clean_lines.insert(0, f"--- a/{file_path}")
            clean_lines.insert(1, f"+++ b/{file_path}")
            repairs.append(f"Injected standard unified diff header for '{file_path}'")
            file_boundary_indices = [0]

        # Break clean_lines into file sections
        file_sections: List[List[str]] = []
        for s_idx, start in enumerate(file_boundary_indices):
            end = file_boundary_indices[s_idx + 1] if s_idx + 1 < len(file_boundary_indices) else len(clean_lines)
            file_sections.append(clean_lines[start:end])

        all_reconstructed_lines: List[str] = []

        # Step 3: Process each file section independently
        for file_lines in file_sections:
            if not file_lines:
                continue

            header_old_idx = -1
            header_new_idx = -1
            for idx, f_line in enumerate(file_lines):
                if f_line.startswith("--- "):
                    header_old_idx = idx
                elif f_line.startswith("+++ ") and header_old_idx != -1:
                    header_new_idx = idx
                    break

            if header_old_idx == -1 or header_new_idx == -1:
                f_path = target_file if target_file else "target_file.py"
                file_lines.insert(0, f"--- a/{f_path}")
                file_lines.insert(1, f"+++ b/{f_path}")
                repairs.append(f"Injected standard unified diff header for '{f_path}'")
                header_old_idx = 0
                header_new_idx = 1

            # Parse hunks in this file section
            hunk_indices: List[int] = []
            for idx, f_line in enumerate(file_lines):
                if f_line.startswith("@@"):
                    hunk_indices.append(idx)

            # If no hunk headers found in this section but lines start with + or -, synthesize @@
            if not hunk_indices and any(l.startswith(("+", "-")) for l in file_lines[header_new_idx + 1:]):
                start_pos = header_new_idx + 1
                file_lines.insert(start_pos, "@@ -1,1 +1,1 @@")
                hunk_indices.append(start_pos)
                repairs.append("Synthesized missing hunk header @@")

            # Lines before first hunk (headers, index, diff --git, etc.)
            prefix_end = hunk_indices[0] if hunk_indices else header_new_idx + 1
            file_reconstructed: List[str] = list(file_lines[:prefix_end])

            for h_i, h_idx in enumerate(hunk_indices):
                next_h_idx = hunk_indices[h_i + 1] if h_i + 1 < len(hunk_indices) else len(file_lines)
                hunk_header_line = file_lines[h_idx]
                hunk_body = file_lines[h_idx + 1:next_h_idx]

                m_header = re.match(r"^@@\s*-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s*@@(.*)$", hunk_header_line)
                orig_old_start = int(m_header.group(1)) if m_header else 1
                orig_new_start = int(m_header.group(3)) if m_header else 1
                hunk_suffix = m_header.group(5) if m_header and m_header.group(5) else ""

                old_count = 0
                new_count = 0
                processed_body: List[str] = []

                for b_line in hunk_body:
                    if not b_line:
                        b_line = " "
                        repairs.append("Normalized empty hunk line to single-space context line")

                    first_char = b_line[0]
                    if first_char == ' ':
                        old_count += 1
                        new_count += 1
                        processed_body.append(b_line)
                    elif first_char == '-':
                        old_count += 1
                        processed_body.append(b_line)
                    elif first_char == '+':
                        new_count += 1
                        processed_body.append(b_line)
                    elif first_char == '\\':
                        processed_body.append(b_line)
                    else:
                        old_count += 1
                        new_count += 1
                        processed_body.append(" " + b_line)
                        repairs.append("Added missing leading space to context line")

                corrected_header = f"@@ -{orig_old_start},{old_count} +{orig_new_start},{new_count} @@{hunk_suffix}"
                if corrected_header != hunk_header_line:
                    repairs.append(f"Recalculated hunk line counts: {corrected_header}")

                file_reconstructed.append(corrected_header)
                file_reconstructed.extend(processed_body)

            all_reconstructed_lines.extend(file_reconstructed)

        final_patch = "\n".join(all_reconstructed_lines).strip() + "\n"
        return final_patch, repairs


class AstGrammarFSM:
    """
    Syntactic projection engine for Python Abstract Syntax Trees (AST).
    Normalizes indentation, wraps unindented blocks, auto-closes delimiters, and compiles code.
    """

    @classmethod
    def repair_and_parse(cls, raw_code: str) -> Tuple[ast.AST, List[str]]:
        repairs: List[str] = []
        text = raw_code.strip()

        # Step 1: Strip markdown code fence
        code_fence_pattern = re.compile(r"^```(?:python|py)?\s*\n?(.*?)\n?```$", re.DOTALL | re.IGNORECASE)
        m_fence = code_fence_pattern.search(text)
        if m_fence:
            text = m_fence.group(1).strip()
            repairs.append("Stripped Python code fence")

        if not text:
            raise ValueError("Empty or whitespace-only code stream cannot be parsed into AST")

        # Step 2: Try parsing directly first
        try:
            tree = ast.parse(text)
            return tree, repairs
        except SyntaxError as parse_err:
            repairs.append(f"Direct AST parse failed ({parse_err}), initiating syntax auto-repair")

        # Step 3: Auto-repair common syntax glitches
        lines = text.splitlines()
        repaired_lines: List[str] = []
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i]
            repaired_lines.append(line)
            stripped = line.strip()

            # If line ends with a colon, check if next line is properly indented
            if stripped.endswith(":") and not stripped.startswith("#"):
                if i + 1 >= n or (lines[i + 1].strip() and len(lines[i + 1]) - len(lines[i + 1].lstrip()) <= len(line) - len(line.lstrip())):
                    indent = " " * ((len(line) - len(line.lstrip())) + 4)
                    repaired_lines.append(f"{indent}pass")
                    repairs.append(f"Inserted 'pass' body for unindented block after: '{stripped}'")
            i += 1

        repaired_text = "\n".join(repaired_lines)

        # Step 4: LIFO Pushdown Stack for open delimiters: '(', '[', '{'
        # Interleaved brackets/parens/braces (e.g. '([(') must be closed in reverse order.
        delimiter_stack: List[str] = []
        delim_map = {'(': ')', '[': ']', '{': '}'}
        closing_delims = {')': '(', ']': '[', '}': '{'}

        idx = 0
        text_len = len(repaired_text)
        in_str = None
        escape = False

        while idx < text_len:
            ch = repaired_text[idx]
            if in_str:
                if escape:
                    escape = False
                    idx += 1
                elif ch == '\\':
                    escape = True
                    idx += 1
                elif in_str in ('"""', "'''"):
                    if repaired_text[idx:idx + 3] == in_str:
                        in_str = None
                        idx += 3
                    else:
                        idx += 1
                elif ch == in_str:
                    in_str = None
                    idx += 1
                else:
                    idx += 1
            elif ch == '#':
                while idx < text_len and repaired_text[idx] != '\n':
                    idx += 1
            elif ch in ('"', "'"):
                if idx + 2 < text_len and repaired_text[idx:idx + 3] in ('"""', "'''"):
                    in_str = repaired_text[idx:idx + 3]
                    idx += 3
                else:
                    in_str = ch
                    idx += 1
            else:
                if ch in delim_map:
                    delimiter_stack.append(delim_map[ch])
                elif ch in closing_delims:
                    expected_closer = ch
                    if delimiter_stack and delimiter_stack[-1] == expected_closer:
                        delimiter_stack.pop()
                idx += 1

        if delimiter_stack:
            closers = []
            while delimiter_stack:
                closers.append(delimiter_stack.pop())
            closing_str = "".join(closers)
            repaired_text += closing_str
            repairs.append(f"Auto-closed unclosed delimiters in LIFO order via pushdown stack: '{closing_str}'")

        try:
            tree = ast.parse(repaired_text)
            return tree, repairs
        except SyntaxError as s_err:
            raise ValueError(f"Unable to project text into valid AST: {s_err}")


class ConstrainedDecoder:
    """
    Production-grade Two-Phase Unconstrained-to-Constrained Decoding Engine.
    Executes free-form thought extraction followed by grammar-guided projection.
    """

    def __init__(self) -> None:
        self.last_repaired_errors: List[str] = []
        self.last_extracted_thought: str = ""

    def extract_thought_stream(self, text: str) -> Tuple[str, str]:
        """
        Phase 1: Free-form Thinking Extraction.
        Extracts unstructured thinking streams (<thought>, <thinking>, <reasoning>,
        scratchpad markdown sections) and isolates candidate payload.
        Returns: (extracted_thought, payload_candidate)
        """
        if not text:
            return "", ""

        thought_accumulator: List[str] = []
        payload = text

        # 1. XML-style thought tags
        tag_pattern = re.compile(r"<(thought|thinking|reasoning)>(.*?)</\1>", re.DOTALL | re.IGNORECASE)
        for match in tag_pattern.finditer(text):
            thought_accumulator.append(match.group(2).strip())

        if thought_accumulator:
            payload = tag_pattern.sub("", text).strip()
        else:
            # 2. Markdown scratchpad or thought block
            scratchpad_pat = re.compile(
                r"(?:^|\n)(?:#+\s*Scratchpad|#+\s*Reasoning|>\s*Thought:?|---+\s*THOUGHT\s*---+)(.*?)(?=(?:```|---+\s*END|\Z))",
                re.DOTALL | re.IGNORECASE
            )
            m_scratch = scratchpad_pat.search(text)
            if m_scratch:
                thought_accumulator.append(m_scratch.group(1).strip())
                payload = scratchpad_pat.sub("", text).strip()

        extracted_thought = "\n\n".join(thought_accumulator).strip()
        self.last_extracted_thought = extracted_thought
        return extracted_thought, payload

    def validate_schema(self, data: Any, schema: Dict[str, Any]) -> Tuple[Any, List[str]]:
        """
        Validates and type-projects data against a JSON schema specification.
        Injects missing required fields and coerces compatible types.
        """
        repairs: List[str] = []
        if not isinstance(schema, dict):
            raise ValueError("Schema must be a dictionary object")

        expected_type = schema.get("type")
        if expected_type == "object":
            if not isinstance(data, dict):
                if data is None:
                    data = {}
                    repairs.append("Initialized missing object data to empty dict")
                else:
                    raise ValueError(f"Schema violation: expected object, got {type(data).__name__}")

            required_keys = schema.get("required", [])
            properties = schema.get("properties", {})

            for req_key in required_keys:
                if req_key not in data or data[req_key] is None:
                    prop_spec = properties.get(req_key, {})
                    prop_type = prop_spec.get("type", "string")
                    default_val: Any = ""
                    if prop_type in ("integer", "number"):
                        default_val = 0
                    elif prop_type == "boolean":
                        default_val = False
                    elif prop_type == "array":
                        default_val = []
                    elif prop_type == "object":
                        default_val = {}
                    data[req_key] = default_val
                    repairs.append(f"Injected default value for required field: '{req_key}'")

            for prop_name, prop_spec in properties.items():
                if prop_name in data:
                    val = data[prop_name]
                    target_type = prop_spec.get("type")
                    if target_type == "integer" and not isinstance(val, int):
                        try:
                            data[prop_name] = int(val)
                            repairs.append(f"Coerced '{prop_name}' to integer")
                        except (ValueError, TypeError) as cast_err:
                            repairs.append(f"Ignored non-integer value for '{prop_name}': {cast_err}")
                    elif target_type == "number" and not isinstance(val, (int, float)):
                        try:
                            data[prop_name] = float(val)
                            repairs.append(f"Coerced '{prop_name}' to float")
                        except (ValueError, TypeError) as cast_err:
                            repairs.append(f"Ignored non-numeric value for '{prop_name}': {cast_err}")
                    elif target_type == "boolean" and not isinstance(val, bool):
                        if str(val).lower() in ("true", "1", "yes"):
                            data[prop_name] = True
                            repairs.append(f"Coerced '{prop_name}' to True")
                        elif str(val).lower() in ("false", "0", "no"):
                            data[prop_name] = False
                            repairs.append(f"Coerced '{prop_name}' to False")
                    elif target_type == "string" and not isinstance(val, str):
                        data[prop_name] = str(val)
                        repairs.append(f"Coerced '{prop_name}' to string")

        return data, repairs

    def _select_payload(self, thought: str, candidate_text: str, mode: str = "json") -> str:
        """Intelligently isolates payload between thought scratchpad and external answer."""
        thought_s = thought.strip()
        cand_s = candidate_text.strip()
        if not cand_s:
            return thought_s
        if not thought_s:
            return cand_s

        if mode == "json":
            has_json_fence = bool(re.search(r"```(?:json)?\s*\n?.*?[{\[].*?```", cand_s, re.DOTALL | re.IGNORECASE))
            has_braces = "{" in cand_s or "[" in cand_s
            cand_has_json = has_json_fence or has_braces

            thought_has_json_fence = bool(re.search(r"```(?:json)?\s*\n?.*?[{\[].*?```", thought_s, re.DOTALL | re.IGNORECASE))
            thought_has_braces = "{" in thought_s or "[" in thought_s
            thought_has_json = thought_has_json_fence or thought_has_braces

            if cand_has_json:
                return cand_s
            if thought_has_json:
                return thought_s
            return cand_s

        elif mode == "patch":
            diff_fence = bool(re.search(r"```(?:diff|patch)\s*\n?.*?```", cand_s, re.DOTALL | re.IGNORECASE))
            diff_markers = ("--- " in cand_s and "+++ " in cand_s) or "@@" in cand_s
            cand_has_diff = diff_fence or diff_markers

            thought_diff_fence = bool(re.search(r"```(?:diff|patch)\s*\n?.*?```", thought_s, re.DOTALL | re.IGNORECASE))
            thought_diff_markers = ("--- " in thought_s and "+++ " in thought_s) or "@@" in thought_s
            thought_has_diff = thought_diff_fence or thought_diff_markers

            if cand_has_diff:
                return cand_s
            if thought_has_diff:
                return thought_s
            return cand_s

        elif mode == "ast":
            py_fence = bool(re.search(r"```(?:python|py)?\s*\n?.*?```", cand_s, re.DOTALL | re.IGNORECASE))
            thought_py_fence = bool(re.search(r"```(?:python|py)?\s*\n?.*?```", thought_s, re.DOTALL | re.IGNORECASE))
            if py_fence:
                return cand_s
            if thought_py_fence:
                return thought_s
            py_keywords = ("def ", "class ", "import ", "from ")
            cand_has_kw = any(kw in cand_s for kw in py_keywords)
            thought_has_kw = any(kw in thought_s for kw in py_keywords)
            if cand_has_kw:
                return cand_s
            if thought_has_kw:
                return thought_s
            return cand_s

        return cand_s if cand_s else thought_s

    def project_json(self, thought_text: str, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Phase 2: Pushdown FSM Grammar Projection for JSON.
        Extracts and converts thinking streams into syntactically valid JSON structures.
        """
        self.last_repaired_errors = []
        if not thought_text or not thought_text.strip():
            raise ValueError("Input thought text is empty or whitespace-only")

        thought, candidate_text = self.extract_thought_stream(thought_text)
        target_payload = self._select_payload(thought, candidate_text, mode="json")

        # Isolate candidate JSON block
        json_candidate = target_payload
        fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", target_payload, re.DOTALL | re.IGNORECASE)
        if fence_match:
            json_candidate = fence_match.group(1).strip()
        else:
            first_brace = target_payload.find('{')
            first_bracket = target_payload.find('[')
            start_pos = -1
            if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
                start_pos = first_brace
            elif first_bracket != -1:
                start_pos = first_bracket

            if start_pos != -1:
                json_candidate = target_payload[start_pos:].strip()

        # Direct JSON parsing fast-path:
        # If candidate is already valid JSON, skip the repair pipeline completely
        parsed_data = None
        try:
            parsed_data = json.loads(json_candidate)
        except json.JSONDecodeError:
            parsed_data = None

        if parsed_data is None:
            # Apply Pushdown Automaton repair
            repaired_json_str, repairs = JsonGrammarFSM.repair_json_string(json_candidate)
            self.last_repaired_errors.extend(repairs)

            try:
                parsed_data = json.loads(repaired_json_str)
            except json.JSONDecodeError as decode_err:
                raise ValueError(f"Failed to project valid JSON from thought stream: {decode_err}")

        # Schema enforcement
        if schema:
            parsed_data, schema_repairs = self.validate_schema(parsed_data, schema)
            self.last_repaired_errors.extend(schema_repairs)

        return parsed_data

    def project_patch(self, thought_text: str, target_file: Optional[str] = None) -> str:
        """
        Phase 2: Grammar Projection for Unified Diff Patches.
        Extracts diff blocks or synthesizes unified diffs with exact line counts.
        """
        self.last_repaired_errors = []
        if not thought_text or not thought_text.strip():
            raise ValueError("Input thought text is empty or whitespace-only")

        thought, candidate_text = self.extract_thought_stream(thought_text)
        target_payload = self._select_payload(thought, candidate_text, mode="patch")

        # Look for diff code fence explicitly tagged diff or patch
        diff_fence_match = re.search(r"```(?:diff|patch)\s*\n?(.*?)\n?```", target_payload, re.DOTALL | re.IGNORECASE)
        diff_text = diff_fence_match.group(1).strip() if diff_fence_match else ""

        if not diff_text:
            payload_lines = target_payload.splitlines()
            has_headers = ("--- " in target_payload and "+++ " in target_payload)
            has_hunk_header = "@@" in target_payload
            has_diff_lines = (any(l.startswith("-") for l in payload_lines) and any(l.startswith("+") for l in payload_lines))

            if has_headers or has_hunk_header or has_diff_lines:
                diff_text = target_payload
            else:
                before_pat = re.search(r"(?:Before|Original|Current):\s*```(?:\w+)?\s*\n?(.*?)\n?```", target_payload, re.DOTALL | re.IGNORECASE)
                after_pat = re.search(r"(?:After|Replacement|Proposed|Fixed):\s*```(?:\w+)?\s*\n?(.*?)\n?```", target_payload, re.DOTALL | re.IGNORECASE)
                if before_pat and after_pat:
                    before_str = before_pat.group(1)
                    after_str = after_pat.group(1)
                    if not before_str.endswith("\n"):
                        before_str += "\n"
                    if not after_str.endswith("\n"):
                        after_str += "\n"
                    fname = target_file if target_file else "target_file.py"
                    diff_gen = difflib.unified_diff(
                        before_str.splitlines(keepends=True),
                        after_str.splitlines(keepends=True),
                        fromfile=f"a/{fname}",
                        tofile=f"b/{fname}"
                    )
                    diff_text = "".join(diff_gen)
                    self.last_repaired_errors.append(f"Synthesized unified diff from Before/After blocks for '{fname}'")

        if not diff_text:
            raise ValueError("No valid patch or code change indicators could be extracted from thought stream")

        final_patch, repairs = PatchGrammarFSM.repair_and_validate(diff_text, target_file=target_file)
        self.last_repaired_errors.extend(repairs)
        return final_patch

    def project_ast(self, thought_text: str) -> ast.AST:
        """
        Phase 2: Syntactic Projection for Python Abstract Syntax Trees (AST).
        Extracts Python code, normalizes indentation, and compiles into an AST Module.
        """
        self.last_repaired_errors = []
        if not thought_text or not thought_text.strip():
            raise ValueError("Input thought text is empty or whitespace-only")

        thought, candidate_text = self.extract_thought_stream(thought_text)
        target_payload = self._select_payload(thought, candidate_text, mode="ast")

        # Check for python code fence
        py_fence_match = re.search(r"```(?:python|py)?\s*\n?(.*?)\n?```", target_payload, re.DOTALL | re.IGNORECASE)
        code_text = py_fence_match.group(1).strip() if py_fence_match else target_payload

        tree, repairs = AstGrammarFSM.repair_and_parse(code_text)
        self.last_repaired_errors.extend(repairs)
        return tree


def build_cli_parser() -> argparse.ArgumentParser:
    """Configures command-line arguments for ConstrainedDecoder."""
    parser = argparse.ArgumentParser(
        description="Synapse-Hub Constrained Decoding Engine (Unconstrained-to-Constrained Projection)"
    )
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument("--input", type=str, help="Path to input text or thought log file")
    input_group.add_argument("--text", type=str, help="Inline thought or reasoning text to decode")

    parser.add_argument(
        "--mode",
        type=str,
        choices=["json", "patch", "ast"],
        default="json",
        help="Projection mode: json (default), patch, or ast"
    )
    parser.add_argument("--schema", type=str, help="Path to JSON schema file for schema-guided projection")
    parser.add_argument("--output", type=str, help="Path to write the projected output")
    parser.add_argument("--json", action="store_true", help="Emit structured telemetry as JSON to stdout")
    return parser


def main() -> int:
    """CLI Entrypoint for ConstrainedDecoder."""
    parser = build_cli_parser()
    args = parser.parse_args()

    raw_text = ""
    if args.text is not None:
        raw_text = args.text
    elif args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            err_msg = f"Input file not found: {args.input}"
            if args.json:
                print(json.dumps({
                    "status": "error",
                    "mode": args.mode,
                    "error": err_msg,
                    "syntax_errors_repaired": []
                }, indent=2))
            else:
                sys.stderr.write(f"Error: {err_msg}\n")
            return 1
        raw_text = input_path.read_text(encoding="utf-8")
    else:
        if not sys.stdin.isatty():
            raw_text = sys.stdin.read()
        else:
            parser.print_help(sys.stderr)
            return 1

    schema_dict: Optional[Dict[str, Any]] = None
    if args.schema:
        schema_path = Path(args.schema)
        if not schema_path.exists():
            err_msg = f"Schema file not found: {args.schema}"
            if args.json:
                print(json.dumps({
                    "status": "error",
                    "mode": args.mode,
                    "error": err_msg,
                    "syntax_errors_repaired": []
                }, indent=2))
            else:
                sys.stderr.write(f"Error: {err_msg}\n")
            return 1
        try:
            schema_dict = json.loads(schema_path.read_text(encoding="utf-8"))
        except Exception as e:
            err_msg = f"Failed to parse schema JSON: {e}"
            if args.json:
                print(json.dumps({
                    "status": "error",
                    "mode": args.mode,
                    "error": err_msg,
                    "syntax_errors_repaired": []
                }, indent=2))
            else:
                sys.stderr.write(f"Error: {err_msg}\n")
            return 1

    decoder = ConstrainedDecoder()
    mode = args.mode

    try:
        if mode == "json":
            result = decoder.project_json(raw_text, schema=schema_dict)
            output_content = json.dumps(result, indent=2)
            projected_for_json = result
        elif mode == "patch":
            result_str = decoder.project_patch(raw_text)
            output_content = result_str
            projected_for_json = result_str
        elif mode == "ast":
            tree = decoder.project_ast(raw_text)
            dumped = ast.dump(tree)
            output_content = dumped
            projected_for_json = dumped
        else:
            raise ValueError(f"Unsupported mode: {mode}")

        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(output_content, encoding="utf-8")

        if args.json:
            response = {
                "status": "ok",
                "mode": mode,
                "projected_output": projected_for_json,
                "syntax_errors_repaired": decoder.last_repaired_errors
            }
            print(json.dumps(response, indent=2))
        else:
            print(output_content)

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({
                "status": "error",
                "mode": mode,
                "error": str(e),
                "syntax_errors_repaired": decoder.last_repaired_errors
            }, indent=2))
        else:
            sys.stderr.write(f"Error [{mode}]: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
