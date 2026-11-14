#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_skills_schema.py — Regression Test Suite for Requirement R7.1
Validates frontmatter YAML syntax, required fields, policy enums, link integrity, and validator CLI.
"""

import os
import sys
import json
import tempfile
import unittest
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
MANIFEST_PATH = REPO_ROOT / "skills_manifest.json"
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import validate_skills_schema


class TestSkillsSchema(unittest.TestCase):

    def test_all_53_skills_discovered(self):
        """Asserts exactly 53 SKILL.md files are discovered across the 11 domain folders."""
        skills = list(SKILLS_DIR.glob("*/*/SKILL.md"))
        self.assertEqual(len(skills), 53, f"Expected 53 skills, found {len(skills)}")

    def test_all_skills_pass_schema_validation(self):
        """Runs validate_skills_schema across all 53 skills; asserts 0 errors."""
        total, failures = validate_skills_schema.run_validation(SKILLS_DIR, check_links=True)
        self.assertEqual(total, 53)
        self.assertEqual(failures, {}, f"Schema validation failures: {json.dumps(failures, indent=2)}")

    def test_policies_enum_values_strictly_valid(self):
        """Verifies every skill's policies block adheres to allowed enum sets."""
        for sf in SKILLS_DIR.glob("*/*/SKILL.md"):
            content = sf.read_text(encoding="utf-8")
            fm, _, errs = validate_skills_schema.parse_yaml_frontmatter(content)
            self.assertIsNotNone(fm, f"Missing frontmatter in {sf}: {errs}")
            policies = fm.get("policies", {})
            self.assertIsInstance(policies, dict, f"policies not a dict in {sf}")
            self.assertIn(policies.get("network"), validate_skills_schema.ALLOWED_POLICIES["network"])
            self.assertIn(policies.get("shell"), validate_skills_schema.ALLOWED_POLICIES["shell"])
            self.assertIn(policies.get("filesystem"), validate_skills_schema.ALLOWED_POLICIES["filesystem"])

    def test_frontmatter_matches_skills_manifest(self):
        """Verifies name, category, and version match skills_manifest.json."""
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        manifest_skills = {s["id"]: s for s in manifest["skills"]}
        for sf in SKILLS_DIR.glob("*/*/SKILL.md"):
            skill_id = sf.parent.name
            self.assertIn(skill_id, manifest_skills)
            m_data = manifest_skills[skill_id]
            fm, _, _ = validate_skills_schema.parse_yaml_frontmatter(sf.read_text(encoding="utf-8"))
            self.assertEqual(fm["name"], m_data["id"])
            self.assertEqual(fm["category"], m_data["category"])
            self.assertEqual(fm["version"], m_data["version"])
            self.assertEqual(fm["policies"], m_data["policies"])

    def test_relative_markdown_links_are_valid(self):
        """Asserts all local markdown links resolve to existing filesystem paths."""
        total, failures = validate_skills_schema.run_validation(SKILLS_DIR, check_links=True)
        link_failures = {k: v for k, v in failures.items() if any("Broken relative link" in err for err in v)}
        self.assertEqual(link_failures, {}, f"Broken links detected: {link_failures}")

    def test_validator_cli_exit_code_zero_on_clean_repo(self):
        """Executes tools/validate_skills_schema.py via CLI and checks returncode 0."""
        script = TOOLS_DIR / "validate_skills_schema.py"
        res = subprocess.run([sys.executable, str(script), "--check-links"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"CLI validation failed: {res.stderr}\n{res.stdout}")

    def test_validator_cli_detects_mutated_invalid_policy(self):
        """Simulates an invalid policy enum (network: 'wildcard-internet') and asserts failure."""
        bad_content = (
            "---\n"
            "name: bad-skill\n"
            "description: Test. Use when testing.\n"
            "category: test_automation_and_execution\n"
            "version: '1.0.0'\n"
            "policies:\n"
            "  network: wildcard-internet\n"
            "  shell: none\n"
            "  filesystem: read-only\n"
            "---\n"
            "# Body\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "bad-skill"
            p.mkdir()
            (p / "SKILL.md").write_text(bad_content, encoding="utf-8")
            (p / "examples").mkdir()
            (p / "examples" / "sample.txt").write_text("ok", encoding="utf-8")
            errs = validate_skills_schema.validate_skill(p / "SKILL.md")
            self.assertTrue(any("Invalid value 'wildcard-internet'" in e for e in errs), f"Expected error not found in: {errs}")

    def test_gate_9_verify_all_invokes_schema_validation(self):
        """Verifies gate_9_skill_collision runs cleanly with schema validation included."""
        import verify_all
        passed = verify_all.gate_9_skill_collision(str(REPO_ROOT), mode="HUB")
        self.assertTrue(passed, "Gate 9 must pass in HUB mode")


if __name__ == "__main__":
    unittest.main()
