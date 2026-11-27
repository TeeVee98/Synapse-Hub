#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/manual/manual_pipeline_adapter.py — Leaf Manual QA Pipeline Adapter
-------------------------------------------------------------------------
Composes existing deterministic Manual QA sensors (goldfish_review,
manual_tc_linter, checklist_query) with HMAC-signed forensic receipts and
Spec-Mutation auditing for `/super-plan`, `/solo`, and `/review --profile manual`.

Strict Leaf Invariant:
  NEVER imports solo_runner.py, plan_review_auditor.py, senior_code_review.py,
  or super_plan_engine.py so the dependency graph stays strictly acyclic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import glob
import hashlib
import hmac
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
import unicodedata

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.lint.manual_tc_linter import (
    _extract_canonical_field,
    lint_test_case_file,
    parse_markdown_tables,
)
from tools.manual.checklist_query import CANONICAL_FIELDS
from tools.orchestration.goldfish_review import evaluate_spec_content
from tools.orchestration.solo_contracts import (
    _get_receipt_hmac_key,
    _write_json_atomic,
    compute_mutation_receipt_hmac,
    get_receipt_hmac_key_readonly,
    resolve_red_receipt_path,
)

MAX_SPEC_BYTES = 512 * 1024
_REQ_ID_RE = re.compile(r"\b((?:AC|REQ|BR|FR|NFR|US|YC)[-_]\d+[A-Za-z0-9_-]*)\b", re.IGNORECASE)
_MANUAL_PROFILE_HEADER_RE = re.compile(
    r"(?:\*\*\s*Profile\s*:\s*\*\*|^\s*(?:>\s*)?Profile\s*:)\s*`?manual`?",
    re.IGNORECASE | re.MULTILINE,
)

# Bilingual English + ASCII-folded Vietnamese multi-word fault/oracle tokens (strictly ASCII source)
_NEG_BOUNDARY_TOKENS = (
    "negative", "boundary", "empty", "null", "invalid", "malformed", "reject",
    "400", "422", "min", "max", "length", "shorter", "exceed", "unicode", "ime", "sqli",
    "khong hop le", "sai dinh dang", "bo trong", "de trong", "vuot qua",
    "do dai", "toi thieu", "toi da", "tu choi", "bao loi", "nho hon", "lon hon",
    "bien duoi", "bien tren", "ky tu dac biet", "ngan hon",
)
_RBAC_TOKENS = (
    "403", "forbidden", "rbac", "idor", "unauthorized", "permission", "role", "denied",
    "khong co quyen", "cam truy cap", "trai phep", "phan quyen",
    "quyen truy cap", "tai khoan khac", "nguoi dung khac",
)
_LOCKOUT_TOKENS = (
    "429", "lockout", "locked", "expired", "attempt", "rate", "too many",
    "khoa tai khoan", "tam khoa", "bi khoa", "het han", "qua so lan",
    "nhap sai qua", "nhap sai lien tiep", "sai lien tiep", "gioi han tan suat", "qua nhieu lan",
)
_RACE_TOKENS = (
    "race", "double-submit", "double submit", "idempoten", "409", "duplicate", "concurrent",
    "nhan dup", "bam dup", "click dup", "gui trung", "dong thoi",
    "trung lap", "hai lan lien tiep", "khong tao trung",
)
_VAGUE_ORACLE_TOKENS = (
    "works properly", "as expected", "nhu mong doi",
    "hoat dong binh thuong", "chay binh thuong",
)
_BOUNDARY_TRIGGERS = (
    "reject", "invalid", "malformed", "shorter", "min", "max", "400", "length", "empty",
    "khong hop le", "sai dinh dang", "bo trong", "de trong", "vuot qua",
    "do dai", "toi thieu", "toi da", "tu choi", "ngan hon",
)
_RBAC_TRIGGERS = (
    "rbac", "idor", "403", "forbidden", "denied", "role", "permission",
    "khong co quyen", "cam truy cap", "trai phep", "phan quyen",
    "nguoi dung khac", "tai khoan khac",
)
_LOCKOUT_TRIGGERS = (
    "otp", "expired", "lock", "429", "attempt", "rate",
    "khoa tai khoan", "tam khoa", "het han", "qua so lan",
    "nhap sai qua", "nhap sai lien tiep", "ma xac thuc",
)
_RACE_TRIGGERS = (
    "double-submit", "double submit", "idempoten", "race", "concurrent",
    "nhan dup", "bam dup", "dong thoi", "trung lap", "gui trung",
)
_VI_FIELD_ALIASES: Dict[str, Tuple[str, ...]] = {
    "email": ("thu dien tu", "dia chi email"),
    "phone": ("so dien thoai", "dien thoai", "di dong"),
    "password": ("mat khau",),
    "number": ("so luong", "so tien", "don gia", "gia tien", "han muc"),
    "date": ("ngay sinh", "ngay giao dich", "thoi gian"),
    "date-range": ("khoang ngay", "tu ngay den ngay"),
    "file-upload": ("tai tep", "tai len", "tep dinh kem", "dinh kem"),
    "otp": ("ma otp", "ma xac thuc", "ma pin"),
    "geo": ("dia chi", "toa do"),
    "signature": ("chu ky",),
    "biometric": ("van tay", "khuon mat", "sinh trac hoc"),
    "camera-qr": ("ma qr", "quet ma"),
    "currency": ("ngoai te", "ty gia", "tien te"),
    "card-iban": ("so the", "the tin dung", "the thanh toan", "so tai khoan"),
}


