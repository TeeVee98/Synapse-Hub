#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""4-Scenario Pytest Suite: Bilingual Intent Normalizer & Cognitive Engine EN/VI Parity (M1-M3).

Covers:
  1. Positive: EN/VI parity across normalizer, StepBackEngine, SelfDiscoverEngine, QAModelRouter, super_plan_engine.
  2. Negative: Pure English passthrough, non-slash file paths/URLs, lightweight triage non-escalation, invalid types.
  3. Boundary: Empty string, whitespace, emoji/diacritic-only strings, 50 KB oversized payloads (< 5ms budget).
  4. CLI / Resilience: `--json` CLI output contract on bilingual_intent_normalizer.py and immutability checks.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import FrozenInstanceError

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
for _p in (REPO_ROOT, TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)


VI_PAYMENT_RACE_PROMPT = (
    "Sửa lỗi bấm đúp nút thanh toán gây xung đột luồng đồng thời và khóa cơ sở dữ liệu giao dịch"
)
EN_PAYMENT_RACE_PROMPT = (
    "Fix double-click race condition in payment checkout causing concurrent database lock"
)


# ==============================================================================
# 1. M1 — BILINGUAL INTENT NORMALIZER (4-SCENARIO BATTERY)
# ==============================================================================


def test_positive_normalizer_vietnamese_race_and_slash_extraction():
    """Positive: Normalizer maps Vietnamese QA/architecture phrases and /slash commands deterministically."""
    from tools.core.bilingual_intent_normalizer import (
        NormalizedIntentDTO,
        normalize_bilingual_intent,
    )

    t0 = time.perf_counter()
    dto = normalize_bilingual_intent(VI_PAYMENT_RACE_PROMPT)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert isinstance(dto, NormalizedIntentDTO)
    assert dto.raw_text == VI_PAYMENT_RACE_PROMPT
    assert dto.has_vietnamese is True
    assert dto.slash_skill is None
    assert elapsed_ms < 50.0  # Generous CI guard; deterministic O(N) path runs < 5ms

    tokens = set(dto.canonical_tokens)
    assert "payment" in tokens
    assert "database" in tokens or "db" in tokens
    assert "lock" in tokens
    assert "race" in tokens or "concurrency" in tokens
    assert "double" in tokens or "double_click" in tokens or "duplicate" in tokens

    # Deterministic repeat execution & frozen immutability
    dto2 = normalize_bilingual_intent(VI_PAYMENT_RACE_PROMPT)
    assert dto == dto2
    with pytest.raises((FrozenInstanceError, AttributeError)):
        dto.canonical_text = "mutated"  # type: ignore[misc]

    # Default DTO field contract
    default_dto = NormalizedIntentDTO("a", "a", ("a",))
    assert default_dto.has_vietnamese is False
    assert default_dto.slash_skill is None

    # Unaccented Vietnamese also normalizes accurately and sets has_vietnamese=True
    unaccented = normalize_bilingual_intent(
        "Sua loi thanh toan bam dup gay khoa co so du lieu dong thoi"
    )
    assert unaccented.has_vietnamese is True
    unaccented_tokens = set(unaccented.canonical_tokens)
    assert "payment" in unaccented_tokens
    assert "lock" in unaccented_tokens
    assert "concurrency" in unaccented_tokens or "race" in unaccented_tokens

    # Diacritics-only Vietnamese without phrase lexicon match still marks has_vietnamese=True
    assert normalize_bilingual_intent("đổi màu nút").has_vietnamese is True
    # Pure English 'double click' must NOT be misclassified as Vietnamese
    en_dbl = normalize_bilingual_intent("Fix double click submission bug")
    assert en_dbl.has_vietnamese is False
    assert "double_click" in set(en_dbl.canonical_tokens)

    # Slash command extraction
    slash_plan = normalize_bilingual_intent("/super-plan Nâng cấp luồng xác thực JWT và phiên đăng nhập")
    assert slash_plan.slash_skill == "super-plan"
    assert "auth" in set(slash_plan.canonical_tokens)
    assert "session" in set(slash_plan.canonical_tokens)

    slash_solo = normalize_bilingual_intent("Please run /solo on tools/core/skill_router.py")
    assert slash_solo.slash_skill == "solo"


