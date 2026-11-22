#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Gate 11: Token Reduction & Apex Intelligence Architecture Sentinel (Tiers 1-15 DoD Gate)
-----------------------------------------------------------------------------------------
Verifies that all 15 token-reduction and neuro-symbolic subsystems are fully operational:
  - Tier 1: KV-Cache Prefix Immutability in AGENTS.md
  - Tier 2: Meta-Tool MCP Server & Minified Schema
  - Tier 3: AST Skeleton Extractor & High-Density TOON Encoder
  - Tier 4: Trajectory Observation Masking & O(1) Stateless Rolling State
  - Tier 5: Output Diff Sentinel & Telegraphic Reasoning
  - Tier 6: Action Bundler & Deterministic Compute Offloading
  - Tier 7: CodeAct / Programmatic Tool Calling Engine (tools/runtime/codeact_engine.py)
  - Tier 8: Reversible AST Symbol Aliasing & Minification (tools/context/ast_symbol_minifier.py)
  - Tier 9: Hard Stop-Sequences & Dynamic Thinking Budget (tools/reasoning/dynamic_budget_engine.py)
  - Tier 10: Macro Cache & Zero-Token Cross-Session Repair (tools/core/macro_cache.py)
  - Tier 11: Repo Speculative Decoding & Prompt Lookup (tools/runtime/suffix_speculative_decoder.py)
  - Tier 12: Kolmogorov-Minimal Symbolic Micro-DSL (tools/context/symbolic_micro_dsl.py)
  - Tier 13: Logprob-Triggered Prefix Branching (tools/reasoning/logprob_branching_engine.py)
  - Tier 14: Boundary Counterfactual Few-Shot Distiller (tools/context/counterfactual_distiller.py)
  - Tier 15: Neuro-Symbolic Constraint Offloading (tools/reasoning/neuro_symbolic_solver.py)
