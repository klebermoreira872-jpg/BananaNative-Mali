// SPDX-License-Identifier: GPL-3.0-or-later
// Pokopia camera aspect adjustment, adapted from Recompia's
// runtime/games/pkp/render/pkp_aspect.cpp (GPL-3.0-or-later).
// Source: https://github.com/Dittobyte/Recompia/tree/75dae2f2ccdada74e6b8ba12ea7de30560a84221
// The Android adaptation preserves the game's 16:9 aspect field and corrects P00 after the builder.
// Camera-only: UI anchoring and canvas changes are deliberately excluded.
//
// KTGL's camera (init main+0x1f12368): projection rows +192, vertical FOV
// (radians) +328, aspect +332, flags +344 (bit 0: orthographic).
// patches.py pins the observation gates to main build 76a489f3...:
//   +0x8cc128 (28), x20: remember a scene camera handed to the render view.
//   +0x1f12130 (29), x0: before the builder reads the fields, increase vertical FOV.
//   +0x1f12354 (30|0), x19: after the builder writes P, restore horizontal reach.
//   +0x0ebecec (30|6), x1: event stencil mask quad rect[4] before submit (Screen shape & variant 43).
//   +0x0ebedd0 (30|7), x1/x19: event alpha-mask quad rect[4] & entry before submit (Screen shape & variant 43).
//
// The game copies the scene camera into a secondary render camera. Remember
// corrected FOV values too, so that copy receives the same projection fix.
// The aspect FIELD stays 16:9: terrain visibility and LOD derive from it.
// Changing that field to the display aspect made terrain cells disappear.
//
// DM_PKP_ASPECT=<picture width/height> is opt-in and read once per game process.
// Changing it requires a restart: live changes cannot safely restore cameras
// that the game has copied or stopped rebuilding. Default/off never writes a
// camera. The picture may use DM_VK_PICTURE_ASPECT; when DM_PATCH_VARIANT is
// unset, this also drives Screen shape UI scaling/anchoring (gates 30|1..3, 30|6..7).
//
// With DM_PATCH_VARIANT=43 (native 4:3 pack variant, main build 76a489f3...),
// world cameras run at 4:3 (W1) plus the T95 7-deg Pokedex portrait camera fix
// on gate 30|0, while gates 30|3..5 dispatch kg175 UI rules (pkp_ui43.c),
// 30|6..7 widen event mask rects, and 30|1..2 are no-ops. Any other
// DM_PATCH_VARIANT disables aspect() / UI squeeze so variants are never double-corrected.
#include "hle.h"
#include "dm.h"
#include "pkp_ui43.h"
#include <math.h>
#include <errno.h>
#include <stdio.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>

#define K169 (16.0 / 9.0)
#define PKP_MAIN_BUILD "76a489f3bd3642fa5e18bd83d32c98ba"
enum {
    CAM_PROJ = 192,
    CAM_FOV = 328,
    CAM_ASPECT = 332,
    CAM_FLAGS = 344,
    NCAM = 8,
    NPUT = 32,
    PKP_FITW_OFF = 0x9131a8,
    PKP_FITW_ORIG_INSN = 0x6e0c0400u,
    PKP_T95_FOV_BITS = 0x3dfa35ddu,
    PKP_T95_LR2_OFF = 0x22bba04u
};

static _Atomic uint64_t g_cam[NCAM];
static _Atomic uint32_t g_cam_fov[NCAM]; // an unchanged scene camera never loses provenance
static _Atomic uint32_t g_put[NPUT];   // corrected FOV bit patterns, including copies
static _Atomic unsigned g_put_at, g_puts;
static pthread_once_t g_config_once = PTHREAD_ONCE_INIT;
static double g_aspect;
static int g_variant_43;
static uint64_t g_main_base;

