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
import ast
import json
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

# Enforce UTF-8 stdout/stderr encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


AMBIGUITY_TRIGGERS = [
    ("storage", re.compile(r"\b(?:database|db|cache|redis|in-memory|storage|persist|lưu\s+trữ)\b", re.I),
     "Lựa chọn cơ chế lưu trữ / cache cho giải pháp?",
     ["(Recommended) In-Memory với LRU cache và thread-safety lock", "Persistent SQLite / File-based persistence", "Redis / External Key-Value store"]),
    ("concurrency", re.compile(r"\b(?:async|sync|thread|concurrency|queue|background|bất\s+đồng\s+bộ|đa\s+luồng)\b", re.I),
     "Mô hình xử lý đồng thời (concurrency model) mong muốn?",
     ["(Recommended) Bounded thread-pool với retry exponential backoff", "Native asyncio event-loop", "Single-threaded synchronous with timeout guard"]),
    ("api_contract", re.compile(r"\b(?:api|endpoint|contract|interface|breaking|tương\s+thích|giao\s+diện)\b", re.I),
     "Mức độ đảm bảo tính tương thích ngược của Interface?",
     ["(Recommended) 100% Backward-compatible adapter (giữ nguyên legacy caller)", "Deprecate warning với version bump", "Hard break with caller migration"]),
    ("performance_sla", re.compile(r"\b(?:speed|latency|scale|fast|performance|hiệu\s+năng|tốc\s+độ)\b", re.I),
     "Ưu tiên chính giữa Tốc độ thực thi và Tính nhất quán?",
     ["(Recommended) Tính nhất quán (Strict Consistency / Zero Data Loss)", "Tốc độ tối đa (Sub-millisecond low-latency, eventual consistency)", "Cân bằng với Circuit Breaker"]),
]


def check_ambiguities(task_description: str) -> List[Dict[str, Any]]:
    """Analyzes task description to identify architectural forks and ambiguity questions."""
    questions: List[Dict[str, Any]] = []

    for key, pattern, question_text, options in AMBIGUITY_TRIGGERS:
        if pattern.search(task_description):
            questions.append({
                "category": key,
                "question": question_text,
                "options": options,
                "recommended": options[0],
            })
            if len(questions) >= 3:
                break

    # If no specific keyword triggered, but task is open or short, generate default grounding question
    if not questions and len(task_description.split()) < 8:
        questions.append({
            "category": "architecture_scope",
            "question": f"Định hướng phạm vi triển khai cho: '{task_description}'?",
            "options": [
                "(Recommended) Tối thiểu hóa blast radius, dùng standard library và giữ nguyên interface hiện tại",
                "Mở rộng thêm abstraction layer mới để tái sử dụng lâu dài",
            ],
            "recommended": "(Recommended) Tối thiểu hóa blast radius, dùng standard library và giữ nguyên interface hiện tại",
        })

    return questions


def extract_file_signatures(filepath: str) -> Dict[str, Any]:
    """Extracts top-level class and function signatures from a Python file using AST."""
    if not os.path.isfile(filepath):
        return {"exists": False, "signatures": []}

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
        sigs: List[str] = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                line = node.lineno
                end_line = getattr(node, "end_lineno", line + 10)
                sigs.append(f"def {node.name}(...) [L{line}-L{end_line}]")
            elif isinstance(node, ast.ClassDef):
                line = node.lineno
                end_line = getattr(node, "end_lineno", line + 20)
                sigs.append(f"class {node.name} [L{line}-L{end_line}]")
        return {"exists": True, "signatures": sigs[:5]}
    except Exception as e:
        return {"exists": True, "error": str(e), "signatures": []}


