#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

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
import ast
import copy
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HUB_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
OUTPUT_TXT = os.path.join(SCRIPT_DIR, "repo_map.txt")
OUTPUT_JSON = os.path.join(SCRIPT_DIR, "repo_map.json")

# Regex patterns for Groovy/Java/TS/JS classes and methods
CLASS_DECL_PATTERN = re.compile(
    r'(?:^|\s)(?:export\s+|public\s+|default\s+|abstract\s+|final\s+)*class\s+([A-Za-z0-9_]+)(?:\s*<[^>]*>)?(?:\s+extends\s+([A-Za-z0-9_]+)(?:<[^>]*>)?)?',
    re.MULTILINE
)
CONTROL_KEYWORDS = {"if", "for", "while", "switch", "catch", "synchronized", "constructor"}


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


def strip_comments_and_strings(source_code: str) -> str:
    """Strips comments, string literals, and template strings preserving line numbers and string length."""
    pattern = re.compile(
        r'(?P<BLOCK_COMMENT>/\*[\s\S]*?\*/)|'
        r'(?P<LINE_COMMENT>//[^\r\n]*)|'
        r'(?P<TRIPLE_DOUBLE>"""[\s\S]*?""")|'
        r'(?P<TRIPLE_SINGLE>\'\'\'[\s\S]*?\'\'\')|'
        r'(?P<DOLLAR_SLASHY>\$/[\s\S]*?/\$)|'
        r'(?P<DOUBLE_STRING>"(?:\\.|[^"\\])*")|'
        r'(?P<SINGLE_STRING>\'(?:\\.|[^\'\\])*\')|'
        r'(?P<BACKTICK_STRING>`(?:\\.|[^`\\])*`)',
        re.DOTALL
    )
    return pattern.sub(lambda m: re.sub(r'[^\r\n]', ' ', m.group(0)), source_code)


def clean_param_sig(p: str) -> str:
    """Simplifies parameter list for compact, token-budgeted method signatures."""
    if not p:
        return ""
    params = []
    current = []
    bracket_depth = 0
    for char in p:
        if char in "([<":
            bracket_depth += 1
            current.append(char)
        elif char in ")]>":
            bracket_depth = max(0, bracket_depth - 1)
            current.append(char)
        elif char == "," and bracket_depth == 0:
            params.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if current:
        params.append("".join(current).strip())

    res = []
    for item in params:
        if not item:
            continue
        if "=" in item:
            item = item.split("=")[0].strip()
        if ":" in item:
            item = item.split(":")[0].strip()
        parts = item.split()
        if len(parts) > 1:
            item = parts[-1]
        res.append(item)
    return ", ".join(res)


def _extract_classes_py(content: str, rel_path: str, raw_size_bytes: int, line_count: int) -> list:
    """Uses Python built-in AST to extract class definitions and direct methods, ignoring nested local functions."""
    try:
        tree = ast.parse(content)
    except Exception:
        return []

    classes = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            extends_name = ""
            if node.bases:
                base = node.bases[0]
                if isinstance(base, ast.Name):
                    extends_name = base.id
                elif isinstance(base, ast.Attribute):
                    extends_name = base.attr
                elif hasattr(ast, "unparse"):
                    extends_name = ast.unparse(base)

            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    name = item.name
                    if name.startswith("__") or name in CONTROL_KEYWORDS:
                        continue
                    args_copy = copy.deepcopy(item.args)
                    if getattr(args_copy, "posonlyargs", None) and args_copy.posonlyargs and args_copy.posonlyargs[0].arg in ("self", "cls"):
                        args_copy.posonlyargs.pop(0)
                    elif args_copy.args and args_copy.args[0].arg in ("self", "cls"):
                        args_copy.args.pop(0)
                    raw_params = ast.unparse(args_copy) if hasattr(ast, "unparse") else ""
                    doc = ast.get_docstring(item) or ""
                    first_doc = doc.strip().splitlines()[0] if doc.strip() else ""
                    methods.append({
                        "name": name,
                        "params": clean_param_sig(re.sub(r'\s+', ' ', raw_params)),
                        "comment": first_doc
                    })

            seen = set()
            unique_methods = []
            for meth in methods:
                sig = f"{meth['name']}({meth['params']})"
                if sig not in seen:
                    seen.add(sig)
                    unique_methods.append(meth)

            classes.append({
                "rel_path": rel_path,
                "class_name": class_name,
                "extends": extends_name,
                "raw_size_bytes": raw_size_bytes,
                "line_count": line_count,
                "methods": unique_methods
            })
    return classes


