#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tools/api/spec_reconciler.py — Ingestion Agent Đối Soát OpenAPI/Swagger + User Story
-------------------------------------------------------------------------------------
Phase 2 Engine: Deep bidirectional reconciliation between natural language User Stories
and OpenAPI 3.0 / Swagger 2.0 schemas. Eliminates AI hallucination by anchoring 100% of
boundary, negative, and happy path test cases into backend schema constraints.

Key Capabilities:
  1. Dual Ingestion: Ingests User Story/PRD text and OpenAPI schema simultaneously.
  2. Recursive Constraint Extraction: Flattens allOf, anyOf, $ref, and endpoint parameters.
  3. Dynamic Story Analysis: Extracts constraints from markdown tables, bullet points, and free text.
  4. Discrepancy Detection: CONSTRAINT_MISMATCH, OMITTED_REQUIRED_IN_STORY, MISSING_IN_STORY, GHOST_FIELD_IN_STORY, TYPE_MISMATCH.
  5. Ground-Truth Test Generation: Standardized 12-column ISO 29119-3 test suites (Golden Ratio: 40/40/20).
"""

import os
import sys
import re
import json
import argparse
from typing import Dict, Any, List, Optional, Tuple, Set

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# UTF-8 terminal encoding
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from tools.api._openapi_parser import load_spec, resolve_ref, extract_endpoints


class SpecReconciler:
    """Reconciles natural language User Stories against OpenAPI / Swagger schemas."""

    def __init__(self, openapi_spec: Any, user_story_text: str):
        self.spec = load_spec(openapi_spec)
        self.story_text = user_story_text
        self.endpoints = extract_endpoints(self.spec)
        self.story_model = self.parse_user_story(user_story_text)
        self.discrepancies: List[Dict[str, Any]] = []

    def parse_user_story(self, text: str) -> Dict[str, Any]:
        """Extracts title, acceptance criteria, and mentioned field rules from User Story."""
        model = {
            "title": "Untitled Story",
            "module": "General",
            "acceptance_criteria": [],
            "fields": {},
            "raw_text": text
        }

        # Extract Title / Feature name
        m_title = re.search(r"^(?:#\s*|Feature:\s*|Story:\s*|User Story:\s*)(.+)$", text, re.MULTILINE | re.IGNORECASE)
        if m_title:
            model["title"] = m_title.group(1).strip()
            model["module"] = model["title"].split(":")[0].strip()

        # Extract Acceptance Criteria (AC-xx, Scenario, etc.)
        ac_matches = re.findall(r"(?:AC[-_]?\d+|Scenario\s*\d*):\s*([^\n]+)", text, re.IGNORECASE)
        if ac_matches:
            model["acceptance_criteria"] = [ac.strip() for ac in ac_matches]
        else:
            bullets = re.findall(r"^[*-]\s*(.+)$", text, re.MULTILINE)
            for b in bullets:
                if any(w in b.lower() for w in ["phải", "bắt buộc", "yêu cầu", "hiển thị", "thành công", "verify", "must", "should", "valid"]):
                    model["acceptance_criteria"].append(b.strip())

        # 1. Parse Fields from Markdown tables if present
        lines = text.splitlines()
        for line in lines:
            trimmed = line.strip()
            if trimmed.startswith("|") and trimmed.endswith("|") and "---" not in trimmed:
                parts = [p.strip() for p in trimmed.split("|")[1:-1]]
                if len(parts) >= 2:
                    col0 = parts[0].strip("`* ")
                    if re.match(r"^[a-zA-Z0-9_-]+$", col0) and col0.lower() not in (
                        "field", "tên trường", "trường", "name", "parameter", "tham số", "header", "stt", "id"
                    ):
                        row_text = " ".join(parts).lower()
                        is_req = any(w in row_text for w in ["có", "yes", "bắt buộc", "required", "true", "x"])
                        max_len = None
                        min_len = None
                        m_max = re.search(r"(?:tối đa|max(?:imum)?|at most|up to|tối đa là)\s*(\d+)", row_text)
                        if m_max:
                            max_len = int(m_max.group(1))
                        m_min = re.search(r"(?:tối thiểu|min(?:imum)?|at least|ít nhất)\s*(\d+)", row_text)
                        if m_min:
                            min_len = int(m_min.group(1))

                        f_type = None
                        if any(w in row_text for w in ["int", "số", "number", "integer"]):
                            f_type = "integer"
                        elif any(w in row_text for w in ["bool", "boolean", "logic"]):
                            f_type = "boolean"
                        elif any(w in row_text for w in ["string", "chuỗi", "text", "varchar"]):
                            f_type = "string"

                        model["fields"][col0] = {
                            "name": col0,
                            "required": is_req,
                            "maxLength": max_len,
                            "minLength": min_len,
                            "type": f_type,
                            "raw_snippet": " | ".join(parts)
                        }

        # 2. Dynamic discovery from text & common keywords
        candidate_field_names: Set[str] = {
            "username", "email", "phone", "password", "company", "name", "address",
            "vat", "tax", "website", "age", "quantity", "price", "title", "notes", "status", "fax",
            "customer_id", "first_name", "last_name", "dob", "gender", "avatar", "role", "code",
            "full_name", "credit_limit", "balance", "currency", "country", "postal_code"
        }

        # Collect backtick identifiers e.g. `field_name`
        backtick_ids = re.findall(r"`([a-zA-Z0-9_]{2,30})`", text)
        for bid in backtick_ids:
            if not bid.startswith("http") and not bid.startswith("api") and not bid.endswith(".com"):
                candidate_field_names.add(bid)

        for cf in candidate_field_names:
            if cf in model["fields"]:
                continue
            pat = rf"\b{re.escape(cf)}\b[^\.\n]*"
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                snippet = m.group(0).lower()
                is_req = any(w in snippet for w in ["bắt buộc", "required", "mandatory", "không được trống", "must enter", "must have", "dấu sao"])
                max_len = None
                min_len = None

                m_max = re.search(r"(?:tối đa|max(?:imum)?|at most|up to|tối đa là)\s*(\d+)", snippet)
                if m_max:
                    max_len = int(m_max.group(1))

                m_min = re.search(r"(?:tối thiểu|min(?:imum)?|at least|ít nhất)\s*(\d+)", snippet)
                if m_min:
                    min_len = int(m_min.group(1))

                f_type = None
                if any(w in snippet for w in ["số nguyên", "number", "integer", "kiểu số"]):
                    f_type = "integer"
                elif any(w in snippet for w in ["boolean", "logic", "true/false"]):
                    f_type = "boolean"
                elif any(w in snippet for w in ["chuỗi", "string", "văn bản"]):
                    f_type = "string"

                model["fields"][cf] = {
                    "name": cf,
                    "required": is_req,
                    "maxLength": max_len,
                    "minLength": min_len,
                    "type": f_type,
                    "raw_snippet": m.group(0)
                }

        return model

    def _flatten_schema_dict(self, schema: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """Recursively flattens allOf, anyOf, oneOf, $ref into properties and required list."""
        merged_props = {}
        merged_req = list(schema.get("required", []))

        if "$ref" in schema:
            ref_schema = resolve_ref(self.spec, schema["$ref"])
            sub_p, sub_r = self._flatten_schema_dict(ref_schema)
            merged_props.update(sub_p)
            merged_req.extend(sub_r)

        for combo in ("allOf", "anyOf", "oneOf"):
            if combo in schema and isinstance(schema[combo], list):
                for sub in schema[combo]:
                    sub_p, sub_r = self._flatten_schema_dict(sub)
                    merged_props.update(sub_p)
                    merged_req.extend(sub_r)

        for p_name, p_def in schema.get("properties", {}).items():
            if "$ref" in p_def:
                p_def = resolve_ref(self.spec, p_def["$ref"])
            merged_props[p_name] = p_def

        return merged_props, list(set(merged_req))

    def get_primary_mutation_schema(self, path_hint: Optional[str] = None) -> Tuple[Dict[str, Any], str, str]:
        """Finds the primary POST/PUT/PATCH endpoint schema to reconcile against."""
        candidates = []
        for ep in self.endpoints:
            if ep["method"] in ("POST", "PUT", "PATCH") and (ep.get("request_schema") or ep.get("parameters")):
                candidates.append(ep)

        if not candidates:
            # Fallback to GET endpoints or direct schemas in components/definitions
            for ep in self.endpoints:
                if ep.get("request_schema") or ep.get("parameters"):
                    candidates.append(ep)

        if not candidates:
            schemas = self.spec.get("components", {}).get("schemas", {}) or self.spec.get("definitions", {})
            if schemas:
                first_k = next(iter(schemas))
                return schemas[first_k], f"Schema:{first_k}", "POST"
            return {}, "Unknown", "POST"

        # Prioritize path_hint if specified
        if path_hint:
            for ep in candidates:
                if path_hint.lower() in ep["path"].lower():
                    return ep.get("request_schema", {}), ep["path"], ep["method"]

        primary = candidates[0]
        schema = primary.get("request_schema", {})

        # If endpoint has parameters (path/query), merge into schema properties
        if primary.get("parameters"):
            param_props = {}
            param_req = []
            for param in primary["parameters"]:
                if "$ref" in param:
                    param = resolve_ref(self.spec, param["$ref"])
                p_name = param.get("name")
                if not p_name:
                    continue
                p_schema = param.get("schema", param)
                param_props[p_name] = p_schema
                if param.get("required"):
                    param_req.append(p_name)
            if param_props:
                schema = dict(schema)
                props = schema.get("properties", {})
                props.update(param_props)
                schema["properties"] = props
                req = schema.get("required", [])
                schema["required"] = list(set(req + param_req))

        return schema, primary["path"], primary["method"]

    def extract_schema_constraints(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Flattens schema properties, resolving refs and extracting all validation constraints."""
        resolved_props = {}
        props, required_list = self._flatten_schema_dict(schema)

        for p_name, p_def in props.items():
            if "$ref" in p_def:
                p_def = resolve_ref(self.spec, p_def["$ref"])

            p_type = p_def.get("type", "string")
            is_req = p_name in required_list

            resolved_props[p_name] = {
                "name": p_name,
                "type": p_type,
                "required": is_req,
                "minLength": p_def.get("minLength"),
                "maxLength": p_def.get("maxLength"),
                "minimum": p_def.get("minimum"),
                "maximum": p_def.get("maximum"),
                "pattern": p_def.get("pattern"),
                "format": p_def.get("format"),
                "enum": p_def.get("enum"),
                "description": p_def.get("description", "")
            }

        return resolved_props

    def reconcile(self, path_hint: Optional[str] = None) -> Dict[str, Any]:
        """Performs deep bidirectional reconciliation between Story and Schema."""
        schema, path, method = self.get_primary_mutation_schema(path_hint)
        schema_props = self.extract_schema_constraints(schema)
        story_fields = self.story_model["fields"]

        self.discrepancies = []
        matched_fields = []
        amb_id = 1

        # 1. Compare Story fields against Schema properties
        for sf_name, sf_info in story_fields.items():
            sp_match = None
            for p_name in schema_props:
                if sf_name.lower() == p_name.lower() or sf_name.lower() in p_name.lower() or p_name.lower() in sf_name.lower():
                    sp_match = schema_props[p_name]
                    break

            if not sp_match:
                # GHOST FIELD: mentioned in Story but missing in API schema
                self.discrepancies.append({
                    "id": f"AMB-{amb_id:02d}",
                    "type": "GHOST_FIELD_IN_STORY",
                    "field": sf_name,
                    "severity": "High",
                    "detail": f"Trường '{sf_name}' được nhắc đến trong User Story nhưng KHÔNG tồn tại trong API Schema ({path}).",
                    "recommendation": f"Xác nhận với Dev xem API có hỗ trợ '{sf_name}' không, hoặc loại bỏ khỏi kịch bản UI."
                })
                amb_id += 1
            else:
                matched_fields.append(sp_match["name"])

                # Check Length Constraint Mismatches
                if sf_info.get("maxLength") and sp_match.get("maxLength"):
                    if sf_info["maxLength"] != sp_match["maxLength"]:
                        self.discrepancies.append({
                            "id": f"AMB-{amb_id:02d}",
                            "type": "CONSTRAINT_MISMATCH",
                            "field": sp_match["name"],
                            "severity": "Critical",
                            "detail": f"Mâu thuẫn maxLength trường '{sp_match['name']}': User Story ghi {sf_info['maxLength']} ký tự nhưng API Schema quy định {sp_match['maxLength']} ký tự.",
                            "recommendation": f"Đồng bộ giới hạn: Chọn {sp_match['maxLength']} (API Ground-Truth) để tránh lỗi 400 Bad Request ngoài ý muốn."
                        })
                        amb_id += 1

                # Check Type Mismatches
                if sf_info.get("type") and sp_match.get("type"):
                    if sf_info["type"] != sp_match["type"]:
                        self.discrepancies.append({
                            "id": f"AMB-{amb_id:02d}",
                            "type": "TYPE_MISMATCH",
                            "field": sp_match["name"],
                            "severity": "Critical",
                            "detail": f"Mâu thuẫn kiểu dữ liệu trường '{sp_match['name']}': User Story ghi kiểu '{sf_info['type']}' nhưng API Schema quy định kiểu '{sp_match['type']}'.",
                            "recommendation": f"Đồng bộ kiểu dữ liệu backend '{sp_match['type']}' để tránh lỗi chuyển đổi kiểu và schema validation 422."
                        })
                        amb_id += 1

                # Check Required Mismatches
                if sp_match["required"] and not sf_info.get("required"):
                    self.discrepancies.append({
                        "id": f"AMB-{amb_id:02d}",
                        "type": "OMITTED_REQUIRED_IN_STORY",
                        "field": sp_match["name"],
                        "severity": "High",
                        "detail": f"Trường '{sp_match['name']}' là BẮT BUỘC (required: true) trong API nhưng User Story không đánh dấu là trường bắt buộc.",
                        "recommendation": "Cập nhật User Story để đánh dấu trường này có dấu sao (*) bắt buộc nhập."
                    })
                    amb_id += 1

        # 2. Check for MISSING_IN_STORY (Required fields in API totally omitted from Story)
        for p_name, p_info in schema_props.items():
            if p_info["required"] and p_name not in matched_fields:
                if not re.search(rf"\b{re.escape(p_name)}\b", self.story_text, re.IGNORECASE):
                    self.discrepancies.append({
                        "id": f"AMB-{amb_id:02d}",
                        "type": "MISSING_IN_STORY",
                        "field": p_name,
                        "severity": "Critical",
                        "detail": f"Trường bắt buộc '{p_name}' ({p_info['type']}) trong API Schema hoàn toàn KHÔNG được đề cập trong User Story.",
                        "recommendation": f"Bổ sung trường '{p_name}' vào biểu mẫu giao diện người dùng; API sẽ trả về 400/422 nếu thiếu trường này."
                    })
                    amb_id += 1

        total_checks = max(1, len(schema_props) + len(story_fields))
        alignment_score = max(0.0, round((1.0 - (len(self.discrepancies) / total_checks)) * 100, 1))

        return {
            "path": path,
            "method": method,
            "story_title": self.story_model["title"],
            "schema_properties_count": len(schema_props),
            "schema_properties": schema_props,
            "discrepancies_count": len(self.discrepancies),
            "discrepancies": self.discrepancies,
            "alignment_score": f"{alignment_score}%"
        }

    def generate_reconciliation_report_md(self, recon_result: Dict[str, Any]) -> str:
        """Generates a professional Markdown reconciliation report."""
        lines = [
            "# BÁO CÁO ĐỐI SOÁT ĐẶC TẢ KỸ THUẬT: USER STORY ↔ OPENAPI SCHEMA",
            "",
            "| Thông tin Đối soát | Chi tiết |",
            "| :--- | :--- |",
            f"| **User Story** | {recon_result['story_title']} |",
            f"| **Target API Endpoint** | `{recon_result['method']} {recon_result['path']}` |",
            f"| **Số lượng Schema Properties** | {recon_result['schema_properties_count']} trường |",
            f"| **Số lượng Bất đồng bộ (Discrepancies)** | {recon_result['discrepancies_count']} điểm mâu thuẫn |",
            f"| **Mức độ Đồng bộ Kỹ thuật (Alignment Score)** | **{recon_result['alignment_score']}** |",
            "",
            "---",
            "",
            "## 1. DANH SÁCH BẤT ĐỒNG BỘ & ĐIỂM DỪNG AMBIGUITY CHECKPOINT",
            ""
        ]

        if not recon_result["discrepancies"]:
            lines.append("✅ **Hoàn hảo:** 100% trường dữ liệu và ràng buộc giữa User Story và OpenAPI Schema hoàn toàn đồng nhất. Không phát hiện mâu thuẫn.")
        else:
            lines.append("| ID | Loại Mâu thuẫn | Trường Dữ liệu | Mức độ | Chi tiết Mâu thuẫn | Khuyến nghị Đồng bộ |")
            lines.append("| :--- | :--- | :--- | :---: | :--- | :--- |")
            for d in recon_result["discrepancies"]:
                prio_badge = f"🔴 {d['severity']}" if d['severity'] == "Critical" else f"🟡 {d['severity']}"
                lines.append(f"| {d['id']} | `{d['type']}` | **{d['field']}** | {prio_badge} | {d['detail']} | {d['recommendation']} |")

        lines.extend([
            "",
            "---",
            "",
            "## 2. MA TRẬN RÀNG BUỘC KỸ THUẬT BACKEND (GROUND-TRUTH CONSTRAINTS)",
            "",
            "| Trường Dữ liệu | Kiểu Dữ liệu | Bắt buộc | Giới hạn Ký tự (Min/Max) | Ràng buộc Giá trị | Pattern / Format |",
            "| :--- | :--- | :---: | :--- | :--- | :--- |"
        ])

        for p_name, p in recon_result["schema_properties"].items():
            req_str = "✅ Có" if p["required"] else "❌ Không"
            len_str = f"{p['minLength'] or 0} .. {p['maxLength'] or '∞'}"
            val_str = f"Min: {p['minimum'] or '-'}, Max: {p['maximum'] or '-'}" if p["type"] in ("integer", "number") else (f"Enum: {p['enum']}" if p.get("enum") else "-")
            pat_str = p.get("pattern") or p.get("format") or "-"
            lines.append(f"| **{p_name}** | `{p['type']}` | {req_str} | {len_str} | {val_str} | `{pat_str}` |")

        return "\n".join(lines)

    def generate_12_column_test_suite_md(self, recon_result: Dict[str, Any], module_prefix: str = "SPEC") -> str:
        """Synthesizes deterministic 12-column ISO 29119-3 test cases based on reconciled constraints."""
        lines = [
            f"# TEST CASES — {recon_result['story_title'].upper()}",
            "",
            "> **Phương pháp:** Ground-Truth Reconciliation (OpenAPI Schema ↔ User Story)  ",
            "> **Tiêu chuẩn:** ISO/IEC/IEEE 29119-3 (Bảng chuẩn 12 cột) & ISTQB CTAL-TAE v2.0  ",
            "> **Tỷ lệ vàng:** 40% Happy Path — 40% Negative & Boundary — 20% Security & Resilience",
            "",
            "---",
            "",
            "| TC ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
        ]

        tc_idx = 1
        module_name = recon_result["story_title"]
        props = recon_result["schema_properties"]
        path = recon_result["path"]
        method = recon_result["method"]

        # Base valid sample payload
        valid_sample = {}
        for p_name, p in props.items():
            if p["type"] == "string":
                if p.get("format") == "email":
                    valid_sample[p_name] = f"valid_{p_name}@example.com"
                else:
                    valid_sample[p_name] = f"Valid_{p_name.capitalize()}"
            elif p["type"] in ("integer", "number"):
                valid_sample[p_name] = p.get("minimum", 1) or 10
            elif p["type"] == "boolean":
                valid_sample[p_name] = True

        valid_data_str = ", ".join([f"{k}='{v}'" for k, v in list(valid_sample.items())[:3]])

        # ---------------------------------------------------------
        # 1. HAPPY PATHS & POSITIVE BOUNDARIES (Target ~40%)
        # ---------------------------------------------------------
        # TC1: Full Valid Payload
        lines.append(
            f"| {module_prefix}_TC_{tc_idx:03d} | {module_name} | High | "
            f"Verify {method} {path} thành công với toàn bộ dữ liệu hợp lệ (Happy Path) | "
            f"Hệ thống API sẵn sàng và người dùng có quyền hợp lệ | "
            f"1. Gửi HTTP {method} đến `{path}`<br>2. Payload chứa toàn bộ trường hợp lệ:<br>`{json.dumps(valid_sample)}` | "
            f"Hệ thống phản hồi mã trạng thái HTTP 200/201 Created thành công, trả về JSON body chứa ID mới và không có lỗi | "
            f"Critical | {valid_data_str} | Yes | API | @Smoke, @Regression, @P0 |"
        )
        tc_idx += 1

        # TC2: Minimal Payload (Only Required Fields)
        req_sample = {k: valid_sample[k] for k in props if props[k]["required"] and k in valid_sample}
        if req_sample and len(req_sample) < len(valid_sample):
            req_data_str = ", ".join([f"{k}='{v}'" for k, v in req_sample.items()])
            lines.append(
                f"| {module_prefix}_TC_{tc_idx:03d} | {module_name} | High | "
                f"Verify {method} {path} thành công chỉ với các trường bắt buộc tối thiểu | "
                f"Hệ thống API sẵn sàng | "
                f"1. Gửi HTTP {method} đến `{path}`<br>2. Payload chỉ chứa các trường bắt buộc:<br>`{json.dumps(req_sample)}` | "
                f"Hệ thống phản hồi mã trạng thái HTTP 200/201 Created thành công, các trường không bắt buộc nhận giá trị mặc định | "
                f"High | {req_data_str} | Yes | API | @Regression, @P1 |"
            )
            tc_idx += 1

        # TC3+: Positive Boundaries (Exact MinLength & Exact MaxLength)
        for p_name, p in props.items():
            if p["type"] == "string" and p.get("minLength") and p["minLength"] >= 1:
                min_l = p["minLength"]
                sample_min = dict(valid_sample)
                sample_min[p_name] = "a" * min_l
                lines.append(
                    f"| {module_prefix}_TC_{tc_idx:03d} | {module_name} | Medium | "
                    f"Verify {method} {path} thành công với trường '{p_name}' đạt độ dài tối thiểu hợp lệ ({min_l} ký tự) | "
                    f"Hệ thống API sẵn sàng | "
                    f"1. Nhập trường `{p_name}` với chuỗi đúng {min_l} ký tự<br>2. Gửi request {method} `{path}` | "
                    f"Hệ thống chấp nhận request thành công, mã phản hồi HTTP 200/201 Created | "
                    f"Medium | {p_name}: Chuỗi {min_l} ký tự 'a' | Yes | API | @Boundary, @Regression |"
                )
                tc_idx += 1

            if p["type"] == "string" and p.get("maxLength"):
                max_l = p["maxLength"]
                sample_max = dict(valid_sample)
                sample_max[p_name] = "a" * max_l
                lines.append(
                    f"| {module_prefix}_TC_{tc_idx:03d} | {module_name} | Medium | "
                    f"Verify {method} {path} thành công với trường '{p_name}' đạt độ dài tối đa hợp lệ ({max_l} ký tự) | "
                    f"Hệ thống API sẵn sàng | "
                    f"1. Nhập trường `{p_name}` với chuỗi đúng {max_l} ký tự<br>2. Gửi request {method} `{path}` | "
                    f"Hệ thống chấp nhận request thành công, mã phản hồi HTTP 200/201 Created | "
                    f"Medium | {p_name}: Chuỗi {max_l} ký tự 'a' | Yes | API | @Boundary, @Regression |"
                )
                tc_idx += 1

            elif p["type"] in ("integer", "number") and p.get("minimum") is not None:
                min_v = p["minimum"]
                lines.append(
                    f"| {module_prefix}_TC_{tc_idx:03d} | {module_name} | Medium | "
                    f"Verify {method} {path} thành công với trường '{p_name}' đạt giá trị biên tối thiểu hợp lệ ({min_v}) | "
                    f"Hệ thống API sẵn sàng | "
                    f"1. Nhập giá trị đúng {min_v} vào trường `{p_name}`<br>2. Gửi request {method} `{path}` | "
                    f"Hệ thống chấp nhận request thành công, mã phản hồi HTTP 200/201 Created | "
                    f"Medium | {p_name}={min_v} | Yes | API | @Boundary, @Regression |"
                )
                tc_idx += 1

        # ---------------------------------------------------------
        # 2. NEGATIVE & BOUNDARY CASES (Target ~40%)
        # ---------------------------------------------------------
        # Missing Required Fields
        for p_name, p in props.items():
            if p["required"]:
                missing_sample = dict(valid_sample)
                missing_sample.pop(p_name, None)
                lines.append(
                    f"| {module_prefix}_TC_{tc_idx:03d} | {module_name} | High | "
                    f"Validate trường bắt buộc '{p_name}' bị thiếu trong payload | "
                    f"Hệ thống API sẵn sàng | "
                    f"1. Gửi HTTP {method} đến `{path}`<br>2. Payload bỏ trống trường bắt buộc `{p_name}` | "
                    f"Hệ thống từ chối request với mã lỗi HTTP 400/422 Unprocessable Entity, response trả về error text: 'Field {p_name} is required' | "
                    f"High | Thiếu {p_name} | Yes | API | @Negative, @Regression |"
                )
                tc_idx += 1

        # Exceed Max Length (Boundary Max+1)
        for p_name, p in props.items():
            if p["type"] == "string" and p.get("maxLength"):
                max_l = p["maxLength"]
                lines.append(
                    f"| {module_prefix}_TC_{tc_idx:03d} | {module_name} | High | "
                    f"Boundary Max+1 - Nhập trường '{p_name}' vượt quá độ dài tối đa ({max_l + 1} ký tự) | "
                    f"Hệ thống API sẵn sàng | "
                    f"1. Nhập trường `{p_name}` với chuỗi {max_l + 1} ký tự<br>2. Gửi request {method} `{path}` | "
                    f"Hệ thống chặn request với mã phản hồi HTTP 400 Bad Request và thông báo lỗi vượt quá độ dài tối đa cho phép | "
                    f"High | {p_name}: Chuỗi {max_l + 1} ký tự 'a' | Yes | API | @Boundary, @Negative |"
                )
                tc_idx += 1

            elif p["type"] in ("integer", "number") and p.get("maximum") is not None:
                max_v = p["maximum"]
                lines.append(
                    f"| {module_prefix}_TC_{tc_idx:03d} | {module_name} | High | "
                    f"Boundary Numeric - Nhập trường '{p_name}' vượt quá giá trị tối đa ({max_v + 1}) | "
                    f"Hệ thống API sẵn sàng | "
                    f"1. Nhập giá trị {max_v + 1} vào trường `{p_name}`<br>2. Gửi request {method} `{path}` | "
                    f"Hệ thống từ chối request với mã phản hồi HTTP 400 Bad Request, giá trị vượt quá ngưỡng cho phép | "
                    f"High | {p_name}={max_v + 1} | Yes | API | @Boundary, @Negative |"
                )
                tc_idx += 1

        # Format & Enum Checks
        for p_name, p in props.items():
            if p.get("format") == "email":
                lines.append(
                    f"| {module_prefix}_TC_{tc_idx:03d} | {module_name} | High | "
                    f"Format Check - Nhập trường '{p_name}' sai định dạng email | "
                    f"Hệ thống API sẵn sàng | "
                    f"1. Nhập `{p_name}`='invalid-email-format'<br>2. Gửi request {method} `{path}` | "
                    f"Hệ thống từ chối request với mã lỗi HTTP 400 Bad Request và thông báo định dạng email không hợp lệ | "
                    f"High | {p_name}='invalid-email-format' | Yes | API | @Negative |"
                )
                tc_idx += 1

            if p.get("enum"):
                lines.append(
                    f"| {module_prefix}_TC_{tc_idx:03d} | {module_name} | High | "
                    f"Enum Check - Nhập giá trị không nằm trong danh sách Enum của '{p_name}' | "
                    f"Hệ thống API sẵn sàng | "
                    f"1. Gửi payload với `{p_name}`='UNSUPPORTED_ENUM_VALUE'<br>2. Thực thi request | "
                    f"Hệ thống từ chối request với mã lỗi HTTP 400/422 và danh sách giá trị enum hợp lệ: {p['enum']} | "
                    f"High | {p_name}='UNSUPPORTED_ENUM_VALUE' | Yes | API | @Negative |"
                )
                tc_idx += 1

        # ---------------------------------------------------------
        # 3. SECURITY & RESILIENCE VECTORS (Target ~20%)
        # ---------------------------------------------------------
        # SQLi Payload
        lines.append(
            f"| {module_prefix}_TC_{tc_idx:03d} | {module_name} | High | "
            f"Security - Tiêm mã độc SQL Injection vào payload {method} | "
            f"Hệ thống API sẵn sàng | "
            f"1. Nhập payload chứa SQLi: `' OR 1=1 --`<br>2. Gửi request {method} `{path}` | "
            f"Hệ thống từ chối request với mã lỗi HTTP 400 Bad Request, Parameterized Query ngăn chặn SQLi thành công, không làm rò rỉ cấu trúc DB và không có lỗi SQL 500 | "
            f"Critical | Payload SQLi `' OR 1=1 --` | Yes | API | @Security, @OWASP |"
        )
        tc_idx += 1

        # XSS Payload
        lines.append(
            f"| {module_prefix}_TC_{tc_idx:03d} | {module_name} | High | "
            f"Security - Tiêm mã độc XSS Script Injection vào trường text | "
            f"Hệ thống API sẵn sàng | "
            f"1. Nhập payload chứa `<script>alert('XSS')</script>`<br>2. Gửi request {method} `{path}` | "
            f"Hệ thống sanitize payload và HTML-escaped an toàn, không thực thi script phía client, mã phản hồi HTTP 400 Bad Request | "
            f"Critical | `<script>alert('XSS')</script>` | Yes | API | @Security, @OWASP |"
        )
        tc_idx += 1

        # Concurrency / Double Submit
        lines.append(
            f"| {module_prefix}_TC_{tc_idx:03d} | {module_name} | High | "
            f"Concurrency - Gửi đồng thời 2 duplicate POST request trong <300ms | "
            f"Tài khoản người dùng hợp lệ | "
            f"1. Gửi 2 request {method} `{path}` giống hệt nhau cùng timestamp (<300ms) | "
            f"Chỉ có đúng 1 request được xử lý thành công (mã 200/201), request thứ 2 nhận mã phản hồi HTTP 409 Conflict ngăn chặn duplicate submission | "
            f"Critical | Cùng payload gửi 2 lần <300ms | Yes | API | @Concurrency, @Resilience |"
        )
        tc_idx += 1

        # Unicode Normalization NFC vs NFD
        lines.append(
            f"| {module_prefix}_TC_{tc_idx:03d} | {module_name} | Medium | "
            f"Resilience - Kiểm tra chuẩn hóa Unicode Normalization NFC vs NFD tiếng Việt | "
            f"Hệ thống API sẵn sàng | "
            f"1. Gửi request với trường text dạng Unicode NFD (Tổ hợp: U+006F U+0300)<br>2. Thực hiện GET lại bản ghi vừa tạo | "
            f"Hệ thống tự động chuẩn hóa về Unicode NFC trước khi lưu vào DB, so khớp dữ liệu GET trả về chuỗi NFC chuẩn mực | "
            f"Medium | Text: `Hoà bình` (NFD) | Yes | API | @Unicode, @Resilience |"
        )
        tc_idx += 1

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Ingestion Agent Đối Soát OpenAPI/Swagger + User Story")
    parser.add_argument("story", help="Path to User Story markdown file or raw text string")
    parser.add_argument("spec", help="Path to OpenAPI / Swagger JSON spec file")
    parser.add_argument("-o", "--output", help="Output path for generated 12-column test cases markdown file")
    parser.add_argument("--report", help="Output path for reconciliation ambiguity report markdown file")
    parser.add_argument("--path-hint", help="Endpoint path filter (e.g. /users, /clients)")
    args = parser.parse_args()

    # Load Story text
    story_text = args.story
    if os.path.isfile(args.story):
        with open(args.story, "r", encoding="utf-8") as f:
            story_text = f.read()

    print("\n" + "=" * 76)
    print("   INGESTION AGENT ĐỐI SOÁT OPENAPI/SWAGGER + USER STORY (PHASE 2)")
    print("=" * 76)

    reconciler = SpecReconciler(args.spec, story_text)
    recon = reconciler.reconcile(path_hint=args.path_hint)

    print(f"\nTarget Story: {recon['story_title']}")
    print(f"Target API  : {recon['method']} {recon['path']}")
    print(f"Properties  : {recon['schema_properties_count']} fields extracted from Schema")
    print(f"Ambiguities : {recon['discrepancies_count']} points of discrepancy detected")
    print(f"Alignment   : {recon['alignment_score']}\n")

    if recon["discrepancies"]:
        print("🚨 BẤT ĐỒNG BỘ ĐƯỢC PHÁT HIỆN:")
        for d in recon["discrepancies"]:
            print(f"  - [{d['id']}] {d['type']} ({d['severity']}): {d['detail']}")
    else:
        print("✅ 100% Hoàn hảo: User Story và OpenAPI Schema hoàn toàn đồng nhất!")

    # Generate Report
    report_md = reconciler.generate_reconciliation_report_md(recon)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"\n📄 Saved Reconciliation Report to: {args.report}")

    # Generate 12-Column Test Cases
    tc_md = reconciler.generate_12_column_test_suite_md(recon)
    output_path = args.output or "Reports/reconciled_test_cases.md"
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(tc_md)
    print(f"✅ Generated ISO 29119-3 12-Column Test Suite: {output_path}")

    print("\n" + "=" * 76 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
