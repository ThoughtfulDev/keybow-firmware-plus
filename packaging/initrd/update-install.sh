#!/bin/sh
# All update paths are created from the device's fixed allowlist.
boot=${KEYBOW_BOOT_ROOT:-/boot}
root="$boot/.keybow-update"
manifest="$root/manifest"

valid_path() {
    case "$1" in
        *..*|*//*|/*) return 1 ;;
        keybow|keys.lua|keybow.lua|default.png|firmware-version|keyboards/*.lua|patterns/*.png) return 0 ;;
        *) return 1 ;;
    esac
}

restore() {
    while read -r rel size digest; do
        valid_path "$rel" || continue
        if [ -f "$root/previous/$rel" ]; then
            cp "$root/previous/$rel" "$boot/$rel.rollback" && mv -f "$boot/$rel.rollback" "$boot/$rel"
        else
            rm -f "$boot/$rel"
        fi
    done < "$manifest"
    sync
    rm -f "$root/pending" "$root/ready"
    echo 'Firmware startup failed; previous runtime restored' > "$root/failed"
    sync
}

if [ ! -f "$manifest" ]; then
    echo 'Firmware update manifest missing' > "$root/failed"
    rm -f "$root/pending"
    exit 0
fi

# Validate the entire staged runtime before changing any live file.
while read -r rel size digest; do
    if ! valid_path "$rel" || [ ! -f "$root/next/$rel" ] ||
       [ "$(wc -c < "$root/next/$rel")" -ne "$size" ] ||
       [ "$(sha256sum "$root/next/$rel" | cut -d ' ' -f 1)" != "$digest" ]; then
        restore
        exit 0
    fi
done < "$manifest"

while read -r rel size digest; do
    if ! cp "$root/next/$rel" "$boot/$rel.update" || ! mv -f "$boot/$rel.update" "$boot/$rel"; then
        restore
        exit 0
    fi
done < "$manifest"
sync
