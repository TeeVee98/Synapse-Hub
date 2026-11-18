#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_synapse_modular_architecture.py — Verification of Phase 1 Modular Architecture
------------------------------------------------------------------------------------------
Verifies that:
1. `import synapse` operates as a first-class enterprise SDK.
2. All 13 domain packages under `tools.*` are importable and expose their exported tools.
3. Backward compatibility is 100% preserved for root `tools.*` imports.
4. Auxiliary/niche extensions are cleanly mapped into `tools.contrib`.
"""

import unittest
import sys
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)


class TestSynapseModularArchitecture(unittest.TestCase):
    """Test suite validating Phase 1 modularization and namespace integrity."""

    def test_synapse_root_sdk_import(self):
        """Verify that `import synapse` exposes version, author and subpackages."""
        import synapse
        self.assertEqual(synapse.__author__, "Thế Vị (@TeeVee98)")
        self.assertTrue(hasattr(synapse, "__version__"))
        self.assertTrue(hasattr(synapse, "core"))
        self.assertTrue(hasattr(synapse, "sentinels"))
        self.assertTrue(hasattr(synapse, "healing"))
        self.assertTrue(hasattr(synapse, "context"))
        self.assertTrue(hasattr(synapse, "security"))
        self.assertTrue(hasattr(synapse, "api"))
        self.assertTrue(hasattr(synapse, "transpiler"))
        self.assertTrue(hasattr(synapse, "design"))
        self.assertTrue(hasattr(synapse, "orchestration"))
        self.assertTrue(hasattr(synapse, "contrib"))

    def test_domain_subpackages_exposure(self):
        """Verify all 13 domain packages are accessible via tools."""
        import tools
        expected_domains = [
            "core", "lint", "heal", "context", "security", "api",
            "perf", "report", "design", "transpiler", "orchestration", "mcp", "contrib"
        ]
        for domain in expected_domains:
            self.assertTrue(
                hasattr(tools, domain),
                f"Missing expected domain package: tools.{domain}"
            )
            subpkg = getattr(tools, domain)
            self.assertTrue(hasattr(subpkg, "__all__"), f"tools.{domain} missing __all__")
            self.assertGreater(len(subpkg.__all__), 0, f"tools.{domain} has empty __all__")

    def test_context_domain_imports(self):
        """Verify context engineering tools are accessible via tools.context."""
        from tools.context import (
            context_slicer,
            distill_log,
            repo_map,
            rule_harvester,
            count_tokens,
        )
        self.assertIsNotNone(context_slicer)
        self.assertIsNotNone(distill_log)
        self.assertIsNotNone(repo_map)
        self.assertIsNotNone(rule_harvester)
        self.assertIsNotNone(count_tokens)

    def test_security_domain_imports(self):
        """Verify security sentinels are accessible via tools.security."""
        from tools.security import (
            asvs_auditor,
            cvss_calculator,
            safety_firewall,
            security_scanner,
            wcag_audit,
        )
        self.assertIsNotNone(asvs_auditor)
        self.assertIsNotNone(cvss_calculator)
        self.assertIsNotNone(safety_firewall)
        self.assertIsNotNone(security_scanner)
        self.assertIsNotNone(wcag_audit)

    def test_api_domain_imports(self):
        """Verify API contract tools are accessible via tools.api."""
        from tools.api import (
            api_drift_sentinel,
            api_fuzzer,
            contract_validator,
            network_mock_shield,
        )
        self.assertIsNotNone(api_drift_sentinel)
        self.assertIsNotNone(api_fuzzer)
        self.assertIsNotNone(contract_validator)
        self.assertIsNotNone(network_mock_shield)

    def test_transpiler_domain_imports(self):
        """Verify Universal IR tools are accessible via tools.transpiler."""
        from tools.transpiler import universal_ir, omni_parser, omni_emitter
        self.assertIsNotNone(universal_ir)
        self.assertIsNotNone(omni_parser)
        self.assertIsNotNone(omni_emitter)

    def test_contrib_domain_imports(self):
        """Verify auxiliary tools are cleanly categorized in tools.contrib."""
        from tools.contrib import (
            slide_deck_exporter,
            payment_interop_simulator,
            openxml_guard,
            diagram_architect,
            cldr_l10n_verifier,
        )
        self.assertIsNotNone(slide_deck_exporter)
        self.assertIsNotNone(payment_interop_simulator)
        self.assertIsNotNone(openxml_guard)
        self.assertIsNotNone(diagram_architect)
        self.assertIsNotNone(cldr_l10n_verifier)

    def test_backward_compatibility_preserved(self):
        """Verify root tool imports continue to work seamlessly without breakage."""
        import verify_all
        import infer_linter
        import micro_mutator
        import check_env
        self.assertTrue(hasattr(verify_all, "run_all_gates"))
        self.assertTrue(hasattr(infer_linter, "run_infer_linter"))
        self.assertTrue(hasattr(micro_mutator, "generate_mutants_for_code"))
        self.assertTrue(hasattr(check_env, "DiagnosticRunner"))

    def test_zero_sprawl_in_tools_root(self):
        """Verify that tools root contains ZERO file sprawl (only __init__.py and domain dirs)."""
        root_py_files = [
            f for f in os.listdir(TOOLS_DIR)
            if f.endswith(".py") and os.path.isfile(os.path.join(TOOLS_DIR, f))
        ]
        self.assertEqual(
            root_py_files,
            ["__init__.py"],
            f"Tools root still contains loose python files: {root_py_files}"
        )


if __name__ == "__main__":
    unittest.main()
