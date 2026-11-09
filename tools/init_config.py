#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tools/init_config.py — Standardized Project Configuration Bootstrapper
----------------------------------------------------------------------
Generates a canonical .synapse.json configuration file for Spoke target projects.
Enables instant project setup with zero manual JSON authoring.

Supports:
  - Interactive questionnaire mode (project name, author, template, sample sheet)
  - Autonomous non-interactive flags (--template, --author, --sheet-name, --force, --dry-run)
  - Direct integration with template_excel_exporter and Definition-of-Done quality gates
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

# Enforce UTF-8 stdio for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (OSError, ValueError) as _err:
        _ = _err

# ANSI Color formatting
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

HUB_ROOT = Path(__file__).resolve().parent.parent


def is_hub_directory(target_path: Path) -> bool:
    """Checks whether the given target path is the Synapse-Hub core repository itself."""
    try:
        resolved = target_path.resolve()
        if resolved == HUB_ROOT:
            return True
        if (resolved / "skills_manifest.json").is_file() and (resolved / "AGENTS.md").is_file():
            return True
    except (OSError, ValueError) as _err:
        _ = _err
    return False


def get_hub_version() -> str:
    """Resolves Hub release version dynamically from package.json with fallback."""
    try:
        pkg_file = HUB_ROOT / "package.json"
        if pkg_file.is_file():
            with open(pkg_file, "r", encoding="utf-8") as f:
                return json.load(f).get("version", "3.2.1")
    except (OSError, json.JSONDecodeError) as _err:
        _ = _err
    return "3.2.1"


def detect_git_user_name() -> Optional[str]:
    """Attempts to auto-detect git user.name for convenient author defaulting."""
    try:
        res = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            timeout=3
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except (subprocess.SubprocessError, OSError) as _err:
        _ = _err
    return None


def build_default_config(
    project_name: str = "Enterprise-QA-Project",
    author: str = "QA Engineer",
    tester: str = "QA Engineer",
    template_path: str = "",
    sample_sheet: str = "Test Cases",
    module_code: str = "MOD",
    module_name: str = "General Module",
    default_output_dir: str = "reports",
    version: Optional[str] = None
) -> Dict[str, Any]:
    """Constructs the canonical .synapse.json dictionary schema."""
    hub_ver = version or get_hub_version()
    return {
        "$schema": "https://raw.githubusercontent.com/TeeVee998/Synapse-Hub/main/docs/schemas/synapse.config.schema.json",
        "version": hub_ver,
        "project": {
            "name": project_name,
            "author": author,
            "tester": tester,
            "description": f"Automated & Manual QA Workspace for {project_name}"
        },
        "testcase_export": {
            "template_path": template_path,
            "sample_sheet": sample_sheet,
            "default_output_dir": default_output_dir,
            "module_code": module_code,
            "module_name": module_name
        },
        "quality_gates": {
            "mutation_min_score": 80,
            "gates": {
                "gate_0_author_integrity": True,
                "gate_1_bom_check": True,
                "gate_2_path_portability": True,
                "gate_3_clean_pom": True,
                "gate_4_ai_docs_lint": True,
                "gate_5_cleanup_blacklist": True,
                "gate_6_credential_security": True,
                "gate_7_infer_linter": True,
                "gate_8_micro_mutator": True,
                "gate_9_skill_collision": True
            }
        },
        "infer_linter": {
            "enabled": True,
            "strict": True,
            "format": "text",
            "exclude_paths": [
                ".git",
                ".synapse",
                "node_modules",
                "templates",
                "reports"
            ],
            "disabled_rules": []
        }
    }