static int close_to(double a, double b) { return fabs(a - b) < 0.02; }
static float rdf(uint64_t a) { float f; memcpy(&f, (void *)a, 4); return f; }
static void wrf(uint64_t a, float f) { memcpy((void *)a, &f, 4); }
static uint32_t rdu(uint64_t a) { uint32_t u; memcpy(&u, (void *)a, 4); return u; }

static const module_t *find_main_mod(void) {
    for (int i = 0; i < g_nmod; i++)
        if (!strcmp(g_mod[i].name, "main")) return &g_mod[i];
    return NULL;
}

static int is_fitw_branch(uint32_t insn) {
    if (insn == PKP_FITW_ORIG_INSN || (insn >> 26) != 0x05u) return 0;
    int32_t imm26 = (int32_t)(insn << 6) >> 6;
    int64_t target = (int64_t)PKP_FITW_OFF + (int64_t)imm26 * 4;
    return target >= 0x2749480 && target < 0x274a000;
}

// With DM_PATCH_VARIANT=43, lock to 4:3 + kg175 UI once main+0x9131a8 shows the variant branch.
// Any other DM_PATCH_VARIANT disables camera/UI correction. When DM_PATCH_VARIANT is unset, fall
// back from DM_PKP_ASPECT to Screen shape's DM_VK_PICTURE_ASPECT=<w>:<h>.
static void config_init(void) {
    const module_t *m = find_main_mod();
    if (!m || strcmp(m->build_id, PKP_MAIN_BUILD)) return;
    g_main_base = (uint64_t)(uintptr_t)m->base;
    const char *var = getenv("DM_PATCH_VARIANT");
    if (var && *var) {
        if (!strcmp(var, "43")) {
            if (!m->base || (m->text_end && m->text_end < PKP_FITW_OFF + 4)) {
                LOG("[RED] pkp ui43: DM_PATCH_VARIANT=43 but main image is unavailable; falling back to non-variant mode");
                return;
            }
            uint32_t insn = rdu(g_main_base + PKP_FITW_OFF);
            if (!is_fitw_branch(insn)) {
                LOG("[RED] pkp ui43: DM_PATCH_VARIANT=43 but main+%#x is %#010x (not 4:3 fitw cut); falling back to non-variant mode",
                    PKP_FITW_OFF, insn);
                return;
            }
            g_variant_43 = 1;
            g_aspect = 4.0 / 3.0;
            LOG("pkp aspect: variant 43 active (4:3 world camera + kg175 UI)");
            return;
        }
        LOG("pkp aspect: disabled under DM_PATCH_VARIANT=%s", var);
        return;
    }
    const char *e = getenv("DM_PKP_ASPECT"), *src = "DM_PKP_ASPECT";
    double a = 0;
    if (e && *e) {
        char *end;
        errno = 0;
        a = strtod(e, &end);
        if (end == e || *end || errno == ERANGE || !isfinite(a)) return;
    } else if ((e = getenv("DM_VK_PICTURE_ASPECT")) && *e) {
        unsigned w = 0, h = 0;
        if (sscanf(e, "%u:%u", &w, &h) != 2 || !w || !h) return;
        a = (double)w / h; src = "DM_VK_PICTURE_ASPECT";
    } else return;
    if (a <= 0.4 || a >= K169 - 0.02) return;
    g_aspect = a;
    LOG("pkp aspect: startup %.6f from %s (restart to change)", a, src);
}

static double aspect(void) {
    if (strcmp(dm_main_build(), PKP_MAIN_BUILD)) return 0;
    pthread_once(&g_config_once, config_init);
    return g_aspect;
}

static int is_variant_43(void) {
    if (strcmp(dm_main_build(), PKP_MAIN_BUILD)) return 0;
    pthread_once(&g_config_once, config_init);
    return g_variant_43;
}

