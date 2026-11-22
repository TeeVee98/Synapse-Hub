#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Enterprise Git Pre-Commit Architecture & Discipline Guard
--------------------------------------------------
Automated gatekeeper executed before every 'git commit'.
Ensures:
  1. 100% UTF-8 No BOM across repository files.
  2. Flat Architecture & Clean POM: Zero raw XPaths or findTestObject in Scripts/TC-xxx.
  3. Path Portability: Zero absolute machine paths (Users/, phungcao, /path/to/project).
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


import sys
import os
import re
import shlex
import subprocess
import json
from typing import List

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

FORBIDDEN_PATHS = ["/Users/", "/home/", "C:\\Workspace\\", "D:\\Workspace\\", "file:///c:", "file:///d:"]
FORBIDDEN_HUB_PREFIXES = (
    "Scripts/", "Keywords/", "Object Repository/", "Test Suites/", "Data Files/", "Include/",
    "e2e/", "pages/", "cypress/"
)

def check_no_verify_attempt(args: list) -> bool:
    """Block any bypass attempt using --no-verify flag (Inspired by wshobson block-no-verify)."""
    if any(arg in ("--no-verify", "-n") for arg in args):
        print("❌ [CRITICAL SECURITY BLOCKED] Git pre-commit bypass flag (--no-verify / -n) is strictly forbidden in Synapse Hub.")
        print("   All commits must adhere to the 10 DoD Quality Gates without exception.")
        return False
    return True

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

    # Scratchpad sandbox exemption for rapid prototyping / POCs
    if norm_lower.startswith("scratch/") or "/scratch/" in norm_lower:
        return False

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

