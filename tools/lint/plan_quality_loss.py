#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/lint/plan_quality_loss.py — Markdown Plan-Domain Quality Loss Engine
--------------------------------------------------------------------------
Evaluates Spec-Driven Super-Plan Markdown documents in their native domain
(DAG completeness, DTO contract specificity, Verification Matrix rigor,
fenced-code anti-pattern hygiene, and AST anchor density) without triggering
false positives on prose anti-pattern mentions.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import os
import re
import sys
from typing import Any, Dict, List, Tuple

# Enforce UTF-8 stdout/stderr encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass


@dataclass(frozen=True)
class PlanQualityGradientDTO:
    """Single actionable quality critique against a Markdown implementation plan."""

    section: str
    line: int
    category: str
    severity: float
    critique: str
    remediation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section": self.section,
            "line": self.line,
            "category": self.category,
            "severity": self.severity,
            "critique": self.critique,
            "remediation": self.remediation,
        }


@dataclass(frozen=True)
class PlanQualityLossDTO:
    """Aggregated plan-domain TextGrad loss result (loss=0.0 -> quality_score=10.0)."""

    plan_path: str
    loss: float
    quality_score: float
    passed: bool
    gradients: Tuple[PlanQualityGradientDTO, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_path": self.plan_path,
            "loss": self.loss,
            "quality_score": self.quality_score,
            "passed": self.passed,
            "gradients": [g.to_dict() for g in self.gradients],
        }


_STATIC_SLEEP_RE = re.compile(
    r"\b(?:time\.sleep|Thread\.sleep|waitForTimeout|asyncio\.sleep)\s*\(",
)
_UNTYPED_ANY_RE = re.compile(
    r"(?<![\"'])\b([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(?:Any|any)\b"
)
_VAGUE_VERIFICATION_PATTERNS = (
    re.compile(r"\bwrite\s+(?:some\s+)?unit\s+tests?\b", re.IGNORECASE),
    re.compile(r"\bwrite\s+tests?\s+later\b", re.IGNORECASE),
    re.compile(r"\bmanually\s+test\s+feature\b", re.IGNORECASE),
)
_NEGATION_GUARD_RE = re.compile(
    r"\b(?:zero|forbid|forbidden|never|avoid|ban|banned|no\s+vague|prohibit)\b",
    re.IGNORECASE,
)
_DANGEROUS_ROLLBACK_RE = re.compile(
    r"\b(?:git\s+reset\s+--hard|git\s+clean\s+-[a-zA-Z]*f|git\s+push\s+.*--force|rm\s+-[a-zA-Z]*r\s+(?:/|\*|~|\.git))\b",
    re.IGNORECASE,
)
_EXEC_CMD_RE = re.compile(
    r"(?:pytest|npm\s+test|npx\s+playwright\s+test|python3?\s+|jest|vitest|mvn\s+test|go\s+test|cargo\s+test)",
    re.IGNORECASE,
)
_AST_ANCHOR_RE = re.compile(
    r"(?:\(L\d+(?:-L?\d+)?\)|:L\d+(?:-L?\d+)?|::[A-Za-z0-9_.]+|\(AST:\s*[^)]+\))",
    re.IGNORECASE,
)
_PLACEHOLDER_FILE_PREFIXES = (
    "path/",
    "src/modules/target_module",
    "src/target_types",
    "src/caller",
    "obsolete/",
)


def _iter_fenced_code_lines(lines: List[str]) -> List[Tuple[int, str, str, str]]:
    """Returns (1-based line_no, current_section, fence_lang, code_line) inside fenced blocks."""
    results: List[Tuple[int, str, str, str]] = []
    in_fence = False
    fence_lang = ""
    current_section = "preamble"
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if not in_fence and stripped.startswith("#"):
            current_section = stripped.lstrip("#").strip()
        if stripped.startswith("```"):
            if not in_fence:
                in_fence = True
                fence_lang = stripped[3:].strip().lower()
            else:
                in_fence = False
                fence_lang = ""
            continue
        if in_fence:
            results.append((idx, current_section, fence_lang, line))
    return results


def _strip_inline_comment(line: str, fence_lang: str) -> str:
    if fence_lang in ("ts", "typescript", "js", "javascript", "java", "groovy"):
        return line.split("//", 1)[0]
    return line.split("#", 1)[0]


