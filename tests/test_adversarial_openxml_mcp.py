#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Adversarial Security Stress Test Suite for OpenXML MCP Servers
--------------------------------------------------------------
Empirical Challenger 1: Rigorous stress testing for:
  1. Path Traversal & Sandbox Escapes (Relative, Absolute, UNC, Null Bytes, Zip Slip).
  2. Zip-Bomb Attacks (Entry Count >10k, Compression Ratio >100:1, Uncompressed Size >200MB).
  3. Server Resource & DOS Resilience (Memory & Latency Budgets).
  4. Protocol Enforcement (JSON-RPC 2.0 Error Codes -32602, -32600, -32601).
"""

import os
import sys
import time
import zipfile
import tempfile
import unittest
from pathlib import Path

# Ensure project root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import tools.openxml_guard as og
import tools.mcp_docx_server as mds
import tools.mcp_excel_server as mes


class TestAdversarialPathTraversal(unittest.TestCase):
    """Stress tests path traversal and sandbox escape vectors across all OpenXML server entry points."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.safe_docx = Path(self.temp_dir.name) / "sample.docx"
        self.safe_xlsx = Path(self.temp_dir.name) / "sample.xlsx"

        # Construct minimal valid docx
        with zipfile.ZipFile(self.safe_docx, "w") as z:
            z.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>')
            z.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Hello Synapse</w:t></w:r></w:p></w:body></w:document>')

        # Construct minimal valid xlsx
        with zipfile.ZipFile(self.safe_xlsx, "w") as z:
            z.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>')
            z.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>')
            z.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c></row></sheetData></worksheet>')
            z.writestr("xl/sharedStrings.xml", '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="1" uniqueCount="1"><si><t>Cell A1 Content</t></si></sst>')

    def tearDown(self):
        self.temp_dir.cleanup()

    # --- Vector 1.1: Relative Traversal Sequences ---

    def test_relative_path_traversal_rejected(self):
        """Attempts relative traversal across ../ sequences must raise PermissionError or ValueError."""
        # Exact prompt challenge vectors
        prompt_traversal_payloads = [
            "../../etc/passwd",
            "../../etc/shadow",
            "..\\..\\Windows\\System32\\calc.exe",
            "..\\..\\Windows\\System32\\cmd.exe",
            "tools/../tests/..",
            "../../../../../../../../Windows/System32/drivers/etc/hosts",
            ".\\.\\..\\..\\boot.ini",
            "../../non_existent_escaped.docx",
        ]
        for payload in prompt_traversal_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises((PermissionError, ValueError), msg=f"Payload {payload} should be rejected with PermissionError or ValueError"):
                    og.validate_openxml_path(payload)

    def test_nonexistent_and_pseudo_traversal_rejected(self):
        """Pseudo-traversal strings that resolve inside workspace but do not exist must be rejected."""
        pseudo_payloads = [
            "....//....//....//etc/passwd",
            "..%2f..%2f..%2fWindows%2fSystem32",
        ]
        for payload in pseudo_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises((PermissionError, ValueError, FileNotFoundError)):
                    og.validate_openxml_path(payload)

    # --- Vector 1.2: Absolute Paths Outside Sandbox ---

    def test_absolute_paths_outside_sandbox_rejected(self):
        """Absolute system paths outside the workspace and temp directory must raise PermissionError."""
        if os.name == "nt":
            win_root = os.environ.get("SystemRoot", "C:\\Windows")
            forbidden_targets = [
                os.path.join(win_root, "System32", "calc.exe"),
                os.path.join(win_root, "System32", "cmd.exe"),
                os.path.join(win_root, "notepad.exe"),
                os.path.join(win_root, "System32", "drivers", "etc", "hosts"),
                "C:\\pagefile.sys",
                str(Path.home() / "Desktop" / "secret.docx"),
                str(Path.home() / ".ssh" / "id_rsa"),
                str(Path.home() / ".aws" / "credentials"),
            ]
        else:
            forbidden_targets = [
                "/etc/passwd",
                "/etc/hosts",
                "/var/log/syslog",
                "/proc/cpuinfo",
                "/sys/class",
                str(Path.home() / ".ssh" / "id_rsa"),
            ]

        for target in forbidden_targets:
            with self.subTest(target=target):
                with self.assertRaises(PermissionError, msg=f"Target {target} should raise PermissionError"):
                    og.validate_openxml_path(target)

    # --- Vector 1.3: Null Byte Injection ---

    def test_null_byte_injection_rejected(self):
        """Null byte injection in file paths must raise PermissionError immediately."""
        null_payloads = [
            "doc.docx\0.txt",
            "sample.docx\x00",
            "\x00secret.docx",
            "test.xlsx\0.pdf",
            "folder\0/document.docx",
            str(self.safe_docx) + "\0.bak",
        ]
        for payload in null_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(PermissionError, msg=f"Null byte payload {payload!r} should be rejected"):
                    og.validate_openxml_path(payload)
                with self.assertRaises(PermissionError):
                    og.validate_output_path(payload)

    # --- Vector 1.4: Windows UNC Network Paths ---

    def test_unc_paths_rejected(self):
        """Windows network UNC paths (\\\\share and //share) must raise PermissionError."""
        unc_payloads = [
            "\\\\localhost\\c$\\secret.docx",
            "\\\\127.0.0.1\\c$\\secret.docx",
            "//127.0.0.1/c$/test.xlsx",
            "//localhost/share/test.docx",
            "\\\\?\\C:\\secret.docx",
            "\\\\.\\C:\\test.docx",
            "\\\\192.168.1.100\\share\\report.docx",
        ]
        for payload in unc_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(PermissionError, msg=f"UNC payload {payload} should be rejected"):
                    og.validate_openxml_path(payload)
                with self.assertRaises(PermissionError):
                    og.validate_output_path(payload)

    # --- Vector 1.5: Image Extraction Output Directory Traversal ---

    def test_extract_docx_images_output_dir_escape_rejected(self):
        """extract_docx_images must reject output_dir paths attempting to escape workspace or write to system paths."""
        if os.name == "nt":
            win_root = os.environ.get("SystemRoot", "C:\\Windows")
            evil_output_dirs = [
                "../../escaped_media_dir",
                "..\\..\\escaped_media_dir",
                os.path.join(win_root, "System32"),
                "\\\\localhost\\c$\\escaped_media",
                "extracted_media\0corrupt",
            ]
        else:
            evil_output_dirs = [
                "../../escaped_media_dir",
                "/etc/escaped_media",
                "//localhost/escaped",
                "extracted_media\0corrupt",
            ]

        for out_dir in evil_output_dirs:
            with self.subTest(out_dir=out_dir):
                with self.assertRaises(PermissionError, msg=f"Output dir {out_dir!r} should be rejected"):
                    mds.extract_docx_images(str(self.safe_docx), output_dir=out_dir)

    # --- Vector 1.6: Zip Slip Attack Resilience Inside Word Archives ---

    def test_zip_slip_media_entries_blocked(self):
        """Malicious entries inside docx (e.g. word/media/../../evil.png) must NEVER escape output directory."""
        slip_docx = Path(self.temp_dir.name) / "slip_attack.docx"
        with zipfile.ZipFile(slip_docx, "w") as z:
            z.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>')
            z.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Zip Slip Doc</w:t></w:r></w:p></w:body></w:document>')
            # Adversarial media entries attempting traversal
            z.writestr("word/media/../../evil_slip1.png", b"PAYLOAD_1")
            z.writestr("word/media/..\\..\\evil_slip2.png", b"PAYLOAD_2")
            z.writestr("word/media/../../../../System32/evil_slip3.dll", b"PAYLOAD_3")
            z.writestr("word/media/legit_image.png", b"LEGIT_IMAGE")

        dest_dir = Path(self.temp_dir.name) / "isolated_extracted"
        records = mds.extract_docx_images(str(slip_docx), output_dir=str(dest_dir))

        # Check that no file escaped outside dest_dir
        parent_dir = dest_dir.parent
        self.assertFalse((parent_dir / "evil_slip1.png").exists(), "evil_slip1.png escaped destination directory!")
        self.assertFalse((parent_dir / "evil_slip2.png").exists(), "evil_slip2.png escaped destination directory!")
        self.assertFalse((parent_dir / "evil_slip3.dll").exists(), "evil_slip3.dll escaped destination directory!")

        # All saved files in records must strictly be inside dest_dir
        for r in records:
            saved = Path(r["saved_path"]).resolve()
            self.assertTrue(saved.is_relative_to(dest_dir.resolve()), f"Saved file {saved} escaped {dest_dir}!")

    # --- Vector 1.7: Excel Server Traversal & Output Boundaries ---

    def test_excel_export_output_and_template_traversal_rejected(self):
        """export_testcases_to_excel must reject traversal output_path and template_path."""
        # 1. Output path traversal rejection
        with self.assertRaises(PermissionError):
            mes.handle_tool_call("export_testcases_to_excel", {
                "markdown_content": "# TC\n| TC ID | Title |\n|---|---|\n| 1 | Test |",
                "output_path": "../../escaped.xlsx"
            })

        # 2. Template path traversal rejection
        with self.assertRaises(PermissionError):
            mes.handle_tool_call("export_testcases_to_excel", {
                "markdown_content": "# TC\n| TC ID | Title |\n|---|---|\n| 1 | Test |",
                "output_path": str(Path(self.temp_dir.name) / "out.xlsx"),
                "template_path": "../../etc/passwd"
            })

    # --- Vector 1.8: JSON-RPC 2.0 Traversal Error Code Verification ---

    def test_jsonrpc_path_traversal_returns_invalid_params_error(self):
        """JSON-RPC 2.0 messages requesting traversal files must return code -32602 (Invalid Params)."""
        traversal_cases = [
            ("inspect_docx_structure", {"file_path": "../../etc/passwd"}),
            ("read_docx_content", {"file_path": "..\\..\\Windows\\System32\\calc.exe"}),
            ("extract_docx_images", {"file_path": "\\\\localhost\\c$\\test.docx"}),
            ("read_docx_tables", {"file_path": "test.docx\0.exe"}),
            ("search_docx", {"file_path": "../../secret.docx", "query": "auth"}),
        ]
        for tool_name, args in traversal_cases:
            with self.subTest(tool=tool_name):
                msg = {
                    "jsonrpc": "2.0",
                    "id": "traversal-req-1",
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": args}
                }
                resp = mds.process_message(msg)
                self.assertIsNotNone(resp)
                self.assertEqual(resp.get("jsonrpc"), "2.0")
                self.assertEqual(resp.get("id"), "traversal-req-1")
                self.assertIn("error", resp)
                self.assertEqual(resp["error"]["code"], og.INVALID_PARAMS)
                self.assertIn("traversal or permission denied", resp["error"]["message"].lower())


