#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, PROJECT_ROOT)

from tools.core.process_supervisor import ProcessSupervisor, kill_process_tree, reap_orphan_processes


class TestProcessSupervisor(unittest.TestCase):

    def setUp(self):
        self.supervisor = ProcessSupervisor(default_timeout=5.0)

    def tearDown(self):
        self.supervisor.cleanup_all()

    def test_run_successful_command(self):
        res = self.supervisor.run([sys.executable, "-c", "print('hello_supervisor')"])
        self.assertTrue(res.ok)
        self.assertEqual(res.returncode, 0)
        self.assertIn("hello_supervisor", res.stdout)
        self.assertFalse(res.timed_out)

    def test_run_failing_command(self):
        res = self.supervisor.run([sys.executable, "-c", "import sys; sys.exit(42)"])
        self.assertFalse(res.ok)
        self.assertEqual(res.returncode, 42)
        self.assertFalse(res.timed_out)

    def test_run_timeout_kills_process_group(self):
        # Command that sleeps for 10s with timeout=0.5s
        res = self.supervisor.run(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            timeout=0.5
        )
        self.assertTrue(res.timed_out)
        self.assertEqual(res.returncode, 124)

    def test_kill_process_tree_posix_does_not_kill_caller_pgrp(self):
        import unittest.mock as mock
        # Simulate POSIX environment where target has same pgid as caller
        with mock.patch("sys.platform", "linux"), \
             mock.patch("os.getpgrp", return_value=1000, create=True), \
             mock.patch("os.getpgid", return_value=1000, create=True), \
             mock.patch("os.killpg", create=True) as mock_killpg, \
             mock.patch("os.kill", create=True) as mock_kill, \
             mock.patch("subprocess.run") as mock_sub:
            mock_sub.return_value = mock.MagicMock(returncode=1, stdout="")
            # Target pid 1005 is not group leader (candidate_pgid 1000 != 1005, and == caller_pgrp)
            res = kill_process_tree(1005, timeout=0.05)
            self.assertTrue(res)
            # mock_killpg MUST NOT be called because it would kill caller's process group
            mock_killpg.assert_not_called()
            # Individual kill on pid 1005 should be called
            mock_kill.assert_any_call(1005, mock.ANY)

    def test_context_manager_usage(self):
        with ProcessSupervisor(default_timeout=2.0) as sup:
            res = sup.run([sys.executable, "-c", "print('inside_ctx')"])
            self.assertTrue(res.ok)
            self.assertIn("inside_ctx", res.stdout)

    def test_kill_process_tree_invalid_pid(self):
        self.assertFalse(kill_process_tree(-1))
        self.assertFalse(kill_process_tree(0))

    def test_reap_orphan_processes_no_crash(self):
        count = reap_orphan_processes(("non_existent_process_xyz_123",))
        self.assertIsInstance(count, int)

    def test_descendant_child_reaped_on_timeout(self):
        # Cross-platform process hierarchy: parent spawns a long-sleeping descendant
        cmd = [
            sys.executable,
            "-c",
            "import subprocess, sys; "
            "p = subprocess.Popen([sys.executable, '-c', 'import time; getattr(time, \"sleep\")(30)']); "
            "p.wait()",
        ]
        res = self.supervisor.run(cmd, timeout=0.3)
        self.assertTrue(res.timed_out)
        self.assertEqual(res.returncode, 124)


if __name__ == "__main__":
    unittest.main()
