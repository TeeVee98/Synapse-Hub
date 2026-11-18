---
name: content-hash-cache-pattern
description: >
  SHA-256 AST content-hash caching skill: avoid redundant reprocessing of unchanged
  files by keying results against the content hash of their inputs. Use for any
  expensive static analysis, compilation, or AI inference pipeline where inputs
  are deterministic.
version: 1.0.0
attribution: Adapted from ECC (affaan-m/ecc, Apache 2.0). Extended by Thế Vị (@TeeVee98).
---

# Content-Hash Cache Pattern Skill (`content-hash-cache-pattern`)

## Overview

The content-hash cache pattern replaces timestamp-based file invalidation with **deterministic SHA-256 input hashing**. Only files whose content has changed since last run are reprocessed; unchanged files return cached results instantly.

> [!TIP]
> This pattern typically achieves 70-90% cache hit rates in incremental CI runs,
> reducing tool execution time from minutes to seconds.

## When to Activate

- Running `tools/core/verify_all.py` on a large monorepo (Gate 7 / Gate 9 static analysis).
- Re-running SkillSpector on a skills catalog where most skills are unchanged.
- Any pipeline where input files are content-addressable and results are deterministic.

## Hash Cache Architecture

```
Input File(s)
     ↓
SHA-256(content) → cache_key
     ↓
Cache Lookup (SQLite WAL or JSON file)
     ↓ HIT → return cached result (< 1ms)
     ↓ MISS → run tool → store result under cache_key
```

## Implementation Template

```python
# tools/core/hash_cache.py
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98)
# SPDX-License-Identifier: MIT
"""SHA-256 content-hash result cache (stdlib-only, SQLite WAL)."""

from __future__ import annotations
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Optional


class ContentHashCache:
    """Persistent cache keyed by SHA-256 hash of file content."""

    def __init__(self, db_path: str = ".synapse/cache/content_hash.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS cache "
            "(key TEXT PRIMARY KEY, result TEXT, created_at TEXT)"
        )
        self._conn.commit()

    @staticmethod
    def hash_file(file_path: str) -> str:
        """Compute SHA-256 hex digest of file content."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def get(self, cache_key: str) -> Optional[Any]:
        row = self._conn.execute(
            "SELECT result FROM cache WHERE key = ?", (cache_key,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, cache_key: str, result: Any) -> None:
        import datetime
        self._conn.execute(
            "INSERT OR REPLACE INTO cache (key, result, created_at) VALUES (?, ?, ?)",
            (cache_key, json.dumps(result), datetime.datetime.utcnow().isoformat()),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "ContentHashCache":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
```

## Usage Pattern

```python
from tools.core.hash_cache import ContentHashCache
from tools.core.skillspector import scan_target

with ContentHashCache() as cache:
    for skill_file in skill_files:
        key = ContentHashCache.hash_file(skill_file)
        cached = cache.get(key)
        if cached is not None:
            report = cached  # Cache hit — skip scan
        else:
            report = scan_target(skill_file)
            cache.put(key, report)   # Cache miss — run and store
```

## Cache Invalidation Rules

1. **Never use mtime as cache key** — timestamps are unreliable across CI agents.
2. **Tool version bump invalidates all entries** — append tool version to key: `f"{sha256}:{tool_version}"`.
3. **TTL**: entries older than 30 days are pruned on startup.
4. **Shared cache** in multi-agent worktree setups: use SQLite WAL for concurrent reads.

## Non-Goals

- Do not cache results for non-deterministic outputs (network calls, timestamps).
- Do not use as a secrets cache — cache stores are not encrypted at rest.
