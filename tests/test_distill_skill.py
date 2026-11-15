#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
tests/test_distill_skill.py — Unit tests for Dual-Skill Distillation Engine
"""

import io
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from tools.distill_skill import (
    distill_file,
    distill_skill,
    main,
    parse_frontmatter,
    split_markdown_sections,
)


class TestDistillSkill(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_distill_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_parse_frontmatter(self):
        content = "---\nname: sample-skill\ndescription: A test skill\n---\n# Heading\nContent here."
        meta, body = parse_frontmatter(content)
        self.assertEqual(meta.get("name"), "sample-skill")
        self.assertEqual(meta.get("description"), "A test skill")
        self.assertIn("# Heading", body)

    def test_parse_frontmatter_missing(self):
        content = "# Just markdown\nNo frontmatter here."
        meta, body = parse_frontmatter(content)
        self.assertEqual(meta, {})
        self.assertEqual(body, content)

    def test_split_markdown_sections_code_block_comments(self):
        doc = (
            "# Main Heading\n\n"
            "Here is some python code:\n"
            "```python\n"
            "# This is a python comment, NOT a markdown heading\n"
            "## Nor is this a subheading\n"
            "x = 42\n"
            "```\n\n"
            "## Real Subheading\n"
            "Code explanation.\n"
        )
        sections = split_markdown_sections(doc)
        section_titles = [title for title, _ in sections]
        self.assertEqual(section_titles, ["Main Heading", "Real Subheading"])
        main_content = sections[0][1]
        self.assertIn("# This is a python comment, NOT a markdown heading", main_content)
        self.assertIn("## Nor is this a subheading", main_content)
        self.assertNotIn("This is a python comment", section_titles)

    def test_distill_skill_separation(self):
        sample_doc = (
            "---\n"
            "name: test-runner-pro\n"
            "description: Automated headless runner\n"
            "---\n\n"
            "# 1. Persona and Communication Style\n"
            "Emit badge: > 🛡️ Synapse Active.\n"
            "Maintain senior dev mindset and doubt-driven falsification.\n\n"
            "# 2. CLI Execution Commands\n"
            "Run headless suite:\n"
            "```bash\n"
            "python3 tools/verify_all.py --fast\n"
            "```\n"
            "Verify all 10 Quality Gates pass with exit code 0.\n\n"
            "# 3. Shared Overview Architecture\n"
            "Common guidelines applicable across both operational and persona domains.\n"
        )
        work_md, persona_md = distill_skill(sample_doc, base_name="test-runner")

        # Positive assertions
        self.assertIn("type: procedural_work_skill", work_md)
        self.assertIn("python3 tools/verify_all.py", work_md)
        self.assertIn("type: cognitive_persona_skill", persona_md)
        self.assertIn("senior dev mindset", persona_md)

        # Negative assertions (falsification & separation verification)
        self.assertNotIn("verify_all.py", persona_md)
        self.assertNotIn("senior dev mindset", work_md)

        # Shared section should be present in both outputs
        self.assertIn("Shared Overview Architecture", work_md)
        self.assertIn("Shared Overview Architecture", persona_md)

    def test_distill_file_output(self):
        sample_file = os.path.join(self.test_dir, "ORIGINAL_SKILL.md")
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write(
                "---\nname: api-gatekeeper\ndescription: API Sentinel\n---\n"
                "# Role & Mindset\nBe skeptical and concise.\n\n"
                "# CLI Verification\n```bash\npytest tests/test_api.py\n```\n"
            )

        work_path, persona_path = distill_file(sample_file, self.test_dir)
        self.assertTrue(os.path.isfile(work_path))
        self.assertTrue(os.path.isfile(persona_path))

        with open(work_path, "r", encoding="utf-8") as f:
            w_content = f.read()
        self.assertIn("pytest tests/test_api.py", w_content)

    def test_distill_file_default_output_dir(self):
        sub_dir = os.path.join(self.test_dir, "sub")
        os.makedirs(sub_dir, exist_ok=True)
        sample_file = os.path.join(sub_dir, "SAMPLE_SKILL.md")
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write(
                "# Mindset\nSenior dev tone.\n\n"
                "# Workflow Step\n```bash\npytest\n```\n"
            )

        work_path, persona_path = distill_file(sample_file)
        self.assertEqual(work_path, os.path.join(sub_dir, "work_skill.md"))
        self.assertEqual(persona_path, os.path.join(sub_dir, "persona_skill.md"))
        self.assertTrue(os.path.isfile(work_path))
        self.assertTrue(os.path.isfile(persona_path))

    def test_distill_file_not_found(self):
        non_existent = os.path.join(self.test_dir, "non_existent.md")
        with self.assertRaises(FileNotFoundError):
            distill_file(non_existent)

    def test_main_cli(self):
        sample_file = os.path.join(self.test_dir, "CLI_SKILL.md")
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write(
                "# CLI Workflow\nExecute tests.\n\n"
                "# Persona Style\nFriendly tone.\n"
            )

        cli_out = os.path.join(self.test_dir, "cli_out")
        test_argv = ["distill_skill.py", sample_file, "--out-dir", cli_out]

        with patch("sys.argv", test_argv), patch("sys.stdout", new=io.StringIO()) as fake_stdout:
            exit_code = main()
            self.assertEqual(exit_code, 0)
            output = fake_stdout.getvalue()
            self.assertIn("Successfully distilled dual skills", output)

        self.assertTrue(os.path.isfile(os.path.join(cli_out, "work_skill.md")))
        self.assertTrue(os.path.isfile(os.path.join(cli_out, "persona_skill.md")))


if __name__ == "__main__":
    unittest.main()
