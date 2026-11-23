// SPDX-License-Identifier: MIT
// The Legend of Zelda: Ocarina of Time (Switch 2), main v131072 (build ID e0f3ccfaf50065ae4ea01eb5aeb13b1a): the dynamic shadow's range (DM_OOT_SHADOW_RANGE).
//
// The scene's cascaded depth shadow (agl's DepthShadow, one per view) keeps its cascade count at +0x250 and, at +0x330, a pointer to its split distances: n + 1 floats, cascade i
// covering the view's slice from split[i] to split[i + 1] (view distance, game units, about metres). Every frame the view update (main+0x711040) copies them from the scene's config
// (the param object's depth_shadow_near_0_<i> at +0x1db8 + 0x20 * i and depth_shadow_far_0 at +0x1e38; from Main.gsys__ModelSceneConfigParam: DepthShadowCascadeNum0 3,
// DepthShadowNear00..02 2, 32, 64, DepthShadowFar0 3000) unless the view's flag bit 1 at +0x234 says the game set them itself, and calls the cascade fit (main+0x712f40) that fits
// each cascade's light-space box to its slice (main+0x713120) and stores its near and far. So the last of the three 1000x1000 depth maps covers 64..3000 m, although the gameplay scenes'
// shadow pre-pass fades the dynamic shadow out from 80 to 200 m (MainField.agl__ShadowPrePassParam DynamicShadowFarFadeStart / End; the far static shadow map takes over): most of
// what that cascade draws is never seen, and its texels are spread over a 3 km slice.
//
// The gate (patches.py OBS row, OBS_OOT_SHADOW) sits on the cascade fit's first load (main+0x712f60, `ldr w8,[x0,#0x250]`; x0 the depth shadow), after this frame's copy and before
// anything reads the splits. DM_OOT_SHADOW_RANGE=<10..20000> caps the last split at that distance; an inner split that would no longer fit below it is pulled down to its share of
// the range (split[0] + (range - split[0]) * i / n), so the splits stay increasing. Read at every fit, so the in-game panel / `nxctl.sh env` changes it live; unset, 0, or a range at or
// beyond the game's own last split leaves the game's values. Where the game does not copy the splits each frame (its flag), the values we wrote stay: a table of what was written
// gives the game's own values back for a new range or for none, so nothing accumulates.
//
// A per-game rule: the host sees only the depth passes' draws, not which slice an object belongs to; the split array is agl's (one engine, several titles) but its offsets and the
// gate are this build's (BINDING in patches.py).
#include "hle.h"
#include "dm.h"
#include <math.h>
#include <pthread.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define OOT_MAIN_BUILD "e0f3ccfaf50065ae4ea01eb5aeb13b1a"
enum { DS_NUM = 0x250, DS_SPLITS = 0x330, DS_MAXNUM = 0x388, SH_MAX = 4, SH_NSEEN = 16 };

// Depth shadows whose splits we wrote: the game's own values and ours (n + 1 each)
typedef struct { uint64_t ds; int n; float orig[SH_MAX + 1], wrote[SH_MAX + 1]; } sh_seen_t;
static sh_seen_t g_seen[SH_NSEEN];
static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;
static float g_logged_range = -1, g_logged_last = -1;   // the last range and game split logged (under g_lock): each new pair is logged once
static unsigned g_nlogged;

static float rdf(uint64_t a) { float f; memcpy(&f, (void *)(uintptr_t)a, 4); return f; }
static void wrf(uint64_t a, float f) { memcpy((void *)(uintptr_t)a, &f, 4); }

static double shadow_range(void) {
    const char *e = getenv("DM_OOT_SHADOW_RANGE");
    if (!e || !*e) return 0;
    char *end;
    double v = strtod(e, &end);
    if (*end || !(v >= 10 && v <= 20000)) return 0;   // not a number, or shorter than the player's own surroundings
    return v;
}

// The splits a range leaves: the last capped, an inner one pulled down to its share where it would not fit below the cap
static void shadow_splits(const float *src, int n, double range, float *out) {
    memcpy(out, src, (size_t)(n + 1) * sizeof *out);
    if (!range || src[n] <= range || range <= src[0]) return;
    out[n] = (float)range;
    for (int i = 1; i < n; i++) {
        float share = (float)(src[0] + (range - src[0]) * i / n);
        if (out[i] > share) out[i] = share;
    }
}

static int same(const float *a, const float *b, int n) { return !memcmp(a, b, (size_t)(n + 1) * sizeof *a); }

static void fit(uint64_t ds) {
    if (!ds || (ds & 7)) return;
    int n = 0, max = 0;
    uint64_t sp = 0;
    memcpy(&n, (void *)(uintptr_t)(ds + DS_NUM), 4);
    memcpy(&max, (void *)(uintptr_t)(ds + DS_MAXNUM), 4);
    memcpy(&sp, (void *)(uintptr_t)(ds + DS_SPLITS), 8);
    if (n < 1) n = 1;   // as the fit clamps it: at least one cascade, at most the cascades made
    if (max < n) n = max;
    if (n < 1 || n > SH_MAX || !sp || (sp & 3)) return;
    float cur[SH_MAX + 1] = {0};
    for (int i = 0; i <= n; i++) {
        cur[i] = rdf(sp + 4 * (uint64_t)i);
        if (!isfinite(cur[i]) || cur[i] < 0 || cur[i] > 1e6f || (i && !(cur[i] > cur[i - 1]))) return;   // no splits the game made
    }
    double range = shadow_range();
    pthread_mutex_lock(&g_lock);
    sh_seen_t *s = NULL, *slot = NULL;
    for (int k = 0; k < SH_NSEEN; k++) {
        if (g_seen[k].ds == ds) s = &g_seen[k];
        else if (!g_seen[k].ds && !slot) slot = &g_seen[k];
    }
    const float *src = s && s->n == n && same(cur, s->wrote, n) ? s->orig : cur;   // still our values: the game's own are the ones we kept
    float out[SH_MAX + 1] = {0};
    shadow_splits(src, n, range, out);
    if (g_nlogged < 32 && ((float)range != g_logged_range || src[n] != g_logged_last)) {
        g_nlogged++; g_logged_range = (float)range; g_logged_last = src[n];
        char a[96] = "", b[96] = "";
        for (int i = 0, la = 0, lb = 0; i <= n; i++) { la += snprintf(a + la, sizeof a - la, " %.1f", src[i]); lb += snprintf(b + lb, sizeof b - lb, " %.1f", out[i]); }
        LOG("oot shadow: %d cascades, the game's splits%s -> %s (shadow range %.0f)", n, a, same(out, src, n) ? "kept" : b + 1, range);
    }
    if (!same(out, cur, n))
        for (int i = 0; i <= n; i++) wrf(sp + 4 * (uint64_t)i, out[i]);
    if (same(out, src, n)) {   // the game's own values in place: nothing to remember
        if (s) s->ds = 0;
    } else {
        if (!s) s = slot ? slot : &g_seen[(ds >> 4) % SH_NSEEN];
        s->ds = ds; s->n = n;
        memmove(s->orig, src, sizeof s->orig);
        memcpy(s->wrote, out, sizeof s->wrote);
    }
    pthread_mutex_unlock(&g_lock);
}

static void oot_shadow_gate(uint64_t *r, int param) {
    if (param < 0 || (param & 31) > 28) return;
    if (strcmp(dm_main_build(), OOT_MAIN_BUILD)) return;
    fit(r[param & 31]);
}

__attribute__((constructor)) static void oot_shadow_attach(void) { gate_obs_set(OBS_OOT_SHADOW, oot_shadow_gate); }
