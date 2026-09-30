# Build firmware and desktop packages

[← Keybow Firmware Plus](../README.md) · [Development setup](development.md) · [Coding guidelines](coding-guidelines.md)

These instructions are for contributors building packages from source. End users should download the [firmware](firmware-update.md) and [desktop app](installation.md) from GitHub Releases. Run commands from the repository root; outputs go to `build/`.

## Keybow SD card package with Docker

Install Docker and `zip`, then run:

```sh
./build-docker.sh
```

The script builds the bundled C sources and dependencies with an ARMv6-compatible cross toolchain. It writes `build/keybow`, a repacked `build/initrd`, and the complete `build/keybow-sdcard.zip`. The ZIP includes the `sdcard/` contents at its root, including boot files, Lua layouts, and patterns. Docker adds the update recovery scripts to the bundled `initrd`; it does not rebuild the kernel or Raspberry Pi boot binaries. It also writes a versioned, checksummed runtime manifest for USB updates. Local builds default to version `0.0.0`; set `KEYBOW_FIRMWARE_VERSION=0.0.1` for a versioned local package. Follow the [firmware update guide](firmware-update.md) for the one-time card upgrade and later USB updates.

Pushing an unused `firmware-vMAJOR.MINOR.PATCH` tag runs the [firmware release workflow](../.github/workflows/firmware-release.yml) on an Ubuntu runner. It builds and checks the SD card ZIP, then attaches a versioned ZIP and its `-update.json` manifest to a separate firmware release. The editor recognizes releases containing both assets. For example, after the commit to release is on the remote branch and `firmware-v0.0.2` is available:

```sh
git tag -a firmware-v0.0.2 -m 'Keybow firmware v0.0.2'
git push origin firmware-v0.0.2
```

Firmware tags use `firmware-vMAJOR.MINOR.PATCH`; desktop editor tags use `vMAJOR.MINOR.PATCH` and run a separate workflow.

## Desktop editor packages

Build on each target operating system and architecture. Each script runs the Python editor tests and needs internet access once to install pinned build dependencies. [PyInstaller builds on the target OS](https://pyinstaller.org/en/latest/usage.html). Packages include Python and app code; users do not install Python separately.

Pushing an unused `vMAJOR.MINOR.PATCH` tag runs the [desktop release workflow](../.github/workflows/desktop-release.yml). It builds both Mac DMGs, a Windows x64 ZIP, and an Ubuntu 24.04 x64 DEB, then attaches all four to a desktop release after every build succeeds. For example, after the commit to release is on the remote branch and `v0.0.2` is available:

```sh
git tag -a v0.0.2 -m 'Keybow Editor v0.0.2'
git push origin v0.0.2
```

Tags must use `vMAJOR.MINOR.PATCH`. The Ubuntu DEB version is derived from the tag without `v`. The workflow uses GitHub's token and does not require a locally authenticated `gh` CLI. These desktop packages are unsigned; the workflow does not build or publish the SD card firmware ZIP. The local scripts below remain available.

### macOS Apple Silicon or Intel

Install Python 3.12 and Xcode command line tools, then run on the Mac matching the architecture you want:

```sh
./packaging/build-macos.sh
```

The output is a compressed, unsigned `build/keybow-editor-macos-arm64.dmg` or `build/keybow-editor-macos-x86_64.dmg` with the app and an Applications shortcut. The Mac build produces a DMG, not a ZIP.

### Windows 10/11 x64

With Python 3.12 and PowerShell, run:

```powershell
.\packaging\build-windows.ps1
```

The output is `build/keybow-editor-windows-x64.zip`.

### Ubuntu 22.04/24.04 x64

Install the build dependencies and run:

```sh
sudo apt install python3-venv python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1
./packaging/build-ubuntu.sh
```

The output is `build/keybow-editor-ubuntu-x64.deb`. The package version defaults to `1.0.0` for a local build; set `KEYBOW_VERSION=0.0.2` before the script to assign another version.

The app icon source and converted macOS, Windows, and Ubuntu assets are in `editor/assets/`. Normal builds need no image conversion tools. To regenerate them after changing the source icon, run `./packaging/generate-icons.sh` on a Mac with ImageMagick installed.

For the browser development server and test command, see [Development setup](development.md).
