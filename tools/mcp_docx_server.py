#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Enterprise Cross-Platform MCP Docx Server (Zero-Dependency)
-----------------------------------------------------------
Implements Model Context Protocol (MCP) JSON-RPC 2.0 stdio server
for reading, inspecting, searching, and extracting text, tables,
and embedded screenshots/images from Microsoft Word (.docx) documents.

Works 100% offline with Python Standard Library (zipfile + xml.etree.ElementTree).
"""

import os
import sys
import json
import zipfile
import re
import argparse
import xml.etree.ElementTree as ET
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

# Enforce UTF-8 stdio encoding for Windows/Linux/macOS console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SERVER_VERSION = "3.8.4"
MAX_DOCX_SIZE = 50 * 1024 * 1024          # 50 MB
MAX_UNCOMPRESSED_SIZE = 200 * 1024 * 1024  # 200 MB
MAX_RATIO = 100                            # 100:1 compression ratio limit

# Office Open XML Namespaces for WordprocessingML
NS_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
NS_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
NS_WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
NS_PIC = "{http://schemas.openxmlformats.org/drawingml/2006/picture}"
NS_V = "{urn:schemas-microsoft-com:vml}"
NS_CP = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"
NS_DC = "{http://purl.org/dc/elements/1.1/}"
NS_DCTERMS = "{http://purl.org/dc/terms/}"


def validate_docx_path(path: str, workspace_root: Optional[Union[str, Path]] = None) -> str:
    """Validates that path is safe, does not resolve to sensitive system directories, and is a valid .docx file."""
    target = validate_openxml_path(
        path,
        workspace_root=workspace_root,
        allowed_extensions=('.docx',),
        max_file_size=MAX_DOCX_SIZE
    )
    return str(target)


def get_docx_zip(docx_path: str) -> zipfile.ZipFile:
    """Opens docx zip with zip-bomb safeguards."""
    valid_path = validate_docx_path(docx_path)
    return safe_open_zip(
        valid_path,
        max_entries=MAX_ZIP_ENTRIES,
        max_uncompressed_size=MAX_UNCOMPRESSED_SIZE,
        max_ratio=MAX_RATIO
    )


def get_docx_relationships(z: zipfile.ZipFile) -> Dict[str, str]:
    """Reads word/_rels/document.xml.rels and returns mapping of rId -> target media path."""
    rels_map = {}
    rels_entry = "word/_rels/document.xml.rels"
    if rels_entry not in z.namelist():
        return rels_map

    try:
        with z.open(rels_entry) as f:
            tree = ET.parse(f)
            root = tree.getroot()
            for elem in root:
                rid = elem.attrib.get("Id")
                target = elem.attrib.get("Target")
                if rid and target:
                    # Normalize target to relative zip path inside word/
                    if not target.startswith("word/") and not target.startswith("/"):
                        norm_target = f"word/{target}" if not target.startswith("media/") else f"word/{target}"
                    else:
                        norm_target = target.lstrip("/")
                    rels_map[rid] = norm_target
    except (ET.ParseError, KeyError, UnicodeDecodeError, ValueError) as err:
        sys.stderr.write(f"Warning: Failed to parse relationships: {err}\n")

    return rels_map


def get_docx_metadata(z: zipfile.ZipFile) -> Dict[str, str]:
    """Extracts core document metadata from docProps/core.xml."""
    meta = {"title": "", "creator": "", "created": "", "modified": "", "description": ""}
    core_entry = "docProps/core.xml"
    if core_entry not in z.namelist():
        return meta

    try:
        with z.open(core_entry) as f:
            tree = ET.parse(f)
            root = tree.getroot()
            for child in root:
                tag = child.tag
                text = (child.text or "").strip()
                if tag == f"{NS_DC}title":
                    meta["title"] = text
                elif tag == f"{NS_DC}creator":
                    meta["creator"] = text
                elif tag == f"{NS_DC}description":
                    meta["description"] = text
                elif tag == f"{NS_DCTERMS}created":
                    meta["created"] = text
                elif tag == f"{NS_DCTERMS}modified":
                    meta["modified"] = text
    except (ET.ParseError, KeyError, UnicodeDecodeError, ValueError) as err:
        sys.stderr.write(f"Warning: Failed to parse metadata: {err}\n")

    return meta


def _extract_heading_level(p_elem: ET.Element) -> Optional[int]:
    """Determines heading level (1 to 6) from paragraph style if present."""
    p_pr = p_elem.find(f"{NS_W}pPr")
    if p_pr is None:
        return None

    p_style = p_pr.find(f"{NS_W}pStyle")
    if p_style is None:
        return None

    val = p_style.attrib.get(f"{NS_W}val", "")
    val_clean = val.lower().replace(" ", "").replace("_", "")

    # Match Heading1, Heading2, H1, H2, Heading 1, etc.
    m = re.search(r'(?:heading|tieude|h)([1-6])', val_clean)
    if m:
        return int(m.group(1))

    if val_clean in ("title", "tieude"):
        return 1
    if val_clean in ("subtitle", "phutieude"):
        return 2

    # Check for direct numeric style (e.g. style="1" or "2")
    if val.isdigit() and 1 <= int(val) <= 6:
        return int(val)

    return None


def _extract_paragraph_text(p_elem: ET.Element) -> str:
    """Concatenates text runs inside a paragraph."""
    parts = []
    for node in p_elem.iter(f"{NS_W}t"):
        if node.text:
            parts.append(node.text)
    return "".join(parts).strip()


def _find_images_in_paragraph(p_elem: ET.Element, rels_map: Dict[str, str]) -> List[Dict[str, str]]:
    """Identifies image drawings and blip embeds inside a paragraph."""
    images = []

    # 1. Search drawing elements
    for drawing in p_elem.iter(f"{NS_W}drawing"):
        doc_pr = drawing.find(f".//{NS_WP}docPr")
        name = doc_pr.attrib.get("name", "") if doc_pr is not None else ""
        descr = doc_pr.attrib.get("descr", "") if doc_pr is not None else ""

        for blip in drawing.iter(f"{NS_A}blip"):
            embed_id = blip.attrib.get(f"{NS_R}embed") or blip.attrib.get(f"{NS_R}link")
            if embed_id and embed_id in rels_map:
                target_zip_path = rels_map[embed_id]
                images.append({
                    "r_id": embed_id,
                    "zip_path": target_zip_path,
                    "filename": os.path.basename(target_zip_path),
                    "caption": descr or name or os.path.basename(target_zip_path),
                })

    # 2. Search legacy VML pict elements
    for pict in p_elem.iter(f"{NS_W}pict"):
        for imagedata in pict.iter(f"{NS_V}imagedata"):
            r_id = imagedata.attrib.get(f"{NS_R}id")
            if r_id and r_id in rels_map:
                target_zip_path = rels_map[r_id]
                images.append({
                    "r_id": r_id,
                    "zip_path": target_zip_path,
                    "filename": os.path.basename(target_zip_path),
                    "caption": os.path.basename(target_zip_path),
                })

    return images


def _extract_table_matrix(tbl_elem: ET.Element) -> List[List[str]]:
    """Extracts rows and cell text from a table element."""
    matrix = []
    for tr in tbl_elem.iter(f"{NS_W}tr"):
        row = []
        for tc in tr.iter(f"{NS_W}tc"):
            cell_text_parts = []
            for p in tc.iter(f"{NS_W}p"):
                t = _extract_paragraph_text(p)
                if t:
                    cell_text_parts.append(t)
            row.append(" ".join(cell_text_parts))
        if any(row):
            matrix.append(row)
    return matrix


def _table_to_markdown(matrix: List[List[str]]) -> str:
    """Formats a 2D matrix into a clean Markdown table."""
    if not matrix:
        return ""

    num_cols = max(len(row) for row in matrix)
    if num_cols == 0:
        return ""

    # Normalize rows
    norm_matrix = []
    for r in matrix:
        padded = r + [""] * (num_cols - len(r))
        clean_row = [c.replace("\n", " ").replace("|", "\\|").strip() for c in padded]
        norm_matrix.append(clean_row)

    header = norm_matrix[0]
    separator = ["---"] * num_cols
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in norm_matrix[1:]:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def inspect_docx(docx_path: str) -> Dict[str, Any]:
    """Inspects docx structure, outline, headings, tables, and embedded images."""
    with get_docx_zip(docx_path) as z:
        metadata = get_docx_metadata(z)
        rels_map = get_docx_relationships(z)

        doc_entry = "word/document.xml"
        if doc_entry not in z.namelist():
            raise ValueError("Corrupt .docx: missing word/document.xml")

        try:
            with z.open(doc_entry) as f:
                root = safe_parse_xml(f)
        except ValueError as err:
            raise ValueError(f"Corrupt .docx: {err}")

        body = root.find(f"{NS_W}body")
        if body is None:
            raise ValueError("Corrupt .docx: missing <w:body> element")

        headings = []
        images_summary = []
        total_paragraphs = 0
        total_tables = 0
        current_heading = "Document Root"

        for elem in body:
            if elem.tag == f"{NS_W}p":
                total_paragraphs += 1
                level = _extract_heading_level(elem)
                text = _extract_paragraph_text(elem)
                if level is not None and text:
                    current_heading = text
                    headings.append({"level": level, "title": text})

                imgs = _find_images_in_paragraph(elem, rels_map)
                for img in imgs:
                    images_summary.append({
                        "filename": img["filename"],
                        "caption": img["caption"],
                        "nearest_heading": current_heading,
                        "context_text": text[:120] if text else "",
                    })
            elif elem.tag == f"{NS_W}tbl":
                total_tables += 1

        all_media_files = [n for n in z.namelist() if n.startswith("word/media/")]

        return {
            "file_name": os.path.basename(docx_path),
            "metadata": metadata,
            "counts": {
                "total_paragraphs": total_paragraphs,
                "total_headings": len(headings),
                "total_tables": total_tables,
                "embedded_images_in_body": len(images_summary),
                "total_media_files_in_zip": len(all_media_files),
            },
            "outline": headings,
            "images": images_summary,
        }


def extract_docx_images(docx_path: str, output_dir: Optional[str] = None, max_images: int = 50) -> List[Dict[str, Any]]:
    """Extracts embedded images/screenshots to a directory with security checks."""
    valid_path = validate_docx_path(docx_path)
    base_name = os.path.splitext(os.path.basename(valid_path))[0]

    if not output_dir:
        output_dir = os.path.join(os.getcwd(), "reports", "docx_media", base_name)

    target_dir = validate_output_path(output_dir, create_parent=True)
    target_dir.mkdir(parents=True, exist_ok=True)

    extracted_records = []
    with get_docx_zip(valid_path) as z:
        rels_map = get_docx_relationships(z)

        # Build mapping of image zip path to context
        img_contexts = {}
        current_heading = "Document Root"

        doc_entry = "word/document.xml"
        if doc_entry in z.namelist():
            try:
                with z.open(doc_entry) as f:
                    root = safe_parse_xml(f)
                    body = root.find(f"{NS_W}body")
                    if body is not None:
                        for elem in body:
                            if elem.tag == f"{NS_W}p":
                                level = _extract_heading_level(elem)
                                text = _extract_paragraph_text(elem)
                                if level is not None and text:
                                    current_heading = text
                                imgs = _find_images_in_paragraph(elem, rels_map)
                                for img in imgs:
                                    zp = img["zip_path"]
                                    if zp not in img_contexts:
                                        img_contexts[zp] = {
                                            "caption": img["caption"],
                                            "heading": current_heading,
                                            "context": text,
                                        }
            except ValueError as err:
                sys.stderr.write(f"Warning: Failed to parse image context: {err}\n")

        media_entries = [n for n in z.namelist() if n.startswith("word/media/")]
        for count, entry in enumerate(media_entries):
            if count >= max_images:
                break

            filename = os.path.basename(entry.replace("\\", "/"))
            dest_file = (target_dir / filename).resolve()

            # Zip Slip / Path traversal safety check
            if not dest_file.is_relative_to(target_dir):
                continue

            with z.open(entry) as src, open(dest_file, "wb") as dst:
                data = src.read()
                dst.write(data)

            ctx = img_contexts.get(entry, {})
            extracted_records.append({
                "filename": filename,
                "saved_path": str(dest_file),
                "size_bytes": len(data),
                "nearest_heading": ctx.get("heading", current_heading),
                "caption": ctx.get("caption", filename),
                "context_text": ctx.get("context", "")[:150],
            })

    return extracted_records


def read_docx_content(docx_path: str, heading_filter: Optional[str] = None, max_paragraphs: int = 250, extract_images_dir: Optional[str] = None) -> str:
    """Reads docx paragraphs and tables formatted as clean Markdown."""
    extracted_map = {}
    if extract_images_dir:
        records = extract_docx_images(docx_path, output_dir=extract_images_dir)
        for r in records:
            extracted_map[r["filename"]] = r["saved_path"]

    with get_docx_zip(docx_path) as z:
        rels_map = get_docx_relationships(z)
        doc_entry = "word/document.xml"
        if doc_entry not in z.namelist():
            raise ValueError("Corrupt .docx: missing word/document.xml")
        try:
            with z.open(doc_entry) as f:
                root = safe_parse_xml(f)
        except ValueError as err:
            raise ValueError(f"Corrupt .docx: {err}")

        body = root.find(f"{NS_W}body")
        if body is None:
            return ""

        output_lines = []
        current_heading = ""
        include_section = True if not heading_filter else False
        p_count = 0

        for elem in body:
            if elem.tag == f"{NS_W}p":
                level = _extract_heading_level(elem)
                text = _extract_paragraph_text(elem)

                if level is not None and text:
                    current_heading = text
                    if heading_filter:
                        include_section = heading_filter.lower() in text.lower()

                    if include_section:
                        prefix = "#" * max(1, min(6, level))
                        output_lines.append(f"\n{prefix} {text}\n")
                    continue

                if not include_section:
                    continue

                imgs = _find_images_in_paragraph(elem, rels_map)

                if text:
                    output_lines.append(text)
                    p_count += 1

                for img in imgs:
                    fname = img["filename"]
                    caption = img["caption"]
                    target_ref = extracted_map.get(fname, f"word/media/{fname}")
                    output_lines.append(f"\n![{caption}]({target_ref})\n")

                if p_count >= max_paragraphs:
                    output_lines.append("\n\n*(Truncated: reached max_paragraphs limit)*")
                    break

            elif elem.tag == f"{NS_W}tbl":
                if not include_section:
                    continue
                matrix = _extract_table_matrix(elem)
                md_table = _table_to_markdown(matrix)
                if md_table:
                    output_lines.append(f"\n{md_table}\n")

        return "\n\n".join(output_lines).strip()


def read_docx_tables(docx_path: str, table_index: Optional[int] = None) -> List[Dict[str, Any]]:
    """Extracts tables from a docx file as structured matrices and Markdown strings."""
    tables = []
    with get_docx_zip(docx_path) as z:
        doc_entry = "word/document.xml"
        if doc_entry not in z.namelist():
            raise ValueError("Corrupt .docx: missing word/document.xml")
        try:
            with z.open(doc_entry) as f:
                root = safe_parse_xml(f)
        except ValueError as err:
            raise ValueError(f"Corrupt .docx: {err}")
        body = root.find(f"{NS_W}body")
        if body is None:
            return tables

        idx = 0
        for elem in body:
            if elem.tag == f"{NS_W}tbl":
                if table_index is not None and idx != table_index:
                    idx += 1
                    continue
                matrix = _extract_table_matrix(elem)
                md = _table_to_markdown(matrix)
                tables.append({
                    "table_index": idx,
                    "rows": len(matrix),
                    "cols": len(matrix[0]) if matrix else 0,
                    "matrix": matrix,
                    "markdown": md,
                })
                idx += 1

    return tables


def search_docx(docx_path: str, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Searches for keyword or phrase across docx body paragraphs."""
    if not query:
        raise ValueError("Search query cannot be empty")

    results = []
    q_lower = query.lower()

    with get_docx_zip(docx_path) as z:
        rels_map = get_docx_relationships(z)
        doc_entry = "word/document.xml"
        if doc_entry not in z.namelist():
            raise ValueError("Corrupt .docx: missing word/document.xml")
        try:
            with z.open(doc_entry) as f:
                root = safe_parse_xml(f)
        except ValueError as err:
            raise ValueError(f"Corrupt .docx: {err}")
        body = root.find(f"{NS_W}body")
        if body is None:
            return results

        current_heading = "Document Root"
        p_index = 0

        for elem in body:
            if elem.tag == f"{NS_W}p":
                p_index += 1
                level = _extract_heading_level(elem)
                text = _extract_paragraph_text(elem)

                if level is not None and text:
                    current_heading = text

                if text and q_lower in text.lower():
                    imgs = _find_images_in_paragraph(elem, rels_map)
                    results.append({
                        "paragraph_index": p_index,
                        "heading": current_heading,
                        "matched_text": text,
                        "images": [img["filename"] for img in imgs],
                    })
                    if len(results) >= max_results:
                        break

    return results


