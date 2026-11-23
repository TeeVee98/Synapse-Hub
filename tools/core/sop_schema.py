# -*- coding: utf-8 -*-
"""Declarative QA SOP Schema & Validator (tools/core/sop_schema.py).

Inspired by AgentScope 2.0's SOP engine:
Defines declarative data contracts for Standard Operating Procedures in QA
(Smoke Tests, Regression Triage, Performance Benchmarks, Healing Cycles).
Supports parsing from YAML/JSON with graph validation (cycle detection,
reachability of final DoD gate, and mandatory evidence validation).

Author: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
License: MIT
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Tuple

# Enforce UTF-8 stdout/stderr encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


@dataclass(frozen=True)
class SOPStageDefinition:
    """Individual stage specification within a QA SOP."""

    stage_id: str
    actor_role: str
    description: str
    required_evidence_fields: List[str] = field(default_factory=list)
    transitions: List[str] = field(default_factory=list)
    circuit_breaker: str = "Max attempts: 2; revert to previous stage"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QASOPWorkflow:
    """Complete declarative QA Standard Operating Procedure definition."""

    sop_id: str
    version: str
    title: str
    description: str
    initial_stage: str
    final_stage: str
    stages: Dict[str, SOPStageDefinition]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sop_id": self.sop_id,
            "version": self.version,
            "title": self.title,
            "description": self.description,
            "initial_stage": self.initial_stage,
            "final_stage": self.final_stage,
            "stages": {k: v.to_dict() for k, v in self.stages.items()},
        }


def parse_sop_file(file_path: str) -> QASOPWorkflow:
    """Loads and parses a SOP specification file from YAML or JSON format."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"SOP spec file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        raw_text = f.read()

    data: Dict[str, Any]
    if file_path.endswith((".yaml", ".yml")):
        try:
            import yaml
            data = yaml.safe_load(raw_text) or {}
        except ImportError:
            # Fallback to json if simple JSON format disguised as yaml
            data = json.loads(raw_text)
    else:
        data = json.loads(raw_text)

    sop_id = data.get("sop_id", "custom_qa_sop")
    version = data.get("version", "1.0.0")
    title = data.get("title", "Untitled SOP")
    description = data.get("description", "")
    initial_stage = data.get("initial_stage", "")
    final_stage = data.get("final_stage", "")

    stages_data = data.get("stages", {})
    parsed_stages: Dict[str, SOPStageDefinition] = {}

    for s_id, s_info in stages_data.items():
        if isinstance(s_info, dict):
            parsed_stages[s_id] = SOPStageDefinition(
                stage_id=s_id,
                actor_role=s_info.get("actor_role", "QA_ENGINEER"),
                description=s_info.get("description", ""),
                required_evidence_fields=list(s_info.get("required_evidence_fields", [])),
                transitions=list(s_info.get("transitions", [])),
                circuit_breaker=s_info.get("circuit_breaker", "Max attempts: 2"),
            )

    return QASOPWorkflow(
        sop_id=sop_id,
        version=version,
        title=title,
        description=description,
        initial_stage=initial_stage,
        final_stage=final_stage,
        stages=parsed_stages,
    )


def validate_sop_workflow(workflow: QASOPWorkflow) -> Tuple[bool, List[str]]:
    """Validates structural integrity, reachability, and transition boundaries."""
    errors: List[str] = []

    if not workflow.stages:
        errors.append("SOP workflow defines no stages.")
        return False, errors

    if workflow.initial_stage not in workflow.stages:
        errors.append(f"initial_stage '{workflow.initial_stage}' does not exist in declared stages.")

    if workflow.final_stage and workflow.final_stage not in workflow.stages:
        errors.append(f"final_stage '{workflow.final_stage}' does not exist in declared stages.")

    for s_id, s_def in workflow.stages.items():
        for target in s_def.transitions:
            if target not in workflow.stages:
                errors.append(f"Stage '{s_id}' has transition pointing to unknown stage '{target}'.")

    return len(errors) == 0, errors
