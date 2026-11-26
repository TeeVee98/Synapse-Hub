#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Synapse-QA-Bench: Tool Function Calling Benchmark (Gorilla BFCL Pattern)
-----------------------------------------------------------------------
Standardized evaluation benchmark measuring tool selection accuracy, AST argument
validation, and irrelevance detection across Synapse-Hub's tool ecosystem.
Inspired by Shishir Patil et al. (Berkeley Function Calling Leaderboard - BFCL).

Reference:
  - Shishir Patil et al. (Gorilla: Large Language Model Connected with Massive APIs).
  - Synapse-Hub Subsystem 5: Section 6.6 of agent_skill_training_analysis.md.
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
import ast
import re
import json
import math
import argparse
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set, Tuple

from tools.core.bilingual_intent_normalizer import normalize_bilingual_intent


@dataclass(frozen=True)
class ToolBenchEvalDTO:
    overall_score: float
    tool_selection_accuracy: float
    arg_validity_accuracy: float
    irrelevance_detection_rate: float
    passed: bool

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.dirname(SCRIPT_DIR)
HUB_ROOT = os.path.abspath(os.path.join(TOOLS_DIR, ".."))

# Benchmark Evaluation Dataset: (Intent Prompt, Expected Tool, Valid Args, Irrelevant Tools)
BENCHMARK_CASES = [
    {
        "id": "TC-BENCH-01",
        "intent": "Run all 10 Definition-of-Done Quality Gates before merging git commit",
        "expected_tool": "verify_all.py",
        "valid_args": ["--mode", "hub"],
        "irrelevant_tools": ["jtl_analyzer.py", "newman_analyzer.py"]
    },
    {
        "id": "TC-BENCH-02",
        "intent": "Detect flaky tests and calculate quarantine instability scores across runner logs",
        "expected_tool": "flaky_detector.py",
        "valid_args": ["--threshold", "0.20"],
        "irrelevant_tools": ["wcag_audit.py", "author_integrity.py"]
    },
    {
        "id": "TC-BENCH-03",
        "intent": "Parse JUnit XML reports in 0.1s to locate the exact failing line number and exception",
        "expected_tool": "pinpoint_failure.py",
        "valid_args": ["Reports/junit.xml"],
        "irrelevant_tools": ["bump_version.py", "generate_jmx_plan.py"]
    },
    {
        "id": "TC-BENCH-04",
        "intent": "Audit skill descriptions for pairwise routing collisions using offline TF-IDF cosine similarity",
        "expected_tool": "skill_collision_guard.py",
        "valid_args": ["--dir", "skills", "--threshold", "0.75"],
        "irrelevant_tools": ["micro_mutator.py", "network_mock_shield.py"]
    },
    {
        "id": "TC-BENCH-05",
        "intent": "Retrieve verified Page Class interaction primitives from lifelong SQLite storage",
        "expected_tool": "skill_vault.py",
        "valid_args": ["--query", "login SSO"],
        "irrelevant_tools": ["debt_harvester.py", "ci_healing_hook.py"]
    },
    {
        "id": "TC-BENCH-06",
        "intent": "Block catastrophic destructive commands (Delete All, Drop Database) before browser execution",
        "expected_tool": "safety_firewall.py",
        "valid_args": ["--dry-run", "--code", "page.click('#btn-delete')"],
        "irrelevant_tools": ["export_postman_collection.py", "trace_data_flow.py"]
    },
    {
        "id": "TC-BENCH-07",
        "intent": "Transpile test cases bidirectionally between Java, TypeScript, and Groovy with zero tokens",
        "expected_tool": "omni_transpiler.py",
        "valid_args": ["tests/sample_test.ts", "--to", "groovy"],
        "irrelevant_tools": ["flaky_detector.py", "wcag_audit.py"]
    },
    {
        "id": "TC-BENCH-08",
        "intent": "Evaluate assertion sensitivity against injected AST mutants and enforce min score 80%",
        "expected_tool": "micro_mutator.py",
        "valid_args": ["tests/", "--min-score", "80.0"],
        "irrelevant_tools": ["auth_session_and_cookie_manager", "mcp_server.py"]
    },
    {
        "id": "TC-BENCH-09",
        "intent": "Deploy a Kubernetes Helm chart to an AWS EKS cluster with Istio service mesh",
        "expected_tool": "",
        "valid_args": [],
        "irrelevant_tools": ["verify_all.py", "flaky_detector.py", "safety_firewall.py"]
    },
    {
        "id": "TC-BENCH-10",
        "intent": "Code-sign an iOS Xcode IPA archive with Apple provisioning profile and upload to TestFlight",
        "expected_tool": "",
        "valid_args": [],
        "irrelevant_tools": ["omni_transpiler.py", "micro_mutator.py", "pinpoint_failure.py"]
    }
]

