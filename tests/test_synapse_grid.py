#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Unit tests for SynapseGrid Distributed Task Coordinator
-------------------------------------------------------
Verifies:
  - Task enqueuing & parallel worker execution
  - Failure reporting and exit code capture
  - Worker heartbeat expiration and auto-requeue
"""

import sqlite3
import threading
import time
from tools.orchestration.synapse_grid import SynapseGrid


def test_grid_parallel_execution_success():
    """Verifies that multiple test tasks are distributed and completed successfully."""
    grid = SynapseGrid(worker_count=3)
    test_files = [
        "tests/test_login.py",
        "tests/test_checkout.py",
        "tests/test_profile.py",
        "tests/test_cart.py",
    ]
    grid.enqueue_tests(test_files)

    def dummy_runner(path: str):
        # Simulate brief test execution
        time.sleep(0.01)
        return 0, "All tests passed"

    summary = grid.execute_all(test_runner_fn=dummy_runner)

    assert summary["status"] == "PASS"
    assert summary["total_tasks"] == 4
    assert summary["completed"] == 4
    assert summary["failed"] == 0
    assert summary["elapsed_sec"] > 0.0

    # Ensure work was distributed across multiple workers
    assigned_workers = {t["worker"] for t in summary["tasks"]}
    assert len(assigned_workers) >= 2


def test_grid_failure_handling():
    """Verifies that individual test failures are properly reported."""
    grid = SynapseGrid(worker_count=2)
    grid.enqueue_tests(["tests/test_pass.py", "tests/test_fail.py"])

    def flaky_runner(path: str):
        if "fail" in path:
            return 1, "AssertionError: Expected 200 OK but got 500"
        return 0, "OK"

    summary = grid.execute_all(test_runner_fn=flaky_runner)

    assert summary["status"] == "FAIL"
    assert summary["completed"] == 1
    assert summary["failed"] == 1

    failed_task = next(t for t in summary["tasks"] if "fail" in t["test_path"])
    assert failed_task["exit_code"] == 1
    assert "AssertionError" in failed_task["error"]


def test_grid_worker_heartbeat_timeout_requeue():
    """Verifies that dead worker tasks are detected and rescheduled."""
    grid = SynapseGrid(worker_count=1, heartbeat_timeout_sec=0.05)
    task_ids = grid.enqueue_tests(["tests/test_heavy.py"])
    t_id = task_ids[0]

    # Manually assign task to worker_1 and simulate heartbeat timeout
    grid.tasks[t_id].status = "RUNNING"
    grid.tasks[t_id].assigned_worker = "worker_1"
    grid.workers["worker_1"].current_task_id = t_id
    grid.workers["worker_1"].last_heartbeat = time.time() - 0.2  # Expired

    requeued_count = grid.check_health_and_requeue()

    assert requeued_count == 1
    assert grid.tasks[t_id].status == "PENDING"
    assert grid.tasks[t_id].retry_count == 1
    assert grid.workers["worker_1"].is_alive is False


def test_grid_active_watchdog_recovers_hung_worker():
    """Verifies that execute_all's active coordinator loop detects heartbeat timeout and recovers."""
    grid = SynapseGrid(worker_count=2, heartbeat_timeout_sec=0.08)
    grid.enqueue_tests(["tests/test_hung_first_attempt.py"])

    attempts = []

    def recovering_runner(path: str):
        attempts.append(1)
        if len(attempts) == 1:
            # First attempt: worker sleeps beyond heartbeat_timeout_sec until watchdog marks it dead
            deadline = time.time() + 1.5
            while time.time() < deadline:
                with grid.lock:
                    dead_workers = [w for w in grid.workers.values() if not w.is_alive]
                    if dead_workers:
                        break
                time.sleep(0.01)
            return 1, "Simulated initial stall"
        # Second attempt (after auto-requeue to alive worker): finishes successfully
        return 0, "Recovered on retry"

    summary = grid.execute_all(test_runner_fn=recovering_runner, poll_interval_sec=0.02)

    assert summary["status"] == "PASS"
    assert summary["completed"] == 1
    assert summary["failed"] == 0
    assert len(attempts) >= 2


