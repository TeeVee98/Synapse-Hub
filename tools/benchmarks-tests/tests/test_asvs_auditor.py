#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

from tools.asvs_auditor import (
    ASVS_CHAPTERS,
    ASVS_REQUIREMENTS,
    generate_asvs_checklist_markdown,
    run_asvs_audit,
    ASVSProbeRunner,
)


def test_asvs_chapters_and_requirements():
    assert len(ASVS_CHAPTERS) == 14
    assert "V1" in ASVS_CHAPTERS
    assert "V14" in ASVS_CHAPTERS
    assert len(ASVS_REQUIREMENTS) >= 25

    # Verify each requirement has mandatory attributes
    for r in ASVS_REQUIREMENTS:
        assert "id" in r
        assert "chapter" in r
        assert "level" in r
        assert r["level"] in (1, 2, 3)
        assert "cwe" in r
        assert "desc" in r


def test_generate_asvs_checklist_markdown():
    md = generate_asvs_checklist_markdown(level=1)
    assert "# OWASP ASVS 4.0.3 Verification Checklist (Level 1)" in md
    assert "Chapter V1:" in md
    assert "V14.4.1" in md

    md_v14 = generate_asvs_checklist_markdown(level=1, chapter="V14")
    assert "Chapter V14:" in md_v14
    assert "Chapter V1:" not in md_v14


def test_run_asvs_audit_offline():
    report = run_asvs_audit(target_url=None, level=1)
    assert report["asvs_version"] == "4.0.3"
    assert report["level"] == 1
    assert report["summary"]["total_requirements"] > 0
    assert report["summary"]["manual_required"] > 0
    assert len(report["requirements"]) == report["summary"]["total_requirements"]


def test_asvs_probe_evaluations_mock():
    runner = ASVSProbeRunner("https://example.com")
    runner.headers_observed = {
        "strict-transport-security": "max-age=31536000; includeSubDomains",
        "content-security-policy": "default-src 'self'",
        "x-frame-options": "DENY",
        "x-content-type-options": "nosniff",
        "referrer-policy": "strict-origin-when-cross-origin",
    }
    runner.cookies_observed = ["session_id=xyz; Secure; HttpOnly; SameSite=Strict"]
    evals = runner.evaluate_asvs_controls()

    assert evals["V9.1.1"]["status"] == "PASS"
    assert evals["V9.2.1"]["status"] == "PASS"
    assert evals["V14.4.1"]["status"] == "PASS"
    assert evals["V14.4.2"]["status"] == "PASS"
    assert evals["V14.4.3"]["status"] == "PASS"
    assert evals["V14.4.4"]["status"] == "PASS"
    assert evals["V3.4.1"]["status"] == "PASS"
    assert evals["V3.4.2"]["status"] == "PASS"
    assert evals["V3.4.3"]["status"] == "PASS"
    assert evals["V7.1.1"]["status"] == "PASS"


def test_asvs_probe_evaluations_fail_mock():
    runner = ASVSProbeRunner("http://insecure-site.example")
    runner.headers_observed = {}
    runner.verbose_error_detected = True
    runner.cors_vulnerable = True

    evals = runner.evaluate_asvs_controls()
    assert evals["V9.1.1"]["status"] == "FAIL"
    assert evals["V9.2.1"]["status"] == "FAIL"
    assert evals["V14.4.1"]["status"] == "FAIL"
    assert evals["V14.5.1"]["status"] == "FAIL"
    assert evals["V7.1.1"]["status"] == "FAIL"
