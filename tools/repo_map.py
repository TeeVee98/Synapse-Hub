#!/usr/bin/env python3
"""
Enterprise Repository Map Compressor (Inspired by Aider-AI/aider)
-----------------------------------------------------------
Extracts an ultra-compact, token-budgeted AST map of all Page Classes and Helpers.
Compresses hundreds of kilobytes of Groovy source code into a clean ~150-line summary.
Enables AI Agents to discover all available methods and signatures with < 600 tokens.
Supports dynamic target repository resolution (CLI flag, CWD auto-detect, ENV var).
Saves a persistent in-place copy (repo_map.txt) inside the target project directory.
"""

import os
import sys
import re
import json
import argparse
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HUB_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
OUTPUT_TXT = os.path.join(SCRIPT_DIR, "repo_map.txt")
OUTPUT_JSON = os.path.join(SCRIPT_DIR, "repo_map.json")

# Regex patterns for Groovy/Java classes and methods
CLASS_PATTERN = re.compile(r'^\s*(?:public\s+|export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?', re.MULTILINE)
PY_CLASS_PATTERN = re.compile(r'^\s*class\s+(\w+)(?:\(([^)]*)\))?\s*:', re.MULTILINE)
METHOD_PATTERN = re.compile(
    r'^\s*(?:@\w+\s+)*(?:public\s+|protected\s+|private\s+)?(?:static\s+)?(?:async\s+)?(?:def\s+|void\s+|[\w<>\[\],]+\s+)?(\w+)\s*\(([^)]*)\)\s*(?:throws\s+[\w,\s]+)?\s*\{',
    re.MULTILINE
)
DOC_PATTERN = re.compile(r'/\*\*(.*?)\*/', re.DOTALL)


def resolve_target_repo(cli_target=None, cli_repo=None):
    """
    Resolves the target repository path for repo mapping:
    1. Explicit CLI flag: --repo / --path or positional target.
    2. Environment variable: TARGET_PROJECT_DIR.
    3. Current Working Directory (if different from Hub and has Keywords/, pages/, or tests/).
    4. Default fallback: QA Hub root (parent of tools/).
    """
    chosen = cli_repo or cli_target
    if chosen:
        resolved = os.path.abspath(chosen)
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"Target repository path not found: {resolved}")
        return resolved

    env_dir = os.environ.get("TARGET_PROJECT_DIR")
    if env_dir and os.path.exists(env_dir):
        return os.path.abspath(env_dir)

    cwd = os.path.abspath(os.getcwd())
    if cwd.lower() != HUB_ROOT.lower():
        markers = ("Keywords", "Scripts", "pages", "tests", "src/pages", "e2e")
        if any(os.path.exists(os.path.join(cwd, m)) for m in markers):
            return cwd

    return HUB_ROOT


def extract_class_info(file_path, repo_root=None):
    """Parses a Groovy, TypeScript, JavaScript, or Python file and extracts class name and methods."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    base_root = repo_root or HUB_ROOT
    try:
        rel_path = os.path.relpath(file_path, base_root)
    except ValueError:
        rel_path = os.path.abspath(file_path)

    ext = os.path.splitext(file_path)[1].lower()
    methods = []
    control_keywords = {"if", "for", "while", "switch", "catch", "synchronized", "constructor"}

    if ext in (".groovy", ".java", ".ts", ".js"):
        class_match = CLASS_PATTERN.search(content)
        if not class_match:
            return None
        class_name = class_match.group(1)
        extends_name = class_match.group(2) or ""

        lines = content.splitlines()
        for idx, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean or line_clean.startswith(("//", "/*", "*")):
                continue

            if "=" in line_clean:
                eq_pos = line_clean.find("=")
                paren_pos = line_clean.find("(")
                if paren_pos != -1 and eq_pos < paren_pos:
                    continue

            if "(" in line_clean and ")" in line_clean:
                has_brace = "{" in line_clean or (idx + 1 < len(lines) and lines[idx + 1].strip().startswith("{"))
                if has_brace:
                    m = re.search(r'(?:public\s+|protected\s+|private\s+|static\s+|async\s+|def\s+|void\s+|[\w<>\[\],]+\s+)*([a-zA-Z_]\w*)\s*\(([^)]*)\)', line_clean)
                    if m:
                        name = m.group(1)
                        params = m.group(2).strip()
                        if name not in control_keywords and name != class_name:
                            comment = ""
                            if idx > 0 and lines[idx - 1].strip().startswith("//"):
                                comment = lines[idx - 1].strip().lstrip("/ ").strip()
                            methods.append({
                                "name": name,
                                "params": re.sub(r'\s+', ' ', params),
                                "comment": comment
                            })

    elif ext == ".py":
        class_match = PY_CLASS_PATTERN.search(content)
        if not class_match:
            return None
        class_name = class_match.group(1)
        extends_name = class_match.group(2) or ""

        lines = content.splitlines()
        for idx, line in enumerate(lines):
            line_clean = line.strip()
            if line_clean.startswith("def "):
                m = re.search(r'def\s+([a-zA-Z_]\w*)\s*\(([^)]*)\):', line_clean)
                if m:
                    name = m.group(1)
                    params = m.group(2).replace("self,", "").replace("self", "").strip()
                    if not name.startswith("__") and name not in control_keywords:
                        comment = ""
                        if idx + 1 < len(lines) and '"""' in lines[idx + 1]:
                            comment = lines[idx + 1].replace('"""', '').strip()
                        methods.append({
                            "name": name,
                            "params": re.sub(r'\s+', ' ', params),
                            "comment": comment
                        })
    else:
        return None

    # Deduplicate methods preserving order
    seen = set()
    unique_methods = []
    for meth in methods:
        sig = f"{meth['name']}({meth['params']})"
        if sig not in seen:
            seen.add(sig)
            unique_methods.append(meth)

    lines = content.splitlines()
    return {
        "rel_path": rel_path,
        "class_name": class_name,
        "extends": extends_name,
        "raw_size_bytes": len(content.encode("utf-8")),
        "line_count": len(lines),
        "methods": unique_methods
    }


