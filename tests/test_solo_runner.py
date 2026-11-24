#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

import os
import sys
import json
import tempfile
import dataclasses
import pytest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_TESTS_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.orchestration.solo_runner import (
    run_debate,
    certify_red_phase,
    certify_green_phase,
    certify_mutation_phase,
    detect_tautological_red,
    resolve_auto_targets,
    get_status,
    resolve_test_adapter,
    PytestAdapter,
    JestPlaywrightAdapter,
    JUnitXMLAdapter,
    select_tournament_winner,
    run_tournament,
    AstTautologyAnalyzer,
    MicroContextPayload,
    SpeculativeCandidatePrompt,
    MicroContextExtractor,
    AsyncCandidateSpeculator,
    ZeroTokenArbiter,
    record_solo_swarm_event,
    query_instinct_guidance,
    record_instinct_observation,
    shard_test_execution,
    certify_purple_phase,
    execute_external_oracle,
    verify_neuro_symbolic_constraints,
    calculate_composite_fitness_score,
    compute_pareto_front,
    compute_test_files_snapshot,
    extract_test_files_from_cmd,
    ReadOnlyTestGuard,
    lock_test_files,
    unlock_test_files,
    execute_state_flushing_batch,
)


class TestSoloSwarmRunner:
    """Comprehensive test suite for Solo-Swarm 4-Weapon Orchestrator."""

    def test_debate_positive_extraction(self):
        """Scenario 1: Positive - Weapon 4 debate generates structured test scenarios."""
        result = run_debate(proposal="Implement idempotent JWT refresh flow", rounds=2)
        assert result["status"] == "COMPLETED"
        assert result["proposal"] == "Implement idempotent JWT refresh flow"
        assert result["counter_examples_count"] >= 1
        assert len(result["structured_test_scenarios"]) == result["counter_examples_count"]
        first_sc = result["structured_test_scenarios"][0]
        assert first_sc["id"].startswith("TC-ADV-")
        assert len(first_sc["description"]) > 0
        assert result["contrarian_perspectives_injected"] >= 4

    def test_red_phase_valid_failure(self):
        """Scenario 1: Positive - Weapon 1 certifies Red phase when test physically fails on domain error."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            receipt = os.path.join(tmp_dir, "test_red.json")
            # Running a domain failure (AttributeError on missing method)
            cmd = f'{sys.executable} -c "raise AttributeError(\'Domain service method not implemented\')"'
            res = certify_red_phase(test_cmd=cmd, receipt_path=receipt)

            assert res["status"] == "CERTIFIED_RED"
            assert res["passed"] is True
            assert res["exit_code"] == 1
            assert os.path.exists(receipt)

            with open(receipt, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data["status"] == "CERTIFIED_RED"
            assert data["exit_code"] == 1
            assert len(data["failure_sha256"]) == 64

    def test_red_phase_real_pytest_failure_accepted(self):
        """Scenario 1: Positive - Real pytest test with dynamic assertion failure is certified Red, not rejected as tautology."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = os.path.join(tmp_dir, "test_sample.py")
            receipt = os.path.join(tmp_dir, "test_red.json")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(
                    "def get_status():\n"
                    "    return 404\n"
                    "\n"
                    "def test_calc():\n"
                    "    actual = get_status()\n"
                    "    expected = 200\n"
                    "    assert actual == expected\n"
                )
            cmd = f"{sys.executable} -m pytest \"{test_file}\""
            res = certify_red_phase(test_cmd=cmd, receipt_path=receipt)
            assert res["status"] == "CERTIFIED_RED"
            assert res["passed"] is True
            assert os.path.exists(receipt)

    def test_ast_constant_propagation_rejected(self):
        """Scenario 2: Anti-Cheat - AST analyzer rejects variable constant-propagation cheat x = 1; y = 2; assert x == y."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = os.path.join(tmp_dir, "test_cheat.py")
            receipt = os.path.join(tmp_dir, "test_red.json")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(
                    "def test_intermediate_var_cheat():\n"
                    "    x = 1\n"
                    "    y = 2\n"
                    "    assert x == y\n"
                )
            cmd = f"{sys.executable} -m pytest \"{test_file}\""
            res = certify_red_phase(test_cmd=cmd, receipt_path=receipt)
            assert res["status"] == "TAUTOLOGICAL_RED_REJECTED"
            assert res["passed"] is False
            assert "AST Constant-Propagation" in res["error"]
            assert not os.path.exists(receipt)

    def test_green_phase_valid_success(self):
        """Scenario 1: Positive - Weapon 2 certifies Green phase when test passes after Red receipt."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            receipt = os.path.join(tmp_dir, "test_red.json")
            # Step 1: Record valid Red receipt
            fail_cmd = f'{sys.executable} -c "raise AttributeError(\'unimplemented\')"'
            red_res = certify_red_phase(test_cmd=fail_cmd, receipt_path=receipt)
            assert red_res["passed"] is True

            # Step 2: Certify Green
            pass_cmd = f'{sys.executable} -c "import sys; sys.exit(0)"'
            green_res = certify_green_phase(test_cmd=pass_cmd, receipt_path=receipt)
            assert green_res["status"] == "CERTIFIED_GREEN"
            assert green_res["passed"] is True
            assert green_res["exit_code"] == 0

    def test_fake_red_rejected(self):
        """Scenario 2: Negative - Weapon 1 rejects test that passes on initial run (Fake Red)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            receipt = os.path.join(tmp_dir, "fake_red.json")
            cmd = f'{sys.executable} -c "import sys; sys.exit(0)"'
            res = certify_red_phase(test_cmd=cmd, receipt_path=receipt)

            assert res["status"] == "FAKE_RED_REJECTED"
            assert res["passed"] is False
            assert res["exit_code"] == 0
            assert "Fake Red Violation" in res["error"]
            assert not os.path.exists(receipt)

    def test_tautological_red_rejected(self):
        """Scenario 2: Anti-Cheat - Weapon 1 rejects literal assert False or assert 1 == 2."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            receipt = os.path.join(tmp_dir, "tautology_red.json")
            # Intentional cheat: assert False
            cmd_false = f'{sys.executable} -c "assert False"'
            res_false = certify_red_phase(test_cmd=cmd_false, receipt_path=receipt)
            assert res_false["status"] == "TAUTOLOGICAL_RED_REJECTED"
            assert res_false["passed"] is False
            assert "Tautological Red Violation" in res_false["error"]
            assert not os.path.exists(receipt)

            # Intentional cheat: assert 1 == 2
            cmd_num = f'{sys.executable} -c "assert 1 == 2"'
            res_num = certify_red_phase(test_cmd=cmd_num, receipt_path=receipt)
            assert res_num["status"] == "TAUTOLOGICAL_RED_REJECTED"
            assert res_num["passed"] is False
            assert "assert 1 == 2" in res_num["error"]

    def test_tautology_detector_unit(self):
        """Unit test for detect_tautological_red heuristic."""
        # Cheat: Literal assert False in source code
        is_t1, msg1 = detect_tautological_red(">       assert False\nE       assert False\n")
        assert is_t1 is True
        assert "assert False" in msg1

        # Cheat: Literal comparison in source code
        is_t2, msg2 = detect_tautological_red(">       assert 0 == 1\nE       assert 0 == 1\n")
        assert is_t2 is True

        # Real test: Dynamic attribute comparison failing with evaluated 404 == 200
        pytest_real = (
            "    def test_status():\n"
            "        resp = get_status()\n"
            ">       assert resp.code == 200\n"
            "E       assert 404 == 200\n"
            "tests/test_api.py:10: AssertionError\n"
        )
        is_real, msg_real = detect_tautological_red(pytest_real, "pytest tests/test_api.py")
        assert is_real is False, f"Real dynamic test was falsely rejected: {msg_real}"

        # Real test: Dynamic boolean assertion failing with evaluated False
        pytest_bool = (
            "    def test_auth():\n"
            ">       assert user.is_authenticated\n"
            "E       assert False\n"
            "tests/test_auth.py:12: AssertionError\n"
        )
        is_bool, msg_bool = detect_tautological_red(pytest_bool, "pytest tests/test_auth.py")
        assert is_bool is False, f"Real boolean test was falsely rejected: {msg_bool}"

        # Real test: Domain exception
        is_t3, msg3 = detect_tautological_red("E       AttributeError: module has no attribute 'foo'\n")
        assert is_t3 is False
        assert msg3 is None

        # AST Constant-propagation Unit Test: intermediate variables
        from tools.orchestration.solo_runner import AstTautologyAnalyzer
        analyzer = AstTautologyAnalyzer()
        findings = analyzer.analyze_source(
            "def test_foo():\n"
            "    a = 10\n"
            "    b = 20\n"
            "    assert a == b\n"
        )
        assert len(findings) == 1
        assert "AST Constant-Propagation" in findings[0][2]
        assert "assert a == b" in findings[0][1]

        # AST Constant-propagation Unit Test: constant folding
        findings_fold = AstTautologyAnalyzer().analyze_source("def test_fold(): assert 1 + 1 == 3")
        assert len(findings_fold) == 1
        assert "assert 1 + 1 == 3" in findings_fold[0][1]

    def test_auto_target_resolution(self):
        """Scenario 3: Anti-Shrinking - resolve_auto_targets excludes tests, handles untracked files and finds modified sources."""
        targets = resolve_auto_targets(repo_root=_REPO_ROOT)
        # Should return a list of strings
        assert isinstance(targets, list)
        for t in targets:
            assert not t.startswith("tests/")
            assert not t.startswith("reports/")
            assert not t.startswith("docs/")

    def test_green_without_red_rejected(self):
        """Scenario 2: Negative - Weapon 2 rejects Green certification when Red receipt is missing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            non_existent_receipt = os.path.join(tmp_dir, "ghost_red.json")
            cmd = f'{sys.executable} -c "import sys; sys.exit(0)"'
            res = certify_green_phase(test_cmd=cmd, receipt_path=non_existent_receipt)

            assert res["status"] == "MISSING_RED_RECEIPT"
            assert res["passed"] is False
            assert "Cannot certify Green Phase without a prior Red Receipt" in res["error"]

    def test_corrupt_red_receipt_rejected(self):
        """Scenario 2: Negative - Weapon 2 handles corrupt Red receipt gracefully."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corrupt_receipt = os.path.join(tmp_dir, "corrupt.json")
            with open(corrupt_receipt, "w", encoding="utf-8") as f:
                f.write("{invalid_json: true")

            cmd = f'{sys.executable} -c "import sys; sys.exit(0)"'
            res = certify_green_phase(test_cmd=cmd, receipt_path=corrupt_receipt)
            assert res["status"] == "CORRUPT_RED_RECEIPT"
            assert res["passed"] is False

    def test_empty_test_command_boundary(self):
        """Scenario 3: Boundary - Empty test command handled gracefully without crash."""
        res_red = certify_red_phase(test_cmd="")
        assert res_red["status"] == "ERROR"
        assert res_red["passed"] is False

        res_green = certify_green_phase(test_cmd="   ")
        assert res_green["status"] == "ERROR"
        assert res_green["passed"] is False

    def test_mutation_phase_missing_target_boundary(self):
        """Scenario 3: Boundary - Mutation certification on non-existent file handled gracefully."""
        res = certify_mutation_phase(target_file="non/existent/file.py", test_cmd="pytest")
        assert res["status"] == "ERROR"
        assert res["passed"] is False
        assert "not found" in res["error"]

    def test_mutation_phase_missing_test_cmd_boundary(self):
        """Scenario 3: Boundary - Mutation certification without test command handled gracefully."""
        sample_file = os.path.join(_REPO_ROOT, "tools", "core", "check_env.py")
        res = certify_mutation_phase(target_file=sample_file, test_cmd="")
        assert res["status"] == "ERROR"
        assert res["passed"] is False
        assert "Missing test command" in res["error"]

    def test_status_inspection(self):
        """Scenario 4: CLI Status - get_status returns structured schema."""
        status = get_status(receipt_path="reports/tdd_red_receipt.json")
        assert "red_receipt_exists" in status
        assert "protocol" in status
        assert "standards_reference" in status
        assert status["contrarian_perspectives_count"] >= 4

    def test_git_resilience_fallback(self):
        """Milestone 1: Git-Resilience - Fallback scans safely when git is clean or not in a git repo."""
        with tempfile.TemporaryDirectory() as empty_dir:
            # Running resolve_auto_targets on a non-git dir should not crash
            res = resolve_auto_targets(repo_root=empty_dir)
            assert isinstance(res, list)

    def test_jest_playwright_adapter(self):
        """Milestone 3: JestPlaywrightAdapter detects literal constant expect cheats."""
        adapter = JestPlaywrightAdapter()
        # Literal cheat: expect(1).toBe(2)
        is_t1, msg1 = adapter.check_tautology("   expect(1).toBe(2)\n")
        assert is_t1 is True
        assert "expect(1).toBe(2)" in msg1

        # Real test: expect(resp.status).toBe(200)
        is_t2, msg2 = adapter.check_tautology("   expect(resp.status).toBe(200)\n")
        assert is_t2 is False

        # Forced fail
        is_t3, msg3 = adapter.check_tautology("   test.fail()\n")
        assert is_t3 is True

    def test_junit_xml_adapter(self):
        """Milestone 3: JUnitXMLAdapter parses XML failure reports and extracts errors."""
        adapter = JUnitXMLAdapter()
        with tempfile.TemporaryDirectory() as tmp_dir:
            xml_file = os.path.join(tmp_dir, "report.xml")
            with open(xml_file, "w", encoding="utf-8") as f:
                f.write(
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<testsuite name="KatalonSuite" tests="2" failures="1" errors="0">\n'
                    '  <testcase name="testPass"/>\n'
                    '  <testcase name="testFail">\n'
                    '    <failure message="assert 1 == 2">Assertion failed at line 12</failure>\n'
                    '  </testcase>\n'
                    '</testsuite>\n'
                )
            fails, errs, msgs = adapter.parse_xml_report(xml_file)
            assert fails == 1
            assert errs == 0
            assert len(msgs) == 1
            assert "assert 1 == 2" in msgs[0]

            # Check tautology detection via XML reference
            is_t, reason = adapter.check_tautology(f"Report written to {xml_file}")
            assert is_t is True
            assert "JUnit XML Tautology" in reason

    def test_resolve_test_adapter_factory(self):
        """Milestone 3: resolve_test_adapter correctly resolves adapter by command or override."""
        ad_pytest = resolve_test_adapter("pytest tests/test_foo.py")
        assert isinstance(ad_pytest, PytestAdapter)

        ad_jest = resolve_test_adapter("npx playwright test")
        assert isinstance(ad_jest, JestPlaywrightAdapter)

        ad_junit = resolve_test_adapter("katalon -runMode=console")
        assert isinstance(ad_junit, JUnitXMLAdapter)

        ad_override = resolve_test_adapter("custom_cmd", runner_override="playwright")
        assert isinstance(ad_override, JestPlaywrightAdapter)

    def test_worktree_tournament_selection(self):
        """Milestone 4: Swarm Tournament selects highest composite fitness score candidate."""
        candidates = [
            {
                "candidate_id": "candidate_1",
                "green_passed": True,
                "mutation_score": 75.0,
                "net_lines_changed": 10,
                "composite_fitness_score": 55.5,
            },
            {
                "candidate_id": "candidate_2",
                "green_passed": True,
                "mutation_score": 92.0,
                "net_lines_changed": 15,
                "composite_fitness_score": 66.4,
            },
            {
                "candidate_id": "candidate_3",
                "green_passed": False,
                "mutation_score": 0.0,
                "net_lines_changed": 5,
                "composite_fitness_score": 0.0,
            },
        ]
        winner = select_tournament_winner(candidates)
        assert winner is not None
        assert winner["candidate_id"] == "candidate_2"
        assert winner["mutation_score"] == 92.0

    def test_tournament_empty_boundary(self):
        """Milestone 4: Swarm Tournament handles missing candidates gracefully."""
        res = run_tournament(candidate_paths=[], repo_root=_REPO_ROOT)
        assert res["status"] == "ERROR"
        assert res["passed"] is False
        assert "No tournament candidate" in res["error"]

    def test_micro_context_bounding(self):
        """Milestone 1 (MCI Swarm): MicroContextExtractor bounds token footprint below 300 tokens."""
        ext_default = MicroContextExtractor()
        assert ext_default.repo_root == _REPO_ROOT
        ext_custom = MicroContextExtractor(repo_root="/custom/workspace/root")
        assert ext_custom.repo_root == "/custom/workspace/root"

        extractor = MicroContextExtractor(repo_root=_REPO_ROOT)
        sample_file = os.path.join(_REPO_ROOT, "tools", "core", "check_env.py")
        long_trace = "AssertionError: simulated failure line\n" * 50

        payload = extractor.build_micro_payload(sample_file, long_trace, max_tokens=250)
        assert payload.target_file == sample_file
        assert len(payload.ast_skeleton) > 0
        assert payload.estimated_tokens <= 300
        prompt = payload.to_compact_prompt("Test directive")
        assert "Persona Directive: Test directive" in prompt
        assert "Target Source File:" in prompt

    def test_speculative_dual_candidate(self):
        """Milestone 2 (MCI Swarm): AsyncCandidateSpeculator prepares 2 distinct personas."""
        speculator = AsyncCandidateSpeculator(repo_root=_REPO_ROOT)
        sample_file = os.path.join(_REPO_ROOT, "tools", "core", "check_env.py")
        payload, prompts = speculator.prepare_speculative_prompts(sample_file, "Error at line 10", count=2)

        assert len(prompts) == 2
        assert prompts[0].candidate_id == "cand_minimalist"
        assert prompts[0].persona == "MINIMALIST_STDLIB"
        assert prompts[0].temperature < prompts[1].temperature
        assert prompts[1].candidate_id == "cand_defensive"
        assert prompts[1].persona == "DEFENSIVE_RESILIENT"

    def test_zero_token_arbitration(self):
        """Milestone 3 (MCI Swarm): ZeroTokenArbiter evaluates candidates with 0 LLM tokens."""
        arbiter = ZeroTokenArbiter(repo_root=_REPO_ROOT)
        res = arbiter.judge_tournament(
            candidate_paths=[],
            test_cmd="pytest",
        )
        assert res["arbitration_mode"] == "100%_MECHANICAL_ZERO_TOKEN"
        assert res["tokens_consumed"] == 0
        assert res["status"] == "ERROR"

    def test_speculative_fallback_single(self):
        """Scenario: Fallback on single candidate or empty tournament without crashing."""
        speculator = AsyncCandidateSpeculator(repo_root=_REPO_ROOT)
        res = speculator.run_speculative_tournament(
            candidate_paths=[],
            test_cmd="pytest",
        )
        assert res["passed"] is False
        assert res["tokens_consumed"] == 0

    def test_event_stream_cryptographic_audit(self):
        """Subagent Skill: event-stream-qa-orchestrator hash-chained recording."""
        with tempfile.TemporaryDirectory() as td:
            stream_file = os.path.join(td, "test_stream.jsonl")
            ev1 = record_solo_swarm_event(
                event_type="RED_CERTIFIED",
                actor="red-team",
                payload={"test_cmd": "pytest test_a.py", "exit_code": 1},
                stream_path=stream_file,
                repo_root=td,
            )
            assert ev1 is not None
            assert ev1["status"] == "PASS"
            assert ev1["index"] == 1

            ev2 = record_solo_swarm_event(
                event_type="GREEN_CERTIFIED",
                actor="blue-team",
                payload={"test_cmd": "pytest test_a.py", "exit_code": 0},
                stream_path=stream_file,
                repo_root=td,
            )
            assert ev2 is not None
            assert ev2["index"] == 2
            assert ev2["prev_hash"] == ev1["event_hash"]

    def test_instinct_vault_memory_integration(self):
        """Subagent Skill: qa-memory-os observation recording & instinct guidance."""
        with tempfile.TemporaryDirectory() as td:
            record_instinct_observation(
                tool_name="test-runner",
                error_signature="sig_timeout_123",
                resolution="Added dynamic wait",
                repo_root=td,
            )
            db_path = os.path.join(td, ".agent_memory", "qa_memory.db")
            assert os.path.exists(db_path)

            guidance = query_instinct_guidance(domain="general", repo_root=td)
            assert isinstance(guidance, list)

    def test_certify_purple_phase_execution(self):
        """Subagent Skill: senior-code-review & goldfish-review (Purple Auditor)."""
        with tempfile.TemporaryDirectory() as td:
            receipt_file = os.path.join(td, "purple_receipt.json")
            res = certify_purple_phase(
                target="uncommitted",
                target_file="standards/qa-process/solo-protocol.md",
                receipt_path=receipt_file,
                repo_root=_REPO_ROOT,
            )
            assert res["status"] in ("CERTIFIED_PURPLE", "PURPLE_AUDIT_WARNINGS")
            assert os.path.exists(receipt_file)
            with open(receipt_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert "status" in data
            assert "findings" in data

    def test_actor_matrix_sharding_lpt(self):
        """Subagent Skill: actor-qa-swarm LPT bin-packing matrix sharding."""
        test_files = [
            "tests/test_solo_runner.py",
            "tests/test_micro_mutator.py",
        ]
        shards = shard_test_execution(test_files, num_shards=2, target_dir=_REPO_ROOT)
        assert len(shards) == 2
        assert shards[0]["shard_index"] == 1
        assert shards[1]["shard_index"] == 2
        assigned = shards[0]["tests"] + shards[1]["tests"]
        assert set(assigned) == set(test_files)

    def test_red_phase_error_fingerprint(self):
        """Subagent Skill: failure-autopsy-and-healing deterministic error fingerprint."""
        with tempfile.TemporaryDirectory() as td:
            receipt = os.path.join(td, "receipt.json")
            res = certify_red_phase(
                test_cmd='python3 -c "raise ValueError(\'Domain business rule failed\')"',
                receipt_path=receipt,
                cwd=td,
            )
            assert res["status"] == "CERTIFIED_RED"
            assert "error_fingerprint" in res
            assert res["error_fingerprint"].startswith("fp_")

    def test_green_phase_with_matrix_shards(self):
        """Subagent Skill: actor-qa-swarm parallel matrix sharded execution during green certification."""
        with tempfile.TemporaryDirectory() as td:
            receipt = os.path.join(td, "receipt.json")
            # Step 1: establish Red receipt
            red_res = certify_red_phase(
                test_cmd='python3 -c "raise ValueError(\'Expected red\')"',
                receipt_path=receipt,
                cwd=td,
            )
            assert red_res["status"] == "CERTIFIED_RED"

            # Step 2: certify Green with 2 parallel shards
            test_cmd = f'{sys.executable} -m pytest tests/test_micro_mutator.py tests/test_skills_schema.py'
            green_res = certify_green_phase(
                test_cmd=test_cmd,
                receipt_path=receipt,
                shard_count=2,
            )
            assert green_res["status"] == "CERTIFIED_GREEN"
            assert green_res["passed"] is True
            assert green_res["sharded"] is True

    def test_custom_event_stream_path_integration(self):
        """Subagent Skill: event-stream-qa-orchestrator custom file routing."""
        with tempfile.TemporaryDirectory() as td:
            receipt = os.path.join(td, "receipt.json")
            custom_stream = os.path.join(td, "custom_audit.jsonl")

            red_res = certify_red_phase(
                test_cmd='python3 -c "raise RuntimeError(\'Custom stream red\')"',
                receipt_path=receipt,
                event_stream_path=custom_stream,
                cwd=td,
            )
            assert red_res["status"] == "CERTIFIED_RED"
            assert os.path.exists(custom_stream)

            green_res = certify_green_phase(
                test_cmd=f'{sys.executable} -c "import sys; sys.exit(0)"',
                receipt_path=receipt,
                event_stream_path=custom_stream,
                cwd=td,
            )
            assert green_res["status"] == "CERTIFIED_GREEN"

            # Verify that custom stream recorded events
            with open(custom_stream, "r", encoding="utf-8") as f:
                lines = [json.loads(l) for l in f if l.strip()]
            assert len(lines) >= 3  # STREAM_INIT + RED_CERTIFIED + GREEN_CERTIFIED
            assert lines[1]["event_type"] == "RED_CERTIFIED"
            assert lines[2]["event_type"] == "GREEN_CERTIFIED"

    def test_dataclass_frozen_immutability_kills_m1_m5(self):
        """Mutant Killer (M1, M5): Verify MicroContextPayload and SpeculativeCandidatePrompt immutability."""
        payload = MicroContextPayload(
            target_file="test.py",
            ast_skeleton="def foo(): pass",
            target_functions=["foo"],
            failure_trace_excerpt="error",
        )
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError)) as exc_info:
            payload.target_file = "mutated.py"  # type: ignore
        assert exc_info.type in (dataclasses.FrozenInstanceError, TypeError)

        prompt = SpeculativeCandidatePrompt(
            candidate_id="cand_1",
            persona="MINIMALIST_STDLIB",
            system_directive="directive",
            temperature=0.2,
            max_tokens=600,
        )
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError)) as exc_info_prompt:
            prompt.persona = "MUTATED"  # type: ignore
        assert exc_info_prompt.type in (dataclasses.FrozenInstanceError, TypeError)

    def test_micro_context_extractor_trace_truncation_kills_m2_m4(self):
        """Mutant Killer (M2-M4): Verify trace truncation at exactly 15 lines and offloader handling."""
        extractor = MicroContextExtractor(repo_root=_REPO_ROOT)
        sample_file = os.path.join(_REPO_ROOT, "tools", "core", "check_env.py")

        # Short trace <= 15 lines
        short_trace = "\n".join([f"line_{i}" for i in range(5)])
        payload_short = extractor.build_micro_payload(sample_file, short_trace)
        assert payload_short.failure_trace_excerpt == short_trace

        # Long trace > 15 lines
        long_trace = "\n".join([f"line_{i}" for i in range(30)])
        payload_long = extractor.build_micro_payload(sample_file, long_trace)
        assert len(payload_long.failure_trace_excerpt.splitlines()) == 15
        assert payload_long.failure_trace_excerpt.splitlines()[0] == "line_15"
        assert payload_long.failure_trace_excerpt.splitlines()[-1] == "line_29"

    def test_ast_tautology_eval_all_mutants_kills_m6_m20(self):
        """Mutant Killer (M6-M20): Statically evaluates AST boolean, unary, binary, and constant expressions."""
        analyzer = AstTautologyAnalyzer()

        # Direct expression evaluation to eliminate mutant survivals
        import ast
        assert analyzer._eval_constant_expr(ast.parse("not True", mode="eval").body) == (True, False)
        assert analyzer._eval_constant_expr(ast.parse("not False", mode="eval").body) == (True, True)
        assert analyzer._eval_constant_expr(ast.parse("-5", mode="eval").body) == (True, -5)
        assert analyzer._eval_constant_expr(ast.parse("+5", mode="eval").body) == (True, 5)
        assert analyzer._eval_constant_expr(ast.parse("~5", mode="eval").body) == (False, None)
        assert analyzer._eval_constant_expr(ast.parse("1 + 2", mode="eval").body) == (True, 3)
        assert analyzer._eval_constant_expr(ast.parse("10 - 4", mode="eval").body) == (True, 6)
        assert analyzer._eval_constant_expr(ast.parse("3 * 5", mode="eval").body) == (True, 15)
        assert analyzer._eval_constant_expr(ast.parse("7 // 2", mode="eval").body) == (True, 3)
        assert analyzer._eval_constant_expr(ast.parse("7 % 3", mode="eval").body) == (True, 1)
        assert analyzer._eval_constant_expr(ast.parse("1 == 1", mode="eval").body) == (True, True)
        assert analyzer._eval_constant_expr(ast.parse("1 != 2", mode="eval").body) == (True, True)
        assert analyzer._eval_constant_expr(ast.parse("1 < 2", mode="eval").body) == (True, True)
        assert analyzer._eval_constant_expr(ast.parse("2 <= 2", mode="eval").body) == (True, True)
        assert analyzer._eval_constant_expr(ast.parse("3 > 2", mode="eval").body) == (True, True)
        assert analyzer._eval_constant_expr(ast.parse("3 >= 3", mode="eval").body) == (True, True)
        assert analyzer._eval_constant_expr(ast.parse("None is None", mode="eval").body) == (True, True)
        assert analyzer._eval_constant_expr(ast.parse("None is not None", mode="eval").body) == (True, False)

        # Constant literal cheats
        code_bool = """
def test_bools():
    assert False
    assert not True
    assert True == False
    assert True != True
    assert None is not None
    assert -1 == 1
    assert +1 == -1
    x = True
    assert not x
    y = False
    assert y == True
    z = None
    assert z is not None
"""
        findings = analyzer.analyze_source(code_bool)
        assert len(findings) == 10

        # Dynamic variable expressions (must return False, None and NOT be flagged as tautology)
        code_dynamic = """
def test_dynamic():
    dynamic_val = get_status()
    assert dynamic_val == 200
    assert dynamic_val is not None
"""
        analyzer_clean = AstTautologyAnalyzer()
        clean_findings = analyzer_clean.analyze_source(code_dynamic)
        assert len(clean_findings) == 0

    def test_external_oracle_execution(self):
        """Milestone 5 (Anti-Bias): External stateless oracle evaluates targets and captures violations."""
        # 1. Positive: Oracle passes
        res_pass = execute_external_oracle(
            oracle_cmd=f'{sys.executable} -c "import json, sys; print(json.dumps({{\\"adversarial_proof\\": \\"clean\\"}})); sys.exit(0)"',
            target_file="sample.py",
        )
        assert res_pass["status"] == "ORACLE_CERTIFIED"
        assert res_pass["passed"] is True
        assert res_pass["parsed"]["adversarial_proof"] == "clean"

        # 2. Negative: Oracle detects violation
        res_fail = execute_external_oracle(
            oracle_cmd=f'{sys.executable} -c "import sys; print(\'Counter-example found\'); sys.exit(1)"',
            target_file="sample.py",
        )
        assert res_fail["status"] == "ORACLE_VIOLATION_DETECTED"
        assert res_fail["passed"] is False
        assert "Counter-example found" in res_fail["output"]

        # 3. Placeholder replacement
        res_sub = execute_external_oracle(
            oracle_cmd=f'{sys.executable} -c "import sys; print(sys.argv[1])" {{target}}',
            target_file="target_module.py",
        )
        assert "target_module.py" in res_sub["output"]

    def test_neuro_symbolic_constraint_verification(self):
        """Milestone 6 (Neuro-Symbolic): Proves topological acyclicity and formal invariant compliance."""
        sample_file = os.path.join(_REPO_ROOT, "tools", "core", "check_env.py")
        res = verify_neuro_symbolic_constraints(target_file=sample_file)

        assert res["status"] == "NEURO_SYMBOLIC_CERTIFIED"
        assert res["passed"] is True
        assert res["has_cycle"] is False
        assert len(res["topological_order"]) > 0

        # File not found
        res_err = verify_neuro_symbolic_constraints(target_file="nonexistent_module_xyz.py")
        assert res_err["status"] == "ERROR"
        assert res_err["passed"] is False

    def test_neuro_symbolic_constraint_verification_with_formal_violation(self):
        """Milestone 5: Neuro-symbolic constraint verification rejects formal contract violations."""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write('''
def withdraw(balance: int, amount: int) -> int:
    """
    Requires: balance >= 0 and amount > 0
    Ensures: result >= 0
    """
    return balance - amount
''')
            tmp_path = f.name
        try:
            res = verify_neuro_symbolic_constraints(target_file=tmp_path)
            assert res["status"] == "CONTRACT_VIOLATION_DETECTED"
            assert res["passed"] is False
            assert "formal_contracts" in res
            assert res["formal_contracts"]["failed_count"] == 1
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_state_flushing_batch_pipeline(self):
        """Milestone 7 (Massive Distributed Systems): State-flushing DAG executes multi-target batch sequentially."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            receipt = os.path.join(tmp_dir, "batch_receipt.json")
            specs = [
                {
                    "target_id": "service_1",
                    "target_file": os.path.join("tools", "core", "check_env.py"),
                    "test_cmd": f"{sys.executable} -c \"import sys; sys.exit(0)\"",
                    "skip_mutation": True,
                },
                {
                    "target_id": "service_2",
                    "target_file": os.path.join("tools", "lint", "cli_schema_sentinel.py"),
                    "test_cmd": f"{sys.executable} -c \"import sys; sys.exit(0)\"",
                    "skip_mutation": True,
                },
            ]

            res = execute_state_flushing_batch(
                batch_specs=specs,
                repo_root=_REPO_ROOT,
                batch_receipt_path=receipt,
            )

            assert res["status"] == "BATCH_CERTIFIED"
            assert res["passed"] is True
            assert res["total_targets"] == 2
            assert res["targets_passed"] == 2
            assert res["targets_failed"] == 0
            assert os.path.exists(receipt)

            with open(receipt, "r", encoding="utf-8") as f:
                saved = json.load(f)
            assert saved["status"] == "BATCH_CERTIFIED"
            assert len(saved["steps"]) == 2

    def test_state_flushing_batch_with_contract_graph_drift_detection(self):
        """Milestone 4: Batch pipeline detects API breaking contract drift and blocks execution."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            receipt = os.path.join(tmp_dir, "batch_receipt.json")
            auth_spec = {
                "openapi": "3.0.0",
                "paths": {
                    "/api/token": {"post": {"responses": {"200": {}}}}
                }
            }
            # Breaking new spec: deletes /api/token
            broken_auth_spec = {
                "openapi": "3.0.0",
                "paths": {
                    "/api/v2/token": {"post": {"responses": {"200": {}}}}
                }
            }
            specs = [
                {
                    "target_id": "auth_service",
                    "spec_data": auth_spec,
                    "new_spec": broken_auth_spec,
                    "test_cmd": f"{sys.executable} -c \"import sys; sys.exit(0)\"",
                    "skip_mutation": True,
                },
                {
                    "target_id": "order_service",
                    "consumes": [{"service_id": "auth_service", "endpoint": "/api/token", "method": "POST"}],
                    "test_cmd": f"{sys.executable} -c \"import sys; sys.exit(0)\"",
                    "skip_mutation": True,
                },
            ]

            res = execute_state_flushing_batch(
                batch_specs=specs,
                repo_root=_REPO_ROOT,
                batch_receipt_path=receipt,
            )

            assert res["status"] == "BATCH_FAILED"
            assert res["passed"] is False
            step0 = res["steps"][0]
            assert "contract" in step0["phases"]
            assert step0["phases"]["contract"]["status"] == "CONTRACT_DRIFT_DETECTED"
            assert "order_service" in step0["phases"]["contract"]["impacted_consumers"]

    def test_state_flushing_batch_with_contract_graph_compatible(self):
        """Milestone 4: Batch pipeline passes when contract modifications are backward compatible."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            receipt = os.path.join(tmp_dir, "batch_receipt.json")
            auth_spec = {
                "openapi": "3.0.0",
                "paths": {
                    "/api/token": {"post": {"responses": {"200": {}}}}
                }
            }
            # Compatible new spec: retains /api/token and adds /api/refresh
            compatible_auth_spec = {
                "openapi": "3.0.0",
                "paths": {
                    "/api/token": {"post": {"responses": {"200": {}}}},
                    "/api/refresh": {"post": {"responses": {"200": {}}}},
                }
            }
            specs = [
                {
                    "target_id": "auth_service",
                    "spec_data": auth_spec,
                    "new_spec": compatible_auth_spec,
                    "test_cmd": f"{sys.executable} -c \"import sys; sys.exit(0)\"",
                    "skip_mutation": True,
                },
                {
                    "target_id": "order_service",
                    "consumes": [{"service_id": "auth_service", "endpoint": "/api/token", "method": "POST"}],
                    "test_cmd": f"{sys.executable} -c \"import sys; sys.exit(0)\"",
                    "skip_mutation": True,
                },
            ]

            res = execute_state_flushing_batch(
                batch_specs=specs,
                repo_root=_REPO_ROOT,
                batch_receipt_path=receipt,
            )

            assert res["status"] == "BATCH_CERTIFIED"
            assert res["passed"] is True
            step0 = res["steps"][0]
            assert "contract" in step0["phases"]
            assert step0["phases"]["contract"]["status"] == "CONTRACT_VERIFIED"

    def test_run_debate_with_external_oracle(self):
        """Milestone 8: Weapon 4 debate enriches counter-examples with external oracle findings."""
        oracle_fail_cmd = f'{sys.executable} -c "import sys; print(\'Downstream service 503 gateway timeout\'); sys.exit(1)"'
        res = run_debate(
            proposal="Implement streaming response pipeline",
            rounds=1,
            oracle_cmd=oracle_fail_cmd,
        )
        assert res["status"] == "COMPLETED"
        assert res["oracle_result"] is not None
        assert res["oracle_result"]["passed"] is False
        assert any("503 gateway timeout" in ce for ce in res["counter_examples"])

    def test_purple_phase_with_oracle_violation(self):
        """Milestone 9: Purple phase catches external adversarial oracle violations."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            receipt = os.path.join(tmp_dir, "purple_receipt.json")
            oracle_fail_cmd = f'{sys.executable} -c "import sys; print(\'Critical security leak\'); sys.exit(1)"'
            res = certify_purple_phase(
                target="uncommitted",
                target_file=os.path.join("tools", "core", "check_env.py"),
                receipt_path=receipt,
                oracle_cmd=oracle_fail_cmd,
            )
            assert res["status"] == "PURPLE_AUDIT_WARNINGS"
            assert res["passed"] is False
            assert any("Critical security leak" in f.get("message", "") for f in res["findings"])

    def test_neuro_symbolic_polyglot_ts(self):
        """Milestone 10: Neuro-symbolic constraint solver verifies TypeScript/JavaScript imports."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            ts_file = os.path.join(tmp_dir, "userService.ts")
            with open(ts_file, "w", encoding="utf-8") as f:
                f.write("import { db } from './database';\nimport { logger } from './logger';\nexport class UserService {}\n")
            res = verify_neuro_symbolic_constraints(target_file=ts_file)
            assert res["status"] == "NEURO_SYMBOLIC_CERTIFIED"
            assert res["passed"] is True
            assert res["has_cycle"] is False
            assert res["edges_evaluated"] == 2

    def test_neuro_symbolic_detects_two_node_cycle(self):
        """M1 Positive: Detects direct 2-node circular dependency (a.py -> b.py -> a.py)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            a_py = os.path.join(tmp_dir, "a.py")
            b_py = os.path.join(tmp_dir, "b.py")
            with open(a_py, "w", encoding="utf-8") as f:
                f.write("import b\n\ndef run_a():\n    return b.run_b()\n")
            with open(b_py, "w", encoding="utf-8") as f:
                f.write("import a\n\ndef run_b():\n    return a.run_a()\n")

            res = verify_neuro_symbolic_constraints(target_file="a.py", repo_root=tmp_dir)
            assert res["status"] == "CYCLE_DETECTED"
            assert res["passed"] is False
            assert res["has_cycle"] is True
            assert len(res["cycles_found"]) >= 1
            assert res["edges_evaluated"] >= 2

    def test_neuro_symbolic_detects_three_node_transitive_cycle(self):
        """M1 Positive: Detects 3-node transitive circular dependency (a -> b -> c -> a)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "a.py"), "w", encoding="utf-8") as f:
                f.write("from b import step_b\n")
            with open(os.path.join(tmp_dir, "b.py"), "w", encoding="utf-8") as f:
                f.write("import c\n")
            with open(os.path.join(tmp_dir, "c.py"), "w", encoding="utf-8") as f:
                f.write("from a import step_a\n")

            res = verify_neuro_symbolic_constraints(target_file="a.py", repo_root=tmp_dir)
            assert res["status"] == "CYCLE_DETECTED"
            assert res["passed"] is False
            assert res["has_cycle"] is True
            assert len(res["cycles_found"]) >= 1
            assert res["edges_evaluated"] >= 3

    def test_neuro_symbolic_acyclic_multi_file_passes(self):
        """M1 Negative/Boundary: Acyclic multi-file import chain (a.py -> b.py) certifies cleanly."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "a.py"), "w", encoding="utf-8") as f:
                f.write("import b\n\ndef main():\n    return b.VALUE\n")
            with open(os.path.join(tmp_dir, "b.py"), "w", encoding="utf-8") as f:
                f.write("VALUE = 42\n")

            res = verify_neuro_symbolic_constraints(target_file="a.py", repo_root=tmp_dir)
            assert res["status"] == "NEURO_SYMBOLIC_CERTIFIED"
            assert res["passed"] is True
            assert res["has_cycle"] is False
            assert res["cycles_found"] == []
            assert res["edges_evaluated"] == 1
            assert res["topological_order"] == ["a", "b"]

    def test_neuro_symbolic_detects_ts_transitive_cycle(self):
        """M1 Polyglot: Detects circular dependency across local TypeScript/JS modules (ESM & CommonJS)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "alpha.ts"), "w", encoding="utf-8") as f:
                f.write("import { beta } from './beta';\nexport const alpha = 1;\n")
            with open(os.path.join(tmp_dir, "beta.ts"), "w", encoding="utf-8") as f:
                f.write("const alpha = require('./alpha');\nexport const beta = 2;\n")

            res = verify_neuro_symbolic_constraints(target_file="alpha.ts", repo_root=tmp_dir)
            assert res["status"] == "CYCLE_DETECTED"
            assert res["passed"] is False
            assert res["has_cycle"] is True
            assert res["edges_evaluated"] == 2

    def test_neuro_symbolic_relative_and_submodule_imports(self):
        """M1 Mutant Killer: Verifies package submodule imports, relative imports, and star-import exclusion."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            pkg_dir = os.path.join(tmp_dir, "pkg")
            os.makedirs(pkg_dir)
            with open(os.path.join(pkg_dir, "mod_a.py"), "w", encoding="utf-8") as f:
                f.write("from pkg import mod_b\nfrom .mod_c import *\n")
            with open(os.path.join(pkg_dir, "mod_b.py"), "w", encoding="utf-8") as f:
                f.write("from . import mod_a\n")
            with open(os.path.join(pkg_dir, "mod_c.py"), "w", encoding="utf-8") as f:
                f.write("from . import *\n")

            res = verify_neuro_symbolic_constraints(target_file="pkg/mod_a.py", repo_root=tmp_dir)
            assert res["status"] == "CYCLE_DETECTED"
            assert res["passed"] is False
            assert res["has_cycle"] is True
            assert res["edges_evaluated"] == 4

            # Also verify parent-relative import (level == 2) and non-relative import from subdir
            sub_dir = os.path.join(pkg_dir, "sub")
            os.makedirs(sub_dir)
            with open(os.path.join(tmp_dir, "root_helper.py"), "w", encoding="utf-8") as f:
                f.write("from pkg.sub import leaf\n")
            with open(os.path.join(sub_dir, "leaf.py"), "w", encoding="utf-8") as f:
                f.write("import root_helper\n")

            res_sub = verify_neuro_symbolic_constraints(target_file="pkg/sub/leaf.py", repo_root=tmp_dir)
            assert res_sub["status"] == "CYCLE_DETECTED"
            assert res_sub["passed"] is False
            assert res_sub["has_cycle"] is True

            # Verify Groovy/Java dotted import extraction
            java_file = os.path.join(tmp_dir, "ServiceA.java")
            with open(java_file, "w", encoding="utf-8") as f:
                f.write("import com.example.RepoB;\npublic class ServiceA {}\n")
            res_java = verify_neuro_symbolic_constraints(target_file="ServiceA.java", repo_root=tmp_dir)
            assert res_java["status"] == "NEURO_SYMBOLIC_CERTIFIED"
            assert res_java["passed"] is True
            assert res_java["edges_evaluated"] == 1
            assert "RepoB" in res_java["topological_order"]

    def test_neuro_symbolic_call_graph_fallback_and_stdlib_guard(self):
        """M1 Mutant Killer: Exercises call_graph_indexer cross-directory lookup, relative scope, and stdlib guard."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir1 = os.path.join(tmp_dir, "svc_one")
            dir2 = os.path.join(tmp_dir, "svc_two")
            os.makedirs(dir1)
            os.makedirs(dir2)
            # Cross-directory bare imports resolved via call_graph_indexer (len(stem) > 2)
            with open(os.path.join(dir1, "alpha_mod.py"), "w", encoding="utf-8") as f:
                f.write("import beta_mod\n")
            with open(os.path.join(dir2, "beta_mod.py"), "w", encoding="utf-8") as f:
                f.write("import alpha_mod\n")

            res_cg = verify_neuro_symbolic_constraints(target_file="svc_one/alpha_mod.py", repo_root=tmp_dir)
            assert res_cg["status"] == "CYCLE_DETECTED"
            assert res_cg["passed"] is False
            assert res_cg["has_cycle"] is True

            # Relative import (level == 1) must NOT search repo root
            with open(os.path.join(tmp_dir, "root_only.py"), "w", encoding="utf-8") as f:
                f.write("import svc_one.rel_caller\n")
            with open(os.path.join(dir1, "rel_caller.py"), "w", encoding="utf-8") as f:
                f.write("from . import root_only\n")

            res_rel = verify_neuro_symbolic_constraints(target_file="svc_one/rel_caller.py", repo_root=tmp_dir)
            assert res_rel["status"] == "NEURO_SYMBOLIC_CERTIFIED"
            assert res_rel["passed"] is True
            assert res_rel["has_cycle"] is False

            # Stdlib guard: `import json` must NOT resolve to unrelated `svc_two/json.py` via call_graph_map
            with open(os.path.join(dir1, "stdlib_user.py"), "w", encoding="utf-8") as f:
                f.write("import json\n")
            with open(os.path.join(dir2, "json.py"), "w", encoding="utf-8") as f:
                f.write("import stdlib_user\n")

            res_std = verify_neuro_symbolic_constraints(target_file="svc_one/stdlib_user.py", repo_root=tmp_dir)
            assert res_std["status"] == "NEURO_SYMBOLIC_CERTIFIED"
            assert res_std["passed"] is True
            assert res_std["has_cycle"] is False

    def test_calculate_composite_fitness_bounded(self):
        """Milestone 1 Anti-Goodhart: Fitness score is strictly bounded in [0.0, 100.0] with exact arithmetic."""
        # Standard valid case with default green_passed=True
        score_default_arg = calculate_composite_fitness_score(mutation_score=100.0, net_lines=1)
        assert score_default_arg == 100.0

        # Exact arithmetic check: mutation 80.0, net_lines 21
        # loc_eff = 100 * (50 / 70) = 71.42857...
        # score = 80 * 0.8 + 71.42857 * 0.2 = 64.0 + 14.2857 = 78.29
        score_exact = calculate_composite_fitness_score(mutation_score=80.0, net_lines=21)
        assert score_exact == 78.29

        # Exact arithmetic check: net_lines 1 (loc_eff = 100.0)
        # score = 80 * 0.8 + 100 * 0.2 = 64.0 + 20.0 = 84.0
        score_1_line = calculate_composite_fitness_score(mutation_score=80.0, net_lines=1, green_passed=True)
        assert score_1_line == 84.0

        # Boundary: 0 lines (treated as <= 1 line -> loc_eff = 100.0)
        score_0_line = calculate_composite_fitness_score(mutation_score=80.0, net_lines=0, green_passed=True)
        assert score_0_line == 84.0

        # Boundary: 10,000 lines (extreme bloat: loc_eff ~= 0.50)
        # score = 100 * 0.8 + 0.50 * 0.2 = 80.1
        score_huge = calculate_composite_fitness_score(mutation_score=100.0, net_lines=10000, green_passed=True)
        assert 80.0 <= score_huge <= 81.0

        # Boundary: green_passed=False must strictly return 0.0
        score_red = calculate_composite_fitness_score(mutation_score=100.0, net_lines=1, green_passed=False)
        assert score_red == 0.0

    def test_tournament_arbiter_anti_goodhart_bound(self):
        """Milestone 1 Anti-Goodhart: 95% mutation (25 LOC) beats 80% mutation 1-line hack."""
        score_clean_25loc = calculate_composite_fitness_score(mutation_score=95.0, net_lines=25, green_passed=True)
        score_golf_1loc = calculate_composite_fitness_score(mutation_score=80.0, net_lines=1, green_passed=True)

        # Under the old broken formula (100/LOC * 0.3), 1 LOC got +30 pts beating 25 LOC (+1.2 pts).
        # Under Anti-Goodhart formula, superior mutation kill rate must win over code golf.
        assert score_clean_25loc > score_golf_1loc
        assert score_clean_25loc == 89.51
        assert score_golf_1loc == 84.00

        cand_clean = {
            "candidate_id": "cand_clean_25loc",
            "green_passed": True,
            "mutation_score": 95.0,
            "net_lines_changed": 25,
            "composite_fitness_score": score_clean_25loc,
        }
        cand_golf = {
            "candidate_id": "cand_golf_1loc",
            "green_passed": True,
            "mutation_score": 80.0,
            "net_lines_changed": 1,
            "composite_fitness_score": score_golf_1loc,
        }
        winner = select_tournament_winner([cand_golf, cand_clean])
        assert winner is not None
        assert winner["candidate_id"] == "cand_clean_25loc"

        # Verify dynamic score calculation when composite_fitness_score is omitted or None
        cand_no_score = {
            "candidate_id": "cand_dynamic_score",
            "green_passed": True,
            "mutation_score": 90.0,
            "net_lines_changed": 10,
        }
        cand_none_score = {
            "candidate_id": "cand_explicit_none",
            "green_passed": True,
            "mutation_score": 85.0,
            "net_lines_changed": 5,
            "composite_fitness_score": None,
        }
        winner_dynamic = select_tournament_winner([cand_none_score, cand_no_score])
        assert winner_dynamic is not None
        # cand_no_score: score = 90 * 0.8 + (100 * 50 / 59) * 0.2 = 88.95
        # cand_none_score: score = 85 * 0.8 + (100 * 50 / 54) * 0.2 = 68.0 + 18.52 = 86.52
        assert cand_none_score["composite_fitness_score"] == 86.52
        assert winner_dynamic["composite_fitness_score"] == 88.95

    def test_pareto_dominance_ranking(self):
        """Milestone 1 Pareto Dominance: Dominating candidate is prioritized on the Pareto front."""
        candidates = [
            {
                "candidate_id": "c1_dominant",
                "green_passed": True,
                "mutation_score": 90.0,
                "net_lines_changed": 10,
            },
            {
                "candidate_id": "c2_dominated_by_c1",
                "green_passed": True,
                "mutation_score": 90.0,
                "net_lines_changed": 25,
            },
            {
                "candidate_id": "c3_strictly_worse",
                "green_passed": True,
                "mutation_score": 70.0,
                "net_lines_changed": 30,
            },
        ]
        ranked = compute_pareto_front(candidates)
        c1 = next(c for c in ranked if c["candidate_id"] == "c1_dominant")
        c2 = next(c for c in ranked if c["candidate_id"] == "c2_dominated_by_c1")
        c3 = next(c for c in ranked if c["candidate_id"] == "c3_strictly_worse")

        assert c1["pareto_front"] is True
        assert c1["pareto_rank"] == 1
        assert c2["pareto_front"] is False
        assert c2["pareto_rank"] == 2
        assert c3["pareto_front"] is False
        assert c3["pareto_rank"] == 3

        # Incomparable trade-off pair: X has higher mutation, Y has fewer lines.
        # Neither dominates the other -> BOTH must be on Pareto front (Rank 1).
        tradeoff_cands = [
            {"candidate_id": "tx_high_mut", "mutation_score": 100.0, "net_lines_changed": 50},
            {"candidate_id": "ty_lean_loc", "mutation_score": 80.0, "net_lines_changed": 10},
        ]
        to_ranked = compute_pareto_front(tradeoff_cands)
        tx = next(c for c in to_ranked if c["candidate_id"] == "tx_high_mut")
        ty = next(c for c in to_ranked if c["candidate_id"] == "ty_lean_loc")
        assert tx["pareto_front"] is True
        assert tx["pareto_rank"] == 1
        assert ty["pareto_front"] is True
        assert ty["pareto_rank"] == 1

        # Strict mutation dominance with equal LOC:
        # Same LOC (10 == 10), but strictly higher mutation (95.0 > 90.0) -> high dominates low
        eq_loc_cands = [
            {"candidate_id": "eq_high", "mutation_score": 95.0, "net_lines_changed": 10},
            {"candidate_id": "eq_low", "mutation_score": 90.0, "net_lines_changed": 10},
        ]
        eq_ranked = compute_pareto_front(eq_loc_cands)
        assert eq_ranked[0]["candidate_id"] == "eq_high"
        assert eq_ranked[0]["pareto_front"] is True
        assert eq_ranked[0]["pareto_rank"] == 1
        assert eq_ranked[1]["candidate_id"] == "eq_low"
        assert eq_ranked[1]["pareto_front"] is False
        assert eq_ranked[1]["pareto_rank"] == 2

        # Test duplicate candidates fallback branch at rank > 1:
        # c0 dominates dup1 and dup2 -> dup1 and dup2 fall to rank 2.
        # When current_rank == 2, their pareto_front MUST be False.
        dup_candidates = [
            {"candidate_id": "c0_master", "mutation_score": 99.0, "net_lines_changed": 5},
            {"candidate_id": "dup1", "mutation_score": 80.0, "net_lines_changed": 15},
            {"candidate_id": "dup2", "mutation_score": 80.0, "net_lines_changed": 15},
        ]
        dup_ranked = compute_pareto_front(dup_candidates)
        c0 = next(c for c in dup_ranked if c["candidate_id"] == "c0_master")
        d1 = next(c for c in dup_ranked if c["candidate_id"] == "dup1")
        d2 = next(c for c in dup_ranked if c["candidate_id"] == "dup2")
        assert c0["pareto_front"] is True
        assert c0["pareto_rank"] == 1
        assert d1["pareto_front"] is False
        assert d1["pareto_rank"] == 2
        assert d2["pareto_front"] is False
        assert d2["pareto_rank"] == 2

    def test_compute_test_files_snapshot(self):
        """Milestone 2: Cryptographic snapshot generates deterministic tree hash and catches alterations."""
        # Test defaults with working_dir=None
        empty_res1 = extract_test_files_from_cmd("")
        empty_res2 = extract_test_files_from_cmd("   ")
        assert empty_res1 == []
        assert empty_res2 == []

        # Test default root resolution (working_dir=None)
        default_files = extract_test_files_from_cmd("pytest tests/test_solo_runner.py")
        assert len(default_files) == 1
        default_snap = compute_test_files_snapshot("pytest tests/test_solo_runner.py")
        assert default_snap["total_files"] == 1
        assert default_snap["tree_hash"] != ""

        with tempfile.TemporaryDirectory() as td:
            f1 = os.path.join(td, "test_alpha.py")
            f2 = os.path.join(td, "spec_beta.py")  # File without 'test' in name but ending in .py
            with open(f1, "w", encoding="utf-8") as f:
                f.write("def test_one(): assert 1 == 1\n")
            with open(f2, "w", encoding="utf-8") as f:
                f.write("def test_two(): assert 2 == 2\n")

            cmd = f'pytest "{f1}" "{f2}"'
            # Must extract spec_beta.py even without 'test' in its filename
            extracted = extract_test_files_from_cmd(test_cmd=cmd, working_dir=td)
            assert len(extracted) == 2

            snap1 = compute_test_files_snapshot(test_cmd=cmd, working_dir=td)
            assert snap1["total_files"] == 2
            assert snap1["tree_hash"] != ""
            assert set(snap1["files"].keys()) == {"test_alpha.py", "spec_beta.py"}

            # Modify f1 slightly -> tree hash must change
            with open(f1, "w", encoding="utf-8") as f:
                f.write("def test_one(): assert 1 == 1  # modified\n")
            snap2 = compute_test_files_snapshot(test_cmd=cmd, working_dir=td)
            assert snap2["tree_hash"] != snap1["tree_hash"]

    def test_read_only_test_guard_physical_block(self):
        """Milestone 2: ReadOnlyTestGuard enforces OS-level read-only permissions on test files."""
        # Test default repo_root=None for guard and unlock
        guard_default = ReadOnlyTestGuard(["tests/test_solo_runner.py"])
        assert guard_default.root == _REPO_ROOT

        with tempfile.TemporaryDirectory() as td:
            t_file = os.path.join(td, "test_immutable.py")
            with open(t_file, "w", encoding="utf-8") as f:
                f.write("def test_core(): assert True\n")

            # Guard context enforces read-only (0o444)
            guard = ReadOnlyTestGuard([t_file], repo_root=td)
            with guard:
                assert len(guard._orig_modes) == 1
                with pytest.raises(PermissionError):
                    with open(t_file, "w", encoding="utf-8") as f:
                        f.write("def test_core(): assert False\n")

            # Upon exit, write permissions are restored and _orig_modes is strictly cleared
            assert len(guard._orig_modes) == 0
            with open(t_file, "a", encoding="utf-8") as f:
                f.write("# unlocked successfully\n")
            assert os.path.exists(t_file)

            # Test standalone lock and unlock functions with relative path and repo_root=td
            locked = lock_test_files(["test_immutable.py"], repo_root=td)
            assert len(locked) == 1
            with pytest.raises(PermissionError):
                with open(t_file, "w", encoding="utf-8") as f:
                    f.write("tamper attempt\n")

            unlocked = unlock_test_files(["test_immutable.py"], repo_root=td)
            assert len(unlocked) == 1
            with open(t_file, "w", encoding="utf-8") as f:
                f.write("def test_ok(): pass\n")

            # Test unlock_test_files with default repo_root=None
            unlocked_default = unlock_test_files([t_file])
            assert len(unlocked_default) == 1

    def test_green_phase_rejects_tampered_tests(self):
        """Milestone 2: certify_green_phase mechanically rejects test tampering by Blue Team."""
        with tempfile.TemporaryDirectory() as td:
            receipt = os.path.join(td, "red_receipt.json")
            m_file = os.path.join(td, "service.py")
            t_file = os.path.join(td, "test_tamper.py")
            c_file = os.path.join(td, "test_clean.py")

            with open(m_file, "w", encoding="utf-8") as f:
                f.write("def compute_val(): return 0\n")

            with open(t_file, "w", encoding="utf-8") as f:
                f.write(
                    "from service import compute_val\n"
                    "def test_failing():\n"
                    "    assert compute_val() == 42, 'Expected domain value 42'\n"
                )

            with open(c_file, "w", encoding="utf-8") as f:
                f.write("from service import compute_val\ndef test_clean_always(): assert compute_val() == 99\n")

            test_cmd = f'{sys.executable} -m pytest "{t_file}" "{c_file}"'
            red_res = certify_red_phase(test_cmd=test_cmd, receipt_path=receipt, cwd=td)
            assert red_res["status"] == "CERTIFIED_RED"
            assert red_res["passed"] is True
            assert "test_tree_hash" in red_res
            assert red_res["test_tree_hash"] != ""

            # Blue Phase Tampering: Blue team modifies ONLY test_tamper.py (test_clean.py is UNTOUCHED)
            with open(t_file, "w", encoding="utf-8") as f:
                f.write(
                    "from service import compute_val\n"
                    "def test_failing():\n"
                    "    # Blue team relaxed assertion to manufactured pass\n"
                    "    assert compute_val() == 0\n"
                )

            green_res = certify_green_phase(test_cmd=test_cmd, receipt_path=receipt, cwd=td)
            assert green_res["status"] == "TEST_TAMPERING_DETECTED"
            assert green_res["passed"] is False
            assert "Tampering Violation" in green_res["error"]
            # Specifically verifies ONLY test_tamper.py is flagged, and untouched test_clean.py is NOT falsely flagged
            assert "test_tamper.py" in green_res["tampered_files"]
            assert "test_clean.py" not in green_res["tampered_files"]

            # Tampering Scenario 2: Blue team completely DELETES the test file
            os.remove(t_file)
            del_green_res = certify_green_phase(test_cmd=test_cmd, receipt_path=receipt, cwd=td)
            assert del_green_res["status"] == "TEST_TAMPERING_DETECTED"
            assert any("test_tamper.py" in tf for tf in del_green_res["tampered_files"])

    def test_green_phase_accepts_untampered_tests(self):
        """Milestone 2: certify_green_phase succeeds when implementation is fixed and tests remain untouched."""
        with tempfile.TemporaryDirectory() as td:
            receipt = os.path.join(td, "red_receipt.json")
            target_mod = os.path.join(td, "calc.py")
            t_file = os.path.join(td, "test_calc.py")

            # Source module with bug
            with open(target_mod, "w", encoding="utf-8") as f:
                f.write("def add(a, b): return a - b  # Bug\n")

            # Authoritative Red test
            with open(t_file, "w", encoding="utf-8") as f:
                f.write("from calc import add\ndef test_add(): assert add(2, 3) == 5\n")

            test_cmd = f'{sys.executable} -m pytest "{t_file}"'
            red_res = certify_red_phase(test_cmd=test_cmd, receipt_path=receipt, cwd=td)
            assert red_res["status"] == "CERTIFIED_RED"

            # Blue team fixes implementation without touching the test
            with open(target_mod, "w", encoding="utf-8") as f:
                f.write("def add(a, b): return a + b  # Fixed\n")

            green_res = certify_green_phase(test_cmd=test_cmd, receipt_path=receipt, cwd=td)
            assert green_res["status"] == "CERTIFIED_GREEN"
            assert green_res["passed"] is True

    def test_run_debate_semantic_entropy_evaluation(self, monkeypatch):
        """Milestone 4 (P2): run_debate evaluates semantic consistency via SemanticEntropyEngine and degrades gracefully."""
        from tools.reasoning.semantic_entropy import SemanticEntropyEngine

        captured_calls = []
        orig_eval = SemanticEntropyEngine.evaluate_hypotheses

        def spy_evaluate(self, hypotheses, threshold=0.50, query_context=None):
            captured_calls.append((list(hypotheses), query_context))
            return orig_eval(self, hypotheses, threshold=threshold, query_context=query_context)

        monkeypatch.setattr(SemanticEntropyEngine, "evaluate_hypotheses", spy_evaluate)

        # 1. Positive: real 2-round debate invokes SemanticEntropyEngine on debate arguments
        res = run_debate(proposal="Implement idempotent JWT refresh flow", rounds=2)
        assert res["status"] == "COMPLETED"
        assert len(captured_calls) == 1
        hyps, q_ctx = captured_calls[0]
        assert len(hyps) >= 4
        assert all(isinstance(h, str) and len(h.strip()) > 0 for h in hyps)
        assert q_ctx == "Implement idempotent JWT refresh flow"

        assert "semantic_entropy" in res
        assert isinstance(res["semantic_entropy"], float)
        assert 0.0 < res["semantic_entropy"] <= 1.0
        assert "uncertainty_status" in res
        assert isinstance(res["uncertainty_status"], str)
        assert res["uncertainty_status"] in ("CONFIDENT_LOW_ENTROPY", "HIGH_ENTROPY_CONFABULATION_RISK")

        # 2. Negative / Graceful Degradation: SemanticEntropyEngine failure does not crash run_debate
        def failing_evaluate(self, hypotheses, threshold=0.50, query_context=None):
            raise RuntimeError("Simulated semantic entropy engine failure")

        monkeypatch.setattr(SemanticEntropyEngine, "evaluate_hypotheses", failing_evaluate)
        res_degraded = run_debate(proposal="Implement idempotent JWT refresh flow", rounds=1)
        assert res_degraded["status"] == "COMPLETED"
        assert isinstance(res_degraded["semantic_entropy"], float)
        assert res_degraded["semantic_entropy"] == 0.0
        assert isinstance(res_degraded["uncertainty_status"], str)
        assert len(res_degraded["uncertainty_status"]) > 0
        assert res_degraded["uncertainty_status"] == "UNAVAILABLE"

    def test_execute_external_oracle_constrained_decoding(self, monkeypatch):
        """Milestone 4 (P2): execute_external_oracle fast-paths valid JSON, repairs LLM JSON via ConstrainedDecoder, and handles plain text."""
        from tools.reasoning.constrained_decoding import ConstrainedDecoder

        with tempfile.TemporaryDirectory() as td:
            valid_script = os.path.join(td, "oracle_valid.py")
            with open(valid_script, "w", encoding="utf-8") as f:
                f.write('import json, sys\nprint(json.dumps({"ok": True, "issues": []}))\nsys.exit(0)\n')

            malformed_script = os.path.join(td, "oracle_malformed.py")
            with open(malformed_script, "w", encoding="utf-8") as f:
                f.write(
                    "import sys\n"
                    "print(\"<thought>checking...</thought>\\n```json\\n{'ok': True, 'issues': ['timeout'],}\\n```\")\n"
                    "sys.exit(0)\n"
                )

            plain_script = os.path.join(td, "oracle_plain.py")
            with open(plain_script, "w", encoding="utf-8") as f:
                f.write('import sys\nprint("ORACLE PASS: no issues")\nsys.exit(0)\n')

            empty_script = os.path.join(td, "oracle_empty.py")
            with open(empty_script, "w", encoding="utf-8") as f:
                f.write("import sys\nsys.exit(0)\n")

            decoder_calls = []
            orig_project = ConstrainedDecoder.project_json

            def spy_project(self, thought_text, schema=None):
                decoder_calls.append(thought_text)
                return orig_project(self, thought_text, schema=schema)

            monkeypatch.setattr(ConstrainedDecoder, "project_json", spy_project)

            # 1. Positive (Fast-path valid JSON): json.loads succeeds without invoking ConstrainedDecoder
            res_valid = execute_external_oracle(
                oracle_cmd=f'{sys.executable} "{valid_script}"',
                target_file="sample.py",
                cwd=td,
            )
            assert res_valid["status"] == "ORACLE_CERTIFIED"
            assert res_valid["passed"] is True
            assert res_valid["parsed"] == {"ok": True, "issues": []}
            assert res_valid["oracle_json_repaired"] is False
            assert len(decoder_calls) == 0

            # 2. Positive (Wrapped/malformed LLM JSON): repaired via ConstrainedDecoder().project_json()
            res_repaired = execute_external_oracle(
                oracle_cmd=f'{sys.executable} "{malformed_script}"',
                target_file="sample.py",
                cwd=td,
            )
            assert res_repaired["status"] == "ORACLE_CERTIFIED"
            assert res_repaired["passed"] is True
            assert res_repaired["parsed"] == {"ok": True, "issues": ["timeout"]}
            assert res_repaired["oracle_json_repaired"] is True
            assert len(decoder_calls) == 1

            # 3. Boundary / Negative (Plain text): parsed is None, oracle_json_repaired is False without crashing
            res_plain = execute_external_oracle(
                oracle_cmd=f'{sys.executable} "{plain_script}"',
                target_file="sample.py",
                cwd=td,
            )
            assert res_plain["status"] == "ORACLE_CERTIFIED"
            assert res_plain["passed"] is True
            assert res_plain["parsed"] is None
            assert res_plain["oracle_json_repaired"] is False

            # 4. Boundary (Empty stdout): parsed is None, oracle_json_repaired is False without crashing
            res_empty = execute_external_oracle(
                oracle_cmd=f'{sys.executable} "{empty_script}"',
                target_file="sample.py",
                cwd=td,
            )
            assert res_empty["status"] == "ORACLE_CERTIFIED"
            assert res_empty["passed"] is True
            assert res_empty["parsed"] is None
            assert res_empty["oracle_json_repaired"] is False