def init_config(
    target_dir: str = ".",
    project_name: Optional[str] = None,
    author: Optional[str] = None,
    tester: Optional[str] = None,
    template_path: Optional[str] = None,
    sample_sheet: Optional[str] = None,
    module_code: Optional[str] = None,
    module_name: Optional[str] = None,
    default_output_dir: Optional[str] = None,
    force: bool = False,
    dry_run: bool = False,
    interactive: bool = False
) -> int:
    """
    Initializes or updates the .synapse.json file in the given target directory.
    Returns 0 on success, non-zero on failure.
    """
    target_path = Path(target_dir).resolve()
    target_file = target_path / ".synapse.json"

    # Hub CWD Confusion Guard (Anti-Pattern Rule 7 & 8)
    if not dry_run and is_hub_directory(target_path):
        print(f"\n{YELLOW}⚠️  [CWD CONFUSION GUARD] Thư mục mục tiêu là Synapse-Hub (Skill Hub trung tâm), không phải dự án Spoke.{RESET}")
        print("  Synapse-Hub đã sử dụng synapse.config.json và không nên khởi tạo file .synapse.json tại đây.")
        print(f"👉 Vui lòng chỉ định đường dẫn dự án mục tiêu: {BOLD}agent-qa init-config <duong_dan_du_an>{RESET}\n")
        return 1

    # Default project name from directory name if not provided
    inferred_project_name = project_name or target_path.name
    inferred_author = author or detect_git_user_name() or "QA Engineer"
    inferred_tester = tester or inferred_author
    inferred_template = template_path or ""
    inferred_sheet = sample_sheet or "Test Cases"
    inferred_mod_code = module_code or "MOD"
    inferred_mod_name = module_name or "General Module"
    inferred_out_dir = default_output_dir or "reports"

    # Check interactive terminal condition
    is_interactive_terminal = hasattr(sys.stdin, "isatty") and sys.stdin.isatty() and not os.environ.get("CI") and not os.environ.get("SYNAPSE_NON_INTERACTIVE")
    should_prompt = interactive or (is_interactive_terminal and not any([project_name, author, template_path, sample_sheet]))

    if should_prompt:
        print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
        print(f"{BOLD}{CYAN}    🧠 SYNAPSE HUB — KHỞI TẠO CẤU HÌNH DỰ ÁN (.synapse.json)           {RESET}")
        print(f"{BOLD}{CYAN}======================================================================{RESET}")
        print("Hãy trả lời các câu hỏi ngắn dưới đây để thiết lập dự án Spoke chuẩn hóa:")
        print(f"(Nhấn {BOLD}Enter{RESET} để chấp nhận giá trị gợi ý mặc định trong ngoặc)\n")

        try:
            val_p = input(f"1. Tên dự án [{BOLD}{inferred_project_name}{RESET}]: ").strip()
            if val_p:
                inferred_project_name = val_p

            val_a = input(f"2. Tác giả / QA Lead [{BOLD}{inferred_author}{RESET}]: ").strip()
            if val_a:
                inferred_author = val_a
                inferred_tester = val_a

            val_t = input("3. Đường dẫn file template Excel (để trống nếu dùng layout chuẩn Hub): ").strip()
            if val_t:
                inferred_template = val_t

            val_s = input(f"4. Tên worksheet mẫu trong template [{BOLD}{inferred_sheet}{RESET}]: ").strip()
            if val_s:
                inferred_sheet = val_s
        except (EOFError, KeyboardInterrupt):
            print(f"\n{YELLOW}Đã hủy khởi tạo cấu hình.{RESET}")
            return 1

    config_data = build_default_config(
        project_name=inferred_project_name,
        author=inferred_author,
        tester=inferred_tester,
        template_path=inferred_template,
        sample_sheet=inferred_sheet,
        module_code=inferred_mod_code,
        module_name=inferred_mod_name,
        default_output_dir=inferred_out_dir
    )

    formatted_json = json.dumps(config_data, indent=2, ensure_ascii=False) + "\n"

    if dry_run:
        print(f"\n{YELLOW}🔍 [DRY-RUN] Xem trước nội dung cấu hình cho '{target_file}':{RESET}\n")
        print(formatted_json)
        print(f"{GREEN}✅ Chạy thử nghiệm thành công (không ghi file thực tế).{RESET}\n")
        return 0

    if target_file.exists() and not force:
        print(f"\n{YELLOW}⚠️  File cấu hình đã tồn tại tại:{RESET} {target_file}")
        print(f"👉 Để ghi đè cấu hình mới, vui lòng thêm cờ {BOLD}--force{RESET} (hoặc {BOLD}-f{RESET}).\n")
        print(f"Ví dụ: {BOLD}agent-qa init-config --force{RESET}\n")
        return 1

    try:
        os.makedirs(target_path, exist_ok=True)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(formatted_json)
    except OSError as err:
        print(f"\n{RED}❌ Không thể ghi file cấu hình tại {target_file}: {err}{RESET}")
        return 2

    print(f"\n{GREEN}✅ Khởi tạo thành công file cấu hình chuẩn hóa:{RESET}")
    print(f"   📂 Đường dẫn: {BOLD}{target_file}{RESET}")
    print(f"   🏷️  Dự án    : {BOLD}{inferred_project_name}{RESET}")
    print(f"   👤 Tác giả  : {BOLD}{inferred_author}{RESET}")
    if inferred_template:
        print(f"   📊 Template : {BOLD}{inferred_template}{RESET} (Sheet: {inferred_sheet})")
    else:
        print("   📊 Template : (Mặc định Hub 12 cột — bạn có thể thêm đường dẫn template sau)")
    print(f"\n{CYAN}💡 Bước Tiếp Theo:{RESET}")
    print("   1. Chạy xuất test cases Markdown sang Excel tự động áp dụng template:")
    print(f"      👉 {BOLD}agent-qa export-excel docs/TEST_CASES.md{RESET}")
    print("   2. Chạy kiểm tra 10 Quality Gates cho dự án:")
    print(f"      👉 {BOLD}agent-qa verify{RESET}\n")
    return 0


