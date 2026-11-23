// Camera callback regression checks: opt-in/build gates, horizontal reach,
// copied render cameras, orthographic exclusion, repeated projection builds,
// Screen shape (PR #412) UI squeeze/text/pane rules, and DM_PATCH_VARIANT=43
// B-1/H-1/H-2/T95 dispatch matrix.
#include "../android/pkp_aspect.c"
#include "../android/pkp_ui43.c"
#include <assert.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>

static module_t test_modules[1];
module_t *g_mod = test_modules;
int g_nmod;
static void (*callbacks[OBS_MAX])(uint64_t *, int);

void gate_obs_set(int id, void (*fn)(uint64_t *, int)) {
    assert(id > 0 && id < OBS_MAX);
    callbacks[id] = fn;
}

static void submit_param(void *camera, int param) {
    uint64_t r[31] = {0};
    r[20] = (uintptr_t)camera;
    callbacks[OBS_PKP_CAM_SUBMIT](r, param);
}
static void build_param(void *camera, int param) {
    uint64_t r[31] = {0};
    r[0] = (uintptr_t)camera;
    callbacks[OBS_PKP_PROJ_BUILD](r, param);
}
static void done_param(void *camera, int param, uint64_t fp) {
    uint64_t r[31] = {0};
    r[19] = (uintptr_t)camera;
    r[29] = fp;
    callbacks[OBS_PKP_PROJ_DONE](r, param);
}
static void submit(void *camera) { submit_param(camera, 0); }
static void build(void *camera) { build_param(camera, 0); }
static void done(void *camera) { done_param(camera, 0, 0); }
static void init_mask_entry(unsigned char entry[0x70], uint64_t tex, uint32_t blend) {
    memset(entry, 0, 0x70);
    memcpy(entry, &tex, sizeof tex);
    memcpy(entry + 0x68, &blend, sizeof blend);
}
static void projection(void *camera) {
    uint64_t a = (uintptr_t)camera;
    float p11 = 1.0f / tanf(rdf(a + CAM_FOV) * 0.5f);
    wrf(a + CAM_PROJ + 20, p11);
    wrf(a + CAM_PROJ, p11 / (float)K169);
}

