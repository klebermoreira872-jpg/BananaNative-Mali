// SPDX-License-Identifier: GPL-3.0-or-later
// The Legend of Zelda: Ocarina of Time (Switch 2), main v131072 (build ID e0f3ccfaf50065ae4ea01eb5aeb13b1a): 3D cameras that follow the picture's shape.
//
// The game draws a 16:9 picture whatever the screen. Game settings › Aspect ratio shows the picture at another shape (DM_VK_PICTURE_ASPECT=<w>:<h>, vka_present.c): the
// game's 1920x1080 frame is fitted into that shape. For the scene to be neither stretched nor cropped, its cameras must use that ratio. Each sead::PerspectiveProjection keeps
// its own aspect at +0xb0 (copied from the camera at +0x140; the game's 16:9 constant is never read by the cameras), and the matrix updates read it with the half-angle's tangent
// at +0xac: m00 = 1 / (tan * aspect), m11 = 1 / tan. Culling reads the same fields. patches.py puts five observation gates (OBS_OOT_WIDE) on those reads; this callback rewrites
// the projection in place before the read:
//   wider than 16:9  (Hor+)  the aspect field becomes the picture's; the vertical field of view stays;
//   narrower         (Vert+) the aspect field becomes the picture's, and the half-angle's tangent grows by (16/9) / aspect, so the horizontal reach stays what a 16:9 picture
//                            shows (a square screen would show a thin slice of the world with Hor+). fovy (+0xa0), sin (+0xa4), cos (+0xa8) and tan (+0xac) are rewritten together.
// Only a projection whose aspect is within 0.01 of 16:9 is touched, so the camera update's fresh values are rewritten once, and a projection that is already ours is not
// scaled again (the aspect field is no longer 16:9; if the game writes 16:9 back and keeps our tangent, the table of recent results recognises it and only the aspect is set).
// The camera objects are not written: the authored field of view (+0x13c) and aspect (+0x140) stay, so nothing accumulates.
//
// Credit chain: the camera sites and the idea of replacing the 16:9 ratio where it is read are Jbuck7's GameBanana mod 737495 (Ocarina of Time 1.1.1 ultrawide), carried to
// NX2navi's patches-v111.txt by Ivan0xFF (MIT), and to Hookshot's nx2/oot_wide.py by NotRexed (GPL-3.0; https://github.com/NotRexed/Hookshot). This file re-expresses
// them as host callbacks on gates the rewriter places (patches.py), with the vertical-FOV compensation for narrow pictures added here. See android/NOTICE.md.
//
// The picture shape is read once at start (restart to change it, as the launcher does). Not set, invalid, or within 0.02 of 16:9: the game stays as it made it.
//
// The 2D layer is laid out for 16:9 and would be stretched (wider picture) or squeezed (narrower) with the picture, so three more gates (the same OBS number, the site kind in the
// parameter's bits from 5 up) keep it in the middle 16:9 of the picture; the 3D fills it all. The same sources: Ivan0xFF's UI, movie and matrix sites, Hookshot's save picture and
// its narrow-screen HUD (PR 2015); the sides stay what the game cleared them to (no side renderer here).
//   HUD     main+0x774368 (ldp q1,q4,[x2], the canvas's projection rows into the matrix product, x0 the canvas). When the rows are the full-screen UI orthographic projection on its
//           3840x2160 grid (m00 = 2/3840, m11 = 2/2160), x2 is pointed at a copy whose x row (wider picture: x 16/9 over the picture's ratio) or y row (narrower: the ratio over 16/9)
//           is scaled; the game's own matrix is never written. The canvas's screen object (the pointer 0x1b8 before the canvas, a vtable) says which screen it is: the item wheel's
//           background (bit 0, redraws a capture of the whole picture), the pause / system menu background (bit 1), the event and loading fades (bit 2) and the fade between areas
//           (bit 3) are known (Hookshot's findings); a screen whose bit is in the keep mask stays whole (default 0xd: 0, 2 and 3 cover the picture, the rest, HUD and menus, take the
//           middle). DM_OOT_WIDE_KEEP=<hex> sets the mask for testing; each screen's first sighting is logged.
//   Movie   main+0x3b5c758 (ldp x9,x8,[x19,#0x18] after the viewport struct at x29-0x28 is built): the movie layer's viewport, min x at +8 and max x at +16 (wider picture) or min y
//           at +12 and max y at +20 (narrower) pulled in by the margin, so a 16:9 movie plays in the middle.
//   Thumb   main+0x284824 (ldr x8,[x8] before the blr of SetViewport; x1..x4 = x, y, w, h of 0,0,543,306): the save picture's texture gets the middle 16:9 (viewport made wider
//           than the texture, or taller, centred).
#include "wide_shape.h"

