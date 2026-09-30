#ifndef KEYBOW_UPDATER_H
#define KEYBOW_UPDATER_H

#include <stddef.h>

/* Returns 1 for an update command; status follows the profile protocol. */
int update_handle(unsigned char command, const unsigned char *payload, size_t length,
                  unsigned char *result, size_t *result_length, unsigned char *status);
int update_busy(void);
void update_poll_reboot(void);

#endif
