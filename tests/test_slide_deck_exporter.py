#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
tests/test_slide_deck_exporter.py — Unit tests for Pure HTML/CSS 16:9 Vector Slide Deck Exporter
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from tools.contrib.slide_deck_exporter import (
    build_qa_executive_deck,
    export_deck_to_file,
    export_pdf_via_playwright,
    generate_slide_html,
    main,
    render_presentation_deck,
)


class TestSlideDeckExporter(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_slides_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_generate_slide_html(self):
        s_html = generate_slide_html("Test Title", "Test Subtitle", "<p>Body text</p>", 1, 3)
        self.assertIn("Test Title", s_html)
        self.assertIn("Test Subtitle", s_html)
        self.assertIn("<p>Body text</p>", s_html)
        self.assertIn("Slide 1 of 3", s_html)

    def test_render_presentation_deck(self):
        slides = [
            {"title": "Slide 1", "subtitle": "Intro", "body_html": "<p>Content 1</p>"},
            {"title": "Slide 2", "subtitle": "Details", "body_html": "<p>Content 2</p>"},
        ]
        deck = render_presentation_deck("Executive Deck", slides)
        self.assertIn("Executive Deck", deck)
        self.assertIn("aspect-ratio: 16 / 9;", deck)
        self.assertIn("slide-1", deck)
        self.assertIn("slide-2", deck)
        self.assertIn("toggleFullscreen()", deck)
        self.assertIn("@media print", deck)

    def test_build_qa_executive_deck_and_export(self):
        mock_report = {
            "mode": "HUB",
            "all_passed": True,
            "gates": {
                "GATE_1": {"name": "Encoding", "status": "PASS"},
                "GATE_2": {"name": "Portability", "status": "PASS"},
            },
        }
        slides = build_qa_executive_deck(mock_report)
        self.assertGreaterEqual(len(slides), 3)

        deck_html = render_presentation_deck("Hub QA Test", slides)
        out_file = os.path.join(self.test_dir, "test_deck.html")
        saved_path = export_deck_to_file(deck_html, out_file)

        self.assertTrue(os.path.isfile(saved_path))
        with open(saved_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("10/10 PASS", content)
        self.assertIn("Clean POM Architecture", content)

    def test_build_qa_executive_deck_all_passed_false(self):
        # Explicitly verify all_passed=False branch
        mock_report = {
            "mode": "TARGET",
            "all_passed": False,
            "gates": {},
        }
        slides = build_qa_executive_deck(mock_report)
        self.assertIn("FAILED", slides[0]["body_html"])
        self.assertNotIn("10/10 PASS", slides[0]["body_html"])
        self.assertIn("Target", slides[0]["subtitle"].title())

    def test_build_qa_executive_deck_all_passed_default(self):
        # When all_passed is omitted, default must be True -> 10/10 PASS
        slides = build_qa_executive_deck({})
        self.assertIn("10/10 PASS", slides[0]["body_html"])
        self.assertNotIn("FAILED", slides[0]["body_html"])

    def test_build_qa_executive_deck_list_implicit_pass(self):
        # Item with neither status nor passed must default to PASS
        mock_report = {
            "gates": [
                {"name": "Gate ImplicitPass"},
            ],
        }
        slides = build_qa_executive_deck(mock_report)
        gates_slide = slides[1]["body_html"]
        self.assertIn("PASS", gates_slide)
        self.assertNotIn("FAIL", gates_slide)
        self.assertIn("metric-card success", gates_slide)

    def test_build_qa_executive_deck_list_format(self):
        # Test list of gates with both passed=True and passed=False
        mock_report = {
            "all_passed": False,
            "gates": [
                {"name": "Gate One", "passed": True},
                {"name": "Gate Two", "passed": False},
                {"name": "Gate Three", "status": "WARN"},
            ],
        }
        slides = build_qa_executive_deck(mock_report)
        gates_slide = slides[1]["body_html"]
        self.assertIn("Gate One", gates_slide)
        self.assertIn("Gate Two", gates_slide)
        self.assertIn("Gate Three", gates_slide)
        self.assertIn("PASS", gates_slide)
        self.assertIn("FAIL", gates_slide)
        self.assertIn("WARN", gates_slide)

    def test_build_qa_executive_deck_dict_format_unnamed_fallback(self):
        # Dict format with missing name must fallback to f"Gate {g_num}" and not None
        mock_report = {
            "gates": {
                "GATE_1": {"status": "PASS"},
                "GATE_2": {"name": None, "status": "PASS"},
            },
        }
        slides = build_qa_executive_deck(mock_report)
        gates_slide = slides[1]["body_html"]
        self.assertIn("Gate 1", gates_slide)
        self.assertIn("Gate 2", gates_slide)
        self.assertNotIn(">None<", gates_slide)

    def test_xss_prevention_in_status_and_name(self):
        xss_payload = '<script>alert("XSS")</script>'
        mock_report = {
            "gates": [
                {"name": xss_payload, "status": xss_payload},
            ],
        }
        slides = build_qa_executive_deck(mock_report)
        deck_html = render_presentation_deck("XSS Test", slides)
        # Raw unescaped script tag MUST NOT appear
        self.assertNotIn(xss_payload, deck_html)
        # Escaped script tag MUST appear
        self.assertIn("&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;", deck_html)

        # Also test dict format XSS
        dict_report = {
            "gates": {
                "GATE_1": {"name": xss_payload, "status": xss_payload},
            },
        }
        dict_slides = build_qa_executive_deck(dict_report)
        dict_html = render_presentation_deck("Dict XSS", dict_slides)
        self.assertNotIn(xss_payload, dict_html)
        self.assertIn("&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;", dict_html)

    def test_malformed_inputs_handling(self):
        # 1. gates is None
        slides1 = build_qa_executive_deck({"gates": None})
        self.assertEqual(len(slides1), 3)

        # 2. gates is a string
        slides2 = build_qa_executive_deck({"gates": "corrupted string"})
        self.assertEqual(len(slides2), 3)

        # 3. gates list contains None or int or missing names
        slides3 = build_qa_executive_deck({
            "gates": [
                None,
                {"name": None, "status": None},
                {"name": 12345, "status": 999},
            ],
        })
        self.assertEqual(len(slides3), 3)
        self.assertIn("Gate 1", slides3[1]["body_html"])
        self.assertIn("12345", slides3[1]["body_html"])

        # 4. gates dict contains non-dict items
        slides4 = build_qa_executive_deck({
            "gates": {
                "GATE_1": "corrupt",
                "GATE_2": None,
            },
        })
        self.assertEqual(len(slides4), 3)

        # 5. report_data is not a dict
        slides5 = build_qa_executive_deck(None)  # type: ignore
        self.assertEqual(len(slides5), 3)

    def test_export_pdf_via_playwright_no_npx(self):
        with patch("shutil.which", return_value=None):
            result = export_pdf_via_playwright("input.html", "output.pdf")
            self.assertFalse(result)

    def test_export_pdf_via_playwright_success(self):
        dummy_pdf = os.path.join(self.test_dir, "output.pdf")
        with open(dummy_pdf, "w") as f:
            f.write("PDF")

        mock_res = MagicMock()
        mock_res.returncode = 0
        with patch("shutil.which", return_value="/usr/local/bin/npx"), \
             patch("subprocess.run", return_value=mock_res) as mock_run:
            result = export_pdf_via_playwright("input.html", dummy_pdf)
            self.assertTrue(result)
            mock_run.assert_called_once_with(
                ["/usr/local/bin/npx", "playwright", "pdf", "input.html", dummy_pdf, "--landscape"],
                capture_output=True,
                text=True,
                timeout=60,
            )

    def test_export_pdf_via_playwright_nonzero_return(self):
        dummy_pdf = os.path.join(self.test_dir, "output.pdf")
        with open(dummy_pdf, "w") as f:
            f.write("PDF")
        mock_res = MagicMock()
        mock_res.returncode = 1
        with patch("shutil.which", return_value="/usr/local/bin/npx"), \
             patch("subprocess.run", return_value=mock_res):
            result = export_pdf_via_playwright("input.html", dummy_pdf)
            self.assertFalse(result)

    def test_export_pdf_via_playwright_missing_output_file(self):
        non_existent_pdf = os.path.join(self.test_dir, "does_not_exist.pdf")
        mock_res = MagicMock()
        mock_res.returncode = 0
        with patch("shutil.which", return_value="/usr/local/bin/npx"), \
             patch("subprocess.run", return_value=mock_res):
            result = export_pdf_via_playwright("input.html", non_existent_pdf)
            self.assertFalse(result)

    def test_export_pdf_via_playwright_exception(self):
        with patch("shutil.which", return_value="/usr/local/bin/npx"), \
             patch("subprocess.run", side_effect=subprocess.SubprocessError("timeout")):
            result = export_pdf_via_playwright("input.html", "output.pdf")
            self.assertFalse(result)

    def test_main_cli_execution(self):
        input_json = os.path.join(self.test_dir, "report.json")
        with open(input_json, "w", encoding="utf-8") as f:
            json.dump({"mode": "HUB", "all_passed": True, "gates": []}, f)

        out_html = os.path.join(self.test_dir, "output.html")
        out_pdf = os.path.join(self.test_dir, "output.pdf")

        # Test CLI run without PDF
        with patch("sys.argv", ["slide_deck_exporter.py", "--input", input_json, "--output", out_html]):
            code = main()
            self.assertEqual(code, 0)
            self.assertTrue(os.path.isfile(out_html))

        # Test CLI run with PDF export fallback
        with patch("sys.argv", ["slide_deck_exporter.py", "--input", input_json, "--output", out_html, "--pdf", out_pdf]), \
             patch("tools.contrib.slide_deck_exporter.export_pdf_via_playwright", return_value=False):
            code = main()
            self.assertEqual(code, 0)

        # Test CLI run with PDF export success
        with patch("sys.argv", ["slide_deck_exporter.py", "--input", input_json, "--output", out_html, "--pdf", out_pdf]), \
             patch("tools.contrib.slide_deck_exporter.export_pdf_via_playwright", return_value=True):
            code = main()
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
