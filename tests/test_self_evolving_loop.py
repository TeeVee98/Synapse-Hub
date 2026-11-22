#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_self_evolving_loop.py — Unit Tests for Recursive Self-Evolving Harness Loop (Algorithm 1)
"""

import os
import shutil
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "core"))

from self_evolving_loop import SelfEvolvingLoop, CandidateEdit


class TestSelfEvolvingLoop(unittest.TestCase):
    """Tests Algorithm 1 candidate generation, mutation strategies, and winner selection."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.harness_file = os.path.join(self.tmpdir, "AGENTS.md")
        with open(self.harness_file, "w", encoding="utf-8") as f:
            f.write("# AGENTS.md\n\n\n## Section 1\n\nSome rule content.\n\n")

        self.loop = SelfEvolvingLoop(
            repo_root=self.tmpdir,
            harness_path=self.harness_file,
            candidate_count=8,
            tier="fast",
            dry_run=True,
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_generate_eight_candidates(self):
        """Generates exactly 8 candidate edits with distinct strategies."""
        content = self.loop.load_current_harness()
        candidates = self.loop.generate_candidate_edits(content, failures=[], baseline_score=99.0)
        self.assertEqual(len(candidates), 8)

        strategies = [c.strategy for c in candidates]
        self.assertEqual(len(set(strategies)), 8)
        self.assertIn("CACHE_PREFIX_DENSIFICATION", strategies)
        self.assertIn("FAILURE_TARGETED_INVARIANT", strategies)
        self.assertIn("CIRCUIT_BREAKER_TUNING", strategies)
        self.assertIn("HYBRID_SYNERGY_OPTIMIZER", strategies)

    def test_mutation_prompt_densification(self):
        """Collapses duplicate blank lines to improve token density."""
        text = "Line 1\n\n\n\nLine 2   \n\n\nLine 3\n"
        mutated = self.loop._mutate_prompt_densification(text)
        self.assertNotIn("\n\n\n", mutated)
        self.assertIn("Line 1\n\nLine 2\n\nLine 3", mutated)

    def test_mutation_failure_reinforcement(self):
        """Injects targeted invariant rules when failure set F contains failures."""
        failures = [
            {"category": "CLEAN_POM_VIOLATION", "message": "Raw selector in test"},
            {"category": "UTF8_BOM_DEFECT", "message": "Found BOM byte"},
        ]
        text = "# Rules\nRule 1"
        mutated = self.loop._mutate_failure_reinforcement(text, failures)
        self.assertIn("POM Sentinel", mutated)
        self.assertIn("UTF-8 Sentinel", mutated)

    def test_candidate_edit_to_dict(self):
        """Serializes candidate result to dictionary correctly."""
        cand = CandidateEdit("e1", "TEST_STRATEGY", "Test description", "content")
        cand.score = 98.5
        cand.delta_score = 1.2
        cand.retention_passed = True
        cand.decision = "ACCEPTED"

        d = cand.to_dict()
        self.assertEqual(d["id"], "e1")
        self.assertEqual(d["strategy"], "TEST_STRATEGY")
        self.assertEqual(d["score"], 98.5)
        self.assertEqual(d["delta_score"], 1.2)
        self.assertTrue(d["retention_passed"])


if __name__ == "__main__":
    unittest.main()
