# Use Keybow Editor

[← Keybow Firmware Plus](../README.md) · [Installation](installation.md) · [Firmware update](firmware-update.md)

Connect the updated 12-key Keybow with a USB data cable and open the [desktop editor](installation.md). The profile list comes from Keybow's SD card each time the editor connects, so the same saved profiles appear when you use another computer with the editor installed.

## Edit and save profiles

Choose a profile in the sidebar, or click **Add**. Click a key on the device view to assign a keyboard key and modifiers, a media control, a layer switch, or **Unassigned**. An unassigned key sends nothing. Use **Rename profile** to change its displayed name; its file ID stays the same.

Choose **Per-key colors** to set a key with the color wheel, brightness slider, hex code, or RGB fields. Choose **Pattern** to use an existing PNG lighting pattern. Click **Save changes** to store the profile on Keybow. If it is the active profile, saving applies the changes immediately. Use **Make active** to switch to another saved profile.

Profiles live on Keybow's SD card, not in the desktop app. You can open the editor on another supported computer and read the same profiles from the connected device.

## Layers

Each profile has a base layer and can have up to three more named layers. Add a layer, then assign a key to **Switch layer**. Choose **Toggle** to stay on the target layer until pressing the same physical key again, **While held** to return on release, or **Return after a delay** for a timed return of 1–3600 seconds. A toggle's target-layer key is reserved for return and cannot run another action. A later layer switch cancels an earlier timer. Keybow starts on the base layer after reconnecting.

## Keyboard layouts

Choose **US English**, **German (macOS)**, **German (Windows)**, or **German (Linux)** for each profile. Match your computer's active input source to the selected profile layout; the editor does not change the operating system's input source. Opening a saved profile on another operating system does not translate its keys automatically. An explicit layout change translates supported assignments across every layer and reports unsupported ones before saving. Mac Command and Windows/Linux GUI shortcuts may need manual reassignment when switching between German targets.

## Connection and save errors

If automatic detection misses Keybow, use **USB serial port** and **Refresh ports**. Close other software using the port. On Linux, see the [serial permission step](installation.md#ubuntu-22042404-x64).

If saving reports an SD card write error, disconnect and reconnect Keybow's USB cable, wait for its keys and lights to return, then retry. The previous profile remains readable when a write fails. If the error continues, back up and check the SD card for filesystem errors; the editor cannot repair it over USB.
