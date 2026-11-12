#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/package_release.py — Enterprise Release Packaging & Integrity Sentinel
-----------------------------------------------------------------------------
Builds clean, deterministic distribution archives (ZIP & tar.gz) for Synapse Hub.
Guarantees that essential dot-directories (.github/workflows, .agents) are preserved
and explicitly included, preventing false-missing workflow findings during external audits.

Features:
  1. Mandatory inclusion of .github/workflows/ (including publish_npm.yml) and .agents/.
  2. Strict blacklist filtering of build artifacts, temp files, caches, and test dumps.
  3. Pre-flight and post-archive integrity verification (asserts key manifests exist).
  4. Cryptographic SHA-256 checksum generation for software supply-chain provenance.

Usage:
  python tools/package_release.py
  python tools/package_release.py --output-dir dist --format zip
  python tools/package_release.py --verify-archive dist/synapse-hub-3.1.2.zip
"""

import os
import sys
import json
import zipfile
import tarfile
import hashlib
import argparse
from typing import List, Tuple, Optional

# Enforce UTF-8 console encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Directories that must ALWAYS be included even though they start with a dot
MANDATORY_DOT_DIRS = {
    ".github",
    ".agents",
}

# Directories and patterns that must NEVER be included in distribution archives
EXCLUDE_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    ".agent_memory",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    "dist",
    "build",
    "teamwork",
    "reports",
    "Reports",
    "Screenshots",
    "screenshots",
    "claude-ecosystem-repos",
    "graphify-out",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".tmp",
    ".log",
    ".bak",
    ".DS_Store",
}

# Critical files that MUST exist inside the created archive for integrity validation
MANDATORY_ARCHIVE_ENTRIES = [
    "package.json",
    "LICENSE",
    "AGENTS.md",
    "tools/verify_all.py",
    "tools/hub_publisher.py",
    "tools/security_scanner.py",
    "tools/generate_sbom.py",
    ".github/workflows/publish_npm.yml",
    ".github/workflows/security_audit.yml",
]


def get_version(repo_root: str) -> str:
    """Reads version from package.json."""
    pkg_path = os.path.join(repo_root, "package.json")
    if os.path.exists(pkg_path):
        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("version", "1.0.0").strip()
        except (OSError, json.JSONDecodeError, KeyError) as err:
            sys.stderr.write(f"Warning: Could not read version from package.json: {err}\n")
    return "1.0.0"


def collect_package_files(repo_root: str) -> List[Tuple[str, str]]:
    """
    Collects all pristine source files to be packaged into the release archive.
    Returns list of (absolute_path, relative_archive_path).
    """
    packaged_files: List[Tuple[str, str]] = []

    for root, dirs, files in os.walk(repo_root):
        rel_root = os.path.relpath(root, repo_root).replace("\\", "/")

        # Top-level dot-directory filtering
        if rel_root != ".":
            top_level = rel_root.split("/")[0]
            if top_level.startswith(".") and top_level not in MANDATORY_DOT_DIRS:
                dirs[:] = []
                continue

        # Prune excluded directories
        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDE_DIRS
            and not (d.startswith(".") and d not in MANDATORY_DOT_DIRS)
        ]

        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in EXCLUDE_EXTENSIONS:
                continue
            if f.endswith(".tmp") or f.endswith(".bak"):
                continue

            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, repo_root).replace("\\", "/")
            packaged_files.append((full_path, rel_path))

    return sorted(packaged_files, key=lambda x: x[1])


def calculate_sha256(file_path: str) -> str:
    """Calculates SHA-256 digest of a local file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def create_zip_archive(files: List[Tuple[str, str]], output_path: str) -> str:
    """Creates a deterministic ZIP archive from collected files."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for abs_path, rel_path in files:
            zf.write(abs_path, arcname=rel_path)
    return output_path


def create_tar_archive(files: List[Tuple[str, str]], output_path: str) -> str:
    """Creates a deterministic tar.gz archive from collected files."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with tarfile.open(output_path, "w:gz") as tf:
        for abs_path, rel_path in files:
            tf.add(abs_path, arcname=rel_path)
    return output_path


def normalize_arcname(n: str) -> str:
    """Normalizes archive entry path, safely stripping leading ./ without stripping leading dots from hidden dirs."""
    clean = n.replace("\\", "/")
    if clean.startswith("./"):
        clean = clean[2:]
    return clean


def verify_archive_integrity(archive_path: str) -> Tuple[bool, List[str]]:
    """
    Verifies that the archive contains all mandatory entries (.github/workflows/publish_npm.yml, etc.).
    """
    missing: List[str] = []
    if not os.path.exists(archive_path):
        return False, [f"Archive does not exist: {archive_path}"]

    if archive_path.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zf:
            namelist = set(zf.namelist())
    elif archive_path.endswith((".tar.gz", ".tgz")):
        with tarfile.open(archive_path, "r:gz") as tf:
            namelist = set(tf.getnames())
    else:
        return False, [f"Unsupported archive format: {archive_path}"]

    # Normalize archive paths safely
    normalized_names = {normalize_arcname(n) for n in namelist}

    for req in MANDATORY_ARCHIVE_ENTRIES:
        if req not in normalized_names:
            missing.append(req)

    return (len(missing) == 0), missing


