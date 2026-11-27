#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Enterprise QA Autonomous Project Setup & Bootstrap Engine
----------------------------------------------------------
Transforms any target test project into an AI-Ready Enterprise Suite in 1-click.
Dispatched automatically by AI Agents (Zero-Command Protocol) or via 'agent-qa setup'.

Automated actions:
  1. Detects project tech stack (Katalon, Playwright, Cypress, Pytest).
  2. Generates tailored 'PROJECT_AI_GUIDE.md' if missing.
  3. Deploys Universal AI Bridges (.cursor/rules, CLAUDE.md, .github/copilot-instructions.md, .windsurfrules).
  4. Injects Antigravity Global Plugin (~/.gemini/config/plugins/synapse-hub).
  5. Installs automated Git Pre-Push Hook (.git/hooks/pre-push) for zero-leakage protection.
  6. Triggers 5-in-1 Health Audit (tools/analyze_project.py):
     - Maps AST method signatures (repo_map.txt).
     - Scans fake passes (infer_linter).
     - Audits database teardown hygiene (trace_data_flow).
     - Generates in-project health report (PROJECT_HEALTH_REPORT.md).
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


import os
import sys
import hashlib
import json
import shutil
import argparse
from dataclasses import dataclass
from pathlib import Path

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HUB_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
TEMPLATES_DIR = os.path.join(HUB_ROOT, "templates")
sys.path.insert(0, SCRIPT_DIR)

import analyze_project  # noqa: E402
import project_state  # noqa: E402

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def resolve_target_repo(cli_target=None, cli_repo=None):
    chosen = cli_repo or cli_target
    if chosen:
        resolved = os.path.abspath(chosen)
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"Target repository path not found: {resolved}")
        if resolved.lower() == HUB_ROOT.lower():
            print(f"{RED}{BOLD}X [CWD CONFUSION GUARD] Target repository cannot be Synapse-Hub itself!{RESET}")
            print("  Synapse-Hub is the centralized skill hub, not an automation target project.")
            print("   Please specify a target project: python tools/setup_project.py --target /path/to/target-project")
            sys.exit(1)
        return resolved

    env_dir = os.environ.get("TARGET_PROJECT_DIR")
    if env_dir and os.path.exists(env_dir):
        resolved_env = os.path.abspath(env_dir)
        if resolved_env.lower() == HUB_ROOT.lower():
            print(f"{RED}{BOLD}X [CWD CONFUSION GUARD] TARGET_PROJECT_DIR points to Synapse-Hub itself!{RESET}")
            sys.exit(1)
        return resolved_env

    cwd = os.path.abspath(os.getcwd())
    if cwd.lower() != HUB_ROOT.lower():
        return cwd

    print(f"{RED}{BOLD}X [CWD CONFUSION GUARD] Current working directory is Synapse-Hub!{RESET}")
    print("  You must run setup inside your target project folder or supply --target:")
    print("   python tools/setup_project.py --target <path_to_target_project>")
    sys.exit(1)


def detect_tech_stack(target_dir):
    """Detects target project automation framework and script language."""
    target_path = Path(target_dir)

    # 0. QA Hub check
    if (target_path / "skills_manifest.json").exists() and (target_path / "tools").is_dir() and (target_path / "tests").is_dir():
        return {
            "name": target_path.name or "Synapse-Hub",
            "framework": "Synapse QA Hub (Multi-Stack Framework)",
            "language": "Polyglot (Python, Node.js, Groovy)",
            "page_dir": "examples",
            "test_dir": "tests",
            "run_cmd": "pytest tests -q"
        }

    # 1. Katalon Studio check
    prj_files = list(target_path.glob("*.prj"))
    has_keywords_profiles = (target_path / "Keywords").is_dir() and (target_path / "Profiles").is_dir()
    has_groovy_scripts = (target_path / "Scripts").is_dir() and any(target_path.glob("Scripts/**/*.groovy"))
    if prj_files or has_keywords_profiles or has_groovy_scripts:
        prj_name = prj_files[0].stem if prj_files else target_path.name
        return {
            "name": prj_name,
            "framework": "Katalon Studio (Enterprise Web)",
            "language": "Groovy",
            "page_dir": "Keywords/pages",
            "test_dir": "Scripts",
            "run_cmd": "katalonc -noSplash -runMode=console"
        }

    # 2. Playwright check
    if (target_path / "playwright.config.ts").exists() or (target_path / "playwright.config.js").exists():
        is_ts = (target_path / "playwright.config.ts").exists() or (target_path / "tsconfig.json").exists()
        return {
            "name": target_path.name,
            "framework": "Playwright Test",
            "language": "TypeScript" if is_ts else "JavaScript",
            "page_dir": "src/pages" if (target_path / "src" / "pages").exists() else "pages",
            "test_dir": "tests",
            "run_cmd": "npx playwright test --project=chromium"
        }

    # 3. Cypress check
    if (target_path / "cypress.config.ts").exists() or (target_path / "cypress.config.js").exists():
        return {
            "name": target_path.name,
            "framework": "Cypress E2E",
            "language": "TypeScript" if (target_path / "cypress.config.ts").exists() else "JavaScript",
            "page_dir": "cypress/pages",
            "test_dir": "cypress/e2e",
            "run_cmd": "npx cypress run --headless"
        }

    # 4. Selenium WebDriver check
    req_txt = target_path / "requirements.txt"
    has_selenium_req = req_txt.exists() and "selenium" in req_txt.read_text(encoding="utf-8", errors="ignore").lower()
    has_selenium_code = any("selenium" in f.read_text(encoding="utf-8", errors="ignore") for f in list(target_path.glob("**/*.py"))[:10]) if list(target_path.glob("**/*.py")) else False
    if has_selenium_req or has_selenium_code:
        return {
            "name": target_path.name,
            "framework": "Selenium WebDriver",
            "language": "Python",
            "page_dir": "pages",
            "test_dir": "tests",
            "run_cmd": "pytest tests/ -v"
        }

    # 5. Pytest check
    if (target_path / "pytest.ini").exists() or list(target_path.glob("test_*.py")):
        return {
            "name": target_path.name,
            "framework": "Pytest",
            "language": "Python",
            "page_dir": "pages",
            "test_dir": "tests",
            "run_cmd": "pytest tests/ -v"
        }

    # Default fallback
    return {
        "name": target_path.name,
        "framework": "Enterprise Test Automation",
        "language": "TypeScript / Groovy",
        "page_dir": "pages",
        "test_dir": "tests",
        "run_cmd": "npm test"
    }