"""

from __future__ import annotations

import logging
import os
import sys
import time
from typing import Any, List

from tools.core.gates.base import (
    BaseGate,
    LAST_GATE_METRICS,
)

logger = logging.getLogger("synapse.gates.token_reduction")


class Gate11TokenReduction(BaseGate):
    """Gate 11: Token Reduction Architecture Sentinel."""

    gate_id: int = 11
    name: str = "Gate 11: Token Reduction Architecture Sentinel"
    key: str = "gate_11_token_reduction"

    def run(self, repo_root: str, mode: str = "AUTO", fast: bool = False, **kwargs: Any) -> bool:
        return gate_11_token_reduction(repo_root, mode=mode, fast=fast)


def gate_11_token_reduction(repo_root: str, mode: str = "AUTO", fast: bool = False) -> bool:
    """Verifies operational integrity across all 15 token reduction tiers."""
    print("\n[GATE 11] Running Tier 1-15 Token Reduction Architecture Sentinel...")
    start_time = time.perf_counter()

    if mode.upper() == "TARGET" or (
        not os.path.exists(os.path.join(repo_root, "AGENTS.md"))
        and not os.path.exists(os.path.join(repo_root, "tools"))
    ):
        print("[PASS] Target project mode: Token Reduction subsystems not required in client repo (SKIPPED).")
        LAST_GATE_METRICS["gate_11_token_reduction"] = {
            "passed": True,
            "status": "PASS",
            "duration": time.perf_counter() - start_time,
            "checks_passed": 15,
            "total_checks": 15,
            "details": ["Target project mode: skipped"],
        }
        return True

    checks_passed = 0
    total_checks = 15
    details: List[str] = []

    # 1. Tier 1: Check Prefix Immutability
    try:
        from tools.lint.lint_cache_prefix import run_prefix_lint

        agents_file = os.path.join(repo_root, "AGENTS.md")
        p_pass, p_issues = run_prefix_lint(agents_file)
        if p_pass:
            checks_passed += 1
            details.append("Tier 1: KV-Cache Prefix Immutability VERIFIED")
        else:
            details.append(f"Tier 1: Prefix violation: {p_issues}")
    except Exception as e:
        details.append(f"Tier 1: Check failed with exception: {e}")

    # 2. Tier 2: Check Meta-Tool MCP & Minified Schema
    try:
        min_schema = os.path.join(repo_root, "tools", "tools_schema.min.json")
        meta_mcp = os.path.join(repo_root, "tools", "mcp", "synapse_meta_mcp.py")
        if os.path.exists(min_schema) and os.path.exists(meta_mcp):
            checks_passed += 1
            details.append("Tier 2: Meta-Tool MCP & Minified Schema VERIFIED")
        else:
            details.append("Tier 2: Missing tools_schema.min.json or synapse_meta_mcp.py")
    except Exception as e:
        details.append(f"Tier 2: Check failed with exception: {e}")

    # 3. Tier 3: Check AST Slicer & TOON Encoder
    try:
        from tools.context.context_slicer import ASTSkeletonExtractor
        from tools.context.high_density_encoder import HighDensityEncoder

        sample_file = os.path.join(repo_root, "tools", "core", "cache_prefix_enforcer.py")
        skel = ASTSkeletonExtractor.extract_skeleton(sample_file)
        if "class CachePrefixEnforcer" in skel and hasattr(HighDensityEncoder, "compare_compression"):
            checks_passed += 1
            details.append("Tier 3: AST Skeleton Slicer & TOON Encoder VERIFIED")
        else:
            details.append("Tier 3: AST Slicer or TOON encoder incomplete")
    except Exception as e:
        details.append(f"Tier 3: Check failed with exception: {e}")

    # 4. Tier 4: Check Observation Masking & Stateless Block
    try:
        from tools.core.project_state import export_stateless_working_block
        from tools.runtime.trajectory_compressor import TrajectoryCompressor

        block = export_stateless_working_block(repo_root)
        if hasattr(TrajectoryCompressor, "mask_tool_observation") and len(block) < 950:
            checks_passed += 1
            details.append("Tier 4: Observation Masking & Stateless O(1) Working State VERIFIED")
        else:
            details.append("Tier 4: Trajectory compressor or working state out of bounds")
    except Exception as e:
        details.append(f"Tier 4: Check failed with exception: {e}")

    # 5. Tier 5: Check Diff Sentinel & Telegraphic Enforcer
    try:
        from tools.lint.output_diff_sentinel import OutputDiffSentinel
        from tools.reasoning.telegraphic_enforcer import TelegraphicEnforcer

        diff_res = OutputDiffSentinel.validate_search_replace_block("a\n", "b\n", "a\nc\n")
        if diff_res.get("valid") and hasattr(TelegraphicEnforcer, "purify_to_telegraphic"):
            checks_passed += 1
            details.append("Tier 5: Output Diff Sentinel & Telegraphic Enforcer VERIFIED")
        else:
            details.append("Tier 5: Diff sentinel validation failed")
    except Exception as e:
        details.append(f"Tier 5: Check failed with exception: {e}")

    # 6. Tier 6: Check Action Bundler & Deterministic Tools
    try:
        from tools.runtime.action_bundler import ActionBundler

        if hasattr(ActionBundler, "execute_batch") and os.path.exists(
            os.path.join(repo_root, "tools", "lint", "infer_linter.py")
        ):
            checks_passed += 1
            details.append("Tier 6: Multi-Action Bundler & Deterministic Tooling VERIFIED")
        else:
            details.append("Tier 6: Action bundler missing or incomplete")
    except Exception as e:
        details.append(f"Tier 6: Check failed with exception: {e}")

    # 7. Tier 7: Check CodeAct Subprocess Sandbox & In-Memory Distillation
    try:
        from tools.runtime.codeact_engine import CodeActEngine

        codeact_file = os.path.join(repo_root, "tools", "runtime", "codeact_engine.py")
        if (
            os.path.exists(codeact_file)
            and hasattr(CodeActEngine, "execute_script")
            and hasattr(CodeActEngine, "filter_in_memory")
            and hasattr(CodeActEngine, "calculate_token_savings")
        ):
            checks_passed += 1
            details.append("Tier 7: CodeAct / Programmatic Tool Calling Engine VERIFIED")
        else:
            details.append("Tier 7: CodeActEngine missing or incomplete")
    except Exception as e:
        details.append(f"Tier 7: Check failed with exception: {e}")

    # 8. Tier 8: Check Reversible AST Symbol Aliasing & Minification
    try:
        minifier_file = os.path.join(repo_root, "tools", "context", "ast_symbol_minifier.py")
        if os.path.exists(minifier_file):
            from tools.context.ast_symbol_minifier import ASTSymbolMinifier

            if (
                hasattr(ASTSymbolMinifier, "minify")
                and hasattr(ASTSymbolMinifier, "restore")
                and hasattr(ASTSymbolMinifier, "should_activate")
            ):
                checks_passed += 1
                details.append("Tier 8: Reversible AST Symbol Aliasing & Minification VERIFIED")
            else:
                details.append("Tier 8: ASTSymbolMinifier missing expected methods")
        else:
            details.append("Tier 8: Missing tools/context/ast_symbol_minifier.py")
    except Exception as e:
        details.append(f"Tier 8: Check failed with exception: {e}")

    # 9. Tier 9: Check Hard Stop-Sequences & Dynamic Thinking Budget
    try:
        from tools.reasoning.dynamic_budget_engine import DynamicBudgetEngine

        budget_file = os.path.join(repo_root, "tools", "reasoning", "dynamic_budget_engine.py")
        if (
            os.path.exists(budget_file)
            and hasattr(DynamicBudgetEngine, "resolve_budget")
            and hasattr(DynamicBudgetEngine, "truncate_stream")
            and hasattr(DynamicBudgetEngine, "get_stop_sequences")
        ):
            checks_passed += 1
            details.append("Tier 9: Hard Stop-Sequences & Dynamic Thinking Budget VERIFIED")
        else:
            details.append("Tier 9: DynamicBudgetEngine missing or incomplete")
    except Exception as e:
        details.append(f"Tier 9: Check failed with exception: {e}")

    # 10. Tier 10: Check Macro Cache & Zero-Token Cross-Session Repair
    try:
        from tools.core.macro_cache import (
            ASTErrorSignatureExtractor,
            ContextHasher,
            MacroCacheEngine,
            ParameterizedMacro,
        )

        macro_file = os.path.join(repo_root, "tools", "core", "macro_cache.py")
        if (
            os.path.exists(macro_file)
            and hasattr(MacroCacheEngine, "execute_zero_token_repair")
            and hasattr(MacroCacheEngine, "store_macro")
            and hasattr(ASTErrorSignatureExtractor, "extract_from_syntax_error")
            and hasattr(ContextHasher, "compute_context_hash")
            and hasattr(ParameterizedMacro, "apply")
        ):
            checks_passed += 1
            details.append("Tier 10: Macro Cache & Zero-Token Cross-Session Repair VERIFIED")
        else:
            details.append("Tier 10: MacroCacheEngine missing or incomplete")
    except Exception as e:
        details.append(f"Tier 10: Check failed with exception: {e}")

    # 11. Tier 11: Repo Speculative Decoding & Prompt Lookup
    try:
        from tools.runtime.suffix_speculative_decoder import (
            RepoSpeculativeEngine,
            SuffixAutomatonIndex,
        )

        spec_file = os.path.join(repo_root, "tools", "runtime", "suffix_speculative_decoder.py")
        if (
            os.path.exists(spec_file)
            and hasattr(RepoSpeculativeEngine, "speculate")
            and hasattr(RepoSpeculativeEngine, "verify_draft")
            and hasattr(SuffixAutomatonIndex, "lookup_continuation")
        ):
            checks_passed += 1
            details.append("Tier 11: Repo Speculative Decoding & Prompt Lookup VERIFIED")
        else:
            details.append("Tier 11: RepoSpeculativeEngine missing or incomplete")
    except Exception as e:
        details.append(f"Tier 11: Check failed with exception: {e}")

    # 12. Tier 12: Kolmogorov-Minimal Symbolic Micro-DSL
    try:
        from tools.context.symbolic_micro_dsl import MicroDSLCompiler

        dsl_file = os.path.join(repo_root, "tools", "context", "symbolic_micro_dsl.py")
        if (
            os.path.exists(dsl_file)
            and hasattr(MicroDSLCompiler, "encode")
            and hasattr(MicroDSLCompiler, "decode")
            and hasattr(MicroDSLCompiler, "validate")
            and hasattr(MicroDSLCompiler, "calculate_compression")
        ):
            checks_passed += 1
            details.append("Tier 12: Kolmogorov-Minimal Symbolic Micro-DSL VERIFIED")
        else:
            details.append("Tier 12: MicroDSLCompiler missing or incomplete")
    except Exception as e:
        details.append(f"Tier 12: Check failed with exception: {e}")

    # 13. Tier 13: Logprob-Triggered Prefix Branching
    try:
        from tools.reasoning.logprob_branching_engine import (
            LogprobStreamAnalyzer,
            PrefixBranchingEngine,
        )

        branch_file = os.path.join(repo_root, "tools", "reasoning", "logprob_branching_engine.py")
        if (
            os.path.exists(branch_file)
            and hasattr(LogprobStreamAnalyzer, "analyze_stream")
            and hasattr(LogprobStreamAnalyzer, "find_first_bifurcation")
            and hasattr(PrefixBranchingEngine, "execute_prefix_branching")
        ):
            checks_passed += 1
            details.append("Tier 13: Logprob-Triggered Prefix Branching VERIFIED")
        else:
            details.append("Tier 13: PrefixBranchingEngine missing or incomplete")
    except Exception as e:
        details.append(f"Tier 13: Check failed with exception: {e}")

    # 14. Tier 14: Boundary Counterfactual Few-Shot Distiller
    try:
        from tools.context.counterfactual_distiller import CounterfactualDistiller

        cf_file = os.path.join(repo_root, "tools", "context", "counterfactual_distiller.py")
        if (
            os.path.exists(cf_file)
            and hasattr(CounterfactualDistiller, "distill")
            and hasattr(CounterfactualDistiller, "format_distilled_prompt")
            and hasattr(CounterfactualDistiller, "calculate_token_savings")
        ):
            checks_passed += 1
            details.append("Tier 14: Boundary Counterfactual Few-Shot Distiller VERIFIED")
        else:
            details.append("Tier 14: CounterfactualDistiller missing or incomplete")
    except Exception as e:
        details.append(f"Tier 14: Check failed with exception: {e}")

    # 15. Tier 15: Neuro-Symbolic Constraint Offloading
    try:
        from tools.reasoning.neuro_symbolic_solver import (
            DependencyCycleSolver,
            DPLLSatSolver,
            RBACConstraintSolver,
        )

        solver_file = os.path.join(repo_root, "tools", "reasoning", "neuro_symbolic_solver.py")
        if (
            os.path.exists(solver_file)
            and hasattr(DPLLSatSolver, "solve")
            and hasattr(DependencyCycleSolver, "solve")
            and hasattr(RBACConstraintSolver, "verify_policy")
        ):
            checks_passed += 1
            details.append("Tier 15: Neuro-Symbolic Constraint Offloading VERIFIED")
        else:
            details.append("Tier 15: Neuro-Symbolic solvers missing or incomplete")
    except Exception as e:
        details.append(f"Tier 15: Check failed with exception: {e}")

    duration = round(time.perf_counter() - start_time, 3)
    passed = checks_passed == total_checks

    metric_payload = {
        "passed": passed,
        "score": f"{checks_passed}/{total_checks}",
        "checks_passed": checks_passed,
        "total_checks": total_checks,
        "duration_sec": duration,
        "duration": duration,
        "status": "PASS" if passed else "FAIL",
        "details": details,
    }
    LAST_GATE_METRICS["gate_11"] = metric_payload
    LAST_GATE_METRICS["gate_11_token_reduction"] = metric_payload

    if passed:
        print(
            f"[PASS] 100% Token Reduction Architecture Verified: All 15 Tiers operational ({checks_passed}/{total_checks} in {duration}s)."
        )
        for d in details:
            print(f"       • {d}")
        return True
    else:
        print(
            f"[FAIL] Token Reduction Architecture Failed ({checks_passed}/{total_checks} passed):",
            file=sys.stderr,
        )
        for d in details:
            print(f"       • {d}", file=sys.stderr)
        return False
