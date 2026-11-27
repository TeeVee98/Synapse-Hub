#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
4-Scenario TDD Verification Suite for Milestone 1 (ModelRegistry & models_manifest.json)
and Milestone 2 (Config Schema & Unified Token/Pricing Hydration).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
import os
import subprocess
import sys
import pytest

from tools.core.model_registry import (
    CapabilityTier,
    CrossModelAssignmentDTO,
    ModelRegistry,
    ModelSpecDTO,
    ProviderFamily,
    load_model_registry,
    normalize_provider_family,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ==============================================================================
# Milestone 1: Canonical models_manifest.json & Typed ModelRegistry (4 Scenarios)
# ==============================================================================


def test_registry_positive_five_providers_and_legacy_aliases(tmp_path):
    """TC-01 Positive: Validates canonical 5-provider manifest, frozen DTOs, legacy aliases, and config overrides."""
    manifest_path = os.path.join(REPO_ROOT, "models_manifest.json")
    assert os.path.isfile(manifest_path), "models_manifest.json must exist at repository root"

    with open(manifest_path, "rb") as raw_fh:
        raw_bytes = raw_fh.read()
    assert not raw_bytes.startswith(b"\xef\xbb\xbf"), "models_manifest.json must be UTF-8 without BOM"

    specs = load_model_registry(manifest_path=manifest_path)
    assert len(specs) == 18

    providers_seen = {spec.provider for spec in specs.values()}
    assert providers_seen == {
        ProviderFamily.GEMINI,
        ProviderFamily.ANTHROPIC,
        ProviderFamily.OPENAI,
        ProviderFamily.DEEPSEEK,
        ProviderFamily.LOCAL_OPENAI,
    }

    tiers_seen = {spec.capability_tier for spec in specs.values()}
    assert tiers_seen == {
        CapabilityTier.FAST_EXPLORER,
        CapabilityTier.CODE_WORKHORSE,
        CapabilityTier.DEEP_ARCHITECT,
        CapabilityTier.ADVERSARIAL_AUDITOR,
    }

    neon = specs["gemini-4-neon"]
    assert isinstance(neon, ModelSpecDTO)
    assert neon.provider == ProviderFamily.GEMINI
    assert neon.capability_tier == CapabilityTier.DEEP_ARCHITECT
    assert "Neon" in neon.display_name
    assert neon.auth_env_var == "GEMINI_API_KEY"
    assert neon.endpoint_protocol == "google_genai"
    assert neon.supports_thinking is True
    assert specs["gemini-3.8-flash"].supports_thinking is False
    assert neon.context_window >= 1_000_000
    assert neon.input_per_m == pytest.approx(3.00)

    with pytest.raises(FrozenInstanceError):
        neon.rank = 99  # type: ignore[misc]

    cfg_path = tmp_path / "synapse.config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "model_router": {
                    "models": {
                        "flash_lite": "deepseek-v4.1-flash",
                        "flash": "claude-sonnet-5.5",
                        "pro": "custom-openai-gpt-7-preview",
                        "auditor": "o3-custom-verifier",
                    },
                    "orchestration": {
                        "preferred_providers": ["anthropic", "openai"],
                        "cross_family_audit": True,
                        "gateway_opt_in": False,
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    reg = ModelRegistry(manifest_path=manifest_path, config_path=str(cfg_path))
    assert reg.resolve_legacy_tier_alias("flash_lite") == CapabilityTier.FAST_EXPLORER
    assert reg.resolve_legacy_tier_alias("flash") == CapabilityTier.CODE_WORKHORSE
    assert reg.resolve_legacy_tier_alias("pro") == CapabilityTier.DEEP_ARCHITECT
    assert reg.resolve_legacy_tier_alias("pro_reasoning") == CapabilityTier.DEEP_ARCHITECT

    assert reg.get_tier_override(CapabilityTier.FAST_EXPLORER) == "deepseek-v4.1-flash"
    assert reg.get_tier_override(CapabilityTier.CODE_WORKHORSE) == "claude-sonnet-5.5"
    assert reg.get_tier_override(CapabilityTier.DEEP_ARCHITECT) == "custom-openai-gpt-7-preview"
    custom_spec = reg.get_model("custom-openai-gpt-7-preview")
    assert custom_spec is not None
    assert custom_spec.provider == ProviderFamily.OPENAI
    assert custom_spec.supports_thinking is True
    o3_spec = reg.get_model("o3-custom-verifier")
    assert o3_spec is not None and o3_spec.provider == ProviderFamily.OPENAI
    assert reg.orchestration_policy["cross_family_audit"] is True
    assert reg.orchestration_policy["preferred_providers"] == ("anthropic", "openai")

    assignment = CrossModelAssignmentDTO(
        task_id="T-M1",
        execution_boundary="hybrid_control_plane_stdlib_gateway",
        capability_tier=CapabilityTier.DEEP_ARCHITECT,
        primary_prover=specs["gemini-4-neon"],
        adversarial_auditor=specs["claude-opus-5.5"],
        fallback_chain=("gpt-6.2-astra", "deepseek-r1"),
        cross_family_isolated=True,
        degradation_reason=None,
    )
    with pytest.raises(FrozenInstanceError):
        assignment.cross_family_isolated = False  # type: ignore[misc]
    assert assignment.to_dict()["cross_family_isolated"] is True
    assert assignment.primary_prover.provider != assignment.adversarial_auditor.provider


def test_registry_negative_malformed_manifest_and_invalid_override(tmp_path):
    """Negative: Corrupt manifest/config JSON falls back to built-in specs; invalid entries skipped; bad alias raises."""
    bad_manifest = tmp_path / "broken_manifest.json"
    bad_manifest.write_text("{corrupt json", encoding="utf-8")
    bad_cfg = tmp_path / "broken_cfg.json"
    bad_cfg.write_text('["not-an-object"]', encoding="utf-8")

    fallback_specs = load_model_registry(
        manifest_path=str(bad_manifest),
        config_path=str(bad_cfg),
    )
    assert "gemini-4-neon" in fallback_specs
    assert fallback_specs["gemini-4-neon"].supports_thinking is True
    assert fallback_specs["gemini-3.8-flash"].supports_thinking is False
    assert "claude-sonnet-5.5" in fallback_specs
    assert "gpt-6.2-sol" in fallback_specs
    assert "deepseek-r1" in fallback_specs
    assert "ollama-qwen3-coder" in fallback_specs

    # Manifest with partially invalid entries retains valid rows and skips invalid provider/tier rows
    partial_manifest = tmp_path / "partial_manifest.json"
    partial_manifest.write_text(
        json.dumps(
            {
                "models": [
                    {"model_id": "", "provider": "gemini", "capability_tier": "fast_explorer"},
                    {"model_id": "bad-prov", "provider": "", "capability_tier": "fast_explorer"},
                    {"model_id": "bad-tier", "provider": "gemini", "capability_tier": "unknown_xyz"},
                    {
                        "model_id": "valid-custom-gemini",
                        "provider": "gemini",
                        "capability_tier": "fast_explorer",
                        "rank": 1,
                        "context_window": 64000,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    partial_specs = load_model_registry(manifest_path=str(partial_manifest), config_path=str(bad_cfg))
    assert list(partial_specs.keys()) == ["valid-custom-gemini"]
    assert partial_specs["valid-custom-gemini"].supports_thinking is False
    assert partial_specs["valid-custom-gemini"].auth_env_var == "SYNAPSE_LLM_API_KEY"
    assert partial_specs["valid-custom-gemini"].endpoint_protocol == "openai_compatible"

    assert normalize_provider_family(None) is None
    assert normalize_provider_family("   ") is None
    assert normalize_provider_family(ProviderFamily.DEEPSEEK) == ProviderFamily.DEEPSEEK
    with pytest.raises(ValueError, match="Unsupported provider family"):
        normalize_provider_family("martian_llm")

    reg = ModelRegistry(manifest_path=str(bad_manifest), config_path=str(bad_cfg))
    assert reg.orchestration_policy["cross_family_audit"] is True
    with pytest.raises(ValueError, match="Unsupported capability tier"):
        reg.resolve_legacy_tier_alias("nonexistent_tier_xyz")


def test_registry_boundary_empty_env_zero_cost_local_and_adv03(tmp_path):
    """Boundary (TC-ADV-03): Empty env probing, falsey env flags, 0-cost local model, and context-window filtering."""
    reg = ModelRegistry(manifest_path=os.path.join(REPO_ROOT, "models_manifest.json"))

    avail_airgapped = reg.detect_available_providers(
        env={"SYNAPSE_LOCAL_LLM_URL": "http://127.0.0.1:11434/v1", "OPENAI_API_KEY": "false"},
        include_local_when_configured=True,
    )
    assert avail_airgapped == (ProviderFamily.LOCAL_OPENAI,)

    avail_no_local = reg.detect_available_providers(
        env={"SYNAPSE_LOCAL_LLM_URL": "http://127.0.0.1:11434/v1"},
        include_local_when_configured=False,
    )
    assert avail_no_local == ()

    avail_empty = reg.detect_available_providers(env={}, include_local_when_configured=True)
    assert avail_empty == ()

    local_candidates = reg.list_models(provider=ProviderFamily.LOCAL_OPENAI)
    assert len(local_candidates) == 2
    assert local_candidates[0].input_per_m == 0.0
    assert local_candidates[0].output_per_m == 0.0

    auditors = reg.list_models(tier=CapabilityTier.ADVERSARIAL_AUDITOR)
    assert len(auditors) >= 4
    assert all(m.capability_tier == CapabilityTier.ADVERSARIAL_AUDITOR for m in auditors)

    million_ctx = reg.list_models(min_context_window=1_000_000)
    assert len(million_ctx) >= 5
    assert all(m.context_window >= 1_000_000 for m in million_ctx)
    assert len(reg.get_tier_chain(CapabilityTier.DEEP_ARCHITECT)) >= 5


def test_registry_cli_json_and_idempotent_resilience():
    """CLI & Resilience (TC-ADV-01): Verifies --json CLI flag, exit code 0 & 2, idempotency, and zero secret leakage."""
    fake_secret = "sk-super-secret-do-not-leak-123456"
    child_env = dict(os.environ)
    child_env["OPENAI_API_KEY"] = fake_secret
    child_env["ANTHROPIC_API_KEY"] = "sk-ant-secret-789"

    script = os.path.join(REPO_ROOT, "tools", "core", "model_registry.py")
    cmd = [sys.executable, script, "--tier", "deep_architect", "--json"]
    proc1 = subprocess.run(cmd, cwd=REPO_ROOT, env=child_env, capture_output=True, text=True, check=False)
    proc2 = subprocess.run(cmd, cwd=REPO_ROOT, env=child_env, capture_output=True, text=True, check=False)

    assert proc1.returncode == 0, proc1.stderr
    assert proc2.returncode == 0, proc2.stderr
    assert fake_secret not in proc1.stdout
    assert "sk-ant-secret-789" not in proc1.stdout

    payload1 = json.loads(proc1.stdout)
    payload2 = json.loads(proc2.stdout)
    assert payload1["models"] == payload2["models"]
    assert "openai" in payload1["available_providers"]
    assert "anthropic" in payload1["available_providers"]
    assert all(item["capability_tier"] == "deep_architect" for item in payload1["models"])

    bad_cmd = [sys.executable, script, "--tier", "invalid_tier_999", "--json"]
    bad_proc = subprocess.run(bad_cmd, cwd=REPO_ROOT, env=child_env, capture_output=True, text=True, check=False)
    assert bad_proc.returncode == 2


# ==============================================================================
# Milestone 2: Config Schema & Unified Token/Pricing Hydration (4 Scenarios)
# ==============================================================================


def test_m2_config_hydration_positive():
    """M2 Positive: synapse.config.json, schema, and count_tokens.PRICING_TABLE align with ModelRegistry."""
    from tools.core import count_tokens

    cfg_path = os.path.join(REPO_ROOT, "synapse.config.json")
    schema_path = os.path.join(REPO_ROOT, "docs", "schemas", "synapse.config.schema.json")
    with open(cfg_path, "r", encoding="utf-8") as cfh:
        cfg = json.load(cfh)
    with open(schema_path, "r", encoding="utf-8") as sfh:
        schema = json.load(sfh)

    mr = cfg["model_router"]
    assert mr["models"]["flash_lite"] == "gemini-3.8-flash"
    assert mr["models"]["flash"] == "gemini-4-hydrogen"
    assert mr["models"]["pro"] == "gemini-4-neon"
    assert "orchestration" in mr
    assert mr["orchestration"]["cross_family_audit"] is True
    assert mr["orchestration"]["gateway_opt_in"] is False
    assert "deepseek" in mr["orchestration"]["preferred_providers"]

    mr_schema = schema["properties"]["model_router"]["properties"]
    assert "orchestration" in mr_schema
    assert "preferred_providers" in mr_schema["orchestration"]["properties"]

    manifest_specs = load_model_registry()
    for model_id, spec in manifest_specs.items():
        assert model_id in count_tokens.PRICING_TABLE, f"Missing hydrated model {model_id} in PRICING_TABLE"
        entry = count_tokens.PRICING_TABLE[model_id]
        assert entry["input_per_m"] == pytest.approx(spec.input_per_m)
        assert entry["output_per_m"] == pytest.approx(spec.output_per_m)


def test_m2_config_hydration_negative_unknown_model():
    """M2 Negative: Unknown model pricing query falls back safely to DEFAULT_MODEL without KeyError."""
    from tools.core import count_tokens

    res = count_tokens.calculate_cost(500_000, 0, 500_000, "unknown-vendor-model-999")
    assert res["total_cost_usd"] > 0.0
    assert res["model_name"] == count_tokens.PRICING_TABLE[count_tokens.DEFAULT_MODEL]["name"]


def test_m2_config_hydration_boundary_zero_tokens_local_model():
    """M2 Boundary: Local Ollama/vLLM hydrated model computes exact $0.00 cost across 0 and 1M tokens."""
    from tools.core import count_tokens

    local_specs = [s for s in load_model_registry().values() if s.provider == ProviderFamily.LOCAL_OPENAI]
    assert len(local_specs) >= 1
    local_id = local_specs[0].model_id
    cost_zero = count_tokens.calculate_cost(0, 0, 0, local_id)
    cost_million = count_tokens.calculate_cost(1_000_000, 500_000, 1_000_000, local_id)
    assert cost_zero["total_cost_usd"] == 0.0
    assert cost_million["total_cost_usd"] == 0.0


def test_m2_config_hydration_cli_json(tmp_path):
    """M2 CLI: count_tokens.py --pricing <hydrated_local_or_codex_model> --json succeeds with exit code 0."""
    transcript = tmp_path / "sample.jsonl"
    transcript.write_text(
        json.dumps({"type": "USER_INPUT", "source": "USER_EXPLICIT", "content": "<USER_REQUEST>ping</USER_REQUEST>"}) + "\n",
        encoding="utf-8",
    )
    local_id = next(s.model_id for s in load_model_registry().values() if s.provider == ProviderFamily.LOCAL_OPENAI)
    proc = subprocess.run(
        [
            sys.executable,
            os.path.join(REPO_ROOT, "tools", "core", "count_tokens.py"),
            "--file",
            str(transcript),
            "--pricing",
            local_id,
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["costs"]["total_cost_usd"] == 0.0


# ==============================================================================
# Phase 2 Milestone 1: Opt-In Live Manifest Discovery & Sync (4 Scenarios)
# ==============================================================================


class _MockDiscoveryResponse:
    def __init__(self, payload: dict) -> None:
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> "_MockDiscoveryResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def test_p2_m1_sync_manifest_positive_dry_run_and_write(tmp_path, monkeypatch):
    """P2-M1 Positive: sync_models_manifest_live discovers OpenAI/DeepSeek/Ollama models, preserves custom models, and writes when dry_run=False."""
    from dataclasses import FrozenInstanceError
    from tools.core.model_registry import ManifestSyncReportDTO, sync_models_manifest_live

    manifest_file = tmp_path / "models_manifest.json"
    manifest_file.write_text(
        json.dumps(
            {
                "version": "1.0",
                "models": [
                    {
                        "model_id": "custom-pinned-model",
                        "provider": "openai",
                        "display_name": "Custom Pinned",
                        "capability_tier": "code_workhorse",
                        "rank": 2,
                        "context_window": 128000,
                        "supports_thinking": False,
                        "input_per_m": 1.0,
                        "cache_per_m": 0.5,
                        "output_per_m": 2.0,
                        "auth_env_var": "OPENAI_API_KEY",
                        "endpoint_protocol": "openai_chat",
                    },
                    {
                        "model_id": "gpt-6.2-sol",
                        "provider": "openai",
                        "display_name": "OpenAI GPT-6.2 Sol",
                        "capability_tier": "code_workhorse",
                        "rank": 2,
                        "context_window": 1050000,
                        "supports_thinking": True,
                        "input_per_m": 2.0,
                        "cache_per_m": 1.0,
                        "output_per_m": 10.0,
                        "auth_env_var": "OPENAI_API_KEY",
                        "endpoint_protocol": "openai_chat",
                    },
                ],
                "default_tier_chains": {"code_workhorse": ["gpt-6.2-sol"]},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("OPENAI_API_KEY", "oai-sync-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-sync-key")
    monkeypatch.setenv("SYNAPSE_LOCAL_LLM_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    def _fake_urlopen(req, timeout=10.0):
        url = req.full_url
        if "api.openai.com" in url:
            return _MockDiscoveryResponse({"data": [{"id": "gpt-6.5-turbo-new"}]})
        if "api.deepseek.com" in url:
            return _MockDiscoveryResponse({"data": [{"id": "deepseek-v4.2-new"}]})
        if "11434" in url:
            return _MockDiscoveryResponse({"models": [{"name": "ollama-qwen3.5:32b"}]})
        raise AssertionError(f"Unexpected discovery URL: {url}")

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    dry_report = sync_models_manifest_live(manifest_path=str(manifest_file), dry_run=True, timeout_sec=8.0)
    assert isinstance(dry_report, ManifestSyncReportDTO)
    with pytest.raises(FrozenInstanceError):
        dry_report.dry_run = False  # type: ignore[misc]
    assert dry_report.dry_run is True
    assert dry_report.manifest_written is False
    assert dry_report.error_code is None
    assert "openai" in dry_report.synced_providers
    assert "deepseek" in dry_report.synced_providers
    assert "local_openai" in dry_report.synced_providers
    assert "gpt-6.5-turbo-new" in dry_report.added_models
    assert "deepseek-v4.2-new" in dry_report.added_models
    assert "ollama-qwen3.5:32b" in dry_report.added_models
    assert "gpt-6.2-sol" in dry_report.deprecated_models
    assert "custom-pinned-model" not in dry_report.deprecated_models

    # Real write mode updates manifest while preserving custom-pinned-model and existing metadata
    write_report = sync_models_manifest_live(manifest_path=str(manifest_file), dry_run=False, timeout_sec=8.0)
    assert write_report.dry_run is False
    assert write_report.manifest_written is True
    written_raw = manifest_file.read_bytes()
    assert not written_raw.startswith(b"\xef\xbb\xbf")
    written = json.loads(written_raw.decode("utf-8"))
    ids = {m["model_id"] for m in written["models"]}
    assert "custom-pinned-model" in ids
    assert "gpt-6.5-turbo-new" in ids
    assert "deepseek-v4.2-new" in ids
    assert "ollama-qwen3.5:32b" in ids


def test_p2_m1_sync_manifest_negative_network_error_and_missing_keys(tmp_path, monkeypatch):
    """P2-M1 Negative: Network errors or missing provider keys degrade safely without corrupting manifest."""
    import urllib.error
    from tools.core.model_registry import sync_models_manifest_live

    manifest_file = tmp_path / "models_manifest.json"
    manifest_file.write_text('{"version": "1.0", "models": []}', encoding="utf-8")

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "oai-fail-key")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("SYNAPSE_LOCAL_LLM_URL", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=10.0: (_ for _ in ()).throw(urllib.error.URLError("endpoint unreachable")),
    )
    report = sync_models_manifest_live(manifest_path=str(manifest_file), dry_run=False)
    assert report.manifest_written is False
    assert report.error_code == "NO_DISCOVERY_SOURCES"


def test_p2_m1_sync_manifest_boundary_clamped_timeout_and_empty_env(tmp_path, monkeypatch):
    """P2-M1 Boundary: Clamps excessive timeout <= 30s and handles zero credentials cleanly."""
    from tools.core.model_registry import sync_models_manifest_live

    for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "SYNAPSE_LOCAL_LLM_URL", "OLLAMA_HOST"):
        monkeypatch.delenv(k, raising=False)

    observed_timeouts = []

    def _capture_timeout(req, timeout=10.0):
        observed_timeouts.append(timeout)
        return _MockDiscoveryResponse({"data": [{"id": "gpt-6.2-sol"}]})

    monkeypatch.setattr("urllib.request.urlopen", _capture_timeout)
    empty_rep = sync_models_manifest_live(manifest_path=str(tmp_path / "missing.json"), dry_run=True, timeout_sec=120.0)
    assert empty_rep.synced_providers == ()
    assert empty_rep.error_code == "NO_DISCOVERY_SOURCES"

    monkeypatch.setenv("OPENAI_API_KEY", "oai-timeout-check")
    ok_rep = sync_models_manifest_live(manifest_path=str(tmp_path / "missing.json"), dry_run=True, timeout_sec=120.0)
    assert ok_rep.synced_providers == ("openai",)
    assert observed_timeouts == [30.0]


def test_p2_m1_sync_manifest_cli_dry_run_json(monkeypatch):
    """P2-M1 CLI: model_registry.py --sync-manifest --dry-run --json exits 0 with structured JSON without network when unconfigured."""
    child_env = dict(os.environ)
    for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "SYNAPSE_LOCAL_LLM_URL", "OLLAMA_HOST"):
        child_env.pop(k, None)

    proc = subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "tools", "core", "model_registry.py"), "--sync-manifest", "--dry-run", "--json"],
        cwd=REPO_ROOT,
        env=child_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["dry_run"] is True
    assert payload["manifest_written"] is False
    assert "synced_providers" in payload
