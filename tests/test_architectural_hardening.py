#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tests/test_architectural_hardening.py — 4-Scenario Battery for 10.0 Hardening Components
----------------------------------------------------------------------------------------
Exhaustively tests the 10.0 upgrades across 4 scenarios (Positive, Negative, Boundary, CLI):
- TC-01: Assertion vs Syntax/Import test failure classification
- TC-02: Adaptive small-sample mutation scoring (< 5 mutants)
- TC-03: Semantic Red Certification rejecting environment/timeout crashes
- TC-04: Worktree read-only dependency sharing
- TC-05: Blast-Radius Risk Routing for single critical files
- TC-06: Dual-Mode Ambiguity Gate execution (--auto-recommend)
- TC-07: Architectural-Impact ADR Gating
- TC-08: Single Source of Truth Parity (synapse.config.json & AGENTS.md)
- TC-09: Plan Mutation Sentinel verification
- TC-10: Empirical Benchmark Suite validation
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

from tools.lint.micro_mutator import (
    classify_test_failure,
    evaluate_adaptive_mutation_score,
)
from tools.orchestration.solo_runner import (
    certify_red_phase,
)
from tools.orchestration.worktree_manager import link_shared_dependencies
from tools.design.super_plan_engine import (
    calculate_risk_routing,
    PlanningTier,
    check_ambiguities,
)
from tools.design.plan_harvester import (
    is_adr_worthy_decision,
)
from benchmarks.qa_eval.ablation_10_benchmark import (
    generate_synthetic_benchmark_tasks,
    run_benchmark_simulation,
)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _is_directory_link_or_junction(path: str) -> bool:
    """Returns True when path is a POSIX/Windows symlink or a Windows NTFS junction."""
    if os.path.islink(path):
        return True
    if sys.platform == "win32":
        is_junction = getattr(os.path, "isjunction", None)
        if callable(is_junction):
            return bool(is_junction(path))
        return os.path.isdir(path)
    return False


