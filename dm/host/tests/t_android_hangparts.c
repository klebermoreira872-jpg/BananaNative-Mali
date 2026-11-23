// Where in a submission the GPU stopped (dm/gfx/vk_android/vka_hangparts.h): the part that started and did not finish, the draws it held, and the other outcomes
#include <stdio.h>
#include <string.h>
#include "../../gfx/vk_android/vka_hangparts.h"

static int fails;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

int main(void) {
    char b[200];
    vkhp_in p; memset(&p, 0, sizeof p);
    p.np = 5; for (int i = 0; i < 5; i++) p.draws[i] = 100;
    // parts 1-2 finished, part 3 started only, parts 4-5 not started
    p.top[0] = p.top[1] = p.top[2] = 1; p.bottom[0] = p.bottom[1] = 1;
    CHECK(vkhp_stuck(&p) == 2, "stuck %d", vkhp_stuck(&p));
    vkhp_describe(&p, b, sizeof b);
    CHECK(strstr(b, "part 3 of 5 started and did not finish") && strstr(b, "draws 200-299") && strstr(b, "2 parts finished, 2 not started"), "%s", b);
    // part 3's top is written while part 2 still runs (a top may precede the previous bottom): the first unfinished part is the one reported
    memset(&p.top, 0, sizeof p.top); memset(&p.bottom, 0, sizeof p.bottom);
    p.top[0] = p.top[1] = p.top[2] = 1; p.bottom[0] = 1;
    CHECK(vkhp_stuck(&p) == 1, "stuck %d", vkhp_stuck(&p));
    // all started parts finished: between parts
    memset(&p.top, 0, sizeof p.top); memset(&p.bottom, 0, sizeof p.bottom);
    p.top[0] = p.top[1] = 1; p.bottom[0] = p.bottom[1] = 1;
    CHECK(vkhp_stuck(&p) == -1, "between %d", vkhp_stuck(&p));
    vkhp_describe(&p, b, sizeof b); CHECK(strstr(b, "between parts"), "%s", b);
    // nothing started
    memset(&p.top, 0, sizeof p.top); memset(&p.bottom, 0, sizeof p.bottom);
    CHECK(vkhp_stuck(&p) == -2, "none %d", vkhp_stuck(&p));
    vkhp_describe(&p, b, sizeof b); CHECK(strstr(b, "never reached"), "%s", b);
    // a part without draws, the last part, and more parts than the table: no overrun
    memset(&p, 0, sizeof p); p.np = 99; p.top[0] = 1; p.draws[0] = 0;
    CHECK(vkhp_stuck(&p) == 0, "stuck %d", vkhp_stuck(&p));
    vkhp_describe(&p, b, sizeof b); CHECK(strstr(b, "draws 0-0"), "%s", b);
    if (!fails) printf("t_android_hangparts: ok\n");
    return fails != 0;
}
