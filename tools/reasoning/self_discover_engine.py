#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/reasoning/self_discover_engine.py — Dynamic Reasoning Scaffolding Engine (Google DeepMind Pattern)
--------------------------------------------------------------------------------------------------------
Elicits latent model capabilities by dynamically composing task-specific reasoning structures
instead of hardcoded static prompts:
  1. Select: Identifies the 3-5 most potent atomic reasoning modules from standards/reasoning/atomic_modules.json.
  2. Adapt: Specializes abstract reasoning primitives to the domain context of the task.
  3. Implement: Generates an actionable reasoning structure (JSON) for subsequent execution.

Usage:
  python tools/reasoning/self_discover_engine.py --task "Design idempotent payment checkout with race condition guard"
  python tools/reasoning/self_discover_engine.py --task "Audit auth token refresh under network flakiness" --json
  python tools/reasoning/self_discover_engine.py --task "Refactor BasePage to eliminate static sleeps" --output reports/reasoning.json
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
from typing import Dict, Any, List, Optional

# Enforce UTF-8 stdio
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEFAULT_MODULES_PATH = os.path.join(_REPO_ROOT, "standards", "reasoning", "atomic_modules.json")


class SelfDiscoverEngine:
    """Engine implementing Google DeepMind's Self-Discover framework for LLM Capability Elicitation."""

    def __init__(self, modules_file: Optional[str] = None):
        self.modules_file = modules_file or DEFAULT_MODULES_PATH
        self.modules_catalog: List[Dict[str, Any]] = self._load_modules()

    def _load_modules(self) -> List[Dict[str, Any]]:
        """Loads atomic reasoning modules from catalog."""
        if not os.path.exists(self.modules_file):
            raise FileNotFoundError(f"Reasoning catalog not found: {self.modules_file}")
        with open(self.modules_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("modules", [])

    def select(self, task_text: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """
        Stage 1 (Select): Selects the most relevant atomic reasoning modules for the task.
        Uses composite scoring: keyword lexical resonance + family diversity.
        """
        tokens = set(re.findall(r"\b[a-zA-Z0-9_]{3,}\b", task_text.lower()))
        scored_modules = []

        for mod in self.modules_catalog:
            keywords = set(k.lower() for k in mod.get("keywords", []))
            name_tokens = set(re.findall(r"\b[a-zA-Z0-9_]{3,}\b", mod.get("name", "").lower()))
            desc_tokens = set(re.findall(r"\b[a-zA-Z0-9_]{3,}\b", mod.get("description", "").lower()))

            # Keyword match score
            kw_hits = len(tokens.intersection(keywords))
            name_hits = len(tokens.intersection(name_tokens))
            desc_hits = len(tokens.intersection(desc_tokens))

            score = (kw_hits * 3.0) + (name_hits * 2.0) + (desc_hits * 0.5)

            # Heuristic boosters for high-criticality task types
            task_lower = task_text.lower()
            if "race" in task_lower or "concurren" in task_lower:
                if mod["id"] in ("MOD_CONCURRENCY_RACE_MODELING", "MOD_IDEMPOTENCY_INVARIANT_CHECK"):
                    score += 5.0
            if "idempotent" in task_lower:
                if mod["id"] in ("MOD_IDEMPOTENCY_INVARIANT_CHECK", "MOD_TRANSACTION_BOUNDARY_INTEGRITY"):
                    score += 5.0
            if "flak" in task_lower or "sleep" in task_lower or "wait" in task_lower:
                if mod["id"] in ("MOD_ASYNC_STATE_SYNCHRONIZATION", "MOD_FLAKINESS_ISOLATION"):
                    score += 5.0
            if "fail" in task_lower or "heal" in task_lower or "circuit" in task_lower:
                if mod["id"] in ("MOD_CIRCUIT_BREAKER_PROTOCOL", "MOD_MULTI_TRIAL_SELF_HEALING"):
                    score += 4.0
            if "test" in task_lower or "assert" in task_lower or "qa" in task_lower:
                if mod["id"] in ("MOD_TRUTH_ANCHOR_VERIFICATION", "MOD_SOCRATIC_INVARIANCE_TESTING"):
                    score += 3.0

            scored_modules.append((score, mod))

        # Sort descending by score
        scored_modules.sort(key=lambda x: x[0], reverse=True)

        # Enforce diversity across cognitive families where possible
        selected: List[Dict[str, Any]] = []
        seen_families = set()

        for score, mod in scored_modules:
            if len(selected) >= top_k:
                break
            # Prefer unique families first if score > 0
            fam = mod.get("family", "")
            if fam not in seen_families or score >= 4.0:
                selected.append({**mod, "selection_score": round(score, 2)})
                seen_families.add(fam)

        # If top_k not reached due to family deduplication, fill remainder
        if len(selected) < top_k:
            for score, mod in scored_modules:
                if len(selected) >= top_k:
                    break
                if mod["id"] not in [s["id"] for s in selected]:
                    selected.append({**mod, "selection_score": round(score, 2)})

        return selected

    def adapt(self, selected_modules: List[Dict[str, Any]], task_text: str) -> List[Dict[str, Any]]:
        """
        Stage 2 (Adapt): Adapts abstract reasoning primitives to the concrete domain of the task.
        """
        adapted = []
        for mod in selected_modules:
            mod_id = mod["id"]
            name = mod["name"]
            family = mod["family"]

            # Generate task-grounded adaptation directives
            directives = []
            if family == "decomposition_structure":
                directives.append(f"Decompose '{task_text}' into decoupled sub-units preserving single responsibility.")
                directives.append("Define clean input/output interfaces and explicit type signatures.")
            elif family == "critical_adversarial":
                directives.append(f"Formulate counterfactual failure cases for '{task_text}'.")
                directives.append("Interrogate edge cases, zero/null inputs, and deliberate fault injections.")
            elif family == "system_dynamics":
                directives.append("Analyze race conditions, double-click submissions, and asynchronous timing barriers.")
                directives.append("Enforce idempotency: repeating the action must produce exactly one state mutation.")
            elif family == "empirical_grounding":
                directives.append("Anchor all locators and assertions in concrete DOM accessibility or AST dataflow.")
                directives.append("Ban assumptions; require explicit empirical evidence before concluding passes.")
            elif family == "resilience_recovery":
                directives.append("Enforce bounded retries (K <= 3) and circuit breaker stops on 3 consecutive errors.")
                directives.append("Ensure graceful degradation and clean state teardown on unexpected exceptions.")

            adapted.append({
                "module_id": mod_id,
                "module_name": name,
                "family": family,
                "abstract_principle": mod.get("description", ""),
                "grounded_directives": directives
            })

        return adapted

    def implement(self, adapted_modules: List[Dict[str, Any]], task_text: str) -> Dict[str, Any]:
        """
        Stage 3 (Implement): Synthesizes an executable JSON reasoning plan (Scaffolding).
        """
        steps = []
        # Phase 1: Step-Back & Invariant Formulation
        steps.append({
            "phase": 1,
            "phase_name": "Step-Back Principle Formulation",
            "objective": "Identify governing physical/architectural invariants before code authoring.",
            "instructions": [
                f"State the core mental model or distributed invariants governing '{task_text}'.",
                "Formulate non-negotiable boundaries: clean state pre-conditions, idempotency requirements, SLA budgets."
            ]
        })

        # Phase 2: Primitive-Driven Execution
        phase_num = 2
        for item in adapted_modules:
            steps.append({
                "phase": phase_num,
                "phase_name": f"Reasoning Action: {item['module_name']}",
                "module_id": item["module_id"],
                "cognitive_family": item["family"],
                "directives": item["grounded_directives"]
            })
            phase_num += 1

        # Final Phase: Truth Anchor & Verification
        steps.append({
            "phase": phase_num,
            "phase_name": "Truth Anchor & Falsification Verification",
            "objective": "Prove delivery correctness without fake passes or unasserted logic.",
            "instructions": [
                "Execute empirical verification sensors (tests, linters, or live inspection).",
                "Confirm that negative and boundary cases fail gracefully and positive cases pass genuinely."
            ]
        })

        return {
            "status": "SUCCESS",
            "framework": "Self-Discover (Google DeepMind Elicitation)",
            "task": task_text,
            "selected_modules_count": len(adapted_modules),
            "reasoning_scaffolding": {
                "total_phases": len(steps),
                "execution_plan": steps
            }
        }

    def run(self, task_text: str, top_k: int = 4) -> Dict[str, Any]:
        """Executes full 3-stage Self-Discover cycle."""
        selected = self.select(task_text, top_k=top_k)
        adapted = self.adapt(selected, task_text)
        scaffold = self.implement(adapted, task_text)
        scaffold["selected_primitives"] = [
            {"id": m["id"], "name": m["name"], "family": m["family"], "score": m.get("selection_score", 0.0)}
            for m in selected
        ]
        return scaffold


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dynamic Reasoning Scaffolding Engine (Google DeepMind Self-Discover Pattern)"
    )
    parser.add_argument("--task", type=str, required=True, help="Task description or problem statement to compose reasoning for")
    parser.add_argument("--modules-file", type=str, default=DEFAULT_MODULES_PATH, help="Path to atomic_modules.json catalog")
    parser.add_argument("--max-modules", type=int, default=4, help="Maximum number of atomic modules to select (default: 4)")
    parser.add_argument("--output", type=str, default="", help="Optional file path to write generated JSON scaffolding to")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format only")

    args = parser.parse_args()

    engine = SelfDiscoverEngine(modules_file=args.modules_file)
    result = engine.run(task_text=args.task, top_k=args.max_modules)

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
        print("  SELF-DISCOVER REASONING SCAFFOLDING ENGINE (DEEPMIND PATTERN)")
        print("=" * 70)
        print(f"Task: {result['task']}")
        print(f"Selected Primitives ({result['selected_modules_count']}):")
        for p in result.get("selected_primitives", []):
            print(f"  - [{p['id']}] {p['name']} ({p['family']}) [Relevance: {p['score']}]")
        print("-" * 70)
        print(f"Synthesized Phases ({result['reasoning_scaffolding']['total_phases']}):")
        for p in result["reasoning_scaffolding"]["execution_plan"]:
            print(f"  Phase {p['phase']}: {p['phase_name']}")
            for ins in p.get("instructions", p.get("directives", [])):
                print(f"    * {ins}")
        print("=" * 70)
        if args.output:
            print(f"Scaffolding saved to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
