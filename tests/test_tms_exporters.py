#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Comprehensive 4-Tier Test Suite for Enterprise TMS Exporters (Jira Xray & TestRail).

Features tested:
  - Feature 5: Jira Xray CSV Exporter (export_to_xray_csv)
  - Feature 6: Jira Xray JSON Exporter (export_to_xray_json)
  - Feature 7: TestRail CSV Exporter (export_to_testrail_csv)
  - Feature 8: TestRail XML Exporter (export_to_testrail_xml)

Coverage Tiers:
  - Tier 1: Feature Coverage & Happy Paths (20 tests)
  - Tier 2: Boundary & Corner Cases (20 tests)
  - Tier 3: Pairwise Cross-Feature Interactions (4 tests)
  - Tier 4: Real-World Application Scenarios (3 tests)
Total: 47 Tests.
"""

import csv
import io
import json
import os
import xml.etree.ElementTree as ET

import pytest

# ==============================================================================
# Shared Fixtures & Dynamic Imports (Progressive Testability & Zero Crash)
# ==============================================================================


@pytest.fixture
def xray_exporter():
    """Dynamically loads tools.contrib.xray_exporter or skips gracefully if not yet implemented."""
    try:
        import tools.contrib.xray_exporter as mod

        return mod
    except ImportError:
        try:
            import xray_exporter as mod

            return mod
        except ImportError:
            pytest.skip("tools.contrib.xray_exporter not yet implemented")


@pytest.fixture
def testrail_exporter():
    """Dynamically loads tools.contrib.testrail_exporter or skips gracefully if not yet implemented."""
    try:
        import tools.contrib.testrail_exporter as mod

        return mod
    except ImportError:
        try:
            import testrail_exporter as mod

            return mod
        except ImportError:
            pytest.skip("tools.contrib.testrail_exporter not yet implemented")


# Sample canonical 12-column ISO 29119-3 Markdown fixture
SAMPLE_12_COL_MD = """
# Test Cases — User Management

| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_SINGLE_01 | REQ_DASH_01 | Dashboard | Verify simple page display | User is logged in | Open dashboard URL | N/A | Dashboard renders successfully | Medium | 12 | Yes / Automated | @Smoke |
| TC_MULTI_01 | REQ_AUTH_01 | Authentication | Verify user login flow with multi-step | Browser is open | 1. Enter username<br>2. Enter password<br>3. Click Submit | user: test@synapse.io<br>pass: Secret123! | 1. Username populated<br>2. Password masked<br>3. Logged in successfully | High | 48 | Yes / Automated | @Smoke, @Regression, @P0 |
"""


# ==============================================================================
# Tier 1: Feature Coverage (Equivalence-Class Happy Paths) — 20 Tests
# ==============================================================================


class TestTier1XrayCSV:
    """Tier 1: Feature 5 — Jira Xray CSV Exporter."""

    def test_xray_csv_export_headers(self, xray_exporter):
        """1. Verifies exact 12 headers in Xray CSV output."""
        csv_str = xray_exporter.export_to_xray_csv(SAMPLE_12_COL_MD)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        expected_headers = [
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
        assert [h.strip() for h in headers] == expected_headers
        assert len(headers) == 12

    def test_xray_csv_single_step_mapping(self, xray_exporter):
        """2. Validates 1-to-1 mapping of test ID, summary, preconditions, priority, component, labels, and single action/result."""
        single_case_md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_SINGLE_01 | REQ_DASH_01 | Dashboard | Verify simple page display | User is logged in | Open dashboard URL | N/A | Dashboard renders successfully | Medium | 12 | Yes / Automated | @Smoke |
"""
        csv_str = xray_exporter.export_to_xray_csv(single_case_md)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        row = next(reader)
        assert row[headers.index("Test ID")] == "TC_SINGLE_01"
        assert row[headers.index("Summary")] == "Verify simple page display"
        assert row[headers.index("Action")].strip() == "Open dashboard URL"
        assert row[headers.index("Result")].strip() == "Dashboard renders successfully"
        assert row[headers.index("Preconditions")].strip() == "User is logged in"
        assert row[headers.index("Component")].strip() == "Dashboard"
        assert "Smoke" in row[headers.index("Labels")]
        assert row[headers.index("Link")].strip() == "REQ_DASH_01"

    def test_xray_csv_multi_step_decomposition(self, xray_exporter):
        """3. Validates a 3-step test case decomposes into 3 sequential rows sharing the same Test ID."""
        multi_step_md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_MULTI_01 | REQ_AUTH_01 | Authentication | Verify user login flow | Browser open | 1. Enter username<br>2. Enter password<br>3. Click Submit | user: test@syn.io<br>pass: 123 | 1. Username populated<br>2. Password masked<br>3. Logged in successfully | High | 48 | Yes / Automated | @Smoke |