@dataclass(frozen=True)
class ManualSpecInventoryDTO:
    """Extracted BRD/Story requirement inventory and 25-field surface for Manual QA planning."""

    spec_path: str
    spec_hash: str
    requirement_ids: Tuple[str, ...]
    detected_fields: Tuple[str, ...]
    goldfish_score: float
    goldfish_passed: bool
    findings: Tuple[str, ...]


@dataclass(frozen=True)
class ManualRedReceiptDTO:
    """HMAC-signed Red Phase receipt locking BRD spec hash and mandatory AC/REQ IDs."""

    milestone_id: str
    profile: str
    status: str
    spec_path: str
    spec_hash: str
    requirement_ids: Tuple[str, ...]
    certified_at: str
    ttl_seconds: int
    receipt_hmac: str


@dataclass(frozen=True)
class ManualCoverageAuditDTO:
    """Deterministic Green Phase verification result across manual_tc_linter, RTM, and field rules."""

    test_case_files: Tuple[str, ...]
    total_test_cases: int
    covered_req_ids: Tuple[str, ...]
    uncovered_req_ids: Tuple[str, ...]
    orphan_tc_ids: Tuple[str, ...]
    linter_passed: bool
    linter_defects: Tuple[str, ...]
    field_checklist_gaps: Tuple[str, ...]
    passed: bool


@dataclass(frozen=True)
class SpecMutationResultDTO:
    """Adversarial Purple Phase Spec-Mutation scorecard measuring fault-catching TC coverage."""

    spec_path: str
    total_mutants: int
    killed_mutants: int
    kill_score: float
    threshold: float
    passed: bool
    survived_mutants: Tuple[str, ...]
    receipt_hmac: str


@dataclass(frozen=True)
class ManualReviewReportDTO:
    """Zero-trust manual audit payload consumed by plan_review_auditor and senior_code_review."""

    profile: str
    spec_inventory: ManualSpecInventoryDTO
    coverage_audit: ManualCoverageAuditDTO
    spec_mutation: Optional[SpecMutationResultDTO]
    receipt_verified: bool
    findings: Tuple[Dict[str, str], ...]
    passed: bool


def detect_plan_profile(plan_content: str, explicit_profile: str = "auto") -> str:
    """Resolves effective pipeline profile ('code' or 'manual') with strict backward-compatible default."""
    norm = str(explicit_profile or "auto").strip().lower()
    if norm in ("code", "manual"):
        return norm
    if plan_content and _MANUAL_PROFILE_HEADER_RE.search(plan_content):
        return "manual"
    return "code"


def _resolve_path(path_str: str, repo_root: str = "") -> str:
    if not path_str:
        return ""
    if os.path.isabs(path_str):
        return os.path.abspath(path_str)
    base = repo_root or _REPO_ROOT
    return os.path.abspath(os.path.join(base, path_str))


def _norm_rel(path_str: str, repo_root: str = "") -> str:
    if not path_str:
        return ""
    base = os.path.abspath(repo_root or _REPO_ROOT)
    abs_p = _resolve_path(path_str, base)
    try:
        rel = os.path.relpath(abs_p, base)
    except ValueError:
        return path_str.replace("\\", "/")
    if not rel.startswith(".."):
        return rel.replace("\\", "/")
    return path_str.replace("\\", "/")


def _read_bounded_text(abs_path: str) -> Optional[str]:
    if not abs_path or not os.path.isfile(abs_path):
        return None
    try:
        with open(abs_path, "rb") as fh:
            raw = fh.read(MAX_SPEC_BYTES)
        return raw.decode("utf-8", errors="replace")
    except OSError:
        return None


def _extract_requirement_ids(text: str) -> Tuple[str, ...]:
    seen: List[str] = []
    seen_set: Set[str] = set()
    for match in _REQ_ID_RE.finditer(text or ""):
        norm_id = match.group(1).upper().replace("_", "-")
        if norm_id not in seen_set:
            seen_set.add(norm_id)
            seen.append(norm_id)
    return tuple(seen)


def _fold_vi_ascii(text: str) -> str:
    """Folds accented Vietnamese text to lowercase ASCII for diacritic-tolerant matching."""
    if not text:
        return ""
    replaced = text.replace("\u0111", "d").replace("\u0110", "d")
    decomposed = unicodedata.normalize("NFKD", replaced)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()