def evaluate_plan_markdown_loss(
    plan_content: str,
    filename: str = "implementation_plan.md",
) -> PlanQualityLossDTO:
    """Computes domain-specific Markdown plan loss (0.0 = 10/10 calibrated) without false test-code triggers."""
    if not (plan_content or "").strip():
        return PlanQualityLossDTO(
            plan_path=filename,
            loss=0.0,
            quality_score=10.0,
            passed=True,
            gradients=(),
        )

    lines = plan_content.splitlines()
    gradients: List[PlanQualityGradientDTO] = []

    # 1. Inspect fenced code blocks ONLY (prose mentions of anti-patterns do not trigger loss)
    in_section_2_langs = {"python", "py", "ts", "typescript", ""}
    fn_start_line: int = 0
    fn_body_lines: int = 0
    fn_section: str = ""
    fn_name: str = ""

    def _flush_fn_body() -> None:
        nonlocal fn_start_line, fn_body_lines, fn_section, fn_name
        if fn_start_line and fn_body_lines > 25:
            gradients.append(
                PlanQualityGradientDTO(
                    section=fn_section or "Data Flow & Interface Signatures",
                    line=fn_start_line,
                    category="ANTI_FULL_CODE_VIOLATION",
                    severity=0.25,
                    critique=(
                        f"Function '{fn_name}' in Section 2 spans {fn_body_lines} executable lines, "
                        "violating the Anti-Full-Code signature-only invariant."
                    ),
                    remediation="Replace full implementation body with typed signature and '...' ellipsis.",
                )
            )
        fn_start_line = 0
        fn_body_lines = 0
        fn_section = ""
        fn_name = ""

    prev_line_no = -1
    for line_no, section, fence_lang, raw_line in _iter_fenced_code_lines(lines):
        if prev_line_no != -1 and line_no > prev_line_no + 1:
            _flush_fn_body()
        prev_line_no = line_no

        code_line = _strip_inline_comment(raw_line, fence_lang)
        stripped = code_line.strip()

        # 1a. Flakiness invariant: static sleep inside fenced code block
        if _STATIC_SLEEP_RE.search(code_line):
            gradients.append(
                PlanQualityGradientDTO(
                    section=section,
                    line=line_no,
                    category="FLAKINESS_INVARIANT",
                    severity=0.35,
                    critique="Static sleep call detected inside fenced code block in implementation plan.",
                    remediation="Replace static sleeps with deterministic smart waits or event-driven assertions.",
                )
            )

        # 1b. Section 2 contract checks (untyped : Any widening & full-body bloat)
        is_sec2 = bool(re.search(r"(?:2[.\s]*)?(?:Data\s+Flow|Interface\s+Signatures|Schemas|DTO)", section, re.IGNORECASE))
        if is_sec2 and fence_lang in in_section_2_langs:
            for m_any in _UNTYPED_ANY_RE.finditer(code_line):
                field_name = m_any.group(1)
                gradients.append(
                    PlanQualityGradientDTO(
                        section=section,
                        line=line_no,
                        category="CONTRACT_WIDENING",
                        severity=0.30,
                        critique=f"Untyped contract widening '{field_name}: Any' weakens Section 2 interface contract.",
                        remediation=f"Specify a concrete scalar, dataclass DTO, or parameterized type for '{field_name}'.",
                    )
                )

            m_def = re.match(r"^(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", stripped)
            if m_def:
                _flush_fn_body()
                fn_start_line = line_no
                fn_body_lines = 0
                fn_section = section
                fn_name = m_def.group(1)
            elif fn_start_line:
                if stripped and not stripped.startswith(('"""', "'''", "...", "pass")):
                    if raw_line.startswith((" ", "\t")):
                        fn_body_lines += 1
                    else:
                        _flush_fn_body()
    _flush_fn_body()

    # 2. Outside fenced code blocks: vague verification & dangerous rollback lines
    in_fence = False
    current_section = "preamble"
    for line_no, raw_line in enumerate(lines, 1):
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped.startswith("#"):
            current_section = stripped.lstrip("#").strip()
            continue

        # 2a. Vague verification prose (ignoring negated rule descriptions like "Zero vague statements like 'write unit tests'")
        if not _NEGATION_GUARD_RE.search(raw_line):
            for pat in _VAGUE_VERIFICATION_PATTERNS:
                if pat.search(raw_line):
                    gradients.append(
                        PlanQualityGradientDTO(
                            section=current_section,
                            line=line_no,
                            category="VAGUE_VERIFICATION",
                            severity=0.40,
                            critique=f"Vague verification phrase detected: '{pat.search(raw_line).group(0)}'.",
                            remediation="Replace with concrete input, expected output, and executable test command.",
                        )
                    )
                    break

        # 2b. Dangerous rollback command on a Rollback / Rollback Hook line
        if re.search(r"Rollback(?:\s+Hook)?\**\s*:", raw_line, re.IGNORECASE):
            if _DANGEROUS_ROLLBACK_RE.search(raw_line):
                gradients.append(
                    PlanQualityGradientDTO(
                        section=current_section,
                        line=line_no,
                        category="DANGEROUS_ROLLBACK",
                        severity=0.45,
                        critique="Destructive rollback command detected on milestone Rollback Hook.",
                        remediation="Use path-scoped restoration (`git checkout -- <files>` or `git restore`).",
                    )
                )

    # 3. Structural section-level checks (only when the corresponding section exists in the plan)
    # 3a. Section 4 Verification Matrix must include concrete executable commands
    m_sec4 = re.search(
        r"^##\s*(?:4[.\s]*)?Verification\s+Matrix[^\n]*\n(.*?)(?=^##\s+|\Z)",
        plan_content,
        re.IGNORECASE | re.DOTALL | re.MULTILINE,
    )
    if m_sec4:
        sec4_body = m_sec4.group(1)
        if not _EXEC_CMD_RE.search(sec4_body):
            sec4_line = plan_content[: m_sec4.start()].count("\n") + 1
            gradients.append(
                PlanQualityGradientDTO(
                    section="4. Verification Matrix",
                    line=sec4_line,
                    category="VERIFICATION_MATRIX_GAP",
                    severity=0.35,
                    critique="Verification Matrix contains zero concrete executable verification commands.",
                    remediation="Attach executable `pytest`, `npm test`, or `python3` commands to each TC row.",
                )
            )

    # 3b. Section 1 [MODIFY] targets should include AST/line anchors when referencing real files
    m_sec1 = re.search(
        r"^##\s*(?:1[.\s]*)?Affected\s+Files[^\n]*\n(.*?)(?=^##\s+|\Z)",
        plan_content,
        re.IGNORECASE | re.DOTALL | re.MULTILINE,
    )
    if m_sec1:
        sec1_body = m_sec1.group(1)
        modify_rows = [
            ln for ln in sec1_body.splitlines()
            if "|" in ln and "[MODIFY]" in ln.upper()
            and not any(pref in ln for pref in _PLACEHOLDER_FILE_PREFIXES)
        ]
        if modify_rows and not any(_AST_ANCHOR_RE.search(ln) for ln in modify_rows):
            sec1_line = plan_content[: m_sec1.start()].count("\n") + 1
            gradients.append(
                PlanQualityGradientDTO(
                    section="1. Affected Files & Blast Radius",
                    line=sec1_line,
                    category="MISSING_AST_ANCHORS",
                    severity=0.20,
                    critique="Section 1 [MODIFY] entries lack AST symbol (`::Symbol` / `(AST: ...)`) or line anchors.",
                    remediation="Anchor each `[MODIFY]` file to its target symbol or line range.",
                )
            )

    raw_loss = sum(g.severity for g in gradients)
    loss = round(min(1.0, max(0.0, raw_loss)), 4)
    quality_score = round(max(0.0, 10.0 * (1.0 - loss)), 2)
    passed = loss == 0.0

    return PlanQualityLossDTO(
        plan_path=filename,
        loss=loss,
        quality_score=quality_score,
        passed=passed,
        gradients=tuple(gradients),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Plan-Domain Markdown Quality Loss Evaluator (tools/lint/plan_quality_loss.py)"
    )
    parser.add_argument("--file", required=True, help="Path to Markdown implementation plan")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON output")
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        err_payload = {"passed": False, "error": f"File not found: {args.file}"}
        if args.json:
            print(json.dumps(err_payload, indent=2))
        else:
            print(f"[FAIL] File not found: {args.file}")
        return 1

    with open(args.file, "r", encoding="utf-8", errors="replace") as fh:
        content = fh.read()

    result = evaluate_plan_markdown_loss(content, filename=os.path.basename(args.file))
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        status = "PASS" if result.passed else "FAIL"
        print(
            f"[{status}] Plan Quality Score: {result.quality_score}/10.0 "
            f"(loss={result.loss}, gradients={len(result.gradients)})"
        )
        for g in result.gradients:
            print(f"  - [{g.category}] L{g.line} ({g.section}): {g.critique}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
