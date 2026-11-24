#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_lint_ai_docs.py — Unit Tests for AI Documentation & Relative Link Sentinel
"""

import os
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "lint"))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

import lint_ai_docs


class TestLintAiDocsRelativeLinks(unittest.TestCase):
    """Tests relative Markdown link checking, metric consistency, and boundary resilience."""

    def test_valid_relative_external_and_anchor_links(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "docs").mkdir()
            (root / "assets").mkdir()
            (root / "notes.txt").write_text("[BrokenInTxt](missing.md)\n", encoding="utf-8")
            (root / "CHANGELOG.md").write_text("[IgnoredChangelog](missing.md)\n", encoding="utf-8")
            (root / "docs" / "subdir.md").mkdir()
            (root / "docs" / "guide.md").write_text("# Guide\n\n[Home](../README.md)\n", encoding="utf-8")
            (root / "assets" / "logo.png").write_bytes(b"PNG")
            (root / "README.en.md").write_text("# Title\n\n[Guide](docs/guide.md)\n", encoding="utf-8")
            (root / "README.md").write_text(
                "# Title\n\n"
                "[Guide](docs/guide.md)\n"
                "[GuideAnchor](docs/guide.md#intro)\n"
                "[Guide Section](<docs/guide.md?v=1#intro> \"Guide Title\")\n"
                "![Logo](assets/logo.png)\n"
                "[Repo](HTTPS://github.com/TeeVee98/Synapse-Hub)\n"
                "[HTTP](http://example.com)\n"
                "[Mail](mailto:qa@example.com)\n"
                "[Anchor](#title)\n",
                encoding="utf-8",
            )

            checker = getattr(lint_ai_docs, "check_markdown_relative_links", None)
            self.assertIsNotNone(checker, "check_markdown_relative_links must exist in lint_ai_docs")

            errors = checker(tmpdir)
            self.assertEqual(errors, [])

            link_dto_cls = getattr(lint_ai_docs, "BrokenMarkdownLinkDTO", None)
            self.assertIsNotNone(link_dto_cls, "BrokenMarkdownLinkDTO must exist in lint_ai_docs")
            link_dto = link_dto_cls(source_doc="README.md", line_number=1, link_label="G", target_path="docs/guide.md")
            with self.assertRaises(FrozenInstanceError):
                link_dto.line_number = 2  # type: ignore[misc]

            dto_cls = getattr(lint_ai_docs, "EntryDocAuditResultDTO", None)
            self.assertIsNotNone(dto_cls, "EntryDocAuditResultDTO must exist in lint_ai_docs")
            audit_dto = dto_cls(checked_docs=["README.md", "docs/guide.md"])
            self.assertEqual(audit_dto.broken_links, [])
            with self.assertRaises(FrozenInstanceError):
                audit_dto.checked_docs = []  # type: ignore[misc]

            lint_errors, _ = lint_ai_docs.lint_docs(tmpdir)
            self.assertEqual(lint_errors, [])

    def test_broken_relative_links_detected_with_line_and_target(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "docs").mkdir()
            (root / "README.en.md").write_text("# Title\n", encoding="utf-8")
            (root / "README.md").write_text(
                "# Title\n\n"
                "Download [VSIX](editors/vscode/dist/missing.vsix) now.\n"
                "```bash\n"
                "[InsideFence](ignored.md)\n"
                "```\n"
                "After fence: [BrokenAfterFence](still_missing.md).\n",
                encoding="utf-8",
            )
            (root / "docs" / "guide.md").write_text(
                "# Guide\n"
                "See [Missing](../nonexistent.md#sec).\n",
                encoding="utf-8",
            )

            checker = getattr(lint_ai_docs, "check_markdown_relative_links", None)
            self.assertIsNotNone(checker, "check_markdown_relative_links must exist in lint_ai_docs")

            errors = checker(tmpdir)
            self.assertEqual(len(errors), 3)
            self.assertTrue(
                any(
                    "README.md:3" in e and "'[VSIX](editors/vscode/dist/missing.vsix)'" in e
                    for e in errors
                ),
                f"Expected README.md:3 exact broken VSIX link error, got: {errors}",
            )
            self.assertTrue(
                any("README.md:7" in e and "still_missing.md" in e for e in errors),
                f"Expected README.md:7 broken link after fence, got: {errors}",
            )
            self.assertTrue(
                any("docs/guide.md:2" in e and "../nonexistent.md" in e for e in errors),
                f"Expected docs/guide.md:2 broken link error, got: {errors}",
            )

            lint_errors, _ = lint_ai_docs.lint_docs(tmpdir)
            self.assertTrue(
                any("editors/vscode/dist/missing.vsix" in e for e in lint_errors),
                f"Expected lint_docs() to propagate broken relative link, got: {lint_errors}",
            )

    def test_broken_obsolete_metrics_detected_with_skills_and_recursive_tools(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skill_dir = root / "skills" / "01-web" / "clean-pom"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: clean-pom\n---\n", encoding="utf-8")
            # Non-skill directory (no SKILL.md) and file should not increment count
            (root / "skills" / "readme.txt").write_text("info", encoding="utf-8")
            (root / "skills" / "01-web" / "empty-dir").mkdir()

            nested_tool_dir = root / "tools" / "core"
            nested_tool_dir.mkdir(parents=True)
            (nested_tool_dir / "__init__.py").write_text("", encoding="utf-8")
            (nested_tool_dir / "verify_all.py").write_text("# tool\n", encoding="utf-8")
            (nested_tool_dir / "cli.py").write_text("# tool\n", encoding="utf-8")
            pycache = root / "tools" / "__pycache__"
            pycache.mkdir()
            (pycache / "cached.py").write_text("# ignored\n", encoding="utf-8")

            (root / "README.md").write_text(
                "# Repo\nWe have 50 skills and 60 tools.\n",
                encoding="utf-8",
            )

            errors = lint_ai_docs.check_doc_metrics_consistency(tmpdir)
            self.assertEqual(len(errors), 2)
            self.assertTrue(any("real count: 1" in e for e in errors), f"Expected real skill count 1: {errors}")
            self.assertTrue(any("real count: 2" in e for e in errors), f"Expected real recursive tool count 2: {errors}")

        # Fallback to .agents/skills when skills/ is absent
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            fallback_skill = root / ".agents" / "skills" / "solo" / "solo-runner"
            fallback_skill.mkdir(parents=True)
            (fallback_skill / "SKILL.md").write_text("---\nname: solo-runner\n---\n", encoding="utf-8")
            (root / "README.en.md").write_text("# Repo\n50 skills.\n", encoding="utf-8")

            errors = lint_ai_docs.check_doc_metrics_consistency(tmpdir)
            self.assertEqual(len(errors), 1)
            self.assertIn("real count: 1", errors[0])

        # Tools-only repo (missing skills/) reports real skill count: 0
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "tools").mkdir()
            (root / "tools" / "helper.py").write_text("# tool\n", encoding="utf-8")
            (root / "README.md").write_text("# Repo\n50 skills.\n", encoding="utf-8")

            errors = lint_ai_docs.check_doc_metrics_consistency(tmpdir)
            self.assertEqual(len(errors), 1)
            self.assertIn("real count: 0", errors[0])

        # Obsolete gate count (9 or 10) rejected while 11 gates accepted
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "tools").mkdir()
            (root / "tools" / "helper.py").write_text("# tool\n", encoding="utf-8")
            (root / "README.md").write_text("# Repo\n10 Cổng Chất Lượng.\n11 Cổng Chất Lượng.\n", encoding="utf-8")
            (root / "README.en.md").write_text("# Repo\n10 Quality Gates.\n11 Quality Gates.\n", encoding="utf-8")

            errors = lint_ai_docs.check_doc_metrics_consistency(tmpdir)
            self.assertEqual(len(errors), 2)
            self.assertTrue(any("11 Cổng Chất Lượng DoD (Gate 1–11)" in e for e in errors), f"Got: {errors}")
            self.assertTrue(any("11 Quality Gates DoD (Gate 1–11)" in e for e in errors), f"Got: {errors}")

    def test_boundary_empty_docs_missing_skills_and_fenced_code_ignored(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "docs").mkdir()
            (root / "README.md").write_text(
                "# Boundary\n\n"
                "```markdown\n"
                "[FencedBroken](missing_in_fence.md)\n"
                "```\n\n"
                "~~~\n"
                "[TildeBroken](missing_in_tilde.md)\n"
                "~~~\n\n"
                "Inline `[InlineBroken](missing_inline.md)` example.\n"
                "[EmptyTarget]()\n"
                "[WhitespaceTarget](   )\n"
                "[FragmentOnly](#local-anchor)\n",
                encoding="utf-8",
            )

            checker = getattr(lint_ai_docs, "check_markdown_relative_links", None)
            self.assertIsNotNone(checker, "check_markdown_relative_links must exist in lint_ai_docs")

            errors = checker(tmpdir)
            self.assertEqual(errors, [])

            # Missing optional doc_paths should not crash
            self.assertEqual(checker(tmpdir, doc_paths=["missing_doc.md"]), [])

            # Missing skills/ and tools/ should not crash metrics checker
            metric_errors = lint_ai_docs.check_doc_metrics_consistency(tmpdir)
            self.assertEqual(metric_errors, [])


if __name__ == "__main__":
    unittest.main()
