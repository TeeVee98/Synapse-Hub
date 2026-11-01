#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/check_version_sync.py — Version Synchronization Sentinel for Synapse Hub

Verifies that the release version is strictly consistent across all manifest,
package, protocol, and CLI definitions in the repository:
  1. package.json (NPM manifest)
  2. pyproject.toml (PEP 621 Python package metadata)
  3. plugin.json (Antigravity plugin manifest)
  4. skills_manifest.json (Skill Catalog index)
  5. synapse.config.json (Hub runtime configuration)
  6. tools/mcp_server.py (MCP server protocol version)
  7. tools/cli.py (Agent-QA CLI hub version)
  8. tools/__init__.py (Python package version)

Usage:
  python3 tools/check_version_sync.py
  python3 tools/check_version_sync.py --expected-version 2.3.0
"""

import os
import sys
import re
import json
import argparse
from typing import Dict, Optional, Tuple

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def extract_versions(repo_root: str) -> Dict[str, str]:
    """Extracts declared versions across all source and manifest targets."""
    versions: Dict[str, str] = {}

    # 1. package.json
    pkg_path = os.path.join(repo_root, "package.json")
    if os.path.exists(pkg_path):
        with open(pkg_path, "r", encoding="utf-8") as f:
            versions["package.json"] = json.load(f).get("version", "")

    # 2. pyproject.toml
    pyproject_path = os.path.join(repo_root, "pyproject.toml")
    if os.path.exists(pyproject_path):
        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()
            m = re.search(r'(?m)^version\s*=\s*["\']([^"\']+)["\']', content)
            if m:
                versions["pyproject.toml"] = m.group(1)

    # 3. plugin.json
    plugin_path = os.path.join(repo_root, "plugin.json")
    if os.path.exists(plugin_path):
        with open(plugin_path, "r", encoding="utf-8") as f:
            versions["plugin.json"] = json.load(f).get("version", "")

    # 4. skills_manifest.json
    manifest_path = os.path.join(repo_root, "skills_manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            versions["skills_manifest.json"] = json.load(f).get("version", "")

    # 5. synapse.config.json
    config_path = os.path.join(repo_root, "synapse.config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            versions["synapse.config.json"] = json.load(f).get("version", "")

    # 6. tools/mcp_server.py
    mcp_path = os.path.join(repo_root, "tools", "mcp_server.py")
    if os.path.exists(mcp_path):
        with open(mcp_path, "r", encoding="utf-8") as f:
            content = f.read()
            m = re.search(r'SERVER_VERSION\s*=\s*["\']([^"\']+)["\']', content)
            if m:
                versions["tools/mcp_server.py"] = m.group(1)

    # 7. tools/cli.py
    cli_path = os.path.join(repo_root, "tools", "cli.py")
    if os.path.exists(cli_path):
        with open(cli_path, "r", encoding="utf-8") as f:
            content = f.read()
            m = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            if m:
                versions["tools/cli.py"] = m.group(1)

    # 8. tools/__init__.py
    init_path = os.path.join(repo_root, "tools", "__init__.py")
    if os.path.exists(init_path):
        with open(init_path, "r", encoding="utf-8") as f:
            content = f.read()
            m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
            if m:
                versions["tools/__init__.py"] = m.group(1)

    return versions


def check_sync(repo_root: str, expected_version: Optional[str] = None) -> Tuple[bool, Dict[str, str], str]:
    """
    Checks if all version definitions match.
    Returns (is_synced, versions_dict, canonical_version_or_error_msg).
    """
    versions = extract_versions(repo_root)
    if not versions:
        return False, {}, "No version files found in repository."

    target_ver = expected_version or versions.get("package.json")
    if not target_ver:
        target_ver = next(iter(versions.values()))

    mismatches = {path: ver for path, ver in versions.items() if ver != target_ver}
    if mismatches:
        return False, versions, target_ver
    return True, versions, target_ver


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify universal version sync across Synapse Hub files")
    parser.add_argument("--expected-version", "-e", help="Expected version string (e.g. from git tag)", default=None)
    parser.add_argument("--repo-root", default=REPO_ROOT, help="Root directory of the repository")
    args = parser.parse_args()

    expected = args.expected_version
    if expected and expected.startswith("v"):
        expected = expected[1:]

    is_synced, versions, canonical = check_sync(args.repo_root, expected)

    print("======================================================================")
    print("      SYNAPSE HUB - UNIVERSAL VERSION SYNCHRONIZATION AUDIT          ")
    print("======================================================================")
    print(f"Target Version: v{canonical}")
    print("----------------------------------------------------------------------")

    all_matched = True
    for file_path, ver in sorted(versions.items()):
        status = "[MATCH]" if ver == canonical else "[MISMATCH]"
        if ver != canonical:
            all_matched = False
        print(f"  {status:<11} {file_path:<26} -> {ver}")

    print("======================================================================")
    if is_synced and all_matched:
        print(f"[PASS] 100% Version synchronization verified across all {len(versions)} targets.")
        return 0
    else:
        print(f"[FAIL] Version mismatch detected! All components must match v{canonical}.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