def _field_aliases(field_key: str) -> Tuple[str, ...]:
    """Returns combined English and ASCII-folded Vietnamese aliases for a canonical field key."""
    en_aliases = tuple(CANONICAL_FIELDS.get(field_key, {}).get("aliases") or ())
    vi_aliases = _VI_FIELD_ALIASES.get(field_key, ())
    return (field_key, *en_aliases, *vi_aliases)


def _detect_canonical_fields(text: str) -> Tuple[str, ...]:
    folded = _fold_vi_ascii(text or "")
    found: List[str] = []
    for key in CANONICAL_FIELDS:
        for alias in _field_aliases(key):
            if len(alias) < 3:
                continue
            if re.search(rf"\b{re.escape(alias.lower())}\b", folded):
                found.append(key)
                break
    return tuple(found)


def compute_manual_red_hmac(
    payload: Dict[str, Any],
    key: Optional[bytes] = None,
    repo_root: Optional[str] = None,
) -> str:
    """Computes canonical HMAC-SHA256 over security-critical Manual Red receipt fields."""
    secret = key if key is not None else _get_receipt_hmac_key(repo_root)
    canonical = {
        "milestone_id": payload.get("milestone_id"),
        "profile": payload.get("profile", "manual"),
        "status": payload.get("status"),
        "spec_path": payload.get("spec_path"),
        "spec_hash": payload.get("spec_hash"),
        "requirement_ids": list(payload.get("requirement_ids") or []),
        "certified_at": payload.get("certified_at"),
        "ttl_seconds": int(payload.get("ttl_seconds", 900) or 900),
    }
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(secret, raw, hashlib.sha256).hexdigest()


def verify_manual_red_hmac(
    payload: Dict[str, Any],
    key: Optional[bytes] = None,
    repo_root: Optional[str] = None,
) -> bool:
    """Verifies Manual Red receipt HMAC in constant time without creating key files on disk."""
    actual = payload.get("receipt_hmac")
    if not isinstance(actual, str) or len(actual) != 64:
        return False
    secret = key if key is not None else get_receipt_hmac_key_readonly(repo_root)
    if secret is None:
        return False
    expected = compute_manual_red_hmac(payload, key=secret, repo_root=repo_root)
    return hmac.compare_digest(expected, actual)


def extract_manual_spec_inventory(
    spec_path: str,
    repo_root: str = "",
) -> ManualSpecInventoryDTO:
    """Extracts requirement IDs, 25-field surface, SHA-256 hash, and Goldfish BRD score."""
    effective_root = repo_root or _REPO_ROOT
    abs_spec = _resolve_path(spec_path, effective_root)
    norm_spec = _norm_rel(spec_path, effective_root)
    content = _read_bounded_text(abs_spec)
    if content is None:
        return ManualSpecInventoryDTO(
            spec_path=norm_spec,
            spec_hash="",
            requirement_ids=(),
            detected_fields=(),
            goldfish_score=0.0,
            goldfish_passed=False,
            findings=(f"Specification file not found or unreadable: {norm_spec}",),
        )

    spec_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    gf = evaluate_spec_content(content, filename=os.path.basename(abs_spec), mode="brd")
    req_ids = _extract_requirement_ids(content)
    fields = _detect_canonical_fields(content)
    findings = [str(item.get("message", "")) for item in (gf.get("findings") or []) if item.get("message")]
    if not content.strip():
        findings.append("Specification content is empty.")
    elif not req_ids:
        findings.append("No structured requirement IDs (AC-xx, REQ-xx, BR-xx) found in specification.")

    return ManualSpecInventoryDTO(
        spec_path=norm_spec,
        spec_hash=spec_hash,
        requirement_ids=req_ids,
        detected_fields=fields,
        goldfish_score=float(gf.get("score", 0.0) or 0.0),
        goldfish_passed=bool(gf.get("passed", False)) and bool(content.strip()),
        findings=tuple(findings),
    )


def certify_manual_red_phase(
    spec_path: str,
    milestone_id: str,
    repo_root: str = "",
    ttl_seconds: int = 900,
    receipt_path: Optional[str] = None,
    plan_slug: Optional[str] = None,
) -> ManualRedReceiptDTO:
    """Locks BRD spec_hash and requirement_ids into an HMAC-signed Red Phase receipt."""
    effective_root = repo_root or _REPO_ROOT
    inv = extract_manual_spec_inventory(spec_path, repo_root=effective_root)
    certified_at = datetime.now(timezone.utc).isoformat()
    status = "CERTIFIED_RED" if (inv.spec_hash and inv.requirement_ids) else "REJECTED_INVALID_SPEC"

    payload: Dict[str, Any] = {
        "milestone_id": milestone_id,
        "profile": "manual",
        "status": status,
        "spec_path": inv.spec_path,
        "spec_hash": inv.spec_hash,
        "requirement_ids": list(inv.requirement_ids),
        "detected_fields": list(inv.detected_fields),
        "goldfish_score": inv.goldfish_score,
        "certified_at": certified_at,
        "ttl_seconds": int(ttl_seconds),
    }
    sig = compute_manual_red_hmac(payload, repo_root=effective_root)
    payload["receipt_hmac"] = sig

    target_path = resolve_red_receipt_path(
        effective_root,
        milestone_id=milestone_id,
        explicit_path=receipt_path,
        plan_slug=plan_slug,
    )
    _write_json_atomic(target_path, payload)

    return ManualRedReceiptDTO(
        milestone_id=milestone_id,
        profile="manual",
        status=status,
        spec_path=inv.spec_path,
        spec_hash=inv.spec_hash,
        requirement_ids=inv.requirement_ids,
        certified_at=certified_at,
        ttl_seconds=int(ttl_seconds),
        receipt_hmac=sig,
    )


