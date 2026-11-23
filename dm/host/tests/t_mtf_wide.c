// Mario Tennis Fever camera and 2D layer callback (android/mtf_wide.c): the build gate is on nro0 (main is a boot stub); a one-view layout's 16:9 aspect becomes the picture's, two or
// more views and other aspects keep theirs; a narrower picture's camera 0 gets the Vert+ fovy in the register only (other cameras, a wider picture and the camera's memory untouched);
// the layout projection is scaled into the middle 16:9 once, a full-canvas pane reads the unscaled one through a stand-in, other projections are left; DM_MTF_HUD=0 leaves the 2D
// layer stretched; 16:9, no shape or another build change nothing. Every case runs in its own process (the shape, the build and the switch are read once).
#include "../android/mtf_wide.c"
#include <assert.h>
#include <sys/wait.h>
#include <unistd.h>

static module_t test_modules[2];
module_t *g_mod = test_modules;
int g_nmod;
static void (*callbacks[OBS_MAX])(uint64_t *, int);
void gate_obs_set(int id, void (*fn)(uint64_t *, int)) { assert(id > 0 && id < OBS_MAX); callbacks[id] = fn; }

static void setup(const char *nro_build, const char *shape) {
    g_nmod = 2;
    strcpy(g_mod[0].name, "main"); strcpy(g_mod[0].build_id, "104bce6874603701935eb76cb7d8b59e");   // the boot stub: its build says nothing about nro0
    strcpy(g_mod[1].name, "nro0"); g_mod[1].nro = 1; strcpy(g_mod[1].build_id, nro_build);
    if (shape) setenv("DM_VK_PICTURE_ASPECT", shape, 1); else unsetenv("DM_VK_PICTURE_ASPECT");
}

static void gate(uint64_t *r, int kind, int reg) { callbacks[OBS_MTF_WIDE](r, kind << 5 | reg); }

static _Alignas(16) unsigned char cams[2 * 0x330];   // the camera array: camera 0, camera 1

// One aspect store: the layout's view count, view 0's aspect in s0; s0 after the gate
static float store(int views, float in) {
    _Alignas(16) unsigned char lay[0x40];
    memset(lay, 0, sizeof lay);
    memcpy(lay + L_VIEWS, &views, 4);
    uint64_t r[100];
    memset(r, 0, sizeof r);
    r[19] = (uintptr_t)lay; r[20] = (uintptr_t)cams;
    *(float *)&r[32] = in;
    gate(r, 0, 0);
    float out = *(float *)&r[32];
    ws_wrf((uintptr_t)cams + C_ASPECT, out);   // the store itself
    return out;
}

// A projection builder's fovy load: camera c (0 or 1) with fovy f in s<reg>; the register after the gate
static float fovy(int c, int reg, float f) {
    uint64_t r[100];
    memset(r, 0, sizeof r);
    r[19] = (uintptr_t)cams + c * 0x330;
    *(float *)&r[32 + 2 * reg] = f;
    gate(r, 1, reg);
    return *(float *)&r[32 + 2 * reg];
}

static const float FULL = 2048.0f / 1152, SMALL = 960.0f / 540, HALF = 1024.0f / 1152, OTHER = 4.0f / 3, F = 0.6f;

static void wide_case(void) {
    setup(MTF_NRO_BUILD, "21:9");
    double A = 21.0 / 9;
    assert(fabs(store(1, SMALL) - A) < 1e-5);   // at Phone 540p's graphics size
    assert(fabs(store(1, FULL) - A) < 1e-5);    // the single view at the game's start: Hor+
    assert(fovy(0, 1, F) == F && fovy(0, 0, F) == F);   // the vertical field stays
    assert(store(2, FULL) == FULL);             // doubles / split: their views are 16:9 boxes
    assert(store(4, FULL) == FULL);
    assert(store(2, HALF) == HALF);
    assert(store(1, OTHER) == OTHER);           // a layout of another shape
    assert(store(0, FULL) == FULL);
    uint64_t r[100] = {0}; *(float *)&r[32] = FULL;   // no layout: nothing
    gate(r, 0, 0); assert(*(float *)&r[32] == FULL);
    r[19] = 2; gate(r, 0, 0); assert(*(float *)&r[32] == FULL);   // unaligned: nothing
    callbacks[OBS_MTF_WIDE](r, -1); assert(*(float *)&r[32] == FULL);
}

