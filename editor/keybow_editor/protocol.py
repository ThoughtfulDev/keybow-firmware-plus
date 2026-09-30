"""Version 1 USB serial framing shared with keybow/profiles.c."""

import os
import struct
import sys
import threading
import serial
from serial.tools import list_ports
import zlib

MAGIC = b"KBW1"
MAX_PAYLOAD = 16384
COMMANDS = {"ping": 1, "list": 2, "read": 3, "write": 4, "activate": 5, "delete": 6,
            "update_info": 7, "update_begin": 8, "update_query": 9,
            "update_chunk": 10, "update_verify": 11, "update_apply": 12,
            "update_reset": 13}
ERRORS = {
    1: "Invalid profile or request",
    2: "Profile not found",
    3: "Keybow could not write to its SD card. Reconnect Keybow's USB cable and retry. If this keeps happening, check the SD card for errors.",
    4: "Profile could not be applied",
}


class DeviceError(Exception):
    pass


def available_ports():
    """All serial ports for manual selection, with likely Keybow ports first."""
    ports = []
    for item in list_ports.comports():
        likely = ("keybow" in f"{item.product} {item.manufacturer} {item.description}".lower()
                  or (item.vid, item.pid) == (0x1d6b, 0x0104))
        ports.append({"device": item.device, "label": item.description or item.device,
                      "likely": likely})
    return sorted(ports, key=lambda item: (not item["likely"], item["device"]))


def serial_error(exc):
    message = str(exc)
    lower = message.lower()
    if "permission denied" in lower:
        advice = (" On Linux, add your user to the dialout group, then sign out and back in."
                  if sys.platform.startswith("linux") else " Check serial port access and close other apps using it.")
        return DeviceError("Cannot open serial port: permission denied." + advice)
    if "busy" in lower or "access is denied" in lower:
        return DeviceError("Serial port is busy. Close any terminal or other editor using Keybow.")
    if "no such file" in lower or "file not found" in lower or "cannot find" in lower:
        return DeviceError("Serial port disappeared. Reconnect Keybow and refresh the port list.")
    return DeviceError(f"Cannot use serial port: {message}")



def frame(command, payload=b""):
    if not 0 <= command <= 127 or len(payload) > MAX_PAYLOAD:
        raise ValueError("Frame is too large")
    body = struct.pack("<BH", command, len(payload)) + payload
    return MAGIC + body + struct.pack("<I", zlib.crc32(body))


def read_exact(port, size):
    data = bytearray()
    while len(data) < size:
        chunk = port.read(size - len(data))
        if not chunk:
            raise DeviceError("Keybow stopped responding")
        data.extend(chunk)
    return bytes(data)


def exchange(port, command, payload=b""):
    port.write(frame(command, payload))
    port.flush()
    header = read_exact(port, 7)
    if header[:4] != MAGIC:
        raise DeviceError("Unexpected data from Keybow")
    response, length = struct.unpack("<BH", header[4:])
    if response != (command | 0x80) or not 1 <= length <= MAX_PAYLOAD:
        raise DeviceError("Invalid Keybow response")
    body = read_exact(port, length)
    checksum = struct.unpack("<I", read_exact(port, 4))[0]
    if zlib.crc32(header[4:] + body) != checksum:
        raise DeviceError("Corrupt Keybow response")
    if body[0]:
        raise DeviceError(ERRORS.get(body[0], "Keybow rejected the request"))
    return body[1:]


class Device:
    def __init__(self, port_factory=None, ports_provider=None):
        self.port = None
        self.port_name = None
        self.selected_port = None
        self.lock = threading.RLock()
        self.port_factory = port_factory or serial.Serial
        self.ports_provider = ports_provider or available_ports

    def ports(self):
        return self.ports_provider()

    def select_port(self, name):
        with self.lock:
            if name is not None and name not in {item["device"] for item in self.ports()}:
                raise DeviceError("Selected serial port is no longer available")
            self.close()
            self.selected_port = name

    def close(self):
        with self.lock:
            if self.port:
                self.port.close()
                self.port = None
                self.port_name = None

    def _connect(self):
        if self.port:
            return
        override = os.environ.get("KEYBOW_PORT")
        names = [override or self.selected_port] if (override or self.selected_port) else [
            item["device"] for item in self.ports() if item["likely"]]
        if not names:
            raise DeviceError("No likely Keybow serial port found. Use the port picker to select one manually.")
        errors = []
        for name in names:
            candidate = None
            try:
                candidate = self.port_factory(name, baudrate=115200, timeout=2, write_timeout=2)
                if exchange(candidate, COMMANDS["ping"]) == b"Keybow 1":
                    self.port = candidate
                    self.port_name = name
                    return
                errors.append(f"{name}: incompatible device")
            except (OSError, serial.SerialException, DeviceError) as exc:
                errors.append(f"{name}: {serial_error(exc) if not isinstance(exc, DeviceError) else exc}")
            finally:
                if candidate and candidate is not self.port:
                    candidate.close()
        if len(names) == 1:
            raise DeviceError(errors[0])
        raise DeviceError("No compatible Keybow found. " + "; ".join(errors))

    def request(self, command, payload=b"", timeout=None):
        with self.lock:
            self._connect()
            old_timeout = self.port.timeout if timeout is not None else None
            try:
                if timeout is not None:
                    self.port.timeout = timeout
                return exchange(self.port, COMMANDS[command], payload)
            except DeviceError as exc:
                if "rejected" not in str(exc) and str(exc) not in ERRORS.values():
                    self.close()
                raise
            except (OSError, serial.SerialException) as exc:
                self.close()
                raise serial_error(exc) from exc
            finally:
                if self.port and timeout is not None:
                    self.port.timeout = old_timeout
