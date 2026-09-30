# Install Keybow Editor

[← Keybow Firmware Plus](../README.md) · [Firmware installation](firmware-update.md) · [Editor usage](usage.md)

Start with the [one-time SD card firmware installation](firmware-update.md) for the 12-key Keybow. Then download the desktop app from the [`v0.0.1` Keybow Editor release](https://github.com/ThoughtfulDev/keybow-firmware-plus/releases/tag/v0.0.1). Editor releases use `v` tags; firmware releases use `firmware-v` tags. The app packages include Python, so you do not need to install it.

Choose the file for your computer below. These packages are unsigned, so your operating system may ask you to approve opening them.

## macOS

Download `keybow-editor-macos-arm64.dmg` for an Apple Silicon Mac or `keybow-editor-macos-x86_64.dmg` for an Intel Mac. Open the DMG, drag **Keybow Editor.app** onto the **Applications** shortcut, and eject the disk image. Before opening the unsigned app, run this in Terminal to remove its quarantine attribute:

```sh
xattr -dr com.apple.quarantine "/Applications/Keybow Editor.app"
```

Open **Keybow Editor** from Applications. Repeat the command after installing a newer DMG. If Terminal reports a permission error, run the same command with `sudo`.

## Windows 10/11 x64

Download `keybow-editor-windows-x64.zip`, extract it, and run `KeybowEditor.exe` inside the extracted `KeybowEditor` folder. Keep that folder together; the executable uses the files beside it. The app needs [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) and explains how to install it if missing.

## Ubuntu 22.04/24.04 x64

Download `keybow-editor-ubuntu-x64.deb`. From the download folder, install it and open **Keybow Editor** from the app menu:

```sh
sudo apt install ./keybow-editor-ubuntu-x64.deb
```

You can also run `keybow-editor` from a terminal. The package declares its GTK, WebKitGTK, and Python GI runtime dependencies. If Linux denies access to Keybow's serial port, add your user to the `dialout` group, then sign out and back in:

```sh
sudo usermod -aG dialout "$USER"
```

## Connect Keybow

Use a USB **data** cable. The editor scans likely USB serial ports and confirms the device with a ping. If it does not find Keybow, choose its port in **USB serial port** and click **Refresh ports**. Close any serial terminal or other editor instance holding that port open.

To update the desktop app later, download and install a newer `v…` release the same way. App updates do not change profiles stored on Keybow. After the initial SD card installation, use the editor's **Firmware** section for compatible runtime firmware updates; see the [firmware guide](firmware-update.md).
