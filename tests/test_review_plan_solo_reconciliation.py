#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""4-Scenario Pytest Suite: Plan-vs-Solo Zero-Trust Review Auditor (M1).

Covers:
  1. Positive (TC-01): Clean /solo execution matching /super-plan contracts, HMAC receipts, and signed review receipt.
  2. Negative (TC-02, TC-03, TC-04): Plan drift & contract widening, tampered Red HMAC & post-Red test relaxation,
     mutation failure, broken downstream callers, and circular imports.
  3. Boundary (TC-05): Empty diff, no plan, corrupt/truncated receipt JSON, missing plan file, syntax error resilience.
  4. Resilience & Architectural Invariants: Zero solo_runner import (acyclic layering), milestone-scoped filtering,
     and strict verdict escalation.
"""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.orchestration.solo_contracts import compute_red_receipt_hmac
from tools.orchestration.plan_review_auditor import (
    CallerCompatibilityDTO,
    PlanReconciliationDTO,
    SoloProvenanceAuditDTO,
    UnifiedReviewReceiptDTO,
    _is_frozen_dataclass,
    _is_test_file,
    _parse_section1_targets,
    audit_plan_and_solo_execution,
    compute_review_verdict,
    sign_and_write_review_receipt,
    verify_review_receipt_hmac,
)


def _write_file(base: Path, rel_path: str, content: str) -> Path:
    target = base / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def _make_signed_red_receipt(
    repo_root: Path,
    test_rel_path: str,
    milestone_id: str = "M1",
    key: bytes = b"test-hmac-secret-key-0123456789abcdef",
) -> Dict[str, object]:
    test_file = repo_root / test_rel_path
    file_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()
    norm_rel = test_rel_path.replace("\\", "/")
    tree_body = f"{norm_rel}:{file_hash}\n"
    tree_hash = hashlib.sha256(tree_body.encode("utf-8")).hexdigest()
    payload: Dict[str, object] = {
        "status": "CERTIFIED_RED",
        "certified_at": "2026-11-26T10:00:00+00:00",
        "commit_hash": "deadbeef12345678",
        "normalized_cmd": f"python -m pytest {norm_rel}",
        "executed_tests": [norm_rel],
        "test_tree_hash": tree_hash,
        "test_files": {norm_rel: file_hash},
        "failure_sha256": "a" * 64,
        "ttl_seconds": 1800,
        "milestone_id": milestone_id,
    }
    payload["receipt_hmac"] = compute_red_receipt_hmac(payload, key=key)
    return payload


def _make_valid_plan_md() -> str:
    return """# Spec-Driven Implementation Plan: Sample Payment Service

## 1. Affected Files & Blast Radius

### Target Files & Structural Anchors
| Action | File Path & Structural Anchor | Scope & Responsibility |
|---|---|---|
| `[CREATE]` | `src/payment.py` (New) | Payment processing engine |
| `[CREATE]` | `tests/test_payment.py` (New) | Unit test suite |

## 2. Data Flow & Interface Signatures

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class PaymentResultDTO:
    tx_id: str
    amount: float
    approved: bool

def process_payment(tx_id: str, amount: float) -> PaymentResultDTO:
    ...
