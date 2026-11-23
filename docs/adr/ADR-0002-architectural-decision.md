<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0002: Architectural Decision

- **Status:** Accepted (DoD Certified)
- **Date:** 2026-11-23
- **Source Plan:** `implementation_plan.md`
- **Deciders:** Synapse Hub Autonomous Agent Core & Engineering Team

---

## Context & Problem Statement
| File Path | Trạng thái | Line Anchors | Trách nhiệm kiến trúc & Blast Radius |
|---|---|---|---|
| `tools/context/output_offloader.py` | `[CREATE]` | `(New)` | Cơ chế tự động offload output log/kết quả test lớn (> 2KB) ra file tạm, trả về ref pointer chống tràn context LLM. |
| `tests/test_output_offloader.py` | `[CREATE]` | `(New)` | Unit test kiểm định ngưỡng kích thước, định dạng metadata và khả năng khôi phục slice log. |
| `tools/runtime/ast_command_guard.py` | `[CREATE]` | `(New)` | AST command parser & security guard: chặn lệnh phá hoại, kiểm tra timeout trước khi `agent_runner` thực thi. |
| `tests/test_ast_command_guard.py` | `[CREATE]` | `(New)` | Unit test kiểm tra nhận diện các mẫu lệnh độc hại, flag cấm và whitelist an toàn. |
| `tools/core/sop_schema.py` | `[CREATE]` | `(New)` | Schema validation và định nghĩa kiểu dữ liệu cho Declarative QA Standard Operating Procedures. |
| `standards/sop/smoke_test_sop.yaml` | `[CREATE]` | `(New)` | File mẫu SOP chuẩn hóa cho quy trình chạy Smoke Test tự động. |
| `tests/test_sop_enforcer.py` | `[CREATE]` | `(New)` | Unit test kiểm tra nạp SOP, chuyển trạng thái và xác thực chứng chỉ cryptographic HMAC token. |
| `tools/api/a2a_qa_server.py` | `[CREATE]` | `(New)` | Server chuẩn giao thức A2A 1.0 (JSON-RPC/SSE) tiếp nhận yêu cầu QA từ agent bên ngoài (Devin, Cursor, Claude Code). |
| `tests/test_a2a_qa_server.py` | `[CREATE]` | `(New)` | Unit test xác thực luồng bắt tay A2A, định dạng JSON-RPC 2.0 và streaming SSE event. |
| `tools/core/agent_runner.py` | `[MODIFY]` | `(L60-L160)` | Tích hợp hook kiểm tra lệnh qua AST Command Guard và tự động offload output lớn qua Output Offloader. |
| `tools/core/fsm_enforcer.py` | `[MODIFY]` | `(L145-L230)` | Mở rộng FSM Enforcer để nạp và thực thi các QA SOP declarative bên cạnh 5 stage mặc định. |

---

---

## Decision Drivers & Invariants
- Grounding Principle: "Read First – Plan Later" (AGENTS.md §5).
- Zero Fake-Passes Invariant & Deterministic Verification Matrix.
- Execution DAG with Milestone Circuit Breakers & Clean Context Handoff.

---

## Considered Options & Architectural Decision
### 2.1 Tool Output Offloader Interface (`tools/context/output_offloader.py`)
```python
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass(frozen=True)
class OffloadedArtifactRef:
    artifact_id: str
    file_path: str
    total_bytes: int
    total_lines: int
    head_excerpt: str
    tail_excerpt: str

class OutputOffloader:
    def __init__(self, storage_dir: str = "scratch/offload", threshold_bytes: int = 2048) -> None: ...
    def process_output(self, raw_output: str, source_command: str) -> Tuple[bool, str, Optional[OffloadedArtifactRef]]: ...
```

### 2.2 AST Command Guard Interface (`tools/runtime/ast_command_guard.py`)
```python
from dataclasses import dataclass
from typing import List, Tuple

@dataclass(frozen=True)
class CommandAuditResult:
    is_safe: bool
    violations: List[str]
    ast_tokens: List[str]
    suggested_action: str

class ASTCommandGuard:
    def audit_command(self, cmd_args: List[str]) -> CommandAuditResult: ...
```

