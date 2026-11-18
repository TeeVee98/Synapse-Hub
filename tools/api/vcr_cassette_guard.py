#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/vcr_cassette_guard.py — Deterministic Network VCR Shield & Cassette Linter
--------------------------------------------------------------------------------
Inspired by Pydantic-AI & Supabase deterministic network testing standards.

Core Capabilities:
  1. Deterministic VCR Record & Replay: Intercepts HTTP/API requests and replays
     recorded responses offline, eliminating third-party network flakiness.
  2. Automatic Sensitive Data Sanitizer: Redacts authorization tokens, cookies,
     credentials, and sensitive payload fields before recording to disk.
  3. AST Orphan Cassette Linter: Scans test files via AST analysis to identify
     orphaned cassette files that are no longer referenced by any active test.
"""
from __future__ import annotations

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


import argparse
import ast
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("vcr_cassette_guard")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Sensitive header keys (case-insensitive) to redact
DEFAULT_SENSITIVE_HEADERS: Set[str] = {
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
    "api-key",
    "apikey",
    "token",
    "secret",
}

# Sensitive body field keys (case-insensitive) to redact
DEFAULT_SENSITIVE_FIELDS: Set[str] = {
    "password",
    "passwd",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "apikey",
    "client_secret",
    "credit_card",
    "card_number",
    "ssn",
}

REDACTED_VALUE = "***REDACTED***"


class CassetteError(Exception):
    """Base exception for cassette operations."""
    pass


class CassetteNotFoundError(CassetteError):
    """Raised when an expected cassette file or interaction is missing."""
    pass


class CassetteMismatchError(CassetteError):
    """Raised when recorded interaction does not match incoming request in replay mode."""
    pass


def sanitize_headers(headers: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize sensitive HTTP headers, replacing secret values with REDACTED_VALUE."""
    sanitized: Dict[str, Any] = {}
    for key, value in headers.items():
        if key.lower() in DEFAULT_SENSITIVE_HEADERS:
            sanitized[key] = REDACTED_VALUE
        else:
            sanitized[key] = value
    return sanitized


def sanitize_payload(payload: Any) -> Any:
    """Recursively sanitize sensitive fields in JSON-serializable payloads."""
    if isinstance(payload, dict):
        sanitized_dict: Dict[str, Any] = {}
        for key, value in payload.items():
            if str(key).lower() in DEFAULT_SENSITIVE_FIELDS:
                sanitized_dict[key] = REDACTED_VALUE
            else:
                sanitized_dict[key] = sanitize_payload(value)
        return sanitized_dict
    elif isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    elif isinstance(payload, str):
        # Redact bearer token patterns if embedded in strings
        sanitized_str = re.sub(
            r"(?i)\bBearer\s+[a-zA-Z0-9_\-\.]{15,}\b",
            f"Bearer {REDACTED_VALUE}",
            payload,
        )
        return sanitized_str
    return payload


