# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""Unit tests for tools/fsm_enforcer.py (Enterprise 5-Stage QA Multi-Agent FSM Enforcer)."""

import os
import sys
import tempfile
import shutil
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

from fsm_enforcer import FsmEnforcer


@pytest.fixture
def temp_fsm_state():
    tmp_dir = tempfile.mkdtemp()
    state_file = os.path.join(tmp_dir, "fsm_session.json")
    yield state_file
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_fsm_linear_workflow_success(temp_fsm_state):
    enforcer = FsmEnforcer(state_file=temp_fsm_state)
    start_res = enforcer.start_session("TEST_SESS_01")
    assert start_res["status"] == "PASS"

    # Stage 1: DISCOVERY
    r1 = enforcer.advance_stage("DISCOVERY", "live-explorer", {"selectors": ["#login-btn"]})
    assert r1["status"] == "PASS"
    assert r1["next_required_stage"] == "CODE_SYNTHESIS"

    # Stage 2: CODE_SYNTHESIS
    r2 = enforcer.advance_stage("CODE_SYNTHESIS", "pom-crafter", {"pages": ["LoginPage.ts"]})
    assert r2["status"] == "PASS"
    assert r2["next_required_stage"] == "HEADLESS_EXEC"

    # Stage 3: HEADLESS_EXEC
    r3 = enforcer.advance_stage("HEADLESS_EXEC", "test-runner", {"exit_code": 0, "tests_run": 5})
    assert r3["status"] == "PASS"
    assert r3["next_required_stage"] == "AUTOPSY_HEAL"

    # Stage 4: AUTOPSY_HEAL
    r4 = enforcer.advance_stage("AUTOPSY_HEAL", "failure-analyst", {"verdict": "PASSED_NO_HEAL_NEEDED"})
    assert r4["status"] == "PASS"
    assert r4["next_required_stage"] == "ACCEPTANCE_DOD"

    # Stage 5: ACCEPTANCE_DOD
    r5 = enforcer.advance_stage("ACCEPTANCE_DOD", "quality-gatekeeper", {"gates_passed": 10})
    assert r5["status"] == "PASS"
    assert r5["workflow_completed"] is True

    # Final compliance check
    comp = enforcer.verify_compliance()
    assert comp["status"] == "PASS"
    assert comp["compliant"] is True
    assert len(comp["proof_tokens"]) == 5


def test_fsm_rejects_stage_jumping(temp_fsm_state):
    enforcer = FsmEnforcer(state_file=temp_fsm_state)
    enforcer.start_session()

    # Attempt to jump straight from start to HEADLESS_EXEC (skipping DISCOVERY & SYNTHESIS)
    bad_res = enforcer.advance_stage("HEADLESS_EXEC", "test-runner", {"exit_code": 0})
    assert bad_res["status"] == "REJECTED"
    assert "preceding stage" in bad_res["error"].lower()

    # Attempt to jump directly to DoD gatekeeper
    bad_dod = enforcer.advance_stage("ACCEPTANCE_DOD", "quality-gatekeeper", {"gates": 10})
    assert bad_dod["status"] == "REJECTED"


def test_fsm_rejects_unauthorized_actor(temp_fsm_state):
    enforcer = FsmEnforcer(state_file=temp_fsm_state)
    enforcer.start_session()

    # Unauthorized actor attempting DISCOVERY signoff
    bad_actor = enforcer.advance_stage("DISCOVERY", "unauthorized-hacker", {"data": 123})
    assert bad_actor["status"] == "REJECTED"
    assert "not authorized" in bad_actor["error"].lower()


def test_fsm_verify_compliance_blocked_when_incomplete(temp_fsm_state):
    enforcer = FsmEnforcer(state_file=temp_fsm_state)
    enforcer.start_session()

    enforcer.advance_stage("DISCOVERY", "live-explorer", {"element": "input"})
    enforcer.advance_stage("CODE_SYNTHESIS", "pom-crafter", {"file": "Page.ts"})

    # Compliance check when only 2 stages done
    comp = enforcer.verify_compliance()
    assert comp["status"] == "BLOCKED"
    assert comp["compliant"] is False
    assert "HEADLESS_EXEC" in comp["missing_stages"]