_BENCH_STOPWORDS = {
    "the", "and", "for", "with", "from", "into", "that", "this", "all", "run",
    "check", "file", "files", "tool", "tools", "python", "script", "scripts",
    "using", "across", "before", "between", "against", "enterprise", "synapse",
    "hub", "cli", "json", "code", "report", "reports", "test", "tests", "are",
    "not", "can", "will", "has", "have", "must", "only", "via", "per",
    "to", "in", "on", "of", "is", "at", "by", "or", "it", "as", "be", "no",
    "so", "up", "if", "an",
}


def _tokenize_for_idf(text: str) -> Set[str]:
    """Extracts normalized alphanumeric and underscore-split tokens for IDF scoring."""
    raw_tokens = re.findall(r"[a-z0-9_]{2,}", text.lower())
    out: Set[str] = set()
    for tok in raw_tokens:
        parts = [tok] + ([p for p in tok.split("_") if len(p) >= 2] if "_" in tok else [])
        for p in parts:
            if p in _BENCH_STOPWORDS:
                continue
            out.add(p)
            if len(p) > 6 and p.endswith("ing"):
                out.add(p[:-3])
            elif len(p) > 5 and p.endswith("ers"):
                out.add(p[:-3])
            elif len(p) > 5 and p.endswith("er"):
                out.add(p[:-2])
            elif len(p) > 6 and p.endswith("e"):
                out.add(p[:-1])
            elif len(p) > 4 and p.endswith("s"):
                out.add(p[:-1])
    return out


_ACTION_ROLE_MAP: Dict[str, Tuple[str, ...]] = {
    "transpile": ("transpiler",),
    "emit": ("emitter",),
    "parse": ("parser",),
    "mutate": ("mutator",),
    "detect": ("detector",),
    "audit": ("auditor", "audit"),
    "scan": ("scanner",),
    "validate": ("validator",),
    "lint": ("linter",),
    "analyze": ("analyzer",),
    "generate": ("generator",),
    "export": ("exporter",),
    "convert": ("converter",),
    "profile": ("profiler",),
    "heal": ("healer", "heal"),
    "shard": ("sharder",),
    "slice": ("slicer",),
    "correlate": ("correlator",),
    "harvest": ("harvester",),
}

_NON_ASCII_WORD_RE = re.compile(r"\S*[^\x00-\x7F]\S*")


def _extract_bilingual_clean_intent(intent: str) -> str:
    """Normalizes bilingual intent while stripping non-ASCII fragments so Vietnamese accents do not dilute IDF."""
    norm_dto = normalize_bilingual_intent(intent or "")
    if not norm_dto.has_vietnamese:
        return norm_dto.canonical_text
    # Keep pure-ASCII technical words from raw prompt (e.g. Java, TypeScript, Groovy, OpenAPI)
    # plus canonical English tokens produced by the bilingual normalizer.
    ascii_only_raw = _NON_ASCII_WORD_RE.sub(" ", norm_dto.raw_text)
    ascii_raw_words = [
        w for w in re.findall(r"[a-zA-Z0-9_]{2,}", ascii_only_raw.lower())
        if w not in {"va", "cho", "voi", "cua", "cac", "trong", "giua", "khong", "ton", "tu", "den"}
    ]
    # Also include normalized English tokens that do not come from raw diacritic-split fragments
    clean_raw_set = set(ascii_raw_words)
    raw_fragment_set = set(re.findall(r"[a-z0-9_]{2,}", norm_dto.raw_text.lower())) - clean_raw_set
    canonical_clean = [tok for tok in norm_dto.canonical_tokens if tok not in raw_fragment_set]
    merged: List[str] = []
    seen: Set[str] = set()
    for w in ascii_raw_words + canonical_clean:
        if w not in seen:
            seen.add(w)
            merged.append(w)
    return " ".join(merged)


