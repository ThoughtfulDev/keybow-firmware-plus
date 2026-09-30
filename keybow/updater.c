#include "updater.h"

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <time.h>
#include <unistd.h>

#define ROOT ".keybow-update"
#define MANIFEST ROOT "/manifest"
#define NEXT ROOT "/next/"
#define PREVIOUS ROOT "/previous/"
#define MAX_FILES 64
#define MAX_MANIFEST 12000
#define MAX_FILE (4 * 1024 * 1024)
#define MAX_TOTAL (8 * 1024 * 1024)
#define CHUNK_SIZE 8192

enum { INFO = 7, BEGIN = 8, QUERY = 9, CHUNK = 10, VERIFY = 11, APPLY = 12, RESET = 13 };
enum { OK = 0, INVALID = 1, MISSING = 2, IO_ERROR = 3, RELOAD_ERROR = 4 };

struct entry { char path[80]; unsigned size; char hash[65]; };
static struct entry entries[MAX_FILES];
static unsigned entry_count;
static time_t reboot_at;

static uint32_t get_u32(const unsigned char *data) {
    return (uint32_t)data[0] | ((uint32_t)data[1] << 8) |
           ((uint32_t)data[2] << 16) | ((uint32_t)data[3] << 24);
}

static void put_u32(unsigned char *data, uint32_t value) {
    for (int i = 0; i < 4; i++) data[i] = (unsigned char)(value >> (8 * i));
}

static int allowed(const char *path) {
    if (!strcmp(path, "keybow") || !strcmp(path, "keys.lua") ||
        !strcmp(path, "keybow.lua") || !strcmp(path, "default.png") ||
        !strcmp(path, "firmware-version")) return 1;
    const char *suffix = NULL;
    if (!strncmp(path, "keyboards/", 10)) suffix = ".lua";
    if (!strncmp(path, "patterns/", 9)) suffix = ".png";
    if (!suffix) return 0;
    const char *name = strchr(path, '/') + 1;
    size_t length = strlen(name), ending = strlen(suffix);
    if (length <= ending || strcmp(name + length - ending, suffix)) return 0;
    for (size_t i = 0; i < length - ending; i++) {
        char c = name[i];
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-' || c == '_')) return 0;
    }
    return 1;
}

static int parse_manifest(const unsigned char *data, size_t length) {
    if (!length || length > MAX_MANIFEST || data[length - 1] != '\n') return -1;
    char copy[MAX_MANIFEST + 1];
    memcpy(copy, data, length);
    copy[length] = 0;
    unsigned count = 0, total = 0;
    char *save = NULL;
    for (char *line = strtok_r(copy, "\n", &save); line; line = strtok_r(NULL, "\n", &save)) {
        if (count >= MAX_FILES) return -1;
        struct entry *item = &entries[count];
        int used = 0;
        if (sscanf(line, "%79s %u %64s%n", item->path, &item->size, item->hash, &used) != 3 ||
            line[used] || !allowed(item->path) || !item->size || item->size > MAX_FILE) return -1;
        if (strlen(item->hash) != 64) return -1;
        for (int i = 0; i < 64; i++) if (!((item->hash[i] >= '0' && item->hash[i] <= '9') ||
                                            (item->hash[i] >= 'a' && item->hash[i] <= 'f'))) return -1;
        for (unsigned i = 0; i < count; i++) if (!strcmp(entries[i].path, item->path)) return -1;
        total += item->size;
        if (total > MAX_TOTAL) return -1;
        count++;
    }
    const char *required[] = {"keybow", "keys.lua", "keybow.lua", "default.png", "firmware-version"};
    for (unsigned r = 0; r < sizeof(required) / sizeof(required[0]); r++) {
        int found = 0;
        for (unsigned i = 0; i < count; i++) if (!strcmp(entries[i].path, required[r])) found = 1;
        if (!found) return -1;
    }
    entry_count = count;
    return 0;
}

static int load_manifest(void) {
    FILE *file = fopen(MANIFEST, "rb");
    if (!file) return -1;
    unsigned char data[MAX_MANIFEST + 1];
    size_t size = fread(data, 1, sizeof(data), file);
    int bad = ferror(file) || size > MAX_MANIFEST;
    fclose(file);
    return bad ? -1 : parse_manifest(data, size);
}

