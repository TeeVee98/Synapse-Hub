# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""Unit tests for tools/test_memory_os.py (Hierarchical QA Test Memory OS)."""

import os
import sys
import tempfile
import shutil
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

from test_memory_os import TestMemoryOS


@pytest.fixture
def temp_db():
    tmp_dir = tempfile.mkdtemp()
    db_file = os.path.join(tmp_dir, "test_memory.db")
    yield db_file
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_core_memory_crud(temp_db):
    mem = TestMemoryOS(db_path=temp_db)
    res = mem.update_core("auth_state", {"token_expiry": "2026-12-31", "role": "ADMIN"})
    assert res["status"] == "PASS"

    block = mem.get_core("auth_state")
    assert block is not None
    assert block["data"]["role"] == "ADMIN"
    assert block["data"]["token_expiry"] == "2026-12-31"

    blocks = mem.list_core()
    assert len(blocks) == 1
    assert blocks[0]["block_key"] == "auth_state"


def test_recall_memory_log(temp_db):
    mem = TestMemoryOS(db_path=temp_db)
    mem.recall_insert("SESSION_001", "ACTION_NAVIGATE", "live-explorer", {"url": "/checkout"})
    mem.recall_insert("SESSION_001", "ACTION_CLICK", "live-explorer", {"target": "#submit-btn"})

    events = mem.recall_log("SESSION_001")
    assert len(events) == 2
    assert events[0]["event_type"] == "ACTION_NAVIGATE"
    assert events[1]["payload"]["target"] == "#submit-btn"


def test_archival_memory_semantic_search_and_version_scoping(temp_db):
    mem = TestMemoryOS(db_path=temp_db)

    # Insert v2.1 mutation
    id1 = mem.archival_insert(
        key="LOCATOR_MUTATION",
        payload={"page": "CheckoutPage", "old": "#submit", "new": "button[data-testid=submit-btn]"},
        aut_version="v2.1",
        tags="checkout,submit,button"
    )
    assert id1.startswith("mem_arch_")

    # Insert v2.2 mutation
    id2 = mem.archival_insert(
        key="LOCATOR_MUTATION",
        payload={"page": "CheckoutPage", "old": "button[data-testid=submit-btn]", "new": "button.aria-submit"},
        aut_version="v2.2",
        tags="checkout,submit,aria"
    )
    assert id2.startswith("mem_arch_")

    # Search with aut_version v2.1: must NOT return v2.2 mutation (eliminates memory rot)
    search_v21 = mem.archival_search("checkout submit button", aut_version="v2.1", top_k=5)
    assert search_v21["status"] == "PASS"
    assert search_v21["matches_found"] == 1
    assert search_v21["results"][0]["aut_version"] == "v2.1"
    assert search_v21["results"][0]["payload"]["new"] == "button[data-testid=submit-btn]"

    # Search without version filter: returns both
    search_all = mem.archival_search("checkout submit button", top_k=5)
    assert search_all["matches_found"] == 2


def test_gc_and_secret_scrubbing(temp_db):
    mem = TestMemoryOS(db_path=temp_db)

    # Insert secret in core memory
    mem.update_core("auth_leak", {"api_key": "secret_key_123456789", "token": "Bearer abcdef1234567890"})

    # Insert secret in archival memory
    mem.archival_insert("LEAKED_CRED", {"password": "super_secret_password_123"}, aut_version="v1.0")

    gc_res = mem.gc(scrub_secrets=True, max_age_days=0)
    assert gc_res["status"] == "PASS"
    assert gc_res["secrets_scrubbed"] >= 2
    assert gc_res["size_status"] == "PASS"

    # Verify secret is masked
    cleansed = mem.get_core("auth_leak")
    assert "[MASKED_SECRET]" in str(cleansed["data"])
    assert "secret_key_123456789" not in str(cleansed["data"])
