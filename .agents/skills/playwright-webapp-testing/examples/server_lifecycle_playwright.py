"""Example: managed server lifecycle + minimal Playwright automation.

Hub baseline: headless chromium, 1920x1080 viewport, networkidle wait,
unconditional teardown. The automation script contains only Playwright
logic; the lifecycle wrapper owns spawn/ready/teardown.
"""
import socket
import subprocess
import time
from contextlib import contextmanager

from playwright.sync_api import sync_playwright

APP_DIR = "apps/web"          # relative to the target project root
START_CMD = ["npm", "run", "dev"]  # argv list: never spawn with shell=True
PORT = 5173
READY_TIMEOUT_S = 30


def _port_ready(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex(("127.0.0.1", port)) == 0


@contextmanager
def managed_server(start_cmd: list, port: int):
    """Spawn the app server, poll readiness, guarantee teardown."""
    proc = subprocess.Popen(start_cmd, shell=False, cwd=APP_DIR)
    try:
        deadline = time.monotonic() + READY_TIMEOUT_S
        while not _port_ready(port):
            if time.monotonic() > deadline:
                raise RuntimeError(f"server not ready on port {port} within {READY_TIMEOUT_S}s")
            time.sleep(0.5)  # poll interval, not a synchronization sleep
        yield
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def run_automation() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # always headless
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        try:
            page.goto("http://localhost:5173")
            page.wait_for_load_state("networkidle")  # CRITICAL before inspection
            # Reconnaissance-then-action: verify selectors via the live DOM
            # contract from playwright-live-interaction before acting on them.
            page.get_by_role("button", name="Create invoice").click()
            page.get_by_role("dialog").wait_for(state="visible")
            assert "Invoice" in page.get_by_role("heading").inner_text()
        finally:
            browser.close()  # unconditional teardown


if __name__ == "__main__":
    with managed_server(START_CMD, PORT):
        run_automation()