static int write_file(const char *path, const void *data, size_t length) {
    FILE *file = fopen(path, "wb");
    if (!file) return -1;
    int bad = fwrite(data, 1, length, file) != length;
    if (fflush(file) || fsync(fileno(file))) bad = 1;
    if (fclose(file)) bad = 1;
    return bad ? -1 : 0;
}

static int same_file(const char *path, const unsigned char *data, size_t length) {
    FILE *file = fopen(path, "rb");
    if (!file) return 0;
    unsigned char buffer[MAX_MANIFEST + 1];
    size_t size = fread(buffer, 1, sizeof(buffer), file);
    fclose(file);
    return size == length && !memcmp(buffer, data, length);
}

static int make_dirs(void) {
    if (mkdir(ROOT, 0700) && errno != EEXIST) return -1;
    const char *dirs[] = {ROOT "/next", ROOT "/next/keyboards", ROOT "/next/patterns",
                          ROOT "/previous", ROOT "/previous/keyboards", ROOT "/previous/patterns"};
    for (unsigned i = 0; i < sizeof(dirs) / sizeof(dirs[0]); i++)
        if (mkdir(dirs[i], 0700) && errno != EEXIST) return -1;
    return 0;
}

static void remove_staging(void) {
    if (load_manifest() == 0) for (unsigned i = 0; i < entry_count; i++) {
        char path[128];
        snprintf(path, sizeof(path), NEXT "%s", entries[i].path); unlink(path);
        snprintf(path, sizeof(path), PREVIOUS "%s", entries[i].path); unlink(path);
    }
    unlink(MANIFEST);
    unlink(ROOT "/prepared");
    unlink(ROOT "/ready");
    unlink(ROOT "/failed");
}

static int sha_matches(const char *path, const char *expected) {
    char command[170];
    if (snprintf(command, sizeof(command), "sha256sum %s", path) >= (int)sizeof(command)) return 0;
    FILE *pipe = popen(command, "r");
    if (!pipe) return 0;
    char line[90];
    int ok = fgets(line, sizeof(line), pipe) && !strncmp(line, expected, 64);
    if (pclose(pipe)) ok = 0;
    return ok;
}

static int copy_file(const char *source, const char *target) {
    FILE *in = fopen(source, "rb"), *out = NULL;
    if (!in) return -1;
    out = fopen(target, "wb");
    if (!out) { fclose(in); return -1; }
    unsigned char buffer[8192];
    size_t count;
    int bad = 0;
    while ((count = fread(buffer, 1, sizeof(buffer), in)))
        if (fwrite(buffer, 1, count, out) != count) { bad = 1; break; }
    if (ferror(in) || fflush(out) || fsync(fileno(out))) bad = 1;
    if (fclose(out)) bad = 1;
    fclose(in);
    return bad ? -1 : 0;
}

int update_busy(void) {
    return access(MANIFEST, F_OK) == 0 && access(ROOT "/failed", F_OK) != 0;
}