def _extract_tc_rows(abs_files: Sequence[str]) -> List[Dict[str, str]]:
    parsed_rows: List[Dict[str, str]] = []
    for abs_f in abs_files:
        text = _read_bounded_text(abs_f)
        if not text:
            continue
        for table in parse_markdown_tables(text):
            for row in table.get("rows") or []:
                tc_id = _extract_canonical_field(row, "case_id")
                if not tc_id:
                    continue
                req_raw = _extract_canonical_field(row, "req_id")
                tags = _extract_canonical_field(row, "tags")
                title = _extract_canonical_field(row, "title")
                steps = _extract_canonical_field(row, "steps")
                expected = _extract_canonical_field(row, "expected")
                data = _extract_canonical_field(row, "data")
                parsed_rows.append(
                    {
                        "tc_id": tc_id,
                        "req_raw": req_raw,
                        "tags": tags,
                        "blob": _fold_vi_ascii(f"{title} {steps} {expected} {data} {tags}"),
                    }
                )
    return parsed_rows


def _row_req_ids(row: Dict[str, str]) -> Tuple[str, ...]:
    combined = f"{row.get('req_raw', '')} {row.get('tags', '')}"
    return _extract_requirement_ids(combined)


def verify_manual_green_phase(
    spec_path: str,
    tc_files: Tuple[str, ...],
    milestone_id: str,
    repo_root: str = "",
    linter_profile: Optional[str] = None,
    strict_semantic: bool = False,
) -> ManualCoverageAuditDTO:
    """Verifies manual test suite against manual_tc_linter, 100% AC RTM linkage, and field checklist."""
    effective_root = repo_root or _REPO_ROOT
    inv = extract_manual_spec_inventory(spec_path, repo_root=effective_root)
    abs_tc_files = [_resolve_path(f, effective_root) for f in tc_files if str(f).strip()]
    norm_tc_files = tuple(_norm_rel(f, effective_root) for f in tc_files if str(f).strip())

    defects: List[str] = []
    linter_all_passed = bool(abs_tc_files)
    for abs_f in abs_tc_files:
        if not os.path.isfile(abs_f):
            linter_all_passed = False
            defects.append(f"Test case file missing: {_norm_rel(abs_f, effective_root)}")
            continue
        res = lint_test_case_file(abs_f, profile=linter_profile, strict_semantic=strict_semantic)
        if not res.get("has_test_cases", False):
            linter_all_passed = False
            defects.append(f"No markdown test case table found in {_norm_rel(abs_f, effective_root)}")
            continue
        if not res.get("passed", False):
            linter_all_passed = False
            for d in res.get("defects") or []:
                tc_tag = f"[{d['tc_id']}] " if d.get("tc_id") else ""
                defects.append(f"L{d.get('line', 1)}: {tc_tag}{d.get('message', '')}")

    rows = _extract_tc_rows(abs_tc_files)
    spec_req_set = set(inv.requirement_ids)
    covered_set: Set[str] = set()
    orphan_tcs: List[str] = []

    for row in rows:
        linked = _row_req_ids(row)
        if not linked:
            if spec_req_set:
                orphan_tcs.append(row["tc_id"])
            continue
        matched_known = [rid for rid in linked if rid in spec_req_set]
        if matched_known:
            covered_set.update(matched_known)
        elif spec_req_set:
            orphan_tcs.append(row["tc_id"])

    covered_ordered = tuple(rid for rid in inv.requirement_ids if rid in covered_set)
    uncovered_ordered = tuple(rid for rid in inv.requirement_ids if rid not in covered_set)

    all_tc_blob = "\n".join(r["blob"] for r in rows)
    field_gaps: List[str] = []
    for field_key in inv.detected_fields:
        aliases = _field_aliases(field_key)
        has_field_neg = any(
            any(a.lower() in r["blob"] for a in aliases if len(a) >= 3)
            and any(tok in r["blob"] for tok in (*_NEG_BOUNDARY_TOKENS, *_LOCKOUT_TOKENS, *_RBAC_TOKENS))
            for r in rows
        )
        if not has_field_neg and all_tc_blob:
            field_gaps.append(field_key)

    passed = (
        bool(inv.requirement_ids)
        and len(rows) > 0
        and linter_all_passed
        and len(uncovered_ordered) == 0
        and len(orphan_tcs) == 0
    )
    return ManualCoverageAuditDTO(
        test_case_files=norm_tc_files,
        total_test_cases=len(rows),
        covered_req_ids=covered_ordered,
        uncovered_req_ids=uncovered_ordered,
        orphan_tc_ids=tuple(orphan_tcs),
        linter_passed=linter_all_passed,
        linter_defects=tuple(defects),
        field_checklist_gaps=tuple(field_gaps),
        passed=passed,
    )


