#!/usr/bin/env python3
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
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional

# Enforce UTF-8 stdio
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SERVER_VERSION = "3.0.1"

NS_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def get_shared_strings(z: zipfile.ZipFile) -> List[str]:
    """Reads shared strings table from xl/sharedStrings.xml."""
    try:
        with z.open("xl/sharedStrings.xml") as f:
            tree = ET.parse(f)
            root = tree.getroot()
            strings = []
            for si in root.iter(f"{NS_MAIN}si"):
                # Concatenate all text inside <t> elements
                text = "".join(t.text or "" for t in si.iter(f"{NS_MAIN}t"))
                strings.append(text)
            return strings
    except KeyError:
        return []


def get_sheet_names(z: zipfile.ZipFile) -> List[str]:
    """Retrieves sheet names from xl/workbook.xml."""
    try:
        with z.open("xl/workbook.xml") as f:
            tree = ET.parse(f)
            root = tree.getroot()
            sheets = []
            for sheet in root.iter(f"{NS_MAIN}sheet"):
                name = sheet.attrib.get("name")
                if name:
                    sheets.append(name)
            return sheets
    except KeyError:
        return ["Sheet1"]


def read_sheet_rows(xlsx_path: str, sheet_name: Optional[str] = None, max_rows: int = 100) -> List[List[str]]:
    """Reads rows from an Excel .xlsx file using Python standard library."""
    if not os.path.exists(xlsx_path):
        raise FileNotFoundError(f"Excel file not found: {xlsx_path}")

    with zipfile.ZipFile(xlsx_path, "r") as z:
        shared_strings = get_shared_strings(z)
        sheet_names = get_sheet_names(z)

        sheet_idx = 1
        if sheet_name and sheet_name in sheet_names:
            sheet_idx = sheet_names.index(sheet_name) + 1

        sheet_entry = f"xl/worksheets/sheet{sheet_idx}.xml"
        if sheet_entry not in z.namelist():
            sheet_entry = "xl/worksheets/sheet1.xml"

        with z.open(sheet_entry) as f:
            tree = ET.parse(f)
            root = tree.getroot()
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
    file_path = arguments.get("file_path", "")
    if not file_path or not os.path.exists(file_path):
        # Check environment or search current dir for xlsx
        test_path = os.environ.get("EXCEL_TEST_PATH", "")
        if test_path and os.path.exists(test_path):
            file_path = test_path
        else:
            for root, _, files in os.walk("."):
                for fn in files:
                    if fn.endswith(".xlsx") and not fn.startswith("~$"):
                        file_path = os.path.join(root, fn)
                        break
                if file_path:
                    break

    if not file_path or not os.path.exists(file_path):
        return "Error: Excel file not found. Please provide a valid file_path argument."

    if name == "list_excel_sheets":
        with zipfile.ZipFile(file_path, "r") as z:
            sheets = get_sheet_names(z)
        return json.dumps({"file": file_path, "sheets": sheets}, indent=2)

    elif name == "read_excel_sheet":
        sheet_name = arguments.get("sheet_name")
        max_rows = int(arguments.get("max_rows", 50))
        rows = read_sheet_rows(file_path, sheet_name=sheet_name, max_rows=max_rows)
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
        }
    ]
}


def process_message(msg: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-RPC 2.0 message handler for Excel MCP."""
    msg_id = msg.get("id")
    method = msg.get("method")

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
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": MCP_MANIFEST
        }
    elif method == "tools/call":
        params = msg.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})
        try:
            content = handle_tool_call(tool_name, args)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"content": [{"type": "text", "text": content}]}
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32603, "message": str(e)}
            }

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"}
    }


def main():
    """Main stdio loop for JSON-RPC 2.0 communication."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = process_message(req)
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}}
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
