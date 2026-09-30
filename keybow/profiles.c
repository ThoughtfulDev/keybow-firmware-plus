#include "profiles.h"
#include "lua-config.h"
#include "serial.h"
#include "updater.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#include <zlib.h>

#define MAX_PAYLOAD 16384
#define FRAME_OVERHEAD 11
#define PROFILE_DIR "profiles"

enum { PING = 1, LIST = 2, READ = 3, WRITE = 4, ACTIVATE = 5, DELETE = 6 };
enum { OK = 0, INVALID = 1, MISSING = 2, IO_ERROR = 3, RELOAD_ERROR = 4 };

static unsigned char receive_buffer[MAX_PAYLOAD + FRAME_OVERHEAD];
static size_t receive_count;
static time_t last_byte_time;

static uint32_t get_u32(const unsigned char *bytes) {
    return (uint32_t)bytes[0] | ((uint32_t)bytes[1] << 8) |
           ((uint32_t)bytes[2] << 16) | ((uint32_t)bytes[3] << 24);
}

static void put_u32(unsigned char *bytes, uint32_t value) {
    for (int i = 0; i < 4; i++) bytes[i] = (unsigned char)(value >> (i * 8));
}

static void respond(unsigned char command, unsigned char status,
                    const unsigned char *data, size_t length) {
    if (length + 1 > MAX_PAYLOAD) return;
    unsigned char *frame = malloc(length + FRAME_OVERHEAD + 1);
    if (!frame) return;
    memcpy(frame, "KBW1", 4);
    frame[4] = command | 0x80;
    size_t payload_length = length + 1;
    frame[5] = payload_length & 0xff;
    frame[6] = (payload_length >> 8) & 0xff;
    frame[7] = status;
    if (length) memcpy(frame + 8, data, length);
    put_u32(frame + 8 + length, crc32(0, frame + 4, (uInt)(4 + length)));
    serial_write_all(frame, length + FRAME_OVERHEAD + 1);
    free(frame);
}

static int valid_id(const unsigned char *bytes, size_t length) {
    if (length == 0 || length > 32) return 0;
    for (size_t i = 0; i < length; i++) {
        unsigned char c = bytes[i];
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-')) return 0;
    }
    return 1;
}

static int profile_path(char *path, size_t capacity,
                        const unsigned char *id, size_t length) {
    if (!valid_id(id, length)) return 0;
    return snprintf(path, capacity, PROFILE_DIR "/%.*s.lua", (int)length, id) < (int)capacity;
}

static int read_file(const char *path, unsigned char *out, size_t *length) {
    FILE *file = fopen(path, "rb");
    if (!file) return -1;
    size_t count = fread(out, 1, MAX_PAYLOAD - 1, file);
    int oversized = fgetc(file) != EOF;
    int failed = ferror(file);
    fclose(file);
    if (oversized || failed) return -1;
    *length = count;
    return 0;
}

static int write_file(const char *path, const unsigned char *data, size_t length) {
    FILE *file = fopen(path, "wb");
    if (!file) return -1;
    int failed = fwrite(data, 1, length, file) != length;
    if (fflush(file) != 0 || fsync(fileno(file)) != 0) failed = 1;
    if (fclose(file) != 0) failed = 1;
    return failed ? -1 : 0;
}

static void active_id(char out[33]) {
    FILE *file = fopen(PROFILE_DIR "/active", "rb");
    if (!file || !fgets(out, 33, file)) {
        strcpy(out, "default");
    } else {
        out[strcspn(out, "\r\n")] = '\0';
        if (!valid_id((const unsigned char *)out, strlen(out))) strcpy(out, "default");
    }
    if (file) fclose(file);
}

static int write_active(const unsigned char *id, size_t length) {
    if (write_file(PROFILE_DIR "/active.tmp", id, length) != 0) return -1;
    if (rename(PROFILE_DIR "/active.tmp", PROFILE_DIR "/active") != 0) {
        unlink(PROFILE_DIR "/active.tmp");
        return -1;
    }
    return 0;
}

