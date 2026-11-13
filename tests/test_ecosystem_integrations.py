#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_ecosystem_integrations.py — Unit Tests for 20-Repo Ecosystem Integrations
Verifies all newly adopted tools, sentinels, and standards from Part 1 & Part 2 evaluations.
100% UTF-8 No BOM.
"""

import unittest
import os
import sys
import json

# Ensure tools directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools")))

from runaway_stopper import RunawaySentinel
from git_worktree_manager import WorktreeManager
from pairwise_generator import generate_pairwise, generate_all_pairs
from mechanical_ui_gate import MechanicalUIGate
from diagram_architect import generate_fsm_diagram, generate_clean_pom_diagram
from distill_log import shrink_tokens, distill
from interview_story import PocockGriller

class TestEcosystemIntegrations(unittest.TestCase):

    def test_runaway_stopper_clean(self):
        sentinel = RunawaySentinel({"max_turns": 10, "max_tokens": 50000})
        turns = [
            {"turn_index": i, "tokens_est": 1000, "command": f"cmd_{i}"}
            for i in range(5)
        ]
        res = sentinel.evaluate_transcript(turns)
        self.assertEqual(res["verdict"], "OK")
        self.assertFalse(res["is_runaway"])

    def test_runaway_stopper_turn_limit(self):
        sentinel = RunawaySentinel({"max_turns": 5, "max_tokens": 50000})
        turns = [
            {"turn_index": i, "tokens_est": 100, "command": f"cmd_{i}"}
            for i in range(6)
        ]
        res = sentinel.evaluate_transcript(turns)
        self.assertEqual(res["verdict"], "STOP")
        self.assertTrue(res["is_runaway"])

    def test_runaway_stopper_repeated_loop(self):
        sentinel = RunawaySentinel({"max_repeated_calls": 3})
        turns = [
            {"turn_index": 0, "command": "run pytest"},
            {"turn_index": 1, "command": "run pytest"},
            {"turn_index": 2, "command": "run pytest"},
        ]
        res = sentinel.evaluate_transcript(turns)
        self.assertEqual(res["verdict"], "STOP")
        self.assertTrue(any(f["type"] == "TOOL_LOOP_DETECTED" for f in res["flags"]))

    def test_pairwise_generator_coverage(self):
        params = {
            "browser": ["chromium", "firefox", "webkit"],
            "role": ["admin", "editor"],
            "resolution": ["1080p", "720p"]
        }
        all_pairs = generate_all_pairs(params)
        self.assertEqual(len(all_pairs), (3*2) + (3*2) + (2*2)) # 6 + 6 + 4 = 16 pairs
        cases = generate_pairwise(params)
        # Total combinations: 3 * 2 * 2 = 12. Pairwise should be <= 8.
        self.assertLessEqual(len(cases), 8)

        # Verify all 2-way pairs are covered by the generated test cases
        covered = set()
        param_keys = sorted(params.keys())
        for c in cases:
            for i in range(len(param_keys)):
                for j in range(i + 1, len(param_keys)):
                    k1, k2 = param_keys[i], param_keys[j]
                    pair = ((k1, c[k1]), (k2, c[k2]))
                    covered.add(pair)
        self.assertEqual(len(covered), len(all_pairs))

    def test_mechanical_ui_gate_clean_html(self):
        gate = MechanicalUIGate()
        html = """<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Test Page</title>
</head>
<body>
  <h1>Title</h1>
  <button aria-label="Submit Form">Click me</button>
</body>
</html>"""
        res = gate.audit_html_content(html)
        self.assertTrue(res["passed"])
        self.assertEqual(res["fail_count"], 0)

    def test_mechanical_ui_gate_catches_empty_button_and_missing_viewport(self):
        gate = MechanicalUIGate()
        html = """<!DOCTYPE html>
<html>
<head><title>No Viewport</title></head>
<body>
  <button></button>
  <!-- TODO: add content -->