#define OOT_MAIN_BUILD "e0f3ccfaf50065ae4ea01eb5aeb13b1a"
#define K169 WS_K169
#define close_to ws_close_to
#define rdf ws_rdf
#define wrf ws_wrf
enum { P_NEAR = 0x98, P_FAR = 0x9c, P_FOVY = 0xa0, P_SIN = 0xa4, P_COS = 0xa8, P_TAN = 0xac, P_ASPECT = 0xb0 };

static ws_cfg_t g_cfg = WS_CFG_INIT;
static ws_seen_t g_seen;   // projections we scaled: where, and the tangent we wrote
static _Atomic unsigned g_fixes;

static double aspect(void) { return ws_aspect(&g_cfg, OOT_MAIN_BUILD, "oot"); }
static uint8_t *main_base(void) { return ws_main_base(); }

// ---- draw distance (DM_OOT_DRAW_DISTANCE) ----
// The main camera's sead::PerspectiveProjection also keeps its near plane at +0x98 and far plane at +0x9c (the matrix update at main+0x3485cc0 builds m22 / m23 from them
// and the flag at +0xa; culling reads them too). The game's far plane is 25000 in play (1000 on the title screen), far beyond anything its fog shows, and the game culls and
// clips by it. DM_OOT_DRAW_DISTANCE=<10..20000> (game units, about metres) caps the far plane at near + that distance: what lies beyond is clipped and the game's own frustum
// culling drops it (castle market, 50: 38 % fewer draws and 26 % less GPU time, the far street fades into the fog). Read at every camera update, so the in-game panel / `nxctl.sh
// env` changes it live; unset, 0 or a value above the game's own far plane leaves the game as it made it. The same gates and the same "16:9 camera" test as the aspect fix pick the
// projection; shadow and light projections have other shapes. Not a general mechanism: the engine's planes are this build's (+0x98 / +0x9c are the same in every sead title, the
// gates are fixed addresses of this build; BINDING in patches.py) and no host-side lever sees what the game decides to draw.
static ws_seen_t g_far_seen;   // projections whose far plane we wrote, and the value
static _Atomic unsigned g_far_logged;
static double far_distance(void) {
    const char *e = getenv("DM_OOT_DRAW_DISTANCE");
    if (!e || !*e) return 0;
    char *end;
    double v = strtod(e, &end);
    if (*end || !(v >= 10 && v <= 20000)) return 0;   // not a number, or below what a scene needs (the player's own feet are inside 10)
    return v;
}
static void far_fix(uint64_t proj) {
    double d = far_distance();
    float nr = rdf(proj + P_NEAR), fr = rdf(proj + P_FAR);
    if (!(nr >= 0.0f && nr < fr && fr < 1e8f)) return;   // no planes the game made
    if (ws_seen_has(g_far_seen, proj, fr)) return;   // the far plane is one we wrote: not capped twice
    unsigned k = atomic_load_explicit(&g_far_logged, memory_order_relaxed);
    if (k < 8 && atomic_compare_exchange_strong_explicit(&g_far_logged, &k, k + 1, memory_order_relaxed, memory_order_relaxed))   // the first planes seen, with or without the cap
        LOG("oot far: projection near %.3f far %.1f (draw distance %.0f)", nr, fr, d);
    if (!d || fr <= nr + d) return;
    float nf = (float)(nr + d);
    wrf(proj + P_FAR, nf);
    ws_seen_set(g_far_seen, proj, nf);
}

