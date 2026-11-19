#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/core/scaffold.py — Instant Project Scaffolding Engine
----------------------------------------------------------
Scaffolds a clean, working test automation project from curated templates in < 5 seconds:
- playwright (TypeScript/Playwright Page Object Model)
- pytest (Python/Pytest API testing suite)
- cypress (JavaScript/Cypress e-commerce suite)
- katalon (Katalon Studio automated suite)
- selenium (Python/Selenium test suite)

Injects .synapse.json with the chosen profile (starter, standard, enterprise).
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from typing import Optional

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from tools.core.init_config import build_default_config, format_config_json
except ImportError:
    from init_config import build_default_config, format_config_json

GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

TEMPLATE_MAP = {
    "playwright": "playwright-crm-suite",
    "pytest": "pytest-api-suite",
    "cypress": "cypress-ecommerce-suite",
    "katalon": "katalon-suite",
    "selenium": "selenium-suite",
}


def scaffold_project(
    project_name: str,
    template: str = "playwright",
    profile: str = "starter",
    target_dir: Optional[str] = None,
    force: bool = False
) -> int:
    """Scaffolds a new project from an existing example template."""
    template_key = template.strip().lower()
    if template_key not in TEMPLATE_MAP:
        print(f"\n{RED}❌ Template '{template}' không hợp lệ.{RESET}")
        print(f"   Các template khả dụng: {', '.join(TEMPLATE_MAP.keys())}\n")
        return 1

    hub_root = Path(__file__).resolve().parent.parent.parent
    source_dir = hub_root / "examples" / TEMPLATE_MAP[template_key]

    if not source_dir.is_dir():
        print(f"\n{RED}❌ Không tìm thấy thư mục template nguồn tại: {source_dir}{RESET}\n")
        return 1

    dest_base = Path(target_dir) if target_dir else Path.cwd()
    dest_path = dest_base / project_name

    if dest_path.exists() and not force:
        print(f"\n{RED}❌ Thư mục '{dest_path}' đã tồn tại! Sử dụng cờ --force để ghi đè.{RESET}\n")
        return 1

    # Copy template files
    try:
        if dest_path.exists() and force:
            shutil.rmtree(dest_path)
        shutil.copytree(
            source_dir,
            dest_path,
            ignore=shutil.ignore_patterns("node_modules", ".venv", "__pycache__", "*.pyc", ".git", "reports")
        )
    except OSError as err:
        print(f"\n{RED}❌ Lỗi khi sao chép template: {err}{RESET}\n")
        return 2

    # Inject tailored .synapse.json
    try:
        cfg_dict = build_default_config(
            project_name=project_name,
            profile=profile
        )
        cfg_file = dest_path / ".synapse.json"
        with open(cfg_file, "w", encoding="utf-8") as f:
            f.write(format_config_json(cfg_dict))
    except Exception as err:
        print(f"{YELLOW}⚠️  Không thể tạo .synapse.json tự động: {err}{RESET}")

    print(f"\n{GREEN}🎉 Khởi tạo dự án thành công: {BOLD}{project_name}{RESET}")
    print(f"   📂 Đường dẫn: {BOLD}{dest_path.resolve()}{RESET}")
    print(f"   📦 Template: {BOLD}{template_key}{RESET} ({TEMPLATE_MAP[template_key]})")
    print(f"   🛡️  Profile:  {BOLD}{profile}{RESET}")
    print(f"\n{CYAN}👉 Các bước tiếp theo để bắt đầu:{RESET}")
    print("   1. Di chuyển vào thư mục dự án:")
    print(f"      {BOLD}cd {project_name}{RESET}")
    if template_key == "playwright":
        print("   2. Cài đặt dependencies:")
        print(f"      {BOLD}npm install{RESET}")
    elif template_key == "pytest":
        print("   2. Cài đặt pytest:")
        print(f"      {BOLD}pip install -r requirements.txt{RESET}")
    print("   3. Chạy quét linter kiểm tra fake-pass & Clean POM:")
    print(f"      {BOLD}synapse lint{RESET}")
    print("   4. Mở giao diện Web Studio trực quan:")
    print(f"      {BOLD}synapse ui{RESET}\n")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="synapse new",
        description="Khởi tạo nhanh một dự án kiểm thử tự động từ template chuẩn hóa trong 5 giây."
    )
    parser.add_argument("project_name", help="Tên thư mục dự án cần tạo")
    parser.add_argument(
        "-t", "--template",
        choices=["playwright", "pytest", "cypress", "katalon", "selenium"],
        default="playwright",
        help="Framework kiểm thử mẫu (mặc định: playwright)"
    )
    parser.add_argument(
        "-p", "--profile",
        choices=["starter", "standard", "enterprise"],
        default="starter",
        help="Cấp độ kiểm soát chất lượng (mặc định: starter)"
    )
    parser.add_argument(
        "-d", "--dir",
        dest="target_dir",
        default=None,
        help="Thư mục chứa dự án mới (mặc định: thư mục hiện tại)"
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Ghi đè nếu thư mục đích đã tồn tại"
    )

    args = parser.parse_args()
    ret = scaffold_project(
        project_name=args.project_name,
        template=args.template,
        profile=args.profile,
        target_dir=args.target_dir,
        force=args.force
    )
    sys.exit(ret)


if __name__ == "__main__":
    main()
