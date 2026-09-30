#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
arch=$(uname -m)
case "$arch" in arm64|x86_64) ;; *) echo "Build on an Apple Silicon or Intel Mac" >&2; exit 1;; esac
python=${PYTHON:-python3.12}
venv="build/editor-venv-$arch"
"$python" -m venv "$venv"
"$venv/bin/python" -m pip install -r editor/requirements-desktop.txt
"$venv/bin/python" -m unittest discover -s tests -p 'test_*.py'
"$venv/bin/python" -m PyInstaller --noconfirm --clean --windowed --onedir \
  --osx-bundle-identifier com.keybow.editor \
  --icon "$(pwd)/editor/assets/keybow-icon.icns" \
  --name 'Keybow Editor' --distpath "build/editor-dist-$arch" \
  --workpath "build/editor-work-$arch" --specpath build \
  --paths editor --add-data "$(pwd)/editor/static:static" editor/launch.py
staging="build/editor-dmg-stage-$arch"
mkdir -p "$staging"
rm -rf "$staging/Keybow Editor.app" "$staging/Applications"
cp -R "build/editor-dist-$arch/Keybow Editor.app" "$staging/Keybow Editor.app"
mkdir -p "$staging/Keybow Editor.app/Contents/Resources"
cp THIRD_PARTY_NOTICES.md "$staging/Keybow Editor.app/Contents/Resources/ThirdPartyNotices.md"
cp editor/LICENSE "$staging/Keybow Editor.app/Contents/Resources/KeybowEditorLicense.txt"
python_license=$("$venv/bin/python" packaging/python-license-path.py)
cp "$python_license" "$staging/Keybow Editor.app/Contents/Resources/PythonLicense.txt"
ln -s /Applications "$staging/Applications"
image="build/keybow-editor-macos-$arch.dmg"
hdiutil create -quiet -ov -format UDZO -imagekey zlib-level=9 \
  -volname 'Keybow Editor' -srcfolder "$staging" "$image"
hdiutil verify -quiet "$image"
rm -f "build/keybow-editor-macos-$arch.zip"
echo "$image"
