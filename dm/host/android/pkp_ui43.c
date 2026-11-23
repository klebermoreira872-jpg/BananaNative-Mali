// SPDX-License-Identifier: GPL-3.0-or-later
// Native 4:3 ScreenLayout bake and matrix rules for Pokemon Pokopia v2.0.1 (build-ID check stays in pkp_aspect.c).
// Direct C port of kg175 (lite.c + kg.c) without shadow/probe logging or dead branches.
#include "pkp_ui43.h"
#include <math.h>
#include <stdatomic.h>
#include <stddef.h>
#include <string.h>

typedef struct {
    float sy;
    float add;
    int claimed;   // a placement rule (ext2, frame bands, details, strips) decided this pane; lite alone did not
} pkp_lite_out_t;

enum { PKP_BAKE_STACK_CAP = 16, PKP_CURSOR_ROOT_CAP = 16 };

typedef struct {
    const void *so;
    float sx;
    float sy;
} pkp_bake_frame_t;

static __thread pkp_bake_frame_t g_bake_stack[PKP_BAKE_STACK_CAP];
static __thread int g_bake_top;

// Shared gmx_fix state (T176-T187): written by layout bakes and read on every ScreenLayout matrix join.
// Stale pane pointers are never dereferenced outside active Pause/cursor layouts: outside Pause the
// cursor root's global m00 is 1.0f so gmx_fix exits before touching g_pause_root.
static _Atomic uintptr_t g_pause_root;
static _Atomic uintptr_t g_cursor_roots[PKP_CURSOR_ROOT_CAP];
static _Atomic uint64_t g_c0_pair;

static inline uint8_t rd_u8(const void *b, size_t o) {
    uint8_t v;
    memcpy(&v, (const char *)b + o, sizeof v);
    return v;
}

static inline void wr_u8(void *b, size_t o, uint8_t v) {
    memcpy((char *)b + o, &v, sizeof v);
}

static inline uint16_t rd_u16(const void *b, size_t o) {
    uint16_t v;
    memcpy(&v, (const char *)b + o, sizeof v);
    return v;
}

static inline float rd_f32(const void *b, size_t o) {
    float v;
    memcpy(&v, (const char *)b + o, sizeof v);
    return v;
}

static inline void wr_f32(void *b, size_t o, float v) {
    memcpy((char *)b + o, &v, sizeof v);
}

static inline const void *rd_ptr(const void *b, size_t o) {
    uintptr_t v;
    memcpy(&v, (const char *)b + o, sizeof v);
    return (const void *)v;
}

static inline void *rd_ptr_mut(void *b, size_t o) {
    uintptr_t v;
    memcpy(&v, (const char *)b + o, sizeof v);
    return (void *)v;
}

static inline uint64_t pack_f32_pair(float a, float b) {
    uint32_t ua, ub;
    memcpy(&ua, &a, sizeof ua);
    memcpy(&ub, &b, sizeof ub);
    return (uint64_t)ua | ((uint64_t)ub << 32);
}

static inline void unpack_f32_pair(uint64_t v, float *a, float *b) {
    uint32_t ua = (uint32_t)v;
    uint32_t ub = (uint32_t)(v >> 32);
    memcpy(a, &ua, sizeof *a);
    memcpy(b, &ub, sizeof *b);
}

static void record_cursor_root(uintptr_t g) {
    for (int i = 0; i < PKP_CURSOR_ROOT_CAP; i++) {
        uintptr_t cur = atomic_load_explicit(&g_cursor_roots[i], memory_order_acquire);
        if (cur == g) return;
        if (cur == 0) {
            uintptr_t expected = 0;
            if (atomic_compare_exchange_strong(&g_cursor_roots[i], &expected, g)) return;
            if (expected == g) return;
        }
    }
}

static int has_cursor_root(uintptr_t par) {
    for (int i = 0; i < PKP_CURSOR_ROOT_CAP; i++) {
        uintptr_t cur = atomic_load_explicit(&g_cursor_roots[i], memory_order_acquire);
        if (!cur) return 0;
        if (cur == par) return 1;
    }
    return 0;
}

static int name_is(const void *p, const char *s, unsigned n) {
    const char *q = (const char *)rd_ptr(p, 0xb0);
    if (!q || rd_u16(p, 0x110) != n) return 0;
    return memcmp(q, s, n) == 0;
}

#define NM(q, lit) name_is(q, lit, (unsigned)(sizeof(lit) - 1))

static int pfx(const void *q, const char *s, unsigned n) {
    const char *nm = (const char *)rd_ptr(q, 0xb0);
    if (!nm || rd_u16(q, 0x110) < n) return 0;
    return memcmp(nm, s, n) == 0;
}

static int is_window_name(const void *p) {
    const char *q = (const char *)rd_ptr(p, 0xb0);
    return q && rd_u16(p, 0x110) > 7 && memcmp(q, "Window_", 7) == 0;
}

static int namish(const void *c) {
    const char *q = (const char *)rd_ptr(c, 0xb0);
    return q && rd_u16(c, 0x110) >= 5 && (q[0] == 'W' || q[0] == 'w') && q[1] == 'i' && q[2] == 'n' &&
           (q[3] == '_' || q[3] == 'd');
}

// Global (x, y) of the Things-to-Do popup's cursor arrow host (CL_0000_parts_cursor_triangle under Null_hint_pokemon), seen at
// the matrix join; see gmx_skip_popup_host.
static _Atomic uint64_t g_popup_host_t;
static _Atomic int g_popup_host_set;

static int cov_pane2(const void *c) {
    int k = rd_u8(c, 0x112);
    unsigned w = rd_u16(c, 0xf0), h = rd_u16(c, 0xf2);
    return (k == 3 || namish(c)) && w >= 800 && h >= 1150 && h <= 1300;
}

