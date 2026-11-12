# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for tools/fsm_middleware.py (Runtime FSM Interceptor & Tool Proxy)."""

import os
import sys
import tempfile
import shutil
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

from fsm_enforcer import FsmEnforcer
from fsm_middleware import FsmMiddleware


@pytest.fixture
def temp_middleware():
    tmp_dir = tempfile.mkdtemp()
    state_file = os.path.join(tmp_dir, "fsm_session.json")
    enforcer = FsmEnforcer(state_file=state_file)
    middleware = FsmMiddleware(enforcer=enforcer)
    yield middleware, enforcer
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_read_only_tools_always_allowed(temp_middleware):
    middleware, enforcer = temp_middleware
    enforcer.start_session("TEST_SESS_READONLY")

    for tool in ["view_file", "list_dir", "grep_search", "find_by_name", "read_url_content"]:
        allowed, reason = middleware.check_precondition(tool)
        assert allowed is True
        assert reason is None

        res = middleware.intercept(tool, {"target": "foo.txt"})
        assert res["status"] == "PASS"
        assert res["precondition_passed"] is True


def test_code_mutation_blocked_without_discovery(temp_middleware):
    middleware, enforcer = temp_middleware
    enforcer.start_session("TEST_SESS_MUTATION_BLOCK")

    # Attempt to write code without DISCOVERY
    for tool in ["write_to_file", "replace_file_content", "edit_file", "code_synthesis"]:
        allowed, reason = middleware.check_precondition(tool, {"TargetFile": "LoginPage.groovy"})
        assert allowed is False
        assert "requires Stage 1 (DISCOVERY)" in reason

        res = middleware.intercept(tool, {"TargetFile": "LoginPage.groovy"})
        assert res["status"] == "REJECTED_BY_FSM_INTERCEPTOR"
        assert res["precondition_passed"] is False


def test_code_mutation_allowed_after_discovery(temp_middleware):
    middleware, enforcer = temp_middleware
    enforcer.start_session("TEST_SESS_DISC_OK")

    # Sign off DISCOVERY with valid DOM/AOM proof
    adv = enforcer.advance_stage("DISCOVERY", "live-explorer", {"selectors": ["#username", "#password", "#login-btn"]})
    assert adv["status"] == "PASS"

    # Now write_to_file is permitted
    allowed, reason = middleware.check_precondition("write_to_file", {"TargetFile": "LoginPage.ts"})
    assert allowed is True
    assert reason is None

    # Handler executes when permitted
    called = []
    handler = lambda params: called.append(params) or "SUCCESS"
    res = middleware.intercept("write_to_file", {"TargetFile": "LoginPage.ts"}, handler=handler)
    assert res["status"] == "PASS"
    assert res["result"] == "SUCCESS"
    assert len(called) == 1


def test_code_mutation_blocked_if_discovery_lacks_dom_proof(temp_middleware):
    middleware, enforcer = temp_middleware
    enforcer.start_session("TEST_SESS_BAD_DISC")

    # DISCOVERY signed off without any DOM/AOM keys
    enforcer.state["completed_stages"]["DISCOVERY"] = {
        "stage": "DISCOVERY",
        "actor": "live-explorer",
        "evidence": {"unrelated_key": "some_value"}
    }
    enforcer._save_state()

    allowed, reason = middleware.check_precondition("write_to_file", {"TargetFile": "LoginPage.ts"})
    assert allowed is False
    assert "does not contain valid DOM/AOM contract data" in reason


def test_scratch_and_planning_files_bypass_mutation_check(temp_middleware):
    middleware, enforcer = temp_middleware
    enforcer.start_session("TEST_SESS_PLANNING")

    # Writing to planning or temp files is permitted even before DISCOVERY
    for f in ["task_plan.md", "findings.md", "progress.md", "scratch.tmp", "run.log"]:
        allowed, reason = middleware.check_precondition("write_to_file", {"TargetFile": f})
        assert allowed is True
        assert reason is None


def test_headless_exec_blocked_before_code_synthesis(temp_middleware):
    middleware, enforcer = temp_middleware
    enforcer.start_session("TEST_SESS_EXEC_BLOCK")

    # Advance DISCOVERY only
    enforcer.advance_stage("DISCOVERY", "live-explorer", {"selectors": ["#btn"]})

    # Test runner is blocked
    for tool in ["run_test", "headless_exec", "execute_test"]:
        allowed, reason = middleware.check_precondition(tool)
        assert allowed is False
        assert "requires Stage 2 (CODE_SYNTHESIS)" in reason

    # Advance CODE_SYNTHESIS
    enforcer.advance_stage("CODE_SYNTHESIS", "pom-crafter", {"pages": ["LoginPage.ts"]})

    # Now test runner is permitted
    allowed, reason = middleware.check_precondition("run_test")
    assert allowed is True
    assert reason is None


