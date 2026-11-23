// The Vulkan shader library reader (android/SHADERS.md "Library format"): one file per game, dmsh_vk.lib, made by dm/gfx/tools/vk_android_build.py. Plain C with no Vulkan,
// so the Mac unit test (dm/host/tests t_android_shlib) runs the same code against a real library. The replay (vka_shader.c) maps the file once and takes modules from it by key
#pragma once
#include <stddef.h>
#include <stdint.h>
#include "../nvn/dmsh_abi_vk.h"

typedef struct {
    const uint8_t *base; size_t size;          // the whole file (mapped, or a caller's buffer)
    const dmsh_vk_header *h;
    const dmsh_vk_entry *ent; const dmsh_vk_bind *bind; const dmsh_vk_module *mod; const uint8_t *blob;
    int mapped;   // 1: base is a mapping of the file (vka_shlib_open); 2: base is a malloc'd image of one entry (vka_shlib_extract); vka_shlib_close undoes either
    int by_abi;   // taken by its abi only: its chain or vk_chain is not the host's (an older library played while its update runs); 1 = the host's ABI, 2 = a compatible older one
    unsigned differs;   // taken by an older ABI of vka_abi_compat.h (by_abi too): what its modules do otherwise (VKA_ABI_*); 0 for the host's own ABI
} vka_shlib;

// Checks a library image against what the host was built with: magic, version, chain, vk_chain and game (NULL = not checked), then every table and range inside the file and the
// entries' key order. abi (the host's DMSH_VK_ABI; NULL = versions only): a library whose chain or vk_chain differs is still taken when its header's abi is this one (by_abi),
// or, when abi is this host's DMSH_VK_ABI, a compatible older one (vka_abi_compat.h; differs says what to follow), the rule for an older library while its delta update runs
// (android/SHADERS.md#delta-updates). 1 = usable; else 0 and err says why (one line)
int vka_shlib_check(vka_shlib *L, const void *base, size_t size, const char *chain, const char *vk_chain, const char *game, const char *abi, char *err, size_t errn);
// Maps path read-only and checks it as above
int vka_shlib_open(vka_shlib *L, const char *path, const char *chain, const char *vk_chain, const char *game, const char *abi, char *err, size_t errn);
void vka_shlib_close(vka_shlib *L);
// Entry e of L as a library of its own: one malloc'd image of L's header (translator answers, ABI) with e (rebased), its bindings, its module records and its blob bytes (c1
// and every module), checked like a file. The run-time shader layer's shaders keep such a copy (vka_shader.c), so no shader points into a layer file that a newer one
// replaces and its mapping can go. Its entry hash (vka_shlib_entry_hash) is e's in L. 1 = *out usable (vka_shlib_close frees it); 0 = out of memory or a bad entry (err)
int vka_shlib_extract(vka_shlib *out, const vka_shlib *L, const dmsh_vk_entry *e, char *err, size_t errn);
// An empty library: no entries, its header (h, the caller's storage, which must outlive L) the host's own (chain, vk_chain, game, abi; NULL = left zero) with the translator
// answers sg (subgroup_size) and sa (ssbo_align) the host's tools build with. Played when a pack has no library but the run-time shader layer may make every shader
// (vka_shader.c lib_load, android/SHADERS.md "Shaders the library lacks"): every key is a miss. 1 = L usable (0 only for a header string of the wrong length)
int vka_shlib_empty(vka_shlib *L, dmsh_vk_header *h, const char *chain, const char *vk_chain, const char *game, const char *abi, uint16_t sg, uint16_t sa, char *err, size_t errn);

uint64_t vka_shlib_key(const uint8_t md[8]);   // the host's 8-byte program key (prog_key) as the library's sort key: its 16 hex digits read as one big-endian number
const dmsh_vk_entry *vka_shlib_find(const vka_shlib *L, uint64_t key);   // NULL = not in the library
static inline const dmsh_vk_bind *vka_shlib_binds(const vka_shlib *L, const dmsh_vk_entry *e) { return L->bind + e->bind; }
const dmsh_vk_module *vka_shlib_module(const vka_shlib *L, const dmsh_vk_entry *e, int variant);   // NULL = no module of that variant
// Offsets in the blob: the low 32 bits and the high bits of their records (a blob past 4 GiB; 0 in a smaller one)
static inline uint64_t vka_shlib_c1_off(const dmsh_vk_entry *e) { return (uint64_t)e->c1_off_hi << 32 | e->c1_off; }
static inline uint64_t vka_shlib_mod_off(const dmsh_vk_module *m) { return (uint64_t)m->off_hi << 32 | m->off; }
static inline const uint8_t *vka_shlib_c1(const vka_shlib *L, const dmsh_vk_entry *e) { return e->c1_len ? L->blob + vka_shlib_c1_off(e) : NULL; }
// The module's SPIR-V words, decompressed when stored with zstd: malloc'd (the caller frees), *nbytes its size. NULL with err on a bad module
uint32_t *vka_shlib_spirv(const vka_shlib *L, const dmsh_vk_module *m, size_t *nbytes, char *err, size_t errn);
// What an entry is, as one number for the pipeline cache's stamp (vka_pso.c, vka_pckeep.h): the 64-byte entry with its positions in the file zeroed (first module, first
// binding, c1 offset), its binding records, its c1 bytes, and each module record (offset zeroed) with its bytes as stored. Two libraries give the same number for an entry
// whose shader is byte for byte the same, wherever it lies in each file and whatever their headers say (a restamped library, a delta update's reused entries); never 0
uint64_t vka_shlib_entry_hash(const vka_shlib *L, const dmsh_vk_entry *e);
// A header string (chain, vk_chain, game, inputs: 16 bytes NUL padded) as a C string
void vka_shlib_str(const char field[16], char out[17]);
