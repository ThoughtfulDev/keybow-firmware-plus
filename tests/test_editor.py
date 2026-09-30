import copy
import io
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
from unittest.mock import patch

if os.name == "posix":
    import pty
import threading
import unittest
import zlib
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "editor"))

from keybow_editor.layouts import active_language, host_layout, translate
from keybow_editor.profile import default_profile, generate_lua, key_options, parse_lua, upgrade, validate
from keybow_editor.protocol import Device, DeviceError, available_ports, exchange, frame
from keybow_editor import server


class FakePort:
    def __init__(self, response=b"", chunk=3):
        self.response = io.BytesIO(response)
        self.chunk = chunk
        self.written = b""

    def write(self, value):
        self.written += value

    def flush(self):
        pass

    def read(self, size):
        return self.response.read(min(size, self.chunk))


class ProfileTests(unittest.TestCase):
    def test_host_keyboard_layout_detection_and_fallback(self):
        with patch("keybow_editor.layouts.subprocess.run", return_value=SimpleNamespace(
            stdout="com.apple.keylayout.German-DIN-2137\n")):
            self.assertEqual(active_language("darwin"), "de")
            self.assertEqual(host_layout("darwin"), "de-macos")
        with patch("keybow_editor.layouts.subprocess.run", return_value=SimpleNamespace(
            stdout="[('xkb', 'de+nodeadkeys'), ('xkb', 'us')]")):
            self.assertEqual(host_layout("linux"), "de-linux")
        self.assertEqual(host_layout("win32", "de_DE"), "de-windows")
        self.assertEqual(host_layout("darwin", "en_US"), "us")

    def test_default_round_trip_and_lua_syntax(self):
        profile = default_profile()
        source = generate_lua(profile)
        self.assertEqual(parse_lua(source), profile)
        self.assertEqual(source, Path("sdcard/profiles/default.lua").read_text())
        if shutil.which("luac"):
            subprocess.run(["luac", "-p", "sdcard/keys.lua", "sdcard/profiles/default.lua"], check=True)

    def test_invalid_profiles_and_tampered_source(self):
        profile = default_profile()
        invalid = copy.deepcopy(profile)
        invalid["keys"][0]["usage"] = -1
        with self.assertRaises(ValueError):
            validate(invalid)
        invalid = copy.deepcopy(profile)
        invalid["lighting"] = {"mode": "preset", "preset": "../../bad"}
        with self.assertRaises(ValueError):
            validate(invalid)
        with self.assertRaises(ValueError):
            parse_lua(generate_lua(profile) + "os.execute('x')")

    def test_static_and_media_profile(self):
        profile = default_profile()
        profile["keys"][0] = {"kind": "media", "usage": 4}
        profile["keys"][1] = {"kind": "keyboard", "usage": 4, "modifiers": 3}
        profile["lighting"] = {"mode": "static", "colors": ["#ff8822"] * 12}
        source = generate_lua(profile)
        self.assertIn("keybow.set_pixel(0, 255, 136, 34)", source)
        self.assertEqual(parse_lua(source), profile)

    def test_unassigned_is_valid_and_sends_nothing(self):
        profile = default_profile()
        profile["keys"][0] = {"kind": "none"}
        source = generate_lua(profile)
        if shutil.which("luac"):
            subprocess.run(["luac", "-p", "-"], input=source, text=True, check=True)
        self.assertIn("function handle_key_00(pressed)  end", source)
        modern = upgrade(profile)
        self.assertEqual(modern["layers"][0]["keys"][0], {"kind": "none"})
        self.assertEqual(parse_lua(generate_lua(modern)), modern)

    def test_layer_validation_and_source_limit(self):
        profile = upgrade(default_profile())
        profile["layers"].append({"id": "other", "name": "Other",
            "keys": [{"kind": "none"} for _ in range(12)],
            "lighting": {"mode": "static", "colors": ["#123456"] * 12}})
        profile["layers"][0]["keys"][0] = {"kind": "layer", "target": "other", "mode": "toggle"}
        self.assertEqual(parse_lua(generate_lua(profile)), profile)
        invalid = copy.deepcopy(profile)
        invalid["layers"][1]["keys"][0] = {"kind": "media", "usage": 0}
        with self.assertRaisesRegex(ValueError, "unassigned"):
            validate(invalid)
        invalid = copy.deepcopy(profile)
        invalid["layers"][0]["keys"][0]["target"] = "absent"
        with self.assertRaisesRegex(ValueError, "target"):
            validate(invalid)
        invalid = copy.deepcopy(profile)
        invalid["layers"][0]["keys"][0] = {"kind": "layer", "target": "other", "mode": "timed", "seconds": 0}
        with self.assertRaisesRegex(ValueError, "seconds"):
            validate(invalid)
        from keybow_editor import profile as profile_module
        original = profile_module.MAX_SOURCE
        profile_module.MAX_SOURCE = 100
        try:
            with self.assertRaisesRegex(ValueError, "limit"):
                generate_lua(profile)
        finally:
            profile_module.MAX_SOURCE = original

    @unittest.skipUnless(shutil.which("lua"), "Lua interpreter unavailable")
    def test_layer_loader_switches_and_releases_keys(self):
        profile = upgrade(default_profile())
        base = profile["layers"][0]
        other = {"id": "other", "name": "Other", "keys": [{"kind": "none"} for _ in range(12)],
                 "lighting": {"mode": "static", "colors": ["#112233"] * 12}}
        third = {"id": "third", "name": "Third", "keys": [{"kind": "none"} for _ in range(12)],
                 "lighting": {"mode": "preset", "preset": "rainbow"}}
        base["keys"][0] = {"kind": "layer", "target": "other", "mode": "toggle"}
        other["keys"][1] = {"kind": "keyboard", "usage": 4, "modifiers": 0}
        other["keys"][2] = {"kind": "layer", "target": "third", "mode": "hold"}
        other["keys"][4] = {"kind": "layer", "target": "third", "mode": "timed", "seconds": 2}
        third["keys"][3] = {"kind": "keyboard", "usage": 5, "modifiers": 0}
        third["keys"][5] = {"kind": "layer", "target": "base", "mode": "timed", "seconds": 1}
        profile["layers"].extend([other, third])
        source = generate_lua(profile)
        root = Path.cwd().resolve()
        with tempfile.TemporaryDirectory() as tmp:
            profiles = Path(tmp) / "profiles"
            profiles.mkdir()
            (profiles / "active").write_text("default")
            (profiles / "default.lua").write_text(source)
            script = f"""
package.path = '{root}/sdcard/?.lua;{root}/sdcard/?/init.lua;' .. package.path
local events = {{}}
local now = 0
local fail_pattern = false
keybow_get_millis = function() return now end
keybow_set_key = function(code, down) events[#events+1] = 'k'..code..tostring(down) end
keybow_set_modifier = function() end
keybow_set_media_key = function() end
keybow_auto_lights = function() end
keybow_set_pixel = function() end
keybow_load_pattern = function() return not fail_pattern end
dofile('{root}/sdcard/keys.lua')
setup()
handle_key_01(true) -- Base key is held during the layer switch.
handle_key_00(true)
handle_key_00(false)
assert(events[#events] == 'k89false')
handle_key_01(false) -- Old release cannot affect the new layer.
handle_key_01(true)
handle_key_01(false)
assert(events[#events] == 'k4false')
handle_key_00(true) -- Reserved return key.
handle_key_00(false)
handle_key_01(true)
handle_key_01(false)
assert(events[#events] == 'k89false')
handle_key_00(true); handle_key_00(false)
fail_pattern = true
handle_key_02(true); handle_key_02(false) -- Failed setup stays on Other.
handle_key_01(true); handle_key_01(false)
assert(events[#events] == 'k4false')
fail_pattern = false
handle_key_02(true) -- Hold Third.
handle_key_03(true); handle_key_03(false)
assert(events[#events] == 'k5false')
handle_key_02(false)
handle_key_01(true); handle_key_01(false)
assert(events[#events] == 'k4false')
handle_key_04(true); handle_key_04(false) -- Timed Third.
tick(1999)
handle_key_03(true); handle_key_03(false)
assert(events[#events] == 'k5false')
tick(2000)
handle_key_01(true); handle_key_01(false)
assert(events[#events] == 'k4false')
now = 2500
handle_key_04(true); handle_key_04(false) -- Timed Third again.
now = 3000
handle_key_05(true); handle_key_05(false) -- New switch cancels earlier timer.
tick(3999)
handle_key_03(true); handle_key_03(false) -- On Base; key 03 is not Third's key.
assert(events[#events] ~= 'k5false')
tick(4000) -- Return to Third.
tick(4500) -- Original timer does not return to Other.
handle_key_03(true); handle_key_03(false)
assert(events[#events] == 'k5false')
"""
            subprocess.run(["lua", "-"], cwd=tmp, input=script, text=True, check=True)

    @unittest.skipUnless(shutil.which("lua"), "Lua interpreter unavailable")
    def test_layer_loader_keeps_legacy_profiles_working(self):
        root = Path.cwd().resolve()
        for version in (1, 2):
            profile = default_profile()
            if version == 2:
                profile["version"] = 2
                profile["layout"] = "de"
            with self.subTest(version=version), tempfile.TemporaryDirectory() as tmp:
                profiles = Path(tmp) / "profiles"
                profiles.mkdir()
                (profiles / "active").write_text("default")
                (profiles / "default.lua").write_text(generate_lua(profile))
                script = f"""
package.path = '{root}/sdcard/?.lua;{root}/sdcard/?/init.lua;' .. package.path
local events = {{}}
keybow_set_key = function(code, down) events[#events+1] = tostring(code)..tostring(down) end
keybow_set_modifier = function() end
keybow_load_pattern = function() return true end
keybow_auto_lights = function() end
dofile('{root}/sdcard/keys.lua')
setup()
handle_key_00(true); handle_key_00(false)
assert(table.concat(events, ',') == '98true,98false')
"""
                subprocess.run(["lua", "-"], cwd=tmp, input=script, text=True, check=True)

    def test_v1_v2_v3_upgrade_and_v4_round_trip(self):
        legacy = default_profile()
        self.assertEqual(parse_lua(generate_lua(legacy)), legacy)
        v2 = {**legacy, "version": 2, "layout": "de"}
        self.assertEqual(parse_lua(generate_lua(v2)), validate(v2))
        modern = upgrade(legacy)
        self.assertEqual(modern["layout"], "us")
        self.assertEqual(modern["version"], 4)
        self.assertEqual(modern["layers"][0]["id"], "base")
        self.assertEqual(parse_lua(generate_lua(modern)), validate(modern))
        self.assertEqual(upgrade(v2)["layout"], "de-macos")
        legacy_v3 = {**modern, "version": 3, "layout": "de"}
        self.assertEqual(upgrade(parse_lua(generate_lua(legacy_v3)))["layout"], "de-macos")
        self.assertEqual(legacy["version"], 1)

    def test_german_legends_and_translation(self):
        options = {item["usage"]: item["label"] for item in key_options("de-macos")}
        self.assertEqual((options[28], options[29], options[45], options[47], options[51], options[52]),
                         ("Z", "Y", "ß", "Ü", "Ö", "Ä"))
        profile = upgrade(default_profile())
        keys = profile["layers"][0]["keys"]
        keys[0] = {"kind": "keyboard", "usage": 29, "modifiers": 8}  # Command+Z
        keys[1] = {"kind": "keyboard", "usage": 31, "modifiers": 2}  # @
        keys[2] = {"kind": "keyboard", "usage": 47, "modifiers": 0}  # [
        keys[3] = {"kind": "media", "usage": 4}
        german = translate(profile, "de-macos")
        changed = german["layers"][0]["keys"]
        self.assertEqual(changed[0], {"kind": "keyboard", "usage": 28, "modifiers": 8})
        self.assertEqual(changed[1], {"kind": "keyboard", "usage": 15, "modifiers": 4})
        self.assertEqual(changed[2], {"kind": "keyboard", "usage": 34, "modifiers": 4})
        self.assertEqual(changed[3], keys[3])
        self.assertEqual(translate(german, "us")["layers"][0]["keys"][:3], keys[:3])
        self.assertEqual(parse_lua(generate_lua(german)), validate(german))

    def test_untranslatable_assignment_aborts_switch(self):
        profile = upgrade(default_profile())
        profile["layout"] = "de-macos"
        profile["layers"][0]["keys"][2] = {"kind": "keyboard", "usage": 52, "modifiers": 0}  # ä
        with self.assertRaisesRegex(ValueError, "03"):
            translate(profile, "us")
        self.assertEqual(profile["layout"], "de-macos")

    def test_windows_linux_german_translation_all_layers(self):
        profile = upgrade(default_profile())
        profile["layers"].append({"id": "other", "name": "Other",
            "keys": [{"kind": "none"} for _ in range(12)],
            "lighting": {"mode": "preset", "preset": "default"}})
        profile["layers"][0]["keys"][0] = {"kind": "keyboard", "usage": 31, "modifiers": 2}  # @
        profile["layers"][1]["keys"][0] = {"kind": "keyboard", "usage": 29, "modifiers": 1}  # Ctrl+Z
        for target in ("de-windows", "de-linux"):
            with self.subTest(target=target):
                german = translate(profile, target)
                self.assertEqual(german["layers"][0]["keys"][0],
                                 {"kind": "keyboard", "usage": 20, "modifiers": 64})
                self.assertEqual(german["layers"][1]["keys"][0],
                                 {"kind": "keyboard", "usage": 28, "modifiers": 1})
                self.assertEqual(translate(german, "us")["layers"], profile["layers"])
                self.assertIn("return {version=3,layers={", generate_lua(german))

    def test_cross_platform_gui_shortcut_requires_manual_choice(self):
        profile = upgrade(default_profile())
        profile["layout"] = "de-macos"
        profile["layers"][0]["keys"][0] = {"kind": "keyboard", "usage": 28, "modifiers": 8}
        with self.assertRaisesRegex(ValueError, "01"):
            translate(profile, "de-windows")
        self.assertEqual(profile["layout"], "de-macos")

    @unittest.skipUnless(shutil.which("lua"), "Lua interpreter unavailable")
    def test_shared_modifier_and_key_release(self):
        profile = default_profile()
        profile["keys"][0] = {"kind": "keyboard", "usage": 4, "modifiers": 1}
        profile["keys"][1] = {"kind": "keyboard", "usage": 4, "modifiers": 1}
        source = generate_lua(profile)
        preamble = """
package.path = 'sdcard/?.lua;sdcard/?/init.lua;' .. package.path
local events = {}
keybow_set_modifier = function(code, pressed)
  table.insert(events, 'm' .. code .. tostring(pressed))
end
keybow_set_key = function(code, pressed)
  table.insert(events, 'k' .. code .. tostring(pressed))
end
keybow_load_pattern = function() return true end
keybow_auto_lights = function() end
"""
        postamble = """
setup()
handle_key_00(true)
handle_key_01(true)
handle_key_00(false)
handle_key_01(false)
assert(table.concat(events, ',') == 'm0true,k4true,k4false,m0false')
"""
        subprocess.run(["lua", "-"], input=preamble + source + postamble, text=True, check=True)

    @unittest.skipUnless(shutil.which("lua"), "Lua interpreter unavailable")
    def test_preset_setup_rejects_missing_pattern(self):
        source = generate_lua(default_profile())
        preamble = """
package.path = 'sdcard/?.lua;sdcard/?/init.lua;' .. package.path
keybow_load_pattern = function() return false end
"""
        subprocess.run(
            ["lua", "-"],
            input=preamble + source + "assert(not pcall(setup))\n",
            text=True, check=True,
        )


