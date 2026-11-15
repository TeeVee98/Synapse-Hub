#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_release_engineering_and_packaging.py
-----------------------------------------------
Acceptance verification for Task 7: Release Engineering, Distribution Parity,
and Clean Onboarding:
  1. Build wheel & npm tarball, install into isolated temp envs outside checkout.
  2. Prove zero imports from source checkout when installed via pip wheel.
  3. Verify resource parity across Python wheel and NPM tarball (53 skills, 13 rules, 9 subagents).
  4. Verify dynamic CLI command list generated from subparsers registry.
  5. Verify elimination of brittle static test/gate/command numbers.
  6. Verify CHANGELOG clearly separates [Unreleased] from published [4.1.4].
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools import cli
from tools.core import i18n

with open(os.path.join(REPO_ROOT, "package.json"), "r", encoding="utf-8") as f:
    CURRENT_VERSION = json.load(f).get("version", "4.1.4")


class TestReleaseEngineeringAndPackaging(unittest.TestCase):
    """Rigorous acceptance test suite for Release Engineering and Packaging Parity."""

    @classmethod
    def setUpClass(cls):
        """Builds Python wheel distribution once for test class."""
        cls.dist_dir = os.path.join(REPO_ROOT, "dist")
        os.makedirs(cls.dist_dir, exist_ok=True)
        # Build wheel using setuptools / build
        cmd = [sys.executable, "-m", "build", "--wheel", "--no-isolation"]
        res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Wheel build failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")

        whl_files = [
            os.path.join(cls.dist_dir, f)
            for f in os.listdir(cls.dist_dir)
            if f.endswith(".whl") and f"synapse_hub-{CURRENT_VERSION}" in f
        ]
        if not whl_files:
            whl_files = [os.path.join(cls.dist_dir, f) for f in os.listdir(cls.dist_dir) if f.endswith(".whl")]
        if not whl_files:
            raise FileNotFoundError(f"Built wheel not found in {cls.dist_dir}")
        cls.wheel_path = sorted(whl_files, key=os.path.getmtime)[-1]

    def test_wheel_contains_all_capabilities_and_zero_teamwork(self):
        """Verifies wheel packages 53 skills, 13 rules, 9 subagents, and excludes teamwork scratch."""
        with zipfile.ZipFile(self.wheel_path, "r") as z:
            names = z.namelist()

            # 1. Manifest and AGENTS.md present
            self.assertIn("skills_manifest.json", names, "skills_manifest.json missing from wheel")
            self.assertIn("AGENTS.md", names, "AGENTS.md missing from wheel")

            # 2. 53 Skills with SKILL.md
            skills = [n for n in names if n.startswith(".agents/skills/") and n.endswith("/SKILL.md")]
            self.assertEqual(len(skills), 53, f"Expected 53 skills in wheel, found {len(skills)}")

            # 3. 13 Core Rules
            rules = [n for n in names if n.startswith(".agents/rules/") and n.endswith(".md")]
            self.assertEqual(len(rules), 13, f"Expected 13 rules in wheel, found {len(rules)}")

            # 4. 9 Subagent profiles
            agents = [n for n in names if n.startswith(".agents/agents/") and n.endswith(".md")]
            self.assertEqual(len(agents), 9, f"Expected 9 subagents in wheel, found {len(agents)}")

            # 5. Strict zero-leakage: No teamwork scratch files in wheel
            teamwork = [n for n in names if ".agents/teamwork" in n]
            self.assertEqual(len(teamwork), 0, f"Found prohibited teamwork files in wheel: {teamwork}")

    def test_wheel_isolated_install_and_zero_source_checkout_import(self):
        """Installs wheel in clean isolated venv outside repo checkout, verifying zero source imports."""
        with tempfile.TemporaryDirectory() as td:
            venv_dir = os.path.join(td, "isolated_venv")
            subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True, capture_output=True)

            pip_bin = os.path.join(venv_dir, "bin", "pip")
            py_bin = os.path.join(venv_dir, "bin", "python")
            agent_qa_bin = os.path.join(venv_dir, "bin", "agent-qa")

            # Install wheel into isolated venv
            install_res = subprocess.run([pip_bin, "install", self.wheel_path], capture_output=True, text=True)
            self.assertEqual(install_res.returncode, 0, f"pip install failed:\n{install_res.stderr}")

            # Run in a clean external workspace directory with NO synapse-hub files
            external_workdir = os.path.join(td, "user_project")
            os.makedirs(external_workdir)

            # 1. Test CLI entrypoint --version
            v_res = subprocess.run([agent_qa_bin, "--version"], cwd=external_workdir, capture_output=True, text=True)
            self.assertEqual(v_res.returncode, 0)
            self.assertIn(CURRENT_VERSION, v_res.stdout)

            # 2. Test CLI entrypoint skills list
            s_res = subprocess.run([agent_qa_bin, "skills"], cwd=external_workdir, capture_output=True, text=True)
            self.assertEqual(s_res.returncode, 0)
            self.assertIn("53", s_res.stdout)

            # 3. Test Python import in external process with strict source isolation check
            probe_script = f"""
import os, sys
import tools
from tools import rules_router, cli
from tools.core import token_estimator

# Verify tools does NOT import from repository checkout
source_repo = {repr(REPO_ROOT)}
assert not tools.__file__.startswith(source_repo), f"Leak: imported from source checkout {{tools.__file__}}"
assert venv_site_packages in tools.__file__, f"Expected venv site-packages, got {{tools.__file__}}"

# Verify repo_root resolves to site-packages directory
repo_root = rules_router._find_repo_root()
assert os.path.isdir(os.path.join(repo_root, ".agents", "skills")), f"Skills dir missing in {{repo_root}}"
assert os.path.isfile(os.path.join(repo_root, "skills_manifest.json")), f"Manifest missing in {{repo_root}}"

# Verify manifest discovery
manifest = token_estimator._get_skills_manifest(repo_root)
assert len(manifest) == 53, f"Expected 53 skills from manifest, got {{len(manifest)}}"

# Verify full routing & hydration in isolated venv
route_result = rules_router.route_rules(os.getcwd(), task_type="api")
assert len(route_result["recommended_rules"]) > 0, "No recommended rules routed"
assert len(route_result["recommended_skills"]) > 0, "No recommended skills routed"
assert "token_metrics" in route_result, "token_metrics missing in route_result"
metrics = route_result["token_metrics"]
assert "estimated_hydration_tokens" in metrics, "Hydration tokens missing"
assert metrics["estimated_hydration_tokens"] > 0, "Hydration tokens must be positive"

print("ISOLATED_INSTALL_VERIFIED_SUCCESS")
"""
            sp_dir = os.path.join(venv_dir, "lib")
            site_packages_hint = "site-packages"

            env = os.environ.copy()
            # Clear PYTHONPATH so it cannot inherit parent repo
            env.pop("PYTHONPATH", None)

            probe_runner = f"""
venv_site_packages = {repr(site_packages_hint)}
{probe_script}
"""
            probe_res = subprocess.run(
                [py_bin, "-c", probe_runner],
                cwd=external_workdir,
                env=env,
                capture_output=True,
                text=True
            )
            self.assertEqual(probe_res.returncode, 0, f"Probe failed:\n{probe_res.stderr}\n{probe_res.stdout}")
            self.assertIn("ISOLATED_INSTALL_VERIFIED_SUCCESS", probe_res.stdout)

    def test_npm_tarball_packaging_and_resource_parity(self):
        """Packs npm tarball and verifies parity of resources (.agents, skills, rules) and bin entrypoint."""
        npm_bin = shutil.which("npm")
        node_bin = shutil.which("node")
        if not npm_bin or not node_bin:
            self.skipTest("npm or node not installed on host")

        with tempfile.TemporaryDirectory() as td:
            pack_res = subprocess.run([npm_bin, "pack", "--pack-destination", td], cwd=REPO_ROOT, capture_output=True, text=True)
            self.assertEqual(pack_res.returncode, 0, f"npm pack failed: {pack_res.stderr}")

            tgz_files = [f for f in os.listdir(td) if f.endswith(".tgz")]
            self.assertTrue(len(tgz_files) > 0, "No npm tarball generated")
            tarball_path = os.path.join(td, tgz_files[0])

            # Unpack tarball in clean directory
            unpack_dir = os.path.join(td, "unpacked")
            os.makedirs(unpack_dir)
            subprocess.run(["tar", "-xzf", tarball_path, "-C", unpack_dir], check=True)

            pkg_root = os.path.join(unpack_dir, "package")
            self.assertTrue(os.path.isdir(pkg_root), "Unpacked package root not found")

            # 1. Verify bin/agent-qa.js execution
            version_res = subprocess.run([node_bin, "bin/agent-qa.js", "version"], cwd=pkg_root, capture_output=True, text=True)
            self.assertEqual(version_res.returncode, 0, f"agent-qa.js version failed: {version_res.stderr}")
            self.assertIn(CURRENT_VERSION, version_res.stdout)
            self.assertIn("53 Standardized Skills", version_res.stdout)

            # 2. Verify skills & rules present
            skills_dir = os.path.join(pkg_root, ".agents", "skills")
            rules_dir = os.path.join(pkg_root, ".agents", "rules")
            self.assertTrue(os.path.isdir(skills_dir), "skills dir missing from npm package")
            self.assertTrue(os.path.isdir(rules_dir), "rules dir missing from npm package")

            # 3. Verify zero teamwork scratch
            teamwork_dir = os.path.join(pkg_root, ".agents", "teamwork")
            self.assertFalse(os.path.exists(teamwork_dir), "teamwork scratch files must not be in npm tarball")

    def test_dynamic_cli_command_list_generation(self):
        """Verifies get_registered_commands dynamically introspects subparsers and powers --json / --markdown."""
        parser = cli.build_parser("en")
        commands = cli.get_registered_commands(parser, "en")

        self.assertGreaterEqual(len(commands), 50, "Expected at least 50 commands registered")
        names = {c["name"] for c in commands}
        self.assertIn("verify", names)
        self.assertIn("mutate", names)
        self.assertIn("rules-router", names)
        self.assertIn("doctor", names)
        self.assertIn("help", names)

        for cmd in commands:
            self.assertTrue(cmd["name"], "Command name must be non-empty")
            self.assertTrue(cmd["prog"].startswith("agent-qa "), f"Invalid prog: {cmd['prog']}")

        # Test CLI help --json
        res_json = subprocess.run([sys.executable, "tools/cli.py", "help", "--json"], cwd=REPO_ROOT, capture_output=True, text=True)
        self.assertEqual(res_json.returncode, 0, res_json.stderr)
        parsed_json = json.loads(res_json.stdout)
        self.assertEqual(len(parsed_json), len(commands))

        # Test CLI help --markdown
        res_md = subprocess.run([sys.executable, "tools/cli.py", "help", "--markdown"], cwd=REPO_ROOT, capture_output=True, text=True)
        self.assertEqual(res_md.returncode, 0, res_md.stderr)
        self.assertIn("| Command | Aliases | Description |", res_md.stdout)
        self.assertIn("`verify`", res_md.stdout)

    def test_zero_stale_static_numbers(self):
        """Ensures i18n, welcome_page, and README have no stale static test or command counts."""
        # 1. i18n should not contain hardcoded "58+" commands
        self.assertNotIn("58+", i18n.MESSAGES["en"]["opt_all"])
        self.assertNotIn("58+", i18n.MESSAGES["vi"]["opt_all"])
        self.assertNotIn("58+", i18n.MESSAGES["en"]["tip_all"])
        self.assertNotIn("58+", i18n.MESSAGES["vi"]["tip_all"])

        # 2. welcome_page fallback totalSkills must match current manifest (53)
        from tools import welcome_page
        meta = welcome_page.get_hub_metadata()
        self.assertEqual(meta["totalSkills"], 53)

        # 3. README.md & README.en.md badges should not contain hardcoded 1001+ tests
        for fname in ("README.md", "README.en.md"):
            with open(os.path.join(REPO_ROOT, fname), "r", encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn("tests-1001%2B", content, f"{fname} has stale 1001+ test badge")

    def test_changelog_separates_unreleased_from_published_v414(self):
        """Verifies CHANGELOG.md strictly distinguishes [Unreleased] from published [4.1.4]."""
        changelog_path = os.path.join(REPO_ROOT, "CHANGELOG.md")
        self.assertTrue(os.path.isfile(changelog_path))
        with open(changelog_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Both sections must exist
        self.assertIn("## [Unreleased]", content)
        self.assertIn("## [4.1.4] - 2026-11-14", content)

        # Unreleased section must come before [4.1.4]
        unreleased_idx = content.index("## [Unreleased]")
        v414_idx = content.index("## [4.1.4] - 2026-11-14")
        self.assertLess(unreleased_idx, v414_idx, "[Unreleased] must precede [4.1.4]")

        # Post-4.1.4 features must reside in [Unreleased]
        unreleased_text = content[unreleased_idx:v414_idx]
        self.assertIn("Release Packaging Parity", unreleased_text)
        self.assertIn("Direct CLI & API Consent Boundaries", unreleased_text)
        self.assertIn("Canonical Skill Folder Content Digest", unreleased_text)
        self.assertIn("Quality Metrics & CI Semantics", unreleased_text)

        # Published 4.1.4 must retain historical release scope
        published_text = content[v414_idx:content.index("## [4.1.3]")]
        self.assertIn("Attribution & License Integrity Guard", published_text)
        self.assertIn("Enterprise Audit Report", published_text)


if __name__ == "__main__":
    unittest.main()
