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

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass

import os
import sys
import json
import re
import difflib
import argparse
from typing import Any, Optional

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
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

def _resolve_manifest_path(repo_root: Optional[str] = None) -> Optional[str]:
    """
    Fallback manifest resolution:
      1. REPO_ROOT/skills_manifest.json
      2. tools/skills_manifest.json
      3. importlib.resources.files("tools").joinpath("skills_manifest.json")
    """
    root = repo_root or REPO_ROOT
    candidate1 = os.path.join(root, "skills_manifest.json")
    if os.path.isfile(candidate1):
        return candidate1
    candidate2 = os.path.join(SCRIPT_DIR, "skills_manifest.json")
    if os.path.isfile(candidate2):
        return candidate2
    candidate2_alt = os.path.join(root, "tools", "skills_manifest.json")
    if os.path.isfile(candidate2_alt):
        return candidate2_alt
    try:
        import importlib.resources as pkg_resources
        resource = pkg_resources.files("tools").joinpath("skills_manifest.json")
        if resource.is_file():
            try:
                r_str = str(resource)
                if os.path.isfile(r_str):
                    return r_str
            except (TypeError, ValueError) as str_err:
                res_str_err = str(str_err)
            with pkg_resources.as_file(resource) as p:
                return str(p)
    except (ImportError, AttributeError, TypeError) as res_err:
        res_load_err = str(res_err)
    return None

def cmd_version(args):
    """Displays the current hub version, skill catalog count, and license information."""
    manifest_path = _resolve_manifest_path()
    version = "4.10.0"
    manifest_skills = 56
    if manifest_path and os.path.exists(manifest_path):
        try:
            import json
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                version = data.get("version", version)
                manifest_skills = data.get("totalSkills", manifest_skills)
        except (OSError, json.JSONDecodeError) as json_err:
            manifest_err = str(json_err)
    print(f"Agent-QA Hub CLI v{version}")
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

# Declarative Lazy-Import Subcommand Registry (replaces 121 repetitive cmd_* wrappers)

def _load_cli_bundle() -> dict[str, Any]:
    """Loads declarative CLI registry, highlights, and command parser specs from cli_specs.json."""
    spec_path = os.path.join(SCRIPT_DIR, "cli_specs.json")
    with open(spec_path, "r", encoding="utf-8") as sf:
        return json.load(sf)

_CLI_BUNDLE = _load_cli_bundle()
SUBCOMMAND_REGISTRY: dict[str, tuple[str, str, str]] = {
    k: (v[0], v[1], v[2]) for k, v in _CLI_BUNDLE["registry"].items()
}
CORE_COMMAND_SPECS = [tuple(x) for x in _CLI_BUNDLE["core_commands"]]
ADVANCED_HIGHLIGHT_SPECS = [tuple(x) for x in _CLI_BUNDLE["advanced_highlights"]]

def _make_lazy_handler(module_path: str, entrypoint: str = 'main'):
    """Creates a lazy-import CLI subcommand handler forwarding arguments to module.entrypoint()."""
    def _handler(args):
        import importlib
        mod = importlib.import_module(module_path)
        fn = getattr(mod, entrypoint)
        sys.argv = _forward_subcommand_args(args)
        res = fn()
        sys.exit(res if isinstance(res, int) else 0)
    _handler.__name__ = f'lazy_{module_path.split(".")[-1]}'
    return _handler

def _dispatch(cmd_name: str):
    """Returns a lazy CLI handler for a registered subcommand name (static-AST F821 safe)."""
    mod_path, ep, _tier = SUBCOMMAND_REGISTRY[cmd_name]
    return _make_lazy_handler(mod_path, ep)

for _cmd_name, (_mod_path, _ep, _tier) in SUBCOMMAND_REGISTRY.items():
    globals()[_cmd_name] = _make_lazy_handler(_mod_path, _ep)

def cmd_fix(args):
    """Automatically fixes common test defects (hard sleep, unawaited expect, swallowed catch)."""
    from infer_linter import main as lint_main
    forwarded = _forward_subcommand_args(args)
    if "--fix" not in forwarded:
        forwarded.append("--fix")
    sys.argv = forwarded
    sys.exit(lint_main())


CORE_12_COMMANDS: tuple[str, ...] = (
    "lint",
    "fix",
    "verify",
    "mutate",
    "distill",
    "analyze",
    "export-excel",
    "scaffold-tc",
    "mcp-serve",
    "lsp",
    "doctor",
    "new",
)

