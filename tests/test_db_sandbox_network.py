#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Unit tests for network database sandboxing and CLI dump/restore validation in tools/db_sandbox.py
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from tools.db_sandbox import DBSandbox


class TestDBSandboxNetwork(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="db_sandbox_test_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sqlite_snapshot_and_restore(self):
        db_file = os.path.join(self.temp_dir, "app.db")
        sandbox = DBSandbox(db_type="sqlite", db_path=db_file, snapshot_dir=self.temp_dir)
        snap = sandbox.create_snapshot("test_snap")
        self.assertEqual(snap["status"], "READY")
        self.assertTrue(os.path.exists(snap["snapshot_path"]))

        res = sandbox.restore_snapshot("test_snap")
        self.assertEqual(res["status"], "RESTORED")
        self.assertTrue(res["zero_pollution_guaranteed"])

    def test_network_db_missing_dump_tool_fails_closed(self):
        # Network PostgreSQL URI
        sandbox = DBSandbox(
            db_type="postgresql",
            db_path="postgresql://user:secret@postgres.internal:5432/testdb",
            snapshot_dir=self.temp_dir,
        )

        with patch("shutil.which", return_value=None):
            meta = sandbox.create_snapshot("net_snap")
            self.assertEqual(meta["status"], "ERROR")
            self.assertIn("Fake snapshot approval blocked", meta.get("error", ""))

            # Restore also fails closed
            restore_res = sandbox.restore_snapshot("net_snap")
            self.assertEqual(restore_res["status"], "ERROR")
            self.assertFalse(restore_res.get("zero_pollution_guaranteed", True))

    def test_network_db_dump_execution_hook(self):
        sandbox = DBSandbox(
            db_type="mysql",
            db_path="mysql://user:pass@mysql.cluster:3306/db",
            snapshot_dir=self.temp_dir,
        )

        with patch("shutil.which", return_value="/usr/bin/mysqldump"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                meta = sandbox.create_snapshot("mysql_snap")
                self.assertEqual(meta["status"], "READY")
                mock_run.assert_called_once()

    def test_network_db_restore_execution_hook(self):
        sandbox = DBSandbox(
            db_type="postgresql",
            db_path="postgresql://user:pass@localhost:5432/app",
            snapshot_dir=self.temp_dir,
        )

        # Create dummy snapshot file
        snap_file = os.path.join(self.temp_dir, "pg_snap.db")
        with open(snap_file, "w") as f:
            f.write("DUMMY DUMP")

        with patch("shutil.which", return_value="/usr/bin/pg_restore"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                res = sandbox.restore_snapshot("pg_snap")
                self.assertEqual(res["status"], "RESTORED")
                self.assertTrue(res["zero_pollution_guaranteed"])

    def test_file_based_nonexistent_returns_error(self):
        sandbox = DBSandbox(
            db_type="duckdb",
            db_path="/non_existent/non_existent_db_12345.duckdb",
            snapshot_dir=self.temp_dir,
        )
        meta = sandbox.create_snapshot("duck_snap")
        self.assertEqual(meta["status"], "ERROR")
        self.assertIn("not found", meta.get("error", ""))

    def test_db_type_auto_inference_from_uri(self):
        # Default db_type is sqlite, but URI should auto-infer postgres and mysql
        sb_pg = DBSandbox(db_path="postgresql://user:pass@localhost:5432/mydb", snapshot_dir=self.temp_dir)
        self.assertEqual(sb_pg.db_type, "postgres")

        sb_my = DBSandbox(db_path="mysql://user:pass@localhost:3306/mydb", snapshot_dir=self.temp_dir)
        self.assertEqual(sb_my.db_type, "mysql")

        with patch("shutil.which", return_value=None):
            meta = sb_pg.create_snapshot("pg_auto_snap")
            self.assertEqual(meta["status"], "ERROR")
            self.assertIn("pg_dump", meta.get("error", ""))

    def test_restore_failed_snapshot_fails_closed(self):
        meta_file = os.path.join(self.temp_dir, "bad_snap_meta.json")
        with open(meta_file, "w") as f:
            f.write('{"status": "ERROR", "error": "Dump tool crashed", "source_db": "postgresql://localhost/db"}')

        sb = DBSandbox(snapshot_dir=self.temp_dir)
        res = sb.restore_snapshot("bad_snap")
        self.assertEqual(res["status"], "ERROR")
        self.assertIn("corrupted/failed", res["message"])
        self.assertFalse(res["zero_pollution_guaranteed"])

    def test_rollback_exception_returns_zero_pollution_false(self):
        db_file = os.path.join(self.temp_dir, "rollback_fail.db")
        sb = DBSandbox(db_type="sqlite", db_path=db_file, snapshot_dir=self.temp_dir)
        sb.create_snapshot("rb_base")

        mock_cursor = MagicMock()
        import sqlite3
        def cursor_exec(sql, *args, **kwargs):
            if "SAVEPOINT" in sql and "ROLLBACK" in sql:
                raise sqlite3.OperationalError("Disk I/O error during rollback")
            if "INVALID_SQL" in sql:
                raise Exception("SQL execution error")
            return MagicMock()

        mock_cursor.execute.side_effect = cursor_exec
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("sqlite3.connect", return_value=mock_conn):
            res = sb.execute_with_savepoint(["INVALID_SQL;"])
            self.assertEqual(res["status"], "ERROR")
            self.assertFalse(res["zero_pollution_verified"])
            self.assertIn("rollback_error", res)
            self.assertIn("Disk I/O error", res["rollback_error"])

    def test_cli_restore_requires_confirm(self):
        import subprocess, sys
        cmd = [sys.executable, "tools/db_sandbox.py", "restore", "--id", "dummy", "--json"]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Refusing to execute destructive database restore without explicit confirmation", proc.stdout + proc.stderr)

    def test_cli_audit_default_dry_run_vs_apply(self):
        import sqlite3, subprocess, sys
        db_file = os.path.join(self.temp_dir, "audit_test.db")
        conn = sqlite3.connect(db_file)
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, code TEXT);")
        conn.execute("INSERT INTO users (code) VALUES ('AUTO_USER_99');")
        conn.commit()
        conn.close()

        # Run audit without --apply (must be dry-run, row must remain)
        cmd_dry = [sys.executable, "tools/db_sandbox.py", "audit", "--db-path", db_file, "--json"]
        proc_dry = subprocess.run(cmd_dry, capture_output=True, text=True)
        self.assertEqual(proc_dry.returncode, 0)
        import json
        dry_res = json.loads(proc_dry.stdout)
        self.assertTrue(dry_res.get("dry_run"))
        self.assertEqual(dry_res.get("total_purged_rows"), 1)

        # Check DB still has the row
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        self.assertEqual(c.fetchone()[0], 1)
        conn.close()

        # Run audit with --apply (must purge the row)
        cmd_apply = [sys.executable, "tools/db_sandbox.py", "audit", "--db-path", db_file, "--apply", "--json"]
        proc_apply = subprocess.run(cmd_apply, capture_output=True, text=True)
        self.assertEqual(proc_apply.returncode, 0)
        apply_res = json.loads(proc_apply.stdout)
        self.assertFalse(apply_res.get("dry_run"))

        # Verify DB is now empty
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        self.assertEqual(c.fetchone()[0], 0)
        conn.close()


if __name__ == "__main__":
    unittest.main()