static void check(int which) {
    static const char *invalid[] = {NULL, "0", "1.109756oops", "nan", "inf", "-1", "1.777778", "1e999"};
    _Alignas(16) unsigned char camera[384] = {0}, copy[384], before[384];
    uint64_t a = (uintptr_t)camera;
    unsetenv("DM_PATCH_VARIANT");
    unsetenv("DM_VK_PICTURE_ASPECT");
    g_nmod = 1;
    strcpy(g_mod[0].name, "main");
    strcpy(g_mod[0].build_id, "76a489f3bd3642fa5e18bd83d32c98ba");
    if (which < 8) {
        if (invalid[which]) setenv("DM_PKP_ASPECT", invalid[which], 1);
        else unsetenv("DM_PKP_ASPECT");
    } else setenv("DM_PKP_ASPECT", "1.109756", 1);
    if (which == 8) g_mod[0].build_id[0] = '0';
    float original_fov = (float)(45.0 / 57.29577951308232);
    wrf(a + CAM_FOV, original_fov);
    wrf(a + CAM_ASPECT, (float)K169);
    if (which == 9) {
        uint32_t orthographic = 1;
        memcpy(camera + CAM_FLAGS, &orthographic, 4);
    }
    projection(camera);
    memcpy(before, camera, sizeof camera);
    submit(camera);
    build(camera);
    done(camera);
    if (which < 10) {
        assert(!memcmp(before, camera, sizeof camera));
        return;
    }

    float corrected = rdf(a + CAM_FOV);
    double expected = 2 * atan(tan(original_fov * 0.5) * K169 / 1.109756);
    assert(fabs(corrected - expected) < 1e-6);
    assert(rdf(a + CAM_ASPECT) == (float)K169);
    projection(camera);
    done(camera);
    float expected_p00 = (float)(1.0 / tan(original_fov * 0.5) / K169);
    assert(fabsf(rdf(a + CAM_PROJ) - expected_p00) < 1e-5f);

    // The game can copy the camera without submitting the copy again.
    memcpy(copy, camera, sizeof copy);
    projection(copy);
    done(copy);
    assert(fabsf(rdf((uintptr_t)copy + CAM_PROJ) - expected_p00) < 1e-5f);

    for (int i = 0; i < 1024; i++) {
        // A live environment edit cannot discard provenance and apply FOV twice.
        if (which == 11 && i == 100) setenv("DM_PKP_ASPECT", "0", 1);
        if (which == 11 && i == 200) setenv("DM_PKP_ASPECT", "1.109756", 1);
        build(camera);
        projection(camera);
        done(camera);
        assert(rdf(a + CAM_FOV) == corrected);
        assert(fabsf(rdf(a + CAM_PROJ) - expected_p00) < 1e-5f);
    }
    // A changed game-owned FOV (zoom/cutscene) is converted once again.
    wrf(a + CAM_FOV, original_fov * 0.8f);
    build(camera);
    assert(fabs(rdf(a + CAM_FOV) - 2 * atan(tan(original_fov * 0.8f * 0.5) * K169 / 1.109756)) < 1e-6);
    if (which == 13) {
        // A copy retains the old corrected FOV after its original zooms. It
        // needs the P00 fix and must not be corrected again if submitted later.
        projection(copy);
        done(copy);
        assert(fabsf(rdf((uintptr_t)copy + CAM_PROJ) - expected_p00) < 1e-5f);
        submit(copy);
        build(copy);
        projection(copy);
        done(copy);
        assert(rdf((uintptr_t)copy + CAM_FOV) == corrected);
        assert(fabsf(rdf((uintptr_t)copy + CAM_PROJ) - expected_p00) < 1e-5f);
    }
    if (which == 12) {
        // An unchanged camera must survive another camera churning the recent
        // FOV history; its game-owned render copy must still be recognized.
        float keep_fov = rdf(a + CAM_FOV);
        float keep_p00 = (float)(1.0 / tan(original_fov * 0.8f * 0.5) / K169);
        memcpy(copy, camera, sizeof copy);
        _Alignas(16) unsigned char other[384] = {0};
        uint64_t b = (uintptr_t)other;
        wrf(b + CAM_ASPECT, (float)K169);
        submit(other);
        for (int i = 0; i < 40; i++) {
            wrf(b + CAM_FOV, 0.2f + i * 0.02f);
            build(other);
            projection(other);
            done(other);
        }
        build(camera);
        projection(camera);
        done(camera);
        assert(rdf(a + CAM_FOV) == keep_fov);
        assert(fabsf(rdf(a + CAM_PROJ) - keep_p00) < 1e-5f);
        projection(copy);
        done(copy);
        assert(fabsf(rdf((uintptr_t)copy + CAM_PROJ) - keep_p00) < 1e-5f);
    }

}

static uint8_t *alloc_main_image(uint32_t fitw_word) {
    uint8_t *img = calloc(1, 0x913200);
    assert(img != NULL);
    memcpy(img + 0x9131a8, &fitw_word, 4);
    g_mod[0].base = img;
    g_mod[0].text_end = 0x2749480;
    return img;
}

