#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Hierarchical QA Test Memory OS (Letta / MemGPT Pattern)
-------------------------------------------------------
Provides a 3-tier persistent memory operating system for test automation:
  1. Core Memory: Fast key-value blocks for active environment context (AUT URL, auth token expiry, flags).
  2. Recall Memory: Sequential event log of recent test execution steps and subagent actions.
  3. Archival Memory: Long-term searchable knowledge base of locator mutations and flaky patterns,
                      version-scoped by AUT release (e.g. v2.1 vs v2.2) to eliminate memory rot.
  4. Memory Hygiene: Garbage collection and secret scrubbing (zero plaintext tokens/passwords).

Usage:
  python tools/test_memory_os.py init --db-path .agent_memory/qa_memory.db
  python tools/test_memory_os.py update-core --block auth_state --data '{"token_expiry": "..."}'
  python tools/test_memory_os.py archival-insert --key LOCATOR_MUTATION --payload '{"page": "LoginPage", ...}' --aut-version "v2.1"
  python tools/test_memory_os.py archival-search --query "Login submit button" --aut-version "v2.1" --json
  python tools/test_memory_os.py gc --scrub-secrets --max-age-days 30
"""

import os
import sys
import re
import json
import sqlite3
import time
import difflib
import argparse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

# Enforce UTF-8 stdout encoding
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


SECRET_PATTERNS = [
    re.compile(r'["\']?(?:password|passwd|pwd|secret|apiKey|api_key|token|bearer)["\']?\s*[:=]\s*["\']?([^"\'\s,;]{8,})["\']?', re.IGNORECASE),
    re.compile(r'Bearer\s+([a-zA-Z0-9_\-\.]{15,})', re.IGNORECASE),
    re.compile(r'-----BEGIN (?:RSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA )?PRIVATE KEY-----'),
]


class TestMemoryOS:
    """3-Tier Hierarchical QA Memory OS."""
    __test__ = False

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = db_path
        else:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            self.db_path = os.path.join(repo_root, ".agent_memory", "qa_memory.db")

        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            # 1. Core Memory Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS core_memory (
                    block_key TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            # 2. Recall Memory Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recall_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_recall_session ON recall_memory(session_id, timestamp)")

            # 3. Archival Memory Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS archival_memory (
                    id TEXT PRIMARY KEY,
                    key TEXT NOT NULL,
                    aut_version TEXT DEFAULT 'latest',
                    payload_json TEXT NOT NULL,
                    tags TEXT DEFAULT '',
                    text_content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_archival_key_ver ON archival_memory(key, aut_version)")

    # ----------------- Tier 1: Core Memory -----------------

    def update_core(self, block_key: str, data: Any) -> Dict[str, Any]:
        """Updates or inserts a core memory block."""
        data_str = json.dumps(data) if not isinstance(data, str) else data
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO core_memory (block_key, data_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(block_key) DO UPDATE SET
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at
            """, (block_key, data_str, now))

        return {
            "status": "PASS",
            "block_key": block_key,
            "updated_at": now
        }

    def get_core(self, block_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves a core memory block."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT data_json, updated_at FROM core_memory WHERE block_key = ?", (block_key,)).fetchone()
            if row:
                try:
                    parsed = json.loads(row["data_json"])
                except Exception:
                    parsed = row["data_json"]
                return {
                    "block_key": block_key,
                    "data": parsed,
                    "updated_at": row["updated_at"]
                }
        return None

    def list_core(self) -> List[Dict[str, Any]]:
        """Lists all core memory blocks."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT block_key, data_json, updated_at FROM core_memory ORDER BY block_key").fetchall()
            results = []
            for r in rows:
                try:
                    parsed = json.loads(r["data_json"])
                except Exception:
                    parsed = r["data_json"]
                results.append({"block_key": r["block_key"], "data": parsed, "updated_at": r["updated_at"]})
            return results

    # ----------------- Tier 2: Recall Memory -----------------

    def recall_insert(self, session_id: str, event_type: str, actor: str, payload: Any) -> int:
        """Inserts an event into recall memory log."""
        payload_str = json.dumps(payload) if not isinstance(payload, str) else payload
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO recall_memory (session_id, event_type, actor, payload_json, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, event_type, actor, payload_str, now))
            return cursor.lastrowid

    def recall_log(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent sequential steps for a session."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT id, session_id, event_type, actor, payload_json, timestamp
                FROM recall_memory
                WHERE session_id = ?
                ORDER BY id ASC
                LIMIT ?
            """, (session_id, limit)).fetchall()
            events = []
            for r in rows:
                try:
                    payload = json.loads(r["payload_json"])
                except Exception:
                    payload = r["payload_json"]
                events.append({
                    "id": r["id"],
                    "session_id": r["session_id"],
                    "event_type": r["event_type"],
                    "actor": r["actor"],
                    "payload": payload,
                    "timestamp": r["timestamp"]
                })
            return events

    # ----------------- Tier 3: Archival Memory -----------------

    def archival_insert(self, key: str, payload: Any, aut_version: str = "latest", tags: str = "") -> str:
        """Inserts long-term searchable knowledge into archival memory."""
        payload_str = json.dumps(payload) if not isinstance(payload, str) else payload
        now = datetime.now(timezone.utc).isoformat()
        mem_id = f"mem_arch_{int(time.time() * 1000) % 10000000}"

        # Flatten text content for semantic/fuzzy search
        text_content = f"{key} {aut_version} {tags} {payload_str}".lower()

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO archival_memory (id, key, aut_version, payload_json, tags, text_content, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (mem_id, key, aut_version, payload_str, tags, text_content, now))

        return mem_id

    def archival_search(self, query: str, aut_version: Optional[str] = None, top_k: int = 3) -> Dict[str, Any]:
        """Searches archival memory with semantic token matching and fuzzy ratio."""
        query_lower = query.lower()
        tokens = set(re.findall(r'\b[a-z0-9_]{3,}\b', query_lower))

        with self._get_connection() as conn:
            if aut_version:
                rows = conn.execute(
                    "SELECT id, key, aut_version, payload_json, tags, text_content, created_at FROM archival_memory WHERE aut_version = ?",
                    (aut_version,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, key, aut_version, payload_json, tags, text_content, created_at FROM archival_memory"
                ).fetchall()

        scored = []
        for r in rows:
            text = r["text_content"]
            # 1. Token overlap score
            text_tokens = set(re.findall(r'\b[a-z0-9_]{3,}\b', text))
            if tokens:
                token_score = len(tokens.intersection(text_tokens)) / len(tokens)
            else:
                token_score = 0.0

            # 2. Fuzzy sequence similarity
            fuzzy_ratio = difflib.SequenceMatcher(None, query_lower, text[:200]).ratio()

            # Combined score: 60% token overlap + 40% fuzzy match
            score = round((0.6 * token_score) + (0.4 * fuzzy_ratio), 3)

            if score > 0.15 or (tokens and tokens.intersection(text_tokens)):
                try:
                    payload = json.loads(r["payload_json"])
                except Exception:
                    payload = r["payload_json"]

                scored.append({
                    "id": r["id"],
                    "similarity_score": score,
                    "key": r["key"],
                    "aut_version": r["aut_version"],
                    "timestamp": r["created_at"],
                    "payload": payload
                })

        scored.sort(key=lambda x: x["similarity_score"], reverse=True)
        results = scored[:top_k]

        return {
            "status": "PASS",
            "query": query,
            "aut_version": aut_version or "all",
            "matches_found": len(results),
            "results": results
        }

    # ----------------- Hygiene & Secret Scrubbing -----------------

    def scrub_string(self, text: str) -> Tuple[str, int]:
        """Masks detected secrets in text."""
        scrubbed = text
        count = 0
        for pat in SECRET_PATTERNS:
            matches = list(pat.finditer(scrubbed))
            if matches:
                count += len(matches)
                for m in matches:
                    val = m.group(0)
                    scrubbed = scrubbed.replace(val, "[MASKED_SECRET]")
        return scrubbed, count

    def gc(self, scrub_secrets: bool = True, max_age_days: int = 30) -> Dict[str, Any]:
        """Performs garbage collection and secret scrubbing."""
        scrub_count = 0
        deleted_recall = 0

        with self._get_connection() as conn:
            # 1. Clean old recall logs
            cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
            cur = conn.execute("DELETE FROM recall_memory WHERE timestamp < ?", (cutoff,))
            deleted_recall = cur.rowcount

            # 2. Scrub secrets in core memory
            if scrub_secrets:
                rows = conn.execute("SELECT block_key, data_json FROM core_memory").fetchall()
                for r in rows:
                    new_val, c = self.scrub_string(r["data_json"])
                    if c > 0:
                        scrub_count += c
                        conn.execute("UPDATE core_memory SET data_json = ? WHERE block_key = ?", (new_val, r["block_key"]))

                # Scrub archival memory
                a_rows = conn.execute("SELECT id, payload_json, text_content FROM archival_memory").fetchall()
                for ar in a_rows:
                    new_p, cp = self.scrub_string(ar["payload_json"])
                    new_t, ct = self.scrub_string(ar["text_content"])
                    if cp > 0 or ct > 0:
                        scrub_count += (cp + ct)
                        conn.execute("UPDATE archival_memory SET payload_json = ?, text_content = ? WHERE id = ?", (new_p, new_t, ar["id"]))

        # Database file size check
        db_size_mb = 0.0
        if os.path.exists(self.db_path):
            db_size_mb = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)

        return {
            "status": "PASS",
            "db_path": self.db_path,
            "db_size_mb": db_size_mb,
            "max_size_limit_mb": 50.0,
            "size_status": "PASS" if db_size_mb <= 50.0 else "WARNING_OVERSIZED",
            "secrets_scrubbed": scrub_count,
            "expired_recall_records_deleted": deleted_recall
        }


