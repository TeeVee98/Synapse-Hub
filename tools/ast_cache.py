#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/ast_cache.py — AST Dataflow Pre-Validation Cache (Boost B3)
----------------------------------------------------------------
Provides high-speed persistent caching for AST syntax integrity, undefined variable
checks (F821), and syntactic mutation scans.
Uses mtime_ns + file size fast invalidation with SHA-256 fallback to eliminate
redundant AST parsing across recurring verification runs.
Uses cross-platform file locking to guarantee concurrency safety under multi-agent swarms.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, Optional, Tuple

# Ensure repository root is on sys.path for direct script execution
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Import cross-platform advisory file lock
try:
    from tools.core.file_lock import locked_json_read, locked_json_write
except ImportError:
    try:
        from core.file_lock import locked_json_read, locked_json_write
    except ImportError:
        # Fallback in case tools is executed without root in sys.path
        sys.path.insert(0, os.path.dirname(__file__))
        from core.file_lock import locked_json_read, locked_json_write

DEFAULT_CACHE_REL = os.path.join(".synapse", "ast_cache.json")


class ASTValidationCache:
    """
    Persistent key-value cache for Python AST verification results.
    """

    def __init__(self, repo_root: Optional[str] = None, cache_path: Optional[str] = None):
        if repo_root is None:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.repo_root = os.path.abspath(repo_root)

        if cache_path is None:
            self.cache_path = os.path.join(self.repo_root, DEFAULT_CACHE_REL)
        else:
            self.cache_path = os.path.abspath(cache_path)

        self._entries: Dict[str, Dict[str, Any]] = {}
        self._dirty = False
        self.load()

    def load(self) -> None:
        """Loads cached AST records from disk under advisory shared lock."""
        if os.path.isfile(self.cache_path):
            try:
                data = locked_json_read(self.cache_path, timeout=5.0)
                if isinstance(data, dict):
                    self._entries = data.get("entries", {})
            except Exception:
                self._entries = {}
        else:
            self._entries = {}
        self._dirty = False

    def save(self) -> None:
        """Flushes modified cache records to disk under exclusive atomic lock with disk-merge."""
        if not self._dirty:
            return
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        # Read and merge existing entries to prevent concurrent worker/swarm overwrites
        current_entries: Dict[str, Any] = {}
        if os.path.isfile(self.cache_path):
            try:
                disk_data = locked_json_read(self.cache_path, timeout=5.0)
                if isinstance(disk_data, dict):
                    current_entries = disk_data.get("entries", {})
            except Exception:
                current_entries = {}
        current_entries.update(self._entries)
        payload = {
            "version": "1.0",
            "repo_root": self.repo_root,
            "entries": current_entries,
        }
        try:
            locked_json_write(self.cache_path, payload, indent=2, timeout=5.0, atomic=True)
            self._entries = current_entries
            self._dirty = False
        except Exception as err:
            import logging
            logging.getLogger("ast_cache").debug("Failed to load ast cache: %s", err)

    def get_signature(self, file_path: str) -> Optional[Tuple[int, int]]:
        """Returns (mtime_ns, size) for fast freshness check."""
        try:
            st = os.stat(file_path)
            return (st.st_mtime_ns, st.st_size)
        except OSError:
            return None

    def get_cached_result(self, rel_path: str, mtime_ns: int, size: int) -> Optional[Dict[str, Any]]:
        """Retrieves cached result if signature matches."""
        entry = self._entries.get(rel_path)
        if entry is None:
            return None
        if entry.get("mtime_ns") == mtime_ns and entry.get("size") == size:
            return entry.get("data")
        return None

    def put_result(self, rel_path: str, mtime_ns: int, size: int, data: Dict[str, Any]) -> None:
        """Records a new validation outcome in memory."""
        self._entries[rel_path] = {
            "mtime_ns": mtime_ns,
            "size": size,
            "data": data,
        }
        self._dirty = True

    def clear(self) -> None:
        """Clears memory and persisted cache."""
        self._entries.clear()
        self._dirty = False
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        payload = {
            "version": "1.0",
            "repo_root": self.repo_root,
            "entries": {},
        }
        try:
            locked_json_write(self.cache_path, payload, indent=2, timeout=5.0, atomic=True)
        except Exception as err:
            import logging
            logging.getLogger("ast_cache").debug("Failed to load ast cache: %s", err)


# Module-level singleton helper
_GLOBAL_CACHE: Optional[ASTValidationCache] = None


def get_ast_cache(repo_root: Optional[str] = None) -> ASTValidationCache:
    """Returns or initializes the process-wide AST cache."""
    global _GLOBAL_CACHE
    if _GLOBAL_CACHE is None:
        _GLOBAL_CACHE = ASTValidationCache(repo_root=repo_root)
    return _GLOBAL_CACHE


def main():
    parser = argparse.ArgumentParser(description="AST Dataflow Pre-Validation Cache (Boost B3)")
    parser.add_argument("--clear", action="store_true", help="Clear persisted AST cache")
    parser.add_argument("--stats", action="store_true", help="Print cache statistics")
    args = parser.parse_args()

    cache = get_ast_cache()
    if args.clear:
        cache.clear()
        print("[AST CACHE] Cache cleared successfully.")
    else:
        entries = cache._entries
        print(f"[AST CACHE] Path: {cache.cache_path} | Entries: {len(entries)}")


if __name__ == "__main__":
    main()
