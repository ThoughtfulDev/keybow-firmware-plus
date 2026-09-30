"""Check that the SD card ZIP is complete and has the expected root layout."""

import hashlib
import struct
import sys
from pathlib import Path, PurePosixPath
from zipfile import ZipFile


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

    for name in ("kernel.img", "initrd"):
        if digest(archive.read(entries[name])) != digest((ROOT / "sdcard" / name).read_bytes()):
            sys.exit(f"{name} differs from the tracked SD card file")

    executable = archive.read(entries["keybow"])
    if digest(executable) != digest((ROOT / "build/keybow").read_bytes()):
        sys.exit("ZIP does not contain the newly built keybow executable")
    if executable[:4] != b"\x7fELF" or struct.unpack_from("<H", executable, 18)[0] != 40:
        sys.exit("keybow is not an ARM ELF executable")

print(f"Verified {ZIP.name}: {len(entries)} files, ARM executable, kernel and initrd")
