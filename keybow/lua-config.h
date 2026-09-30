#include <errno.h>
#include <stdio.h>
#include <stddef.h>
#include <fcntl.h>
#include <stdio.h>
#include <lua.h>
#include <lualib.h>
#include <lauxlib.h>

#pragma once

int initLUA();
void luaTick(void);
int luaHandleKey(unsigned short key_index, unsigned short state);
void luaClose(void);
int luaCallSetup(void);
int luaReload(void);
int luaCheckSource(const char *source, size_t length);