def scaffold_super_plan(task: str, target_files: Optional[List[str]] = None, tournament: bool = False) -> str:
    """Generates a grounded Spec-Driven Super-Plan markdown skeleton."""
    if not target_files:
        target_files = ["src/target_module.py", "tests/test_target_module.py"]

    file_rows: List[str] = []
    for f in target_files:
        rel = os.path.relpath(f, _REPO_ROOT) if os.path.isabs(f) else f
        full_path = os.path.join(_REPO_ROOT, rel)
        info = extract_file_signatures(full_path)
        if info.get("exists") and info.get("signatures"):
            anchor = info["signatures"][0].split()[-1]  # e.g. [L10-L25]
            anchor_str = anchor.replace("[", "(").replace("]", ")")
            action = "[MODIFY]"
        elif info.get("exists"):
            anchor_str = "(L1-L50)"
            action = "[MODIFY]"
        else:
            anchor_str = "(New)"
            action = "[CREATE]"
        file_rows.append(f"| `{action}` | `{rel}` {anchor_str} | Core implementation or test coverage |")

    files_table = "\n".join(file_rows)

    tournament_block = ""
    if tournament:
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

> **Reference Protocol:** [AGENTS.md §5](AGENTS.md), [ai-agents/workflows/super-plan.md](ai-agents/workflows/super-plan.md)
> **Ambiguity Gate Status:** Resolved (Architectural choices confirmed upfront)
> 📝 **Plan Changelog (v1.0):**
> - Initial super-plan drafted with verified grounding and DAG constraints.
{tournament_block}
---

## 1. Affected Files & Blast Radius

### Target Files & Line Anchors
| Action | File Path & Line Anchor | Scope & Responsibility |
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
- **Goal:** Define DTOs, type contracts, and compile check.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if out-of-scope files touched | Rollback: `git checkout -- {target_files[0] if target_files else 'src/types.py'}`
- **Pass Gate:** `python3 -m py_compile {target_files[0] if target_files else 'src/types.py'}`

### Milestone 2: Core Business Logic & Unit Tests
- **Node ID:** `M2` | **depends_on:** `[M1]`
- **Compute Tier:** `[Model: Pro / Reasoning | Thinking: High | Best-of-3]`
- **Files Modified (Max 2):** `{target_files[1] if len(target_files) > 1 else 'tests/test_feature.py'}`
- **Goal:** Implement core logic satisfying deterministic test scenarios.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if new dependency introduced | Rollback: `git checkout -- {target_files[1] if len(target_files) > 1 else 'tests/test_feature.py'}`
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

    # ambiguity-check sub-command
    amb_parser = subparsers.add_parser("ambiguity-check", help="Detects architectural forks and outputs MCQs")
    amb_parser.add_argument("--task", required=True, help="Task description")
    amb_parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    # scaffold sub-command
    scaff_parser = subparsers.add_parser("scaffold", help="Generates grounded implementation plan draft")
    scaff_parser.add_argument("--task", required=True, help="Task description")
    scaff_parser.add_argument("--files", nargs="*", help="List of candidate files")
    scaff_parser.add_argument("--tournament", action="store_true", help="Generate 3-way orthogonal tournament Trade-off Matrix")
    scaff_parser.add_argument("--output", help="Optional output filepath to save plan")
    scaff_parser.add_argument("--json", action="store_true", help="Output metadata in JSON format")

    # validate sub-command
    val_parser = subparsers.add_parser("validate", help="Validates an implementation plan")
    val_parser.add_argument("--file", required=True, help="Path to markdown plan")
    val_parser.add_argument("--mode", choices=["standard", "super", "auto"], default="super")
    val_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    args = parser.parse_args()

    if args.command == "ambiguity-check":
        questions = check_ambiguities(args.task)
        if args.json:
            print(json.dumps({"task": args.task, "has_ambiguity": len(questions) > 0, "questions": questions}, indent=2))
        else:
            if questions:
                print(f"[AMBIGUITY GATE TRIGGERED] Found {len(questions)} architectural decision fork(s):")
                for idx, q in enumerate(questions, 1):
                    print(f"\n{idx}. {q['question']}")
                    for opt in q['options']:
                        print(f"   - {opt}")
            else:
                print("[AMBIGUITY GATE CLEAR] Task has unambiguous constraints. Ready for planning.")
        return 0

    elif args.command == "scaffold":
        plan_md = scaffold_super_plan(args.task, args.files, tournament=getattr(args, "tournament", False))
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

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
