#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_db_sandbox.py — Comprehensive Unit & Boundary Tests for tools/db_sandbox.py
-------------------------------------------------------------------------------------
Verifies:
  1. Dry-run safety: Zero database writes or row mutations when dry_run=True.
  2. Granular consent enforcement: Rejection of generic boolean consent (consent=True)
     and unauthenticated shared environment variables (SYNAPSE_FORCE_RESTORE, SYNAPSE_FORCE_PURGE).
  3. Path containment: PathContainmentError raised on ../, absolute paths outside root, and symlink escapes.
  4. Nonce single-use replay defense and expiry rejection.
  5. CLI confirmation auto-grant semantics.
"""

import os
import sys
import time
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools")))
from db_sandbox import DBSandbox, main as db_sandbox_main
from pentest_scope_guard import (
    PathContainmentError,
    ConsentGrant,
    create_consent_grant,
    clear_consumed_nonces,
)


class TestDBSandboxPathContainment(unittest.TestCase):
    """Verifies that DBSandbox path containment rejects traversal, symlink escapes, and outside paths."""

    def setUp(self):
        self.sandbox_dir = tempfile.mkdtemp(prefix="db_contain_test_")
        self.outside_dir = tempfile.mkdtemp(prefix="db_contain_outside_")

    def tearDown(self):
        shutil.rmtree(self.sandbox_dir, ignore_errors=True)
        shutil.rmtree(self.outside_dir, ignore_errors=True)

    def test_contained_path_success(self):
        valid_db = os.path.join(self.sandbox_dir, "valid.db")
        sandbox = DBSandbox(db_type="sqlite", db_path=valid_db, snapshot_dir=self.sandbox_dir, sandbox_root=self.sandbox_dir)
        self.assertEqual(sandbox.db_path, os.path.realpath(valid_db))

    def test_parent_traversal_rejected(self):
        with self.assertRaises(PathContainmentError):
            DBSandbox(
                db_type="sqlite",
                db_path="../../outside.db",
                snapshot_dir=self.sandbox_dir,
                sandbox_root=self.sandbox_dir
            )

    def test_absolute_path_outside_sandbox_root_rejected(self):
        outside_db = os.path.join(self.outside_dir, "outside.db")
        with open(outside_db, "w") as f:
            f.write("")
        with self.assertRaises(PathContainmentError):
            DBSandbox(
                db_type="sqlite",
                db_path=outside_db,
                snapshot_dir=self.sandbox_dir,
                sandbox_root=self.sandbox_dir
            )

    def test_symlink_escape_rejected(self):
        outside_db = os.path.join(self.outside_dir, "secret.db")
        with open(outside_db, "w") as f:
            f.write("")
        symlink_path = os.path.join(self.sandbox_dir, "symlink_escape.db")
        try:
            os.symlink(outside_db, symlink_path)
        except OSError:
            self.skipTest("Symlinks not supported without admin privileges on Windows")

        with self.assertRaises(PathContainmentError):
            DBSandbox(
                db_type="sqlite",
                db_path=symlink_path,
                snapshot_dir=self.sandbox_dir,
                sandbox_root=self.sandbox_dir
            )


class TestDBSandboxGranularConsent(unittest.TestCase):
    """Verifies that destructive restore and purge require an explicit ConsentGrant."""

    def setUp(self):
        clear_consumed_nonces()
        self.temp_dir = tempfile.mkdtemp(prefix="db_grant_test_")
        self.db_path = os.path.join(self.temp_dir, "app.db")
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, code TEXT, name TEXT);")
        cur.execute("INSERT INTO users (code, name) VALUES ('AUTO_01', 'Test User');")
        cur.execute("INSERT INTO users (code, name) VALUES ('PROD_01', 'Real User');")
        conn.commit()
        conn.close()

        self.sandbox = DBSandbox(db_type="sqlite", db_path=self.db_path, snapshot_dir=self.temp_dir)
        self.sandbox.create_snapshot("clean_baseline")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_dry_run_zero_writes_on_restore_and_purge(self):
        # Mutate database
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO users (code, name) VALUES ('AUTO_DIRTY', 'Dirty Row');")
        conn.commit()
        conn.close()

        # Dry run restore produces preview with zero mutation
        res_rest = self.sandbox.restore_snapshot("clean_baseline", dry_run=True)
        self.assertEqual(res_rest["status"], "dry_run_preview")
        self.assertTrue(res_rest["dry_run"])
        self.assertNotIn("consent=True", res_rest["message"])
        self.assertIn("ConsentGrant", res_rest["message"])

        conn = sqlite3.connect(self.db_path)
        cnt = conn.execute("SELECT COUNT(*) FROM users;").fetchone()[0]
        conn.close()
        self.assertEqual(cnt, 3)

        # Dry run purge produces preview with zero deletion
        res_purge = self.sandbox.audit_and_purge_pollution(dry_run=True)
        self.assertEqual(res_purge["status"], "DRY_RUN")
        self.assertTrue(res_purge["dry_run"])
        self.assertEqual(res_purge["total_purged_rows"], 2)
        # In dry run with dirty rows remaining, zero_pollution_achieved MUST be False
        self.assertFalse(res_purge["zero_pollution_achieved"])

        conn = sqlite3.connect(self.db_path)
        cnt2 = conn.execute("SELECT COUNT(*) FROM users;").fetchone()[0]
        conn.close()
        self.assertEqual(cnt2, 3)

    def test_nonexistent_db_purge_returns_zero_pollution_false(self):
        """Auditing a missing or nonexistent DB returns SKIPPED with zero_pollution_achieved False."""
        missing_sb = DBSandbox(db_type="sqlite", db_path=os.path.join(self.temp_dir, "missing.db"), snapshot_dir=self.temp_dir)
        res = missing_sb.audit_and_purge_pollution(dry_run=True)
        self.assertEqual(res["status"], "SKIPPED")
        self.assertFalse(res["zero_pollution_achieved"])

    def test_restore_rejects_targetless_dict_grant(self):
        """Destructive database restore rejects targetless dictionary grants."""
        res = self.sandbox.restore_snapshot("clean_baseline", dry_run=False, consent={"action": "db:restore"})
        self.assertEqual(res["status"], "ERROR")
        self.assertIn("missing required target sandbox binding", res["message"])

    def test_purge_rejects_targetless_dict_grant(self):
        """Destructive database purge rejects targetless dictionary grants."""
        res = self.sandbox.audit_and_purge_pollution(dry_run=False, consent={"action": "db:purge"})
        self.assertEqual(res["status"], "ERROR")
        self.assertIn("missing required target sandbox binding", res["message"])

    def test_restore_rejects_generic_boolean_consent(self):
        res = self.sandbox.restore_snapshot("clean_baseline", dry_run=False, consent=True)
        self.assertEqual(res["status"], "ERROR")
        self.assertIn("explicit consent", res["message"].lower())
        self.assertFalse(res["zero_pollution_guaranteed"])

    def test_restore_rejects_unauthenticated_env_vars(self):
        with patch.dict(os.environ, {"SYNAPSE_FORCE_RESTORE": "1", "PENTEST_CONSENT_ACKNOWLEDGED": "1"}):
            res = self.sandbox.restore_snapshot("clean_baseline", dry_run=False, consent=False)
            self.assertEqual(res["status"], "ERROR")
            self.assertIn("explicit consent", res["message"].lower())

    def test_restore_rejects_expired_grant(self):
        expired = ConsentGrant(
            action="db:restore",
            target=self.db_path,
            caller_session="s1",
            nonce="nonce_exp",
            expiry=time.time() - 100.0,
            db_identity=self.db_path
        )
        res = self.sandbox.restore_snapshot("clean_baseline", dry_run=False, consent=expired)
        self.assertEqual(res["status"], "ERROR")
        self.assertIn("validation failed", res["message"].lower())

    def test_restore_rejects_replayed_nonce(self):
        replayed = create_consent_grant(
            action="db:restore",
            target=self.db_path,
            caller_session="s1",
            nonce="single_use_db_nonce",
            db_identity=self.db_path
        )
        # First execution succeeds
        res1 = self.sandbox.restore_snapshot("clean_baseline", dry_run=False, consent=replayed)
        self.assertEqual(res1["status"], "RESTORED")

        # Second execution with same nonce fails closed
        res2 = self.sandbox.restore_snapshot("clean_baseline", dry_run=False, consent=replayed)
        self.assertEqual(res2["status"], "ERROR")
        self.assertIn("validation failed", res2["message"].lower())

    def test_restore_with_valid_grant_succeeds(self):
        grant = create_consent_grant(
            action="db:restore",
            target=self.db_path,
            caller_session="s1",
            db_identity=self.db_path
        )
        res = self.sandbox.restore_snapshot("clean_baseline", dry_run=False, consent=grant)
        self.assertEqual(res["status"], "RESTORED")
        self.assertTrue(res["zero_pollution_guaranteed"])

    def test_purge_rejects_generic_boolean_consent(self):
        res = self.sandbox.audit_and_purge_pollution(dry_run=False, consent=True)
        self.assertEqual(res["status"], "ERROR")
        self.assertIn("explicit consent", res["message"].lower())

    def test_purge_rejects_unauthenticated_env_vars(self):
        with patch.dict(os.environ, {"SYNAPSE_FORCE_PURGE": "1"}):
            res = self.sandbox.audit_and_purge_pollution(dry_run=False, consent=False)
            self.assertEqual(res["status"], "ERROR")
            self.assertIn("explicit consent", res["message"].lower())

    def test_purge_with_valid_grant_purges_matching_records(self):
        grant = create_consent_grant(
            action="db:purge",
            target=self.db_path,
            caller_session="s_purge",
            db_identity=self.db_path
        )
        res = self.sandbox.audit_and_purge_pollution(dry_run=False, consent=grant)
        self.assertEqual(res["status"], "CLEAN")
        self.assertEqual(res["total_purged_rows"], 1)

        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("SELECT code FROM users;").fetchall()
        conn.close()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "PROD_01")


class TestDBSandboxCLI(unittest.TestCase):
    """Verifies that CLI commands require explicit --confirm and generate session grants."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="db_cli_test_")
        self.db_path = os.path.join(self.temp_dir, "cli_app.db")
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, code TEXT, name TEXT);")
        cur.execute("INSERT INTO users (code, name) VALUES ('AUTO_CLI_01', 'CLI Test');")
        cur.execute("INSERT INTO users (code, name) VALUES ('REAL_CLI_01', 'Real User');")
        conn.commit()
        conn.close()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cli_restore_without_confirm_is_blocked(self):
        test_args = ["db_sandbox.py", "restore", "--id", "snap", "--db-path", self.db_path]
        with patch.object(sys, "argv", test_args):
            exit_code = db_sandbox_main()
            self.assertEqual(exit_code, 1)

    def test_cli_purge_without_confirm_is_blocked(self):
        test_args = ["db_sandbox.py", "audit", "--apply", "--db-path", self.db_path]
        with patch.object(sys, "argv", test_args):
            exit_code = db_sandbox_main()
            self.assertEqual(exit_code, 1)

    def test_cli_purge_with_confirm_executes(self):
        test_args = ["db_sandbox.py", "audit", "--apply", "--confirm", "--db-path", self.db_path]
        with patch.object(sys, "argv", test_args):
            exit_code = db_sandbox_main()
            self.assertEqual(exit_code, 0)

        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("SELECT code FROM users;").fetchall()
        conn.close()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "REAL_CLI_01")


if __name__ == "__main__":
    unittest.main()
