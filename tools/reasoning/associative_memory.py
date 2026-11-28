#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/reasoning/associative_memory.py — Associative Graph Memory & Sleep Consolidation Engine
---------------------------------------------------------------------------------------------
Implements an associative entity-relationship knowledge graph with continuous exponential
time-decay weighting (w(t) = w0 * e^(-lambda * t)) and an idle sleep consolidation process.
Sleep consolidation clusters recurring granular defect nodes into generalized invariant
principles and prunes/archives obsolete rules from refactored or deleted modules to solve
the "rules only grow" knowledge bloat.
"""

import os
import sys

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except (ImportError, Exception):  # synapse-ignore: SWALLOWED_EXCEPTION
    pass

# Enforce UTF-8 stdio for cross-platform deterministic streaming
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import argparse
import collections
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
import math
import sqlite3
from typing import Any, Dict, List, Optional


def _parse_iso_datetime(iso_str: Optional[str]) -> datetime:
    """Parses an ISO-8601 formatted datetime string into a timezone-aware UTC datetime."""
    if not iso_str or not isinstance(iso_str, str):
        return datetime.now(timezone.utc)
    s = iso_str.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


def _format_iso_datetime(dt: Optional[datetime] = None) -> str:
    """Formats a datetime into ISO-8601 UTC string."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


