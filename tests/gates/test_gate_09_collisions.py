#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for Gate 9: Tier-2 Skill Routing & Collision Guard."""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from tools.core.gates.gate_09_collisions import Gate09Collisions, gate_9_skill_collision


class TestGate09Collisions(unittest.TestCase):
    def test_gate_09_class_wrapper(self):
        gate = Gate09Collisions()
        self.assertEqual(gate.gate_id, 9)
        self.assertEqual(gate.name, "Gate 9: Tier-2 Skill Routing & Collision Guard")
        self.assertEqual(gate.key, "gate_9_skill_collision")

    def test_gate_09_target_mode_skips_when_no_skills(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # When target project has no .agents/skills/ and no skills_manifest.json, Gate 9 skips
            real_exists = os.path.exists
            def side_effect(path):
                norm = path.replace("\\", "/")
                if norm.endswith(".agents/skills") or norm.endswith("skills_manifest.json"):
                    return False
                return real_exists(path)

            with patch("os.path.exists", side_effect=side_effect):
                res = gate_9_skill_collision(tmpdir, mode="TARGET")
                self.assertTrue(res)

    @patch("tools.core.gates.gate_09_collisions.resolve_tool_path")
    @patch("subprocess.run")
    def test_gate_09_hub_mode_executes(self, mock_run, mock_resolve):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_resolve.return_value = "/mock/tools/skill_collision_guard.py"
            with patch("os.path.exists", return_value=True):
                mock_proc = MagicMock()
                mock_proc.returncode = 0
                mock_proc.stdout = "All skills clean"
                mock_proc.stderr = ""
                mock_run.return_value = mock_proc

                with patch("skill_canonical_digest.validate_lockfile_integrity", return_value=(True, "Lockfile valid")):
                    gate = Gate09Collisions()
                    res = gate.execute(tmpdir, mode="HUB")
                    self.assertTrue(res.passed)


if __name__ == "__main__":
    unittest.main()
