#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_ai_reasoning_6layer_upgrade.py — 4-Scenario Regression Suite for 6-Layer AI Reasoning & Verification Upgrade
---------------------------------------------------------------------------------------------------------------------------
Validates TC-01 through TC-06 from implementation_plan_ai_reasoning_upgrade.md across:
  1. Positive: Architecture Step-Back/Self-Discover alignment, Grounded Semantic Entropy & Multi-Round Debate,
               EvalRunner native 10/10 on CoVe & TextGrad.
  2. Negative: Unsanctioned swallowed exception AST hygiene in CoVe, TextGrad --metric filtering & invalid CLI exit.
  3. Boundary: Empty/single inputs, # synapse-ignore bootstrap except ImportError safety, round clamping 0..10.
  4. CLI Flags: JSON stdout execution across all 6 upgraded engines + EvalRunner monotonic duration & resilience.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT_DIR / "tools"
for _p in (str(ROOT_DIR), str(TOOLS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.ai.cove_verifier import ChainOfVerificationEngine
from tools.ai.textgrad_optimizer import TextGradOptimizer
from tools.core.eval_runner import EvalRunner
from tools.reasoning.prover_verifier_games import ProverVerifierGame, VerifierAgent
from tools.reasoning.self_discover_engine import SelfDiscoverEngine
from tools.reasoning.semantic_entropy import SemanticEntropyEngine
from tools.reasoning.step_back_engine import StepBackEngine


class TestSixLayerPositive:
    """TC-01, TC-02, TC-03: Positive scenarios for all 6 reasoning/AI layers and EvalRunner."""

    def test_step_back_and_self_discover_architecture(self) -> None:
        """TC-01: Architecture/verification tasks derive Guide-Sensor invariants without unconditional network idle."""
        sb = StepBackEngine()
        task = "Evaluate Synapse Hub architecture and verification pipeline"
        sb_res = sb.run(task)

        questions = sb_res["step_back_abstraction"]["abstract_questions"]
        categories = [q["category"] for q in questions]
        assert "HARNESS_VERIFICATION_ARCHITECTURE" in categories

        # Non-architecture task must NOT emit HARNESS_VERIFICATION_ARCHITECTURE
        non_arch_cats = [q["category"] for q in sb.generate_abstract_questions("Fix double-click race condition")]
        assert "HARNESS_VERIFICATION_ARCHITECTURE" not in non_arch_cats

        principles = sb_res["step_back_abstraction"]["governing_principles"]
        arch_principles = [p for p in principles if p["category"] == "HARNESS_VERIFICATION_ARCHITECTURE"]
        assert len(arch_principles) == 1
        assert "guide" in arch_principles[0]["core_invariant"].lower() or "sensor" in arch_principles[0]["core_invariant"].lower()
        assert len(arch_principles[0]["concrete_guardrails"]) >= 2

        # Verify ASYNCHRONOUS_OBSERVABILITY no longer recommends unconditional "network idle"
        async_principles = sb.derive_governing_principles(
            "Fix Playwright locator wait",
            [{"id": "SQ1", "category": "ASYNCHRONOUS_OBSERVABILITY", "abstract_question": "q", "target_mental_model": "m"}],
        )
        all_guardrails = " ".join(async_principles[0]["concrete_guardrails"]).lower()
        assert "network idle" not in all_guardrails
        assert "waitforurl" in all_guardrails or "waitforresponse" in all_guardrails

        # SelfDiscoverEngine architecture boosters & K <= 2 alignment
        sd = SelfDiscoverEngine()
        selected = sd.select(task, top_k=4)
        selected_ids = [m["id"] for m in selected]
        assert "MOD_INVARIANT_ISOLATION" in selected_ids
        assert "MOD_AST_GROUNDED_TRACING" in selected_ids
        assert "MOD_TRUTH_ANCHOR_VERIFICATION" in selected_ids

        adapted = sd.adapt(selected, task)
        truth_mod = [a for a in adapted if a["module_id"] == "MOD_TRUTH_ANCHOR_VERIFICATION"][0]
        truth_text = " ".join(truth_mod["grounded_directives"]).lower()
        assert "k <= 2" in truth_text
        assert "k <= 3" not in truth_text

        # Other resilience_recovery modules also align to K <= 2
        resilience_adapted = sd.adapt(
            [{"id": "MOD_CIRCUIT_BREAKER_PROTOCOL", "name": "Circuit Breaker", "family": "resilience_recovery", "description": "cb"}],
            task,
        )
        res_text = " ".join(resilience_adapted[0]["grounded_directives"]).lower()
        assert "k <= 2" in res_text
        assert "k <= 3" not in res_text

    def test_grounded_entropy_and_multi_round_debate(self) -> None:
        """TC-02: Grounded repo queries converge SE <= 0.50; brand noise stripped; multi-round debate rotates vectors."""
        se = SemanticEntropyEngine(repo_root=str(ROOT_DIR))

        # Grounded repo query referencing real Hub files/symbols
        is_grounded, facts = se._probe_repo_grounding("Verify EvalRunner and verify_all.py gate pipeline")
        assert is_grounded is True
        assert "tools/core/verify_all.py" in facts
        assert any("EvalRunner" in f for f in facts)

        # Single file-only and symbol-only grounding probes (tests 0->1 boundary & symbol->module resolution)
        file_only_ok, file_only_facts = se._probe_repo_grounding("Inspect verify_all.py")
        assert file_only_ok is True
        assert file_only_facts == ["tools/core/verify_all.py"]

        sym_only_ok, sym_only_facts = se._probe_repo_grounding("Inspect EvalRunner")
        assert sym_only_ok is True
        assert any("symbol EvalRunner in tools/core/eval_runner.py" == f for f in sym_only_facts)

        # File lookup cap <= 5 candidate files
        many_files_ok, many_facts = se._probe_repo_grounding(
            "Check verify_all.py eval_runner.py step_back_engine.py self_discover_engine.py semantic_entropy.py cove_verifier.py"
        )
        assert many_files_ok is True
        assert len([f for f in many_facts if not f.startswith("symbol ")]) <= 5

        # Ignored brand-only or empty or missing-root probes must return False, []
        assert se._probe_repo_grounding("Verify Synapse Hub") == (False, [])
        assert se._probe_repo_grounding("") == (False, [])
        assert se._probe_repo_grounding("   ") == (False, [])
        missing_se = SemanticEntropyEngine(repo_root=str(ROOT_DIR / "nonexistent_dir_xyz_404"))
        assert missing_se._probe_repo_grounding("Verify EvalRunner") == (False, [])

        hyps = se.generate_candidate_hypotheses("Verify EvalRunner and verify_all.py gate pipeline", count=4)
        assert len(hyps) == 4
        eval_res = se.evaluate_hypotheses(hyps, threshold=0.50)
        assert eval_res["normalized_entropy"] <= 0.50
        assert eval_res["code_write_permission"] is True

        # Brand noise ("Synapse", "Hub") stripped from epistemic search target hint
        plan = se._generate_epistemic_search_plan("Inspect Synapse Hub architecture for BasePage")
        step2_target = plan[1]["target"]
        assert "Synapse" not in step2_target
        assert "Hub" not in step2_target
        assert "BasePage" in step2_target

        # Multi-round debate on AGENTS.md rotates distinct counter-examples across rounds 1..3
        game = ProverVerifierGame(repo_root=str(ROOT_DIR))
        agents_path = str(ROOT_DIR / "AGENTS.md")
        debate = game.run_debate(proposal=agents_path, rounds=3, judge_mode="evidence_weighted")
        assert debate["rounds_completed"] == 3
        round_vectors = [
            tuple(r["verifier_counter"]["counter_examples"])
            for r in debate["transcript"]
        ]
        assert len(set(round_vectors)) == 3

    def test_eval_runner_zero_loss_and_cove_precision(self) -> None:
        """TC-03: EvalRunner achieves native 10.0/10 on TextGrad and 100% PASS on CoVe without bare except pass."""
        eval_runner_path = str(ROOT_DIR / "tools" / "core" / "eval_runner.py")
        eval_src = Path(eval_runner_path).read_text(encoding="utf-8")

        # No time.time() duration drift or bare pass swallow in eval_runner.py
        assert "time.monotonic()" in eval_src
        assert "# synapse-ignore" not in eval_src

        cove = ChainOfVerificationEngine(repo_root=str(ROOT_DIR))
        cove_report = cove.verify(eval_runner_path)
        assert cove_report["status"] == "PASS"
        assert cove_report["factual_confidence_pct"] == 100.0
        assert cove_report["discrepancies_count"] == 0

        # Ensure word "composite" alone does not trigger DATA_COLLISION question
        q_cats = [
            q["category"]
            for q in cove.generate_verification_questions("composite_score = 100.0\n", "sample.py")
        ]
        assert "DATA_COLLISION" not in q_cats

        tg = TextGradOptimizer(target_path=eval_runner_path, metric="all")
        tg_res = tg.optimize(in_place=False)
        assert tg_res["initial_quality"] == "10.0/10"
        assert tg_res["final_quality"] == "10.0/10"
        assert tg_res["history"][0]["loss"] == 0.0
        assert tg_res["status"] == "PASS"


class TestSixLayerNegative:
    """TC-04: Negative scenarios for CoVe EXCEPTION_HYGIENE and TextGrad --metric filtering."""

    def test_negative_exception_hygiene_and_metric_filter(self, tmp_path: Path) -> None:
        """TC-04: CoVe flags unsanctioned except pass; TextGrad --metric resilience filters POM-only gradients."""
        bad_py = tmp_path / "bad_swallow.py"
        bad_py.write_text(
            "def risky():\n"
            "    try:\n"
            "        return 1 / 0\n"
            "    except ValueError:\n"
            "        pass\n",
            encoding="utf-8",
        )
        cove = ChainOfVerificationEngine()
        cove_res = cove.verify(str(bad_py))
        assert cove_res["status"] == "DISCREPANCY_DETECTED"
        disc_cats = [d["category"] for d in cove_res["discrepancies"]]
        assert "EXCEPTION_HYGIENE" in disc_cats

        # Multi-class BasePage inheritance check catches violation on 2nd class and single bad base
        multi_cls = tmp_path / "multi_page.py"
        multi_cls.write_text(
            "class Helper:\n    pass\n\nclass BadPage(BasePage, Helper):\n    pass\n",
            encoding="utf-8",
        )
        cls_res = cove.verify(str(multi_cls))
        assert cls_res["status"] == "DISCREPANCY_DETECTED"
        assert "INHERITANCE_INVARIANT" in [d["category"] for d in cls_res["discrepancies"]]

        single_bad_base = tmp_path / "bad_single_base.py"
        single_bad_base.write_text("class CustomPage(OtherBase):\n    pass\n# BasePage\n", encoding="utf-8")
        assert cove.verify(str(single_bad_base))["status"] == "DISCREPANCY_DETECTED"

        good_multi_cls = tmp_path / "good_multi_page.py"
        good_multi_cls.write_text(
            "class Helper:\n    pass\n\nclass GoodPage(BasePage):\n    pass\n",
            encoding="utf-8",
        )
        good_multi_res = cove.verify(str(good_multi_cls))
        assert good_multi_res["status"] == "PASS"
        inh_entry = next(v for v in good_multi_res["verification_ledger"] if v["category"] == "INHERITANCE_INVARIANT")
        assert "Helper(object)" in inh_entry["ground_truth_evidence"]

        # CoVe _has_real_assertion variants (Assert, Name, Attribute assert_names & prefix, and negative non-assert call)
        ast_test_file = tmp_path / "test_ast_asserts.py"
        ast_test_file.write_text(
            "def test_raw_assert():\n    assert 2 == 2\n\n"
            "def test_name_verify():\n    verify_ok()\n\n"
            "def test_attr_raises():\n    pytest.raises(ValueError)\n\n"
            "def test_attr_expect(page):\n    page.to_be_visible()\n",
            encoding="utf-8",
        )
        assert cove.verify(str(ast_test_file))["status"] == "PASS"

        no_assert_file = tmp_path / "test_no_assert_call.py"
        no_assert_file.write_text("def test_missing():\n    helper_call()\n", encoding="utf-8")
        no_assert_res = cove.verify(str(no_assert_file))
        assert no_assert_res["status"] == "DISCREPANCY_DETECTED"
        assert "TRUTH_ANCHOR" in [d["category"] for d in no_assert_res["discrepancies"]]

        # TextGrad --metric resilience filters out CLEAN_POM_VIOLATION and COLLISION_RISK
        test_draft = tmp_path / "test_pom_mix.py"
        pom_code = (
            "def test_sample(page):\n"
            "    page.locator('#btn').click()\n"
            "    create_item('STATIC_CODE_123')\n"
            "    assert True\n"
        )
        test_draft.write_text(pom_code, encoding="utf-8")

        tg_all = TextGradOptimizer(target_path=str(test_draft), metric="")
        assert tg_all.metric == "all"
        loss_all, grads_all = tg_all.evaluate_loss(pom_code, "test_pom_mix.py")
        assert loss_all > 0.0
        assert any(g.loss_category == "CLEAN_POM_VIOLATION" for g in grads_all)

        # Explicit metric override in evaluate_loss() overrides self.metric
        loss_override, grads_override = tg_all.evaluate_loss(pom_code, "test_pom_mix.py", metric="resilience")
        assert loss_override == 0.0
        assert grads_override == []

        tg_resilience = TextGradOptimizer(target_path=str(test_draft), metric="resilience")
        loss_res, grads_res = tg_resilience.evaluate_loss(pom_code, "test_pom_mix.py")
        assert loss_res == 0.0
        assert not any(g.loss_category in ("CLEAN_POM_VIOLATION", "COLLISION_RISK") for g in grads_res)

        # Invalid metric raises ValueError and CLI --metric unknown exits non-zero
        with pytest.raises(ValueError):
            TextGradOptimizer(target_path=str(test_draft), metric="unknown")

        proc = subprocess.run(
            [
                sys.executable,
                str(TOOLS_DIR / "ai" / "textgrad_optimizer.py"),
                "--target",
                str(test_draft),
                "--metric",
                "unknown",
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0


class TestSixLayerBoundary:
    """TC-05: Boundary conditions, empty/single inputs, and bootstrap ImportError guard safety."""

    def test_boundary_empty_and_bootstrap_update(self, tmp_path: Path) -> None:
        """TC-05: Empty/single inputs never crash; # synapse-ignore and ImportError bootstrap preserved cleanly."""
        se = SemanticEntropyEngine(repo_root=str(ROOT_DIR))
        empty_eval = se.evaluate_hypotheses([], threshold=0.50)
        assert empty_eval["normalized_entropy"] == 0.0
        assert se.evaluate_hypotheses(["Single"], threshold=0.50)["normalized_entropy"] == 0.0

        # Ambiguous ungrounded prompt remains high entropy (> 0.50)
        ambig_hyps = se.generate_candidate_hypotheses("Unknown nonexistent quantum sprocket xyzzy999", count=4)
        ambig_eval = se.evaluate_hypotheses(ambig_hyps, threshold=0.50)
        assert ambig_eval["normalized_entropy"] > 0.50
        assert ambig_eval["code_write_permission"] is False

        # Round clamping 0 -> 1 and 10 -> 5 with distinct vectors across rounds 1..5
        game = ProverVerifierGame(repo_root=str(ROOT_DIR))
        agents_path = str(ROOT_DIR / "AGENTS.md")
        r_zero = game.run_debate(proposal=agents_path, rounds=0)
        assert r_zero["rounds_completed"] == 1
        r_ten = game.run_debate(proposal=agents_path, rounds=10)
        assert r_ten["rounds_completed"] == 5
        vectors_5 = [tuple(r["verifier_counter"]["counter_examples"]) for r in r_ten["transcript"]]
        assert len(set(vectors_5)) == 5
        assert "high concurrency memory pressure" in vectors_5[0][0].lower()
        assert "subprocess timeout" in vectors_5[1][0].lower()
        # Direct round_num=0 clamping on VerifierAgent.generate_attack must still select index 0
        from tools.reasoning.prover_verifier_games import ProverArgument
        v0 = VerifierAgent.generate_attack(0, "mutex lock retry backoff empty bound", "", ProverArgument("c", [], 0.8))
        assert "high concurrency memory pressure" in v0.counter_examples[0].lower()

        # Sanctioned # synapse-ignore on except line OR pass line gives 0.0 loss (incl. final-line boundary)
        bootstrap_code = (
            "try:\n"
            "    import optional_dep\n"
            "except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION\n"
            "    pass"
        )
        bs_file = tmp_path / "bootstrap_mod.py"
        bs_file.write_text(bootstrap_code, encoding="utf-8")
        tg = TextGradOptimizer(target_path=str(bs_file), metric="all")
        bs_loss, bs_grads = tg.evaluate_loss(bootstrap_code, "bootstrap_mod.py")
        assert bs_loss == 0.0
        assert len(bs_grads) == 0

        stmt_ignore_code = (
            "try:\n"
            "    import optional_dep\n"
            "except ImportError:\n"
            "    pass  # synapse-ignore: SWALLOWED_EXCEPTION"
        )
        stmt_loss, stmt_grads = tg.evaluate_loss(stmt_ignore_code, "bootstrap_mod.py")
        assert stmt_loss == 0.0
        assert len(stmt_grads) == 0

        # Unmarked except ImportError updated by apply_textual_update must remain valid syntax without RuntimeError crash
        unmarked_bootstrap = (
            "try:\n"
            "    import optional_dep\n"
            "except ImportError:\n"
            "    pass\n"
        )
        unmarked_loss, unmarked_grads = tg.evaluate_loss(unmarked_bootstrap, "bootstrap_mod.py")
        assert unmarked_loss > 0.0
        updated = tg.apply_textual_update(unmarked_bootstrap, unmarked_grads)
        compile(updated, "bootstrap_mod.py", "exec")
        assert "raise RuntimeError" not in updated


class TestSixLayerCLIFlags:
    """TC-06: CLI --json output and EvalRunner monotonic timing & resilience metadata."""

    def test_cli_json_outputs_and_eval_runner_monotonic(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """TC-06: All 6 upgraded CLIs return valid JSON with exit 0 and EvalRunner uses monotonic duration."""
        cmds = [
            [sys.executable, str(TOOLS_DIR / "reasoning" / "step_back_engine.py"), "--task", "Audit verification pipeline architecture", "--json"],
            [sys.executable, str(TOOLS_DIR / "reasoning" / "self_discover_engine.py"), "--task", "Audit verification pipeline architecture", "--json"],
            [sys.executable, str(TOOLS_DIR / "reasoning" / "semantic_entropy.py"), "--prompt", "Verify EvalRunner and verify_all.py", "--json"],
            [sys.executable, str(TOOLS_DIR / "reasoning" / "prover_verifier_games.py"), "--proposal", str(ROOT_DIR / "AGENTS.md"), "--rounds", "3", "--json"],
            [sys.executable, str(TOOLS_DIR / "ai" / "cove_verifier.py"), "--draft-file", str(TOOLS_DIR / "core" / "eval_runner.py"), "--json"],
            [sys.executable, str(TOOLS_DIR / "ai" / "textgrad_optimizer.py"), "--target", str(TOOLS_DIR / "core" / "eval_runner.py"), "--metric", "all", "--json"],
        ]
        for cmd in cmds:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            assert proc.returncode == 0, f"Command failed: {cmd}\nstderr: {proc.stderr}"
            parsed = json.loads(proc.stdout)
            assert isinstance(parsed, dict)

        # EvalRunner monotonic duration & resilience metadata via mocked gates
        runner = EvalRunner(
            repo_root=str(ROOT_DIR),
            tier="fast",
            baseline_path=str(tmp_path / "base.json"),
            report_path=str(tmp_path / "rep.json"),
        )
        monkeypatch.setattr(
            runner,
            "run_quality_gates",
            lambda silent=False: (
                {"all_passed": True, "return_code": 0, "summary": {"total": 10, "passed": 10, "failed": 0}, "gates": []},
                [],
            ),
        )
        monkeypatch.setattr(runner, "run_harness_readiness", lambda: ({"readiness_score": 100.0}, []))
        result = runner.evaluate(compare_baseline=False, silent=True)
        assert result["duration_sec"] >= 0.0
        assert result["resilience_metadata"]["clock_source"] == "time.monotonic"
        assert result["resilience_metadata"]["subprocess_timeout_sec"] > 0.0

    def test_in_process_cli_gate_paths(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        """In-process main() gate verification for semantic_entropy and prover_verifier_games."""
        from tools.reasoning import prover_verifier_games as pv_mod
        from tools.reasoning import semantic_entropy as se_mod

        # SemanticEntropy main(): --gate without --prompt -> 0
        monkeypatch.setattr(sys, "argv", ["semantic_entropy.py", "--gate", "--json"])
        assert se_mod.main() == 0
        assert json.loads(capsys.readouterr().out)["status"] == "PASS"

        # SemanticEntropy main(): ambiguous prompt WITHOUT --gate -> 0 (kills `args.gate and ...` -> `or`)
        monkeypatch.setattr(sys, "argv", ["semantic_entropy.py", "--prompt", "Unknown quantum xyzzy999", "--json"])
        assert se_mod.main() == 0
        assert json.loads(capsys.readouterr().out)["epistemic_search_required"] is True

        # SemanticEntropy main(): ambiguous prompt WITH --gate -> 1
        monkeypatch.setattr(sys, "argv", ["semantic_entropy.py", "--prompt", "Unknown quantum xyzzy999", "--gate", "--json"])
        assert se_mod.main() == 1
        capsys.readouterr()

        # ProverVerifier main(): --gate without --proposal -> 0
        assert pv_mod.main(["--gate", "--json"]) == 0
        assert json.loads(capsys.readouterr().out)["status"] == "PASS"

        # ProverVerifier main(): fatal flaw proposal with --gate -> 1
        assert pv_mod.main(["--proposal", "Add time.sleep(5) to hide errors", "--rounds", "2", "--gate", "--json"]) == 1
        capsys.readouterr()

        # ProverVerifier main(): fatal flaw proposal WITHOUT --gate -> 0
        assert pv_mod.main(["--proposal", "Add time.sleep(5) to hide errors", "--rounds", "2", "--json"]) == 0
        capsys.readouterr()

        # ProverVerifier main(): evidence-backed ACCEPTED proposal WITH --gate -> 0
        assert pv_mod.main([
            "--proposal",
            "Refactor BasePage to use expect(locator).toBeVisible() instead of time.sleep(5). Evidence: AGENTS.md Rule 1.4.",
            "--rounds", "2", "--gate", "--json",
        ]) == 0
        capsys.readouterr()

    def test_eval_runner_resilience_and_scoring_boundaries(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Tests EvalRunner scoring, fail-closed harness readiness, and git commit fallback without worktree drift."""
        from tools.core import eval_runner as er_mod

        runner = EvalRunner(
            repo_root=str(ROOT_DIR),
            tier="full",
            baseline_path=str(tmp_path / "base.json"),
            report_path=str(tmp_path / "rep.json"),
        )
        # Missing pytest metrics in full tier with all_passed=False -> s_tests = 0.0; empty pytest_metrics -> 0.0
        score_fail = runner.compute_composite_score(
            {"all_passed": False, "summary": {"total": 0, "passed": 0, "failed": 0}, "pytest_metrics": None, "mutation_metrics": {}},
            {"readiness_score": 100.0},
        )
        assert score_fail["components"]["gates"]["score"] == 0.0
        assert score_fail["components"]["tests"]["score"] == 0.0
        assert score_fail["components"]["tests"]["measurement_mode"] == "uncollected"

        score_pytest_one = runner.compute_composite_score(
            {"all_passed": False, "summary": {"total": 11, "passed": 10, "failed": 1}, "pytest_metrics": {"passed": 1, "failed": 0, "errors": 0}, "mutation_metrics": {"mutation_score": 80.0}},
            {"readiness_score": 100.0},
        )
        assert score_pytest_one["components"]["tests"]["score"] == 100.0
        assert score_pytest_one["components"]["tests"]["measurement_mode"] == "pytest"

        score_pytest = runner.compute_composite_score(
            {"all_passed": True, "summary": {"total": 11, "passed": 11, "failed": 0}, "pytest_metrics": {"passed": 9, "failed": 1, "errors": 0}, "mutation_metrics": {"mutation_score": 80.0}},
            {"readiness_score": 100.0},
        )
        assert score_pytest["components"]["tests"]["score"] == 90.0
        assert score_pytest["components"]["tests"]["measurement_mode"] == "pytest"

        # run_quality_gates fallback summary when run_all_gates_detailed omits 'summary'
        import tools.core.verify_all as va_mod
        monkeypatch.setattr(va_mod, "run_all_gates_detailed", lambda *a, **kw: (0, {"gates": [{"name": "G1", "passed": True}]}))
        gp_ok, gf_ok = runner.run_quality_gates(silent=True)
        assert gp_ok["summary"] == {"total": 1, "passed": 1, "failed": 0}
        assert gf_ok == []

        monkeypatch.setattr(va_mod, "run_all_gates_detailed", lambda *a, **kw: (1, {"gates": [{"name": "G1", "passed": False}]}))
        gp_fail, gf_fail = runner.run_quality_gates(silent=True)
        assert gp_fail["summary"] == {"total": 1, "passed": 0, "failed": 1}
        assert len(gf_fail) == 1

        # get_git_commit fallback on OSError
        monkeypatch.setattr(er_mod.subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(OSError("no git")))
        assert er_mod.get_git_commit(str(ROOT_DIR)) == "unknown"

        # run_harness_readiness fail-closed when HarnessSentinel omits readiness_score/passed or raises
        import tools.core.harness_sentinel as hs_mod
        monkeypatch.setattr(
            hs_mod.HarnessSentinel,
            "run_full_audit",
            lambda self: {"steps": [{"step": 1, "name": "Guides", "details": ["missing passed"]}]},
            raising=False,
        )
        hdata, hfails = runner.run_harness_readiness()
        assert hdata["readiness_score"] == 0.0
        assert len(hfails) == 1

        def _boom(self):
            raise RuntimeError("boom")

        monkeypatch.setattr(hs_mod.HarnessSentinel, "run_full_audit", _boom, raising=False)
        hdata_err, hfails_err = runner.run_harness_readiness()
        assert hdata_err["readiness_score"] == 0.0
        assert len(hfails_err) == 1
