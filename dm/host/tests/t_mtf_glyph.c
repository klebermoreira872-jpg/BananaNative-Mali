// Mario Tennis Fever glyph gate (android/mtf_glyph.c): on a frame whose draw flag is 0 the store that marks the dirty-rect ring consumed writes the read index back (w8 :=
// read index), so the rects stay pending; on a drawn frame w8 stays the write index; a GOT that does not point at the draw flag, and another nro0 build, change nothing.
// Every build case runs in its own process (the build is checked once).
#include "../android/mtf_glyph.c"
#include <assert.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>

static module_t test_modules[2];
module_t *g_mod = test_modules;
int g_nmod;
static void (*callbacks[OBS_MAX])(uint64_t *, int);
void gate_obs_set(int id, void (*fn)(uint64_t *, int)) { assert(id > 0 && id < OBS_MAX); callbacks[id] = fn; }

static uint8_t *g_img;   // nro0's image, as far as the draw flag
static void setup(const char *build, int got_ok) {
    size_t n = M_FLAG + 0x1000;
    g_img = mmap(NULL, n, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0); assert(g_img != MAP_FAILED);
    uint64_t got = (uint64_t)(uintptr_t)g_img + (got_ok ? M_FLAG : 0x100);
    memcpy(g_img + M_FLAG_GOT, &got, 8);
    g_nmod = 2;
    strcpy(g_mod[0].name, "main"); strcpy(g_mod[0].build_id, "104bce6874603701935eb76cb7d8b59e");
    strcpy(g_mod[1].name, "nro0"); g_mod[1].nro = 1; strcpy(g_mod[1].build_id, build); g_mod[1].base = g_img;
}

// One call of the gate with the draw flag, the ring's write and read indices: w8 after it (the value the store writes into the read index)
static uint64_t run(int flag, uint32_t wr, uint32_t rd) {
    g_img[M_FLAG] = (uint8_t)flag;
    _Alignas(16) uint32_t ring[2] = {wr, rd};
    uint64_t r[100];
    memset(r, 0, sizeof r);
    r[26] = (uintptr_t)ring; r[8] = wr;
    callbacks[OBS_MTF_GLYPH](r, 0);
    assert(ring[0] == wr && ring[1] == rd);   // the gate never writes the ring itself
    return r[8];
}

static void cases(void) {
    setup(MTF_GLYPH_BUILD, 1);
    assert(run(1, 7, 3) == 7);    // drawn frame: consumed as the game does
    assert(run(0, 7, 3) == 3);    // undrawn frame: left pending
    assert(run(0, 2, 30) == 30);  // wrapped indices: the read index as it is
    assert(run(0, 5, 5) == 5);    // nothing pending
    assert(run(1, 9, 3) == 9);    // the next drawn frame takes all of it
    assert(g_kept == 3 && g_seen == 5);
}

static void bad_got(void) { setup(MTF_GLYPH_BUILD, 0); assert(run(0, 7, 3) == 7); }
static void other_build(void) { setup("00000000000000000000000000000000", 1); assert(run(0, 7, 3) == 7); }

static void in_child(void (*fn)(void), const char *what) {
    fflush(stdout);
    pid_t p = fork();
    if (!p) { fn(); _exit(0); }
    int st = 0; waitpid(p, &st, 0);
    if (!(p > 0 && WIFEXITED(st) && WEXITSTATUS(st) == 0)) { printf("FAIL t_mtf_glyph: %s\n", what); exit(1); }
}

int main(void) {
    assert(callbacks[OBS_MTF_GLYPH]);
    in_child(cases, "nro0 1.1.1: the ring left pending on undrawn frames only");
    in_child(bad_got, "a GOT that does not point at the draw flag: nothing changed");
    in_child(other_build, "another nro0 build: nothing changed");
    printf("t_mtf_glyph: OK\n");
    return 0;
}
