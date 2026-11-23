// SPDX-License-Identifier: MIT
// Mario Tennis Fever (Switch 2), nro0 of 1.1.1 (build ID 250a510a934129cb38e930c9a29082b6): full game speed at low frame rates, by the game's own draw flag.
//
// The engine counts frames: game logic calls WaitFrame (nro0+0x11fa2e0), which runs the frame function (nro0+0x11f82a0) once a step, and game time is one 1/60 s step a frame.
// The present interval is the game's own, min(frames since the last present, 5) (nro0+0x11f9850..0x11f986c, the counter framework+0x5cb8), so a frame that is not presented still
// counts and the next present is held for as many vsyncs; with presentation following the game's interval (the profile's default, DM_PRESENT_INTERVAL=game) game time stays equal
// to vsync time across frames that are not shown. A frame over 16.7 ms shown at interval 1 plays at half speed (Forgejo #302, #307).
//
// The game has a "draw this frame" byte for that (nro0+0x17999bc, GOT nro0+0x1760c20): read in the frame function before the job lists' dispatch (0x11f8638, 0x11f8720), before the
// submit and fence (0x11f9330: nvnQueueSubmitCommands and FenceSync through 0x25440, where the host translates the frame) and the present (0x11f975c), and at 0x11f98f4 (the shown
// frames' buffer index). Every store of the game's writes 1, and the frame's end (0x11f75b0, which every caller of the frame function runs after it: 0x11f7664) writes 1 again, so
// the path with 0 never runs in the shipped game. The host writes 0 on a frame it skips: the step and the job recording still run, nothing is submitted or presented, and the
// counter keeps counting, so the next shown frame asks for interval 2.
//
// Two gates (patches.py OBS rows, kind OBS_MTF_SKIP, the parameter which one): FRAME at nro0+0x11f8624 (`ldr x21,[x21,#0xc20]`, the flag's GOT load before its first read, reached
// by every call of the frame function) decides for the frame; SUBMIT at nro0+0x11f932c (`ldr x8,[x8,#0xc20]`, the GOT load before the submit's read) writes the 0. So the job
// lists are dispatched and waited for as on every frame, and only the submit, the present and what follows them are left out. Writing 0 at FRAME instead (DM_MTF_SKIP_EARLY=1)
// would also leave out the jobs' dispatch (O->vtable+8 at 0x11f8660 / 0x11f8678 / 0x11f8744) while their wait (O->vtable+0x20 at 0x11f8764..0x11f878c) is still called; whether that
// wait returns for lists that were not dispatched is not known from the code (the job manager's vtable was not resolved), so it is a probe, not the default.
//
// A frame is skipped only when all of these hold (skip_pick): real time is at least one step ahead of the frames counted since the clock started; fewer than DM_MTF_SKIP_MAX
// (default 1: at least 30 frames a second shown) frames were skipped since the last shown one; more than SKIP_GRACE frames have run since the last load (a frame over 100 ms starts
// the clock again); and the frame's draw jobs are the last shown frame's (jobs_sig: the job table at nro0+0x3ea5160, its (function, object) pairs, and the callables it keeps at
// +0xe010), so a frame with a new job, such as the stage's atmosphere table filled once, is drawn. Real time more than SKIP_AHEAD_MAX steps ahead starts the clock again: the
// game slows down there and never runs ahead to catch up. Off with Full game speed at low frame rates (dm_fps_decouple_on: the launcher's setting, DM_FPS_DECOUPLE=0, the in-game
// panel live) and where presentation follows the host's tick (DM_PRESENT_INTERVAL=display: one frame a tick would make two steps a tick). Gate frame (entry.S dm_gate): x0..x30 at
// r[0..30]; the gates read no register and write only the flag byte.
#include "hle.h"
#include "dm.h"
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>

