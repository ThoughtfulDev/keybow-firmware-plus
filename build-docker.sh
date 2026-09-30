#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$repo_dir"

staging_dir=$(mktemp -d)
container_id=
cleanup() {
    if [ -n "$container_id" ]; then
        docker rm "$container_id" >/dev/null 2>&1 || true
    fi
    rm -rf "$staging_dir"
}
trap cleanup EXIT

docker build -t keybow-firmware .
container_id=$(docker create keybow-firmware /keybow)
mkdir -p build
docker cp "$container_id:/keybow" build/keybow
docker cp "$container_id:/initrd" build/initrd
docker rm "$container_id" >/dev/null
container_id=

cp -R sdcard/. "$staging_dir/"
cp THIRD_PARTY_NOTICES.md "$staging_dir/THIRD_PARTY_NOTICES.md"
cp build/keybow "$staging_dir/keybow"
cp build/initrd "$staging_dir/initrd"
version=${KEYBOW_FIRMWARE_VERSION:-0.0.0}
version=${version#firmware-v}
printf '%s\n' "$version" > "$staging_dir/firmware-version"
PYTHONPATH=editor python3 - "$staging_dir" "$version" <<'PY'
import json
import sys
from pathlib import Path
from keybow_editor.firmware_manifest import create

root = Path(sys.argv[1])
(root / "firmware-update.json").write_text(
    json.dumps(create(root, sys.argv[2]), separators=(",", ":")) + "\n"
)
PY
cp "$staging_dir/firmware-update.json" build/firmware-update.json
rm -f build/keybow-sdcard.zip
(cd "$staging_dir" && zip -q -r -X "$repo_dir/build/keybow-sdcard.zip" .)

printf 'Firmware: %s\nSD card archive: %s\n' \
    "$repo_dir/build/keybow" "$repo_dir/build/keybow-sdcard.zip"
