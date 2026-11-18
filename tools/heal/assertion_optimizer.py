#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/assertion_optimizer.py — Unified Assertion Optimization & Tuning Suite
----------------------------------------------------------------------------
Unifies and orchestrates declarative typed signatures, instruction tuning,
and AST-guided assertion sensitivity feedback into a single CLI tool.

Subcommands:
  signatures : Inspect or compile declarative typed QA signatures.
  tune       : Run prompt optimization over candidate instructions & demonstrations.
  gradient   : Compute sensitivity feedback from surviving micro-mutants to refine assertions.
  eval       : Evaluate assertion code against Synapse-Hub 10 Quality Gates DoD metric.

100% UTF-8 No BOM.
"""

import os
import sys
import json
import argparse

# Enforce UTF-8 stdio
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.dirname(SCRIPT_DIR)
for _p in (SCRIPT_DIR, TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Safe imports from underlying assertion engines
try:
    from tools.orchestration import typed_prompt_signatures
except ImportError:
    try:
        import typed_prompt_signatures
    except ImportError:
        typed_prompt_signatures = None

try:
    from tools.lint import mipro_assertion_tuner
except ImportError:
    try:
        import mipro_assertion_tuner
    except ImportError:
        mipro_assertion_tuner = None

try:
    from tools.heal import ast_assertion_optimizer
except ImportError:
    try:
        import ast_assertion_optimizer
    except ImportError:
        ast_assertion_optimizer = None


def run_signatures_cmd(args: argparse.Namespace) -> int:
    """Handles signatures subcommand."""
    if not typed_prompt_signatures:
        print("Error: typed_prompt_signatures engine not available.", file=sys.stderr)
        return 1

    print("====================================================================")
    print("       DECLARATIVE TYPED QA SIGNATURES ENGINE")
    print("====================================================================")
    print("Registered Signatures:")
    print("  1. UserStoryToUniversalIR   : Formalizes agile stories into AST IR.")
    print("  2. UniversalIRToCleanPOM    : Transpiles Universal IR into Clean POM Page Classes.")
    print("  3. RCAFailureDiagnosis      : Extracts root cause analysis from test trace.")
    print("====================================================================")
    return 0


def run_tune_cmd(args: argparse.Namespace) -> int:
    """Handles prompt tuning subcommand."""
    if not mipro_assertion_tuner:
        print("Error: mipro_assertion_tuner engine not available.", file=sys.stderr)
        return 1

    tuner = mipro_assertion_tuner.MiproAssertionTuner()
    res = tuner.compile_module(signature_name="AssertionGenerator", trials=args.trials)
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print("====================================================================")
        print("       BAYESIAN ASSERTION INSTRUCTION TUNING RESULTS")
        print("====================================================================")
        print(f"Optimal Score: {res.get('best_score', 0):.2f}%")
        print(f"Instruction  : {res.get('best_instruction', '')}")
        print(f"Few-Shot Demos: {len(res.get('best_demonstrations', []))}")
        print("====================================================================")
    return 0


def run_gradient_cmd(args: argparse.Namespace) -> int:
    """Handles assertion sensitivity feedback subcommand."""
    if not ast_assertion_optimizer:
        print("Error: ast_assertion_optimizer engine not available.", file=sys.stderr)
        return 1

    optimizer = ast_assertion_optimizer.ASTAssertionOptimizer(
        target_score=args.target_score,
        max_iterations=args.max_iterations,
    )
    initial_code = args.prompt or (
        "import { test, expect } from '@playwright/test';\n"
        "test('demo test', async ({ page }) => {\n"
        "  expect(1).toBe(1);\n"
        "});"
    )
    success, optimized_code, history = optimizer.optimize_assertions(initial_code)
    if args.json:
        payload = {
            "success": success,
            "optimized_code": optimized_code,
            "history": history,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("====================================================================")
        print("       AST ASSERTION SENSITIVITY OPTIMIZATION RESULTS")
        print("====================================================================")
        print(f"Convergence  : {'SUCCESS' if success else 'PARTIAL'}")
        print(f"Iterations   : {len(history)}")
        print(f"Optimized Code:\n{optimized_code}")
        print("====================================================================")
    return 0 if success else 1


def run_eval_cmd(args: argparse.Namespace) -> int:
    """Evaluates assertion snippet against QA DoD metric."""
    if not typed_prompt_signatures:
        print("Error: typed_prompt_signatures engine not available.", file=sys.stderr)
        return 1

    class _MockPred:
        def __init__(self, code: str):
            self.test_script_code = code
            self.page_class_code = "export class Page { async doAction() {} }"

    code_to_eval = args.code or (
        "import { test, expect } from '@playwright/test';\n"
        "test('demo', async ({ page }) => {\n"
        "  expect(true).toBe(true);\n"
        "});"
    )
    score = typed_prompt_signatures.qa_dod_metric(None, _MockPred(code_to_eval))
    print(f"DoD Metric Score: {score:.2f} (Passed: {score >= 0.8})")
    return 0 if score >= 0.8 else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Unified Assertion Optimization & Tuning Suite (DSPy v2, MIPROv2 & TextGrad)"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # Signatures
    sub_sig = subparsers.add_parser("signatures", help="Inspect or compile declarative QA DSPy signatures")
    sub_sig.set_defaults(func=run_signatures_cmd)

    # Tune
    sub_tune = subparsers.add_parser("tune", help="Run MIPROv2 Bayesian instruction & few-shot search")
    sub_tune.add_argument("--trials", type=int, default=10, help="Number of search trials")
    sub_tune.add_argument("--json", action="store_true", help="Output JSON")
    sub_tune.set_defaults(func=run_tune_cmd)

    # Gradient
    sub_grad = subparsers.add_parser("gradient", help="Compute textual gradients from surviving mutants")
    sub_grad.add_argument("--prompt", type=str, default="", help="Initial assertion prompt")
    sub_grad.add_argument("--target-score", type=float, default=80.0, help="Target mutation score (default: 80.0)")
    sub_grad.add_argument("--max-iterations", type=int, default=3, help="Max gradient steps")
    sub_grad.add_argument("--json", action="store_true", help="Output JSON")
    sub_grad.set_defaults(func=run_gradient_cmd)

    # Eval
    sub_eval = subparsers.add_parser("eval", help="Evaluate code snippet against DoD metric")
    sub_eval.add_argument("--code", type=str, default="", help="Code snippet to evaluate")
    sub_eval.set_defaults(func=run_eval_cmd)

    args = parser.parse_args()
    if not hasattr(args, "func") or not args.subcommand:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
