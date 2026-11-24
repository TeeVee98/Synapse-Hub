# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""Unit tests for QAModelRouter (tests/test_qa_model_router.py).

Verifies semantic heuristic classification, cost ratio calculation,
and context length escalation.

Author: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
License: MIT
"""

import json
import pytest

from tools.reasoning.qa_model_router import (
    ModelComputeTier,
    ModelRouteDecision,
    QAModelRouter,
)


@pytest.fixture
def router():
    return QAModelRouter()


def test_complex_rca_routed_to_pro(router):
    decision = router.route_task("Perform root cause analysis on flaky test_checkout locator failure")
    assert isinstance(decision, ModelRouteDecision)
    assert decision.tier == ModelComputeTier.PRO_REASONING
    assert decision.recommended_model == "gemini-4-neon"
    assert decision.estimated_cost_ratio == 1.0
    assert "root cause" in decision.reason.lower() or "flaky" in decision.reason.lower()


def test_pom_refactoring_routed_to_pro(router):
    decision = router.route_task("Refactor LoginPage POM design to eliminate duplicate selectors")
    assert decision.tier == ModelComputeTier.PRO_REASONING
    assert decision.recommended_model == "gemini-4-neon"


def test_lightweight_lint_routed_to_flash_lite(router):
    decision = router.route_task("Run ruff format and check clean encoding")
    assert decision.tier == ModelComputeTier.FLASH_LITE
    assert decision.recommended_model == "gemini-3.8-flash"
    assert decision.estimated_cost_ratio == 0.05


def test_standard_test_run_routed_to_flash(router):
    decision = router.route_task("Execute pytest tests/test_login.py with coverage report")
    assert decision.tier == ModelComputeTier.FLASH
    assert decision.recommended_model == "gemini-4-hydrogen"
    assert decision.estimated_cost_ratio == 0.20


def test_large_context_escalates_to_pro(router):
    # Standard task description, but large context load
    decision = router.route_task("Check test summary", context_tokens=45000)
    assert decision.tier == ModelComputeTier.PRO_REASONING
    assert "High context load" in decision.reason


def test_boundary_empty_query_defaults_to_lite(router):
    decision = router.route_task("")
    assert decision.tier == ModelComputeTier.FLASH_LITE


def test_extract_intended_qa_action(router):
    assert router.extract_intended_qa_action("Chạy fast gate ngay lập tức") == "fast-gate"
    assert router.extract_intended_qa_action("Quét pass ảo và nuốt lỗi") == "infer-lint"
    assert router.extract_intended_qa_action("Kiểm tra Clean POM kiến trúc") == "clean-pom"
    assert router.extract_intended_qa_action("Chẩn đoán môi trường doctor") == "doctor"
    assert router.extract_intended_qa_action("Chạy 10 quality gates toàn diện") == "hub-verify"
    assert router.extract_intended_qa_action("Một câu hỏi lý thuyết bình thường") is None
    assert router.extract_intended_qa_action("") is None


def test_degraded_fallback_model(router):
    fb_pro = router.get_degraded_fallback_model(ModelComputeTier.PRO_REASONING)
    assert fb_pro == "gemini-4-hydrogen"

    fb_flash = router.get_degraded_fallback_model(ModelComputeTier.FLASH)
    assert fb_flash == "gemini-3.8-flash"

    fb_lite = router.get_degraded_fallback_model(ModelComputeTier.FLASH_LITE)
    assert fb_lite == "gemini-3.8-flash"


def test_config_override_nested_model_router_models(tmp_path):
    """M1 Positive: Loads model overrides from model_router.models in synapse.config.json."""
    cfg_file = tmp_path / "synapse.config.json"
    cfg_file.write_text(
        json.dumps(
            {
                "model_router": {
                    "models": {
                        "flash_lite": "gemini-3.0-flash-lite",
                        "flash": "gemini-3.0-flash",
                        "pro": "gemini-3.0-pro",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    custom_router = QAModelRouter(config_path=str(cfg_file))

    assert custom_router.route_task("").recommended_model == "gemini-3.0-flash-lite"
    assert custom_router.route_task("Run ruff format").recommended_model == "gemini-3.0-flash-lite"
    assert custom_router.route_task("Run login suite").recommended_model == "gemini-3.0-flash"
    assert custom_router.route_task("Perform root cause analysis").recommended_model == "gemini-3.0-pro"
    assert custom_router.route_task("Check test summary", context_tokens=45000).recommended_model == "gemini-3.0-pro"

    assert custom_router.get_degraded_fallback_model(ModelComputeTier.PRO_REASONING) == "gemini-3.0-flash"
    assert custom_router.get_degraded_fallback_model(ModelComputeTier.FLASH) == "gemini-3.0-flash-lite"
    assert custom_router.get_degraded_fallback_model(ModelComputeTier.FLASH_LITE) == "gemini-3.0-flash-lite"


def test_config_override_flat_and_top_level_models(tmp_path):
    """M1 Positive: Supports both flat model_router section and top-level models section."""
    flat_cfg = tmp_path / "flat.json"
    flat_cfg.write_text(
        json.dumps({"model_router": {"pro_reasoning": "gemini-4-neon-high"}}),
        encoding="utf-8",
    )
    flat_router = QAModelRouter(config_path=str(flat_cfg))
    assert flat_router.route_task("root cause race condition").recommended_model == "gemini-4-neon-high"
    # Unspecified tiers preserve defaults
    assert flat_router.route_task("Run login suite").recommended_model == "gemini-2.5-flash"
    assert flat_router.route_task("").recommended_model == "gemini-2.5-flash-lite"

    top_cfg = tmp_path / "top.json"
    top_cfg.write_text(
        json.dumps({"models": {"flash": "gemini-4-hydrogen-medium"}}),
        encoding="utf-8",
    )
    top_router = QAModelRouter(config_path=str(top_cfg))
    assert top_router.route_task("Run login suite").recommended_model == "gemini-4-hydrogen-medium"
    assert top_router.get_degraded_fallback_model(ModelComputeTier.PRO_REASONING) == "gemini-4-hydrogen-medium"


def test_config_fallback_on_missing_or_malformed_config(tmp_path):
    """M1 Negative/Boundary: Missing, malformed, non-dict, or blank overrides fall back cleanly to defaults."""
    # Missing file
    missing_router = QAModelRouter(config_path=str(tmp_path / "does_not_exist.json"))
    assert missing_router.route_task("root cause").recommended_model == "gemini-2.5-pro"

    # Malformed JSON
    bad_json = tmp_path / "malformed.json"
    bad_json.write_text("{broken json", encoding="utf-8")
    malformed_router = QAModelRouter(config_path=str(bad_json))
    assert malformed_router.route_task("root cause").recommended_model == "gemini-2.5-pro"

    # Non-dict JSON root
    list_json = tmp_path / "list.json"
    list_json.write_text('["not", "a", "dict"]', encoding="utf-8")
    list_router = QAModelRouter(config_path=str(list_json))
    assert list_router.route_task("Run login suite").recommended_model == "gemini-2.5-flash"

    # Blank / non-string / unknown tier entries ignored
    invalid_vals = tmp_path / "invalid_vals.json"
    invalid_vals.write_text(
        json.dumps(
            {
                "model_router": {
                    "models": {
                        "pro": "   ",
                        "flash": 12345,
                        "unknown_tier": "some-model",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    invalid_router = QAModelRouter(config_path=str(invalid_vals))
    assert invalid_router.route_task("root cause").recommended_model == "gemini-2.5-pro"
    assert invalid_router.route_task("Run login suite").recommended_model == "gemini-2.5-flash"
    assert invalid_router.route_task("").recommended_model == "gemini-2.5-flash-lite"

    # Config with no model_router/models keys
    empty_cfg = tmp_path / "empty.json"
    empty_cfg.write_text(json.dumps({"version": "4.8.1"}), encoding="utf-8")
    empty_router = QAModelRouter(config_path=str(empty_cfg))
    assert empty_router.route_task("root cause").recommended_model == "gemini-2.5-pro"
