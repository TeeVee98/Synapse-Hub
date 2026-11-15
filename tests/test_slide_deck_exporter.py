#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
tests/test_slide_deck_exporter.py — Unit tests for Pure HTML/CSS 16:9 Vector Slide Deck Exporter
"""

import os
import shutil
import tempfile
import unittest

from tools.slide_deck_exporter import (
    build_qa_executive_deck,
    export_deck_to_file,
    generate_slide_html,
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


if __name__ == "__main__":
    unittest.main()
