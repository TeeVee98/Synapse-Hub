import unittest
import os
import tempfile
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import infer_linter


class TestInferLinter(unittest.TestCase):
    def test_strip_comments_and_strings(self):
        code = """
        // Single comment with assert
        /* Block comment
           with assert inside
        */
        String doc = \"\"\"
           multiline assert statement
        \"\"\"
        String normal = "string with assert"
        int actualCode = 42
        """
        stripped = infer_linter.strip_comments_and_strings(code)
        self.assertNotIn("with assert inside", stripped)
        self.assertNotIn("multiline assert", stripped)
        self.assertIn("actualCode", stripped)
        # Line count preserved
        self.assertEqual(code.count("\n"), stripped.count("\n"))

    def test_swallowed_exception_detection(self):
        # Catch with only comments inside should be detected as empty
        with tempfile.NamedTemporaryFile("w", suffix=".groovy", delete=False, encoding="utf-8") as f:
            f.write("""
            try {
                doSomething()
            } catch (Exception e) {
                // Ignore exception silently
                /* Another comment */
            }
            assert true
            """)
            temp_path = f.name

        try:
            res = infer_linter.analyze_script(temp_path)
            defect_types = [d["type"] for d in res["defects"]]
            self.assertIn("SWALLOWED_EXCEPTION", defect_types)
        finally:
            os.remove(temp_path)

    def test_not_swallowed_when_exception_handled(self):
        with tempfile.NamedTemporaryFile("w", suffix=".groovy", delete=False, encoding="utf-8") as f:
            f.write("""
            try {
                doSomething()
            } catch (Exception e) {
                logger.error("Failed: " + e.getMessage())
                throw e
            }
            assert true
            """)
            temp_path = f.name

        try:
            res = infer_linter.analyze_script(temp_path)
            defect_types = [d["type"] for d in res["defects"]]
            self.assertNotIn("SWALLOWED_EXCEPTION", defect_types)
        finally:
            os.remove(temp_path)

    def test_fake_pass_when_assert_in_comment_or_string(self):
        # Interactions exist, but 'assert' is only inside comment & string literal
        with tempfile.NamedTemporaryFile("w", suffix=".groovy", delete=False, encoding="utf-8") as f:
            f.write("""
            // Line 1: perform mutation
            page.clickSubmitButton()
            page.saveChanges()
            // assert page.verifySuccess()
            /*
               assert true
            */
            String msg = "assert that changes are saved"
            """)
            temp_path = f.name

        try:
            res = infer_linter.analyze_script(temp_path)
            defect_types = [d["type"] for d in res["defects"]]
            self.assertIn("FAKE_PASS_NO_ASSERTION", defect_types)
        finally:
            os.remove(temp_path)

    def test_clean_script_with_valid_assertion(self):
        with tempfile.NamedTemporaryFile("w", suffix=".groovy", delete=False, encoding="utf-8") as f:
            f.write("""
            page.openCreateModal()
            page.fillCreateForm("CODE_123", "Name")
            page.clickSubmitButton()
            page.verifyCreateSuccess("CODE_123")
            """)
            temp_path = f.name

        try:
            res = infer_linter.analyze_script(temp_path)
            defect_types = [d["type"] for d in res["defects"]]
            self.assertNotIn("FAKE_PASS_NO_ASSERTION", defect_types)
            self.assertTrue(res["is_clean"])
        finally:
            os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
