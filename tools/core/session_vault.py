#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Enterprise Session State & Authentication Vault (Zero-Second Auth Bridge)
--------------------------------------------------------------------------
Provides secure management, caching, and TTL expiry validation for browser
authentication states (Playwright storageState.json, cookies, and tokens).

Eliminates repetitive multi-turn login flows across complex corporate SSO
(Okta, Azure AD, Keycloak) by hydrating valid sessions in under 5ms.

Features:
  1. Profile-Based Session Isolation:
     - Stores session states per role/tenant (e.g. 'admin', 'user', 'manager').
  2. Intelligent Expiry & TTL Validation:
     - Parses cookie 'expires' timestamps and JWT token 'exp' claims.
     - Prevents test runs with stale credentials before browser launch.
  3. Safe Local Storage:
     - Defaults to '.auth/' within project root (excluded from Git commits).
  4. One-Line Playwright Hydration:
     - browser.new_context(storage_state=vault.get_state_path('admin'))
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


import os
import sys
import json
import time
import base64
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
DEFAULT_VAULT_DIR = os.path.join(REPO_ROOT, ".auth")


def _decode_jwt_payload(token: str) -> Optional[Dict[str, Any]]:
    """Extracts and decodes JWT payload without signature verification for expiry check."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload_b64 = parts[1]
        # Pad base64 if needed
        padding = 4 - (len(payload_b64) % 4)
        if padding != 4:
            payload_b64 += "=" * padding
        decoded = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        return None


class SessionVault:
    """Enterprise authentication state manager and zero-second login vault."""

    def __init__(self, vault_dir: Optional[str] = None):
        self.vault_dir = vault_dir or os.environ.get("SYNAPSE_AUTH_VAULT_DIR") or DEFAULT_VAULT_DIR
        os.makedirs(self.vault_dir, exist_ok=True)

    def _state_file(self, role: str) -> str:
        safe_role = "".join(c for c in role if c.isalnum() or c in ("-", "_")).lower()
        return os.path.join(self.vault_dir, f"{safe_role}_state.json")

    def _meta_file(self, role: str) -> str:
        safe_role = "".join(c for c in role if c.isalnum() or c in ("-", "_")).lower()
        return os.path.join(self.vault_dir, f"{safe_role}_meta.json")

    def save_session(
        self,
        role: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        ttl_seconds: int = 3600,
    ) -> str:
        """
        Saves browser storageState (cookies & origins) to the vault with TTL metadata.
        Returns the absolute path to the stored storageState JSON file.
        """
        state_path = self._state_file(role)
        meta_path = self._meta_file(role)

        now = time.time()
        meta = {
            "role": role,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_ts": now,
            "ttl_seconds": ttl_seconds,
            "expires_ts": now + ttl_seconds,
            "cookie_count": len(state.get("cookies", [])),
            "origin_count": len(state.get("origins", [])),
            "custom": metadata or {},
        }

        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        return state_path

    def save_from_file(self, role: str, file_path: str, ttl_seconds: int = 3600) -> str:
        """Loads a storageState file from disk and imports it into the vault."""
        with open(file_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        return self.save_session(role, state, ttl_seconds=ttl_seconds)

    def validate_session(self, role: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validates whether a stored session exists and is unexpired.
        Returns (is_valid, reason, info_dict).
        """
        state_path = self._state_file(role)
        meta_path = self._meta_file(role)

        if not os.path.exists(state_path) or not os.path.exists(meta_path):
            return False, f"No stored session found for role '{role}'", {}

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as e:
            return False, f"Corrupted session metadata for '{role}': {e}", {}

        now = time.time()
        expires_ts = meta.get("expires_ts", 0)
        if now >= expires_ts:
            expired_ago = int(now - expires_ts)
            return False, f"Session expired {expired_ago}s ago", meta

        # Inspect cookie expirations if available
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            cookies = state.get("cookies", [])
            for c in cookies:
                c_exp = c.get("expires")
                if c_exp and c_exp > 0 and c_exp < now:
                    # Stale cookie detected
                    return False, f"Cookie '{c.get('name')}' has expired", meta

            # Inspect JWT tokens in localStorage origins
            for origin in state.get("origins", []):
                for item in origin.get("localStorage", []):
                    val = item.get("value", "")
                    if val.startswith("eyJ"):  # Common JWT prefix
                        jwt_data = _decode_jwt_payload(val)
                        if jwt_data and "exp" in jwt_data:
                            if jwt_data["exp"] < now:
                                return False, f"JWT token in localStorage '{item.get('name')}' has expired", meta
        except Exception as e:
            return False, f"Could not parse session state file: {e}", meta

        remaining = int(expires_ts - now)
        return True, f"Session valid (expires in {remaining}s)", meta

    def get_state_path(self, role: str) -> Optional[str]:
        """Returns the path to the storageState file if valid, or None if expired/missing."""
        valid, _, _ = self.validate_session(role)
        if valid:
            return self._state_file(role)
        return None

    def load_session(self, role: str) -> Optional[Dict[str, Any]]:
        """Loads and returns storageState dict if valid, or None if expired."""
        valid, _, _ = self.validate_session(role)
        if not valid:
            return None
        with open(self._state_file(role), "r", encoding="utf-8") as f:
            return json.load(f)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Enumerates all sessions stored in the vault with their validity status."""
        results = []
        if not os.path.exists(self.vault_dir):
            return results

        for fname in os.listdir(self.vault_dir):
            if fname.endswith("_meta.json"):
                role = fname[:-10]
                valid, reason, meta = self.validate_session(role)
                results.append({
                    "role": role,
                    "valid": valid,
                    "reason": reason,
                    "expires_ts": meta.get("expires_ts"),
                    "cookie_count": meta.get("cookie_count", 0),
                    "created_at": meta.get("created_at"),
                })
        return results

    def prune_expired(self) -> int:
        """Removes all expired session and metadata files. Returns number of pruned sessions."""
        pruned = 0
        for s in self.list_sessions():
            if not s["valid"]:
                role = s["role"]
                s_file = self._state_file(role)
                m_file = self._meta_file(role)
                if os.path.exists(s_file):
                    os.remove(s_file)
                if os.path.exists(m_file):
                    os.remove(m_file)
                pruned += 1
        return pruned


def main():
    parser = argparse.ArgumentParser(description="Enterprise Session State Vault CLI")
    subparsers = parser.add_subparsers(dest="command", help="Session vault subcommands")

    # save
    p_save = subparsers.add_parser("save", help="Save a session from a Playwright storageState JSON file")
    p_save.add_argument("--role", required=True, help="Session profile role identifier (e.g. 'admin')")
    p_save.add_argument("--file", required=True, help="Path to storageState.json file")
    p_save.add_argument("--ttl", type=int, default=3600, help="Session Time-to-Live in seconds (default: 3600)")

    # check
    p_check = subparsers.add_parser("check", help="Check validity of a stored session role")
    p_check.add_argument("--role", required=True, help="Session profile role identifier")

    # list
    subparsers.add_parser("list", help="List all stored sessions in the vault")

    # prune
    subparsers.add_parser("prune", help="Prune all expired sessions from the vault")

    args = parser.parse_args()
    vault = SessionVault()

    if args.command == "save":
        saved_path = vault.save_from_file(args.role, args.file, ttl_seconds=args.ttl)
        print(f"✅ Session for role '{args.role}' successfully saved to: {saved_path}")

    elif args.command == "check":
        valid, reason, meta = vault.validate_session(args.role)
        status_icon = "✅" if valid else "❌"
        print(f"{status_icon} Role '{args.role}': {reason}")
        if meta:
            print(f"   Created At: {meta.get('created_at')}")
            print(f"   Cookies   : {meta.get('cookie_count')}")
        sys.exit(0 if valid else 1)

    elif args.command == "list":
        sessions = vault.list_sessions()
        if not sessions:
            print("ℹ️ No session profiles currently stored in vault.")
            return
        print(f"{'ROLE':<15} {'STATUS':<10} {'COOKIES':<10} {'REASON'}")
        print("-" * 60)
        for s in sessions:
            st = "VALID" if s["valid"] else "EXPIRED"
            print(f"{s['role']:<15} {st:<10} {s['cookie_count']:<10} {s['reason']}")

    elif args.command == "prune":
        count = vault.prune_expired()
        print(f"🧹 Pruned {count} expired session(s) from vault.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