def test_autopsy_heal_blocked_before_headless_exec(temp_middleware):
    middleware, enforcer = temp_middleware
    enforcer.start_session("TEST_SESS_AUTOPSY")

    enforcer.advance_stage("DISCOVERY", "live-explorer", {"selectors": ["#btn"]})
    enforcer.advance_stage("CODE_SYNTHESIS", "pom-crafter", {"pages": ["LoginPage.ts"]})

    # Auto heal is blocked before execution
    allowed, reason = middleware.check_precondition("auto_heal")
    assert allowed is False
    assert "requires Stage 3 (HEADLESS_EXEC)" in reason

    # Advance HEADLESS_EXEC
    enforcer.advance_stage("HEADLESS_EXEC", "test-runner", {"exit_code": 1})

    # Auto heal is now permitted
    allowed, reason = middleware.check_precondition("auto_heal")
    assert allowed is True
    assert reason is None


def test_completion_blocked_if_stages_incomplete(temp_middleware):
    middleware, enforcer = temp_middleware
    enforcer.start_session("TEST_SESS_INCOMPLETE_DOD")

    enforcer.advance_stage("DISCOVERY", "live-explorer", {"selectors": ["#btn"]})

    # Task completion blocked
    for tool in ["complete_task", "finish_task", "verify_dod"]:
        allowed, reason = middleware.check_precondition(tool)
        assert allowed is False
        assert "must be completed before final DoD signoff" in reason


def test_full_5_stage_lifecycle_passes_middleware(temp_middleware):
    middleware, enforcer = temp_middleware
    enforcer.start_session("TEST_SESS_FULL_PIPELINE")

    # Stage 1: DISCOVERY
    assert middleware.check_precondition("write_to_file", {"TargetFile": "Page.ts"})[0] is False
    enforcer.advance_stage("DISCOVERY", "live-explorer", {"selectors": ["#btn"]})
    assert middleware.check_precondition("write_to_file", {"TargetFile": "Page.ts"})[0] is True

    # Stage 2: CODE_SYNTHESIS
    assert middleware.check_precondition("run_test")[0] is False
    enforcer.advance_stage("CODE_SYNTHESIS", "pom-crafter", {"pages": ["Page.ts"]})
    assert middleware.check_precondition("run_test")[0] is True

    # Stage 3: HEADLESS_EXEC
    assert middleware.check_precondition("auto_heal")[0] is False
    enforcer.advance_stage("HEADLESS_EXEC", "test-runner", {"exit_code": 0})
    assert middleware.check_precondition("auto_heal")[0] is True

    # Stage 4: AUTOPSY_HEAL
    assert middleware.check_precondition("complete_task")[0] is False
    enforcer.advance_stage("AUTOPSY_HEAL", "failure-analyst", {"status": "PASSED"})

    # Stage 5: ACCEPTANCE_DOD
    enforcer.advance_stage("ACCEPTANCE_DOD", "quality-gatekeeper", {"gates_passed": 10})

    # Now completion is permitted and DoD passes
    allowed, reason = middleware.check_precondition("complete_task")
    assert allowed is True
    assert reason is None


def test_custom_guard_registration(temp_middleware):
    middleware, enforcer = temp_middleware
    enforcer.start_session("TEST_SESS_CUSTOM")

    # Register custom guard requiring HEADLESS_EXEC and exit_code == 0
    def validator(params):
        if params.get("env") != "staging":
            return False, "Must deploy to staging first"
        return True, None

    middleware.register_guard("deploy_artifact", "HEADLESS_EXEC", validator)

    # Blocked because HEADLESS_EXEC not completed
    allowed, reason = middleware.check_precondition("deploy_artifact", {"env": "staging"})
    assert allowed is False
    assert "Requires Stage 'HEADLESS_EXEC'" in reason

    # Advance to HEADLESS_EXEC
    enforcer.advance_stage("DISCOVERY", "live-explorer", {"selectors": ["#btn"]})
    enforcer.advance_stage("CODE_SYNTHESIS", "pom-crafter", {"pages": ["Page.ts"]})
    enforcer.advance_stage("HEADLESS_EXEC", "test-runner", {"exit_code": 0})

    # Custom validator fails if env != staging
    allowed, reason = middleware.check_precondition("deploy_artifact", {"env": "prod"})
    assert allowed is False
    assert "Must deploy to staging first" in reason

    # Custom validator passes
    allowed, reason = middleware.check_precondition("deploy_artifact", {"env": "staging"})
    assert allowed is True
    assert reason is None