```

## 3. Atomic Milestones (Execution DAG)

### Milestone 1: Payment Engine
- **Node ID:** `M1` | **depends_on:** `[]`
- **Write Set:** `['src/payment.py', 'tests/test_payment.py']`
- **Pass Gate:** `python3 -m pytest tests/test_payment.py -q`

## 4. Verification Matrix ("Define the Exam in the Plan")

| ID | Test Scenario | Input / Precondition | Expected Output / Assertion | Verification Command |
|---|---|---|---|---|
| **TC-01** | Positive payment | Valid positive amount | Approved DTO | `python3 -m pytest tests/test_payment.py -k "test_process_payment_positive"` |
"""


# ==============================================================================
# 1. POSITIVE SCENARIO (TC-01)
# ==============================================================================


def test_positive_clean_solo_matches_super_plan(tmp_path: Path, monkeypatch):
    """Positive (TC-01): Clean /solo execution matching /super-plan returns APPROVED and 100% scores."""
    secret = "unit-test-review-hmac-secret-123456"
    monkeypatch.setenv("SYNAPSE_RECEIPT_HMAC_KEY", secret)

    _write_file(tmp_path, "plan.md", _make_valid_plan_md())
    _write_file(
        tmp_path,
        "src/payment.py",
        """from dataclasses import dataclass

@dataclass(frozen=True)
class PaymentResultDTO:
    tx_id: str
    amount: float
    approved: bool

def process_payment(tx_id: str, amount: float) -> PaymentResultDTO:
    return PaymentResultDTO(tx_id=tx_id, amount=amount, approved=amount > 0)
""",
    )
    _write_file(
        tmp_path,
        "tests/test_payment.py",
        """from src.payment import process_payment

def test_process_payment_positive():
    res = process_payment("TX-1", 42.5)
    assert res.approved is True
    assert res.amount == 42.5
""",
    )

    red_payload = _make_signed_red_receipt(
        tmp_path, "tests/test_payment.py", milestone_id="M1", key=secret.encode("utf-8")
    )
    _write_file(tmp_path, "reports/solo_receipts/M1_red.json", json.dumps(red_payload, indent=2))
    _write_file(
        tmp_path,
        "reports/solo_receipts/M1_mutation.json",
        json.dumps(
            {
                "status": "CERTIFIED_MUTATION",
                "passed": True,
                "mutation_score": 92.5,
                "required_threshold": 80.0,
                "killed": 37,
                "survived": 3,
                "target_details": {},
            }
        ),
    )
    _write_file(
        tmp_path,
        "decisions.tsv",
        "ts\tphase\tdecision\twhy\tevidence\tresult\n"
        "2026-11-26T10:00:00Z\tM1\tImplemented PaymentResultDTO\tPlan M1\ttests/test_payment.py\tPASS\n",
    )

    plan_dto, solo_dto, caller_dto, findings = audit_plan_and_solo_execution(
        repo_root=str(tmp_path),
        changed_files=["src/payment.py", "tests/test_payment.py"],
        diff_text="",
        plan_path="plan.md",
        milestone_id=None,
        strict_solo=True,
    )

    assert isinstance(plan_dto, PlanReconciliationDTO)
    assert plan_dto.passed is True
    assert plan_dto.alignment_score_pct == 100.0
    assert plan_dto.missing_planned_files == ()
    assert plan_dto.undeleted_files == ()
    assert plan_dto.unplanned_modified_files == ()
    assert plan_dto.drifted_contracts == ()
    assert plan_dto.missing_matrix_tests == ()

    assert isinstance(solo_dto, SoloProvenanceAuditDTO)
    assert solo_dto.solo_detected is True
    assert solo_dto.passed is True
    assert solo_dto.provenance_score_pct == 100.0
    assert solo_dto.decision_log_valid is True
    assert solo_dto.tampered_or_invalid_receipts == ()
    assert solo_dto.post_red_tampered_tests == ()
    assert solo_dto.mutation_scores.get("M1") == 92.5

    assert isinstance(caller_dto, CallerCompatibilityDTO)
    assert caller_dto.passed is True
    assert findings == []

    verdict, passed, exit_code = compute_review_verdict(findings, strict=False)
    assert verdict == "APPROVED"
    assert passed is True
    assert exit_code == 0

    receipt_path = tmp_path / "reports" / "code_review_receipt.json"
    receipt = sign_and_write_review_receipt(
        receipt_path=str(receipt_path),
        repo_root=str(tmp_path),
        verdict=verdict,
        passed=passed,
        target_scope="uncommitted",
        files_changed=2,
        must_fix_count=0,
        should_fix_count=0,
        nice_to_have_count=0,
        plan_reconciliation=plan_dto,
        solo_provenance=solo_dto,
        caller_compatibility=caller_dto,
    )
    assert isinstance(receipt, UnifiedReviewReceiptDTO)
    assert receipt.verdict == "APPROVED"
    assert len(receipt.receipt_hmac) == 64
    assert receipt_path.is_file()
    loaded = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert verify_review_receipt_hmac(loaded, key=secret.encode("utf-8")) is True

    # Verify all 4 DTOs enforce @dataclass(frozen=True) immutability
    with pytest.raises(FrozenInstanceError):
        plan_dto.passed = False  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        solo_dto.passed = False  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        caller_dto.passed = False  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        receipt.passed = False  # type: ignore[misc]


# ==============================================================================
# 2. NEGATIVE SCENARIOS (TC-02, TC-03, TC-04)
# ==============================================================================


def test_negative_plan_drift_and_missing_contracts(tmp_path: Path):
    """Negative (TC-02): Detects missing files, undeleted files, contract Any-widening, arity break, and tautology."""
    plan_md = """# Spec-Driven Implementation Plan: Drift Fixture

## 1. Affected Files & Blast Radius

| Action | File Path & Structural Anchor | Scope & Responsibility |
|---|---|---|
| `[CREATE]` | `src/missing_mod.py` (New) | Never created |
| `[DELETE]` | `src/legacy_old.py` (Delete) | Should have been removed |
| `[CREATE]` | `src/service.py` (New) | Core service |
| `[CREATE]` | `tests/test_service.py` (New) | Tests |

## 2. Data Flow & Interface Signatures

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class OrderDTO:
    order_id: str
    total: float

def submit_order(order_id: str, total: float) -> OrderDTO:
    ...
```

