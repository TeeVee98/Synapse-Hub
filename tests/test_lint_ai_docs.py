#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_lint_ai_docs.py — Unit Tests for AI Documentation & Relative Link Sentinel
"""

import os
import re
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

    def test_client_mode_skips_hub_bilingual_doc_requirement(self):
        """P0-1: Client/Target projects with README.md only must not fail bilingual Hub doc gate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "tests").mkdir()
            (root / "playwright.config.ts").write_text("export default {};\n", encoding="utf-8")
            (root / "README.md").write_text("# Client Project\n\nSingle-language client README.\n", encoding="utf-8")

            lint_errors, _ = lint_ai_docs.lint_docs(tmpdir)
            self.assertEqual(lint_errors, [], f"Client mode must not require README.en.md: {lint_errors}")

    def test_hub_mode_still_enforces_bilingual_doc_requirement(self):
        """P0-1 Negative: Hub repository enforces bidirectional README.md <-> README.en.md parity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "tools" / "core").mkdir(parents=True)
            (root / "tools" / "core" / "verify_all.py").write_text("# hub marker\n", encoding="utf-8")
            (root / "skills_manifest.json").write_text('{"version": "4.8.3", "skills": []}\n', encoding="utf-8")

            # Neither file present -> no spurious bilingual error
            empty_errors, _ = lint_ai_docs.lint_docs(tmpdir)
            self.assertEqual(empty_errors, [])

            # Missing English counterpart
            (root / "README.md").write_text("# Hub Repo\n", encoding="utf-8")
            lint_errors, _ = lint_ai_docs.lint_docs(tmpdir)
            self.assertTrue(
                any("Missing English bilingual documentation counterpart for README.md" in e for e in lint_errors),
                f"Hub mode must enforce README.en.md parity: {lint_errors}",
            )

            # Missing Vietnamese counterpart
            (root / "README.md").unlink()
            (root / "README.en.md").write_text("# Hub Repo EN\n", encoding="utf-8")
            en_only_errors, _ = lint_ai_docs.lint_docs(tmpdir)
            self.assertTrue(
                any("Missing Vietnamese bilingual documentation counterpart for README.en.md" in e for e in en_only_errors),
                f"Hub mode must enforce README.md parity: {en_only_errors}",
            )

    def test_lint_docs_scans_skills_markdown_for_broken_tool_refs(self):
        """P1-3: lint_ai_docs scans skills/**/*.md and catches non-existent tool script references."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skill_md = root / "skills" / "01-web-automation" / "demo" / "SKILL.md"
            skill_md.parent.mkdir(parents=True)
            skill_md.write_text("# Demo Skill\n\nRun `python tools/definitely_missing_automation_tool.py`.\n", encoding="utf-8")

            docs = lint_ai_docs.find_doc_files(tmpdir)
            self.assertIn("skills/01-web-automation/demo/SKILL.md", docs)
            lint_errors, _ = lint_ai_docs.lint_docs(tmpdir)
            self.assertTrue(
                any("definitely_missing_automation_tool.py" in e for e in lint_errors),
                f"Expected missing tool error in skills/: {lint_errors}",
            )

    def test_live_automation_skills_have_zero_broken_refs_and_valid_waits(self):
        """P1-3: Automation SKILL.md files have zero broken refs and no prescriptive networkidle/wait_for_timeout."""
        repo_root = Path(__file__).resolve().parent.parent
        domains = (
            "01-web-automation",
            "03-api-and-contracts",
            "06-healing-and-resilience",
            "07-data-and-state",
            "09-ci-and-devops",
        )
        ref_pat = re.compile(
            r"(?:tools/[a-zA-Z0-9_./-]+|automation/[a-zA-Z0-9_./-]+|testing/[a-zA-Z0-9_./-]+|\.agents/skills/[a-zA-Z0-9_./-]+|skills/[0-9]+-[a-zA-Z0-9_./-]+)"
        )
        wait_pat = re.compile(r"networkidle|wait_for_timeout|waitForTimeout")
        missing_refs = []
        bad_waits = []
        for domain in domains:
            base = repo_root / "skills" / domain
            for file_path in base.rglob("*"):
                if file_path.suffix not in (".md", ".sh", ".py", ".ts", ".js", ".groovy"):
                    continue
                if file_path.parent.name == "references" and file_path.name in ("recipes.md", "advanced_superpowers.md"):
                    continue
                rel = file_path.relative_to(repo_root).as_posix()
                for line_no, line in enumerate(file_path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    for m in ref_pat.finditer(line):
                        ref = m.group(0).rstrip(".,:;`)'\"")
                        if "<" in ref or "*" in ref or "example" in ref or ref.endswith("/"):
                            continue
                        if not (repo_root / ref).exists():
                            missing_refs.append(f"{rel}:{line_no} -> {ref}")
                    if wait_pat.search(line) and not any(
                        kw in line.lower() for kw in ("prohibit", "avoid", "ban", "never", "anti-pattern", "do not", "instead of", "replaced with", "0 static")
                    ):
                        bad_waits.append(f"{rel}:{line_no} -> {line.strip()}")

        self.assertEqual(missing_refs, [], f"Broken path references remain: {missing_refs}")
        self.assertEqual(bad_waits, [], f"Prescriptive wait anti-patterns remain: {bad_waits}")

        webapp_skill = (repo_root / "skills" / "01-web-automation" / "playwright-webapp-testing" / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("page.getByRole('heading', { name: 'Dashboard' })", webapp_skill)


if __name__ == "__main__":
    unittest.main()
