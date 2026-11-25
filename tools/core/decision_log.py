#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""tools/core/decision_log.py — Append-Only Per-Run TSV Decision & Evidence Logger.

Role Boundary vs `tools/core/decision_ledger.py`:
- `decision_log.py` maintains lightweight, per-run/session append-only TSV trails
  (`decisions.tsv`) during `/solo`, `/goal`, or multi-milestone runs.
- `decision_ledger.py` maintains the long-term, repo-wide architectural decision
  ledger (`docs/decisions.jsonl` and `docs/DECISIONS_OBSIDIAN.md`).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
import sys
from typing import Any, Dict, List

try:
    from tools.core.file_lock import FileLock
except ImportError:
    try:
        from file_lock import FileLock  # type: ignore[no-redef]
    except ImportError:
        class FileLock:  # type: ignore[no-redef]
            """No-op fallback when file_lock is unavailable in isolated contexts."""

            def __init__(self, target_path: str, timeout: float = 10.0, **_kwargs: Any) -> None:
                self.target_path = target_path
                self.timeout = timeout

            def __enter__(self) -> Any:
                return self

            def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                pass

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass

TSV_HEADER = ("ts", "phase", "decision", "why", "evidence", "result")
_FORMULA_PREFIXES = ("=", "+", "-", "@")


@dataclass(frozen=True)
class DecisionRowDTO:
    """Typed row for append-only decisions.tsv audit trails."""

    ts: str
    phase: str
    decision: str
    why: str
    evidence: str
    result: str


def sanitize_tsv_cell(value: str) -> str:
    """Strip tabs/newlines and prefix spreadsheet formula characters."""
    cleaned = str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ").strip()
    if cleaned and cleaned[0] in _FORMULA_PREFIXES:
        cleaned = f"'{cleaned}"
    return cleaned


def append_decision_row(log_path: str, row: DecisionRowDTO) -> bool:
    """Append a single DecisionRowDTO to log_path, creating header if needed."""
    if not row.phase or not row.phase.strip():
        raise ValueError("DecisionRowDTO.phase must be non-empty.")
    if not row.decision or not row.decision.strip():
        raise ValueError("DecisionRowDTO.decision must be non-empty.")

    parent = os.path.dirname(os.path.abspath(log_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    ts_val = row.ts.strip() if row.ts and row.ts.strip() else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cells = [
        sanitize_tsv_cell(ts_val),
        sanitize_tsv_cell(row.phase),
        sanitize_tsv_cell(row.decision),
        sanitize_tsv_cell(row.why),
        sanitize_tsv_cell(row.evidence),
        sanitize_tsv_cell(row.result),
    ]
    with FileLock(log_path, timeout=10.0):
        needs_header = not os.path.isfile(log_path) or os.path.getsize(log_path) == 0
        with open(log_path, "a", encoding="utf-8", newline="\n") as f:
            if needs_header:
                f.write("\t".join(TSV_HEADER) + "\n")
            f.write("\t".join(cells) + "\n")
    return True


def audit_decision_log(log_path: str, strict: bool = False) -> Dict[str, Any]:
    """Audit a decisions.tsv file for existence, header, 6-column integrity, and required values."""
    if not os.path.isfile(log_path):
        return {"exists": False, "valid": False, "row_count": 0, "issues": ["Log file does not exist."]}

    with open(log_path, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\r\n") for line in f if line.strip()]

    if not lines:
        return {"exists": True, "valid": False, "row_count": 0, "issues": ["Log file is empty."]}

    issues: List[str] = []
    header_cols = lines[0].split("\t")
    if tuple(header_cols) != TSV_HEADER:
        issues.append(f"Invalid header at line 1: expected {TSV_HEADER}, got {tuple(header_cols)}.")

    required_cols = ((0, "ts"), (1, "phase"), (2, "decision"), (5, "result"))
    strict_cols = ((3, "why"), (4, "evidence"))

    data_rows = lines[1:]
    for idx, raw_line in enumerate(data_rows, start=2):
        cols = raw_line.split("\t")
        if len(cols) != len(TSV_HEADER):
            issues.append(f"Malformed row at line {idx}: expected {len(TSV_HEADER)} columns, got {len(cols)}.")
            continue
        for col_idx, col_name in required_cols:
            if not cols[col_idx].strip():
                issues.append(f"Empty required column '{col_name}' at line {idx}.")
        if strict:
            for col_idx, col_name in strict_cols:
                if not cols[col_idx].strip():
                    issues.append(f"Strict audit: empty '{col_name}' column at line {idx}.")

    return {
        "exists": True,
        "valid": len(issues) == 0,
        "row_count": len(data_rows),
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Append-only TSV decision and evidence logger.")
    parser.add_argument("--log", required=True, help="Path to decisions.tsv file.")
    parser.add_argument("--audit", action="store_true", help="Audit the TSV file instead of appending.")
    parser.add_argument("--strict", action="store_true", help="Fail audit if why or evidence cells are empty.")
    parser.add_argument("--ts", default="", help="ISO-8601 timestamp (defaults to current UTC).")
    parser.add_argument("--phase", default="", help="Phase or workstream name.")
    parser.add_argument("--decision", default="", help="One-line decision summary.")
    parser.add_argument("--why", default="", help="Plain-language rationale.")
    parser.add_argument("--evidence", default="", help="Pointer to commit, file:line, or test output.")
    parser.add_argument("--result", default="open", help="Outcome state (e.g., tests green, reverted).")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    if args.audit:
        report = audit_decision_log(args.log, strict=args.strict)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"[{'PASS' if report['valid'] else 'FAIL'}] rows={report['row_count']} issues={len(report['issues'])}")
        return 0 if report["valid"] else 1

    try:
        row = DecisionRowDTO(
            ts=args.ts or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            phase=args.phase,
            decision=args.decision,
            why=args.why,
            evidence=args.evidence,
            result=args.result,
        )
        ok = append_decision_row(args.log, row)
        payload = {"appended": ok, "log": args.log, "row": asdict(row)}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"[OK] Appended decision to {args.log}")
        return 0
    except ValueError as exc:
        if args.json:
            print(json.dumps({"appended": False, "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