int update_handle(unsigned char command, const unsigned char *payload, size_t length,
                  unsigned char *result, size_t *result_length, unsigned char *status) {
    if (command < INFO || command > RESET) return 0;
    *result_length = 0;
    *status = OK;
    if (command == INFO) {
        if (length) { *status = INVALID; return 1; }
        char version[40] = "unknown";
        FILE *file = fopen("firmware-version", "r");
        if (file) { if (fgets(version, sizeof(version), file)) version[strcspn(version, "\r\n")] = 0; fclose(file); }
        const char *state = access(ROOT "/failed", F_OK) == 0 ? "rolled-back" :
                            access(ROOT "/pending", F_OK) == 0 ? "pending" :
                            access(ROOT "/prepared", F_OK) == 0 ? "prepared" :
                            update_busy() ? "staging" : "idle";
        *result_length = (size_t)snprintf((char *)result, 160, "%s\n%s", version, state);
        return 1;
    }
    if (access(ROOT "/pending", F_OK) == 0) { *status = INVALID; return 1; }
    if (command == RESET) {
        if (length) *status = INVALID;
        else remove_staging();
        return 1;
    }
    if (command == BEGIN) {
        if (parse_manifest(payload, length)) { *status = INVALID; return 1; }
        if (same_file(MANIFEST, payload, length)) return 1;
        struct statvfs space;
        unsigned total = 0;
        for (unsigned i = 0; i < entry_count; i++) total += entries[i].size;
        unsigned long long available = 0;
        if (!statvfs(".", &space)) available = (unsigned long long)space.f_bavail * space.f_frsize;
#ifdef KEYBOW_UPDATER_TEST
        const char *override = getenv("KEYBOW_TEST_FREE_BYTES");
        if (override) available = strtoull(override, NULL, 10);
#endif
        if (available < 2ULL * total + 1024 * 1024) {
            *status = IO_ERROR; return 1;
        }
        remove_staging();
        if (make_dirs() || write_file(MANIFEST, payload, length)) *status = IO_ERROR;
        return 1;
    }
    if (load_manifest()) { *status = MISSING; return 1; }
    if (command == QUERY) {
        if (length) { *status = INVALID; return 1; }
        unsigned i = 0, offset = 0;
        for (; i < entry_count; i++) {
            char path[128]; struct stat info;
            snprintf(path, sizeof(path), NEXT "%s", entries[i].path);
            offset = stat(path, &info) ? 0 : (unsigned)info.st_size;
            if (offset < entries[i].size) break;
            if (offset > entries[i].size) { *status = INVALID; return 1; }
        }
        result[0] = (unsigned char)i;
        put_u32(result + 1, i == entry_count ? 0 : offset);
        *result_length = 5;
        return 1;
    }
    if (command == CHUNK) {
        if (length < 6 || length > CHUNK_SIZE + 5 || payload[0] >= entry_count ||
            access(ROOT "/prepared", F_OK) == 0) { *status = INVALID; return 1; }
        struct entry *item = &entries[payload[0]];
        unsigned offset = get_u32(payload + 1);
        char path[128]; struct stat info;
        snprintf(path, sizeof(path), NEXT "%s", item->path);
        unsigned current = stat(path, &info) ? 0 : (unsigned)info.st_size;
        if (offset != current || offset + length - 5 > item->size) { *status = INVALID; return 1; }
        FILE *file = fopen(path, "ab");
        if (!file) { *status = IO_ERROR; return 1; }
        int bad = fwrite(payload + 5, 1, length - 5, file) != length - 5;
        if (fflush(file) || fsync(fileno(file))) bad = 1;
        if (fclose(file)) bad = 1;
        if (bad) *status = IO_ERROR;
        return 1;
    }
    if (length) { *status = INVALID; return 1; }
    if (command == VERIFY) {
        for (unsigned i = 0; i < entry_count; i++) {
            char next[128], previous[128]; struct stat info;
            snprintf(next, sizeof(next), NEXT "%s", entries[i].path);
            snprintf(previous, sizeof(previous), PREVIOUS "%s", entries[i].path);
            if (stat(next, &info) || (unsigned)info.st_size != entries[i].size ||
                !sha_matches(next, entries[i].hash)) { *status = INVALID; return 1; }
            if (access(entries[i].path, F_OK) == 0 && copy_file(entries[i].path, previous)) {
                *status = IO_ERROR; return 1;
            }
        }
        if (write_file(ROOT "/prepared", "ok\n", 3)) *status = IO_ERROR;
        sync();
        return 1;
    }
    if (access(ROOT "/prepared", F_OK)) { *status = INVALID; return 1; }
    unlink(ROOT "/ready");
    unlink(ROOT "/failed");
    if (write_file(ROOT "/pending", "pending\n", 8)) *status = IO_ERROR;
    else { sync(); reboot_at = time(NULL) + 2; }
    return 1;
}

void update_poll_reboot(void) {
    if (reboot_at && time(NULL) >= reboot_at) { sync(); reboot(RB_AUTOBOOT); reboot_at = 0; }
}
