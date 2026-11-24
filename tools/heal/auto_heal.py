#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Enterprise Closed-Loop Autonomous Test Healer Engine
-----------------------------------------------------
Diagnoses test failures in 0.1s from JUnit XML and terminal logs, queries the
semantic memory cache for proven patches, and orchestrates targeted re-tests.
Dispatched automatically by AI Agents when test runs encounter failures.
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
import re
import json
import argparse

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HUB_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
sys.path.insert(0, SCRIPT_DIR)

import pinpoint_failure
import cache_resolver
import project_state
import heuristic_locator_matcher
import auto_heal_reflexion
from tools.core.macro_cache import MacroCacheEngine
from tools.reasoning.entropy_pruning import EntropyPruner
from tools.reasoning.associative_memory import AssociativeMemory
from typing import Optional, Dict, Any, List, Tuple

_MAX_ERROR_SIGNATURE_CHARS = 400

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def capture_live_aom_snapshot(url: str, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
    """
    Connects headless Playwright to live URL and extracts the Accessibility Object Model (AOM)
    snapshot for semantic locator healing.
    """
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=int(timeout * 1000), wait_until="domcontentloaded")
            snapshot = page.accessibility.snapshot()
            browser.close()
            return snapshot
    except Exception as _err:
        import logging
        logging.getLogger("auto_heal").debug("Playwright snapshot capture failed: %s", _err)
        return None


def _detect_macro_failure_kind(failure_info: Dict[str, Any], err_sig: str) -> Optional[str]:
    """Classifies whether a failure qualifies for Tier 10 zero-token macro repair."""
    cat = str(failure_info.get("category", "")).lower().strip()
    err_type = str(failure_info.get("type", "")).lower().strip()
    sig_lower = str(err_sig).lower()

    if cat == "syntax" or err_type == "syntaxerror" or "syntaxerror" in sig_lower:
        return "syntax"
    if (
        cat == "schema_drift"
        or "schema_drift" in sig_lower
        or "given_args" in failure_info
    ):
        return "schema_drift"
    return None


def _attempt_zero_token_macro_repair(
    target_dir: str,
    failure_info: Dict[str, Any],
    failing_file: str,
    line_num: Any,
    test_name: str,
    err_sig: str,
) -> Optional[Dict[str, Any]]:
    """Checks Tier 10 MacroCacheEngine on syntax or schema-drift failures before reflexion escalation."""
    kind = _detect_macro_failure_kind(failure_info, err_sig)
    if not kind:
        return None

    db_path = failure_info.get("macro_db_path")
    if not db_path:
        db_path = os.path.join(target_dir, ".synapse", "macro_cache.db")
    try:
        macro_engine = MacroCacheEngine(db_path=db_path)
        if kind == "syntax":
            repair_context = failure_info.get("context")
            if repair_context is None and failing_file != "UnknownFile":
                candidate = failing_file if os.path.isabs(failing_file) else os.path.join(target_dir, failing_file)
                if os.path.isfile(candidate):
                    with open(candidate, "r", encoding="utf-8") as cf:
                        repair_context = cf.read()
            if repair_context is None:
                repair_context = failure_info.get("line_text", "")

            syntax_err = SyntaxError(err_sig)
            if str(line_num).isdigit():
                syntax_err.lineno = int(line_num)
            if failure_info.get("line_text"):
                syntax_err.text = str(failure_info["line_text"])
            return macro_engine.execute_zero_token_repair(repair_context, syntax_err)

        repair_context = failure_info.get("context", failure_info.get("given_args", {}))
        error_obj = {
            "category": "schema_drift",
            "tool_name": failure_info.get("tool_name", test_name),
            "given_args": failure_info.get("given_args", {}),
            "expected_schema": failure_info.get("expected_schema", {}),
        }
        return macro_engine.execute_zero_token_repair(repair_context, error_obj)
    except Exception as exc:
        import logging
        logging.getLogger("auto_heal").debug("Tier 10 macro cache lookup failed: %s", exc)
        return {"repaired": False, "tokens_consumed": 0, "error": str(exc)}


