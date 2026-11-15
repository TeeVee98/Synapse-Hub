#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) Cloudflare, Inc.
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Adapted from cloudflare/security-audit-skill for Synapse-Hub Enterprise QA.

"""
Mathematical Security Coverage Ledger & Audit Tracker
-----------------------------------------------------
Manages and verifies formal audit coverage units across enterprise codebases:
  Coverage Unit = Surface × Boundary × Subsystem × Attack Class [× Lifecycle]

Features:
  1. RFC 3986 deterministic percent-encoded canonical coverage IDs.
  2. Mathematical state tracking (planned, in_progress, covered, candidate, blocked, deferred, not_applicable, out_of_scope).
  3. Full 19-field Cloudflare-compatible CoverageUnit schema.
  4. Strict state machine invariant validation without external dependencies.
  5. Dual document format support: top-level JSON array [...] and object {"units": [...]}.
  6. Mathematical coverage and blocker rate metrics.
  7. Safe identifier enforcement (anti-injection, Windows reserved device checks).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Enforce UTF-8 output encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

VALID_STATUSES = {
    "planned",
    "in_progress",
    "covered",
    "candidate",
    "blocked",
    "deferred",
    "out_of_scope",
    "not_applicable",
}

WINDOWS_RESERVED_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    "com1",
    "com2",
    "com3",
    "com4",
    "com5",
    "com6",
    "com7",
    "com8",
    "com9",
    "lpt1",
    "lpt2",
    "lpt3",
    "lpt4",
    "lpt5",
    "lpt6",
    "lpt7",
    "lpt8",
    "lpt9",
}

SAFE_ID_REGEX = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$", re.IGNORECASE)


def encode_canonical_ref(val: str) -> str:
    """RFC 3986 percent encoding: unreserved [A-Za-z0-9-._~] preserved, uppercase %XX for others."""
    s = str(val).strip()
    return urllib.parse.quote(s, safe="-._~")


@dataclass
class CoverageUnit:
    coverage_id: str = ""
    surface: str = ""
    boundary: str = ""
    subsystem: str = ""
    attack_class: str = ""
    status: str = "planned"
    wave: int = 1
    agent_id: Optional[str] = None
    canonical_refs: Optional[Dict[str, str]] = None
    starting_paths: List[str] = field(default_factory=list)
    ordinary_attack_class_block: str = "ordinary"
    selected_companion_blocks: List[str] = field(default_factory=list)
    excluded_blocks: List[str] = field(default_factory=list)
    prior_status: Optional[str] = None
    attempts: int = 0
    reviewed_paths: List[str] = field(default_factory=list)
    local_checks: List[str] = field(default_factory=list)
    result_fingerprints: List[str] = field(default_factory=list)
    unresolved: List[str] = field(default_factory=list)
    lifecycle: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self):
        if self.canonical_refs is None:
            refs = {
                "surface": self.surface,
                "boundary": self.boundary,
                "subsystem": self.subsystem,
                "attack_class": self.attack_class,
            }
            if self.lifecycle:
                refs["lifecycle"] = self.lifecycle
            self.canonical_refs = refs

        if not self.coverage_id:
            self.coverage_id = CoverageLedgerManager.canonical_id(
                self.surface, self.boundary, self.subsystem, self.attack_class, lifecycle=self.lifecycle
            )


class CoverageLedgerManager:
    """Manages and validates coverage-ledger.json with mathematical rigor."""

    def __init__(self, ledger_path: Path | str):
        self.ledger_path = Path(ledger_path)
        self.units: List[CoverageUnit] = []
        self.format: str = "object"  # 'object' | 'array'
        if self.ledger_path.exists():
            self.load()

    @staticmethod
    def canonical_id(
        surface: str,
        boundary: str,
        subsystem: str,
        attack_class: str,
        lifecycle: Optional[str] = None,
    ) -> str:
        """Construct canonical deterministic coverage ID using RFC 3986 encoding."""
        parts = [
            encode_canonical_ref(s)
            for s in (surface, boundary, subsystem, attack_class)
        ]
        if lifecycle:
            parts.append(encode_canonical_ref(lifecycle))
        return "::".join(parts)

    def load(self) -> None:
        """Load and parse ledger JSON supporting both array and object formats."""
        try:
            content = self.ledger_path.read_text(encoding="utf-8")
            raw = json.loads(content)
            if isinstance(raw, list):
                self.format = "array"
                units_data = raw
            elif isinstance(raw, dict):
                self.format = "object"
                units_data = raw.get("units", [])
            else:
                raise ValueError("Expected JSON array or object with 'units'")

            if not isinstance(units_data, list):
                raise ValueError("Expected 'units' to be a list")

            parsed: List[CoverageUnit] = []
            for u in units_data:
                if not isinstance(u, dict):
                    continue
                # Filter out unknown keys safely
                unit_args = {
                    k: v
                    for k, v in u.items()
                    if k in CoverageUnit.__dataclass_fields__
                }
                parsed.append(CoverageUnit(**unit_args))
            self.units = parsed
        except (json.JSONDecodeError, OSError, ValueError, TypeError, AttributeError) as err:
            sys.stderr.write(f"[LEDGER] Error reading ledger file: {err}\n")
            self.units = []

    def save(self, format_type: Optional[str] = None) -> None:
        """Write units to ledger file with deterministic sorting and chosen format."""
        fmt = format_type or self.format
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        sorted_units = sorted(self.units, key=lambda u: u.coverage_id)
        units_dicts = [asdict(u) for u in sorted_units]

        if fmt == "array":
            content = json.dumps(units_dicts, indent=2, ensure_ascii=False)
        else:
            payload = {
                "$schema": "synapse://schemas/v1/coverage-ledger.json",
                "total_units": len(sorted_units),
                "units": units_dicts,
            }
            content = json.dumps(payload, indent=2, ensure_ascii=False)

        self.ledger_path.write_text(content, encoding="utf-8")

    def add_unit(
        self,
        surface: str,
        boundary: str,
        subsystem: str,
        attack_class: str,
        lifecycle: Optional[str] = None,
        wave: int = 1,
        agent_id: Optional[str] = None,
        status: str = "planned",
        reviewed_paths: Optional[List[str]] = None,
        local_checks: Optional[List[str]] = None,
        result_fingerprints: Optional[List[str]] = None,
        unresolved: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> CoverageUnit:
        """Add or update a coverage unit."""
        cov_id = self.canonical_id(
            surface, boundary, subsystem, attack_class, lifecycle=lifecycle
        )
        for existing in self.units:
            if existing.coverage_id == cov_id:
                if wave != 1:
                    existing.wave = wave
                if agent_id is not None:
                    existing.agent_id = agent_id
                if status != "planned":
                    existing.status = status
                if reviewed_paths is not None and len(reviewed_paths) > 0:
                    existing.reviewed_paths = reviewed_paths
                if local_checks is not None and len(local_checks) > 0:
                    existing.local_checks = local_checks
                if result_fingerprints is not None and len(result_fingerprints) > 0:
                    existing.result_fingerprints = result_fingerprints
                if unresolved is not None and len(unresolved) > 0:
                    existing.unresolved = unresolved
                if notes is not None:
                    existing.notes = notes
                self.save()
                return existing

        refs = {
            "surface": surface,
            "boundary": boundary,
            "subsystem": subsystem,
            "attack_class": attack_class,
        }
        if lifecycle:
            refs["lifecycle"] = lifecycle

        unit = CoverageUnit(
            coverage_id=cov_id,
            surface=surface,
            boundary=boundary,
            subsystem=subsystem,
            attack_class=attack_class,
            status=status,
            wave=wave,
            agent_id=agent_id,
            canonical_refs=refs,
            reviewed_paths=reviewed_paths or [],
            local_checks=local_checks or [],
            result_fingerprints=result_fingerprints or [],
            unresolved=unresolved or [],
            lifecycle=lifecycle,
            notes=notes,
        )
        self.units.append(unit)
        self.save()
        return unit

    def validate(self) -> List[str]:
        """Validate all units against strict state machine and security invariants."""
        errors: List[str] = []
        seen_ids: Set[str] = set()

        if len(self.units) > 10000:
            errors.append("Ledger exceeds maximum limit of 10,000 units.")

        for idx, u in enumerate(self.units, start=1):
            base_label = f"Unit #{idx} ('{u.coverage_id}')"

            # Check unique ID
            if u.coverage_id in seen_ids:
                errors.append(f"{base_label}: Duplicate coverage_id.")
            seen_ids.add(u.coverage_id)

            # Check status validity
            if u.status not in VALID_STATUSES:
                errors.append(
                    f"{base_label}: Invalid status '{u.status}'. Allowed: {sorted(list(VALID_STATUSES))}"
                )
                continue

            # Check wave validity
            if not isinstance(u.wave, int) or isinstance(u.wave, bool) or u.wave < 1:
                errors.append(
                    f"{base_label}: Invalid wave '{u.wave}'. Wave must be an integer >= 1."
                )

            # Check agent_id safety
            if u.agent_id:
                agent_lower = u.agent_id.strip().lower()
                if agent_lower in WINDOWS_RESERVED_NAMES:
                    errors.append(
                        f"{base_label}: agent_id '{u.agent_id}' is a Windows reserved device name."
                    )
                if not SAFE_ID_REGEX.match(u.agent_id):
                    errors.append(
                        f"{base_label}: agent_id '{u.agent_id}' contains invalid characters."
                    )

            # Check canonical consistency
            expected_id = self.canonical_id(
                u.surface, u.boundary, u.subsystem, u.attack_class, lifecycle=u.lifecycle
            )
            if u.coverage_id != expected_id:
                errors.append(
                    f"{base_label}: ID does not match RFC 3986 canonical formula '{expected_id}'"
                )

            # Check result_fingerprints exclusivity (only 'candidate' units can have fingerprints)
            if u.status != "candidate" and u.result_fingerprints:
                errors.append(
                    f"{base_label}: Unit with status '{u.status}' must have empty result_fingerprints."
                )

            # State Machine Invariant Verification
            if u.status == "planned":
                if u.agent_id is not None:
                    errors.append(f"{base_label}: Planned unit must be unassigned (agent_id must be None).")
                if u.reviewed_paths:
                    errors.append(f"{base_label}: Planned unit must have empty reviewed_paths.")
                if u.local_checks:
                    errors.append(f"{base_label}: Planned unit must have empty local_checks.")
                if u.unresolved:
                    errors.append(f"{base_label}: Planned unit must have empty unresolved list.")

            elif u.status == "in_progress":
                if not u.agent_id:
                    errors.append(f"{base_label}: In-progress unit requires an assigned agent_id.")
                if u.reviewed_paths:
                    errors.append(f"{base_label}: In-progress unit must have empty reviewed_paths before completion.")
                if u.local_checks:
                    errors.append(f"{base_label}: In-progress unit must have empty local_checks before completion.")
                if u.unresolved:
                    errors.append(f"{base_label}: In-progress unit must have empty unresolved list.")

            elif u.status == "covered":
                if not u.agent_id:
                    errors.append(f"{base_label}: Covered unit requires an assigned agent_id.")
                if not u.reviewed_paths:
                    errors.append(f"{base_label}: Covered unit requires non-empty reviewed_paths.")
                if not u.local_checks:
                    errors.append(f"{base_label}: Covered unit requires non-empty local_checks.")
                if u.unresolved:
                    errors.append(f"{base_label}: Covered unit must have empty unresolved list.")

            elif u.status == "candidate":
                if not u.agent_id:
                    errors.append(f"{base_label}: Candidate finding unit requires an assigned agent_id.")
                if not u.reviewed_paths:
                    errors.append(f"{base_label}: Candidate finding unit requires non-empty reviewed_paths.")
                if not u.local_checks:
                    errors.append(f"{base_label}: Candidate finding unit requires non-empty local_checks.")
                if not u.result_fingerprints:
                    errors.append(f"{base_label}: Candidate finding unit requires non-empty result_fingerprints.")

            elif u.status == "blocked":
                if not u.agent_id:
                    errors.append(f"{base_label}: Blocked unit requires an assigned agent_id.")
                if not u.reviewed_paths:
                    errors.append(f"{base_label}: Blocked unit requires reviewed_paths to establish blockage context.")
                if not u.local_checks:
                    errors.append(f"{base_label}: Blocked unit requires local_checks to establish blockage context.")
                if not u.unresolved:
                    errors.append(f"{base_label}: Blocked unit requires non-empty unresolved explanations.")

            elif u.status in {"deferred", "out_of_scope", "not_applicable"}:
                if u.agent_id is not None:
                    errors.append(f"{base_label}: Unit with status '{u.status}' must be unassigned.")
                if u.reviewed_paths:
                    errors.append(f"{base_label}: Unit with status '{u.status}' must have empty reviewed_paths.")
                if u.local_checks:
                    errors.append(f"{base_label}: Unit with status '{u.status}' must have empty local_checks.")
                if not u.unresolved:
                    errors.append(f"{base_label}: Unit with status '{u.status}' must state reason in unresolved list.")

        return errors

    def get_metrics(self) -> Dict[str, Any]:
        """Compute mathematical coverage metrics across all units."""
        total = len(self.units)
        status_counts = {s: 0 for s in VALID_STATUSES}
        wave_counts: Dict[int, int] = {}

        for u in self.units:
            status_counts[u.status] = status_counts.get(u.status, 0) + 1
            wave_counts[u.wave] = wave_counts.get(u.wave, 0) + 1

        out_of_scope = status_counts.get("out_of_scope", 0)
        not_applicable = status_counts.get("not_applicable", 0)
        in_scope = total - out_of_scope - not_applicable

        covered = status_counts.get("covered", 0)
        candidate = status_counts.get("candidate", 0)
        audited = covered + candidate
        blocked = status_counts.get("blocked", 0)

        coverage_pct = round((audited / in_scope * 100.0), 2) if in_scope > 0 else 0.0
        blocker_rate_pct = round((blocked / in_scope * 100.0), 2) if in_scope > 0 else 0.0

        return {
            "total_units": total,
            "in_scope_units": in_scope,
            "audited_units": audited,
            "audited_coverage_pct": coverage_pct,
            "blocker_rate_pct": blocker_rate_pct,
            "status_breakdown": status_counts,
            "wave_breakdown": wave_counts,
        }

    def get_summary(self) -> Dict[str, int]:
        """Return basic status breakdown for backward-compatibility."""
        counts = {s: 0 for s in VALID_STATUSES}
        for u in self.units:
            counts[u.status] = counts.get(u.status, 0) + 1
        return counts


def main():
    parser = argparse.ArgumentParser(
        description="Mathematical Security Coverage Ledger Manager (Cloudflare Pattern)"
    )
    subparsers = parser.add_subparsers(dest="command")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize a new ledger")
    init_parser.add_argument(
        "--file", "-f", default="coverage-ledger.json", help="Ledger output path"
    )
    init_parser.add_argument(
        "--format", choices=["array", "object"], default="object", help="Document format (array or object)"
    )

    # validate
    val_parser = subparsers.add_parser("validate", help="Validate an existing ledger")
    val_parser.add_argument("file", help="Ledger path")

    # add
    add_parser = subparsers.add_parser("add", help="Add a unit")
    add_parser.add_argument("--file", "-f", default="coverage-ledger.json")
    add_parser.add_argument("--surface", "-s", required=True)
    add_parser.add_argument("--boundary", "-b", required=True)
    add_parser.add_argument("--subsystem", required=True)
    add_parser.add_argument("--attack-class", "-a", required=True)
    add_parser.add_argument("--lifecycle", default=None)
    add_parser.add_argument("--wave", type=int, default=1)
    add_parser.add_argument("--agent-id", default=None)
    add_parser.add_argument("--status", default="planned")
    add_parser.add_argument("--reviewed-paths", nargs="*", default=[])
    add_parser.add_argument("--local-checks", nargs="*", default=[])
    add_parser.add_argument("--unresolved", nargs="*", default=[])
    add_parser.add_argument("--result-fingerprints", nargs="*", default=[])
    add_parser.add_argument("--notes", default=None)

    # summary
    sum_parser = subparsers.add_parser("summary", help="Print summary metrics")
    sum_parser.add_argument("file", help="Ledger path")
    sum_parser.add_argument("--json", action="store_true", help="Output summary as JSON")

    args = parser.parse_args()

    if args.command == "init":
        mgr = CoverageLedgerManager(args.file)
        mgr.save(format_type=args.format)
        print(f"✨ Initialized empty coverage ledger ({args.format} format) at: {args.file}")
    elif args.command == "add":
        mgr = CoverageLedgerManager(args.file)
        unit = mgr.add_unit(
            surface=args.surface,
            boundary=args.boundary,
            subsystem=args.subsystem,
            attack_class=args.attack_class,
            lifecycle=args.lifecycle,
            wave=args.wave,
            agent_id=args.agent_id,
            status=args.status,
            reviewed_paths=args.reviewed_paths,
            local_checks=args.local_checks,
            result_fingerprints=args.result_fingerprints,
            unresolved=args.unresolved,
            notes=args.notes,
        )
        print(f"✅ Added coverage unit: {unit.coverage_id} [{unit.status}]")
    elif args.command == "validate":
        mgr = CoverageLedgerManager(args.file)
        errors = mgr.validate()
        if errors:
            print(f"❌ Validation failed with {len(errors)} error(s):")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)
        else:
            print(f"✅ Ledger valid! {len(mgr.units)} units inspected with zero violations.")
    elif args.command == "summary":
        mgr = CoverageLedgerManager(args.file)
        metrics = mgr.get_metrics()
        if args.json:
            print(json.dumps(metrics, indent=2, ensure_ascii=False))
        else:
            print(f"📊 Security Coverage Ledger Metrics ({metrics['total_units']} total units):")
            print(f"  - In-Scope Units:       {metrics['in_scope_units']}")
            print(f"  - Audited Coverage:     {metrics['audited_coverage_pct']}% ({metrics['audited_units']}/{metrics['in_scope_units']} units)")
            print(f"  - Blocker Rate:         {metrics['blocker_rate_pct']}%")
            print("  Status Breakdown:")
            for status, count in metrics["status_breakdown"].items():
                print(f"    - {status.upper():16s}: {count}")
            print("  Wave Breakdown:")
            sorted_waves = sorted(
                metrics["wave_breakdown"].items(),
                key=lambda item: (0, item[0]) if isinstance(item[0], int) else (1, str(item[0])),
            )
            for wave, count in sorted_waves:
                print(f"    - Wave {str(wave):<11s}: {count}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