static int layout_cover2(const void *p) {
    const void *c = p;
    if (cov_pane2(p)) return 1;
    for (int n = 0; n < 256 && c; n++) {
        const void *nd = rd_ptr(c, 0xc8);
        if (!nd) break;
        nd = rd_ptr(nd, 0);
        if (!nd) break;
        c = rd_ptr(nd, 0x10);
        if (c && cov_pane2(c)) return 3;
    }
    c = p;
    for (int n = 0; n < 256 && c; n++) {
        const void *nd = rd_ptr(c, 0xc8);
        if (!nd) break;
        nd = rd_ptr(nd, 8);
        if (!nd) break;
        c = rd_ptr(nd, 0x10);
        if (c && cov_pane2(c)) return 1;
    }
    return 0;
}

// The layout's pane list is a doubly linked ring of nodes: pane+0xc8 is the pane's own node, node+0 the previous node,
// node+8 the next, node+0x10 the pane.
static const void *pane_step(const void *c, size_t dir) {
    const void *nd = rd_ptr(c, 0xc8);
    nd = nd ? rd_ptr(nd, dir) : NULL;
    return nd ? rd_ptr(nd, 0x10) : NULL;
}

// A Window that frames a popup or dialog: 1600+ wide and 880..1300 tall. On the 16:9 screens frames measure 82..96 % of the
// screen height and floating boxes 26..29 %, so a Window this tall is a full-height frame whatever it is called. The size bands
// that cam_ext already frames (the Pokedex sheet 1850x1016 / 1740x908) and the cover sizes (>= 1900x1060) keep their own
// rules and do not make a layout a popup layout.
static int popup_window(const void *c) {
    int k = rd_u8(c, 0x112);
    unsigned w = rd_u16(c, 0xf0), h = rd_u16(c, 0xf2);
    if (!(k == 3 || namish(c)) || w < 1600 || h < 880 || h > 1300) return 0;
    if (w <= 1920 && w >= 1850 && h >= 1000 && h <= 1060) return 0;
    if (w >= 1740 && w <= 1800 && h >= 900 && h <= 945) return 0;
    return !(w >= 1900 && h >= 1060);
}

static int popup_layout(const void *p) {
    if (popup_window(p)) return 1;
    for (size_t dir = 0; dir <= 8; dir += 8) {
        const void *c = p;
        for (int n = 0; n < 256 && c; n++) {
            c = pane_step(c, dir);
            if (c && popup_window(c)) return 1;
        }
    }
    return 0;
}

static int in_details(const void *p) {
    int d = 0;
    for (const void *q = p; q && d < 10; q = rd_ptr(q, 0xd0), d++) {
        if (NM(q, "Null_311_features") || NM(q, "Null_312_encounter_location") || NM(q, "Null_313_likes") ||
            NM(q, "Null_back_base") || NM(q, "Null_name"))
            return 1;
        if (NM(q, "Null_pokemon") && rd_u16(q, 0xf0) == 764) return 1;
        if (NM(q, "Null_tab") && rd_u16(q, 0xf0) == 644) return 1;
    }
    return 0;
}

// Anchors: [bit7=exact | len][u16 width_lo][u16 width_hi][prefix], NUL-terminated.
static const char k_anch[] =
    "\x12\x00\x00" "Null_habitat_still"
    "\x08\x78\x03" "Null_All"
    "\x0a\x32\x00" "Null_flame"
    "\x0c\x00\x00" "Null_txtline"
    "\x0e\x00\x00" "CL_0361_part_t"
    "\x16\x00\x00" "0300_base_tutorial_txt"
    "\x11\x00\x00" "TextBox__contents"
    "\x08\x00\x00" "CL_0314_"
    "\x11\x00\x00" "0000_base_common_"
    "\x0f\x00\x00" "Null_conditions"
    "\x0a\x00\x00" "Null_title"
    "\x09\x32\x00" "Null_info"
    "\x0c\x32\x00" "Null_pokemon"
    "\x86\x80\x07" "Window"
    "\x0c\x00\x00" "scroll_anime"
    "\x16\x00\x00" "Null_collection_camera"
    "\x89\x58\x01" "Null_base"
    "\x10\x80\x07" "Null_misson_list"
    "\x85\xd6\x06" "inout"
    "\x08\x52\x03" "Null_All"
    "\x08\x0e\x06" "Null_All"
    "\x08\xa4\x06" "Null_All"
    "\x0c\x5c\x03" "Null_ani_all"
    "\x10\x48\x02" "Null_cursor_chat"
    "\x11\x54\x02" "Null_cursol_emote";

static int in_fam2(const void *p) {
    int d = 0;
    for (const void *q = p; q && d < 10; q = rd_ptr(q, 0xd0), d++) {
        const char *nm = (const char *)rd_ptr(q, 0xb0);
        unsigned L = rd_u16(q, 0x110), x = 1;
        if (!nm) continue;
        for (const unsigned char *e = (const unsigned char *)k_anch; *e; e += 3 + (e[0] & 0x7f), x++) {
            unsigned n = e[0] & 0x7f, w = (unsigned)e[1] | ((unsigned)e[2] << 8);
            if (L < n || ((e[0] & 0x80) && L != n) || (w && rd_u16(q, 0xf0) != w)) continue;
            if (memcmp(nm, e + 3, n) == 0) return (d << 8) | (int)x;
        }
    }
    return 0;
}

static int pc169(const void *p, const void *t) {
    const void *pp = rd_ptr(p, 0xd0);
    if (!pp) return 0;
    if (NM(pp, "Null_All") && pfx(p, "CL_0800_parts_menu_btn_", 23)) return 1;
    if (NM(pp, "Null_All") && NM(p, "posi_btn_S")) return 1;
    if (NM(pp, "Null_ani_all")) {
        int tx = (int)rd_f32(t, 0x30), ty = (int)rd_f32(t, 0x34);
        if (pfx(p, "Null_table_", 11)) return 1;
        if (tx == -608 && (ty == 333 || ty == 158)) return 1;
    }
    return 0;
}