def test_journal_crash_after_claim_restart_and_idempotent_reconciliation(tmp_path):
    """
    Positive & Resilience: Persists claims/leases/results in SQLite across restart.
    Crash after claim reschedules expired work; committed results are reconciled
    once without duplicate re-execution (replayed tasks assume idempotent fixtures).
    """
    db_path = str(tmp_path / "grid_journal.db")
    clock_now = [100.0]

    # Phase 1: Coordinator enqueues two tasks, claims task 1, commits task 2, then stops
    g1 = SynapseGrid(worker_count=1, journal_path=db_path, run_id="run-m11-1", lease_sec=5.0, clock_fn=lambda: clock_now[0])
    task_ids = g1.enqueue_tests(["tests/t1.py", "tests/t2.py"])
    t1_id, t2_id = task_ids
    assert g1.tasks[t1_id].attempt == 0

    claimed_1 = g1.claim_next_task("worker_1")
    assert claimed_1 is not None
    task1, attempt1 = claimed_1
    assert task1.task_id == t1_id
    assert attempt1 == 1
    assert g1._claim_task(task1, "worker_2") is None

    claimed_2 = g1.claim_next_task("worker_1")
    assert claimed_2 is not None
    task2, attempt2 = claimed_2
    assert g1.commit_task_result(task2.task_id, attempt2, "worker_1", 0, None, 0.05) is True

    mem_grid = SynapseGrid(worker_count=1)
    [mem_tid] = mem_grid.enqueue_tests(["tests/mem.py"])
    mem_grid.execute_all(test_runner_fn=lambda p: (0, "OK"), poll_interval_sec=0.01)
    assert mem_grid.tasks[mem_tid].attempt == 1

    # Phase 2: Before lease expiry, restarting coordinator does NOT prematurely reschedule t1
    clock_now[0] = 102.0
    g2 = SynapseGrid(worker_count=1, journal_path=db_path, run_id="run-m11-1", lease_sec=5.0, clock_fn=lambda: clock_now[0])
    rec_early = g2.recover_from_journal()
    assert rec_early["requeued_expired"] == 0
    assert rec_early["active_unexpired"] == 1
    assert rec_early["reconciled_terminal"] == 1

    # Phase 3: Advance clock past lease expiry (106.0 > 105.0) and restart coordinator
    clock_now[0] = 106.0
    g3 = SynapseGrid(worker_count=1, journal_path=db_path, run_id="run-m11-1", lease_sec=5.0, clock_fn=lambda: clock_now[0])
    rec_expired = g3.recover_from_journal()
    assert rec_expired["requeued_expired"] == 1
    assert rec_expired["reconciled_terminal"] == 1

    executed = []

    def idempotent_runner(path: str):
        executed.append(path)
        return 0, "OK"

    summary = g3.execute_all(test_runner_fn=idempotent_runner, poll_interval_sec=0.01)
    assert summary["status"] == "PASS"
    assert summary["completed"] == 2
    assert executed == ["tests/t1.py"]

    # Phase 4: Stale completion from attempt 1 must be rejected and only 1 terminal result persisted
    assert g3.commit_task_result(t1_id, attempt1, "worker_1", 1, "stale fail", 1.0) is False
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        rows = conn.execute("SELECT task_id, status FROM grid_results WHERE run_id = ?", ("run-m11-1",)).fetchall()
    assert sorted(rows) == sorted([(t1_id, "COMPLETED"), (t2_id, "COMPLETED")])

    # Phase 5: Restarting after all results committed reconciles without re-running anything
    g4 = SynapseGrid(worker_count=1, journal_path=db_path, run_id="run-m11-1", lease_sec=5.0, clock_fn=lambda: clock_now[0])
    rec_done = g4.recover_from_journal()
    assert rec_done["requeued_expired"] == 0
    assert rec_done["reconciled_terminal"] == 2
    executed.clear()
    summary_done = g4.execute_all(test_runner_fn=idempotent_runner, poll_interval_sec=0.01)
    assert summary_done["completed"] == 2
    assert executed == []