"""
        csv_str = xray_exporter.export_to_xray_csv(multi_step_md)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        rows = list(reader)
        assert len(rows) == 3
        test_id_idx = headers.index("Test ID")
        action_idx = headers.index("Action")
        result_idx = headers.index("Result")
        for r in rows:
            assert r[test_id_idx] == "TC_MULTI_01"
        assert "username" in rows[0][action_idx].lower()
        assert "Username populated" in rows[0][result_idx]
        assert "password" in rows[1][action_idx].lower()
        assert "Password masked" in rows[1][result_idx]
        assert "submit" in rows[2][action_idx].lower()
        assert "Logged in successfully" in rows[2][result_idx]

    def test_xray_csv_priority_normalization(self, xray_exporter):
        """4. Validates normalization of P0/P1/Critical/High/Medium/Low into Jira priority strings."""
        prio_md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_P0 | REQ_01 | Mod | Title P0 | None | Step 1 | Data | Result 1 | P0 | 100 | Yes | @Tag |
| TC_P1 | REQ_02 | Mod | Title P1 | None | Step 1 | Data | Result 1 | P1 | 80 | Yes | @Tag |
| TC_P2 | REQ_03 | Mod | Title P2 | None | Step 1 | Data | Result 1 | P2 | 40 | Yes | @Tag |
| TC_P3 | REQ_04 | Mod | Title P3 | None | Step 1 | Data | Result 1 | P3 | 10 | Yes | @Tag |
"""
        csv_str = xray_exporter.export_to_xray_csv(prio_md)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        rows = list(reader)
        assert len(rows) == 4
        prio_idx = headers.index("Priority")
        allowed_priorities = {"Critical", "High", "Medium", "Low"}
        for r in rows:
            assert r[prio_idx] in allowed_priorities
        assert rows[0][prio_idx] in ("Critical", "High")
        assert rows[3][prio_idx] == "Low"

    def test_xray_csv_requirement_link(self, xray_exporter):
        """5. Validates REQ_ID maps correctly to Link column."""
        req_md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_LINK_01 | REQ_AUTH_99 | Auth | Verify link | None | Step 1 | Data | Result | High | 50 | Yes | @Smoke |
"""
        csv_str = xray_exporter.export_to_xray_csv(req_md)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        row = next(reader)
        link_idx = headers.index("Link")
        assert row[link_idx].strip() == "REQ_AUTH_99"


class TestTier1XrayJSON:
    """Tier 1: Feature 6 — Jira Xray JSON Exporter."""

    def test_xray_json_export_structure(self, xray_exporter):
        """6. Verifies output is a list[dict] conforming to Xray REST API schema (fields, testtype, steps)."""
        res = xray_exporter.export_to_xray_json(SAMPLE_12_COL_MD)
        assert isinstance(res, list)
        assert len(res) == 2
        for tc in res:
            assert "testtype" in tc
            assert tc["testtype"] in ("Manual", "Automated")
            assert "fields" in tc
            assert isinstance(tc["fields"], dict)
            assert "summary" in tc["fields"]
            assert "project" in tc["fields"]
            assert "key" in tc["fields"]["project"]
            assert "steps" in tc
            assert isinstance(tc["steps"], list)

    def test_xray_json_project_key_parameter(self, xray_exporter):
        """7. Verifies custom project_key is injected into fields.project.key."""
        res = xray_exporter.export_to_xray_json(SAMPLE_12_COL_MD, project_key="SYNAPSE_QA")
        assert len(res) >= 1
        for tc in res:
            assert tc["fields"]["project"]["key"] == "SYNAPSE_QA"

    def test_xray_json_manual_steps_array_fidelity(self, xray_exporter):
        """8. Verifies numbered steps are parsed into individual step dicts with action, data, and result."""
        multi_step_md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_FID_01 | REQ_01 | Core | Verify fidelity | Precond | 1. Open home page<br>2. Fill credentials<br>3. Click sign in | User: admin<br>Pass: secret | 1. Page loaded<br>2. Form filled<br>3. Welcome banner shown | High | 36 | Yes | @Smoke |
"""
        res = xray_exporter.export_to_xray_json(multi_step_md)
        assert len(res) == 1
        steps = res[0]["steps"]
        assert len(steps) == 3
        for s in steps:
            assert "action" in s
            assert "result" in s
        assert "Open home page" in steps[0]["action"]
        assert "Page loaded" in steps[0]["result"]
        assert "Fill credentials" in steps[1]["action"]
        assert "Form filled" in steps[1]["result"]
        assert "Click sign in" in steps[2]["action"]
        assert "Welcome banner shown" in steps[2]["result"]

    def test_xray_json_priority_and_tags_mapping(self, xray_exporter):
        """9. Verifies priority and tags are cleanly mapped into fields.priority and fields.labels."""
        tag_md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_TAG_01 | REQ_01 | Mod | Tag test | None | Step 1 | Data | Result 1 | Critical | 100 | Yes | @Smoke, @Regression, @Security |
"""
        res = xray_exporter.export_to_xray_json(tag_md)
        assert len(res) == 1
        fields = res[0]["fields"]
        assert "priority" in fields
        assert fields["priority"]["name"] in ("Critical", "High")
        assert "labels" in fields
        assert isinstance(fields["labels"], list)
        assert "Smoke" in fields["labels"]
        assert "Regression" in fields["labels"]
        assert "Security" in fields["labels"]
        for label in fields["labels"]:
            assert not label.startswith("@")

    def test_xray_json_serializability(self, xray_exporter):
        """10. Verifies output passes json.dumps and json.loads without TypeError or character loss."""
        res = xray_exporter.export_to_xray_json(SAMPLE_12_COL_MD)
        json_str = json.dumps(res, ensure_ascii=False, indent=2)
        assert isinstance(json_str, str)
        reloaded = json.loads(json_str)
        assert reloaded == res
        assert len(json_str) > 100


class TestTier1TestRailCSV:
    """Tier 1: Feature 7 — TestRail CSV Exporter."""

    def test_testrail_csv_export_headers(self, testrail_exporter):
        """11. Verifies exact 14 headers in TestRail CSV output."""
        csv_str = testrail_exporter.export_to_testrail_csv(SAMPLE_12_COL_MD)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        expected_headers = [
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
        assert [h.strip() for h in headers] == expected_headers
        assert len(headers) == 14

    def test_testrail_csv_single_step_mapping(self, testrail_exporter):
        """12. Validates ID, Title, Section, Template, Type, Priority, Preconditions, Steps, RPN, Tags."""
        single_case_md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_TR_01 | REQ_DASH_01 | Dashboard | Verify simple page display | User logged in | Open dashboard URL | N/A | Dashboard renders successfully | Medium | 12 | Yes / Automated | @Smoke |
"""
        csv_str = testrail_exporter.export_to_testrail_csv(single_case_md)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        row = next(reader)
        assert row[headers.index("ID")] == "TC_TR_01"
        assert row[headers.index("Title")] == "Verify simple page display"
        assert row[headers.index("Section")] == "Dashboard"
        assert row[headers.index("Template")] == "Test Case (Steps)"
        assert row[headers.index("References")] == "REQ_DASH_01"
        assert row[headers.index("Steps (Step)")].strip() == "Open dashboard URL"
        assert row[headers.index("Steps (Expected Result)")].strip() == "Dashboard renders successfully"

    def test_testrail_csv_multi_step_decomposition(self, testrail_exporter):
        """13. Validates multi-step rows maintain sequential steps and separate Steps (Step) / Steps (Expected Result)."""
        multi_step_md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_TR_MULTI | REQ_01 | Auth | Multi step testrail | None | 1. Enter email<br>2. Enter password<br>3. Submit | email: a@b.com | 1. Email accepted<br>2. Pass accepted<br>3. Dashboard visible | High | 40 | Yes | @Smoke |
