// Where in a submission the GPU stopped (Android; used by vka_exec.c vka_exec_hang_parts, checked by dm/host/tests/t_android_hangparts.c).
// A submission goes to the queue in parts (vka_exec.c chunk), and each part writes a top and a bottom timestamp. After a hang that left the device usable (no
// VK_ERROR_DEVICE_LOST yet) the queries tell which of them the GPU wrote: the first part whose bottom is missing is where it stopped. With each part's draw range
// that names the draws, and the pipeline or shader of the last of them can be looked for in the replay log. Pure functions: no Vulkan, so they run on the Mac.
#ifndef VKA_HANGPARTS_H
#define VKA_HANGPARTS_H
#include <stdint.h>
#include <stdio.h>

enum { VKHP_MAX = 33 };
typedef struct {
    uint32_t np;                  // parts handed to the queue, plus the one being recorded when the hang came
    uint8_t top[VKHP_MAX];        // 1: the part's top timestamp was written (the GPU started it)
    uint8_t bottom[VKHP_MAX];     // 1: its bottom timestamp was written (the GPU finished it)
    uint32_t draws[VKHP_MAX];     // draws recorded in the part
} vkhp_in;

// The first part that started and did not finish (the one the GPU is in), or -1 when every started part finished (the stop is between parts: a wait, or a part the
// GPU never started), or -2 when no part started at all
static inline int vkhp_stuck(const vkhp_in *p) {
    int started = 0;
    for (uint32_t i = 0; i < p->np && i < VKHP_MAX; i++) {
        if (p->top[i]) started = 1;
        if (p->top[i] && !p->bottom[i]) return (int)i;
    }
    return started ? -1 : -2;
}
// One line for the log: "part 7 of 12 started and did not finish (draws 3400-3699 of the submission; 6 parts finished, 5 not started)"
static inline void vkhp_describe(const vkhp_in *p, char *out, size_t n) {
    int s = vkhp_stuck(p);
    uint32_t done = 0, idle = 0;
    for (uint32_t i = 0; i < p->np && i < VKHP_MAX; i++) { if (p->bottom[i]) done++; if (!p->top[i]) idle++; }
    if (s >= 0) {
        uint64_t d0 = 0; for (int i = 0; i < s; i++) d0 += p->draws[i];
        snprintf(out, n, "part %d of %u started and did not finish (draws %llu-%llu of the submission; %u parts finished, %u not started)", s + 1, p->np,
                 (unsigned long long)d0, (unsigned long long)(d0 + (p->draws[s] ? p->draws[s] - 1 : 0)), done, idle);
    } else if (s == -1) snprintf(out, n, "every part that started finished (%u of %u; %u not started): the GPU stopped between parts", done, p->np, idle);
    else snprintf(out, n, "no part started (%u parts handed to the queue): the GPU never reached this submission", p->np);
}
#endif
