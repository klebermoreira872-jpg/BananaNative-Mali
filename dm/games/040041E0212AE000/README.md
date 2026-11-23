# Fast Fusion (`040041E0212AE000`)

A Switch 2 game: v262144, SDK 20.5.13 (`Ounce`), NVN2, Shin'en's engine. Modules `main` and `sdk`. **Plays on the Mac** (M6, 16 GB, macOS 27.2, 2026-11-14): title, Championship menus, the first available race, acceleration and scenery streaming, with sound enabled. The final race run renders the sky and volumetric fog; the earlier black sky was the missing fog dispatch described below. Testing totalled 9 minutes 50 seconds, including starts, menus and a final 30-second boot/menu check after rebasing onto current main; no race was completed. No iPhone or iPad test or IPA build.

## What it needs

| Setting | Where | Why |
|---|---|---|
| `modules main sdk` | [`game.tsv`](game.tsv) | the host supplies the imports that otherwise reach `subsdk0` and `subsdk1`; neither needs to load |
| `mem_reserve 0x270000000`, `mem_alias 0x10000000`, `mem_stack 0x10000000`, `app_pool 0x240000000` | `game.tsv` | the Switch 2's 9 GB pool; the game requests an 8.94 GB heap in the 9 GB heap region |
| `sys_resource 0x0` | `game.tsv` | the NPDM declares no system resource, so virtual address memory is off |
| `depth_mode zero` | `game.tsv` | the game sets near = 0; the offline pipeline archive must use the same depth entry |
| `shader_groups`, `shader_note` | `game.tsv` | name the packages of loose shaders, scene resources and the NDSR pack |

There is no game-specific rewriter patch, host branch or shader override. The shared resource reader has `engine` binding through the `SHN!` / `SHDROUNC` signatures; the instruction and texture-table fixes have `host` binding through NVN2 semantics. Both are at their loosest correct binding. The build row registers this main build only (`e76e60ef4fe21decb40223b5de5e6396`); other versions have not been tested.

## Files and shaders

- The supplied NUP is named v0 but contains a standalone update v262144, with no base package, control data or icon. The actual display version is unknown; the app bundle uses the packer's fallback version 1.0. The update holds all files needed by the tested route.
- RomFS: 3,355 files, 3.62 GB. The `SHN!` wrapper also carries textures, particles and other resources; finding that magic alone does not identify a shader.
- 152 loose `.shdr` files and 402 `.w3d` scene files contain 2,948 unique shader stages in `SHDROUNC` objects. All 26 shader control keys and GPU-code areas captured at startup match the offline extraction byte for byte. See SHN resources and embedded shader objects.
- The loose NDSR pack contributes 28 more stages. [`shader_map.tsv`](shader_map.tsv) has 2,976: 1,398 vertex, 1,431 pixel, 85 compute, 31 task and 31 mesh. Every shader builds on the Mac.
- The task and mesh programs need subword stage-memory accesses. Before those were implemented, all 62 failed to translate.
- `cded8d0899ba4a6d` (`shaders/volumetricfog.shdr`) needs indexed texture handles in NVN2 compute c0. Before the fix its reflection could not load and the race's sky was black. All 2,975 other base Metal shader sources are byte-identical across that fix.
- [`pso_manifest.tsv`](pso_manifest.tsv) records the title, menus and first race: 932 shader, 292 render-pipeline and 2 compute-pipeline rows. It does not cover the other courses.

## Running on the Mac

Build with `python3 scripts/build_ipa_from_nsp.py <folder> --platform mac-app`. The Mac app is self-contained. The NUP has no icon, so `--icon <image>` is needed for a game-specific app icon.

For development, use `--platform mac` and the command it prints, with `DM_WINDOW=1 DM_WINDOW_TOP=1 DM_METAL_HUD=1`. The work folder on this machine is `/Volumes/S790/nsp/Fast Fusion/040041E0212AE000-work`; `run/boot.sh <log> <seconds> [VAR=value ...]` starts its own renamed host, with `DM_CTL=run/ctl.txt`. `DM_FOCUS_KEEP=1` keeps scripted runs progressing when another app takes focus. The test's memory cap is 10 GB.

From the title: `L+R`, then four separate `A` presses select Championship, the first league, the first cup and the first vehicle/start. Wait between menu transitions. `A` accelerates; `LLeft` / `LRight` steer. A frame-based route from a fresh start is `f600:L+R~f30,f780:A,f900:A,f1020:A,f1140:A,f2200:A~f2400`. Capture after frame 2400 for an early race frame. The first shader and pipeline preparation can delay the first start.

## Android