# ----------------------------------------------------------------------
# MCP Protocol Handlers & Manifest
# ----------------------------------------------------------------------

MCP_DOCX_MANIFEST = {
    "tools": [
        {
            "name": "inspect_docx_structure",
            "description": "Inspects Microsoft Word (.docx) document structure: outline, metadata, heading hierarchy, tables count, and embedded screenshots/images count in 0.05s.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute or relative path to the .docx file"}
                },
                "required": ["file_path"]
            }
        },
        {
            "name": "read_docx_content",
            "description": "Reads docx document content converted cleanly to Markdown (headings, bullet points, tables, and image references). Supports section filtering to preserve AI context tokens.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the .docx file"},
                    "heading_filter": {"type": "string", "description": "Optional section heading to read (reads only this section)"},
                    "max_paragraphs": {"type": "integer", "description": "Maximum paragraphs to read (default: 200)"},
                    "extract_images_dir": {"type": "string", "description": "Optional directory to extract embedded images and embed local paths in markdown"}
                },
                "required": ["file_path"]
            }
        },
        {
            "name": "extract_docx_images",
            "description": "Extracts embedded screenshots and images from Word (.docx) to a local directory with surrounding context for Multimodal AI Vision analysis.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the .docx file"},
                    "output_dir": {"type": "string", "description": "Target folder for extracted images (defaults to reports/docx_media/<doc_name>)"},
                    "max_images": {"type": "integer", "description": "Maximum images to extract (default: 50)"}
                },
                "required": ["file_path"]
            }
        },
        {
            "name": "read_docx_tables",
            "description": "Extracts structured tables from a Word (.docx) document as JSON matrices and Markdown tables for test case requirements and matrix validation.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the .docx file"},
                    "table_index": {"type": "integer", "description": "Optional 0-based index of a specific table to extract"}
                },
                "required": ["file_path"]
            }
        },
        {
            "name": "search_docx",
            "description": "Searches for keywords or requirements across a Word (.docx) document and returns matching paragraphs with their parent heading and nearby screenshots.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the .docx file"},
                    "query": {"type": "string", "description": "Keyword or text phrase to locate"},
                    "max_results": {"type": "integer", "description": "Maximum search matches (default: 10)"}
                },
                "required": ["file_path", "query"]
            }
        }
    ]
}


