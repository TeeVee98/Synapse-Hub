# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""Unit tests for tools/mipro_assertion_tuner.py (DSPy v2 MIPROv2 Prompt Tuner)."""

import os
import sys
import tempfile
import shutil
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

from mipro_assertion_tuner import MiproAssertionTuner


@pytest.fixture
def temp_module_dir():
    tmp_dir = tempfile.mkdtemp()
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_compile_module(temp_module_dir):
    tuner = MiproAssertionTuner(repo_root=temp_module_dir)
    out_file = os.path.join(temp_module_dir, "optimized_module.json")

    res = tuner.compile_module(signature_name="AssertionGenerator", trials=10, out_module=out_file)

    assert res["status"] == "PASS"
    assert res["module"] == "AssertionGenerator"
    assert res["optimized_mutation_score"] >= 0.85
    assert res["estimated_token_footprint"] <= 800
    assert os.path.exists(out_file)


def test_evaluate_compiled_module(temp_module_dir):
    tuner = MiproAssertionTuner(repo_root=temp_module_dir)
    out_file = os.path.join(temp_module_dir, "compiled_test.json")
    tuner.compile_module(signature_name="AssertionGenerator", trials=5, out_module=out_file)

    eval_res = tuner.evaluate(out_file)
    assert eval_res["status"] == "PASS"
    assert eval_res["certification"] == "APPROVED"
    assert eval_res["mutation_score"] >= 0.85
