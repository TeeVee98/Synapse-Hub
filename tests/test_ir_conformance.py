#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tests/test_ir_conformance.py — Universal IR Conformance & Cross-Framework Parity Tests
--------------------------------------------------------------------------------------
Validates:
  1. Universal IR Schema conformance against JSON Schema (schemas/universal_ir.schema.json).
  2. Golden Fixtures round-trip serialization fidelity.
  3. Polyglot code emission parity across all 4 canonical target frameworks:
     - Playwright TypeScript (playwright-ts)
     - Playwright Python (playwright-python)
     - Selenium Java (selenium-java)
     - Katalon Groovy (katalon-groovy)
"""

import os
import sys
import json
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
sys.path.insert(0, TOOLS_DIR)

from universal_ir import ProjectIR, CURRENT_SCHEMA_VERSION
from omni_emitter import OmniEmitter
from omni_parser import OmniParser


class TestUniversalIRConformance(unittest.TestCase):
    """Verifies Universal IR schema integrity and cross-framework code generation parity."""

    def setUp(self):
        self.fixtures_dir = os.path.join(REPO_ROOT, "tests", "fixtures", "golden_ir")
        self.schema_path = os.path.join(REPO_ROOT, "schemas", "universal_ir.schema.json")

    def test_schema_json_file_is_valid_json(self):
        self.assertTrue(os.path.exists(self.schema_path), f"JSON Schema file missing: {self.schema_path}")
        with open(self.schema_path, "r", encoding="utf-8") as f:
            schema_data = json.load(f)
        self.assertEqual(schema_data.get("title"), "Universal Testing Intermediate Representation (ProjectIR)")
        self.assertIn("properties", schema_data)
        self.assertIn("schema_version", schema_data["properties"])

    def test_golden_fixtures_exist_and_conform_to_ir(self):
        self.assertTrue(os.path.isdir(self.fixtures_dir), "Golden fixtures directory must exist")
        fixture_files = [f for f in os.listdir(self.fixtures_dir) if f.endswith(".json")]
        self.assertGreaterEqual(len(fixture_files), 2, "Must contain at least 2 golden fixtures")

        for f_name in fixture_files:
            f_path = os.path.join(self.fixtures_dir, f_name)
            with open(f_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Assert mandatory root properties
            self.assertIn("schema_version", data, f"{f_name} missing schema_version")
            self.assertEqual(data["schema_version"], CURRENT_SCHEMA_VERSION)
            self.assertIn("name", data, f"{f_name} missing name")
            self.assertIn("pages", data, f"{f_name} missing pages")
            self.assertIn("test_cases", data, f"{f_name} missing test_cases")

            # Load into ProjectIR
            project = ProjectIR.from_dict(data)
            self.assertEqual(project.schema_version, CURRENT_SCHEMA_VERSION)
            self.assertGreaterEqual(len(project.pages), 1, f"{f_name} must have at least 1 page")
            self.assertGreaterEqual(len(project.test_cases), 1, f"{f_name} must have at least 1 test case")

            # Round-trip check
            serialized = project.to_dict()
            restored = ProjectIR.from_dict(serialized)
            self.assertEqual(project.name, restored.name)
            self.assertEqual(len(project.pages), len(restored.pages))
            self.assertEqual(project.pages[0].name, restored.pages[0].name)
            self.assertEqual(len(project.pages[0].locators), len(restored.pages[0].locators))

    def test_cross_framework_emission_parity(self):
        """Verifies that OmniEmitter generates non-empty, idiomatic code for all 4 frameworks."""
        fixture_path = os.path.join(self.fixtures_dir, "login_flow.json")
        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        project = ProjectIR.from_dict(data)
        targets = ["playwright-ts", "playwright-python", "selenium-java", "katalon-groovy"]

        for target in targets:
            emitted = OmniEmitter.emit(project, target)
            self.assertIsInstance(emitted, dict, f"Emission for {target} must return a dict of files")
            self.assertGreaterEqual(len(emitted), 1, f"Emission for {target} must produce at least 1 file")

            # Verify Page Class file and Test Script file separation (Clean POM Flat Architecture)
            page_files = [f for f in emitted.keys() if "LoginPage" in f and ("pages" in f or "Page" in f)]
            self.assertGreaterEqual(len(page_files), 1, f"Page Class file missing for target {target}")

            page_code = emitted[page_files[0]]
            self.assertTrue("txtusername" in page_code.lower(), f"Locator txtUsername missing in {target} Page Class")
            self.assertIn("login", page_code, f"Method login missing in {target} Page Class")

            # Verify Test Script file exists and executes workflow
            test_files = [f for f in emitted.keys() if "tests/" in f or "Scripts/" in f or "Test" in f]
            self.assertGreaterEqual(len(test_files), 1, f"Test script file missing for target {target}")
            test_file = test_files[0]
            test_code = emitted[test_file]
            self.assertTrue("TC_AUTH_001" in test_file or "tc_auth_001" in test_file.lower() or "TC_AUTH_001" in test_code or "tc_auth_001" in test_code.lower(), f"Test case ID missing in {target} test script")

    def test_schema_matrix_conformance(self):
        """Validates all golden IR fixtures against JSON Schema structural invariants."""
        fixture_files = [f for f in os.listdir(self.fixtures_dir) if f.endswith(".json")]
        self.assertGreaterEqual(len(fixture_files), 2)

        ALLOWED_STRATEGIES = {"role", "label", "test_id", "text", "css", "xpath", "placeholder", "id", "name", "class_name", "unknown"}

        for f_name in fixture_files:
            f_path = os.path.join(self.fixtures_dir, f_name)
            with open(f_path, "r", encoding="utf-8") as f:
                doc = json.load(f)

            # 1. Root constraints
            self.assertIsInstance(doc, dict)
            self.assertIn("schema_version", doc)
            self.assertRegex(doc["schema_version"], r"^\d+\.\d+\.\d+$")
            self.assertIn("name", doc)
            self.assertIn("pages", doc)
            self.assertIn("test_cases", doc)
            self.assertIsInstance(doc["pages"], list)
            self.assertIsInstance(doc["test_cases"], list)

            # 2. Page & Locator constraints
            for page in doc["pages"]:
                self.assertIn("name", page)
                self.assertIn("locators", page)
                for loc in page.get("locators", []):
                    self.assertIn("name", loc)
                    self.assertIn("strategy", loc)
                    self.assertIn(loc["strategy"].lower(), ALLOWED_STRATEGIES)
                    self.assertIn("value", loc)

            # 3. Test case constraints
            for tc in doc["test_cases"]:
                self.assertIn("id", tc)
                self.assertIn("title", tc)
                self.assertIn("steps", tc)

    def test_roundtrip_two_way_conformance_all_frameworks(self):
        """
        Validates 2-way round-trip transpilation across all 4 canonical frameworks:
        IR -> OmniEmitter (TS/Py/Java/Groovy) -> OmniParser -> Restored IR.
        Verifies Page Classes, Locators, and Methods are preserved without loss.
        """
        fixture_path = os.path.join(self.fixtures_dir, "login_flow.json")
        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        project = ProjectIR.from_dict(data)
        targets = ["playwright-ts", "playwright-python", "selenium-java", "katalon-groovy"]
        orig_page = project.pages[0]
        expected_locator_names = {loc.name for loc in orig_page.locators}

        for target in targets:
            emitted = OmniEmitter.emit(project, target)
            page_files = [f for f in emitted.keys() if "LoginPage" in f and ("pages" in f or "Page" in f)]
            self.assertGreaterEqual(len(page_files), 1, f"Missing Page file for {target}")
            page_path = page_files[0]
            page_code = emitted[page_path]

            # Parse emitted code back into Universal IR
            restored = OmniParser.parse_code(page_code, file_path=page_path)
            self.assertGreaterEqual(len(restored.pages), 1, f"{target} failed to parse PageClass")

            restored_page = restored.pages[0]
            self.assertEqual(restored_page.name, orig_page.name, f"{target} PageClass name mismatch")

            # Check that locators were preserved (case-insensitive across idiomatic conventions)
            restored_loc_names = {loc.name.lower() for loc in restored_page.locators}
            expected_lower = {loc.lower() for loc in expected_locator_names}
            self.assertEqual(restored_loc_names, expected_lower,
                             f"{target} locators mismatch! Expected {expected_lower}, got {restored_loc_names}")

            # Check that business action method was preserved
            restored_method_names = {m.name for m in restored_page.methods}
            self.assertIn("login", restored_method_names, f"{target} missing 'login' action method")


if __name__ == "__main__":
    unittest.main()
