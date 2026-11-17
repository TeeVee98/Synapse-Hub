#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/heap_leak_analyzer.py — Client-Side Memory Leak Sentinel & Heap Analyzer
-------------------------------------------------------------------------------
Inspired by Oven Bun and Zed Industries memory profiling standards.

Core Capabilities:
  1. JS Heap Growth Delta: Compares memory metrics between baseline (T0) and
     post-iteration (T1) states. Flags memory leaks if heap growth exceeds
     the specified threshold (default: 15.0%).
  2. Detached DOM Nodes Sentinel: Detects lingering detached DOM elements
     retained in memory after page navigation or component destruction.
  3. Actionable Diagnostics: Highlights memory retention leaks and recommends
     unbinding event listeners, clearing intervals, or nulling detached DOM handles.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger("heap_leak_analyzer")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEFAULT_HEAP_GROWTH_THRESHOLD_PCT = 15.0
DEFAULT_DETACHED_DOM_THRESHOLD = 0


class MemoryLeakError(Exception):
    """Raised when client memory leak thresholds are exceeded."""
    pass


def parse_metric_value(raw: Any) -> float:
    """Parse integer or float byte metric safely."""
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        cleaned = raw.strip().replace(",", "")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    return 0.0


def analyze_memory_delta(
    t0_metrics: Dict[str, Any],
    t1_metrics: Dict[str, Any],
    threshold_pct: float = DEFAULT_HEAP_GROWTH_THRESHOLD_PCT,
    max_detached_nodes: int = DEFAULT_DETACHED_DOM_THRESHOLD,
) -> Dict[str, Any]:
    """
    Compares baseline (T0) and post-action (T1) browser performance metrics.

    Metrics evaluated:
      - JSHeapUsedSize (bytes)
      - JSHeapTotalSize (bytes)
      - DetachedDOMNodes / Nodes count
    """
    heap_t0 = parse_metric_value(
        t0_metrics.get("JSHeapUsedSize", t0_metrics.get("js_heap_used", 0))
    )
    heap_t1 = parse_metric_value(
        t1_metrics.get("JSHeapUsedSize", t1_metrics.get("js_heap_used", 0))
    )

    detached_t0 = int(
        parse_metric_value(
            t0_metrics.get("DetachedDOMNodes", t0_metrics.get("detached_nodes", 0))
        )
    )
    detached_t1 = int(
        parse_metric_value(
            t1_metrics.get("DetachedDOMNodes", t1_metrics.get("detached_nodes", 0))
        )
    )

    heap_delta_bytes = heap_t1 - heap_t0
    heap_growth_pct = (
        round((heap_delta_bytes / heap_t0) * 100.0, 2) if heap_t0 > 0 else 0.0
    )
    detached_delta = detached_t1 - detached_t0

    violations: List[str] = []

    # 1. Monotonic Heap Growth Check
    if heap_t0 > 0 and heap_growth_pct > threshold_pct:
        violations.append(
            f"JS Heap grew by {heap_growth_pct}% ({heap_delta_bytes / 1024 / 1024:.2f} MB), "
            f"exceeding threshold of {threshold_pct}%."
        )

    # 2. Detached DOM Nodes Check
    if detached_t1 > max_detached_nodes:
        violations.append(
            f"Detected {detached_t1} detached DOM nodes in memory (delta: +{detached_delta}), "
            f"exceeding allowed threshold of {max_detached_nodes}."
        )

    is_leak_detected = len(violations) > 0

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_leak_detected": is_leak_detected,
        "heap_t0_bytes": heap_t0,
        "heap_t1_bytes": heap_t1,
        "heap_delta_bytes": heap_delta_bytes,
        "heap_growth_pct": heap_growth_pct,
        "threshold_pct": threshold_pct,
        "detached_t0": detached_t0,
        "detached_t1": detached_t1,
        "detached_delta": detached_delta,
        "max_detached_nodes": max_detached_nodes,
        "violations": violations,
        "remediation": [
            "Check for unremoved event listeners on destroyed DOM elements.",
            "Verify setInterval / setTimeout timers are cleared on unmount.",
            "Ensure detached component closures or global registries do not retain DOM elements.",
        ] if is_leak_detected else [],
    }


def inspect_heap_snapshot(snapshot_path: str) -> Dict[str, Any]:
    """
    Parses a Chrome DevTools heap snapshot JSON file to extract summary statistics.
    """
    if not os.path.isfile(snapshot_path):
        raise FileNotFoundError(f"Heap snapshot file not found: {snapshot_path}")

    with open(snapshot_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("snapshot", {}).get("meta", {})
    node_fields = meta.get("node_fields", [])
    node_types = meta.get("node_types", [[]])[0] if meta.get("node_types") else []

    nodes = data.get("nodes", [])
    node_stride = len(node_fields) if node_fields else 1
    total_nodes = len(nodes) // node_stride if node_stride > 0 else 0

    return {
        "snapshot_path": snapshot_path,
        "total_nodes": total_nodes,
        "node_types": node_types,
        "meta": data.get("snapshot", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Heap Leak Analyzer — Client Memory Leak Sentinel"
    )
    parser.add_argument(
        "--t0",
        help="JSON string or file path containing baseline metrics (T0).",
    )
    parser.add_argument(
        "--t1",
        help="JSON string or file path containing post-iteration metrics (T1).",
    )
    parser.add_argument(
        "--threshold-pct",
        type=float,
        default=DEFAULT_HEAP_GROWTH_THRESHOLD_PCT,
        help="Allowed JS heap growth percentage (default: 15.0%%).",
    )
    parser.add_argument(
        "--max-detached",
        type=int,
        default=DEFAULT_DETACHED_DOM_THRESHOLD,
        help="Allowed detached DOM nodes (default: 0).",
    )
    parser.add_argument(
        "--snapshot",
        help="Inspect a single Chrome DevTools .heapsnapshot JSON file.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON results.",
    )

    args = parser.parse_args()

    if args.snapshot:
        try:
            info = inspect_heap_snapshot(args.snapshot)
            if args.json:
                print(json.dumps(info, indent=2))
            else:
                print(f"[PASS] Snapshot parsed: {info['total_nodes']} total nodes.")
            return 0
        except Exception as e:
            print(f"[FAIL] Snapshot error: {e}")
            return 1

    if args.t0 and args.t1:
        def load_metrics(val: str) -> Dict[str, Any]:
            if os.path.isfile(val):
                with open(val, "r", encoding="utf-8") as f:
                    return json.load(f)
            return json.loads(val)

        try:
            m0 = load_metrics(args.t0)
            m1 = load_metrics(args.t1)
        except Exception as e:
            print(f"[FAIL] Failed to parse input metrics: {e}")
            return 1

        result = analyze_memory_delta(
            m0,
            m1,
            threshold_pct=args.threshold_pct,
            max_detached_nodes=args.max_detached,
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["is_leak_detected"]:
                print(f"[FAIL] Memory leak detected ({result['heap_growth_pct']}% growth):")
                for v in result["violations"]:
                    print(f"   - {v}")
                print("\nRecommended remediation:")
                for r in result["remediation"]:
                    print(f"   * {r}")
                return 1
            else:
                print(
                    f"[PASS] Memory stable: JS Heap growth {result['heap_growth_pct']}% "
                    f"<= {args.threshold_pct}%, Detached Nodes: {result['detached_t1']}."
                )
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
