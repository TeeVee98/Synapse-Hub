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


def test_fsm_evidence_schema_validation_rejection(temp_fsm_state):
    """Verifies that evidence failing the stage schema contract is rejected."""
    enforcer = FsmEnforcer(state_file=temp_fsm_state)
    enforcer.start_session()

    # DISCOVERY requires selectors / locators / target
    r_bad_disc = enforcer.advance_stage("DISCOVERY", "live-explorer", {"unrelated_field": 123})
    assert r_bad_disc["status"] == "REJECTED"
    assert "missing required context" in r_bad_disc["error"].lower()

    # Valid DISCOVERY
    r_ok_disc = enforcer.advance_stage("DISCOVERY", "live-explorer", {"selectors": ["#btn"]})
    assert r_ok_disc["status"] == "PASS"

    # SYNTHESIS requires pages / files / scripts
    r_bad_syn = enforcer.advance_stage("CODE_SYNTHESIS", "pom-crafter", {"random": True})
    assert r_bad_syn["status"] == "REJECTED"

    # Valid SYNTHESIS
    r_ok_syn = enforcer.advance_stage("CODE_SYNTHESIS", "pom-crafter", {"pages": ["Page.ts"]})
    assert r_ok_syn["status"] == "PASS"

    # HEADLESS_EXEC requires exit_code as int
    r_bad_exec = enforcer.advance_stage("HEADLESS_EXEC", "test-runner", {"summary": "all good"})
    assert r_bad_exec["status"] == "REJECTED"
    assert "missing mandatory field 'exit_code'" in r_bad_exec["error"]

    r_bad_type = enforcer.advance_stage("HEADLESS_EXEC", "test-runner", {"exit_code": "0"})
    assert r_bad_type["status"] == "REJECTED"
    assert "must be of type int" in r_bad_type["error"]


def test_fsm_cryptographic_tamper_detection(temp_fsm_state):
    """Verifies that tampering with serialized state file invalidates proof tokens."""
    import json
    enforcer = FsmEnforcer(state_file=temp_fsm_state)
    enforcer.start_session("TAMPER_TEST_SESS")

    enforcer.advance_stage("DISCOVERY", "live-explorer", {"selectors": ["#btn"]})
    enforcer.advance_stage("CODE_SYNTHESIS", "pom-crafter", {"pages": ["Page.ts"]})
    enforcer.advance_stage("HEADLESS_EXEC", "test-runner", {"exit_code": 0})
    enforcer.advance_stage("AUTOPSY_HEAL", "failure-analyst", {"verdict": "PASSED_NO_HEAL_NEEDED"})
    enforcer.advance_stage("ACCEPTANCE_DOD", "quality-gatekeeper", {"gates_passed": 10})

    # Legitimate state passes
    comp = enforcer.verify_compliance()
    assert comp["status"] == "PASS"
    assert comp["compliant"] is True

    # Tamper with the evidence on disk
    with open(temp_fsm_state, "r", encoding="utf-8") as f:
        state_data = json.load(f)

    # Tamper with DISCOVERY evidence maliciously
    state_data["completed_stages"]["DISCOVERY"]["evidence"]["malicious_injection"] = "hacked"
    with open(temp_fsm_state, "w", encoding="utf-8") as f:
        json.dump(state_data, f, indent=2)

    # New enforcer instance audits tampered state
    auditor = FsmEnforcer(state_file=temp_fsm_state)
    tampered_comp = auditor.verify_compliance()
    assert tampered_comp["status"] == "BLOCKED"
    assert tampered_comp["compliant"] is False
    assert "DISCOVERY" in tampered_comp["tampered_stages"]