Played with the Android app on the AYN Odin 3 (Adreno 830, 24 GB), on the phone's own driver and on Turnip v32 (2026-11-19): title, menus and races, about 60 fps. A race in Docked (1080p) takes about 14.5 ms of GPU time (DLSS 960x540 to 1920x1080 on the stand-in, GSR 2); in Handheld (720p) about 12.3 ms (640x360 to 1920x1080). Memory: the host's footprint up to about 1 GB on the phone's driver and 3 GB on Turnip, GPU memory up to about 4.6 GB ([readiness.tsv](readiness.tsv)).

- **Pack.** `pack_android.py` builds 2,914 of its 2,976 shaders; the 62 that fail are its 31 task and 31 mesh programs, which the game does not use on the tested route (no mesh draw is made). Since 2026-11-22 the profile's [`vk_delta.tsv`](vk_delta.tsv) lists those 62 as not built (`-`) for Vulkan chain `6eaa66f9f1e4` and inputs `48fb7f0c192e`, so the phone's Prepare passes without them: in 0.3.50 it stopped with `62 of 2976 shaders did not build: no library written (DMSH_VK_REQUIRE_ALL)` (Forgejo #566; [the shaders step fails on a shader that does not build on the Mac either](../../../docs/reference/packing.md#the-phones-shaders-step-fails-on-a-shader-that-does-not-build-on-the-mac-either)). The cause, task and mesh programs without a mesh layout in the Vulkan chain, is open.
- **Choices.** Docked (1080p) and Handheld (720p) from the `graphics_scale` rows, and the Upscaler row (`dlss_standin`): see [Graphics on Android](#graphics-on-android).
- **Starter set.** [shader_first.tsv](shader_first.tsv): the 391 shaders a first start with no library asked for, from one run on the phone's driver. Without a library the picture is black for the whole first route while they build.
- **Not in the profile.** A prewarm seed: the key lists of runs on both drivers (254 pipelines) were made and play their keys back in 0.1 s; the seed is a binary file built from them.

### Graphics on Android

The game renders its 3D scene at a size its scripts pick and evaluates NVN2 DLSS on it; the host draws that DLSS call with its stand-in (`vka_dlss.c`). Measured on the AYN Odin 3, phone's own driver, a race (2026-11-19):

| Launcher choice | Operation mode | DLSS call | GPU, fps |
|---|---|---|---|
| Docked (1080p), the default | docked | 960x540 to 1920x1080 (2x) | about 14.5 ms, 60 fps |
| Handheld (720p) | handheld | 640x360 to 1920x1080 (3x); the window crop is 1920x1080 since the host reports the Switch 2's 1080p screen in handheld mode (before, 1280x720) | about 12.3 ms, 60 fps |

The menus evaluate DLSS at 1920x1080 to 1920x1080 (NVIDIA's DLAA: anti-aliasing at the same size). The Upscaler row picks what draws the call: GSR 2 (the default: temporal, three passes and RCAS), FSR 1 (spatial, faster), FSR 3.1 (temporal) or Bilinear. All four keep the colour's alpha, which the game composites its 3D layer over the menu UI by.

The game's own Options, GRAPHICS (TV mode), docked, as its menu describes them and as they ran:

| Mode | The game's description | On the phone |
|---|---|---|
| PURE | 60 fps, 1440p dynamic resolution, dynamic cubemap reflections, no anti-aliasing, no AO | no change seen |
| PERFORMANCE (default) | 60 fps, 1080p, realtime reflections, dynamic shadows, AA, AO | 960x540 to 1920x1080 in races; about 14.5 ms, 60 fps |
| BALANCED | as PERFORMANCE, 1440p | no change seen |
| QUALITY | 60 fps, 4K, realtime reflections, static and screen-space shadows, AA, AO | no change seen |
| ULTRA QUALITY | 30 fps in races, 4K, realtime reflections, dynamic shadows, AA, AO | no change seen; races stay at 60 fps |

On the phone none of the five modes was seen to change anything: at the same moment of the race start every mode's picture is within the noise of PERFORMANCE run twice, the GPU time and the DLSS sizes are the same (960x540 to 1080p in races), and ULTRA QUALITY's races stay at 60 fps. The setting does not hold: Options shows PERFORMANCE again when it is opened again or after a restart. Open: whether the game's save of the setting is lost on the host, or the modes need a TV or dock condition the host does not report. Their larger output sizes (1440p, 4K) could not show in any case: the game draws at most the size `oe::GetDefaultDisplayResolution` reports, and the host reports a 1080p TV when docked.

## Rendering and memory

The race evaluates DLSS at 960x540 to 1920x1080; the shared MetalFX temporal scaler answers it. The window's captured surface is 3840x2160. Resident memory settled around 6.7–7.0 GB during the first race; GPU allocation about 6.3–6.6 GB, with no sustained growth over the observed interval. On the M6 above, the final run's frame-3000 sample reports frame time p50 34.19 ms (about 29 fps), p95 59.81 ms; GPU time p50 20.30 ms, p95 32.77 ms. This is a diagnostic run with the Metal HUD, shader/pipeline recording and frame captures, not a controlled performance benchmark; the capture at frame 2400 caused a roughly one-second hitch. No performance optimization or comparison against a correctly rendered earlier build is claimed.

## Validation

All 2,976 shaders build on the Mac. The focused graphics/parser suite runs 181 tests with no failures (one optional test skipped), including GPU checks of subword shared stores and synthetic indexed NVN2 texture tables. After rebasing, all 38 documentation, game-profile, chain and environment-switch checks and all 70 Mac packaging tests pass. Python lint adds no findings. The initial broader tool run's environment-switch documentation failure is fixed by current main; its three .NET runtime-selection failures pass when allowed to use the installed .NET 11 runtime.

The broader native graphics suite completes its other targets but fails the clock test's two-nanosecond feedback-conversion tolerance intermittently (`feedback conversion uses the resumed guest epoch`); the same binary passes when rerun alone. The clock implementation and test are unchanged by this port. This broad run is not a clean pass.

Regression level: moderate, because shared shader extraction and translation changed, with the new paths gated by resource signatures or NVN2 instruction/layout semantics. The Binding of Isaac Rebirth is the light original-NVN smoke test: its 19 translated shaders are unchanged, it reaches the same route with no new red log messages, and `regress.py check --quick` passes. The Mac was busy during that run, so its timing differences are not treated as performance evidence. Fast Fusion itself covers the new paths through the title, menus and first race described above.

## Found on this game

- SHN resources and embedded shader objects.
- Subword task and mesh payload accesses.
- [The phone's shaders step fails on a shader that does not build on the Mac either](../../../docs/reference/packing.md#the-phones-shaders-step-fails-on-a-shader-that-does-not-build-on-the-mac-either) (Android, 0.3.50, Forgejo #566): the 62 task and mesh programs, until the profile's `vk_delta.tsv` listed them.
- Indexed texture handles in NVN2 compute c0.
- [The DLSS stand-in wrote alpha 1 over the colour's alpha](../../../docs/reference/rendering.md#the-dlss-stand-in-wrote-alpha-1-over-the-colours-alpha-android) (Android): the main menu showed only the ship; resolved on GSR 2 and FSR 1, open on FSR 3.1.
- DLSS scalers released under their encoders: already fixed before this bring-up; the earlier report reached its eighth network after about nine minutes.
- [A 2D texture in a cube slot binds the zero cube](../../../docs/reference/rendering.md#a-2d-texture-in-a-cube-slot-binds-the-zero-cube) (Android): `vka_tex_id_can_cube` falls back to the cube placeholder for `1x1` 2D placeholders behind cubemap views (`cded8d0899ba4a6d`, `4927a5fe392e5496` at race load on the Android app on the Odin 3, system driver and Turnip v32).
- [DLSS debug overlay setters](../../../docs/reference/rendering.md#dlss-debug-overlay-setters): `nvnDlssParametersSetOverlayDebugLayer`, `nvnDlssParametersSetOverlayFullScreen`, `nvnDlssParametersSetOverlayJitterDebug`, and `nvnDlssParametersSetOverlayShowNans` implemented as no-ops (Android app on the Odin 3, system driver and Turnip v32).
- [Shin'en engine runs at half speed under a 30 fps cap](../../../docs/reference/frame-rate.md#shinen-engine-runs-at-half-speed-under-a-30-fps-cap): fixed `1/60 s` step requires `eFrameskipType` `odd` at 30 fps (0.97–1.03× speed on the Android app on the Odin 3, system driver and Turnip v32).
- [NVN2 draws with 32 vertex attributes](../../../docs/reference/rendering.md#nvn2-draws-with-32-vertex-attributes-android) (Android): `BindVertexAttribState` with `n=32` recorded and replayed on Android Vulkan (Android app on the Odin 3, system driver and Turnip v32).

## Open

- Later courses, a complete race, multiplayer, online modes and frame generation have not been tested.
- The log still reports an unbound vertex uniform slot in the startup effect (`eb5ec3e356bf7ad1`, slot 1), two unimplemented DLSS overlay setters called with zero, and a cube view of a one-face texture. Their effects outside the tested route are not established; none was hidden with a profile switch or stub.
- Android, GRAPHICS modes: they have no effect on the phone right now, and more testing is required. Not established: whether the menu shows the live mode rather than the stored choice, whether the game's dynamic resolution scales the higher modes back down on a phone, and whether the choice is kept once the game saves; the higher modes' output sizes also need the host to report a larger TV when docked, which it does not ([Graphics on Android](#graphics-on-android)).
- Android: `nvnCommandBufferSetProvokingVertexMode` is not implemented (logged once); shader `cded8d0899ba4a6d` reads unbound textures at binding 8 at race load; on Turnip one pipeline was still made on the frame path after prewarm (6.9 ms).
- No on-device iOS validation. The app's icon is absent because the supplied NUP carries none.
