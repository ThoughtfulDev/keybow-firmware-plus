# Coding guidelines

[← Keybow Firmware Plus](../README.md) · [Development setup](development.md) · [Build packages](building.md) · [Editor usage](usage.md)

Use this guide when changing the editor, device firmware, or packaging. Keep user-facing instructions in the [installation](installation.md), [usage](usage.md), and [firmware update](firmware-update.md) guides.

## Profiles and keys

- Treat the version 4 profile format as the current editor format. Keep loading older saved profiles through the existing upgrade path, and generate Lua that the device layer loader can run. Validate a profile and its 15,000-byte source limit before sending it.
- Keep the physical orientation used by the editor when the USB cutout faces away from the user: `12 09 06 03 / 11 08 05 02 / 10 07 04 01`. Test key-number or layer changes against that orientation.
- Keyboard layouts are stored per profile. Opening a profile on another OS must not silently change assignments; explicit layout changes translate supported keys across every layer and report keys that cannot be translated.
- Preserve the behavior of **Unassigned** as no action and of toggle return keys as reserved. Release held keys when switching layers or profiles.

## USB and firmware updates

- Keep host and device protocol changes in sync. Bound frames and file transfers, validate incoming paths and hashes, and handle interrupted transfers without applying incomplete data. Add tests for both normal and rejected requests.
- Firmware updates may replace only the runtime files allowed by the update manifest. Keep saved profiles and the active selection intact, and preserve the boot rollback path. Kernel, `initrd`, and boot-file changes still require an SD card package.
- The editor HTTP server is local to `127.0.0.1`. Keep state-changing requests restricted to its local origin, and make connection or SD card failures visible to the user.

## Before a release

- Run the [editor tests](development.md#run-checks). Build and inspect the relevant [desktop or firmware package](building.md); check that the SD card ZIP has its files at the archive root.
- Update end-user instructions when an installation or workflow changes. Keep build commands and implementation details in developer docs.
- Use a new, unused `vMAJOR.MINOR.PATCH` tag for the desktop app or `firmware-vMAJOR.MINOR.PATCH` for firmware. Verify the matching GitHub Actions run and release assets. Do not move a published tag to a different commit.
