#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/core/model_registry.py — Canonical Multi-Provider Model Registry
----------------------------------------------------------------------
Zero-dependency registry loading `models_manifest.json` and merging
backward-compatible `synapse.config.json` overrides across 5 provider families:
  - Google Gemini (`gemini`)
  - Anthropic Claude (`anthropic`)
  - OpenAI / Codex (`openai`)
  - DeepSeek (`deepseek`)
  - Local OpenAI-Compatible (`local_openai` — Ollama / vLLM / LM Studio)
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from enum import Enum
import json
import os
import sys
from typing import Any, Dict, List, Mapping, Optional, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)


class ProviderFamily(str, Enum):
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    LOCAL_OPENAI = "local_openai"


class CapabilityTier(str, Enum):
    FAST_EXPLORER = "fast_explorer"
    CODE_WORKHORSE = "code_workhorse"
    DEEP_ARCHITECT = "deep_architect"
    ADVERSARIAL_AUDITOR = "adversarial_auditor"


@dataclass(frozen=True)
class ModelSpecDTO:
    model_id: str
    provider: ProviderFamily
    display_name: str
    capability_tier: CapabilityTier
    rank: int
    context_window: int
    supports_thinking: bool
    input_per_m: float
    cache_per_m: float
    output_per_m: float
    auth_env_var: str
    endpoint_protocol: str

    def to_public_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["provider"] = self.provider.value
        data["capability_tier"] = self.capability_tier.value
        return data


@dataclass(frozen=True)
class CrossModelAssignmentDTO:
    task_id: str
    execution_boundary: str
    capability_tier: CapabilityTier
    primary_prover: ModelSpecDTO
    adversarial_auditor: ModelSpecDTO
    fallback_chain: Tuple[str, ...]
    cross_family_isolated: bool
    degradation_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "execution_boundary": self.execution_boundary,
            "capability_tier": self.capability_tier.value,
            "primary_prover": self.primary_prover.to_public_dict(),
            "adversarial_auditor": self.adversarial_auditor.to_public_dict(),
            "fallback_chain": list(self.fallback_chain),
            "cross_family_isolated": self.cross_family_isolated,
            "degradation_reason": self.degradation_reason,
        }


@dataclass(frozen=True)
class PackagedCatalogResolutionDTO:
    manifest_path: str
    config_path: Optional[str]
    model_count: int
    used_builtin_fallback: bool


@dataclass(frozen=True)
class PackageParityReceiptDTO:
    source_model_ids: Tuple[str, ...]
    npm_model_ids: Tuple[str, ...]
    wheel_model_ids: Tuple[str, ...]
    tier_chains_equal: bool
    router_overrides_equal: bool


@dataclass(frozen=True)
class ManifestSyncReportDTO:
    synced_providers: Tuple[str, ...]
    discovered_models: Tuple[str, ...]
    added_models: Tuple[str, ...]
    deprecated_models: Tuple[str, ...]
    dry_run: bool
    manifest_written: bool
    error_code: Optional[str] = None


LEGACY_TIER_ALIASES: Dict[str, CapabilityTier] = {
    "flash_lite": CapabilityTier.FAST_EXPLORER,
    "fast_explorer": CapabilityTier.FAST_EXPLORER,
    "lite": CapabilityTier.FAST_EXPLORER,
    "flash": CapabilityTier.CODE_WORKHORSE,
    "code_workhorse": CapabilityTier.CODE_WORKHORSE,
    "workhorse": CapabilityTier.CODE_WORKHORSE,
    "pro": CapabilityTier.DEEP_ARCHITECT,
    "pro_reasoning": CapabilityTier.DEEP_ARCHITECT,
    "deep_architect": CapabilityTier.DEEP_ARCHITECT,
    "architect": CapabilityTier.DEEP_ARCHITECT,
    "adversarial_auditor": CapabilityTier.ADVERSARIAL_AUDITOR,
    "auditor": CapabilityTier.ADVERSARIAL_AUDITOR,
    "purple": CapabilityTier.ADVERSARIAL_AUDITOR,
}

