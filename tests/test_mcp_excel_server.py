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
"""

import os
import sys
import json
import zipfile
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