## 3. Atomic Milestones (Execution DAG)

### Milestone 1: Service
- **Node ID:** `M1` | **depends_on:** `[]`
- **Write Set:** `['src/missing_mod.py', 'src/legacy_old.py', 'src/service.py', 'tests/test_service.py']`

## 4. Verification Matrix ("Define the Exam in the Plan")

| ID | Test Scenario | Input / Precondition | Expected Output / Assertion | Verification Command |
|---|---|---|---|---|
| **TC-01** | Real behavior | Valid | Pass | `python3 -m pytest tests/test_service.py -k "test_real_behavior"` |
| **TC-02** | Tautology check | Bad | Catch | `python3 -m pytest tests/test_service.py -k "test_tautology"` |
"""
    _write_file(tmp_path, "plan.md", plan_md)
    _write_file(tmp_path, "src/legacy_old.py", "OLD = True\n")
    _write_file(
        tmp_path,
        "src/service.py",
        """from dataclasses import dataclass
from typing import Any

@dataclass
class OrderDTO:
    order_id: str
    total: Any

def submit_order(order_id: str) -> OrderDTO:
    return OrderDTO(order_id=order_id, total=0)
""",
    )
    _write_file(
        tmp_path,
        "tests/test_service.py",
        """def test_tautology():
    assert False
