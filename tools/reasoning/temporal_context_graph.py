#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Bi-Temporal Context Graph & Zero-Dependency Community Summary Engine.

Synthesizes Graphiti's bi-temporal episode provenance & automatic contradiction
invalidation with GraphRAG's community detection & Global/Local retrieval in
pure Python 3.10+ stdlib (SQLite WAL).
"""

from __future__ import annotations

import argparse
from contextlib import nullcontext
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
import sqlite3
import sys
from typing import Any, Dict, List, Literal, Optional, Sequence, Set, Tuple
import uuid

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass

try:
    from tools.core.file_lock import acquire_file_lock
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    acquire_file_lock = None  # type: ignore[assignment]

SearchMode = Literal["local", "global", "hybrid"]
VALID_SEARCH_MODES: Tuple[str, ...] = ("local", "global", "hybrid")


def _parse_iso_strict(ts: str) -> datetime:
    """Strictly parses an ISO-8601 timestamp string into timezone-aware UTC datetime."""
    if not isinstance(ts, str) or not ts.strip():
        raise ValueError("Timestamp must be a non-empty ISO-8601 string.")
    raw = ts.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid ISO-8601 timestamp: '{ts}'") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _format_utc(dt: Optional[datetime] = None) -> str:
    cur = dt if dt is not None else datetime.now(timezone.utc)
    if cur.tzinfo is None:
        cur = cur.replace(tzinfo=timezone.utc)
    return cur.astimezone(timezone.utc).isoformat()


@dataclass(frozen=True)
class EpisodeRecordDTO:
    episode_id: str
    source: str
    content: str
    reference_time: str
    created_at: str
    entity_ids: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BiTemporalEdgeDTO:
    edge_id: str
    source_id: str
    target_id: str
    relation: str
    fact: str
    valid_at: str
    invalid_at: Optional[str]
    created_at: str
    expired_at: Optional[str]
    episode_ids: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CommunitySummaryDTO:
    community_id: str
    level: int
    member_ids: Tuple[str, ...]
    summary_text: str
    modularity_weight: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TemporalContextGraph:
    """SQLite WAL bi-temporal entity-episode graph with pure-Python community clustering."""

    def __init__(self, db_path: str = ".synapse/temporal_context_graph.db", auto_wal: bool = True) -> None:
        self.db_path = db_path
        self._is_memory = db_path == ":memory:"
        if not self._is_memory:
            parent = os.path.dirname(os.path.abspath(db_path))
            if parent:
                os.makedirs(parent, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        if auto_wal and not self._is_memory:
            self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA busy_timeout=5000;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.execute("PRAGMA foreign_keys=ON;")
        self._init_schema()

    def _lock_ctx(self):
        if self._is_memory or acquire_file_lock is None:
            return nullcontext()
        return acquire_file_lock(f"{self.db_path}.lock", timeout=5.0)

    def _init_schema(self) -> None:
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    episode_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    content TEXT NOT NULL,
                    reference_time TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    entity_ids_json TEXT NOT NULL DEFAULT '[]'
                );
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS temporal_edges (
                    edge_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    fact TEXT NOT NULL,
                    valid_at TEXT NOT NULL,
                    invalid_at TEXT,
                    created_at TEXT NOT NULL,
                    expired_at TEXT,
                    episode_ids_json TEXT NOT NULL DEFAULT '[]'
                );
                """
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tedges_subj_rel ON temporal_edges(source_id, relation);"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tedges_valid ON temporal_edges(valid_at, invalid_at);"
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS communities (
                    community_id TEXT PRIMARY KEY,
                    level INTEGER NOT NULL,
                    member_ids_json TEXT NOT NULL,
                    summary_text TEXT NOT NULL,
                    modularity_weight REAL NOT NULL,
                    as_of TEXT NOT NULL
                );
                """
            )

    def close(self) -> None:
        if self.conn:
            self.conn.close()

    def __enter__(self) -> "TemporalContextGraph":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _upsert_fact_edge(
        self,
        src_id: str,
        rel: str,
        tgt_id: str,
        fact_text: str,
        ref_dt: datetime,
        ref_iso: str,
        created_iso: str,
        episode_id: str,
    ) -> None:
        """Records a fact edge with order-safe bi-temporal invalidation."""
        cur = self.conn.execute(
            """
            SELECT edge_id, target_id, episode_ids_json, valid_at, invalid_at
            FROM temporal_edges
            WHERE source_id = ? AND relation = ?
            ORDER BY valid_at ASC;
            """,
            (src_id, rel),
        )
        rows = cur.fetchall()
        same_target_row = None
        earliest_future_iso: Optional[str] = None
        earliest_future_dt: Optional[datetime] = None

        for row in rows:
            row_valid_dt = _parse_iso_strict(row["valid_at"])
            row_inv_dt = _parse_iso_strict(row["invalid_at"]) if row["invalid_at"] is not None else None
            overlaps_now = row_valid_dt <= ref_dt and (row_inv_dt is None or ref_dt < row_inv_dt)
            if row["target_id"] == tgt_id and overlaps_now:
                same_target_row = row
                continue
            if row["target_id"] != tgt_id and overlaps_now:
                self.conn.execute(
                    "UPDATE temporal_edges SET invalid_at = ?, expired_at = ? WHERE edge_id = ?;",
                    (ref_iso, created_iso, row["edge_id"]),
                )
            elif row_valid_dt > ref_dt and (earliest_future_dt is None or row_valid_dt < earliest_future_dt):
                earliest_future_dt = row_valid_dt
                earliest_future_iso = row["valid_at"]

        if same_target_row is not None:
            existing_eps = list(json.loads(same_target_row["episode_ids_json"]))
            if episode_id not in existing_eps:
                existing_eps.append(episode_id)
            self.conn.execute(
                "UPDATE temporal_edges SET episode_ids_json = ?, fact = ? WHERE edge_id = ?;",
                (json.dumps(existing_eps), fact_text, same_target_row["edge_id"]),
            )
            return

        edge_id = f"edge_{uuid.uuid4().hex[:12]}"
        new_expired = created_iso if earliest_future_iso is not None else None
        self.conn.execute(
            """
            INSERT INTO temporal_edges (
                edge_id, source_id, target_id, relation, fact,
                valid_at, invalid_at, created_at, expired_at, episode_ids_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                edge_id,
                src_id,
                tgt_id,
                rel,
                fact_text,
                ref_iso,
                earliest_future_iso,
                created_iso,
                new_expired,
                json.dumps([episode_id]),
            ),
        )

    def add_episode(
        self,
        source: str,
        content: str,
        reference_time: str,
        facts: Sequence[Tuple[str, str, str, str]],
    ) -> EpisodeRecordDTO:
        """Ingests an episode, records provenance, and invalidates conflicting active edges."""
        if not isinstance(source, str) or not source.strip():
            raise ValueError("Episode source must be a non-empty string.")
        ref_dt = _parse_iso_strict(reference_time)
        ref_iso = _format_utc(ref_dt)
        created_iso = _format_utc()
        episode_id = f"ep_{uuid.uuid4().hex[:12]}"

        validated_facts: List[Tuple[str, str, str, str]] = []
        entities: List[str] = []
        seen_entities: Set[str] = set()
        for item in facts:
            if len(item) != 4:
                raise ValueError("Each fact must be a 4-tuple: (source_id, relation, target_id, fact_text).")
            src_id, rel, tgt_id, fact_text = item
            if not src_id or not src_id.strip() or not tgt_id or not tgt_id.strip() or not rel or not rel.strip():
                raise ValueError("Fact entity IDs and relation must be non-empty strings.")
            s_clean, r_clean, t_clean, f_clean = src_id.strip(), rel.strip(), tgt_id.strip(), str(fact_text).strip()
            validated_facts.append((s_clean, r_clean, t_clean, f_clean))
            for ent in (s_clean, t_clean):
                if ent not in seen_entities:
                    seen_entities.add(ent)
                    entities.append(ent)

        with self._lock_ctx():
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO episodes (episode_id, source, content, reference_time, created_at, entity_ids_json)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (episode_id, source.strip(), str(content), ref_iso, created_iso, json.dumps(entities)),
                )
                for src_id, rel, tgt_id, fact_text in validated_facts:
                    self._upsert_fact_edge(src_id, rel, tgt_id, fact_text, ref_dt, ref_iso, created_iso, episode_id)

        return EpisodeRecordDTO(
            episode_id=episode_id,
            source=source.strip(),
            content=str(content),
            reference_time=ref_iso,
            created_at=created_iso,
            entity_ids=tuple(entities),
        )

    def _row_to_edge(self, row: sqlite3.Row) -> BiTemporalEdgeDTO:
        return BiTemporalEdgeDTO(
            edge_id=row["edge_id"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            relation=row["relation"],
            fact=row["fact"],
            valid_at=row["valid_at"],
            invalid_at=row["invalid_at"],
            created_at=row["created_at"],
            expired_at=row["expired_at"],
            episode_ids=tuple(json.loads(row["episode_ids_json"])),
        )

    def list_edges(
        self,
        include_invalid: bool = False,
        as_of: Optional[str] = None,
    ) -> List[BiTemporalEdgeDTO]:
        """Lists edges optionally filtered at an exact point-in-time [valid_at, invalid_at)."""
        cur = self.conn.execute("SELECT * FROM temporal_edges ORDER BY valid_at ASC, edge_id ASC;")
        edges = [self._row_to_edge(r) for r in cur.fetchall()]
        if as_of is not None:
            as_of_dt = _parse_iso_strict(as_of)
            filtered: List[BiTemporalEdgeDTO] = []
            for e in edges:
                v_dt = _parse_iso_strict(e.valid_at)
                if as_of_dt < v_dt:
                    continue
                if e.invalid_at is not None:
                    inv_dt = _parse_iso_strict(e.invalid_at)
                    if as_of_dt >= inv_dt:
                        continue
                filtered.append(e)
            return filtered
        if not include_invalid:
            return [e for e in edges if e.invalid_at is None]
        return edges

    def _compute_communities_at(self, as_of_iso: str) -> List[CommunitySummaryDTO]:
        """Pure-Python deterministic label-propagation community clustering at exact timestamp."""
        active_edges = self.list_edges(as_of=as_of_iso)
        if not active_edges:
            return []

        adjacency: Dict[str, Set[str]] = {}
        for e in active_edges:
            adjacency.setdefault(e.source_id, set()).add(e.target_id)
            adjacency.setdefault(e.target_id, set()).add(e.source_id)

        nodes = sorted(adjacency.keys())
        labels: Dict[str, str] = {n: n for n in nodes}
        for _ in range(max(10, len(nodes))):
            changed = False
            for n in nodes:
                nbrs = adjacency[n]
                if not nbrs:
                    continue
                counts: Dict[str, int] = {}
                for nb in nbrs:
                    lbl = labels[nb]
                    counts[lbl] = counts.get(lbl, 0) + 1
                best_lbl = min(counts.keys(), key=lambda k: (-counts[k], k))
                if best_lbl != labels[n]:
                    labels[n] = best_lbl
                    changed = True
            if not changed:
                break

        groups: Dict[str, List[str]] = {}
        for n in nodes:
            groups.setdefault(labels[n], []).append(n)

        total_edges = max(1, len(active_edges))
        summaries: List[CommunitySummaryDTO] = []
        for root_key in sorted(groups.keys()):
            members = tuple(sorted(groups[root_key]))
            member_set = set(members)
            internal_edges = [
                e for e in active_edges if e.source_id in member_set and e.target_id in member_set
            ]
            facts_preview = "; ".join(
                f"{e.source_id} -{e.relation}-> {e.target_id} ({e.fact})" for e in internal_edges[:8]
            )
            summary_text = (
                f"Community [{', '.join(members)}] ({len(members)} entities, "
                f"{len(internal_edges)} active relations): {facts_preview}"
            )
            modularity_weight = round(len(internal_edges) / float(total_edges), 4)
            cid_hash = hashlib.sha256("|".join(members).encode("utf-8")).hexdigest()[:10]
            summaries.append(
                CommunitySummaryDTO(
                    community_id=f"comm_{cid_hash}",
                    level=0,
                    member_ids=members,
                    summary_text=summary_text,
                    modularity_weight=modularity_weight,
                )
            )
        return summaries

    def rebuild_communities(self, as_of: Optional[str] = None) -> List[CommunitySummaryDTO]:
        """Rebuilds and persists community summary reports for the given timestamp."""
        as_of_iso = _format_utc(_parse_iso_strict(as_of)) if as_of is not None else _format_utc()
        summaries = self._compute_communities_at(as_of_iso)
        with self._lock_ctx():
            with self.conn:
                self.conn.execute("DELETE FROM communities;")
                for c in summaries:
                    self.conn.execute(
                        """
                        INSERT INTO communities (
                            community_id, level, member_ids_json, summary_text, modularity_weight, as_of
                        ) VALUES (?, ?, ?, ?, ?, ?);
                        """,
                        (c.community_id, c.level, json.dumps(list(c.member_ids)), c.summary_text, c.modularity_weight, as_of_iso),
                    )
        return summaries

    def query_as_of(
        self,
        query: str,
        as_of: Optional[str] = None,
        mode: SearchMode = "hybrid",
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Queries active facts and/or community summaries at a specific timestamp."""
        if mode not in VALID_SEARCH_MODES:
            raise ValueError(f"Invalid search mode '{mode}'. Must be one of {VALID_SEARCH_MODES}.")
        as_of_iso = _format_utc(_parse_iso_strict(as_of)) if as_of is not None else _format_utc()
        q_tokens = [tok for tok in str(query or "").lower().replace("_", " ").split() if tok]
        q_raw = str(query or "").lower().strip()

        matched_edges: List[Dict[str, Any]] = []
        if mode in ("local", "hybrid"):
            edges = self.list_edges(as_of=as_of_iso)
            for e in edges:
                haystack = f"{e.source_id} {e.relation} {e.target_id} {e.fact}".lower()
                if not q_raw or q_raw in haystack or any(t in haystack for t in q_tokens):
                    matched_edges.append(e.to_dict())
            matched_edges = matched_edges[: max(1, int(limit))]

        matched_comms: List[Dict[str, Any]] = []
        if mode in ("global", "hybrid"):
            cur = self.conn.execute(
                "SELECT * FROM communities WHERE as_of = ? ORDER BY modularity_weight DESC, community_id ASC;",
                (as_of_iso,),
            )
            rows = cur.fetchall()
            if not rows:
                comm_dicts = [c.to_dict() for c in self._compute_communities_at(as_of_iso)]
            else:
                comm_dicts = [
                    CommunitySummaryDTO(
                        community_id=r["community_id"],
                        level=r["level"],
                        member_ids=tuple(json.loads(r["member_ids_json"])),
                        summary_text=r["summary_text"],
                        modularity_weight=float(r["modularity_weight"]),
                    ).to_dict()
                    for r in rows
                ]
            for c in comm_dicts:
                haystack = f"{c['summary_text']} {' '.join(c['member_ids'])}".lower()
                if not q_raw or q_raw in haystack or any(t in haystack for t in q_tokens):
                    matched_comms.append(c)
            matched_comms = matched_comms[: max(1, int(limit))]

        return {
            "status": "ok",
            "mode": mode,
            "as_of": as_of_iso,
            "query": query,
            "edges": matched_edges,
            "communities": matched_comms,
        }

    def get_stats(self) -> Dict[str, int]:
        ep_cnt = int(self.conn.execute("SELECT COUNT(*) FROM episodes;").fetchone()[0])
        total_edges = int(self.conn.execute("SELECT COUNT(*) FROM temporal_edges;").fetchone()[0])
        active_edges = int(
            self.conn.execute("SELECT COUNT(*) FROM temporal_edges WHERE invalid_at IS NULL;").fetchone()[0]
        )
        comm_cnt = int(self.conn.execute("SELECT COUNT(*) FROM communities;").fetchone()[0])
        return {
            "episodes": ep_cnt,
            "total_edges": total_edges,
            "active_edges": active_edges,
            "invalidated_edges": total_edges - active_edges,
            "communities": comm_cnt,
        }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Synapse Hub Bi-Temporal Context Graph & Community Engine")
    parser.add_argument("--db-path", default=".synapse/temporal_context_graph.db", help="SQLite DB path")
    sub = parser.add_subparsers(dest="command")

    p_add = sub.add_parser("add-episode", help="Ingest a temporal episode with facts")
    p_add.add_argument("--source", required=True)
    p_add.add_argument("--content", required=True)
    p_add.add_argument("--reference-time", required=True)
    p_add.add_argument("--facts-json", default="[]")
    p_add.add_argument("--json", action="store_true")

    p_q = sub.add_parser("query", help="Point-in-time query (local/global/hybrid)")
    p_q.add_argument("--query", default="")
    p_q.add_argument("--as-of", default=None)
    p_q.add_argument("--mode", default="hybrid", choices=list(VALID_SEARCH_MODES))
    p_q.add_argument("--limit", type=int, default=20)
    p_q.add_argument("--json", action="store_true")

    p_c = sub.add_parser("communities", help="Rebuild community summaries at timestamp")
    p_c.add_argument("--as-of", default=None)
    p_c.add_argument("--json", action="store_true")

    p_s = sub.add_parser("stats", help="Show temporal graph statistics")
    p_s.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    with TemporalContextGraph(db_path=args.db_path) as graph:
        if args.command == "add-episode":
            raw_facts = json.loads(args.facts_json)
            facts = [tuple(f) for f in raw_facts]
            ep = graph.add_episode(
                source=args.source,
                content=args.content,
                reference_time=args.reference_time,
                facts=facts,
            )
            payload = {"status": "ok", "episode": ep.to_dict()}
        elif args.command == "query":
            payload = graph.query_as_of(query=args.query, as_of=args.as_of, mode=args.mode, limit=args.limit)
        elif args.command == "communities":
            comms = graph.rebuild_communities(as_of=args.as_of)
            payload = {
                "status": "ok",
                "community_count": len(comms),
                "communities": [c.to_dict() for c in comms],
            }
        else:
            payload = {"status": "ok", "stats": graph.get_stats()}

    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2))
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