static void handle(unsigned char command, const unsigned char *payload, size_t length) {
    unsigned char result[MAX_PAYLOAD];
    char path[64];
    char current[33];
    size_t result_length = 0;
    unsigned char status = OK;

    if (update_handle(command, payload, length, result, &result_length, &status)) {
        respond(command, status, status == OK ? result : NULL, status == OK ? result_length : 0);
        return;
    }
    if (update_busy() && (command == WRITE || command == ACTIVATE || command == DELETE)) {
        respond(command, IO_ERROR, NULL, 0);
        return;
    }

    switch (command) {
    case PING:
        if (length) { status = INVALID; break; }
        memcpy(result, "Keybow 1", 8);
        result_length = 8;
        break;
    case LIST: {
        if (length) { status = INVALID; break; }
        active_id(current);
        result_length = (size_t)snprintf((char *)result, sizeof(result), "%s\n", current);
        DIR *directory = opendir(PROFILE_DIR);
        if (!directory) { status = IO_ERROR; break; }
        struct dirent *entry;
        while ((entry = readdir(directory))) {
            size_t name_length = strlen(entry->d_name);
            if (name_length < 5 || strcmp(entry->d_name + name_length - 4, ".lua")) continue;
            if (!valid_id((const unsigned char *)entry->d_name, name_length - 4)) continue;
            if (result_length + name_length + 1 >= sizeof(result)) { status = IO_ERROR; break; }
            memcpy(result + result_length, entry->d_name, name_length - 4);
            result_length += name_length - 4;
            result[result_length++] = '\n';
        }
        closedir(directory);
        break;
    }
    case READ:
        if (!profile_path(path, sizeof(path), payload, length)) { status = INVALID; break; }
        if (read_file(path, result, &result_length) != 0) status = MISSING;
        break;
    case WRITE: {
        const unsigned char *separator = memchr(payload, '\n', length);
        if (!separator || !profile_path(path, sizeof(path), payload, (size_t)(separator - payload))) {
            status = INVALID; break;
        }
        size_t source_length = length - (size_t)(separator - payload) - 1;
        const unsigned char *source = separator + 1;
        if (!source_length || luaCheckSource((const char *)source, source_length)) {
            status = INVALID; break;
        }
        char temp_path[80], backup_path[80];
        snprintf(temp_path, sizeof(temp_path), "%s.tmp", path);
        snprintf(backup_path, sizeof(backup_path), "%s.bak", path);
        if (write_file(temp_path, source, source_length) != 0) { status = IO_ERROR; break; }
        int had_old = access(path, F_OK) == 0;
        if (had_old) {
            size_t old_length = 0;
            if (read_file(path, result, &old_length) != 0 ||
                write_file(backup_path, result, old_length) != 0) {
                unlink(temp_path);
                status = IO_ERROR;
                break;
            }
        }
        if (rename(temp_path, path) != 0) {
            if (had_old) unlink(backup_path);
            unlink(temp_path);
            status = IO_ERROR; break;
        }
        active_id(current);
        if (strlen(current) == (size_t)(separator - payload) &&
            memcmp(current, payload, separator - payload) == 0 && luaReload() != 0) {
            unlink(path);
            if (had_old) rename(backup_path, path);
            status = RELOAD_ERROR;
        } else if (had_old) {
            unlink(backup_path);
        }
        break;
    }
    case ACTIVATE: {
        if (!profile_path(path, sizeof(path), payload, length)) { status = INVALID; break; }
        if (read_file(path, result, &result_length) != 0) { status = MISSING; break; }
        if (luaCheckSource((const char *)result, result_length)) { status = INVALID; break; }
        active_id(current);
        if (write_active(payload, length) != 0) { status = IO_ERROR; break; }
        if (luaReload() != 0) {
            write_active((const unsigned char *)current, strlen(current));
            status = RELOAD_ERROR;
        }
        result_length = 0;
        break;
    }
    case DELETE:
        if (!profile_path(path, sizeof(path), payload, length)) { status = INVALID; break; }
        active_id(current);
        if (strlen(current) == length && !memcmp(current, payload, length)) { status = INVALID; break; }
        if (unlink(path) != 0) status = errno == ENOENT ? MISSING : IO_ERROR;
        break;
    default:
        status = INVALID;
    }
    respond(command, status, status == OK ? result : NULL, status == OK ? result_length : 0);
}

void profiles_poll(void) {
    unsigned char incoming[256];
    int count = serial_read_bytes(incoming, sizeof(incoming));
    if (count <= 0) return;
    time_t now = time(NULL);
    if (receive_count && now - last_byte_time > 3) receive_count = 0;
    last_byte_time = now;
    for (int i = 0; i < count; i++) {
        if (receive_count == sizeof(receive_buffer)) receive_count = 0;
        receive_buffer[receive_count++] = incoming[i];
        while (receive_count >= 4) {
            if (memcmp(receive_buffer, "KBW1", 4) != 0) {
                memmove(receive_buffer, receive_buffer + 1, --receive_count);
                continue;
            }
            if (receive_count < 7) break;
            size_t payload_length = receive_buffer[5] | ((size_t)receive_buffer[6] << 8);
            if (payload_length > MAX_PAYLOAD) {
                memmove(receive_buffer, receive_buffer + 1, --receive_count);
                continue;
            }
            size_t frame_length = FRAME_OVERHEAD + payload_length;
            if (receive_count < frame_length) break;
            uint32_t expected = get_u32(receive_buffer + 7 + payload_length);
            uint32_t actual = crc32(0, receive_buffer + 4, (uInt)(3 + payload_length));
            if (expected == actual && !(receive_buffer[4] & 0x80)) {
                handle(receive_buffer[4], receive_buffer + 7, payload_length);
            }
            receive_count -= frame_length;
            memmove(receive_buffer, receive_buffer + frame_length, receive_count);
        }
    }
}
