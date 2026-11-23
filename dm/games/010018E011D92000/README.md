# Pokémon Shining Pearl (`010018E011D92000`)

Update 1.3.0 (v393216) over the base game. Unity 2019.4.27f1 IL2CPP, SDK 11.4.3, NVN. Pokémon Brilliant Diamond's twin ([0100000011D90000](../0100000011D90000/README.md)): the same engine and the same `subsdk0` (NintendoSDK_movie) and `sdk` builds; only `main` is a build of its own (`38f59cbd…`, Brilliant Diamond's is `94ceae32…`). Everything in Brilliant Diamond's note about the engine, its memory, files and shaders holds here; this note gives only what differs or was checked again. The profile is Brilliant Diamond's with Shining Pearl's title, name, build row, marker file and shader tables. Made by Peanuts Native (igawa6/peanuts-native) on Linux for Android, where it reached play on an AYN Thor; not built for the Mac or iOS, and not run with this tree's build.

## What it needs

The same keys as Brilliant Diamond's profile, for the same reasons ([Brilliant Diamond, What it needs](../0100000011D90000/README.md#what-it-needs)). The SDK node area cut comes with the `sdk` build (`2d369d99…`, `dm/tools/sdk_patches.py`).

- `romfs_marker`: the ending movies are under `Movie/pea`, not `Movie/dia`.
- `fps_target 60`: Unity's `Application.targetFrameRate` is at the same place as in Brilliant Diamond's `main` (the setter at `main+0x5fa630` stores at `main+0x4afc868`, read from this build's code), so `dm/host/hle_fpslock.c` has a row for this build with the same offset.

No `patches.py`.

## Files and shaders

- Shaders: 14,441, the same content keys as Brilliant Diamond's. The 14,430 in the RomFS are at the same places; the 11 in `main` are at other offsets, so the map is this game's own (`shader_split.py` on this game's files). The facts and pairs tables come from the same run.

## Open

- Only a first run to play on the AYN Thor (Peanuts Native): the 60 fps row, memory and the later routes are not checked separately from Brilliant Diamond's.
