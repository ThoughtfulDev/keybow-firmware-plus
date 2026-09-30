#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include <zlib.h>

#include "../keybow/profiles.h"

static unsigned char incoming[20000], outgoing[20000];
static size_t in_length, in_offset, out_length;
static size_t chunk_size = 256;
static int fail_reload;

int serial_read_bytes(void *target, size_t limit) {
    if (in_offset == in_length) return 0;
    size_t count = in_length - in_offset;
    if (count > limit) count = limit;
    if (count > chunk_size) count = chunk_size;
    memcpy(target, incoming + in_offset, count);
    in_offset += count;
    return (int)count;
}

int serial_write_all(const void *source, size_t length) {
    assert(out_length + length < sizeof(outgoing));
    memcpy(outgoing + out_length, source, length);
    out_length += length;
    return (int)length;
}

int luaCheckSource(const char *source, size_t length) {
    return !length || source[0] == '!';
}

int luaReload(void) {
    return fail_reload;
}

static uint32_t le32(const unsigned char *bytes) {
    return bytes[0] | ((uint32_t)bytes[1] << 8) |
           ((uint32_t)bytes[2] << 16) | ((uint32_t)bytes[3] << 24);
}

static void command(unsigned char op, const char *payload, int bad_crc) {
    size_t length = strlen(payload);
    in_length = 11 + length;
    in_offset = out_length = 0;
    memcpy(incoming, "KBW1", 4);
    incoming[4] = op;
    incoming[5] = length & 0xff;
    incoming[6] = length >> 8;
    memcpy(incoming + 7, payload, length);
    uint32_t crc = crc32(0, incoming + 4, (uInt)(length + 3));
    if (bad_crc) crc++;
    for (int i = 0; i < 4; i++) incoming[7 + length + i] = crc >> (8 * i);
}

static int receive_status(void) {
    while (in_offset < in_length) profiles_poll();
    assert(out_length >= 12);
    assert(!memcmp(outgoing, "KBW1", 4));
    assert(le32(outgoing + out_length - 4) == crc32(0, outgoing + 4, (uInt)(out_length - 8)));
    return outgoing[7];
}

static void write_text(const char *path, const char *text) {
    FILE *file = fopen(path, "wb");
    assert(file);
    assert(fwrite(text, 1, strlen(text), file) == strlen(text));
    assert(!fclose(file));
}

static void assert_text(const char *path, const char *expected) {
    char content[100];
    FILE *file = fopen(path, "rb");
    assert(file);
    size_t length = fread(content, 1, sizeof(content) - 1, file);
    fclose(file);
    content[length] = 0;
    assert(!strcmp(content, expected));
}

int main(void) {
    char folder[] = "/tmp/keybow-profile-test-XXXXXX";
    assert(mkdtemp(folder));
    assert(chdir(folder) == 0);
    assert(mkdir("profiles", 0700) == 0);
    write_text("profiles/default.lua", "old source");
    write_text("profiles/active", "default");

    chunk_size = 2;
    command(1, "", 0);
    profiles_poll();
    assert(!out_length);
    assert(receive_status() == 0);

    command(1, "", 1);
    while (in_offset < in_length) profiles_poll();
    assert(!out_length);

    command(4, "default\n!bad source", 0);
    assert(receive_status() == 1);
    assert_text("profiles/default.lua", "old source");

    fail_reload = 1;
    command(4, "default\nnew source", 0);
    assert(receive_status() == 4);
    assert_text("profiles/default.lua", "old source");

    command(4, "second\nvalid source", 0);
    assert(receive_status() == 0);
    assert_text("profiles/second.lua", "valid source");

    command(5, "second", 0);
    assert(receive_status() == 4);
    assert_text("profiles/active", "default");

    fail_reload = 0;
    command(5, "second", 0);
    assert(receive_status() == 0);
    assert_text("profiles/active", "second");

    command(6, "second", 0);
    assert(receive_status() == 1);

    command(2, "", 0);
    assert(receive_status() == 0);
    assert(!memcmp(outgoing + 8, "second\n", 7));
    puts("device profile protocol: OK");
    return 0;
}
