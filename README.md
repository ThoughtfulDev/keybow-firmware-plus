![Keybow Firmware Plus banner with a lit 12-key Keybow](docs/images/keybow-banner.webp)

---

**Keybow Firmware Plus** is a fork of [Pimoroni's original Keybow firmware](https://github.com/pimoroni/keybow-firmware). It adds a desktop editor and USB profile updates for the **12-key Keybow**, so you can change keys, layers, and lighting without removing the SD card after the initial firmware update. These additions have not been verified on Keybow MINI.

- Edit named profiles on macOS, Windows, or Ubuntu; profiles are stored on Keybow's SD card.
- Assign keyboard shortcuts, media controls, or no action to each key.
- Use up to four layers with toggle, hold, or timed switching.
- Set per-key colors or use the existing lighting patterns.
- Choose US or German keyboard layouts for macOS, Windows, and Linux.

## Get started

1. [Install the one-time Keybow firmware update](docs/firmware-update.md).
2. [Install the desktop editor](docs/installation.md).
3. [Edit profiles and lighting](docs/usage.md).

For local firmware and desktop package builds, see [Building](docs/building.md).

<details>
<summary>See editor screenshots</summary>

### Profile and device view

![Keybow Editor with a demo profile and its 12-key device view](docs/images/editor-overview.png)

### Per-key color controls

![Keybow Editor showing the color wheel, brightness, hex, and RGB controls](docs/images/editor-color.png)

### Media layer

![Keybow Editor showing a second layer with media controls and a reserved return key](docs/images/editor-layers.png)

Screenshots use a simulated demo profile; no connected Keybow profile was changed.

</details>

The original hardware and software guides remain available on [Pimoroni's Keybow learning portal](https://learn.pimoroni.com/product/keybow). See [LICENSE](LICENSE) for component licensing and [third-party notices](THIRD_PARTY_NOTICES.md) for bundled dependencies and firmware provenance.
