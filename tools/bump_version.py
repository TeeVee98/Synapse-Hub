#!/usr/bin/env python3
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

import sys
import os
import re
import json
import argparse
import subprocess

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
        data = json.load(f)

    old_ver = data.get("version")
    if old_ver == new_ver:
        print(f"  [SKIP] {rel_path} already at v{new_ver}")
        return False

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
    if count == 0:
        print(f"  [SKIP] No pattern match in {rel_path}")
        return False

    if not dry_run:
        with open(full_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_content)
        print(f"  [UPDATED] {rel_path} ({count} occurrence{'s' if count > 1 else ''})")
    else:
        print(f"  [DRY-RUN] Would update {rel_path} ({count} occurrence{'s' if count > 1 else ''})")
    return True

def run_tests() -> bool:
    """Executes the test suite and 10 DoD Quality Gates before release.

    Returns:
        True if all tests and gates pass.
    """
    print("\n🔍 Running verification suite...")
    cmd = [sys.executable, "-m", "unittest", "discover", "tests", "-p", "test_*.py"]
    try:
        res = subprocess.run(cmd, cwd=REPO_ROOT, timeout=120.0)
        if res.returncode != 0:
            print("❌ Unit tests failed! Aborting release.")
            return False
        print("✅ All unit tests PASSED.")
    except subprocess.TimeoutExpired:
        print("❌ Unit tests timed out after 120s! Aborting release.")
        return False

    verify_script = os.path.join(REPO_ROOT, "tools", "verify_all.py")
    try:
        res_verify = subprocess.run([sys.executable, verify_script], cwd=REPO_ROOT, timeout=120.0)
        if res_verify.returncode != 0:
            print("❌ Quality Gates failed! Aborting release.")
            return False
        print("✅ 10 Quality Gates DoD PASSED.")
    except subprocess.TimeoutExpired:
        print("❌ Quality Gates timed out after 120s! Aborting release.")
        return False
    return True

def git_commit_and_tag(version: str, push: bool = False):
    """Creates a conventional Git release commit and tags the repository.

    Args:
        version: Target version string.
        push: If True, pushes the commit and tag to git remote origin.
    """
    print(f"\n📦 Creating Git commit and tag v{version}...")
    subprocess.run(["git", "add", "-u"], cwd=REPO_ROOT, check=True, timeout=30.0)
    subprocess.run(["git", "commit", "-m", f"chore(release): bump version to v{version}"], cwd=REPO_ROOT, check=True, timeout=30.0)
    subprocess.run(["git", "tag", f"v{version}"], cwd=REPO_ROOT, check=True, timeout=30.0)
    print(f"✅ Git commit and tag v{version} created.")

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

    # 1. package.json
    update_json_root_version("package.json", new_ver, args.dry_run)

    # 1b. plugin.json
    update_json_root_version("plugin.json", new_ver, args.dry_run)

    # 1c. editors/vscode/package.json
    update_json_root_version("editors/vscode/package.json", new_ver, args.dry_run)

    # 2. pyproject.toml
    update_file("pyproject.toml", r'(?m)^(\s*version\s*=\s*")[^"]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 3. skills_manifest.json
    update_json_root_version("skills_manifest.json", new_ver, args.dry_run)

    # 3b. synapse.config.json
    update_json_root_version("synapse.config.json", new_ver, args.dry_run)

    # 3c. agentskills.json
    update_json_root_version("agentskills.json", new_ver, args.dry_run)

    # 4. tools/cli.py
    update_file("tools/cli.py", r'(version\s*=\s*")[^"]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 5. tools/mcp_server.py
    update_file("tools/mcp_server.py", r'(SERVER_VERSION\s*=\s*")[^"]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 6. tools/browser_helpers.js
    update_file("tools/browser_helpers.js", r"(__version === ')[^']+(')", rf"\g<1>{new_ver}\g<2>", args.dry_run)
    update_file("tools/browser_helpers.js", r"(__version:\s*')[^']+(')", rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 7. tools/mcp_excel_server.py
    update_file("tools/mcp_excel_server.py", r'(SERVER_VERSION\s*=\s*")[^"]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)
    update_file("tools/mcp_excel_server.py", r'("serverInfo":\s*\{[^}]*"version":\s*")[^"]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 8. docs/ARCHITECTURE.md & docs/ARCHITECTURE.en.md
    update_file("docs/ARCHITECTURE.md", r'(>\s*\*\*Version:\*\*\s*`)[^`]+(`)', rf"\g<1>{new_ver}\g<2>", args.dry_run)
    update_file("docs/ARCHITECTURE.en.md", r'(>\s*\*\*Version:\*\*\s*`)[^`]+(`)', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 9. README.md & README.en.md (Documentation headings and badges)
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

    # 10b. tools/ui_server.py
    update_file("tools/ui_server.py", r'("version":\s*")[0-9]+\.[0-9]+\.[0-9]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 11. tools/welcome_page.py
    update_file("tools/welcome_page.py", r'("version":\s*")[^"]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 12. tools/dashboard_generator.py
    update_file("tools/dashboard_generator.py", r'(Synapse-Hub v)[0-9]+\.[0-9]+\.[0-9]+', rf"\g<1>{new_ver}", args.dry_run)

    # 13. tools/update_sentinel.py
    update_file("tools/update_sentinel.py", r'(\.get\("version",\s*")[^"]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)
    update_file("tools/update_sentinel.py", r'(return\s*")[0-9]+\.[0-9]+\.[0-9]+(")', rf"\g<1>{new_ver}\g<2>", args.dry_run)

    # 14. CHANGELOG.md
    cl_path = os.path.join(REPO_ROOT, "CHANGELOG.md")
    if os.path.exists(cl_path) and not args.dry_run:
        try:
            with open(cl_path, "r", encoding="utf-8") as f:
                cl_text = f.read()
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

    # Tests verification
    if not args.no_test:
        if not run_tests():
            sys.exit(1)

    # Git operations
    if args.commit or args.push:
        git_commit_and_tag(new_ver, push=args.push)

    print("\n======================================================================")
    print(f"🎉 VERSION BUMP COMPLETE: v{current_ver} ➔ v{new_ver}")
    print("======================================================================")
    print("Next steps:")
    print("  • Publish to NPM : npm publish")
    print("  • Or Git Push    : git push origin HEAD --tags")
    print("======================================================================")

if __name__ == "__main__":
    main()