### 2.3 Declarative SOP Engine Schema (`tools/core/sop_schema.py`)
```python
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass(frozen=True)
class SOPTransitionRule:
    target_stage: str
    required_evidence_fields: List[str]
    condition_expression: Optional[str] = None

@dataclass(frozen=True)
class SOPStageDefinition:
    stage_id: str
    actor_role: str
    description: str
    transitions: List[SOPTransitionRule]

@dataclass(frozen=True)
class QASOPWorkflow:
    sop_id: str
    version: str
    description: str
    initial_stage: str
    stages: Dict[str, SOPStageDefinition]
```

### 2.4 A2A 1.0 JSON-RPC / SSE Server Interface (`tools/api/a2a_qa_server.py`)
```python
from typing import Any, AsyncIterator, Dict

class A2AQAServer:
    def handle_jsonrpc_request(self, payload: Dict[str, Any]) -> Dict[str, Any]: ...
    async def stream_task_execution(self, task_id: str, action: str) -> AsyncIterator[str]: ...
```

---

---

## Vulnerability Self-Critique & Mitigation Strategies
### 5.1 Phân tích 3 Nhóm Lỗ Hổng Bắt Buộc (Tri-Vulnerability Self-Critique)

1. **Vulnerability 1 — Race Conditions, Concurrency & State Inconsistency:**
   - *Nguy cơ:* Khi nhiều agent hoặc subprocess gọi `OutputOffloader` cùng lúc, việc ghi đồng thời vào thư mục `scratch/offload` có thể gây va chạm tên file hoặc hỏng dữ liệu (concurrency conflict).
   - *Biện pháp giảm thiểu:* Sử dụng UUID ngẫu nhiên kết hợp băm nội dung SHA256 và ghi qua file tạm (`atomic write`: ghi ra `.tmp` rồi đổi tên `os.replace`), đảm bảo tính idempotent tuyệt đối khi thao tác ghi đồng thời.

2. **Vulnerability 2 — Resource Extremes, Boundary & Timeout:**
   - *Nguy cơ:* Test log cực lớn (> 500MB) có thể làm cạn bộ nhớ RAM (OOM) nếu load toàn bộ vào memory trước khi offload, hoặc lệnh shell bị treo vô hạn (timeout).
   - *Biện pháp giảm thiểu:* Xử lý stream I/O theo chunk 64KB khi đọc stdout/stderr, chặn hard timeout 60s cho các lệnh kiểm tra AST guard, và trả về excerpt cắt gọn bounded trong trường hợp cực biên.

3. **Vulnerability 3 — Blast Radius & Backward Compatibility:**
   - *Nguy cơ:* Việc sửa đổi `tools/core/agent_runner.py` và `tools/core/fsm_enforcer.py` có thể làm hỏng các workflow hiện hành đang dựa vào 5-stage FSM cũ hoặc các test suite của Synapse Hub.
   - *Biện pháp giảm thiểu:* Giữ nguyên hoàn toàn chữ ký hàm (backward compatible API) của `agent_runner.run_monitored_command` và các stage mặc định của `fsm_enforcer`. Chức năng SOP và Offload hoạt động dưới dạng cờ mở rộng (opt-in / progressive enhancement), không phá vỡ bất kỳ caller hiện tại nào.

### 5.2 Rollback & State-Migration Matrix
- **Khi M1 hoặc M2 gặp sự cố:** Hoàn tác nhanh bằng `git checkout -- tools/core/agent_runner.py` và xóa file mới trong `tests/` và `tools/runtime/`. Hệ thống quay về trạng thái chạy runner cũ không bị gián đoạn.
- **Khi M3 hoặc M4 gặp sự cố:** Hoàn tác nhanh bằng `git checkout -- tools/core/fsm_enforcer.py`. FSM cũ tiếp tục hoạt động bình thường với 5 stage truyền thống.
- **Khi M5 gặp sự cố:** Xóa endpoint server `tools/api/a2a_qa_server.py`. Hệ sinh thái Synapse Hub hoạt động hoàn toàn độc lập với các agent bên ngoài.

---

## Consequences & Guarantees
- **Positive:** Sealed interface contracts, zero-regression blast radius, idempotent execution.
- **Negative / Constraints:** Strict adherence to atomic milestone budget (<= 3 files) and type contracts.
---

## Plan Calibration & Drift Analysis
- **Plan Accuracy Score:** 73.3%
- **Plan Drift Ratio:** 0.267
- **Unplanned Files (4):** `project_state.json`, `tests/test_agent_runner.py`, `tools/tools_schema.json`, `standards/sop/`

