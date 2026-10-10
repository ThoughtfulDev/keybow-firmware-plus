# Coding guidelines

[← Keybow Firmware Plus](../README.md) · [Development setup](development.md) · [Build packages](building.md) · [Editor usage](usage.md)

Use this guide when changing the editor, device firmware, or packaging. Keep user-facing instructions in the [installation](installation.md), [usage](usage.md), and [firmware update](firmware-update.md) guides.

## Profiles and keys

- Treat the version 5 profile format as the current editor format. Keep loading older saved profiles through the existing upgrade path, and generate Lua that the device layer loader can run. Validate a profile and its 15,000-byte source limit before sending it.
- Keep the physical orientation used by the editor when the USB cutout faces away from the user: `12 09 06 03 / 11 08 05 02 / 10 07 04 01`. Test key-number or layer changes against that orientation.
- Keyboard layouts are stored per profile. Opening a profile on another OS must not silently change assignments; explicit layout changes translate supported keys across every layer and report keys that cannot be translated.
- Preserve the behavior of **Unassigned** as no action and of toggle return keys as reserved. Release held keys when switching layers or profiles.

## Text and macro sequences

- `text` actions store literal text. `macro` actions store `steps`: recorded `event` entries (`device`, `usage`, `pressed`), `delay` entries (`ms`), or complete `keyboard`, `media`, and `text` actions. Validate balanced events, character support, 512-character blocks, 256 authored events, 2,048 expanded events, 120-second duration, and the generated source limit.
- Compile deterministic HID events in Python. Lua runtime table version 4 carries compact arrays: `{device, usage, state}` where devices are keyboard=0, modifier=1, media=2 and state is 0/1; a numeric entry is a delay in milliseconds. Profiles without sequences retain runtime table version 3. Keep loading saved profile formats 1–4.
- Advance at most one HID transition per tick, never sleep during playback. Cancel sequences and release generated keys before switching layers or profiles and while firmware staging is active. Keep recording inside a focused field and clean up on focus loss. Test with a fake clock and mocked HID setters.
- Protocol command 14 is a read-only capability query, returning `sequences-v1` when the installed loader supports sequences. Reject sequence saves and activation on unsupported devices; do not infer support from a version number. `/api/status` exposes `sequencesReady`; `/api/validate` checks profile compilation and reports `sourceBytes` without writing to Keybow.

## USB and firmware updates

- Keep host and device protocol changes in sync. Bound frames and file transfers, validate incoming paths and hashes, and handle interrupted transfers without applying incomplete data. Add tests for both normal and rejected requests.
- Firmware updates may replace only the runtime files allowed by the update manifest. Keep saved profiles and the active selection intact, and preserve the boot rollback path. Kernel, `initrd`, and boot-file changes still require an SD card package.
- The editor HTTP server is local to `127.0.0.2`. Keep state-changing requests restricted to its local origin, and make connection or SD card failures visible to the user.

## Before a release

- Run the [editor tests](development.md#run-checks). Build and inspect the relevant [desktop or firmware package](building.md); check that the SD card ZIP has its files at the archive root.
- Update end-user instructions when an installation or workflow changes. Keep build commands and implementation details in developer docs.
- Use a new, unused `vMAJOR.MINOR.PATCH` tag for the desktop app or `firmware-vMAJOR.MINOR.PATCH` for firmware. Verify the matching GitHub Actions run and release assets. Do not move a published tag to a different commit.
