"""AirPresent desktop receiver v2.0 (Windows).

Run this on the presentation PC, then scan the QR code or enter the dynamic 6-digit PIN on your phone.
Both devices must be on the same Wi-Fi network.
"""
from __future__ import annotations

import json
import os
import secrets
import socket
import sys
import time
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import ctypes
from ctypes import wintypes

if getattr(sys, "frozen", False):
    # Running inside PyInstaller bundle or frozen executable
    bundle_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    ROOT = bundle_dir / "phone_app"
    if not ROOT.exists():
        ROOT = Path(sys.executable).parent / "phone_app"
else:
    ROOT = Path(__file__).parent / "phone_app"

PORT = 8765
# Generate cryptographically secure dynamic 6-digit PIN and 256-bit session token
PAIRING_CODE = f"{secrets.randbelow(1000000):06d}"
SESSION_TOKEN = secrets.token_urlsafe(32)

# Rate limiting data for brute-force protection
FAILED_PAIR_ATTEMPTS = 0
LAST_FAILED_TIME = 0.0

USER32 = ctypes.windll.user32
USER32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
USER32.GetCursorPos.restype = wintypes.BOOL
USER32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
USER32.SetCursorPos.restype = wintypes.BOOL
USER32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_ulong]
USER32.mouse_event.restype = None

cursor_acc_x: float = 0.0
cursor_acc_y: float = 0.0


def local_ip() -> str:
    """Find the LAN address without sending any traffic."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("192.0.2.1", 80))
            return sock.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def move_cursor(dx: float, dy: float) -> None:
    global cursor_acc_x, cursor_acc_y
    cursor_acc_x += dx
    cursor_acc_y += dy
    move_x = int(cursor_acc_x)
    move_y = int(cursor_acc_y)
    if move_x != 0 or move_y != 0:
        cursor_acc_x -= move_x
        cursor_acc_y -= move_y
        USER32.mouse_event(0x0001, ctypes.c_ulong(move_x & 0xFFFFFFFF), ctypes.c_ulong(move_y & 0xFFFFFFFF), 0, 0)


def mouse_click(button: str) -> None:
    flags = {"left": (0x0002, 0x0004), "right": (0x0008, 0x0010)}
    down, up = flags[button]
    USER32.mouse_event(down, 0, 0, 0, 0)
    USER32.mouse_event(up, 0, 0, 0, 0)


def key_press(key: str) -> None:
    code = {"next": 0x27, "previous": 0x25, "escape": 0x1B}[key]
    USER32.keybd_event(code, 0, 0, 0)
    USER32.keybd_event(code, 0, 0x0002, 0)


class AirPresentHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def translate_path(self, path: str) -> str:
        path = urlparse(path).path
        if path == "/":
            path = "/index.html"
        return str(ROOT / path.lstrip("/"))

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.end_headers()

    def do_GET(self) -> None:
        super().do_GET()

    def do_POST(self) -> None:
        global FAILED_PAIR_ATTEMPTS, LAST_FAILED_TIME

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if not 0 < content_length <= 2048:
                self.send_error(400, "Invalid request length")
                return
            event: dict[str, Any] = json.loads(self.rfile.read(content_length))
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            self.send_error(400, "Invalid control request")
            return

        if self.path == "/pair":
            now = time.time()
            if FAILED_PAIR_ATTEMPTS >= 5 and (now - LAST_FAILED_TIME) < 60:
                print("⚠️ Security Rate Limit: Too many failed pairing attempts. Please wait 60s.")
                self.send_error(429, "Too Many Requests: Rate limited")
                return

            submitted_code = str(event.get("code", "")).strip()
            allowed = secrets.compare_digest(submitted_code, PAIRING_CODE)

            if allowed:
                FAILED_PAIR_ATTEMPTS = 0
                print(f"✅ Phone paired successfully using PIN [{PAIRING_CODE}].")
                self.send_json({"ok": True, "token": SESSION_TOKEN})
            else:
                FAILED_PAIR_ATTEMPTS += 1
                LAST_FAILED_TIME = now
                print(f"❌ Pairing refused: invalid PIN [{submitted_code}]. Correct PIN is [{PAIRING_CODE}].")
                self.send_json({"ok": False, "error": "Invalid PIN code"})

        elif self.path == "/control":
            req_token = str(event.pop("token", ""))
            if secrets.compare_digest(req_token, SESSION_TOKEN):
                self.apply_event(event)
                self.send_json({"ok": True})
            else:
                self.send_error(403, "Forbidden: Invalid session token")
        else:
            self.send_error(404, "Not found")

    def send_json(self, value: dict[str, Any]) -> None:
        payload = json.dumps(value).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    @staticmethod
    def apply_event(event: dict[str, Any]) -> None:
        event_type = event.get("type")
        if event_type == "move":
            dx = max(-120, min(120, float(event.get("dx", 0))))
            dy = max(-120, min(120, float(event.get("dy", 0))))
            move_cursor(dx, dy)
        elif event_type == "click" and event.get("button") in ("left", "right"):
            mouse_click(event["button"])
        elif event_type == "key" and event.get("key") in ("next", "previous", "escape"):
            key_press(event["key"])

    def log_message(self, format: str, *args: Any) -> None:
        if "POST" in format:
            super().log_message(format, *args)


if __name__ == "__main__":
    os.chdir(ROOT)
    host = local_ip()
    pair_url = f"http://{host}:{PORT}#code={PAIRING_CODE}"

    try:
        server = ThreadingHTTPServer(("0.0.0.0", PORT), AirPresentHandler)
    except OSError as error:
        print(f"\nAirPresent could not start: {error}")
        print("Close every other AirPresent window, then run this file again.")
        raise SystemExit(1)

    print("\n" + "=" * 60)
    print("  🎯 AirPresent Receiver v2.0 — Secure Release")
    print("=" * 60)
    print(f"  📍 Web Address  : http://{host}:{PORT}")
    print(f"  🔑 Dynamic PIN  : [ {PAIRING_CODE} ]")
    print(f"  ⚡ Auto-Pair URL: {pair_url}")
    print("=" * 60)

    try:
        import qrcode

        print("\n  📱 Scan QR Code with Phone Camera to Connect Instantly:\n")
        qr = qrcode.QRCode(border=1)
        qr.add_data(pair_url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except Exception as e:
        print(f"\n  (Scan URL: {pair_url})")

    print("\n  Receiver active. Waiting for secure connection...\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAirPresent Receiver stopped.")
    finally:
        server.server_close()
