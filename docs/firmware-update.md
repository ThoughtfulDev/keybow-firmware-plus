# Update Keybow firmware

[← Keybow Firmware Plus](../README.md) · [Installation](installation.md) · [Usage](usage.md) · [Building](building.md)

The USB editor and layer loader need a **one-time SD card update** on the 12-key Keybow. To enable firmware updates from the editor, install the newer SD card package containing the USB updater and boot recovery hook. Back up the card before changing it. After this upgrade, profile edits and later runtime firmware updates use USB.

## Prepare the SD card package

Download a tagged firmware ZIP from [GitHub Releases](https://github.com/ThoughtfulDev/keybow-firmware-plus/releases), or build the complete SD card ZIP locally with Docker and `zip` from the repository root:

```sh
./build-docker.sh
```

The downloaded firmware ZIP or local `build/keybow-sdcard.zip` contains the files that belong at the **root** of a FAT32 micro-SD card: boot files, `initrd`, Lua files, lighting patterns, and the newly built `keybow` executable. Do not copy only the `.bin` or `keybow` executable to a new card. The [build guide](building.md) explains how the Docker build repacks `initrd` with the recovery hook while retaining the bundled kernel and boot binaries.

## New card or original firmware

Format a micro-SD card as FAT32. Extract the **contents** of the firmware ZIP directly to the card root, not into an extra folder. Eject the card, insert it in Keybow, then connect Keybow over USB. The original Pimoroni release ZIP is for the original firmware and does not include this fork's USB editor features.

## Upgrade a card already running this fork

Copy the entire card to a folder on your computer first. Extract the new ZIP to a separate folder. From that folder, replace `initrd`, `keybow`, `keys.lua`, `keybow.lua`, `default.png`, and `firmware-version` at the card root, plus the shipped files in `keyboards/` and `patterns/`. Leave `profiles/` and `layouts/` untouched. Eject the card, insert it in Keybow, and reconnect USB. The editor's Firmware section should show the installed version. The recovery hook begins working after this manual upgrade.

If you still need the layer loader marker from an older update, copy `profiles/layer-loader.lua` from the ZIP only when it is missing on the card. Do not replace `profiles/active` or your saved profile files.

## Later updates through the editor

Connect Keybow and open the desktop editor. In **Firmware**, click **Check updates**. The editor reads the latest compatible `firmware-vX.Y.Z` release from GitHub. Save or discard any unsaved profile changes, then click **Update**. Keep Keybow connected until it restarts and the editor reports the result. The editor downloads and verifies the release ZIP, backs up every profile and the active selection on your computer, sends the runtime files over USB, and checks the profiles again after reconnecting. If a transfer is interrupted before restart, reconnect Keybow and click **Update** again to resume it. Kernel, `initrd`, and Raspberry Pi boot files still require an SD card update.

Backups are kept in `~/Library/Application Support/Keybow Editor/firmware-backups` on macOS, `%APPDATA%\Keybow Editor\firmware-backups` on Windows, and `${XDG_DATA_HOME:-~/.local/share}/keybow-editor/firmware-backups` on Linux. Each backup contains the original `.lua` profile files and `backup.json` with the active profile ID and hashes. Keep the backup until you have tested your keys and lighting.

If the new runtime fails to start, the boot hook restores the previous runtime and restarts Keybow. The editor will report the rollback after reconnecting. If Keybow does not reappear, remove the card and restore the card backup you made before the initial upgrade; the computer-side profile backup can then restore the saved layouts. A damaged card or boot image may still need manual SD card recovery.

An editor application update alone does not change the card firmware.

Keybow mounts its own SD card, so this project does not expose it as a writable USB drive to the computer.
