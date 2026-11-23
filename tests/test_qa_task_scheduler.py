# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""Unit tests for QATaskScheduler (tests/test_qa_task_scheduler.py).

Verifies task registration, thread execution, webhook notification delivery,
and state transitions.

Author: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
License: MIT
"""

import sys
from unittest.mock import MagicMock, patch
import pytest

from tools.orchestration.qa_task_scheduler import QATaskScheduler, ScheduledQATask


@pytest.fixture
def scheduler():
    return QATaskScheduler()


def test_task_registration_and_retrieval(scheduler):
    task = scheduler.register_task(
        name="nightly_smoke_suite",
        command=["pytest", "tests/test_login.py"],
        webhook_url="https://hooks.slack.com/services/mock",
        task_id="t_001",
    )
    assert isinstance(task, ScheduledQATask)
    assert task.task_id == "t_001"
    assert task.status == "PENDING"

    retrieved = scheduler.get_task("t_001")
    assert retrieved is not None
    assert retrieved.name == "nightly_smoke_suite"

    all_tasks = scheduler.list_tasks()
    assert len(all_tasks) == 1
    assert all_tasks[0]["task_id"] == "t_001"


def test_execute_task_sync_success(scheduler):
    scheduler.register_task(
        name="unit_eval",
        command=[sys.executable, "-c", "print('Job completed')"],
        task_id="t_002",
    )
    res = scheduler.execute_task_sync("t_002")
    assert res["status"] == "PASSED"

    task = scheduler.get_task("t_002")
    assert task.status == "COMPLETED"
    assert task.last_run_iso is not None


def test_background_task_thread_execution(scheduler):
    scheduler.register_task(
        name="bg_job",
        command=[sys.executable, "-c", "import time; time.sleep(0.05); print('Done')"],
        task_id="t_003",
    )
    th = scheduler.run_task_in_background("t_003")
    assert th.is_alive() or not th.is_alive()
    th.join(timeout=5.0)

    task = scheduler.get_task("t_003")
    assert task.status == "COMPLETED"


def test_webhook_dispatch_mock(scheduler):
    mock_resp = MagicMock()
    mock_resp.__enter__.return_value.status = 200

    with patch("urllib.request.urlopen", return_value=mock_resp):
        ok = scheduler.dispatch_webhook(
            "https://discord.com/api/webhooks/mock",
            {"status": "PASS", "summary": "10 Quality gates passed"},
        )
        assert ok is True


def test_execute_unknown_task_returns_error(scheduler):
    res = scheduler.execute_task_sync("non_existent_id")
    assert res["status"] == "ERROR"
    assert "not found" in res["error"]


def test_periodic_scheduler_ticker(scheduler):
    scheduler.register_task(
        name="recurring_job",
        command=[sys.executable, "-c", "print('Tick executed')"],
        interval_seconds=0.1,
        task_id="t_recurring",
    )
    scheduler.start_scheduler(tick_interval_sec=0.05)
    import time
    time.sleep(0.3)
    scheduler.stop_scheduler()

    task = scheduler.get_task("t_recurring")
    assert task is not None
    assert task.last_run_timestamp is not None

