#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""4-Scenario Unit Tests for tools/core/scaffold.py and templates/PROJECT_AI_GUIDE_TEMPLATE.md."""

import json
import os
import subprocess
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tools.core.scaffold import TEMPLATE_MAP, scaffold_project


class TestScaffoldAndTemplate:
    def test_scaffold_positive_mobile_and_synapse_config_json(self, tmp_path):
        assert "mobile" in TEMPLATE_MAP
        rc = scaffold_project(
            project_name="MobileDemo",
            template="mobile",
            profile="enterprise",
            target_dir=str(tmp_path),
        )
        assert rc == 0
        proj_dir = tmp_path / "MobileDemo"
        assert (proj_dir / "synapse.config.json").is_file()
        assert not (proj_dir / ".synapse.json").exists()
        cfg = json.loads((proj_dir / "synapse.config.json").read_text(encoding="utf-8"))
        assert cfg["project"]["name"] == "MobileDemo"
        assert cfg["quality_gates"]["profile"] == "enterprise"

    def test_scaffold_ignores_test_results_and_node_modules_and_force_overwrite(self, tmp_path):
        rc = scaffold_project(
            project_name="PwDemo",
            template="playwright",
            profile="starter",
            target_dir=str(tmp_path),
        )
        assert rc == 0
        proj_dir = tmp_path / "PwDemo"
        assert not (proj_dir / "node_modules").exists()
        assert not (proj_dir / "test-results").exists()
        assert not (proj_dir / "playwright-report").exists()

        # Negative: collision without force fails with 1
        assert scaffold_project("PwDemo", "playwright", "starter", str(tmp_path), force=False) == 1
        # Boundary: force=True overwrites cleanly
        assert scaffold_project("PwDemo", "playwright", "standard", str(tmp_path), force=True) == 0
        cfg = json.loads((proj_dir / "synapse.config.json").read_text(encoding="utf-8"))
        assert cfg["quality_gates"]["profile"] == "standard"

    def test_scaffold_negative_invalid_template_and_cli_help(self, tmp_path):
        rc = scaffold_project("BadProj", template="unknown_stack", target_dir=str(tmp_path))
        assert rc == 1

        res = subprocess.run(
            [sys.executable, os.path.join(ROOT_DIR, "tools", "core", "scaffold.py"), "--help"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert res.returncode == 0
        assert "mobile" in res.stdout

    def test_project_ai_guide_template_is_clean_client_mode_compliant(self):
        tpl_path = os.path.join(ROOT_DIR, "templates", "PROJECT_AI_GUIDE_TEMPLATE.md")
        content = open(tpl_path, "r", encoding="utf-8").read()
        assert "verify_all.py --mode hub" not in content
        assert "../Synapse-Hub/" not in content
        assert "networkidle" not in content
        assert "2 consecutive times" in content
        assert "3 consecutive times" not in content
        assert "11 Quality Gates" in content
        assert "10 Quality Gates" not in content
        assert content.count("## 8.") == 1
        assert "## 9." in content