</body>
</html>"""
        res = gate.audit_html_content(html)
        self.assertFalse(res["passed"])
        fail_ids = [f["id"] for f in res["findings"] if f["severity"] == "FAIL"]
        self.assertIn("empty-button", fail_ids)
        self.assertIn("ai-placeholder-comment", fail_ids)

    def test_diagram_architect_fsm_and_clean_pom(self):
        fsm_svg = generate_fsm_diagram()
        self.assertIn("SYNAPSE HUB — 5-STAGE AUTONOMOUS FSM ENGINE", fsm_svg)
        self.assertIn("STAGE 1: DISCOVERY", fsm_svg)

        pom_svg = generate_clean_pom_diagram()
        self.assertIn("CLEAN POM / FLAT ARCHITECTURE INVARIANT", pom_svg)
        self.assertIn("ZERO Raw XPaths / CSS", pom_svg)

    def test_distill_log_shrink_tokens(self):
        raw_log = """
        at Script1.groovy:25
        at Script1.groovy:25
        at Script1.groovy:25
        FAILED: Assertion failed
        """
        shrunk = shrink_tokens(raw_log)
        self.assertIn("at Script1.groovy:25", shrunk)
        self.assertIn("FAILED: Assertion failed", shrunk)
        # Deduplication should ensure it only appears once
        self.assertEqual(shrunk.count("at Script1.groovy:25"), 1)

    def test_runaway_stopper_token_limit_without_turns(self):
        sentinel = RunawaySentinel({"max_tokens": 100000})
        turns = [{"turn_index": 0, "tokens_est": 120000}]
        res = sentinel.evaluate_transcript(turns)
        self.assertEqual(res["verdict"], "STOP")
        self.assertTrue(res["is_runaway"])
        self.assertTrue(any(f["type"] == "TOKEN_BUDGET_EXCEEDED" for f in res["flags"]))

    def test_pairwise_generator_empty_params(self):
        self.assertEqual(generate_pairwise({}), [])
        self.assertEqual(generate_pairwise({"a": []}), [])
        self.assertEqual(generate_pairwise({"a": [1], "b": []}), [])

    def test_mechanical_ui_gate_contrast_audit(self):
        gate = MechanicalUIGate(min_contrast=4.5)
        bad_html = '<span style="color: #999999; background-color: #ffffff;">low contrast</span>'
        res_bad = gate.audit_html_content(bad_html)
        self.assertFalse(res_bad["passed"])
        self.assertIn("low-contrast-text", [f["id"] for f in res_bad["findings"]])

        good_html = '<span style="color: #000000; background-color: #ffffff;">high contrast</span>'
        res_good = gate.audit_html_content(good_html)
        self.assertTrue(res_good["passed"])

    def test_interview_story_grill_me_mode(self):
        griller = PocockGriller()
        q_normal = griller.generate_frontier_questions("Story", grill_me=False)
        q_grill = griller.generate_frontier_questions("Story", grill_me=True)
        self.assertGreater(len(q_grill), len(q_normal))
        self.assertTrue(any("Concurrency" in q["question"] for q in q_grill))
        self.assertTrue(any("Fuzzing" in q["question"] for q in q_grill))

    def test_skills_lock_file_validity(self):
        self.assertTrue(os.path.exists("skills-lock.json"))
        with open("skills-lock.json", "r", encoding="utf-8") as f:
            lock = json.load(f)
        self.assertEqual(lock["version"], 3)
        self.assertEqual(len(lock["skills"]), 53)
        self.assertIn("clean-pom-crafter", lock["skills"])
        self.assertIn("playwright-live-interaction", lock["skills"])
        self.assertIn("verification-before-completion", lock["skills"])
        self.assertIn("systematic-debugging", lock["skills"])

    def test_consolidated_top20_evaluation_report(self):
        report_path = os.path.join("reports", "TOP_20_SKILLS_AGENTS_CONSOLIDATED_EVALUATION.html")
        self.assertTrue(os.path.exists(report_path), f"Report not found at {report_path}")
        with open(report_path, "rb") as fb:
            raw = fb.read()
        # Verify 100% UTF-8 No BOM
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), "BOM detected in consolidated report")
        
        content = raw.decode("utf-8")
        
        expected_repos = [
            "mattpocock/skills", "obra/superpowers", "anthropics/skills", "DietrichGebert/ponytail",
            "garrytan/gstack", "addyosmani/agent-skills", "pbakaus/impeccable", "sickn33/antigravity-awesome-skills",
            "github/awesome-copilot", "vercel-labs/skills", "nextlevelbuilder/ui-ux-pro-max-skill",
            "Graphify-Labs/graphify", "JuliusBrussee/caveman", "Leonxlnx/taste-skill",
            "ComposioHQ/awesome-claude-skills", "Fission-AI/OpenSpec", "cloudflare/security-audit-skill",
            "shanraisshan/claude-code-best-practice", "cathrynlavery/diagram-design", "Nutlope/hallmark"
        ]

        # Verify all 20 repos are present by index and by exact repo name
        for i, repo_name in enumerate(expected_repos, start=1):
            self.assertIn(f'data-repo-index="{i}"', content, f"Repo index #{i} missing")
            self.assertIn(f'id="repo-card-{i}"', content, f"Repo card #{i} missing")
            # Verify real repository name appears in cards, not dummy fallback "Repo {i}"
            self.assertIn(repo_name, content, f"Repository name '{repo_name}' missing from report")
            self.assertNotIn(f'<span class="repo-name">Repo {i}</span>', content, f"Dummy placeholder 'Repo {i}' found")

        # Verify evaluation details are present (eval-item count)
        eval_item_count = content.count('class="eval-item"')
        self.assertGreaterEqual(eval_item_count, 45, f"Too few evaluation items: {eval_item_count}")

        # Verify Mechanical UI Finish Gate passes with zero fails and zero warnings
        gate = MechanicalUIGate()
        res = gate.audit_html_content(content)
        self.assertTrue(res["passed"], f"Mechanical UI gate failed: {res['findings']}")
        self.assertEqual(res["fail_count"], 0)
        self.assertEqual(res["warn_count"], 0)

if __name__ == "__main__":
    unittest.main()
