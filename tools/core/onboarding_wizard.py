#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/core/onboarding_wizard.py — Interactive Onboarding & Role-Based Persona Dispatcher
------------------------------------------------------------------------------------------
Provides a guided, zero-friction interactive onboarding wizard for Synapse Hub.
Detects developer environment capabilities, prompts for target testing persona,
and synthesizes personalized quick-start recommendations with zero cognitive overload.
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

import json
import shutil
import argparse
import subprocess
from typing import Dict, Any, Optional

# Enforce UTF-8 stdout encoding for cross-platform compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HUB_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

ROLES = {
    "manual": {
        "title_vi": "👔 Manual QA / QC (Zero-Code)",
        "title_en": "👔 Manual QA / QC (Zero-Code)",
        "desc_vi": "Thiết kế test case, kiểm tra logic yêu cầu, xuất Excel 12 cột và chuyển test case Markdown sang Clean POM.",
        "desc_en": "Design test cases, verify requirements, export 12-column Excel sheets, and transpile Markdown test specs to Clean POM.",
        "skills": ["rbt-manual-testing", "manual-qa-and-rtm-bridge", "gherkin-to-suite"],
        "recommended_commands": [
            {"cmd": "agent-qa export-excel", "desc_vi": "Xuất template Excel 12 cột chuẩn Enterprise", "desc_en": "Export 12-column enterprise Excel test case template"},
            {"cmd": "agent-qa scaffold-tc testcase.md --out tests/e2e/", "desc_vi": "Chuyển test case Markdown sang mã Clean POM", "desc_en": "Scaffold Markdown test specs into Clean POM code"},
            {"cmd": "agent-qa ui", "desc_vi": "Mở Web Studio trực quan trên trình duyệt", "desc_en": "Launch visual Web Studio in your browser"}
        ]
    },
    "starter": {
        "title_vi": "🎓 Junior Automation Engineer (Playwright / Pytest)",
        "title_en": "🎓 Junior Automation Engineer (Playwright / Pytest)",
        "desc_vi": "Khởi tạo dự án test Clean POM trong 5s, tự bắt test giả và tự động sửa sleep tĩnh.",
        "desc_en": "Bootstrap Clean POM projects in 5s, catch fake-passes, and auto-fix hard static sleeps.",
        "skills": ["clean-pom-crafter", "e2e-testing-patterns", "playwright-webapp-testing"],
        "recommended_commands": [
            {"cmd": "agent-qa new my-tests --template playwright --profile starter", "desc_vi": "Tạo dự án kiểm thử Playwright mẫu siêu tốc", "desc_en": "Scaffold starter Playwright test project in seconds"},
            {"cmd": "agent-qa lint", "desc_vi": "Quét bắt lỗi test pass ảo / sleep cứng ngay lập tức", "desc_en": "Scan AST catching fake-passes and hard sleeps"},
            {"cmd": "agent-qa fix", "desc_vi": "Tự động sửa nhanh lỗi sleep cứng và unawaited expect", "desc_en": "Auto-fix static sleeps and unawaited expect assertions"}
        ]
    },
    "sdet": {
        "title_vi": "⚡ Senior SDET / Performance & Resilience",
        "title_en": "⚡ Senior SDET / Performance & Resilience",
        "desc_vi": "Chạy Micro-Mutation testing, tự phục hồi locator, kiểm thử Core Web Vitals và phát hiện flaky test.",
        "desc_en": "Run micro-mutation tests, auto-heal broken locators, audit Core Web Vitals, and quarantine flaky tests.",
        "skills": ["failure-autopsy-and-healing", "flaky-test-sentinel-and-quarantine", "self-healing-locator", "backend-load-and-stress-patterns"],
        "recommended_commands": [
            {"cmd": "agent-qa mutate tests/", "desc_vi": "Bơm đột biến kiểm tra độ nhạy của assertions (Kill rate >= 80%)", "desc_en": "Inject AST mutants to verify assertion sensitivity (Kill rate >= 80%)"},
            {"cmd": "agent-qa heal reports/junit.xml", "desc_vi": "Tự chẩn đoán và sửa locator gãy từ báo cáo JUnit XML", "desc_en": "Diagnose and auto-heal broken locators from JUnit XML"},
            {"cmd": "agent-qa flaky --quarantine", "desc_vi": "Cách ly và đo lường non-deterministic flaky tests", "desc_en": "Detect and quarantine non-deterministic flaky tests"}
        ]
    },
    "architect": {
        "title_vi": "🏛️ AI QA Architect & Tech Lead",
        "title_en": "🏛️ AI QA Architect & Tech Lead",
        "desc_vi": "Điều phối Swarm 9 subagents FSM, gác 10 cổng chất lượng DoD, nén log 95% và đồng bộ hóa quy tắc AI.",
        "desc_en": "Orchestrate 9-agent FSM Swarm, enforce 10 Quality Gates DoD, compress 95% logs, and sync AI rules.",
        "skills": ["actor-qa-swarm", "verification-before-completion", "repo-quality-audit", "token-and-context-optimizer"],
        "recommended_commands": [
            {"cmd": "python tools/core/verify_all.py --mode hub", "desc_vi": "Chạy kiểm định toàn diện 10 cổng chất lượng DoD", "desc_en": "Run full 10 Quality Gates DoD verification"},
            {"cmd": "agent-qa distill build.log", "desc_vi": "Nén 95% log CI dài hàng nghìn dòng thành stacktrace gốc", "desc_en": "Compress CI logs by 95% down to root causes"},
            {"cmd": "python tools/core/sync_agent_rules.py", "desc_vi": "Đồng bộ hóa quy tắc sang Cursor, Claude, Antigravity, Copilot", "desc_en": "Sync core rules across Cursor, Claude, Antigravity, Copilot"}
        ]
    }
}


