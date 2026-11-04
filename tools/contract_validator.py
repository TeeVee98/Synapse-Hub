#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Swarm Data Contract Validator (Single Front-Door Integrity Guard)
-----------------------------------------------------------------
Validates the JSON Data Contract emitted by `live-explorer` before
`pom-crafter` consumes it for Clean POM code synthesis.
Ensures zero locator guessing, validates semantic ARIA roles, and enforces
latency measurement (< 200ms) for durable selectors.
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, List, Tuple

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

CONTRACT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "SelectorContract",
    "type": "object",
    "required": ["url", "screen_name", "elements"],
    "properties": {
        "url": {"type": "string"},
        "screen_name": {"type": "string"},
        "viewport": {
            "type": "object",
            "properties": {
                "width": {"type": "integer"},
                "height": {"type": "integer"}
            }
        },
        "elements": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["name", "role"],
                "properties": {
                    "name": {"type": "string"},
                    "role": {"type": "string"},
                    "selector": {"type": "string"},
                    "target": {"type": "string"},
                    "latency_ms": {"type": "number"},
                    "action_type": {"type": "string"}
                }
            }
        }
    }
}


def validate_contract_dict(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validates contract structure without external dependencies."""
    errors = []
    if not isinstance(data, dict):
        return False, ["Root contract must be a JSON object."]

    # Required top-level fields
    for field in ("url", "screen_name", "elements"):
        if field not in data:
            errors.append(f"Missing required top-level field: '{field}'")

    if "elements" in data:
        elements = data["elements"]
        if not isinstance(elements, list) or len(elements) == 0:
            errors.append("'elements' must be a non-empty list of interactive components.")
        else:
            for idx, el in enumerate(elements):
                if not isinstance(el, dict):
                    errors.append(f"Element at index {idx} must be a dictionary object.")
                    continue
                if "name" not in el or not el["name"]:
                    errors.append(f"Element at index {idx} missing 'name' identifier.")
                if "role" not in el or not el["role"]:
                    errors.append(f"Element at index {idx} missing ARIA 'role' classification.")
                if "selector" not in el and "target" not in el:
                    errors.append(f"Element '{el.get('name', f'index_{idx}')}' must provide 'selector' or 'target'.")

                latency = el.get("latency_ms")
                if latency is not None and isinstance(latency, (int, float)):
                    if latency > 200:
                        errors.append(
                            f"Element '{el.get('name')}' latency ({latency}ms) exceeds the 200ms latency budget."
                        )

    return len(errors) == 0, errors


def validate_contract_file(file_path: str) -> Tuple[bool, List[str]]:
    """Loads and validates a contract file from disk."""
    if not os.path.exists(file_path):
        return False, [f"Contract file does not exist: {file_path}"]
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return validate_contract_dict(data)
    except json.JSONDecodeError as err:
        return False, [f"Malformed JSON syntax: {err}"]
    except OSError as err:
        return False, [f"File read error: {err}"]


def main():
    parser = argparse.ArgumentParser(description="Swarm Data Contract Validator")
    parser.add_argument("contract_path", nargs="?", default=None, help="Path to JSON Data Contract file")
    parser.add_argument("--schema", action="store_true", help="Print standard JSON schema and exit")
    args = parser.parse_args()

    if args.schema:
        print(json.dumps(CONTRACT_SCHEMA, indent=2))
        return 0

    if not args.contract_path:
        parser.print_help()
        return 1

    valid, errors = validate_contract_file(args.contract_path)
    if valid:
        print(f"✅ [VALID CONTRACT] '{args.contract_path}' is ready for Clean POM synthesis.")
        return 0
    else:
        print(f"❌ [INVALID CONTRACT] '{args.contract_path}' contains {len(errors)} violation(s):")
        for err in errors:
            print(f"   • {err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
