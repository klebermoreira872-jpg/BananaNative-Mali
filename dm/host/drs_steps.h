// SPDX-License-Identifier: GPL-3.0-or-later
// A dynamic resolution range fitted to the sizes a game's controller can render at (probe.c drs_fit; Donkey Kong Bananza's drs_ctl rows). Header only, pure: no guest memory,
// so dm/host/tests/t_drs_steps.c builds it as it is.
//
// The controller keeps its render size as a rate, the upscaler's target over the render size on each side (1.0 the full size, 2.0 half), and only ever stores one of its own
// steps, up to 9 rising rates: it rounds every rate down to the step below it. A range end between two steps therefore acts as the step below it, and the launcher's 80 %
// (rate 1.25), with no step between 1.0 and 1.375, never left the full size (#269). drs_steps_fit gives the step whose size is nearest the size chosen instead, as the
// game will hold it under its own cap.
#pragma once
#include <math.h>
#include <stdint.h>

// A table to fit to: 1 to 9 finite rates from 0.5 to 16, strictly rising (the game's round-down keeps such a step as it is)
static inline int drs_steps_ok(const float *e, uint32_t n) {
    if (n < 1 || n > 9) return 0;
    for (uint32_t i = 0; i < n; i++)
        if (!(e[i] >= 0.5f && e[i] <= 16.0f) || (i && !(e[i] > e[i - 1]))) return 0;
    return 1;
}

// The step whose size (1 / rate) is nearest the size of rate r (r > 0; a table drs_steps_ok accepts); a tie goes to the larger size. The result is the table's own value
static inline float drs_steps_nearest(const float *e, uint32_t n, float r) {
    float best = e[0], bd = fabsf(1.0f / e[0] - 1.0f / r);
    for (uint32_t i = 1; i < n; i++) { float d = fabsf(1.0f / e[i] - 1.0f / r); if (d < bd) { bd = d; best = e[i]; } }
    return best;
}

// The game's round-down (main+0x38deb0 to 0x38df08) of rate x under its cap: the first step whose next one is above min(cap, x), as the instructions take it (fcsel gt:
// a NaN cap gives the cap; b.ls: a NaN ends the run). With an infinite cap it is also what the step down (main+0x38e0f0) returns at a step above the max rate x
static inline float drs_steps_snap(const float *e, uint32_t n, float cap, float x) {
    float v = cap > x ? x : cap;
    uint32_t i = 0; while (i + 1 < n && e[i + 1] <= v) i++;
    return e[i];
}

// What a range end of rate r becomes: the nearest step, as the game rounds it under its cap (a cap below that step gives the step at or below the cap)
static inline float drs_steps_fit(const float *e, uint32_t n, float cap, float r) { return drs_steps_snap(e, n, cap, drs_steps_nearest(e, n, r)); }