""",
    )
    _write_file(tmp_path, "src/unrelated_creep.py", "X = 1\n")

    plan_dto, _, _, findings = audit_plan_and_solo_execution(
        repo_root=str(tmp_path),
        changed_files=["src/service.py", "tests/test_service.py", "src/unrelated_creep.py"],
        diff_text="",
        plan_path="plan.md",
        strict_solo=False,
    )

    assert plan_dto is not None
    assert plan_dto.passed is False
    assert plan_dto.alignment_score_pct < 100.0
    assert "src/missing_mod.py" in plan_dto.missing_planned_files
    assert "src/legacy_old.py" in plan_dto.undeleted_files
    assert "src/unrelated_creep.py" in plan_dto.unplanned_modified_files
    assert len(plan_dto.drifted_contracts) >= 2
    assert len(plan_dto.missing_matrix_tests) >= 2

    codes = {f["code"] for f in findings}
    assert "UNIMPLEMENTED_PLANNED_FILES" in codes
    assert "UNDELETED_PLANNED_FILES" in codes
    assert "CONTRACT_SIGNATURE_DRIFT" in codes
    assert "UNFROZEN_DTO_CONTRACT" in codes
    assert "UNVERIFIED_MATRIX_SCENARIOS" in codes
    assert "UNPLANNED_SCOPE_CREEP" in codes

    verdict, passed, exit_code = compute_review_verdict(findings, strict=False)
    assert verdict == "CHANGES_REQUESTED"
    assert passed is False
    assert exit_code == 1


def test_negative_tampered_solo_receipt_and_post_red_edit(tmp_path: Path, monkeypatch):
    """Negative (TC-03): Flags forged HMAC, post-Red test file relaxation, failed mutation, and strict missing solo."""
    secret = "unit-test-tamper-hmac-secret-99999"
    monkeypatch.setenv("SYNAPSE_RECEIPT_HMAC_KEY", secret)

    # Case A: Forged HMAC in M1_red.json
    _write_file(tmp_path, "tests/test_alpha.py", "def test_a():\n    assert 1 + 1 == 2\n")
    forged = _make_signed_red_receipt(
        tmp_path, "tests/test_alpha.py", milestone_id="M1", key=secret.encode("utf-8")
    )
    forged["receipt_hmac"] = "0" * 64
    _write_file(tmp_path, "reports/solo_receipts/M1_red.json", json.dumps(forged))

    # Case B: Valid HMAC in M2_red.json, then test_beta.py edited AFTER Red certification
    _write_file(tmp_path, "tests/test_beta.py", "def test_b():\n    assert compute(2) == 4\n")
    valid_m2 = _make_signed_red_receipt(
        tmp_path, "tests/test_beta.py", milestone_id="M2", key=secret.encode("utf-8")
    )
    _write_file(tmp_path, "reports/solo_receipts/M2_red.json", json.dumps(valid_m2))
    # Tamper test_beta.py after Red receipt was signed
    _write_file(tmp_path, "tests/test_beta.py", "def test_b():\n    assert True\n")

    # Case C: Mutation receipt below threshold with survived mutants
    _write_file(
        tmp_path,
        "reports/solo_receipts/M2_mutation.json",
        json.dumps(
            {
                "status": "MUTATION_REJECTED",
                "passed": False,
                "mutation_score": 60.0,
                "required_threshold": 80.0,
                "survived": 2,
                "target_details": {
                    "src/beta.py": {
                        "survived_mutants": [
                            {"line": 12, "operator": "Gt->GtE", "description": "Boundary condition survived"}
                        ]
                    }
                },
            }
        ),
    )

    _, solo_dto, _, findings = audit_plan_and_solo_execution(
        repo_root=str(tmp_path),
        changed_files=["tests/test_alpha.py", "tests/test_beta.py"],
        diff_text="",
        plan_path=None,
        strict_solo=True,
    )

    assert solo_dto is not None
    assert solo_dto.solo_detected is True
    assert solo_dto.passed is False
    assert solo_dto.provenance_score_pct < 100.0
    assert any("M1_red.json" in r for r in solo_dto.tampered_or_invalid_receipts)
    assert "tests/test_beta.py" in solo_dto.post_red_tampered_tests
    assert solo_dto.mutation_scores.get("M2") == 60.0
    assert len(solo_dto.survived_mutant_summaries) >= 1

    codes = {f["code"] for f in findings}
    assert "TAMPERED_RED_RECEIPT" in codes
    assert "TEST_DRIFT_AFTER_RED" in codes
    assert "MUTATION_THRESHOLD_FAILED" in codes

    verdict, passed, exit_code = compute_review_verdict(findings, strict=False)
    assert verdict == "CHANGES_REQUESTED"
    assert passed is False
    assert exit_code == 1

    # Case D: strict_solo=True in empty repo with zero receipts -> MISSING_SOLO_RECEIPTS
    empty_repo = tmp_path / "empty_strict"
    empty_repo.mkdir()
    _, empty_solo, _, empty_findings = audit_plan_and_solo_execution(
        repo_root=str(empty_repo),
        changed_files=[],
        diff_text="",
        plan_path=None,
        strict_solo=True,
    )
    assert empty_solo is not None
    assert empty_solo.passed is False
    assert any(f["code"] == "MISSING_SOLO_RECEIPTS" for f in empty_findings)


def test_negative_broken_downstream_caller_and_cycle(tmp_path: Path):
    """Negative (TC-04): Detects broken downstream call sites beyond diff and circular imports."""
    _write_file(
        tmp_path,
        "src/client.py",
        """def connect(host: str) -> str:
    return f"tcp://{host}"
