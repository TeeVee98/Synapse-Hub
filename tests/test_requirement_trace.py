#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_requirement_trace.py
Verifies versioned requirement extraction (DOCX paragraphs & tables), many-to-many links,
ambiguous duplicate IDs, changed requirement history, and build-specific JUnit execution denominators.
"""

import dataclasses
from pathlib import Path
import zipfile
import pytest


def _make_docx(path: Path, paragraphs: list[str], table_rows: list[list[str]] | None = None) -> Path:
    """Creates a minimal valid .docx archive with paragraphs and optional table rows."""
    p_xml = "".join(
        f"<w:p><w:r><w:t>{txt}</w:t></w:r></w:p>" for txt in paragraphs
    )
    tbl_xml = ""
    if table_rows:
        rows_xml = ""
        for row in table_rows:
            cells_xml = "".join(
                f"<w:tc><w:p><w:r><w:t>{cell}</w:t></w:r></w:p></w:tc>" for cell in row
            )
            rows_xml += f"<w:tr>{cells_xml}</w:tr>"
        tbl_xml = f"<w:tbl>{rows_xml}</w:tbl>"

    doc_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{p_xml}{tbl_xml}</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>')
        zf.writestr("word/document.xml", doc_xml)
    return path


def test_docx_extraction_two_revisions_many_to_many_and_explicit_denominators(tmp_path):
    """Positive: Extracts DOCX paragraphs/tables across two sources, handles M:N links and build denominators."""
    from tools.manual.requirement_trace import (
        RequirementLink,
        build_trace_matrix,
        extract_docx_requirements,
    )

    urd_v1 = _make_docx(
        tmp_path / "urd_v1.docx",
        paragraphs=["REQ-01: User must sign in with email and password."],
        table_rows=[["ID", "Rule"], ["REQ-02", "Reject locked user accounts."]],
    )
    srs_v1 = _make_docx(
        tmp_path / "srs_v1.docx",
        paragraphs=["REQ-01: Sign-in API returns session token.", "REQ-03: Password reset expires after 15m."],
    )

    urd_reqs = extract_docx_requirements(str(urd_v1), document_id="URD", document_version="v1.0")
    srs_reqs = extract_docx_requirements(str(srs_v1), document_id="SRS", document_version="v1.0")
    assert [r.requirement_id for r in urd_reqs] == ["REQ-01", "REQ-02"]
    assert urd_reqs[1].source_anchor.startswith("tbl:")
    assert [r.requirement_id for r in srs_reqs] == ["REQ-01", "REQ-03"]

    with pytest.raises(dataclasses.FrozenInstanceError) as rec_exc:
        urd_reqs[0].requirement_id = "REQ-999"  # type: ignore[misc]
    assert rec_exc.value is not None

    links = [
        RequirementLink("v1.0", "URD#p:1", "REQ-01", "TC-AUTH-01", "build-2"),
        RequirementLink("v1.0", "SRS#p:1", "REQ-01", "TC-AUTH-01", "build-2"),
        RequirementLink("v1.0", "tbl:0:r:1", "REQ-02", "TC-AUTH-02", "build-2"),
    ]
    junit_results = {
        ("TC-AUTH-01", "build-2"): "passed",
        ("TC-AUTH-02", "build-2"): "passed",
        ("TC-AUTH-03", "build-1"): "passed",
    }
    dispositions = {
        "URD:REQ-01": "mapped_explicit_urd",
        "SRS:REQ-01": "mapped_explicit_srs",
    }
    matrix = build_trace_matrix(
        requirements=urd_reqs + srs_reqs,
        links=links,
        junit_results=junit_results,
        candidate_build="build-2",
        dispositions=dispositions,
    )
    counts = matrix["counts"]
    assert counts["total_requirements"] == 4
    assert counts["designed"]["numerator"] == 3 and counts["designed"]["denominator"] == 4
    assert counts["automated"]["numerator"] == 3 and counts["automated"]["denominator"] == 4
    assert counts["executed"]["numerator"] == 3 and counts["executed"]["denominator"] == 4
    assert counts["passed"]["numerator"] == 3 and counts["passed"]["denominator"] == 4

    unlinked = [row for row in matrix["rows"] if row["requirement_id"] == "REQ-03"]
    assert len(unlinked) == 1 and unlinked[0]["disposition"] == "unlinked"


def test_older_build_changed_requirement_history_and_ambiguous_duplicates(tmp_path):
    """Negative: Older build results do not certify candidate; changed req keeps history; duplicate needs disposition."""
    from tools.manual.requirement_trace import (
        RequirementLink,
        build_trace_matrix,
        extract_docx_requirements,
    )

    urd_v1 = _make_docx(tmp_path / "urd_v1.docx", ["REQ-01: Initial sign-in spec."])
    urd_v2 = _make_docx(tmp_path / "urd_v2.docx", ["REQ-01: Updated sign-in spec with MFA."])
    srs_v1 = _make_docx(tmp_path / "srs_v1.docx", ["REQ-01: Duplicate label in SRS."])

    prior = extract_docx_requirements(str(urd_v1), document_id="URD", document_version="v1.0")
    curr_urd = extract_docx_requirements(str(urd_v2), document_id="URD", document_version="v2.0")
    curr_srs = extract_docx_requirements(str(srs_v1), document_id="SRS", document_version="v1.0")

    links = [
        RequirementLink("v2.0", "URD#p:1", "REQ-01", "TC-01", "build-2"),
        RequirementLink("v1.0", "SRS#p:1", "REQ-01", "TC-02", "build-1"),
    ]
    junit_results = {
        ("TC-01", "build-1"): "passed",  # Older build only
        ("TC-02", "build-1"): "passed",
    }
    matrix = build_trace_matrix(
        requirements=curr_urd + curr_srs,
        links=links,
        junit_results=junit_results,
        candidate_build="build-2",
        prior_requirements=prior,
    )
    assert matrix["counts"]["executed"]["numerator"] == 0
    assert matrix["counts"]["passed"]["numerator"] == 0

    urd_row = next(r for r in matrix["rows"] if r["document_id"] == "URD")
    assert urd_row["changed_review_requested"] is True
    assert len(urd_row["history"]) == 1
    assert urd_row["history"][0]["document_version"] == "v1.0"
    assert urd_row["ambiguity_status"] == "ambiguous_requires_disposition"


def test_manual_pipeline_adapter_reads_docx_and_corrupt_boundary(tmp_path):
    """Boundary: manual_pipeline_adapter extracts .docx paragraphs/tables; corrupt .docx fails cleanly."""
    from tools.manual.manual_pipeline_adapter import extract_manual_spec_inventory
    from tools.manual.requirement_trace import RequirementLink, build_trace_matrix

    docx_spec = _make_docx(
        tmp_path / "brd.docx",
        paragraphs=["AC-01: User submits valid email and password to login."],
        table_rows=[["Req", "Detail"], ["REQ-02", "Lock account after 5 invalid OTP attempts."]],
    )
    inv = extract_manual_spec_inventory(str(docx_spec), repo_root=str(tmp_path))
    assert "AC-01" in inv.requirement_ids
    assert "REQ-02" in inv.requirement_ids
    assert "email" in inv.detected_fields

    bad_docx = tmp_path / "corrupt.docx"
    bad_docx.write_bytes(b"not-a-zip")
    bad_inv = extract_manual_spec_inventory(str(bad_docx), repo_root=str(tmp_path))
    assert bad_inv.requirement_ids == ()

    md_spec = tmp_path / "brd_plain.md"
    md_spec.write_text("REQ-99: Plain markdown specification with email field.\n", encoding="utf-8")
    md_inv = extract_manual_spec_inventory(str(md_spec), repo_root=str(tmp_path))
    assert "REQ-99" in md_inv.requirement_ids

    empty_docx = tmp_path / "empty.docx"
    empty_docx.write_bytes(b"")
    empty_inv = extract_manual_spec_inventory(str(empty_docx), repo_root=str(tmp_path))
    assert empty_inv.requirement_ids == ()
    assert empty_inv.spec_hash != ""

    tiny_docx = tmp_path / "tiny.docx"
    tiny_docx.write_bytes(b"x")
    tiny_inv = extract_manual_spec_inventory(str(tiny_docx), repo_root=str(tmp_path))
    assert tiny_inv.spec_hash == ""

    empty_matrix = build_trace_matrix([], [], {}, candidate_build="build-1")
    assert empty_matrix["counts"]["total_requirements"] == 0

    link = RequirementLink("v1.0", "p:1", "REQ-01", "TC-1", "build-1")
    with pytest.raises(dataclasses.FrozenInstanceError) as frozen_exc:
        link.case_id = "TC-2"  # type: ignore[misc]
    assert frozen_exc.value is not None


def test_dispositions_resolve_duplicate_labels_and_failed_case_blocks_pass(tmp_path):
    """Resilience: Explicit manual dispositions resolve duplicate IDs and failed JUnit prevents pass."""
    from tools.manual.requirement_trace import (
        RequirementLink,
        build_trace_matrix,
        extract_docx_requirements,
    )

    d1 = _make_docx(tmp_path / "d1.docx", ["REQ-10: Export CSV."])
    d2 = _make_docx(tmp_path / "d2.docx", ["REQ-10: Export XLSX."])
    reqs = extract_docx_requirements(str(d1), "DOC1", "v1") + extract_docx_requirements(str(d2), "DOC2", "v1")

    links = [
        RequirementLink("v1", "DOC1#p:1", "REQ-10", "TC-CSV", "b-9"),
        RequirementLink("v1", "DOC2#p:1", "REQ-10", "TC-XLSX", "b-9"),
    ]
    junit_results = {
        ("TC-CSV", "b-9"): "passed",
        ("TC-XLSX", "b-9"): "failed",
    }
    matrix = build_trace_matrix(
        requirements=reqs,
        links=links,
        junit_results=junit_results,
        candidate_build="b-9",
        dispositions={"DOC1:REQ-10": "resolved_csv", "DOC2:REQ-10": "resolved_xlsx"},
    )
    assert all(r["ambiguity_status"] == "resolved" for r in matrix["rows"])
    assert matrix["counts"]["executed"]["numerator"] == 2
    assert matrix["counts"]["passed"]["numerator"] == 1

    # Non-duplicate requirement using fallback anchor resolves without disposition; unlinked unique req resolves cleanly
    unique_d = _make_docx(tmp_path / "uniq.docx", ["REQ-20: Unique req.", "REQ-21: Unlinked unique req."])
    u_reqs = extract_docx_requirements(str(unique_d), "UNIQ", "v1")
    u_matrix = build_trace_matrix(
        requirements=u_reqs,
        links=[RequirementLink("v1", "legacy-anchor", "REQ-20", "TC-20", "b-9")],
        junit_results={("TC-20", "b-9"): "passed"},
        candidate_build="b-9",
    )
    r20 = next(r for r in u_matrix["rows"] if r["requirement_id"] == "REQ-20")
    r21 = next(r for r in u_matrix["rows"] if r["requirement_id"] == "REQ-21")
    assert r20["ambiguity_status"] == "resolved"
    assert r20["linked_cases"] == ["TC-20"]
    assert r21["ambiguity_status"] == "resolved"
    assert r21["disposition"] == "unlinked"

    zero_docx = tmp_path / "zero.docx"
    zero_docx.write_bytes(b"")
    from tools.manual.manual_pipeline_adapter import extract_manual_spec_inventory
    zero_inv = extract_manual_spec_inventory(str(zero_docx), repo_root=str(tmp_path))
    assert zero_inv.requirement_ids == ()
