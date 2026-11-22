# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for tools/ai/textgrad_optimizer.py (Stanford TextGrad Pattern)."""

import os
import sys
import tempfile

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

from ai.textgrad_optimizer import TextGradOptimizer


def test_textgrad_evaluate_clean_code():
    clean_code = """
def test_valid_operation():
    expected = 42
    actual = 42
    assert actual == expected
"""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(clean_code)
        f_path = f.name

    try:
        opt = TextGradOptimizer(target_path=f_path)
        loss, grads = opt.evaluate_loss(clean_code, "test_clean.py")
        assert loss == 0.0
        assert len(grads) == 0
        assert opt.compute_quality_score(loss) == 10.0
    finally:
        os.remove(f_path)


def test_textgrad_evaluate_and_converge_defective_code():
    defective_code = """
import time

def test_flaky_flow():
    try:
        time.sleep(5)
        res = False
        assert res is True
    except Exception as e:
        pass
"""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(defective_code)
        f_path = f.name

    try:
        opt = TextGradOptimizer(target_path=f_path, max_iterations=3)
        res = opt.optimize(in_place=False)

        assert res["initial_quality"] != "10.0/10"
        assert res["loss_reduction"] > 0
        assert res["total_iterations"] >= 1
        assert res["is_converged"] is True

        # Check gradients
        initial_grads = res["history"][0]["gradients"]
        categories = [g["category"] for g in initial_grads]
        assert "TRUTH_ANCHOR_VIOLATION" in categories
        assert "FLAKINESS_INVARIANT" in categories
    finally:
        os.remove(f_path)
