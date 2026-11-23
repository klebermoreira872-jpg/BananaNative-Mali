# What changed, and what to check first

Files (same paths as in the archive): `dm/gfx/vk_android/vka_texlimit.h`, `vka_tex.c`, `vka_dev.c`, `vka_present.c`.
`changes.patch` is the same change as a unified diff (apply with `patch -p0` from the folder that holds `dm/`), in case your local files differ from the archive.

Checked: syntax-checked against the project's headers with stub Android headers, no new compiler warnings, and the project's own `t_android_texlimit` / `t_android_soft` host tests pass with the patched header.
NOT checked: no NDK build, no run on a Mali device. Whether these changes bring the picture back is unknown until you run it.

## 1. Texture cache (vka_tex.c, vka_texlimit.h)
- `DM_VK_IMG_CAP_MB` (live). Default 512 when sparse residency images are unavailable (`vks_on()` false = `sparse.residencyImages=0`), else 0 (no cap). 0 turns it off.
- The cache limit is never above the cap; the working-set guard is off under the cap, so eviction is plain least-recently-used (images used in the last 2 frames, held, in-flight and GPU-written images still stay: a render target cannot be re-uploaded).
- Under the cap soft textures are on (large BC/ASTC game textures drop their finest 2 levels, DM_VK_TEX_SOFT=0 / DM_VK_TEX_SOFT_LEVELS override) and a sparse texture made dense is held to 64 MiB (DM_VK_SPARSE_DENSE_MB).
- Not done: lowering bits-per-pixel (transcoding to a smaller format). Nothing in the renderer converts texture formats, and doing it blind would risk wrong colours. Mip dropping is the reduction used.
- Risk: a scene whose textures in use exceed 512 MiB will evict and upload every frame (slow). The log then says "image cache over its limit". Raise DM_VK_IMG_CAP_MB if that happens.

## 2. PanVK defaults (vka_dev.c)
- PanVK is detected by driver ID or name. On it: graphics pipeline libraries off (whole pipelines) and mesh draws through compute, unless DM_VK_GPL / DM_VK_MESH_EMU are set. `vka_is_panvk()` exposes it.
- New log lines: `Mesa PanVK detected`, and `mesh through compute needs: ...` with the device limits the emulation depends on.
- These two env switches already existed and already did this when you set them; the change is the default plus the limits line. I could not find, from the archive alone, a code bug in the emulation or the monolithic path that drops draws: the drops are logged as `[RED]` lines (see below), which is what decides the next step.

## 3. Presentation (vka_present.c)
- The Android present already creates an RGBA8/BGRA8 UNORM swapchain and blits (or draws) the window texture into it. `DM_PRESENT_SNAP` exists only in the Metal host (`nvn_mtl.m`), so it has no effect here and I did not port it.
- Changed: the format choice looks for R8G8B8A8_UNORM / B8G8R8A8_UNORM in any colour space before falling back to the surface's first format (`DM_VK_SWAP_FORMAT=bgra` flips the order); if the swapchain format cannot be a blit destination the picture goes through the existing shader copy.
- New log: `present N: window texture ... inited 0|1 ... blit ...`. If `inited 0`, the replay never drew into the window texture: the problem is upstream of the swapchain.

## What to send / grep in the log (this decides the real cause)
`draws and dispatches are off`, `no placed maps or exported guest memory alias`, `its draws are skipped`, `has no Vulkan format on this device`, `cannot be blitted to the swapchain: presented black`, `present 0:`, `Mesa PanVK detected`, `mesh through compute needs`.
A GPU frame of 0.3-0.4 ms means almost nothing is being drawn, so the draw-skip lines are the first suspects.