static void check_variant(int which) {
    _Alignas(16) unsigned char camera[384] = {0}, before[384];
    _Alignas(16) unsigned char so[0x40] = {0}, root[0x160] = {0}, pane[0x160] = {0}, tr[0x40] = {0};
    uint64_t a = (uintptr_t)camera;
    float s = 1.0f, sy = 0.75f, one = 1.0f;
    memcpy(so + 0x10, &s, 4);
    memcpy(so + 0x14, &sy, 4);
    memcpy(so + 0x18, &one, 4);

    const char *rname = "Root", *pname = "Child";
    uint16_t rw = 1920, rh = 1080, pw = 200, ph = 100, rlen = 4, plen = 5;
    uintptr_t p_rname = (uintptr_t)rname, p_pname = (uintptr_t)pname;
    uintptr_t p_root = (uintptr_t)root, p_tr = (uintptr_t)tr;
    memcpy(root + 0xb0, &p_rname, sizeof p_rname);
    memcpy(root + 0xf0, &rw, 2);
    memcpy(root + 0xf2, &rh, 2);
    memcpy(root + 0x110, &rlen, 2);
    memcpy(pane + 0xb0, &p_pname, sizeof p_pname);
    memcpy(pane + 0xd0, &p_root, sizeof p_root);
    memcpy(pane + 0xe8, &p_tr, sizeof p_tr);
    memcpy(pane + 0xf0, &pw, 2);
    memcpy(pane + 0xf2, &ph, 2);
    pane[0x10c] = 0x11;
    memcpy(pane + 0x110, &plen, 2);
    float ty = 400.0f;
    memcpy(tr + 0x34, &ty, 4);

    g_nmod = 1;
    strcpy(g_mod[0].name, "main");
    strcpy(g_mod[0].build_id, "76a489f3bd3642fa5e18bd83d32c98ba");

    if (which == 14) {
        // B-1 row: DM_PATCH_VARIANT=43 active with real fitw cut -> W1 at 4:3, param 1/2 no-ops, param 4/5 bake.
        uint8_t *img = alloc_main_image(0x1478d8b6u);
        setenv("DM_PATCH_VARIANT", "43", 1);
        setenv("DM_PKP_ASPECT", "1.109756", 1);
        float original_fov = (float)(45.0 / 57.29577951308232);
        wrf(a + CAM_FOV, original_fov);
        wrf(a + CAM_ASPECT, (float)K169);
        projection(camera);
        submit(camera);
        build(camera);
        projection(camera);
        done(camera);
        double expected = 2.0 * atan(tan(original_fov * 0.5) * K169 / (4.0 / 3.0));
        assert(fabs(rdf(a + CAM_FOV) - expected) < 1e-6);
        float expected_p00 = (float)(1.0 / tan(original_fov * 0.5) / K169);
        assert(fabsf(rdf(a + CAM_PROJ) - expected_p00) < 1e-5f);

        // Param 1 and 2 must be no-ops under variant 43; non-scene UI camera on param 0 stays untouched.
        _Alignas(16) unsigned char ui_cam[384] = {0};
        wrf((uintptr_t)ui_cam + CAM_FOV, original_fov);
        wrf((uintptr_t)ui_cam + CAM_ASPECT, (float)K169);
        projection(ui_cam);
        memcpy(before, ui_cam, sizeof ui_cam);
        done_param(ui_cam, 0, 0);
        assert(!memcmp(before, ui_cam, sizeof ui_cam));
        wrf((uintptr_t)ui_cam + CAM_PROJ, 1.0f / 960.0f);
        uint32_t ortho = 1;
        memcpy(ui_cam + CAM_FLAGS, &ortho, 4);
        memcpy(before, ui_cam, sizeof ui_cam);
        done_param(ui_cam, 1, 0);
        assert(!memcmp(before, ui_cam, sizeof ui_cam));

        _Alignas(16) unsigned char prog[0x60] = {0}, mat[0x20] = {0};
        uint64_t p_prog = (uintptr_t)prog;
        uint32_t prog_id = 0x1au << 8, tag = 0x474f5250u;
        memcpy(mat + 0x10, &p_prog, 8);
        memcpy(prog + 0x10, &prog_id, 4);
        memcpy(prog + 0x48, &tag, 4);
        float batch[4] = {2.0f / 1920.0f, -2.0f / 1080.0f, -1.0f, 1.0f};
        uint64_t tr_r[31] = {0};
        tr_r[1] = (uintptr_t)mat;
        tr_r[8] = (uintptr_t)batch;
        callbacks[OBS_PKP_PROJ_DONE](tr_r, 2);
        assert(fabsf(batch[1] - (-2.0f / 1080.0f)) < 1e-7f && batch[3] == 1.0f);

        // Param 4/5 pre/post bake must run under variant 43.
        uint64_t r[31] = {0};
        r[0] = (uintptr_t)so;
        r[1] = (uintptr_t)pane;
        callbacks[OBS_PKP_PROJ_DONE](r, 4);
        assert(fabsf(rdf((uintptr_t)so + 0x1c) - 135.0f) < 1e-4f);
        r[19] = (uintptr_t)so;
        callbacks[OBS_PKP_PROJ_DONE](r, 5);
        assert(fabsf(rdf((uintptr_t)so + 0x1c)) < 1e-6f);

        // Param 6 widens event stencil mask rect around its center under variant 43.
        float mask_rect[4] = {651.681f, 445.084f, 1251.681f, 1045.084f};
        uint64_t mr[31] = {0};
        mr[1] = (uintptr_t)mask_rect;
        callbacks[OBS_PKP_PROJ_DONE](mr, 6);
        assert(fabsf(mask_rect[0] - 551.681f) < 1e-3f);
        assert(fabsf(mask_rect[2] - 1351.681f) < 1e-3f);
        assert(mask_rect[1] == 445.084f && mask_rect[3] == 1045.084f);

        // Param 7 widens qualifying alpha-mask rect (non-null tex + 0x918000u blend) and leaves full-screen fade untouched.
        _Alignas(16) unsigned char entry[0x70];
        init_mask_entry(entry, 1, 0x918000u);
        float alpha_rect[4] = {651.681f, 445.084f, 1251.681f, 1045.084f};
        uint64_t ar[31] = {0};
        ar[1] = (uintptr_t)alpha_rect;
        ar[19] = (uintptr_t)entry;
        callbacks[OBS_PKP_PROJ_DONE](ar, 7);
        assert(fabsf(alpha_rect[0] - 551.681f) < 1e-3f);
        assert(fabsf(alpha_rect[2] - 1351.681f) < 1e-3f);
        assert(alpha_rect[1] == 445.084f && alpha_rect[3] == 1045.084f);

        init_mask_entry(entry, 0, 0x90800u);
        float fade_rect[4] = {0.0f, 0.0f, 1920.0f, 1080.0f};
        ar[1] = (uintptr_t)fade_rect;
        callbacks[OBS_PKP_PROJ_DONE](ar, 7);
        assert(fade_rect[0] == 0.0f && fade_rect[1] == 0.0f &&
               fade_rect[2] == 1920.0f && fade_rect[3] == 1080.0f);
        free(img);
    } else if (which == 15) {
        // B-1 row: non-43 DM_PATCH_VARIANT disables DM_PKP_ASPECT, Screen shape, and 30|3..5.
        uint8_t *img = alloc_main_image(0x1478d8b6u);
        setenv("DM_PATCH_VARIANT", "other", 1);
        setenv("DM_PKP_ASPECT", "1.109756", 1);
        wrf(a + CAM_FOV, 0.8f);
        wrf(a + CAM_ASPECT, (float)K169);
        projection(camera);
        memcpy(before, camera, sizeof camera);
        submit(camera);
        build(camera);
        done(camera);
        assert(!memcmp(before, camera, sizeof camera));
        uint64_t r[31] = {0};
        r[0] = (uintptr_t)so;
        r[1] = (uintptr_t)pane;
        callbacks[OBS_PKP_PROJ_DONE](r, 4);
        assert(fabsf(rdf((uintptr_t)so + 0x1c)) < 1e-6f);
        float mask_rect[4] = {651.681f, 445.084f, 1251.681f, 1045.084f};
        uint64_t mr[31] = {0};
        mr[1] = (uintptr_t)mask_rect;
        callbacks[OBS_PKP_PROJ_DONE](mr, 6);
        assert(mask_rect[0] == 651.681f && mask_rect[1] == 445.084f &&
               mask_rect[2] == 1251.681f && mask_rect[3] == 1045.084f);
        _Alignas(16) unsigned char entry[0x70];
        init_mask_entry(entry, 1, 0x918000u);
        mr[19] = (uintptr_t)entry;
        callbacks[OBS_PKP_PROJ_DONE](mr, 7);
        assert(mask_rect[0] == 651.681f && mask_rect[1] == 445.084f &&
               mask_rect[2] == 1251.681f && mask_rect[3] == 1045.084f);
        free(img);
    } else if (which == 16) {
        // B-1 row: unset DM_PATCH_VARIANT runs DM_PKP_ASPECT on 28/29/30|0, leaves 30|4..5 no-ops.
        unsetenv("DM_PATCH_VARIANT");
        setenv("DM_PKP_ASPECT", "1.109756", 1);
        uint64_t r[31] = {0};
        r[0] = (uintptr_t)so;
        r[1] = (uintptr_t)pane;
        callbacks[OBS_PKP_PROJ_DONE](r, 4);
        assert(fabsf(rdf((uintptr_t)so + 0x1c)) < 1e-6f);
        // Also verify T95 does NOT trigger without variant 43.
        uint8_t *img = alloc_main_image(0x6e0c0400u);
        uint64_t caller[2] = {0, (uint64_t)(uintptr_t)img + 0x22bba04u};
        uint64_t cur[2] = {(uintptr_t)caller, 0};
        uint32_t fov_t95 = 0x3dfa35ddu;
        memcpy(camera + CAM_FOV, &fov_t95, 4);
        wrf(a + CAM_ASPECT, 1.0f);
        projection(camera);
        memcpy(before, camera, sizeof camera);
        done_param(camera, 0, (uintptr_t)cur);
        assert(!memcmp(before, camera, sizeof camera));
        free(img);
    } else if (which == 17) {
        // H-1: DM_PATCH_VARIANT=43 with stock main (0x6e0c0400 at +0x9131a8) falls back cleanly.
        uint8_t *img = alloc_main_image(0x6e0c0400u);
        setenv("DM_PATCH_VARIANT", "43", 1);
        setenv("DM_PKP_ASPECT", "1.109756", 1);
        wrf(a + CAM_FOV, 0.8f);
        wrf(a + CAM_ASPECT, (float)K169);
        projection(camera);
        memcpy(before, camera, sizeof camera);
        submit(camera);
        build(camera);
        done(camera);
        assert(!memcmp(before, camera, sizeof camera));
        uint64_t r[31] = {0};
        r[0] = (uintptr_t)so;
        r[1] = (uintptr_t)pane;
        callbacks[OBS_PKP_PROJ_DONE](r, 4);
        assert(fabsf(rdf((uintptr_t)so + 0x1c)) < 1e-6f);
        free(img);
    } else if (which == 18) {
        // H-2: T95 PAC-signed LR2 (dirty bits 39..63 on 39-bit VA Android), plus negative checks.
        uint8_t *img = alloc_main_image(0x1478d8b6u);
        setenv("DM_PATCH_VARIANT", "43", 1);
        uint64_t lr2_raw = (uint64_t)(uintptr_t)img + 0x22bba04u;
        uint64_t lr2_pac39 = (lr2_raw & 0x0000007fffffffffull) | (0x01ab7full << 39);
        uint64_t caller[2] = {0, lr2_pac39};
        uint64_t cur[2] = {(uintptr_t)caller, 0};
        uint32_t fov_t95 = 0x3dfa35ddu;
        memcpy(camera + CAM_FOV, &fov_t95, 4);
        wrf(a + CAM_ASPECT, 1.0f);
        projection(camera);
        float p0_orig = rdf(a + CAM_PROJ);
        done_param(camera, 0, (uintptr_t)cur);
        assert(fabsf(rdf(a + CAM_PROJ) - p0_orig / 0.75f) < 1e-4f);

        // Wrong caller LR2 -> untouched
        caller[1] = (lr2_raw + 4) | (0x01ab7full << 39);
        projection(camera);
        done_param(camera, 0, (uintptr_t)cur);
        assert(fabsf(rdf(a + CAM_PROJ) - p0_orig) < 1e-5f);

        // Wrong FOV -> untouched
        caller[1] = lr2_pac39;
        wrf(a + CAM_FOV, 0.5f);
        projection(camera);
        float p0_other = rdf(a + CAM_PROJ);
        done_param(camera, 0, (uintptr_t)cur);
        assert(fabsf(rdf(a + CAM_PROJ) - p0_other) < 1e-5f);

        // Unaligned/null fp -> no crash, untouched
        memcpy(camera + CAM_FOV, &fov_t95, 4);
        projection(camera);
        done_param(camera, 0, 0);
        done_param(camera, 0, (uintptr_t)cur + 3);
        assert(fabsf(rdf(a + CAM_PROJ) - p0_orig) < 1e-5f);
        free(img);
    }
}

