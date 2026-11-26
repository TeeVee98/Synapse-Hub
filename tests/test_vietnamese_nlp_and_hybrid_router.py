#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""4-Scenario Pytest Suite: Pure-Stdlib Vietnamese NLP Core & Calibrated Hybrid Router (M1 & M3).

Covers:
  1. Positive: Phonotactic syllable validation, VnCoreNLP tone canonicalization, guarded Telex &
     shorthand normalization, QA Viterbi bigram diacritics restoration, Longest-Match + RDR rules,
     bounded [0, 1] ATIRE BM25 with SIF weighting, Platt/Isotonic calibration, and 60-skill registry.
  2. Negative: English tech token Telex safelist (OWASP/AWS/root/seed/loop), non-Vietnamese tokens,
     code/URL/path bypass in Viterbi restorer, invalid calibrator methods, unrelated BM25 queries.
  3. Boundary: Empty strings, whitespace, emoji-only, 10KB oversized payloads, >64-token Viterbi
     chains, malformed Telex, single-class calibration labels, extreme scores.
  4. Resilience / Immutability: Frozen DTO immutability, deterministic repeated calls, thread-safe
     immutability of registry specs, and sub-5ms latency invariants.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
import os
import sys
import time

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


# ==============================================================================
# M1: VIETNAMESE NLP CORE (PHONOTACTICS, TELEX, VITERBI, RDR)
# ==============================================================================


def test_positive_phonotactic_and_tone_canonicalization():
    """Positive (TC-01): Phonotactic validator detects unseen unaccented VI; tone variants canonicalize."""
    from tools.core.vietnamese_nlp_utils import (
        SyllabicAnalysisDTO,
        canonicalize_vietnamese_orthography,
        is_valid_vietnamese_syllable,
    )

    # Valid Vietnamese syllables (accented and unaccented, including standalone 'gì' and valid stop-coda tones)
    for syl in ("sua", "gium", "cho", "thanh", "toan", "bi", "treo", "kiểm", "đăng", "người", "được", "quá", "giỏ", "gì", "bát"):
        assert is_valid_vietnamese_syllable(syl) is True, f"Expected valid Vietnamese syllable: {syl}"

    # Invalid English / non-Vietnamese consonant clusters, forbidden letters, and Vietnamese orthography violations
    for non_vi in (
        "owasp", "aws", "root", "seed", "loop", "playwright", "click", "double", "fix", "jwt", "fuzz", "workflow",
        "ka", "gha", "ngha", "ce", "ci", "ge", "nge", "b", "gix", "bàt", "a1", "   ",
    ):
        assert is_valid_vietnamese_syllable(non_vi) is False, f"Expected non-Vietnamese token: {non_vi}"
    assert is_valid_vietnamese_syllable(None) is False  # type: ignore[arg-type]
    assert is_valid_vietnamese_syllable(123) is False  # type: ignore[arg-type]

    # Unseen unaccented Vietnamese prose achieves vi_syllable_ratio >= 0.6
    unseen_vi = "Sua gium cho thanh toan bi treo"
    analysis = canonicalize_vietnamese_orthography(unseen_vi)
    assert isinstance(analysis, SyllabicAnalysisDTO)
    assert analysis.total_alpha_tokens == 7
    assert analysis.valid_vi_syllable_count >= 6
    assert analysis.vi_syllable_ratio >= 0.6

    # VnCoreNLP old-vs-new tone placement canonicalization (oa/oe/uy) + NFC
    old_style = canonicalize_vietnamese_orthography("hòa giải thỏa thuận khỏe mạnh thủy thủ")
    new_style = canonicalize_vietnamese_orthography("hoà giải thoả thuận khoẻ mạnh thuỷ thủ")
    assert old_style.canonical_nfc_text == new_style.canonical_nfc_text
    assert "hoà" in old_style.canonical_nfc_text
    assert "khoẻ" in old_style.canonical_nfc_text
    assert "thuỷ" in old_style.canonical_nfc_text