_CLI_FALLBACK_HELP = {
    "cmd_lsp": {
        "en": "Start the JSON-RPC 2.0 stdio Universal QA Language Server (JetBrains/Neovim/VS Code)",
        "vi": "Khoi dong Universal QA Language Server (LSP 3.17 stdio cho JetBrains/Neovim/VS Code)",
    },
    "cmd_lab": {
        "en": "Access ~180 specialized contrib/research commands (`synapse lab --list` or `synapse lab <cmd>`)",
        "vi": "Truy cap ~180 lenh chuyen sau/nghien cuu (`synapse lab --list` hoac `synapse lab <cmd>`)",
    },
    "cmd_fpr_bench": {
        "en": "Run empirical real-world False-Positive Rate (FPR <= 5.0%) & latency benchmark",
        "vi": "Chay benchmark ty le canh bao gia (FPR <= 5.0%) va do tre thuc te",
    },
}


def cmd_lsp(args):
    """Starts the zero-dependency Universal QA Language Server (LSP 3.17 over stdio)."""
    import importlib
    mod = importlib.import_module("tools.mcp.qa_lsp_server")
    sys.argv = _forward_subcommand_args("lsp")
    res = mod.main()
    sys.exit(res if isinstance(res, int) else 0)


def cmd_fpr_bench(args):
    """Runs the empirical real-world False-Positive Rate & latency benchmark runner."""
    import importlib
    mod = importlib.import_module("benchmarks.real_world_fpr_runner")
    sys.argv = _forward_subcommand_args("fpr-bench")
    res = mod.main()
    sys.exit(res if isinstance(res, int) else 0)


def cmd_lab(args):
    """Two-tier router exposing specialized contrib/research tools via `synapse lab <cmd>`."""
    core_set = set(CORE_12_COMMANDS) | {"lab", "help", "version"}
    lab_specs = [
        spec for spec in _CLI_BUNDLE.get("commands", [])
        if spec.get("name") not in core_set
    ]
    lab_names = sorted(spec["name"] for spec in lab_specs)

    target_cmd = getattr(args, "lab_cmd", None)
    list_flag = bool(getattr(args, "list_lab", False))
    json_flag = bool(getattr(args, "json_output", False))

    if list_flag or not target_cmd:
        payload = {
            "core_commands_count": len(CORE_12_COMMANDS),
            "lab_commands_count": len(lab_names),
            "legacy_aliases_preserved": True,
            "lsp_registered": any(s.get("name") == "lsp" for s in _CLI_BUNDLE.get("commands", [])),
            "core_commands": list(CORE_12_COMMANDS),
            "lab_commands": lab_names,
        }
        if json_flag:
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        print(f"\n{BOLD}{CYAN}Synapse Hub Lab — Specialized & Research Commands ({len(lab_names)} available){RESET}")
        print("Usage: synapse lab <command> [args...]  (all legacy top-level aliases remain 100% active)\n")
        for idx in range(0, len(lab_names), 4):
            row = "  ".join(f"{name:<22}" for name in lab_names[idx:idx + 4])
            print(f"  {row}")
        print()
        return 0

    # Resolve target command or alias against declarative command table
    matched_spec = None
    for spec in _CLI_BUNDLE.get("commands", []):
        if spec.get("name") == target_cmd or target_cmd in spec.get("aliases", []):
            matched_spec = spec
            break
    if matched_spec is None:
        sys.stderr.write(f"[ERROR] Unknown lab command: '{target_cmd}'. Run 'synapse lab --list' to view available tools.\n")
        sys.exit(2)

    handler_name = matched_spec["handler"]
    handler_fn = globals().get(handler_name) or _dispatch(handler_name)
    extra_args = list(getattr(args, "lab_args", None) or [])
    sys.argv = [sys.argv[0], target_cmd] + _strip_interface_lang_flags(extra_args)
    args.subcommand = target_cmd
    res = handler_fn(args)
    sys.exit(res if isinstance(res, int) else 0)

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

def cmd_uninstall(args):
    """Reverts and cleans configuration files and Git hooks installed by setup in target project."""
    from setup_project import uninstall_setup, resolve_target_repo
    target = getattr(args, "target", None)
    target_repo = resolve_target_repo(cli_target=target)
    sys.exit(uninstall_setup(target_repo))

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

