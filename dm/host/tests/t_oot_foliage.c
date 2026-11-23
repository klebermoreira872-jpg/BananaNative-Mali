// Ocarina of Time foliage distance gate (android/oot_foliage.c): unset, 100 and invalid values leave the game's own load; a percent scales the value the load reads through a copy,
// the game's object is never written (repeated gates do not accumulate), the value follows the switch live, and another main build does nothing (its own process: checked once).
#include "../android/oot_foliage.c"
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

static const int FIELDS[6] = {F_UNDERGROWTH0, F_UNDERGROWTH1, F_ORNAMENT, F_SHOOTLEAF, F_LOWTREE, F_LOWTREE_SHADOW};   // the six gates' parameters (patches.py)

// A LodSetting as the constructor and a scene file leave it (the defaults, Dist_Ornament 75 as in the field scenes)
static void make(unsigned char *o) {
    memset(o, 0, 0x68);
    const float v[9] = {135, 40, 30, 75, 40, 60, 10, 45, 0.3f};
    memcpy(o + 0x38, v, sizeof v);
}

// The gate on the load `ldr sN, [x19, #f]`, then the load itself: what the game reads
static float load(unsigned char *o, int f) {
    uint64_t r[31] = {0};
    r[19] = (uintptr_t)o;
    r[20] = 0x1234;
    callbacks[OBS_OOT_FOLIAGE](r, f);
    assert(r[20] == 0x1234);   // only x19 may change
    float v;
    memcpy(&v, (void *)(uintptr_t)(r[19] + (unsigned)f), 4);
    return v;
}

static void cases(void) {
    _Alignas(16) unsigned char o[0x68], before[0x68];
    g_nmod = 1;
    strcpy(g_mod[0].name, "main");
    strcpy(g_mod[0].build_id, OOT_FOLIAGE_BUILD);
    make(o);
    memcpy(before, o, sizeof o);
    float game[6];
    for (int i = 0; i < 6; i++) memcpy(&game[i], o + FIELDS[i], 4);

    static const char *own[] = {NULL, "", "100", "abc", "24", "201", "50x", "-50", "0"};   // the game's own value, the object untouched
    for (unsigned k = 0; k < sizeof own / sizeof *own; k++) {
        if (own[k]) setenv("DM_OOT_FOLIAGE_DISTANCE", own[k], 1); else unsetenv("DM_OOT_FOLIAGE_DISTANCE");
        for (int i = 0; i < 6; i++) assert(load(o, FIELDS[i]) == game[i]);
    }
    assert(!memcmp(before, o, sizeof o));

    setenv("DM_OOT_FOLIAGE_DISTANCE", "50", 1);
    for (int rep = 0; rep < 100; rep++)   // every frame, every view: the same scaled value, never compounded
        for (int i = 0; i < 6; i++) assert(fabsf(load(o, FIELDS[i]) - game[i] * 0.5f) < 1e-4f);
    assert(!memcmp(before, o, sizeof o));
    assert(load(o, F_LOWTREE) > load(o, F_SHOOTLEAF) + 0.01f);   // the order the update checks holds

    setenv("DM_OOT_FOLIAGE_DISTANCE", "25", 1);   // a live change takes effect at the next load
    assert(fabsf(load(o, F_ORNAMENT) - 75 * 0.25f) < 1e-4f);
    setenv("DM_OOT_FOLIAGE_DISTANCE", "200", 1);
    assert(fabsf(load(o, F_LOWTREE) - 270) < 1e-3f);

    // The game writes a new scene's values: they are what is scaled
    float lt = 90;
    memcpy(o + F_LOWTREE, &lt, 4);
    setenv("DM_OOT_FOLIAGE_DISTANCE", "50", 1);
    assert(fabsf(load(o, F_LOWTREE) - 45) < 1e-4f);

    // No distance the game made, a null or unaligned object, a parameter that is no gate's: the load as it was
    float bad = -1;
    memcpy(o + F_ORNAMENT, &bad, 4);
    assert(load(o, F_ORNAMENT) == -1);
    uint64_t r[31] = {0};
    callbacks[OBS_OOT_FOLIAGE](r, F_LOWTREE); assert(r[19] == 0);
    r[19] = (uintptr_t)o + 1; callbacks[OBS_OOT_FOLIAGE](r, F_LOWTREE); assert(r[19] == (uintptr_t)o + 1);
    r[19] = (uintptr_t)o; callbacks[OBS_OOT_FOLIAGE](r, 0x50); assert(r[19] == (uintptr_t)o);
    callbacks[OBS_OOT_FOLIAGE](r, 0x3a); assert(r[19] == (uintptr_t)o);
    callbacks[OBS_OOT_FOLIAGE](r, -1); assert(r[19] == (uintptr_t)o);
}

static void other_build(void) {
    _Alignas(16) unsigned char o[0x68];
    g_nmod = 1;
    strcpy(g_mod[0].name, "main");
    strcpy(g_mod[0].build_id, OOT_FOLIAGE_BUILD);
    g_mod[0].build_id[0] = '0';
    make(o);
    setenv("DM_OOT_FOLIAGE_DISTANCE", "50", 1);
    for (int i = 0; i < 6; i++) { float v; memcpy(&v, o + FIELDS[i], 4); assert(load(o, FIELDS[i]) == v); }
}

static int in_child(void (*fn)(void)) {
    pid_t p = fork();
    if (p == 0) { fn(); _exit(0); }
    int st;
    waitpid(p, &st, 0);
    return WIFEXITED(st) && WEXITSTATUS(st) == 0;
}

int main(void) {
    assert(callbacks[OBS_OOT_FOLIAGE]);
    assert(in_child(cases));
    assert(in_child(other_build));
    printf("t_oot_foliage: ok\n");
    return 0;
}
