# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
tests/test_sarif_export.py — Unit tests for SARIF v2.1.0 export in tools.security_scanner
"""

from tools.security.security_scanner import format_sarif


def test_format_sarif_clean_report():
    clean_report = {
        "status": "PASS",
        "timestamp": "2026-11-15T00:00:00Z",
        "checks": {
            "python_dependencies": {"passed": True, "findings": []},
            "npm_dependencies": {"passed": True, "findings": []},
            "threat_model_firewall": {"passed": True, "findings": []},
        },
    }
    sarif = format_sarif(clean_report)
    assert sarif["version"] == "2.1.0"
    assert "$schema" in sarif
    assert len(sarif["runs"]) == 1
    run = sarif["runs"][0]
    assert run["tool"]["driver"]["name"] == "Synapse-Hub Security Sentinel"
    assert len(run["tool"]["driver"]["rules"]) == 3
    assert run["results"] == []


def test_format_sarif_with_findings():
    vuln_report = {
        "status": "FAIL",
        "timestamp": "2026-11-15T00:00:00Z",
        "checks": {
            "python_dependencies": {
                "passed": False,
                "findings": ["Vulnerability found in demo-pkg: CVE-2026-9999"],
            },
            "npm_dependencies": {"passed": True, "findings": []},
            "threat_model_firewall": {
                "passed": False,
                "findings": ["Firewall Failure: Destructive action was NOT blocked"],
            },
        },
    }
    sarif = format_sarif(vuln_report)
    run = sarif["runs"][0]
    results = run["results"]
    assert len(results) == 2
    rule_ids = [r["ruleId"] for r in results]
    assert "SEC002-CWE-1104" in rule_ids
    assert "SEC003-CWE-284" in rule_ids
