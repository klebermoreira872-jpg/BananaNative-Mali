// Ocarina of Time fog at the draw-distance cut (android/oot_fog.c): nothing changes unless both DM_OOT_FOG_AT_CUT=1 and a valid DM_OOT_DRAW_DISTANCE are set; then a fog that ends
// beyond the cut fades in over the last 15 % and is full at 0.95 of the distance, a nearer fog stays the game's, repeated gates do not compound, a fresh value the game writes is
// taken as its own, the game's values come back when either switch is unset, and another main build does nothing (its own process: checked once).
#include "../android/oot_fog.c"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>

static module_t test_modules[1];
module_t *g_mod = test_modules;
int g_nmod;
static void (*callbacks[OBS_MAX])(uint64_t *, int);
void gate_obs_set(int id, void (*fn)(uint64_t *, int)) { assert(id > 0 && id < OBS_MAX); callbacks[id] = fn; }

static _Alignas(16) unsigned char g_mgr[0x1000], g_sky[0xc00];

static float f(int off) { return rd((uint64_t)(uintptr_t)g_sky + off); }
static void setf(int off, float v) { wr((uint64_t)(uintptr_t)g_sky + off, v); }
static int near_(float a, float b) { return fabsf(a - b) < 1e-3f; }

// A sky as MainField leaves it: scatter fog 0..15000, adhoc fog 0..300 (alpha 0)
static void make(void) {
    memset(g_mgr, 0, sizeof g_mgr);
    memset(g_sky, 0, sizeof g_sky);
    uint64_t s = (uintptr_t)g_sky;
    memcpy(g_mgr + M_SKY, &s, 8);
    setf(S_SCATTER_NEAR, 0); setf(S_SCATTER_FAR, 15000); setf(0x8c0, 0.85f); setf(0x8e0, 30);
    setf(S_ADHOC_NEAR, 0); setf(S_ADHOC_FAR, 300);
}

// The gate at the view update (x19) or the scene draw (x21)
static void gate(int reg) {
    uint64_t r[31] = {0};
    r[reg] = (uintptr_t)g_mgr;
    r[20] = 0x1234;
    callbacks[OBS_OOT_FOG](r, reg);
    assert(r[reg] == (uintptr_t)g_mgr && r[20] == 0x1234);   // no register changes
}

static void set(const char *fog, const char *dd) {
    if (fog) setenv("DM_OOT_FOG_AT_CUT", fog, 1); else unsetenv("DM_OOT_FOG_AT_CUT");
    if (dd) setenv("DM_OOT_DRAW_DISTANCE", dd, 1); else unsetenv("DM_OOT_DRAW_DISTANCE");
}

