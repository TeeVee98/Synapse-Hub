#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""tools/core/brain_indexer.py — Markdown Brain Vault Indexer."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import json
import os
import re
import sys
from typing import Any, Dict, List, Set

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

_WIKILINK_RE = re.compile(r"\[\[([^\[\]|#]+)(?:[#|][^\[\]]*)?\]\]")


@dataclass(frozen=True)
class BrainIndexReportDTO:
    """Typed summary emitted by build_brain_index."""

    brain_dir: str
    indexed_files: int
    index_path: str
    broken_links: List[str]
    ambiguous_links: List[str] = field(default_factory=list)


def _strip_fenced_code_blocks(content: str) -> str:
    """Remove fenced ``` or ~~~ blocks so illustrative [[wikilinks]] do not trigger false broken links."""
    kept: List[str] = []
    active_fence = ""
    for line in content.splitlines():
        stripped = line.lstrip()
        if not active_fence:
            if stripped.startswith("```"):
                active_fence = "```"
                continue
            if stripped.startswith("~~~"):
                active_fence = "~~~"
                continue
            kept.append(line)
        elif stripped.startswith(active_fence):
            active_fence = ""
    return "\n".join(kept)


def build_brain_index(brain_dir: str, dry_run: bool = False) -> BrainIndexReportDTO:
    """Scan a markdown brain vault, detect broken/ambiguous [[wikilinks]], and write index.md."""
    if not os.path.isdir(brain_dir):
        raise FileNotFoundError(f"Brain directory does not exist: {brain_dir}")

    rel_stems: List[str] = []
    stem_targets: Set[str] = {"index"}
    basename_map: Dict[str, List[str]] = {}
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
            stem_targets.add(stem)
            basename_map.setdefault(os.path.basename(stem), []).append(stem)

            with open(full_path, "r", encoding="utf-8") as f:
                content = _strip_fenced_code_blocks(f.read())
            for match in _WIKILINK_RE.finditer(content):
                target = match.group(1).strip()
                if target:
                    discovered_links.append(target)

    broken: Set[str] = set()
    ambiguous: Set[str] = set()
    for link in discovered_links:
        if link in stem_targets:
            continue
        matching_stems = basename_map.get(link)
        if matching_stems:
            if len(matching_stems) > 1:
                ambiguous.add(link)
        else:
            broken.add(link)

    index_path = os.path.join(brain_dir, "index.md")

    if not dry_run:
        lines = ["# Brain Index", "", *(f"- [[{stem}]]" for stem in sorted(rel_stems)), ""]
        with FileLock(index_path, timeout=10.0):
            tmp_path = f"{index_path}.tmp"
            with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(lines))
            os.replace(tmp_path, index_path)

    return BrainIndexReportDTO(
        brain_dir=brain_dir,
        indexed_files=len(rel_stems),
        index_path=index_path,
        broken_links=sorted(broken),
        ambiguous_links=sorted(ambiguous),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build index.md and validate [[wikilinks]] for a Markdown brain vault.")
    parser.add_argument("--dir", required=True, help="Path to brain/ directory.")
    parser.add_argument("--dry-run", action="store_true", help="Scan without writing index.md.")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when broken or ambiguous [[wikilinks]] exist.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    try:
        report = build_brain_index(args.dir, dry_run=args.dry_run)
        if args.json:
            print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
        else:
            print(
                f"[OK] Indexed {report.indexed_files} files "
                f"(broken_links={len(report.broken_links)}, ambiguous_links={len(report.ambiguous_links)})"
            )
        if args.strict and (report.broken_links or report.ambiguous_links):
            return 1
        return 0
    except FileNotFoundError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        else:
            print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