class VCRCassetteGuard:
    """
    Manages deterministic HTTP/API cassette recordings and offline replays.
    Enforces the Pydantic-AI standard: 100% deterministic offline replay.
    """

    def __init__(
        self,
        cassette_dir: str,
        mode: str = "replay",
        sanitize: bool = True,
    ) -> None:
        self.cassette_dir = os.path.abspath(cassette_dir)
        self.mode = mode.lower()  # "record", "replay", or "passthrough"
        self.sanitize = sanitize
        os.makedirs(self.cassette_dir, exist_ok=True)

    def _get_cassette_path(self, cassette_name: str) -> str:
        stem = cassette_name
        if stem.endswith((".json", ".yaml", ".yml")):
            stem = os.path.splitext(stem)[0]
        return os.path.join(self.cassette_dir, f"{stem}.json")

    def record_interaction(
        self,
        cassette_name: str,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
    ) -> str:
        """
        Record a single HTTP interaction into the cassette.
        Automatically sanitizes sensitive headers and payload fields.
        """
        path = self._get_cassette_path(cassette_name)

        req_headers = request_data.get("headers", {})
        res_headers = response_data.get("headers", {})
        req_body = request_data.get("body")
        res_body = response_data.get("body")

        if self.sanitize:
            req_headers = sanitize_headers(req_headers)
            res_headers = sanitize_headers(res_headers)
            if req_body is not None:
                req_body = sanitize_payload(req_body)
            if res_body is not None:
                res_body = sanitize_payload(res_body)

        interaction = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "request": {
                "method": request_data.get("method", "GET").upper(),
                "url": request_data.get("url", ""),
                "headers": req_headers,
                "body": req_body,
            },
            "response": {
                "status": response_data.get("status", 200),
                "headers": res_headers,
                "body": res_body,
            },
        }

        existing_interactions: List[Dict[str, Any]] = []
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        existing_interactions = data
                    elif isinstance(data, dict) and "interactions" in data:
                        existing_interactions = data["interactions"]
            except Exception as e:
                logger.warning("Failed to parse existing cassette %s: %s", path, e)
                existing_interactions = []

        existing_interactions.append(interaction)

        cassette_content = {
            "version": "1.0",
            "cassette": os.path.basename(path),
            "interactions": existing_interactions,
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(cassette_content, f, indent=2, ensure_ascii=False)

        return path

    def replay_interaction(
        self,
        cassette_name: str,
        request_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Replay an interaction matching method and URL from the cassette.
        Raises CassetteNotFoundError if cassette or interaction is absent.
        """
        path = self._get_cassette_path(cassette_name)
        if not os.path.exists(path):
            raise CassetteNotFoundError(
                f"Cassette file not found: {path} (mode={self.mode}). "
                "Deterministic replay requires pre-recorded cassette fixtures."
            )

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        interactions = data.get("interactions", []) if isinstance(data, dict) else data
        target_method = request_data.get("method", "GET").upper()
        target_url = request_data.get("url", "")

        for entry in interactions:
            req = entry.get("request", {})
            if (
                req.get("method", "").upper() == target_method
                and req.get("url", "") == target_url
            ):
                return entry.get("response", {})

        raise CassetteMismatchError(
            f"No matching interaction found in {os.path.basename(path)} for "
            f"[{target_method} {target_url}]."
        )


def extract_referenced_cassettes_from_python_ast(file_path: str) -> Set[str]:
    """Parse a Python test file and extract cassette names used in decorators or function calls."""
    referenced: Set[str] = set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=file_path)
    except Exception:
        return referenced

    for node in ast.walk(tree):
        # Match function calls or decorator calls
        if isinstance(node, ast.Call):
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            # Check if function name indicates cassette / vcr usage
            is_vcr_call = any(k in func_name.lower() for k in ("cassette", "vcr", "record", "replay"))

            if is_vcr_call:
                # Extract first positional arg if string literal
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    stem = os.path.splitext(node.args[0].value)[0]
                    referenced.add(stem)

            # Check any keyword arguments like cassette="name", cassette_name="name", etc.
            for kw in node.keywords:
                if kw.arg and any(k in kw.arg.lower() for k in ("cassette", "fixture", "mock_record")):
                    if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        stem = os.path.splitext(kw.value.value)[0]
                        referenced.add(stem)

        # Match constant strings ending in .json or .yaml inside tests/cassettes
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            val = node.value
            if "cassette" in val.lower() or val.endswith((".cassette.json", ".cassette.yaml")):
                clean_name = os.path.splitext(os.path.basename(val))[0]
                if clean_name:
                    referenced.add(clean_name)

    return referenced


def extract_referenced_cassettes_from_text(file_path: str) -> Set[str]:
    """Fallback text & regex scanner for JS/TS/Groovy test files."""
    referenced: Set[str] = set()
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return referenced

    patterns = [
        re.compile(r"""(?:use_cassette|useCassette|cassette)\s*\(\s*['"]([^'"]+)['"]"""),
        re.compile(r"""cassette(?:_name)?\s*[:=]\s*['"]([^'"]+)['"]"""),
        re.compile(r"""['"]([^'"]+\.cassette\.json)['"]"""),
    ]

    for pat in patterns:
        for match in pat.finditer(content):
            raw = match.group(1)
            stem = os.path.splitext(os.path.basename(raw))[0]
            referenced.add(stem)

    return referenced


def find_orphaned_cassettes(
    repo_root: str,
    cassette_dir: Optional[str] = None,
) -> List[str]:
    """
    Identifies cassette files on disk that are never referenced by any active test.
    Returns a list of orphaned cassette file paths.
    """
    repo_root = os.path.abspath(repo_root)

    # Resolve cassette directories to inspect
    candidate_dirs: List[str] = []
    if cassette_dir:
        candidate_dirs.append(os.path.abspath(cassette_dir))
    else:
        for root, dirs, _ in os.walk(repo_root):
            if any(p in root for p in [".git", "node_modules", ".venv", "build", "dist"]):
                continue
            for d in dirs:
                if d.lower() == "cassettes":
                    candidate_dirs.append(os.path.join(root, d))

    if not candidate_dirs:
        return []

    # 1. Collect physical cassette files
    physical_cassettes: Dict[str, str] = {}  # stem -> full path
    for cdir in candidate_dirs:
        if not os.path.isdir(cdir):
            continue
        for fname in os.listdir(cdir):
            if fname.endswith((".json", ".yaml", ".yml")):
                stem = os.path.splitext(fname)[0]
                physical_cassettes[stem] = os.path.join(cdir, fname)

    if not physical_cassettes:
        return []

    # 2. Collect referenced cassette stems from all test files
    referenced_stems: Set[str] = set()
    ignored_dirs = {".git", "node_modules", ".venv", "venv", "build", "dist", ".gradle", "__pycache__"}

    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]
        for f in files:
            if f.endswith((".py", ".ts", ".js", ".groovy")):
                fpath = os.path.join(root, f)
                if f.endswith(".py"):
                    referenced_stems.update(extract_referenced_cassettes_from_python_ast(fpath))
                else:
                    referenced_stems.update(extract_referenced_cassettes_from_text(fpath))

    # 3. Detect orphans
    orphans: List[str] = []
    for stem, full_path in physical_cassettes.items():
        if stem not in referenced_stems:
            orphans.append(full_path)

    return sorted(orphans)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="VCR Cassette Guard — Deterministic Network & Cassette Linter"
    )
    parser.add_argument(
        "--lint-orphans",
        action="store_true",
        help="Scan for unreferenced orphaned cassette files.",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory (default: current directory).",
    )
    parser.add_argument(
        "--cassette-dir",
        default=None,
        help="Specific cassette directory to inspect.",
    )
    parser.add_argument(
        "--sanitize-file",
        help="Path to an existing cassette file to sanitize in place.",
    )

    args = parser.parse_args()

    if args.sanitize_file:
        if not os.path.isfile(args.sanitize_file):
            print(f"[FAIL] File not found: {args.sanitize_file}")
            return 1
        with open(args.sanitize_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        sanitized = sanitize_payload(data)
        with open(args.sanitize_file, "w", encoding="utf-8") as f:
            json.dump(sanitized, f, indent=2, ensure_ascii=False)
        print(f"[PASS] Successfully sanitized {args.sanitize_file}")
        return 0

    if args.lint_orphans:
        orphans = find_orphaned_cassettes(args.repo_root, args.cassette_dir)
        if orphans:
            print(f"[FAIL] Found {len(orphans)} orphaned cassette file(s):")
            for o in orphans:
                print(f"   - {o}")
            return 1
        print("[PASS] 100% Cassette integrity: Zero orphaned cassette files detected.")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
