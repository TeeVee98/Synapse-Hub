#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
4-Scenario TDD Verification Suite for Multi-Model Orchestration across:
  - Milestone 3 (Capability-Tier Router, Cross-Family Pairing & Tier-Preserving Cascade)
  - Milestone 4 (5-Provider Dynamic Budgets, KV-Cache Prefix & Declarative Persona Tiers)
  - Milestone 5 (Host Control Plane Wiring: super_plan_engine, fsm_enforcer, solo_runner --purple)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import pytest

from tools.core.circuit_breaker import (
    CircuitBreakerState,
    RateLimitExceededError,
    TokenCircuitBreaker,
    resolve_tier_preserving_failover,
)
from tools.core.model_registry import (
    CapabilityTier,
    CrossModelAssignmentDTO,
    ProviderFamily,
)
from tools.reasoning.qa_model_router import (
    QAModelRouter,
    resolve_cross_family_assignment,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ==============================================================================
# Milestone 3: Capability Router, Cross-Family Pairing & Failover Cascade
# ==============================================================================


def test_cross_family_and_failover_positive():
    """TC-02 Positive: Cross-family Prover/Auditor isolation, preferred provider routing, and 429/503 cascade."""
    assignment = resolve_cross_family_assignment(
        "Architect distributed payment auth schema refactor",
        available_providers=(ProviderFamily.GEMINI, ProviderFamily.ANTHROPIC, ProviderFamily.OPENAI),
    )
    assert isinstance(assignment, CrossModelAssignmentDTO)
    assert assignment.capability_tier == CapabilityTier.DEEP_ARCHITECT
    assert assignment.primary_prover.provider == ProviderFamily.GEMINI
    assert assignment.adversarial_auditor.provider != assignment.primary_prover.provider
    assert assignment.adversarial_auditor.provider in (ProviderFamily.ANTHROPIC, ProviderFamily.OPENAI)
    assert assignment.cross_family_isolated is True
    assert assignment.degradation_reason is None
    assert len(assignment.fallback_chain) >= 2
    assert assignment.primary_prover.model_id not in assignment.fallback_chain

    router = QAModelRouter()
    fast_anthropic = router.route_capability(
        "Run ruff format and utf-8 check",
        preferred_provider=ProviderFamily.ANTHROPIC,
    )
    assert fast_anthropic.capability_tier == CapabilityTier.FAST_EXPLORER
    assert fast_anthropic.provider == ProviderFamily.ANTHROPIC
    assert fast_anthropic.model_id == "claude-haiku-5.5"

    work_openai = router.route_capability(
        "Execute login smoke workflow",
        preferred_provider=ProviderFamily.OPENAI,
    )
    assert work_openai.capability_tier == CapabilityTier.CODE_WORKHORSE
    assert work_openai.provider == ProviderFamily.OPENAI
    assert work_openai.model_id == "gpt-6.2-sol"

    # Tier-preserving failover excludes failed provider and ranks >= required_tier first
    candidates = resolve_tier_preserving_failover(
        failed_model_id="gemini-4-neon",
        required_tier=CapabilityTier.DEEP_ARCHITECT,
        excluded_providers=(ProviderFamily.GEMINI,),
    )
    assert len(candidates) >= 3
    assert all(c.provider != ProviderFamily.GEMINI for c in candidates)
    assert candidates[0].rank == 3

    # TokenCircuitBreaker tier-preserving failover on HTTP 429 and transient 503 (TC-ADV-02)
    cb = TokenCircuitBreaker(rate_limit_threshold=1)
    next_spec_429 = cb.route_failover_candidate(
        failed_model_id="gemini-4-neon",
        required_tier=CapabilityTier.DEEP_ARCHITECT,
        status_code=429,
    )
    assert next_spec_429.provider != ProviderFamily.GEMINI
    assert cb.state == CircuitBreakerState.FALLBACK

    next_spec_503 = cb.route_failover_candidate(
        failed_model_id=next_spec_429.model_id,
        required_tier=CapabilityTier.DEEP_ARCHITECT,
        status_code=503,
    )
    assert next_spec_503.provider not in (ProviderFamily.GEMINI, next_spec_429.provider)


def test_m3_negative_exhausted_providers_and_unknown_model():
    """M3 Negative: All providers excluded returns empty list and trips circuit breaker on HTTP 429."""
    empty_failover = resolve_tier_preserving_failover(
        failed_model_id="gemini-4-neon",
        required_tier=CapabilityTier.DEEP_ARCHITECT,
        excluded_providers=tuple(ProviderFamily),
    )
    assert empty_failover == []

    # Unknown model ID still computes valid failover list for unexcluded providers
    unknown_failover = resolve_tier_preserving_failover(
        failed_model_id="nonexistent-model-xyz",
        required_tier=CapabilityTier.CODE_WORKHORSE,
        excluded_providers=(ProviderFamily.GEMINI,),
    )
    assert len(unknown_failover) >= 2
    assert all(m.provider != ProviderFamily.GEMINI for m in unknown_failover)

    cb = TokenCircuitBreaker(rate_limit_threshold=1)
    with pytest.raises(RateLimitExceededError):
        cb.route_failover_candidate(
            failed_model_id="gemini-4-neon",
            required_tier=CapabilityTier.DEEP_ARCHITECT,
            status_code=429,
            excluded_providers=tuple(ProviderFamily),
        )
    assert cb.state == CircuitBreakerState.OPEN


def test_single_provider_and_boundary():
    """TC-04 Boundary: Single-provider air-gapped degradation, empty query, and 1M context window constraint."""
    single = resolve_cross_family_assignment(
        "Implement CheckoutPage POM workflow",
        available_providers=(ProviderFamily.LOCAL_OPENAI,),
    )
    assert single.primary_prover.provider == ProviderFamily.LOCAL_OPENAI
    assert single.adversarial_auditor.provider == ProviderFamily.LOCAL_OPENAI
    assert single.cross_family_isolated is False
    assert single.degradation_reason == "single_provider_available"

    offline = resolve_cross_family_assignment(
        "",
        available_providers=(),
    )
    assert offline.capability_tier == CapabilityTier.FAST_EXPLORER
    assert offline.cross_family_isolated is True
    assert offline.degradation_reason == "offline_default_catalog"

    high_ctx = resolve_cross_family_assignment(
        "Inspect large monorepo trace",
        available_providers=(ProviderFamily.ANTHROPIC, ProviderFamily.OPENAI, ProviderFamily.GEMINI),
        preferred_provider=ProviderFamily.ANTHROPIC,
        context_tokens=500_000,
    )
    # Anthropic 200k models cannot hold 500k context -> automatically selects >=500k model (OpenAI/Gemini)
    assert high_ctx.capability_tier == CapabilityTier.DEEP_ARCHITECT
    assert high_ctx.primary_prover.context_window >= 500_000


def test_m3_resilience_concurrent_cas_failover_and_legacy_compat():
    """M3 Resilience (TC-ADV-01): Concurrent threads tripping same failed_model_id transition exactly once."""
    cb = TokenCircuitBreaker(rate_limit_threshold=1)
    results = []
    lock = threading.Lock()

    def _worker():
        chosen = cb.route_failover_candidate(
            failed_model_id="gemini-4-neon",
            required_tier=CapabilityTier.DEEP_ARCHITECT,
            status_code=429,
        )
        with lock:
            results.append(chosen.model_id)

    threads = [threading.Thread(target=_worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    assert len(results) == 8
    assert len(set(results)) == 1, f"Concurrent CAS failover must select one deterministic hop, got {results}"

    # Legacy QAModelRouter contract remains 100% intact
    legacy_router = QAModelRouter()
    assert legacy_router.route_task("Perform root cause analysis on flaky test").recommended_model == "gemini-4-neon"
    assert legacy_router.route_task("Run ruff format").recommended_model == "gemini-3.8-flash"


# ==============================================================================
# Milestone 4: 5-Provider Dynamic Budgets, KV-Cache Prefix & Persona Tiers
# ==============================================================================


def test_m4_budgets_and_cache_positive_five_providers():
    """M4 Positive: DynamicBudgetEngine, CachePrefixEnforcer, and agents_manifest.json support all 5 providers."""
    from tools.core.cache_prefix_enforcer import CachePrefixEnforcer
    from tools.reasoning.dynamic_budget_engine import DynamicBudgetEngine

    rca_budget = DynamicBudgetEngine.resolve_budget(fsm_stage="AUTOPSY_HEAL")
    ds_payload = DynamicBudgetEngine.format_provider_payload(rca_budget, provider="deepseek")
    assert ds_payload["max_tokens"] == 4096
    assert len(ds_payload["stop"]) <= 4
    assert ds_payload["thinking"] == {"type": "enabled"}

    local_payload = DynamicBudgetEngine.format_provider_payload(rca_budget, provider="local_openai")
    assert local_payload["max_tokens"] == 4096
    assert len(local_payload["stop"]) <= 4
    assert local_payload["options"]["num_predict"] == 4096

    # KV-Cache prefix formatting across all 5 provider families
    sample_prompt = ("# Immutable Rule Prefix\n" * 300) + "\n<!-- DYNAMIC_PROMPT_BOUNDARY -->\nTask: audit login"
    part = CachePrefixEnforcer.partition_prompt(sample_prompt)
    assert part["is_cache_eligible"] is True

    ds_cache = CachePrefixEnforcer.format_provider_caching(part, provider="deepseek")
    assert ds_cache["prefix_cache_eligible"] is True
    assert ds_cache["messages"][0]["role"] == "system"
    assert ds_cache["messages"][1]["role"] == "user"

    oai_cache = CachePrefixEnforcer.format_provider_caching(part, provider="openai")
    assert oai_cache["prefix_cache_eligible"] is True
    assert oai_cache["messages"][0]["role"] == "system"

    local_cache = CachePrefixEnforcer.format_provider_caching(part, provider="local_openai")
    assert local_cache["keep_alive"] == "10m"
    assert local_cache["messages"][0]["role"] == "system"

    # Declarative persona & specialist capability tiers in agents_manifest.json
    manifest_p = os.path.join(REPO_ROOT, "agents_manifest.json")
    with open(manifest_p, "r", encoding="utf-8") as afh:
        adata = json.load(afh)

    valid_tiers = {t.value for t in CapabilityTier}
    for persona in adata["personas"]:
        assert persona.get("capability_tier") in valid_tiers, f"Missing capability_tier on {persona['id']}"
        assert isinstance(persona.get("requires_orthogonal_auditor"), bool)
    for spec in adata["specialists"]:
        assert spec.get("capability_tier") in valid_tiers, f"Missing capability_tier on {spec['id']}"

    gatekeeper = next(p for p in adata["personas"] if p["id"] == "quality-gatekeeper")
    assert gatekeeper["requires_orthogonal_auditor"] is True


def test_m4_budgets_and_cache_negative_unknown_provider_and_stop_limits():
    """M4 Negative: Stop-sequence limits enforced per provider and unknown providers use safe generic fallback."""
    from tools.reasoning.dynamic_budget_engine import DynamicBudgetEngine

    many_stops = [f"</s{i}>" for i in range(12)]
    cfg = {"max_tokens": 512, "thinking_budget": 1024, "stop_sequences": many_stops}
    assert len(DynamicBudgetEngine.format_provider_payload(cfg, provider="deepseek")["stop"]) == 4
    assert len(DynamicBudgetEngine.format_provider_payload(cfg, provider="local_openai")["stop"]) == 4
    assert len(DynamicBudgetEngine.format_provider_payload(cfg, provider="openai")["stop"]) == 4
    assert len(DynamicBudgetEngine.format_provider_payload(cfg, provider="gemini")["generationConfig"]["stopSequences"]) == 5
    assert len(DynamicBudgetEngine.format_provider_payload(cfg, provider="anthropic")["stop_sequences"]) == 10

    generic = DynamicBudgetEngine.format_provider_payload(cfg, provider="custom_unknown")
    assert generic["max_tokens"] == 512


def test_m4_budgets_and_cache_boundary_zero_thinking_budget():
    """M4 Boundary: Mechanical step with thinking_budget=0 disables DeepSeek thinking and omits local thinking."""
    from tools.reasoning.dynamic_budget_engine import DynamicBudgetEngine

    mech = DynamicBudgetEngine.resolve_budget(fsm_stage="DISCOVERY")
    assert mech["thinking_budget"] == 0
    ds_mech = DynamicBudgetEngine.format_provider_payload(mech, provider="deepseek")
    assert ds_mech["thinking"] == {"type": "disabled"}

    no_think_cfg = {"max_tokens": 256, "thinking_budget": 1024, "supports_thinking": False}
    local_no_think = DynamicBudgetEngine.format_provider_payload(no_think_cfg, provider="local_openai")
    assert "thinking" not in local_no_think


def test_m4_budgets_and_cache_cli_json():
    """M4 CLI: dynamic_budget_engine.py and cache_prefix_enforcer.py support --provider deepseek --json."""
    proc_budget = subprocess.run(
        [
            sys.executable,
            os.path.join(REPO_ROOT, "tools", "reasoning", "dynamic_budget_engine.py"),
            "--fsm-stage",
            "AUTOPSY_HEAL",
            "--provider",
            "deepseek",
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_budget.returncode == 0, proc_budget.stderr
    b_json = json.loads(proc_budget.stdout)
    assert b_json["provider_payload"]["thinking"] == {"type": "enabled"}

    proc_cache = subprocess.run(
        [
            sys.executable,
            os.path.join(REPO_ROOT, "tools", "core", "cache_prefix_enforcer.py"),
            "--provider",
            "deepseek",
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_cache.returncode == 0, proc_cache.stderr
    c_json = json.loads(proc_cache.stdout)
    assert "messages" in c_json["provider_payload"]


# ==============================================================================
# Milestone 5: Host Control Plane Wiring (super_plan_engine, fsm, solo_runner)
# ==============================================================================


def test_m5_control_plane_positive_hosts_fsm_and_purple(tmp_path):
    """M5 Positive: Multi-host routing across 8 hosts, FSM model binding, and Purple cross-family provenance."""
    from tools.core.fsm_enforcer import FsmEnforcer, resolve_actor_model_binding
    from tools.design.super_plan_engine import PlanningTier, calculate_risk_routing, detect_active_host
    from tools.orchestration.solo_runner import certify_purple_phase

    for host_key in ("antigravity", "codex", "claude", "cursor", "copilot", "windsurf", "deepseek", "local"):
        assert detect_active_host(host=host_key) == host_key
        tier, metric = calculate_risk_routing(
            "Architect distributed auth schema migration",
            target_files=["tools/core/model_registry.py"],
            repo_root=REPO_ROOT,
            host=host_key,
        )
        assert tier == PlanningTier.TIER_2_DEEP
        assert metric.detected_host == host_key
        assert len(metric.recommended_model) > 3

    ds_tier, ds_metric = calculate_risk_routing(
        "Architect distributed auth schema migration",
        target_files=["tools/core/model_registry.py"],
        repo_root=REPO_ROOT,
        host="deepseek",
    )
    assert "DeepSeek" in ds_metric.recommended_model

    local_tier, local_metric = calculate_risk_routing(
        "Update LoginPage helper",
        target_files=["tools/core/model_registry.py"],
        repo_root=REPO_ROOT,
        host="local",
    )
    assert "Ollama" in local_metric.recommended_model or "Local" in local_metric.recommended_model

    # FSM actor model binding & non-breaking compliance
    binding = resolve_actor_model_binding("quality-gatekeeper", repo_root=REPO_ROOT)
    assert binding["capability_tier"] == CapabilityTier.ADVERSARIAL_AUDITOR.value
    assert binding["requires_orthogonal_auditor"] is True

    fsm_state = tmp_path / "fsm_session.json"
    enforcer = FsmEnforcer(state_file=str(fsm_state))
    enforcer.start_session("M5_MULTI_MODEL_SESS")
    adv = enforcer.advance_stage("DISCOVERY", "live-explorer", {"selectors": ["#submit"]})
    assert adv["status"] == "PASS"
    assert adv["model_binding"]["capability_tier"] == CapabilityTier.FAST_EXPLORER.value

    # Purple phase receipt includes Cross-Family Adversarial Pairing metadata
    purple_receipt = tmp_path / "m5_purple.json"
    p_res = certify_purple_phase(
        target="HEAD",
        target_file="tools/core/model_registry.py",
        receipt_path=str(purple_receipt),
        repo_root=REPO_ROOT,
        check_neuro_symbolic=True,
    )
    assert "cross_model_pairing" in p_res
    pairing = p_res["cross_model_pairing"]
    assert pairing["primary_prover_provider"] != pairing["adversarial_auditor_provider"]
    assert pairing["cross_family_isolated"] is True


def test_m5_control_plane_negative_invalid_host():
    """M5 Negative: Unsupported host string raises ValueError cleanly."""
    from tools.design.super_plan_engine import detect_active_host

    with pytest.raises(ValueError, match="Unsupported host"):
        detect_active_host(host="unsupported_ide_xyz")


def test_m5_control_plane_boundary_env_and_model_inference(monkeypatch):
    """M5 Boundary: Detects DeepSeek, Local Ollama, Cursor, and Windsurf from active_model or env."""
    from tools.design.super_plan_engine import detect_active_host

    for key in ("SYNAPSE_HOST", "CODEX_THREAD_ID", "CLAUDECODE", "ANTIGRAVITY_AGENT"):
        monkeypatch.delenv(key, raising=False)

    assert detect_active_host(active_model="deepseek-r1") == "deepseek"
    assert detect_active_host(active_model="ollama-qwen3-coder") == "local"
    monkeypatch.setenv("SYNAPSE_HOST", "cursor")
    assert detect_active_host() == "cursor"
    monkeypatch.setenv("SYNAPSE_HOST", "windsurf")
    assert detect_active_host() == "windsurf"


def test_m5_control_plane_cli_route_json():
    """M5 CLI: super_plan_engine.py route --host deepseek/local --json exits 0 with provider-matched model."""
    for host_name, expected_token in (("deepseek", "DeepSeek"), ("local", "Local")):
        proc = subprocess.run(
            [
                sys.executable,
                os.path.join(REPO_ROOT, "tools", "design", "super_plan_engine.py"),
                "route",
                "--task",
                "Refactor CheckoutPage POM",
                "--host",
                host_name,
                "--json",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        payload = json.loads(proc.stdout)
        assert payload["detected_host"] == host_name
        assert expected_token in payload["recommended_model"]


# ==============================================================================
# Phase 2 Milestone 4: Live Cross-Family Semantic Judge in --purple & /review
# ==============================================================================


def test_cross_llm_positive_cli_bridge_and_gateway_merge(monkeypatch, tmp_path):
    """P2-M4 Positive: Opt-in --cross-llm merges CLI Bridge and HTTP Gateway findings into --purple and /review."""
    from tools.orchestration.ide_cli_bridge import CliBridgeFindingDTO, CliBridgeResultDTO
    from tools.orchestration.multi_model_gateway import StdlibGatewayResponseDTO
    from tools.orchestration.senior_code_review import evaluate_review, run_cross_llm_semantic_audit
    from tools.orchestration.solo_runner import certify_purple_phase

    sample_diff = "diff --git a/tools/demo.py b/tools/demo.py\n+token = 'abc'\n"
    monkeypatch.setattr(
        "tools.orchestration.senior_code_review.discover_local_cli_adapters",
        lambda preferred_order=(): {ProviderFamily.ANTHROPIC: "/usr/local/bin/claude"},
    )
    monkeypatch.setattr(
        "tools.orchestration.senior_code_review.invoke_readonly_cli_audit",
        lambda req, allow_live_subprocess=True: CliBridgeResultDTO(
            success=True,
            cli_binary="/usr/local/bin/claude",
            provider=ProviderFamily.ANTHROPIC,
            model_id="claude-opus-5.5",
            read_only_enforced=True,
            findings=(
                CliBridgeFindingDTO(
                    severity="Must fix",
                    category="security",
                    title="Hardcoded secret token",
                    file_path="tools/demo.py",
                    line_no=2,
                    rationale="Use os.environ for secret injection.",
                ),
            ),
            raw_summary="CLI audit detected 1 blocker.",
            error_code=None,
        ),
    )

    sem_res = run_cross_llm_semantic_audit(sample_diff, repo_root=str(tmp_path), cross_llm=True)
    assert sem_res.success is True
    assert sem_res.provider == ProviderFamily.ANTHROPIC
    assert sem_res.read_only_enforced is True
    assert len(sem_res.findings) == 1
    assert sem_res.findings[0].severity == "Must fix"

    monkeypatch.setattr("tools.orchestration.solo_runner.get_git_diff", lambda r, t: sample_diff)
    monkeypatch.setattr("tools.orchestration.solo_runner.parse_diff", lambda d: [{"path": "tools/demo.py", "added_lines": [(2, "token = 'abc'")], "removed_lines": []}])
    monkeypatch.setattr("tools.orchestration.solo_runner.analyze_diff", lambda f, r: ([], 0))
    purple_res = certify_purple_phase(
        target="uncommitted",
        target_file="tools/core/model_registry.py",
        receipt_path=str(tmp_path / "purple.json"),
        repo_root=REPO_ROOT,
        check_neuro_symbolic=False,
        cross_llm=True,
    )
    assert purple_res["cross_llm_audit"]["success"] is True
    assert purple_res["cross_llm_audit"]["provider"] == "anthropic"
    assert any(f.get("title") == "Hardcoded secret token" for f in purple_res["findings"])
    assert purple_res["passed"] is False

    # Verify evaluate_review merges Must fix finding when cross_llm=True
    monkeypatch.setattr("tools.orchestration.senior_code_review.get_git_diff", lambda r, t: sample_diff)
    monkeypatch.setattr("tools.orchestration.senior_code_review.parse_diff", lambda d: [])
    monkeypatch.setattr("tools.orchestration.senior_code_review.analyze_diff", lambda f, r: ([], 0))
    monkeypatch.setattr(
        "tools.orchestration.senior_code_review.audit_diff_bloat",
        lambda r, target="uncommitted": {"diff_bloat_passed": True, "diff_bloat_warnings": 0, "diff_bloat_violations": []},
    )
    exit_c, rev_payload, _, _ = evaluate_review(
        repo_dir=REPO_ROOT,
        target="uncommitted",
        write_receipt=False,
        cross_llm=True,
    )
    assert exit_c == 1
    assert rev_payload["verdict"] == "CHANGES_REQUESTED"
    assert rev_payload["cross_llm_audit"]["provider"] == "anthropic"
    assert any(f.get("title") == "Hardcoded secret token" for f in rev_payload["findings"])

    # Verify fallback to HTTP Gateway when no local CLI exists
    monkeypatch.setattr(
        "tools.orchestration.senior_code_review.discover_local_cli_adapters",
        lambda preferred_order=(): {},
    )
    monkeypatch.setattr(
        "tools.orchestration.senior_code_review.execute_stdlib_gateway_call",
        lambda req, available_providers=None: StdlibGatewayResponseDTO(
            success=True,
            provider="openai",
            model_id="gpt-6.2-astra",
            content="Gateway audit verified cleanly.",
            http_status=200,
            failover_attempts=0,
            error_code=None,
        ),
    )
    gw_audit = run_cross_llm_semantic_audit(
        sample_diff,
        repo_root=str(tmp_path),
        cross_llm=True,
        preferred_auditor=ProviderFamily.OPENAI,
    )
    assert gw_audit.success is True
    assert gw_audit.cli_binary == "stdlib_gateway"
    assert gw_audit.provider == ProviderFamily.OPENAI
    assert gw_audit.read_only_enforced is True


def test_cross_llm_negative_disabled_by_default(monkeypatch, tmp_path):
    """P2-M4 Negative: Cross-LLM audit stays opt-in disabled by default unless flag or env var is enabled."""
    from tools.orchestration.senior_code_review import evaluate_review, run_cross_llm_semantic_audit
    from tools.orchestration.solo_runner import certify_purple_phase

    monkeypatch.delenv("SYNAPSE_CROSS_LLM_AUDIT", raising=False)
    res = run_cross_llm_semantic_audit("diff --git a/x.py b/x.py\n+x=1\n", repo_root=str(tmp_path))
    assert res.success is False
    assert res.read_only_enforced is True
    assert res.error_code == "CROSS_LLM_DISABLED"

    monkeypatch.setattr("tools.orchestration.solo_runner.get_git_diff", lambda r, t: "")
    monkeypatch.setattr("tools.orchestration.solo_runner.parse_diff", lambda d: [])
    monkeypatch.setattr("tools.orchestration.solo_runner.analyze_diff", lambda f, r: ([], 0))
    purple_off = certify_purple_phase(
        target="uncommitted",
        target_file="tools/core/model_registry.py",
        receipt_path=str(tmp_path / "purple_off.json"),
        repo_root=REPO_ROOT,
        check_neuro_symbolic=False,
    )
    assert purple_off["cross_llm_audit"] is None

    monkeypatch.setattr("tools.orchestration.senior_code_review.get_git_diff", lambda r, t: "")
    monkeypatch.setattr("tools.orchestration.senior_code_review.parse_diff", lambda d: [])
    monkeypatch.setattr("tools.orchestration.senior_code_review.analyze_diff", lambda f, r: ([], 0))
    monkeypatch.setattr(
        "tools.orchestration.senior_code_review.audit_diff_bloat",
        lambda r, target="uncommitted": {"diff_bloat_passed": True, "diff_bloat_warnings": 0, "diff_bloat_violations": []},
    )
    _, rev_off, _, _ = evaluate_review(repo_dir=REPO_ROOT, target="uncommitted", write_receipt=False)
    assert "cross_llm_audit" not in rev_off


def test_cross_llm_boundary_and_resilience(monkeypatch, tmp_path):
    """TC-04 Boundary: Empty diff short-circuits cleanly and unavailable CLI+Gateway degrades gracefully."""
    from tools.orchestration.multi_model_gateway import StdlibGatewayResponseDTO
    from tools.orchestration.senior_code_review import run_cross_llm_semantic_audit

    empty_res = run_cross_llm_semantic_audit("   ", repo_root=str(tmp_path), cross_llm=True)
    assert empty_res.success is True
    assert empty_res.read_only_enforced is True
    assert empty_res.findings == ()
    assert empty_res.error_code is None

    monkeypatch.setattr(
        "tools.orchestration.senior_code_review.discover_local_cli_adapters",
        lambda preferred_order=(): {},
    )
    seen_gw_models = []

    def _fake_unavail_gw(req, available_providers=None):
        seen_gw_models.append(req.model_id)
        return StdlibGatewayResponseDTO(
            success=False,
            provider="none",
            model_id=req.model_id,
            content="",
            http_status=0,
            failover_attempts=0,
            error_code="GATEWAY_OPT_IN_REQUIRED",
        )

    monkeypatch.setattr("tools.orchestration.senior_code_review.execute_stdlib_gateway_call", _fake_unavail_gw)
    monkeypatch.setenv("SYNAPSE_CROSS_LLM_AUDIT", "1")
    unavail = run_cross_llm_semantic_audit(
        "diff --git a/a.py b/a.py\n+a = 1\n",
        repo_root=str(tmp_path),
    )
    assert unavail.success is False
    assert unavail.read_only_enforced is True
    assert unavail.error_code == "CROSS_LLM_UNAVAILABLE"
    assert seen_gw_models == ["claude-opus-5.5"]


def test_cross_llm_cli_flags_help():
    """P2-M4 CLI: --cross-llm flag is exposed cleanly on solo_runner.py and senior_code_review.py."""
    for rel in ("tools/orchestration/solo_runner.py", "tools/orchestration/senior_code_review.py"):
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO_ROOT, rel), "--help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        assert "--cross-llm" in proc.stdout


def test_cross_llm_cli_main_respects_flag_and_repo_root(monkeypatch, tmp_path, capsys):
    """P2-M4 CLI: solo_runner.main keeps cross_llm=False by default and respects non-parent _REPO_ROOT."""
    from tools.orchestration import senior_code_review as scr
    from tools.orchestration import solo_runner as sr

    td = tmp_path / "ext_repo"
    (td / ".git").mkdir(parents=True)
    wt = tmp_path / "unrelated_wt"
    wt.mkdir(parents=True)
    (wt / ".git").write_text("gitdir: /tmp/mock\n", encoding="utf-8")

    captured = {}

    def _fake_purple(**kwargs):
        captured["cross_llm"] = kwargs.get("cross_llm")
        return {"status": "CERTIFIED_PURPLE", "passed": True, "findings_count": 0}

    def _fake_eval(**kwargs):
        captured["review_root"] = kwargs.get("repo_dir")
        return 0, {"verdict": "APPROVED", "passed": True, "findings_count": 0}, [], {}

    monkeypatch.setattr(sr, "_REPO_ROOT", str(td))
    monkeypatch.setattr(sr, "certify_purple_phase", _fake_purple)
    monkeypatch.setattr(scr, "evaluate_review", _fake_eval)
    monkeypatch.chdir(wt)
    monkeypatch.setattr(sys, "argv", ["solo_runner.py", "--purple", "--json"])

    rc = sr.main()
    capsys.readouterr()
    assert rc == 0
    assert captured["cross_llm"] is False
    assert os.path.abspath(captured["review_root"]) == os.path.abspath(str(td))