def score_action_aligned_tool_candidates(
    intent: str,
    candidates: List[str],
    abstain_threshold: float = 0.25,
    corpus_docs: Optional[Dict[str, str]] = None,
) -> str:
    """Resolves open-pool CLI tools with bilingual normalization and verb-to-agent-noun alignment (transpile -> transpiler)."""
    clean_intent = _extract_bilingual_clean_intent(intent)
    q_tokens = _tokenize_for_idf(clean_intent)
    if not q_tokens or not candidates:
        return ""

    raw_q_words = set(re.findall(r"[a-z0-9]+", clean_intent.lower()))
    target_roles: Set[str] = set()
    for verb, roles in _ACTION_ROLE_MAP.items():
        if verb in raw_q_words:
            target_roles.update(roles)
        for role in roles:
            if role in raw_q_words:
                target_roles.add(role)

    docs: Dict[str, Set[str]] = {}
    df: Dict[str, int] = {}
    for tool_name in candidates:
        if not tool_name:
            continue
        if corpus_docs and tool_name in corpus_docs:
            doc_text = corpus_docs[tool_name]
        else:
            stem = tool_name[:-3] if tool_name.endswith(".py") else tool_name
            doc_text = f"{stem} {stem.replace('_', ' ')}"
        tset = _tokenize_for_idf(doc_text)
        docs[tool_name] = tset
        for tok in tset:
            df[tok] = df.get(tok, 0) + 1

    if not docs:
        return ""

    num_docs = len(docs)
    idf: Dict[str, float] = {
        tok: math.log((num_docs + 1.0) / (df.get(tok, 0) + 1.0)) + 1.0
        for tok in q_tokens
    }
    total_q_idf = sum(idf.values())
    if total_q_idf <= 0.0:
        return ""

    best_tool = ""
    best_recall = 0.0
    best_rank_score = 0.0

    for tool_name, d_tokens in docs.items():
        matched = [t for t in q_tokens if t in d_tokens]
        if not matched:
            continue
        recall = sum(idf[t] for t in matched) / total_q_idf
        # Require at least 2 distinct matched domain tokens and minimum raw query coverage
        raw_coverage = len(matched) / max(1, len(q_tokens))
        if len(q_tokens) >= 4 and (len(matched) < 2 or raw_coverage < 0.28):
            continue
        stem = (tool_name[:-3] if tool_name.endswith(".py") else tool_name).lower()
        stem_space = stem.replace("_", " ")
        stem_tokens = _tokenize_for_idf(stem_space)
        stem_parts = {p for p in stem.split("_") if len(p) >= 2}
        stem_bonus = 0.15 * (len(q_tokens & stem_tokens) / max(1, len(q_tokens)))
        role_bonus = 0.35 if (target_roles and (stem_parts & target_roles)) else 0.0
        rank_score = recall + stem_bonus + role_bonus
        if rank_score > best_rank_score:
            best_rank_score = rank_score
            best_recall = recall
            best_tool = tool_name

    return best_tool if best_recall >= abstain_threshold else ""


def score_open_pool_candidates(
    intent: str,
    candidates: List[str],
    abstain_threshold: float = 0.18,
    corpus_docs: Optional[Dict[str, str]] = None,
) -> str:
    """Scores candidates using IDF-weighted token recall with action-role alignment and abstains ('') below threshold."""
    return score_action_aligned_tool_candidates(
        intent,
        candidates,
        abstain_threshold=abstain_threshold,
        corpus_docs=corpus_docs,
    )