class EditorFlowTests(unittest.TestCase):
    def test_desktop_launcher_closes_server_and_port(self):
        from keybow_editor import desktop
        events = []
        class Httpd:
            server_port = 8765
            def __init__(self, *args):
                events.append("bind")
            def serve_forever(self):
                events.append("serve")
            def shutdown(self):
                events.append("shutdown")
            def server_close(self):
                events.append("server_close")
        fake_webview = SimpleNamespace(
            create_window=lambda *a, **k: events.append(("window", a[1])),
            start=lambda **k: events.append("window_exit"))
        with patch.object(desktop.server, "ThreadingHTTPServer", Httpd), \
             patch.object(desktop.server, "DEVICE", SimpleNamespace(close=lambda: events.append("port_close"))), \
             patch.dict(sys.modules, {"webview": fake_webview}):
            desktop.main()
        self.assertIn(("window", "http://127.0.0.1:8765/"), events)
        self.assertEqual(events[-3:], ["shutdown", "server_close", "port_close"])

    def test_http_profile_save_and_activate_with_fake_device(self):
        class FakeDevice:
            def __init__(self):
                self.files = {"default": generate_lua(default_profile()).encode(),
                              server.MARKER_ID: server.MARKER_SOURCE}
                self.active = "default"
                self.selected_port = None
                self.port_name = "COM7"

            def ports(self):
                return [{"device": "COM7", "label": "Keybow", "likely": True}]

            def select_port(self, name):
                if name not in (None, "COM7"):
                    raise DeviceError("Selected serial port is no longer available")
                self.selected_port = name

            def request(self, command, payload=b""):
                if command == "ping":
                    return b"Keybow 1"
                if command == "list":
                    return (self.active + "\n" + "\n".join(self.files) + "\n").encode()
                if command == "read":
                    if payload.decode() not in self.files:
                        raise DeviceError("missing")
                    return self.files[payload.decode()]
                if command == "write":
                    identifier, source = payload.split(b"\n", 1)
                    self.files[identifier.decode()] = source
                    return b""
                if command == "activate":
                    self.active = payload.decode()
                    return b""
                raise AssertionError(command)

        def request(method, path, body=None):
            client, endpoint = socket.socketpair()
            data = b"" if body is None else json.dumps(body).encode()
            headers = (f"{method} {path} HTTP/1.1\r\nHost: 127.0.0.1:8765\r\n"
                       f"Origin: http://127.0.0.1:8765\r\nContent-Length: {len(data)}\r\n"
                       "Connection: close\r\n\r\n").encode()
            try:
                client.sendall(headers + data)
                client.shutdown(socket.SHUT_WR)
                server.Handler(endpoint, ("127.0.0.1", 0), SimpleNamespace(server_port=8765))
                endpoint.close()
                response = bytearray()
                while chunk := client.recv(65536):
                    response.extend(chunk)
                return json.loads(bytes(response).split(b"\r\n\r\n", 1)[1])
            finally:
                client.close()
                endpoint.close()

        import json
        original = server.DEVICE
        server.DEVICE = FakeDevice()
        try:
            current = request("GET", "/api/profiles/default")
            self.assertEqual((current["version"], current["layout"]), (4, "us"))
            self.assertTrue(request("GET", "/api/status")["layersReady"])
            self.assertEqual(request("GET", "/api/ports")["ports"][0]["device"], "COM7")
            self.assertEqual(request("POST", "/api/port", {"device": "COM7"}), {"selected": "COM7"})
            self.assertIn("available", request("POST", "/api/port", {"device": "COM9"})["error"])
            self.assertEqual(request("GET", "/api/template")["version"], 4)
            self.assertNotIn(server.MARKER_ID, request("GET", "/api/profiles")["ids"])
            current["id"] = "german-test"
            current["name"] = "German layers"
            current["layout"] = "de-macos"
            current["layers"][0]["lighting"] = {"mode": "static", "colors": ["#2a569b"] * 12}
            current["layers"].append({"id": "second", "name": "Second",
                "keys": [{"kind": "none"} for _ in range(12)],
                "lighting": {"mode": "preset", "preset": "rainbow"}})
            current["layers"][0]["keys"][0] = {"kind": "layer", "target": "second", "mode": "toggle"}
            saved = request("PUT", "/api/profiles/german-test", current)
            self.assertEqual(saved, current)
            self.assertEqual(request("GET", "/api/profiles/german-test"), current)
            current["name"] = "Renamed profile"
            self.assertEqual(request("PUT", "/api/profiles/german-test", current)["id"], "german-test")
            self.assertEqual(request("GET", "/api/profiles/german-test")["name"], "Renamed profile")
            self.assertEqual(request("POST", "/api/active", {"id": "german-test"}),
                             {"active": "german-test"})
            self.assertEqual(request("GET", "/api/profiles")["active"], "german-test")
            translated = request("POST", "/api/translate", {"profile": current, "layout": "us"})
            self.assertEqual(translated["layout"], "us")
            del server.DEVICE.files[server.MARKER_ID]
            self.assertFalse(request("GET", "/api/status")["layersReady"])
            self.assertIn("Install the layer SD card update",
                          request("PUT", "/api/profiles/german-test", current)["error"])
        finally:
            server.DEVICE = original

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_color_conversion_and_invalid_input(self):
        script = """
const c = require('./editor/static/color.js');
for (const hex of ['#000000', '#ffffff', '#ff0000', '#38a7d2', '#00ff80']) {
  const rgb = c.parseHex(hex), hsv = c.rgbToHsv(rgb);
  if (c.toHex(rgb) !== hex || c.hsvToRgb(hsv.h, hsv.s, hsv.v).some((n, i) => Math.abs(n-rgb[i]) > 1)) process.exit(1);
}
if (c.parseHex('#wrong') !== null || c.parseHex('#ff00') !== null) process.exit(1);
"""
        subprocess.run(["node", "-e", script], check=True)


