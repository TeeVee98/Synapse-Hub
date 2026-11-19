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

    attempt_count = 0

    def recovering_runner(path: str):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            # First attempt: worker sleeps beyond heartbeat_timeout_sec without heartbeat
            time.sleep(0.15)
            return 1, "Simulated initial stall"
        # Second attempt (after auto-requeue to worker_2): finishes successfully
        return 0, "Recovered on retry"

    summary = grid.execute_all(test_runner_fn=recovering_runner, poll_interval_sec=0.02)

    assert summary["status"] == "PASS"
    assert summary["completed"] == 1
    assert summary["failed"] == 0
    assert attempt_count >= 2
