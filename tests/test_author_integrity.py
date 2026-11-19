#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_author_integrity.py
-------------------------------
Unit tests for Author Attribution & Anti-Tamper Integrity Guard (tools/author_integrity.py).
"""

import os
import sys
import tempfile
import unittest
import hashlib
from unittest.mock import patch
import io
import contextlib

# Ensure tools/ is on path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import author_integrity
import verify_all


class TestAuthorIntegrity(unittest.TestCase):

    def test_canonical_watermark_contains_author(self):
        wm = author_integrity.get_canonical_watermark()
        self.assertIn("Thế Vị", wm)
        self.assertIn("@TeeVee98", wm)
        self.assertIn("Synapse-Hub", wm)

    def test_current_repo_passes_integrity(self):
        valid, violations = author_integrity.verify_author_attribution(REPO_ROOT)
        self.assertTrue(valid, f"Current repo failed author attribution: {violations}")
        self.assertEqual(len(violations), 0)

    def test_missing_license_detected(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            valid, violations = author_integrity.verify_author_attribution(tmp_dir)
            self.assertFalse(valid)
            self.assertTrue(any("LICENSE" in v for v in violations))

    def test_tampered_license_detected(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a LICENSE with altered copyright notice
            with open(os.path.join(tmp_dir, "LICENSE"), "w", encoding="utf-8") as f:
                f.write("MIT License\nCopyright (c) 2026 John Doe. All rights reserved.\n")
            valid, violations = author_integrity.verify_author_attribution(tmp_dir)
            self.assertFalse(valid)
            self.assertTrue(any("LICENSE file modified" in v for v in violations))

    def test_tampered_package_json_detected(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create valid LICENSE
            with open(os.path.join(tmp_dir, "LICENSE"), "w", encoding="utf-8") as f:
                f.write("Copyright (c) 2026 Thế Vị (@TeeVee98)\nhttps://github.com/TeeVee98/Synapse-Hub\n")
            # Create tampered package.json
            with open(os.path.join(tmp_dir, "package.json"), "w", encoding="utf-8") as f:
                f.write('{"name": "tampered", "author": "John Doe <john@example.com>"}\n')
            valid, violations = author_integrity.verify_author_attribution(tmp_dir)
            self.assertFalse(valid)
            self.assertTrue(any("package.json modified" in v for v in violations))

    def test_tampered_readme_detected(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create valid LICENSE
            with open(os.path.join(tmp_dir, "LICENSE"), "w", encoding="utf-8") as f:
                f.write("Copyright (c) 2026 Thế Vị (@TeeVee98)\nhttps://github.com/TeeVee98/Synapse-Hub\n")
            # Create tampered README.md
            with open(os.path.join(tmp_dir, "README.md"), "w", encoding="utf-8") as f:
                f.write("# Generic Project\nNo author attribution here.\n")
            valid, violations = author_integrity.verify_author_attribution(tmp_dir)
            self.assertFalse(valid)
            self.assertTrue(any("README.md modified" in v for v in violations))

    def test_legacy_author_handle_backwards_compatible(self):
        """Verifies that legacy @TeeVee998 in LICENSE continues to satisfy author attribution without error."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "LICENSE"), "w", encoding="utf-8") as f:
                f.write("Copyright (c) 2026 Thế Vị (@TeeVee998)\nhttps://github.com/TeeVee998/Synapse-Hub\n")
            with open(os.path.join(tmp_dir, "package.json"), "w", encoding="utf-8") as f:
                f.write('{"name": "@teevee98/synapse-hub", "author": "Thế Vị (@TeeVee98) <https://github.com/TeeVee98>"}\n')
            with open(os.path.join(tmp_dir, "README.md"), "w", encoding="utf-8") as f:
                f.write("# Synapse Hub\nAuthor: Thế Vị (@TeeVee98) https://github.com/TeeVee98/Synapse-Hub\n")
            valid, violations = author_integrity.verify_author_attribution(tmp_dir)
            self.assertTrue(valid, f"Legacy @TeeVee998 must be accepted for backwards compatibility: {violations}")
            self.assertEqual(len(violations), 0)

    def test_enforce_attribution_non_strict_returns_false_on_tamper(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Empty temp dir will fail verification; capture stderr to keep test output clean
            with io.StringIO() as buf, contextlib.redirect_stderr(buf):
                result = author_integrity.enforce_author_attribution(repo_root=tmp_dir, strict=False)
                self.assertFalse(result)
                self.assertIn("AUTHOR ATTRIBUTION & INTEGRITY VIOLATION DETECTED", buf.getvalue())

    def test_gate_0_in_verify_all(self):
        with io.StringIO() as buf, contextlib.redirect_stdout(buf):
            self.assertTrue(verify_all.gate_0_author_integrity(REPO_ROOT, mode="HUB"))
            self.assertTrue(verify_all.gate_0_author_integrity(REPO_ROOT, mode="TARGET"))

    def test_cryptographic_fingerprint_valid(self):
        self.assertTrue(author_integrity.verify_author_fingerprint())

    def test_assert_integrity_or_raise_passes_on_canonical_repo(self):
        self.assertTrue(author_integrity.assert_integrity_or_raise(REPO_ROOT))

    def test_cryptographic_fingerprint_mismatch_raises_runtime_error(self):
        orig_sig = author_integrity.CANONICAL_AUTHOR_SIG
        try:
            author_integrity.CANONICAL_AUTHOR_SIG = "0000000000000000000000000000000000000000000000000000000000000000"
            self.assertFalse(author_integrity.verify_author_fingerprint())
            with self.assertRaises(RuntimeError) as ctx:
                author_integrity.assert_integrity_or_raise(REPO_ROOT)
            self.assertIn("CRITICAL INTEGRITY CORRUPTED", str(ctx.exception))
        finally:
            author_integrity.CANONICAL_AUTHOR_SIG = orig_sig


    def test_verify_source_headers_passes_on_canonical_repo(self):
        valid, missing = author_integrity.verify_source_headers(REPO_ROOT)
        self.assertTrue(valid, f"Missing headers in repo files: {missing}")
        self.assertEqual(len(missing), 0)

    def test_verify_source_headers_detects_missing_in_temp_dir(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tools_dir = os.path.join(tmp_dir, "tools")
            os.makedirs(tools_dir, exist_ok=True)
            with open(os.path.join(tools_dir, "unattributed.py"), "w", encoding="utf-8") as f:
                f.write("def run():\n    pass\n")
            valid, missing = author_integrity.verify_source_headers(tmp_dir, scan_dirs=["tools"])
            self.assertFalse(valid)
            self.assertEqual(len(missing), 1)
            self.assertIn("unattributed.py", missing[0])

    def test_verify_source_headers_accepts_valid_spdx_in_temp_dir(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tools_dir = os.path.join(tmp_dir, "tools")
            os.makedirs(tools_dir, exist_ok=True)
            spdx_header = (
                "# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>\n"
                "# SPDX-License-Identifier: MIT\n"
                "def run():\n    pass\n"
            )
            with open(os.path.join(tools_dir, "attributed.py"), "w", encoding="utf-8") as f:
                f.write(spdx_header)
            valid, missing = author_integrity.verify_source_headers(tmp_dir, scan_dirs=["tools"])
            self.assertTrue(valid)
            self.assertEqual(len(missing), 0)

    def test_fork_provenance_blocks_unauthorized_third_party_fork(self):
        old_ci = os.environ.get("GITHUB_ACTIONS")
        old_repo = os.environ.get("GITHUB_REPOSITORY")
        old_salt = os.environ.get("SYNAPSE_AUTHOR_SALT")
        try:
            os.environ["GITHUB_ACTIONS"] = "true"
            os.environ["GITHUB_REPOSITORY"] = "unauthorized-stranger/synapse-hub-ripoff"
            os.environ.pop("SYNAPSE_AUTHOR_SALT", None)
            os.environ.pop("AUTHOR_INTEGRITY_SALT", None)

            ok, err = author_integrity.verify_remote_provenance_secret()
            self.assertFalse(ok)
            self.assertIn("FORK PROVENANCE VIOLATION", err)
            self.assertIn("SYNAPSE_AUTHOR_SALT", err)

            # When invalid random salt provided on fork, it is rejected
            os.environ["SYNAPSE_AUTHOR_SALT"] = "random_unauthorized_salt"
            ok_bad, err_bad = author_integrity.verify_remote_provenance_secret()
            self.assertFalse(ok_bad)
            self.assertIn("FORK PROVENANCE CORRUPTED", err_bad)

            # Even if attacker copies the digest string from the code, it is REJECTED
            os.environ["SYNAPSE_AUTHOR_SALT"] = author_integrity._PROVENANCE_DIGEST
            ok_digest_copy, err_digest_copy = author_integrity.verify_remote_provenance_secret()
            self.assertFalse(ok_digest_copy)
            self.assertIn("FORK PROVENANCE CORRUPTED", err_digest_copy)

            # When valid ephemeral test secret matching mocked digest is provided, it succeeds
            ephemeral_test_key = "ephemeral_mock_unit_test_secret_only"
            ephemeral_digest = hashlib.sha256((ephemeral_test_key + "::synapse_immutable_root").encode("utf-8")).hexdigest()
            with patch.object(author_integrity, "_PROVENANCE_DIGEST", ephemeral_digest):
                os.environ["SYNAPSE_AUTHOR_SALT"] = ephemeral_test_key
                ok_auth, err_auth = author_integrity.verify_remote_provenance_secret()
                self.assertTrue(ok_auth)
                self.assertIsNone(err_auth)
        finally:
            if old_ci is not None:
                os.environ["GITHUB_ACTIONS"] = old_ci
            else:
                os.environ.pop("GITHUB_ACTIONS", None)
            if old_repo is not None:
                os.environ["GITHUB_REPOSITORY"] = old_repo
            else:
                os.environ.pop("GITHUB_REPOSITORY", None)
            if old_salt is not None:
                os.environ["SYNAPSE_AUTHOR_SALT"] = old_salt
            else:
                os.environ.pop("SYNAPSE_AUTHOR_SALT", None)

    def test_fork_provenance_passes_on_canonical_repo(self):
        old_ci = os.environ.get("GITHUB_ACTIONS")
        old_repo = os.environ.get("GITHUB_REPOSITORY")
        try:
            os.environ["GITHUB_ACTIONS"] = "true"
            os.environ["GITHUB_REPOSITORY"] = "TeeVee98/Synapse-Hub"
            ok, err = author_integrity.verify_remote_provenance_secret()
            self.assertTrue(ok)
            self.assertIsNone(err)
        finally:
            if old_ci is not None:
                os.environ["GITHUB_ACTIONS"] = old_ci
            else:
                os.environ.pop("GITHUB_ACTIONS", None)
            if old_repo is not None:
                os.environ["GITHUB_REPOSITORY"] = old_repo
            else:
                os.environ.pop("GITHUB_REPOSITORY", None)


if __name__ == "__main__":
    unittest.main()