#define MTF_SPEED_BUILD "250a510a934129cb38e930c9a29082b6"
enum { M_FLAG = 0x17999bc, M_FLAG_GOT = 0x1760c20, M_JOBS = 0x3ea5160, M_JOBS_GOT = 0x1760c30 };   // nro0 offsets: the draw flag, the job table, and their GOT slots
enum { J_COUNT = 0xe000, J_FN = 0x1050, J_OBJ = 0x1058, J_STRIDE = 0x68, J_MAX = 0x1ff,            // the job table: count, then (function, object, ...) records of 0x68
       J_CALLS = 0xe010, C_STRIDE = 0x30, C_FUNCTOR = 0x20, C_MAX = 0x1000 };                     // its callables: a vector (begin, end) of 0x30 each, the functor's pointer at +0x20
enum { GATE_FRAME = 0, GATE_SUBMIT = 1 };   // the gate number's parameter (bits 8 up)

#define SKIP_STEP_NS 16666667ull       // one step of the game: 1/60 s
#define SKIP_LOAD_NS 100000000ull      // a frame longer than this is a load: the clock starts again, and the grace
#define SKIP_GRACE 120                 // frames after a load before any skip (a stage's one-shot passes)
#define SKIP_AHEAD_MAX 6               // real time more steps ahead than this: the clock starts again (no running ahead after a stall)
#define SKIP_STALL_NS 1000000000ull    // a frame after a skipped one that long counts as a stall the skip may have caused
#define SKIP_STRIKES 2                 // that many stalls: no more skips this session
#define SKIP_LOG_FRAMES 300            // the statistics line's window

int dm_fps_decouple_on(void);   // hle_fpslock.c: Full game speed at low frame rates (the launcher, DM_FPS_DECOUPLE, nxhost_fps_decouple_set)
int dm_fps_half_on(void);       // hle_fpslock.c: a 30 cap through flag 15 takes priority over the dynamic skip

typedef struct {
    uint64_t ref, last;   // the clock's start and the last frame's start (ns); last 0 = start again at the next frame
    uint32_t steps;       // frames since ref
    uint32_t calm;        // frames since the last load
    int run;              // frames skipped since the last shown one
    int have_sig;         // sig holds the last shown frame's job signature
    uint64_t sig;
    int skipped;          // the last frame was skipped
    int strikes, dead;    // stalls after a skipped frame; dead: no more skips this session
} skip_t;

// The decision for the frame that starts at now with job signature sig: 1 = skip its submit and present
static int skip_pick(skip_t *s, uint64_t now, uint64_t sig, int max_skip) {
    if (s->last && now - s->last > SKIP_LOAD_NS) {
        if (s->skipped && now - s->last >= SKIP_STALL_NS && ++s->strikes >= SKIP_STRIKES) s->dead = 1;
        s->last = 0;
    }
    if (!s->last) { s->ref = now; s->steps = 0; s->calm = 0; s->run = 0; s->have_sig = 0; }
    s->last = now;
    double ahead = (double)(now - s->ref) / (double)SKIP_STEP_NS - (double)s->steps;   // steps of real time not yet stepped, before this frame's
    s->steps++;
    if (s->calm < 0x7fffffff) s->calm++;
    if (ahead > SKIP_AHEAD_MAX) { s->ref = now; s->steps = 1; ahead = 0; }
    int skip = !s->dead && s->calm > SKIP_GRACE && ahead >= 1 && s->run < max_skip && s->have_sig && sig == s->sig;
    if (skip) s->run++;
    else { s->run = 0; s->sig = sig; s->have_sig = 1; }
    s->skipped = skip;
    return skip;
}