static int cam_index(uint64_t cam) {
    for (int i = 0; i < NCAM; i++)
        if (atomic_load_explicit(&g_cam[i], memory_order_relaxed) == cam) return i;
    return -1;
}
static void remember(uint64_t cam) {
    if (cam_index(cam) >= 0) return;
    for (int i = 0; i < NCAM; i++) {
        uint64_t z = 0;
        if (atomic_compare_exchange_strong(&g_cam[i], &z, cam)) return;
    }
}
static int ours(uint32_t fb) {
    if (!fb) return 0;
    for (int i = 0; i < NCAM; i++)
        if (atomic_load_explicit(&g_cam_fov[i], memory_order_relaxed) == fb) return 1;
    for (int i = 0; i < NPUT; i++)
        if (atomic_load_explicit(&g_put[i], memory_order_relaxed) == fb) return 1;
    return 0;
}
static void put(uint32_t fb) {
    // Deduplicate only the recent history: the scene slot already holds fb,
    // but its game-owned copies need this value after the scene zoom changes.
    for (int i = 0; i < NPUT; i++)
        if (atomic_load_explicit(&g_put[i], memory_order_relaxed) == fb) return;
    atomic_store_explicit(&g_put[atomic_fetch_add(&g_put_at, 1) % NPUT], fb, memory_order_relaxed);
}

static void cam_submit(uint64_t *r, int param) {
    if (param != 0 || !aspect() || !r[20]) return;
    remember(r[20]);
}


// A scene camera's original FOV becomes taller. One already corrected is left
// alone, including when the game submits its copied render camera again.
static void proj_build(uint64_t *r, int param) {
    if (param != 0) return;
    double a = aspect();
    uint64_t cam = r[0];
    int index = cam_index(cam);
    if (!a || !cam || index < 0 || (rdu(cam + CAM_FLAGS) & 1)) return;
    float f = rdf(cam + CAM_FOV);
    uint32_t fb = rdu(cam + CAM_FOV);
    if (ours(fb)) {
        atomic_store_explicit(&g_cam_fov[index], fb, memory_order_relaxed);
        return;
    }
    if (!(f > 0.05f && f < 3.0f) || !close_to(rdf(cam + CAM_ASPECT), K169)) return;
    float nf = (float)(2.0 * atan(tan(f * 0.5) * K169 / a));
    wrf(cam + CAM_FOV, nf);
    fb = rdu(cam + CAM_FOV);
    atomic_store_explicit(&g_cam_fov[index], fb, memory_order_relaxed);
    put(fb);
    if (atomic_fetch_add_explicit(&g_puts, 1, memory_order_relaxed) == 0)
        LOG("pkp aspect %.4f: camera %d FOV %.1f -> %.1f deg vertical",
            a, cam_index(cam), f * 57.29578, nf * 57.29578);
}

