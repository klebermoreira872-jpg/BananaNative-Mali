// Whether a driver's placed maps work at all (dm/gfx/vk_android/vka_placefail.h): the verdict comes at VKP_LIMIT failures in a row with no placement ever made, once; a
// success before it, or between failures, means the driver places and a failure is that pool's own. The skipped-work warning names the guest memory cause (vka_skipwarn.h).
#include <stdio.h>
#include <string.h>
#include "../../gfx/vk_android/vka_placefail.h"
#include "../../gfx/vk_android/vka_skipwarn.h"

static int fails;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

int main(void) {
    // every placement fails (a Mali-G77's PanVK: VK_ERROR_MEMORY_MAP_FAILED = -5): the verdict at the VKP_LIMIT-th, once
    vkplace p = {0}; int said = 0, at = 0;
    for (int i = 1; i <= 40; i++) if (vkplace_note(&p, 0, -5)) { said++; at = i; }
    CHECK(said == 1 && at == VKP_LIMIT, "verdict %d times, at %d", said, at);
    CHECK(p.fail == 40 && p.ok == 0 && p.result == -5 && p.declared, "counts: %u failed, %u made, result %d", p.fail, p.ok, p.result);

    // one pool at a busy address fails among others that work: never a verdict
    vkplace q = {0};
    for (int i = 0; i < 100; i++) CHECK(!vkplace_note(&q, i % 5 != 0, -5), "mixed outcomes say nothing (%d)", i);

    // a driver that placed once is not declared broken by the failures after (a pool of its own)
    vkplace r = {0}; vkplace_note(&r, 1, 0);
    for (int i = 0; i < 50; i++) CHECK(!vkplace_note(&r, 0, -5), "failures after a success say nothing (%d)", i);

    // failures that a success interrupts start counting again, and with a success made the verdict stays off
    vkplace s = {0};
    for (int i = 0; i < VKP_LIMIT - 1; i++) vkplace_note(&s, 0, -5);
    CHECK(!s.declared, "one short of the limit");
    vkplace_note(&s, 1, 0);
    CHECK(s.row == 0 && s.ok == 1, "a success clears the run");
    for (int i = 0; i < 20; i++) CHECK(!vkplace_note(&s, 0, -5), "no verdict after a success");

    // the failures that stay under the limit say nothing
    vkplace t = {0};
    for (int i = 0; i < VKP_LIMIT - 1; i++) CHECK(!vkplace_note(&t, 0, -5), "under the limit (%d)", i);

    // the skipped-work warning counts the memory the GPU cannot see, and names it first when it is the largest cause
    CHECK(!strcmp(vks_name[VKS_GUESTMEM], "guest memory the GPU cannot see"), "cause name '%s'", vks_name[VKS_GUESTMEM]);
    vkskip w = {0}; uint64_t dev[VKS_N] = {0}, work = 0, f = 1500;
    vkskip_step(&w, f, work, dev, 0, 5);
    for (int i = 0; i < 2; i++) { f += VKS_WINDOW; work += 1000; dev[VKS_GUESTMEM] += 4000; dev[VKS_SHADER] += 20; vkskip_step(&w, f, work, dev, 0, 5); }
    CHECK(w.fired && !strcmp(w.causes, "guest memory the GPU cannot see 4000, shaders refused 20"), "causes '%s'", w.causes);

    if (!fails) printf("t_android_placefail: ok\n");
    return fails ? 1 : 0;
}
