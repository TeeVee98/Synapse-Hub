#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/core/task_graph_memory.py — Persistent Dependency-Graph Task Memory
-------------------------------------------------------------------------
Stdlib SQLite (WAL mode) + JSONL persistent task dependency graph inspired by
gastownhall/beads and mcp-shrimp-task-manager:
  - Typed dependency edges: blocks, waits_for, discovered_from, related
  - Acyclic blocking invariant with cycle detection before insertion
  - Transitive is_blocked computation and ready() frontier queries
  - Optimistic concurrency control via row_version compare-and-swap (CAS)
  - Lease TTL claiming, heartbeat renewal, and expired-lease reclamation
  - Compaction-resilient JSONL snapshot export & archived memory records
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, Set, Tuple, Union

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

logger = logging.getLogger(__name__)

EdgeType = Literal["blocks", "discovered_from", "waits_for", "related"]
TaskLifecycleStatus = Literal["open", "in_progress", "done", "blocked", "cancelled"]

VALID_EDGE_TYPES: Tuple[str, ...] = ("blocks", "discovered_from", "waits_for", "related")
BLOCKING_EDGE_TYPES: Tuple[str, ...] = ("blocks", "waits_for")
VALID_STATUSES: Tuple[str, ...] = ("open", "in_progress", "done", "blocked", "cancelled")
TERMINAL_STATUSES: Tuple[str, ...] = ("done", "cancelled")


class StaleRevisionError(RuntimeError):
    """Raised when optimistic row_version compare-and-swap detects a concurrent write."""


class LeaseConflictError(RuntimeError):
    """Raised when attempting to claim a task held by an active non-expired lease."""


@dataclass(frozen=True)
class TaskNodeDTO:
    task_id: str
    title: str
    status: TaskLifecycleStatus
    complexity_score: int
    row_version: int
    is_blocked: bool = False
    blocking_ids: Tuple[str, ...] = ()
    lease_owner: Optional[str] = None
    lease_expires_at: Optional[float] = None
    verification_criteria: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["blocking_ids"] = list(self.blocking_ids)
        payload["verification_criteria"] = list(self.verification_criteria)
        return payload