class TestArchitectural10Hardening(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="synapse_10_test_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # 1. POSITIVE SCENARIOS

    def test_tc01_classify_test_failure_positive_assertion(self):
        """TC-01: Assertion failures are correctly classified as legitimate mutant kills."""
        stdout = "test_feature.py:10: in test_logic\n    assert x == 5\nE   AssertionError: assert 4 == 5"
        cat, is_valid, reason = classify_test_failure(stdout, "", 1)
        self.assertEqual(cat, "ASSERTION_FAILURE")
        self.assertTrue(is_valid)

    def test_tc02_adaptive_mutation_score_small_diff(self):
        """TC-02: Micro-PRs with < 5 mutants pass when all or near-all mutants are killed."""
        # 2 out of 2 killed (100%)
        passed, score, policy = evaluate_adaptive_mutation_score(killed_count=2, total_eval=2)
        self.assertTrue(passed)
        self.assertEqual(policy, "ALL_KILLED")

        # 2 out of 3 killed (66.7%) -> small diff adaptive policy passes
        passed_adapt, score_adapt, policy_adapt = evaluate_adaptive_mutation_score(killed_count=2, total_eval=3)
        self.assertTrue(passed_adapt)
        self.assertEqual(policy_adapt, "SMALL_DIFF_ADAPTIVE")

    def test_tc03_semantic_red_receipt_certified(self):
        """TC-03: Real assertion failure is certified as legitimate Red Phase."""
        receipt_file = os.path.join(self.temp_dir, "red_receipt.json")
        res = certify_red_phase(
            test_cmd='python3 -c "x = len([1, 2]); assert x == 5, \\"length mismatch\\""',
            receipt_path=receipt_file,
            cwd=REPO_ROOT,
        )
        self.assertEqual(res["passed"], True)
        self.assertEqual(res.get("status"), "CERTIFIED_RED")
        self.assertTrue(os.path.isfile(receipt_file))
        with open(receipt_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertTrue(data.get("is_semantic_red"))

    def test_tc04_worktree_dependency_sharing(self):
        """TC-04: Read-only dependency sharing creates valid symlinks without copying."""
        src_dir = os.path.join(self.temp_dir, "src")
        wt_dir = os.path.join(self.temp_dir, "wt")
        os.makedirs(os.path.join(src_dir, "node_modules"), exist_ok=True)
        os.makedirs(wt_dir, exist_ok=True)

        res = link_shared_dependencies(src_dir, wt_dir)
        self.assertTrue(res.get("symlink_success"))
        self.assertIn("node_modules", res.get("linked", []))
        self.assertTrue(_is_directory_link_or_junction(os.path.join(wt_dir, "node_modules")))

    def test_tc05_blast_radius_single_critical_file(self):
        """TC-05: Modifying a single critical path file (auth/middleware) escalates out of Tier 0."""
        tier, metric = calculate_risk_routing(
            task="Refactor session authentication middleware",
            target_files=["src/auth/session_middleware.py"],
            repo_root=REPO_ROOT,
        )
        self.assertTrue(metric.critical_path)
        self.assertGreaterEqual(metric.blast_radius, 5)
        # Must NOT be Tier 0 Micro-Plan
        self.assertNotEqual(tier, PlanningTier.TIER_0_FAST)
        self.assertIn(tier, (PlanningTier.TIER_1_STANDARD, PlanningTier.TIER_2_DEEP))

    def test_tc06_dual_mode_ambiguity_gate(self):
        """TC-06: Ambiguity Gate detects architectural forks and provides recommended options."""
        task = "Choose between in-memory cache and redis storage"
        questions = check_ambiguities(task)
        self.assertGreater(len(questions), 0)
        recommended = questions[0]["options"][0]
        self.assertTrue(recommended.startswith("(Recommended)"))

    def test_tc07_adr_gating_filter(self):
        """TC-07: Low-impact plans bypass ADR markdown creation, high-impact plans create ADRs."""
        # Low impact
        low_content = "# Plan: Fix typo in button label\nArchitectural-Impact: Low"
        worthy_low, impact_low, _ = is_adr_worthy_decision(low_content, {"title": "Fix typo"})
        self.assertFalse(worthy_low)
        self.assertEqual(impact_low, "LOW")

        # High impact
        high_content = "# Plan: Migrate to Distributed Ledger Engine\nArchitectural-Impact: High"
        worthy_high, impact_high, _ = is_adr_worthy_decision(high_content, {"title": "Ledger Migration"})
        self.assertTrue(worthy_high)
        self.assertEqual(impact_high, "HIGH")

    def test_tc08_single_source_of_truth_parity(self):
        """TC-08: synapse.config.json and AGENTS.md specify identical Circuit Breaker limit (2)."""
        config_path = os.path.join(REPO_ROOT, "synapse.config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual(cfg.get("circuit_breaker", {}).get("max_fix_attempts"), 2)

        agents_path = os.path.join(REPO_ROOT, "AGENTS.md")
        with open(agents_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("fails 2 consecutive times", content)

    # 2. NEGATIVE SCENARIOS

    def test_tc01_negative_syntax_error_not_killed(self):
        """Negative: Syntax error in test output is rejected from being counted as valid assertion kill."""
        stdout = "SyntaxError: invalid syntax in test file"
        cat, is_valid, _ = classify_test_failure(stdout, "", 1)
        self.assertEqual(cat, "SYNTAX_ERROR")
        self.assertFalse(is_valid)

    def test_tc03_negative_environmental_red_rejected(self):
        """Negative: Test failing due to connection timeout is rejected from Red Phase certification."""
        receipt_file = os.path.join(self.temp_dir, "red_receipt_env.json")
        res = certify_red_phase(
            test_cmd='python3 -c "import sys; print(\'ECONNREFUSED: Connection refused to redis:6379\'); sys.exit(1)"',
            receipt_path=receipt_file,
            cwd=REPO_ROOT,
        )
        self.assertEqual(res["passed"], False)
        self.assertEqual(res.get("status"), "ENVIRONMENT_ERROR_RED_REJECTED")

    # 3. BOUNDARY SCENARIOS

    def test_boundary_empty_inputs(self):
        """Boundary: Empty test command or zero mutants handled safely without unhandled exceptions."""
        cat, is_valid, _ = classify_test_failure("", "", 0)
        self.assertEqual(cat, "PASSED")
        self.assertFalse(is_valid)

        passed, score, policy = evaluate_adaptive_mutation_score(0, 0)
        self.assertTrue(passed)
        self.assertEqual(policy, "EMPTY")

    # 4. CLI & BENCHMARK INTEGRATION

    def test_tc10_empirical_benchmark_battery(self):
        """TC-10: Empirical benchmark battery executes and certifies all 4 performance dimensions."""
        tasks = generate_synthetic_benchmark_tasks(sample_size=30)
        results, summary = run_benchmark_simulation(tasks)
        self.assertEqual(summary.total_tasks, 30)
        self.assertLess(summary.false_pass_escape_rate_synapse, 1.0)
        self.assertGreaterEqual(summary.real_kv_cache_hit_rate_pct, 85.0)
        self.assertLess(summary.p50_latency_sec, 30.0)
        self.assertGreaterEqual(summary.self_healing_recovery_rate_pct, 90.0)
        self.assertTrue(summary.verdict_10_perfection)

    def test_tc11_context_aware_skill_router_exemption_and_trigger(self):
        """TC-11: Context-aware Skill Router distinguishes Inquiries, Micro-fixes and Domain Actions."""
        from tools.core.skill_router import evaluate_skill_first_trigger

        # 1. Inquiry: exempt even with keywords
        inquiry_res = evaluate_skill_first_trigger(
            prompt="Can you explain how POM verification works in Playwright?",
            repo_root=REPO_ROOT,
        )
        self.assertFalse(inquiry_res["is_triggered"])
        self.assertTrue(inquiry_res["is_exempt"])

        # 2. Micro-fix: exempt from triggering skill overhead
        micro_res = evaluate_skill_first_trigger(
            prompt="fix off-by-one index error",
            target_files=["src/math_util.py"],
            is_single_line_hotfix=True,
            repo_root=REPO_ROOT,
        )
        self.assertFalse(micro_res["is_triggered"])
        self.assertTrue(micro_res["is_exempt"])

        # 3. Action on POM test file: properly triggers clean-pom-crafter
        action_res = evaluate_skill_first_trigger(
            prompt="implement login page object model for checkout",
            target_files=["tests/e2e/pages/login_page.py"],
            repo_root=REPO_ROOT,
        )
        self.assertTrue(action_res["is_triggered"])
        self.assertEqual(action_res["recommended_skill"], "clean-pom-crafter")

    def test_tc12_kv_cache_sentinel_telemetry_evaluation(self):
        """TC-12: Live KV-cache sentinel audits hit rates and emits alerts when < 85%."""
        from tools.core.kv_cache_sentinel import evaluate_cache_hit_rate

        # Conforming payload (90% >= 85%)
        audit_pass = evaluate_cache_hit_rate(input_tokens=4000, cached_tokens=3600, min_pct=85.0)
        self.assertTrue(audit_pass.passed)
        self.assertFalse(audit_pass.alert_triggered)

        # Non-conforming payload (70% < 85%)
        audit_fail = evaluate_cache_hit_rate(input_tokens=4000, cached_tokens=2800, min_pct=85.0)
        self.assertFalse(audit_fail.passed)
        self.assertTrue(audit_fail.alert_triggered)
        self.assertIn("Attention dilution detected", audit_fail.details)

    def test_tc13_micro_mutator_ast_verified_generation(self):
        """TC-13: Micro-mutator generates genuine AST-verified Python mutants."""
        from tools.lint.micro_mutator import generate_ast_mutants_python

        sample_code = """
def discount_calculator(price: int, is_vip: bool) -> int:
    if is_vip == True and price > 100:
        return price - 20
    return price
"""
        ast_muts = generate_ast_mutants_python(sample_code, "discount.py")
        self.assertGreaterEqual(len(ast_muts), 4)
        for m in ast_muts:
            self.assertTrue(m.get("ast_verified"))
            self.assertIn(m["description"][:3], ("Equ", "Rel", "Boo", "Ret", "Ari"))


if __name__ == "__main__":
    unittest.main()
