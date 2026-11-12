#!/usr/bin/env python3
"""
==============================================================================
Enterprise Automation - Environment & Onboarding Diagnostic Tool
==============================================================================
Comprehensive environment diagnostic tool for freshly cloned test repositories.
Supports Automation QA, SDETs, Developers, and CI/CD pipelines.
Zero external dependencies (Pure Python Standard Library).
Autonomously detects Target Project or QA Hub (CLI, CWD, ENV).
==============================================================================
"""

import os
import sys
import shlex
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

# Console colors
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
    def __init__(self, target_dir=None, insecure: bool = False):
        self.target_dir = Path(target_dir or HUB_ROOT).resolve()
        self.insecure = insecure
        self.results = []
        self.warnings = []
        self.errors = []
        self.is_standalone = False

    def log_check(self, name, status, message, fix_hint=""):
        badge = f"{GREEN}[PASS]{RESET}" if status == "PASS" else (f"{YELLOW}[WARN]{RESET}" if status == "WARN" else f"{RED}[FAIL]{RESET}")
        print(f" {badge} {BOLD}{name:<32}{RESET} : {message}")
        if fix_hint and status in ("WARN", "FAIL"):
            print(f"        👉 {CYAN}Fix Hint:{RESET} {fix_hint}")
            if status == "FAIL":
                self.errors.append((name, fix_hint))
            else:
                self.warnings.append((name, fix_hint))

    def run_command(self, cmd, timeout: float = 15.0):
        try:
            if isinstance(cmd, str):
                cmd_args = shlex.split(cmd, posix=(platform.system() != "Windows"))
            else:
                cmd_args = list(cmd)
            res = subprocess.run(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=False, timeout=timeout)
            out = res.stdout.strip() if res.stdout.strip() else res.stderr.strip()
            return res.returncode == 0, out
        except Exception as e:
            return False, str(e)

    def check_os(self):
        """Verifies operating system platform, kernel version, and architecture."""
        os_name = platform.system()
        os_ver = platform.release()
        arch = platform.machine()
        self.log_check("Operating System", "PASS", f"{os_name} {os_ver} ({arch})")

    def check_git(self):
        """Verifies presence of Git in PATH for repository hooks and version control."""
        found, out = self.run_command("git --version")
        if found and out:
            self.log_check("Git Version Control", "PASS", f"{out.splitlines()[0]}")
        else:
            self.log_check("Git Version Control", "FAIL", "Command 'git' not found in PATH",
                           "Install Git from https://git-scm.com/ to enable repository hooks and version control.")

    def check_chrome(self):
        """Checks for Google Chrome, Chromium, Brave, or Playwright browser runtimes."""
        # 1. Search via 'where' (Windows) or 'which' (Unix)
        cmd = "where chrome" if platform.system() == "Windows" else "which google-chrome google-chrome-stable chromium chromium-browser"
        found, out = self.run_command(cmd)
        if found and out:
            self.log_check("Google Chrome (Browser)", "PASS", f"Installed at {out.splitlines()[0]}")
            return

        # 2. Search macOS standard application bundles
        if platform.system() == "Darwin":
            mac_paths = [
                Path("/Applications/Google Chrome.app"),
                Path.home() / "Applications/Google Chrome.app",
                Path("/Applications/Chromium.app"),
                Path("/Applications/Brave Browser.app"),
                Path("/Applications/Microsoft Edge.app")
            ]
            for p in mac_paths:
                if p.exists():
                    self.log_check("Google Chrome (Browser)", "PASS", f"Installed at {p}")
                    return
            # Also check Playwright managed browser installations
            pw_cache = Path.home() / "Library/Caches/ms-playwright"
            if pw_cache.exists() and any(pw_cache.glob("chromium-*")):
                self.log_check("Google Chrome (Browser)", "PASS", f"Playwright Chromium runtime verified at {pw_cache}")
                return

        # 3. Search Windows standard installation paths
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

        self.log_check("Google Chrome (Browser)", "FAIL", "Google Chrome browser not found on system",
                       "Download and install Google Chrome from https://www.google.com/chrome/")

    def check_java(self):
        """Verifies presence of Java JRE/JDK runtime via CLI or JAVA_HOME."""
        found, out = self.run_command("java -version")
        if found or "version" in out:
            ver = out.splitlines()[0] if out else "Installed"
            self.log_check("Java Runtime (JRE/JDK)", "PASS", f"Java runtime available ({ver})")
        else:
            jh = os.environ.get("JAVA_HOME")
            if jh and os.path.exists(jh):
                self.log_check("Java Runtime (JRE/JDK)", "PASS", f"JAVA_HOME = {jh}")
            else:
                self.log_check("Java Runtime (JRE/JDK)", "WARN", "Command 'java' not found in PATH or JAVA_HOME",
                               "Katalon includes embedded JRE, but for Gradle/Jenkins CLI, install OpenJDK 17.")

    def check_katalon(self):
        """Verifies Katalon Studio / Katalon Runtime Engine installation if applicable."""
        # Context-aware: check if current target is actually a Katalon project
        is_katalon_project = (
            any(self.target_dir.glob("*.prj"))
            or (self.target_dir / "Keywords").exists()
            or ((self.target_dir / "Scripts").exists() and any(self.target_dir.glob("Scripts/**/*.groovy")))
        )

        found, out = self.run_command("where katalonc" if platform.system() == "Windows" else "which katalonc")
        if found and out:
            self.log_check("Katalon Runtime Engine (KRE)", "PASS", f"Found katalonc at {out.splitlines()[0]}")
            return

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
                            self.log_check("Katalon Studio IDE", "PASS", f"Installation directory located at {os.path.join(c, item)}")
                            return

        if is_katalon_project:
            self.log_check("Katalon Studio IDE", "WARN", "Katalon Studio installation not found in standard paths",
                           "Download and install Katalon Studio from https://katalon.com/download")
        else:
            self.log_check("Katalon Studio IDE", "PASS", "Not installed (Optional - not required for Playwright/Cypress/Pytest)")

    def check_node_allure(self):
        """Verifies presence of Node.js runtime for test runners and Allure reports."""
        found_node, node_ver = self.run_command("node -v")
        if found_node:
            self.log_check("Node.js Runtime", "PASS", f"Node.js {node_ver}")
        else:
            self.log_check("Allure Reporting Engine", "WARN", "Node.js not installed (required to serve Allure reports)",
                           "Install Node.js from https://nodejs.org/ to execute 'python tools/generate_allure_report.py serve'")

    def check_python_runner(self):
        """Verifies active Python environment and optional virtual environment presence."""
        py_ver = sys.version.split()[0]
        venv_path = self.target_dir / ".venv"

        if venv_path.exists():
            self.log_check("Python Virtual Environment", "PASS", f"Python {py_ver} (Active .venv detected)")
        else:
            self.log_check("Python Virtual Environment", "PASS", f"Python {py_ver} (Optional: create .venv if using auxiliary runners)")

    def check_openpyxl(self):
        """Checks if openpyxl is available for template-driven Excel export."""
        try:
            import openpyxl
            ver = getattr(openpyxl, "__version__", "installed")
            self.log_check("Excel Engine (openpyxl)", "PASS", f"openpyxl {ver} available")
        except Exception:
            self.log_check("Excel Engine (openpyxl)", "WARN", "openpyxl is not installed",
                           "Run: pip install openpyxl (needed for Excel export: agent-qa export-excel)")

    def check_project_structure(self):
        """Audits folder layout and configuration integrity for Hub or Spoke projects."""
        # 1. QA Hub Repository Check
        is_hub = (self.target_dir / "skills_manifest.json").exists() or (self.target_dir / ".agents" / "skills").is_dir()
        if is_hub:
            required_dirs = [".agents/skills", ".agents/rules", "tools", "tests"]
            missing = [rd for rd in required_dirs if not (self.target_dir / rd).exists()]
            if not missing:
                skills_dir = self.target_dir / ".agents" / "skills"
                skill_count = len([d for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]) if skills_dir.exists() else 0
                self.log_check("Project Structure (QA Hub)", "PASS", f"QA Hub integrity verified ({skill_count} Skills, Rules, Tools, Unit Tests)")
            else:
                self.log_check("Project Structure (QA Hub)", "FAIL", f"Missing directories: {', '.join(missing)}",
                               "Restore from official Synapse Hub Git repository.")
            return

        # 2. Standalone Host / User Home Detection
        is_user_home = False
        try:
            is_user_home = self.target_dir.resolve() == Path.home().resolve()
        except OSError:
            is_user_home = False

        has_project_marker = any([
            (self.target_dir / marker).exists() for marker in [
                ".git", "package.json", "requirements.txt", "pom.xml", "build.gradle",
                "pytest.ini", "cypress.config.ts", "cypress.config.js",
                "playwright.config.ts", "playwright.config.js", "Keywords", "Scripts"
            ]
        ]) or bool(list(self.target_dir.glob("*.prj")))

        if is_user_home or not has_project_marker:
            self.is_standalone = True
            self.log_check("Project Structure (Standalone)", "PASS",
                           "Host machine environment verified. (To diagnose a specific test project: agent-qa doctor <path>)")
            return

        # 3. Playwright Check
        pkg_json = self.target_dir / "package.json"
        has_playwright_pkg = pkg_json.exists() and "@playwright/test" in pkg_json.read_text(encoding="utf-8", errors="ignore")
        is_playwright = (self.target_dir / "playwright.config.ts").exists() or (self.target_dir / "playwright.config.js").exists() or has_playwright_pkg
        if is_playwright:
            has_tests = (self.target_dir / "tests").is_dir() or (self.target_dir / "e2e").is_dir() or (self.target_dir / "src").is_dir()
            if has_tests:
                self.log_check("Project Structure (Playwright)", "PASS", "Playwright test project structure verified")
            else:
                self.log_check("Project Structure (Playwright)", "WARN", "Missing 'tests/' or 'e2e/' directory for Playwright specs",
                               "Create a 'tests/' directory or run 'npx playwright test --init'")
            return

        # 4. Cypress Check
        is_cypress = (self.target_dir / "cypress.config.ts").exists() or (self.target_dir / "cypress.config.js").exists() or (self.target_dir / "cypress").is_dir()
        if is_cypress:
            if (self.target_dir / "cypress").is_dir():
                self.log_check("Project Structure (Cypress)", "PASS", "Cypress test project structure verified")
            else:
                self.log_check("Project Structure (Cypress)", "WARN", "Missing 'cypress/' directory",
                               "Create a 'cypress/' directory for E2E specs")
            return

        # 5. Pytest / Python Selenium Check
        is_pytest = (self.target_dir / "pytest.ini").exists() or (self.target_dir / "conftest.py").exists()
        has_py_tests = (self.target_dir / "tests").is_dir() or bool(list(self.target_dir.glob("test_*.py")))
        if is_pytest or (has_py_tests and (self.target_dir / "requirements.txt").exists()):
            self.log_check("Project Structure (Pytest)", "PASS", "Python/Pytest test project structure verified")
            return

        # 6. Katalon Studio (Enterprise Web Clean POM)
        is_katalon = bool(list(self.target_dir.glob("*.prj"))) or (self.target_dir / "Keywords").is_dir() or (self.target_dir / "Scripts").is_dir()
        if is_katalon:
            required_dirs = ["Scripts", "Keywords", "Profiles"]
            missing = [rd for rd in required_dirs if not (self.target_dir / rd).exists()]
            if not missing:
                self.log_check("Project Structure (Clean POM)", "PASS", "Clean POM structure verified (Keywords, Profiles, Scripts)")
            else:
                self.log_check("Project Structure (POM)", "WARN" if len(missing) < len(required_dirs) else "FAIL",
                               f"Missing directories: {', '.join(missing)}",
                               "Verify git clone command or select target test project directory.")
            return

        # 7. Generic Test Project (any project with tests/ or test/)
        if (self.target_dir / "tests").is_dir() or (self.target_dir / "test").is_dir() or (self.target_dir / "e2e").is_dir():
            self.log_check("Project Structure (Automated Tests)", "PASS", "Standard automated test directory detected")
            return

        # Fallback: General project structure missing test suite
        self.log_check("Project Structure", "WARN", "No automated test directories detected (tests/, Scripts/, cypress/)",
                       "Run 'agent-qa setup .' to initialize Clean POM / Playwright configuration for this project.")

    def check_network(self):
        """Audits AUT network reachability via BASE_URL configured in environment."""
        env_file = self.target_dir / ".env"
        if env_file.exists():
            try:
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        if k.strip() not in os.environ:
                            os.environ[k.strip()] = v.strip().strip("'\"")
            except OSError as err:
                sys.stderr.write(f"Notice: .env read failed: {err}\n")

        if os.environ.get("AGENT_QA_OFFLINE") == "1":
            self.log_check("Network / Server Base URL", "PASS", "Skipped in offline/air-gapped mode (AGENT_QA_OFFLINE=1)")
            return

        base = os.environ.get("BASE_URL", "").rstrip("/")
        if not base:
            if getattr(self, "is_standalone", False):
                self.log_check("Network / Server Base URL", "PASS", "Host standalone check (configure BASE_URL in project .env when targeting an AUT)")
                return
            self.log_check("Network / Server Base URL", "WARN", "BASE_URL not configured in .env",
                           "Copy .env.example to .env and configure BASE_URL to verify connectivity.")
            return
        test_url = f"{base}/login"
        try:
            # Respect explicit insecure flag or environment variable; default to secure TLS
            allow_insecure = bool(
                getattr(self, "insecure", False)
                or os.environ.get("SYNAPSE_INSECURE_SSL") == "1"
            )
            ctx = ssl.create_default_context()
            if allow_insecure:
                print("  ⚠️ [SECURITY NOTICE] TLS certificate verification is bypassed (--insecure / SYNAPSE_INSECURE_SSL).")
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(test_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:  # nosec B310
                code = resp.getcode()
                if code in (200, 301, 302):
                    self.log_check("Network / Server Base URL", "PASS", f"Connection successful to {test_url} (HTTP {code})")
                else:
                    self.log_check("Network / Server Base URL", "WARN", f"HTTP response code {code}", "Check proxy configuration or corporate network access.")
        except Exception as e:
            self.log_check("Network / Server Base URL", "WARN", f"Direct connection failed ({e})",
                           "Check internet connection or enable VPN if corporate network required.")

    def run_all(self):
        """Runs the complete diagnostic suite and returns 0 if all prerequisites pass."""
        print(f"\n{BOLD}{'='*70}{RESET}")
        print(f"{BOLD}{CYAN} ENTERPRISE AUTOMATION - ENVIRONMENT & ONBOARDING DIAGNOSTIC{RESET}")
        print(f"{BOLD}{'='*70}{RESET}")
        print(f"📁 Target Directory: {self.target_dir}\n")

        self.check_os()
        self.check_git()
        self.check_chrome()
        self.check_java()
        self.check_katalon()
        self.check_node_allure()
        self.check_python_runner()
        self.check_openpyxl()
        self.check_project_structure()
        self.check_network()

        print(f"\n{BOLD}{'='*70}{RESET}")
        if not self.errors:
            print(f"{BOLD}{GREEN}🎉 SUMMARY: ENVIRONMENT IS READY!{RESET}")
            if self.warnings:
                print(f"{YELLOW}Note: {len(self.warnings)} optional warning(s) detected above; address as needed.{RESET}")
        else:
            print(f"{BOLD}{RED}❌ SUMMARY: {len(self.errors)} PREREQUISITE(S) REQUIRE REMEDIATION!{RESET}")
            for name, hint in self.errors:
                print(f"   - {BOLD}{name}:{RESET} {hint}")
        print(f"{BOLD}{'='*70}{RESET}\n")
        return 0 if not self.errors else 1


def main():
    parser = argparse.ArgumentParser(description="Enterprise Environment Diagnostic Tool")
    parser.add_argument("target", nargs="?", default=None, help="Target repository path to diagnose")
    parser.add_argument("--repo", "--path", dest="repo_path", default=None, help="Target repository path")
    parser.add_argument("--insecure", action="store_true", help="Allow unverified SSL certificates during connectivity checks")
    args = parser.parse_args()

    try:
        target_dir = resolve_target_repo(cli_target=args.target, cli_repo=args.repo_path)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        return 1

    runner = DiagnosticRunner(target_dir=target_dir, insecure=args.insecure)
    return runner.run_all()


if __name__ == "__main__":
    sys.exit(main())