def cmd_new(args):
    """Scaffolds a new QA test project from standardized templates in 5 seconds."""
    try:
        from tools.core.scaffold import main as scaffold_main
    except ImportError:
        from scaffold import main as scaffold_main
    sys.argv = _forward_subcommand_args(args)
    sys.exit(scaffold_main())

def get_registered_commands(parser: Optional[argparse.ArgumentParser] = None, lang: str = "en") -> list[dict[str, Any]]:
    """
    Dynamically introspects the CLI parser subparsers action and extracts
    all registered commands, aliases, and localized descriptions directly from the registry.
    """
    if parser is None:
        parser = build_parser(lang)

    subparsers_action = None
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            subparsers_action = action
            break

    if not subparsers_action:
        return []

    help_map = {a.dest: a.help for a in getattr(subparsers_action, "_choices_actions", [])}

    commands = []
    seen_parsers = set()
    for name, subp in subparsers_action.choices.items():
        if id(subp) in seen_parsers:
            continue
        seen_parsers.add(id(subp))
        aliases = [n for n, s in subparsers_action.choices.items() if s is subp and n != name]
        help_text = help_map.get(name) or getattr(subp, "description", None) or getattr(subp, "help", "") or ""
        commands.append({
            "name": name,
            "aliases": aliases,
            "help": help_text,
            "prog": getattr(subp, "prog", f"agent-qa {name}"),
        })
    commands.sort(key=lambda c: c["name"])
    return commands

def cmd_help(args):
    """Displays command-line help and usage documentation."""
    parser = getattr(args, "_parser", None)
    if not parser:
        lang = getattr(args, "lang", None) or resolve_language(_extract_cli_lang())
        parser = build_parser(lang)

    lang = getattr(parser, "lang", "en")

    if getattr(args, "json_output", False):
        commands = get_registered_commands(parser, lang)
        print(json.dumps(commands, indent=2, ensure_ascii=False))
        sys.exit(0)

    if getattr(args, "md_output", False):
        commands = get_registered_commands(parser, lang)
        lines = [
            "| Command | Aliases | Description |",
            "| :--- | :--- | :--- |",
        ]
        for cmd in commands:
            aliases_str = ", ".join(f"`{a}`" for a in cmd["aliases"]) if cmd["aliases"] else "—"
            desc = cmd["help"].replace("\n", " ").strip()
            lines.append(f"| `{cmd['name']}` | {aliases_str} | {desc} |")
        print("\n".join(lines))
        sys.exit(0)

    if parser:
        parser.print_help()
        sys.exit(0)
    print("Run 'agent-qa --help' to view command-line usage.")
    sys.exit(0)

def cmd_update(args):
    import update_sentinel
    if getattr(args, "auto", False):
        update_sentinel.run_auto_update_hook()
        sys.exit(0)
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

def cmd_release(args):
    """1-Click atomic release: bumps version across all files, runs 11 Quality Gates, tags & pushes to trigger NPM/PyPI Trusted Publishing."""
    from bump_version import main as bump_main
    forwarded = _forward_subcommand_args(args)
    if "--no-push" not in forwarded and "--push" not in forwarded:
        forwarded.append("--push")
    if "--commit" not in forwarded and "--no-commit" not in forwarded:
        forwarded.append("--commit")
    sys.argv = forwarded
    sys.exit(bump_main())

def cmd_ui(args):
    """Launches the interactive QA Mission Control Web UI."""
    from tools.contrib.ui_server import run_server
    target = getattr(args, "target", None) or getattr(args, "repo", None)
    run_server(host=args.host, port=args.port, open_browser=not args.no_browser, target_dir=target)

def cmd_knowledge_lake(args):
    """Queries Federated Knowledge Lake patterns cleanly with bounded SQLite lifecycle."""
    from tools.core.federated_knowledge_lake import FederatedKnowledgeLake
    db_path = getattr(args, "db_path", None)
    query_text = getattr(args, "query", "") or ""
    with FederatedKnowledgeLake(db_path=db_path) as lake:
        matches = lake.query(search_text=query_text if query_text else None)
    payload = {"status": "OK", "query": query_text, "count": len(matches), "matches": matches}
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"Federated Knowledge Lake: {len(matches)} pattern(s) matched.")
    sys.exit(0)

