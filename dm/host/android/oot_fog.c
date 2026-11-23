// SPDX-License-Identifier: MIT
// The Legend of Zelda: Ocarina of Time (Switch 2), main v131072 (build ID e0f3ccfaf50065ae4ea01eb5aeb13b1a): the game's own distance fog pulled in to the draw distance
// (DM_OOT_FOG_AT_CUT), so the far-plane cap of DM_OOT_DRAW_DISTANCE (oot_wide.c far_fix) ends in haze instead of a hard horizon.
//
// Where the game keeps its fog. agl's sky (the graphics scene manager's main sky at [manager+0xc98], the cube-map capture's at +0xca0; flags at sky+0xbc0) holds two distance
// fogs as agl::utl::Parameter<float> values (parameter at P, value at P+0x18; names from its constructor around main+0xcdc5f4):
//   scatter fog (the atmospheric scattering haze, coloured by the sky): scatter_fog_near +0x880, scatter_fog_far +0x8a0, density +0x8c0, atten +0x8e0, horz +0x900;
//   adhoc fog (a coloured linear fog): adhoc_fog_near +0x920, adhoc_fog_far +0x940, atten_grd +0x960, atten_sky +0x980, atten_minscale_sky +0x9a0, colour RGBA +0x9c0..+0x9cc.
// Their data is agl/SkyParam (gsys/EnvSetParam's Sky; MainField: ScatterFogNear 0, ScatterFogFar 15000, Density 0.85, Atten 30, Horz 2.5; AdhocFogNear 0, AdhocFogFar 300,
// AdhocFogColor alpha 0), copied into the sky by the parameter mirror (main+0xee4d64 and its siblings) and rewritten by the game's environment update main+0x3ba7d0 (time of
// day and area blends, which store all four distances straight into the sky). Both fogs are linear in view distance: the scene manager's per-frame view update main+0x474700
// writes 1 / (far - near) and near / (far - near) of each into the view's constant block (+0x600 / +0x604 scatter, +0x620 / +0x624 adhoc, colour at +0x640), and the sky's
// own constants (main+0x285e20, from the scene draw at main+0x6428d8 with the camera's near and far) hold the same terms over the camera's depth range. So the GPU reads them
// from constant buffers the game fills each frame from these four floats: no shader change is needed to move the fog.
//
// The lever. Two observation gates (patches.py OBS rows, OBS_OOT_FOG; the register that holds the scene manager in the parameter bits 0-4) sit where the manager loads its
// sky before each of those two consumers: the view update (main+0x4747dc, x19) and the scene draw (main+0x6428a4, x21). With DM_OOT_FOG_AT_CUT=<1..3> and DM_OOT_DRAW_DISTANCE=d set,
// a fog that ends beyond 0.95 d is moved to fade in from the level's start (0.50, 0.35 or 0.20 d) and be full at 0.95 d, just inside the clip at near + d: the cut is hidden by the game's own fog in its own colour
// (scatter: the sky's horizon haze; adhoc: its colour, which is invisible where its alpha is 0, as in the fields). A fog that already ends nearer stays as the game made it, and
// colour stays the game's. DM_OOT_FOG_AT_CUT is a level (1 Light, 2 Medium, 3 Strong; k_levels below) that sets the strength; developer overrides, which win when valid (all
// read at every gate, used only while the cut is set): DM_OOT_FOG_START_PCT=<0..90> moves the fade's start (a percent of d), DM_OOT_FOG_DENSITY=<10..1000> and DM_OOT_FOG_ATTEN=<10..1000> scale the scatter fog's density (+0x8c0) and attenuation (+0x8e0) by that percent of the game's value
// (100 or unset: the game's). How the shader uses them is not read (the translated shaders were not decompiled): the CPU passes both through unchanged, density clamped at 0
// (view block +0x618, sky constants at its +0x104) and atten raised to a tiny minimum (+0x610: a divisor or exponent, never 0); the editor labels are "fog density" (Min 0,
// Max 1: likely the haze's opacity at the far end, so above 1 / 0.85 = 118 % it may saturate) and "attenuation (power)" (Min 0, Max 10; the field data has 30, the shape of the
// curve over near..far). The game's values are remembered (a value at a field that is not the one written here is the game's fresh value, so its
// time of day and area blends go on), and put back when the switch or the draw distance is unset. Read at every gate, so `nxctl.sh env` and the in-game panel change it live.
// A per-game rule: the host sees only constant buffers it cannot tell apart, not which floats are the fog.
#include "hle.h"
#include "dm.h"
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define OOT_FOG_BUILD "e0f3ccfaf50065ae4ea01eb5aeb13b1a"
enum { M_SKY = 0xc98, S_SCATTER_NEAR = 0x880, S_SCATTER_FAR = 0x8a0, S_ADHOC_NEAR = 0x920, S_ADHOC_FAR = 0x940 };
#define FOG_FULL 0.95f   // the fog is full here, a fraction of the draw distance (inside the clip at near + d)
#define FOG_FROM 80      // the start percent logged while off (the levels set their own)
enum { S_SCATTER_DENSITY = 0x8c0, S_SCATTER_ATTEN = 0x8e0 };

