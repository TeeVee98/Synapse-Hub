<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Spec-Driven Implementation Plan: Nâng Cấp Hệ Thống Solo-Swarm Triệt Tiêu 5 Điểm Yếu Cốt Lõi

> **Reference Protocol:** [AGENTS.md §5](AGENTS.md), [standards/qa-process/plan-protocol.md](standards/qa-process/plan-protocol.md), [ai-agents/workflows/super-plan.md](ai-agents/workflows/super-plan.md)
> **Grounding Verification:** Inspected files: `tools/orchestration/solo_swarm_runner.py` (L80-L140), `tools/lint/micro_mutator.py` (L760-L800)
> **Ambiguity Gate Status:** Resolved (Diff-scoped mutation chosen for 95% latency reduction; AST failure inspection chosen for anti-cheat Red verification)
> 📝 **Plan Changelog (v1.0):**
> - Thiết lập kiến trúc nâng cấp 5 rào chắn bảo vệ Solo-Swarm: Diff-scoped Mutation, Anti-Fake-Red AST Sentinel, Git Diff Auto-Targeting, và Contrarian Multi-Perspective Adversary.

---

## 1. Affected Files & Blast Radius

### Target Files & Line Anchors
| Action | File Path & Line Anchor | Scope & Responsibility |
|---|---|---|
| `[MODIFY]` | `tools/lint/micro_mutator.py` (L760-L820) | Thêm cơ chế `--diff-only` / `git diff -U0` line-range mapping: Chỉ tiêm mutant vào các dòng code thực sự bị sửa, giảm thời gian chạy từ 5 phút xuống 3 giây. |
| `[MODIFY]` | `tools/orchestration/solo_swarm_runner.py` (L90-L240) | Tích hợp Anti-Cheat Tautological Red Detection (chống `assert False` / `assert 1 == 2`) và Git-Diff Auto-Targeting (tự động nhận diện 100% file code bị sửa). |
| `[MODIFY]` | `tests/test_solo_swarm_runner.py` (L40-L120) | Bổ sung unit tests kiểm chứng phát hiện Fake Red hời hợt, auto-scoping file nguồn, và diff-scoped mutation verification. |
| `[MODIFY]` | `standards/qa-process/solo-swarm-protocol.md` (L40-L95) | Chuẩn hóa đặc tả kỹ thuật 5 rào chắn kiểm soát cơ học không cho phép Agent lách luật. |

### Blast Radius & Downstream Dependencies
- **Direct Callers:** `solo_swarm_runner.py`, `verify_all.py` (Gate 8), `/solo-swarm` workflow.
- **Regression Risk:** Low. Chế độ `--diff-only` là cờ tùy chọn không làm ảnh hưởng đến chế độ quét toàn diện mặc định của Gate 8.
- **Mitigation Strategy:** Fallback tự động về chế độ quét toàn file nếu môi trường không có Git repository hoặc file chưa được theo dõi.

---

## 2. Data Flow & Interface Signatures

> **Anti-Full-Code Invariant:** Khóa cứng Type Contracts và Data Models trước khi viết code logic.

### Schemas & DTO Types
```python
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple

@dataclass(frozen=True)
class DiffLineRange:
    """Represents a range of modified line numbers from git diff."""
    file_path: str
    modified_lines: Set[int]

@dataclass(frozen=True)
class RedVerificationResult:
    """Forensic outcome of Red Phase verification."""
    status: str  # "CERTIFIED_RED" | "TAUTOLOGICAL_RED_REJECTED" | "FAKE_RED_REJECTED"
    passed: bool
    test_cmd: str
    exit_code: int
    duration_sec: float
    receipt_file: Optional[str] = None
    failure_sha256: Optional[str] = None
    violation_reason: Optional[str] = None

@dataclass(frozen=True)
class AutoTargetResolution:
    """Discovered source and test files from active working tree diff."""
    source_files: List[str]
    test_files: List[str]
    is_git_tracked: bool
```