PROVIDER_ALIASES: Dict[str, ProviderFamily] = {
    "gemini": ProviderFamily.GEMINI,
    "google": ProviderFamily.GEMINI,
    "antigravity": ProviderFamily.GEMINI,
    "anthropic": ProviderFamily.ANTHROPIC,
    "claude": ProviderFamily.ANTHROPIC,
    "openai": ProviderFamily.OPENAI,
    "codex": ProviderFamily.OPENAI,
    "deepseek": ProviderFamily.DEEPSEEK,
    "local": ProviderFamily.LOCAL_OPENAI,
    "local_openai": ProviderFamily.LOCAL_OPENAI,
    "ollama": ProviderFamily.LOCAL_OPENAI,
    "vllm": ProviderFamily.LOCAL_OPENAI,
}

_PROVIDER_ENV_PROBES: Tuple[Tuple[ProviderFamily, Tuple[str, ...]], ...] = (
    (ProviderFamily.GEMINI, ("GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTIGRAVITY_AGENT")),
    (ProviderFamily.ANTHROPIC, ("ANTHROPIC_API_KEY", "CLAUDECODE", "CLAUDE_CODE_SESSION_ID")),
    (ProviderFamily.OPENAI, ("OPENAI_API_KEY", "CODEX_THREAD_ID", "OPENAI_CODEX")),
    (ProviderFamily.DEEPSEEK, ("DEEPSEEK_API_KEY",)),
    (ProviderFamily.LOCAL_OPENAI, ("SYNAPSE_LOCAL_LLM_URL", "OLLAMA_HOST", "VLLM_BASE_URL")),
)

# Compact fallback rows: (id, provider, name, tier, rank, ctx, thinking_flag, in_m, cache_m, out_m, env, proto)
_FALLBACK_ROWS: Tuple[Tuple[str, str, str, str, int, int, int, float, float, float, str, str], ...] = (
    ("gemini-3.8-flash", "gemini", "Google Gemini 3.8 Flash", "fast_explorer", 1, 1048576, 0, 0.075, 0.01875, 0.30, "GEMINI_API_KEY", "google_genai"),
    ("gemini-4-hydrogen", "gemini", "Google Gemini 4 Hydrogen", "code_workhorse", 2, 1048576, 1, 1.50, 0.375, 7.50, "GEMINI_API_KEY", "google_genai"),
    ("gemini-4-neon", "gemini", "Google Gemini 4 Neon", "deep_architect", 3, 1048576, 1, 3.00, 0.15, 15.00, "GEMINI_API_KEY", "google_genai"),
    ("gemini-4-carbon", "gemini", "Google Gemini 4 Carbon", "adversarial_auditor", 3, 1048576, 1, 4.00, 0.20, 20.00, "GEMINI_API_KEY", "google_genai"),
    ("claude-sonnet-5.5", "anthropic", "Anthropic Claude Sonnet 5.5", "code_workhorse", 2, 200000, 1, 2.00, 0.20, 10.00, "ANTHROPIC_API_KEY", "anthropic_messages"),
    ("claude-opus-5.5", "anthropic", "Anthropic Claude Opus 5.5", "adversarial_auditor", 3, 200000, 1, 4.00, 0.40, 20.00, "ANTHROPIC_API_KEY", "anthropic_messages"),
    ("gpt-6.2-sol", "openai", "OpenAI GPT-6.2 Sol", "code_workhorse", 2, 1050000, 1, 2.00, 1.00, 10.00, "OPENAI_API_KEY", "openai_chat"),
    ("gpt-6.2-astra", "openai", "OpenAI GPT-6.2 Astra", "deep_architect", 3, 1050000, 1, 10.00, 5.00, 50.00, "OPENAI_API_KEY", "openai_chat"),
    ("deepseek-v4.1-flash", "deepseek", "DeepSeek-V4.1-Flash", "fast_explorer", 1, 1000000, 0, 0.30, 0.006, 1.20, "DEEPSEEK_API_KEY", "openai_compatible"),
    ("deepseek-r1", "deepseek", "DeepSeek R1", "adversarial_auditor", 3, 128000, 1, 0.55, 0.14, 2.19, "DEEPSEEK_API_KEY", "openai_compatible"),
    ("ollama-qwen3-coder", "local_openai", "Local Ollama Qwen3-Coder", "code_workhorse", 2, 131072, 1, 0.0, 0.0, 0.0, "SYNAPSE_LOCAL_LLM_URL", "openai_compatible"),
)


