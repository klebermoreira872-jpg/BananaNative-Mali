// The run-time shader layer's request side and its mappings' lifetime (vka_shader.c; android/SHADERS.md "Shaders the library lacks"), free of Android and Vulkan so the Mac's
// unit test (dm/host/tests/t_android_layerreq.c) runs it: where the layer lives, a set of keys already handled this run, the writer of requests, which takes a program's stages
// (control section and code, copied by the caller) on a bounded queue and writes them on a thread of its own, so the render path that met the miss does no file work, and the
// references that keep a layer mapped while a lookup uses it.
// A request is req/<key>.code, then req/<key>.ctl (last: it says the pair is whole), and the program's (vertex, pixel) pairs appended to req/pairs.tsv (each pair once: the
// writer reads the file's pairs first). A stage or pair the writer could not write is handed back (vka_lrq.unwritten), so the caller unmarks it and asks again
#ifndef VKA_LAYERREQ_H
#define VKA_LAYERREQ_H
#include <errno.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

// The layer's folder: DM_VK_LAYER_DIR (dir) when set, else $DM_TEMP/shader_layer (temp); none when the layer is off (DM_VK_LAYER=0: on = 0) or neither is set.
// 1 = out holds the folder
static inline int vka_layer_root_of(char *out, size_t n, const char *dir, const char *temp, int on) {
    out[0] = 0;
    if (!on) return 0;
    int w = dir && *dir ? snprintf(out, n, "%s", dir) : temp && *temp ? snprintf(out, n, "%s/shader_layer", temp) : -1;
    if (w < 0 || (size_t)w >= n) { out[0] = 0; return 0; }
    while (w > 1 && out[w - 1] == '/') out[--w] = 0;   // (a trailing slash given)
    return 1;
}

// Keys handled this run: open addressing, a fixed table (power of two, twice the keys). 1 = added now, 0 = there already, -1 = the table is full (not added)
#define VKA_KEYSET_CAP 16384
typedef struct { uint64_t k[2 * VKA_KEYSET_CAP]; unsigned n; } vka_keyset;
static inline unsigned vka_keyset_slot(uint64_t k) { return (unsigned)((k * 0x9E3779B97F4A7C15ull) >> 40) & (2 * VKA_KEYSET_CAP - 1); }
static inline int vka_keyset_has(const vka_keyset *s, uint64_t k) {
    if (!k) return 0;
    for (unsigned i = vka_keyset_slot(k); s->k[i]; i = (i + 1) & (2 * VKA_KEYSET_CAP - 1)) if (s->k[i] == k) return 1;
    return 0;
}
static inline int vka_keyset_add(vka_keyset *s, uint64_t k) {
    if (!k) return 0;   // (0 is the empty slot)
    unsigned i = vka_keyset_slot(k);
    for (; s->k[i]; i = (i + 1) & (2 * VKA_KEYSET_CAP - 1)) if (s->k[i] == k) return 0;
    if (s->n >= VKA_KEYSET_CAP) return -1;
    s->k[i] = k; s->n++; return 1;
}
// Takes k out (backward-shift deletion, so the probe runs of the other keys stay whole). 1 = it was there
static inline int vka_keyset_del(vka_keyset *s, uint64_t k) {
    const unsigned m = 2 * VKA_KEYSET_CAP - 1;
    if (!k) return 0;
    unsigned i = vka_keyset_slot(k);
    for (; s->k[i] != k; i = (i + 1) & m) if (!s->k[i]) return 0;
    for (unsigned j = i;;) {   // i: the hole; a later key of the run moves into it unless its home slot lies cyclically in (i, j]
        j = (j + 1) & m;
        if (!s->k[j]) break;
        unsigned h = vka_keyset_slot(s->k[j]);
        if (i <= j ? (i < h && h <= j) : (i < h || h <= j)) continue;
        s->k[i] = s->k[j]; i = j;
    }
    s->k[i] = 0; s->n--;
    return 1;
}