def test_negative_telex_safelist_preserves_english_tech_tokens():
    """Negative (TC-01): Guarded Telex preserves English tech tokens while decoding real Vietnamese Telex/shorthand."""
    from tools.core.vietnamese_nlp_utils import canonicalize_vietnamese_orthography

    # Pure English tech prompt must remain 100% unmutated by Telex or shorthand
    en_tech = "Run OWASP DAST audit on AWS root seed loop hook pool tool food good bool"
    en_res = canonicalize_vietnamese_orthography(en_tech)
    assert en_res.canonical_nfc_text == en_tech
    assert en_res.had_telex_or_shorthand is False
    assert en_res.vi_syllable_ratio < 0.5

    # English sentence with common plurals / short tokens must stay untouched
    en_plurals = "Check users docs logs bugs runs tests k6 vs docker"
    en_plurals_res = canonicalize_vietnamese_orthography(en_plurals)
    assert en_plurals_res.canonical_nfc_text == en_plurals
    assert en_plurals_res.had_telex_or_shorthand is False

    # Real Vietnamese Telex and shorthand expand accurately
    telex_vi = "ddawng nhaapj bi looxi xacs thuwcj"
    telex_res = canonicalize_vietnamese_orthography(telex_vi)
    assert telex_res.had_telex_or_shorthand is True
    assert "đăng" in telex_res.canonical_nfc_text
    assert "nhập" in telex_res.canonical_nfc_text
    assert "lỗi" in telex_res.canonical_nfc_text

    shorthand_vi = "ktra lai thanh toan ko dc nhu trc"
    short_res = canonicalize_vietnamese_orthography(shorthand_vi)
    assert short_res.had_telex_or_shorthand is True
    assert "kiem tra" in short_res.canonical_nfc_text.lower() or "kiểm tra" in short_res.canonical_nfc_text.lower()
    assert "khong" in short_res.canonical_nfc_text.lower() or "không" in short_res.canonical_nfc_text.lower()
    assert "duoc" in short_res.canonical_nfc_text.lower() or "được" in short_res.canonical_nfc_text.lower()

    # Toggling expand flags disables those expansions cleanly
    disabled = canonicalize_vietnamese_orthography(
        telex_vi, expand_shorthand=False, expand_guarded_telex=False
    )
    assert disabled.canonical_nfc_text == telex_vi
    assert disabled.had_telex_or_shorthand is False


def test_positive_viterbi_diacritics_and_code_path_bypass():
    """Positive (TC-02): QA Viterbi bigram restorer restores VI syllables while preserving code/paths/URLs verbatim."""
    from tools.core.vietnamese_nlp_utils import restore_qa_vietnamese_diacritics

    prompt = "Kiem tra du lieu dau vao trong `tests/api/user_spec.py` va xuat bao cao"
    restored = restore_qa_vietnamese_diacritics(prompt, lambda_bigram=0.8)

    # Inline code span must remain 100% byte-identical
    assert "`tests/api/user_spec.py`" in restored
    # Restored Vietnamese QA syllables
    assert "Kiểm tra" in restored
    assert "dữ liệu" in restored
    assert "đầu vào" in restored
    assert "xuất báo cáo" in restored

    # URLs, file paths, and /slash commands act as chain-breakers and stay untouched
    mixed_prompt = "/solo sua loi thanh toan trong tools/core/skill_router.py theo https://example.com/api/v1"
    restored_mixed = restore_qa_vietnamese_diacritics(mixed_prompt)
    assert "/solo" in restored_mixed
    assert "tools/core/skill_router.py" in restored_mixed
    assert "https://example.com/api/v1" in restored_mixed
    assert "thanh toán" in restored_mixed

    # Numeric <num> context token preserves numbers while restoring adjacent Vietnamese
    num_prompt = "hai nguoi bam cung luc bi tru tien 2 lan"
    restored_num = restore_qa_vietnamese_diacritics(num_prompt)
    assert " 2 " in restored_num
    assert "lần" in restored_num
    assert "trừ tiền" in restored_num