// Restore the original horizontal reach for a corrected scene camera or its
// game-owned copy. The view-projection multiplication follows this gate.
// Every other perspective camera with the 16:9 aspect field (the UI's ScreenLayout cameras: near 0.1 /
// far 20000, a 45-degree view of a 1920x1080 plane 1303.6 away; the HUD's 0.1 / 55 cameras; render copies)
// gets the same result as a corrected scene camera: its vertical scale P11 times a / (16/9), the
// horizontal one unchanged. The UI is then laid out 1920 wide and 1920 / a high, squeezed into the game's
// 16:9 frame, and the stretched picture shows it in its own proportions. The FOV field is left alone (the
// scene path changes it for culling; the UI culls nothing). DM_PKP_UI=0 keeps the old world-only fix.
#define DEFAULT_CROP ""
static int g_ui = -1;
static int ui_on(void) {
    if (g_ui < 0) { const char *e = getenv("DM_PKP_UI"); g_ui = !(e && *e == '0'); LOG("pkp aspect: UI %s (DM_PKP_UI)", g_ui ? "squeezed" : "left at 16:9"); }
    return g_ui;
}
// Camera families by (near, far): each one logged once. DM_PKP_CROP=<near>:<far>[,...] lists families whose view is a
// set built for exactly 16:9 (a taller view shows the empty space above and below it): those keep their vertical
// view and lose the sides instead (P00 / k), which on the stretched picture fills the screen in proportion.
static float g_crop[8][2]; static int g_ncrop = -1;
static int crop_family(float nr, float fr) {
    if (g_ncrop < 0) {
        g_ncrop = 0; const char *e = getenv("DM_PKP_CROP");
        if (!e) e = DEFAULT_CROP;
        for (char *q = (char *)e; *q && g_ncrop < 8;) { float a = strtof(q, &q); if (*q != ':') break; q++; float b = strtof(q, &q); g_crop[g_ncrop][0] = a; g_crop[g_ncrop][1] = b; g_ncrop++; while (*q == ',') q++; }
        LOG("pkp aspect: crop families: %s", *e ? e : "none");
    }
    for (int i = 0; i < g_ncrop; i++) if (fabsf(nr - g_crop[i][0]) <= 1e-4f * fmaxf(1, g_crop[i][0]) && fabsf(fr - g_crop[i][1]) <= 1e-3f * fmaxf(1, g_crop[i][1])) return 1;
    return 0;
}
static void ui_squeeze(uint64_t cam, float *p, double a) {
    if (!ui_on()) return;
    float nr = rdf(cam + 320), fr = rdf(cam + 324);
    int crop = !(rdu(cam + CAM_FLAGS) & 1) && crop_family(nr, fr);
    if (crop) p[0] /= (float)(a / K169); else p[5] *= (float)(a / K169);
    static float seen[32][2]; static int ns; static _Atomic int lk;
    int known = 0;
    for (int i = 0; i < ns; i++) if (seen[i][0] == nr && seen[i][1] == fr) { known = 1; break; }
    if (!known && !atomic_exchange(&lk, 1)) {
        if (ns < 32) { seen[ns][0] = nr; seen[ns][1] = fr; ns++;
            LOG("pkp aspect %.4f: camera family near %g far %g%s: %s", a, nr, fr, rdu(cam + CAM_FLAGS) & 1 ? " (orthographic)" : "", crop ? "sides cropped (P00 / k)" : "taller view (P11 x k)"); }
        atomic_store(&lk, 0);
    }
}

// Text: glyphs come in screen pixels (y down), and the 2D batch's constants map them to the screen as
// (2 sx / w, -2 sy / h, -1, 1) (main+0x17b97b4: sx, sy the batch's scale, w x h its target). Gate param 2
// sits after the store, x8 = the four words. Pixel mode on a 1080-high target (sx = sy = 1: 2/1920,
// -2/1080) gets the same vertical squeeze about the centre: y scale and y offset times a / (16/9). The
// normalized mode (1, -2: full-screen quads in 0..1) is left alone, so full-screen layers keep filling it.
static int text_prog(unsigned id) {
    static unsigned ids[8]; static int n = -1;
    if (n < 0) {
        const char *e = getenv("DM_PKP_TEXT_PROGS"); if (!e || !*e) e = "1a,11,14";
        n = 0; for (char *q = (char *)e; *q && n < 8;) { ids[n++] = (unsigned)strtoul(q, &q, 16); while (*q == ',') q++; }
        LOG("pkp aspect: text programs squeezed: %s", e);
    }
    for (int i = 0; i < n; i++) if (ids[i] == id) return 1;
    return 0;
}
static void text_consts(uint64_t *r, double a) {
    if (!ui_on() || !r[8]) return;
    float *w = (float *)r[8];
    // Only the text programs: the scene's own full-screen composite is a pixel-mode batch on the same
    // 1920x1080 target. x1 = the batch's material, [+0x10] its "PROG" object, [+0x10] the program number
    // << 8 (this build: 0x1a, 0x11, 0x14 text, the key help among them; 0x03, 0x0b, 0x0e, 0x1d the other 2D batches). DM_PKP_TEXT_PROGS=<hex,...>
    uint64_t prog = r[1] ? *(uint64_t *)(r[1] + 0x10) : 0;
    if (!prog || *(uint32_t *)(prog + 0x40 + 8) != 0x474f5250u) return;   // "PROG"
    unsigned id = *(uint32_t *)(prog + 0x10) >> 8;
    if (fabsf(w[0] * 960.0f - 1.0f) > 0.01f || fabsf(w[1] * 540.0f + 1.0f) > 0.01f || w[3] != 1.0f) return;
    static _Atomic uint64_t seen[4];
    if (id < 256 && !(atomic_fetch_or(&seen[id / 64], 1ull << (id % 64)) & 1ull << (id % 64)))
        LOG("pkp aspect: 2D program %#x in pixel mode: %s", id, text_prog(id) ? "squeezed (text)" : "left (DM_PKP_TEXT_PROGS)");
    if (!text_prog(id)) return;
    float k = (float)(a / K169);
    w[1] *= k; w[3] = k;
}