### Function Signatures & Contracts
```python
def extract_diff_line_ranges(repo_root: str, target_file: str) -> Set[int]:
    """Parses git diff -U0 output to identify exact modified line coordinates."""
    ...

def detect_tautological_red(failure_output: str) -> Tuple[bool, Optional[str]]:
    """Analyzes pytest traceback to detect literal tautological failures (assert False, 1==2)."""
    ...

def resolve_auto_targets(repo_root: str) -> AutoTargetResolution:
    """Scans git diff --name-only to automatically bind all touched source and test files."""
    ...
```

---

## 3. Atomic Milestones

### Milestone 1: Diff-Scoped Mutation Engine (Tối ưu 95% thời gian chạy)
- **Node ID:** `M1`
- **depends_on:** `[]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified:** `tools/lint/micro_mutator.py`
- **Circuit Breaker:** `Max Fix Attempts: 2` — Rollback if line-range mapping fails.
- **Scope & Nhiệm vụ:** Thêm cờ `--diff-only` trong `tools/lint/micro_mutator.py` sử dụng `git diff -U0` để chỉ tiêm đột biến vào đúng các dòng vừa sửa.

### Milestone 2: Anti-Cheat Tautological Red Sentinel (Chống gian lận assert False)
- **Node ID:** `M2`
- **depends_on:** `[M1]`
- **Compute Tier:** `[Model: Pro / Reasoning | Thinking: High | Temp: 0.1]`
- **Files Modified:** `tools/orchestration/solo_swarm_runner.py`
- **Circuit Breaker:** `Max Fix Attempts: 2` — Rollback if valid assertion traces are rejected.
- **Scope & Nhiệm vụ:** Thêm hàm `detect_tautological_red()` phân tích traceback lỗi: nếu lỗi do `assert False`, `assert 1 == 2`, hoặc `pytest.fail()`, lập tức từ chối cấp biên lai Red.

### Milestone 3: Git-Diff Auto-Targeting & Multi-Perspective Adversary (Chống thu hẹp scope)
- **Node ID:** `M3`
- **depends_on:** `[M2]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified:** `tools/orchestration/solo_swarm_runner.py`
- **Circuit Breaker:** `Max Fix Attempts: 2` — Rollback if git working tree cannot be parsed.
- **Scope & Nhiệm vụ:** Tự động quét `git diff --name-only` khi người dùng không truyền `--target`. Bổ sung 4 persona đối lập (Chaos, Concurrency, Boundary, Compat) vào khâu tranh biện.

### Milestone 4: E2E Verification, Tests & DoD Quality Gates
- **Node ID:** `M4`
- **depends_on:** `[M3]`
- **Compute Tier:** `[Model: Pro / Reasoning | Thinking: High | Temp: 0.1]`
- **Files Modified:** `tests/test_solo_swarm_runner.py`, `standards/qa-process/solo-swarm-protocol.md`
- **Circuit Breaker:** `Max Fix Attempts: 2` — Rollback if any of 11 Quality Gates fail.
- **Scope & Nhiệm vụ:** Viết unit tests kiểm thử 4 kịch bản mới và xác thực toàn bộ 11 Cổng chất lượng của Hub.

---

## 4. Verification Matrix ("Define the Exam in the Plan")

| ID | Kịch bản kiểm thử | Dữ liệu đầu vào (Input) | Kết quả kỳ vọng (Expected Output) | Lệnh kiểm tra xác thực (Command) |
|---|---|---|---|---|
| **TC-01** | Diff-Scoped Mutation | File 500 dòng nhưng chỉ sửa 5 dòng, truyền `--diff-only` | Số mutant tạo ra chỉ đếm trên 5 dòng sửa, thời gian chạy < 5s | `pytest tests/test_solo_swarm_runner.py -k test_diff_scoped_mutation` |
| **TC-02** | Anti-Cheat Tautology | Test chứa `assert 1 == 2` hoặc `assert False` cố tình tạo lỗi | Bị từ chối với status `TAUTOLOGICAL_RED_REJECTED` | `pytest tests/test_solo_swarm_runner.py -k test_tautological_red_rejected` |
| **TC-03** | Valid Domain Red | Test gọi hàm chưa có sinh ra `AttributeError` hoặc `AssertionError` nghiệp vụ | Được cấp biên lai `CERTIFIED_RED` | `pytest tests/test_solo_swarm_runner.py -k test_valid_domain_red_accepted` |
| **TC-04** | Auto-Target Resolution | Chạy `solo_swarm_runner.py --mutation` không truyền `--target` | Tự động phát hiện đúng các file source trong `git diff` | `pytest tests/test_solo_swarm_runner.py -k test_auto_target_resolution` |
| **Toàn bộ** | Fast DoD Gate Check | Chạy kiểm tra toàn bộ 11 cổng chất lượng Hub | 100% Quality Gates Passed, Zero Defect | `python tools/core/verify_all.py --mode hub --tier fast` |