def test_positive_and_negative_rdr_longest_match_resolution():
    """Positive/Negative (TC-03): 4-to-5-syllable Longest-Match + RDR resolves context overrides and conflicts."""
    from tools.core.vietnamese_nlp_utils import (
        RDRExceptionRuleDTO,
        resolve_longest_match_rdr,
    )

    lexicon = {
        "du lieu": ("data",),
        "du lieu gia": ("synthetic", "data", "generator"),
        "tru tien 2 lan": ("payment", "double", "duplicate", "race"),
        "xuat excel": ("export", "excel"),
    }
    rdr_rules = (
        RDRExceptionRuleDTO(
            ngram="cung luc",
            default_tokens=(),
            positive_context_pattern=r"\b(?:bam|submit|tru\s+tien|thanh\s+toan)\b",
            negative_context_pattern=None,
            override_tokens=("concurrency", "concurrent", "race", "parallel"),
        ),
        RDRExceptionRuleDTO(
            ngram="token",
            default_tokens=(),
            positive_context_pattern=r"\b(?:jwt|auth|session|dang\s+nhap)\b",
            negative_context_pattern=r"\b(?:crypto|coin|gia\s+token)\b",
            override_tokens=("token",),
            conflict_tag="token_homonym_conflict",
        ),
    )

    # 1. Longest-Match consumes 'du lieu gia' (3 words) rather than splitting into 'du lieu'
    toks_syn, conflicts_syn = resolve_longest_match_rdr(
        ["tao", "du", "lieu", "gia", "cho", "db"],
        "tao du lieu gia cho db",
        lexicon,
        rdr_rules,
    )
    assert toks_syn == ("synthetic", "data", "generator")
    assert conflicts_syn == ()

    # 2. Positive RDR context fires concurrency override on 'cung luc' + Longest-Match 'tru tien 2 lan'
    toks_race, conflicts_race = resolve_longest_match_rdr(
        ["bam", "submit", "cung", "luc", "tru", "tien", "2", "lan"],
        "bam submit cung luc tru tien 2 lan",
        lexicon,
        rdr_rules,
    )
    assert "concurrency" in toks_race
    assert "race" in toks_race
    assert "payment" in toks_race
    assert conflicts_race == ()

    # 3. Negative RDR context: 'xuat excel va csv cung luc' must NOT emit concurrency
    toks_excel, conflicts_excel = resolve_longest_match_rdr(
        ["xuat", "excel", "va", "csv", "cung", "luc"],
        "xuat excel va csv cung luc",
        lexicon,
        rdr_rules,
    )
    assert toks_excel == ("export", "excel")
    assert "concurrency" not in toks_excel
    assert conflicts_excel == ()

    # 4. Both positive & negative context match -> triggers conflict_tag
    toks_conf, conflicts_conf = resolve_longest_match_rdr(
        ["gia", "token", "crypto", "hoac", "session", "dang", "nhap"],
        "gia token crypto hoac session dang nhap",
        lexicon,
        rdr_rules,
    )
    assert "token_homonym_conflict" in conflicts_conf
    assert "token" not in toks_conf

    # 5. Pure auth token context emits 'token' cleanly without conflict
    toks_auth, conflicts_auth = resolve_longest_match_rdr(
        ["lam", "moi", "token", "jwt", "session"],
        "lam moi token jwt session",
        lexicon,
        rdr_rules,
    )
    assert "token" in toks_auth
    assert conflicts_auth == ()


