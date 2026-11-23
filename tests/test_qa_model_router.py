# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""Unit tests for QAModelRouter (tests/test_qa_model_router.py).

Verifies semantic heuristic classification, cost ratio calculation,
and context length escalation.

Author: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
License: MIT
"""

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
    assert decision.recommended_model == "gemini-2.5-pro"
    assert decision.estimated_cost_ratio == 1.0
    assert "root cause" in decision.reason.lower() or "flaky" in decision.reason.lower()


def test_pom_refactoring_routed_to_pro(router):
    decision = router.route_task("Refactor LoginPage POM design to eliminate duplicate selectors")
    assert decision.tier == ModelComputeTier.PRO_REASONING
    assert decision.recommended_model == "gemini-2.5-pro"


def test_lightweight_lint_routed_to_flash_lite(router):
    decision = router.route_task("Run ruff format and check clean encoding")
    assert decision.tier == ModelComputeTier.FLASH_LITE
    assert decision.recommended_model == "gemini-2.5-flash-lite"
    assert decision.estimated_cost_ratio == 0.05


def test_standard_test_run_routed_to_flash(router):
    decision = router.route_task("Execute pytest tests/test_login.py with coverage report")
    assert decision.tier == ModelComputeTier.FLASH
    assert decision.recommended_model == "gemini-2.5-flash"
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
    assert fb_pro == "gemini-2.5-flash"

    fb_flash = router.get_degraded_fallback_model(ModelComputeTier.FLASH)
    assert fb_flash == "gemini-2.5-flash-lite"