def handle_tool_call(name: str, arguments: Dict[str, Any]) -> str:
    """Executes Docx MCP tool functions."""
    file_path = arguments.get("file_path", "")
    if not file_path:
        raise ValueError("Missing required 'file_path' argument")

    if name == "inspect_docx_structure":
        data = inspect_docx(file_path)
        return json.dumps(data, ensure_ascii=False, indent=2)

    elif name == "read_docx_content":
        heading_filter = arguments.get("heading_filter")
        max_paragraphs = int(arguments.get("max_paragraphs", 200))
        extract_images_dir = arguments.get("extract_images_dir")
        content = read_docx_content(file_path, heading_filter=heading_filter, max_paragraphs=max_paragraphs, extract_images_dir=extract_images_dir)
        return content or "*(Document is empty or filtered section not found)*"

    elif name == "extract_docx_images":
        output_dir = arguments.get("output_dir")
        max_images = int(arguments.get("max_images", 50))
        images = extract_docx_images(file_path, output_dir=output_dir, max_images=max_images)
        return json.dumps(images, ensure_ascii=False, indent=2)

    elif name == "read_docx_tables":
        table_idx = arguments.get("table_index")
        if table_idx is not None:
            table_idx = int(table_idx)
        tables = read_docx_tables(file_path, table_index=table_idx)
        return json.dumps(tables, ensure_ascii=False, indent=2)

    elif name == "search_docx":
        query = arguments.get("query", "")
        max_results = int(arguments.get("max_results", 10))
        results = search_docx(file_path, query=query, max_results=max_results)
        return json.dumps(results, ensure_ascii=False, indent=2)

    raise ValueError(f"Unknown MCP Docx tool: '{name}'")


