#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Release Pilot Scorecard & Evidence Manifest Aggregator
------------------------------------------------------
Reconciles all nine release-readiness domain receipts into one signed pilot
manifest, binding product evidence to candidate build/package digest and
evaluation/manual evidence to versioned inputs while keeping missing external
observations pending.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class PilotArtifactVerificationDTO:
    domain_id: str
    artifact_path: str
    declared_sha256: str
    computed_sha256: str
    verified_total: int
    audit_total: int

_PILOT_DOMAINS: Tuple[Tuple[str, str, int, int, int], ...] = (
    ("release_verdict", "product", 8, 15, 15),
    ("packaged_skills_ide", "product", 9, 14, 15),
    ("web_api_mobile", "product", 11, 14, 15),
    ("workload_sla", "product", 6, 9, 10),
    ("requirements_reporting", "versioned_manual", 12, 14, 15),
    ("model_orchestration_quality", "versioned_eval", 7, 9, 10),
    ("worker_recovery", "product", 6, 7, 8),
    ("accessibility", "product_human", 5, 6, 7),
    ("support_documentation", "product", 3, 5, 5),
)


def _sha256_canonical(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _verify_receipt_artifact(
    domain_id: str,
    audit_pts: int,
    target_pts: int,
    rec: Dict[str, Any],
    base_dir: Optional[str],
    verify_artifacts: bool,
) -> Optional[str]:
    """Validates 64-hex SHA-256 format, prevents path traversal outside base_dir, and checks on-disk bytes."""
    raw_sha = rec.get("receipt_sha256")
    if not isinstance(raw_sha, str) or not _SHA256_HEX_RE.match(raw_sha):
        return "invalid_receipt_sha256"

    art_path = str(rec.get("artifact_path") or "").strip()
    if not art_path:
        return "missing_artifact_file" if verify_artifacts else None

    if base_dir:
        if os.path.isabs(art_path):
            return "invalid_artifact_path"
        base_real = os.path.realpath(base_dir)
        resolved = os.path.realpath(os.path.join(base_real, art_path))
        if os.path.commonpath([base_real, resolved]) != base_real:
            return "invalid_artifact_path"
    else:
        resolved = art_path

    if not os.path.isfile(resolved):
        return "missing_artifact_file"

    computed = _sha256_file(resolved)
    verification = PilotArtifactVerificationDTO(
        domain_id=domain_id,
        artifact_path=art_path,
        declared_sha256=raw_sha,
        computed_sha256=computed,
        verified_total=target_pts,
        audit_total=audit_pts,
    )
    if verification.computed_sha256 != verification.declared_sha256:
        return "artifact_checksum_mismatch"
    return None


def _evaluate_domain_receipt(
    domain_id: str,
    binding_kind: str,
    audit_pts: int,
    target_pts: int,
    max_pts: int,
    rec: Any,
    manifest: Dict[str, Any],
    base_dir: Optional[str],
    verify_artifacts: bool,
) -> Dict[str, Any]:
    base = {"audit_score": audit_pts, "target_score": target_pts, "max_score": max_pts}
    if not isinstance(rec, dict) or not rec:
        return {**base, "status": "pending", "reason": "missing_receipt", "awarded_score": audit_pts}

    if binding_kind in ("product", "product_human"):
        same_build = rec.get("candidate_build") == manifest.get("candidate_build")
        same_pkg = rec.get("package_digest") == manifest.get("package_digest")
        if not (same_build and same_pkg and manifest.get("candidate_build")):
            return {**base, "status": "failed", "reason": "candidate_build_mismatch", "awarded_score": audit_pts}
        if binding_kind == "product_human" and rec.get("human_evidence_status") != "verified":
            return {**base, "status": "pending", "reason": "pending_human_evidence", "awarded_score": audit_pts}

    if binding_kind == "versioned_manual":
        same_req = rec.get("requirement_revision") == manifest.get("expected_requirement_revision")
        same_tpl = rec.get("template_digest") == manifest.get("expected_template_digest")
        if not (same_req and same_tpl and manifest.get("expected_requirement_revision")):
            return {**base, "status": "failed", "reason": "versioned_input_mismatch", "awarded_score": audit_pts}

    if binding_kind == "versioned_eval":
        same_ds = rec.get("dataset_digest") == manifest.get("expected_dataset_digest")
        same_rub = rec.get("rubric_revision") == manifest.get("expected_rubric_revision")
        if not (same_ds and same_rub and manifest.get("expected_dataset_digest")):
            return {**base, "status": "failed", "reason": "versioned_input_mismatch", "awarded_score": audit_pts}

    if rec.get("passed") is not True:
        return {**base, "status": "failed", "reason": "receipt_failed", "awarded_score": audit_pts}

    art_err = _verify_receipt_artifact(domain_id, audit_pts, target_pts, rec, base_dir, verify_artifacts)
    if art_err is not None:
        return {**base, "status": "failed", "reason": art_err, "awarded_score": audit_pts}

    return {**base, "status": "achieved", "reason": "verified", "awarded_score": target_pts}


def _evaluate_pilot_manifest(
    manifest: Dict[str, Any],
    base_dir: Optional[str],
    verify_artifacts: bool,
) -> Dict[str, Any]:
    """Reconciles 9 domain receipts, bindings, physical artifact digests, scores, QA sign-off, and archive checksums."""
    receipts = manifest.get("receipts") if isinstance(manifest.get("receipts"), dict) else {}
    domains_out: Dict[str, Dict[str, Any]] = {}
    pending_domains: List[str] = []
    failed_domains: List[str] = []
    receipt_checksums: Dict[str, str] = {}

    for domain_id, binding_kind, audit_pts, target_pts, max_pts in _PILOT_DOMAINS:
        rec = receipts.get(domain_id)
        if isinstance(rec, dict) and rec:
            receipt_checksums[domain_id] = _sha256_canonical(rec)
        entry = _evaluate_domain_receipt(
            domain_id,
            binding_kind,
            audit_pts,
            target_pts,
            max_pts,
            rec,
            manifest,
            base_dir=base_dir,
            verify_artifacts=verify_artifacts,
        )
        domains_out[domain_id] = entry
        if entry["status"] == "pending":
            pending_domains.append(domain_id)
        elif entry["status"] == "failed":
            failed_domains.append(domain_id)

    signoff = manifest.get("qa_lead_signoff")
    qa_lead_signed = bool(isinstance(signoff, dict) and str(signoff.get("signed_by") or "").strip())
    audit_total = sum(d["audit_score"] for d in domains_out.values())
    target_total = sum(d["target_score"] for d in domains_out.values())
    max_total = sum(d["max_score"] for d in domains_out.values())
    achieved_total = sum(d["awarded_score"] for d in domains_out.values())
    verified_total = sum(d["target_score"] for d in domains_out.values() if d["status"] == "achieved")
    passed = not pending_domains and not failed_domains and qa_lead_signed

    payload: Dict[str, Any] = {
        "candidate_build": str(manifest.get("candidate_build") or ""),
        "package_digest": str(manifest.get("package_digest") or ""),
        "passed": passed,
        "qa_lead_signed": qa_lead_signed,
        "audit_total": audit_total,
        "target_total": target_total,
        "max_total": max_total,
        "achieved_total": achieved_total,
        "verified_total": verified_total,
        "pending_domains": pending_domains,
        "failed_domains": failed_domains,
        "domains": domains_out,
        "archived_checksums": {
            "manifest_sha256": _sha256_canonical(manifest),
            "receipts": receipt_checksums,
        },
    }
    payload["receipt_sha256"] = _sha256_canonical(payload)
    return payload


def evaluate_pilot_manifest(
    manifest: Dict[str, Any],
    base_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Reconciles 9 domain receipts, bindings, physical artifact digests, scores, QA sign-off, and archive checksums."""
    return _evaluate_pilot_manifest(manifest, base_dir=base_dir, verify_artifacts=False)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entrypoint for scoring a release pilot manifest."""
    parser = argparse.ArgumentParser(description="Assemble and verify 9-domain release pilot evidence manifest.")
    parser.add_argument("--manifest", required=True, help="Path to pilot evidence manifest JSON.")
    parser.add_argument(
        "--verify-artifacts",
        action="store_true",
        help="Require physical on-disk artifact_path SHA-256 verification for every domain receipt.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON scorecard to stdout.")
    args = parser.parse_args(argv)

    manifest_dir = os.path.dirname(os.path.abspath(args.manifest))
    with open(args.manifest, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    report = _evaluate_pilot_manifest(
        manifest,
        base_dir=manifest_dir,
        verify_artifacts=bool(args.verify_artifacts),
    )
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(
            f"Pilot={report['candidate_build']} passed={report['passed']} "
            f"verified={report['verified_total']}/{report['max_total']} achieved={report['achieved_total']}/{report['max_total']}"
        )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
