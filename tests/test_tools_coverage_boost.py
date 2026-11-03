#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tests/test_tools_coverage_boost.py
----------------------------------
Comprehensive unit tests boosting code coverage across critical hub tools:
  1. output_formatter (debug, info, warn, error, success, get_logger, format_table)
  2. visual_diff_canvas (is_canvas_blank, compare_canvas_images)
  3. telemetry_correlator (pearson correlation, correlation attribution)
  4. test_impact (fallback AST graph, impacted script identification)
  5. auto_heal (failure diagnosis and healing plan from JUnit XML)
  6. cli (SynapseArgumentParser fuzzy typo suggestion, command registry)
"""

import os
import sys
import json
import tempfile
import unittest
import io
from pathlib import Path

# Add tools to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore
    HAS_PIL = False


class TestOutputFormatterCoverage(unittest.TestCase):
    """Thorough tests for tools/output_formatter.py functions and logging adapter."""

    def setUp(self):
        import output_formatter
        self.output_formatter = output_formatter
        self.fmt = output_formatter.OutputFormatter()

    def test_basic_logging_functions(self):
        buf = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = buf
            self.fmt.info("Informational message")
            self.fmt.warn("Warning message")
            self.fmt.error("Error message")
            self.fmt.success("Success message")
            self.fmt.header("Section Header")
            self.fmt.step(1, 3, "Step Title")
            self.fmt.print_data({"status": "ok"}, format_type="json")
            self.fmt.print_data("plain text", format_type="text")
        finally:
            sys.stdout = old_stdout

        out = buf.getvalue()
        self.assertIn("Informational message", out)
        self.assertIn("Warning message", out)
        self.assertIn("Error message", out)
        self.assertIn("Success message", out)
        self.assertIn("Section Header", out)
        self.assertIn("Step Title", out)
        self.assertIn('"status": "ok"', out)

    def test_debug_logging_with_verbose_flag(self):
        buf = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = buf
            # Verbose off: debug should be silent
            fmt_normal = self.output_formatter.OutputFormatter(verbose=False)
            fmt_normal.debug("Hidden debug detail")
            self.assertNotIn("Hidden debug detail", buf.getvalue())

            # Verbose on: debug should print
            fmt_verbose = self.output_formatter.OutputFormatter(verbose=True)
            fmt_verbose.debug("Visible debug detail")
            self.assertIn("Visible debug detail", buf.getvalue())
        finally:
            sys.stdout = old_stdout

    def test_quiet_mode_suppression(self):
        buf = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = buf
            fmt_quiet = self.output_formatter.OutputFormatter(quiet=True)
            fmt_quiet.info("Should not appear in quiet mode")
            fmt_quiet.warn("Should not appear in quiet mode either")
            self.assertNotIn("Should not appear in quiet mode", buf.getvalue())
        finally:
            sys.stdout = old_stdout

    def test_colors_and_helpers(self):
        from output_formatter import Colors
        self.assertTrue(len(Colors.cyan("cyan_text")) > 0)
        self.assertTrue(len(Colors.green("green_text")) > 0)
        self.assertTrue(len(Colors.yellow("yellow_text")) > 0)
        self.assertTrue(len(Colors.red("red_text")) > 0)
        self.assertTrue(len(Colors.bold("bold_text")) > 0)
        self.assertTrue(len(Colors.dim("dim_text")) > 0)

    def test_get_logger_bridge(self):
        logger = self.output_formatter.get_logger("test_module_boost", verbose=True)
        buf = io.StringIO()
        old_stderr = sys.stderr
        try:
            sys.stderr = buf
            # Also redirect handler's stream
            for h in logger.handlers:
                h.stream = buf
            logger.info("Logger bridge info")
            logger.warning("Logger bridge warning")
            logger.error("Logger bridge error")
        finally:
            sys.stderr = old_stderr

        out = buf.getvalue()
        self.assertIn("Logger bridge info", out)
        self.assertIn("Logger bridge warning", out)
        self.assertIn("Logger bridge error", out)


@unittest.skipUnless(HAS_PIL, "Pillow is required for visual diff tests")
class TestVisualDiffCanvasCoverage(unittest.TestCase):
    """Unit tests for tools/visual_diff_canvas.py."""

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.test_dir.name)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_is_canvas_blank_on_solid_image(self):
        from visual_diff_canvas import is_canvas_blank
        solid_path = str(self.dir_path / "solid_white.png")
        img = Image.new("RGB", (200, 200), color=(255, 255, 255))
        img.save(solid_path)

        is_blank, std_dev = is_canvas_blank(solid_path, std_dev_threshold=2.0)
        self.assertTrue(is_blank)
        self.assertAlmostEqual(std_dev, 0.0, places=2)

    def test_is_canvas_blank_on_non_blank_image(self):
        from visual_diff_canvas import is_canvas_blank
        rich_path = str(self.dir_path / "rich_chart.png")
        img = Image.new("RGB", (200, 200), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([20, 20, 80, 80], fill=(255, 0, 0))
        draw.line([0, 0, 200, 200], fill=(0, 0, 255), width=3)
        img.save(rich_path)

        is_blank, std_dev = is_canvas_blank(rich_path, std_dev_threshold=2.0)
        self.assertFalse(is_blank)
        self.assertGreater(std_dev, 5.0)

    def test_compare_canvas_images_identical_and_different(self):
        from visual_diff_canvas import compare_canvas_images
        base_path = str(self.dir_path / "base.png")
        curr_same = str(self.dir_path / "curr_same.png")
        curr_diff = str(self.dir_path / "curr_diff.png")
        diff_out = str(self.dir_path / "diff_overlay.png")

        img_base = Image.new("RGB", (100, 100), color=(100, 150, 200))
        img_base.save(base_path)
        img_base.save(curr_same)

        img_diff = Image.new("RGB", (100, 100), color=(100, 150, 200))
        draw = ImageDraw.Draw(img_diff)
        draw.rectangle([30, 30, 70, 70], fill=(255, 0, 0))
        img_diff.save(curr_diff)

        # Identical comparison
        match, ratio, diff_pixels = compare_canvas_images(base_path, curr_same)
        self.assertTrue(match)
        self.assertEqual(diff_pixels, 0)
        self.assertEqual(ratio, 0.0)

        # Different comparison
        match, ratio, diff_pixels = compare_canvas_images(base_path, curr_diff, diff_output_path=diff_out, threshold=0.01)
        self.assertFalse(match)
        self.assertGreater(diff_pixels, 0)
        self.assertTrue(os.path.exists(diff_out))


class TestTelemetryCorrelatorCoverage(unittest.TestCase):
    """Unit tests for tools/telemetry_correlator.py."""

    def test_calculate_pearson_correlation(self):
        from telemetry_correlator import calculate_pearson_correlation

        # Perfect positive correlation (r = 1.0)
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [10.0, 20.0, 30.0, 40.0, 50.0]
        r = calculate_pearson_correlation(x, y)
        self.assertAlmostEqual(r, 1.0, places=4)

        # Perfect negative correlation (r = -1.0)
        y_neg = [50.0, 40.0, 30.0, 20.0, 10.0]
        r_neg = calculate_pearson_correlation(x, y_neg)
        self.assertAlmostEqual(r_neg, -1.0, places=4)

        # Degenerate cases: empty or single point
        self.assertEqual(calculate_pearson_correlation([], []), 0.0)
        self.assertEqual(calculate_pearson_correlation([1.0], [2.0]), 0.0)

        # Zero variance returns 0.0 safely
        self.assertEqual(calculate_pearson_correlation([5.0, 5.0, 5.0], [1.0, 2.0, 3.0]), 0.0)


class TestTestImpactCoverage(unittest.TestCase):
    """Unit tests for tools/test_impact.py."""

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.test_dir.name)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_build_fallback_graph_and_impact(self):
        from test_impact import build_fallback_graph, resolve_target_repo

        # Create simulated project structure
        pages_dir = self.root / "Keywords" / "pages"
        pages_dir.mkdir(parents=True)
        scripts_dir = self.root / "Scripts" / "orders"
        scripts_dir.mkdir(parents=True)

        # OrderPage.groovy
        order_page = pages_dir / "OrderPage.groovy"
        order_page.write_text("class OrderPage { void checkout() {} }", encoding="utf-8")

        # OrderTest.groovy referencing OrderPage
        order_test = scripts_dir / "OrderTest.groovy"
        order_test.write_text("def p = new OrderPage(); p.checkout()", encoding="utf-8")

        # Independent test
        unrelated_test = scripts_dir / "UnrelatedTest.groovy"
        unrelated_test.write_text("// does not use order page", encoding="utf-8")

        graph = build_fallback_graph(str(self.root))
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        node_ids = [n["id"] for n in nodes]
        self.assertIn("OrderPage", node_ids)

        # Check edge exists connecting OrderTest to OrderPage
        has_edge = any(
            e.get("target") == "OrderPage" and "OrderTest" in e.get("source", "")
            for e in edges
        )
        self.assertTrue(has_edge, "Graph must link OrderTest to OrderPage")

        # Test target repository resolution
        resolved = resolve_target_repo(cli_target=str(self.root))
        self.assertEqual(os.path.realpath(resolved), os.path.realpath(str(self.root.resolve())))


class TestAutoHealCoverage(unittest.TestCase):
    """Unit tests for tools/auto_heal.py."""

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.test_dir.name)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_diagnose_and_plan_heal_with_junit_xml(self):
        from auto_heal import diagnose_and_plan_heal

        xml_path = self.root / "test_report.xml"
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="OrderTestSuite" tests="1" failures="1" errors="0" time="2.5">
    <testcase classname="orders.OrderTest" name="testPlaceOrder" time="2.5">
        <failure message="NoSuchElementException: Unable to locate element //button[@id='submit']" type="NoSuchElementException">
            orders.OrderTest.testPlaceOrder(OrderTest.groovy:42)
        </failure>
    </testcase>
</testsuite>
"""
        xml_path.write_text(xml_content, encoding="utf-8")

        buf = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = buf
            plan = diagnose_and_plan_heal(str(self.root), junit_xml_path=str(xml_path))
        finally:
            sys.stdout = old_stdout

        self.assertIsInstance(plan, dict)
        self.assertIn("status", plan)


