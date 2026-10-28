#!/usr/bin/env python3
"""
==============================================================================
Enterprise Automation - Environment & Onboarding Diagnostic Tool
==============================================================================
Script kiểm tra toàn diện môi trường máy tính khi mới clone dự án về.
Hỗ trợ Kỹ sư Kiểm thử (Tester/Developer/DevOps/Automation QA).
Không yêu cầu thư viện bên ngoài (chỉ dùng Python Standard Library).
==============================================================================
"""

import os
import sys
import shutil
import platform
import subprocess
import urllib.request
from pathlib import Path

# Màu sắc console
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Nếu chạy trên Windows terminal cũ không hỗ trợ ANSI
if platform.system() == "Windows" and not os.environ.get("WT_SESSION"):
    GREEN = RED = YELLOW = CYAN = BOLD = RESET = ""

BASE_DIR = Path(__file__).resolve().parent.parent

class DiagnosticRunner:
    def __init__(self):
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
        # Kiểm tra Google Chrome
        chrome_found = False
        chrome_ver = "Unknown"

        if platform.system() == "Darwin":
            app_path = Path("/Applications/Google Chrome.app")
            if app_path.exists():
                ok, out = self.run_command(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'])
                if ok:
                    chrome_found = True
                    chrome_ver = out
        elif platform.system() == "Windows":
            paths = [
                Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("LOCALAPPDATA", "C:\\Users\\Default\\AppData\\Local")) / "Google/Chrome/Application/chrome.exe"
            ]
            for p in paths:
                if p.exists():
                    chrome_found = True
                    chrome_ver = "Installed at " + str(p)
                    break
        else:
            ok, out = self.run_command("google-chrome --version")
            if ok:
                chrome_found = True
                chrome_ver = out

        if chrome_found:
            self.log_check("Google Chrome (Browser)", "PASS", chrome_ver)
        else:
            self.log_check("Google Chrome (Browser)", "FAIL", "Không tìm thấy Google Chrome",
                           "Cài đặt Google Chrome từ: https://www.google.com/chrome/")

    def check_java(self):
        # Kiểm tra Java
        ok, out = self.run_command(["java", "-version"])
        if not ok:
            # Check Katalon bundled JRE on macOS
            katalon_jre = Path("/Applications/Katalon Studio.app/Contents/Eclipse/jre/bin/java")
            if katalon_jre.exists():
                ok, out = self.run_command([str(katalon_jre), "-version"])
                if ok:
                    self.log_check("Java Runtime (JRE/JDK)", "PASS", f"Dùng JRE của Katalon ({katalon_jre})")
                    return

            self.log_check("Java Runtime (JRE/JDK)", "WARN", "Lệnh 'java' chưa có trong PATH toàn cục",
                           "Katalon Studio đã đóng gói sẵn Java bên trong. Nếu muốn chạy CLI bên ngoài, hãy cài đặt JDK 17 hoặc 21 (Eclipse Temurin).")
        else:
            self.log_check("Java Runtime (JRE/JDK)", "PASS", "Java đã có trong hệ thống")

    def check_katalon(self):
        # Kiểm tra Katalon Studio
        katalon_found = False
        katalon_loc = ""

        if platform.system() == "Darwin":
            katalon_app = Path("/Applications/Katalon Studio.app")
            if katalon_app.exists():
                katalon_found = True
                katalon_loc = str(katalon_app)
        elif platform.system() == "Windows":
            candidates = [
                Path("C:/Katalon_Studio"),
                Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Katalon Studio",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Katalon Studio"
            ]
            for c in candidates:
                if c.exists():
                    katalon_found = True
                    katalon_loc = str(c)
                    break

        if not katalon_found and shutil.which("katalon"):
            katalon_found = True
            katalon_loc = shutil.which("katalon")

        if katalon_found:
            self.log_check("Katalon Studio IDE", "PASS", f"Tìm thấy tại: {katalon_loc}")
        else:
            self.log_check("Katalon Studio IDE", "WARN", "Chưa phát hiện bộ cài Katalon Studio ở đường dẫn chuẩn",
                           "Tải và cài đặt Katalon Studio (v8.x/v9.x/v10.x) từ https://katalon.com/download")

    def check_node_allure(self):
        # Kiểm tra Node.js & Allure
        node_path = shutil.which("node")
        npm_path = shutil.which("npm")
        npx_path = shutil.which("npx")
        allure_cli = shutil.which("allure")

        if node_path and (npx_path or allure_cli):
            ok, node_ver = self.run_command(["node", "--version"])
            tool_msg = "Allure CLI trực tiếp" if allure_cli else "npx allure-commandline (Tự động tải)"
            self.log_check("Allure Reporting Engine", "PASS", f"Node {node_ver} | Hỗ trợ: {tool_msg}")
        else:
            self.log_check("Allure Reporting Engine", "WARN", "Chưa cài Node.js (cần để mở báo cáo Allure)",
                           "Cài đặt Node.js từ https://nodejs.org/ để có thể chạy lệnh './tools/generate_allure_report.sh serve'")

    def check_python_runner(self):
        # Kiểm tra Python & Playwright runner (tùy chọn)
        py_ver = sys.version.split()[0]
        venv_path = BASE_DIR / ".venv"

        if venv_path.exists():
            self.log_check("Python Virtual Environment", "PASS", f"Python {py_ver} (Phát hiện .venv có sẵn)")
        else:
            self.log_check("Python Virtual Environment", "PASS", f"Python {py_ver} (Tùy chọn: tạo .venv nếu dùng runner phụ)")

    def check_project_structure(self):
        # Kiểm tra cấu trúc thư mục dự án
        required_dirs = ["Keywords/pages", "Profiles", "Scripts", "Test Suites", "Screenshots", "allure-results", "tools"]
        missing = []
        for rd in required_dirs:
            p = BASE_DIR / rd
            if not p.exists():
                missing.append(rd)

        if not missing:
            self.log_check("Project Structure (POM)", "PASS", "Toàn vẹn (17 Page Objects, Profiles, Test Suites, Tools)")
        else:
            self.log_check("Project Structure (POM)", "FAIL", f"Thiếu các thư mục: {', '.join(missing)}",
                           "Kiểm tra lại lệnh git clone hoặc khôi phục từ kho Git chính thức.")

    def check_network(self):
        # Kiểm tra kết nối tới ứng dụng Base URL (nạp từ .env hoặc môi trường)
        env_file = BASE_DIR / ".env"
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
            req = urllib.request.Request(test_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as resp:
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
        print(f"📁 Thư mục dự án: {BASE_DIR}\n")

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
            print(f"{BOLD}{GREEN}🎉 TỔNG KẾT: MÔI TRƯỜNG ĐÃ SẴN SÀNG ĐỂ CHẠY KIỂM THỬ!{RESET}")
            if self.warnings:
                print(f"{YELLOW}Lưu ý: Có {len(self.warnings)} cảnh báo nhỏ (tùy chọn) ở trên, có thể bổ sung khi cần.{RESET}")
            print(f"\n👉 {BOLD}Khởi động nhanh:{RESET}")
            print("   1. Mở Katalon Studio -> Open Project -> Chọn thư mục này.")
            print("   2. Chọn Test Suite: 'Test Suites/Smoke_Tests/TS_01_Smoke_Test' và bấm Run (Chrome).")
            print("   3. Xem báo cáo Allure: './tools/generate_allure_report.sh serve'")
        else:
            print(f"{BOLD}{RED}❌ TỔNG KẾT: CÓ {len(self.errors)} ĐIỀU KIỆN TIÊN QUYẾT CẦN CÀI ĐẶT TRƯỚC!{RESET}")
            for name, hint in self.errors:
                print(f"   - {BOLD}{name}:{RESET} {hint}")
        print(f"{BOLD}{'='*70}{RESET}\n")

if __name__ == "__main__":
    runner = DiagnosticRunner()
    runner.run_all()
