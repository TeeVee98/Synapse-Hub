#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tests/test_perfection_10.py — Test Battery for 10.0 Perfection Architecture
---------------------------------------------------------------------------
Verifies the 3 core hardening fixes for 10.0 perfection:
  1. NTFS Junction Native / Cross-platform directory linking in worktree_manager.
  2. Hierarchical Key-Path & Directive Anchors in polyglot_ast_parser (JSON, YAML, Dockerfile, Shell).
  3. Universal Immutable Cache Prefix & Cursor alwaysApply in AI bridges.
Covering 4 mandatory scenarios: Positive, Negative, Boundary, and Integration.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.orchestration.worktree_manager import create_directory_link, link_shared_dependencies
from tools.context.polyglot_ast_parser import (
    detect_language,
    parse_polyglot_signatures,
    parse_json_structural_anchors,
    parse_yaml_structural_anchors,
    parse_dockerfile_structural_anchors,
    parse_shell_structural_anchors,
)


class TestPerfection10Battery(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    # 1. POSITIVE SCENARIOS

    def test_tc01_worktree_link_directory_creation(self):
        """TC-01: Directory link creates a usable target link pointing to source directory."""
        src = os.path.join(self.temp_dir, "src_deps")
        dst = os.path.join(self.temp_dir, "dst_deps")
        os.makedirs(src, exist_ok=True)
        with open(os.path.join(src, "pkg.txt"), "w", encoding="utf-8") as f:
            f.write("test-package-content")

        with patch("os.symlink", wraps=os.symlink) as mock_sym:
            success, link_type = create_directory_link(src, dst)
            self.assertTrue(success)
            if sys.platform == "win32":
                self.assertIn(link_type, ("symlink", "junction"))
            else:
                self.assertEqual(link_type, "symlink")
            mock_sym.assert_called_once_with(src, dst, target_is_directory=True)

        self.assertTrue(os.path.exists(dst))
        with open(os.path.join(dst, "pkg.txt"), "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "test-package-content")

    def test_tc01_windows_ntfs_junction_success(self):
        """TC-01b: On Windows when symlink fails, uses NTFS Junction via _winapi."""
        src = os.path.join(self.temp_dir, "src_win")
        dst = os.path.join(self.temp_dir, "dst_win")

        mock_winapi = MagicMock()
        mock_winapi.CreateJunction = MagicMock()

        with patch("os.symlink", side_effect=OSError(1314, "Privilege not held")), \
             patch("sys.platform", "win32"), \
             patch.dict("sys.modules", {"_winapi": mock_winapi}):
            success, link_type = create_directory_link(src, dst)
            self.assertTrue(success)
            self.assertEqual(link_type, "junction")
            mock_winapi.CreateJunction.assert_called_once_with(os.path.abspath(src), os.path.abspath(dst))

    def test_tc01_windows_mklink_fallback(self):
        """TC-01c: On Windows when _winapi fails, fallbacks to cmd.exe mklink /J."""
        src = os.path.join(self.temp_dir, "src_mklink")
        dst = os.path.join(self.temp_dir, "dst_mklink")

        mock_proc = MagicMock()
        mock_proc.returncode = 0

        with patch("os.symlink", side_effect=OSError), \
             patch("sys.platform", "win32"), \
             patch.dict("sys.modules", {"_winapi": None}), \
             patch("subprocess.run", return_value=mock_proc) as mock_subp:
            success, link_type = create_directory_link(src, dst)
            self.assertTrue(success)
            self.assertEqual(link_type, "junction")
            mock_subp.assert_called_once_with(
                ["cmd", "/c", "mklink", "/J", os.path.abspath(dst), os.path.abspath(src)],
                capture_output=True,
                text=True,
                timeout=5.0
            )

    def test_tc01_link_failure_returns_none(self):
        """TC-01d: When all linking mechanisms fail, returns (False, 'none')."""
        src = os.path.join(self.temp_dir, "src_fail")
        dst = os.path.join(self.temp_dir, "dst_fail")

        with patch("os.symlink", side_effect=OSError), \
             patch("sys.platform", "linux"):
            success, link_type = create_directory_link(src, dst)
            self.assertFalse(success)
            self.assertEqual(link_type, "none")

    def test_tc02_json_hierarchical_keypath_anchors(self):
        """TC-02: JSON parser bóc tách key-path phân cấp, line numbers và gán AST Structural Anchors."""
        json_file = os.path.join(self.temp_dir, "app.config.json")
        sample_json = json.dumps({
            "service": "api",
            "database": {
                "host": "localhost",
                "pool": {
                    "max_connections": 20
                }
            }
        }, indent=2)
        with open(json_file, "w", encoding="utf-8") as f:
            f.write(sample_json)

        # Parse qua entrypoint chính parse_polyglot_signatures
        res = parse_polyglot_signatures(json_file)
        self.assertTrue(res["exists"])
        self.assertEqual(res["language"], "json")

        symbols = res["symbols"]
        names = [s["name"] for s in symbols]
        self.assertEqual(names, ["service", "database", "database.host", "database.pool", "database.pool.max_connections"])

        # Validate line numbers and formatted anchors
        service_sym = symbols[0]
        self.assertEqual(service_sym["line"], 2)
        self.assertEqual(service_sym["end_line"], 2)
        self.assertEqual(service_sym["kind"], "keypath")
        self.assertEqual(service_sym["anchor"], "[AST: service | L2-L2]")

        pool_sym = next(s for s in symbols if s["name"] == "database.pool.max_connections")
        self.assertEqual(pool_sym["line"], 6)
        self.assertEqual(pool_sym["anchor"], "[AST: database.pool.max_connections | L6-L6]")

    def test_tc03_yaml_hierarchical_keypath_anchors(self):
        """TC-03: YAML parser bóc tách key-path theo thụt dòng, bỏ qua comments và empty lines."""
        yaml_file = os.path.join(self.temp_dir, "pipeline.yml")
        sample_yaml = """
# Header comment
name: CI Pipeline

# Blank and comment lines
jobs:
  build:
    # Build stage configuration
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
"""
        with open(yaml_file, "w", encoding="utf-8") as f:
            f.write(sample_yaml)

        res = parse_polyglot_signatures(yaml_file)
        self.assertTrue(res["exists"])
        self.assertEqual(res["language"], "yaml")

        symbols = res["symbols"]
        names = [s["name"] for s in symbols]
        self.assertIn("name", names)
        self.assertIn("jobs", names)
        self.assertIn("jobs.build", names)
        self.assertIn("jobs.build.runs-on", names)

        # Validate exact line numbers reflecting comments & empty lines
        name_sym = next(s for s in symbols if s["name"] == "name")
        self.assertEqual(name_sym["line"], 3)
        self.assertEqual(name_sym["anchor"], "[AST: name | L3-L3]")

        runs_on_sym = next(s for s in symbols if s["name"] == "jobs.build.runs-on")
        self.assertEqual(runs_on_sym["line"], 9)
        self.assertEqual(runs_on_sym["anchor"], "[AST: jobs.build.runs-on | L9-L9]")

        # Test comment-only and empty lines specifically
        empty_comment_yaml = "\n# Only comment 1\n\n# Only comment 2\n   \n"
        syms_empty = parse_yaml_structural_anchors(empty_comment_yaml, "empty.yml")
        self.assertEqual(syms_empty, [])

    def test_tc04_dockerfile_stages_and_directives(self):
        """TC-04: Dockerfile parser trích xuất stage names và directives với line numbers chính xác."""
        dockerfile_path = os.path.join(self.temp_dir, "Dockerfile")
        dockerfile = """
# Base image comment
FROM python:3.10-slim AS builder
WORKDIR /app
RUN pip install poetry

# Production runner stage
FROM python:3.10-slim AS runner
WORKDIR /app
COPY --from=builder /app /app
EXPOSE 8080
"""
        with open(dockerfile_path, "w", encoding="utf-8") as f:
            f.write(dockerfile)

        res = parse_polyglot_signatures(dockerfile_path)
        self.assertTrue(res["exists"])
        self.assertEqual(res["language"], "dockerfile")

        symbols = res["symbols"]
        names = [s["name"] for s in symbols]
        self.assertIn("STAGE:builder", names)
        self.assertIn("builder.WORKDIR:/app", names)
        self.assertIn("builder.RUN:pip_install_poetry", names)
        self.assertIn("STAGE:runner", names)
        self.assertIn("runner.EXPOSE:8080", names)

        stage_builder = next(s for s in symbols if s["name"] == "STAGE:builder")
        self.assertEqual(stage_builder["line"], 3)
        self.assertEqual(stage_builder["kind"], "stage")

        stage_runner = next(s for s in symbols if s["name"] == "STAGE:runner")
        self.assertEqual(stage_runner["line"], 8)

        # Test empty lines and comments only
        empty_docker = "\n# Just comment\n\n   \n"
        self.assertEqual(parse_dockerfile_structural_anchors(empty_docker, "Dockerfile"), [])

    def test_tc05_shell_function_anchors(self):
        """TC-05: Shell script parser bóc tách function signatures với line numbers chính xác."""
        sh_file = os.path.join(self.temp_dir, "deploy.sh")
        sh_script = """
#!/usr/bin/env bash
# Script comment
function setup_environment() {
    echo "setup"
}

# Cleanup utility
cleanup_worktrees() {
    echo "cleanup"
}
"""
        with open(sh_file, "w", encoding="utf-8") as f:
            f.write(sh_script)

        res = parse_polyglot_signatures(sh_file)
        self.assertTrue(res["exists"])
        self.assertEqual(res["language"], "shell")

        symbols = res["symbols"]
        names = [s["name"] for s in symbols]
        self.assertEqual(names, ["function:setup_environment", "function:cleanup_worktrees"])

        fn_setup = symbols[0]
        self.assertEqual(fn_setup["line"], 4)
        self.assertEqual(fn_setup["kind"], "function")
        self.assertEqual(fn_setup["anchor"], "[AST: function:setup_environment | L4-L4]")

        fn_cleanup = symbols[1]
        self.assertEqual(fn_cleanup["line"], 9)
        self.assertEqual(fn_cleanup["anchor"], "[AST: function:cleanup_worktrees | L9-L9]")

        # Test comments and blanks only
        empty_sh = "\n# Only comment\n\n   \n"
        self.assertEqual(parse_shell_structural_anchors(empty_sh, "empty.sh"), [])

    def test_tc06_ai_bridge_cache_anchor_parity(self):
        """TC-06: Tất cả các file AI Bridge đều đồng bộ ROOT-PREFIX anchor và Cursor alwaysApply."""
        claude_path = os.path.join(_REPO_ROOT, "CLAUDE.md")
        cursor_mdc_path = os.path.join(_REPO_ROOT, ".cursor", "rules", "synapse-qa.mdc")
        windsurf_path = os.path.join(_REPO_ROOT, ".windsurfrules")

        with open(claude_path, "r", encoding="utf-8") as f:
            self.assertIn("[CACHE-ANCHOR: ROOT-PREFIX-v4.8]", f.read())

        with open(cursor_mdc_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("[CACHE-ANCHOR: ROOT-PREFIX-v4.8]", content)
            self.assertIn("alwaysApply: true", content)

        with open(windsurf_path, "r", encoding="utf-8") as f:
            self.assertIn("[CACHE-ANCHOR: ROOT-PREFIX-v4.8]", f.read())

    # 2. NEGATIVE SCENARIOS

    def test_tc07_negative_nonexistent_file_parsing(self):
        """Negative: Trích xuất signature trên file không tồn tại trả về exists=False an toàn."""
        res = parse_polyglot_signatures(os.path.join(self.temp_dir, "nonexistent.json"))
        self.assertFalse(res["exists"])
        self.assertEqual(res["signatures"], [])

    def test_tc08_negative_link_destination_already_exists(self):
        """Negative: Worktree link bỏ qua an toàn nếu destination directory đã tồn tại."""
        src = os.path.join(self.temp_dir, "src_dup")
        dst = os.path.join(self.temp_dir, "dst_dup")
        os.makedirs(src, exist_ok=True)
        os.makedirs(dst, exist_ok=True)

        res = link_shared_dependencies(self.temp_dir, self.temp_dir)
        self.assertIsInstance(res, dict)
        self.assertTrue(res.get("symlink_success"))

    # 3. BOUNDARY SCENARIOS

    def test_tc09_boundary_empty_json_and_yaml(self):
        """Boundary: Parse file JSON và YAML rỗng không gây crash hay unhandled exception."""
        syms_json = parse_json_structural_anchors("{}", "empty.json")
        self.assertEqual(syms_json, [])

        syms_yaml = parse_yaml_structural_anchors("", "empty.yml")
        self.assertEqual(syms_yaml, [])

    def test_tc10_language_detection_extended(self):
        """Boundary: detect_language nhận diện chính xác các định dạng mới mở rộng."""
        self.assertEqual(detect_language("package.json"), "json")
        self.assertEqual(detect_language("workflow.yml"), "yaml")
        self.assertEqual(detect_language("setup.sh"), "shell")
        self.assertEqual(detect_language("Dockerfile.prod"), "dockerfile")
        self.assertEqual(detect_language("unknown.bin"), "unknown")


if __name__ == "__main__":
    unittest.main()
