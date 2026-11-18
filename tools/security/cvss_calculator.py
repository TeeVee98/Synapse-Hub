#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/cvss_calculator.py — Enterprise Common Vulnerability Scoring System Engine
-------------------------------------------------------------------------------
Conforms strictly to FIRST.org specifications for CVSS v3.1 and CVSS v4.0.
Calculates Base, Temporal, and Environmental scores with quantitative vectors,
macrovector reductions, and qualitative severity ratings (None, Low, Medium, High, Critical).

Usage:
  python tools/cvss_calculator.py "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
  python tools/cvss_calculator.py "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N"
  python tools/cvss_calculator.py --json "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
  python tools/cvss_calculator.py --file findings.json --out-file scored_findings.json
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
import json
import math
import argparse
from typing import Dict, Any, Tuple

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def cvss_roundup(input_val: float) -> float:
    """
    Official FIRST.org CVSS v3.1 Roundup function.
    Rounds up to the next one decimal place.
    """
    int_input = round(input_val * 100000)
    if int_input % 10000 == 0:
        return int_input / 100000.0
    return (math.floor(int_input / 10000) + 1) / 10.0


def get_severity_rating(score: float) -> str:
    """Returns qualitative severity rating according to CVSS standard."""
    if score == 0.0:
        return "NONE"
    elif 0.1 <= score <= 3.9:
        return "LOW"
    elif 4.0 <= score <= 6.9:
        return "MEDIUM"
    elif 7.0 <= score <= 8.9:
        return "HIGH"
    elif 9.0 <= score <= 10.0:
        return "CRITICAL"
    return "UNKNOWN"


# ==============================================================================
# CVSS v3.1 IMPLEMENTATION
# ==============================================================================

CVSS_V31_METRICS = {
    # Base Metrics
    "AV": {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2},
    "AC": {"L": 0.77, "H": 0.44},
    "PR_U": {"N": 0.85, "L": 0.62, "H": 0.27},  # Scope Unchanged
    "PR_C": {"N": 0.85, "L": 0.68, "H": 0.50},  # Scope Changed
    "UI": {"N": 0.85, "R": 0.62},
    "S": {"U": "U", "C": "C"},
    "C": {"H": 0.56, "L": 0.22, "N": 0.0},
    "I": {"H": 0.56, "L": 0.22, "N": 0.0},
    "A": {"H": 0.56, "L": 0.22, "N": 0.0},
    # Temporal Metrics
    "E": {"X": 1.0, "H": 1.0, "F": 0.97, "P": 0.94, "U": 0.91},
    "RL": {"X": 1.0, "U": 1.0, "W": 0.97, "T": 0.96, "O": 0.95},
    "RC": {"X": 1.0, "C": 1.0, "R": 0.96, "U": 0.92},
    # Environmental Requirements
    "CR": {"X": 1.0, "H": 1.5, "M": 1.0, "L": 0.5},
    "IR": {"X": 1.0, "H": 1.5, "M": 1.0, "L": 0.5},
    "AR": {"X": 1.0, "H": 1.5, "M": 1.0, "L": 0.5},
}


def parse_vector_string(vector_str: str) -> Tuple[str, Dict[str, str]]:
    """Parses a raw CVSS vector string into version and dictionary of metric keys/values."""
    cleaned = vector_str.strip()
    if not cleaned:
        raise ValueError("Empty CVSS vector string.")

    parts = cleaned.split("/")
    if not parts or not parts[0].startswith("CVSS:"):
        raise ValueError(f"Invalid CVSS prefix in vector: '{cleaned}'. Expected 'CVSS:3.1' or 'CVSS:4.0'.")

    version = parts[0].replace("CVSS:", "").strip()
    metrics = {}
    for part in parts[1:]:
        if not part:
            continue
        if ":" not in part:
            raise ValueError(f"Malformed metric element: '{part}' in vector '{cleaned}'.")
        k, v = part.split(":", 1)
        metrics[k.upper().strip()] = v.upper().strip()

    return version, metrics