MCP_DOCX_TOOL_NAMES = {t["name"] for t in MCP_DOCX_MANIFEST["tools"]}


def process_message(msg: Any) -> Optional[Dict[str, Any]]:
    """JSON-RPC 2.0 message handler for Docx MCP."""
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
                "serverInfo": {"name": "synapse-mcp-docx", "version": SERVER_VERSION}
            }
        }
    elif method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": MCP_DOCX_MANIFEST
        }
    elif method == "tools/call":
        params = msg.get("params")
        if not isinstance(params, dict):
            return jsonrpc_error_response(INVALID_PARAMS, "Invalid params: 'params' must be a dictionary", req_id=msg_id)

        tool_name = params.get("name")
        if not isinstance(tool_name, str) or not tool_name:
            return jsonrpc_error_response(INVALID_PARAMS, "Invalid params: tool 'name' must be a non-empty string", req_id=msg_id)

        if tool_name not in MCP_DOCX_TOOL_NAMES:
            return jsonrpc_error_response(METHOD_NOT_FOUND, f"Method not found: Unknown tool '{tool_name}'", req_id=msg_id)

        args = params.get("arguments")
        if args is None:
            args = {}
        if not isinstance(args, dict):
            return jsonrpc_error_response(INVALID_PARAMS, "Invalid params: 'arguments' must be a dictionary", req_id=msg_id)

        # Validate mandatory file_path argument
        file_path = args.get("file_path")
        if not file_path or not isinstance(file_path, str):
            return jsonrpc_error_response(INVALID_PARAMS, "Invalid params: 'file_path' is required and must be a non-empty string", req_id=msg_id)

        if tool_name == "search_docx":
            query = args.get("query")
            if not query or not isinstance(query, str):
                return jsonrpc_error_response(INVALID_PARAMS, "Invalid params: 'query' is required and must be a non-empty string", req_id=msg_id)

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


