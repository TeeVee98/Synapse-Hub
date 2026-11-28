#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""4-Scenario Verification Battery for M5: Spec-Kit Go/Kill Gate, Converge, Complexity & PlanHarvester Memory Archive."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def test_assess_idea_converge_and_memory_archive_positive(tmp_path: Path) -> None:
    """Positive: strong criteria -> go, converge detects unbuilt files, harvester archives memory snapshot."""
    from tools.core.task_graph_memory import TaskGraphMemory
    from tools.design.plan_harvester import archive_completed_plan_memory
    from tools.design.super_plan_engine import (
        assess_idea_gate,
        converge_plan_delta,
        score_milestone_complexity,
    )

    # 1. Idea assessment: GO
    verdict = assess_idea_gate(
        slug="graph-memory",
        criteria={
            "problem_validity": "strong",
            "evidence_strength": "strong",
            "value_vs_inaction": "adequate",
            "feasibility_fit": "strong",
            "strategic_fit": "strong",
            "risk_posture": "adequate",
        },
        concept_shaped=True,
    )
    assert verdict.verdict == "go"
    assert verdict.downgraded_from_go is False
    assert verdict.slug == "graph-memory"

    # 2. Converge spec-to-code delta
    existing_file = tmp_path / "tools" / "existing.py"
    existing_file.parent.mkdir(parents=True, exist_ok=True)
    existing_file.write_text("def ok():\n    return 1\n", encoding="utf-8")

    plan_md = """### Milestone 1: Existing
- **Node ID:** `M1` | **depends_on:** `[]`
- **Write Set:** `['tools/existing.py']`

### Milestone 2: Unbuilt
- **Node ID:** `M2` | **depends_on:** `[M1]`
- **Write Set:** `['tools/unbuilt_new.py']`
"""
    delta = converge_plan_delta(plan_md, repo_root=str(tmp_path))
    assert delta["completed_milestones"] == ["M1"]
    assert delta["remaining_milestones"] == ["M2"]
    assert "tools/unbuilt_new.py" in delta["missing_files"]

    # 3. Complexity scorer (task-master pattern)
    high_c = score_milestone_complexity(
        files=["a.py", "b.py", "c.py"],
        has_state_mutation=True,
        cross_boundary=True,
        fan_in=40,
    )
    assert high_c["complexity_score"] >= 7
    assert high_c["expand_recommended"] is True

    # 4. PlanHarvester memory archival (shrimp pattern)
    snap_id = archive_completed_plan_memory(
        plan_slug="graph-memory",
        title="Task Graph Memory Upgrade",
        calibration={"accuracy_score": 1.0, "planned_files": ["tools/existing.py"]},
        repo_root=str(tmp_path),
    )
    assert snap_id >= 1
    with TaskGraphMemory(tmp_path / ".synapse" / "task_graph.db") as mem:
        snaps = mem.list_archived_snapshots()
        assert len(snaps) == 1
        assert snaps[0]["plan_slug"] == "graph-memory"


def test_assess_idea_and_symlink_guard_negative(tmp_path: Path) -> None:
    """Negative: weak evidence downgrades go->needs-clarification; weak problem -> kill; symlink escape blocked."""
    from tools.design.super_plan_engine import assess_idea_gate, resolve_safe_plan_path

    # Weak evidence forces downgrade from go -> needs-clarification
    v_clarify = assess_idea_gate(
        slug="unproven-cache",
        criteria={
            "problem_validity": "strong",
            "evidence_strength": "unknown",
            "value_vs_inaction": "strong",
            "feasibility_fit": "adequate",
            "strategic_fit": "adequate",
            "risk_posture": "adequate",
        },
        concept_shaped=True,
    )
    assert v_clarify.verdict == "needs-clarification"
    assert v_clarify.downgraded_from_go is True
    assert len(v_clarify.required_clarifications) >= 1

    # Weak problem validity -> kill
    v_kill = assess_idea_gate(
        slug="vanity-rewrite",
        criteria={
            "problem_validity": "weak",
            "evidence_strength": "strong",
            "value_vs_inaction": "weak",
            "feasibility_fit": "adequate",
            "strategic_fit": "weak",
            "risk_posture": "weak",
        },
        concept_shaped=True,
    )
    assert v_kill.verdict == "kill"

    # Symlink traversal attack blocked
    outside = tmp_path.parent / "outside_escape_target"
    outside.mkdir(exist_ok=True)
    synapse_dir = tmp_path / ".synapse"
    synapse_dir.mkdir(parents=True, exist_ok=True)
    evil_link = synapse_dir / "plans"
    os.symlink(str(outside), str(evil_link))

    with pytest.raises(ValueError, match="symlink|escape|traversal"):
        resolve_safe_plan_path("my-plan", repo_root=str(tmp_path))


def test_super_plan_reasoning_boundaries(tmp_path: Path) -> None:
    """Boundary: unshaped concept downgrades go, invalid slug rejected, low complexity does not expand."""
    from tools.design.super_plan_engine import (
        assess_idea_gate,
        resolve_safe_plan_path,
        score_milestone_complexity,
    )

    v_unshaped = assess_idea_gate(
        slug="raw-idea",
        criteria={
            "problem_validity": "strong",
            "evidence_strength": "adequate",
            "value_vs_inaction": "adequate",
            "feasibility_fit": "adequate",
            "strategic_fit": "adequate",
            "risk_posture": "adequate",
        },
        concept_shaped=False,
    )
    assert v_unshaped.verdict == "needs-clarification"
    assert v_unshaped.downgraded_from_go is True

    with pytest.raises(ValueError, match="slug"):
        resolve_safe_plan_path("///...", repo_root=str(tmp_path))

    low_c = score_milestone_complexity(files=["one.py"], has_state_mutation=False, cross_boundary=False, fan_in=0)
    assert 1 <= low_c["complexity_score"] <= 4
    assert low_c["expand_recommended"] is False


def test_super_plan_new_cli_subcommands_json(tmp_path: Path) -> None:
    """CLI Contract: assess-idea and converge subcommands emit valid JSON with exit 0."""
    script = Path(__file__).resolve().parents[1] / "tools" / "design" / "super_plan_engine.py"

    r1 = subprocess.run(
        [
            sys.executable,
            str(script),
            "assess-idea",
            "--slug",
            "mcp-reasoning",
            "--criteria",
            "problem_validity=strong,evidence_strength=adequate,value_vs_inaction=strong,feasibility_fit=strong,strategic_fit=strong,risk_posture=adequate",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r1.returncode == 0, r1.stderr
    p1 = json.loads(r1.stdout)
    assert p1["verdict"] == "go"

    plan_file = tmp_path / "plan.md"
    plan_file.write_text("### Milestone 1: Test\n- **Node ID:** `M1` | **depends_on:** `[]`\n- **Write Set:** `['missing_file.py']`\n", encoding="utf-8")
    r2 = subprocess.run(
        [sys.executable, str(script), "converge", "--file", str(plan_file), "--repo-root", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r2.returncode == 0, r2.stderr
    p2 = json.loads(r2.stdout)
    assert p2["remaining_milestones"] == ["M1"]
