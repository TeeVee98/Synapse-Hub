# Hướng Dẫn Cấu Hình Model Context Protocol (MCP) Server — Synapse Hub

> **Tác giả & Bản quyền MIT:** Synapse Hub là phần mềm mã nguồn mở được phát triển bởi **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) theo giấy phép MIT.

---

## 1. Giới Thiệu

Synapse Hub cung cấp giao thức **Model Context Protocol (MCP)** tiêu chuẩn (JSON-RPC 2.0 stdio), cho phép các trợ lý lập trình AI (Cursor, Claude Code, Windsurf, Google Antigravity, GitHub Copilot) tương tác trực tiếp với các công cụ kiểm thử tự động, linter AST và các cổng chất lượng của kho mã nguồn.

### 5 Công Cụ MCP Cốt Lõi (Tier-S Standard):

| Tên Công Cụ | Mô Tả Chức Năng | Đầu Vào (Parameters) |
|---|---|---|
| `synapse_lint` | Chạy bộ linter tĩnh & AST analyzer phát hiện fake pass, static sleep, catch rỗng. | `target_path`: đường dẫn tệp hoặc thư mục. |
| `synapse_verify` | Chạy 10 Cổng Chất Lượng Definition-of-Done (DoD) với kiểm tra trước pre-flight. | `repo_path`: đường dẫn repo (mặc định CWD). |
| `synapse_mutate` | Kiểm thử đột biến AST (micro-mutation) đo độ nhạy của các câu lệnh assert. | `test_file`: tệp test, `sample_rate`: tỷ lệ lấy mẫu (0.0-1.0). |
| `synapse_distill_logs` | Tinh gọn log kiểm thử cồng kềnh (>500 dòng) thành bản tóm tắt nguyên nhân lỗi. | `log_path`: đường dẫn tệp log. |
| `synapse_security_scan` | Quét lỗ hổng bảo mật phụ thuộc (Python/NPM) và rò rỉ secret ở chế độ fail-closed. | `repo_path`: thư mục repo, `strict`: boolean (default: true). |

---

## 2. Hướng Dẫn Cấu Hình Nhanh (1 Phút)

### 2.1 Cấu Hình Cho Cursor (`.cursor/mcp.json`)

Tạo hoặc chỉnh sửa tệp `.cursor/mcp.json` trong thư mục dự án hoặc cấu hình toàn cục:

```json
{
  "mcpServers": {
    "synapse-hub": {
      "command": "node",
      "args": ["bin/agent-qa.js", "mcp"],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

*Hoặc nếu sử dụng Python trực tiếp:*

```json
{
  "mcpServers": {
    "synapse-hub": {
      "command": "python",
      "args": ["tools/mcp/mcp_server.py"],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

---

### 2.2 Cấu Hình Cho Claude Desktop (`claude_desktop_config.json`)

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "synapse-hub": {
      "command": "python",
      "args": ["D:/Synapse Hub/tools/mcp/mcp_server.py"],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

---

### 2.3 Cấu Hình Cho Windsurf (`~/.codeium/windsurf/mcp_config.json`)

```json
{
  "mcpServers": {
    "synapse-hub": {
      "command": "npx",
      "args": ["@teevee98/synapse-hub", "mcp"]
    }
  }
}
```

---

### 2.4 Cấu Hình Cho Google Antigravity

Trong tệp cấu hình plugin hoặc IDE settings (`antigravity.config.json`):

```json
{
  "mcpServers": {
    "synapse-hub": {
      "command": "python",
      "args": ["tools/mcp/mcp_server.py"]
    }
  }
}
```

---

## 3. Kiểm Tra Kết Nối

Chạy lệnh CLI sau để xác nhận server MCP phản hồi tốt:

```bash
# Kiểm tra khởi động thông qua Node CLI Launcher
node bin/agent-qa.js mcp --help

# Kiểm tra trực tiếp qua Python Engine
python tools/mcp/mcp_server.py --help
```
