"""AirPresent desktop receiver v2.1 (Windows GUI & CLI).

Run this on the presentation PC, then scan the QR code or enter the dynamic 6-digit PIN on your phone.
Both devices must be on the same Wi-Fi network.
"""
from __future__ import annotations

import io
import json
import os
import secrets
import socket
import sys
import time
import threading
import queue
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import ctypes
from ctypes import wintypes

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

if getattr(sys, "frozen", False):
    # Running inside PyInstaller bundle or frozen executable
    bundle_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    ROOT = bundle_dir / "phone_app"
    if not ROOT.exists():
        ROOT = Path(sys.executable).parent / "phone_app"
else:
    ROOT = Path(__file__).parent / "phone_app"

PORT = 8765
PAIRING_CODE = f"{secrets.randbelow(1000000):06d}"
SESSION_TOKEN = secrets.token_urlsafe(32)

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

# Queue for thread-safe GUI log messages
LOG_QUEUE = queue.Queue()
GUI_INSTANCE = None


def local_ip() -> str:
    """Find the LAN address without sending any traffic."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("192.0.2.1", 80))
            return sock.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def move_cursor(dx: float, dy: float) -> None:
    """Applies a 1€ Low-Pass Tremor Filter & sub-pixel accumulator before moving mouse."""
    global cursor_acc_x, cursor_acc_y, smooth_dx, smooth_dy

    speed = math.hypot(dx, dy)

    # 1. Micro-Tremor Suppression (filters out hand twitches)
    if speed < TREMOR_DEADZONE:
        smooth_dx *= 0.4
        smooth_dy *= 0.4
        return

    # 2. Dynamic Adaptive Smoothing Alpha
    # Slow movement (aiming): alpha ~ 0.25 (High smoothing, rock-solid cursor)
    # Fast movement (swiping): alpha ~ 0.85 (Zero lag)
    speed_factor = min(1.0, max(0.0, (speed - 0.5) / 4.5))
    alpha = 0.25 + 0.60 * speed_factor

    # Exponential Moving Average (EMA) low-pass filter
    smooth_dx = alpha * dx + (1.0 - alpha) * smooth_dx
    smooth_dy = alpha * dy + (1.0 - alpha) * smooth_dy

    cursor_acc_x += smooth_dx
    cursor_acc_y += smooth_dy
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


def gui_log(message: str) -> None:
    LOG_QUEUE.put(message)
    print(message)


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
            # Auto-reset failed counter if 15s passed since last failure
            if (now - LAST_FAILED_TIME) > 15:
                FAILED_PAIR_ATTEMPTS = 0

            if FAILED_PAIR_ATTEMPTS >= 8 and (now - LAST_FAILED_TIME) < 10:
                gui_log("⚠️ Rate Limit: Too many failed pairing attempts (10s cooldown).")
                self.send_json({"ok": False, "error": "Rate limited: Wait 10s or click New PIN on PC."})
                return

            submitted_code = str(event.get("code", "")).strip()
            allowed = secrets.compare_digest(submitted_code, PAIRING_CODE)

            if allowed:
                FAILED_PAIR_ATTEMPTS = 0
                gui_log(f"✅ Phone paired successfully using PIN [{PAIRING_CODE}].")
                self.send_json({"ok": True, "token": SESSION_TOKEN})
            else:
                FAILED_PAIR_ATTEMPTS += 1
                LAST_FAILED_TIME = now
                gui_log(f"❌ Pairing refused: invalid PIN [{submitted_code}].")
                self.send_json({"ok": False, "error": "Invalid PIN code. Check your PC screen."})

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
            gui_log(f"🖱️ Mouse click: {event['button'].capitalize()}")
            mouse_click(event["button"])
        elif event_type == "key" and event.get("key") in ("next", "previous", "escape"):
            gui_log(f"⚡ Key action: {event['key'].capitalize()}")
            key_press(event["key"])

    def log_message(self, format: str, *args: Any) -> None:
        pass  # Suppress default HTTP request logs in console


class ServerThread(threading.Thread):
    def __init__(self, host: str, port: int):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.server: ThreadingHTTPServer | None = None
        self.running = False

    def run(self):
        try:
            self.server = ThreadingHTTPServer((self.host, self.port), AirPresentHandler)
            self.running = True
            gui_log(f"🚀 AirPresent Server started on http://{local_ip()}:{self.port}")
            self.server.serve_forever()
        except Exception as e:
            gui_log(f"❌ Server error: {e}")
            self.running = False

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.running = False
            gui_log("⏹️ AirPresent Server stopped.")


class AirPresentApp(tk.Tk):
    def __init__(self, host_ip: str, port: int):
        super().__init__()
        self.host_ip = host_ip
        self.port = port
        self.server_thread: ServerThread | None = None

        self.title("AirPresent Server v2.1")
        self.geometry("480x680")
        self.resizable(False, False)
        self.configure(bg="#0b0f19")

        # Apply Windows Dark Titlebar
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)
        except Exception:
            pass

        self.setup_ui()

        # Start Server automatically
        self.start_server()

        # Schedule queue polling for logs
        self.after(100, self.poll_log_queue)

    def setup_ui(self):
        # Header Container
        header_frame = tk.Frame(self, bg="#111827", pady=15, padx=20)
        header_frame.pack(fill="x")

        title_lbl = tk.Label(header_frame, text="🎯 AirPresent", font=("Segoe UI", 20, "bold"), fg="#ffffff", bg="#111827")
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(header_frame, text="Wireless PC Presentation Controller & Air Mouse", font=("Segoe UI", 10), fg="#9ca3af", bg="#111827")
        sub_lbl.pack(anchor="w")

        # Status Bar Card
        self.status_card = tk.Frame(self, bg="#1e293b", padx=15, pady=10)
        self.status_card.pack(fill="x", padx=20, pady=(15, 10))

        self.status_lbl = tk.Label(self.status_card, text="🟢 ONLINE  |  http://" + self.host_ip + ":" + str(self.port), font=("Consolas", 11, "bold"), fg="#34d399", bg="#1e293b")
        self.status_lbl.pack(side="left")

        copy_btn = tk.Button(self.status_card, text="📋 Copy", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#374151", activebackground="#4b5563", activeforeground="#ffffff", bd=0, padx=10, pady=3, command=self.copy_pair_url)
        copy_btn.pack(side="right")

        # QR Code Card
        qr_card = tk.Frame(self, bg="#111827", padx=15, pady=15, highlightbackground="#1f2937", highlightthickness=1)
        qr_card.pack(fill="x", padx=20, pady=5)

        self.qr_lbl = tk.Label(qr_card, bg="#111827")
        self.qr_lbl.pack(pady=(0, 8))

        qr_hint = tk.Label(qr_card, text="Scan with Phone Camera or AirPresent Android App", font=("Segoe UI", 9), fg="#9ca3af", bg="#111827")
        qr_hint.pack()

        # Passcode Display Card
        pin_card = tk.Frame(self, bg="#111827", padx=15, pady=12, highlightbackground="#1f2937", highlightthickness=1)
        pin_card.pack(fill="x", padx=20, pady=5)

        pin_title = tk.Label(pin_card, text="DYNAMIC SECURITY PIN", font=("Segoe UI", 9, "bold"), fg="#60a5fa", bg="#111827")
        pin_title.pack(anchor="w")

        pin_subframe = tk.Frame(pin_card, bg="#111827")
        pin_subframe.pack(fill="x", pady=(5, 0))

        self.pin_lbl = tk.Label(pin_subframe, text=PAIRING_CODE, font=("Consolas", 22, "bold"), fg="#38bdf8", bg="#111827")
        self.pin_lbl.pack(side="left")

        regen_btn = tk.Button(pin_subframe, text="🔄 New PIN", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#374151", activebackground="#4b5563", activeforeground="#ffffff", bd=0, padx=10, pady=4, command=self.regenerate_pin)
        regen_btn.pack(side="right")

        # Live Console Activity Logs
        log_frame = tk.Frame(self, bg="#0b0f19")
        log_frame.pack(fill="both", expand=True, padx=20, pady=10)

        log_title = tk.Label(log_frame, text="LIVE EVENT CONSOLE", font=("Segoe UI", 9, "bold"), fg="#9ca3af", bg="#0b0f19")
        log_title.pack(anchor="w", pady=(0, 4))

        self.log_widget = scrolledtext.ScrolledText(log_frame, font=("Consolas", 9), bg="#111827", fg="#34d399", bd=0, highlightbackground="#1f2937", highlightthickness=1, height=8)
        self.log_widget.pack(fill="both", expand=True)

        # Bottom Button Bar
        btn_bar = tk.Frame(self, bg="#0b0f19", pady=10)
        btn_bar.pack(fill="x", padx=20)

        self.toggle_btn = tk.Button(btn_bar, text="⏸ Stop Server", font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#ef4444", activebackground="#dc2626", activeforeground="#ffffff", bd=0, pady=6, command=self.toggle_server)
        self.toggle_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        copy_link_btn = tk.Button(btn_bar, text="📋 Copy Auto-Pair Link", font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#2563eb", activebackground="#1d4ed8", activeforeground="#ffffff", bd=0, pady=6, command=self.copy_pair_url)
        copy_link_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))

        # Render QR Code image
        self.update_qr_image()

    def get_pair_url(self) -> str:
        return f"http://{self.host_ip}:{self.port}#code={PAIRING_CODE}"

    def update_qr_image(self):
        if QR_AVAILABLE:
            url = self.get_pair_url()
            qr = qrcode.QRCode(box_size=4, border=1)
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            self.qr_photo = tk.PhotoImage(data=buf.getvalue())
            self.qr_lbl.configure(image=self.qr_photo)

    def regenerate_pin(self):
        global PAIRING_CODE, SESSION_TOKEN, FAILED_PAIR_ATTEMPTS
        PAIRING_CODE = f"{secrets.randbelow(1000000):06d}"
        SESSION_TOKEN = secrets.token_urlsafe(32)
        FAILED_PAIR_ATTEMPTS = 0
        self.pin_lbl.configure(text=PAIRING_CODE)
        self.update_qr_image()
        gui_log(f"🔑 Security PIN regenerated: [{PAIRING_CODE}] (Rate limit reset)")

    def copy_pair_url(self):
        url = self.get_pair_url()
        try:
            self.clipboard_clear()
            self.clipboard_append(url)
            self.update()
        except Exception:
            pass
        gui_log("📋 Auto-Pair URL copied to clipboard!")

    def start_server(self):
        if not self.server_thread or not self.server_thread.running:
            self.server_thread = ServerThread(self.host_ip, self.port)
            self.server_thread.start()
            self.status_lbl.configure(text="🟢 ONLINE  |  http://" + self.host_ip + ":" + str(self.port), fg="#34d399")
            self.toggle_btn.configure(text="⏸ Stop Server", bg="#ef4444", activebackground="#dc2626")

    def stop_server(self):
        if self.server_thread and self.server_thread.running:
            self.server_thread.stop()
            self.status_lbl.configure(text="🔴 STOPPED  |  Server Offline", fg="#f87171")
            self.toggle_btn.configure(text="▶ Start Server", bg="#10b981", activebackground="#059669")

    def toggle_server(self):
        if self.server_thread and self.server_thread.running:
            self.stop_server()
        else:
            self.start_server()

    def poll_log_queue(self):
        while not LOG_QUEUE.empty():
            msg = LOG_QUEUE.get_nowait()
            timestamp = time.strftime("%H:%M:%S")
            self.log_widget.insert(tk.END, f"[{timestamp}] {msg}\n")
            self.log_widget.see(tk.END)
        self.after(100, self.poll_log_queue)

    def destroy(self):
        self.stop_server()
        super().destroy()


def run_cli_server():
    os.chdir(ROOT)
    host = local_ip()
    pair_url = f"http://{host}:{PORT}#code={PAIRING_CODE}"

    try:
        server = ThreadingHTTPServer(("0.0.0.0", PORT), AirPresentHandler)
    except OSError as error:
        print(f"\nAirPresent could not start: {error}")
        raise SystemExit(1)

    print("\n" + "=" * 60)
    print("  🎯 AirPresent Receiver v2.1 — CLI Mode")
    print("=" * 60)
    print(f"  📍 Web Address  : http://{host}:{PORT}")
    print(f"  🔑 Dynamic PIN  : [ {PAIRING_CODE} ]")
    print(f"  ⚡ Auto-Pair URL: {pair_url}")
    print("=" * 60)

    if QR_AVAILABLE:
        try:
            print("\n  📱 Scan QR Code with Phone Camera to Connect Instantly:\n")
            qr = qrcode.QRCode(border=1)
            qr.add_data(pair_url)
            qr.make(fit=True)
            qr.print_ascii(invert=True)
        except Exception:
            print(f"\n  (Scan URL: {pair_url})")

    print("\n  Receiver active. Waiting for secure connection...\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAirPresent Receiver stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    os.chdir(ROOT)
    use_cli = "--cli" in sys.argv or not GUI_AVAILABLE

    if use_cli:
        run_cli_server()
    else:
        host = local_ip()
        app = AirPresentApp(host, PORT)
        app.mainloop()
