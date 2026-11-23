// Where the process's RAM is, by category (the `[mem] rss:` line, vka_mem.c rss_main): /proc/self/smaps summed in one pass into the guest block, the pools in files,
// the GPU driver's maps, other anonymous memory and files, with /proc/meminfo's MemAvailable and zram swap, free of Vulkan so the Mac's unit tests
// (dm/host/tests/t_android_rsslog.c) can check the parser. docs/reference/memory.md "A per-category RSS line".
//
// Categories (each map goes into exactly one, in this order):
//   driver      the name has "kgsl", starts with /dev/ or has dmabuf: the GPU driver's memory (CPU maps of its allocations)
//   pools_file  an unlinked file ("/... (deleted)"): the file-backed pools (DM_MEM_FILEBACK, TMPDIR) and memfds
//   guest_none  inside the guest block, no access (---p): memory the host gave back (guest_release) or has not opened. Resident pages here are the ones the host
//               unmapped or freed but the kernel still holds
//   guest       inside the guest block otherwise: the game's heap, stacks, alias region (anonymous)
//   file        any other named file: the libraries, the APK, fonts, caches
//   anon        everything else: the host's malloc, thread stacks, the driver's compiler blocks, [anon:...]
#ifndef VKA_RSSLOG_H
#define VKA_RSSLOG_H
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "vka_mapbudget.h"

enum { VKRS_DRIVER, VKRS_POOLS, VKRS_GUEST_NONE, VKRS_GUEST, VKRS_FILE, VKRS_ANON, VKRS_N };
static const char *const vkrs_name[VKRS_N] = {"driver", "pools in files", "guest unmapped", "guest", "files", "other anon"};

typedef struct {
    uint64_t rss[VKRS_N], pss[VKRS_N], swap[VKRS_N];   // kB, as smaps gives them
    long maps[VKRS_N];
    int cur;                                            // the category of the map whose fields come next (-1 before the first)
} vkrs_t;

