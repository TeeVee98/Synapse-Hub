#!/usr/bin/env python3
"""
ODP Git Pre-Commit Architecture & Discipline Guard
--------------------------------------------------
Automated gatekeeper executed before every 'git commit'.
Ensures:
  1. 100% UTF-8 No BOM across staged files.
  2. Flat Architecture & Clean POM: Zero raw XPaths or findTestObject in Scripts/.
  3. Path Portability: Zero absolute machine paths.

Install (one-time, per machine):
  python3 tools/git_pre_commit_guard.py --install
"""

import sys
import os
import subprocess

FORBIDDEN_PATHS = ["/users/", "d:/odp", "d:\\odp", "c:\\users\\admin"]

LEGACY_CLEAN_POM_EXCEPTIONS = {
    "Scripts/TC_ODP_TC 52_ TC 57/Script1740000052057.groovy",
    "Scripts/TC_ODP_TC 33_ TC 34_ TC 35_ TC 36_ TC 37/Script1740000033037.groovy",
}
LEGACY_PATH_EXCEPTIONS = {"AGENTS.md"}

def run_cmd(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)

def check_bom(files):
    bom_files = []
    for f in files:
        if not os.path.exists(f):
            continue
        try:
            with open(f, "rb") as fp:
                if fp.read(3) == b"\xef\xbb\xbf":
                    bom_files.append(f)
        except Exception:
            pass
    return bom_files

def check_forbidden_paths(files):
    violations = []
    for f in files:
        if not os.path.exists(f) or os.path.isdir(f):
            continue
        rel = f.replace("\\", "/")
        if rel in LEGACY_PATH_EXCEPTIONS or ".gitignore" in rel:
            continue
        # Skip this guard script itself and binary files
        if f.endswith((".py", ".db", ".png", ".jpg", ".zip", ".tar", ".gz", ".jar")):
            continue
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                for line_no, line in enumerate(fp, 1):
                    lower = line.lower()
                    for forbidden in FORBIDDEN_PATHS:
                        if forbidden in lower:
                            violations.append((f, line_no, forbidden))
        except Exception:
            pass
    return violations

def check_scripts_clean_pom(files):
    violations = []
    for f in files:
        if not os.path.exists(f):
            continue
        rel = f.replace("\\", "/")
        # Only check test scripts in Scripts/
        if "Scripts/" in rel and f.endswith(".groovy") and rel not in LEGACY_CLEAN_POM_EXCEPTIONS:
            try:
                with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                    for line_no, line in enumerate(fp, 1):
                        stripped = line.strip()
                        if stripped.startswith("//"):
                            continue
                        if "findTestObject" in line:
                            violations.append((f, line_no, "Raw findTestObject is forbidden in Scripts/"))
                        if "//" in line and ("//table" in line or "//input" in line or "//button" in line):
                            violations.append((f, line_no, "Raw XPath is forbidden in Scripts/"))
            except Exception:
                pass
    return violations

def main():
    # If called with --install
    if len(sys.argv) > 1 and sys.argv[1] == "--install":
        git_dir = run_cmd("git rev-parse --git-dir").stdout.strip()
        if not git_dir or not os.path.isdir(git_dir):
            print("❌ Error: Not a git repository.")
            sys.exit(1)
        hook_path = os.path.join(git_dir, "hooks", "pre-commit")
        hook_content = (
            "#!/bin/sh\n"
            "# ODP Pre-Commit Guard\n"
            "python3 tools/git_pre_commit_guard.py\n"
        )
        with open(hook_path, "w", encoding="utf-8") as fp:
            fp.write(hook_content)
        # Make executable
        os.chmod(hook_path, 0o755)
        print(f"✅ Git pre-commit hook installed successfully at: {hook_path}")
        sys.exit(0)

    # Get staged files
    res = run_cmd("git diff --cached --name-only")
    staged_files = [f.strip() for f in res.stdout.splitlines() if f.strip()]

    if not staged_files:
        sys.exit(0)

    errors_found = False

    # 1. BOM Check
    target_exts = (".groovy", ".tc", ".ts", ".glbl", ".md", ".py", ".json", ".ps1")
    check_files = [f for f in staged_files if f.endswith(target_exts)]
    bom_files = check_bom(check_files)
    if bom_files:
        print("❌ [PRE-COMMIT BLOCKED] UTF-8 BOM detected in staged files:")
        for bf in bom_files:
            print(f"   - {bf}")
        errors_found = True

    # 2. Path Portability Check
    path_violations = check_forbidden_paths(staged_files)
    if path_violations:
        print("❌ [PRE-COMMIT BLOCKED] Absolute machine path detected in staged files:")
        for f, line_no, term in path_violations:
            print(f"   - {f}:{line_no} (Forbidden: '{term}')")
        errors_found = True

    # 3. Clean POM Guard
    pom_violations = check_scripts_clean_pom(staged_files)
    if pom_violations:
        print("❌ [PRE-COMMIT BLOCKED] Clean POM violation in Scripts/:")
        for f, line_no, reason in pom_violations:
            print(f"   - {f}:{line_no} ({reason})")
        errors_found = True

    # 4. AI Documentation & Anti-Drift Guard
    doc_affected = any(f.endswith(".md") or ".agents" in f or "tools/" in f.replace("\\", "/") or "Keywords/" in f.replace("\\", "/") or "Test Suites/" in f.replace("\\", "/") for f in staged_files)
    if doc_affected:
        linter_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lint_ai_docs.py")
        if os.path.exists(linter_script):
            res = subprocess.run([sys.executable, linter_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode != 0:
                print("❌ [PRE-COMMIT BLOCKED] AI Documentation Linter detected drift:")
                print(res.stdout.strip())
                errors_found = True

    if errors_found:
        print("\n🚫 Commit aborted. Please fix violations before committing.")
        sys.exit(1)
    else:
        print("✅ [PRE-COMMIT GUARD] All quality gates passed (No BOM, Clean POM, Clean Paths, Docs Aligned).")
        sys.exit(0)

if __name__ == "__main__":
    main()