"""
        csv_str = testrail_exporter.export_to_testrail_csv(multi_step_md)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        rows = list(reader)
        assert len(rows) == 3
        step_col = headers.index("Steps (Step)")
        res_col = headers.index("Steps (Expected Result)")
        assert "email" in rows[0][step_col].lower()
        assert "Email accepted" in rows[0][res_col]
        assert "password" in rows[1][step_col].lower()
        assert "Pass accepted" in rows[1][res_col]
        assert "submit" in rows[2][step_col].lower()
        assert "Dashboard visible" in rows[2][res_col]

    def test_testrail_csv_custom_rpn_and_tags(self, testrail_exporter):
        """14. Validates custom RPN and tags mapping."""
        rpn_md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_RPN_01 | REQ_01 | Orders | Checkout order | None | Checkout | Cart full | Order placed | High | 72 | Yes | @Regression, @API |
"""
        csv_str = testrail_exporter.export_to_testrail_csv(rpn_md)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        row = next(reader)
        rpn_col = headers.index("Custom (RPN)")
        tags_col = headers.index("Custom (Tags)")
        assert row[rpn_col].strip() == "72"
        assert "Regression" in row[tags_col]
        assert "API" in row[tags_col]

    def test_testrail_csv_references_and_defaults(self, testrail_exporter):
        """15. Validates references (REQ_ID) and default Template and Type."""
        ref_md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_REF_01 | REQ-202 | Core | Reference check | None | Step | Data | Result | Medium | 10 | Yes | @Smoke |
"""
        csv_str = testrail_exporter.export_to_testrail_csv(ref_md)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        row = next(reader)
        assert row[headers.index("References")] == "REQ-202"
        assert row[headers.index("Template")] == "Test Case (Steps)"
        assert row[headers.index("Type")] in ("Automated", "Functional")
        assert len(row[headers.index("Estimate")]) > 0


class TestTier1TestRailXML:
    """Tier 1: Feature 8 — TestRail XML Exporter."""

    def test_testrail_xml_structure_and_parsing(self, testrail_exporter):
        """16. Validates XML structure parsing via xml.etree.ElementTree without error."""
        xml_str = testrail_exporter.export_to_testrail_xml(SAMPLE_12_COL_MD)
        assert isinstance(xml_str, str)
        root = ET.fromstring(xml_str)
        assert root.tag == "suite"
        assert root.find("sections") is not None

    def test_testrail_xml_section_case_hierarchy(self, testrail_exporter):
        """17. Validates <suite><sections><section><cases><case> hierarchy."""
        xml_str = testrail_exporter.export_to_testrail_xml(SAMPLE_12_COL_MD)
        root = ET.fromstring(xml_str)
        sections = root.findall("sections/section")
        assert len(sections) >= 1
        for s in sections:
            assert s.find("name") is not None
            assert len(s.find("name").text) > 0
            cases = s.findall("cases/case")
            assert len(cases) >= 1
            for c in cases:
                assert c.find("id") is not None
                assert c.find("title") is not None

    def test_testrail_xml_step_content_and_results(self, testrail_exporter):
        """18. Validates step content and expected results inside <custom><steps_separated><step>."""
        multi_step_md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_XML_STEPS | REQ_01 | Auth | Multi step xml | None | 1. Step Alpha<br>2. Step Beta | Data | 1. Alpha OK<br>2. Beta OK | High | 20 | Yes | @Smoke |
"""
        xml_str = testrail_exporter.export_to_testrail_xml(multi_step_md)
        root = ET.fromstring(xml_str)
        case = root.find(".//case")
        assert case is not None
        steps = case.findall(".//steps_separated/step")
        assert len(steps) == 2
        assert "Step Alpha" in steps[0].find("content").text
        assert "Alpha OK" in steps[0].find("expected").text
        assert "Step Beta" in steps[1].find("content").text
        assert "Beta OK" in steps[1].find("expected").text

    def test_testrail_xml_custom_fields_rpn_tags(self, testrail_exporter):
        """19. Validates <custom><rpn> and <custom><tags> in XML output."""
        md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_CUST_XML | REQ_99 | Sec | Custom fields XML | None | Run scan | None | Scan clean | Critical | 144 | Yes | @Security, @P0 |
