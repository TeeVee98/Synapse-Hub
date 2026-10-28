#!/usr/bin/env python3
"""
Enterprise Agent-QA CLI Entrypoint
----------------------------------
Provides a centralized command-line interface for the agent-skills ecosystem.
Dispatches commands to underlying specialized tools in tools/.
"""

import os
import sys
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))


def cmd_version(args):
    manifest_path = os.path.join(REPO_ROOT, "skills_manifest.json")
    version = "2.0.0"
    if os.path.exists(manifest_path):
        try:
            import json
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                version = data.get("version", version)
        except Exception:
            pass
    print(f"Agent-QA Hub CLI v{version}")
    print("Catalog: 30 Standardized Skills | 6 Subagent Swarm Profiles")


def cmd_verify(args):
    from verify_all import main as verify_main
    sys.exit(verify_main())


def cmd_lint(args):
    from infer_linter import main as lint_main
    sys.exit(lint_main())


def cmd_heal(args):
    from cache_resolver import main as heal_main
    sys.exit(heal_main())


def cmd_distill(args):
    from distill_log import main as distill_main
    sys.exit(distill_main())


def cmd_impact(args):
    from test_impact import main as impact_main
    sys.exit(impact_main())


def cmd_canary(args):
    from agent_canary import main as canary_main
    sys.exit(canary_main())


def main():
    parser = argparse.ArgumentParser(
        prog="agent-qa",
        description="Enterprise AI Agent Quality Engineering & Test Automation Hub CLI"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # version
    p_ver = subparsers.add_parser("version", help="Show Hub version and catalog metadata")
    p_ver.set_defaults(func=cmd_version)

    # verify
    p_verify = subparsers.add_parser("verify", help="Execute 7 Quality Gates DoD Verification")
    p_verify.set_defaults(func=cmd_verify)

    # lint
    p_lint = subparsers.add_parser("lint", help="Run AST Fake-Pass & Zero-Assertion Sentinel")
    p_lint.set_defaults(func=cmd_lint)

    # heal
    p_heal = subparsers.add_parser("heal", help="Query or initialize semantic error memory cache")
    p_heal.set_defaults(func=cmd_heal)

    # distill
    p_distill = subparsers.add_parser("distill", help="Distill and filter verbose CLI logs by 95 percent")
    p_distill.set_defaults(func=cmd_distill)

    # impact
    p_impact = subparsers.add_parser("impact", help="Analyze code change impact using AST Knowledge Graph")
    p_impact.set_defaults(func=cmd_impact)

    # canary
    p_canary = subparsers.add_parser("canary", help="Run autonomous canary resilience benchmark")
    p_canary.set_defaults(func=cmd_canary)

    args, unknown = parser.parse_known_args()
    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    # Dispatch subcommand
    args.func(args)


if __name__ == "__main__":
    main()
