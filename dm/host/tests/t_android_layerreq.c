// The run-time shader layer's request side with no prepared library (dm/gfx/vk_android/vka_layerreq.h, vka_shlib_empty; android/SHADERS.md "Shaders the library lacks"),
// on the Mac: the layer's folder (DM_VK_LAYER_DIR, $DM_TEMP/shader_layer, off), the empty library a pack without one plays (the host's header and translator answers, every
// key a miss), the run's key set, and the writer thread: a program's misses become req/<key>.code and .ctl and pairs.tsv lines, once per key, an earlier run's request is
// not written again, and a full queue refuses without losing the keys; a stage or pair it cannot write is handed back (unmarked), a removed folder is made again, a pair is
// appended once across runs; and the layer's mappings: a replaced one is dropped when its last lookup gives it back
#include "../../gfx/vk_android/vka_shlib.h"
#include "../../gfx/vk_android/vka_layerreq.h"
#include "../../gfx/nvn/dmsh_chain.h"
#include "../../gfx/nvn/dmsh_chain_vk.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <stdint.h>

static int g_fail;
#define CHECK(c, ...) do { if (!(c)) { g_fail++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

static void test_root(void) {
    char r[64];
    CHECK(vka_layer_root_of(r, sizeof r, "/pack/shader_layer", "/t", 1) && !strcmp(r, "/pack/shader_layer"), "DM_VK_LAYER_DIR wins: %s", r);
    CHECK(vka_layer_root_of(r, sizeof r, "/pack/layer//", NULL, 1) && !strcmp(r, "/pack/layer"), "trailing slashes: %s", r);
    CHECK(vka_layer_root_of(r, sizeof r, "", "/t", 1) && !strcmp(r, "/t/shader_layer"), "DM_TEMP: %s", r);
    CHECK(vka_layer_root_of(r, sizeof r, NULL, "/t", 1) && !strcmp(r, "/t/shader_layer"), "DM_TEMP: %s", r);
    CHECK(!vka_layer_root_of(r, sizeof r, "/pack", "/t", 0) && !r[0], "DM_VK_LAYER=0: no layer");
    CHECK(!vka_layer_root_of(r, sizeof r, NULL, NULL, 1) && !r[0], "neither folder: no layer");
    char longp[200]; memset(longp, 'a', sizeof longp - 1); longp[sizeof longp - 1] = 0;
    CHECK(!vka_layer_root_of(r, sizeof r, longp, NULL, 1) && !r[0], "a folder too long for the buffer: no layer");
}

