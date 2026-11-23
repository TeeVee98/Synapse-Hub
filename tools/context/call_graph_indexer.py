#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
"""
Call Graph & Fan-In Indexer with Incremental Disk Cache
Part of Synapse Hub — Created by Thế Vị (@TeeVee98) under MIT License.

Maintains an indexed graph of file dependencies, symbol callers, and Fan-In scores
across code files (.py, .ts, .js, .java, .groovy).
Caches graph structure to `.cache/call_graph_index.json` with mtime validation
for sub-5ms lookup latency.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Set


_CODE_EXTS = (".py", ".ts", ".js", ".java", ".groovy")
_IGNORE_DIRS = {
    ".git", ".cache", "node_modules", "__pycache__",
    ".venv", "venv", ".idea", ".vscode", "dist", "build"
}


@dataclass
class CallGraphIndex:
    repo_root: str
    files: Dict[str, Dict[str, Any]]  # rel_path -> {mtime, base, refs}
    fan_in: Dict[str, int]            # rel_path -> count of dependent files
    dependents: Dict[str, List[str]]  # rel_path -> list of files importing/referencing it
    last_updated: float

    def get_fan_in(self, target: str) -> int:
        """Returns Fan-In count for given target file or base name."""
        rel = self._normalize_target(target)
        if rel in self.fan_in:
            return self.fan_in[rel]

        # Fallback by base name
        base = os.path.splitext(os.path.basename(rel))[0]
        for f, count in self.fan_in.items():
            if os.path.splitext(os.path.basename(f))[0] == base:
                return count
        return 0

    def get_dependents(self, target: str) -> List[str]:
        """Returns list of files that reference or import target."""
        rel = self._normalize_target(target)
        if rel in self.dependents:
            return self.dependents[rel]

        base = os.path.splitext(os.path.basename(rel))[0]
        for f, deps in self.dependents.items():
            if os.path.splitext(os.path.basename(f))[0] == base:
                return deps
        return []

    def get_dependencies(self, target: str) -> List[str]:
        """Returns list of files referenced by target."""
        rel = self._normalize_target(target)
        f_info = self.files.get(rel)
        if not f_info:
            base = os.path.splitext(os.path.basename(rel))[0]
            for f, info in self.files.items():
                if os.path.splitext(os.path.basename(f))[0] == base:
                    f_info = info
                    break
        if not f_info:
            return []
        return f_info.get("refs", [])

    def _normalize_target(self, target: str) -> str:
        if os.path.isabs(target):
            try:
                return os.path.relpath(target, self.repo_root)
            except ValueError:
                return target
        return os.path.normpath(target)


def _scan_repo_files(repo_root: str) -> Dict[str, float]:
    """Scans all eligible code files in repo returning {rel_path: mtime}."""
    results: Dict[str, float] = {}
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS]
        for f in files:
            if f.endswith(_CODE_EXTS):
                abs_p = os.path.join(root, f)
                rel_p = os.path.relpath(abs_p, repo_root)
                try:
                    results[rel_p] = os.path.getmtime(abs_p)
                except OSError:
                    continue
    return results


def _extract_file_references(abs_path: str, all_bases: Dict[str, str]) -> List[str]:
    """
    Scans a source file for imports or mentions of known module bases.
    all_bases: {base_name: rel_path}
    """
    try:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        return []

    refs: Set[str] = set()
    my_rel = os.path.basename(abs_path)

    for base, target_rel in all_bases.items():
        if os.path.basename(target_rel) == my_rel:
            continue
        # Fast substring check before regex
        if base in content:
            # Word boundary check
            if re.search(rf"\b{re.escape(base)}\b", content):
                refs.add(target_rel)

    return sorted(list(refs))


def get_or_build_call_graph(
    repo_root: str,
    cache_dir: Optional[str] = None,
    force_rebuild: bool = False
) -> CallGraphIndex:
    """
    Loads CallGraphIndex from cache if valid; incrementally updates stale entries;
    writes back to cache on modifications.
    """
    if cache_dir is None:
        cache_dir = os.path.join(repo_root, ".cache")
    cache_path = os.path.join(cache_dir, "call_graph_index.json")

    cached_data: Optional[Dict[str, Any]] = None
    if not force_rebuild and os.path.isfile(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
        except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
            cached_data = None

    current_files = _scan_repo_files(repo_root)

    # Map base names to target rel paths
    all_bases: Dict[str, str] = {}
    for rel_p in current_files:
        base = os.path.splitext(os.path.basename(rel_p))[0]
        if len(base) > 2:
            all_bases[base] = rel_p

    files_index: Dict[str, Dict[str, Any]] = {}
    dirty = False

    if cached_data and "files" in cached_data:
        old_files = cached_data.get("files", {})
        # Keep unchanged files
        for rel_p, mtime in current_files.items():
            if rel_p in old_files and abs(old_files[rel_p].get("mtime", 0) - mtime) < 0.001:
                files_index[rel_p] = old_files[rel_p]
            else:
                dirty = True
        if len(files_index) != len(old_files):
            dirty = True
    else:
        dirty = True

    # Re-index files that need update
    if dirty:
        for rel_p, mtime in current_files.items():
            if rel_p not in files_index:
                abs_p = os.path.join(repo_root, rel_p)
                refs = _extract_file_references(abs_p, all_bases)
                base = os.path.splitext(os.path.basename(rel_p))[0]
                files_index[rel_p] = {
                    "mtime": mtime,
                    "base": base,
                    "refs": refs
                }

    # Compute inverted dependents and fan-in
    dependents_map: Dict[str, List[str]] = {f: [] for f in current_files}
    for caller, info in files_index.items():
        for target_rel in info.get("refs", []):
            if target_rel in dependents_map:
                dependents_map[target_rel].append(caller)

    fan_in_map: Dict[str, int] = {
        f: len(callers) for f, callers in dependents_map.items()
    }

    index = CallGraphIndex(
        repo_root=repo_root,
        files=files_index,
        fan_in=fan_in_map,
        dependents=dependents_map,
        last_updated=time.time()
    )

    # Persist cache if dirty
    if dirty:
        try:
            os.makedirs(cache_dir, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({
                    "version": "1.0",
                    "repo_root": ".",
                    "last_updated": index.last_updated,
                    "files": files_index,
                    "fan_in": fan_in_map,
                    "dependents": dependents_map
                }, f, indent=2)
        except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
            pass

    return index


def main() -> int:
    parser = argparse.ArgumentParser(description="Call Graph & Fan-In Indexer")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--file", "-f", help="Query target file for fan-in and dependents")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild cache")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    args = parser.parse_args()

    repo = os.path.abspath(args.repo_root)
    t0 = time.perf_counter()
    graph = get_or_build_call_graph(repo, force_rebuild=args.rebuild)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    if args.file:
        fan_in = graph.get_fan_in(args.file)
        dependents = graph.get_dependents(args.file)
        if args.json:
            print(json.dumps({
                "target": args.file,
                "fan_in": fan_in,
                "dependents": dependents,
                "lookup_time_ms": elapsed_ms
            }, indent=2))
        else:
            print(f"Target: {args.file}")
            print(f"Fan-In: {fan_in}")
            print(f"Dependents ({len(dependents)}):")
            for d in dependents[:10]:
                print(f"  - {d}")
            if len(dependents) > 10:
                print(f"  ... and {len(dependents) - 10} more")
            print(f"Lookup completed in {elapsed_ms:.2f}ms")
    else:
        top_fan = sorted(graph.fan_in.items(), key=lambda x: x[1], reverse=True)[:10]
        if args.json:
            print(json.dumps({
                "total_files": len(graph.files),
                "top_fan_in": top_fan,
                "lookup_time_ms": elapsed_ms
            }, indent=2))
        else:
            print(f"Indexed {len(graph.files)} files in {elapsed_ms:.2f}ms")
            print("Top 10 Fan-In targets:")
            for f, count in top_fan:
                print(f"  {count:3d}  {f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