def _extract_req_lines(spec_text: str) -> Dict[str, str]:
    req_lines: Dict[str, str] = {}
    for line in (spec_text or "").splitlines():
        ids = _extract_requirement_ids(line)
        for rid in ids:
            prev = req_lines.get(rid, "")
            req_lines[rid] = f"{prev} {line}".strip()
    return req_lines


def _build_spec_mutants(
    inv: ManualSpecInventoryDTO,
    spec_text: str,
) -> List[Tuple[str, str, Tuple[str, ...]]]:
    """Generates deterministic fault-injection mutants (mutant_id, req_id, kill_tokens)."""
    mutants: List[Tuple[str, str, Tuple[str, ...]]] = []
    req_lines = _extract_req_lines(spec_text)

    for rid in inv.requirement_ids:
        line_low = _fold_vi_ascii(req_lines.get(rid, ""))
        mutants.append((f"M_REQ_OMIT::{rid}", rid, ()))
        if any(tok in line_low for tok in _BOUNDARY_TRIGGERS):
            mutants.append((f"M_BOUNDARY_INVERT::{rid}", rid, _NEG_BOUNDARY_TOKENS))
        if any(tok in line_low for tok in _RBAC_TRIGGERS):
            mutants.append((f"M_RBAC_BYPASS::{rid}", rid, _RBAC_TOKENS))
        if any(tok in line_low for tok in _LOCKOUT_TRIGGERS):
            mutants.append((f"M_LOCKOUT_BYPASS::{rid}", rid, _LOCKOUT_TOKENS))
        if any(tok in line_low for tok in _RACE_TRIGGERS):
            mutants.append((f"M_RACE_DOUBLE_SUBMIT::{rid}", rid, _RACE_TOKENS))

    for field_key in inv.detected_fields:
        mutants.append((f"M_FIELD_FAULT::{field_key}", "", (field_key,)))
    return mutants


def _execute_spec_mutation_audit(
    spec_path: str,
    tc_files: Tuple[str, ...],
    threshold: float = 80.0,
    repo_root: str = "",
    milestone_id: Optional[str] = None,
    write_receipt: bool = True,
) -> SpecMutationResultDTO:
    """Internal Spec-Mutation executor supporting read-only auditing during /review."""
    effective_root = repo_root or _REPO_ROOT
    inv = extract_manual_spec_inventory(spec_path, repo_root=effective_root)
    abs_spec = _resolve_path(spec_path, effective_root)
    spec_text = _read_bounded_text(abs_spec) or ""
    abs_tc_files = [_resolve_path(f, effective_root) for f in tc_files if str(f).strip()]
    rows = _extract_tc_rows(abs_tc_files)

    mutants = _build_spec_mutants(inv, spec_text)
    total = len(mutants)
    killed = 0
    survived: List[str] = []

    for mutant_id, req_id, required_tokens in mutants:
        if req_id:
            matching_rows = [r for r in rows if req_id in _row_req_ids(r)]
            if not required_tokens:
                is_killed = any(
                    len(r["blob"].strip()) >= 15 and not any(v in r["blob"] for v in _VAGUE_ORACLE_TOKENS)
                    for r in matching_rows
                )
            else:
                is_killed = any(any(tok in r["blob"] for tok in required_tokens) for r in matching_rows)
        else:
            field_key = required_tokens[0]
            aliases = _field_aliases(field_key)
            is_killed = any(
                any(a.lower() in r["blob"] for a in aliases if len(a) >= 3)
                and any(tok in r["blob"] for tok in (*_NEG_BOUNDARY_TOKENS, *_LOCKOUT_TOKENS, *_RBAC_TOKENS))
                for r in rows
            )

        if is_killed:
            killed += 1
        else:
            survived.append(mutant_id)

    kill_score = round((killed / total) * 100.0, 2) if total > 0 else 0.0
    passed = total > 0 and kill_score >= float(threshold)

    receipt_payload: Dict[str, Any] = {
        "status": "SPEC_MUTATION_PASSED" if passed else "SPEC_MUTATION_FAILED",
        "profile": "manual",
        "passed": passed,
        "mutation_score": kill_score,
        "required_threshold": float(threshold),
        "total_generated": total,
        "killed": killed,
        "survived": len(survived),
        "survived_mutants": survived,
        "targets_evaluated": [inv.spec_path] if inv.spec_path else [],
    }
    if milestone_id:
        receipt_payload["milestone_id"] = milestone_id

    sig = ""
    if write_receipt:
        sig = compute_mutation_receipt_hmac(receipt_payload, repo_root=effective_root)
        receipt_payload["receipt_hmac"] = sig
        if milestone_id:
            safe_ms = re.sub(r"[^A-Za-z0-9_\-]", "_", str(milestone_id).strip())
            out_path = os.path.join(effective_root, "reports", "solo_receipts", f"{safe_ms}_mutation.json")
        else:
            out_path = os.path.join(effective_root, "reports", "tdd_mutation_receipt.json")
        _write_json_atomic(out_path, receipt_payload)
    else:
        ro_key = get_receipt_hmac_key_readonly(effective_root)
        if ro_key is not None:
            sig = compute_mutation_receipt_hmac(receipt_payload, key=ro_key, repo_root=effective_root)

    return SpecMutationResultDTO(
        spec_path=inv.spec_path,
        total_mutants=total,
        killed_mutants=killed,
        kill_score=kill_score,
        threshold=float(threshold),
        passed=passed,
        survived_mutants=tuple(survived),
        receipt_hmac=sig,
    )