// ---- model LOD distance (DM_OOT_LOD_SCALE) ----
// The model LOD level is picked per model and view by one function, main+0x31d4d80 (and the same code inlined at main+0x31d48b0, +0x7bb80 three times, +0x12142c0, +0x3627b20,
// +0x36982e0), on the graphics scene manager (its ModelLodParam handle at +0xd50, the param object at handle +0x150). Its distance path (the only one: its screen-size path needs a
// manager flag, +0xe20 bit 22, that no code of this build sets): S is the model's LOD start distance, D its distance from the camera, n its level count; for S under 50 the start
// distance is S * model coef (GameModelController_LodStartDistCoef, model +0x40) * manager +0xd90 (the game copies LodStartDistCoefForHandheld 0.8 or ForConsole 1.0 there, by
// the operation mode), blending to plain S at S 100; beyond the start, the level grows with (D - start) over ModelLodParam MaxLevelDistScale (+0x50, 1.0) * the model's own
// scale (model +0x44), up to n - 1. DM_OOT_LOD_SCALE=<0.1..1> multiplies the two shared inputs, the start coefficient and MaxLevelDistScale, by k: models drop to coarser
// levels nearer (k 0.5: about half the distance for models whose LOD starts within 50 units; the steps after the start come k times sooner for all). The game's own LOD meshes,
// no clip. The gate is the scene manager's per-frame view update (main+0x4753c8, after it stored its LOD distance offset +0xd8c): read every frame, so the in-game panel /
// `nxctl.sh env` changes it live; unset, invalid or 1 puts back the game's values (they are remembered; a fresh value the game writes is taken as its own). The param object is
// only written when it is ModelLodParam (its vtable) and has no parent param (the game would read the parent's value). A per-game rule like the draw distance: the host sees no LOD.
#define OOT_LOD_PARAM_VT 0x4b87a88   // ModelLodParam's vtable, main-relative (its constructor main+0xf7e7d0)
enum { M_LOD_PARAM = 0xd50, M_LOD_START = 0xd90, LP_PARENT = 0x10, LP_MAXLEVEL = 0x50, LP_MAXLEVEL_OWN = 0x5d };
typedef struct { uint64_t at; float orig, wrote; } lod_kept_t;
static lod_kept_t g_lod_kept[8];   // fields we scaled: where, the game's value, the value we wrote
static pthread_mutex_t g_lod_lock = PTHREAD_MUTEX_INITIALIZER;
static unsigned g_lod_logged;   // under g_lod_lock, with the scale last logged
static double g_lod_k;
static double lod_scale(void) {
    const char *e = getenv("DM_OOT_LOD_SCALE");
    if (!e || !*e) return 1;
    char *end;
    double v = strtod(e, &end);
    return *end || !(v >= 0.1 && v <= 1) ? 1 : v;   // not a number or outside 0.1..1: the game's own
}
// One float field: the game's value is what we find unless it is the value we wrote; it gets the game's value times k
static void lod_field(uint64_t at, double k) {
    float cur = rdf(at);
    lod_kept_t *e = NULL;
    for (int i = 0; i < 8 && !e; i++) if (g_lod_kept[i].at == at) e = &g_lod_kept[i];
    if (!e) {
        if (k == 1) return;   // never written: nothing to put back
        for (int i = 0; i < 8 && !e; i++) if (!g_lod_kept[i].at) e = &g_lod_kept[i];
        if (!e) return;
        e->at = at; e->wrote = cur; e->orig = cur;
    }
    if (ws_bits(cur) != ws_bits(e->wrote)) e->orig = cur;   // the game wrote a fresh value
    if (!(e->orig > 0 && e->orig < 1000)) return;   // not a coefficient the game made
    float nv = (float)(e->orig * k);
    if (ws_bits(nv) != ws_bits(cur)) wrf(at, nv);
    e->wrote = nv;
}
static void lod_fix(uint64_t mgr) {
    if (!mgr || (mgr & 7) || strcmp(dm_main_build(), OOT_MAIN_BUILD)) return;
    double k = lod_scale();
    uint64_t h, p = 0, vt = 0, parent = 0, base = (uint64_t)(uintptr_t)main_base();
    memcpy(&h, (void *)(mgr + M_LOD_PARAM), 8);
    if (h && !(h & 7)) memcpy(&p, (void *)(h + 0x150), 8);
    if (p && !(p & 7)) { memcpy(&vt, (void *)p, 8); memcpy(&parent, (void *)(p + LP_PARENT), 8); }
    int param = base && p && !(p & 7) && vt == base + OOT_LOD_PARAM_VT && (!parent || (*(uint8_t *)(p + LP_MAXLEVEL_OWN) & 1));
    pthread_mutex_lock(&g_lod_lock);
    float s0 = rdf(mgr + M_LOD_START), m0 = param ? rdf(p + LP_MAXLEVEL) : 0;
    lod_field(mgr + M_LOD_START, k);
    if (param) lod_field(p + LP_MAXLEVEL, k);
    if (g_lod_logged < 16 && (!g_lod_logged || k != g_lod_k)) {   // the first sighting and every change of the scale
        g_lod_logged++;
        g_lod_k = k;
        LOG("oot lod: LOD scale %.2f: start coefficient %.3f -> %.3f, max level distance scale %.3f -> %.3f%s", k, s0, rdf(mgr + M_LOD_START), m0, param ? rdf(p + LP_MAXLEVEL) : 0.0,
            param ? "" : " (no ModelLodParam of its own here: start coefficient only)");
    }
    pthread_mutex_unlock(&g_lod_lock);
}