def run_stdio_server():
    """Runs standard JSON-RPC 2.0 stdio server loop."""
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


def main():
    """CLI dispatcher and stdio server entry point."""
    parser = argparse.ArgumentParser(description="Synapse Hub MCP Microsoft Word (.docx) Inspection & Extraction Server")
    parser.add_argument("command", nargs="?", default="mcp", choices=["mcp", "inspect", "read", "extract-images", "tables", "search"], help="Operation to perform (default: mcp)")
    parser.add_argument("file_path", nargs="?", help="Path to .docx document")
    parser.add_argument("--heading", help="Filter by section heading")
    parser.add_argument("--out-dir", help="Output directory for extracted images")
    parser.add_argument("--query", "-q", help="Search query string")
    parser.add_argument("--max", type=int, default=50, help="Maximum items/paragraphs/images to process")
    parser.add_argument("--index", type=int, help="Table index to read")

    args = parser.parse_args()

    if args.command == "mcp" and not args.file_path:
        run_stdio_server()
        return

    if not args.file_path:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "inspect":
            data = inspect_docx(args.file_path)
            print(json.dumps(data, ensure_ascii=False, indent=2))
        elif args.command == "read":
            content = read_docx_content(args.file_path, heading_filter=args.heading, max_paragraphs=args.max, extract_images_dir=args.out_dir)
            print(content)
        elif args.command == "extract-images":
            records = extract_docx_images(args.file_path, output_dir=args.out_dir, max_images=args.max)
            print(f"Extracted {len(records)} images:")
            for r in records:
                print(f"  • {r['filename']} ({r['size_bytes']} bytes) -> {r['saved_path']} [Section: {r['nearest_heading']}]")
        elif args.command == "tables":
            tables = read_docx_tables(args.file_path, table_index=args.index)
            print(json.dumps(tables, ensure_ascii=False, indent=2))
        elif args.command == "search":
            if not args.query:
                print("Error: --query is required for search command", file=sys.stderr)
                sys.exit(1)
            results = search_docx(args.file_path, query=args.query, max_results=args.max)
            print(json.dumps(results, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
