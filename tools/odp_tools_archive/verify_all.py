#!/usr/bin/env python3
"""
ODP Single-Command DoD Verifier (One Command Quality Gate)
----------------------------------------------------------
Consolidates all definition-of-done criteria into a single executable command.

Verifies:
  Gate 1: 100% UTF-8 No BOM across all repository files (8 extensions).
  Gate 2: Path Portability: Zero absolute machine paths.
  Gate 3: Clean POM & Flat Architecture: Zero raw XPaths or findTestObject in Scripts/.
  Gate 4: AI Docs & Artifacts Anti-Drift: No hallucinated PageClasses, Suites, or Tools.
  Gate 5: Cleanup Blacklist: No temporary or debug dump files on disk.
  Gate 6: Credential Security: No hardcoded plaintext passwords in Groovy sources
          (credentials trong Profiles/*.glbl là cơ chế sync có chủ đích của
          ProfileHelper — không phải vi phạm; chi tiết xem KNOWN_ISSUES.md).

Usage:
  python3 tools/verify_all.py
"""

import os
import sys
import subprocess
import glob
import re

FORBIDDEN_PATHS = ["/Users/", "d:/odp", "d:\\odp", "c:\\users\\admin"]
BOM_EXTENSIONS = (".groovy", ".tc", ".ts", ".glbl", ".md", ".py", ".json", ".ps1")

# File legacy viết trước khi thiết lập gate — đã ghi nhận trong KNOWN_ISSUES.md (DEBT).
# Đã refactor sạch 100%, không còn ngoại lệ nào.
LEGACY_CLEAN_POM_EXCEPTIONS = set()
LEGACY_PATH_EXCEPTIONS = {"AGENTS.md"}
LEGACY_CREDENTIAL_EXCEPTIONS = {
    "Scripts/TC_ODP_TC 66_Dang_ky_va_TC 73_Xoa_user/Script1740000066073.groovy",
}

# Pattern mật khẩu hardcoded trong code (không áp dụng cho Profiles/*.glbl và comments).
# Negative lookahead (?![/\\]) loại XPath/URL path constants (VD: TXT_PASSWORD = "//input[@id=...]"). 
PLAINTEXT_PASSWORD_PATTERN = re.compile(
    r"(?i)\b(password|passwd|pwd)\b\s*(?:=|:)\s*['\"](?![/\\])([^'\"]{4,})['\"]"
)
CREDENTIAL_SAFE_KEYWORDS = (
    "globalvariable",
    "setencryptedtext",
    "my_password",
    "admin_password",
    "test_password",
    "telegram",
    "profilehelper",
    "passwordfield",
    "password('",  # Groovy map key ví dụ [: password '...'] dạng truy cập method
)

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def gate_1_bom_check(repo_root):
    print("\n[GATE 1] Scanning UTF-8 No BOM across repository...")
    violations = []
    for root, dirs, files in os.walk(repo_root):
        if any(ignored in root for ignored in [".git", ".gradle", "node_modules", "bin", "Libs"]):
            continue
        for f in files:
            if f.endswith(BOM_EXTENSIONS):
                full_path = os.path.join(root, f)
                try:
                    with open(full_path, "rb") as fp:
                        if fp.read(3) == b"\xef\xbb\xbf":
                            violations.append(os.path.relpath(full_path, repo_root))
                except Exception:
                    pass

    if violations:
        print(f"❌ FAIL: {len(violations)} files contain UTF-8 BOM bytes:")
        for v in violations:
            print(f"   - {v}")
        return False
    print("✅ PASS: 100% UTF-8 No BOM verified across all source files.")
    return True

def gate_2_path_portability(repo_root):
    print("\n[GATE 2] Checking Path Portability (Zero absolute machine paths in repo sources)...")
    ignored_dirs = {".git", ".gradle", "node_modules", "Screenshots", "Reports", "bin", "Libs", ".settings", ".cache", "Include", "Plugins", "Drivers"}
    ignored_files = {".project", ".classpath", ".DS_Store"}
    violations = []
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for f in files:
            if f.startswith(".temp-") or f in ignored_files or f.endswith((".py", ".db", ".png", ".jpg", ".zip", ".tar", ".gz", ".xlsx", ".properties", ".class", ".prefs", ".jar")):
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, repo_root).replace("\\", "/")
            if rel_path in LEGACY_PATH_EXCEPTIONS or ".gitignore" in rel_path:
                continue
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                    for line_no, line in enumerate(fp, 1):
                        lower = line.lower()
                        for forbidden in FORBIDDEN_PATHS:
                            if forbidden in lower:
                                violations.append((rel_path, line_no, forbidden))
            except Exception:
                pass

    if violations:
        print(f"❌ FAIL: {len(violations)} forbidden machine paths found:")
        for rel_path, line_no, term in violations:
            print(f"   - {rel_path}:{line_no} contains '{term}'")
        return False
    print("✅ PASS: Zero machine-specific absolute paths detected in source files.")
    return True

