#include "updater.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static unsigned char result[16384], status;
static size_t result_length;

static void call(unsigned char command, const void *payload, size_t length, int expected) {
    assert(update_handle(command, payload, length, result, &result_length, &status));
    assert(status == expected);
}

static unsigned char *read_file(const char *path, size_t *size) {
    FILE *file = fopen(path, "rb");
    assert(file);
    assert(!fseek(file, 0, SEEK_END));
    *size = (size_t)ftell(file);
    rewind(file);
    unsigned char *data = malloc(*size + 1);
    assert(data && fread(data, 1, *size, file) == *size);
    fclose(file);
    return data;
}

int main(int argc, char **argv) {
    assert(argc == 3);
    size_t manifest_size;
    unsigned char *manifest = read_file(argv[1], &manifest_size);
    assert(!chdir(argv[2]));

    const char *bad = "profiles/active 1 0000000000000000000000000000000000000000000000000000000000000000\n";
    call(8, bad, strlen(bad), 1);
    setenv("KEYBOW_TEST_FREE_BYTES", "0", 1);
    call(8, manifest, manifest_size, 3);
    unsetenv("KEYBOW_TEST_FREE_BYTES");
    call(8, manifest, manifest_size, 0);
    assert(update_busy());
    call(9, NULL, 0, 0);
    assert(result_length == 5 && result[0] == 0 && result[1] == 0);
    const unsigned char out_of_order[] = {0, 1, 0, 0, 0, 'x'};
    call(10, out_of_order, sizeof(out_of_order), 1);

    char line[160], path[80], hash[65];
    unsigned size, index = 0;
    FILE *lines = fopen(argv[1], "r");
    assert(lines);
    while (fgets(line, sizeof(line), lines)) {
        assert(sscanf(line, "%79s %u %64s", path, &size, hash) == 3);
        char source[160];
        snprintf(source, sizeof(source), "new/%s", path);
        size_t data_size;
        unsigned char *data = read_file(source, &data_size);
        assert(data_size == size);
        unsigned offset = 0;
        while (offset < size) {
            unsigned amount = size - offset > 7 ? 7 : size - offset;
            unsigned char payload[12] = {(unsigned char)index, (unsigned char)offset,
                                         (unsigned char)(offset >> 8), (unsigned char)(offset >> 16),
                                         (unsigned char)(offset >> 24)};
            memcpy(payload + 5, data + offset, amount);
            call(10, payload, amount + 5, 0);
            offset += amount;
            if (index == 0 && offset == amount) call(8, manifest, manifest_size, 0);
            call(9, NULL, 0, 0);
            if (offset < size) assert(result[0] == index && result[1] == offset);
        }
        free(data);
        index++;
    }
    fclose(lines);
    call(9, NULL, 0, 0);
    assert(result[0] == index);
    call(11, NULL, 0, 0);
    call(12, NULL, 0, 0);
    call(7, NULL, 0, 0);
    result[result_length] = 0;
    assert(strstr((char *)result, "pending"));
    free(manifest);
    return 0;
}