static void check_screen_shape(int which) {
    _Alignas(16) unsigned char camera[384] = {0}, ui_cam[384] = {0}, ortho_cam[384] = {0};
    uint64_t a = (uintptr_t)camera, u = (uintptr_t)ui_cam, o = (uintptr_t)ortho_cam;
    unsetenv("DM_PATCH_VARIANT");
    unsetenv("DM_PKP_ASPECT");
    setenv("DM_VK_PICTURE_ASPECT", "4:3", 1);
    g_nmod = 1;
    strcpy(g_mod[0].name, "main");
    strcpy(g_mod[0].build_id, "76a489f3bd3642fa5e18bd83d32c98ba");

    if (which == 19) {
        // PR #412 Screen shape: DM_VK_PICTURE_ASPECT=4:3 fallback + UI perspective/ortho squeeze + DM_PKP_CROP.
        setenv("DM_PKP_CROP", "0.2:50", 1);
        float original_fov = (float)(45.0 / 57.29577951308232);
        wrf(a + CAM_FOV, original_fov);
        wrf(a + CAM_ASPECT, (float)K169);
        projection(camera);
        submit(camera);
        build(camera);
        projection(camera);
        done(camera);
        double expected = 2.0 * atan(tan(original_fov * 0.5) * K169 / (4.0 / 3.0));
        assert(fabs(rdf(a + CAM_FOV) - expected) < 1e-6);

        // Non-scene perspective UI camera (near=0.1, far=20000) gets P11 *= 0.75
        wrf(u + CAM_FOV, original_fov);
        wrf(u + CAM_ASPECT, (float)K169);
        wrf(u + 320, 0.1f);
        wrf(u + 324, 20000.0f);
        projection(ui_cam);
        float p11_ui = rdf(u + CAM_PROJ + 20), p00_ui = rdf(u + CAM_PROJ);
        done(ui_cam);
        assert(fabsf(rdf(u + CAM_PROJ + 20) - p11_ui * 0.75f) < 1e-5f);
        assert(fabsf(rdf(u + CAM_PROJ) - p00_ui) < 1e-5f);

        // Cropped camera family (near=0.2, far=50) gets P00 /= 0.75 instead of P11 *= 0.75
        wrf(u + 320, 0.2f);
        wrf(u + 324, 50.0f);
        projection(ui_cam);
        done(ui_cam);
        assert(fabsf(rdf(u + CAM_PROJ) - p00_ui / 0.75f) < 1e-5f);
        assert(fabsf(rdf(u + CAM_PROJ + 20) - p11_ui) < 1e-5f);

        // Orthographic UI camera (P00 = 2/1920) on param 1 gets P11 *= 0.75
        uint32_t ortho = 1;
        memcpy(ortho_cam + CAM_FLAGS, &ortho, 4);
        wrf(o + CAM_ASPECT, (float)K169);
        wrf(o + CAM_PROJ, 2.0f / 1920.0f);
        wrf(o + CAM_PROJ + 20, -2.0f / 1080.0f);
        done_param(ortho_cam, 1, 0);
        assert(fabsf(rdf(o + CAM_PROJ + 20) - (-2.0f / 1080.0f) * 0.75f) < 1e-6f);

        // Param 6 widens event stencil mask rect around its center by (16/9)/(4/3) = 4/3.
        float mask_rect[4] = {651.681f, 445.084f, 1251.681f, 1045.084f};
        uint64_t mr[31] = {0};
        mr[1] = (uintptr_t)mask_rect;
        callbacks[OBS_PKP_PROJ_DONE](mr, 6);
        assert(fabsf(mask_rect[0] - 551.681f) < 1e-3f);
        assert(fabsf(mask_rect[2] - 1351.681f) < 1e-3f);
        assert(mask_rect[1] == 445.084f && mask_rect[3] == 1045.084f);

        // Param 7 widens qualifying alpha-mask rect and leaves full-screen fade untouched.
        _Alignas(16) unsigned char entry[0x70];
        init_mask_entry(entry, 1, 0x918000u);
        float alpha_rect[4] = {651.681f, 445.084f, 1251.681f, 1045.084f};
        uint64_t ar[31] = {0};
        ar[1] = (uintptr_t)alpha_rect;
        ar[19] = (uintptr_t)entry;
        callbacks[OBS_PKP_PROJ_DONE](ar, 7);
        assert(fabsf(alpha_rect[0] - 551.681f) < 1e-3f);
        assert(fabsf(alpha_rect[2] - 1351.681f) < 1e-3f);
        assert(alpha_rect[1] == 445.084f && alpha_rect[3] == 1045.084f);

        init_mask_entry(entry, 0, 0x90800u);
        float fade_rect[4] = {0.0f, 0.0f, 1920.0f, 1080.0f};
        ar[1] = (uintptr_t)fade_rect;
        callbacks[OBS_PKP_PROJ_DONE](ar, 7);
        assert(fade_rect[0] == 0.0f && fade_rect[1] == 0.0f &&
               fade_rect[2] == 1920.0f && fade_rect[3] == 1080.0f);
    } else if (which == 20) {
        // PR #412 Screen shape: text_consts (param 2) + DM_PKP_UI=0 disables UI squeeze/text.
        _Alignas(16) unsigned char prog[0x60] = {0}, mat[0x20] = {0};
        uint64_t p_prog = (uintptr_t)prog;
        uint32_t tag = 0x474f5250u;
        memcpy(mat + 0x10, &p_prog, 8);
        memcpy(prog + 0x48, &tag, 4);

        uint32_t prog_text = 0x1au << 8;
        memcpy(prog + 0x10, &prog_text, 4);
        float batch[4] = {2.0f / 1920.0f, -2.0f / 1080.0f, -1.0f, 1.0f};
        uint64_t r[31] = {0};
        r[1] = (uintptr_t)mat;
        r[8] = (uintptr_t)batch;
        callbacks[OBS_PKP_PROJ_DONE](r, 2);
        assert(fabsf(batch[1] - (-2.0f / 1080.0f) * 0.75f) < 1e-6f);
        assert(fabsf(batch[3] - 0.75f) < 1e-6f);

        // Non-text 2D program (0x03) stays untouched
        uint32_t prog_other = 0x03u << 8;
        memcpy(prog + 0x10, &prog_other, 4);
        batch[1] = -2.0f / 1080.0f;
        batch[3] = 1.0f;
        callbacks[OBS_PKP_PROJ_DONE](r, 2);
        assert(fabsf(batch[1] - (-2.0f / 1080.0f)) < 1e-7f && batch[3] == 1.0f);
    } else if (which == 21) {
        // PR #412 Screen shape: DM_PKP_UI=0 leaves UI cameras and text untouched while world camera still runs.
        setenv("DM_PKP_UI", "0", 1);
        float original_fov = (float)(45.0 / 57.29577951308232);
        wrf(a + CAM_FOV, original_fov);
        wrf(a + CAM_ASPECT, (float)K169);
        projection(camera);
        submit(camera);
        build(camera);
        projection(camera);
        done(camera);
        double expected = 2.0 * atan(tan(original_fov * 0.5) * K169 / (4.0 / 3.0));
        assert(fabs(rdf(a + CAM_FOV) - expected) < 1e-6);

        wrf(u + CAM_FOV, original_fov);
        wrf(u + CAM_ASPECT, (float)K169);
        projection(ui_cam);
        float p11_ui = rdf(u + CAM_PROJ + 20);
        done(ui_cam);
        assert(fabsf(rdf(u + CAM_PROJ + 20) - p11_ui) < 1e-6f);

        float mask_rect[4] = {651.681f, 445.084f, 1251.681f, 1045.084f};
        uint64_t mr[31] = {0};
        mr[1] = (uintptr_t)mask_rect;
        callbacks[OBS_PKP_PROJ_DONE](mr, 6);
        assert(mask_rect[0] == 651.681f && mask_rect[1] == 445.084f &&
               mask_rect[2] == 1251.681f && mask_rect[3] == 1045.084f);
        _Alignas(16) unsigned char entry[0x70];
        init_mask_entry(entry, 1, 0x918000u);
        mr[19] = (uintptr_t)entry;
        callbacks[OBS_PKP_PROJ_DONE](mr, 7);
        assert(mask_rect[0] == 651.681f && mask_rect[1] == 445.084f &&
               mask_rect[2] == 1251.681f && mask_rect[3] == 1045.084f);
    } else if (which == 22) {
        // PR #412 Screen shape: pane_rules (param 3) cover + edge shift when guest 0x40.. address is available.
        void *mem = mmap((void *)0x4010000000ull, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (mem != MAP_FAILED && (((uintptr_t)mem) >> 32) == 0x40) {
            memset(mem, 0, 4096);
            uint8_t *base = (uint8_t *)mem;
            uint8_t *root = base + 0x000, *child = base + 0x200, *cov = base + 0x400;
            float *rg = (float *)(base + 0x600), *rl = (float *)(base + 0x640);
            float *cg = (float *)(base + 0x680), *cl = (float *)(base + 0x6c0);
            float *vg = (float *)(base + 0x700), *vl = (float *)(base + 0x740);
            rg[0] = 1.0f; rg[5] = 1.0f; rg[10] = 1.0f; rg[15] = 1.0f;
            rl[0] = 1.0f; rl[5] = 1.0f; rl[10] = 1.0f; rl[15] = 1.0f;
            cg[0] = 1.0f; cg[5] = 1.0f; cg[10] = 1.0f; cg[15] = 1.0f; cg[13] = -400.0f;
            cl[0] = 1.0f; cl[5] = 1.0f; cl[10] = 1.0f; cl[15] = 1.0f; cl[13] = -400.0f;
            vg[0] = 1.0f; vg[5] = 1.0f; vg[10] = 1.0f; vg[15] = 1.0f;
            vl[0] = 1.0f; vl[5] = 1.0f; vl[10] = 1.0f; vl[15] = 1.0f;

            uint64_t p_rg = (uintptr_t)rg, p_rl = (uintptr_t)rl, p_root = (uintptr_t)root;
            uint64_t p_cg = (uintptr_t)cg, p_cl = (uintptr_t)cl;
            uint64_t p_vg = (uintptr_t)vg, p_vl = (uintptr_t)vl;
            int16_t rsz[2] = {1920, 1080}, csz[2] = {200, 100}, vsz[2] = {1920, 1080};
            memcpy(root + 0xe0, &p_rg, 8); memcpy(root + 0xe8, &p_rl, 8); memcpy(root + 0xf0, rsz, 4);
            memcpy(child + 0xd0, &p_root, 8); memcpy(child + 0xe0, &p_cg, 8); memcpy(child + 0xe8, &p_cl, 8);
            memcpy(child + 0xf0, csz, 4);
            memcpy(cov + 0xd0, &p_root, 8); memcpy(cov + 0xe0, &p_vg, 8); memcpy(cov + 0xe8, &p_vl, 8);
            memcpy(cov + 0xf0, vsz, 4);

            uint64_t r[31] = {0};
            r[19] = (uintptr_t)child;
            r[20] = 1;
            callbacks[OBS_PKP_PROJ_DONE](r, 3);
            assert(fabsf(cg[13] - (-580.0f)) < 1e-3f);
            uint32_t cfl = 0;
            memcpy(&cfl, child + 0x104, 4);
            assert((cfl & MOVED) != 0);

            r[19] = (uintptr_t)cov;
            r[20] = 1;
            callbacks[OBS_PKP_PROJ_DONE](r, 3);
            assert(fabsf(vg[0] - (4.0f / 3.0f)) < 1e-4f);
            assert(fabsf(vg[5] - (4.0f / 3.0f)) < 1e-4f);
        }
        if (mem != MAP_FAILED) munmap(mem, 4096);
    }
}

int main(void) {
    for (int i = 0; i < 23; i++) {
        pid_t child = fork();
        assert(child >= 0);
        if (!child) {
            if (i < 14) check(i);
            else if (i < 19) check_variant(i);
            else check_screen_shape(i);
            _exit(0);
        }
        int status;
        assert(waitpid(child, &status, 0) == child);
        if (!WIFEXITED(status) || WEXITSTATUS(status)) {
            fprintf(stderr, "pkp aspect case %d failed\n", i);
            return 1;
        }
    }
    puts("pkp aspect: 23 opt-in, build, camera, Screen shape, variant 43 and T95 cases passed");
    return 0;
}