// A list row: a pane the row rules below place at full-scale position (pc169 Null_table_* under Null_ani_all, the Habitat
// rows 1500x240, the recipe rows 640x128). Sizes are read from the unbaked pane, so the test is for a pane that follows
// its parent in the layout.
static int list_row(const void *c, const void *par) {
    const void *t = rd_ptr(c, 0xe8);
    unsigned w = rd_u16(c, 0xf0), h = rd_u16(c, 0xf2);
    if (NM(par, "Null_ani_all") && pfx(c, "Null_table_", 11)) return 1;
    if (w == 640 && h == 128) return 1;
    return t && w == 1500 && h == 240 && (int)rd_f32(t, 0x30) == 0;
}

// The pane that moves a list's rows when it scrolls (Challenges Null_ani_all, Habitat Dex Null_habitat_table, the
// recipe book's Null_scroll_anime). The layout animation writes its translation as [pane+0x14c] * key (main+0x1f73880..
// 0x1f738c0, absolute, the bake's add is not included) and the bake stores the pane's y scale in [pane+0x14c] (main+
// 0x1f854d4). The rows sit at full-scale positions (add = 0.25 s ty), so a carrier baked at 0.75 moves them 0.75 * key and
// the last rows end 0.25 * key too low (see the game note, "List scrolling").
static int scroll_carrier(const void *p) {
    const void *c = pane_step(p, 8);
    return c && rd_ptr(c, 0xd0) == p && list_row(c, p);
}

enum { PKP_ROOT_CACHE_CAP = 4 };
static __thread struct { const void *root; float dy; } g_root_dy[PKP_ROOT_CACHE_CAP];
static __thread int g_root_dy_next;

// Edge anchor for a standalone part whose root is a screen-wide strip (Null_All 1920x500, build materials 07d796d6)
// while its content overhangs the root's bottom (a white body 1920x234 at ty -310). lite_decide cannot call it a screen:
// the root is 500 tall. Its children are the screen-level units, so the bottom overhang is read from them: the lowest
// extent of the non-strip children, found while they are all unbaked (when the first child is decided) and kept for the
// others. Same clamp as the screen rule; the 16:9 edge distance is kept and the key guide below sits where it does there.
static float root_overhang_dy(const void *p, float lim, float hlim) {
    const void *q = rd_ptr(p, 0xd0);
    if (!q || rd_u8(q, 0x112) != 0 || (float)rd_u16(q, 0xf0) < lim || (float)rd_u16(q, 0xf2) >= hlim) return 0.0f;
    const void *qp = rd_ptr(q, 0xd0);
    if (qp && (rd_u16(qp, 0xf0) >= 8 || rd_ptr(qp, 0xd0))) return 0.0f;
    if (pane_step(p, 0) == q) {
        const void *qt = rd_ptr(q, 0xe8);
        float qb = qt ? rd_f32(qt, 0x34) - (1.0f - (float)(rd_u8(q, 0x10c) & 15) * 0.5f) * (float)rd_u16(q, 0xf2) : 0.0f;
        float b = 1e9f, dy = 0.0f;
        for (const void *c = p; c; c = pane_step(c, 8)) {
            const void *t = rd_ptr(c, 0xe8);
            if (rd_ptr(c, 0xd0) != q || !t || (rd_u16(c, 0xf0) >= 1800 && rd_u16(c, 0xf2) <= 150)) continue;
            float av = (float)(rd_u8(c, 0x10c) & 15) * 0.5f;
            float bc = rd_f32(t, 0x34) - (1.0f - av) * (float)rd_u16(c, 0xf2);
            if (bc < b) b = bc;
        }
        // Any bottom below -360 gives the screen rule its -135 clamp (dn = -540 - 0.75 b <= -135 up to b = -540, and the
        // ext2 snap makes the few units beyond it -135 as well), so the units of one sheet agree on the clamp.
        if (b < -360.0f && b < qb - 1.0f) dy = -135.0f;
        int slot = g_root_dy_next;
        for (int i = 0; i < PKP_ROOT_CACHE_CAP; i++)
            if (g_root_dy[i].root == q) slot = i;
        if (slot == g_root_dy_next) g_root_dy_next = (g_root_dy_next + 1) % PKP_ROOT_CACHE_CAP;
        g_root_dy[slot].root = q;
        g_root_dy[slot].dy = dy;
    }
    for (int i = 0; i < PKP_ROOT_CACHE_CAP; i++)
        if (g_root_dy[i].root == q) return g_root_dy[i].dy;
    return 0.0f;
}

