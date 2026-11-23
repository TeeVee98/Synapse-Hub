# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""Background Task Scheduler & Webhook Dispatcher (tools/orchestration/qa_task_scheduler.py).

Inspired by AgentScope 2.0's background task scheduling & wake-up events:
Enables offloading long-running QA workloads (JMeter load tests, large regression
suites) to asynchronous background threads with automatic Webhook notification
upon DoD completion.

Author: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
License: MIT
"""

from __future__ import annotations

import datetime
import json
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

# Enforce UTF-8 stdout/stderr encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


@dataclass
class ScheduledQATask:
    """Descriptor for an asynchronous background QA task."""

    task_id: str
    name: str
    command: List[str]
    interval_seconds: Optional[float] = None
    webhook_url: Optional[str] = None
    status: str = "PENDING"
    last_run_iso: Optional[str] = None
    last_run_timestamp: Optional[float] = None
    last_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class QATaskScheduler:
    """Thread-safe background scheduler and event notifier for long-running QA runs."""

    def __init__(self) -> None:
        self._tasks: Dict[str, ScheduledQATask] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_threads: Dict[str, threading.Thread] = {}
        self._scheduler_thread: Optional[threading.Thread] = None

    def start_scheduler(self, tick_interval_sec: float = 0.5) -> None:
        """Starts the active background scheduler ticker loop."""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            return
        self._stop_event.clear()
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            args=(tick_interval_sec,),
            daemon=True,
            name="qa_scheduler_ticker",
        )
        self._scheduler_thread.start()

    def stop_scheduler(self) -> None:
        """Stops the active background scheduler ticker loop cleanly."""
        self._stop_event.set()
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=2.0)

    def _scheduler_loop(self, tick_interval_sec: float) -> None:
        """Internal periodic ticker evaluating interval tasks."""
        while not self._stop_event.is_set():
            now = time.time()
            tasks_to_run: List[str] = []

            with self._lock:
                for task in self._tasks.values():
                    if task.interval_seconds and task.interval_seconds > 0:
                        if task.last_run_timestamp is None or (now - task.last_run_timestamp >= task.interval_seconds):
                            task.last_run_timestamp = now
                            tasks_to_run.append(task.task_id)

            for t_id in tasks_to_run:
                self.run_task_in_background(t_id)

            self._stop_event.wait(tick_interval_sec)

    def register_task(
        self,
        name: str,
        command: List[str],
        interval_seconds: Optional[float] = None,
        webhook_url: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> ScheduledQATask:
        """Registers a new QA job for execution."""
        t_id = task_id or f"task_{uuid.uuid4().hex[:8]}"
        task = ScheduledQATask(
            task_id=t_id,
            name=name,
            command=command,
            interval_seconds=interval_seconds,
            webhook_url=webhook_url,
            status="PENDING",
        )
        with self._lock:
            self._tasks[t_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[ScheduledQATask]:
        """Retrieves task state descriptor."""
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self) -> List[Dict[str, Any]]:
        """Returns list of all registered tasks."""
        with self._lock:
            return [t.to_dict() for t in self._tasks.values()]

    def dispatch_webhook(self, webhook_url: str, payload: Dict[str, Any]) -> bool:
        """Dispatches an HTTP POST notification to external chat or CI/CD webhook."""
        if not webhook_url:
            return False
        try:
            data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=data_bytes,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                code = getattr(resp, "status", getattr(resp, "code", 200))
                try:
                    code_int = int(code)
                    return 200 <= code_int < 300
                except (ValueError, TypeError):
                    return True
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            sys.stderr.write(f"[WARN] Webhook dispatch to {webhook_url} failed: {err}\n")
            return False

    def execute_task_sync(self, task_id: str) -> Dict[str, Any]:
        """Executes the task synchronously, updates state, and fires webhook."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return {"status": "ERROR", "error": f"Task '{task_id}' not found"}
            task.status = "RUNNING"

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Import agent_runner to execute command safely
        try:
            from tools.core.agent_runner import execute_agent_run

            run_res = execute_agent_run(task.command, label=task.name)
            exit_code = run_res.get("exit_code", 1)
            status = "COMPLETED" if exit_code == 0 else "FAILED"
        except (ImportError, Exception) as err:
            run_res = {"status": "FAILED", "error": str(err)}
            status = "FAILED"

        with self._lock:
            task.status = status
            task.last_run_iso = now_iso
            task.last_result = run_res

        # Fire webhook notification
        if task.webhook_url:
            payload = {
                "event": "QA_TASK_COMPLETED",
                "task_id": task.task_id,
                "task_name": task.name,
                "status": status,
                "timestamp": now_iso,
                "summary": run_res.get("summary", ""),
            }
            self.dispatch_webhook(task.webhook_url, payload)

        return run_res

    def run_task_in_background(self, task_id: str) -> threading.Thread:
        """Launches task execution in an unblocking detached background thread."""
        thread = threading.Thread(
            target=self.execute_task_sync,
            args=(task_id,),
            daemon=True,
            name=f"qa_worker_{task_id}",
        )
        with self._lock:
            self._worker_threads[task_id] = thread
        thread.start()
        return thread
