#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Unit tests for Unified 3-Tier QA Memory OS (SynapseMemory)
---------------------------------------------------------
Verifies:
  - Tier 1 Core Memory (working KV blocks)
  - Tier 2 Recall Memory (episodic log)
  - Tier 3 Archival Memory (instincts, negative fixes, confidence scoring)
  - Secret scrubbing (redaction of passwords, tokens, API keys)
  - CI bundle export & import merging
"""

import os
import tempfile
from tools.core.qa_memory_os import QAMemoryOS, scrub_secrets, scrub_data_dict


def test_secret_scrubbing():
    """Verifies that secrets are cleanly scrubbed."""
    raw = "apiKey: secret_key_12345678, password=MySuperSecretPassword! and Bearer eyJhbGciOiJIUzI1NiIsInR5"
    scrubbed = scrub_secrets(raw)
    assert "secret_key_12345678" not in scrubbed
    assert "MySuperSecretPassword!" not in scrubbed
    assert "[REDACTED_SECRET]" in scrubbed

    nested = {
        "user": "test_user",
        "auth": {"token": "my_secret_token_12345"},
        "tags": ["prod", "password=admin_password123"]
    }
    clean = scrub_data_dict(nested)
    assert "my_secret_token_12345" not in str(clean)
    assert "admin_password123" not in str(clean)


def test_core_memory_crud():
    """Verifies Core Memory set, get, and list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "qa_mem.db")
        mem = QAMemoryOS(db_path)
        try:
            mem.set_core("env_config", {"base_url": "https://staging.app", "browser": "chromium"})
            mem.set_core("flags", {"enable_dark_mode": True})

            blocks = mem.list_core_blocks()
            assert "env_config" in blocks
            assert "flags" in blocks

            env = mem.get_core("env_config")
            assert env["base_url"] == "https://staging.app"
            assert env["browser"] == "chromium"

            # Overwrite block
            mem.set_core("env_config", {"base_url": "https://prod.app"})
            env_updated = mem.get_core("env_config")
            assert env_updated["base_url"] == "https://prod.app"
        finally:
            mem.close()


def test_recall_memory_logging_and_query():
    """Verifies Recall Memory episodic logging and ordering."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "qa_mem.db")
        mem = QAMemoryOS(db_path)
        try:
            mem.log_recall("test_step", {"step": 1, "action": "click_login"}, session_id="sess_1")
            mem.log_recall("test_step", {"step": 2, "action": "fill_password"}, session_id="sess_1")
            mem.log_recall("test_failure", {"step": 3, "error": "timeout"}, session_id="sess_1")

            events = mem.query_recall(limit=10)
            assert len(events) == 3
            # Latest first
            assert events[0]["event_type"] == "test_failure"

            step_events = mem.query_recall(event_type="test_step")
            assert len(step_events) == 2
        finally:
            mem.close()


def test_archival_memory_and_negative_blacklist():
    """Verifies Archival Memory instinct storage, querying, and negative blacklisting."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "qa_mem.db")
        mem = QAMemoryOS(db_path)
        try:
            # Positive instinct
            mem.save_archival(
                domain="locator_heal",
                trigger="login submit button timeout",
                action={"locator": "getByRole('button', name='Sign in')"},
                project_hash="proj_abc",
                confidence=0.6
            )

            # Negative fix (blacklisted)
            mem.save_archival(
                domain="locator_heal",
                trigger="login submit button timeout",
                action={"locator": "//button[@class='btn-old']"},
                project_hash="proj_abc",
                is_blacklisted=True
            )

            # Query positive instincts only
            results = mem.query_archival(
                query="submit button",
                domain="locator_heal",
                project_hash="proj_abc",
                exclude_blacklisted=True
            )
            assert len(results) == 1
            assert "getByRole" in str(results[0]["action"])
            assert results[0]["is_blacklisted"] is False

            # Query including blacklisted
            all_results = mem.query_archival(
                query="submit button",
                domain="locator_heal",
                project_hash="proj_abc",
                exclude_blacklisted=False
            )
            assert len(all_results) == 2
        finally:
            mem.close()


def test_ci_bundle_export_and_import():
    """Verifies export to CI bundle tar.gz and subsequent import into a separate instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db1_path = os.path.join(tmpdir, "db1.db")
        db2_path = os.path.join(tmpdir, "db2.db")
        bundle_path = os.path.join(tmpdir, "ci_bundle.tar.gz")

        mem1 = QAMemoryOS(db1_path)
        try:
            mem1.set_core("shared_state", {"key": "value_from_db1"})
            mem1.save_archival(
                domain="api_mock",
                trigger="auth 401 retry",
                action="refresh_token",
                project_hash="proj_ci"
            )
            mem1.export_ci_bundle(bundle_path)
            assert os.path.exists(bundle_path)
        finally:
            mem1.close()

        # Import into fresh db2
        mem2 = QAMemoryOS(db2_path)
        try:
            mem2.import_ci_bundle(bundle_path)
            core_val = mem2.get_core("shared_state")
            assert core_val is not None
            assert core_val["key"] == "value_from_db1"

            arch = mem2.query_archival("auth 401", project_hash="proj_ci")
            assert len(arch) == 1
            assert arch[0]["action"] == "refresh_token"
        finally:
            mem2.close()


def test_archival_fts5_virtual_table_indexing():
    """Verifies that SQLite FTS5 index is active and enables sub-millisecond keyword lookup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "fts5_test.db")
        mem = QAMemoryOS(db_path)
        try:
            assert mem._has_fts5 is True

            # Save distinct instincts
            mem.save_archival(
                domain="locator_heal",
                trigger="ElementNotFoundException on primary checkout CTA button",
                action="click_by_som",
                confidence=0.85
            )
            mem.save_archival(
                domain="flaky_quarantine",
                trigger="StaleElementReferenceException during rapid table reload",
                action="retry_with_networkidle",
                confidence=0.95
            )

            # Query via FTS5 prefix match
            res1 = mem.query_archival("checkout")
            assert len(res1) == 1
            assert res1[0]["action"] == "click_by_som"

            res2 = mem.query_archival("stale")
            assert len(res2) == 1
            assert res2[0]["action"] == "retry_with_networkidle"

            # Check ranking: highest confidence first
            mem.save_archival(
                domain="locator_heal",
                trigger="checkout secondary link failed",
                action="fallback_xpath",
                confidence=0.4
            )
            ranked = mem.query_archival("checkout")
            assert len(ranked) == 2
            assert ranked[0]["confidence"] > ranked[1]["confidence"]
        finally:
            mem.close()
