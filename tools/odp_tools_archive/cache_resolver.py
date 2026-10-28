#!/usr/bin/env python3
"""
ODP Local Semantic Memory Cache & Self-Healing Resolver
-------------------------------------------------------
Provides 100% Offline, Zero-Token diagnostic resolution for known test failures.
Solutions are stored in an SQLite database (tools/memory_cache.db) which is
AUTO-CREATED AND SEEDED on first run (runtime-generated artifact, not committed).
When identical failures occur, returns pre-tested Groovy patches with 0 LLM Tokens.

Usage:
  python3 tools/cache_resolver.py init
  python3 tools/cache_resolver.py query --error "ElementClickInterceptedException" --module DatasetPage
  python3 tools/cache_resolver.py learn --error <sig> --module <Page> --symptom <s> --cause <c> --patch <groovy>
  python3 tools/cache_resolver.py stats
"""

import sys
import os
import sqlite3
import argparse
import re
import math
from collections import Counter

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory_cache.db")

SEED_SOLUTIONS = [
    {
        "error_signature": "ElementClickInterceptedException",
        "module_name": "GLOBAL",
        "symptom": "Select2 drop-mask or Bootstrap modal backdrop (.select2-drop-mask, .modal-backdrop) blocks button click.",
        "root_cause": "CKAN jQuery overlay animation fade-out latency.",
        "groovy_patch": "BasePage.clickJS(to); // already strips .select2-drop-mask / .modal-backdrop then JS-clicks"
    },
    {
        "error_signature": "Save_Button_Noop",
        "module_name": "GLOBAL",
        "symptom": "Save/Luu button click has no effect or stays disabled.",
        "root_cause": "CKAN required field empty or old text never cleared before typing.",
        "groovy_patch": "BasePage.fillInput(BasePage.x(\"//input[@id='field-title']\"), DataHelper.generateUniqueName(\"Auto\"));"
    },
    {
        "error_signature": "StaleElementReferenceException",
        "module_name": "GLOBAL",
        "symptom": "Element is not attached to the DOM.",
        "root_cause": "CKAN AJAX re-rendered the list node after API response.",
        "groovy_patch": "for (int i = 0; i < 3; i++) {\n    try {\n        driver.findElement(By.xpath(xp)).click();\n        break;\n    } catch (StaleElementReferenceException e) {\n        WebUI.delay(1);\n    }\n}"
    },
    {
        "error_signature": "Duplicate_Name_Error",
        "module_name": "GLOBAL",
        "symptom": "Red alert: 'Ten da ton tai' / entity name collision.",
        "root_cause": "Hardcoded or non-unique test identifier collided with existing record.",
        "groovy_patch": "String name = DataHelper.generateUniqueName(\"Auto_Group\");"
    },
    {
        "error_signature": "Harvest_Duplicate_URL",
        "module_name": "HarvestPage",
        "symptom": "Error: 'URL da ton tai' when creating a new CKAN harvest source.",
        "root_cause": "CKAN keeps soft-deleted source URLs; reusing a previously harvested URL collides.",
        "groovy_patch": "String url = DataHelper.getAvailableHarvestUrl(); // queries harvest_source_list API + unique ?ref= param (ISSUE-AUT-01)"
    },
    {
        "error_signature": "Select2_Option_Not_Applied",
        "module_name": "GLOBAL",
        "symptom": "Select2 dropdown value not selected; option click misses.",
        "root_cause": "Select2 panel not rendered or has search input requiring ENTER dispatch.",
        "groovy_patch": "odp.common.Select2Helper.selectOption(containerXpath, optionText); // handles search-input + plain result lists"
    },
    {
        "error_signature": "Modal_Confirm_Not_Clicked",
        "module_name": "GLOBAL",
        "symptom": "Bootstrap delete-confirm modal stays open after click.",
        "root_cause": "Modal animation/z-index; native Selenium click misses the footer button.",
        "groovy_patch": "boolean ok = BasePage.confirmModal(5); // native click -> WebUI.click -> jQuery trigger fallback"
    },
    {
        "error_signature": "Login_Failed_After_Password_Change",
        "module_name": "LoginPage",
        "symptom": "Login fails on next run after TC_70 changed the password.",
        "root_cause": "New password not synced into Profiles/default.glbl.",
        "groovy_patch": "odp.common.ProfileHelper.updatePasswordInProfile(newPassword); // AGENTS.md section 4 mandatory sync"
    },
    {
        "error_signature": "BeforeUnload_InvalidArgumentException",
        "module_name": "GLOBAL",
        "symptom": "InvalidArgumentException: beforeunload dialog blocks navigation.",
        "root_cause": "Chrome beforeunload dialog raised by CKAN page leaving.",
        "groovy_patch": "BasePage.dismissBeforeUnload(); // auto-invoked inside navigateTo() and safeClick()"
    },
    {
        "error_signature": "TimeoutException_List_Not_Loaded",
        "module_name": "GLOBAL",
        "symptom": "Timeout waiting for dataset list or button.",
        "root_cause": "Slow CKAN API on public portal; page still loading.",
        "groovy_patch": "WebUI.waitForElementVisible(to, GlobalVariable.TIMEOUT_LONG); // forbid blind sleeps"
    }
]

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(seed=True):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS healing_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_signature TEXT NOT NULL,
                module_name TEXT DEFAULT 'GLOBAL',
                symptom TEXT,
                root_cause TEXT,
                groovy_patch TEXT NOT NULL,
                hit_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(error_signature, module_name)
            )
        """)
        conn.commit()

        if seed:
            for s in SEED_SOLUTIONS:
                cursor.execute("""
                    INSERT OR IGNORE INTO healing_cache
                    (error_signature, module_name, symptom, root_cause, groovy_patch)
                    VALUES (?, ?, ?, ?, ?)
                """, (s["error_signature"], s["module_name"], s["symptom"], s["root_cause"], s["groovy_patch"]))
            conn.commit()

def tokenize(text):
    if not text:
        return []
    return re.findall(r'\b\w+\b', text.lower())

def compute_cosine_similarity(text1, text2):
    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)
    if not tokens1 or not tokens2:
        return 0.0
    vec1 = Counter(tokens1)
    vec2 = Counter(tokens2)
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])
    sum1 = sum([val**2 for val in vec1.values()])
    sum2 = sum([val**2 for val in vec2.values()])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)
    if not denominator:
        return 0.0
    return float(numerator) / denominator

def query_solution(error_signature, module_name="GLOBAL", threshold=0.25):
    init_db(seed=True)
    with get_db() as conn:
        cursor = conn.cursor()
        # 1. Exact match with module
        cursor.execute("""
            SELECT * FROM healing_cache
            WHERE error_signature = ? AND module_name = ?
        """, (error_signature, module_name))
        row = cursor.fetchone()
        match_type = "EXACT_MODULE"

        # 2. Fallback to GLOBAL match
        if not row:
            cursor.execute("""
                SELECT * FROM healing_cache
                WHERE error_signature = ? AND module_name = 'GLOBAL'
            """, (error_signature,))
            row = cursor.fetchone()
            match_type = "GLOBAL_MATCH"

        # 3. Fuzzy search on symptom/error
        if not row:
            cursor.execute("""
                SELECT * FROM healing_cache
                WHERE error_signature LIKE ? OR symptom LIKE ?
            """, (f"%{error_signature}%", f"%{error_signature}%"))
            row = cursor.fetchone()
            match_type = "FUZZY_SQL"

        # 4. Offline Semantic Vector Cosine Similarity
        confidence = 1.0
        if not row:
            cursor.execute("SELECT * FROM healing_cache")
            all_rows = cursor.fetchall()
            best_score = 0.0
            best_row = None
            for candidate in all_rows:
                target_corpus = f"{candidate['error_signature']} {candidate['symptom']} {candidate['root_cause']}"
                score = compute_cosine_similarity(error_signature, target_corpus)
                if score > best_score:
                    best_score = score
                    best_row = candidate

            if best_row and best_score >= threshold:
                row = best_row
                match_type = f"SEMANTIC_SIMILARITY ({best_score*100:.1f}%)"
                confidence = best_score

        if row:
            cursor.execute("""
                UPDATE healing_cache
                SET hit_count = hit_count + 1
                WHERE id = ?
            """, (row["id"],))
            conn.commit()
            result = dict(row)
            result["match_type"] = match_type
            result["confidence"] = confidence
            return result
        return None

def learn_solution(error_signature, module_name, symptom, root_cause, groovy_patch):
    init_db(seed=True)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO healing_cache (error_signature, module_name, symptom, root_cause, groovy_patch)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(error_signature, module_name) DO UPDATE SET
                symptom = excluded.symptom,
                root_cause = excluded.root_cause,
                groovy_patch = excluded.groovy_patch
        """, (error_signature, module_name or "GLOBAL", symptom, root_cause, groovy_patch))
        conn.commit()
        return True

