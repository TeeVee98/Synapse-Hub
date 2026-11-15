#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
tests/test_distill_skill.py — Unit tests for Dual-Skill Distillation Engine
"""

import os
import shutil
import tempfile
import unittest

from tools.distill_skill import distill_file, distill_skill, parse_frontmatter


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
            "Verify all 10 Quality Gates pass with exit code 0.\n"
        )
        work_md, persona_md = distill_skill(sample_doc, base_name="test-runner")

        self.assertIn("type: procedural_work_skill", work_md)
        self.assertIn("python3 tools/verify_all.py", work_md)

        self.assertIn("type: cognitive_persona_skill", persona_md)
        self.assertIn("senior dev mindset", persona_md)

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


if __name__ == "__main__":
    unittest.main()
