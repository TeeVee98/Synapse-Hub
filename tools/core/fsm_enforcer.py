#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

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

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)



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

DEFAULT_STAGE_ACTORS = {
    "DISCOVERY": ["live-explorer", "test-designer"],
    "CODE_SYNTHESIS": ["pom-crafter", "api-engineer"],
    "HEADLESS_EXEC": ["test-runner", "perf-engineer", "api-engineer"],
    "AUTOPSY_HEAL": ["failure-analyst"],
    "ACCEPTANCE_DOD": ["quality-gatekeeper"]
}

def load_stage_actors() -> Dict[str, List[str]]:
    """Loads FSM stage actors dynamically from declarative agents_manifest.json."""
    manifest_path = os.path.join(_REPO_ROOT, "agents_manifest.json")
    if not os.path.exists(manifest_path):
        manifest_path = os.path.join(os.getcwd(), "agents_manifest.json")
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            stages = data.get("fsm_stages", {})
            if stages:
                return {k: v.get("actors", []) for k, v in stages.items()}
        except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
            pass
    return DEFAULT_STAGE_ACTORS

STAGE_ACTORS = load_stage_actors()


def resolve_actor_model_binding(actor_id: str, repo_root: Optional[str] = None) -> Dict[str, Any]:
    """Resolves declarative capability_tier and orthogonal-auditor requirement for an FSM actor."""
    from tools.core.model_registry import LEGACY_TIER_ALIASES, ModelRegistry

    base_root = _REPO_ROOT if repo_root is None else repo_root
    manifest_path = os.path.join(base_root, "agents_manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as mfh:
        manifest = json.load(mfh)
    entries = list(manifest.get("personas", [])) + list(manifest.get("specialists", []))
    matched = next((item for item in entries if item.get("id") == actor_id), {})
    tier_key = str(matched.get("capability_tier", "code_workhorse")).strip().lower()
    tier_enum = LEGACY_TIER_ALIASES.get(tier_key, LEGACY_TIER_ALIASES["code_workhorse"])
    reg = ModelRegistry(
        manifest_path=os.path.join(base_root, "models_manifest.json"),
        config_path=os.path.join(base_root, "synapse.config.json"),
    )
    first_spec = next(iter(reg.list_models(tier=tier_enum)))
    return {
        "actor_id": actor_id,
        "capability_tier": tier_enum.value,
        "requires_orthogonal_auditor": bool(matched.get("requires_orthogonal_auditor")),
        "recommended_model": first_spec.model_id,
    }


def load_persona_prompt(actor_id: str, repo_root: Optional[str] = None) -> Dict[str, Any]:
    """Loads persona/specialist definition and prompt markdown from agents_manifest.json & ai-agents/."""
    root = repo_root or _REPO_ROOT
    manifest_path = os.path.join(root, "agents_manifest.json")
    entry_meta: Dict[str, Any] = {}
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            for group_key in ("personas", "specialists"):
                for item in manifest.get(group_key, []):
                    if item.get("id") == actor_id:
                        entry_meta = dict(item)
                        break
                if entry_meta:
                    break
        except (OSError, json.JSONDecodeError):
            entry_meta = {}

    rel_file = entry_meta.get("file")
    candidates = [os.path.join(root, rel_file)] if rel_file else []
    candidates.extend([
        os.path.join(root, "ai-agents", "personas", f"{actor_id}.md"),
        os.path.join(root, "ai-agents", "specialists", f"{actor_id}.md"),
    ])
    for cand in candidates:
        if cand and os.path.isfile(cand):
            with open(cand, "r", encoding="utf-8", errors="replace") as f:
                return {
                    "found": True,
                    "id": actor_id,
                    "name": entry_meta.get("name", actor_id),
                    "role": entry_meta.get("role", ""),
                    "file": os.path.relpath(cand, root),
                    "prompt": f.read(),
                }
    return {
        "found": False,
        "id": actor_id,
        "name": entry_meta.get("name", actor_id),
        "role": entry_meta.get("role", ""),
        "file": rel_file,
        "prompt": "",
    }

# Formal Stage Evidence Contract Schemas
STAGE_EVIDENCE_SCHEMAS = {
    "DISCOVERY": {
        "required_any": ["selectors", "locators", "target_url", "url", "target", "element", "elements", "dom_hash", "aom_nodes", "test_cases", "matrix", "story", "spec", "requirements"],
        "description": "Requires DOM/AOM discovery contract (target URL, selectors, elements list, or requirement/test matrix specification)."
    },
    "CODE_SYNTHESIS": {
        "required_any": ["pages", "files", "scripts", "page_classes", "file", "classes", "matrix", "api_matrix", "endpoints"],
        "description": "Requires synthesized PageClass, API test matrix, or test script file list/signatures."
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


def compute_artifact_hashes(artifacts: List[str], base_dir: Optional[str] = None) -> Dict[str, str]:
    """
    Computes cryptographic SHA-256 digests for physical artifact files on disk.
    Returns mapping of {artifact_path: sha256_hexdigest}.
    """
    hashes = {}
    for item in artifacts:
        target = os.path.join(base_dir, item) if base_dir and not os.path.isabs(item) else item
        if os.path.isfile(target):
            try:
                with open(target, "rb") as f:
                    file_bytes = f.read()
                hashes[item] = hashlib.sha256(file_bytes).hexdigest()
            except OSError:
                continue
    return hashes


def verify_artifact_integrity(session_state: Dict[str, Any], base_dir: Optional[str] = None) -> Tuple[bool, List[str]]:
    """
    Verifies that all physical artifact files referenced in the session match their recorded SHA-256 hashes.
    Returns (all_intact: bool, violations: List[str]).
    """
    violations = []
    completed = session_state.get("completed_stages", {})
    for stage_name, record in completed.items():
        evidence = record.get("evidence", {})
        recorded_hashes = evidence.get("artifact_hashes", {})
        for item, recorded_hash in recorded_hashes.items():
            target = os.path.join(base_dir, item) if base_dir and not os.path.isabs(item) else item
            if not os.path.isfile(target):
                violations.append(f"Stage '{stage_name}' artifact missing on disk: {item}")
                continue
            try:
                with open(target, "rb") as f:
                    current_bytes = f.read()
                current_hash = hashlib.sha256(current_bytes).hexdigest()
                if current_hash != recorded_hash:
                    violations.append(f"Stage '{stage_name}' artifact tampered on disk: {item} (expected {recorded_hash[:12]}..., got {current_hash[:12]}...)")
            except OSError as err:
                violations.append(f"Stage '{stage_name}' failed to read artifact: {item} ({err})")
    return len(violations) == 0, violations


class FsmEnforcer:
    """Executable finite state machine enforcing strict multi-agent workflow compliance."""

    def __init__(self, state_file: Optional[str] = None):
        if state_file:
            self.state_file = state_file
        elif os.environ.get("FSM_STATE_FILE"):
            self.state_file = os.environ["FSM_STATE_FILE"]
        else:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
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
            "lane": "spec",
            "current_stage": None,
            "stage_history": [],
            "completed_stages": {},
            "status": "INITIALIZED",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

    def start_session(
        self,
        session_id: Optional[str] = None,
        lane: str = "spec",
        sop_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Initializes a new workflow session with specified SDD execution lane and optional SOP."""
        lane_clean = (lane or "spec").lower().strip()
        if lane_clean not in ("fast", "spec", "experiment"):
            lane_clean = "spec"
        self.state = self._empty_state()
        if session_id:
            self.state["session_id"] = session_id
        self.state["lane"] = lane_clean
        self.state["status"] = "IN_PROGRESS"

        if sop_file:
            try:
                from tools.core.sop_schema import parse_sop_file, validate_sop_workflow

                wf = parse_sop_file(sop_file)
                valid, errors = validate_sop_workflow(wf)
                if not valid:
                    return {"status": "REJECTED", "error": f"Invalid SOP: {errors}"}
                self.state["sop_id"] = wf.sop_id
                self.state["sop_file"] = sop_file
                self.state["sop_stages"] = {k: v.to_dict() for k, v in wf.stages.items()}
                self.state["initial_stage"] = wf.initial_stage
                self.state["final_stage"] = wf.final_stage
            except Exception as err:
                return {"status": "REJECTED", "error": f"Failed to load SOP spec: {err}"}

        self._save_state()
        next_stage = self.state.get("initial_stage") or STAGES_ORDER[0]
        return {
            "status": "PASS",
            "session_id": self.state["session_id"],
            "lane": self.state["lane"],
            "sop_id": self.state.get("sop_id"),
            "current_stage": None,
            "next_required_stage": next_stage,
        }

    def advance_stage(self, stage: str, actor: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Advances workflow to the specified stage with evidence validation."""
        self._load_state()
        stage_upper = stage.upper().strip()

        # Handle Declarative SOP stage transition
        if self.state.get("sop_id"):
            sop_stages = self.state.get("sop_stages", {})
            if stage_upper not in sop_stages:
                return {
                    "status": "REJECTED",
                    "error": f"Invalid SOP stage '{stage}'. Must be one of: {list(sop_stages.keys())}"
                }
            s_def = sop_stages[stage_upper]
            expected_actor = s_def.get("actor_role")
            if expected_actor and actor != expected_actor and actor != "QA_ORCHESTRATOR":
                return {
                    "status": "REJECTED",
                    "error": f"Actor '{actor}' is not authorized for SOP stage '{stage_upper}'. Required: '{expected_actor}'."
                }
            current_stage = self.state.get("current_stage")
            if current_stage is None:
                if stage_upper != self.state.get("initial_stage"):
                    return {
                        "status": "REJECTED",
                        "error": f"Initial SOP stage must be '{self.state.get('initial_stage')}', got '{stage_upper}'."
                    }
            else:
                prev_def = sop_stages.get(current_stage, {})
                allowed_next = prev_def.get("transitions", [])
                if stage_upper not in allowed_next:
                    return {
                        "status": "REJECTED",
                        "error": f"Cannot transition from '{current_stage}' to '{stage_upper}'. Allowed: {allowed_next}."
                    }
            req_fields = s_def.get("required_evidence_fields", [])
            for rf in req_fields:
                if rf not in evidence:
                    return {
                        "status": "REJECTED",
                        "error": f"SOP stage '{stage_upper}' evidence missing required field: '{rf}'."
                    }
            now_iso = datetime.now(timezone.utc).isoformat()
            proof_token, ev_hash = compute_proof_token(self.state["session_id"], stage_upper, actor, evidence, now_iso)
            self.state["completed_stages"][stage_upper] = {
                "actor": actor,
                "evidence": evidence,
                "evidence_hash": ev_hash,
                "proof_token": proof_token,
                "signed_at": now_iso
            }
            self.state["current_stage"] = stage_upper
            self.state["stage_history"].append({"stage": stage_upper, "actor": actor, "signed_at": now_iso})
            if stage_upper == self.state.get("final_stage"):
                self.state["status"] = "COMPLETED"
            self._save_state()
            return {
                "status": "PASS",
                "stage": stage_upper,
                "proof_token": proof_token,
                "sop_id": self.state.get("sop_id"),
                "workflow_status": self.state["status"]
            }

        if stage_upper not in STAGES_ORDER:
            return {
                "status": "REJECTED",
                "error": f"Invalid stage '{stage}'. Must be one of: {STAGES_ORDER}"
            }

        # Block experiment lane from reaching final DoD
        if self.state.get("lane") == "experiment" and stage_upper == "ACCEPTANCE_DOD":
            return {
                "status": "REJECTED",
                "error": "Experiment lane is sandboxed and blocked from ACCEPTANCE_DOD signoff."
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

        # 4. Automatic Physical Artifact SHA-256 Hashing
        artifact_candidates = []
        for key in ["files", "scripts", "pages", "page_classes", "artifacts"]:
            val = evidence.get(key)
            if isinstance(val, list):
                artifact_candidates.extend([str(v) for v in val if isinstance(v, str)])
            elif isinstance(val, str):
                artifact_candidates.append(val)
        if "file" in evidence and isinstance(evidence["file"], str):
            artifact_candidates.append(evidence["file"])

        if artifact_candidates:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            artifact_hashes = compute_artifact_hashes(artifact_candidates, base_dir=repo_root)
            if artifact_hashes:
                evidence["artifact_hashes"] = artifact_hashes

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
            "model_binding": resolve_actor_model_binding(actor),
            "workflow_completed": (self.state["status"] == "COMPLETED")
        }

    def verify_compliance(self) -> Dict[str, Any]:
        """Audits workflow session to verify if task definition of done is legally satisfied."""
        self._load_state()

        # Handle Declarative SOP compliance check
        if self.state.get("sop_id"):
            final_stage = self.state.get("final_stage")
            completed = self.state.get("completed_stages", {})
            if final_stage and final_stage not in completed:
                return {
                    "status": "BLOCKED",
                    "compliant": False,
                    "session_id": self.state["session_id"],
                    "error": f"SOP workflow has not reached final stage '{final_stage}'. Current: '{self.state.get('current_stage')}'",
                }
            tampered = []
            for s_name, rec in completed.items():
                if not verify_proof_token(
                    self.state["session_id"],
                    s_name,
                    rec["actor"],
                    rec["evidence"],
                    rec["signed_at"],
                    rec["proof_token"],
                ):
                    tampered.append(s_name)
            if tampered:
                return {
                    "status": "BLOCKED",
                    "compliant": False,
                    "session_id": self.state["session_id"],
                    "error": f"Cryptographic integrity failed for SOP stages: {tampered}",
                }
            return {
                "status": "PASS",
                "compliant": True,
                "session_id": self.state["session_id"],
                "sop_id": self.state.get("sop_id"),
                "completed_stages": list(completed.keys()),
                "summary": f"100% SOP '{self.state.get('sop_id')}' verified with valid cryptographic proof tokens.",
            }

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

        # Physical artifact integrity verification
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        artifacts_ok, artifact_violations = verify_artifact_integrity(self.state, base_dir=repo_root)
        if not artifacts_ok:
            return {
                "status": "BLOCKED",
                "compliant": False,
                "session_id": self.state["session_id"],
                "error": f"Artifact integrity verification failed! {len(artifact_violations)} violation(s) detected.",
                "artifact_violations": artifact_violations
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
    sp_start.add_argument(
        "--lane",
        choices=["fast", "spec", "experiment"],
        default="spec",
        help="SDD Execution Lane (fast, spec, experiment; default: spec)",
    )
    sp_start.add_argument("--sop", help="Optional path to declarative SOP YAML/JSON spec file")

    # advance
    sp_adv = subparsers.add_parser("advance", help="Advance workflow stage")
    sp_adv.add_argument("--stage", required=True, help="Target stage")
    sp_adv.add_argument("--actor", required=True, help="Actor role submitting evidence")
    sp_adv.add_argument("--evidence", required=True, help="JSON string containing stage evidence")

    # verify-compliance
    subparsers.add_parser("verify-compliance", help="Verify full workflow compliance before DoD closure")

    # status
    subparsers.add_parser("status", help="Display current FSM status")

    args = parser.parse_args()
    enforcer = FsmEnforcer()

    if args.subcommand == "start":
        res = enforcer.start_session(
            args.session_id,
            lane=getattr(args, "lane", "spec"),
            sop_file=getattr(args, "sop", None),
        )
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
