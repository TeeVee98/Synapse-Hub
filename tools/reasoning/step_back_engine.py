#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/reasoning/step_back_engine.py — Step-Back Prompting & Attention Engineering Engine
-----------------------------------------------------------------------------------------
Implements Google DeepMind's "Take a Step Back: Evoking Reasoning via Abstraction"
and Stanford University's "Lost in the Middle: How Language Models Use Long Contexts":
  1. Abstraction Elicitation (Step-Back): Rather than rushing into narrow implementation details,
     formulates high-level abstract questions about the foundational scientific, architectural,
     and algorithmic principles governing the problem.
  2. Governing Principles Synthesis: Derives fundamental invariants (CAP, ACID, Idempotency,
     AOM, Event-Loop Non-Blocking) to anchor the solution.
  3. Attention Layout Optimization (Lost in the Middle): Restructures long context to defeat
     U-shaped attention dropoff by placing critical invariants at the Primacy Anchor (0-15%),
     compressed reference materials in the Middle (15-85%), and execution triggers at the
     Recency Anchor (85-100%).

Usage:
  python tools/reasoning/step_back_engine.py --task "Fix double-click race condition in payment checkout"
  python tools/reasoning/step_back_engine.py --task "Audit auth token refresh under network flakiness" --json
  python tools/reasoning/step_back_engine.py --task "Refactor BasePage" --context-file reports/log.txt --output reports/optimized_prompt.json
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

import json
import argparse
from typing import Dict, Any, List, Optional

from tools.core.bilingual_intent_normalizer import (
    is_non_auth_token_context,
    normalize_bilingual_text,
)

# Enforce UTF-8 stdio
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


