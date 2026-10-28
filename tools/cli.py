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

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, SCRIPT_DIR)


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
    manifest_skills = 34
    if os.path.exists(manifest_path):
        try:
            import json
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_skills = json.load(f).get("totalSkills", 34)
        except Exception:
            pass
    print(f"Catalog: {manifest_skills} Standardized Skills | 6 Subagent Swarm Profiles")


def cmd_verify(args):
    from verify_all import main as verify_main
    sys.argv = [sys.argv[0]] + (sys.argv[2:] if len(sys.argv) > 2 else [])
    sys.exit(verify_main())


def cmd_lint(args):
    from infer_linter import main as lint_main
    sys.argv = [sys.argv[0]] + (sys.argv[2:] if len(sys.argv) > 2 else [])
    sys.exit(lint_main())


def cmd_heal(args):
    from cache_resolver import main as heal_main
    sys.argv = [sys.argv[0]] + (sys.argv[2:] if len(sys.argv) > 2 else [])
    sys.exit(heal_main())


def cmd_distill(args):
    from distill_log import main as distill_main
    sys.argv = [sys.argv[0]] + (sys.argv[2:] if len(sys.argv) > 2 else [])
    sys.exit(distill_main())


def cmd_impact(args):
    from test_impact import main as impact_main
    sys.argv = [sys.argv[0]] + (sys.argv[2:] if len(sys.argv) > 2 else [])
    sys.exit(impact_main())


def cmd_clean(args):
    """Cleans temporary build files, __pycache__, and compiled bytecode across the repository."""
    import shutil
    removed_count = 0
    print("🧹 Cleaning temporary build artifacts and bytecode caches...")
    for root, dirs, files in os.walk(REPO_ROOT):
        for d in list(dirs):
            if d == "__pycache__":
                full_dir = os.path.join(root, d)
                try:
                    shutil.rmtree(full_dir)
                    removed_count += 1
                    dirs.remove(d)
                except Exception as e:
                    print(f"⚠️  Could not remove {full_dir}: {e}")
        for f in files:
            if f.endswith((".pyc", ".pyo", ".tmp")):
                try:
                    os.remove(os.path.join(root, f))
                    removed_count += 1
                except Exception:
                    pass
    print(f"✅ Cleanup finished: {removed_count} build artifacts and caches removed.")


def cmd_flaky(args):
    from flaky_detector import main as flaky_main
    sys.argv = [sys.argv[0]] + (sys.argv[2:] if len(sys.argv) > 2 else [])
    sys.exit(flaky_main())


def cmd_canary(args):
    from agent_canary import main as canary_main
    sys.argv = [sys.argv[0]] + (sys.argv[2:] if len(sys.argv) > 2 else [])
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
    p_heal = subparsers.add_parser("heal", help="Query, learn, or record-failed into semantic memory cache")
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

    # clean
    p_clean = subparsers.add_parser("clean", help="Clean build artifacts, __pycache__, and bytecode")
    p_clean.set_defaults(func=cmd_clean)

    # flaky
    p_flaky = subparsers.add_parser("flaky", help="Detect flaky tests and manage quarantine lifecycle")
    p_flaky.set_defaults(func=cmd_flaky)

    args, unknown = parser.parse_known_args()
    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    # Dispatch subcommand
    args.func(args)


if __name__ == "__main__":
    main()
