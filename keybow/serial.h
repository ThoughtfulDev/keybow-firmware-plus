#ifndef KEYBOW_SERIAL
#define KEYBOW_SERIAL "/dev/ttyGS0"
#endif
#include <stddef.h>
int serial_open(void);
int serial_read_bytes(void *buffer, size_t length);
int serial_write_all(const void *buffer, size_t length);
char *serial_read(void);
int serial_write(const char *data, int length);
