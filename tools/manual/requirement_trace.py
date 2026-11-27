#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/manual/requirement_trace.py — Versioned Requirement & Execution Traceability
-----------------------------------------------------------------------------------
Extracts versioned requirements from DOCX paragraphs and tables via mcp_docx_server,
resolves many-to-many requirement-to-case links across document revisions, preserves
changed-requirement history, flags ambiguous duplicate labels, and computes explicit
denominators bound to candidate build JUnit results.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from tools.mcp.mcp_docx_server import (
    NS_W,
    _extract_paragraph_text,
    get_docx_zip,
    read_docx_tables,
    safe_parse_xml,
)

_REQ_ID_RE = re.compile(r"\b((?:AC|REQ|BR|FR|NFR|US|YC)[-_]\d+[A-Za-z0-9_-]*)\b", re.IGNORECASE)


@dataclass(frozen=True)
class RequirementLink:
    """Typed link binding a versioned requirement anchor to an automated/manual case and build."""

    document_version: str
    source_anchor: str
    requirement_id: str
    case_id: str
    build_id: str | None


@dataclass(frozen=True)
class RequirementRecord:
    """Extracted requirement item with version, structural anchor, and content SHA-256 digest."""

    document_id: str
    document_version: str
    source_anchor: str
    requirement_id: str
    content_digest: str


def read_docx_text_blocks(docx_path: str) -> List[Tuple[str, str]]:
    """Reads (source_anchor, text) blocks from DOCX paragraphs and tables via mcp_docx_server."""
    blocks: List[Tuple[str, str]] = []
    with get_docx_zip(docx_path) as zf:
        if "word/document.xml" not in zf.namelist():
            raise ValueError("Corrupt .docx: missing word/document.xml")
        with zf.open("word/document.xml") as fp:
            root = safe_parse_xml(fp)
    body = root.find(f"{NS_W}body")
    if body is None:
        return blocks

    p_idx = 0
    for elem in body:
        if elem.tag == f"{NS_W}p":
            p_idx += 1
            text = _extract_paragraph_text(elem).strip()
            if text:
                blocks.append((f"p:{p_idx}", text))

    for tbl in read_docx_tables(docx_path):
        t_idx = tbl.get("table_index", 0)
        for r_idx, row in enumerate(tbl.get("matrix") or []):
            joined = " | ".join(str(cell).strip() for cell in row if str(cell).strip())
            if joined:
                blocks.append((f"tbl:{t_idx}:r:{r_idx}", joined))
    return blocks


def extract_docx_requirements(
    docx_path: str,
    document_id: str,
    document_version: str,
) -> List[RequirementRecord]:
    """Extracts unique versioned RequirementRecord entries from DOCX paragraphs and tables."""
    records: List[RequirementRecord] = []
    seen_ids: Set[str] = set()
    for anchor, text in read_docx_text_blocks(docx_path):
        for match in _REQ_ID_RE.finditer(text):
            req_id = match.group(1).upper().replace("_", "-")
            if req_id in seen_ids:
                continue
            seen_ids.add(req_id)
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            records.append(
                RequirementRecord(
                    document_id=document_id,
                    document_version=document_version,
                    source_anchor=anchor,
                    requirement_id=req_id,
                    content_digest=digest,
                )
            )
    return records


def _match_links_for_requirement(
    rec: RequirementRecord,
    links: Sequence[RequirementLink],
    is_duplicate_label: bool,
    disposition: Optional[str],
) -> Tuple[List[RequirementLink], str]:
    """Resolves many-to-many links for one requirement, distinguishing ambiguous duplicates."""
    exact_anchor = [
        lk for lk in links
        if lk.requirement_id.upper() == rec.requirement_id
        and lk.document_version == rec.document_version
        and (
            lk.source_anchor == rec.source_anchor
            or lk.source_anchor == f"{rec.document_id}#{rec.source_anchor}"
            or lk.source_anchor.startswith(f"{rec.document_id}#")
        )
    ]
    if exact_anchor:
        amb_status = "resolved" if (not is_duplicate_label or disposition) else "ambiguous_requires_disposition"
        return exact_anchor, amb_status

    fallback = [lk for lk in links if lk.requirement_id.upper() == rec.requirement_id]
    if is_duplicate_label and fallback and not disposition:
        return fallback, "ambiguous_requires_disposition"
    amb_status = "resolved" if (not is_duplicate_label or disposition) else "ambiguous_requires_disposition"
    return fallback, amb_status


