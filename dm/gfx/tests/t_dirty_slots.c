#include "../nvn/nvn_dirty.h"
#include "../../host/dm.h"
#include <sys/mman.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <pthread.h>
#include <stdatomic.h>

module_t *g_mod;
int g_nmod;
module_t *module_of(const void *p) { (void)p; return NULL; }
void crash_install(void);

static int g_fail;
#define EXPECT(name, want, got) do { \
    long long want_ = (long long)(want), got_ = (long long)(got); \
    printf("%-52s expected %-4lld → got %-4lld %s\n", name, want_, got_, want_ == got_ ? "✓" : "✗"); \
    if (want_ != got_) g_fail++; \
} while (0)

static void *page_map(void) {
    void *p = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
    if (p == MAP_FAILED) { perror("mmap"); exit(2); }
    return p;
}

// Lookup cache (find_span): adjacent pools can share a host page after rounding, and only the protected one gets a generation on the write fault. Warming the other
// range must not change which range a later lookup selects. GUEST: a quarter host page (the guest's 4 KB on the Mac's 16 KB pages; 1 KB on 4 KB pages)
enum { PROBE = 16 };
enum { ENDS_SOONER, STARTS_LATER };
static void *shared_page_cache(void *arg) {
    int layout = (int)(intptr_t)arg;
    size_t pg = (size_t)getpagesize(), guest = pg / 4;
    uint8_t *m = mmap(NULL, 4 * pg, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
    if (m == MAP_FAILED) { perror("mmap"); exit(2); }
    uint8_t *first, *second; const void *second_only; size_t nfirst, nsecond;
    if (layout == STARTS_LATER) { first = m + 2 * pg - guest; nfirst = guest; second = m; nsecond = 2 * pg - guest; second_only = m; }
    else { first = m; nfirst = pg - guest; second = m + pg - guest; nsecond = 2 * pg; second_only = m + pg; }
    nvn_dirty_add_range(first, nfirst);
    const void *first_range = nvn_dirty_span(first, PROBE);   // looked up before its neighbour exists
    nvn_dirty_add_range(second, nsecond);
    uint64_t stamp = nvn_dirty_now();
    nvn_dirty_protect(first, PROBE);
    const void *other = nvn_dirty_span(second_only, pg);
    first[0] = 7;
    printf("lookup cache, shared page (%s):\n", layout == STARTS_LATER ? "earlier range starts later" : "earlier range ends sooner");
    EXPECT("warmed a different containing range", 1, first_range != other);
    EXPECT("cached lookup still sees the write", 1, nvn_dirty_since(first, PROBE, stamp));
    EXPECT("cached lookup keeps the first containing range", 1, nvn_dirty_span(first, PROBE) == first_range);
    nvn_dirty_remove_range(first); nvn_dirty_remove_range(second);
    munmap(m, 4 * pg);
    return NULL;
}
// Another thread's cached selection of a later range is dropped when an earlier slot is reused by a pool that holds the span
typedef struct { const void *probe, *want; _Atomic int phase; int matched; } reuse_t;
static void *reuse_reader(void *arg) {
    reuse_t *t = arg;
    nvn_dirty_span(t->probe, PROBE);   // warm while only the later slot holds the span
    atomic_store(&t->phase, 1);
    while (atomic_load(&t->phase) != 2) usleep(100);
    t->matched = nvn_dirty_span(t->probe, PROBE) == t->want;
    return NULL;
}
static void cache_slot_reuse(void) {
    size_t pg = (size_t)getpagesize(), guest = pg / 4;
    uint8_t *m = mmap(NULL, 4 * pg, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
    if (m == MAP_FAILED) { perror("mmap"); exit(2); }
    uint8_t *later = m + 2 * pg;
    nvn_dirty_add_range(m, pg);
    nvn_dirty_add_range(later, 2 * pg);
    const void *first_slot = nvn_dirty_span(m, PROBE), *later_slot = nvn_dirty_span(later, 2 * pg);
    nvn_dirty_remove_range(m);
    uint8_t *repl = later + guest;
    reuse_t t = { .probe = repl, .want = first_slot };
    pthread_t th; if (pthread_create(&th, NULL, reuse_reader, &t)) exit(2);
    while (atomic_load(&t.phase) != 1) usleep(100);
    nvn_dirty_add_range(repl, pg - guest);   // takes the earlier slot, overlapping the reader's cached range
    atomic_store(&t.phase, 2);
    pthread_join(th, NULL);
    EXPECT("slot reuse drops another thread's cached selection", 1, t.matched);
    EXPECT("the reused earlier slot is the first match", 1, nvn_dirty_span(repl, PROBE) == first_slot);
    nvn_dirty_remove_range(repl);
    EXPECT("retiring a cached match falls back to the remaining range", 1, nvn_dirty_span(repl, PROBE) == later_slot);
    nvn_dirty_remove_range(later);
    munmap(m, 4 * pg);
}

int main(void) {    crash_install();

    for (int i = 0; i < 65; i++) {
        void *p = page_map();
        nvn_dirty_add_range(p, 4096);
        nvn_dirty_remove_range(p);
        munmap(p, 4096);
    }

    void *reused = page_map();
    nvn_dirty_add_range(reused, 4096);
    nvn_dirty_protect(reused, 4096);
    uint64_t stamp = nvn_dirty_now();
    ((volatile uint8_t *)reused)[0] = 1;
    EXPECT("after 65 pool destroys in total, a write to a new pool is dirty", 1, nvn_dirty_since(reused, 4096, stamp));
    nvn_dirty_remove_range(reused);
    munmap(reused, 4096);

    // A pool destroyed and another registered over the same memory (the same slot): the new pool's data was written while the memory was in no pool, so no page fault and no
    // generation saw it, and the generations start again at 0. A stamp from the old pool's time must count as written (born): a caller's kept handle (nvn_dirty_span) outlives its pool
    void *again = page_map();
    nvn_dirty_add_range(again, 4096);
    nvn_dirty_protect(again, 4096);
    stamp = nvn_dirty_now();
    const void *kept = nvn_dirty_span(again, 4096);
    EXPECT("a protected pool not written: clean", 0, nvn_dirty_since_span(kept, again, 4096, stamp));
    nvn_dirty_remove_range(again);
    ((volatile uint8_t *)again)[0] = 3;   // the next pool's data, written with no pool registered: no fault
    nvn_dirty_add_range(again, 4096);
    EXPECT("same memory, a new pool: an older stamp is dirty", 1, nvn_dirty_since(again, 4096, stamp));
    EXPECT("the same, through the handle kept from the old pool", 1, nvn_dirty_since_span(kept, again, 4096, stamp));
    { size_t lo = 1, hi = 0; EXPECT("the same, as written bounds: all of it", 1, nvn_dirty_bounds_since(kept, again, 4096, stamp, &lo, &hi) && lo == 0 && hi == 4096); }
    uint64_t stamp2 = nvn_dirty_now();
    EXPECT("a stamp taken after the new pool's registration: clean", 0, nvn_dirty_since(again, 4096, stamp2));
    nvn_dirty_remove_range(again);
    munmap(again, 4096);

    void *live[300];
    for (int i = 0; i < 300; i++) {
        live[i] = page_map();
        nvn_dirty_add_range(live[i], 4096);
    }
    void *overflow = live[299];
    nvn_dirty_protect(overflow, 4096);
    stamp = nvn_dirty_now();
    ((volatile uint8_t *)overflow)[0] = 2;
    EXPECT("pools beyond the live limit are conservatively dirty", 1, nvn_dirty_since(overflow, 4096, stamp));
    for (int i = 0; i < 300; i++) {
        nvn_dirty_remove_range(live[i]);
        munmap(live[i], 4096);
    }

    // More pools alive at once than the table's fixed 4,096 slots used to hold (Breath of the Wild reaches 4,006 in its first shrine): the table grows, and the last pool is still tracked
    enum { NMANY = 5000 };
    void **many = malloc(NMANY * sizeof *many);
    for (int i = 0; i < NMANY; i++) { many[i] = page_map(); nvn_dirty_add_range(many[i], 4096); }
    void *last = many[NMANY - 1];
    EXPECT("5000 live pools: the last one is tracked", 1, nvn_dirty_tracked(last, 4096));
    nvn_dirty_protect(last, 4096);
    stamp = nvn_dirty_now();
    EXPECT("pool 5000 not written after protect: clean", 0, nvn_dirty_since(last, 4096, stamp));
    ((volatile uint8_t *)last)[0] = 5;
    EXPECT("pool 5000 written by the game: dirty", 1, nvn_dirty_since(last, 4096, stamp));
    for (int i = 0; i < NMANY; i++) { nvn_dirty_remove_range(many[i]); munmap(many[i], 4096); }
    free(many);

    // Adjacent pools sharing a host page (pools are 4 KB aligned, host pages 16 KB): the first page of SMBW's ASTC texture pool is shared with a small preceding pool, and was judged untracked and re-uploaded on every use
    size_t pg = (size_t)getpagesize();
    uint8_t *blk = mmap(NULL, 4 * pg, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
    if (blk == MAP_FAILED) { perror("mmap"); exit(2); }
    uint8_t *pa = blk, *pb = blk + pg - 0x1000;           // pool A covers the start of page 0, pool B starts in the last 4 KB of page 0
    size_t na = pg - 0x1000, nb = 2 * pg, tex = pg + 0x800;   // the texture in B spans the shared page and the next one
    nvn_dirty_add_range(pa, na);
    nvn_dirty_add_range(pb, nb);
    EXPECT("texture in the later of two page-sharing pools is tracked", 1, nvn_dirty_tracked(pb, tex));
    nvn_dirty_protect(pb, tex);
    stamp = nvn_dirty_now();
    EXPECT("page-sharing texture not written after protect: clean", 0, nvn_dirty_since(pb, tex, stamp));
    pb[0x10] = 3;
    EXPECT("game writes B's part of the shared page: B's texture dirty", 1, nvn_dirty_since(pb, tex, stamp));
    nvn_dirty_protect(pb, tex);
    stamp = nvn_dirty_now();
    pa[0x10] = 4;   // same physical page, A's part: the page is read-only, the fault must be claimed through B's range or it is treated as a crash
    EXPECT("game writes A's part of the shared page: B's texture conservatively dirty", 1, nvn_dirty_since(pb, tex, stamp));
    nvn_dirty_protect(pb, tex);
    stamp = nvn_dirty_now();
    dm_guest_write_prepare(pa, 0x20); pa[0x20] = 5;   // the host writes A on behalf of the GPU: the shared page must also release B's protection
    EXPECT("host unprotects the shared page before writing: B's texture dirty", 1, nvn_dirty_since(pb, tex, stamp));
    nvn_dirty_remove_range(pb);
    EXPECT("A still tracked after destroying B (ranges keyed by pool start)", 1, nvn_dirty_tracked(pa, na));
    EXPECT("B no longer tracked after destroying B", 0, nvn_dirty_tracked(pb, tex));
    nvn_dirty_remove_range(pa);
    munmap(blk, 4 * pg);
    for (int layout = ENDS_SOONER; layout <= STARTS_LATER; layout++) {   // each on a new thread, with an empty lookup cache
        pthread_t th; if (pthread_create(&th, NULL, shared_page_cache, (void *)(intptr_t)layout)) exit(2);
        pthread_join(th, NULL);
    }
    cache_slot_reuse();
    return g_fail != 0;
}
