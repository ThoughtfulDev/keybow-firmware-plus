#include "serial.h"

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <termios.h>
#include <unistd.h>

static int port_fd = -1;
static char line_buffer[512];

int serial_open(void) {
    if (port_fd >= 0) return 0;
    port_fd = open(KEYBOW_SERIAL, O_RDWR | O_NOCTTY | O_NONBLOCK);
    if (port_fd < 0) return -1;

    struct termios settings;
    if (tcgetattr(port_fd, &settings) == 0) {
        cfmakeraw(&settings);
        settings.c_cflag |= CLOCAL | CREAD;
        cfsetispeed(&settings, B115200);
        cfsetospeed(&settings, B115200);
        tcsetattr(port_fd, TCSANOW, &settings);
    }
    return 0;
}

int serial_read_bytes(void *buffer, size_t length) {
    if (serial_open() != 0) return 0;
    ssize_t count = read(port_fd, buffer, length);
    if (count > 0) return (int)count;
    if (count == 0 || errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR) return 0;
    close(port_fd);
    port_fd = -1;
    return -1;
}

int serial_write_all(const void *buffer, size_t length) {
    if (serial_open() != 0) return -1;
    const unsigned char *bytes = buffer;
    size_t offset = 0;
    while (offset < length) {
        ssize_t count = write(port_fd, bytes + offset, length - offset);
        if (count > 0) {
            offset += (size_t)count;
            continue;
        }
        if (count < 0 && errno == EINTR) continue;
        if (count < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
            struct pollfd descriptor = {.fd = port_fd, .events = POLLOUT};
            if (poll(&descriptor, 1, 1000) > 0) continue;
        }
        close(port_fd);
        port_fd = -1;
        return -1;
    }
    return (int)offset;
}

char *serial_read(void) {
    size_t used = 0;
    while (used < sizeof(line_buffer) - 1) {
        char c;
        if (serial_read_bytes(&c, 1) <= 0) break;
        if (c == '\n') break;
        if (c != '\r') line_buffer[used++] = c;
    }
    line_buffer[used] = '\0';
    return line_buffer;
}

int serial_write(const char *data, int length) {
    return length < 0 ? -1 : serial_write_all(data, (size_t)length);
}
