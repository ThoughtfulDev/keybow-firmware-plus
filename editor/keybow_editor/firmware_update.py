"""GitHub firmware release discovery and a profile-preserving USB update."""

import hashlib
import io
import json
import os
from pathlib import Path
import re
import struct
import sys
import tempfile
import time
from urllib.request import Request, urlopen
from urllib.error import URLError
from zipfile import ZipFile

from .firmware_manifest import from_zip, wire_manifest
from .protocol import DeviceError

REPOSITORY = "ThoughtfulDev/keybow-firmware-plus"
RELEASES_URL = f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=100"
TAG = re.compile(r"firmware-v([0-9]+)\.([0-9]+)\.([0-9]+)\Z")
MAX_DOWNLOAD = 35 * 1024 * 1024


class UpdateFailed(DeviceError):
    pass


def get_url(url, limit=MAX_DOWNLOAD):
    request = Request(url, headers={"User-Agent": "keybow-editor-firmware-update/1", "Accept": "application/vnd.github+json"})
    try:
        with urlopen(request, timeout=20) as response:
            if not response.geturl().startswith("https://"):
                raise ValueError("Firmware download did not use HTTPS")
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > limit:
                raise ValueError("Firmware download is too large")
            data = response.read(limit + 1)
    except (URLError, TimeoutError) as exc:
        raise ValueError(f"Could not reach GitHub for firmware: {exc}") from exc
    if len(data) > limit:
        raise ValueError("Firmware download is too large")
    return data


def latest_release():
    releases = json.loads(get_url(RELEASES_URL, 4 * 1024 * 1024))
    if not isinstance(releases, list):
        raise ValueError("GitHub did not return a firmware release list")
    candidates = []
    for item in releases:
        match = TAG.fullmatch(item.get("tag_name", ""))
        if not match or item.get("draft") or item.get("prerelease"):
            continue
        tag = item["tag_name"]
        filename = f"keybow-firmware-plus-{tag}-sdcard.zip"
        manifest_name = f"keybow-firmware-plus-{tag}-update.json"
        asset = next((asset for asset in item.get("assets", []) if asset.get("name") == filename), None)
        manifest_asset = next((asset for asset in item.get("assets", []) if asset.get("name") == manifest_name), None)
        if asset and manifest_asset and isinstance(asset.get("size"), int) and asset["size"] <= MAX_DOWNLOAD:
            url = asset.get("browser_download_url", "")
            expected = f"https://github.com/{REPOSITORY}/releases/download/{tag}/{filename}"
            if url.lower() == expected.lower():
                candidates.append((tuple(map(int, match.groups())), {"tag": tag, "version": tag.removeprefix("firmware-v"),
                                                               "url": url, "size": asset.get("size")}))
    if not candidates:
        raise ValueError("No compatible firmware release was found on GitHub")
    return max(candidates, key=lambda pair: pair[0])[1]


def backup_root():
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/Keybow Editor/firmware-backups"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming")) / "Keybow Editor/firmware-backups"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "keybow-editor/firmware-backups"


def read_profiles(device):
    lines = device.request("list").decode("ascii").splitlines()
    if not lines or not re.fullmatch(r"[a-z0-9-]{1,32}", lines[0]):
        raise DeviceError("Keybow returned an invalid active profile")
    ids = sorted(set(lines[1:]))
    if not ids or lines[0] not in ids or any(not re.fullmatch(r"[a-z0-9-]{1,32}", identifier) for identifier in ids):
        raise DeviceError("Keybow returned an invalid profile list")
    profiles = {identifier: device.request("read", identifier.encode("ascii")) for identifier in ids}
    if any(not source or len(source) > 15000 for source in profiles.values()):
        raise DeviceError("A profile could not be backed up")
    return lines[0], profiles


def save_backup(active, profiles):
    root = backup_root()
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="keybow-update-", dir=root) as temp:
        directory = Path(temp)
        (directory / "profiles").mkdir()
        hashes = {}
        for identifier, source in profiles.items():
            path = directory / "profiles" / f"{identifier}.lua"
            path.write_bytes(source)
            hashes[identifier] = hashlib.sha256(source).hexdigest()
        metadata = {"active": active, "sha256": hashes}
        (directory / "backup.json").write_text(json.dumps(metadata, indent=2) + "\n")
        for identifier, digest in hashes.items():
            if hashlib.sha256((directory / "profiles" / f"{identifier}.lua").read_bytes()).hexdigest() != digest:
                raise OSError("Profile backup failed verification")
        destination = root / f"{time.strftime('%Y%m%d-%H%M%S')}-{time.time_ns() % 1000000:06d}"
        directory.rename(destination)
    return destination


