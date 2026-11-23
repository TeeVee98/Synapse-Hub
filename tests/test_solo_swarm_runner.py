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

from tools.orchestration.solo_swarm_runner import (
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
        from tools.orchestration.solo_swarm_runner import AstTautologyAnalyzer
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
                target_file="standards/qa-process/solo-swarm-protocol.md",
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
            "tests/test_solo_swarm_runner.py",
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



