#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Humanize & Anti-AI Slop Linter (Enterprise QA Hub)
-------------------------------------------------
Scans documentation, test docstrings, commit messages, and PR descriptions
to detect and eliminate robotic AI buzzwords, cliches, and formatting quirks.
Provides clear, natural, human-grade plain text replacements.

Inspired by fcakyon/claude-codex-settings and Wikipedia's Signs of AI Writing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Enforce UTF-8 output encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def masked(text: str, keep: List[bool]) -> str:
    """Mask excluded characters with spaces while preserving newlines."""
    return "".join(char if char in "\r\n" or keep[i] else " " for i, char in enumerate(text))


def md_text(text: str) -> str:
    """Mask fenced and inline Markdown code without changing source offsets."""
    keep = [True] * len(text)
    offset = 0
    fence = None
    for line in text.splitlines(keepends=True):
        match = re.match(r" {0,3}(`{3,}|~{3,})(.*)$", line.rstrip("\r\n"))
        if fence:
            keep[offset : offset + len(line)] = [False] * len(line)
            if (
                match
                and match.group(1)[0] == fence[0]
                and len(match.group(1)) >= len(fence)
                and not match.group(2).strip()
            ):
                fence = None
        elif match:
            fence = match.group(1)
            keep[offset : offset + len(line)] = [False] * len(line)
        offset += len(line)

    i = 0
    while i < len(text):
        if text[i] != "`" or not keep[i]:
            i += 1
            continue
        end = i
        while end < len(text) and text[end] == "`":
            end += 1
        delimiter = text[i:end]
        close = text.find(delimiter, end)
        if close < 0:
            i = end
            continue
        keep[i : close + len(delimiter)] = [False] * (close + len(delimiter) - i)
        i = close + len(delimiter)
    return masked(text, keep)


# Stock AI buzzwords with direct plain-word swaps
BUZZWORD_SWAPS: Dict[str, str] = {
    "leverage": "use",
    "utilize": "use",
    "plethora": "many",
    "myriad": "many",
    "delve": "look at",
    "paradigm": "model",
    "tapestry": "mix",
    "showcase": "show",
    "prose": "text",
    "realm": "area",
    "landscape": "field",
    "innovative": "new",
    "transformative": "major",
    "unprecedented": "new",
    "consolidate": "merge",
    "modernize": "update",
    "streamline": "simplify",
    "flexible": "adjustable",
    "establish": "set up",
    "enhance": "improve",
    "enhanced": "better",
    "comprehensive": "full",
    "optimize": "improve",
    "unequivocally": "clearly",
    "symphony": "mix",
    "delicate": "fragile",
    "begrudgingly": "reluctantly",
    "merit": "worth",
    "albeit": "though",
    "reverent": "respectful",
    "revolutionize": "change",
    "revolutionizing": "changing",
    "crucially": "drop it",
    "remarkably": "drop it",
    "seamlessly": "drop it",
    "manifestation": "sign",
    "testament": "sign",
    "prominent": "clear",
    "underscoring": "showing",
    "symbolizing": "showing",
    "cultivate": "build",
    "cultivating": "building",
    "foster": "build",
    "fostering": "building",
    "encompass": "cover",
    "encompassing": "covering",
    "facilitate": "help",
    "facilitating": "helping",
    "emphasize": "show",
    "emphasizing": "showing",
    "embody": "show",
    "embodying": "showing",
    "underlies": "drives",
    "evoke": "stir",
    "enduring": "lasting",
    "nestled": "in",
    "fascinating": "notable",
    "vibrant": "lively",
    "game-changing": "big",
    "cutting-edge": "latest",
    "robust": "strong",
    "pivotal": "key",
    "deep dive": "detailed review",
    "garner": "collect",
    "intricate": "complex",
    "meticulous": "careful",
    "interplay": "interaction",
    "bolster": "strengthen",
    "bolstered": "strengthened",
    "boast": "have",
    "boasts": "has",
    "valuable": "useful",
}

# Filler cliches and robotic openers
CLICHE_PHRASES: List[Tuple[str, str]] = [
    (r"\bever[- ]evolving\b", "drop 'ever-evolving'"),
    (r"\bfast[- ]paced world\b", "drop 'fast-paced world'"),
    (r"\ba testament to\b", "say what it shows"),
    (r"\bvibrant tapestry\b", "drop the cliche"),
    (r"\baims to explore\b", "say 'covers'"),
    (r"\baims to bridge\b", "say what it connects"),
    (r"\bfoster innovation\b", "say what gets built"),
    (r"\bmeasured steps\b", "drop the cliche"),
    (r"\bpracticed efficiency\b", "drop the cliche"),
    (r"\bstark reminder\b", "drop the cliche"),
    (r"\bit is important to note\b", "state the point directly"),
    (r"\bas an ai language model\b", "drop it completely"),
    (r"\bin conclusion\b", "drop it"),
    (r"\bin summary\b", "drop it"),
    (r"\bto sum up\b", "drop it"),
    (r"\bplays? a \w+ role in shaping\b", "say what it does directly"),
    (r"\bstands as\b", "replace with 'is'"),
    (r"\bserves as\b", "replace with 'is'"),
    (r"\bplays a pivotal role\b", "replace with 'is key'"),
    (r"\breflects a broader trend\b", "say 'shows a trend'"),
    (r"\bmarks a significant shift\b", "say 'marks a shift'"),
    (r"\bin today's ever-evolving landscape\b", "say 'today'"),
]

