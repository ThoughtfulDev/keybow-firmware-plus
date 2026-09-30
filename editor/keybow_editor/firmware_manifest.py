"""Create and validate the small, explicitly allowlisted USB runtime package."""

import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile

DEVICE = "keybow-12"
FORMAT = 1
MAX_FILE = 4 * 1024 * 1024
MAX_TOTAL = 8 * 1024 * 1024
MAX_FILES = 64
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+\Z")
FIXED = {"keybow", "keys.lua", "keybow.lua", "default.png", "firmware-version"}
NAME = re.compile(r"(?:keyboards/[a-z0-9_-]+\.lua|patterns/[a-z0-9_-]+\.png)\Z")


def permitted(path):
    return path in FIXED or bool(NAME.fullmatch(path))


def paths_from_card(root):
    paths = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and permitted(p.relative_to(root).as_posix()))
    if not FIXED.issubset(paths) or len(paths) > MAX_FILES:
        raise ValueError("Incomplete or oversized firmware runtime")
    return paths


def create(root, version):
    if not VERSION.fullmatch(version):
        raise ValueError("Expected a numeric firmware version")
    paths = paths_from_card(root)
    files = []
    for path in paths:
        data = (root / path).read_bytes()
        files.append({"path": path, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    manifest = {"format": FORMAT, "device": DEVICE, "version": version, "files": files}
    validate(manifest, lambda path: (root / path).read_bytes())
    return manifest


def validate(manifest, read_file):
    if not isinstance(manifest, dict) or manifest.get("format") != FORMAT or manifest.get("device") != DEVICE or not isinstance(manifest.get("version"), str) or not VERSION.fullmatch(manifest["version"]):
        raise ValueError("Unsupported firmware manifest")
    files = manifest.get("files")
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES:
        raise ValueError("Invalid firmware file list")
    seen = set()
    total = 0
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "size", "sha256"}:
            raise ValueError("Invalid firmware file entry")
        path, size, digest = item["path"], item["size"], item["sha256"]
        if not isinstance(path, str) or not permitted(path) or path in seen:
            raise ValueError("Unsafe or duplicate firmware path")
        if type(size) is not int or not 0 < size <= MAX_FILE or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Invalid firmware file size or hash")
        seen.add(path)
        total += size
        if total > MAX_TOTAL:
            raise ValueError("Firmware runtime is too large")
        data = read_file(path)
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"Firmware file failed verification: {path}")
    if not FIXED.issubset(seen):
        raise ValueError("Firmware runtime is incomplete")
    if read_file("firmware-version") != (manifest["version"] + "\n").encode():
        raise ValueError("Firmware version does not match manifest")
    return manifest


def from_zip(archive, expected_version):
    names = {}
    for info in archive.infolist():
        name = info.filename.removeprefix("./")
        if name in names:
            raise ValueError("Duplicate ZIP path")
        names[name] = info
    if "firmware-update.json" not in names or names["firmware-update.json"].file_size > 16384:
        raise ValueError("Firmware ZIP has no update manifest")
    manifest = json.loads(archive.read(names["firmware-update.json"]))
    if not isinstance(manifest, dict):
        raise ValueError("Invalid firmware update manifest")
    if manifest.get("version") != expected_version:
        raise ValueError("Firmware release version does not match its package")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) > MAX_FILES:
        raise ValueError("Invalid firmware file list")
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not permitted(item["path"]):
            raise ValueError("Unsafe firmware path")
        info = names.get(item["path"])
        if info is None or info.file_size > MAX_FILE:
            raise ValueError("Firmware file is missing or too large")
    return validate(manifest, lambda path: archive.read(names[path]) if path in names else b"")


def wire_manifest(manifest):
    return "".join(f"{item['path']} {item['size']} {item['sha256']}\n" for item in manifest["files"]).encode("ascii")
