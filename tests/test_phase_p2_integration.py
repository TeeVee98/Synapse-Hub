# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Phase P2/P3 Implementation Verification Suite
Tests:
  1. Mutant-Directed Textual Loss Optimizer (Subsystem 4 - TextGrad Pattern)
  2. Synapse-QA-Bench Tool Function Calling Benchmark (Subsystem 5 - Gorilla BFCL Pattern)
  3. Modern Package Standards (Subsystem 6 - agentskills.io Compliance)
"""

import os
import sys
import json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

import textgrad_mutation_optimizer
import synapse_qa_bench


def test_mutation_loss_evaluator():
    evaluator = textgrad_mutation_optimizer.MutationLossEvaluator(target_score=80.0)
    unasserted_code = """
def test_calc():
    a = 10
    b = 20
    if a > 5 and b < 30:
        total = a + b
"""
    res = evaluator.compute_loss(unasserted_code)
    assert res["status"] in ("PASS", "FAIL")
    assert "mutation_score" in res
    assert "textual_loss" in res


def test_textual_gradient_optimizer_convergence():
    optimizer = textgrad_mutation_optimizer.TextualGradientOptimizer(target_score=80.0, max_iterations=3)
    sample_code = """
def test_checkout_flow():
    amount = 500
    is_valid = True
    if amount > 100 and is_valid:
        order.submit()
"""
    success, opt_code, history = optimizer.optimize_assertions(sample_code)
    assert len(history) >= 1
    assert "assert" in opt_code
    assert any(term in opt_code for term in ("amount", "is_valid", "order"))
    assert history[-1]["score"] >= 80.0
    assert success is True


def test_synapse_qa_bench_execution():
    bench = synapse_qa_bench.SynapseQABench()
    report = bench.run_benchmark()
    assert report["total_cases"] >= 5
    assert report["overall_score"] >= 85.0
    assert report["passed"] is True
    assert report["tool_selection_accuracy"] >= 90.0


def test_agentskills_json_manifest():
    manifest_path = os.path.join(ROOT_DIR, "agentskills.json")
    assert os.path.exists(manifest_path), "agentskills.json must exist in repository root"
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["name"] == "Synapse-Hub"
    assert "skillsRoot" in data
    assert "standards" in data