def cmd_harvest_journey(args):
    """Clusters JSON telemetry events into Clean POM journeys without side effects."""
    from tools.core.journey_harvester import JourneyHarvester
    events_file = getattr(args, "events_file", "") or ""
    suite_name = getattr(args, "suite_name", "HarvestedJourney") or "HarvestedJourney"
    events = []
    if events_file:
        if not os.path.isfile(events_file):
            msg = f"Events file not found: {events_file}"
            if getattr(args, "json", False):
                print(json.dumps({"status": "ERROR", "error": msg}), file=sys.stderr)
            else:
                print(msg, file=sys.stderr)
            sys.exit(1)
        with open(events_file, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
            events = loaded if isinstance(loaded, list) else loaded.get("events", [])
    harvester = JourneyHarvester()
    ingested = harvester.ingest_events(events) if events else 0
    journeys = harvester.cluster_journeys() if ingested else []
    payload = {
        "status": "OK",
        "suite_name": suite_name,
        "events_ingested": ingested,
        "journeys_count": len(journeys),
    }
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"JourneyHarvester: ingested {ingested} events into {len(journeys)} journey(s).")
    sys.exit(0)

def cmd_grid(args):
    """Inspects SynapseGrid distributed execution readiness without blocking."""
    from tools.orchestration.synapse_grid import SynapseGrid
    workers = max(1, int(getattr(args, "workers", 2) or 2))
    grid = SynapseGrid(worker_count=workers)
    payload = {"status": "READY", "max_workers": grid.worker_count, "queued_tasks": len(grid.tasks)}
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2))
    else:
        print(f"SynapseGrid ready with {grid.worker_count} worker(s).")
    sys.exit(0)

def cmd_schedule(args):
    """Inspects QATaskScheduler tasks without starting background daemon loops."""
    from tools.orchestration.qa_task_scheduler import QATaskScheduler
    scheduler = QATaskScheduler()
    tasks = scheduler.list_tasks()
    payload = {"status": "READY", "task_count": len(tasks), "tasks": tasks}
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"QATaskScheduler ready ({len(tasks)} registered tasks).")
    sys.exit(0)

def cmd_flow(args):
    """Compiles and dry-runs a deterministic Synapse Flow StateGraph."""
    from tools.core.synapse_flow import END, StateGraph
    graph = StateGraph()
    graph.add_node("verify", lambda state: {**state, "verified": True})
    graph.set_entry_point("verify")
    graph.add_edge("verify", END)
    with graph.compile() as compiled:
        final_state = compiled.invoke({})
    payload = {"status": "OK", "state": final_state}
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"SynapseFlow compiled and verified: {final_state}")
    sys.exit(0)

def _hub_version():
    manifest_path = _resolve_manifest_path()
    version = "4.10.0"
    if manifest_path and os.path.exists(manifest_path):
        try:
            import json
            with open(manifest_path, "r", encoding="utf-8") as f:
                version = json.load(f).get("version", version)
        except (OSError, json.JSONDecodeError):
            version = "4.10.0"
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
        desc = t(msg_key, lang=lang)
        if desc == msg_key and msg_key in _CLI_FALLBACK_HELP:
            desc = _CLI_FALLBACK_HELP[msg_key].get(lang, _CLI_FALLBACK_HELP[msg_key]["en"])
        desc = desc.replace("10 Quality Gates", "11 Quality Gates").replace("10 Cổng Chất Lượng", "11 Cổng Chất Lượng")
        lines.append(f"  {BOLD}{GREEN}{cmd:<14}{RESET} {desc}")

    lines.append(f"\n{BOLD}{t('advanced_highlights_title', lang=lang)}{RESET}")
    for cmd, msg_key in ADVANCED_HIGHLIGHT_SPECS:
        desc = t(msg_key, lang=lang)
        if desc == msg_key and msg_key in _CLI_FALLBACK_HELP:
            desc = _CLI_FALLBACK_HELP[msg_key].get(lang, _CLI_FALLBACK_HELP[msg_key]["en"])
        lines.append(f"  {CYAN}{cmd:<14}{RESET} {desc}")

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
                    import logging
                    logging.getLogger("cli").debug("Argparse error formatting: %s", _err)

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

_TYPE_MAP = {"int": int, "float": float, "str": str}

