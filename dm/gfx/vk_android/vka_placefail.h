// Whether a driver's placed maps work at all (vka_mem.c place): a driver can advertise VK_EXT_map_memory_placed (readiness passes) and still fail every placed map, as
// PanVK builds do on a Mali-G77 (vkMapMemory2 returns VK_ERROR_MEMORY_MAP_FAILED, BananaNative #92, #20). Nothing is then placed, the GPU sees none of the game's memory
// and the picture stays black while the log repeats one line per pool. This counts the outcomes so the host can say it once: after VKP_LIMIT failures in a row with no
// placement ever made, the driver is declared not to place. Pure counters, free of Android and Vulkan so the Mac's unit test (dm/host/tests/t_android_placefail.c) can
// check them. A single failure (one pool at an address another mapping holds) says nothing, and one success clears the verdict for good: the driver places, a later failure is
// that pool's own.
#ifndef VKA_PLACEFAIL_H
#define VKA_PLACEFAIL_H
#include <stdint.h>

enum { VKP_LIMIT = 8 };
typedef struct { uint32_t ok, fail, row; int result; int declared; } vkplace;   // placements made, failed; failures since the last success; the last failure's VkResult; verdict given

// One placement's outcome (ok: 1 made, 0 failed, with the driver's VkResult). Returns 1 once, at the failure that makes VKP_LIMIT in a row with none ever made
static inline int vkplace_note(vkplace *p, int ok, int result) {
    if (ok) { p->ok++; p->row = 0; return 0; }
    p->fail++; p->row++; p->result = result;
    if (!p->ok && !p->declared && p->row >= VKP_LIMIT) { p->declared = 1; return 1; }
    return 0;
}
#endif
