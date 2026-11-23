// SPDX-License-Identifier: GPL-3.0-or-later
// Mario Tennis Fever (Switch 2), nro0 of 1.1.1 (build ID 250a510a934129cb38e930c9a29082b6): the gameplay camera and the 2D layer follow the picture's shape.
//
// The game draws a 16:9 frame whatever the screen; Game settings > Aspect ratio shows the frame at another shape (DM_VK_PICTURE_ASPECT=<w>:<h>, vka_present.c). See wide_shape.h.
// main is a boot stub; the game's code is nro0, so the build check is on that NRO (ws_aspect_nro), not on main. Gates: patches.py OBS rows, kind in the parameter's bits 5 up.
// Gate frame (entry.S dm_gate): x0..x30 at r[0..30], q0..q31 at r[32 + 2 * n]; a write to a register takes effect when the gate returns.
//
// Kind 0, the camera's aspect: nro0+0x11a2660 is the display layout setter (x0 the layout, w1 the mode, x2 the views' sizes). It keeps the mode at layout +0x20, the view count at
// +0x24 (mode 0: 1 view, modes 1-3: 2-4 views, 4 and up: 2; nro0+0x11a27f4), view 0's size (u32 width, height) at +0x2c, and ends by writing each view's width over height into the
// camera array (GOT slot nro0+0x175ecd8, stride 0x330): nro0+0x11a2fc8 `str s0,[x20,#0x40]` is camera 0's aspect, the gameplay camera's. It runs at every layout apply, the scene size
// function's resize (nro0+0x125ec28) among them, and no other code stores that field through the array's GOT slot. The gate runs before the store: with one view (layout +0x24 == 1)
// and an aspect within 0.01 of 16:9, the aspect becomes the picture's. Two or more views keep theirs: the viewport function nro0+0x11da0c0 builds each view as a 16:9 box
// (nro0+0x11da5d0) in the 16:9 frame.
//
// Kind 1, the vertical field of view (narrower picture only, Vert+): camera 0's fovy (+0x4c, radians, the vertical angle) is NOT a value to rewrite in memory: camera directors
// write it every frame (nro0+0x969e40 and its twin nro0+0x990068 copy their own fovy and the eye into camera 0, then call its update; nro0+0x990cd0 reads camera 0's fovy back as a
// blend's start; the debug camera nro0+0x933568 adds to it), so a scaled value would be scaled again or fed back. The gates sit instead after each load of fovy inside the projection
// builders, and change only the register: nro0+0x932378 (the table path, s1 = the fovy loaded by `ldp s5,s1,[x19,#0x48]` at nro0+0x931ef0; nothing between writes s1 and nothing
// branches into the range), nro0+0x93252c and nro0+0x932700 in the updater nro0+0x931868, and nro0+0x9334ac in its refresh nro0+0x933358 (s0 = `ldr s0,[x19,#0x4c]` just before;
// these are the only loads of +0x4c in both). x19 is the camera. Only camera 0 with the aspect kind 0 wrote is changed: the half angle's tangent grows by (16/9) / aspect, so the
// horizontal reach stays a 16:9 picture's (ws_vertplus_half). The frustum these build (+0x2a4..+0x2bc) is what culling reads.
//
// Kinds 2-4, the 2D layer (nn::ui2d layouts in 1920x1080 units): nro0+0x11d54a0 sets a layout's draw info up (x19; draw info at +0x1f8): ortho from the layout rect, or perspective
// when the layout carries a field of view, built at sp+0x80 (4x4 floats, the x row first) and copied into the draw info's +0x10 by nro0+0x665fc (a plain 64-byte copy) at
// nro0+0x11d6620. Kind 2 is the instruction before that bl (nro0+0x11d661c, x1 = the stack matrix, x0 the draw info; straight-line code from the merge at nro0+0x11d649c, x1 not
// written): a 16:9 matrix there gets its x row (wider picture) or y row (narrower) scaled, so the layout sits in the middle 16:9; the draw info gets the scaled copy. The capture path
// nro0+0xaf6440 (a pane drawn into a texture with its own ortho, the draw info's matrix saved and put back) is not gated, so captures keep their own projection.
// A pane over the whole canvas (fades, backdrops: size x global matrix >= 98% of 1920x1080) keeps the whole picture: nn::ui2d's draw constant-buffer setup and text setup are the
// same SDK code as Mario Kart World 1.8.0's (mkw_wide.c; the projection getter nro0+0x66718 is the same five words, the two functions the same instructions and registers), so
// kind 3 (nro0+0x75a98, before its bl to the getter; pane matrix x23, size x22) and kind 4 (nro0+0x8a2ec; pane x21) point x0 at a thread-local draw info holding the unscaled matrix
// when the draw info holds a matrix kind 2 scaled. DM_MTF_HUD=0 leaves the 2D layer stretched with the frame.
//
// Not done here: the world-anchored markers (name tags, ball marker; nro0+0xd63140 and about five inlined copies map camera to layout units), so with the 2D layer in the middle they
// sit nearer the middle than the 3D they point at; camera 1's store (nro0+0x11a2fdc, a two-view mode's second view); multi-view layouts (16:9 views in the middle). See the README.
#include "wide_shape.h"

