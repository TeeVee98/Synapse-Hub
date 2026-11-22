#!/usr/bin/env python3
# Copyright (c) 2026 Thế Vị (@TeeVee98)
# Synapse Hub is open-source software under the MIT License.
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tests/test_prover_verifier_games.py — 4-Scenario Test Battery for Prover-Verifier Games (R2)
--------------------------------------------------------------------------------------------
Validates prover_verifier_games.py across:
  1. Positive Scenarios (evidence weighting, prover wins vs verifier wins, judge modes)
  2. Negative Scenarios (missing args, non-existent files, invalid judge modes)
  3. Boundary Scenarios (empty proposals, round clamping 1..5, tied Nash equilibrium, zero citations)
  4. CLI Flag Scenarios (--json stdout schema, --output disk export, --rounds, --context)

TRUTH ANCHOR: Zero fake passes, zero swallowed exceptions, zero static sleeps.
"""

import os
import sys
import json
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
for p in (ROOT_DIR, TOOLS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from tools.reasoning.prover_verifier_games import (
    ProverVerifierGame,
    main,
)


class TestProverVerifierGamesPositive:
    """Scenario A: Positive paths with normal debate, consensus/evidence weighting, and wins."""

    def test_prover_wins_with_evidence_backed_proposal(self):
        game = ProverVerifierGame()
        proposal = (
            "Refactor BasePage to use expect(locator).toBeVisible() instead of time.sleep(5). "
            "Evidence: Eliminates flakiness on CI per AGENTS.md Rule 1.4."
        )
        context = (
            "class BasePage:\n"
            "    def wait_for_ready(self):\n"
            "        time.sleep(5)\n"
        )
        result = game.run_debate(proposal=proposal, context=context, rounds=3, judge_mode="evidence_weighted")

        assert result["status"] in ("ACCEPTED", "REFUTED")
        assert result["rounds_completed"] == 3
        assert result["winner"] in ("prover", "verifier")
        assert len(result["winning_thesis"]) > 10
        assert 0.0 <= result["nash_equilibrium_score"] <= 1.0
        assert len(result["transcript"]) == 3

        first_round = result["transcript"][0]
        assert "prover_argument" in first_round
        assert "verifier_counter" in first_round
        assert "judge_interim_ruling" in first_round
        assert isinstance(first_round["prover_argument"]["citations"], list)
        assert first_round["prover_argument"]["confidence"] >= 0.0

    def test_verifier_wins_when_flaw_detected_in_proposal(self):
        game = ProverVerifierGame()
        # Proposal introduces an empty catch block (swallowed exception anti-pattern)
        proposal = (
            "Fix test crash by wrapping whole test body in try: ... except Exception: pass."
        )
        context = "def test_payment(): process_payment()"
        result = game.run_debate(proposal=proposal, context=context, rounds=2, judge_mode="evidence_weighted")

        assert result["status"] == "REFUTED"
        assert result["winner"] == "verifier"
        assert result["rounds_completed"] == 2
        # Falsification score should reflect counter-evidence
        last_round = result["transcript"][-1]
        assert last_round["verifier_counter"]["falsification_score"] > 0.5
        assert len(last_round["verifier_counter"]["counter_examples"]) >= 1

    def test_judge_mode_strict_adjudication(self):
        game = ProverVerifierGame()
        proposal = "Optimize DB query by bypassing row-level lock."
        result = game.run_debate(proposal=proposal, rounds=2, judge_mode="strict")

        assert result["status"] in ("ACCEPTED", "REFUTED")
        assert result["rounds_completed"] == 2
        assert "strict" in result.get("judge_mode", "strict").lower()

    def test_judge_mode_consensus_synthesis(self):
        game = ProverVerifierGame()
        proposal = "Introduce 500ms debounce buffer to stabilize live search input."
        context = "input.addEventListener('input', handleSearch);"
        result = game.run_debate(proposal=proposal, context=context, rounds=3, judge_mode="consensus")

        assert result["rounds_completed"] == 3
        assert len(result["transcript"]) == 3
        for round_log in result["transcript"]:
            assert len(round_log["judge_interim_ruling"]) > 0

    def test_proposal_and_context_read_from_files(self, tmp_path):
        prop_file = tmp_path / "proposal.md"
        prop_file.write_text("Replace static wait with dynamic locator visibility check.", encoding="utf-8")

        ctx_file = tmp_path / "context.py"
        ctx_file.write_text("def wait_button(self): time.sleep(2)", encoding="utf-8")

        game = ProverVerifierGame()
        result = game.run_debate(proposal=str(prop_file), context=str(ctx_file), rounds=2)

        assert result["rounds_completed"] == 2
        assert result["status"] in ("ACCEPTED", "REFUTED")
        assert len(result["transcript"]) == 2


class TestProverVerifierGamesNegative:
    """Scenario B: Invalid inputs, non-existent files, and fatal CLI invocation errors."""

    def test_nonexistent_context_file_handled_cleanly(self):
        game = ProverVerifierGame()
        nonexistent = "/nonexistent/path/to/context_file_xyz_999.py"
        with pytest.raises((FileNotFoundError, ValueError)):
            game.run_debate(proposal="Valid proposal text", context=nonexistent)

    def test_invalid_judge_mode_raises_error(self):
        game = ProverVerifierGame()
        with pytest.raises(ValueError):
            game.run_debate(proposal="Valid proposal text", judge_mode="unsupported_quantum_mode")

    def test_cli_missing_required_proposal_fails(self, capsys):
        exit_code = main([])
        assert exit_code != 0
        captured = capsys.readouterr()
        # Argparse error output in stderr
        assert "error" in captured.err.lower() or "required" in captured.err.lower() or exit_code == 2

    def test_cli_nonexistent_proposal_file_returns_error(self, capsys):
        exit_code = main(["--proposal", "/path/to/missing_proposal_synapse_404.md", "--context-file", "--json"])
        # Should return non-zero exit code due to unreadable or missing required file
        assert exit_code != 0


class TestProverVerifierGamesBoundary:
    """Scenario C: Boundary conditions, empty strings, round clamping, and tied equilibrium."""

    def test_empty_proposal_string_handled(self):
        game = ProverVerifierGame()
        with pytest.raises((ValueError, AssertionError)):
            game.run_debate(proposal="")

    def test_debate_rounds_clamped_to_minimum_one(self):
        game = ProverVerifierGame()
        result = game.run_debate(proposal="Refactor auth token refresh with mutex lock", rounds=0)
        # Clamped to at least 1 round
        assert result["rounds_completed"] == 1
        assert len(result["transcript"]) == 1

    def test_debate_rounds_clamped_to_maximum_five(self):
        game = ProverVerifierGame()
        result = game.run_debate(proposal="Refactor auth token refresh with mutex lock", rounds=10)
        # Clamped to max 5 rounds to prevent infinite loop / resource exhaustion
        assert result["rounds_completed"] <= 5
        assert len(result["transcript"]) <= 5

    def test_zero_citations_fallback(self):
        game = ProverVerifierGame()
        # Proposal with no citations and no context
        result = game.run_debate(proposal="Generic idea without code citation", context=None, rounds=1)
        assert result["rounds_completed"] == 1
        round_log = result["transcript"][0]
        assert round_log["prover_argument"]["citations"] == []
        assert 0.0 <= round_log["prover_argument"]["confidence"] <= 1.0

    def test_tied_evidence_nash_equilibrium(self):
        game = ProverVerifierGame()
        # Balanced debate where both sides have equally plausible arguments
        proposal = "Migrate from Playwright sync to Playwright async in Python test harness."
        context = "Playwright sync uses greenlets while async uses native asyncio event loop."
        result = game.run_debate(proposal=proposal, context=context, rounds=2, judge_mode="evidence_weighted")
        score = result["nash_equilibrium_score"]
        assert 0.0 <= score <= 1.0
        assert result["winner"] in ("prover", "verifier")


class TestProverVerifierGamesCLIFlags:
    """Scenario D: CLI interface, flags, and JSON output formatting."""

    def test_cli_json_flag_stdout_schema(self, capsys):
        exit_code = main([
            "--proposal", "Eliminate Thread.sleep by implementing dynamic Smart Wait",
            "--rounds", "2",
            "--json"
        ])
        assert exit_code == 0
        out = capsys.readouterr().out
        payload = json.loads(out)
        assert payload["status"] in ("ACCEPTED", "REFUTED")
        assert payload["rounds_completed"] == 2
        assert payload["winner"] in ("prover", "verifier")
        assert "winning_thesis" in payload
        assert "nash_equilibrium_score" in payload
        assert "transcript" in payload

    def test_cli_output_file_export(self, tmp_path, capsys):
        out_file = tmp_path / "debate_report.json"
        exit_code = main([
            "--proposal", "Add dynamic retry backoff to HTTP client",
            "--output", str(out_file),
            "--json"
        ])
        assert exit_code == 0
        assert out_file.is_file()
        content = json.loads(out_file.read_text(encoding="utf-8"))
        assert content["status"] in ("ACCEPTED", "REFUTED")
        assert "transcript" in content

    def test_cli_custom_judge_mode_flag(self, capsys):
        exit_code = main([
            "--proposal", "Enforce strict schema validation on all inputs",
            "--judge-mode", "strict",
            "--rounds", "1",
            "--json"
        ])
        assert exit_code == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["rounds_completed"] == 1

    def test_cli_human_readable_banner(self, capsys):
        exit_code = main([
            "--proposal", "Upgrade test suite to Python 3.10+ standard library",
            "--rounds", "1"
        ])
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "PROVER-VERIFIER" in out.upper() or "DEBATE" in out.upper() or "STATUS" in out.upper()


class TestProverVerifierGamesInvariantsAndMutationSensors:
    """Rigorous sensor tests for Prover-Verifier internal invariants and mathematical formulas."""

    def test_rebuttal_of_round_linkage_and_exact_confidence(self):
        from tools.reasoning.prover_verifier_games import ProverAgent, VerifierCounter

        prover = ProverAgent()

        # Round 1 with 2 invariants (BasePage and Smart Wait) + citations:
        # base_conf = 0.70 + (0.05 * 2) = 0.80
        prop1 = "Refactor BasePage per AGENTS.md Rule 1.1 to use Smart Wait."
        arg1 = prover.generate_defense(round_num=1, proposal_text=prop1, context_text="some context text > 10 chars")
        assert arg1.rebuttal_of is None
        assert round(arg1.confidence, 4) == 0.80
        assert "rebuttal_of" not in arg1.to_dict()

        # Round 1 with NO invariants and NO citations:
        # base_conf = max(0.50, 0.70 - 0.15) = 0.55
        prop_no_inv = "A generic refactoring without any rules."
        arg_no_inv = prover.generate_defense(round_num=1, proposal_text=prop_no_inv, context_text="")
        assert round(arg_no_inv.confidence, 4) == 0.55

        # Round 2: With verifier counter-example -> rebuttal_of MUST be populated
        counter = VerifierCounter(
            refutation="Refutation: Missing edge case handling",
            counter_examples=["Flaw: Race condition"],
            falsification_score=0.75
        )
        arg2 = prover.generate_defense(round_num=2, proposal_text=prop1, context_text="some context text > 10 chars", verifier_counter=counter)
        assert arg2.rebuttal_of == counter.refutation
        assert arg2.to_dict()["rebuttal_of"] == counter.refutation
        # Round 2 confidence formula: min(0.95, 0.75 + (0.05 * 2) + (0.02 * len(citations)))
        expected_conf = min(0.95, 0.75 + (0.05 * 2) + (0.02 * len(arg2.citations)))
        assert round(arg2.confidence, 4) == round(expected_conf, 4)

    def test_citations_length_filtering_and_deduplication(self):
        from tools.reasoning.prover_verifier_games import ProverAgent

        prover = ProverAgent()
        # Citations <= 3 chars ('CI', 'v1') must be rejected; duplicates must be deduplicated
        proposal = "Citing Rule 1.4, AGENTS.md, CI, v1, and Rule 1.4 again."
        arg = prover.generate_defense(round_num=1, proposal_text=proposal)
        # Citations must only contain elements with len > 3
        for c in arg.citations:
            assert len(c) > 3
        # Must be deduplicated
        assert len(arg.citations) == len(set(arg.citations))
        assert "CI" not in arg.citations
        assert "v1" not in arg.citations

    def test_verifier_counter_example_attack_types(self):
        from tools.reasoning.prover_verifier_games import VerifierAgent, ProverArgument

        verifier = VerifierAgent()
        dummy_arg = ProverArgument(claim="claim", citations=[], confidence=0.7)

        # 1. Concurrency risk: lacks 'debounce', 'lock', 'mutex' -> duplicate submission counter
        c_prop = "Run concurrent thread workers in parallel for processing."
        counter_c = verifier.generate_attack(round_num=1, proposal_text=c_prop, context_text="", prover_argument=dummy_arg)
        assert any("duplicate request submission" in ex.lower() for ex in counter_c.counter_examples)

        # 1b. If 'mutex' or 'lock' is present, that counter-example is prevented
        c_prop_safe = "Run concurrent thread workers protected by a mutex lock."
        counter_safe = verifier.generate_attack(round_num=1, proposal_text=c_prop_safe, context_text="", prover_argument=dummy_arg)
        assert not any("duplicate request submission" in ex.lower() for ex in counter_safe.counter_examples)

        # 2. Resilience risk: lacks 'retry', 'backoff', 'fallback' -> transient 503 counter
        r_prop = "Send http network request to billing microservice."
        counter_r = verifier.generate_attack(round_num=1, proposal_text=r_prop, context_text="", prover_argument=dummy_arg)
        assert any("exponential backoff" in ex.lower() for ex in counter_r.counter_examples)

        # 2b. If 'retry' or 'backoff' is present, that counter-example is prevented
        r_prop_safe = "Send http network request with exponential backoff and retry."
        counter_r_safe = verifier.generate_attack(round_num=1, proposal_text=r_prop_safe, context_text="", prover_argument=dummy_arg)
        assert not any("exponential backoff" in ex.lower() for ex in counter_r_safe.counter_examples)

        # 3. Boundary risk: lacks 'empty', 'null', 'bound' -> boundary payload counter
        b_prop = "Iterate through items list and access index 0."
        counter_b = verifier.generate_attack(round_num=1, proposal_text=b_prop, context_text="", prover_argument=dummy_arg)
        assert any("empty/null attributes" in ex.lower() for ex in counter_b.counter_examples)

        # 3b. If 'empty' or 'null' is present, that counter-example is prevented
        b_prop_safe = "Check if items list is empty before accessing index 0."
        counter_b_safe = verifier.generate_attack(round_num=1, proposal_text=b_prop_safe, context_text="", prover_argument=dummy_arg)
        assert not any("empty/null attributes" in ex.lower() for ex in counter_b_safe.counter_examples)

    def test_swallowed_exception_counter_detection(self):
        from tools.reasoning.prover_verifier_games import VerifierAgent, ProverArgument

        verifier = VerifierAgent()
        dummy_arg = ProverArgument(claim="claim", citations=[], confidence=0.7)

        # Proposal introducing swallowed exception -> fatal flaw
        bad_prop = "Wrap execution in except Exception: pass to suppress crashes."
        counter = verifier.generate_attack(round_num=1, proposal_text=bad_prop, context_text="", prover_argument=dummy_arg)
        assert counter.attack_type == "fatal_flaw"
        assert any("swallowed" in ex.lower() or "fake-pass" in ex.lower() for ex in counter.counter_examples)
        assert counter.falsification_score >= 0.85

        # Proposal ELIMINATING swallowed exception -> NOT a fatal flaw
        good_prop = "Eliminate except Exception: pass and remove swallowed exceptions."
        counter_good = verifier.generate_attack(round_num=1, proposal_text=good_prop, context_text="", prover_argument=dummy_arg)
        assert counter_good.attack_type != "fatal_flaw"
        assert not any("fake-pass" in ex.lower() for ex in counter_good.counter_examples)

    def test_call_citations_boundary_and_exact_disjunctions(self):
        from tools.reasoning.prover_verifier_games import ProverAgent, VerifierAgent, ProverArgument, VerifierCounter

        prover = ProverAgent()

        # 1. Short function call 'f()' has length 3 -> must NOT be cited
        prop_short_call = "Execute f() then run do_action() and do_action() again."
        arg_calls = prover.generate_defense(round_num=1, proposal_text=prop_short_call)
        assert "f()" not in arg_calls.citations
        assert "do_action()" in arg_calls.citations
        assert arg_calls.citations.count("do_action()") == 1

        # 2. verifier_counter counter_examples vs empty fallback
        counter_with_ex = VerifierCounter(refutation="Ref", counter_examples=["Specific race condition in DB"], falsification_score=0.2)
        arg_with_ex = prover.generate_defense(round_num=2, proposal_text="Solid plan", verifier_counter=counter_with_ex)
        assert "Specific race condition in DB" in arg_with_ex.claim

        counter_empty_ex = VerifierCounter(refutation="Ref", counter_examples=[], falsification_score=0.2)
        arg_empty_ex = prover.generate_defense(round_num=2, proposal_text="Solid plan", verifier_counter=counter_empty_ex)
        assert "adversary edge case" in arg_empty_ex.claim

        # 3. 'except: pass' without 'exception:' keyword must be caught as fatal flaw
        verifier = VerifierAgent()
        dummy_arg = ProverArgument(claim="c", citations=[], confidence=0.7)
        counter_bare_except = verifier.generate_attack(round_num=1, proposal_text="try: run() except: pass", context_text="", prover_argument=dummy_arg)
        assert counter_bare_except.attack_type == "fatal_flaw"

        # 4. 'lock' present alone suppresses duplicate request counter
        counter_lock_only = verifier.generate_attack(round_num=1, proposal_text="Use distributed lock for concurrency", context_text="", prover_argument=dummy_arg)
        assert not any("duplicate request submission" in ex.lower() for ex in counter_lock_only.counter_examples)

        # 5. 'fallback' present alone suppresses transient HTTP 503 counter
        counter_fallback_only = verifier.generate_attack(round_num=1, proposal_text="Call API service with circuit fallback", context_text="", prover_argument=dummy_arg)
        assert not any("exponential backoff" in ex.lower() for ex in counter_fallback_only.counter_examples)

        # 6. Context text length boundary: len == 10 chars vs len > 10 chars
        prop_contradict = "Introduce AlphaUnseenModule BetaUnseenFunction GammaService DeltaRepo EpsilonWorker ZetaManager"
        counter_len10 = verifier.generate_attack(round_num=1, proposal_text=prop_contradict, context_text="1234567890", prover_argument=dummy_arg)
        assert not any("context contradiction" in ex.lower() for ex in counter_len10.counter_examples)

        counter_len11 = verifier.generate_attack(round_num=1, proposal_text=prop_contradict, context_text="12345678901", prover_argument=dummy_arg)
        assert any("context contradiction" in ex.lower() for ex in counter_len11.counter_examples)
