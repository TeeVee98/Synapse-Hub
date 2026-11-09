"""
Synapse Hub — Enterprise AI Agent Quality Engineering & Automated Testing Tooling Suite.
========================================================================================
Author: Thế Vị (@TeeVee998)
Repository: https://github.com/TeeVee998/Synapse-Hub
License: MIT

Domain Packages:
- tools.core: Execution engines, 10 DoD Quality Gates, setup, CLI, AST maps.
- tools.lint: Static code defect, encoding, author integrity, and AI doc sentinels.
- tools.report: HTML dashboards, spreadsheets, telemetry correlation, and metrics.
- tools.heal: Locator healing, episodic Reflexion memory, and agentless patching.
- tools.perf: Flakiness detection, JMeter plans, BFCL benchmarks, and matrix sharding.
- tools.mcp: Model Context Protocol servers (core QA and Excel manipulation).
"""

__version__ = "3.7.1"
__author__ = "Thế Vị (@TeeVee998)"

# Expose domain packages
from tools import core, heal, lint, mcp, perf, report  # noqa: F401

__all__ = [
    "core",
    "heal",
    "lint",
    "mcp",
    "perf",
    "report",
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
]