def _prune_error_signature(err_sig: str) -> Tuple[str, int]:
    """Compresses error signatures exceeding 400 chars via EntropyPruner."""
    sig = str(err_sig or "")
    if len(sig) <= _MAX_ERROR_SIGNATURE_CHARS:
        return sig, 0
    try:
        compressed, _meta = EntropyPruner.compress(sig)
        pruned = (compressed or "").strip()
        if not pruned:
            pruned = sig[:_MAX_ERROR_SIGNATURE_CHARS]
        elif len(pruned) > _MAX_ERROR_SIGNATURE_CHARS:
            pruned = pruned[:_MAX_ERROR_SIGNATURE_CHARS]
        return pruned, max(0, len(sig) - len(pruned))
    except Exception as exc:
        import logging
        logging.getLogger("auto_heal").debug("EntropyPruner compression failed: %s", exc)
        fallback = sig[:_MAX_ERROR_SIGNATURE_CHARS]
        return fallback, max(0, len(sig) - len(fallback))


def _associative_db_path(target_dir: str) -> str:
    """Resolves the target-scoped AssociativeMemory SQLite database path."""
    return os.path.join(target_dir or HUB_ROOT, ".synapse", "associative_memory.db")


def _build_defect_node_id(err_sig: str) -> str:
    """Builds a deterministic defect entity_id for an error signature."""
    fp = cache_resolver.compute_error_fingerprint("", str(err_sig or "UnknownError"))
    return f"defect:{fp}"


def _query_associative_matches(
    target_dir: str,
    err_sig: str,
    pruned_err_sig: str,
) -> List[Dict[str, Any]]:
    """Queries AssociativeMemory for prior resolved_by fixes without leaking SQLite handles."""
    matches: List[Dict[str, Any]] = []
    try:
        with AssociativeMemory(db_path=_associative_db_path(target_dir)) as mem:
            node_ids = [_build_defect_node_id(err_sig)]
            if pruned_err_sig and pruned_err_sig != err_sig:
                pruned_id = _build_defect_node_id(pruned_err_sig)
                if pruned_id not in node_ids:
                    node_ids.append(pruned_id)

            assocs: List[Dict[str, Any]] = []
            for nid in node_ids:
                assocs = mem.query_associations(nid, min_weight=0.0, limit=5)
                if assocs:
                    break

            for assoc in assocs:
                if assoc.get("relation") != "resolved_by":
                    continue
                fix_node = mem.get_node(assoc["neighbor_id"]) or {}
                attrs = fix_node.get("attributes") or {}
                matches.append(
                    {
                        "entity_id": assoc["neighbor_id"],
                        "relation": assoc["relation"],
                        "weight": assoc["weight"],
                        "successful_fix": attrs.get("successful_fix", ""),
                        "lesson_summary": attrs.get("lesson_summary", ""),
                        "page_context": attrs.get("page_context", ""),
                    }
                )
    except Exception as exc:
        import logging
        logging.getLogger("auto_heal").debug("AssociativeMemory lookup failed: %s", exc)
        return []
    return matches


