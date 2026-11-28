# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""4-scenario verification suite for M6: True Reverse-Mode TextGrad Autograd DAG & Momentum."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.ai.textgrad_optimizer import (
    AutogradStepReceiptDTO,
    TGDOptimizerWithMomentum,
    TextVariable,
    TextualComputationGraph,
    reduce_gradients,
)


def test_textgrad_dag_backward_and_constraints() -> None:
    """Positive + Negative scenario: 3-node DAG reverse topo backward(), multi-path reduction, momentum, hard constraints."""
    prompt_var = TextVariable(
        name="system_prompt",
        value="Generate Playwright test",
        role_description="Prompt instructing QA test generation",
        requires_grad=True,
    )
    frozen_ctx = TextVariable(
        name="static_schema",
        value="OpenAPI v3.1",
        role_description="Immutable API spec",
        requires_grad=False,
    )
    code_var = TextVariable(
        name="test_code",
        value="time.sleep(2)\nassert True",
        role_description="Generated test script",
        requires_grad=True,
        predecessors=[prompt_var, frozen_ctx],
        grad_fn=lambda _node, incoming: {
            "system_prompt": f"Propagated from code: {incoming}",
            "static_schema": "Should never attach because requires_grad=False",
        },
    )
    loss_var = TextVariable(
        name="eval_loss",
        value="FAIL: static sleep detected",
        role_description="Evaluation loss node",
        requires_grad=True,
        predecessors=[code_var],
        grad_fn=lambda _node, incoming: {"test_code": f"Eliminate static sleep: {incoming}"},
    )

    graph = TextualComputationGraph(loss_var)
    order = graph.backward("Replace time.sleep with web-first assertion")
    # Must propagate in reverse topological order: eval_loss -> test_code -> system_prompt
    assert order.index("eval_loss") < order.index("test_code") < order.index("system_prompt")
    assert len(code_var.gradients) == 1
    assert len(prompt_var.gradients) == 1
    assert frozen_ctx.gradients == []

    # Multi-path reduce_gradients deduplicates and preserves order
    reduced = reduce_gradients(["fix sleep", "fix sleep", "add assert"])
    assert reduced == "1. fix sleep\n2. add assert"

    # Hard constraint: updated value must preserve "assert"
    def must_keep_assert(candidate: str) -> bool:
        return "assert" in candidate

    opt = TGDOptimizerWithMomentum(
        parameters=[code_var],
        constraints=[must_keep_assert],
        momentum_window=2,
    )

    # Step 1: valid update satisfies constraint and reduces loss
    receipts_ok = opt.step(
        updater=lambda var, grad, mem: var.value.replace("time.sleep(2)", "expect(btn).to_be_visible()"),
        loss_evaluator=lambda var: 2.0 if "time.sleep" in var.value else 0.0,
    )
    assert len(receipts_ok) == 1
    r1 = receipts_ok[0]
    assert isinstance(r1, AutogradStepReceiptDTO)
    assert r1.step_index == 1
    assert r1.loss_before == 2.0
    assert r1.loss_after == 0.0
    assert r1.constraints_satisfied is True
    assert r1.gradient_count == 1
    assert r1.momentum_window == 2
    assert "expect(btn).to_be_visible()" in code_var.value
    with pytest.raises(FrozenInstanceError):
        r1.loss_after = 9.9  # type: ignore[misc]

    # Step 2: constraint-violating update (strips assert) must be rejected & original value preserved
    code_var.gradients.append("strip everything")
    prev_val = code_var.value
    receipts_bad = opt.step(
        updater=lambda _var, _grad, _mem: "no checks left",
        loss_evaluator=lambda _var: 1.0,
    )
    assert receipts_bad[0].constraints_satisfied is False
    assert code_var.value == prev_val

    # Step 3: momentum window=2 caps memory length to 2
    code_var.gradients.append("grad_3")
    opt.step(
        updater=lambda var, _grad, _mem: var.value + "\nassert 1 == 1",
        loss_evaluator=lambda _var: 0.0,
    )
    assert len(opt.gradient_memory["test_code"]) == 2
    opt.zero_grad()
    assert code_var.gradients == []


def test_textgrad_autograd_negative_and_boundary() -> None:
    """Negative & Boundary scenarios: cyclic DAG, invalid variable name/momentum, empty gradients, zero-grad leaf."""
    with pytest.raises(ValueError, match="name"):
        TextVariable("   ", "v", "role")
    with pytest.raises(ValueError, match="momentum_window"):
        TGDOptimizerWithMomentum([], momentum_window=0)

    assert reduce_gradients([]) == ""
    assert reduce_gradients(["  ", ""]) == ""

    # Cyclic DAG detection
    a = TextVariable("a", "va", "ra")
    b = TextVariable("b", "vb", "rb", predecessors=[a])
    a.predecessors.append(b)
    with pytest.raises(ValueError, match="Cycle"):
        TextualComputationGraph(b).topological_order()

    # Leaf with no gradients skips mutation cleanly
    leaf = TextVariable("leaf", "clean code", "leaf role", requires_grad=True)
    opt = TGDOptimizerWithMomentum([leaf], momentum_window=2)
    recs = opt.step(
        updater=lambda var, _g, _m: var.value + " mutated",
        loss_evaluator=lambda _v: 0.0,
    )
    assert recs[0].gradient_count == 0
    assert leaf.value == "clean code"


def test_textgrad_cli_json_contract(tmp_path: Path) -> None:
    """CLI scenario: legacy --target --json remains 100% compatible and --autograd-demo --json exits 0."""
    worktree_root = Path(__file__).resolve().parents[1]
    script = str(worktree_root / "tools" / "ai" / "textgrad_optimizer.py")

    sample = tmp_path / "sample_t.py"
    sample.write_text("import time\ndef test_x():\n    time.sleep(1)\n    assert True\n", encoding="utf-8")

    r_legacy = subprocess.run(
        [sys.executable, script, "--target", str(sample), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r_legacy.returncode == 0, r_legacy.stderr
    legacy_data = json.loads(r_legacy.stdout)
    assert legacy_data["status"] in ("PASS", "OPTIMIZED")

    r_demo = subprocess.run(
        [sys.executable, script, "--autograd-demo", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r_demo.returncode == 0, r_demo.stderr
    demo_data = json.loads(r_demo.stdout)
    assert demo_data["status"] == "ok"
    assert demo_data["receipt"]["constraints_satisfied"] is True
    assert demo_data["receipt"]["loss_after"] < demo_data["receipt"]["loss_before"]
