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
docker rm "$container_id" >/dev/null
container_id=

cp -R sdcard/. "$staging_dir/"
cp build/keybow "$staging_dir/keybow"
rm -f build/keybow-sdcard.zip
(cd "$staging_dir" && zip -q -r -X "$repo_dir/build/keybow-sdcard.zip" .)

printf 'Firmware: %s\nSD card archive: %s\n' \
    "$repo_dir/build/keybow" "$repo_dir/build/keybow-sdcard.zip"