def diagnose_and_plan_heal(target_dir=HUB_ROOT, junit_xml_path=None, failure_info=None, live_url=None, aom_snapshot=None):
    """
    Parses test failure, checks memory cache, updates project state watchpoints,
    and returns a structured healing plan.
    """
    print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
    print(f"{BOLD}{CYAN}           AUTONOMOUS CLOSED-LOOP TEST HEALING SENTINEL               {RESET}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}")
    print(f"📁 Target Project  : {target_dir}")

    # 1. Live AOM snapshot extraction
    aom_data = aom_snapshot
    if not aom_data and live_url:
        print(f"  {CYAN}🌐 [PLAYWRIGHT CDP] Extracting live AOM snapshot from {live_url}...{RESET}")
        aom_data = capture_live_aom_snapshot(live_url)
        if aom_data:
            print(f"  {GREEN}[AOM EXTRACTED] Live accessibility tree captured successfully.{RESET}")

    # 1b. Pinpoint failure from JUnit XML or logs if not directly provided
    if not failure_info and junit_xml_path and os.path.exists(junit_xml_path):
        failures = getattr(pinpoint_failure, "parse_failures", None) or getattr(pinpoint_failure, "parse_junit_xml", None)
        if failures:
            res = failures(junit_xml_path)
            if res:
                failure_info = res[0]

    if not failure_info:
        # Search for any recent report across Reports/, reports/, test-results/, allure-results/
        latest_report = pinpoint_failure.find_latest_report(target_dir) if hasattr(pinpoint_failure, "find_latest_report") else None
        if latest_report and os.path.exists(latest_report):
            parsed = pinpoint_failure.parse_junit_xml(latest_report)
            if parsed:
                failure_info = parsed[0]
        elif not failure_info:
            for r_cand in ["Reports", "reports", "test-results", "allure-results"]:
                r_dir = os.path.join(target_dir, r_cand)
                if os.path.isdir(r_dir):
                    for root, _, files in os.walk(r_dir):
                        for f in files:
                            if f.endswith(".xml"):
                                parsed = pinpoint_failure.parse_junit_xml(os.path.join(root, f))
                                if parsed:
                                    failure_info = parsed[0]
                                    break
                        if failure_info:
                            break
                if failure_info:
                    break

    if not failure_info:
        print("  [INFO] Zero active JUnit XML failures detected on disk.")
        return {"status": "NO_FAILURE_DETECTED"}

    err_sig = failure_info.get("reason", failure_info.get("message", failure_info.get("error", failure_info.get("type", "UnknownError"))))
    test_name = failure_info.get("tc", failure_info.get("name", failure_info.get("test_name", "UnknownTest")))
    failing_file = failure_info.get("file", "UnknownFile")
    line_num = failure_info.get("line", "?")

    if (failing_file == "UnknownFile" or line_num == "?") and failure_info.get("failed_at"):
        first_loc = failure_info["failed_at"][0]
        if ":" in str(first_loc) and not str(first_loc).startswith("See JUnit"):
            parts = str(first_loc).rsplit(":", 1)
            if failing_file == "UnknownFile":
                failing_file = parts[0]
            if line_num == "?":
                line_num = parts[1]

    print(f"  ❌ Failing Test   : {test_name}")
    print(f"  📍 Source Location: {failing_file}:{line_num}")
    print(f"  ⚠️ Error Signature: {err_sig[:120]}...\n")

    pruned_err_sig, pruned_chars_saved = _prune_error_signature(err_sig)

    # 2. Check Tier 10 MacroCacheEngine before escalating to reflexion / LLM healing
    macro_repair = _attempt_zero_token_macro_repair(
        target_dir=target_dir,
        failure_info=failure_info,
        failing_file=failing_file,
        line_num=line_num,
        test_name=test_name,
        err_sig=err_sig,
    )
    macro_cache_match = bool(macro_repair and macro_repair.get("repaired"))

    # 2b. Query 0-token memory cache & 3-layer heuristic matcher
    print(f"{BOLD}[1/2] Checking 3-Layer Heuristic Matcher & Memory Cache...{RESET}")
    cache_solution = cache_resolver.query_solution(err_sig, threshold=0.35)

    # 2c. Query Episodic Reflexion Memory (Top 2 historical lessons)
    lessons = cache_resolver.query_lessons(f"{test_name} {err_sig}", limit=2)

    # 2d. Query Associative Graph Memory for prior resolved fixes
    associative_matches = _query_associative_matches(target_dir, err_sig, pruned_err_sig)

    plan = {
        "status": "HEALING_PLAN_READY",
        "test_name": test_name,
        "failing_file": failing_file,
        "line": line_num,
        "error_signature": err_sig,
        "pruned_error_signature": pruned_err_sig,
        "pruned_chars_saved": pruned_chars_saved,
        "cache_match": bool(cache_solution),
        "macro_cache_match": macro_cache_match,
        "macro_repair": macro_repair,
        "heuristic_match": None,
        "recommended_patch": None,
        "verbal_reflection": None,
        "episodic_lessons": [les["lesson_summary"] for les in lessons],
        "associative_matches": associative_matches,
        "aom_snapshot_captured": bool(aom_data)
    }

    if aom_data:
        plan["pruned_aom"] = auto_heal_reflexion.prune_aom_tree(aom_data, target_selector=err_sig)

    if macro_cache_match:
        print(
            f"  {GREEN}[TIER 10 MACRO HIT] Zero-token repair ready "
            f"({macro_repair.get('macro_id')}): {macro_repair.get('signature')}{RESET}"
        )
        plan["recommended_patch"] = (
            f"Apply Tier 10 zero-token macro repair ({macro_repair.get('macro_id')}): "
            f"{macro_repair.get('signature')}"
        )
    else:
        # Reflexion Verbal Diagnosis
        healer = auto_heal_reflexion.ClosedLoopHealer(max_trials=3)
        verbal_reflection = healer.generate_reflection(err_sig, "", "")
        plan["verbal_reflection"] = verbal_reflection

        if lessons:
            print(f"  {CYAN}🧠 [EPISODIC REFLEXION] Top Historical Lessons for Context:{RESET}")
            for idx, les in enumerate(lessons, 1):
                print(f"     {idx}. [{les['page_context']}]: {les['lesson_summary']}")
        print(f"  {CYAN}💡 [REFLEXION DIAGNOSIS] {verbal_reflection}{RESET}")

        if cache_solution:
            score_val = cache_solution.get('score') or cache_solution.get('confidence', 1.0)
            fix_val = cache_solution.get('solution') or cache_solution.get('code_patch') or cache_solution.get('recommended_fix', '')
            print(f"  {GREEN}[MATCH] Found cached resolution (Score: {score_val:.2f}):{RESET}")
            print(f"  💡 Prescribed Fix : {fix_val}")
            plan["recommended_patch"] = fix_val
        else:
            # Check if error message contains broken locator pattern
            loc_candidate_m = re.search(r"locator\(['\"]([^'\"]+)['\"]\)|By\.[a-zA-Z]+\(['\"]([^'\"]+)['\"]\)", err_sig)
            if loc_candidate_m:
                broken_loc = loc_candidate_m.group(1) or loc_candidate_m.group(2)
                heuristic_res = heuristic_locator_matcher.HeuristicLocatorMatcher.match(broken_loc, dom_snapshot=aom_data if isinstance(aom_data, list) else [])
                plan["heuristic_match"] = heuristic_res
                if heuristic_res.get("matched"):
                    print(f"  {GREEN}[HEURISTIC L{heuristic_res['layer']}] 0-Token match ({heuristic_res['confidence']*100:.1f}%): {heuristic_res['healed_locator']}{RESET}")
                    plan["recommended_patch"] = f"Update locator to: {heuristic_res['healed_locator']}"
                else:
                    print("  [MISS] Heuristic confidence < 85%. Fallback to Live DOM exploration.")
                    plan["recommended_patch"] = "Inspect element using Playwright Live Explorer and apply resilient locator / smart wait."
            else:
                print("  [MISS] No direct cache match. AI Agent will inspect live DOM/AOM via Playwright.")
                plan["recommended_patch"] = "Inspect element using Playwright Live Explorer and apply resilient locator / smart wait."

    # 3. Anchor watchpoint in PROJECT_STATE.md
    print(f"\n{BOLD}[2/2] Anchoring Watchpoint in PROJECT_STATE.md...{RESET}")
    try:
        project_state.update_state(
            target_dir=target_dir,
            watchpoint=f"{test_name} -> {failing_file}:{line_num}",
            gate_status="HEALING_IN_PROGRESS"
        )
        print("  [OK] Project state watchpoint updated.")
    except Exception as e:
        print(f"  ⚠️ Could not update PROJECT_STATE.md: {e}")

    print(f"{BOLD}{CYAN}======================================================================{RESET}\n")
    return plan