static uint64_t mix(uint64_t x) { x ^= x >> 33; x *= 0xff51afd7ed558ccdull; x ^= x >> 33; x *= 0xc4ceb9fe1a85ec53ull; x ^= x >> 33; return x; }
static uint64_t rd8(uintptr_t a) { uint64_t v; memcpy(&v, (const void *)a, 8); return v; }
// The frame's draw jobs: the job table's count and (function, object) pairs, and its callables' functor types (each functor's vtable), summed so the table's order does not matter
static uint64_t jobs_sig(uintptr_t t, uint32_t *njobs, uint32_t *ncalls) {
    uint32_t n; memcpy(&n, (const void *)(t + J_COUNT), 4);
    if (n > J_MAX) n = J_MAX;
    uint64_t h = mix(n + 1), sum = 0;
    for (uint32_t i = 0; i < n; i++) sum += mix(rd8(t + J_FN + i * J_STRIDE) ^ mix(rd8(t + J_OBJ + i * J_STRIDE)));
    uint64_t b = rd8(t + J_CALLS), e = rd8(t + J_CALLS + 8), nc = 0;
    if (b && !(b & 7) && e >= b && (e - b) % C_STRIDE == 0 && (e - b) / C_STRIDE <= C_MAX) nc = (e - b) / C_STRIDE;
    for (uint64_t i = 0; i < nc; i++) {
        uint64_t f = rd8((uintptr_t)(b + i * C_STRIDE + C_FUNCTOR));
        sum += mix((f && !(f & 7) ? rd8((uintptr_t)f) : 0) + 0x5bd1e995);
    }
    *njobs = n; *ncalls = (uint32_t)nc;
    return h ^ mix(nc + 0x1000) ^ sum;
}

static _Atomic int g_build_ok = -1;   // -1 not checked yet, 0 another build or layout (the gates do nothing), 1 nro0 1.1.1
static uintptr_t g_base;
static int build_ok(void) {
    int v = g_build_ok;
    if (v >= 0) return v;
    v = 0;
    for (int i = 0; i < g_nmod; i++) if (g_mod[i].nro && !strcmp(g_mod[i].name, "nro0") && !strcmp(g_mod[i].build_id, MTF_SPEED_BUILD)) g_base = (uintptr_t)g_mod[i].base;
    if (!g_base) LOG("[RED] mtf skip: the gate ran outside nro0 1.1.1 (%s); every frame is drawn", MTF_SPEED_BUILD);
    else if (rd8(g_base + M_FLAG_GOT) != g_base + M_FLAG || rd8(g_base + M_JOBS_GOT) != g_base + M_JOBS)   // the GOT holds the relocated addresses the frame function loads
        LOG("[RED] mtf skip: nro0's GOT does not point at the draw flag and the job table (%#llx, %#llx); every frame is drawn",
            (unsigned long long)(rd8(g_base + M_FLAG_GOT) - g_base), (unsigned long long)(rd8(g_base + M_JOBS_GOT) - g_base));
    else v = 1;
    g_build_ok = v;
    return v;
}

static void flag_write(uint8_t v) {
    uint8_t *p = (uint8_t *)(g_base + M_FLAG);
    dm_guest_write_prepare(p, 1);
    __atomic_store_n(p, v, __ATOMIC_RELAXED);
}

// The switches, read at the first frame
static int g_max = -1, g_early, g_test, g_log, g_display;
static void config(void) {
    const char *e = getenv("DM_MTF_SKIP_MAX"); g_max = e ? atoi(e) : 1;
    if (g_max < 1) g_max = 1;
    if (g_max > 2) g_max = 2;
    e = getenv("DM_MTF_SKIP_EARLY"); g_early = e && atoi(e) > 0;
    e = getenv("DM_MTF_SKIP_TEST"); g_test = e ? atoi(e) : 0;
    if (g_test < 0) g_test = 0;
    e = getenv("DM_MTF_SKIP_LOG"); g_log = e && atoi(e) > 0;
    e = getenv("DM_PRESENT_INTERVAL"); g_display = e ? !strcmp(e, "display") : DM_GAME_PRESENT_DISPLAY;
    LOG("mtf skip: frames behind real time skip their submit and present (up to %d a shown frame%s%s%s)", g_max, g_early ? "; DM_MTF_SKIP_EARLY: the job dispatch too" : "",
        g_test ? "; DM_MTF_SKIP_TEST: one frame in every n forced" : "", g_display ? "; off: DM_PRESENT_INTERVAL=display presents one frame a tick" : "");
}

static skip_t g_s;
static int g_apply;   // this frame is skipped: SUBMIT writes the 0
static struct { uint32_t frames, skipped; uint64_t start, prev, after_shown, after_skip; uint32_t n_shown, n_skip; int prev_skip; uint64_t sig; } g_st;

