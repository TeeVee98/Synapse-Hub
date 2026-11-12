#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Deep unit tests for tools/test_impact.py (AST test impact analyzer)
"""

import os
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import tools.test_impact as ti


class TestTestImpactDeep(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="impact_test_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_resolve_target_repo(self):
        # Explicit path
        res = ti.resolve_target_repo(cli_target=self.temp_dir)
        self.assertEqual(res, os.path.abspath(self.temp_dir))

        # Non-existent path raises FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            ti.resolve_target_repo(cli_target="/non_existent_path_xyz_888")

        # TARGET_PROJECT_DIR env var
        with patch.dict(os.environ, {"TARGET_PROJECT_DIR": self.temp_dir}):
            res_env = ti.resolve_target_repo()
            self.assertEqual(res_env, os.path.abspath(self.temp_dir))

    def test_build_fallback_graph(self):
        kw_dir = os.path.join(self.temp_dir, "Keywords", "pages")
        sc_dir = os.path.join(self.temp_dir, "Scripts", "features")
        os.makedirs(kw_dir)
        os.makedirs(sc_dir)

        base_page = os.path.join(kw_dir, "BasePage.groovy")
        with open(base_page, "w", encoding="utf-8") as f:
            f.write("class BasePage { void click() {} }")

        login_page = os.path.join(kw_dir, "LoginPage.groovy")
        with open(login_page, "w", encoding="utf-8") as f:
            f.write("class LoginPage extends BasePage { void login() {} }")

        test_script = os.path.join(sc_dir, "TC_Login.groovy")
        with open(test_script, "w", encoding="utf-8") as f:
            f.write("LoginPage page = new LoginPage(); page.login();")

        graph = ti.build_fallback_graph(self.temp_dir)
        self.assertIn("nodes", graph)
        self.assertIn("edges", graph)
        nodes = {n["id"] for n in graph["nodes"]}
        self.assertIn("BasePage", nodes)
        self.assertIn("LoginPage", nodes)

        edges = [(e["source"], e["target"]) for e in graph["edges"]]
        self.assertIn(("LoginPage", "BasePage"), edges)

    def test_merge_graphs(self):
        g1 = {
            "nodes": [{"id": "Node1", "file": "f1"}],
            "edges": [{"source": "Node1", "target": "Node2"}]
        }
        g2 = {
            "nodes": [{"id": "Node1", "file": "f1"}, {"id": "Node2", "file": "f2"}],
            "edges": [{"source": "Node1", "target": "Node2"}, {"source": "Node2", "target": "Node3"}]
        }
        merged = ti.merge_graphs(g1, g2)
        self.assertEqual(len(merged["nodes"]), 2)
        self.assertEqual(len(merged["edges"]), 2)

    def test_load_graph_with_file(self):
        graph_out = os.path.join(self.temp_dir, "graphify-out")
        os.makedirs(graph_out)
        graph_file = os.path.join(graph_out, "graph.json")
        sample_data = {"nodes": [{"id": "NodeX", "file": "X"}], "edges": []}
        with open(graph_file, "w", encoding="utf-8") as f:
            json.dump(sample_data, f)

        loaded = ti.load_graph(self.temp_dir)
        self.assertIn("nodes", loaded)
        ids = [n["id"] for n in loaded["nodes"]]
        self.assertIn("NodeX", ids)

    def test_analyze_impact(self):
        graph = {
            "nodes": [
                {"id": "BasePage", "file": "Keywords/BasePage.groovy", "label": "BasePage"},
                {"id": "LoginPage", "file": "Keywords/LoginPage.groovy", "label": "LoginPage"},
                {"id": "Scripts/TC_01_Login.groovy", "file": "Scripts/TC_01_Login.groovy", "label": "TC_01_Login"},
            ],
            "edges": [
                {"source": "LoginPage", "target": "BasePage"},
                {"source": "Scripts/TC_01_Login.groovy", "target": "LoginPage"},
            ],
        }

        # Changing LoginPage directly impacts TC_01_Login
        impacted = ti.analyze_impact(graph, ["Keywords/LoginPage.groovy"])
        self.assertGreater(len(impacted), 0)
        self.assertIn("TC_01_Login", impacted)

    def test_get_total_test_cases(self):
        # Override total
        self.assertEqual(ti.get_total_test_cases(override_total=42), 42)

        # File-based count
        tests_dir = os.path.join(self.temp_dir, "tests")
        os.makedirs(tests_dir)
        with open(os.path.join(tests_dir, "test_sample.py"), "w") as f:
            f.write("# sample test")

        total = ti.get_total_test_cases(workspace_dir=self.temp_dir)
        self.assertGreaterEqual(total, 1)

    @patch("subprocess.run")
    def test_get_git_modified_files(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Keywords/LoginPage.groovy\nKeywords/CommonHelper.groovy\n",
            stderr=""
        )
        changed = ti.get_git_modified_files(self.temp_dir)
        self.assertEqual(len(changed), 2)
        self.assertIn("Keywords/LoginPage.groovy", changed)


if __name__ == "__main__":
    unittest.main()