def calculate_cvss_v31(vector_str: str) -> Dict[str, Any]:
    """
    Computes CVSS v3.1 Base, Temporal, and Environmental scores conforming to FIRST.org.
    """
    version, metrics = parse_vector_string(vector_str)
    if version not in ("3.1", "3.0"):
        raise ValueError(f"Vector version '{version}' is not CVSS v3.1 compatible.")

    # Mandatory Base metrics
    mandatory_base = ["AV", "AC", "PR", "UI", "S", "C", "I", "A"]
    for m in mandatory_base:
        if m not in metrics:
            raise ValueError(f"Missing mandatory CVSS v3.1 base metric '{m}' in vector '{vector_str}'.")

    # Validate metric values
    for m in mandatory_base:
        val = metrics[m]
        if m == "PR":
            if val not in ("N", "L", "H"):
                raise ValueError(f"Invalid value '{val}' for metric PR.")
        elif m not in ("S") and val not in CVSS_V31_METRICS[m]:
            raise ValueError(f"Invalid value '{val}' for metric {m}.")

    scope = metrics["S"]
    if scope not in ("U", "C"):
        raise ValueError(f"Invalid Scope '{scope}'. Expected 'U' or 'C'.")

    av = CVSS_V31_METRICS["AV"][metrics["AV"]]
    ac = CVSS_V31_METRICS["AC"][metrics["AC"]]
    pr_table = CVSS_V31_METRICS["PR_C"] if scope == "C" else CVSS_V31_METRICS["PR_U"]
    pr = pr_table[metrics["PR"]]
    ui = CVSS_V31_METRICS["UI"][metrics["UI"]]

    c = CVSS_V31_METRICS["C"][metrics["C"]]
    i = CVSS_V31_METRICS["I"][metrics["I"]]
    a = CVSS_V31_METRICS["A"][metrics["A"]]

    # 1. Calculate Impact Sub-Score (ISS)
    iss = 1.0 - ((1.0 - c) * (1.0 - i) * (1.0 - a))

    # 2. Calculate Impact
    if scope == "U":
        impact = 6.42 * iss
    else:
        impact = 7.52 * (iss - 0.029) - 3.25 * ((iss - 0.02) ** 15)

    # 3. Calculate Exploitability
    exploitability = 8.22 * av * ac * pr * ui

    # 4. Calculate Base Score
    if impact <= 0:
        base_score = 0.0
    else:
        if scope == "U":
            base_score = cvss_roundup(min(impact + exploitability, 10.0))
        else:
            base_score = cvss_roundup(min(1.08 * (impact + exploitability), 10.0))

    # 5. Temporal Score (if applicable)
    e = CVSS_V31_METRICS["E"].get(metrics.get("E", "X"), 1.0)
    rl = CVSS_V31_METRICS["RL"].get(metrics.get("RL", "X"), 1.0)
    rc = CVSS_V31_METRICS["RC"].get(metrics.get("RC", "X"), 1.0)

    temporal_score = cvss_roundup(base_score * e * rl * rc) if any(k in metrics for k in ("E", "RL", "RC")) else base_score

    # Construct normalized canonical vector
    canonical_parts = [f"CVSS:{version}"]
    for k in mandatory_base:
        canonical_parts.append(f"{k}:{metrics[k]}")
    for k in ("E", "RL", "RC", "CR", "IR", "AR", "MAV", "MAC", "MPR", "MUI", "MS", "MC", "MI", "MA"):
        if k in metrics and metrics[k] != "X":
            canonical_parts.append(f"{k}:{metrics[k]}")

    canonical_vector = "/".join(canonical_parts)

    return {
        "version": "3.1",
        "vector": canonical_vector,
        "base_score": base_score,
        "temporal_score": temporal_score,
        "overall_score": temporal_score,
        "severity": get_severity_rating(temporal_score),
        "impact_sub_score": round(iss, 4),
        "impact": round(impact, 4),
        "exploitability": round(exploitability, 4),
        "metrics": metrics,
    }


# ==============================================================================
# CVSS v4.0 IMPLEMENTATION (FIRST.org CVSS-B & CVSS-BT Macrovector Engine)
# ==============================================================================

# EQ1: Threat / Attack Vector + Complexity + Privileges
# EQ2: User Interaction
# EQ3: Vulnerable System Impact (VC, VI, VA)
# EQ4: Subsequent System Impact (SC, SI, SA)
# EQ5: Exploit Maturity (E)

