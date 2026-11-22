# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for tools/reasoning/self_discover_engine.py (Google DeepMind Pattern)."""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

from reasoning.self_discover_engine import SelfDiscoverEngine


def test_self_discover_catalog_loading():
    engine = SelfDiscoverEngine()
    assert len(engine.modules_catalog) == 36
    ids = [m["id"] for m in engine.modules_catalog]
    assert "MOD_FIRST_PRINCIPLES" in ids
    assert "MOD_IDEMPOTENCY_INVARIANT_CHECK" in ids
    assert "MOD_CONCURRENCY_RACE_MODELING" in ids
    assert "MOD_CIRCUIT_BREAKER_PROTOCOL" in ids


def test_self_discover_select_stage():
    engine = SelfDiscoverEngine()
    task = "Design idempotent payment checkout with double-click race condition defense"
    selected = engine.select(task, top_k=4)

    assert len(selected) == 4
    selected_ids = [s["id"] for s in selected]
    assert "MOD_IDEMPOTENCY_INVARIANT_CHECK" in selected_ids
    assert "MOD_CONCURRENCY_RACE_MODELING" in selected_ids

    # Scores must be positive and sorted descending
    scores = [s["selection_score"] for s in selected]
    assert scores == sorted(scores, reverse=True)


def test_self_discover_adapt_stage():
    engine = SelfDiscoverEngine()
    task = "Refactor BasePage to eliminate static sleeps"
    selected = engine.select(task, top_k=3)
    adapted = engine.adapt(selected, task)

    assert len(adapted) == 3
    for a in adapted:
        assert "module_id" in a
        assert "module_name" in a
        assert "grounded_directives" in a
        assert len(a["grounded_directives"]) >= 1


def test_self_discover_implement_stage():
    engine = SelfDiscoverEngine()
    task = "Audit auth token refresh under network flakiness"
    result = engine.run(task, top_k=3)

    assert result["status"] == "SUCCESS"
    assert result["task"] == task
    assert result["selected_modules_count"] == 3

    scaffold = result["reasoning_scaffolding"]
    assert scaffold["total_phases"] >= 4
    phases = scaffold["execution_plan"]

    # Phase 1 must be Step-Back Principle Formulation
    assert phases[0]["phase_name"] == "Step-Back Principle Formulation"
    # Final phase must be Truth Anchor & Falsification
    assert phases[-1]["phase_name"] == "Truth Anchor & Falsification Verification"
