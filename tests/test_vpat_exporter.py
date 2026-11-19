#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

from tools.contrib.vpat_exporter import (
    VPAT_CRITERIA_CATALOG,
    compile_vpat_assessment,
    export_vpat_markdown,
    export_vpat_html,
    audit_html_source,
)


def test_vpat_catalog_structure():
    assert len(VPAT_CRITERIA_CATALOG) >= 12
    for c in VPAT_CRITERIA_CATALOG:
        assert "wcag_id" in c
        assert "name" in c
        assert "level" in c
        assert "section_508" in c
        assert "en_301_549" in c
        assert "desc" in c


def test_compile_vpat_clean():
    res = compile_vpat_assessment(
        violations=[],
        product_name="Clean Web Portal",
        product_version="2.0.0",
    )
    assert res["vpat_version"].startswith("2.5")
    assert res["conformance_summary"]["supports"] == len(VPAT_CRITERIA_CATALOG)
    assert res["conformance_summary"]["does_not_support"] == 0
    assert res["conformance_summary"]["conformance_rate_pct"] == 100.0


def test_compile_vpat_with_violations():
    mock_violations = [
        {"criterion": "1.1.1 Non-text Content (Level A)", "severity": "CRITICAL", "message": "Missing alt on image"},
        {"criterion": "1.1.1 Non-text Content (Level A)", "severity": "CRITICAL", "message": "Missing alt on icon"},
        {"criterion": "1.1.1 Non-text Content (Level A)", "severity": "CRITICAL", "message": "Missing alt on banner"},
        {"criterion": "1.4.3 Contrast (Minimum) (Level AA)", "severity": "MEDIUM", "message": "Contrast ratio 3.8:1 below 4.5:1"},
    ]
    res = compile_vpat_assessment(
        violations=mock_violations,
        product_name="Defective Web Portal",
    )
    assert res["conformance_summary"]["does_not_support"] >= 1  # 1.1.1 has 3 violations
    assert res["conformance_summary"]["partially_supports"] >= 1  # 1.4.3 has 1 violation
    assert res["conformance_summary"]["conformance_rate_pct"] < 100.0


def test_export_markdown_and_html():
    res = compile_vpat_assessment(violations=[])
    md = export_vpat_markdown(res)
    assert "# Accessibility Conformance Report (VPAT® Version 2.5)" in md
    assert "Section 508 Chapter 5" in md
    assert "EN 301 549 Clause 9" in md

    html = export_vpat_html(res)
    assert "<!DOCTYPE html>" in html
    assert "Accessibility Conformance Report (VPAT® 2.5)" in html
    assert "100.0%" in html


def test_audit_html_source():
    bad_html = "<html><body><img src='test.jpg'><button></button></body></html>"
    viols = audit_html_source(bad_html)
    assert len(viols) >= 1
    assert any("1.1.1" in v.get("criterion", "") for v in viols)


def test_audit_html_source_parser_error_handling(monkeypatch):
    """Verifies Truth Anchor: parser failures produce CRITICAL violation rather than fake pass."""
    import tools.contrib.wcag_audit as wcag_mod

    def buggy_feed(self, content):
        raise ValueError("Corrupted token stream")

    monkeypatch.setattr(wcag_mod.WCAGAuditor, "feed", buggy_feed)
    viols = audit_html_source("<malformed")
    assert len(viols) == 1
    assert viols[0]["severity"] == "CRITICAL"
    assert "4.1.1" in viols[0]["criterion"]
    assert "Corrupted token stream" in viols[0]["message"]
