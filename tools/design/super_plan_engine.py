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
from tools.lint.plan_quality_loss import evaluate_plan_markdown_loss
from tools.context.polyglot_ast_parser import parse_polyglot_signatures
from tools.context.call_graph_indexer import get_or_build_call_graph
from tools.reasoning.step_back_engine import StepBackEngine
from tools.reasoning.self_discover_engine import SelfDiscoverEngine
from tools.reasoning.dynamic_budget_engine import DynamicBudgetEngine
from tools.design.dag_self_healer import parse_plan_to_dag
from tools.design.plan_harvester import harvest_plan
from tools.core.debt_harvester import run_debt_harvest
from tools.core.bilingual_intent_normalizer import (
    is_non_auth_token_context,
    normalize_bilingual_intent,
)
from tools.orchestration.solo_contracts import (
    build_plan_slug,
    inspect_workspace_concurrency,
    resolve_slugged_plan_path,
)


@dataclass(frozen=True)
class CalibratedSuperPlanDTO:
    """Typed calibration summary produced by super_plan_engine."""

    plan_path: str
    risk_score: float
    textgrad_loss: float
    quality_score: float = 10.0
    status: str = "CALIBRATED"


@dataclass(frozen=True)
class PipelineStageArtifact:
    """Typed stage receipt persisted by run_super_plan_pipeline (M5 P1.3)."""
    stage: str
    lifecycle_state: str
    artifact_path: str
    passed: bool
    metrics: Dict[str, Any]

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
    if not text:
        return set()
    normalized = normalize_bilingual_intent(text)
    tokens = set(re.split(r"[^a-z0-9]+", normalized.canonical_text.lower())) - {""}
    tokens.update(normalized.canonical_tokens)
    return tokens


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
    transitive_fan_in: int = 0
    coupling_memory_penalty: float = 0.0
    recommended_model: str = ""
    detected_host: str = ""

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


def _estimate_fallback_fan_in(files: List[str], repo_root: str) -> int:
    """Fallback static filename reference scan when CallGraphIndexer is unavailable."""
    tools_dir = os.path.join(repo_root, "tools")
    if not os.path.isdir(tools_dir):
        return 0
    code_exts = (".py", ".ts", ".js", ".java", ".groovy")
    patterns: List[Tuple[str, re.Pattern[str]]] = []
    for f in files:
        if not f.lower().endswith(code_exts):
            continue
        base_name = os.path.basename(f)
        stem = os.path.splitext(base_name)[0]
        if len(stem) > 2:
            patterns.append((base_name, re.compile(rf"\b{re.escape(stem)}\b")))
    if not patterns:
        return 0

    hits = 0
    for root, _, dirfiles in os.walk(tools_dir):
        for df in dirfiles:
            if not df.endswith(".py"):
                continue
            try:
                content = open(os.path.join(root, df), "r", encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            hits += sum(1 for base_name, pat in patterns if df != base_name and pat.search(content))
    return hits


def _compute_manual_req_boost(files: List[str], repo_root: str, profile: str) -> int:
    """Counts structured requirement IDs across manual spec targets to size blast radius."""
    if profile != "manual":
        return 0
    from tools.manual.manual_pipeline_adapter import extract_manual_spec_inventory

    boost = 0
    for f in files:
        if f.lower().endswith((".md", ".feature")):
            boost += len(extract_manual_spec_inventory(f, repo_root=repo_root).requirement_ids)
    return boost


def calculate_risk_routing(
    task: str,
    target_files: Optional[List[str]] = None,
    repo_root: str = _REPO_ROOT,
    profile: str = "code",
    host: Optional[str] = None,
) -> Tuple[PlanningTier, RiskMetricDTO]:
    """Calculates deterministic RiskScore (0 LLM token) and routes to optimal planning tier."""
    if profile not in ("code", "manual"):
        raise ValueError(f"Unsupported profile '{profile}'; expected 'code' or 'manual'.")
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

    # 4. HistoryDrift & CouplingMemory from project_state.json
    history_drift = 0.1
    coupling_memory_raw: Dict[str, float] = {}
    state_path = os.path.join(repo_root, "project_state.json")
    if os.path.isfile(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as fh:
                sdata = json.load(fh)
            history_drift = float(sdata.get("plan_calibration", {}).get("last_drift_ratio", 0.1))
            raw_cm = sdata.get("coupling_memory", {})
            if isinstance(raw_cm, dict):
                coupling_memory_raw = {
                    str(k).replace("\\", "/"): float(v)
                    for k, v in raw_cm.items()
                    if isinstance(v, (int, float))
                }
        except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
            history_drift = 0.1
            coupling_memory_raw = {}

    coupling_memory_penalty = 0.0
    coupling_boost = 0
    if coupling_memory_raw and files:
        by_base = {os.path.basename(k): v for k, v in coupling_memory_raw.items()}
        for f in files:
            norm_f = f.replace("\\", "/").lstrip("./")
            weight = coupling_memory_raw.get(norm_f)
            if weight is None:
                weight = by_base.get(os.path.basename(norm_f), 0.0)
            if weight > 0.0:
                coupling_memory_penalty += weight
                coupling_boost += math.ceil(weight * 3)
        coupling_memory_penalty = round(coupling_memory_penalty, 3)

    # 5. FanIn & 2-hop Transitive Blast Radius calculation: indexed graph of callers/references
    fan_in = 0
    transitive_fan_in = 0
    graph_unknown = False
    try:
        graph = get_or_build_call_graph(repo_root)
        direct_deps: Set[str] = set()
        norm_targets = {f.replace("\\", "/").lstrip("./") for f in files}
        for f in files:
            fan_in += graph.get_fan_in(f)
            direct_deps.update(d.replace("\\", "/") for d in graph.get_dependents(f))
        second_hop: Set[str] = set()
        for dep in direct_deps:
            second_hop.update(d.replace("\\", "/") for d in graph.get_dependents(dep))
        second_hop -= (direct_deps | norm_targets)
        transitive_fan_in = len(second_hop)
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        graph_unknown = bool(files)
        fan_in = _estimate_fallback_fan_in(files, repo_root)

    transitive_boost = int(round(0.5 * transitive_fan_in))
    manual_req_boost = _compute_manual_req_boost(files, repo_root, profile)
    blast_radius = fan_in + transitive_boost + coupling_boost + manual_req_boost + (5 if critical_path else 0)

    provisional_metric = RiskMetricDTO(
        fan_in=fan_in,
        cross_boundary=cross_boundary,
        state_mutation=state_mutation,
        history_drift=history_drift,
        critical_path=critical_path,
        blast_radius=blast_radius,
        fan_cap=fan_cap,
        hard_critical=hard_critical,
        graph_unknown=graph_unknown,
        transitive_fan_in=transitive_fan_in,
        coupling_memory_penalty=coupling_memory_penalty,
    )

    score = provisional_metric.risk_score
    if score < 0.35 and not critical_path and blast_radius < 5 and len(files) <= 2:
        tier = PlanningTier.TIER_0_FAST
    elif score < 0.70 and blast_radius < 10:
        tier = PlanningTier.TIER_1_STANDARD
    else:
        tier = PlanningTier.TIER_2_DEEP

    resolved_host = detect_active_host(repo_root=repo_root, host=host)
    rec_model, _ = _recommend_execution_profile(tier, host=resolved_host)
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
        transitive_fan_in=transitive_fan_in,
        coupling_memory_penalty=coupling_memory_penalty,
        recommended_model=rec_model,
        detected_host=resolved_host,
    )

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
    (
        "resilience_retry",
        re.compile(r"\b(?:retry|retries|backoff|circuit\s*breaker)\b", re.I),
        "Which retry and fault-tolerance strategy should be used?",
        [
            ("sync_backoff", "Synchronous bounded retry with exponential backoff and jitter",
             "Counter-Argument: Holds caller thread during retry wait windows."),
            ("async_backoff", "Asynchronous non-blocking retry with cancellation token",
             "Counter-Argument: Requires async caller propagation and event-loop lifecycle handling."),
            ("circuit_breaker", "Fail-fast circuit breaker with half-open recovery probe",
             "Counter-Argument: Rejects transient bursts immediately until cooldown expires.")
        ],
        {
            "sync_backoff": ("sync", "synchronous", "bounded", "jitter"),
            "async_backoff": ("async", "asyncio", "non-blocking", "queue"),
            "circuit_breaker": ("circuit", "breaker", "fail-fast", "half-open")
        }
    ),
]


_NEGATION_PREFIX_RE = re.compile(
    r"(?:^|[\s,;(])(?:no|not|without|avoid|avoiding|never|don't|dont|do\s+not|exclude|excluding|instead\s+of|rather\s+than|"
    r"không\s+(?:dùng|sử\s+dụng|xài|cần|chọn)|tránh\s+(?:dùng|sử\s+dụng)|bỏ\s+qua|đừng\s+(?:dùng|sử\s+dụng|xài|chọn)|cấm\s+(?:dùng|sử\s+dụng)|loại\s+trừ|thay\s+vì|"
    r"khong\s+(?:dung|su\s+dung|xai|can|chon)|tranh\s+(?:dung|su\s+dung)|bo\s+qua|dung\s+(?:dung|su\s+dung|xai|chon)|cam\s+(?:dung|su\s+dung)|loai\s+tru|thay\s+vi)\s+(?:any\s+|an?\s+|the\s+|external\s+|using\s+)?$",
    re.IGNORECASE,
)


