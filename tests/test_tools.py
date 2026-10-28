#!/usr/bin/env python3
"""
Enterprise Automated Testing Suite for AI Agent Tools & Hub Integrity
----------------------------------------------------------------------
Verifies the syntactic correctness, importability, and deterministic
behavior of all centralized tools in `tools/` using standard library `unittest`.
"""

import os
import sys
import json
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
sys.path.insert(0, TOOLS_DIR)


class TestToolsIntegrity(unittest.TestCase):
    """Automated unit and integration tests for tools in tools/."""

    def test_browser_helpers_exists_and_complete(self):
        """Validates that browser_helpers.js exists and exports core capabilities."""
        helper_path = os.path.join(TOOLS_DIR, "browser_helpers.js")
        self.assertTrue(os.path.exists(helper_path), "tools/browser_helpers.js must exist")

        with open(helper_path, "r", encoding="utf-8") as f:
            code = f.read()

        expected_methods = ["batch:", "audit:", "heal:", "clickSafe:", "exportSession:", "isStable:"]
        for method in expected_methods:
            self.assertIn(method, code, f"browser_helpers.js missing method: {method}")

    def test_skills_manifest_integrity(self):
        """Validates that skills_manifest.json matches disk files."""
        manifest_path = os.path.join(REPO_ROOT, "skills_manifest.json")
        self.assertTrue(os.path.exists(manifest_path), "skills_manifest.json must exist")

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("version"), "2.0.0", "Manifest version must be 2.0.0")
        manifest_skills = [s["name"] for s in data.get("skills", [])]
        self.assertEqual(len(manifest_skills), 30, "Manifest must declare exactly 30 skills")

        skills_dir = os.path.join(REPO_ROOT, ".agents", "skills")
        for skill_name in manifest_skills:
            skill_md = os.path.join(skills_dir, skill_name, "SKILL.md")
            self.assertTrue(os.path.exists(skill_md), f"Skill file must exist: {skill_md}")

    def test_cache_resolver_cosine_similarity(self):
        """Validates cosine similarity calculation in cache_resolver."""
        import cache_resolver
        v1 = [1.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]
        v3 = [0.0, 1.0, 0.0]

        self.assertAlmostEqual(cache_resolver.cosine_similarity(v1, v2), 1.0, places=4)
        self.assertAlmostEqual(cache_resolver.cosine_similarity(v1, v3), 0.0, places=4)

    def test_distill_log_parser(self):
        """Validates that distill_log strips noise while preserving stacktraces."""
        import distill_log
        sample_log = [
            "2026-10-28 10:00:00.123 [DEBUG] org.apache.http.wire - >> GET /ping HTTP/1.1",
            "2026-10-28 10:00:00.124 [DEBUG] org.apache.http.headers - << HTTP/1.1 200 OK",
            "Exception in thread \"main\" java.lang.AssertionError: Expected toast not found",
            "\tat com.enterprise.pages.LoginPage.login(LoginPage.groovy:42)"
        ]
        filtered = distill_log.distill_lines(sample_log)
        filtered_text = "\n".join(filtered)
        self.assertIn("AssertionError", filtered_text)
        self.assertNotIn("org.apache.http.wire", filtered_text)

    def test_infer_linter_ast_rule_definitions(self):
        """Validates that infer_linter has AST detection rules registered."""
        import infer_linter
        self.assertTrue(hasattr(infer_linter, "LINTER_RULES") or hasattr(infer_linter, "check_test_script") or hasattr(infer_linter, "scan_script"))

    def test_verify_all_seven_gates_defined(self):
        """Validates that verify_all.py defines all 7 Quality Gates."""
        import verify_all
        gates = ["gate1_utf8_no_bom", "gate2_clean_pom", "gate3_dynamic_test_data",
                 "gate4_path_portability", "gate5_ai_docs_drift", "gate6_temporary_files",
                 "gate7_truth_anchor"]
        for gate in gates:
            self.assertTrue(hasattr(verify_all, gate), f"verify_all.py must define {gate}")


if __name__ == "__main__":
    unittest.main()
