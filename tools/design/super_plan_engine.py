#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/design/super_plan_engine.py — Mechanical Engine for /super-plan Workflow
--------------------------------------------------------------------------------
Provides CLI automation for the 5-phase Super-Plan pipeline:
  1. ambiguity-check: Scans tasks for architectural forks & generates up to 3 MCQs.
  2. scaffold: Generates a grounded Execution-DAG implementation plan skeleton.
  3. validate: Runs strict plan schema sentinel verification.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
from enum import Enum
import json
import math
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.lint.plan_schema_sentinel import validate_plan_content
from tools.lint.plan_mutator import run_plan_mutation_audit
from tools.context.polyglot_ast_parser import parse_polyglot_signatures
from tools.context.call_graph_indexer import get_or_build_call_graph

# Enforce UTF-8 stdout/stderr encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


class PlanningTier(str, Enum):
    TIER_0_FAST = "FAST_TRACK"        # RiskScore < 0.35, <= 2 files: 1-shot Micro-plan (< 10s)
    TIER_1_STANDARD = "STANDARD"       # 0.35 <= RiskScore < 0.70: 1 branch + Contract Check
    TIER_2_DEEP = "DEEP_SUPER_PLAN"    # RiskScore >= 0.70: Full 5 stages + Tournament + Mutation


@dataclass(frozen=True)
class RiskMetricDTO:
    fan_in: int
    cross_boundary: bool
    state_mutation: bool
    history_drift: float
    critical_path: bool = False
    blast_radius: int = 0

    @property
    def risk_score(self) -> float:
        eff_fan_in = self.blast_radius if self.blast_radius > 0 else self.fan_in
        base = (
            0.35 * math.log2(1 + eff_fan_in) +
            0.25 * float(self.cross_boundary) +
            0.25 * float(self.state_mutation) +
            0.15 * min(1.0, max(0.0, self.history_drift))
        )
        if self.critical_path:
            base = max(base, 0.40)  # Guarantees critical paths never route to Tier 0 Micro-Plan
        return round(base, 3)