class ProtocolTests(unittest.TestCase):
    @staticmethod
    def response(command, status, payload=b""):
        body = struct.pack("<BH", command | 0x80, len(payload) + 1) + bytes([status]) + payload
        return b"KBW1" + body + struct.pack("<I", zlib.crc32(body))

    def test_fragmented_response_and_request_crc(self):
        port = FakePort(self.response(1, 0, b"Keybow 1"), chunk=1)
        self.assertEqual(exchange(port, 1), b"Keybow 1")
        self.assertEqual(port.written, frame(1))
        self.assertEqual(struct.unpack("<I", port.written[-4:])[0], zlib.crc32(port.written[4:-4]))

    def test_corrupt_timeout_and_device_rejection(self):
        corrupt = bytearray(self.response(2, 0, b"default\n"))
        corrupt[-1] ^= 1
        with self.assertRaisesRegex(DeviceError, "Corrupt"):
            exchange(FakePort(bytes(corrupt)), 2)
        with self.assertRaisesRegex(DeviceError, "stopped responding"):
            exchange(FakePort(), 2)
        with self.assertRaisesRegex(DeviceError, "could not be applied"):
            exchange(FakePort(self.response(5, 4)), 5)
        with self.assertRaisesRegex(DeviceError, "Reconnect Keybow"):
            exchange(FakePort(self.response(4, 3)), 4)

    def test_oversized_request(self):
        with self.assertRaises(ValueError):
            frame(4, b"x" * 16385)

    def test_discovery_selection_and_reconnect(self):
        items = [SimpleNamespace(device="COM2", description="Other", product=None,
                                 manufacturer=None, vid=1, pid=2),
                 SimpleNamespace(device="COM7", description="USB Serial", product="Keybow",
                                 manufacturer="Pimoroni", vid=0x1d6b, pid=0x0104)]
        from keybow_editor import protocol
        with patch.object(protocol.list_ports, "comports", return_value=items):
            ports = available_ports()
        self.assertEqual([entry["device"] for entry in ports], ["COM7", "COM2"])
        opened = []
        class Port(FakePort):
            def close(self):
                self.closed = True
        def factory(name, **kwargs):
            self.assertEqual(kwargs["baudrate"], 115200)
            port = Port(self.response(1, 0, b"Keybow 1") + self.response(1, 0, b"Keybow 1"))
            port.name = name
            port.closed = False
            opened.append(port)
            return port
        device = Device(port_factory=factory, ports_provider=lambda: ports)
        with patch.dict(os.environ, {"KEYBOW_PORT": ""}):
            self.assertEqual(device.request("ping"), b"Keybow 1")
            self.assertEqual(device.port_name, "COM7")
            device.select_port("COM2")
            self.assertTrue(opened[0].closed)
            self.assertEqual(device.request("ping"), b"Keybow 1")
            self.assertEqual(device.port_name, "COM2")
            device.close()
            self.assertEqual(device.request("ping"), b"Keybow 1")
            self.assertEqual(device.port_name, "COM2")
            with self.assertRaisesRegex(DeviceError, "no longer available"):
                device.select_port("COM9")
            device.close()

    def test_port_errors(self):
        from keybow_editor.protocol import serial_error
        with patch("keybow_editor.protocol.sys.platform", "linux"):
            self.assertIn("dialout", str(serial_error(OSError("Permission denied"))))
        self.assertIn("busy", str(serial_error(OSError("Device or resource busy"))))
        device = Device(ports_provider=lambda: [])
        with self.assertRaisesRegex(DeviceError, "port picker"):
            device.request("ping")

    def test_disconnect_closes_port_and_next_request_reconnects(self):
        opened = []
        class Port(FakePort):
            def close(self):
                self.closed = True
        def factory(name, **kwargs):
            response = self.response(1, 0, b"Keybow 1")
            port = Port(response if not opened else response + response)
            port.closed = False
            opened.append(port)
            return port
        device = Device(port_factory=factory, ports_provider=lambda: [
            {"device": "COM7", "label": "Keybow", "likely": True}])
        with patch.dict(os.environ, {"KEYBOW_PORT": ""}):
            with self.assertRaisesRegex(DeviceError, "stopped responding"):
                device.request("ping")
            self.assertTrue(opened[0].closed)
            self.assertEqual(device.request("ping"), b"Keybow 1")
            self.assertEqual(len(opened), 2)
            device.close()

    @unittest.skipUnless(os.name == "posix", "PTY test needs POSIX")
    def test_serial_transport_over_pty(self):
        master, slave = pty.openpty()
        import serial
        port = serial.Serial(os.ttyname(slave), baudrate=115200, timeout=2, write_timeout=2)

        def device():
            request = bytearray()
            while len(request) < 11:
                request.extend(os.read(master, 11 - len(request)))
            self.assertEqual(bytes(request), frame(1))
            os.write(master, self.response(1, 0, b"Keybow 1"))

        worker = threading.Thread(target=device)
        worker.start()
        try:
            self.assertEqual(exchange(port, 1), b"Keybow 1")
        finally:
            worker.join(timeout=2)
            port.close()
            os.close(master)
            os.close(slave)


if __name__ == "__main__":
    unittest.main()
