#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_bump_version.py — Unit Tests for Atomic Universal Version Bumper
"""

import io
import os
import sys
import json
import unittest
import tempfile
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

import bump_version


class TestBumpVersion(unittest.TestCase):
    """Tests semantic versioning and atomic rollback in bump_version."""

    def test_parse_semver_valid(self):
        self.assertEqual(bump_version.parse_semver("1.2.3"), (1, 2, 3, ""))
        self.assertEqual(bump_version.parse_semver("3.4.0-rc1"), (3, 4, 0, "-rc1"))

    def test_parse_semver_invalid(self):
        with self.assertRaises(ValueError):
            bump_version.parse_semver("invalid-version")
        with self.assertRaises(ValueError):
            bump_version.parse_semver("1.2")

    def test_calculate_next_version(self):
        self.assertEqual(bump_version.calculate_next_version("3.4.0", "patch"), "3.4.1")
        self.assertEqual(bump_version.calculate_next_version("3.4.0", "minor"), "3.5.0")
        self.assertEqual(bump_version.calculate_next_version("3.4.0", "major"), "4.0.0")
        self.assertEqual(bump_version.calculate_next_version("3.4.0", "3.4.5"), "3.4.5")

    def test_rollback_mechanism(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("ORIGINAL_CONTENT")

            # Setup snapshot
            bump_version.ORIGINAL_SNAPSHOTS[test_file] = "ORIGINAL_CONTENT"

            # Mutate file
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("MUTATED_CONTENT")
            self.assertEqual(open(test_file, "r", encoding="utf-8").read(), "MUTATED_CONTENT")

            # Rollback
            bump_version.rollback_all_files()
            self.assertEqual(open(test_file, "r", encoding="utf-8").read(), "ORIGINAL_CONTENT")

            # Clean snapshot dict
            bump_version.ORIGINAL_SNAPSHOTS.clear()

    @patch("subprocess.run")
    def test_run_tests_success(self, mock_run):
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_run.return_value = mock_res
        self.assertTrue(bump_version.run_tests())

    @patch("subprocess.run")
    def test_run_tests_failure(self, mock_run):
        mock_res = MagicMock()
        mock_res.returncode = 1
        mock_run.return_value = mock_res
        self.assertFalse(bump_version.run_tests())

    @patch("subprocess.run")
    def test_git_commit_and_tag_tag_exists_reuses_cleanly(self, mock_run):
        # 1. git status (clean)
        res_status = MagicMock(returncode=0, stdout="")
        # 2. git add -u
        res_add = MagicMock(returncode=0)
        # 3. git commit
        res_commit = MagicMock(returncode=0)
        # 4. git tag -l returning existing tag
        res_tag_l = MagicMock(returncode=0, stdout="v3.5.0\n")

        mock_run.side_effect = [res_status, res_add, res_commit, res_tag_l]

        bump_version.git_commit_and_tag("3.5.0", push=False)
        # Verify git tag creation was NOT called (4 calls total)
        self.assertEqual(mock_run.call_count, 4)

    def _create_temp_bump_repo(self, root: Path, create_vsix: bool = False) -> None:
        (root / "package.json").write_text(json.dumps({"name": "synapse-hub", "version": "4.8.1"}), encoding="utf-8")
        (root / "editors" / "vscode").mkdir(parents=True, exist_ok=True)
        (root / "editors" / "vscode" / "README.md").write_text(
            "Install [VSIX](dist/synapse-hub-vscode-4.7.2.vsix).\n",
            encoding="utf-8",
        )
        badges_dir = root / "docs" / "badges"
        badges_dir.mkdir(parents=True, exist_ok=True)
        (badges_dir / "npm-version.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="88" height="20" role="img" aria-label="npm: v4.8.1">'
            '<title>npm: v4.8.1</title><g shape-rendering="crispEdges"><rect width="35" height="20" fill="#555"/>'
            '<rect x="35" width="53" height="20" fill="#007ec6"/></g>'
            '<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" '
            'text-rendering="geometricPrecision" font-size="110">'
            '<text x="185" y="140" textLength="250" transform="scale(.1)">npm</text>'
            '<text x="605" y="140" textLength="430" transform="scale(.1)">v4.8.1</text></g></svg>\n',
            encoding="utf-8",
        )
        (badges_dir / "vscode-marketplace.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="180" height="20" role="img" aria-label="VS Code Marketplace: v4.8.1">'
            '<title>VS Code Marketplace: v4.8.1</title><g shape-rendering="crispEdges"><rect width="127" height="20" fill="#555"/>'
            '<rect x="127" width="53" height="20" fill="#007ec6"/></g>'
            '<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" '
            'text-rendering="geometricPrecision" font-size="110">'
            '<text x="645" y="140" textLength="1170" transform="scale(.1)">VS Code Marketplace</text>'
            '<text x="1525" y="140" textLength="430" transform="scale(.1)">v4.8.1</text></g></svg>\n',
            encoding="utf-8",
        )
        (root / "README.md").write_text(
            "[![npm version](docs/badges/npm-version.svg)](https://www.npmjs.com/package/@teevee98/synapse-hub)\n"
            "[![VS Code Marketplace](docs/badges/vscode-marketplace.svg)](https://marketplace.visualstudio.com/items?itemName=Teevee98.synapse-hub-vscode)\n"
            "> **Phiên bản:** `v4.8.1`\n"
            "VSIX: editors/vscode/dist/synapse-hub-vscode-4.7.2.vsix\n"
            "  uses: TeeVee98/Synapse-Hub@v4.8.1\n"
            "    rev: v4.8.1\n",
            encoding="utf-8",
        )
        (root / "README.en.md").write_text(
            "[![npm version](docs/badges/npm-version.svg)](https://www.npmjs.com/package/@teevee98/synapse-hub)\n"
            "[![VS Code Marketplace](docs/badges/vscode-marketplace.svg)](https://marketplace.visualstudio.com/items?itemName=Teevee98.synapse-hub-vscode)\n"
            "> **Version:** `v4.8.1`\n"
            "VSIX: editors/vscode/dist/synapse-hub-vscode-4.7.2.vsix\n"
            "  uses: TeeVee98/Synapse-Hub@v4.8.1\n"
            "    rev: v4.8.1\n",
            encoding="utf-8",
        )
        if create_vsix:
            dist_dir = root / "editors" / "vscode" / "dist"
            dist_dir.mkdir(parents=True)
            (dist_dir / "synapse-hub-vscode-4.8.2.vsix").write_bytes(b"VSIX")

    def test_vsix_guard_skips_rewrite_when_artifact_absent(self):
        update_vsix = getattr(bump_version, "update_vsix_links", None)
        dto_cls = getattr(bump_version, "VsixBumpDecisionDTO", None)
        self.assertIsNotNone(update_vsix, "update_vsix_links must exist in bump_version")
        self.assertIsNotNone(dto_cls, "VsixBumpDecisionDTO must exist in bump_version")

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._create_temp_bump_repo(root, create_vsix=False)
            orig_root = bump_version.REPO_ROOT
            bump_version.REPO_ROOT = tmpdir
            bump_version.ORIGINAL_SNAPSHOTS.clear()
            try:
                buf = io.StringIO()
                with redirect_stdout(buf):
                    decision = update_vsix("4.8.2", dry_run=False)

                self.assertIsInstance(decision, dto_cls)
                self.assertEqual(decision.target_version, "4.8.2")
                self.assertEqual(decision.vsix_path, "editors/vscode/dist/synapse-hub-vscode-4.8.2.vsix")
                self.assertFalse(decision.artifact_exists)
                self.assertFalse(decision.rewritten)
                self.assertIn("[WARN]", buf.getvalue())
                with self.assertRaises(FrozenInstanceError):
                    decision.rewritten = True  # type: ignore[misc]

                self.assertIn("4.7.2.vsix", (root / "README.md").read_text(encoding="utf-8"))
                self.assertIn("4.7.2.vsix", (root / "README.en.md").read_text(encoding="utf-8"))
                self.assertIn("4.7.2.vsix", (root / "editors" / "vscode" / "README.md").read_text(encoding="utf-8"))

                with patch.object(sys, "argv", ["bump_version.py", "4.8.2", "--no-test"]):
                    bump_version.main()

                readme_vi = (root / "README.md").read_text(encoding="utf-8")
                readme_en = (root / "README.en.md").read_text(encoding="utf-8")
                self.assertIn("4.7.2.vsix", readme_vi)
                self.assertIn("4.7.2.vsix", readme_en)
                self.assertIn("uses: TeeVee98/Synapse-Hub@v4.8.2", readme_vi)
                self.assertIn("uses: TeeVee98/Synapse-Hub@v4.8.2", readme_en)
            finally:
                bump_version.REPO_ROOT = orig_root
                bump_version.ORIGINAL_SNAPSHOTS.clear()

    def test_vsix_guard_rewrites_when_artifact_present_and_updates_action_pins(self):
        update_vsix = getattr(bump_version, "update_vsix_links", None)
        update_pins = getattr(bump_version, "update_readme_action_pins", None)
        self.assertIsNotNone(update_vsix, "update_vsix_links must exist in bump_version")
        self.assertIsNotNone(update_pins, "update_readme_action_pins must exist in bump_version")

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._create_temp_bump_repo(root, create_vsix=True)
            orig_root = bump_version.REPO_ROOT
            bump_version.REPO_ROOT = tmpdir
            bump_version.ORIGINAL_SNAPSHOTS.clear()
            try:
                dry_decision = update_vsix("4.8.2", dry_run=True)
                self.assertTrue(dry_decision.artifact_exists)
                self.assertTrue(dry_decision.rewritten)
                self.assertIn("4.7.2.vsix", (root / "README.md").read_text(encoding="utf-8"))

                # Default dry_run=False must write to disk
                decision = update_vsix("4.8.2")
                self.assertTrue(decision.artifact_exists)
                self.assertTrue(decision.rewritten)
                self.assertIn("4.8.2.vsix", (root / "README.md").read_text(encoding="utf-8"))
                self.assertIn("4.8.2.vsix", (root / "README.en.md").read_text(encoding="utf-8"))
                self.assertIn("4.8.2.vsix", (root / "editors" / "vscode" / "README.md").read_text(encoding="utf-8"))

                # Default dry_run=False must update action pins even if only one README needs updating
                (root / "README.en.md").write_text(
                    (root / "README.en.md").read_text(encoding="utf-8").replace("@v4.8.1", "@v4.8.2"),
                    encoding="utf-8",
                )
                self.assertTrue(update_pins("4.8.2"))
                self.assertIn("uses: TeeVee98/Synapse-Hub@v4.8.2", (root / "README.md").read_text(encoding="utf-8"))
                self.assertIn("uses: TeeVee98/Synapse-Hub@v4.8.2", (root / "README.en.md").read_text(encoding="utf-8"))
                self.assertFalse(update_pins("4.8.2"))

                # Verify main() invokes update_vsix_links when VSIX artifact exists
                self._create_temp_bump_repo(root, create_vsix=False)
                with patch.object(sys, "argv", ["bump_version.py", "4.8.2", "--no-test"]):
                    bump_version.main()
                self.assertIn("4.8.2.vsix", (root / "README.md").read_text(encoding="utf-8"))
                self.assertIn("4.8.2.vsix", (root / "README.en.md").read_text(encoding="utf-8"))
            finally:
                bump_version.REPO_ROOT = orig_root
                bump_version.ORIGINAL_SNAPSHOTS.clear()

    def test_readme_version_badges_four_scenarios(self):
        """Positive, Negative, Boundary, and Resilience scenarios for local SVG badges."""
        update_badges = getattr(bump_version, "update_readme_version_badges", None)
        self.assertIsNotNone(update_badges, "update_readme_version_badges must exist in bump_version")

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._create_temp_bump_repo(root, create_vsix=False)
            orig_root = bump_version.REPO_ROOT
            bump_version.REPO_ROOT = tmpdir
            bump_version.ORIGINAL_SNAPSHOTS.clear()
            try:
                npm_svg = root / "docs" / "badges" / "npm-version.svg"
                vsc_svg = root / "docs" / "badges" / "vscode-marketplace.svg"

                # Boundary: dry_run=True detects change without writing to disk
                self.assertTrue(update_badges("4.8.2", dry_run=True))
                self.assertIn("v4.8.1", npm_svg.read_text(encoding="utf-8"))

                # Negative: invalid or empty version raises ValueError cleanly
                with self.assertRaises(ValueError):
                    update_badges("")
                with self.assertRaises(ValueError):
                    update_badges("invalid-ver")

                # Positive: updates both local SVG badges via main()
                with patch.object(sys, "argv", ["bump_version.py", "4.8.2", "--no-test"]):
                    bump_version.main()

                for svg_path, prefix in ((npm_svg, "npm: v4.8.2"), (vsc_svg, "VS Code Marketplace: v4.8.2")):
                    txt = svg_path.read_text(encoding="utf-8")
                    self.assertIn(prefix, txt)
                    self.assertIn(">v4.8.2</text>", txt)
                    self.assertNotIn("v4.8.1", txt)

                # Boundary: idempotent re-run returns False & prerelease suffix updates cleanly
                self.assertFalse(update_badges("4.8.2"))
                self.assertTrue(update_badges("4.9.0-rc1"))
                self.assertIn(">v4.9.0-rc1</text>", npm_svg.read_text(encoding="utf-8"))
                self.assertIn("VS Code Marketplace: v4.9.0-rc1", vsc_svg.read_text(encoding="utf-8"))

                # Resilience: missing local badge SVGs return False without crashing
                npm_svg.unlink()
                vsc_svg.unlink()
                self.assertFalse(update_badges("4.9.1"))
            finally:
                bump_version.REPO_ROOT = orig_root
                bump_version.ORIGINAL_SNAPSHOTS.clear()


if __name__ == "__main__":
    unittest.main()
