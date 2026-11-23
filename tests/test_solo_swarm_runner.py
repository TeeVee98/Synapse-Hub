#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

import os
import sys
import json
import tempfile

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
                    "def test_calc():\n"
                    "    actual = 404\n"
                    "    expected = 200\n"
                    "    assert actual == expected\n"
                )
            cmd = f"{sys.executable} -m pytest \"{test_file}\""
            res = certify_red_phase(test_cmd=cmd, receipt_path=receipt)
            assert res["status"] == "CERTIFIED_RED"
            assert res["passed"] is True
            assert os.path.exists(receipt)

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