def test_negative_normalizer_english_passthrough_and_non_slash_paths():
    """Negative: Pure English preserves tokens cleanly; paths and URLs do not trigger false slash_skill."""
    from tools.core.bilingual_intent_normalizer import normalize_bilingual_intent

    dto = normalize_bilingual_intent(
        "Refactor tools/core/skill_router.py per https://example.com/solo/docs"
    )
    assert dto.has_vietnamese is False
    assert dto.slash_skill is None
    tokens = set(dto.canonical_tokens)
    assert "refactor" in tokens
    assert "skill_router" in tokens or "skill" in tokens

    # Non-string / None resilient fallback
    none_dto = normalize_bilingual_intent(None)  # type: ignore[arg-type]
    assert none_dto.raw_text == ""
    assert none_dto.canonical_text == ""
    assert none_dto.canonical_tokens == ()
    assert none_dto.slash_skill is None
    assert none_dto.has_vietnamese is False


def test_boundary_normalizer_empty_unicode_and_oversized_payload():
    """Boundary: Empty, whitespace, emoji/diacritic-only, and 50KB payloads run fast without crashing."""
    from tools.core.bilingual_intent_normalizer import normalize_bilingual_intent

    for sample in ("", "   \n\t  ", "🔥🎯✨", "áàảãạ ếềệểễ"):
        dto = normalize_bilingual_intent(sample)
        assert isinstance(dto.canonical_text, str)
        assert isinstance(dto.canonical_tokens, tuple)
    assert normalize_bilingual_intent("").has_vietnamese is False
    assert normalize_bilingual_intent("   ").has_vietnamese is False

    # Oversized 50 KB prompt must be bounded and fast
    huge = ("xác thực thanh toán đồng thời " * 2000) + " tail_marker_should_be_clipped"
    assert len(huge) > 50_000
    t0 = time.perf_counter()
    dto_huge = normalize_bilingual_intent(huge)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 100.0
    assert "tail_marker_should_be_clipped" not in dto_huge.canonical_tokens
    assert "payment" in set(dto_huge.canonical_tokens)


