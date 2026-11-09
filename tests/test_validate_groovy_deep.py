#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Deep unit tests for tools/validate_groovy_scripts.py
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tools.validate_groovy_scripts as vgs


class TestValidateGroovyDeep(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="groovy_test_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_strip_comments_and_strings_complex(self):
        code = """
        // Line comment
        /* Multi-line
           comment */
        String tripleD = \"\"\"This is {inside} a triple string\"\"\"
        String tripleS = \'\'\'This is (inside) single triple\'\'\'
        String ds_var = $/dollar $slashy {with} /braces/$
        String normalStr = "Hello \\"world\\" {foo}"
        String singleStr = 'Single \\'quote\\' (bar)'
        def regex = ~/[A-Z]+{2}/
        def foo() {
            int a = 10 / 2 + 5 / 1;
            println("Done");
        }
        """
        stripped = vgs.strip_comments_and_strings(code)
        self.assertNotIn("Line comment", stripped)
        self.assertNotIn("Multi-line", stripped)
        self.assertNotIn("inside", stripped)
        self.assertNotIn("dollar", stripped)
        self.assertEqual(stripped.count("{"), 1)
        self.assertEqual(stripped.count("}"), 1)

    def test_check_file_unescaped_backslash(self):
        bad_file = Path(self.temp_dir) / "bad.groovy"
        bad_file.write_text('String s = "\\";\n', encoding="utf-8")
        errs = vgs.check_file(bad_file)
        self.assertTrue(any("Unescaped single backslash" in e for e in errs))

    def test_check_file_unmatched_parens(self):
        bad_file = Path(self.temp_dir) / "unmatched_paren.groovy"
        bad_file.write_text("def run() { println('hello'; }\n", encoding="utf-8")
        errs = vgs.check_file(bad_file)
        self.assertTrue(any("Unmatched parentheses" in e for e in errs))

    def test_check_file_latin1_fallback(self):
        latin_file = Path(self.temp_dir) / "latin.groovy"
        # Write bytes invalid in UTF-8 but valid in latin-1
        latin_file.write_bytes(b"// Comment with accent \xe9\nclass LatinPage {}\n")
        errs = vgs.check_file(latin_file)
        self.assertEqual(errs, [])

    def test_main_with_clean_files(self):
        scripts_dir = Path(self.temp_dir) / "Scripts"
        scripts_dir.mkdir()
        good_script = scripts_dir / "TC_Good.groovy"
        good_script.write_text("class GoodScript { void run() { println('OK'); } }\n", encoding="utf-8")

        with patch("sys.argv", ["validate_groovy_scripts.py", "--dir", str(scripts_dir)]):
            exit_code = vgs.main()
            self.assertEqual(exit_code, 0)

    def test_main_with_syntax_errors(self):
        bad_dir = Path(self.temp_dir) / "BadScripts"
        bad_dir.mkdir()
        bad_script = bad_dir / "TC_Bad.groovy"
        bad_script.write_text("class BadScript { void run() { }\n", encoding="utf-8")  # Missing close brace

        with patch("sys.argv", ["validate_groovy_scripts.py", "--dir", str(bad_dir)]):
            exit_code = vgs.main()
            self.assertEqual(exit_code, 1)

    def test_main_single_file_target(self):
        single_file = Path(self.temp_dir) / "Single.groovy"
        single_file.write_text("class Single { void run() {} }\n", encoding="utf-8")
        with patch("sys.argv", ["validate_groovy_scripts.py", str(single_file)]):
            exit_code = vgs.main()
            self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