class SynapseQABench:
    """Evaluates agent tool-calling capabilities against standardized QA benchmark cases."""

    def __init__(self, cases: Optional[List[Dict[str, Any]]] = None):
        self.cases = cases or BENCHMARK_CASES
        self._schema_tools = self._load_tools_schema()
        self._catalog_tools = self._load_tools_catalog()
        self._open_pool_candidates = self._build_open_pool_candidates()
        self._corpus_docs_cache: Optional[Dict[str, str]] = None

    @staticmethod
    def _load_tools_schema() -> Dict[str, Any]:
        schema_path = os.path.join(TOOLS_DIR, "tools_schema.json")
        if not os.path.exists(schema_path):
            return {}
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                return json.load(f).get("tools", {})
        except Exception:
            return {}

    @staticmethod
    def _load_tools_catalog() -> Dict[str, Dict[str, Any]]:
        catalog_path = os.path.join(TOOLS_DIR, "TOOL_CATALOG.json")
        if not os.path.exists(catalog_path):
            return {}
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                entries = json.load(f).get("tools", [])
            catalog: Dict[str, Dict[str, Any]] = {}
            for entry in entries:
                if isinstance(entry, dict) and entry.get("file"):
                    bname = os.path.basename(str(entry["file"]))
                    catalog[bname] = entry
            return catalog
        except Exception:
            return {}

    def _build_open_pool_candidates(self) -> List[str]:
        pool: Set[str] = set(self._catalog_tools.keys())
        for stem, meta in self._schema_tools.items():
            if isinstance(meta, dict) and meta.get("path"):
                pool.add(os.path.basename(str(meta["path"])))
            else:
                pool.add(f"{stem}.py")
        for case in self.cases:
            exp = str(case.get("expected_tool", "")).strip()
            if exp:
                pool.add(exp)
            for irr in case.get("irrelevant_tools", []):
                if irr:
                    pool.add(str(irr))
        return sorted(pool)

    def _resolve_tool_file(self, tool_name: str) -> Optional[str]:
        if not tool_name:
            return None
        cat_entry = self._catalog_tools.get(tool_name)
        if cat_entry and cat_entry.get("file"):
            rel_path = os.path.join(HUB_ROOT, str(cat_entry["file"]))
            if os.path.exists(rel_path):
                return rel_path
        try:
            import tools
            resolved = tools.resolve_tool_path(tool_name)
            if resolved and os.path.exists(resolved):
                return resolved
        except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
            pass
        for base in (TOOLS_DIR, SCRIPT_DIR):
            candidate = os.path.join(base, tool_name)
            if os.path.exists(candidate):
                return candidate
        return None

    @staticmethod
    def _extract_argparse_flags(tool_path: str) -> Set[str]:
        """Extracts defined CLI option flags from Python tool AST add_argument calls."""
        flags: Set[str] = set()
        try:
            with open(tool_path, "r", encoding="utf-8", errors="replace") as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "add_argument"
                ):
                    for arg in node.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.startswith("-"):
                            flags.add(arg.value)
        except (OSError, SyntaxError) as exc:
            sys.stderr.write(f"[SynapseQABench] AST parse skipped for {tool_path}: {exc}\n")
        return flags

    def _validate_args_ast(self, tool_name: str, tool_path: Optional[str], valid_args: List[Any]) -> Tuple[bool, List[str]]:
        """Validates CLI argument types and verifies every flag against tool AST argparse / schema."""
        if not tool_path or not all(isinstance(a, str) for a in valid_args):
            return False, ["tool_missing_or_non_str_args"]
        defined_flags = self._extract_argparse_flags(tool_path)
        stem = tool_name[:-3] if tool_name.endswith(".py") else tool_name
        schema_args = self._schema_tools.get(stem, {}).get("args", {})
        if isinstance(schema_args, dict):
            defined_flags.update(k for k in schema_args.keys() if k.startswith("-"))
        requested_flags = [a for a in valid_args if a.startswith("-")]
        if not defined_flags:
            return len(requested_flags) == 0, requested_flags
        missing_flags = [fl for fl in requested_flags if fl not in defined_flags]
        return len(missing_flags) == 0, missing_flags

    def _build_corpus_docs(self, candidates: List[str]) -> Dict[str, str]:
        if self._corpus_docs_cache is not None and all(c in self._corpus_docs_cache for c in candidates if c):
            return self._corpus_docs_cache
        docs: Dict[str, str] = dict(self._corpus_docs_cache or {})
        for tool_name in candidates:
            if not tool_name or tool_name in docs:
                continue
            stem = tool_name[:-3] if tool_name.endswith(".py") else tool_name
            doc_parts = [stem.replace("_", " "), stem.replace("_", " ")]
            cat_entry = self._catalog_tools.get(tool_name, {})
            if isinstance(cat_entry, dict):
                doc_parts.append(str(cat_entry.get("description", "")))
                doc_parts.append(str(cat_entry.get("category", "")))
            schema_entry = self._schema_tools.get(stem, {})
            if isinstance(schema_entry, dict):
                doc_parts.append(str(schema_entry.get("summary", "")))
                args_meta = schema_entry.get("args", {})
                if isinstance(args_meta, dict):
                    for a_name, a_info in args_meta.items():
                        doc_parts.append(str(a_name))
                        if isinstance(a_info, dict):
                            doc_parts.append(str(a_info.get("help", "")))
            resolved = self._resolve_tool_file(tool_name)
            if resolved and resolved.endswith(".py"):
                try:
                    with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                        src = f.read()
                    tree = ast.parse(src)
                    mod_doc = ast.get_docstring(tree)
                    if mod_doc:
                        doc_parts.append(mod_doc)
                    else:
                        doc_parts.append(src[:600])
                except (OSError, SyntaxError) as exc:
                    sys.stderr.write(f"[SynapseQABench] Failed to read {resolved}: {exc}\n")
            docs[tool_name] = " ".join(doc_parts)
        self._corpus_docs_cache = docs
        return docs

    def _default_tool_resolver(self, intent: str, candidates: List[str]) -> str:
        """Deterministic IDF-weighted resolver scoring candidate tools with action-role alignment and abstention threshold."""
        corpus_docs = self._build_corpus_docs(candidates)
        return score_action_aligned_tool_candidates(intent, candidates, abstain_threshold=0.25, corpus_docs=corpus_docs)

    def run_benchmark(self, tool_resolver_fn=None) -> Dict[str, Any]:
        """
        Runs the benchmark suite using either a custom resolver or the built-in
        open-pool IDF docstring/catalog/schema resolver and AST argparse flag validation.
        """
        total = len(self.cases)
        correct_selections = 0
        valid_args_count = 0
        irrelevance_detected = 0

        details = []
        open_pool = self._open_pool_candidates

        for case in self.cases:
            expected_tool = str(case.get("expected_tool", "")).strip()
            if open_pool:
                candidates = open_pool
            else:
                candidates = [t for t in ([expected_tool] + [str(t) for t in case.get("irrelevant_tools", [])]) if t]

            if tool_resolver_fn is None:
                selected_tool = self._default_tool_resolver(case["intent"], candidates)
            else:
                selected_tool = tool_resolver_fn(case["intent"])

            is_abstention_case = (expected_tool == "")
            is_tool_correct = (selected_tool == expected_tool)
            if is_tool_correct:
                correct_selections += 1

            if is_abstention_case:
                tool_exists = True
                args_valid = (selected_tool == "") and (len(case.get("valid_args", [])) == 0)
                missing_flags = [] if args_valid else ["expected_abstention"]
                irrelevant_check = (selected_tool == "")
            else:
                expected_path = self._resolve_tool_file(expected_tool)
                if not selected_tool:
                    tool_exists = bool(expected_path and os.path.exists(expected_path))
                    args_valid, missing_flags = False, ["no_tool_selected"]
                else:
                    selected_path = self._resolve_tool_file(selected_tool)
                    tool_exists = bool(selected_path and os.path.exists(selected_path))
                    args_valid, missing_flags = self._validate_args_ast(
                        selected_tool,
                        selected_path,
                        case.get("valid_args", []),
                    )
                irrelevant_check = not any(selected_tool == irr for irr in case.get("irrelevant_tools", []))

            if args_valid:
                valid_args_count += 1
            if irrelevant_check:
                irrelevance_detected += 1

            details.append({
                "id": case["id"],
                "intent": case["intent"],
                "expected": expected_tool,
                "selected": selected_tool,
                "tool_matched": is_tool_correct,
                "args_valid": args_valid,
                "missing_ast_flags": missing_flags,
                "tool_exists_on_disk": tool_exists
            })

        selection_acc = round((correct_selections / total) * 100.0, 2)
        arg_validity_acc = round((valid_args_count / total) * 100.0, 2)
        irrelevance_acc = round((irrelevance_detected / total) * 100.0, 2)
        overall_score = round((selection_acc * 0.5 + arg_validity_acc * 0.3 + irrelevance_acc * 0.2), 2)

        return {
            "candidate_pool_size": len(open_pool),
            "total_cases": total,
            "overall_score": overall_score,
            "tool_selection_accuracy": selection_acc,
            "arg_validity_accuracy": arg_validity_acc,
            "irrelevance_detection_rate": irrelevance_acc,
            "passed": overall_score >= 85.0,
            "details": details
        }


def main():
    parser = argparse.ArgumentParser(description="Synapse-QA-Bench Tool Function Calling Benchmark")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    bench = SynapseQABench()
    report = bench.run_benchmark()

    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if report["passed"] else 1

    print("\n" + "=" * 70)
    print("  SYNAPSE-QA-BENCH: TOOL FUNCTION CALLING BENCHMARK (GORILLA BFCL PATTERN)")
    print("=" * 70)
    print(f"Candidate Tool Pool Size     : {report['candidate_pool_size']} tools")
    print(f"Total Benchmark Test Cases   : {report['total_cases']}")
    print(f"Tool Selection Accuracy (F1) : {report['tool_selection_accuracy']}%")
    print(f"AST Argument Validity Rate   : {report['arg_validity_accuracy']}%")
    print(f"Irrelevance Detection Rate   : {report['irrelevance_detection_rate']}%")
    print("-" * 70)
    print(f"Overall Benchmark Score (BFCL): {report['overall_score']}%")
    print(f"Status                       : {'✅ PASSED (>= 85.0%)' if report['passed'] else '❌ FAILED'}")
    print("=" * 70 + "\n")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
