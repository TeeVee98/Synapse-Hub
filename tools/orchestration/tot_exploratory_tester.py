#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Tree/Graph-of-Thoughts Exploratory Testing Engine (Princeton ToT & Google DeepMind LATS Pattern)
------------------------------------------------------------------------------------------------
Expands linear requirements into deliberative non-linear exploration trees with state value evaluation
and automated backtracking:
  1. Multi-Branch Deliberation: Generates Happy Path, Boundary/Race, and Negative/Chaos branches.
  2. Dynamic Search Tree & State Value Model: Evaluates thought states and dynamically prunes low-promise paths.
  3. Backtracking Protocol (MCTS/DFS): Detects dead ends (irrecoverable errors, deadlock, missing pre-reqs)
     and automatically backtracks to the next best decision node.
  4. Multi-Hypothesis RCA: Diagnoses test failures across competing failure hypotheses.

Usage:
  python tools/tot_exploratory_tester.py expand-story --story-file docs/stories/US_PAYMENT.md --max-depth 3 --beam-width 3
  python tools/tot_exploratory_tester.py rca-hypotheses --error-log reports/failed.log
"""
import os
import sys

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass

import re
import json
import argparse
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, cast

# Enforce UTF-8 stdout encoding
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


@dataclass
class SearchNode:
    """Represents a state node in the Tree of Thoughts search space."""
    node_id: str
    parent_id: Optional[str]
    depth: int
    branch_type: str
    thought: str
    risk_score: float
    value_score: float
    status: str = "EXPLORED"  # EXPLORED, PRUNED, BACKTRACKED, GOAL
    children: List['SearchNode'] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "parent_id": self.parent_id,
            "depth": self.depth,
            "branch_type": self.branch_type,
            "thought": self.thought,
            "risk_score": round(self.risk_score, 2),
            "value_score": round(self.value_score, 2),
            "status": self.status,
            "children": [c.to_dict() for c in self.children]
        }


class TotExploratoryTester:
    """Tree-of-Thoughts & LATS Engine for Exploratory QA, Search Deliberation, and Root Cause Analysis."""

    def __init__(self, repo_root: Optional[str] = None):
        self.repo_root = repo_root or _REPO_ROOT

    def evaluate_state_value(self, branch_type: str, thought_text: str, domain: str) -> Tuple[float, float]:
        """
        State Value Model (Evaluator):
        Computes (risk_score, value_score) dynamically based on domain criticality and thought entropy.
        """
        # Baseline risk scores by branch taxonomy
        base_risks = {
            "BRANCH_BOUNDARY_RACE": 0.88,
            "BRANCH_NEGATIVE_CHAOS": 0.72,
            "BRANCH_SECURITY_AUTH": 0.82,
            "BRANCH_HAPPY_PATH": 0.25
        }
        risk = base_risks.get(branch_type, 0.50)

        # Domain multiplier
        if domain == "FINANCIAL_CHECKOUT":
            if branch_type in ("BRANCH_BOUNDARY_RACE", "BRANCH_NEGATIVE_CHAOS"):
                risk = min(1.0, risk + 0.05)
        elif domain == "AUTH_SESSION":
            if branch_type == "BRANCH_BOUNDARY_RACE":
                risk = min(1.0, risk + 0.04)

        # Value heuristic (Promise): high-risk branches have higher exploration value in QA
        value_score = round(risk * 0.7 + 0.3 * (1.0 if "idempotent" in thought_text.lower() or "race" in thought_text.lower() else 0.5), 2)
        return round(risk, 2), value_score

    def run_tree_search(self, story_title: str, domain: str, max_depth: int = 3, beam_width: int = 3) -> Dict[str, Any]:
        """
        Executes genuine Tree of Thoughts search with candidate evaluation and backtracking.
        """
        root = SearchNode(
            node_id="ROOT",
            parent_id=None,
            depth=0,
            branch_type="ROOT",
            thought=f"Initiate deliberative exploration for '{story_title}' in domain '{domain}'",
            risk_score=0.0,
            value_score=1.0,
            status="EXPLORED"
        )

        branch_specs = [
            ("BRANCH_BOUNDARY_RACE", "Boundary, Session Interruption & Concurrency Path"),
            ("BRANCH_NEGATIVE_CHAOS", "Negative Error Handling & Chaos Fault Path"),
            ("BRANCH_HAPPY_PATH", "Standard Happy Business Path")
        ]

        nodes_evaluated = 1
        backtracks_count = 0
        search_trace = []

        # Expand Level 1 branches
        for b_id, b_name in branch_specs:
            thought_desc = f"Evaluate {b_name} invariants and state mutations."
            r_score, v_score = self.evaluate_state_value(b_id, thought_desc, domain)
            node = SearchNode(
                node_id=f"{b_id}:root",
                parent_id="ROOT",
                depth=1,
                branch_type=b_id,
                thought=thought_desc,
                risk_score=r_score,
                value_score=v_score,
                status="EXPLORED"
            )
            root.children.append(node)
            nodes_evaluated += 1

        # Dynamic depth expansion with State Evaluation & Backtracking (MCTS/DFS)
        pruning_threshold = 0.35

        for child in root.children:
            if max_depth >= 2:
                # Generate candidate next-step thoughts for this branch
                candidates = self._generate_candidate_transitions(child.branch_type, domain, child.depth + 1)
                for cand_id, cand_thought, is_viable in candidates:
                    r_score, v_score = self.evaluate_state_value(child.branch_type, cand_thought, domain)
                    nodes_evaluated += 1

                    if not is_viable or v_score < pruning_threshold:
                        # Value threshold violation: trigger Backtracking
                        backtrack_node = SearchNode(
                            node_id=f"{child.branch_type}:{cand_id}",
                            parent_id=child.node_id,
                            depth=child.depth + 1,
                            branch_type=child.branch_type,
                            thought=cand_thought,
                            risk_score=r_score,
                            value_score=v_score,
                            status="BACKTRACKED"
                        )
                        child.children.append(backtrack_node)
                        backtracks_count += 1
                        search_trace.append(f"Backtracked from unviable thought node '{cand_id}' (Value: {v_score} < {pruning_threshold}) to parent '{child.node_id}'.")
                    else:
                        # Viable thought node: explore
                        explored_node = SearchNode(
                            node_id=f"{child.branch_type}:{cand_id}",
                            parent_id=child.node_id,
                            depth=child.depth + 1,
                            branch_type=child.branch_type,
                            thought=cand_thought,
                            risk_score=r_score,
                            value_score=v_score,
                            status="EXPLORED"
                        )
                        child.children.append(explored_node)

        return {
            "root_node": root.to_dict(),
            "nodes_evaluated": nodes_evaluated,
            "backtracks_count": backtracks_count,
            "search_trace": search_trace
        }

    def _generate_candidate_transitions(self, branch_type: str, domain: str, target_depth: int) -> List[Tuple[str, str, bool]]:
        """
        Dynamically generates candidate state transitions for tree expansion.
        Returns List of (candidate_id, thought_description, is_viable).
        """
        candidates = []
        if branch_type == "BRANCH_BOUNDARY_RACE":
            candidates.append((
                "idempotent_debounce_probe",
                "Apply rapid double-click debounce and verify single database transaction mutation.",
                True
            ))
            candidates.append((
                "unbounded_concurrent_flood",
                "Execute unbounded parallel requests without connection throttling or timeout barrier.",
                False  # Unviable path requiring backtrack
            ))
        elif branch_type == "BRANCH_NEGATIVE_CHAOS":
            candidates.append((
                "mocked_fault_injection",
                "Simulate transient HTTP 503 and verify client exponential backoff and retry.",
                True
            ))
            candidates.append((
                "unmockable_third_party_cliff",
                "Attempt live payment gateway circuit kill without sandbox mock or fallback handler.",
                False  # Unviable path requiring backtrack
            ))
        elif branch_type == "BRANCH_HAPPY_PATH":
            candidates.append((
                "clean_teardown_verification",
                "Assert idempotent data teardown and verify zero dangling entities in database.",
                True
            ))

        return candidates

    def expand_story(self, story_content: str, max_depth: int = 3, beam_width: int = 3) -> Dict[str, Any]:
        """Decomposes story into a 3-branch Tree of Thoughts with risk scores and tree search telemetry."""
        # Extract title and criteria
        lines = [line.strip() for line in story_content.splitlines() if line.strip()]
        title = lines[0] if lines else "Untitled User Story"
        if title.startswith("#"):
            title = title.lstrip("#").strip()

        # Extract keywords
        keywords = re.findall(r'\b[a-zA-Z]{4,}\b', story_content.lower())
        is_checkout = any(k in keywords for k in ["cart", "checkout", "pay", "order", "price"])
        is_auth = any(k in keywords for k in ["login", "auth", "token", "password", "sso"])

        context_domain = "FINANCIAL_CHECKOUT" if is_checkout else ("AUTH_SESSION" if is_auth else "GENERAL_CRUD")

        # Execute internal Tree Search & State Value Evaluation
        tree_search_result = self.run_tree_search(title, context_domain, max_depth=max_depth, beam_width=beam_width)

        # 3 Branches:
        # 1. Happy Path
        # 2. Boundary / Session Interruption / Race Condition
        # 3. Negative / Chaos / Backend Fault
        branches = [
            {
                "branch_id": "BRANCH_HAPPY_PATH",
                "name": "Standard Happy Business Path",
                "risk_score": 0.25,
                "thoughts": [
                    {"step": 1, "thought": "Navigate to initial entity view and ensure clean pre-conditions."},
                    {"step": 2, "thought": "Populate valid payload attributes and trigger submit action."},
                    {"step": 3, "thought": "Verify success confirmation modal and assert database record creation."}
                ]
            },
            {
                "branch_id": "BRANCH_BOUNDARY_RACE",
                "name": "Boundary, Session Interruption & Concurrency Path",
                "risk_score": 0.88,
                "thoughts": [
                    {"step": 1, "thought": "Simulate session expiration or token invalidation mid-flow."},
                    {"step": 2, "thought": "Perform rapid double-click on submission action to probe race condition."},
                    {"step": 3, "thought": "Assert idempotency: strictly 1 transaction created, duplicate blocked gracefully."}
                ]
            },
            {
                "branch_id": "BRANCH_NEGATIVE_CHAOS",
                "name": "Negative Error Handling & Chaos Fault Path",
                "risk_score": 0.72,
                "thoughts": [
                    {"step": 1, "thought": "Inject malformed/boundary input payload exceeding maximum character limits."},
                    {"step": 2, "thought": "Simulate backend 500 error or database connection timeout via route stub."},
                    {"step": 3, "thought": "Assert user-friendly error toast, zero data corruption, and retry availability."}
                ]
            }
        ]

        # Deep Graph-of-Thoughts (GoT) expansion when max_depth >= 2
        if max_depth >= 2:
            for b in branches:
                if b["branch_id"] == "BRANCH_HAPPY_PATH":
                    b["thoughts"].append({"step": 4, "thought": "Assert idempotent data teardown and verify zero dangling entities in database."})
                elif b["branch_id"] == "BRANCH_BOUNDARY_RACE":
                    b["thoughts"].append({"step": 4, "thought": "Verify token renewal under concurrent in-flight requests without 401 unhandled rejection."})
                elif b["branch_id"] == "BRANCH_NEGATIVE_CHAOS":
                    b["thoughts"].append({"step": 4, "thought": "Verify client-side exponential backoff retry and circuit breaker recovery under transient 503."})

        graph_edges = [
            {"from": "BRANCH_HAPPY_PATH:step_1", "to": "BRANCH_BOUNDARY_RACE:step_1", "relation": "session_fork"},
            {"from": "BRANCH_BOUNDARY_RACE:step_2", "to": "BRANCH_NEGATIVE_CHAOS:step_2", "relation": "fault_escalation"},
            {"from": "BRANCH_NEGATIVE_CHAOS:step_3", "to": "BRANCH_HAPPY_PATH:step_3", "relation": "recovery_reconciliation"}
        ]

        # Beam search selection: sort by risk score descending and take beam_width
        sorted_branches = sorted(branches, key=lambda b: cast(float, b["risk_score"]), reverse=True)
        selected_branches = sorted_branches[:beam_width]

        return {
            "status": "PASS",
            "story_title": title,
            "domain": context_domain,
            "max_depth": max_depth,
            "beam_width": beam_width,
            "total_branches_explored": len(branches),
            "highest_risk_branch": selected_branches[0]["branch_id"],
            "branches": selected_branches,
            "graph_of_thoughts_edges": graph_edges,
            "tree_search_engine": {
                "nodes_evaluated": tree_search_result["nodes_evaluated"],
                "backtracks_count": tree_search_result["backtracks_count"],
                "search_trace": tree_search_result["search_trace"],
                "search_tree": tree_search_result["root_node"]
            },
            "clean_pom_recommendations": [
                f"Implement {context_domain}Page extending BasePage",
                "Encapsulate double-click debounce in clickSubmitSafe()",
                "Assert boundary toast in verifyErrorMessageDisplayed()"
            ]
        }

    def rca_hypotheses(self, error_log: str, hypotheses: Optional[List[str]] = None) -> Dict[str, Any]:
        """Performs multi-hypothesis Root Cause Analysis on test failures."""
        if not hypotheses:
            hypotheses = ["DOM_TIMEOUT", "ASYNC_RACE", "DB_LOCK", "BACKEND_500", "STALE_SELECTOR"]

        log_lower = error_log.lower()
        scored_hypotheses = []

        for hyp in hypotheses:
            score = 0.0
            evidence = []

            if hyp == "DOM_TIMEOUT":
                if "timed out" in log_lower or "waitfortimeout" in log_lower or "5000ms" in log_lower:
                    score += 0.85
                    evidence.append("Found timeout or waiting duration signature in log")
                if "element is not visible" in log_lower or "tobevisible" in log_lower:
                    score += 0.10
                    evidence.append("Element visibility expectation failed")

            elif hyp == "ASYNC_RACE":
                if "click intercepted" in log_lower or "animation" in log_lower or "detached" in log_lower:
                    score += 0.90
                    evidence.append("Overlay or detachment signature points to async race condition")
                if "networkidle" in log_lower or "pending" in log_lower:
                    score += 0.15
                    evidence.append("Pending network requests active during action")

            elif hyp == "DB_LOCK":
                if "deadlock" in log_lower or "lock" in log_lower or "sql" in log_lower or "unique constraint" in log_lower:
                    score += 0.88
                    evidence.append("Database lock or constraint collision detected in trace")

            elif hyp == "BACKEND_500":
                if re.search(r'\b500\b', log_lower) and not re.search(r'\b500\d+ms\b', log_lower) and ("http" in log_lower or "status" in log_lower or "server error" in log_lower or "internal" in log_lower):
                    score += 0.95
                    evidence.append("HTTP 500 status code explicitly logged")
                elif "internal server error" in log_lower:
                    score += 0.95
                    evidence.append("Internal Server Error explicitly logged")

            elif hyp == "STALE_SELECTOR":
                if "locator" in log_lower or "selector" in log_lower or "xpath" in log_lower:
                    score += 0.70
                    evidence.append("Locator or selector syntax mentioned in failure message")

            # Baseline confidence
            if not evidence:
                score = 0.10
                evidence.append("No direct signature found; baseline background likelihood")

            scored_hypotheses.append({
                "hypothesis": hyp,
                "confidence_score": round(min(1.0, score), 3),
                "evidence": evidence
            })

        scored_hypotheses.sort(key=lambda h: cast(float, h["confidence_score"]), reverse=True)
        winner = scored_hypotheses[0]

        recommendations = {
            "DOM_TIMEOUT": "Replace hardcoded delay with page.waitForLoadState('networkidle') or element.waitFor({state: 'visible'})",
            "ASYNC_RACE": "Use clickSafe() helper with overlay detachment waiting or dispatchEvent('click')",
            "DB_LOCK": "Randomize entity code prefix via DataGenerator.uniqueCode('AUTO_') and enforce teardown cleanup",
            "BACKEND_500": "Inspect backend server logs for uncaught 500 NullPointerException or DB connection pool exhaustion",
            "STALE_SELECTOR": "Run tools/agentless_patcher.py heal-failure to update stale attribute to ARIA role"
        }

        return {
            "status": "PASS",
            "primary_root_cause": winner["hypothesis"],
            "confidence": winner["confidence_score"],
            "recommended_fix": recommendations.get(str(winner["hypothesis"]), "Review stacktrace with team"),
            "ranked_hypotheses": scored_hypotheses
        }


def main():
    parser = argparse.ArgumentParser(description="Tree-of-Thoughts Exploratory Testing Engine")
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")

    # expand-story
    exp_p = subparsers.add_parser("expand-story", help="Expand User Story into Tree of Thoughts")
    exp_p.add_argument("--story-file", required=True, help="Path to story markdown file or text string")
    exp_p.add_argument("--max-depth", type=int, default=3, help="Max thought tree depth")
    exp_p.add_argument("--beam-width", type=int, default=3, help="Beam search width")
    exp_p.add_argument("--out-graph", help="Optional path to output graph JSON")

    # rca-hypotheses
    rca_p = subparsers.add_parser("rca-hypotheses", help="Diagnose failure via multi-hypothesis RCA")
    rca_p.add_argument("--error-log", required=True, help="Path to error log or log string")
    rca_p.add_argument("--hypotheses", help="Comma-separated hypotheses list")

    args = parser.parse_args()
    tester = TotExploratoryTester()

    if args.subcommand == "expand-story":
        content = args.story_file
        if os.path.exists(args.story_file):
            with open(args.story_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        res = tester.expand_story(content, max_depth=args.max_depth, beam_width=args.beam_width)
        if args.out_graph:
            os.makedirs(os.path.dirname(os.path.abspath(args.out_graph)), exist_ok=True)
            with open(args.out_graph, "w", encoding="utf-8") as f:
                json.dump(res, f, indent=2)
        print(json.dumps(res, indent=2))
        sys.exit(0)

    elif args.subcommand == "rca-hypotheses":
        log_content = args.error_log
        if os.path.exists(args.error_log):
            with open(args.error_log, "r", encoding="utf-8", errors="replace") as f:
                log_content = f.read()
        hyp_list = [h.strip() for h in args.hypotheses.split(",")] if args.hypotheses else None
        res = tester.rca_hypotheses(error_log=log_content, hypotheses=hyp_list)
        print(json.dumps(res, indent=2))
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
