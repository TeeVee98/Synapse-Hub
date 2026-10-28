#!/usr/bin/env python3
"""
Enterprise Agent-Skills Hub Distribution Packager
================================================
Packages the complete, clean repository into a release-ready zip file (agent-skills.zip).
Ensures 100% inclusion of all mandatory folders:
  - .agents/    (skills, rules, workflows, agents)
  - docs/       (ARCHITECTURE.md, CLI_REFERENCE.md, CONTRIBUTING.md)
  - scripts/    (install.ps1, setup.sh, setup_environment.ps1, lint_skills.ps1)
  - templates/  (PROJECT_AI_GUIDE_TEMPLATE.md)
  - tools/      (all CLI tools and utilities)
  - root configs (README.md, AGENTS.md, pyproject.toml, requirements.txt, skills_manifest.json)

Excludes ephemeral clutter (.git, .venv, __pycache__, reports, temp files).
"""

import os
import sys
import zipfile
from pathlib import Path

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
    "agent_qa.egg-info",
    "archive",
    "reports",
}

EXCLUDE_EXTS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".log",
    ".tmp",
    ".zip",
}

MANDATORY_CHECKS = [
    "docs/ARCHITECTURE.md",
    "docs/CLI_REFERENCE.md",
    "scripts/install.ps1",
    "scripts/setup.sh",
    "templates/PROJECT_AI_GUIDE_TEMPLATE.md",
    "README.md",
    "AGENTS.md",
    "tools/infer_linter.py",
    "tools/verify_all.py",
    "tools/browser_helpers.js",
]


def create_package(output_zip: str = "agent-skills.zip") -> Path:
    out_path = REPO_ROOT / output_zip
    print(f"📦 Packaging Enterprise Agent-Skills Hub into: {out_path.name}")
    print("=" * 60)

    total_files = 0
    total_size = 0

    with zipfile.ZipFile(out_path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for root, dirs, files in os.walk(REPO_ROOT):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".temp-")]

            rel_root = Path(root).relative_to(REPO_ROOT)
            if any(part in EXCLUDE_DIRS for part in rel_root.parts):
                continue

            for file_name in files:
                if any(file_name.endswith(ext) for ext in EXCLUDE_EXTS):
                    continue
                if file_name == output_zip:
                    continue

                full_path = Path(root) / file_name
                rel_path = full_path.relative_to(REPO_ROOT)
                arc_name = rel_path.as_posix()

                zf.write(full_path, arcname=arc_name)
                total_files += 1
                total_size += full_path.stat().st_size

    zip_size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"✅ Packaging complete:")
    print(f"   • Total files packaged : {total_files}")
    print(f"   • Uncompressed size    : {total_size / (1024 * 1024):.2f} MB")
    print(f"   • Archive size (.zip)  : {zip_size_mb:.2f} MB")

    # Verify mandatory files
    print("\n🔍 Verifying mandatory files inside archive:")
    with zipfile.ZipFile(out_path, mode="r") as zf:
        namelist = set(zf.namelist())
        all_ok = True
        for chk in MANDATORY_CHECKS:
            if chk in namelist:
                print(f"   [PASS] {chk}")
            else:
                print(f"   [FAIL] Missing: {chk}")
                all_ok = False

    if not all_ok:
        print("\n❌ Error: Archive is missing critical files!")
        sys.exit(1)

    print(f"\n✨ Archive is 100% intact and ready for distribution: {out_path}")
    return out_path


if __name__ == "__main__":
    create_package()
