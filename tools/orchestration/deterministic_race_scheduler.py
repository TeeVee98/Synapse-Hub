#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Deterministic Concurrency & Race Condition Interleaving Scheduler
-----------------------------------------------------------------
Replaces non-deterministic sleep-based concurrency tests with exhaustive
or bounded permutation interleaving. Explores critical preemption points
to detect lost updates, dirty reads, double-actions, and broken invariants.
"""

import os
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Callable, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass


@dataclass
class ConcurrentAction:
    """Represents a sequence of operations performed by an actor/thread."""
    actor_id: str
    steps: List[Tuple[str, Callable[[Any], Any]]]


@dataclass
class FailingSchedule:
    """Details of a schedule interleaving that triggered a race condition."""
    schedule: List[str]
    final_state: Dict[str, Any]
    violation_reason: str


@dataclass
class RaceAuditResult:
    """Summary of deterministic race condition audit."""
    has_race_condition: bool
    invariant_name: str
    schedules_explored: int
    failing_schedules: List[FailingSchedule] = field(default_factory=list)
    duration_ms: float = 0.0


class DeterministicRaceScheduler:
    """
    Exhaustive and Bounded Deterministic Interleaving Scheduler.
    Permutes thread/actor preemption points without static sleeps.
    """

    @classmethod
    def _generate_interleavings(
        cls, actions_remaining: List[List[Tuple[str, Callable[[Any], Any]]]]
    ) -> List[List[Tuple[str, Callable[[Any], Any]]]]:
        """
        Recursively generates all valid interleavings of steps across actors,
        strictly preserving the internal FIFO ordering of steps within each actor.
        """
        # Filter out empty action queues
        active = [(i, q) for i, q in enumerate(actions_remaining) if q]
        if not active:
            return [[]]

        all_interleavings: List[List[Tuple[str, Callable[[Any], Any]]]] = []

        for idx, queue in active:
            head = queue[0]
            rest_for_idx = queue[1:]

            # Clone actions state with head removed from actor `idx`
            next_state = [list(q) for q in actions_remaining]
            next_state[idx] = rest_for_idx

            sub_interleavings = cls._generate_interleavings(next_state)
            for sub in sub_interleavings:
                all_interleavings.append([head] + sub)

        return all_interleavings

    @classmethod
    def audit_concurrency(
        cls,
        action_factory: Callable[[List[str]], Tuple[Any, List[ConcurrentAction]]],
        invariant_check: Callable[[Any], bool],
        invariant_name: str = "Invariant Holds",
        max_schedules: int = 200,
    ) -> RaceAuditResult:
        """
        Audits concurrent actions across all deterministic step interleavings.
        Returns RaceAuditResult with detailed failing schedules if a race condition is found.
        """
        t0 = time.perf_counter()

        # Probe actions structure using dummy run
        probe_svc, probe_actions = action_factory([])
        step_queues = [list(act.steps) for act in probe_actions]

        # Generate all permutations preserving actor internal step order
        all_schedules = cls._generate_interleavings(step_queues)
        if len(all_schedules) > max_schedules:
            all_schedules = all_schedules[:max_schedules]

        failing: List[FailingSchedule] = []

        for sched_steps in all_schedules:
            sched_labels = [s[0] for s in sched_steps]
            # Create fresh instance for this schedule
            service, actions = action_factory(sched_labels)

            # Map step labels to concrete lambdas for this fresh instance
            step_map: Dict[str, Callable[[Any], Any]] = {}
            for act in actions:
                for lbl, fn in act.steps:
                    step_map[lbl] = fn

            # Execute steps in deterministic interleaved order
            for lbl in sched_labels:
                step_fn = step_map.get(lbl)
                if step_fn:
                    step_fn(service)

            # Assert invariant
            is_valid = False
            try:
                is_valid = bool(invariant_check(service))
            except Exception:
                is_valid = False

            if not is_valid:
                # Capture final state
                state_dict: Dict[str, Any] = {}
                if hasattr(service, "__dict__"):
                    for k, v in service.__dict__.items():
                        if not k.startswith("_"):
                            state_dict[k] = v
                else:
                    state_dict["value"] = str(service)

                failing.append(FailingSchedule(
                    schedule=sched_labels,
                    final_state=state_dict,
                    violation_reason=f"Invariant violated: {invariant_name}",
                ))

        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        has_race = len(failing) > 0

        return RaceAuditResult(
            has_race_condition=has_race,
            invariant_name=invariant_name,
            schedules_explored=len(all_schedules),
            failing_schedules=failing,
            duration_ms=duration_ms,
        )
