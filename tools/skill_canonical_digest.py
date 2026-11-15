#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/skill_canonical_digest.py — Single Source of Truth for Skill Canonical Digest & Lockfile Integrity
----------------------------------------------------------------------------------------------------------
Defines and enforces the strict deterministic canonicalization contract for skill folders:

1. Canonicalization Semantics:
   - Root: The skill folder directory (resolves parent directory if pointing to SKILL.md).
   - Traversal: Recursive directory walk across all nested files and subdirectories.
   - Exclusion Set:
       * OS artifacts: .DS_Store, Thumbs.db, desktop.ini, ehthumbs.db
       * Bytecode & runtime cache: __pycache__ directories, *.pyc, *.pyo, *.pyd
       * Editor swap/temp files: *~, *.swp, *.swo, *.tmp, .#*
       * Version control internals: .git, .svn, .hg, .gitignore
   - Symlink Policy: Prohibited (Fail-Closed). Any symlink inside a skill package raises ValueError.
   - Sorting / Ordering: Canonical lexicographical sort on relative POSIX paths (using forward slashes '/').
   - Entry Delimitation:
       * Relative POSIX path encoded as UTF-8, terminated by null byte (b"\\0").
       * Raw binary content read in 64KB chunks.
       * Trailing null byte (b"\\0") after file content to prevent path/content boundary collision.
   - Digest Algorithm: SHA-256 (64 lowercase hexadecimal characters).

2. Validation Invariant (Check Mode):
   - Purely read-only: STRICTLY ZERO filesystem modifications in check mode.
   - Lockfile Parity: skills-lock.json and .skill-lock.json must be byte-for-byte identical.
   - Dynamic Recomputation: Every validation computes digests live from disk; never trusts format alone.
   - Fail-Closed: Any missing file, forged hash, parity mismatch, or corrupted entry fails immediately.

3. Generation Invariant (Update Mode):
   - Explicit generator only (--update-hashes).
   - Deterministic key ordering and LF line endings produce 100% byte-identical output across runs.
