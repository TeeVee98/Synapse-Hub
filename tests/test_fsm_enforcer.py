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


def test_fsm_rejects_orchestrator_bypass_strict_separation(temp_fsm_state):
    """Verifies that orchestrator bypass is strictly blocked across all 5 execution stages."""
    enforcer = FsmEnforcer(state_file=temp_fsm_state)
    enforcer.start_session("STRICT_ACTOR_TEST")

    # Orchestrator cannot sign off on DISCOVERY
    r1 = enforcer.advance_stage("DISCOVERY", "orchestrator", {"selectors": ["#btn"]})
    assert r1["status"] == "REJECTED"
    assert "not authorized" in r1["error"].lower()

    # Legitimate actor signs off DISCOVERY
    r1_ok = enforcer.advance_stage("DISCOVERY", "live-explorer", {"selectors": ["#btn"]})
    assert r1_ok["status"] == "PASS"

    # Orchestrator cannot sign off on CODE_SYNTHESIS
    r2 = enforcer.advance_stage("CODE_SYNTHESIS", "orchestrator", {"pages": ["Page.ts"]})
    assert r2["status"] == "REJECTED"
    assert "not authorized" in r2["error"].lower()

    # Legitimate actor signs off CODE_SYNTHESIS
    r2_ok = enforcer.advance_stage("CODE_SYNTHESIS", "pom-crafter", {"pages": ["Page.ts"]})
    assert r2_ok["status"] == "PASS"

    # Orchestrator cannot sign off on HEADLESS_EXEC
    r3 = enforcer.advance_stage("HEADLESS_EXEC", "orchestrator", {"exit_code": 0})
    assert r3["status"] == "REJECTED"
    assert "not authorized" in r3["error"].lower()

    # Legitimate actor signs off HEADLESS_EXEC
    r3_ok = enforcer.advance_stage("HEADLESS_EXEC", "test-runner", {"exit_code": 0})
    assert r3_ok["status"] == "PASS"

    # Orchestrator cannot sign off on AUTOPSY_HEAL
    r4 = enforcer.advance_stage("AUTOPSY_HEAL", "orchestrator", {"status": "PASSED"})
    assert r4["status"] == "REJECTED"
    assert "not authorized" in r4["error"].lower()

    # Legitimate actor signs off AUTOPSY_HEAL
    r4_ok = enforcer.advance_stage("AUTOPSY_HEAL", "failure-analyst", {"status": "PASSED"})
    assert r4_ok["status"] == "PASS"

    # Orchestrator cannot sign off on ACCEPTANCE_DOD
    r5 = enforcer.advance_stage("ACCEPTANCE_DOD", "orchestrator", {"gates": 10})
    assert r5["status"] == "REJECTED"
    assert "not authorized" in r5["error"].lower()

    # Legitimate actor signs off ACCEPTANCE_DOD
    r5_ok = enforcer.advance_stage("ACCEPTANCE_DOD", "quality-gatekeeper", {"gates": 10})
    assert r5_ok["status"] == "PASS"
    assert r5_ok["workflow_completed"] is True


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


