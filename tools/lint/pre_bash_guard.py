#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

r"""
tools/lint/pre_bash_guard.py — Active Defense-in-Depth Pre-Tool Shell Interceptor
---------------------------------------------------------------------------------
Defense-in-depth shell command analyzer complementing OS/IDE sandbox boundaries.
Tokenizes shell pipelines and subshells via shlex, normalizes short/long flags,
and unwraps nested shell invocations (bash -c, sh -c, eval) up to bounded depth.

Enforces:
  1. Destructive Filesystem & Permission Guard: Blocks recursive root/home deletions
     (rm -rf /, /*, ~, $HOME, find / -delete, chmod -R 777 /, mkfs, dd to /dev/*).
  2. Remote Code Execution & Secret Exfiltration Guard: Blocks curl/wget piped to shells
     and sensitive secret sources (.env, private keys, printenv) piped to network sinks.
  3. Position-Independent Git Branch Safety: Blocks force pushes (-f, --force,
     --force-with-lease, +refspec) targeting main/master/develop/release in any arg order.
  4. Scope Isolation & Rule 9 (Ask First): Blocks running target runners in Hub root and
     blocks unconfirmed test/BasePage deletions or npm/yarn/pnpm/pip/uv/poetry mutations.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
import re
import shlex
import sys
from typing import List, Optional, Set, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass

REPO_ROOT = _REPO_ROOT
MAX_WRAPPER_DEPTH = 4

TRANSPARENT_WRAPPERS = frozenset({"sudo", "command", "nohup", "nice", "time", "builtin"})
SHELL_BINARIES = frozenset({"sh", "bash", "zsh", "dash", "ksh"})
PROTECTED_BRANCHES = frozenset({"main", "master", "develop", "production", "release"})
NETWORK_SINKS = frozenset({"curl", "wget", "nc", "netcat", "ncat", "scp", "sftp", "ssh", "telnet", "socat"})

SENSITIVE_SECRET_RE = re.compile(
    r"(?:^|[/\s@\"'])(?:\.env(?:\.[a-zA-Z0-9_\-]+)?|id_rsa|id_ed25519|[^\s]*\.pem|[^\s]*\.key|credentials\.json)(?:$|[\s\"'])",
    re.IGNORECASE,
)
REMOTE_EXEC_PIPE_RE = re.compile(
    r"\b(?:curl|wget|fetch)\b[^;\n]*\|\s*(?:sudo\s+|env\s+)*(?:ba|z|da|k)?sh\b",
    re.IGNORECASE,
)
POWERSHELL_WIPE_RE = re.compile(
    r"\bRemove-Item\b.*-(?:Recurse|r)\b.*-(?:Force|f)\b.*[a-zA-Z]:|\brmdir\s+/[sS]\s+/[qQ]\s+[a-zA-Z]:",
    re.IGNORECASE,
)
SUBSHELL_EXTRACT_RE = re.compile(r"\$\(([^()]+)\)|`([^`]+)`")


@dataclass(frozen=True)
class ShellGuardVerdictDTO:
    """Tokenized shell command security verdict covering chained, piped, and nested invocations."""

    allowed: bool
    violation_code: str
    reason: str
    inspected_segments: int


def _split_shell_segments(cmd: str) -> List[Tuple[str, str]]:
    """Splits unquoted shell segments returning [(segment_text, trailing_operator), ...]."""
    segments: List[Tuple[str, str]] = []
    buf: List[str] = []
    in_single = False
    in_double = False
    i = 0
    n = len(cmd)
    while i < n:
        ch = cmd[i]
        if ch == "\\" and not in_single and i + 1 < n:
            buf.append(ch)
            buf.append(cmd[i + 1])
            i += 2
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            buf.append(ch)
            i += 1
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            buf.append(ch)
            i += 1
            continue
        if not in_single and not in_double:
            two = cmd[i:i + 2]
            if two in ("&&", "||"):
                segments.append(("".join(buf).strip(), two))
                buf = []
                i += 2
                continue
            if ch in (";", "|", "\n"):
                segments.append(("".join(buf).strip(), ch))
                buf = []
                i += 1
                continue
        buf.append(ch)
        i += 1
    if in_single or in_double:
        raise ValueError("Unbalanced quotes in shell command")
    tail = "".join(buf).strip()
    if tail:
        segments.append((tail, ""))
    return segments


def _unwrap_leading_tokens(tokens: List[str]) -> List[str]:
    """Strips leading VAR=val assignments and transparent command wrappers (sudo, env, nohup)."""
    idx = 0
    n = len(tokens)
    while idx < n:
        tok = tokens[idx]
        if "=" in tok and not tok.startswith("-") and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tok):
            idx += 1
            continue
        base = os.path.basename(tok).lower()
        if base == "env":
            idx += 1
            while idx < n and (tokens[idx].startswith("-") or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[idx])):
                idx += 1
            continue
        if base in TRANSPARENT_WRAPPERS:
            idx += 1
            while idx < n and tokens[idx].startswith("-"):
                # sudo -u root <cmd>
                if base == "sudo" and tokens[idx] in ("-u", "-g", "-C") and idx + 1 < n:
                    idx += 2
                else:
                    idx += 1
            continue
        break
    return tokens[idx:]


def _is_critical_root_or_home_path(raw_target: str) -> bool:
    """Returns True if raw_target points to filesystem root, wildcard root, home directory, or parent escape."""
    t = raw_target.strip().rstrip("/")
    if raw_target.strip() in ("/", "/*", "//"):
        return True
    if t in ("", "~", "$HOME", "${HOME}", "*", "..", "../..", ".git"):
        return True
    if raw_target.startswith(("~/", "$HOME/", "${HOME}/", "/*")):
        return True
    if re.match(r"^[a-zA-Z]:[/\\]?(\*)?$", raw_target.strip()):
        return True
    return False


def _extract_flags_and_positionals(args: List[str]) -> Tuple[Set[str], Set[str], List[str]]:
    """Returns (short_flags_chars, long_flags, positional_args) respecting '--' terminator."""
    short_flags: Set[str] = set()
    long_flags: Set[str] = set()
    positionals: List[str] = []
    after_double_dash = False
    for a in args:
        if after_double_dash:
            positionals.append(a)
        elif a == "--":
            after_double_dash = True
        elif a.startswith("--"):
            long_flags.add(a.split("=", 1)[0].lower())
        elif a.startswith("-") and len(a) > 1:
            for ch in a[1:]:
                short_flags.add(ch)
        else:
            positionals.append(a)
    return short_flags, long_flags, positionals


def _validate_pipeline_exfiltration(segments: List[Tuple[str, str]]) -> Optional[str]:
    """Detects secret reading piped into network sinks or direct curl @.env uploads."""
    saw_secret_source = False
    for seg_text, op in segments:
        if not seg_text:
            continue
        try:
            raw_tokens = shlex.split(seg_text, posix=True)
        except ValueError:
            return "SECURITY_VIOLATION: Malformed quoting in pipeline."
        tokens = _unwrap_leading_tokens(raw_tokens)
        if not tokens:
            continue
        binary = os.path.basename(tokens[0]).lower()
        joined = " ".join(tokens)

        # Direct secret upload e.g. curl -d @.env or curl -F file=@id_rsa
        if binary in NETWORK_SINKS and SENSITIVE_SECRET_RE.search(joined):
            return "SECURITY_VIOLATION: Direct network transmission of sensitive credential/env file is prohibited."

        if saw_secret_source and binary in NETWORK_SINKS:
            return "SECURITY_VIOLATION: Piping sensitive secrets/environment variables into an external network sink is prohibited."

        is_secret_reader = (
            binary in ("cat", "head", "tail", "less", "more", "grep", "awk", "sed", "base64", "xxd", "strings")
            and bool(SENSITIVE_SECRET_RE.search(joined))
        ) or binary in ("printenv",)
        if op == "|":
            saw_secret_source = saw_secret_source or is_secret_reader
        else:
            saw_secret_source = False
    return None


def _inspect_command_recursive(
    command: str,
    is_cwd_hub: bool,
    norm_cwd: str,
    user_confirmed: bool,
    depth: int = 0,
) -> Tuple[bool, str, int]:
    if depth > MAX_WRAPPER_DEPTH:
        return False, "SECURITY_VIOLATION: Excessive nested shell wrapper depth (> 4) rejected.", 1

    if REMOTE_EXEC_PIPE_RE.search(command):
        return False, "SECURITY_VIOLATION: Piping remote network content directly into a shell interpreter is strictly prohibited.", 1

    if POWERSHELL_WIPE_RE.search(command):
        return False, "SECURITY_VIOLATION: Dangerous recursive deletion of Windows drive root is strictly prohibited.", 1

    # Inspect embedded command substitutions $(...) and `...`
    for m_sub in SUBSHELL_EXTRACT_RE.finditer(command):
        sub_cmd = (m_sub.group(1) or m_sub.group(2) or "").strip()
        if sub_cmd:
            sub_ok, sub_reason, _ = _inspect_command_recursive(sub_cmd, is_cwd_hub, norm_cwd, user_confirmed, depth + 1)
            if not sub_ok:
                return False, sub_reason, 1

    try:
        segments = _split_shell_segments(command)
    except ValueError as exc:
        return False, f"SECURITY_VIOLATION: Fail-closed on malformed shell quoting ({exc}).", 1

    exfil_err = _validate_pipeline_exfiltration(segments)
    if exfil_err:
        return False, exfil_err, len(segments)

    inspected = 0
    for seg_text, _ in segments:
        if not seg_text:
            continue
        inspected += 1
        try:
            raw_tokens = shlex.split(seg_text, posix=True)
        except ValueError as exc:
            return False, f"SECURITY_VIOLATION: Fail-closed on malformed token quoting ({exc}).", inspected

        tokens = _unwrap_leading_tokens(raw_tokens)
        if not tokens:
            continue

        binary = os.path.basename(tokens[0]).lower()
        args = tokens[1:]

        # 0. Unwrap nested shell invocations: bash -c "...", sh -lc "...", eval "..."
        if binary in SHELL_BINARIES:
            for idx, arg in enumerate(args):
                if arg == "-c" or (arg.startswith("-") and not arg.startswith("--") and "c" in arg[1:]):
                    if idx + 1 < len(args):
                        ok_in, reason_in, sub_cnt = _inspect_command_recursive(
                            args[idx + 1], is_cwd_hub, norm_cwd, user_confirmed, depth + 1
                        )
                        inspected += sub_cnt
                        if not ok_in:
                            return False, reason_in, inspected
                    break
        elif binary == "eval" and args:
            ok_in, reason_in, sub_cnt = _inspect_command_recursive(
                " ".join(args), is_cwd_hub, norm_cwd, user_confirmed, depth + 1
            )
            inspected += sub_cnt
            if not ok_in:
                return False, reason_in, inspected

        # 1. Destructive filesystem & permission mutations
        if binary in ("rm", "del"):
            s_flags, l_flags, pos = _extract_flags_and_positionals(args)
            is_rec = ("r" in s_flags) or ("R" in s_flags) or ("--recursive" in l_flags) or ("/s" in [p.lower() for p in args])
            is_force = ("f" in s_flags) or ("F" in s_flags) or ("--force" in l_flags)
            if "--no-preserve-root" in l_flags:
                return False, "SECURITY_VIOLATION: 'rm --no-preserve-root' is strictly prohibited.", inspected
            if is_rec or is_force:
                for target in pos:
                    if _is_critical_root_or_home_path(target):
                        return False, f"SECURITY_VIOLATION: Dangerous recursive deletion of root or home target ('{target}') is strictly prohibited.", inspected
            if not user_confirmed:
                for target in pos:
                    if re.search(r"(?:^|[/\\])(?:BasePage|base_page)\b", target, re.IGNORECASE):
                        return False, (
                            "HUMAN_CONFIRMATION_REQUIRED: Deleting core BasePage classes "
                            "requires explicit user approval per Rule 9 (Ask First). Set SYNAPSE_USER_CONFIRMED=1 after confirmation."
                        ), inspected
                    if (is_rec or is_force) and re.search(r"(?:^|[/\\])(?:tests?|Scripts?|fixtures?|specs?)(?:$|[/\\])", target, re.IGNORECASE):
                        return False, (
                            "HUMAN_CONFIRMATION_REQUIRED: Bulk deletion of test suites or test fixtures "
                            "requires explicit user approval per Rule 9 (Ask First). Set SYNAPSE_USER_CONFIRMED=1 after confirmation."
                        ), inspected

        if binary == "find":
            has_delete = ("-delete" in args) or ("rm" in args and "-exec" in args)
            if has_delete:
                roots = [a for a in args if not a.startswith("-") and a not in ("!", "(", ")", ";", "+", "{}")]
                if not roots or any(_is_critical_root_or_home_path(r) for r in roots[:2]):
                    return False, "SECURITY_VIOLATION: Destructive 'find ... -delete' on root or home directory is strictly prohibited.", inspected

        if binary in ("chmod", "chown"):
            s_flags, l_flags, pos = _extract_flags_and_positionals(args)
            is_rec = ("R" in s_flags) or ("--recursive" in l_flags)
            has_777 = any(p in ("777", "0777", "a+rwx", "ugo+rwx") for p in pos)
            targets = pos[1:] if len(pos) >= 2 else pos
            if is_rec and (has_777 or any(_is_critical_root_or_home_path(t) for t in targets)):
                return False, "SECURITY_VIOLATION: Recursive chmod/chown 777 or root permission mutation is strictly prohibited.", inspected

        if binary.startswith("mkfs") or (binary == "dd" and any(a.startswith("of=/dev/") for a in args)):
            return False, "SECURITY_VIOLATION: Raw block-device formatting or disk overwrite is strictly prohibited.", inspected

        # 2. Position-Independent Git Force Push Guard
        if binary == "git" and args:
            # Skip git top-level flags like -C <dir> or -c k=v
            g_idx = 0
            while g_idx < len(args) and args[g_idx].startswith("-"):
                if args[g_idx] in ("-C", "-c", "--git-dir", "--work-tree") and g_idx + 1 < len(args):
                    g_idx += 2
                else:
                    g_idx += 1
            if g_idx < len(args) and args[g_idx] == "push":
                push_args = args[g_idx + 1:]
                s_flags, l_flags, pos = _extract_flags_and_positionals(push_args)
                has_force = (
                    ("f" in s_flags)
                    or any(lf.startswith("--force") for lf in l_flags)
                    or any(p.startswith("+") for p in pos)
                )
                if has_force:
                    # Check if any refspec mentions a protected branch (or no branch specified -> implicit upstream)
                    refspecs = pos[1:] if len(pos) >= 2 else []
                    targets_protected = (not refspecs) or any(
                        any(pb in ref.lstrip("+").split(":")[-1].lower() for pb in PROTECTED_BRANCHES)
                        for ref in refspecs
                    )
                    if targets_protected:
                        return False, "SAFETY_VIOLATION: Force push to protected branch (main/master/develop) is strictly prohibited by Git Push Protocol.", inspected

        # 3. Scope Isolation in Hub Root
        if is_cwd_hub:
            joined_seg = " ".join(tokens)
            hub_forbidden = [
                (re.compile(r"^(?:npx\s+)?playwright\s+test\b", re.IGNORECASE), "playwright test"),
                (re.compile(r"^(?:npx\s+)?cypress\s+(?:run|open)\b", re.IGNORECASE), "cypress run/open"),
                (re.compile(r"^mvn\s+test\b", re.IGNORECASE), "mvn test"),
                (re.compile(r"^gradle\s+test\b", re.IGNORECASE), "gradle test"),
            ]
            for pat, runner_name in hub_forbidden:
                if pat.search(joined_seg):
                    return False, (
                        f"SCOPE_VIOLATION: Attempted to run '{runner_name}' directly in Synapse-Hub root. "
                        "Synapse-Hub holds 0 business tests (Lesson Learned #7 & #8). "
                        "Identify target client project workspace and execute tests there."
                    ), inspected

        # 4. Oven Bun Debug Build Guard
        if binary == "bun" and args and args[0].lower() == "test" and os.path.exists(os.path.join(norm_cwd, "src", "bun.js")):
            return False, (
                "BUN_GUARD_VIOLATION: Never run 'bun test' directly in runtime development; "
                "it does not include local changes. Use 'bun bd test <file>' instead."
            ), inspected

        # 5. Rule 9 (Ask First): Unconfirmed External Dependency Mutations (JS & Python ecosystems)
        if not user_confirmed:
            benign_pkg_flags = {"--dry-run", "--help", "-h", "--version", "-v", "-V"}
            has_benign = any(a in benign_pkg_flags for a in args)
            is_js_pkg_mut = binary in ("npm", "yarn", "pnpm") and bool(args) and args[0].lower() in ("install", "i", "add", "remove", "uninstall") and len(args) >= 2
            is_py_pkg_mut = (
                (binary in ("pip", "pip3") and bool(args) and args[0].lower() in ("install", "uninstall") and len(args) >= 2)
                or (binary in ("python", "python3") and len(args) >= 3 and args[0] == "-m" and args[1] == "pip" and args[2].lower() in ("install", "uninstall"))
                or (binary == "uv" and len(args) >= 3 and args[0] == "pip" and args[1].lower() in ("install", "uninstall"))
                or (binary == "poetry" and bool(args) and args[0].lower() in ("add", "remove") and len(args) >= 2)
            )
            if (is_js_pkg_mut or is_py_pkg_mut) and not has_benign:
                return False, (
                    "HUMAN_CONFIRMATION_REQUIRED: Modifying external dependencies "
                    "requires explicit user approval per Rule 9 (Ask First). Set SYNAPSE_USER_CONFIRMED=1 after confirmation."
                ), inspected

    return True, "Command approved", max(1, inspected)


def normalize_and_inspect_shell(command: str, cwd: Optional[str] = None) -> ShellGuardVerdictDTO:
    """Structured entrypoint returning ShellGuardVerdictDTO."""
    if not command or not command.strip():
        return ShellGuardVerdictDTO(allowed=True, violation_code="NONE", reason="Empty command", inspected_segments=0)

    norm_cwd = os.path.abspath(cwd or os.getcwd()).replace("\\", "/")
    norm_hub = REPO_ROOT.replace("\\", "/")
    is_cwd_hub = norm_cwd == norm_hub
    user_confirmed = os.environ.get("SYNAPSE_USER_CONFIRMED", "0") == "1"

    ok, reason, segs = _inspect_command_recursive(
        command.strip(),
        is_cwd_hub=is_cwd_hub,
        norm_cwd=norm_cwd,
        user_confirmed=user_confirmed,
        depth=0,
    )
    code = "NONE" if ok else reason.split(":", 1)[0].strip()
    return ShellGuardVerdictDTO(allowed=ok, violation_code=code, reason=reason, inspected_segments=segs)


def validate_shell_command(command: str, cwd: Optional[str] = None) -> Tuple[bool, str]:
    """
    Inspects and validates a shell command string before execution.
    Returns (True, "Command approved") or (False, "Violation reason").
    """
    verdict = normalize_and_inspect_shell(command, cwd=cwd)
    return verdict.allowed, verdict.reason


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Active Defense-in-Depth Pre-Tool Shell Guard"
    )
    parser.add_argument("command", help="Shell command string to validate")
    parser.add_argument("--cwd", default=None, help="Working directory context for execution")
    parser.add_argument("--json", action="store_true", help="Output validation result in JSON format")
    args = parser.parse_args()

    ok, reason = validate_shell_command(args.command, cwd=args.cwd)
    if args.json:
        import json
        output = {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow" if ok else "deny",
            "permissionDecisionReason": reason,
            "command": args.command,
            "cwd": args.cwd or os.getcwd(),
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        if ok:
            print(f"[PASS] Pre-Tool Shell Guard: {reason}")
        else:
            print(f"[DENY] Pre-Tool Shell Guard: {reason}", file=sys.stderr)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