static void test_empty(void) {
    vka_shlib L; dmsh_vk_header h; char err[256];
    CHECK(vka_shlib_empty(&L, &h, DMSH_CHAIN, DMSH_VK_CHAIN, "040074A01BF12000", DMSH_VK_ABI, DMSH_VK_SUBGROUP_SIZE, DMSH_VK_SSBO_ALIGN, err, sizeof err), "empty library: %s", err);
    CHECK(L.h == &h && L.h->entry_count == 0 && L.h->mod_count == 0 && L.by_abi == 0 && L.differs == 0 && !L.mapped, "empty library fields");
    CHECK(h.subgroup_size == DMSH_VK_SUBGROUP_SIZE && h.ssbo_align == DMSH_VK_SSBO_ALIGN, "translator answers %u %u", h.subgroup_size, h.ssbo_align);
    CHECK(!memcmp(h.abi, DMSH_VK_ABI, sizeof h.abi), "abi");
    char s[17]; vka_shlib_str(h.vk_chain, s); CHECK(!strcmp(s, DMSH_VK_CHAIN), "vk chain %s", s);
    vka_shlib_str(h.game, s); CHECK(!strcmp(s, "040074A01BF12000"), "game %s", s);
    CHECK(!vka_shlib_find(&L, 0x0011223344556677ull) && !vka_shlib_find(&L, 0) && !vka_shlib_find(&L, ~0ull), "every key is a miss");
    // The header passes the same checks a layer does (vka_layer_poll opens the layer with the host's chain, Vulkan chain, game and ABI)
    vka_shlib L2; CHECK(vka_shlib_check(&L2, &h, sizeof h, DMSH_CHAIN, DMSH_VK_CHAIN, "040074A01BF12000", DMSH_VK_ABI, err, sizeof err), "empty header rechecked: %s", err);
    vka_shlib_close(&L);   // (not mapped: only cleared)
    CHECK(!L.h, "closed");
    CHECK(!vka_shlib_empty(&L, &h, DMSH_CHAIN, DMSH_VK_CHAIN, "0123456789abcdef0", DMSH_VK_ABI, 64, 64, err, sizeof err), "a 17-character game refused");
    CHECK(!vka_shlib_empty(&L, &h, DMSH_CHAIN, DMSH_VK_CHAIN, "040074A01BF12000", "abc", 64, 64, err, sizeof err), "a short ABI refused");
    // Two empty headers of one host are byte for byte the same (vka_shader_lib_id hashes the header: the pipeline cache's stamp stays across such runs)
    dmsh_vk_header h2; vka_shlib L3;
    vka_shlib_empty(&L, &h, DMSH_CHAIN, DMSH_VK_CHAIN, "040074A01BF12000", DMSH_VK_ABI, 64, 64, err, sizeof err);
    vka_shlib_empty(&L3, &h2, DMSH_CHAIN, DMSH_VK_CHAIN, "040074A01BF12000", DMSH_VK_ABI, 64, 64, err, sizeof err);
    CHECK(!memcmp(&h, &h2, sizeof h), "empty headers differ");
}

static vka_keyset g_ks;   // (256 KB: not on the stack)
static void test_keyset(void) {
    memset(&g_ks, 0, sizeof g_ks);
    CHECK(vka_keyset_add(&g_ks, 5) == 1 && vka_keyset_add(&g_ks, 5) == 0 && vka_keyset_has(&g_ks, 5) && !vka_keyset_has(&g_ks, 6), "add / has");
    CHECK(vka_keyset_add(&g_ks, 0) == 0 && !vka_keyset_has(&g_ks, 0), "key 0 is never kept");
    for (uint64_t k = 100; g_ks.n < VKA_KEYSET_CAP; k++) vka_keyset_add(&g_ks, k * 0x10001ull);
    CHECK(vka_keyset_add(&g_ks, 0xfeedull) == -1 && !vka_keyset_has(&g_ks, 0xfeedull) && vka_keyset_has(&g_ks, 5), "full: refused, the old keys kept");
    // Deletion keeps every other key findable (backward shift over probe runs, the wrap at the table's end included)
    CHECK(vka_keyset_del(&g_ks, 5) == 1 && !vka_keyset_has(&g_ks, 5) && g_ks.n == VKA_KEYSET_CAP - 1, "deleted");
    CHECK(vka_keyset_del(&g_ks, 5) == 0 && vka_keyset_del(&g_ks, 0) == 0, "deleted twice / key 0");
    CHECK(vka_keyset_add(&g_ks, 0xfeedull) == 1, "room again after a deletion");
    unsigned missing = 0;
    for (uint64_t k = 100; k < 100 + VKA_KEYSET_CAP; k++) if (k % 3 == 0) vka_keyset_del(&g_ks, k * 0x10001ull);
    for (uint64_t k = 100; k < 100 + VKA_KEYSET_CAP - 1; k++) if ((k % 3 != 0) != vka_keyset_has(&g_ks, k * 0x10001ull)) missing++;
    CHECK(!missing && vka_keyset_has(&g_ks, 0xfeedull), "%u keys wrong after deleting a third", missing);
    // Colliding keys: many with one home slot (and the slots after it), one taken out of the middle of the run
    static vka_keyset c; memset(&c, 0, sizeof c); uint64_t col[40]; unsigned nc = 0; unsigned home = vka_keyset_slot(0x1234567ull);
    for (uint64_t k = 1; nc < 40 && k < 50000000ull; k++) { unsigned sl = vka_keyset_slot(k); if (sl == home || sl == ((home + 1) & (2 * VKA_KEYSET_CAP - 1))) { col[nc++] = k; vka_keyset_add(&c, k); } }
    CHECK(nc == 40, "colliding keys found: %u", nc);
    vka_keyset_del(&c, col[3]); vka_keyset_del(&c, col[20]);
    missing = 0; for (unsigned i = 0; i < nc; i++) if (vka_keyset_has(&c, col[i]) != (i != 3 && i != 20)) missing++;
    CHECK(!missing && c.n == nc - 2, "colliding keys after two deletions: %u wrong", missing);
}

