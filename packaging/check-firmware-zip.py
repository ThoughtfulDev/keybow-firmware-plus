"""Check that the SD card ZIP is complete and has the expected root layout."""

import hashlib
import os
import struct
import sys
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "editor"))
from keybow_editor.firmware_manifest import from_zip  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT / "build/keybow-sdcard.zip"
REQUIRED = {
    "bootcode.bin",
    "start.elf",
    "fixup.dat",
    "kernel.img",
    "initrd",
    "keybow",
    "keybow.lua",
    "keys.lua",
    "profiles/active",
    "profiles/layer-loader.lua",
    "LICENCE.broadcom",
    "COPYING.linux",
    "THIRD_PARTY_NOTICES.md",
    "firmware-version",
    "firmware-update.json",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


with ZipFile(ZIP) as archive:
    entries = {}
    for info in archive.infolist():
        name = info.filename
        while name.startswith("./"):
            name = name[2:]
        if not name or info.is_dir():
            continue
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or name in entries:
            sys.exit(f"Unsafe or duplicate ZIP entry: {info.filename}")
        entries[name] = info

    missing = REQUIRED - entries.keys()
    if missing:
        sys.exit(f"Missing SD card files: {', '.join(sorted(missing))}")
    if archive.testzip() is not None:
        sys.exit("SD card ZIP failed its CRC check")

    for name, expected in (("kernel.img", ROOT / "sdcard/kernel.img"),
                           ("initrd", ROOT / "build/initrd")):
        if digest(archive.read(entries[name])) != digest(expected.read_bytes()):
            sys.exit(f"{name} differs from the expected build file")

    executable = archive.read(entries["keybow"])
    if digest(executable) != digest((ROOT / "build/keybow").read_bytes()):
        sys.exit("ZIP does not contain the newly built keybow executable")
    if executable[:4] != b"\x7fELF" or struct.unpack_from("<H", executable, 18)[0] != 40:
        sys.exit("keybow is not an ARM ELF executable")
    version = archive.read(entries["firmware-version"]).decode().strip()
    expected = os.environ.get("KEYBOW_FIRMWARE_VERSION", "").removeprefix("firmware-v")
    if expected and version != expected:
        sys.exit("Firmware version does not match the release tag")
    from_zip(archive, version)
    if archive.read(entries["firmware-update.json"]) != (ROOT / "build/firmware-update.json").read_bytes():
        sys.exit("Published update manifest differs from the ZIP manifest")

print(f"Verified {ZIP.name}: {len(entries)} files, ARM executable, update manifest and initrd")
