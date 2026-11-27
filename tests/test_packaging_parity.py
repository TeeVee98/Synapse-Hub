#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tests/test_packaging_parity.py — Package Integrity & Strict Release Workflows Test Suite
-----------------------------------------------------------------------------------------
Validates:
  1. Python wheel artifact builds cleanly and includes skills_manifest.json and agent-skills entry point.
  2. Built wheel executes smoke tests in a clean, isolated environment without repository checkout.
  3. tools/author_integrity.py validates licenses from dist-info metadata in isolated environments.
  4. All GitHub Action workflows pin action references to 40-character commit SHAs.
  5. No indiscriminate continue-on-error statements exist in release publishing workflows.
  6. Documentation installation recipes synchronize with package metadata (pip install synapse-hub).
"""

import json
import os
import sys
import re
import glob
import tarfile
import zipfile
import tempfile
import subprocess
import shutil
import pytest
from tools.core.file_lock import FileLock

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WORKFLOW_DIR = os.path.join(REPO_ROOT, ".github", "workflows")
_WHEEL_LOCK = os.path.join(tempfile.gettempdir(), "synapse_wheel_build.lock")


def test_wheel_build_parity_and_entrypoints():
    """Verifies that the wheel builds cleanly and packages skills_manifest.json and all console scripts."""
    with FileLock(_WHEEL_LOCK, timeout=120.0):
        build_dir = os.path.join(REPO_ROOT, "build")
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir, ignore_errors=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [sys.executable, "-m", "pip", "wheel", "--no-deps", "-w", tmpdir, REPO_ROOT]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            assert res.returncode == 0, f"pip wheel build failed:\n{res.stderr}\n{res.stdout}"

            wheels = glob.glob(os.path.join(tmpdir, "*.whl"))
            assert len(wheels) == 1, f"Expected 1 wheel, found: {wheels}"
            wheel_path = wheels[0]

            with zipfile.ZipFile(wheel_path, "r") as zf:
                namelist = zf.namelist()

                # Verify skills_manifest.json is packaged
                has_manifest = any("skills_manifest.json" in n for n in namelist)
                assert has_manifest, f"skills_manifest.json missing from wheel namelist: {namelist[:20]}"

                # Verify entry_points.txt declares agent-skills
                ep_entries = [n for n in namelist if n.endswith("entry_points.txt")]
                assert ep_entries, "entry_points.txt not found in wheel dist-info"
                ep_content = zf.read(ep_entries[0]).decode("utf-8")

                expected_scripts = ["agent-qa", "agent-skills", "synapse", "synapse-hub"]
                for script in expected_scripts:
                    assert f"{script} = tools.core.cli:main" in ep_content, (
                        f"Console script '{script}' missing from wheel entry_points.txt:\n{ep_content}"
                    )


def test_wheel_smoke_in_isolated_environment():
    """Verifies that the built wheel executes smoke commands in an isolated directory without repository checkout."""
    with FileLock(_WHEEL_LOCK, timeout=120.0):
        build_dir = os.path.join(REPO_ROOT, "build")
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir, ignore_errors=True)
        # Clean ephemeral lock files that could conflict with wheel build on Windows
        for lock_file in glob.glob(os.path.join(REPO_ROOT, "tools", "*.lock")):
            try:
                os.remove(lock_file)
            except OSError:
                pass
        with tempfile.TemporaryDirectory() as wheel_dir, tempfile.TemporaryDirectory() as isolated_env:
            # 1. Build the wheel
            cmd = [sys.executable, "-m", "pip", "wheel", "--no-deps", "-w", wheel_dir, REPO_ROOT]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            assert res.returncode == 0, f"pip wheel failed: {res.stderr}"
            wheel_path = glob.glob(os.path.join(wheel_dir, "*.whl"))[0]

            # 2. Extract wheel into an isolated directory (simulating site-packages)
            with zipfile.ZipFile(wheel_path, "r") as zf:
                zf.extractall(isolated_env)

            # 3. Execute `tools.cli:main version` in isolated environment (outside repo checkout)
            runner_code = (
                "import sys; "
                f"sys.path.insert(0, r'{isolated_env}'); "
                "from tools.core.cli import main; "
                "sys.argv = ['agent-qa', 'version']; "
                "main()"
            )
            run_env = os.environ.copy()
            run_env["PYTHONIOENCODING"] = "utf-8"
            run_res = subprocess.run(
                [sys.executable, "-c", runner_code],
                cwd=isolated_env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=run_env,
                timeout=30,
            )
            assert run_res.returncode == 0, (
                f"Isolated CLI version execution failed (exit code {run_res.returncode}):\n"
                f"stdout: {run_res.stdout}\nstderr: {run_res.stderr}"
            )
            assert "Agent-QA Hub CLI v" in run_res.stdout
            assert "Catalog: 57 Standardized Skills" in run_res.stdout
            assert "Thế Vị (@TeeVee98)" in run_res.stdout

            # 4. Execute `tools.cli:main skills --list-profiles`
            runner_skills = (
                "import sys; "
                f"sys.path.insert(0, r'{isolated_env}'); "
                "from tools.core.cli import main; "
                "sys.argv = ['agent-qa', 'skills', '--list-profiles']; "
                "main()"
            )
            skills_res = subprocess.run(
                [sys.executable, "-c", runner_skills],
                cwd=isolated_env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=run_env,
                timeout=30,
            )
            assert skills_res.returncode == 0, (
                f"Isolated CLI skills execution failed (exit code {skills_res.returncode}):\n"
                f"stdout: {skills_res.stdout}\nstderr: {skills_res.stderr}"
            )
            assert "core-web-qa" in skills_res.stdout
            assert "perf-and-load" in skills_res.stdout


def test_author_integrity_handles_dist_info_licenses():
    """Verifies that author_integrity.py correctly resolves licenses from dist-info directories when root LICENSE is absent."""
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))
    from author_integrity import verify_author_attribution, assert_integrity_or_raise, _resolve_license_content

    # In current repository root, LICENSE exists and passes
    valid, violations = verify_author_attribution(REPO_ROOT)
    assert valid, f"Repository author attribution failed: {violations}"
    assert assert_integrity_or_raise(REPO_ROOT) is True

    # In a simulated isolated site-packages environment (where LICENSE is in dist-info/licenses/)
    with tempfile.TemporaryDirectory() as fake_site_packages:
        dist_info = os.path.join(fake_site_packages, "synapse_hub-4.1.4.dist-info", "licenses")
        os.makedirs(dist_info, exist_ok=True)

        # Copy canonical LICENSE into dist-info
        canonical_lic = os.path.join(REPO_ROOT, "LICENSE")
        with open(canonical_lic, "r", encoding="utf-8") as f:
            lic_body = f.read()
        with open(os.path.join(dist_info, "LICENSE"), "w", encoding="utf-8") as f:
            f.write(lic_body)

        # Ensure no root LICENSE exists in fake_site_packages
        assert not os.path.exists(os.path.join(fake_site_packages, "LICENSE"))

        # Verify that _resolve_license_content finds dist-info/licenses/LICENSE
        content, src = _resolve_license_content(fake_site_packages)
        assert content is not None, "Failed to resolve license from dist-info"
        assert "Thế Vị" in content

        # Verify attribution check passes in simulated site-packages
        valid_iso, viols_iso = verify_author_attribution(fake_site_packages)
        assert valid_iso, f"Expected valid attribution in isolated dist-info: {viols_iso}"

        # Negative test: corrupted license notice raises violation
        with open(os.path.join(dist_info, "LICENSE"), "w", encoding="utf-8") as f:
            f.write("Altered license without author attribution.")
        bad_valid, bad_viols = verify_author_attribution(fake_site_packages)
        assert not bad_valid
        assert any("LICENSE" in v for v in bad_viols)


def test_workflow_actions_pinned_to_full_commit_shas():
    """Verifies that all GitHub Action references across all .github/workflows/*.yml files are pinned to full 40-character SHAs."""
    workflow_files = glob.glob(os.path.join(WORKFLOW_DIR, "*.yml"))
    assert len(workflow_files) >= 5, f"Expected at least 5 workflow files, found: {workflow_files}"

    sha_pattern = re.compile(r"^[a-zA-Z0-9_\-\.\/]+@[0-9a-f]{40}(\s*#.*)?$")
    unpinned = []

    for wf in workflow_files:
        with open(wf, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("uses:"):
                action_ref = stripped.split("uses:", 1)[1].strip()
                # Exclude local composite actions like `./.github/actions/...`
                if action_ref.startswith("./"):
                    continue
                if not sha_pattern.match(action_ref):
                    unpinned.append(f"{os.path.basename(wf)}:{idx}: {action_ref}")

    assert not unpinned, (
        f"Found {len(unpinned)} unpinned GitHub Action reference(s) (must use 40-char SHA):\n"
        + "\n".join(unpinned)
    )


def test_no_indiscriminate_continue_on_error_in_workflows():
    """Verifies that no publish job or step uses indiscriminate continue-on-error: true."""
    publish_wf = os.path.join(WORKFLOW_DIR, "publish_npm.yml")
    assert os.path.exists(publish_wf), f"Workflow file not found: {publish_wf}"

    with open(publish_wf, "r", encoding="utf-8") as f:
        content = f.read()

    # Assert no continue-on-error exists in publish_npm.yml
    assert "continue-on-error: true" not in content, (
        "publish_npm.yml must not contain indiscriminate continue-on-error: true"
    )

    # Verify duplicate version regex catches exact expected patterns
    expected_regex = r"EPUBLISHCONFLICT|previously published|already exists|409 Conflict"
    assert "EPUBLISHCONFLICT|previously published|already exists|409 Conflict" in content, (
        f"Missing exact duplicate conflict pattern '{expected_regex}' in publish_npm.yml"
    )

    # Verify all workflows have no continue-on-error: true
    for wf in glob.glob(os.path.join(WORKFLOW_DIR, "*.yml")):
        with open(wf, "r", encoding="utf-8") as f:
            c = f.read()
        assert "continue-on-error: true" not in c, (
            f"Indiscriminate continue-on-error: true found in {os.path.basename(wf)}"
        )


def test_readme_install_recipe_parity():
    """Verifies that README.md and README.en.md use verified GitHub pip install instead of stale PyPI claims."""
    expected_pip_recipe = "pip install git+https://github.com/TeeVee98/Synapse-Hub.git"
    for filename in ["README.md", "README.en.md"]:
        path = os.path.join(REPO_ROOT, filename)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "pip install agent-qa" not in content, (
            f"{filename} contains outdated 'pip install agent-qa' reference"
        )
        assert "pip install synapse-hub" not in content, (
            f"{filename} contains unverified PyPI 'pip install synapse-hub' claim"
        )
        assert expected_pip_recipe in content, (
            f"{filename} missing synchronized '{expected_pip_recipe}' reference"
        )


def test_manifest_fallback_resolution_and_error_handling():
    """Verifies fallback manifest resolution and graceful error handling when manifest is missing."""
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))
    import skill_profiles

    # 1. Normal resolution finds root skills_manifest.json
    resolved = skill_profiles.resolve_manifest_path(REPO_ROOT)
    assert resolved is not None and os.path.isfile(resolved)
    mf = skill_profiles.load_manifest(resolved)
    assert mf.get("totalSkills") == 57

    # 2. In a directory with no manifest, raises FileNotFoundError with clear actionable instructions
    with tempfile.TemporaryDirectory() as empty_dir:
        with pytest.raises(FileNotFoundError) as exc_info:
            skill_profiles.load_manifest(os.path.join(empty_dir, "skills_manifest.json"))
        err_text = str(exc_info.value)
        assert "Skills manifest could not be located" in err_text or "Ensure Synapse Hub" in err_text


def _pack_npm_tarball(pack_dir: str) -> str:
    """Packs the repository npm tarball into pack_dir and returns the .tgz path."""
    npm_bin = shutil.which("npm")
    assert npm_bin, "npm executable not found in PATH"
    res = subprocess.run(
        [npm_bin, "pack", "--pack-destination", pack_dir],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert res.returncode == 0, f"npm pack failed:\n{res.stderr}\n{res.stdout}"
    tgz_files = glob.glob(os.path.join(pack_dir, "*.tgz"))
    assert len(tgz_files) == 1, f"Expected 1 .tgz tarball, found: {tgz_files}"
    return tgz_files[0]


def test_npm_tarball_installs_catalog_and_workflow_skills_clean_client():
    """Positive: Packed npm .tgz ships .agent/skills & .claude/commands and installs all 57+3 skills."""
    npm_bin = shutil.which("npm")
    assert npm_bin, "npm executable not found in PATH"
    with tempfile.TemporaryDirectory() as pack_dir, tempfile.TemporaryDirectory() as client_dir:
        tarball = _pack_npm_tarball(pack_dir)
        with tarfile.open(tarball, "r:gz") as tf:
            names = set(tf.getnames())
        for wf in ("solo", "review", "super-plan"):
            assert f"package/.agent/skills/{wf}/SKILL.md" in names, f"Missing workflow skill {wf} in tarball"
            assert f"package/.claude/commands/{wf}.md" in names, f"Missing Claude command {wf} in tarball"

        inst = subprocess.run(
            [npm_bin, "install", "--offline", "--no-audit", "--no-fund", tarball],
            cwd=client_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert inst.returncode == 0, f"npm install tarball failed:\n{inst.stderr}\n{inst.stdout}"

        cli_bin = os.path.join(client_dir, "node_modules", ".bin", "agent-qa")
        setup_res = subprocess.run(
            [cli_bin, "setup", client_dir, "--ide", "codex", "--no-git-hook"],
            cwd=client_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert setup_res.returncode == 0, f"agent-qa setup failed:\n{setup_res.stderr}\n{setup_res.stdout}"

        skills_dir = os.path.join(client_dir, ".agents", "skills")
        for wf in ("solo", "review", "super-plan"):
            assert os.path.isfile(os.path.join(skills_dir, wf, "SKILL.md")), f"Workflow {wf} not installed in client"
        with open(os.path.join(REPO_ROOT, "skills_index.json"), "r", encoding="utf-8") as idx_fp:
            catalog_ids = [item["id"] for item in json.load(idx_fp)["skills"]]
        for sid in catalog_ids:
            assert os.path.isfile(os.path.join(skills_dir, sid, "SKILL.md")), f"Catalog skill {sid} missing in client"


def test_npm_tarball_upgrade_preserves_user_owned_skill_bytes():
    """Boundary & Resilience: Repeat setup and upgrade from tarball preserve user-owned skill bytes."""
    npm_bin = shutil.which("npm")
    assert npm_bin, "npm executable not found in PATH"
    with tempfile.TemporaryDirectory() as pack_dir, tempfile.TemporaryDirectory() as client_dir:
        tarball = _pack_npm_tarball(pack_dir)
        inst = subprocess.run(
            [npm_bin, "install", "--offline", "--no-audit", "--no-fund", tarball],
            cwd=client_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert inst.returncode == 0
        cli_bin = os.path.join(client_dir, "node_modules", ".bin", "agent-qa")

        first = subprocess.run(
            [cli_bin, "setup", client_dir, "--ide", "codex", "--no-git-hook"],
            cwd=client_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert first.returncode == 0

        user_skill_dir = os.path.join(client_dir, ".agents", "skills", "user-owned-smoke")
        os.makedirs(user_skill_dir, exist_ok=True)
        user_skill_file = os.path.join(user_skill_dir, "SKILL.md")
        expected_bytes = b"---\nname: user-owned-smoke\n---\n# Custom team workflow bytes v1\n"
        with open(user_skill_file, "wb") as ufp:
            ufp.write(expected_bytes)

        upgrade = subprocess.run(
            [cli_bin, "setup", client_dir, "--ide", "codex", "--no-git-hook"],
            cwd=client_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert upgrade.returncode == 0
        with open(user_skill_file, "rb") as ufp:
            assert ufp.read() == expected_bytes
        for wf in ("solo", "review", "super-plan"):
            assert os.path.isfile(os.path.join(client_dir, ".agents", "skills", wf, "SKILL.md"))


def test_npm_manifest_and_publish_workflow_tarball_contract():
    """Negative & CLI Contract: package.json ships workflow dirs and publish_npm.yml publishes tested tarball."""
    with open(os.path.join(REPO_ROOT, "package.json"), "r", encoding="utf-8") as pkg_fp:
        pkg = json.load(pkg_fp)
    files_list = pkg.get("files", [])
    assert any(p in files_list for p in (".agent", ".agent/skills")), "package.json missing .agent/skills"
    assert any(p in files_list for p in (".claude", ".claude/commands")), "package.json missing .claude/commands"

    with open(os.path.join(WORKFLOW_DIR, "publish_npm.yml"), "r", encoding="utf-8") as wf_fp:
        wf_text = wf_fp.read()
    assert "npm pack" in wf_text, "publish_npm.yml must pack a .tgz tarball before publishing"
    assert ".tgz" in wf_text or "TARBALL_PATH" in wf_text, "publish_npm.yml must verify and publish packed tarball"
    assert "sha256" in wf_text.lower(), "publish_npm.yml must record tested tarball digest"

    # Negative check: stripping one workflow from an unpacked package leaves < 3 workflows installed
    with tempfile.TemporaryDirectory() as pkg_copy, tempfile.TemporaryDirectory() as client_dir:
        shutil.copytree(os.path.join(REPO_ROOT, "skills"), os.path.join(pkg_copy, "skills"))
        shutil.copytree(os.path.join(REPO_ROOT, ".agent"), os.path.join(pkg_copy, ".agent"))
        shutil.rmtree(os.path.join(pkg_copy, ".agent", "skills", "review"))
        sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "core"))
        import setup_project
        orig_hub_root = setup_project.HUB_ROOT
        try:
            setup_project.HUB_ROOT = pkg_copy
            setup_project.install_codex_skills(client_dir)
        finally:
            setup_project.HUB_ROOT = orig_hub_root
        assert not os.path.exists(os.path.join(client_dir, ".agents", "skills", "review", "SKILL.md"))


def test_wheel_packages_workflow_skills_parity():
    """Positive & Boundary: Built Python wheel contains solo, review, and super-plan workflow SKILL.md files."""
    with FileLock(_WHEEL_LOCK, timeout=120.0):
        build_dir = os.path.join(REPO_ROOT, "build")
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir, ignore_errors=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            res = subprocess.run(
                [sys.executable, "-m", "pip", "wheel", "--no-deps", "-w", tmpdir, REPO_ROOT],
                capture_output=True,
                text=True,
                timeout=120,
            )
            assert res.returncode == 0, f"pip wheel failed:\n{res.stderr}\n{res.stdout}"
            wheels = glob.glob(os.path.join(tmpdir, "*.whl"))
            assert len(wheels) == 1
            with zipfile.ZipFile(wheels[0], "r") as zf:
                namelist = zf.namelist()
            for wf in ("solo", "review", "super-plan"):
                assert any(n.endswith(f".agent/skills/{wf}/SKILL.md") for n in namelist), (
                    f"Wheel missing .agent/skills/{wf}/SKILL.md"
                )
                assert any(n.endswith(f".claude/commands/{wf}.md") for n in namelist), (
                    f"Wheel missing .claude/commands/{wf}.md"
                )
