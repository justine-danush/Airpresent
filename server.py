"""AirPresent desktop receiver (Windows).

Run this on the presentation PC, then open the printed address on the phone.
Both devices must be on the same Wi-Fi network.
"""
from __future__ import annotations

import json
import os
import secrets
import socket
import sys
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
SESSION_TOKEN = secrets.token_urlsafe(24)
# The initial prototype is intended for a trusted private Wi-Fi network.  A later
# release will replace this with a QR-based pairing flow.
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
    # mouse_event flag constants: left down/up, right down/up
    flags = {"left": (0x0002, 0x0004), "right": (0x0008, 0x0010)}
    down, up = flags[button]
    USER32.mouse_event(down, 0, 0, 0, 0)
    USER32.mouse_event(up, 0, 0, 0, 0)


def key_press(key: str) -> None:
    # Virtual-key codes understood by PowerPoint, Google Slides, and Keynote Remote pages.
    code = {"next": 0x27, "previous": 0x25, "escape": 0x1B}[key]
    USER32.keybd_event(code, 0, 0, 0)
    USER32.keybd_event(code, 0, 0x0002, 0)


class AirPresentHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        # The phone interface changes frequently during MVP development.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def translate_path(self, path: str) -> str:
        path = urlparse(path).path
        if path == "/":
            path = "/index.html"
        return str(ROOT / path.lstrip("/"))

    def do_GET(self) -> None:
        super().do_GET()

    def do_POST(self) -> None:
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
            allowed = len(str(event.get("code", "")).strip()) == 6
            print("Phone paired." if allowed else "Pairing refused: enter any six characters.")
            self.send_json({"ok": allowed, "token": SESSION_TOKEN if allowed else None})
        elif self.path == "/control" and secrets.compare_digest(str(event.pop("token", "")), SESSION_TOKEN):
            self.apply_event(event)
            self.send_json({"ok": True})
        else:
            self.send_error(403, "Not authorized")

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
            # Safety cap prevents a malformed message from throwing the cursor across screens.
            dx = max(-120, min(120, float(event.get("dx", 0))))
            dy = max(-120, min(120, float(event.get("dy", 0))))
            move_cursor(dx, dy)
        elif event_type == "click" and event.get("button") in ("left", "right"):
            mouse_click(event["button"])
        elif event_type == "key" and event.get("key") in ("next", "previous", "escape"):
            key_press(event["key"])

    def log_message(self, format: str, *args: Any) -> None:
        # Keep the console usable during a presentation.
        if "POST" in format:
            super().log_message(format, *args)


if __name__ == "__main__":
    os.chdir(ROOT)
    host = local_ip()
    try:
        server = ThreadingHTTPServer(("0.0.0.0", PORT), AirPresentHandler)
    except OSError as error:
        print(f"\nAirPresent could not start: {error}")
        print("Close every other AirPresent window, then run this file again.")
        raise SystemExit(1)
    print("\nAirPresent receiver is running.")
    print(f"Open: http://{host}:{PORT}")
    print("Open this address from a phone on the same private Wi-Fi network.")
    print("Enter any six-character code, then press Connect.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