def _extract_classes_brace(content: str, rel_path: str, raw_size_bytes: int, line_count: int) -> list:
    """
    Parses TS, JS, Groovy, Java tracking brace depth to only capture methods at direct class body level (depth 1).
    Eliminates false-positive method calls inside function bodies.
    Supports multiple classes per file, multiline method declarations, and multiline class headers.
    """
    clean = strip_comments_and_strings(content)
    orig_lines = content.splitlines()
    clean_lines = clean.splitlines()
    classes = []

    current_class = None
    pending_class = None
    class_depth = 0
    depth = 0
    pending_method = None
    in_multiline_annotation = False

    for idx, (orig_line, clean_line) in enumerate(zip(orig_lines, clean_lines)):
        clean_strip = clean_line.strip()

        # Check for class declaration when not in class
        if current_class is None and pending_class is None:
            m = CLASS_DECL_PATTERN.search(clean_line)
            if m:
                eq_pos = clean_line.find("=")
                cls_pos = m.start()
                if eq_pos == -1 or cls_pos < eq_pos:
                    pending_class = {
                        "rel_path": rel_path,
                        "class_name": m.group(1),
                        "extends": m.group(2) or "",
                        "raw_size_bytes": raw_size_bytes,
                        "line_count": line_count,
                        "methods": [],
                        "decl_depth": depth
                    }

        if pending_class is not None and current_class is None:
            if not pending_class["extends"]:
                ext_m = re.search(r'\bextends\s+([A-Za-z0-9_]+)', clean_line)
                if ext_m:
                    pending_class["extends"] = ext_m.group(1)
            if "{" in clean_line:
                current_class = pending_class
                pending_class = None
                class_depth = current_class["decl_depth"] + 1

        if current_class is not None:
            # Handle multiline annotations
            if in_multiline_annotation:
                if ")" in clean_strip:
                    in_multiline_annotation = False
                    clean_strip = clean_strip[clean_strip.find(")") + 1:].strip()
                else:
                    clean_strip = ""

            # Check and strip annotations (e.g. @Keyword(...), @Step(...))
            if clean_strip.startswith("@"):
                open_p = clean_strip.count("(")
                close_p = clean_strip.count(")")
                if open_p > close_p:
                    in_multiline_annotation = True
                    clean_strip = ""
                else:
                    clean_strip = re.sub(r'^\s*@\w+(?:\([^)]*\))?\s*', '', clean_strip).strip()

            if pending_method is not None:
                # Accumulate multiline parameters
                for char in clean_line:
                    if char == "(":
                        pending_method["paren_depth"] += 1
                        pending_method["param_parts"].append(char)
                    elif char == ")":
                        pending_method["paren_depth"] -= 1
                        if pending_method["paren_depth"] == 0:
                            raw_params = "".join(pending_method["param_parts"]).strip()
                            current_class["methods"].append({
                                "name": pending_method["name"],
                                "params": clean_param_sig(re.sub(r'\s+', ' ', raw_params)),
                                "comment": pending_method["comment"]
                            })
                            pending_method = None
                            break
                        else:
                            pending_method["param_parts"].append(char)
                    else:
                        pending_method["param_parts"].append(char)

            elif depth == class_depth and clean_strip:
                eq_pos = clean_strip.find("=")
                paren_pos = clean_strip.find("(")
                if paren_pos != -1 and (eq_pos == -1 or paren_pos < eq_pos):
                    meth_start_m = re.search(
                        r'(?:public\s+|protected\s+|private\s+|static\s+|async\s+|def\s+|void\s+|[\w<>\[\],]+\s+)*([a-zA-Z_]\w*)\s*\(',
                        clean_strip
                    )
                    if meth_start_m:
                        name = meth_start_m.group(1)
                        if name not in CONTROL_KEYWORDS and name != current_class["class_name"]:
                            start_p = meth_start_m.end() - 1
                            paren_depth = 0
                            param_parts = []
                            finished = False
                            for char in clean_strip[start_p:]:
                                if char == "(":
                                    paren_depth += 1
                                    if paren_depth > 1:
                                        param_parts.append(char)
                                elif char == ")":
                                    paren_depth -= 1
                                    if paren_depth == 0:
                                        finished = True
                                        break
                                    else:
                                        param_parts.append(char)
                                else:
                                    param_parts.append(char)

                            comment = ""
                            if idx > 0 and orig_lines[idx - 1].strip().startswith("//"):
                                comment = orig_lines[idx - 1].strip().lstrip("/ ").strip()

                            if finished:
                                raw_params = "".join(param_parts).strip()
                                current_class["methods"].append({
                                    "name": name,
                                    "params": clean_param_sig(re.sub(r'\s+', ' ', raw_params)),
                                    "comment": comment
                                })
                            else:
                                pending_method = {
                                    "name": name,
                                    "comment": comment,
                                    "paren_depth": paren_depth,
                                    "param_parts": param_parts
                                }

            open_braces = clean_line.count("{")
            close_braces = clean_line.count("}")
            depth += (open_braces - close_braces)

            if depth < class_depth:
                seen = set()
                unique_methods = []
                for meth in current_class["methods"]:
                    sig = f"{meth['name']}({meth['params']})"
                    if sig not in seen:
                        seen.add(sig)
                        unique_methods.append(meth)
                current_class["methods"] = unique_methods
                if "decl_depth" in current_class:
                    del current_class["decl_depth"]
                classes.append(current_class)
                current_class = None
                class_depth = 0
                pending_method = None

    return classes