def calculate_risk_routing(
    task: str,
    target_files: Optional[List[str]] = None,
    repo_root: str = _REPO_ROOT
) -> Tuple[PlanningTier, RiskMetricDTO]:
    """Calculates deterministic RiskScore (0 LLM token) and routes to optimal planning tier."""
    files = target_files or []

    # 1. CrossBoundary detection: touches Public API, DB schema, Auth, or Shared Standards
    cross_boundary_patterns = re.compile(
        r"\b(?:api|endpoint|schema|migration|auth|token|jwt|credential|permission|shared|public|protocol|standard)\b",
        re.I
    )
    cross_boundary = bool(cross_boundary_patterns.search(task))
    for f in files:
        if any(kw in f.lower() for kw in ("api", "schema", "auth", "standards/", "models/", "routes/")):
            cross_boundary = True
            break

    # 2. StateMutation detection: concurrency, lock, db write, payments, cache flush
    state_mutation_patterns = re.compile(
        r"\b(?:concurrency|async|thread|mutex|lock|race|state|mutate|database|db|migration|ledger|payment|transaction|queue)\b",
        re.I
    )
    state_mutation = bool(state_mutation_patterns.search(task))

    # 3. Critical Path detection (auth, security, schema, database, core, runner, base_page)
    critical_path_keywords = (
        "auth", "security", "schema", "database", "core", "runner", "base_page",
        "migration", "payment", "middleware", "transaction", "invariant"
    )
    critical_path = any(cp in task.lower() for cp in critical_path_keywords)
    for f in files:
        f_lower = f.lower()
        if any(cp in f_lower for cp in critical_path_keywords):
            critical_path = True
            break

    # 4. HistoryDrift from project_state.json
    history_drift = 0.1
    state_path = os.path.join(repo_root, "project_state.json")
    if os.path.isfile(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as fh:
                sdata = json.load(fh)
            history_drift = float(sdata.get("plan_calibration", {}).get("last_drift_ratio", 0.1))
        except Exception:
            history_drift = 0.1

    # 5. FanIn & Blast Radius calculation: indexed graph of callers/references in codebase
    fan_in = 0
    try:
        graph = get_or_build_call_graph(repo_root)
        for f in files:
            fan_in += graph.get_fan_in(f)
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        code_exts = (".py", ".ts", ".js", ".java", ".groovy")
        for f in files:
            if not f.lower().endswith(code_exts):
                continue
            base = os.path.splitext(os.path.basename(f))[0]
            if base and len(base) > 2 and os.path.isdir(os.path.join(repo_root, "tools")):
                pattern = re.compile(rf"\b{re.escape(base)}\b")
                for root, _, dirfiles in os.walk(os.path.join(repo_root, "tools")):
                    for df in dirfiles:
                        if df.endswith(".py") and df != os.path.basename(f):
                            p = os.path.join(root, df)
                            try:
                                with open(p, "r", encoding="utf-8", errors="ignore") as pf:
                                    if pattern.search(pf.read()):
                                        fan_in += 1
                            except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                                pass

    blast_radius = fan_in + (5 if critical_path else 0)

    metric = RiskMetricDTO(
        fan_in=fan_in,
        cross_boundary=cross_boundary,
        state_mutation=state_mutation,
        history_drift=history_drift,
        critical_path=critical_path,
        blast_radius=blast_radius,
    )

    score = metric.risk_score
    if score < 0.35 and not critical_path and blast_radius < 5 and len(files) <= 2:
        tier = PlanningTier.TIER_0_FAST
    elif score < 0.70 and blast_radius < 10:
        tier = PlanningTier.TIER_1_STANDARD
    else:
        tier = PlanningTier.TIER_2_DEEP

    return tier, metric


AMBIGUITY_TRIGGERS = [
    ("storage", re.compile(r"\b(?:database|db|cache|redis|in-memory|storage|persist|lưu\s+trữ)\b", re.I),
     "Lựa chọn cơ chế lưu trữ / cache cho giải pháp?",
     [
         "(Recommended) In-Memory với LRU cache và thread-safety lock",
         "Persistent SQLite / File-based persistence",
         "Redis / External Key-Value store"
     ],
     {
         "(Recommended) In-Memory với LRU cache và thread-safety lock": "Counter-Argument: Dữ liệu mất khi restart tiến trình; tốn RAM nếu cache unbounded.",
         "Persistent SQLite / File-based persistence": "Counter-Argument: Độ trễ I/O đĩa tăng; nguy cơ table lock khi đa tiến trình ghi đồng thời.",
         "Redis / External Key-Value store": "Counter-Argument: Thêm external dependency; tăng network latency và nguy cơ connection timeout."
     }),
    ("concurrency", re.compile(r"\b(?:async|sync|thread|concurrency|queue|background|bất\s+đồng\s+bộ|đa\s+luồng)\b", re.I),
     "Mô hình xử lý đồng thời (concurrency model) mong muốn?",
     [
         "(Recommended) Bounded thread-pool với retry exponential backoff",
         "Native asyncio event-loop",
         "Single-threaded synchronous with timeout guard"
     ],
     {
         "(Recommended) Bounded thread-pool với retry exponential backoff": "Counter-Argument: Khó debug race conditions; tốn overhead thread context switch.",
         "Native asyncio event-loop": "Counter-Argument: Dễ vỡ nếu có third-party sync blocking call; đòi hỏi migrate toàn bộ caller sang async.",
         "Single-threaded synchronous with timeout guard": "Counter-Argument: Không tận dụng đa lõi; throughput giảm khi xử lý tác vụ I/O nặng."
     }),
    ("api_contract", re.compile(r"\b(?:api|endpoint|contract|interface|breaking|tương\s+thích|giao\s+diện)\b", re.I),
     "Mức độ đảm bảo tính tương thích ngược của Interface?",
     [
         "(Recommended) 100% Backward-compatible adapter (giữ nguyên legacy caller)",
         "Deprecate warning với version bump",
         "Hard break with caller migration"
     ],
     {
         "(Recommended) 100% Backward-compatible adapter (giữ nguyên legacy caller)": "Counter-Argument: Tích tụ technical debt và shim adapter code lâu dài.",
         "Deprecate warning với version bump": "Counter-Argument: Caller cũ vẫn có thể bỏ qua warning gây khó kiểm soát vòng đời.",
         "Hard break with caller migration": "Counter-Argument: Gãy các downstream modules chưa kịp migrate đồng bộ."
     }),
    ("performance_sla", re.compile(r"\b(?:speed|latency|scale|fast|performance|hiệu\s+năng|tốc\s+độ)\b", re.I),
     "Ưu tiên chính giữa Tốc độ thực thi và Tính nhất quán?",
     [
         "(Recommended) Tính nhất quán (Strict Consistency / Zero Data Loss)",
         "Tốc độ tối đa (Sub-millisecond low-latency, eventual consistency)",
         "Cân bằng với Circuit Breaker"
     ],
     {
         "(Recommended) Tính nhất quán (Strict Consistency / Zero Data Loss)": "Counter-Argument: Giảm throughput tại các hot-path có tần suất ghi cao.",
         "Tốc độ tối đa (Sub-millisecond low-latency, eventual consistency)": "Counter-Argument: Tồn tại cửa sổ stale read; rủi ro xung đột dữ liệu.",
         "Cân bằng với Circuit Breaker": "Counter-Argument: Tăng độ phức tạp cấu hình ngưỡng trip và trạng thái half-open."
     }),
]


def check_ambiguities(task_description: str) -> List[Dict[str, Any]]:
    """Analyzes task description to identify architectural forks with anti-rubber-stamping counter-arguments."""
    questions: List[Dict[str, Any]] = []

    for key, pattern, question_text, options, counter_args in AMBIGUITY_TRIGGERS:
        if pattern.search(task_description):
            questions.append({
                "category": key,
                "question": question_text,
                "options": options,
                "recommended": options[0],
                "counter_arguments": counter_args,
                "recommended_counter_argument": counter_args.get(options[0], ""),
            })
            if len(questions) >= 3:
                break

    # If no specific keyword triggered, but task is open or short, generate default grounding question
    if not questions and len(task_description.split()) < 8:
        default_opts = [
            "(Recommended) Tối thiểu hóa blast radius, dùng standard library và giữ nguyên interface hiện tại",
            "Mở rộng thêm abstraction layer mới để tái sử dụng lâu dài",
        ]
        default_counters = {
            default_opts[0]: "Counter-Argument: Khó mở rộng thêm tính năng đa dạng trong tương lai nếu phạm vi bị ép quá hẹp.",
            default_opts[1]: "Counter-Argument: Tăng số lượng files và nguy cơ over-engineering cho một tác vụ đơn giản."
        }
        questions.append({
            "category": "architecture_scope",
            "question": f"Định hướng phạm vi triển khai cho: '{task_description}'?",
            "options": default_opts,
            "recommended": default_opts[0],
            "counter_arguments": default_counters,
            "recommended_counter_argument": default_counters[default_opts[0]],
        })

    return questions


def extract_file_signatures(filepath: str) -> Dict[str, Any]:
    """Extracts top-level class and function signatures with AST Structural Anchors across Python, TS, JS, Java, Groovy."""
    if not os.path.isfile(filepath):
        return {"exists": False, "signatures": []}

    try:
        res = parse_polyglot_signatures(filepath)
        sigs = res.get("signatures", [])
        return {
            "exists": True,
            "language": res.get("language", "unknown"),
            "signatures": sigs[:5],
            "symbols": res.get("symbols", [])
        }
    except Exception as e:
        return {"exists": True, "error": str(e), "signatures": []}


def scaffold_super_plan(
    task: str,
    target_files: Optional[List[str]] = None,
    tournament: bool = False,
    tier: Optional[PlanningTier] = None,
) -> str:
    """Generates a grounded Spec-Driven Super-Plan markdown skeleton."""
    if not target_files:
        target_files = ["src/target_module.py", "tests/test_target_module.py"]

    if tier is None:
        tier, metric = calculate_risk_routing(task, target_files, repo_root=_REPO_ROOT)
    else:
        _, metric = calculate_risk_routing(task, target_files, repo_root=_REPO_ROOT)

    file_rows: List[str] = []
    for f in target_files:
        rel = os.path.relpath(f, _REPO_ROOT) if os.path.isabs(f) else f
        full_path = os.path.join(_REPO_ROOT, rel)
        info = extract_file_signatures(full_path)
        if info.get("exists") and info.get("signatures"):
            raw_sig = info["signatures"][0]
            m_anchor = re.search(r"\[AST:\s*([^\]]+)\]", raw_sig)
            if m_anchor:
                clean_sym = re.sub(r":L\d+(-L?\d+)?", "", m_anchor.group(1)).strip()
                anchor_str = f"(AST: {clean_sym})"
            else:
                anchor = raw_sig.split()[-1]
                anchor_str = anchor.replace("[", "(").replace("]", ")")
            action = "[MODIFY]"
        elif info.get("exists"):
            anchor_str = "(AST: module_root)"
            action = "[MODIFY]"
        else:
            anchor_str = "(New)"
            action = "[CREATE]"
        file_rows.append(f"| `{action}` | `{rel}` {anchor_str} | Core implementation or test coverage |")

    files_table = "\n".join(file_rows)

    # Tier 0 Fast-Track Micro-Plan: bypass heavy tournament and red-teaming for sub-10s turnaround
    if tier == PlanningTier.TIER_0_FAST and not tournament:
        return f"""<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Fast-Track Micro-Plan: {task}

> **Reference Protocol:** [AGENTS.md §5](AGENTS.md) (Tier 0 Fast-Track: RiskScore {metric.risk_score} < 0.35)
> **Ambiguity Gate Status:** Exempt (Low complexity, blast radius <= 2 files)
> 📝 **Plan Changelog (v1.0):** Initial fast-track plan.

---

## 1. Affected Files & Blast Radius

### Target Files & Structural Anchors
| Action | File Path & Structural Anchor | Scope & Responsibility |
|---|---|---|
{files_table}

---

## 2. Data Flow & Interface Signatures

```python
# Minimal complete interface
def execute_quick_fix() -> bool:
    ...
```

---

## 3. Atomic Milestones (Execution DAG)

### Milestone 1: Implementation & Verification [PARALLEL_OK]
- **Node ID:** `M1` | **depends_on:** `[]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 2):** `{target_files[0] if target_files else 'src/types.py'}`
- **Write Set:** `['{target_files[0] if target_files else 'src/types.py'}']`
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if out-of-scope files touched | Rollback: `git checkout -- {target_files[0] if target_files else 'src/types.py'}`
- **Pass Gate:** `pytest {target_files[1] if len(target_files) > 1 else 'tests/'}`

---

## 4. Verification Matrix ("Define the Exam in the Plan")

| ID | Test Scenario | Input / Precondition | Expected Output / Assertion | Verification Command |
|---|---|---|---|---|
| **TC-01** | Happy Path | Valid input | Success, exit code 0 | `pytest {target_files[1] if len(target_files) > 1 else 'tests/'}` |
| **TC-02** | Boundary / Negative | Handled gracefully | No unhandled exception | `pytest {target_files[1] if len(target_files) > 1 else 'tests/'}` |
"""

    include_tournament = tournament or tier == PlanningTier.TIER_2_DEEP
    tournament_block = ""
    if include_tournament:
        tournament_block = """
## 0. Orthogonal Architectural Tournament (Trade-off Matrix)

| Evaluation Criteria | 🏛️ Branch A: Minimalist | 📐 Branch B: Clean Architecture | ⚡ Branch C: High Performance |
|---|---|---|---|
| **Core Philosophy** | Minimal code delta, zero new files, stdlib only | Explicit interface separation & adapter pattern | Async non-blocking, zero-copy, cached hot-path |
| **Blast Radius** | Minimal (<= 2 existing files touched) | Modular (isolated domain components) | Targeted (algorithmic optimization) |
| **Regression Risk** | Lowest (preserves 100% legacy contracts) | Low (tested via clean mock adapters) | Medium (requires concurrency verification) |
| **Execution Speed** | Standard | High maintainability | Maximum sub-millisecond throughput |
| **Selection Verdict** | **(Recommended)** Minimalist & Low-Risk | Best for extensible domain features | Best for high-traffic SLA bottlenecks |

> **Ruling:** Selected Branch: **[Branch A: Minimalist]** with Branch B interface contracts.

---
"""

    return f"""<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Spec-Driven Implementation Plan: {task}

> **Reference Protocol:** [AGENTS.md §5](AGENTS.md), [standards/qa-process/plan-protocol.md](standards/qa-process/plan-protocol.md)
> **Ambiguity Gate Status:** Resolved (Architectural choices confirmed upfront)
> 📝 **Plan Changelog (v1.0):**
> - Initial super-plan drafted with verified grounding and DAG constraints.
{tournament_block}
---

## 1. Affected Files & Blast Radius

### Target Files & Structural Anchors
| Action | File Path & Structural Anchor | Scope & Responsibility |
|---|---|---|
{files_table}

### Blast Radius & Downstream Dependencies
- **Direct Callers:** Downstream modules referencing modified symbols.
- **Downstream Tests:** Targeted regression suite.
- **Regression Risk:** Low (Strict backward compatibility adapter enforced).

---

## 2. Data Flow & Interface Signatures

> **Anti-Full-Code Invariant:** Define ONLY DTOs, schemas, and function signatures with type contracts. Full implementation body is strictly deferred to the execution phase.

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ExecutionInputDTO:
    task_id: str
    payload: dict
    dry_run: bool = False

@dataclass(frozen=True)
class ExecutionResultDTO:
    success: bool
    message: str
    error_code: Optional[str] = None

def execute_operation(input_data: ExecutionInputDTO) -> ExecutionResultDTO:
    \"\"\"Executes {task} idempotently.
    Guarantees:
      - Validates schema before mutation.
      - Zero unhandled exceptions.
    Raises:
      - ValueError: on malformed task_id.
    \"\"\"
    ...
```

---

## 3. Atomic Milestones (Execution DAG)

### Milestone 1: Interfaces, Types & Test Harness [PARALLEL_OK]
- **Node ID:** `M1` | **depends_on:** `[]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 2):** `{target_files[0] if target_files else 'src/types.py'}`
- **Write Set:** `['{target_files[0] if target_files else 'src/types.py'}']`
- **Typed Interface Manifest:**
  - **consumes:** `[]`
  - **produces:** `[{{"contract": "ExecutionResultDTO", "fields": {{"success": "bool"}}}}]`
  - **invariants:** `["idempotent(task_id)", "timeout_ms <= 5000"]`
- **Goal:** Define DTOs, type contracts, and compile check.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if out-of-scope files touched | Rollback: `git checkout -- {target_files[0] if target_files else 'src/types.py'}`
- **Rollback Hook:** `git checkout -- {target_files[0] if target_files else 'src/types.py'}`
- **Pass Gate:** `python3 -m py_compile {target_files[0] if target_files else 'src/types.py'}`

### Milestone 2: Core Business Logic & Unit Tests
- **Node ID:** `M2` | **depends_on:** `[M1]`
- **Compute Tier:** `[Model: Pro / Reasoning | Thinking: High | Best-of-3]`
- **Files Modified (Max 2):** `{target_files[1] if len(target_files) > 1 else 'tests/test_feature.py'}`
- **Write Set:** `['{target_files[1] if len(target_files) > 1 else 'tests/test_feature.py'}']`
- **Typed Interface Manifest:**
  - **consumes:** `[{{"contract": "ExecutionResultDTO"}}]`
  - **produces:** `[{{"contract": "ExecutionIntegrationResult", "fields": {{"verified": "bool"}}}}]`
  - **invariants:** `["zero_unhandled_exceptions"]`
- **Goal:** Implement core logic satisfying deterministic test scenarios.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if new dependency introduced | Rollback: `git checkout -- {target_files[1] if len(target_files) > 1 else 'tests/test_feature.py'}`
- **Rollback Hook:** `git checkout -- {target_files[1] if len(target_files) > 1 else 'tests/test_feature.py'}`
- **Pass Gate:** `pytest {target_files[1] if len(target_files) > 1 else 'tests/test_feature.py'}`

---

## 4. Verification Matrix ("Define the Exam in the Plan")

| ID | Test Scenario | Input / Precondition | Expected Output / Assertion | Verification Command |
|---|---|---|---|---|
| **TC-01** | Happy Path | `ExecutionInputDTO(task_id="T1", payload={{"valid": True}})` | `ExecutionResultDTO.success == True` | `pytest tests/ -k "test_happy_path"` |
| **TC-02** | Boundary (Empty Input) | `ExecutionInputDTO(task_id="", payload={{}})` | Raises `ValueError` handled gracefully | `pytest tests/ -k "test_empty_input"` |
| **TC-03** | Error Handling / Timeout | Downstream dependency fails | Fallback triggered, error logged | `pytest tests/ -k "test_timeout_fallback"` |

---

## 5. Tri-Vulnerability Self-Critique & Mitigations

1. **Vulnerability 1 (Concurrency / Race Condition):**
   - *Risk:* Concurrent duplicate requests causing state drift.
   - *Mitigation:* Enforce check-and-set idempotency token validation.
2. **Vulnerability 2 (Resource Extremes / Timeout):**
   - *Risk:* Unbounded execution or network stall.
   - *Mitigation:* Apply strict 5s timeout guard with graceful fallback.
3. **Vulnerability 3 (Blast Radius / Backward Compatibility):**
   - *Risk:* Breaking changes affecting legacy callers.
   - *Mitigation:* Maintain parameter defaults and adapter wrapper.

---

## 6. Rollback & State-Migration Matrix (Zero-Downtime Guard)

| Phase | Trigger Scenario | Mitigation / Dual-mode | Rollback Command |
|---|---|---|---|
| State Migration | Schema/state corruption | Atomic transaction with checkpoint | `git checkout -- <file>` |
| Service Cutover | High error rate (> 1%) | Instant flag toggle fallback | Revert commit or toggle feature flag |

---

## 7. Execution Transition & Plan Harvesting
- **Clean Context Handoff:** Execute via clean context session or subagent with only this plan + AST slices.
- **Surgical Patch Protocol:** Edit only targeted blocks upon feedback with Changelog update; forbid whole-file regenerations.
- **Plan Harvesting Hook:** Upon passing all 11 DoD Quality Gates, harvest decisions into `docs/adr/`.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Super-Plan Engine: Automated scaffold, ambiguity gate, and validator")
    subparsers = parser.add_subparsers(dest="command", help="Available sub-commands")

    # route sub-command
    route_parser = subparsers.add_parser("route", help="Determines deterministic planning tier and risk score")
    route_parser.add_argument("--task", required=True, help="Task description")
    route_parser.add_argument("--files", nargs="*", help="Candidate target files")
    route_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    # ambiguity-check sub-command
    amb_parser = subparsers.add_parser("ambiguity-check", help="Detects architectural forks and outputs MCQs")
    amb_parser.add_argument("--task", required=True, help="Task description")
    amb_parser.add_argument("--non-interactive", "--auto-recommend", action="store_true", dest="auto_recommend", help="Headless CI mode: auto-selects (Recommended) choices without blocking")
    amb_parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    # scaffold sub-command
    scaff_parser = subparsers.add_parser("scaffold", help="Generates grounded implementation plan draft")
    scaff_parser.add_argument("--task", required=True, help="Task description")
    scaff_parser.add_argument("--files", nargs="*", help="List of candidate files")
    scaff_parser.add_argument("--tier", choices=["fast", "standard", "deep", "auto"], default="auto", help="Planning tier override (default auto)")
    scaff_parser.add_argument("--tournament", action="store_true", help="Generate 3-way orthogonal tournament Trade-off Matrix")
    scaff_parser.add_argument("--output", help="Optional output filepath to save plan")
    scaff_parser.add_argument("--json", action="store_true", help="Output metadata in JSON format")

    # validate sub-command
    val_parser = subparsers.add_parser("validate", help="Validates an implementation plan")
    val_parser.add_argument("--file", required=True, help="Path to markdown plan")
    val_parser.add_argument("--mode", choices=["standard", "super", "auto"], default="super")
    val_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    # mutate sub-command
    mut_parser = subparsers.add_parser("mutate", help="Runs mechanical plan mutation testing")
    mut_parser.add_argument("--file", required=True, help="Path to markdown plan")
    mut_parser.add_argument("--threshold", type=float, default=90.0, help="Pass gate threshold (default 90.0)")
    mut_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    args = parser.parse_args()

    if args.command == "route":
        tier, metric = calculate_risk_routing(args.task, args.files, repo_root=_REPO_ROOT)
        if args.json:
            print(json.dumps({
                "task": args.task,
                "tier": tier.value,
                "risk_score": metric.risk_score,
                "metrics": {
                    "fan_in": metric.fan_in,
                    "cross_boundary": metric.cross_boundary,
                    "state_mutation": metric.state_mutation,
                    "history_drift": metric.history_drift,
                }
            }, indent=2))
        else:
            print(f"[RISK ROUTING] Task: '{args.task}'")
            print(f"  -> Planning Tier: {tier.value} (RiskScore: {metric.risk_score})")
            print(f"  -> Breakdown: FanIn={metric.fan_in}, CrossBoundary={metric.cross_boundary}, StateMutation={metric.state_mutation}, HistoryDrift={metric.history_drift}")
        return 0

    elif args.command == "ambiguity-check":
        questions = check_ambiguities(args.task)
        if getattr(args, "auto_recommend", False):
            if questions:
                auto_choices = [q['options'][0] for q in questions]
                if args.json:
                    print(json.dumps({
                        "task": args.task,
                        "has_ambiguity": True,
                        "auto_recommended": True,
                        "selected": auto_choices,
                        "questions": questions
                    }, indent=2))
                else:
                    print(f"[AMBIGUITY GATE AUTO-RECOMMEND] Headless mode auto-selected {len(questions)} default choice(s):")
                    for idx, q in enumerate(questions, 1):
                        print(f"  {idx}. {q['question']} -> {q['options'][0]}")
            else:
                if args.json:
                    print(json.dumps({"task": args.task, "has_ambiguity": False, "auto_recommended": True, "questions": []}, indent=2))
                else:
                    print("[AMBIGUITY GATE CLEAR] Task has unambiguous constraints. Ready for planning.")
            return 0

        if args.json:
            print(json.dumps({"task": args.task, "has_ambiguity": len(questions) > 0, "questions": questions}, indent=2))
        else:
            if questions:
                print(f"[AMBIGUITY GATE TRIGGERED] Found {len(questions)} architectural decision fork(s):")
                for idx, q in enumerate(questions, 1):
                    print(f"\n{idx}. {q['question']}")
                    for opt in q['options']:
                        counter = q.get('counter_arguments', {}).get(opt, "")
                        print(f"   - {opt}")
                        if counter:
                            print(f"     ⚠️ {counter}")
            else:
                print("[AMBIGUITY GATE CLEAR] Task has unambiguous constraints. Ready for planning.")
        return 0

    elif args.command == "scaffold":
        tier_arg = getattr(args, "tier", "auto")
        chosen_tier = None
        if tier_arg == "fast":
            chosen_tier = PlanningTier.TIER_0_FAST
        elif tier_arg == "standard":
            chosen_tier = PlanningTier.TIER_1_STANDARD
        elif tier_arg == "deep":
            chosen_tier = PlanningTier.TIER_2_DEEP

        plan_md = scaffold_super_plan(args.task, args.files, tournament=getattr(args, "tournament", False), tier=chosen_tier)
        if args.output:
            out_dir = os.path.dirname(os.path.abspath(args.output))
            os.makedirs(out_dir, exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(plan_md)
            print(f"[SCAFFOLD COMPLETE] Saved grounded plan to {args.output}")
        elif args.json:
            print(json.dumps({"task": args.task, "plan_markdown": plan_md}, indent=2))
        else:
            print(plan_md)
        return 0

    elif args.command == "validate":
        if not os.path.isfile(args.file):
            print(f"Error: File not found: {args.file}")
            return 1
        with open(args.file, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        passed, issues, details = validate_plan_content(content, filename=args.file, mode=args.mode)
        if args.json:
            print(json.dumps({"passed": passed, "issues": issues, "details": details}, indent=2))
        else:
            status_str = "PASS" if passed else "FAIL"
            print(f"[{status_str}] {args.file}")
            for issue in issues:
                print(f"  - [X] {issue}")
        return 0 if passed else 1

    elif args.command == "mutate":
        if not os.path.isfile(args.file):
            print(f"Error: File not found: {args.file}")
            return 1
        with open(args.file, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        report = run_plan_mutation_audit(content, threshold=args.threshold)
        if args.json:
            print(json.dumps(asdict(report), indent=2))
        else:
            status_str = "PASS" if report.passed else "FAIL"
            print(f"[{status_str}] Plan Mutation Kill Score: {report.kill_score}% ({report.killed_mutants}/{report.total_mutants})")
            for m, res in report.details.items():
                k_str = "[KILL]" if res["killed"] else "[SURVIVE]"
                print(f"  {k_str} {m}: {res['verdict']}")
        return 0 if report.passed else 1

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