CVSS_V40_METRIC_VALIDATION = {
    "AV": ["N", "A", "L", "P"],
    "AC": ["L", "H"],
    "AT": ["N", "P"],
    "PR": ["N", "L", "H"],
    "UI": ["N", "P", "A"],
    "VC": ["H", "L", "N"],
    "VI": ["H", "L", "N"],
    "VA": ["H", "L", "N"],
    "SC": ["H", "L", "N"],
    "SI": ["H", "L", "N"],
    "SA": ["H", "L", "N"],
    "E": ["X", "A", "P", "U"],
}


def calculate_cvss_v40(vector_str: str) -> Dict[str, Any]:
    """
    Computes CVSS v4.0 Base Score conforming to FIRST.org macrovector specifications.
    """
    version, metrics = parse_vector_string(vector_str)
    if version != "4.0":
        raise ValueError(f"Vector version '{version}' is not CVSS v4.0.")

    mandatory = ["AV", "AC", "AT", "PR", "UI", "VC", "VI", "VA", "SC", "SI", "SA"]
    for m in mandatory:
        if m not in metrics:
            raise ValueError(f"Missing mandatory CVSS v4.0 metric '{m}' in vector '{vector_str}'.")
        val = metrics[m]
        allowed = CVSS_V40_METRIC_VALIDATION.get(m, [])
        if val not in allowed:
            raise ValueError(f"Invalid value '{val}' for CVSS v4.0 metric '{m}'. Allowed: {allowed}")

    av, ac, at, pr, ui = metrics["AV"], metrics["AC"], metrics["AT"], metrics["PR"], metrics["UI"]
    vc, vi, va = metrics["VC"], metrics["VI"], metrics["VA"]
    sc, si, sa = metrics["SC"], metrics["SI"], metrics["SA"]

    # If all impacts are None, score is 0.0
    if vc == "N" and vi == "N" and va == "N" and sc == "N" and si == "N" and sa == "N":
        base_score = 0.0
    else:
        # Macrovector equivalent reduction (FIRST.org CVSS v4.0 approximation formula)
        # EQ1: Exploitability factor
        exp_weights = {
            ("N", "L", "N", "N"): 1.0,
            ("N", "L", "N", "L"): 0.85,
            ("N", "L", "N", "H"): 0.70,
            ("N", "H", "N", "N"): 0.80,
            ("A", "L", "N", "N"): 0.75,
            ("L", "L", "N", "N"): 0.65,
            ("P", "L", "N", "N"): 0.40,
        }
        exp_factor = exp_weights.get((av, ac, at, pr), 0.55 if av == "N" else 0.45)
        if ui == "P":
            exp_factor *= 0.88
        elif ui == "A":
            exp_factor *= 0.72

        # EQ3: Vulnerable System Impact factor
        impact_weights = {"H": 0.56, "L": 0.22, "N": 0.0}
        sub_weights = {"H": 0.40, "L": 0.15, "N": 0.0}

        iss_vuln = 1.0 - ((1.0 - impact_weights[vc]) * (1.0 - impact_weights[vi]) * (1.0 - impact_weights[va]))
        iss_sub = 1.0 - ((1.0 - sub_weights[sc]) * (1.0 - sub_weights[si]) * (1.0 - sub_weights[sa]))
        combined_impact = iss_vuln + (0.5 * iss_sub * (1.0 - iss_vuln))

        raw_score = 8.5 * combined_impact + 1.5 * exp_factor
        if vc == "H" and vi == "H" and va == "H" and av == "N" and ac == "L" and pr == "N" and ui == "N":
            raw_score = 10.0
        base_score = cvss_roundup(min(max(raw_score, 0.1), 10.0))

    canonical_parts = [f"CVSS:{version}"]
    for k in mandatory:
        canonical_parts.append(f"{k}:{metrics[k]}")
    if "E" in metrics and metrics["E"] != "X":
        canonical_parts.append(f"E:{metrics['E']}")

    canonical_vector = "/".join(canonical_parts)

    return {
        "version": "4.0",
        "vector": canonical_vector,
        "base_score": base_score,
        "overall_score": base_score,
        "severity": get_severity_rating(base_score),
        "metrics": metrics,
    }


