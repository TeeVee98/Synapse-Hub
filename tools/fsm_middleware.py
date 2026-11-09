#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Runtime FSM Interceptor & Tool Proxy Middleware
------------------------------------------------
Provides dynamic precondition enforcement and runtime tool proxying connected
to the Enterprise 5-Stage Multi-Agent FSM (tools/fsm_enforcer.py):

Precondition Invariants:
  1. Before executing CODE_SYNTHESIS or mutating source/test code (write_to_file,
     replace_file_content), Stage 1 (DISCOVERY) MUST be completed with valid
     live DOM/AOM proof (selectors, locators, target_url, or aom_nodes).
  2. Before executing HEADLESS_EXEC or running tests, Stage 2 (CODE_SYNTHESIS)
     MUST be completed with registered Page Classes or test scripts.
  3. Before executing AUTOPSY_HEAL, Stage 3 (HEADLESS_EXEC) MUST have executed.
  4. Before declaring task completion or DoD signoff (finish_task, verify_all),
     Stages 1-4 MUST be completed and Stage 5 (ACCEPTANCE_DOD) verified.
  5. Read-only inspection tools (view_file, list_dir, grep_search) pass transparently.

Usage:
  python tools/fsm_middleware.py check-precondition --action write_to_file
  python tools/fsm_middleware.py intercept --tool write_to_file --params '{"TargetFile": "LoginPage.ts"}'
  python tools/fsm_middleware.py status
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, Callable

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from fsm_enforcer import FsmEnforcer, STAGES_ORDER


# Safe, read-only tools that never require stage prerequisites
READ_ONLY_TOOLS = {
    "view_file",
    "list_dir",
    "grep_search",
    "find_by_name",
    "read_url_content",
    "ask_question",
    "manage_task",
    "schedule",
    "search_web"
}

# Code modification tools subject to DISCOVERY gate
CODE_MUTATION_TOOLS = {
    "write_to_file",
    "replace_file_content",
    "create_file",
    "edit_file",
    "synthesize_code"
}

# Test execution tools subject to CODE_SYNTHESIS gate
TEST_EXECUTION_TOOLS = {
    "run_test",
    "execute_test",
    "test_runner",
    "run_pytest",
    "run_playwright",
    "run_katalon"
}

# Final completion actions subject to DoD gate
COMPLETION_ACTIONS = {
    "complete_task",
    "finish_task",
    "close_task",
    "verify_dod",
    "verify_compliance"
}


