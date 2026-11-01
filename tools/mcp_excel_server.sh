#!/usr/bin/env bash
# Enterprise MCP Excel Server Wrapper
set -e
python3 "$(dirname "$0")/mcp_excel_server.py" "$@"
