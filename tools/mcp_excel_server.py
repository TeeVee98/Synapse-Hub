#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Enterprise Cross-Platform MCP Excel Server (Zero-Dependency)
-----------------------------------------------------------
Implements Model Context Protocol (MCP) JSON-RPC 2.0 stdio server
for reading and inspecting Microsoft Excel (.xlsx) workbooks.
Works 100% offline with Python Standard Library (zipfile + xml.etree.ElementTree),
with transparent fallback to openpyxl if installed.
"""

import os
import sys
import json
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

try:
    from openxml_guard import (
        validate_openxml_path,
        validate_output_path,
        safe_open_zip,
        safe_parse_xml,
        jsonrpc_error_response,
        PARSE_ERROR,
        INVALID_REQUEST,
        METHOD_NOT_FOUND,
        INVALID_PARAMS,
        INTERNAL_ERROR,
        MAX_ZIP_ENTRIES
    )
except ImportError:
    from tools.openxml_guard import (
        validate_openxml_path,
        validate_output_path,
        safe_open_zip,
        safe_parse_xml,
        jsonrpc_error_response,
        PARSE_ERROR,
        INVALID_REQUEST,
        METHOD_NOT_FOUND,
        INVALID_PARAMS,
        INTERNAL_ERROR,
        MAX_ZIP_ENTRIES
    )

# Enforce UTF-8 stdio
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SERVER_VERSION = "4.1.4"
MAX_XLSX_SIZE = 50 * 1024 * 1024          # 50 MB
MAX_UNCOMPRESSED_SIZE = 200 * 1024 * 1024  # 200 MB
MAX_RATIO = 100                            # 100:1 compression ratio limit

NS_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def validate_excel_path(path: str, workspace_root: Optional[Union[str, Path]] = None) -> str:
    """Validates that path is safe, does not resolve to sensitive system directories, and is a valid .xlsx file."""
    target = validate_openxml_path(
        path,
        workspace_root=workspace_root,
        allowed_extensions=('.xlsx',),
        max_file_size=MAX_XLSX_SIZE
    )
    return str(target)


def get_shared_strings(z: zipfile.ZipFile) -> List[str]:
    """Reads shared strings table from xl/sharedStrings.xml."""
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    try:
        with z.open("xl/sharedStrings.xml") as f:
            root = safe_parse_xml(f)
            strings = []
            for si in root.iter(f"{NS_MAIN}si"):
                # Concatenate all text inside <t> elements
                text = "".join(t.text or "" for t in si.iter(f"{NS_MAIN}t"))
                strings.append(text)
            return strings
    except (KeyError, ValueError):
        return []


def get_sheet_names(z: zipfile.ZipFile) -> List[str]:
    """Retrieves sheet names from xl/workbook.xml."""
    if "xl/workbook.xml" not in z.namelist():
        return ["Sheet1"]
    try:
        with z.open("xl/workbook.xml") as f:
            root = safe_parse_xml(f)
            sheets = []
            for sheet in root.iter(f"{NS_MAIN}sheet"):
                name = sheet.attrib.get("name")
                if name:
                    sheets.append(name)
            return sheets or ["Sheet1"]
    except (KeyError, ValueError):
        return ["Sheet1"]


def read_sheet_rows(xlsx_path: str, sheet_name: Optional[str] = None, max_rows: int = 100) -> List[List[str]]:
    """Reads rows from an Excel .xlsx file using Python standard library."""
    valid_path = validate_excel_path(xlsx_path)

    with safe_open_zip(valid_path, max_entries=MAX_ZIP_ENTRIES, max_uncompressed_size=MAX_UNCOMPRESSED_SIZE, max_ratio=MAX_RATIO) as z:
        shared_strings = get_shared_strings(z)
        sheet_names = get_sheet_names(z)

        sheet_idx = 1
        if sheet_name and sheet_name in sheet_names:
            sheet_idx = sheet_names.index(sheet_name) + 1

        sheet_entry = f"xl/worksheets/sheet{sheet_idx}.xml"
        if sheet_entry not in z.namelist():
            candidates = [n for n in z.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
            if candidates:
                sheet_entry = candidates[0]
            else:
                return []

        try:
            with z.open(sheet_entry) as f:
                root = safe_parse_xml(f)
        except ValueError as err:
            raise ValueError(f"Corrupt worksheet '{sheet_entry}': {err}")

        rows_data = []
        for row in root.iter(f"{NS_MAIN}row"):
            cells = []
            for c in row.iter(f"{NS_MAIN}c"):
                cell_type = c.attrib.get("t")
                val_elem = c.find(f"{NS_MAIN}v")
                raw_val = (val_elem.text or "") if val_elem is not None else ""

                if cell_type == "s" and raw_val.isdigit():
                    idx = int(raw_val)
                    val = shared_strings[idx] if idx < len(shared_strings) else raw_val
                elif cell_type == "b":
                    val = "TRUE" if raw_val == "1" else "FALSE"
                else:
                    val = raw_val

                cells.append(str(val))
            if any(cells):
                rows_data.append(cells)
            if len(rows_data) >= max_rows:
                break

        return rows_data


def handle_tool_call(name: str, arguments: Dict[str, Any]) -> str:
    """Executes Excel MCP tool functions."""
    if name not in MCP_EXCEL_TOOL_NAMES:
        raise ValueError(f"Unknown MCP Excel tool: {name}")

    if name == "list_excel_sheets":
        file_path = arguments.get("file_path")
        if not file_path or not isinstance(file_path, str):
            raise ValueError("Tool argument 'file_path' is required and must be a string.")
        valid_path = validate_excel_path(file_path)
        with safe_open_zip(valid_path, max_entries=MAX_ZIP_ENTRIES, max_uncompressed_size=MAX_UNCOMPRESSED_SIZE, max_ratio=MAX_RATIO) as z:
            sheets = get_sheet_names(z)
        return json.dumps({"file": valid_path, "sheets": sheets}, indent=2)

    elif name == "read_excel_sheet":
        file_path = arguments.get("file_path")
        if not file_path or not isinstance(file_path, str):
            raise ValueError("Tool argument 'file_path' is required and must be a string.")
        valid_path = validate_excel_path(file_path)
        sheet_name = arguments.get("sheet_name")
        max_rows = int(arguments.get("max_rows", 50))
        rows = read_sheet_rows(valid_path, sheet_name=sheet_name, max_rows=max_rows)
        if not rows:
            return f"Sheet '{sheet_name or 'Sheet1'}' is empty."

        # Format as Markdown table
        header = rows[0]
        md_lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(["---"] * len(header)) + " |"
        ]
        for row in rows[1:]:
            padded = row + [""] * (len(header) - len(row))
            md_lines.append("| " + " | ".join(padded[:len(header)]) + " |")

        return "\n".join(md_lines)

    elif name == "export_testcases_to_excel":
        markdown_content = arguments.get("markdown_content", "")
        output_path = arguments.get("output_path", "")
        if not markdown_content or not output_path:
            raise ValueError("Both 'markdown_content' and 'output_path' are required.")

        valid_output = validate_output_path(output_path, allowed_extensions=('.xlsx',), create_parent=True)

        template_path = arguments.get("template_path")
        if template_path:
            template_path = str(validate_openxml_path(template_path, allowed_extensions=('.xlsx',)))

        sample_sheet = arguments.get("sample_sheet")
        sheet_name = arguments.get("sheet_name")
        module_code = arguments.get("module_code", "MODULE")
        module_name = arguments.get("module_name", "Test Cases")
        author = arguments.get("author", "QA Engineer")

        try:
            import template_excel_exporter as tee
        except ImportError:
            from tools import template_excel_exporter as tee

        cfg = tee.find_project_config(os.path.dirname(os.path.abspath(str(valid_output))))
        if cfg and not template_path:
            tc_cfg = cfg.get("testcase_export", {})
            cfg_dir = cfg.get("_config_dir", "")
            if "template_path" in tc_cfg:
                raw_tp = os.path.normpath(os.path.join(cfg_dir, tc_cfg["template_path"]))
                if os.path.exists(raw_tp):
                    template_path = str(validate_openxml_path(raw_tp, allowed_extensions=('.xlsx',)))
            if "sample_sheet" in tc_cfg:
                sample_sheet = tc_cfg["sample_sheet"]
            if "author" in cfg.get("project", {}):
                author = cfg["project"]["author"]

        rows = tee.parse_testcases_from_markdown(markdown_content)
        if template_path and os.path.exists(template_path):
            res_path = tee.clone_and_export_template(
                rows=rows,
                output_path=str(valid_output),
                template_path=template_path,
                sample_sheet_name=sample_sheet,
                target_sheet_name=sheet_name,
                module_code=module_code,
                module_name=module_name,
                author=author
            )
            case_count = len([r for r in rows if r.get('type') == 'case'])
            return f"Successfully exported {case_count} test cases into '{res_path}' using template '{sample_sheet}'."
        else:
            # Fallback to standard 12-column layout
            import tempfile
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as tf:
                tf.write(markdown_content)
                tf_path = tf.name
            try:
                try:
                    import md_to_xlsx
                except ImportError:
                    from tools import md_to_xlsx
                md_to_xlsx.convert_markdown_to_xlsx(tf_path, str(valid_output), sheet_name=sheet_name or "Test Cases")
            finally:
                if os.path.exists(tf_path):
                    os.unlink(tf_path)
            return f"Successfully exported to '{valid_output}' using Hub default 12-column layout."

    raise ValueError(f"Unknown MCP Excel tool: {name}")


MCP_MANIFEST = {
    "tools": [
        {
            "name": "list_excel_sheets",
            "description": "Lists all worksheet names present in a Microsoft Excel (.xlsx) file.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute or relative path to the .xlsx file"}
                },
                "required": ["file_path"]
            }
        },
        {
            "name": "read_excel_sheet",
            "description": "Reads and displays tabular rows from an Excel worksheet formatted as a Markdown table.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the .xlsx file"},
                    "sheet_name": {"type": "string", "description": "Optional name of the worksheet to read"},
                    "max_rows": {"type": "integer", "description": "Maximum number of rows to retrieve (default: 50)"}
                },
                "required": ["file_path"]
            }
        },
        {
            "name": "export_testcases_to_excel",
            "description": "Exports test cases into an Excel workbook (.xlsx). If a project template (.synapse.json or template_path) is configured, it clones the corporate template preserving headers, styling, and formulas. Otherwise, it generates the Hub 12-column standard layout.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "markdown_content": {"type": "string", "description": "Markdown test case content or table"},
                    "output_path": {"type": "string", "description": "Output path for the generated .xlsx file"},
                    "sheet_name": {"type": "string", "description": "Name for the worksheet (e.g. feature name)"},
                    "template_path": {"type": "string", "description": "Optional path to template .xlsx file (overrides .synapse.json)"},
                    "sample_sheet": {"type": "string", "description": "Optional sheet in template to clone (defaults to .synapse.json or first sheet)"},
                    "module_code": {"type": "string", "description": "Module code (e.g. TC_MOD)"},
                    "module_name": {"type": "string", "description": "Module title in Vietnamese or English"},
                    "author": {"type": "string", "description": "Author name"}
                },
                "required": ["markdown_content", "output_path"]
            }
        }
    ]
}


MCP_EXCEL_TOOL_NAMES = {t["name"] for t in MCP_MANIFEST["tools"]}


def process_message(msg: Any) -> Optional[Dict[str, Any]]:
    """JSON-RPC 2.0 message handler for Excel MCP."""
    if not isinstance(msg, dict):
        return jsonrpc_error_response(INVALID_REQUEST, "Invalid Request: message must be a JSON object", req_id=None)

    msg_id = msg.get("id")

    if msg.get("jsonrpc") != "2.0":
        return jsonrpc_error_response(INVALID_REQUEST, "Invalid Request: 'jsonrpc' must be exactly '2.0'", req_id=msg_id)

    method = msg.get("method")
    if not isinstance(method, str) or not method:
        return jsonrpc_error_response(INVALID_REQUEST, "Invalid Request: 'method' must be a non-empty string", req_id=msg_id)

    # Notifications handling (no response per JSON-RPC 2.0 spec)
    if method in ("notifications/initialized", "initialized") or method.startswith("notifications/"):
        return None
    if msg_id is None:
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "synapse-mcp-excel", "version": SERVER_VERSION}
            }
        }
    elif method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": MCP_MANIFEST
        }
    elif method == "tools/call":
        params = msg.get("params")
        if not isinstance(params, dict):
            return jsonrpc_error_response(INVALID_PARAMS, "Invalid params: 'params' must be a dictionary", req_id=msg_id)

        tool_name = params.get("name")
        if not isinstance(tool_name, str) or not tool_name:
            return jsonrpc_error_response(INVALID_PARAMS, "Invalid params: tool 'name' must be a non-empty string", req_id=msg_id)

        if tool_name not in MCP_EXCEL_TOOL_NAMES:
            return jsonrpc_error_response(METHOD_NOT_FOUND, f"Method not found: Unknown tool '{tool_name}'", req_id=msg_id)

        args = params.get("arguments")
        if args is None:
            args = {}
        if not isinstance(args, dict):
            return jsonrpc_error_response(INVALID_PARAMS, "Invalid params: 'arguments' must be a dictionary", req_id=msg_id)

        # Validate mandatory tool arguments
        if tool_name in ("list_excel_sheets", "read_excel_sheet"):
            file_path = args.get("file_path")
            if not file_path or not isinstance(file_path, str):
                return jsonrpc_error_response(INVALID_PARAMS, "Invalid params: 'file_path' is required and must be a non-empty string", req_id=msg_id)
        elif tool_name == "export_testcases_to_excel":
            if "markdown_content" not in args or not isinstance(args["markdown_content"], str):
                return jsonrpc_error_response(INVALID_PARAMS, "Invalid params: 'markdown_content' is required and must be a string", req_id=msg_id)
            if "output_path" not in args or not isinstance(args["output_path"], str) or not args["output_path"].strip():
                return jsonrpc_error_response(INVALID_PARAMS, "Invalid params: 'output_path' is required and must be a non-empty string", req_id=msg_id)

        try:
            content = handle_tool_call(tool_name, args)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"content": [{"type": "text", "text": content}], "isError": False}
            }
        except PermissionError as e:
            return jsonrpc_error_response(INVALID_PARAMS, f"Invalid params (traversal or permission denied): {e}", req_id=msg_id)
        except (ValueError, FileNotFoundError) as e:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}
            }
        except Exception as e:
            return jsonrpc_error_response(INTERNAL_ERROR, f"Internal error: {e}", req_id=msg_id)

    return jsonrpc_error_response(METHOD_NOT_FOUND, f"Method not found: '{method}'", req_id=msg_id)


def main():
    """Main stdio loop for JSON-RPC 2.0 communication."""
    if len(sys.argv) > 1 and any(arg in sys.argv for arg in ("-h", "--help")):
        print("Usage: python3 tools/mcp_excel_server.py")
        print("Model Context Protocol (MCP) server providing Excel automation tools over stdio.")
        print("Supported operations: read_sheet, write_sheet, get_metadata, run_audit")
        sys.exit(0)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req_id = None
        try:
            try:
                req = json.loads(line)
                if isinstance(req, dict):
                    req_id = req.get("id")
            except Exception as e:
                err_resp = jsonrpc_error_response(PARSE_ERROR, f"Parse error: {e}", req_id=None)
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()
                continue

            resp = process_message(req)
            if resp is not None:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
        except Exception as e:
            err_resp = jsonrpc_error_response(INTERNAL_ERROR, f"Internal error: {e}", req_id=req_id)
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
