/*
 * proc_io_shim.c
 *
 * Workaround for WSL2 kernel 6.18+ built without CONFIG_TASKSTATS, which
 * causes /proc/<pid>/io to not exist. Typesense's internal brpc library
 * reads this file during startup before its logger is ready, causing a
 * segfault. This shim intercepts fopen/fopen64 and returns fake zero-valued
 * I/O stats when that path is requested.
 *
 * Compile: gcc -shared -fPIC -O2 -o proc_io_shim.so proc_io_shim.c -ldl
 * Use:     LD_PRELOAD=/path/to/proc_io_shim.so ./typesense-server ...
 */

#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static FILE *(*real_fopen)(const char *, const char *)   = NULL;
static FILE *(*real_fopen64)(const char *, const char *) = NULL;

static void init_real(void) {
    if (!real_fopen)   real_fopen   = dlsym(RTLD_NEXT, "fopen");
    if (!real_fopen64) real_fopen64 = dlsym(RTLD_NEXT, "fopen64");
}

/* Match /proc/<anything>/io */
static int is_proc_io(const char *path) {
    if (!path || strncmp(path, "/proc/", 6) != 0) return 0;
    const char *p = path + 6;
    while (*p && *p != '/') p++;   /* skip pid or "self" */
    return strcmp(p, "/io") == 0;
}

static const char FAKE_IO[] =
    "rchar: 0\n"
    "wchar: 0\n"
    "syscr: 0\n"
    "syscw: 0\n"
    "read_bytes: 0\n"
    "write_bytes: 0\n"
    "cancelled_write_bytes: 0\n";

static FILE *make_fake_io(void) {
    return fmemopen((void *)FAKE_IO, sizeof(FAKE_IO) - 1, "r");
}

FILE *fopen(const char *path, const char *mode) {
    init_real();
    return is_proc_io(path) ? make_fake_io() : real_fopen(path, mode);
}

FILE *fopen64(const char *path, const char *mode) {
    init_real();
    return is_proc_io(path) ? make_fake_io() : real_fopen64(path, mode);
}
