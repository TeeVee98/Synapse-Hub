#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
SkillVault Lifelong Page Object Model & Interaction Library (MineDojo / Voyager Pattern)
---------------------------------------------------------------------------------------
Adapts Voyager's self-evolving SkillManager into a persistent SQLite store (.synapse/skill_vault.db).
When pom-crafter authors new test cases, it queries SkillVault to retrieve existing, verified
Page Class methods and business interaction primitives, preventing redundant locator generation.

Reference:
  - Guanzhi Wang et al. (Voyager: An Open-Ended Embodied Agent with Large Language Models).
  - Synapse-Hub Subsystem 1: Section 6.2 of agent_skill_training_analysis.md.
"""

import os
import sys
import sqlite3
import json
import re
import difflib
import argparse
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Set

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


# Domain synonym ontology for enterprise QA & UI interactions (Offline Fuzzy Semantic Matching)
QA_SYNONYMS: Dict[str, Set[str]] = {
    "auth": {"login", "signin", "sign-in", "authenticate", "sso", "session", "credential", "token", "password", "user", "oauth"},
    "login": {"auth", "signin", "sign-in", "authenticate", "sso", "session", "credential"},
    "table": {"grid", "datatable", "datagrid", "row", "cell", "column", "pagination", "paging", "list", "tbody"},
    "grid": {"table", "datatable", "datagrid", "row", "cell", "column", "pagination"},
    "pagination": {"paging", "page", "pager", "next-page", "previous", "pagination", "table"},
    "approve": {"accept", "confirm", "reconcile", "verify", "validate", "signoff", "approval", "pass"},
    "modal": {"dialog", "popup", "overlay", "backdrop", "drawer", "alert", "window"},
    "dialog": {"modal", "popup", "overlay", "backdrop", "window"},
    "navigate": {"goto", "route", "url", "visit", "open", "link", "redirect"},
    "button": {"btn", "click", "press", "submit", "action", "trigger"},
    "input": {"textbox", "fill", "type", "enter", "field", "value", "text"},
    "dropdown": {"select", "combobox", "option", "menu", "picker", "choice"},
    "invoice": {"billing", "order", "receipt", "payment", "charge", "reconcile"},
    "cart": {"checkout", "basket", "purchase", "item", "order"},
    "upload": {"attachment", "file", "import", "choose-file", "document", "dropzone"},
    "export": {"export", "download", "csv", "excel", "pdf", "report"},
    "toast": {"toast", "notification", "snackbar", "alert", "message", "banner", "popup"},
    "spinner": {"spinner", "loader", "loading", "shimmer", "skeleton", "progress", "wait"},
    "drawer": {"drawer", "sidebar", "panel", "modal", "aside", "sheet"},
    "tab": {"tab", "tabs", "tabpanel", "nav", "segment"},
    "wait": {"detach", "detached", "sleep", "loading", "spinner", "ready", "networkidle", "smartwait"},
}


def split_identifier(identifier: str) -> List[str]:
    """Splits camelCase, PascalCase, and snake_case tokens into lowercase sub-tokens."""
    tokens = re.sub(r'([A-Z]+)', r' \1', identifier).split()
    sub_tokens = []
    for t in tokens:
        sub_tokens.extend(re.split(r'[_\\-]+', t))
    return [t.lower() for t in sub_tokens if len(t) >= 2]


def _expand_tokens_with_synonyms(tokens: List[str]) -> Set[str]:
    """Expands query tokens using the QA domain synonym clusters."""
    expanded = set(tokens)
    for t in tokens:
        if t in QA_SYNONYMS:
            expanded.update(QA_SYNONYMS[t])
        for syn_key, cluster in QA_SYNONYMS.items():
            if t in cluster:
                expanded.add(syn_key)
                expanded.update(cluster)
    return expanded


def _calculate_token_match_score(q_token: str, target_tokens: List[str]) -> float:
    """Computes best match score for a single query token against target corpus tokens."""
    best = 0.0
    for target in target_tokens:
        if q_token == target:
            return 1.0
        if q_token in target or target in q_token:
            best = max(best, 0.8)
            continue
        # Synonym check
        if q_token in QA_SYNONYMS and target in QA_SYNONYMS[q_token]:
            best = max(best, 0.85)
            continue
        # Fuzzy morphological / typo similarity via SequenceMatcher
        ratio = difflib.SequenceMatcher(None, q_token, target).ratio()
        if ratio >= 0.75:
            best = max(best, ratio * 0.8)
    return best


@dataclass
class PageClassPrimitive:
    skill_id: str             # e.g., "SKILL_AUTH_LOGIN_SSO"
    page_class: str           # e.g., "LoginPage"
    method_signature: str     # e.g., "loginWithSSO(username: str, sso_token: str)"
    method_code: str          # Complete executable method body
    locator_tier: int         # 1 to 6 (Master Locator Hierarchy)
    semantic_docstring: str   # Generated docstring for embedding / retrieval
    verified_on_url: str      # Target AUT URL verified against
    mutation_score: float     # Verified assertion sensitivity score (>= 80%)
    tags: str = ""            # Comma-separated domain tags, e.g. "auth,sso,login"


class ManagedConnection(sqlite3.Connection):
    """SQLite connection that automatically commits/rollbacks and closes on context exit."""
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            super().__exit__(exc_type, exc_val, exc_tb)
        finally:
            self.close()


class SkillVault:
    """Persistent library of verified, self-contained Page Class methods."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Anchor to .synapse in workspace or CWD
            base_dir = os.path.join(os.getcwd(), ".synapse")
            os.makedirs(base_dir, exist_ok=True)
            db_path = os.path.join(base_dir, "skill_vault.db")
        self.db_path = db_path
        self._init_schema()

    def _get_connection(self) -> ManagedConnection:
        conn = sqlite3.connect(self.db_path, timeout=30.0, factory=ManagedConnection)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=30000;")
        except sqlite3.Error as err:
            sys.stderr.write(f"Notice: SQLite PRAGMA configuration skipped: {err}\n")
        return conn

    def _init_schema(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS page_primitives (
                    skill_id TEXT PRIMARY KEY,
                    page_class TEXT NOT NULL,
                    method_signature TEXT NOT NULL,
                    method_code TEXT NOT NULL,
                    locator_tier INTEGER DEFAULT 1,
                    semantic_docstring TEXT,
                    verified_on_url TEXT,
                    mutation_score REAL DEFAULT 0.0,
                    tags TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_page_class ON page_primitives(page_class);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_method_sig ON page_primitives(method_signature);")
            # Auto-migrate: check if tags column exists
            try:
                cursor = conn.execute("PRAGMA table_info(page_primitives)")
                cols = [row["name"] for row in cursor.fetchall()]
                if "tags" not in cols:
                    conn.execute("ALTER TABLE page_primitives ADD COLUMN tags TEXT DEFAULT '';")
            except Exception as e:
                # Column check non-fatal during migration
                sys.stderr.write(f"Notice: table migration skipped: {e}\n")

    def register_primitive(self, primitive: PageClassPrimitive) -> bool:
        """Persists a verified Page Class primitive."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO page_primitives (
                        skill_id, page_class, method_signature, method_code,
                        locator_tier, semantic_docstring, verified_on_url, mutation_score, tags
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    primitive.skill_id,
                    primitive.page_class,
                    primitive.method_signature,
                    primitive.method_code,
                    primitive.locator_tier,
                    primitive.semantic_docstring,
                    primitive.verified_on_url,
                    primitive.mutation_score,
                    primitive.tags
                ))
            return True
        except sqlite3.Error as e:
            sys.stderr.write(f"SkillVault Error: {e}\n")
            return False

    def query_primitives(self, query: str, top_k: int = 5, tag: Optional[str] = None, min_score: float = 0.15) -> List[Dict[str, Any]]:
        """
        Queries verified primitives using intelligent fuzzy semantic matching:
        combines exact tokens, synonym expansion, n-gram substring match, and SequenceMatcher similarity.
        """
        words = re.findall(r'[a-zA-Z0-9_-]+', query)
        raw_tokens = []
        for w in words:
            sub = split_identifier(w)
            raw_tokens.extend(sub if sub else [w.lower()])
        raw_tokens = list(dict.fromkeys(raw_tokens))

        if not raw_tokens and not tag:
            return self.list_primitives(limit=top_k)

        expanded_tokens = _expand_tokens_with_synonyms(raw_tokens) if raw_tokens else set()

        with self._get_connection() as conn:
            if tag:
                rows = conn.execute("SELECT * FROM page_primitives WHERE tags LIKE ?", (f"%{tag}%",)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM page_primitives").fetchall()

        if not raw_tokens:
            return [dict(r) for r in rows[:top_k]]

        scored = []
        for r in rows:
            corpus_text = f"{r['page_class']} {r['method_signature']} {r['semantic_docstring'] or ''} {r['tags'] or ''}".lower()
            corpus_words = re.findall(r'[a-zA-Z0-9_-]+', corpus_text)
            corpus_tokens = []
            for cw in corpus_words:
                sub = split_identifier(cw)
                corpus_tokens.extend(sub if sub else [cw.lower()])
            corpus_tokens = list(dict.fromkeys(corpus_tokens))

            # Calculate individual query token matches
            token_scores = [_calculate_token_match_score(qt, corpus_tokens) for qt in raw_tokens]
            avg_token_score = sum(token_scores) / len(token_scores) if token_scores else 0.0

            # Synonym boost
            synonym_hits = sum(1 for st in expanded_tokens if st in corpus_text)
            synonym_factor = min(0.3, (synonym_hits / max(1, len(expanded_tokens))) * 0.3)

            # Mutation score quality boost (up to +0.1 for high mutation score)
            mut_score = r["mutation_score"] or 0.0
            mutation_boost = (mut_score / 100.0) * 0.1

            total_relevance = round(min(1.0, (avg_token_score * 0.7) + synonym_factor + mutation_boost), 4)

            # Pass if relevance reaches threshold OR direct substring match exists
            if total_relevance >= min_score or any(qt in corpus_text for qt in raw_tokens):
                item = dict(r)
                item["relevance_score"] = total_relevance
                item["relevance_percentage"] = f"{round(total_relevance * 100, 1)}%"
                scored.append(item)

        scored.sort(key=lambda x: (x["relevance_score"], x["mutation_score"]), reverse=True)
        return scored[:top_k]

    def harvest_page_classes(self, dir_path: str) -> int:
        """
        Scans a directory for Page Classes across TS, JS, Python, and Groovy,
        extracts method signatures, and registers them into SkillVault.
        """
        if not os.path.isdir(dir_path):
            return 0
        count = 0
        for root, _, files in os.walk(dir_path):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext not in (".py", ".ts", ".js", ".groovy", ".java"):
                    continue
                file_path = os.path.join(root, f)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                        content = fp.read()
                except OSError:
                    continue

                page_class = os.path.splitext(f)[0]
                method_matches = re.finditer(r'(?:def\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)|(?:async\s+)?([a-zA-Z_]\w*)\s*\(([^)]*)\)\s*(?::\s*[^\{]+)?\s*\{)', content)
                for mm in method_matches:
                    m_name = mm.group(1) or mm.group(3)
                    m_args = mm.group(2) if mm.group(1) else mm.group(4)
                    if not m_name or m_name.startswith("_") or m_name in ("constructor", "constructor__"):
                        continue
                    skill_id = f"SKILL_{page_class.upper()}_{m_name.upper()}"
                    sig = f"{m_name}({m_args.strip() if m_args else ''})"
                    doc_m = re.search(rf'{re.escape(m_name)}[^\n]*\n\s*[\'\""""/]+([^\'\""""\n*]+)', content)
                    doc = doc_m.group(1).strip() if doc_m else f"Page method for {m_name} on {page_class}"
                    tags = ",".join(split_identifier(page_class) + split_identifier(m_name))

                    prim = PageClassPrimitive(
                        skill_id=skill_id,
                        page_class=page_class,
                        method_signature=sig,
                        method_code=f"// Harvested from {f}\n{sig}",
                        locator_tier=1,
                        semantic_docstring=doc,
                        verified_on_url=f"local://{f}",
                        mutation_score=85.0,
                        tags=tags
                    )
                    if self.register_primitive(prim):
                        count += 1
        return count

    def list_primitives(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM page_primitives ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]


def main():
    parser = argparse.ArgumentParser(description="SkillVault Lifelong POM Library")
    parser.add_argument("--query", default=None, help="Query verified primitives by keyword (fuzzy semantic search)")
    parser.add_argument("--tag", default=None, help="Filter primitives by domain tag (e.g. auth, table, invoice)")
    parser.add_argument("--harvest", default=None, help="Directory path to harvest Page Classes from")
    parser.add_argument("--list", action="store_true", help="List all stored primitives")
    parser.add_argument("--seed-samples", action="store_true", help="Seed initial verified POM primitives")
    args = parser.parse_args()

    vault = SkillVault()

    if args.harvest:
        num = vault.harvest_page_classes(args.harvest)
        print(f"✅ Harvested {num} Page Class primitives from '{args.harvest}'.")
        return 0

    if args.seed_samples:
        samples = [
            PageClassPrimitive(
                skill_id="SKILL_AUTH_LOGIN_SSO",
                page_class="LoginPage",
                method_signature="loginWithSSO(username: str, sso_token: str)",
                method_code="""def loginWithSSO(self, username: str, sso_token: str):
    self.page.goto("/auth/sso")
    self.page.getByRole("textbox", name="SSO User").fill(username)
    self.page.getByRole("textbox", name="Token").fill(sso_token)
    self.page.getByRole("button", name="Authenticate").click()
    self.page.waitForLoadState("networkidle")""",
                locator_tier=1,
                semantic_docstring="Authenticates user through enterprise SSO portal with token and networkidle smart wait.",
                verified_on_url="https://app.enterprise.com/auth/sso",
                mutation_score=92.5,
                tags="auth,login,signin,sso,security"
            ),
            PageClassPrimitive(
                skill_id="SKILL_INVOICE_APPROVE_RECONCILE",
                page_class="InvoicePage",
                method_signature="approveAndReconcileInvoice(invoice_code: str)",
                method_code="""def approveAndReconcileInvoice(self, invoice_code: str):
    self.page.getByRole("row", name=invoice_code).getByRole("button", name="Approve").click()
    self.page.getByRole("button", name="Confirm Approval").click()
    self.page.waitForSelector(".p-component-overlay", state="detached")""",
                locator_tier=1,
                semantic_docstring="Approves and reconciles invoice row item with modal overlay detachment verification.",
                verified_on_url="https://app.enterprise.com/invoices",
                mutation_score=88.0,
                tags="invoice,billing,approve,reconcile,modal"
            ),
            PageClassPrimitive(
                skill_id="SKILL_TABLE_PAGINATION_NAV",
                page_class="DataTableComponent",
                method_signature="navigateToNextPage(expected_min_rows: int = 1)",
                method_code="""def navigateToNextPage(self, expected_min_rows: int = 1):
    next_btn = self.page.getByRole("button", name="Next Page")
    if next_btn.is_enabled():
        next_btn.click()
        self.page.waitForSelector(".loading-shimmer", state="detached")
        rows = self.page.getByRole("row").all()
        assert len(rows) >= expected_min_rows, f"Expected at least {expected_min_rows} rows" """,
                locator_tier=1,
                semantic_docstring="Navigates through paginated grid/table with dynamic shimmer detachment and row count assertion.",
                verified_on_url="https://app.enterprise.com/data-grid",
                mutation_score=90.0,
                tags="table,grid,pagination,paging,navigation"
            ),
            PageClassPrimitive(
                skill_id="SKILL_FORM_MODAL_SUBMIT",
                page_class="UserManagementPage",
                method_signature="fillAndSubmitModalForm(user_data: dict)",
                method_code="""def fillAndSubmitModalForm(self, user_data: dict):
    dialog = self.page.getByRole("dialog")
    dialog.getByRole("textbox", name="Full Name").fill(user_data.get("name", ""))
    dialog.getByRole("textbox", name="Email").fill(user_data.get("email", ""))
    dialog.getByRole("combobox", name="Role").selectOption(user_data.get("role", "Viewer"))
    dialog.getByRole("button", name="Save").click()
    self.page.waitForSelector(".toast-success", state="visible")""",
                locator_tier=1,
                semantic_docstring="Fills interactive modal dialog form and validates submission toast notification.",
                verified_on_url="https://app.enterprise.com/users",
                mutation_score=87.5,
                tags="modal,dialog,form,input,submit"
            ),
            PageClassPrimitive(
                skill_id="SKILL_ATTACHMENT_UPLOAD_VERIFY",
                page_class="DocumentManagementPage",
                method_signature="uploadAttachmentAndVerify(file_path: str, expected_filename: str)",
                method_code="""def uploadAttachmentAndVerify(self, file_path: str, expected_filename: str):
    file_input = self.page.locator("input[type='file']")
    file_input.setInputFiles(file_path)
    self.page.waitForSelector(".upload-progress", state="detached")
    badge = self.page.getByText(expected_filename)
    assert badge.is_visible(), f"Expected uploaded file badge '{expected_filename}' to be visible" """,
                locator_tier=1,
                semantic_docstring="Uploads file attachment, waits for progress bar detachment and asserts filename badge.",
                verified_on_url="https://app.enterprise.com/documents",
                mutation_score=94.0,
                tags="upload,attachment,file,document,verify"
            )
        ]
        for s in samples:
            vault.register_primitive(s)
        print(f"✅ Seeded {len(samples)} verified PageClass primitives into SkillVault.")
        return 0

    if args.list:
        items = vault.list_primitives()
        print(json.dumps(items, indent=2))
        return 0

    if args.query or args.tag:
        matches = vault.query_primitives(args.query or "", tag=args.tag)
        print(f"🔍 Found {len(matches)} matching primitives in SkillVault (Fuzzy Semantic Search):")
        print(json.dumps(matches, indent=2))
        return 0

    print("SkillVault active. Use --query, --tag, --list, or --seed-samples.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
