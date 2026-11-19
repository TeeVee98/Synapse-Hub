#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/report/sarif_exporter.py — Standardized OASIS SARIF v2.1.0 Exporter
-------------------------------------------------------------------------
Exports Synapse Hub 10 Quality Gates, infer_linter, and security audit
findings into OASIS SARIF v2.1.0 format for direct ingestion into GitHub
Code Scanning, GitLab SAST, and DevSecOps pipelines.

Usage:
  python3 tools/report/sarif_exporter.py --input <results.json> --output <report.sarif>
  python3 tools/report/sarif_exporter.py --scan-dir <repo_root> --output <report.sarif>
"""

import os
import json
import argparse
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

SARIF_SCHEMA_V2_1_0 = "https://docs.oasis-open.org/sarif/sarif/v2.1.0/cos01/schemas/sarif-schema-2.1.0.json"
TOOL_NAME = "Synapse-Hub-Quality-Sentinel"
TOOL_VERSION = "4.6.3"
TOOL_INFORMATION_URI = "https://github.com/TeeVee98/Synapse-Hub"

# CWE mappings for common QA defects
RULE_DEFINITIONS = {
    "SYNAPSE001_FAKE_PASS": {
        "id": "SYNAPSE001",
        "name": "FakePassNoAssertion",
        "shortDescription": {"text": "Test contains zero assertions or fake passes."},
        "fullDescription": {"text": "A test execution block completed with 0 assertions or tautological checks, violating Truth Anchor."},
        "defaultConfiguration": {"level": "error"},
        "helpUri": "https://github.com/TeeVee98/Synapse-Hub#truth-anchor",
        "properties": {"tags": ["quality", "truth-anchor", "CWE-398"]},
    },
    "SYNAPSE002_SWALLOWED_EXCEPTION": {
        "id": "SYNAPSE002",
        "name": "SwallowedException",
        "shortDescription": {"text": "Silent catch block or suppressed exception."},
        "fullDescription": {"text": "An exception was swallowed using empty except/catch or dummy assignment."},
        "defaultConfiguration": {"level": "error"},
        "helpUri": "https://github.com/TeeVee98/Synapse-Hub#truth-anchor",
        "properties": {"tags": ["reliability", "CWE-390"]},
    },
    "SYNAPSE003_STATIC_SLEEP": {
        "id": "SYNAPSE003",
        "name": "StaticSleepAntiPattern",
        "shortDescription": {"text": "Static sleep detected in test automation script."},
        "fullDescription": {"text": "Static sleeps cause flakiness and slow execution; dynamic smart waits are required."},
        "defaultConfiguration": {"level": "warning"},
        "helpUri": "https://github.com/TeeVee98/Synapse-Hub#smart-waits",
        "properties": {"tags": ["flakiness", "performance"]},
    },
    "SYNAPSE004_CLEAN_POM_VIOLATION": {
        "id": "SYNAPSE004",
        "name": "CleanPomFlatArchitectureViolation",
        "shortDescription": {"text": "Raw selector in test script or deep Page Class inheritance."},
        "fullDescription": {"text": "Test scripts must only invoke business methods on Page Classes extending BasePage directly."},
        "defaultConfiguration": {"level": "error"},
        "helpUri": "https://github.com/TeeVee98/Synapse-Hub#clean-pom",
        "properties": {"tags": ["architecture", "maintainability"]},
    },
    "SYNAPSE005_CREDENTIAL_LEAK": {
        "id": "SYNAPSE005",
        "name": "HardcodedCredentialDetected",
        "shortDescription": {"text": "Hardcoded secret, private key, or password detected."},
        "fullDescription": {"text": "Sensitive credentials committed in code or test fixtures violate Gate 6."},
        "defaultConfiguration": {"level": "error"},
        "helpUri": "https://github.com/TeeVee98/Synapse-Hub#security",
        "properties": {"tags": ["security", "CWE-798"]},
    },
}


def build_sarif_log(results: List[Dict[str, Any]], rules: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Assembles a valid OASIS SARIF v2.1.0 document."""
    if rules is None:
        rules = list(RULE_DEFINITIONS.values())

    run: Dict[str, Any] = {
        "tool": {
            "driver": {
                "name": TOOL_NAME,
                "version": TOOL_VERSION,
                "informationUri": TOOL_INFORMATION_URI,
                "rules": rules,
            }
        },
        "results": results,
        "invocations": [
            {
                "executionSuccessful": True,
                "endTimeUtc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        ],
    }

    return {
        "$schema": SARIF_SCHEMA_V2_1_0,
        "version": "2.1.0",
        "runs": [run],
    }


def format_result(
    rule_id: str,
    message: str,
    file_path: str,
    start_line: int = 1,
    start_column: int = 1,
    level: str = "error",
) -> Dict[str, Any]:
    """Formats a single diagnostic finding into a SARIF result item."""
    return {
        "ruleId": rule_id,
        "level": level,
        "message": {"text": message},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": file_path.replace("\\", "/"),
                        "uriBaseId": "%SRCROOT%",
                    },
                    "region": {
                        "startLine": max(1, start_line),
                        "startColumn": max(1, start_column),
                    },
                }
            }
        ],
    }


def export_sarif(findings: List[Dict[str, Any]], output_path: str) -> str:
    """Exports structured findings list to a SARIF v2.1.0 JSON file."""
    sarif_results = []
    for item in findings:
        sarif_results.append(
            format_result(
                rule_id=item.get("rule_id", "SYNAPSE001"),
                message=item.get("message", "Quality violation detected"),
                file_path=item.get("file_path", "unknown"),
                start_line=item.get("line", 1),
                level=item.get("level", "error"),
            )
        )

    sarif_data = build_sarif_log(sarif_results)
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sarif_data, f, indent=2, ensure_ascii=False)

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Export Synapse Hub QA Findings to OASIS SARIF v2.1.0")
    parser.add_argument("--input", help="Path to input JSON findings file")
    parser.add_argument("--output", default="reports/synapse_quality.sarif", help="Path to output SARIF file")
    args = parser.parse_args()

    findings = []
    if args.input and os.path.exists(args.input):
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                findings = data
            elif isinstance(data, dict):
                findings = data.get("findings", data.get("defects", []))

    exported = export_sarif(findings, args.output)
    print(f"[SARIF EXPORT] Successfully exported {len(findings)} finding(s) to: {exported}")


if __name__ == "__main__":
    main()
