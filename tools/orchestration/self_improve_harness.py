#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Agno /improve EvalRegressionSuite Ratchet + CAMEL CriticRubric & SelfImprovingCoT.

Enforces a monotonic quality ratchet for agent skill/prompt/code improvements:
any candidate that regresses baseline pass rate or fails weighted CriticAgent
cross-examination is deterministically rejected. Includes CAMEL-inspired
SelfImprovingTraceLoop (CoT rejection sampling + refinement) and Workforce
failure escalation (`retry -> replan -> decompose`).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
import sys
from typing import Any, Callable, Dict, List, Literal, Optional, Sequence, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass

ImproveVerdict = Literal["accepted", "rejected_regression", "rejected_critic", "no_improvement"]


@dataclass(frozen=True)
class EvalCaseDTO:
    case_id: str
    input_text: str
    expected_token: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvalSuiteResultDTO:
    suite_name: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    baseline_pass_rate: float
    verdict: ImproveVerdict
    critic_score: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CriticRubricEvaluator:
    """CAMEL-inspired weighted criteria cross-examination evaluator with veto gate."""

    def __init__(self, weights: Dict[str, float], veto_threshold: float = 0.7) -> None:
        if not weights:
            raise ValueError("weights must be a non-empty dictionary.")
        if veto_threshold < 0.0 or veto_threshold > 1.0:
            raise ValueError("veto_threshold must be between 0.0 and 1.0.")
        total_w = sum(float(v) for v in weights.values())
        if total_w <= 0.0:
            raise ValueError("Sum of weights must be positive.")
        self.weights: Dict[str, float] = {k: float(v) / total_w for k, v in weights.items()}
        self.veto_threshold = float(veto_threshold)

    def evaluate(self, scores: Dict[str, float]) -> Tuple[float, bool]:
        weighted_sum = 0.0
        for criterion, weight in self.weights.items():
            val = max(0.0, min(1.0, float(scores.get(criterion, 0.0))))
            weighted_sum += val * weight
        final_score = round(weighted_sum, 4)
        approved = final_score >= self.veto_threshold
        return final_score, approved


class EvalRegressionSuite:
    """Agno-inspired deterministic regression evaluation suite."""

    def __init__(self, suite_name: str, cases: Sequence[EvalCaseDTO]) -> None:
        if not isinstance(suite_name, str) or not suite_name.strip():
            raise ValueError("suite_name must be a non-empty string.")
        self.suite_name = suite_name.strip()
        self.cases = list(cases)

    def run(self, solver: Callable[[str], str]) -> Dict[str, Any]:
        total = len(self.cases)
        if total == 0:
            return {"total_cases": 0, "passed_cases": 0, "failed_cases": 0, "pass_rate": 0.0, "details": []}
        passed = 0
        details: List[Dict[str, Any]] = []
        for case in self.cases:
            output = str(solver(case.input_text))
            ok = case.expected_token in output
            if ok:
                passed += 1
            details.append({"case_id": case.case_id, "passed": ok, "output": output})
        return {
            "total_cases": total,
            "passed_cases": passed,
            "failed_cases": total - passed,
            "pass_rate": round(passed / float(total), 4),
            "details": details,
        }


class SelfImprovingTraceLoop:
    """CAMEL Self-Improving CoT trace rejection & iterative refinement loop."""

    def __init__(self, max_rounds: int = 3, min_reward: float = 0.8) -> None:
        if int(max_rounds) <= 0:
            raise ValueError("max_rounds must be a positive integer.")
        self.max_rounds = int(max_rounds)
        self.min_reward = float(min_reward)

    def refine(
        self,
        initial_trace: str,
        reward_fn: Callable[[str], float],
        improve_fn: Callable[[str, int], str],
    ) -> Dict[str, Any]:
        current = str(initial_trace)
        best_trace = current
        best_reward = float(reward_fn(current))
        rounds_run = 0
        converged = best_reward >= self.min_reward

        while not converged and rounds_run < self.max_rounds:
            rounds_run += 1
            candidate = str(improve_fn(current, rounds_run))
            cand_reward = float(reward_fn(candidate))
            if cand_reward > best_reward:
                best_reward = cand_reward
                best_trace = candidate
            current = candidate
            if best_reward >= self.min_reward:
                converged = True

        return {
            "converged": converged,
            "rounds": rounds_run,
            "best_reward": round(best_reward, 4),
            "best_trace": best_trace,
        }


class WorkforceFailureEscalator:
    """CAMEL Workforce-inspired failure recovery policy: retry -> replan -> decompose."""

    def decide_action(self, attempt: int, max_retries: int = 2) -> str:
        if int(attempt) < int(max_retries):
            return "retry"
        if int(attempt) == int(max_retries):
            return "replan"
        return "decompose"


class SelfImproveHarness:
    """Monotonic /improve regression ratchet paired with CriticRubricEvaluator."""

    def __init__(self, suite: EvalRegressionSuite, critic: CriticRubricEvaluator) -> None:
        self.suite = suite
        self.critic = critic

    def evaluate_candidate(
        self,
        baseline_solver: Callable[[str], str],
        candidate_solver: Callable[[str], str],
        critic_scores: Dict[str, float],
    ) -> EvalSuiteResultDTO:
        base_res = self.suite.run(baseline_solver)
        cand_res = self.suite.run(candidate_solver)
        critic_score, critic_ok = self.critic.evaluate(critic_scores)

        base_rate = float(base_res["pass_rate"])
        cand_rate = float(cand_res["pass_rate"])

        if cand_rate < base_rate:
            verdict: ImproveVerdict = "rejected_regression"
        elif not critic_ok:
            verdict = "rejected_critic"
        elif cand_rate > base_rate:
            verdict = "accepted"
        else:
            verdict = "no_improvement"

        return EvalSuiteResultDTO(
            suite_name=self.suite.suite_name,
            total_cases=int(cand_res["total_cases"]),
            passed_cases=int(cand_res["passed_cases"]),
            failed_cases=int(cand_res["failed_cases"]),
            pass_rate=cand_rate,
            baseline_pass_rate=base_rate,
            verdict=verdict,
            critic_score=critic_score,
        )


def run_demo_improve() -> Dict[str, Any]:
    cases = [
        EvalCaseDTO("d1", "auth", "OK_AUTH"),
        EvalCaseDTO("d2", "checkout", "OK_CHECKOUT"),
    ]
    suite = EvalRegressionSuite("demo_improve_suite", cases)
    critic = CriticRubricEvaluator({"correctness": 0.6, "safety": 0.4}, veto_threshold=0.75)
    harness = SelfImproveHarness(suite, critic)
    result = harness.evaluate_candidate(
        baseline_solver=lambda s: "OK_AUTH" if s == "auth" else "FAIL",
        candidate_solver=lambda s: f"OK_{s.upper()}",
        critic_scores={"correctness": 0.95, "safety": 0.90},
    )
    return {"status": "ok", "result": result.to_dict()}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Synapse Hub /improve Regression Ratchet & Critic Harness")
    parser.add_argument("--demo", action="store_true", help="Run deterministic /improve ratchet demo")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.demo:
        parser.print_help()
        return 1
    payload = run_demo_improve()
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