def _build_builtin_specs() -> Dict[str, ModelSpecDTO]:
    built: Dict[str, ModelSpecDTO] = {}
    for row in _FALLBACK_ROWS:
        mid, prov, name, tier_key, rank, ctx, think_flag, in_m, cache_m, out_m, env_k, proto = row
        built[mid] = ModelSpecDTO(
            model_id=mid,
            provider=ProviderFamily(prov),
            display_name=name,
            capability_tier=LEGACY_TIER_ALIASES[tier_key],
            rank=rank,
            context_window=ctx,
            supports_thinking=bool(think_flag),
            input_per_m=in_m,
            cache_per_m=cache_m,
            output_per_m=out_m,
            auth_env_var=env_k,
            endpoint_protocol=proto,
        )
    return built


def normalize_provider_family(raw: Optional[str]) -> Optional[ProviderFamily]:
    """Resolves a provider string or alias into ProviderFamily, or None if empty."""
    if raw is None:
        return None
    if isinstance(raw, ProviderFamily):
        return raw
    cleaned = str(raw).strip().lower().replace("-", "_")
    if not cleaned:
        return None
    resolved = PROVIDER_ALIASES.get(cleaned)
    if resolved is None:
        raise ValueError(f"Unsupported provider family '{raw}'.")
    return resolved


def _parse_model_spec_entry(item: Mapping[str, Any]) -> Optional[ModelSpecDTO]:
    """Converts one manifest JSON entry into an immutable ModelSpecDTO, or None if invalid."""
    model_id = str(item.get("model_id", "")).strip()
    if not model_id:
        return None
    try:
        provider = normalize_provider_family(str(item.get("provider", "")))
    except ValueError:
        return None
    tier = LEGACY_TIER_ALIASES.get(str(item.get("capability_tier", "")).strip().lower())
    if provider is None or tier is None:
        return None
    return ModelSpecDTO(
        model_id=model_id,
        provider=provider,
        display_name=str(item.get("display_name") or model_id),
        capability_tier=tier,
        rank=max(1, min(3, int(item.get("rank", 2)))),
        context_window=max(1024, int(item.get("context_window", 128000))),
        supports_thinking=bool(item.get("supports_thinking", False)),
        input_per_m=max(0.0, float(item.get("input_per_m", 0.0))),
        cache_per_m=max(0.0, float(item.get("cache_per_m", 0.0))),
        output_per_m=max(0.0, float(item.get("output_per_m", 0.0))),
        auth_env_var=str(item.get("auth_env_var") or "SYNAPSE_LLM_API_KEY"),
        endpoint_protocol=str(item.get("endpoint_protocol") or "openai_compatible"),
    )


