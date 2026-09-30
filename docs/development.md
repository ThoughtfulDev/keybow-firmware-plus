# Develop Keybow Firmware Plus

[← Keybow Firmware Plus](../README.md) · [Build packages](building.md) · [Coding guidelines](coding-guidelines.md) · [Editor usage](usage.md)

This guide runs the editor from source while you work on it. The [build guide](building.md) covers distributable desktop packages and the complete Keybow SD card ZIP. End users should use the [published releases](../README.md#install).

## Run the editor locally

Use Python 3.12. On macOS or Linux, create a virtual environment and start the browser-based development server:

```sh
python3.12 -m venv build/editor-dev-venv
build/editor-dev-venv/bin/python -m pip install -r editor/requirements-desktop.txt
PYTHON=build/editor-dev-venv/bin/python ./run-editor.sh
```

On Windows PowerShell:

```powershell
py -3.12 -m venv build\editor-dev-venv
.\build\editor-dev-venv\Scripts\python.exe -m pip install -r editor\requirements-desktop.txt
$env:PYTHONPATH = (Resolve-Path editor).Path
.\build\editor-dev-venv\Scripts\python.exe -m keybow_editor.server
```

The server binds to `127.0.0.1` and uses a real connected Keybow. Set `KEYBOW_PORT` to a serial port for development if automatic detection selects the wrong one. Saving in this editor writes to the device, so use a test profile when working on a connected Keybow.

## Run checks

On macOS or Linux:

```sh
PYTHONPATH=editor build/editor-dev-venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

On Windows PowerShell, set `PYTHONPATH` as above and run:

```powershell
.\build\editor-dev-venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py'
```

The suite covers profile validation, layout translation, serial framing, simulated editor requests, and firmware update behavior. Some tests need `node`, a C compiler, Lua, or POSIX tools and skip when those tools are unavailable. Run the relevant package build on each target OS before releasing; PyInstaller does not cross-compile desktop apps.

## Code map

- `editor/keybow_editor/` contains profile generation, layout translation, USB serial transport, the local HTTP server, and firmware release/update logic.
- `editor/static/` contains the desktop window's HTML, CSS, and JavaScript. The desktop launcher loads this UI in pywebview.
- `keybow/` contains the ARM executable and USB update receiver; `sdcard/` contains the files copied to the card, including the Lua layer loader.
- `packaging/initrd/` contains the boot update and rollback scripts. `packaging/` and the root `build-docker.sh` create release packages.
- `tests/` contains host-side and simulated device tests. Hardware checks still need a physical 12-key Keybow.

See [Coding guidelines](coding-guidelines.md) before changing the profile format, serial protocol, or updater.