#define MTF_NRO "nro0"
#define MTF_NRO_BUILD "250a510a934129cb38e930c9a29082b6"
#define K169 WS_K169
enum { L_VIEWS = 0x24, C_ASPECT = 0x40, DI_MTX = 0x10 };

static ws_cfg_t g_cfg = WS_CFG_INIT;
static ws_seen_t g_ui_seen;                     // draw infos whose layout matrix kind 2 scaled: where, and the scaled diagonal entry (m00 wider, m11 narrower)
static _Atomic uint64_t g_cam0;                  // the camera kind 0 converted (camera 0), and the aspect it wrote
static _Atomic uint32_t g_cam0_aspect;
static _Atomic unsigned g_cam_logs, g_fov_logs;
static _Atomic int g_ui_logged[5], g_hud_mode = -1;
static _Thread_local _Alignas(16) unsigned char t_di[0x60];   // a draw info stand-in: the getter (nro0+0x66718) reads +0x10..+0x4f only

static double aspect(void) { return ws_aspect_nro(&g_cfg, MTF_NRO, MTF_NRO_BUILD, "mtf"); }

// DM_MTF_HUD: 1 (unset) the 2D layer in the middle 16:9, 0 stretched with the frame
static int hud_on(void) {
    int m = atomic_load_explicit(&g_hud_mode, memory_order_acquire);
    if (m >= 0) return m;
    const char *e = getenv("DM_MTF_HUD");
    int want = !e || !*e || !strcmp(e, "1") ? 1 : 0;
    m = -1;
    if (atomic_compare_exchange_strong_explicit(&g_hud_mode, &m, want, memory_order_acq_rel, memory_order_acquire)) {
        if (e && *e && strcmp(e, "0") && strcmp(e, "1")) LOG("[RED] DM_MTF_HUD=%s: must be 0 or 1; the 2D layer is left stretched", e);
        return want;
    }
    return m;
}

// Kind 0: camera 0's aspect store, x19 the layout, x20 the camera array, s0 view 0's width over height
static void cam(uint64_t *r) {
    double A = aspect();
    uint64_t lay = r[19];
    if (!A || !lay || (lay & 3)) return;
    int32_t views;
    memcpy(&views, (void *)(uintptr_t)(lay + L_VIEWS), 4);
    float *s0 = (float *)(void *)&r[32];
    float in = *s0;
    if (views != 1 || !ws_close_to(in, K169, 0.01)) return;
    float out = (float)A;
    atomic_store_explicit(&g_cam0_aspect, ws_bits(out), memory_order_relaxed);
    atomic_store_explicit(&g_cam0, r[20], memory_order_release);
    unsigned n = atomic_load_explicit(&g_cam_logs, memory_order_relaxed);
    if (n < 8 && atomic_fetch_add_explicit(&g_cam_logs, 1, memory_order_relaxed) < 8)
        LOG("mtf wide: camera aspect %.4f -> %.4f (one view, %s)", in, out, A > K169 ? "Hor+" : "Vert+");
    *s0 = out;
}