def test_cli_normalizer_json_output_contract(capsys):
    """CLI: Running tools/core/bilingual_intent_normalizer.py --text ... --json returns exit 0 and valid DTO JSON."""
    from tools.core import bilingual_intent_normalizer as mod

    # Direct in-process CLI invocation checks return code, ensure_ascii=False UTF-8 output, and required --text guard
    rc = mod.main(["--text", "/super-plan " + VI_PAYMENT_RACE_PROMPT, "--json"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "thanh toán" in captured.out
    in_proc_data = json.loads(captured.out)
    assert in_proc_data["slash_skill"] == "super-plan"
    assert in_proc_data["has_vietnamese"] is True

    # Missing required --text argument must fail argument parsing
    with pytest.raises(SystemExit) as exc_info:
        mod.main(["--json"])
    assert exc_info.value.code != 0

    script = os.path.join(REPO_ROOT, "tools", "core", "bilingual_intent_normalizer.py")
    proc = subprocess.run(
        [sys.executable, script, "--text", "/super-plan " + VI_PAYMENT_RACE_PROMPT, "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr
    assert "thanh toán" in proc.stdout
    data = json.loads(proc.stdout)
    assert data["slash_skill"] == "super-plan"
    assert data["has_vietnamese"] is True
    assert isinstance(data["canonical_tokens"], list)
    assert "payment" in data["canonical_tokens"]
    assert "lock" in data["canonical_tokens"]


# ==============================================================================
# 2. M2 — COGNITIVE & REASONING ENGINES EN/VI PARITY
# ==============================================================================


def test_en_vi_parity_reasoning_engines():
    """Positive (TC-01): StepBack, SelfDiscover, and QAModelRouter achieve EN/VI parity on race/DB-lock prompts."""
    from tools.reasoning.qa_model_router import ModelComputeTier, QAModelRouter
    from tools.reasoning.self_discover_engine import SelfDiscoverEngine
    from tools.reasoning.step_back_engine import StepBackEngine

    sb = StepBackEngine()
    en_sb = sb.run(EN_PAYMENT_RACE_PROMPT)
    vi_sb = sb.run(VI_PAYMENT_RACE_PROMPT)

    en_cats = {q["category"] for q in en_sb["step_back_abstraction"]["abstract_questions"]}
    vi_cats = {q["category"] for q in vi_sb["step_back_abstraction"]["abstract_questions"]}
    assert "DISTRIBUTED_CONCURRENCY" in en_cats
    assert "DISTRIBUTED_CONCURRENCY" in vi_cats

    # Vietnamese auth/session & performance prompts also trigger right StepBack categories
    vi_auth = sb.run("Kiểm tra lỗi làm mới token xác thực phiên đăng nhập khi mạng chập chờn")
    auth_cats = {q["category"] for q in vi_auth["step_back_abstraction"]["abstract_questions"]}
    assert "SECURITY_IDENTITY" in auth_cats

    vi_perf = sb.run("Phân tích độ trễ phản hồi chậm và quá tải khi kiểm thử hiệu năng chịu tải")
    perf_cats = {q["category"] for q in vi_perf["step_back_abstraction"]["abstract_questions"]}
    assert "SYSTEM_SATURATION" in perf_cats

    # SelfDiscoverEngine resonance parity
    sd = SelfDiscoverEngine()
    en_sd = sd.select(EN_PAYMENT_RACE_PROMPT, top_k=4)
    vi_sd = sd.select(VI_PAYMENT_RACE_PROMPT, top_k=4)
    en_ids = {m["id"] for m in en_sd}
    vi_ids = {m["id"] for m in vi_sd}
    assert "MOD_CONCURRENCY_RACE_MODELING" in en_ids
    assert "MOD_CONCURRENCY_RACE_MODELING" in vi_ids
    assert vi_sd[0]["selection_score"] >= 5.0

    # QAModelRouter tier parity
    router = QAModelRouter()
    en_route = router.route_task(EN_PAYMENT_RACE_PROMPT)
    vi_route = router.route_task(VI_PAYMENT_RACE_PROMPT)
    assert en_route.tier == ModelComputeTier.PRO_REASONING
    assert vi_route.tier == ModelComputeTier.PRO_REASONING


def test_negative_reasoning_vietnamese_triage_does_not_over_escalate():
    """Negative: Lightweight Vietnamese lint/status query routes to FLASH_LITE, not PRO_REASONING."""
    from tools.reasoning.qa_model_router import ModelComputeTier, QAModelRouter
    from tools.reasoning.step_back_engine import StepBackEngine

    router = QAModelRouter()
    triage_decision = router.route_task("Kiểm tra định dạng utf-8 và chạy git status nhanh")
    assert triage_decision.tier == ModelComputeTier.FLASH_LITE

    sb = StepBackEngine()
    generic = sb.run("Đổi màu nút bấm giao diện tiêu đề")
    cats = {q["category"] for q in generic["step_back_abstraction"]["abstract_questions"]}
    assert "FIRST_PRINCIPLES_SOFTWARE" in cats


def test_boundary_reasoning_empty_and_unicode_inputs():
    """Boundary: Empty and emoji-only inputs across reasoning engines never crash."""
    from tools.reasoning.qa_model_router import ModelComputeTier, QAModelRouter
    from tools.reasoning.self_discover_engine import SelfDiscoverEngine
    from tools.reasoning.step_back_engine import StepBackEngine

    sb = StepBackEngine()
    sd = SelfDiscoverEngine()
    router = QAModelRouter()

    for sample in ("", "   ", "🚀🔥"):
        sb_res = sb.run(sample)
        assert sb_res["status"] == "SUCCESS"
        assert sb_res["step_back_abstraction"]["total_questions"] >= 1

        sd_res = sd.select(sample, top_k=3)
        assert len(sd_res) == 3

        route = router.route_task(sample)
        assert route.tier in (ModelComputeTier.FLASH_LITE, ModelComputeTier.FLASH)


# ==============================================================================
# 3. M3 — SUPER-PLAN RISK ROUTER & AMBIGUITY GATE EN/VI PARITY
# ==============================================================================


def test_en_vi_parity_super_plan_risk_and_ambiguity():
    """Positive (TC-01): super_plan_engine produces DEEP_SUPER_PLAN (risk >= 0.70) for Vietnamese payment race/DB lock."""
    from tools.design.super_plan_engine import (
        PlanningTier,
        calculate_risk_routing,
        check_ambiguities,
    )

    en_tier, en_metric = calculate_risk_routing(EN_PAYMENT_RACE_PROMPT, target_files=[])
    vi_tier, vi_metric = calculate_risk_routing(VI_PAYMENT_RACE_PROMPT, target_files=[])

    assert en_tier == PlanningTier.TIER_2_DEEP
    assert vi_tier == PlanningTier.TIER_2_DEEP
    assert en_metric.risk_score >= 0.70
    assert vi_metric.risk_score >= 0.70
    assert vi_metric.state_mutation is True
    assert vi_metric.hard_critical is True

    # Ambiguity gate activates on Vietnamese DB/concurrency prompt and respects Vietnamese negation
    vi_amb = check_ambiguities(
        "Thiết kế bộ nhớ đệm cơ sở dữ liệu xử lý đồng thời nhưng không dùng redis"
    )
    cats = {q["category"] for q in vi_amb}
    assert "storage" in cats
    storage_q = next(q for q in vi_amb if q["category"] == "storage")
    assert "redis" in storage_q["excluded_by_negation"]


def test_boundary_super_plan_tokenize_unicode():
    """Boundary: tokenize_text handles empty, emoji, and Vietnamese prompts gracefully."""
    from tools.design.super_plan_engine import tokenize_text

    assert tokenize_text("") == set()
    assert tokenize_text("🎯✨") == set()
    vi_tokens = tokenize_text(VI_PAYMENT_RACE_PROMPT)
    assert "payment" in vi_tokens
    assert "lock" in vi_tokens


# ==============================================================================
# 4. M7 — COLLOQUIAL EXPANSION & CONFIDENCE-GATED CLARIFICATION (4 SCENARIOS)
# ==============================================================================


def test_positive_colloquial_vietnamese_and_clarification_gate():
    """Positive: Colloquial Vietnamese phrases resolve accurately; unmapped freeform prose triggers clarification."""
    from tools.core.bilingual_intent_normalizer import normalize_bilingual_intent
    from tools.design.super_plan_engine import (
        PlanningTier,
        assess_intent_clarity,
        calculate_risk_routing,
        check_ambiguities,
    )
    from tools.reasoning.qa_model_router import ModelComputeTier, QAModelRouter
    from tools.reasoning.step_back_engine import StepBackEngine

    # 1. Colloquial race / money double-deduction resolves without needing clarification
    colloq_race = normalize_bilingual_intent("Hai nguoi bam cung luc bi tru tien 2 lan")
    assert colloq_race.has_vietnamese is True
    assert colloq_race.unmapped_vietnamese is False
    assert colloq_race.needs_clarification is False
    assert {"payment", "concurrency", "race"}.issubset(set(colloq_race.canonical_tokens))

    sb = StepBackEngine()
    colloq_cats = {q["category"] for q in sb.run("Hai người bấm cùng lúc bị trừ tiền 2 lần")["step_back_abstraction"]["abstract_questions"]}
    assert "DISTRIBUTED_CONCURRENCY" in colloq_cats

    tier, metric = calculate_risk_routing("Hai người bấm cùng lúc bị trừ tiền 2 lần", target_files=[])
    assert tier == PlanningTier.TIER_2_DEEP
    assert metric.risk_score >= 0.70

    # 2. Colloquial flaky UI phrase & expanded Vietnamese negation
    colloq_flaky = normalize_bilingual_intent("Kịch bản chạy lúc pass lúc fail vì nút bấm bị chậm")
    assert colloq_flaky.needs_clarification is False
    assert "flaky" in set(colloq_flaky.canonical_tokens)
    assert QAModelRouter().route_task("Kịch bản chạy lúc pass lúc fail").tier == ModelComputeTier.PRO_REASONING

    neg_vi = check_ambiguities("Thiết kế bộ nhớ đệm cơ sở dữ liệu bỏ qua redis")
    storage_q = next(q for q in neg_vi if q["category"] == "storage")
    assert "redis" in storage_q["excluded_by_negation"]

    # 3. Unmapped freeform Vietnamese prose (both accented and unaccented) triggers needs_clarification
    for vague_vi in (
        "Làm lại giùm chỗ xử lý hôm qua cho mượt hơn đi",
        "No cu giat giat kho chiu qua",
        "Chinh giup phan gio hang hom truoc voi",
    ):
        vague_dto = normalize_bilingual_intent(vague_vi)
        assert vague_dto.has_vietnamese is True, vague_vi
        assert vague_dto.unmapped_vietnamese is True, vague_vi
        assert vague_dto.needs_clarification is True, vague_vi
        assert len(vague_dto.clarifying_questions) >= 1, vague_vi
        assert len(vague_dto.clarifying_questions[0]["options"]) >= 3, vague_vi

    clarity = assess_intent_clarity("Làm lại giùm chỗ xử lý hôm qua cho mượt hơn đi", target_files=[])
    assert clarity["needs_clarification"] is True
    assert len(clarity["clarifying_questions"]) >= 1

    amb_vague = check_ambiguities("No cu giat giat kho chiu qua")
    assert len(amb_vague) == 1
    assert amb_vague[0]["category"] == "context_clarification"
    assert amb_vague[0]["resolved_by_invariant"] is False


def test_negative_clarification_not_triggered_on_english_or_scoped_files():
    """Negative: Pure English, known domain prompts, and file-scoped tasks do NOT falsely trigger clarification."""
    from tools.core.bilingual_intent_normalizer import normalize_bilingual_intent
    from tools.design.super_plan_engine import assess_intent_clarity, check_ambiguities

    # Pure English simple task remains clear
    en_dto = normalize_bilingual_intent("Update copyright year in footer banner")
    assert en_dto.unmapped_vietnamese is False
    assert en_dto.needs_clarification is False
    assert en_dto.clarifying_questions == ()
    assert check_ambiguities("Update copyright year in footer banner") == []

    # File-scoped Vietnamese task already has concrete file context -> clear
    scoped = assess_intent_clarity(
        "Làm lại giùm chỗ xử lý hôm qua cho mượt hơn đi",
        target_files=["tests/e2e/pages/login_page.py"],
    )
    assert scoped["needs_clarification"] is False


def test_boundary_clarification_single_word_or_empty_vi():
    """Boundary: Empty, whitespace, emoji, or single-token Vietnamese never crashes clarification gate."""
    from tools.core.bilingual_intent_normalizer import normalize_bilingual_intent
    from tools.design.super_plan_engine import assess_intent_clarity

    for sample in ("", "   ", "🔥", "lỗi"):
        dto = normalize_bilingual_intent(sample)
        assert dto.needs_clarification is False
        clarity = assess_intent_clarity(sample, target_files=[])
        assert clarity["needs_clarification"] is False


def test_cli_super_plan_ambiguity_check_blocks_unmapped_vietnamese():
    """CLI: super_plan_engine.py ambiguity-check --auto-recommend blocks unmapped vague Vietnamese (exit 3)."""
    script = os.path.join(REPO_ROOT, "tools", "design", "super_plan_engine.py")
    proc = subprocess.run(
        [
            sys.executable,
            script,
            "ambiguity-check",
            "--task",
            "Làm lại giùm chỗ xử lý hôm qua cho mượt hơn đi",
            "--auto-recommend",
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        encoding="utf-8",
    )
    assert proc.returncode == 3, proc.stdout + proc.stderr
    data = json.loads(proc.stdout)
    assert data["status"] == "UNRESOLVED_FORK"
    assert data["has_ambiguity"] is True
    assert data["questions"][0]["category"] == "context_clarification"


# ==============================================================================
# 5. M8 — SYMMETRICAL ENGLISH COLLOQUIAL EXPANSION & VAGUE-EN CLARIFICATION GATE
# ==============================================================================


def test_positive_english_colloquial_parity_and_vague_clarification():
    """Positive: Casual English bug descriptions match Vietnamese parity; vague English triggers clarification."""
    from tools.core.bilingual_intent_normalizer import normalize_bilingual_intent
    from tools.design.super_plan_engine import (
        PlanningTier,
        assess_intent_clarity,
        calculate_risk_routing,
        check_ambiguities,
    )
    from tools.reasoning.qa_model_router import ModelComputeTier, QAModelRouter
    from tools.reasoning.step_back_engine import StepBackEngine

    # 1. Casual English double-charge race matches DISTRIBUTED_CONCURRENCY + PRO_REASONING + TIER_2_DEEP
    casual_race = "Two users clicked submit at the same time and got charged twice"
    race_dto = normalize_bilingual_intent(casual_race)
    assert race_dto.has_vietnamese is False
    assert race_dto.unmapped_english is False
    assert race_dto.needs_clarification is False
    assert {"payment", "concurrency", "race"}.issubset(set(race_dto.canonical_tokens))

    sb = StepBackEngine()
    race_cats = {q["category"] for q in sb.run(casual_race)["step_back_abstraction"]["abstract_questions"]}
    assert "DISTRIBUTED_CONCURRENCY" in race_cats
    assert QAModelRouter().route_task(casual_race).tier == ModelComputeTier.PRO_REASONING
    tier, metric = calculate_risk_routing(casual_race, target_files=[])
    assert tier == PlanningTier.TIER_2_DEEP
    assert metric.risk_score >= 0.70

    # 2. Casual English flaky & session-logout phrases escalate properly
    casual_flaky = "Tests pass sometimes and fail randomly"
    assert QAModelRouter().route_task(casual_flaky).tier == ModelComputeTier.PRO_REASONING
    assert "flaky" in set(normalize_bilingual_intent(casual_flaky).canonical_tokens)

    casual_auth = "Users keep getting logged out unexpectedly"
    auth_cats = {q["category"] for q in sb.run(casual_auth)["step_back_abstraction"]["abstract_questions"]}
    assert "SECURITY_IDENTITY" in auth_cats

    # 3. Underspecified vague English triggers clarification symmetrically
    for vague_en in (
        "Redo that broken part from yesterday to make it smoother",
        "It keeps glitching and acting weird",
    ):
        dto = normalize_bilingual_intent(vague_en)
        assert dto.has_vietnamese is False, vague_en
        assert dto.unmapped_english is True, vague_en
        assert dto.needs_clarification is True, vague_en
        assert len(dto.clarifying_questions) >= 1, vague_en

    clarity = assess_intent_clarity("Redo that broken part from yesterday to make it smoother", target_files=[])
    assert clarity["needs_clarification"] is True
    amb = check_ambiguities("Redo that broken part from yesterday to make it smoother")
    assert len(amb) == 1
    assert amb[0]["category"] == "context_clarification"


def test_negative_concrete_english_tasks_and_questions_stay_clear():
    """Negative: Concrete non-skill English tasks and domain-anchored vague tasks do NOT ask clarifying questions."""
    from tools.core.bilingual_intent_normalizer import normalize_bilingual_intent
    from tools.design.super_plan_engine import assess_intent_clarity, check_ambiguities

    for concrete in (
        "Update copyright year in footer banner",
        "Fix typo in constant name",
        "Fix that broken part in auth/login",
    ):
        dto = normalize_bilingual_intent(concrete)
        assert dto.unmapped_english is False, concrete
        assert dto.needs_clarification is False, concrete
        assert assess_intent_clarity(concrete, target_files=[])["needs_clarification"] is False
    assert check_ambiguities("Update copyright year in footer banner") == []