class FsmMiddleware:
    """Runtime Interceptor and Tool Proxy enforcing 5-Stage FSM Preconditions."""

    def __init__(self, enforcer: Optional[FsmEnforcer] = None, state_file: Optional[str] = None):
        if enforcer is not None:
            self.enforcer = enforcer
        else:
            self.enforcer = FsmEnforcer(state_file=state_file)

        self._custom_guards: Dict[str, Tuple[str, Optional[Callable[[Dict[str, Any]], Tuple[bool, Optional[str]]]]]] = {}

    def register_guard(
        self,
        tool_or_action: str,
        required_stage: str,
        custom_validator: Optional[Callable[[Dict[str, Any]], Tuple[bool, Optional[str]]]] = None
    ):
        """Registers a custom precondition guard for a specific tool or action name."""
        self._custom_guards[tool_or_action.lower()] = (required_stage.upper(), custom_validator)

    def is_read_only(self, tool_or_action: str) -> bool:
        """Determines whether a tool is pure read-only inspection."""
        return tool_or_action.lower() in READ_ONLY_TOOLS

    def is_circuit_breaker_active(self, ctx: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str]]:
        """
        Checks whether an emergency circuit breaker is active to bypass DISCOVERY gate
        when the live explorer or browser CDP process hangs or times out.
        """
        env_token = os.environ.get("SYNAPSE_CIRCUIT_BREAKER_OVERRIDE")
        if env_token:
            return True, f"Environment variable SYNAPSE_CIRCUIT_BREAKER_OVERRIDE is set ({env_token})"

        if ctx:
            ctx_token = ctx.get("circuit_breaker_override") or ctx.get("emergency_override_token")
            if ctx_token:
                return True, f"Context override token provided: {ctx_token}"

        self.enforcer._load_state()
        cb_state = self.enforcer.state.get("circuit_breaker", {})
        if cb_state.get("tripped", False):
            return True, cb_state.get("reason", "Live Explorer CDP timeout")

        return False, None

    def trip_circuit_breaker(self, reason: str = "Live Explorer CDP hung") -> Dict[str, Any]:
        """Trips the emergency circuit breaker, recording audit reason and timestamp."""
        self.enforcer._load_state()
        self.enforcer.state["circuit_breaker"] = {
            "tripped": True,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.enforcer._save_state()
        return self.enforcer.state["circuit_breaker"]

    def reset_circuit_breaker(self) -> Dict[str, Any]:
        """Resets the circuit breaker back to normal FSM enforcement mode."""
        self.enforcer._load_state()
        self.enforcer.state["circuit_breaker"] = {
            "tripped": False,
            "reason": None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.enforcer._save_state()
        return self.enforcer.state["circuit_breaker"]

    def check_precondition(
        self,
        action_or_tool: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluates whether an action or tool invocation satisfies FSM prerequisites.
        Returns (is_allowed, rejection_reason).
        """
        tool_clean = action_or_tool.strip().lower()
        ctx = context or {}

        # 1. Read-only inspection tools are always permitted
        if self.is_read_only(tool_clean):
            return True, None

        state = self.enforcer.get_status()
        completed = state.get("completed_stages", [])

        # 2. Check custom registered guards first
        if tool_clean in self._custom_guards:
            req_stage, custom_fn = self._custom_guards[tool_clean]
            if req_stage not in completed:
                return False, (
                    f"FSM Interceptor BLOCKED '{action_or_tool}': Requires Stage '{req_stage}' "
                    f"to be completed first. Current completed stages: {completed}."
                )
            if custom_fn:
                valid, err = custom_fn(ctx)
                if not valid:
                    return False, f"FSM Interceptor custom validation failed for '{action_or_tool}': {err}"
            return True, None

        # 3. Rule: Code Synthesis / Code Mutation requires DISCOVERY stage completed with DOM/AOM proof
        if tool_clean in CODE_MUTATION_TOOLS or tool_clean == "code_synthesis":
            # If target file is scratch or planning, allow pass-through
            target_file = ctx.get("TargetFile") or ctx.get("target_file") or ctx.get("file") or ""
            if any(target_file.endswith(ext) for ext in (".tmp", ".log", "task_plan.md", "findings.md", "progress.md")):
                return True, None

            # Emergency Circuit Breaker check
            cb_active, cb_reason = self.is_circuit_breaker_active(ctx)
            if cb_active:
                sys.stderr.write(
                    f"[CIRCUIT_BREAKER] Emergency override active: Stage 1 DISCOVERY gate bypassed for '{action_or_tool}' ({cb_reason}).\n"
                )
                return True, None

            if "DISCOVERY" not in completed:
                return False, (
                    f"FSM Interceptor BLOCKED '{action_or_tool}': Modifying code or synthesizing PageClasses/tests "
                    f"requires Stage 1 (DISCOVERY) to be signed off by actor 'live-explorer' with valid "
                    f"live DOM/AOM proof before touching code. Current completed stages: {completed}."
                )

            # Check that DISCOVERY evidence contained actual DOM/AOM evidence
            self.enforcer._load_state()
            disc_record = self.enforcer.state.get("completed_stages", {}).get("DISCOVERY", {})
            disc_evidence = disc_record.get("evidence", {})
            dom_keys = {"selectors", "locators", "target_url", "url", "target", "element", "elements", "dom_hash", "aom_nodes"}
            if not any(k in disc_evidence for k in dom_keys):
                return False, (
                    f"FSM Interceptor BLOCKED '{action_or_tool}': Stage 1 (DISCOVERY) evidence does not contain "
                    f"valid DOM/AOM contract data. Evidence recorded: {list(disc_evidence.keys())}."
                )

            return True, None

        # 4. Rule: Headless Execution / Test Running requires CODE_SYNTHESIS stage completed
        cmd_str = str(ctx.get("CommandLine") or ctx.get("command") or ctx.get("cmd") or "").strip().lower()
        is_cmd_test_runner = any(cmd_str.startswith(r) or f" {r} " in f" {cmd_str} " for r in (
            "pytest", "playwright", "npx playwright", "katalon", "npm test", "npm run test", "gradle test"
        ))

        if tool_clean in TEST_EXECUTION_TOOLS or tool_clean == "headless_exec" or is_cmd_test_runner:
            if "CODE_SYNTHESIS" not in completed:
                return False, (
                    f"FSM Interceptor BLOCKED '{action_or_tool}': Headless test execution requires Stage 2 (CODE_SYNTHESIS) "
                    f"to be signed off by actor 'pom-crafter' with synthesized Page Classes/scripts first. "
                    f"Current completed stages: {completed}."
                )
            return True, None

        # 5. Rule: Autopsy & Self-Healing requires HEADLESS_EXEC executed
        if tool_clean in {"autopsy_heal", "heal", "auto_heal", "diagnose_failure"}:
            if "HEADLESS_EXEC" not in completed:
                return False, (
                    f"FSM Interceptor BLOCKED '{action_or_tool}': Failure autopsy & healing requires Stage 3 (HEADLESS_EXEC) "
                    f"to have run first. Current completed stages: {completed}."
                )
            return True, None

        # 6. Rule: Stage 5 (ACCEPTANCE_DOD) execution requires Stages 1-4 completed
        if tool_clean == "acceptance_dod":
            missing_prior = [s for s in STAGES_ORDER[:4] if s not in completed]
            if missing_prior:
                return False, (
                    f"FSM Interceptor BLOCKED '{action_or_tool}': Entering Stage 5 (ACCEPTANCE_DOD) requires "
                    f"preceding stages {missing_prior} to be completed first. Current: {completed}."
                )
            return True, None

        # 7. Rule: Task Completion / DoD Gatekeeper requires stages 1-5 completed and full cryptographic compliance
        if tool_clean in COMPLETION_ACTIONS:
            missing_prior = [s for s in STAGES_ORDER if s not in completed]
            if missing_prior:
                return False, (
                    f"FSM Interceptor BLOCKED task completion '{action_or_tool}': Preceding stages {missing_prior} "
                    f"must be completed before final DoD signoff."
                )

            # Audit full compliance token integrity
            comp = self.enforcer.verify_compliance()
            if not comp.get("compliant", False):
                return False, (
                    f"FSM Interceptor BLOCKED task completion: Full 5-stage FSM DoD verification failed: "
                    f"{comp.get('error', 'Incomplete compliance verification')}."
                )
            return True, None

        # By default, unrecognized commands pass through with advisory notice
        return True, None

    def intercept(
        self,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None,
        handler: Optional[Callable[[Dict[str, Any]], Any]] = None
    ) -> Dict[str, Any]:
        """
        Intercepts a tool invocation. If preconditions pass, executes handler;
        otherwise intercepts and rejects immediately.
        """
        payload = params or {}
        allowed, reason = self.check_precondition(tool_name, payload)

        if not allowed:
            return {
                "status": "REJECTED_BY_FSM_INTERCEPTOR",
                "tool": tool_name,
                "error": reason,
                "precondition_passed": False
            }

        if handler is not None:
            try:
                result = handler(payload)
                return {
                    "status": "PASS",
                    "tool": tool_name,
                    "precondition_passed": True,
                    "result": result
                }
            except Exception as e:
                return {
                    "status": "EXECUTION_ERROR",
                    "tool": tool_name,
                    "precondition_passed": True,
                    "error": str(e)
                }

        return {
            "status": "PASS",
            "tool": tool_name,
            "precondition_passed": True,
            "message": f"Preconditions satisfied for '{tool_name}'."
        }


def main():
    parser = argparse.ArgumentParser(description="Runtime FSM Interceptor & Tool Proxy Middleware")
    subparsers = parser.add_subparsers(dest="subcommand", help="Command to run")

    # check-precondition
    sp_chk = subparsers.add_parser("check-precondition", help="Check if an action satisfies FSM preconditions")
    sp_chk.add_argument("--action", required=True, help="Tool or action name to evaluate")
    sp_chk.add_argument("--params", default="{}", help="Optional JSON parameters for the tool call")

    # intercept
    sp_int = subparsers.add_parser("intercept", help="Intercept tool invocation")
    sp_int.add_argument("--tool", required=True, help="Target tool name")
    sp_int.add_argument("--params", default="{}", help="JSON parameters")

    # status
    subparsers.add_parser("status", help="Get current FSM session and middleware status")

    # trip-circuit-breaker
    sp_trip = subparsers.add_parser("trip-circuit-breaker", help="Trip emergency circuit breaker to bypass DISCOVERY gate")
    sp_trip.add_argument("--reason", default="Live Explorer CDP hung", help="Reason for emergency bypass")

    # reset-circuit-breaker
    subparsers.add_parser("reset-circuit-breaker", help="Reset circuit breaker to normal FSM enforcement")

    args = parser.parse_args()
    middleware = FsmMiddleware()

    if args.subcommand == "check-precondition":
        try:
            params = json.loads(args.params)
        except Exception:
            params = {}
        allowed, reason = middleware.check_precondition(args.action, params)
        res = {
            "action": args.action,
            "allowed": allowed,
            "reason": reason
        }
        print(json.dumps(res, indent=2))
        sys.exit(0 if allowed else 1)

    elif args.subcommand == "intercept":
        try:
            params = json.loads(args.params)
        except Exception:
            params = {}
        res = middleware.intercept(args.tool, params)
        print(json.dumps(res, indent=2))
        sys.exit(0 if res.get("precondition_passed") else 1)

    elif args.subcommand == "status":
        status = middleware.enforcer.get_status()
        print(json.dumps(status, indent=2))
        sys.exit(0)

    elif args.subcommand == "trip-circuit-breaker":
        res = middleware.trip_circuit_breaker(reason=args.reason)
        print(json.dumps({"status": "CIRCUIT_BREAKER_TRIPPED", "details": res}, indent=2))
        sys.exit(0)

    elif args.subcommand == "reset-circuit-breaker":
        res = middleware.reset_circuit_breaker()
        print(json.dumps({"status": "CIRCUIT_BREAKER_RESET", "details": res}, indent=2))
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
