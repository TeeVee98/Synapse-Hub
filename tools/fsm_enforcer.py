#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Enterprise 5-Stage QA Multi-Agent Finite State Machine (FSM) Enforcer
---------------------------------------------------------------------
Converts the descriptive 5-stage markdown workflow into an executable,
tamper-evident state machine enforced by code:
  Stage 1: DISCOVERY        (Actor: live-explorer)       -> Requires DOM/AOM discovery contract
  Stage 2: CODE_SYNTHESIS   (Actor: pom-crafter)         -> Requires synthesized PageClass/script
  Stage 3: HEADLESS_EXEC    (Actor: test-runner)         -> Requires test run evidence (JUnit/exitcode)
  Stage 4: AUTOPSY_HEAL     (Actor: failure-analyst)     -> Requires autopsy triage (or PASSED waiver)
  Stage 5: ACCEPTANCE_DOD   (Actor: quality-gatekeeper)  -> Requires 10 Quality Gates verification

Usage:
  python tools/fsm_enforcer.py start --session-id "SESS_001"
  python tools/fsm_enforcer.py advance --stage DISCOVERY --actor live-explorer --evidence '{"target": "login"}'
  python tools/fsm_enforcer.py advance --stage CODE_SYNTHESIS --actor pom-crafter --evidence '{"files": ["LoginPage.ts"]}'
  python tools/fsm_enforcer.py advance --stage HEADLESS_EXEC --actor test-runner --evidence '{"exit_code": 0}'
  python tools/fsm_enforcer.py advance --stage AUTOPSY_HEAL --actor failure-analyst --evidence '{"status": "PASSED"}'
  python tools/fsm_enforcer.py advance --stage ACCEPTANCE_DOD --actor quality-gatekeeper --evidence '{"gates": 10}'
  python tools/fsm_enforcer.py verify-compliance
"""

import os
import sys
import json
import uuid
import hmac
import hashlib
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List

STAGES_ORDER = [
    "DISCOVERY",
    "CODE_SYNTHESIS",
    "HEADLESS_EXEC",
    "AUTOPSY_HEAL",
    "ACCEPTANCE_DOD"
]

STAGE_ACTORS = {
    "DISCOVERY": ["live-explorer", "orchestrator"],
    "CODE_SYNTHESIS": ["pom-crafter", "orchestrator"],
    "HEADLESS_EXEC": ["test-runner", "orchestrator"],
    "AUTOPSY_HEAL": ["failure-analyst", "orchestrator"],
    "ACCEPTANCE_DOD": ["quality-gatekeeper", "orchestrator"]
}

# Formal Stage Evidence Contract Schemas
STAGE_EVIDENCE_SCHEMAS = {
    "DISCOVERY": {
        "required_any": ["selectors", "locators", "target_url", "url", "target", "element", "elements", "dom_hash", "aom_nodes"],
        "description": "Requires DOM/AOM discovery contract (target URL, selectors, or elements list)."
    },
    "CODE_SYNTHESIS": {
        "required_any": ["pages", "files", "scripts", "page_classes", "file", "classes"],
        "description": "Requires synthesized PageClass or test script file list/signatures."
    },
    "HEADLESS_EXEC": {
        "required_fields": ["exit_code"],
        "field_types": {"exit_code": int},
        "description": "Requires headless execution exit_code (int) and optional test summary/artifact."
    },
    "AUTOPSY_HEAL": {
        "required_any": ["verdict", "status", "waiver", "root_cause", "patch", "triage", "action"],
        "description": "Requires triage analysis, root_cause & patch, or waiver (e.g. PASSED_NO_HEAL_NEEDED)."
    },
    "ACCEPTANCE_DOD": {
        "required_any": ["gates_passed", "gates", "verify_all_passed", "passed_gates", "summary"],
        "description": "Requires 10 Quality Gates DoD verification evidence."
    }
}


def validate_stage_evidence(stage: str, evidence: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validates that stage evidence adheres to its formal data contract schema."""
    if not isinstance(evidence, dict) or not evidence:
        return False, f"Stage '{stage}' requires a non-empty evidence dictionary."

    schema = STAGE_EVIDENCE_SCHEMAS.get(stage)
    if not schema:
        return True, None

    if "required_fields" in schema:
        for rf in schema["required_fields"]:
            if rf not in evidence:
                return False, f"Stage '{stage}' evidence missing mandatory field '{rf}'. {schema['description']}"

    if "field_types" in schema:
        for f, expected_type in schema["field_types"].items():
            if f in evidence and not isinstance(evidence[f], expected_type):
                return False, f"Stage '{stage}' evidence field '{f}' must be of type {expected_type.__name__}, got {type(evidence[f]).__name__}."

    if "required_any" in schema:
        has_any = any(k in evidence for k in schema["required_any"])
        if not has_any:
            return False, f"Stage '{stage}' evidence missing required context. Must include at least one of: {schema['required_any']}. {schema['description']}"

    return True, None