// ScreenLayout panes (main+0x1f71de0, the transform update; gate param 3 at its tail main+0x1f72270, after the
// pane's global matrix is final and before its children are updated). A pane: +0xd0 parent, +0xe0 global matrix
// (4x4 rows, translation +0x30), +0xe8 local matrix, +0xf0 / +0xf2 int16 size, +0x154 / +0x158 base size floats
// (size animations scale those), +0x10d anchor (always centre here: the 16:9 layouts never anchor to an edge).
// x20 = what the update did (0 nothing, 1 full, 2 translation only). With the UI squeezed, the visible layout is
// 1920 wide and 1080 / k high (k = a / (16/9)); two rules make the HUD and full-screen layers use it:
//  - edge: a pane whose parent is a centred full-screen container (>= 1920x1080) and whose own y is at least
//    DM_PKP_EDGE (default 300) from the centre moves 540 (1/k - 1) toward that edge (180 at 4:3). Its children are
//    updated from its global matrix after this, so the group moves as one. Recomputed at every update: no drift.
//  - cover: a centred pane whose drawn size covers the 16:9 screen but not the taller one (a background, a fade)
//    gets its size and base size times 1/k on both axes: it fills the screen with its proportions kept (the sides
//    fall off screen), and its children (centre-anchored) stay where they are. DM_PKP_COVER=0 turns it off.
enum { MOVED = 0x40000000 };   // a flag bit the game never sets (seen: 0x0241b19d at most): this pane was moved by the edge rules
static float g_edge_t = -1, g_edge_t2 = -1, g_edge_gap = -1; static int g_cover = -1; static _Atomic unsigned g_pane_logs;
static void pane_rules(uint64_t *r, double a) {
    if (!ui_on() || !(a < K169 - 0.02)) return;
    if (g_edge_t < 0) {
        const char *e = getenv("DM_PKP_EDGE"); g_edge_t = e && *e ? strtof(e, NULL) : 300.0f;
        e = getenv("DM_PKP_EDGE_GAP"); g_edge_gap = e && *e ? strtof(e, NULL) : 160.0f;
        e = getenv("DM_PKP_EDGE2"); g_edge_t2 = e && *e ? strtof(e, NULL) : 430.0f;
        e = getenv("DM_PKP_COVER"); g_cover = !(e && *e == '0');
        LOG("pkp aspect: HUD edge rules: |y| >= %g under a full-screen container, global |y| >= %g elsewhere (0 off); cover rule %s", g_edge_t, g_edge_t2, g_cover ? "on" : "off");
    }
    uint64_t n = r[19];
    if (!n || !r[20] || (n >> 32) != 0x40) return;
    uint64_t par = *(uint64_t *)(n + 0xd0), gp = *(uint64_t *)(n + 0xe0), lp = *(uint64_t *)(n + 0xe8);
    if ((gp >> 32) != 0x40 || (lp >> 32) != 0x40) return;
    float *g = (float *)gp, *l = (float *)lp;
    double k = a / K169, inv = 1.0 / k;
    if (g_cover) {
        int16_t *sz = (int16_t *)(n + 0xf0);
        float dw = sz[0] * hypotf(g[0], g[1]), dh = sz[1] * hypotf(g[4], g[5]);
        // at least 1800x1000 drawn (the title's backdrop zooms between 0.95 and 1), centred, not yet as tall as the screen;
        // menu windows (1730 wide) are not layers. The factor makes the drawn height reach 1080 / k
        if (dw >= 1800 && dh >= 1000 && dh < 1080 * inv - 20 && fabsf(g[12]) < 2 && fabsf(g[13]) < 2) {
            double f = fmax(inv, 1080 * inv / dh);
            if (!*(uint64_t *)(n + 0x38)) {   // a leaf (no child list, +0x38): pictures draw from their texture size, so scale its matrix
                for (int i = 0; i < 3; i++) { g[i] *= (float)f; g[4 + i] *= (float)f; }
            } else {   // a container with children: its size (the children are centre-anchored and stay)
                sz[0] = (int16_t)lround(sz[0] * f); sz[1] = (int16_t)lround(sz[1] * f);
                float *base = (float *)(n + 0x154);
                if (base[0] > 0) base[0] *= (float)f; if (base[1] > 0) base[1] *= (float)f;
            }
            if (atomic_fetch_add_explicit(&g_pane_logs, 1, memory_order_relaxed) < 12) LOG("pkp aspect: cover pane %#llx: drawn %.0fx%.0f -> size %dx%d", (unsigned long long)n, dw, dh, sz[0], sz[1]);
        }
    }
    uint32_t *fl = (uint32_t *)(n + 0x104);
    *fl &= ~MOVED;
    if (!par || (par >> 32) != 0x40) return;
    int16_t *ps = (int16_t *)(par + 0xf0);
    uint64_t pgp = *(uint64_t *)(par + 0xe0);
    if ((pgp >> 32) != 0x40) return;
    float *pg = (float *)pgp;
    int under_screen = 0;   // some ancestor is a full-screen container (the field HUD, the Pokedex, the title): rule 1's layouts
    uint64_t root = par, top = par;   // top: the layout's outermost container (the root's child)
    for (uint64_t c = par; c && (c >> 32) == 0x40; c = *(uint64_t *)(c + 0xd0)) {   // a group that moved takes this pane along
        if (*(uint32_t *)(c + 0x104) & MOVED) return;
        int16_t *cs = (int16_t *)(c + 0xf0);
        if (cs[0] >= 1900 && cs[1] >= 1060) under_screen = 1;
        top = root; root = c;
    }
    // HUD sub-layouts (the field key help's text rows: 1920x512 strips) are drawn under their host pane, so a host that
    // moved has moved them without their own matrices showing it: rule 2 only in screen-height panel layouts (the bag's
    // and menus' key help part: 1200x1080, 1208x1020)
    int panel_layout = top != root && ((int16_t *)(top + 0xf0))[1] >= 1000;
    // A part (a layout placed inside another one's pane, e.g. the field HUD's tool wheel and key help) is linked to its
    // host by something other than +0xd0: its chain ends at its own root, which sits where the host is. Only a layout
    // whose root is at the centre is a screen of its own; in a part, a moved host has already moved it
    uint64_t rgp = *(uint64_t *)(root + 0xe0);
    int own_screen = (rgp >> 32) == 0x40 && fabsf(((float *)rgp)[12]) < 1 && fabsf(((float *)rgp)[13]) < 1;
    float y = l[13], gy = g[13];
    int move = 0;
    // 1. under a centred, unscaled full-screen container (>= 1920x1080): DM_PKP_EDGE (300) from the centre (the
    //    field HUD's key help group at -332, the tool wheel at -451, the title's copyright)
    //    Or by its near edge: a pane clearly off the centre (|y| >= 100), at most 600 tall (not a panel spanning the
    //    screen) and reaching within DM_PKP_EDGE_GAP (160) of the 16:9 frame's edge belongs to that edge (the bag's item
    //    window band: 1920x520 at +180, top edge 100 below the frame top; a menu's map panel near the bottom)
    float half = 0.5f * ((int16_t *)(n + 0xf0))[1] * fabsf(g[5]);
    // Only wide bands (>= 1500: the bag window is 1672): a side panel near the edge (the menu's 616-wide map) belongs with the panel beside
    // it (16:9: the map's bottom lines up with the red menu panel's), which stays centred
    int near_edge = g_edge_gap > 0 && ((int16_t *)(n + 0xf0))[0] * fabsf(g[0]) >= 1500 && fabsf(y) >= 100 && half <= 300 && fabsf(y) + half >= 540 - g_edge_gap;
    //    The container may also be a large centred panel (>= 1200x900) inside a full-screen layout: the bag's 1648x940
    //    panel, whose 1648x1024 bottom section at -314 holds the key help bar
    //    (the bag's panel is drawn at scale 0.97: parents within 10 % of 1). Also in a layout of its own (root at the
    //    centre) without a full-screen container: the menu's 1500x1714 frame, whose key help bar sits at -486
    //    And a layout's root itself (a 4x4 null at the centre without a parent): the bag's and menus' key help is a
    //    layout of its own, a 1920x72 bar placed at (-960, -463) straight under its root
    int16_t *nsz = (int16_t *)(n + 0xf0);
    int at_root = !*(uint64_t *)(par + 0xd0) && nsz[0] >= 1900 && nsz[1] <= 200;   // only a full-width bar (any other root child may be a HUD part drawn under a moved host)
    int screen_box = (ps[0] >= 1900 && ps[1] >= 1060) || ((under_screen || own_screen) && ps[0] >= 1200 && ps[1] >= 900) || at_root;
    if (g_edge_t > 0 && screen_box && fabsf(pg[12]) <= 1 && fabsf(pg[13]) <= 1 && fabsf(pg[5] - 1) <= 0.1f
        && (fabsf(y) >= g_edge_t || near_edge)) move = 1;
    // 2. in screen-height panel layouts without a full-screen container (their outer container >= 1000 tall: menus'
    //    key help parts, 818x200 bars inside 818x600 / 1200x1080 panels placed by their own animations): the top pane of
    //    what sits in the 16:9 edge zone (global |y| >= DM_PKP_EDGE2, default 430) under a parent that does not, and only
    //    a pane that reaches outside its parent's box, never a panel's own piece. Layouts whose root is not at the centre
    //    and HUD sub-layouts (1920x512 strips: the field key help's text rows) are left out: they are drawn under a host
    //    pane, and a moved host has moved them already without their own matrices showing it
    else if (g_edge_t2 > 0 && !under_screen && own_screen && panel_layout && fabsf(y) + 0.5f * ((int16_t *)(n + 0xf0))[1] > 0.5f * ps[1] + 1 && fabsf(gy) >= g_edge_t2 && fabsf(pg[13]) < g_edge_t2 && fabsf(pg[5] - 1) <= 0.01f) move = 1;
    if (!move) return;
    g[13] += copysignf((float)(540.0 * (inv - 1)), gy);
    *fl |= MOVED;
}