// One program's request: its stages the layer is asked for (each with its own malloc'd copies) and its (vertex, pixel) pairs. A request may hold pairs only (a program
// whose stages were all asked for before)
#define VKA_LREQ_STAGES 6
typedef struct vka_lreq {
    struct vka_lreq *next;
    unsigned ns, np;
    struct { uint64_t key; uint8_t *ctl, *code; uint32_t nctl, ncode; } st[VKA_LREQ_STAGES];
    struct { uint64_t vs, ps; } pr[VKA_LREQ_STAGES * VKA_LREQ_STAGES];
    size_t bytes;   // what it holds (the queue's bound)
} vka_lreq;
// A pair as one key of a vka_keyset (never 0)
static inline uint64_t vka_lreq_pair_id(uint64_t vs, uint64_t ps) {
    uint64_t h = (vs ^ 0x9E3779B97F4A7C15ull) * 0xBF58476D1CE4E5B9ull; h ^= h >> 31; h = (h ^ ps) * 0x94D049BB133111EBull; h ^= h >> 29;
    return h ? h : 1;
}
static inline void vka_lreq_free(vka_lreq *r) {
    if (!r) return;
    for (unsigned i = 0; i < r->ns; i++) { free(r->st[i].ctl); free(r->st[i].code); }
    free(r);
}
// Adds a stage (copies ctl and code; 0 = out of memory or full)
static inline int vka_lreq_add(vka_lreq *r, uint64_t key, const void *ctl, uint32_t nctl, const void *code, uint32_t ncode) {
    if (r->ns >= VKA_LREQ_STAGES || !ctl || !code || !nctl || !ncode) return 0;
    uint8_t *c = malloc(nctl), *d = malloc(ncode);
    if (!c || !d) { free(c); free(d); return 0; }
    memcpy(c, ctl, nctl); memcpy(d, code, ncode);
    r->st[r->ns].key = key; r->st[r->ns].ctl = c; r->st[r->ns].nctl = nctl; r->st[r->ns].code = d; r->st[r->ns].ncode = ncode; r->ns++;
    r->bytes += (size_t)nctl + ncode;
    return 1;
}
static inline int vka_lreq_pair(vka_lreq *r, uint64_t vs, uint64_t ps) {   // 0 = full, or there already
    if (!vs || !ps || r->np >= VKA_LREQ_STAGES * VKA_LREQ_STAGES) return 0;
    for (unsigned i = 0; i < r->np; i++) if (r->pr[i].vs == vs && r->pr[i].ps == ps) return 0;
    r->pr[r->np].vs = vs; r->pr[r->np].ps = ps; r->np++; r->bytes += 34;
    return 1;
}