static pkp_lite_out_t lite_decide(const void *so, const void *p) {
    pkp_lite_out_t o;
    float s = rd_f32(so, 0x10), lim = 1800.0f * (s < 1.0f ? s : 1.0f);
    float hlim = 700.0f * (s < 1.0f ? s : 1.0f);
    const void *q = rd_ptr(p, 0xd0);
    int type = rd_u8(p, 0x112), screen = 0;
    float w = rd_u16(p, 0xf0), h = rd_u16(p, 0xf2);
    o.sy = rd_f32(so, 0x14);
    o.add = 0.0f;
    o.claimed = 0;
    while (q) {
        const void *t = rd_ptr(q, 0xe8);
        // Full-width strips (h < hlim) are section/bar containers rather than the screen root;
        // q's height at +0xf2 is already baked by 0.75 * s (1080 -> 810 * s >= 700 * s, vs strips <= 391 * s),
        // while full-screen Null sub-layouts (e.g. dyeing list inside Null_tab) stay screen-relative via unbaked p.
        if ((float)rd_u16(q, 0xf0) >= lim && ((float)rd_u16(q, 0xf2) >= hlim || (type == 0 && w >= lim && h >= hlim))) {
            screen = 1;
            break;
        }
        if (rd_u16(q, 0xf0) != 0 || !t || fabsf(rd_f32(t, 0x30)) >= 1.0f || fabsf(rd_f32(t, 0x34)) >= 1.0f) break;
        q = rd_ptr(q, 0xd0);
    }
    if (screen) {
        const void *t = rd_ptr(p, 0xe8);
        if (type != 0 && type != 2 && w >= 1824.0f && h >= 1026.0f) { o.sy = s; return o; }
        if (!t) return o;
        float ty = rd_f32(t, 0x34), av = (float)(rd_u8(p, 0x10c) & 15) * 0.5f, cy = ty + (av - 0.5f) * h;
        // T27 (lite4): panels centred near screen centre stay put so child icons and headers keep registration.
        // 185 keeps bottom build strip (loop_all ty=-190) edge-clamped while centered dialogs (<=180) stay put.
        if (fabsf(cy) < 185.0f) return o;
        // Centered square Null FX/icon containers (move-learn halo/aura/skill icon) keep add=0 with their sibling
        // particles/characters inside the 720-unit band, while bottom-right HUD disc landings (tx=763, cy=-410) still edge-shift.
        if (type == 0 && w == h && w <= 600.0f && fabsf(rd_f32(t, 0x30)) < 300.0f && fabsf(cy) < 360.0f) return o;
        // T29 (lite5): small top-edge unit (coin pill) following a phone-body panel stays docked to the body.
        if (w <= 400.0f && h <= 100.0f && ty + av * h > 360.0f) {
            const void *c = p;
            for (int n = 0; n < 512 && c; n++) {
                const void *nd = rd_ptr(c, 0xc8);
                if (!nd) break;
                nd = rd_ptr(nd, 0);
                if (!nd) break;
                c = rd_ptr(nd, 0x10);
                if (c) {
                    int ct = rd_u8(c, 0x112);
                    unsigned cw = rd_u16(c, 0xf0), ch = rd_u16(c, 0xf2);
                    if (ct != 0 && ct != 2 && ch >= 780 && cw >= 900 && cw < 1400) return o;
                }
            }
        }
        float T = ty + av * h, B = ty - (1.0f - av) * h;
        float up = 540.0f - 0.75f * T, dn = -540.0f - 0.75f * B, dy = 0.0f;
        if (T > 360.0f) dy += up < 135.0f ? up : 135.0f;
        if (B < -360.0f) dy += dn > -135.0f ? dn : -135.0f;
        o.add = dy * s;
    } else if (!(w >= 1800.0f && h <= 150.0f)) {
        o.add = root_overhang_dy(p, lim, hlim) * s;
    }
    return o;
}

// The Memories viewer (layout 19237b8c) draws the captured photo in a 1460x830 Window (the white frame) and a 1440x810
// Picture (the photo) under Null_photo (50x50) in Null_photo_all. A photo is a snapshot of the game's frame, and in this
// variant the frame holds the 4:3 world stretched to 16:9 (the host squeezes it back to 4:3 on the display). A 16:9 pane
// at the layout's uniform (1.0, 0.75) is a 16:9 rectangle on the display, so the photo came out 4/3 too wide. Baking both
// panes at (0.75, 0.75) gives 1080x607 frame units: 720x540 px of 1280x960, 4:3 as the photo is, with the same height.
static int photo_view(void *so, const void *p, pkp_lite_out_t *o) {
    const void *pp = rd_ptr(p, 0xd0), *gp = pp ? rd_ptr(pp, 0xd0) : NULL;
    if (!gp || !NM(pp, "Null_photo") || rd_u16(pp, 0xf0) > 100 || !NM(gp, "Null_photo_all")) return 0;
    int k = rd_u8(p, 0x112);
    unsigned w = rd_u16(p, 0xf0), h = rd_u16(p, 0xf2);
    if (!((k == 3 && NM(p, "Window") && w == 1460 && h == 830) ||
          (k == 1 && NM(p, "0000_prt_dummy_0") && w == 1440 && h == 810)))
        return 0;
    float sc = rd_f32(so, 0x10);
    wr_f32(so, 0x10, 0.75f * sc);   // post_bake restores it
    o->sy = 0.75f * sc;
    o->add = 0.0f;
    return 1;
}

