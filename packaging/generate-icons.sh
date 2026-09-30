#!/bin/sh
# Regenerate committed platform icons after changing editor/assets/keybow-icon-source.png.
# Regular desktop builds use the committed files and do not run this script.
set -eu
cd "$(dirname "$0")/.."
command -v magick >/dev/null || { echo 'ImageMagick (magick) is required' >&2; exit 1; }
command -v iconutil >/dev/null || { echo 'Run icon generation on macOS' >&2; exit 1; }
command -v sips >/dev/null || { echo 'sips is required' >&2; exit 1; }
source=editor/assets/keybow-icon-source.png
output=editor/assets/keybow-icon
[ -f "$source" ] || { echo "Missing $source" >&2; exit 1; }
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
iconset="$tmp/keybow-icon.iconset"
mkdir "$iconset"
magick "$source" -resize 1024x1024 -strip "$output.png"
for size in 16 32 128 256 512; do
  sips -z "$size" "$size" "$output.png" --out "$iconset/icon_${size}x${size}.png" >/dev/null
  double=$((size * 2))
  sips -z "$double" "$double" "$output.png" --out "$iconset/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil --convert icns --output "$output.icns" "$iconset"
magick "$output.png" -define icon:auto-resize=256,128,64,48,32,16 "$output.ico"
sips -z 256 256 "$output.png" --out "$output-256.png" >/dev/null
echo "Generated $output.png, $output-256.png, $output.icns, and $output.ico"
