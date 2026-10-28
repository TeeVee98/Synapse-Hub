#!/usr/bin/env python3
"""
Universal Local Semantic Memory Cache & Self-Healing Resolver
-------------------------------------------------------
Provides 100% Offline, Zero-Token diagnostic resolution for known test failures.
Saves solutions directly into an SQLite database (tools/memory_cache.db).
When identical failures occur, returns pre-tested Groovy patches with 0 LLM Tokens.
"""

import sys
import os
import sqlite3
import json
import argparse
import re
import math
from collections import Counter
from datetime import datetime

GLOBAL_DIR = os.path.expanduser("~/.agent_memory")
GLOBAL_DB = os.path.join(GLOBAL_DIR, "global_cache.db")
LOCAL_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory_cache.db")

def resolve_db_path(use_local=False):
    """Returns the SQLite database path. Defaults to Global Central Memory."""
    if use_local:
        return LOCAL_DB
    os.makedirs(GLOBAL_DIR, exist_ok=True)
    return GLOBAL_DB

DB_FILE = resolve_db_path()

SEED_SOLUTIONS = [
    {
        "error_signature": "ElementClickInterceptedException",
        "module_name": "GLOBAL",
        "symptom": "Modal backdrop or PrimeNG overlay (.p-component-overlay) blocks button click.",
        "root_cause": "Angular PrimeNG animation fade-out latency.",
        "groovy_patch": "((JavascriptExecutor) driver).executeScript(\"arguments[0].click();\", element);"
    },
    {
        "error_signature": "Save_Button_Disabled",
        "module_name": "GLOBAL",
        "symptom": "Green Save button [ âœ“ ] or Submit button remains dimmed/disabled.",
        "root_cause": "Angular Reactive Form missing synthetic input/change event or required field empty.",
        "groovy_patch": "WebElement el = findElement(By.cssSelector(\"input[formcontrolname='code']\"));\njsSetInput(el, uniqueCode);"
    },
    {
        "error_signature": "StaleElementReferenceException",
        "module_name": "GLOBAL",
        "symptom": "Element is not attached to the DOM.",
        "root_cause": "Angular re-rendered DOM node after async API response.",
        "groovy_patch": "for (int i = 0; i < 3; i++) {\n    try {\n        findElement(by).click();\n        break;\n    } catch (StaleElementReferenceException e) {\n        sleep(500);\n    }\n}"
    },
    {
        "error_signature": "Duplicate_Code_Error",
        "module_name": "GLOBAL",
        "symptom": "Red toast: 'MÃ£ Ä‘Ã£ tá»“n táº¡i' or 'Dá»¯ liá»‡u Ä‘Ã£ tá»“n táº¡i'.",
        "root_cause": "Hardcoded or non-unique test identifier collided with existing record.",
        "groovy_patch": "String code = BasePage.uniqueCode(\"CCN_\");"
    },
    {
        "error_signature": "GIS_Boundary_Overlap",
        "module_name": "DataMiningPage",
        "symptom": "Alert: 'Pháº¡m vi giá»¯a cÃ¡c khu/cá»¥m khÃ´ng há»£p lá»‡'.",
        "root_cause": "Drawn polygon overlaps previously saved spatial feature.",
        "groovy_patch": "Actions actions = new Actions(driver);\nactions.moveToElement(viewport, -180, -80).click().perform();"
    },
    {
        "error_signature": "PrimeNG_Dropdown_Empty",
        "module_name": "GLOBAL",
        "symptom": "Dropdown item not clicked or panel not visible.",
        "root_cause": "Overlay panel (.p-dropdown-panel) has not rendered when click dispatched.",
        "groovy_patch": "waitForElementVisible(By.cssSelector(\".p-dropdown-panel\"), 5);\nfindElement(By.xpath(\"//li[contains(., '\" + text + \"')]\")).click();"
    },
    {
        "error_signature": "BlockUI_TimeoutException",
        "module_name": "GLOBAL",
        "symptom": "Timeout waiting for table or form interaction.",
        "root_cause": "PrimeNG loading mask (.p-blockui, .p-progress-spinner) still active.",
        "groovy_patch": "waitForElementNotVisible(By.cssSelector(\".p-blockui, .p-progress-spinner\"), 10);"
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

        # Migrate existing solutions from local DB if initializing global DB for the first time
        if DB_FILE == GLOBAL_DB and os.path.exists(LOCAL_DB):
            try:
                local_conn = sqlite3.connect(LOCAL_DB)
                local_conn.row_factory = sqlite3.Row
                rows = local_conn.execute("SELECT * FROM healing_cache").fetchall()
                for r in rows:
                    cursor.execute("""
                        INSERT OR IGNORE INTO healing_cache 
                        (error_signature, module_name, symptom, root_cause, groovy_patch, hit_count)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (r["error_signature"], r["module_name"], r["symptom"], r["root_cause"], r["groovy_patch"], r["hit_count"]))
                conn.commit()
                local_conn.close()
            except Exception:
                pass

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
            # Increment hit count
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

def sync_db():
    """Bidirectional synchronization between Global Central Memory and Local Project Cache."""
    init_db(seed=True)
    
    g_conn = sqlite3.connect(GLOBAL_DB)
    g_conn.row_factory = sqlite3.Row
    l_conn = sqlite3.connect(LOCAL_DB)
    l_conn.row_factory = sqlite3.Row
    
    # 1. Sync Global to Local
    g_rows = g_conn.execute("SELECT * FROM healing_cache").fetchall()
    for r in g_rows:
        l_conn.execute("""
            INSERT INTO healing_cache (error_signature, module_name, symptom, root_cause, groovy_patch, hit_count)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(error_signature, module_name) DO UPDATE SET
                symptom = excluded.symptom,
                root_cause = excluded.root_cause,
                groovy_patch = excluded.groovy_patch
        """, (r["error_signature"], r["module_name"], r["symptom"], r["root_cause"], r["groovy_patch"], r["hit_count"]))
    l_conn.commit()

    # 2. Sync Local to Global
    l_rows = l_conn.execute("SELECT * FROM healing_cache").fetchall()
    for r in l_rows:
        g_conn.execute("""
            INSERT INTO healing_cache (error_signature, module_name, symptom, root_cause, groovy_patch, hit_count)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(error_signature, module_name) DO UPDATE SET
                symptom = excluded.symptom,
                root_cause = excluded.root_cause,
                groovy_patch = excluded.groovy_patch
        """, (r["error_signature"], r["module_name"], r["symptom"], r["root_cause"], r["groovy_patch"], r["hit_count"]))
    g_conn.commit()
    g_conn.close()
    l_conn.close()
    return len(g_rows)

def get_stats():
    init_db(seed=True)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total_solutions, SUM(hit_count) as total_hits FROM healing_cache")
        row = cursor.fetchone()
        total_sol = row["total_solutions"] or 0
        total_hits = row["total_hits"] or 0
        # Estimated tokens saved: ~2,000 tokens per avoided LLM diagnosis
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
    global DB_FILE
    parser = argparse.ArgumentParser(description="DMIT Central Agent Memory & Self-Healing Resolver")
    parser.add_argument("--local", action="store_true", help="Force local project memory_cache.db instead of Global Central Memory")
    subparsers = parser.add_subparsers(dest="command")

    # Query command
    query_parser = subparsers.add_parser("query", help="Query solution for an error (Zero Token)")
    query_parser.add_argument("--error", required=True, help="Error signature or keyword")
    query_parser.add_argument("--module", default="GLOBAL", help="Module or Page Class name")

    # Learn command
    learn_parser = subparsers.add_parser("learn", help="Save new solution into cache")
    learn_parser.add_argument("--error", required=True, help="Error signature")
    learn_parser.add_argument("--module", default="GLOBAL", help="Module or Page Class name")
    learn_parser.add_argument("--symptom", required=True, help="Symptom description")
    learn_parser.add_argument("--cause", required=True, help="Root cause")
    learn_parser.add_argument("--patch", required=True, help="Groovy patch code")

    # Stats command
    subparsers.add_parser("stats", help="View memory cache statistics and token savings")

    # Sync command
    subparsers.add_parser("sync", help="Synchronize Global Central Memory with Local Project Cache")

    # Init command
    subparsers.add_parser("init", help="Initialize and seed database")

    args = parser.parse_args()
    if args.local:
        DB_FILE = resolve_db_path(use_local=True)
    else:
        DB_FILE = resolve_db_path(use_local=False)

    if args.command == "query":
        sol = query_solution(args.error, args.module)
        if sol:
            print("==================================================")
            print(f"âœ… [CACHE HIT - 0 TOKENS] Found pre-tested solution!")
            print(f"Database Scope  : {'LOCAL' if args.local else 'GLOBAL CENTRAL (~/.agent_memory)'}")
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
            print(f"âŒ [CACHE MISS] No cached solution found for: '{args.error}'. Triggering LLM reasoning.")
            sys.exit(1)

    elif args.command == "learn":
        ok = learn_solution(args.error, args.module, args.symptom, args.cause, args.patch)
        if ok:
            print(f"âœ… [MEMORY LEARNED] Solution for '{args.error}' ({args.module}) cached in {'LOCAL' if args.local else 'GLOBAL CENTRAL'} memory.")

    elif args.command == "stats":
        stats = get_stats()
        print("==================================================")
        print(f"ðŸ“Š AGENT MEMORY CACHE STATISTICS ({'LOCAL' if args.local else 'GLOBAL CENTRAL'})")
        print(f"Database Path           : {DB_FILE}")
        print(f"Total Cached Solutions  : {stats['total_solutions']}")
        print(f"Total Cache Hits        : {stats['total_hits']}")
        print(f"Estimated Tokens Saved  : ~{stats['estimated_tokens_saved']:,} tokens")
        print("--------------------------------------------------")
        print("Top Solutions by Hit Count:")
        for s in stats["solutions"]:
            print(f" - [{s['hit_count']} hits] {s['error_signature']} ({s['module_name']})")
        print("==================================================")

    elif args.command == "sync":
        count = sync_db()
        print(f"âœ… [MEMORY SYNC] Bidirectional sync completed ({count} solutions synchronized between Global & Local).")

    elif args.command == "init" or args.command is None:
        init_db(seed=True)
        print(f"âœ… Central Agent Memory initialized at: {DB_FILE}")

if __name__ == "__main__":
    main()