def test_fsm_artifact_hashing_and_tamper_detection(temp_fsm_state):
    """Verifies that physical files on disk have their SHA-256 hashes recorded and verified."""
    enforcer = FsmEnforcer(state_file=temp_fsm_state)
    enforcer.start_session("TEST_ARTIFACT_SESS")

    tmp_dir = os.path.dirname(temp_fsm_state)
    dummy_page = os.path.join(tmp_dir, "LoginPage.ts")
    with open(dummy_page, "w", encoding="utf-8") as f:
        f.write("export class LoginPage {}")

    enforcer.advance_stage("DISCOVERY", "live-explorer", {"selectors": ["#login"]})
    adv = enforcer.advance_stage("CODE_SYNTHESIS", "pom-crafter", {"pages": [dummy_page]})
    assert adv["status"] == "PASS"

    # Verify SHA-256 hash was embedded
    rec = enforcer.state["completed_stages"]["CODE_SYNTHESIS"]
    assert "artifact_hashes" in rec["evidence"]
    assert dummy_page in rec["evidence"]["artifact_hashes"]
    original_hash = rec["evidence"]["artifact_hashes"][dummy_page]
    assert len(original_hash) == 64

    # Advance remaining stages
    enforcer.advance_stage("HEADLESS_EXEC", "test-runner", {"exit_code": 0})
    enforcer.advance_stage("AUTOPSY_HEAL", "failure-analyst", {"status": "PASSED"})
    enforcer.advance_stage("ACCEPTANCE_DOD", "quality-gatekeeper", {"gates": 10})

    # Integrity passes while file is untouched
    comp = enforcer.verify_compliance()
    assert comp["status"] == "PASS"

    # Tamper with the physical file on disk
    with open(dummy_page, "a", encoding="utf-8") as f:
        f.write("\n// Malicious injection after signoff")

    tampered_comp = enforcer.verify_compliance()
    assert tampered_comp["status"] == "BLOCKED"
    assert "Artifact integrity verification failed" in tampered_comp["error"]


def test_perf_engineer_headless_exec_stage(temp_fsm_state):
    """Verifies that perf-engineer can advance HEADLESS_EXEC stage with performance test evidence."""
    enforcer = FsmEnforcer(state_file=temp_fsm_state)
    enforcer.start_session("PERF_TEST_SESS")

    enforcer.advance_stage("DISCOVERY", "live-explorer", {"target_url": "https://api.staging.example.com"})
    enforcer.advance_stage("CODE_SYNTHESIS", "pom-crafter", {"scripts": ["load_plan.jmx"]})

    # Stage 3: HEADLESS_EXEC with perf-engineer actor
    r3 = enforcer.advance_stage(
        "HEADLESS_EXEC",
        "perf-engineer",
        {"exit_code": 0, "vus": 50, "p95_ms": 320, "error_rate": 0.0}
    )
    assert r3["status"] == "PASS"
    assert r3["next_required_stage"] == "AUTOPSY_HEAL"
    assert enforcer.state["completed_stages"]["HEADLESS_EXEC"]["actor"] == "perf-engineer"


def test_test_designer_discovery_stage(temp_fsm_state):
    """Verifies that test-designer can advance DISCOVERY stage with manual test matrix evidence."""
    enforcer = FsmEnforcer(state_file=temp_fsm_state)
    enforcer.start_session("MANUAL_DESIGN_SESS")

    r1 = enforcer.advance_stage(
        "DISCOVERY",
        "test-designer",
        {"matrix": "Login_Traceability_Matrix.xlsx", "test_cases": 15}
    )
    assert r1["status"] == "PASS"
    assert r1["next_required_stage"] == "CODE_SYNTHESIS"
    assert enforcer.state["completed_stages"]["DISCOVERY"]["actor"] == "test-designer"


def test_api_engineer_stages(temp_fsm_state):
    """Verifies that api-engineer can synthesize API matrices and execute API tests in FSM."""
    enforcer = FsmEnforcer(state_file=temp_fsm_state)
    enforcer.start_session("API_TEST_SESS")

    enforcer.advance_stage("DISCOVERY", "live-explorer", {"target_url": "https://api.staging.example.com"})

    # Stage 2: CODE_SYNTHESIS with api-engineer
    r2 = enforcer.advance_stage(
        "CODE_SYNTHESIS",
        "api-engineer",
        {"api_matrix": "orders_api_matrix.json", "endpoints": ["/api/v1/orders"]}
    )
    assert r2["status"] == "PASS"
    assert r2["next_required_stage"] == "HEADLESS_EXEC"

    # Stage 3: HEADLESS_EXEC with api-engineer
    r3 = enforcer.advance_stage(
        "HEADLESS_EXEC",
        "api-engineer",
        {"exit_code": 0, "tests_run": 12, "failed": 0}
    )
    assert r3["status"] == "PASS"
    assert r3["next_required_stage"] == "AUTOPSY_HEAL"
    assert enforcer.state["completed_stages"]["HEADLESS_EXEC"]["actor"] == "api-engineer"
