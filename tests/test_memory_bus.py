# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_memory_bus.py — Comprehensive Unit Tests for Unified QA Memory Bus
-----------------------------------------------------------------------------
Verifies:
  1. Initialization & Pragmas (WAL mode, foreign keys).
  2. Memory Blocks partition (CRUD, scope isolation, JSON serialization).
  3. Actor Mailbox partition (asynchronous message queuing, peek, read receipts).
  4. Skill Vault partition (Page Class cataloging, search, verification state).
  5. Healing Cache partition (error signatures, hit counting, patch lookup).
  6. Event Stream partition (cryptographic SHA-256 hash chaining, tamper detection).
  7. Checkpoints & Reversible Stream Rollback.
  8. ACID Transactions (commit on success, automatic rollback on exception).
  9. Nested Savepoints.
  10. Synchronous Test Abort & Mailbox Cancellation.
"""

import os
import sys
import tempfile
import shutil
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from tools.core.memory_bus import UnifiedMemoryBus, GENESIS_HASH


@pytest.fixture
def temp_db():
    tmp_dir = tempfile.mkdtemp()
    db_file = os.path.join(tmp_dir, "test_memory.db")
    bus = UnifiedMemoryBus(db_path=db_file)
    yield bus
    bus.close()
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def mem_bus():
    bus = UnifiedMemoryBus(db_path=":memory:")
    yield bus
    bus.close()


# ---------------------------------------------------------------------------
# 1. Initialization & Schema Integrity
# ---------------------------------------------------------------------------

def test_memory_bus_initialization_and_stats(temp_db):
    stats = temp_db.get_stats()
    assert stats["memory_blocks"] == 0
    assert stats["actor_mailbox"] == 0
    assert stats["skill_vault"] == 0
    assert stats["healing_cache"] == 0
    assert stats["event_stream"] == 0


def test_memory_bus_wal_mode_on_disk(temp_db):
    cur = temp_db._conn.cursor()
    cur.execute("PRAGMA journal_mode;")
    mode = cur.fetchone()[0]
    cur.close()
    assert mode.lower() == "wal"


# ---------------------------------------------------------------------------
# 2. Blocks Partition
# ---------------------------------------------------------------------------

def test_blocks_set_get_and_update(mem_bus):
    # Insert new block
    res = mem_bus.set_block(
        label="auth_session",
        content={"token": "abc123xyz", "expires_in": 3600},
        scope="auth",
        tags="jwt,login"
    )
    assert res["label"] == "auth_session"
    assert res["scope"] == "auth"

    # Get block
    block = mem_bus.get_block("auth_session", scope="auth")
    assert block is not None
    assert block["content"]["token"] == "abc123xyz"
    assert block["tags"] == "jwt,login"

    # Update existing block
    mem_bus.set_block(
        label="auth_session",
        content={"token": "refreshed_token", "expires_in": 7200},
        scope="auth",
        tags="jwt,refreshed"
    )
    updated = mem_bus.get_block("auth_session", scope="auth")
    assert updated["content"]["token"] == "refreshed_token"
    assert updated["tags"] == "jwt,refreshed"


def test_blocks_scope_isolation_and_delete(mem_bus):
    mem_bus.set_block("config", "scope_a_val", scope="project_a")
    mem_bus.set_block("config", "scope_b_val", scope="project_b")

    a = mem_bus.get_block("config", scope="project_a")
    b = mem_bus.get_block("config", scope="project_b")
    assert a["content"] == "scope_a_val"
    assert b["content"] == "scope_b_val"

    # List by scope
    list_a = mem_bus.list_blocks(scope="project_a")
    assert len(list_a) == 1
    assert list_a[0]["label"] == "config"

    # Delete
    deleted = mem_bus.delete_block("config", scope="project_a")
    assert deleted is True
    assert mem_bus.get_block("config", scope="project_a") is None
    assert mem_bus.get_block("config", scope="project_b") is not None


# ---------------------------------------------------------------------------
# 3. Actor Mailbox Partition
# ---------------------------------------------------------------------------

def test_actor_mailbox_flow(mem_bus):
    # live-explorer sends discovery data to pom-crafter
    msg_id = mem_bus.send_message(
        sender="live-explorer",
        recipient="pom-crafter",
        stage="DISCOVERY",
        payload={"url": "https://example.com/login", "inputs": ["#user", "#pass"]}
    )
    assert msg_id.startswith("msg_")

    # Peek message does not change status
    peeked = mem_bus.peek_messages(recipient="pom-crafter")
    assert len(peeked) == 1
    assert peeked[0]["status"] == "PENDING"
    assert peeked[0]["payload"]["url"] == "https://example.com/login"

    # Receive message marks as PROCESSED
    received = mem_bus.receive_messages(recipient="pom-crafter", mark_read=True)
    assert len(received) == 1
    assert received[0]["message_id"] == msg_id

    # Subsequent receive has no pending messages
    none_pending = mem_bus.receive_messages(recipient="pom-crafter")
    assert len(none_pending) == 0


def test_actor_mailbox_filtering_and_custom_status(mem_bus):
    mem_bus.send_message("orchestrator", "test-runner", "HEADLESS_EXEC", {"run": 1})
    mem_bus.send_message("orchestrator", "failure-analyst", "AUTOPSY_HEAL", {"err": "timeout"})

    runner_msgs = mem_bus.receive_messages("test-runner", stage="HEADLESS_EXEC", mark_read=False)
    assert len(runner_msgs) == 1

    msg_id = runner_msgs[0]["message_id"]
    mem_bus.mark_message_status(msg_id, "ARCHIVED")

    archived = mem_bus.receive_messages("test-runner", status="ARCHIVED", mark_read=False)
    assert len(archived) == 1
    assert archived[0]["status"] == "ARCHIVED"


# ---------------------------------------------------------------------------
# 4. Skill Vault Partition
# ---------------------------------------------------------------------------

def test_skill_vault_store_and_search(mem_bus):
    sk_id = mem_bus.store_skill(
        name="LoginPage.submitCredentials",
        framework="Playwright_TS",
        content="async submitCredentials(u: string, p: string) { ... }",
        signature="submitCredentials(username: string, password: string): Promise<void>",
        metadata={"role": "auth", "tier": 1},
        verified=True
    )
    assert sk_id.startswith("sk_")

    # Exact lookup
    skill = mem_bus.get_skill("LoginPage.submitCredentials", "Playwright_TS")
    assert skill is not None
    assert skill["verified"] is True
    assert skill["metadata"]["role"] == "auth"

    # Search by keyword
    results = mem_bus.find_skills(query="submitCredentials", framework="Playwright_TS")
    assert len(results) == 1

    # Delete
    deleted = mem_bus.delete_skill(skill["skill_id"])
    assert deleted is True
    assert mem_bus.get_skill("LoginPage.submitCredentials", "Playwright_TS") is None


# ---------------------------------------------------------------------------
# 5. Healing Cache Partition
# ---------------------------------------------------------------------------

def test_healing_cache_record_and_hit_counting(mem_bus):
    sig = "ERR_ELEMENT_CLICK_INTERCEPTED_#checkout-btn"
    cache_id = mem_bus.record_healing(
        error_signature=sig,
        failed_code="page.click('#checkout-btn');",
        patch_code="await page.waitForSelector('.overlay', { state: 'detached' }); await page.click('#checkout-btn');",
        rca_verdict="Overlay backdrop blocking pointer events",
        verified=False
    )
    assert cache_id.startswith("heal_")

    item = mem_bus.lookup_healing(sig)
    assert item is not None
    assert item["hit_count"] == 1
    assert item["verified"] is False

    # Second hit increments count
    mem_bus.record_healing(
        error_signature=sig,
        failed_code="page.click('#checkout-btn');",
        patch_code="await page.locator('#checkout-btn').click({ force: true });",
        rca_verdict="Forced click fallback"
    )
    hit_item = mem_bus.lookup_healing(sig)
    assert hit_item["hit_count"] == 2
    assert "force" in hit_item["patch_code"]

    # Verify healing
    mem_bus.verify_healing(hit_item["cache_id"], verified=True)
    verified_item = mem_bus.lookup_healing(sig, verified_only=True)
    assert verified_item is not None
    assert verified_item["verified"] is True


# ---------------------------------------------------------------------------
# 6. Event Stream Partition & Hash Chaining
# ---------------------------------------------------------------------------

def test_event_stream_hash_chain_and_integrity(mem_bus):
    sess = "SESS_TEST_STREAM"

    ev1 = mem_bus.record_event(sess, "ACTION_NAVIGATE", "live-explorer", "DISCOVERY", {"url": "/login"})
    assert ev1["sequence"] == 1
    assert ev1["prev_hash"] == GENESIS_HASH

    ev2 = mem_bus.record_event(sess, "ACTION_CLICK", "live-explorer", "DISCOVERY", {"target": "#submit"})
    assert ev2["sequence"] == 2
    assert ev2["prev_hash"] == ev1["event_hash"]

    ev3 = mem_bus.record_event(sess, "ASSERTION_PASSED", "quality-gatekeeper", "ACCEPTANCE_DOD", {"gates": 10})
    assert ev3["sequence"] == 3
    assert ev3["prev_hash"] == ev2["event_hash"]

    valid, err = mem_bus.verify_stream_integrity(sess)
    assert valid is True
    assert err is None


def test_event_stream_detects_tampering(mem_bus):
    sess = "SESS_TAMPER"
    mem_bus.record_event(sess, "EVT_1", "actor", "DISCOVERY", {"v": 1})
    mem_bus.record_event(sess, "EVT_2", "actor", "DISCOVERY", {"v": 2})

    # Tamper with event 1 in database
    mem_bus._conn.execute(
        "UPDATE event_stream SET payload = '{\"malicious\": true}' WHERE session_id = ? AND sequence = 1;",
        (sess,)
    )

    valid, err = mem_bus.verify_stream_integrity(sess)
    assert valid is False
    assert "tampered" in err.lower() or "mismatch" in err.lower()


# ---------------------------------------------------------------------------
# 7. Checkpoints & Reversible Rollback
# ---------------------------------------------------------------------------

def test_event_stream_checkpoint_and_rollback(mem_bus):
    sess = "SESS_REVERSIBLE"

    mem_bus.record_event(sess, "INIT", "system", "DISCOVERY", {"status": "ok"})
    mem_bus.create_checkpoint(sess, "system", "DISCOVERY", "CP_BEFORE_DANGEROUS_ACTION")

    # Flaky or destructive operations occur
    mem_bus.record_event(sess, "DELETE_DATA", "test-runner", "HEADLESS_EXEC", {"dropped": True})
    mem_bus.record_event(sess, "FAIL_EXCEPTION", "test-runner", "HEADLESS_EXEC", {"error": "crash"})

    events_before = mem_bus.get_events(sess)
    assert len(events_before) == 4

    # Roll back to checkpoint
    rb = mem_bus.rollback_to_checkpoint(sess, "CP_BEFORE_DANGEROUS_ACTION")
    assert rb["event_type"] == "ROLLBACK_EXECUTED"

    events_after = mem_bus.get_events(sess)
    # Checkpoint preserved, delete & fail pruned, rollback event appended
    types = [e["event_type"] for e in events_after]
    assert "DELETE_DATA" not in types
    assert "FAIL_EXCEPTION" not in types
    assert "ROLLBACK_EXECUTED" in types


# ---------------------------------------------------------------------------
# 8. ACID Transactions & Rollback
# ---------------------------------------------------------------------------

def test_transaction_commit_on_success(mem_bus):
    with mem_bus.transaction():
        mem_bus.set_block("txn_key", "txn_val")
        mem_bus.send_message("a", "b", "STAGE", {"data": 123})

    # Both committed
    assert mem_bus.get_block("txn_key")["content"] == "txn_val"
    assert len(mem_bus.peek_messages("b")) == 1


def test_transaction_rollback_on_exception(mem_bus):
    with pytest.raises(RuntimeError, match="Intentional test abort"):
        with mem_bus.transaction():
            mem_bus.set_block("rollback_key", "doomed_val")
            mem_bus.send_message("a", "b", "STAGE", {"doomed": True})
            raise RuntimeError("Intentional test abort within transaction")

    # Uncommitted mutations rolled back cleanly
    assert mem_bus.get_block("rollback_key") is None
    assert len(mem_bus.peek_messages("b")) == 0


# ---------------------------------------------------------------------------
# 9. Nested Savepoints
# ---------------------------------------------------------------------------

def test_nested_savepoint_rollback(mem_bus):
    with mem_bus.transaction():
        mem_bus.set_block("outer_key", "outer_val")

        with pytest.raises(ValueError, match="Nested step failed"):
            with mem_bus.savepoint("nested_trial"):
                mem_bus.set_block("nested_key", "nested_val")
                raise ValueError("Nested step failed")

        # Outer key preserved
        mem_bus.set_block("after_nested", "survived")

    assert mem_bus.get_block("outer_key")["content"] == "outer_val"
    assert mem_bus.get_block("nested_key") is None
    assert mem_bus.get_block("after_nested")["content"] == "survived"


# ---------------------------------------------------------------------------
# 10. Synchronous Test Abort
# ---------------------------------------------------------------------------

def test_abort_test_cleans_up_and_records_audit(mem_bus):
    sess = "SESS_ABORT"
    # Pre-existing pending message in mailbox
    mem_bus.send_message("live-explorer", "pom-crafter", "DISCOVERY", {"msg": "pending"})

    # Uncommitted transaction during test execution
    mem_bus.begin()
    mem_bus.set_block("uncommitted_block", "temporary")

    # Abort test triggered
    mem_bus.abort_test(session_id=sess, reason="Timeout waiting for DOM selector")

    # Uncommitted block rolled back
    assert mem_bus.get_block("uncommitted_block") is None

    # Pending mailbox messages updated to ABORTED
    aborted_msgs = mem_bus.receive_messages("pom-crafter", status="ABORTED", mark_read=False)
    assert len(aborted_msgs) == 1
    assert aborted_msgs[0]["status"] == "ABORTED"

    # Audit event logged
    events = mem_bus.get_events(sess)
    assert len(events) == 1
    assert events[0]["event_type"] == "TEST_ABORTED"
    assert "Timeout" in events[0]["payload"]["reason"]


# ---------------------------------------------------------------------------
# 11. Concurrency, String Payloads & Session Scoping Edge Cases
# ---------------------------------------------------------------------------

def test_event_stream_compact_and_arbitrary_string_payloads(mem_bus):
    """Verifies that compact JSON strings, raw strings, and primitives maintain hash integrity."""
    import json
    sess = "SESS_STRING_PAYLOADS"
    compact_json = json.dumps({"key": 1, "arr": [1, 2, 3]}, separators=(",", ":"))
    mem_bus.record_event(sess, "EVT_COMPACT", "actor", "STAGE", compact_json)
    mem_bus.record_event(sess, "EVT_RAW_STR", "actor", "STAGE", "Plain text message without JSON")
    mem_bus.record_event(sess, "EVT_DICT", "actor", "STAGE", {"nested": {"a": True, "b": None}})
    mem_bus.record_event(sess, "EVT_INT", "actor", "STAGE", 42)

    valid, err = mem_bus.verify_stream_integrity(sess)
    assert valid is True, f"Integrity check failed: {err}"
    assert err is None


def test_event_stream_multi_threaded_barrier_concurrency():
    """Verifies that multiple concurrent processes/threads recording events with barrier serialize without collisions."""
    import threading
    import tempfile
    import shutil

    tmp_dir = tempfile.mkdtemp()
    db_file = os.path.join(tmp_dir, "concurrent_bus.db")
    sess = "SESS_BARRIER_CONCURRENCY"

    # Pre-initialize schema in main thread to eliminate DD/pragma race on initial connect
    init_bus = UnifiedMemoryBus(db_path=db_file)
    init_bus.close()

    num_workers = 8
    barrier = threading.Barrier(num_workers)
    errors = []

    def worker(worker_id):
        worker_bus = None
        try:
            worker_bus = UnifiedMemoryBus(db_path=db_file)
            barrier.wait(timeout=10.0)
            for j in range(10):
                worker_bus.record_event(sess, f"EVT_{worker_id}_{j}", f"actor_{worker_id}", "EXEC", {"j": j})
        except Exception as e:
            errors.append((worker_id, type(e).__name__, str(e)))
        finally:
            if worker_bus:
                worker_bus.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15.0)

    assert len(errors) == 0, f"Concurrent workers encountered errors: {errors}"

    verifier_bus = UnifiedMemoryBus(db_path=db_file)
    events = verifier_bus.get_events(sess)
    assert len(events) == 80
    valid, err = verifier_bus.verify_stream_integrity(sess)
    verifier_bus.close()
    shutil.rmtree(tmp_dir, ignore_errors=True)

    assert valid is True, f"Concurrent stream integrity failed: {err}"
    assert err is None


def test_rollback_to_checkpoint_selects_latest_duplicate_name(mem_bus):
    """Verifies that rollback selects the latest checkpoint when identical checkpoint names exist."""
    sess = "SESS_DUP_CHECKPOINTS"
    mem_bus.record_event(sess, "INIT", "sys", "DISCOVERY", {"step": 1})
    mem_bus.create_checkpoint(sess, "sys", "DISCOVERY", "CP_SAVE")  # sequence 2
    mem_bus.record_event(sess, "WORK_A", "sys", "DISCOVERY", {"step": 2})
    mem_bus.create_checkpoint(sess, "sys", "DISCOVERY", "CP_SAVE")  # sequence 4 (latest)
    mem_bus.record_event(sess, "WORK_B", "sys", "DISCOVERY", {"step": 3})  # sequence 5

    events_before = mem_bus.get_events(sess)
    assert len(events_before) == 5

    # Roll back to CP_SAVE should revert to sequence 4, removing sequence 5 only
    rb = mem_bus.rollback_to_checkpoint(sess, "CP_SAVE")
    assert rb["event_type"] == "ROLLBACK_EXECUTED"
    assert rb["payload"]["reverted_to_sequence"] == 4

    events_after = mem_bus.get_events(sess)
    types = [e["event_type"] for e in events_after]
    assert "WORK_B" not in types
    assert "WORK_A" in types
    assert types == ["INIT", "CHECKPOINT", "WORK_A", "CHECKPOINT", "ROLLBACK_EXECUTED"]


def test_actor_mailbox_session_isolation_and_abort(mem_bus):
    """Verifies that messages with session_id are isolated and only aborted for matching session."""
    # S1 message
    mem_bus.send_message("live-explorer", "pom-crafter", "DISCOVERY", {"task": "S1"}, session_id="SESS_01")
    # S2 message
    mem_bus.send_message("live-explorer", "pom-crafter", "DISCOVERY", {"task": "S2"}, session_id="SESS_02")

    # Both are pending
    s1_msgs = mem_bus.peek_messages("pom-crafter", session_id="SESS_01")
    s2_msgs = mem_bus.peek_messages("pom-crafter", session_id="SESS_02")
    assert len(s1_msgs) == 1
    assert len(s2_msgs) == 1

    # Abort only SESS_01
    mem_bus.abort_test(session_id="SESS_01", reason="S1 abort")

    # SESS_01 message is ABORTED
    aborted_s1 = mem_bus.receive_messages("pom-crafter", status="ABORTED", mark_read=False, session_id="SESS_01")
    assert len(aborted_s1) == 1

    # SESS_02 message is still PENDING
    pending_s2 = mem_bus.peek_messages("pom-crafter", session_id="SESS_02")
    assert len(pending_s2) == 1
    assert pending_s2[0]["payload"]["task"] == "S2"
