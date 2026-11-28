#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Template-Driven Excel Test Case Exporter
-----------------------------------------
Enables zero-pollution, template-driven test case export into existing corporate
Excel workbooks. Preserves 100% of the original template's styling, formulas,
merged headers, summary dashboards, fonts, borders, and column widths.

Design Philosophy (Hub & Spoke):
  - Hub remains 100% generic, zero hardcoding of any specific client/project.
  - Client projects specify their template via `--template` or `.synapse.json`.
  - If no template is provided, falls back cleanly to the Hub standard 12-column layout.
"""
import os
import sys

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.append(_p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass


import os
import sys
import re
import json
import datetime
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional


@dataclass(frozen=True)
class TraceCellMismatchDTO:
    sheet: str
    cell: str
    row: int
    case_id: str
    role: str
    expected: str
    actual: str

# Enforce UTF-8 stdio
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


def find_project_config(start_dir: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Walks up from start_dir to find a .synapse.json configuration file."""
    cur = Path(start_dir or os.getcwd()).resolve()
    user_home = Path.home().resolve()
    for p in [cur] + list(cur.parents):
        if p == user_home:
            # ~/.synapse.json in user home is a global user preference, not a project config
            break
        cfg_file = p / ".synapse.json"
        if cfg_file.is_file():
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data["_config_dir"] = str(p)
                    return data
            except Exception:
                continue
    return None


def parse_testcases_from_markdown(content: str) -> List[Dict[str, Any]]:
    """
    Parses test cases from a Markdown text.
    Supports both table format (| TC_ID | ...) and structured list items.
    """
    rows = []
    lines = content.splitlines()
    in_table = False
    headers = []

    for line in lines:
        line_s = line.strip()
        if not line_s:
            continue

        # Check section header (e.g., "### 1. Màn hình [...]" or "**1. Màn hình [...]**")
        sec_m = re.match(r'^(?:#{1,4}\s*|\*{2})?([0-9]+\.\s*Màn hình.*)', line_s, re.IGNORECASE)
        if sec_m:
            in_table = False
            sec_title = sec_m.group(1).rstrip('*').strip()
            rows.append({"type": "section", "text": sec_title})
            continue

        # Sub-action header (e.g. "Truy cập và kiểm tra...")
        if line_s.startswith("## ") or (line_s.startswith("**") and line_s.endswith("**") and not line_s.startswith("|")):
            in_table = False
            action_title = line_s.strip("#* ").strip()
            rows.append({"type": "subsection", "text": action_title})
            continue

        # Precondition block
        if line_s.lower().startswith("tiền điều kiện:") or line_s.lower().startswith("**tiền điều kiện:**"):
            in_table = False
            precond_text = re.sub(r'^\*?\*?tiền điều kiện:\*?\*?\s*', '', line_s, flags=re.IGNORECASE).strip()
            rows.append({"type": "precondition", "text": precond_text})
            continue

        # Markdown Table parsing
        if line_s.startswith("|") and line_s.endswith("|"):
            parts = [c.strip() for c in line_s.split("|")[1:-1]]
            if not in_table or (parts and parts[0].lower() in ("testcase_id", "tc_id", "tc id", "tc", "stt")):
                # Table headers
                headers = [p.lower() for p in parts]
                in_table = True
                continue
            elif all(re.match(r'^:?-+:?$', p) for p in parts if p):
                # Separator line
                continue
            else:
                # Data row
                row_dict = {"type": "case"}
                for i, h in enumerate(headers):
                    if i < len(parts):
                        row_dict[h] = parts[i]
                rows.append(row_dict)
        else:
            in_table = False

    return rows


