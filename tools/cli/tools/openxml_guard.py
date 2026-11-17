#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
OpenXML Security & Protocol Defense Guard
-----------------------------------------
Shared hardening library for OpenXML MCP servers (Word .docx and Excel .xlsx).
Provides:
  1. Canonical workspace path traversal validation & sandbox enforcement.
  2. Zip-bomb defense (uncompressed size, compression ratio, entry count).
  3. OpenXML XML parsing resilience (handling malformed XML, missing parts, 0-byte files).
  4. Standard JSON-RPC 2.0 error and response helpers (-32700 to -32603).
"""

import os
import sys
import zipfile
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Security Thresholds
MAX_FILE_SIZE = 50 * 1024 * 1024          # 50 MB
MAX_UNCOMPRESSED_SIZE = 200 * 1024 * 1024  # 200 MB
MAX_RATIO = 100.0                          # 100:1 compression ratio limit
MAX_ZIP_ENTRIES = 10000                    # 10,000 entries threshold

# JSON-RPC 2.0 Standard Error Codes
PARSE_ERROR = -32700        # Invalid JSON was received by the server.
INVALID_REQUEST = -32600    # The JSON sent is not a valid Request object.
METHOD_NOT_FOUND = -32601   # The method does not exist / is not available.
INVALID_PARAMS = -32602     # Invalid method parameter(s).
INTERNAL_ERROR = -32603     # Internal JSON-RPC error.


def get_workspace_root() -> Path:
    """Returns canonical workspace root directory from environment or current working directory."""
    env_root = os.environ.get("SYNAPSE_PROJECT_ROOT") or os.environ.get("SYNAPSE_WORKSPACE")
    if env_root:
        return Path(env_root).resolve()
    repo_root = Path(__file__).resolve().parent.parent
    cwd = Path.cwd().resolve()
    # If daemon was launched from an application bundle (e.g. AppData/Local/Programs/antigravity), default to repo_root
    cwd_lower = str(cwd).lower()
    if "antigravity" in cwd_lower or "electron" in cwd_lower or "programs" in cwd_lower:
        return repo_root
    for prefix in get_sensitive_prefixes():
        try:
            res_prefix = prefix.resolve()
            if cwd == res_prefix or res_prefix in cwd.parents:
                return repo_root
        except (ValueError, OSError):
            continue
    return cwd


def get_sensitive_prefixes() -> List[Path]:
    """Returns list of sensitive system directories that must never be accessed."""
    prefixes: List[Path] = [
        Path("/etc"),
        Path("/var/run"),
        Path("/proc"),
        Path("/sys"),
        Path("/dev"),
        Path("/root"),
    ]

    # User credential directories
    try:
        user_home = Path.home().resolve()
        prefixes.extend([
            user_home / ".ssh",
            user_home / ".aws",
            user_home / ".gnupg",
            user_home / ".config",
        ])
    except (OSError, RuntimeError) as err:
        sys.stderr.write(f"Warning: Failed to resolve user home: {err}\n")

    # Windows system directories
    if os.name == "nt":
        win_dir = os.environ.get("SystemRoot", "C:\\Windows")
        prefixes.extend([
            Path(win_dir),
            Path(win_dir) / "System32",
            Path(win_dir) / "SysWOW64",
            Path("C:\\Program Files"),
            Path("C:\\Program Files (x86)"),
        ])

    return prefixes


def validate_openxml_path(
    path: Union[str, Path],
    workspace_root: Optional[Union[str, Path]] = None,
    allowed_extensions: Tuple[str, ...] = ('.docx', '.xlsx'),
    max_file_size: int = MAX_FILE_SIZE,
    allow_empty: bool = False
) -> Path:
    """
    Validates that a path is safe, does not escape workspace boundaries,
    does not point to sensitive directories, exists, and is a valid OpenXML document.

    Raises:
        ValueError: If path is empty, non-string, wrong extension, empty file (0 bytes), or exceeds size.
        PermissionError: If path contains null bytes, UNC prefixes, traversal escapes, or points to system directories.
        FileNotFoundError: If the file does not exist on disk.
    """
    if not path or not isinstance(path, (str, Path)):
        raise ValueError("File path must be a non-empty string")

    raw_path = str(path).strip()
    if not raw_path:
        raise ValueError("File path cannot be blank")

    # Reject null bytes
    if "\0" in raw_path:
        raise PermissionError(f"Access denied: path contains null bytes '{raw_path}'")

    # Reject UNC paths (Windows network shares)
    if raw_path.startswith("\\\\") or raw_path.startswith("//"):
        raise PermissionError(f"Access denied: UNC paths are not permitted '{raw_path}'")

    # Normalize backslashes to forward slashes for cross-platform path resolution
    normalized_path = raw_path.replace("\\", "/")
    target = Path(normalized_path).resolve()

    # Determine boundary roots
    root = Path(workspace_root).resolve() if workspace_root else get_workspace_root()
    temp_dir = Path(tempfile.gettempdir()).resolve()

    # Check sensitive system prefixes without swallowing PermissionError
    sensitive_prefixes = get_sensitive_prefixes()
    for prefix in sensitive_prefixes:
        try:
            resolved_prefix = prefix.resolve()
        except (ValueError, OSError):
            continue
        if target == resolved_prefix or resolved_prefix in target.parents:
            raise PermissionError(f"Access denied: path points to protected system directory '{raw_path}'")

    # Enforce boundary: MUST be inside workspace root OR inside temp directory
    is_in_root = False
    try:
        is_in_root = (target == root or root in target.parents or target.is_relative_to(root))
    except (ValueError, AttributeError):
        try:
            target.relative_to(root)
            is_in_root = True
        except ValueError:
            is_in_root = False

    is_in_temp = False
    try:
        is_in_temp = (target == temp_dir or temp_dir in target.parents or target.is_relative_to(temp_dir))
    except (ValueError, AttributeError):
        try:
            target.relative_to(temp_dir)
            is_in_temp = True
        except ValueError:
            is_in_temp = False

    repo_root = Path(__file__).resolve().parent.parent
    is_in_repo = False
    try:
        is_in_repo = (target == repo_root or repo_root in target.parents or target.is_relative_to(repo_root))
    except (ValueError, AttributeError):
        try:
            target.relative_to(repo_root)
            is_in_repo = True
        except ValueError:
            is_in_repo = False

    if not is_in_root and not is_in_temp and not is_in_repo:
        raise PermissionError(f"Access denied: path '{raw_path}' resolves outside authorized workspace '{root}'")

    if not target.exists():
        raise FileNotFoundError(f"File not found: '{raw_path}'")

    if not target.is_file():
        raise ValueError(f"Path is not a regular file: '{raw_path}'")

    # Validate file size: reject 0-byte empty files unless explicitly permitted
    file_size = target.stat().st_size
    if not allow_empty and file_size == 0:
        raise ValueError(f"OpenXML file is empty (0 bytes): '{raw_path}'")

    if max_file_size and file_size > max_file_size:
        raise ValueError(f"File exceeds maximum allowed size ({file_size} > {max_file_size} bytes)")

    # Validate allowed extensions
    if allowed_extensions:
        ext = target.suffix.lower()
        valid_exts = tuple(e.lower() for e in allowed_extensions)
        if ext not in valid_exts:
            raise ValueError(f"Invalid file extension '{ext}'. Allowed: {', '.join(allowed_extensions)}")

    return target


def validate_docx_path(path: str, workspace_root: Optional[Union[str, Path]] = None) -> str:
    """Convenience wrapper validating .docx paths and returning string representation."""
    p = validate_openxml_path(path, workspace_root=workspace_root, allowed_extensions=('.docx',))
    return str(p)


def validate_excel_path(path: str, workspace_root: Optional[Union[str, Path]] = None) -> str:
    """Convenience wrapper validating .xlsx paths and returning string representation."""
    p = validate_openxml_path(path, workspace_root=workspace_root, allowed_extensions=('.xlsx',))
    return str(p)


def validate_output_path(
    path: Union[str, Path],
    workspace_root: Optional[Union[str, Path]] = None,
    allowed_extensions: Optional[Tuple[str, ...]] = None,
    create_parent: bool = True,
    is_dir: bool = False
) -> Path:
    """
    Validates destination output paths (e.g. for image extraction or exported spreadsheets)
    to ensure output files do not escape the workspace sandbox or overwrite system files.
    """
    if not path or not isinstance(path, (str, Path)):
        raise ValueError("Output path must be a non-empty string")

    raw_path = str(path).strip()
    if not raw_path:
        raise ValueError("Output path cannot be blank")

    if "\0" in raw_path:
        raise PermissionError(f"Access denied: output path contains null bytes '{raw_path}'")

    if raw_path.startswith("\\\\") or raw_path.startswith("//"):
        raise PermissionError(f"Access denied: UNC paths are not permitted '{raw_path}'")

    target = Path(raw_path).resolve()
    root = Path(workspace_root).resolve() if workspace_root else get_workspace_root()
    temp_dir = Path(tempfile.gettempdir()).resolve()

    # Reject system directories
    for prefix in get_sensitive_prefixes():
        try:
            resolved_prefix = prefix.resolve()
        except (ValueError, OSError):
            continue
        if target == resolved_prefix or resolved_prefix in target.parents:
            raise PermissionError(f"Access denied: output destination in protected directory '{raw_path}'")

    # Enforce boundary
    is_in_root = False
    try:
        is_in_root = (target == root or root in target.parents or target.is_relative_to(root))
    except (ValueError, AttributeError):
        try:
            target.relative_to(root)
            is_in_root = True
        except ValueError:
            is_in_root = False

    is_in_temp = False
    try:
        is_in_temp = (target == temp_dir or temp_dir in target.parents or target.is_relative_to(temp_dir))
    except (ValueError, AttributeError):
        try:
            target.relative_to(temp_dir)
            is_in_temp = True
        except ValueError:
            is_in_temp = False

    repo_root = Path(__file__).resolve().parent.parent
    is_in_repo = False
    try:
        is_in_repo = (target == repo_root or repo_root in target.parents or target.is_relative_to(repo_root))
    except (ValueError, AttributeError):
        try:
            target.relative_to(repo_root)
            is_in_repo = True
        except ValueError:
            is_in_repo = False

    if not is_in_root and not is_in_temp and not is_in_repo:
        raise PermissionError(f"Access denied: output path '{raw_path}' resolves outside workspace '{root}'")

    if allowed_extensions:
        ext = target.suffix.lower()
        valid_exts = tuple(e.lower() for e in allowed_extensions)
        if ext not in valid_exts:
            raise ValueError(f"Invalid output extension '{ext}'. Allowed: {', '.join(allowed_extensions)}")

    if create_parent:
        if is_dir or not target.suffix:
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)

    return target


def safe_open_zip(
    zip_path: Union[str, Path],
    max_entries: int = MAX_ZIP_ENTRIES,
    max_uncompressed_size: int = MAX_UNCOMPRESSED_SIZE,
    max_ratio: float = MAX_RATIO
) -> zipfile.ZipFile:
    """
    Opens a zip archive with multi-tier zip-bomb and integrity safeguards:
      - Validates archive is a valid zip without crashing.
      - Enforces total entry count ceiling (<= max_entries).
      - Enforces uncompressed size limit (<= max_uncompressed_size).
      - Enforces compression ratio limit (<= max_ratio).

    Raises:
        ValueError: If zip bomb or corrupt archive is detected.
    """
    try:
        z = zipfile.ZipFile(str(zip_path), "r")
    except zipfile.BadZipFile as err:
        raise ValueError(f"Corrupt or invalid zip archive: {err}")
    except (KeyError, OSError, UnicodeDecodeError) as err:
        raise ValueError(f"Failed to open zip archive: {err}")

    try:
        infolist = z.infolist()
    except Exception as err:
        z.close()
        raise ValueError(f"Corrupt zip table of contents: {err}")

    # 1. Entry count ceiling check
    if len(infolist) > max_entries:
        z.close()
        raise ValueError(
            f"Zip bomb detected: entry count ({len(infolist)}) exceeds ceiling of {max_entries} entries."
        )

    # 2. Total uncompressed size check
    total_uncompressed = sum(info.file_size for info in infolist)
    if total_uncompressed > max_uncompressed_size:
        z.close()
        raise ValueError(
            f"Zip bomb detected: uncompressed size ({total_uncompressed} bytes) exceeds {max_uncompressed_size} bytes limit."
        )

    # 3. Compression ratio check
    try:
        compressed_size = os.path.getsize(str(zip_path))
    except (OSError, ValueError):
        compressed_size = 0

    if compressed_size > 0 and (total_uncompressed / compressed_size) > max_ratio:
        ratio = total_uncompressed / compressed_size
        z.close()
        raise ValueError(
            f"Zip bomb detected: compression ratio ({ratio:.1f}:1) exceeds {max_ratio:.1f}:1 ceiling."
        )

    return z


def safe_parse_xml(source: Any) -> ET.Element:
    """
    Parses XML data safely from stream, bytes, or string.
    Catches ET.ParseError, KeyError, and UnicodeDecodeError, raising clean ValueError.
    """
    try:
        if isinstance(source, (bytes, str)):
            return ET.fromstring(source)
        tree = ET.parse(source)
        return tree.getroot()
    except ET.ParseError as err:
        raise ValueError(f"Malformed XML document: {err}")
    except (KeyError, UnicodeDecodeError) as err:
        raise ValueError(f"XML decoding error: {err}")


def safe_read_xml_from_zip(z: zipfile.ZipFile, entry_name: str) -> Optional[ET.Element]:
    """
    Safely reads and parses an XML entry from an open zip archive.
    Returns None if entry is missing, or parsed root Element if successful.
    Raises ValueError on parse or decode failure.
    """
    if entry_name not in z.namelist():
        return None
    try:
        with z.open(entry_name) as f:
            return safe_parse_xml(f)
    except (KeyError, ET.ParseError, UnicodeDecodeError, ValueError) as err:
        raise ValueError(f"Corrupt OpenXML entry '{entry_name}': {err}")


def jsonrpc_error_response(
    code: int,
    message: str,
    req_id: Any = None,
    data: Any = None
) -> Dict[str, Any]:
    """Constructs a compliant JSON-RPC 2.0 error response preserving request id."""
    err: Dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": err
    }


def jsonrpc_success_response(result: Any, req_id: Any = None) -> Dict[str, Any]:
    """Constructs a compliant JSON-RPC 2.0 success response."""
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": result
    }


def mcp_tool_result(content_text: str, is_error: bool = False, req_id: Any = None) -> Dict[str, Any]:
    """Constructs a compliant MCP CallToolResult object."""
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "content": [{"type": "text", "text": content_text}],
            "isError": is_error
        }
    }