def check_forbidden_paths(files=None, diff_text=None):
    r"""
    Checks for forbidden absolute machine paths (Users/, /home/, C:\Workspace, etc.).
    When diff_text is provided, scans ONLY added lines in the diff (+ lines),
    preventing false positives on existing regex definitions, historical logs, or doc files.
    When diff_text is not provided or files is passed alone, falls back to full-file scanning.
    """
    violations = []
    exempt_basenames = {
        "git_pre_commit_guard.py", "verify_all.py", "base.py",
        "gate_02_portability.py", "test_git_pre_commit_guard.py", "test_tools.py"
    }

    # 1. If diff_text is provided, scan ONLY added lines (+) in staged diff
    if diff_text:
        current_file = "staged_diff"
        line_num = 0
        for raw_line in diff_text.splitlines():
            if raw_line.startswith("diff --git "):
                parts = raw_line.split()
                if len(parts) >= 4:
                    current_file = parts[3].lstrip("b/")
                line_num = 0
                continue
            elif raw_line.startswith("+++ b/"):
                current_file = raw_line[6:].strip()
                line_num = 0
                continue
            elif raw_line.startswith("@@"):
                m = re.search(r'\+(\d+)', raw_line)
                if m:
                    line_num = int(m.group(1)) - 1
                continue

            if raw_line.startswith(" ") or raw_line.startswith("+"):
                line_num += 1

            if not raw_line.startswith("+") or raw_line.startswith("+++"):
                continue

            line = raw_line[1:]

            # Exemption checks for current_file
            base = os.path.basename(current_file)
            if base in exempt_basenames:
                continue
            if any(p in current_file for p in ("FINAL_REPORT.md", "AUDIT_REPORT.md", "PROJECT_HEALTH_REPORT.md", ".gitignore")):
                continue
            if current_file.endswith((".db", ".png", ".jpg", ".jpeg", ".zip", ".tar", ".gz", ".ico", ".bin")):
                continue

            for forbidden in FORBIDDEN_PATHS:
                if forbidden in line:
                    violations.append((current_file, line_num, forbidden))

        return violations

    # 2. Fallback: Full-file scanning when no diff_text is provided
    if files:
        for f in files:
            if not os.path.exists(f) or os.path.isdir(f):
                continue
            if os.path.basename(f) in exempt_basenames or f.endswith(
                (".db", ".png", ".jpg", ".jpeg", ".zip", ".tar", ".gz", ".ico", ".bin")
            ):
                continue
            try:
                with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                    for line_no, line in enumerate(fp, 1):
                        if any(p in f for p in ("FINAL_REPORT.md", "AUDIT_REPORT.md", "PROJECT_HEALTH_REPORT.md", ".gitignore")):
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
    semantic_locator_pattern = re.compile(
        r'(?:page|frame)\.(?:getByRole|getByLabel|getByPlaceholder|getByText|getByTestId|getByAltText|getByTitle)\s*\('
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
                        if semantic_locator_pattern.search(line):
                            violations.append((f, line_no, "Raw Playwright semantic locator is forbidden in test scripts (encapsulate in Page Class)"))
                        # Strip standard HTTP/HTTPS URLs before checking XPath syntax
                        line_no_urls = re.sub(r'https?://[^\s\'"]+', '', line)
                        if "//" in line_no_urls and xpath_pattern.search(line_no_urls):
                            violations.append((f, line_no, "Raw XPath is forbidden in test scripts"))
            except OSError as err:
                sys.stderr.write(f"Notice: Could not parse {f}: {err}\n")
    return violations


# Gate 6 High-Confidence Secret Scanning Patterns (Mirroring tools/verify_all.py Gate 6)
GATE_6_SECRET_PATTERNS = [
    (re.compile(r'\bghp_[0-9a-zA-Z]{36}\b'), "GitHub Personal Access Token"),
    (re.compile(r'\bgithub_pat_[0-9a-zA-Z_]{82}\b'), "GitHub Fine-Grained Personal Access Token"),
    (re.compile(r'\bAKIA[0-9A-Z]{16}\b'), "AWS Access Key ID"),
    (re.compile(r'\bsk_(?:live|test)_[0-9a-zA-Z]{24,}\b'), "Stripe Secret Key"),
    (re.compile(r'\bxox[baprs]-[0-9a-zA-Z-]{10,48}\b'), "Slack API Token"),
    (re.compile(r'\bAIza[0-9A-Za-z-_]{35}\b'), "Google API Key"),
    (re.compile(r'-----BEGIN (?:RSA|OPENSSH|EC|DSA|PGP)?\s?PRIVATE KEY-----'), "Private Key Header"),
    (re.compile(r'\beyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b'), "JSON Web Token (JWT)"),
]

PASSWORD_PATTERNS = [
    (re.compile(r'(?i)\b(?:Password@?\d+|Admin@?\d+|Root@?\d+|Default@?\d+)\b'), "Known Default Password"),
    (re.compile(r'(?i)\b(?:password|passwd|pwd)\s*[:=]\s*[\x22\x27][^\x22\x27]{4,}[\x22\x27]'), "Hardcoded Plaintext Password Assignment"),
]

PASSWORD_ALLOWLIST_INDICATORS = [
    "System.getenv", "os.getenv", "os.environ", "process.env",
    "dummy", "placeholder", "***", "<password>",
    "secret_patterns", "<name>PASSWORD</name>", 'password = ""', "password = ''",
    "type=str", "help="
]

POLYGLOT_FALLBACK_PATTERNS = [
    (re.compile(r'process\.env\.[A-Za-z0-9_]*(?:PASS|SECRET|PWD|AUTH_TOKEN|API_KEY|PRIVATE_KEY)[A-Za-z0-9_]*\s*(?:\|\||\?\?)\s*[\'"][^\'"]{4,}[\'"]', re.IGNORECASE), "JS/TS Fallback Credential behind Env Query"),
    (re.compile(r'(?:os\.getenv|os\.environ\.get)\s*\(\s*[\'"][A-Za-z0-9_]*(?:PASS|SECRET|PWD|AUTH_TOKEN|API_KEY|PRIVATE_KEY)[A-Za-z0-9_]*[\'"]\s*,\s*[\'"][^\'"]{4,}[\'"]\s*\)', re.IGNORECASE), "Python Fallback Credential behind Env Query"),
    (re.compile(r'(?:vars\.get|System\.getenv)\s*\(\s*[\'"][A-Za-z0-9_]*(?:PASS|SECRET|PWD|AUTH_TOKEN|API_KEY|PRIVATE_KEY)[A-Za-z0-9_]*[\'"]\s*\)\s*\?:\s*[\'"][^\'"]{4,}[\'"]', re.IGNORECASE), "JVM/Groovy Fallback Credential behind Env Query"),
]


def check_secrets(files=None, diff_text=None):
    """
    Scans staged files and/or git diff text for high-confidence secrets (Gate 6).
    Honors # gate6-allowlist comments on the same line to support synthetic fixtures.
    Returns a list of violations: [(file_path, line_no, description), ...]
    """
    violations = []
    allowlist_token = "# gate6-allowlist"

    # Self-exclusion and test scanner file exemptions
    exempt_files = {
        "git_pre_commit_guard.py", "verify_all.py",
        "test_tools.py", "test_git_pre_commit_guard.py", "test_audit_remediation_e2e.py",
        "AUDIT_REMEDIATION_PLAN.md"
    }

    # 1. If diff_text is provided, scan added lines in the staged diff
    if diff_text:
        current_file = "staged_diff"
        line_num = 0
        for raw_line in diff_text.splitlines():
            if raw_line.startswith("diff --git "):
                parts = raw_line.split()
                if len(parts) >= 4:
                    current_file = parts[3].lstrip("b/")
                line_num = 0
                continue
            elif raw_line.startswith("+++ b/"):
                current_file = raw_line[6:].strip()
                line_num = 0
                continue
            elif raw_line.startswith("@@"):
                m = re.search(r'\+(\d+)', raw_line)
                if m:
                    line_num = int(m.group(1)) - 1
                continue

            if raw_line.startswith(" ") or (raw_line.startswith("+") and not raw_line.startswith("+++")):
                line_num += 1

            if not raw_line.startswith("+") or raw_line.startswith("+++"):
                continue

            line = raw_line[1:]
            base_name = os.path.basename(current_file)
            if base_name in exempt_files or current_file.endswith(
                (".png", ".jpg", ".jpeg", ".zip", ".tar", ".gz", ".ico", ".bin", ".db")
            ):
                continue

            if allowlist_token in line or "#gate6-allowlist" in line:
                continue

            # Check high-confidence token patterns
            for pat, desc in GATE_6_SECRET_PATTERNS:
                if pat.search(line):
                    violations.append((current_file, line_num, desc))
                    break

            # Check polyglot fallback credentials
            for pat, desc in POLYGLOT_FALLBACK_PATTERNS:
                if pat.search(line):
                    violations.append((current_file, line_num, desc))
                    break

            # Check password patterns
            if not any(ind in line for ind in PASSWORD_ALLOWLIST_INDICATORS):
                for pat, desc in PASSWORD_PATTERNS:
                    if pat.search(line):
                        violations.append((current_file, line_num, desc))
                        break

    # 2. If files list is provided, scan files directly
    if files:
        for f in files:
            if not os.path.exists(f) or os.path.isdir(f):
                continue
            base_name = os.path.basename(f)
            if base_name in exempt_files or f.endswith(
                (".png", ".jpg", ".jpeg", ".zip", ".tar", ".gz", ".ico", ".bin", ".db")
            ):
                continue
            try:
                with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                    for line_no, line in enumerate(fp, 1):
                        if allowlist_token in line or "#gate6-allowlist" in line:
                            continue

                        # Check high-confidence tokens
                        for pat, desc in GATE_6_SECRET_PATTERNS:
                            if pat.search(line):
                                violations.append((f, line_no, desc))
                                break

                        # Check polyglot fallback credentials
                        for pat, desc in POLYGLOT_FALLBACK_PATTERNS:
                            if pat.search(line):
                                violations.append((f, line_no, desc))
                                break

                        # Check passwords
                        if not any(ind in line for ind in PASSWORD_ALLOWLIST_INDICATORS):
                            for pat, desc in PASSWORD_PATTERNS:
                                if pat.search(line):
                                    violations.append((f, line_no, desc))
                                    break
            except OSError as err:
                sys.stderr.write(f"Notice: Could not scan {f} for secrets: {err}\n")

    # De-duplicate violations while preserving order
    deduped = []
    seen = set()
    for v in violations:
        key = (v[0], v[1], v[2])
        if key not in seen:
            seen.add(key)
            deduped.append(v)
    return deduped


# Alias for backward-compatibility and diverse test imports
scan_secrets = check_secrets


def check_author_integrity(files=None, repo_root=None):
    """
    Pre-flight author integrity check ensuring staged source files preserve
    mandatory SPDX and author attribution headers.
    Returns list of missing/violating file descriptions.
    """
    violations = []
    root = repo_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_files = files if files is not None else []

    # If no files specified, run full author_integrity tool check
    if not target_files:
        author_tool = os.path.join(os.path.dirname(__file__), "author_integrity.py")
        if os.path.exists(author_tool):
            res = run_cmd([sys.executable, author_tool], timeout=60.0)
            if res.returncode != 0:
                violations.append("Author attribution or license integrity check failed")
        return violations

    source_exts = (".py", ".ts", ".groovy")
    for f in target_files:
        if not f.endswith(source_exts) or not os.path.isfile(f):
            continue
        # Skip vendor/build/cache directories and scratch sandbox
        norm = f.replace("\\", "/")
        if any(ignored in norm for ignored in ("node_modules/", ".git/", "__pycache__/", "build/", "dist/", "scratch/")):
            continue
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                header = fp.read(800)
            has_author = ("Thế Vị" in header or "TeeVee98" in header or "TeeVee998" in header) and "SPDX-FileCopyrightText" in header
            has_license = "SPDX-License-Identifier" in header
            if not (has_author and has_license):
                violations.append(f"{f}: Missing mandatory SPDX author header or MIT license notice")
        except OSError as err:
            violations.append(f"{f}: Could not inspect file header: {err}")

    return violations


def check_project_state_invariants(repo_root: str) -> List[str]:
    """
    Check 9: Anthropic & LangChain State Invariant Guard.
    Ensures that if project_state.json exists:
    1. It is valid JSON conforming to schema.
    2. There is no desynchronization drift with PROJECT_STATE.md.
    3. Blocks commit if schema is corrupted.
    """
    violations = []
    json_path = os.path.join(repo_root, "project_state.json")
    md_path = os.path.join(repo_root, "PROJECT_STATE.md")

    if not os.path.exists(json_path):
        return violations

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        violations.append(f"project_state.json is corrupted or invalid JSON: {e}")
        return violations

    if "schema_version" not in data or "tasks" not in data:
        violations.append("project_state.json missing mandatory schema fields ('schema_version', 'tasks').")

    if os.path.exists(md_path):
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                md_content = f.read()
            if data.get("project") and f"- **Project:** `{data.get('project')}`" not in md_content:
                violations.append("Desynchronization drift: PROJECT_STATE.md project name does not match project_state.json.")
        except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
            pass

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
            "for p in \"tools/lint/git_pre_commit_guard.py\" \"tools/git_pre_commit_guard.py\"; do\n"
            "    if [ -f \"$p\" ]; then\n"
            "        exec python3 \"$p\" \"$@\"\n"
            "    fi\n"
            "done\n"
        )
        with open(pre_commit_path, "w", encoding="utf-8") as fp:
            fp.write(pre_commit_content)
        os.chmod(pre_commit_path, 0o755)

        # 2. Post-merge hook (Auto-sync memory cache on git pull)
        post_merge_path = os.path.join(git_dir, "hooks", "post-merge")
        post_merge_content = (
            "#!/bin/sh\n"
            "# Enterprise Post-Merge Hook: Automatically initialize & sync Central Agent Memory\n"
            "for p in \"tools/core/cache_resolver.py\" \"tools/cache_resolver.py\"; do\n"
            "    if [ -f \"$p\" ]; then\n"
            "        echo \"🔄 [Git Post-Merge] Syncing Central Agent Memory...\"\n"
            "        python3 \"$p\" init 2>/dev/null || true\n"
            "        break\n"
            "    fi\n"
            "done\n"
        )
        with open(post_merge_path, "w", encoding="utf-8") as fp:
            fp.write(post_merge_content)
        os.chmod(post_merge_path, 0o755)

        # 3. Pre-push hook (Auto-sync memory cache on git push)
        pre_push_path = os.path.join(git_dir, "hooks", "pre-push")
        pre_push_content = (
            "#!/bin/sh\n"
            "# Enterprise Pre-Push Hook: Synchronize Central Agent Memory before pushing\n"
            "for p in \"tools/core/cache_resolver.py\" \"tools/cache_resolver.py\"; do\n"
            "    if [ -f \"$p\" ]; then\n"
            "        echo \"🔄 [Git Pre-Push] Synchronizing Central Agent Memory to local cache...\"\n"
            "        python3 \"$p\" sync 2>/dev/null || true\n"
            "        break\n"
            "    fi\n"
            "done\n"
        )
        with open(pre_push_path, "w", encoding="utf-8") as fp:
            fp.write(pre_push_content)
        os.chmod(pre_push_path, 0o755)

        print("✅ Git hooks installed successfully:")
        print(f"   - Pre-commit: {pre_commit_path}")
        print(f"   - Post-merge: {post_merge_path} (Auto-runs cache_resolver.py init on git pull)")
        print(f"   - Pre-push:   {pre_push_path} (Auto-runs cache_resolver.py sync on git push)")
        sys.exit(0)

    # Block --no-verify attempt
    if not check_no_verify_attempt(sys.argv[1:]):
        sys.exit(1)

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

            # Scratchpad sandbox exemption for rapid prototyping / POCs
            if norm_lower.startswith("scratch/") or "/scratch/" in norm_lower:
                continue

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

    # 2. Path Portability Check (Diff Hunk Scanning to eliminate false-positives)
    diff_res = run_cmd("git diff --cached")
    path_violations = check_forbidden_paths(staged_files, diff_text=diff_res.stdout)
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

    # 6. Test scripts change -> Static Defect Linter (Zero-Sleep & Smart Wait Sentinel - Boost B6)
    test_prefixes = ("Scripts/", "tests/", "test/", "e2e/", "specs/", "cypress/")
    test_exts = (".groovy", ".py", ".ts", ".js")
    scripts_affected = any(f.startswith(test_prefixes) and f.endswith(test_exts) for f in staged_files)
    if scripts_affected:
        infer_script = os.path.join(os.path.dirname(__file__), "infer_linter.py")
        if os.path.exists(infer_script):
            res = run_cmd([sys.executable, infer_script, "--strict"], timeout=60.0)
            if res.returncode != 0:
                print("❌ [PRE-COMMIT BLOCKED] Static Defect Sentinel detected critical issues in staged scripts (Zero-Sleep / Fake Pass):")
                print(res.stdout.strip())
                errors_found = True

    # 7. Credential Security & Secret Scanning (Gate 6 on Staged Diffs & Files)
    diff_res = run_cmd("git diff --cached")
    secret_violations = check_secrets(files=staged_files, diff_text=diff_res.stdout)
    if secret_violations:
        print("❌ [PRE-COMMIT BLOCKED] Hardcoded secrets/credentials detected in staged changes (Gate 6):")
        for f, line_no, desc in secret_violations:
            print(f"   - {f}:{line_no} contains '{desc}'")
        errors_found = True

    # 8. Author Integrity Pre-Flight Guard
    author_violations = check_author_integrity(staged_files)
    if author_violations:
        print("❌ [PRE-COMMIT BLOCKED] Author attribution / SPDX header integrity violation:")
        for av in author_violations:
            print(f"   - {av}")
        errors_found = True

    # 9. Anthropic & LangChain Dual-State Integrity Guard
    state_violations = check_project_state_invariants(os.getcwd())
    if state_violations:
        print("❌ [PRE-COMMIT BLOCKED] Anthropic Dual-State / project_state.json integrity violation:")
        for sv in state_violations:
            print(f"   - {sv}")
        errors_found = True

    # 10. Ephemeral Debug Breadcrumb Guard (@crumbs)
    crumbs_violations = []
    crumbs_pat = re.compile(r"(?:#|//|<!--|\*)\s*@crumbs\b")
    for f in staged_files:
        if not os.path.isfile(f) or any(ignored in f.replace("\\", "/") for ignored in ("node_modules/", ".git/", "scratch/", "debug_crumbs.py", "git_pre_commit_guard.py", "TOOLS_RUNBOOK.md", "tests/")):
            continue
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                for line_idx, line in enumerate(fp, 1):
                    if crumbs_pat.search(line):
                        crumbs_violations.append((f, line_idx))
        except OSError as read_err:
            sys.stderr.write(f"Warning reading staged file {f}: {read_err}\n")
    if crumbs_violations:
        print("❌ [PRE-COMMIT BLOCKED] Ephemeral debug breadcrumb (@crumbs) detected in staged files:")
        for f, line_idx in crumbs_violations:
            print(f"   - {f}:{line_idx}")
        print("   Run 'python3 tools/core/debug_crumbs.py --strip' to clean breadcrumbs before committing.")
        errors_found = True

    if errors_found:
        print("\n🚫 Commit aborted. Please fix violations before committing.")
        sys.exit(1)
    else:
        print("✅ [PRE-COMMIT GUARD] All quality gates passed (No BOM, Clean POM, Clean Paths, Docs Aligned, Static Lint Pass, Secrets Clean, Author Verified).")
        sys.exit(0)

if __name__ == "__main__":
    main()
