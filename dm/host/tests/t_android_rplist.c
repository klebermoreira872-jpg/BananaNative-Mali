// The classic render passes' list (dm/gfx/vk_android/vka_rplist.h): passes and pipelines of one shape get separate objects, so a render pass given to a pipeline create
// the driver refused is never one a pass begins; a refused pipeline object is retired for later pipelines of its shape, a pass object (DM_VK_RP_SHARED=1) only counted.
#include <stdio.h>
#include <string.h>
#include "../../gfx/vk_android/vka_rplist.h"

static int fails;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

typedef struct { uint32_t cf[8], n, ds, d, s, samples, clear; } key;   // the shape of vka_draw.c's rpkey
static uint64_t next = 0x1000;
// rp_obtain's lookup: the live object of the shape and use, else a new one
static uint64_t obtain(vkrl *l, const key *k, int use) {
    uint64_t r = vkrl_find(l, use, k, sizeof *k);
    if (r) return r;
    r = next++; CHECK(vkrl_add(l, use, k, sizeof *k, r), "kept");
    return r;
}

int main(void) {
    vkrl l; memset(&l, 0, sizeof l);
    key a; memset(&a, 0, sizeof a); a.n = 1; a.cf[0] = 37; a.samples = 1;   // one RGBA8 target
    key b = a; b.ds = 126; b.d = 1;                                         // and a depth target

    // one object per shape and use, kept: the same shape asks again and gets the same one
    uint64_t pass_a = obtain(&l, &a, VKRL_PASS), pipe_a = obtain(&l, &a, VKRL_PIPE);
    CHECK(pass_a && pipe_a && pass_a != pipe_a, "pass %#llx and pipeline %#llx objects differ", (unsigned long long)pass_a, (unsigned long long)pipe_a);
    CHECK(obtain(&l, &a, VKRL_PASS) == pass_a && obtain(&l, &a, VKRL_PIPE) == pipe_a, "kept per shape and use");
    uint64_t pass_b = obtain(&l, &b, VKRL_PASS), pipe_b = obtain(&l, &b, VKRL_PIPE);
    CHECK(pass_b != pass_a && pipe_b != pipe_a && pass_b != pipe_b, "another shape, other objects");
    CHECK(l.n == 4, "%d objects", l.n);

    // the driver refuses a pipeline made against the pipeline object of shape a: logged once, retired; the next pipeline of shape a gets a new object, passes keep theirs
    CHECK(vkrl_refused(&l, pipe_a) == 1, "first refusal against it said");
    CHECK(vkrl_refused(&l, pipe_a) == 0, "second refusal against the same object not said again");
    uint64_t pipe_a2 = obtain(&l, &a, VKRL_PIPE);
    CHECK(pipe_a2 && pipe_a2 != pipe_a && pipe_a2 != pass_a, "a new pipeline object (%#llx)", (unsigned long long)pipe_a2);
    CHECK(obtain(&l, &a, VKRL_PASS) == pass_a, "the pass object is unchanged");
    CHECK(obtain(&l, &b, VKRL_PIPE) == pipe_b, "another shape's pipeline object is unchanged");
    CHECK(vkrl_of(&l, pipe_a) && vkrl_of(&l, pipe_a)->retired && vkrl_of(&l, pipe_a)->refused == 2, "the old object stays listed, retired, with its refusals");
    CHECK(l.refused == 2 && l.retired == 1, "run counts: %u refused, %u retired", l.refused, l.retired);

    // with DM_VK_RP_SHARED=1 pipelines take the pass object: a refusal against it is counted and said, but the object passes begin stays
    CHECK(vkrl_refused(&l, pass_b) == 1, "a refusal against a pass object is said");
    CHECK(obtain(&l, &b, VKRL_PASS) == pass_b && !vkrl_of(&l, pass_b)->retired, "a pass object is not retired");
    CHECK(l.retired == 1, "still one retired");

    // a handle the list does not know (dynamic rendering: VK_NULL_HANDLE; or another list): counted, nothing retired, nothing said
    CHECK(vkrl_refused(&l, 0) == 0 && vkrl_refused(&l, 0xdead) == 0, "unknown handles");
    CHECK(l.retired == 1 && l.refused == 5, "counts after unknown handles: %u retired, %u refused", l.retired, l.refused);

    // the list grows past its first capacity and keeps finding every shape
    key many[300]; uint64_t got[300];
    for (int i = 0; i < 300; i++) { many[i] = a; many[i].cf[0] = 1000 + (uint32_t)i; got[i] = obtain(&l, &many[i], VKRL_PIPE); }
    int same = 1; for (int i = 0; i < 300; i++) if (vkrl_find(&l, VKRL_PIPE, &many[i], sizeof many[i]) != got[i]) same = 0;
    CHECK(same, "found after growth");
    CHECK(!vkrl_find(&l, VKRL_PASS, &many[7], sizeof many[7]), "a use with no object yet");

    // keys longer than the list's: never kept, never found (the caller still uses the object it made)
    uint8_t big[VKRL_KEYMAX + 8]; memset(big, 1, sizeof big);
    CHECK(!vkrl_add(&l, VKRL_PIPE, big, sizeof big, 0x77) && !vkrl_find(&l, VKRL_PIPE, big, sizeof big), "a key too long");
    CHECK(!vkrl_add(&l, VKRL_PIPE, &a, sizeof a, 0), "no null handle kept");

    free(l.e);
    if (fails) { printf("t_android_rplist: %d failures\n", fails); return 1; }
    printf("t_android_rplist: ok\n");
    return 0;
}
