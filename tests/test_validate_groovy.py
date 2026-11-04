#!/usr/bin/env python3
"""
Unit tests for tools/validate_groovy_scripts.py
"""

import tempfile
from pathlib import Path
import unittest

from tools.validate_groovy_scripts import (
    resolve_target_repo,
    strip_comments_and_strings,
    check_file,
    HUB_ROOT,
)


class TestValidateGroovyScripts(unittest.TestCase):
    def test_strip_comments_and_strings(self):
        source = """
        // Line comment with { braces }
        /* Block comment
           with ( parens ) */
        String msg = "Hello {world}"
        String regex = ~/[a-z]{3}/
        def foo() {
            println("bar")
        }
        """
        stripped = strip_comments_and_strings(source)
        self.assertNotIn("Line comment", stripped)
        self.assertNotIn("Block comment", stripped)
        self.assertNotIn("Hello {world}", stripped)
        self.assertEqual(stripped.count("{"), 1)
        self.assertEqual(stripped.count("}"), 1)

    def test_check_file_valid_groovy(self):
        with tempfile.NamedTemporaryFile("w", suffix=".groovy", delete=False, encoding="utf-8") as f:
            f.write("""
            class LoginPage extends BasePage {
                void login(String u, String p) {
                    WebUI.setText(findTestObject('input_user'), u)
                }
            }
            """)
            temp_path = Path(f.name)

        try:
            errors = check_file(temp_path)
            self.assertEqual(len(errors), 0, f"Expected no errors but got: {errors}")
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_check_file_unmatched_braces(self):
        with tempfile.NamedTemporaryFile("w", suffix=".groovy", delete=False, encoding="utf-8") as f:
            f.write("""
            class BrokenPage {
                void test() {
            }
            """)
            temp_path = Path(f.name)

        try:
            errors = check_file(temp_path)
            self.assertTrue(any("Unmatched braces" in e for e in errors))
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_check_file_illegal_escape(self):
        with tempfile.NamedTemporaryFile("w", suffix=".groovy", delete=False, encoding="utf-8") as f:
            f.write("""
            String badRegex = "[\\]"
            """)
            temp_path = Path(f.name)

        try:
            errors = check_file(temp_path)
            self.assertTrue(any("Illegal escape sequence" in e for e in errors))
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_resolve_target_repo(self):
        # Fallback to HUB_ROOT when None
        res = resolve_target_repo(None, None)
        self.assertEqual(res, HUB_ROOT)

        # Explicit existing directory
        with tempfile.TemporaryDirectory() as td:
            res_td = resolve_target_repo(td, None)
            self.assertEqual(res_td, Path(td).resolve())

        # Non-existent directory raises FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            resolve_target_repo("/non_existent_path_xyz_123", None)


if __name__ == "__main__":
    unittest.main()