static int ext2(void *so, void *p, void *t, pkp_lite_out_t *o) {
    static const float k175[4] = {1.33333333f, -300.0f, -604.5f, -67.0f};
    static const float k193 = 233.16f;
    static const float k200[2] = {-135.0f, 68.25f};
    if (photo_view(so, p, o)) return 1;
    int k = rd_u8(p, 0x112);
    unsigned w = rd_u16(p, 0xf0), h = rd_u16(p, 0xf2);
    float sc = rd_f32(so, 0x10);
    {
        const void *pp = rd_ptr(p, 0xd0);
        if (t && NM(p, "0300_prt_pokedex_open") && pp)
            atomic_store_explicit(&g_pause_root, (uintptr_t)pp, memory_order_release);
        if (pp && NM(p, "0000_prt_cursor_triangle_000_00")) {
            const void *g = rd_ptr(pp, 0xd0);
            if (g) record_cursor_root((uintptr_t)g);
        }
    }
    if (t && NM(p, "0300_prt_pokedex_open")) {
        void *pp = rd_ptr_mut(p, 0xd0);
        void *gp = pp ? rd_ptr_mut(pp, 0xd0) : NULL;
        void *gt = gp ? rd_ptr_mut(gp, 0xe8) : NULL;
        if (gp && gt) {
            wr_f32(gp, 0xf4, k175[0]);
            wr_f32(gp, 0xf8, k175[0]);
            wr_f32(gt, 0x30, k175[1]);
            wr_u8(gp, 0x104, (uint8_t)(rd_u8(gp, 0x104) & ~4u));
        }
    }
    if (t && w == 512 && h == 512 && NM(p, "CL_0200_parts_hud_minimap")) {
        wr_f32(p, 0xf4, k175[0]);
        wr_f32(p, 0xf8, k175[0]);
        wr_f32(t, 0x30, k175[2]);
        o->add = k175[3] * sc;
        return 1;
    }
    int hold = 0;
    if (t && o->add == 0.0f) {
        for (const void *q = rd_ptr(p, 0xd0); q;) {
            const void *qp = rd_ptr(q, 0xd0), *qt;
            if (!qp) { hold = rd_u16(q, 0xf0) < 8; break; }
            if (rd_u16(q, 0xf0) != 0 || !(qt = rd_ptr(q, 0xe8)) ||
                fabsf(rd_f32(qt, 0x30)) >= 1.0f || fabsf(rd_f32(qt, 0x34)) >= 1.0f)
                break;
            q = qp;
        }
        if (hold) {
            float av = (float)(rd_u8(p, 0x10c) & 15) * 0.5f, ty = rd_f32(t, 0x34);
            float T = ty + av * (float)h, B = ty - (1.0f - av) * (float)h;
            float up = 540.0f - 0.75f * T, dn = -540.0f - 0.75f * B, dy = 0.0f;
            if (T > 360.0f) dy += up < 135.0f ? up : 135.0f;
            if (B < -360.0f) dy += dn > -135.0f ? dn : -135.0f;
            o->add = dy * sc;
        }
    }
    if (t) {
        float av = (float)(rd_u8(p, 0x10c) & 15) * 0.5f;
        float B = rd_f32(t, 0x34) - (1.0f - av) * (float)h, dn = -540.0f - 0.75f * B;
        if (B < -540.0f && dn > -135.0f && fabsf(o->add - dn * sc) < 0.5f * sc) o->add = -135.0f * sc;
    }
    if (t) {
        float av = (float)(rd_u8(p, 0x10c) & 15) * 0.5f;
        float T = rd_f32(t, 0x34) + av * (float)h, up = 540.0f - 0.75f * T;
        if (T > 540.0f && up < 135.0f && fabsf(o->add - up * sc) < 0.5f * sc) o->add = 135.0f * sc;
    }
    if (t && layout_cover2(p)) {
        if (k == 3 || is_window_name(p) || (w >= 1900 && h >= 1060)) {
            o->sy = sc;
            o->add = 0.0f;
        } else {
            o->sy = rd_f32(so, 0x14);
            o->add = 0.25f * sc * rd_f32(t, 0x34);
        }
        return 1;
    }
    // Challenges cursor host (ac6b2753 CL_0000_parts_cursor_triangle under Null_ani_all, rest ty 333 = 175 above row 0 at
    // 158). The game moves the cursor to the selected card by the host's baked rest offset from row 0, and that offset
    // lands in the cards' 0.75 space: rest the host at row 0's full-scale position plus 0.75 * 175. Baked at full scale
    // (pc169) the arrow floated 0.25 * 175 units (~42 px) above the card; with this rule it meets the card as in 16:9.
    if (t && (int)rd_f32(t, 0x30) == -608 && (int)rd_f32(t, 0x34) == 333 && NM(p, "CL_0000_parts_cursor_triangle")) {
        o->sy = rd_f32(so, 0x14);
        o->add = 0.25f * sc * 158.0f;
        return 1;
    }
    // Things-to-Do popup cursor host (814b184d, tx -540 ty 84 under Null_hint_pokemon): the same mechanism. Its target
    // cursor_character_0000 rests at ty -3, so rest the host at that full-scale position (add = 0.25 * -3) and the game's
    // offset of 87 lands at 0.75 * 87 as the cards' space does, instead of 87 at full scale (~19 px too high).
    if (t && (int)rd_f32(t, 0x30) == -540 && (int)rd_f32(t, 0x34) == 84 && NM(p, "CL_0000_parts_cursor_triangle")) {
        const void *hp = rd_ptr(p, 0xd0);
        if (hp && NM(hp, "Null_hint_pokemon")) {
            o->sy = rd_f32(so, 0x14);
            o->add = 0.25f * sc * -3.0f;
            return 1;
        }
    }
    if (t && pc169(p, t)) { o->sy = rd_f32(so, 0x14); o->add = 0.25f * sc * rd_f32(t, 0x34); return 1; }
    if (t && NM(p, "Null_skilllist_all") && w == 840) {
        const void *pp = rd_ptr(p, 0xd0), *pt = pp ? rd_ptr(pp, 0xe8) : NULL;
        float ty = rd_f32(t, 0x34), pty = pt ? rd_f32(pt, 0x34) : 0.0f;
        o->sy = (ty < -1.0f || ty > 1.0f) ? sc * (ty + 0.25f * pty) / ty : sc;
        o->add = 0.0f;
        return 1;
    }
    if (t) {
        const void *pp = rd_ptr(p, 0xd0);
        if (pp && NM(pp, "Null_skilllist_all") && rd_u16(pp, 0xf0) == 840) {
            o->sy = rd_f32(so, 0x14);
            o->add = 0.25f * sc * rd_f32(t, 0x34);
            return 1;
        }
    }
    if (w == 24 && ((k && (h == 696 || h == 36)) || (t && k == 0 && (h == 696 || h == 680)))) {
        o->sy = sc;
        o->add = (t && (int)rd_f32(t, 0x30) == 758 ? 95.0f : 0.0f) * sc;
        return 1;
    }
    if (t && k && w == 720 && h == 100 && (int)rd_f32(t, 0x30) == 0 && (int)rd_f32(t, 0x34) == 428) {
        o->add = 0.25f * sc * 428.0f;
        return 1;
    }
    if (t && k == 0 && w == 128 && h == 184 && NM(p, "CL_0342_parts_wheel_key")) {
        wr_f32(p, 0xf8, rd_f32(p, 0xf8) * 0.75f);
        return 1;
    }
    {
        int d = 0;
        for (const void *q = p; q && d < 6; q = rd_ptr(q, 0xd0), d++) {
            if (NM(q, "Null_All") && rd_u16(q, 0xf0) == 128 && rd_u16(q, 0xf2) == 184) {
                o->sy = sc;
                o->add = 0.0f;
                return 1;
            }
        }
    }
    if (t && k == 0 && NM(p, "Null_list_set")) {
        const void *pp = rd_ptr(p, 0xd0);
        if (pp && NM(pp, "Null_All") && rd_u16(pp, 0xf0) == 640) { o->sy = sc; o->add = 0.0f; return 1; }
    }
    // Scroll carriers take the rows' full-scale factor so the animated scroll offset matches them. Static ty of every
    // carrier found is 0; a carrier with one would sit at ty * sc, like the rows it moves.
    if (t && k == 0 && scroll_carrier(p)) { o->sy = sc; o->add = 0.0f; return 1; }
    int f = in_fam2(p);
    if (f) {
        if (f > 0x100 && (f & 0xff) == 1) return 1;
        if (f == 0x110 && t) {
            if (w == 1920 && h == 122) { o->sy = sc * (444.5f / 450.0f); o->add = 0.0f; }
            else o->add = 0.25f * sc * rd_f32(t, 0x34);
            return 1;
        }
        if (f == 0x112 && w == 1680 && h == 1548) { o->sy = sc; o->add = 79.6f * sc; return 1; }
        if (f == 15) { o->sy = sc; o->add = 0.0f; return 1; }
        if ((f & 0xff) == 16 && w == 4 && h == 560) { o->sy = sc; o->add = 0.0f; return 1; }
        if ((f & 0xff) == 17) { o->sy = rd_f32(so, 0x14); o->add = 0.0f; return 1; }
        if (f == 24 || f == 25) { o->sy = sc; o->add = 0.0f; return 1; }
        if ((f & 0xff) == 23 && k && w == 960 && h == 1100) { o->sy = sc; o->add = 0.0f; return 1; }
        if (k == 3 || is_window_name(p) || (w >= 1900 && h >= 1060) || f == 0x115) {
            o->sy = sc;
            o->add = 0.0f;
            return 1;
        }
        if (t) o->add = 0.25f * sc * rd_f32(t, 0x34);
        return 1;
    }
    if (k == 1 && w <= 1960 && h <= 1100 && o->sy == sc && o->add == 0.0f && w >= 1824 && h >= 1026) {
        wr_f32(so, 0x10, sc / 0.75f);
        return 1;
    }
    if (k && ((w == 476 && h == 316) || (w == 500 && h == 644))) { o->sy = sc; o->add = 0.0f; return 1; }
    if (t && k && ((w == 876 && h == 905) || (w == 780 && (int)rd_f32(t, 0x30) == -425))) {
        o->sy = sc;
        o->add = 0.0f;
        return 1;
    }
    if (t && k && w == 1920 && (int)rd_f32(t, 0x30) == 0 &&
        (h == 183 || h == 49 || h == 64 || h == 88 || h == 460 || h == 240 || h == 354 || h == 177)) {
        o->sy = sc;
        o->add = 0.0f;
        return 1;
    }
    if (t && k && ((w == 432 && h == 256) || (w == 368 && h == 200)) &&
        (int)rd_f32(t, 0x30) == 0 && (int)rd_f32(t, 0x34) == 0) {
        o->sy = sc;
        o->add = 0.0f;
        return 1;
    }
    if (t && k && w == 1920 && h == 360) { o->add = 0.0f; return 1; }
    {
        const void *pp = rd_ptr(p, 0xd0);
        const char *nm = (const char *)rd_ptr(p, 0xb0);
        if (t && k && w == 128 && h == 128 && pp && nm && rd_u16(p, 0x110) == 20 &&
            nm[5] == 'b' && NM(pp, "Null_base")) {
            const void *ppp = rd_ptr(pp, 0xd0);
            if (ppp && NM(ppp, "Null_item_scale")) {
                wr_f32(p, 0xf8, rd_f32(p, 0xf8) * 0.75f);
                return 1;
            }
        }
    }
    if (t && k && w == 544 && h == 52) { o->add = -0.25f * sc * rd_f32(t, 0x34); o->claimed = 1; }
    if (t && k == 0) {
        int tx = (int)rd_f32(t, 0x30), ty = (int)rd_f32(t, 0x34);
        if (w == 654 && h == 128 && tx == -683) { o->add = (0.25f * (float)ty - 9.25f) * sc; return 1; }
        if (w == 654 && h == 128 && (tx == -759 || tx == -699)) {
            o->add -= (float)(tx == -759 ? 74 : 53) * sc;
            return 1;
        }
        if (w == 108 && h == 108 && tx == 0 && ty == -18) { o->add = 8.0f * sc; return 1; }
        if ((w == 1730 && (h == 1280 || h == 256)) || (w == 1650 && (h == 1098 || h == 132)) ||
            (w == 640 && (h == 620 || h == 128)) || (w == 428 && h == 108) ||
            (w == 1920 && h == 122 && tx == 0 && ty >= 440)) {
            o->add = 0.25f * sc * rd_f32(t, 0x34) - (ty == 444 ? 6.0f * sc : 0.0f);
            return 1;
        }
        if (w == 1920 && h == 90 && ty == 45) { o->add = 8.5f * sc; return 1; }
        if (w == 84 && h == 84 && tx == -648) { o->add = -6.75f * sc; return 1; }
        if (w == 24 && h == 24 && tx == -144 && ty == 238) { o->add = 0.0f; return 1; }
        if (w == 654 && h == 128 && tx == -506 && ty == 377) { o->add = 0.25f * sc * k193; return 1; }
        if ((w == 84 && h == 84 && (tx == -648 || tx == -659)) || (w == 1500 && h == 240 && tx == 0) ||
            (w == 421 && h == 72 && tx == 563 && ty == -178)) {
            o->add = 0.25f * sc * rd_f32(t, 0x34);
            return 1;
        }
        if (tx == -610 && ty == 351 && NM(p, "CL_0000_parts_cursor_triangle")) { o->add = k200[0] * sc; return 1; }
        if (tx == 639 && ty == 273 && NM(p, "CL_0300_parts_mission_tutorial")) { o->add = k200[1] * sc; return 1; }
    }
    return 0;
}