def main():
    parser = argparse.ArgumentParser(description="Hierarchical QA Test Memory OS (Letta Pattern)")
    parser.add_argument("--db-path", help="Path to SQLite database file")
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize memory OS database")

    # update-core
    uc_parser = subparsers.add_parser("update-core", help="Update core memory block")
    uc_parser.add_argument("--block", required=True, help="Core memory block key")
    uc_parser.add_argument("--data", required=True, help="JSON or text payload")

    # get-core
    gc_parser = subparsers.add_parser("get-core", help="Retrieve core memory block")
    gc_parser.add_argument("--block", required=True, help="Core memory block key")

    # archival-insert
    ai_parser = subparsers.add_parser("archival-insert", help="Insert long-term knowledge into Archival Memory")
    ai_parser.add_argument("--key", required=True, help="Knowledge key (e.g. LOCATOR_MUTATION)")
    ai_parser.add_argument("--payload", required=True, help="JSON data payload")
    ai_parser.add_argument("--aut-version", default="latest", help="AUT release version (e.g. v2.1)")
    ai_parser.add_argument("--tags", default="", help="Comma-separated search tags")

    # archival-search
    as_parser = subparsers.add_parser("archival-search", help="Search archival memory by query")
    as_parser.add_argument("--query", required=True, help="Search query string")
    as_parser.add_argument("--aut-version", help="Filter by AUT release version")
    as_parser.add_argument("--top-k", type=int, default=3, help="Max results to return")
    as_parser.add_argument("--json", action="store_true", help="Print JSON output")

    # gc
    clean_parser = subparsers.add_parser("gc", help="Garbage collection and secret scrubbing")
    clean_parser.add_argument("--scrub-secrets", action="store_true", default=True, help="Scrub sensitive credentials")
    clean_parser.add_argument("--max-age-days", type=int, default=30, help="Max age for recall logs")

    args = parser.parse_args()
    mem = TestMemoryOS(db_path=args.db_path)

    if args.subcommand == "init":
        print(json.dumps({"status": "PASS", "db_path": mem.db_path, "initialized": True}, indent=2))

    elif args.subcommand == "update-core":
        try:
            parsed_data = json.loads(args.data)
        except Exception:
            parsed_data = args.data
        res = mem.update_core(args.block, parsed_data)
        print(json.dumps(res, indent=2))

    elif args.subcommand == "get-core":
        res = mem.get_core(args.block)
        print(json.dumps(res or {"status": "NOT_FOUND", "block": args.block}, indent=2))

    elif args.subcommand == "archival-insert":
        try:
            parsed_payload = json.loads(args.payload)
        except Exception:
            parsed_payload = args.payload
        mid = mem.archival_insert(args.key, parsed_payload, aut_version=args.aut_version, tags=args.tags)
        print(json.dumps({"status": "PASS", "id": mid, "key": args.key, "aut_version": args.aut_version}, indent=2))

    elif args.subcommand == "archival-search":
        res = mem.archival_search(args.query, aut_version=args.aut_version, top_k=args.top_k)
        print(json.dumps(res, indent=2))

    elif args.subcommand == "gc":
        res = mem.gc(scrub_secrets=args.scrub_secrets, max_age_days=args.max_age_days)
        print(json.dumps(res, indent=2))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
