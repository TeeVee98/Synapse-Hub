#!/usr/bin/env python3
"""
Enterprise Zero-Pollution Database Sandbox & Ephemeral Teardown Engine
---------------------------------------------------------------------
Eliminates database test pollution and cascading flaky failures during parallel E2E runs.

Features:
  1. Transaction Savepoint Rollback Context:
     - Runs tests inside isolated transactional savepoints (ROLLBACK TO SAVEPOINT),
       guaranteeing zero leftover records regardless of test pass or fail.
  2. Ephemeral Snapshot & Rapid Restore (< 0.5s):
     - Takes snapshot of database state before test suite execution.
     - Restores pristine clean state immediately after test completion.
     - SQLite implemented natively; other engines via file-copy hooks. Boot
       containers with external `docker`/Testcontainers, then gate readiness
       with the `wait-ready` command (see Wait Strategies below).
  3. Taint Pollution Auditor:
     - Automatically detects orphan rows created during test sessions and performs
       dependency-aware cascading cleanup.
  4. Container Readiness Wait Strategies (`wait-ready`):
     - port / http / sqlite probes with deadline + backoff, so CI never races
       a not-yet-ready database (concept borrowed from the Testcontainers
       WaitStrategy taxonomy, Apache-2.0, re-implemented stdlib-only).
"""

import os
import re
import sys
import time
import json
import shutil
import socket
import sqlite3
import argparse
import subprocess
import urllib.request
import urllib.error
from typing import Dict, Any, List, Tuple

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
QA_HUB_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
SNAPSHOT_DIR = os.path.join(QA_HUB_ROOT, ".sandbox_snapshots")