def record_heal_lesson(
    page_context,
    error_signature,
    root_cause,
    failed_attempt,
    successful_fix,
    lesson_summary,
    target_dir=HUB_ROOT,
):
    """Saves a 2-line practical lesson learned into SQLite and AssociativeMemory after successful healing."""
    recorded = cache_resolver.record_lesson(
        page_context=page_context,
        error_signature=error_signature,
        root_cause=root_cause,
        failed_attempt=failed_attempt,
        successful_fix=successful_fix,
        lesson_summary=lesson_summary
    )
    try:
        safe_ctx = cache_resolver.sanitize_text(page_context or "GLOBAL")
        safe_err = cache_resolver.sanitize_text(error_signature or "UnknownError")
        safe_root = cache_resolver.sanitize_text(root_cause or "")
        safe_failed = cache_resolver.sanitize_text(failed_attempt or "")
        safe_fix = cache_resolver.sanitize_text(successful_fix or "")
        safe_summary = cache_resolver.sanitize_text((lesson_summary or "").strip())

        ctx_node_id = f"module:{safe_ctx}"
        err_node_id = _build_defect_node_id(error_signature)
        fix_key = (safe_fix or safe_summary or "unknown_fix").strip()
        fix_node_id = f"fix:{cache_resolver.djb2_hash(fix_key)}"

        with AssociativeMemory(db_path=_associative_db_path(target_dir)) as mem:
            mem.record_node(ctx_node_id, "module", attributes={"page_context": safe_ctx})
            mem.record_node(
                err_node_id,
                "defect",
                attributes={"error_signature": safe_err, "root_cause": safe_root},
            )
            mem.record_node(
                fix_node_id,
                "concept",
                attributes={
                    "successful_fix": safe_fix,
                    "lesson_summary": safe_summary,
                    "failed_attempt": safe_failed,
                    "page_context": safe_ctx,
                },
            )
            mem.record_association(ctx_node_id, err_node_id, "exhibits_failure", weight=1.0)
            mem.record_association(err_node_id, fix_node_id, "resolved_by", weight=1.0)
    except Exception as exc:
        import logging
        logging.getLogger("auto_heal").debug("AssociativeMemory record failed: %s", exc)
    return recorded


