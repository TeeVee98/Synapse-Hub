<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0030: Hybrid Multi-Model Orchestration & Cross-Family Adversarial Pairing

### Status
Accepted

### Context
Model identifiers, pricing tables, stop-sequence caps, and fallback lists previously lived in six separate modules (`synapse.config.json`, `qa_model_router.py`, `circuit_breaker.py`, `dynamic_budget_engine.py`, `cache_prefix_enforcer.py`, `super_plan_engine.py`, and `count_tokens.py`), defaulting primarily to Google Gemini strings. That coupling created three operational risks:
1. Updating or adding models across Anthropic Claude, OpenAI/Codex, DeepSeek, or air-gapped Local Ollama/vLLM endpoints required synchronized edits across six files.
2. Running code synthesis (`/solo`) and post-code auditing (`--purple` / `/review`) on the same model family preserved correlated blind spots.
3. Headless CLI/CI runs lacked a zero-SDK multi-provider HTTP transport with tier-preserving failover.

### Decision
Adopt a three-part Multi-Model Orchestration architecture:
1. **Canonical `models_manifest.json` + `ModelRegistry` (`tools/core/model_registry.py`):** Store model metadata, token rates, context windows, thinking capabilities, and ordered tier chains across five provider families (`gemini`, `anthropic`, `openai`, `deepseek`, `local_openai`), supporting opt-in live discovery/sync (`sync_models_manifest_live`, `--sync-manifest`) while keeping `synapse.config.json::model_router.models` (`flash_lite`, `flash`, `pro`) 100% backward-compatible as user overrides.
2. **Capability-Tier Routing, Read-Only IDE Bridge & Cross-Family Pairing (`qa_model_router.py`, `circuit_breaker.py`, `ide_cli_bridge.py`, `senior_code_review.py`, `solo_runner.py`):** Bind tasks and `agents_manifest.json` personas to four logical tiers (`fast_explorer`, `code_workhorse`, `deep_architect`, `adversarial_auditor`). Pair an orthogonal `ProviderFamily` for `--purple` / `/review` verification when two or more providers are available, cascade across same-rank peer providers on HTTP 429/503 before stepping down, and support opt-in semantic auditing (`--cross-llm`) via the strictly read-only CLI bridge (`ide_cli_bridge.py`) before falling back to the HTTP gateway.
3. **Hybrid Control Plane + Opt-In Streaming Stdlib HTTP Gateway (`tools/orchestration/multi_model_gateway.py`, `tools/reasoning/dynamic_budget_engine.py`):** Keep IDE Host mode offline by default (`network_opt_in=False`), while providing a Python stdlib `urllib.request` gateway (`0` third-party packages, `<= 30s` socket timeout, secret header scrubbing, SSE streaming with normalized `NormalizedToolCallDTO` parsing and `detect_partial_stop_sequence` truncation) gated behind explicit opt-in (`SYNAPSE_GATEWAY_ENABLED=1` or `network_opt_in=True`).

### Consequences
- **Positive:** Eliminates single-vendor lock-in across IDE hosts and CI runners, enforces cross-family verification independence, supports opt-in read-only multi-CLI auditing & SSE streaming with zero external SDK dependencies, and unifies token cost tables.
- **Negative:** Introduces `models_manifest.json` as an additional root manifest whose schema and pricing entries must remain synchronized during major model refreshes; cross-family pairing requires at least two configured providers to avoid single-family fallback mode.
- **Compliance:** Enforced via `tests/test_model_registry.py`, `tests/test_ide_cli_bridge.py`, `tests/test_multi_model_orchestration.py`, `tests/test_multi_model_gateway.py`, and `tools/core/verify_all.py --mode hub --tier impact`.
