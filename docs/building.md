# Build firmware and desktop packages

[← Keybow Firmware Plus](../README.md) · [Installation](installation.md) · [Firmware update](firmware-update.md) · [Usage](usage.md)

Run these commands from the repository root. Outputs go to `build/`.

## Keybow SD card package with Docker

Install Docker and `zip`, then run:

```sh
./build-docker.sh
```

The script builds the bundled C sources and dependencies with an ARMv6-compatible cross toolchain. It writes `build/keybow` and the complete `build/keybow-sdcard.zip`. The ZIP includes the `sdcard/` contents at its root, including boot files, `initrd`, Lua layouts, and patterns. Docker compiles the `keybow` executable; it packages the existing boot files and `initrd` without rebuilding them. Follow the [firmware update guide](firmware-update.md) to put the result on a card.

## Desktop editor packages

Build on each target operating system and architecture. Each script runs the Python editor tests and needs internet access once to install pinned build dependencies. [PyInstaller builds on the target OS](https://pyinstaller.org/en/latest/usage.html). Packages include Python and app code; users do not install Python separately.

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

The output is `build/keybow-editor-ubuntu-x64.deb`.

The app icon source and converted macOS, Windows, and Ubuntu assets are in `editor/assets/`. Normal builds need no image conversion tools. To regenerate them after changing the source icon, run `./packaging/generate-icons.sh` on a Mac with ImageMagick installed.

## Browser development

Install `editor/requirements-desktop.txt` in a Python environment and run:

```sh
PYTHON=/path/to/venv/bin/python ./run-editor.sh
```

The development server listens on `127.0.0.1` only.

## Legacy native firmware build

A native build targets the **host** computer's architecture. Use the Docker build above for a Pi Zero firmware binary. The older manual build route installs a local toolchain and builds the bundled dependencies first:

```sh
sudo apt install build-essential autoconf libtool libconfig-dev libpng-dev libreadline-dev

cd bcm2835-1.68
autoreconf -f -i
mkdir build
./configure --prefix="$(pwd)/build"
make
make install
cd ..

cd libusbgx
autoreconf -i
mkdir build
./configure --prefix="$(pwd)/build"
make
make install
cd ..

cd lua-5.4.0
make linux
cd ..
```

The upstream [Pimoroni repository](https://github.com/pimoroni/keybow-firmware) provides historical build context for this route.