""",
    )
    _write_file(
        tmp_path,
        "src/service_b.py",
        """from src.client import connect

def boot() -> str:
    return connect("db.internal", timeout=5)
""",
    )
    _write_file(
        tmp_path,
        "src/cycle_a.py",
        """import src.cycle_b

def ping():
    return "a"
""",
    )
    _write_file(
        tmp_path,
        "src/cycle_b.py",
        """import src.cycle_a

def pong():
    return "b"
""",
    )

    sample_diff = """diff --git a/src/client.py b/src/client.py
--- a/src/client.py
+++ b/src/client.py
@@ -1,2 +1,2 @@
-def connect(host: str, timeout: int = 5) -> str:
+def connect(host: str) -> str:
     return f"tcp://{host}"
"""

    _, _, caller_dto, findings = audit_plan_and_solo_execution(
        repo_root=str(tmp_path),
        changed_files=["src/client.py", "src/cycle_a.py", "src/cycle_b.py"],
        diff_text=sample_diff,
        plan_path=None,
        strict_solo=False,
    )

    assert caller_dto.passed is False
    assert "connect" in caller_dto.modified_symbols
    assert any("service_b.py:4" in site for site in caller_dto.broken_call_sites)
    assert len(caller_dto.import_cycles) >= 1

    codes = {f["code"] for f in findings}
    assert "BROKEN_DOWNSTREAM_CALLER" in codes
    assert "CIRCULAR_IMPORT_DETECTED" in codes


# ==============================================================================
# 3. BOUNDARY SCENARIO (TC-05)
# ==============================================================================


def test_boundary_clean_diff_no_plan_and_corrupt_receipt(tmp_path: Path):
    """Boundary (TC-05): Clean diff without plan, corrupt JSON receipt, missing plan, and syntax errors never crash."""
    # 1. Clean empty repo, no plan, no diff
    plan_dto, solo_dto, caller_dto, findings = audit_plan_and_solo_execution(
        repo_root=str(tmp_path),
        changed_files=[],
        diff_text="",
        plan_path=None,
        strict_solo=False,
    )
    assert plan_dto is None
    assert solo_dto is None
    assert caller_dto.passed is True
    assert findings == []

    # 2. Corrupt / truncated JSON in reports/solo_receipts/M1_red.json
    _write_file(tmp_path, "reports/solo_receipts/M1_red.json", "{truncated_json...")
    _, solo_corrupt, _, findings_corrupt = audit_plan_and_solo_execution(
        repo_root=str(tmp_path),
        changed_files=[],
        diff_text="",
        plan_path=None,
        strict_solo=False,
    )
    assert solo_corrupt is not None
    assert solo_corrupt.passed is False
    assert any(f["code"] == "CORRUPT_SOLO_RECEIPT" for f in findings_corrupt)

    # 3. Missing plan file path + syntax-broken Python file
    _write_file(tmp_path, "src/broken.py", "def broken(:\n    pass\n")
    plan_missing, _, caller_syntax, findings_missing = audit_plan_and_solo_execution(
        repo_root=str(tmp_path),
        changed_files=["src/broken.py"],
        diff_text="",
        plan_path="non_existent_plan.md",
        strict_solo=False,
    )
    assert plan_missing is not None
    assert plan_missing.passed is False
    assert caller_syntax.passed is False
    codes = {f["code"] for f in findings_missing}
    assert "PLAN_FILE_NOT_FOUND" in codes
    assert "SYNTAX_ERROR" in codes


# ==============================================================================
# 4. RESILIENCE & ARCHITECTURAL INVARIANTS (ACYCLIC + MILESTONE SCOPING)
# ==============================================================================


def test_resilience_acyclic_imports_and_milestone_scoping(tmp_path: Path):
    """Resilience: plan_review_auditor never imports solo_runner; milestone scoping isolates M1 from M2."""
    auditor_path = Path(REPO_ROOT) / "tools" / "orchestration" / "plan_review_auditor.py"
    tree = ast.parse(auditor_path.read_text(encoding="utf-8"))
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
    assert not any("solo_runner" in m for m in imported_modules), (
        f"Circular import guard violated: plan_review_auditor imports solo_runner ({imported_modules})"
    )

    # Milestone scoping: M1 implemented, M2 not yet created -> scoping to M1 passes 100%
    plan_md = """# Spec-Driven Implementation Plan: Two Milestones