initialize_config = init_config


def main():
    parser = argparse.ArgumentParser(
        prog="agent-qa init-config",
        description="Khởi tạo file cấu hình .synapse.json chuẩn hóa cho dự án mục tiêu (Spoke)."
    )
    parser.add_argument("target_dir", nargs="?", default=".", help="Thư mục đích khởi tạo file cấu hình (mặc định: .)")
    parser.add_argument("-t", "--template", dest="template_path", default=None, help="Đường dẫn file template Excel (.xlsx)")
    parser.add_argument("-a", "--author", default=None, help="Tên tác giả / QA Lead phụ trách dự án")
    parser.add_argument("--tester", default=None, help="Tên kiểm thử viên phụ trách")
    parser.add_argument("-s", "--sheet-name", dest="sample_sheet", default=None, help="Tên worksheet mẫu cần clone (mặc định: Test Cases)")
    parser.add_argument("-p", "--project-name", default=None, help="Tên định danh của dự án (mặc định: tên thư mục)")
    parser.add_argument("--module-code", default="MOD", help="Mã module viết tắt (mặc định: MOD)")
    parser.add_argument("--module-name", default="General Module", help="Tên phân hệ kiểm thử (mặc định: General Module)")
    parser.add_argument("--out-dir", dest="default_output_dir", default="reports", help="Thư mục xuất báo cáo mặc định (mặc định: reports)")
    parser.add_argument("-f", "--force", action="store_true", help="Ghi đè file .synapse.json nếu đã tồn tại")
    parser.add_argument("--dry-run", action="store_true", help="In nội dung file JSON ra màn hình mà không ghi xuống ổ đĩa")
    parser.add_argument("-i", "--interactive", action="store_true", help="Kích hoạt chế độ hỏi đáp tương tác trực tiếp")

    args = parser.parse_args()

    ret = init_config(
        target_dir=args.target_dir,
        project_name=args.project_name,
        author=args.author,
        tester=args.tester,
        template_path=args.template_path,
        sample_sheet=args.sample_sheet,
        module_code=args.module_code,
        module_name=args.module_name,
        default_output_dir=args.default_output_dir,
        force=args.force,
        dry_run=args.dry_run,
        interactive=args.interactive
    )
    sys.exit(ret)


if __name__ == "__main__":
    main()
