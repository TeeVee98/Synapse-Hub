#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tests/test_security_scanner.py — Unit Tests for SBOM Generation & Security Scanner
"""

import os
import sys
import json
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
sys.path.insert(0, TOOLS_DIR)

import generate_sbom
import security_scanner


class TestSecurityScannerAndSBOM(unittest.TestCase):
    """Verifies that SBOM generation and security scanning function correctly."""

    def test_spdx_sbom_generation_conforms_to_standard(self):
        sbom = generate_sbom.build_spdx_sbom(REPO_ROOT)
        self.assertEqual(sbom.get("spdxVersion"), "SPDX-2.3")
        self.assertEqual(sbom.get("dataLicense"), "CC0-1.0")
        self.assertIn("packages", sbom)
        self.assertIn("relationships", sbom)
        self.assertGreaterEqual(len(sbom["packages"]), 1)

        # Verify root package
        root = sbom["packages"][0]
        self.assertEqual(root["name"], "synapse-hub")
        self.assertEqual(root["licenseConcluded"], "MIT")
        self.assertIn("Thế Vị (@TeeVee998)", root["supplier"])

    def test_shannon_entropy_calculation(self):
        low_entropy = security_scanner.calculate_shannon_entropy("aaaaaaaaaaaa")
        high_entropy = security_scanner.calculate_shannon_entropy("xK9$mZ2!pL8@vQ4#wR7*")
        self.assertLess(low_entropy, 1.0)
        self.assertGreater(high_entropy, 3.5)

    def test_run_security_scan_passes(self):
        report = security_scanner.run_security_scan(REPO_ROOT)
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["checks"]["threat_model_firewall"]["passed"])
        self.assertEqual(len(report["checks"]["threat_model_firewall"]["findings"]), 0)


if __name__ == "__main__":
    unittest.main()
