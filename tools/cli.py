#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Enterprise Agent-QA CLI Entrypoint
----------------------------------
Provides a centralized command-line interface for the Synapse Hub ecosystem.
Dispatches commands to underlying specialized tools in tools/.
"""

import os
import sys
import json
import re
import difflib
import argparse
from typing import Optional

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
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from tools.core.i18n import resolve_language, t, persist_language_preference
except ImportError:
    try:
        from core.i18n import resolve_language, t, persist_language_preference
    except ImportError:
        def resolve_language(lang=None):
            return "en"
        def t(key, lang=None, **kwargs):
            return key
        def persist_language_preference(lang, target_dir=None):
            return ""

# ANSI Color formatting
def _is_color_allowed() -> bool:
    if os.environ.get("NO_COLOR") is not None or os.environ.get("TERM") == "dumb":
        return False
    if os.environ.get("FORCE_COLOR") in ("1", "true", "TRUE"):
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


_use_color = _is_color_allowed()
CYAN = "\033[96m" if _use_color else ""
GREEN = "\033[92m" if _use_color else ""
YELLOW = "\033[93m" if _use_color else ""
RED = "\033[91m" if _use_color else ""
BOLD = "\033[1m" if _use_color else ""
RESET = "\033[0m" if _use_color else ""


def cmd_set_lang(args):
    """Sets and persists the CLI interface language preference."""
    target_lang = getattr(args, "language", None)
    if not target_lang:
        cur = resolve_language()
        if cur == "vi":
            print("Ngôn ngữ giao diện hiện tại: Tiếng Việt (vi). Cú pháp: agent-qa set-lang <en|vi>")
        else:
            print("Current interface language: English (en). Usage: agent-qa set-lang <en|vi>")
        sys.exit(0)
    target_lang = str(target_lang).strip().lower()
    if target_lang not in ("en", "vi"):
        cur = resolve_language()
        if cur == "vi":
            print(f"❌ Lỗi: Mã ngôn ngữ '{target_lang}' không được hỗ trợ. Vui lòng chọn 'en' hoặc 'vi'.")
        else:
            print(f"❌ Error: Invalid language '{target_lang}'. Supported: 'en', 'vi'.")
        sys.exit(2)

    target_dir = os.getcwd() if getattr(args, "local", False) else None
    cfg_file = persist_language_preference(target_lang, target_dir=target_dir)
    os.environ["SYNAPSE_LANG"] = target_lang

    lang_names = {
        "en": "English" if target_lang == "en" else "Tiếng Anh",
        "vi": "Vietnamese" if target_lang == "en" else "Tiếng Việt"
    }
    lang_name = lang_names.get(target_lang, target_lang)
    print(t("lang_saved", lang=target_lang, lang_name=lang_name, lang_code=target_lang, config_path=cfg_file))
    print(f"\n{t('tip_lang_switch', lang=target_lang)}")
    sys.exit(0)


def cmd_version(args):
    """Displays the current hub version, skill catalog count, and license information."""
    manifest_path = os.path.join(REPO_ROOT, "skills_manifest.json")
    version = "4.1.0"
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
    print(f"Catalog: {manifest_skills} Standardized Skills | 9 Subagent Swarm Profiles")
    print("Created by: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>")
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


def _strip_interface_lang_flags(args: list) -> list:
    """Strips global interface language flags (--lang/ -l {en,vi}) from forwarded args.

    CRITICAL DOMAIN INVARIANT: Only strips when the language value is in ('en', 'vi').
    Preserves tool-specific flags like '--lang=python' or '--lang cypress'.
    """
    if not args:
        return []
    filtered = []
    skip_next = False
    for i, a in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if a in ("--lang", "-l") and i + 1 < len(args) and args[i + 1].strip().lower() in ("en", "vi"):
            skip_next = True
            continue
        if a.startswith(("--lang=", "-l=")):
            val = a.split("=", 1)[1].strip().lower()
            if val in ("en", "vi"):
                continue
        filtered.append(a)
    return filtered


def _forward_subcommand_args(args_or_name=None) -> list:
    """Safely extracts and forwards arguments intended for the underlying subcommand tool."""
    subcmd = args_or_name if isinstance(args_or_name, str) else getattr(args_or_name, "subcommand", None)
    if subcmd and subcmd in sys.argv:
        raw_args = sys.argv[sys.argv.index(subcmd) + 1:]
    else:
        raw_args = sys.argv[2:] if len(sys.argv) > 2 else []

    return [sys.argv[0]] + _strip_interface_lang_flags(raw_args)



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


def cmd_skills(args):
    from skill_profiles import main as skills_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(skills_main())


def cmd_analyze_jtl(args):
    from jtl_analyzer import main as jtl_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(jtl_main())


def cmd_export_excel(args):
    """Converts Markdown test cases into styled Excel, cloning corporate template if configured."""
    from template_excel_exporter import main as excel_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(excel_main())


def cmd_init_config(args):
    """Initializes a canonical .synapse.json configuration file for Spoke target projects."""
    from init_config import main as init_cfg_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(init_cfg_main())


def cmd_help(args):
    """Displays command-line help and usage documentation."""
    parser = getattr(args, "_parser", None)
    if parser:
        parser.print_help()
        sys.exit(0)
    print("Run 'agent-qa --help' to view command-line usage.")
    sys.exit(0)


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


def cmd_rules_router(args):
    from rules_router import main as router_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(router_main())


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


def cmd_mcp_docx(args):
    from mcp_docx_server import main as mcp_docx_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(mcp_docx_main())


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


def cmd_hub_publish(args):
    """End-to-End Hub release & publish pipeline: push to main, tag, release, GitHub Packages, and NPM Registry."""
    from hub_publisher import main as publisher_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(publisher_main())


def cmd_ui(args):
    """Launches the interactive QA Mission Control Web UI."""
    from ui_server import run_server
    target = getattr(args, "target", None) or getattr(args, "repo", None)
    run_server(host=args.host, port=args.port, open_browser=not args.no_browser, target_dir=target)


def cmd_jira_sync(args):
    """Synchronizes test cases, user stories, execution results, and bugs with Jira/Xray."""
    from jira_sync import main as jira_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(jira_main())


def cmd_trend(args):
    """Historical Quality Trend & Flakiness Analytics Engine."""
    from trend_analytics import main as trend_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(trend_main())


def _hub_version():
    manifest_path = os.path.join(REPO_ROOT, "skills_manifest.json")
    version = "4.1.0"
    if os.path.exists(manifest_path):
        try:
            import json
            with open(manifest_path, "r", encoding="utf-8") as f:
                version = json.load(f).get("version", version)
        except (OSError, json.JSONDecodeError):
            version = "4.1.0"
    return version


def _extract_cli_lang(argv: Optional[list] = None) -> Optional[str]:
    """Scans argv (or sys.argv) early for explicit --lang {en,vi} or -l {en,vi} flag."""
    target_args = argv if argv is not None else sys.argv
    for i, arg in enumerate(target_args):
        if arg in ("--lang", "-l") and i + 1 < len(target_args):
            val = target_args[i + 1].strip().lower()
            if val in ("en", "vi"):
                os.environ["SYNAPSE_LANG"] = val
                return val
        elif arg.startswith(("--lang=", "-l=")):
            val = arg.split("=", 1)[1].strip().lower()
            if val in ("en", "vi"):
                os.environ["SYNAPSE_LANG"] = val
                return val
    return None


CORE_COMMAND_SPECS = [
    ("doctor", "cmd_doctor"),
    ("setup", "cmd_setup"),
    ("init-config", "cmd_init_config"),
    ("lint", "cmd_lint"),
    ("verify", "cmd_verify"),
    ("export-excel", "cmd_export_excel"),
    ("welcome", "cmd_welcome"),
    ("ui", "cmd_ui"),
    ("dashboard", "cmd_dashboard"),
    ("analyze", "cmd_analyze"),
    ("set-lang", "cmd_set_lang"),
]

ADVANCED_HIGHLIGHT_SPECS = [
    ("mutate", "cmd_mutate"),
    ("auto-heal", "cmd_auto_heal"),
    ("som", "cmd_som"),
    ("fuzz-api", "cmd_fuzz_api"),
    ("transpile", "cmd_transpile"),
]


def _render_tiered_cli_help(lang: str) -> str:
    """Renders the localized, tiered CLI help banner for Core & Daily Workflows."""
    lines = [
        f"\n{BOLD}{CYAN}======================================================================{RESET}",
        f"{BOLD}{CYAN}  🧠 {t('banner_title', lang=lang)}    {RESET}",
        f"{BOLD}{CYAN}======================================================================{RESET}",
        f"{t('version_info', lang=lang, version=_hub_version())}\n",
        f"{BOLD}{t('usage_title', lang=lang)}{RESET}",
        f"{t('usage_syntax', lang=lang)}\n",
        f"{BOLD}{t('core_commands_title', lang=lang)}{RESET}",
    ]

    for cmd, msg_key in CORE_COMMAND_SPECS:
        lines.append(f"  {BOLD}{GREEN}{cmd:<14}{RESET} {t(msg_key, lang=lang)}")

    lines.append(f"\n{BOLD}{t('advanced_highlights_title', lang=lang)}{RESET}")
    for cmd, msg_key in ADVANCED_HIGHLIGHT_SPECS:
        lines.append(f"  {CYAN}{cmd:<14}{RESET} {t(msg_key, lang=lang)}")

    lines.append(f"\n{BOLD}{t('general_options_title', lang=lang)}{RESET}")
    lines.append(f"  {BOLD}-a, --all{RESET}      {t('opt_all', lang=lang)}")
    lines.append(f"  {BOLD}--version{RESET}      {t('opt_version', lang=lang)}")
    lines.append(f"  {BOLD}--offline{RESET}      {t('opt_offline', lang=lang)}")
    lines.append(f"  {BOLD}-q, --quiet{RESET}    {t('opt_quiet', lang=lang)}")
    lines.append(f"  {BOLD}--lang {{en,vi}}{RESET} {t('opt_lang', lang=lang)}")

    lines.append(f"\n{YELLOW}{t('tips_header', lang=lang)}{RESET}")
    lines.append(f"  {t('tip_all', lang=lang)}")
    lines.append(f"  {t('tip_cmd', lang=lang)}")
    lines.append(f"  {t('tip_welcome', lang=lang)}")
    lines.append(f"  {t('tip_lang_switch', lang=lang)}\n")
    return "\n".join(lines)


class SynapseArgumentParser(argparse.ArgumentParser):
    """Enhanced ArgumentParser providing bilingual support and fuzzy Did-You-Mean suggestions."""

    def __init__(self, *args, lang: Optional[str] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.lang = lang or resolve_language(_extract_cli_lang())
        self._localize_argparse_groups()

    def _localize_argparse_groups(self):
        """Applies active language localization to built-in argparse section titles and help."""
        if self.lang == "vi":
            if self.prog == "agent-qa":
                self._positionals.title = "Tham số và lệnh khả dụng"
                self._optionals.title = "Tùy chọn chung"
            else:
                self._positionals.title = "Tham số vị trí"
                self._optionals.title = "Tùy chọn"
            for a in self._actions:
                if a.dest == "help":
                    a.help = "Hiển thị hướng dẫn sử dụng và thoát"
        else:
            if self.prog == "agent-qa":
                self._positionals.title = "positional arguments"
                self._optionals.title = "general options"
            else:
                self._positionals.title = "positional arguments"
                self._optionals.title = "options"
            for a in self._actions:
                if a.dest == "help":
                    a.help = "show this help message and exit"

    def error(self, message):
        m = re.search(r"(?:argument\s+)?subcommand:\s+invalid choice:\s+'([^']+)'", message)
        if m:
            bad_choice = m.group(1)
            choices = []
            for action in self._actions:
                if isinstance(action, argparse._SubParsersAction):
                    choices = list(action.choices.keys())
                    break
            matches = difflib.get_close_matches(bad_choice, choices, n=3, cutoff=0.4)
            err_msg = t("typo_error", lang=self.lang, choice=bad_choice)
            sys.stderr.write(f"\n{BOLD}{RED}{err_msg}{RESET}\n")
            if matches:
                suggestions = ", ".join(f"{BOLD}{GREEN}{c}{RESET}" for c in matches)
                sug_msg = t("typo_suggest", lang=self.lang, suggestions=suggestions)
                hint_msg = t("typo_help_hint", lang=self.lang, first_match=matches[0])
                sys.stderr.write(f"{sug_msg}\n\n")
                sys.stderr.write(f"{hint_msg}\n\n")
            else:
                list_msg = t("typo_list_hint", lang=self.lang)
                sys.stderr.write(f"{list_msg}\n\n")
            sys.exit(2)
        super().error(message)

    def _delegate_subcommand_help(self):
        """Attempts to delegate help display to underlying tool if handler forwards args."""
        custom_actions = [a for a in self._actions if not isinstance(a, argparse._HelpAction)]
        if custom_actions:
            return

        if "--help" in sys.argv or "-h" in sys.argv:
            subcmd = self.prog.split()[-1] if " " in self.prog else self.prog
            if subcmd in ("mcp-excel", "mcp-docx", "mcp-serve"):
                return
            handler = self._defaults.get("func")
            if handler and "_forward_subcommand_args" in getattr(getattr(handler, "__code__", None), "co_names", ()):
                try:
                    ns = argparse.Namespace(subcommand=subcmd)
                    handler(ns)
                except SystemExit as exc:
                    sys.exit(exc.code if exc.code is not None else 0)
                except Exception as _err:
                    _ = _err

    def format_help(self):
        self._localize_argparse_groups()

        # If this is a subcommand parser (e.g. agent-qa mutate --help)
        if self.prog != "agent-qa":
            self._delegate_subcommand_help()
            base_help = super().format_help()
            switch_tip = f"\n{YELLOW}{t('tip_lang_switch', lang=self.lang)}{RESET}\n"
            return base_help + switch_tip

        # Check if full list is requested via --all or -a
        if "--all" in sys.argv or "-a" in sys.argv:
            base_help = super().format_help()
            switch_tip = f"\n{YELLOW}{t('tip_lang_switch', lang=self.lang)}{RESET}\n"
            return base_help + switch_tip

        return _render_tiered_cli_help(self.lang)


def _lh(en_text: str, vi_text: str, lang: str) -> str:
    """Selects localized text based on the active language code ('en' or 'vi')."""
    return vi_text if lang == "vi" else en_text



def _register_core_and_setup_commands(subparsers, lang: Optional[str] = None):
    """Registers core environment, setup, and informational subcommands."""
    lang = lang or resolve_language(_extract_cli_lang())
    # help
    p_help = subparsers.add_parser("help", help=t("cmd_help", lang=lang))
    p_help.add_argument("--all", "-a", action="store_true", dest="show_all", help=t("opt_all", lang=lang))
    p_help.set_defaults(func=cmd_help)

    # set-lang
    p_set_lang = subparsers.add_parser(
        "set-lang",
        aliases=["lang"],
        help=t("cmd_set_lang", lang=lang)
    )
    p_set_lang.add_argument(
        "language",
        choices=["en", "vi"],
        nargs="?",
        help=_lh("Language code to set and persist (en: English, vi: Vietnamese)", "Mã ngôn ngữ cần thiết lập và ghi nhớ (en: Tiếng Anh, vi: Tiếng Việt)", lang)
    )
    p_set_lang.add_argument(
        "--local",
        action="store_true",
        help=_lh("Persist to local .synapse.json in current directory", "Lưu cấu hình vào file .synapse.json tại thư mục hiện tại", lang)
    )
    p_set_lang.set_defaults(func=cmd_set_lang)

    # init-config
    p_init_cfg = subparsers.add_parser(
        "init-config",
        aliases=["init"],
        help=t("cmd_init_config", lang=lang)
    )
    p_init_cfg.add_argument(
        "target_dir",
        nargs="?",
        default=".",
        help=_lh("Target directory to initialize configuration (default: .)", "Thư mục đích khởi tạo file cấu hình (mặc định: .)", lang)
    )
    p_init_cfg.add_argument(
        "-t", "--template",
        dest="template_path",
        default=None,
        help=_lh("Path to template Excel file (.xlsx)", "Đường dẫn file template Excel (.xlsx)", lang)
    )
    p_init_cfg.add_argument(
        "-a", "--author",
        default=None,
        help=_lh("Author or QA Lead name", "Tên tác giả / QA Lead phụ trách dự án", lang)
    )
    p_init_cfg.add_argument(
        "--tester",
        default=None,
        help=_lh("Tester or QA engineer name", "Tên kiểm thử viên phụ trách", lang)
    )
    p_init_cfg.add_argument(
        "-s", "--sheet-name",
        dest="sample_sheet",
        default=None,
        help=_lh("Sample worksheet name to clone (default: Test Cases)", "Tên worksheet mẫu cần clone (mặc định: Test Cases)", lang)
    )
    p_init_cfg.add_argument(
        "-p", "--project-name",
        default=None,
        help=_lh("Project identifier name (default: directory name)", "Tên định danh của dự án (mặc định: tên thư mục)", lang)
    )
    p_init_cfg.add_argument(
        "--module-code",
        default="MOD",
        help=_lh("Abbreviated module code (default: MOD)", "Mã module viết tắt (mặc định: MOD)", lang)
    )
    p_init_cfg.add_argument(
        "--module-name",
        default="General Module",
        help=_lh("Test module name (default: General Module)", "Tên phân hệ kiểm thử (mặc định: General Module)", lang)
    )
    p_init_cfg.add_argument(
        "--out-dir",
        dest="default_output_dir",
        default="reports",
        help=_lh("Default report export directory (default: reports)", "Thư mục xuất báo cáo mặc định (mặc định: reports)", lang)
    )
    p_init_cfg.add_argument(
        "-f", "--force",
        action="store_true",
        help=_lh("Overwrite .synapse.json if it already exists", "Ghi đè file .synapse.json nếu đã tồn tại", lang)
    )
    p_init_cfg.add_argument(
        "--dry-run",
        action="store_true",
        help=_lh("Print JSON configuration to stdout without writing to disk", "In nội dung file JSON ra màn hình mà không ghi xuống ổ đĩa", lang)
    )
    p_init_cfg.add_argument(
        "-i", "--interactive",
        action="store_true",
        help=_lh("Enable interactive Q&A wizard mode", "Kích hoạt chế độ hỏi đáp tương tác trực tiếp", lang)
    )
    p_init_cfg.set_defaults(func=cmd_init_config)
    # version
    p_ver = subparsers.add_parser("version", help=t("cmd_version", lang=lang))
    p_ver.set_defaults(func=cmd_version)

    # setup
    p_setup = subparsers.add_parser("setup", help=t("cmd_setup", lang=lang))
    p_setup.set_defaults(func=cmd_setup)

    # doctor
    p_doctor = subparsers.add_parser("doctor", description=_lh("Enterprise Environment Diagnostic Tool", "Công cụ chẩn đoán môi trường kiểm thử doanh nghiệp", lang), help=t("cmd_doctor", lang=lang))
    p_doctor.add_argument("target", nargs="?", default=None, help=_lh("Target repository path to diagnose", "Đường dẫn thư mục dự án cần chẩn đoán", lang))
    p_doctor.add_argument("--repo", "--path", dest="repo_path", default=None, help=_lh("Target repository path", "Đường dẫn thư mục dự án mục tiêu", lang))
    p_doctor.add_argument("--insecure", action="store_true", help=_lh("Allow unverified SSL certificates during connectivity checks", "Cho phép bỏ qua kiểm tra chứng chỉ SSL", lang))
    p_doctor.set_defaults(func=cmd_doctor)

    # uninstall
    p_uninstall = subparsers.add_parser("uninstall", help=t("cmd_uninstall", lang=lang))
    p_uninstall.add_argument("target", nargs="?", default=None, help=_lh("Target repository path to revert", "Đường dẫn thư mục dự án cần gỡ bỏ cài đặt", lang))
    p_uninstall.set_defaults(func=cmd_uninstall)

    # welcome
    p_welcome = subparsers.add_parser("welcome", description=_lh("Interactive Visual Landing Page", "Trang Landing Page trực quan giới thiệu Synapse Hub", lang), help=t("cmd_welcome", lang=lang))
    p_welcome.add_argument("target", nargs="?", default=None, help=_lh("Target repository directory (default: current directory)", "Thư mục dự án mục tiêu (mặc định: thư mục hiện tại)", lang))
    p_welcome.add_argument("--output", "-o", default=None, help=_lh("Output HTML file path (default: reports/WELCOME.html)", "Đường dẫn file HTML đầu ra (mặc định: reports/WELCOME.html)", lang))
    p_welcome.add_argument("--lang", choices=["vi", "en"], default="vi", help=_lh("Default initial language (vi: Vietnamese, en: English, default: vi)", "Ngôn ngữ khởi tạo mặc định (vi: Tiếng Việt, en: Tiếng Anh, mặc định: vi)", lang))
    p_welcome.add_argument("--no-browser", action="store_true", help=_lh("Do not open the browser after generating the page", "Không tự động mở trình duyệt sau khi tạo trang", lang))
    p_welcome.add_argument("--open", action="store_true", help=_lh("Explicitly open the browser", "Tự động mở trình duyệt sau khi tạo trang", lang))
    p_welcome.add_argument("--first-run", action="store_true", help=_lh("Only open if running for the first time (e.g. npm install or first pull)", "Chỉ mở trình duyệt nếu là lần chạy đầu tiên", lang))
    p_welcome.set_defaults(func=cmd_welcome)

    # ui
    p_ui = subparsers.add_parser(
        "ui",
        help=t("cmd_ui", lang=lang)
    )
    p_ui.add_argument(
        "target",
        nargs="?",
        default=None,
        help=_lh("Target project directory (default: CWD)", "Thư mục dự án mục tiêu (mặc định: CWD)", lang)
    )
    p_ui.add_argument(
        "--repo", "--target",
        dest="repo",
        default=None,
        help=_lh("Target project directory", "Thư mục dự án mục tiêu", lang)
    )
    p_ui.add_argument(
        "--port", "-p",
        type=int,
        default=8080,
        help=_lh("TCP port to listen on (default: 8080)", "Cổng TCP khởi chạy (mặc định: 8080)", lang)
    )
    p_ui.add_argument(
        "--host",
        default="127.0.0.1",
        help=_lh("Host interface (default: 127.0.0.1)", "Host interface (mặc định: 127.0.0.1)", lang)
    )
    p_ui.add_argument(
        "--no-browser",
        action="store_true",
        help=_lh("Do not automatically open browser", "Không tự động mở trình duyệt", lang)
    )
    p_ui.set_defaults(func=cmd_ui)

    # dashboard
    p_dashboard = subparsers.add_parser("dashboard", help=t("cmd_dashboard", lang=lang))
    p_dashboard.add_argument("target", nargs="?", default=None, help=_lh("Target repository directory (default: current or Hub)", "Thư mục dự án mục tiêu (mặc định: thư mục hiện tại hoặc Hub)", lang))
    p_dashboard.add_argument("--output", "-o", help=_lh("Output HTML file path (default: <target>/reports/PROJECT_DASHBOARD.html)", "Đường dẫn file HTML đầu ra (mặc định: <target>/reports/PROJECT_DASHBOARD.html)", lang))
    p_dashboard.add_argument("--open", action="store_true", help=_lh("Automatically open generated dashboard in default browser", "Tự động mở dashboard trên trình duyệt mặc định", lang))
    p_dashboard.add_argument("--json", action="store_true", help=_lh("Print summary JSON to stdout", "In tóm tắt kết quả dưới dạng JSON ra màn hình", lang))
    p_dashboard.add_argument("--lang", choices=["vi", "en"], default="vi", help=_lh("Default display language (vi: Vietnamese, en: English, default: vi)", "Ngôn ngữ hiển thị mặc định (vi: Tiếng Việt, en: Tiếng Anh, mặc định: vi)", lang))
    p_dashboard.set_defaults(func=cmd_dashboard)

    # clean
    p_clean = subparsers.add_parser("clean", help=t("cmd_clean", lang=lang))
    p_clean.set_defaults(func=cmd_clean)

    # update
    p_update = subparsers.add_parser("update", help=t("cmd_update", lang=lang))
    p_update.add_argument("--check", action="store_true", help=_lh("Check for available updates without applying", "Kiểm tra bản cập nhật mới mà không áp dụng", lang))
    p_update.set_defaults(func=cmd_update)

    # check-version
    p_ver_sync = subparsers.add_parser("check-version", help=t("cmd_check_version", lang=lang))
    p_ver_sync.add_argument("--expected-version", "-e", help=_lh("Expected version string (e.g. from git tag)", "Chuỗi phiên bản kỳ vọng (ví dụ từ git tag)", lang), default=None)
    p_ver_sync.set_defaults(func=cmd_check_version)

    # sync-rules
    p_sync_rules = subparsers.add_parser("sync-rules", help=t("cmd_sync_rules", lang=lang))
    p_sync_rules.add_argument("--check", action="store_true", help=_lh("Verify all AI bridges are in sync without writing", "Kiểm tra tính đồng bộ của cầu nối AI mà không ghi file", lang))
    p_sync_rules.set_defaults(func=cmd_sync_rules)


def _register_testing_and_execution_commands(subparsers, lang: Optional[str] = None):
    """Registers automated testing, linting, healing, and mutation subcommands."""
    lang = lang or resolve_language(_extract_cli_lang())
    # verify
    p_verify = subparsers.add_parser("verify", help=t("cmd_verify", lang=lang))
    p_verify.set_defaults(func=cmd_verify)

    # lint
    p_lint = subparsers.add_parser("lint", help=t("cmd_lint", lang=lang))
    p_lint.set_defaults(func=cmd_lint)

    # auto-heal
    p_auto_heal = subparsers.add_parser("auto-heal", help=t("cmd_auto_heal", lang=lang))
    p_auto_heal.set_defaults(func=cmd_auto_heal)

    # heal-pr
    p_heal_pr = subparsers.add_parser("heal-pr", help=t("cmd_heal_pr", lang=lang))
    p_heal_pr.set_defaults(func=cmd_heal_pr)

    # heal (memory cache)
    p_heal = subparsers.add_parser("heal", help=t("cmd_heal", lang=lang))
    p_heal.set_defaults(func=cmd_heal)

    # mutate
    p_mut = subparsers.add_parser("mutate", help=t("cmd_mutate", lang=lang).replace("%", "%%"))
    p_mut.set_defaults(func=cmd_mutate)

    # shard
    p_shard = subparsers.add_parser("shard", help=t("cmd_shard", lang=lang))
    p_shard.set_defaults(func=cmd_shard)

    # sync-jira
    p_jira = subparsers.add_parser(
        "sync-jira",
        add_help=False,
        aliases=["jira", "jira-sync"],
        help=t("cmd_sync_jira", lang=lang)
    )
    p_jira.set_defaults(func=cmd_jira_sync)

    # trend
    p_trend = subparsers.add_parser(
        "trend",
        add_help=False,
        aliases=["trends", "history"],
        help=t("cmd_trend", lang=lang)
    )
    p_trend.set_defaults(func=cmd_trend)

    # flaky
    p_flaky = subparsers.add_parser("flaky", help=t("cmd_flaky", lang=lang))
    p_flaky.set_defaults(func=cmd_flaky)

    # canary
    p_canary = subparsers.add_parser("canary", help=t("cmd_canary", lang=lang))
    p_canary.set_defaults(func=cmd_canary)

    # watch
    p_watch = subparsers.add_parser("watch", help=t("cmd_watch", lang=lang))
    p_watch.add_argument("target", nargs="?", default=".", help=_lh("Directory to monitor (default: current directory)", "Thư mục cần giám sát (mặc định: thư mục hiện tại)", lang))
    p_watch.add_argument("--debounce", type=float, default=0.8, help=_lh("Debounce interval in seconds (default: 0.8)", "Khoảng thời gian debounce tính bằng giây (mặc định: 0.8)", lang))
    p_watch.add_argument("--inactivity-timeout", type=float, default=0.0, help=_lh("Inactivity timeout in seconds to trigger stuck warning (default: 0 = disabled)", "Thời gian chờ không hoạt động để cảnh báo tắc nghẽn tính bằng giây (mặc định: 0 = tắt)", lang))
    p_watch.add_argument("--once", action="store_true", help=_lh("Run incremental scan once on all files and exit", "Chạy quét gia tăng một lần trên toàn bộ tệp và thoát", lang))
    p_watch.set_defaults(func=cmd_watch)

    # pinpoint-failure
    p_pinpoint = subparsers.add_parser("pinpoint-failure", help=t("cmd_pinpoint_failure", lang=lang))
    p_pinpoint.add_argument("report_file", nargs="?", default="", help=_lh("Path to JUnit XML test report", "Đường dẫn tới file báo cáo kiểm thử JUnit XML", lang))
    p_pinpoint.set_defaults(func=cmd_pinpoint_failure)

    # ci-hook
    p_ci = subparsers.add_parser("ci-hook", help=t("cmd_ci_hook", lang=lang))
    p_ci.set_defaults(func=cmd_ci_hook)


def _register_audit_and_inspection_commands(subparsers, lang: Optional[str] = None):
    """Registers security, architecture, and code quality inspection subcommands."""
    lang = lang or resolve_language(_extract_cli_lang())
    # analyze
    p_analyze = subparsers.add_parser("analyze", help=t("cmd_analyze", lang=lang))
    p_analyze.set_defaults(func=cmd_analyze)

    # debt
    p_debt = subparsers.add_parser("debt", aliases=["harvest-debt"], help=t("cmd_debt", lang=lang))
    p_debt.add_argument("target", nargs="?", default=".", help=_lh("Directory to scan (default: current directory)", "Thư mục cần quét (mặc định: thư mục hiện tại)", lang))
    p_debt.add_argument("--keyword", "-k", default=None, help=_lh("Custom marker keyword (default: shortcut or ponytail)", "Từ khóa đánh dấu nợ kỹ thuật tùy chỉnh (mặc định: shortcut hoặc ponytail)", lang))
    p_debt.add_argument("--output", "-o", default=None, help=_lh("Save report to Markdown file", "Lưu báo cáo vào file Markdown", lang))
    p_debt.add_argument("--json", action="store_true", help=_lh("Output results in JSON format", "Xuất kết quả dưới định dạng JSON", lang))
    p_debt.set_defaults(func=cmd_debt)

    # review
    p_review = subparsers.add_parser("review", aliases=["code-review"], help=t("cmd_review", lang=lang))
    p_review.add_argument("target_dir", nargs="?", default=".", help=_lh("Repository directory (default: current directory)", "Thư mục dự án (mặc định: thư mục hiện tại)", lang))
    p_review.add_argument("--staged", action="store_true", help=_lh("Review staged git changes", "Đánh giá các thay đổi git đã staged", lang))
    p_review.add_argument("--branch", default=None, help=_lh("Review changes against a git branch or commit ref", "Đánh giá thay đổi so với nhánh git hoặc commit ref", lang))
    p_review.add_argument("--json", action="store_true", help=_lh("Output results in JSON format", "Xuất kết quả dưới định dạng JSON", lang))
    p_review.set_defaults(func=cmd_review)

    # safety-check
    p_safety = subparsers.add_parser("safety-check", help=t("cmd_safety_check", lang=lang))
    p_safety.set_defaults(func=cmd_safety_check)

    # contract-drift
    p_drift = subparsers.add_parser("contract-drift", help=t("cmd_contract_drift", lang=lang))
    p_drift.set_defaults(func=cmd_contract_drift)

    # skillspector
    p_skillspector = subparsers.add_parser("skillspector", help=t("cmd_skillspector", lang=lang))
    p_skillspector.add_argument("path", nargs="?", default=".", help=_lh("Skill directory or file to scan (default: current directory)", "Thư mục hoặc tệp kỹ năng cần quét (mặc định: thư mục hiện tại)", lang))
    p_skillspector.add_argument("--format", choices=["terminal", "json", "markdown", "sarif"], default="terminal", help=_lh("Output format", "Định dạng đầu ra", lang))
    p_skillspector.add_argument("--output", "-o", help=_lh("Write report to output file", "Ghi báo cáo ra tệp đầu ra", lang))
    p_skillspector.add_argument("--strict", action="store_true", help=_lh("Fail with non-zero exit code on HIGH/CRITICAL finding", "Thoát với mã lỗi khác 0 khi phát hiện cảnh báo HIGH/CRITICAL", lang))
    p_skillspector.set_defaults(func=cmd_skillspector)

    # skills / profiles
    p_skills = subparsers.add_parser("skills", aliases=["profiles", "list-skills"], help=t("cmd_skills", lang=lang))
    p_skills.add_argument("--profile", "-p", help=_lh("Filter skills by capability profile (core-web-qa, perf-and-load, api-security, enterprise-rbt)", "Lọc kỹ năng theo gói năng lực (core-web-qa, perf-and-load, api-security, enterprise-rbt)", lang))
    p_skills.add_argument("--list-profiles", "-l", action="store_true", help=_lh("List all available capability profiles with summaries", "Liệt kê danh sách tất cả các gói năng lực kèm tóm tắt", lang))
    p_skills.add_argument("--category", "-c", help=_lh("Filter skills by category", "Lọc kỹ năng theo danh mục", lang))
    p_skills.add_argument("--query", "-q", help=_lh("Search skills by keyword", "Tìm kiếm kỹ năng theo từ khóa", lang))
    p_skills.add_argument("--format", choices=["text", "json"], default="text", help=_lh("Output format (text or json)", "Định dạng xuất kết quả (text hoặc json)", lang))
    p_skills.set_defaults(func=cmd_skills)

    # verify-author
    p_author = subparsers.add_parser("verify-author", help=t("cmd_verify_author", lang=lang))
    p_author.set_defaults(func=cmd_verify_author)

    # wcag-audit
    p_wcag = subparsers.add_parser("wcag-audit", help=t("cmd_wcag_audit", lang=lang))
    p_wcag.add_argument("target", nargs="?", default=".", help=_lh("Target HTML file or directory to audit", "Tệp HTML hoặc thư mục cần kiểm toán WCAG", lang))
    p_wcag.set_defaults(func=cmd_wcag_audit)

    # rules-router (Boost B2)
    p_router = subparsers.add_parser("rules-router", aliases=["route-rules"], help=_lh("Progressive Rules Router & Token Optimizer", "Định tuyến quy tắc thông minh & tối ưu token", lang))
    p_router.add_argument("workspace", nargs="?", default=".", help=_lh("Target workspace directory to inspect", "Thư mục dự án cần phân tích stack", lang))
    p_router.add_argument("--json", action="store_true", help=_lh("Output machine-readable JSON format", "Xuất định dạng JSON cho máy đọc", lang))
    p_router.add_argument("--summary", action="store_true", help=_lh("Output concise 1-line summary", "Xuất tóm tắt 1 dòng ngắn gọn", lang))
    p_router.set_defaults(func=cmd_rules_router)

    # impact
    p_impact = subparsers.add_parser("impact", help=t("cmd_impact", lang=lang))
    p_impact.set_defaults(func=cmd_impact)

    # review-spec
    p_review_spec = subparsers.add_parser("review-spec", help=t("cmd_review_spec", lang=lang))
    p_review_spec.add_argument("spec_file", nargs="?", default="", help=_lh("Path to specification file (Markdown or Gherkin .feature, use '-' for stdin)", "Đường dẫn tới file đặc tả (Markdown hoặc Gherkin .feature, dùng '-' cho stdin)", lang))
    p_review_spec.add_argument("--stdin", action="store_true", help=_lh("Read specification from standard input (stdin)", "Đọc nội dung đặc tả từ luồng vào chuẩn (stdin)", lang))
    p_review_spec.add_argument("--json", action="store_true", help=_lh("Output machine-readable JSON format", "Xuất định dạng JSON cho máy đọc", lang))
    p_review_spec.add_argument("--min-score", type=int, default=80, help=_lh("Minimum readiness score threshold (default: 80)", "Ngưỡng điểm sẵn sàng tối thiểu (mặc định: 80)", lang))
    p_review_spec.set_defaults(func=cmd_review_spec)

    # drift-check
    p_spec_drift = subparsers.add_parser("drift-check", help=t("cmd_drift_check", lang=lang))
    p_spec_drift.add_argument("--spec", required=True, help=_lh("Path to specification file (Markdown or Gherkin .feature)", "Đường dẫn tới file đặc tả (Markdown hoặc Gherkin .feature)", lang))
    p_spec_drift.add_argument("--code", required=True, help=_lh("Path to test script or directory of test scripts", "Đường dẫn tới kịch bản test hoặc thư mục kịch bản", lang))
    p_spec_drift.add_argument("--markdown", "-m", help=_lh("Path to export Markdown drift report (e.g. SPEC_DRIFT_REPORT.md)", "Đường dẫn xuất báo cáo độ lệch Markdown (ví dụ: SPEC_DRIFT_REPORT.md)", lang))
    p_spec_drift.add_argument("--json", action="store_true", help=_lh("Output machine-readable JSON format", "Xuất định dạng JSON cho máy đọc", lang))
    p_spec_drift.set_defaults(func=cmd_drift_check)

    # trace-data-flow
    p_trace = subparsers.add_parser("trace-data-flow", help=t("cmd_trace_data_flow", lang=lang))
    p_trace.add_argument("target", nargs="?", default=".", help=_lh("Target test directory to inspect", "Thư mục kiểm thử mục tiêu cần phân tích luồng dữ liệu", lang))
    p_trace.set_defaults(func=cmd_trace_data_flow)


def _register_platform_and_tools_commands(subparsers, lang: Optional[str] = None):
    """Registers protocol generators, converters, MCP servers, and utility subcommands."""
    lang = lang or resolve_language(_extract_cli_lang())
    # distill
    p_distill = subparsers.add_parser("distill", help=t("cmd_distill", lang=lang).replace("%", "%%"))
    p_distill.set_defaults(func=cmd_distill)

    # gherkin
    p_gherkin = subparsers.add_parser("gherkin", help=t("cmd_gherkin", lang=lang))
    p_gherkin.set_defaults(func=cmd_gherkin)

    # transpile
    p_trans = subparsers.add_parser("transpile", help=t("cmd_transpile", lang=lang))
    p_trans.add_argument("source", help=_lh("Source file path", "Đường dẫn file nguồn kiểm thử", lang))
    p_trans.add_argument("--to", required=True, choices=["playwright-ts", "playwright-python", "selenium-java", "katalon-groovy", "cypress-js"], help=_lh("Target framework", "Framework kiểm thử mục tiêu chuyển đổi", lang))
    p_trans.add_argument("--out", default=None, help=_lh("Output directory", "Thư mục lưu trữ kết quả đầu ra", lang))
    p_trans.set_defaults(func=cmd_transpile)

    # omni-scan
    p_omni = subparsers.add_parser("omni-scan", help=t("cmd_omni_scan", lang=lang))
    p_omni.add_argument("path", default=".", nargs="?", help=_lh("Directory to scan", "Thư mục cần quét danh mục test", lang))
    p_omni.add_argument("--json", action="store_true", help=_lh("Output raw JSON", "Xuất kết quả định dạng JSON thô", lang))
    p_omni.set_defaults(func=cmd_omni_scan)

    # report-bug
    p_bug = subparsers.add_parser("report-bug", help=t("cmd_report_bug", lang=lang))
    p_bug.set_defaults(func=cmd_report_bug)

    # mock-shield
    p_mock = subparsers.add_parser("mock-shield", help=t("cmd_mock_shield", lang=lang))
    p_mock.set_defaults(func=cmd_mock_shield)

    # visual-mask
    p_mask = subparsers.add_parser("visual-mask", help=t("cmd_visual_mask", lang=lang))
    p_mask.set_defaults(func=cmd_visual_mask)

    # migrate
    p_migrate = subparsers.add_parser("migrate", help=t("cmd_migrate", lang=lang))
    p_migrate.add_argument("--src", required=True, help=_lh("Source legacy test suite file or directory", "Đường dẫn file hoặc thư mục kịch bản test cũ", lang))
    p_migrate.add_argument("--dest", default="playwright_suite", help=_lh("Destination directory for migrated code", "Thư mục lưu mã nguồn kiểm thử mới sau khi chuyển đổi", lang))
    p_migrate.add_argument("--target", default="playwright-ts", choices=["playwright-ts", "playwright-python", "selenium-java", "cypress-js"], help=_lh("Target framework", "Framework kiểm thử mục tiêu", lang))
    p_migrate.set_defaults(func=cmd_migrate)

    # decouple-config
    p_decouple = subparsers.add_parser("decouple-config", help=t("cmd_decouple_config", lang=lang))
    p_decouple.add_argument("target", nargs="?", default=os.getcwd(), help=_lh("Target directory to scan", "Thư mục cần quét tách cấu hình", lang))
    p_decouple.add_argument("--fix", action="store_true", help=_lh("Apply environment variable replacements in-place", "Áp dụng thay thế biến môi trường trực tiếp trên tệp", lang))
    p_decouple.add_argument("--out-dir", default=None, help=_lh("Output directory for config profiles", "Thư mục lưu các file hồ sơ cấu hình môi trường", lang))
    p_decouple.set_defaults(func=cmd_decouple_config)

    # fuzz-api
    p_fuzz = subparsers.add_parser("fuzz-api", help=t("cmd_fuzz_api", lang=lang))
    p_fuzz.set_defaults(func=cmd_fuzz_api)

    # som
    p_som = subparsers.add_parser("som", help=t("cmd_som", lang=lang))
    p_som.set_defaults(func=cmd_som)

    # export-postman
    p_postman = subparsers.add_parser("export-postman", help=t("cmd_export_postman", lang=lang))
    p_postman.set_defaults(func=cmd_export_postman)

    # generate-jmx
    p_jmx = subparsers.add_parser("generate-jmx", help=t("cmd_generate_jmx", lang=lang))
    p_jmx.set_defaults(func=cmd_generate_jmx)

    # analyze-jtl
    p_jtl = subparsers.add_parser("analyze-jtl", help=t("cmd_analyze_jtl", lang=lang))
    p_jtl.set_defaults(func=cmd_analyze_jtl)

    # export-excel
    p_excel = subparsers.add_parser(
        "export-excel",
        help=t("cmd_export_excel", lang=lang)
    )
    p_excel.add_argument(
        "input",
        nargs="?",
        help=_lh("Path to Markdown test cases specification file (.md)", "Đường dẫn file Markdown test cases (.md)", lang)
    )
    p_excel.add_argument(
        "-o", "--output",
        help=_lh("Path to output Excel file (.xlsx)", "Đường dẫn file Excel đầu ra (.xlsx)", lang)
    )
    p_excel.add_argument(
        "-t", "--template",
        help=_lh("Path to corporate template Excel file", "Đường dẫn file Excel template doanh nghiệp", lang)
    )
    p_excel.add_argument(
        "-s", "--sample-sheet",
        default=None,
        help=_lh("Sample worksheet name to clone", "Tên worksheet mẫu cần clone", lang)
    )
    p_excel.add_argument(
        "--sheet-name",
        help=_lh("Target worksheet name (default: Test Cases)", "Tên worksheet mục tiêu (mặc định: Test Cases)", lang)
    )
    p_excel.add_argument(
        "--module-code",
        default="MODULE",
        help=_lh("Module code (default: MODULE)", "Mã phân hệ (Module Code)", lang)
    )
    p_excel.add_argument(
        "--module-name",
        default="Test Module",
        help=_lh("Test module name (default: Test Module)", "Tên phân hệ kiểm thử", lang)
    )
    p_excel.add_argument(
        "--author",
        default=None,
        help=_lh("Author or QA Lead name", "Tên tác giả / QA Lead", lang)
    )
    p_excel.add_argument(
        "--tester",
        default=None,
        help=_lh("Tester or QA engineer name", "Tên kiểm thử viên", lang)
    )
    p_excel.add_argument(
        "--standalone",
        action="store_true",
        help=_lh("Keep only newly exported sheet, remove others", "Chỉ giữ lại sheet mới xuất, xóa các sheet khác", lang)
    )
    p_excel.set_defaults(func=cmd_export_excel)

    # correlate-telemetry
    p_telemetry = subparsers.add_parser("correlate-telemetry", help=t("cmd_correlate_telemetry", lang=lang))
    p_telemetry.set_defaults(func=cmd_correlate_telemetry)

    # analyze-newman
    p_newman = subparsers.add_parser("analyze-newman", help=t("cmd_analyze_newman", lang=lang))
    p_newman.set_defaults(func=cmd_analyze_newman)

    # tokens
    p_tokens = subparsers.add_parser("tokens", help=t("cmd_tokens", lang=lang))
    p_tokens.add_argument("--platform", "-p", choices=["auto", "antigravity", "cursor", "claude", "all"], default="auto", help=_lh("AI platform to audit (default: auto)", "Nền tảng AI cần kiểm toán token (mặc định: auto)", lang))
    p_tokens.add_argument("--session", type=str, help=_lh("Specific session ID or index to audit", "Mã phiên hoặc chỉ số phiên cụ thể cần kiểm toán", lang))
    p_tokens.add_argument("--current", action="store_true", help=_lh("Audit current active conversation", "Kiểm toán phiên hội thoại đang hoạt động hiện tại", lang))
    p_tokens.add_argument("--last", action="store_true", help=_lh("Audit previous completed session (default)", "Kiểm toán phiên hội thoại hoàn thành gần nhất (mặc định)", lang))
    p_tokens.add_argument("--last-task", action="store_true", help=_lh("Audit specifically the last turn of target session", "Kiểm toán riêng lượt trao đổi cuối của phiên mục tiêu", lang))
    p_tokens.add_argument("--turns", action="store_true", help=_lh("Show full turn-by-turn breakdown table", "Hiển thị bảng chi tiết phân tích từng lượt trao đổi", lang))
    p_tokens.add_argument("--rolling", "--budget", action="store_true", dest="rolling", help=_lh("Show 5-hour and 7-day rolling window quota & remaining tokens", "Hiển thị định mức cửa sổ 5 giờ và 7 ngày kèm lượng token còn lại", lang))
    p_tokens.add_argument("--savings", action="store_true", help=_lh("Show Hub vs. Non-Hub token and cost savings comparison", "So sánh tỷ lệ tiết kiệm token và chi phí giữa Hub và Non-Hub", lang))
    p_tokens.add_argument("--header", action="store_true", help=_lh("Print Pre-Flight confirmation block lines", "In khối xác nhận Pre-Flight", lang))
    p_tokens.add_argument("--list", action="store_true", help=_lh("List recent conversations", "Liệt kê danh sách các phiên hội thoại gần đây", lang))
    p_tokens.add_argument("--pricing", choices=["gemini-flash", "gemini-pro", "claude-sonnet", "claude-opus", "gpt-4o", "gpt-4o-mini"], default=None, help=_lh("Model pricing basis (default: auto-detected)", "Bảng giá mô hình áp dụng tính chi phí (mặc định: tự động phát hiện)", lang))
    p_tokens.add_argument("--json", action="store_true", help=_lh("Output machine-readable JSON format", "Xuất kết quả định dạng JSON cho máy đọc", lang))
    p_tokens.add_argument("--file", type=str, help=_lh("Direct path to a transcript.jsonl file", "Đường dẫn trực tiếp tới tệp nhật ký transcript.jsonl", lang))
    p_tokens.set_defaults(func=cmd_tokens)

    # lookup-tc
    p_lookup_tc = subparsers.add_parser("lookup-tc", help=t("cmd_lookup_tc", lang=lang))
    p_lookup_tc.add_argument("query", nargs="?", default="", help=_lh("Query keyword or TC ID", "Từ khóa tìm kiếm hoặc mã Test Case (TC ID)", lang))
    p_lookup_tc.set_defaults(func=cmd_lookup_tc)

    # lookup-xpath
    p_lookup_xpath = subparsers.add_parser("lookup-xpath", help=t("cmd_lookup_xpath", lang=lang))
    p_lookup_xpath.add_argument("query", nargs="?", default="", help=_lh("Element text, test-id, or locator label", "Văn bản phần tử, thuộc tính test-id hoặc nhãn định vị", lang))
    p_lookup_xpath.set_defaults(func=cmd_lookup_xpath)

    # generate-tc
    p_gen_tc = subparsers.add_parser("generate-tc", help=t("cmd_generate_tc", lang=lang))
    p_gen_tc.add_argument("story_file", nargs="?", default="", help=_lh("Path to markdown/text user story specification", "Đường dẫn tới tệp đặc tả user story bằng Markdown hoặc văn bản", lang))
    p_gen_tc.set_defaults(func=cmd_generate_tc)

    # api-matrix
    p_api_mat = subparsers.add_parser("api-matrix", help=t("cmd_api_matrix", lang=lang))
    p_api_mat.add_argument("--spec", "-s", help=_lh("Path to OpenAPI / Swagger JSON/YAML file", "Đường dẫn tới file OpenAPI / Swagger định dạng JSON hoặc YAML", lang))
    p_api_mat.add_argument("--format", "-f", choices=["markdown", "json"], default="markdown", help=_lh("Output format (markdown, json)", "Định dạng đầu ra (markdown, json)", lang))
    p_api_mat.add_argument("--output", "-o", help=_lh("Output file path", "Đường dẫn tệp đầu ra", lang))
    p_api_mat.add_argument("--sample", action="store_true", help=_lh("Generate a sample matrix using built-in demonstration schema", "Tạo ma trận mẫu sử dụng lược đồ minh họa có sẵn", lang))
    p_api_mat.set_defaults(func=cmd_api_matrix)

    # canvas-diff
    p_canvas = subparsers.add_parser("canvas-diff", help=t("cmd_canvas_diff", lang=lang))
    p_canvas.add_argument("canvas_args", nargs="*", help=_lh("Subcommand (compare/check-blank) and image paths", "Lệnh con (compare/check-blank) và đường dẫn ảnh", lang))
    p_canvas.set_defaults(func=cmd_canvas_diff)

    # validate-groovy
    p_groovy = subparsers.add_parser("validate-groovy", help=t("cmd_validate_groovy", lang=lang))
    p_groovy.add_argument("target", nargs="?", default=None, help=_lh("Target repository or file to validate", "Thư mục dự án hoặc tệp kịch bản cần kiểm tra cú pháp", lang))
    p_groovy.add_argument("--dir", "-d", help=_lh("Explicit directory to scan", "Thư mục cụ thể cần quét kiểm tra", lang))
    p_groovy.set_defaults(func=cmd_validate_groovy)

    # mcp-serve
    p_mcp = subparsers.add_parser("mcp-serve", help=t("cmd_mcp_serve", lang=lang))
    p_mcp.set_defaults(func=cmd_mcp_serve)

    # mcp-excel
    p_mcp_excel = subparsers.add_parser("mcp-excel", help=t("cmd_mcp_excel", lang=lang))
    p_mcp_excel.set_defaults(func=cmd_mcp_excel)

    # mcp-docx
    p_mcp_docx = subparsers.add_parser("mcp-docx", help=t("cmd_mcp_docx", lang=lang))
    p_mcp_docx.set_defaults(func=cmd_mcp_docx)

    # release
    p_release = subparsers.add_parser("release", help=t("cmd_release", lang=lang))
    p_release.add_argument("action", nargs="?", default="patch", help=_lh("patch | minor | major | <explicit_version> (default: patch)", "patch | minor | major | <phiên_bản_cụ_thể> (mặc định: patch)", lang))
    p_release.add_argument("--push", action="store_true", default=True, help=_lh("Auto-push commit and tag to origin to trigger CI release (default: true)", "Tự động đẩy commit và tag lên origin để kích hoạt CI release (mặc định: true)", lang))
    p_release.add_argument("--no-push", dest="push", action="store_false", help=_lh("Do not push to remote", "Không đẩy lên kho chứa từ xa (remote)", lang))
    p_release.add_argument("--no-test", action="store_true", help=_lh("Skip running tests before release", "Bỏ qua việc chạy kiểm thử trước khi phát hành", lang))
    p_release.set_defaults(func=cmd_release)

    # publish / hub-push
    p_publish = subparsers.add_parser(
        "publish",
        aliases=["hub-push", "push-hub"],
        help=t("cmd_publish", lang=lang)
    )
    p_publish.add_argument("--message", "-m", help=_lh("Optional commit message for unstaged/pending changes", "Thông điệp commit tùy chọn cho các thay đổi chưa commit", lang))
    p_publish.add_argument("--skip-verify", action="store_true", help=_lh("Skip running 10 Quality Gates DoD before push", "Bỏ qua kiểm tra 10 Cổng Chất Lượng DoD trước khi đẩy", lang))
    p_publish.add_argument("--dry-run", action="store_true", help=_lh("Simulate all steps without pushing or publishing", "Mô phỏng toàn bộ các bước mà không thực sự đẩy hay xuất bản", lang))
    p_publish.add_argument("--no-wait", action="store_true", help=_lh("Fire and forget without waiting for CI workflow / npm verification", "Chạy nền mà không chờ quy trình CI workflow / kiểm tra NPM hoàn tất", lang))
    p_publish.add_argument("--timeout", type=int, default=180, help=_lh("Maximum seconds to wait for npm publication", "Thời gian chờ tối đa tính bằng giây cho việc xuất bản NPM", lang))
    p_publish.set_defaults(func=cmd_hub_publish)


def _handle_interactive_wizard(parser, args):
    """Offers a friendly quick-start menu if running in an interactive terminal."""
    is_interactive = hasattr(sys.stdin, "isatty") and sys.stdin.isatty() and not os.environ.get("CI") and not os.environ.get("SYNAPSE_NON_INTERACTIVE")
    if is_interactive:
        print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
        print(f"{BOLD}{CYAN}    🧠 SYNAPSE HUB — INTERACTIVE TERMINAL WIZARD                      {RESET}")
        print(f"{BOLD}{CYAN}======================================================================{RESET}")
        if parser.lang == "vi":
            print("Chào bạn! Hãy chọn nhanh một tác vụ để bắt đầu (hoặc nhấn Enter để xem Trợ Giúp):")
            print(f"  {BOLD}1.{RESET} 🩺 {BOLD}Doctor{RESET}       - Kiểm tra chẩn đoán môi trường (Node, Python, Chrome, Git)")
            print(f"  {BOLD}2.{RESET} 🚀 {BOLD}Setup{RESET}        - Thiết lập bảo vệ 1-click cho dự án kiểm thử mục tiêu")
            print(f"  {BOLD}3.{RESET} ⚙️  {BOLD}Init-Config{RESET}  - Khởi tạo file cấu hình .synapse.json chuẩn hóa cho dự án Spoke")
            print(f"  {BOLD}4.{RESET} 🔍 {BOLD}Lint{RESET}         - Quét phát hiện test pass ảo, 0 assert, sleep cứng")
            print(f"  {BOLD}5.{RESET} 🛡️  {BOLD}Verify{RESET}       - Chạy kiểm tra 10 Cổng Chất Lượng DoD")
            print(f"  {BOLD}6.{RESET} 📊 {BOLD}Export-Excel{RESET} - Xuất test cases Markdown sang file Excel (.xlsx)")
            print(f"  {BOLD}7.{RESET} 🌐 {BOLD}Welcome{RESET}      - Mở trang Landing Page trực quan")
            print(f"  {BOLD}8.{RESET} ❓ {BOLD}Help{RESET}         - Xem danh sách đầy đủ tất cả các lệnh CLI")
            print(f"{BOLD}{CYAN}======================================================================{RESET}")
            prompt = f"Nhập lựa chọn {BOLD}[1-8]{RESET} (mặc định: 8): "
        else:
            print("Welcome! Select a quick workflow to begin (or press Enter to view Help):")
            print(f"  {BOLD}1.{RESET} 🩺 {BOLD}Doctor{RESET}       - Diagnostic environment check (Node, Python, Chrome, Git)")
            print(f"  {BOLD}2.{RESET} 🚀 {BOLD}Setup{RESET}        - 1-click bootstrap & protection for target test project")
            print(f"  {BOLD}3.{RESET} ⚙️  {BOLD}Init-Config{RESET}  - Initialize standardized .synapse.json config for Spoke project")
            print(f"  {BOLD}4.{RESET} 🔍 {BOLD}Lint{RESET}         - AST scan catching fake-passes, 0 asserts, hard sleeps")
            print(f"  {BOLD}5.{RESET} 🛡️  {BOLD}Verify{RESET}       - Execute 10 Quality Gates Definition of Done (DoD)")
            print(f"  {BOLD}6.{RESET} 📊 {BOLD}Export-Excel{RESET} - Export Markdown test cases to enterprise Excel (.xlsx)")
            print(f"  {BOLD}7.{RESET} 🌐 {BOLD}Welcome{RESET}      - Launch interactive visual landing page")
            print(f"  {BOLD}8.{RESET} ❓ {BOLD}Help{RESET}         - Display full list of CLI commands")
            print(f"{BOLD}{CYAN}======================================================================{RESET}")
            prompt = f"Enter choice {BOLD}[1-8]{RESET} (default: 8): "
        try:
            choice = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

        dispatch_map = {
            "1": ("doctor", cmd_doctor),
            "2": ("setup", cmd_setup),
            "3": ("init-config", cmd_init_config),
            "4": ("lint", cmd_lint),
            "5": ("verify", cmd_verify),
            "6": ("export-excel", cmd_export_excel),
            "7": ("welcome", cmd_welcome),
        }
        if choice in dispatch_map:
            subcmd, handler = dispatch_map[choice]
            args.subcommand = subcmd
            return handler(args)

    parser.print_help()
    show_all = getattr(args, "show_all", False) or "--all" in sys.argv or "-a" in sys.argv
    if show_all:
        print(f"\n💡 {t('tip_welcome', lang=parser.lang)}")
    sys.exit(0)


def build_parser(active_lang: str) -> SynapseArgumentParser:
    """Builds and configures the root SynapseArgumentParser with all arguments and subcommands."""
    parser = SynapseArgumentParser(
        prog="agent-qa",
        description=t("hub_cli_description", lang=active_lang),
        lang=active_lang
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Agent-QA Hub CLI v{_hub_version()}",
        help=t("opt_version", lang=parser.lang)
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        dest="show_all",
        help=t("opt_all", lang=parser.lang)
    )
    parser.add_argument(
        "--offline", "--offline-deterministic",
        action="store_true",
        dest="offline",
        help=t("opt_offline", lang=parser.lang).replace("%", "%%")
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        dest="quiet",
        help=t("opt_quiet", lang=parser.lang)
    )
    parser.add_argument(
        "-l", "--lang",
        choices=["en", "vi"],
        type=str.lower,
        default=None,
        dest="lang",
        help=t("opt_lang", lang=parser.lang)
    )
    subparsers = parser.add_subparsers(
        dest="subcommand",
        help=t("subcommands_help", lang=parser.lang),
        parser_class=lambda **kw: SynapseArgumentParser(lang=parser.lang, **kw)
    )

    # Modular command registration (Refactored Command Dispatcher Pattern)
    _register_core_and_setup_commands(subparsers, lang=parser.lang)
    _register_testing_and_execution_commands(subparsers, lang=parser.lang)
    _register_audit_and_inspection_commands(subparsers, lang=parser.lang)
    _register_platform_and_tools_commands(subparsers, lang=parser.lang)
    return parser


def main():
    cli_lang = _extract_cli_lang()
    if cli_lang:
        try:
            persist_language_preference(cli_lang)
        except Exception as _err:
            _ = _err
    active_lang = resolve_language(cli_lang)
    parser = build_parser(active_lang)
    args, unknown = parser.parse_known_args()
    if getattr(args, "offline", False):
        os.environ["AGENT_QA_OFFLINE"] = "1"
        if active_lang == "vi":
            print("🔒 [CHẾ ĐỘ OFFLINE] Chế độ cục bộ 100% không mạng. Sử dụng AST & Heuristics nội bộ.")
        else:
            print("🔒 [OFFLINE MODE] Air-Gapped Deterministic Mode Active. 100% Local AST & Heuristics (Zero External API calls).")
    if getattr(args, "show_all", False) or "--all" in sys.argv or "-a" in sys.argv:
        parser.print_help()
        print(f"\n💡 {t('tip_welcome', lang=parser.lang)}")
        return
    if cli_lang and not args.subcommand and not unknown:
        cfg_path = persist_language_preference(cli_lang)
        lang_names = {
            "en": "English" if cli_lang == "en" else "Tiếng Anh",
            "vi": "Vietnamese" if cli_lang == "en" else "Tiếng Việt"
        }
        lang_name = lang_names.get(cli_lang, cli_lang)
        print(t("lang_saved", lang=cli_lang, lang_name=lang_name, lang_code=cli_lang, config_path=cfg_path))
        print(f"\n{t('tip_lang_switch', lang=cli_lang)}")
        return
    if not args.subcommand:
        if unknown:
            parser.error(f"unrecognized arguments: {' '.join(unknown)}")
        return _handle_interactive_wizard(parser, args)
    if args.subcommand == "help":
        args._parser = parser

    from author_integrity import assert_integrity_or_raise
    assert_integrity_or_raise()

    if getattr(args, "quiet", False):
        os.environ["SYNAPSE_QUIET"] = "1"
    elif args.subcommand not in ("update", "mcp-serve", "version", "help"):
        try:
            import update_sentinel
            update_sentinel.check_for_updates(force=False, notify=True)
        except (ImportError, OSError, TimeoutError):
            _ = False
    args.func(args)


if __name__ == "__main__":
    main()