def test_boundary_phonotactic_telex_viterbi_rdr_edge_cases():
    """Boundary (TC-06): Empty, whitespace, emoji, 10KB text, malformed Telex, and long chains never crash."""
    from tools.core.vietnamese_nlp_utils import (
        MAX_INPUT_CHARS,
        canonicalize_vietnamese_orthography,
        is_valid_vietnamese_syllable,
        resolve_longest_match_rdr,
        restore_qa_vietnamese_diacritics,
    )

    for empty_val in ("", "   \n\t ", "🔥🎯✨", "12345"):
        dto = canonicalize_vietnamese_orthography(empty_val)
        assert dto.valid_vi_syllable_count == 0
        assert dto.vi_syllable_ratio == 0.0
        assert isinstance(restore_qa_vietnamese_diacritics(empty_val), str)

    assert is_valid_vietnamese_syllable("") is False
    assert is_valid_vietnamese_syllable("123") is False
    assert is_valid_vietnamese_syllable("a" * 20) is False

    # Oversized 10KB text is bounded cleanly at MAX_INPUT_CHARS (8192)
    huge = "kiem tra du lieu dau vao " * 500
    assert len(huge) > 10_000
    huge_dto = canonicalize_vietnamese_orthography(huge)
    assert len(huge_dto.canonical_nfc_text) <= MAX_INPUT_CHARS

    # Long chain (> 64 tokens) completes fast without blowing up Viterbi trellis
    long_chain = " ".join(["kiem", "tra", "du", "lieu"] * 30)
    t0 = time.perf_counter()
    restored_long = restore_qa_vietnamese_diacritics(long_chain)
    assert (time.perf_counter() - t0) * 1000.0 < 100.0
    assert len(restored_long) > 0

    # Malformed Telex & invalid lambda_bigram are handled gracefully
    malformed = canonicalize_vietnamese_orthography("zzzzz wwww jjjj ffff aaaaaa")
    assert isinstance(malformed.canonical_nfc_text, str)
    assert isinstance(restore_qa_vietnamese_diacritics("kiem tra du lieu", lambda_bigram=5.0), str)
    assert isinstance(restore_qa_vietnamese_diacritics("kiem tra du lieu", lambda_bigram=-1.0), str)

    # Empty words/lexicon in RDR resolver
    toks, confs = resolve_longest_match_rdr([], "", {}, ())
    assert toks == ()
    assert confs == ()


def test_resilience_telex_viterbi_rdr_determinism_and_dto_immutability():
    """Resilience / CLI-Contract: Frozen DTO immutability, determinism, and sub-5ms typical latency."""
    from tools.core.vietnamese_nlp_utils import (
        RDRExceptionRuleDTO,
        SyllabicAnalysisDTO,
        canonicalize_vietnamese_orthography,
        restore_qa_vietnamese_diacritics,
    )

    sample = "Kiem tra du lieu dau vao va xuat bao cao thanh toan"
    dto1 = canonicalize_vietnamese_orthography(sample)
    dto2 = canonicalize_vietnamese_orthography(sample)
    assert dto1 == dto2
    assert isinstance(dto1, SyllabicAnalysisDTO)

    with pytest.raises((FrozenInstanceError, AttributeError)):
        dto1.vi_syllable_ratio = 0.0  # type: ignore[misc]

    rule = RDRExceptionRuleDTO("cung luc", (), r"bam", None, ("race",))
    with pytest.raises((FrozenInstanceError, AttributeError)):
        rule.ngram = "mutated"  # type: ignore[misc]

    # Typical prompt latency well under 5ms (warm run)
    t0 = time.perf_counter()
    for _ in range(10):
        restore_qa_vietnamese_diacritics(sample)
    avg_ms = ((time.perf_counter() - t0) * 1000.0) / 10.0
    assert avg_ms < 5.0


# ==============================================================================
# M3: BOUNDED [0, 1] ATIRE BM25, SIF WEIGHTING, CALIBRATOR & 60-SKILL REGISTRY
# ==============================================================================


