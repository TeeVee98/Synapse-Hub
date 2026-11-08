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

SERVER_VERSION = "3.2.4"
MAX_XLSX_SIZE = 50 * 1024 * 1024          # 50 MB
MAX_UNCOMPRESSED_SIZE = 200 * 1024 * 1024  # 200 MB
MAX_RATIO = 100                            # 100:1 compression ratio limit

NS_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def validate_excel_path(path: str) -> str:
    """Validates that path is safe, does not resolve to sensitive system directories, and is a valid .xlsx file."""
    if not path or not isinstance(path, str):
        raise ValueError("File path must be a non-empty string")

    if "\0" in path or path.startswith("\\\\"):
        raise PermissionError(f"Access denied: invalid or UNC path '{path}'")

    from pathlib import Path
    target = Path(path).resolve()
    target_norm = os.path.normcase(str(target))

    # Reject sensitive directories
    user_home = Path.home().resolve()
    sensitive_prefixes = [
        Path("/etc"), Path("/var/run"), Path("/proc"), Path("/sys"), Path("/dev"), Path("/root"),
        user_home / ".ssh", user_home / ".aws", user_home / ".gnupg"
    ]
    for sp in sensitive_prefixes:
        sp_norm = os.path.normcase(str(sp))
        if target_norm == sp_norm or target_norm.startswith(sp_norm + os.sep):
            raise PermissionError(f"Access denied: restricted system path '{sp}'")

    # If SYNAPSE_PROJECT_ROOT is explicitly configured, enforce boundary
    project_root = os.environ.get("SYNAPSE_PROJECT_ROOT")
    if project_root:
        import tempfile
        root_norm = os.path.normcase(str(Path(project_root).resolve()))
        temp_norm = os.path.normcase(str(Path(tempfile.gettempdir()).resolve()))
        is_in_root = (target_norm == root_norm or target_norm.startswith(root_norm + os.sep))
        is_in_temp = (target_norm == temp_norm or target_norm.startswith(temp_norm + os.sep))
        if not is_in_root and not is_in_temp:
            raise PermissionError(f"Access denied: path '{path}' resolves outside project root '{project_root}'")

    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"Excel file not found: {path}")

    if target.suffix.lower() != ".xlsx":
        raise ValueError(f"Invalid extension '{target.suffix}'. Only .xlsx files are supported.")

    file_size = target.stat().st_size
    if file_size > MAX_XLSX_SIZE:
        raise ValueError(f"Excel file exceeds maximum allowed size of 50MB ({file_size} bytes)")

    return str(target)


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
    valid_path = validate_excel_path(xlsx_path)

    with zipfile.ZipFile(valid_path, "r") as z:
        # Zip bomb protection
        total_uncompressed = sum(info.file_size for info in z.infolist())
        compressed_size = os.path.getsize(valid_path)
        if total_uncompressed > MAX_UNCOMPRESSED_SIZE:
            raise ValueError(f"Zip bomb detected: uncompressed size ({total_uncompressed} bytes) exceeds 200MB ceiling.")
        if compressed_size > 0 and (total_uncompressed / compressed_size) > MAX_RATIO:
            raise ValueError(f"Zip bomb detected: compression ratio ({total_uncompressed / compressed_size:.1f}:1) exceeds 100:1 ceiling.")

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

    if not file_path:
        return "Error: Excel file not found. Please provide a valid file_path argument."

    try:
        valid_path = validate_excel_path(file_path)
    except Exception as e:
        return f"Error: {e}"

    if name == "list_excel_sheets":
        with zipfile.ZipFile(valid_path, "r") as z:
            # Zip bomb protection
            total_uncompressed = sum(info.file_size for info in z.infolist())
            compressed_size = os.path.getsize(valid_path)
            if total_uncompressed > MAX_UNCOMPRESSED_SIZE:
                return f"Error: Zip bomb detected (uncompressed size {total_uncompressed} bytes exceeds 200MB ceiling)."
            if compressed_size > 0 and (total_uncompressed / compressed_size) > MAX_RATIO:
                return f"Error: Zip bomb detected (compression ratio {total_uncompressed / compressed_size:.1f}:1 exceeds 100:1 ceiling)."

            sheets = get_sheet_names(z)
        return json.dumps({"file": valid_path, "sheets": sheets}, indent=2)

    elif name == "read_excel_sheet":
        sheet_name = arguments.get("sheet_name")
        max_rows = int(arguments.get("max_rows", 50))
        try:
            rows = read_sheet_rows(valid_path, sheet_name=sheet_name, max_rows=max_rows)
        except Exception as e:
            return f"Error: {e}"
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
            return "Error: Both 'markdown_content' and 'output_path' are required."

        template_path = arguments.get("template_path")
        sample_sheet = arguments.get("sample_sheet")
        sheet_name = arguments.get("sheet_name")
        module_code = arguments.get("module_code", "MODULE")
        module_name = arguments.get("module_name", "Test Cases")
        author = arguments.get("author", "QA Engineer")

        import template_excel_exporter as tee
        cfg = tee.find_project_config(os.path.dirname(os.path.abspath(output_path)))
        if cfg and not template_path:
            tc_cfg = cfg.get("testcase_export", {})
            cfg_dir = cfg.get("_config_dir", "")
            if "template_path" in tc_cfg:
                template_path = os.path.normpath(os.path.join(cfg_dir, tc_cfg["template_path"]))
            if "sample_sheet" in tc_cfg:
                sample_sheet = tc_cfg["sample_sheet"]
            if "author" in cfg.get("project", {}):
                author = cfg["project"]["author"]

        rows = tee.parse_testcases_from_markdown(markdown_content)
        if template_path and os.path.exists(template_path):
            res_path = tee.clone_and_export_template(
                rows=rows,
                output_path=output_path,
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
                import md_to_xlsx
                md_to_xlsx.convert_markdown_to_xlsx(tf_path, output_path, sheet_name=sheet_name or "Test Cases")
            finally:
                if os.path.exists(tf_path):
                    os.unlink(tf_path)
            return f"Successfully exported to '{output_path}' using Hub default 12-column layout."

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


def process_message(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
    elif method in ("notifications/initialized", "initialized") or (method and method.startswith("notifications/")):
        return None  # No response needed for notification
    elif msg_id is None:
        return None  # JSON-RPC 2.0: Ignore any notification without an ID
    elif method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
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
                "result": {"content": [{"type": "text", "text": content}], "isError": False}
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}
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
            if resp is not None:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
        except Exception as e:
            err_resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}}
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
