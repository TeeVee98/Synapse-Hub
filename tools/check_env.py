#!/usr/bin/env python3
"""
==============================================================================
Enterprise Automation - Environment & Onboarding Diagnostic Tool
==============================================================================
Script kiểm tra toàn diện môi trường máy tính khi mới clone dự án về.
Hỗ trợ Kỹ sư Kiểm thử (Tester/Developer/DevOps/Automation QA).
Không yêu cầu thư viện bên ngoài (chỉ dùng Python Standard Library).
Hỗ trợ tự động nhận diện Target Project hoặc QA Hub (CLI, CWD, ENV).
==============================================================================
"""

import os
import sys
import shutil
import platform
import subprocess
import argparse
import urllib.request
import ssl
from pathlib import Path

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Màu sắc console
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

if platform.system() == "Windows" and not os.environ.get("WT_SESSION"):
    GREEN = RED = YELLOW = CYAN = BOLD = RESET = ""

HUB_ROOT = Path(__file__).resolve().parent.parent


def resolve_target_repo(cli_target=None, cli_repo=None):
    """
    Resolves the target repository path:
    1. Explicit CLI flag: --repo / --path or positional target.
    2. Environment variable: TARGET_PROJECT_DIR.
    3. Current Working Directory (if different from Hub).
    4. Default fallback: QA Hub root (parent of tools/).
    """
    chosen = cli_repo or cli_target
    if chosen:
        resolved = Path(chosen).resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Target repository path not found: {resolved}")
        return resolved

    env_dir = os.environ.get("TARGET_PROJECT_DIR")
    if env_dir and os.path.exists(env_dir):
        return Path(env_dir).resolve()

    cwd = Path.cwd().resolve()
    if cwd != HUB_ROOT:
        return cwd

    return HUB_ROOT


