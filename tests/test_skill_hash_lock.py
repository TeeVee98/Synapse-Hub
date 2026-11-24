#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tests/test_skill_hash_lock.py — Regression & Content Integrity Tests for Canonical Skill Hashes
------------------------------------------------------------------------------------------------
Comprehensive tests verifying the deterministic canonicalization contract:
  1. All 53 registered skills in skills-lock.json match their live folder content SHA-256 hash.
  2. Byte-for-byte parity synchronization between skills-lock.json and .skill-lock.json.
  3. Fake 64-hex hash fails validation (format-only check is rejected).
  4. Single byte alteration in SKILL.md fails validation.
  5. Adding or removing a file in a skill package alters the hash and fails validation.
  6. Renaming a file in a skill package alters the relative POSIX path and alters the hash.
  7. Modifying a nested resource in a subfolder alters the hash.
  8. OS artifacts (.DS_Store, Thumbs.db, __pycache__) are ignored and do not alter the hash.
  9. Check mode is strictly read-only and never modifies the working tree (no auto-sync in check mode).
  10. Generating lockfile twice on the same tree produces 100% byte-identical output.
  11. Symlinks inside skill packages are prohibited (fail-closed).
"""

import os
import sys
import json
import shutil
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from skill_canonical_digest import (
    compute_skill_folder_hash,
    validate_lockfile_integrity,
    update_skills_lockfile,
    resolve_contained_skill_path,
)


def _link_or_copy_dir(src, dst):
    """Safely links or copies directory for cross-platform test isolation (Windows non-admin safe)."""
    if sys.platform == "win32":
        try:
            import _winapi
            _winapi.CreateJunction(src, dst)
            return
        except Exception:
            pass
    try:
        os.symlink(src, dst)
    except OSError:
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("*.lock", "*.tmp", "__pycache__", "*.pyc"))


def _link_skills_into_td(td):
    for d in ["skills", "standards", "requirement", "test-design", "testing", "automation", "ai-agents", "integrations"]:
        src = os.path.join(REPO_ROOT, d)
        if os.path.exists(src):
            dst = os.path.join(td, d)
            if not os.path.exists(dst):
                shutil.copytree(
                    src, dst, symlinks=False, ignore=shutil.ignore_patterns("*.lock", "*.tmp", "__pycache__", "*.pyc")
                )


class TestSkillHashLockIntegrity(unittest.TestCase):
    """Test suite for canonical skill folder digest computation and verification."""

    def test_all_56_skills_match_canonical_hashes(self):
        """Positive test: all skills in the repository must match their content SHA-256."""
        ok, msg = validate_lockfile_integrity(REPO_ROOT, enforce_content_hash=True)
        self.assertTrue(ok, f"Lockfile integrity verification failed: {msg}")
        self.assertIn("57/57 skills verified with valid paths & content SHA-256 hashes", msg)

    def test_lockfile_parity_synchronized(self):
        """Canonical skills-lock.json must exist and duplicate .skill-lock.json must be absent."""
        p1 = os.path.join(REPO_ROOT, "skills-lock.json")
        p2 = os.path.join(REPO_ROOT, ".skill-lock.json")
        self.assertTrue(os.path.exists(p1), "skills-lock.json must exist")
        self.assertFalse(os.path.exists(p2), "Duplicate .skill-lock.json must not exist")

    def test_fake_64_hex_hash_rejected(self):
        """Negative test: a validly-formatted 64-hex hash with incorrect content must fail validation."""
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(REPO_ROOT, "skills-lock.json"), "r", encoding="utf-8") as f:
                lock_data = json.load(f)

            # Tamper one skill with a fake 64-hex hash
            target_skill = next(iter(lock_data["skills"]))
            original_hash = lock_data["skills"][target_skill]["skillFolderHash"]
            fake_hash = "0" * 64
            lock_data["skills"][target_skill]["skillFolderHash"] = fake_hash

            content_str = json.dumps(lock_data, indent=2) + "\n"
            with open(os.path.join(td, "skills-lock.json"), "w", encoding="utf-8") as f:
                f.write(content_str)

            _link_skills_into_td(td)
            ok_fake, msg_fake = validate_lockfile_integrity(td, enforce_content_hash=True)
            self.assertFalse(ok_fake, "Validation must fail when hash is forged")
            self.assertIn("content hash mismatch", msg_fake)
            self.assertIn(fake_hash, msg_fake)

    def test_single_byte_mutation_in_skill_fails(self):
        """Negative test: altering a single byte in any skill file must invalidate the canonical hash."""
        with tempfile.TemporaryDirectory() as td:
            skill_dir = os.path.join(td, "mock-skill")
            os.makedirs(skill_dir, exist_ok=True)
            skill_md = os.path.join(skill_dir, "SKILL.md")
            with open(skill_md, "w", encoding="utf-8") as f:
                f.write("# Clean POM Crafter Skill\nVersion: 1.0\n")

            initial_hash = compute_skill_folder_hash(skill_dir)
            self.assertEqual(len(initial_hash), 64)

            # Mutate one byte
            with open(skill_md, "w", encoding="utf-8") as f:
                f.write("# Clean POM Crafter Skill\nVersion: 1.1\n")

            mutated_hash = compute_skill_folder_hash(skill_dir)
            self.assertNotEqual(initial_hash, mutated_hash, "Hash must change when content changes by 1 byte")

    def test_adding_or_removing_file_in_skill_alters_hash(self):
        """Negative test: adding or removing a file in a skill folder alters the digest."""
        with tempfile.TemporaryDirectory() as td:
            skill_dir = os.path.join(td, "mock-skill")
            os.makedirs(skill_dir, exist_ok=True)
            with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
                f.write("# Skill\n")

            base_hash = compute_skill_folder_hash(skill_dir)

            # Add a secondary file
            extra_file = os.path.join(skill_dir, "extra.json")
            with open(extra_file, "w", encoding="utf-8") as f:
                f.write('{"test": true}\n')

            hash_with_added = compute_skill_folder_hash(skill_dir)
            self.assertNotEqual(base_hash, hash_with_added, "Adding a file must alter the canonical digest")

            # Remove the secondary file
            os.remove(extra_file)
            hash_after_remove = compute_skill_folder_hash(skill_dir)
            self.assertEqual(base_hash, hash_after_remove, "Removing added file must restore original digest")

    def test_renaming_file_with_same_content_alters_hash(self):
        """Negative test: renaming a file with identical content alters relative path and digest."""
        with tempfile.TemporaryDirectory() as td:
            skill_dir = os.path.join(td, "mock-skill")
            os.makedirs(os.path.join(skill_dir, "examples"), exist_ok=True)
            with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
                f.write("# Skill\n")

            path_a = os.path.join(skill_dir, "examples", "file_a.json")
            with open(path_a, "w", encoding="utf-8") as f:
                f.write('{"payload": 123}\n')

            hash_a = compute_skill_folder_hash(skill_dir)

            # Rename file_a.json to file_b.json (content identical)
            path_b = os.path.join(skill_dir, "examples", "file_b.json")
            os.rename(path_a, path_b)
            hash_b = compute_skill_folder_hash(skill_dir)

            self.assertNotEqual(hash_a, hash_b, "Renaming a file must alter canonical digest due to path change")

    def test_modifying_nested_resource_alters_hash(self):
        """Negative test: modifying a nested file in a subdirectory alters the digest."""
        with tempfile.TemporaryDirectory() as td:
            skill_dir = os.path.join(td, "mock-skill")
            nested_dir = os.path.join(skill_dir, "references", "specs")
            os.makedirs(nested_dir, exist_ok=True)
            with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
                f.write("# Skill\n")
            spec_file = os.path.join(nested_dir, "contract.json")
            with open(spec_file, "w", encoding="utf-8") as f:
                f.write('{"version": "1.0.0"}\n')

            hash_initial = compute_skill_folder_hash(skill_dir)

            # Mutate nested file
            with open(spec_file, "w", encoding="utf-8") as f:
                f.write('{"version": "1.0.1"}\n')

            hash_mutated = compute_skill_folder_hash(skill_dir)
            self.assertNotEqual(hash_initial, hash_mutated, "Mutating nested file must alter canonical digest")

    def test_excluded_files_do_not_alter_hash(self):
        """Positive test: OS and temporary artifacts (.DS_Store, Thumbs.db, __pycache__) do not alter hash."""
        with tempfile.TemporaryDirectory() as td:
            skill_dir = os.path.join(td, "mock-skill")
            os.makedirs(skill_dir, exist_ok=True)
            with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
                f.write("# Deterministic Skill\n")

            clean_hash = compute_skill_folder_hash(skill_dir)

            # Add OS artifacts and cache files
            with open(os.path.join(skill_dir, ".DS_Store"), "wb") as f:
                f.write(b"\x00\x01\x02\x03")
            with open(os.path.join(skill_dir, "Thumbs.db"), "wb") as f:
                f.write(b"THUMBS_DB_MOCK")
            pycache_dir = os.path.join(skill_dir, "__pycache__")
            os.makedirs(pycache_dir, exist_ok=True)
            with open(os.path.join(pycache_dir, "helper.cpython-310.pyc"), "wb") as f:
                f.write(b"BYTECODE_MOCK")

            hash_with_artifacts = compute_skill_folder_hash(skill_dir)
            self.assertEqual(clean_hash, hash_with_artifacts, "Excluded artifacts must not alter canonical digest")

    def test_check_mode_never_modifies_working_tree(self):
        """In check mode, validate_lockfile_integrity must NEVER rewrite or modify files on disk."""
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(REPO_ROOT, "skills-lock.json"), "r", encoding="utf-8") as f:
                lock_data = json.load(f)

            canonical_p = os.path.join(td, "skills-lock.json")
            secondary_p = os.path.join(td, ".skill-lock.json")

            with open(canonical_p, "w", encoding="utf-8") as f:
                json.dump(lock_data, f, indent=2)

            # Secondary lockfile has different content (stale)
            stale_data = {"version": 3, "stale": True}
            with open(secondary_p, "w", encoding="utf-8") as f:
                json.dump(stale_data, f, indent=2)

            mtime_before = os.path.getmtime(secondary_p)
            with open(secondary_p, "rb") as f:
                content_before = f.read()

            # Run validation in check mode
            ok, msg = validate_lockfile_integrity(td, enforce_content_hash=True)
            self.assertFalse(ok, "Check mode must fail when secondary lockfile has parity mismatch")
            self.assertIn("parity mismatch", msg.lower())

            # Verify that secondary_p was NOT modified
            with open(secondary_p, "rb") as f:
                content_after = f.read()
            self.assertEqual(content_before, content_after, "Check mode must not modify working tree")

    def test_generate_lock_twice_is_byte_identical(self):
        """Generating lockfile twice on the exact same tree must produce 100% byte-identical output."""
        with tempfile.TemporaryDirectory() as td:
            # Copy canonical lockfile and unified skills/
            shutil.copy2(os.path.join(REPO_ROOT, "skills-lock.json"), os.path.join(td, "skills-lock.json"))
            _link_skills_into_td(td)

            # Run generation 1
            ok1, msg1 = update_skills_lockfile(td)
            self.assertTrue(ok1, msg1)
            with open(os.path.join(td, "skills-lock.json"), "rb") as f:
                run1_bytes = f.read()

            # Run generation 2
            ok2, msg2 = update_skills_lockfile(td)
            self.assertTrue(ok2, msg2)
            with open(os.path.join(td, "skills-lock.json"), "rb") as f:
                run2_bytes = f.read()

            self.assertEqual(run1_bytes, run2_bytes, "Generating lockfile twice must produce byte-identical output")

    def test_symlinks_inside_skill_package_prohibited(self):
        """Symlinks inside a skill folder are prohibited to prevent arbitrary traversal."""
        with tempfile.TemporaryDirectory() as td:
            skill_dir = os.path.join(td, "mock-skill")
            os.makedirs(skill_dir, exist_ok=True)
            with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
                f.write("# Skill\n")

            # Create an internal symlink
            symlink_p = os.path.join(skill_dir, "symlink_test.md")
            try:
                os.symlink(os.path.join(skill_dir, "SKILL.md"), symlink_p)
            except OSError:
                self.skipTest("Symlinks not supported without admin privileges on Windows")

            with self.assertRaises(ValueError) as ctx:
                compute_skill_folder_hash(skill_dir)
            self.assertIn("Symlinks are strictly prohibited", str(ctx.exception))

    def test_resolve_contained_skill_path_rejects_parent_traversal(self):
        """Negative test: path traversal using '..' is rejected."""
        with self.assertRaises(ValueError) as ctx:
            resolve_contained_skill_path(REPO_ROOT, "../../outside/sensitive.txt")
        self.assertIn("Directory traversal '..' prohibited", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx2:
            resolve_contained_skill_path(REPO_ROOT, ".agents/skills/../../etc/shadow")
        self.assertIn("Directory traversal '..' prohibited", str(ctx2.exception))

    def test_resolve_contained_skill_path_rejects_absolute_path_outside_repo(self):
        """Negative test: absolute path outside repository root is rejected."""
        with self.assertRaises(ValueError) as ctx:
            resolve_contained_skill_path(REPO_ROOT, "/etc/passwd")
        self.assertIn("Absolute path outside repo root prohibited", str(ctx.exception))

    def test_resolve_contained_skill_path_rejects_symlink_target(self):
        """Negative test: symlink skill targets are rejected fail-closed."""
        with tempfile.TemporaryDirectory() as td:
            outside = os.path.join(td, "outside_dir")
            os.makedirs(outside)
            target_outside = os.path.join(outside, "target.txt")
            with open(target_outside, "w") as f:
                f.write("OUTSIDE")

            repo_mock = os.path.join(td, "repo")
            os.makedirs(repo_mock)
            symlink_path = os.path.join(repo_mock, "sym_skill")
            try:
                os.symlink(target_outside, symlink_path)
            except OSError:
                self.skipTest("Symlinks not supported on filesystem")

            with self.assertRaises(ValueError) as ctx:
                resolve_contained_skill_path(repo_mock, "sym_skill")
            self.assertIn("Symlinks are strictly prohibited", str(ctx.exception))

    def test_resolve_contained_skill_path_accepts_valid_contained_path(self):
        """Positive test: valid relative skill paths resolve strictly under repo root."""
        valid_rel = "skills/01-web-automation/clean-pom-crafter/SKILL.md"
        resolved = resolve_contained_skill_path(REPO_ROOT, valid_rel)
        expected = os.path.normpath(os.path.join(REPO_ROOT, valid_rel))
        self.assertEqual(resolved, expected)
        self.assertTrue(os.path.isfile(resolved))

    def test_one_to_one_manifest_to_lock_mapping(self):
        """Verifies 1:1 parity between skills_manifest.json and skills-lock.json with 0 stale entries."""
        manifest_path = os.path.join(REPO_ROOT, "skills_manifest.json")
        lock_path = os.path.join(REPO_ROOT, "skills-lock.json")

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
        with open(lock_path, "r", encoding="utf-8") as f:
            lock_data = json.load(f)

        manifest_ids = {s["id"] for s in manifest_data.get("skills", [])}
        lock_ids = set(lock_data.get("skills", {}).keys())

        self.assertEqual(len(manifest_ids), 57, f"Expected 57 manifest skills, got {len(manifest_ids)}")
        self.assertEqual(len(lock_ids), 57, f"Expected 57 lock skills, got {len(lock_ids)}")
        self.assertEqual(manifest_ids, lock_ids, "Manifest and lockfile must have identical skill ID sets")


if __name__ == "__main__":
    unittest.main()