class TestCliFuzzyTypoSuggestions(unittest.TestCase):
    """Unit tests for tools/cli.py fuzzy typo matching."""

    def test_fuzzy_did_you_mean_on_typo(self):
        from cli import SynapseArgumentParser

        parser = SynapseArgumentParser(prog="agent-qa")
        subparsers = parser.add_subparsers(dest="subcommand")
        subparsers.add_parser("doctor")
        subparsers.add_parser("verify")
        subparsers.add_parser("setup")

        buf = io.StringIO()
        old_stderr = sys.stderr
        try:
            sys.stderr = buf
            with self.assertRaises(SystemExit) as cm:
                parser.parse_args(["docor"])  # Typo for 'doctor'
            self.assertEqual(cm.exception.code, 2)
        finally:
            sys.stderr = old_stderr

        out = buf.getvalue()
        self.assertIn("doctor", out)
        self.assertIn("Có phải ý bạn là", out)


class TestBumpVersionCoverage(unittest.TestCase):
    """Unit tests for tools/bump_version.py version calculation and regex replacement."""

    def test_calculate_next_version(self):
        from bump_version import calculate_next_version, parse_semver

        self.assertEqual(calculate_next_version("2.4.3", "patch"), "2.4.4")
        self.assertEqual(calculate_next_version("2.4.3", "minor"), "2.5.0")
        self.assertEqual(calculate_next_version("2.4.3", "major"), "3.0.0")
        self.assertEqual(calculate_next_version("2.4.3", "2.4.5"), "2.4.5")
        self.assertEqual(calculate_next_version("2.4.3", "3.0.1"), "3.0.1")

        major, minor, patch, suffix = parse_semver("3.12.8")
        self.assertEqual((major, minor, patch, suffix), (3, 12, 8, ""))


