#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/author_integrity.py — Author Attribution & Repository Provenance Guard
-----------------------------------------------------------------------------
Verifies author provenance and copyright attribution across Synapse Hub repository assets.
Enforces the mandatory Attribution condition of the MIT License:
  "The above copyright notice and this permission notice shall be included
   in all copies or substantial portions of the Software."

Note on Legal Scope:
  This script serves as an in-repository integrity and provenance verification sentinel.
  It confirms internal file consistency and attribution headers, but is not a substitute
  for external legal SBOM scans or formal trademark/copyright enforcement.

Checks:
  1. LICENSE file exists with original copyright notice (Thế Vị @TeeVee98).
  2. package.json maintains the original author attribution.
  3. README.md retains the original creator and repository provenance.
  4. pyproject.toml preserves the author declaration.
"""

import os
import sys
import json
import hashlib
from typing import Tuple, List, Optional

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ORIGINAL_AUTHOR_NAME = "Thế Vị"
ORIGINAL_AUTHOR_HANDLE = "@TeeVee98"
ORIGINAL_REPO_URL = "https://github.com/TeeVee98/Synapse-Hub"

# Pre-computed SHA-256 fingerprints of canonical author credentials (@TeeVee98 and legacy @TeeVee998)
CANONICAL_AUTHOR_SIGS = {
    "6c56b5f2c2d6f4e4b82cf4d1fa6ccd4a5e8cf0cb0e15a4a60136965fe8ebb697",  # Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
    "ea09e6bd3428c00581a385ec13bb7d8cd7d9e800fbdd1094c6d5a7bfb4060475",  # Thế Vị (@TeeVee998) <https://github.com/TeeVee998/Synapse-Hub> (legacy provenance)
}
CANONICAL_AUTHOR_SIG = "6c56b5f2c2d6f4e4b82cf4d1fa6ccd4a5e8cf0cb0e15a4a60136965fe8ebb697"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _find_repo_root() -> str:
    curr = SCRIPT_DIR
    while curr and curr != os.path.dirname(curr):
        if os.path.isfile(os.path.join(curr, "LICENSE")) or os.path.isfile(os.path.join(curr, "package.json")):
            return curr
        curr = os.path.dirname(curr)
    return os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))


DEFAULT_REPO_ROOT = _find_repo_root()


def get_canonical_watermark() -> str:
    return f"{ORIGINAL_AUTHOR_NAME} ({ORIGINAL_AUTHOR_HANDLE}) <{ORIGINAL_REPO_URL}>"


def verify_author_fingerprint() -> bool:
    """Validates that the canonical author attribution metadata matches the reference integrity hash."""
    watermark = get_canonical_watermark()
    computed = hashlib.sha256(watermark.encode("utf-8")).hexdigest()
    if CANONICAL_AUTHOR_SIG not in CANONICAL_AUTHOR_SIGS:
        return False
    return computed == CANONICAL_AUTHOR_SIG or computed in CANONICAL_AUTHOR_SIGS


def _resolve_license_content(root: str, allow_global_metadata: bool = False) -> Tuple[Optional[str], Optional[str]]:
    """
    Locates LICENSE content and its origin path across repository root, tools/,
    dist-info directories, or distribution metadata (importlib.metadata).
    Returns (license_text, origin_description).
    """
    # 1. Direct LICENSE in root
    license_path = os.path.join(root, "LICENSE")
    if os.path.isfile(license_path):
        try:
            with open(license_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(), license_path
        except Exception as e:
            return None, f"Could not read LICENSE file: {e}"

    # 2. Check dist-info directories specifically inside the given root
    if os.path.isdir(root):
        try:
            for entry in os.listdir(root):
                if entry.endswith(".dist-info") and ("synapse" in entry.lower()):
                    dist_info_dir = os.path.join(root, entry)
                    for sub in (
                        os.path.join("licenses", "LICENSE"),
                        "LICENSE",
                        "LICENSE.txt",
                    ):
                        lic_candidate = os.path.join(dist_info_dir, sub)
                        if os.path.isfile(lic_candidate):
                            try:
                                with open(lic_candidate, "r", encoding="utf-8", errors="ignore") as f:
                                    return f.read(), lic_candidate
                            except (OSError, UnicodeDecodeError) as read_err:
                                lic_read_err = str(read_err)
                                continue
        except OSError as list_err:
            lic_list_err = str(list_err)

    # 3. Check tools/LICENSE inside root
    root_tools_lic = os.path.join(root, "tools", "LICENSE")
    if os.path.isfile(root_tools_lic):
        try:
            with open(root_tools_lic, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(), root_tools_lic
        except (OSError, UnicodeDecodeError) as tools_err:
            lic_tools_err = str(tools_err)

    # 4. Only if allowed (running in installed runtime / default root), check global metadata and SCRIPT_DIR
    if allow_global_metadata:
        tools_lic = os.path.join(SCRIPT_DIR, "LICENSE")
        if os.path.isfile(tools_lic):
            try:
                with open(tools_lic, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read(), tools_lic
            except (OSError, UnicodeDecodeError) as s_err:
                lic_s_err = str(s_err)

        try:
            import importlib.metadata as meta
            for pkg in ("synapse-hub", "synapse_hub"):
                try:
                    pkg_files = meta.files(pkg)
                    if pkg_files:
                        for pf in pkg_files:
                            p_str = str(pf).replace("\\", "/")
                            if p_str.endswith("LICENSE") or "licenses/LICENSE" in p_str:
                                try:
                                    return pf.read_text(encoding="utf-8"), f"metadata:{p_str}"
                                except (OSError, UnicodeDecodeError) as meta_read_err:
                                    lic_meta_err = str(meta_read_err)
                                    continue
                except meta.PackageNotFoundError:
                    continue
        except Exception as meta_err:
            lic_import_err = str(meta_err)

        parent_script = os.path.dirname(SCRIPT_DIR)
        if os.path.isdir(parent_script) and parent_script != root:
            try:
                for entry in os.listdir(parent_script):
                    if entry.endswith(".dist-info") and ("synapse" in entry.lower()):
                        dist_info_dir = os.path.join(parent_script, entry)
                        for sub in (
                            os.path.join("licenses", "LICENSE"),
                            "LICENSE",
                            "LICENSE.txt",
                        ):
                            lic_candidate = os.path.join(dist_info_dir, sub)
                            if os.path.isfile(lic_candidate):
                                try:
                                    with open(lic_candidate, "r", encoding="utf-8", errors="ignore") as f:
                                        return f.read(), lic_candidate
                                except (OSError, UnicodeDecodeError) as p_err:
                                    lic_p_err = str(p_err)
                                    continue
            except OSError as p_list_err:
                lic_p_list_err = str(p_list_err)

    return None, None


def assert_integrity_or_raise(repo_root: Optional[str] = None) -> bool:
    """
    Enforces author attribution and MIT License provenance in accordance with open-source licensing.
    Under the MIT License, preserving the original copyright notice in LICENSE is mandatory.
    If mandatory LICENSE copyright notice is missing, halts execution to protect author attribution.
    """
    if not verify_author_fingerprint():
        raise RuntimeError(
            "🛑 CRITICAL INTEGRITY CORRUPTED: Canonical author fingerprint mismatch. "
            "Synapse Hub requires original author attribution ('Thế Vị @TeeVee98') to execute."
        )
    valid, violations = verify_author_attribution(repo_root)
    license_violations = [v for v in violations if "LICENSE" in v]
    if license_violations:
        # Fallback inspection of distribution metadata before declaring critical violation
        root = repo_root or DEFAULT_REPO_ROOT
        lic_content, _ = _resolve_license_content(root, allow_global_metadata=True)
        if lic_content and ORIGINAL_AUTHOR_NAME in lic_content and ("@TeeVee98" in lic_content or "@TeeVee998" in lic_content) and "Synapse-Hub" in lic_content:
            license_violations = []
            violations = [v for v in violations if "LICENSE" not in v]

    if license_violations:
        err_msg = "🛑 CRITICAL INTEGRITY VIOLATION: Mandatory MIT copyright notice missing or altered.\n"
        for v in license_violations:
            err_msg += f"  • {v}\n"
        err_msg += "Under the MIT License, original author attribution to 'Thế Vị (@TeeVee98)' must be preserved in LICENSE."
        raise RuntimeError(err_msg)
    elif not valid:
        # Non-fatal warning for peripheral files (README/package.json) to allow flexible downstream fork usage
        for v in violations:
            print(f"[WARN] Attribution Notice: {v}", file=sys.stderr)
    return True


def verify_author_attribution(repo_root: Optional[str] = None) -> Tuple[bool, List[str]]:
    """
    Validates that the repository preserves the author attribution required by MIT license.
    Returns (is_valid, list_of_violations).
    """
    root = repo_root or DEFAULT_REPO_ROOT
    allow_global = (repo_root is None or repo_root == DEFAULT_REPO_ROOT)
    violations: List[str] = []

    # 1. Check LICENSE file or distribution metadata
    lic_content, lic_source = _resolve_license_content(root, allow_global_metadata=allow_global)
    if lic_content is None:
        if lic_source and lic_source.startswith("Could not read"):
            violations.append(lic_source)
        else:
            violations.append("Missing LICENSE file. MIT License with author copyright notice is mandatory.")
    else:
        try:
            if ORIGINAL_AUTHOR_NAME not in lic_content or ("@TeeVee98" not in lic_content and "@TeeVee998" not in lic_content):
                violations.append("LICENSE file modified: original copyright notice for 'Thế Vị (@TeeVee98)' was removed or altered.")
            if "Synapse-Hub" not in lic_content:
                violations.append("LICENSE file modified: original repository URL was removed.")
        except Exception as e:
            violations.append(f"Could not read LICENSE file: {e}")

    # 2. Check package.json
    pkg_path = os.path.join(root, "package.json")
    if os.path.exists(pkg_path):
        try:
            with open(pkg_path, "r", encoding="utf-8", errors="ignore") as f:
                pkg_data = json.load(f)
            author_val = str(pkg_data.get("author", ""))
            if ORIGINAL_AUTHOR_NAME not in author_val or ("TeeVee98" not in author_val and "TeeVee998" not in author_val):
                violations.append("package.json modified: 'author' field does not credit 'Thế Vị (@TeeVee98)'.")
        except Exception as e:
            violations.append(f"Could not read package.json: {e}")

    # 3. Check README.md
    readme_path = os.path.join(root, "README.md")
    if os.path.exists(readme_path):
        try:
            with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
                readme_content = f.read()
            if ORIGINAL_AUTHOR_NAME not in readme_content or ("@TeeVee98" not in readme_content and "@TeeVee998" not in readme_content):
                violations.append("README.md modified: author attribution for 'Thế Vị (@TeeVee98)' was removed.")
            if "Synapse-Hub" not in readme_content:
                violations.append("README.md modified: upstream repository provenance link was removed.")
        except Exception as e:
            violations.append(f"Could not read README.md: {e}")

    # 4. Check pyproject.toml
    pyproject_path = os.path.join(root, "pyproject.toml")
    if os.path.exists(pyproject_path):
        try:
            with open(pyproject_path, "r", encoding="utf-8", errors="ignore") as f:
                pyproj_content = f.read()
            if ORIGINAL_AUTHOR_NAME not in pyproj_content:
                violations.append("pyproject.toml modified: author declaration does not include 'Thế Vị'.")
        except Exception as e:
            violations.append(f"Could not read pyproject.toml: {e}")

    is_valid = len(violations) == 0
    return is_valid, violations


def enforce_author_attribution(repo_root: Optional[str] = None, strict: bool = True) -> bool:
    """
    Enforces author attribution at runtime. If attribution is violated,
    displays a transparent copyright notice and halts execution if strict=True.
    """
    is_valid, violations = verify_author_attribution(repo_root)
    if not is_valid:
        CYAN = "\033[96m"
        RED = "\033[91m"
        BOLD = "\033[1m"
        RESET = "\033[0m"

        print(f"\n{BOLD}{RED}======================================================================{RESET}", file=sys.stderr)
        print(f"{BOLD}{RED}  🛑 [AUTHOR ATTRIBUTION & INTEGRITY VIOLATION DETECTED]               {RESET}", file=sys.stderr)
        print(f"{BOLD}{RED}======================================================================{RESET}", file=sys.stderr)
        print(f"{BOLD}Original Creator & Copyright Holder:{RESET} {ORIGINAL_AUTHOR_NAME} ({ORIGINAL_AUTHOR_HANDLE})", file=sys.stderr)
        print(f"{BOLD}Original Project Repository        :{RESET} {ORIGINAL_REPO_URL}", file=sys.stderr)
        print(f"{BOLD}Legal Notice                       :{RESET} Under the MIT License, you are free to use,", file=sys.stderr)
        print("                                     modify, and distribute this software, PROVIDED", file=sys.stderr)
        print("                                     that the original copyright notice is preserved.", file=sys.stderr)
        print("\nViolations detected:", file=sys.stderr)
        for v in violations:
            print(f"  • {v}", file=sys.stderr)
        print(f"\n{CYAN}👉 Please restore original author attribution to continue using Synapse Hub.{RESET}", file=sys.stderr)
        print(f"{RED}======================================================================{RESET}\n", file=sys.stderr)

        if strict:
            sys.exit(1)
        return False
    return True


def verify_source_headers(
    repo_root: Optional[str] = None,
    extensions: Tuple[str, ...] = (".py", ".ts", ".groovy"),
    scan_dirs: Optional[List[str]] = None,
) -> Tuple[bool, List[str]]:
    """
    Validates that internal source files preserve the mandatory author attribution header:
      SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
      SPDX-License-Identifier: MIT
    Returns (is_valid, list_of_missing_files).
    """
    root = repo_root or DEFAULT_REPO_ROOT
    ignored_dirs = {
        ".git", ".gradle", "node_modules", "allure-results", "graphify-out",
        "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache",
        "build", "dist", "claude-ecosystem-repos", "external_repos",
        "teamwork", ".synapse", ".sandbox_snapshots"
    }
    missing: List[str] = []
    dirs_to_scan = scan_dirs or ["tools", "tests", "examples", "scripts", "benchmarks", ".agents"]

    for d in dirs_to_scan:
        full_d = os.path.join(root, d)
        if not os.path.isdir(full_d):
            continue
        for cur_root, dirs, files in os.walk(full_d):
            dirs[:] = [sub for sub in dirs if sub not in ignored_dirs]
            for f in sorted(files):
                if any(f.endswith(ext) for ext in extensions):
                    file_path = os.path.join(cur_root, f)
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                            header = fp.read(600)
                        has_author = (
                            ("Thế Vị" in header or "TeeVee98" in header or "TeeVee998" in header)
                            and "SPDX-FileCopyrightText" in header
                        )
                        has_license = "SPDX-License-Identifier" in header
                        if not (has_author and has_license):
                            missing.append(os.path.relpath(file_path, root).replace(os.sep, "/"))
                    except OSError as err:
                        missing.append(f"{os.path.relpath(file_path, root)}: {err}")

    return len(missing) == 0, missing


if __name__ == "__main__":
    valid, viols = verify_author_attribution()
    headers_valid, missing_headers = verify_source_headers()
    if valid and headers_valid:
        print(f"✅ Author attribution is 100% verified intact: {get_canonical_watermark()}")
        print("✅ Source file SPDX headers verified intact (0 missing across source tree).")
        sys.exit(0)
    else:
        if not headers_valid:
            print(f"[WARN] Missing SPDX headers in {len(missing_headers)} files:", file=sys.stderr)
            for mf in missing_headers[:10]:
                print(f"   • {mf}", file=sys.stderr)
        enforce_author_attribution(strict=True)