// The layer's mappings (vka_ly_*): a layer replaced while a lookup holds it stays until that lookup gives it back; the current one never goes
static int g_dropped[8];
static void drop_cb(void *o) { g_dropped[(intptr_t)o]++; }
static void test_lifetime(void) {
    static vka_lylife l = VKA_LYLIFE_INIT(drop_cb);
    CHECK(!vka_ly_get(&l), "no layer yet");
    vka_ly_set(&l, (void *)1);
    vka_lyh *a = vka_ly_get(&l); CHECK(a && a->obj == (void *)1 && l.live == 1, "layer 1 held");
    vka_ly_set(&l, (void *)2);   // replaced while held
    CHECK(!g_dropped[1] && l.live == 2, "a held layer was dropped when replaced");
    vka_lyh *b = vka_ly_get(&l); CHECK(b && b->obj == (void *)2, "a lookup after the swap takes the new layer");
    vka_ly_put(&l, a); CHECK(g_dropped[1] == 1 && l.live == 1 && l.dropped == 1, "the replaced layer dropped when its last lookup gave it back");
    vka_ly_put(&l, b); CHECK(!g_dropped[2], "the current layer dropped");
    vka_ly_set(&l, (void *)3); CHECK(g_dropped[2] == 1 && l.live == 1, "a replaced layer no lookup holds is dropped at once");
    vka_ly_put(&l, NULL);
    vka_lyh *c = vka_ly_get(&l); vka_lyh *d = vka_ly_get(&l); vka_ly_set(&l, (void *)4); vka_ly_put(&l, c);
    CHECK(!g_dropped[3], "dropped with a lookup still holding it"); vka_ly_put(&l, d); CHECK(g_dropped[3] == 1 && !g_dropped[4], "two lookups");
}

static long fsize(const char *p) { FILE *f = fopen(p, "rb"); if (!f) return -1; fseek(f, 0, SEEK_END); long n = ftell(f); fclose(f); return n; }
static char *slurp(const char *p) {
    FILE *f = fopen(p, "rb"); if (!f) return NULL; fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
    char *b = calloc(1, (size_t)n + 1); if (fread(b, 1, (size_t)n, f) != (size_t)n) { free(b); b = NULL; } fclose(f); return b;
}

