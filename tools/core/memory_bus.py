# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tools/core/memory_bus.py — Unified QA Memory Bus Architecture
--------------------------------------------------------------
Provides a centralized, SQLite WAL-mode persistent memory bus (.synapse/memory.db)
unifying 5 critical QA operating partitions:
  1. blocks: Core environment, authentication, and session memory blocks.
  2. actor_mailbox: Asynchronous actor-to-actor message queues for swarm agents.
  3. skill_vault: Persistent store of verified Page Classes and interaction skills.
  4. healing_cache: Closed-loop error signatures, root causes, and verified code patches.
  5. event_stream: Deterministic, immutable hash-chained execution timeline with checkpoints.

Features:
  - SQLite WAL (Write-Ahead Logging) mode for concurrent read/write throughput.
  - Full ACID transaction support with atomic commits and automatic rollback on test abort.
  - Named savepoints for nested transaction isolation.
  - Automatic cryptographic SHA-256 event chaining for stream tamper evidence.
"""

import os
import sys
import time
import random
import json
import uuid
import sqlite3
import hashlib
import threading
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Dict, Any, List, Optional, Tuple, Generator

GENESIS_HASH = "0" * 64


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_loads(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return text


class UnifiedMemoryBus:
    """
    Centralized persistent memory bus coordinating multi-agent state across
    blocks, actor_mailbox, skill_vault, healing_cache, and event_stream.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            synapse_dir = os.path.join(repo_root, ".synapse")
            os.makedirs(synapse_dir, exist_ok=True)
            self.db_path = os.path.join(synapse_dir, "memory.db")
        else:
            if db_path != ":memory:":
                parent = os.path.dirname(os.path.abspath(db_path))
                if parent:
                    os.makedirs(parent, exist_ok=True)
            self.db_path = db_path

        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=10.0,
            isolation_level=None  # Explicit autocommit mode, transactions handled manually
        )
        self._conn.row_factory = sqlite3.Row
        self._in_transaction = False
        self._savepoint_depth = 0
        self._init_pragmas_and_schema()

    def _init_pragmas_and_schema(self):
        with self._lock:
            cur = self._conn.cursor()
            if self.db_path != ":memory:":
                cur.execute("PRAGMA journal_mode = WAL;")
            cur.execute("PRAGMA synchronous = NORMAL;")
            cur.execute("PRAGMA foreign_keys = ON;")
            cur.execute("PRAGMA busy_timeout = 5000;")

            # 1. Blocks Partition
            cur.execute("""
                CREATE TABLE IF NOT EXISTS memory_blocks (
                    block_id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL DEFAULT 'global',
                    label TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(scope, label)
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_blocks_scope ON memory_blocks(scope);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_blocks_label ON memory_blocks(label);")

            # 2. Actor Mailbox Partition
            cur.execute("""
                CREATE TABLE IF NOT EXISTS actor_mailbox (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    sender TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    created_at TEXT NOT NULL,
                    read_at TEXT
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_mailbox_recipient ON actor_mailbox(recipient, status);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_mailbox_stage ON actor_mailbox(stage);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_mailbox_session ON actor_mailbox(session_id);")
            try:
                cur.execute("ALTER TABLE actor_mailbox ADD COLUMN session_id TEXT;")
            except sqlite3.OperationalError as _err:
                _ = _err

            # 3. Skill Vault Partition
            cur.execute("""
                CREATE TABLE IF NOT EXISTS skill_vault (
                    skill_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    framework TEXT NOT NULL,
                    content TEXT NOT NULL,
                    signature TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}',
                    verified INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(name, framework)
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_skill_name ON skill_vault(name);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_skill_framework ON skill_vault(framework);")

            # 4. Healing Cache Partition
            cur.execute("""
                CREATE TABLE IF NOT EXISTS healing_cache (
                    cache_id TEXT PRIMARY KEY,
                    error_signature TEXT NOT NULL UNIQUE,
                    failed_code TEXT NOT NULL,
                    patch_code TEXT NOT NULL,
                    rca_verdict TEXT DEFAULT '',
                    verified INTEGER NOT NULL DEFAULT 0,
                    hit_count INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_healing_sig ON healing_cache(error_signature);")

            # 5. Event Stream Partition
            cur.execute("""
                CREATE TABLE IF NOT EXISTS event_stream (
                    event_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    checkpoint_name TEXT,
                    timestamp TEXT NOT NULL,
                    UNIQUE(session_id, sequence)
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_event_session ON event_stream(session_id, sequence);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_event_checkpoint ON event_stream(session_id, checkpoint_name);")
            cur.close()

    # ---------------------------------------------------------------------------
    # Transaction Management & Abort Rollback
    # ---------------------------------------------------------------------------

    def begin(self):
        """Begins an explicit database transaction."""
        with self._lock:
            if not self._in_transaction:
                self._conn.execute("BEGIN IMMEDIATE;")
                self._in_transaction = True

    def commit(self):
        """Commits active database transaction."""
        with self._lock:
            if self._in_transaction:
                self._conn.execute("COMMIT;")
                self._in_transaction = False

    def rollback(self):
        """Rolls back active database transaction."""
        with self._lock:
            if self._in_transaction:
                self._conn.execute("ROLLBACK;")
                self._in_transaction = False

    @contextmanager
    def transaction(self) -> Generator["UnifiedMemoryBus", None, None]:
        """
        Transactional context manager. Automatically commits on successful exit
        or rolls back on exception.
        """
        with self._lock:
            if not self._in_transaction:
                self.begin()
                try:
                    yield self
                    self.commit()
                except Exception:
                    self.rollback()
                    raise
            else:
                # Nested transaction implemented via savepoint
                sp_name = f"sp_{uuid.uuid4().hex[:8]}"
                self._conn.execute(f"SAVEPOINT {sp_name};")
                try:
                    yield self
                    self._conn.execute(f"RELEASE SAVEPOINT {sp_name};")
                except Exception:
                    self._conn.execute(f"ROLLBACK TO SAVEPOINT {sp_name};")
                    raise

    @contextmanager
    def savepoint(self, name: Optional[str] = None) -> Generator[str, None, None]:
        """Named savepoint context manager for partial rollback boundaries."""
        with self._lock:
            sp_name = name or f"sp_{uuid.uuid4().hex[:8]}"
            self._conn.execute(f"SAVEPOINT {sp_name};")
            try:
                yield sp_name
                self._conn.execute(f"RELEASE SAVEPOINT {sp_name};")
            except Exception:
                self._conn.execute(f"ROLLBACK TO SAVEPOINT {sp_name};")
                raise

    def abort_test(self, session_id: Optional[str] = None, reason: str = "Test aborted"):
        """
        Synchronous test abort handler. Rolls back active uncommitted transactions,
        cancels pending mailbox messages, and records an abort event if session_id is provided.
        """
        with self._lock:
            if self._in_transaction:
                self.rollback()

            if session_id:
                # Mark pending messages for this session's agents as ABORTED
                self._conn.execute(
                    "UPDATE actor_mailbox SET status = 'ABORTED' WHERE status = 'PENDING' AND (session_id = ? OR session_id IS NULL OR session_id = '');",
                    (session_id,)
                )
                self.record_event(
                    session_id=session_id,
                    event_type="TEST_ABORTED",
                    actor="system",
                    stage="ABORT_HANDLER",
                    payload={"reason": reason, "aborted_at": _now_iso()}
                )
            else:
                self._conn.execute(
                    "UPDATE actor_mailbox SET status = 'ABORTED' WHERE status = 'PENDING';"
                )

    # ---------------------------------------------------------------------------
    # Partition 1: Memory Blocks API
    # ---------------------------------------------------------------------------

    def set_block(self, label: str, content: Any, scope: str = "global", tags: str = "") -> Dict[str, Any]:
        """Creates or updates a memory block under a specific scope."""
        with self._lock:
            now = _now_iso()
            content_str = _json_dumps(content) if not isinstance(content, str) else content
            block_id = f"blk_{uuid.uuid4().hex[:12]}"
            cur = self._conn.cursor()
            cur.execute("""
                INSERT INTO memory_blocks (block_id, scope, label, content, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(scope, label) DO UPDATE SET
                    content = excluded.content,
                    tags = excluded.tags,
                    updated_at = excluded.updated_at;
            """, (block_id, scope, label, content_str, tags, now, now))
            cur.close()
            return {
                "scope": scope,
                "label": label,
                "content": content,
                "tags": tags,
                "updated_at": now
            }

    def get_block(self, label: str, scope: str = "global") -> Optional[Dict[str, Any]]:
        """Retrieves a memory block by label and scope."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT * FROM memory_blocks WHERE scope = ? AND label = ? LIMIT 1;",
                (scope, label)
            )
            row = cur.fetchone()
            cur.close()
            if not row:
                return None
            return {
                "block_id": row["block_id"],
                "scope": row["scope"],
                "label": row["label"],
                "content": _json_loads(row["content"]),
                "tags": row["tags"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }

    def delete_block(self, label: str, scope: str = "global") -> bool:
        """Deletes a memory block by label and scope."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("DELETE FROM memory_blocks WHERE scope = ? AND label = ?;", (scope, label))
            deleted = cur.rowcount > 0
            cur.close()
            return deleted

    def list_blocks(self, scope: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists all memory blocks, optionally filtered by scope."""
        with self._lock:
            cur = self._conn.cursor()
            if scope:
                cur.execute("SELECT * FROM memory_blocks WHERE scope = ? ORDER BY label ASC;", (scope,))
            else:
                cur.execute("SELECT * FROM memory_blocks ORDER BY scope ASC, label ASC;")
            rows = cur.fetchall()
            cur.close()
            return [
                {
                    "block_id": r["block_id"],
                    "scope": r["scope"],
                    "label": r["label"],
                    "content": _json_loads(r["content"]),
                    "tags": r["tags"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"]
                }
                for r in rows
            ]

    # ---------------------------------------------------------------------------
    # Partition 2: Actor Mailbox API
    # ---------------------------------------------------------------------------

    def send_message(
        self,
        sender: str,
        recipient: str,
        stage: str,
        payload: Any,
        session_id: Optional[str] = None
    ) -> str:
        """Queues an asynchronous message from sender to recipient actor."""
        with self._lock:
            msg_id = f"msg_{uuid.uuid4().hex[:12]}"
            now = _now_iso()
            payload_str = _json_dumps(payload) if not isinstance(payload, str) else payload
            cur = self._conn.cursor()
            cur.execute("""
                INSERT INTO actor_mailbox (message_id, session_id, sender, recipient, stage, payload, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?);
            """, (msg_id, session_id, sender, recipient, stage, payload_str, now))
            cur.close()
            return msg_id

    def receive_messages(
        self,
        recipient: str,
        stage: Optional[str] = None,
        status: str = "PENDING",
        mark_read: bool = True,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves and optionally marks messages as PROCESSED for recipient."""
        with self._lock:
            cur = self._conn.cursor()
            query = "SELECT * FROM actor_mailbox WHERE recipient = ? AND status = ?"
            params: List[Any] = [recipient, status]
            if stage:
                query += " AND stage = ?"
                params.append(stage)
            if session_id:
                query += " AND (session_id = ? OR session_id IS NULL)"
                params.append(session_id)
            query += " ORDER BY created_at ASC;"

            cur.execute(query, params)
            rows = cur.fetchall()

            messages = []
            msg_ids = []
            for r in rows:
                msg_ids.append(r["message_id"])
                messages.append({
                    "message_id": r["message_id"],
                    "session_id": r["session_id"] if "session_id" in r.keys() else None,
                    "sender": r["sender"],
                    "recipient": r["recipient"],
                    "stage": r["stage"],
                    "payload": _json_loads(r["payload"]),
                    "status": r["status"],
                    "created_at": r["created_at"],
                    "read_at": r["read_at"]
                })

            if mark_read and msg_ids:
                now = _now_iso()
                placeholders = ",".join("?" for _ in msg_ids)
                cur.execute(
                    f"UPDATE actor_mailbox SET status = 'PROCESSED', read_at = ? WHERE message_id IN ({placeholders});",
                    [now] + msg_ids
                )
            cur.close()
            return messages

    def peek_messages(
        self,
        recipient: str,
        stage: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Inspects pending messages without changing status."""
        return self.receive_messages(
            recipient=recipient, stage=stage, status="PENDING", mark_read=False, session_id=session_id
        )

    def mark_message_status(self, message_id: str, status: str) -> bool:
        """Updates the status of an actor mailbox message."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "UPDATE actor_mailbox SET status = ?, read_at = ? WHERE message_id = ?;",
                (status, _now_iso(), message_id)
            )
            updated = cur.rowcount > 0
            cur.close()
            return updated

    # ---------------------------------------------------------------------------
    # Partition 3: Skill Vault API
    # ---------------------------------------------------------------------------

    def store_skill(
        self,
        name: str,
        framework: str,
        content: str,
        signature: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        verified: bool = True
    ) -> str:
        """Persists or updates an interaction skill or Page Class snippet."""
        with self._lock:
            skill_id = f"sk_{uuid.uuid4().hex[:12]}"
            now = _now_iso()
            meta_str = _json_dumps(metadata or {})
            ver_int = 1 if verified else 0
            cur = self._conn.cursor()
            cur.execute("""
                INSERT INTO skill_vault (skill_id, name, framework, content, signature, metadata, verified, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name, framework) DO UPDATE SET
                    content = excluded.content,
                    signature = excluded.signature,
                    metadata = excluded.metadata,
                    verified = excluded.verified,
                    updated_at = excluded.updated_at;
            """, (skill_id, name, framework, content, signature, meta_str, ver_int, now, now))
            cur.close()
            return skill_id

    def get_skill(self, name: str, framework: str) -> Optional[Dict[str, Any]]:
        """Retrieves a skill by name and framework."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT * FROM skill_vault WHERE name = ? AND framework = ? LIMIT 1;",
                (name, framework)
            )
            row = cur.fetchone()
            cur.close()
            if not row:
                return None
            return {
                "skill_id": row["skill_id"],
                "name": row["name"],
                "framework": row["framework"],
                "content": row["content"],
                "signature": row["signature"],
                "metadata": _json_loads(row["metadata"]),
                "verified": bool(row["verified"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }

    def find_skills(
        self,
        query: str = "",
        framework: Optional[str] = None,
        verified_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Searches skills by substring in name/signature, optionally filtered."""
        with self._lock:
            cur = self._conn.cursor()
            sql = "SELECT * FROM skill_vault WHERE 1=1"
            params: List[Any] = []
            if verified_only:
                sql += " AND verified = 1"
            if framework:
                sql += " AND framework = ?"
                params.append(framework)
            if query:
                sql += " AND (name LIKE ? OR signature LIKE ? OR content LIKE ?)"
                pattern = f"%{query}%"
                params.extend([pattern, pattern, pattern])
            sql += " ORDER BY name ASC;"

            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()
            return [
                {
                    "skill_id": r["skill_id"],
                    "name": r["name"],
                    "framework": r["framework"],
                    "content": r["content"],
                    "signature": r["signature"],
                    "metadata": _json_loads(r["metadata"]),
                    "verified": bool(r["verified"]),
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"]
                }
                for r in rows
            ]

    def delete_skill(self, skill_id: str) -> bool:
        """Deletes a skill by its skill_id."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("DELETE FROM skill_vault WHERE skill_id = ?;", (skill_id,))
            deleted = cur.rowcount > 0
            cur.close()
            return deleted

    # ---------------------------------------------------------------------------
    # Partition 4: Healing Cache API
    # ---------------------------------------------------------------------------

    def record_healing(
        self,
        error_signature: str,
        failed_code: str,
        patch_code: str,
        rca_verdict: str = "",
        verified: bool = False
    ) -> str:
        """Records a healing patch or increments hit count if signature exists."""
        with self._lock:
            now = _now_iso()
            cache_id = f"heal_{uuid.uuid4().hex[:12]}"
            ver_int = 1 if verified else 0
            cur = self._conn.cursor()
            cur.execute("""
                INSERT INTO healing_cache (cache_id, error_signature, failed_code, patch_code, rca_verdict, verified, hit_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(error_signature) DO UPDATE SET
                    failed_code = excluded.failed_code,
                    patch_code = excluded.patch_code,
                    rca_verdict = excluded.rca_verdict,
                    verified = MAX(healing_cache.verified, excluded.verified),
                    hit_count = healing_cache.hit_count + 1,
                    updated_at = excluded.updated_at;
            """, (cache_id, error_signature, failed_code, patch_code, rca_verdict, ver_int, now, now))
            cur.close()
            return cache_id

    def lookup_healing(self, error_signature: str, verified_only: bool = False) -> Optional[Dict[str, Any]]:
        """Looks up a cached healing patch by error signature."""
        with self._lock:
            cur = self._conn.cursor()
            sql = "SELECT * FROM healing_cache WHERE error_signature = ?"
            params: List[Any] = [error_signature]
            if verified_only:
                sql += " AND verified = 1"
            sql += " LIMIT 1;"

            cur.execute(sql, params)
            row = cur.fetchone()
            cur.close()
            if not row:
                return None
            return {
                "cache_id": row["cache_id"],
                "error_signature": row["error_signature"],
                "failed_code": row["failed_code"],
                "patch_code": row["patch_code"],
                "rca_verdict": row["rca_verdict"],
                "verified": bool(row["verified"]),
                "hit_count": row["hit_count"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }

    def verify_healing(self, cache_id: str, verified: bool = True) -> bool:
        """Marks a healing record as verified or unverified."""
        with self._lock:
            cur = self._conn.cursor()
            ver_int = 1 if verified else 0
            cur.execute(
                "UPDATE healing_cache SET verified = ?, updated_at = ? WHERE cache_id = ?;",
                (ver_int, _now_iso(), cache_id)
            )
            updated = cur.rowcount > 0
            cur.close()
            return updated

    # ---------------------------------------------------------------------------
    # Partition 5: Event Stream API (Hash-Chained & Checkpoint Rollbacks)
    # ---------------------------------------------------------------------------

    def record_event(
        self,
        session_id: str,
        event_type: str,
        actor: str,
        stage: str,
        payload: Any,
        checkpoint_name: Optional[str] = None,
        max_retries: int = 15
    ) -> Dict[str, Any]:
        """
        Appends a new event to the session's hash-chained timeline.
        Features concurrency retry with BEGIN IMMEDIATE to serialize multi-process writes.
        """
        with self._lock:
            payload_str = _json_dumps(payload) if not isinstance(payload, str) else payload

            # If already inside an explicit caller transaction, execute directly within that transaction
            if self._in_transaction:
                cur = self._conn.cursor()
                cur.execute(
                    "SELECT sequence, event_hash FROM event_stream WHERE session_id = ? ORDER BY sequence DESC LIMIT 1;",
                    (session_id,)
                )
                last_row = cur.fetchone()
                seq = (last_row["sequence"] + 1) if last_row else 1
                prev_hash = last_row["event_hash"] if last_row else GENESIS_HASH

                event_id = f"evt_{uuid.uuid4().hex[:12]}"
                now = _now_iso()
                hash_input = f"{session_id}:{seq}:{event_type}:{actor}:{stage}:{payload_str}:{prev_hash}:{now}"
                event_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

                cur.execute("""
                    INSERT INTO event_stream (
                        event_id, session_id, sequence, event_type, actor, stage, payload,
                        prev_hash, event_hash, checkpoint_name, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (event_id, session_id, seq, event_type, actor, stage, payload_str, prev_hash, event_hash, checkpoint_name, now))
                cur.close()

                return {
                    "event_id": event_id,
                    "session_id": session_id,
                    "sequence": seq,
                    "event_type": event_type,
                    "actor": actor,
                    "stage": stage,
                    "payload": payload,
                    "prev_hash": prev_hash,
                    "event_hash": event_hash,
                    "checkpoint_name": checkpoint_name,
                    "timestamp": now
                }

            # Otherwise, use isolated immediate transaction with retry loop for concurrent safety
            for attempt in range(max_retries):
                try:
                    self._conn.execute("BEGIN IMMEDIATE;")
                    cur = self._conn.cursor()
                    cur.execute(
                        "SELECT sequence, event_hash FROM event_stream WHERE session_id = ? ORDER BY sequence DESC LIMIT 1;",
                        (session_id,)
                    )
                    last_row = cur.fetchone()
                    seq = (last_row["sequence"] + 1) if last_row else 1
                    prev_hash = last_row["event_hash"] if last_row else GENESIS_HASH

                    event_id = f"evt_{uuid.uuid4().hex[:12]}"
                    now = _now_iso()
                    hash_input = f"{session_id}:{seq}:{event_type}:{actor}:{stage}:{payload_str}:{prev_hash}:{now}"
                    event_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

                    cur.execute("""
                        INSERT INTO event_stream (
                            event_id, session_id, sequence, event_type, actor, stage, payload,
                            prev_hash, event_hash, checkpoint_name, timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """, (event_id, session_id, seq, event_type, actor, stage, payload_str, prev_hash, event_hash, checkpoint_name, now))
                    self._conn.execute("COMMIT;")
                    cur.close()

                    return {
                        "event_id": event_id,
                        "session_id": session_id,
                        "sequence": seq,
                        "event_type": event_type,
                        "actor": actor,
                        "stage": stage,
                        "payload": payload,
                        "prev_hash": prev_hash,
                        "event_hash": event_hash,
                        "checkpoint_name": checkpoint_name,
                        "timestamp": now
                    }
                except (sqlite3.IntegrityError, sqlite3.OperationalError):
                    try:
                        self._conn.execute("ROLLBACK;")
                    except Exception as _rb_err:
                        _ = _rb_err
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(random.uniform(0.005, 0.02 * (attempt + 1)))

    def get_events(self, session_id: str, since_sequence: int = 0) -> List[Dict[str, Any]]:
        """Retrieves timeline events for a session."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT * FROM event_stream WHERE session_id = ? AND sequence >= ? ORDER BY sequence ASC;",
                (session_id, since_sequence)
            )
            rows = cur.fetchall()
            cur.close()
            return [
                {
                    "event_id": r["event_id"],
                    "session_id": r["session_id"],
                    "sequence": r["sequence"],
                    "event_type": r["event_type"],
                    "actor": r["actor"],
                    "stage": r["stage"],
                    "payload": _json_loads(r["payload"]),
                    "prev_hash": r["prev_hash"],
                    "event_hash": r["event_hash"],
                    "checkpoint_name": r["checkpoint_name"],
                    "timestamp": r["timestamp"]
                }
                for r in rows
            ]

    def verify_stream_integrity(self, session_id: str) -> Tuple[bool, Optional[str]]:
        """
        Cryptographically verifies SHA-256 hash chaining across session event stream.
        Directly checks raw payload as persisted in DB to prevent serialization drift.
        Returns (is_valid, error_description).
        """
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT sequence, event_type, actor, stage, payload, prev_hash, event_hash, timestamp "
                "FROM event_stream WHERE session_id = ? ORDER BY sequence ASC;",
                (session_id,)
            )
            rows = cur.fetchall()
            cur.close()

            if not rows:
                return True, None

            expected_prev = GENESIS_HASH
            for r in rows:
                seq = r["sequence"]
                if r["prev_hash"] != expected_prev:
                    return False, f"Broken hash chain at sequence {seq}: expected prev_hash {expected_prev[:12]}..., got {r['prev_hash'][:12]}..."

                # Recalculate hash on exact persisted payload string
                payload_str = r["payload"]
                hash_input = f"{session_id}:{seq}:{r['event_type']}:{r['actor']}:{r['stage']}:{payload_str}:{r['prev_hash']}:{r['timestamp']}"
                expected_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

                if r["event_hash"] != expected_hash:
                    return False, f"Tampered event payload at sequence {seq}: hash mismatch."

                expected_prev = r["event_hash"]

            return True, None

    def create_checkpoint(self, session_id: str, actor: str, stage: str, checkpoint_name: str) -> Dict[str, Any]:
        """Creates a named checkpoint event in the session timeline."""
        return self.record_event(
            session_id=session_id,
            event_type="CHECKPOINT",
            actor=actor,
            stage=stage,
            payload={"checkpoint": checkpoint_name},
            checkpoint_name=checkpoint_name
        )

    def rollback_to_checkpoint(self, session_id: str, checkpoint_name: str) -> Dict[str, Any]:
        """
        Rolls back the event stream to the state of the named checkpoint.
        Removes succeeding events and appends a ROLLBACK_EXECUTED audit event.
        """
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT sequence FROM event_stream WHERE session_id = ? AND checkpoint_name = ? ORDER BY sequence DESC LIMIT 1;",
                (session_id, checkpoint_name)
            )
            row = cur.fetchone()
            if not row:
                cur.close()
                raise ValueError(f"Checkpoint '{checkpoint_name}' not found for session '{session_id}'.")

            cp_seq = row["sequence"]
            # Delete events after this checkpoint sequence
            cur.execute(
                "DELETE FROM event_stream WHERE session_id = ? AND sequence > ?;",
                (session_id, cp_seq)
            )
            cur.close()

            # Record rollback event
            return self.record_event(
                session_id=session_id,
                event_type="ROLLBACK_EXECUTED",
                actor="system",
                stage="ROLLBACK_CONTROLLER",
                payload={"target_checkpoint": checkpoint_name, "reverted_to_sequence": cp_seq}
            )

    # ---------------------------------------------------------------------------
    # Diagnostics & Lifecycle
    # ---------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, int]:
        """Returns row counts across all 5 partitions."""
        with self._lock:
            cur = self._conn.cursor()
            stats = {}
            for table in ("memory_blocks", "actor_mailbox", "skill_vault", "healing_cache", "event_stream"):
                cur.execute(f"SELECT COUNT(*) AS cnt FROM {table};")
                stats[table] = cur.fetchone()["cnt"]
            cur.close()
            return stats

    def clear_all(self):
        """Clears all records across all partitions (test teardown helper)."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("DELETE FROM memory_blocks;")
            cur.execute("DELETE FROM actor_mailbox;")
            cur.execute("DELETE FROM skill_vault;")
            cur.execute("DELETE FROM healing_cache;")
            cur.execute("DELETE FROM event_stream;")
            cur.close()

    def close(self):
        """Closes the underlying SQLite connection."""
        with self._lock:
            try:
                self._conn.close()
            except Exception as err:
                _ = err

    def __enter__(self) -> "UnifiedMemoryBus":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Singleton / factory helper
_GLOBAL_BUS: Optional[UnifiedMemoryBus] = None
_BUS_LOCK = threading.Lock()


def get_memory_bus(db_path: Optional[str] = None) -> UnifiedMemoryBus:
    """Returns singleton UnifiedMemoryBus instance or creates new if path specified."""
    global _GLOBAL_BUS
    if db_path is not None:
        return UnifiedMemoryBus(db_path=db_path)
    with _BUS_LOCK:
        if _GLOBAL_BUS is None:
            _GLOBAL_BUS = UnifiedMemoryBus()
        return _GLOBAL_BUS
