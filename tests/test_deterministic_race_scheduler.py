# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Tests for Deterministic Concurrency & Race Condition Interleaving Scheduler
Validates deterministic execution interleaving, lost-update detection,
double-spend detection, and race-free mutex verification without flaky sleeps.
"""

import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_TESTS_DIR)
_TOOLS_DIR = os.path.join(_REPO_ROOT, "tools")
for _p in (_REPO_ROOT, _TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.orchestration.deterministic_race_scheduler import (
    DeterministicRaceScheduler,
    ConcurrentAction,
    RaceAuditResult,
)


def test_deterministic_scheduler_detects_lost_update_race():
    """
    Simulates classic Read-Modify-Write race condition:
    Two actors increment a shared counter without locking.
    Initial: counter = 0
    Actor 1: Read counter, compute counter + 1, write counter
    Actor 2: Read counter, compute counter + 1, write counter
    Expected serial: counter = 2
    Interleaved: counter = 1 (Lost update!)
    """
    class CounterService:
        def __init__(self):
            self.counter = 0

        def create_increment_action(self, actor_id: str) -> ConcurrentAction:
            local = {}
            steps = [
                (f"{actor_id}:read", lambda s: local.update({"val": self.counter})),
                (f"{actor_id}:compute", lambda s: local.update({"val": local["val"] + 1})),
                (f"{actor_id}:write", lambda s: setattr(self, "counter", local["val"])),
            ]
            return ConcurrentAction(actor_id=actor_id, steps=steps)

    def run_simulation(schedule_indices):
        service = CounterService()
        act1 = service.create_increment_action("actor1")
        act2 = service.create_increment_action("actor2")
        return service, [act1, act2]

    scheduler = DeterministicRaceScheduler()
    res: RaceAuditResult = scheduler.audit_concurrency(
        action_factory=run_simulation,
        invariant_check=lambda svc: svc.counter == 2,
        invariant_name="counter == 2 (Zero lost updates)",
    )

    assert res.has_race_condition is True
    assert len(res.failing_schedules) >= 1
    # Verify that at least one schedule produced counter == 1
    assert any(fs.final_state.get("counter") == 1 for fs in res.failing_schedules)


def test_deterministic_scheduler_passes_race_free_atomic():
    """
    With atomic/locked increment, counter is always 2 regardless of interleaving.
    """
    class AtomicCounterService:
        def __init__(self):
            self.counter = 0
            self.lock = False

        def create_increment_action(self, actor_id: str) -> ConcurrentAction:
            steps = [
                (f"{actor_id}:atomic_inc", lambda s: setattr(self, "counter", self.counter + 1)),
            ]
            return ConcurrentAction(actor_id=actor_id, steps=steps)

    def run_simulation(schedule_indices):
        service = AtomicCounterService()
        act1 = service.create_increment_action("actor1")
        act2 = service.create_increment_action("actor2")
        return service, [act1, act2]

    scheduler = DeterministicRaceScheduler()
    res = scheduler.audit_concurrency(
        action_factory=run_simulation,
        invariant_check=lambda svc: svc.counter == 2,
        invariant_name="counter == 2 (Atomic increments preserved)",
    )

    assert res.has_race_condition is False
    assert len(res.failing_schedules) == 0
    assert res.schedules_explored >= 1
    assert 0.0 <= res.duration_ms < 1000.0


def test_deterministic_scheduler_max_schedules_bounding():
    """Verifies that max_schedules truncates the permutation search space."""
    class SimpleService:
        def create_action(self, actor_id: str) -> ConcurrentAction:
            return ConcurrentAction(actor_id=actor_id, steps=[(f"{actor_id}:1", lambda s: None), (f"{actor_id}:2", lambda s: None)])

    def run_sim(sched):
        svc = SimpleService()
        return svc, [svc.create_action("a"), svc.create_action("b")]

    scheduler = DeterministicRaceScheduler()
    # 2 actions with 2 steps each = 6 permutations. With max_schedules=2, only 2 explored.
    res = scheduler.audit_concurrency(
        action_factory=run_sim,
        invariant_check=lambda s: True,
        max_schedules=2,
    )
    assert res.schedules_explored == 2


def test_deterministic_scheduler_invariant_exception_handled():
    """Verifies that exceptions in invariant_check are cleanly caught and flagged as violations."""
    class SimpleService:
        def create_action(self, actor_id: str) -> ConcurrentAction:
            return ConcurrentAction(actor_id=actor_id, steps=[(f"{actor_id}:1", lambda s: None)])

    def run_sim(sched):
        svc = SimpleService()
        return svc, [svc.create_action("a")]

    def buggy_invariant(svc):
        raise RuntimeError("Invariant calculation exploded")

    scheduler = DeterministicRaceScheduler()
    res = scheduler.audit_concurrency(
        action_factory=run_sim,
        invariant_check=buggy_invariant,
        invariant_name="Exploding Invariant",
    )
    assert res.has_race_condition is True
    assert len(res.failing_schedules) == 1


def test_deterministic_scheduler_detects_double_spend():
    """
    Two withdrawal requests of $80 from an account with $100.
    Serial: Exactly one succeeds, balance = 20.
    Unprotected Interleaved: Both check balance >= 80, both withdraw -> balance = -60!
    """
    class BankAccount:
        def __init__(self):
            self.balance = 100
            self.withdrawals_approved = 0

        def create_withdraw_action(self, actor_id: str, amount: int) -> ConcurrentAction:
            local = {}
            steps = [
                (f"{actor_id}:check", lambda s: local.update({"can_withdraw": self.balance >= amount})),
                (f"{actor_id}:commit", lambda s: (
                    setattr(self, "balance", self.balance - amount),
                    setattr(self, "withdrawals_approved", self.withdrawals_approved + 1)
                ) if local.get("can_withdraw") else None),
            ]
            return ConcurrentAction(actor_id=actor_id, steps=steps)

    def run_simulation(schedule_indices):
        account = BankAccount()
        act1 = account.create_withdraw_action("user1", 80)
        act2 = account.create_withdraw_action("user2", 80)
        return account, [act1, act2]

    scheduler = DeterministicRaceScheduler()
    res = scheduler.audit_concurrency(
        action_factory=run_simulation,
        invariant_check=lambda acc: acc.balance >= 0 and acc.withdrawals_approved <= 1,
        invariant_name="balance >= 0 and approvals <= 1 (No double spend)",
    )

    assert res.has_race_condition is True
    # Failing schedule has balance < 0 or approvals == 2
    failing = res.failing_schedules[0]
    assert failing.final_state.get("balance") == -60 or failing.final_state.get("withdrawals_approved") == 2