// Kind 1: a projection builder has just loaded camera x19's fovy into s<reg>; a narrower picture's camera 0 gets the Vert+ angle in the register only
static void fov(uint64_t *r, int reg) {
    double A = aspect();
    uint64_t c = r[19];
    if (!A || A > K169 || reg < 0 || reg > 31 || !c || (c & 3)) return;
    if (c != atomic_load_explicit(&g_cam0, memory_order_acquire) || ws_bits(ws_rdf(c + C_ASPECT)) != atomic_load_explicit(&g_cam0_aspect, memory_order_relaxed)) return;
    float *s = (float *)(void *)&r[32 + 2 * reg];
    float f = *s;
    if (!(f > 0.01f && f < 3.0f)) return;   // radians, as the game clamps them (0.5 to 179 degrees)
    float out = (float)(2 * ws_vertplus_half(tanf(f / 2), A));
    unsigned n = atomic_load_explicit(&g_fov_logs, memory_order_relaxed);
    if (n < 4 && atomic_fetch_add_explicit(&g_fov_logs, 1, memory_order_relaxed) < 4) LOG("mtf wide: camera fovy %.4f -> %.4f rad (Vert+)", f, out);
    *s = out;
}

// x and y unskewed, |m11 / m00| within 0.008 of `want` (row-major, x row first)
static int unskewed_shape(const float *m, double want) {
    if (m[1] || m[2] || m[4] || m[6] || m[8] || m[9] || m[12] || m[13] || !m[0]) return 0;
    float a = m[5] / m[0];
    return ws_close_to(a < 0 ? -a : a, want, 0.008);
}

static void ui_log(int kind, const char *what) {
    if (!atomic_exchange_explicit(&g_ui_logged[kind], 1, memory_order_relaxed)) LOG("mtf wide: 2D layer: %s (%s row)", what, aspect() > K169 ? "x" : "y");
}

// Kind 2: the layout's projection at x1 (the game's stack copy), about to be copied into the draw info x0
static void ui_setup(uint64_t *r) {
    double A = aspect();
    uint64_t di = r[0], src = r[1];
    if (!A || !hud_on() || !di || (di & 3) || !src || (src & 3)) return;
    float m[16];
    memcpy(m, (void *)(uintptr_t)src, sizeof m);
    if (!unskewed_shape(m, K169)) return;
    int row = A > K169 ? 0 : 1;
    float q = ws_squeeze(A);
    for (int k = 0; k < 4; k++) m[4 * row + k] *= q;
    memcpy((void *)(uintptr_t)src, m, sizeof m);
    ws_seen_set(g_ui_seen, di, m[5 * row]);
    ui_log(2, "a layout projection scaled into the middle 16:9");
}

// A pane over the whole 1920x1080 canvas: mtx = its global matrix, size = its size, mtx - 0x20 when they belong together
static int full_screen_pane(uint64_t mtx, uint64_t size) {
    if (size != mtx - 0x20 || (mtx & 3) || mtx < 0x70) return 0;
    const float *g = (const float *)(uintptr_t)mtx, *sz = (const float *)(uintptr_t)size;
    return fabsf(g[0] * sz[0]) > 1920 * 0.98f && fabsf(g[5] * sz[1]) > 1080 * 0.98f;
}

// Kinds 3 and 4: nn::ui2d is about to read the draw info x0's projection for a pane; a full-canvas pane under a matrix kind 2 scaled reads the unscaled one from the stand-in
static void ui_pane(uint64_t *r, int text) {
    double A = aspect();
    uint64_t di = r[0];
    if (!A || !hud_on() || !di || (di & 3)) return;
    float m[16];
    memcpy(m, (void *)(uintptr_t)(di + DI_MTX), sizeof m);
    int row = A > K169 ? 0 : 1;
    if (!ws_seen_has(g_ui_seen, di, m[5 * row]) || !unskewed_shape(m, A)) return;
    if (!(text ? full_screen_pane(r[21] + 0x70, r[21] + 0x50) : full_screen_pane(r[23], r[22]))) return;
    float q = ws_squeeze(A);
    for (int k = 0; k < 4; k++) m[4 * row + k] /= q;
    memcpy(t_di + DI_MTX, m, sizeof m);
    r[0] = (uint64_t)(uintptr_t)t_di;
    ui_log(text ? 4 : 3, text ? "a full-canvas text pane kept over the whole picture" : "a full-canvas pane kept over the whole picture");
}

static void mtf_wide_gate(uint64_t *r, int param) {
    if (param < 0) return;
    switch (param >> 5) {
    case 0: cam(r); break;
    case 1: fov(r, param & 31); break;
    case 2: ui_setup(r); break;
    case 3: ui_pane(r, 0); break;
    case 4: ui_pane(r, 1); break;
    }
}

__attribute__((constructor)) static void mtf_wide_attach(void) { gate_obs_set(OBS_MTF_WIDE, mtf_wide_gate); }