"""
        xml_str = testrail_exporter.export_to_testrail_xml(md)
        root = ET.fromstring(xml_str)
        case = root.find(".//case")
        assert case is not None
        custom = case.find("custom")
        assert custom is not None
        rpn = custom.find("rpn")
        assert rpn is not None
        assert rpn.text.strip() == "144"
        tags = custom.find("tags")
        assert tags is not None
        assert "Security" in tags.text

    def test_testrail_xml_suite_name_parameter(self, testrail_exporter):
        """20. Validates custom suite_name parameterization."""
        xml_str = testrail_exporter.export_to_testrail_xml(SAMPLE_12_COL_MD, suite_name="Billing CRM Master Suite")
        root = ET.fromstring(xml_str)
        name = root.find("name")
        assert name is not None
        assert name.text == "Billing CRM Master Suite"


# ==============================================================================
# Tier 2: Boundary & Corner Cases — 20 Tests
# ==============================================================================


class TestTier2XrayCSVBoundaries:
    """Tier 2: Boundary Cases for Jira Xray CSV."""

    def test_xray_csv_missing_optional_fields(self, xray_exporter):
        """21. Tables missing Pre-condition, Data, or Tags default gracefully to empty strings."""
        md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_OPT_01 | | ModuleX | Title with missing optionals | | Click button | | Success | Medium | | | |
"""
        csv_str = xray_exporter.export_to_xray_csv(md)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        row = next(reader)
        assert row[headers.index("Test ID")] == "TC_OPT_01"
        assert row[headers.index("Summary")] == "Title with missing optionals"
        assert row[headers.index("Action")] == "Click button"
        assert row[headers.index("Result")] == "Success"

    def test_xray_csv_unconventional_bullet_points(self, xray_exporter):
        """22. Steps formatted with dashes or asterisks are decomposed properly."""
        md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_BULLET_01 | REQ_01 | Mod | Bullets | None | - Open settings<br>- Click profile<br>- Update avatar | None | * Settings opened<br>* Profile visible<br>* Avatar saved | Medium | 10 | Yes | @Smoke |
"""
        csv_str = xray_exporter.export_to_xray_csv(md)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        rows = list(reader)
        assert len(rows) == 3
        action_idx = headers.index("Action")
        assert "Open settings" in rows[0][action_idx]
        assert "Click profile" in rows[1][action_idx]
        assert "Update avatar" in rows[2][action_idx]

    def test_xray_csv_large_payload_cells(self, xray_exporter):
        """23. Large payload cells (5000 chars) preserved without truncation or row disruption."""
        large_payload = "X" * 5000
        md = f"""
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_PAYLOAD_01 | REQ_01 | Mod | Large payload | None | Send big request | {large_payload} | Response 200 OK | High | 50 | Yes | @Perf |
"""
        csv_str = xray_exporter.export_to_xray_csv(md)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        rows = list(reader)
        assert len(rows) == 1
        data_idx = headers.index("Data")
        assert len(rows[0][data_idx]) >= 5000

    def test_xray_csv_empty_table_input(self, xray_exporter):
        """24. Empty markdown or table with no data rows returns headers only without crash."""
        empty_md = "# Documentation\n\nNo test cases table present.\n"
        csv_str = xray_exporter.export_to_xray_csv(empty_md)
        reader = csv.reader(io.StringIO(csv_str))
        rows = list(reader)
        assert len(rows) == 1
        assert len(rows[0]) == 12

    def test_xray_csv_rfc4180_quotes_and_commas(self, xray_exporter):
        """25. Fields with commas, quotes, and newlines properly escaped per RFC 4180."""
        md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_RFC_01 | REQ_01 | Mod | Title with "Quotes" and commas, etc. | None | Click "Save, Continue & Next", then enter "John, Jr." | name: "John, Jr.", code: 123 | Output: "Success, item saved" | Medium | 10 | Yes | @Smoke |
"""
        csv_str = xray_exporter.export_to_xray_csv(md)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        rows = list(reader)
        assert len(rows) == 1
        assert len(rows[0]) == 12
        action_idx = headers.index("Action")
        assert 'Click "Save, Continue & Next", then enter "John, Jr."' in rows[0][action_idx]


class TestTier2XrayJSONBoundaries:
    """Tier 2: Boundary Cases for Jira Xray JSON."""

    def test_xray_json_unicode_and_vietnamese(self, xray_exporter):
        """26. Vietnamese characters with tones/diacritics preserved accurately."""
        vn_md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_VN_01 | REQ_AUTH | Xác thực tài khoản | Xác thực đăng nhập thành công với tài khoản quản trị | Đã tạo tài khoản | 1. Nhập email nguyễn_văn_a@doanhnghiệp.vn<br>2. Nhập mật khẩu bí mật | Mật khẩu: MậtKhẩu@123 | 1. Email được chấp nhận<br>2. Chuyển hướng bảng điều khiển | High | 30 | Yes | @ĐăngNhập, @Khói |
