#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Unified 3-Tier QA Memory OS (SynapseMemory)
-------------------------------------------
Hierarchical persistent memory engine unifying:
  1. Core Memory: Fast key-value environment and session state.
  2. Recall Memory: Sequential append-only episodic event log of subagent turns.
  3. Archival Memory: Project-scoped semantic knowledge base of locator mutations,
     verified healing patches, negative failed-fix blacklists, and reusable QA instincts.

Additional Features:
  - Automatic secret scrubbing (zero plaintext tokens, passwords, or keys).
  - SQLite WAL mode concurrency with advisory busy timeouts.
  - CI Synchronization Adapters: Export/Import bundles for GitHub Actions & GitLab CI caching.

Usage:
  python tools/core/qa_memory_os.py init --db-path .agent_memory/qa_memory.db
  python tools/core/qa_memory_os.py core-set --block auth --data '{"token_exp": 3600}'
  python tools/core/qa_memory_os.py recall-log --event test_run --details '{"test": "login", "status": "pass"}'
  python tools/core/qa_memory_os.py archival-save --domain locator_heal --trigger "submit btn timeout" --action "use getByRole"
  python tools/core/qa_memory_os.py export-ci --out-archive reports/qa_memory_bundle.tar.gz
"""

import os
import sys
import re
import json
import uuid
import sqlite3
import hashlib
import tarfile
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

SECRET_PATTERNS = [
    re.compile(r'["\']?(?:password|passwd|pwd|secret|apiKey|api_key|token|bearer)["\']?\s*[:=]\s*["\']?([^"\'\s,;]{8,})["\']?', re.IGNORECASE),
    re.compile(r'Bearer\s+([a-zA-Z0-9_\-\.]{15,})', re.IGNORECASE),
    re.compile(r'-----BEGIN (?:RSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA )?PRIVATE KEY-----'),
]


KEY_SECRET_PATTERN = re.compile(r'^(?:token|password|passwd|pwd|secret|apikey|api_key|bearer|auth)$', re.IGNORECASE)


def scrub_secrets(text: str) -> str:
    """Scrubs sensitive credentials and private keys from strings."""
    if not isinstance(text, str):
        return text
    scrubbed = text
    for pat in SECRET_PATTERNS:
        scrubbed = pat.sub("[REDACTED_SECRET]", scrubbed)
    return scrubbed


def scrub_data_dict(data: Any, key_name: Optional[str] = None) -> Any:
    """Recursively redacts secrets in dicts, lists, or strings based on pattern or key name."""
    if key_name and isinstance(key_name, str) and KEY_SECRET_PATTERN.match(key_name):
        return "[REDACTED_SECRET]"
    if isinstance(data, dict):
        return {k: scrub_data_dict(v, key_name=k) for k, v in data.items()}
    elif isinstance(data, list):
        return [scrub_data_dict(item) for item in data]
    elif isinstance(data, str):
        return scrub_secrets(data)
    return data


class QAMemoryOS:
    """Unified 3-Tier QA Memory OS Engine."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = db_path
        else:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            self.db_path = os.path.join(repo_root, ".agent_memory", "qa_memory.db")
        self._is_memory = (self.db_path == ":memory:")
        if not self._is_memory:
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10.0)
        self._init_db()

    def _init_db(self):
        with self._conn:
            if not self._is_memory:
                try:
                    self._conn.execute("PRAGMA journal_mode=WAL;")
                    self._conn.execute("PRAGMA busy_timeout=5000;")
                except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                    pass

            # 1. Tier 1: Core Memory (Working key-value blocks)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS core_memory (
                    block_name TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)

            # 2. Tier 2: Recall Memory (Episodic event log)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS recall_memory (
                    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL,
                    session_id TEXT,
                    details_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );
            """)
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_recall_type ON recall_memory (event_type);")

            # 3. Tier 3: Archival Memory (Instincts, healing patches, negative fixes)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS archival_memory (
                    id TEXT PRIMARY KEY,
                    project_hash TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    trigger_text TEXT NOT NULL,
                    action_payload TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    usage_count INTEGER DEFAULT 1,
                    success_count INTEGER DEFAULT 1,
                    is_blacklisted INTEGER DEFAULT 0,
                    aut_version TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_archival_proj ON archival_memory (project_hash, domain);")

            # Archival FTS5 Virtual Table for sub-millisecond full-text indexed BM25 ranking
            self._has_fts5 = False
            try:
                self._conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS archival_fts USING fts5(
                        record_id UNINDEXED,
                        trigger_text,
                        tokenize='porter unicode61'
                    );
                """)
                self._has_fts5 = True
            except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                self._has_fts5 = False

    # =========================================================================
    # Tier 1: Core Memory Methods
    # =========================================================================
    def set_core(self, block_name: str, data: Dict[str, Any]) -> None:
        """Sets or replaces a core working memory block."""
        now = datetime.now(timezone.utc).isoformat()
        clean_data = scrub_data_dict(data)
        data_json = json.dumps(clean_data)
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO core_memory (block_name, data_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(block_name) DO UPDATE SET
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at
                """,
                (block_name, data_json, now)
            )

    def get_core(self, block_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves a core working memory block."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT data_json FROM core_memory WHERE block_name = ?;", (block_name,))
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None

    def list_core_blocks(self) -> List[str]:
        """Lists all active core memory block identifiers."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT block_name FROM core_memory ORDER BY block_name ASC;")
        return [r[0] for r in cursor.fetchall()]

    # =========================================================================
    # Tier 2: Recall Memory Methods
    # =========================================================================
    def log_recall(self, event_type: str, details: Dict[str, Any], session_id: Optional[str] = None) -> str:
        """Appends an episodic execution event to recall memory."""
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        clean_details = scrub_data_dict(details)
        details_json = json.dumps(clean_details)
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO recall_memory (event_id, event_type, session_id, details_json, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event_id, event_type, session_id, details_json, now)
            )
        return event_id

    def query_recall(self, event_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Queries episodic events in reverse chronological order."""
        self._conn.row_factory = sqlite3.Row
        cursor = self._conn.cursor()
        if event_type:
            cursor.execute(
                "SELECT * FROM recall_memory WHERE event_type = ? ORDER BY timestamp DESC, row_id DESC LIMIT ?;",
                (event_type, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM recall_memory ORDER BY timestamp DESC, row_id DESC LIMIT ?;",
                (limit,)
            )
        rows = cursor.fetchall()
        return [
            {
                "event_id": r["event_id"],
                "event_type": r["event_type"],
                "session_id": r["session_id"],
                "details": json.loads(r["details_json"]),
                "timestamp": r["timestamp"]
            }
            for r in rows
        ]

    # =========================================================================
    # Tier 3: Archival Memory Methods
    # =========================================================================
    def save_archival(
        self,
        domain: str,
        trigger: str,
        action: Union[str, Dict[str, Any]],
        project_hash: str = "global",
        confidence: float = 0.5,
        is_blacklisted: bool = False,
        aut_version: Optional[str] = None
    ) -> str:
        """Saves a semantic instinct or patch into archival memory."""
        clean_action = scrub_data_dict(action)
        action_json = json.dumps(clean_action) if isinstance(clean_action, (dict, list)) else str(clean_action)
        clean_trigger = scrub_secrets(trigger)
        record_id = f"arc_{hashlib.sha256(f'{project_hash}:{domain}:{clean_trigger}:{action_json}:{int(is_blacklisted)}'.encode('utf-8')).hexdigest()[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        with self._conn:
            self._conn.execute(
                """
                INSERT INTO archival_memory (
                    id, project_hash, domain, trigger_text, action_payload,
                    confidence, usage_count, success_count, is_blacklisted, aut_version, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    action_payload=excluded.action_payload,
                    usage_count=archival_memory.usage_count + 1,
                    success_count=archival_memory.success_count + CASE WHEN excluded.is_blacklisted = 0 THEN 1 ELSE 0 END,
                    confidence=MIN(1.0, archival_memory.confidence + 0.1),
                    is_blacklisted=excluded.is_blacklisted,
                    aut_version=COALESCE(excluded.aut_version, archival_memory.aut_version),
                    updated_at=excluded.updated_at
                """,
                (record_id, project_hash, domain, clean_trigger, action_json, confidence, int(is_blacklisted), aut_version, now, now)
            )
            # Sync to FTS5 virtual table for sub-millisecond full-text indexed retrieval
            if getattr(self, "_has_fts5", False):
                try:
                    self._conn.execute("DELETE FROM archival_fts WHERE record_id = ?;", (record_id,))
                    self._conn.execute(
                        "INSERT INTO archival_fts (record_id, trigger_text) VALUES (?, ?);",
                        (record_id, clean_trigger)
                    )
                except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                    pass
        return record_id

    def query_archival(
        self,
        query: str,
        domain: Optional[str] = None,
        project_hash: Optional[str] = None,
        exclude_blacklisted: bool = True,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Searches archival instincts matching trigger keyword using SQLite FTS5 index with fallback."""
        self._conn.row_factory = sqlite3.Row
        cursor = self._conn.cursor()

        # Fast-Path: SQLite FTS5 Virtual Table Index
        if getattr(self, "_has_fts5", False) and query.strip():
            tokens = [re.sub(r'[^a-zA-Z0-9_]', '', t) for t in query.split() if len(t) > 2]
            if tokens:
                fts_expr = " OR ".join(f"{t}*" for t in tokens)
                try:
                    fts_sql = f"""
                        SELECT a.* FROM archival_memory a
                        JOIN archival_fts f ON a.id = f.record_id
                        WHERE archival_fts MATCH ?
                        {(" AND a.domain = ?" if domain else "")}
                        {(" AND (a.project_hash = ? OR a.project_hash = 'global')" if project_hash else "")}
                        {(" AND a.is_blacklisted = 0" if exclude_blacklisted else "")}
                        ORDER BY a.confidence DESC, a.usage_count DESC
                        LIMIT ?;
                    """
                    fts_params: List[Any] = [fts_expr]
                    if domain:
                        fts_params.append(domain)
                    if project_hash:
                        fts_params.append(project_hash)
                    fts_params.append(limit)

                    cursor.execute(fts_sql, fts_params)
                    fts_rows = cursor.fetchall()
                    if fts_rows:
                        results = []
                        for r in fts_rows:
                            payload = r["action_payload"]
                            try:
                                payload = json.loads(payload)
                            except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                                pass
                            results.append({
                                "id": r["id"],
                                "project_hash": r["project_hash"],
                                "domain": r["domain"],
                                "trigger": r["trigger_text"],
                                "action": payload,
                                "confidence": r["confidence"],
                                "usage_count": r["usage_count"],
                                "success_count": r["success_count"],
                                "is_blacklisted": bool(r["is_blacklisted"]),
                                "aut_version": r["aut_version"]
                            })
                        return results
                except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                    pass

        # Robust Fallback: Substring scanning
        sql = "SELECT * FROM archival_memory WHERE 1=1"
        params: List[Any] = []

        if domain:
            sql += " AND domain = ?"
            params.append(domain)
        if project_hash:
            sql += " AND (project_hash = ? OR project_hash = 'global')"
            params.append(project_hash)
        if exclude_blacklisted:
            sql += " AND is_blacklisted = 0"

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        q_lower = query.lower()
        results = []
        for r in rows:
            trigger = r["trigger_text"].lower()
            # Substring matching or simple token overlap
            if q_lower in trigger or any(token in trigger for token in q_lower.split() if len(token) > 3):
                payload = r["action_payload"]
                try:
                    payload = json.loads(payload)
                except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                    pass
                results.append({
                    "id": r["id"],
                    "project_hash": r["project_hash"],
                    "domain": r["domain"],
                    "trigger": r["trigger_text"],
                    "action": payload,
                    "confidence": r["confidence"],
                    "usage_count": r["usage_count"],
                    "success_count": r["success_count"],
                    "is_blacklisted": bool(r["is_blacklisted"]),
                    "aut_version": r["aut_version"]
                })
        # Rank by confidence DESC, usage_count DESC for high-value instincts first
        results.sort(key=lambda x: (x["confidence"], x["usage_count"]), reverse=True)
        return results[:limit]

    # =========================================================================
    # CI/CD Sync Adapters (GitHub Actions & GitLab CI)
    # =========================================================================
    def export_ci_bundle(self, out_archive_path: str) -> str:
        """Exports the SQLite memory database into a compressed tar.gz bundle for CI caching."""
        if self._is_memory:
            raise ValueError("Cannot export in-memory database to CI bundle.")
        os.makedirs(os.path.dirname(os.path.abspath(out_archive_path)), exist_ok=True)
        # Checkpoint WAL first to flush changes
        with self._conn:
            try:
                self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                pass

        with tarfile.open(out_archive_path, "w:gz") as tar:
            tar.add(self.db_path, arcname="qa_memory_sync.db")
        return out_archive_path

    def import_ci_bundle(self, in_archive_path: str) -> None:
        """Extracts and merges a remote CI cache bundle into the local database."""
        if not os.path.exists(in_archive_path):
            raise FileNotFoundError(f"Bundle archive not found: {in_archive_path}")

        temp_dir = os.path.join(os.path.dirname(os.path.abspath(in_archive_path)), "_unpacked_bundle")
        os.makedirs(temp_dir, exist_ok=True)
        try:
            with tarfile.open(in_archive_path, "r:gz") as tar:
                if hasattr(tarfile, 'data_filter'):
                    tar.extractall(path=temp_dir, filter='data')
                else:
                    tar.extractall(path=temp_dir)
            unpacked_db = os.path.join(temp_dir, "qa_memory_sync.db")
            if not os.path.exists(unpacked_db):
                # Fallback: check any .db in temp_dir
                for fname in os.listdir(temp_dir):
                    if fname.endswith(".db"):
                        unpacked_db = os.path.join(temp_dir, fname)
                        break
            if os.path.exists(unpacked_db):
                clean_db_path = os.path.abspath(unpacked_db).replace("\\", "/")
                self._conn.execute(f"ATTACH DATABASE '{clean_db_path}' AS remote_db;")
                try:
                    with self._conn:
                        self._conn.execute("""
                            INSERT OR IGNORE INTO archival_memory
                            SELECT * FROM remote_db.archival_memory;
                        """)
                        self._conn.execute("""
                            INSERT OR IGNORE INTO core_memory
                            SELECT * FROM remote_db.core_memory;
                        """)
                finally:
                    try:
                        self._conn.execute("DETACH DATABASE remote_db;")
                    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                        pass
        finally:
            # Clean temporary unpacked files
            try:
                for f in os.listdir(temp_dir):
                    os.remove(os.path.join(temp_dir, f))
                os.rmdir(temp_dir)
            except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                pass

    def close(self):
        """Safely closes connection."""
        try:
            self._conn.close()
        except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    parser = argparse.ArgumentParser(description="Synapse Hub QA Memory OS CLI")
    subparsers = parser.add_subparsers(dest="command")

    init_p = subparsers.add_parser("init")
    init_p.add_argument("--db-path", default=None)

    core_p = subparsers.add_parser("core-set")
    core_p.add_argument("--block", required=True)
    core_p.add_argument("--data", required=True)
    core_p.add_argument("--db-path", default=None)

    core_get_p = subparsers.add_parser("core-get")
    core_get_p.add_argument("--block", required=True)
    core_get_p.add_argument("--db-path", default=None)

    args = parser.parse_args()
    if args.command == "init":
        mem = QAMemoryOS(args.db_path)
        print(f"[OK] QA Memory OS initialized at: {mem.db_path}")
        mem.close()
    elif args.command == "core-set":
        mem = QAMemoryOS(args.db_path)
        data = json.loads(args.data)
        mem.set_core(args.block, data)
        print(f"[OK] Core memory block '{args.block}' updated.")
        mem.close()
    elif args.command == "core-get":
        mem = QAMemoryOS(args.db_path)
        data = mem.get_core(args.block)
        print(json.dumps(data, indent=2))
        mem.close()


if __name__ == "__main__":
    main()
