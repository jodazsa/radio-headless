#!/usr/bin/env python3
"""Local backend for controlling radio-headless on the Pi itself.

Run this on the Raspberry Pi. It executes a small whitelist of local commands
(no SSH hop) and exposes a JSON API for a browser UI.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
import shlex
import subprocess
from typing import Any

BIND_HOST = os.getenv("BIND_HOST", "0.0.0.0")
BIND_PORT = int(os.getenv("BIND_PORT", "8080"))
RADIO_PLAY_CMD = os.getenv("RADIO_PLAY_CMD", "radio-play")
STATE_FILE = os.getenv("RADIO_STATE_FILE", "/home/radio/.radio-state")
WEB_ROOT = Path(os.getenv("WEB_ROOT", Path(__file__).resolve().parent))
DEFAULT_PAGE = os.getenv("WEB_DEFAULT_PAGE", "radio.html")
SETUP_PAGE = os.getenv("WEB_SETUP_PAGE", "setup.html")
SETUP_MARKER_FILE = Path(os.getenv("RADIO_SETUP_MARKER_FILE", "/var/lib/radio/setup-mode"))
SETUP_APPLY_CMD = os.getenv("RADIO_SETUP_APPLY_CMD", "/usr/bin/sudo /usr/local/lib/radio/apply-network-config")

ALLOWED_COMMANDS = [
    r"^mpc\s+(play|pause|stop|next|prev|volume\s+\d{1,3})$",
    r"^radio-play\s+\d+\s+\d+$",
]

HOSTNAME_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def is_command_allowed(command: str) -> bool:
    cmd = command.strip()
    return any(re.match(pattern, cmd) for pattern in ALLOWED_COMMANDS)


def command_to_argv(command: str) -> list[str]:
    argv = shlex.split(command)
    if argv and argv[0] == "radio-play":
        argv[0] = RADIO_PLAY_CMD
    return argv


def is_setup_mode() -> bool:
    return SETUP_MARKER_FILE.exists()


def normalize_hostname(hostname: str) -> str:
    return hostname.strip().lower()


def validate_setup_payload(data: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    errors: dict[str, str] = {}

    ssid = str(data.get("ssid", "")).strip()
    password = str(data.get("password", ""))
    hostname = normalize_hostname(str(data.get("hostname", "")))

    if not ssid:
        errors["ssid"] = "SSID is required"
    elif len(ssid) > 32:
        errors["ssid"] = "SSID must be 32 characters or less"

    if len(password) < 8:
        errors["password"] = "Password must be at least 8 characters"
    elif len(password) > 63:
        errors["password"] = "Password must be 63 characters or less"

    if not hostname:
        errors["hostname"] = "Hostname is required"
    elif len(hostname) > 63 or HOSTNAME_PATTERN.match(hostname) is None:
        errors["hostname"] = "Hostname must be lowercase letters, numbers, hyphens, and 63 chars max"

    return {"ssid": ssid, "password": password, "hostname": hostname}, errors


class CommandHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path in {"/", ""}:
            self._send_static_file(DEFAULT_PAGE)
            return

        if self.path == f"/{DEFAULT_PAGE}":
            self._send_static_file(DEFAULT_PAGE)
            return

        if self.path in {"/setup", "/setup.html", f"/{SETUP_PAGE}"}:
            self._send_static_file(SETUP_PAGE)
            return

        if self.path == "/config":
            self.send_json_response(
                200,
                {
                    "mode": "local",
                    "bind_host": BIND_HOST,
                    "bind_port": BIND_PORT,
                    "radio_play_cmd": RADIO_PLAY_CMD,
                },
            )
            return

        if self.path == "/setup/config":
            self.send_json_response(
                200,
                {
                    "success": True,
                    "setup_mode": is_setup_mode(),
                    "setup_page": SETUP_PAGE,
                },
            )
            return

        if self.path.startswith("/") and self.path.count("/") == 1 and not self.path.endswith("/"):
            self._send_static_file(self.path[1:])
            return

        self.send_error(404)

    def _send_static_file(self, relative_path: str):
        try:
            requested = (WEB_ROOT / relative_path).resolve()
            if WEB_ROOT not in requested.parents and requested != WEB_ROOT:
                self.send_error(403)
                return
            if not requested.is_file():
                self.send_error(404)
                return

            content_type = mimetypes.guess_type(requested.name)[0] or "application/octet-stream"
            content = requested.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except OSError as exc:
            self.send_json_response(500, {"success": False, "error": str(exc), "error_type": "io_error"})

    def do_POST(self):
        if self.path == "/command":
            data = self._read_json_body(optional=True)
            if data is None:
                return

            command = data.get("command", "")
            if not is_command_allowed(command):
                self.send_json_response(
                    403,
                    {
                        "success": False,
                        "error": f"Command not allowed: {command}",
                        "error_type": "forbidden_command",
                    },
                )
                return

            self._send_local_command(command)
            return

        if self.path == "/status":
            data = self._read_json_body(optional=True)
            if data is None:
                return
            self._send_status()
            return

        if self.path == "/state":
            data = self._read_json_body(optional=True)
            if data is None:
                return
            self._send_state()
            return

        if self.path == "/setup/apply":
            data = self._read_json_body(optional=False)
            if data is None:
                return
            self._apply_setup(data)
            return

        self.send_error(404)

    def _read_json_body(self, optional: bool = False) -> dict[str, Any] | None:
        content_length = self.headers.get("Content-Length")
        if optional and (content_length is None or content_length == "0"):
            return {}

        try:
            body = self.rfile.read(int(content_length or "0"))
            if not body and optional:
                return {}
            return json.loads(body.decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            self.send_json_response(
                400,
                {
                    "success": False,
                    "error": "Invalid request format",
                    "error_type": "invalid_request",
                },
            )
            return None

    def _run_local(
        self,
        argv: list[str],
        *,
        timeout: int = 10,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, input=input_text)

    def _apply_setup(self, data: dict[str, Any]):
        if not is_setup_mode():
            self.send_json_response(
                403,
                {"success": False, "error": "Setup mode is not enabled", "error_type": "setup_mode_disabled"},
            )
            return

        payload, errors = validate_setup_payload(data)
        if errors:
            self.send_json_response(
                400,
                {
                    "success": False,
                    "error": "Invalid setup payload",
                    "error_type": "invalid_setup_payload",
                    "fields": errors,
                },
            )
            return

        try:
            result = self._run_local(
                shlex.split(SETUP_APPLY_CMD),
                timeout=60,
                input_text=json.dumps(payload),
            )
            if result.returncode != 0:
                self.send_json_response(
                    500,
                    {
                        "success": False,
                        "error": result.stderr.strip() or "Failed to apply settings",
                        "error_type": "apply_failed",
                        "exit_code": result.returncode,
                    },
                )
                return

            output = result.stdout.strip()
            if output:
                try:
                    data = json.loads(output)
                    if isinstance(data, dict):
                        self.send_json_response(200, data)
                        return
                except json.JSONDecodeError:
                    pass

            self.send_json_response(200, {"success": True, "message": "Settings applied"})
        except subprocess.TimeoutExpired:
            self.send_json_response(504, {"success": False, "error": "Apply command timed out", "error_type": "timeout"})
        except FileNotFoundError as exc:
            self.send_json_response(
                500,
                {"success": False, "error": f"Apply command missing: {exc}", "error_type": "command_not_found"},
            )

    def _send_local_command(self, command: str):
        try:
            result = self._run_local(command_to_argv(command))
            if result.returncode == 0:
                self.send_json_response(
                    200,
                    {"success": True, "output": result.stdout.strip(), "command": command},
                )
            else:
                self.send_json_response(
                    200,
                    {
                        "success": False,
                        "error": result.stderr.strip() or "Command failed",
                        "error_type": "command_failed",
                        "exit_code": result.returncode,
                    },
                )
        except subprocess.TimeoutExpired:
            self.send_json_response(504, {"success": False, "error": "Command timed out", "error_type": "timeout"})
        except FileNotFoundError as exc:
            self.send_json_response(
                500,
                {"success": False, "error": f"Command not found: {exc}", "error_type": "command_not_found"},
            )

    def _send_status(self):
        try:
            current_result = self._run_local(["mpc", "current"])
            status_result = self._run_local(["mpc", "status"])

            current_track = current_result.stdout.strip() if current_result.returncode == 0 else ""
            status_text = status_result.stdout
            volume = 50
            volume_match = re.search(r"volume:\s*(\d+)%", status_text)
            if volume_match:
                volume = int(volume_match.group(1))

            self.send_json_response(
                200,
                {
                    "success": True,
                    "current_track": current_track,
                    "is_playing": "[playing]" in status_text,
                    "is_paused": "[paused]" in status_text,
                    "volume": volume,
                },
            )
        except subprocess.TimeoutExpired:
            self.send_json_response(504, {"success": False, "error": "Timeout getting status", "error_type": "timeout"})
        except FileNotFoundError as exc:
            self.send_json_response(500, {"success": False, "error": f"Command not found: {exc}", "error_type": "command_not_found"})

    def _send_state(self):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                lines = f.read().strip().splitlines()
        except FileNotFoundError:
            self.send_json_response(200, {"success": False, "error": f"State file not found: {STATE_FILE}"})
            return
        except OSError as exc:
            self.send_json_response(500, {"success": False, "error": str(exc), "error_type": "io_error"})
            return

        parsed: dict[str, str] = {}
        for line in lines:
            if "=" in line:
                key, value = line.split("=", 1)
                parsed[key] = value

        self.send_json_response(
            200,
            {
                "success": True,
                "bank": int(parsed.get("current_bank", 0)),
                "station": int(parsed.get("current_station", 0)),
                "bank_name": parsed.get("bank_name", ""),
                "station_name": parsed.get("station_name", ""),
                "playback_state": parsed.get("playback_state", "stopped"),
            },
        )

    def send_json_response(self, status_code: int, data: dict[str, Any]):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def log_message(self, fmt: str, *args: object):
        print(f"[{self.log_date_time_string()}] {fmt % args}")


def main():
    print("=" * 60)
    print("Pi Music Controller Backend Server (LOCAL MODE)")
    print("=" * 60)
    print(f"Listening on: http://{BIND_HOST}:{BIND_PORT}")
    print(f"radio-play command: {RADIO_PLAY_CMD}")
    print(f"state file: {STATE_FILE}")
    print(f"web root: {WEB_ROOT}")
    print(f"default page: {DEFAULT_PAGE}")
    print(f"setup page: {SETUP_PAGE}")
    print(f"setup marker: {SETUP_MARKER_FILE}")
    print(f"setup apply command: {SETUP_APPLY_CMD}")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    server = HTTPServer((BIND_HOST, BIND_PORT), CommandHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