static inline int vkrs_has(const char *s, size_t n, const char *w) {
    size_t k = strlen(w);
    for (size_t i = 0; i + k <= n; i++) if (!memcmp(s + i, w, k)) return 1;
    return 0;
}
// The category of one map: its start, permissions (4 characters) and name, with the guest block [glo, ghi)
static inline int vkrs_class(uint64_t lo, const char perms[5], const char *nm, size_t nl, uint64_t glo, uint64_t ghi) {
    if (vkrs_has(nm, nl, "kgsl") || (nl >= 5 && !memcmp(nm, "/dev/", 5)) || vkrs_has(nm, nl, "dmabuf")) return VKRS_DRIVER;
    if (nl > 10 && nm[0] == '/' && !memcmp(nm + nl - 10, " (deleted)", 10)) return VKRS_POOLS;
    if (lo >= glo && lo < ghi) return perms[0] == '-' && perms[1] == '-' && perms[2] == '-' ? VKRS_GUEST_NONE : VKRS_GUEST;
    if (nl && nm[0] == '/') return VKRS_FILE;
    return VKRS_ANON;
}
static inline void vkrs_init(vkrs_t *s) { memset(s, 0, sizeof *s); s->cur = -1; }
// One line of /proc/self/smaps (without its newline): a map's header starts a category; its Rss, Pss and Swap fields (kB) add to it. Other lines are ignored
static inline void vkrs_line(vkrs_t *s, uint64_t glo, uint64_t ghi, const char *ln, size_t len) {
    uint64_t a; int kg;
    if (vkmb_line(ln, len, &a, &kg)) {
        uint64_t lo, hi; char pm[5]; const char *nm; size_t nl;
        if (vkmb_fields(ln, len, &lo, &hi, pm, &nm, &nl)) { s->cur = vkrs_class(lo, pm, nm, nl, glo, ghi); s->maps[s->cur]++; }
        else s->cur = -1;
        return;
    }
    if (s->cur < 0) return;
    uint64_t *to = NULL; size_t k = 0;
    if (len > 4 && !memcmp(ln, "Rss:", 4)) { to = &s->rss[s->cur]; k = 4; }
    else if (len > 4 && !memcmp(ln, "Pss:", 4)) { to = &s->pss[s->cur]; k = 4; }
    else if (len > 5 && !memcmp(ln, "Swap:", 5)) { to = &s->swap[s->cur]; k = 5; }
    if (!to) return;
    while (k < len && ln[k] == ' ') k++;
    uint64_t v = 0; for (; k < len && ln[k] >= '0' && ln[k] <= '9'; k++) v = v * 10 + (uint64_t)(ln[k] - '0');
    *to += v;
}
// A whole buffer of smaps text (the tests' fixtures)
static inline void vkrs_text(vkrs_t *s, uint64_t glo, uint64_t ghi, const char *t, size_t n) {
    size_t st = 0;
    for (size_t i = 0; i < n; i++) if (t[i] == '\n') { vkrs_line(s, glo, ghi, t + st, i - st); st = i + 1; }
    if (st < n) vkrs_line(s, glo, ghi, t + st, n - st);
}
// The value of "Key:" (kB) at the start of a line of /proc/meminfo or /proc/self/smaps_rollup; 0 = not there
static inline uint64_t vkrs_kb(const char *t, const char *key) {
    size_t kl = strlen(key);
    for (const char *p = t; *p; ) {
        if (!strncmp(p, key, kl) && p[kl] == ':') return strtoull(p + kl + 1, NULL, 10);
        while (*p && *p != '\n') p++;
        if (*p) p++;
    }
    return 0;
}
// The line (after its "[mem] rss:" prefix): each category's RSS / PSS / swap in MiB, the totals, the guest memory the host gave back but the kernel still holds, MemAvailable
// and zram swap in use. rollup: the kernel's own totals (smaps_rollup) as a check of the sum; meminfo: /proc/meminfo's text
static inline void vkrs_format(char *b, size_t n, const vkrs_t *s, const char *rollup, const char *meminfo) {
    uint64_t r = 0, p = 0, w = 0; size_t o = 0;
    for (int i = 0; i < VKRS_N; i++) { r += s->rss[i]; p += s->pss[i]; w += s->swap[i]; }
    o += (size_t)snprintf(b + o, o < n ? n - o : 0, "total %.0f MiB (pss %.0f, in swap %.0f)", r / 1024.0, p / 1024.0, w / 1024.0);
    for (int i = 0; i < VKRS_N; i++)
        o += (size_t)snprintf(b + o, o < n ? n - o : 0, "; %s %.0f/%.0f/%.0f MiB (%ld maps)", vkrs_name[i], s->rss[i] / 1024.0, s->pss[i] / 1024.0, s->swap[i] / 1024.0, s->maps[i]);
    o += (size_t)snprintf(b + o, o < n ? n - o : 0, " [rss/pss/swap]; guest memory unmapped by the host but resident: %.0f MiB (%llu pages of 4 KiB)",
                          s->rss[VKRS_GUEST_NONE] / 1024.0, (unsigned long long)(s->rss[VKRS_GUEST_NONE] / 4));
    if (rollup && *rollup) o += (size_t)snprintf(b + o, o < n ? n - o : 0, "; smaps_rollup rss %.0f pss %.0f swap %.0f MiB", vkrs_kb(rollup, "Rss") / 1024.0, vkrs_kb(rollup, "Pss") / 1024.0, vkrs_kb(rollup, "Swap") / 1024.0);
    if (meminfo && *meminfo) {
        uint64_t st = vkrs_kb(meminfo, "SwapTotal"), sf = vkrs_kb(meminfo, "SwapFree");
        o += (size_t)snprintf(b + o, o < n ? n - o : 0, "; MemAvailable %.0f of %.0f MiB, swap in use %.0f of %.0f MiB (zram)", vkrs_kb(meminfo, "MemAvailable") / 1024.0, vkrs_kb(meminfo, "MemTotal") / 1024.0,
                              (st > sf ? st - sf : 0) / 1024.0, st / 1024.0);
    }
}
#endif
