# Hyrule Warriors: Age of Imprisonment (`04003F40232DE000`)

Hyrule Warriors: Age of Imprisonment is in bring-up on the phone. On the tested 16 GB handheld with Turnip it plays the initial settings, opening VP9 movie, realtime intro cutscene and the first 3D forest field at 52-56 fps. Later combat stages, autosave reload and Qualcomm's system driver have not been tested yet, so treat these numbers as early bring-up results.

<!-- TODO screenshot: Hyrule Warriors: Age of Imprisonment first field -->

## At a glance

| | |
|---|---|
| Version | update 196608 (NUP container with update only, 47 GB) |
| Result so far | Initial settings, opening VP9 movie, intro cutscene (46.6 fps) and first playable 3D forest field (52.3-55.7 fps) on an AYN Thor (Adreno 740, 16 GB, Android 13) on Turnip 27.0.0-devel |
| Frame rate | 59.8 fps in menus and the opening VP9 movie, 46.6 fps in the intro realtime cutscene, 52.3-55.7 fps in the first 3D field (GPU busy 16.10-17.57 ms) |
| Memory | 6.85 GiB PSS / 6.96 GiB RSS in the first field on the tested 16 GB handheld (5.90 GiB MemAvailable). Phones with less than 12 GB get a required memory warning; under 16 GB gets a degraded memory notice |
| Driver | Tested on Turnip (`Mesa 27.0.0-devel`, Vulkan 1.4.363) only ([GPU drivers](GPU-Drivers)); Qualcomm's system driver is not tested yet |
| Package | A `.nup` holding the update only (47 GB, no NACP or icon; `readiness.tsv` notes 160 compute shaders in the full archive request up to 48,128 bytes of shared memory) |

## What to expect

- **Large shader archive:** the full game contains 101,860 shaders (0 mesh or task programs), so an initial full Prepare takes time ([First start and Prepare](First-Start-and-Prepare)). From boot through the first 3D field, 15,449 shaders were seen (`shader_seen.tsv`); none of those require more than 14,896 bytes of compute shared memory, while 160 compute shaders later in the archive ask for up to 48,128 bytes.
- **Saves:** the game keeps a single flat 8 MB `DATA.BIN` save file, created at first boot and updated at autosave points (the opening and first field walk reach no autosave write point yet).
- **Bring-up warning:** the app shows a warning before every start, as for every game in bring-up.

## Settings that matter for this game

Common settings are in [Settings overview](Settings-Overview). No game-specific presets are defined for `04003F40232DE000` yet; tests ran at `1920x1080` with Turnip.

## Known issues

- Combat stages, later missions and mid-stage autosave write/reload have not been reached yet on Android.
- Qualcomm's own system driver and phones with less than 16 GB RAM have not been tested yet.
- If something goes wrong, please open an issue with the log ([Troubleshooting](Troubleshooting)).

More games: [Games](Games). Phones that were tested: [Tested devices](Tested-Devices).
