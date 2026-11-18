# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub — Enterprise AI Agent Quality Engineering & Automated Testing Tooling Suite.
========================================================================================
Author: Thế Vị (@TeeVee98)
Repository: https://github.com/TeeVee98/Synapse-Hub
License: MIT

Domain Packages:
- tools.core: Execution engines, 10 DoD Quality Gates, setup, CLI, AST maps.
- tools.lint: Static code defect, encoding, author integrity, and AI doc sentinels.
- tools.heal: Locator healing, episodic Reflexion memory, and agentless patching.
- tools.context: AI Context engineering, token economy, log distillation, AST slicing.
- tools.security: OWASP ASVS auditing, CVSS scoring, DAST, and compliance guards.
- tools.api: OpenAPI matrix generation, contract drift, traffic recording, and mocking.
- tools.perf: Flakiness detection, JMeter plans, BFCL benchmarks, and matrix sharding.
- tools.report: HTML dashboards, spreadsheets, telemetry correlation, and metrics.
- tools.design: Gherkin suites, pairwise generation, and test story analysis.
- tools.transpiler: Universal Intermediate Representation (IR) cross-language compiler.
- tools.orchestration: Multi-Agent FSM enforcers, event stream, and memory systems.
- tools.mcp: Model Context Protocol servers (core QA, Excel, and Word manipulation).
- tools.contrib: Specialized auxiliary extension tools and integrations.
"""

__version__ = "4.5.0"
__author__ = "Thế Vị (@TeeVee98)"

import os
import sys

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

# Expose domain packages
from tools import (  # noqa: F401
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

__all__ = [
    # Domain Subpackages
    "core",
    "lint",
    "heal",
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
    # Core CLI & Sentinel Exports
    "verify_all",
    "infer_linter",
    "micro_mutator",
    "setup_project",
    "analyze_project",
    "distill_log",
    "repo_map",
    "cache_resolver",
    "check_env",
    "api_fuzzer",
    "test_impact",
    "watch_mode",
    "author_integrity",
    "session_vault",
    "visual_som_helper",
    "live_visual_healer",
]