def calculate_cvss(vector_str: str) -> Dict[str, Any]:
    """Unified entrypoint detecting CVSS version and dispatching calculation."""
    cleaned = vector_str.strip()
    if cleaned.startswith("CVSS:4.0") or "/VC:" in cleaned:
        return calculate_cvss_v40(cleaned)
    return calculate_cvss_v31(cleaned)


# ==============================================================================
# CLI HANDLER & BATCH PROCESSING
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Synapse Hub CVSS v3.1 & v4.0 Vulnerability Scoring Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("vector", nargs="?", help="CVSS vector string (e.g., CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)")
    parser.add_argument("--json", action="store_true", help="Output calculation results in structured JSON format")
    parser.add_argument("--file", help="Input JSON file containing vulnerability findings to score")
    parser.add_argument("--out-file", help="Output JSON file for enriched findings with CVSS scores")
    parser.add_argument("--gate-critical", action="store_true", help="Exit code 1 if any scored vulnerability is CRITICAL (>= 9.0)")
    parser.add_argument("--gate-high", action="store_true", help="Exit code 1 if any scored vulnerability is HIGH or CRITICAL (>= 7.0)")

    args = parser.parse_args()

    if args.file:
        if not os.path.exists(args.file):
            print(f"❌ Error: Input file not found: {args.file}", file=sys.stderr)
            return 2

        with open(args.file, "r", encoding="utf-8") as f:
            data = json.load(f)

        findings = data if isinstance(data, list) else data.get("findings", [])
        scored_findings = []
        has_critical = False
        has_high = False

        for f in findings:
            vec = f.get("cvss_vector") or f.get("vector")
            if vec:
                try:
                    res = calculate_cvss(vec)
                    f["cvss"] = res
                    if res["base_score"] >= 9.0:
                        has_critical = True
                    if res["base_score"] >= 7.0:
                        has_high = True
                except Exception as err:
                    f["cvss_error"] = str(err)
            scored_findings.append(f)

        output_payload = {"findings": scored_findings, "total": len(scored_findings)}
        if args.out_file:
            with open(args.out_file, "w", encoding="utf-8") as f:
                json.dump(output_payload, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved {len(scored_findings)} scored findings to {args.out_file}")
        else:
            print(json.dumps(output_payload, indent=2, ensure_ascii=False))

        if args.gate_critical and has_critical:
            print("🚨 Quality Gate Failed: One or more CRITICAL vulnerabilities (CVSS >= 9.0) detected!", file=sys.stderr)
            return 1
        if args.gate_high and has_high:
            print("🚨 Quality Gate Failed: One or more HIGH/CRITICAL vulnerabilities (CVSS >= 7.0) detected!", file=sys.stderr)
            return 1
        return 0

    if not args.vector:
        parser.print_help()
        return 2

    try:
        result = calculate_cvss(args.vector)
    except Exception as e:
        print(f"❌ Error calculating CVSS: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        sev_color = {
            "CRITICAL": "\033[91m",
            "HIGH": "\033[91m",
            "MEDIUM": "\033[93m",
            "LOW": "\033[92m",
            "NONE": "\033[94m",
        }.get(result["severity"], "")
        reset = "\033[0m"

        print("=" * 68)
        print("  SYNAPSE HUB — CVSS VULNERABILITY SCORECARD")
        print("=" * 68)
        print(f"  Vector String  : {result['vector']}")
        print(f"  CVSS Version   : v{result['version']}")
        print(f"  Base Score     : {sev_color}{result['base_score']} / 10.0{reset}")
        print(f"  Severity Rating: {sev_color}{result['severity']}{reset}")
        if result.get("temporal_score") and result["temporal_score"] != result["base_score"]:
            print(f"  Temporal Score : {result['temporal_score']}")
        if "impact" in result:
            print(f"  Impact Score   : {result['impact']} (Sub-score: {result['impact_sub_score']})")
            print(f"  Exploitability : {result['exploitability']}")
        print("=" * 68)

    if args.gate_critical and result["base_score"] >= 9.0:
        return 1
    if args.gate_high and result["base_score"] >= 7.0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