def run_spec_mutation_audit(
    spec_path: str,
    tc_files: Tuple[str, ...],
    threshold: float = 80.0,
    repo_root: str = "",
    milestone_id: Optional[str] = None,
) -> SpecMutationResultDTO:
    """Runs deterministic fault-injection Spec-Mutation against manual test suites."""
    return _execute_spec_mutation_audit(
        spec_path=spec_path,
        tc_files=tc_files,
        threshold=threshold,
        repo_root=repo_root,
        milestone_id=milestone_id,
        write_receipt=True,
    )


def _make_manual_finding(
    severity: str,
    code: str,
    title: str,
    file_path: str,
    what_is: str,
    problem: str,
    fix: str,
    if_skipped: str,
) -> Dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "title": title,
        "file_path": file_path,
        "line_no": "1",
        "what_is": what_is,
        "problem": problem,
        "fix": fix,
        "if_skipped": if_skipped,
    }


def list_manual_red_receipts(repo_root: str, milestone_id: Optional[str] = None) -> Tuple[str, ...]:
    """Returns normalized relative paths of discovered Manual Red receipts under repo_root."""
    abs_root = os.path.abspath(repo_root or _REPO_ROOT)
    return tuple(_norm_rel(p, abs_root) for p in _find_manual_red_receipts(abs_root, milestone_id))


def _is_manual_red_expired(payload: Dict[str, Any]) -> bool:
    """Returns True when a signed Manual Red receipt has exceeded its certified TTL."""
    raw_ts = str(payload.get("certified_at") or "").strip()
    ttl_raw = payload.get("ttl_seconds")
    if not raw_ts or ttl_raw is None:
        return False
    try:
        ttl_sec = int(ttl_raw)
        cert_dt = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    if cert_dt.tzinfo is None:
        cert_dt = cert_dt.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - cert_dt).total_seconds()
    return elapsed > max(1, ttl_sec)


def _find_manual_red_receipts(repo_root: str, milestone_id: Optional[str]) -> List[str]:
    solo_dir = os.path.join(repo_root, "reports", "solo_receipts")
    candidates: List[str] = []
    if os.path.isdir(solo_dir):
        if milestone_id:
            safe_ms = re.sub(r"[^A-Za-z0-9_\-]", "_", milestone_id.strip())
            candidates.extend(sorted(glob.glob(os.path.join(solo_dir, f"*__{safe_ms}_red.json"))))
            direct = os.path.join(solo_dir, f"{safe_ms}_red.json")
            if os.path.isfile(direct):
                candidates.append(direct)
        else:
            candidates.extend(sorted(glob.glob(os.path.join(solo_dir, "*_red.json"))))
    legacy = os.path.join(repo_root, "reports", "tdd_red_receipt.json")
    if not milestone_id and os.path.isfile(legacy):
        candidates.append(legacy)
    return list(dict.fromkeys(candidates))