def ensure_project_ai_guide(target_dir, stack_info, profile="full"):
    """Generates PROJECT_AI_GUIDE.md tailored to the target project if missing."""
    guide_path = os.path.join(target_dir, "PROJECT_AI_GUIDE.md")
    if os.path.exists(guide_path):
        print(f"  [PASS] PROJECT_AI_GUIDE.md already exists: {guide_path}")
        return False

    template_path = os.path.join(TEMPLATES_DIR, "PROJECT_AI_GUIDE_TEMPLATE.md")
    content = ""
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = f"# PROJECT AI GUIDE: {stack_info['name']}\n\n## 1. General System Under Test\n"

    # Populate template placeholders with detected project metadata
    content = content.replace("[TARGET_PROJECT_NAME]", stack_info["name"])
    content = content.replace("[e.g., Enterprise Billing Platform / Customer Portal]", stack_info["name"])
    content = content.replace("[e.g., Playwright Test, Katalon Studio 10.x, Cypress, Selenium]", stack_info["framework"])
    content = content.replace("[e.g., TypeScript, Groovy, Python, JavaScript]", stack_info["language"])
    content = content.replace("src/pages/... or Keywords/pages/...", stack_info["page_dir"])
    content = content.replace("tests/e2e/... or Scripts/...", stack_info["test_dir"])
    content = content.replace("[e.g., npx playwright test --project=chromium --reporter=html,junit:results.xml]", stack_info["run_cmd"])

    profile_line = f"- **Active Skills Profile:** `{profile.upper()}`"
    if profile_line not in content:
        lang_target = f"- **Script Language:** `{stack_info['language']}`"
        if lang_target in content:
            content = content.replace(lang_target, f"{lang_target}\n{profile_line}")
        else:
            content = content.replace("## 1. General System Under Test", f"## 1. General System Under Test\n{profile_line}")

    with open(guide_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  {GREEN}[OK] Generated PROJECT_AI_GUIDE.md tailored to {stack_info['framework']}:{RESET} {guide_path}")
    return True


def ensure_synapse_config(target_dir, profile="auto"):
    """Auto-generates canonical synapse.config.json (preserving legacy .synapse.json read fallback)."""
    canonical_cfg = os.path.join(target_dir, "synapse.config.json")
    legacy_cfg = os.path.join(target_dir, ".synapse.json")
    if os.path.isfile(canonical_cfg) or os.path.isfile(legacy_cfg):
        return True
    try:
        import init_config
        prj_name = os.path.basename(os.path.abspath(target_dir))
        cfg_data = init_config.build_default_config(project_name=prj_name)
        if str(profile or "").lower() not in ("perf", "perf-and-load"):
            cfg_data.setdefault("quality_gates", {}).setdefault("gates", {})["gate_10_performance_sla"] = False
        with open(canonical_cfg, "w", encoding="utf-8") as f:
            f.write(init_config.format_config_json(cfg_data))
        print(f"  {GREEN}[OK] Generated canonical synapse.config.json:{RESET} {canonical_cfg}")
        return True
    except Exception as e:
        print(f"  ⚠️ Could not auto-generate synapse.config.json: {e}")
        return False


def install_git_pre_push_hook(target_dir):
    """
    Installs or appends an automated pre-push hook into target project's .git repository.
    Safely backs up any existing pre-push hook (e.g. Husky, Lefthook) to prevent side-effects.
    """
    git_dir = os.path.join(target_dir, ".git")
    if not os.path.isdir(git_dir):
        print("  [SKIP] Not a Git repository root (.git folder not found). Skipped Git Hook installation.")
        return False

    hooks_dir = os.path.join(git_dir, "hooks")
    os.makedirs(hooks_dir, exist_ok=True)
    hook_file = os.path.join(hooks_dir, "pre-push")

    # Resolve pinned package version
    manifest_file = os.path.join(HUB_ROOT, "skills_manifest.json")
    pkg_ver = "2.2.2"
    if os.path.exists(manifest_file):
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                pkg_ver = json.load(f).get("version", pkg_ver)
        except (IOError, json.JSONDecodeError, KeyError):
            pkg_ver = "2.4.3"

    hook_snippet = f"""
# --- Synapse-Hub Pre-Push Quality Gate (v{pkg_ver}) ---
echo "\\n[AI-GUARD] Running Pre-Push Verification (Quality Gates DoD)..."
# Use portable relative Hub tools (when inside Hub) or globally/npx-resolved CLI
if [ -f "./tools/core/verify_all.py" ]; then
    python3 "./tools/core/verify_all.py" || python "./tools/core/verify_all.py"
elif command -v synapse-hub >/dev/null 2>&1; then
    synapse-hub verify
elif command -v synapse >/dev/null 2>&1; then
    synapse verify
elif command -v agent-qa >/dev/null 2>&1; then
    agent-qa verify
elif command -v npx >/dev/null 2>&1; then
    npx --no-install @teevee98/synapse-hub verify 2>/dev/null || npx @teevee98/synapse-hub@{pkg_ver} verify
else
    echo "\\n[AI-GUARD - REJECTED] No verification engine found (synapse-hub, synapse, agent-qa, npx missing)."
    exit 1
fi
if [ $? -ne 0 ]; then
    echo "\\n[AI-GUARD - REJECTED] Git Push aborted: Quality Gates verification failed!"
    echo "Please fix defects or run 'npx @teevee98/synapse-hub verify' locally before pushing.\\n"
    exit 1
fi

echo "[AI-GUARD - PASSED] Quality Gates satisfied. Syncing project health report..."
if [ -f "./tools/core/analyze_project.py" ]; then
    python3 "./tools/core/analyze_project.py" || python "./tools/core/analyze_project.py"
elif command -v synapse-hub >/dev/null 2>&1; then
    synapse-hub analyze
elif command -v synapse >/dev/null 2>&1; then
    synapse analyze
elif command -v agent-qa >/dev/null 2>&1; then
    agent-qa analyze
elif command -v npx >/dev/null 2>&1; then
    npx --no-install @teevee98/synapse-hub analyze 2>/dev/null || npx @teevee98/synapse-hub@{pkg_ver} analyze
fi
echo "[AI-GUARD - READY] Pushing to remote...\\n"
# --- End Synapse-Hub Quality Gate ---
"""

    try:
        if os.path.exists(hook_file):
            with open(hook_file, "r", encoding="utf-8", errors="ignore") as f:
                existing_content = f.read()

            if "Synapse-Hub" in existing_content or "synapse-hub" in existing_content:
                print(f"  {CYAN}[SKIP] Pre-Push Git Hook already present:{RESET} {hook_file}")
                return True

            # Safely backup existing hook (e.g. Husky, Lefthook)
            backup_file = f"{hook_file}.backup"
            shutil.copy2(hook_file, backup_file)
            print(f"  {YELLOW}[BACKUP] Existing pre-push hook backed up to:{RESET} {backup_file}")

            # Append non-destructively
            final_content = existing_content.rstrip() + "\n" + hook_snippet
        else:
            final_content = "#!/bin/sh\n" + hook_snippet

        with open(hook_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(final_content)

        # Attempt to make executable on Unix-like environments
        try:
            os.chmod(hook_file, 0o755)  # nosec B103
        except OSError:
            pass

        print(f"  {GREEN}[OK] Configured automated Pre-Push Git Hook:{RESET} {hook_file} (pinned to v{pkg_ver})")
        return True
    except Exception as e:
        print(f"  ⚠️ Could not install Git hook: {e}")
        return False


def ensure_gitignore_protection(target_dir):
    """Ensures local cache and generated AST intelligence artifacts are ignored in target repo."""
    gitignore_path = os.path.join(target_dir, ".gitignore")
    entries = [".synapse/", "repo_map.txt", "repo_map.json"]
    try:
        existing = ""
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
                existing = f.read()
        missing = [e for e in entries if e not in existing]
        if missing:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                if existing and not existing.endswith("\n"):
                    f.write("\n")
                f.write("\n# Synapse-Hub Local Cache & AST Intelligence\n")
                for e in missing:
                    f.write(f"{e}\n")
            print(f"  {GREEN}[OK] Protected local cache in .gitignore:{RESET} {gitignore_path}")
            return True
    except OSError as err:
        sys.stderr.write(f"Notice: .gitignore update skipped: {err}\n")
    return False


def install_git_post_merge_hook(target_dir):
    """
    Installs or appends an automated post-merge hook into target project's .git repository.
    When a developer pulls code for the first time via 'git pull', this triggers the
    welcome landing page once, then silently records it as completed.
    """
    git_dir = os.path.join(target_dir, ".git")
    if not os.path.isdir(git_dir):
        return False

    hooks_dir = os.path.join(git_dir, "hooks")
    os.makedirs(hooks_dir, exist_ok=True)
    hook_file = os.path.join(hooks_dir, "post-merge")

    hook_snippet = """# --- Synapse-Hub Post-Merge First-Pull Sentinel ---
# Security & portability invariant: Never embed machine-specific absolute paths
if [ -f "./tools/contrib/welcome_page.py" ]; then
    python3 "./tools/contrib/welcome_page.py" --first-run 2>/dev/null || python "./tools/contrib/welcome_page.py" --first-run 2>/dev/null || true
elif command -v synapse-hub >/dev/null 2>&1; then
    synapse-hub welcome --first-run 2>/dev/null || true
elif command -v synapse >/dev/null 2>&1; then
    synapse welcome --first-run 2>/dev/null || true
elif command -v agent-qa >/dev/null 2>&1; then
    agent-qa welcome --first-run 2>/dev/null || true
fi
"""
    try:
        if os.path.exists(hook_file):
            with open(hook_file, "r", encoding="utf-8", errors="ignore") as f:
                existing_content = f.read()

            if "Synapse-Hub Post-Merge" in existing_content:
                return True

            final_content = existing_content.rstrip() + "\n" + hook_snippet
        else:
            final_content = "#!/bin/sh\n" + hook_snippet

        with open(hook_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(final_content)

        try:
            os.chmod(hook_file, 0o755)  # nosec B103
        except OSError:
            pass

        print(f"  {GREEN}[OK] Configured Post-Merge First-Pull Git Hook:{RESET} {hook_file}")
        return True
    except (OSError, UnicodeDecodeError):
        return False


def inject_antigravity_global_plugin():
    """
    Automatically injects Synapse-Hub into Antigravity's Global Plugin Directory
    (~/.gemini/config/plugins/synapse-hub).
    Ensures that running `npx @teevee98/synapse-hub setup` activates the 57 skills and 9 subagents
    globally across ALL projects in Google Antigravity.
    """
    try:
        plugins_dir = os.path.expanduser("~/.gemini/config/plugins")
        target_plugin_dir = os.path.join(plugins_dir, "synapse-hub")
        os.makedirs(target_plugin_dir, exist_ok=True)

        # 1. plugin.json
        src_plugin_json = os.path.join(HUB_ROOT, "plugin.json")
        dst_plugin_json = os.path.join(target_plugin_dir, "plugin.json")
        if os.path.exists(src_plugin_json):
            if not os.path.exists(dst_plugin_json) or not os.path.samefile(src_plugin_json, dst_plugin_json):
                shutil.copy2(src_plugin_json, dst_plugin_json)

        # 2. README.md
        src_readme = os.path.join(HUB_ROOT, "README.md")
        dst_readme = os.path.join(target_plugin_dir, "README.md")
        if os.path.exists(src_readme):
            if not os.path.exists(dst_readme) or not os.path.samefile(src_readme, dst_readme):
                shutil.copy2(src_readme, dst_readme)

        # 3. LICENSE & NOTICE (MIT License Provenance & Author Attribution)
        for meta_file in ("LICENSE", "NOTICE"):
            src_meta = os.path.join(HUB_ROOT, meta_file)
            dst_meta = os.path.join(target_plugin_dir, meta_file)
            if os.path.exists(src_meta):
                if not os.path.exists(dst_meta) or not os.path.samefile(src_meta, dst_meta):
                    shutil.copy2(src_meta, dst_meta)

        # Helper to sync directory (junction or copy)
        def sync_dir(src, dst):
            if not os.path.exists(src):
                return
            if os.path.exists(dst) and os.path.samefile(src, dst):
                return
            if os.path.islink(dst):
                try:
                    os.unlink(dst)
                except OSError as err:
                    import logging
                    logging.getLogger("setup_project").debug("Unlink failed: %s", err)
            if sys.platform == "win32":
                try:
                    import _winapi
                    if not os.path.exists(dst):
                        _winapi.CreateJunction(src, dst)
                        return
                except (OSError, ImportError, AttributeError) as err:
                    import logging
                    logging.getLogger("setup_project").debug("Windows junction failed, falling back to copytree: %s", err)
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.tmp"))

        skills_src = os.path.join(HUB_ROOT, "skills")
        if not os.path.isdir(skills_src):
            skills_src = os.path.join(HUB_ROOT, ".agents", "skills")
        sync_dir(skills_src, os.path.join(target_plugin_dir, "skills"))

        agents_src = os.path.join(HUB_ROOT, "ai-agents")
        if not os.path.isdir(agents_src):
            agents_src = os.path.join(HUB_ROOT, ".agents", "agents")
        if os.path.isdir(agents_src):
            sync_dir(agents_src, os.path.join(target_plugin_dir, "ai-agents"))

        commands_src = os.path.join(HUB_ROOT, "commands")
        if os.path.isdir(commands_src):
            sync_dir(commands_src, os.path.join(target_plugin_dir, "commands"))

        src_agents_manifest = os.path.join(HUB_ROOT, "agents_manifest.json")
        dst_agents_manifest = os.path.join(target_plugin_dir, "agents_manifest.json")
        if os.path.exists(src_agents_manifest):
            if not os.path.exists(dst_agents_manifest) or not os.path.samefile(src_agents_manifest, dst_agents_manifest):
                shutil.copy2(src_agents_manifest, dst_agents_manifest)

        sync_dir(os.path.join(HUB_ROOT, "tools"), os.path.join(target_plugin_dir, "tools"))

        # 3. Client-Safe Rules (avoid leaking Hub-only tools/ into external workspaces)
        dst_rules = os.path.join(target_plugin_dir, "rules")
        os.makedirs(dst_rules, exist_ok=True)
        src_client_rules = os.path.join(HUB_ROOT, "templates", "ai_bridges", "CLAUDE.md")
        if not os.path.exists(src_client_rules):
            src_client_rules = os.path.join(HUB_ROOT, "AGENTS.md")
        dst_agents_md = os.path.join(dst_rules, "AGENTS.md")
        if os.path.exists(src_client_rules):
            if not os.path.exists(dst_agents_md) or not os.path.samefile(src_client_rules, dst_agents_md):
                shutil.copy2(src_client_rules, dst_agents_md)

        print(f"  {GREEN}[OK] Injected Antigravity Global Plugin:{RESET} {target_plugin_dir}")
        return True
    except Exception as e:
        print(f"  ⚠️ Antigravity Global Plugin notice: {e}")
        return False


@dataclass(frozen=True)
class CodexSkillDeployResultDTO:
    """Typed result of deploying Synapse skills into target .agents/skills/."""
    installed_skills: list
    skipped_existing: list
    target_dir: str


def _normalize_skill_frontmatter(raw_text: str) -> str:
    """Ensures YAML frontmatter delimiter '---' starts on line 1 for Codex skill discovery."""
    stripped = raw_text.lstrip("\ufeff \t\r\n")
    if stripped.startswith("---"):
        return stripped
    if stripped.startswith("<!--"):
        end_comment = stripped.find("-->")
        if end_comment != -1:
            comment_block = stripped[: end_comment + 3]
            remainder = stripped[end_comment + 3 :].lstrip("\r\n")
            if remainder.startswith("---"):
                end_fm = remainder.find("\n---", 3)
                if end_fm != -1:
                    fm_block = remainder[: end_fm + 4]
                    body = remainder[end_fm + 4 :].lstrip("\r\n")
                    return f"{fm_block}\n{comment_block}\n\n{body}"
    return raw_text


def _copy_skill_package(src_dir: str, dst_dir: str) -> None:
    """Copies a single skill directory while normalizing SKILL.md frontmatter."""
    os.makedirs(dst_dir, exist_ok=True)
    for entry in os.listdir(src_dir):
        if entry in ("__pycache__", ".DS_Store") or entry.endswith((".pyc", ".tmp")):
            continue
        src_entry = os.path.join(src_dir, entry)
        dst_entry = os.path.join(dst_dir, entry)
        if os.path.isdir(src_entry):
            shutil.copytree(
                src_entry,
                dst_entry,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.tmp"),
            )
        elif entry == "SKILL.md":
            with open(src_entry, "r", encoding="utf-8", errors="replace") as rf:
                normalized = _normalize_skill_frontmatter(rf.read())
            with open(dst_entry, "w", encoding="utf-8", newline="\n") as wf:
                wf.write(normalized)
        else:
            shutil.copy2(src_entry, dst_entry)


def _iter_codex_skill_sources() -> list:
    """Returns sorted (skill_id, src_dir) tuples for all Hub domain and workflow skills."""
    candidate_dirs = []
    domain_skills_root = os.path.join(HUB_ROOT, "skills")
    if os.path.isdir(domain_skills_root):
        for domain in sorted(os.listdir(domain_skills_root)):
            domain_path = os.path.join(domain_skills_root, domain)
            if not os.path.isdir(domain_path):
                continue
            for skill_id in sorted(os.listdir(domain_path)):
                skill_path = os.path.join(domain_path, skill_id)
                if os.path.isfile(os.path.join(skill_path, "SKILL.md")):
                    candidate_dirs.append((skill_id, skill_path))

    workflow_skills_root = os.path.join(HUB_ROOT, ".agent", "skills")
    if os.path.isdir(workflow_skills_root):
        for wf_id in sorted(os.listdir(workflow_skills_root)):
            wf_path = os.path.join(workflow_skills_root, wf_id)
            if os.path.isfile(os.path.join(wf_path, "SKILL.md")):
                candidate_dirs.append((wf_id, wf_path))

    return candidate_dirs


def compute_codex_skills_digest() -> str:
    """Computes a deterministic SHA-256 digest over all Hub SKILL.md packages for fast stale detection."""
    hasher = hashlib.sha256()
    for skill_id, src_path in _iter_codex_skill_sources():
        skill_md = os.path.join(src_path, "SKILL.md")
        hasher.update(skill_id.encode("utf-8"))
        hasher.update(b"\0")
        try:
            with open(skill_md, "rb") as sf:
                hasher.update(sf.read())
        except OSError:
            continue
        hasher.update(b"\n")
    return hasher.hexdigest()


def install_codex_skills(target_dir: str, profile: str = "auto") -> CodexSkillDeployResultDTO:
    """Deploys Synapse Hub SKILL.md packages into target_dir/.agents/skills/ without overwriting user skills."""
    resolved_target = os.path.abspath(target_dir)
    if resolved_target.lower() == HUB_ROOT.lower():
        raise ValueError("Refusing to deploy Codex skills into Synapse-Hub root itself.")

    dest_skills_root = os.path.join(resolved_target, ".agents", "skills")
    os.makedirs(dest_skills_root, exist_ok=True)
    manifest_file = os.path.join(dest_skills_root, ".synapse-managed.json")

    previously_managed = set()
    if os.path.isfile(manifest_file):
        try:
            with open(manifest_file, "r", encoding="utf-8") as mf:
                previously_managed = set(json.load(mf).get("skills", []))
        except (OSError, json.JSONDecodeError, TypeError):
            previously_managed = set()

    candidate_dirs = _iter_codex_skill_sources()

    installed_skills = []
    skipped_existing = []

    if os.path.isdir(dest_skills_root):
        for existing_name in sorted(os.listdir(dest_skills_root)):
            if existing_name.startswith("."):
                continue
            existing_path = os.path.join(dest_skills_root, existing_name)
            if os.path.isdir(existing_path) and existing_name not in previously_managed:
                if existing_name not in {sid for sid, _ in candidate_dirs}:
                    skipped_existing.append(existing_name)

    for skill_id, src_path in candidate_dirs:
        dst_path = os.path.join(dest_skills_root, skill_id)
        if os.path.exists(dst_path) and skill_id not in previously_managed:
            skipped_existing.append(skill_id)
            continue
        _copy_skill_package(src_path, dst_path)
        installed_skills.append(skill_id)

    managed_all = sorted(previously_managed | set(installed_skills))
    skills_digest = compute_codex_skills_digest()
    with open(manifest_file, "w", encoding="utf-8", newline="\n") as mf:
        json.dump(
            {
                "managed_by": "synapse-hub",
                "profile": profile,
                "skills_digest": skills_digest,
                "skills": managed_all,
            },
            mf,
            indent=2,
        )
        mf.write("\n")

    return CodexSkillDeployResultDTO(
        installed_skills=installed_skills,
        skipped_existing=sorted(set(skipped_existing)),
        target_dir=dest_skills_root,
    )


def auto_sync_codex_skills_if_stale(target_dir: str = None) -> dict:
    """Silently refreshes managed .agents/skills/ when Hub SKILL.md digest changes (zero stdout)."""
    if os.environ.get("SYNAPSE_AUTO_SYNC_SKILLS", "1").strip().lower() in ("0", "false", "no", "off"):
        return {"synced": False, "reason": "disabled_by_env"}

    resolved_target = os.path.abspath(target_dir or os.getcwd())
    if resolved_target.lower() == HUB_ROOT.lower():
        return {"synced": False, "reason": "hub_root_skipped"}

    dest_skills_root = os.path.join(resolved_target, ".agents", "skills")
    manifest_file = os.path.join(dest_skills_root, ".synapse-managed.json")
    if not os.path.isfile(manifest_file):
        return {"synced": False, "reason": "not_managed"}

    current_digest = compute_codex_skills_digest()
    manifest_profile = "auto"
    manifest_digest = None
    try:
        with open(manifest_file, "r", encoding="utf-8") as mf:
            manifest_data = json.load(mf)
        if isinstance(manifest_data, dict):
            manifest_profile = str(manifest_data.get("profile") or "auto")
            manifest_digest = manifest_data.get("skills_digest")
    except (OSError, json.JSONDecodeError, TypeError):
        manifest_digest = None

    if manifest_digest == current_digest:
        return {"synced": False, "reason": "up_to_date", "digest": current_digest}

    try:
        res = install_codex_skills(resolved_target, profile=manifest_profile)
        return {
            "synced": True,
            "reason": "digest_updated",
            "installed_count": len(res.installed_skills),
            "digest": current_digest,
        }
    except (OSError, ValueError) as err:
        sys.stderr.write(f"[synapse] Auto-sync Codex skills skipped: {err}\n")
        return {"synced": False, "reason": "error", "error": str(err)}


def _deploy_or_append_bridge(
    src_path: str,
    dst_path: str,
    marker: str,
    label_created: str,
    label_appended: str,
    deployed: list,
    separator: str = "\n\n",
) -> None:
    """Copies a bridge file if missing, or appends it once when marker is absent."""
    if not os.path.exists(src_path):
        return
    dst_parent = os.path.dirname(dst_path)
    if dst_parent:
        os.makedirs(dst_parent, exist_ok=True)
    if not os.path.exists(dst_path):
        shutil.copy2(src_path, dst_path)
        deployed.append(label_created)
        return
    with open(dst_path, "r", encoding="utf-8", errors="ignore") as fh:
        existing_content = fh.read()
    if marker in existing_content:
        return
    with open(src_path, "r", encoding="utf-8") as fh:
        append_data = fh.read()
    with open(dst_path, "a", encoding="utf-8") as fh:
        fh.write(separator + append_data)
    deployed.append(label_appended)


def install_universal_ai_bridges(target_dir, ide="all"):
    """
    Deploys Universal AI Bridge configuration files into the target project workspace
    for seamless integration with Codex, Cursor, Claude Code, GitHub Copilot, and Windsurf.
    Supports IDE-selective deployment to save 1,500-2,500 prompt tokens per turn:
      - 'all' / 'auto': deploys standard bridges (Codex, Cursor modern, Claude, Copilot, Windsurf)
      - 'codex': deploys AGENTS.md and .codex/config.toml
      - 'cursor': deploys only .cursor/rules/synapse-qa.mdc (avoids legacy .cursorrules redundancy)
      - 'cursor-legacy': deploys only .cursorrules
      - 'windsurf': deploys only .windsurfrules
      - 'claude': deploys only CLAUDE.md
      - 'copilot': deploys only .github/copilot-instructions.md
    """
    bridges_dir = os.path.join(TEMPLATES_DIR, "ai_bridges")
    if not os.path.exists(bridges_dir):
        return False

    deployed = []
    ide_choice = (ide or "all").lower().strip()
    install_all = ide_choice in ("all", "auto")

    # 1. Cursor Modern (.cursor/rules/synapse-qa.mdc)
    if install_all or ide_choice == "cursor":
        cursor_dir = os.path.join(target_dir, ".cursor", "rules")
        src_cursor = os.path.join(bridges_dir, "cursor_synapse_qa.mdc")
        if os.path.exists(src_cursor):
            os.makedirs(cursor_dir, exist_ok=True)
            shutil.copy2(src_cursor, os.path.join(cursor_dir, "synapse-qa.mdc"))
            deployed.append("Cursor (.cursor/rules/synapse-qa.mdc)")

    # 1b. Cursor Legacy (.cursorrules)
    if ide_choice == "cursor-legacy":
        src_cr = os.path.join(HUB_ROOT, ".cursorrules")
        if os.path.exists(src_cr):
            shutil.copy2(src_cr, os.path.join(target_dir, ".cursorrules"))
            deployed.append("Cursor Legacy (.cursorrules)")

    # 2. Claude Code (CLAUDE.md)
    if install_all or ide_choice == "claude":
        _deploy_or_append_bridge(
            src_path=os.path.join(bridges_dir, "CLAUDE.md"),
            dst_path=os.path.join(target_dir, "CLAUDE.md"),
            marker="Synapse-Hub",
            label_created="Claude Code (CLAUDE.md)",
            label_appended="Claude Code (appended to CLAUDE.md)",
            deployed=deployed,
        )

    # 3. GitHub Copilot (.github/copilot-instructions.md)
    if install_all or ide_choice == "copilot":
        _deploy_or_append_bridge(
            src_path=os.path.join(bridges_dir, "copilot-instructions.md"),
            dst_path=os.path.join(target_dir, ".github", "copilot-instructions.md"),
            marker="Synapse-Hub",
            label_created="GitHub Copilot (.github/copilot-instructions.md)",
            label_appended="GitHub Copilot (appended to copilot-instructions.md)",
            deployed=deployed,
        )

    # 4. Windsurf (.windsurfrules)
    if install_all or ide_choice == "windsurf":
        _deploy_or_append_bridge(
            src_path=os.path.join(bridges_dir, "windsurfrules"),
            dst_path=os.path.join(target_dir, ".windsurfrules"),
            marker="Synapse-Hub",
            label_created="Windsurf (.windsurfrules)",
            label_appended="Windsurf (appended to .windsurfrules)",
            deployed=deployed,
        )

    # 5. OpenAI Codex (AGENTS.md + .codex/config.toml)
    if install_all or ide_choice == "codex":
        _deploy_or_append_bridge(
            src_path=os.path.join(bridges_dir, "AGENTS.md"),
            dst_path=os.path.join(target_dir, "AGENTS.md"),
            marker="Synapse-Hub",
            label_created="Codex (AGENTS.md)",
            label_appended="Codex (appended to AGENTS.md)",
            deployed=deployed,
        )
        _deploy_or_append_bridge(
            src_path=os.path.join(bridges_dir, "codex_config.toml"),
            dst_path=os.path.join(target_dir, ".codex", "config.toml"),
            marker="[mcp_servers.synapse-hub]",
            label_created="Codex (.codex/config.toml)",
            label_appended="Codex (appended MCP to .codex/config.toml)",
            deployed=deployed,
            separator="\n",
        )

    if deployed:
        print(f"  {GREEN}[OK] Deployed Universal AI Bridges ({ide_choice}):{RESET} {', '.join(deployed)}")
    return True


def uninstall_setup(target_repo: str) -> int:
    """Safely reverts and removes files installed by setup_project in the target repo."""
    print(f"\n{BOLD}{YELLOW}======================================================================{RESET}")
    print(f"{BOLD}{YELLOW}          SYNAPSE HUB — REVERT & UNINSTALL SETUP                      {RESET}")
    print(f"{BOLD}{YELLOW}======================================================================{RESET}")
    print(f"Target Repository: {target_repo}")

    reverted_items = 0

    # 1. Remove PROJECT_AI_GUIDE.md
    guide_file = os.path.join(target_repo, "PROJECT_AI_GUIDE.md")
    if os.path.exists(guide_file):
        os.remove(guide_file)
        print(f"  {GREEN}[REMOVED]{RESET} {guide_file}")
        reverted_items += 1

    # 2. Restore/Remove Git Pre-Push & Post-Merge Hooks
    hook_file = os.path.join(target_repo, ".git", "hooks", "pre-push")
    backup_candidates = [
        os.path.join(target_repo, ".git", "hooks", "pre-push.backup"),
        os.path.join(target_repo, ".git", "hooks", "pre-push.bak"),
    ]
    restored_backup = False
    for backup_file in backup_candidates:
        if os.path.exists(backup_file):
            if os.path.exists(hook_file):
                os.remove(hook_file)
            shutil.move(backup_file, hook_file)
            print(f"  {GREEN}[RESTORED]{RESET} Restored original pre-push hook from backup")
            reverted_items += 1
            restored_backup = True
            break
    if not restored_backup and os.path.exists(hook_file):
        with open(hook_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if "Synapse-Hub" in content or "synapse-hub" in content:
            os.remove(hook_file)
            print(f"  {GREEN}[REMOVED]{RESET} Cleaned Synapse-Hub pre-push hook")
            reverted_items += 1

    post_merge_file = os.path.join(target_repo, ".git", "hooks", "post-merge")
    if os.path.exists(post_merge_file):
        with open(post_merge_file, "r", encoding="utf-8", errors="ignore") as f:
            pm_content = f.read()
        if "Synapse-Hub" in pm_content or "synapse-hub" in pm_content:
            os.remove(post_merge_file)
            print(f"  {GREEN}[REMOVED]{RESET} Cleaned Synapse-Hub post-merge hook")
            reverted_items += 1

    # 3. Remove Cursor rule
    cursor_rule = os.path.join(target_repo, ".cursor", "rules", "synapse-qa.mdc")
    if os.path.exists(cursor_rule):
        os.remove(cursor_rule)
        print(f"  {GREEN}[REMOVED]{RESET} {cursor_rule}")
        reverted_items += 1

    # 4. Remove Copilot instruction
    copilot_file = os.path.join(target_repo, ".github", "copilot-instructions.md")
    if os.path.exists(copilot_file):
        os.remove(copilot_file)
        print(f"  {GREEN}[REMOVED]{RESET} {copilot_file}")
        reverted_items += 1

    # 5. Remove Windsurf rules
    windsurf_file = os.path.join(target_repo, ".windsurfrules")
    if os.path.exists(windsurf_file):
        os.remove(windsurf_file)
        print(f"  {GREEN}[REMOVED]{RESET} {windsurf_file}")
        reverted_items += 1

    # 6. Remove Synapse-templated CLAUDE.md, state anchors, and config
    claude_file = os.path.join(target_repo, "CLAUDE.md")
    if os.path.exists(claude_file):
        with open(claude_file, "r", encoding="utf-8", errors="ignore") as f:
            claude_txt = f.read()
        if "SYNAPSE-HUB CLIENT AI BRIDGE TEMPLATE" in claude_txt:
            os.remove(claude_file)
            print(f"  {GREEN}[REMOVED]{RESET} {claude_file}")
            reverted_items += 1

    # 6b. Remove Synapse-templated Codex assets (preserve user-authored files)
    agents_file = os.path.join(target_repo, "AGENTS.md")
    if os.path.exists(agents_file):
        with open(agents_file, "r", encoding="utf-8", errors="ignore") as f:
            agents_txt = f.read()
        if agents_txt.lstrip().startswith("# AGENTS.md — Synapse-Hub") and "SYNAPSE-HUB CLIENT AI BRIDGE TEMPLATE" in agents_txt:
            os.remove(agents_file)
            print(f"  {GREEN}[REMOVED]{RESET} {agents_file}")
            reverted_items += 1

    codex_toml = os.path.join(target_repo, ".codex", "config.toml")
    if os.path.exists(codex_toml):
        with open(codex_toml, "r", encoding="utf-8", errors="ignore") as f:
            toml_txt = f.read()
        if "SYNAPSE-HUB CODEX MCP CONFIGURATION" in toml_txt and toml_txt.lstrip().startswith("# =="):
            os.remove(codex_toml)
            print(f"  {GREEN}[REMOVED]{RESET} {codex_toml}")
            reverted_items += 1
            codex_dir = os.path.join(target_repo, ".codex")
            if os.path.isdir(codex_dir) and not os.listdir(codex_dir):
                os.rmdir(codex_dir)

    codex_skills_dir = os.path.join(target_repo, ".agents", "skills")
    managed_manifest = os.path.join(codex_skills_dir, ".synapse-managed.json")
    if os.path.isfile(managed_manifest):
        try:
            with open(managed_manifest, "r", encoding="utf-8") as mf:
                managed_ids = json.load(mf).get("skills", [])
            for sid in managed_ids:
                skill_dir = os.path.join(codex_skills_dir, sid)
                if os.path.isdir(skill_dir):
                    shutil.rmtree(skill_dir)
                    reverted_items += 1
            os.remove(managed_manifest)
            if os.path.isdir(codex_skills_dir) and not os.listdir(codex_skills_dir):
                os.rmdir(codex_skills_dir)
            agents_dir = os.path.join(target_repo, ".agents")
            if os.path.isdir(agents_dir) and not os.listdir(agents_dir):
                os.rmdir(agents_dir)
            print(f"  {GREEN}[REMOVED]{RESET} Cleaned Synapse-managed Codex skills in {codex_skills_dir}")
        except (OSError, json.JSONDecodeError, TypeError) as err:
            sys.stderr.write(f"Notice: Could not clean Synapse-managed Codex skills: {err}\n")

    for state_rel in ("PROJECT_STATE.md", "project_state.json"):
        state_path = os.path.join(target_repo, state_rel)
        if os.path.exists(state_path):
            with open(state_path, "r", encoding="utf-8", errors="ignore") as f:
                st_txt = f.read()
            if "Project Execution State" in st_txt or "Anthropic-Compliant Dual-State Anchor" in st_txt:
                os.remove(state_path)
                print(f"  {GREEN}[REMOVED]{RESET} {state_path}")
                reverted_items += 1

    cfg_path = os.path.join(target_repo, "synapse.config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8", errors="ignore") as f:
            cfg_txt = f.read()
        if "TeeVee98/Synapse-Hub" in cfg_txt or "circuit_breaker" in cfg_txt:
            os.remove(cfg_path)
            print(f"  {GREEN}[REMOVED]{RESET} {cfg_path}")
            reverted_items += 1

    print(f"\n{GREEN}✅ Uninstall complete! Cleaned {reverted_items} configuration files/hooks.{RESET}\n")
    return 0


def _resolve_active_profile(profile: str, stack_info: dict) -> str:
    """Resolves 'auto' setup profile into a concrete stack profile."""
    if profile != "auto":
        return profile
    fw = stack_info.get("framework", "").lower()
    lang = stack_info.get("language", "").lower()
    for token in ("playwright", "selenium", "cypress", "katalon", "pytest"):
        if token in fw:
            return token
    if "python" in lang:
        return "pytest"
    return "full"


def run_setup(target_repo, dry_run=False, profile="auto", no_global=True, no_git_hook=False, no_browser=True, open_browser=False, ide="all"):
    """Main execution entrypoint for automated project setup."""
    print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
    print(f"{BOLD}{CYAN}      AUTONOMOUS ZERO-COMMAND PROJECT BOOTSTRAP (AI-READY SETUP)     {RESET}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}")
    print(f"📁 Target Project  : {target_repo}")

    # 1. Detect Stack
    stack_info = detect_tech_stack(target_repo)
    print(f"🔍 Detected Stack  : {BOLD}{stack_info['framework']}{RESET} ({stack_info['language']})")
    print(f"📂 Structure Scope : Pages: `{stack_info['page_dir']}` | Tests: `{stack_info['test_dir']}`\n")

    profile = _resolve_active_profile(profile, stack_info)

    print(f"🎯 Selected Profile: {BOLD}{profile.upper()}{RESET}")
    if dry_run:
        print(f"Operational Mode   : {YELLOW}DRY-RUN (Simulating without modifying files on disk){RESET}\n")
    else:
        print("Operational Mode   : APPLY CHANGES\n")

    if dry_run:
        print(f"{YELLOW}[DRY-RUN PREVIEW]{RESET}")
        print(f"  • Profile: {profile.upper()}")
        print(f"  • Would generate: {os.path.join(target_repo, 'PROJECT_AI_GUIDE.md')}")
        print("  • Would deploy AI bridges: AGENTS.md, .codex/config.toml, .cursor/rules/synapse-qa.mdc, .github/copilot-instructions.md, .windsurfrules")
        if (ide or "all").lower().strip() in ("all", "auto", "codex"):
            print(f"  • Would export Codex skills: {os.path.join(target_repo, '.agents', 'skills')}")
        print(f"  • Would install pre-push hook: {os.path.join(target_repo, '.git', 'hooks', 'pre-push')}")
        print(f"  • Would auto-generate: {os.path.join(target_repo, 'synapse.config.json')} (if missing)")
        print("  • Would initialize: Central Agent Memory (~/.agent_memory/global_cache.db)")
        print(f"\n{GREEN}✅ Dry-run completed successfully. Zero changes written to disk.{RESET}\n")
        return 0

    # 2. Ensure PROJECT_AI_GUIDE.md, PROJECT_STATE.md & .synapse.json
    print(f"{BOLD}[1/5] Checking Project AI Guide, State Anchor & Default Config...{RESET}")
    ensure_project_ai_guide(target_repo, stack_info, profile=profile)
    project_state.init_state(target_repo)
    ensure_synapse_config(target_repo, profile=profile)

    # 3. Deploy Universal AI Bridges (Codex, Cursor, Claude Code, GitHub Copilot, Windsurf)
    print(f"\n{BOLD}[2/5] Deploying Universal AI Bridges (ide={ide})...{RESET}")
    install_universal_ai_bridges(target_repo, ide=ide)
    if (ide or "all").lower().strip() in ("all", "auto", "codex"):
        codex_res = install_codex_skills(target_repo, profile=profile)
        print(f"  {GREEN}[OK] Exported {len(codex_res.installed_skills)} Codex skills to:{RESET} {codex_res.target_dir}")

    # 4. Inject Antigravity Global Plugin
    plugin_injected = False
    if no_global:
        print(f"\n{BOLD}[3/5] Checking Antigravity Global Plugin (~/.gemini/config/plugins)...{RESET}")
        print(f"  {YELLOW}[SKIP] Local-only mode (default). Skipped global plugin injection (pass --global to install globally).{RESET}")
    else:
        print(f"\n{BOLD}[3/5] Injecting Antigravity Global Plugin (~/.gemini/config/plugins)...{RESET}")
        plugin_injected = inject_antigravity_global_plugin()

        # 4.1 Initialize Central Agent Memory (SQLite Cache)
        try:
            import cache_resolver
            cache_resolver.init_db(seed=True)
            print(f"  {GREEN}[OK] Initialized Central Agent Memory (SQLite):{RESET} ~/.agent_memory/global_cache.db")
        except Exception as e:
            print(f"  ⚠️ Could not initialize memory cache: {e}")

        # 4.2 Protect local cache in .gitignore
        ensure_gitignore_protection(target_repo)

    # 5. Install Pre-Push & Post-Merge Git Hooks
    hook_installed = False
    if no_git_hook:
        print(f"\n{BOLD}[4/5] Installing Zero-Leakage Git Hooks...{RESET}")
        print(f"  {YELLOW}[SKIP] Skipped Git hook installation (--no-git-hook).{RESET}")
    else:
        print(f"\n{BOLD}[4/5] Installing Zero-Leakage Git Hooks...{RESET}")
        hook_installed = install_git_pre_push_hook(target_repo)
        install_git_post_merge_hook(target_repo)

    # 6. Run 5-in-1 Comprehensive Health & AST Analysis
    print(f"\n{BOLD}[5/5] Executing Initial Health Audit & AST Mapping...{RESET}")
    analysis_code = analyze_project.run_full_analysis(target_repo)

    # 7. Generate & Launch Interactive Visual Landing Page (Silent by default unless --open)
    welcome_url = None
    try:
        from tools.contrib.welcome_page import generate_welcome_page
        should_open = (not no_browser) and open_browser and (not os.environ.get("CI")) and (not os.environ.get("HEADLESS")) and ("unittest" not in sys.modules) and ("pytest" not in sys.modules)
        welcome_file = generate_welcome_page(
            target_repo=target_repo,
            stack_info=stack_info,
            open_browser=should_open
        )
        welcome_url = f"file://{welcome_file}"
    except (ImportError, OSError, ValueError):
        welcome_url = ""

    print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
    print(f"{BOLD}{CYAN}            🎉 PROJECT IS NOW 100% AI-READY (LEVEL 5 SETUP)           {RESET}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}")
    print(f"  Target Framework    : {stack_info['framework']}")
    print(f"  Active Profile      : {profile.upper()}")
    print(f"  AI Project Guide    : {os.path.join(target_repo, 'PROJECT_AI_GUIDE.md')}")
    print("  Universal Bridges   : Codex (AGENTS.md + .codex/config.toml + .agents/skills), Cursor, Claude Code, Copilot, Windsurf")
    print(f"  Antigravity Plugin  : {'ACTIVE (~/.gemini/config/plugins/synapse-hub)' if plugin_injected else 'STANDALONE'}")
    print(f"  AST Method Map      : {os.path.join(target_repo, 'repo_map.txt')}")
    print(f"  Health Report       : {os.path.join(target_repo, 'PROJECT_HEALTH_REPORT.md')}")
    print(f"  Pre-Push Sentinel   : {'ACTIVE (.git/hooks/pre-push)' if hook_installed else 'MANUAL (No .git folder)'}")
    if welcome_url:
        print(f"  Visual Landing Page : {welcome_url}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}\n")

    return analysis_code


def main():
    parser = argparse.ArgumentParser(description="Autonomous Enterprise QA Project Setup")
    parser.add_argument("target", nargs="?", default=None, help="Target repository path to setup")
    parser.add_argument("--target", "--repo", "--path", dest="repo_path", default=None, help="Target repository path")
    parser.add_argument(
        "--profile",
        default="auto",
        choices=["auto", "core", "web-e2e", "api-perf", "full", "playwright", "pytest", "cypress", "katalon"],
        help="Skills profile to install (auto, core, web-e2e, api-perf, full, playwright, pytest, cypress, katalon)"
    )
    parser.add_argument(
        "--ide",
        default="all",
        choices=["auto", "all", "codex", "cursor", "cursor-legacy", "windsurf", "claude", "copilot"],
        help="Target IDE AI bridge to install (auto, all, codex, cursor, cursor-legacy, windsurf, claude, copilot)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Simulate setup actions without modifying disk")
    parser.add_argument("--uninstall", action="store_true", help="Revert and remove files installed by setup_project")
    parser.add_argument("--global", "--global-plugin", action="store_true", dest="enable_global", default=False,
                        help="Inject Synapse-Hub into Antigravity global plugins (~/.gemini/config/plugins) and central memory")
    parser.add_argument("--local-only", "--no-global", action="store_true", dest="no_global", default=True,
                        help="Only configure project-local assets (PROJECT_AI_GUIDE.md, bridges), do not touch ~/.gemini (default: True)")
    parser.add_argument("--no-git-hook", action="store_true",
                        help="Skip installing automated .git/hooks/pre-push")
    parser.add_argument("--open", action="store_true", dest="open_browser",
                        help="Launch landing page in web browser")
    parser.add_argument("--no-browser", "--no-open", action="store_true", dest="no_browser", default=True,
                        help="Do not automatically launch landing page in web browser (default: True)")
    args = parser.parse_args()

    try:
        target_repo = resolve_target_repo(cli_target=args.target, cli_repo=args.repo_path)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        return 1

    if args.uninstall:
        return uninstall_setup(target_repo)

    # When --open is explicitly requested, honor it
    no_browser = False if getattr(args, "open_browser", False) else True
    open_browser = bool(getattr(args, "open_browser", False))
    use_no_global = False if getattr(args, "enable_global", False) else True

    return run_setup(
        target_repo,
        dry_run=args.dry_run,
        profile=args.profile,
        no_global=use_no_global,
        no_git_hook=args.no_git_hook,
        no_browser=no_browser,
        open_browser=open_browser,
        ide=args.ide
    )


if __name__ == "__main__":
    sys.exit(main())
