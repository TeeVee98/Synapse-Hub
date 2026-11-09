#!/usr/bin/env python3
"""
Unit tests validating tools domain packages structure and backwards compatibility.
"""

import unittest
from tools import core, heal, lint, mcp, perf, report


class TestDomainPackages(unittest.TestCase):
    def test_core_package_exports(self):
        self.assertTrue(hasattr(core, "verify_all"))
        self.assertTrue(hasattr(core, "cli"))
        self.assertTrue(hasattr(core, "setup_project"))
        self.assertTrue(hasattr(core, "analyze_project"))
        self.assertTrue(callable(getattr(core.verify_all, "run_all_gates", None)))

    def test_lint_package_exports(self):
        self.assertTrue(hasattr(lint, "infer_linter"))
        self.assertTrue(hasattr(lint, "lint_ai_docs"))
        self.assertTrue(hasattr(lint, "author_integrity"))
        self.assertTrue(callable(getattr(lint.infer_linter, "run_infer_linter", None)))

    def test_report_package_exports(self):
        self.assertTrue(hasattr(report, "dashboard_generator"))
        self.assertTrue(hasattr(report, "output_formatter"))
        self.assertTrue(hasattr(report, "telemetry_correlator"))
        self.assertTrue(callable(getattr(report.dashboard_generator, "generate_target_project_html", None)))

    def test_heal_package_exports(self):
        self.assertTrue(hasattr(heal, "auto_heal"))
        self.assertTrue(hasattr(heal, "cache_resolver"))
        self.assertTrue(hasattr(heal, "reversible_sandbox"))
        self.assertTrue(callable(getattr(heal.auto_heal, "main", None)))

    def test_perf_package_exports(self):
        self.assertTrue(hasattr(perf, "generate_jmx_plan"))
        self.assertTrue(hasattr(perf, "flaky_detector"))
        self.assertTrue(hasattr(perf, "matrix_sharder"))
        self.assertTrue(callable(getattr(perf.matrix_sharder, "main", None)))

    def test_mcp_package_exports(self):
        self.assertTrue(hasattr(mcp, "mcp_server"))
        self.assertTrue(hasattr(mcp, "mcp_excel_server"))
        self.assertTrue(hasattr(mcp, "mcp_docx_server"))
        self.assertTrue(callable(getattr(mcp.mcp_server, "run_stdio_server", None)))


if __name__ == "__main__":
    unittest.main()