def probe_environment() -> Dict[str, Any]:
    """Inspects underlying environment tools and runtimes."""
    node_v = None
    if shutil.which("node"):
        try:
            res = subprocess.run(["node", "-v"], capture_output=True, text=True, timeout=3)
            node_v = res.stdout.strip()
        except (subprocess.SubprocessError, OSError) as err:
            sys.stderr.write(f"Notice: node probe failed: {err}\n")
            node_v = None

    python_v = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    git_v = None
    if shutil.which("git"):
        try:
            res = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=3)
            git_v = res.stdout.strip()
        except (subprocess.SubprocessError, OSError) as err:
            sys.stderr.write(f"Notice: git probe failed: {err}\n")
            git_v = None

    has_chrome = bool(shutil.which("google-chrome") or shutil.which("chrome") or os.path.exists("/Applications/Google Chrome.app"))
    has_playwright = bool(shutil.which("playwright") or shutil.which("npx"))

    return {
        "python": python_v,
        "node": node_v,
        "git": git_v,
        "chrome_installed": has_chrome,
        "playwright_ready": has_playwright,
    }


def run_onboarding(role_key: Optional[str] = None, lang: str = "vi", as_json: bool = False, interactive: bool = False) -> int:
    """Executes onboarding wizard and outputs tailored quickstart guide."""
    env_info = probe_environment()

    if not role_key and interactive:
        print("\n" + "=" * 65)
        print("🚀 SYNAPSE HUB — INTERACTIVE ONBOARDING WIZARD")
        print("   " + ("Chọn vai trò của bạn để nhận lộ trình phù hợp nhất:" if lang == "vi" else "Select your role to get a tailored quickstart guide:"))
        print("=" * 65)
        keys = list(ROLES.keys())
        for idx, k in enumerate(keys, 1):
            r = ROLES[k]
            title = r["title_vi"] if lang == "vi" else r["title_en"]
            desc = r["desc_vi"] if lang == "vi" else r["desc_en"]
            print(f" [{idx}] {title}")
            print(f"     -> {desc}")
        try:
            choice = input("\n👉 " + ("Nhập lựa chọn (1-4) [mặc định: 2]: " if lang == "vi" else "Enter choice (1-4) [default: 2]: ")).strip()
            if choice in ("1", "2", "3", "4"):
                role_key = keys[int(choice) - 1]
            else:
                role_key = "starter"
        except (KeyboardInterrupt, EOFError):
            print("\n")
            return 1

    if not role_key or role_key not in ROLES:
        role_key = "starter"

    chosen = ROLES[role_key]
    title = chosen["title_vi"] if lang == "vi" else chosen["title_en"]
    desc = chosen["desc_vi"] if lang == "vi" else chosen["desc_en"]

    if as_json:
        data = {
            "role": role_key,
            "title": title,
            "description": desc,
            "skills": chosen["skills"],
            "environment": env_info,
            "recommendations": [
                {
                    "command": item["cmd"],
                    "description": item["desc_vi"] if lang == "vi" else item["desc_en"]
                }
                for item in chosen["recommended_commands"]
            ]
        }
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    print("\n" + "═" * 70)
    print(f"✨ CHÀO MỪNG BẠN ĐẾN VỚI SYNAPSE HUB (PROFILE: {role_key.upper()})")
    print("═" * 70)
    print(f"🏷️  Vai trò: {title}")
    print(f"💡 Mục tiêu: {desc}\n")

    print("🔍 Môi trường phát hiện được:")
    print(f"   • Python       : {env_info['python']} (OK)")
    print(f"   • Node.js      : {env_info['node'] or 'Chưa cài đặt (Khuyên dùng v18+)'}")
    print(f"   • Git          : {env_info['git'] or 'Chưa cài đặt'}")
    print(f"   • Trình duyệt  : {'Sẵn sàng (Chrome)' if env_info['chrome_installed'] else 'Chưa phát hiện Chrome'}\n")

    print("🚀 3 BƯỚC BẮT ĐẦU NHANH NHẤT (Copy & Chạy ngay):")
    for i, cmd_info in enumerate(chosen["recommended_commands"], 1):
        cmd_desc = cmd_info["desc_vi"] if lang == "vi" else cmd_info["desc_en"]
        print(f"  {i}. {cmd_desc}:")
        print(f"     \033[92m{cmd_info['cmd']}\033[0m")

    print("\n📚 Tài liệu & Hướng dẫn đầy đủ:")
    print("   • Hướng dẫn chi tiết : README.md / README.en.md")
    print("   • Cẩm nang công cụ   : tools/TOOLS_RUNBOOK.md")
    print("   • Web Studio trực quan: agent-qa ui (hoặc npx @teevee98/synapse-hub ui)")
    print("═" * 70 + "\n")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Synapse Hub Guided Onboarding & Persona Setup Wizard"
    )
    parser.add_argument(
        "--role",
        choices=["manual", "starter", "sdet", "architect"],
        default=None,
        help="Select target role (manual, starter, sdet, architect)"
    )
    parser.add_argument(
        "--lang",
        choices=["vi", "en"],
        default="vi",
        help="Language for onboarding guide (default: vi)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON configuration"
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run without prompting (defaults to starter profile)"
    )

    args = parser.parse_args()
    interactive = not args.non_interactive and args.role is None
    return run_onboarding(
        role_key=args.role,
        lang=args.lang,
        as_json=args.json,
        interactive=interactive
    )


if __name__ == "__main__":
    sys.exit(main())
