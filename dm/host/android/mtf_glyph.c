// SPDX-License-Identifier: MIT
// Mario Tennis Fever (Switch 2), nro0 of 1.1.1 (build ID 250a510a934129cb38e930c9a29082b6): no glyph is lost on a frame the game does not draw.
//
// The font cache rasterizes a new glyph on the CPU (worker nro0+0x11de140), marks it resident and pushes its dirty rect into a ring (glyph context +0x2088; write index +0x1c088,
// read index +0x1c08c). A deferred callback, nro0+0x11deac0, runs inside the frame function's item loop (nro0+0x11f909c / 0x11f9134), records the compute pass that copies the rects
// into the glyph textures into the frame's command buffer (renderctx+0x5b8), and at its end marks the ring consumed (nro0+0x11ded28: read index = write index). The frame function
// submits that command buffer only when the draw flag (nro0+0x17999bc) is 1 (nro0+0x11f9334). The flag is 0 on every other frame under the game's half-rate mode (flag 15, which
// fps_half_draw sets for a 30 fps cap: hle_fpslock.c), so the rects consumed on those frames never reached the GPU and their letters stayed blank for good (#302).
//
// The gate (patches.py OBS row, kind OBS_MTF_GLYPH) sits on that store, `str w8, [x26, #4]` at nro0+0x11ded2c (x26 = the ring's indices, w8 = the write index). On a frame whose
// draw flag is 0 it writes the read index into w8, so the store leaves the ring as it was: the upload recorded into the frame's buffer is dropped with that buffer, the rects stay
// pending, and the next drawn frame's callback uploads them. The flag is read here, inside the frame being recorded, so it is the value the submit reads later in the same frame.
// Two other changes were tried and failed: submitting the undrawn frame's buffer (on the first frames after a loading screen it is not a valid command list; the host crashed
// replaying it), and gating the producer that enqueues the callback (nro0+0x11ddfb0; letters were still lost: it runs one frame before the frame that drains its entry, so its
// flag is the other frame's). Gate frame (entry.S dm_gate): x0..x30 at r[0..30].
#include "hle.h"
#include "dm.h"
#include <stdatomic.h>
#include <string.h>

#define MTF_GLYPH_BUILD "250a510a934129cb38e930c9a29082b6"
enum { M_FLAG = 0x17999bc, M_FLAG_GOT = 0x1760c20 };   // nro0 offsets: the draw flag and its GOT slot

static _Atomic int g_ok = -1;   // -1 not checked yet, 0 another build or layout (the gate does nothing), 1 nro0 1.1.1
static uintptr_t g_base;
static _Atomic uint64_t g_kept, g_seen;
static int build_ok(void) {
    int v = g_ok;
    if (v >= 0) return v;
    v = 0;
    for (int i = 0; i < g_nmod; i++) if (g_mod[i].nro && !strcmp(g_mod[i].name, "nro0") && !strcmp(g_mod[i].build_id, MTF_GLYPH_BUILD)) g_base = (uintptr_t)g_mod[i].base;
    uint64_t got = 0;
    if (g_base) memcpy(&got, (const void *)(g_base + M_FLAG_GOT), 8);
    if (!g_base) LOG("[RED] mtf glyph: the gate ran outside nro0 1.1.1 (%s): glyph uploads are not held for drawn frames", MTF_GLYPH_BUILD);
    else if (got != g_base + M_FLAG) LOG("[RED] mtf glyph: nro0's GOT does not point at the draw flag (%#llx): glyph uploads are not held for drawn frames", (unsigned long long)(got - g_base));
    else v = 1;
    g_ok = v;
    return v;
}

static void mtf_glyph_gate(uint64_t *r, int param) {
    (void)param;
    if (!build_ok()) return;
    atomic_fetch_add(&g_seen, 1);
    if (__atomic_load_n((const uint8_t *)(g_base + M_FLAG), __ATOMIC_RELAXED)) return;
    uint32_t rd; memcpy(&rd, (const void *)(uintptr_t)(r[26] + 4), 4);
    r[8] = rd;   // the store writes the read index back: the ring keeps its rects for the next drawn frame
    uint64_t k = atomic_fetch_add(&g_kept, 1) + 1;
    if (k == 1 || !(k & (k - 1))) LOG("[mtf glyph] glyph uploads held for a drawn frame: %llu of %llu (the frame's draw flag was 0)", (unsigned long long)k, (unsigned long long)atomic_load(&g_seen));
}
__attribute__((constructor)) static void mtf_glyph_attach(void) { gate_obs_set(OBS_MTF_GLYPH, mtf_glyph_gate); }
