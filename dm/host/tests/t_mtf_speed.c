// Mario Tennis Fever frame skip (android/mtf_speed.c): the skip decision (skip_pick) on a synthetic clock — nothing in the grace after a load, at most DM_MTF_SKIP_MAX skips a
// shown frame, none at 60 fps, none for a frame whose jobs differ from the last shown frame's, a slow frame starts again, two stalls after skipped frames end it, and game time
// keeps up with real time when frames are late; the job signature (order-free, a new job or callable changes it); and the gates on a sparse copy of nro0's layout: another build,
// a GOT that does not match, the setting off and display presentation write nothing; the SUBMIT gate writes the 0 (DM_MTF_SKIP_EARLY: the FRAME gate); DM_MTF_SKIP_TEST forces
// one frame in n. Every gate case runs in its own process (the build and the switches are read once).
#include "../android/mtf_speed.c"
#include <assert.h>
#include <stdio.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>

static module_t test_modules[2];
module_t *g_mod = test_modules;
int g_nmod;
static void (*callbacks[OBS_MAX])(uint64_t *, int);
void gate_obs_set(int id, void (*fn)(uint64_t *, int)) { assert(id > 0 && id < OBS_MAX); callbacks[id] = fn; }
static uint64_t g_now;
uint64_t now_ns(void) { return g_now; }
static int g_on = 1, g_half;
int dm_fps_decouple_on(void) { return g_on; }
int dm_fps_half_on(void) { return g_half; }
static int g_writes;
void dm_guest_write_prepare(void *p, size_t n) { (void)p; assert(n == 1); g_writes++; }

#define MS 1000000ull

// ---- skip_pick ----
// n frames with the given cost (ns; a skipped frame costs skip_cost), the signature sig; returns the skips, the longest run, and the game time / real time after the first frame
static int frames(skip_t *s, int n, uint64_t cost, uint64_t skip_cost, uint64_t sig, int max_skip, int *longest, double *ratio) {
    int skips = 0, run = 0; uint64_t t0 = g_now; uint32_t steps = 0;
    if (longest) *longest = 0;
    for (int i = 0; i < n; i++) {
        int k = skip_pick(s, g_now, sig, max_skip);
        skips += k; run = k ? run + 1 : 0; steps++;
        if (longest && run > *longest) *longest = run;
        g_now += k ? skip_cost : cost;
    }
    if (ratio) *ratio = (steps * (double)SKIP_STEP_NS) / (double)(g_now - t0);
    return skips;
}