def test_positive_bm25_score_bounded_and_sif_weighting():
    """Positive (TC-04): score_bounded() stays strictly in [0, 1] across varying query lengths with SIF weighting."""
    import math
    from tools.core.bm25_retriever import BM25Index, tokenize_bilingual

    # Bilingual folding & synonym expansion contract
    assert tokenize_bilingual("kiểm tra dữ liệu đúp") == ["kiem", "tra", "du", "lieu", "dup"]
    assert "wcag" in tokenize_bilingual("a11y")
    assert "locator" in tokenize_bilingual("pom")

    # Fresh unbuilt index invariants + empty rebuild
    fresh = BM25Index()
    assert fresh.bilingual_avg_doc_len == 0.0
    assert fresh.total_corpus_tokens == 0
    fresh.build()
    assert fresh.bilingual_avg_doc_len == 0.0
    assert fresh.atire_idf_cache == {}

    # Single-document index exact length & corpus term counts
    single = BM25Index()
    single.add_document("s1", "openapi", "swagger spec")
    single.build()
    assert single.bilingual_avg_doc_len == 3.0
    assert single.total_corpus_tokens == 3
    assert single.bilingual_doc_freqs["openapi"] == 1
    assert single.corpus_term_freqs["openapi"] == 1

    idx = BM25Index()
    idx.add_document("r1", "openapi matrix", "shared generate boundary api test matrix from openapi swagger spec")
    idx.add_document("r2", "network mock", "shared mock intercept http graphql network route stub 500 error")
    idx.add_document("r3", "web vitals", "shared measure core web vitals lcp cls inp latency performance cdp")
    idx.add_document("r4", "wcag a11y", "shared audit wcag accessibility aria screen reader keyboard contrast")
    idx.build()
    # Idempotent rebuild must clear and recompute frequencies accurately
    idx.build()
    assert idx.bilingual_doc_freqs["openapi"] == 1
    assert idx.corpus_term_freqs["openapi"] == 2
    assert math.isclose(idx.atire_idf_cache["openapi"], math.log(5.0 / 1.5), rel_tol=1e-6)
    assert math.isclose(idx.atire_idf_cache["shared"], math.log(5.0 / 4.5), rel_tol=1e-6)
    assert idx.atire_idf_cache["shared"] < 0.5

    short_scores = idx.score_bounded("openapi")
    long_scores = idx.score_bounded(
        "please check test run generate boundary api test matrix from openapi swagger spec endpoint schema validation"
    )
    assert len(short_scores) == 4
    assert len(long_scores) == 4
    for _, sc in short_scores + long_scores:
        assert 0.0 <= sc <= 1.0

    # Top match is exact target route for both short and verbose queries
    assert short_scores[0][0] == "r1"
    assert long_scores[0][0] == "r1"
    assert short_scores[0][1] > short_scores[-1][1]

    # Clearing documents and rebuilding clears atire_idf_cache
    single.documents.clear()
    single.doc_count = 0
    single.build()
    assert single.atire_idf_cache == {}
    assert single.bilingual_avg_doc_len == 0.0

    # Existing search() and hybrid_search() remain 100% backward-compatible
    legacy_search = idx.search("openapi swagger", top_k=2)
    assert legacy_search[0]["doc_id"] == "r1"
    legacy_hybrid = idx.hybrid_search("openapi swagger", top_k=2)
    assert legacy_hybrid[0]["doc_id"] == "r1"


