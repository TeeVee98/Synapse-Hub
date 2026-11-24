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
from typing import Any, Dict, List, Optional, Set, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.lint.plan_schema_sentinel import validate_plan_content
from tools.lint.plan_mutator import run_plan_mutation_audit
from tools.context.polyglot_ast_parser import parse_polyglot_signatures
from tools.context.call_graph_indexer import get_or_build_call_graph
from tools.reasoning.step_back_engine import StepBackEngine
from tools.reasoning.self_discover_engine import SelfDiscoverEngine
from tools.reasoning.dynamic_budget_engine import DynamicBudgetEngine
from tools.design.dag_self_healer import parse_plan_to_dag
from tools.design.plan_harvester import harvest_plan
from tools.ai.textgrad_optimizer import TextGradOptimizer

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


def _get_planning_config(repo_root: str) -> Dict[str, Any]:
    cfg_path = os.path.join(repo_root, "synapse.config.json")
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("planning", {})
        except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
            pass
    return {}


def tokenize_text(text: str) -> Set[str]:
    return set(re.split(r"[^a-z0-9]+", text.lower())) - {""}


HARD_CRITICAL_PATHS = {
    "auth", "authn", "authz", "authentication", "authorization", "oauth", "jwt",
    "security", "schema", "database", "migration", "payment", "transaction"
}

SOFT_CRITICAL_PATHS = {
    "core", "runner", "base_page", "middleware", "invariant"
}


@dataclass(frozen=True)
class RiskMetricDTO:
    fan_in: int
    cross_boundary: bool
    state_mutation: bool
    history_drift: float
    critical_path: bool = False
    blast_radius: int = 0
    fan_cap: int = 32
    hard_critical: bool = False
    graph_unknown: bool = False

    @property
    def risk_score(self) -> float:
        eff_fan_in = self.blast_radius if self.blast_radius > 0 else self.fan_in
        cap = max(self.fan_cap, 2)
        blast = min(1.0, math.log2(1 + eff_fan_in) / math.log2(1 + cap))
        base = (
            0.35 * blast +
            0.25 * float(self.cross_boundary) +
            0.25 * float(self.state_mutation) +
            0.15 * min(1.0, max(0.0, self.history_drift))
        )
        if self.hard_critical:
            base = max(base, 0.70)
        elif self.critical_path:
            base = max(base, 0.40)
        if self.graph_unknown:
            base = max(base, 0.40)
        return round(min(1.0, max(0.0, base)), 3)


def calculate_risk_routing(
    task: str,
    target_files: Optional[List[str]] = None,
    repo_root: str = _REPO_ROOT
) -> Tuple[PlanningTier, RiskMetricDTO]:
    """Calculates deterministic RiskScore (0 LLM token) and routes to optimal planning tier."""
    files = target_files or []
    cfg = _get_planning_config(repo_root)
    hard_paths = set(cfg.get("hard_critical_paths", HARD_CRITICAL_PATHS))
    soft_paths = set(cfg.get("soft_critical_paths", SOFT_CRITICAL_PATHS))
    fan_cap = int(cfg.get("fan_cap", 32))

    task_tokens = tokenize_text(task)
    file_tokens: Set[str] = set()
    for f in files:
        file_tokens.update(tokenize_text(f))
    all_tokens = task_tokens | file_tokens

    # 1. CrossBoundary detection: touches Public API, DB schema, Auth, or Shared Standards
    cross_boundary_keywords = {
        "api", "endpoint", "schema", "migration", "auth", "token", "jwt",
        "credential", "permission", "shared", "public", "protocol", "standard"
    }
    cross_boundary = bool(all_tokens & cross_boundary_keywords)
    for f in files:
        f_lower = f.lower().replace("\\", "/")
        if any(kw in f_lower for kw in ("api", "schema", "auth", "standards/", "models/", "routes/")):
            cross_boundary = True
            break

    # 2. StateMutation detection: concurrency, lock, db write, payments, cache flush
    state_mutation_keywords = {
        "concurrency", "async", "thread", "mutex", "lock", "race", "state",
        "mutate", "database", "db", "migration", "ledger", "payment", "transaction", "queue"
    }
    state_mutation = bool(all_tokens & state_mutation_keywords)

    # 3. Critical Path detection via whole-word token matching
    hard_critical = bool(all_tokens & hard_paths)
    soft_critical = bool(all_tokens & soft_paths)
    critical_path = hard_critical or soft_critical

    # 4. HistoryDrift from project_state.json
    history_drift = 0.1
    state_path = os.path.join(repo_root, "project_state.json")
    if os.path.isfile(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as fh:
                sdata = json.load(fh)
            history_drift = float(sdata.get("plan_calibration", {}).get("last_drift_ratio", 0.1))
        except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
            history_drift = 0.1

    # 5. FanIn & Blast Radius calculation: indexed graph of callers/references in codebase
    fan_in = 0
    graph_unknown = False
    try:
        graph = get_or_build_call_graph(repo_root)
        for f in files:
            fan_in += graph.get_fan_in(f)
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        graph_unknown = bool(files)
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
        fan_cap=fan_cap,
        hard_critical=hard_critical,
        graph_unknown=graph_unknown,
    )

    score = metric.risk_score
    if score < 0.35 and not critical_path and blast_radius < 5 and len(files) <= 2:
        tier = PlanningTier.TIER_0_FAST
    elif score < 0.70 and blast_radius < 10:
        tier = PlanningTier.TIER_1_STANDARD
    else:
        tier = PlanningTier.TIER_2_DEEP

    return tier, metric


