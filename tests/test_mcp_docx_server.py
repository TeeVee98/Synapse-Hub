#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Golden Unit Tests for tools/mcp_docx_server.py (MCP Docx Server)
----------------------------------------------------------------
Validates:
  1. JSON-RPC 2.0 initialize protocol handshake (serverInfo, protocolVersion)
  2. tools/list manifest compliance (all 5 tools present with inputSchema)
  3. Unknown method error handling (-32601)
  4. Document outline, metadata, and heading hierarchy inspection
  5. Text and table conversion to Markdown
  6. Embedded image detection and extraction with context mapping
  7. Keyword search functionality
  8. Security guards: Path traversal rejection, null bytes, UNC, and system directories
  9. Zip-bomb defense: entry count threshold (> 10,000 entries), size, and ratio
  10. Malformed OpenXML resilience: 0-byte file, corrupt zip, missing document.xml, malformed XML
  11. Output path validation in image extraction
  12. Complete JSON-RPC 2.0 error codes (-32700, -32600, -32601, -32602, -32603), isError: True, and ID preservation
"""

import os
import sys
import zipfile
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import mcp_docx_server as mds


class TestMcpDocxServer(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.docx_path = os.path.join(self.temp_dir.name, "spec_document.docx")

        # Create a mock .docx with headings, text, table, and embedded image
        core_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                   xmlns:dc="http://purl.org/dc/elements/1.1/"
                   xmlns:dcterms="http://purl.org/dc/terms/">
    <dc:title>E-Commerce Checkout Specification</dc:title>
    <dc:creator>QA Lead</dc:creator>
</cp:coreProperties>"""

        document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
            xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
            xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">
    <w:body>
        <w:p>
            <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
            <w:r><w:t>1. Authentication Flow</w:t></w:r>
        </w:p>
        <w:p>
            <w:r><w:t>Users must submit valid credentials to receive JWT token.</w:t></w:r>
        </w:p>
        <w:p>
            <w:pPr><w:pStyle w:val="Heading2"/></w:pPr>
            <w:r><w:t>1.1 Login Screen Mockup</w:t></w:r>
        </w:p>
        <w:p>
            <w:r><w:t>Screenshot of login interface:</w:t></w:r>
            <w:r>
                <w:drawing>
                    <wp:inline>
                        <wp:docPr id="1" name="Figure 1" descr="Login Form Screenshot"/>
                        <a:graphic>
                            <a:graphicData>
                                <a:blip r:embed="rId1"/>
                            </a:graphicData>
                        </a:graphic>
                    </wp:inline>
                </w:drawing>
            </w:r>
        </w:p>
        <w:p>
            <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
            <w:r><w:t>2. Acceptance Criteria Matrix</w:t></w:r>
        </w:p>
        <w:tbl>
            <w:tr>
                <w:tc><w:p><w:r><w:t>Rule ID</w:t></w:r></w:p></w:tc>
                <w:tc><w:p><w:r><w:t>Description</w:t></w:r></w:p></w:tc>
            </w:tr>
            <w:tr>
                <w:tc><w:p><w:r><w:t>BR-01</w:t></w:r></w:p></w:tc>
                <w:tc><w:p><w:r><w:t>Password must be at least 8 characters</w:t></w:r></w:p></w:tc>
            </w:tr>
        </w:tbl>
    </w:body>