static void pick_cases(void) {
    skip_t s; int longest; double ratio;
    g_now = 1000 * MS;
    // 60 fps: never behind, never a skip
    memset(&s, 0, sizeof s);
    assert(frames(&s, 600, SKIP_STEP_NS, SKIP_STEP_NS, 7, 1, NULL, &ratio) == 0);
    // late frames (25 ms shown, 3 ms skipped): nothing in the grace, then about every other frame skipped, never two in a row, game time = real time
    memset(&s, 0, sizeof s);
    assert(frames(&s, SKIP_GRACE, 25 * MS, 3 * MS, 7, 1, NULL, NULL) == 0);
    int k = frames(&s, 600, 25 * MS, 3 * MS, 7, 1, &longest, &ratio);
    assert(k > 100 && k < 400 && longest == 1);
    assert(ratio > 0.97 && ratio < 1.03);
    // without the skip that is 0.67 of real time
    // 40 ms shown frames with two skips allowed: runs of two, still at full speed (3 steps in 40 + 2 x 3 ms)
    memset(&s, 0, sizeof s);
    frames(&s, SKIP_GRACE + 1, 40 * MS, 3 * MS, 7, 2, NULL, NULL);
    k = frames(&s, 600, 40 * MS, 3 * MS, 7, 2, &longest, &ratio);
    assert(longest == 2 && ratio > 0.97 && ratio < 1.03);
    // ... and with one: the cap holds at one, the game slows to 2 steps in 43 ms and the clock starts again past SKIP_AHEAD_MAX (no catching up)
    memset(&s, 0, sizeof s);
    frames(&s, SKIP_GRACE + 1, 40 * MS, 3 * MS, 7, 1, NULL, NULL);
    k = frames(&s, 600, 40 * MS, 3 * MS, 7, 1, &longest, &ratio);
    assert(longest == 1 && ratio > 0.70 && ratio < 0.85);
    // a frame whose jobs differ from the last shown one's is drawn, and its jobs are the new reference
    memset(&s, 0, sizeof s);
    frames(&s, SKIP_GRACE + 1, 25 * MS, 3 * MS, 7, 1, NULL, NULL);
    g_now += 60 * MS;   // well behind, but not a load (the gap stays under SKIP_LOAD_NS)
    assert(skip_pick(&s, g_now, 7, 1) == 1 || skip_pick(&s, g_now += 3 * MS, 7, 1) == 1);   // one of the next two frames is skipped
    while (s.run) skip_pick(&s, g_now += 25 * MS, 7, 1);   // to a shown frame
    assert(skip_pick(&s, g_now += 25 * MS, 8, 1) == 0);    // new jobs: drawn
    assert(s.sig == 8);
    assert(skip_pick(&s, g_now += 25 * MS, 8, 1) == 1);    // the same jobs again, still behind: skipped
    assert(skip_pick(&s, g_now += 3 * MS, 9, 1) == 0 && s.run == 0);
    // a slow frame (a load) starts the clock and the grace again
    assert(frames(&s, 200, 25 * MS, 3 * MS, 9, 1, NULL, NULL) > 0);
    g_now += SKIP_LOAD_NS + MS;
    assert(frames(&s, SKIP_GRACE, 25 * MS, 3 * MS, 9, 1, NULL, NULL) == 0);
    assert(frames(&s, 60, 25 * MS, 3 * MS, 9, 1, NULL, NULL) > 0);
    // a stall right after a skipped frame counts; the second one ends the skips for the session. A long frame after a shown one does not count
    while (!s.skipped) skip_pick(&s, g_now += 25 * MS, 9, 1);
    g_now += SKIP_STALL_NS + MS; skip_pick(&s, g_now, 9, 1);
    assert(s.strikes == 1 && !s.dead);
    while (s.skipped || s.calm <= SKIP_GRACE) skip_pick(&s, g_now += s.skipped ? 3 * MS : 25 * MS, 9, 1);
    g_now += SKIP_STALL_NS + MS; skip_pick(&s, g_now, 9, 1);   // after a shown frame
    assert(s.strikes == 1);
    while (!s.skipped) skip_pick(&s, g_now += 25 * MS, 9, 1);
    g_now += SKIP_STALL_NS + MS; skip_pick(&s, g_now, 9, 1);
    assert(s.strikes == 2 && s.dead);
    assert(frames(&s, 600, 25 * MS, 3 * MS, 9, 1, NULL, NULL) == 0);
}

// ---- nro0's layout, sparse ----
static uint8_t *g_img;
static void put8(uint64_t off, uint64_t v) { memcpy(g_img + off, &v, 8); }
static void job(int i, uint64_t fn, uint64_t obj) { put8(M_JOBS + J_FN + i * J_STRIDE, fn); put8(M_JOBS + J_OBJ + i * J_STRIDE, obj); }
static void jobs(uint32_t n) { memcpy(g_img + M_JOBS + J_COUNT, &n, 4); }