static void screen_wide(void) { setup(MTF_NRO_BUILD, "20:9"); assert(fabs(store(1, FULL) - 20.0 / 9) < 1e-5); }   // Screen shape on a 20:9 phone

static void narrow_case(void) {
    setup(MTF_NRO_BUILD, "4:3");
    double A = 4.0 / 3;
    assert(fovy(0, 0, F) == F);                 // before any layout apply: nothing converted
    assert(fabs(store(1, FULL) - A) < 1e-5);
    ws_wrf((uintptr_t)cams + 0x330 + C_ASPECT, (float)A);   // camera 1 with the same aspect: not the converted camera
    for (int reg = 0; reg <= 1; reg++) {
        float out = fovy(0, reg, F);
        assert(fabs(tan(out / 2) * A - tan(F / 2) * K169) < 1e-5);   // the horizontal reach of a 16:9 picture stays
        assert(fovy(0, reg, F) == out);         // each load converts the game's value again, never a converted one: same result
        assert(fovy(1, reg, F) == F);
    }
    assert(ws_rdf((uintptr_t)cams + 0x4c) == 0);   // the camera's memory is not written
    assert(fovy(0, 0, 3.1f) == 3.1f && fovy(0, 0, 0.0f) == 0.0f);   // outside the game's clamp: left
    float wide = fovy(0, 0, 2.9f);
    assert(wide > 2.9f && wide <= 3.0f);        // held under 172 degrees
    ws_wrf((uintptr_t)cams + C_ASPECT, FULL);   // the game wrote 16:9 again (a layout of two views): camera 0 is not converted
    assert(fovy(0, 0, F) == F);
}

static void one_one(void) {
    setup(MTF_NRO_BUILD, "1:1");
    assert(fabs(store(1, FULL) - 1.0) < 1e-5);
    float out = fovy(0, 0, F);
    assert(fabs(tan(out / 2) - tan(F / 2) * K169) < 1e-5);
}

// The layout setup's projection (ortho 1920x1080, or the perspective of a layout with a field of view) and a pane's draw
static const float ORTHO[16] = {2.0f / 1920, 0, 0, 0, 0, -2.0f / 1080, 0, 0, 0, 0, -0.004f, -1, 0, 0, 0, 1};
static const float PERSP[16] = {1.358f, 0, 0, 0, 0, 2.414f, 0, 0, 0, 0, -1.00002f, -2.00002f, 0, 0, -1, 0};

static void ui_check(double A, int on) {
    for (int p = 0; p < 2; p++) {
        const float *proj = p ? PERSP : ORTHO;
        _Alignas(16) unsigned char di[0x200], stack[0x40];
        memset(di, 0, sizeof di);
        memcpy(stack, proj, 64);
        uint64_t r[100] = {0};
        r[0] = (uintptr_t)di; r[1] = (uintptr_t)stack;
        gate(r, 2, 0);
        float m[16]; memcpy(m, stack, 64);
        int row = A > K169 ? 0 : 1;
        float q = (float)(A > K169 ? K169 / A : A / K169);
        for (int k = 0; k < 16; k++) {
            float want = on && k / 4 == row ? proj[k] * q : proj[k];
            assert(fabsf(m[k] - want) < 1e-7f);
        }
        memcpy(di + DI_MTX, m, 64);   // the copy into the draw info (nro0+0x665fc)
        // pane draws: a small pane and a full-canvas pane, through the draw setup (pane matrix x23, size x22) and the text setup (pane x21)
        _Alignas(16) unsigned char pane[0x200];
        memset(pane, 0, sizeof pane);
        float *g = (float *)(pane + 0x70), *sz = (float *)(pane + 0x50);
        g[0] = g[5] = 1;
        for (int text = 0; text < 2; text++) for (int full = 0; full < 2; full++) {
            sz[0] = full ? 1920 : 300; sz[1] = full ? 1080 : 200;
            memset(r, 0, sizeof r);
            r[0] = (uintptr_t)di;
            if (text) r[21] = (uintptr_t)pane; else { r[23] = (uintptr_t)(pane + 0x70); r[22] = (uintptr_t)(pane + 0x50); }
            gate(r, text ? 4 : 3, 0);
            if (!(on && full)) { assert(r[0] == (uintptr_t)di); continue; }
            assert(r[0] != (uintptr_t)di);
            const float *s = (const float *)(uintptr_t)(r[0] + DI_MTX);
            for (int k = 0; k < 16; k++) assert(fabsf(s[k] - proj[k]) < 1e-6f * (fabsf(proj[k]) + 1));
            assert(!memcmp(di + DI_MTX, m, 64));   // the draw info keeps the scaled one
        }
        // another projection in the draw info (a capture's own ortho, nro0+0xaf6440): a full-canvas pane is left alone
        float cap[16] = {2.0f / 1920, 0, 0, -1, 0, -2.0f / 1080, 0, 1, 0, 0, -0.002f, 0, 0, 0, 0, 1};
        memcpy(di + DI_MTX, cap, 64);
        sz[0] = 1920; sz[1] = 1080;
        memset(r, 0, sizeof r); r[0] = (uintptr_t)di; r[21] = (uintptr_t)pane;
        gate(r, 4, 0); assert(r[0] == (uintptr_t)di);
    }
    // a projection of another shape at the setup: left
    float sq[16]; memcpy(sq, ORTHO, 64); sq[5] = -2.0f / 1920;
    _Alignas(16) unsigned char di[0x80]; memset(di, 0, sizeof di);
    uint64_t r[100] = {0}; r[0] = (uintptr_t)di; r[1] = (uintptr_t)sq;
    gate(r, 2, 0); assert(sq[0] == ORTHO[0] && sq[5] == -2.0f / 1920);
}