def extract_class_info(file_path, repo_root=None):
    """Parses a Groovy, TypeScript, JavaScript, or Python file and extracts class names and direct methods."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    base_root = repo_root or HUB_ROOT
    try:
        rel_path = os.path.relpath(file_path, base_root)
    except ValueError:
        rel_path = os.path.abspath(file_path)

    ext = os.path.splitext(file_path)[1].lower()
    raw_size_bytes = len(content.encode("utf-8"))
    lines = content.splitlines()
    line_count = len(lines)

    if ext in (".groovy", ".java", ".ts", ".js"):
        return _extract_classes_brace(content, rel_path, raw_size_bytes, line_count)
    elif ext == ".py":
        return _extract_classes_py(content, rel_path, raw_size_bytes, line_count)
    return []


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

    # If target repo is Hub mode or no root page dirs found, scan polyglot suites in examples/
    if not any(os.path.isdir(d) for d in candidate_dirs):
        examples_dir = os.path.join(repo, "examples")
        if os.path.isdir(examples_dir):
            for root, dirs, _ in os.walk(examples_dir):
                if any(ignored in root for ignored in (".git", "node_modules", "__pycache__", ".venv")):
                    continue
                for dname in ("pages", "Keywords", "page-objects", "page_objects"):
                    if dname in dirs:
                        candidate_dirs.append(os.path.join(root, dname))

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
                            file_classes = extract_class_info(full_path, repo_root=repo)
                            if isinstance(file_classes, dict):
                                file_classes = [file_classes]
                            file_counted = False
                            for info in (file_classes or []):
                                if info and info.get("methods"):
                                    classes.append(info)
                                    if not file_counted:
                                        total_raw_bytes += info["raw_size_bytes"]
                                        total_raw_lines += info["line_count"]
                                        file_counted = True

    # Sort classes: BasePage first, then alphabetical
    classes.sort(key=lambda c: (0 if c["class_name"] == "BasePage" else 1, c["class_name"]))

    # Render text map (< 500 tokens budget)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target_name = os.path.basename(repo) or repo
    out_lines = [
        f"# AST REPO MAP | Target: {target_name} | < 500 tokens\n"
    ]

    total_methods = 0
    for cls in classes:
        display_path = cls["rel_path"].replace("\\", "/")
        if display_path.startswith("examples/"):
            display_path = display_path[len("examples/"):]
        ext_str = f" extends {cls['extends']}" if (cls["extends"] and cls["extends"] != "BasePage") else ""
        out_lines.append(f"{display_path} ({cls['line_count']} lines)")
        out_lines.append(f"class {cls['class_name']}{ext_str}:")
        for m in cls["methods"]:
            total_methods += 1
            out_lines.append(f"  {m['name']}({m['params']})")
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
