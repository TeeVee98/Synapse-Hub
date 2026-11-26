#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""4-Scenario Pytest Suite: Context-Aware Skill Router Turn-1 & Slash Precision (M3).

Covers:
  1. Positive: Turn-1 file-less routing (generate/design/mock/heal/transpile/export), .agent/skills slash commands, bilingual VI prompts.
  2. Negative: Pure INQUIRY exemption, --micro-fix exemption, out-of-domain touched files exemption, low-confidence abstention.
  3. Boundary: Empty prompt, unicode/emoji prompt, non-existent /unknown-slash command.
  4. CLI / Resilience: `skill_router.py --prompt ... --json` contract & exit code 0.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.core.skill_router import (
    SkillRouteVerdictDTO,
    _detect_meta_workflow_skill,
    classify_intent,
    evaluate_skill_first_trigger,
    load_agent_local_skills,
)


# ==============================================================================
# 1. POSITIVE SCENARIOS
# ==============================================================================


def test_turn1_and_slash_skill_routing_positive():
    """Positive (TC-02): Turn-1 file-less routing and /slash meta-skill resolution select exact SKILL.md."""
    # 1. Turn-1 file-less OpenAPI generation (no target_files passed!)
    res_api = evaluate_skill_first_trigger(
        prompt="Generate boundary API test matrix from OpenAPI spec",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert res_api["intent"] == "ACTION"
    assert res_api["is_triggered"] is True
    assert res_api["is_exempt"] is False
    assert res_api["recommended_skill"] == "api-spec-to-e2e-matrix"
    assert res_api["skill_md_path"] == "skills/03-api-and-contracts/api-spec-to-e2e-matrix/SKILL.md"
    assert os.path.isfile(os.path.join(REPO_ROOT, res_api["skill_md_path"]))
    assert res_api.get("score", 0) >= 4

    # 2. Expanded action verbs: design, mock, heal, transpile, export
    for verb_prompt, expected_skill in (
        ("Mock HTTP network routes and inject 503 chaos faults", "api-network-mocking-interception"),
        ("Heal broken Playwright locator using semantic AOM diffing", "self-healing-locator"),
        ("Design risk-based manual testing matrix and Excel export", "rbt-manual-testing"),
    ):
        r = evaluate_skill_first_trigger(prompt=verb_prompt, target_files=[], repo_root=REPO_ROOT)
        assert r["intent"] == "ACTION", f"Expected ACTION for: {verb_prompt}"
        assert r["is_triggered"] is True
        assert r["recommended_skill"] == expected_skill
        assert r["skill_md_path"] and os.path.isfile(os.path.join(REPO_ROOT, r["skill_md_path"]))

    # Verify classify_intent recognizes transpile and export as ACTION
    assert classify_intent("Transpile Selenium Java tests to Playwright TypeScript") == "ACTION"
    assert classify_intent("Export test report matrix to Excel workbook") == "ACTION"

    # 3. .agent/skills slash commands (/super-plan, /solo)
    res_plan = evaluate_skill_first_trigger(
        prompt="/super-plan Design distributed payment lock architecture",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert res_plan["is_triggered"] is True
    assert res_plan["recommended_skill"] == "super-plan"
    assert res_plan["skill_md_path"] == ".agent/skills/super-plan/SKILL.md"

    res_solo = evaluate_skill_first_trigger(
        prompt="/solo Execute implementation_plan.md milestones sequentially",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert res_solo["is_triggered"] is True
    assert res_solo["recommended_skill"] == "solo"
    assert res_solo["skill_md_path"] == ".agent/skills/solo/SKILL.md"

    # 4. Vietnamese Turn-1 file-less routing (both accented and unaccented) via bilingual normalizer
    for vi_api_prompt in (
        "Tạo ma trận kiểm thử API biên từ đặc tả OpenAPI",
        "Tao ma tran kiem thu api tu dac ta OpenAPI",
    ):
        res_vi = evaluate_skill_first_trigger(
            prompt=vi_api_prompt,
            target_files=[],
            repo_root=REPO_ROOT,
        )
        assert res_vi["intent"] == "ACTION", vi_api_prompt
        assert res_vi["is_triggered"] is True, vi_api_prompt
        assert res_vi["recommended_skill"] == "api-spec-to-e2e-matrix", vi_api_prompt


# ==============================================================================
# 2. NEGATIVE SCENARIOS
# ==============================================================================


def test_negative_exemptions_and_low_confidence_abstention():
    """Negative (TC-03): Pure INQUIRY, --micro-fix, and out-of-scope files remain exempt."""
    # 1. Pure conceptual inquiry
    inq = evaluate_skill_first_trigger(
        prompt="How does Clean POM work?",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert inq["intent"] == "INQUIRY"
    assert inq["is_triggered"] is False
    assert inq["is_exempt"] is True
    assert inq["recommended_skill"] is None
    assert inq["ambiguous_context"] is False
    assert inq["context_conflicts"] == []

    # 1b. Underspecified colloquial INQUIRY exemption keeps ambiguous_context=False
    vague_inq = evaluate_skill_first_trigger(
        prompt="Nó cứ giật giật khó chịu quá",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert vague_inq["needs_clarification"] is True
    assert vague_inq["ambiguous_context"] is False
    assert vague_inq["context_conflicts"] == []

    # 2. Single-line micro-fix exemption
    micro = evaluate_skill_first_trigger(
        prompt="Fix typo in constant name",
        target_files=["tests/e2e/pages/login_page.py"],
        is_single_line_hotfix=True,
        repo_root=REPO_ROOT,
    )
    assert micro["is_triggered"] is False
    assert micro["is_exempt"] is True
    assert micro["ambiguous_context"] is False
    assert micro["context_conflicts"] == []

    # 3. Touched files outside managed skill domains
    outside = evaluate_skill_first_trigger(
        prompt="Update README changelog notes",
        target_files=["CHANGELOG.md"],
        repo_root=REPO_ROOT,
    )
    assert outside["is_triggered"] is False
    assert outside["is_exempt"] is True
    assert outside["ambiguous_context"] is False
    assert outside["context_conflicts"] == []

    # 4. Generic file-less non-skill action does not force an unrelated recommended_skill
    generic = evaluate_skill_first_trigger(
        prompt="Update copyright year in footer banner",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert generic["recommended_skill"] is None
    assert generic["is_triggered"] is False


# ==============================================================================
# 3. BOUNDARY SCENARIOS
# ==============================================================================


def test_boundary_empty_unicode_and_unknown_slash_command():
    """Boundary: Empty, whitespace, emoji-only, and unknown /slash commands never crash."""
    for sample in ("", "   ", "🎯🔥", "/nonexistent-imaginary-skill do nothing"):
        res = evaluate_skill_first_trigger(prompt=sample, target_files=[], repo_root=REPO_ROOT)
        assert isinstance(res, dict)
        assert "is_triggered" in res
        assert "recommended_skill" in res


# ==============================================================================
# 4. CLI & RESILIENCE SCENARIOS
# ==============================================================================


def test_cli_skill_router_json_output_turn1():
    """CLI: Running tools/core/skill_router.py --prompt ... --json returns exit 0 and Turn-1 recommendation."""
    script = os.path.join(REPO_ROOT, "tools", "core", "skill_router.py")
    proc = subprocess.run(
        [
            sys.executable,
            script,
            "--prompt",
            "Generate boundary API test matrix from OpenAPI spec",
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["intent"] == "ACTION"
    assert data["is_triggered"] is True
    assert data["recommended_skill"] == "api-spec-to-e2e-matrix"
    assert data["skill_md_path"] == "skills/03-api-and-contracts/api-spec-to-e2e-matrix/SKILL.md"


def test_clarification_gate_on_vague_vietnamese_vs_exemptions():
    """Positive/Negative/Boundary/CLI: Arbitrary vague Vietnamese triggers needs_clarification; exemptions do not."""
    # Positive: Diverse vague Vietnamese phrasings (even without explicit verbs from ACTION_PATTERNS)
    vague_prompts = [
        "Làm lại giùm chỗ xử lý hôm qua cho mượt hơn đi",
        "Chỉnh giúp phần giỏ hàng bị đơ với",
        "Nó cứ giật giật khó chịu quá",
        "Đoạn tính tiền hôm trước chạy sai kết quả rồi",
        "No cu giat giat kho chiu qua",
        "Chinh giup cho nay duoc khong?",
        "Bạn sửa giúp chỗ này được không?",
    ]
    for prompt_text in vague_prompts:
        vague_res = evaluate_skill_first_trigger(
            prompt=prompt_text,
            target_files=[],
            repo_root=REPO_ROOT,
        )
        assert vague_res["is_triggered"] is False, prompt_text
        assert vague_res["recommended_skill"] is None, prompt_text
        assert vague_res["needs_clarification"] is True, prompt_text
        assert vague_res["clarification_reason"], prompt_text
        assert len(vague_res["clarifying_questions"]) >= 1, prompt_text

    # Negative 1: Explicit Vietnamese questions (accented & unaccented) remain INQUIRY and do NOT ask clarifying questions
    for q_prompt in (
        "Phần xử lý hôm qua là gì vậy?",
        "Chức năng này hoạt động sao?",
        "Clean POM la gi?",
        "Tai sao test bi cham?",
    ):
        inq_res = evaluate_skill_first_trigger(
            prompt=q_prompt,
            target_files=[],
            repo_root=REPO_ROOT,
        )
        assert inq_res["intent"] == "INQUIRY", q_prompt
        assert inq_res["needs_clarification"] is False, q_prompt

    # Negative 2: File-scoped prompt resolves domain directly without needing clarification
    scoped_res = evaluate_skill_first_trigger(
        prompt="Làm lại giùm chỗ xử lý hôm qua cho mượt hơn đi",
        target_files=["tests/e2e/pages/login_page.py"],
        repo_root=REPO_ROOT,
    )
    assert scoped_res["is_triggered"] is True
    assert scoped_res["needs_clarification"] is False

    # Boundary: Empty prompt does not trigger clarification
    empty_res = evaluate_skill_first_trigger(prompt="", target_files=[], repo_root=REPO_ROOT)
    assert empty_res["needs_clarification"] is False

    # CLI JSON contract includes needs_clarification
    script = os.path.join(REPO_ROOT, "tools", "core", "skill_router.py")
    proc = subprocess.run(
        [
            sys.executable,
            script,
            "--prompt",
            "Làm lại giùm chỗ xử lý hôm qua cho mượt hơn đi",
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr
    cli_data = json.loads(proc.stdout)
    assert cli_data["needs_clarification"] is True
    assert len(cli_data["clarifying_questions"]) >= 1


def test_meta_workflow_skill_dto_and_local_agent_skills(tmp_path: Path, capsys):
    """Mutation-hardening: Covers SkillRouteVerdictDTO, _detect_meta_workflow_skill, and load_agent_local_skills."""
    dto = SkillRouteVerdictDTO("ACTION", True, False, "solo", ".agent/skills/solo/SKILL.md")
    assert dto.score == 0.0
    assert dto.needs_clarification is False
    assert dto.calibrated_confidence == 0.0
    assert dto.matched_utterances == ()
    with pytest.raises((FrozenInstanceError, AttributeError)):
        dto.intent = "INQUIRY"  # type: ignore[misc]

    assert _detect_meta_workflow_skill(None, [], "INQUIRY", REPO_ROOT) is None  # type: ignore[arg-type]
    assert _detect_meta_workflow_skill("/solo run tests", [], "ACTION", REPO_ROOT)["id"] == "solo"
    assert _detect_meta_workflow_skill("/super-plan arch", [], "ACTION", REPO_ROOT)["id"] == "super-plan"
    assert _detect_meta_workflow_skill("Use solo_runner", [], "ACTION", REPO_ROOT)["id"] == "solo"
    assert _detect_meta_workflow_skill("Build execution dag", [], "ACTION", REPO_ROOT)["id"] == "super-plan"

    two_files = ["tools/design/a.py", "tools/design/b.py"]
    three_files = ["tools/design/a.py", "tools/design/b.py", "tools/design/c.py"]
    assert _detect_meta_workflow_skill("refactor", two_files, "ACTION", REPO_ROOT) is None
    assert _detect_meta_workflow_skill("explain", three_files, "INQUIRY", REPO_ROOT) is None
    assert _detect_meta_workflow_skill("refactor", three_files, "ACTION", REPO_ROOT)["id"] == "solo"

    agent_skills = tmp_path / ".agent" / "skills"
    (agent_skills / "solo").mkdir(parents=True)
    (agent_skills / "solo" / "SKILL.md").write_text("# override", encoding="utf-8")
    (agent_skills / "empty-dir").mkdir(parents=True)
    (agent_skills / "custom-flow").mkdir(parents=True)
    (agent_skills / "custom-flow" / "SKILL.md").write_text("# custom", encoding="utf-8")

    local = load_agent_local_skills(str(tmp_path))
    by_id = {s["id"]: s for s in local}
    assert "solo" in by_id and "Single-Agent" in by_id["solo"]["summary"]
    assert "custom-flow" in by_id
    assert "empty-dir" not in by_id

    (tmp_path / "skills_index.json").write_text(
        json.dumps({"skills": [{"id": "solo", "domain": "10-agent-orchestration", "path": "skills/solo/SKILL.md", "stack_triggers": ["solo"], "summary": "Indexed solo"}]}),
        encoding="utf-8",
    )
    res_custom = evaluate_skill_first_trigger("Run /custom-flow workflow", target_files=[], repo_root=str(tmp_path))
    assert res_custom["recommended_skill"] == "custom-flow"
    assert res_custom["skill_md_path"] == ".agent/skills/custom-flow/SKILL.md"
    res_indexed_solo = evaluate_skill_first_trigger("Run /solo workflow", target_files=[], repo_root=str(tmp_path))
    assert res_indexed_solo["skill_md_path"] == "skills/solo/SKILL.md"

    with patch("tools.core.skill_router.os.listdir", side_effect=OSError("perm denied")):
        load_agent_local_skills(str(tmp_path))
    assert "Unable to scan .agent/skills directory" in capsys.readouterr().err


def test_english_colloquial_and_vague_clarification_symmetry():
    """Symmetry: English polite requests classify accurately and vague English triggers clarification."""
    auth_check = evaluate_skill_first_trigger(
        prompt="Can you check why users keep getting logged out?",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert auth_check["intent"] == "DIAGNOSTIC"
    assert auth_check["is_triggered"] is True
    assert auth_check["recommended_skill"] == "auth-session-and-cookie-manager"
    assert auth_check["needs_clarification"] is False

    flaky_res = evaluate_skill_first_trigger(
        prompt="Investigate why tests pass sometimes and fail randomly",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert flaky_res["intent"] == "DIAGNOSTIC"
    assert flaky_res["is_triggered"] is True
    assert flaky_res["recommended_skill"] == "flaky-test-sentinel-and-quarantine"

    for vague_en in (
        "Redo that broken part from yesterday to make it smoother",
        "It keeps glitching and acting weird",
        "Could you fix that weird thing from earlier?",
    ):
        res = evaluate_skill_first_trigger(prompt=vague_en, target_files=[], repo_root=REPO_ROOT)
        assert res["is_triggered"] is False, vague_en
        assert res["recommended_skill"] is None, vague_en
        assert res["needs_clarification"] is True, vague_en
        assert len(res["clarifying_questions"]) >= 1, vague_en

    q_en = evaluate_skill_first_trigger(
        prompt="How does health check work?",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert q_en["intent"] == "INQUIRY"
    assert q_en["needs_clarification"] is False


def test_cross_domain_vietnamese_verbs_and_vague_english_polish():
    """M10: Single-word VI verbs (chuyển/đo), DB/File/CWV precision, and no-deictic vague English."""
    gherkin_res = evaluate_skill_first_trigger(
        prompt="Chuyển file feature Gherkin BDD thành ma trận kiểm thử",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert gherkin_res["intent"] == "ACTION"
    assert gherkin_res["is_triggered"] is True
    assert gherkin_res["recommended_skill"] == "gherkin-to-suite"

    cwv_res = evaluate_skill_first_trigger(
        prompt="Đo chỉ số hiệu năng Core Web Vitals LCP và CLS",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert cwv_res["intent"] == "DIAGNOSTIC"
    assert cwv_res["is_triggered"] is True
    assert cwv_res["recommended_skill"] == "web-vitals-and-performance-profiler"

    db_res = evaluate_skill_first_trigger(
        prompt="Kiểm tra dữ liệu database và dọn dẹp fixture sau khi test",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert db_res["recommended_skill"] == "db-state-verifier-and-seeder"

    file_res = evaluate_skill_first_trigger(
        prompt="Kiểm tra cấu trúc file Excel và CSV tải về",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert file_res["recommended_skill"] == "file-and-report-validator"

    vague_en = evaluate_skill_first_trigger(
        prompt="Make the whole thing faster and cleaner please",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert vague_en["intent"] == "ACTION"
    assert vague_en["needs_clarification"] is True
    assert vague_en["recommended_skill"] is None


def test_layer1_layer2_skill_router_homonym_and_ambiguous_context():
    """M11: App form validation does not hijack QA synthetic-data skill; close cross-domain ties flag ambiguous_context."""
    # 1. App registration form validation must NOT select synthetic-test-data-generator
    form_res = evaluate_skill_first_trigger(
        prompt="Sửa hàm kiểm tra dữ liệu đầu vào form đăng ký",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert form_res["recommended_skill"] is None
    assert form_res["is_triggered"] is False
    assert form_res["ambiguous_context"] is True
    assert "app_validation_vs_qa_data" in form_res["context_conflicts"]

    # 2. Unaccented vague UI cleanup triggers needs_clarification
    unacc_ui = evaluate_skill_first_trigger(
        prompt="Don dep giao dien cho sach se hon",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert unacc_ui["needs_clarification"] is True

    # 3. Clear single-domain prompt keeps ambiguous_context=False
    clear_res = evaluate_skill_first_trigger(
        prompt="Generate boundary API test matrix from OpenAPI spec",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert clear_res["recommended_skill"] == "api-spec-to-e2e-matrix"
    assert clear_res["ambiguous_context"] is False
    assert clear_res["context_conflicts"] == []

    # 4. Close cross-domain skill tie flags ambiguous_context and close_cross_domain_skill_tie
    tie_res = evaluate_skill_first_trigger(
        prompt="Check bdd mock",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert tie_res["is_triggered"] is True
    assert tie_res["ambiguous_context"] is True
    assert "close_cross_domain_skill_tie" in tie_res["context_conflicts"]

    # 5. Cross-domain score gap >= 2 or same-domain close tie stays unambiguous
    non_tie = evaluate_skill_first_trigger(
        prompt="Check mock tdd",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert non_tie["is_triggered"] is True
    assert non_tie["ambiguous_context"] is False
    assert non_tie["context_conflicts"] == []

    same_dom = evaluate_skill_first_trigger(
        prompt="Verify export csv synthetic schema report",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert same_dom["is_triggered"] is True
    assert same_dom["ambiguous_context"] is False
    assert same_dom["context_conflicts"] == []


# ==============================================================================
# 5. M4 (v2.2) — HYBRID CALIBRATED UTTERANCE ROUTING & BACKWARD-COMPAT JSON
# ==============================================================================


def test_positive_hybrid_natural_vietnamese_utterance_routing():
    """Positive (TC-05): Colloquial VI, unaccented/Telex prompts, and meta-skills route with calibrated confidence."""
    from tools.core import skill_router as mod

    assert hasattr(mod, "BoundedRouteMatchDTO")
    assert hasattr(mod, "get_utterance_router_index")
    sample_match = mod.BoundedRouteMatchDTO("solo", "10-agent-orchestration", 0.8, 0.9, ("run /solo",))
    with pytest.raises((FrozenInstanceError, AttributeError)):
        sample_match.calibrated_confidence = 0.0  # type: ignore[misc]

    # Natural colloquial Vietnamese prompts routed via hybrid bounded BM25 + utterance index
    natural_vi_cases = (
        (
            "Kiểm tra vì sao trang web tải chậm bị giật bố cục CLS và LCP quá cao",
            "web-vitals-and-performance-profiler",
        ),
        (
            "Giả lập phản hồi lỗi 500 cho truy vấn GraphQL khi test giao diện",
            "api-network-mocking-interception",
        ),
        (
            "Rà soát lỗi thiếu nhãn ARIA cho trình đọc màn hình và thứ tự phím Tab",
            "wcag-audit-patterns",
        ),
        (
            "kiem tra vi sao trang web tai cham bi giat bo cuc cls va lcp",
            "web-vitals-and-performance-profiler",
        ),
        (
            "ddawng nhaapj bi rot phien cookie het han",
            "auth-session-and-cookie-manager",
        ),
    )
    for prompt_text, expected_skill in natural_vi_cases:
        res = evaluate_skill_first_trigger(prompt=prompt_text, target_files=[], repo_root=REPO_ROOT)
        assert res["is_triggered"] is True, prompt_text
        assert res["recommended_skill"] == expected_skill, f"{prompt_text} -> {res['recommended_skill']}"
        assert 0.35 <= res["calibrated_confidence"] <= 1.0, prompt_text
        assert isinstance(res["matched_utterances"], list)
        assert len(res["matched_utterances"]) >= 1, prompt_text

    # Meta-workflow routing (/review, /solo, /super-plan) remains intact with high confidence
    for meta_prompt, meta_id in (
        ("/review Check diff and HMAC receipts against implementation_plan.md", "review"),
        ("/solo Execute M4 milestones sequentially", "solo"),
        ("/super-plan Design calibrated router architecture", "super-plan"),
    ):
        m_res = evaluate_skill_first_trigger(prompt=meta_prompt, target_files=[], repo_root=REPO_ROOT)
        assert m_res["is_triggered"] is True
        assert m_res["recommended_skill"] == meta_id
        assert m_res["calibrated_confidence"] >= 0.9


def test_negative_hybrid_per_route_threshold_abstention():
    """Negative (TC-05): Generic non-skill and vague prompts abstain cleanly below per-route thresholds."""
    for non_skill in (
        "Update copyright year in footer banner",
        "Rename local variable foo to bar in helper",
    ):
        res = evaluate_skill_first_trigger(prompt=non_skill, target_files=[], repo_root=REPO_ROOT)
        assert res["is_triggered"] is False, non_skill
        assert res["recommended_skill"] is None, non_skill
        assert 0.0 <= res["calibrated_confidence"] <= 1.0
        assert res["calibrated_confidence"] < 0.45

    # Vague Vietnamese still triggers clarification rather than hijacking an unrelated skill
    vague = evaluate_skill_first_trigger(
        prompt="May in bi ket giay hoai luon",
        target_files=[],
        repo_root=REPO_ROOT,
    )
    assert vague["is_triggered"] is False
    assert vague["recommended_skill"] is None
    assert vague["needs_clarification"] is True


def test_boundary_and_cli_hybrid_router_calibrated_json_contract():
    """Boundary/CLI (TC-05/TC-06): Calibrated keys present on empty inputs and CLI --json output."""
    from tools.core.skill_router import get_utterance_router_index

    idx = get_utterance_router_index()
    assert idx.match_routes("") == []
    assert idx.match_routes("   ") == []
    assert idx.calibrator.predict_proba(0.05) < 0.30
    assert idx.calibrator.predict_proba(0.50) > 0.85

    empty_res = evaluate_skill_first_trigger(prompt="", target_files=[], repo_root=REPO_ROOT)
    assert empty_res["calibrated_confidence"] == 0.0
    assert empty_res["matched_utterances"] == []

    script = os.path.join(REPO_ROOT, "tools", "core", "skill_router.py")
    proc = subprocess.run(
        [
            sys.executable,
            script,
            "--prompt",
            "Rà soát lỗi thiếu nhãn ARIA cho trình đọc màn hình và thứ tự phím Tab",
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["recommended_skill"] == "wcag-audit-patterns"
    assert 0.35 <= data["calibrated_confidence"] <= 1.0
    assert isinstance(data["matched_utterances"], list)
    assert len(data["matched_utterances"]) >= 1