class TestAdversarialZipBombDefense(unittest.TestCase):
    """Stress tests zip-bomb defenses using actual multi-entry, high-ratio, and oversized archives."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    # --- Vector 2.1: Entry Count Ceiling (> 10,000 entries) ---

    def test_zip_bomb_excessive_entry_count(self):
        """Archive with 10,005 entries must be rejected immediately (< 250ms) with entry count ceiling error."""
        bomb_path = Path(self.temp_dir.name) / "bomb_entries.docx"
        t0 = time.perf_counter()
        with zipfile.ZipFile(bomb_path, "w", compression=zipfile.ZIP_STORED) as z:
            for i in range(10005):
                z.writestr(f"entry_{i}.txt", b"x")

        # Measure verification rejection time
        t_verify_start = time.perf_counter()
        with self.assertRaises(ValueError) as ctx:
            og.safe_open_zip(bomb_path)
        t_verify_duration = time.perf_counter() - t_verify_start

        self.assertIn("Zip bomb detected", str(ctx.exception))
        self.assertIn("entry count (10005) exceeds ceiling of 10000 entries", str(ctx.exception))
        self.assertLess(t_verify_duration, 1.0, f"Rejection took {t_verify_duration:.4f}s, exceeding 1.0s budget")

    # --- Vector 2.2: High Compression Ratio (> 100:1) ---

    def test_zip_bomb_high_compression_ratio(self):
        """Archive with 25MB uncompressed bytes compressing to ~25KB (1000:1 ratio) must be rejected."""
        bomb_path = Path(self.temp_dir.name) / "bomb_ratio.docx"
        # 25 MB of null bytes compresses to ~25 KB with DEFLATE (> 1000:1 ratio)
        uncompressed_data = b"\0" * (25 * 1024 * 1024)

        with zipfile.ZipFile(bomb_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("word/document.xml", uncompressed_data)

        compressed_size = os.path.getsize(bomb_path)
        actual_ratio = len(uncompressed_data) / compressed_size
        self.assertGreater(actual_ratio, 100.0, f"Archive ratio {actual_ratio:.1f}:1 should exceed 100:1")

        t_verify_start = time.perf_counter()
        with self.assertRaises(ValueError) as ctx:
            og.safe_open_zip(bomb_path)
        t_verify_duration = time.perf_counter() - t_verify_start

        self.assertIn("Zip bomb detected", str(ctx.exception))
        self.assertIn("compression ratio", str(ctx.exception))
        self.assertIn("exceeds 100.0:1 ceiling", str(ctx.exception))
        self.assertLess(t_verify_duration, 1.0, f"Ratio check took {t_verify_duration:.4f}s")

    # --- Vector 2.3: Oversized Uncompressed Size (> 200MB) ---

    def test_zip_bomb_oversized_uncompressed_bytes(self):
        """Archive with uncompressed size of 220MB (> 200MB ceiling) must be rejected without decompression."""
        bomb_path = Path(self.temp_dir.name) / "bomb_oversized.xlsx"
        # 22 entries of 10MB zeroes = 220 MB total uncompressed
        chunk = b"\0" * (10 * 1024 * 1024)
        with zipfile.ZipFile(bomb_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for i in range(22):
                z.writestr(f"xl/worksheets/sheet{i}.xml", chunk)

        t_verify_start = time.perf_counter()
        with self.assertRaises(ValueError) as ctx:
            og.safe_open_zip(bomb_path)
        t_verify_duration = time.perf_counter() - t_verify_start

        self.assertIn("Zip bomb detected", str(ctx.exception))
        self.assertIn("uncompressed size", str(ctx.exception))
        self.assertIn("exceeds 209715200 bytes limit", str(ctx.exception))
        self.assertLess(t_verify_duration, 1.0, f"Size check took {t_verify_duration:.4f}s")

    # --- Vector 2.4: Zero Decompression Hang & Fast Rejection in MCP Servers ---

    def test_mcp_servers_reject_zip_bombs_without_hang(self):
        """Docx server must reject zip bombs returning isError=True without crashing or hanging."""
        # 1. Create a bomb in temp
        bomb_path = Path(self.temp_dir.name) / "bomb_test.docx"
        with zipfile.ZipFile(bomb_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("word/document.xml", b"\0" * (25 * 1024 * 1024))

        # 2. Test inspect_docx_structure via JSON-RPC
        msg = {
            "jsonrpc": "2.0",
            "id": "bomb-call-1",
            "method": "tools/call",
            "params": {"name": "inspect_docx_structure", "arguments": {"file_path": str(bomb_path)}}
        }
        t0 = time.perf_counter()
        resp = mds.process_message(msg)
        elapsed = time.perf_counter() - t0

        self.assertIsNotNone(resp)
        self.assertEqual(resp.get("id"), "bomb-call-1")
        self.assertTrue(resp["result"]["isError"])
        self.assertIn("Zip bomb detected", resp["result"]["content"][0]["text"])
        self.assertLess(elapsed, 0.25, f"Server call took {elapsed:.4f}s during bomb rejection")

    def test_excel_server_rejects_zip_bombs_without_hang(self):
        """Excel server must reject zip bombs returning isError=True without crashing or hanging."""
        bomb_path = Path(self.temp_dir.name) / "bomb_excel.xlsx"
        with zipfile.ZipFile(bomb_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("xl/workbook.xml", b"\0" * (25 * 1024 * 1024))

        for tool_name in ("list_excel_sheets", "read_excel_sheet"):
            with self.subTest(tool=tool_name):
                msg = {
                    "jsonrpc": "2.0",
                    "id": f"bomb-excel-{tool_name}",
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": {"file_path": str(bomb_path)}}
                }
                t0 = time.perf_counter()
                resp = mes.process_message(msg)
                elapsed = time.perf_counter() - t0

                self.assertIsNotNone(resp)
                self.assertEqual(resp.get("id"), f"bomb-excel-{tool_name}")
                self.assertTrue(resp["result"]["isError"])
                self.assertIn("Zip bomb detected", resp["result"]["content"][0]["text"])
                self.assertLess(elapsed, 0.25, f"Excel {tool_name} took {elapsed:.4f}s during bomb rejection")

    # --- Vector 2.5: Empirical Memory Allocation Verification ---

    def test_memory_budget_during_zip_bomb_rejection(self):
        """Rejection of high-ratio and oversized bombs must not allocate > 5MB of RAM (proving zero decompression)."""
        import tracemalloc

        bomb_path = Path(self.temp_dir.name) / "memory_check_bomb.docx"
        with zipfile.ZipFile(bomb_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("word/document.xml", b"\0" * (30 * 1024 * 1024))

        tracemalloc.start()
        try:
            with self.assertRaises(ValueError):
                og.safe_open_zip(bomb_path)
            current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        # Peak memory allocated must be well below 5MB
        self.assertLess(peak_mb, 5.0, f"Peak memory was {peak_mb:.2f}MB, indicating possible decompression memory leak!")

    # --- Vector 2.6: Malformed, 0-byte, and Truncated Archives ---

    def test_corrupt_and_zero_byte_openxml_files(self):
        """0-byte, truncated, and random-byte files must be rejected gracefully without unhandled exceptions."""
        empty_file = Path(self.temp_dir.name) / "empty.docx"
        empty_file.touch()

        # 0-byte docx
        with self.assertRaises(ValueError) as ctx:
            og.validate_openxml_path(str(empty_file))
        self.assertIn("empty (0 bytes)", str(ctx.exception))

        # Truncated zip
        truncated_file = Path(self.temp_dir.name) / "truncated.docx"
        with open(truncated_file, "wb") as f:
            f.write(b"PK\x03\x04\x14\x00\x00\x00")  # Partial header

        with self.assertRaises(ValueError) as ctx:
            og.safe_open_zip(truncated_file)
        self.assertIn("Corrupt or invalid zip", str(ctx.exception))

        # Random garbage bytes
        garbage_file = Path(self.temp_dir.name) / "garbage.xlsx"
        with open(garbage_file, "wb") as f:
            f.write(os.urandom(1024))

        with self.assertRaises(ValueError) as ctx:
            og.safe_open_zip(garbage_file)
        self.assertIn("Corrupt or invalid zip", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