static void setup(const char *build, int got_ok) {
    size_t len = M_JOBS + 0x10000;
    g_img = mmap(NULL, len, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
    assert(g_img != MAP_FAILED);
    g_nmod = 2;
    strcpy(g_mod[0].name, "main"); strcpy(g_mod[0].build_id, "104bce6874603701935eb76cb7d8b59e");
    strcpy(g_mod[1].name, "nro0"); g_mod[1].nro = 1; strcpy(g_mod[1].build_id, build); g_mod[1].base = g_img; g_mod[1].size = len;
    put8(M_FLAG_GOT, (uint64_t)(uintptr_t)g_img + M_FLAG + (got_ok ? 0 : 8)); put8(M_JOBS_GOT, (uint64_t)(uintptr_t)g_img + M_JOBS);
    g_img[M_FLAG] = 1;
    job(0, 0x91000, 0x5000000); job(1, 0x92000, 0x5000100); jobs(2);
    setenv("DM_PRESENT_INTERVAL", "game", 1);
    g_now = 1000 * MS;
}

static void sig_cases(void) {
    setup(MTF_SPEED_BUILD, 1);
    uint32_t nj, nc;
    uint64_t a = jobs_sig((uintptr_t)g_img + M_JOBS, &nj, &nc);
    assert(nj == 2 && nc == 0);
    job(0, 0x92000, 0x5000100); job(1, 0x91000, 0x5000000);   // the same jobs in another order
    assert(jobs_sig((uintptr_t)g_img + M_JOBS, &nj, &nc) == a);
    job(2, 0x93000, 0x5000200); jobs(3);   // one more (a stage's one-shot pass)
    uint64_t b = jobs_sig((uintptr_t)g_img + M_JOBS, &nj, &nc);
    assert(nj == 3 && b != a);
    job(2, 0x93000, 0x5000300);   // the same function on another object
    assert(jobs_sig((uintptr_t)g_img + M_JOBS, &nj, &nc) != b);
    jobs(2);
    // one callable (a functor held inline: its pointer at +0x20 points at the element, whose first word is the functor's vtable)
    uint64_t v = (uint64_t)(uintptr_t)g_img + 0x100000, el = v + 0x100;
    put8(0x100000 + 0x100, 0x777000); put8(0x100000 + 0x100 + C_FUNCTOR, el);
    put8(M_JOBS + J_CALLS, el); put8(M_JOBS + J_CALLS + 8, el + C_STRIDE);
    assert(jobs_sig((uintptr_t)g_img + M_JOBS, &nj, &nc) != a && nc == 1);
    put8(M_JOBS + J_CALLS + 8, el + 1);   // not a whole element: not read
    assert(jobs_sig((uintptr_t)g_img + M_JOBS, &nj, &nc) == a && nc == 0);
    jobs(0x7fffffff);   // a count past the table: clamped to it
    jobs_sig((uintptr_t)g_img + M_JOBS, &nj, &nc);
    assert(nj == J_MAX);
}

// One frame through both gates: whether the flag was 0 at the submit's read; the cost to the next frame (ns)
static int frame(uint64_t cost) {
    uint64_t r[32] = {0};
    callbacks[OBS_MTF_SKIP](r, GATE_FRAME);
    int early0 = g_img[M_FLAG] == 0;
    callbacks[OBS_MTF_SKIP](r, GATE_SUBMIT);
    int skipped = g_img[M_FLAG] == 0;
    assert(!early0 || skipped);
    g_img[M_FLAG] = 1;   // the frame's end (0x11f75b0)
    g_now += skipped ? 3 * MS : cost;
    return skipped;
}
static int run(int n, uint64_t cost) { int k = 0; for (int i = 0; i < n; i++) k += frame(cost); return k; }

static void gate_late(void) {   // the default: the FRAME gate leaves the flag alone, the SUBMIT gate writes the 0
    setup(MTF_SPEED_BUILD, 1);
    uint64_t r[32] = {0};
    assert(run(SKIP_GRACE, 25 * MS) == 0);
    int k = 0;
    for (int i = 0; i < 300; i++) {
        callbacks[OBS_MTF_SKIP](r, GATE_FRAME);
        assert(g_img[M_FLAG] == 1);
        callbacks[OBS_MTF_SKIP](r, GATE_SUBMIT);
        int s = g_img[M_FLAG] == 0; k += s;
        g_img[M_FLAG] = 1; g_now += s ? 3 * MS : 25 * MS;
    }
    assert(k > 50);
    g_on = 0;   // Full game speed off (the in-game panel): nothing written
    assert(run(300, 25 * MS) == 0);
    g_on = 1;   // on again: a fresh clock and grace
    assert(run(SKIP_GRACE, 25 * MS) == 0);
    assert(run(100, 25 * MS) > 0);
}
static void gate_early(void) {   // DM_MTF_SKIP_EARLY=1: the FRAME gate writes the 0, before the job lists' dispatch
    setenv("DM_MTF_SKIP_EARLY", "1", 1);
    setup(MTF_SPEED_BUILD, 1);
    uint64_t r[32] = {0};
    run(SKIP_GRACE, 25 * MS);
    int k = 0;
    for (int i = 0; i < 300; i++) {
        callbacks[OBS_MTF_SKIP](r, GATE_FRAME);
        int s = g_img[M_FLAG] == 0; k += s;
        callbacks[OBS_MTF_SKIP](r, GATE_SUBMIT);
        assert(g_img[M_FLAG] == (s ? 0 : 1));
        g_img[M_FLAG] = 1; g_now += s ? 3 * MS : 25 * MS;
    }
    assert(k > 50);
}
static void gate_60(void) { setup(MTF_SPEED_BUILD, 1); assert(run(600, SKIP_STEP_NS) == 0 && g_writes == 0); }
static void gate_jobs_change(void) {   // every frame brings a new job: every frame drawn
    setup(MTF_SPEED_BUILD, 1);
    int k = 0;
    for (int i = 0; i < 400; i++) { job(1, 0x92000 + (uint64_t)i * 0x10, 0x5000100); k += frame(25 * MS); }
    assert(k == 0);
}
static void gate_other_build(void) { setup("00000000000000000000000000000000", 1); assert(run(400, 25 * MS) == 0 && g_writes == 0); }
static void gate_bad_got(void) { setup(MTF_SPEED_BUILD, 0); assert(run(400, 25 * MS) == 0 && g_writes == 0); }
static void gate_off(void) { setenv("DM_FPS_DECOUPLE", "0", 1); g_on = 0; setup(MTF_SPEED_BUILD, 1); assert(run(400, 25 * MS) == 0 && g_writes == 0); }
static void gate_display(void) { setup(MTF_SPEED_BUILD, 1); setenv("DM_PRESENT_INTERVAL", "display", 1); assert(run(400, 25 * MS) == 0 && g_writes == 0); }
static void gate_test(void) {   // DM_MTF_SKIP_TEST=4: every fourth frame, from the first, whatever the clock and the setting
    setenv("DM_MTF_SKIP_TEST", "4", 1); g_on = 0;
    setup(MTF_SPEED_BUILD, 1);
    for (int i = 1; i <= 40; i++) assert(frame(SKIP_STEP_NS) == (i % 4 == 0));
}
static void gate_stuck_flag(void) {   // a 0 left at a frame's start (a caller without the frame's end) is written back to 1 before the dispatch reads it
    setup(MTF_SPEED_BUILD, 1);
    uint64_t r[32] = {0};
    g_img[M_FLAG] = 0;
    callbacks[OBS_MTF_SKIP](r, GATE_FRAME);
    assert(g_img[M_FLAG] == 1);
}
static void gate_half_draw(void) {   // cap 30 through flag 15 takes priority: the skip stands down and leaves the engine's 0 on odd steps alone
    setup(MTF_SPEED_BUILD, 1);
    g_half = 1;
    uint64_t r[32] = {0};
    g_img[M_FLAG] = 0;
    callbacks[OBS_MTF_SKIP](r, GATE_FRAME);
    assert(g_img[M_FLAG] == 0 && g_writes == 0);
    g_img[M_FLAG] = 1;
    assert(run(400, 25 * MS) == 0 && g_writes == 0);
}

static void in_child(void (*fn)(void), const char *what) {
    fflush(stdout);
    pid_t p = fork();
    if (!p) { fn(); _exit(0); }
    int st = 0; waitpid(p, &st, 0);
    if (!(p > 0 && WIFEXITED(st) && WEXITSTATUS(st) == 0)) { printf("FAIL t_mtf_speed: %s\n", what); exit(1); }
}

int main(void) {
    in_child(pick_cases, "skip_pick");
    in_child(sig_cases, "jobs_sig");
    in_child(gate_late, "the SUBMIT gate writes the 0; the setting off and on");
    in_child(gate_early, "DM_MTF_SKIP_EARLY");
    in_child(gate_60, "60 fps");
    in_child(gate_jobs_change, "new jobs every frame");
    in_child(gate_other_build, "another nro0 build");
    in_child(gate_bad_got, "a GOT that does not match");
    in_child(gate_off, "DM_FPS_DECOUPLE=0");
    in_child(gate_display, "DM_PRESENT_INTERVAL=display");
    in_child(gate_test, "DM_MTF_SKIP_TEST");
    in_child(gate_stuck_flag, "a 0 left at a frame's start");
    in_child(gate_half_draw, "cap 30 through flag 15 takes priority");
    printf("t_mtf_speed: ok\n");
    return 0;
}
