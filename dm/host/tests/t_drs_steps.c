// Donkey Kong Bananza's dynamic resolution range fitted to the game's rate steps and cap (drs_steps.h, probe.c drs_fit; issue #269). drs_steps_snap models the game's
// round-down (main+0x38dea0 to 0x38df0c) and its step down's limit (main+0x38e0f0) from the disassembly, to show what each launcher choice gives with and without the fit.
#include "../drs_steps.h"
#include <stdio.h>
#include <stdlib.h>

static int fails;
#define CHECK(c, what) do { if (!(c)) { printf("FAIL t_drs_steps: %s\n", what); fails++; } } while (0)

static float size_off(float rate, int pct) { return fabsf(1.0f / rate - (float)pct / 100.0f); }   // how far a rate's size is from the size chosen

int main(void) {
    // Ingot Isle Cave-In: nine steps and a cap of 3.0, read from the running game (2026-11-16; the log prints three decimals, so 5/3, 12/7 and 11/6 stand for 1.667, 1.714, 1.833)
    static const float sl10[9] = {1.0f, 1.375f, 1.5f, 5.0f / 3.0f, 12.0f / 7.0f, 11.0f / 6.0f, 2.0f, 2.2f, 3.0f};
    const float cap = 3.0f;
    CHECK(drs_steps_ok(sl10, 9), "the measured table is accepted");

    // The launcher's choices (Prefs.DRS: min % of 80 down to 30, max always 100): the max rate 100 / min % without the fit and with it
    static const struct { int pct; float fit; } want[] = {{80, 1.375f}, {70, 1.375f}, {60, 5.0f / 3.0f}, {50, 2.0f}, {40, 2.2f}, {30, 3.0f}};
    for (unsigned i = 0; i < sizeof want / sizeof *want; i++) {
        char what[96]; float raw = 100.0f / (float)want[i].pct, fit = drs_steps_nearest(sl10, 9, raw);
        snprintf(what, sizeof what, "%d %%: the nearest step, also under the measured cap", want[i].pct); CHECK(fit == want[i].fit && drs_steps_fit(sl10, 9, cap, raw) == want[i].fit, what);
        snprintf(what, sizeof what, "%d %%: the game keeps the fitted max", want[i].pct); CHECK(drs_steps_snap(sl10, 9, cap, fit) == fit, what);
        snprintf(what, sizeof what, "%d %%: the step down can reach it", want[i].pct); CHECK(drs_steps_snap(sl10, 9, INFINITY, fit) == fit, what);
    }
    CHECK(drs_steps_nearest(sl10, 9, 1.0f) == 1.0f, "the full size end stays at 1.0");
    // #269: without the fit, 80 % (rate 1.25) is rounded to the full size, and the step down never picks a smaller one
    CHECK(drs_steps_snap(sl10, 9, cap, 1.25f) == 1.0f, "80 % without the fit: rounded to the full size");
    CHECK(drs_steps_snap(sl10, 9, INFINITY, 1.25f) == 1.0f, "80 % without the fit: the step down stops at the full size");
    // Every step stays itself
    for (unsigned i = 0; i < 9; i++) CHECK(drs_steps_nearest(sl10, 9, sl10[i]) == sl10[i], "a range end on a step stays there");
    // Any whole percent from 10 to 100: the fit is a step the game keeps, and never further from the size chosen than what the round-down gave
    for (int pct = 10; pct <= 100; pct++) {
        float raw = 100.0f / (float)pct, fit = drs_steps_nearest(sl10, 9, raw), was = drs_steps_snap(sl10, 9, cap, raw);
        char what[96]; snprintf(what, sizeof what, "%d %%: the fit is kept and no further than the round-down", pct);
        CHECK(drs_steps_snap(sl10, 9, cap, fit) == fit && size_off(fit, pct) <= size_off(was, pct) + 1e-6f, what);
    }
    // A step a hair above 100 / 60 (if the game holds 1.667 as written): without the fit 60 % falls to 1.5 (66.7 %), with it it takes that step
    { float e[9]; for (int i = 0; i < 9; i++) e[i] = sl10[i]; e[3] = 1.667f;
      CHECK(drs_steps_snap(e, 9, cap, 100.0f / 60.0f) == 1.5f, "60 % below a 1.667 step: the round-down gives 1.5");
      CHECK(drs_steps_nearest(e, 9, 100.0f / 60.0f) == 1.667f, "60 % below a 1.667 step: the fit takes it"); }
    // The game's cap [S+8] comes first: a cap below the nearest step gives the step at or below the cap
    CHECK(drs_steps_fit(sl10, 9, cap, 1.25f) == 1.375f, "80 % under the measured cap 3.0: 1.375");
    CHECK(drs_steps_fit(sl10, 9, 1.2f, 1.25f) == 1.0f, "80 % under a cap of 1.2: the full size, as the game will hold it");
    CHECK(drs_steps_fit(sl10, 9, 1.5f, 2.5f) == 1.5f, "40 % under a cap of 1.5: 1.5");
    CHECK(drs_steps_fit(sl10, 9, 1.6f, 2.5f) == 1.5f, "40 % under a cap of 1.6, between two steps: the step below it");
    CHECK(drs_steps_fit(sl10, 9, INFINITY, 2.5f) == 2.2f, "no cap: the nearest step");
    CHECK(drs_steps_fit(sl10, 9, NAN, 2.5f) == 1.0f, "a NaN cap: the first step, as the game's fcsel takes it");
    CHECK(drs_steps_fit(sl10, 9, 0.0f, 2.5f) == 1.0f, "a cap of 0: the first step");
    { const float hiFirst[2] = {1.375f, 1.5f}; CHECK(drs_steps_snap(hiFirst, 2, 3.0f, 1.0f) == 1.375f, "the round-down never goes below the first step's index"); }
    { const float nan1[3] = {1.0f, NAN, 1.5f}; CHECK(drs_steps_snap(nan1, 3, 3.0f, 2.0f) == 1.0f, "the round-down stops at a NaN step"); }
    // The tables drs_fit trusts
    { const float one[1] = {1.0f}; CHECK(drs_steps_ok(one, 1) && drs_steps_nearest(one, 1, 2.5f) == 1.0f, "one step"); }
    CHECK(!drs_steps_ok(sl10, 0), "no steps");
    { float e[10]; for (int i = 0; i < 10; i++) e[i] = 1.0f + (float)i * 0.25f; CHECK(!drs_steps_ok(e, 10), "ten steps"); }
    static const float bad[][3] = {{1.0f, NAN, 2.0f}, {1.0f, INFINITY, 2.0f}, {0.0f, 1.0f, 2.0f}, {-1.0f, 1.0f, 2.0f}, {0.4f, 1.0f, 2.0f}, {1.0f, 2.0f, 17.0f},
                                   {1.0f, 1.5f, 1.5f}, {1.0f, 2.0f, 1.5f}};
    for (unsigned i = 0; i < sizeof bad / sizeof *bad; i++) CHECK(!drs_steps_ok(bad[i], 3), "a NaN, infinite, out of range, repeated or falling step is refused");

    if (fails) return 1;
    printf("t_drs_steps: OK\n");
    return 0;
}