def _resolve_spec_text(expr: Any, lang: str) -> Any:
    """Resolves localized help/description text from declarative cli_specs.json."""
    if isinstance(expr, dict):
        if "$t" in expr:
            val = t(expr["$t"], lang=lang)
        elif "$en" in expr:
            val = expr["$vi"] if lang == "vi" else expr["$en"]
        else:
            return expr
        return val.replace("%", "%%") if expr.get("$pct") else val
    return expr

def _resolve_spec_value(val: Any) -> Any:
    """Resolves symbolic defaults/types from declarative cli_specs.json."""
    if isinstance(val, str):
        if val.startswith("$") and val[1:] in _TYPE_MAP:
            return _TYPE_MAP[val[1:]]
        if val == "$cwd":
            return os.getcwd()
    return val

def _register_commands_from_specs(subparsers, group: Optional[str] = None, lang: Optional[str] = None):
    """Registers CLI subparsers declaratively from cli_specs.json."""
    active_lang = lang or resolve_language(_extract_cli_lang())
    for spec in _CLI_BUNDLE["commands"]:
        if group is not None and spec.get("group") != group:
            continue
        kw: dict[str, Any] = {}
        if "aliases" in spec:
            kw["aliases"] = spec["aliases"]
        if "help" in spec:
            kw["help"] = _resolve_spec_text(spec["help"], active_lang)
        if "description" in spec:
            kw["description"] = _resolve_spec_text(spec["description"], active_lang)
        sub_p = subparsers.add_parser(spec["name"], **kw)
        for arg in spec.get("args", []):
            flags = arg["flags"]
            akw = {}
            for k, v in arg.items():
                if k == "flags":
                    continue
                akw[k] = _resolve_spec_text(v, active_lang) if k == "help" else _resolve_spec_value(v)
            sub_p.add_argument(*flags, **akw)
        handler_name = spec["handler"]
        handler_fn = globals().get(handler_name) or _dispatch(handler_name)
        sub_p.set_defaults(func=handler_fn)

def _register_core_and_setup_commands(subparsers, lang: Optional[str] = None):
    """Registers core environment, setup, and informational subcommands."""
    _register_commands_from_specs(subparsers, group="core_and_setup", lang=lang)

def _register_testing_and_execution_commands(subparsers, lang: Optional[str] = None):
    """Registers QA execution, linting, mutation, healing, and CI gating subcommands."""
    _register_commands_from_specs(subparsers, group="testing_and_execution", lang=lang)

def _register_audit_and_inspection_commands(subparsers, lang: Optional[str] = None):
    """Registers codebase analysis, security audit, and artifact inspection subcommands."""
    _register_commands_from_specs(subparsers, group="audit_and_inspection", lang=lang)

def _register_platform_and_tools_commands(subparsers, lang: Optional[str] = None):
    """Registers protocol generators, converters, MCP servers, and utility subcommands."""
    _register_commands_from_specs(subparsers, group="platform_and_tools", lang=lang)

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
            print(f"  {BOLD}5.{RESET} 🛡️  {BOLD}Verify{RESET}       - Chạy kiểm tra 11 Cổng Chất Lượng DoD")
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
            print(f"  {BOLD}5.{RESET} 🛡️  {BOLD}Verify{RESET}       - Execute 11 Quality Gates Definition of Done (DoD)")
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
            "1": ("doctor", _dispatch("cmd_doctor")),
            "2": ("setup", _dispatch("cmd_setup")),
            "3": ("init-config", _dispatch("cmd_init_config")),
            "4": ("lint", _dispatch("cmd_lint")),
            "5": ("verify", _dispatch("cmd_verify")),
            "6": ("export-excel", _dispatch("cmd_export_excel")),
            "7": ("welcome", _dispatch("cmd_welcome")),
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
            import logging
            logging.getLogger("cli").debug("Failed to persist language preference: %s", _err)
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

    is_json_output = "--json" in sys.argv or getattr(args, "format", None) == "json"
    if getattr(args, "quiet", False):
        os.environ["SYNAPSE_QUIET"] = "1"
    elif args.subcommand not in ("update", "mcp-serve", "version", "help") and not is_json_output:
        try:
            import update_sentinel
            update_sentinel.check_for_updates(force=False, notify=True)
        except (ImportError, OSError, TimeoutError) as err:
            import logging
            logging.getLogger("cli").debug("Update check skipped: %s", err)
    args.func(args)

if __name__ == "__main__":
    main()
