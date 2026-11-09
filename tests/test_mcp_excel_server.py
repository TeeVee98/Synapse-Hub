#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Golden Unit Tests for tools/mcp_excel_server.py (MCP Excel Server)
------------------------------------------------------------------
Validates:
  1. JSON-RPC 2.0 initialize protocol handshake (serverInfo, protocolVersion)
  2. tools/list manifest compliance
  3. Unknown method handling (-32601)
  4. list_excel_sheets and read_excel_sheet execution via handle_tool_call
  5. Excel zipfile parsing using Python standard library (without openpyxl)
  6. Security guards: Path traversal rejection, null bytes, UNC, and system directories
  7. Zip-bomb defense: entry count threshold (> 10,000 entries), size, and ratio
  8. Malformed OpenXML resilience: 0-byte file, corrupt zip, corrupt sheet XML
  9. export_testcases_to_excel dispatch without existing .xlsx in CWD
  10. Complete JSON-RPC 2.0 error codes (-32700, -32600, -32601, -32602, -32603), isError: True, and ID preservation
"""

import os
import sys
import json
import zipfile
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import mcp_excel_server as mes


class TestMcpExcelServer(unittest.TestCase):

    def setUp(self):
        # Create a mock minimal .xlsx file using zipfile
        self.temp_dir = tempfile.TemporaryDirectory()
        self.xlsx_path = os.path.join(self.temp_dir.name, "test_cases.xlsx")

        workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
    <sheets>
        <sheet name="TestCases" sheetId="1" r:id="rId1" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>
    </sheets>
</workbook>"""

        shared_strings_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="4" uniqueCount="4">
    <si><t>TC_ID</t></si>
    <si><t>Title</t></si>
    <si><t>TC_01</t></si>
    <si><t>Login Success</t></si>