typedef struct { uint64_t at; float orig, wrote; } fog_kept_t;
static fog_kept_t g_kept[16];   // fields written: where, the game's value, the value written (a ring: a sky that went away gives its slots up)
static unsigned g_kept_next;
static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;
static _Atomic int g_build_ok = -1;   // -1 not checked yet, 0 another main build, 1 main v131072
static unsigned g_logged;             // under g_lock: lines logged, with the switches last logged
static uint64_t g_logged_key = UINT64_MAX;

static float rd(uint64_t a) { float v; memcpy(&v, (void *)(uintptr_t)a, 4); return v; }
static void wr(uint64_t a, float v) { memcpy((void *)(uintptr_t)a, &v, 4); }
static uint32_t bits(float v) { uint32_t u; memcpy(&u, &v, 4); return u; }

// DM_OOT_FOG_AT_CUT's levels (phone sweep at draw distance 100, system driver): start percent, scatter density and atten percent of the game's. Light: the haze starts at half the
// distance (80 was barely visible). Medium: density x3 (clearly hazier; x10 looked no hazier, it saturates). Strong: also atten x3, which turned the far hills a bluish aerial haze
typedef struct { int start, density, atten; } fog_level_t;
static const fog_level_t k_levels[4] = {{0, 0, 0}, {50, 100, 100}, {35, 300, 100}, {20, 300, 300}};
static _Atomic int g_bad_logged;
// The level: 0 off (unset, empty or 0), 1..3; any other value is off, logged once
static int fog_level(void) {
    const char *e = getenv("DM_OOT_FOG_AT_CUT");
    if (!e || !*e || !strcmp(e, "0")) return 0;
    if (e[0] >= '1' && e[0] <= '3' && !e[1]) return e[0] - '0';
    if (!atomic_exchange_explicit(&g_bad_logged, 1, memory_order_relaxed)) LOG("[RED] oot fog: DM_OOT_FOG_AT_CUT=%s is not 0..3; fog at the cut off", e);
    return 0;
}
// DM_OOT_DRAW_DISTANCE as oot_wide.c reads it: 0 when unset or invalid (no cap, so no fog change)
static float cut_distance(void) {
    const char *e = getenv("DM_OOT_DRAW_DISTANCE");
    if (!e || !*e) return 0;
    char *end;
    double v = strtod(e, &end);
    if (*end || !(v >= 10 && v <= 20000)) return 0;
    return (float)v;
}

// A percent switch: def when unset or outside lo..hi
static int pct_env(const char *name, int lo, int hi, int def) {
    const char *e = getenv(name);
    if (!e || !*e) return def;
    char *end;
    long v = strtol(e, &end, 10);
    return *end || v < lo || v > hi ? def : (int)v;
}