static void cam_ext(void *so, void *p, void *t, pkp_lite_out_t *o) {
    if (ext2(so, p, t, o)) { o->claimed = 1; return; }
    int k = rd_u8(p, 0x112), hit = 0;
    unsigned w = rd_u16(p, 0xf0), h = rd_u16(p, 0xf2);
    if (k == 3 && ((w >= 1740 && w <= 1800 && h >= 76 && h <= 88) || (w >= 540 && w <= 570 && h >= 50 && h <= 56))) {
        o->sy = rd_f32(so, 0x10);
        o->claimed = 1;
    }
    if (k == 3 && ((w >= 285 && w <= 330 && h >= 285 && h <= 330) || (w >= 84 && w <= 100 && h >= 84 && h <= 100))) {
        o->sy = rd_f32(so, 0x10);
        o->claimed = 1;
    }
    if (k == 3 && ((w >= 1850 && w <= 1920 && h >= 1000 && h <= 1060) || (w >= 1740 && w <= 1800 && h >= 900 && h <= 945))) {
        o->sy = rd_f32(so, 0x10);
        o->claimed = 1;
    }
    if (in_details(p)) {
        float sc = rd_f32(so, 0x10);
        o->claimed = 1;
        if (w >= 2300 && h >= 1060 && k != 3 && !is_window_name(p)) { o->sy = sc; o->add = 0.0f; return; }
        if (k == 3 || is_window_name(p) || (w == 764 && h == 1024)) { o->sy = sc; o->add = 0.0f; return; }
        if (NM(p, "off_screen")) { o->add = -71.0f * sc; return; }
        if (t) o->add = 0.25f * sc * rd_f32(t, 0x34);
        return;
    }
    if (!t) return;
    {
        int tx = (int)rd_f32(t, 0x30), ty = (int)rd_f32(t, 0x34);
        if (k == 0) {
            if (w >= 120 && w <= 220) hit = ty == -406 || ty == -383 || ty == -349;
            else if (w >= 1700 && w <= 1900) hit = tx == 0 && ty == 298;
            else if (w >= 500 && w <= 545) hit = ty == -411;
            else if (w >= 600 && w <= 640) hit = tx == 0 && ty == 481;
        } else if (w == 84 || w == 42) {
            hit = (tx == -790 || tx == 839 || tx == 769 || tx == -860) && (ty == 0 || ty == 108 || ty == -108);
        }
        int row = ty == 257 || ty == 97 || ty == -63 || ty == -223 || ty == -383 || ty == -543 || ty == -703;
        int full = 0;
        if (k == 0) {
            if (w == 1920 && h == 122) hit |= tx == 0 && ty == 450;
            else if (w == 1500 && h == 772) hit |= tx == 0 && (ty == 416 || ty == 440 || ty == 160);
            else if (w == 1500 && h == 180) hit |= tx == 0 && row;
            else if ((w == 180 && h == 180) || (w == 256 && h == 60)) hit |= tx == -587 && ty == 257;
            else if (w == 654 && h == 128) hit |= tx == -587 && ty == 346;
        } else {
            if (k == 3) {}
            else if (w == 256 && h == 1024) full = (tx == -744 || tx == 744) && ty == 0;
            else if (w == 1308 && h == 160) full = (tx == -13 && row) || (tx == 0 && ty == 0);
            else if (w == 1940 && h == 1100) full = tx == 0 && ty == 4;
        }
        if (full) { o->sy = rd_f32(so, 0x10); o->add = 0.0f; o->claimed = 1; return; }
    }
    if (hit) {
        o->add = 0.25f * rd_f32(so, 0x10) * rd_f32(t, 0x34);
        o->claimed = 1;
    }
}

