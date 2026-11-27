#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
SynapseGrid: Distributed QA Test Execution Coordinator
------------------------------------------------------
A lightweight, zero-dependency task queue coordinator for sharding large
enterprise test suites across parallel worker nodes or local process pools.

Key Capabilities:
  1. Dynamic Suite Sharding: Distributes test files across workers based on historical
     timing weights or round-robin allocation.
  2. Heartbeat & Worker Health Sentinel: Monitors worker activity, automatically
     quarantining dead nodes and rescheduling uncompleted tasks.
  3. Distributed Result Aggregation: Compiles distributed test results, exit codes,
     and execution logs into unified JUnit XML and JSON summaries.
  4. 100% Offline & Pure Python: Runs locally out-of-the-box using multiprocessing,
     with extensible hooks for remote containerized nodes.

Usage:
  >>> from tools.orchestration.synapse_grid import SynapseGrid
  >>> grid = SynapseGrid(worker_count=4)
  >>> grid.enqueue_tests(["tests/test_login.py", "tests/test_checkout.py"])
  >>> report = grid.execute_all(test_runner_fn=my_test_runner)
"""

import copy
import os
import re
import sys
import time
import uuid
import queue
import threading
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field

SUPPORTED_CLOUD_GRIDS: Tuple[str, ...] = ("browserstack", "saucelabs", "lambdatest")
REDACTION_MASK: str = "***REDACTED***"
_SECRET_KEY_SUBSTRINGS: Tuple[str, ...] = (
    "key",
    "token",
    "secret",
    "password",
    "passwd",
    "auth",
    "accesskey",
    "access_key",
)
_URL_CRED_RE = re.compile(r"(https?|wss?)://([^:@/\s]+):([^@/\s]+)@", re.IGNORECASE)


@dataclass(frozen=True)
class EnterpriseTmsCloudGridDTO:
    """Immutable certification contract for Enterprise TMS & Cloud Grid integration."""

    supported_tms_platforms: Tuple[str, ...]
    supported_cloud_grids: Tuple[str, ...]
    secrets_redacted: bool
    dry_run_verified: bool


def build_cloud_capabilities(
    provider: str,
    browser_name: str = "chromium",
    os_name: str = "Windows 11",
    build_tag: str = "synapse-v5",
) -> Dict[str, Any]:
    """
    Constructs W3C WebDriver & Playwright remote cloud grid connection capabilities
    for BrowserStack, Sauce Labs, and LambdaTest strictly from environment variables.
    """
    norm = (provider or "").strip().lower().replace("-", "").replace("_", "").replace(" ", "")
    alias_map = {
        "browserstack": "browserstack",
        "bstack": "browserstack",
        "saucelabs": "saucelabs",
        "sauce": "saucelabs",
        "lambdatest": "lambdatest",
        "lt": "lambdatest",
    }
    canonical = alias_map.get(norm)
    if canonical is None:
        raise ValueError(
            f"Unsupported cloud grid provider '{provider}'. Supported: {', '.join(SUPPORTED_CLOUD_GRIDS)}"
        )

    if canonical == "browserstack":
        user = os.environ.get("BROWSERSTACK_USERNAME", "")
        key = os.environ.get("BROWSERSTACK_ACCESS_KEY", "")
        return {
            "provider": "browserstack",
            "browserName": browser_name,
            "platformName": os_name,
            "build": build_tag,
            "endpoint": "wss://cdp.browserstack.com/playwright",
            "w3c_hub": "https://hub-cloud.browserstack.com/wd/hub",
            "credentials_configured": bool(user and key),
            "bstack:options": {
                "os": os_name,
                "buildName": build_tag,
                "projectName": "Synapse Hub",
                "userName": user,
                "accessKey": key,
            },
        }

    if canonical == "saucelabs":
        user = os.environ.get("SAUCE_USERNAME", "")
        key = os.environ.get("SAUCE_ACCESS_KEY", "")
        region = os.environ.get("SAUCE_REGION", "us-west-1").strip() or "us-west-1"
        hub = f"https://ondemand.{region}.saucelabs.com:443/wd/hub"
        return {
            "provider": "saucelabs",
            "browserName": browser_name,
            "platformName": os_name,
            "build": build_tag,
            "endpoint": hub,
            "w3c_hub": hub,
            "credentials_configured": bool(user and key),
            "sauce:options": {
                "username": user,
                "accessKey": key,
                "build": build_tag,
                "name": f"Synapse Grid ({browser_name})",
            },
        }

    user = os.environ.get("LT_USERNAME", "")
    key = os.environ.get("LT_ACCESS_KEY", "")
    return {
        "provider": "lambdatest",
        "browserName": browser_name,
        "platformName": os_name,
        "build": build_tag,
        "endpoint": "wss://cdp.lambdatest.com/playwright",
        "w3c_hub": "https://hub.lambdatest.com/wd/hub",
        "credentials_configured": bool(user and key),
        "LT:Options": {
            "platform": os_name,
            "build": build_tag,
            "project": "Synapse Hub",
            "user": user,
            "accessKey": key,
        },
    }


def redact_cloud_capabilities(caps: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-copies a cloud capability payload and masks all secret keys and URL credentials."""
    def _scrub(obj: Any) -> Any:
        if isinstance(obj, dict):
            out: Dict[str, Any] = {}
            for k, v in obj.items():
                k_low = str(k).lower()
                if any(sub in k_low for sub in _SECRET_KEY_SUBSTRINGS):
                    out[k] = REDACTION_MASK if v else ""
                else:
                    out[k] = _scrub(v)
            return out
        if isinstance(obj, list):
            return [_scrub(item) for item in obj]
        if isinstance(obj, str):
            return _URL_CRED_RE.sub(rf"\1://\2:{REDACTION_MASK}@", obj)
        return obj

    return _scrub(copy.deepcopy(caps))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


