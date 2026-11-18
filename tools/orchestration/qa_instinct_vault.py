#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/orchestration/qa_instinct_vault.py — Project-Scoped QA Flakiness & Defect Instinct Bank
---------------------------------------------------------------------------------------------
Inspired by Continuous Learning v2.1 Homunculus (affaan-m/ecc).
Captures runtime test execution lessons, selector self-heals, and timing adaptations
into project-scoped atomic instincts backed by an embedded SQLite database in WAL mode.

Key Architectural Safeguards:
  1. Scoped Isolation: 12-char SHA-256 project hash isolates instincts per client project.
  2. Multi-Process Safe: Enforces PRAGMA journal_mode=WAL; and PRAGMA busy_timeout=5000;
  3. Auto-Promotion Gate: Promotes instincts to permanent assets when verified >= 2 runs (confidence >= 0.70).
  4. 100% UTF-8 No BOM, Python Standard Library first (zero external dependencies).

Usage:
  python3 tools/orchestration/qa_instinct_vault.py record --project-dir . --domain locator_heal --trigger "btn timeout" --action "use web-first expect"
  python3 tools/orchestration/qa_instinct_vault.py query --project-dir . --domain locator_heal
  python3 tools/orchestration/qa_instinct_vault.py status --project-dir .
  python3 tools/orchestration/qa_instinct_vault.py promote-auto --project-dir .
