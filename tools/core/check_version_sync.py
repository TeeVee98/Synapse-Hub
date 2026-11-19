#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

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
  6. agentskills.json (Agent Skills specification)
  7. tools/mcp_server.py (MCP server protocol version)
  8. tools/cli.py (Agent-QA CLI hub version)
  9. tools/__init__.py (Python package version)
  10. tools/ui_server.py (Web UI dashboard version)

Usage:
  python3 tools/check_version_sync.py
  python3 tools/check_version_sync.py --expected-version 2.3.0
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


import os
import sys
import re
import json
import argparse
from typing import Dict, List, Optional, Tuple

def _find_repo_root() -> str:
    curr = os.path.dirname(os.path.abspath(__file__))
    while curr and curr != os.path.dirname(curr):
        if os.path.isfile(os.path.join(curr, "package.json")) or os.path.isfile(os.path.join(curr, "pyproject.toml")):
            return curr
        curr = os.path.dirname(curr)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


REPO_ROOT = _find_repo_root()


def extract_versions(repo_root: str) -> Dict[str, str]:
    """Extracts declared versions across all source and manifest targets."""
    versions: Dict[str, str] = {}

    # 1. package.json
    pkg_path = os.path.join(repo_root, "package.json")
    if os.path.exists(pkg_path):
        with open(pkg_path, "r", encoding="utf-8") as f:
            versions["package.json"] = json.load(f).get("version", "")

    # 1b. editors/vscode/package.json
    for candidate in (
        os.path.join(repo_root, "integrations", "editors", "editors", "vscode", "package.json"),
        os.path.join(repo_root, "integrations", "editors", "package.json"),
        os.path.join(repo_root, "editors", "vscode", "package.json"),
    ):
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                versions["editors/vscode/package.json"] = json.load(f).get("version", "")
            break

    # 2. pyproject.toml
    pyproject_path = os.path.join(repo_root, "pyproject.toml")
    if os.path.exists(pyproject_path):
        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()
            m = re.search(r'(?m)^version\s*=\s*["\']([^"\']+)["\']', content)
            if m:
                versions["pyproject.toml"] = m.group(1)

    # 3. plugin.json
    for candidate in (
        os.path.join(repo_root, "tools", "schemas", "plugin.json"),
        os.path.join(repo_root, "plugin.json"),
    ):
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                versions["plugin.json"] = json.load(f).get("version", "")
            break

    # 3b. .claude-plugin/plugin.json
    cp_plugin = os.path.join(repo_root, ".claude-plugin", "plugin.json")
    if os.path.exists(cp_plugin):
        with open(cp_plugin, "r", encoding="utf-8") as f:
            versions[".claude-plugin/plugin.json"] = json.load(f).get("version", "")

    # 3c. .claude-plugin/marketplace.json
    cp_mkt = os.path.join(repo_root, ".claude-plugin", "marketplace.json")
    if os.path.exists(cp_mkt):
        with open(cp_mkt, "r", encoding="utf-8") as f:
            mkt_data = json.load(f)
            for p in mkt_data.get("plugins", []):
                if p.get("name") == "synapse-hub":
                    versions[".claude-plugin/marketplace.json"] = p.get("version", "")
                    break

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

    # 5b. agentskills.json
    for candidate in (
        os.path.join(repo_root, "tools", "schemas", "agentskills.json"),
        os.path.join(repo_root, "agentskills.json"),
    ):
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                versions["agentskills.json"] = json.load(f).get("version", "")
            break

    # 5c. agents_manifest.json
    agents_manifest = os.path.join(repo_root, "agents_manifest.json")
    if os.path.exists(agents_manifest):
        with open(agents_manifest, "r", encoding="utf-8") as f:
            versions["agents_manifest.json"] = json.load(f).get("version", "")

    # 6. tools/mcp_server.py
    for candidate in (
        os.path.join(repo_root, "tools", "cli", "tools", "mcp_server.py"),
        os.path.join(repo_root, "tools", "mcp_server.py"),
    ):
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                content = f.read()
                m = re.search(r'SERVER_VERSION\s*=\s*["\']([^"\']+)["\']', content)
                if m:
                    versions["tools/mcp_server.py"] = m.group(1)
            break

    # 7. tools/cli.py
    for candidate in (
        os.path.join(repo_root, "tools", "cli", "tools", "cli.py"),
        os.path.join(repo_root, "tools", "cli.py"),
    ):
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                content = f.read()
                m = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                if m:
                    versions["tools/cli.py"] = m.group(1)
            break

    # 8. tools/__init__.py
    for candidate in (
        os.path.join(repo_root, "tools", "cli", "tools", "__init__.py"),
        os.path.join(repo_root, "tools", "__init__.py"),
    ):
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                content = f.read()
                m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
                if m:
                    versions["tools/__init__.py"] = m.group(1)
            break

    # 8b. synapse/__init__.py
    synapse_init = os.path.join(repo_root, "synapse", "__init__.py")
    if os.path.exists(synapse_init):
        with open(synapse_init, "r", encoding="utf-8") as f:
            content = f.read()
            m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
            if m:
                versions["synapse/__init__.py"] = m.group(1)

    # 9. tools/mcp_excel_server.py & tools/mcp_docx_server.py
    for candidate in (
        os.path.join(repo_root, "tools", "cli", "tools", "mcp_excel_server.py"),
        os.path.join(repo_root, "tools", "mcp_excel_server.py"),
    ):
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                content = f.read()
                m = re.search(r'SERVER_VERSION\s*=\s*["\']([^"\']+)["\']', content)
                if m:
                    versions["tools/mcp_excel_server.py"] = m.group(1)
            break

    for candidate in (
        os.path.join(repo_root, "tools", "cli", "tools", "mcp_docx_server.py"),
        os.path.join(repo_root, "tools", "mcp_docx_server.py"),
    ):
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                content = f.read()
                m = re.search(r'SERVER_VERSION\s*=\s*["\']([^"\']+)["\']', content)
                if m:
                    versions["tools/mcp_docx_server.py"] = m.group(1)
            break

    # 9c. tools/report/sarif_exporter.py
    for candidate in (
        os.path.join(repo_root, "tools", "report", "sarif_exporter.py"),
        os.path.join(repo_root, "tools", "sarif_exporter.py"),
    ):
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                content = f.read()
                m = re.search(r'TOOL_VERSION\s*=\s*["\']([^"\']+)["\']', content)
                if m:
                    versions["tools/report/sarif_exporter.py"] = m.group(1)
            break

    # 10. docs/ARCHITECTURE.md & docs/ARCHITECTURE.en.md
    for candidate in (
        os.path.join(repo_root, "docs", "guides", "ARCHITECTURE.md"),
        os.path.join(repo_root, "docs", "ARCHITECTURE.md"),
    ):
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                content = f.read()
                m = re.search(r'>\s*\*\*Version:\*\*\s*`([^`]+)`', content)
                if m:
                    versions["docs/ARCHITECTURE.md"] = m.group(1)
            break

    for candidate in (
        os.path.join(repo_root, "docs", "guides", "ARCHITECTURE.en.md"),
        os.path.join(repo_root, "docs", "ARCHITECTURE.en.md"),
    ):
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                content = f.read()
                m = re.search(r'>\s*\*\*Version:\*\*\s*`([^`]+)`', content)
                if m:
                    versions["docs/ARCHITECTURE.en.md"] = m.group(1)
            break

    # 11. README.md
    readme_path = os.path.join(repo_root, "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
            m_badge = re.search(r'Phiên bản(?: Hub)?:\*\*\s*`v([0-9]+\.[0-9]+\.[0-9]+)', content)
            m_rev = re.search(r'rev:\s*v([0-9]+\.[0-9]+\.[0-9]+)', content)
            if m_badge:
                versions["README.md"] = m_badge.group(1)
            elif m_rev:
                versions["README.md"] = m_rev.group(1)
            if m_badge and m_rev:
                versions["README.md (rev)"] = m_rev.group(1)

    # 12. README.en.md
    readme_en_path = os.path.join(repo_root, "README.en.md")
    if os.path.exists(readme_en_path):
        with open(readme_en_path, "r", encoding="utf-8") as f:
            content = f.read()
            m_badge = re.search(r'(?:Hub )?Version:\*\*\s*`v([0-9]+\.[0-9]+\.[0-9]+)', content)
            m_rev = re.search(r'rev:\s*v([0-9]+\.[0-9]+\.[0-9]+)', content)
            if m_badge:
                versions["README.en.md"] = m_badge.group(1)
            elif m_rev:
                versions["README.en.md"] = m_rev.group(1)
            if m_badge and m_rev:
                versions["README.en.md (rev)"] = m_rev.group(1)

    # 13. SECURITY.md
    sec_path = os.path.join(repo_root, "SECURITY.md")
    if os.path.exists(sec_path):
        with open(sec_path, "r", encoding="utf-8") as f:
            content = f.read()
            m = re.search(r'\|\s*`([0-9]+\.[0-9]+\.x)`\s*\|\s*✅', content)
            if m:
                versions["SECURITY.md"] = m.group(1)

    # 14. tools/ui_server.py
    ui_path = os.path.join(repo_root, "tools", "ui_server.py")
    if os.path.exists(ui_path):
        with open(ui_path, "r", encoding="utf-8") as f:
            content = f.read()
            m = re.search(r'"version":\s*["\']([^"\']+)["\']', content)
            if m:
                versions["tools/ui_server.py"] = m.group(1)

    return versions


from skill_canonical_digest import (
    validate_lockfile_integrity,
    update_skills_lockfile,
)


def check_docs_as_code(repo_root: str) -> Tuple[bool, List[str]]:
    """Verifies Docs-as-Code consistency: skill count (57) and tool catalog count (166)."""
    violations = []

    # 1. Skills count in skills_manifest.json and skills_index.json
    for cand in ("skills_manifest.json", "skills_index.json"):
        p = os.path.join(repo_root, cand)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    cnt = len(json.load(f).get("skills", []))
                    if cnt != 57:
                        violations.append(f"{cand} declared {cnt} skills (expected 57)")
            except Exception as e:
                violations.append(f"Error reading {cand}: {e}")

    # 2. Tools count in tools/TOOL_CATALOG.json
    catalog_path = os.path.join(repo_root, "tools", "TOOL_CATALOG.json")
    if os.path.exists(catalog_path):
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                tools_list = data.get("tools", data) if isinstance(data, dict) else data
                cnt = len(tools_list)
                if cnt != 166:
                    violations.append(f"tools/TOOL_CATALOG.json declared {cnt} tools (expected 166)")
        except Exception as e:
            violations.append(f"Error reading TOOL_CATALOG.json: {e}")

    # 3. README scale declarations
    for rname in ("README.md", "README.en.md"):
        rpath = os.path.join(repo_root, rname)
        if os.path.exists(rpath):
            try:
                with open(rpath, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "57" not in content or "166" not in content:
                        violations.append(f"{rname} scale declaration does not match 57 skills and 166 tools")
            except Exception as e:
                violations.append(f"Error reading {rname}: {e}")

    return len(violations) == 0, violations


def check_sync(repo_root: str, expected_version: Optional[str] = None) -> Tuple[bool, Dict[str, str], str]:
    """
    Checks if all version definitions match across manifests and verifies canonical skill lockfile integrity.
    Returns (is_synced, versions_dict, canonical_version_or_error_msg).
    """
    versions = extract_versions(repo_root)
    if not versions:
        return False, {}, "No version files found in repository."

    target_ver = expected_version or versions.get("package.json")
    if not target_ver:
        target_ver = next(iter(versions.values()))

    target_prefix = ".".join(target_ver.split(".")[:2]) + ".x"
    mismatches = {}
    for path, ver in versions.items():
        if path == "SECURITY.md":
            if ver != target_prefix:
                mismatches[path] = ver
        elif ver != target_ver:
            mismatches[path] = ver

    if mismatches:
        return False, versions, target_ver

    # Enforce canonical skills lockfile integrity (live content hash validation)
    lock_ok, lock_msg = validate_lockfile_integrity(repo_root, enforce_content_hash=True)
    if not lock_ok:
        return False, versions, f"Lockfile integrity verification failed: {lock_msg}"

    # Enforce Docs-as-Code inventory parity (57 skills, 166 tools)
    docs_ok, docs_viols = check_docs_as_code(repo_root)
    if not docs_ok:
        return False, versions, f"Docs-as-code parity failed: {'; '.join(docs_viols)}"

    return True, versions, target_ver


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify universal version sync across Synapse Hub files")
    parser.add_argument("--expected-version", "-e", help="Expected version string (e.g. from git tag)", default=None)
    parser.add_argument("--repo-root", default=REPO_ROOT, help="Root directory of the repository")
    parser.add_argument("--update-hashes", action="store_true", help="Recalculate and update canonical skill folder hashes in lockfiles")
    args = parser.parse_args()

    if args.update_hashes:
        ok, msg = update_skills_lockfile(args.repo_root)
        print(f"[{'SUCCESS' if ok else 'FAIL'}] {msg}")
        return 0 if ok else 1

    expected = args.expected_version
    if expected and expected.startswith("v"):
        expected = expected[1:]

    is_synced, versions, canonical = check_sync(args.repo_root, expected)

    print("======================================================================")
    print("      SYNAPSE HUB - UNIVERSAL VERSION SYNCHRONIZATION AUDIT          ")
    print("======================================================================")
    print(f"Target Version: v{canonical}")
    print("----------------------------------------------------------------------")

    target_prefix = ".".join(canonical.split(".")[:2]) + ".x"
    all_matched = True
    for file_path, ver in sorted(versions.items()):
        is_match = (ver == target_prefix) if file_path == "SECURITY.md" else (ver == canonical)
        status = "[MATCH]" if is_match else "[MISMATCH]"
        if not is_match:
            all_matched = False
        print(f"  {status:<11} {file_path:<26} -> {ver}")

    lock_ok, lock_msg = validate_lockfile_integrity(args.repo_root)
    lock_status = "[MATCH]" if lock_ok else "[MISMATCH]"
    print(f"  {lock_status:<11} {'skills-lock.json (SHA-256)':<26} -> {lock_msg}")
    if not lock_ok:
        all_matched = False

    docs_ok, docs_viols = check_docs_as_code(args.repo_root)
    docs_status = "[MATCH]" if docs_ok else "[MISMATCH]"
    docs_msg = "57 Skills, 166 Tools inventory verified across manifests & README" if docs_ok else "; ".join(docs_viols)
    print(f"  {docs_status:<11} {'Docs-as-Code Parity':<26} -> {docs_msg}")
    if not docs_ok:
        all_matched = False

    print("======================================================================")
    if is_synced and all_matched:
        print(f"[PASS] 100% Version synchronization verified across all {len(versions)} targets.")
        return 0
    else:
        print(f"[FAIL] Version mismatch detected! All components must match v{canonical}.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