// One projection, in place (the callbacks below; the unit test calls it through them)
static void fix(uint64_t proj) {
    double a = aspect();
    if (!proj || (proj & 3)) return;
    if (!close_to(rdf(proj + P_ASPECT), K169, 0.01)) return;
    float tn = rdf(proj + P_TAN);
    if (!(tn > 0.01f && tn < 20.0f)) return;   // not a perspective lens the game made
    if (!strcmp(dm_main_build(), OOT_MAIN_BUILD)) far_fix(proj);
    if (!a) return;
    if (a < K169) {
        if (!ws_seen_has(g_seen, proj, tn)) {
            double half = ws_vertplus_half(tn, a);   // under 172 degrees: a tangent past that is no lens
            float ntan = (float)tan(half);
            if (atomic_fetch_add_explicit(&g_fixes, 1, memory_order_relaxed) == 0)
                LOG("oot wide: first projection fovy %.2f (sin %.4f cos %.4f tan %.4f) -> %.2f deg vertical (aspect %.4f -> %.4f)", rdf(proj + P_FOVY) * 57.29578,
                    rdf(proj + P_SIN), rdf(proj + P_COS), tn, 2 * half * 57.29578, rdf(proj + P_ASPECT), a);
            wrf(proj + P_FOVY, (float)(2 * half));
            wrf(proj + P_SIN, (float)sin(half));
            wrf(proj + P_COS, (float)cos(half));
            wrf(proj + P_TAN, ntan);
            ws_seen_set(g_seen, proj, ntan);
        }
    }
    wrf(proj + P_ASPECT, (float)a);
}

// ---- the 2D layer ----
static const uint32_t HUD_SCREEN[4] = {0x4bed098, 0x4be4fb0, 0x4be61c8, 0x4be7b30};   // vtables (main-relative) of the screens whose canvas keeps the whole picture by default: bit k of the keep mask
static pthread_once_t g_keep_once = PTHREAD_ONCE_INIT;
static unsigned g_keep = 0xd;
static _Atomic uint64_t g_logged[16];   // screen vtables already logged
static _Atomic unsigned g_nlogged;
static _Thread_local _Alignas(16) float t_rows[8];   // the scaled copy of the canvas's first two projection rows, read by the very next instruction

static void keep_init(void) {
    const char *e = getenv("DM_OOT_WIDE_KEEP");
    char *end;
    if (e && *e) { unsigned long v = strtoul(e, &end, 16); if (!*end) g_keep = (unsigned)v & 0xf; }
}

