# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub — Enterprise AI Agent Quality Engineering Operating System
======================================================================
Official High-Level Python API and Modular SDK for Synapse Hub.

Author: Thế Vị (@TeeVee98)
Repository: https://github.com/TeeVee98/Synapse-Hub
License: MIT
"""

__version__ = "4.7.2"
__author__ = "Thế Vị (@TeeVee98)"

# Expose domain packages via high-level namespaces
from tools import (
    api,
    context,
    contrib,
    core,
    design,
    heal,
    lint,
    mcp,
    orchestration,
    perf,
    report,
    security,
    transpiler,
)

# Semantic Aliases for Enterprise SDK
sentinels = lint
healing = heal

# Enterprise Core Engines
try:
    from tools.core.session_vault import SessionVault
except ImportError:
    SessionVault = None

try:
    from tools.heal.visual_som_helper import VisualSoMHelper
except ImportError:
    VisualSoMHelper = None

try:
    from tools.heal.live_visual_healer import LiveVisualHealer
except ImportError:
    LiveVisualHealer = None

__all__ = [
    "__version__",
    "__author__",
    "SessionVault",
    "VisualSoMHelper",
    "LiveVisualHealer",
    "core",
    "lint",
    "sentinels",
    "heal",
    "healing",
    "context",
    "security",
    "api",
    "perf",
    "report",
    "design",
    "transpiler",
    "orchestration",
    "mcp",
    "contrib",
]
