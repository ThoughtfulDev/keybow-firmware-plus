# Install Keybow Editor

[← Keybow Firmware Plus](../README.md) · [Firmware update](firmware-update.md) · [Usage](usage.md) · [Building](building.md)

Install the [one-time SD card firmware update](firmware-update.md) before saving profiles from the editor. The editor runs locally on your computer and communicates with Keybow through USB serial. The packages include Python and the editor code; you do not need to install Python to use them.

This project currently provides local build scripts, not hosted releases. Build a package on its target operating system using the [build guide](building.md), or use a package built from this repository on that system.

## macOS

Open `keybow-editor-macos-arm64.dmg` on Apple Silicon or `keybow-editor-macos-x86_64.dmg` on an Intel Mac. Drag **Keybow Editor.app** onto the **Applications** shortcut, eject the disk image, and open the app from Applications. The local builds are unsigned, so macOS may ask you to approve opening the app.

## Windows 10/11 x64

Extract `keybow-editor-windows-x64.zip` and run `KeybowEditor.exe` inside the extracted folder. Keep the folder together. The app needs [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) and explains how to install it if missing. The local build is unsigned, so Windows may ask you to approve opening it.

## Ubuntu 22.04/24.04 x64

Install the package and open **Keybow Editor** from the app menu:

```sh
sudo apt install ./keybow-editor-ubuntu-x64.deb
```

You can also run `keybow-editor` from a terminal. The package declares its GTK, WebKitGTK, and Python GI runtime dependencies. If Linux denies access to Keybow's serial port, add your user to the `dialout` group, then sign out and back in:

```sh
sudo usermod -aG dialout "$USER"
```

## Connect Keybow

Use a USB **data** cable. The editor scans likely USB serial ports and confirms the device with a ping. If it does not find Keybow, choose its port in **USB serial port** and click **Refresh ports**. Close any serial terminal or other editor instance holding that port open. For development, `KEYBOW_PORT` selects a port explicitly.

Editor app updates only replace the app on your computer. They do not alter profiles on Keybow. Firmware executable updates and the first USB editor upgrade use the [SD card procedure](firmware-update.md).