class TaskGraphMemory:
    """SQLite WAL-backed dependency graph with CAS revisions and lease TTL."""

    def __init__(self, db_path: Union[str, Path]) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                complexity_score INTEGER NOT NULL DEFAULT 3,
                row_version INTEGER NOT NULL DEFAULT 1,
                lease_owner TEXT,
                lease_expires_at REAL,
                heartbeat_at REAL,
                verification_criteria TEXT NOT NULL DEFAULT '[]',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS edges (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                created_at REAL NOT NULL,
                PRIMARY KEY (source_id, target_id, edge_type),
                FOREIGN KEY (source_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES tasks(task_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS memory_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_slug TEXT NOT NULL,
                summary TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            """
        )
        self._conn.commit()

    def close(self) -> None:
        if getattr(self, "_conn", None) is not None:
            self._conn.close()

    def __enter__(self) -> "TaskGraphMemory":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def add_task(
        self,
        task_id: str,
        title: str,
        complexity_score: int = 3,
        verification_criteria: Sequence[str] = (),
        status: TaskLifecycleStatus = "open",
    ) -> TaskNodeDTO:
        clean_id = (task_id or "").strip()
        clean_title = (title or "").strip()
        if not clean_id:
            raise ValueError("task_id must be a non-empty string")
        if not clean_title:
            raise ValueError("title must be a non-empty string")
        if not isinstance(complexity_score, int) or complexity_score < 1 or complexity_score > 10:
            raise ValueError("complexity_score must be an integer between 1 and 10")
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}")

        now = time.time()
        criteria_list = [str(c).strip() for c in verification_criteria if str(c).strip()]
        self._conn.execute(
            """
            INSERT INTO tasks (
                task_id, title, status, complexity_score, row_version,
                verification_criteria, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (clean_id, clean_title, status, complexity_score, json.dumps(criteria_list), now, now),
        )
        self._conn.commit()
        node = self.get_task(clean_id)
        if node is None:
            raise RuntimeError(f"Failed to load inserted task: {clean_id}")
        return node

    def _creates_blocking_cycle(self, source_id: str, target_id: str) -> bool:
        if source_id == target_id:
            return True
        visited: Set[str] = set()
        stack: List[str] = [target_id]
        placeholders = ",".join("?" for _ in BLOCKING_EDGE_TYPES)
        while stack:
            current = stack.pop()
            if current == source_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            rows = self._conn.execute(
                f"SELECT target_id FROM edges WHERE source_id = ? AND edge_type IN ({placeholders})",
                (current, *BLOCKING_EDGE_TYPES),
            ).fetchall()
            for row in rows:
                nxt = str(row["target_id"])
                if nxt not in visited:
                    stack.append(nxt)
        return False

    def add_edge(self, source_id: str, target_id: str, edge_type: EdgeType = "blocks") -> None:
        if edge_type not in VALID_EDGE_TYPES:
            raise ValueError(f"Invalid edge_type: {edge_type}")
        if self.get_task(source_id) is None or self.get_task(target_id) is None:
            raise ValueError(f"Both source_id ({source_id}) and target_id ({target_id}) must exist")
        if edge_type in BLOCKING_EDGE_TYPES and self._creates_blocking_cycle(source_id, target_id):
            raise ValueError(f"Blocking edge {source_id} -> {target_id} would introduce a dependency cycle")

        self._conn.execute(
            """
            INSERT OR IGNORE INTO edges (source_id, target_id, edge_type, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (source_id, target_id, edge_type, time.time()),
        )
        self._conn.commit()

    def _compute_blocking_ids(self, task_id: str) -> Tuple[str, ...]:
        """Returns all unresolved ancestor blockers (direct & transitive) for task_id."""
        placeholders = ",".join("?" for _ in BLOCKING_EDGE_TYPES)
        visited: Set[str] = set()
        unresolved: List[str] = []
        queue: List[str] = [task_id]
        while queue:
            current = queue.pop(0)
            rows = self._conn.execute(
                f"""
                SELECT e.source_id, t.status
                FROM edges e
                JOIN tasks t ON t.task_id = e.source_id
                WHERE e.target_id = ? AND e.edge_type IN ({placeholders})
                ORDER BY e.source_id ASC
                """,
                (current, *BLOCKING_EDGE_TYPES),
            ).fetchall()
            for row in rows:
                blocker_id = str(row["source_id"])
                blocker_status = str(row["status"])
                if blocker_id in visited:
                    continue
                visited.add(blocker_id)
                if blocker_status not in TERMINAL_STATUSES:
                    unresolved.append(blocker_id)
                queue.append(blocker_id)
        return tuple(sorted(unresolved))

    def _row_to_dto(self, row: sqlite3.Row) -> TaskNodeDTO:
        tid = str(row["task_id"])
        blocking = self._compute_blocking_ids(tid)
        criteria_raw = json.loads(row["verification_criteria"] or "[]")
        return TaskNodeDTO(
            task_id=tid,
            title=str(row["title"]),
            status=row["status"],
            complexity_score=int(row["complexity_score"]),
            row_version=int(row["row_version"]),
            is_blocked=len(blocking) > 0,
            blocking_ids=blocking,
            lease_owner=row["lease_owner"],
            lease_expires_at=row["lease_expires_at"],
            verification_criteria=tuple(str(x) for x in criteria_raw),
        )

    def get_task(self, task_id: str) -> Optional[TaskNodeDTO]:
        row = self._conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_dto(row)

    def list_tasks(self) -> List[TaskNodeDTO]:
        rows = self._conn.execute("SELECT * FROM tasks ORDER BY created_at ASC, task_id ASC").fetchall()
        return [self._row_to_dto(r) for r in rows]

    def get_ready_tasks(self) -> List[TaskNodeDTO]:
        """Returns open tasks that have zero unresolved blocking dependencies."""
        rows = self._conn.execute(
            "SELECT * FROM tasks WHERE status = 'open' ORDER BY created_at ASC, task_id ASC"
        ).fetchall()
        ready: List[TaskNodeDTO] = []
        for row in rows:
            dto = self._row_to_dto(row)
            if not dto.is_blocked:
                ready.append(dto)
        return ready

    def update_status(
        self,
        task_id: str,
        status: TaskLifecycleStatus,
        expected_version: Optional[int] = None,
    ) -> TaskNodeDTO:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}")
        existing = self.get_task(task_id)
        if existing is None:
            raise KeyError(f"Task not found: {task_id}")
        if expected_version is not None and existing.row_version != expected_version:
            raise StaleRevisionError(
                f"Stale revision for {task_id}: expected {expected_version}, actual {existing.row_version}"
            )
        new_version = existing.row_version + 1
        now = time.time()
        clear_lease = status in TERMINAL_STATUSES or status == "open"
        if clear_lease:
            cursor = self._conn.execute(
                """
                UPDATE tasks
                SET status = ?, row_version = ?, lease_owner = NULL, lease_expires_at = NULL, updated_at = ?
                WHERE task_id = ? AND row_version = ?
                """,
                (status, new_version, now, task_id, existing.row_version),
            )
        else:
            cursor = self._conn.execute(
                """
                UPDATE tasks
                SET status = ?, row_version = ?, updated_at = ?
                WHERE task_id = ? AND row_version = ?
                """,
                (status, new_version, now, task_id, existing.row_version),
            )
        if cursor.rowcount != 1:
            self._conn.rollback()
            raise StaleRevisionError(f"Concurrent modification detected on task {task_id}")
        self._conn.commit()
        updated = self.get_task(task_id)
        if updated is None:
            raise RuntimeError(f"Failed to reload task after update: {task_id}")
        return updated

    def claim_task(
        self,
        task_id: str,
        owner: str,
        ttl_sec: float = 300.0,
        now_ts: Optional[float] = None,
    ) -> TaskNodeDTO:
        clean_owner = (owner or "").strip()
        if not clean_owner:
            raise ValueError("owner must be a non-empty string")
        if ttl_sec <= 0:
            raise ValueError("ttl_sec must be positive")
        existing = self.get_task(task_id)
        if existing is None:
            raise KeyError(f"Task not found: {task_id}")
        now = time.time() if now_ts is None else float(now_ts)
        if (
            existing.lease_owner is not None
            and existing.lease_owner != clean_owner
            and existing.lease_expires_at is not None
            and existing.lease_expires_at > now
        ):
            raise LeaseConflictError(
                f"Task {task_id} is actively leased by {existing.lease_owner} until {existing.lease_expires_at}"
            )

        expires_at = now + float(ttl_sec)
        new_version = existing.row_version + 1
        cursor = self._conn.execute(
            """
            UPDATE tasks
            SET status = 'in_progress', lease_owner = ?, lease_expires_at = ?, heartbeat_at = ?,
                row_version = ?, updated_at = ?
            WHERE task_id = ? AND row_version = ?
            """,
            (clean_owner, expires_at, now, new_version, now, task_id, existing.row_version),
        )
        if cursor.rowcount != 1:
            self._conn.rollback()
            raise StaleRevisionError(f"Concurrent claim detected on task {task_id}")
        self._conn.commit()
        claimed = self.get_task(task_id)
        if claimed is None:
            raise RuntimeError(f"Failed to reload claimed task: {task_id}")
        return claimed

    def heartbeat(
        self,
        task_id: str,
        owner: str,
        ttl_sec: float = 300.0,
        now_ts: Optional[float] = None,
    ) -> TaskNodeDTO:
        existing = self.get_task(task_id)
        if existing is None:
            raise KeyError(f"Task not found: {task_id}")
        if existing.lease_owner != owner:
            raise LeaseConflictError(f"Owner {owner} does not hold lease for {task_id}")
        now = time.time() if now_ts is None else float(now_ts)
        expires_at = now + float(ttl_sec)
        self._conn.execute(
            "UPDATE tasks SET lease_expires_at = ?, heartbeat_at = ?, updated_at = ? WHERE task_id = ?",
            (expires_at, now, now, task_id),
        )
        self._conn.commit()
        refreshed = self.get_task(task_id)
        if refreshed is None:
            raise RuntimeError(f"Failed to reload task after heartbeat: {task_id}")
        return refreshed

    def reclaim_expired_leases(self, now_ts: Optional[float] = None) -> List[str]:
        now = time.time() if now_ts is None else float(now_ts)
        rows = self._conn.execute(
            """
            SELECT task_id FROM tasks
            WHERE lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL AND lease_expires_at <= ?
            ORDER BY task_id ASC
            """,
            (now,),
        ).fetchall()
        reclaimed = [str(r["task_id"]) for r in rows]
        if reclaimed:
            self._conn.execute(
                """
                UPDATE tasks
                SET status = CASE WHEN status = 'in_progress' THEN 'open' ELSE status END,
                    lease_owner = NULL, lease_expires_at = NULL, row_version = row_version + 1, updated_at = ?
                WHERE lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL AND lease_expires_at <= ?
                """,
                (now, now),
            )
            self._conn.commit()
        return reclaimed

    def archive_plan_snapshot(self, plan_slug: str, summary: str, payload: Dict[str, Any]) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO memory_snapshots (plan_slug, summary, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (plan_slug, summary, json.dumps(payload, sort_keys=True), time.time()),
        )
        self._conn.commit()
        return int(cur.lastrowid or 0)

    def list_archived_snapshots(self, limit: int = 20) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM memory_snapshots ORDER BY snapshot_id DESC LIMIT ?",
            (max(1, int(limit)),),
        ).fetchall()
        return [
            {
                "snapshot_id": int(r["snapshot_id"]),
                "plan_slug": str(r["plan_slug"]),
                "summary": str(r["summary"]),
                "payload": json.loads(r["payload_json"]),
                "created_at": float(r["created_at"]),
            }
            for r in rows
        ]

    def export_jsonl_snapshot(self, output_path: Union[str, Path]) -> int:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        tasks = self.list_tasks()
        lines = [json.dumps(t.to_dict(), sort_keys=True) for t in tasks]
        content = "\n".join(lines) + ("\n" if lines else "")
        try:
            from tools.core.file_lock import locked_write
            locked_write(str(out), content)
        except Exception as exc:
            logger.debug("Fallback unlocked write for snapshot %s: %s", out, exc)
            out.write_text(content, encoding="utf-8")
        return len(tasks)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synapse Hub Persistent Task Dependency Graph Memory")
    parser.add_argument("--db", default=".synapse/task_graph.db", help="Path to SQLite task graph database")
    sub = parser.add_subparsers(dest="command")

    p_add = sub.add_parser("add", help="Add a new task node")
    p_add.add_argument("--id", required=True, dest="task_id")
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--complexity", type=int, default=3)
    p_add.add_argument("--json", action="store_true")

    p_edge = sub.add_parser("edge", help="Add a dependency edge")
    p_edge.add_argument("--from", required=True, dest="source_id")
    p_edge.add_argument("--to", required=True, dest="target_id")
    p_edge.add_argument("--type", default="blocks", choices=list(VALID_EDGE_TYPES), dest="edge_type")
    p_edge.add_argument("--json", action="store_true")

    p_ready = sub.add_parser("ready", help="List unblocked open tasks")
    p_ready.add_argument("--json", action="store_true")

    p_status = sub.add_parser("status", help="Update task status")
    p_status.add_argument("--id", required=True, dest="task_id")
    p_status.add_argument("--state", required=True, choices=list(VALID_STATUSES))
    p_status.add_argument("--version", type=int, default=None)
    p_status.add_argument("--json", action="store_true")

    p_snap = sub.add_parser("snapshot", help="Export JSONL snapshot")
    p_snap.add_argument("--out", default=".synapse/task_graph_snapshot.jsonl")
    p_snap.add_argument("--json", action="store_true")
    return parser


def _dispatch_cli_command(mem: TaskGraphMemory, args: argparse.Namespace) -> Optional[Dict[str, Any]]:
    if args.command == "add":
        return mem.add_task(args.task_id, args.title, complexity_score=args.complexity).to_dict()
    if args.command == "edge":
        mem.add_edge(args.source_id, args.target_id, edge_type=args.edge_type)
        return {"ok": True, "source_id": args.source_id, "target_id": args.target_id, "edge_type": args.edge_type}
    if args.command == "ready":
        ready = mem.get_ready_tasks()
        return {"ready_count": len(ready), "tasks": [t.to_dict() for t in ready]}
    if args.command == "status":
        return mem.update_status(args.task_id, args.state, expected_version=args.version).to_dict()
    if args.command == "snapshot":
        count = mem.export_jsonl_snapshot(args.out)
        return {"exported": count, "path": str(args.out)}
    return None


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    as_json = bool(getattr(args, "json", False))
    try:
        with TaskGraphMemory(db_path=args.db) as mem:
            payload = _dispatch_cli_command(mem, args)
    except (ValueError, KeyError, StaleRevisionError, LeaseConflictError) as exc:
        if as_json:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1

    if payload is None:
        return 1
    print(json.dumps(payload, indent=2) if as_json else json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
