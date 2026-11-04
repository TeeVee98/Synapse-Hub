"""
Synapse Hub — Reporting & Telemetry Engines (tools.report)
----------------------------------------------------------
Domain package grouping all HTML dashboard, spreadsheet, JTL/Newman
metric parser, and visual reporting tools.
"""

from tools import (
    bug_reporter,
    dashboard_generator,
    generate_allure_report,
    generate_test_reports,
    jtl_analyzer,
    md_to_xlsx,
    newman_analyzer,
    output_formatter,
    telemetry_correlator,
    welcome_page,
)

__all__ = [
    "bug_reporter",
    "dashboard_generator",
    "generate_allure_report",
    "generate_test_reports",
    "jtl_analyzer",
    "md_to_xlsx",
    "newman_analyzer",
    "output_formatter",
    "telemetry_correlator",
    "welcome_page",
]