// Compare low 32 bits of lr2 so PAC/TBI bits (39..63 on 39-bit-VA Android) do not break T95.
static int t95_caller_is_22bba04(uint64_t fp) {
    if (!g_main_base || fp < 0x10000ull || (fp & 7)) return 0;
    uint64_t caller_fp = 0;
    memcpy(&caller_fp, (const void *)(uintptr_t)fp, sizeof caller_fp);
    if (caller_fp < 0x10000ull || (caller_fp & 7)) return 0;
    uint64_t lr2 = 0;
    memcpy(&lr2, (const void *)(uintptr_t)(caller_fp + 8), sizeof lr2);
    return (uint32_t)lr2 == (uint32_t)(g_main_base + PKP_T95_LR2_OFF);
}

static void proj_done(uint64_t *r, int param) {
    if (param == 6 || param == 7) {
        double a = aspect();
        if (!a || (!is_variant_43() && !ui_on()) || !r[1]) return;
        if (param == 7) {
            uint64_t entry = r[19];
            if (!entry || !*(uint64_t *)(uintptr_t)entry ||
                *(uint32_t *)(uintptr_t)(entry + 0x68) != 0x918000u)
                return;
        }
        float *rect = (float *)(uintptr_t)r[1];
        if (!isfinite(rect[0]) || !isfinite(rect[2])) return;
        float cx = 0.5f * (rect[0] + rect[2]);
        float hw = 0.5f * (rect[2] - rect[0]) * (float)(K169 / a);
        static _Atomic int logged;
        if (!atomic_exchange_explicit(&logged, 1, memory_order_relaxed))
            LOG("pkp aspect %.4f: mask rect (%d) (%.1f..%.1f) -> (%.1f..%.1f)",
                a, param, rect[0], rect[2], cx - hw, cx + hw);
        rect[0] = cx - hw;
        rect[2] = cx + hw;
        return;
    }
    int v43 = is_variant_43();
    if (param == 4) {
        if (v43) pkp_ui43_pre_bake((void *)(uintptr_t)r[0], (void *)(uintptr_t)r[1]);
        return;
    }
    if (param == 5) {
        if (v43) pkp_ui43_post_bake((void *)(uintptr_t)r[19]);
        return;
    }
    double a = aspect();
    if (param == 3) {
        if (v43) pkp_ui43_gmx_fix(r);
        else if (a) pane_rules(r, a);
        return;
    }
    if (param == 2) {
        if (!v43 && a) text_consts(r, a);
        return;
    }
    if (param != 0 && (param != 1 || v43)) return;
    uint64_t cam = r[19];
    if (!a || !cam) return;
    float *p = (float *)(uintptr_t)(cam + CAM_PROJ);
    if (!isfinite(p[0]) || !isfinite(p[5]) || !(fabsf(p[5]) > 1e-6f)) return;
    // Orthographic: only the UI's screen-pixel cameras (P00 = 2/1920: text and 2D layers, near 0.001 far
    // 10000), never the world's (the 64 / 80000 shadow cameras are 16:9 too, but hundreds of units wide)
    if (rdu(cam + CAM_FLAGS) & 1) {
        if (!v43 && close_to(rdf(cam + CAM_ASPECT), K169) && fabsf(fabsf(p[0]) * 960.0f - 1.0f) < 0.01f)
            ui_squeeze(cam, p, a);
        return;
    }
    uint32_t fb = rdu(cam + CAM_FOV);
    if (ours(fb)) {
        if (close_to(rdf(cam + CAM_ASPECT), K169))
            p[0] = copysignf((float)(fabsf(p[5]) / a), p[0]);
        return;
    }
    if (v43) {
        if (fb == PKP_T95_FOV_BITS && t95_caller_is_22bba04(r[29]))
            p[0] /= 0.75f;
    } else if (close_to(rdf(cam + CAM_ASPECT), K169)) {
        ui_squeeze(cam, p, a);
    }
}

__attribute__((constructor)) static void pkp_aspect_attach(void) {
    gate_obs_set(OBS_PKP_CAM_SUBMIT, cam_submit);
    gate_obs_set(OBS_PKP_PROJ_BUILD, proj_build);
    gate_obs_set(OBS_PKP_PROJ_DONE, proj_done);
}