// 1 = written whole; 0 = not (the file removed), *err its errno
static inline int vka_lreq_file(const char *path, const void *p, size_t n, int *err) {
    FILE *o = fopen(path, "wb"); if (!o) { *err = errno; return 0; }
    int ok = fwrite(p, 1, n, o) == n; if (!ok) *err = errno ? errno : EIO;
    if (fclose(o) && ok) { ok = 0; *err = errno ? errno : EIO; }
    if (!ok) unlink(path);
    return ok;
}
static inline int vka_lreq_dirs(const char *root, const char *dir) {   // 1 = root/req is a folder (made when missing)
    mkdir(root, 0777); mkdir(dir, 0777); struct stat sb;
    return !stat(dir, &sb) && S_ISDIR(sb.st_mode);
}
// The queue and its writer thread (started at the first push). Bounded by requests and bytes: a push past either is refused (the caller frees the request and leaves
// its keys unmarked, so a later resolution asks again). unwritten (set before the first push; may be NULL) is called on the writer thread, without the queue's lock, for
// each stage (pair 0: a = its key) or pair (pair 1: a, b = vertex, pixel key) it could not write, with the errno: the caller unmarks it, so it is asked for again
typedef struct vka_lrq {
    pthread_mutex_t mu; pthread_cond_t cv, idle;
    vka_lreq *head, *tail; unsigned n, max_n; size_t bytes, max_bytes;
    int started, busy, dirs_made;
    char root[1024];
    unsigned long long written, refused, failed;   // stages written; requests refused (full); stages and pairs not written
    void (*unwritten)(void *ctx, int pair, uint64_t a, uint64_t b, int err); void *ctx;
    int pairs_read, pairs_cut;   // (the writer thread's) pairs.tsv's pairs read into pseen; its last line lacks its newline
    vka_keyset pseen;            // (the writer thread's) the pairs in pairs.tsv
} vka_lrq;
#define VKA_LRQ_INIT {.mu = PTHREAD_MUTEX_INITIALIZER, .cv = PTHREAD_COND_INITIALIZER, .idle = PTHREAD_COND_INITIALIZER, .max_n = 256, .max_bytes = 64u << 20}
static inline void vka_lrq_fail(vka_lrq *q, int pair, uint64_t a, uint64_t b, int err) {
    pthread_mutex_lock(&q->mu); q->failed++; pthread_mutex_unlock(&q->mu);
    if (q->unwritten) q->unwritten(q->ctx, pair, a, b, err);
}
// The pairs pairs.tsv holds (an earlier run's, or this run's), read once, so a pair is appended once
static inline void vka_lrq_read_pairs(vka_lrq *q, const char *path) {
    q->pairs_read = 1;
    FILE *f = fopen(path, "rb"); if (!f) return;
    char ln[128]; int last = '\n';
    while (fgets(ln, sizeof ln, f)) {
        size_t l = strlen(ln); if (l) last = ln[l - 1];
        unsigned long long vs, ps;
        if (l >= 33 && ln[16] == '\t' && sscanf(ln, "%16llx\t%16llx", &vs, &ps) == 2 && ln[l - 1] == '\n') vka_keyset_add(&q->pseen, vka_lreq_pair_id(vs, ps));
    }
    q->pairs_cut = last != '\n';
    fclose(f);
}
// Writes r under root/req/ (made at the first request, and again when a file cannot be made in it: Storage may remove the folder while the game runs). A stage whose .ctl
// is there already (an earlier run's request) is not written again; a pair pairs.tsv has is not appended again. Returns the stages written
static inline unsigned vka_lreq_write(vka_lrq *q, const vka_lreq *r) {
    char dir[1100], f[1200], fc[1200]; unsigned wrote = 0; int err = 0;
    if (snprintf(dir, sizeof dir, "%s/req", q->root) >= (int)sizeof dir) err = ENAMETOOLONG;
    else if (!q->dirs_made && !(q->dirs_made = vka_lreq_dirs(q->root, dir))) err = errno ? errno : ENOTDIR;
    for (unsigned i = 0; i < r->ns; i++) {
        int e = err;
        if (!e) {
            snprintf(f, sizeof f, "%s/%016llx.ctl", dir, (unsigned long long)r->st[i].key);
            if (!access(f, F_OK)) continue;
            snprintf(fc, sizeof fc, "%s/%016llx.code", dir, (unsigned long long)r->st[i].key);
            for (int t = 0; t < 2; t++) {
                e = 0;
                if (vka_lreq_file(fc, r->st[i].code, r->st[i].ncode, &e) && vka_lreq_file(f, r->st[i].ctl, r->st[i].nctl, &e)) { wrote++; break; }
                unlink(fc);
                if (t || (e != ENOENT && e != ENOTDIR) || !(q->dirs_made = vka_lreq_dirs(q->root, dir))) break;   // (the folder gone: made again, tried once more)
            }
            if (!e) continue;
        }
        vka_lrq_fail(q, 0, r->st[i].key, 0, e);
    }
    if (!r->np) return wrote;
    snprintf(f, sizeof f, "%s/pairs.tsv", dir);
    if (!err && !q->pairs_read) vka_lrq_read_pairs(q, f);
    char txt[VKA_LREQ_STAGES * VKA_LREQ_STAGES * 34 + 2]; size_t tl = 0; unsigned want[VKA_LREQ_STAGES * VKA_LREQ_STAGES], nw = 0;
    for (unsigned i = 0; i < r->np; i++) {
        if (vka_keyset_has(&q->pseen, vka_lreq_pair_id(r->pr[i].vs, r->pr[i].ps))) continue;
        want[nw++] = i;
        tl += (size_t)snprintf(txt + tl, sizeof txt - tl, "%016llx\t%016llx\n", (unsigned long long)r->pr[i].vs, (unsigned long long)r->pr[i].ps);
    }
    if (!nw) return wrote;
    int e = err;
    if (!e) {
        FILE *o = fopen(f, "a");
        if (!o && (errno == ENOENT || errno == ENOTDIR) && (q->dirs_made = vka_lreq_dirs(q->root, dir))) o = fopen(f, "a");
        if (!o) e = errno ? errno : EIO;
        else {
            int ok = (!q->pairs_cut || fputc('\n', o) != EOF) && fwrite(txt, 1, tl, o) == tl;   // (a line an earlier stop cut short is ended first)
            if (!ok) e = errno ? errno : EIO;
            if (fclose(o) && ok) { ok = 0; e = errno ? errno : EIO; }
            if (ok) { q->pairs_cut = 0; for (unsigned k = 0; k < nw; k++) vka_keyset_add(&q->pseen, vka_lreq_pair_id(r->pr[want[k]].vs, r->pr[want[k]].ps)); return wrote; }
        }
    }
    for (unsigned k = 0; k < nw; k++) vka_lrq_fail(q, 1, r->pr[want[k]].vs, r->pr[want[k]].ps, e);
    return wrote;
}
static inline void *vka_lrq_thread(void *a) {
    vka_lrq *q = a;
    pthread_mutex_lock(&q->mu);
    for (;;) {
        while (!q->head) pthread_cond_wait(&q->cv, &q->mu);
        vka_lreq *r = q->head; q->head = r->next; if (!q->head) q->tail = NULL;
        q->n--; q->bytes -= r->bytes; q->busy = 1;
        pthread_mutex_unlock(&q->mu);
        unsigned w = vka_lreq_write(q, r);   // (dirs_made, pseen: only this thread touches them once started)
        vka_lreq_free(r);
        pthread_mutex_lock(&q->mu);
        q->written += w; q->busy = 0;
        if (!q->head) pthread_cond_broadcast(&q->idle);
    }
    return NULL;
}
// 1 = queued (the queue owns r); 0 = refused (full, or no thread): the caller still owns r
static inline int vka_lrq_push(vka_lrq *q, const char *root, vka_lreq *r) {
    int ok = 0;
    pthread_mutex_lock(&q->mu);
    if (!q->started) {
        snprintf(q->root, sizeof q->root, "%s", root);
        pthread_t th; pthread_attr_t at; pthread_attr_init(&at); pthread_attr_setdetachstate(&at, PTHREAD_CREATE_DETACHED);
        q->started = pthread_create(&th, &at, vka_lrq_thread, q) == 0 ? 1 : -1;
        pthread_attr_destroy(&at);
#if defined(__ANDROID__) || defined(__linux__)
        if (q->started > 0) pthread_setname_np(th, "vk-layer-req");
#endif
    }
    if (q->started > 0 && q->n < q->max_n && q->bytes + r->bytes <= q->max_bytes) {
        r->next = NULL; if (q->tail) q->tail->next = r; else q->head = r; q->tail = r;
        q->n++; q->bytes += r->bytes; ok = 1;
        pthread_cond_signal(&q->cv);
    } else q->refused++;
    pthread_mutex_unlock(&q->mu);
    return ok;
}
// 1 = the queue is at most half full (a request it refused may be asked again)
static inline int vka_lrq_room(vka_lrq *q) {
    pthread_mutex_lock(&q->mu); int r = q->n <= q->max_n / 2 && q->bytes <= q->max_bytes / 2; pthread_mutex_unlock(&q->mu);
    return r;
}
static inline unsigned long long vka_lrq_written(vka_lrq *q) { pthread_mutex_lock(&q->mu); unsigned long long w = q->written; pthread_mutex_unlock(&q->mu); return w; }
// Waits until every queued request is written (tests, and a caller that must see the files)
static inline void vka_lrq_drain(vka_lrq *q) {
    pthread_mutex_lock(&q->mu);
    while (q->head || q->busy) pthread_cond_wait(&q->idle, &q->mu);
    pthread_mutex_unlock(&q->mu);
}

