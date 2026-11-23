<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0003: Architectural Decision

- **Status:** Accepted (DoD Certified)
- **Date:** 2026-11-23
- **Source Plan:** `implementation_plan.md`
- **Deciders:** Synapse Hub Autonomous Agent Core & Engineering Team

---

## Context & Problem Statement
| File Path | Trạng thái | Line Anchors | Trách nhiệm kiến trúc & Blast Radius |
|---|---|---|---|
| `tools/runtime/docker_sandbox_runner.py` | `[CREATE]` | `(New)` | Driver quản lý container Docker: kiểm tra daemon, ánh xạ workspace, cô lập thực thi và fallback tự động về Local Subprocess. |
| `tests/test_docker_sandbox_runner.py` | `[CREATE]` | `(New)` | Unit test kiểm tra phát hiện docker daemon, sinh lệnh `docker run` cách ly, fallback an toàn và timeout handling. |
| `tools/reasoning/qa_model_router.py` | `[CREATE]` | `(New)` | Bộ định tuyến Model Router theo độ phức tạp tác vụ: phân loại log/lint sang Flash model, debug POM/RCA sang Reasoning/Pro model. |
| `tests/test_qa_model_router.py` | `[CREATE]` | `(New)` | Unit test xác thực thuật toán heuristic phân loại task, ước tính chi phí token và fallback model khi lỗi. |
| `tools/orchestration/qa_task_scheduler.py` | `[CREATE]` | `(New)` | Trình lập lịch tác vụ nền (Background Task Scheduler): quản lý hàng đợi chạy test dài (JMeter/Regression), dispatch Webhook thông báo. |
| `tests/test_qa_task_scheduler.py` | `[CREATE]` | `(New)` | Unit test kiểm tra cơ chế lập lịch cron/interval, chạy ngầm không block luồng chính, và payload gửi webhook. |
| `tests/test_dashboard_chat.py` | `[CREATE]` | `(New)` | Unit test xác thực endpoint `/api/chat` và luồng SSE streaming trong `serve_dashboard.py`. |
| `tools/core/agent_runner.py` | `[MODIFY]` | `(L120-L180)` | Bổ sung cờ `--sandbox {local,docker}` và hook chuyển hướng thực thi qua module Docker Sandbox Runner. |
| `tools/dashboard/serve_dashboard.py` | `[MODIFY]` | `(L300-L500)` | Tích hợp giao diện tab "Interactive QA Chat & Swarm Console", handler nhận câu hỏi và stream phản hồi thời gian thực qua SSE. |

---

---

## Decision Drivers & Invariants
- Grounding Principle: "Read First – Plan Later" (AGENTS.md §5).
- Zero Fake-Passes Invariant & Deterministic Verification Matrix.
- Execution DAG with Milestone Circuit Breakers & Clean Context Handoff.

---

## Considered Options & Architectural Decision
### 2.1 Docker Sandbox Runner Interface (`tools/runtime/docker_sandbox_runner.py`)
```python
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

@dataclass(frozen=True)
class SandboxConfig:
    image: str = "python:3.12-slim"
    memory_limit: str = "2g"
    cpu_limit: float = 2.0
    timeout_sec: float = 120.0
    network_enabled: bool = True

class DockerSandboxRunner:
    def __init__(self, config: Optional[SandboxConfig] = None) -> None: ...
    def is_docker_available(self) -> bool: ...
    def run_sandboxed(self, command: List[str], workspace_dir: str) -> Dict[str, Any]: ...
```

### 2.2 QA Model Router Interface (`tools/reasoning/qa_model_router.py`)
```python
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

class ModelComputeTier(Enum):
    FLASH_LITE = "flash_lite"      # Triage, linting, format check
    FLASH = "flash"                # Standard test execution, assertion checks
    PRO_REASONING = "pro"          # Root cause analysis, POM refactor, flaky repair

@dataclass(frozen=True)
class ModelRouteDecision:
    tier: ModelComputeTier
    recommended_model: str
    estimated_cost_ratio: float
    reason: str

class QAModelRouter:
    def route_task(self, task_description: str, context_tokens: int = 0) -> ModelRouteDecision: ...
```

### 2.3 QA Task Scheduler & Webhook Interface (`tools/orchestration/qa_task_scheduler.py`)
```python
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

@dataclass(frozen=True)
class ScheduledQATask:
    task_id: str
    name: str
    command: List[str]
    cron_expression: Optional[str] = None
    webhook_url: Optional[str] = None
    status: str = "PENDING"

class QATaskScheduler:
    def register_task(self, task: ScheduledQATask) -> str: ...
    def execute_background_job(self, task_id: str) -> Dict[str, Any]: ...
    def dispatch_webhook(self, webhook_url: str, payload: Dict[str, Any]) -> bool: ...
```