"""
        res = xray_exporter.export_to_xray_json(vn_md)
        assert len(res) == 1
        assert res[0]["fields"]["summary"] == "Xác thực đăng nhập thành công với tài khoản quản trị"
        assert "nguyễn_văn_a@doanhnghiệp.vn" in res[0]["steps"][0]["action"]
        assert "bảng điều khiển" in res[0]["steps"][1]["result"]

    def test_xray_json_special_characters_in_summary(self, xray_exporter):
        """27. Special characters, regex patterns, and code snippets preserved in summary and steps."""
        spec_md = r"""
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_SPEC_01 | REQ_01 | Mod | Check regex: ^[\w\.-]+@([\w-]+\.)+[\w-]{2,4}$ & <script>alert("XSS")</script> | None | Validate regex | regex: ^[\w\.-]+@ | Match verified | High | 20 | Yes | @Sec |
"""
        res = xray_exporter.export_to_xray_json(spec_md)
        assert len(res) == 1
        summary = res[0]["fields"]["summary"]
        assert r"^[\w\.-]+@([\w-]+\.)+[\w-]{2,4}$" in summary
        assert '<script>alert("XSS")</script>' in summary

    def test_xray_json_empty_markdown_returns_empty_list(self, xray_exporter):
        """28. Markdown with no test cases returns empty list []."""
        assert xray_exporter.export_to_xray_json("") == []
        assert xray_exporter.export_to_xray_json("# Just text without tables\n\nNo test cases.") == []

    def test_xray_json_missing_or_non_numeric_rpn(self, xray_exporter):
        """29. Missing or non-numeric RPN (N/A, TBD, -) handled gracefully without exception."""
        md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_RPN_STR | REQ_01 | Mod | Non numeric RPN | None | Step | Data | Result | Medium | N/A | Yes | @Tag |
| TC_RPN_EMPTY | REQ_02 | Mod | Empty RPN | None | Step | Data | Result | Medium | | Yes | @Tag |
"""
        res = xray_exporter.export_to_xray_json(md)
        assert len(res) == 2
        assert res[0]["fields"]["summary"] == "Non numeric RPN"
        assert res[1]["fields"]["summary"] == "Empty RPN"

    def test_xray_json_asymmetric_steps_and_results(self, xray_exporter):
        """30. 4 steps with 1 general expected result does not crash with IndexError."""
        md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_ASYMM_01 | REQ_01 | Mod | Asymmetric steps | None | 1. Step 1<br>2. Step 2<br>3. Step 3<br>4. Step 4 | Data | Single final result for all steps | Medium | 10 | Yes | @Smoke |
"""
        res = xray_exporter.export_to_xray_json(md)
        assert len(res) == 1
        steps = res[0]["steps"]
        assert len(steps) == 4
        for s in steps:
            assert "action" in s
            assert "result" in s


class TestTier2TestRailCSVBoundaries:
    """Tier 2: Boundary Cases for TestRail CSV."""

    def test_testrail_csv_commas_and_quotes_escaping(self, testrail_exporter):
        """31. Commas and quotes in step action and expected result escaped per CSV standards."""
        md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_TR_ESC | REQ_01 | UI | Test quotes "admin" and commas, foo, bar | None | Select "Option 1, 2, or 3" | input: "quoted value" | Verified: "Option 1, 2, or 3" active | Medium | 10 | Yes | @Smoke |
"""
        csv_str = testrail_exporter.export_to_testrail_csv(md)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        row = next(reader)
        assert len(row) == 14
        step_col = headers.index("Steps (Step)")
        res_col = headers.index("Steps (Expected Result)")
        assert 'Select "Option 1, 2, or 3"' in row[step_col]
        assert 'Verified: "Option 1, 2, or 3" active' in row[res_col]

    def test_testrail_csv_multiple_tags_formatting(self, testrail_exporter):
        """32. Multiple tags separated cleanly in Custom (Tags)."""
        md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_TAGS_01 | REQ_01 | Mod | Multiple tags | None | Step | Data | Result | Medium | 10 | Yes | @Smoke, @Regression, @P0, @Security |
"""
        csv_str = testrail_exporter.export_to_testrail_csv(md)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        row = next(reader)
        tags_val = row[headers.index("Custom (Tags)")]
        assert "Smoke" in tags_val
        assert "Regression" in tags_val
        assert "Security" in tags_val

    def test_testrail_csv_non_numeric_rpn_fallback(self, testrail_exporter):
        """33. Non-numeric RPN fallback handles strings cleanly without crash."""
        md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_RPN_FALL | REQ_01 | Mod | Fallback RPN | None | Step | Data | Result | Low | Unknown | Yes | @Smoke |
"""
        csv_str = testrail_exporter.export_to_testrail_csv(md)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        row = next(reader)
        rpn_val = row[headers.index("Custom (RPN)")]
        assert rpn_val in ("Unknown", "0", "")

    def test_testrail_csv_empty_precondition_dash_handling(self, testrail_exporter):
        """34. Preconditions containing -, None, Không, N/A handled cleanly."""
        md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_PRE_DASH | REQ_01 | Mod | Dash precond | - | Step | Data | Result | Low | 10 | Yes | @Smoke |
