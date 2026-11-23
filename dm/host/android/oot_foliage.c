// SPDX-License-Identifier: MIT
// The Legend of Zelda: Ocarina of Time (Switch 2), main v131072 (build ID e0f3ccfaf50065ae4ea01eb5aeb13b1a): the foliage draw distances scaled (DM_OOT_FOLIAGE_DISTANCE).
//
// Where the game reads them. Each scene's Foliage/ResFoliageScene (game__foliage__ResFoliageScene, an engine reflection object; constructor main+0xe33c90) points at two
// LodSetting objects, docked at +0x40 and handheld (LodSetting_hh) at +0x48 (field visitors main+0x2be8ed0 / +0x2be90b0). A LodSetting (0x68 bytes, constructor main+0xfea770,
// field visitors main+0x2bed300 / +0x2bed940) keeps floats: Dist_LowTree +0x38 (default 135), Dist_LowTreeShadow +0x3c (40), Dist_LowTreeShootLeaf +0x40 (30),
// Dist_Ornament +0x44 (35; 75 in the field scenes), Dist_Undergrowth0 +0x48 (40), Dist_Undergrowth1 +0x4c (60), Range_LowTree01 +0x50, Range_LowTree12 +0x54, Turf_1PolyLen
// +0x58; one "set" byte a field at +0x5c.. (+0x5c Undergrowth0 .. +0x64 Turf_1PolyLen, the visitor's order). A field whose byte is clear is taken from the parent resource
// (+0x10 / +0x18, the .gyml's $parent), as the getters do (main+0x2bedd60 for Dist_Ornament). The one consumer is the foliage system's per-frame, per-view update
// main+0x567c80 (called by main+0x5679e0 with the frame counter and the time; the scene object at [x0+0x2a90]+0x150): it picks LodSetting or LodSetting_hh (main+0x567f18,
// by the operation mode), resolves each field through its parent chain with inlined getters, and loads the float with `ldr sN, [x19, #field]`, x19 the object that holds it:
//   main+0x568be8 Dist_Undergrowth0, +0x568c04 Dist_Undergrowth1, +0x569228 Dist_Ornament, +0x569244 Dist_LowTreeShootLeaf, +0x569260 Dist_LowTree, +0x56927c Dist_LowTreeShadow.
// The values go into the view's foliage constants (the stack block at +0x2d8.. and +0x15c..), which the GPU's foliage culling reads; no other code reads these fields
// (the getters are called only by the visitors, and the inlined getter pattern occurs only in this function).
//
// The lever. Six observation gates (patches.py OBS rows, OBS_OOT_FOLIAGE, the field offset in the parameter bits) sit on those loads. With DM_OOT_FOLIAGE_DISTANCE=<25..200>
// (percent of the game's own distances), the callback reads the game's value from [x19 + field], writes value * percent / 100 into a thread-local copy at the same offset and
// points x19 at the copy, so the load reads the scaled value. The game's objects are never written, so nothing accumulates and every frame starts from the game's own value.
// x19 is not read again after any of the six loads before it is written (checked by disassembly on every path), so the pointer to the copy does not leak. Read at every gate,
// so the in-game panel's slider or `nxctl.sh env` changes it live, from the next frame; unset, 100 or a value outside 25..200 leaves the game's own. All six fields are scaled by one
// factor, so the order the update checks (Dist_LowTree above Dist_LowTreeShootLeaf) holds. The LOD ranges (Range_LowTree01 / 12) and the turf parameters stay the game's.
#include "hle.h"
#include "dm.h"
#include <stdatomic.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define OOT_FOLIAGE_BUILD "e0f3ccfaf50065ae4ea01eb5aeb13b1a"
enum { F_LOWTREE = 0x38, F_LOWTREE_SHADOW = 0x3c, F_SHOOTLEAF = 0x40, F_ORNAMENT = 0x44, F_UNDERGROWTH0 = 0x48, F_UNDERGROWTH1 = 0x4c, F_END = 0x50 };

static _Thread_local _Alignas(16) float t_lod[F_END / 4];   // the scaled copy: [field / 4] the value the next load reads
static _Atomic int g_build_ok = -1;                           // -1 not checked yet, 0 another main build, 1 main v131072
static _Atomic unsigned g_logged;                             // fields logged at the current percent (bit field / 4 - 14)
static _Atomic int g_logged_pct;

static int foliage_pct(void) {
    const char *e = getenv("DM_OOT_FOLIAGE_DISTANCE");
    if (!e || !*e) return 100;
    char *end;
    long v = strtol(e, &end, 10);
    if (*end || v < 25 || v > 200) return 100;   // not a number, or outside what the slider offers: the game's own
    return (int)v;
}

static const char *field_name(int f) {
    switch (f) {
    case F_LOWTREE: return "Dist_LowTree";
    case F_LOWTREE_SHADOW: return "Dist_LowTreeShadow";
    case F_SHOOTLEAF: return "Dist_LowTreeShootLeaf";
    case F_ORNAMENT: return "Dist_Ornament";
    case F_UNDERGROWTH0: return "Dist_Undergrowth0";
    default: return "Dist_Undergrowth1";
    }
}

static void oot_foliage_gate(uint64_t *r, int param) {
    int f = param;
    if (f < F_LOWTREE || f >= F_END || (f & 3)) return;
    int pct = foliage_pct();
    if (pct == 100) return;
    int ok = g_build_ok;
    if (ok < 0) {
        ok = !strcmp(dm_main_build(), OOT_FOLIAGE_BUILD);
        if (!ok) LOG("[RED] oot foliage: the gate ran outside main %s; the game's own distances", OOT_FOLIAGE_BUILD);
        g_build_ok = ok;
    }
    if (!ok) return;
    uint64_t obj = r[19];
    if (!obj || (obj & 3)) return;
    float v;
    memcpy(&v, (void *)(uintptr_t)(obj + (unsigned)f), 4);
    if (!(v > 0.0f && v < 100000.0f)) return;   // no distance the game made
    float nv = v * (float)pct / 100.0f;
    t_lod[f / 4] = nv;
    r[19] = (uint64_t)(uintptr_t)t_lod;
    if (atomic_exchange_explicit(&g_logged_pct, pct, memory_order_relaxed) != pct) atomic_store_explicit(&g_logged, 0, memory_order_relaxed);
    unsigned bit = 1u << (f / 4 - F_LOWTREE / 4);
    if (!(atomic_fetch_or_explicit(&g_logged, bit, memory_order_relaxed) & bit))
        LOG("oot foliage: %s %.1f -> %.1f (%d %%)", field_name(f), v, nv, pct);
}

__attribute__((constructor)) static void oot_foliage_attach(void) { gate_obs_set(OBS_OOT_FOLIAGE, oot_foliage_gate); }
