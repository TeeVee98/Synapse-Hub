#!/usr/bin/env python3
"""
Enterprise Test Impact Analyzer (Graphify-Powered)
--------------------------------------------
Analyzes which Test Cases out of Enterprise Test Cases are directly or transitively
impacted when Page Classes or Helper classes are modified.

Usage:
  python3 tools/test_impact.py --file Keywords/pages/CommonCategoryPage.groovy
  python3 tools/test_impact.py --git-diff
"""

import os
import sys
import json
import argparse
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
GRAPH_PATH = os.path.join(REPO_ROOT, "graphify-out", "graph.json")

def load_graph():
    if not os.path.exists(GRAPH_PATH):
        print(f"❌ Không tìm thấy {GRAPH_PATH}!")
        print("💡 Hãy chạy: ~/.venv_graphify/bin/graphify update .")
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
        if not files:
            res = subprocess.run(
                ["git", "-C", REPO_ROOT, "status", "--porcelain"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            files = [line[3:].strip() for line in res.stdout.splitlines() if line.strip()]
        return files
    except Exception as e:
        print(f"⚠️  Không thể lấy git diff: {e}")
        return []

def analyze_impact(graph_data, target_files):
    nodes_by_id = {n["id"]: n for n in graph_data.get("nodes", [])}
    links = graph_data.get("links", [])

    # Map target files to node IDs
    target_ids = set()
    for n in graph_data.get("nodes", []):
        src_file = n.get("source_file", "")
        for tf in target_files:
            tf_norm = tf.replace("\\", "/")
            if src_file and (src_file == tf_norm or src_file.endswith("/" + os.path.basename(tf_norm))):
                target_ids.add(n["id"])

    if not target_ids:
        return {}

    # Build reverse adjacency map (target -> sources depending on it)
    rev_adj = {}
    for link in links:
        src = link.get("source")
        tgt = link.get("target")
        if tgt and src:
            rev_adj.setdefault(tgt, set()).add(src)

    # BFS traversal to discover all dependent scripts
    visited = set(target_ids)
    queue = list(target_ids)
    impacted_scripts = set()

    while queue:
        curr = queue.pop(0)
        for parent in rev_adj.get(curr, []):
            if parent not in visited:
                visited.add(parent)
                queue.append(parent)
                p_node = nodes_by_id.get(parent)
                if p_node:
                    src_f = p_node.get("source_file", "").replace("\\", "/")
                    if src_f.startswith("Scripts/"):
                        # Extract folder name under Scripts/
                        parts = src_f.split("/")
                        if len(parts) >= 2:
                            tc_folder = parts[1]
                            impacted_scripts.add(tc_folder)

    return sorted(list(impacted_scripts))

def main():
    parser = argparse.ArgumentParser(description="Enterprise Test Impact Analyzer")
    parser.add_argument("--file", "-f", nargs="+", help="Tệp tin cần phân tích (ví dụ: Keywords/pages/CommonCategoryPage.groovy)")
    parser.add_argument("--git-diff", action="store_true", help="Tự động phân tích các tệp tin thay đổi qua git")
    parser.add_argument("--json", action="store_true", help="Xuất kết quả dưới dạng JSON")
    args = parser.parse_args()

    target_files = []
    if args.file:
        target_files.extend(args.file)
    if args.git_diff or not target_files:
        git_files = get_git_modified_files()
        target_files.extend([f for f in git_files if f.startswith("Keywords/")])

    if not target_files:
        print("ℹ️  Không có file Keywords/ nào được chỉ định hoặc thay đổi trong git.")
        return

    graph_data = load_graph()
    impacted_tcs = analyze_impact(graph_data, target_files)

    total_tcs = 259
    impacted_count = len(impacted_tcs)
    saved_count = total_tcs - impacted_count
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
    print("  Enterprise Test Impact ANALYZER (GRAPHIFY AST KNOWLEDGE GRAPH)")
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
