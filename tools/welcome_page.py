#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tools/welcome_page.py — Interactive Visual Landing Page for Synapse Hub
-------------------------------------------------------------------------
Generates and automatically launches a modern, responsive, 100% self-contained
HTML5 product landing page that introduces Synapse Hub's capabilities across
Manual, Automation, API, and Performance testing.

Features:
  - Default Vietnamese interface with instant 1-click English toggle (bilingual i18n).
  - 100% air-gapped & offline-ready (Zero external CDNs or remote dependencies).
  - Dark glassmorphism interface with responsive layout.
  - Interactive tabs covering the 4 Core Pillars of QA Intelligence.
  - Interactive CLI Cheatsheet with 1-click clipboard copy.
  - Comparison matrix vs existing industry tools (ESLint, Stryker, Allure, Healenium).
  - 6 Subagent Swarm Profiles & 9 Quality Gates DoD showcase.
  - Automatic browser launching on setup, pull, or CLI dispatch.
"""

import os
import sys
import json
import html as html_lib
import argparse
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HUB_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
FIRST_RUN_MARKER_FILENAME = ".welcome_shown"


def get_hub_metadata() -> Dict[str, Any]:
    """Retrieves version and catalog count from skills_manifest.json."""
    manifest_path = os.path.join(HUB_ROOT, "skills_manifest.json")
    meta = {
        "version": "2.4.1",
        "totalSkills": 38,
        "author": "Thế Vị (@TeeVee998)",
        "repo": "https://github.com/TeeVee998/Synapse-Hub"
    }
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                meta["version"] = data.get("version", meta["version"])
                meta["totalSkills"] = data.get("totalSkills", meta["totalSkills"])
        except (OSError, json.JSONDecodeError):
            pass
    return meta


def is_hub_repo(path_str: Optional[str]) -> bool:
    """Checks whether the given path corresponds to the Synapse-Hub core repository itself."""
    if not path_str:
        return True
    resolved = os.path.abspath(path_str)
    if resolved.lower() == HUB_ROOT.lower():
        return True
    if os.path.exists(os.path.join(resolved, "skills_manifest.json")) or os.path.isdir(os.path.join(resolved, ".agents", "skills")):
        return True
    return False


def generate_welcome_html(target_repo: Optional[str] = None, stack_info: Optional[Dict[str, str]] = None, default_lang: str = "vi") -> str:
    """Renders the standalone interactive HTML5 landing page with bilingual language switcher."""
    meta = get_hub_metadata()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    is_external_target = bool(target_repo and not is_hub_repo(target_repo) and stack_info)
    if is_external_target:
        raw_target_name = (stack_info.get("name") if stack_info else "") or os.path.basename(os.path.abspath(target_repo))
        raw_framework = (stack_info.get("framework") if stack_info else "") or "Automated QA"
        target_name = html_lib.escape(str(raw_target_name))
        framework_name = html_lib.escape(str(raw_framework))
        hero_pill_content = f"""<span data-i18n="hero_pill_tag">🛡️ Trung Tâm Trí Tuệ Chất Lượng AI Doanh Nghiệp</span>
                <span>&bull;</span>
                <span><span data-i18n="hero_target_label">Dự án mục tiêu</span>: <strong>{target_name}</strong> ({framework_name})</span>"""
    else:
        hero_pill_content = """<span data-i18n="hero_pill_tag">🛡️ Trung Tâm Trí Tuệ Chất Lượng AI Doanh Nghiệp</span>
                <span>&bull;</span>
                <span data-i18n="hero_pill_status">Sẵn Sàng 100% Offline</span>"""

    tmpl_candidates = [
        os.path.join(HUB_ROOT, "templates", "welcome.html.tmpl"),
        os.path.join(SCRIPT_DIR, "..", "templates", "welcome.html.tmpl"),
        os.path.join(SCRIPT_DIR, "templates", "welcome.html.tmpl"),
    ]
    template_str = None
    for cand in tmpl_candidates:
        if os.path.exists(cand):
            try:
                with open(cand, "r", encoding="utf-8") as tf:
                    template_str = tf.read()
                    break
            except OSError:
                pass

    if not template_str:
        return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Synapse Hub</title></head>
<body style="font-family:sans-serif;background:#0f172a;color:#f8fafc;padding:40px;text-align:center;">
<h1>🛡️ Synapse Hub Enterprise QA v{meta.get('version', '2.4.0')}</h1>
<p>{hero_pill_content}</p>
<p>Total Standardized Skills: {meta.get('totalSkills', 38)}</p>
<p>Author: {meta.get('author', 'Thế Vị (@TeeVee998)')}</p>
</body></html>"""

    rendered_html = (
        template_str.replace("__DEFAULT_LANG__", default_lang)
        .replace("__HERO_PILL_CONTENT__", hero_pill_content)
        .replace("__NOW_STR__", now_str)
        .replace("__VERSION__", str(meta.get("version", "2.4.0")))
        .replace("__AUTHOR__", str(meta.get("author", "Thế Vị (@TeeVee998)")))
        .replace("__TOTAL_SKILLS__", str(meta.get("totalSkills", 38)))
        .replace("__REPO__", str(meta.get("repo", "https://github.com/TeeVee998/Synapse-Hub")))
    )
    return rendered_html