class TestNewmanAnalyzerCoverage(unittest.TestCase):
    """Unit tests for tools/newman_analyzer.py report parsing and SLA evaluation."""

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.test_dir.name)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_parse_and_evaluate_newman(self):
        from newman_analyzer import parse_newman_json, evaluate_newman_sla, generate_markdown_report

        report_file = self.root / "newman_run.json"
        sample_json = {
            "run": {
                "stats": {
                    "iterations": {"total": 1, "failed": 0},
                    "requests": {"total": 5, "failed": 0},
                    "prerequests": {"total": 5, "failed": 0},
                    "testScripts": {"total": 5, "failed": 0},
                    "assertions": {"total": 10, "failed": 0}
                },
                "timings": {
                    "responseAverage": 120.5,
                    "responseMin": 45.0,
                    "responseMax": 250.0,
                    "started": 1700000000000,
                    "completed": 1700000005000
                },
                "executions": [
                    {
                        "item": {"name": "Get User Profile"},
                        "request": {"method": "GET", "url": {"raw": "https://api.example.com/user"}},
                        "response": {"code": 200, "responseTime": 110, "status": "OK"},
                        "assertions": [{"assertion": "Status is 200", "skipped": False}]
                    }
                ],
                "failures": []
            }
        }
        report_file.write_text(json.dumps(sample_json), encoding="utf-8")

        summary = parse_newman_json(str(report_file))
        self.assertEqual(summary["total_requests"], 5)
        self.assertEqual(summary["total_assertions"], 10)
        self.assertEqual(summary["failed_assertions"], 0)

        passed, violations = evaluate_newman_sla(summary, max_failures=0, sla_avg=500.0)
        self.assertTrue(passed)
        self.assertEqual(len(violations), 0)

        md = generate_markdown_report(summary, passed, violations)
        self.assertIn("Postman / Newman API Automated Test Report", md)
        self.assertIn("Get User Profile", md)


class TestExportPostmanCoverage(unittest.TestCase):
    """Unit tests for tools/export_postman_collection.py schema parsing."""

    def test_export_openapi_to_postman_collection(self):
        from export_postman_collection import parse_openapi_spec, generate_postman_environment, generate_ddt_dataset

        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Sample API", "version": "1.0.0"},
            "servers": [{"url": "https://api.enterprise.local/v1"}],
            "paths": {
                "/users/{id}": {
                    "get": {
                        "summary": "Get user by ID",
                        "parameters": [
                            {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                        ],
                        "responses": {
                            "200": {
                                "description": "User found",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {"id": {"type": "integer"}, "name": {"type": "string"}}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        col = parse_openapi_spec(spec)
        self.assertIn("info", col)
        self.assertEqual(col["info"]["name"], "Sample API")
        self.assertTrue(len(col["item"]) > 0)

        env = generate_postman_environment("Staging", "https://api.staging.local")
        self.assertIn("values", env)

        ddt = generate_ddt_dataset("ecommerce")
        self.assertIsInstance(ddt, list)
        self.assertTrue(len(ddt) > 0)


if __name__ == "__main__":
    unittest.main()
