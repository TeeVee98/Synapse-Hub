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


def test_load_persona_prompt_and_non_tool_hub_wiring(tmp_path, monkeypatch):
    """Verifies ai-agents persona/specialist loading, plugin.json skills, v5 collision guard, and global plugin sync."""
    import json
    from fsm_enforcer import load_persona_prompt
    from tools.core import check_env, setup_project
    from tools.lint.skill_collision_guard import SkillCollisionGuard

    # 1. Persona & specialist prompt loader (ai-agents/ + agents_manifest.json)
    orch = load_persona_prompt("orchestrator", repo_root=ROOT_DIR)
    assert orch["found"] is True
    assert "orchestrator" in orch["file"]
    assert len(orch["prompt"]) > 50

    spec = load_persona_prompt("silent-failure-hunter", repo_root=ROOT_DIR)
    assert spec["found"] is True
    assert "specialists" in spec["file"]

    missing = load_persona_prompt("nonexistent-persona-xyz", repo_root=ROOT_DIR)
    assert missing["found"] is False
    assert missing["prompt"] == ""

    # 2. .claude-plugin/plugin.json exposes ./skills/
    with open(os.path.join(ROOT_DIR, ".claude-plugin", "plugin.json"), "r", encoding="utf-8") as f:
        cp_plugin = json.load(f)
    assert "./skills/" in cp_plugin.get("skills", [])

    # 3. check_env recognizes v5 skills/ + standards/ layout
    runner = check_env.DiagnosticRunner(target_dir=ROOT_DIR)
    runner.check_project_structure()
    assert len(runner.errors) == 0

    # 4. SkillCollisionGuard resolves v5 skills/ and standards/ when .agents/skills or .agents/rules is absent
    guard = SkillCollisionGuard()
    descs = guard.load_descriptions()
    assert len(descs) >= 57
    rules = guard.load_rules()
    assert len(rules) >= 1

    # 5. inject_antigravity_global_plugin syncs ai-agents/, commands/, and agents_manifest.json
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(os.path, "expanduser", lambda p: p.replace("~", str(fake_home), 1))
    assert setup_project.inject_antigravity_global_plugin() is True
    plugin_dir = fake_home / ".gemini" / "config" / "plugins" / "synapse-hub"
    assert (plugin_dir / "ai-agents" / "personas" / "orchestrator.md").is_file()
    assert (plugin_dir / "commands" / "synapse-audit.toml").is_file()
    assert (plugin_dir / "agents_manifest.json").is_file()
    assert (plugin_dir / "skills").is_dir()


# ==============================================================================
# Milestone 6 (P1.4): Fail-Closed FSM Middleware & Fail-Safe Semantic Entropy
# ==============================================================================

def test_m6_unknown_action_blocked_in_active_workflow(temp_middleware):
    """Negative (TC-09): Unknown/unrecognized actions fail closed (UNKNOWN_ACTION_BLOCKED) in active workflow."""
    middleware, enforcer = temp_middleware
    enforcer.start_session("TEST_M6_FAIL_CLOSED")

    assert middleware.is_workflow_active() is True
    for unknown_action in ("unknown_custom_mutation", "arbitrary_bypass_tool", "stealth_write"):
        allowed, reason = middleware.check_precondition(unknown_action, {"TargetFile": "x.py"})
        assert allowed is False
        assert reason is not None
        assert "UNKNOWN_ACTION_BLOCKED" in reason

        called = []
        res = middleware.intercept(unknown_action, {"TargetFile": "x.py"}, handler=lambda p: called.append(p))
        assert res["status"] == "REJECTED_BY_FSM_INTERCEPTOR"
        assert res["precondition_passed"] is False
        assert "UNKNOWN_ACTION_BLOCKED" in res["error"]
        assert called == []

    # Verify 'done' action also enforces Stage 1-5 completion gate
    allowed_done, reason_done = middleware.check_precondition("done")
    assert allowed_done is False
    assert "must be completed before final DoD signoff" in reason_done


