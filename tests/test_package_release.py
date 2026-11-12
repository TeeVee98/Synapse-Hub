#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tests/test_package_release.py — Unit Tests for Enterprise Release Packaging
"""

import os
import sys
import tempfile
import unittest
import zipfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

import package_release


class TestPackageRelease(unittest.TestCase):
    """Verifies packaging logic, dot-dir preservation, and archive integrity checks."""

    def test_normalize_arcname(self):
        self.assertEqual(package_release.normalize_arcname("./.github/workflows/test.yml"), ".github/workflows/test.yml")
        self.assertEqual(package_release.normalize_arcname(".github/test.yml"), ".github/test.yml")
        self.assertEqual(package_release.normalize_arcname(r".github\workflows\test.yml"), ".github/workflows/test.yml")

    def test_collect_package_files_includes_mandatory_dot_dirs(self):
        files = package_release.collect_package_files(REPO_ROOT)
        rel_paths = [rel for _, rel in files]

        self.assertIn(".github/workflows/publish_npm.yml", rel_paths, "Mandatory publish_npm.yml must be included")
        self.assertIn(".github/workflows/nightly-mutation.yml", rel_paths, "Nightly mutation workflow must be included")
        self.assertIn("package.json", rel_paths)
        self.assertIn("LICENSE", rel_paths)

        # Assert excluded patterns are absent
        for path in rel_paths:
            self.assertFalse(path.startswith(".git/"), f"Excluded dir .git found in {path}")
            self.assertFalse("__pycache__" in path, f"__pycache__ found in {path}")
            self.assertFalse(path.endswith(".pyc"), f".pyc found in {path}")

    def test_verify_archive_integrity_valid_and_invalid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "test.zip")
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("package.json", "{}")
                zf.writestr("LICENSE", "MIT")
                zf.writestr("AGENTS.md", "# Test")
                zf.writestr("tools/verify_all.py", "# Test")
                zf.writestr("tools/hub_publisher.py", "# Test")
                zf.writestr("tools/security_scanner.py", "# Test")
                zf.writestr("tools/generate_sbom.py", "# Test")
                zf.writestr(".github/workflows/publish_npm.yml", "name: Test")
                zf.writestr(".github/workflows/security_audit.yml", "name: Test")

            valid, missing = package_release.verify_archive_integrity(zip_path)
            self.assertTrue(valid)
            self.assertEqual(missing, [])

            # Test missing file
            bad_zip_path = os.path.join(tmpdir, "bad.zip")
            with zipfile.ZipFile(bad_zip_path, "w") as zf:
                zf.writestr("package.json", "{}")

            valid_bad, missing_bad = package_release.verify_archive_integrity(bad_zip_path)
            self.assertFalse(valid_bad)
            self.assertIn(".github/workflows/publish_npm.yml", missing_bad)

    def test_pyproject_harmonized_metadata(self):
        """Verifies pyproject.toml package name is harmonized to synapse-hub with backward-compatible CLI aliases."""
        pyproject_path = os.path.join(REPO_ROOT, "pyproject.toml")
        self.assertTrue(os.path.isfile(pyproject_path), "pyproject.toml must exist")
        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()

        import re
        # Validate package name
        name_match = re.search(r'(?m)^name\s*=\s*["\']([^"\']+)["\']', content)
        self.assertIsNotNone(name_match, "pyproject.toml must declare package name")
        self.assertEqual(name_match.group(1), "synapse-hub")

        # Validate scripts aliases
        self.assertIn('agent-qa = "tools.cli:main"', content)
        self.assertIn('synapse = "tools.cli:main"', content)
        self.assertIn('synapse-hub = "tools.cli:main"', content)


if __name__ == "__main__":
    unittest.main()