static void stats(uint64_t now, int skip, uint64_t sig, uint32_t nj, uint32_t nc) {
    if (g_log && sig != g_st.sig) {
        static int n;
        if (n++ < 4000) LOG("mtf skip: frame %u: %u jobs, %u callables, signature %016llx", g_s.steps, nj, nc, (unsigned long long)sig);
        g_st.sig = sig;
    }
    if (g_st.prev && now - g_st.prev <= SKIP_LOAD_NS) {   // the time from the last frame's start to this one's: its own cost and the step after it
        if (g_st.prev_skip) { g_st.after_skip += now - g_st.prev; g_st.n_skip++; } else { g_st.after_shown += now - g_st.prev; g_st.n_shown++; }
    }
    if (!g_st.start) g_st.start = now;
    g_st.prev = now; g_st.prev_skip = skip; g_st.frames++; g_st.skipped += (uint32_t)skip;
    if (g_st.frames < SKIP_LOG_FRAMES) return;
    double real = (double)(now - g_st.start) / 1e9, game = (g_st.frames - 1) / 60.0;
    LOG("mtf skip: %u frames, %u skipped (%.0f%%): game time %.2f s in %.2f s (%.3f of real time); %.1f ms after a shown frame, %.1f ms after a skipped one", g_st.frames, g_st.skipped,
        100.0 * g_st.skipped / g_st.frames, game, real, real > 0 ? game / real : 0, g_st.n_shown ? g_st.after_shown / 1e6 / g_st.n_shown : 0, g_st.n_skip ? g_st.after_skip / 1e6 / g_st.n_skip : 0);
    memset(&g_st, 0, sizeof g_st); g_st.start = g_st.prev = now; g_st.prev_skip = skip; g_st.sig = sig;
}

static void frame_gate(uint64_t now) {
    static int was_on = -1, nwarn;
    g_apply = 0;
    if (dm_fps_half_on()) {
        if (was_on > 0) { LOG("mtf skip: off (frame rate cap 30: flag 15 draws every other step)"); was_on = 0; }
        g_s.last = 0; memset(&g_st, 0, sizeof g_st);
        return;
    }
    if (__atomic_load_n((uint8_t *)(g_base + M_FLAG), __ATOMIC_RELAXED) == 0) {   // only the host writes 0, and the frame's end writes 1 again
        if (nwarn++ < 4) LOG("[RED] mtf skip: the draw flag was still 0 at a frame's start; written 1");
        flag_write(1);
    }
    if (g_test) {   // DM_MTF_SKIP_TEST=<n>: one frame in every n, whatever the clock (the probe of the skip path)
        static uint32_t k;
        g_apply = ++k % (uint32_t)g_test == 0;
        if (g_apply && g_early) flag_write(0);
        return;
    }
    int on = dm_fps_decouple_on() && !g_display;
    if (on != was_on) { if (was_on >= 0) LOG("mtf skip: %s (Full game speed at low frame rates)", on ? "on" : "off"); was_on = on; g_s.last = 0; memset(&g_st, 0, sizeof g_st); }
    if (!on || g_s.dead) return;
    uint32_t nj, nc;
    uint64_t sig = jobs_sig(g_base + M_JOBS, &nj, &nc);
    int strikes = g_s.strikes;
    uint64_t gap = g_s.last ? now - g_s.last : 0;
    int skip = skip_pick(&g_s, now, sig, g_max);
    if (g_s.strikes != strikes)
        LOG("[RED] mtf skip: the frame after a skipped one took %.0f ms%s", gap / 1e6, g_s.dead ? "; no more skips this session (a stall the skip may cause: the job lists' wait, the fence)" : "");
    stats(now, skip, sig, nj, nc);
    g_apply = skip;
    if (skip && g_early) flag_write(0);
}

static void mtf_skip_gate(uint64_t *r, int param) {
    (void)r;
    if (!build_ok()) return;
    if (g_max < 0) config();
    if (param == GATE_FRAME) frame_gate(now_ns());
    else if (param == GATE_SUBMIT) { if (g_apply && !g_early) flag_write(0); g_apply = 0; }
}

__attribute__((constructor)) static void mtf_skip_attach(void) { gate_obs_set(OBS_MTF_SKIP, mtf_skip_gate); }