AMBIGUITY_DEFINITIONS = [
    (
        "storage",
        re.compile(r"\b(?:database|db|cache|redis|in-memory|storage|persist)\b", re.I),
        "Which storage or caching mechanism should be selected for this solution?",
        [
            ("in_memory", "In-Memory with LRU cache and thread-safety lock",
             "Counter-Argument: Data lost on process restart; memory overhead if cache is unbounded."),
            ("sqlite", "Persistent SQLite / File-based persistence",
             "Counter-Argument: Increased disk I/O latency; risk of table lock under concurrent multi-process writes."),
            ("redis", "Redis / External Key-Value store",
             "Counter-Argument: Introduces external dependency; network latency and connection timeout risks.")
        ],
        {
            "in_memory": ("in-memory", "lru", "ephemeral", "zero dependency", "no dependency"),
            "sqlite": ("sqlite", "file-based", "relational", "postgres", "postgresql", "mysql"),
            "redis": ("redis", "memcached", "external", "distributed", "cluster")
        }
    ),
    (
        "concurrency",
        re.compile(r"\b(?:async|sync|thread|concurrency|queue|background|worker)\b", re.I),
        "Which concurrency model should be adopted?",
        [
            ("thread_pool", "Bounded thread-pool with exponential backoff",
             "Counter-Argument: Harder to debug race conditions; thread context-switch overhead."),
            ("asyncio", "Native asyncio event-loop",
             "Counter-Argument: Easily blocks on third-party synchronous calls; requires migrating callers to async."),
            ("sync", "Single-threaded synchronous with timeout guard",
             "Counter-Argument: Does not leverage multi-core compute; throughput drops on blocking I/O.")
        ],
        {
            "asyncio": ("async", "asyncio", "event-loop", "coroutine"),
            "thread_pool": ("thread", "thread-pool", "worker", "pool", "parallel"),
            "sync": ("sync", "synchronous", "single-thread", "blocking")
        }
    ),
    (
        "api_contract",
        re.compile(r"\b(?:api|endpoint|contract|interface|breaking|compatibility)\b", re.I),
        "What level of interface backward compatibility is guaranteed?",
        [
            ("backward_compat", "100% Backward-compatible adapter (preserves legacy callers)",
             "Counter-Argument: Accumulates technical debt and long-term adapter maintenance."),
            ("deprecate_warning", "Deprecation warning with semantic version bump",
             "Counter-Argument: Legacy callers may ignore runtime warnings, complicating deprecation."),
            ("hard_break", "Hard break with coordinated caller migration",
             "Counter-Argument: Breaks downstream callers not synchronized with this release.")
        ],
        {
            "backward_compat": ("backward", "compatible", "preserve", "legacy", "adapter"),
            "deprecate_warning": ("deprecate", "warning", "bump"),
            "hard_break": ("breaking", "hard break", "migration", "overhaul")
        }
    ),
    (
        "performance_sla",
        re.compile(r"\b(?:speed|latency|scale|fast|performance|sla|throughput)\b", re.I),
        "What is the primary trade-off priority between execution speed and consistency?",
        [
            ("consistency", "Strict Consistency (Zero Data Loss)",
             "Counter-Argument: Reduced write throughput on hot execution paths."),
            ("speed", "Maximum Speed (Sub-millisecond low-latency, eventual consistency)",
             "Counter-Argument: Stale read window; potential state reconciliation anomalies."),
            ("balanced", "Balanced with Circuit Breaker",
             "Counter-Argument: Increased configuration complexity for trip thresholds and half-open states.")
        ],
        {
            "consistency": ("consistency", "zero data loss", "strict", "atomic", "acid"),
            "speed": ("speed", "latency", "sub-millisecond", "low-latency", "throughput", "eventual"),
            "balanced": ("balanced", "circuit breaker", "hybrid")
        }
    ),
    (
        "auth_security",
        re.compile(r"\b(?:auth|token|jwt|session|oauth|security|credential)\b", re.I),
        "Which authentication or authorization mechanism should be enforced?",
        [
            ("jwt", "Stateless cryptographic JWT tokens with signature validation",
             "Counter-Argument: Cannot immediately revoke token before expiration without blacklist."),
            ("session", "Server-side stateful session store",
             "Counter-Argument: Requires shared session storage in multi-instance deployments."),
            ("api_key", "Static API Key / Secret Token header verification",
             "Counter-Argument: High exposure risk if leaked; lacks fine-grained expiration.")
        ],
        {
            "jwt": ("jwt", "stateless", "bearer"),
            "session": ("session", "cookie", "stateful"),
            "api_key": ("api_key", "static", "header", "secret")
        }
    ),
]


