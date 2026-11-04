#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Multi-Trial Episodic Reflexion Loop for Autonomous Healing (Noah Shinn / Reflexion Pattern)
------------------------------------------------------------------------------------------
Replaces single-shot heuristic locator healing with an iterative, multi-trial reflection
loop (K=3). When a test fails:
  1. Evaluator extracts failure stacktrace & symptom.
  2. Reflexion Generator creates a 2-line verbal diagnosis of why the patch/locator failed.
  3. Memory Buffer accumulates trials across attempts.
  4. Actor synthesizes the next patch conditioned on previous reflections.
  5. Upon pass -> records to positive cache (healing_cache & lessons_learned).
  6. Upon exhaustion of K=3 -> records to negative cache (failed_fixes) to block blind retries.

Reference:
  - Noah Shinn et al. (Reflexion: Language Agents with Verbal Reinforcement Learning).
  - Synapse-Hub Subsystem 2: Section 6.3 of agent_skill_training_analysis.md.
"""

import os
import sys
import json
import argparse
from dataclasses import dataclass, asdict
from typing import List, Optional, Callable, Dict, Any, Tuple

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import cache_resolver


@dataclass
class ReflexionTrial:
    trial_number: int
    patch_attempt: str
    error_feedback: str
    verbal_reflection: str
    is_passing: bool


class ClosedLoopHealer:
    """Orchestrates multi-trial reflection loops for self-healing test automation."""

    def __init__(self, max_trials: int = 3):
        self.max_trials = max_trials
        self.memory_buffer: List[ReflexionTrial] = []

    def generate_reflection(self, error_sig: str, patch_attempt: str, previous_error: str) -> str:
        """
        Synthesizes a structured 2-line verbal reflection explaining why the previous attempt failed
        and prescribing the strategic adjustment for the next attempt.
        """
        err_lower = (previous_error or error_sig).lower()
        if "staleelement" in err_lower or "stale" in err_lower:
            return "Reflection: DOM node re-rendered asynchronously after API call. Adjustment: Must wait for loader/backdrop detachment before re-querying element."
        elif "intercepted" in err_lower or "click" in err_lower:
            return "Reflection: Click intercepted by fading overlay/spinner animation. Adjustment: Use smart wait for overlay detachment or bypass via safe JS click."
        elif "timeout" in err_lower or "nosuchelement" in err_lower:
            return "Reflection: Static selector did not appear within timeout window. Adjustment: Fallback to Accessibility role/label or dynamic data-testid attribute."
        elif "assert" in err_lower:
            return "Reflection: Assertion condition violated actual state. Adjustment: Check if state change was asynchronous or if expected data was corrupted."
        return f"Reflection: Patch attempt failed with '{error_sig[:80]}'. Adjustment: Re-examine live DOM tree and avoid static sleeps."

    def execute_healing_loop(
        self,
        failing_test: str,
        initial_error: str,
        patch_synthesizer: Callable[[str, str, List[ReflexionTrial]], str],
        verifier: Callable[[str, str], Tuple[bool, str]],
        page_context: str = "GLOBAL"
    ) -> Tuple[bool, Optional[str], List[ReflexionTrial]]:
        """
        Executes up to max_trials attempts.
        Returns (is_success, winning_patch, trial_history).
        """
        self.memory_buffer.clear()
        current_error = initial_error

        print(f"\n🔄 [REFLEXION LOOP] Starting Multi-Trial Self-Healing (Max K={self.max_trials}) for '{failing_test}'...")

        for t in range(1, self.max_trials + 1):
            prev_attempt = self.memory_buffer[-1].patch_attempt if self.memory_buffer else ""
            reflection = self.generate_reflection(initial_error, prev_attempt, current_error)

            print(f"\n  --- Trial {t}/{self.max_trials} ---")
            print(f"  🧠 Verbal Reflection: {reflection}")

            # Synthesize next patch conditioned on reflection memory
            candidate_patch = patch_synthesizer(failing_test, reflection, self.memory_buffer)
            print(f"  🔧 Candidate Patch  : {candidate_patch[:100]}...")

            # Verify patch in headless execution
            is_pass, new_error = verifier(failing_test, candidate_patch)

            trial = ReflexionTrial(
                trial_number=t,
                patch_attempt=candidate_patch,
                error_feedback=new_error if not is_pass else "PASS",
                verbal_reflection=reflection,
                is_passing=is_pass
            )
            self.memory_buffer.append(trial)

            if is_pass:
                print(f"  ✅ [TRIAL {t} SUCCESS] Patch verified passing!")
                self._record_positive_memory(page_context, initial_error, candidate_patch, reflection)
                return True, candidate_patch, self.memory_buffer
            else:
                print(f"  ❌ [TRIAL {t} FAILED] Error: {new_error[:100]}")
                current_error = new_error

        print(f"\n⚠️  [REFLEXION EXHAUSTED] Failed after {self.max_trials} trials. Persisting to negative memory blacklist.")
        self._record_negative_memory(initial_error, self.memory_buffer[-1].patch_attempt, f"Failed across {self.max_trials} multi-trial attempts")
        return False, None, self.memory_buffer

    def _record_positive_memory(self, page_context: str, error_sig: str, patch: str, reflection: str):
        try:
            cache_resolver.record_lesson(
                page_context=page_context,
                error_signature=error_sig,
                root_cause=reflection,
                failed_attempt="Initial failing code",
                successful_fix=patch,
                lesson_summary=reflection
            )
        except Exception as e:
            sys.stderr.write(f"Notice: Failed to record positive memory: {e}\n")

    def _record_negative_memory(self, error_sig: str, failed_patch: str, reason: str):
        try:
            cache_resolver.record_failed_fix(
                error_signature=error_sig,
                patch=failed_patch,
                reason=reason,
                agent_role="failure-analyst"
            )
        except Exception as e:
            sys.stderr.write(f"Notice: Failed to record negative memory: {e}\n")


def main():
    parser = argparse.ArgumentParser(description="Multi-Trial Episodic Reflexion Self-Healer")
    parser.add_argument("--test", default="SampleTest", help="Failing test identifier")
    parser.add_argument("--error", default="ElementClickInterceptedException", help="Initial error signature")
    parser.add_argument("--max-trials", type=int, default=3, help="Max trials (default: 3)")
    args = parser.parse_args()

    healer = ClosedLoopHealer(max_trials=args.max_trials)
    reflection = healer.generate_reflection(args.error, "", "")
    print(json.dumps({
        "test": args.test,
        "error": args.error,
        "max_trials": args.max_trials,
        "initial_reflection": reflection
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
