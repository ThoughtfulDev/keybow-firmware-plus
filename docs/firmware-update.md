# Update Keybow firmware

[← Keybow Firmware Plus](../README.md) · [Installation](installation.md) · [Usage](usage.md) · [Building](building.md)

The USB editor and layer loader need a **one-time SD card update** on the 12-key Keybow. Back up the card before changing it. After this update, saving profiles and lighting uses USB; you do not need to remove the card for ordinary edits. A later firmware executable update still requires updating the card.

## Prepare the SD card package

From the repository root, build the firmware and complete SD card ZIP with Docker and `zip`:

```sh
./build-docker.sh
```

The result, `build/keybow-sdcard.zip`, contains the files that belong at the **root** of a FAT32 micro-SD card: boot files, `initrd`, Lua files, lighting patterns, and the newly built `keybow` executable. Do not copy only the `.bin` or `keybow` executable to a new card. The [build guide](building.md) explains what the Docker build does and does not rebuild.

## New card or original firmware

Format a micro-SD card as FAT32. Extract the **contents** of `build/keybow-sdcard.zip` directly to the card root, not into an extra folder. Eject the card, insert it in Keybow, then connect Keybow over USB. The original Pimoroni release ZIP is for the original firmware and does not include this fork's USB editor features.

## Card already running this fork's USB editor firmware

To add the current layer loader while keeping existing profiles, copy `sdcard/keys.lua` to the card root and `sdcard/profiles/layer-loader.lua` to its `profiles/` directory. Leave `profiles/active` and your saved profile files in place. Eject the card, insert it in Keybow, and reconnect USB.

For a later **executable** firmware update, back up your card and replace the relevant firmware files from a freshly built package while preserving your saved profiles. An editor application update alone does not require changing the card.

Keybow mounts its own SD card, so this project does not expose it as a writable USB drive to the computer.