def write_welcome_page(output_path: Optional[str] = None, target_repo: Optional[str] = None, stack_info: Optional[Dict[str, str]] = None, default_lang: str = "vi") -> str:
    """Generates and writes the welcome landing page to disk."""
    if not output_path:
        base_dir = target_repo if target_repo else HUB_ROOT
        reports_dir = os.path.join(base_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        output_path = os.path.join(reports_dir, "WELCOME.html")
    else:
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    html_content = generate_welcome_html(target_repo=target_repo, stack_info=stack_info, default_lang=default_lang)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_path


def get_marker_path(target_repo: Optional[str] = None) -> str:
    """Returns the path to the .welcome_shown marker file for the given repository."""
    base = target_repo if target_repo else HUB_ROOT
    return os.path.join(base, "reports", FIRST_RUN_MARKER_FILENAME)


def is_first_run(target_repo: Optional[str] = None) -> bool:
    """
    Checks whether this is the first install / first pull for the hub.
    Returns True if the welcome page has not been displayed yet.
    """
    marker_path = get_marker_path(target_repo)
    if os.path.exists(marker_path):
        return False

    global_dir = os.path.expanduser("~/.agent_memory")
    global_marker = os.path.join(global_dir, "welcome_shown.json")
    if os.path.exists(global_marker):
        try:
            with open(global_marker, "r", encoding="utf-8") as f:
                data = json.load(f)
                key = os.path.realpath(target_repo or HUB_ROOT)
                if key in data:
                    return False
        except (OSError, json.JSONDecodeError):
            pass

    return True


def mark_first_run_completed(target_repo: Optional[str] = None):
    """
    Records that the landing page has been shown so it does not open again.
    """
    marker_path = get_marker_path(target_repo)
    try:
        os.makedirs(os.path.dirname(marker_path), exist_ok=True)
        with open(marker_path, "w", encoding="utf-8") as f:
            json.dump({
                "shown_at": datetime.now().isoformat(),
                "repo": os.path.realpath(target_repo or HUB_ROOT)
            }, f, indent=2)
    except OSError:
        pass

    try:
        global_dir = os.path.expanduser("~/.agent_memory")
        os.makedirs(global_dir, exist_ok=True)
        global_marker = os.path.join(global_dir, "welcome_shown.json")
        data = {}
        if os.path.exists(global_marker):
            try:
                with open(global_marker, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                data = {}
        key = os.path.realpath(target_repo or HUB_ROOT)
        data[key] = datetime.now().isoformat()
        with open(global_marker, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


def open_welcome_page(file_path: str) -> bool:
    """
    Opens the welcome page in the user's default browser if not running in headless/CI mode or test runner.
    Returns True if successfully launched, False otherwise.
    """
    if (
        os.environ.get("CI")
        or os.environ.get("HEADLESS")
        or os.environ.get("AGENT_QA_NO_BROWSER")
        or "unittest" in sys.modules
        or "pytest" in sys.modules
    ):
        return False

    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        return False

    file_url = f"file://{abs_path}"
    try:
        webbrowser.open(file_url)
        return True
    except Exception:
        return False


def generate_welcome_page(target_repo: Optional[str] = None, output_path: Optional[str] = None, stack_info: Optional[Dict[str, str]] = None, open_browser: bool = True, default_lang: str = "vi") -> str:
    """
    Full workflow helper: generates the landing page and opens it if requested.
    """
    out_file = write_welcome_page(output_path=output_path, target_repo=target_repo, stack_info=stack_info, default_lang=default_lang)
    if open_browser:
        opened = open_welcome_page(out_file)
        if opened:
            print(f"  🚀 Đã mở Visual Landing Page trong trình duyệt của bạn.")
    return out_file


def main():
    parser = argparse.ArgumentParser(description="Synapse Hub Visual Landing Page Generator (Bilingual VI/EN)")
    parser.add_argument("target", nargs="?", default=None, help="Target repository directory (default: current directory)")
    parser.add_argument("--output", "-o", default=None, help="Output HTML file path (default: reports/WELCOME.html)")
    parser.add_argument("--lang", choices=["vi", "en"], default="vi", help="Default initial language (default: vi = Vietnamese)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser after generating the page")
    parser.add_argument("--open", action="store_true", help="Explicitly open the browser")
    parser.add_argument("--first-run", action="store_true", help="Only generate and open if running for the first time (e.g. npm install or first pull)")
    args = parser.parse_args()

    target_dir = os.path.abspath(args.target) if args.target else HUB_ROOT

    # If --first-run requested, check if it was already displayed
    if args.first_run:
        if not is_first_run(target_dir):
            return

    should_open = not args.no_browser if (not os.environ.get("CI")) else args.open
    if args.first_run and (os.environ.get("CI") or os.environ.get("HEADLESS") or "unittest" in sys.modules or "pytest" in sys.modules):
        should_open = False

    print(f"🎨 Generating Synapse Hub Visual Landing Page (Language: {args.lang.upper()})...")
    out_path = generate_welcome_page(
        target_repo=target_dir,
        output_path=args.output,
        open_browser=should_open,
        default_lang=args.lang
    )
    if args.first_run or should_open:
        mark_first_run_completed(target_dir)

    print(f"✅ Landing page generated successfully at:\n   file://{out_path}")
    print(f"👉 You can re-open it anytime with: npx synapse-hub welcome")


if __name__ == "__main__":
    main()