// Popup and dialog layouts (see popup_window): the frame behind them is a full-height frame, so the popup is one too. Its
// frame Windows and full-size Pictures take the full height and everything else sits at full-scale position (the same
// treatment as every other full-height frame). Runs only for panes no other rule placed, so the layouts that carry their
// own rules keep them.
static void popup_place(void *so, const void *p, const void *t, pkp_lite_out_t *o) {
    int k = rd_u8(p, 0x112);
    unsigned w = rd_u16(p, 0xf0), h = rd_u16(p, 0xf2);
    float sc = rd_f32(so, 0x10);
    // Panel-size Windows (the frame and its masks, the text and comment boxes: their text sits at full-scale positions, so the
    // box stretches with it) and covers take the full height. Small decorations (both sides under 400: the round empty
    // Pokemon slots, the badges; in the popup-rule layouts the Windows measure 150x56 .. 360x352 or 425x108 and up) keep the
    // stock size at their full-scale position.
    if (((k == 3 || is_window_name(p)) && (w >= 400 || h >= 400)) || (k != 0 && w >= 1900 && h >= 1060)) {
        o->sy = sc;
        o->add = 0.0f;
    } else {
        o->sy = rd_f32(so, 0x14);
        o->add = 0.25f * sc * rd_f32(t, 0x34);
    }
}

static pkp_lite_out_t kg_decide2(void *so, void *p) {
    pkp_lite_out_t o = lite_decide(so, p);
    void *t = rd_ptr_mut(p, 0xe8);
    if (t && rd_u16(p, 0xf0) >= 1800 && rd_u16(p, 0xf2) <= 150 && fabsf(rd_f32(t, 0x34)) >= 1.0f) {
        float s = rd_f32(so, 0x10), ty = rd_f32(t, 0x34), h = rd_u16(p, 0xf2);
        float av = (float)(rd_u8(p, 0x10c) & 15) * 0.5f;
        float T = ty + av * h, B = ty - (1.0f - av) * h;
        float up = 540.0f - 0.75f * T, dn = -540.0f - 0.75f * B, dy = 0.0f;
        if (T > 360.0f) dy += up < 135.0f ? up : 135.0f;
        if (B < -360.0f) dy += dn > -135.0f ? dn : -135.0f;
        if (dy < 0.0f && o.add == 0.0f) dy += 9.0f;
        o.add = dy * s;
        o.claimed = 1;
    }
    if (t && rd_u16(p, 0xf0) == 512 && rd_u16(p, 0xf2) == 512 &&
        rd_f32(t, 0x30) < -600.0f && rd_f32(t, 0x34) < -200.0f)
        o.add = 0.0f;
    cam_ext(so, p, t, &o);
    if (rd_u8(p, 0x112) == 3 && rd_u16(p, 0xf0) >= 1836 && rd_u16(p, 0xf0) <= 1844) {
        o.sy = rd_f32(so, 0x10);
        o.claimed = 1;
    }
    if (!o.claimed && t && popup_layout(p)) popup_place(so, p, t, &o);
    return o;
}

