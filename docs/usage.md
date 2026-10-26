# Use Keybow Editor

[← Keybow Firmware Plus](../README.md) · [Installation](installation.md) · [Firmware update](firmware-update.md)

Connect the updated 12-key Keybow with a USB data cable and open the [desktop editor](installation.md). The profile list comes from Keybow's SD card each time the editor connects, so the same saved profiles appear when you use another computer with the editor installed.

## Edit and save profiles

Choose a profile in the sidebar, or click **Add**. Click a key on the device view to assign a keyboard key and modifiers, a media control, a layer switch, **Type text**, **Macro**, or **Unassigned**. An unassigned key sends nothing. Use **Rename profile** to change its displayed name; its file ID stays the same.

Choose **Per-key colors** to set a key with the color wheel, brightness slider, hex code, or RGB fields. Choose **Pattern** to use an existing PNG lighting pattern. Click **Save changes** to store the profile on Keybow. If it is the active profile, saving applies the changes immediately. Use **Make active** to switch to another saved profile.

Profiles live on Keybow's SD card, not in the desktop app. You can open the editor on another supported computer and read the same profiles from the connected device.

## Rotate the device view

Click **Rotate view** beside **Your Keybow** to turn the illustration clockwise in 90° steps. Key numbers, assignments, colors, and the selected key stay attached to the same physical keys. The USB cutout and caption show the current orientation; labels remain upright.

The editor remembers this view on your computer across profiles and restarts, including when Keybow is disconnected. Rotation does not change profiles or send anything to Keybow, and requires no firmware update.

## Layers

Each profile has a base layer and can have up to three more named layers. Add a layer, then assign a key to **Switch layer**. Choose **Toggle** to stay on the target layer until pressing the same physical key again, **While held** to return on release, or **Return after a delay** for a timed return of 1–3600 seconds. A toggle's target-layer key is reserved for return and cannot run another action. A later layer switch cancels an earlier timer. Keybow starts on the base layer after reconnecting.

## Type text

Choose **Type text** and enter the text to send, including tabs and newlines. It runs once when you press the assigned key, even with the editor closed. Match your computer’s input source to the profile’s layout and turn Caps Lock off. US and German characters supported by that layout are accepted; unsupported characters, including emoji, are reported before saving. German literal circumflex, acute, and grave accents use a dead key followed by Space.

## Record and edit macros

Choose **Macro**, click **Record**, and type in the focused recorder field. It records key presses, releases, modifiers, overlaps, and the time between events. **Stop** replaces the event list with the recording; **Cancel** keeps the previous list. Escape stops recording. Leaving the field also stops and adds releases for keys still held. The recorder ignores keyboard auto-repeat. It records only inside the editor, so system-reserved shortcuts and IME input may need manual entry.

Review the event list before saving. You can change keys, press/release states, and delays, or delete events. **Add event** inserts a key shortcut, text, media control, delay, or a recorded press/release. To insert in the middle, use **Insert before** on that event. A shortcut or media action is a complete tap; individual recorded presses require matching releases. Release all recorded keys and modifiers before inserting text, shortcuts, or media actions.

A macro runs once per physical press and continues after releasing its trigger. Only one text/macro sequence runs at a time; additional triggers are ignored. Playback releases already-held Keybow actions and suppresses ordinary key actions until it finishes. Layer switches, profile activation, and firmware updates cancel playback and release its keys. Keys held during suppression must be released before they can run again. Keys held on another keyboard cannot be controlled by Keybow.

Each text block accepts up to 512 characters. Macros accept up to 256 authored events, expanded playback up to 2,048 events, and a duration up to 120 seconds. The generated profile must also fit the device’s 15,000-byte source limit, so large multi-layer profiles may reach that limit earlier. The recorder stops early enough to leave room for cleanup releases. Explicit layout changes translate supported recorded chords; incompatible overlaps are reported without changing the saved profile.

Text and macros require runtime firmware 0.0.2 or later. If their options are disabled, use the [firmware update instructions](firmware-update.md). A Keybow with the USB updater bootstrap can receive this runtime through the editor from a compatible firmware release. Saved profiles and active selection are preserved.

## Keyboard layouts

Choose **US English**, **German (macOS)**, **German (Windows)**, or **German (Linux)** for each profile. Match your computer's active input source to the selected profile layout; the editor does not change the operating system's input source. Opening a saved profile on another operating system does not translate its keys automatically. An explicit layout change translates supported assignments across every layer and reports unsupported ones before saving. Mac Command and Windows/Linux GUI shortcuts may need manual reassignment when switching between German targets.

## Connection and save errors

If automatic detection misses Keybow, use **USB serial port** and **Refresh ports**. Close other software using the port. On Linux, see the [serial permission step](installation.md#ubuntu-22042404-x64).

If saving reports an SD card write error, disconnect and reconnect Keybow's USB cable, wait for its keys and lights to return, then retry. The previous profile remains readable when a write fails. If the error continues, back up and check the SD card for filesystem errors; the editor cannot repair it over USB.