# Words that are fine in isolation, but suspicious when piled up (>= 3 times)
PILEUP_LIMIT = 3
PILEUP_WORDS = [
    "crucial",
    "essential",
    "vital",
    "significant",
    "moreover",
    "furthermore",
    "additionally",
    "aligns",
    "explore",
    "prompted",
]

# AI punctuation quirks
PUNCTUATION_MARKS: Dict[str, Tuple[str, str]] = {
    "—": ("em-dash", "use commas, hyphens, or periods"),
    "§": ("section sign", "use word 'Section' or remove"),
    ";": ("semicolon in prose", "use comma, period, or separate sentence"),
}


def build_inflection_pattern(word: str) -> re.Pattern:
    """Build regex pattern matching word and its common verb/noun inflections."""
    w = word.lower()
    prefix = r"(?<![a-zA-Z0-9])"
    suffix = r"(?![a-zA-Z0-9])"

    if " " in w or "-" in w:
        return re.compile(rf"{prefix}{re.escape(w)}{suffix}", re.IGNORECASE)

    # Verbs ending in 'e' (leverage, utilize, optimize, streamline, delve, enhance, etc.)
    if w.endswith("e") and len(w) > 3:
        stem = w[:-1]
        return re.compile(rf"{prefix}{re.escape(stem)}(?:e|es|ed|ing){suffix}", re.IGNORECASE)

    # Verbs ending in 'y' (embody)
    if w.endswith("y") and len(w) > 3:
        stem = w[:-1]
        return re.compile(rf"{prefix}(?:{re.escape(w)}|{re.escape(stem)}ies|{re.escape(stem)}ied|{re.escape(w)}ing){suffix}", re.IGNORECASE)

    # Verbs ending in consonants (bolster, boast, foster, garner)
    if w in {"bolster", "boast", "foster", "garner", "showcase", "transform"}:
        return re.compile(rf"{prefix}{re.escape(w)}(?:s|ed|ing)?{suffix}", re.IGNORECASE)

    return re.compile(rf"{prefix}{re.escape(w)}{suffix}", re.IGNORECASE)


@dataclass
class LintIssue:
    line_number: int
    matched_text: str
    issue_type: str  # 'buzzword' | 'cliche' | 'pileup' | 'punctuation'
    suggestion: str
    context: str


