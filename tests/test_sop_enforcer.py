# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""Unit tests for Declarative SOP execution in FsmEnforcer (tests/test_sop_enforcer.py).

Verifies SOP session initialization, transition rules, required evidence validation,
unauthorized actor rejection, and compliance verification.

Author: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
License: MIT
"""

import os
import tempfile
import pytest

from tools.core.fsm_enforcer import FsmEnforcer


@pytest.fixture
def temp_fsm_enforcer():
    temp_dir = tempfile.mkdtemp(prefix="test_fsm_sop_")
    state_file = os.path.join(temp_dir, "fsm_state.json")
    enforcer = FsmEnforcer(state_file=state_file)
    yield enforcer


def test_sop_session_initialization(temp_fsm_enforcer):
    sop_path = os.path.join("standards", "sop", "smoke_test_sop.yaml")
    res = temp_fsm_enforcer.start_session(session_id="sop_sess_001", sop_file=sop_path)

    assert res["status"] == "PASS"
    assert res["session_id"] == "sop_sess_001"
    assert res["sop_id"] == "qa_smoke_test_sop"
    assert res["next_required_stage"] == "ENV_PRECHECK"


def test_sop_stage_evidence_validation_and_transition(temp_fsm_enforcer):
    sop_path = os.path.join("standards", "sop", "smoke_test_sop.yaml")
    temp_fsm_enforcer.start_session(session_id="sop_sess_002", sop_file=sop_path)

    # 1. Advance to initial stage ENV_PRECHECK with missing evidence -> REJECTED
    res_bad = temp_fsm_enforcer.advance_stage(
        stage="ENV_PRECHECK",
        actor="QA_ORCHESTRATOR",
        evidence={"random_field": "val"},  # Missing python_version and git_branch
    )
    assert res_bad["status"] == "REJECTED"
    assert "missing required field" in res_bad["error"]

    # 2. Advance to ENV_PRECHECK with valid evidence -> PASS
    res_ok = temp_fsm_enforcer.advance_stage(
        stage="ENV_PRECHECK",
        actor="QA_ORCHESTRATOR",
        evidence={"python_version": "3.12.10", "git_branch": "develop"},
    )
    assert res_ok["status"] == "PASS"
    assert "proof_token" in res_ok

    # 3. Unauthorized actor rejection
    res_unauth = temp_fsm_enforcer.advance_stage(
        stage="TEST_EXECUTION",
        actor="RANDOM_DEV",  # Expected: TEST_RUNNER
        evidence={"exit_code": 0, "total_tests": 10, "passed_tests": 10},
    )
    assert res_unauth["status"] == "REJECTED"
    assert "not authorized" in res_unauth["error"]

    # 4. Valid advance to TEST_EXECUTION
    res_test = temp_fsm_enforcer.advance_stage(
        stage="TEST_EXECUTION",
        actor="TEST_RUNNER",
        evidence={"exit_code": 0, "total_tests": 10, "passed_tests": 10},
    )
    assert res_test["status"] == "PASS"

    # 5. Advance to DOD_SIGN_OFF (final stage)
    res_dod = temp_fsm_enforcer.advance_stage(
        stage="DOD_SIGN_OFF",
        actor="DOD_GATEKEEPER",
        evidence={"dod_passed": True, "gates_verified": 10},
    )
    assert res_dod["status"] == "PASS"
    assert res_dod["workflow_status"] == "COMPLETED"

    # 6. Verify full compliance
    comp = temp_fsm_enforcer.verify_compliance()
    assert comp["status"] == "PASS"
    assert comp["compliant"] is True
    assert comp["sop_id"] == "qa_smoke_test_sop"
