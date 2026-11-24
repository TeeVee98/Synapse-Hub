#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for PocockGriller story-aware English interrogation engine."""

import json
import os
import re
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.contrib import interview_story
from tools.contrib.interview_story import DOMAIN_QUESTIONS, PocockGriller

_NON_ASCII_VI_RE = re.compile(r"[^\x00-\x7F]")


def _assert_english_only(questions):
    for q in questions:
        assert not _NON_ASCII_VI_RE.search(q["question"]), f"Non-ASCII found in question: {q['question']}"
        assert isinstance(q["is_multi_select"], bool)
        assert isinstance(q["options"], list) and len(q["options"]) >= 2
        assert any(opt.startswith("(Recommended)") for opt in q["options"])
        for opt in q["options"]:
            assert not _NON_ASCII_VI_RE.search(opt), f"Non-ASCII found in option: {opt}"


def test_interview_story_positive_domain_awareness():
    """Positive: payment, auth, upload, state_machine, concurrency stories trigger targeted English questions."""
    griller = PocockGriller()

    for domain_key, q_obj in DOMAIN_QUESTIONS.items():
        assert q_obj["is_multi_select"] is False, f"{domain_key} should be single-select"

    payment_story = (
        "As a customer, I want to pay my invoice via Stripe credit card checkout "
        "with currency USD and refund handling."
    )
    payment_qs = griller.generate_frontier_questions(payment_story, grill_me=False)
    _assert_english_only(payment_qs)
    payment_domains = griller.detect_domains(payment_story)
    assert "payment" in payment_domains
    pay_domain_qs = [q for q in payment_qs if "Payment Idempotency" in q["question"]]
    assert len(pay_domain_qs) == 1
    assert pay_domain_qs[0]["is_multi_select"] is False

    auth_story = (
        "As an admin user, I want to log in with MFA OTP and RBAC role permissions "
        "before uploading KYC PDF files."
    )
    auth_qs = griller.generate_frontier_questions(auth_story, grill_me=True)
    _assert_english_only(auth_qs)
    auth_domains = griller.detect_domains(auth_story)
    assert "auth" in auth_domains
    assert "upload" in auth_domains
    assert any("Pocock Concurrency Frontier" in q["question"] and q["is_multi_select"] is False for q in auth_qs)
    assert len(auth_qs) > len(payment_qs)

    concurrent_story = "Users concurrently reserve limited stock voucher slots."
    conc_qs = griller.generate_frontier_questions(concurrent_story, grill_me=True)
    assert not any("Pocock Concurrency Frontier" in q["question"] for q in conc_qs)
    assert any("Resource Contention & Concurrency Frontier" in q["question"] for q in conc_qs)


def test_interview_story_boundary_empty_and_oversized():
    """Boundary: empty, whitespace-only, and >100KB stories produce valid English questions safely."""
    griller = PocockGriller()

    empty_qs = griller.generate_frontier_questions("", grill_me=False)
    assert len(empty_qs) >= 2
    _assert_english_only(empty_qs)

    ws_qs = griller.generate_frontier_questions("   \n\t  ", grill_me=False)
    assert len(ws_qs) >= 2
    _assert_english_only(ws_qs)

    huge_story = "As a user I want to approve pending invoice state transitions. " * 3000
    assert len(huge_story) > 100_000
    huge_qs = griller.generate_frontier_questions(huge_story, grill_me=True)
    assert len(huge_qs) >= 3
    _assert_english_only(huge_qs)
    assert "state_machine" in griller.detect_domains(huge_story)


def test_interview_story_cli_negative_missing_file(tmp_path, monkeypatch, capsys):
    """Negative: non-existent --story-file exits cleanly with code 1 without stacktrace."""
    missing = tmp_path / "does_not_exist.md"
    monkeypatch.setattr(sys, "argv", ["interview_story.py", "--story-file", str(missing), "--json"])
    rc = interview_story.main()
    captured = capsys.readouterr()
    assert rc == 1
    err_payload = json.loads(captured.err)
    assert err_payload["status"] == "ERROR"


def test_interview_story_cli_flags_and_story_file(tmp_path, monkeypatch, capsys):
    """CLI Flags: --story-file, inline positional story, --grill-me, and --json emit valid JSON."""
    story_file = tmp_path / "checkout_story.md"
    story_file.write_text(
        "As a shopper, I want to submit an order concurrently with limited stock inventory "
        "and transition order status from Draft to Paid.",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["interview_story.py", "--story-file", str(story_file), "--grill-me", "--json"],
    )
    rc = interview_story.main()
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["story_source"] == str(story_file)
    assert "concurrency" in payload["detected_domains"]
    assert "state_machine" in payload["detected_domains"]
    assert isinstance(payload["questions"], list) and len(payload["questions"]) >= 4
    _assert_english_only(payload["questions"])

    # Positional inline story + default fallback when empty
    monkeypatch.setattr(sys, "argv", ["interview_story.py", "As a buyer I want to pay via card", "--json"])
    assert interview_story.main() == 0
    inline_payload = json.loads(capsys.readouterr().out)
    assert "As a buyer" in inline_payload["story"]
    assert "payment" in inline_payload["detected_domains"]

    monkeypatch.setattr(sys, "argv", ["interview_story.py", "--json"])
    assert interview_story.main() == 0
    default_payload = json.loads(capsys.readouterr().out)
    assert default_payload["story_source"] == "default_sample"
    assert "approve invoices" in default_payload["story"]
