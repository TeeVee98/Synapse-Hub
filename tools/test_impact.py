#!/usr/bin/env python3
"""
Universal Test Impact Analyzer (Graphify AST-Powered)
---------------------------------------------------
Analyzes which Test Cases are directly or transitively impacted
when Page Classes or Helper classes are modified, saving CI/CD execution time.

Usage:
  python3 tools/test_impact.py --file Keywords/pages/CommonCategoryPage.groovy
  python3 tools/test_impact.py --git-diff
"""

import os
import sys
import json
import glob
import argparse
import subprocess

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
GRAPH_PATH = os.path.join(REPO_ROOT, "graphify-out", "graph.json")


def load_graph():
    if not os.path.exists(GRAPH_PATH):
        print(f"❌ Không tìm thấy {GRAPH_PATH}!")
        print("💡 Hãy chạy: graphify update .")
        sys.exit(1)
    with open(GRAPH_PATH, "r", encoding="utf-8") as fp:
        return json.load(fp)


def get_git_modified_files():
    try:
        res = subprocess.run(
            ["git", "-C", REPO_ROOT, "diff", "--name-only", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        files = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        return files
    except Exception as e:
        print(f"⚠️  Không thể lấy git diff: {e}")
        return []


def get_total_test_cases(workspace_dir=REPO_ROOT, graph_data=None, override_total=None):
    """Dynamically counts test cases in repository or knowledge graph."""
    if override_total is not None and override_total > 0:
        return override_total

    # 1. Scan filesystem for test scripts
    test_patterns = [
        os.path.join(workspace_dir, "Scripts", "**", "*.groovy"),
        os.path.join(workspace_dir, "tests", "**", "*.spec.ts"),
        os.path.join(workspace_dir, "tests", "**", "*.test.ts"),
        os.path.join(workspace_dir, "tests", "**", "*.spec.js"),
        os.path.join(workspace_dir, "tests", "**", "*.test.js"),
        os.path.join(workspace_dir, "tests", "**", "test_*.py"),
        os.path.join(workspace_dir, "tests", "**", "*_test.py"),
    ]
    files = set()
    for pat in test_patterns:
        files.update(glob.glob(pat, recursive=True))
    if files:
        return len(files)

    # 2. Count test case nodes in graph if available
    if graph_data and "nodes" in graph_data:
        tc_nodes = [
            n for n in graph_data["nodes"]
            if any(k in str(n.get("label", "")).lower() or k in str(n.get("name", "")).lower()
                   for k in ["tc-", "testcase", "test_case", "spec"])
        ]
        if tc_nodes:
            return len(tc_nodes)

    return 0


def analyze_impact(graph_data, target_files):
    nodes = {n["id"]: n for n in graph_data.get("nodes", [])}
    edges = graph_data.get("edges", [])

    # Map target files to node IDs
    target_node_ids = set()
    for tf in target_files:
        norm_tf = tf.replace("\\", "/")
        base_name = os.path.basename(norm_tf)
        class_name = os.path.splitext(base_name)[0]

        for n_id, n in nodes.items():
            n_file = n.get("file", "").replace("\\", "/")
            if norm_tf in n_file or n_id == class_name or n.get("label") == class_name:
                target_node_ids.add(n_id)

    if not target_node_ids:
        return []

    # Build reverse dependency graph (who calls target)
    callers = {}
    for edge in edges:
        src = edge.get("source")
        tgt = edge.get("target")
        if tgt not in callers:
            callers[tgt] = set()
        callers[tgt].add(src)

    # BFS to find all upstream impacted nodes
    visited = set()
    queue = list(target_node_ids)
    while queue:
        curr = queue.pop(0)
        if curr in visited:
            continue
        visited.add(curr)
        for parent in callers.get(curr, []):
            if parent not in visited:
                queue.append(parent)

    # Filter for Test Case nodes
    impacted_test_cases = set()
    for node_id in visited:
        node = nodes.get(node_id, {})
        file_path = node.get("file", "")
        label = node.get("label", node_id)

        if "Scripts/" in file_path or "tests/" in file_path or "TC-" in label or "TC_" in label or "TC" in label:
            impacted_test_cases.add(label)

    return sorted(list(impacted_test_cases))


def main():
    parser = argparse.ArgumentParser(description="Universal Test Impact Analyzer")
    parser.add_argument("--file", "-f", nargs="+", help="Target modified files (e.g. Keywords/pages/CommonCategoryPage.groovy)")
    parser.add_argument("--git-diff", action="store_true", help="Analyze git modified files automatically")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--total", "-t", type=int, default=None, help="Explicit total test case count override")
    args = parser.parse_args()

    target_files = []
    if args.file:
        target_files.extend(args.file)
    if args.git_diff or not target_files:
        git_files = get_git_modified_files()
        target_files.extend([f for f in git_files if "Keywords/" in f or "pages/" in f or "src/" in f])

    if not target_files:
        print("ℹ️  Không có file Page Class / Keywords nào được chỉ định hoặc thay đổi trong git.")
        return

    graph_data = load_graph()
    impacted_tcs = analyze_impact(graph_data, target_files)

    total_tcs = get_total_test_cases(REPO_ROOT, graph_data, args.total)
    if total_tcs == 0:
        total_tcs = max(len(impacted_tcs), 1)

    impacted_count = len(impacted_tcs)
    saved_count = max(0, total_tcs - impacted_count)
    reduction_pct = (saved_count / total_tcs * 100) if total_tcs else 0

    if args.json:
        result = {
            "target_files": target_files,
            "impacted_count": impacted_count,
            "total_test_cases": total_tcs,
            "time_saved_percent": round(reduction_pct, 1),
            "impacted_test_cases": impacted_tcs
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print("\n" + "=" * 70)
    print("  UNIVERSAL TEST IMPACT ANALYZER (GRAPHIFY AST KNOWLEDGE GRAPH)")
    print("=" * 70)
    print("🔍 Tệp tin thay đổi / kiểm tra:")
    for tf in target_files:
        print(f"   • {tf}")

    print("\n📊 Đánh giá tác động kiểm thử:")
    print(f"   - Số Test Case bị ảnh hưởng trực tiếp : {impacted_count} / {total_tcs} TCs")
    print(f"   - Số Test Case KHÔNG cần chạy lại     : {saved_count} TCs")
    print(f"   - Tỷ lệ tiết kiệm thời gian CI/CD      : {reduction_pct:.1f}%")

    if impacted_tcs:
        print("\n📋 Danh sách Test Cases cần re-test:")
        for idx, tc in enumerate(impacted_tcs[:20], 1):
            print(f"   {idx:2d}. {tc}")
        if len(impacted_tcs) > 20:
            print(f"   ... và {len(impacted_tcs) - 20} Test Cases khác.")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
