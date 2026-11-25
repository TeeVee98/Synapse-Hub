#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""tools/core/brain_indexer.py — Markdown Brain Vault Indexer."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
import re
import sys
from typing import List, Set

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass

_WIKILINK_RE = re.compile(r"\[\[([^\[\]|#]+)(?:[#|][^\[\]]*)?\]\]")


@dataclass(frozen=True)
class BrainIndexReportDTO:
    """Typed summary emitted by build_brain_index."""

    brain_dir: str
    indexed_files: int
    index_path: str
    broken_links: List[str]


def build_brain_index(brain_dir: str, dry_run: bool = False) -> BrainIndexReportDTO:
    """Scan a markdown brain vault, detect broken [[wikilinks]], and write index.md."""
    if not os.path.isdir(brain_dir):
        raise FileNotFoundError(f"Brain directory does not exist: {brain_dir}")

    rel_stems: List[str] = []
    known_targets: Set[str] = {"index"}
    discovered_links: List[str] = []

    for root, dirs, files in os.walk(brain_dir):
        dirs.sort()
        for fname in sorted(files):
            if not fname.endswith(".md"):
                continue
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, brain_dir).replace("\\", "/")
            if rel_path == "index.md":
                continue
            stem = rel_path[:-3]
            rel_stems.append(stem)
            known_targets.add(stem)
            known_targets.add(os.path.basename(stem))

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            for match in _WIKILINK_RE.finditer(content):
                target = match.group(1).strip()
                if target:
                    discovered_links.append(target)

    broken = sorted({link for link in discovered_links if link not in known_targets})
    index_path = os.path.join(brain_dir, "index.md")

    if not dry_run:
        lines = ["# Brain Index", "", *(f"- [[{stem}]]" for stem in sorted(rel_stems)), ""]
        tmp_path = f"{index_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines))
        os.replace(tmp_path, index_path)

    return BrainIndexReportDTO(
        brain_dir=brain_dir,
        indexed_files=len(rel_stems),
        index_path=index_path,
        broken_links=broken,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build index.md and validate [[wikilinks]] for a Markdown brain vault.")
    parser.add_argument("--dir", required=True, help="Path to brain/ directory.")
    parser.add_argument("--dry-run", action="store_true", help="Scan without writing index.md.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    try:
        report = build_brain_index(args.dir, dry_run=args.dry_run)
        if args.json:
            print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
        else:
            print(f"[OK] Indexed {report.indexed_files} files (broken_links={len(report.broken_links)})")
        return 0
    except FileNotFoundError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        else:
            print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
