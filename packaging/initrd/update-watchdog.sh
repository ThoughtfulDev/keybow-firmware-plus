#!/bin/sh
boot=${KEYBOW_BOOT_ROOT:-/boot}
root="$boot/.keybow-update"
limit=${KEYBOW_WATCHDOG_TIMEOUT:-60}
elapsed=0
while [ "$elapsed" -lt "$limit" ]; do
    if [ -f "$root/ready" ]; then
        rm -f "$root/pending"
        sync
        while read -r rel size digest; do
            case "$rel" in
                *..*|*//*|/*) continue ;;
                keybow|keys.lua|keybow.lua|default.png|firmware-version|keyboards/*.lua|patterns/*.png) ;;
                *) continue ;;
            esac
            rm -f "$root/next/$rel" "$root/previous/$rel"
        done < "$root/manifest"
        rm -f "$root/manifest" "$root/ready"
        rm -f "$root/prepared" "$root/failed"
        sync
        exit 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
done

# The new process never reached its health marker. Keep the backups for recovery.
while read -r rel size digest; do
    case "$rel" in
        *..*|*//*|/*) continue ;;
        keybow|keys.lua|keybow.lua|default.png|firmware-version|keyboards/*.lua|patterns/*.png) ;;
        *) continue ;;
    esac
    if [ -f "$root/previous/$rel" ]; then
        cp "$root/previous/$rel" "$boot/$rel.rollback" && mv -f "$boot/$rel.rollback" "$boot/$rel"
    else
        rm -f "$boot/$rel"
    fi
done < "$root/manifest"
sync
rm -f "$root/pending" "$root/ready"
echo 'Firmware startup timed out; previous runtime restored' > "$root/failed"
sync
${KEYBOW_REBOOT_CMD:-reboot} -f