static void hud(uint64_t *r) {
    double a = aspect();
    uint64_t m = r[2], cv = r[0];
    if (!a || !m || (m & 3) || !cv) return;
    if (rdf(m) != 2.0f / 3840.0f || rdf(m + 0x14) != 2.0f / 2160.0f) return;   // not the full-screen UI projection
    pthread_once(&g_keep_once, keep_init);
    uint64_t vt, base = (uint64_t)(uintptr_t)main_base();
    memcpy(&vt, (void *)(cv - 0x1b8), 8);
    int bit = -1;
    for (int k = 0; k < 4; k++) if (base && vt == base + HUD_SCREEN[k]) bit = k;
    int whole = bit >= 0 && (g_keep >> bit & 1);
    if (atomic_load_explicit(&g_nlogged, memory_order_relaxed) < 16) {   // each screen, once (a few races log twice at worst)
        unsigned i, n = atomic_load_explicit(&g_nlogged, memory_order_relaxed);
        for (i = 0; i < n; i++) if (atomic_load_explicit(&g_logged[i], memory_order_relaxed) == vt) break;
        if (i == n) {
            unsigned k = atomic_fetch_add_explicit(&g_nlogged, 1, memory_order_relaxed);
            if (k < 16) {
                atomic_store_explicit(&g_logged[k], vt, memory_order_relaxed);
                LOG("oot wide: UI canvas, screen vtable main+%#llx (%s): %s", (unsigned long long)(vt - base),
                    bit < 0 ? "not a listed screen" : bit == 0 ? "item wheel background" : bit == 1 ? "pause menu background" : bit == 2 ? "event / loading fade" : "area change fade",
                    whole ? "kept whole" : a > K169 ? "x row squeezed into the middle 16:9" : "y row squeezed into the middle 16:9");
            }
        }
    }
    if (whole) return;
    ws_squeeze_rows(t_rows, (const float *)(uintptr_t)m, a);
    r[2] = (uint64_t)(uintptr_t)t_rows;
}

static _Atomic int g_movie_logged;
static void movie(uint64_t *r) {
    double a = aspect();
    uint64_t vp = r[29] - 40;
    if (!a || !r[29]) return;
    float v[6];
    memcpy(v, (void *)(vp + 8), 4); memcpy(v + 1, (void *)(vp + 12), 4); memcpy(v + 2, (void *)(vp + 16), 4); memcpy(v + 3, (void *)(vp + 20), 4);
    if (!(v[2] > v[0]) && !(v[3] > v[1])) return;
    int wide = a > K169;
    double margin = ws_margin(a);
    int lo = wide ? 0 : 1, hi = wide ? 2 : 3;
    if (!(v[hi] > v[lo])) return;
    float in = (float)((v[hi] - v[lo]) * margin), nlo = v[lo] + in, nhi = v[hi] - in;
    if (!atomic_exchange_explicit(&g_movie_logged, 1, memory_order_relaxed))
        LOG("oot wide: movie viewport (%.1f %.1f)-(%.1f %.1f): %s %.1f..%.1f -> %.1f..%.1f", v[0], v[1], v[2], v[3], wide ? "x" : "y", v[lo], v[hi], nlo, nhi);
    wrf(vp + 8 + 4 * (wide ? 0 : 1), nlo);
    wrf(vp + 8 + 4 * (wide ? 2 : 3), nhi);
}

static void thumb(uint64_t *r) {
    double a = aspect();
    if (!a || (uint32_t)r[1] != 0 || (uint32_t)r[2] != 0 || (uint32_t)r[3] != 543 || (uint32_t)r[4] != 306) return;   // the save picture's 543x306 viewport only
    if (a > K169) {
        int w = (int)(543.0 * a / K169 + 0.5);
        r[1] = (uint32_t)((543 - w) / 2); r[3] = (uint32_t)w;
    } else {
        int h = (int)(306.0 * K169 / a + 0.5);
        r[2] = (uint32_t)((306 - h) / 2); r[4] = (uint32_t)h;
    }
}

// The gate number's upper bits (param): the site kind from bit 5 (0 camera, 1 HUD, 2 movie, 3 save picture, 4 model LOD: the scene manager in the register of bits 0-4), the register of a camera site in bits 0-4 (patches.py)
static void oot_wide_gate(uint64_t *r, int param) {
    if (param < 0) return;
    switch (param >> 5) {
    case 0: if ((param & 31) <= 28) fix(r[param & 31]); break;
    case 1: hud(r); break;
    case 2: movie(r); break;
    case 3: thumb(r); break;
    case 4: if ((param & 31) <= 28) lod_fix(r[param & 31]); break;
    }
}

__attribute__((constructor)) static void oot_wide_attach(void) { gate_obs_set(OBS_OOT_WIDE, oot_wide_gate); }
