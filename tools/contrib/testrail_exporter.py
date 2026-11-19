#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""TestRail Test Case & Test Suite Exporter (CSV & XML).

Converts ISO/IEC/IEEE 29119-3 12-column Markdown test case specifications into
standard TestRail multi-step CSV (for TestRail CSV Import Wizard) and TestRail XML
(for TestRail Suite Import/Export schema).

100% Python Standard Library. Zero external dependencies.
"""

import argparse
import csv
import io
import os
import re
import sys
import xml.etree.ElementTree as ET

# Ensure UTF-8 stdio
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

TESTRAIL_CSV_HEADERS: list[str] = [
    "ID",
    "Title",
    "Section",
    "Template",
    "Type",
    "Priority",
    "Estimate",
    "References",
    "Preconditions",
    "Steps (Step)",
    "Steps (Data)",
    "Steps (Expected Result)",
    "Custom (RPN)",
    "Custom (Tags)",
]


class TestCase:
    """Represents a standardized test case parsed from Markdown tables."""

    def __init__(
        self,
        case_id: str = "",
        req_id: str = "",
        module: str = "",
        title: str = "",
        precondition: str = "",
        steps: str = "",
        test_data: str = "",
        expected_result: str = "",
        priority: str = "Medium",
        rpn: str = "",
        automatable: str = "",
        tags: str = "",
    ) -> None:
        self.case_id = case_id.strip()
        self.req_id = req_id.strip()
        self.module = module.strip()
        self.title = title.strip()
        self.precondition = precondition.strip()
        self.steps = steps.strip()
        self.test_data = test_data.strip()
        self.expected_result = expected_result.strip()
        self.priority = normalize_priority(priority)
        self.rpn = rpn.strip()
        self.automatable = automatable.strip()
        self.tags = tags.strip()


def normalize_priority(raw_priority: str) -> str:
    """Normalizes priority strings into standard TestRail values: Critical, High, Medium, Low."""
    if not raw_priority:
        return "Medium"
    val = raw_priority.strip().upper()
    if "P0" in val or "CRITICAL" in val or "BLOCKER" in val or "URGENT" in val:
        return "Critical"
    if "P1" in val or "HIGH" in val:
        return "High"
    if "P2" in val or "MEDIUM" in val or "NORMAL" in val:
        return "Medium"
    if "P3" in val or "P4" in val or "LOW" in val or "MINOR" in val or "TRIVIAL" in val:
        return "Low"
    return "Medium"


def parse_tags(raw_tags: str) -> list[str]:
    """Parses automation tags string into clean label strings stripped of '@' prefix."""
    if not raw_tags:
        return []
    items = [t.strip() for t in raw_tags.split(",") if t.strip()]
    labels: list[str] = []
    for item in items:
        clean = re.sub(r"^@+", "", item).strip()
        if clean:
            labels.append(clean)
    return labels


def is_automated_type(val: str) -> bool:
    """Detects whether Automatable / Type specifies automation."""
    if not val:
        return False
    return bool(re.search(r"\b(?:yes|auto|automated|api|ui|e2e)\b", val, re.IGNORECASE))


def split_steps_text(text: str) -> list[str]:
    """Splits step action or result strings on <br> tags or newlines, stripping leading bullets."""
    if not text:
        return []
    parts = re.split(r"<br\s*/?>|\r?\n", text, flags=re.IGNORECASE)
    cleaned: list[str] = []
    for p in parts:
        p_str = p.strip()
        if not p_str:
            continue
        p_clean = re.sub(r"^\s*(?:\d+[\.\)]|[-*•])\s*", "", p_str).strip()
        cleaned.append(p_clean if p_clean else p_str)
    return cleaned


def align_steps(
    steps_text: str, data_text: str, results_text: str
) -> tuple[list[str], list[str], list[str]]:
    """Aligns multi-step actions with their corresponding data and expected results.

    Handles asymmetric step vs result counts by distributing or reusing the final result.
    """
    actions = split_steps_text(steps_text)
    if not actions:
        actions = [""]
    n = len(actions)

    raw_results = split_steps_text(results_text)
    if not raw_results:
        results = [""] * n
    elif len(raw_results) == 1:
        results = [raw_results[0]] * n
    elif len(raw_results) == n:
        results = raw_results
    elif len(raw_results) < n:
        results = raw_results + [raw_results[-1]] * (n - len(raw_results))
    else:
        results = raw_results[: n - 1] + ["<br>".join(raw_results[n - 1 :])]

    raw_data = split_steps_text(data_text)
    if not raw_data:
        data_items = [""] * n
    elif len(raw_data) == 1:
        data_items = [raw_data[0]] * n
    elif len(raw_data) == n:
        data_items = raw_data
    elif len(raw_data) < n:
        data_items = raw_data + [""] * (n - len(raw_data))
    else:
        data_items = raw_data[: n - 1] + ["<br>".join(raw_data[n - 1 :])]

    return actions, data_items, results


def map_table_headers(headers: list[str]) -> dict[int, str]:
    """Maps table column indices to standardized 12-column canonical field names."""
    mapping: dict[int, str] = {}
    for idx, h in enumerate(headers):
        norm = re.sub(r"[\s_\-/()]+", "", h.lower())
        if norm in ("caseid", "tcid", "testid", "id") or "caseid" in norm or norm == "id":
            mapping[idx] = "case_id"
        elif norm in ("reqid", "requirementid", "references", "reference", "req", "ref") or "reqid" in norm:
            mapping[idx] = "req_id"
        elif norm in ("modulescreen", "module", "screen", "section", "component", "mod"):
            mapping[idx] = "module"
        elif norm in ("testtitleobjective", "testtitle", "title", "summary", "testname", "objective") or "title" in norm:
            mapping[idx] = "title"
        elif norm in ("precondition", "preconditions", "precond", "preconds") or "precond" in norm:
            mapping[idx] = "precondition"
        elif norm in ("teststeps11", "teststeps", "steps", "step", "action") or "steps" in norm:
            mapping[idx] = "steps"
        elif norm in ("testdata", "data"):
            mapping[idx] = "test_data"
        elif norm in ("expectedresult", "expectedresults", "expected", "result") or "expected" in norm or "result" in norm:
            mapping[idx] = "expected_result"
        elif norm in ("priorityseverity", "priority", "severity", "prio"):
            mapping[idx] = "priority"
        elif norm in ("riskscorerpn", "riskscore", "rpn") or "rpn" in norm:
            mapping[idx] = "rpn"
        elif norm in ("automatabletype", "automatable", "type", "autotype", "automationtype") or "automatable" in norm:
            mapping[idx] = "automatable"
        elif norm in ("automationtags", "tags", "labels", "tag", "label") or "tag" in norm or "label" in norm:
            mapping[idx] = "tags"

    if len(headers) == 12 and len(mapping) < 8:
        std_keys = [
            "case_id",
            "req_id",
            "module",
            "title",
            "precondition",
            "steps",
            "test_data",
            "expected_result",
            "priority",
            "rpn",
            "automatable",
            "tags",
        ]
        mapping = dict(enumerate(std_keys))

    return mapping


def parse_markdown_test_cases(content: str) -> list[TestCase]:
    """Parses all 12-column test case tables found within markdown content."""
    if not content or not content.strip():
        return []

    lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    test_cases: list[TestCase] = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("|") and line.endswith("|"):
            raw_headers = [c.strip() for c in line[1:-1].split("|")]
            if i + 1 < len(lines):
                sep_line = lines[i + 1].strip()
                if sep_line.startswith("|") and "---" in sep_line:
                    col_map = map_table_headers(raw_headers)
                    if "case_id" in col_map.values() and (
                        "title" in col_map.values()
                        or "steps" in col_map.values()
                        or len(raw_headers) >= 10
                    ):
                        j = i + 2
                        while j < len(lines):
                            row_line = lines[j].strip()
                            if not (row_line.startswith("|") and row_line.endswith("|")):
                                break
                            if "---" in row_line and set(row_line.replace("|", "").strip()).issubset({"-", ":", " "}):
                                break
                            cells = [
                                c.strip().replace(r"\|", "|")
                                for c in re.split(r"(?<!\\)\|", row_line[1:-1])
                            ]
                            if len(cells) < len(raw_headers):
                                cells.extend([""] * (len(raw_headers) - len(cells)))

                            row_data: dict[str, str] = {}
                            for col_idx, col_name in col_map.items():
                                if col_idx < len(cells):
                                    row_data[col_name] = cells[col_idx]
                                else:
                                    row_data[col_name] = ""

                            if any(row_data.values()):
                                tc = TestCase(
                                    case_id=row_data.get("case_id", ""),
                                    req_id=row_data.get("req_id", ""),
                                    module=row_data.get("module", ""),
                                    title=row_data.get("title", ""),
                                    precondition=row_data.get("precondition", ""),
                                    steps=row_data.get("steps", ""),
                                    test_data=row_data.get("test_data", ""),
                                    expected_result=row_data.get("expected_result", ""),
                                    priority=row_data.get("priority", "Medium"),
                                    rpn=row_data.get("rpn", ""),
                                    automatable=row_data.get("automatable", ""),
                                    tags=row_data.get("tags", ""),
                                )
                                if tc.case_id or tc.title or tc.steps:
                                    test_cases.append(tc)
                            j += 1
                        i = j
                        continue
        i += 1

    return test_cases


def export_to_testrail_csv(markdown_text: str) -> str:
    """Exports 12-column ISO 29119-3 Markdown test cases to standard TestRail CSV.

    Produces a multi-step CSV conforming to the official TestRail CSV Import Wizard.
    If input is empty or contains no test case tables, returns the 14 headers.
    """
    test_cases = parse_markdown_test_cases(markdown_text)
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    writer.writerow(TESTRAIL_CSV_HEADERS)

    for tc in test_cases:
        actions, data_items, results = align_steps(tc.steps, tc.test_data, tc.expected_result)
        tags_str = ", ".join(parse_tags(tc.tags))
        tr_type = "Automated" if is_automated_type(tc.automatable) else "Functional"

        for action, data, result in zip(actions, data_items, results):
            row = [
                tc.case_id,
                tc.title,
                tc.module,
                "Test Case (Steps)",
                tr_type,
                tc.priority,
                "180",
                tc.req_id,
                tc.precondition,
                action,
                data,
                result,
                tc.rpn,
                tags_str,
            ]
            writer.writerow(row)

    return output.getvalue()


def export_to_testrail_xml(markdown_text: str, suite_name: str = "Test Suite") -> str:
    """Exports 12-column ISO 29119-3 Markdown test cases to TestRail Test Suite XML schema.

    Generates valid XML with UTF-8 declaration, grouping test cases into sections
    by Module / Screen.
    """
    test_cases = parse_markdown_test_cases(markdown_text)

    root = ET.Element("suite")
    s_id = ET.SubElement(root, "id")
    s_id.text = "S1"
    s_name = ET.SubElement(root, "name")
    s_name.text = suite_name
    s_desc = ET.SubElement(root, "description")
    s_desc.text = "Exported from Synapse-Hub ISO 29119-3 Markdown Specification"
    sections_elem = ET.SubElement(root, "sections")

    sections_map: dict[str, list[TestCase]] = {}
    for tc in test_cases:
        sec_name = tc.module if tc.module else "General"
        sections_map.setdefault(sec_name, []).append(tc)

    for sec_name, cases in sections_map.items():
        sec_elem = ET.SubElement(sections_elem, "section")
        sec_n = ET.SubElement(sec_elem, "name")
        sec_n.text = sec_name
        sec_d = ET.SubElement(sec_elem, "description")
        sec_d.text = f"Test cases for {sec_name}"
        cases_elem = ET.SubElement(sec_elem, "cases")

        for tc in cases:
            case_elem = ET.SubElement(cases_elem, "case")

            c_id = ET.SubElement(case_elem, "id")
            c_id.text = tc.case_id

            c_title = ET.SubElement(case_elem, "title")
            c_title.text = tc.title

            c_tpl = ET.SubElement(case_elem, "template")
            c_tpl.text = "Test Case (Steps)"

            c_type = ET.SubElement(case_elem, "type")
            c_type.text = "Automated" if is_automated_type(tc.automatable) else "Functional"

            c_prio = ET.SubElement(case_elem, "priority")
            c_prio.text = tc.priority

            c_est = ET.SubElement(case_elem, "estimate")
            c_est.text = "180"

            c_refs = ET.SubElement(case_elem, "references")
            c_refs.text = tc.req_id

            custom_elem = ET.SubElement(case_elem, "custom")

            c_pre = ET.SubElement(custom_elem, "preconds")
            c_pre.text = tc.precondition

            steps_sep = ET.SubElement(custom_elem, "steps_separated")
            actions, data_items, results = align_steps(tc.steps, tc.test_data, tc.expected_result)
            for idx, (act, dt, res) in enumerate(zip(actions, data_items, results), start=1):
                step_elem = ET.SubElement(steps_sep, "step")
                s_idx = ET.SubElement(step_elem, "index")
                s_idx.text = str(idx)
                s_cnt = ET.SubElement(step_elem, "content")
                s_cnt.text = act
                s_info = ET.SubElement(step_elem, "additional_info")
                s_info.text = dt
                s_exp = ET.SubElement(step_elem, "expected")
                s_exp.text = res

            c_rpn = ET.SubElement(custom_elem, "rpn")
            c_rpn.text = tc.rpn

            c_auto = ET.SubElement(custom_elem, "automation_type")
            c_auto.text = tc.automatable

            c_tags = ET.SubElement(custom_elem, "tags")
            c_tags.text = ", ".join(parse_tags(tc.tags))

    ET.indent(root, space="  ")
    xml_body = ET.tostring(root, encoding="utf-8").decode("utf-8")
    xml_str = f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_body}\n'
    return xml_str


def export_testrail_csv_file(input_file: str, output_file: str | None = None) -> str:
    """Reads a markdown file, exports to TestRail CSV, and optionally saves to an output file."""
    with open(input_file, encoding="utf-8") as f:
        content = f.read()
    csv_str = export_to_testrail_csv(content)
    if output_file:
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(csv_str)
    return csv_str


def export_testrail_xml_file(
    input_file: str, output_file: str | None = None, suite_name: str = "Test Suite"
) -> str:
    """Reads a markdown file, exports to TestRail XML, and optionally saves to an output file."""
    with open(input_file, encoding="utf-8") as f:
        content = f.read()
    xml_str = export_to_testrail_xml(content, suite_name=suite_name)
    if output_file:
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(xml_str)
    return xml_str


def main(argv: list[str] | None = None) -> int:
    """CLI dispatcher for TestRail exporter."""
    parser = argparse.ArgumentParser(
        description="Synapse-Hub TestRail Test Case Exporter (CSV & XML)",
        prog="python -m tools.contrib.testrail_exporter",
    )
    parser.add_argument("positional_input", nargs="?", help="Path to input Markdown file")
    parser.add_argument("-i", "--input", dest="input_file", help="Path to input Markdown file")
    parser.add_argument("-o", "--output", dest="output_file", help="Path to output file")
    parser.add_argument(
        "-f",
        "--format",
        dest="format",
        choices=["csv", "xml"],
        default="csv",
        help="Export format: csv or xml (default: csv)",
    )
    parser.add_argument(
        "--suite-name",
        dest="suite_name",
        default="Test Suite",
        help="TestRail suite name for XML export (default: Test Suite)",
    )

    args = parser.parse_args(argv)

    target_input = args.input_file or args.positional_input
    if target_input:
        with open(target_input, encoding="utf-8") as f:
            content = f.read()
    elif not sys.stdin.isatty():
        content = sys.stdin.read()
    else:
        parser.print_help()
        return 1

    if args.format == "csv":
        result = export_to_testrail_csv(content)
        if args.output_file:
            os.makedirs(os.path.dirname(os.path.abspath(args.output_file)), exist_ok=True)
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"Exported TestRail CSV to: {args.output_file}")
        else:
            sys.stdout.write(result)
    else:
        xml_res = export_to_testrail_xml(content, suite_name=args.suite_name)
        if args.output_file:
            os.makedirs(os.path.dirname(os.path.abspath(args.output_file)), exist_ok=True)
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write(xml_res)
            print(f"Exported TestRail XML to: {args.output_file}")
        else:
            sys.stdout.write(xml_res)

    return 0


if __name__ == "__main__":
    sys.exit(main())
