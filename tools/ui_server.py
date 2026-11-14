#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/ui_server.py — Synapse Hub Interactive QA Mission Control Web Server
-------------------------------------------------------------------------
Lightweight local web server (pure Python standard library, zero external deps).
Provides real-time interactive QA dashboard:
1. 1-Click execution for 10 Quality Gates DoD, Infer Linter, and Micro-Mutation.
2. Real-time streaming console logs directly in the browser via polling/SSE.
3. Interactive repository health, diagnostics, and Excel export.
"""

import os
import sys
import json
import time
import socket
import argparse
import threading
import subprocess
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Dict, Any, Optional

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEMPLATE_PATH = os.path.join(REPO_ROOT, "templates", "ui", "index.html")

COMMAND_MAP = {
    "verify": [sys.executable, os.path.join(REPO_ROOT, "tools", "verify_all.py"), "--mode", "hub"],
    "lint": [sys.executable, os.path.join(REPO_ROOT, "tools", "infer_linter.py")],
    "mutate": [sys.executable, os.path.join(REPO_ROOT, "tools", "micro_mutator.py"), "--min-score", "80"],
    "doctor": [sys.executable, os.path.join(REPO_ROOT, "tools", "check_env.py")],
    "analyze": [sys.executable, os.path.join(REPO_ROOT, "tools", "analyze_project.py")],
    "export-excel": [sys.executable, os.path.join(REPO_ROOT, "tools", "template_excel_exporter.py")],
    "init-config": [sys.executable, os.path.join(REPO_ROOT, "tools", "init_config.py"), "--force"],
    "dashboard": [sys.executable, os.path.join(REPO_ROOT, "tools", "dashboard_generator.py")],
    "trend": [sys.executable, os.path.join(REPO_ROOT, "tools", "trend_analytics.py")],
    "version": [sys.executable, os.path.join(REPO_ROOT, "tools", "cli.py"), "version"],
}


def get_command_for_target(command_name: str, target_dir: Optional[str] = None) -> list:
    """Resolves command execution arguments scoped to target project or Hub mode."""
    target = os.path.abspath(target_dir) if target_dir else None
    is_target_mode = target is not None and target != REPO_ROOT

    if not is_target_mode:
        return list(COMMAND_MAP[command_name])

    # Target Project Scoped Commands
    if command_name == "verify":
        return [sys.executable, os.path.join(REPO_ROOT, "tools", "verify_all.py"), target, "--mode", "target"]
    elif command_name == "lint":
        return [sys.executable, os.path.join(REPO_ROOT, "tools", "infer_linter.py"), target]
    elif command_name == "mutate":
        return [sys.executable, os.path.join(REPO_ROOT, "tools", "micro_mutator.py"), target, "--min-score", "80"]
    elif command_name == "doctor":
        return [sys.executable, os.path.join(REPO_ROOT, "tools", "check_env.py"), target]
    elif command_name == "analyze":
        return [sys.executable, os.path.join(REPO_ROOT, "tools", "analyze_project.py"), target]
    elif command_name == "dashboard":
        return [sys.executable, os.path.join(REPO_ROOT, "tools", "dashboard_generator.py"), target]
    elif command_name == "init-config":
        return [sys.executable, os.path.join(REPO_ROOT, "tools", "init_config.py"), "--force", target]
    elif command_name in COMMAND_MAP:
        return list(COMMAND_MAP[command_name])
    raise ValueError(f"Unknown or disallowed command: '{command_name}'")


class JobManager:
    """Thread-safe manager for tracking asynchronous background tool execution."""

    def __init__(self, target_dir: Optional[str] = None):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.target_dir = os.path.abspath(target_dir) if target_dir else None

    def start_job(self, command_name: str, cwd: Optional[str] = None) -> str:
        if command_name not in COMMAND_MAP:
            raise ValueError(f"Unknown or disallowed command: '{command_name}'")

        exec_cwd = os.path.abspath(cwd) if cwd else (self.target_dir or REPO_ROOT)
        cmd_list = get_command_for_target(command_name, exec_cwd)
        job_id = f"job_{int(time.time() * 1000)}"

        job = {
            "id": job_id,
            "command": command_name,
            "cmd_list": cmd_list,
            "status": "RUNNING",
            "logs": [],
            "exit_code": None,
            "start_time": time.time(),
            "end_time": None
        }

        with self.lock:
            self.jobs[job_id] = job

        def worker():
            try:
                env = os.environ.copy()
                env["PYTHONUNBUFFERED"] = "1"
                env["PYTHONIOENCODING"] = "utf-8"
                proc = subprocess.Popen(
                    cmd_list,
                    cwd=exec_cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    env=env
                )
                if proc.stdout:
                    for line in iter(proc.stdout.readline, ''):
                        if not line:
                            break
                        with self.lock:
                            job["logs"].append(line)
                    proc.stdout.close()
                proc.wait()
                with self.lock:
                    job["status"] = "PASSED" if proc.returncode == 0 else "FAILED"
                    job["exit_code"] = proc.returncode
                    job["end_time"] = time.time()
            except Exception as e:
                with self.lock:
                    job["logs"].append(f"[ERROR] Process execution failure: {str(e)}\n")
                    job["status"] = "FAILED"
                    job["exit_code"] = -1
                    job["end_time"] = time.time()

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return job_id

    def get_job(self, job_id: str, offset: int = 0) -> Optional[Dict[str, Any]]:
        with self.lock:
            if job_id not in self.jobs:
                return None
            j = self.jobs[job_id]
            logs = j["logs"][offset:]
            return {
                "id": j["id"],
                "command": j["command"],
                "status": j["status"],
                "logs": logs,
                "next_offset": len(j["logs"]),
                "exit_code": j["exit_code"],
                "duration": round((j["end_time"] or time.time()) - j["start_time"], 2)
            }


JOB_MANAGER = JobManager()


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def _is_allowed_origin(origin: str) -> bool:
    """Validates that CORS origin is strictly localhost or 127.0.0.1 to block origin spoofing."""
    if not origin:
        return False
    try:
        parsed = urllib.parse.urlparse(origin)
        return parsed.scheme in ("http", "https") and parsed.hostname in ("localhost", "127.0.0.1")
    except Exception:
        return False


class SynapseUiHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler serving SPA interface and REST APIs."""

    def log_message(self, format, *args):
        # Suppress routine GET log spam to keep console clean
        pass

    def send_json(self, status_code: int, data: Any):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        origin = self.headers.get("Origin", "")
        if _is_allowed_origin(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        origin = self.headers.get("Origin", "")
        if _is_allowed_origin(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            if os.path.exists(TEMPLATE_PATH):
                with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
                    content = f.read().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "UI Template file not found on disk.")
            return

        if path == "/api/status":
            active_target = JOB_MANAGER.target_dir or REPO_ROOT
            self.send_json(200, {
                "version": "4.1.3",
                "status": "ONLINE",
                "os": sys.platform,
                "workspace": active_target,
                "hub_root": REPO_ROOT,
                "target_mode": os.path.abspath(active_target) != REPO_ROOT,
                "author": "Thế Vị (@TeeVee98)",
                "license": "MIT"
            })
            return

        if path == "/api/trends":
            try:
                import trend_analytics
                active_target = JOB_MANAGER.target_dir or REPO_ROOT
                target_ledger = os.path.join(active_target, "reports", "history_ledger.json") if os.path.abspath(active_target) != REPO_ROOT else None
                ledger_arg = target_ledger if (target_ledger and os.path.isfile(target_ledger)) else None
                self.send_json(200, {
                    "svg_trend": trend_analytics.generate_trend_svg(ledger_path=ledger_arg),
                    "svg_duration": trend_analytics.generate_duration_svg(ledger_path=ledger_arg),
                    "ledger": trend_analytics.load_history_ledger(ledger_path=ledger_arg)[-10:]
                })
            except Exception as err:
                self.send_json(500, {"error": str(err)})
            return

        if path.startswith("/api/run/"):
            job_id = path[len("/api/run/"):]
            query = urllib.parse.parse_qs(parsed.query)
            offset = int(query.get("offset", [0])[0])
            job_info = JOB_MANAGER.get_job(job_id, offset)
            if job_info is None:
                self.send_json(404, {"error": "Job not found"})
            else:
                self.send_json(200, job_info)
            return

        # Serve static reports safely with path traversal protection
        unquoted_path = urllib.parse.unquote(path)
        if unquoted_path.startswith("/reports/"):
            rel_file = unquoted_path.lstrip("/")
            safe_target = None

            # 1. Check target project reports directory first if scoped to a Spoke project
            if JOB_MANAGER.target_dir and os.path.abspath(JOB_MANAGER.target_dir) != REPO_ROOT:
                target_reports_dir = os.path.realpath(os.path.join(JOB_MANAGER.target_dir, "reports"))
                candidate = os.path.realpath(os.path.join(JOB_MANAGER.target_dir, rel_file))
                if candidate.startswith(target_reports_dir + os.sep) and os.path.isfile(candidate):
                    safe_target = candidate

            # 2. Fallback to Hub reports directory
            if not safe_target:
                reports_dir = os.path.realpath(os.path.join(REPO_ROOT, "reports"))
                candidate = os.path.realpath(os.path.join(REPO_ROOT, rel_file))
                if candidate.startswith(reports_dir + os.sep) and os.path.isfile(candidate):
                    safe_target = candidate

            if not safe_target:
                self.send_error(404, "Report file not found.")
                return

            with open(safe_target, "rb") as f:
                body = f.read()
            mime = "text/html; charset=utf-8" if safe_target.endswith(".html") else "application/octet-stream"
            if safe_target.endswith(".json"):
                mime = "application/json; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            origin = self.headers.get("Origin", "")
            if _is_allowed_origin(origin):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_error(404, "Endpoint not found.")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/run":
            length = int(self.headers.get("Content-Length", 0))
            body_raw = self.rfile.read(length).decode("utf-8", errors="ignore")
            try:
                payload = json.loads(body_raw) if body_raw else {}
                cmd = payload.get("command", "")
                job_id = JOB_MANAGER.start_job(cmd)
                self.send_json(200, {"job_id": job_id, "command": cmd, "status": "STARTED"})
            except ValueError as err:
                self.send_json(400, {"error": str(err)})
            except Exception as err:
                self.send_json(500, {"error": f"Internal execution error: {err}"})
            return

        self.send_error(404, "Endpoint not found.")


def find_free_port(start_port: int = 8080, max_attempts: int = 20) -> int:
    """Finds an available local TCP port."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port


def run_server(host: str = "127.0.0.1", port: int = 8080, open_browser: bool = True, target_dir: Optional[str] = None):
    """Starts the Synapse Hub Mission Control HTTP server."""
    if target_dir:
        JOB_MANAGER.target_dir = os.path.abspath(target_dir)
    elif os.path.abspath(os.getcwd()) != REPO_ROOT:
        JOB_MANAGER.target_dir = os.path.abspath(os.getcwd())
    else:
        JOB_MANAGER.target_dir = REPO_ROOT

    actual_port = find_free_port(port)
    server_address = (host, actual_port)
    httpd = ThreadingHTTPServer(server_address, SynapseUiHandler)

    url = f"http://{host}:{actual_port}"
    print("\n" + "=" * 70)
    print("  ⚡ SYNAPSE HUB — INTERACTIVE QA MISSION CONTROL")
    print("=" * 70)
    print(f"  Server URL   : {url}")
    print(f"  Workspace    : {JOB_MANAGER.target_dir}")
    print(f"  Hub Root     : {REPO_ROOT}")
    print(f"  Scope Mode   : {'TARGET PROJECT' if JOB_MANAGER.target_dir != REPO_ROOT else 'HUB'}")
    print("  Created by   : Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>")
    print("  License      : MIT")
    print("=" * 70)
    print("  [INFO] Press Ctrl+C in terminal to stop server.\n")

    if open_browser:
        def opener():
            time.sleep(0.5)
            webbrowser.open(url)
        threading.Thread(target=opener, daemon=True).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Stopping Synapse Hub Mission Control server...")
    finally:
        httpd.server_close()
        print("[INFO] Server stopped gracefully.")


def main():
    parser = argparse.ArgumentParser(description="Launch Synapse Hub Interactive QA Mission Control Web UI")
    parser.add_argument("target", nargs="?", default=None, help="Target project directory (defaults to CWD or Hub root)")
    parser.add_argument("--target", dest="target_opt", default=None, help="Target project directory")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", "-p", type=int, default=8080, help="Initial port to bind (default: 8080)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser on startup")
    args = parser.parse_args()

    target_path = args.target_opt or args.target
    run_server(host=args.host, port=args.port, open_browser=not args.no_browser, target_dir=target_path)


if __name__ == "__main__":
    main()