static fog_kept_t *kept(uint64_t at) {
    for (unsigned i = 0; i < sizeof g_kept / sizeof *g_kept; i++) if (g_kept[i].at == at) return &g_kept[i];
    return NULL;
}
// The game's value of a field: what is there, unless it is the value written here (then the one it replaced)
static float game_value(uint64_t at) {
    float cur = rd(at);
    fog_kept_t *e = kept(at);
    if (!e) return cur;
    if (bits(cur) != bits(e->wrote)) e->orig = cur;   // the game wrote a fresh value
    return e->orig;
}
static void put(uint64_t at, float v, float game) {
    fog_kept_t *e = kept(at);
    if (!e) {
        if (bits(v) == bits(game)) return;   // never written and nothing to write
        e = &g_kept[g_kept_next++ % (sizeof g_kept / sizeof *g_kept)];
        e->at = at;
        e->orig = game;
    }
    if (bits(rd(at)) != bits(v)) wr(at, v);
    e->wrote = v;
}
// One fog's near and far: the game's own, or pulled in to the cut when it ends beyond it. Returns whether it was moved
static int fog_pair(uint64_t sky, int near_off, int far_off, float d, int from, float *gn, float *gf) {
    float n = game_value(sky + near_off), f = game_value(sky + far_off), nn = n, nf = f;
    *gn = n; *gf = f;
    int ok = n >= -5000.0f && n < f && f < 1e7f;   // the parameter's own range (Min -5000), and a fog the game made
    if (ok && d > 0 && f > d * FOG_FULL) { nf = d * FOG_FULL; nn = d * (float)from / 100.0f; }
    put(sky + near_off, nn, n);
    put(sky + far_off, nf, f);
    return nf != f;
}
// One scatter term scaled by pct % of the game's value (100: the game's); returns the game's value
static float fog_scale(uint64_t at, int pct) {
    float g = game_value(at), v = g;
    if (pct != 100 && g >= 0.0f && g < 1e6f) v = g * (float)pct / 100.0f;
    put(at, v, g);
    return g;
}

static void oot_fog_gate(uint64_t *r, int param) {
    int reg = param & 31;
    if (reg > 28) return;
    int ok = g_build_ok;
    if (ok < 0) {
        ok = !strcmp(dm_main_build(), OOT_FOG_BUILD);
        if (!ok) LOG("[RED] oot fog: the gate ran outside main %s; the game's own fog", OOT_FOG_BUILD);
        g_build_ok = ok;
    }
    if (!ok) return;
    uint64_t mgr = r[reg], sky = 0;
    if (!mgr || (mgr & 7)) return;
    memcpy(&sky, (void *)(uintptr_t)(mgr + M_SKY), 8);
    if (!sky || (sky & 7)) return;
    int lv = fog_level();
    float d = lv ? cut_distance() : 0;
    const fog_level_t *L = &k_levels[lv];   // the developer switches, when valid, win over the level's numbers
    int from = d ? pct_env("DM_OOT_FOG_START_PCT", 0, 90, L->start) : FOG_FROM;
    int dens = d ? pct_env("DM_OOT_FOG_DENSITY", 10, 1000, L->density) : 100, att = d ? pct_env("DM_OOT_FOG_ATTEN", 10, 1000, L->atten) : 100;
    uint64_t key = (uint64_t)d << 40 | (uint64_t)from << 24 | (uint64_t)dens << 12 | (uint64_t)att;   // what the log line shows changed
    pthread_mutex_lock(&g_lock);
    if (d || kept(sky + S_SCATTER_FAR) || kept(sky + S_ADHOC_FAR) || kept(sky + S_SCATTER_NEAR) || kept(sky + S_ADHOC_NEAR) || kept(sky + S_SCATTER_DENSITY) ||
        kept(sky + S_SCATTER_ATTEN)) {   // nothing to do until the switch is first used
        float sn, sf, an, af;
        int ms = fog_pair(sky, S_SCATTER_NEAR, S_SCATTER_FAR, d, from, &sn, &sf);
        int ma = fog_pair(sky, S_ADHOC_NEAR, S_ADHOC_FAR, d, from, &an, &af);
        float gd = fog_scale(sky + S_SCATTER_DENSITY, dens), ga = fog_scale(sky + S_SCATTER_ATTEN, att);
        if (g_logged < 32 && key != g_logged_key) {   // the first use and every change of the switches
            g_logged++;
            g_logged_key = key;
            LOG("oot fog: draw distance %.0f%s: scatter fog %.1f..%.1f%s, adhoc fog %.1f..%.1f%s (colour alpha %.2f); start %d %%, scatter density %.3f -> %.3f, atten %.3f -> %.3f",
                d, d ? "" : " (off: the game's own)", sn, sf, ms ? " -> pulled to the cut" : "", an, af, ma ? " -> pulled to the cut" : "", rd(sky + 0x9cc), from, gd,
                rd(sky + S_SCATTER_DENSITY), ga, rd(sky + S_SCATTER_ATTEN));
        }
    }
    pthread_mutex_unlock(&g_lock);
}

__attribute__((constructor)) static void oot_fog_attach(void) { gate_obs_set(OBS_OOT_FOG, oot_fog_gate); }