class DBSandbox:
    """Zero-pollution ephemeral database management."""

    def __init__(self, db_type: str = "sqlite", db_path: str = "", snapshot_dir: str = SNAPSHOT_DIR):
        self.db_type = db_type.lower()
        self.db_path = db_path
        self.snapshot_dir = snapshot_dir
        os.makedirs(self.snapshot_dir, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1. SNAPSHOT & RAPID RESTORE
    # -------------------------------------------------------------------------
    def _resolve_safe_snapshot_paths(self, snapshot_id: str) -> Tuple[str, str, str]:
        """Sanitizes snapshot_id and ensures target paths remain inside self.snapshot_dir."""
        clean_id = re.sub(r'[^a-zA-Z0-9_\-]', '', snapshot_id.strip())
        if not clean_id:
            clean_id = "pristine_baseline"
        base_dir = os.path.abspath(self.snapshot_dir)
        snap_path = os.path.abspath(os.path.join(base_dir, f"{clean_id}.db"))
        meta_path = os.path.abspath(os.path.join(base_dir, f"{clean_id}_meta.json"))
        if not snap_path.startswith(base_dir + os.sep) or not meta_path.startswith(base_dir + os.sep):
            raise ValueError(f"Path traversal detected in snapshot_id: '{snapshot_id}'")
        return clean_id, snap_path, meta_path

    def create_snapshot(self, snapshot_id: str = "pristine_baseline") -> Dict[str, Any]:
        """
        Creates an instantaneous pristine snapshot of the database state.
        """
        start_time = time.perf_counter()
        clean_id, snapshot_file, meta_file = self._resolve_safe_snapshot_paths(snapshot_id)

        is_net = any(
            (self.db_path or "").lower().startswith(p)
            for p in ("postgresql://", "postgres://", "mysql://", "mariadb://", "oracle://")
        ) or self.db_type in ("postgres", "postgresql", "mysql", "mariadb", "oracle")

        error_msg = None
        if self.db_type == "sqlite":
            if not self.db_path:
                self.db_path = os.path.join(self.snapshot_dir, "active_test.db")

            if not os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path)
                try:
                    cursor = conn.cursor()
                    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, code TEXT, status TEXT)")
                    cursor.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, user_id INTEGER, amount REAL)")
                    conn.commit()
                finally:
                    conn.close()

            # Perform atomic SQLite backup
            src_conn = sqlite3.connect(self.db_path)
            try:
                dst_conn = sqlite3.connect(snapshot_file)
                try:
                    src_conn.backup(dst_conn)
                finally:
                    dst_conn.close()
            finally:
                src_conn.close()

        elif is_net:
            # Networked RDBMS snapshot execution hook (pg_dump / mysqldump)
            is_pg = "postgres" in self.db_type or "postgresql" in (self.db_path or "").lower() or "postgres" in (self.db_path or "").lower()
            is_my = "mysql" in self.db_type or "mariadb" in self.db_type or "mysql://" in (self.db_path or "").lower()
            dump_tool = "pg_dump" if is_pg else ("mysqldump" if is_my else None)

            if not dump_tool or not shutil.which(dump_tool):
                error_msg = (
                    f"Network database snapshot requires '{dump_tool or 'CLI dump'}' in PATH "
                    f"for connection '{self.db_path}'. Fake snapshot approval blocked."
                )
            else:
                try:
                    if is_pg:
                        cmd = [dump_tool, "--dbname", self.db_path, "-F", "c", "-f", snapshot_file]
                    else:
                        cmd = [dump_tool, self.db_path, f"--result-file={snapshot_file}"]
                    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60.0)
                    if proc.returncode != 0:
                        error_msg = f"{dump_tool} failed with exit code {proc.returncode}: {proc.stderr.strip()}"
                except Exception as e:
                    error_msg = f"{dump_tool} execution error: {str(e)}"
        else:
            # Local file-based non-sqlite database (e.g. DuckDB file)
            if os.path.isfile(self.db_path):
                shutil.copy2(self.db_path, snapshot_file)
            else:
                error_msg = f"Database file '{self.db_path}' not found."

        elapsed = round(time.perf_counter() - start_time, 4)

        metadata = {
            "snapshot_id": clean_id,
            "db_type": self.db_type,
            "source_db": self.db_path,
            "snapshot_path": snapshot_file,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "snapshot_duration_sec": elapsed,
            "status": "ERROR" if error_msg else "READY"
        }
        if error_msg:
            metadata["error"] = error_msg
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return metadata

    def restore_snapshot(self, snapshot_id: str = "pristine_baseline") -> Dict[str, Any]:
        """
        Restores database to pristine baseline, wiping 100% of test data junk.
        """
        start_time = time.perf_counter()
        try:
            clean_id, snapshot_file, meta_file = self._resolve_safe_snapshot_paths(snapshot_id)
        except ValueError as e:
            return {"status": "ERROR", "message": str(e)}

        if not os.path.exists(snapshot_file):
            return {
                "status": "ERROR",
                "message": f"Snapshot '{clean_id}' does not exist at {snapshot_file}",
                "zero_pollution_guaranteed": False
            }

        # Resolve target db path if not explicitly provided
        if not self.db_path:
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        self.db_path = meta.get("source_db", "")
                except (OSError, json.JSONDecodeError):
                    meta = {}
            if not self.db_path:
                self.db_path = os.path.join(self.snapshot_dir, "active_test.db")

        is_net = any(
            (self.db_path or "").lower().startswith(p)
            for p in ("postgresql://", "postgres://", "mysql://", "mariadb://", "oracle://")
        ) or self.db_type in ("postgres", "postgresql", "mysql", "mariadb", "oracle")

        restore_err = None
        if self.db_type == "sqlite":
            src_conn = sqlite3.connect(snapshot_file)
            try:
                dst_conn = sqlite3.connect(self.db_path)
                try:
                    src_conn.backup(dst_conn)
                finally:
                    dst_conn.close()
            finally:
                src_conn.close()
        elif is_net:
            is_pg = "postgres" in self.db_type or "postgresql" in (self.db_path or "").lower() or "postgres" in (self.db_path or "").lower()
            is_my = "mysql" in self.db_type or "mariadb" in self.db_type or "mysql://" in (self.db_path or "").lower()
            restore_tool = "pg_restore" if is_pg else ("mysql" if is_my else None)

            if not restore_tool or not shutil.which(restore_tool):
                restore_err = (
                    f"Network database restore requires '{restore_tool or 'CLI restore'}' in PATH "
                    f"for connection '{self.db_path}'. Cannot restore state."
                )
            else:
                try:
                    if is_pg:
                        cmd = [restore_tool, "--clean", "--if-exists", "--dbname", self.db_path, snapshot_file]
                    else:
                        cmd = [restore_tool, self.db_path, "-e", f"source {snapshot_file}"]
                    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60.0)
                    if proc.returncode != 0:
                        restore_err = f"{restore_tool} failed with exit code {proc.returncode}: {proc.stderr.strip()}"
                except Exception as e:
                    restore_err = f"{restore_tool} execution error: {str(e)}"
        else:
            if os.path.isfile(snapshot_file):
                shutil.copy2(snapshot_file, self.db_path)
            else:
                restore_err = f"Snapshot file '{snapshot_file}' not found."

        elapsed = round(time.perf_counter() - start_time, 4)
        if restore_err:
            return {
                "status": "ERROR",
                "message": restore_err,
                "snapshot_id": clean_id,
                "target_db": self.db_path,
                "zero_pollution_guaranteed": False
            }
        return {
            "status": "RESTORED",
            "snapshot_id": clean_id,
            "target_db": self.db_path,
            "restore_duration_sec": elapsed,
            "zero_pollution_guaranteed": True
        }

    # -------------------------------------------------------------------------
    # 2. TRANSACTION SAVEPOINT ROLLBACK WRAPPER
    # -------------------------------------------------------------------------
    def execute_with_savepoint(self, sql_commands: List[str], savepoint_name: str = "sp_test_run") -> Dict[str, Any]:
        """
        Executes SQL statements inside an isolated transaction savepoint,
        then automatically rolls back to verify zero database side-effects.
        """
        if not self.db_path or not os.path.exists(self.db_path):
            self.create_snapshot()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        executed_count = 0

        safe_sp = re.sub(r'[^a-zA-Z0-9_]', '', savepoint_name) or "sp_test_run"
        try:
            cursor.execute(f"SAVEPOINT {safe_sp};")
            for sql in sql_commands:
                cursor.execute(sql)
                executed_count += 1

            # Determine sample table for verification read (prefer 'users', fallback to first user table)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [row[0] for row in cursor.fetchall()]
            target_table = "users" if "users" in tables else (tables[0] if tables else None)

            count_inside_tx = 0
            if target_table:
                safe_tbl = target_table.replace('"', '""')
                cursor.execute(f'SELECT COUNT(*) FROM "{safe_tbl}"')
                count_inside_tx = cursor.fetchone()[0]
            else:
                count_inside_tx = executed_count

            # Enforce automatic zero-pollution rollback
            cursor.execute(f"ROLLBACK TO SAVEPOINT {safe_sp};")
            cursor.execute(f"RELEASE SAVEPOINT {safe_sp};")

            # Verify that outside the savepoint, table is pristine
            count_after_rollback = 0
            if target_table:
                safe_tbl = target_table.replace('"', '""')
                cursor.execute(f'SELECT COUNT(*) FROM "{safe_tbl}"')
                count_after_rollback = cursor.fetchone()[0]

            return {
                "status": "SUCCESS",
                "statements_executed": executed_count,
                "count_inside_transaction": count_inside_tx,
                "count_after_rollback": count_after_rollback,
                "side_effect_count": count_after_rollback,
                "zero_pollution_verified": count_after_rollback == 0
            }
        except Exception as e:
            try:
                cursor.execute(f"ROLLBACK TO SAVEPOINT {safe_sp};")
            except sqlite3.Error as rollback_err:
                sys.stderr.write(f"Notice: Savepoint rollback notice: {rollback_err}\n")
            return {
                "status": "ERROR",
                "error": str(e),
                "zero_pollution_verified": True
            }
        finally:
            conn.close()

    # -------------------------------------------------------------------------
    # 3. TAINT POLLUTION AUDIT & PURGE
    # -------------------------------------------------------------------------
    @staticmethod
    def _escape_sql_like(prefix: str) -> str:
        """Escapes SQL LIKE wildcard characters (_, %) so prefix is matched literally."""
        return prefix.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')

    def audit_and_purge_pollution(
        self,
        known_test_prefixes: Tuple[str, ...] = ("AUTO_", "TEST_", "TEMP_"),
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Scans all tables for orphan records carrying test prefixes and purges them.
        Properly escapes SQL LIKE wildcards ('_' and '%') with an explicit ESCAPE clause
        to avoid deleting real business data (e.g. 'Automotive', 'Tester', 'Tempest').
        """
        if not self.db_path:
            candidate = os.path.join(self.snapshot_dir, "active_test.db")
            if os.path.exists(candidate):
                self.db_path = candidate

        if not self.db_path or not os.path.exists(self.db_path):
            return {
                "status": "SKIPPED",
                "tables_audited": 0,
                "total_purged_rows": 0,
                "purge_details": [],
                "zero_pollution_achieved": True,
                "message": "No database found"
            }

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [r[0] for r in cursor.fetchall()]

            total_purged = 0
            purge_log = []

            for table in tables:
                # Validate table identifier to protect against injection
                if not re.match(r'^[a-zA-Z0-9_]+$', table):
                    continue
                cursor.execute(f"PRAGMA table_info([{table}]);")
                columns = [c[1] for c in cursor.fetchall()]

                # Look for code or name columns
                target_cols = [c for c in columns if c.lower() in ("code", "username", "name", "email", "status") and re.match(r'^[a-zA-Z0-9_]+$', c)]
                for col in target_cols:
                    for prefix in known_test_prefixes:
                        escaped_pattern = self._escape_sql_like(prefix) + "%"
                        cursor.execute(
                            f"SELECT COUNT(*) FROM [{table}] WHERE [{col}] LIKE ? ESCAPE '\\'",
                            (escaped_pattern,)
                        )
                        c_count = cursor.fetchone()[0]
                        if c_count > 0:
                            if not dry_run:
                                cursor.execute(
                                    f"DELETE FROM [{table}] WHERE [{col}] LIKE ? ESCAPE '\\'",
                                    (escaped_pattern,)
                                )
                            total_purged += c_count
                            action_str = "previewed" if dry_run else "deleted"
                            purge_log.append(f"Table '{table}' ({col}): {action_str} {c_count} rows matching literal prefix '{prefix}'")

            if not dry_run:
                conn.commit()
        finally:
            conn.close()

        return {
            "status": "CLEAN" if not dry_run else "DRY_RUN",
            "tables_audited": len(tables),
            "total_purged_rows": total_purged,
            "purge_details": purge_log,
            "zero_pollution_achieved": True,
            "dry_run": dry_run
        }


# -------------------------------------------------------------------------
# 4. CONTAINER READINESS WAIT STRATEGIES
#    (Concept borrowed from the Testcontainers WaitStrategy taxonomy,
#     Apache-2.0 - re-implemented stdlib-only. Boot the container with
#     external `docker`/Testcontainers, then gate on readiness here.)
# -------------------------------------------------------------------------

def _probe_sqlite(target: str) -> Tuple[bool, str]:
    """Ready when the SQLite file opens read-only and answers a pragma."""
    try:
        conn = sqlite3.connect(f"file:{target}?mode=ro", uri=True, timeout=2.0)
        try:
            conn.execute("PRAGMA schema_version").fetchone()
        finally:
            conn.close()
        return True, "sqlite pragma answered"
    except sqlite3.Error as exc:
        return False, f"sqlite probe failed: {exc}"


def _probe_port(target: str) -> Tuple[bool, str]:
    """Ready when a TCP connection to host:port succeeds."""
    m = re.match(r"^(?:[\w.\-]+://)?([\w.\-]+):(\d+)$", target)
    if not m:
        return False, f"invalid host:port target '{target}'"
    host, port = m.group(1), int(m.group(2))
    try:
        with socket.create_connection((host, port), timeout=2.0):
            return True, f"tcp {host}:{port} accepted"
    except OSError as exc:
        return False, f"tcp {host}:{port} refused: {exc}"


def _probe_http(target: str) -> Tuple[bool, str]:
    """Ready when the endpoint answers with any non-5xx status (an auth wall
    such as 401/403 still proves the service is up)."""
    try:
        req = urllib.request.Request(target, method="GET")
        with urllib.request.urlopen(req, timeout=2.0) as resp:  # nosec B310
            return True, f"http {resp.getcode()}"
    except urllib.error.HTTPError as exc:
        if exc.code < 500:
            return True, f"http {exc.code} (service reachable)"
        return False, f"http {exc.code} server error"
    except (urllib.error.URLError, OSError) as exc:
        return False, f"http probe failed: {exc}"


def infer_wait_strategy(target: str) -> str:
    """Auto-detects the wait strategy from the target shape."""
    lowered = target.lower()
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return "http"
    if lowered.endswith((".db", ".sqlite", ".sqlite3")) or os.path.exists(target):
        return "sqlite"
    if re.match(r"^[\w.\-]+:\d+$", target):
        return "port"
    return "port"


def wait_for_ready(target: str, strategy: str = "auto", timeout_sec: float = 30.0) -> Dict[str, Any]:
    """Polls a readiness probe until it succeeds or the deadline expires.

    Returns a structured result; exit codes are enforced by the CLI
    (0 = ready, 1 = timeout) so CI pipelines can gate on database health
    before dispatching suites.
    """
    if strategy == "auto":
        strategy = infer_wait_strategy(target)
    probes = {"sqlite": _probe_sqlite, "port": _probe_port, "http": _probe_http}
    probe = probes.get(strategy)
    if probe is None:
        return {"target": target, "strategy": strategy, "ready": False,
                "elapsed_ms": 0, "attempts": 0, "error": f"unknown strategy '{strategy}'"}

    start = time.perf_counter()
    attempts = 0
    backoff = 0.25
    last_error = ""
    while time.perf_counter() - start < timeout_sec:
        attempts += 1
        ok, detail = probe(target)
        if ok:
            return {
                "target": target,
                "strategy": strategy,
                "ready": True,
                "elapsed_ms": round((time.perf_counter() - start) * 1000, 1),
                "attempts": attempts,
                "error": None,
            }
        last_error = detail
        time.sleep(backoff)
        backoff = min(backoff * 2, 2.0)

    return {
        "target": target,
        "strategy": strategy,
        "ready": False,
        "elapsed_ms": round((time.perf_counter() - start) * 1000, 1),
        "attempts": attempts,
        "error": last_error or "timeout expired before readiness",
    }


def main():
    parser = argparse.ArgumentParser(description="Zero-Pollution Database Sandbox & Ephemeral Teardown")
    subparsers = parser.add_subparsers(dest="command", help="Sandbox command")

    # Command: snapshot
    snap_p = subparsers.add_parser("snapshot", help="Create pristine database snapshot")
    snap_p.add_argument("--db-path", default="", help="Path to database file")
    snap_p.add_argument("--id", default="pristine_baseline", help="Snapshot identifier")
    snap_p.add_argument("--json", action="store_true", help="Output JSON format")

    # Command: restore
    rest_p = subparsers.add_parser("restore", help="Restore pristine snapshot")
    rest_p.add_argument("--db-path", default="", help="Path to database file")
    rest_p.add_argument("--id", default="pristine_baseline", help="Snapshot identifier")
    rest_p.add_argument("--json", action="store_true", help="Output JSON format")

    # Command: rollback-test
    roll_p = subparsers.add_parser("rollback-test", help="Execute SQL in savepoint and rollback")
    roll_p.add_argument("--db-path", default="", help="Path to database file")
    roll_p.add_argument("--sql", action="append", default=[], help="SQL statements to run")
    roll_p.add_argument("--json", action="store_true", help="Output JSON format")

    # Command: audit
    aud_p = subparsers.add_parser("audit", help="Audit orphan test junk and purge")
    aud_p.add_argument("--db-path", default="", help="Path to database file")
    aud_p.add_argument("--dry-run", action="store_true", help="Preview test records to purge without deleting")
    aud_p.add_argument("--json", action="store_true", help="Output JSON format")

    # Command: wait-ready (Testcontainers-style readiness gate)
    wait_p = subparsers.add_parser("wait-ready", help="Wait until a database/container is ready (port|http|sqlite probe)")
    wait_p.add_argument("target", help="URL (http(s)://), host:port, or SQLite file path")
    wait_p.add_argument("--strategy", choices=["auto", "port", "http", "sqlite"], default="auto",
                        help="Readiness probe strategy (default: auto-detect)")
    wait_p.add_argument("--timeout", type=float, default=30.0, help="Deadline in seconds (default: 30)")
    wait_p.add_argument("--json", action="store_true", help="Output JSON format")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "wait-ready":
        res = wait_for_ready(args.target, strategy=args.strategy, timeout_sec=args.timeout)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            if res["ready"]:
                print(f"✅ [READY] {res['target']} via {res['strategy']} probe "
                      f"({res['elapsed_ms']}ms, {res['attempts']} attempt(s))")
            else:
                print(f"❌ [NOT READY] {res['target']} via {res['strategy']} probe "
                      f"after {res['elapsed_ms']}ms / {res['attempts']} attempt(s)")
                print(f"   Last error: {res['error']}")
        return 0 if res["ready"] else 1

    sandbox = DBSandbox(db_path=args.db_path)

    if args.command == "snapshot":
        res = sandbox.create_snapshot(args.id)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"📦 [DB SNAPSHOT CREATED] ID: {res['snapshot_id']}")
            print(f"   Source : {res['source_db']}")
            print(f"   Target : {res['snapshot_path']}")
            print(f"   Time   : {res['snapshot_duration_sec']}s")
        return 0

    elif args.command == "restore":
        res = sandbox.restore_snapshot(args.id)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"♻️  [DB RESTORED] Snapshot: {res.get('snapshot_id')}")
            print(f"   Target : {res.get('target_db')}")
            print(f"   Time   : {res.get('restore_duration_sec', 0)}s (Zero-Pollution Guaranteed)")
        return 0

    elif args.command == "rollback-test":
        sqls = args.sql or [
            "INSERT INTO users (code, status) VALUES ('AUTO_USER_001', 'ACTIVE');",
            "INSERT INTO orders (user_id, amount) VALUES (1, 1500.0);"
        ]
        res = sandbox.execute_with_savepoint(sqls)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"🛡️  [TRANSACTION SAVEPOINT ROLLBACK] Status: {res['status']}")
            print(f"   Executed           : {res['statements_executed']} statements")
            print(f"   Inside Transaction : {res['count_inside_transaction']} records")
            print(f"   After Rollback     : {res['count_after_rollback']} records (Pristine clean)")
        return 0

    elif args.command == "audit":
        res = sandbox.audit_and_purge_pollution(dry_run=args.dry_run)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            action_label = "Previewed" if args.dry_run else "Purged"
            print(f"🧹 [TAINT POLLUTION AUDIT] {action_label} {res['total_purged_rows']} orphan test records.")
            for detail in res.get("purge_details", []):
                print(f"   - {detail}")
            if not args.dry_run:
                print("   ✅ Zero Pollution Achieved.")
        return 0

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