def check_ambiguities(
    task_description: str,
    invariants: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Analyzes task description to identify architectural forks with dynamic recommendations."""
    questions: List[Dict[str, Any]] = []
    inv_text = " ".join(invariants or []).lower()
    full_context = f"{task_description.lower()} {inv_text}"

    for category, pattern, question_text, options_data, keyword_maps in AMBIGUITY_DEFINITIONS:
        if pattern.search(task_description):
            chosen_key = None
            for opt_key, kws in keyword_maps.items():
                if any(kw in full_context for kw in kws):
                    chosen_key = opt_key
                    break

            resolved_by_invariant = chosen_key is not None
            if not chosen_key and options_data:
                chosen_key = options_data[0][0]

            counter_args = {}
            options = []
            rec_text = None
            rec_counter = ""

            for opt_key, opt_label, counter_arg in options_data:
                counter_args[opt_label] = counter_arg
                counter_args[f"(Recommended) {opt_label}"] = counter_arg
                if opt_key == chosen_key:
                    labeled = f"(Recommended) {opt_label}"
                    options.append(labeled)
                    rec_text = labeled
                    rec_counter = counter_arg
                else:
                    options.append(opt_label)

            if rec_text and rec_text in options:
                options.remove(rec_text)
                options.insert(0, rec_text)

            questions.append({
                "category": category,
                "question": question_text,
                "options": options,
                "recommended": rec_text,
                "resolved_by_invariant": resolved_by_invariant,
                "counter_arguments": counter_args,
                "recommended_counter_argument": rec_counter,
            })
            if len(questions) >= 3:
                break

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


_TIER_TO_FSM_STAGE: Dict[PlanningTier, str] = {
    PlanningTier.TIER_0_FAST: "DISCOVERY",
    PlanningTier.TIER_1_STANDARD: "CODE_SYNTHESIS",
    PlanningTier.TIER_2_DEEP: "AUTOPSY_HEAL",
}


def synthesize_cognitive_planning_brief(
    task: str,
    tier: PlanningTier = PlanningTier.TIER_1_STANDARD,
) -> Dict[str, Any]:
    """Synthesizes Step-Back principles, Self-Discover primitives, and DynamicBudget allocation."""
    normalized_task = (task or "").strip() or "general software task"

    governing_principles: List[str] = []
    try:
        sb_res = StepBackEngine().run(normalized_task)
        raw_principles = sb_res.get("step_back_abstraction", {}).get("governing_principles", [])
        for p in raw_principles:
            name = str(p.get("principle_name", "")).strip()
            inv = str(p.get("core_invariant", "")).strip()
            if name and inv:
                governing_principles.append(f"{name}: {inv}")
            elif name:
                governing_principles.append(name)
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        governing_principles = []
    if not governing_principles:
        governing_principles = [
            "Clean Separation of Concerns: Preserve single responsibility and invariant boundaries."
        ]

    selected_primitives: List[str] = []
    try:
        sd_res = SelfDiscoverEngine().run(normalized_task, top_k=3)
        for mod in sd_res.get("selected_primitives", []):
            mod_id = str(mod.get("id", "")).strip()
            mod_name = str(mod.get("name", "")).strip()
            if mod_id and mod_name:
                selected_primitives.append(f"{mod_id}: {mod_name}")
            elif mod_name or mod_id:
                selected_primitives.append(mod_name or mod_id)
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        selected_primitives = []
    if not selected_primitives:
        selected_primitives = [
            "MOD_FIRST_PRINCIPLES: First Principles Abstraction"
        ]

    fsm_stage = _TIER_TO_FSM_STAGE.get(tier, "DISCOVERY")
    budget = DynamicBudgetEngine.resolve_budget(fsm_stage=fsm_stage)

    return {
        "governing_principles": governing_principles,
        "selected_primitives": selected_primitives,
        "thinking_budget": int(budget.get("thinking_budget", 0)),
        "max_tokens": int(budget.get("max_tokens", 256)),
        "task_category": str(budget.get("task_type", "mechanical")),
    }


def _format_cognitive_grounding_block(brief: Dict[str, Any]) -> str:
    """Formats a compact Cognitive Grounding & Budget markdown block compatible with plan sentinels."""
    principles_str = "; ".join(brief.get("governing_principles", [])[:2])
    primitives_str = ", ".join(brief.get("selected_primitives", [])[:3])
    return (
        "## Cognitive Grounding & Budget\n"
        f"- **Step-Back Principles:** {principles_str}\n"
        f"- **Self-Discover Primitives:** {primitives_str}\n"
        f"- **DynamicBudget Allocation:** category=`{brief['task_category']}` | "
        f"thinking_budget=`{brief['thinking_budget']}` | max_tokens=`{brief['max_tokens']}`"
    )


def _recommend_execution_profile(tier: PlanningTier) -> Tuple[str, str]:
    """Selects a single recommended model and thinking level for the plan tier."""
    if tier == PlanningTier.TIER_0_FAST:
        return (
            "Gemini 4 Hydrogen (Medium)",
            "Low-risk <= 2-file change; Medium thinking balances turnaround speed and accuracy.",
        )
    if tier == PlanningTier.TIER_2_DEEP:
        return (
            "Gemini 4 Neon (High)",
            "High-risk / multi-module DAG; High thinking prevents architectural and concurrency drift.",
        )
    return (
        "Gemini 4 Hydrogen (High)",
        "Standard multi-step Single-Agent /solo plan; High thinking ensures Red->Blue->Purple rigor.",
    )


def scaffold_super_plan(
    task: str,
    target_files: Optional[List[str]] = None,
    tournament: bool = False,
    tier: Optional[PlanningTier] = None,
    execution_mode: str = "solo",
) -> str:
    """Generates a grounded Spec-Driven Super-Plan markdown skeleton."""
    if execution_mode not in ("solo", "teamwork"):
        raise ValueError(
            f"Unsupported execution_mode '{execution_mode}'; expected 'solo' or 'teamwork'."
        )
    is_teamwork = execution_mode == "teamwork"
    parallel_tag = " [PARALLEL_OK]" if is_teamwork else ""

    if not target_files:
        target_files = ["src/target_module.py", "tests/test_target_module.py"]

    if tier is None:
        tier, metric = calculate_risk_routing(task, target_files, repo_root=_REPO_ROOT)
    else:
        _, metric = calculate_risk_routing(task, target_files, repo_root=_REPO_ROOT)

    rec_model, rec_rationale = _recommend_execution_profile(tier)
    mode_banner = (
        "/teamwork (Multi-Worker Parallel on disjoint `[PARALLEL_OK]` milestones)"
        if is_teamwork
        else "Single-Agent Sequential (`/solo`) — One session, one recommended model/thinking level; execute milestones sequentially. Do NOT spawn `swarm` workers or parallel subagents."
    )
    handoff_cmd = (
        '"Read implementation_plan.md and execute via /teamwork"'
        if is_teamwork
        else '"Read implementation_plan.md and execute sequentially via /solo (single-agent mode, no swarm workers)"'
    )

    cognitive_brief = synthesize_cognitive_planning_brief(task, tier)
    cognitive_block = _format_cognitive_grounding_block(cognitive_brief)

    file_rows: List[str] = []
    for f in target_files:
        rel = os.path.relpath(f, _REPO_ROOT) if os.path.isabs(f) else f
        full_path = os.path.join(_REPO_ROOT, rel)
        info = extract_file_signatures(full_path)
        if info.get("exists") and (info.get("symbols") or info.get("signatures")):
            task_tokens = tokenize_text(task)
            chosen_sym_name = None
            symbols = info.get("symbols", [])
            if symbols:
                best_score = 0
                best_sym = None
                for sym in symbols:
                    sym_tokens = tokenize_text(sym.get("name", ""))
                    score = len(task_tokens & sym_tokens)
                    if score > best_score:
                        best_score = score
                        best_sym = sym
                if best_score > 0 and best_sym:
                    chosen_sym_name = best_sym.get("name", "")

            if not chosen_sym_name and info.get("signatures"):
                raw_sig = info["signatures"][0]
                m_anchor = re.search(r"\[AST:\s*([^\]]+)\]", raw_sig)
                if m_anchor:
                    clean_sym = re.sub(r"(\||:)\s*L\d+(-L?\d+)?", "", m_anchor.group(1)).strip()
                    chosen_sym_name = clean_sym
                else:
                    anchor = raw_sig.split()[-1]
                    chosen_sym_name = anchor.replace("[", "").replace("]", "")

            if chosen_sym_name:
                anchor_str = f"(AST: {chosen_sym_name})"
            else:
                anchor_str = "(AST: module_root)"
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
> **Execution Mode:** {mode_banner}
> **Ambiguity Gate Status:** Exempt (Low complexity, blast radius <= 2 files)
> 📝 **Plan Changelog (v1.0):** Initial fast-track plan.

---

{cognitive_block}

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

### Milestone 1: Implementation & Verification{parallel_tag}
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

---

## 5. Execution Handoff
- **Recommended Execution Model & Thinking Level:** `{rec_model}` — {rec_rationale}
- **Clean Context Handoff:** {handoff_cmd}
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
> **Execution Mode:** {mode_banner}
> **Ambiguity Gate Status:** Resolved (Architectural choices confirmed upfront)
> 📝 **Plan Changelog (v1.0):**
> - Initial super-plan drafted with verified grounding and DAG constraints.
{tournament_block}
---

{cognitive_block}

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

### Milestone 1: Interfaces, Types & Test Harness{parallel_tag}
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
- **Execution Mode:** {mode_banner}
- **Recommended Execution Model & Thinking Level:** `{rec_model}` — {rec_rationale}
- **Clean Context Handoff:** {handoff_cmd} (pass only this plan + AST slices).
- **Surgical Patch Protocol:** Edit only targeted blocks upon feedback with Changelog update; forbid whole-file regenerations.
- **Plan Harvesting Hook:** Upon passing all 11 DoD Quality Gates, harvest decisions into `docs/adr/`.
"""


def calibrate_and_refine_plan(
    plan_path: str,
    repo_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Calibrates a markdown plan via DAG parsing, dry-run harvesting, and TextGrad loss evaluation."""
    if not plan_path or not str(plan_path).strip():
        raise FileNotFoundError("Plan path must be a non-empty file path.")

    effective_root = repo_root or _REPO_ROOT
    resolved_path = (
        plan_path
        if os.path.isabs(plan_path) or os.path.isfile(plan_path)
        else os.path.join(effective_root, plan_path)
    )
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"Plan file not found: {resolved_path}")

    with open(resolved_path, "r", encoding="utf-8", errors="replace") as fh:
        plan_content = fh.read()

    executor = parse_plan_to_dag(plan_content)
    dag_nodes = [node.to_dict() for node in executor.nodes.values()]
    ready_nodes = [node.node_id for node in executor.get_ready_nodes()]

    adr_dir = os.path.join(effective_root, "docs", "adr")
    harvest_output_dir = (
        adr_dir
        if os.path.isdir(adr_dir)
        else os.path.dirname(os.path.abspath(resolved_path))
    )
    harvest_ok, harvest_message, harvest_data = harvest_plan(
        resolved_path,
        output_dir=harvest_output_dir,
        dry_run=True,
    )
    calibration = harvest_data.get("calibration", {}) if harvest_ok else {}

    optimizer = TextGradOptimizer(target_path=resolved_path, repo_root=effective_root)
    loss, raw_gradients = optimizer.evaluate_loss(
        plan_content,
        filename=os.path.basename(resolved_path),
    )
    textgrad_loss = float(loss)
    textgrad_gradients = [g.to_dict() for g in raw_gradients]
    textgrad_quality_score = optimizer.compute_quality_score(textgrad_loss)

    if not plan_content.strip():
        status = "EMPTY_PLAN"
    elif textgrad_loss > 0.0:
        status = "NEEDS_REFINEMENT"
    else:
        status = "CALIBRATED"

    return {
        "status": status,
        "plan_path": resolved_path,
        "dag_node_count": len(dag_nodes),
        "dag_nodes": dag_nodes,
        "ready_nodes": ready_nodes,
        "harvest_dry_run": bool(harvest_data.get("dry_run", True)),
        "harvest_message": harvest_message,
        "calibration": calibration,
        "textgrad_loss": textgrad_loss,
        "textgrad_quality_score": textgrad_quality_score,
        "textgrad_gradient_count": len(textgrad_gradients),
        "textgrad_gradients": textgrad_gradients,
    }


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
    scaff_parser.add_argument("--execution-mode", choices=["solo", "teamwork"], default="solo", help="Execution mode: sequential single-agent /solo (default) or multi-worker /teamwork")
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

    # calibrate sub-command
    cal_parser = subparsers.add_parser(
        "calibrate",
        help="Calibrates a plan via DAG parsing, dry-run harvesting, and TextGrad loss evaluation",
    )
    cal_parser.add_argument("--file", required=True, help="Path to markdown plan")
    cal_parser.add_argument("--json", action="store_true", help="Output in JSON format")

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
            unresolved = [q for q in questions if not q.get("resolved_by_invariant", False)]
            if unresolved:
                if args.json:
                    print(json.dumps({
                        "task": args.task,
                        "status": "UNRESOLVED_FORK",
                        "has_ambiguity": True,
                        "auto_recommended": False,
                        "unresolved_count": len(unresolved),
                        "questions": questions,
                    }, indent=2))
                else:
                    print(f"[AMBIGUITY GATE BLOCKED — UNRESOLVED_FORK] {len(unresolved)} ungrounded architectural fork(s) require explicit user or invariant specification:")
                    for idx, q in enumerate(unresolved, 1):
                        print(f"  {idx}. {q['question']} (specify concrete choice instead of generic trigger noun)")
                return 3
            if questions:
                auto_choices = [q['options'][0] for q in questions]
                if args.json:
                    print(json.dumps({
                        "task": args.task,
                        "status": "RESOLVED_BY_INVARIANT",
                        "has_ambiguity": True,
                        "auto_recommended": True,
                        "selected": auto_choices,
                        "questions": questions
                    }, indent=2))
                else:
                    print(f"[AMBIGUITY GATE AUTO-RECOMMEND] Headless mode resolved {len(questions)} grounded choice(s):")
                    for idx, q in enumerate(questions, 1):
                        print(f"  {idx}. {q['question']} -> {q['options'][0]}")
            else:
                if args.json:
                    print(json.dumps({"task": args.task, "status": "CLEAR", "has_ambiguity": False, "auto_recommended": True, "questions": []}, indent=2))
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

        plan_md = scaffold_super_plan(
            args.task,
            args.files,
            tournament=getattr(args, "tournament", False),
            tier=chosen_tier,
            execution_mode=getattr(args, "execution_mode", "solo"),
        )
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

    elif args.command == "calibrate":
        try:
            result = calibrate_and_refine_plan(args.file, repo_root=_REPO_ROOT)
        except FileNotFoundError as exc:
            if args.json:
                print(json.dumps({"status": "ERROR", "error": str(exc)}, indent=2))
            else:
                print(f"Error: {exc}")
            return 1
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(
                f"[CALIBRATE:{result['status']}] {result['plan_path']} "
                f"(DAG nodes: {result['dag_node_count']}, "
                f"TextGrad loss: {result['textgrad_loss']}, "
                f"Accuracy: {result['calibration'].get('accuracy_score', 1.0)})"
            )
        return 0

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
