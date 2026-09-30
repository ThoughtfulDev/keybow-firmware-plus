"""Local-only HTTP bridge for the Keybow visual editor."""

import json
import os
import sys
from pathlib import Path
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
import webbrowser

from .layouts import LAYOUTS, characters, host_layout, translate
from .profile import MEDIA, PRESETS, default_profile, generate_lua, key_options, parse_lua, upgrade, validate
from .protocol import Device, DeviceError

STATIC = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "static"
DEVICE = Device()
ID_PATH = re.compile(r"/api/profiles/([a-z0-9-]{1,32})\Z")
MARKER_ID = "layer-loader"
marker_profile = default_profile()
marker_profile.update(id=MARKER_ID, name="Layer loader support")
MARKER_SOURCE = generate_lua(marker_profile).encode("utf-8")


def layers_ready():
    try:
        return DEVICE.request("read", MARKER_ID.encode("ascii")) == MARKER_SOURCE
    except DeviceError:
        return False


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def log_message(self, format, *args):
        pass

    def json_response(self, value, status=200):
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def body_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= 65536:
            raise ValueError("Request body is too large or empty")
        return json.loads(self.rfile.read(length))

    def local_origin(self):
        origin = self.headers.get("Origin")
        expected = f"http://127.0.0.1:{self.server.server_port}"
        return origin == expected

    def do_GET(self):
        url = urlsplit(self.path)
        path = url.path
        try:
            if path == "/api/options":
                layout = parse_qs(url.query).get("layout", ["us"])[0]
                self.json_response({"layout": layout, "layouts": LAYOUTS,
                                    "hostLayout": host_layout(),
                                    "hostPlatform": sys.platform,
                                    "keys": key_options(layout), "media": MEDIA, "presets": PRESETS,
                                    "characters": {f"{usage}:{int(shift)}:{int(option)}": char
                                                   for (usage, shift, option), char in characters(layout).items()}})
            elif path == "/api/status":
                try:
                    DEVICE.request("ping")
                    self.json_response({"connected": True, "layersReady": layers_ready(),
                                        "port": getattr(DEVICE, "port_name", None),
                                        "selectedPort": getattr(DEVICE, "selected_port", None)})
                except DeviceError as exc:
                    self.json_response({"connected": False, "message": str(exc),
                                        "selectedPort": getattr(DEVICE, "selected_port", None)})
            elif path == "/api/ports":
                self.json_response({"ports": DEVICE.ports(),
                                    "selected": getattr(DEVICE, "selected_port", None)})
            elif path == "/api/template":
                profile = upgrade(default_profile())
                profile["layout"] = host_layout()
                self.json_response(profile)
            elif path == "/api/profiles":
                lines = DEVICE.request("list").decode("ascii").splitlines()
                self.json_response({"active": lines[0], "ids": sorted(id for id in lines[1:] if id != MARKER_ID)})
            elif match := ID_PATH.fullmatch(path):
                if match.group(1) == MARKER_ID:
                    raise ValueError("This ID is reserved for the layer loader")
                source = DEVICE.request("read", match.group(1).encode("ascii")).decode("utf-8")
                self.json_response(upgrade(parse_lua(source)))
            elif path == "/":
                self.path = "/index.html"
                super().do_GET()
            else:
                super().do_GET()
        except (DeviceError, ValueError, UnicodeError, IndexError) as exc:
            self.json_response({"error": str(exc)}, 400)

    def do_PUT(self):
        self.mutate("put")

    def do_POST(self):
        self.mutate("post")

    def do_DELETE(self):
        self.mutate("delete")

    def mutate(self, method):
        if not self.local_origin():
            self.json_response({"error": "Request must come from the local editor"}, 403)
            return
        path = urlsplit(self.path).path
        try:
            if method == "put" and (match := ID_PATH.fullmatch(path)):
                if match.group(1) == MARKER_ID:
                    raise ValueError("This ID is reserved for the layer loader")
                if not layers_ready():
                    raise ValueError("Install the layer SD card update before saving profiles")
                profile = upgrade(self.body_json())
                if profile["id"] != match.group(1):
                    raise ValueError("Profile ID and URL differ")
                source = generate_lua(profile).encode("utf-8")
                DEVICE.request("write", profile["id"].encode("ascii") + b"\n" + source)
                self.json_response(profile)
            elif method == "post" and path == "/api/translate":
                request = self.body_json()
                profile = upgrade(request["profile"])
                target = request["layout"]
                self.json_response(validate(translate(profile, target)))
            elif method == "post" and path == "/api/port":
                value = self.body_json().get("device")
                if value is not None and not isinstance(value, str):
                    raise ValueError("Invalid serial port")
                DEVICE.select_port(value)
                self.json_response({"selected": value})
            elif method == "post" and path == "/api/active":
                identifier = self.body_json().get("id")
                if not isinstance(identifier, str) or not re.fullmatch(r"[a-z0-9-]{1,32}", identifier) or identifier == MARKER_ID:
                    raise ValueError("Invalid profile ID")
                DEVICE.request("activate", identifier.encode("ascii"))
                self.json_response({"active": identifier})
            elif method == "delete" and (match := ID_PATH.fullmatch(path)):
                if match.group(1) == MARKER_ID:
                    raise ValueError("This ID is reserved for the layer loader")
                DEVICE.request("delete", match.group(1).encode("ascii"))
                self.json_response({"deleted": match.group(1)})
            else:
                self.json_response({"error": "Unknown action"}, 404)
        except (DeviceError, ValueError, UnicodeError, AttributeError, KeyError, TypeError) as exc:
            self.json_response({"error": str(exc)}, 400)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"Keybow editor: {url}", flush=True)
    if not os.environ.get("KEYBOW_NO_BROWSER"):
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        DEVICE.close()
        server.server_close()


if __name__ == "__main__":
    main()
