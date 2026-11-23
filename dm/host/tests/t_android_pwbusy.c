// Speculative compiles that did not finish (dm/gfx/vk_android/vka_pwbusy.h; vka_pso.c spec_begin / spec_end / unf_load): the busy and unfinished sets, their files'
// text, and a start after a run that ended during a compile (Pokopia, af8f64d9f5542ef2 on Qualcomm's compiler)
#include <stdio.h>
#include "../../gfx/vk_android/vka_pwbusy.h"

static int fails;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

static vkpb_set S(void) { vkpb_set s; memset(&s, 0, sizeof s); return s; }

int main(void) {
    // add, has, del
    vkpb_set s = S();
    CHECK(vkpb_add(&s, 0xaf8f64d9f5542ef2ull) == 1 && s.n == 1, "add");
    CHECK(vkpb_add(&s, 0xaf8f64d9f5542ef2ull) == 0 && s.n == 1, "a key twice is kept once");
    CHECK(vkpb_add(&s, 0) == 0 && s.n == 1, "key 0 is no key");
    CHECK(vkpb_add(&s, 0x87a4d043cdd3b963ull) == 1 && vkpb_add(&s, 0x6bef3d23a8ddeafdull) == 1 && s.n == 3, "three");
    CHECK(vkpb_del(&s, 0x87a4d043cdd3b963ull) == 1 && s.n == 2 && s.k[0] == 0xaf8f64d9f5542ef2ull && s.k[1] == 0x6bef3d23a8ddeafdull, "del keeps the order");
    CHECK(vkpb_del(&s, 0x87a4d043cdd3b963ull) == 0 && s.n == 2, "del of a key not there");
    CHECK(vkpb_has(&s, 0x6bef3d23a8ddeafdull) && !vkpb_has(&s, 0x87a4d043cdd3b963ull), "has");

    // full set
    vkpb_set f = S();
    for (int i = 1; i <= VKPB_MAX; i++) vkpb_add(&f, (uint64_t)i);
    CHECK(f.n == VKPB_MAX && vkpb_add(&f, 0xffffull) == 0 && f.n == VKPB_MAX, "a full set takes no more");

    // format and parse round trip
    char b[VKPB_MAX * 17 + 1];
    size_t n = vkpb_format(&s, b, sizeof b);
    CHECK(n == 34 && !strcmp(b, "af8f64d9f5542ef2\n6bef3d23a8ddeafd\n"), "format: %s", b);
    vkpb_set r = S();
    CHECK(vkpb_parse(&r, b, n) == 2 && r.n == 2 && r.k[0] == s.k[0] && r.k[1] == s.k[1], "parse back");
    vkpb_set e = S();
    CHECK(vkpb_format(&e, b, sizeof b) == 0 && b[0] == 0, "an empty set is an empty file");
    char small[20];
    CHECK(vkpb_format(&s, small, sizeof small) == 0 && small[0] == 0, "no room: nothing written");

    // damaged text: an empty line, a short line, a non-hex line, upper case, a truncated last line without its newline, no final newline on a whole key
    const char *t = "\nAF8F64D9F5542EF2\n12345\nzzzzzzzzzzzzzzzz\n00d2cc376b83dedc\n6bef3d23a8dd";
    vkpb_set d = S();
    CHECK(vkpb_parse(&d, t, strlen(t)) == 2 && d.k[0] == 0xaf8f64d9f5542ef2ull && d.k[1] == 0x00d2cc376b83dedcull, "damaged text: %d keys", d.n);
    const char *t2 = "5a542c6c2f5ad3ea";
    vkpb_set d2 = S();
    CHECK(vkpb_parse(&d2, t2, strlen(t2)) == 1 && d2.k[0] == 0x5a542c6c2f5ad3eaull, "a last key without its newline");

    // a start after a run that ended during af8f64d9's compile, with 6bef3d23 already unfinished from a run before
    vkpb_set busy = S(), unf = S();
    vkpb_add(&unf, 0x6bef3d23a8ddeafdull);
    vkpb_add(&busy, 0xaf8f64d9f5542ef2ull); vkpb_add(&busy, 0x6bef3d23a8ddeafdull);
    CHECK(vkpb_carry(&unf, &busy) == 1 && unf.n == 2 && vkpb_has(&unf, 0xaf8f64d9f5542ef2ull), "carry: the new one");
    // a later build of it finishes (a draw needed it): off the list
    CHECK(vkpb_del(&unf, 0xaf8f64d9f5542ef2ull) == 1 && unf.n == 1, "finished: off the list");

    if (fails) { printf("t_android_pwbusy: %d failed\n", fails); return 1; }
    printf("t_android_pwbusy: ok\n");
    return 0;
}
