#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_skills_schema.py — Regression Test Suite for Requirements R4 & R7.1
Validates frontmatter YAML syntax, upstream schema layer, Synapse policy extensions layer,
code block classification, link & backtick reference resolution, GitHub Actions pinning,
and validator CLI across layers.
"""

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


def _get_skill_files():
    if SKILLS_DIR.is_dir():
        files = list(SKILLS_DIR.glob("*/*/SKILL.md"))
        if files:
            return files
    if MANIFEST_PATH.is_file():
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [REPO_ROOT / s["path"] for s in data.get("skills", []) if (REPO_ROOT / s["path"]).is_file()]
    return []


class TestSkillsSchema(unittest.TestCase):

    def test_all_56_skills_discovered(self):
        """Asserts exactly 57 SKILL.md files are discovered."""
        skills = _get_skill_files()
        self.assertEqual(len(skills), 57, f"Expected 57 skills, found {len(skills)}")

    def test_all_skills_pass_schema_validation(self):
        """Runs validate_skills_schema across all 57 skills with layer='all'; asserts 0 errors."""
        target_dir = SKILLS_DIR if SKILLS_DIR.is_dir() else REPO_ROOT
        total, failures = validate_skills_schema.run_validation(target_dir, check_links=True, layer="all")
        self.assertEqual(total, 57)
        self.assertEqual(failures, {}, f"Schema validation failures: {json.dumps(failures, indent=2)}")

    def test_policies_enum_values_strictly_valid(self):
        """Verifies every skill's policies block adheres to allowed enum sets."""
        for sf in _get_skill_files():
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
        total, failures = validate_skills_schema.run_validation(SKILLS_DIR, check_links=True, layer="all")
        link_failures = {k: v for k, v in failures.items() if any("Broken relative link" in err for err in v)}
        self.assertEqual(link_failures, {}, f"Broken links detected: {link_failures}")

    def test_validator_cli_exit_code_zero_on_clean_repo(self):
        """Executes tools/validate_skills_schema.py via CLI and checks returncode 0."""
        script = TOOLS_DIR / "validate_skills_schema.py"
        res = subprocess.run([sys.executable, str(script), "--layer", "all", "--check-links"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"CLI validation failed: {res.stderr}\n{res.stdout}")

    def test_validator_cli_layers(self):
        """Tests CLI execution across --layer upstream, --layer policy, and --layer all."""
        script = TOOLS_DIR / "validate_skills_schema.py"
        for layer in ("upstream", "policy", "all"):
            res = subprocess.run([sys.executable, str(script), "--layer", layer], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(res.returncode, 0, f"CLI validation failed for layer '{layer}': {res.stderr}\n{res.stdout}")

    def test_validate_upstream_schema_contract(self):
        """Tests Layer 1 Upstream Schema Conformance validation rules."""
        valid_data = {
            "name": "valid-skill-name",
            "description": "Enterprise QA skill. Use when testing contract schemas.",
        }
        ok, errs = validate_skills_schema.validate_upstream_schema(valid_data)
        self.assertTrue(ok, f"Valid upstream data failed: {errs}")

        # Invalid name: uppercase
        bad_name_data = {"name": "Invalid_Skill_Name", "description": "Use when testing."}
        ok, errs = validate_skills_schema.validate_upstream_schema(bad_name_data)
        self.assertFalse(ok)
        self.assertTrue(any("Invalid 'name' format" in e for e in errs))

        # Missing "use when" trigger clause in description
        missing_trigger_data = {"name": "test-skill", "description": "A skill without activation clause."}
        ok, errs = validate_skills_schema.validate_upstream_schema(missing_trigger_data)
        self.assertFalse(ok)
        self.assertTrue(any("mandatory activation trigger clause" in e for e in errs))

    def test_classify_code_blocks(self):
        """Tests code block classification extraction for runnable, pseudocode, and illustrative blocks."""
        sample_md = (
            "# Test Document\n\n"
            "<!-- classification: runnable -->\n"
            "```python\n"
            "# Prerequisites: python >= 3.10\n"
            "# Test Data: {'key': 'value'}\n"
            "# Expected Output: True\n"
            "def run_check():\n"
            "    return True\n"
            "```\n\n"
            "<!-- classification: pseudocode -->\n"
            "```typescript\n"
            "function sketchAlgorithm() {\n"
            "    // abstract logic\n"
            "}\n"
            "```\n\n"
            "<!-- classification: illustrative -->\n"
            "```bash\n"
            "echo 'illustrative snippet'\n"
            "```\n"
        )
        blocks = validate_skills_schema.classify_code_blocks(sample_md)
        self.assertEqual(len(blocks), 3)

        self.assertEqual(blocks[0].language, "python")
        self.assertEqual(blocks[0].classification, "runnable")
        self.assertTrue(blocks[0].has_prerequisites)
        self.assertTrue(blocks[0].has_test_data)
        self.assertTrue(blocks[0].has_expected_output)

        self.assertEqual(blocks[1].language, "typescript")
        self.assertEqual(blocks[1].classification, "pseudocode")

        self.assertEqual(blocks[2].language, "bash")
        self.assertEqual(blocks[2].classification, "illustrative")

    def test_github_actions_sha_pinning_check(self):
        """Asserts validator catches unpinned actions like 'actions/checkout@v4'."""
        unpinned_content = (
            "---\nname: pin-test\ndescription: Use when testing.\ncategory: architecture_and_analysis\nversion: '1.0.0'\n"
            "policies:\n  network: none\n  shell: none\n  filesystem: workspace-sandbox\n---\n"
            "## 1. Trigger & Activation ('Use when...')\n## 2. Non-Goals & Boundary Constraints\n"
            "## 3. Ordered Execution Workflow\n```yaml\nuses: actions/checkout@v4\n```\n"
            "## 4. Verification Points & DoD\n## 5. Handoff Protocol\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "pin-test"
            p.mkdir()
            (p / "SKILL.md").write_text(unpinned_content, encoding="utf-8")
            (p / "examples").mkdir()
            (p / "examples" / "sample.yml").write_text("ok", encoding="utf-8")
            errs = validate_skills_schema.validate_skill(p / "SKILL.md", layer="policy")
            self.assertTrue(any("Unpinned GitHub Action detected" in e for e in errs), f"Expected pinning error not found: {errs}")

    def test_unproven_claims_heuristic_detection(self):
        """Asserts validator catches unproven superlative/percentage claims."""
        unproven_content = (
            "---\nname: claim-test\ndescription: Use when testing.\ncategory: architecture_and_analysis\nversion: '1.0.0'\n"
            "policies:\n  network: none\n  shell: none\n  filesystem: workspace-sandbox\n---\n"
            "## 1. Trigger & Activation ('Use when...')\n## 2. Non-Goals & Boundary Constraints\n"
            "## 3. Ordered Execution Workflow\nGuaranteed 100% selector hit rate under all conditions.\n"
            "## 4. Verification Points & DoD\n## 5. Handoff Protocol\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "claim-test"
            p.mkdir()
            (p / "SKILL.md").write_text(unproven_content, encoding="utf-8")
            (p / "examples").mkdir()
            (p / "examples" / "sample.txt").write_text("ok", encoding="utf-8")
            errs = validate_skills_schema.validate_skill(p / "SKILL.md", layer="policy")
            self.assertTrue(any("Unproven quantitative/superlative claim detected" in e for e in errs), f"Expected claim error not found: {errs}")

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
