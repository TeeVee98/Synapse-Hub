#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/core/macro_cache.py — Tier 10 Semantic Trajectory & Macro Caching Engine
-----------------------------------------------------------------------------
Zero-token cross-session repair of recurring syntax errors, schema drifts,
and type mismatches via parameterized macros stored in SQLite WAL.
"""

from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
from dataclasses import dataclass
import difflib
import hashlib
import json
import logging
import os
import re
import sqlite3
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("synapse.core.macro_cache")

# Secret patterns for scrubbing credentials from cached contexts and params
SECRET_PATTERNS = [
    re.compile(
        r'["\']?(?:password|passwd|pwd|secret|apiKey|api_key|token|bearer)["\']?\s*[:=]\s*["\']?([^"\'\s,;]{8,})["\']?',
        re.IGNORECASE,
    ),
    re.compile(r"Bearer\s+([a-zA-Z0-9_\-\.]{15,})", re.IGNORECASE),
    re.compile(r"-----BEGIN (?:RSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA )?PRIVATE KEY-----"),
]


def scrub_secrets(text: str) -> str:
    """Scrubs sensitive credentials, tokens, and private keys from strings."""
    if not isinstance(text, str):
        return text
    scrubbed = text
    for pat in SECRET_PATTERNS:
        scrubbed = pat.sub("[REDACTED_SECRET]", scrubbed)
    return scrubbed


def scrub_data_dict(data: Any) -> Any:
    """Recursively scrub secrets from nested dicts, lists, or strings."""
    if isinstance(data, str):
        return scrub_secrets(data)
    elif isinstance(data, dict):
        return {k: scrub_data_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [scrub_data_dict(item) for item in data]
    return data


class ASTErrorSignatureExtractor:
    """Extracts deterministic canonical signatures for syntax errors, schema drift, and type mismatches."""

    @staticmethod
    def extract_from_syntax_error(err: SyntaxError, source_code: str) -> Dict[str, Any]:
        """
        Extracts canonical AST error signature from SyntaxError.
        Detects missing colons, unmatched delimiters, unclosed blocks/strings.
        """
        line_no = err.lineno or 1
        offset = err.offset or 0
        err_msg = str(err.msg or "").strip().lower()

        lines = source_code.splitlines() if source_code else []
        line_text = lines[line_no - 1] if 0 <= line_no - 1 < len(lines) else (err.text or "").strip()
        stripped_line = line_text.strip()

        # 1. Detect missing colon on statement headers
        colon_kw_match = re.match(
            r"^(?:async\s+)?(def|class|if|elif|else|for|while|try|except|finally|with|match|case)\b",
            stripped_line,
        )
        if colon_kw_match and not stripped_line.endswith(":"):
            stmt_type = colon_kw_match.group(1)
            sig = f"SYNTAX:MISSING_COLON:{stmt_type}"
            return {
                "category": "syntax",
                "error_type": "SyntaxError",
                "signature": sig,
                "line": line_no,
                "offset": offset,
                "details": {
                    "statement_type": stmt_type,
                    "line_text": line_text,
                    "line_no": line_no,
                    "missing": ":",
                },
            }
        if "expected ':'" in err_msg or "colon" in err_msg:
            stmt_type = colon_kw_match.group(1) if colon_kw_match else "statement"
            return {
                "category": "syntax",
                "error_type": "SyntaxError",
                "signature": f"SYNTAX:MISSING_COLON:{stmt_type}",
                "line": line_no,
                "offset": offset,
                "details": {
                    "statement_type": stmt_type,
                    "line_text": line_text,
                    "line_no": line_no,
                    "missing": ":",
                },
            }

        # 2. Detect unmatched or unclosed delimiters
        unmatched_match = re.search(
            r"closing parenthesis '([)\]}])' does not match opening parenthesis '([(\[{])'|unmatched '([)\]}])'",
            err_msg,
        )
        if unmatched_match:
            delim = unmatched_match.group(1) or unmatched_match.group(3) or ")"
            return {
                "category": "syntax",
                "error_type": "SyntaxError",
                "signature": f"SYNTAX:UNMATCHED_DELIMITER:{delim}",
                "line": line_no,
                "offset": offset,
                "details": {
                    "delimiter": delim,
                    "line_text": line_text,
                    "line_no": line_no,
                },
            }

        if "was never closed" in err_msg or "unexpected eof" in err_msg:
            delim_match = re.search(r"'([(\[{'\"])' was never closed", err_msg)
            delim = delim_match.group(1) if delim_match else "block"
            return {
                "category": "syntax",
                "error_type": "SyntaxError",
                "signature": f"SYNTAX:UNCLOSED_BLOCK:{delim}",
                "line": line_no,
                "offset": offset,
                "details": {
                    "delimiter": delim,
                    "line_text": line_text,
                    "line_no": line_no,
                },
            }

        # Fallback generic syntax error
        clean_msg = re.sub(r"[^a-zA-Z0-9_]+", "_", err_msg).strip("_")
        return {
            "category": "syntax",
            "error_type": "SyntaxError",
            "signature": f"SYNTAX:INVALID_SYNTAX:{clean_msg[:32]}",
            "line": line_no,
            "offset": offset,
            "details": {
                "message": err_msg,
                "line_text": line_text,
                "line_no": line_no,
            },
        }

    @staticmethod
    def extract_from_schema_drift(tool_name: str, given_args: dict, expected_schema: dict) -> Dict[str, Any]:
        """
        Extracts canonical error signature when tool arguments drift from expected schema.
        Detects renamed params, missing required params, unknown extra params.
        """
        properties: Dict[str, Any] = {}
        required: List[str] = []
        if isinstance(expected_schema, dict):
            if "properties" in expected_schema and isinstance(expected_schema["properties"], dict):
                properties = expected_schema["properties"]
            else:
                properties = {
                    k: v
                    for k, v in expected_schema.items()
                    if k not in ("type", "required", "title", "description")
                }
            required = expected_schema.get("required", [])

        expected_keys = list(properties.keys())
        given_keys = list(given_args.keys()) if isinstance(given_args, dict) else []

        # Check for renamed parameters
        renamed: List[Tuple[str, str]] = []
        for g_k in given_keys:
            if g_k not in expected_keys:
                g_norm = g_k.replace("_", "").replace("-", "").lower()
                best_match = None
                best_ratio = 0.0
                for e_k in expected_keys:
                    e_norm = e_k.replace("_", "").replace("-", "").lower()
                    if g_norm == e_norm:
                        best_match = e_k
                        best_ratio = 1.0
                        break
                    ratio = difflib.SequenceMatcher(None, g_k.lower(), e_k.lower()).ratio()
                    if ratio > best_ratio and ratio >= 0.7:
                        best_ratio = ratio
                        best_match = e_k
                if best_match and best_match not in given_keys:
                    renamed.append((g_k, best_match))

        if renamed:
            old_k, new_k = renamed[0]
            sig = f"SCHEMA:RENAMED_PARAM:{tool_name}:{old_k}->{new_k}"
            return {
                "category": "schema_drift",
                "error_type": "SchemaDriftError",
                "signature": sig,
                "tool_name": tool_name,
                "details": {
                    "old_key": old_k,
                    "new_key": new_k,
                    "tool_name": tool_name,
                    "all_renamed": renamed,
                },
            }

        # Check for missing required params
        missing = [r for r in required if r not in given_keys]
        if missing:
            sig = f"SCHEMA:MISSING_REQUIRED:{tool_name}:{missing[0]}"
            return {
                "category": "schema_drift",
                "error_type": "SchemaDriftError",
                "signature": sig,
                "tool_name": tool_name,
                "details": {
                    "missing_param": missing[0],
                    "all_missing": missing,
                    "tool_name": tool_name,
                },
            }

        # Check for extra unknown params
        extra = [g for g in given_keys if g not in expected_keys]
        if extra:
            sig = f"SCHEMA:EXTRA_PARAM:{tool_name}:{extra[0]}"
            return {
                "category": "schema_drift",
                "error_type": "SchemaDriftError",
                "signature": sig,
                "tool_name": tool_name,
                "details": {
                    "extra_param": extra[0],
                    "all_extra": extra,
                    "tool_name": tool_name,
                },
            }

        return {
            "category": "schema_drift",
            "error_type": "SchemaDriftError",
            "signature": f"SCHEMA:DRIFT:{tool_name}:UNKNOWN",
            "tool_name": tool_name,
            "details": {"given_keys": given_keys, "expected_keys": expected_keys},
        }

    @staticmethod
    def extract_from_type_error(err: TypeError, context_info: dict) -> Dict[str, Any]:
        """
        Extracts canonical error signature from TypeError and context information.
        Detects string vs int, json string vs object, single vs list.
        """
        field_name = context_info.get("field_name", "value")
        given_val = context_info.get("given_value")
        expected_type = str(context_info.get("expected_type", "")).lower()
        err_msg = str(err).lower()

        # Deduce from err_msg if not explicitly provided
        if not expected_type:
            if "int" in err_msg or "integer" in err_msg:
                expected_type = "int"
            elif "dict" in err_msg or "object" in err_msg or "mapping" in err_msg:
                expected_type = "dict"
            elif "list" in err_msg or "array" in err_msg or "sequence" in err_msg:
                expected_type = "list"
            elif "float" in err_msg or "number" in err_msg:
                expected_type = "float"

        given_type_name = type(given_val).__name__ if given_val is not None else "str"

        if isinstance(given_val, str) and expected_type in ("int", "integer"):
            sig = f"TYPE:STRING_TO_INT:{field_name}"
        elif isinstance(given_val, str) and expected_type in ("float", "number"):
            sig = f"TYPE:STRING_TO_FLOAT:{field_name}"
        elif (
            isinstance(given_val, str)
            and (given_val.strip().startswith("{") or given_val.strip().startswith("["))
            and expected_type in ("dict", "object", "list", "array")
        ):
            sig = f"TYPE:JSON_STRING_TO_OBJECT:{field_name}"
        elif not isinstance(given_val, (list, tuple)) and expected_type in ("list", "array"):
            sig = f"TYPE:SINGLE_TO_LIST:{field_name}"
        else:
            sig = f"TYPE:MISMATCH:{field_name}:{given_type_name}->{expected_type or 'unknown'}"

        return {
            "category": "type_mismatch",
            "error_type": "TypeError",
            "signature": sig,
            "details": {
                "field_name": field_name,
                "given_value": given_val,
                "given_type": given_type_name,
                "expected_type": expected_type or "int",
            },
        }


class ContextHasher:
    """Computes deterministic normalized context hash for code and trajectories."""

    @staticmethod
    def compute_context_hash(code_or_context: str) -> str:
        """
        Normalizes AST / text by stripping comments, whitespace variations,
        timestamps, memory addresses (0x[0-9a-fA-F]+), and line numbers.
        Produces deterministic SHA-256 hash.
        """
        if not isinstance(code_or_context, str):
            try:
                code_or_context = json.dumps(code_or_context, sort_keys=True)
            except Exception:
                code_or_context = str(code_or_context)

        text = code_or_context

        # Strip volatile memory addresses
        text = re.sub(r"0x[0-9a-fA-F]+", "<ADDR>", text)
        # Strip timestamps
        text = re.sub(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?", "<TIMESTAMP>", text)
        # Strip line numbers in error messages (e.g., "line 42")
        text = re.sub(r"\bline\s+\d+\b", "line <N>", text, flags=re.IGNORECASE)

        # Line-by-line normalization and comment stripping
        normalized_lines: List[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # Strip pure comment line
            if stripped.startswith("#"):
                continue
            # Strip trailing comments if safe (not inside string quotes)
            if "#" in line and '"' not in line and "'" not in line:
                line = line.split("#", 1)[0]
            # Normalize whitespace: collapse consecutive spaces/tabs to a single space
            norm_line = " ".join(line.split())
            if norm_line:
                normalized_lines.append(norm_line)

        canonical_text = "\n".join(normalized_lines)
        return hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()


@dataclass
class ParameterizedMacro:
    """Represents an in-memory parameterized transformation macro."""

    macro_id: str
    context_hash: str
    ast_error_sig: str
    error_category: str  # 'syntax', 'schema_drift', 'type_mismatch'
    action_type: str  # 'insert_token', 'remap_key', 'cast_type', 'regex_replace'
    params: Dict[str, Any]
    confidence: float = 0.8
    usage_count: int = 1
    success_count: int = 1
    is_blacklisted: bool = False

    def apply(self, target: Any) -> Tuple[bool, Any]:
        """
        Safely applies the macro transformation in-memory.
        Returns: (success: bool, repaired_target: Any)
        NO eval/exec on untrusted code!
        """
        act = (self.action_type or "").lower().strip()
        try:
            if act in ("insert_token", "syntax_missing_colon", "missing_colon"):
                return self._apply_insert_token(target)
            elif act in ("remap_key", "rename_param", "schema_rename_key"):
                return self._apply_remap_key(target)
            elif act in ("cast_type", "type_cast", "type_mismatch"):
                return self._apply_cast_type(target)
            elif act in ("regex_replace", "replace"):
                return self._apply_regex_replace(target)
            return False, target
        except Exception as ex:
            logger.debug("Failed applying macro %s: %s", self.macro_id, ex)
            return False, target

    def _apply_insert_token(self, target: Any) -> Tuple[bool, Any]:
        if not isinstance(target, str):
            return False, target
        token = self.params.get("token") or self.params.get("append_char") or ":"
        line_no = self.params.get("line_no") or self.params.get("line")
        lines = target.splitlines()

        if line_no is not None and 1 <= line_no <= len(lines):
            idx = line_no - 1
            if not lines[idx].rstrip().endswith(token):
                lines[idx] = lines[idx].rstrip() + token
                return True, "\n".join(lines)
            return True, target

        # Find header line that requires the token
        stmt_pat = re.compile(
            r"^(?P<indent>\s*)(?P<stmt>(?:async\s+)?(?:def|class|if|elif|else|for|while|try|except|finally|with|match|case)\b[^:]*)$"
        )
        new_lines = []
        modified = False
        for line in lines:
            if not modified and stmt_pat.match(line):
                new_lines.append(line.rstrip() + token)
                modified = True
            else:
                new_lines.append(line)
        if modified:
            return True, "\n".join(new_lines)

        # Fallback for single line without colon
        if len(lines) == 1 and not lines[0].rstrip().endswith(token):
            return True, lines[0].rstrip() + token

        return False, target

    def _apply_remap_key(self, target: Any) -> Tuple[bool, Any]:
        old_key = self.params.get("old_key")
        new_key = self.params.get("new_key")
        if not old_key or not new_key:
            return False, target

        if isinstance(target, dict):
            if old_key in target:
                res = dict(target)
                res[new_key] = res.pop(old_key)
                return True, res
            return False, target

        if isinstance(target, str):
            try:
                parsed = json.loads(target)
                if isinstance(parsed, dict) and old_key in parsed:
                    parsed[new_key] = parsed.pop(old_key)
                    return True, json.dumps(parsed)
            except Exception as ex:
                logger.debug("String is not JSON formatted: %s", ex)
            pat = rf'([\'"]){re.escape(old_key)}\1\s*:'
            if re.search(pat, target):
                return True, re.sub(pat, rf"\1{new_key}\1:", target)

        return False, target

    def _apply_cast_type(self, target: Any) -> Tuple[bool, Any]:
        field = self.params.get("field")
        target_type = str(self.params.get("target_type", "int")).lower()

        def _cast(val: Any) -> Any:
            if target_type in ("int", "integer"):
                return int(val)
            elif target_type in ("float", "number"):
                return float(val)
            elif target_type in ("dict", "object", "json_object"):
                return json.loads(val) if isinstance(val, str) else dict(val)
            elif target_type in ("list", "array"):
                return json.loads(val) if isinstance(val, str) else list(val)
            elif target_type in ("bool", "boolean"):
                if isinstance(val, str):
                    return val.lower() in ("true", "1", "yes")
                return bool(val)
            return val

        if isinstance(target, dict):
            if field and field in target:
                res = dict(target)
                res[field] = _cast(res[field])
                return True, res
            if not field and len(target) == 1:
                k = list(target.keys())[0]
                res = dict(target)
                res[k] = _cast(res[k])
                return True, res
            return False, target

        try:
            return True, _cast(target)
        except Exception:
            return False, target

    def _apply_regex_replace(self, target: Any) -> Tuple[bool, Any]:
        pattern = self.params.get("pattern")
        replacement = self.params.get("replacement", "")
        if pattern and isinstance(target, str):
            new_target, count = re.subn(pattern, replacement, target)
            return count > 0, new_target
        return False, target


class MacroCacheEngine:
    """
    Tier 10 Macro Cache Engine.
    Persists parameterized macros in SQLite WAL mode.
    Enables zero-token repair for syntax errors, schema drift, and type mismatches.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.extractor = ASTErrorSignatureExtractor()
        self.hasher = ContextHasher()

        if db_path is None:
            repo_root = os.getcwd()
            synapse_dir = os.path.join(repo_root, ".synapse")
            os.makedirs(synapse_dir, exist_ok=True)
            self.db_path = os.path.join(synapse_dir, "macro_cache.db")
        else:
            self.db_path = db_path
            parent_dir = os.path.dirname(self.db_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    @contextmanager
    def _open_connection(self):
        """Context manager that commits/rolls back AND always closes the SQLite connection."""
        conn = self._get_connection()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._open_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS macro_cache (
                    macro_id TEXT PRIMARY KEY,
                    context_hash TEXT NOT NULL,
                    ast_error_sig TEXT NOT NULL,
                    error_category TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    confidence REAL DEFAULT 0.8,
                    usage_count INTEGER DEFAULT 1,
                    success_count INTEGER DEFAULT 1,
                    is_blacklisted INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_macro_lookup ON macro_cache (context_hash, ast_error_sig);"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_macro_sig ON macro_cache (ast_error_sig);")
            conn.commit()

    def compute_context_hash(self, context_str: str) -> str:
        """Computes deterministic context hash."""
        return self.hasher.compute_context_hash(context_str)

    def extract_error_signature(self, error: Exception | dict, source_or_context: Any = "") -> Dict[str, Any]:
        """Extracts canonical error signature and category."""
        if isinstance(error, SyntaxError):
            code = source_or_context if isinstance(source_or_context, str) else str(source_or_context)
            return self.extractor.extract_from_syntax_error(error, code)
        elif isinstance(error, TypeError):
            ctx = source_or_context if isinstance(source_or_context, dict) else {"given_value": source_or_context}
            return self.extractor.extract_from_type_error(error, ctx)
        elif isinstance(error, dict):
            if "signature" in error and "category" in error:
                return error
            cat = error.get("category", "")
            if cat == "schema_drift" or "tool_name" in error or "expected_schema" in error:
                tool_name = error.get("tool_name", "tool")
                given_args = error.get(
                    "given_args", source_or_context if isinstance(source_or_context, dict) else {}
                )
                expected_schema = error.get("expected_schema", {})
                return self.extractor.extract_from_schema_drift(tool_name, given_args, expected_schema)
            elif cat == "type_mismatch" or "expected_type" in error:
                dummy_err = TypeError(error.get("message", "type mismatch"))
                return self.extractor.extract_from_type_error(dummy_err, error)
            elif cat == "syntax":
                code = source_or_context if isinstance(source_or_context, str) else str(source_or_context)
                dummy_syntax = SyntaxError(error.get("message", "syntax error"))
                dummy_syntax.lineno = error.get("line", 1)
                dummy_syntax.offset = error.get("offset", 0)
                dummy_syntax.text = error.get("line_text", "")
                return self.extractor.extract_from_syntax_error(dummy_syntax, code)
            elif "signature" in error:
                return error

        # Fallback
        err_str = str(error)
        clean_sig = re.sub(r"[^a-zA-Z0-9_]+", "_", err_str)[:32]
        return {
            "category": "unknown",
            "error_type": type(error).__name__,
            "signature": f"GENERIC:ERROR:{clean_sig}",
            "details": {"error": err_str},
        }

    def store_macro(
        self,
        context_hash: str,
        error_sig: str,
        action_type: str,
        params: dict,
        error_category: str = "syntax",
        confidence: float = 0.8,
    ) -> str:
        """Stores or updates a parameterized macro in SQLite WAL."""
        scrubbed_params = scrub_data_dict(params)
        params_json = json.dumps(scrubbed_params, sort_keys=True)
        raw_id_seed = f"{context_hash}:{error_sig}:{action_type}:{params_json}"
        macro_id = f"macro_{hashlib.sha256(raw_id_seed.encode('utf-8')).hexdigest()[:16]}"

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._open_connection() as conn:
            conn.execute(
                """
                INSERT INTO macro_cache (
                    macro_id, context_hash, ast_error_sig, error_category,
                    action_type, params_json, confidence, usage_count,
                    success_count, is_blacklisted, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, 0, ?, ?)
                ON CONFLICT(macro_id) DO UPDATE SET
                    confidence = max(macro_cache.confidence, excluded.confidence),
                    usage_count = macro_cache.usage_count + 1,
                    success_count = macro_cache.success_count + 1,
                    updated_at = excluded.updated_at;
                """,
                (
                    macro_id,
                    context_hash,
                    error_sig,
                    error_category,
                    action_type,
                    params_json,
                    confidence,
                    now,
                    now,
                ),
            )
            conn.commit()
        return macro_id

    def lookup_macro(self, context_hash: str, error_sig: str) -> Optional[ParameterizedMacro]:
        """Looks up best matching parameterized macro from SQLite WAL."""
        with self._open_connection() as conn:
            # 1. Exact match on (context_hash, ast_error_sig)
            cursor = conn.execute(
                """
                SELECT macro_id, context_hash, ast_error_sig, error_category,
                       action_type, params_json, confidence, usage_count,
                       success_count, is_blacklisted
                FROM macro_cache
                WHERE context_hash = ? AND ast_error_sig = ? AND is_blacklisted = 0
                ORDER BY confidence DESC, success_count DESC
                LIMIT 1;
                """,
                (context_hash, error_sig),
            )
            row = cursor.fetchone()
            if not row:
                # 2. Fallback to match on ast_error_sig alone
                cursor = conn.execute(
                    """
                    SELECT macro_id, context_hash, ast_error_sig, error_category,
                           action_type, params_json, confidence, usage_count,
                           success_count, is_blacklisted
                    FROM macro_cache
                    WHERE ast_error_sig = ? AND is_blacklisted = 0
                    ORDER BY confidence DESC, success_count DESC
                    LIMIT 1;
                    """,
                    (error_sig,),
                )
                row = cursor.fetchone()

            if row:
                return ParameterizedMacro(
                    macro_id=row[0],
                    context_hash=row[1],
                    ast_error_sig=row[2],
                    error_category=row[3],
                    action_type=row[4],
                    params=json.loads(row[5]),
                    confidence=float(row[6]),
                    usage_count=int(row[7]),
                    success_count=int(row[8]),
                    is_blacklisted=bool(row[9]),
                )
        return None

    def record_feedback(self, macro_id: str, success: bool) -> None:
        """Records outcome feedback for a macro and adjusts confidence/blacklist status."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._open_connection() as conn:
            cursor = conn.execute(
                "SELECT confidence, usage_count, success_count FROM macro_cache WHERE macro_id = ?",
                (macro_id,),
            )
            row = cursor.fetchone()
            if not row:
                return
            conf, usages, successes = float(row[0]), int(row[1]) + 1, int(row[2])
            if success:
                successes += 1
                conf = min(1.0, conf + 0.05)
            else:
                conf = max(0.0, conf - 0.2)

            is_blacklisted = 1 if (conf < 0.3 or (usages >= 3 and (successes / usages) < 0.3)) else 0

            conn.execute(
                """
                UPDATE macro_cache
                SET confidence = ?, usage_count = ?, success_count = ?,
                    is_blacklisted = ?, updated_at = ?
                WHERE macro_id = ?;
                """,
                (conf, usages, successes, is_blacklisted, now, macro_id),
            )
            conn.commit()

    def execute_zero_token_repair(self, context: Any, error: Exception | dict) -> Dict[str, Any]:
        """
        Executes local in-memory macro fix with verifiable 0 tokens consumed.
        Returns:
            {"repaired": bool, "output": Any, "tokens_consumed": 0, "macro_id": Optional[str], "signature": str}
        """
        sig_info = self.extract_error_signature(error, context)
        error_sig = sig_info.get("signature", "")
        category = sig_info.get("category", "")
        ctx_hash = self.compute_context_hash(str(context))

        macro = self.lookup_macro(ctx_hash, error_sig)

        # Auto-synthesize seed macro for known deterministic patterns if not cached yet
        if not macro:
            synthesized = self._synthesize_seed_macro(ctx_hash, sig_info, context)
            if synthesized:
                self.store_macro(
                    context_hash=ctx_hash,
                    error_sig=error_sig,
                    action_type=synthesized["action_type"],
                    params=synthesized["params"],
                    error_category=category,
                    confidence=synthesized.get("confidence", 0.85),
                )
                macro = self.lookup_macro(ctx_hash, error_sig)

        if macro:
            success, repaired_output = macro.apply(context)
            if success:
                # Validate output if syntax
                if category == "syntax" and isinstance(repaired_output, str):
                    try:
                        ast.parse(repaired_output)
                    except SyntaxError:
                        self.record_feedback(macro.macro_id, False)
                        return {
                            "repaired": False,
                            "output": context,
                            "tokens_consumed": 0,
                            "macro_id": macro.macro_id,
                            "signature": error_sig,
                        }

                self.record_feedback(macro.macro_id, True)
                return {
                    "repaired": True,
                    "output": repaired_output,
                    "tokens_consumed": 0,
                    "macro_id": macro.macro_id,
                    "signature": error_sig,
                }
            else:
                self.record_feedback(macro.macro_id, False)

        return {
            "repaired": False,
            "output": context,
            "tokens_consumed": 0,
            "macro_id": None,
            "signature": error_sig,
        }

    def _synthesize_seed_macro(
        self, context_hash: str, sig_info: Dict[str, Any], context: Any
    ) -> Optional[Dict[str, Any]]:
        """Synthesizes a safe deterministic seed macro for recurring canonical errors."""
        sig = sig_info.get("signature", "")
        details = sig_info.get("details", {})
        category = sig_info.get("category", "")

        if category == "syntax":
            if sig.startswith("SYNTAX:MISSING_COLON"):
                line_no = sig_info.get("line") or details.get("line_no")
                return {
                    "action_type": "insert_token",
                    "params": {
                        "token": ":",
                        "line_no": line_no,
                        "statement_type": details.get("statement_type", "def"),
                    },
                    "confidence": 0.9,
                }
        elif category == "schema_drift":
            if sig.startswith("SCHEMA:RENAMED_PARAM"):
                old_k = details.get("old_key")
                new_k = details.get("new_key")
                if old_k and new_k:
                    return {
                        "action_type": "remap_key",
                        "params": {"old_key": old_k, "new_key": new_k},
                        "confidence": 0.95,
                    }
        elif category == "type_mismatch":
            field_name = details.get("field_name")
            expected_type = details.get("expected_type", "int")
            if field_name:
                return {
                    "action_type": "cast_type",
                    "params": {"field": field_name, "target_type": expected_type},
                    "confidence": 0.9,
                }

        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Tier 10 Macro Cache Engine & Zero-Token Repair")
    parser.add_argument(
        "--error-type",
        type=str,
        default="",
        help="Error category (syntax, schema_drift, type_mismatch)",
    )
    parser.add_argument("--error-msg", type=str, default="", help="Error message text")
    parser.add_argument("--context", type=str, default="", help="Context string or path to source/JSON file")
    parser.add_argument("--repair", action="store_true", help="Execute zero-token repair on given context")
    parser.add_argument("--db-path", type=str, default=None, help="Path to SQLite cache DB")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()

    engine = MacroCacheEngine(db_path=args.db_path)

    context_str = args.context
    if os.path.exists(context_str) and os.path.isfile(context_str):
        with open(context_str, "r", encoding="utf-8") as f:
            context_str = f.read()
    elif "\\n" in context_str and "\n" not in context_str:
        context_str = context_str.encode("utf-8").decode("unicode_escape")

    parsed_context: Any = context_str
    if context_str.strip().startswith("{") and context_str.strip().endswith("}"):
        try:
            parsed_context = json.loads(context_str)
        except Exception:
            parsed_context = context_str

    if not context_str.strip():
        result = {
            "status": "empty_context",
            "repaired": False,
            "tokens_consumed": 0,
            "macro_id": None,
            "signature": "NONE",
            "output": context_str,
        }
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("[EMPTY CONTEXT] No context provided to repair.")
        return 0

    error_obj: Union[Exception, dict]
    if args.error_type == "syntax":
        syntax_err = None
        if isinstance(parsed_context, str):
            try:
                ast.parse(parsed_context)
            except SyntaxError as e:
                syntax_err = e
        if syntax_err is None:
            syntax_err = SyntaxError(args.error_msg or "syntax error")
            syntax_err.lineno = 1
            syntax_err.offset = len(str(parsed_context).splitlines()[0]) if str(parsed_context) else 0
        error_obj = syntax_err
    elif args.error_type == "type_mismatch":
        error_obj = {
            "category": "type_mismatch",
            "message": args.error_msg or "type mismatch",
            "field_name": "timeout",
            "expected_type": "int",
        }
    elif args.error_type == "schema_drift":
        renamed_m = re.search(r"(\w+)\s*(?:->|to)\s*(\w+)", args.error_msg)
        old_k = renamed_m.group(1) if renamed_m else "filepath"
        new_k = renamed_m.group(2) if renamed_m else "file_path"
        error_obj = {
            "category": "schema_drift",
            "tool_name": "tool",
            "given_args": parsed_context if isinstance(parsed_context, dict) else {},
            "expected_schema": {"properties": {new_k: {"type": "string"}}, "required": [new_k]},
        }
    else:
        syntax_err = None
        if isinstance(parsed_context, str):
            try:
                ast.parse(parsed_context)
            except SyntaxError as e:
                syntax_err = e
        if syntax_err:
            error_obj = syntax_err
        else:
            error_obj = {"category": "unknown", "message": args.error_msg or "generic error"}

    if args.repair:
        repair_res = engine.execute_zero_token_repair(parsed_context, error_obj)
        res_output = {
            "status": "success" if repair_res["repaired"] else "unrepaired",
            "repaired": repair_res["repaired"],
            "tokens_consumed": repair_res["tokens_consumed"],
            "macro_id": repair_res["macro_id"],
            "signature": repair_res.get("signature"),
            "output": repair_res["output"],
        }
        if args.json:
            print(json.dumps(res_output, indent=2))
        else:
            print(
                f"[REPAIR] Status: {res_output['status']}, Tokens Consumed: 0, Signature: {res_output['signature']}"
            )
            if repair_res["repaired"]:
                print(f"Repaired Output:\n{res_output['output']}")
        return 0
    else:
        sig_info = engine.extract_error_signature(error_obj, parsed_context)
        ctx_hash = engine.compute_context_hash(str(parsed_context))
        res_output = {
            "status": "signature_extracted",
            "context_hash": ctx_hash,
            "signature": sig_info.get("signature"),
            "category": sig_info.get("category"),
            "details": sig_info.get("details"),
        }
        if args.json:
            print(json.dumps(res_output, indent=2))
        else:
            print(
                f"[SIGNATURE] Category: {res_output['category']}, Sig: {res_output['signature']}, Hash: {ctx_hash}"
            )
        return 0


if __name__ == "__main__":
    sys.exit(main())