def build_repo_map(target_repo=None, output_txt=None, output_json=None):
    """Scans Page Classes across polyglot targets (Groovy, TypeScript, Python) and builds map."""
    repo = target_repo or resolve_target_repo()
    txt_dest = output_txt or OUTPUT_TXT
    json_dest = output_json or OUTPUT_JSON

    classes = []
    total_raw_bytes = 0
    total_raw_lines = 0

    candidate_dirs = [
        os.path.join(repo, "Keywords"),
        os.path.join(repo, "pages"),
        os.path.join(repo, "page-objects"),
        os.path.join(repo, "page_objects"),
        os.path.join(repo, "src", "pages"),
        os.path.join(repo, "tests", "pages"),
    ]

    scanned_files = set()
    for d in candidate_dirs:
        if os.path.isdir(d):
            for root, _, files in os.walk(d):
                if any(ignored in root for ignored in (".git", "node_modules", "__pycache__", ".venv")):
                    continue
                for fname in sorted(files):
                    if fname.endswith((".groovy", ".ts", ".js", ".py", ".java")):
                        full_path = os.path.join(root, fname)
                        if full_path not in scanned_files:
                            scanned_files.add(full_path)
                            info = extract_class_info(full_path, repo_root=repo)
                            if info and info.get("methods"):
                                classes.append(info)
                                total_raw_bytes += info["raw_size_bytes"]
                                total_raw_lines += info["line_count"]

    # Sort classes: BasePage first, then alphabetical
    classes.sort(key=lambda c: (0 if c["class_name"] == "BasePage" else 1, c["class_name"]))

    # Render text map
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out_lines = [
        "# ==============================================================================",
        "# ENTERPRISE AUTOMATION REPOSITORY MAP (Aider-Style AST Compression)",
        f"# Generated : {timestamp}",
        f"# Target    : {repo}",
        f"# Scope     : {len(classes)} Classes ({total_raw_lines} source lines, {total_raw_bytes / 1024:.1f} KB)",
        "# Purpose   : Token-budgeted index (< 600 tokens) for instant method lookup",
        "# ==============================================================================\n"
    ]

    total_methods = 0
    for cls in classes:
        ext_str = f" extends {cls['extends']}" if cls['extends'] else ""
        out_lines.append(f"{cls['rel_path']} ({cls['line_count']} lines)")
        out_lines.append(f"  class {cls['class_name']}{ext_str}:")
        for m in cls["methods"]:
            total_methods += 1
            cmt = f" # {m['comment']}" if m['comment'] else ""
            out_lines.append(f"    def {m['name']}({m['params']}){cmt}")
        out_lines.append("")

    rendered_text = "\n".join(out_lines)
    compressed_bytes = len(rendered_text.encode("utf-8"))
    ratio = (1.0 - (compressed_bytes / total_raw_bytes)) * 100 if total_raw_bytes > 0 else 0.0
    est_tokens = len(rendered_text) // 4

    json_payload = {
        "generated_at": timestamp,
        "target_repository": repo,
        "classes_count": len(classes),
        "methods_count": total_methods,
        "source_lines": total_raw_lines,
        "raw_bytes": total_raw_bytes,
        "compressed_bytes": compressed_bytes,
        "compression_ratio_pct": round(ratio, 2),
        "estimated_tokens": est_tokens,
        "classes": classes
    }

    # 1. Save to primary destination (tools/repo_map.txt in Hub) with cross-platform advisory locking
    try:
        from tools.core.file_lock import locked_write, locked_json_write
    except ImportError:
        try:
            from core.file_lock import locked_write, locked_json_write
        except ImportError:
            def locked_write(p, c, **kw):
                with open(p, "w", encoding="utf-8") as f:
                    f.write(c)
            def locked_json_write(p, d, **kw):
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(d, f, indent=2, ensure_ascii=False)

    try:
        is_hub_target = os.path.samefile(repo, HUB_ROOT)
    except (FileNotFoundError, OSError, ValueError):
        is_hub_target = os.path.realpath(repo).lower() == os.path.realpath(HUB_ROOT).lower()

    if is_hub_target:
        try:
            locked_write(txt_dest, rendered_text)
            locked_json_write(json_dest, json_payload)
        except OSError as err:
            sys.stderr.write(f"Notice: Hub repo_map write skipped (read-only environment): {err}\n")
    else:
        # Spoke project target: strictly isolate from Hub directory
        if output_txt:
            try:
                locked_write(output_txt, rendered_text)
            except OSError as err:
                sys.stderr.write(f"Notice: Could not write custom repo_map txt: {err}\n")
        if output_json:
            try:
                locked_json_write(output_json, json_payload)
            except OSError as err:
                sys.stderr.write(f"Notice: Could not write custom repo_map json: {err}\n")
        if not output_txt and not output_json:
            try:
                target_txt = os.path.join(repo, "repo_map.txt")
                locked_write(target_txt, rendered_text)
                target_json = os.path.join(repo, "repo_map.json")
                locked_json_write(target_json, json_payload)
            except OSError as err:
                sys.stderr.write(f"Notice: Could not write target repo_map: {err}\n")

    output_dest = output_txt if output_txt else (txt_dest if is_hub_target else os.path.join(repo, "repo_map.txt"))

    return {
        "target_repo": repo,
        "classes_count": len(classes),
        "methods_count": total_methods,
        "source_lines": total_raw_lines,
        "raw_bytes": total_raw_bytes,
        "compressed_bytes": compressed_bytes,
        "compression_ratio_pct": ratio,
        "estimated_tokens": est_tokens,
        "output_file": output_dest
    }


