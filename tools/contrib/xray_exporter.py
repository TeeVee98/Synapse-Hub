#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Jira Xray Test Case Exporter (CSV & JSON).

Converts ISO/IEC/IEEE 29119-3 12-column Markdown test case specifications into
standard Jira Xray CSV (for Test Case Importer) and Xray REST API JSON
(for Test Case & Test Execution bulk imports).

100% Python Standard Library. Zero external dependencies.
"""

import argparse
import csv
import io
import json
import os
import re
import sys
from typing import Any

# Ensure UTF-8 stdio
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

XRAY_CSV_HEADERS: list[str] = [
    "Test ID",
    "Summary",
    "Description",
    "Test Type",
    "Action",
    "Data",
    "Result",
    "Preconditions",
    "Priority",
    "Component",
    "Labels",
    "Link",
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
    """Normalizes priority strings into standard Jira values: Critical, High, Medium, Low."""
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


def export_to_xray_csv(markdown_text: str) -> str:
    """Exports 12-column ISO 29119-3 Markdown test cases to standard Jira Xray CSV.

    Produces a multi-row step structure conforming to the official Xray Test Case Importer.
    If input is empty or contains no test case tables, returns the 12 headers.
    """
    test_cases = parse_markdown_test_cases(markdown_text)
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    writer.writerow(XRAY_CSV_HEADERS)

    for tc in test_cases:
        actions, data_items, results = align_steps(tc.steps, tc.test_data, tc.expected_result)
        labels_str = ", ".join(parse_tags(tc.tags))
        test_type = "Automated" if is_automated_type(tc.automatable) else "Manual"

        for action, data, result in zip(actions, data_items, results):
            row = [
                tc.case_id,
                tc.title,
                tc.title,
                test_type,
                action,
                data,
                result,
                tc.precondition,
                tc.priority,
                tc.module,
                labels_str,
                tc.req_id,
            ]
            writer.writerow(row)

    return output.getvalue()


def export_to_xray_json(markdown_text: str, project_key: str = "SYN") -> list[dict[str, Any]]:
    """Exports 12-column ISO 29119-3 Markdown test cases to Jira Xray REST API JSON schema.

    Returns a list of dictionaries ready for Xray bulk import endpoint.
    If input has no test cases, returns [].
    """
    test_cases = parse_markdown_test_cases(markdown_text)
    if not test_cases:
        return []

    xray_cases: list[dict[str, Any]] = []
    for tc in test_cases:
        actions, data_items, results = align_steps(tc.steps, tc.test_data, tc.expected_result)
        labels = parse_tags(tc.tags)
        test_type = "Automated" if is_automated_type(tc.automatable) else "Manual"

        steps = [
            {"action": action, "data": data, "result": result}
            for action, data, result in zip(actions, data_items, results)
        ]

        fields: dict[str, Any] = {
            "summary": tc.title,
            "description": tc.title,
            "project": {"key": project_key},
            "priority": {"name": tc.priority},
            "labels": labels,
            "components": [{"name": tc.module}] if tc.module else [],
        }

        xray_fields: dict[str, Any] = {
            "preconditions": [{"definition": tc.precondition}] if tc.precondition else [],
            "requirements": [{"key": tc.req_id}] if tc.req_id else [],
        }

        case_dict: dict[str, Any] = {
            "testtype": test_type,
            "fields": fields,
            "steps": steps,
            "xrayFields": xray_fields,
        }
        xray_cases.append(case_dict)

    return xray_cases


def export_xray_csv_file(input_file: str, output_file: str | None = None) -> str:
    """Reads a markdown file, exports to Jira Xray CSV, and optionally saves to an output file."""
    with open(input_file, encoding="utf-8") as f:
        content = f.read()
    csv_str = export_to_xray_csv(content)
    if output_file:
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(csv_str)
    return csv_str


def export_xray_json_file(
    input_file: str, output_file: str | None = None, project_key: str = "SYN"
) -> list[dict[str, Any]]:
    """Reads a markdown file, exports to Jira Xray JSON, and optionally saves to an output file."""
    with open(input_file, encoding="utf-8") as f:
        content = f.read()
    json_data = export_to_xray_json(content, project_key=project_key)
    if output_file:
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
    return json_data


def main(argv: list[str] | None = None) -> int:
    """CLI dispatcher for Jira Xray exporter."""
    parser = argparse.ArgumentParser(
        description="Synapse-Hub Jira Xray Test Case Exporter (CSV & JSON)",
        prog="python -m tools.contrib.xray_exporter",
    )
    parser.add_argument("positional_input", nargs="?", help="Path to input Markdown file")
    parser.add_argument("-i", "--input", dest="input_file", help="Path to input Markdown file")
    parser.add_argument("-o", "--output", dest="output_file", help="Path to output file")
    parser.add_argument(
        "-f",
        "--format",
        dest="format",
        choices=["csv", "json"],
        default="csv",
        help="Export format: csv or json (default: csv)",
    )
    parser.add_argument(
        "--project-key",
        dest="project_key",
        default="SYN",
        help="Jira project key for Xray JSON export (default: SYN)",
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
        result = export_to_xray_csv(content)
        if args.output_file:
            os.makedirs(os.path.dirname(os.path.abspath(args.output_file)), exist_ok=True)
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"Exported Xray CSV to: {args.output_file}")
        else:
            sys.stdout.write(result)
    else:
        json_res = export_to_xray_json(content, project_key=args.project_key)
        json_str = json.dumps(json_res, ensure_ascii=False, indent=2)
        if args.output_file:
            os.makedirs(os.path.dirname(os.path.abspath(args.output_file)), exist_ok=True)
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write(json_str)
            print(f"Exported Xray JSON to: {args.output_file}")
        else:
            sys.stdout.write(json_str)

    return 0


if __name__ == "__main__":
    sys.exit(main())
