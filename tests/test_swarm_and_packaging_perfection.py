#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Regression Test Suite: Swarm Hardening & Enterprise Packaging Integrity
Asserts fail-closed Red/Green/Purple certifications, anti-replay, ratchet gates, and leak prevention.
"""

import json
import os
import time
from datetime import datetime, timezone
import pytest

from tools.orchestration.solo_swarm_runner import (
    certify_red_phase,
    certify_green_phase,
    certify_purple_phase,
    classify_test_failure,
)
from tools.core.package_release import (
    verify_archive_integrity,
    create_zip_archive,
    MANDATORY_DOT_DIRS,
)


@pytest.fixture
def temp_receipt_path(tmp_path):
    return str(tmp_path / "test_receipt.json")


class TestRedPhaseHardening:
    """Verifies fail-closed semantics for Red Certification."""

    def test_classify_assertion_failure(self):
        output = "FAILED tests/test_demo.py::test_fail - AssertionError: Expected 10 but got 20"
        cat, is_sem, _ = classify_test_failure(1, output)
        assert cat == "ASSERTION_FAILURE"
        assert is_sem is True

    def test_classify_syntax_error(self):
        output = "SyntaxError: invalid syntax in test file"
        cat, is_sem, _ = classify_test_failure(2, output)
        assert cat == "SYNTAX_ERROR"
        assert is_sem is False

    def test_classify_timeout(self):
        output = "Command timed out after 30 seconds"
        cat, is_sem, _ = classify_test_failure(124, output)
        assert cat == "TIMEOUT"
        assert is_sem is False

    def test_classify_missing_command(self):
        output = "/bin/sh: non_existent_cmd: command not found"
        cat, is_sem, _ = classify_test_failure(127, output)
        assert cat == "COMMAND_NOT_FOUND"
        assert is_sem is False

    def test_certify_red_rejects_missing_command(self, temp_receipt_path):
        res = certify_red_phase(
            test_cmd="non_existent_binary_xyz_12345",
            receipt_path=temp_receipt_path,
        )
        assert res["passed"] is False
        assert "REJECTED" in res["status"]


class TestGreenPhaseAntiReplay:
    """Verifies anti-replay, TTL expiry, and command binding in Green certification."""

    def test_green_rejects_missing_red_receipt(self, tmp_path):
        non_existent = str(tmp_path / "absent_receipt.json")
        res = certify_green_phase(
            test_cmd="python3 -c 'exit(0)'",
            receipt_path=non_existent,
        )
        assert res["passed"] is False
        assert res["status"] == "MISSING_RED_RECEIPT"

    def test_green_rejects_expired_red_receipt(self, temp_receipt_path):
        # Create an expired receipt (16 minutes old)
        old_time = time.time() - 960  # 16 min ago
        receipt_data = {
            "status": "CERTIFIED_RED",
            "certified_at": datetime.fromtimestamp(old_time, tz=timezone.utc).isoformat(),
            "timestamp": old_time,
            "test_cmd": "python3 -c 'exit(0)'",
            "git_commit": "dummy_sha",
            "test_tree_hash": "",
        }
        with open(temp_receipt_path, "w", encoding="utf-8") as f:
            json.dump(receipt_data, f)

        res = certify_green_phase(
            test_cmd="python3 -c 'exit(0)'",
            receipt_path=temp_receipt_path,
        )
        assert res["passed"] is False
        assert res["status"] == "EXPIRED_RED_RECEIPT"

    def test_green_rejects_command_mismatch(self, temp_receipt_path):
        receipt_data = {
            "status": "CERTIFIED_RED",
            "certified_at": datetime.now(timezone.utc).isoformat(),
            "timestamp": time.time(),
            "test_cmd": "pytest tests/test_target.py -k test_feature",
            "git_commit": "dummy_sha",
            "test_tree_hash": "",
        }
        with open(temp_receipt_path, "w", encoding="utf-8") as f:
            json.dump(receipt_data, f)

        res = certify_green_phase(
            test_cmd="pytest tests/test_other.py",
            receipt_path=temp_receipt_path,
        )
        assert res["passed"] is False
        assert res["status"] == "COMMAND_MISMATCH_REJECTED"


class TestPurpleAuditorHardening:
    """Verifies Purple Auditor security checks, swallowed exception catching, and blast radius."""

    def test_purple_fails_on_empty_scope_without_target(self, tmp_path):
        fake_receipt = str(tmp_path / "purple_receipt.json")
        res = certify_purple_phase(
            target="uncommitted",
            target_file="",
            receipt_path=fake_receipt,
            check_neuro_symbolic=False,
        )
        # If no uncommitted files exist or empty scope
        if res.get("files_analyzed", 0) == 0:
            assert res["passed"] is False
            assert res["status"] == "PURPLE_AUDIT_WARNINGS"

    def test_purple_downstream_blast_radius(self, tmp_path):
        fake_receipt = str(tmp_path / "purple_receipt.json")
        res = certify_purple_phase(
            target="uncommitted",
            target_file="tools/orchestration/solo_swarm_runner.py",
            receipt_path=fake_receipt,
            check_neuro_symbolic=False,
        )
        impact = res.get("downstream_impact")
        assert impact is not None
        assert "fan_in" in impact
        assert isinstance(impact["fan_in"], int)
        assert "dependents" in impact
        assert isinstance(impact["dependents"], list)


class TestPackagingAndLeakPrevention:
    """Verifies release package filtering, dot-directory preservation, and forbidden leak prevention."""

    def test_mandatory_dot_dirs_include_agent_and_agents(self):
        assert ".agent" in MANDATORY_DOT_DIRS
        assert ".agents" in MANDATORY_DOT_DIRS
        assert ".github" in MANDATORY_DOT_DIRS

    def test_forbidden_file_leak_detection(self, tmp_path):
        fake_archive = str(tmp_path / "leaky_release.zip")
        files = [
            (str(tmp_path / "dummy.txt"), "dummy.txt"),
            (str(tmp_path / "secret.env"), ".env"),
        ]
        # Create dummy source files
        with open(tmp_path / "dummy.txt", "w") as f:
            f.write("safe content")
        with open(tmp_path / "secret.env", "w") as f:
            f.write("SECRET_KEY=12345")

        create_zip_archive(files, fake_archive)
        is_valid, errors = verify_archive_integrity(fake_archive)
        assert is_valid is False
        assert any("leak detected" in err.lower() for err in errors)


class TestQualityGateRatchetSentinel:
    """Verifies that disabling quality gates in Hub mode violates Invariant 11 and fails DoD."""

    def test_skipped_gate_fails_hub_mode(self, tmp_path):
        from tools.core.verify_all import run_all_gates
        # Create a config file that disables gate 8
        bad_config = tmp_path / "bad_synapse.config.json"
        config_data = {
            "quality_gates": {
                "gates": {
                    "gate_8_micro_mutator": False
                }
            }
        }
        with open(bad_config, "w", encoding="utf-8") as f:
            json.dump(config_data, f)

        res_code = run_all_gates(
            repo_root=os.getcwd(),
            mode="hub",
            config_path=str(bad_config),
            output_format="json",
            fast=True,
        )
        assert res_code == 1, "Disabling a required quality gate in Hub mode must exit code 1"