| TC_PRE_NONE | REQ_02 | Mod | None precond | Không | Step | Data | Result | Low | 10 | Yes | @Smoke |
"""
        csv_str = testrail_exporter.export_to_testrail_csv(md)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        rows = list(reader)
        assert len(rows) == 2
        pre_col = headers.index("Preconditions")
        assert rows[0][pre_col] in ("-", "", "None")
        assert rows[1][pre_col] in ("Không", "", "None")

    def test_testrail_csv_crlf_normalization(self, testrail_exporter):
        """35. Input containing mixed line breaks normalized cleanly in CSV."""
        crlf_md = (
            "| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | "
            "Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | "
            "Automatable / Type | Automation Tags |\r\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|\r\n"
            "| TC_CRLF_01 | REQ_01 | Mod | CRLF Title | None | 1. Step 1<br>2. Step 2 | Data | "
            "1. Res 1<br>2. Res 2 | Low | 10 | Yes | @Smoke |\r\n"
        )
        csv_str = testrail_exporter.export_to_testrail_csv(crlf_md)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        rows = list(reader)
        assert len(rows) == 2
        step_col = headers.index("Steps (Step)")
        assert "Step 1" in rows[0][step_col]
        assert "Step 2" in rows[1][step_col]


class TestTier2TestRailXMLBoundaries:
    """Tier 2: Boundary Cases for TestRail XML."""

    def test_testrail_xml_reserved_entities_escaped(self, testrail_exporter):
        """36. Special XML entities (&, <, >, \", ') properly escaped."""
        md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_ENT_01 | REQ_01 | Mod | Test & <Verify> "Double" 'Single' | None | Step with & and <tag> | Data | Result with & and > | High | 20 | Yes | @Smoke |
"""
        xml_str = testrail_exporter.export_to_testrail_xml(md)
        assert isinstance(xml_str, str)
        root = ET.fromstring(xml_str)
        case = root.find(".//case")
        assert case is not None
        title = case.find("title").text
        assert 'Test & <Verify> "Double" \'Single\'' == title

    def test_testrail_xml_html_and_code_snippets_in_steps(self, testrail_exporter):
        """37. HTML snippets inside steps handled safely in XML without parsing errors."""
        md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_HTML_01 | REQ_01 | Mod | HTML snippets | None | Enter <input type="hidden" name="token"> | `<script>alert(1)</script>` | Form submits without executing <script> | High | 30 | Yes | @Security |
"""
        xml_str = testrail_exporter.export_to_testrail_xml(md)
        root = ET.fromstring(xml_str)
        step = root.find(".//steps_separated/step")
        assert step is not None
        content = step.find("content").text
        assert '<input type="hidden" name="token">' in content

    def test_testrail_xml_empty_sections_resilience(self, testrail_exporter):
        """38. Empty markdown input generates valid minimal XML without crashing."""
        xml_str = testrail_exporter.export_to_testrail_xml("")
        root = ET.fromstring(xml_str)
        assert root.tag == "suite"
        assert root.find("sections") is not None

    def test_testrail_xml_deep_step_hierarchy(self, testrail_exporter):
        """39. Test case with 12 sequential steps produces corresponding <step> elements in exact order."""
        steps_12 = "<br>".join([f"{i}. Action step {i}" for i in range(1, 13)])
        results_12 = "<br>".join([f"{i}. Expected result {i}" for i in range(1, 13)])
        md = f"""
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_DEEP_01 | REQ_01 | Mod | 12 steps deep | None | {steps_12} | Data | {results_12} | High | 50 | Yes | @Smoke |
"""
        xml_str = testrail_exporter.export_to_testrail_xml(md)
        root = ET.fromstring(xml_str)
        steps = root.findall(".//steps_separated/step")
        assert len(steps) == 12
        for idx, s in enumerate(steps, start=1):
            assert int(s.find("index").text) == idx
            assert f"Action step {idx}" in s.find("content").text
            assert f"Expected result {idx}" in s.find("expected").text

    def test_testrail_xml_utf8_declaration_and_diacritics(self, testrail_exporter):
        """40. XML contains UTF-8 declaration and preserves Vietnamese diacritics."""
        md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_XML_VN | REQ_01 | Bán Hàng & Kho Bãi | Kiểm tra quản lý đơn đặt hàng trực tuyến | Đã đăng nhập | 1. Chọn sản phẩm<br>2. Xác nhận thanh toán | Sản phẩm A | 1. Thêm giỏ hàng thành công<br>2. Hóa đơn được tạo | High | 40 | Yes | @ĐơnHàng |
"""
        xml_str = testrail_exporter.export_to_testrail_xml(md)
        assert 'encoding="utf-8"' in xml_str.lower()
        root = ET.fromstring(xml_str.encode("utf-8"))
        section_name = root.find(".//section/name").text
        assert section_name == "Bán Hàng & Kho Bãi"
        case_title = root.find(".//case/title").text
        assert case_title == "Kiểm tra quản lý đơn đặt hàng trực tuyến"


# ==============================================================================
# Tier 3: Pairwise Cross-Feature Interactions — 4 Tests
# ==============================================================================


class TestTier3CrossFeaturePipelines:
    """Tier 3: Pairwise Interactions across Exporters."""

    def test_clean_suite_to_xray_csv_pipeline(self, xray_exporter):
        """41. Clean ISO-12 suite converted to Xray CSV pipeline verifies complete data fidelity and row counts."""
        clean_suite_md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_PL_01 | REQ_01 | Module A | Case 1 | Pre 1 | 1. Step 1<br>2. Step 2 | D1 | 1. R1<br>2. R2 | High | 20 | Yes | @Tag1 |
| TC_PL_02 | REQ_02 | Module B | Case 2 | Pre 2 | Single step | D2 | Single res | Medium | 10 | Yes | @Tag2 |
| TC_PL_03 | REQ_03 | Module B | Case 3 | Pre 3 | 1. S1<br>2. S2<br>3. S3 | D3 | 1. R1<br>2. R2<br>3. R3 | Low | 5 | Yes | @Tag3 |
"""
        csv_str = xray_exporter.export_to_xray_csv(clean_suite_md)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        rows = list(reader)
        assert len(rows) == 6
        test_id_idx = headers.index("Test ID")
        ids = [r[test_id_idx] for r in rows]
        assert ids.count("TC_PL_01") == 2
        assert ids.count("TC_PL_02") == 1
        assert ids.count("TC_PL_03") == 3

    def test_clean_suite_to_xray_json_pipeline(self, xray_exporter):
        """42. Clean ISO-12 suite converted to Xray JSON pipeline verifies schema validation and nested objects."""
        clean_suite_md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_PL_01 | REQ_01 | Module A | Case 1 | Pre 1 | 1. Step 1<br>2. Step 2 | D1 | 1. R1<br>2. R2 | High | 20 | Yes | @Tag1 |
| TC_PL_02 | REQ_02 | Module B | Case 2 | Pre 2 | Single step | D2 | Single res | Medium | 10 | Yes | @Tag2 |
| TC_PL_03 | REQ_03 | Module B | Case 3 | Pre 3 | 1. S1<br>2. S2<br>3. S3 | D3 | 1. R1<br>2. R2<br>3. R3 | Low | 5 | Yes | @Tag3 |
"""
        res = xray_exporter.export_to_xray_json(clean_suite_md)
        assert len(res) == 3
        assert len(res[0]["steps"]) == 2
        assert len(res[1]["steps"]) == 1
        assert len(res[2]["steps"]) == 3

    def test_clean_suite_to_testrail_csv_pipeline(self, testrail_exporter):
        """43. Clean ISO-12 suite converted to TestRail CSV pipeline verifies all 14 columns populated."""
        clean_suite_md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_PL_01 | REQ_01 | Module A | Case 1 | Pre 1 | 1. Step 1<br>2. Step 2 | D1 | 1. R1<br>2. R2 | High | 20 | Yes | @Tag1 |
| TC_PL_02 | REQ_02 | Module B | Case 2 | Pre 2 | Single step | D2 | Single res | Medium | 10 | Yes | @Tag2 |
| TC_PL_03 | REQ_03 | Module B | Case 3 | Pre 3 | 1. S1<br>2. S2<br>3. S3 | D3 | 1. R1<br>2. R2<br>3. R3 | Low | 5 | Yes | @Tag3 |
"""
        csv_str = testrail_exporter.export_to_testrail_csv(clean_suite_md)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)
        rows = list(reader)
        assert len(headers) == 14
        assert len(rows) == 6

    def test_dual_export_xray_json_and_testrail_xml_consistency(self, xray_exporter, testrail_exporter):
        """44. Dual export Xray JSON and TestRail XML consistency (strictly identical test case counts and case IDs)."""
        suite_md = """
| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_CONS_01 | REQ_01 | Auth | Consistency TC 1 | Pre 1 | Step 1 | D1 | R1 | High | 30 | Yes | @Smoke |
| TC_CONS_02 | REQ_02 | Billing | Consistency TC 2 | Pre 2 | Step 1 | D2 | R2 | Medium | 20 | Yes | @Regression |
| TC_CONS_03 | REQ_03 | Billing | Consistency TC 3 | Pre 3 | Step 1 | D3 | R3 | Low | 10 | Yes | @Regression |
"""
        xray_json = xray_exporter.export_to_xray_json(suite_md)
        testrail_xml = testrail_exporter.export_to_testrail_xml(suite_md)
        root = ET.fromstring(testrail_xml)
        cases_xml = root.findall(".//case")
        assert len(xray_json) == len(cases_xml) == 3
        xml_ids = {c.find("id").text.strip() for c in cases_xml}
        assert xml_ids == {"TC_CONS_01", "TC_CONS_02", "TC_CONS_03"}


