import unittest
import os
import tempfile
import threading
import gc
import sys

# Ensure tools directory is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import cache_resolver


class TestCacheResolver(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self.temp_dir.name, "test_cache.db")
        self.orig_db_file = cache_resolver.DB_FILE
        cache_resolver.DB_FILE = self.db_path

    def tearDown(self):
        cache_resolver.DB_FILE = self.orig_db_file
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_wal_mode_enabled(self):
        conn = cache_resolver.get_db(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        self.assertEqual(mode.lower(), "wal")
        conn.close()

    def test_positive_and_negative_memory(self):
        # 1. Record solution
        cache_resolver.learn_solution(
            error_signature="StaleElementTest",
            module_name="TestPage",
            symptom="Stale element reference",
            root_cause="DOM re-rendered",
            groovy_patch="BasePage.clickJS(el)"
        )
        # 2. Record failed fix
        cache_resolver.record_failed_fix(
            error_signature="StaleElementTest",
            attempted_patch="el.click()",
            failure_reason="Still stale",
            agent_role="pom-crafter"
        )

        # 3. Query solution
        res = cache_resolver.query_solution("StaleElementTest", module_name="TestPage")
        self.assertIsNotNone(res)
        self.assertEqual(res["groovy_patch"], "BasePage.clickJS(el)")
        self.assertEqual(len(res["failed_fixes"]), 1)
        self.assertEqual(res["failed_fixes"][0]["attempted_patch"], "el.click()")

    def test_concurrent_writes(self):
        """Stress test: 10 concurrent threads inserting into SQLite without database is locked error."""
        errors = []

        def worker(thread_id):
            try:
                for i in range(15):
                    cache_resolver.record_failed_fix(
                        error_signature=f"ConcurrentErr_{thread_id}",
                        attempted_patch=f"patch_{i}",
                        failure_reason="test concurrent locking",
                        agent_role=f"worker_{thread_id}"
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Encountered concurrency errors: {errors}")


if __name__ == "__main__":
    unittest.main()
