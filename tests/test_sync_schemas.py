# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Unit Test Suite for Schema Synchronizer (tools.core.sync_schemas)
------------------------------------------------------------------
Validates JSON schema validation, codegen for Python/TS, and drift detection.
"""

import os
import sys
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.core import sync_schemas


class TestSyncSchemas(unittest.TestCase):
    def test_validate_config_conformance_valid(self):
        valid_cfg = {
            "version": "4.7.3",
            "quality_gates": {
                "mutation_min_score": 90,
                "gates": {
                    "gate_1_bom_check": True,
                    "gate_2_path_portability": True,
                    "gate_3_clean_pom": True,
                    "gate_4_ai_docs_lint": True,
                    "gate_5_cleanup_blacklist": True,
                    "gate_6_credential_security": True,
                    "gate_7_infer_linter": True,
                    "gate_8_micro_mutator": True,
                    "gate_9_skill_collision": True,
                    "gate_10_performance_sla": True,
                }
            }
        }
        errors = sync_schemas.validate_config_conformance(valid_cfg, {})
        self.assertEqual(len(errors), 0)

    def test_validate_config_conformance_missing_fields(self):
        invalid_cfg = {
            "version": "4.7.3",
            "quality_gates": {}
        }
        errors = sync_schemas.validate_config_conformance(invalid_cfg, {})
        self.assertGreaterEqual(len(errors), 1)
        self.assertTrue(any("mutation_min_score" in e for e in errors))

    def test_generate_python_models_contains_expected_classes(self):
        py_code = sync_schemas.generate_python_models({})
        self.assertIn("class QualityGatesDict(TypedDict):", py_code)
        self.assertIn("class QualityGateConfig(TypedDict):", py_code)
        self.assertIn("class SynapseConfig(TypedDict, total=False):", py_code)

    def test_generate_typescript_declarations_contains_expected_interfaces(self):
        ts_code = sync_schemas.generate_typescript_declarations({})
        self.assertIn("export interface QualityGatesMap {", ts_code)
        self.assertIn("export interface QualityGateConfig {", ts_code)
        self.assertIn("export interface SynapseConfig {", ts_code)

    def test_sync_all_check_only_passes_on_repo(self):
        ret = sync_schemas.sync_all(check_only=True)
        self.assertEqual(ret, 0)


if __name__ == "__main__":
    unittest.main()
