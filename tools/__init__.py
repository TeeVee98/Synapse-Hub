# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub — Enterprise AI Agent Quality Engineering & Automated Testing Tooling Suite.
========================================================================================
Author: Thế Vị (@TeeVee98)
Repository: https://github.com/TeeVee98/Synapse-Hub
License: MIT

Dynamically discovers all domain subpackages under `tools/` (core, lint, heal,
context, security, api, perf, design, report, transpiler, orchestration, mcp,
contrib, manual, reasoning, runtime, alm, ai, dashboard, catalogs) without
requiring a stale hardcoded tool map.
"""

__version__ = "4.9.0"
__author__ = "Thế Vị (@TeeVee98)"

import os
import sys
import importlib
import importlib.util
from importlib.abc import MetaPathFinder, Loader
from typing import Dict, List

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))

# Priority-ordered domain packages (all 20 subpackages discovered dynamically)
_PREFERRED_DOMAIN_ORDER = [
    "core", "lint", "heal", "context", "security", "api", "perf", "design",
    "report", "transpiler", "orchestration", "mcp", "contrib", "manual",
    "reasoning", "runtime", "alm", "ai", "dashboard", "catalogs",
]


def _discover_domains_and_tools() -> tuple[List[str], Dict[str, str]]:
    """Dynamically discovers all domain subpackages and maps bare tool stems to their domain."""
    if not os.path.isdir(_TOOLS_DIR):
        return [], {}
    discovered_dirs = {
        entry for entry in os.listdir(_TOOLS_DIR)
        if os.path.isdir(os.path.join(_TOOLS_DIR, entry))
        and not entry.startswith(("_", "."))
        and entry not in ("templates", "benchmarks-tests")
    }
    domains = [d for d in _PREFERRED_DOMAIN_ORDER if d in discovered_dirs]
    for extra in sorted(discovered_dirs - set(domains)):
        domains.append(extra)

    tool_map: Dict[str, str] = {}
    for domain in domains:
        domain_dir = os.path.join(_TOOLS_DIR, domain)
        try:
            for fname in sorted(os.listdir(domain_dir)):
                if fname.endswith(".py") and not fname.startswith("_"):
                    stem = fname[:-3]
                    if stem not in tool_map:
                        tool_map[stem] = domain
        except OSError:
            continue
    return domains, tool_map


_DOMAINS, _TOOL_DOMAIN_MAP = _discover_domains_and_tools()

# Bootstrap all discovered domain packages into sys.path for bare intra-tool imports
for _d in _DOMAINS:
    _dp = os.path.join(_TOOLS_DIR, _d)
    if _dp not in sys.path:
        sys.path.insert(0, _dp)

if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)


def resolve_tool_path(tool_name: str, domain: str = "") -> str:
    """Resolves the absolute filesystem path of a tool script across all domain subpackages."""
    clean_name = tool_name[:-3] if tool_name.endswith(".py") else tool_name
    d = domain or _TOOL_DOMAIN_MAP.get(clean_name, "")
    if d:
        candidate = os.path.join(_TOOLS_DIR, d, f"{clean_name}.py")
        if os.path.isfile(candidate):
            return candidate
    for dom in _DOMAINS:
        candidate = os.path.join(_TOOLS_DIR, dom, f"{clean_name}.py")
        if os.path.isfile(candidate):
            _TOOL_DOMAIN_MAP[clean_name] = dom
            return candidate
    p_direct = os.path.join(_TOOLS_DIR, f"{clean_name}.py")
    if os.path.exists(p_direct):
        return p_direct
    return os.path.join(_TOOLS_DIR, d, f"{clean_name}.py") if d else p_direct


class _AliasLoader(Loader):
    def __init__(self, target_module):
        self.target_module = target_module

    def create_module(self, spec):
        return self.target_module

    def exec_module(self, module):
        pass


class _ToolsDomainRedirectFinder(MetaPathFinder):
    """Dynamic MetaPathFinder providing transparent redirection from tools.<tool> to tools.<domain>.<tool>."""
    def find_spec(self, fullname, path, target=None):
        if fullname.startswith("tools."):
            parts = fullname.split(".")
            if len(parts) == 2:
                tool_name = parts[1]
                if tool_name in _TOOL_DOMAIN_MAP and tool_name not in _DOMAINS:
                    domain = _TOOL_DOMAIN_MAP[tool_name]
                    target_name = f"tools.{domain}.{tool_name}"
                    try:
                        target_module = importlib.import_module(target_name)
                        tools_mod = sys.modules.get("tools")
                        if tools_mod is not None:
                            setattr(tools_mod, tool_name, target_module)
                        return importlib.util.spec_from_loader(fullname, _AliasLoader(target_module))
                    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                        return None
        return None


if not any(isinstance(finder, _ToolsDomainRedirectFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, _ToolsDomainRedirectFinder())


def __getattr__(name: str):
    """Dynamic attribute resolver for bare tools.<name> access."""
    if name in _TOOL_DOMAIN_MAP:
        domain = _TOOL_DOMAIN_MAP[name]
        mod = importlib.import_module(f"tools.{domain}.{name}")
        globals()[name] = mod
        return mod
    if name in _DOMAINS:
        mod = importlib.import_module(f"tools.{name}")
        globals()[name] = mod
        return mod
    raise AttributeError(f"module 'tools' has no attribute '{name}'")


def __dir__():
    return sorted(list(globals().keys()) + list(_TOOL_DOMAIN_MAP.keys()) + _DOMAINS)


# Expose core domain packages eagerly for backward compatibility
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

__all__ = _DOMAINS + list(_TOOL_DOMAIN_MAP.keys()) + ["resolve_tool_path"]