def _match_keyword_polarity(context: str, kw: str) -> Tuple[bool, bool]:
    """Returns (has_positive_match, has_negated_match) for keyword in context."""
    pat = re.compile(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", re.IGNORECASE)
    has_pos = False
    has_neg = False
    for match in pat.finditer(context):
        prefix = context[max(0, match.start() - 36) : match.start()]
        if _NEGATION_PREFIX_RE.search(prefix):
            has_neg = True
        else:
            has_pos = True
    return has_pos, has_neg


def _parse_decisions_arg(raw: Optional[str]) -> Dict[str, str]:
    """Parses --decisions CLI argument from JSON dict or comma-separated key=value pairs."""
    if not raw or not str(raw).strip():
        return {}
    text = str(raw).strip()
    if text.startswith("{"):
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("--decisions JSON must be an object mapping category to choice.")
        return {str(k).strip(): str(v).strip() for k, v in parsed.items() if str(k).strip() and str(v).strip()}
    result: Dict[str, str] = {}
    for pair in text.split(","):
        if "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        if k.strip() and v.strip():
            result[k.strip()] = v.strip()
    return result


def _evaluate_ambiguity_category(
    category: str,
    question_text: str,
    options_data: List[Tuple[str, str, str]],
    keyword_maps: Dict[str, Tuple[str, ...]],
    full_context: str,
    explicit_decisions: Dict[str, str],
) -> Dict[str, Any]:
    """Resolves polarity, negations, explicit decisions, and counter-arguments for one ambiguity fork."""
    positive_keys: List[str] = []
    negated_keys: Set[str] = set()
    for opt_key, kws in keyword_maps.items():
        hits = [_match_keyword_polarity(full_context, kw) for kw in kws]
        opt_pos = any(p for p, _ in hits)
        opt_neg = any(n for _, n in hits)
        if opt_pos:
            positive_keys.append(opt_key)
        elif opt_neg:
            negated_keys.add(opt_key)

    valid_positives = [k for k in positive_keys if k not in negated_keys]
    remaining_options = [opt_key for opt_key, _, _ in options_data if opt_key not in negated_keys]

    chosen_key: Optional[str] = None
    resolved_by_invariant = False
    resolved_by_decision = False
    dec_val = explicit_decisions.get(category.lower())
    if dec_val:
        opt_keys = [opt_key for opt_key, _, _ in options_data]
        matched_dec = next(
            (ok for ok in opt_keys if ok.lower() == dec_val.lower() or dec_val.lower() in ok.lower()),
            None,
        )
        chosen_key = matched_dec or (opt_keys[0] if opt_keys else None)
        resolved_by_invariant = True
        resolved_by_decision = True
    elif valid_positives:
        chosen_key = valid_positives[0]
        resolved_by_invariant = True
    elif remaining_options:
        chosen_key = remaining_options[0]
        resolved_by_invariant = len(remaining_options) == 1 and bool(negated_keys)
    elif options_data:
        chosen_key = options_data[0][0]

    counter_args: Dict[str, str] = {}
    options: List[str] = []
    rec_text: Optional[str] = None
    rec_counter = ""

    for opt_key, opt_label, counter_arg in options_data:
        counter_args[opt_label] = counter_arg
        counter_args[f"(Recommended) {opt_label}"] = counter_arg
        if opt_key == chosen_key:
            labeled = f"(Recommended) {opt_label}"
            options.insert(0, labeled)
            rec_text = labeled
            rec_counter = counter_arg
        else:
            options.append(opt_label)

    return {
        "category": category,
        "question": question_text,
        "options": options,
        "recommended": rec_text,
        "resolved_by_invariant": resolved_by_invariant,
        "resolved_by_decision": resolved_by_decision,
        "decision_value": dec_val,
        "excluded_by_negation": sorted(list(negated_keys)),
        "counter_arguments": counter_args,
        "recommended_counter_argument": rec_counter,
    }


MANUAL_AMBIGUITY_DEFINITIONS = [
    (
        "manual_pricing_rounding",
        re.compile(r"\b(?:currency|pricing|rounding|checkout|payment|tax|discount|fx)\b", re.IGNORECASE),
        "Which financial rounding & currency precision policy applies to checkout/pricing test assertions?",
        [
            ("half_even", "Banker's rounding (HALF_EVEN) with integer minor units",
             "Counter-Argument: Requires explicit minor-unit conversion fixtures for zero-decimal currencies like VND/JPY."),
            ("half_up", "Standard commercial HALF_UP rounding to 2 decimal places",
             "Counter-Argument: Can accumulate cumulative rounding drift on multi-item invoices."),
            ("truncate", "Truncate fractional minor units without rounding",
             "Counter-Argument: May mismatch payment gateway settlement amounts."),
        ],
        {
            "half_even": ("half_even", "banker", "minor_units"),
            "half_up": ("half_up", "commercial"),
            "truncate": ("truncate", "floor"),
        },
    ),
    (
        "manual_otp_lockout",
        re.compile(r"\b(?:otp|mfa|lockout|login|auth|password|session)\b", re.IGNORECASE),
        "Which OTP expiry and brute-force lockout boundary applies to authentication manual test cases?",
        [
            ("hard_lockout", "60s OTP TTL and 15-minute lockout after 5 consecutive failures",
             "Counter-Argument: Can cause temporary self-lockout for legitimate users mistyping SMS codes."),
            ("backoff", "120s OTP TTL with exponential backoff and no hard lockout",
             "Counter-Argument: Requires rate-limit telemetry assertions instead of deterministic HTTP 429 lockout."),
            ("admin_unlock", "Strict 30s OTP TTL with permanent admin-unlock lockout",
             "Counter-Argument: High support overhead and slower manual test teardown."),
        ],
        {
            "hard_lockout": ("60s", "5_attempts", "lockout"),
            "backoff": ("backoff", "exponential"),
            "admin_unlock": ("admin_unlock", "permanent"),
        },
    ),
    (
        "manual_rbac_roles",
        re.compile(r"\b(?:rbac|role|permission|admin|idor|access|tenant)\b", re.IGNORECASE),
        "Which RBAC/IDOR denial contract applies when an unauthorized actor accesses another user's resource?",
        [
            ("http_403", "Return HTTP 403 Forbidden with zero resource data leakage",
             "Counter-Argument: Reveals resource existence on predictable IDs unless paired with UUIDs."),
            ("http_404", "Return HTTP 404 Not Found to mask resource existence",
             "Counter-Argument: Harder for QA to distinguish genuine missing records from authorization denials."),
            ("redirect", "Redirect browser to /unauthorized without API error payload",
             "Counter-Argument: Unsuitable for REST/GraphQL API clients expecting JSON status codes."),
        ],
        {
            "http_403": ("403", "forbidden"),
            "http_404": ("404", "mask"),
            "redirect": ("redirect", "unauthorized"),
        },
    ),
]


def check_ambiguities(
    task_description: str,
    invariants: Optional[List[str]] = None,
    decisions: Optional[Dict[str, str]] = None,
    profile: str = "code",
) -> List[Dict[str, Any]]:
    """Analyzes task description to identify architectural or business-rule forks with recommendations."""
    if profile not in ("code", "manual"):
        raise ValueError(f"Unsupported profile '{profile}'; expected 'code' or 'manual'.")
    questions: List[Dict[str, Any]] = []
    norm_dto = normalize_bilingual_intent(task_description or "")
    canonical_task = norm_dto.canonical_text
    inv_text = " ".join(invariants or []).lower()
    full_context = f"{canonical_task.lower()} {inv_text}"
    explicit_decisions = {
        str(k).strip().lower(): str(v).strip()
        for k, v in (decisions or {}).items()
        if str(k).strip() and str(v).strip()
    }

    active_defs = MANUAL_AMBIGUITY_DEFINITIONS if profile == "manual" else AMBIGUITY_DEFINITIONS
    for category, pattern, question_text, options_data, keyword_maps in active_defs:
        if category == "auth_security" and is_non_auth_token_context(task_description or ""):
            if not re.search(r"\b(?:auth|jwt|session|oauth|security|credential)\b", canonical_task, re.I):
                continue
        if not pattern.search(canonical_task):
            continue
        questions.append(
            _evaluate_ambiguity_category(
                category, question_text, options_data, keyword_maps, full_context, explicit_decisions
            )
        )
        if len(questions) >= 3:
            break

    if not questions and norm_dto.needs_clarification and norm_dto.clarifying_questions:
        questions.extend(dict(q) for q in norm_dto.clarifying_questions)

    return questions


def assess_intent_clarity(
    task: str,
    target_files: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Evaluates whether a task prompt has sufficient technical signal or requires user clarification."""
    files = target_files or []
    norm_dto = normalize_bilingual_intent(task or "")
    if files:
        return {
            "needs_clarification": False,
            "reason": None,
            "matched_domain_tokens": list(norm_dto.matched_domain_tokens),
            "clarifying_questions": [],
            "ambiguous_context": False,
            "context_conflicts": [],
        }
    needs_clarification = bool(norm_dto.needs_clarification)
    return {
        "needs_clarification": needs_clarification,
        "reason": (
            "Unmapped colloquial or underspecified prompt lacks technical domain anchors or target files."
            if needs_clarification
            else None
        ),
        "matched_domain_tokens": list(norm_dto.matched_domain_tokens),
        "clarifying_questions": list(norm_dto.clarifying_questions) if needs_clarification else [],
        "ambiguous_context": bool(norm_dto.ambiguous_context),
        "context_conflicts": list(norm_dto.context_conflicts),
    }


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


_HOST_ALIASES: Dict[str, str] = {
    "antigravity": "antigravity",
    "agy": "antigravity",
    "gemini": "antigravity",
    "codex": "codex",
    "openai-codex": "codex",
    "openai": "codex",
    "claude": "claude",
    "claude-code": "claude",
    "claudecode": "claude",
    "anthropic": "claude",
    "cursor": "cursor",
    "copilot": "copilot",
    "github-copilot": "copilot",
    "windsurf": "windsurf",
    "codeium": "windsurf",
    "deepseek": "deepseek",
    "local": "local",
    "local_openai": "local",
    "ollama": "local",
    "vllm": "local",
}

_CODEX_ENV_VARS = (
    "CODEX_THREAD_ID",
    "CODEX_CI",
    "CODEX_SANDBOX",
    "CODEX_SANDBOX_NETWORK_DISABLED",
    "CODEX_MANAGED_BY_NPM",
    "CODEX_MANAGED_BY_BUN",
    "CODEX_HOME",
    "CODEX_MODEL",
    "OPENAI_CODEX",
)

_CLAUDE_ENV_VARS = (
    "CLAUDECODE",
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_CODE_MAX_OUTPUT_TOKENS",
    "CLAUDE_MODEL",
)

_ANTIGRAVITY_ENV_VARS = (
    "ANTIGRAVITY_AGENT",
    "ANTIGRAVITY_CLI_ALIAS",
    "AGY_ACCOUNT",
)

_HOST_EXECUTION_PROFILES: Dict[Tuple[str, PlanningTier], Tuple[str, str]] = {
    ("antigravity", PlanningTier.TIER_0_FAST): (
        "Gemini 4 Hydrogen (Medium)",
        "Low-risk <= 2-file change; Medium thinking balances turnaround speed and accuracy.",
    ),
    ("antigravity", PlanningTier.TIER_1_STANDARD): (
        "Gemini 4 Hydrogen (High)",
        "Standard multi-step Single-Agent /solo plan; High thinking ensures Red->Blue->Purple rigor.",
    ),
    ("antigravity", PlanningTier.TIER_2_DEEP): (
        "Gemini 4 Neon (High)",
        "High-risk / multi-module DAG; High thinking prevents architectural and concurrency drift.",
    ),
    ("codex", PlanningTier.TIER_0_FAST): (
        "GPT-6-Luna / GPT-6.2-Sol (Reasoning: medium)",
        "Low-risk <= 2-file change; medium reasoning effort balances turnaround speed and accuracy.",
    ),
    ("codex", PlanningTier.TIER_1_STANDARD): (
        "GPT-6.2-Sol (Reasoning: high)",
        "Standard multi-step Single-Agent /solo plan; high reasoning ensures Red->Blue->Purple rigor.",
    ),
    ("codex", PlanningTier.TIER_2_DEEP): (
        "GPT-6.2-Astra (Reasoning: high / xhigh)",
        "High-risk / multi-module DAG; Astra with high/xhigh reasoning prevents architectural and concurrency drift.",
    ),
    ("claude", PlanningTier.TIER_0_FAST): (
        "Claude Sonnet 5.5 (Effort: medium)",
        "Low-risk <= 2-file change; medium effort balances turnaround speed and accuracy.",
    ),
    ("claude", PlanningTier.TIER_1_STANDARD): (
        "Claude Sonnet 5.5 (Effort: high)",
        "Standard multi-step Single-Agent /solo plan; high effort ensures Red->Blue->Purple rigor.",
    ),
    ("claude", PlanningTier.TIER_2_DEEP): (
        "Claude Opus 5.5 / Fable 5.2 (Effort: high / xhigh)",
        "High-risk / multi-module DAG; Opus 5.5 / Fable 5.2 with high/xhigh effort prevents architectural and concurrency drift.",
    ),
    ("cursor", PlanningTier.TIER_0_FAST): (
        "Claude Haiku 5.5 / GPT-6-Luna (Fast)",
        "Low-risk <= 2-file change in Cursor IDE.",
    ),
    ("cursor", PlanningTier.TIER_1_STANDARD): (
        "Claude Sonnet 5.5 / GPT-6.2-Sol (High)",
        "Standard multi-step /solo plan in Cursor IDE.",
    ),
    ("cursor", PlanningTier.TIER_2_DEEP): (
        "Claude Opus 5.5 / GPT-6.2-Astra (High)",
        "High-risk multi-module DAG in Cursor IDE.",
    ),
    ("copilot", PlanningTier.TIER_0_FAST): (
        "GPT-6-Luna / Claude Haiku 5.5 (Fast)",
        "Low-risk <= 2-file change in GitHub Copilot.",
    ),
    ("copilot", PlanningTier.TIER_1_STANDARD): (
        "GPT-6.2-Sol / Claude Sonnet 5.5 (High)",
        "Standard multi-step /solo plan in GitHub Copilot.",
    ),
    ("copilot", PlanningTier.TIER_2_DEEP): (
        "GPT-6.2-Astra / Claude Opus 5.5 (High)",
        "High-risk multi-module DAG in GitHub Copilot.",
    ),
    ("windsurf", PlanningTier.TIER_0_FAST): (
        "Claude Haiku 5.5 / Gemini 3.8 Flash (Fast)",
        "Low-risk <= 2-file change in Windsurf Cascade.",
    ),
    ("windsurf", PlanningTier.TIER_1_STANDARD): (
        "Claude Sonnet 5.5 / Gemini 4 Hydrogen (High)",
        "Standard multi-step /solo plan in Windsurf Cascade.",
    ),
    ("windsurf", PlanningTier.TIER_2_DEEP): (
        "Claude Opus 5.5 / Gemini 4 Neon (High)",
        "High-risk multi-module DAG in Windsurf Cascade.",
    ),
    ("deepseek", PlanningTier.TIER_0_FAST): (
        "DeepSeek-V4.1-Flash (Fast)",
        "Low-risk <= 2-file change on DeepSeek fast explorer.",
    ),
    ("deepseek", PlanningTier.TIER_1_STANDARD): (
        "DeepSeek V3 / R1 (Thinking: Medium)",
        "Standard multi-step /solo plan on DeepSeek workhorse.",
    ),
    ("deepseek", PlanningTier.TIER_2_DEEP): (
        "DeepSeek R1 (Thinking: High)",
        "High-risk multi-module DAG on DeepSeek R1 reasoning engine.",
    ),
    ("local", PlanningTier.TIER_0_FAST): (
        "Local Ollama Qwen3-Coder (Fast)",
        "Air-gapped <= 2-file change on local OpenAI-compatible runtime.",
    ),
    ("local", PlanningTier.TIER_1_STANDARD): (
        "Local Ollama Qwen3-Coder (Thinking: Medium)",
        "Air-gapped multi-step /solo plan on local Qwen3-Coder workhorse.",
    ),
    ("local", PlanningTier.TIER_2_DEEP): (
        "Local vLLM DeepSeek-R1-Distill / Ollama Qwen3-Coder (Thinking: High)",
        "Air-gapped multi-module DAG with local reasoning verification.",
    ),
}


def _env_flag_active(name: str) -> bool:
    val = os.environ.get(name, "").strip()
    return bool(val) and val.lower() not in ("0", "false", "no")


def _normalize_host_name(host: Optional[str]) -> Optional[str]:
    if host is None:
        return None
    cleaned = str(host).strip().lower()
    if not cleaned or cleaned == "auto":
        return None
    canonical = _HOST_ALIASES.get(cleaned)
    if canonical is None:
        raise ValueError(
            f"Unsupported host '{host}'; expected 'auto', 'antigravity', 'codex', 'claude', 'cursor', 'copilot', 'windsurf', 'deepseek', or 'local'."
        )
    return canonical


def _infer_host_from_model(active_model: Optional[str]) -> Optional[str]:
    if not active_model or not str(active_model).strip():
        return None
    norm = str(active_model).strip().lower()
    if re.search(
        r"(?<![a-z0-9])(?:codex|gpt-[a-z0-9.-]+|astra|sol|luna|o1|o3(?:-pro|-mini)?|o4(?:-mini)?)(?![a-z0-9])",
        norm,
    ):
        return "codex"
    if re.search(r"(?<![a-z0-9])(?:claude|fable|mythos|opus|opusplan|sonnet|haiku)(?![a-z0-9])", norm):
        return "claude"
    if re.search(r"(?<![a-z0-9])deepseek(?![a-z0-9])", norm) is not None:
        return "deepseek"
    if re.search(r"(?<![a-z0-9])(?:ollama|vllm|local)(?![a-z0-9])", norm) is not None:
        return "local"
    if re.search(r"(?<![a-z0-9])(?:gemini|hydrogen|neon|carbon|argon|flash)(?![a-z0-9])", norm):
        return "antigravity"
    return None


def detect_active_host(
    repo_root: Optional[str] = None,
    host: Optional[str] = None,
    active_model: Optional[str] = None,
) -> str:
    """Auto-detects active AI host ('antigravity', 'codex', or 'claude') from CLI, env, model, or workspace."""
    explicit = _normalize_host_name(host)
    if explicit:
        return explicit

    env_host = _normalize_host_name(os.environ.get("SYNAPSE_HOST"))
    if env_host:
        return env_host

    model_host = _infer_host_from_model(active_model)
    if model_host is not None:
        return model_host

    # Runtime session env vars take precedence (even inside an outer IDE terminal or multi-bridge repo)
    if any(_env_flag_active(k) for k in _CODEX_ENV_VARS) or any(
        k.startswith("CODEX_") and _env_flag_active(k) for k in os.environ
    ):
        return "codex"
    if any(_env_flag_active(k) for k in _CLAUDE_ENV_VARS) or any(
        k.startswith("CLAUDE_CODE_") and _env_flag_active(k) for k in os.environ
    ):
        return "claude"
    if any(_env_flag_active(k) for k in _ANTIGRAVITY_ENV_VARS) or any(
        k.startswith("ANTIGRAVITY_") and _env_flag_active(k) for k in os.environ
    ):
        return "antigravity"

    # Client-workspace fallback (skip when .agent/skills marks a multi-bridge Hub/Antigravity checkout)
    effective_root = repo_root or _REPO_ROOT
    if effective_root and os.path.isdir(effective_root):
        has_antigravity_skills = os.path.isdir(os.path.join(effective_root, ".agent", "skills"))
        if not has_antigravity_skills:
            if os.path.isfile(os.path.join(effective_root, ".codex", "config.toml")):
                return "codex"
            if os.path.isdir(os.path.join(effective_root, ".claude")) or os.path.isfile(
                os.path.join(effective_root, "CLAUDE.md")
            ):
                return "claude"
            if os.path.isdir(os.path.join(effective_root, ".agents", "skills")):
                return "codex"

    return "antigravity"


def _classify_active_model_rank(active_model: str) -> int:
    """Maps Antigravity, Codex/OpenAI, and Claude Code model strings to tier ranks 1..3."""
    norm = active_model.strip().lower()

    # Whole-word check prevents 'gemini' from matching 'mini'
    if re.search(r"(?<![a-z0-9])(?:mini|nano|haiku|flash|luna)(?![a-z0-9])", norm):
        return 1
    if re.search(
        r"(?:\((?:low|off|minimal|medium)\)|(?:reasoning|thinking|effort)\s*:\s*(?:low|off|minimal|medium)\b)",
        norm,
    ):
        return 1

    # Rank 3: Deep architectural & flagship / xhigh / max reasoning models
    if re.search(
        r"(?<![a-z0-9])(?:carbon|argon|opus|opusplan|fable|mythos|astra|xhigh|extra-high|ultra|o3-pro)(?![a-z0-9])|neon\s*\(?\s*high\b",
        norm,
    ):
        return 3
    if re.search(r"(?<![a-z0-9])(?:sonnet|sol)(?![a-z0-9])", norm) and re.search(
        r"(?<![a-z0-9])(?:max|xhigh|extra-high)(?![a-z0-9])", norm
    ):
        return 3

    # Rank 2: Standard high-capability workhorse models
    if re.search(
        r"(?<![a-z0-9])(?:sonnet|pro|sol|codex|gpt-6(?:\.\d+)?|gpt-5(?:\.\d+)?|o3|o1|o4)(?![a-z0-9])|(?:hydrogen\s*\(?\s*high|neon\s*\(?\s*medium)\b",
        norm,
    ):
        return 2

    return 1


def _recommend_execution_profile(
    tier: PlanningTier,
    host: Optional[str] = None,
    repo_root: Optional[str] = None,
) -> Tuple[str, str]:
    """Selects a host-aware recommended model and thinking/reasoning level for the plan tier."""
    resolved_host = detect_active_host(repo_root=repo_root, host=host)
    return _HOST_EXECUTION_PROFILES.get(
        (resolved_host, tier),
        _HOST_EXECUTION_PROFILES[("antigravity", PlanningTier.TIER_1_STANDARD)],
    )


def assess_pre_plan_model_fit(
    tier: PlanningTier,
    active_model: Optional[str] = None,
    host: Optional[str] = None,
    repo_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluates whether the active session model matches the required planning tier."""
    resolved_active = active_model
    if resolved_active is None:
        for env_key in ("SYNAPSE_ACTIVE_MODEL", "CODEX_MODEL", "ANTHROPIC_MODEL", "CLAUDE_MODEL"):
            candidate = os.environ.get(env_key, "").strip()
            if candidate:
                resolved_active = candidate
                break

    resolved_host = detect_active_host(repo_root=repo_root, host=host, active_model=resolved_active)
    rec_model, rationale = _recommend_execution_profile(tier, host=resolved_host, repo_root=repo_root)
    if not resolved_active or not resolved_active.strip():
        return {
            "tier": tier.value,
            "detected_host": resolved_host,
            "active_model": None,
            "recommended_model": rec_model,
            "fit_status": "UNSPECIFIED",
            "advice": f"[{resolved_host}] Recommended {rec_model} ({rationale}).",
        }

    active_rank = _classify_active_model_rank(resolved_active)

    required_rank = {
        PlanningTier.TIER_0_FAST: 1,
        PlanningTier.TIER_1_STANDARD: 2,
        PlanningTier.TIER_2_DEEP: 3,
    }.get(tier, 2)

    if active_rank < required_rank:
        fit_status = "UNDER_PROVISIONED"
        advice = f"[{resolved_host}] Upgrade from '{resolved_active}' to '{rec_model}' before drafting {tier.value} plan."
    elif tier == PlanningTier.TIER_0_FAST and active_rank >= 3:
        fit_status = "OVER_PROVISIONED"
        advice = f"[{resolved_host}] Consider stepping down from '{resolved_active}' to '{rec_model}' to conserve tokens."
    else:
        fit_status = "RIGHT_SIZED"
        advice = f"[{resolved_host}] Active model '{resolved_active}' is right-sized for {tier.value}."

    return {
        "tier": tier.value,
        "detected_host": resolved_host,
        "active_model": resolved_active,
        "recommended_model": rec_model,
        "fit_status": fit_status,
        "advice": advice,
    }


_ARCH_TOURNAMENT_KEYWORDS = frozenset({
    "architecture", "security", "contract", "schema", "isolation", "audit",
    "governance", "migration", "plugin", "sandbox", "auth", "permission",
    "guard", "receipt", "compliance", "protocol", "fsm", "orchestrator",
})
_PERF_TOURNAMENT_KEYWORDS = frozenset({
    "performance", "latency", "cache", "throughput", "async", "concurrent",
    "concurrency", "bottleneck", "memory", "scale", "shard", "sharding",
    "batch", "optimize", "optimization", "sla", "load", "speed", "fast",
})


def evaluate_orthogonal_tournament(
    task: str,
    metric: RiskMetricDTO,
    tier: PlanningTier,
) -> Dict[str, Any]:
    """
    Dynamically evaluates 3 orthogonal architectural branches (Minimalist, Clean Architecture,
    High Performance) using weighted risk metrics and task intent signals.
    """
    tokens = tokenize_text(task or "")
    arch_hits = len(tokens & _ARCH_TOURNAMENT_KEYWORDS)
    perf_hits = len(tokens & _PERF_TOURNAMENT_KEYWORDS)

    # Dynamic criteria weights sum to 1.0 (driven by genuine risk/intent signals, not unconditional tier bias)
    w_blast = 0.35 if metric.risk_score < 0.45 else 0.20
    w_arch = 0.45 if (metric.cross_boundary or metric.state_mutation or arch_hits > 0 or metric.fan_in >= 15) else 0.25
    w_perf = 0.45 if perf_hits > 0 else 0.15
    w_reg = 0.25
    total_w = w_blast + w_arch + w_perf + w_reg
    weights = {
        "blast_radius_control": round(w_blast / total_w, 3),
        "extensibility_isolation": round(w_arch / total_w, 3),
        "performance_throughput": round(w_perf / total_w, 3),
        "regression_safety": round(w_reg / total_w, 3),
    }

    # Score Branch A: Minimalist
    score_a = (
        (9.0 if metric.risk_score < 0.45 else 5.5) * weights["blast_radius_control"]
        + (5.0 if metric.cross_boundary else 7.5) * weights["extensibility_isolation"]
        + (5.0 if perf_hits > 0 else 6.5) * weights["performance_throughput"]
        + (8.5 if not metric.state_mutation else 6.0) * weights["regression_safety"]
    )
    if metric.fan_in < 10 and not metric.cross_boundary and not metric.state_mutation and perf_hits == 0:
        score_a += 1.2

    # Score Branch B: Clean Architecture
    score_b = (
        7.5 * weights["blast_radius_control"]
        + (9.5 if (metric.cross_boundary or metric.state_mutation or arch_hits > 0) else 7.5) * weights["extensibility_isolation"]
        + 6.5 * weights["performance_throughput"]
        + (9.0 if (metric.fan_in >= 10 or metric.cross_boundary or arch_hits > 0) else 7.5) * weights["regression_safety"]
    )
    if arch_hits > 0:
        score_b += min(1.5, 0.5 * arch_hits)

    # Score Branch C: High Performance
    score_c = (
        6.0 * weights["blast_radius_control"]
        + 6.5 * weights["extensibility_isolation"]
        + (9.8 if perf_hits > 0 else 7.0) * weights["performance_throughput"]
        + (6.5 if metric.state_mutation else 7.5) * weights["regression_safety"]
    )
    if perf_hits > 0:
        score_c += min(2.0, 0.65 * perf_hits)

    scores = {
        "Branch A": round(score_a, 2),
        "Branch B": round(score_b, 2),
        "Branch C": round(score_c, 2),
    }

    branch_labels = {
        "Branch A": "Branch A: Minimalist",
        "Branch B": "Branch B: Clean Architecture",
        "Branch C": "Branch C: High Performance",
    }
    winner_key = max(("Branch A", "Branch B", "Branch C"), key=lambda k: scores[k])
    selected_branch = branch_labels[winner_key]

    verdict_a = (
        f"**(Recommended)** Score {scores['Branch A']} — Lowest blast radius for bounded change"
        if winner_key == "Branch A"
        else f"Score {scores['Branch A']} — Minimalist fallback"
    )
    verdict_b = (
        f"**(Recommended)** Score {scores['Branch B']} — Best isolation for cross-boundary/high-fan-in risk"
        if winner_key == "Branch B"
        else f"Score {scores['Branch B']} — Extensible domain separation"
    )
    verdict_c = (
        f"**(Recommended)** Score {scores['Branch C']} — Highest throughput/latency optimization fit"
        if winner_key == "Branch C"
        else f"Score {scores['Branch C']} — High-traffic SLA optimization"
    )

    rationale = (
        f"risk_score={metric.risk_score}, fan_in={metric.fan_in}, "
        f"cross_boundary={metric.cross_boundary}, state_mutation={metric.state_mutation}, "
        f"tier={tier.value}, arch_signals={arch_hits}, perf_signals={perf_hits} "
        f"(scores A={scores['Branch A']}, B={scores['Branch B']}, C={scores['Branch C']})"
    )

    markdown_block = f"""
## 0. Orthogonal Architectural Tournament (Trade-off Matrix)

| Evaluation Criteria | 🏛️ Branch A: Minimalist | 📐 Branch B: Clean Architecture | ⚡ Branch C: High Performance |
|---|---|---|---|
| **Core Philosophy** | Minimal code delta, zero new files, stdlib only | Explicit interface separation & adapter pattern | Async non-blocking, zero-copy, cached hot-path |
| **Blast Radius** | Minimal (<= 2 existing files touched) | Modular (isolated domain components) | Targeted (algorithmic optimization) |
| **Regression Risk** | Lowest (preserves 100% legacy contracts) | Low (tested via clean mock adapters) | Medium (requires concurrency verification) |
| **Execution Speed** | Standard | High maintainability | Maximum sub-millisecond throughput |
| **Selection Verdict** | {verdict_a} | {verdict_b} | {verdict_c} |

> **Ruling:** Selected Branch: **[{selected_branch}]** (Heuristic Baseline — confirm/override per architecture) — {rationale}.

---
"""

    return {
        "selected_branch": selected_branch,
        "winner_key": winner_key,
        "scores": scores,
        "criteria_weights": weights,
        "rationale": rationale,
        "markdown_block": markdown_block,
    }


_ANCHOR_STOP_WORDS = frozenset({
    "add", "fix", "update", "create", "remove", "delete", "edit", "change",
    "refactor", "with", "for", "the", "and", "from", "into", "to", "in",
    "of", "on", "by", "as", "an", "a", "new", "use", "using", "get", "set",
    "run", "make", "code", "file", "files", "plan", "test", "tests", "module",
})


def _is_test_target(path: str) -> bool:
    norm = path.replace("\\", "/").strip().lower()
    base = os.path.basename(norm)
    return (
        norm.startswith("tests/")
        or "/tests/" in norm
        or base.startswith("test_")
        or base.endswith(("_test.py", ".spec.ts", ".test.ts", ".spec.js", ".test.js"))
    )


def _derive_task_contract_names(task: str) -> Tuple[str, str, str, str, str]:
    """Derives task-grounded DTO & operation names instead of generic ExecutionInputDTO boilerplate."""
    slug = build_plan_slug(task or "")
    raw_words = [w for w in slug.split("-") if w and w.isidentifier()]
    meaningful = [w for w in raw_words if w not in _ANCHOR_STOP_WORDS]
    chosen = (meaningful or raw_words)[:4]
    if not chosen:
        chosen = ["workflow", "task"]
    pascal = "".join(w.capitalize() for w in chosen)
    if pascal.lower() == "execution":
        pascal = "WorkflowTask"
    snake = "_".join(chosen)
    if snake == "operation":
        snake = "workflow_task"
    return (
        f"{pascal}InputDTO",
        f"{pascal}ResultDTO",
        f"{pascal}IntegrationResult",
        f"execute_{snake}",
        snake,
    )


def _collect_direct_callers_summary(target_files: List[str], repo_root: str) -> Tuple[List[str], bool]:
    """Queries CallGraphIndexer for real direct callers of target_files."""
    try:
        graph = get_or_build_call_graph(repo_root)
        norm_targets = {f.replace("\\", "/").lstrip("./") for f in target_files}
        callers: Set[str] = set()
        for f in target_files:
            for dep in graph.get_dependents(f):
                nd = dep.replace("\\", "/").lstrip("./")
                if nd and nd not in norm_targets:
                    callers.add(nd)
        return sorted(callers), True
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        return [], False


def _partition_tdd_milestones(target_files: List[str]) -> List[List[str]]:
    """Groups >2 target files into TDD-aligned milestones (<=3 files) pairing source with matching test files."""
    tests = [f for f in target_files if _is_test_target(f)]
    sources = [f for f in target_files if not _is_test_target(f)]
    used_tests: Set[str] = set()
    ordered: List[str] = []

    for src in sources:
        src_stem = os.path.splitext(os.path.basename(src))[0].lower()
        src_toks = {t for t in re.split(r"[_\-]+", src_stem) if len(t) > 2}
        best_t: Optional[str] = None
        best_overlap = 0
        for tf in tests:
            if tf in used_tests:
                continue
            t_stem = os.path.splitext(os.path.basename(tf))[0].lower()
            t_toks = {t for t in re.split(r"[_\-]+", t_stem) if len(t) > 2 and t != "test"}
            overlap = len(src_toks & t_toks)
            if src_stem and src_stem in t_stem:
                overlap += 3
            if overlap > best_overlap:
                best_overlap = overlap
                best_t = tf
        ordered.append(src)
        if best_t is not None:
            ordered.append(best_t)
            used_tests.add(best_t)

    for tf in tests:
        if tf not in used_tests:
            ordered.append(tf)

    # Partition paired (source, test) slices into ceil(N / 2) atomic milestones (<= 2 files each, within <= 3 budget)
    return [ordered[i : i + 2] for i in range(0, len(ordered), 2)]


def _extract_target_ast_anchor(full_path: str, task_tokens: Set[str]) -> Tuple[str, str]:
    """Resolves action ([MODIFY]/[CREATE]) and AST symbol anchor for a single target file."""
    info = extract_file_signatures(full_path)
    if not info.get("exists"):
        return "[CREATE]", "(New)"
    if not (info.get("symbols") or info.get("signatures")):
        return "[MODIFY]", "(AST: module_root)"

    meaningful_tokens = task_tokens - _ANCHOR_STOP_WORDS
    scoring_tokens = meaningful_tokens if meaningful_tokens else task_tokens

    chosen_sym_name: Optional[str] = None
    best_score = 0
    for sym in info.get("symbols", []):
        sym_name = sym.get("name", "")
        sym_tokens = tokenize_text(sym_name) - _ANCHOR_STOP_WORDS
        score = len(scoring_tokens & sym_tokens)
        if score > best_score:
            best_score = score
            chosen_sym_name = sym_name

    if not chosen_sym_name and info.get("signatures"):
        raw_sig = info["signatures"][0]
        m_anchor = re.search(r"\[AST:\s*([^\]]+)\]", raw_sig)
        if m_anchor:
            chosen_sym_name = re.sub(r"(\||:)\s*L\d+(-L?\d+)?", "", m_anchor.group(1)).strip()
        else:
            chosen_sym_name = raw_sig.split()[-1].replace("[", "").replace("]", "")

    anchor_str = f"(AST: {chosen_sym_name})" if chosen_sym_name else "(AST: module_root)"
    return "[MODIFY]", anchor_str


def _scaffold_manual_super_plan(
    task: str,
    target_files: List[str],
    tier: PlanningTier,
    metric: RiskMetricDTO,
    mode_banner: str,
    handoff_target: str,
    decisions: Optional[Dict[str, str]],
    effective_root: str,
    host: Optional[str] = None,
) -> str:
    """Generates a Manual QA Spec-Driven Super-Plan grounded in BRD requirements and 25-field rules."""
    from tools.manual.manual_pipeline_adapter import extract_manual_spec_inventory

    spec_file = next(
        (f for f in target_files if f.lower().endswith((".md", ".feature")) and ("brd" in f.lower() or "spec" in f.lower() or f.lower().endswith(".feature"))),
        target_files[0] if target_files else "docs/spec_brd.md",
    )
    tc_file = next(
        (f for f in target_files if f != spec_file and f.lower().endswith(".md")),
        "docs/manual_testcases.md",
    )

    inv = extract_manual_spec_inventory(spec_file, repo_root=effective_root)
    req_ids = inv.requirement_ids if inv.requirement_ids else ("AC-01", "AC-02", "AC-03")
    fields = inv.detected_fields if inv.detected_fields else ("text",)
    req_csv = ", ".join(f"`{r}`" for r in req_ids)
    fields_csv = ", ".join(f"`{fld}`" for fld in fields)
    rec_model, rec_rationale = _recommend_execution_profile(tier, host=host, repo_root=effective_root)
    amb_questions = check_ambiguities(task, decisions=decisions, profile="manual")
    unresolved = [q for q in amb_questions if not q.get("resolved_by_invariant", False)]
    amb_status = (
        f"Pending User Confirmation ({len(unresolved)} open business fork(s))"
        if unresolved
        else "Clear (Business rules grounded)"
    )

    return f"""<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Manual QA Super-Plan: {task}

> **Profile:** `manual`
> **Spec Source:** `{spec_file}`
> **Reference Protocol:** [AGENTS.md §5](AGENTS.md), [rbt-manual-testing](skills/02-test-design/rbt-manual-testing/SKILL.md)
> **Pre-Plan Model Fit Gate:** Recommended `{rec_model}` — {rec_rationale}
> **Execution Mode:** {mode_banner}
> **Ambiguity Gate Status:** {amb_status}
> **Plan Changelog (v1.0):** Grounded Manual QA Super-Plan with AC/REQ Coverage Contract, 25-field surface, and Spec-Mutation gates.

---

## 1. Affected Files & Blast Radius

| Action | File Path & Structural Anchor | Scope & Responsibility |
| :--- | :--- | :--- |
| `[MODIFY]` | `{spec_file}` (L1-L50) | Input BRD / User Story specification (`goldfish_score={inv.goldfish_score}`) |
| `[CREATE]` | `{tc_file}` (New) | ISO/IEC/IEEE 29119-3 13-column Manual Test Suite with REQ ID RTM mapping |

- **Regression Risk:** RiskScore `{metric.risk_score}`, BlastRadius `{metric.blast_radius}`, Requirements `{len(req_ids)}`.

---

## 2. Data Flow & Interface Signatures (Manual QA Coverage Contract)

- **Mandatory Requirement IDs (100% RTM Coverage):** {req_csv}
- **Detected 25-Field Validation Surface (`checklist_query.py`):** {fields_csv}
- **Golden Ratio Commitment:** `Golden Ratio 40% Happy / 40% Negative / 20% Security & Resilience` (or domain-specific `synapse-linter-profile`).
- **Spec-Mutation Pass Threshold:** `>= 80.0%` fault-injection kill score across boundary, RBAC/IDOR, null/Unicode, and race conditions.

---

## 3. Atomic Milestones (Execution DAG)

### Milestone 1: Lock Spec Inventory & Author Manual Test Suite
- **Node ID:** `M1`
- **depends_on:** `[]`
- **Compute Tier:** `[Model: Pro | Thinking: High]`
- **Write Set:** `['{tc_file}']`
- **Typed Interface Manifest:**
  - **consumes:** `[]`
  - **produces:** `[{{'contract': 'ManualTestSuiteRTM', 'file': '{tc_file}'}}]`
- **Circuit Breaker:** `max_fix_attempts: 2`, `scope_guard: strict`
- **Rollback Hook:** `git checkout -- {tc_file}`
- **Pass Gate:** `python3 tools/lint/manual_tc_linter.py {tc_file}`

### Milestone 2: Adversarial Spec-Mutation & Zero-Trust Manual Review
- **Node ID:** `M2`
- **depends_on:** `['M1']`
- **Compute Tier:** `[Model: Flash | Thinking: Medium]`
- **Write Set:** `['{tc_file}']`
- **Typed Interface Manifest:**
  - **consumes:** `[{{'contract': 'ManualTestSuiteRTM', 'from': 'M1'}}]`
  - **produces:** `[]`
- **Circuit Breaker:** `max_fix_attempts: 2`, `scope_guard: strict`
- **Rollback Hook:** `git checkout -- {tc_file}`
- **Pass Gate:** `python3 tools/orchestration/solo_runner.py --profile manual --mutation --spec {spec_file} --target {tc_file} --threshold 80.0 --json`

---

## 4. Verification Matrix ("Define the Exam in the Plan")

| ID | Test Scenario | Input / Precondition | Expected Output / Assertion | Verification Command |
| :--- | :--- | :--- | :--- | :--- |
| **TC-01** | Spec Readiness (BRD Audit) | `{spec_file}` | Goldfish BRD review passes with zero critical ambiguity | `python3 tools/orchestration/goldfish_review.py {spec_file} --mode brd --json` |
| **TC-02** | Format, Golden Ratio & Clarity | `{tc_file}` | ISO 29119-3 13-column lint passes with 0 defects and 0 vague oracles | `python3 tools/lint/manual_tc_linter.py {tc_file}` |
| **TC-03** | Spec-Mutation & RTM Coverage | `{spec_file}` + `{tc_file}` | 100% REQ/AC coverage and Spec-Mutation kill score >= 80.0% | `python3 tools/orchestration/solo_runner.py --profile manual --mutation --spec {spec_file} --target {tc_file} --json` |
| **TC-04** | Zero-Trust Manual Review | `{handoff_target}` | `/review --profile manual --strict-solo` returns `APPROVED` | `python3 tools/orchestration/senior_code_review.py --profile manual --plan {handoff_target} --strict-solo --json` |

---

## 5. Tri-Vulnerability Self-Critique & Mitigations

1. **Concurrency / Race Condition (`race_condition`):**
   - *Risk:* Double-submit or multi-tab state drift overlooked in happy-path-only manual cases.
   - *Mitigation:* Spec-Mutation injects double-submit/idempotency fault mutants requiring explicit race-condition test cases.
2. **Boundary & Resource Limits (`boundary_resource`):**
   - *Risk:* Missing empty/null, max-length, or Unicode/IME edge cases across input fields.
   - *Mitigation:* `checklist_query.py` surfaces all detected 25-field types and enforces negative/boundary test coverage.
3. **Backward Compatibility & Traceability (`backward_compat`):**
   - *Risk:* Spec changes after Red lock causing stale manual test cases or orphan TC IDs.
   - *Mitigation:* HMAC-signed `spec_hash` locks requirement scope and `/review --profile manual` blocks on `SPEC_DRIFT_AFTER_RED`.
"""


def scaffold_super_plan(
    task: str,
    target_files: Optional[List[str]] = None,
    tournament: bool = False,
    tier: Optional[PlanningTier] = None,
    execution_mode: str = "solo",
    plan_output_path: Optional[str] = None,
    decisions: Optional[Dict[str, str]] = None,
    repo_root: Optional[str] = None,
    profile: str = "code",
    host: Optional[str] = None,
) -> str:
    """Generates a task-grounded, TDD-aligned Spec-Driven Super-Plan markdown draft."""
    if execution_mode not in ("solo", "teamwork"):
        raise ValueError(
            f"Unsupported execution_mode '{execution_mode}'; expected 'solo' or 'teamwork'."
        )
    if profile not in ("code", "manual"):
        raise ValueError(
            f"Unsupported profile '{profile}'; expected 'code' or 'manual'."
        )
    is_teamwork = execution_mode == "teamwork"
    parallel_tag = " [PARALLEL_OK]" if is_teamwork else ""
    effective_root = repo_root or _REPO_ROOT

    if not target_files:
        target_files = (
            ["docs/spec_brd.md", "docs/manual_testcases.md"]
            if profile == "manual"
            else ["src/target_module.py", "tests/test_target_module.py"]
        )

    if tier is None:
        tier, metric = calculate_risk_routing(task, target_files, repo_root=effective_root, profile=profile, host=host)
    else:
        _, metric = calculate_risk_routing(task, target_files, repo_root=effective_root, profile=profile, host=host)

    handoff_target = (plan_output_path or "implementation_plan.md").replace("\\", "/")
    mode_banner = (
        "/teamwork (Multi-Worker Parallel on disjoint `[PARALLEL_OK]` milestones)"
        if is_teamwork
        else "Single-Agent Sequential (`/solo`) — One session, one recommended model/thinking level; execute milestones sequentially. Do NOT spawn `swarm` workers or parallel subagents."
    )
    if profile == "manual":
        return _scaffold_manual_super_plan(
            task=task,
            target_files=list(target_files),
            tier=tier,
            metric=metric,
            mode_banner=mode_banner,
            handoff_target=handoff_target,
            decisions=decisions,
            effective_root=effective_root,
            host=host,
        )

    rec_model, rec_rationale = _recommend_execution_profile(tier, host=host, repo_root=effective_root)
    handoff_cmd = (
        f'"Read {handoff_target} and execute via /teamwork"'
        if is_teamwork
        else f'"Read {handoff_target} and execute sequentially via /solo (single-agent mode, no swarm workers)"'
    )

    cognitive_brief = synthesize_cognitive_planning_brief(task, tier)
    cognitive_block = _format_cognitive_grounding_block(cognitive_brief)
    input_dto, result_dto, integration_dto, entry_fn, task_snake = _derive_task_contract_names(task)

    # Real Ambiguity Gate telemetry (never hardcodes Resolved when forks remain open)
    amb_questions = check_ambiguities(task, decisions=decisions)
    unresolved_forks = [q for q in amb_questions if not q.get("resolved_by_invariant", False)]
    if decisions:
        dec_summary = ", ".join(f"{k}={v}" for k, v in sorted(decisions.items()))
    else:
        dec_summary = ""
    if unresolved_forks:
        open_cats = ", ".join(q["category"] for q in unresolved_forks)
        ambiguity_status = (
            f"Pending User Confirmation ({len(unresolved_forks)} open fork(s): {open_cats}; "
            "confirm via `--decisions`)"
        )
    elif dec_summary:
        ambiguity_status = f"Resolved (Confirmed decisions: {dec_summary})"
    elif amb_questions:
        resolved_cats = ", ".join(q["category"] for q in amb_questions)
        ambiguity_status = f"Resolved (Invariant-grounded: {resolved_cats})"
    else:
        ambiguity_status = "Clear (No open architectural forks detected)"

    # Real Regression Risk & Direct Callers from CallGraphIndexer
    direct_callers, graph_ok = _collect_direct_callers_summary(target_files, effective_root)
    if tier == PlanningTier.TIER_2_DEEP or metric.fan_in >= 15 or metric.blast_radius >= 10:
        regression_risk_label = (
            f"High (risk_score={metric.risk_score}, fan_in={metric.fan_in}, "
            f"blast_radius={metric.blast_radius}; backward-compatible adapter required)"
        )
    elif tier == PlanningTier.TIER_1_STANDARD or metric.fan_in >= 5 or metric.cross_boundary or metric.state_mutation:
        regression_risk_label = (
            f"Medium (risk_score={metric.risk_score}, fan_in={metric.fan_in}, "
            f"blast_radius={metric.blast_radius})"
        )
    else:
        regression_risk_label = (
            f"Low (risk_score={metric.risk_score}, fan_in={metric.fan_in}, "
            f"blast_radius={metric.blast_radius})"
        )

    if direct_callers:
        shown = ", ".join(f"`{c}`" for c in direct_callers[:6])
        more = f" (+{len(direct_callers) - 6} more)" if len(direct_callers) > 6 else ""
        callers_summary = f"{shown}{more} (total fan-in: {metric.fan_in})"
    elif graph_ok:
        callers_summary = f"None detected in indexed call graph (fan-in: {metric.fan_in})"
    else:
        callers_summary = f"Call graph unavailable (fallback fan-in estimate: {metric.fan_in})"

    file_rows: List[str] = []
    task_tokens = tokenize_text(task)
    for f in target_files:
        rel = os.path.relpath(f, effective_root) if os.path.isabs(f) else f
        full_path = os.path.join(effective_root, rel)
        action, anchor_str = _extract_target_ast_anchor(full_path, task_tokens)
        role_desc = "Automated test coverage" if _is_test_target(rel) else "Core implementation"
        file_rows.append(f"| `{action}` | `{rel}` {anchor_str} | {role_desc} |")

    files_table = "\n".join(file_rows)

    existing_test_targets = [f for f in target_files if _is_test_target(f)]
    primary_test_target = (
        existing_test_targets[0]
        if existing_test_targets
        else f"tests/test_{task_snake}.py"
    )

    # Tier 0 Fast-Track Micro-Plan: includes ALL target_files in Write Set (source + test)
    if tier == PlanningTier.TIER_0_FAST and not tournament:
        t0_files = list(target_files[:3])
        t0_files_csv = ", ".join(f"`{fp}`" for fp in t0_files)
        t0_ws_repr = "[" + ", ".join(f"'{fp}'" for fp in t0_files) + "]"
        t0_rollback = " ".join(t0_files)
        t0_gate = (
            f"python3 -m pytest {' '.join(existing_test_targets)} -q"
            if existing_test_targets
            else f"python3 -m py_compile {' '.join(t0_files)}"
        )
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
# Minimal complete interface for {task}
def {entry_fn}() -> bool:
    ...
```

---

## 3. Atomic Milestones (Execution DAG)

### Milestone 1: Implementation & Verification{parallel_tag}
- **Node ID:** `M1` | **depends_on:** `[]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 3):** {t0_files_csv}
- **Write Set:** `{t0_ws_repr}`
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if out-of-scope files touched | Rollback: `git checkout -- {t0_rollback}`
- **Rollback Hook:** `git checkout -- {t0_rollback}`
- **Pass Gate:** `{t0_gate}`

---

## 4. Verification Matrix ("Define the Exam in the Plan")

| ID | Test Scenario | Input / Precondition | Expected Output / Assertion | Verification Command |
|---|---|---|---|---|
| **TC-01** | Positive (Happy Path) | Valid input for `{entry_fn}` | Success, exit code 0 | `python3 -m pytest {primary_test_target} -k "test_{task_snake}_positive"` |
| **TC-02** | Boundary / Negative | Empty or invalid input | Handled gracefully, zero unhandled exceptions | `python3 -m pytest {primary_test_target} -k "test_{task_snake}_negative"` |

---

## 5. Execution Handoff
- **Recommended Execution Model & Thinking Level:** `{rec_model}` — {rec_rationale}
- **Clean Context Handoff:** {handoff_cmd}
- **Closed-Loop CLI Handoff:** `agent-qa solo --from-plan {handoff_target} --json`
"""

    include_tournament = tournament or tier == PlanningTier.TIER_2_DEEP
    tournament_block = ""
    if include_tournament:
        tournament_eval = evaluate_orthogonal_tournament(task, metric, tier)
        tournament_block = tournament_eval["markdown_block"]

    decisions_block = ""
    if dec_summary:
        decisions_block = f"\n> **Confirmed Architectural Decisions:** `{dec_summary}`"

    # Partition target_files into TDD-aligned milestones (<= 3 files per milestone)
    milestone_sections: List[str] = []
    if len(target_files) <= 2:
        f1 = target_files[0]
        f2 = target_files[1] if len(target_files) > 1 else f"tests/test_{task_snake}.py"
        if not is_teamwork and len(target_files) == 2 and _is_test_target(f2) and not _is_test_target(f1):
            # TDD order: Test Harness & Contract first (M1), Core Implementation & Regression second (M2)
            m1_file, m2_file = f2, f1
            m1_title = "Test Harness & Interface Contract (Red-First)"
            m1_gate = f"python3 -m pytest {m1_file} -q"
            m2_title = "Core Business Logic & Regression Verification"
            m2_gate = f"python3 -m pytest {m1_file} -q"
        else:
            m1_file, m2_file = f1, f2
            m1_title = "Interfaces, Types & Test Harness"
            m1_gate = (
                f"python3 -m pytest {m1_file} -q"
                if _is_test_target(m1_file)
                else f"python3 -m py_compile {m1_file}"
            )
            m2_title = "Core Business Logic & Unit Tests"
            m2_gate = (
                f"python3 -m pytest {m2_file} -q"
                if _is_test_target(m2_file)
                else f"python3 -m py_compile {m2_file}"
            )

        m2_deps = "[]" if is_teamwork else "[M1]"
        m2_consumes = "[]" if is_teamwork else f'[{{"contract": "{result_dto}"}}]'
        m2_tag = parallel_tag if is_teamwork else ""
        milestone_sections.append(
            f"""### Milestone 1: {m1_title}{parallel_tag}
- **Node ID:** `M1` | **depends_on:** `[]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 3):** `{m1_file}`
- **Write Set:** `['{m1_file}']`
- **Typed Interface Manifest:**
  - **consumes:** `[]`
  - **produces:** `[{{"contract": "{result_dto}", "fields": {{"success": "bool"}}}}]`
  - **invariants:** `["idempotent(task_id)", "timeout_ms <= 5000"]`
- **Goal:** Define typed contracts and Red-First verification harness for `{m1_file}`.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if out-of-scope files touched | Rollback: `git checkout -- {m1_file}`
- **Rollback Hook:** `git checkout -- {m1_file}`
- **Pass Gate:** `{m1_gate}`"""
        )
        milestone_sections.append(
            f"""### Milestone 2: {m2_title}{m2_tag}
- **Node ID:** `M2` | **depends_on:** `{m2_deps}`
- **Compute Tier:** `[Model: Pro / Reasoning | Thinking: High | Best-of-3]`
- **Files Modified (Max 3):** `{m2_file}`
- **Write Set:** `['{m2_file}']`
- **Typed Interface Manifest:**
  - **consumes:** `{m2_consumes}`
  - **produces:** `[{{"contract": "{integration_dto}", "fields": {{"verified": "bool"}}}}]`
  - **invariants:** `["zero_unhandled_exceptions"]`
- **Goal:** Implement core logic in `{m2_file}` satisfying deterministic verification scenarios.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if new dependency introduced | Rollback: `git checkout -- {m2_file}`
- **Rollback Hook:** `git checkout -- {m2_file}`
- **Pass Gate:** `{m2_gate}`"""
        )
    else:
        chunks = _partition_tdd_milestones(target_files)
        prev_contract = ""
        for idx, chunk in enumerate(chunks, 1):
            node_id = f"M{idx}"
            is_first = idx == 1
            is_last = idx == len(chunks)
            depends_str = "[]" if (is_first or is_teamwork) else f"[M{idx - 1}]"
            tag = parallel_tag if (is_teamwork and not is_last) else ""
            tier_annot = (
                "[Model: Pro / Reasoning | Thinking: High | Best-of-3]"
                if idx <= max(1, len(chunks) - 1)
                else "[Model: Flash | Thinking: Off | Temp: 0.1]"
            )
            files_csv = ", ".join(f"`{fp}`" for fp in chunk)
            write_set_repr = "[" + ", ".join(f"'{fp}'" for fp in chunk) + "]"
            rollback_targets = " ".join(chunk)
            test_candidates = [fp for fp in chunk if _is_test_target(fp)]
            pass_gate = (
                f"python3 -m pytest {' '.join(test_candidates)} -q"
                if test_candidates
                else f"python3 -m py_compile {' '.join(chunk)}"
            )
            produces_contract = (
                result_dto
                if is_first
                else (integration_dto if is_last else f"{result_dto}Stage{idx}")
            )
            if is_first or is_teamwork:
                consumes_str = "[]"
            else:
                consumes_str = f'[{{"contract": "{prev_contract}"}}]'
            prev_contract = produces_contract

            title_label = (
                "Interfaces, Contracts & TDD Harness"
                if is_first
                else ("Verification, Integration & Quality Gates" if is_last else f"Core Implementation Slice {idx}")
            )
            milestone_sections.append(
                f"""### Milestone {idx}: {title_label}{tag}
- **Node ID:** `{node_id}` | **depends_on:** `{depends_str}`
- **Compute Tier:** `{tier_annot}`
- **Files Modified (Max 3):** {files_csv}
- **Write Set:** `{write_set_repr}`
- **Typed Interface Manifest:**
  - **consumes:** `{consumes_str}`
  - **produces:** `[{{"contract": "{produces_contract}", "fields": {{"success": "bool"}}}}]`
  - **invariants:** `["idempotent(task_id)", "zero_unhandled_exceptions"]`
- **Goal:** Implement and TDD-verify `{', '.join(chunk)}` within atomic file budget (<= 3 files).
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if out-of-scope files touched | Rollback: `git checkout -- {rollback_targets}`
- **Rollback Hook:** `git checkout -- {rollback_targets}`
- **Pass Gate:** `{pass_gate}`"""
            )

    milestones_block = "\n\n".join(milestone_sections)

    return f"""<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Spec-Driven Implementation Plan: {task}

> **Reference Protocol:** [AGENTS.md §5](AGENTS.md), [standards/qa-process/plan-protocol.md](standards/qa-process/plan-protocol.md)
> **Pre-Plan Model Fit Gate:** Recommended `{rec_model}` — {rec_rationale}
> **Execution Mode:** {mode_banner}
> **Ambiguity Gate Status:** {ambiguity_status}{decisions_block}
> 📝 **Plan Changelog (v1.0):**
> - Initial super-plan drafted with verified AST grounding, real call-graph risk telemetry, and TDD DAG constraints.
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
- **Direct Callers:** {callers_summary}
- **Downstream Tests:** `{primary_test_target}` (targeted 4-scenario regression suite).
- **Regression Risk:** {regression_risk_label}

---

## 2. Data Flow & Interface Signatures

> **Anti-Full-Code Invariant:** Define ONLY DTOs, schemas, and function signatures with type contracts. Full implementation body is strictly deferred to the execution phase.

```python
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass(frozen=True)
class {input_dto}:
    task_id: str
    payload: Dict[str, str]
    dry_run: bool = False

@dataclass(frozen=True)
class {result_dto}:
    success: bool
    message: str
    error_code: Optional[str] = None

def {entry_fn}(input_data: {input_dto}) -> {result_dto}:
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

{milestones_block}

---

## 4. Verification Matrix ("Define the Exam in the Plan")

| ID | Test Scenario | Input / Precondition | Expected Output / Assertion | Verification Command |
|---|---|---|---|---|
| **TC-01** | Positive (Happy Path) | `{input_dto}(task_id="T1", payload={{"valid": "true"}})` | `{result_dto}.success == True` | `python3 -m pytest {primary_test_target} -k "test_{task_snake}_positive"` |
| **TC-02** | Negative (Error Handling) | Malformed payload or downstream failure | Controlled error code returned, zero unhandled crash | `python3 -m pytest {primary_test_target} -k "test_{task_snake}_negative"` |
| **TC-03** | Boundary (Empty Input) | `{input_dto}(task_id="", payload={{}})` | Raises `ValueError` handled gracefully | `python3 -m pytest {primary_test_target} -k "test_{task_snake}_boundary"` |
| **TC-04** | Resilience / CLI Contract | Repeated idempotent invocation & `--json` output | Stable deterministic output, exit code 0 | `python3 -m pytest {primary_test_target} -k "test_{task_snake}_resilience"` |

---

## 5. Tri-Vulnerability Self-Critique & Mitigations

1. **Vulnerability 1 (Concurrency / Race Condition):**
   - *Risk:* Concurrent duplicate requests causing state drift.
   - *Mitigation:* Enforce check-and-set idempotency token validation.
2. **Vulnerability 2 (Resource Extremes / Timeout):**
   - *Risk:* Unbounded execution or network stall.
   - *Mitigation:* Apply strict 5s timeout guard with graceful fallback.
3. **Vulnerability 3 (Blast Radius / Backward Compatibility):**
   - *Risk:* Breaking changes affecting legacy callers ({callers_summary}).
   - *Mitigation:* Maintain parameter defaults and adapter wrapper.

---

## 6. Rollback & State-Migration Matrix (Zero-Downtime Guard)

| Phase | Trigger Scenario | Mitigation / Dual-mode | Rollback Command |
|---|---|---|---|
| State Migration | Schema/state corruption | Atomic transaction with checkpoint | `git checkout -- {' '.join(target_files[:3])}` |
| Service Cutover | High error rate (> 1%) | Instant flag toggle fallback | Revert commit or toggle feature flag |

---

## 7. Execution Transition & Plan Harvesting
- **Execution Mode:** {mode_banner}
- **Recommended Execution Model & Thinking Level:** `{rec_model}` — {rec_rationale}
- **Clean Context Handoff:** {handoff_cmd} (pass only this plan + AST slices).
- **Closed-Loop CLI Handoff:** `agent-qa solo --from-plan {handoff_target} --json`
- **Surgical Patch Protocol:** Edit only targeted blocks upon feedback with Changelog update; forbid whole-file regenerations.
- **Plan Harvesting Hook:** Upon passing all 11 DoD Quality Gates, harvest decisions into `docs/adr/` and clean up ephemeral `.synapse/plans/` drafts.
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

    loss_dto = evaluate_plan_markdown_loss(
        plan_content,
        filename=os.path.basename(resolved_path),
    )
    textgrad_loss = float(loss_dto.loss)
    textgrad_gradients = [g.to_dict() for g in loss_dto.gradients]
    textgrad_quality_score = float(loss_dto.quality_score)

    if not plan_content.strip():
        status = "EMPTY_PLAN"
    elif textgrad_loss > 0.0:
        status = "NEEDS_REFINEMENT"
    else:
        status = "CALIBRATED"

    return {
        "status": status,
        "loss_engine": "plan_quality_loss",
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


def _write_stage_json(path: str, data: Dict[str, Any]) -> str:
    """Writes stage artifact JSON atomically with UTF-8 encoding."""
    abs_path = os.path.abspath(path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    return abs_path


def run_super_plan_pipeline(
    task: str,
    target_files: Optional[List[str]] = None,
    tier: Optional[PlanningTier] = None,
    execution_mode: str = "solo",
    output_dir: Optional[str] = None,
    plan_output_path: Optional[str] = None,
    mutation_threshold: float = 90.0,
    non_interactive: bool = True,
    execute_dod_harvest: bool = False,
    debt_scan_dir: Optional[str] = None,
    repo_root: Optional[str] = None,
    decisions: Optional[Dict[str, str]] = None,
    profile: str = "code",
    host: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Unified Super-Plan stage orchestrator chaining:
      route -> ambiguity -> scaffold -> validate -> mutate -> calibrate -> [debt_harvest]
    Persists per-stage JSON/Markdown artifacts and enforces distinct lifecycle states:
      PLAN_GENERATED -> PLAN_VALIDATED -> PLAN_EXECUTED (only when post-DoD harvest runs).
    """
    if not task or not str(task).strip():
        raise ValueError("Task description must be a non-empty string.")

    effective_root = repo_root or _REPO_ROOT
    slug = build_plan_slug(task)
    if plan_output_path:
        resolved_plan_path = os.path.abspath(
            plan_output_path if os.path.isabs(plan_output_path) else os.path.join(effective_root, plan_output_path)
        )
    elif output_dir:
        resolved_plan_path = os.path.abspath(os.path.join(output_dir, "03_implementation_plan.md"))
    else:
        resolved_plan_path = os.path.abspath(resolve_slugged_plan_path(task, effective_root))

    stage_dir = os.path.abspath(
        output_dir or os.path.join(effective_root, "reports", "super_plan_pipeline", slug)
    )
    os.makedirs(stage_dir, exist_ok=True)

    stages: List[PipelineStageArtifact] = []
    stage_transitions: List[str] = []

    def _record_stage(
        stage: str,
        lifecycle_state: str,
        artifact_path: str,
        passed: bool,
        metrics: Dict[str, Any],
    ) -> PipelineStageArtifact:
        art = PipelineStageArtifact(
            stage=stage,
            lifecycle_state=lifecycle_state,
            artifact_path=artifact_path,
            passed=passed,
            metrics=metrics,
        )
        stages.append(art)
        if lifecycle_state not in stage_transitions:
            stage_transitions.append(lifecycle_state)
        return art

    # Stage 1: Route
    computed_tier, metric = calculate_risk_routing(
        task, target_files, repo_root=effective_root, profile=profile, host=host
    )
    chosen_tier = tier or computed_tier
    route_payload = {
        "task": task,
        "profile": profile,
        "detected_host": metric.detected_host,
        "tier": chosen_tier.value,
        "computed_tier": computed_tier.value,
        "risk_score": metric.risk_score,
        "metrics": asdict(metric),
    }
    route_path = _write_stage_json(os.path.join(stage_dir, "01_route.json"), route_payload)
    _record_stage("route", "ROUTED", route_path, True, {"tier": chosen_tier.value, "risk_score": metric.risk_score})

    # Stage 2: Ambiguity Gate
    questions = check_ambiguities(task, decisions=decisions, profile=profile)
    unresolved = [q for q in questions if not q.get("resolved_by_invariant", False)]
    amb_blocked = bool(non_interactive and unresolved)
    amb_state = "AMBIGUITY_BLOCKED" if amb_blocked else "AMBIGUITY_CLEARED"
    amb_payload = {
        "task": task,
        "profile": profile,
        "status": amb_state,
        "non_interactive": non_interactive,
        "questions_count": len(questions),
        "unresolved_count": len(unresolved),
        "questions": questions,
    }
    amb_path = _write_stage_json(os.path.join(stage_dir, "02_ambiguity.json"), amb_payload)
    _record_stage(
        "ambiguity",
        amb_state,
        amb_path,
        not amb_blocked,
        {"questions_count": len(questions), "unresolved_count": len(unresolved)},
    )

    if amb_blocked:
        manifest = {
            "task": task,
            "profile": profile,
            "passed": False,
            "lifecycle_state": "AMBIGUITY_BLOCKED",
            "stage_transitions": stage_transitions,
            "plan_path": None,
            "tournament": None,
            "stages": [asdict(s) for s in stages],
        }
        manifest_path = _write_stage_json(os.path.join(stage_dir, "pipeline_manifest.json"), manifest)
        manifest["manifest_path"] = manifest_path
        return manifest

    # Stage 3: Scaffold (PLAN_GENERATED)
    include_tournament = chosen_tier == PlanningTier.TIER_2_DEEP
    tournament_eval = (
        evaluate_orthogonal_tournament(task, metric, chosen_tier) if include_tournament else None
    )
    try:
        rel_plan_display = os.path.relpath(resolved_plan_path, effective_root).replace("\\", "/")
    except ValueError:
        rel_plan_display = resolved_plan_path.replace("\\", "/")
    plan_md = scaffold_super_plan(
        task,
        target_files=target_files,
        tournament=include_tournament,
        tier=chosen_tier,
        execution_mode=execution_mode,
        plan_output_path=rel_plan_display,
        decisions=decisions,
        repo_root=effective_root,
        profile=profile,
        host=host,
    )
    os.makedirs(os.path.dirname(resolved_plan_path), exist_ok=True)
    with open(resolved_plan_path, "w", encoding="utf-8") as fh:
        fh.write(plan_md)

    scaffold_payload = {
        "task": task,
        "profile": profile,
        "tier": chosen_tier.value,
        "execution_mode": execution_mode,
        "plan_path": resolved_plan_path,
        "tournament": (
            {
                "selected_branch": tournament_eval["selected_branch"],
                "scores": tournament_eval["scores"],
                "rationale": tournament_eval["rationale"],
            }
            if tournament_eval
            else None
        ),
    }
    scaffold_path = _write_stage_json(os.path.join(stage_dir, "03_scaffold.json"), scaffold_payload)
    _record_stage(
        "scaffold",
        "PLAN_GENERATED",
        scaffold_path,
        True,
        {"plan_path": resolved_plan_path, "chars": len(plan_md)},
    )

    # Stage 4: Validate (PLAN_VALIDATED vs PLAN_VALIDATION_FAILED)
    val_mode = "standard" if chosen_tier == PlanningTier.TIER_0_FAST else "super"
    val_passed, val_issues, val_details = validate_plan_content(
        plan_md, filename=resolved_plan_path, mode=val_mode, profile=profile
    )
    val_state = "PLAN_VALIDATED" if val_passed else "PLAN_VALIDATION_FAILED"
    val_path = _write_stage_json(
        os.path.join(stage_dir, "04_validate.json"),
        {"passed": val_passed, "mode": val_mode, "issues": val_issues, "details": val_details},
    )
    _record_stage(
        "validate",
        val_state,
        val_path,
        val_passed,
        {"issue_count": len(val_issues), "mode": val_mode},
    )

    # Stage 5: Plan Mutation Red-Teaming
    if chosen_tier == PlanningTier.TIER_0_FAST:
        mut_passed = True
        mut_payload: Dict[str, Any] = {
            "passed": True,
            "skipped": True,
            "reason": "Tier 0 Fast-Track exempt from heavy plan mutation audit",
            "kill_score": 100.0,
        }
    else:
        mut_report = run_plan_mutation_audit(plan_md, threshold=mutation_threshold)
        mut_passed = bool(mut_report.passed)
        mut_payload = asdict(mut_report)
    mut_state = "PLAN_MUTATION_VERIFIED" if mut_passed else "PLAN_MUTATION_FAILED"
    mut_path = _write_stage_json(os.path.join(stage_dir, "05_mutate.json"), mut_payload)
    _record_stage(
        "mutate",
        mut_state,
        mut_path,
        mut_passed,
        {"kill_score": mut_payload.get("kill_score", 0.0)},
    )

    # Stage 6: Calibrate & Refine
    cal_result = calibrate_and_refine_plan(resolved_plan_path, repo_root=effective_root)
    cal_path = _write_stage_json(os.path.join(stage_dir, "06_calibrate.json"), cal_result)
    _record_stage(
        "calibrate",
        "PLAN_CALIBRATED",
        cal_path,
        True,
        {
            "dag_node_count": cal_result.get("dag_node_count", 0),
            "textgrad_loss": cal_result.get("textgrad_loss", 0.0),
        },
    )

    # Stage 7: Optional Post-DoD Debt Harvest -> PLAN_EXECUTED
    debt_payload: Optional[Dict[str, Any]] = None
    if execute_dod_harvest:
        scan_target = debt_scan_dir or effective_root
        raw_debt = run_debt_harvest(scan_target, return_payload=True)
        debt_payload = raw_debt if isinstance(raw_debt, dict) else {"status": "ERROR", "total": 0}
        debt_path = _write_stage_json(os.path.join(stage_dir, "07_debt_harvest.json"), debt_payload)
        _record_stage(
            "debt_harvest",
            "PLAN_EXECUTED",
            debt_path,
            True,
            {
                "total_shortcuts": debt_payload.get("total", 0),
                "no_trigger_count": debt_payload.get("no_trigger_count", 0),
                "status": debt_payload.get("status", "CLEAN"),
            },
        )

    overall_passed = val_passed and mut_passed
    if not val_passed:
        final_lifecycle = "PLAN_VALIDATION_FAILED"
    elif not mut_passed:
        final_lifecycle = "PLAN_MUTATION_FAILED"
    elif execute_dod_harvest:
        final_lifecycle = "PLAN_EXECUTED"
    else:
        final_lifecycle = "PLAN_VALIDATED"

    manifest = {
        "task": task,
        "profile": profile,
        "tier": chosen_tier.value,
        "execution_mode": execution_mode,
        "passed": overall_passed,
        "lifecycle_state": final_lifecycle,
        "stage_transitions": stage_transitions,
        "plan_path": resolved_plan_path,
        "tournament": (
            {
                "selected_branch": tournament_eval["selected_branch"],
                "scores": tournament_eval["scores"],
                "rationale": tournament_eval["rationale"],
            }
            if tournament_eval
            else None
        ),
        "debt_harvest": debt_payload,
        "stages": [asdict(s) for s in stages],
    }
    manifest_path = _write_stage_json(os.path.join(stage_dir, "pipeline_manifest.json"), manifest)
    manifest["manifest_path"] = manifest_path
    return manifest


def _effective_cli_repo_root(repo_root_arg: Optional[str] = None) -> str:
    """Resolves workspace root for CLI invocations (explicit -> env -> active cwd worktree/temp -> _REPO_ROOT)."""
    if repo_root_arg and str(repo_root_arg).strip():
        return os.path.abspath(str(repo_root_arg).strip())
    env_root = os.environ.get("SYNAPSE_REPO_ROOT", "").strip()
    if env_root:
        return os.path.abspath(env_root)
    cwd = os.path.abspath(os.getcwd())
    if os.path.exists(os.path.join(cwd, ".git")) or cwd != os.path.abspath(_REPO_ROOT):
        return cwd
    return _REPO_ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description="Super-Plan Engine: Automated scaffold, ambiguity gate, and validator")
    subparsers = parser.add_subparsers(dest="command", help="Available sub-commands")

    # route sub-command
    route_parser = subparsers.add_parser("route", help="Determines deterministic planning tier and risk score")
    route_parser.add_argument("--task", required=True, help="Task description")
    route_parser.add_argument("--files", nargs="*", help="Candidate target files")
    route_parser.add_argument("--profile", choices=["code", "manual"], default="code", help="Planning profile: code (default) or manual")
    _host_opt = route_parser.add_argument("--host", choices=["auto", "antigravity", "codex", "claude", "cursor", "copilot", "windsurf", "deepseek", "local"], default="auto", help="AI host override for model recommendations (default auto)")
    route_parser.add_argument("--repo-root", help="Optional target repository/worktree root")
    route_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    # ambiguity-check sub-command
    amb_parser = subparsers.add_parser("ambiguity-check", help="Detects architectural forks and outputs MCQs")
    amb_parser.add_argument("--task", required=True, help="Task description")
    amb_parser.add_argument("--profile", choices=["code", "manual"], default="code", help="Planning profile: code (default) or manual")
    amb_parser.add_argument("--non-interactive", "--auto-recommend", action="store_true", dest="auto_recommend", help="Headless CI mode: auto-selects (Recommended) choices without blocking")
    amb_parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    # scaffold sub-command
    scaff_parser = subparsers.add_parser("scaffold", help="Generates grounded implementation plan draft")
    scaff_parser.add_argument("--task", required=True, help="Task description")
    scaff_parser.add_argument("--files", nargs="*", help="List of candidate files")
    scaff_parser.add_argument("--tier", choices=["fast", "standard", "deep", "auto"], default="auto", help="Planning tier override (default auto)")
    scaff_parser.add_argument("--execution-mode", choices=["solo", "teamwork"], default="solo", help="Execution mode: sequential single-agent /solo (default) or multi-worker /teamwork")
    scaff_parser.add_argument("--profile", choices=["code", "manual"], default="code", help="Planning profile: code (default) or manual")
    _host_opt = scaff_parser.add_argument("--host", choices=["auto", "antigravity", "codex", "claude", "cursor", "copilot", "windsurf", "deepseek", "local"], default="auto", help="AI host override for model recommendations (default auto)")
    scaff_parser.add_argument("--tournament", action="store_true", help="Generate 3-way orthogonal tournament Trade-off Matrix")
    scaff_parser.add_argument("--decisions", help="Optional JSON or k=v,k2=v2 architectural decisions resolving Ambiguity Gate forks")
    scaff_parser.add_argument("--output", help="Optional output filepath to save plan (pass 'auto' for .synapse/plans/<slug>.md)")
    scaff_parser.add_argument("--repo-root", help="Optional target repository/worktree root")
    scaff_parser.add_argument("--json", action="store_true", help="Output metadata in JSON format")

    # validate sub-command
    val_parser = subparsers.add_parser("validate", help="Validates an implementation plan")
    val_parser.add_argument("--file", required=True, help="Path to markdown plan")
    val_parser.add_argument("--mode", choices=["standard", "super", "auto"], default="super")
    val_parser.add_argument("--profile", choices=["auto", "code", "manual"], default="auto", help="Validation profile (auto, code, or manual)")
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
    cal_parser.add_argument("--repo-root", help="Optional target repository/worktree root")
    cal_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    # run-pipeline sub-command (reuses registered flag names)
    pipe_parser = subparsers.add_parser(
        "run-pipeline",
        help="Chains route -> ambiguity -> scaffold -> validate -> mutate -> calibrate with persisted stage artifacts",
    )
    pipe_parser.add_argument("--task", required=True, help="Task description")
    pipe_parser.add_argument("--files", nargs="*", help="List of candidate files")
    pipe_parser.add_argument("--tier", choices=["fast", "standard", "deep", "auto"], default="auto", help="Planning tier override (default auto)")
    pipe_parser.add_argument("--execution-mode", choices=["solo", "teamwork"], default="solo", help="Execution mode: sequential single-agent /solo (default) or multi-worker /teamwork")
    pipe_parser.add_argument("--profile", choices=["code", "manual"], default="code", help="Planning profile: code (default) or manual")
    _host_opt = pipe_parser.add_argument("--host", choices=["auto", "antigravity", "codex", "claude", "cursor", "copilot", "windsurf", "deepseek", "local"], default="auto", help="AI host override for model recommendations (default auto)")
    pipe_parser.add_argument("--output", help="Optional output directory to persist pipeline stage artifacts")
    pipe_parser.add_argument("--repo-root", help="Optional target repository/worktree root")
    pipe_parser.add_argument("--threshold", type=float, default=90.0, help="Pass gate threshold (default 90.0)")
    pipe_parser.add_argument("--decisions", help="Optional JSON or k=v,k2=v2 architectural decisions resolving Ambiguity Gate forks")
    pipe_parser.add_argument("--non-interactive", action="store_true", help="Headless CI mode: fail closed on unresolved architectural forks")
    pipe_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    args = parser.parse_args()
    dispatch = {
        "route": _cli_handle_route,
        "ambiguity-check": _cli_handle_ambiguity_check,
        "scaffold": _cli_handle_scaffold,
        "validate": _cli_handle_validate,
        "mutate": _cli_handle_mutate,
        "calibrate": _cli_handle_calibrate,
        "run-pipeline": _cli_handle_run_pipeline,
    }
    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    return handler(args)


def _parse_tier_override(tier_arg: str) -> Optional[PlanningTier]:
    mapping = {
        "fast": PlanningTier.TIER_0_FAST,
        "standard": PlanningTier.TIER_1_STANDARD,
        "deep": PlanningTier.TIER_2_DEEP,
    }
    return mapping.get(tier_arg)


def _cli_handle_route(args: argparse.Namespace) -> int:
    target_root = _effective_cli_repo_root(getattr(args, "repo_root", None))
    profile = getattr(args, "profile", "code")
    host_arg = getattr(args, "host", "auto")
    tier, metric = calculate_risk_routing(args.task, args.files, repo_root=target_root, profile=profile, host=host_arg)
    model_fit = assess_pre_plan_model_fit(tier, host=host_arg, repo_root=target_root)
    concurrency = inspect_workspace_concurrency(target_root, task=args.task)
    if args.json:
        print(json.dumps({
            "task": args.task,
            "profile": profile,
            "detected_host": metric.detected_host,
            "tier": tier.value,
            "risk_score": metric.risk_score,
            "recommended_model": metric.recommended_model,
            "model_fit": model_fit,
            "suggested_plan_path": concurrency["suggested_plan_path"],
            "concurrency_status": concurrency["concurrency_status"],
            "active_plans": concurrency["active_plans"],
            "dirty_files_count": concurrency["dirty_files_count"],
            "recommended_worktree_cmd": concurrency["recommended_worktree_cmd"],
            "metrics": {
                "fan_in": metric.fan_in,
                "transitive_fan_in": metric.transitive_fan_in,
                "coupling_memory_penalty": metric.coupling_memory_penalty,
                "blast_radius": metric.blast_radius,
                "cross_boundary": metric.cross_boundary,
                "state_mutation": metric.state_mutation,
                "history_drift": metric.history_drift,
            }
        }, indent=2))
        return 0
    print(f"[RISK ROUTING] Task: '{args.task}'")
    print(f"  -> Detected Host: {metric.detected_host}")
    print(f"  -> Planning Tier: {tier.value} (RiskScore: {metric.risk_score})")
    print(
        f"  -> Breakdown: FanIn={metric.fan_in}, TransitiveFanIn={metric.transitive_fan_in}, "
        f"CouplingPenalty={metric.coupling_memory_penalty}, BlastRadius={metric.blast_radius}, "
        f"CrossBoundary={metric.cross_boundary}, StateMutation={metric.state_mutation}, "
        f"HistoryDrift={metric.history_drift}"
    )
    print(f"  -> Recommended Model: {metric.recommended_model}")
    print(f"  -> Suggested Plan Path: {concurrency['suggested_plan_path']} ({concurrency['concurrency_status']})")
    if concurrency["concurrency_status"] == "CONCURRENT_SESSION_DETECTED":
        print(f"  -> Isolate Workspace: {concurrency['recommended_worktree_cmd']}")
    return 0


def _cli_handle_ambiguity_check(args: argparse.Namespace) -> int:
    questions = check_ambiguities(args.task, profile=getattr(args, "profile", "code"))
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
            auto_choices = [q["options"][0] for q in questions]
            if args.json:
                print(json.dumps({
                    "task": args.task,
                    "status": "RESOLVED_BY_INVARIANT",
                    "has_ambiguity": True,
                    "auto_recommended": True,
                    "selected": auto_choices,
                    "questions": questions,
                }, indent=2))
            else:
                print(f"[AMBIGUITY GATE AUTO-RECOMMEND] Headless mode resolved {len(questions)} grounded choice(s):")
                for idx, q in enumerate(questions, 1):
                    print(f"  {idx}. {q['question']} -> {q['options'][0]}")
            return 0
        if args.json:
            print(json.dumps({"task": args.task, "status": "CLEAR", "has_ambiguity": False, "auto_recommended": True, "questions": []}, indent=2))
        else:
            print("[AMBIGUITY GATE CLEAR] Task has unambiguous constraints. Ready for planning.")
        return 0

    if args.json:
        print(json.dumps({"task": args.task, "has_ambiguity": len(questions) > 0, "questions": questions}, indent=2))
        return 0
    if not questions:
        print("[AMBIGUITY GATE CLEAR] Task has unambiguous constraints. Ready for planning.")
        return 0
    print(f"[AMBIGUITY GATE TRIGGERED] Found {len(questions)} architectural decision fork(s):")
    for idx, q in enumerate(questions, 1):
        print(f"\n{idx}. {q['question']}")
        for opt in q["options"]:
            print(f"   - {opt}")
            counter = q.get("counter_arguments", {}).get(opt, "")
            if counter:
                print(f"     ⚠️ {counter}")
    return 0


def _cli_handle_scaffold(args: argparse.Namespace) -> int:
    chosen_tier = _parse_tier_override(getattr(args, "tier", "auto"))
    target_root = _effective_cli_repo_root(getattr(args, "repo_root", None))
    out_arg = getattr(args, "output", None)
    resolved_out = None
    display_out = None
    if out_arg:
        resolved_out = os.path.abspath(
            resolve_slugged_plan_path(args.task, target_root, explicit_path=out_arg, auto_unique=True)
        )
        try:
            display_out = os.path.relpath(resolved_out, target_root).replace("\\", "/")
        except ValueError:
            display_out = resolved_out.replace("\\", "/")

    parsed_decisions = _parse_decisions_arg(getattr(args, "decisions", None))
    profile = getattr(args, "profile", "code")
    plan_md = scaffold_super_plan(
        args.task,
        args.files,
        tournament=getattr(args, "tournament", False),
        tier=chosen_tier,
        execution_mode=getattr(args, "execution_mode", "solo"),
        plan_output_path=display_out,
        decisions=parsed_decisions or None,
        repo_root=target_root,
        profile=profile,
        host=getattr(args, "host", "auto"),
    )
    if resolved_out:
        os.makedirs(os.path.dirname(resolved_out), exist_ok=True)
        with open(resolved_out, "w", encoding="utf-8") as fh:
            fh.write(plan_md)
        if args.json:
            print(json.dumps({"task": args.task, "profile": profile, "plan_path": resolved_out, "plan_rel_path": display_out, "plan_markdown": plan_md}, indent=2))
        else:
            print(f"[SCAFFOLD COMPLETE] Saved grounded plan to {resolved_out}")
        return 0
    if args.json:
        print(json.dumps({"task": args.task, "profile": profile, "plan_markdown": plan_md}, indent=2))
    else:
        print(plan_md)
    return 0


def _cli_handle_validate(args: argparse.Namespace) -> int:
    if not os.path.isfile(args.file):
        print(f"Error: File not found: {args.file}")
        return 1
    with open(args.file, "r", encoding="utf-8", errors="replace") as fh:
        content = fh.read()
    passed, issues, details = validate_plan_content(
        content,
        filename=args.file,
        mode=args.mode,
        profile=getattr(args, "profile", "auto"),
    )
    if args.json:
        print(json.dumps({"passed": passed, "issues": issues, "details": details}, indent=2))
        return 0 if passed else 1
    status_str = "PASS" if passed else "FAIL"
    print(f"[{status_str}] {args.file}")
    for issue in issues:
        print(f"  - [X] {issue}")
    return 0 if passed else 1


def _cli_handle_mutate(args: argparse.Namespace) -> int:
    if not os.path.isfile(args.file):
        print(f"Error: File not found: {args.file}")
        return 1
    with open(args.file, "r", encoding="utf-8", errors="replace") as fh:
        content = fh.read()
    report = run_plan_mutation_audit(content, threshold=args.threshold)
    if args.json:
        print(json.dumps(asdict(report), indent=2))
        return 0 if report.passed else 1
    status_str = "PASS" if report.passed else "FAIL"
    print(f"[{status_str}] Plan Mutation Kill Score: {report.kill_score}% ({report.killed_mutants}/{report.total_mutants})")
    for m, res in report.details.items():
        k_str = "[KILL]" if res["killed"] else "[SURVIVE]"
        print(f"  {k_str} {m}: {res['verdict']}")
    return 0 if report.passed else 1


def _cli_handle_calibrate(args: argparse.Namespace) -> int:
    target_root = _effective_cli_repo_root(getattr(args, "repo_root", None))
    try:
        result = calibrate_and_refine_plan(args.file, repo_root=target_root)
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


def _cli_handle_run_pipeline(args: argparse.Namespace) -> int:
    chosen_tier = _parse_tier_override(getattr(args, "tier", "auto"))
    target_root = _effective_cli_repo_root(getattr(args, "repo_root", None))
    try:
        parsed_decisions = _parse_decisions_arg(getattr(args, "decisions", None))
        pipe_res = run_super_plan_pipeline(
            task=args.task,
            target_files=args.files,
            tier=chosen_tier,
            execution_mode=getattr(args, "execution_mode", "solo"),
            output_dir=args.output,
            mutation_threshold=getattr(args, "threshold", 90.0),
            non_interactive=True,
            repo_root=target_root,
            decisions=parsed_decisions or None,
            profile=getattr(args, "profile", "code"),
            host=getattr(args, "host", "auto"),
        )
    except ValueError as exc:
        if args.json:
            print(json.dumps({"status": "ERROR", "passed": False, "error": str(exc)}, indent=2))
        else:
            print(f"Error: {exc}")
        return 1
    if args.json:
        print(json.dumps(pipe_res, indent=2))
    else:
        print(
            f"[PIPELINE:{pipe_res['lifecycle_state']}] passed={pipe_res['passed']} "
            f"stages={len(pipe_res['stages'])} manifest={pipe_res['manifest_path']}"
        )
    return 0 if pipe_res.get("passed", False) else 1


if __name__ == "__main__":
    sys.exit(main())