def _evaluate_case_execution(
    matched_links: Sequence[RequirementLink],
    junit_results: Dict[Tuple[str, str], str],
    candidate_build: str,
) -> Tuple[bool, bool, bool, bool]:
    """Computes (designed, automated, executed, passed) flags for one requirement on candidate_build."""
    if not matched_links:
        return False, False, False, False
    case_ids = sorted({lk.case_id for lk in matched_links if lk.case_id})
    designed = len(case_ids) > 0
    automated = designed
    statuses = [junit_results.get((cid, candidate_build)) for cid in case_ids]
    exec_statuses = [st for st in statuses if st in ("passed", "failed")]
    executed = len(exec_statuses) > 0
    passed = executed and len(exec_statuses) == len(case_ids) and all(st == "passed" for st in exec_statuses)
    return designed, automated, executed, passed


def build_trace_matrix(
    requirements: Sequence[RequirementRecord],
    links: Sequence[RequirementLink],
    junit_results: Dict[Tuple[str, str], str],
    candidate_build: str,
    prior_requirements: Optional[Sequence[RequirementRecord]] = None,
    dispositions: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Reconciles versioned requirements, M:N links, dispositions, and build-specific JUnit outcomes."""
    disp_map = dispositions or {}
    prior_by_key: Dict[Tuple[str, str], List[RequirementRecord]] = {}
    for prev in prior_requirements or ():
        prior_by_key.setdefault((prev.document_id, prev.requirement_id), []).append(prev)

    label_counts: Dict[str, int] = {}
    for rec in requirements:
        label_counts[rec.requirement_id] = label_counts.get(rec.requirement_id, 0) + 1

    rows: List[Dict[str, Any]] = []
    designed_n = automated_n = executed_n = passed_n = 0

    for rec in requirements:
        is_dup = label_counts.get(rec.requirement_id, 0) > 1
        disp_key = f"{rec.document_id}:{rec.requirement_id}"
        disp = disp_map.get(disp_key) or disp_map.get(rec.requirement_id)
        matched_links, amb_status = _match_links_for_requirement(rec, links, is_dup, disp)
        designed, automated, executed, passed = _evaluate_case_execution(matched_links, junit_results, candidate_build)

        designed_n += int(designed)
        automated_n += int(automated)
        executed_n += int(executed)
        passed_n += int(passed)

        prior_list = prior_by_key.get((rec.document_id, rec.requirement_id), [])
        history = [
            {"document_version": p.document_version, "content_digest": p.content_digest, "source_anchor": p.source_anchor}
            for p in prior_list
        ]
        changed = any(
            p.content_digest != rec.content_digest or p.document_version != rec.document_version
            for p in prior_list
        )
        disposition = disp or ("unlinked" if not matched_links else ("passed" if passed else "pending_or_failed"))
        rows.append(
            {
                "document_id": rec.document_id,
                "document_version": rec.document_version,
                "requirement_id": rec.requirement_id,
                "source_anchor": rec.source_anchor,
                "content_digest": rec.content_digest,
                "linked_cases": sorted({lk.case_id for lk in matched_links}),
                "ambiguity_status": amb_status,
                "changed_review_requested": changed,
                "history": history,
                "disposition": disposition,
                "executed_on_candidate": executed,
                "passed_on_candidate": passed,
            }
        )

    total = len(requirements)
    return {
        "candidate_build": candidate_build,
        "rows": rows,
        "counts": {
            "total_requirements": total,
            "designed": {"numerator": designed_n, "denominator": total, "ratio": f"{designed_n}/{total}"},
            "automated": {"numerator": automated_n, "denominator": total, "ratio": f"{automated_n}/{total}"},
            "executed": {"numerator": executed_n, "denominator": total, "ratio": f"{executed_n}/{total}"},
            "passed": {"numerator": passed_n, "denominator": total, "ratio": f"{passed_n}/{total}"},
        },
    }