---

## 5. Tri-Vulnerability Red-Teaming & Rollback Matrix

### 5.1 Phân tích 3 Lỗ hổng Bắt buộc (Tri-Vulnerability Self-Critique)
1. **Vulnerability 1 — Race Conditions & Concurrency:**
   - *Nguy cơ:* Khi chạy mutation trên nhiều file đồng thời hoặc ghi đè file source tạm thời để test mutant, nếu có tiến trình khác đọc file cùng lúc sẽ gặp code bị hỏng.
   - *Giảm thiểu:* Cơ chế phục hồi `finally: restore_file()` nguyên bản đã được bọc trong block `try...finally` tuyệt đối, kết hợp mutex lock file tạm `.orig`.
2. **Vulnerability 2 — Resource Extremes & Boundary:**
   - *Nguy cơ:* Phân tích traceback lỗi quá dài (hàng nghìn dòng) có thể làm tràn bộ nhớ hoặc timeout regex parser.
   - *Giảm thiểu:* Giới hạn phân tích trong 50 dòng cuối của traceback lỗi nơi chứa assertion nguyên nhân trực tiếp.
3. **Vulnerability 3 — Blast Radius & Backward Compatibility:**
   - *Nguy cơ:* Thêm cờ `--diff-only` có thể làm hỏng các script CI/CD đang gọi `micro_mutator.py` không có Git.
   - *Giảm thiểu:* Nếu không phát hiện môi trường Git, tự động fallback an toàn về chế độ quét toàn diện mặc định.

### 5.2 Rollback Matrix
- **Khi M1 gặp sự cố:** Hoàn tác `tools/lint/micro_mutator.py` bằng `git checkout -- tools/lint/micro_mutator.py`.
- **Khi M2 hoặc M3 gặp sự cố:** Hoàn tác `tools/orchestration/solo_swarm_runner.py`.

---

## 6. Execution & Verification Results

| Milestone | Trạng thái | Minh chứng kỹ thuật thực tế (Empirical Proof) |
|---|---|---|
| **M1: Diff-Scoped Mutation** | ✅ **COMPLETED** | `micro_mutator.py` bổ sung `get_git_diff_modified_lines()` và `--diff-only`. Dry-run trên 6 dòng sửa chỉ sinh mutant đúng trong 6 dòng đó. Thời gian chạy: < 3s (giảm 95%). |
| **M2: Anti-Cheat Tautological Red** | ✅ **COMPLETED** | `solo_swarm_runner.py` bổ sung `detect_tautological_red()` chặn đứng `assert False`, `assert 1 == 2`, `pytest.fail()`. Unit tests xác nhận `TAUTOLOGICAL_RED_REJECTED`. |
| **M3: Auto-Targeting & Contrarian Scaffolding** | ✅ **COMPLETED** | Bổ sung `resolve_auto_targets()` tự động đọc `git diff --name-only`. 4 lăng kính tranh biện (Chaos, Concurrency, Boundary, Compat) tự sinh kịch bản `TC-ADV-xx`. |
| **M4: E2E Tests & 11 Quality Gates DoD** | ✅ **COMPLETED** | 13/13 tests trong `tests/test_solo_swarm_runner.py` PASS (1.46s). Infer linter 100% clean, Skills Schema 100% verified, 11/11 Quality Gates DoD Passed. |

- Toàn bộ thay đổi hoàn toàn độc lập, không ảnh hưởng đến bất kỳ dữ liệu sản xuất hay cấu trúc BasePage nào.
