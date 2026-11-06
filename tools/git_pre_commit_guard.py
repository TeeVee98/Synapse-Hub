#!/usr/bin/env python3
"""
Enterprise Git Pre-Commit Architecture & Discipline Guard
--------------------------------------------------
Automated gatekeeper executed before every 'git commit'.
Ensures:
  1. 100% UTF-8 No BOM across repository files.
  2. Flat Architecture & Clean POM: Zero raw XPaths or findTestObject in Scripts/TC-xxx.
  3. Path Portability: Zero absolute machine paths (Users/, phungcao, /path/to/project).
"""

import sys
import os
import re
import shlex
import subprocess

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

FORBIDDEN_PATHS = ["/Users/", "C:\\Workspace\\", "D:\\Workspace\\", "file:///c:", "file:///d:"]
FORBIDDEN_HUB_PREFIXES = (
    "Scripts/", "Keywords/", "Object Repository/", "Test Suites/", "Data Files/", "Include/",
    "e2e/", "pages/", "cypress/"
)

def is_test_script(file_path: str) -> bool:
    """
    Identifies test scripts across polyglot test frameworks:
    - Katalon (Scripts/*.groovy)
    - Playwright / Cypress (e2e/, cypress/, *.spec.[tj]sx?, *.test.[tj]sx?, *.cy.[tj]sx?)
    - Pytest (test_*.py, *_test.py)
    """
    if not file_path:
        return False
    norm = file_path.replace("\\", "/")
    base = os.path.basename(norm).lower()
    norm_lower = norm.lower()

    # Katalon scripts
    if "scripts/" in norm_lower and norm_lower.endswith(".groovy"):
        return True

    # Playwright / Cypress / E2E directory structures
    if any(norm_lower.startswith(p) or f"/{p}" in norm_lower for p in ("e2e/", "cypress/")):
        if norm_lower.endswith((".ts", ".js", ".mjs", ".cjs", ".tsx", ".jsx", ".py")):
            return True

    # Spec and test suffixes for JS/TS
    test_suffixes = (
        ".spec.ts", ".test.ts", ".spec.js", ".test.js",
        ".spec.tsx", ".test.tsx", ".spec.jsx", ".test.jsx",
        ".cy.ts", ".cy.js", ".cy.tsx", ".cy.jsx"
    )
    if any(suffix in base for suffix in test_suffixes):
        return True

    # Pytest / Python test scripts
    if norm_lower.endswith(".py"):
        if base.startswith("test_") or base.endswith("_test.py"):
            return True

    return False

def run_cmd(cmd, timeout: float = 60.0):
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    try:
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, returncode=124, stdout="", stderr=f"Command timed out after {timeout}s")

def check_bom(files):
    bom_files = []
    for f in files:
        if not os.path.exists(f):
            continue
        try:
            with open(f, "rb") as fp:
                if fp.read(3) == b"\xef\xbb\xbf":
                    bom_files.append(f)
        except OSError as err:
            sys.stderr.write(f"Notice: Could not read {f}: {err}\n")
    return bom_files

def check_forbidden_paths(files):
    violations = []
    for f in files:
        if not os.path.exists(f) or os.path.isdir(f):
            continue
        # Skip this guard script itself and binary files
        if f.endswith((".py", ".db", ".png", ".jpg", ".zip", ".tar", ".gz")):
            continue
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                for line_no, line in enumerate(fp, 1):
                    # Allow mention in historical report or gitignore
                    if "FINAL_REPORT.md" in f or ".gitignore" in f:
                        continue
                    for forbidden in FORBIDDEN_PATHS:
                        if forbidden in line:
                            violations.append((f, line_no, forbidden))
        except OSError as err:
            sys.stderr.write(f"Notice: Could not read {f}: {err}\n")
    return violations

