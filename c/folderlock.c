#include <stdlib.h>
#include <stdio.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <string.h>
#include <assert.h>
#include <errno.h>

#if defined(_WIN32) || defined(__MINGW32__) || defined(__MINGW64__)
#ifndef WINDOWS_MODE
#define WINDOWS_MODE 1
#endif
#else
#ifndef WINDOWS_MODE
#define _XOPEN_SOURCE 700
#define WINDOWS_MODE 0
#endif
#endif

#define PATH_SIZE PATH_MAX

#if WINDOWS_MODE == 0
#define PATHSEP "/"
#include <dirent.h>
#else
#define PATHSEP "\\"
#include <wchar.h>
#include <fileapi.h>
#include <windows.h>
#define sleep(_secs) Sleep(_secs)
#endif

static void pathAsserts(const char *where, const char *name, char *path, size_t pathSize) {
    assert(where);
    assert(name);
    assert(path);
    assert(strlen(where) + strlen(name) + 1 < pathSize);
}
//returns 0 if something went wrong
static int getPath(const char *where, const char *name, char *path, size_t pathSize) {
    if (!where || !name || !path) return 0;
    int whereLen = strlen(where);
    if (whereLen + strlen(name) + 1 >= pathSize) return 0;

    if (!(whereLen == 0 || (whereLen == 1 && where[0] == '.'))) {
        strcpy(path, where);
        strcat(path, PATHSEP);
    }
    strcat(path, name);
    return 1;
}

static int getPidFromFolder(const char *path) {
#if WINDOWS_MODE == 1
    HANDLE hfind;
    WIN32_FIND_DATAA data;
    hfind = FindFirstFileA(path, &data);
    if (hfind == INVALID_HANDLE_VALUE) {
        return -1;
    }
    int rv = atoi(data.cFileName);
    FindClose(hfind);
#else
    DIR *dp;
    struct dirent *ep;
    dp = opendir(path);
    if (dp == NULL) {
        return -1;
    }
    ep = readdir(dp);
    if (ep == NULL) {
        (void) closedir(dp);
        return -2;
    }
    int rv = atoi(ep->d_name);
    (void) closedir(dp);
    return rv;
#endif
}

//returns 1 if lock was aquired, 0 otherwise
int static_try_lock(const char *where, const char *name) {
    char path[PATH_SIZE];
    pathAsserts(where, name, path, sizeof(path));
    getPath(where, name, path, sizeof(path));
    int success = mkdir(path, 0777);
    if (success == 0) {
        //succeded at making lock dir
        //make pid file
        char pidpath[PATH_SIZE];
        char pidstr[16];
        sprintf(pidstr, "%d", getpid());
        int rv = getPath(path, pidstr, pidpath, sizeof(pidpath));
        if (!rv) {
            rmdir(path);
            return 0;
        }
        FILE *f = fopen(pidstr, "w");
        fclose(f);
        return 1;
    } else {
        return 0;
    }
}

void unlock(const char *where, const char *name) {
    char path[PATH_SIZE];
    pathAsserts(where, name, path, sizeof(path));
    getPath(where, name, path, sizeof(path));
    //complete
}

