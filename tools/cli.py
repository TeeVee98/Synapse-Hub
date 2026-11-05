#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Enterprise Agent-QA CLI Entrypoint
----------------------------------
Provides a centralized command-line interface for the agent-skills ecosystem.
Dispatches commands to underlying specialized tools in tools/.
"""

import os
import sys
import json
import re
import difflib
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

# ANSI Color formatting
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def cmd_version(args):
    """Displays the current hub version, skill catalog count, and license information."""
    manifest_path = os.path.join(REPO_ROOT, "skills_manifest.json")
    version = "3.1.1"
    if os.path.exists(manifest_path):
        try:
            import json
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                version = data.get("version", version)
        except (OSError, json.JSONDecodeError):
            data = {}
    print(f"Agent-QA Hub CLI v{version}")
    manifest_skills = 42
    if os.path.exists(manifest_path):
        try:
            import json
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_skills = json.load(f).get("totalSkills", 42)
        except (OSError, json.JSONDecodeError):
            manifest_skills = 42
    print(f"Catalog: {manifest_skills} Standardized Skills | 6 Subagent Swarm Profiles")
    print("Created by: Thế Vị (@TeeVee998) <https://github.com/TeeVee998/Synapse-Hub>")
    print("License   : MIT (Attribution Required)")


def cmd_verify_author(args):
    """Validates author attribution and MIT provenance integrity across the repository."""
    from author_integrity import verify_author_attribution, get_canonical_watermark, enforce_author_attribution
    valid, violations = verify_author_attribution()
    if valid:
        print(f"✅ Author attribution & provenance verified: {get_canonical_watermark()}")
        sys.exit(0)
    else:
        enforce_author_attribution(strict=True)


def _forward_subcommand_args(args_or_name=None) -> list:
    """Safely extracts and forwards arguments intended for the underlying subcommand tool."""
    subcmd = None
    if isinstance(args_or_name, str):
        subcmd = args_or_name
    elif hasattr(args_or_name, "subcommand"):
        subcmd = args_or_name.subcommand

    if subcmd and subcmd in sys.argv:
        idx = sys.argv.index(subcmd)
        return [sys.argv[0]] + sys.argv[idx + 1:]
    return [sys.argv[0]] + (sys.argv[2:] if len(sys.argv) > 2 else [])


def cmd_verify(args):
    """Executes the 10 Quality Gates Definition of Done (DoD) verification suite."""
    from verify_all import main as verify_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(verify_main())


def cmd_lint(args):
    """Runs the Meta Infer-style AST Fake-Pass, zero-assertion, and hard sleep scanner."""
    from infer_linter import main as lint_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(lint_main())


def cmd_heal(args):
    """Interacts with the central episodic self-healing solution memory cache."""
    from cache_resolver import main as heal_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(heal_main())


def cmd_distill(args):
    """Distills and filters high-volume CI/CD test execution logs by ~95%."""
    from distill_log import main as distill_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(distill_main())


def cmd_impact(args):
    """Analyzes code change impact and scopes affected tests using AST graph mapping."""
    from test_impact import main as impact_main
    sys.argv = _forward_subcommand_args(args)
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
                except OSError as err:
                    getattr(args, "verbose", False) and print(f"Notice: Could not remove {f}: {err}")
    print(f"✅ Cleanup finished: {removed_count} build artifacts and caches removed.")


def cmd_flaky(args):
    """Detects non-deterministic flaky tests and manages quarantine governance."""
    from flaky_detector import main as flaky_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(flaky_main())


def cmd_canary(args):
    """Executes the autonomous canary self-healing benchmark across 8 failure vectors."""
    from agent_canary import main as canary_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(canary_main())


def cmd_analyze(args):
    """Runs comprehensive 5-in-1 project health and AST architecture analysis."""
    from analyze_project import main as analyze_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(analyze_main())


def cmd_setup(args):
    """Bootstraps a target test repository with AI guide, Git hook, and AST map."""
    from setup_project import main as setup_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(setup_main())


def cmd_doctor(args):
    """Runs a 1-click diagnostic check of system environment, tools, and dependencies."""
    from check_env import main as check_env_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(check_env_main())


def cmd_uninstall(args):
    """Reverts and cleans configuration files and Git hooks installed by setup in target project."""
    from setup_project import uninstall_setup, resolve_target_repo
    target = getattr(args, "target", None)
    target_repo = resolve_target_repo(cli_target=target)
    sys.exit(uninstall_setup(target_repo))


def cmd_auto_heal(args):
    """Executes closed-loop test failure diagnosis and creates a locator healing plan."""
    from auto_heal import main as auto_heal_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(auto_heal_main())


def cmd_safety_check(args):
    """Validates actions against the Action Safety Firewall to prevent destructive operations."""
    from safety_firewall import main as safety_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(safety_main())


def cmd_contract_drift(args):
    """Detects breaking API changes across OpenAPI / Swagger contract specifications."""
    from api_drift_sentinel import main as drift_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(drift_main())


def cmd_mcp_serve(args):
    """Starts the JSON-RPC 2.0 stdio Model Context Protocol (MCP) server."""
    from mcp_server import run_stdio_server
    run_stdio_server()


def cmd_mutate(args):
    """Injects syntactic micro-mutations to measure test assertion sensitivity."""
    from micro_mutator import main as mut_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(mut_main())


def cmd_heal_pr(args):
    """Calculates self-healing confidence and generates an automated Git pull request draft."""
    from heal_pr_automator import main as pr_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(pr_main())


def cmd_shard(args):
    """Balances parallel CI/CD test execution using duration-balanced bin-packing."""
    from matrix_sharder import main as shard_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(shard_main())


def cmd_transpile(args):
    from omni_transpiler import transpile_file
    res = transpile_file(args.source, args.to, args.out)
    print(f"✅ Transpiled '{args.source}' -> {args.to} ({len(res)} files):")
    for p, code in res.items():
        print(f"  • {p} ({len(code.splitlines())} lines)")
        if not args.out:
            print("---")
            print(code)
            print("---")


def cmd_omni_scan(args):
    from omni_transpiler import scan_repository
    inv = scan_repository(args.path)
    if getattr(args, "json", False):
        print(json.dumps(inv, indent=2))
    else:
        print("======================================================================")
        print("  OMNI-AUTOMATION POLYGLOT REPOSITORY INVENTORY (0-TOKEN AST SCAN)")
        print("======================================================================")
        print(f"📁 Target Directory   : {inv['repository']}")
        print(f"📄 Scanned Files      : {inv['total_files_scanned']}")
        print(f"🌐 Languages Detected : {inv['languages']}")
        print(f"⚡ Frameworks         : {inv['frameworks']}")
        print(f"🏛️ Page Classes Found : {len(inv['pages'])}")
        print(f"🎯 Total Locators     : {inv['total_locators']}")
        print(f"⚙️ Action Methods     : {inv['total_methods']}")
        print(f"🧪 Test Cases Found   : {len(inv['test_cases'])}")
        print("======================================================================")


def cmd_report_bug(args):
    from bug_reporter import main as bug_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(bug_main())


def cmd_mock_shield(args):
    from network_mock_shield import main as mock_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(mock_main())


def cmd_visual_mask(args):
    from smart_visual_masker import main as mask_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(mask_main())


def cmd_review_spec(args):
    from goldfish_review import main as review_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(review_main())


def cmd_drift_check(args):
    from spec_drift_sentinel import main as drift_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(drift_main())


def cmd_ci_hook(args):
    from ci_healing_hook import main as hook_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(hook_main())


def cmd_migrate(args):
    """Migrates an entire legacy test suite (Katalon, Cypress, Selenium) to modern target (Playwright TS)."""
    from omni_transpiler import transpile_file
    src = getattr(args, "src", None)
    dest = getattr(args, "dest", None) or "playwright_suite"
    target = getattr(args, "target", "playwright-ts")
    if not src:
        print("❌ Error: --src parameter is required for migrate.")
        sys.exit(1)

    if os.path.isdir(src):
        migrated_count = 0
        test_exts = {".groovy", ".java", ".js", ".ts", ".py"}
        for root, _, files in os.walk(src):
            for f in files:
                if os.path.splitext(f)[1].lower() in test_exts:
                    file_path = os.path.join(root, f)
                    try:
                        transpile_file(file_path, target, output_dir=dest, hermetic=True)
                        migrated_count += 1
                    except (OSError, ValueError, SyntaxError) as e:
                        print(f"  ⚠️ Skipping {f}: {e}")
        print(f"✅ [MIGRATION COMPLETE] {migrated_count} test files converted to {target} in '{dest}'.")
    else:
        transpile_file(src, target, output_dir=dest, hermetic=True)
        print(f"✅ [MIGRATION COMPLETE] '{src}' -> {target} in '{dest}'.")


def cmd_decouple_config(args):
    from config_decoupler import main as decouple_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(decouple_main())


def cmd_fuzz_api(args):
    from api_fuzzer import main as fuzz_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(fuzz_main())


def cmd_som(args):
    from visual_som_helper import main as som_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(som_main())


def cmd_gherkin(args):
    from gherkin_suite import main as gherkin_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(gherkin_main())


def cmd_export_postman(args):
    from export_postman_collection import main as postman_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(postman_main())


def cmd_generate_jmx(args):
    from generate_jmx_plan import main as jmx_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(jmx_main())


def cmd_skillspector(args):
    from skillspector import main as skillspector_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(skillspector_main())


def cmd_analyze_jtl(args):
    from jtl_analyzer import main as jtl_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(jtl_main())


def cmd_export_excel(args):
    from md_to_xlsx import main as excel_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(excel_main())


def cmd_correlate_telemetry(args):
    from telemetry_correlator import main as telem_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(telem_main())


def cmd_analyze_newman(args):
    from newman_analyzer import main as newman_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(newman_main())


def cmd_update(args):
    import update_sentinel
    if getattr(args, "check", False):
        has_update, cur, rem = update_sentinel.check_for_updates(force=True, notify=False)
        print(f"Current Hub Version : v{cur}")
        print(f"Latest Upstream     : v{rem if rem else 'Unknown'}")
        if has_update:
            print(f"⚠️ An update is available: v{cur} -> v{rem}. Run 'agent-qa update' to upgrade.")
            sys.exit(1)
        else:
            print("✅ Synapse-Hub is up to date.")
            sys.exit(0)
    update_sentinel.perform_update()


def cmd_tokens(args):
    import count_tokens
    sys.argv = _forward_subcommand_args(args)
    count_tokens.main()


def cmd_dashboard(args):
    import dashboard_generator
    sys.argv = _forward_subcommand_args(args)
    dashboard_generator.main()


def cmd_watch(args):
    import watch_mode
    sys.argv = _forward_subcommand_args(args)
    watch_mode.main()


def cmd_welcome(args):
    import welcome_page
    sys.argv = _forward_subcommand_args(args)
    welcome_page.main()


def cmd_wcag_audit(args):
    from wcag_audit import main as wcag_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(wcag_main())


def cmd_lookup_tc(args):
    from lookup_tc import main as tc_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(tc_main())


def cmd_lookup_xpath(args):
    from lookup_xpath import main as xpath_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(xpath_main())


def cmd_trace_data_flow(args):
    from trace_data_flow import main as tdf_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(tdf_main())


def cmd_generate_tc(args):
    from generate_tc_from_story import main as gen_tc_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(gen_tc_main())


def cmd_pinpoint_failure(args):
    from pinpoint_failure import main as pp_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(pp_main())


def cmd_sync_rules(args):
    from sync_agent_rules import main as sync_rules_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(sync_rules_main())


def cmd_api_matrix(args):
    from generate_api_matrix import main as api_matrix_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(api_matrix_main())


def cmd_canvas_diff(args):
    from visual_diff_canvas import main as canvas_diff_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(canvas_diff_main())


def cmd_validate_groovy(args):
    from validate_groovy_scripts import main as groovy_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(groovy_main())


def cmd_check_version(args):
    from check_version_sync import main as ver_sync_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(ver_sync_main())


def cmd_mcp_excel(args):
    from mcp_excel_server import main as mcp_excel_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(mcp_excel_main())


def cmd_debt(args):
    """Harvests shortcut: and deliberate debt comments into a tracked technical debt ledger."""
    from debt_harvester import main as debt_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(debt_main())


def cmd_review(args):
    """Senior developer diff & code review checking bugs, security, scale, missing tests, and bloat."""
    from senior_code_review import main as review_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(review_main())


def cmd_release(args):
    """1-Click atomic release: bumps version across all files, runs 10 Quality Gates, tags & pushes to trigger NPM Trusted Publishing."""
    from bump_version import main as bump_main
    forwarded = _forward_subcommand_args(args)
    if "--no-push" not in forwarded and "--push" not in forwarded:
        forwarded.append("--push")
    if "--commit" not in forwarded and "--no-commit" not in forwarded:
        forwarded.append("--commit")
    sys.argv = forwarded
    sys.exit(bump_main())


def _hub_version():
    manifest_path = os.path.join(REPO_ROOT, "skills_manifest.json")
    version = "3.1.1"
    if os.path.exists(manifest_path):
        try:
            import json
            with open(manifest_path, "r", encoding="utf-8") as f:
                version = json.load(f).get("version", version)
        except (OSError, json.JSONDecodeError):
            version = "3.1.1"
    return version


class SynapseArgumentParser(argparse.ArgumentParser):
    """Enhanced ArgumentParser providing fuzzy Did-You-Mean suggestions on command typos."""
    def error(self, message):
        m = re.search(r"invalid choice: '([^']+)'", message)
        if m:
            bad_choice = m.group(1)
            choices = []
            for action in self._actions:
                if isinstance(action, argparse._SubParsersAction):
                    choices = list(action.choices.keys())
                    break
            matches = difflib.get_close_matches(bad_choice, choices, n=3, cutoff=0.4)
            sys.stderr.write(f"\n{BOLD}{RED}❌ Error: Lệnh '{bad_choice}' không tồn tại trong Synapse-Hub.{RESET}\n")
            if matches:
                suggestions = ", ".join(f"{BOLD}{GREEN}{c}{RESET}" for c in matches)
                sys.stderr.write(f"💡 Có phải ý bạn là: {suggestions} ?\n\n")
                sys.stderr.write(f"👉 Thử chạy: {BOLD}agent-qa {matches[0]} --help{RESET}\n\n")
            else:
                sys.stderr.write(f"👉 Gõ {BOLD}agent-qa --help{RESET} để xem danh sách tất cả các lệnh khả dụng.\n\n")
            sys.exit(2)
        super().error(message)


def _register_core_and_setup_commands(subparsers):
    """Registers core environment, setup, and informational subcommands."""
    # version
    p_ver = subparsers.add_parser("version", help="Show Hub version and catalog metadata")
    p_ver.set_defaults(func=cmd_version)

    # setup
    p_setup = subparsers.add_parser("setup", help="Autonomous 1-click bootstrap of target project (AI guide, Git hook, AST map)")
    p_setup.set_defaults(func=cmd_setup)

    # doctor
    p_doctor = subparsers.add_parser("doctor", description="Enterprise Environment Diagnostic Tool", help="Run 1-click diagnostic check of system environment, tools, and dependencies")
    p_doctor.add_argument("target", nargs="?", default=None, help="Target repository path to diagnose")
    p_doctor.add_argument("--repo", "--path", dest="repo_path", default=None, help="Target repository path")
    p_doctor.add_argument("--insecure", action="store_true", help="Allow unverified SSL certificates during connectivity checks")
    p_doctor.set_defaults(func=cmd_doctor)

    # uninstall
    p_uninstall = subparsers.add_parser("uninstall", help="Revert and remove files installed by setup in target project")
    p_uninstall.add_argument("target", nargs="?", default=None, help="Target repository path to revert")
    p_uninstall.set_defaults(func=cmd_uninstall)

    # welcome
    p_welcome = subparsers.add_parser("welcome", description="Interactive Visual Landing Page", help="Launch interactive visual landing page introducing Synapse Hub")
    p_welcome.add_argument("target", nargs="?", default=None, help="Target repository directory (default: current directory)")
    p_welcome.add_argument("--output", "-o", default=None, help="Output HTML file path (default: reports/WELCOME.html)")
    p_welcome.add_argument("--lang", choices=["vi", "en"], default="vi", help="Default initial language (default: vi = Vietnamese)")
    p_welcome.add_argument("--no-browser", action="store_true", help="Do not open the browser after generating the page")
    p_welcome.add_argument("--open", action="store_true", help="Explicitly open the browser")
    p_welcome.add_argument("--first-run", action="store_true", help="Only open if running for the first time (e.g. npm install or first pull)")
    p_welcome.set_defaults(func=cmd_welcome)

    # dashboard
    p_dashboard = subparsers.add_parser("dashboard", help="Generate standalone one-page executive HTML dashboard (zero CDN deps)")
    p_dashboard.add_argument("target", nargs="?", default=None, help="Target repository directory (default: current or Hub)")
    p_dashboard.add_argument("--output", "-o", help="Output HTML file path (default: <target>/reports/PROJECT_DASHBOARD.html)")
    p_dashboard.add_argument("--open", action="store_true", help="Automatically open generated dashboard in default browser")
    p_dashboard.add_argument("--json", action="store_true", help="Print summary JSON to stdout")
    p_dashboard.add_argument("--lang", choices=["vi", "en"], default="vi", help="Default display language (vi: Tiếng Việt, en: English, default: vi)")
    p_dashboard.set_defaults(func=cmd_dashboard)

    # clean
    p_clean = subparsers.add_parser("clean", help="Clean build artifacts, __pycache__, and bytecode")
    p_clean.set_defaults(func=cmd_clean)

    # update
    p_update = subparsers.add_parser("update", help="1-Click update Synapse-Hub to latest version from GitHub/NPM")
    p_update.add_argument("--check", action="store_true", help="Check for available updates without applying")
    p_update.set_defaults(func=cmd_update)

    # check-version
    p_ver_sync = subparsers.add_parser("check-version", help="Verify universal version synchronization across all files")
    p_ver_sync.add_argument("--expected-version", "-e", help="Expected version string (e.g. from git tag)", default=None)
    p_ver_sync.set_defaults(func=cmd_check_version)

    # sync-rules
    p_sync_rules = subparsers.add_parser("sync-rules", help="Synchronize AGENTS.md single source of truth across all AI IDE bridges")
    p_sync_rules.add_argument("--check", action="store_true", help="Verify all AI bridges are in sync without writing")
    p_sync_rules.set_defaults(func=cmd_sync_rules)


def _register_testing_and_execution_commands(subparsers):
    """Registers automated testing, linting, healing, and mutation subcommands."""
    # verify
    p_verify = subparsers.add_parser("verify", help="Execute 10 Quality Gates DoD Verification")
    p_verify.set_defaults(func=cmd_verify)

    # lint
    p_lint = subparsers.add_parser("lint", help="Run AST Fake-Pass & Zero-Assertion Sentinel")
    p_lint.set_defaults(func=cmd_lint)

    # auto-heal
    p_auto_heal = subparsers.add_parser("auto-heal", help="Autonomous closed-loop test failure diagnosis and healing plan")
    p_auto_heal.set_defaults(func=cmd_auto_heal)

    # heal-pr
    p_heal_pr = subparsers.add_parser("heal-pr", help="Calculate self-healing confidence and generate Git PR draft")
    p_heal_pr.set_defaults(func=cmd_heal_pr)

    # heal (memory cache)
    p_heal = subparsers.add_parser("heal", help="Query, learn, or record-failed into semantic memory cache")
    p_heal.set_defaults(func=cmd_heal)

    # mutate
    p_mut = subparsers.add_parser("mutate", help="Inject syntactic micro-mutants to verify test assertion strength")
    p_mut.set_defaults(func=cmd_mutate)

    # shard
    p_shard = subparsers.add_parser("shard", help="Balance parallel CI/CD test execution using duration-balanced bin-packing")
    p_shard.set_defaults(func=cmd_shard)

    # flaky
    p_flaky = subparsers.add_parser("flaky", help="Detect flaky tests and manage quarantine lifecycle")
    p_flaky.set_defaults(func=cmd_flaky)

    # canary
    p_canary = subparsers.add_parser("canary", help="Run autonomous canary resilience benchmark")
    p_canary.set_defaults(func=cmd_canary)

    # watch
    p_watch = subparsers.add_parser("watch", help="Real-Time incremental watch mode & test engineering HUD (< 100ms feedback)")
    p_watch.add_argument("target", nargs="?", default=".", help="Directory to monitor (default: current directory)")
    p_watch.add_argument("--debounce", type=float, default=0.8, help="Debounce interval in seconds (default: 0.8)")
    p_watch.add_argument("--inactivity-timeout", type=float, default=0.0, help="Inactivity timeout in seconds to trigger stuck warning (default: 0 = disabled)")
    p_watch.add_argument("--once", action="store_true", help="Run incremental scan once on all files and exit")
    p_watch.set_defaults(func=cmd_watch)

    # pinpoint-failure
    p_pinpoint = subparsers.add_parser("pinpoint-failure", help="Parse JUnit XML and locate exact failing line in 0.1s")
    p_pinpoint.add_argument("report_file", nargs="?", default="", help="Path to JUnit XML test report")
    p_pinpoint.set_defaults(func=cmd_pinpoint_failure)

    # ci-hook
    p_ci = subparsers.add_parser("ci-hook", help="CI/CD Silent Self-Healing Pipeline Hook & Automated PR Generator")
    p_ci.set_defaults(func=cmd_ci_hook)


def _register_audit_and_inspection_commands(subparsers):
    """Registers security, architecture, and code quality inspection subcommands."""
    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Execute Comprehensive Project Health & AST Analysis")
    p_analyze.set_defaults(func=cmd_analyze)

    # debt
    p_debt = subparsers.add_parser("debt", aliases=["harvest-debt"], help="Harvest shortcut: comments into a tracked technical debt ledger")
    p_debt.add_argument("target", nargs="?", default=".", help="Directory to scan (default: current directory)")
    p_debt.add_argument("--keyword", "-k", default=None, help="Custom marker keyword (default: shortcut or ponytail)")
    p_debt.add_argument("--output", "-o", default=None, help="Save report to Markdown file")
    p_debt.add_argument("--json", action="store_true", help="Output results in JSON format")
    p_debt.set_defaults(func=cmd_debt)

    # review
    p_review = subparsers.add_parser("review", aliases=["code-review"], help="Senior developer quality & lean diff review (bugs, security, scale, tests, bloat)")
    p_review.add_argument("target_dir", nargs="?", default=".", help="Repository directory (default: current directory)")
    p_review.add_argument("--staged", action="store_true", help="Review staged git changes")
    p_review.add_argument("--branch", default=None, help="Review changes against a git branch or commit ref")
    p_review.add_argument("--json", action="store_true", help="Output results in JSON format")
    p_review.set_defaults(func=cmd_review)

    # safety-check
    p_safety = subparsers.add_parser("safety-check", help="Action Safety Firewall & Blast Radius Containment")
    p_safety.set_defaults(func=cmd_safety_check)

    # contract-drift
    p_drift = subparsers.add_parser("contract-drift", help="Detect breaking API changes across OpenAPI / Swagger specs")
    p_drift.set_defaults(func=cmd_contract_drift)

    # skillspector
    p_skillspector = subparsers.add_parser("skillspector", help="AI Agent Skill & MCP Security Sentinel (71 vectors, NVIDIA SkillSpector spec)")
    p_skillspector.add_argument("path", nargs="?", default=".", help="Skill directory or file to scan (default: current directory)")
    p_skillspector.add_argument("--format", choices=["terminal", "json", "markdown", "sarif"], default="terminal", help="Output format")
    p_skillspector.add_argument("--output", "-o", help="Write report to output file")
    p_skillspector.add_argument("--strict", action="store_true", help="Fail with non-zero exit code on HIGH/CRITICAL finding")
    p_skillspector.set_defaults(func=cmd_skillspector)

    # verify-author
    p_author = subparsers.add_parser("verify-author", help="Verify author attribution, provenance, and anti-tamper integrity")
    p_author.set_defaults(func=cmd_verify_author)

    # wcag-audit
    p_wcag = subparsers.add_parser("wcag-audit", help="Audit WCAG 2.2 accessibility conformance and contrast ratios")
    p_wcag.add_argument("target", nargs="?", default=".", help="Target HTML file or directory to audit")
    p_wcag.set_defaults(func=cmd_wcag_audit)

    # impact
    p_impact = subparsers.add_parser("impact", help="Analyze code change impact using AST Knowledge Graph")
    p_impact.set_defaults(func=cmd_impact)

    # review-spec
    p_review_spec = subparsers.add_parser("review-spec", help="Zero-context stress-test for specifications and user stories (Elephant-Goldfish Model)")
    p_review_spec.add_argument("spec_file", nargs="?", default="", help="Path to specification file (Markdown or Gherkin .feature, use '-' for stdin)")
    p_review_spec.add_argument("--stdin", action="store_true", help="Read specification from standard input (stdin)")
    p_review_spec.add_argument("--json", action="store_true", help="Output machine-readable JSON format")
    p_review_spec.add_argument("--min-score", type=int, default=80, help="Minimum readiness score threshold (default: 80)")
    p_review_spec.set_defaults(func=cmd_review_spec)

    # drift-check
    p_spec_drift = subparsers.add_parser("drift-check", help="Spec-to-Code Drift Sentinel checking Deficit & Scope Drift")
    p_spec_drift.add_argument("--spec", required=True, help="Path to specification file (Markdown or Gherkin .feature)")
    p_spec_drift.add_argument("--code", required=True, help="Path to test script or directory of test scripts")
    p_spec_drift.add_argument("--markdown", "-m", help="Path to export Markdown drift report (e.g. SPEC_DRIFT_REPORT.md)")
    p_spec_drift.add_argument("--json", action="store_true", help="Output machine-readable JSON format")
    p_spec_drift.set_defaults(func=cmd_drift_check)

    # trace-data-flow
    p_trace = subparsers.add_parser("trace-data-flow", help="Trace test data lifecycles to detect DB leaks and missing teardowns")
    p_trace.add_argument("target", nargs="?", default=".", help="Target test directory to inspect")
    p_trace.set_defaults(func=cmd_trace_data_flow)


def _register_platform_and_tools_commands(subparsers):
    """Registers protocol generators, converters, MCP servers, and utility subcommands."""
    # distill
    p_distill = subparsers.add_parser("distill", help="Distill and filter verbose CLI logs by 95 percent")
    p_distill.set_defaults(func=cmd_distill)

    # gherkin
    p_gherkin = subparsers.add_parser("gherkin", help="Compile Gherkin .feature files into test matrix, Universal IR and coverage-gap report (0-token)")
    p_gherkin.set_defaults(func=cmd_gherkin)

    # transpile
    p_trans = subparsers.add_parser("transpile", help="Transpile test files across languages and frameworks (0-token)")
    p_trans.add_argument("source", help="Source file path")
    p_trans.add_argument("--to", required=True, choices=["playwright-ts", "playwright-python", "selenium-java", "katalon-groovy", "cypress-js"], help="Target framework")
    p_trans.add_argument("--out", default=None, help="Output directory")
    p_trans.set_defaults(func=cmd_transpile)

    # omni-scan
    p_omni = subparsers.add_parser("omni-scan", help="Scan repository and build polyglot test inventory (0-token)")
    p_omni.add_argument("path", default=".", nargs="?", help="Directory to scan")
    p_omni.add_argument("--json", action="store_true", help="Output raw JSON")
    p_omni.set_defaults(func=cmd_omni_scan)

    # report-bug
    p_bug = subparsers.add_parser("report-bug", help="Auto-generate enterprise Jira/Markdown Bug Ticket with RCA")
    p_bug.set_defaults(func=cmd_report_bug)

    # mock-shield
    p_mock = subparsers.add_parser("mock-shield", help="Generate API Route Interception & Chaos Fault Injection Shield")
    p_mock.set_defaults(func=cmd_mock_shield)

    # visual-mask
    p_mask = subparsers.add_parser("visual-mask", help="Smart Visual Masking & Anti-Flake Animation Blocker")
    p_mask.set_defaults(func=cmd_visual_mask)

    # migrate
    p_migrate = subparsers.add_parser("migrate", help="Autonomous suite migration from legacy (Katalon/Cypress) to modern Playwright")
    p_migrate.add_argument("--src", required=True, help="Source legacy test suite file or directory")
    p_migrate.add_argument("--dest", default="playwright_suite", help="Destination directory for migrated code")
    p_migrate.add_argument("--target", default="playwright-ts", choices=["playwright-ts", "playwright-python", "selenium-java", "cypress-js"], help="Target framework")
    p_migrate.set_defaults(func=cmd_migrate)

    # decouple-config
    p_decouple = subparsers.add_parser("decouple-config", help="Decouple hardcoded URLs, credentials, and secrets into env profiles")
    p_decouple.add_argument("target", nargs="?", default=os.getcwd(), help="Target directory to scan")
    p_decouple.add_argument("--fix", action="store_true", help="Apply environment variable replacements in-place")
    p_decouple.add_argument("--out-dir", default=None, help="Output directory for config profiles")
    p_decouple.set_defaults(func=cmd_decouple_config)

    # fuzz-api
    p_fuzz = subparsers.add_parser("fuzz-api", help="Autonomous API Fuzzing & Chaos Breaker (bắn mutation payloads, bắt 500, DB leak, SLA breach)")
    p_fuzz.set_defaults(func=cmd_fuzz_api)

    # som
    p_som = subparsers.add_parser("som", help="Multimodal Vision Grounding & Set-of-Marks (SoM) for Canvas/GIS without DOM")
    p_som.set_defaults(func=cmd_som)

    # export-postman
    p_postman = subparsers.add_parser("export-postman", help="Export OpenAPI / Swagger / HAR to Postman Collection v2.1.0 with auto-asserts")
    p_postman.set_defaults(func=cmd_export_postman)

    # generate-jmx
    p_jmx = subparsers.add_parser("generate-jmx", help="Generate Apache JMeter 5.x Test Plan XML (.jmx) with JMeter 360 Enterprise Capabilities")
    p_jmx.set_defaults(func=cmd_generate_jmx)

    # analyze-jtl
    p_jtl = subparsers.add_parser("analyze-jtl", help="Analyze JMeter .jtl results, evaluate P90/P95/P99 SLA, and enforce CI/CD Quality Gate")
    p_jtl.set_defaults(func=cmd_analyze_jtl)

    # export-excel
    p_excel = subparsers.add_parser("export-excel", help="Convert Markdown Test Cases into Styled Enterprise Excel (.xlsx)")
    p_excel.add_argument("input", nargs="?", help="Path to input Markdown file (.md)")
    p_excel.add_argument("-o", "--output", help="Path to output Excel file (.xlsx)")
    p_excel.add_argument("--sheet-name", default="Test Cases", help="Worksheet title (default: Test Cases)")
    p_excel.set_defaults(func=cmd_export_excel)

    # correlate-telemetry
    p_telemetry = subparsers.add_parser("correlate-telemetry", help="Correlate Client-Side JMeter latency with Server-Side APM CPU/RAM/DB telemetry")
    p_telemetry.set_defaults(func=cmd_correlate_telemetry)

    # analyze-newman
    p_newman = subparsers.add_parser("analyze-newman", help="Analyze Postman / Newman test results, triage failed assertions, and enforce CI/CD Quality Gate")
    p_newman.set_defaults(func=cmd_analyze_newman)

    # tokens
    p_tokens = subparsers.add_parser("tokens", help="Audit token usage and estimated API cost across Antigravity, Cursor, and Claude Code")
    p_tokens.add_argument("--platform", "-p", choices=["auto", "antigravity", "cursor", "claude", "all"], default="auto", help="AI platform to audit (default: auto)")
    p_tokens.add_argument("--session", type=str, help="Specific session ID or index to audit")
    p_tokens.add_argument("--current", action="store_true", help="Audit current active conversation")
    p_tokens.add_argument("--last", action="store_true", help="Audit previous completed session (default)")
    p_tokens.add_argument("--last-task", action="store_true", help="Audit specifically the last turn of target session")
    p_tokens.add_argument("--turns", action="store_true", help="Show full turn-by-turn breakdown table")
    p_tokens.add_argument("--rolling", "--budget", action="store_true", dest="rolling", help="Show 5-hour and 7-day rolling window quota & remaining tokens")
    p_tokens.add_argument("--savings", action="store_true", help="Show Hub vs. Non-Hub token and cost savings comparison")
    p_tokens.add_argument("--header", action="store_true", help="Print Pre-Flight confirmation block lines")
    p_tokens.add_argument("--list", action="store_true", help="List recent conversations")
    p_tokens.add_argument("--pricing", choices=["gemini-flash", "gemini-pro", "claude-sonnet", "claude-opus", "gpt-4o", "gpt-4o-mini"], default=None, help="Model pricing basis (default: auto-detected)")
    p_tokens.add_argument("--json", action="store_true", help="Output machine-readable JSON format")
    p_tokens.add_argument("--file", type=str, help="Direct path to a transcript.jsonl file")
    p_tokens.set_defaults(func=cmd_tokens)

    # lookup-tc
    p_lookup_tc = subparsers.add_parser("lookup-tc", help="Search test cases by ID, tag, priority, or flow")
    p_lookup_tc.add_argument("query", nargs="?", default="", help="Query keyword or TC ID")
    p_lookup_tc.set_defaults(func=cmd_lookup_tc)

    # lookup-xpath
    p_lookup_xpath = subparsers.add_parser("lookup-xpath", help="Query cached resilient XPath & AOM locators")
    p_lookup_xpath.add_argument("query", nargs="?", default="", help="Element text, test-id, or locator label")
    p_lookup_xpath.set_defaults(func=cmd_lookup_xpath)

    # generate-tc
    p_gen_tc = subparsers.add_parser("generate-tc", help="Compile natural language user stories into Clean POM test cases")
    p_gen_tc.add_argument("story_file", nargs="?", default="", help="Path to markdown/text user story specification")
    p_gen_tc.set_defaults(func=cmd_generate_tc)

    # api-matrix
    p_api_mat = subparsers.add_parser("api-matrix", help="Generate Positive, Boundary, and Negative test matrix from OpenAPI/Swagger")
    p_api_mat.add_argument("--spec", "-s", help="Path to OpenAPI / Swagger JSON/YAML file")
    p_api_mat.add_argument("--format", "-f", choices=["markdown", "json"], default="markdown", help="Output format (markdown, json)")
    p_api_mat.add_argument("--output", "-o", help="Output file path")
    p_api_mat.add_argument("--sample", action="store_true", help="Generate a sample matrix using built-in demonstration schema")
    p_api_mat.set_defaults(func=cmd_api_matrix)

    # canvas-diff
    p_canvas = subparsers.add_parser("canvas-diff", help="HTML5 Canvas visual regression diffing & blank check")
    p_canvas.add_argument("canvas_args", nargs="*", help="Subcommand (compare/check-blank) and image paths")
    p_canvas.set_defaults(func=cmd_canvas_diff)

    # validate-groovy
    p_groovy = subparsers.add_parser("validate-groovy", help="Pre-check Groovy scripts & keywords syntax balance")
    p_groovy.add_argument("target", nargs="?", default=None, help="Target repository or file to validate")
    p_groovy.add_argument("--dir", "-d", help="Explicit directory to scan")
    p_groovy.set_defaults(func=cmd_validate_groovy)

    # mcp-serve
    p_mcp = subparsers.add_parser("mcp-serve", help="Start the JSON-RPC 2.0 stdio Model Context Protocol (MCP) server")
    p_mcp.set_defaults(func=cmd_mcp_serve)

    # mcp-excel
    p_mcp_excel = subparsers.add_parser("mcp-excel", help="Start the JSON-RPC 2.0 stdio MCP Excel server")
    p_mcp_excel.set_defaults(func=cmd_mcp_excel)

    # release
    p_release = subparsers.add_parser("release", help="1-Click atomic release: bump version across all targets, verify DoD gates, git tag & push for NPM Trusted Publishing")
    p_release.add_argument("action", nargs="?", default="patch", help="patch | minor | major | <explicit_version> (default: patch)")
    p_release.add_argument("--push", action="store_true", default=True, help="Auto-push commit and tag to origin to trigger CI release (default: true)")
    p_release.add_argument("--no-push", dest="push", action="store_false", help="Do not push to remote")
    p_release.add_argument("--no-test", action="store_true", help="Skip running tests before release")
    p_release.set_defaults(func=cmd_release)


def _handle_interactive_wizard(parser, args):
    """Offers a friendly quick-start menu if running in an interactive terminal."""
    is_interactive = hasattr(sys.stdin, "isatty") and sys.stdin.isatty() and not os.environ.get("CI") and not os.environ.get("SYNAPSE_NON_INTERACTIVE")
    if is_interactive:
        print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
        print(f"{BOLD}{CYAN}    🧠 SYNAPSE HUB — INTERACTIVE TERMINAL WIZARD                      {RESET}")
        print(f"{BOLD}{CYAN}======================================================================{RESET}")
        print("Chào bạn! Hãy chọn nhanh một tác vụ để bắt đầu (hoặc nhấn Enter để xem Trợ Giúp):")
        print(f"  {BOLD}1.{RESET} 🩺 {BOLD}Doctor{RESET}       - Kiểm tra chẩn đoán môi trường (Node, Python, Chrome, Git)")
        print(f"  {BOLD}2.{RESET} 🚀 {BOLD}Setup{RESET}        - Thiết lập bảo vệ 1-click cho dự án kiểm thử mục tiêu")
        print(f"  {BOLD}3.{RESET} 🔍 {BOLD}Lint{RESET}         - Quét phát hiện test pass ảo, 0 assert, sleep cứng")
        print(f"  {BOLD}4.{RESET} 🛡️  {BOLD}Verify{RESET}       - Chạy kiểm tra 9 Cổng Chất Lượng DoD")
        print(f"  {BOLD}5.{RESET} 🌐 {BOLD}Welcome{RESET}      - Mở trang Landing Page trực quan")
        print(f"  {BOLD}6.{RESET} ❓ {BOLD}Help{RESET}         - Xem danh sách đầy đủ tất cả các lệnh CLI")
        print(f"{BOLD}{CYAN}======================================================================{RESET}")
        try:
            choice = input(f"Nhập lựa chọn {BOLD}[1-6]{RESET} (mặc định: 6): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

        dispatch_map = {
            "1": ("doctor", cmd_doctor),
            "2": ("setup", cmd_setup),
            "3": ("lint", cmd_lint),
            "4": ("verify", cmd_verify),
            "5": ("welcome", cmd_welcome),
        }
        if choice in dispatch_map:
            subcmd, handler = dispatch_map[choice]
            args.subcommand = subcmd
            return handler(args)

    parser.print_help()
    print("\n💡 Tip: Run 'npx synapse-hub welcome' (or 'npm start') to launch the visual landing page.")
    sys.exit(0)


def main():
    parser = SynapseArgumentParser(
        prog="agent-qa",
        description="Enterprise AI Agent Quality Engineering & Test Automation Hub CLI"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Agent-QA Hub CLI v{_hub_version()}"
    )
    parser.add_argument(
        "--offline", "--offline-deterministic",
        action="store_true",
        dest="offline",
        help="Force 100%% offline air-gapped deterministic mode (zero external network / LLM API calls)"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        dest="quiet",
        help="Suppress informational banners and output only critical verdicts"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # Modular command registration (Refactored Command Dispatcher Pattern)
    _register_core_and_setup_commands(subparsers)
    _register_testing_and_execution_commands(subparsers)
    _register_audit_and_inspection_commands(subparsers)
    _register_platform_and_tools_commands(subparsers)

    args, unknown = parser.parse_known_args()
    if getattr(args, "offline", False):
        os.environ["AGENT_QA_OFFLINE"] = "1"
        print("🔒 [OFFLINE MODE] Air-Gapped Deterministic Mode Active. 100% Local AST & Heuristics (Zero External API calls).")

    if not args.subcommand:
        return _handle_interactive_wizard(parser, args)

    # Enforce canonical author attribution and anti-tamper provenance
    from author_integrity import assert_integrity_or_raise
    assert_integrity_or_raise()

    if getattr(args, "quiet", False):
        os.environ["SYNAPSE_QUIET"] = "1"

    # Non-intrusive cached update notification (24h cache)
    if args.subcommand not in ("update", "mcp-serve", "version") and not getattr(args, "quiet", False):
        try:
            import update_sentinel
            update_sentinel.check_for_updates(force=False, notify=True)
        except (ImportError, OSError, TimeoutError):
            _ = False

    # Dispatch subcommand
    args.func(args)


if __name__ == "__main__":
    main()
