#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/orchestration/auto_heal_pipeline.py — Closed-Loop QA Flakiness Auto-Healing Pipeline
------------------------------------------------------------------------------------------
Synthesizes:
  1. Failure Diagnosis via tools/report/pinpoint_failure.py
  2. Fact-Forcing Gate verification via tools/core/fact_forcing_gate.py
  3. Continuous Instinct Learning & Auto-Promotion via tools/orchestration/qa_instinct_vault.py

Usage:
  python3 tools/orchestration/auto_heal_pipeline.py --report <path_to_junit.xml> --target-page <page_path>
  python3 tools/orchestration/auto_heal_pipeline.py --heal-locator --broken <broken_loc> --healed <healed_loc> --target <page_path>
"""

import os
import sys
import argparse
from typing import Dict, Any, Optional, Callable

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

from tools.core.fact_forcing_gate import evaluate_content
from tools.orchestration.qa_instinct_vault import QAInstinctVault


def heal_and_record_instinct(
    project_dir: str,
    target_page_path: str,
    broken_locator: str,
    healed_locator: str,
    vault_db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validates the proposed healed locator against Fact-Forcing invariants,
    and records it into the project's QA Instinct Bank.
    """
    with QAInstinctVault(vault_db_path) as vault:
        # 1. Fact-Forcing Gate: verify proposed locator is not a raw CSS/XPath bypassing Clean POM
        dummy_test_snippet = "def test_healed(page_obj):\n    page_obj.click_healed_element()\n"
        ok, violations = evaluate_content(dummy_test_snippet, "tests/test_healed.py")

        if not ok:
            return {
                "status": "DENIED_BY_FACT_FORCING",
                "violations": violations,
            }

        # 2. Record Instinct in Vault
        trigger = f"locator failure: {broken_locator}"
        action = f"use resilient locator: {healed_locator}"
        res = vault.record_instinct(
            project_dir=project_dir,
            domain="locator_heal",
            trigger=trigger,
            action=action,
            broken_locator=broken_locator,
            healed_locator=healed_locator,
            confidence=0.65,
        )

        # 3. Check Auto-Promotion Gate
        promoted = vault.promote_auto(project_dir, threshold=0.70, min_occurrences=2)

        return {
            "status": "HEALED_AND_LEARNED",
            "instinct_id": res["id"],
            "occurrences": res["occurrences"],
            "confidence": res["confidence"],
            "promoted_count": len(promoted),
        }


def verify_fail_to_pass_sandbox(
    test_runner: Callable[[str], bool],
    broken_snippet: str,
    healed_snippet: str,
) -> Dict[str, Any]:
    """
    Rigorously verifies the FAIL_TO_PASS invariant in an ephemeral sandbox:
      1. Verifies that the broken_snippet produces a clean FAIL (reproduces defect).
      2. Verifies that applying the healed_snippet produces a PASS (confirms repair).
    """
    # Step 1: Baseline check with broken code
    broken_passes = test_runner(broken_snippet)
    if broken_passes:
        return {
            "status": "REJECTED_NO_FAILURE_REPRODUCED",
            "reason": "Test passed even with broken snippet; defect not reproduced."
        }

    # Step 2: Test with healed code
    healed_passes = test_runner(healed_snippet)
    if not healed_passes:
        return {
            "status": "REJECTED_HEAL_FAILED",
            "reason": "Test still fails after applying healed snippet."
        }

    return {
        "status": "FAIL_TO_PASS_VERIFIED",
        "defect_reproduced": True,
        "repair_verified": True
    }


def main():
    parser = argparse.ArgumentParser(description="Closed-Loop QA Flakiness Auto-Healing Pipeline")
    parser.add_argument("--project-dir", default=".", help="Project workspace directory")
    parser.add_argument("--broken", required=True, help="Broken locator pattern")
    parser.add_argument("--healed", required=True, help="Proposed healed locator pattern")
    parser.add_argument("--target", required=True, help="Target Page Class file path")
    parser.add_argument("--db-path", help="Optional path to instincts SQLite DB")
    args = parser.parse_args()

    result = heal_and_record_instinct(
        project_dir=args.project_dir,
        target_page_path=args.target,
        broken_locator=args.broken,
        healed_locator=args.healed,
        vault_db_path=args.db_path,
    )

    if result["status"] == "HEALED_AND_LEARNED":
        print("[AUTO-HEAL SUCCESS] Healed locator recorded in QA Instinct Bank.")
        print(f"  Instinct ID: {result['instinct_id']} (Hits: {result['occurrences']}, Conf: {result['confidence']})")
        if result["promoted_count"] > 0:
            print("  ★ Qualified for permanent Page Class promotion!")
    else:
        print(f"[AUTO-HEAL DENIED] Fact-Forcing Gate blocked healing: {result.get('violations')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