static void cases(void) {
    g_nmod = 1;
    strcpy(g_mod[0].name, "main");
    strcpy(g_mod[0].build_id, OOT_FOG_BUILD);
    make();
    unsigned char before[sizeof g_sky];
    memcpy(before, g_sky, sizeof g_sky);

    // The game's own fog: either switch missing or invalid
    static const char *own[][2] = {{NULL, NULL}, {"1", NULL}, {NULL, "100"}, {"0", "100"}, {"yes", "100"}, {"1", ""}, {"1", "5"}, {"1", "30000"}, {"1", "100x"}, {"4", "100"}, {"12", "100"}, {"-1", "100"}, {"2x", "100"}};
    for (unsigned k = 0; k < sizeof own / sizeof *own; k++) {
        set(own[k][0], own[k][1]);
        gate(19); gate(21);
        assert(!memcmp(before, g_sky, sizeof g_sky));
    }

    // Light (1) at draw distance 100: both fogs end beyond 95, so both fade from 50 to 95; density and the rest untouched
    set("1", "100");
    for (int rep = 0; rep < 50; rep++) { gate(19); gate(21); }   // every frame, both consumers: never compounded
    assert(near_(f(S_SCATTER_NEAR), 50) && near_(f(S_SCATTER_FAR), 95));
    assert(near_(f(S_ADHOC_NEAR), 50) && near_(f(S_ADHOC_FAR), 95));
    assert(f(0x8c0) == 0.85f && f(0x8e0) == 30);

    // Live: Long (300) moves both (the adhoc fog's 300 is beyond 285)
    set("1", "300");
    gate(19);
    assert(near_(f(S_SCATTER_NEAR), 150) && near_(f(S_SCATTER_FAR), 285));
    assert(near_(f(S_ADHOC_NEAR), 150) && near_(f(S_ADHOC_FAR), 285));
    set("1", "1000");   // the adhoc fog ends at 300, inside the cut: the game's own again
    gate(21);
    assert(near_(f(S_SCATTER_NEAR), 500) && near_(f(S_SCATTER_FAR), 950));
    assert(f(S_ADHOC_NEAR) == 0 && f(S_ADHOC_FAR) == 300);

    // The game writes fresh values (its time of day or a new area): they are what is moved, and what comes back
    setf(S_SCATTER_FAR, 12000);
    setf(S_ADHOC_NEAR, 10); setf(S_ADHOC_FAR, 2000);
    set("1", "100");
    gate(19);
    assert(near_(f(S_SCATTER_FAR), 95) && near_(f(S_ADHOC_NEAR), 50) && near_(f(S_ADHOC_FAR), 95));
    set("1", NULL);   // the draw distance back to Auto: the game's values
    gate(19);
    assert(f(S_SCATTER_NEAR) == 0 && f(S_SCATTER_FAR) == 12000 && f(S_ADHOC_NEAR) == 10 && f(S_ADHOC_FAR) == 2000);
    set("1", "40");
    gate(21);
    assert(near_(f(S_SCATTER_NEAR), 20) && near_(f(S_SCATTER_FAR), 38));
    set(NULL, "40");   // the fog switch off: the game's values
    gate(21);
    assert(f(S_SCATTER_NEAR) == 0 && f(S_SCATTER_FAR) == 12000 && f(S_ADHOC_NEAR) == 10 && f(S_ADHOC_FAR) == 2000);
    gate(19);
    assert(f(S_SCATTER_FAR) == 12000);

    // Strength: the start percent moves both fogs' near; density and atten scale the scatter fog's, only while the cut is set, never compounded, restored with the rest
    set("1", "100");
    setenv("DM_OOT_FOG_START_PCT", "50", 1);
    setenv("DM_OOT_FOG_DENSITY", "300", 1);
    setenv("DM_OOT_FOG_ATTEN", "50", 1);
    for (int rep = 0; rep < 20; rep++) { gate(19); gate(21); }
    assert(near_(f(S_SCATTER_NEAR), 50) && near_(f(S_SCATTER_FAR), 95) && near_(f(S_ADHOC_NEAR), 50));
    assert(near_(f(S_SCATTER_DENSITY), 2.55f) && near_(f(S_SCATTER_ATTEN), 15));
    setf(S_SCATTER_DENSITY, 0.5f);   // the game's time of day writes a fresh density: that is what is scaled
    gate(19);
    assert(near_(f(S_SCATTER_DENSITY), 1.5f));
    static const char *bad[] = {"", "1001", "abc", "-100", "50%"};   // invalid percents: the game's value (level 1: start 50)
    for (unsigned k = 0; k < sizeof bad / sizeof *bad; k++) {
        setenv("DM_OOT_FOG_START_PCT", bad[k], 1);
        setenv("DM_OOT_FOG_DENSITY", bad[k], 1);
        setenv("DM_OOT_FOG_ATTEN", bad[k], 1);
        gate(21);
        assert(near_(f(S_SCATTER_NEAR), 50) && f(S_SCATTER_DENSITY) == 0.5f && f(S_SCATTER_ATTEN) == 30);
    }
    setenv("DM_OOT_FOG_START_PCT", "91", 1);   // a start at or past the full point is refused
    gate(19);
    assert(near_(f(S_SCATTER_NEAR), 50));
    setenv("DM_OOT_FOG_START_PCT", "0", 1);
    setenv("DM_OOT_FOG_DENSITY", "1000", 1);
    gate(19);
    assert(f(S_SCATTER_NEAR) == 0 && near_(f(S_SCATTER_FAR), 95) && near_(f(S_SCATTER_DENSITY), 5));
    set("1", NULL);   // no cut: density, atten and the distances are the game's, whatever the strength switches say
    gate(19);
    assert(f(S_SCATTER_DENSITY) == 0.5f && f(S_SCATTER_ATTEN) == 30 && f(S_SCATTER_NEAR) == 0 && f(S_SCATTER_FAR) == 12000);
    unsetenv("DM_OOT_FOG_START_PCT"); unsetenv("DM_OOT_FOG_DENSITY"); unsetenv("DM_OOT_FOG_ATTEN");

    // The levels: Medium (35 %, density x3), Strong (20 %, density and atten x3); repeated gates never compound; a valid override wins over the level's number
    set("2", "100");
    for (int rep = 0; rep < 20; rep++) { gate(19); gate(21); }
    assert(near_(f(S_SCATTER_NEAR), 35) && near_(f(S_ADHOC_NEAR), 35) && near_(f(S_SCATTER_FAR), 95));
    assert(near_(f(S_SCATTER_DENSITY), 1.5f) && f(S_SCATTER_ATTEN) == 30);
    set("3", "100");
    for (int rep = 0; rep < 20; rep++) { gate(21); gate(19); }
    assert(near_(f(S_SCATTER_NEAR), 20) && near_(f(S_SCATTER_DENSITY), 1.5f) && near_(f(S_SCATTER_ATTEN), 90));
    setenv("DM_OOT_FOG_START_PCT", "60", 1);
    setenv("DM_OOT_FOG_DENSITY", "100", 1);
    gate(19);
    assert(near_(f(S_SCATTER_NEAR), 60) && f(S_SCATTER_DENSITY) == 0.5f && near_(f(S_SCATTER_ATTEN), 90));
    unsetenv("DM_OOT_FOG_START_PCT"); unsetenv("DM_OOT_FOG_DENSITY");
    set("2", "100");   // Strong to Medium, live: atten back to the game's
    gate(19);
    assert(near_(f(S_SCATTER_NEAR), 35) && f(S_SCATTER_ATTEN) == 30);
    set("3", "100");
    gate(19);
    set("0", "100");   // off: every field the game's
    gate(21);
    assert(f(S_SCATTER_NEAR) == 0 && f(S_SCATTER_FAR) == 12000 && f(S_ADHOC_NEAR) == 10 && f(S_ADHOC_FAR) == 2000 && f(S_SCATTER_DENSITY) == 0.5f && f(S_SCATTER_ATTEN) == 30);
    set("3", "100");
    gate(19);
    set("7", "100");   // an invalid level: off, restored
    gate(19);
    assert(f(S_SCATTER_NEAR) == 0 && f(S_SCATTER_DENSITY) == 0.5f && f(S_SCATTER_ATTEN) == 30);

    // A fog the game did not make (far not beyond near, out of range) is left alone
    setf(S_SCATTER_NEAR, 500); setf(S_SCATTER_FAR, 400);
    set("1", "100");
    gate(19);
    assert(f(S_SCATTER_NEAR) == 500 && f(S_SCATTER_FAR) == 400);
    assert(near_(f(S_ADHOC_FAR), 95));

    // No manager, an unaligned one, no sky, a register no gate names: nothing read or written
    uint64_t r[31] = {0};
    callbacks[OBS_OOT_FOG](r, 19);
    r[19] = (uintptr_t)g_mgr + 4; callbacks[OBS_OOT_FOG](r, 19);
    memset(g_mgr + M_SKY, 0, 8);
    r[19] = (uintptr_t)g_mgr; callbacks[OBS_OOT_FOG](r, 19);
    callbacks[OBS_OOT_FOG](r, 31);
}

static void other_build(void) {
    g_nmod = 1;
    strcpy(g_mod[0].name, "main");
    strcpy(g_mod[0].build_id, OOT_FOG_BUILD);
    g_mod[0].build_id[0] = '0';
    make();
    set("1", "100");
    gate(19);
    assert(f(S_SCATTER_FAR) == 15000 && f(S_ADHOC_FAR) == 300);
}

static int in_child(void (*fn)(void)) {
    pid_t p = fork();
    if (p == 0) { fn(); _exit(0); }
    int st;
    waitpid(p, &st, 0);
    return WIFEXITED(st) && WEXITSTATUS(st) == 0;
}

int main(void) {
    assert(callbacks[OBS_OOT_FOG]);
    assert(in_child(cases));
    assert(in_child(other_build));
    printf("t_oot_fog: ok\n");
    return 0;
}