## 1. Affected Files & Blast Radius

| Action | File Path & Structural Anchor | Scope & Responsibility |
|---|---|---|
| `[CREATE]` | `src/m1.py` (New) | Milestone 1 |
| `[CREATE]` | `src/m2.py` (New) | Milestone 2 |

## 2. Data Flow & Interface Signatures

```python
def run_m1(val: int) -> int:
    ...
```

## 3. Atomic Milestones (Execution DAG)

### Milestone 1: First
- **Node ID:** `M1` | **depends_on:** `[]`
- **Write Set:** `['src/m1.py']`

### Milestone 2: Second
- **Node ID:** `M2` | **depends_on:** `[M1]`
- **Write Set:** `['src/m2.py']`

## 4. Verification Matrix

| ID | Test Scenario | Input / Precondition | Expected Output / Assertion | Verification Command |
|---|---|---|---|---|
"""
    _write_file(tmp_path, "plan.md", plan_md)
    _write_file(tmp_path, "src/m1.py", "def run_m1(val: int) -> int:\n    return val + 1\n")

    plan_dto, _, _, findings = audit_plan_and_solo_execution(
        repo_root=str(tmp_path),
        changed_files=["src/m1.py"],
        diff_text="",
        plan_path="plan.md",
        milestone_id="M1",
        strict_solo=False,
    )
    assert plan_dto is not None
    assert plan_dto.milestone_scope == "M1"
    assert plan_dto.passed is True
    assert "src/m2.py" not in plan_dto.missing_planned_files
    assert findings == []

    # Tiered verdict strict vs non-strict on Should fix
    should_only = [{"severity": "Should fix", "code": "UNPLANNED_SCOPE_CREEP", "title": "x"}]
    v_norm, p_norm, rc_norm = compute_review_verdict(should_only, strict=False)
    assert (v_norm, p_norm, rc_norm) == ("APPROVED_WITH_NOTES", True, 0)
    v_strict, p_strict, rc_strict = compute_review_verdict(should_only, strict=True)
    assert (v_strict, p_strict, rc_strict) == ("CHANGES_REQUESTED", False, 1)

    # Helper boundary assertions (test-path matching, Section 1 tags, frozen dataclass AST detection)
    for test_path in (
        "tests/unit.py",
        "pkg/tests/unit.py",
        "test_unit.py",
        "unit_test.py",
        "login.spec.ts",
        "login.test.js",
    ):
        assert _is_test_file(test_path) is True, f"Expected test path: {test_path}"
    assert _is_test_file("src/payment.py") is False

    cm, dl = _parse_section1_targets(
        "| `[CREATE]` | `src/new.py` | a |\n"
        "| `[MODIFY]` | `src/existing.py` | b |\n"
        "| `[DELETE]` | `src/old.py` | c |\n"
    )
    assert cm == ["src/new.py", "src/existing.py"]
    assert dl == ["src/old.py"]

    dc_tree = ast.parse(
        "@dataclass(frozen=True)\nclass A:\n    x: int\n"
        "@dataclasses.dataclass(frozen=True)\nclass B:\n    x: int\n"
        "@dataclass(frozen=False)\nclass C:\n    x: int\n"
        "@dataclass\nclass D:\n    x: int\n"
        "@other_dec(frozen=True)\nclass E:\n    x: int\n"
        "@mod.other_dec(frozen=True)\nclass F:\n    x: int\n"
        "class G:\n    x: int\n"
    )
    cls_nodes = {n.name: n for n in dc_tree.body if isinstance(n, ast.ClassDef)}
    assert _is_frozen_dataclass(cls_nodes["A"]) is True
    assert _is_frozen_dataclass(cls_nodes["B"]) is True
    assert _is_frozen_dataclass(cls_nodes["C"]) is False
    assert _is_frozen_dataclass(cls_nodes["D"]) is False
    assert _is_frozen_dataclass(cls_nodes["E"]) is False
    assert _is_frozen_dataclass(cls_nodes["F"]) is False
    assert _is_frozen_dataclass(cls_nodes["G"]) is False


def test_standalone_strict_solo_receipt_scoping_without_milestone_or_plan(tmp_path: Path, monkeypatch):
    """Standalone --strict-solo scoping: global tdd_red/mutation receipts isolate stale M* receipts without skipping tamper checks."""
    secret = "standalone-receipt-scope-hmac-secret-01"
    monkeypatch.setenv("SYNAPSE_RECEIPT_HMAC_KEY", secret)

    # 1. Positive: valid global tdd_red_receipt.json + tdd_mutation_receipt.json pass even if stale M1_* receipts exist
    pos_repo = tmp_path / "pos_global"
    _write_file(pos_repo, "src/new_mod.py", "def ok() -> int:\n    return 1\n")
    _write_file(pos_repo, "tests/test_new_mod.py", "from src.new_mod import ok\n\ndef test_ok():\n    assert ok() == 1\n")
    _write_file(pos_repo, "tests/test_old_task.py", "def test_old():\n    assert True\n")

    global_red = _make_signed_red_receipt(pos_repo, "tests/test_new_mod.py", milestone_id="global", key=secret.encode("utf-8"))
    global_red.pop("milestone_id", None)
    global_red["receipt_hmac"] = compute_red_receipt_hmac(global_red, key=secret.encode("utf-8"))
    _write_file(pos_repo, "reports/tdd_red_receipt.json", json.dumps(global_red))
    _write_file(
        pos_repo,
        "reports/tdd_mutation_receipt.json",
        json.dumps(
            {
                "status": "CERTIFIED_MUTATION",
                "passed": True,
                "mutation_score": 90.0,
                "required_threshold": 80.0,
                "targets_evaluated": ["src/new_mod.py"],
                "target_details": {},
            }
        ),
    )
    # Leftover stale/forged milestone receipts from a previous task in reports/solo_receipts/
    stale_m1 = _make_signed_red_receipt(pos_repo, "tests/test_old_task.py", milestone_id="M1", key=secret.encode("utf-8"))
    stale_m1["receipt_hmac"] = "f" * 64
    _write_file(pos_repo, "reports/solo_receipts/M1_red.json", json.dumps(stale_m1))
    _write_file(
        pos_repo,
        "reports/solo_receipts/M1_mutation.json",
        json.dumps({"status": "MUTATION_REJECTED", "passed": False, "mutation_score": 20.0, "required_threshold": 80.0}),
    )

    _, solo_pos, _, findings_pos = audit_plan_and_solo_execution(
        repo_root=str(pos_repo),
        changed_files=["src/new_mod.py", "tests/test_new_mod.py"],
        diff_text="",
        plan_path=None,
        milestone_id=None,
        strict_solo=True,
    )
    assert solo_pos is not None
    assert solo_pos.passed is True
    assert findings_pos == []

    # 2. Negative: tampered tdd_red_receipt.json still fails even if a valid leftover M1_red.json exists
    tamper_repo = tmp_path / "neg_tampered_global"
    _write_file(tamper_repo, "tests/test_new_mod.py", "def test_ok():\n    assert 1 == 1\n")
    _write_file(tamper_repo, "tests/test_old_task.py", "def test_old():\n    assert 2 == 2\n")
    bad_global = _make_signed_red_receipt(tamper_repo, "tests/test_new_mod.py", key=secret.encode("utf-8"))
    bad_global.pop("milestone_id", None)
    bad_global["receipt_hmac"] = "0" * 64
    _write_file(tamper_repo, "reports/tdd_red_receipt.json", json.dumps(bad_global))
    valid_old_m1 = _make_signed_red_receipt(tamper_repo, "tests/test_old_task.py", milestone_id="M1", key=secret.encode("utf-8"))
    _write_file(tamper_repo, "reports/solo_receipts/M1_red.json", json.dumps(valid_old_m1))

    _, solo_tamper, _, findings_tamper = audit_plan_and_solo_execution(
        repo_root=str(tamper_repo),
        changed_files=["tests/test_new_mod.py"],
        diff_text="",
        plan_path=None,
        milestone_id=None,
        strict_solo=True,
    )
    assert solo_tamper is not None
    assert solo_tamper.passed is False
    assert any(f["code"] == "TAMPERED_RED_RECEIPT" for f in findings_tamper)

    # 3. Negative: global mutation receipt without global Red receipt must fail (stale M1_red cannot mask missing Red)
    missing_red_repo = tmp_path / "neg_missing_global_red"
    _write_file(missing_red_repo, "tests/test_old_task.py", "def test_old():\n    assert 2 == 2\n")
    _write_file(
        missing_red_repo,
        "reports/tdd_mutation_receipt.json",
        json.dumps({"status": "CERTIFIED_MUTATION", "passed": True, "mutation_score": 95.0, "required_threshold": 80.0}),
    )
    valid_old_m1_2 = _make_signed_red_receipt(
        missing_red_repo, "tests/test_old_task.py", milestone_id="M1", key=secret.encode("utf-8")
    )
    _write_file(missing_red_repo, "reports/solo_receipts/M1_red.json", json.dumps(valid_old_m1_2))

    _, solo_missing_red, _, findings_missing_red = audit_plan_and_solo_execution(
        repo_root=str(missing_red_repo),
        changed_files=["src/new_mod.py"],
        diff_text="",
        plan_path=None,
        milestone_id=None,
        strict_solo=True,
    )
    assert solo_missing_red is not None
    assert solo_missing_red.passed is False
    assert any(f["code"] == "MISSING_SOLO_RECEIPTS" for f in findings_missing_red)
    verdict, passed, exit_code = compute_review_verdict(findings_missing_red, strict=False)
    assert (verdict, passed, exit_code) == ("CHANGES_REQUESTED", False, 1)

    # 4. Negative: no global receipts and only unrelated leftover M1_red.json -> skipped by changed_files -> MISSING_SOLO_RECEIPTS
    unrelated_repo = tmp_path / "neg_unrelated_m1"
    _write_file(unrelated_repo, "tests/test_old_task.py", "def test_old():\n    assert 2 == 2\n")
    valid_old_m1_3 = _make_signed_red_receipt(
        unrelated_repo, "tests/test_old_task.py", milestone_id="M1", key=secret.encode("utf-8")
    )
    _write_file(unrelated_repo, "reports/solo_receipts/M1_red.json", json.dumps(valid_old_m1_3))
    # Edit test_old_task.py later; unrelated to current diff on src/new_mod.py + tests/test_new_mod.py
    _write_file(unrelated_repo, "tests/test_old_task.py", "def test_old():\n    assert 3 == 3\n")

    _, solo_unrel, _, findings_unrel = audit_plan_and_solo_execution(
        repo_root=str(unrelated_repo),
        changed_files=["src/new_mod.py", "tests/test_new_mod.py"],
        diff_text="",
        plan_path=None,
        milestone_id=None,
        strict_solo=True,
    )
    assert solo_unrel is not None
    assert solo_unrel.passed is False
    codes_unrel = {f["code"] for f in findings_unrel}
    assert "MISSING_SOLO_RECEIPTS" in codes_unrel
    assert "TEST_DRIFT_AFTER_RED" not in codes_unrel