// What vka_shader.c does at a program whose shaders the (empty) library lacks: every stage is asked for, the program's (vertex, pixel) pairs with them
static vka_lreq *program(const vka_keyset *done, const uint64_t *keys, const char *const *stage, unsigned n) {
    vka_lreq *r = calloc(1, sizeof *r); uint8_t ctl[0xd8], code[300];
    for (unsigned i = 0; i < n; i++) {
        if (vka_keyset_has(done, keys[i])) continue;
        memset(ctl, (int)(0x10 + i), sizeof ctl); memset(code, (int)(0x80 + i), sizeof code);
        vka_lreq_add(r, keys[i], ctl, sizeof ctl, code, 100 + 50 * i);
    }
    for (unsigned a = 0; r->ns && a < n; a++) for (unsigned b = 0; b < n; b++)
        if (!strcmp(stage[a], "vertex") && !strcmp(stage[b], "pixel")) vka_lreq_pair(r, keys[a], keys[b]);
    return r;
}
// The caller's unmarking (vka_shader.c req_unwritten): the keys and pairs handed back
static vka_keyset *g_unmark_keys, *g_unmark_pairs; static int g_nunw, g_unw_err;
static void unwritten(void *ctx, int pair, uint64_t a, uint64_t b, int err) {
    (void)ctx; g_nunw++; g_unw_err = err;
    if (pair) { if (g_unmark_pairs) vka_keyset_del(g_unmark_pairs, vka_lreq_pair_id(a, b)); }
    else if (g_unmark_keys) vka_keyset_del(g_unmark_keys, a);
}
static int ask(vka_lrq *q, const char *root, vka_keyset *done, const uint64_t *keys, const char *const *stage, unsigned n) {   // (layer_request) the stages queued
    vka_lreq *r = program(done, keys, stage, n); unsigned ns = r->ns; uint64_t ks[VKA_LREQ_STAGES];
    for (unsigned i = 0; i < ns; i++) ks[i] = r->st[i].key;
    if (ns && vka_lrq_push(q, root, r)) { for (unsigned i = 0; i < ns; i++) vka_keyset_add(done, ks[i]); return (int)ns; }
    vka_lreq_free(r); return ns ? -1 : 0;
}

