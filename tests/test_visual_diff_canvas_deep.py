#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Deep unit tests for tools/visual_diff_canvas.py
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw

import tools.visual_diff_canvas as vdc


class TestVisualDiffCanvasDeep(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="canvas_diff_test_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_image(self, filename, color, draw_pattern=False):
        fpath = os.path.join(self.temp_dir, filename)
        img = Image.new("RGB", (100, 100), color=color)
        if draw_pattern:
            draw = ImageDraw.Draw(img)
            draw.rectangle([20, 20, 80, 80], fill=(255, 0, 0))
            draw.line([0, 0, 100, 100], fill=(0, 255, 0), width=3)
        img.save(fpath)
        return fpath

    def test_is_canvas_blank(self):
        # Uniform solid white image -> blank = True
        blank_img = self._create_image("blank.png", color=(255, 255, 255), draw_pattern=False)
        is_blank, std = vdc.is_canvas_blank(blank_img, std_dev_threshold=2.0)
        self.assertTrue(is_blank)
        self.assertLess(std, 2.0)

        # Patterned image -> blank = False
        active_img = self._create_image("pattern.png", color=(255, 255, 255), draw_pattern=True)
        is_blank2, std2 = vdc.is_canvas_blank(active_img, std_dev_threshold=2.0)
        self.assertFalse(is_blank2)
        self.assertGreaterEqual(std2, 2.0)

    def test_compare_canvas_images_identical(self):
        img1 = self._create_image("base.png", color=(200, 200, 200), draw_pattern=True)
        img2 = self._create_image("curr.png", color=(200, 200, 200), draw_pattern=True)

        is_match, ratio, diff_count = vdc.compare_canvas_images(img1, img2, threshold=0.01)
        self.assertTrue(is_match)
        self.assertEqual(diff_count, 0)
        self.assertEqual(ratio, 0.0)

    def test_compare_canvas_images_divergence_and_diff_generation(self):
        img_base = self._create_image("base.png", color=(255, 255, 255), draw_pattern=False)
        img_curr = self._create_image("curr.png", color=(255, 255, 255), draw_pattern=True)
        diff_out = os.path.join(self.temp_dir, "diff_highlight.png")

        is_match, ratio, diff_count = vdc.compare_canvas_images(
            img_base, img_curr, diff_output_path=diff_out, threshold=0.01
        )
        self.assertFalse(is_match)
        self.assertGreater(diff_count, 100)
        self.assertGreater(ratio, 0.01)
        self.assertTrue(os.path.exists(diff_out))

    def test_compare_canvas_different_dimensions_resized(self):
        # img1 is 100x100
        img1 = self._create_image("base100.png", color=(128, 128, 128))
        # img2 is 50x50
        img2_path = os.path.join(self.temp_dir, "curr50.png")
        img2 = Image.new("RGB", (50, 50), color=(128, 128, 128))
        img2.save(img2_path)

        is_match, ratio, diff_count = vdc.compare_canvas_images(img1, img2_path, threshold=0.05)
        self.assertTrue(is_match)

    def test_main_cli_compare(self):
        img1 = self._create_image("cli_b.png", color=(100, 100, 100))
        img2 = self._create_image("cli_c.png", color=(100, 100, 100))

        # PASS path
        with patch("sys.argv", ["visual_diff_canvas.py", "compare", img1, img2]):
            with self.assertRaises(SystemExit) as cm:
                vdc.main()
            self.assertEqual(cm.exception.code, 0)

        # Missing file path
        with patch("sys.argv", ["visual_diff_canvas.py", "compare", "non_existent.png", img2]):
            with self.assertRaises(SystemExit) as cm:
                vdc.main()
            self.assertEqual(cm.exception.code, 2)

    def test_main_cli_check_blank(self):
        solid = self._create_image("solid.png", color=(0, 0, 0))
        with patch("sys.argv", ["visual_diff_canvas.py", "check-blank", solid]):
            with self.assertRaises(SystemExit) as cm:
                vdc.main()
            self.assertEqual(cm.exception.code, 1)  # Blank exits with 1


if __name__ == "__main__":
    unittest.main()
