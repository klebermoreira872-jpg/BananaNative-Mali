// The `[mem] rss:` line's parser (dm/gfx/vk_android/vka_rsslog.h; vka_mem.c rss_log): /proc/self/smaps text into categories, and the line built from them.
// The fixture is smaps as the kernel writes it (fields of one map in order, VmFlags last), with a guest block at 0x7000000000-0x7100000000
#include <stdio.h>
#include "../../gfx/vk_android/vka_rsslog.h"

static int fails;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

#define FIELDS(rss, pss, swap) "Size:             99999 kB\nKernelPageSize:        4 kB\nRss:             " #rss " kB\nPss:             " #pss " kB\nPss_Dirty:             0 kB\nShared_Clean:          0 kB\n" \
    "Private_Dirty:         0 kB\nAnonymous:             0 kB\nSwap:            " #swap " kB\nSwapPss:           777 kB\nLocked:                0 kB\nVmFlags: rd wr mr mw me ac\n"

static const char smaps[] =
    "7000000000-7010000000 rw-p 00000000 00:00 0                              [anon:dm_guest]\n" FIELDS(1000, 1000, 200)       // guest heap
    "7010000000-7020000000 ---p 00000000 00:00 0                              [anon:dm_guest]\n" FIELDS(300, 300, 50)         // given back, still resident
    "7020000000-7021000000 rw-s 00000000 fd:0e 1234                           /data/user/0/dev.nxnative.android/cache/fb-1 (deleted)\n" FIELDS(64, 64, 0)   // a pool moved into the file, inside the guest block
    "7030000000-7031000000 rw-s 00000000 00:00 99                             /dev/kgsl-3d0\n" FIELDS(4000, 4000, 0)           // placed memory inside the guest block
    "7200000000-7210000000 rw-s 00000000 00:00 99                             /dev/kgsl-3d0\n" FIELDS(2000, 2000, 0)
    "7300000000-7300100000 rw-p 00000000 00:00 0                              [anon:scudo:primary]\n" FIELDS(500, 500, 100)
    "7400000000-7400001000 rw-p 00000000 00:00 0 \n" FIELDS(4, 4, 0)                                                           // no name
    "7500000000-7500400000 r-xp 00000000 fd:03 77                             /system/lib64/libc.so\n" FIELDS(700, 90, 0)
    "7600000000-7600100000 rw-s 00000000 00:01 5                              /memfd:vk (deleted)\n" FIELDS(10, 10, 0)
    "7700000000-7700001000 rw-p 00000000 00:00 0                              [stack]\n" FIELDS(8, 8, 0);

int main(void) {
    const uint64_t glo = 0x7000000000ull, ghi = 0x7100000000ull;
    vkrs_t s; vkrs_init(&s); vkrs_text(&s, glo, ghi, smaps, sizeof smaps - 1);
    CHECK(s.rss[VKRS_GUEST] == 1000 && s.swap[VKRS_GUEST] == 200 && s.maps[VKRS_GUEST] == 1, "guest: rss %llu swap %llu maps %ld", (unsigned long long)s.rss[VKRS_GUEST], (unsigned long long)s.swap[VKRS_GUEST], s.maps[VKRS_GUEST]);
    CHECK(s.rss[VKRS_GUEST_NONE] == 300 && s.pss[VKRS_GUEST_NONE] == 300 && s.maps[VKRS_GUEST_NONE] == 1, "an inaccessible guest map is the host's unmapped but resident memory");
    CHECK(s.rss[VKRS_POOLS] == 64 + 10 && s.maps[VKRS_POOLS] == 2, "a deleted file (the pool file, a memfd) is pools in files, also inside the guest block: %llu", (unsigned long long)s.rss[VKRS_POOLS]);
    CHECK(s.rss[VKRS_DRIVER] == 6000 && s.maps[VKRS_DRIVER] == 2, "kgsl maps are the driver's, inside the guest block or not: %llu", (unsigned long long)s.rss[VKRS_DRIVER]);
    CHECK(s.rss[VKRS_ANON] == 500 + 4 + 8 && s.swap[VKRS_ANON] == 100 && s.maps[VKRS_ANON] == 3, "named, unnamed and stack anonymous memory outside the guest block: %llu", (unsigned long long)s.rss[VKRS_ANON]);
    CHECK(s.rss[VKRS_FILE] == 700 && s.pss[VKRS_FILE] == 90 && s.maps[VKRS_FILE] == 1, "a library is a file");
    uint64_t sw = 0; for (int i = 0; i < VKRS_N; i++) sw += s.swap[i];
    CHECK(sw == 350, "SwapPss is not swap: %llu", (unsigned long long)sw);
    vkrs_t t; vkrs_init(&t); vkrs_text(&t, glo, ghi, smaps, sizeof smaps - 1);
    CHECK(!memcmp(&s, &t, sizeof s), "deterministic");
    vkrs_t e; vkrs_init(&e); vkrs_text(&e, glo, ghi, "Rss:   5 kB\nVmFlags: rd\n", 22);
    CHECK(e.rss[VKRS_ANON] == 0 && e.maps[VKRS_ANON] == 0, "fields before any map header are dropped");
    // meminfo and the rollup
    const char mi[] = "MemTotal:       11534336 kB\nMemFree:          200000 kB\nMemAvailable:    1048576 kB\nSwapTotal:       8388608 kB\nSwapFree:        5242880 kB\n";
    const char roll[] = "7000000000-7700001000 ---p 00000000 00:00 0                              [rollup]\nRss:              14000 kB\nPss:               9000 kB\nSwap:               350 kB\n";
    CHECK(vkrs_kb(mi, "MemAvailable") == 1048576 && vkrs_kb(mi, "MemTotal") == 11534336 && vkrs_kb(mi, "Mem") == 0 && vkrs_kb(mi, "Swap") == 0, "meminfo keys match whole names");
    CHECK(vkrs_kb(roll, "Rss") == 14000 && vkrs_kb(roll, "Swap") == 350, "rollup");
    char b[2048]; vkrs_format(b, sizeof b, &s, roll, mi);
    printf("sample: [dm] [mem] rss: %s\n", b);
    CHECK(strstr(b, "guest memory unmapped by the host but resident: 0 MiB (75 pages of 4 KiB)") != NULL, "300 kB = 75 pages: %s", b);
    CHECK(strstr(b, "MemAvailable 1024 of 11264 MiB, swap in use 3072 of 8192 MiB (zram)") != NULL, "meminfo in the line");
    CHECK(strstr(b, "smaps_rollup rss 14 pss 9 swap 0 MiB") != NULL, "rollup in the line");
    char small[64]; vkrs_format(small, sizeof small, &s, roll, mi);   // a short buffer is cut, never overrun (ASan checks)
    CHECK(strlen(small) < sizeof small, "bounded");
    printf(fails ? "rsslog: %d failures\n" : "rsslog passed\n", fails);
    return fails != 0;
}