class HumanizeLinter:
    """Lints text for AI writing artifacts and robotic buzzwords."""

    def __init__(self, check_pileup: bool = True):
        self.check_pileup = check_pileup
        # Compile word boundaries for buzzwords with inflections
        self.buzzword_patterns = {
            word: (build_inflection_pattern(word), swap)
            for word, swap in BUZZWORD_SWAPS.items()
        }
        # Compile cliches
        self.cliche_patterns = [
            (re.compile(pattern, re.IGNORECASE), suggestion)
            for pattern, suggestion in CLICHE_PHRASES
        ]
        # Compile pileup words
        self.pileup_patterns = {
            word: re.compile(rf"(?<![a-zA-Z0-9]){re.escape(word)}(?![a-zA-Z0-9])", re.IGNORECASE)
            for word in PILEUP_WORDS
        }

    def lint_text(self, text: str, source_label: str = "<input>") -> List[LintIssue]:
        """Lint text line-by-line while masking code fences and inline backticks."""
        masked_content = md_text(text)
        issues: List[LintIssue] = []
        lines_orig = text.splitlines()
        lines_masked = masked_content.splitlines()

        for idx, line_masked in enumerate(lines_masked, start=1):
            line_orig = lines_orig[idx - 1] if idx - 1 < len(lines_orig) else ""
            stripped = line_masked.strip()
            if not stripped:
                continue
            # Scan markdown headings for buzzwords by stripping leading '#' characters
            if stripped.startswith("#"):
                heading_masked = line_masked.lstrip("# \t")
                heading_orig = line_orig.lstrip("# \t")
                offset = len(line_orig) - len(heading_orig)
                for word, (pattern, swap) in self.buzzword_patterns.items():
                    for match in pattern.finditer(heading_masked):
                        matched_text = line_orig[offset + match.start() : offset + match.end()]
                        issues.append(
                            LintIssue(
                                line_number=idx,
                                matched_text=matched_text,
                                issue_type="buzzword",
                                suggestion=f"replace with '{swap}'",
                                context=line_orig.strip()[:80],
                            )
                        )
                continue

            # Check buzzwords on masked line
            for word, (pattern, swap) in self.buzzword_patterns.items():
                for match in pattern.finditer(line_masked):
                    matched_text = line_orig[match.start() : match.end()]
                    issues.append(
                        LintIssue(
                            line_number=idx,
                            matched_text=matched_text,
                            issue_type="buzzword",
                            suggestion=f"replace with '{swap}'",
                            context=line_orig.strip()[:80],
                        )
                    )

            # Check cliches on masked line
            for pattern, suggestion in self.cliche_patterns:
                for match in pattern.finditer(line_masked):
                    matched_text = line_orig[match.start() : match.end()]
                    issues.append(
                        LintIssue(
                            line_number=idx,
                            matched_text=matched_text,
                            issue_type="cliche",
                            suggestion=suggestion,
                            context=line_orig.strip()[:80],
                        )
                    )

            # Check punctuation marks on masked line (pre-mask HTML entities with spaces)
            punct_line = re.sub(r"&[a-zA-Z0-9#]+;", lambda m: " " * len(m.group(0)), line_masked)
            for mark, (name, suggestion) in PUNCTUATION_MARKS.items():
                if mark in punct_line:
                    issues.append(
                        LintIssue(
                            line_number=idx,
                            matched_text=mark,
                            issue_type="punctuation",
                            suggestion=f"{name} detected: {suggestion}",
                            context=line_orig.strip()[:80],
                        )
                    )

        # Document-wide pileup check on masked text
        if self.check_pileup:
            for word, pattern in self.pileup_patterns.items():
                matches = list(pattern.finditer(masked_content))
                if len(matches) >= PILEUP_LIMIT:
                    first_match = matches[0]
                    line_no = masked_content[: first_match.start()].count("\n") + 1
                    issues.append(
                        LintIssue(
                            line_number=line_no,
                            matched_text=word,
                            issue_type="pileup",
                            suggestion=(
                                f"word '{word}' repeated {len(matches)} times (>= {PILEUP_LIMIT}). "
                                "Vary vocabulary or simplify sentence structure."
                            ),
                            context=f"Repeated {len(matches)} times across document",
                        )
                    )

        return issues

    def lint_file(self, file_path: Path | str) -> List[LintIssue]:
        """Lint a single file (markdown, docstring, commit text)."""
        path = Path(file_path)
        if not path.is_file():
            return []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []
        return self.lint_text(content, source_label=str(path))


def format_cli_report(issues: List[LintIssue], source_name: str) -> str:
    """Format lint issues into human-friendly CLI string."""
    if not issues:
        return f"✨ {source_name}: Clean! No AI buzzwords or cliches detected."

    out = [f"⚠️  {source_name}: Found {len(issues)} writing/tone issue(s):"]
    for issue in issues:
        out.append(
            f"  - L{issue.line_number} [{issue.issue_type.upper()}]: "
            f"'{issue.matched_text}' -> {issue.suggestion}"
        )
        if issue.context:
            out.append(f"    Excerpt: \"{issue.context}\"")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(
        description="Humanize & Anti-AI Slop Linter for Enterprise QA"
    )
    parser.add_argument("--text", "-t", type=str, help="Text string to lint")
    parser.add_argument("--file", "-f", type=str, help="File path to lint")
    parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )
    parser.add_argument(
        "--strict", action="store_true", help="Exit code 1 if issues found"
    )
    args = parser.parse_args()

    linter = HumanizeLinter()
    issues: List[LintIssue] = []
    source = "<input>"

    if args.text:
        source = "string_input"
        issues = linter.lint_text(args.text, source_label=source)
    elif args.file:
        target = Path(args.file)
        if not target.is_file():
            sys.stderr.write(f"Error: File not found or not a regular file: {args.file}\n")
            sys.exit(2)
        source = args.file
        issues = linter.lint_file(target)
    else:
        # Read from stdin if piped
        if not sys.stdin.isatty():
            content = sys.stdin.read()
            source = "stdin"
            issues = linter.lint_text(content, source_label=source)
        else:
            parser.print_help()
            sys.exit(0)

    if args.json:
        result = {
            "source": source,
            "issue_count": len(issues),
            "clean": len(issues) == 0,
            "issues": [asdict(i) for i in issues],
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_cli_report(issues, source))

    if args.strict and issues:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
