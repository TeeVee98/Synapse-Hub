import unittest
import os
import tempfile
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import verify_all


class TestVerifyAll(unittest.TestCase):
    def test_gate_1_detects_utf8_bom(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            bom_file = os.path.join(tmp_dir, "test_with_bom.groovy")
            with open(bom_file, "wb") as f:
                f.write(b'\xef\xbb\xbfclass TestClass {}')

            clean_file = os.path.join(tmp_dir, "test_clean.groovy")
            with open(clean_file, "wb") as f:
                f.write(b'class CleanClass {}')

            # Gate 1 should fail because of bom_file
            passed = verify_all.gate_1_bom_check(tmp_dir, mode="HUB")
            self.assertFalse(passed)

    def test_gate_1_passes_clean_utf8(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            clean_file = os.path.join(tmp_dir, "test_clean.groovy")
            with open(clean_file, "wb") as f:
                f.write(b'class CleanClass {}')

            passed = verify_all.gate_1_bom_check(tmp_dir, mode="HUB")
            self.assertTrue(passed)

    def test_gate_2_path_portability_clean(self):
        # Current repo should have 0 path portability violations
        passed = verify_all.gate_2_path_portability(verify_all.REPO_ROOT, mode="HUB")
        self.assertTrue(passed)

    def test_gate_6_credential_security_clean(self):
        # Current repo should have 0 hardcoded credentials
        passed = verify_all.gate_6_credential_security(verify_all.REPO_ROOT, mode="HUB")
        self.assertTrue(passed)


if __name__ == "__main__":
    unittest.main()
