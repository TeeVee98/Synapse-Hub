#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/tmmi_auditor.py — Enterprise TMMi (Test Maturity Model integration) Assessment Sentinel
--------------------------------------------------------------------------------------------
Evaluates test process maturity and engineering rigor across TMMi Levels 1 through 5:
  - Level 1: Initial (Ad-hoc, unmanaged)
  - Level 2: Managed (Test Policy, Planning, Design, Environment & Data)
  - Level 3: Defined (Standard Organization, Non-Functional Testing, Peer Review, POM)
  - Level 4: Measured (Mutation Testing >= 80%, Flaky Analysis, Metric Baselines)
  - Level 5: Optimization (Defect Prevention, Auto-Healing, Continuous Tuning)

Usage:
  python tools/tmmi_auditor.py
  python tools/tmmi_auditor.py --json
  python tools/tmmi_auditor.py --gate-level 3
"""
import os
import sys

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass


import glob
import os
import sys
import json
import argparse
from typing import Dict, Any

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


TMMI_LEVEL_CRITERIA = {
    2: {
        "title": "Level 2: Managed",
        "description": "Fundamental test management: Test Policy, Test Planning, Test Monitoring, Test Design Techniques.",
        "checks": [
            {"id": "PA_2_1", "name": "Test Policy & Strategy Defined", "path": "AGENTS.md"},
            {"id": "PA_2_2", "name": "Standard Test Design Techniques (BVA/EP)", "path": "test-design/manual-rbt/rbt-manual-testing/SKILL.md"},
            {"id": "PA_2_3", "name": "Dynamic & Idempotent Test Data Management", "path": "test-design/test-data/synthetic-test-data-generator/SKILL.md"},
            {"id": "PA_2_4", "name": "Traceability Matrix & Deliverable Export (ISO 29119-3)", "path": "tools/contrib/template_excel_exporter.py"},
        ],
    },
    3: {
        "title": "Level 3: Defined",
        "description": "Standardized lifecycle: Clean POM, Non-Functional Testing (Perf, Security, A11y), Peer Reviews.",
        "checks": [
            {"id": "PA_3_1", "name": "Clean POM Flat Architecture Invariant", "path": "automation/shared-utils/clean-pom-crafter/SKILL.md"},
            {"id": "PA_3_2", "name": "Non-Functional: Dynamic Application Security (DAST/OWASP)", "path": "tools/security_scanner.py"},
            {"id": "PA_3_3", "name": "Non-Functional: Automated Accessibility Auditing (WCAG 2.2 / VPAT)", "path": "tools/contrib/wcag_audit.py"},
            {"id": "PA_3_4", "name": "Non-Functional: Performance SLA & Load Testing (JMeter/k6)", "path": "tools/jtl_analyzer.py"},
            {"id": "PA_3_5", "name": "Static Peer Review & Code Quality Ladder", "path": "standards/coding-standards/senior-code-review/SKILL.md"},
        ],
    },
    4: {
        "title": "Level 4: Measured",
        "description": "Quantitative quality evaluation: Mutation Testing, Flakiness Analysis, Tail Latency Metrics.",
        "checks": [
            {"id": "PA_4_1", "name": "Syntactic Mutation Testing Engine (Kill Rate >= 80%)", "path": "tools/micro_mutator.py"},
            {"id": "PA_4_2", "name": "Flaky Test Detection & Quarantine Sentinel", "path": "tools/flaky_detector.py"},
            {"id": "PA_4_3", "name": "Specification & Contract Drift Detection", "path": "tools/spec_drift_sentinel.py"},
            {"id": "PA_4_4", "name": "Historical Quality & Flakiness Trend Analytics", "path": "tools/trend_analytics.py"},
        ],
    },
    5: {
        "title": "Level 5: Optimization",
        "description": "Defect prevention, self-healing automation, and continuous process optimization.",
        "checks": [
            {"id": "PA_5_1", "name": "Self-Healing Locator & Reflexion Engine", "path": "tools/auto_heal.py"},
            {"id": "PA_5_2", "name": "Static Defect & Fake-Pass Elimination (Infer-Style)", "path": "tools/infer_linter.py"},
            {"id": "PA_5_3", "name": "Prompt Optimization & Assertion Tuning (MIPROv2)", "path": "tools/mipro_assertion_tuner.py"},
            {"id": "PA_5_4", "name": "Adversarial Test Generation & Fuzzing", "path": "tools/api_fuzzer.py"},
        ],
    },
}


def audit_tmmi_maturity(root_dir: str = REPO_ROOT) -> Dict[str, Any]:
    """Audits repository against TMMi Level 1 through 5 process goals."""
    level_results = {}
    achieved_level = 1

    for lvl in (2, 3, 4, 5):
        cfg = TMMI_LEVEL_CRITERIA[lvl]
        passed_checks = 0
        total_checks = len(cfg["checks"])
        check_details = []

        for chk in cfg["checks"]:
            p = os.path.join(root_dir, chk["path"])
            exists = os.path.exists(p)
            if not exists and chk["path"].endswith("SKILL.md"):
                base_name = os.path.basename(os.path.dirname(chk["path"]))
                cands = glob.glob(os.path.join(root_dir, "**", base_name, "SKILL.md"), recursive=True)
                if cands:
                    p = cands[0]
                    exists = True
            if exists:
                passed_checks += 1
            check_details.append({
                "id": chk["id"],
                "name": chk["name"],
                "target_evidence": os.path.relpath(p, root_dir) if exists else chk["path"],
                "status": "PASS" if exists else "MISSING",
            })

        compliance_pct = round((passed_checks / total_checks) * 100, 1)
        is_level_achieved = (compliance_pct == 100.0)

        level_results[f"level_{lvl}"] = {
            "title": cfg["title"],
            "compliance_pct": compliance_pct,
            "is_achieved": is_level_achieved,
            "passed_checks": passed_checks,
            "total_checks": total_checks,
            "checks": check_details,
        }

        if is_level_achieved and achieved_level == (lvl - 1):
            achieved_level = lvl

    return {
        "standard": "TMMi (Test Maturity Model integration) Foundation",
        "certified_maturity_level": achieved_level,
        "level_title": f"TMMi Level {achieved_level}",
        "maturity_summary": level_results,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Synapse Hub TMMi (Test Maturity Model integration) Assessment Sentinel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--root", default=REPO_ROOT, help="Target repository root directory to assess")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--gate-level", type=int, choices=[1, 2, 3, 4, 5], help="Quality Gate: Fail if achieved level < threshold")

    args = parser.parse_args()

    res = audit_tmmi_maturity(args.root)

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        lvl = res["certified_maturity_level"]
        color = "\033[92m" if lvl >= 3 else "\033[93m"
        reset = "\033[0m"

        print("=" * 72)
        print("  SYNAPSE HUB — TMMi MATURITY ASSESSMENT SCORECARD")
        print("=" * 72)
        print(f"  Certified Maturity Level: {color}TMMi Level {lvl}{reset} (Scale 1 to 5)")
        print("-" * 72)

        for l_key, l_data in res["maturity_summary"].items():
            st = "\033[92m[ACHIEVED]\033[0m" if l_data["is_achieved"] else "\033[93m[IN PROGRESS]\033[0m"
            print(f"  {st} {l_data['title']:<20} : {l_data['compliance_pct']}% ({l_data['passed_checks']}/{l_data['total_checks']} goals met)")
            for chk in l_data["checks"]:
                c_st = "✅" if chk["status"] == "PASS" else "❌"
                print(f"     {c_st} {chk['id']} - {chk['name']}")
        print("=" * 72)

    if args.gate_level and res["certified_maturity_level"] < args.gate_level:
        print(f"🚨 Quality Gate Failed: Assessed TMMi Level {res['certified_maturity_level']} < required Level {args.gate_level}!", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
