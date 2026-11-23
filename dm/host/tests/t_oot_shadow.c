// Ocarina of Time shadow range (android/oot_shadow.c): opt-in and build gate, the last cascade split capped, inner splits pulled below a short range, a live change and a reset
// while the game copies the splits every frame and while it does not (no accumulation), and depth shadows whose fields are not the game's. Each case runs in its own process.
#include "../android/oot_shadow.c"
#include <assert.h>
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>

static module_t test_modules[1];
module_t *g_mod = test_modules;
int g_nmod;
static void (*callbacks[OBS_MAX])(uint64_t *, int);

void gate_obs_set(int id, void (*fn)(uint64_t *, int)) {
    assert(id > 0 && id < OBS_MAX);
    callbacks[id] = fn;
}

static _Alignas(16) unsigned char ds[0x400];
static float splits[8];
static const float GAME[4] = {2, 32, 64, 3000};   // Main.gsys__ModelSceneConfigParam: DepthShadowNear00..02 and DepthShadowFar0, three cascades

static void make(int n, int max) {   // the depth shadow as the view update leaves it before the fit: count, cascades made, split pointer; the game's splits copied in
    memset(ds, 0, sizeof ds);
    memcpy(ds + DS_NUM, &n, 4);
    memcpy(ds + DS_MAXNUM, &max, 4);
    uint64_t p = (uintptr_t)splits;
    memcpy(ds + DS_SPLITS, &p, 8);
    memset(splits, 0, sizeof splits);
    memcpy(splits, GAME, sizeof GAME);
}
static void copy(void) { memcpy(splits, GAME, sizeof GAME); }   // the game's own per-frame copy from its config
static void gate(void) {
    uint64_t r[31] = {0};
    r[0] = (uintptr_t)ds;
    callbacks[OBS_OOT_SHADOW](r, 0);
}
static int is(float a, float b, float c, float d) { return splits[0] == a && splits[1] == b && splits[2] == c && splits[3] == d; }

static void check(int which) {   // 0 unset, 1 "", 2 "0", 3 junk, 4 "5" (below 10), 5 "5000" (beyond the game's 3000), 6 "200" on another build: no change; 7 "200"; 8 "50"; 9 "50" with 2 cascades made
    static const char *val[] = {NULL, "", "0", "abc", "5", "5000", "200", "200", "50", "50"};
    g_nmod = 1;
    strcpy(g_mod[0].name, "main");
    strcpy(g_mod[0].build_id, which == 6 ? "0000" : OOT_MAIN_BUILD);
    if (val[which]) setenv("DM_OOT_SHADOW_RANGE", val[which], 1); else unsetenv("DM_OOT_SHADOW_RANGE");
    make(3, which == 9 ? 2 : 3);
    gate();
    if (which < 7) { assert(is(2, 32, 64, 3000)); return; }
    if (which == 9) { assert(is(2, 26, 50, 3000)); return; }   // the fit uses 2 cascades (splits 0..2): the last of them capped, the fourth float not touched
    if (which == 8) { assert(is(2, 18, 34, 50)); return; }   // the inner splits pulled to their share of 2..50
    assert(is(2, 32, 64, 200));
    // every frame: the game copies and the fit runs again, or the game keeps the splits (its flag) and the fit runs again: never capped twice, never drifting
    for (int i = 0; i < 100; i++) { if (i & 1) copy(); gate(); assert(is(2, 32, 64, 200)); }
    // a live change while the array still holds our values: taken from the game's own
    setenv("DM_OOT_SHADOW_RANGE", "1000", 1); gate(); assert(is(2, 32, 64, 1000));
    setenv("DM_OOT_SHADOW_RANGE", "40", 1); gate(); assert(splits[0] == 2 && fabsf(splits[1] - 14.666667f) < 1e-4f && fabsf(splits[2] - 27.333334f) < 1e-4f && splits[3] == 40);
    setenv("DM_OOT_SHADOW_RANGE", "200", 1); gate(); assert(is(2, 32, 64, 200));
    // reset while the game does not copy: the game's values come back; while it copies: they stay
    unsetenv("DM_OOT_SHADOW_RANGE"); gate(); assert(is(2, 32, 64, 3000));
    gate(); assert(is(2, 32, 64, 3000));
    copy(); gate(); assert(is(2, 32, 64, 3000));
    // the game sets new splits of its own (a cutscene): they are capped as they are
    setenv("DM_OOT_SHADOW_RANGE", "200", 1);
    splits[1] = 10; splits[2] = 20; splits[3] = 500; gate(); assert(is(2, 10, 20, 200));
    splits[3] = 150; gate(); assert(is(2, 10, 20, 150));   // already inside the range
    // not the game's splits: decreasing, NaN, negative, absurd; a null or unaligned pointer, a count past the maximum
    float bad[][4] = {{2, 32, 16, 3000}, {2, NAN, 64, 3000}, {-1, 32, 64, 3000}, {2, 32, 64, 1e9f}};
    for (int k = 0; k < 4; k++) { memcpy(splits, bad[k], sizeof bad[k]); gate(); assert(!memcmp(splits, bad[k], sizeof bad[k]) || (k == 1 && isnan(splits[1]))); }
    copy();
    uint64_t z = 0; memcpy(ds + DS_SPLITS, &z, 8); gate();
    uint64_t r[31] = {0}; r[0] = (uintptr_t)ds + 4; callbacks[OBS_OOT_SHADOW](r, 0); r[0] = 0; callbacks[OBS_OOT_SHADOW](r, 0);
    make(9, 9); gate(); assert(is(2, 32, 64, 3000));
    make(3, 0); gate(); assert(is(2, 32, 64, 3000));
}

int main(void) {
    for (int i = 0; i < 10; i++) {
        pid_t child = fork();
        assert(child >= 0);
        if (!child) { check(i); _exit(0); }
        int status;
        assert(waitpid(child, &status, 0) == child);
        if (!WIFEXITED(status) || WEXITSTATUS(status)) {
            fprintf(stderr, "oot shadow case %d failed\n", i);
            return 1;
        }
    }
    puts("oot shadow: 10 shadow range cases passed");
    return 0;
}