def clone_and_export_template(
    rows: List[Dict[str, Any]],
    output_path: str,
    template_path: str,
    sample_sheet_name: Optional[str] = None,
    target_sheet_name: Optional[str] = None,
    module_code: str = "MODULE",
    module_name: str = "Test Module",
    author: str = "QA Engineer",
    tester: str = "QA Engineer",
    keep_other_sheets: bool = True
) -> str:
    """
    Clones the template workbook or sample worksheet, updates metadata and formulas,
    populates test cases, and writes to output_path.
    """
    if not OPENPYXL_AVAILABLE:
        raise RuntimeError("openpyxl is required for template-driven Excel export. Run: pip install openpyxl")

    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template Excel file not found: {template_path}")

    wb = openpyxl.load_workbook(template_path, data_only=False)

    if not sample_sheet_name or sample_sheet_name not in wb.sheetnames:
        # Fallback to first available sheet in the template
        sample_sheet_name = wb.sheetnames[0]

    src_sheet = wb[sample_sheet_name]
    new_sheet_name = target_sheet_name or sample_sheet_name

    if new_sheet_name == sample_sheet_name and not keep_other_sheets:
        target_ws = src_sheet
    elif new_sheet_name in wb.sheetnames and new_sheet_name != sample_sheet_name:
        target_ws = wb[new_sheet_name]
    else:
        target_ws = wb.copy_worksheet(src_sheet)
        target_ws.title = new_sheet_name

    # Unmerge stale merged cells from row 11 downwards only
    merged_to_remove = [rng for rng in target_ws.merged_cells.ranges if rng.min_row >= 11]
    for rng in merged_to_remove:
        target_ws.unmerge_cells(str(rng))

    template_max_r = target_ws.max_row

    # Update metadata header (rows 2-6)
    target_ws["B2"] = module_code
    target_ws["D2"] = module_name
    target_ws["B3"] = author
    target_ws["B4"] = datetime.datetime.now().strftime("%Y-%m-%d")
    target_ws["B5"] = tester
    target_ws["B6"] = datetime.datetime.now().strftime("%Y-%m-%d")

    # Font and Border styles matching corporate template
    font_case = Font(name="Times New Roman", size=11, bold=False, italic=False, color="000000")
    font_case_bold = Font(name="Times New Roman", size=11, bold=True, italic=False, color="000000")
    font_sec1 = Font(name="Times New Roman", size=11, bold=True, italic=False, color="000000")
    font_sec2 = Font(name="Times New Roman", size=11, bold=True, italic=False, color="000000")
    font_precond_label = Font(name="Times New Roman", size=11, bold=True, italic=True, color="0000FF")

    # Fills matching template colors exactly
    fill_sec1 = PatternFill(start_color="C9DAF8", end_color="C9DAF8", fill_type="solid")  # Soft Blue
    fill_sec2 = PatternFill(start_color="FCE5CD", end_color="FCE5CD", fill_type="solid")  # Soft Peach
    fill_white = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    fill_pass = PatternFill(start_color="B7E1CD", end_color="B7E1CD", fill_type="solid")  # Mint Green
    fill_fail = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")  # Bright Red
    fill_na = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")    # Soft Yellow
    fill_prog = PatternFill(start_color="FCE5CD", end_color="FCE5CD", fill_type="solid")  # In Progress Peach

    font_fail = Font(name="Times New Roman", size=11, bold=True, color="FFFFFF")
    font_pass = Font(name="Times New Roman", size=11, color="000000")
    font_na = Font(name="Times New Roman", size=11, color="000000")

    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    align_top = Alignment(horizontal="left", vertical="top", wrap_text=True)
    align_top_center = Alignment(horizontal="center", vertical="top", wrap_text=True)
    thin_border = Border(
        left=Side(style='thin', color='000000'),
        right=Side(style='thin', color='000000'),
        top=Side(style='thin', color='000000'),
        bottom=Side(style='thin', color='000000')
    )

    # Clean existing data cells from row 11 downwards before writing new rows
    for r in range(11, template_max_r + 1):
        for c in range(1, 26):
            cell = target_ws.cell(r, c)
            cell.value = None
            cell.fill = fill_white
            cell.border = thin_border
            cell.font = font_case
            cell.alignment = align_top

    def apply_status_style(cell, val):
        val_str = str(val or "").strip()
        if val_str.lower() == "pass":
            cell.fill = fill_pass
            cell.font = font_pass
        elif val_str.lower() == "fail":
            cell.fill = fill_fail
            cell.font = font_fail
        elif val_str.lower() in ("n/a", "na"):
            cell.fill = fill_na
            cell.font = font_na
        elif val_str.lower() in ("in progress", "doing"):
            cell.fill = fill_prog
            cell.font = font_pass
        else:
            cell.fill = fill_white
            cell.font = font_case

    start_row = 11
    cur_row = start_row
    case_count = 0

    for item in rows:
        itype = item.get("type", "case")

        if itype == "section":
            # Section Level 1 row (Pastel Blue fill across all 21 columns)
            for c in range(1, 22):
                cell = target_ws.cell(cur_row, c)
                cell.fill = fill_sec1
                cell.border = thin_border
                cell.font = font_sec1
            target_ws.cell(cur_row, 2, item.get("text", "")).font = font_sec1
            target_ws.cell(cur_row, 2).alignment = align_left
            target_ws.row_dimensions[cur_row].height = 24
            cur_row += 1

        elif itype == "subsection":
            # Section Level 2 row (Pastel Peach fill across all 21 columns)
            for c in range(1, 22):
                cell = target_ws.cell(cur_row, c)
                cell.fill = fill_sec2
                cell.border = thin_border
                cell.font = font_sec2
            target_ws.cell(cur_row, 3, item.get("text", "")).font = font_sec2
            target_ws.cell(cur_row, 3).alignment = align_left
            target_ws.row_dimensions[cur_row].height = 20
            cur_row += 1

        elif itype == "precondition":
            # Precondition row: Col B = "Tiền điều kiện:" in Blue Bold, Cols C:D = MERGED
            for c in range(1, 22):
                cell = target_ws.cell(cur_row, c)
                cell.border = thin_border
                cell.fill = fill_white
                cell.font = font_case

            target_ws.cell(cur_row, 2, "Tiền điều kiện:").font = font_precond_label
            target_ws.cell(cur_row, 2).alignment = align_left
            target_ws.cell(cur_row, 3, item.get("text", "")).font = font_case
            target_ws.cell(cur_row, 3).alignment = align_top

            # Explicitly merge C{cur_row}:D{cur_row}
            target_ws.merge_cells(start_row=cur_row, start_column=3, end_row=cur_row, end_column=4)
            # Re-apply border to merged cells so no border lines are lost
            target_ws.cell(cur_row, 3).border = thin_border
            target_ws.cell(cur_row, 4).border = thin_border

            # Auto-generated TC formula for Col A if formula-based
            target_ws.cell(cur_row, 1, f'=IF(F{cur_row}="","",("TC_"&$B$2&"_0"&ROW()-10-COUNTBLANK($F$11:F{cur_row})))')
            target_ws.cell(cur_row, 1).alignment = align_top
            target_ws.cell(cur_row, 1).font = font_case

            target_ws.row_dimensions[cur_row].height = 28
            cur_row += 1

        elif itype == "case":
            # Concrete test case row
            tc_id = item.get("testcase_id") or item.get("tc_id") or item.get("tc id")
            title = item.get("tên testcase") or item.get("test title") or item.get("tiêu đề") or ""
            precond = item.get("tiền điều kiện") or item.get("pre-condition") or item.get("precondition") or ""
            steps = item.get("các bước thực hiện") or item.get("test steps") or item.get("steps") or ""
            data_test = item.get("data test") or item.get("test data") or ""
            expected = item.get("kết quả mong đợi") or item.get("expected result") or item.get("expected") or ""
            depends = item.get("phụ thuộc testcase_id") or item.get("phụ thuộc") or ""
            severity = item.get("mức độ nghiêm trọng lỗi") or item.get("mức độ") or item.get("severity") or "Major"
            priority = item.get("độ ưu tiên") or item.get("priority") or "High"
            res1 = item.get("lần 1") or item.get("result") or ""
            res2 = item.get("lần 2") or ""
            bug1 = item.get("bug id") or item.get("bug") or ""
            notes1 = item.get("notes") or ""
            notes = item.get("ghi chú") or ""

            # Replace <br> with newlines
            steps = re.sub(r'<br\s*/?>', '\n', steps, flags=re.IGNORECASE)
            expected = re.sub(r'<br\s*/?>', '\n', expected, flags=re.IGNORECASE)
            precond = re.sub(r'<br\s*/?>', '\n', precond, flags=re.IGNORECASE)

            # Col 1: Formula if tc_id is not fixed
            if tc_id and not tc_id.startswith("TC_AUTO"):
                target_ws.cell(cur_row, 1, tc_id)
            else:
                target_ws.cell(cur_row, 1, f'=IF(F{cur_row}="","",("TC_"&$B$2&"_0"&ROW()-10-COUNTBLANK($F$11:F{cur_row})))')
            target_ws.cell(cur_row, 1).alignment = align_top

            # Col 2-6: Content
            target_ws.cell(cur_row, 2, title).alignment = align_top
            target_ws.cell(cur_row, 3, precond).alignment = align_top
            target_ws.cell(cur_row, 4, steps).alignment = align_top
            target_ws.cell(cur_row, 5, data_test).alignment = align_top
            target_ws.cell(cur_row, 6, expected).alignment = align_top

            # Col 7-9: Metadata
            target_ws.cell(cur_row, 7, depends).alignment = align_top
            target_ws.cell(cur_row, 8, severity).alignment = align_top_center
            target_ws.cell(cur_row, 9, priority).alignment = align_top

            # Execution round 1 (Cols 10-14) - Unexecuted test cases remain pristine/blank
            c10 = target_ws.cell(cur_row, 10, res1 if res1 else None)
            c10.alignment = align_top_center
            if res1:
                apply_status_style(c10, res1)

            target_ws.cell(cur_row, 11, f'=IF(OR(J{cur_row}="Pass", J{cur_row}="Fail"), $B$5, "")').alignment = align_top_center
            target_ws.cell(cur_row, 12, f'=IF(OR(J{cur_row}="", J{cur_row}="N/A"), "", IF(OR(L{cur_row}="", L{cur_row}=0), TODAY(), L{cur_row}))').alignment = align_top_center
            target_ws.cell(cur_row, 13, bug1).alignment = align_top_center
            target_ws.cell(cur_row, 14, notes1).alignment = align_top

            # Execution round 2 (Cols 15-19)
            c15 = target_ws.cell(cur_row, 15, res2 if res2 else None)
            c15.alignment = align_top_center
            if res2:
                apply_status_style(c15, res2)

            target_ws.cell(cur_row, 16, f'=IF(OR(O{cur_row}="Pass", O{cur_row}="Fail"), $B$5, "")').alignment = align_top_center
            target_ws.cell(cur_row, 17, f'=IF(OR(O{cur_row}="", O{cur_row}="N/A"), "", IF(OR(Q{cur_row}="", Q{cur_row}=0), TODAY(), Q{cur_row}))').alignment = align_top_center
            target_ws.cell(cur_row, 18, "").alignment = align_top_center
            target_ws.cell(cur_row, 19, "").alignment = align_top

            # Col 20: Dynamic result formula & Col 21: Notes
            c20 = target_ws.cell(cur_row, 20, f'=IF(OR(J{cur_row}="N/A", O{cur_row}="Untested"), J{cur_row}, IF(COUNTA(J{cur_row},O{cur_row})=1, "In Progress", IF(OR(J{cur_row}="Fail", O{cur_row}="Fail"), "Fail", IF(AND(J{cur_row}="Pass", O{cur_row}="Pass"), "Pass", ""))))')
            c20.alignment = align_top_center
            if res1:
                apply_status_style(c20, res1)

            target_ws.cell(cur_row, 21, notes).alignment = align_top

            # Unconditionally enforce exact font, border, and background on ALL cells (Cols 1 to 21)
            for c in range(1, 22):
                cell = target_ws.cell(cur_row, c)
                if c == 8:
                    cell.font = font_case_bold
                else:
                    if not (c in (10, 15, 20) and cell.value and str(cell.value).strip().lower() == "fail"):
                        cell.font = font_case
                cell.border = thin_border
                if cell.fill.fill_type != 'solid':
                    cell.fill = fill_white

            # Height calculation
            lines_cnt = max(len(steps.splitlines()), len(expected.splitlines()), 1)
            target_ws.row_dimensions[cur_row].height = max(26, lines_cnt * 18)

            cur_row += 1
            case_count += 1

    last_row = max(cur_row - 1, start_row)

    # Cleanly remove any trailing rows from bottom up if template had more rows
    if template_max_r > last_row:
        target_ws.delete_rows(last_row + 1, template_max_r - last_row)

    # Dynamic formula update in summary header (rows 3-7) to match exact case rows
    target_ws["I3"] = f'=COUNTIFS($I$11:$I${last_row},I$2,$T$11:$T${last_row},$H3)'
    target_ws["J3"] = f'=COUNTIFS($I$11:$I${last_row},$J$2,$T$11:$T${last_row},$H3)'
    target_ws["K3"] = f'=COUNTIFS($I$11:$I${last_row},$K$2,$T$11:$T${last_row},$H3)'

    target_ws["I4"] = f'=COUNTIFS($I$11:$I${last_row},$I$2,$T$11:$T${last_row},$H4)'
    target_ws["J4"] = f'=COUNTIFS($I$11:$I${last_row},$J$2,$T$11:$T${last_row},$H4)'
    target_ws["K4"] = f'=COUNTIFS($I$11:$I${last_row},$K$2,$T$11:$T${last_row},$H4)'

    target_ws["I5"] = f'=COUNTIFS($I$11:$I${last_row},$I$2,$T$11:$T${last_row},$H5)'
    target_ws["J5"] = f'=COUNTIFS($I$11:$I${last_row},$J$2,$T$11:$T${last_row},$H5)'
    target_ws["K5"] = f'=COUNTIFS($I$11:$I${last_row},$K$2,$T$11:$T${last_row},$H5)'

    target_ws["I6"] = f'=COUNTIFS($I$11:$I${last_row},$I$2,$T$11:$T${last_row},$H6)'
    target_ws["J6"] = f'=COUNTIFS($I$11:$I${last_row},$J$2,$T$11:$T${last_row},$H6)'
    target_ws["K6"] = f'=COUNTIFS($I$11:$I${last_row},$K$2,$T$11:$T${last_row},$H6)'

    target_ws["Q3"] = f'=COUNTIF($I$11:$I${last_row},Q2)'
    target_ws["R3"] = f'=COUNTIF($I$11:$I${last_row},R2)'
    target_ws["S3"] = f'=COUNTIF($I$11:$I${last_row},S2)'

    if not keep_other_sheets:
        for sname in list(wb.sheetnames):
            if sname != new_sheet_name:
                del wb[sname]

    # Save workbook
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    wb.save(output_path)
    return output_path