"""

import os
import sys
import sqlite3
import hashlib
import json
import argparse
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEFAULT_DB_PATH = os.path.join(os.path.expanduser("~"), ".agent_memory", "qa_instincts.db")


def get_project_hash(project_dir: str) -> str:
    """Computes a deterministic 12-character project identifier."""
    abs_path = os.path.abspath(project_dir).replace("\\", "/").lower()
    git_dir = os.path.join(project_dir, ".git")

    seed = abs_path
    if os.path.exists(git_dir):
        config_path = os.path.join(git_dir, "config")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if "url =" in line:
                            seed = line.split("url =", 1)[1].strip()
                            break
            except OSError:  # synapse-ignore: SWALLOWED_EXCEPTION
                pass
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


def init_database(db_path: str) -> sqlite3.Connection:
    """Initializes SQLite database with WAL mode and tables."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA synchronous=NORMAL;")

    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS qa_instincts (
                id TEXT PRIMARY KEY,
                project_hash TEXT NOT NULL,
                domain TEXT NOT NULL,
                trigger_text TEXT NOT NULL,
                action_text TEXT NOT NULL,
                confidence REAL NOT NULL,
                occurrences INTEGER DEFAULT 1,
                broken_locator TEXT,
                healed_locator TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                last_verified_at TEXT NOT NULL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_instincts_proj_domain ON qa_instincts(project_hash, domain);")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS qa_observations (
                id TEXT PRIMARY KEY,
                project_hash TEXT NOT NULL,
                session_id TEXT,
                tool_name TEXT NOT NULL,
                error_signature TEXT NOT NULL,
                resolution TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
    return conn


class QAInstinctVault:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.conn = init_database(self.db_path)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """Closes the underlying SQLite connection."""
        if hasattr(self, "conn") and self.conn:
            try:
                self.conn.close()
            except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                pass

    def record_instinct(
        self,
        project_dir: str,
        domain: str,
        trigger: str,
        action: str,
        broken_locator: Optional[str] = None,
        healed_locator: Optional[str] = None,
        confidence: float = 0.5,
    ) -> Dict[str, Any]:
        """Records or reinforces an atomic QA instinct."""
        proj_hash = get_project_hash(project_dir)
        now = datetime.now(timezone.utc).isoformat()
        instinct_id = f"inst_{hashlib.sha256(f'{proj_hash}:{domain}:{trigger}'.encode()).hexdigest()[:10]}"

        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("SELECT occurrences, confidence FROM qa_instincts WHERE id = ?", (instinct_id,))
            row = cursor.fetchone()

            if row:
                occurrences = row[0] + 1
                # Asymptotic confidence reinforcement formula
                new_confidence = min(0.99, row[1] + (1.0 - row[1]) * 0.25)
                cursor.execute("""
                    UPDATE qa_instincts
                    SET occurrences = ?, confidence = ?, broken_locator = COALESCE(?, broken_locator),
                        healed_locator = COALESCE(?, healed_locator), last_verified_at = ?
                    WHERE id = ?
                """, (occurrences, new_confidence, broken_locator, healed_locator, now, instinct_id))
            else:
                occurrences = 1
                new_confidence = max(0.3, min(confidence, 0.9))
                cursor.execute("""
                    INSERT INTO qa_instincts (
                        id, project_hash, domain, trigger_text, action_text, confidence,
                        occurrences, broken_locator, healed_locator, status, created_at, last_verified_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """, (instinct_id, proj_hash, domain, trigger, action, new_confidence, occurrences, broken_locator, healed_locator, now, now))

        return {
            "id": instinct_id,
            "project_hash": proj_hash,
            "occurrences": occurrences,
            "confidence": round(new_confidence, 4),
        }

    def query_instincts(
        self,
        project_dir: str,
        domain: Optional[str] = None,
        min_confidence: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """Queries instincts for a given project."""
        proj_hash = get_project_hash(project_dir)
        cursor = self.conn.cursor()

        if domain:
            cursor.execute("""
                SELECT id, domain, trigger_text, action_text, confidence, occurrences, broken_locator, healed_locator, status
                FROM qa_instincts
                WHERE project_hash = ? AND domain = ? AND confidence >= ?
                ORDER BY confidence DESC, occurrences DESC
            """, (proj_hash, domain, min_confidence))
        else:
            cursor.execute("""
                SELECT id, domain, trigger_text, action_text, confidence, occurrences, broken_locator, healed_locator, status
                FROM qa_instincts
                WHERE project_hash = ? AND confidence >= ?
                ORDER BY confidence DESC, occurrences DESC
            """, (proj_hash, min_confidence))

        results = []
        for r in cursor.fetchall():
            results.append({
                "id": r[0],
                "domain": r[1],
                "trigger": r[2],
                "action": r[3],
                "confidence": round(r[4], 4),
                "occurrences": r[5],
                "broken_locator": r[6],
                "healed_locator": r[7],
                "status": r[8],
            })
        return results

    def promote_auto(self, project_dir: str, threshold: float = 0.70, min_occurrences: int = 2) -> List[Dict[str, Any]]:
        """Promotes instincts that have demonstrated repeated verification success."""
        proj_hash = get_project_hash(project_dir)
        promoted = []

        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, domain, trigger_text, action_text, confidence, occurrences, broken_locator, healed_locator
                FROM qa_instincts
                WHERE project_hash = ? AND status = 'pending' AND confidence >= ? AND occurrences >= ?
            """, (proj_hash, threshold, min_occurrences))

            rows = cursor.fetchall()
            for r in rows:
                inst_id = r[0]
                cursor.execute("UPDATE qa_instincts SET status = 'promoted' WHERE id = ?", (inst_id,))
                promoted.append({
                    "id": inst_id,
                    "domain": r[1],
                    "trigger": r[2],
                    "action": r[3],
                    "confidence": r[4],
                    "occurrences": r[5],
                    "healed_locator": r[7],
                })
        return promoted


def main():
    parser = argparse.ArgumentParser(description="QA Flakiness & Defect Instinct Bank")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Path to SQLite database")
    subparsers = parser.add_subparsers(dest="command")

    p_rec = subparsers.add_parser("record", help="Record a learned QA instinct")
    p_rec.add_argument("--project-dir", default=".", help="Project workspace directory")
    p_rec.add_argument("--domain", default="locator_heal", help="Instinct domain")
    p_rec.add_argument("--trigger", required=True, help="Trigger condition")
    p_rec.add_argument("--action", required=True, help="Recommended action")
    p_rec.add_argument("--broken", help="Broken locator pattern")
    p_rec.add_argument("--healed", help="Healed locator pattern")
    p_rec.add_argument("--confidence", type=float, default=0.6, help="Initial confidence")

    p_qry = subparsers.add_parser("query", help="Query stored instincts for project")
    p_qry.add_argument("--project-dir", default=".", help="Project workspace directory")
    p_qry.add_argument("--domain", help="Filter by domain")
    p_qry.add_argument("--min-confidence", type=float, default=0.3, help="Minimum confidence threshold")

    p_prom = subparsers.add_parser("promote-auto", help="Auto-promote qualified instincts")
    p_prom.add_argument("--project-dir", default=".", help="Project workspace directory")
    p_prom.add_argument("--threshold", type=float, default=0.70, help="Confidence threshold")

    p_stat = subparsers.add_parser("status", help="Get summary status of instincts for project")
    p_stat.add_argument("--project-dir", default=".", help="Project workspace directory")

    args = parser.parse_args()
    vault = QAInstinctVault(args.db_path)

    if not args.command or args.command == "status":
        p_dir = getattr(args, "project_dir", ".")
        instincts = vault.query_instincts(p_dir, min_confidence=0.0)
        p_hash = get_project_hash(p_dir)
        print(f"[QA INSTINCT BANK] Project: '{p_dir}' (Hash: {p_hash})")
        print(f"Total Instincts: {len(instincts)}")
        for inst in instincts:
            status_badge = "★ PROMOTED" if inst["status"] == "promoted" else "○ PENDING"
            print(f"  [{status_badge}] [{inst['domain']}] {inst['trigger']} -> {inst['action']} (Conf: {inst['confidence']}, Hits: {inst['occurrences']})")

    elif args.command == "record":
        res = vault.record_instinct(
            args.project_dir, args.domain, args.trigger, args.action,
            broken_locator=args.broken, healed_locator=args.healed, confidence=args.confidence
        )
        print(f"[QA INSTINCT RECORDED] ID: {res['id']} | Hits: {res['occurrences']} | Confidence: {res['confidence']}")

    elif args.command == "query":
        results = vault.query_instincts(args.project_dir, domain=args.domain, min_confidence=args.min_confidence)
        print(json.dumps(results, indent=2, ensure_ascii=False))

    elif args.command == "promote-auto":
        promoted = vault.promote_auto(args.project_dir, threshold=args.threshold)
        print(f"[QA INSTINCT AUTO-PROMOTION] Promoted {len(promoted)} instinct(s) to permanent status:")
        for p in promoted:
            print(f"  - {p['id']}: {p['trigger']} -> {p['action']}")


if __name__ == "__main__":
    main()
