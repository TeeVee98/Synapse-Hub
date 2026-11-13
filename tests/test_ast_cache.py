#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

import os
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, PROJECT_ROOT)

from tools.ast_cache import ASTValidationCache


class TestASTCache(unittest.TestCase):
    """Verifies AST Dataflow Pre-Validation Cache (Boost B3)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_file = os.path.join(self.temp_dir.name, "cache.json")
        self.cache = ASTValidationCache(repo_root=self.temp_dir.name, cache_path=self.cache_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cache_miss_and_put(self):
        test_py = os.path.join(self.temp_dir.name, "sample.py")
        with open(test_py, "w", encoding="utf-8") as f:
            f.write("x = 42\n")

        sig = self.cache.get_signature(test_py)
        self.assertIsNotNone(sig)
        mtime, size = sig

        # Miss initially
        res = self.cache.get_cached_result("sample.py", mtime, size)
        self.assertIsNone(res)

        # Put result and save
        self.cache.put_result("sample.py", mtime, size, {"violations": []})
        self.cache.save()

        # Reload cache from disk
        fresh_cache = ASTValidationCache(repo_root=self.temp_dir.name, cache_path=self.cache_file)
        hit = fresh_cache.get_cached_result("sample.py", mtime, size)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["violations"], [])

    def test_cache_invalidation_on_modification(self):
        test_py = os.path.join(self.temp_dir.name, "mutated.py")
        with open(test_py, "w", encoding="utf-8") as f:
            f.write("a = 1\n")

        sig1 = self.cache.get_signature(test_py)
        self.cache.put_result("mutated.py", sig1[0], sig1[1], {"violations": []})

        # Modify file
        with open(test_py, "w", encoding="utf-8") as f:
            f.write("a = 1\nb = 2\n")

        sig2 = self.cache.get_signature(test_py)
        # Old signature should miss
        miss = self.cache.get_cached_result("mutated.py", sig2[0], sig2[1])
        self.assertIsNone(miss)

    def test_concurrent_disk_merge(self):
        """Boost B3: Parallel workers saving cache do not overwrite each other's entries."""
        # Worker 1 saves file1
        cache1 = ASTValidationCache(repo_root=self.temp_dir.name, cache_path=self.cache_file)
        cache1.put_result("file1.py", 100, 200, {"violations": []})
        cache1.save()

        # Worker 2 loads, adds file2, saves
        cache2 = ASTValidationCache(repo_root=self.temp_dir.name, cache_path=self.cache_file)
        cache2.put_result("file2.py", 300, 400, {"violations": []})
        cache2.save()

        # Worker 1 adds file3 and saves; file2 must NOT be lost!
        cache1.put_result("file3.py", 500, 600, {"violations": []})
        cache1.save()

        # Reload and check all three exist
        merged_cache = ASTValidationCache(repo_root=self.temp_dir.name, cache_path=self.cache_file)
        self.assertIsNotNone(merged_cache.get_cached_result("file1.py", 100, 200))
        self.assertIsNotNone(merged_cache.get_cached_result("file2.py", 300, 400))
        self.assertIsNotNone(merged_cache.get_cached_result("file3.py", 500, 600))

    def test_clear_and_nonexistent_file(self):
        """Boost B3: get_signature on missing file returns None and clear() empties cache."""
        self.assertIsNone(self.cache.get_signature(os.path.join(self.temp_dir.name, "does_not_exist.py")))

        self.cache.put_result("dummy.py", 111, 222, {"violations": []})
        self.cache.save()
        self.assertTrue(len(self.cache._entries) > 0)

        self.cache.clear()
        self.assertEqual(len(self.cache._entries), 0)

        reloaded = ASTValidationCache(repo_root=self.temp_dir.name, cache_path=self.cache_file)
        self.assertEqual(len(reloaded._entries), 0)

    def test_cli_execution(self):
        """Boost B3: ast_cache.py runs cleanly as standalone script."""
        import subprocess
        proc = subprocess.run([sys.executable, os.path.join(PROJECT_ROOT, "tools", "ast_cache.py"), "--stats"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("[AST CACHE]", proc.stdout)


if __name__ == "__main__":
    unittest.main()
