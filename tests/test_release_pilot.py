#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_release_pilot.py
Validates the 9-domain pilot scorecard aggregator, build/digest bindings,
missing external run pending retention, negative receipt removal/substitution,
QA lead sign-off, checksum archive, and CLI JSON output.
"""

import json
from pathlib import Path
import subprocess
import sys


def _make_green_manifest() -> dict:
    build = "sha-rc-4100"
    pkg_digest = "pkg-sha256-4100"
    req_rev = "URD:v2.0.5+SRS:v2.0.4"
    tpl_digest = "tpl-sha256-900"
    ds_digest = "ds-sha256-20x3"
    rubric_rev = "rubric-v1.0"
    return {
        "candidate_build": build,
        "package_digest": pkg_digest,
        "expected_requirement_revision": req_rev,
        "expected_template_digest": tpl_digest,
        "expected_dataset_digest": ds_digest,
        "expected_rubric_revision": rubric_rev,
        "qa_lead_signoff": {
            "signed_by": "qa.lead@synapse.test",
            "accepted_scope": ["npm", "wheel", "staging-web-api", "mobile-android", "k6", "trace", "eval", "grid", "a11y", "docs"],
        },
        "receipts": {
            "release_verdict": {"candidate_build": build, "package_digest": pkg_digest, "passed": True, "receipt_sha256": "r1"},
            "packaged_skills_ide": {"candidate_build": build, "package_digest": pkg_digest, "passed": True, "receipt_sha256": "r2"},
            "web_api_mobile": {"candidate_build": build, "package_digest": pkg_digest, "passed": True, "receipt_sha256": "r3"},
            "workload_sla": {"candidate_build": build, "package_digest": pkg_digest, "passed": True, "receipt_sha256": "r4"},
            "requirements_reporting": {
                "requirement_revision": req_rev,
                "template_digest": tpl_digest,
                "passed": True,
                "receipt_sha256": "r5",
            },
            "model_orchestration_quality": {
                "dataset_digest": ds_digest,
                "rubric_revision": rubric_rev,
                "passed": True,
                "receipt_sha256": "r6",
            },
            "worker_recovery": {"candidate_build": build, "package_digest": pkg_digest, "passed": True, "receipt_sha256": "r7"},
            "accessibility": {
                "candidate_build": build,
                "package_digest": pkg_digest,
                "human_evidence_status": "verified",
                "passed": True,
                "receipt_sha256": "r8",
            },
            "support_documentation": {"candidate_build": build, "package_digest": pkg_digest, "passed": True, "receipt_sha256": "r9"},
        },
    }


def test_green_pilot_reconciles_nine_scores_and_archives_checksums():
    """Positive: Complete 9-domain manifest binds product/versioned inputs and reaches target score 93."""
    from tools.report.release_pilot import evaluate_pilot_manifest

    manifest = _make_green_manifest()
    report = evaluate_pilot_manifest(manifest)

    assert report["passed"] is True
    assert report["audit_total"] == 67
    assert report["target_total"] == 93
    assert report["max_total"] == 100
    assert report["achieved_total"] == 93
    assert report["pending_domains"] == []
    assert report["failed_domains"] == []
    assert len(report["domains"]) == 9
    assert report["qa_lead_signed"] is True
    assert len(report["archived_checksums"]["receipts"]) == 9
    assert len(report["archived_checksums"]["manifest_sha256"]) == 64


def test_negative_removed_or_substituted_receipt_and_missing_signoff_block_acceptance():
    """Negative: Missing required receipt, substituted build/dataset digest, or missing signoff fail certification."""
    from tools.report.release_pilot import evaluate_pilot_manifest

    # 1. Removed required receipt keeps audit score and enters pending_domains
    removed = _make_green_manifest()
    del removed["receipts"]["workload_sla"]
    res_rem = evaluate_pilot_manifest(removed)
    assert res_rem["passed"] is False
    assert "workload_sla" in res_rem["pending_domains"]
    assert res_rem["domains"]["workload_sla"]["status"] == "pending"
    assert res_rem["domains"]["workload_sla"]["awarded_score"] == 6
    assert res_rem["achieved_total"] == 90

    # 2. Substituted candidate build in release_verdict & mismatched dataset digest in model eval fail
    substituted = _make_green_manifest()
    substituted["receipts"]["release_verdict"]["candidate_build"] = "wrong-build"
    substituted["receipts"]["model_orchestration_quality"]["dataset_digest"] = "stale-dataset"
    res_sub = evaluate_pilot_manifest(substituted)
    assert res_sub["passed"] is False
    assert sorted(res_sub["failed_domains"]) == ["model_orchestration_quality", "release_verdict"]
    assert res_sub["domains"]["release_verdict"]["reason"] == "candidate_build_mismatch"
    assert res_sub["domains"]["model_orchestration_quality"]["reason"] == "versioned_input_mismatch"

    # 3. Missing QA lead sign-off blocks final acceptance
    no_signoff = _make_green_manifest()
    no_signoff["qa_lead_signoff"] = {}
    res_sig = evaluate_pilot_manifest(no_signoff)
    assert res_sig["passed"] is False
    assert res_sig["qa_lead_signed"] is False


def test_boundary_pending_external_run_and_empty_manifest():
    """Boundary: Pending external accessibility review retains audit score (5); empty manifest fails cleanly."""
    from tools.report.release_pilot import evaluate_pilot_manifest

    ext_pending = _make_green_manifest()
    ext_pending["receipts"]["accessibility"]["human_evidence_status"] = "pending"
    res = evaluate_pilot_manifest(ext_pending)
    assert res["passed"] is False
    assert res["domains"]["accessibility"]["status"] == "pending"
    assert res["domains"]["accessibility"]["awarded_score"] == 5
    assert "accessibility" in res["pending_domains"]

    empty_res = evaluate_pilot_manifest({})
    assert empty_res["passed"] is False
    assert empty_res["achieved_total"] == 67
    assert len(empty_res["pending_domains"]) == 9


def test_cli_release_pilot_green_and_negative_rehearsal(tmp_path):
    """CLI: Evaluates green manifest (exit 0) vs copy with removed receipt (exit 1)."""
    green = _make_green_manifest()
    removed = _make_green_manifest()
    removed["receipts"].pop("worker_recovery")

    green_file = tmp_path / "manifest.json"
    bad_file = tmp_path / "manifest_missing.json"
    green_file.write_text(json.dumps(green), encoding="utf-8")
    bad_file.write_text(json.dumps(removed), encoding="utf-8")

    repo_root = Path(__file__).resolve().parent.parent
    script = str(repo_root / "tools" / "report" / "release_pilot.py")

    r_ok = subprocess.run(
        [sys.executable, script, "--manifest", str(green_file), "--json"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert r_ok.returncode == 0, r_ok.stderr
    p_ok = json.loads(r_ok.stdout)
    assert p_ok["passed"] is True
    assert p_ok["achieved_total"] == 93

    r_bad = subprocess.run(
        [sys.executable, script, "--manifest", str(bad_file), "--json"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert r_bad.returncode != 0
    p_bad = json.loads(r_bad.stdout)
    assert p_bad["passed"] is False
    assert "worker_recovery" in p_bad["pending_domains"]