class StepBackEngine:
    """Engine executing Step-Back Abstraction & Attention Placement Optimization."""

    def __init__(self, repo_root: Optional[str] = None):
        self.repo_root = repo_root or _REPO_ROOT

    def generate_abstract_questions(self, task_text: str) -> List[Dict[str, str]]:
        """
        Step 1: Generates high-level abstract questions stepping back from task details.
        """
        task_lower = normalize_bilingual_text(task_text).lower()
        questions = []
        q_idx = 1

        # Concurrency / Race Conditions / Idempotency
        if any(k in task_lower for k in ["race", "concurren", "double", "idempotent", "duplicate", "parallel"]):
            questions.append({
                "id": f"SQ{q_idx}",
                "category": "DISTRIBUTED_CONCURRENCY",
                "abstract_question": "What fundamental principles govern concurrent mutations and duplicate prevention in distributed systems?",
                "target_mental_model": "Distributed Idempotency, Optimistic vs Pessimistic Locking, Request Deduplication"
            })
            q_idx += 1

        # Authentication / Session / Tokens (guard non-auth 'token' homonyms like crypto/price/LLM)
        auth_keywords = ["auth", "session", "jwt", "login", "cookie", "refresh"]
        if not is_non_auth_token_context(task_text):
            auth_keywords.append("token")
        if any(k in task_lower for k in auth_keywords):
            questions.append({
                "id": f"SQ{q_idx}",
                "category": "SECURITY_IDENTITY",
                "abstract_question": "What lifecycle invariants govern cryptographic token renewal under asynchronous transport degradation?",
                "target_mental_model": "OAuth2 Refresh Race Invariance, In-Flight Request Stashing, Replay Protection"
            })
            q_idx += 1

        # Performance / Latency / Rate Limits
        if any(k in task_lower for k in ["perf", "load", "latency", "stress", "rate", "timeout", "slow", "k6"]):
            questions.append({
                "id": f"SQ{q_idx}",
                "category": "SYSTEM_SATURATION",
                "abstract_question": "What physical constraints dictate throughput saturation and queuing degradation cliffs in networked services?",
                "target_mental_model": "Little's Law, Universal Scalability Law (Amdahl), Backpressure & Graceful Shedding"
            })
            q_idx += 1

        # Testing / Waits / Flakiness / DOM
        if any(k in task_lower for k in ["test", "wait", "sleep", "flak", "locator", "page", "pom", "playwright"]):
            questions.append({
                "id": f"SQ{q_idx}",
                "category": "ASYNCHRONOUS_OBSERVABILITY",
                "abstract_question": "What deterministic invariants distinguish genuine state transition events from non-deterministic rendering latency?",
                "target_mental_model": "Browser Event-Loop Microtask Timing, Accessibility Object Model (AOM) State Predicates"
            })
            q_idx += 1

        # Harness / Verification / Architecture / Invariant Gates
        if any(k in task_lower for k in ["architecture", "verification", "pipeline", "harness", "invariant", "gate"]):
            questions.append({
                "id": f"SQ{q_idx}",
                "category": "HARNESS_VERIFICATION_ARCHITECTURE",
                "abstract_question": "What Guide-Sensor feedback invariants ensure verification pipelines detect defects without vacuous or false-positive passes?",
                "target_mental_model": "Guide-Sensor Feedback Completeness, Monotonic Quality Ratchet, Truth Anchor Verification"
            })

        # Default foundational question if no specialized domain triggered
        if not questions:
            questions.append({
                "id": f"SQ{q_idx}",
                "category": "FIRST_PRINCIPLES_SOFTWARE",
                "abstract_question": "What architectural decomposition principles guarantee single responsibility and invariant preservation in this component?",
                "target_mental_model": "Separation of Concerns, Contract-First Decoupling, Postel's Law"
            })

        return questions

    def derive_governing_principles(self, task_text: str, questions: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Step 2: Answers the abstract questions with concrete governing architectural principles.
        """
        principles = []
        for q in questions:
            cat = q["category"]

            if cat == "DISTRIBUTED_CONCURRENCY":
                principles.append({
                    "category": cat,
                    "principle_name": "Idempotency & Atomic State Transition Guarantee",
                    "core_invariant": "A mutation operation repeated N times must emit identical side effects to exactly 1 operation.",
                    "concrete_guardrails": [
                        "Enforce a unique transaction/idempotency key per user interaction.",
                        "Disable UI trigger immediately on first event dispatch to block rapid duplicate clicks.",
                        "Isolate transactional database boundary; reject duplicate in-flight tokens with HTTP 409."
                    ]
                })

            elif cat == "SECURITY_IDENTITY":
                principles.append({
                    "category": cat,
                    "principle_name": "Atomic Token Refresh & Request Queue Stashing",
                    "core_invariant": "Concurrent requests during token renewal must pause and share a single in-flight refresh promise.",
                    "concrete_guardrails": [
                        "Never trigger multiple concurrent refresh calls; queue secondary requests until primary resolves.",
                        "On HTTP 401 retry strictly once with renewed credentials before escalating failure.",
                        "Invalidate stale session memory deterministically upon permanent authentication rejection."
                    ]
                })

            elif cat == "SYSTEM_SATURATION":
                principles.append({
                    "category": cat,
                    "principle_name": "Non-Linear Latency Cliff & Backpressure Containment",
                    "core_invariant": "Queue wait times grow asymptotically when resource utilization approaches 100% (Little's Law).",
                    "concrete_guardrails": [
                        "Bound maximum concurrency and enforce connection pool timeouts.",
                        "Reject excess load with HTTP 429 / Retry-After rather than accumulating unbounded memory buffers.",
                        "Trip circuit breaker immediately when error rates cross the resilience threshold."
                    ]
                })

            elif cat == "ASYNCHRONOUS_OBSERVABILITY":
                principles.append({
                    "category": cat,
                    "principle_name": "Event-Driven State Predicate Polling (Zero Sleep Invariant)",
                    "core_invariant": "State correctness must be asserted via observable DOM/AOM transitions, never wall-clock time passage.",
                    "concrete_guardrails": [
                        "Strictly ban static time.sleep / waitForTimeout.",
                        "Query semantic Accessibility roles (Role, Accessible Name) rather than fragile CSS hierarchies.",
                        "Wait for bounded navigation/response predicates (waitForURL, waitForResponse) and element visibility before triggering mutations."
                    ]
                })

            elif cat == "HARNESS_VERIFICATION_ARCHITECTURE":
                principles.append({
                    "category": cat,
                    "principle_name": "Guide-Sensor Feedback Completeness & Monotonic Quality Ratchet",
                    "core_invariant": "Every declared Guide invariant must map to an AST-grounded, non-vacuous Sensor that never relaxes assertions or swallows exceptions.",
                    "concrete_guardrails": [
                        "Enforce strict AST and word-boundary sensors without substring false positives or bare except-pass blocks.",
                        "Use monotonic clocks (time.monotonic) for duration/expiry telemetry and bound circuit-breaker retries at K <= 2.",
                        "Require fresh empirical command receipts and >= 80% mutation kill sensitivity before certifying completion."
                    ]
                })

            else:
                principles.append({
                    "category": cat,
                    "principle_name": "Clean Separation of Concerns & Clean POM Flat Architecture",
                    "core_invariant": "Presentation element interaction and business workflow assertions must be decoupled across layers.",
                    "concrete_guardrails": [
                        "Encapsulate all locators in Page Classes extending BasePage (max 1 level inheritance).",
                        "Keep test scripts strictly focused on business workflows and assertions.",
                        "Guarantee clean state pre-conditions and idempotent teardown cleanup."
                    ]
                })

        return principles

    def optimize_attention_layout(
        self,
        task_text: str,
        governing_principles: List[Dict[str, Any]],
        context_data: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Step 3: Restructures prompt context to conquer Stanford's 'Lost in the Middle' dropoff.
        - Primacy Zone (Top 0-15%): Core Rules & Governing Architectural Invariants.
        - Middle Zone (15-85%): Compressed, distilled reference context / AST / logs.
        - Recency Zone (Bottom 85-100%): Target task parameters and immediate execution directive.
        """
        # 1. Primacy Zone (Head)
        primacy_blocks = [
            "# IMMUTABLE GOVERNING INVARIANTS (STEP-BACK ABSTRACTION PRINCIPLES)",
            "> Engineered for maximum attention retention and zero hallucination drift."
        ]
        for p in governing_principles:
            primacy_blocks.append(f"## {p['principle_name']}")
            primacy_blocks.append(f"- **Core Invariant:** {p['core_invariant']}")
            primacy_blocks.append("- **Mandatory Guardrails:**")
            for g in p["concrete_guardrails"]:
                primacy_blocks.append(f"  * {g}")

        primacy_text = "\n".join(primacy_blocks)

        # 2. Middle Zone (Body) - Compressed Context
        middle_text = ""
        if context_data:
            lines = context_data.strip().splitlines()
            if len(lines) > 60:
                # Distill context to head and tail with summary in between
                head_lines = "\n".join(lines[:25])
                tail_lines = "\n".join(lines[-25:])
                middle_text = f"### Distilled Context Trace (Middle Compressed - {len(lines)} lines reduced):\n{head_lines}\n... [Middle content distilled to prevent LLM attention loss] ...\n{tail_lines}"
            else:
                middle_text = f"### Reference Context Data:\n{context_data.strip()}"
        else:
            middle_text = "### Reference Context Data:\n[No noisy background context supplied; clean execution space]"

        # 3. Recency Zone (Tail)
        recency_blocks = [
            "# IMMEDIATE EXECUTION TARGET (RECENCY ANCHOR)",
            f"**Task Description:** {task_text}",
            "**Directive:** Execute the task adhering strictly to the Immutable Governing Invariants established at the Primacy Anchor above. Falsify assumptions with empirical evidence before marking done."
        ]
        recency_text = "\n".join(recency_blocks)

        full_prompt_payload = f"{primacy_text}\n\n---\n\n{middle_text}\n\n---\n\n{recency_text}"

        return {
            "attention_optimization_applied": True,
            "architecture": "Lost-in-the-Middle U-Curve Compensation (Stanford Pattern)",
            "primacy_anchor_char_count": len(primacy_text),
            "middle_zone_char_count": len(middle_text),
            "recency_anchor_char_count": len(recency_text),
            "total_prompt_characters": len(full_prompt_payload),
            "optimized_prompt_payload": full_prompt_payload
        }

    def run(self, task_text: str, context_data: Optional[str] = None) -> Dict[str, Any]:
        """Executes full Step-Back Abstraction and Attention Placement workflow."""
        questions = self.generate_abstract_questions(task_text)
        principles = self.derive_governing_principles(task_text, questions)
        attention_layout = self.optimize_attention_layout(task_text, principles, context_data)

        return {
            "status": "SUCCESS",
            "framework": "Step-Back Prompting (DeepMind) & Attention Layout (Stanford)",
            "task": task_text,
            "step_back_abstraction": {
                "total_questions": len(questions),
                "abstract_questions": questions,
                "governing_principles": principles
            },
            "attention_layout": attention_layout
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Step-Back Prompting & Attention Engineering Engine (DeepMind & Stanford Patterns)"
    )
    parser.add_argument("--task", type=str, required=True, help="Task description or problem statement to abstract")
    parser.add_argument("--context-file", type=str, default="", help="Optional context data/log file to place in middle zone")
    parser.add_argument("--output", type=str, default="", help="Optional path to output JSON payload")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format only")

    args = parser.parse_args()

    context_content = None
    if args.context_file and os.path.exists(args.context_file):
        with open(args.context_file, "r", encoding="utf-8", errors="replace") as f:
            context_content = f.read()

    engine = StepBackEngine()
    result = engine.run(task_text=args.task, context_data=context_content)

    if args.output:
        out_dir = os.path.dirname(os.path.abspath(args.output))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("=" * 70)
        print("  STEP-BACK PROMPTING & ATTENTION ENGINEERING ENGINE")
        print("=" * 70)
        print(f"Task: {result['task']}")
        print(f"Abstract Questions Generated ({result['step_back_abstraction']['total_questions']}):")
        for q in result["step_back_abstraction"]["abstract_questions"]:
            print(f"  [{q['id']}] {q['abstract_question']}")
            print(f"       -> Target Mental Model: {q['target_mental_model']}")
        print("-" * 70)
        print("Derived Governing Principles:")
        for p in result["step_back_abstraction"]["governing_principles"]:
            print(f"  * {p['principle_name']}: {p['core_invariant']}")
        print("-" * 70)
        print("Attention U-Curve Layout:")
        layout = result["attention_layout"]
        print(f"  Primacy Anchor (Top)   : {layout['primacy_anchor_char_count']} chars")
        print(f"  Middle Zone (Distilled): {layout['middle_zone_char_count']} chars")
        print(f"  Recency Anchor (Bottom): {layout['recency_anchor_char_count']} chars")
        print("=" * 70)
        if args.output:
            print(f"Optimized payload written to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