def _resolve_manual_artifacts(
    repo_root: str,
    plan_path: Optional[str],
    changed_files: Tuple[str, ...],
    explicit_spec: Optional[str],
    milestone_id: Optional[str] = None,
) -> Tuple[str, Tuple[str, ...]]:
    spec_candidate = explicit_spec or ""
    tc_candidates: List[str] = []
    norm_plan = _norm_rel(plan_path, repo_root) if plan_path else ""

    if plan_path and not spec_candidate:
        plan_text = _read_bounded_text(_resolve_path(plan_path, repo_root)) or ""
        m_spec = re.search(r"Spec\s+Source[^\n:]*:[\s*`]*([A-Za-z0-9_.\-/\\]+\.(?:md|feature))", plan_text, re.IGNORECASE)
        if m_spec:
            spec_candidate = m_spec.group(1)

    for cf in changed_files:
        norm = _norm_rel(cf, repo_root)
        if not norm.lower().endswith(".md"):
            continue
        base_name = os.path.basename(norm).lower()
        if (
            norm == norm_plan
            or norm.startswith(".synapse/")
            or norm.startswith("reports/")
            or base_name.endswith("implementation_plan.md")
        ):
            continue
        abs_cf = _resolve_path(norm, repo_root)
        text = _read_bounded_text(abs_cf) or ""
        tables = parse_markdown_tables(text)
        has_tc = any(
            _extract_canonical_field(r, "case_id")
            for t in tables
            if t.get("is_test_table")
            for r in (t.get("rows") or [])
        )
        if has_tc:
            tc_candidates.append(norm)
        elif not spec_candidate and _extract_requirement_ids(text):
            spec_candidate = norm

    if not spec_candidate:
        for rf in _find_manual_red_receipts(repo_root, milestone_id):
            try:
                with open(rf, "r", encoding="utf-8") as fh:
                    rec_payload = json.load(fh)
                rec_spec = str(rec_payload.get("spec_path") or "").strip()
                if rec_spec:
                    spec_candidate = rec_spec
                    break
            except (OSError, json.JSONDecodeError):
                continue

    return spec_candidate, tuple(dict.fromkeys(tc_candidates))


