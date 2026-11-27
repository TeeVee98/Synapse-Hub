#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_coverage_workbook_pilot.py
Validates generic versioned trace workbook export and reopen comparison across a
synthetic 75-case pilot fixture mirroring assignment sheets, requirement revisions,
formulas, merged banners, unmapped/unrun dispositions, and summary reconciliation.
"""

import json
from pathlib import Path
import subprocess
import sys
import zipfile
import openpyxl
import pytest


def _make_docx(path: Path, paragraphs: list[str]) -> Path:
    body = "".join(f"<w:p><w:r><w:t>{txt}</w:t></w:r></w:p>" for txt in paragraphs)
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>')
        zf.writestr("word/document.xml", xml)
    return path


def _build_synthetic_75_workbook(path: Path) -> Path:
    wb = openpyxl.Workbook()
    ws_sum = wb.active
    ws_sum.title = "ExecutiveSummary"
    ws_sum.merge_cells("A1:D1")
    ws_sum["A1"] = "Synthetic QA Coverage Dashboard"
    ws_sum["A3"] = "Total Cases"
    ws_sum["B3"] = "=COUNTA(AssignmentSheet!B5:B79)"
    ws_sum["A4"] = "Passed"
    ws_sum["B4"] = '=COUNTIF(AssignmentSheet!G5:G79,"passed")'
    ws_sum["A5"] = "Unrun"
    ws_sum["B5"] = '=COUNTIF(AssignmentSheet!G5:G79,"unrun")'
    ws_sum["A6"] = "Unmapped"
    ws_sum["B6"] = '=COUNTIF(AssignmentSheet!G5:G79,"unmapped")'

    ws_det = wb.create_sheet("AssignmentSheet")
    ws_det.merge_cells("A1:I1")
    ws_det["A1"] = "Synthetic Multi-Module Assignment Plan"
    ws_det.append([])
    ws_det.append([])
    ws_det.append([
        "Seq",
        "Automation Case ID",
        "Owner",
        "Requirement Refs",
        "Doc Revisions",
        "Source Anchors",
        "Trace Disposition",
        "Candidate Build",
        "Execution Result",
    ])
    for idx in range(1, 76):
        ws_det.append([
            idx,
            f"SYN-TC-{idx:03d}",
            f"qa_owner_{(idx % 5) + 1}",
            "",
            "",
            "",
            "",
            "",
            "=IF(G" + str(idx + 4) + '="passed","OK","REVIEW")',
        ])

    ws_hist = wb.create_sheet("RevisionNotes")
    ws_hist["A1"] = "Baseline untouched metadata"
    ws_hist["B2"] = "Keep intact"

    wb.save(path)
    return path


def _build_synthetic_75_trace_matrix(tmp_path: Path) -> dict:
    from tools.manual.requirement_trace import (
        RequirementLink,
        build_trace_matrix,
        extract_docx_requirements,
    )

    urd_prev = _make_docx(tmp_path / "urd_v1.docx", [f"REQ-{i:02d}: Legacy spec {i}." for i in range(1, 16)])
    urd_curr = _make_docx(tmp_path / "urd_v2.docx", [f"REQ-{i:02d}: Updated spec {i}." if i == 1 else f"REQ-{i:02d}: Spec {i}." for i in range(1, 16)])
    srs_curr = _make_docx(tmp_path / "srs_v2.docx", [f"SRS-{i:02d}: Api rule {i}." for i in range(1, 16)])

    prior = extract_docx_requirements(str(urd_prev), "URD", "v2.0.0")
    reqs = extract_docx_requirements(str(urd_curr), "URD", "v2.0.5") + extract_docx_requirements(str(srs_curr), "SRS", "v2.0.4")

    links = []
    junit_results = {}
    # Link first 70 cases across URD & SRS; leave 71-73 unrun, 74-75 unmapped
    for idx in range(1, 74):
        case_id = f"SYN-TC-{idx:03d}"
        req_idx = ((idx - 1) % 15) + 1
        req_id = f"REQ-{req_idx:02d}"
        links.append(RequirementLink("v2.0.5", f"URD#p:{req_idx}", req_id, case_id, "build-rc-75"))
        if idx <= 60:
            junit_results[(case_id, "build-rc-75")] = "passed"
        elif idx <= 70:
            junit_results[(case_id, "build-rc-75")] = "failed"
        # 71..73 remain unrun on build-rc-75 (older build only or absent)
        junit_results[(case_id, "build-old")] = "passed"

    matrix = build_trace_matrix(
        requirements=reqs,
        links=links,
        junit_results=junit_results,
        candidate_build="build-rc-75",
        prior_requirements=prior,
    )
    matrix["case_outcomes"] = {
        cid: status
        for (cid, build_id), status in junit_results.items()
        if build_id == "build-rc-75"
    }
    return matrix


def test_synthetic_75_case_pilot_preserves_workbook_and_reconciles(tmp_path):
    """Positive: 75 anonymized synthetic cases receive explicit dispositions and reconcile on reopen."""
    from tools.contrib.template_excel_exporter import export_versioned_trace_workbook

    template_xlsx = _build_synthetic_75_workbook(tmp_path / "pilot_template.xlsx")
    out_xlsx = tmp_path / "pilot_exported.xlsx"
    matrix = _build_synthetic_75_trace_matrix(tmp_path)

    profile = {
        "detail_sheet": "AssignmentSheet",
        "summary_sheet": "ExecutiveSummary",
        "header_row": 4,
        "column_labels": {
            "case_id": ["Automation Case ID"],
            "requirement_id": ["Requirement Refs"],
            "document_version": ["Doc Revisions"],
            "source_anchor": ["Source Anchors"],
            "disposition": ["Trace Disposition"],
            "candidate_build": ["Candidate Build"],
        },
    }
    report = export_versioned_trace_workbook(
        template_path=str(template_xlsx),
        output_path=str(out_xlsx),
        trace_matrix=matrix,
        profile=profile,
        compare_after_reopen=True,
    )

    assert report["case_count"] == 75
    counts = report["disposition_counts"]
    assert sum(counts.values()) == 75
    assert counts["passed"] == 60
    assert counts["failed"] == 10
    assert counts["unrun"] == 3
    assert counts["unmapped"] == 2

    cmp_res = report["comparison"]
    assert cmp_res["passed"] is True
    assert cmp_res["sheet_order_preserved"] is True
    assert cmp_res["formulas_preserved"] is True
    assert cmp_res["merged_cells_preserved"] is True
    assert cmp_res["unrelated_cells_preserved"] is True
    assert cmp_res["reconciled"] is True

    reopened = openpyxl.load_workbook(out_xlsx, data_only=False)
    assert reopened["AssignmentSheet"]["C5"].value == "qa_owner_2"
    assert reopened["AssignmentSheet"]["D5"].value == "REQ-01"
    assert reopened["AssignmentSheet"]["E5"].value == "URD:v2.0.5"
    assert reopened["AssignmentSheet"]["F5"].value == "URD#p:1"
    assert reopened["AssignmentSheet"]["H5"].value == "build-rc-75"
    assert reopened["AssignmentSheet"]["I5"].value == '=IF(G5="passed","OK","REVIEW")'
    assert reopened["RevisionNotes"]["B2"].value == "Keep intact"


def test_negative_missing_sheet_tampered_reopen_and_generic_hub_code(tmp_path):
    """Negative: Missing target sheet or header fails loudly; reopened formula drift fails comparison."""
    from tools.contrib.template_excel_exporter import (
        compare_workbook_semantics,
        export_versioned_trace_workbook,
    )

    exporter_src = (Path(__file__).resolve().parent.parent / "tools" / "contrib" / "template_excel_exporter.py").read_text(encoding="utf-8")
    assert "edig" not in exporter_src.lower()
    assert "odp" not in exporter_src.lower()

    template_xlsx = _build_synthetic_75_workbook(tmp_path / "neg_template.xlsx")
    out_xlsx = tmp_path / "neg_exported.xlsx"
    matrix = _build_synthetic_75_trace_matrix(tmp_path)

    with pytest.raises(ValueError) as missing_sheet_exc:
        export_versioned_trace_workbook(
            template_path=str(template_xlsx),
            output_path=str(out_xlsx),
            trace_matrix=matrix,
            profile={"detail_sheet": "NonExistentTab"},
        )
    assert "NonExistentTab" in str(missing_sheet_exc.value)

    profile = {
        "detail_sheet": "AssignmentSheet",
        "summary_sheet": "ExecutiveSummary",
        "column_labels": {
            "case_id": ["Automation Case ID"],
            "disposition": ["Trace Disposition"],
        },
    }
    export_versioned_trace_workbook(str(template_xlsx), str(out_xlsx), matrix, profile=profile)
    # Tamper formula & merged range in exported workbook
    tampered_wb = openpyxl.load_workbook(out_xlsx)
    tampered_wb["ExecutiveSummary"]["B3"] = 999
    tampered_wb.save(out_xlsx)

    bad_cmp = compare_workbook_semantics(str(template_xlsx), str(out_xlsx), profile=profile)
    assert bad_cmp["passed"] is False
    assert bad_cmp["formulas_preserved"] is False


def test_boundary_empty_trace_marks_all_unmapped_and_missing_header_fails(tmp_path):
    """Boundary: Empty trace marks all 75 rows unmapped; unresolvable header label raises ValueError."""
    from tools.contrib.template_excel_exporter import export_versioned_trace_workbook

    template_xlsx = _build_synthetic_75_workbook(tmp_path / "empty_trace.xlsx")
    out_xlsx = tmp_path / "empty_trace_out.xlsx"
    profile = {
        "detail_sheet": "AssignmentSheet",
        "summary_sheet": "ExecutiveSummary",
        "column_labels": {
            "case_id": ["Automation Case ID"],
            "disposition": ["Trace Disposition"],
        },
    }
    report = export_versioned_trace_workbook(
        template_path=str(template_xlsx),
        output_path=str(out_xlsx),
        trace_matrix={"candidate_build": "build-empty", "rows": []},
        profile=profile,
    )
    assert report["case_count"] == 75
    assert report["disposition_counts"].get("unmapped") == 75
    assert report["comparison"]["passed"] is True

    with pytest.raises(ValueError) as bad_hdr_exc:
        export_versioned_trace_workbook(
            template_path=str(template_xlsx),
            output_path=str(out_xlsx),
            trace_matrix={"candidate_build": "build-empty", "rows": []},
            profile={"detail_sheet": "AssignmentSheet", "column_labels": {"case_id": ["NoSuchHeader"]}},
        )
    assert "NoSuchHeader" in str(bad_hdr_exc.value) or "case_id" in str(bad_hdr_exc.value)


def test_cli_trace_export_json_and_reopen_idempotency(tmp_path):
    """CLI & Resilience: Exporter CLI --trace-json --template-profile --json runs cleanly twice."""
    template_xlsx = _build_synthetic_75_workbook(tmp_path / "cli_template.xlsx")
    out_xlsx = tmp_path / "cli_exported.xlsx"
    trace_json = tmp_path / "trace.json"
    profile_json = tmp_path / "profile.json"

    trace_json.write_text(json.dumps(_build_synthetic_75_trace_matrix(tmp_path)), encoding="utf-8")
    profile_json.write_text(
        json.dumps(
            {
                "detail_sheet": "AssignmentSheet",
                "summary_sheet": "ExecutiveSummary",
                "column_labels": {
                    "case_id": ["Automation Case ID"],
                    "requirement_id": ["Requirement Refs"],
                    "document_version": ["Doc Revisions"],
                    "source_anchor": ["Source Anchors"],
                    "disposition": ["Trace Disposition"],
                    "candidate_build": ["Candidate Build"],
                },
            }
        ),
        encoding="utf-8",
    )

    repo_root = Path(__file__).resolve().parent.parent
    cmd = [
        sys.executable,
        str(repo_root / "tools" / "contrib" / "template_excel_exporter.py"),
        "--template",
        str(template_xlsx),
        "-o",
        str(out_xlsx),
        "--trace-json",
        str(trace_json),
        "--template-profile",
        str(profile_json),
        "--json",
    ]
    res1 = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True, timeout=30)
    assert res1.returncode == 0, res1.stderr
    payload1 = json.loads(res1.stdout)
    assert payload1["case_count"] == 75
    assert payload1["comparison"]["passed"] is True

    res2 = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True, timeout=30)
    assert res2.returncode == 0, res2.stderr
    payload2 = json.loads(res2.stdout)
    assert payload2["disposition_counts"] == payload1["disposition_counts"]
