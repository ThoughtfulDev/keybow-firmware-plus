#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
[ "$(uname -s)" = Linux ] && [ "$(uname -m)" = x86_64 ] || { echo 'Build on Ubuntu x64' >&2; exit 1; }
. /etc/os-release
[ "$ID" = ubuntu ] && { [ "$VERSION_ID" = 22.04 ] || [ "$VERSION_ID" = 24.04 ]; } || { echo 'Use Ubuntu 22.04 or 24.04' >&2; exit 1; }
gtk_package=libgtk-3-0
[ "$VERSION_ID" = 24.04 ] && gtk_package=libgtk-3-0t64
python=${PYTHON:-python3}
venv=build/editor-venv-linux
"$python" -m venv --system-site-packages "$venv"
"$venv/bin/python" -m pip install -r editor/requirements-desktop.txt
"$venv/bin/python" -m unittest discover -s tests -p test_editor.py
"$venv/bin/python" -m PyInstaller --noconfirm --clean --windowed --onedir --collect-all webview \
  --name keybow-editor --distpath build/editor-dist-linux \
  --workpath build/editor-work-linux --specpath build \
  --paths editor --add-data "$(pwd)/editor/static:static" --hidden-import webview.platforms.gtk editor/launch.py
pkg=build/keybow-editor-deb
mkdir -p "$pkg/DEBIAN" "$pkg/opt/keybow-editor" "$pkg/usr/bin" "$pkg/usr/share/applications" \
  "$pkg/usr/share/doc/keybow-editor" \
  "$pkg/usr/share/icons/hicolor/256x256/apps"
cp -R build/editor-dist-linux/keybow-editor/. "$pkg/opt/keybow-editor/"
install -m 644 THIRD_PARTY_NOTICES.md "$pkg/usr/share/doc/keybow-editor/THIRD_PARTY_NOTICES.md"
install -m 644 editor/LICENSE "$pkg/usr/share/doc/keybow-editor/KeybowEditorLicense.txt"
python_prefix=$("$venv/bin/python" -c 'import sys; print(sys.base_prefix)')
install -m 644 "$python_prefix/LICENSE" "$pkg/usr/share/doc/keybow-editor/PythonLicense.txt"
cat > "$pkg/DEBIAN/control" <<EOF
Package: keybow-editor
Version: 1.0.0
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Local build <local@localhost>
Depends: $gtk_package, gir1.2-gtk-3.0, gir1.2-webkit2-4.1, python3-gi, python3-gi-cairo
Description: Local visual editor for Keybow USB profiles
EOF
cat > "$pkg/usr/bin/keybow-editor" <<'EOF'
#!/bin/sh
exec /opt/keybow-editor/keybow-editor "$@"
EOF
chmod 755 "$pkg/usr/bin/keybow-editor"
install -m 644 editor/assets/keybow-icon-256.png \
  "$pkg/usr/share/icons/hicolor/256x256/apps/keybow-editor.png"
cat > "$pkg/usr/share/applications/keybow-editor.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Keybow Editor
Exec=keybow-editor
Icon=keybow-editor
Categories=Utility;
EOF
dpkg-deb --build --root-owner-group "$pkg" build/keybow-editor-ubuntu-x64.deb
echo build/keybow-editor-ubuntu-x64.deb
