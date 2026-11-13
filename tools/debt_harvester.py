#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/debt_harvester.py — Technical Debt & Shortcut Harvester
-----------------------------------------------------------
Scans repositories for deliberate simplification markers ('shortcut:' or 'ponytail:').
Compiles them into a structured Technical Debt Ledger so pragmatic compromises
and deferred upgrades are tracked and do not rot into forgotten technical debt.

Usage:
  python3 tools/debt_harvester.py [target_dir]
  python3 tools/debt_harvester.py [target_dir] --output DEBT_LEDGER.md
  python3 tools/debt_harvester.py [target_dir] --json
  python3 tools/debt_harvester.py [target_dir] --keyword "custom-tag:"
"""

import os
import sys
import re
import json
import argparse
from typing import Dict, List, Any, Optional

# UTF-8 stdout encoding enforcement
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception as exc:
        _ = exc

# Default directories to ignore during scan
IGNORED_DIRS = {
    ".git", "node_modules", "dist", "build", ".next", "out",
    "venv", ".venv", "env", ".env", "__pycache__", ".idea",
    ".vscode", "coverage", ".mypy_cache", ".ruff_cache",
    ".pytest_cache", ".sandbox_snapshots", "graphify-out",
    "claude-ecosystem-repos", "Reports", "reports", "TestReports",
    "allure-results", "results", "execution_results", "bin", "Libs", "Drivers"
}

# Supported comment markers across major languages
# Supports: # (Python, Bash, YAML), // (JS, TS, Java, Groovy, C, C++),
# /* ... */, -- (SQL, Lua), <!-- (HTML, XML, Markdown)
DEBT_REGEX = re.compile(
    r'(?:#|//|/\*|--|<!--)\s*(?:shortcut|ponytail):\s*(.+?)(?:\*/|-->)?$',
    re.IGNORECASE
)


class ShortcutEntry:
    def __init__(self, file_path: str, line_no: int, raw_comment: str):
        self.file_path = file_path
        self.line_no = line_no
        self.raw_comment = raw_comment.strip()
        self.description = ""
        self.ceiling = ""
        self.upgrade_trigger = ""
        self.owner = "@TeeVee98 (Core Hub)"
        self.sla = "v4.1.0-Sprint"
        self.has_trigger = False
        self._parse()

    def _parse(self):
        text = self.raw_comment
        # Format patterns:
        # 1. shortcut: <desc>, ceiling: <limit>, upgrade: <trigger>, owner: <owner>, sla: <date>
        # 2. shortcut: <desc>, <limit>, <trigger>
        # 3. shortcut: <limit>, <when to upgrade>

        parts = [p.strip() for p in text.split(',') if p.strip()]

        # Check explicit labels
        ceiling_match = re.search(r'(?:ceiling|limit):\s*([^,]+)', text, re.IGNORECASE)
        upgrade_match = re.search(r'(?:upgrade|when|trigger):\s*([^,]+)', text, re.IGNORECASE)
        owner_match = re.search(r'owner:\s*([^,]+)', text, re.IGNORECASE)
        sla_match = re.search(r'(?:sla|due):\s*([^,]+)', text, re.IGNORECASE)

        if owner_match:
            self.owner = owner_match.group(1).strip()
        if sla_match:
            self.sla = sla_match.group(1).strip()

        if ceiling_match or upgrade_match:
            self.ceiling = ceiling_match.group(1).strip() if ceiling_match else ""
            self.upgrade_trigger = upgrade_match.group(1).strip() if upgrade_match else ""
            # Description is what's left before ceiling/upgrade/owner/sla
            desc_part = re.split(r'(?:ceiling|limit|upgrade|when|trigger|owner|sla|due):', text, flags=re.IGNORECASE)[0]
            self.description = desc_part.strip().rstrip(',')
        elif len(parts) >= 2:
            self.description = parts[0]
            self.ceiling = parts[1]
            if len(parts) >= 3:
                self.upgrade_trigger = parts[2]
            else:
                self.upgrade_trigger = parts[1]
        elif len(parts) == 1:
            self.description = parts[0]
            self.ceiling = "Not specified"
            self.upgrade_trigger = ""

        if self.upgrade_trigger:
            self.has_trigger = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file_path,
            "line": self.line_no,
            "description": self.description or self.raw_comment,
            "ceiling": self.ceiling or "Not specified",
            "upgrade_trigger": self.upgrade_trigger or "No trigger specified",
            "owner": self.owner,
            "sla": self.sla,
            "has_trigger": self.has_trigger,
            "raw": self.raw_comment
        }


def scan_directory(target_dir: str, keyword: Optional[str] = None) -> List[ShortcutEntry]:
    """Scans all non-ignored source files in target_dir for shortcut/debt markers."""
    target_dir = os.path.abspath(target_dir)
    results: List[ShortcutEntry] = []

    pattern = DEBT_REGEX
    if keyword:
        escaped = re.escape(keyword.rstrip(':'))
        pattern = re.compile(
            rf'(?:#|//|/\*|--|<!--)\s*{escaped}:\s*(.+?)(?:\*/|-->)?$',
            re.IGNORECASE
        )

    for root, dirs, files in os.walk(target_dir):
        # Exclude ignored directories in-place
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith('.')]

        for f in sorted(files):
            # Skip non-text or binary files
            ext = os.path.splitext(f)[1].lower()
            if ext in {".png", ".jpg", ".jpeg", ".svg", ".zip", ".tar", ".gz", ".lock", ".ico", ".pdf"}:
                continue

            file_path = os.path.join(root, f)
            rel_path = os.path.relpath(file_path, target_dir)

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                    for line_idx, line in enumerate(fh, start=1):
                        match = pattern.search(line)
                        if match:
                            comment_body = match.group(1).strip()
                            # Filter false positives like documentation describing the marker itself
                            if "shortcut: <" in comment_body or "shortcut: (" in comment_body:
                                continue
                            results.append(ShortcutEntry(rel_path, line_idx, comment_body))
            except Exception:
                continue

    return results


def format_markdown(entries: List[ShortcutEntry], target_dir: str) -> str:
    """Renders shortcut debt entries into a structured Markdown ledger."""
    total = len(entries)
    no_trigger = sum(1 for e in entries if not e.has_trigger)

    lines = [
        "# Technical Debt & Shortcut Ledger",
        "",
        "> **Ledger Policy:** Deliberate shortcuts prevent over-engineering. Track limits and upgrade triggers so they never rot silently into permanent defects.",
        "",
        f"- **Repository:** `{os.path.basename(target_dir)}`",
        f"- **Total Shortcuts:** `{total}`",
        f"- **Missing Upgrade Triggers:** `{no_trigger}` " + ("⚠️ *(Action Required)*" if no_trigger > 0 else "✅ *(All tracked)*"),
        "",
        "---",
        "",
    ]

    if not entries:
        lines.append("🎉 **No shortcut debt found. Clean ledger.**")
        return "\n".join(lines)

    lines.append("| Location | Description | Ceiling (Limit) | Upgrade Trigger | Owner | SLA | Status |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

    for e in entries:
        status = "✅ Tracked" if e.has_trigger else "⚠️ `no-trigger`"
        loc = f"`{e.file_path}:{e.line_no}`"
        lines.append(f"| {loc} | {e.description} | {e.ceiling} | {e.upgrade_trigger or 'None'} | {e.owner} | {e.sla} | {status} |")

    lines.append("")
    lines.append("### Recommended Action")
    if no_trigger > 0:
        lines.append(f"1. Review the `{no_trigger}` shortcut(s) tagged `no-trigger` above and define concrete upgrade conditions.")
    else:
        lines.append("1. All tracked shortcuts have defined upgrade boundaries. Review them during sprint refactoring cycles.")
    lines.append("2. Run `agent-qa debt` in CI to monitor debt accumulation.")

    return "\n".join(lines)


def run_debt_harvest(target_dir: str, keyword: Optional[str] = None, output_file: Optional[str] = None, as_json: bool = False) -> int:
    """Executes the debt scan and prints/writes results."""
    entries = scan_directory(target_dir, keyword)
    total = len(entries)
    no_trigger = sum(1 for e in entries if not e.has_trigger)

    if as_json:
        payload = {
            "target": os.path.abspath(target_dir),
            "total": total,
            "no_trigger_count": no_trigger,
            "items": [e.to_dict() for e in entries]
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    md_report = format_markdown(entries, target_dir)

    if output_file:
        out_path = os.path.abspath(output_file)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md_report)
        print(f"\n✅ Technical Debt Ledger saved to: {out_path} ({total} entries)")
    else:
        print("\n" + md_report)

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Harvest shortcut: and deliberate debt comments into a tracked technical debt ledger."
    )
    parser.add_argument("target", nargs="?", default=".", help="Directory to scan (default: current directory)")
    parser.add_argument("--keyword", "-k", default=None, help="Custom marker keyword (default: shortcut or ponytail)")
    parser.add_argument("--output", "-o", default=None, help="Save report to Markdown file")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    sys.exit(run_debt_harvest(args.target, args.keyword, args.output, args.json))


if __name__ == "__main__":
    main()
