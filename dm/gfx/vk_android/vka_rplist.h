// The classic render passes' list (vka_draw.c rp_obtain, DM_VK_CLASSIC_RP): one VkRenderPass per shape and use, kept for the run. Two uses of one shape get two objects:
// VKRL_PASS, the one vkCmdBeginRenderPass begins, and VKRL_PIPE, the one graphics pipelines are made against (vka_rp_compat). Vulkan's render pass compatibility makes
// a pipeline made against either usable in a pass begun with the other (same formats and samples; loads and clears do not count).
// Why two (docs/reference/rendering.md "Classic render passes crashed Qualcomm's driver in vkCmdBeginRenderPass after refused pipelines"): Qualcomm's driver on the AYN Thor's Android 13
// (Adreno 740, build 69e13475cb) refuses some of Ocarina of Time's pipelines with VK_ERROR_UNKNOWN, and with classic render passes every such run then crashed in
// vkCmdBeginRenderPass on the encoder thread (SIGSEGV at 0x140), while the same refusals with dynamic rendering did not crash (the driver's side is inferred, not
// proven). The pipeline is skipped, as on every driver, and the render pass given to the refused create is no longer the one passes begin. A pipeline object it was given to and the driver refused is also retired
// for later pipelines of its shape (vkrl_refused): they get a new one.
// Pure bookkeeping, free of Vulkan and Android, so the Mac's unit test (dm/host/tests/t_android_rplist.c) can check it; handles are 64-bit values, 0 none.
#ifndef VKA_RPLIST_H
#define VKA_RPLIST_H
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

enum { VKRL_PASS = 0, VKRL_PIPE = 1, VKRL_KEYMAX = 64 };
typedef struct { uint8_t key[VKRL_KEYMAX]; uint32_t klen, refused; uint64_t rp; uint8_t use, retired; } vkrl_ent;
typedef struct { vkrl_ent *e; int n, cap; uint32_t refused, retired; } vkrl;

// The live object of this shape and use, or 0
static inline uint64_t vkrl_find(const vkrl *l, int use, const void *key, uint32_t klen) {
    if (klen > VKRL_KEYMAX) return 0;
    for (int i = 0; i < l->n; i++) {
        const vkrl_ent *x = &l->e[i];
        if (!x->retired && x->use == use && x->klen == klen && !memcmp(x->key, key, klen)) return x->rp;
    }
    return 0;
}
// A new object for this shape and use (made by the caller). 0 = not kept (out of memory or key too long): the caller still uses it, as before
static inline int vkrl_add(vkrl *l, int use, const void *key, uint32_t klen, uint64_t rp) {
    if (!rp || klen > VKRL_KEYMAX) return 0;
    if (l->n == l->cap) {
        int nc = l->cap ? 2 * l->cap : 64; vkrl_ent *n = (vkrl_ent *)realloc(l->e, (size_t)nc * sizeof *n);
        if (!n) return 0;
        l->e = n; l->cap = nc;
    }
    vkrl_ent *x = &l->e[l->n++]; memset(x, 0, sizeof *x);
    memcpy(x->key, key, klen); x->klen = klen; x->use = (uint8_t)use; x->rp = rp;
    return 1;
}
static inline vkrl_ent *vkrl_of(vkrl *l, uint64_t rp) {
    if (!rp) return NULL;
    for (int i = 0; i < l->n; i++) if (l->e[i].rp == rp) return &l->e[i];
    return NULL;
}
// The driver refused a pipeline made against rp. A pipeline object (VKRL_PIPE) is retired: the next pipeline of its shape gets a new one (the old one stays alive:
// pipelines made against it hold no reference, and a thread may be making one now). A pass object (VKRL_PASS, when pipelines share it: DM_VK_RP_SHARED=1) is only
// counted. Returns 1 at the first refusal against rp (the caller logs it), else 0
static inline int vkrl_refused(vkrl *l, uint64_t rp) {
    vkrl_ent *x = vkrl_of(l, rp);
    l->refused++;
    if (!x) return 0;
    int first = x->refused++ == 0;
    if (x->use == VKRL_PIPE && !x->retired) { x->retired = 1; l->retired++; }
    return first;
}
#endif
