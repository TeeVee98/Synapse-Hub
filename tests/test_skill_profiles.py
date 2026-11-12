#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tests/test_skill_profiles.py — Unit Tests for 4 Core Capability Profiles & Skill Filtering
"""

import os
import sys
import unittest
import json
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import skill_profiles


class TestSkillProfiles(unittest.TestCase):
    """Verifies profile modularization, filtering, and CLI outputs."""

    def test_list_profiles_contains_four_core_capability_profiles(self):
        profiles = skill_profiles.list_profiles()
        core_keys = ["core-web-qa", "perf-and-load", "api-security", "enterprise-rbt"]
        for key in core_keys:
            self.assertIn(key, profiles, f"Profile '{key}' must be present in skills_manifest.json")
            p = profiles[key]
            self.assertGreater(p["skill_count"], 0, f"Profile '{key}' must contain skills")
            self.assertIsInstance(p["skills"], list)

    def test_filter_skills_by_profile(self):
        web_skills = skill_profiles.filter_skills(profile_key="core-web-qa")
        web_ids = [s["id"] for s in web_skills]
        self.assertIn("clean-pom-crafter", web_ids)
        self.assertIn("playwright-live-interaction", web_ids)
        self.assertIn("self-healing-locator", web_ids)

        perf_skills = skill_profiles.filter_skills(profile_key="perf-and-load")
        perf_ids = [s["id"] for s in perf_skills]
        self.assertIn("backend-load-and-stress-patterns", perf_ids)
        self.assertIn("web-vitals-and-performance-profiler", perf_ids)

        api_skills = skill_profiles.filter_skills(profile_key="api-security")
        api_ids = [s["id"] for s in api_skills]
        self.assertIn("api-spec-to-e2e-matrix", api_ids)
        self.assertIn("security-dast-sentinel", api_ids)

        rbt_skills = skill_profiles.filter_skills(profile_key="enterprise-rbt")
        rbt_ids = [s["id"] for s in rbt_skills]
        self.assertIn("rbt-manual-testing", rbt_ids)
        self.assertIn("wcag-audit-patterns", rbt_ids)

    def test_four_core_capability_profiles_cover_all_53_skills(self):
        """Verifies that 100% of the 53 skills are covered across the 4 core profiles with zero orphaned skills."""
        manifest = skill_profiles.load_manifest()
        all_skills = {s["id"] for s in manifest.get("skills", [])}
        self.assertEqual(len(all_skills), 53, "Catalog must declare exactly 53 skills")

        core_keys = ["core-web-qa", "perf-and-load", "api-security", "enterprise-rbt"]
        union_skills = set()
        for k in core_keys:
            skills = manifest["profiles"][k]["skills"]
            self.assertGreater(len(skills), 0)
            union_skills.update(skills)

        # Assert 100% coverage
        self.assertEqual(union_skills, all_skills, f"Orphaned skills detected: {all_skills - union_skills}")

        # Assert no skill has empty profiles list
        for s in manifest.get("skills", []):
            self.assertTrue(len(s.get("profiles", [])) > 0, f"Skill {s['id']} has empty profiles list")

    def test_filter_skills_by_description_query(self):
        """Verifies search matching against skill description field."""
        results = skill_profiles.filter_skills(query="BOLA")
        self.assertTrue(any(s["id"] == "security-dast-sentinel" for s in results))

    def test_filter_skills_case_insensitive_profile_key(self):
        """Verifies profile lookup is resilient to case differences."""
        skills = skill_profiles.filter_skills(profile_key="CORE-WEB-QA")
        self.assertGreater(len(skills), 0)

    def test_filter_skills_unknown_profile_raises_value_error(self):
        with self.assertRaises(ValueError):
            skill_profiles.filter_skills(profile_key="non-existent-profile-xyz")

    def test_filter_skills_by_query_and_category(self):
        results = skill_profiles.filter_skills(query="playwright")
        self.assertTrue(any("playwright" in s["id"] for s in results))

        cat_results = skill_profiles.filter_skills(category="verification_and_resilience")
        self.assertTrue(len(cat_results) > 0)
        self.assertTrue(all(s["category"] == "verification_and_resilience" for s in cat_results))

    def test_cli_skills_command_execution(self):
        cmd = [sys.executable, os.path.join(TOOLS_DIR, "cli.py"), "skills", "--list-profiles"]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=REPO_ROOT)
        self.assertEqual(res.returncode, 0)
        self.assertIn("core-web-qa", res.stdout)
        self.assertIn("perf-and-load", res.stdout)
        self.assertIn("api-security", res.stdout)
        self.assertIn("enterprise-rbt", res.stdout)

    def test_cli_skills_profile_json_format(self):
        cmd = [sys.executable, os.path.join(TOOLS_DIR, "cli.py"), "skills", "-p", "api-security", "--format", "json"]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=REPO_ROOT)
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertIsInstance(data, list)
        ids = [item["id"] for item in data]
        self.assertIn("api-spec-to-e2e-matrix", ids)


if __name__ == "__main__":
    unittest.main()
