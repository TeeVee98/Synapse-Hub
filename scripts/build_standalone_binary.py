#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
scripts/build_standalone_binary.py — Standalone Binary Builder
--------------------------------------------------------------
Compiles Synapse-Hub into a single self-contained executable using PyInstaller.
Eliminates Python runtime dependency on client machines.
Output location: dist/bin/synapse (or dist/bin/synapse.exe on Windows).
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def find_or_setup_pyinstaller() -> str:
    """Finds existing pyinstaller executable or sets up an isolated environment."""
    existing = shutil.which("pyinstaller")
    if existing:
        return existing

    # Check temp venv
    temp_venv_pyinstaller = Path("/tmp/synapse_build_venv/bin/pyinstaller")
    if temp_venv_pyinstaller.exists():
        return str(temp_venv_pyinstaller)

    print(f"{YELLOW}⚙️  PyInstaller chưa được cài đặt. Đang khởi tạo môi trường build cô lập...{RESET}")
    venv_dir = Path("/tmp/synapse_build_venv")
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    pip_cmd = venv_dir / ("Scripts" if os.name == "nt" else "bin") / "pip"
    subprocess.run([str(pip_cmd), "install", "pyinstaller"], check=True)

    pyi_cmd = venv_dir / ("Scripts" if os.name == "nt" else "bin") / ("pyinstaller.exe" if os.name == "nt" else "pyinstaller")
    return str(pyi_cmd)


def build_binary() -> int:
    """Builds the standalone onefile binary."""
    pyi_path = find_or_setup_pyinstaller()
    print(f"\n{BOLD}{CYAN}🚀 Bắt đầu đóng gói Synapse-Hub Standalone Binary...{RESET}")
    print(f"   Trình biên dịch: {BOLD}{pyi_path}{RESET}")

    dist_bin = REPO_ROOT / "dist" / "bin"
    work_dir = REPO_ROOT / "build" / "pyinstaller_work"
    spec_dir = REPO_ROOT / "build" / "spec"
    dist_bin.mkdir(parents=True, exist_ok=True)

    data_sep = ";" if os.name == "nt" else ":"
    data_files = [
        "LICENSE",
        "NOTICE",
        "package.json",
        "skills_manifest.json",
        "skills_index.json",
        "synapse.config.json",
    ]

    cmd = [
        pyi_path,
        "--onefile",
        "--name", "synapse",
        "--distpath", str(dist_bin),
        "--workpath", str(work_dir),
        "--specpath", str(spec_dir),
    ]

    for df in data_files:
        src = REPO_ROOT / df
        if src.exists():
            cmd.extend(["--add-data", f"{src.resolve()}{data_sep}."])

    cmd.append(str((REPO_ROOT / "tools" / "core" / "cli.py").resolve()))

    print("   Đang biên dịch tệp thực thi duy nhất...")
    res = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if res.returncode != 0:
        print(f"\n{RED}❌ Quá trình đóng gói thất bại với mã thoát: {res.returncode}{RESET}\n")
        return res.returncode

    exe_name = "synapse.exe" if os.name == "nt" else "synapse"
    output_bin = dist_bin / exe_name

    if output_bin.exists():
        size_mb = output_bin.stat().st_size / (1024 * 1024)
        print(f"\n{GREEN}✅ Đóng gói Standalone Binary thành công!{RESET}")
        print(f"   📂 Tệp xuất ra: {BOLD}{output_bin}{RESET} ({size_mb:.2f} MB)")

        # Verify execution
        print("   🔍 Đang kiểm tra chạy thử nghiệm:")
        verify_res = subprocess.run([str(output_bin), "version"], capture_output=True, text=True)
        if verify_res.returncode == 0:
            print(f"      {GREEN}✓ Xác minh thành công: {verify_res.stdout.strip().splitlines()[0]}{RESET}\n")
            return 0
        else:
            print(f"      {RED}✗ Lỗi khi chạy thử nghiệm: {verify_res.stderr.strip()}{RESET}\n")
            return 1
    return 1


if __name__ == "__main__":
    sys.exit(build_binary())
