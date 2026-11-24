#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
tools/bump_version.py — Atomic Universal Version Bumper for Synapse Hub

Synchronizes version numbers across all polyglot targets in a single command:
  1. package.json (NPM)
  2. pyproject.toml (Python/Poetry/PEP 621)
  3. skills_manifest.json (Skill Catalog Index)
  4. agentskills.json (Agent Skills Manifest)
  5. tools/cli.py (Agent-QA CLI)
  6. tools/mcp_server.py (MCP Protocol Server)
  7. tools/browser_helpers.js (In-Browser CDP Helper)
  8. tools/mcp_excel_server.py (Excel MCP Service)
  9. docs/ARCHITECTURE.md (Architecture Specifications)
  10. README.md (Bilingual Documentation & Badges)

Usage:
  python3 tools/bump_version.py patch                  # 2.0.1 -> 2.0.2
  python3 tools/bump_version.py minor                  # 2.0.1 -> 2.1.0
  python3 tools/bump_version.py major                  # 2.0.1 -> 3.0.0
  python3 tools/bump_version.py 2.0.5                  # Explicit version
  python3 tools/bump_version.py patch --commit         # Bump + git commit
  python3 tools/bump_version.py patch --commit --push  # Bump + commit + git push + tag
  python3 tools/bump_version.py patch --dry-run        # Preview only