def check_scripts_clean_pom(files):
    violations = []
    is_hub = os.path.exists("skills_manifest.json") and os.path.isdir(".agents")
    xpath_pattern = re.compile(
        r'(?<!:)//(?:\*|table|input|button|div|span|form|select|textarea|a(?=[\[/@\s\'"]|$))'
    )
    for f in files:
        if not os.path.exists(f):
            continue
        norm = f.replace("\\", "/")
        # In Hub repository, ignore Hub's internal unit/functional test suite (tests/test_*.py)
        if is_hub and norm.startswith("tests/"):
            continue
        if is_test_script(f):
            try:
                with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                    for line_no, line in enumerate(fp, 1):
                        stripped = line.strip()
                        if stripped.startswith("//") or stripped.startswith("#"):
                            continue
                        if "findTestObject" in line:
                            violations.append((f, line_no, "Raw findTestObject is forbidden in test scripts"))
                        if "xpath=" in line:
                            violations.append((f, line_no, "Explicit xpath= locator is forbidden in test scripts"))
                        # Strip standard HTTP/HTTPS URLs before checking XPath syntax
                        line_no_urls = re.sub(r'https?://[^\s\'"]+', '', line)
                        if "//" in line_no_urls and xpath_pattern.search(line_no_urls):
                            violations.append((f, line_no, "Raw XPath is forbidden in test scripts"))
            except OSError as err:
                sys.stderr.write(f"Notice: Could not parse {f}: {err}\n")
    return violations