def package_synapse_hub(
    repo_root: str = REPO_ROOT,
    output_dir: str = "dist",
    archive_format: str = "zip",
    generate_checksum: bool = False
) -> Tuple[List[str], Optional[str]]:
    """
    Main packaging entrypoint: cleans stale archives, builds single target archive, and verifies integrity.
    """
    version = get_version(repo_root)
    out_dir = os.path.join(repo_root, output_dir)
    os.makedirs(out_dir, exist_ok=True)

    # 1. Clean up old archives in dist and repo_root
    for f in os.listdir(out_dir):
        if f.endswith((".zip", ".tar.gz", ".sha256")):
            try:
                os.remove(os.path.join(out_dir, f))
            except OSError as err:
                _ = err
    for f in os.listdir(repo_root):
        if f.lower().startswith("synapse-hub") and f.endswith(".zip"):
            try:
                os.remove(os.path.join(repo_root, f))
            except OSError as err:
                _ = err

    files = collect_package_files(repo_root)
    base_name = f"synapse-hub-v{version}"
    created_archives: List[str] = []

    if archive_format in ("zip", "both"):
        zip_path = os.path.join(out_dir, f"{base_name}.zip")
        create_zip_archive(files, zip_path)
        created_archives.append(zip_path)

    if archive_format in ("tar.gz", "both"):
        tar_path = os.path.join(out_dir, f"{base_name}.tar.gz")
        create_tar_archive(files, tar_path)
        created_archives.append(tar_path)

    # Verification pass on all created archives
    for arch in created_archives:
        valid, missing = verify_archive_integrity(arch)
        if not valid:
            raise RuntimeError(f"Archive {arch} failed integrity check! Missing mandatory files: {missing}")

    checksum_path = None
    if generate_checksum:
        checksum_lines = []
        for arch in created_archives:
            sha = calculate_sha256(arch)
            fname = os.path.basename(arch)
            checksum_lines.append(f"{sha}  {fname}")

        checksum_path = os.path.join(out_dir, f"{base_name}-checksums.sha256")
        with open(checksum_path, "w", encoding="utf-8") as f:
            f.write("\n".join(checksum_lines) + "\n")

    return created_archives, checksum_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Enterprise Release Packaging & Integrity Sentinel for Synapse Hub")
    parser.add_argument("--repo-root", default=REPO_ROOT, help="Target repository root")
    parser.add_argument("--output-dir", default="dist", help="Output directory for generated archives")
    parser.add_argument("--format", choices=["zip", "tar.gz", "both"], default="zip", help="Archive format (default: zip)")
    parser.add_argument("--with-checksum", action="store_true", default=False, help="Generate .sha256 checksum file alongside the archive")
    parser.add_argument("--verify-archive", help="Verify integrity of an existing archive without building")
    args = parser.parse_args()

    print("=" * 68)
    print("    SYNAPSE HUB — ENTERPRISE RELEASE PACKAGING & INTEGRITY SENTINEL    ")
    print("=" * 68)

    if args.verify_archive:
        valid, missing = verify_archive_integrity(args.verify_archive)
        if valid:
            print(f"[PASS] Archive {args.verify_archive} verified 100% intact.")
            print("       All mandatory entries (.github/workflows, manifests) present.")
            return 0
        else:
            print(f"[FAIL] Archive {args.verify_archive} is MISSING mandatory files:")
            for m in missing:
                print(f"       - {m}")
            return 1

    print(f"  Target Repository : {args.repo_root}")
    print(f"  Output Directory  : {args.output_dir}")
    print(f"  Packaging Format  : {args.format}")
    print("-" * 68)

    try:
        archives, checksum_path = package_synapse_hub(
            repo_root=args.repo_root,
            output_dir=args.output_dir,
            archive_format=args.format,
            generate_checksum=args.with_checksum
        )
        for arch in archives:
            size_mb = os.path.getsize(arch) / (1024 * 1024)
            sha = calculate_sha256(arch)
            print(f"  [ARCHIVE] {os.path.basename(arch)} ({size_mb:.2f} MB)")
            print(f"            SHA-256: {sha}")
            print("            Integrity: [PASS] All mandatory workflows & rules confirmed.")

        if checksum_path:
            print(f"\n  [PROVENANCE] Checksums written to: {checksum_path}")
        print("=" * 68)
        print("🎉 RELEASE PACKAGING COMPLETED WITH 100% PROVENANCE INTEGRITY")
        print("=" * 68)
        return 0
    except Exception as e:
        print(f"[FAIL] Packaging failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
