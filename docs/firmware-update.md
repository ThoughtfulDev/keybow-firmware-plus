# Install and update Keybow firmware

[← Keybow Firmware Plus](../README.md) · [Install the editor](installation.md) · [Editor usage](usage.md)

The 12-key Keybow needs one SD card installation to enable the desktop editor and later USB firmware updates. Afterward, you can edit profiles and install compatible runtime firmware releases while Keybow stays connected. Kernel, `initrd`, and Raspberry Pi boot-file updates still require the SD card.

## One-time SD card installation

1. Download `keybow-firmware-plus-firmware-v0.0.2-sdcard.zip` from the [`firmware-v0.0.2` GitHub release](https://github.com/ThoughtfulDev/keybow-firmware-plus/releases/tag/firmware-v0.0.2). Choose the **SD card ZIP**, not the companion `-update.json` file or a desktop app package. Back up every file on your current card before changing it.
2. Extract the ZIP to a folder on your computer. It includes `kernel.img`, `initrd`, and the other files that belong at the **root** of a FAT32 micro-SD card, not inside an extra folder.
3. Install the files using the case below, then eject the card, insert it in Keybow, and reconnect the USB cable. Open the editor; its **Firmware** section should show `0.0.2` for this package.

### Fresh card

Format the card as FAT32 and copy **all extracted contents** to its root. Copying only the `keybow` executable will not install the boot files or update receiver.

### Card already in use

Keep your backed-up card contents. From the extracted ZIP, replace `initrd`, `keybow`, `keys.lua`, `keybow.lua`, `default.png`, and `firmware-version` at the card root, along with the shipped files in `keyboards/` and `patterns/`. Add `profiles/layer-loader.lua` from the ZIP only if it is missing. **Do not replace `profiles/active` or your saved profile files.**

## Later updates through the editor

Connect Keybow with a USB data cable and open the desktop editor. In **Firmware**, click **Check updates**. The editor finds compatible `firmware-v…` releases on GitHub. Save or discard any unsaved profile changes, click **Update**, and keep Keybow connected until it restarts and the editor reports the result.

The editor verifies the release package, backs up all profiles and the active selection on your computer, sends the runtime files over USB, and checks them again after reconnecting. If a transfer stops before restart, reconnect Keybow and click **Update** again to resume. An app update from a `v…` release replaces only the desktop app; it does not update card firmware or erase profiles.

Profile backups are stored in `~/Library/Application Support/Keybow Editor/firmware-backups` on macOS, `%APPDATA%\Keybow Editor\firmware-backups` on Windows, and `${XDG_DATA_HOME:-~/.local/share}/keybow-editor/firmware-backups` on Linux. Keep the backup until you have tested your keys and lighting.

### Manual runtime update on an upgraded card

If your card already has the USB updater bootstrap, you can also install a runtime release manually. Unplug Keybow, back up the card, and extract the release SD card ZIP to a folder on your computer. Replace `keybow`, `keys.lua`, `keybow.lua`, `default.png`, and `firmware-version` at the card root, plus the shipped files inside `keyboards/` and `patterns/`. Leave the entire `profiles/` directory untouched, including `profiles/active`. Eject the card before reconnecting Keybow.

For this runtime update, keep the existing `initrd`, `kernel.img`, and Raspberry Pi boot files. Do not copy the entire ZIP over an existing card. The companion `-update.json` is for the USB updater and does not need to be copied to the card. Firmware 0.0.2 adds text/macros and ensures profile saves are flushed before reporting success.

## If an update fails

If the new runtime fails to start, the boot recovery hook attempts to restore the previous runtime. If Keybow does not reappear, remove the card and restore the card backup you made before the one-time installation. The editor's computer-side profile backup contains the saved `.lua` profiles and `backup.json` with their hashes and active ID.

A damaged card or boot image may still need manual SD card recovery. Keybow mounts its own card, so the editor does not expose it as a writable USB drive.