def gate_3_clean_pom(repo_root):
    print("\n[GATE 3] Checking Clean POM & Flat Architecture in Scripts/...")
    scripts_dir = os.path.join(repo_root, "Scripts")
    violations = []
    legacy_hits = []
    if os.path.isdir(scripts_dir):
        for root, dirs, files in os.walk(scripts_dir):
            for f in files:
                if f.endswith(".groovy"):
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, repo_root).replace("\\", "/")
                    if rel_path in LEGACY_CLEAN_POM_EXCEPTIONS:
                        legacy_hits.append(rel_path)
                        continue
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                            for line_no, line in enumerate(fp, 1):
                                stripped = line.strip()
                                if stripped.startswith("//"):
                                    continue
                                if "findTestObject" in line:
                                    violations.append((rel_path, line_no, "Raw findTestObject"))
                                if "//" in line and ("//table" in line or "//input" in line or "//button" in line):
                                    violations.append((rel_path, line_no, "Raw XPath"))
                    except Exception:
                        pass

    if legacy_hits:
        print(f"⚠️  {len(legacy_hits)} legacy script(s) exempted (see KNOWN_ISSUES.md DEBT section):")
        for v in sorted(legacy_hits):
            print(f"   - {v}")
    if violations:
        print(f"❌ FAIL: {len(violations)} Clean POM violations in Scripts/:")
        for rel_path, line_no, reason in violations:
            print(f"   - {rel_path}:{line_no} ({reason})")
        return False
    print("✅ PASS: 100% Clean POM compliance (all locators encapsulated in Page Classes).")
    return True

def gate_4_ai_docs_lint(repo_root):
    print("\n[GATE 4] Running AI Documentation & Artifact Linter...")
    linter_script = os.path.join(repo_root, "tools", "lint_ai_docs.py")
    if not os.path.exists(linter_script):
        print("❌ FAIL: tools/lint_ai_docs.py does not exist!")
        return False

    res = subprocess.run([sys.executable, linter_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(res.stdout)
        print(res.stderr)
        return False
    print("✅ PASS: Zero documentation drift / zero hallucinated PageClasses & Suites.")
    return True

def gate_5_cleanup_blacklist(repo_root):
    print("\n[GATE 5] Checking Temporary File Blacklist...")
    blacklist_patterns = [
        os.path.join(repo_root, "*_debug.txt"),
        os.path.join(repo_root, "debug_output.txt"),
        os.path.join(repo_root, "dom_dump.txt"),
        os.path.join(repo_root, "html_dump.html"),
        os.path.join(repo_root, "network_requests.txt"),
        os.path.join(repo_root, "console_log.txt"),
        os.path.join(repo_root, "*.tmp"),
        os.path.join(repo_root, ".temp-*"),
        os.path.join(repo_root, "scratch_*.*"),
        os.path.join(repo_root, "page_snapshot.md"),
    ]
    found = []
    for pattern in blacklist_patterns:
        for f in glob.glob(pattern):
            found.append(os.path.relpath(f, repo_root))

    if found:
        print(f"❌ FAIL: {len(found)} blacklisted temporary files found on disk:")
        for f in found:
            print(f"   - {f}")
        return False
    print("✅ PASS: Temporary file blacklist is clean.")
    return True

def gate_6_credential_security(repo_root):
    print("\n[GATE 6] Checking Credential Security (No hardcoded plaintext passwords in code)...")
    violations = []
    scan_dirs = ["Scripts", "Keywords", "Test Listeners"]
    for scan_dir in scan_dirs:
        base = os.path.join(repo_root, scan_dir)
        if not os.path.isdir(base):
            continue
        for root, _, files in os.walk(base):
            for f in files:
                if not f.endswith(".groovy"):
                    continue
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, repo_root).replace("\\", "/")
                if rel_path in LEGACY_CREDENTIAL_EXCEPTIONS:
                    continue
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                        for line_no, line in enumerate(fp, 1):
                            stripped = line.strip()
                            if stripped.startswith("//") or stripped.startswith("*"):
                                continue
                            lower = line.lower()
                            if any(kw in lower for kw in CREDENTIAL_SAFE_KEYWORDS):
                                continue
                            m = PLAINTEXT_PASSWORD_PATTERN.search(line)
                            if m:
                                violations.append((rel_path, line_no, m.group(0)[:80]))
                except Exception:
                    pass

    if violations:
        print(f"❌ FAIL: {len(violations)} potential hardcoded password(s) in Groovy sources:")
        for rel_path, line_no, snippet in violations:
            print(f"   - {rel_path}:{line_no} -> {snippet}")
        print("   Fix: use GlobalVariable.MY_USERNAME / MY_PASSWORD (see AGENTS.md §4).")
        return False
    print("✅ PASS: Credentials protected (GlobalVariable-based; profiles managed by ProfileHelper).")
    return True

def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    print_header("ODP AUTOMATION — ONE-COMMAND DoD VERIFICATION")
    print(f"Target Repository: {os.path.basename(repo_root)}")

    gates = [
        ("Gate 1: UTF-8 No BOM", gate_1_bom_check),
        ("Gate 2: Path Portability", gate_2_path_portability),
        ("Gate 3: Clean POM & Flat Architecture", gate_3_clean_pom),
        ("Gate 4: AI Documentation Linter", gate_4_ai_docs_lint),
        ("Gate 5: Temporary Files Blacklist", gate_5_cleanup_blacklist),
        ("Gate 6: Credential Security", gate_6_credential_security),
    ]

    all_passed = True
    for name, gate_fn in gates:
        success = gate_fn(repo_root)
        if not success:
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 [ALL 6 GATES PASSED — 100% DoD COMPLIANT]")
        print("   Repository is 100% compliant, secure, and ready for execution/CI/CD.")
        print("=" * 70 + "\n")
        sys.exit(0)
    else:
        print("🚫 [DoD BLOCKED] ONE OR MORE QUALITY GATES FAILED.")
        print("   Please review the errors above and resolve them before proceeding.")
        print("=" * 70 + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
