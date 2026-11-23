# Fast Fusion (`040041E0212AE000`)

Fast Fusion is in bring-up on the phone. On the tested phone it plays the title, the menus and races at about 60 fps, on the system driver and on Turnip. It has been tried on one phone only, so treat everything here as early results.

<!-- TODO screenshot: Fast Fusion race -->

## At a glance

| | |
|---|---|
| Version | update 262144 (the package the profile was made for) |
| Result so far | Title, menus and races on the AYN Odin 3 (Adreno 830), on the system driver and on Turnip v32. Not tried on other phones |
| Frame rate | About 60 fps in races on the tested phone: about 14.5 ms of GPU time per frame in Docked (1080p), about 12.3 ms in Handheld (720p) |
| Memory | Up to about 5.5 GB on the system driver and 7.5 GB on Turnip on the tested phone (24 GB). A phone with less than 10 GB gets a warning; smaller phones are not tested |
| Driver | Both the system driver and Turnip v32 start and play it ([GPU drivers](GPU-Drivers)) |
| Package | A `.nup` holding the update only (no base package, name or icon) |

## What to expect

- **First Prepare:** the game has about 2,976 shaders. 62 of them (its mesh and task programs) are not built; the game did not use them on the tested route. Let Prepare finish with the phone charged ([First start and Prepare](First-Start-and-Prepare)).
- **First start without a shader library:** the app ships a starter set of 391 shaders ([Live shader building](Live-Shader-Building)). Until they are built, the picture can stay black for the first route.
- **Picture:** the game draws its 3D scene smaller than the screen and the app scales it up with a stand-in for the console's DLSS: 960x540 to 1080p in Docked, 640x360 to 1080p in Handheld.
- **Bring-up warning:** the app shows a warning before every start, as for every game in bring-up.

## Settings that matter for this game

Common settings are in [Settings overview](Settings-Overview).

| Setting | What it does | When to toggle | What to expect | Default |
|---|---|---|---|---|
| **Resolution** | Two choices: **Docked (1080p)** and **Handheld (720p)**, the console's two modes | Handheld if the GPU is short of time | Handheld saves about 2 ms of GPU time per frame on the tested phone; the picture is softer | Docked (1080p) |
| **Upscaler** | Picks what enlarges the 3D picture: the DLSS stand-in's choices GSR 2, FSR 1, FSR 3.1 or Bilinear ([Settings Performance](Settings-Performance)) | If the picture looks too soft, or to save GPU time | Cost per choice is not measured yet | GSR 2 (smooth) |

The game's own **Options**, **GRAPHICS** (PURE, PERFORMANCE, BALANCED, QUALITY, ULTRA QUALITY) has no effect on the phone yet: every mode looks and runs the same as PERFORMANCE, and the menu shows PERFORMANCE again when it is opened again. Leave it on PERFORMANCE.

## Known issues

- The game's own GRAPHICS modes have no effect right now and do not stay set (see above). More testing is required.
- Tested on one phone only. Phones with less memory and other GPUs are not tried.
- Online play is not tested.
- If something goes wrong, please open an issue with the log ([Troubleshooting](Troubleshooting)).

More games: [Games](Games). Phones that were tested: [Tested devices](Tested-Devices).