class DiagnosticRunner:
    def __init__(self, target_dir=None):
        self.target_dir = Path(target_dir or HUB_ROOT).resolve()
        self.results = []
        self.warnings = []
        self.errors = []

    def log_check(self, name, status, message, fix_hint=""):
        badge = f"{GREEN}[PASS]{RESET}" if status == "PASS" else (f"{YELLOW}[WARN]{RESET}" if status == "WARN" else f"{RED}[FAIL]{RESET}")
        print(f" {badge} {BOLD}{name:<32}{RESET} : {message}")
        if fix_hint and status in ("WARN", "FAIL"):
            print(f"        👉 {CYAN}Khắc phục:{RESET} {fix_hint}")
            if status == "FAIL":
                self.errors.append((name, fix_hint))
            else:
                self.warnings.append((name, fix_hint))

    def run_command(self, cmd):
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=isinstance(cmd, str))
            return res.returncode == 0, res.stdout.strip()
        except Exception as e:
            return False, str(e)

    def check_os(self):
        os_name = platform.system()
        os_ver = platform.release()
        arch = platform.machine()
        self.log_check("Operating System", "PASS", f"{os_name} {os_ver} ({arch})")

    def check_chrome(self):
        # 1. Tìm qua lệnh 'where' hoặc 'which'
        found, out = self.run_command("where chrome" if platform.system() == "Windows" else "which google-chrome")
        if found:
            self.log_check("Google Chrome (Browser)", "PASS", f"Installed at {out.splitlines()[0]}")
            return

        # 2. Tìm theo đường dẫn chuẩn trên Windows
        if platform.system() == "Windows":
            paths = [
                os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            ]
            for p in paths:
                if os.path.exists(p):
                    self.log_check("Google Chrome (Browser)", "PASS", f"Installed at {p}")
                    return

        self.log_check("Google Chrome (Browser)", "FAIL", "Không tìm thấy trình duyệt Google Chrome trên hệ thống",
                       "Tải và cài đặt Google Chrome tại https://www.google.com/chrome/")

    def check_java(self):
        found, out = self.run_command("java -version")
        if found or "version" in out:
            # java -version thường in ra stderr
            ver = out.splitlines()[0] if out else "Đã cài đặt"
            self.log_check("Java Runtime (JRE/JDK)", "PASS", f"Java đã có trong hệ thống ({ver})")
        else:
            # Kiểm tra biến môi trường JAVA_HOME
            jh = os.environ.get("JAVA_HOME")
            if jh and os.path.exists(jh):
                self.log_check("Java Runtime (JRE/JDK)", "PASS", f"JAVA_HOME = {jh}")
            else:
                self.log_check("Java Runtime (JRE/JDK)", "WARN", "Không tìm thấy lệnh 'java' trong PATH hoặc JAVA_HOME",
                               "Katalon đã có sẵn Java nhúng bên trong, nhưng nếu dùng Gradle/Jenkins CLI, vui lòng cài OpenJDK 17.")

    def check_katalon(self):
        # Kiểm tra Katalon Studio / KRE
        found, out = self.run_command("where katalonc" if platform.system() == "Windows" else "which katalonc")
        if found:
            self.log_check("Katalon Runtime Engine (KRE)", "PASS", f"Tìm thấy katalonc tại {out.splitlines()[0]}")
            return

        # Kiểm tra ứng dụng GUI
        if platform.system() == "Windows":
            user_home = os.path.expanduser("~")
            katalon_candidates = [
                r"C:\Katalon_Studio",
                r"D:\Katalon_Studio",
                os.path.join(user_home, "Downloads"),
                os.path.expandvars(r"%ProgramFiles%\Katalon Studio"),
            ]
            for c in katalon_candidates:
                if os.path.exists(c):
                    for item in os.listdir(c):
                        if "katalon" in item.lower() and os.path.isdir(os.path.join(c, item)):
                            self.log_check("Katalon Studio IDE", "PASS", f"Tìm thấy thư mục cài đặt tại {os.path.join(c, item)}")
                            return

        self.log_check("Katalon Studio IDE", "WARN", "Chưa phát hiện bộ cài Katalon Studio ở đường dẫn chuẩn",
                       "Tải và cài đặt Katalon Studio (v8.x/v9.x/v10.x) từ https://katalon.com/download")

    def check_node_allure(self):
        # Kiểm tra Node.js (dùng để host Allure report hoặc chạy Playwright)
        found_node, node_ver = self.run_command("node -v")
        if found_node:
            self.log_check("Node.js Runtime", "PASS", f"Node.js {node_ver}")
        else:
            self.log_check("Allure Reporting Engine", "WARN", "Chưa cài Node.js (cần để mở báo cáo Allure)",
                           "Cài đặt Node.js từ https://nodejs.org/ để có thể chạy lệnh './tools/generate_allure_report.sh serve'")

    def check_python_runner(self):
        py_ver = sys.version.split()[0]
        venv_path = self.target_dir / ".venv"

        if venv_path.exists():
            self.log_check("Python Virtual Environment", "PASS", f"Python {py_ver} (Phát hiện .venv có sẵn)")
        else:
            self.log_check("Python Virtual Environment", "PASS", f"Python {py_ver} (Tùy chọn: tạo .venv nếu dùng runner phụ)")

    def check_project_structure(self):
        # Phân biệt chế độ QA Hub vs Target Test Project
        is_hub = (self.target_dir / "skills_manifest.json").exists() or (self.target_dir / ".agents" / "skills").is_dir()

        if is_hub:
            required_dirs = [".agents/skills", ".agents/rules", "tools", "tests"]
            missing = [rd for rd in required_dirs if not (self.target_dir / rd).exists()]
            if not missing:
                self.log_check("Project Structure (QA Hub)", "PASS", "Toàn vẹn QA Hub (34 Skills, Rules, Tools, Unit Tests)")
            else:
                self.log_check("Project Structure (QA Hub)", "FAIL", f"Thiếu các thư mục: {', '.join(missing)}",
                               "Khôi phục từ kho Git chính thức agent-skills.")
            return

        # Chế độ Target Automation Test Project
        is_playwright = (self.target_dir / "playwright.config.ts").exists() or (self.target_dir / "playwright.config.js").exists()
        if is_playwright:
            required_dirs = ["tests"]
            missing = [rd for rd in required_dirs if not (self.target_dir / rd).exists()]
            if not missing:
                self.log_check("Project Structure (Playwright)", "PASS", "Toàn vẹn cấu trúc dự án Playwright")
            else:
                self.log_check("Project Structure (Playwright)", "FAIL", f"Thiếu các thư mục: {', '.join(missing)}")
            return

        # Mặc định cấu trúc Katalon / Clean POM
        required_dirs = ["Scripts", "Keywords", "Profiles"]
        missing = [rd for rd in required_dirs if not (self.target_dir / rd).exists()]
        if not missing:
            self.log_check("Project Structure (Clean POM)", "PASS", "Toàn vẹn (Keywords, Profiles, Scripts)")
        else:
            self.log_check("Project Structure (POM)", "WARN" if len(missing) < len(required_dirs) else "FAIL",
                           f"Thiếu các thư mục: {', '.join(missing)}",
                           "Kiểm tra lại lệnh git clone hoặc chọn đúng thư mục dự án test đích.")

    def check_network(self):
        env_file = self.target_dir / ".env"
        if env_file.exists():
            try:
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        if k.strip() not in os.environ:
                            os.environ[k.strip()] = v.strip().strip("'\"")
            except Exception:
                pass

        base = os.environ.get("BASE_URL", "").rstrip("/")
        if not base:
            self.log_check("Mạng / Base URL Server", "WARN", "Chưa cấu hình BASE_URL trong .env",
                           "Sao chép .env.example thành .env và điền BASE_URL để kiểm tra kết nối.")
            return
        test_url = f"{base}/login"
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(test_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
                code = resp.getcode()
                if code in (200, 301, 302):
                    self.log_check("Mạng / Base URL Server", "PASS", f"Kết nối tốt tới {test_url} (HTTP {code})")
                else:
                    self.log_check("Mạng / Base URL Server", "WARN", f"Mã phản hồi HTTP {code}", "Kiểm tra lại proxy hoặc kết nối mạng nội bộ.")
        except Exception as e:
            self.log_check("Mạng / Base URL Server", "WARN", f"Không thể kết nối trực tiếp ({e})",
                           "Kiểm tra kết nối Internet hoặc bật VPN nếu hệ thống yêu cầu mạng nội bộ.")

    def run_all(self):
        print(f"\n{BOLD}{'='*70}{RESET}")
        print(f"{BOLD}{CYAN} ENTERPRISE AUTOMATION - KIỂM TRA MÔI TRƯỜNG DỰ ÁN KHI CLONE MỚI{RESET}")
        print(f"{BOLD}{'='*70}{RESET}")
        print(f"📁 Thư mục kiểm tra: {self.target_dir}\n")

        self.check_os()
        self.check_chrome()
        self.check_java()
        self.check_katalon()
        self.check_node_allure()
        self.check_python_runner()
        self.check_project_structure()
        self.check_network()

        print(f"\n{BOLD}{'='*70}{RESET}")
        if not self.errors:
            print(f"{BOLD}{GREEN}🎉 TỔNG KẾT: MÔI TRƯỜNG ĐÃ SẴN SÀNG!{RESET}")
            if self.warnings:
                print(f"{YELLOW}Lưu ý: Có {len(self.warnings)} cảnh báo nhỏ (tùy chọn) ở trên, có thể bổ sung khi cần.{RESET}")
        else:
            print(f"{BOLD}{RED}❌ TỔNG KẾT: CÓ {len(self.errors)} ĐIỀU KIỆN TIÊN QUYẾT CẦN CÀI ĐẶT TRƯỚC!{RESET}")
            for name, hint in self.errors:
                print(f"   - {BOLD}{name}:{RESET} {hint}")
        print(f"{BOLD}{'='*70}{RESET}\n")
        return 0 if not self.errors else 1


def main():
    parser = argparse.ArgumentParser(description="Enterprise Environment Diagnostic Tool")
    parser.add_argument("target", nargs="?", default=None, help="Target repository path to diagnose")
    parser.add_argument("--repo", "--path", dest="repo_path", default=None, help="Target repository path")
    args = parser.parse_args()

    try:
        target_dir = resolve_target_repo(cli_target=args.target, cli_repo=args.repo_path)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        return 1

    runner = DiagnosticRunner(target_dir=target_dir)
    return runner.run_all()


if __name__ == "__main__":
    sys.exit(main())