def main():
    parser = argparse.ArgumentParser(description="Enterprise Repository Map Compressor")
    parser.add_argument("target", nargs="?", default=None, help="Target repository containing Keywords/")
    parser.add_argument("--target", "--repo", "--path", dest="repo_path", default=None, help="Target repository path")
    parser.add_argument("--print", action="store_true", help="Print repository map to console")
    args = parser.parse_args()

    try:
        target_repo = resolve_target_repo(cli_target=args.target, cli_repo=args.repo_path)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        return 1

    stats = build_repo_map(target_repo=target_repo)
    print("\n======================================================================")
    print("       Enterprise Repository Map Compressor (Aider-Style AST Map)           ")
    print("======================================================================")
    print(f"  Target Repository       : {stats['target_repo']}")
    print(f"  Indexed Classes         : {stats['classes_count']} Page Classes & Helpers")
    print(f"  Extracted Methods       : {stats['methods_count']} API signatures")
    print(f"  Source Lines Processed  : {stats['source_lines']:,} lines ({stats['raw_bytes'] / 1024:.1f} KB)")
    print(f"  Compressed Map Size     : {stats['compressed_bytes'] / 1024:.1f} KB (~{stats['estimated_tokens']} tokens)")
    print(f"  Compression Ratio       : {stats['compression_ratio_pct']:.1f}% reduction")
    print(f"  Artifact Generated      : {stats['output_file']}")
    print("======================================================================\n")

    if args.print:
        with open(stats['output_file'], "r", encoding="utf-8") as f:
            print(f.read())

    return 0


if __name__ == "__main__":
    sys.exit(main())
