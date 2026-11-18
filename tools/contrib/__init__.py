# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub — Contrib & Auxiliary Extension Tools (tools.contrib)
-----------------------------------------------------------------
Domain package grouping specialized, auxiliary, or domain-specific tools
that extend Synapse Hub beyond its core test automation kernel.
"""

import os
import sys

# Ensure repository root and tools directory are in sys.path
_CONTRIB_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_CONTRIB_DIR)
_REPO_ROOT = os.path.dirname(_TOOLS_DIR)
for _p in (_REPO_ROOT, _TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.contrib import (
    cldr_l10n_verifier,
    dashboard_generator,
    diagram_architect,
    etl_data_reconciler,
    export_postman_collection,
    generate_jmx_plan,
    generate_tc_from_story,
    interview_story,
    jira_sync,
    md_to_xlsx,
    openxml_guard,
    payment_interop_simulator,
    slide_deck_exporter,
    template_excel_exporter,
    tmmi_auditor,
    tms_sync_bridge,
    ui_server,
    vpat_exporter,
    wcag_audit,
    welcome_page,
)

__all__ = [
    "cldr_l10n_verifier",
    "dashboard_generator",
    "diagram_architect",
    "etl_data_reconciler",
    "export_postman_collection",
    "generate_jmx_plan",
    "generate_tc_from_story",
    "interview_story",
    "jira_sync",
    "md_to_xlsx",
    "openxml_guard",
    "payment_interop_simulator",
    "slide_deck_exporter",
    "template_excel_exporter",
    "tmmi_auditor",
    "tms_sync_bridge",
    "ui_server",
    "vpat_exporter",
    "wcag_audit",
    "welcome_page",
]
