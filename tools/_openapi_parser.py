#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tools/_openapi_parser.py — Shared OpenAPI & Swagger Specification Parser
-------------------------------------------------------------------------
Internal shared helper module consolidating OpenAPI 3.0 and Swagger 2.0
schema ingestion, $ref dereferencing, endpoint extraction, and boundary
value test scenario synthesis across API testing tools.
"""

import os
import sys
import json
from typing import Dict, Any, List

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


def load_spec(spec_input: Any) -> Dict[str, Any]:
    """
    Loads OpenAPI / Swagger spec from a file path, raw JSON string, or dict.
    """
    if isinstance(spec_input, dict):
        return spec_input
    if isinstance(spec_input, str):
        if os.path.exists(spec_input):
            with open(spec_input, "r", encoding="utf-8") as f:
                return json.load(f)
        try:
            return json.loads(spec_input)
        except Exception:
            raise ValueError(f"Unable to parse spec input as JSON file or string: {spec_input[:100]}")
    raise TypeError(f"Expected dict, str path, or JSON string; got {type(spec_input)}")


def resolve_ref(spec_data: Dict[str, Any], ref_str: str) -> Dict[str, Any]:
    """
    Resolves local JSON pointers such as '#/components/schemas/User' or '#/definitions/User'.
    """
    if not ref_str.startswith("#/"):
        return {}
    parts = ref_str[2:].split("/")
    curr = spec_data
    for p in parts:
        if isinstance(curr, dict) and p in curr:
            curr = curr[p]
        else:
            return {}
    return curr if isinstance(curr, dict) else {}


def extract_endpoints(spec_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parses paths and HTTP operations into a normalized list of API endpoints.
    """
    endpoints = []
    paths = spec_data.get("paths", {})

    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, details in methods.items():
            if method.lower() not in ("get", "post", "put", "delete", "patch", "options", "head"):
                continue
            if not isinstance(details, dict):
                continue

            summary = details.get("summary", details.get("operationId", f"{method.upper()} {path}"))
            operation_id = details.get("operationId", f"{method.lower()}_{path.replace('/', '_').strip('_')}")
            tags = details.get("tags", ["General"])

            # Parameters (Path, Query, Header)
            parameters = details.get("parameters", [])

            # Request Body Schema (OpenAPI 3.0 application/json)
            req_content = details.get("requestBody", {}).get("content", {})
            schema = req_content.get("application/json", {}).get("schema", {})
            if "$ref" in schema:
                schema = resolve_ref(spec_data, schema["$ref"])

            # Swagger 2.0 body parameter fallback
            if not schema:
                for param in parameters:
                    if param.get("in") == "body" and "schema" in param:
                        s = param["schema"]
                        schema = resolve_ref(spec_data, s["$ref"]) if "$ref" in s else s
                        break

            # Response schemas
            responses = details.get("responses", {})

            endpoints.append({
                "path": path,
                "method": method.upper(),
                "summary": summary,
                "operation_id": operation_id,
                "tags": tags,
                "parameters": parameters,
                "request_schema": schema,
                "responses": responses
            })

    return endpoints


def generate_boundary_scenarios(field_name: str, field_schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generates standard positive and boundary value test scenarios for a given field schema.
    """
    boundaries = []
    f_type = field_schema.get("type", "string")

    if f_type == "string":
        min_l = field_schema.get("minLength", 1)
        max_l = field_schema.get("maxLength", 50)
        boundaries.append({"scenario": f"{field_name} Empty String", "value": "", "expected": 400})
        boundaries.append({
            "scenario": f"{field_name} Below MinLength ({min_l - 1} chars)",
            "value": "A" * max(0, min_l - 1),
            "expected": 400 if min_l > 0 else 200
        })
        boundaries.append({
            "scenario": f"{field_name} Exact MaxLength ({max_l} chars)",
            "value": "A" * max_l,
            "expected": 200
        })
        boundaries.append({
            "scenario": f"{field_name} Exceed MaxLength ({max_l + 1} chars)",
            "value": "A" * (max_l + 1),
            "expected": 400
        })
        boundaries.append({
            "scenario": f"{field_name} Special & XSS Payload",
            "value": "<script>alert(1)</script>",
            "expected": 400
        })

    elif f_type in ("integer", "number"):
        minimum = field_schema.get("minimum", 0)
        maximum = field_schema.get("maximum", 1000)
        boundaries.append({"scenario": f"{field_name} Negative Value ({minimum - 1})", "value": minimum - 1, "expected": 400})
        boundaries.append({"scenario": f"{field_name} Boundary Minimum ({minimum})", "value": minimum, "expected": 200})
        boundaries.append({"scenario": f"{field_name} Boundary Maximum ({maximum})", "value": maximum, "expected": 200})
        boundaries.append({"scenario": f"{field_name} Exceed Maximum ({maximum + 1})", "value": maximum + 1, "expected": 400})
        boundaries.append({"scenario": f"{field_name} 32-bit Integer Overflow", "value": 2147483648, "expected": 400})

    elif f_type == "boolean":
        boundaries.append({"scenario": f"{field_name} Invalid String Instead of Boolean", "value": "not_a_bool", "expected": 400})

    return boundaries