def test_acceptance_dod_allowed_after_stages_1_to_4(temp_middleware):
    """Verifies that entering Stage 5 (acceptance_dod) is allowed once stages 1-4 are done (no circular deadlock)."""
    middleware, enforcer = temp_middleware
    enforcer.start_session("TEST_SESS_DOD_ENTRY")

    # Before stages 1-4, acceptance_dod is blocked
    allowed, reason = middleware.check_precondition("acceptance_dod")
    assert allowed is False
    assert "Entering Stage 5 (ACCEPTANCE_DOD) requires" in reason

    # Complete stages 1-4
    enforcer.advance_stage("DISCOVERY", "live-explorer", {"target_url": "https://example.com"})
    enforcer.advance_stage("CODE_SYNTHESIS", "pom-crafter", {"pages": ["Login.ts"]})
    enforcer.advance_stage("HEADLESS_EXEC", "test-runner", {"exit_code": 0})
    enforcer.advance_stage("AUTOPSY_HEAL", "failure-analyst", {"waiver": "PASS"})

    # Now acceptance_dod must be allowed to execute
    allowed, reason = middleware.check_precondition("acceptance_dod")
    assert allowed is True
    assert reason is None

    # But task completion (e.g. finish_task) must still be blocked until Stage 5 is signed off
    allowed_finish, _ = middleware.check_precondition("finish_task")
    assert allowed_finish is False


def test_run_command_intercepts_test_runners(temp_middleware):
    """Verifies that run_command with test runners (pytest, playwright, npm test) is blocked before CODE_SYNTHESIS."""
    middleware, enforcer = temp_middleware
    enforcer.start_session("TEST_SESS_CMD_INTERCEPT")

    # Blocked before CODE_SYNTHESIS
    for cmd in ["pytest tests/ -q", "playwright test", "npm test -- e2e"]:
        allowed, reason = middleware.check_precondition("run_command", {"CommandLine": cmd})
        assert allowed is False
        assert "requires Stage 2 (CODE_SYNTHESIS)" in reason

    # Advance DISCOVERY and CODE_SYNTHESIS
    enforcer.advance_stage("DISCOVERY", "live-explorer", {"selectors": ["#btn"]})
    enforcer.advance_stage("CODE_SYNTHESIS", "pom-crafter", {"pages": ["Login.ts"]})

    # Now allowed
    for cmd in ["pytest tests/ -q", "playwright test", "npm test -- e2e"]:
        allowed, reason = middleware.check_precondition("run_command", {"CommandLine": cmd})
        assert allowed is True
        assert reason is None


def test_circuit_breaker_override_context_token(temp_middleware):
    """Verifies that an emergency context token bypasses DISCOVERY gate for code mutation."""
    middleware, enforcer = temp_middleware
    enforcer.start_session("TEST_SESS_CB_CTX")

    # DISCOVERY is NOT done. Normally write_to_file is blocked.
    allowed, _ = middleware.check_precondition("write_to_file", {"TargetFile": "OrderPage.ts"})
    assert allowed is False

    # With circuit breaker override token in context, it is allowed
    allowed_override, reason = middleware.check_precondition(
        "write_to_file",
        {"TargetFile": "OrderPage.ts", "circuit_breaker_override": "CDP_HANG_RECOVERY"}
    )
    assert allowed_override is True
    assert reason is None


def test_circuit_breaker_override_env_var(temp_middleware, monkeypatch):
    """Verifies that SYNAPSE_CIRCUIT_BREAKER_OVERRIDE env var bypasses DISCOVERY gate."""
    middleware, enforcer = temp_middleware
    enforcer.start_session("TEST_SESS_CB_ENV")

    # Normally blocked
    allowed, _ = middleware.check_precondition("write_to_file", {"TargetFile": "OrderPage.ts"})
    assert allowed is False

    # Set env var
    monkeypatch.setenv("SYNAPSE_CIRCUIT_BREAKER_OVERRIDE", "EMERGENCY_PROD_HOTFIX")
    allowed_env, reason = middleware.check_precondition("write_to_file", {"TargetFile": "OrderPage.ts"})
    assert allowed_env is True
    assert reason is None


def test_circuit_breaker_state_trip_and_reset(temp_middleware):
    """Verifies that trip_circuit_breaker() and reset_circuit_breaker() toggle bypass behavior."""
    middleware, enforcer = temp_middleware
    enforcer.start_session("TEST_SESS_CB_TRIP")

    # Initial state: not tripped, blocked
    allowed, _ = middleware.check_precondition("write_to_file", {"TargetFile": "OrderPage.ts"})
    assert allowed is False
    active, _ = middleware.is_circuit_breaker_active()
    assert active is False

    # Trip breaker
    cb_data = middleware.trip_circuit_breaker(reason="Headless browser crash on port 9222")
    assert cb_data["tripped"] is True
    assert cb_data["reason"] == "Headless browser crash on port 9222"

    active_after, reason = middleware.is_circuit_breaker_active()
    assert active_after is True
    assert "Headless browser crash" in reason

    # Now allowed even without DISCOVERY
    allowed_tripped, reason_tripped = middleware.check_precondition("write_to_file", {"TargetFile": "OrderPage.ts"})
    assert allowed_tripped is True
    assert reason_tripped is None

    # Reset breaker
    reset_data = middleware.reset_circuit_breaker()
    assert reset_data["tripped"] is False
    assert reset_data["reason"] is None

    # Should be blocked again
    allowed_reset, reason_reset = middleware.check_precondition("write_to_file", {"TargetFile": "OrderPage.ts"})
    assert allowed_reset is False
    assert "requires Stage 1 (DISCOVERY)" in reason_reset


