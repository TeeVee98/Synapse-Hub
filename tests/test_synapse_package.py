#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tests/test_synapse_package.py — Unit tests for PEP 517 synapse package
---------------------------------------------------------------------
Verifies that `synapse` namespace imports cleanly, matches version 4.7.0,
and exposes core SDK modules and classes without broken references.
"""

import json
import os
import unittest
import synapse


class TestSynapsePackage(unittest.TestCase):

    def test_synapse_version_and_author(self):
        pkg_path = os.path.join(os.path.dirname(__file__), "..", "package.json")
        with open(pkg_path, "r", encoding="utf-8") as f:
            expected_ver = json.load(f)["version"]
        self.assertEqual(synapse.__version__, expected_ver)
        self.assertIn("Thế Vị (@TeeVee98)", synapse.__author__)

    def test_synapse_core_engines_imported(self):
        self.assertIsNotNone(synapse.SessionVault)
        self.assertIsNotNone(synapse.VisualSoMHelper)
        self.assertIsNotNone(synapse.LiveVisualHealer)

    def test_synapse_namespaces(self):
        self.assertTrue(hasattr(synapse, "core"))
        self.assertTrue(hasattr(synapse, "lint"))
        self.assertTrue(hasattr(synapse, "mcp"))
        self.assertTrue(hasattr(synapse, "orchestration"))
        self.assertTrue(hasattr(synapse, "security"))
        self.assertTrue(hasattr(synapse, "sentinels"))
        self.assertTrue(hasattr(synapse, "healing"))


if __name__ == "__main__":
    unittest.main()