def test_m6_uninitialized_mode_backward_compatible_and_verdict_contract(temp_middleware):
    """Positive: Uncontrolled/uninitialized mode remains backward-compatible; FailClosedGuardVerdict enforces entropy gate."""
    from dataclasses import FrozenInstanceError
    from fsm_middleware import FailClosedGuardVerdict

    middleware, enforcer = temp_middleware
    # Uninitialized workflow (start_session not called) -> backward-compatible pass-through
    assert middleware.is_workflow_active() is False
    allowed, reason = middleware.check_precondition("unknown_custom_mutation")
    assert allowed is True
    assert reason is None

    # Active workflow -> FailClosedGuardVerdict contract is frozen & enforces entropy
    enforcer.start_session("TEST_M6_VERDICT")
    enforcer.advance_stage("DISCOVERY", "live-explorer", {"selectors": ["#submit"]})

    verdict_ok = middleware.evaluate_guard_verdict("write_to_file", {"TargetFile": "App.ts"}, entropy_status="CONFIDENT_LOW_ENTROPY")
    assert isinstance(verdict_ok, FailClosedGuardVerdict)
    assert verdict_ok.allowed is True
    assert verdict_ok.workflow_active is True
    assert verdict_ok.code_write_permission is True
    with pytest.raises(FrozenInstanceError):
        verdict_ok.allowed = False  # type: ignore[misc]

    # When entropy reports ERROR_REVIEW_REQUIRED, code_write_permission MUST be False
    verdict_err = middleware.evaluate_guard_verdict("write_to_file", {"TargetFile": "App.ts"}, entropy_status="ERROR_REVIEW_REQUIRED")
    assert verdict_err.allowed is True
    assert verdict_err.code_write_permission is False
    assert verdict_err.entropy_status == "ERROR_REVIEW_REQUIRED"

    # Unknown action in verdict produces allowed=False and code_write_permission=False
    verdict_unk = middleware.evaluate_guard_verdict("unknown_custom_mutation")
    assert verdict_unk.allowed is False
    assert verdict_unk.code_write_permission is False
    assert verdict_unk.reason is not None and "UNKNOWN_ACTION_BLOCKED" in verdict_unk.reason


def test_m6_boundary_empty_and_whitespace_action_blocked_when_active(temp_middleware):
    """Boundary: Empty or whitespace action strings fail closed in active workflow."""
    middleware, enforcer = temp_middleware
    enforcer.start_session("TEST_M6_BOUNDARY")

    for blank in ("", "   ", "\t\n"):
        allowed, reason = middleware.check_precondition(blank)
        assert allowed is False
        assert reason is not None
        assert "UNKNOWN_ACTION_BLOCKED" in reason


def test_m6_run_debate_semantic_entropy_exception_fails_closed(monkeypatch):
    """Negative & Resilience (TC-09): SemanticEntropyEngine exceptions fail closed instead of silently returning 0.0."""
    from tools.orchestration import solo_runner

    # 1. Runtime exception in SemanticEntropyEngine -> fail closed
    def _boom(*args, **kwargs):
        raise RuntimeError("embedding backend offline")

    monkeypatch.setattr(solo_runner.SemanticEntropyEngine, "evaluate_hypotheses", _boom)
    res_err = solo_runner.run_debate(proposal="Harden auth token rotation", rounds=1)
    assert res_err["semantic_entropy"] is None
    assert res_err["uncertainty_status"] == "ERROR_REVIEW_REQUIRED"
    assert res_err["code_write_permission"] is False
    assert "embedding backend offline" in (res_err.get("entropy_error") or "")

    # 2. Malformed/empty payload from SemanticEntropyEngine -> fail closed
    monkeypatch.setattr(solo_runner.SemanticEntropyEngine, "evaluate_hypotheses", lambda *a, **kw: {})
    res_bad = solo_runner.run_debate(proposal="Harden auth token rotation", rounds=1)
    assert res_bad["semantic_entropy"] is None
    assert res_bad["uncertainty_status"] == "ERROR_REVIEW_REQUIRED"
    assert res_bad["code_write_permission"] is False

    # 3. Normal execution restores real float entropy and boolean code_write_permission
    monkeypatch.undo()
    res_ok = solo_runner.run_debate(proposal="Implement idempotent JWT refresh", rounds=1)
    assert isinstance(res_ok["semantic_entropy"], float)
    assert isinstance(res_ok["code_write_permission"], bool)
    assert res_ok["uncertainty_status"] != "ERROR_REVIEW_REQUIRED"
    assert res_ok["entropy_error"] is None


def test_m6_cli_check_precondition_json_output():
    """CLI: fsm_middleware.py check-precondition returns valid JSON status and exit code."""
    import json
    import subprocess

    script = os.path.join(ROOT_DIR, "tools", "core", "fsm_middleware.py")
    proc = subprocess.run(
        [sys.executable, script, "check-precondition", "--action", "view_file"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["action"] == "view_file"
    assert payload["allowed"] is True
    assert payload["reason"] is None