def main():
    parser = argparse.ArgumentParser(description="Autonomous Closed-Loop Test Healer")
    parser.add_argument("target", nargs="?", default=os.getcwd(), help="Target project root directory")
    parser.add_argument("--xml", default=None, help="Path to JUnit XML test report")
    parser.add_argument("--record-lesson", default=None, help="Record a 2-line lesson learned after healing")
    parser.add_argument("--context", default="GLOBAL", help="Page context for the recorded lesson")
    parser.add_argument("--error", default="UnknownError", help="Error signature for the recorded lesson")
    parser.add_argument("--fix", default="", help="Successful fix for the recorded lesson")
    parser.add_argument("--reflexion", action="store_true", help="Execute multi-trial reflection loop (K=3)")
    parser.add_argument("--max-trials", type=int, default=3, help="Max trials for reflexion healing loop")
    parser.add_argument("--live-url", default=None, help="Live AUT URL to capture AOM snapshot via headless Playwright")
    parser.add_argument("--aom", default=None, help="Path to pre-captured AOM JSON file")
    args = parser.parse_args()

    aom_snap = None
    if getattr(args, "aom", None) and os.path.exists(args.aom):
        try:
            with open(args.aom, "r", encoding="utf-8") as af:
                aom_snap = json.load(af)
        except Exception as _err:
            import logging
            logging.getLogger("auto_heal").debug("Failed to read AOM snapshot: %s", _err)

    if args.record_lesson:
        ok = record_heal_lesson(
            page_context=args.context,
            error_signature=args.error,
            root_cause="Autonomous Healer Diagnosis",
            failed_attempt="",
            successful_fix=args.fix,
            lesson_summary=args.record_lesson
        )
        if ok:
            print(f"✅ [EPISODIC REFLEXION] Lesson recorded for '{args.context}': {args.record_lesson}")
        return 0

    if args.reflexion:
        healer = auto_heal_reflexion.ClosedLoopHealer(max_trials=args.max_trials)
        reflection = healer.generate_reflection(args.error, "", "")
        print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
        print(f"{BOLD}{CYAN}      MULTI-TRIAL EPISODIC REFLEXION HEALER LOOP (K={args.max_trials})         {RESET}")
        print(f"{BOLD}{CYAN}======================================================================{RESET}")
        print(f"  Target Context : {args.context}")
        print(f"  Error Signature: {args.error}")
        print(f"  Diagnosis (VRL): {reflection}")
        target_dir = os.path.abspath(args.target)
        plan = diagnose_and_plan_heal(target_dir, junit_xml_path=args.xml, live_url=args.live_url, aom_snapshot=aom_snap)
        plan["reflexion"] = {
            "max_trials": args.max_trials,
            "verbal_reflection": reflection,
            "status": "INITIAL_TRIAL_DISPATCHED"
        }
        print(json.dumps(plan, indent=2))
        return 0

    target_dir = os.path.abspath(args.target)
    plan = diagnose_and_plan_heal(target_dir, junit_xml_path=args.xml, live_url=args.live_url, aom_snapshot=aom_snap)
    print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