def _read_json_dict(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, ValueError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


def resolve_packaged_resource_path(
    filename: str,
    explicit_path: Optional[str] = None,
    repo_root: Optional[str] = None,
) -> Optional[str]:
    """Resolves a packaged resource via explicit path -> repo root -> tools root -> importlib.resources."""
    if not filename:
        return None
    clean_name = str(filename).strip()
    if not clean_name:
        return None
    if explicit_path:
        cleaned_explicit = str(explicit_path).strip()
        return cleaned_explicit if os.path.isfile(cleaned_explicit) else None

    search_dirs = (
        *(d for d in (repo_root, _REPO_ROOT) if d),
        *(os.path.join(d, "tools") for d in (repo_root, _REPO_ROOT) if d),
        _TOOLS_ROOT,
        os.path.join(_TOOLS_ROOT, "core"),
    )
    for base_dir in search_dirs:
        cand = os.path.join(base_dir, clean_name)
        if os.path.isfile(cand):
            return cand

    try:
        import importlib.resources as pkg_resources

        resource = pkg_resources.files("tools").joinpath(clean_name)
        if resource.is_file():
            r_str = str(resource)
            if os.path.isfile(r_str):
                return r_str
            with pkg_resources.as_file(resource) as extracted:
                return str(extracted)
    except (ImportError, AttributeError, TypeError, OSError):
        return None
    return None


def _synthesize_custom_override_spec(model_id: str, tier: CapabilityTier) -> ModelSpecDTO:
    """Synthesizes a safe ModelSpecDTO when synapse.config.json specifies a custom model ID."""
    low = model_id.lower()
    if any(tok in low for tok in ("claude", "haiku", "sonnet", "opus")):
        provider, proto, env_key = ProviderFamily.ANTHROPIC, "anthropic_messages", "ANTHROPIC_API_KEY"
    elif "gpt" in low or low.startswith(("o1", "o3", "o4")) or "codex" in low:
        provider, proto, env_key = ProviderFamily.OPENAI, "openai_chat", "OPENAI_API_KEY"
    elif "deepseek" in low:
        provider, proto, env_key = ProviderFamily.DEEPSEEK, "openai_compatible", "DEEPSEEK_API_KEY"
    elif any(tok in low for tok in ("ollama", "vllm", "local")):
        provider, proto, env_key = ProviderFamily.LOCAL_OPENAI, "openai_compatible", "SYNAPSE_LOCAL_LLM_URL"
    else:
        provider, proto, env_key = ProviderFamily.GEMINI, "google_genai", "GEMINI_API_KEY"
    rank = 1 if tier == CapabilityTier.FAST_EXPLORER else (2 if tier == CapabilityTier.CODE_WORKHORSE else 3)
    return ModelSpecDTO(
        model_id=model_id,
        provider=provider,
        display_name=model_id,
        capability_tier=tier,
        rank=rank,
        context_window=128000,
        supports_thinking=rank >= 3,
        input_per_m=0.0,
        cache_per_m=0.0,
        output_per_m=0.0,
        auth_env_var=env_key,
        endpoint_protocol=proto,
    )


class ModelRegistry:
    """Zero-dependency canonical model catalog with legacy synapse.config.json override support."""

    def __init__(
        self,
        manifest_path: Optional[str] = None,
        config_path: Optional[str] = None,
    ) -> None:
        self.manifest_path = (
            manifest_path
            or resolve_packaged_resource_path("models_manifest.json")
            or os.path.join(_REPO_ROOT, "models_manifest.json")
        )
        self.config_path = (
            config_path
            or resolve_packaged_resource_path("synapse.config.json")
            or os.path.join(_REPO_ROOT, "synapse.config.json")
        )
        self._specs: Dict[str, ModelSpecDTO] = {}
        self._tier_chains: Dict[CapabilityTier, Tuple[str, ...]] = {}
        self._tier_overrides: Dict[CapabilityTier, str] = {}
        self.orchestration_policy: Dict[str, Any] = {
            "strategy": "capability_tier_cross_family_pairing",
            "execution_boundary": "hybrid_control_plane_stdlib_gateway",
            "preferred_providers": ("gemini", "anthropic", "openai", "deepseek", "local_openai"),
            "cross_family_audit": True,
            "gateway_opt_in": False,
            "local_endpoint_url": "http://127.0.0.1:11434/v1",
        }
        self._load_manifest()
        self._load_config_overrides()

    def _load_manifest(self) -> None:
        raw = _read_json_dict(self.manifest_path)
        loaded: Dict[str, ModelSpecDTO] = {}
        if raw and isinstance(raw.get("models"), list):
            for entry in raw["models"]:
                if isinstance(entry, Mapping):
                    parsed = _parse_model_spec_entry(entry)
                    if parsed is not None:
                        loaded[parsed.model_id] = parsed
        self.used_builtin_fallback = not bool(loaded)
        self._specs = loaded if loaded else _build_builtin_specs()
        chains = raw.get("default_tier_chains") if raw else None
        if isinstance(chains, Mapping):
            for raw_tier, model_list in chains.items():
                tier = LEGACY_TIER_ALIASES.get(str(raw_tier).strip().lower())
                if tier is not None and isinstance(model_list, list):
                    cleaned = tuple(str(m).strip() for m in model_list if str(m).strip())
                    if cleaned:
                        self._tier_chains[tier] = cleaned

    def _load_config_overrides(self) -> None:
        cfg = _read_json_dict(self.config_path)
        if not cfg:
            return
        router_cfg = cfg.get("model_router")
        if not isinstance(router_cfg, Mapping):
            return
        raw_models = router_cfg.get("models") if isinstance(router_cfg.get("models"), Mapping) else router_cfg
        if isinstance(raw_models, Mapping):
            for key, val in raw_models.items():
                if not isinstance(val, str) or not val.strip():
                    continue
                tier = LEGACY_TIER_ALIASES.get(str(key).strip().lower())
                if tier is None:
                    continue
                clean_id = val.strip()
                self._tier_overrides[tier] = clean_id
                if clean_id not in self._specs:
                    self._specs[clean_id] = _synthesize_custom_override_spec(clean_id, tier)

        orch = router_cfg.get("orchestration")
        if isinstance(orch, Mapping):
            self._apply_orchestration_overrides(orch)

    def _apply_orchestration_overrides(self, orch: Mapping[str, Any]) -> None:
        for str_key in ("strategy", "execution_boundary", "local_endpoint_url"):
            val = orch.get(str_key)
            if isinstance(val, str) and val.strip():
                self.orchestration_policy[str_key] = val.strip()
        for bool_key in ("cross_family_audit", "gateway_opt_in"):
            if isinstance(orch.get(bool_key), bool):
                self.orchestration_policy[bool_key] = bool(orch[bool_key])
        prefs = orch.get("preferred_providers")
        if isinstance(prefs, list):
            valid_prefs: List[str] = []
            for item in prefs:
                try:
                    fam = normalize_provider_family(str(item))
                except ValueError:
                    fam = None
                if fam is not None and fam.value not in valid_prefs:
                    valid_prefs.append(fam.value)
            if valid_prefs:
                self.orchestration_policy["preferred_providers"] = tuple(valid_prefs)

    @property
    def specs(self) -> Dict[str, ModelSpecDTO]:
        return dict(self._specs)

    def get_resolution_receipt(self) -> PackagedCatalogResolutionDTO:
        return PackagedCatalogResolutionDTO(
            manifest_path=self.manifest_path,
            config_path=self.config_path if os.path.isfile(self.config_path) else None,
            model_count=len(self._specs),
            used_builtin_fallback=self.used_builtin_fallback,
        )

    def get_model(self, model_id: str) -> Optional[ModelSpecDTO]:
        return self._specs.get(str(model_id or "").strip())

    def resolve_legacy_tier_alias(self, alias: str) -> CapabilityTier:
        """Maps legacy (`flash_lite`, `flash`, `pro`) and canonical tier names to CapabilityTier."""
        cleaned = str(alias or "").strip().lower()
        tier = LEGACY_TIER_ALIASES.get(cleaned)
        if tier is None:
            raise ValueError(
                f"Unsupported capability tier '{alias}'. Expected one of: {sorted(LEGACY_TIER_ALIASES.keys())}"
            )
        return tier

    def get_tier_override(self, tier: CapabilityTier) -> Optional[str]:
        return self._tier_overrides.get(tier)

    def get_tier_chain(self, tier: CapabilityTier) -> Tuple[str, ...]:
        chain = list(self._tier_chains.get(tier, ()))
        for spec in self._specs.values():
            if spec.capability_tier == tier and spec.model_id not in chain:
                chain.append(spec.model_id)
        return tuple(chain)

    def detect_available_providers(
        self,
        env: Optional[Mapping[str, str]] = None,
        include_local_when_configured: bool = True,
    ) -> Tuple[ProviderFamily, ...]:
        """Detects configured provider families by env key presence without reading raw secrets into logs."""
        effective_env = os.environ if env is None else env
        detected: List[ProviderFamily] = []
        for family, env_keys in _PROVIDER_ENV_PROBES:
            if family == ProviderFamily.LOCAL_OPENAI and not include_local_when_configured:
                continue
            has_signal = any(
                bool(str(effective_env.get(k, "")).strip())
                and str(effective_env.get(k, "")).strip().lower() not in ("0", "false", "no")
                for k in env_keys
            )
            if has_signal and family not in detected:
                detected.append(family)
        return tuple(detected)

    def list_models(
        self,
        provider: Optional[ProviderFamily] = None,
        tier: Optional[CapabilityTier] = None,
        min_context_window: int = 0,
    ) -> List[ModelSpecDTO]:
        out: List[ModelSpecDTO] = []
        for spec in self._specs.values():
            if provider is not None and spec.provider != provider:
                continue
            if tier is not None and spec.capability_tier != tier:
                continue
            if spec.context_window < min_context_window:
                continue
            out.append(spec)
        return out


def load_model_registry(
    manifest_path: Optional[str] = None,
    config_path: Optional[str] = None,
) -> Dict[str, ModelSpecDTO]:
    """Loads canonical models_manifest.json merged with backward-compatible synapse.config.json overrides."""
    return ModelRegistry(manifest_path=manifest_path, config_path=config_path).specs


_CLOUD_DISCOVERY_SPECS: Tuple[Tuple[ProviderFamily, str, str, str, str], ...] = (
    (ProviderFamily.OPENAI, "OPENAI_API_KEY", "https://api.openai.com/v1/models", "Authorization", "Bearer "),
    (ProviderFamily.DEEPSEEK, "DEEPSEEK_API_KEY", "https://api.deepseek.com/models", "Authorization", "Bearer "),
    (ProviderFamily.ANTHROPIC, "ANTHROPIC_API_KEY", "https://api.anthropic.com/v1/models", "x-api-key", ""),
    (ProviderFamily.GEMINI, "GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/models", "x-goog-api-key", ""),
)


def _extract_discovered_model_ids(payload: Mapping[str, Any]) -> Tuple[str, ...]:
    rows = payload.get("data") or payload.get("models") or ()
    cleaned = [
        str(item.get("id") or item.get("name") or "").strip().removeprefix("models/")
        for item in rows
        if isinstance(item, Mapping)
    ]
    return tuple(dict.fromkeys(mid for mid in cleaned if mid))


def _probe_discovery_sources(timeout_sec: float) -> Tuple[Tuple[str, ...], Dict[str, ProviderFamily]]:
    import urllib.error
    import urllib.request

    targets: List[Tuple[ProviderFamily, str, Dict[str, str]]] = [
        (fam, url, {hdr: f"{prefix}{os.environ[env_k].strip()}"})
        for fam, env_k, url, hdr, prefix in _CLOUD_DISCOVERY_SPECS
        if os.environ.get(env_k, "").strip()
    ]
    local_raw = (os.environ.get("SYNAPSE_LOCAL_LLM_URL") or os.environ.get("OLLAMA_HOST") or "").strip()
    if local_raw:
        base = local_raw[:-3] if local_raw.endswith("/v1") else local_raw
        targets.append((ProviderFamily.LOCAL_OPENAI, f"{base.rstrip('/')}/api/tags", {}))

    synced: List[str] = []
    discovered: Dict[str, ProviderFamily] = {}
    for family, url, hdrs in targets:
        req = urllib.request.Request(url=url, headers=hdrs, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:  # nosec B310
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            continue
        synced.append(family.value)
        for mid in _extract_discovered_model_ids(data):
            discovered[mid] = family

    return tuple(synced), discovered


def sync_models_manifest_live(
    manifest_path: Optional[str] = None,
    dry_run: bool = True,
    timeout_sec: float = 10.0,
) -> ManifestSyncReportDTO:
    """Explicit opt-in live discovery syncing OpenAI/DeepSeek/Ollama/Gemini/Anthropic model lists into models_manifest.json."""
    clamped_timeout = min(30.0, float(timeout_sec))
    synced, discovered = _probe_discovery_sources(clamped_timeout)
    if not synced:
        return ManifestSyncReportDTO(
            synced_providers=(),
            discovered_models=(),
            added_models=(),
            deprecated_models=(),
            dry_run=dry_run,
            manifest_written=False,
            error_code="NO_DISCOVERY_SOURCES",
        )

    target_path = (
        manifest_path
        or resolve_packaged_resource_path("models_manifest.json")
        or os.path.join(_REPO_ROOT, "models_manifest.json")
    )
    manifest_obj = _read_json_dict(target_path) or {"version": "1.0", "models": []}
    raw_models = list(manifest_obj.get("models", []))
    existing_ids = {str(m.get("model_id", "")).strip() for m in raw_models if isinstance(m, Mapping)}
    synced_set = set(synced)

    added = tuple(mid for mid in discovered if mid not in existing_ids)
    deprecated = tuple(
        str(m.get("model_id"))
        for m in raw_models
        if isinstance(m, Mapping)
        and str(m.get("provider", "")) in synced_set
        and str(m.get("model_id", "")) not in discovered
        and not str(m.get("model_id", "")).startswith("custom-")
    )

    written = False
    if not dry_run:
        for mid in added:
            spec = _synthesize_custom_override_spec(mid, CapabilityTier.CODE_WORKHORSE)
            raw_models.append(spec.to_public_dict())
        manifest_obj["models"] = raw_models
        with open(target_path, "w", encoding="utf-8") as fh:
            json.dump(manifest_obj, fh, indent=2)
        written = True

    return ManifestSyncReportDTO(
        synced_providers=synced,
        discovered_models=tuple(discovered.keys()),
        added_models=added,
        deprecated_models=deprecated,
        dry_run=dry_run,
        manifest_written=written,
        error_code=None,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Synapse Hub Multi-Provider Model Registry")
    parser.add_argument("--manifest", help="Optional path to models_manifest.json")
    parser.add_argument("--config", help="Optional path to synapse.config.json")
    parser.add_argument("--provider", help="Filter models by provider family")
    parser.add_argument("--tier", help="Filter models by capability tier or legacy alias")
    _a5 = parser.add_argument("--min-context", type=int, default=0, help="Minimum context window tokens")
    _a6 = parser.add_argument("--sync-manifest", action="store_true", help="Opt-in live discovery syncing model catalog")
    _a7 = parser.add_argument("--dry-run", action="store_true", help="Preview manifest sync without writing disk")
    _a8 = parser.add_argument("--json", action="store_true", help="Emit deterministic JSON summary")
    args = parser.parse_args()

    if args.sync_manifest:
        rep = sync_models_manifest_live(manifest_path=args.manifest, dry_run=bool(args.dry_run))
        print(json.dumps(asdict(rep), indent=2))
        return 0

    try:
        reg = ModelRegistry(manifest_path=args.manifest, config_path=args.config)
        prov_filter = normalize_provider_family(args.provider) if args.provider else None
        tier_filter = reg.resolve_legacy_tier_alias(args.tier) if args.tier else None
    except ValueError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, indent=2))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 2

    models = reg.list_models(
        provider=prov_filter,
        tier=tier_filter,
        min_context_window=max(0, int(args.min_context)),
    )
    avail = [p.value for p in reg.detect_available_providers()]
    payload = {
        "available_providers": avail,
        "orchestration_policy": {
            k: list(v) if isinstance(v, tuple) else v
            for k, v in reg.orchestration_policy.items()
        },
        "models_count": len(models),
        "models": [m.to_public_dict() for m in models],
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Synapse Hub Model Registry ({len(models)} models | available providers: {', '.join(avail) or 'offline-default'})")
    for spec in models:
        print(f"  - {spec.model_id} [{spec.provider.value} | {spec.capability_tier.value} | ctx={spec.context_window}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