</sst>"""

        sheet1_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
    <sheetData>
        <row r="1">
            <c r="A1" t="s"><v>0</v></c>
            <c r="B1" t="s"><v>1</v></c>
        </row>
        <row r="2">
            <c r="A2" t="s"><v>2</v></c>
            <c r="B2" t="s"><v>3</v></c>
        </row>
    </sheetData>
</worksheet>"""

        with zipfile.ZipFile(self.xlsx_path, "w") as z:
            z.writestr("xl/workbook.xml", workbook_xml)
            z.writestr("xl/sharedStrings.xml", shared_strings_xml)
            z.writestr("xl/worksheets/sheet1.xml", sheet1_xml)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_notifications_ignored(self):
        # JSON-RPC 2.0 notifications (messages without ID or initialized notification) must return None
        req1 = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        resp1 = mes.process_message(req1)
        self.assertIsNone(resp1)

        req2 = {"jsonrpc": "2.0", "method": "initialized"}
        resp2 = mes.process_message(req2)
        self.assertIsNone(resp2)

        req3 = {"jsonrpc": "2.0", "method": "custom_notification_without_id"}
        resp3 = mes.process_message(req3)
        self.assertIsNone(resp3)

    def test_initialize(self):
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
        resp = mes.process_message(req)

        self.assertEqual(resp["id"], 1)
        self.assertEqual(resp["result"]["protocolVersion"], "2024-11-05")
        self.assertEqual(resp["result"]["serverInfo"]["name"], "synapse-mcp-excel")
        self.assertEqual(resp["result"]["serverInfo"]["version"], mes.SERVER_VERSION)

    def test_tools_list(self):
        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        resp = mes.process_message(req)

        self.assertEqual(resp["id"], 2)
        tools = resp["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        self.assertIn("list_excel_sheets", tool_names)
        self.assertIn("read_excel_sheet", tool_names)
        self.assertIn("export_testcases_to_excel", tool_names)

    def test_unknown_method(self):
        req = {"jsonrpc": "2.0", "id": 99, "method": "unknown_action"}
        resp = mes.process_message(req)

        self.assertEqual(resp["id"], 99)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32601)

    def test_list_excel_sheets(self):
        output = mes.handle_tool_call("list_excel_sheets", {"file_path": self.xlsx_path})
        data = json.loads(output)
        self.assertIn("sheets", data)
        self.assertEqual(data["sheets"], ["TestCases"])

    def test_read_excel_sheet(self):
        output = mes.handle_tool_call("read_excel_sheet", {"file_path": self.xlsx_path, "sheet_name": "TestCases"})
        self.assertIn("| TC_ID | Title |", output)
        self.assertIn("| TC_01 | Login Success |", output)

    def test_tools_call_via_process_message(self):
        req = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "list_excel_sheets",
                "arguments": {"file_path": self.xlsx_path}
            }
        }
        resp = mes.process_message(req)
        self.assertEqual(resp["id"], 10)
        self.assertIn("result", resp)
        self.assertIn("content", resp["result"])
        text = resp["result"]["content"][0]["text"]
        self.assertIn("TestCases", text)

    def test_security_path_traversal_attempts(self):
        """Verifies rejection of directory traversal, null bytes, UNC, and sensitive directories."""
        # Null bytes in path
        with self.assertRaises(PermissionError):
            mes.validate_excel_path("cases.xlsx\0.exe")

        # UNC network path
        with self.assertRaises(PermissionError):
            mes.validate_excel_path("\\\\192.168.1.1\\share\\cases.xlsx")
        with self.assertRaises(PermissionError):
            mes.validate_excel_path("//network-share/cases.xlsx")

        # Sensitive system directory protection (NEVER swallowed)
        if os.name == "nt":
            win_dir = os.environ.get("SystemRoot", "C:\\Windows")
            with self.assertRaises(PermissionError):
                mes.validate_excel_path(os.path.join(win_dir, "System32", "cases.xlsx"))
        else:
            with self.assertRaises(PermissionError):
                mes.validate_excel_path("/etc/cases.xlsx")

        # Wrong file extension
        txt_file = os.path.join(self.temp_dir.name, "notes.txt")
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write("notes")
        with self.assertRaises(ValueError):
            mes.validate_excel_path(txt_file)

        # Blank path rejection
        with self.assertRaises(ValueError):
            mes.validate_excel_path("")
        with self.assertRaises(ValueError):
            mes.validate_excel_path("   ")

    def test_security_zip_bombs(self):
        """Verifies rejection of zip bombs: entry count ceiling, size, and ratio."""
        # 1. Entry count ceiling (> 10,000 entries)
        bomb_entries_path = os.path.join(self.temp_dir.name, "bomb_entries.xlsx")
        with zipfile.ZipFile(bomb_entries_path, "w") as z:
            for i in range(10005):
                z.writestr(f"sheet_{i}.xml", "<sheet/>")

        with self.assertRaises(ValueError) as ctx:
            mes.handle_tool_call("list_excel_sheets", {"file_path": bomb_entries_path})
        self.assertIn("Zip bomb detected", str(ctx.exception))
        self.assertIn("entry count", str(ctx.exception))

        # 2. Uncompressed size ceiling
        with patch.object(mes, "MAX_UNCOMPRESSED_SIZE", 50):
            with self.assertRaises(ValueError) as ctx:
                mes.read_sheet_rows(self.xlsx_path)
            self.assertIn("Zip bomb detected", str(ctx.exception))
            self.assertIn("uncompressed size", str(ctx.exception))

        # 3. Compression ratio ceiling
        with patch.object(mes, "MAX_RATIO", 0.5):
            with self.assertRaises(ValueError) as ctx:
                mes.read_sheet_rows(self.xlsx_path)
            self.assertIn("Zip bomb detected", str(ctx.exception))
            self.assertIn("compression ratio", str(ctx.exception))

    def test_malformed_and_empty_excel_files(self):
        """Verifies graceful handling of 0-byte file, corrupt zip, and corrupt worksheet XML."""
        # 1. 0-byte empty file
        empty_xlsx = os.path.join(self.temp_dir.name, "empty.xlsx")
        with open(empty_xlsx, "wb") as f:
            pass  # 0 bytes

        with self.assertRaises(ValueError) as ctx:
            mes.validate_excel_path(empty_xlsx)
        self.assertIn("empty (0 bytes)", str(ctx.exception))

        # 2. Corrupt non-zip file
        corrupt_xlsx = os.path.join(self.temp_dir.name, "corrupt.xlsx")
        with open(corrupt_xlsx, "wb") as f:
            f.write(b"NOT A REAL EXCEL ZIP ARCHIVE")

        with self.assertRaises(ValueError) as ctx:
            mes.handle_tool_call("list_excel_sheets", {"file_path": corrupt_xlsx})
        self.assertIn("Corrupt or invalid zip archive", str(ctx.exception))

        # 3. Corrupt worksheet XML
        corrupt_sheet_xlsx = os.path.join(self.temp_dir.name, "corrupt_sheet.xlsx")
        with zipfile.ZipFile(corrupt_sheet_xlsx, "w") as z:
            z.writestr("xl/workbook.xml", "<workbook/>")
            z.writestr("xl/worksheets/sheet1.xml", "<worksheet><sheetData><unclosed>")

        with self.assertRaises(ValueError) as ctx:
            mes.read_sheet_rows(corrupt_sheet_xlsx)
        self.assertIn("Corrupt worksheet", str(ctx.exception))

        # 4. Missing workbook.xml defaults safely to ["Sheet1"] without crash
        missing_wb_xlsx = os.path.join(self.temp_dir.name, "missing_wb.xlsx")
        with zipfile.ZipFile(missing_wb_xlsx, "w") as z:
            z.writestr("xl/worksheets/sheet1.xml", "<worksheet/>")

        out = mes.handle_tool_call("list_excel_sheets", {"file_path": missing_wb_xlsx})
        data = json.loads(out)
        self.assertEqual(data["sheets"], ["Sheet1"])

    def test_export_testcases_to_excel_dispatch_without_cwd_xlsx(self):
        """Verifies export_testcases_to_excel succeeds without requiring any .xlsx in CWD."""
        out_file = os.path.join(self.temp_dir.name, "generated_export.xlsx")
        markdown = """# Test Suite
| TC ID | Title | Priority |
|---|---|---|
| TC_001 | Verify User Login | High |
| TC_002 | Verify Password Reset | Medium |
"""
        result = mes.handle_tool_call("export_testcases_to_excel", {
            "markdown_content": markdown,
            "output_path": out_file
        })
        self.assertIn("Successfully exported", result)
        self.assertTrue(os.path.exists(out_file))

        # Missing required parameters
        with self.assertRaises(ValueError):
            mes.handle_tool_call("export_testcases_to_excel", {"markdown_content": markdown})
        with self.assertRaises(ValueError):
            mes.handle_tool_call("export_testcases_to_excel", {"output_path": out_file})

        # Output path in sensitive system directory
        if os.name == "nt":
            win_dir = os.environ.get("SystemRoot", "C:\\Windows")
            with self.assertRaises(PermissionError):
                mes.handle_tool_call("export_testcases_to_excel", {
                    "markdown_content": markdown,
                    "output_path": os.path.join(win_dir, "System32", "bad.xlsx")
                })

    def test_jsonrpc_protocol_error_codes(self):
        """Verifies JSON-RPC 2.0 error codes -32600, -32601, -32602, -32603, isError: True, and ID preservation."""
        # -32600 Invalid Request: non-dict message
        resp1 = mes.process_message([10, 20])
        self.assertEqual(resp1["error"]["code"], -32600)
        self.assertIsNone(resp1["id"])

        # -32600 Invalid Request: missing jsonrpc version
        resp2 = mes.process_message({"id": 201, "method": "ping"})
        self.assertEqual(resp2["error"]["code"], -32600)
        self.assertEqual(resp2["id"], 201)

        # -32600 Invalid Request: non-string method
        resp3 = mes.process_message({"jsonrpc": "2.0", "id": 202, "method": 999})
        self.assertEqual(resp3["error"]["code"], -32600)
        self.assertEqual(resp3["id"], 202)

        # -32601 Method Not Found: unknown protocol method
        resp4 = mes.process_message({"jsonrpc": "2.0", "id": 203, "method": "unsupported/action"})
        self.assertEqual(resp4["error"]["code"], -32601)
        self.assertEqual(resp4["id"], 203)

        # -32601 Method Not Found: unknown tool in tools/call
        resp5 = mes.process_message({
            "jsonrpc": "2.0",
            "id": 204,
            "method": "tools/call",
            "params": {"name": "ghost_tool", "arguments": {}}
        })
        self.assertEqual(resp5["error"]["code"], -32601)
        self.assertEqual(resp5["id"], 204)

        # -32602 Invalid Params: non-dict params
        resp6 = mes.process_message({
            "jsonrpc": "2.0",
            "id": 205,
            "method": "tools/call",
            "params": "invalid"
        })
        self.assertEqual(resp6["error"]["code"], -32602)
        self.assertEqual(resp6["id"], 205)

        # -32602 Invalid Params: missing required file_path
        resp7 = mes.process_message({
            "jsonrpc": "2.0",
            "id": 206,
            "method": "tools/call",
            "params": {"name": "list_excel_sheets", "arguments": {}}
        })
        self.assertEqual(resp7["error"]["code"], -32602)
        self.assertEqual(resp7["id"], 206)

        # -32602 Invalid Params: path traversal attempt in arguments
        resp8 = mes.process_message({
            "jsonrpc": "2.0",
            "id": 207,
            "method": "tools/call",
            "params": {"name": "list_excel_sheets", "arguments": {"file_path": "cases.xlsx\0.exe"}}
        })
        self.assertEqual(resp8["error"]["code"], -32602)
        self.assertEqual(resp8["id"], 207)

        # Tool execution error: CallToolResult with isError: True and preserved ID
        empty_xlsx = os.path.join(self.temp_dir.name, "rpc_empty.xlsx")
        with open(empty_xlsx, "wb") as f:
            pass
        resp9 = mes.process_message({
            "jsonrpc": "2.0",
            "id": 208,
            "method": "tools/call",
            "params": {"name": "list_excel_sheets", "arguments": {"file_path": empty_xlsx}}
        })
        self.assertEqual(resp9["id"], 208)
        self.assertIn("result", resp9)
        self.assertTrue(resp9["result"]["isError"])
        self.assertIn("Error:", resp9["result"]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