def get_stats():
    init_db(seed=True)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total_solutions, SUM(hit_count) as total_hits FROM healing_cache")
        row = cursor.fetchone()
        total_sol = row["total_solutions"] or 0
        total_hits = row["total_hits"] or 0
        saved_tokens = total_hits * 2000

        cursor.execute("SELECT error_signature, module_name, hit_count FROM healing_cache ORDER BY hit_count DESC")
        top_solutions = [dict(r) for r in cursor.fetchall()]

        return {
            "total_solutions": total_sol,
            "total_hits": total_hits,
            "estimated_tokens_saved": saved_tokens,
            "solutions": top_solutions
        }

def main():
    parser = argparse.ArgumentParser(description="ODP Local Memory Cache & Self-Healing Resolver")
    subparsers = parser.add_subparsers(dest="command")

    query_parser = subparsers.add_parser("query", help="Query solution for an error (Zero Token)")
    query_parser.add_argument("--error", required=True, help="Error signature or keyword")
    query_parser.add_argument("--module", default="GLOBAL", help="Module or Page Class name")

    learn_parser = subparsers.add_parser("learn", help="Save new solution into cache")
    learn_parser.add_argument("--error", required=True, help="Error signature")
    learn_parser.add_argument("--module", default="GLOBAL", help="Module or Page Class name")
    learn_parser.add_argument("--symptom", required=True, help="Symptom description")
    learn_parser.add_argument("--cause", required=True, help="Root cause")
    learn_parser.add_argument("--patch", required=True, help="Groovy patch code")

    subparsers.add_parser("stats", help="View memory cache statistics and token savings")
    subparsers.add_parser("init", help="Initialize and seed database")

    args = parser.parse_args()

    if args.command == "query":
        sol = query_solution(args.error, args.module)
        if sol:
            print("==================================================")
            print(f"✅ [CACHE HIT - 0 TOKENS] Found pre-tested solution!")
            print(f"Match Strategy  : {sol.get('match_type', 'EXACT')}")
            print(f"Error Signature : {sol['error_signature']}")
            print(f"Module Scope    : {sol['module_name']}")
            print(f"Root Cause      : {sol['root_cause']}")
            print(f"Hit Count       : {sol['hit_count']}")
            print("--------------------------------------------------")
            print("Groovy Healing Patch:")
            print(sol["groovy_patch"])
            print("==================================================")
        else:
            print(f"❌ [CACHE MISS] No cached solution found for: '{args.error}'. Triggering LLM reasoning.")
            sys.exit(1)

    elif args.command == "learn":
        ok = learn_solution(args.error, args.module, args.symptom, args.cause, args.patch)
        if ok:
            print(f"✅ [MEMORY LEARNED] Solution for '{args.error}' ({args.module}) cached successfully.")

    elif args.command == "stats":
        stats = get_stats()
        print("==================================================")
        print("📊 ODP LOCAL MEMORY CACHE STATISTICS")
        print(f"Total Cached Solutions  : {stats['total_solutions']}")
        print(f"Total Cache Hits        : {stats['total_hits']}")
        print(f"Estimated Tokens Saved  : ~{stats['estimated_tokens_saved']:,} tokens")
        print("--------------------------------------------------")
        print("Top Solutions by Hit Count:")
        for s in stats["solutions"]:
            print(f" - [{s['hit_count']} hits] {s['error_signature']} ({s['module_name']})")
        print("==================================================")

    elif args.command == "init" or args.command is None:
        init_db(seed=True)
        print(f"✅ Memory Cache initialized at: tools/memory_cache.db")

if __name__ == "__main__":
    main()