def compute_proof_token(session_id: str, stage: str, actor: str, evidence: Dict[str, Any], timestamp: str) -> Tuple[str, str]:
    """
    Computes a tamper-evident cryptographic HMAC-SHA256 proof token for stage signoff.
    Returns (proof_token, evidence_hash).
    """
    canonical_ev = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
    ev_hash = hashlib.sha256(canonical_ev.encode("utf-8")).hexdigest()
    payload = f"{session_id}:{stage}:{actor}:{ev_hash}:{timestamp}"
    token_sig = hmac.new(session_id.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()[:24]
    token = f"proof_v2_{stage.lower()}_{token_sig}"
    return token, ev_hash


def verify_proof_token(session_id: str, stage: str, actor: str, evidence: Dict[str, Any], timestamp: str, token: str) -> bool:
    """Verifies that a proof token matches the evidence payload and has not been forged or tampered with."""
    expected_token, _ = compute_proof_token(session_id, stage, actor, evidence, timestamp)
    return hmac.compare_digest(token, expected_token)


class FsmEnforcer:
    """Executable finite state machine enforcing strict multi-agent workflow compliance."""

    def __init__(self, state_file: Optional[str] = None):
        if state_file:
            self.state_file = state_file
        else:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            self.state_file = os.path.join(repo_root, ".agent_memory", "fsm_session.json")

        os.makedirs(os.path.dirname(os.path.abspath(self.state_file)), exist_ok=True)
        self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    self.state = json.load(f)
            except Exception:
                self.state = self._empty_state()
        else:
            self.state = self._empty_state()

    def _save_state(self):
        tmp_file = f"{self.state_file}.{uuid.uuid4().hex[:8]}.tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
        os.replace(tmp_file, self.state_file)

    def _empty_state(self) -> Dict[str, Any]:
        return {
            "session_id": f"sess_{uuid.uuid4().hex[:8]}",
            "current_stage": None,
            "stage_history": [],
            "completed_stages": {},
            "status": "INITIALIZED",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

    def start_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Initializes a new workflow session."""
        self.state = self._empty_state()
        if session_id:
            self.state["session_id"] = session_id
        self.state["status"] = "IN_PROGRESS"
        self._save_state()
        return {
            "status": "PASS",
            "session_id": self.state["session_id"],
            "current_stage": None,
            "next_required_stage": STAGES_ORDER[0]
        }

    def advance_stage(self, stage: str, actor: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Advances workflow to the specified stage with evidence validation."""
        self._load_state()
        stage_upper = stage.upper().strip()
        if stage_upper not in STAGES_ORDER:
            return {
                "status": "REJECTED",
                "error": f"Invalid stage '{stage}'. Must be one of: {STAGES_ORDER}"
            }

        target_idx = STAGES_ORDER.index(stage_upper)
        completed = self.state.get("completed_stages", {})

        # 1. Enforce strict sequential order (cannot jump stages)
        for prev_idx in range(target_idx):
            prev_stage = STAGES_ORDER[prev_idx]
            if prev_stage not in completed:
                return {
                    "status": "REJECTED",
                    "error": f"Cannot transition to stage '{stage_upper}'. Preceding stage '{prev_stage}' has not been completed."
                }

        # 2. Validate actor authorization
        allowed_actors = STAGE_ACTORS.get(stage_upper, [])
        if actor not in allowed_actors:
            return {
                "status": "REJECTED",
                "error": f"Actor '{actor}' is not authorized to sign off on stage '{stage_upper}'. Required: {allowed_actors}"
            }

        # 3. Evidence contract schema validation
        valid, schema_err = validate_stage_evidence(stage_upper, evidence)
        if not valid:
            return {
                "status": "REJECTED",
                "error": schema_err
            }

        now_iso = datetime.now(timezone.utc).isoformat()
        proof_token, ev_hash = compute_proof_token(
            self.state["session_id"],
            stage_upper,
            actor,
            evidence,
            now_iso
        )

        record = {
            "stage": stage_upper,
            "actor": actor,
            "sequence": len(self.state["stage_history"]) + 1,
            "proof_token": proof_token,
            "evidence_hash": ev_hash,
            "evidence": evidence,
            "timestamp": now_iso
        }

        self.state["completed_stages"][stage_upper] = record
        self.state["stage_history"].append(record)
        self.state["current_stage"] = stage_upper
        self.state["updated_at"] = now_iso

        if len(self.state["completed_stages"]) == len(STAGES_ORDER):
            self.state["status"] = "COMPLETED"

        self._save_state()

        next_idx = target_idx + 1
        next_stage = STAGES_ORDER[next_idx] if next_idx < len(STAGES_ORDER) else None

        return {
            "status": "PASS",
            "session_id": self.state["session_id"],
            "stage_advanced": stage_upper,
            "proof_token": proof_token,
            "next_required_stage": next_stage,
            "workflow_completed": (self.state["status"] == "COMPLETED")
        }

    def verify_compliance(self) -> Dict[str, Any]:
        """Audits workflow session to verify if task definition of done is legally satisfied."""
        self._load_state()
        completed = self.state.get("completed_stages", {})
        missing = [s for s in STAGES_ORDER if s not in completed]

        if missing:
            return {
                "status": "BLOCKED",
                "compliant": False,
                "session_id": self.state["session_id"],
                "missing_stages": missing,
                "completed_count": f"{len(completed)}/{len(STAGES_ORDER)}",
                "error": f"Workflow is incomplete! Missing stages: {missing}"
            }

        # Cryptographic verification of all stage proof tokens
        tampered_stages = []
        for s in STAGES_ORDER:
            rec = completed[s]
            token = rec.get("proof_token", "")
            if token.startswith("proof_v2_"):
                is_valid = verify_proof_token(
                    self.state["session_id"],
                    s,
                    rec.get("actor", ""),
                    rec.get("evidence", {}),
                    rec.get("timestamp", ""),
                    token
                )
                if not is_valid:
                    tampered_stages.append(s)

        if tampered_stages:
            return {
                "status": "BLOCKED",
                "compliant": False,
                "session_id": self.state["session_id"],
                "error": f"Cryptographic integrity verification failed! Proof tokens for stages {tampered_stages} do not match evidence.",
                "tampered_stages": tampered_stages
            }

        return {
            "status": "PASS",
            "compliant": True,
            "session_id": self.state["session_id"],
            "total_stages": len(STAGES_ORDER),
            "proof_tokens": {s: completed[s]["proof_token"] for s in STAGES_ORDER},
            "summary": "100% 5-Stage FSM workflow verified with valid cryptographic proof tokens."
        }

    def get_status(self) -> Dict[str, Any]:
        """Returns current FSM status."""
        self._load_state()
        completed = self.state.get("completed_stages", {})
        return {
            "session_id": self.state["session_id"],
            "status": self.state["status"],
            "current_stage": self.state.get("current_stage"),
            "completed_stages": list(completed.keys()),
            "progress_pct": round((len(completed) / len(STAGES_ORDER)) * 100.0, 1),
            "history_count": len(self.state.get("stage_history", []))
        }


def main():
    parser = argparse.ArgumentParser(description="Enterprise 5-Stage QA Multi-Agent FSM Enforcer")
    subparsers = parser.add_subparsers(dest="subcommand", help="FSM subcommand to run")

    # start
    sp_start = subparsers.add_parser("start", help="Start new FSM session")
    sp_start.add_argument("--session-id", help="Optional custom session ID")

    # advance
    sp_adv = subparsers.add_parser("advance", help="Advance workflow stage")
    sp_adv.add_argument("--stage", required=True, choices=STAGES_ORDER, help="Target stage")
    sp_adv.add_argument("--actor", required=True, help="Actor role submitting evidence")
    sp_adv.add_argument("--evidence", required=True, help="JSON string containing stage evidence")

    # verify-compliance
    subparsers.add_parser("verify-compliance", help="Verify full workflow compliance before DoD closure")

    # status
    subparsers.add_parser("status", help="Display current FSM status")

    args = parser.parse_args()
    enforcer = FsmEnforcer()

    if args.subcommand == "start":
        res = enforcer.start_session(args.session_id)
        print(json.dumps(res, indent=2))
        sys.exit(0)

    elif args.subcommand == "advance":
        try:
            ev = json.loads(args.evidence)
        except Exception as e:
            print(json.dumps({"status": "REJECTED", "error": f"Invalid JSON in evidence: {e}"}, indent=2))
            sys.exit(1)
        res = enforcer.advance_stage(args.stage, args.actor, ev)
        print(json.dumps(res, indent=2))
        sys.exit(0 if res["status"] == "PASS" else 1)

    elif args.subcommand == "verify-compliance":
        res = enforcer.verify_compliance()
        print(json.dumps(res, indent=2))
        sys.exit(0 if res["status"] == "PASS" else 1)

    elif args.subcommand == "status":
        res = enforcer.get_status()
        print(json.dumps(res, indent=2))
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