static void ui_wide(void) { setup(MTF_NRO_BUILD, "21:9"); ui_check(21.0 / 9, 1); }
static void ui_narrow(void) { setup(MTF_NRO_BUILD, "4:3"); ui_check(4.0 / 3, 1); }
static void ui_off(void) { setup(MTF_NRO_BUILD, "21:9"); setenv("DM_MTF_HUD", "0", 1); ui_check(21.0 / 9, 0); }
static void ui_169(void) { setup(MTF_NRO_BUILD, "16:9"); ui_check(21.0 / 9, 0); }
static void same(void) { setup(MTF_NRO_BUILD, "16:9"); assert(store(1, FULL) == FULL); }
static void unset(void) { setup(MTF_NRO_BUILD, NULL); assert(store(1, FULL) == FULL); }
static void other_build(void) { setup("00000000000000000000000000000000", "4:3"); assert(store(1, FULL) == FULL); assert(fovy(0, 0, F) == F); ui_check(4.0 / 3, 0); }
static void main_not_nro(void) {   // a main of nro0's build ID is not nro0: the gate keys on the NRO
    setup("00000000000000000000000000000000", "21:9");
    strcpy(g_mod[0].build_id, MTF_NRO_BUILD);
    assert(store(1, FULL) == FULL);
}

static void in_child(void (*fn)(void), const char *what) {
    fflush(stdout);
    pid_t p = fork();
    if (!p) { fn(); _exit(0); }
    int st = 0; waitpid(p, &st, 0);
    if (!(p > 0 && WIFEXITED(st) && WEXITSTATUS(st) == 0)) { printf("FAIL t_mtf_wide: %s\n", what); exit(1); }
}

int main(void) {
    assert(callbacks[OBS_MTF_WIDE]);
    in_child(wide_case, "21:9: one 16:9 view widened, fovy kept, multi-view and other aspects kept");
    in_child(screen_wide, "20:9 Screen shape widened");
    in_child(narrow_case, "4:3: camera 0 Vert+ in the register, camera 1 and memory untouched");
    in_child(one_one, "1:1: Vert+");
    in_child(ui_wide, "21:9: layout x row scaled, full-canvas panes whole");
    in_child(ui_narrow, "4:3: layout y row scaled, full-canvas panes whole");
    in_child(ui_off, "DM_MTF_HUD=0: 2D layer stretched");
    in_child(ui_169, "16:9: 2D layer untouched");
    in_child(same, "16:9: nothing");
    in_child(unset, "no shape: nothing");
    in_child(other_build, "another nro0 build: nothing");
    in_child(main_not_nro, "the build ID on main only: nothing");
    printf("t_mtf_wide: OK\n");
    return 0;
}