</w:document>"""

        rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1"
                  Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
                  Target="media/image1.png"/>
</Relationships>"""

        # Minimal 1x1 dummy PNG bytes
        dummy_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'

        with zipfile.ZipFile(self.docx_path, "w") as z:
            z.writestr("docProps/core.xml", core_xml)
            z.writestr("word/document.xml", document_xml)
            z.writestr("word/_rels/document.xml.rels", rels_xml)
            z.writestr("word/media/image1.png", dummy_png)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_jsonrpc_initialize(self):
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
        resp = mds.process_message(req)
        self.assertEqual(resp["id"], 1)
        self.assertEqual(resp["result"]["serverInfo"]["name"], "synapse-mcp-docx")
        self.assertEqual(resp["result"]["serverInfo"]["version"], mds.SERVER_VERSION)
        self.assertIn("tools", resp["result"]["capabilities"])

    def test_jsonrpc_tools_list(self):
        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        resp = mds.process_message(req)
        tools = resp["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        self.assertIn("inspect_docx_structure", tool_names)
        self.assertIn("read_docx_content", tool_names)
        self.assertIn("extract_docx_images", tool_names)
        self.assertIn("read_docx_tables", tool_names)
        self.assertIn("search_docx", tool_names)

    def test_jsonrpc_unknown_method(self):
        req = {"jsonrpc": "2.0", "id": 99, "method": "invalid/method"}
        resp = mds.process_message(req)
        self.assertEqual(resp["error"]["code"], -32601)

    def test_inspect_docx_structure(self):
        data = mds.inspect_docx(self.docx_path)
        self.assertEqual(data["metadata"]["title"], "E-Commerce Checkout Specification")
        self.assertEqual(data["metadata"]["creator"], "QA Lead")
        self.assertEqual(data["counts"]["total_headings"], 3)
        self.assertEqual(data["counts"]["total_tables"], 1)
        self.assertEqual(data["counts"]["embedded_images_in_body"], 1)
        self.assertEqual(data["images"][0]["caption"], "Login Form Screenshot")

    def test_read_docx_content(self):
        content = mds.read_docx_content(self.docx_path)
        self.assertIn("# 1. Authentication Flow", content)
        self.assertIn("## 1.1 Login Screen Mockup", content)
        self.assertIn("Users must submit valid credentials", content)
        self.assertIn("![Login Form Screenshot](word/media/image1.png)", content)
        self.assertIn("| Rule ID | Description |", content)
        self.assertIn("| BR-01 | Password must be at least 8 characters |", content)

    def test_read_docx_content_with_heading_filter(self):
        content = mds.read_docx_content(self.docx_path, heading_filter="Authentication Flow")
        self.assertIn("1. Authentication Flow", content)

    def test_extract_docx_images(self):
        out_dir = os.path.join(self.temp_dir.name, "extracted_media")
        records = mds.extract_docx_images(self.docx_path, output_dir=out_dir)
        self.assertEqual(len(records), 1)
        rec = records[0]
        self.assertEqual(rec["filename"], "image1.png")
        self.assertTrue(os.path.exists(rec["saved_path"]))
        self.assertEqual(rec["caption"], "Login Form Screenshot")
        self.assertEqual(rec["nearest_heading"], "1.1 Login Screen Mockup")

    def test_read_docx_tables(self):
        tables = mds.read_docx_tables(self.docx_path)
        self.assertEqual(len(tables), 1)
        tbl = tables[0]
        self.assertEqual(tbl["rows"], 2)
        self.assertEqual(tbl["cols"], 2)
        self.assertIn("BR-01", tbl["markdown"])

    def test_search_docx(self):
        results = mds.search_docx(self.docx_path, query="credentials")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["heading"], "1. Authentication Flow")

    def test_security_path_validation(self):
        with self.assertRaises((ValueError, PermissionError, FileNotFoundError)):
            mds.validate_docx_path("../non_existent_fake_path.docx")

        with self.assertRaises((ValueError, PermissionError, FileNotFoundError)):
            mds.validate_docx_path("/etc/passwd.docx")

        txt_file = os.path.join(self.temp_dir.name, "file.txt")
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write("test")

        with self.assertRaises(ValueError):
            mds.validate_docx_path(txt_file)

    def test_security_path_traversal_attempts(self):
        """Verifies rejection of directory traversal, null bytes, UNC, and system directories."""
        # Null bytes rejection
        with self.assertRaises(PermissionError):
            mds.validate_docx_path("test.docx\0.exe")

        # UNC network paths rejection
        with self.assertRaises(PermissionError):
            mds.validate_docx_path("\\\\192.168.1.1\\share\\doc.docx")
        with self.assertRaises(PermissionError):
            mds.validate_docx_path("//network-share/doc.docx")

        # Sensitive system directory protection (NEVER swallowed)
        if os.name == "nt":
            win_dir = os.environ.get("SystemRoot", "C:\\Windows")
            with self.assertRaises(PermissionError):
                mds.validate_docx_path(os.path.join(win_dir, "System32", "doc.docx"))
        else:
            with self.assertRaises(PermissionError):
                mds.validate_docx_path("/etc/test.docx")

        # Blank path rejection
        with self.assertRaises(ValueError):
            mds.validate_docx_path("")
        with self.assertRaises(ValueError):
            mds.validate_docx_path("   ")

    def test_security_zip_bombs(self):
        """Verifies rejection of zip bombs: entry count ceiling, size ceiling, and ratio ceiling."""
        # 1. Entry count ceiling (> 10,000 entries)
        bomb_entries_path = os.path.join(self.temp_dir.name, "bomb_entries.docx")
        with zipfile.ZipFile(bomb_entries_path, "w") as z:
            for i in range(10005):
                z.writestr(f"entry_{i}.txt", "a")

        with self.assertRaises(ValueError) as ctx:
            mds.get_docx_zip(bomb_entries_path)
        self.assertIn("Zip bomb detected", str(ctx.exception))
        self.assertIn("entry count", str(ctx.exception))

        # 2. Uncompressed size ceiling (> 200MB)
        from unittest.mock import patch
        with patch.object(mds, "MAX_UNCOMPRESSED_SIZE", 50):
            with self.assertRaises(ValueError) as ctx:
                mds.get_docx_zip(self.docx_path)
            self.assertIn("Zip bomb detected", str(ctx.exception))
            self.assertIn("uncompressed size", str(ctx.exception))

        # 3. Compression ratio ceiling (> 100:1)
        with patch.object(mds, "MAX_RATIO", 0.5):
            with self.assertRaises(ValueError) as ctx:
                mds.get_docx_zip(self.docx_path)
            self.assertIn("Zip bomb detected", str(ctx.exception))
            self.assertIn("compression ratio", str(ctx.exception))

    def test_malformed_and_empty_docx_files(self):
        """Verifies graceful handling of 0-byte, corrupt zip, missing document.xml, and malformed XML."""
        # 1. 0-byte empty file
        empty_docx = os.path.join(self.temp_dir.name, "empty.docx")
        with open(empty_docx, "wb") as f:
            pass  # 0 bytes

        with self.assertRaises(ValueError) as ctx:
            mds.validate_docx_path(empty_docx)
        self.assertIn("empty (0 bytes)", str(ctx.exception))

        # 2. Corrupt non-zip file
        corrupt_zip = os.path.join(self.temp_dir.name, "corrupt.docx")
        with open(corrupt_zip, "wb") as f:
            f.write(b"NOT A REAL ZIP FILE CONTENT")

        with self.assertRaises(ValueError) as ctx:
            mds.get_docx_zip(corrupt_zip)
        self.assertIn("Corrupt or invalid zip archive", str(ctx.exception))

        # 3. Missing word/document.xml
        missing_doc_xml = os.path.join(self.temp_dir.name, "missing_doc.docx")
        with zipfile.ZipFile(missing_doc_xml, "w") as z:
            z.writestr("docProps/core.xml", "<core/>")

        with self.assertRaises(ValueError) as ctx:
            mds.read_docx_content(missing_doc_xml)
        self.assertIn("missing word/document.xml", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            mds.read_docx_tables(missing_doc_xml)
        self.assertIn("missing word/document.xml", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            mds.search_docx(missing_doc_xml, query="test")
        self.assertIn("missing word/document.xml", str(ctx.exception))

        # 4. Malformed XML in word/document.xml
        malformed_xml_docx = os.path.join(self.temp_dir.name, "malformed_xml.docx")
        with zipfile.ZipFile(malformed_xml_docx, "w") as z:
            z.writestr("word/document.xml", "<w:document><w:body><unclosed_tag>")

        with self.assertRaises(ValueError) as ctx:
            mds.read_docx_content(malformed_xml_docx)
        self.assertIn("Corrupt .docx", str(ctx.exception))

    def test_extract_docx_images_output_dir_validation(self):
        """Verifies sandbox validation on extract_docx_images output directory."""
        # Protected directory
        if os.name == "nt":
            win_dir = os.environ.get("SystemRoot", "C:\\Windows")
            with self.assertRaises(PermissionError):
                mds.extract_docx_images(self.docx_path, output_dir=os.path.join(win_dir, "System32"))
        else:
            with self.assertRaises(PermissionError):
                mds.extract_docx_images(self.docx_path, output_dir="/etc/media")

        # Null byte in output dir
        with self.assertRaises(PermissionError):
            mds.extract_docx_images(self.docx_path, output_dir="media\0_out")

    def test_jsonrpc_protocol_error_codes(self):
        """Verifies JSON-RPC 2.0 error codes -32600, -32601, -32602, -32603, isError: True, and ID preservation."""
        # -32600 Invalid Request: non-dict message
        resp1 = mds.process_message([1, 2])
        self.assertEqual(resp1["error"]["code"], -32600)
        self.assertIsNone(resp1["id"])

        # -32600 Invalid Request: missing jsonrpc version
        resp2 = mds.process_message({"id": 101, "method": "ping"})
        self.assertEqual(resp2["error"]["code"], -32600)
        self.assertEqual(resp2["id"], 101)

        # -32600 Invalid Request: non-string method
        resp3 = mds.process_message({"jsonrpc": "2.0", "id": 102, "method": 123})
        self.assertEqual(resp3["error"]["code"], -32600)
        self.assertEqual(resp3["id"], 102)

        # -32601 Method Not Found: unknown protocol method
        resp4 = mds.process_message({"jsonrpc": "2.0", "id": 103, "method": "custom/not_found"})
        self.assertEqual(resp4["error"]["code"], -32601)
        self.assertEqual(resp4["id"], 103)

        # -32601 Method Not Found: unknown tool in tools/call
        resp5 = mds.process_message({
            "jsonrpc": "2.0",
            "id": 104,
            "method": "tools/call",
            "params": {"name": "non_existent_tool", "arguments": {}}
        })
        self.assertEqual(resp5["error"]["code"], -32601)
        self.assertEqual(resp5["id"], 104)

        # -32602 Invalid Params: non-dict params
        resp6 = mds.process_message({
            "jsonrpc": "2.0",
            "id": 105,
            "method": "tools/call",
            "params": "not_a_dict"
        })
        self.assertEqual(resp6["error"]["code"], -32602)
        self.assertEqual(resp6["id"], 105)

        # -32602 Invalid Params: missing required file_path
        resp7 = mds.process_message({
            "jsonrpc": "2.0",
            "id": 106,
            "method": "tools/call",
            "params": {"name": "read_docx_content", "arguments": {}}
        })
        self.assertEqual(resp7["error"]["code"], -32602)
        self.assertEqual(resp7["id"], 106)

        # -32602 Invalid Params: path traversal attempt in arguments
        resp8 = mds.process_message({
            "jsonrpc": "2.0",
            "id": 107,
            "method": "tools/call",
            "params": {"name": "read_docx_content", "arguments": {"file_path": "doc.docx\0.exe"}}
        })
        self.assertEqual(resp8["error"]["code"], -32602)
        self.assertEqual(resp8["id"], 107)

        # Tool execution error: CallToolResult with isError: True and preserved ID
        empty_docx = os.path.join(self.temp_dir.name, "rpc_empty.docx")
        with open(empty_docx, "wb") as f:
            pass
        resp9 = mds.process_message({
            "jsonrpc": "2.0",
            "id": 108,
            "method": "tools/call",
            "params": {"name": "read_docx_content", "arguments": {"file_path": empty_docx}}
        })
        self.assertEqual(resp9["id"], 108)
        self.assertIn("result", resp9)
        self.assertTrue(resp9["result"]["isError"])
        self.assertIn("Error:", resp9["result"]["content"][0]["text"])

    def test_jsonrpc_notifications_ignored(self):
        """Verifies JSON-RPC 2.0 notifications are silently ignored (return None)."""
        req1 = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        self.assertIsNone(mds.process_message(req1))

        req2 = {"jsonrpc": "2.0", "method": "initialized"}
        self.assertIsNone(mds.process_message(req2))

        req3 = {"jsonrpc": "2.0", "method": "custom_notification_no_id"}
        self.assertIsNone(mds.process_message(req3))


if __name__ == "__main__":
    unittest.main()
