// Speculative pipeline compiles that did not finish (vka_pso.c spec_begin / spec_end / unf_load), free of Vulkan so the Mac's unit test (dm/host/tests/t_android_pwbusy.c)
// checks it. A speculative compile (a prewarm key of an earlier run, the optimizer's twin of a linked pipeline) is one no draw asked for yet. While one runs, its shader
// key is in <cache file>.busy beside the driver's pipeline cache; it leaves the file when the build returns. A key still there at the next start was being compiled when
// the process ended: it moves to <cache file>.unfinished, and prewarm and the optimizer leave it out on this driver from then on. A build of it that does finish (a draw
// needs it: the frame path and the asynchronous threads are never held) takes it off the list again.
// Why: one compile can end the process. Pokopia's compute shader af8f64d9f5542ef2 (1.6 MB of SPIR-V) runs Qualcomm's compiler (System Driver v800.72, Adreno 830) for
// 60-77 s, and its working memory, 64 KiB blocks each with a guard map, takes the maps outside the guest block from 7,700 to 65,800: past vm.max_map_count the driver's
// next allocation fails (Scudo internal map failure, std::bad_alloc, SIGABRT), 4 of 4 starts on the first-boot language screen, which needs no such pipeline. The .heavy
// list (build_end) never learned it, because the build never ended, and the maps gate (vkpg_spec_ok) checks only before a compile starts, so every start tried it again.
// A workaround: the cause is in the driver's compiler, which the host cannot change; docs/reference/memory.md has the entry.
#ifndef VKA_PWBUSY_H
#define VKA_PWBUSY_H
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { VKPB_MAX = 256 };   // keys a set holds (busy: compiles at once, at most a handful; unfinished: a driver's runaway shaders, a few)
typedef struct { uint64_t k[VKPB_MAX]; int n; } vkpb_set;

static inline int vkpb_has(const vkpb_set *s, uint64_t k) { for (int i = 0; i < s->n; i++) if (s->k[i] == k) return 1; return 0; }
// 1 = added; 0 for key 0, a key already there, or a full set
static inline int vkpb_add(vkpb_set *s, uint64_t k) {
    if (!k || vkpb_has(s, k) || s->n >= VKPB_MAX) return 0;
    s->k[s->n++] = k; return 1;
}
// 1 = removed (the others keep their order)
static inline int vkpb_del(vkpb_set *s, uint64_t k) {
    for (int i = 0; i < s->n; i++) if (s->k[i] == k) { memmove(&s->k[i], &s->k[i + 1], (size_t)(s->n - i - 1) * sizeof s->k[0]); s->n--; return 1; }
    return 0;
}
// A file's text, a hex key a line (as written by vkpb_format): the keys added. Lines that are not a key (empty, damaged, a truncated last one) are skipped
static inline int vkpb_parse(vkpb_set *s, const char *t, size_t len) {
    int added = 0; size_t i = 0;
    while (i < len) {
        size_t e = i; while (e < len && t[e] != '\n') e++;
        if (e - i == 16) {
            uint64_t k = 0; int ok = 1;
            for (size_t j = i; j < e && ok; j++) { char c = t[j]; int d = c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : c >= 'A' && c <= 'F' ? c - 'A' + 10 : -1; if (d < 0) ok = 0; else k = k << 4 | (uint64_t)d; }
            if (ok) added += vkpb_add(s, k);
        }
        i = e + 1;
    }
    return added;
}
// The set as a file's text into b (cap bytes, NUL-terminated): its length, or 0 when it does not fit (cap of 17 bytes a key and 1 suffices)
static inline size_t vkpb_format(const vkpb_set *s, char *b, size_t cap) {
    size_t o = 0;
    if (!cap) return 0;
    for (int i = 0; i < s->n; i++) { int w = snprintf(b + o, cap - o, "%016llx\n", (unsigned long long)s->k[i]); if (w < 0 || (size_t)w >= cap - o) { b[0] = 0; return 0; } o += (size_t)w; }
    b[o] = 0; return o;
}
// At a start: every key of the busy file joins the unfinished ones. The keys that are new there
static inline int vkpb_carry(vkpb_set *unf, const vkpb_set *busy) { int n = 0; for (int i = 0; i < busy->n; i++) n += vkpb_add(unf, busy->k[i]); return n; }
#endif