static void test_requests(void) {
    char root[512]; const char *tmp = getenv("TMPDIR"); snprintf(root, sizeof root, "%s/t_layerreq_XXXXXX", tmp && *tmp ? tmp : "/tmp");
    if (!mkdtemp(root)) { CHECK(0, "mkdtemp %s", root); return; }
    char lr[600]; snprintf(lr, sizeof lr, "%s/pack/shader_layer", root);   // DM_VK_LAYER_DIR inside a pack folder that has no layer yet: the writer makes it
    char pk[600]; snprintf(pk, sizeof pk, "%s/pack", root); mkdir(pk, 0777);
    static vka_lrq q = VKA_LRQ_INIT; static vka_keyset done;
    const uint64_t p1[3] = {0x1111000000000001ull, 0x1111000000000002ull, 0x1111000000000003ull}; const char *s1[3] = {"vertex", "pixel", "geometry"};
    CHECK(ask(&q, lr, &done, p1, s1, 3) == 3, "first program queued");
    const uint64_t p2[2] = {0x1111000000000001ull, 0x2222000000000002ull}; const char *s2[2] = {"vertex", "pixel"};   // shares the vertex shader: only its pixel shader is new
    CHECK(ask(&q, lr, &done, p2, s2, 2) == 1, "second program: one new stage");
    CHECK(ask(&q, lr, &done, p1, s1, 3) == 0, "the same program again: nothing asked");
    const uint64_t p3[1] = {0x3333000000000005ull}; const char *s3[1] = {"compute"};
    CHECK(ask(&q, lr, &done, p3, s3, 1) == 1, "a compute program queued");
    vka_lrq_drain(&q);
    char f[800];
    for (int i = 0; i < 3; i++) {
        snprintf(f, sizeof f, "%s/req/%016llx.ctl", lr, (unsigned long long)p1[i]); CHECK(fsize(f) == 0xd8, "%s: %ld bytes", f, fsize(f));
        snprintf(f, sizeof f, "%s/req/%016llx.code", lr, (unsigned long long)p1[i]); CHECK(fsize(f) == 100 + 50 * i, "%s: %ld bytes", f, fsize(f));
    }
    snprintf(f, sizeof f, "%s/req/%016llx.code", lr, (unsigned long long)p2[1]); CHECK(fsize(f) == 150, "%s: %ld", f, fsize(f));   // (the program's stage 1: 150 bytes)
    snprintf(f, sizeof f, "%s/req/%016llx.ctl", lr, (unsigned long long)p3[0]); CHECK(fsize(f) == 0xd8, "compute request");
    snprintf(f, sizeof f, "%s/req/pairs.tsv", lr); char *pairs = slurp(f);
    CHECK(pairs && !strcmp(pairs, "1111000000000001\t1111000000000002\n1111000000000001\t2222000000000002\n"), "pairs.tsv: %s", pairs ? pairs : "(none)");
    free(pairs);
    CHECK(q.written == 5, "%llu stages written", q.written);
    // A later run (a new key set): an earlier run's request is on disk, so it is not written again, and its program adds no pairs
    static vka_keyset done2; static vka_lrq q2 = VKA_LRQ_INIT;
    snprintf(f, sizeof f, "%s/req/%016llx.ctl", lr, (unsigned long long)p3[0]); FILE *o = fopen(f, "wb"); fputs("x", o); fclose(o);   // (marked: a 1-byte .ctl)
    CHECK(ask(&q2, lr, &done2, p3, s3, 1) == 1, "queued again in a new run");
    vka_lrq_drain(&q2);
    CHECK(fsize(f) == 1 && q2.written == 0, "an earlier run's request rewritten (%ld bytes, %llu written)", fsize(f), q2.written);
    // A full queue: refused, and the keys stay unasked so the next resolution asks again
    static vka_keyset done3; static vka_lrq q3 = VKA_LRQ_INIT; q3.max_bytes = 64;
    const uint64_t p4[1] = {0x4444000000000004ull}; const char *s4[1] = {"pixel"};
    CHECK(ask(&q3, lr, &done3, p4, s4, 1) == -1 && !vka_keyset_has(&done3, p4[0]) && q3.refused == 1, "a request past the bound refused, its key not marked");
    q3.max_bytes = 64u << 20;
    CHECK(ask(&q3, lr, &done3, p4, s4, 1) == 1, "asked again once there is room");
    vka_lrq_drain(&q3);
    snprintf(f, sizeof f, "%s/req/%016llx.ctl", lr, (unsigned long long)p4[0]); CHECK(fsize(f) == 0xd8, "the retried request written");
    // The folder cannot be made (a file in its place): nothing written, no crash
    char cmd[800];
    static vka_keyset done4; static vka_lrq q4 = VKA_LRQ_INIT; char bad[700]; snprintf(bad, sizeof bad, "%s/afile", root); o = fopen(bad, "wb"); fclose(o);
    CHECK(ask(&q4, bad, &done4, p4, s4, 1) == 1, "queued for a folder that cannot be made");
    vka_lrq_drain(&q4);
    CHECK(q4.written == 0, "written under a file: %llu", q4.written);
    // A stage the writer cannot write is handed back with its errno, so the caller unmarks it and asks again
    static vka_keyset done5; static vka_lrq q5 = VKA_LRQ_INIT; q5.unwritten = unwritten; g_unmark_keys = &done5; g_nunw = 0;
    CHECK(ask(&q5, bad, &done5, p4, s4, 1) == 1 && vka_keyset_has(&done5, p4[0]), "queued and marked");
    vka_lrq_drain(&q5);
    CHECK(g_nunw == 1 && g_unw_err == ENOTDIR && !vka_keyset_has(&done5, p4[0]) && q5.failed == 1, "an unwritten stage handed back (%d calls, errno %d, failed %llu)", g_nunw, g_unw_err, q5.failed);
    // The folder removed while the game runs (Storage): made again at the next request
    static vka_keyset done6; static vka_lrq q6 = VKA_LRQ_INIT; q6.unwritten = unwritten; g_unmark_keys = &done6; g_nunw = 0;
    char lr6[700]; snprintf(lr6, sizeof lr6, "%s/pack/layer6", root);
    const uint64_t p6[1] = {0x6666000000000006ull}; const uint64_t p7[1] = {0x7777000000000007ull};
    CHECK(ask(&q6, lr6, &done6, p6, s4, 1) == 1, "queued (layer6)"); vka_lrq_drain(&q6);
    snprintf(cmd, sizeof cmd, "rm -rf '%s'", lr6); if (system(cmd)) {}
    CHECK(ask(&q6, lr6, &done6, p7, s4, 1) == 1, "queued after the folder went"); vka_lrq_drain(&q6);
    snprintf(f, sizeof f, "%s/req/%016llx.ctl", lr6, (unsigned long long)p7[0]);
    CHECK(fsize(f) == 0xd8 && g_nunw == 0 && q6.written == 2, "the folder made again (%ld bytes, %d unwritten, %llu written)", fsize(f), g_nunw, q6.written);
    // Pairs: a program whose stages were all asked for before still records a new pair (a pairs-only request); a pair is appended once, across runs too; a last line an
    // earlier stop cut short is ended before the next pair
    static vka_lrq q7 = VKA_LRQ_INIT; q7.unwritten = unwritten;
    vka_lreq *r = calloc(1, sizeof *r); vka_lreq_pair(r, p6[0], p7[0]); CHECK(!vka_lreq_pair(r, p6[0], p7[0]) && r->np == 1, "a pair twice in one request");
    CHECK(vka_lrq_push(&q7, lr6, r), "a pairs-only request queued"); vka_lrq_drain(&q7);
    snprintf(f, sizeof f, "%s/req/pairs.tsv", lr6); char *pt = slurp(f);
    CHECK(pt && !strcmp(pt, "6666000000000006\t7777000000000007\n"), "pairs-only request: %s", pt ? pt : "(none)"); free(pt);
    r = calloc(1, sizeof *r); vka_lreq_pair(r, p6[0], p7[0]); vka_lrq_push(&q7, lr6, r); vka_lrq_drain(&q7);
    pt = slurp(f); CHECK(pt && strlen(pt) == 34, "a pair appended twice in a run: %s", pt ? pt : "(none)"); free(pt);
    o = fopen(f, "ab"); fputs("6666000000000006\t88", o); fclose(o);   // (a later run starts on a file whose last line was cut)
    static vka_lrq q8 = VKA_LRQ_INIT;
    r = calloc(1, sizeof *r); vka_lreq_pair(r, p6[0], p7[0]); vka_lreq_pair(r, p7[0], p6[0]); vka_lrq_push(&q8, lr6, r); vka_lrq_drain(&q8);
    pt = slurp(f);
    CHECK(pt && !strcmp(pt, "6666000000000006\t7777000000000007\n6666000000000006\t88\n7777000000000007\t6666000000000006\n"), "a later run: %s", pt ? pt : "(none)"); free(pt);
    // A pair that cannot be appended is handed back
    static vka_keyset pairs9; static vka_lrq q9 = VKA_LRQ_INIT; q9.unwritten = unwritten; g_unmark_pairs = &pairs9; g_nunw = 0;
    vka_keyset_add(&pairs9, vka_lreq_pair_id(p6[0], p7[0]));
    r = calloc(1, sizeof *r); vka_lreq_pair(r, p6[0], p7[0]); vka_lrq_push(&q9, bad, r); vka_lrq_drain(&q9);
    CHECK(g_nunw == 1 && !vka_keyset_has(&pairs9, vka_lreq_pair_id(p6[0], p7[0])), "an unwritten pair handed back (%d)", g_nunw);
    CHECK(vka_lreq_pair_id(1, 2) != vka_lreq_pair_id(2, 1) && vka_lreq_pair_id(0, 0), "pair ids");
    snprintf(cmd, sizeof cmd, "rm -rf '%s'", root); if (system(cmd)) {}
}

int main(void) {
    test_root(); test_empty(); test_keyset(); test_lifetime(); test_requests();
    if (g_fail) { printf("t_android_layerreq: %d failure(s)\n", g_fail); return 1; }
    printf("t_android_layerreq: ok\n");
    return 0;
}
