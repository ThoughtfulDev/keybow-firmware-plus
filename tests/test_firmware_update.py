import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "editor"))
from keybow_editor import firmware_manifest, firmware_update


def sample(root):
    content = {"keybow": b"new binary", "keys.lua": b"new keys", "keybow.lua": b"new library",
               "default.png": b"new picture", "firmware-version": b"1.2.3\n",
               "patterns/rainbow.png": b"new lights"}
    for name, data in content.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return content, firmware_manifest.create(root, "1.2.3")


class FirmwareUpdateTests(unittest.TestCase):
    def test_manifest_rejects_tampering_and_profile_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content, manifest = sample(root)
            firmware_manifest.validate(manifest, lambda path: content[path])
            changed = dict(content, keybow=b"tampered")
            with self.assertRaisesRegex(ValueError, "verification"):
                firmware_manifest.validate(manifest, lambda path: changed[path])
            bad = json.loads(json.dumps(manifest))
            bad["files"][0]["path"] = "profiles/active"
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                firmware_manifest.validate(bad, lambda path: content.get(path, b""))
            with io.BytesIO() as buffer:
                with ZipFile(buffer, "w") as archive:
                    for name, data in content.items():
                        archive.writestr(name, data)
                    archive.writestr("firmware-update.json", json.dumps(manifest))
                with ZipFile(io.BytesIO(buffer.getvalue())) as archive:
                    self.assertEqual(firmware_manifest.from_zip(archive, "1.2.3"), manifest)
                    with self.assertRaisesRegex(ValueError, "version"):
                        firmware_manifest.from_zip(archive, "1.2.4")

    def test_latest_firmware_release_selection(self):
        def release(tag):
            return {"tag_name": tag, "draft": False, "prerelease": False,
                    "assets": [{"name": f"keybow-firmware-plus-{tag}-sdcard.zip",
                                "browser_download_url": f"https://github.com/ThoughtfulDev/keybow-firmware-plus/releases/download/{tag}/keybow-firmware-plus-{tag}-sdcard.zip",
                                "size": 1234},
                               {"name": f"keybow-firmware-plus-{tag}-update.json"}]}
        payload = json.dumps([release("firmware-v1.9.0"), release("v9.0.0"),
                              release("firmware-v1.10.0")]).encode()
        with patch.object(firmware_update, "get_url", return_value=payload):
            self.assertEqual(firmware_update.latest_release()["version"], "1.10.0")

    def test_c_device_transfer_and_boot_commit_or_rollback(self):
        if os.name != "posix" or not shutil.which("cc") or not shutil.which("sha256sum"):
            self.skipTest("POSIX C compiler and sha256sum required")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            device = root / "device"
            device.mkdir()
            content, manifest = sample(device / "new")
            for name in content:
                old = device / name
                old.parent.mkdir(parents=True, exist_ok=True)
                old.write_bytes(b"old " + name.encode())
            wire = firmware_manifest.wire_manifest(manifest)
            source = root / "manifest"
            source.write_bytes(wire)
            executable = root / "updater-test"
            subprocess.run(["cc", "-DKEYBOW_UPDATER_TEST", "-I", str(ROOT / "keybow"), str(ROOT / "tests/updater_device_test.c"),
                            str(ROOT / "keybow/updater.c"), "-o", str(executable)], check=True)
            subprocess.run([str(executable), str(source), str(device)], check=True)
            env = dict(os.environ, KEYBOW_BOOT_ROOT=str(device))
            subprocess.run(["sh", str(ROOT / "packaging/initrd/update-install.sh")], env=env, check=True)
            self.assertEqual((device / "keybow").read_bytes(), content["keybow"])
            (device / ".keybow-update/ready").write_text("ready\n")
            subprocess.run(["sh", str(ROOT / "packaging/initrd/update-watchdog.sh")], env=env, check=True)
            self.assertFalse((device / ".keybow-update/pending").exists())
            self.assertFalse((device / ".keybow-update/manifest").exists())
            self.assertEqual((device / "keybow").read_bytes(), content["keybow"])

            # A failed startup restores the previous runtime from durable backups.
            second = root / "rollback"
            second.mkdir()
            state = second / ".keybow-update"
            for name, data in content.items():
                (second / name).parent.mkdir(parents=True, exist_ok=True)
                (second / name).write_bytes(data)
                (state / "previous" / name).parent.mkdir(parents=True, exist_ok=True)
                (state / "previous" / name).write_bytes(b"old " + name.encode())
            state.mkdir(exist_ok=True)
            (state / "manifest").write_bytes(wire)
            (state / "pending").write_text("pending\n")
            env.update(KEYBOW_BOOT_ROOT=str(second), KEYBOW_WATCHDOG_TIMEOUT="0", KEYBOW_REBOOT_CMD="true")
            subprocess.run(["sh", str(ROOT / "packaging/initrd/update-watchdog.sh")], env=env, check=True)
            self.assertEqual((second / "keybow").read_bytes(), b"old keybow")
            self.assertTrue((state / "failed").exists())
            self.assertFalse((state / "pending").exists())

            # A damaged staged file is rejected before any new runtime file is installed.
            third = root / "damaged"
            third.mkdir()
            stage = third / ".keybow-update"
            for name, data in content.items():
                (third / name).parent.mkdir(parents=True, exist_ok=True)
                (third / name).write_bytes(b"old " + name.encode())
                (stage / "next" / name).parent.mkdir(parents=True, exist_ok=True)
                (stage / "next" / name).write_bytes(b"broken" if name == "keybow" else data)
                (stage / "previous" / name).parent.mkdir(parents=True, exist_ok=True)
                (stage / "previous" / name).write_bytes(b"old " + name.encode())
            (stage / "manifest").write_bytes(wire)
            (stage / "pending").write_text("pending\n")
            env["KEYBOW_BOOT_ROOT"] = str(third)
            subprocess.run(["sh", str(ROOT / "packaging/initrd/update-install.sh")], env=env, check=True)
            self.assertEqual((third / "keybow").read_bytes(), b"old keybow")
            self.assertTrue((stage / "failed").exists())

    def test_latest_release_and_profile_preserving_update(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content, manifest = sample(root / "package")
            buffer = io.BytesIO()
            with ZipFile(buffer, "w") as archive:
                for name, data in content.items():
                    archive.writestr(name, data)
                archive.writestr("firmware-update.json", json.dumps(manifest))
            release = {"tag": "firmware-v1.2.3", "version": "1.2.3", "url": "https://example.invalid/package.zip"}

            class Device:
                version = "1.0.0"
                active = "personal"
                files = {"personal": b"function setup() end", "another": b"function setup() end\n"}
                offsets = None

                def close(self):
                    pass

                def request(self, command, payload=b"", timeout=None):
                    if command == "update_info": return f"{self.version}\nidle".encode()
                    if command == "list": return (self.active + "\n" + "\n".join(self.files) + "\n").encode()
                    if command == "read": return self.files[payload.decode()]
                    if command == "write":
                        identifier, source = payload.split(b"\n", 1)
                        self.files[identifier.decode()] = source
                        return b""
                    if command == "activate": self.active = payload.decode(); return b""
                    if command == "update_begin":
                        self.offsets = [bytearray() for _ in manifest["files"]]
                        self.begin = payload
                        return b""
                    if command == "update_query":
                        for i, item in enumerate(manifest["files"]):
                            if len(self.offsets[i]) < item["size"]:
                                return bytes([i]) + struct.pack("<I", len(self.offsets[i]))
                        return bytes([len(self.offsets)]) + b"\0" * 4
                    if command == "update_chunk":
                        i, offset = payload[0], struct.unpack("<I", payload[1:5])[0]
                        assert offset == len(self.offsets[i])
                        self.offsets[i].extend(payload[5:])
                        return b""
                    if command == "update_verify":
                        for item, data in zip(manifest["files"], self.offsets):
                            assert hashlib.sha256(data).hexdigest() == item["sha256"]
                        return b""
                    if command == "update_apply": self.version = "1.2.3"; return b""
                    raise AssertionError(command)

            device = Device()
            progress = []
            with patch.object(firmware_update, "get_url", return_value=buffer.getvalue()), \
                 patch.object(firmware_update, "backup_root", return_value=root / "backups"), \
                 patch.object(firmware_update.time, "sleep", return_value=None):
                backup = firmware_update.install(device, release, lambda *args: progress.append(args))
            self.assertEqual(device.version, "1.2.3")
            self.assertEqual(device.active, "personal")
            self.assertEqual((Path(backup) / "profiles/personal.lua").read_bytes(), device.files["personal"])
            self.assertIn(b"keybow ", device.begin)
            self.assertEqual(progress[-1][0], "Restarting Keybow")


if __name__ == "__main__":
    unittest.main()