// ---- The layer's mappings. A lookup takes the current layer with a reference (vka_ly_get) and gives it back when done (vka_ly_put); a new layer replaces the current one
// (vka_ly_set), and a layer replaced is dropped (drop(obj): unmapped, so the disk space of its file, which the packer replaced, is freed) when its last reference goes.
// Nothing else may keep a pointer into a layer: the shaders made from one keep a copy of their entry (vka_shlib_extract)
typedef struct vka_lyh { void *obj; unsigned refs; } vka_lyh;
typedef struct {
    pthread_mutex_t mu; vka_lyh *cur; void (*drop)(void *obj);
    unsigned live; unsigned long long set, dropped;   // layers mapped now (the current one and replaced ones a lookup still holds); layers taken; layers dropped
} vka_lylife;
#define VKA_LYLIFE_INIT(drop_fn) {.mu = PTHREAD_MUTEX_INITIALIZER, .drop = (drop_fn)}
static inline vka_lyh *vka_ly_get(vka_lylife *l) {   // NULL = no layer
    pthread_mutex_lock(&l->mu); vka_lyh *h = l->cur; if (h) h->refs++; pthread_mutex_unlock(&l->mu);
    return h;
}
static inline void vka_ly_put(vka_lylife *l, vka_lyh *h) {
    if (!h) return;
    pthread_mutex_lock(&l->mu); int gone = --h->refs == 0; if (gone) { l->live--; l->dropped++; } pthread_mutex_unlock(&l->mu);
    if (gone) { if (l->drop) l->drop(h->obj); free(h); }
}
static inline int vka_ly_set(vka_lylife *l, void *obj) {   // 0 = out of memory (obj not taken)
    vka_lyh *n = malloc(sizeof *n); if (!n) return 0;
    n->obj = obj; n->refs = 1;   // (the current layer's own reference)
    pthread_mutex_lock(&l->mu); vka_lyh *old = l->cur; l->cur = n; l->live++; l->set++; pthread_mutex_unlock(&l->mu);
    vka_ly_put(l, old);
    return 1;
}
#endif