def audit_manual_delivery(
    repo_root: str,
    plan_path: Optional[str],
    changed_files: Tuple[str, ...],
    milestone_id: Optional[str] = None,
    strict_solo: bool = False,
    spec_path: Optional[str] = None,
) -> ManualReviewReportDTO:
    """Zero-trust read-only Manual QA audit reconciling spec, test cases, HMAC receipts, and Spec-Mutation."""
    abs_root = os.path.abspath(repo_root or _REPO_ROOT)
    findings: List[Dict[str, str]] = []
    resolved_spec, resolved_tcs = _resolve_manual_artifacts(
        abs_root, plan_path, changed_files, spec_path, milestone_id=milestone_id
    )

    inv = extract_manual_spec_inventory(resolved_spec, repo_root=abs_root)
    coverage = verify_manual_green_phase(
        spec_path=resolved_spec,
        tc_files=resolved_tcs,
        milestone_id=milestone_id or "M1",
        repo_root=abs_root,
    )
    spec_mut = _execute_spec_mutation_audit(
        spec_path=resolved_spec,
        tc_files=resolved_tcs,
        threshold=80.0,
        repo_root=abs_root,
        milestone_id=milestone_id,
        write_receipt=False,
    )

    ro_key = get_receipt_hmac_key_readonly(abs_root)
    red_files = _find_manual_red_receipts(abs_root, milestone_id)
    receipt_verified = False

    if not red_files:
        if strict_solo:
            findings.append(
                _make_manual_finding(
                    severity="Must fix",
                    code="MISSING_MANUAL_RED_RECEIPT",
                    title="Missing Manual Red Phase receipt under --strict-solo",
                    file_path="reports/solo_receipts/",
                    what_is="No signed Manual Red receipt was found for this delivery.",
                    problem="Without a Red Spec-Hash receipt, requirement scope could be silently dropped.",
                    fix="Run agent-qa solo --profile manual --red --spec <spec.md> --milestone <ID>.",
                    if_skipped="Unverified requirement coverage bypasses zero-trust QA governance.",
                )
            )
    else:
        verified_any = False
        for rf in red_files:
            rel_rf = _norm_rel(rf, abs_root)
            try:
                with open(rf, "r", encoding="utf-8") as fh:
                    payload = json.load(fh)
            except (OSError, json.JSONDecodeError):
                findings.append(
                    _make_manual_finding(
                        severity="Must fix",
                        code="TAMPERED_MANUAL_RED_RECEIPT",
                        title=f"Unreadable Manual Red receipt: {rel_rf}",
                        file_path=rel_rf,
                        what_is="Manual Red receipt JSON could not be parsed.",
                        problem="Corrupted receipt invalidates cryptographic provenance.",
                        fix="Re-run agent-qa solo --profile manual --red.",
                        if_skipped="Audit integrity is compromised.",
                    )
                )
                continue
            if not verify_manual_red_hmac(payload, key=ro_key, repo_root=abs_root):
                findings.append(
                    _make_manual_finding(
                        severity="Must fix",
                        code="TAMPERED_MANUAL_RED_RECEIPT",
                        title=f"Invalid Manual Red receipt HMAC: {rel_rf}",
                        file_path=rel_rf,
                        what_is=f"Constant-time HMAC verification failed on '{rel_rf}'.",
                        problem="Receipt was modified or signed with an unknown key.",
                        fix="Re-certify via agent-qa solo --profile manual --red.",
                        if_skipped="Forged Red provenance masks dropped requirements.",
                    )
                )
                continue
            if _is_manual_red_expired(payload):
                findings.append(
                    _make_manual_finding(
                        severity="Must fix",
                        code="EXPIRED_MANUAL_RED_RECEIPT",
                        title=f"Expired Manual Red receipt TTL: {rel_rf}",
                        file_path=rel_rf,
                        what_is=f"Receipt '{rel_rf}' exceeded its signed ttl_seconds window.",
                        problem="Stale Red receipts cannot certify current specification freshness.",
                        fix="Re-run agent-qa solo --profile manual --red to issue a fresh receipt.",
                        if_skipped="Outdated Red locks bypass specification freshness guarantees.",
                    )
                )
                continue
            expected_hash = str(payload.get("spec_hash") or "")
            if expected_hash and inv.spec_hash and not hmac.compare_digest(expected_hash, inv.spec_hash):
                findings.append(
                    _make_manual_finding(
                        severity="Must fix",
                        code="SPEC_DRIFT_AFTER_RED",
                        title=f"Specification modified after Red certification: {inv.spec_path}",
                        file_path=inv.spec_path or rel_rf,
                        what_is="Live spec SHA-256 hash differs from signed Red receipt.",
                        problem="Spec changed after Red lock without recertification.",
                        fix="Re-run agent-qa solo --profile manual --red to lock the updated spec.",
                        if_skipped="Test suite may verify an outdated specification.",
                    )
                )
                continue
            verified_any = True
        receipt_verified = verified_any and not any(
            f["code"] in ("TAMPERED_MANUAL_RED_RECEIPT", "EXPIRED_MANUAL_RED_RECEIPT", "SPEC_DRIFT_AFTER_RED")
            for f in findings
        )

    if coverage.uncovered_req_ids:
        findings.append(
            _make_manual_finding(
                severity="Must fix",
                code="UNCOVERED_REQUIREMENTS",
                title=f"Uncovered BRD requirements: {', '.join(coverage.uncovered_req_ids)}",
                file_path=resolved_tcs[0] if resolved_tcs else (inv.spec_path or "docs/"),
                what_is="One or more specification requirement IDs have zero linked test cases.",
                problem="Planned acceptance criteria ship without manual test coverage.",
                fix="Add ISO 29119-3 test cases linked to every uncovered REQ/AC ID.",
                if_skipped="Business requirements remain untested prior to release.",
            )
        )

    if coverage.orphan_tc_ids:
        findings.append(
            _make_manual_finding(
                severity="Should fix",
                code="ORPHAN_TEST_CASES",
                title=f"Orphan test cases unmapped to spec requirements: {', '.join(coverage.orphan_tc_ids)}",
                file_path=resolved_tcs[0] if resolved_tcs else "docs/",
                what_is="Test cases reference missing or unknown REQ/AC IDs.",
                problem="Broken RTM traceability hides coverage gaps.",
                fix="Map each test case REQ ID to a valid specification requirement.",
                if_skipped="Traceability matrix audits will fail.",
            )
        )

    if not coverage.linter_passed:
        findings.append(
            _make_manual_finding(
                severity="Must fix",
                code="MANUAL_LINTER_DEFECT",
                title=f"manual_tc_linter reported {len(coverage.linter_defects)} defect(s)",
                file_path=resolved_tcs[0] if resolved_tcs else "docs/",
                what_is="; ".join(coverage.linter_defects[:3]) or "Manual test case table failed lint gate.",
                problem="Vague oracles, missing columns, or Golden Ratio violations degrade QA rigor.",
                fix="Resolve defects reported by python3 tools/lint/manual_tc_linter.py.",
                if_skipped="Ambiguous manual test steps cause inconsistent QA execution.",
            )
        )

    if not spec_mut.passed:
        findings.append(
            _make_manual_finding(
                severity="Must fix",
                code="SPEC_MUTATION_BELOW_THRESHOLD",
                title=f"Spec-Mutation score {spec_mut.kill_score}% < {spec_mut.threshold}%",
                file_path=resolved_tcs[0] if resolved_tcs else (inv.spec_path or "docs/"),
                what_is=f"Survived fault-injection mutants: {', '.join(spec_mut.survived_mutants[:5])}.",
                problem="Test suite lacks negative, boundary, RBAC, or resilience coverage to catch injected faults.",
                fix="Add concrete test cases killing the surviving spec mutants.",
                if_skipped="High-severity defects escape manual QA.",
            )
        )

    has_must_fix = any(f["severity"] == "Must fix" for f in findings)
    passed = (not has_must_fix) and coverage.passed and spec_mut.passed and (receipt_verified or not strict_solo)

    return ManualReviewReportDTO(
        profile="manual",
        spec_inventory=inv,
        coverage_audit=coverage,
        spec_mutation=spec_mut,
        receipt_verified=receipt_verified,
        findings=tuple(findings),
        passed=passed,
    )