def test_journal_negative_stale_worker_fencing_and_threading_event_recovery(tmp_path):
    """Negative & Concurrency: Uses threading.Event (zero time.sleep) to fence delayed stale writers."""
    db_path = str(tmp_path / "fenced.db")
    clock_now = [200.0]

    g1 = SynapseGrid(worker_count=1, journal_path=db_path, run_id="run-fence", lease_sec=4.0, clock_fn=lambda: clock_now[0])
    [t_id] = g1.enqueue_tests(["tests/fenced_case.py"])

    started = threading.Event()
    lease_reclaimed = threading.Event()
    results_seen = {}

    def stalled_worker_fn():
        claimed = g1.claim_next_task("worker_1")
        assert claimed is not None
        _, att1 = claimed
        started.set()
        assert lease_reclaimed.wait(timeout=2.0)
        results_seen["stale_commit"] = g1.commit_task_result(t_id, att1, "worker_1", 1, "late failure", 2.0)

    t = threading.Thread(target=stalled_worker_fn)
    t.start()
    assert started.wait(timeout=2.0)

    # Wrong worker rejected while attempt 1 active
    assert g1.commit_task_result(t_id, 1, "worker_wrong", 0, None, 0.1) is False

    # Expire lease and recover on new coordinator instance
    clock_now[0] = 205.0
    g2 = SynapseGrid(worker_count=1, journal_path=db_path, run_id="run-fence", lease_sec=4.0, clock_fn=lambda: clock_now[0])
    rec = g2.recover_from_journal()
    assert rec["requeued_expired"] == 1

    res2 = g2.execute_all(test_runner_fn=lambda p: (0, "fresh success"), poll_interval_sec=0.01)
    assert res2["completed"] == 1
    lease_reclaimed.set()
    t.join(timeout=2.0)

    assert results_seen["stale_commit"] is False
    assert g2.tasks[t_id].status == "COMPLETED"


def test_journal_boundary_retry_exhaustion_and_empty_recovery(tmp_path):
    """Boundary: Repeated expired claims beyond max_retries mark TIMED_OUT; empty run recovers cleanly."""
    db_path = str(tmp_path / "boundary.db")
    clock_now = [300.0]

    g_empty = SynapseGrid(worker_count=1, journal_path=db_path, run_id="empty-run", clock_fn=lambda: clock_now[0])
    empty_rec = g_empty.recover_from_journal()
    assert empty_rec == {"requeued_expired": 0, "requeued_pending": 0, "reconciled_terminal": 0, "active_unexpired": 0, "timed_out": 0}

    g = SynapseGrid(worker_count=1, journal_path=db_path, run_id="retry-run", lease_sec=2.0, clock_fn=lambda: clock_now[0])
    [t_id] = g.enqueue_tests(["tests/flaky.py"])
    g.tasks[t_id].max_retries = 1
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE grid_tasks SET max_retries = 1 WHERE run_id = ? AND task_id = ?", ("retry-run", t_id))

    assert g.claim_next_task("worker_1") is not None
    clock_now[0] = 303.0
    g_retry1 = SynapseGrid(worker_count=1, journal_path=db_path, run_id="retry-run", lease_sec=2.0, clock_fn=lambda: clock_now[0])
    assert g_retry1.recover_from_journal()["requeued_expired"] == 1

    assert g_retry1.claim_next_task("worker_1") is not None
    clock_now[0] = 306.0
    g_retry2 = SynapseGrid(worker_count=1, journal_path=db_path, run_id="retry-run", lease_sec=2.0, clock_fn=lambda: clock_now[0])
    rec2 = g_retry2.recover_from_journal()
    assert rec2["timed_out"] == 1
    assert g_retry2.tasks[t_id].status == "TIMED_OUT"