# ==============================================================================
# Tier 4: Real-World Scenarios — 3 Tests
# ==============================================================================


class TestTier4RealWorldScenarios:
    """Tier 4: End-to-End Real World Scenarios."""

    def test_real_world_book_management_api_export(self, xray_exporter, testrail_exporter):
        """45. Book Management API real suite export to Xray CSV & TestRail CSV."""
        book_api_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "examples",
            "practices",
            "testcases",
            "api",
            "book_management_api_test_cases.md",
        )
        assert os.path.exists(book_api_path), f"File not found: {book_api_path}"
        with open(book_api_path, encoding="utf-8") as f:
            content = f.read()

        xray_csv = xray_exporter.export_to_xray_csv(content)
        tr_csv = testrail_exporter.export_to_testrail_csv(content)

        r_xray = csv.reader(io.StringIO(xray_csv))
        headers_xray = next(r_xray)
        rows_xray = list(r_xray)
        assert len(headers_xray) == 12
        assert len(rows_xray) >= 10

        r_tr = csv.reader(io.StringIO(tr_csv))
        headers_tr = next(r_tr)
        rows_tr = list(r_tr)
        assert len(headers_tr) == 14
        assert len(rows_tr) >= 10

        combined_rows = " ".join([" ".join(r) for r in rows_xray])
        assert any(term in combined_rows for term in ("/api/book", "GET", "POST", "Clean Code"))

    def test_real_world_enterprise_25_field_kyc_export(self, testrail_exporter):
        """46. Enterprise 25-Field KYC Form export to TestRail XML with deep hierarchy."""
        kyc_md = """
# Enterprise KYC & Compliance 25-Field Test Suite

| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_KYC_GEO | REQ_KYC_16 | Verification / Geo | Verify geo location precision | GPS enabled | 1. Request location<br>2. Submit coordinates | lat: 10.762622, lon: 106.660172 | 1. Coordinates captured<br>2. Within 50m radius | High | 72 | Yes | @Geo, @KYC |
| TC_KYC_SIG | REQ_KYC_17 | Verification / Signature | Verify digital signature canvas | Tablet active | 1. Draw signature on canvas<br>2. Save vector signature | base64: iVBORw0KGgoAAAANSUhEUg... | 1. Stroke rendered<br>2. SHA-256 hash generated | Critical | 144 | Yes | @Signature, @Compliance |
| TC_KYC_BIO | REQ_KYC_18 | Verification / Biometric | Verify biometric WebAuthn prompt | Device supported | 1. Trigger biometric check<br>2. Verify TouchID/FaceID | CredentialID: FIDO2_CRED_001 | 1. OS biometric modal shown<br>2. Challenge signed | Critical | 180 | Yes | @Biometric, @Security |
| TC_KYC_CAM | REQ_KYC_19 | Verification / Camera | Verify camera barcode and QR scanning | Camera permission | 1. Open scanner<br>2. Scan ISO 18004 QR code | QR: KYC_USER_TOKEN_9981 | 1. Camera preview active<br>2. Token decoded in < 500ms | High | 96 | Yes | @Camera, @QR |
| TC_KYC_FX | REQ_KYC_20 | Finance / Currency | Verify multi currency FX conversion | Exchange rate live | 1. Input foreign currency<br>2. Convert USD to VND | USD: 1500.50, Rate: 25450.00 | 1. Currency formatted<br>2. Result: 38,187,725 VND | High | 80 | Yes | @FX, @Finance |
| TC_KYC_CC | REQ_KYC_21 | Finance / Cards | Verify credit card Luhn check and mask | Form open | 1. Enter card number<br>2. Blur card field | Card: 4532 0150 9999 1234 | 1. Luhn algorithm valid<br>2. Masked: ****-****-****-1234 | Critical | 120 | Yes | @Cards, @PCI_DSS |
| TC_KYC_AUTO | REQ_KYC_22 | Form / Typeahead | Verify async autocomplete for nationality | Network active | 1. Type "Viet"<br>2. Wait 300ms debounce | Query: "Viet" | 1. Dropdown shows "Vietnam"<br>2. Country code VN selected | Medium | 36 | Yes | @Autocomplete |
| TC_KYC_CRON | REQ_KYC_23 | Scheduler / Cron | Verify cron recurrence schedule expression | Quartz scheduler | 1. Enter cron expression<br>2. Calculate next fire times | Cron: "0 0 12 * * ?" | 1. Parsed as daily at 12:00<br>2. Next 5 fire dates listed | Medium | 40 | Yes | @Cron |
| TC_KYC_CODE | REQ_KYC_24 | Editor / Code | Verify JSON formula editor syntax linter | Monaco editor | 1. Paste complex JSON rule<br>2. Validate syntax | {"rule": "if(A1>0, B1, 0)"} | 1. Editor highlights syntax<br>2. 0 parse errors displayed | Medium | 45 | Yes | @Editor |
| TC_KYC_GRID | REQ_KYC_25 | Grid / DataGrid | Verify inline editable data grid commit | Grid loaded | 1. Double click cell [2, 3]<br>2. Edit value and press Enter | NewValue: 99.99 | 1. Cell changes to edit mode<br>2. Value committed with dirty badge | Medium | 48 | Yes | @DataGrid |
"""
        xml_str = testrail_exporter.export_to_testrail_xml(kyc_md, suite_name="Enterprise 25-Field KYC Suite")
        root = ET.fromstring(xml_str)
        assert root.find("name").text == "Enterprise 25-Field KYC Suite"
        cases = root.findall(".//case")
        assert len(cases) == 10
        case_ids = [c.find("id").text.strip() for c in cases]
        assert "TC_KYC_GEO" in case_ids
        assert "TC_KYC_SIG" in case_ids
        assert "TC_KYC_BIO" in case_ids
        assert "TC_KYC_CAM" in case_ids
        assert "TC_KYC_FX" in case_ids
        assert "TC_KYC_CC" in case_ids
        assert "TC_KYC_AUTO" in case_ids
        assert "TC_KYC_CRON" in case_ids
        assert "TC_KYC_CODE" in case_ids
        assert "TC_KYC_GRID" in case_ids

        sig_case = [c for c in cases if c.find("id").text.strip() == "TC_KYC_SIG"][0]
        case_xml_text = ET.tostring(sig_case, encoding="unicode")
        assert "iVBORw0KGgoAAAANSUhEUg" in case_xml_text

    def test_real_world_dual_tms_roundtrip_unicode_vietnamese(self, xray_exporter, testrail_exporter):
        """47. Dual TMS roundtrip Unicode & Vietnamese export against JSON & XML parsers."""
        vn_suite_md = """
# Bộ Kiểm Thử Xác Thực Và Phân Quyền Quản Trị Viên

| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TC_VN_AUTH_01 | REQ_AUTH_01 | Quản Lý Người Dùng | Xác thực đăng nhập hệ thống với tài khoản quản trị viên cấp cao | Hệ thống hoạt động bình thường | 1. Mở trang quản trị<br>2. Nhập tài khoản: trần_thị_bích_hồng@côngty.vn<br>3. Bấm Đăng Nhập | Email: trần_thị_bích_hồng@côngty.vn<br>Mật khẩu: MậtKhẩuBảoMật#2026 | 1. Trang đăng nhập hiển thị đầy đủ<br>2. Thông tin hợp lệ<br>3. Chuyển hướng tới bảng điều khiển tổng | Critical | 160 | Yes | @XácThực, @QuảnTrị, @ƯuTiênCao |
| TC_VN_AUTH_02 | REQ_AUTH_02 | Phân Quyền Hệ Thống | Kiểm tra tính năng thu hồi quyền hạn nhân viên bán hàng | Tài khoản đã được cấp quyền | 1. Chọn nhân viên: Nguyễn Hoàng Long<br>2. Bấm Thu Hồi Quyền | Nhân viên: Nguyễn Hoàng Long | 1. Hộp thoại xác nhận hiển thị<br>2. Quyền truy cập bị khóa ngay lập tức | High | 90 | Yes | @PhânQuyền, @BảoMật |
"""
        xray_json = xray_exporter.export_to_xray_json(vn_suite_md)
        testrail_xml = testrail_exporter.export_to_testrail_xml(vn_suite_md, suite_name="Bộ Kiểm Thử Xác Thực")

        # Roundtrip JSON
        json_str = json.dumps(xray_json, ensure_ascii=False)
        assert "\ufffd" not in json_str
        reloaded_json = json.loads(json_str)
        assert reloaded_json[0]["fields"]["summary"] == "Xác thực đăng nhập hệ thống với tài khoản quản trị viên cấp cao"
        assert "trần_thị_bích_hồng@côngty.vn" in reloaded_json[0]["steps"][1]["action"]

        # Roundtrip XML
        assert "\ufffd" not in testrail_xml
        root = ET.fromstring(testrail_xml.encode("utf-8"))
        assert root.find("name").text == "Bộ Kiểm Thử Xác Thực"
        case_titles = [c.find("title").text for c in root.findall(".//case")]
        assert "Xác thực đăng nhập hệ thống với tài khoản quản trị viên cấp cao" in case_titles
        assert "Kiểm tra tính năng thu hồi quyền hạn nhân viên bán hàng" in case_titles