@dataclass
class MemoryNode:
    entity_id: str
    entity_type: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    access_count: int = 0
    status: str = "active"  # "active", "archived", "pruned"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryEdge:
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AssociativeMemory:
    """
    Associative Entity-Relationship Knowledge Graph Memory Engine backed by SQLite WAL mode.
    Manages entities, causal/associative relations, continuous exponential time decay,
    and idle sleep consolidation into synthesized invariant principles.
    """

    def __init__(self, db_path: str = ".synapse/associative_memory.db", auto_wal: bool = True) -> None:
        self.db_path = db_path
        if db_path != ":memory:":
            parent_dir = os.path.dirname(os.path.abspath(db_path))
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        if auto_wal and db_path != ":memory:":
            self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.execute("PRAGMA foreign_keys=ON;")
        self._init_schema()

    def _init_schema(self) -> None:
        """Initializes tables and indexes for nodes and edges."""
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS nodes (
                    entity_id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    attributes TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    access_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active'
                );
                """
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(entity_type);"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_nodes_status ON nodes(status);"
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS edges (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    weight REAL NOT NULL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (source_id, target_id, relation),
                    FOREIGN KEY (source_id) REFERENCES nodes(entity_id) ON DELETE CASCADE,
                    FOREIGN KEY (target_id) REFERENCES nodes(entity_id) ON DELETE CASCADE
                );
                """
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_edges_weight ON edges(weight);"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_edges_relation ON edges(relation);"
            )

    def close(self) -> None:
        """Closes the underlying SQLite database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self) -> "AssociativeMemory":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    @staticmethod
    def _infer_entity_type(entity_id: str) -> str:
        """Heuristically infers entity type from entity_id naming convention."""
        if not entity_id or not isinstance(entity_id, str):
            return "concept"
        eid = entity_id.lower()
        if eid.startswith("module:") or eid.startswith("mod_"):
            return "module"
        if eid.startswith("rule:") or eid.startswith("inv_"):
            return "rule"
        if eid.startswith("defect:") or eid.startswith("bug:") or eid.startswith("err_"):
            return "defect"
        if eid.startswith("test:") or eid.startswith("tc_"):
            return "test"
        return "concept"

    def record_node(
        self,
        entity_id: str,
        entity_type: str,
        attributes: Optional[Dict[str, Any]] = None,
        status: str = "active",
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Records or updates a node in associative memory.
        If the node already exists, merges attributes and increments access_count.
        """
        if not entity_id or not isinstance(entity_id, str):
            raise ValueError("entity_id must be a non-empty string")
        if not entity_type or not isinstance(entity_type, str):
            raise ValueError("entity_type must be a non-empty string")

        now_str = _format_iso_datetime(timestamp)
        attrs = attributes if attributes is not None else {}
        attrs_json = json.dumps(attrs, ensure_ascii=False)

        with self.conn:
            cursor = self.conn.execute(
                "SELECT attributes, access_count FROM nodes WHERE entity_id = ?",
                (entity_id,),
            )
            row = cursor.fetchone()
            if row:
                existing_attrs = {}
                try:
                    existing_attrs = json.loads(row["attributes"])
                except Exception:
                    existing_attrs = {}
                existing_attrs.update(attrs)
                merged_attrs_json = json.dumps(existing_attrs, ensure_ascii=False)
                new_access_count = row["access_count"] + 1
                self.conn.execute(
                    """
                    UPDATE nodes
                    SET entity_type = ?,
                        attributes = ?,
                        updated_at = ?,
                        access_count = ?,
                        status = ?
                    WHERE entity_id = ?
                    """,
                    (entity_type, merged_attrs_json, now_str, new_access_count, status, entity_id),
                )
            else:
                self.conn.execute(
                    """
                    INSERT INTO nodes (entity_id, entity_type, attributes, created_at, updated_at, access_count, status)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                    """,
                    (entity_id, entity_type, attrs_json, now_str, now_str, status),
                )

    def get_node(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves node metadata by entity_id, or None if not found."""
        cursor = self.conn.execute(
            "SELECT entity_id, entity_type, attributes, created_at, updated_at, access_count, status FROM nodes WHERE entity_id = ?",
            (entity_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        attrs = {}
        try:
            attrs = json.loads(row["attributes"])
        except Exception:
            attrs = {}
        return {
            "entity_id": row["entity_id"],
            "entity_type": row["entity_type"],
            "attributes": attrs,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "access_count": row["access_count"],
            "status": row["status"],
        }

    def record_association(
        self,
        source_id: str,
        target_id: str,
        relation: str,
        weight: float = 1.0,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Records or updates an associative relationship between source_id and target_id.
        Automatically provisions placeholder nodes if entities are not yet recorded.
        """
        if not source_id or not isinstance(source_id, str):
            raise ValueError("source_id must be a non-empty string")
        if not target_id or not isinstance(target_id, str):
            raise ValueError("target_id must be a non-empty string")
        if not relation or not isinstance(relation, str):
            raise ValueError("relation must be a non-empty string")

        weight_float = float(weight)
        if math.isnan(weight_float) or math.isinf(weight_float):
            raise ValueError("weight must be a finite float")

        now_str = _format_iso_datetime(timestamp)

        with self.conn:
            # Ensure source and target nodes exist to satisfy foreign key integrity
            for eid in (source_id, target_id):
                cur = self.conn.execute("SELECT entity_id FROM nodes WHERE entity_id = ?", (eid,))
                if not cur.fetchone():
                    self.conn.execute(
                        """
                        INSERT INTO nodes (entity_id, entity_type, attributes, created_at, updated_at, access_count, status)
                        VALUES (?, ?, '{}', ?, ?, 1, 'active')
                        """,
                        (eid, self._infer_entity_type(eid), now_str, now_str),
                    )

            # Upsert edge
            self.conn.execute(
                """
                INSERT INTO edges (source_id, target_id, relation, weight, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, target_id, relation) DO UPDATE SET
                    weight = excluded.weight,
                    updated_at = excluded.updated_at
                """,
                (source_id, target_id, relation, weight_float, now_str, now_str),
            )

    def query_associations(
        self,
        entity_id: str,
        min_weight: float = 0.0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Queries all active associative relationships connected to entity_id (source or target).
        Increments access count for queried entity. Ordered by weight descending.
        """
        if not entity_id or not isinstance(entity_id, str):
            return []

        # Bump access count
        with self.conn:
            self.conn.execute(
                "UPDATE nodes SET access_count = access_count + 1 WHERE entity_id = ?",
                (entity_id,),
            )

        cursor = self.conn.execute(
            """
            SELECT e.source_id, e.target_id, e.relation, e.weight, e.created_at, e.updated_at,
                   n_src.entity_type AS src_type, n_src.status AS src_status,
                   n_tgt.entity_type AS tgt_type, n_tgt.status AS tgt_status
            FROM edges e
            JOIN nodes n_src ON e.source_id = n_src.entity_id
            JOIN nodes n_tgt ON e.target_id = n_tgt.entity_id
            WHERE (e.source_id = ? OR e.target_id = ?)
              AND e.weight >= ?
              AND n_src.status != 'pruned'
              AND n_tgt.status != 'pruned'
            ORDER BY e.weight DESC, e.updated_at DESC
            LIMIT ?
            """,
            (entity_id, entity_id, float(min_weight), int(limit)),
        )

        results = []
        for row in cursor.fetchall():
            is_outgoing = row["source_id"] == entity_id
            neighbor_id = row["target_id"] if is_outgoing else row["source_id"]
            neighbor_type = row["tgt_type"] if is_outgoing else row["src_type"]
            neighbor_status = row["tgt_status"] if is_outgoing else row["src_status"]

            results.append(
                {
                    "source_id": row["source_id"],
                    "target_id": row["target_id"],
                    "neighbor_id": neighbor_id,
                    "neighbor_type": neighbor_type,
                    "neighbor_status": neighbor_status,
                    "relation": row["relation"],
                    "direction": "outgoing" if is_outgoing else "incoming",
                    "weight": row["weight"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )
        return results

    def apply_time_decay(
        self,
        half_life_days: float = 7.0,
        decay_lambda: Optional[float] = None,
        current_time: Optional[datetime] = None,
    ) -> int:
        """
        Computes continuous temporal weight decay across all edges:
            w(t) = w0 * e^(-lambda * Delta t)
        where Delta t is elapsed time in days from last update to current_time.
        If decay_lambda is not provided, lambda = ln(2) / half_life_days.
        Returns the count of decayed edges.
        """
        if decay_lambda is not None:
            lam = float(decay_lambda)
            if lam < 0.0 or math.isnan(lam):
                raise ValueError("decay_lambda must be non-negative")
        else:
            hl = float(half_life_days)
            if hl <= 0.0 or math.isnan(hl):
                raise ValueError("half_life_days must be strictly positive")
            lam = math.log(2.0) / hl

        t_now = current_time if current_time is not None else datetime.now(timezone.utc)
        if t_now.tzinfo is None:
            t_now = t_now.replace(tzinfo=timezone.utc)
        now_str = _format_iso_datetime(t_now)

        cursor = self.conn.execute(
            "SELECT source_id, target_id, relation, weight, updated_at FROM edges"
        )
        edges_to_update = []
        for row in cursor.fetchall():
            updated_at_dt = _parse_iso_datetime(row["updated_at"])
            delta_seconds = (t_now - updated_at_dt).total_seconds()
            delta_days = max(0.0, delta_seconds / 86400.0)

            # If no time has elapsed, no decay
            if delta_days <= 0.0:
                continue

            decay_factor = math.exp(-lam * delta_days)
            new_weight = max(0.0, row["weight"] * decay_factor)
            edges_to_update.append((new_weight, now_str, row["source_id"], row["target_id"], row["relation"]))

        if edges_to_update:
            with self.conn:
                self.conn.executemany(
                    """
                    UPDATE edges
                    SET weight = ?, updated_at = ?
                    WHERE source_id = ? AND target_id = ? AND relation = ?
                    """,
                    edges_to_update,
                )
        return len(edges_to_update)

    def sleep_consolidate(
        self,
        prune_threshold: float = 0.15,
        generalize_min_cooccurrence: int = 2,
        half_life_days: float = 7.0,
        decay_lambda: Optional[float] = None,
        current_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Executes idle sleep consolidation:
        1. Temporal Weight Decay: Applies exponential decay to compute current weights.
        2. Principle Synthesis & Generalization: Clusters recurrent defect nodes linked to
           common modules or invariants into synthesized generalized rule nodes ("guards").
           Subsumes granular defects into the generalized rule and marks them archived.
        3. Pruning & Archiving: Identifies obsolete rules and weak edges (weight < prune_threshold)
           or orphaned associations, archiving or pruning them to prevent knowledge bloat.
        Returns summary metrics:
            {"nodes_count": int, "edges_count": int, "decayed_count": int, "pruned_count": int, "consolidated_principles": [...]}
        """
        t_now = current_time if current_time is not None else datetime.now(timezone.utc)
        now_str = _format_iso_datetime(t_now)

        # 1. Apply continuous decay
        decayed_count = self.apply_time_decay(
            half_life_days=half_life_days,
            decay_lambda=decay_lambda,
            current_time=t_now,
        )

        consolidated_principles = []
        with self.conn:
            # 2. Defect Pattern Clustering & Invariant Generalization
            # Find active defect nodes and the targets they violate/cause/link to
            defect_cursor = self.conn.execute(
                """
                SELECT n.entity_id AS defect_id, n.attributes AS defect_attrs,
                       e.target_id AS target_id, e.relation AS relation, e.weight AS weight
                FROM nodes n
                JOIN edges e ON n.entity_id = e.source_id
                WHERE n.entity_type = 'defect'
                  AND n.status = 'active'
                  AND e.relation IN ('violates', 'causes', 'found_in', 'associated_with')
                """
            )

            target_clusters: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
            for row in defect_cursor.fetchall():
                target_clusters[row["target_id"]].append(
                    {
                        "defect_id": row["defect_id"],
                        "relation": row["relation"],
                        "weight": row["weight"],
                        "attributes": json.loads(row["defect_attrs"]) if row["defect_attrs"] else {},
                    }
                )

            # Synthesize principles for targets exceeding co-occurrence threshold
            for target_id, defects in target_clusters.items():
                if len(defects) >= generalize_min_cooccurrence:
                    clean_target = target_id.replace("module:", "").replace("rule:", "").replace(":", "_")
                    principle_id = f"rule:consolidated:{clean_target}"
                    principle_name = f"Consolidated Invariant Guard for {target_id}"
                    subsumed_ids = [d["defect_id"] for d in defects]

                    # Synthesize principle node
                    self.record_node(
                        entity_id=principle_id,
                        entity_type="rule",
                        attributes={
                            "name": principle_name,
                            "target": target_id,
                            "subsumed_defects": subsumed_ids,
                            "consolidated_at": now_str,
                            "is_generalized": True,
                        },
                        status="active",
                        timestamp=t_now,
                    )

                    # Guard link to target module
                    self.record_association(
                        source_id=principle_id,
                        target_id=target_id,
                        relation="guards",
                        weight=1.0,
                        timestamp=t_now,
                    )

                    # Subsume granular defects
                    for defect_info in defects:
                        did = defect_info["defect_id"]
                        self.record_association(
                            source_id=did,
                            target_id=principle_id,
                            relation="subsumed_by",
                            weight=0.8,
                            timestamp=t_now,
                        )
                        # Archive granular defect to free active cognitive capacity
                        self.conn.execute(
                            "UPDATE nodes SET status = 'archived', updated_at = ? WHERE entity_id = ?",
                            (now_str, did),
                        )

                    consolidated_principles.append(
                        {
                            "principle_id": principle_id,
                            "target_id": target_id,
                            "subsumed_defects_count": len(subsumed_ids),
                            "subsumed_defects": subsumed_ids,
                        }
                    )

            # 3. Pruning and Archiving
            # Identify and delete weak edges below prune_threshold
            edge_prune_cur = self.conn.execute(
                "DELETE FROM edges WHERE weight < ?", (float(prune_threshold),)
            )
            pruned_edges_count = edge_prune_cur.rowcount

            # Archive orphan rule nodes that have no active outgoing or incoming connections
            orphan_rules_cur = self.conn.execute(
                """
                UPDATE nodes
                SET status = 'archived', updated_at = ?
                WHERE entity_type = 'rule'
                  AND status = 'active'
                  AND entity_id NOT IN (
                      SELECT source_id FROM edges
                      UNION
                      SELECT target_id FROM edges
                  )
                """,
                (now_str,),
            )
            pruned_nodes_count = orphan_rules_cur.rowcount

            total_pruned_count = pruned_edges_count + pruned_nodes_count

            # Final metrics
            active_nodes_cur = self.conn.execute(
                "SELECT COUNT(*) as cnt FROM nodes WHERE status = 'active'"
            )
            active_nodes_count = active_nodes_cur.fetchone()["cnt"]

            edges_count_cur = self.conn.execute("SELECT COUNT(*) as cnt FROM edges")
            edges_count = edges_count_cur.fetchone()["cnt"]

        return {
            "nodes_count": active_nodes_count,
            "edges_count": edges_count,
            "decayed_count": decayed_count,
            "pruned_count": total_pruned_count,
            "consolidated_principles": consolidated_principles,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Calculates graph memory statistics including node breakdowns, edge counts, and weights."""
        cursor = self.conn.execute(
            """
            SELECT
                COUNT(*) as total_nodes,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_nodes,
                SUM(CASE WHEN status = 'archived' THEN 1 ELSE 0 END) as archived_nodes,
                SUM(CASE WHEN status = 'pruned' THEN 1 ELSE 0 END) as pruned_nodes
            FROM nodes
            """
        )
        node_stats = cursor.fetchone()

        type_cursor = self.conn.execute(
            "SELECT entity_type, COUNT(*) as cnt FROM nodes GROUP BY entity_type"
        )
        node_types = {row["entity_type"]: row["cnt"] for row in type_cursor.fetchall()}

        edge_cursor = self.conn.execute(
            """
            SELECT
                COUNT(*) as total_edges,
                COALESCE(AVG(weight), 0.0) as avg_weight,
                COALESCE(MIN(weight), 0.0) as min_weight,
                COALESCE(MAX(weight), 0.0) as max_weight
            FROM edges
            """
        )
        edge_stats = edge_cursor.fetchone()

        rel_cursor = self.conn.execute(
            "SELECT relation, COUNT(*) as cnt FROM edges GROUP BY relation"
        )
        relations = {row["relation"]: row["cnt"] for row in rel_cursor.fetchall()}

        return {
            "total_nodes": node_stats["total_nodes"] or 0,
            "active_nodes": node_stats["active_nodes"] or 0,
            "archived_nodes": node_stats["archived_nodes"] or 0,
            "pruned_nodes": node_stats["pruned_nodes"] or 0,
            "total_edges": edge_stats["total_edges"] or 0,
            "avg_weight": round(float(edge_stats["avg_weight"] or 0.0), 4),
            "min_weight": round(float(edge_stats["min_weight"] or 0.0), 4),
            "max_weight": round(float(edge_stats["max_weight"] or 0.0), 4),
            "node_types": node_types,
            "relations": relations,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the entire associative memory knowledge graph to a dictionary."""
        node_cur = self.conn.execute(
            "SELECT entity_id, entity_type, attributes, created_at, updated_at, access_count, status FROM nodes"
        )
        nodes = []
        for row in node_cur.fetchall():
            attrs = {}
            try:
                attrs = json.loads(row["attributes"])
            except Exception:
                attrs = {}
            nodes.append(
                {
                    "entity_id": row["entity_id"],
                    "entity_type": row["entity_type"],
                    "attributes": attrs,
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "access_count": row["access_count"],
                    "status": row["status"],
                }
            )

        edge_cur = self.conn.execute(
            "SELECT source_id, target_id, relation, weight, created_at, updated_at FROM edges"
        )
        edges = [
            {
                "source_id": row["source_id"],
                "target_id": row["target_id"],
                "relation": row["relation"],
                "weight": row["weight"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in edge_cur.fetchall()
        ]

        return {"nodes": nodes, "edges": edges}

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Loads nodes and edges from a serialized dictionary into the database."""
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        for n in nodes:
            eid = n.get("entity_id")
            etype = n.get("entity_type", "concept")
            attrs = n.get("attributes", {})
            status = n.get("status", "active")
            ts = _parse_iso_datetime(n.get("created_at"))
            if eid:
                self.record_node(eid, etype, attrs, status=status, timestamp=ts)

        for e in edges:
            src = e.get("source_id")
            tgt = e.get("target_id")
            rel = e.get("relation", "associated_with")
            w = float(e.get("weight", 1.0))
            ts = _parse_iso_datetime(e.get("created_at"))
            if src and tgt:
                self.record_association(src, tgt, rel, weight=w, timestamp=ts)

    def sync_to_temporal_graph(
        self,
        temporal_graph: Any,
        reference_time: Optional[str] = None,
        source: str = "associative_memory_sync",
        min_weight: float = 0.0,
    ) -> Dict[str, Any]:
        """Exports active associative edges into a TemporalContextGraph episode."""
        ref_iso = reference_time or _format_iso_datetime()
        cur = self.conn.execute(
            """
            SELECT source_id, relation, target_id, weight
            FROM edges
            WHERE weight >= ?
            ORDER BY source_id ASC, relation ASC, target_id ASC;
            """,
            (float(min_weight),),
        )
        facts = [
            (
                str(r["source_id"]),
                str(r["relation"]),
                str(r["target_id"]),
                f"Associative relation weight={float(r['weight']):.2f}",
            )
            for r in cur.fetchall()
        ]
        episode = temporal_graph.add_episode(
            source=source,
            content=f"Synced {len(facts)} associative edges",
            reference_time=ref_iso,
            facts=facts,
        )
        return {
            "status": "ok",
            "episode_id": episode.episode_id,
            "synced_edges": len(facts),
            "reference_time": episode.reference_time,
        }


def build_arg_parser() -> argparse.ArgumentParser:
    """Builds the CLI argument parser with subcommands and shared flags."""
    parser = argparse.ArgumentParser(
        description="Synapse Hub Associative Graph Memory & Sleep Consolidation Engine (R5)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--db-path",
        default=".synapse/associative_memory.db",
        help="Path to SQLite knowledge graph database file",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Path to file to write JSON/text output",
    )
    parser.add_argument(
        "--gate",
        action="store_true",
        default=False,
        help="Run DoD gate check and self-verification",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Emit strictly valid JSON output to stdout",
    )

    # Subparser common options with default=argparse.SUPPRESS to prevent clobbering parent values
    common_sub_parser = argparse.ArgumentParser(add_help=False)
    common_sub_parser.add_argument(
        "--db-path",
        default=argparse.SUPPRESS,
        help="Path to SQLite knowledge graph database file",
    )
    common_sub_parser.add_argument(
        "--output",
        "-o",
        default=argparse.SUPPRESS,
        help="Path to file to write JSON/text output",
    )
    common_sub_parser.add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Emit strictly valid JSON output to stdout",
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Operational Subcommands")

    # Record / Insert subcommand
    record_parser = subparsers.add_parser(
        "record",
        aliases=["insert"],
        help="Record node or association edge",
        parents=[common_sub_parser],
    )
    record_parser.add_argument("--source", "-s", help="Source entity ID (for association)")
    record_parser.add_argument("--target", "-t", help="Target entity ID (for association)")
    record_parser.add_argument("--relation", "-r", default="associated_with", help="Relationship type")
    record_parser.add_argument("--weight", "-w", type=float, default=1.0, help="Initial association weight (w0)")
    record_parser.add_argument("--entity", "-e", help="Entity ID (for single node recording)")
    record_parser.add_argument("--type", dest="entity_type", default="concept", help="Entity type (module, rule, defect, concept)")
    record_parser.add_argument("--attributes", "-a", help="JSON string of entity attributes")
    record_parser.add_argument("--content", "-c", help="Text content or description of entity (convenience helper)")

    # Query subcommand
    query_parser = subparsers.add_parser(
        "query",
        help="Query associative relationships connected to an entity",
        parents=[common_sub_parser],
    )
    query_parser.add_argument("--entity", "-e", required=True, help="Entity ID to inspect")
    query_parser.add_argument("--min-weight", type=float, default=0.0, help="Minimum association weight threshold")
    query_parser.add_argument("--limit", type=int, default=20, help="Maximum number of associations to return")

    # Decay subcommand
    decay_parser = subparsers.add_parser(
        "decay",
        help="Apply continuous temporal exponential decay",
        parents=[common_sub_parser],
    )
    decay_parser.add_argument("--half-life-days", type=float, default=7.0, help="Half-life in days for weight decay")
    decay_parser.add_argument("--decay-lambda", type=float, default=None, help="Explicit exponential decay constant lambda")

    # Consolidate / Prune subcommand
    cons_parser = subparsers.add_parser(
        "consolidate",
        aliases=["prune"],
        help="Execute sleep consolidation and pruning",
        parents=[common_sub_parser],
    )
    cons_parser.add_argument("--prune-threshold", type=float, default=0.15, help="Weight threshold below which edges are pruned")
    cons_parser.add_argument("--min-cooccurrence", type=int, default=2, help="Min co-occurrence to generalize defect pattern into rule")
    cons_parser.add_argument("--half-life-days", type=float, default=7.0, help="Half-life in days for temporal decay")
    cons_parser.add_argument("--decay-lambda", type=float, default=None, help="Explicit decay lambda")

    # Stats subcommand
    subparsers.add_parser(
        "stats",
        help="Compute knowledge graph statistics and node/edge breakdowns",
        parents=[common_sub_parser],
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI Entry point for associative_memory tool."""
    parser = build_arg_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as se:
        return int(se.code) if isinstance(se.code, int) else 1

    if getattr(args, "gate", False):
        try:
            mem = AssociativeMemory(db_path=":memory:")
            mem.record_node("gate_concept_1", "concept", {"desc": "Test Gate Concept"})
            mem.record_node("gate_concept_2", "concept", {"desc": "Related Gate Concept"})
            mem.record_association("gate_concept_1", "gate_concept_2", "relates_to", weight=0.85)
            stats = mem.get_stats()
            passed = stats.get("total_nodes") == 2 and stats.get("total_edges") == 1
            if args.json:
                print(json.dumps({"gate": "associative_memory", "status": "PASS" if passed else "FAIL", "stats": stats}, indent=2))
            else:
                print("[PASS] Associative Graph Memory DoD Gate verified." if passed else "[FAIL] Associative Memory Gate failed.")
            return 0 if passed else 1
        except Exception as gate_err:
            if args.json:
                print(json.dumps({"gate": "associative_memory", "status": "FAIL", "error": str(gate_err)}, indent=2))
            else:
                print(f"[FAIL] Associative Memory Gate failed: {gate_err}")
            return 1

    if not args.subcommand:
        parser.print_help()
        return 1

    try:
        memory = AssociativeMemory(db_path=args.db_path)
    except Exception as e:
        err_dict = {"status": "error", "error": f"Failed to initialize associative memory database: {str(e)}"}
        if args.json:
            print(json.dumps(err_dict, indent=2))
        else:
            sys.stderr.write(f"Error: {err_dict['error']}\n")
        return 1

    result_payload: Dict[str, Any] = {}
    exit_code = 0

    try:
        subcmd = args.subcommand
        if subcmd in ("record", "insert"):
            attrs = {}
            if getattr(args, "attributes", None):
                try:
                    attrs = json.loads(args.attributes)
                except json.JSONDecodeError as err:
                    raise ValueError(f"Invalid JSON string in --attributes: {err}")
            if getattr(args, "content", None):
                attrs["content"] = args.content

            if args.source and args.target:
                memory.record_association(
                    source_id=args.source,
                    target_id=args.target,
                    relation=args.relation,
                    weight=args.weight,
                )
                result_payload = {
                    "status": "ok",
                    "action": "record_association",
                    "source_id": args.source,
                    "target_id": args.target,
                    "relation": args.relation,
                    "weight": args.weight,
                }
            elif args.entity:
                memory.record_node(
                    entity_id=args.entity,
                    entity_type=args.entity_type,
                    attributes=attrs,
                )
                result_payload = {
                    "status": "ok",
                    "action": "record_node",
                    "entity_id": args.entity,
                    "entity_type": args.entity_type,
                    "attributes": attrs,
                }
            else:
                raise ValueError("Must specify either (--source and --target) for an association or (--entity) for a node.")

        elif subcmd == "query":
            results = memory.query_associations(
                entity_id=args.entity,
                min_weight=args.min_weight,
                limit=args.limit,
            )
            result_payload = {
                "status": "ok",
                "entity_id": args.entity,
                "associations_count": len(results),
                "associations": results,
            }

        elif subcmd == "decay":
            decayed = memory.apply_time_decay(
                half_life_days=args.half_life_days,
                decay_lambda=args.decay_lambda,
            )
            result_payload = {
                "status": "ok",
                "action": "apply_time_decay",
                "decayed_count": decayed,
                "half_life_days": args.half_life_days,
                "decay_lambda": args.decay_lambda,
            }

        elif subcmd in ("consolidate", "prune"):
            summary = memory.sleep_consolidate(
                prune_threshold=args.prune_threshold,
                generalize_min_cooccurrence=args.min_cooccurrence,
                half_life_days=args.half_life_days,
                decay_lambda=args.decay_lambda,
            )
            result_payload = {"status": "ok", **summary}

        elif subcmd == "stats":
            stats = memory.get_stats()
            result_payload = {"status": "ok", **stats}

        else:
            raise ValueError(f"Unknown subcommand: {subcmd}")

    except Exception as e:
        exit_code = 1
        result_payload = {"status": "error", "error": str(e)}

    finally:
        memory.close()

    # Output formatting
    formatted_json = json.dumps(result_payload, indent=2, ensure_ascii=False)
    if args.output:
        try:
            out_dir = os.path.dirname(os.path.abspath(args.output))
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as fp:
                fp.write(formatted_json if args.json else json.dumps(result_payload, indent=2))
        except OSError as io_err:
            sys.stderr.write(f"Warning: Failed to write to output file {args.output}: {io_err}\n")

    if args.json:
        print(formatted_json)
    else:
        if exit_code != 0:
            sys.stderr.write(f"Error: {result_payload.get('error')}\n")
        else:
            print(f"[{result_payload.get('status', 'OK').upper()}] {args.subcommand}: {result_payload}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