"""

from __future__ import annotations

import os
import json
import hashlib
from typing import Tuple, List, Dict, Any

# Files and directories excluded from canonical hash calculation
EXCLUDED_FILENAMES = frozenset({
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    "ehthumbs.db",
    ".gitignore",
})

EXCLUDED_EXTENSIONS = (
    ".pyc",
    ".pyo",
    ".pyd",
    ".swp",
    ".swo",
    ".tmp",
    "~",
)

EXCLUDED_DIRNAMES = frozenset({
    "__pycache__",
    ".git",
    ".svn",
    ".hg",
})

TOTAL_REGISTERED_SKILLS = 53


def resolve_contained_skill_path(repo_root: str, skill_path: str) -> str:
    """
    Resolves skill_path strictly contained within repo_root.
    Rejects:
      - Parent directory traversal ('..')
      - Absolute paths outside repo_root
      - Symlinks and symlink escapes outside repo_root

    Returns:
      Canonical path within repo_root.

    Raises:
      ValueError: If skill_path violates containment constraints.
    """
    if not skill_path or not isinstance(skill_path, str):
        raise ValueError(f"Invalid skill_path: {skill_path!r}")

    # 1. Reject directory traversal '..'
    raw_parts = skill_path.replace("\\", "/").split("/")
    norm_parts = os.path.normpath(skill_path).replace("\\", "/").split("/")
    if ".." in raw_parts or ".." in norm_parts:
        raise ValueError(f"Directory traversal '..' prohibited in skill path: {skill_path}")

    norm_root = os.path.realpath(repo_root)
    agents_root = os.path.realpath(os.path.join(repo_root, ".agents"))

    # 2. Reject absolute path outside repo_root
    if os.path.isabs(skill_path):
        real_target = os.path.realpath(skill_path)
        is_under_root = real_target == norm_root or real_target.startswith(norm_root + os.sep)
        is_under_agents = os.path.exists(agents_root) and (real_target == agents_root or real_target.startswith(agents_root + os.sep))
        if not (is_under_root or is_under_agents):
            raise ValueError(f"Absolute path outside repo root prohibited: {skill_path}")
        target_path = os.path.normpath(skill_path)
    else:
        target_path = os.path.normpath(os.path.join(repo_root, skill_path))

    # 3. Reject symlink target
    if os.path.islink(target_path):
        raise ValueError(f"Symlinks are strictly prohibited for skill path: {skill_path}")

    # 4. Reject real target outside repo_root or .agents root
    real_target = os.path.realpath(target_path)
    is_under_root = real_target == norm_root or real_target.startswith(norm_root + os.sep)
    is_under_agents = os.path.exists(agents_root) and (real_target == agents_root or real_target.startswith(agents_root + os.sep))
    if not (is_under_root or is_under_agents):
        raise ValueError(f"Path escape outside repository root prohibited: {skill_path}")

    return target_path


def get_skill_canonical_entries(skill_folder_or_file: str) -> List[Tuple[str, str]]:
    """
    Collects and validates all canonical file entries for a skill folder.
    Returns a sorted list of (relative_posix_path, absolute_file_path).
    Raises ValueError if symlinks or invalid files are detected.
    """
    clean_path = os.path.abspath(skill_folder_or_file)
    if not os.path.exists(clean_path):
        raise FileNotFoundError(f"Skill path does not exist: {clean_path}")

    folder = os.path.dirname(clean_path) if os.path.isfile(clean_path) else clean_path
    entries: List[Tuple[str, str]] = []

    for root, dirs, files in os.walk(folder, topdown=True):
        # Prune excluded directories in-place (sorted for determinism)
        dirs[:] = [d for d in sorted(dirs) if d not in EXCLUDED_DIRNAMES]

        for f in sorted(files):
            # Exclude OS, editor, and cache files
            if f in EXCLUDED_FILENAMES:
                continue
            if any(f.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
                continue
            if f.startswith(".#"):
                continue

            full_p = os.path.join(root, f)
            rel_p = os.path.relpath(full_p, folder).replace("\\", "/")

            # Enforce symlink policy: reject symlinks to prevent traversal / spoofing
            if os.path.islink(full_p):
                raise ValueError(f"Symlinks are strictly prohibited inside canonical skill packages: {rel_p}")

            entries.append((rel_p, full_p))

    entries.sort(key=lambda x: x[0])
    return entries


def compute_skill_folder_hash(skill_folder_or_file: str) -> str:
    """
    Computes a deterministic canonical SHA-256 digest of a skill folder.
    Incorporates relative POSIX paths and file byte contents delimited by null bytes.
    """
    entries = get_skill_canonical_entries(skill_folder_or_file)
    hasher = hashlib.sha256()

    for rel_p, full_p in entries:
        hasher.update(rel_p.encode("utf-8"))
        hasher.update(b"\0")
        with open(full_p, "rb") as fh:
            while chunk := fh.read(65536):
                hasher.update(chunk)
        hasher.update(b"\0")

    return hasher.hexdigest().lower()


def validate_lockfile_integrity(repo_root: str, enforce_content_hash: bool = True) -> Tuple[bool, str]:
    """
    Validates canonical lockfile (skills-lock.json) and secondary (.skill-lock.json) integrity.
    Recomputes SHA-256 digests live from disk contents.

    IMPORTANT: This function runs strictly in check mode and NEVER modifies the working tree.
    """
    canonical_lock = os.path.join(repo_root, "skills-lock.json")
    secondary_lock = os.path.join(repo_root, ".skill-lock.json")

    # 1. Existence check
    if not os.path.exists(canonical_lock):
        return False, "Canonical lockfile skills-lock.json is missing!"
    if not os.path.exists(secondary_lock):
        return False, "Secondary lockfile .skill-lock.json is missing! Run generator to restore parity."

    # 2. Strict Lockfile Parity (Must be byte-for-byte identical; no auto-sync during check)
    try:
        with open(canonical_lock, "rb") as cf, open(secondary_lock, "rb") as sf:
            if cf.read() != sf.read():
                return False, (
                    "Lockfile parity mismatch: skills-lock.json and .skill-lock.json differ in content. "
                    "Run 'python3 tools/check_version_sync.py --update-hashes' to synchronize."
                )
    except OSError as err:
        return False, f"Failed to read lockfiles for parity check: {err}"

    # 3. JSON Parsing & Structure Validation
    try:
        with open(canonical_lock, "r", encoding="utf-8") as f:
            lock_data = json.load(f)
    except Exception as e:
        return False, f"skills-lock.json malformed JSON: {e}"

    if lock_data.get("version") != 3:
        return False, f"Unsupported lockfile format version: expected 3, found {lock_data.get('version')}"

    skills = lock_data.get("skills", {})
    if len(skills) != TOTAL_REGISTERED_SKILLS:
        return False, f"Expected {TOTAL_REGISTERED_SKILLS} skills in skills-lock.json, found {len(skills)}"

    # 4. Per-Skill Disk Recomputation & Verification
    for s_name, s_meta in skills.items():
        s_path = s_meta.get("skillPath")
        if not s_path:
            return False, f"Skill '{s_name}' missing skillPath"

        try:
            full_path = resolve_contained_skill_path(repo_root, s_path)
        except (ValueError, Exception) as err:
            return False, f"Skill '{s_name}' invalid skillPath: {err}"

        if not os.path.exists(full_path):
            return False, f"Skill '{s_name}' path not found: {s_path}"

        s_hash = s_meta.get("skillFolderHash")
        if not s_hash or len(s_hash) != 64 or not all(c in "0123456789abcdefABCDEF" for c in s_hash):
            return False, f"Skill '{s_name}' has invalid SHA-256 hash format: {s_hash}"

        if enforce_content_hash:
            try:
                computed_hash = compute_skill_folder_hash(full_path)
            except Exception as err:
                return False, f"Failed to compute canonical hash for skill '{s_name}': {err}"

            if s_hash.lower() != computed_hash.lower():
                return False, f"Skill '{s_name}' content hash mismatch: expected {computed_hash}, found in lockfile {s_hash}"

    return True, f"{len(skills)}/{TOTAL_REGISTERED_SKILLS} skills verified with valid paths & content SHA-256 hashes"


def update_skills_lockfile(repo_root: str) -> Tuple[bool, str]:
    """
    Recalculates canonical SHA-256 hashes for all 53 skills and writes to skills-lock.json & .skill-lock.json.
    Ensures deterministic output: generating twice on the same tree produces byte-identical files.
    """
    canonical_lock = os.path.join(repo_root, "skills-lock.json")
    secondary_lock = os.path.join(repo_root, ".skill-lock.json")

    if not os.path.exists(canonical_lock):
        return False, "Canonical lockfile skills-lock.json is missing!"

    try:
        with open(canonical_lock, "r", encoding="utf-8") as f:
            lock_data = json.load(f)
    except Exception as e:
        return False, f"skills-lock.json read error: {e}"

    skills = lock_data.get("skills", {})
    updated_skills: Dict[str, Any] = {}

    # Sort skills by name for deterministic serialization
    for s_name in sorted(skills.keys()):
        s_meta = skills[s_name]
        s_path = s_meta.get("skillPath")
        if not s_path:
            return False, f"Skill '{s_name}' missing skillPath"
        try:
            full_path = resolve_contained_skill_path(repo_root, s_path)
        except (ValueError, Exception) as err:
            return False, f"Skill '{s_name}' invalid skillPath: {err}"
        if not os.path.exists(full_path):
            return False, f"Skill '{s_name}' path not found: {s_path}"

        computed_hash = compute_skill_folder_hash(full_path)
        s_meta["skillFolderHash"] = computed_hash
        updated_skills[s_name] = s_meta

    lock_data["skills"] = updated_skills
    content_str = json.dumps(lock_data, indent=2, ensure_ascii=False) + "\n"

    try:
        with open(canonical_lock, "w", encoding="utf-8", newline="\n") as f:
            f.write(content_str)
        with open(secondary_lock, "w", encoding="utf-8", newline="\n") as f:
            f.write(content_str)
    except OSError as err:
        return False, f"Failed to write lockfiles: {err}"

    return True, f"Successfully recalculated and synchronized canonical hashes for {len(updated_skills)} skills."