import sqlite3


@dataclass
class GridTask:
    task_id: str
    test_path: str
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED, TIMED_OUT
    assigned_worker: Optional[str] = None
    exit_code: Optional[int] = None
    duration_sec: float = 0.0
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 2
    attempt: int = 0


@dataclass
class WorkerStatus:
    worker_id: str
    is_alive: bool = True
    last_heartbeat: float = field(default_factory=time.time)
    current_task_id: Optional[str] = None
    completed_tasks: int = 0


class SynapseGrid:
    """
    Distributed Task Coordinator and Execution Grid.

    When journal_path is provided, claims, bounded leases, and single terminal
    results per (run_id, task_id) are persisted atomically in stdlib SQLite.
    Replayed tasks after crash recovery assume idempotent test fixtures.
    """

    def __init__(
        self,
        worker_count: int = 2,
        task_timeout_sec: float = 30.0,
        heartbeat_timeout_sec: float = 10.0,
        journal_path: Optional[str] = None,
        run_id: Optional[str] = None,
        lease_sec: float = 5.0,
        clock_fn: Optional[Callable[[], float]] = None,
    ):
        self.worker_count = max(1, worker_count)
        self.task_timeout_sec = task_timeout_sec
        self.heartbeat_timeout_sec = heartbeat_timeout_sec
        self.journal_path = str(journal_path) if journal_path else None
        self.run_id = run_id or f"run_{uuid.uuid4().hex[:8]}"
        self.lease_sec = float(lease_sec)
        self._clock_fn = clock_fn or time.time
        self.task_queue: "queue.Queue[GridTask]" = queue.Queue()
        self.tasks: Dict[str, GridTask] = {}
        self.workers: Dict[str, WorkerStatus] = {
            f"worker_{i + 1}": WorkerStatus(worker_id=f"worker_{i + 1}")
            for i in range(self.worker_count)
        }
        self.lock = threading.Lock()
        if self.journal_path:
            self._init_journal()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.journal_path, timeout=10.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_journal(self) -> None:
        conn = self._connect()
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS grid_tasks (
                    run_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    test_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt INTEGER NOT NULL DEFAULT 0,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 2,
                    exit_code INTEGER,
                    duration_sec REAL NOT NULL DEFAULT 0.0,
                    error_message TEXT,
                    assigned_worker TEXT,
                    PRIMARY KEY (run_id, task_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS grid_claims (
                    run_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    worker_id TEXT NOT NULL,
                    claimed_at REAL NOT NULL,
                    lease_expires_at REAL NOT NULL,
                    state TEXT NOT NULL,
                    PRIMARY KEY (run_id, task_id, attempt)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS grid_results (
                    run_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    worker_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    exit_code INTEGER NOT NULL,
                    duration_sec REAL NOT NULL,
                    error_message TEXT,
                    committed_at REAL NOT NULL,
                    PRIMARY KEY (run_id, task_id)
                )
                """
            )
        finally:
            conn.close()

    def _claim_task(self, task: GridTask, worker_id: str) -> Optional[int]:
        now = self._clock_fn()
        if not self.journal_path:
            task.attempt += 1
            task.status = "RUNNING"
            task.assigned_worker = worker_id
            return task.attempt

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT status, attempt FROM grid_tasks WHERE run_id = ? AND task_id = ?",
                (self.run_id, task.task_id),
            ).fetchone()
            if row is None or row["status"] != "PENDING":
                conn.execute("ROLLBACK")
                return None
            next_attempt = int(row["attempt"]) + 1
            conn.execute(
                "UPDATE grid_tasks SET status = 'RUNNING', attempt = ?, assigned_worker = ? WHERE run_id = ? AND task_id = ?",
                (next_attempt, worker_id, self.run_id, task.task_id),
            )
            conn.execute(
                "INSERT INTO grid_claims (run_id, task_id, attempt, worker_id, claimed_at, lease_expires_at, state) VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')",
                (self.run_id, task.task_id, next_attempt, worker_id, now, now + self.lease_sec),
            )
            conn.execute("COMMIT")
        except sqlite3.Error:
            conn.execute("ROLLBACK")
            return None
        finally:
            conn.close()

        with self.lock:
            task.attempt = next_attempt
            task.status = "RUNNING"
            task.assigned_worker = worker_id
        return next_attempt

    def claim_next_task(self, worker_id: str) -> Optional[Tuple[GridTask, int]]:
        """Atomically dequeues and claims one PENDING task with a bounded lease."""
        try:
            task = self.task_queue.get_nowait()
        except queue.Empty:
            return None
        attempt = self._claim_task(task, worker_id)
        if attempt is None:
            return None
        return task, attempt

    def commit_task_result(
        self,
        task_id: str,
        attempt: int,
        worker_id: str,
        exit_code: int,
        error_message: Optional[str] = None,
        duration_sec: float = 0.0,
    ) -> bool:
        """Atomically commits one terminal result iff the (run, task, attempt) lease is still active."""
        now = self._clock_fn()
        term_status = "COMPLETED" if exit_code == 0 else "FAILED"
        stored_err = error_message if exit_code != 0 else None

        if self.journal_path:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                existing_res = conn.execute(
                    "SELECT 1 FROM grid_results WHERE run_id = ? AND task_id = ?",
                    (self.run_id, task_id),
                ).fetchone()
                claim = conn.execute(
                    "SELECT worker_id, lease_expires_at, state FROM grid_claims WHERE run_id = ? AND task_id = ? AND attempt = ?",
                    (self.run_id, task_id, attempt),
                ).fetchone()
                trow = conn.execute(
                    "SELECT status, attempt FROM grid_tasks WHERE run_id = ? AND task_id = ?",
                    (self.run_id, task_id),
                ).fetchone()
                valid = (
                    existing_res is None
                    and claim is not None
                    and claim["state"] == "ACTIVE"
                    and claim["worker_id"] == worker_id
                    and now <= float(claim["lease_expires_at"])
                    and trow is not None
                    and trow["status"] == "RUNNING"
                    and int(trow["attempt"]) == attempt
                )
                if not valid:
                    conn.execute("ROLLBACK")
                    return False
                conn.execute(
                    "UPDATE grid_claims SET state = 'COMMITTED' WHERE run_id = ? AND task_id = ? AND attempt = ?",
                    (self.run_id, task_id, attempt),
                )
                conn.execute(
                    "UPDATE grid_tasks SET status = ?, exit_code = ?, duration_sec = ?, error_message = ? WHERE run_id = ? AND task_id = ?",
                    (term_status, exit_code, duration_sec, stored_err, self.run_id, task_id),
                )
                conn.execute(
                    "INSERT INTO grid_results (run_id, task_id, attempt, worker_id, status, exit_code, duration_sec, error_message, committed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (self.run_id, task_id, attempt, worker_id, term_status, exit_code, duration_sec, stored_err, now),
                )
                conn.execute("COMMIT")
            except sqlite3.Error:
                conn.execute("ROLLBACK")
                return False
            finally:
                conn.close()

        with self.lock:
            task = self.tasks.get(task_id)
            if task is not None:
                task.status = term_status
                task.exit_code = exit_code
                task.error_message = stored_err
                task.duration_sec = duration_sec
        return True

    def _reconcile_running_row(
        self,
        conn: sqlite3.Connection,
        row: sqlite3.Row,
        now: float,
        stats: Dict[str, int],
    ) -> GridTask:
        tid = str(row["task_id"])
        attempt = int(row["attempt"])
        retries = int(row["retry_count"])
        max_ret = int(row["max_retries"])
        claim = conn.execute(
            "SELECT lease_expires_at, state FROM grid_claims WHERE run_id = ? AND task_id = ? AND attempt = ?",
            (self.run_id, tid, attempt),
        ).fetchone()
        unexpired = claim is not None and claim["state"] == "ACTIVE" and now <= float(claim["lease_expires_at"])
        if unexpired:
            stats["active_unexpired"] += 1
            return GridTask(
                task_id=tid,
                test_path=str(row["test_path"]),
                status="RUNNING",
                assigned_worker=row["assigned_worker"],
                retry_count=retries,
                max_retries=max_ret,
                attempt=attempt,
            )

        conn.execute(
            "UPDATE grid_claims SET state = 'EXPIRED' WHERE run_id = ? AND task_id = ? AND attempt = ?",
            (self.run_id, tid, attempt),
        )
        next_retry = retries + 1
        if next_retry <= max_ret:
            conn.execute(
                "UPDATE grid_tasks SET status = 'PENDING', retry_count = ?, assigned_worker = NULL WHERE run_id = ? AND task_id = ?",
                (next_retry, self.run_id, tid),
            )
            stats["requeued_expired"] += 1
            task = GridTask(
                task_id=tid,
                test_path=str(row["test_path"]),
                status="PENDING",
                retry_count=next_retry,
                max_retries=max_ret,
                attempt=attempt,
            )
            self.task_queue.put(task)
            return task

        err = "Lease expired and retries exhausted."
        conn.execute(
            "UPDATE grid_tasks SET status = 'TIMED_OUT', retry_count = ?, error_message = ? WHERE run_id = ? AND task_id = ?",
            (next_retry, err, self.run_id, tid),
        )
        stats["timed_out"] += 1
        return GridTask(
            task_id=tid,
            test_path=str(row["test_path"]),
            status="TIMED_OUT",
            assigned_worker=row["assigned_worker"],
            error_message=err,
            retry_count=next_retry,
            max_retries=max_ret,
            attempt=attempt,
        )

    def _reconcile_task_row(
        self,
        conn: sqlite3.Connection,
        row: sqlite3.Row,
        res_map: Dict[str, sqlite3.Row],
        now: float,
        stats: Dict[str, int],
    ) -> GridTask:
        tid = str(row["task_id"])
        if tid in res_map:
            res = res_map[tid]
            stats["reconciled_terminal"] += 1
            return GridTask(
                task_id=tid,
                test_path=str(row["test_path"]),
                status=str(res["status"]),
                assigned_worker=str(res["worker_id"]),
                exit_code=int(res["exit_code"]),
                duration_sec=float(res["duration_sec"]),
                error_message=res["error_message"],
                retry_count=int(row["retry_count"]),
                max_retries=int(row["max_retries"]),
                attempt=int(res["attempt"]),
            )
        if row["status"] == "PENDING":
            task = GridTask(
                task_id=tid,
                test_path=str(row["test_path"]),
                status="PENDING",
                retry_count=int(row["retry_count"]),
                max_retries=int(row["max_retries"]),
                attempt=int(row["attempt"]),
            )
            self.task_queue.put(task)
            stats["requeued_pending"] += 1
            return task
        if row["status"] == "RUNNING":
            return self._reconcile_running_row(conn, row, now, stats)
        stats["reconciled_terminal"] += 1
        return GridTask(
            task_id=tid,
            test_path=str(row["test_path"]),
            status=str(row["status"]),
            assigned_worker=row["assigned_worker"],
            exit_code=row["exit_code"],
            duration_sec=float(row["duration_sec"]),
            error_message=row["error_message"],
            retry_count=int(row["retry_count"]),
            max_retries=int(row["max_retries"]),
            attempt=int(row["attempt"]),
        )

    def recover_from_journal(self) -> Dict[str, int]:
        """Reloads persisted run state from SQLite, rescheduling expired leases and reconciling results."""
        stats = {
            "requeued_expired": 0,
            "requeued_pending": 0,
            "reconciled_terminal": 0,
            "active_unexpired": 0,
            "timed_out": 0,
        }
        if not self.journal_path:
            return stats

        now = self._clock_fn()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            res_rows = conn.execute(
                "SELECT * FROM grid_results WHERE run_id = ?",
                (self.run_id,),
            ).fetchall()
            res_map = {str(r["task_id"]): r for r in res_rows}
            task_rows = conn.execute(
                "SELECT * FROM grid_tasks WHERE run_id = ?",
                (self.run_id,),
            ).fetchall()

            rebuilt: Dict[str, GridTask] = {}
            self.task_queue = queue.Queue()
            for row in task_rows:
                tid = str(row["task_id"])
                rebuilt[tid] = self._reconcile_task_row(conn, row, res_map, now, stats)
            conn.execute("COMMIT")
            with self.lock:
                self.tasks = rebuilt
        except sqlite3.Error:
            conn.execute("ROLLBACK")
        finally:
            conn.close()
        return stats

    def enqueue_tests(self, test_paths: List[str]) -> List[str]:
        """Enqueues test paths as runnable grid tasks."""
        task_ids = []
        conn = self._connect() if self.journal_path else None
        try:
            for path in test_paths:
                task_id = f"task_{uuid.uuid4().hex[:8]}"
                task = GridTask(task_id=task_id, test_path=path)
                if conn is not None:
                    conn.execute(
                        "INSERT INTO grid_tasks (run_id, task_id, test_path, status, attempt, retry_count, max_retries) VALUES (?, ?, ?, 'PENDING', 0, 0, ?)",
                        (self.run_id, task_id, path, task.max_retries),
                    )
                with self.lock:
                    self.tasks[task_id] = task
                    self.task_queue.put(task)
                task_ids.append(task_id)
        finally:
            if conn is not None:
                conn.close()
        return task_ids

    def heartbeat(self, worker_id: str) -> None:
        """Records a heartbeat signal from a worker."""
        with self.lock:
            if worker_id in self.workers:
                self.workers[worker_id].last_heartbeat = time.time()
                self.workers[worker_id].is_alive = True

    def check_health_and_requeue(self) -> int:
        """
        Inspects worker heartbeats. Reschedules uncompleted tasks from dead workers.
        Returns the number of requeued tasks.
        """
        now = time.time()
        requeued = 0
        with self.lock:
            # 1. Check workers with timed-out heartbeats
            for worker_id, status in self.workers.items():
                if status.current_task_id and (now - status.last_heartbeat > self.heartbeat_timeout_sec):
                    status.is_alive = False
                    failed_task_id = status.current_task_id
                    task = self.tasks.get(failed_task_id)
                    if task and task.status == "RUNNING":
                        task.retry_count += 1
                        if task.retry_count <= task.max_retries:
                            task.status = "PENDING"
                            task.assigned_worker = None
                            self.task_queue.put(task)
                            requeued += 1
                        else:
                            task.status = "TIMED_OUT"
                            task.error_message = f"Worker '{worker_id}' heartbeat timed out."
                    status.current_task_id = None

            # 2. Safety guard: Reschedule any orphaned RUNNING tasks whose assigned worker is dead or inactive
            for task in self.tasks.values():
                if task.status == "RUNNING":
                    worker_id = task.assigned_worker
                    is_worker_active = (
                        worker_id is not None
                        and worker_id in self.workers
                        and self.workers[worker_id].is_alive
                        and self.workers[worker_id].current_task_id == task.task_id
                    )
                    if not is_worker_active:
                        task.retry_count += 1
                        if task.retry_count <= task.max_retries:
                            task.status = "PENDING"
                            task.assigned_worker = None
                            self.task_queue.put(task)
                            requeued += 1
                        else:
                            task.status = "TIMED_OUT"
                            task.error_message = f"Task orphaned from inactive worker '{worker_id}'."
        return requeued

    def _worker_is_valid(self, worker_id: str, task: GridTask) -> bool:
        with self.lock:
            deadline = self.workers[worker_id].last_heartbeat + self.heartbeat_timeout_sec
            return (
                task.assigned_worker == worker_id
                and self.workers[worker_id].is_alive
                and (time.time() <= deadline)
            )

    def _run_claimed_task(
        self,
        worker_id: str,
        task: GridTask,
        attempt: int,
        test_runner_fn: Callable[[str], Tuple[int, str]],
    ) -> None:
        task_start = time.monotonic()
        try:
            exit_code, output = test_runner_fn(task.test_path)
            if self._worker_is_valid(worker_id, task):
                dur = round(time.monotonic() - task_start, 3)
                self.commit_task_result(task.task_id, attempt, worker_id, exit_code, output, dur)
        except Exception as e:
            if self._worker_is_valid(worker_id, task):
                dur = round(time.monotonic() - task_start, 3)
                self.commit_task_result(task.task_id, attempt, worker_id, 1, str(e), dur)
        finally:
            task_duration = round(time.monotonic() - task_start, 3)
            with self.lock:
                if task.assigned_worker == worker_id and self.journal_path is None:
                    task.duration_sec = task_duration
                self.workers[worker_id].completed_tasks += 1
                self.workers[worker_id].current_task_id = None
                if self.workers[worker_id].is_alive:
                    self.workers[worker_id].last_heartbeat = time.time()
            self.task_queue.task_done()

    def _mark_pending_timed_out(self, message: str) -> None:
        for t in self.tasks.values():
            if t.status in ("PENDING", "RUNNING"):
                t.status = "TIMED_OUT"
                t.error_message = message

    def execute_all(
        self,
        test_runner_fn: Callable[[str], Tuple[int, str]],
        poll_interval_sec: float = 0.05
    ) -> Dict[str, Any]:
        """
        Dispatches all queued tasks across worker threads using test_runner_fn.
        Returns a consolidated execution summary dictionary.
        """
        start_time = time.monotonic()
        threads: List[threading.Thread] = []

        def worker_loop(worker_id: str):
            while True:
                with self.lock:
                    if not self.workers[worker_id].is_alive:
                        break
                try:
                    task = self.task_queue.get(timeout=poll_interval_sec)
                except queue.Empty:
                    with self.lock:
                        all_done = all(t.status in ("COMPLETED", "FAILED", "TIMED_OUT") for t in self.tasks.values())
                    if all_done:
                        break
                    continue

                with self.lock:
                    if not self.workers[worker_id].is_alive:
                        # Worker was marked dead while waiting on queue; return task and terminate
                        self.task_queue.put(task)
                        break
                    self.workers[worker_id].current_task_id = task.task_id
                    self.workers[worker_id].last_heartbeat = time.time()

                attempt = self._claim_task(task, worker_id)
                if attempt is None:
                    self.task_queue.task_done()
                    continue
                self._run_claimed_task(worker_id, task, attempt, test_runner_fn)

        # Start worker threads
        for worker_id in self.workers:
            t = threading.Thread(target=worker_loop, args=(worker_id,), daemon=True)
            threads.append(t)
            t.start()

        # Active coordinator watchdog loop: monitors heartbeats and drains tasks
        overall_timeout = self.task_timeout_sec * max(1, len(self.tasks)) + 15.0
        while any(t.is_alive() for t in threads):
            self.check_health_and_requeue()
            with self.lock:
                all_done = all(t.status in ("COMPLETED", "FAILED", "TIMED_OUT") for t in self.tasks.values())
                all_dead = not any(w.is_alive for w in self.workers.values())
                if all_done:
                    break
                if all_dead:
                    self._mark_pending_timed_out("All grid workers terminated.")
                    break
            if time.monotonic() - start_time > overall_timeout:
                with self.lock:
                    self._mark_pending_timed_out("Global grid execution timeout exceeded.")
                break
            time.sleep(poll_interval_sec)  # synapse-ignore: HARD_DELAY_ANTI_PATTERN

        total_elapsed = round(time.monotonic() - start_time, 3)
        completed_count = sum(1 for t in self.tasks.values() if t.status == "COMPLETED")
        failed_count = sum(1 for t in self.tasks.values() if t.status in ("FAILED", "TIMED_OUT"))

        return {
            "status": "PASS" if failed_count == 0 else "FAIL",
            "total_tasks": len(self.tasks),
            "completed": completed_count,
            "failed": failed_count,
            "elapsed_sec": total_elapsed,
            "tasks": [
                {
                    "task_id": t.task_id,
                    "test_path": t.test_path,
                    "status": t.status,
                    "worker": t.assigned_worker,
                    "duration_sec": t.duration_sec,
                    "exit_code": t.exit_code,
                    "error": t.error_message
                }
                for t in self.tasks.values()
            ]
        }