### 2.4 Interactive Dashboard QA Chat Protocol (`tools/dashboard/serve_dashboard.py`)
```python
# API Endpoint: POST /api/chat
# Request Payload: {"message": "Chạy smoke test và phân tích lỗi", "session_id": "sess_123"}
# Response: Server-Sent Events (SSE) streaming token chunks & execution progress
```

---

---

## Vulnerability Self-Critique & Mitigation Strategies
### 5.1 Phân tích 3 Nhóm Lỗ Hổng Bắt Buộc (Tri-Vulnerability Self-Critique)

1. **Vulnerability 1 — Race Conditions, Concurrency & State Inconsistency:**
   - *Nguy cơ:* Khi nhiều tác vụ chạy ngầm được lập lịch cùng lúc (`qa_task_scheduler`), việc truy cập đồng thời vào file trạng thái hoặc tài nguyên test có thể gây xung đột ghi (concurrency write collision) hoặc sai lệch hàng đợi.
   - *Biện pháp giảm thiểu:* Dùng cơ chế khóa tiểu trình `threading.Lock` kết hợp bộ nhớ hàng đợi an toàn đa luồng (`queue.Queue`) và ghi file atomic (`.tmp` + `os.replace`), đảm bảo tính idempotent tuyệt đối khi đa tiến trình chạy song song.

2. **Vulnerability 2 — Resource Extremes, Boundary & Timeout:**
   - *Nguy cơ:* Chạy container Docker có thể bị treo vô hạn nếu script test rơi vào vòng lặp vô tận, hoặc container ngốn sạch tài nguyên RAM của host máy tính (OOM).
   - *Biện pháp giảm thiểu:* Cấu hình cứng giới hạn tài nguyên container (`--memory=2g`, `--cpus=2.0`) và hard timeout 120s trong `DockerSandboxRunner`. Nếu vượt ngưỡng, tự động kill container và thu hồi tài nguyên sạch sẽ.

3. **Vulnerability 3 — Blast Radius & Backward Compatibility:**
   - *Nguy cơ:* Sửa đổi `serve_dashboard.py` (file hơn 1.000 dòng) và `agent_runner.py` có thể làm hỏng giao diện Dashboard hiện hành hoặc làm đứt gãy các lệnh test CLI cũ của Synapse Hub.
   - *Biện pháp giảm thiểu:* Thêm endpoint `/api/chat` mới độc lập mà không can thiệp vào các endpoint telemetry hiện tại (`/api/status`, `/api/skills`). Với `agent_runner.py`, cờ `--sandbox` mặc định là `local`, giữ nguyên 100% hành vi cũ trừ khi người dùng chủ động truyền `--sandbox docker`.

### 5.2 Rollback & State-Migration Matrix
- **Khi M1 gặp sự cố:** Chạy `git checkout -- tools/core/agent_runner.py` và xóa `tools/runtime/docker_sandbox_runner.py`. Hệ thống lập tức quay về chạy local subprocess bình thường.
- **Khi M2 hoặc M3 gặp sự cố:** Xóa các file mới tương ứng trong `tools/reasoning/` và `tools/orchestration/`. Không ảnh hưởng đến bất kỳ core test runner nào.
- **Khi M4 gặp sự cố:** Hoàn tác nhanh bằng `git checkout -- tools/dashboard/serve_dashboard.py`. Dashboard trở về trạng thái Mission Control ban đầu.

---

## Consequences & Guarantees
- **Positive:** Sealed interface contracts, zero-regression blast radius, idempotent execution.
- **Negative / Constraints:** Strict adherence to atomic milestone budget (<= 3 files) and type contracts.
---

## Plan Calibration & Drift Analysis
- **Plan Accuracy Score:** 38.5%
- **Plan Drift Ratio:** 0.615
- **Unplanned Files (16):** `AGENTS.md`, `project_state.json`, `standards/qa-process/plan-protocol.md`, `tests/test_agent_runner.py`, `tools/core/fsm_enforcer.py`, `tools/tools_schema.json`, `standards/qa-process/solo-swarm-protocol.md`, `standards/sop/`, `tests/test_a2a_qa_server.py`, `tests/test_ast_command_guard.py`, `tests/test_output_offloader.py`, `tests/test_sop_enforcer.py`, `tools/api/a2a_qa_server.py`, `tools/context/output_offloader.py`, `tools/core/sop_schema.py`, `tools/runtime/ast_command_guard.py`