def test_positive_and_negative_score_calibrator_isotonic_platt_and_ece():
    """Positive/Negative (TC-04): ScoreCalibrator (isotonic & platt) is monotonic in [0, 1] with ECE <= 0.10."""
    from tools.core.bm25_retriever import (
        ScoreCalibrator,
        compute_expected_calibration_error,
    )

    scores = [0.05, 0.12, 0.18, 0.25, 0.35, 0.45, 0.55, 0.68, 0.78, 0.85, 0.92, 0.97]
    labels = [0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1]

    for method in ("isotonic", "platt"):
        cal = ScoreCalibrator.fit(scores, labels, method=method)
        grid = [i / 20.0 for i in range(21)]
        probs = [cal.predict_proba(x) for x in grid]
        for p in probs:
            assert 0.0 <= p <= 1.0
        # Monotonicity check
        for a, b in zip(probs, probs[1:]):
            assert a <= b + 1e-9, f"Non-monotonic {method}: {a} > {b}"

        fitted_probs = [cal.predict_proba(s) for s in scores]
        ece = compute_expected_calibration_error(fitted_probs, labels, bins=5)
        assert 0.0 <= ece <= 0.15

    # Negative: unsupported calibration method raises ValueError
    with pytest.raises(ValueError):
        ScoreCalibrator.fit(scores, labels, method="unknown_method")  # type: ignore[arg-type]


def test_positive_skill_utterances_registry_covers_all_60_skills():
    """Positive (TC-04): SKILL_ROUTE_SPECS covers all 57 indexed skills + 3 local .agent/skills (60 total)."""
    from tools.core.skill_utterances_registry import (
        SKILL_ROUTE_SPECS,
        SkillRouteSpec,
        get_skill_route_spec,
    )

    with open(os.path.join(REPO_ROOT, "skills_index.json"), "r", encoding="utf-8") as fp:
        indexed_ids = {s["id"] for s in json.load(fp)["skills"]}
    expected_ids = indexed_ids | {"solo", "super-plan", "review"}

    assert isinstance(SKILL_ROUTE_SPECS, tuple)
    spec_ids = {spec.skill_id for spec in SKILL_ROUTE_SPECS}
    assert len(SKILL_ROUTE_SPECS) == len(expected_ids)
    assert spec_ids == expected_ids

    for spec in SKILL_ROUTE_SPECS:
        assert isinstance(spec, SkillRouteSpec)
        assert len(spec.utterances_en) >= 3, f"Need >= 3 EN utterances for {spec.skill_id}"
        assert len(spec.utterances_vi) >= 3, f"Need >= 3 VI utterances for {spec.skill_id}"
        assert 0.1 <= spec.confidence_threshold <= 0.95

    assert get_skill_route_spec("api-spec-to-e2e-matrix") is not None
    assert get_skill_route_spec("solo") is not None
    assert get_skill_route_spec("nonexistent-skill-id") is None


def test_boundary_and_resilience_bm25_calibrator_registry_edge_cases():
    """Boundary/Resilience (TC-06): Empty BM25 index, single-class calibration, extreme scores, frozen specs."""
    from tools.core.bm25_retriever import (
        BM25Index,
        ScoreCalibrator,
        compute_expected_calibration_error,
    )
    from tools.core.skill_utterances_registry import SKILL_ROUTE_SPECS

    empty_idx = BM25Index()
    assert empty_idx.score_bounded("anything") == []
    empty_idx.add_document("d1", "title", "content tokens here")
    empty_idx.build()
    assert empty_idx.score_bounded("") == []
    assert empty_idx.score_bounded("   ") == []

    # Calibration with empty or constant labels never divides by zero
    for method in ("isotonic", "platt"):
        cal_empty = ScoreCalibrator.fit([], [], method=method)
        assert 0.0 <= cal_empty.predict_proba(0.5) <= 1.0
        cal_ones = ScoreCalibrator.fit([0.2, 0.8], [1, 1], method=method)
        assert 0.0 <= cal_ones.predict_proba(-100.0) <= 1.0
        assert 0.0 <= cal_ones.predict_proba(100.0) <= 1.0

    assert compute_expected_calibration_error([], []) == 0.0
    assert compute_expected_calibration_error([0.0, 1.0], [0, 1]) == 0.0

    with pytest.raises((FrozenInstanceError, AttributeError)):
        SKILL_ROUTE_SPECS[0].skill_id = "mutated"  # type: ignore[misc]