def reconcile(device, active, profiles):
    try:
        new_active, new_profiles = read_profiles(device)
    except DeviceError:
        new_active, new_profiles = None, {}
    for identifier, source in profiles.items():
        if new_profiles.get(identifier) != source:
            device.request("write", identifier.encode("ascii") + b"\n" + source)
    if new_active != active:
        device.request("activate", active.encode("ascii"))
    final_active, final_profiles = read_profiles(device)
    if final_active != active or any(final_profiles.get(identifier) != source for identifier, source in profiles.items()):
        raise DeviceError("Saved profiles differ after the update; use the local backup to recover them")


def device_info(device):
    try:
        lines = device.request("update_info").decode("ascii").splitlines()
    except DeviceError as exc:
        if "Invalid profile or request" in str(exc) or "rejected" in str(exc):
            raise DeviceError("Keybow needs the one-time SD card updater upgrade") from exc
        raise
    if len(lines) != 2 or not re.fullmatch(r"(?:unknown|[0-9]+\.[0-9]+\.[0-9]+)", lines[0]) or lines[1] not in {"idle", "staging", "prepared", "pending", "rolled-back"}:
        raise DeviceError("Keybow returned invalid firmware status")
    return {"version": lines[0], "state": lines[1]}


def install(device, release, progress):
    current = device_info(device)
    if current["state"] == "pending":
        raise DeviceError("Keybow is already restarting for an update")
    if current["version"] != "unknown" and tuple(map(int, current["version"].split("."))) >= tuple(map(int, release["version"].split("."))):
        raise ValueError("Keybow already has this firmware version or a newer one")
    progress("Downloading firmware", 0)
    package = get_url(release["url"])
    with ZipFile(io.BytesIO(package)) as archive:
        manifest = from_zip(archive, release["version"])
        files = [(item, archive.read(item["path"])) for item in manifest["files"]]
    progress("Backing up profiles", 0)
    active, profiles = read_profiles(device)
    backup = save_backup(active, profiles)
    progress("Sending firmware", 0, str(backup))
    device.request("update_begin", wire_manifest(manifest))
    total = sum(item["size"] for item, _ in files)
    failures = 0
    while True:
        answer = device.request("update_query")
        if len(answer) != 5:
            raise DeviceError("Keybow returned invalid transfer progress")
        index, offset = answer[0], struct.unpack("<I", answer[1:])[0]
        if index == len(files):
            break
        if index > len(files) or offset > len(files[index][1]):
            raise DeviceError("Keybow returned invalid transfer offset")
        completed = sum(len(data) for _, data in files[:index]) + offset
        progress("Sending firmware", int(completed * 100 / total), str(backup))
        payload = bytes([index]) + struct.pack("<I", offset) + files[index][1][offset:offset + 8192]
        if len(payload) <= 5:
            raise DeviceError("Keybow stopped accepting firmware data")
        try:
            device.request("update_chunk", payload)
            failures = 0
        except DeviceError as exc:
            if "could not write to its SD card" in str(exc):
                raise
            failures += 1
            if failures >= 3:
                raise DeviceError("USB transfer stopped after three failed attempts") from exc
            # A lost response can mean the chunk was committed. Query its durable offset.
            device.close()
            time.sleep(0.5)
    progress("Verifying on Keybow", 100, str(backup))
    try:
        device.request("update_verify", timeout=30)
    except DeviceError:
        try:
            device.request("update_reset")
        except DeviceError:
            pass
        raise
    progress("Restarting Keybow", 100, str(backup))
    device.request("update_apply")
    device.close()
    deadline = time.monotonic() + 120
    last_error = None
    while time.monotonic() < deadline:
        time.sleep(2)
        try:
            info = device_info(device)
            if info["state"] in {"pending", "staging", "prepared"}:
                device.close()
                continue
            reconcile(device, active, profiles)
            if info["state"] == "rolled-back":
                raise UpdateFailed("The firmware failed to start and Keybow restored its previous runtime")
            if info["version"] != release["version"]:
                raise UpdateFailed("Keybow restarted with an unexpected firmware version")
            return str(backup)
        except UpdateFailed:
            raise
        except DeviceError as exc:
            last_error = exc
            device.close()
    raise DeviceError(f"Could not verify Keybow after restart. Profile backup: {backup}. Last error: {last_error}")