void pkp_ui43_pre_bake(void *so, void *p) {
    if (!so || !p) return;
    // T194 defensive reset: if so+0x10 entered inflated from an interrupted T193 cover bake, restore sx first.
    float sy_cur = rd_f32(so, 0x14);
    if (sy_cur > 0.0f) {
        float base_sx = sy_cur / 0.75f;
        if (rd_f32(so, 0x10) > base_sx * 1.25f) wr_f32(so, 0x10, base_sx);
    }
    float orig_sx = rd_f32(so, 0x10);
    float orig_sy = rd_f32(so, 0x14);
    if (g_bake_top < PKP_BAKE_STACK_CAP) {
        g_bake_stack[g_bake_top].so = so;
        g_bake_stack[g_bake_top].sx = orig_sx;
        g_bake_stack[g_bake_top].sy = orig_sy;
        g_bake_top++;
    }
    pkp_lite_out_t o = kg_decide2(so, p);
    wr_f32(so, 0x14, o.sy);
    wr_f32(so, 0x1c, o.add);
}

void pkp_ui43_post_bake(void *so) {
    if (!so) return;
    for (int i = g_bake_top - 1; i >= 0; i--) {
        if (g_bake_stack[i].so == so) {
            wr_f32(so, 0x10, g_bake_stack[i].sx);
            wr_f32(so, 0x14, g_bake_stack[i].sy);
            for (int j = i; j + 1 < g_bake_top; j++) g_bake_stack[j] = g_bake_stack[j + 1];
            g_bake_top--;
            break;
        }
    }
    wr_f32(so, 0x1c, 0.0f);
}

// The cursor sub-layout 1b16778d is shared: the Pause menu hosts it, and gmx_fix corrects its root there for the Pause layout's
// scale. The Things-to-Do popup hosts the same sub-layout in CL_0000_parts_cursor_triangle under Null_hint_pokemon, whose
// global scale is not 1 (0.57-0.66 measured), so the Pause correction (host - Pause root) * (1 - 1 / m00) moved its arrow off
// the selected Pokemon (about -94, +158 stored units). The sub-layout root has no link to its host, so it is told by
// position: its global translation equals the host's, which gmx_fix records when the host passes the join. A root at that
// position is the popup's and is left as the game placed it. Verified on the phone (Turnip): the arrow sits above the icon.
static int gmx_skip_popup_host(const void *pg) {
    if (!atomic_load_explicit(&g_popup_host_set, memory_order_acquire)) return 0;
    float hx, hy;
    unpack_f32_pair(atomic_load_explicit(&g_popup_host_t, memory_order_acquire), &hx, &hy);
    return fabsf(rd_f32(pg, 0x30) - hx) < 2.0f && fabsf(rd_f32(pg, 0x34) - hy) < 2.0f;
}

void pkp_ui43_gmx_fix(uint64_t *r) {
    uint32_t w20 = (uint32_t)r[20];
    if (!w20) return;
    void *p = (void *)(uintptr_t)r[19];
    if (!p) return;
    const void *par = rd_ptr(p, 0xd0);
    if (par && NM(p, "CL_0000_parts_cursor_triangle") && NM(par, "Null_hint_pokemon")) {
        const void *hg = rd_ptr(p, 0xe0);
        if (hg) {
            atomic_store_explicit(&g_popup_host_t, pack_f32_pair(rd_f32(hg, 0x30), rd_f32(hg, 0x34)), memory_order_release);
            atomic_store_explicit(&g_popup_host_set, 1, memory_order_release);
        }
    }
    if (!par || !has_cursor_root((uintptr_t)par)) return;
    const void *pg = rd_ptr(par, 0xe0);
    if (!pg || gmx_skip_popup_host(pg)) return;
    float m00 = rd_f32(pg, 0x00), m11 = rd_f32(pg, 0x14);
    if (m00 == 1.0f || m00 == 0.0f || m11 == 0.0f) return;
    const void *rw0 = (const void *)atomic_load_explicit(&g_pause_root, memory_order_acquire);
    if (!rw0) return;
    const void *rw0g = rd_ptr(rw0, 0xe0);
    void *g = rd_ptr_mut(p, 0xe0);
    if (!rw0g || !g) return;
    float cx = (rd_f32(pg, 0x30) - rd_f32(rw0g, 0x30)) * (1.0f - 1.0f / m00);
    float cy = (rd_f32(pg, 0x34) - rd_f32(rw0g, 0x34)) * (1.0f - 1.0f / m11);
    float dx = cx, dy = cy;
    if (w20 == 1) {
        atomic_store_explicit(&g_c0_pair, pack_f32_pair(cx, cy), memory_order_release);
    } else {
        uint64_t expected = atomic_load_explicit(&g_c0_pair, memory_order_acquire);
        uint64_t next;
        do {
            float c0x, c0y;
            unpack_f32_pair(expected, &c0x, &c0y);
            dx = cx - c0x;
            dy = cy - c0y;
            next = pack_f32_pair(c0x + dx, c0y + dy);
        } while (!atomic_compare_exchange_weak_explicit(
            &g_c0_pair, &expected, next, memory_order_acq_rel, memory_order_acquire));
    }
    wr_f32(g, 0x30, rd_f32(g, 0x30) - dx);
    wr_f32(g, 0x34, rd_f32(g, 0x34) - dy);
}