def main():
    # If called with --install
    if len(sys.argv) > 1 and sys.argv[1] == "--install":
        git_dir = run_cmd("git rev-parse --git-dir").stdout.strip()
        if not git_dir or not os.path.isdir(git_dir):
            print("❌ Error: Not a git repository.")
            sys.exit(1)

        # 1. Pre-commit hook
        pre_commit_path = os.path.join(git_dir, "hooks", "pre-commit")
        pre_commit_content = (
            "#!/bin/sh\n"
            "# Enterprise Pre-Commit Guard\n"
            "python3 \"$0/../tools/git_pre_commit_guard.py\" 2>/dev/null || python tools/git_pre_commit_guard.py \"$@\"\n"
        )
        with open(pre_commit_path, "w", encoding="utf-8") as fp:
            fp.write(pre_commit_content)
        os.chmod(pre_commit_path, 0o755)

        # 2. Post-merge hook (Auto-sync memory cache on git pull)
        post_merge_path = os.path.join(git_dir, "hooks", "post-merge")
        post_merge_content = (
            "#!/bin/sh\n"
            "# Enterprise Post-Merge Hook: Automatically initialize & sync Central Agent Memory\n"
            "if [ -f \"tools/cache_resolver.py\" ]; then\n"
            "    echo \"🔄 [Git Post-Merge] Syncing Central Agent Memory...\"\n"
            "    python3 \"$0/../tools/cache_resolver.py\" init 2>/dev/null || python tools/cache_resolver.py init 2>/dev/null || true\n"
            "fi\n"
        )
        with open(post_merge_path, "w", encoding="utf-8") as fp:
            fp.write(post_merge_content)
        os.chmod(post_merge_path, 0o755)

        # 3. Pre-push hook (Auto-sync memory cache on git push)
        pre_push_path = os.path.join(git_dir, "hooks", "pre-push")
        pre_push_content = (
            "#!/bin/sh\n"
            "# Enterprise Pre-Push Hook: Synchronize Central Agent Memory before pushing\n"
            "if [ -f \"tools/cache_resolver.py\" ]; then\n"
            "    echo \"🔄 [Git Pre-Push] Synchronizing Central Agent Memory to local cache...\"\n"
            "    python3 \"$0/../tools/cache_resolver.py\" sync 2>/dev/null || python tools/cache_resolver.py sync 2>/dev/null || true\n"
            "fi\n"
        )
        with open(pre_push_path, "w", encoding="utf-8") as fp:
            fp.write(pre_push_content)
        os.chmod(pre_push_path, 0o755)

        print("✅ Git hooks installed successfully:")
        print(f"   - Pre-commit: {pre_commit_path}")
        print(f"   - Post-merge: {post_merge_path} (Auto-runs cache_resolver.py init on git pull)")
        print(f"   - Pre-push:   {pre_push_path} (Auto-runs cache_resolver.py sync on git push)")
        sys.exit(0)

    # Get staged files
    res = run_cmd("git diff --cached --name-only")
    staged_files = [f.strip() for f in res.stdout.splitlines() if f.strip()]

    if not staged_files:
        sys.exit(0)

    errors_found = False

    # 0. Hub Pollution Guard (When committing inside Synapse-Hub)
    is_hub = os.path.exists("skills_manifest.json") and os.path.isdir(".agents")
    if is_hub:
        polluting_files = []
        for f in staged_files:
            norm = f.replace("\\", "/")
            norm_lower = norm.lower()
            # Katalon Scripts/ is case-sensitive or .groovy to avoid collision with Hub's scripts/
            is_katalon_script = norm.startswith("Scripts/") or (norm_lower.startswith("scripts/") and norm_lower.endswith(".groovy"))
            is_forbidden_prefix = is_katalon_script or any(
                p.lower() != "scripts/" and norm_lower.startswith(p.lower())
                for p in FORBIDDEN_HUB_PREFIXES
            )
            is_hub_internal_test = norm_lower.startswith("tests/")
            if is_forbidden_prefix or (is_test_script(f) and not is_hub_internal_test):
                polluting_files.append(f)
        if polluting_files:
            print("❌ [PRE-COMMIT BLOCKED] Target project business test files detected in Synapse-Hub:")
            for pf in polluting_files:
                print(f"   - {pf}")
            print("\n🚨 CWD CONFUSION GUARD: You are attempting to commit target project code into Synapse-Hub!")
            print("   Please unstage these files ('git reset HEAD') and commit them inside your target project workspace.")
            errors_found = True

    # 1. BOM Check
    target_exts = (
        ".groovy", ".tc", ".ts", ".js", ".mjs", ".cjs", ".tsx", ".jsx",
        ".glbl", ".md", ".py", ".json", ".ps1", ".sh", ".yml", ".yaml"
    )
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
        print("❌ [PRE-COMMIT BLOCKED] Clean POM violation in test scripts:")
        for f, line_no, reason in pom_violations:
            print(f"   - {f}:{line_no} ({reason})")
        errors_found = True

    # 4. AI Documentation & Anti-Drift Guard
    doc_affected = any(f.endswith(".md") or ".agents" in f or "tools/" in f or "Keywords/" in f or "Test Suites/" in f for f in staged_files)
    if doc_affected:
        linter_script = os.path.join(os.path.dirname(__file__), "lint_ai_docs.py")
        if os.path.exists(linter_script):
            res = run_cmd([sys.executable, linter_script], timeout=60.0)
            if res.returncode != 0:
                print("❌ [PRE-COMMIT BLOCKED] AI Documentation Linter detected drift:")
                print(res.stdout.strip())
                errors_found = True

    # 5. Keywords/ change -> Auto-regenerate Repo Map
    keywords_affected = any(f.startswith("Keywords/") and f.endswith(".groovy") for f in staged_files)
    if keywords_affected:
        repo_map_script = os.path.join(os.path.dirname(__file__), "repo_map.py")
        if os.path.exists(repo_map_script):
            run_cmd([sys.executable, repo_map_script], timeout=60.0)
            # Stage updated repo_map files
            run_cmd(["git", "add", "tools/repo_map.txt", "tools/repo_map.json"], timeout=30.0)

    # 6. Scripts/ change -> Static Defect Linter (Meta Infer-Style)
    scripts_affected = any(f.startswith("Scripts/") and f.endswith(".groovy") for f in staged_files)
    if scripts_affected:
        infer_script = os.path.join(os.path.dirname(__file__), "infer_linter.py")
        if os.path.exists(infer_script):
            res = run_cmd([sys.executable, infer_script], timeout=60.0)
            if res.returncode != 0:
                print("❌ [PRE-COMMIT BLOCKED] Static Defect Sentinel detected critical issues in staged scripts:")
                print(res.stdout.strip())
                errors_found = True

    if errors_found:
        print("\n🚫 Commit aborted. Please fix violations before committing.")
        sys.exit(1)
    else:
        print("✅ [PRE-COMMIT GUARD] All quality gates passed (No BOM, Clean POM, Clean Paths, Docs Aligned, Static Lint Pass).")
        sys.exit(0)

if __name__ == "__main__":
    main()
