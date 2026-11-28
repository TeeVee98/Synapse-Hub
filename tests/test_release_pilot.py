#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_release_pilot.py
Validates the 9-domain pilot scorecard aggregator, build/digest bindings,
physical on-disk SHA-256 artifact checksum verification, baseline vs verified
score transparency, missing external run pending retention, QA lead sign-off,
checksum archive, and CLI JSON output.
"""

import hashlib
import json
from pathlib import Path
import subprocess
import sys


def _write_domain_artifact(artifacts_dir: Path, domain_id: str, extra: dict) -> tuple[str, str]:
    """Writes a concrete domain receipt artifact on disk and returns (relative_path, sha256)."""
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    rel_name = f"receipts/{domain_id}.json"
    artifact_file = artifacts_dir / rel_name
    artifact_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {"domain_id": domain_id, **extra}
    raw = json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")
    artifact_file.write_bytes(raw)
    return rel_name, hashlib.sha256(raw).hexdigest()


def _make_green_manifest(base_dir: Path) -> dict:
    build = "sha-rc-4110"
    pkg_digest = "a" * 64
    req_rev = "URD:v2.0.5+SRS:v2.0.4"
    tpl_digest = "b" * 64
    ds_digest = "c" * 64
    rubric_rev = "rubric-v1.0"

    specs = {
        "release_verdict": {"candidate_build": build, "package_digest": pkg_digest, "passed": True},
        "packaged_skills_ide": {"candidate_build": build, "package_digest": pkg_digest, "passed": True},
        "web_api_mobile": {"candidate_build": build, "package_digest": pkg_digest, "passed": True},
        "workload_sla": {"candidate_build": build, "package_digest": pkg_digest, "passed": True},
        "requirements_reporting": {"requirement_revision": req_rev, "template_digest": tpl_digest, "passed": True},
        "model_orchestration_quality": {"dataset_digest": ds_digest, "rubric_revision": rubric_rev, "passed": True},
        "worker_recovery": {"candidate_build": build, "package_digest": pkg_digest, "passed": True},
        "accessibility": {
            "candidate_build": build,
            "package_digest": pkg_digest,
            "human_evidence_status": "verified",
            "passed": True,
        },
        "support_documentation": {"candidate_build": build, "package_digest": pkg_digest, "passed": True},
    }

    receipts = {}
    for domain_id, fields in specs.items():
        rel_path, digest = _write_domain_artifact(base_dir, domain_id, fields)
        receipts[domain_id] = {
            **fields,
            "artifact_path": rel_path,
            "receipt_sha256": digest,
        }

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
        "receipts": receipts,
    }


def test_green_pilot_reconciles_nine_scores_and_archives_checksums(tmp_path):
    """Positive: Complete 9-domain manifest with authentic on-disk SHA-256 artifacts reaches target & verified score 93."""
    from tools.report.release_pilot import evaluate_pilot_manifest

    manifest = _make_green_manifest(tmp_path)
    report = evaluate_pilot_manifest(manifest, base_dir=str(tmp_path))

    assert report["passed"] is True
    assert report["audit_total"] == 67
    assert report["target_total"] == 93
    assert report["max_total"] == 100
    assert report["achieved_total"] == 93
    assert report["verified_total"] == 93
    assert report["pending_domains"] == []
    assert report["failed_domains"] == []
    assert len(report["domains"]) == 9
    assert report["qa_lead_signed"] is True
    assert len(report["archived_checksums"]["receipts"]) == 9
    assert len(report["archived_checksums"]["manifest_sha256"]) == 64


def test_negative_removed_substituted_corrupted_or_short_hash_blocks_acceptance(tmp_path):
    """Negative (TC-PILOT-01): Removed receipt, 1-byte file tamper, missing artifact, short fake hash, or build drift fail."""
    from tools.report.release_pilot import evaluate_pilot_manifest

    # 1. Removed required receipt keeps audit score in achieved_total, drops verified_total, and enters pending_domains
    removed = _make_green_manifest(tmp_path / "case_removed")
    del removed["receipts"]["workload_sla"]
    res_rem = evaluate_pilot_manifest(removed, base_dir=str(tmp_path / "case_removed"))
    assert res_rem["passed"] is False
    assert "workload_sla" in res_rem["pending_domains"]
    assert res_rem["domains"]["workload_sla"]["status"] == "pending"
    assert res_rem["domains"]["workload_sla"]["awarded_score"] == 6
    assert res_rem["achieved_total"] == 90
    assert res_rem["verified_total"] == 84

    # 2. Substituted candidate build & mismatched dataset digest fail
    sub_dir = tmp_path / "case_sub"
    substituted = _make_green_manifest(sub_dir)
    substituted["receipts"]["release_verdict"]["candidate_build"] = "wrong-build"
    substituted["receipts"]["model_orchestration_quality"]["dataset_digest"] = "stale-dataset"
    res_sub = evaluate_pilot_manifest(substituted, base_dir=str(sub_dir))
    assert res_sub["passed"] is False
    assert sorted(res_sub["failed_domains"]) == ["model_orchestration_quality", "release_verdict"]
    assert res_sub["domains"]["release_verdict"]["reason"] == "candidate_build_mismatch"
    assert res_sub["domains"]["model_orchestration_quality"]["reason"] == "versioned_input_mismatch"

    # 3. 1-byte corruption of physical on-disk artifact fails with artifact_checksum_mismatch
    tamper_dir = tmp_path / "case_tamper"
    tampered = _make_green_manifest(tamper_dir)
    target_artifact = tamper_dir / tampered["receipts"]["web_api_mobile"]["artifact_path"]
    raw_bytes = target_artifact.read_bytes()
    target_artifact.write_bytes(raw_bytes + b" ")
    res_tamper = evaluate_pilot_manifest(tampered, base_dir=str(tamper_dir))
    assert res_tamper["passed"] is False
    assert "web_api_mobile" in res_tamper["failed_domains"]
    assert res_tamper["domains"]["web_api_mobile"]["reason"] == "artifact_checksum_mismatch"

    # 4. Missing physical artifact on disk fails with missing_artifact_file
    missing_dir = tmp_path / "case_missing_file"
    missing_art = _make_green_manifest(missing_dir)
    (missing_dir / missing_art["receipts"]["worker_recovery"]["artifact_path"]).unlink()
    res_missing = evaluate_pilot_manifest(missing_art, base_dir=str(missing_dir))
    assert res_missing["passed"] is False
    assert res_missing["domains"]["worker_recovery"]["reason"] == "missing_artifact_file"

    # 5. Short fake checksum like "r1" is rejected with invalid_receipt_sha256
    short_dir = tmp_path / "case_short_hash"
    short_hash = _make_green_manifest(short_dir)
    short_hash["receipts"]["release_verdict"]["receipt_sha256"] = "r1"
    res_short = evaluate_pilot_manifest(short_hash, base_dir=str(short_dir))
    assert res_short["passed"] is False
    assert res_short["domains"]["release_verdict"]["reason"] == "invalid_receipt_sha256"

    # 6. Path traversal (../ escape or absolute path outside base_dir) is rejected even with matching SHA-256
    outside_file = tmp_path / "outside_secret.json"
    outside_bytes = b'{"outside": true}'
    outside_file.write_bytes(outside_bytes)
    outside_sha = hashlib.sha256(outside_bytes).hexdigest()

    trav_dir = tmp_path / "case_traversal"
    trav_rel = _make_green_manifest(trav_dir)
    trav_rel["receipts"]["release_verdict"]["artifact_path"] = "../outside_secret.json"
    trav_rel["receipts"]["release_verdict"]["receipt_sha256"] = outside_sha
    res_trav_rel = evaluate_pilot_manifest(trav_rel, base_dir=str(trav_dir))
    assert res_trav_rel["passed"] is False
    assert res_trav_rel["domains"]["release_verdict"]["reason"] == "invalid_artifact_path"

    trav_abs = _make_green_manifest(tmp_path / "case_abs_escape")
    trav_abs["receipts"]["release_verdict"]["artifact_path"] = str(outside_file)
    trav_abs["receipts"]["release_verdict"]["receipt_sha256"] = outside_sha
    res_trav_abs = evaluate_pilot_manifest(trav_abs, base_dir=str(tmp_path / "case_abs_escape"))
    assert res_trav_abs["passed"] is False
    assert res_trav_abs["domains"]["release_verdict"]["reason"] == "invalid_artifact_path"

    # 7. Missing artifact_path passes default verify_artifacts=False but fails verify_artifacts=True
    from tools.report.release_pilot import _evaluate_pilot_manifest

    opt_dir = tmp_path / "case_opt_art"
    opt_art = _make_green_manifest(opt_dir)
    opt_art["receipts"]["release_verdict"].pop("artifact_path")
    res_opt_default = evaluate_pilot_manifest(opt_art, base_dir=str(opt_dir))
    assert res_opt_default["passed"] is True
    res_opt_strict = _evaluate_pilot_manifest(opt_art, base_dir=str(opt_dir), verify_artifacts=True)
    assert res_opt_strict["passed"] is False
    assert res_opt_strict["domains"]["release_verdict"]["reason"] == "missing_artifact_file"

    # 7. Missing QA lead sign-off blocks final acceptance
    sig_dir = tmp_path / "case_nosig"
    no_signoff = _make_green_manifest(sig_dir)
    no_signoff["qa_lead_signoff"] = {}
    res_sig = evaluate_pilot_manifest(no_signoff, base_dir=str(sig_dir))
    assert res_sig["passed"] is False
    assert res_sig["qa_lead_signed"] is False


def test_boundary_pending_external_run_and_empty_manifest(tmp_path):
    """Boundary (TC-PILOT-01): Pending external accessibility retains audit score; empty {} reports verified_total == 0."""
    from tools.report.release_pilot import evaluate_pilot_manifest

    ext_dir = tmp_path / "case_pending"
    ext_pending = _make_green_manifest(ext_dir)
    ext_pending["receipts"]["accessibility"]["human_evidence_status"] = "pending"
    res = evaluate_pilot_manifest(ext_pending, base_dir=str(ext_dir))
    assert res["passed"] is False
    assert res["domains"]["accessibility"]["status"] == "pending"
    assert res["domains"]["accessibility"]["awarded_score"] == 5
    assert "accessibility" in res["pending_domains"]

    empty_res = evaluate_pilot_manifest({})
    assert empty_res["passed"] is False
    assert empty_res["audit_total"] == 67
    assert empty_res["achieved_total"] == 67
    assert empty_res["verified_total"] == 0
    assert len(empty_res["pending_domains"]) == 9


def test_cli_release_pilot_green_verify_artifacts_and_negative_rehearsal(tmp_path):
    """CLI (TC-PILOT-01): --verify-artifacts passes on authentic files (exit 0) and fails on tamper or missing artifact_path (exit 1)."""
    green_dir = tmp_path / "cli_green"
    green = _make_green_manifest(green_dir)
    green_file = green_dir / "manifest.json"
    green_file.write_text(json.dumps(green), encoding="utf-8")

    tamper_dir = tmp_path / "cli_tamper"
    tamper = _make_green_manifest(tamper_dir)
    tamper_file = tamper_dir / "manifest.json"
    tamper_file.write_text(json.dumps(tamper), encoding="utf-8")
    (tamper_dir / tamper["receipts"]["support_documentation"]["artifact_path"]).write_bytes(b"{corrupted}")

    no_art_dir = tmp_path / "cli_no_art"
    no_art = _make_green_manifest(no_art_dir)
    no_art["receipts"]["release_verdict"].pop("artifact_path")
    no_art_file = no_art_dir / "manifest.json"
    no_art_file.write_text(json.dumps(no_art), encoding="utf-8")

    empty_file = tmp_path / "empty_manifest.json"
    empty_file.write_text("{}", encoding="utf-8")

    repo_root = Path(__file__).resolve().parent.parent
    script = str(repo_root / "tools" / "report" / "release_pilot.py")

    r_ok = subprocess.run(
        [sys.executable, script, "--manifest", str(green_file), "--verify-artifacts", "--json"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert r_ok.returncode == 0, r_ok.stderr
    p_ok = json.loads(r_ok.stdout)
    assert p_ok["passed"] is True
    assert p_ok["achieved_total"] == 93
    assert p_ok["verified_total"] == 93

    r_tamper = subprocess.run(
        [sys.executable, script, "--manifest", str(tamper_file), "--verify-artifacts", "--json"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert r_tamper.returncode != 0
    p_tamper = json.loads(r_tamper.stdout)
    assert p_tamper["passed"] is False
    assert p_tamper["domains"]["support_documentation"]["reason"] == "artifact_checksum_mismatch"

    r_no_art = subprocess.run(
        [sys.executable, script, "--manifest", str(no_art_file), "--verify-artifacts", "--json"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert r_no_art.returncode != 0
    p_no_art = json.loads(r_no_art.stdout)
    assert p_no_art["domains"]["release_verdict"]["reason"] == "missing_artifact_file"

    # In-process CLI main() invocation exercises --verify-artifacts argparse flag directly
    from tools.report.release_pilot import main as pilot_main

    assert pilot_main(["--manifest", str(green_file), "--verify-artifacts", "--json"]) == 0
    assert pilot_main(["--manifest", str(no_art_file), "--verify-artifacts", "--json"]) == 1

    r_empty = subprocess.run(
        [sys.executable, script, "--manifest", str(empty_file), "--json"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert r_empty.returncode != 0
    p_empty = json.loads(r_empty.stdout)
    assert p_empty["verified_total"] == 0
    assert p_empty["audit_total"] == 67