"""
import os
import sys

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass


import sys
import os
import re
import json
import argparse
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class VsixBumpDecisionDTO:
    """Decision record for guarded VSIX link rewriting during version bumps."""

    target_version: str
    vsix_path: str
    artifact_exists: bool
    rewritten: bool

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def parse_semver(v_str: str):
    """Parses a semantic version string into major, minor, patch integers and optional suffix.

    Args:
        v_str: The version string to parse (e.g. '2.9.0' or '2.9.0-rc1').

    Returns:
        A tuple of (major, minor, patch, suffix).

    Raises:
        ValueError: If the string does not follow semantic versioning.
    """
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)$", v_str.strip())
    if not m:
        raise ValueError(f"Invalid semver: '{v_str}'. Must follow major.minor.patch[-suffix]")
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)

def calculate_next_version(current: str, action: str) -> str:
    """Computes the target version based on an action or explicit semver string.

    Args:
        current: Current semver version string.
        action: 'patch', 'minor', 'major', or an explicit target version string.

    Returns:
        The computed next semver version string.
    """
    major, minor, patch, suffix = parse_semver(current)
    action = action.lower()
    if action == "patch":
        return f"{major}.{minor}.{patch + 1}"
    elif action == "minor":
        return f"{major}.{minor + 1}.0"
    elif action == "major":
        return f"{major + 1}.0.0"
    else:
        # Validate that action itself is a valid semver
        parse_semver(action)
        return action

def get_current_version() -> str:
    """Reads the current canonical version from package.json in the repository root.

    Returns:
        The version string.

    Raises:
        ValueError: If package.json is missing or lacks a valid version field.
    """
    pkg_file = os.path.join(REPO_ROOT, "package.json")
    with open(pkg_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    version = data.get("version")
    if not version:
        raise ValueError("package.json does not contain a valid 'version' field.")
    return version

ORIGINAL_SNAPSHOTS = {}

def rollback_all_files():
    """Restores all modified files to their original snapshot on failure."""
    if not ORIGINAL_SNAPSHOTS:
        return
    print("\n🔄 Rolling back version changes across files to restore clean working tree...")
    for fpath, orig_text in ORIGINAL_SNAPSHOTS.items():
        try:
            with open(fpath, "w", encoding="utf-8", newline="\n") as rf:
                rf.write(orig_text)
            print(f"  [RESTORED] {os.path.relpath(fpath, REPO_ROOT)}")
        except Exception as e:
            print(f"  [ERROR] Failed to restore {fpath}: {e}")

def update_json_root_version(rel_path: str, new_ver: str, dry_run: bool = False) -> bool:
    """Updates the top-level 'version' property in a JSON manifest file.

    Args:
        rel_path: Relative path to the target JSON file from repo root.
        new_ver: Target version string.
        dry_run: If True, previews changes without writing to disk.

    Returns:
        True if the file was modified or would be updated.
    """
    full_path = os.path.join(REPO_ROOT, rel_path)
    if not os.path.exists(full_path):
        print(f"  [WARN] File not found: {rel_path}")
        return False

    with open(full_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as err:
        print(f"  [ERROR] Invalid JSON in {rel_path}: {err}")
        return False

    old_ver = data.get("version")
    if old_ver == new_ver:
        print(f"  [SKIP] {rel_path} already at v{new_ver}")
        return False

    if not dry_run and full_path not in ORIGINAL_SNAPSHOTS:
        ORIGINAL_SNAPSHOTS[full_path] = raw_text

    data["version"] = new_ver
    if not dry_run:
        with open(full_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"  [UPDATED] {rel_path} (root version {old_ver} -> {new_ver})")
    else:
        print(f"  [DRY-RUN] Would update {rel_path} (root version {old_ver} -> {new_ver})")
    return True

def update_file(rel_path: str, pattern: str, replacement: str, dry_run: bool = False) -> bool:
    """Performs regex replacement within a target file to update version strings.

    Args:
        rel_path: Relative path to the target file from repo root.
        pattern: Regular expression pattern matching existing version occurrences.
        replacement: String replacement containing the new version.
        dry_run: If True, previews changes without writing to disk.

    Returns:
        True if matches were found and updated.
    """
    full_path = os.path.join(REPO_ROOT, rel_path)
    if not os.path.exists(full_path):
        print(f"  [WARN] File not found: {rel_path}")
        return False

    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_content, count = re.subn(pattern, replacement, content)
    if count == 0 or new_content == content:
        print(f"  [SKIP] No version change needed in {rel_path}")
        return False

    if not dry_run and full_path not in ORIGINAL_SNAPSHOTS:
        ORIGINAL_SNAPSHOTS[full_path] = content

    if not dry_run:
        with open(full_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_content)
        print(f"  [UPDATED] {rel_path} ({count} occurrence{'s' if count > 1 else ''})")
    else:
        print(f"  [DRY-RUN] Would update {rel_path} ({count} occurrence{'s' if count > 1 else ''})")
    return True

def update_vsix_links(new_ver: str, dry_run: bool = False) -> VsixBumpDecisionDTO:
    """Guards VSIX link rewrites behind physical artifact existence on disk."""
    vsix_rel = f"editors/vscode/dist/synapse-hub-vscode-{new_ver}.vsix"
    vsix_abs = os.path.join(REPO_ROOT, "editors", "vscode", "dist", f"synapse-hub-vscode-{new_ver}.vsix")
    if not os.path.isfile(vsix_abs):
        print(f"  [WARN] VSIX artifact missing at {vsix_rel}; skipping .vsix link rewrite.")
        return VsixBumpDecisionDTO(
            target_version=new_ver,
            vsix_path=vsix_rel,
            artifact_exists=False,
            rewritten=False,
        )

    pattern = r'(synapse-hub-vscode-)[0-9]+\.[0-9]+\.[0-9]+(\.vsix)'
    replacement = rf"\g<1>{new_ver}\g<2>"
    rewritten = any([
        update_file("editors/vscode/README.md", pattern, replacement, dry_run),
        update_file("README.md", pattern, replacement, dry_run),
        update_file("README.en.md", pattern, replacement, dry_run),
    ])
    return VsixBumpDecisionDTO(
        target_version=new_ver,
        vsix_path=vsix_rel,
        artifact_exists=True,
        rewritten=rewritten,
    )


def update_readme_action_pins(new_ver: str, dry_run: bool = False) -> bool:
    """Updates GitHub Action @vX.Y.Z pins in README.md and README.en.md."""
    pattern = r'(uses:\s*TeeVee98/Synapse-Hub@v)[0-9]+\.[0-9]+\.[0-9]+'
    replacement = rf"\g<1>{new_ver}"
    updated_vi = update_file("README.md", pattern, replacement, dry_run)
    updated_en = update_file("README.en.md", pattern, replacement, dry_run)
    return updated_vi or updated_en


def run_tests(tier: str = "full") -> bool:
    """Executes the DoD Quality Gates before and after release.

    Note: verify_all.py executes the regression test suite under Gate 7,
    scoped according to tier ('full' or 'impact').
    """
    print(f"\n🔍 Running DoD Quality Gates verification (Tier: {tier.upper()})...")
    verify_script = os.path.join(REPO_ROOT, "tools", "core", "verify_all.py")
    cmd = [sys.executable, verify_script, "--mode", "hub"]
    if tier != "full":
        cmd.extend(["--tier", tier])
    try:
        res_verify = subprocess.run(cmd, cwd=REPO_ROOT, timeout=360.0)
        if res_verify.returncode != 0:
            print(f"❌ Quality Gates ({tier}) failed! Aborting release.")
            return False
        print(f"✅ DoD Quality Gates ({tier}) PASSED.")
    except subprocess.TimeoutExpired:
        print(f"❌ Quality Gates ({tier}) timed out after 360s! Aborting release.")
        return False
    return True

def git_commit_and_tag(version: str, push: bool = False):
    """Creates a conventional Git release commit and tags the repository.

    Args:
        version: Target version string.
        push: If True, pushes the commit and tag to git remote origin.
    """
    tag_name = f"v{version}"

    # Pre-check: warn about untracked files
    try:
        status_res = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=15.0)
        untracked = [line for line in status_res.stdout.splitlines() if line.startswith("??")]
        if untracked:
            print(f"⚠️ Warning: Detected {len(untracked)} untracked file(s). Note that 'git add -u' only stages modified tracked files.")
    except Exception as err:
        print(f"Notice: Could not check untracked files ({err}).")

    print(f"\n📦 Creating Git commit and tag {tag_name}...")
    subprocess.run(["git", "add", "-u"], cwd=REPO_ROOT, check=True, timeout=30.0)
    subprocess.run(["git", "commit", "-m", f"chore(release): bump version to {tag_name}"], cwd=REPO_ROOT, check=True, timeout=30.0)

    # Check if tag already exists before creating
    tag_check = subprocess.run(["git", "tag", "-l", tag_name], cwd=REPO_ROOT, capture_output=True, text=True, timeout=15.0)
    if tag_check.stdout.strip():
        print(f"⚠️ Tag {tag_name} already exists locally. Reusing existing tag.")
    else:
        subprocess.run(["git", "tag", tag_name], cwd=REPO_ROOT, check=True, timeout=30.0)
        print(f"✅ Git commit and tag {tag_name} created.")

    if push:
        print("🚀 Pushing commit and tags to remote origin...")
        res = subprocess.run(["git", "branch", "--show-current"], cwd=REPO_ROOT, stdout=subprocess.PIPE, text=True, timeout=30.0)
        cur_branch = res.stdout.strip()
        if cur_branch == "develop":
            try:
                subprocess.run(["git", "checkout", "main"], cwd=REPO_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30.0)
                subprocess.run(["git", "merge", "develop", "--ff-only"], cwd=REPO_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30.0)
                subprocess.run(["git", "checkout", "develop"], cwd=REPO_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30.0)
                subprocess.run(["git", "push", "origin", "develop", "main", "--tags"], cwd=REPO_ROOT, check=True, timeout=60.0)
            except Exception:
                subprocess.run(["git", "push", "origin", "HEAD", "--tags"], cwd=REPO_ROOT, check=True, timeout=60.0)
        else:
            subprocess.run(["git", "push", "origin", "HEAD", "--tags"], cwd=REPO_ROOT, check=True, timeout=60.0)
        print("✅ Remote origin synchronized.")

def main():
    """CLI entrypoint for bumping Synapse Hub version synchronously across manifests."""
    parser = argparse.ArgumentParser(description="Atomic Universal Version Bumper for Synapse Hub")
    parser.add_argument("action", nargs="?", default="patch", help="patch | minor | major | <explicit_version> (default: patch)")
    parser.add_argument("--dry-run", action="store_true", help="Preview version changes without writing files")
    parser.add_argument("--no-test", action="store_true", help="Skip running test suite after bumping")
    parser.add_argument("--commit", action="store_true", help="Auto-commit changes with conventional message")
    parser.add_argument("--tag", action="store_true", help="Create Git tag v<version>")
    parser.add_argument("--push", action="store_true", help="Push commit and tags to Git remote")

    args = parser.parse_args()

    current_ver = get_current_version()
    new_ver = calculate_next_version(current_ver, args.action)

    print("======================================================================")
    print("       SYNAPSE HUB — ATOMIC UNIVERSAL VERSION BUMPER                  ")
    print("======================================================================")
    print(f"  Current Version : {current_ver}")
    print(f"  Target Version  : {new_ver} ({args.action})")
    print(f"  Mode            : {'DRY RUN (Preview)' if args.dry_run else 'APPLY CHANGES'}")
    print("======================================================================")

    # Pre-flight baseline verification (ensure starting state is clean and passing)
    if not args.no_test and not args.dry_run:
        print("\n🔍 Running pre-flight baseline verification...")
        if not run_tests():
            print("❌ Baseline test suite or Quality Gates failed! Zero files modified on disk.")
            sys.exit(1)

    # 1. package.json
    update_json_root_version("package.json", new_ver, args.dry_run)

    # 1b. plugin.json
    update_json_root_version("plugin.json", new_ver, args.dry_run)

    # 1c. editors/vscode/package.json
    update_json_root_version("editors/vscode/package.json", new_ver, args.dry_run)

    # 1d. .claude-plugin/plugin.json
    update_json_root_version(".claude-plugin/plugin.json", new_ver, args.dry_run)

    # 1e. .claude-plugin/marketplace.json
    cl_mkt = os.path.join(REPO_ROOT, ".claude-plugin", "marketplace.json")
    if os.path.exists(cl_mkt):
        try:
            with open(cl_mkt, "r", encoding="utf-8") as f:
                raw_mkt = f.read()
            mkt_data = json.loads(raw_mkt)
            updated_mkt = False
            for p in mkt_data.get("plugins", []):
                if p.get("version") != new_ver:
                    p["version"] = new_ver
                    updated_mkt = True
            if updated_mkt:
                if not args.dry_run and cl_mkt not in ORIGINAL_SNAPSHOTS:
                    ORIGINAL_SNAPSHOTS[cl_mkt] = raw_mkt
                if not args.dry_run:
                    with open(cl_mkt, "w", encoding="utf-8", newline="\n") as f:
                        json.dump(mkt_data, f, indent=2, ensure_ascii=False)
                        f.write("\n")
                    print(f"  [UPDATED] .claude-plugin/marketplace.json ({new_ver})")
                else:
                    print(f"  [DRY-RUN] Would update .claude-plugin/marketplace.json ({new_ver})")
        except Exception as e:
            print(f"  [WARN] .claude-plugin/marketplace.json update notice: {e}")

    # 2. pyproject.toml
    update_file("pyproject.toml", r'(?m)^(\s*version\s*=\s*")[^"]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 3. skills_manifest.json
    update_json_root_version("skills_manifest.json", new_ver, args.dry_run)

    # 3b. synapse.config.json
    update_json_root_version("synapse.config.json", new_ver, args.dry_run)

    # 3c. agentskills.json
    update_json_root_version("agentskills.json", new_ver, args.dry_run)

    # 3d. agents_manifest.json
    update_json_root_version("agents_manifest.json", new_ver, args.dry_run)

    # 3e. .release-please-manifest.json
    full_rpm = os.path.join(REPO_ROOT, ".release-please-manifest.json")
    if os.path.exists(full_rpm):
        if not args.dry_run:
            with open(full_rpm, "w", encoding="utf-8") as f:
                json.dump({".": new_ver}, f, indent=2)
                f.write("\n")
            print(f"  [UPDATED] .release-please-manifest.json ({new_ver})")
        else:
            print(f"  [DRY-RUN] Would update .release-please-manifest.json ({new_ver})")

    # 3f. synapse/__init__.py
    update_file("synapse/__init__.py", r'(__version__\s*=\s*")[^"]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 3g. benchmarks/context_benchmark.json
    ctx_bm = os.path.join(REPO_ROOT, "benchmarks", "context_benchmark.json")
    if os.path.exists(ctx_bm):
        try:
            with open(ctx_bm, "r", encoding="utf-8") as f:
                raw_bm = f.read()
            bm_data = json.loads(raw_bm)
            bm_data["version"] = new_ver
            if "synthetic_track" in bm_data and isinstance(bm_data["synthetic_track"], dict):
                bm_data["synthetic_track"]["version"] = new_ver
            if "empirical_track" in bm_data and isinstance(bm_data["empirical_track"], dict):
                bm_data["empirical_track"]["version"] = new_ver
            if not args.dry_run and ctx_bm not in ORIGINAL_SNAPSHOTS:
                ORIGINAL_SNAPSHOTS[ctx_bm] = raw_bm
            if not args.dry_run:
                with open(ctx_bm, "w", encoding="utf-8", newline="\n") as f:
                    json.dump(bm_data, f, indent=2, ensure_ascii=False)
                    f.write("\n")
                print(f"  [UPDATED] benchmarks/context_benchmark.json ({new_ver})")
            else:
                print(f"  [DRY-RUN] Would update benchmarks/context_benchmark.json ({new_ver})")
        except Exception as e:
            print(f"  [WARN] benchmarks/context_benchmark.json update notice: {e}")

    # 3h. benchmarks/qa_eval/eval_runner.py
    update_file("benchmarks/qa_eval/eval_runner.py", r'("benchmark_metadata":\s*\{[^}]*"version":\s*")[^"]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 4. tools/core/cli.py
    update_file("tools/core/cli.py", r'(version\s*=\s*")[^"]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 5. tools/mcp/mcp_server.py
    update_file("tools/mcp/mcp_server.py", r'(SERVER_VERSION\s*=\s*")[^"]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 6. tools/browser_helpers.js
    update_file("tools/browser_helpers.js", r"(__version === ')[^']+(')", rf"\g<1>{new_ver}\g<2>", args.dry_run)
    update_file("tools/browser_helpers.js", r"(__version:\s*')[^']+(')", rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 7. tools/mcp/mcp_excel_server.py & tools/mcp/mcp_docx_server.py
    update_file("tools/mcp/mcp_excel_server.py", r'(SERVER_VERSION\s*=\s*")[^"]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)
    update_file("tools/mcp/mcp_excel_server.py", r'("serverInfo":\s*\{[^}]*"version":\s*")[^"]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)
    update_file("tools/mcp/mcp_docx_server.py", r'(SERVER_VERSION\s*=\s*")[^"]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)
    update_file("tools/mcp/mcp_docx_server.py", r'("serverInfo":\s*\{[^}]*"version":\s*")[^"]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 7b. tools/report/sarif_exporter.py
    update_file("tools/report/sarif_exporter.py", r'(TOOL_VERSION\s*=\s*")[^"]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 7c. tools/security/asvs_auditor.py (User-Agent version)
    update_file("tools/security/asvs_auditor.py", r'(Synapse-Hub-ASVS-Auditor/)[0-9]+\.[0-9]+\.[0-9]+', rf"\g<1>{new_ver}", args.dry_run)

    # 7d. tools/contrib/vpat_exporter.py (User-Agent version)
    update_file("tools/contrib/vpat_exporter.py", r'(Synapse-Hub-VPAT/)[0-9]+\.[0-9]+\.[0-9]+', rf"\g<1>{new_ver}", args.dry_run)

    # 8. docs/ARCHITECTURE.md & docs/ARCHITECTURE.en.md
    update_file("docs/ARCHITECTURE.md", r'(>\s*\*\*Version:\*\*\s*`)[^`]+(`)', rf"\g<1>{new_ver}\g<2>", args.dry_run)
    update_file("docs/ARCHITECTURE.en.md", r'(>\s*\*\*Version:\*\*\s*`)[^`]+(`)', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 8b. editors/vscode/README.md and root READMEs vsix links (guarded by artifact existence)
    update_vsix_links(new_ver, dry_run=args.dry_run)

    # 9. README.md & README.en.md (Documentation headings, action pins, and badges)
    update_readme_action_pins(new_ver, dry_run=args.dry_run)
    update_file("README.md", r'(Phiên bản(?: Hub)?:\*\*\s*`v)[^`]+(`)', rf"\g<1>{new_ver}\g<2>", args.dry_run)
    update_file("README.md", r'((?:Hub )?Version:\*\*\s*`v)[^`]+(`)', rf"\g<1>{new_ver}\g<2>", args.dry_run)
    update_file("README.md", r'(Intelligence Core v)[^")\]]+', rf"\g<1>{new_ver}", args.dry_run)
    update_file("README.md", r'(rev:\s*v)[0-9]+\.[0-9]+\.[0-9]+', rf"\g<1>{new_ver}", args.dry_run)
    update_file("README.md", r'(Synapse Hub \(Core v)[0-9]+\.[0-9]+\.[0-9]+(\))', rf"\g<1>{new_ver}\g<2>", args.dry_run)
    update_file("README.en.md", r'((?:Hub )?Version:\*\*\s*`v)[^`]+(`)', rf"\g<1>{new_ver}\g<2>", args.dry_run)
    update_file("README.en.md", r'(Intelligence Core v)[^")\]]+', rf"\g<1>{new_ver}", args.dry_run)
    update_file("README.en.md", r'(rev:\s*v)[0-9]+\.[0-9]+\.[0-9]+', rf"\g<1>{new_ver}", args.dry_run)
    update_file("README.en.md", r'(Synapse Hub \(Core v)[0-9]+\.[0-9]+\.[0-9]+(\))', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 9b. SECURITY.md
    major, minor, _, _ = parse_semver(new_ver)
    current_branch = f"{major}.{minor}.x"
    update_file("SECURITY.md", r'(\|\s*`)[0-9]+\.[0-9]+\.x(`\s*\|\s*✅)', rf"\g<1>{current_branch}\g<2>", args.dry_run)

    # 10. tools/__init__.py
    update_file("tools/__init__.py", r'(__version__\s*=\s*")[^"]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 10b. tools/contrib/ui_server.py
    update_file("tools/contrib/ui_server.py", r'("version":\s*")[0-9]+\.[0-9]+\.[0-9]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 11. tools/contrib/welcome_page.py
    update_file("tools/contrib/welcome_page.py", r'("version":\s*")[^"]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 12. tools/contrib/dashboard_generator.py
    update_file("tools/contrib/dashboard_generator.py", r'(Synapse-Hub v)[0-9]+\.[0-9]+\.[0-9]+', rf"\g<1>{new_ver}", args.dry_run)

    # 13. tools/lint/update_sentinel.py
    update_file("tools/lint/update_sentinel.py", r'(\.get\("version",\s*")[^"]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)
    update_file("tools/lint/update_sentinel.py", r'(return\s*")[0-9]+\.[0-9]+\.[0-9]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 13b. tests/test_synapse_package.py
    update_file("tests/test_synapse_package.py", r'(matches version )[0-9]+\.[0-9]+\.[0-9]+', rf"\g<1>{new_ver}", args.dry_run)

    # 13c. tests/test_release_engineering_and_packaging.py
    update_file("tests/test_release_engineering_and_packaging.py", r'(\.get\("version",\s*")[0-9]+\.[0-9]+\.[0-9]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 14. CHANGELOG.md
    cl_path = os.path.join(REPO_ROOT, "CHANGELOG.md")
    if os.path.exists(cl_path) and not args.dry_run:
        try:
            with open(cl_path, "r", encoding="utf-8") as f:
                cl_text = f.read()
            if cl_path not in ORIGINAL_SNAPSHOTS:
                ORIGINAL_SNAPSHOTS[cl_path] = cl_text
            if f"## [{new_ver}]" not in cl_text:
                from datetime import date
                today_str = date.today().isoformat()
                new_block = f"---\n\n## [{new_ver}] - {today_str}\n\n### Changed\n- Maintenance & version release v{new_ver}.\n\n"
                cl_text = re.sub(r'(?m)^---\s*\n\s*##\s*\[', new_block + "## [", cl_text, count=1)
                with open(cl_path, "w", encoding="utf-8") as f:
                    f.write(cl_text)
                print(f"  [UPDATED] CHANGELOG.md (v{new_ver} entry added)")
        except Exception as e:
            print(f"  [WARN] CHANGELOG.md update notice: {e}")

    if args.dry_run:
        print("\n[INFO] Dry-run completed. No files modified on disk.")
        return

    # Post-bump tests verification (validate that bumped files pass all gates and version sync)
    if not args.no_test:
        sync_script = os.path.join(REPO_ROOT, "tools", "core", "check_version_sync.py")
        if os.path.exists(sync_script):
            res_sync = subprocess.run([sys.executable, sync_script], cwd=REPO_ROOT)
            if res_sync.returncode != 0:
                print("❌ Version Synchronization failed! Rolling back all version changes...")
                rollback_all_files()
                sys.exit(1)

        if not run_tests(tier="impact"):
            print("❌ Post-bump verification failed! Rolling back all version changes...")
            rollback_all_files()
            sys.exit(1)

    # Git operations
    if args.commit or args.push:
        try:
            git_commit_and_tag(new_ver, push=args.push)
        except Exception as e:
            print(f"❌ Git commit or tag operation failed: {e}")
            rollback_all_files()
            sys.exit(1)

    print("\n======================================================================")
    print(f"🎉 VERSION BUMP COMPLETE: v{current_ver} ➔ v{new_ver}")
    print("======================================================================")
    print("Next steps:")
    print("  • Publish to NPM : npm publish")
    print("  • Or Git Push    : git push origin HEAD --tags")
    print("======================================================================")

if __name__ == "__main__":
    main()
