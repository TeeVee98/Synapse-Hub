#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tests/test_git_pre_commit_guard.py — Tests for Git Pre-Commit Guard (SEC-04 / Feature 23)
Validates secret scanning (Gate 6 patterns, allowlists, diff parsing) and author integrity pre-flight.
"""

import os
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "tools"))

import git_pre_commit_guard


class TestGitPreCommitGuard(unittest.TestCase):
    """Test suite for pre-commit secret scanning and author checks."""

    def test_check_secrets_detects_github_pat_in_diff(self):
        dummy_pat = "gh" + "p_" + ("1234567890" * 3) + "123456"
        diff_text = f"""diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -1,3 +1,4 @@
 import os
+GH_TOKEN = "{dummy_pat}"
 def run(): pass
"""
        violations = git_pre_commit_guard.check_secrets(diff_text=diff_text)
        self.assertGreaterEqual(len(violations), 1)
        self.assertEqual(violations[0][0], "src/app.py")
        self.assertIn("GitHub Personal Access Token", violations[0][2])

    def test_check_secrets_detects_aws_key_in_diff(self):
        dummy_aws = "AK" + "IA" + "IOSFODNN7EXAMPLE"
        diff_text = f"""diff --git a/config.py b/config.py
--- a/config.py
+++ b/config.py
@@ -1,2 +1,3 @@
+AWS_KEY = "{dummy_aws}"
"""
        violations = git_pre_commit_guard.check_secrets(diff_text=diff_text)
        self.assertGreaterEqual(len(violations), 1)
        self.assertIn("AWS Access Key ID", violations[0][2])

    def test_check_secrets_detects_stripe_key_in_diff(self):
        dummy_stripe = "sk_" + "live_" + "1234567890abcdef1234567890"
        diff_text = f"""diff --git a/billing.py b/billing.py
--- a/billing.py
+++ b/billing.py
@@ -1,2 +1,3 @@
+STRIPE_KEY = "{dummy_stripe}"
"""
        violations = git_pre_commit_guard.check_secrets(diff_text=diff_text)
        self.assertGreaterEqual(len(violations), 1)
        self.assertIn("Stripe Secret Key", violations[0][2])

    def test_check_secrets_detects_private_key_in_diff(self):
        diff_text = """diff --git a/certs/key.pem b/certs/key.pem
--- a/certs/key.pem
+++ b/certs/key.pem
@@ -0,0 +1,3 @@
+-----BEGIN RSA PRIVATE KEY-----
+MIIEowIBAAKCAQEA0...
+-----END RSA PRIVATE KEY-----
"""
        violations = git_pre_commit_guard.check_secrets(diff_text=diff_text)
        self.assertGreaterEqual(len(violations), 1)
        self.assertIn("Private Key Header", violations[0][2])

    def test_check_secrets_honors_gate6_allowlist_in_diff(self):
        dummy_pat = "gh" + "p_" + ("1234567890" * 3) + "123456"
        diff_text = f"""diff --git a/tests/fixture.py b/tests/fixture.py
--- a/tests/fixture.py
+++ b/tests/fixture.py
@@ -1,2 +1,3 @@
+DUMMY_TOKEN = "{dummy_pat}"  # gate6-allowlist: synthetic test fixture
"""
        violations = git_pre_commit_guard.check_secrets(diff_text=diff_text)
        self.assertEqual(len(violations), 0)

    def test_check_secrets_on_files_detects_secret_and_allows_gate6(self):
        dummy_pat = "gh" + "p_" + ("1234567890" * 3) + "123456"
        with tempfile.TemporaryDirectory() as td:
            bad_file = os.path.join(td, "bad.py")
            with open(bad_file, "w", encoding="utf-8") as f:
                f.write(f'API_KEY = "{dummy_pat}"\\n')

            good_file = os.path.join(td, "good.py")
            with open(good_file, "w", encoding="utf-8") as f:
                f.write(f'API_KEY = "{dummy_pat}"  # gate6-allowlist: test\\n')

            clean_file = os.path.join(td, "clean.py")
            with open(clean_file, "w", encoding="utf-8") as f:
                f.write('def get_key(): return os.environ.get("API_KEY")\n')

            # bad_file has violation
            v_bad = git_pre_commit_guard.check_secrets(files=[bad_file])
            self.assertEqual(len(v_bad), 1)
            self.assertEqual(v_bad[0][0], bad_file)

            # good_file with allowlist has 0 violations
            v_good = git_pre_commit_guard.check_secrets(files=[good_file])
            self.assertEqual(len(v_good), 0)

            # clean_file has 0 violations
            v_clean = git_pre_commit_guard.check_secrets(files=[clean_file])
            self.assertEqual(len(v_clean), 0)

    def test_check_author_integrity_detects_missing_headers(self):
        with tempfile.TemporaryDirectory() as td:
            missing_header_file = os.path.join(td, "script.py")
            with open(missing_header_file, "w", encoding="utf-8") as f:
                f.write('print("hello world")\n')

            valid_header_file = os.path.join(td, "valid.py")
            with open(valid_header_file, "w", encoding="utf-8") as f:
                f.write('# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>\n# SPDX-License-Identifier: MIT\nprint("hello")\n')

            v_missing = git_pre_commit_guard.check_author_integrity([missing_header_file])
            self.assertEqual(len(v_missing), 1)
            self.assertIn("Missing mandatory SPDX author header", v_missing[0])

            v_valid = git_pre_commit_guard.check_author_integrity([valid_header_file])
            self.assertEqual(len(v_valid), 0)

    def test_check_no_verify_attempt(self):
        self.assertFalse(git_pre_commit_guard.check_no_verify_attempt(["--no-verify"]))
        self.assertFalse(git_pre_commit_guard.check_no_verify_attempt(["-n"]))
        self.assertTrue(git_pre_commit_guard.check_no_verify_attempt(["-m", "feat: my commit"]))


if __name__ == "__main__":
    unittest.main()