_DEFAULT_TRACE_LABELS: Dict[str, List[str]] = {
    "case_id": ["Testcase_ID", "TC_ID", "Case_ID", "Automation Case ID", "CaseKey"],
    "requirement_id": ["Requirement_ID", "Req_ID", "Requirement Refs", "ReqLinks"],
    "document_version": ["Document_Version", "Doc_Version", "Doc Revisions", "Revision"],
    "source_anchor": ["Source_Anchor", "Source Anchors", "Anchor"],
    "disposition": ["Disposition", "Trace_Disposition", "Trace Disposition"],
    "candidate_build": ["Candidate_Build", "Candidate Build", "Build_ID"],
}
_WRITTEN_TRACE_ROLES = ("requirement_id", "document_version", "source_anchor", "disposition", "candidate_build")


def resolve_template_profile(
    profile_config: Optional[Dict[str, Any]] = None,
    cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Resolves generic workbook sheet names and header label aliases without client hardcoding."""
    labels: Dict[str, List[str]] = {k: list(v) for k, v in _DEFAULT_TRACE_LABELS.items()}
    merged: Dict[str, Any] = {"detail_sheet": None, "summary_sheet": None, "header_row": None, "column_labels": labels}
    sources = []
    if isinstance(cfg, dict) and isinstance(cfg.get("trace_profile"), dict):
        sources.append(cfg["trace_profile"])
    if isinstance(profile_config, dict):
        sources.append(profile_config)
    for src in sources:
        for key in ("detail_sheet", "summary_sheet", "header_row"):
            if src.get(key) is not None:
                merged[key] = src[key]
        raw_labels = src.get("column_labels")
        if isinstance(raw_labels, dict):
            for role, aliases in raw_labels.items():
                alias_list = [aliases] if isinstance(aliases, str) else list(aliases or [])
                if alias_list:
                    labels[role] = alias_list
    return merged


def find_header_columns(
    ws: Any,
    label_map: Dict[str, Any],
    header_row: Optional[int] = None,
) -> tuple:
    """Finds header row and canonical role -> 1-based column index mapping by label."""
    alias_to_role: Dict[str, str] = {}
    for role, aliases in label_map.items():
        for alias in ([aliases] if isinstance(aliases, str) else aliases):
            norm = str(alias).strip().lower()
            if norm:
                alias_to_role[norm] = role

    r_start = int(header_row) if header_row else 1
    r_end = int(header_row) if header_row else ws.max_row
    for r, row_vals in enumerate(
        ws.iter_rows(min_row=r_start, max_row=r_end, values_only=True),
        start=r_start,
    ):
        found: Dict[str, int] = {}
        for c, val in enumerate(row_vals, start=1):
            if isinstance(val, str):
                role = alias_to_role.get(val.strip().lower())
                if role and role not in found:
                    found[role] = c
        if "case_id" in found:
            return r, found
    raise ValueError(f"Could not resolve required header column 'case_id' ({label_map.get('case_id')}) in sheet '{ws.title}'.")


def _extract_case_trace_index(trace_matrix: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    candidate_build = str(trace_matrix.get("candidate_build") or "")
    has_case_outcomes = trace_matrix.get("case_outcomes") is not None
    case_outcomes = dict(trace_matrix.get("case_outcomes") or {})
    acc: Dict[str, Dict[str, Any]] = {}
    for row in trace_matrix.get("rows") or []:
        req_id = str(row.get("requirement_id") or "")
        doc_id = str(row.get("document_id") or "")
        doc_ver = f"{doc_id}:{row.get('document_version', '')}".strip(":")
        raw_anchor = str(row.get("source_anchor") or "")
        anchor = f"{doc_id}#{raw_anchor}" if doc_id and raw_anchor else raw_anchor
        executed = bool(row.get("executed_on_candidate"))
        passed = bool(row.get("passed_on_candidate"))
        for cid in row.get("linked_cases") or []:
            entry = acc.setdefault(cid, {"reqs": [], "vers": [], "anchors": [], "executed": False, "all_passed": True})
            if req_id and req_id not in entry["reqs"]:
                entry["reqs"].append(req_id)
            if doc_ver and doc_ver not in entry["vers"]:
                entry["vers"].append(doc_ver)
            if anchor and anchor not in entry["anchors"]:
                entry["anchors"].append(anchor)
            entry["executed"] = entry["executed"] or executed
            entry["all_passed"] = entry["all_passed"] and passed

    out: Dict[str, Dict[str, str]] = {}
    for cid, info in acc.items():
        if has_case_outcomes:
            explicit = case_outcomes.get(cid)
            disp = str(explicit) if explicit in ("passed", "failed", "unrun") else "unrun"
        elif not info["executed"]:
            disp = "unrun"
        else:
            disp = "passed" if info["all_passed"] else "failed"
        out[cid] = {
            "requirement_id": ", ".join(info["reqs"]),
            "document_version": ", ".join(info["vers"]),
            "source_anchor": ", ".join(info["anchors"]),
            "disposition": disp,
            "candidate_build": candidate_build,
        }
    return out


def _compare_sheet_cells(
    sws: Any,
    ows: Any,
    skip_after_row: Optional[int] = None,
    allowed_cols: Optional[set] = None,
) -> tuple:
    """Checks non-trace cells for unchanged formulas and unrelated cell values."""
    formulas_ok = True
    unrelated_ok = True
    cols = allowed_cols or set()
    for r in range(1, max(sws.max_row, ows.max_row) + 1):
        for c in range(1, max(sws.max_column, ows.max_column) + 1):
            if skip_after_row is not None and r > skip_after_row and c in cols:
                continue
            sval = sws.cell(r, c).value
            oval = ows.cell(r, c).value
            if isinstance(sval, str) and sval.startswith("="):
                formulas_ok = formulas_ok and (oval == sval)
            else:
                unrelated_ok = unrelated_ok and (oval == sval)
    return formulas_ok, unrelated_ok


def _collect_row_trace_mismatches(
    det_ws: Any,
    detail_name: str,
    row_idx: int,
    case_id: str,
    col_map: Dict[str, int],
    exp_rec: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Checks all mapped trace role columns on a single reopened worksheet row."""
    mismatches: List[Dict[str, Any]] = []
    for role in _WRITTEN_TRACE_ROLES:
        if role not in col_map or role not in exp_rec:
            continue
        col_idx = col_map[role]
        raw_exp = exp_rec[role]
        expected_val = "" if raw_exp is None else str(raw_exp).strip()
        raw_act = det_ws.cell(row_idx, col_idx).value
        actual_val = "" if raw_act is None else str(raw_act).strip()
        if actual_val != expected_val:
            mismatch = TraceCellMismatchDTO(
                sheet=detail_name,
                cell=f"{get_column_letter(col_idx)}{row_idx}",
                row=row_idx,
                case_id=case_id,
                role=role,
                expected=expected_val,
                actual=actual_val,
            )
            mismatches.append(asdict(mismatch))
    return mismatches


def compare_workbook_semantics(
    source_path: str,
    exported_path: str,
    profile: Optional[Dict[str, Any]] = None,
    expected_dispositions: Optional[Dict[str, str]] = None,
    expected_counts: Optional[Dict[str, int]] = None,
    expected_case_traces: Optional[Dict[str, Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Reopens exported workbook and verifies sheet order, formulas, merges, unrelated cells, and totals."""
    eff_profile = resolve_template_profile(profile)
    src_wb = openpyxl.load_workbook(source_path, data_only=False)
    out_wb = openpyxl.load_workbook(exported_path, data_only=False)

    sheet_order_preserved = list(src_wb.sheetnames) == list(out_wb.sheetnames)
    formulas_preserved = True
    merged_cells_preserved = True
    unrelated_cells_preserved = True

    detail_name = eff_profile.get("detail_sheet") or src_wb.sheetnames[0]
    if detail_name not in out_wb.sheetnames:
        raise ValueError(f"Detail sheet '{detail_name}' missing from reopened workbook.")

    det_ws = out_wb[detail_name]
    hdr_row, col_map = find_header_columns(det_ws, eff_profile["column_labels"], eff_profile.get("header_row"))
    allowed_cols = {col_map[role] for role in _WRITTEN_TRACE_ROLES if role in col_map}

    for sname in src_wb.sheetnames:
        if sname not in out_wb.sheetnames:
            continue
        sws = src_wb[sname]
        ows = out_wb[sname]
        src_merges = {str(r) for r in sws.merged_cells.ranges}
        out_merges = {str(r) for r in ows.merged_cells.ranges}
        merged_cells_preserved = merged_cells_preserved and src_merges.issubset(out_merges)
        f_ok, u_ok = _compare_sheet_cells(
            sws,
            ows,
            skip_after_row=hdr_row if sname == detail_name else None,
            allowed_cols=allowed_cols if sname == detail_name else None,
        )
        formulas_preserved = formulas_preserved and f_ok
        unrelated_cells_preserved = unrelated_cells_preserved and u_ok

    counts: Dict[str, int] = {}
    actual_case_count = 0
    disp_match = True
    cell_mismatches: List[Dict[str, Any]] = []
    case_col = col_map["case_id"]
    disp_col = col_map.get("disposition")
    for r in range(hdr_row + 1, det_ws.max_row + 1):
        cid_val = det_ws.cell(r, case_col).value
        if cid_val is None or not str(cid_val).strip():
            continue
        cid = str(cid_val).strip()
        actual_case_count += 1
        dval = str(det_ws.cell(r, disp_col).value or "").strip() if disp_col else ""
        if not dval:
            disp_match = False
        counts[dval] = counts.get(dval, 0) + 1
        if expected_dispositions and expected_dispositions.get(cid) != dval:
            disp_match = False
        if expected_case_traces and cid in expected_case_traces:
            cell_mismatches.extend(
                _collect_row_trace_mismatches(
                    det_ws,
                    detail_name,
                    r,
                    cid,
                    col_map,
                    expected_case_traces[cid],
                )
            )

    reconciled = (
        disp_match
        and len(cell_mismatches) == 0
        and sum(counts.values()) == actual_case_count
        and (expected_counts is None or counts == expected_counts)
    )
    passed = (
        sheet_order_preserved
        and formulas_preserved
        and merged_cells_preserved
        and unrelated_cells_preserved
        and reconciled
    )
    return {
        "passed": passed,
        "sheet_order_preserved": sheet_order_preserved,
        "formulas_preserved": formulas_preserved,
        "merged_cells_preserved": merged_cells_preserved,
        "unrelated_cells_preserved": unrelated_cells_preserved,
        "reconciled": reconciled,
        "case_count": actual_case_count,
        "disposition_counts": counts,
        "cell_mismatches": cell_mismatches,
    }


def export_versioned_trace_workbook(
    template_path: str,
    output_path: str,
    trace_matrix: Dict[str, Any],
    profile: Optional[Dict[str, Any]] = None,
    compare_after_reopen: bool = True,
) -> Dict[str, Any]:
    """Exports versioned requirement trace dispositions into a template workbook and compares after reopen."""
    if not OPENPYXL_AVAILABLE:
        raise RuntimeError("openpyxl is required for template-driven Excel export. Run: pip install openpyxl")
    if not os.path.isfile(template_path):
        raise FileNotFoundError(f"Template Excel file not found: {template_path}")

    eff_profile = resolve_template_profile(profile)
    wb = openpyxl.load_workbook(template_path, data_only=False)
    detail_sheet = eff_profile.get("detail_sheet") or wb.sheetnames[0]
    if detail_sheet not in wb.sheetnames:
        raise ValueError(f"Detail sheet '{detail_sheet}' not found in workbook '{template_path}'.")

    ws = wb[detail_sheet]
    hdr_row, col_map = find_header_columns(ws, eff_profile["column_labels"], eff_profile.get("header_row"))
    case_index = _extract_case_trace_index(trace_matrix)
    candidate_build = str(trace_matrix.get("candidate_build") or "")

    counts: Dict[str, int] = {}
    expected_dispositions: Dict[str, str] = {}
    expected_case_traces: Dict[str, Dict[str, str]] = {}
    case_count = 0
    case_col = col_map["case_id"]
    for r in range(hdr_row + 1, ws.max_row + 1):
        cid_val = ws.cell(r, case_col).value
        if cid_val is None or not str(cid_val).strip():
            continue
        cid = str(cid_val).strip()
        case_count += 1
        rec = case_index.get(cid)
        if rec is None:
            rec = {
                "requirement_id": "",
                "document_version": "",
                "source_anchor": "",
                "disposition": "unmapped",
                "candidate_build": candidate_build,
            }
        for role in _WRITTEN_TRACE_ROLES:
            if role in col_map:
                cell = ws.cell(r, col_map[role])
                if not (isinstance(cell.value, str) and cell.value.startswith("=")):
                    cell.value = rec[role]
        disp = rec["disposition"]
        counts[disp] = counts.get(disp, 0) + 1
        expected_dispositions[cid] = disp
        expected_case_traces[cid] = dict(rec)

    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    wb.save(output_path)

    comparison = None
    if compare_after_reopen:
        comparison = compare_workbook_semantics(
            source_path=template_path,
            exported_path=output_path,
            profile=eff_profile,
            expected_dispositions=expected_dispositions,
            expected_counts=counts,
            expected_case_traces=expected_case_traces,
        )
    return {
        "output_path": output_path,
        "detail_sheet": detail_sheet,
        "candidate_build": candidate_build,
        "case_count": case_count,
        "disposition_counts": counts,
        "comparison": comparison,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Template-driven Excel test case exporter for Synapse Hub.")
    parser.add_argument("input_file", nargs="?", help="Path to markdown test cases file")
    parser.add_argument("-o", "--output", help="Output .xlsx file path")
    parser.add_argument("-t", "--template", help="Path to corporate template Excel workbook")
    parser.add_argument("-s", "--sample-sheet", default=None, help="Sample sheet name to clone (defaults to .synapse.json or first sheet)")
    parser.add_argument("--sheet-name", help="Target worksheet title")
    parser.add_argument("--module-code", default="MODULE", help="Module Code identifier")
    parser.add_argument("--module-name", default="Test Module", help="Module Name in Vietnamese/English")
    parser.add_argument("--author", default="QA Engineer", help="Author name")
    parser.add_argument("--tester", default="QA Engineer", help="Tester name")
    parser.add_argument("--standalone", action="store_true", help="Keep only the newly exported sheet, removing others")
    parser.add_argument("--trace-json", help="Path to JSON trace matrix for versioned workbook export")
    parser.add_argument("--template-profile", help="Path to JSON template profile configuration")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON summary")

    args = parser.parse_args()

    # Auto-load from .synapse.json if available
    cfg = find_project_config()
    template_path = args.template
    sample_sheet = args.sample_sheet
    author = args.author
    default_out = "test_cases_exported.xlsx"

    if cfg:
        tc_cfg = cfg.get("testcase_export", {})
        cfg_dir = cfg.get("_config_dir", "")
        if not template_path and tc_cfg.get("template_path"):
            template_path = os.path.normpath(os.path.join(cfg_dir, tc_cfg["template_path"]))
        if "sample_sheet" in tc_cfg:
            sample_sheet = tc_cfg["sample_sheet"]
        project_cfg = cfg.get("project")
        if isinstance(project_cfg, dict) and "author" in project_cfg:
            author = project_cfg["author"]
        if "default_output_dir" in tc_cfg:
            default_out = os.path.join(cfg_dir, tc_cfg["default_output_dir"], "test_cases_output.xlsx")

    output_path = args.output or default_out

    if args.trace_json:
        if not template_path or not os.path.isfile(template_path):
            print("Error: --template must point to an existing .xlsx workbook when using --trace-json.", file=sys.stderr)
            return 1
        with open(args.trace_json, "r", encoding="utf-8") as fh:
            trace_matrix = json.load(fh)
        profile_cfg = None
        if args.template_profile:
            with open(args.template_profile, "r", encoding="utf-8") as fh:
                profile_cfg = json.load(fh)
        eff_profile = resolve_template_profile(profile_cfg, cfg=cfg)
        result = export_versioned_trace_workbook(
            template_path=template_path,
            output_path=output_path,
            trace_matrix=trace_matrix,
            profile=eff_profile,
        )
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if (result.get("comparison") or {}).get("passed", True) else 1

    if not args.input_file or not args.input_file.strip():
        print("\n❌ Lỗi: Bạn chưa cung cấp đường dẫn file Markdown test cases.")
        print("\n💡 Hướng Dẫn Sử Dụng (Friendly Fix Hints):")
        print("   👉 Cú pháp cơ bản:")
        print("      agent-qa export-excel <duong_dan_file.md> [-o output.xlsx]")
        print("      python tools/template_excel_exporter.py <duong_dan_file.md> [tùy_chọn]")
        print("\n   👉 Ví dụ thực tế:")
        print("      agent-qa export-excel docs/TEST_CASES.md -o reports/test_cases.xlsx")
        print("      agent-qa export-excel docs/TEST_CASES.md -t templates/template.xlsx --sheet-name \"DangNhap\"")
        print("\n   👉 Khởi tạo file cấu hình .synapse.json cho dự án:")
        print("      agent-qa init-config\n")
        sys.exit(1)

    if not os.path.exists(args.input_file):
        print(f"\n❌ Lỗi: Không tìm thấy file Markdown: '{args.input_file}'")
        print("💡 Hãy kiểm tra lại đường dẫn file hoặc tạo file Markdown test cases trước khi xuất Excel.")
        print("   Ví dụ: agent-qa export-excel docs/TEST_CASES.md -o output.xlsx\n")
        sys.exit(1)

    with open(args.input_file, "r", encoding="utf-8") as f:
        content = f.read()

    rows = parse_testcases_from_markdown(content)
    if not template_path or not os.path.isfile(template_path):
        if template_path:
            print(f"Notice: Template file '{template_path}' not found or is not a valid file. Falling back to Hub default 12-column exporter.")
        else:
            print("Notice: No template file specified. Falling back to Hub default 12-column exporter.")
        import importlib.util
        md_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "md_to_xlsx.py")
        md_spec = importlib.util.spec_from_file_location("md_to_xlsx", md_path)
        md_to_xlsx = importlib.util.module_from_spec(md_spec)
        md_spec.loader.exec_module(md_to_xlsx)
        try:
            total = md_to_xlsx.convert_markdown_to_xlsx(args.input_file, output_path, sheet_name=args.sheet_name or "Test Cases")
            print(f"Successfully exported {total} test case(s) to '{output_path}' (Default Hub 12-Column Layout)")
            return 0
        except Exception as e:
            print(f"Error: Failed to export test cases: {e}", file=sys.stderr)
            return 1

    out = clone_and_export_template(
        rows=rows,
        output_path=output_path,
        template_path=template_path,
        sample_sheet_name=sample_sheet,
        target_sheet_name=args.sheet_name or sample_sheet,
        module_code=args.module_code,
        module_name=args.module_name,
        author=author,
        tester=args.tester,
        keep_other_sheets=not args.standalone
    )
    print(f"Successfully exported {len([r for r in rows if r.get('type') == 'case'])} test cases to '{out}' using template '{sample_sheet}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
