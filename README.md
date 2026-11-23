<p align="center"><img src="android/images/logo.svg" alt="Banana Native logo" width="128"></p>

# Banana Native

Banana Native runs Switch 2 games from your own dumps on Android phones. Like Wine, it emulates no hardware: the
game's own ARM64 code runs on the phone's CPU, Banana Native supplies the system services it calls and translates its
graphics to Vulkan. It is an Android port of [nxnative](https://github.com/seedds/nxnative) by seedds.

> [!NOTE]
> Unofficial and experimental. Not affiliated with Nintendo, nxnative or Eden. The project contains no Nintendo code,
> firmware or keys and decrypts nothing: it reads only a dump of a game you own, made from your own console. Most of the
> code was written with an AI coding assistant (Claude) and tested by hand. [More](docs/players/about.md).

## Games

| Game | Version | Status | Notes |
|---|---|---|---|
| Donkey Kong Bananza (`040074A01BF12000`) | update 458752 | Supported | 30 fps |
| Fire Emblem Fortune's Weave (`04007EF01F8AE000`) | update 131072 | Supported | 30 fps; native 4:3 option; on Adreno 740 pick Turnip |
| Mario Kart World (`0400C3F00006E000`) | 1.8.0 | Supported | a phone cooler is recommended |
| Pokémon Pokopia (`0400A3A01EE4C000`) | update 655360 (Ver. 2.0.1) | Supported | about 60 fps |
| The Legend of Zelda: Ocarina of Time (`0400486024DEC000`) | 2.0 | Experimental | plays on the system driver and Turnip, full foliage; about 30 fps in Kokiri Forest, 50 indoors |
| Star Fox (`0400E88025B1A000`) | update 131072 | Supported | played from start to finish by a player, who reported no problems; frame rate and memory not measured |
| Mario Tennis Fever (`0400D4201C6EA000`) | update 327680 (1.1.1) | Experimental | plays at 60 fps on Turnip on the tested phone; Qualcomm's own driver stalls and shows dark patches on the player intros; a long first Prepare (35,045 shaders) |
| Fast Fusion (`040041E0212AE000`) | update 262144 | Experimental | in bring-up: title, menus and races at about 60 fps on the system driver and Turnip on the tested phone; the game's own GRAPHICS modes have no effect yet |
| Hyrule Warriors: Age of Imprisonment (`04003F40232DE000`) | update 196608 | Experimental | in bring-up: menus, opening movie, cutscenes and the first field at 52-56 fps on Turnip on the tested 16 GB handheld; battles and the system driver are not tested yet |
| Super Mario Bros. Wonder - Nintendo Switch 2 Edition (`040015100B514001`) | update 327680 (1.2.1), program 1 | Experimental | reached a first course at 30 fps on Turnip on one phone; the system driver is not tested; needs a dump with the edition's own program |
| Splatoon Raiders (`0400380020056000`) | update 65536 | Experimental | boots and runs, but not playable yet (very low frame rate) |

The app tells you if your dump is another version. Splatoon Raiders is not playable yet: it boots and runs at a very low
frame rate, and ships so that people can test it and help. Ocarina of Time: only version 2.0 is
tested; the first starts are slow (minutes of loading, then low fps and black frames) until the GPU driver's pipeline cache fills.
Games with a recommendation for your phone show it at the top of their ⋯ page: one tap applies it. Game language follows the
phone (Polish and Thai too, where the game has them) or can be set per game. [Experimental games](docs/guides/experimental-games.md) has their known problems and how to help.

## What you need

- An Android 13+ phone with a Snapdragon (Adreno) GPU and at least 12 GB of RAM, 16 GB for Mario Kart World
  (`0400C3F00006E000`). Tested on a Snapdragon 8 Elite Gen 5 with 16 GB, with the phone's own Qualcomm (system) driver
  and Turnip.
- Your own dump of the game, as a folder (or a `.nup` file of one): `base/`, and `updates/<version>/` and `dlc/` if you
  have them, each with `exefs/` and `romfs/`. XCI and encrypted (retail) NSP files don't work; a plain NSP that NSP Box wrote is read where it is, as a `.nup` is.
- Recommended: a Windows PC or a Mac, and a phone cooler.

## Setup

Each game is prepared once into a **pack** (its code rewritten for Android, its shaders translated for Vulkan). A
computer does this much faster than the phone.

First install the APK from [Releases](https://github.com/moceure/BananaNative/releases) (or the mirror on [git.eden-emu.dev](https://git.eden-emu.dev/moceure/BananaNative/releases)) and allow **All files access**.

**PC (Windows) or Mac** ([guide](docs/guides/pc-mac-packing.md)). Mac: tested. Windows: new and not yet tested on a
real PC — please report how it goes.

1. Download this repository and double-click `scripts\bananative.bat` (Windows) or `scripts/bananative.command`
   (Mac). The first time, it installs its tools (about 400 MB) into a folder you pick.
2. Pick the game (its folder or `.nup` file) and click **Prepare**.
3. Copy the game folder to the phone, and the pack next to it: `<title ID>-work/android-pack`.
4. In the app, tap **Add game** and pick the game folder. It finds the pack. (Or use **Import pack…** with the pack
   folder.)

**Phone only** ([guide](docs/guides/getting-started.md)): copy the game folder to the phone, tap **Add game**, then
**Prepare**. It runs in the background and can be paused; keep the phone on the charger. The first Prepare takes
about 20–45 minutes (mostly translating shaders). Prepare is incremental: later runs reuse existing shaders and
only rewrite code when its key changes (a few minutes). A computer is recommended for Mario Kart World (`0400C3F00006E000`).

## Problems

- Settings › **Readiness check** says what your phone is missing and fixes most items.
- A game's ⋯ button › **Share log** shares its log.
- Open an [issue](https://github.com/moceure/BananaNative/issues/new/choose) with the form; questions go to
  [Discussions](https://github.com/moceure/BananaNative/discussions). More: [Troubleshooting](docs/guides/troubleshooting.md).

> [!IMPORTANT]
> The official places for Banana Native are this GitHub repository and its mirror on
> [git.eden-emu.dev](https://git.eden-emu.dev/moceure/BananaNative): download the APK only from their releases. Nobody
> from the project will ask you for money, keys or game files.

## Guides

[Getting started](docs/guides/getting-started.md) ·
[PC or Mac](docs/guides/pc-mac-packing.md) ·
[Storage access](docs/guides/storage-access.md) ·
[Saves](docs/guides/saves.md) ·
[Packs and app updates](docs/guides/packs-and-updates.md) ·
[GPU drivers](docs/guides/gpu-drivers.md) ·
[Troubleshooting](docs/guides/troubleshooting.md) ·
[Experimental games](docs/guides/experimental-games.md)

## More

[Features](docs/players/features.md) ·
[Performance](docs/players/performance.md) ·
[How it works](docs/players/how-it-works.md) ·
[About the project](docs/players/about.md) ·
[Videos and device reports](docs/players/videos.md) ·
[History](docs/players/history.md)

## Contributing

Each game's note says what is known and what is open ([games table](dm/games/README.md#games)); working on the code:
[docs/agents](docs/agents/README.md), [android/README.md](android/README.md). The experimental games need the
most help: see the issues marked
[help wanted](https://github.com/moceure/BananaNative/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22).

## Contributors

Thank you to everyone whose pull requests are part of Banana Native:

<!-- contributors:start -->
[1982tito](https://git.eden-emu.dev/1982tito), [aidankinzett](https://git.eden-emu.dev/aidankinzett), [Amost-](https://github.com/Amost-), [blasteryui](https://git.eden-emu.dev/blasteryui), [casual-goon](https://git.eden-emu.dev/casual-goon), [Cer0-D](https://github.com/Cer0-D), [cr1stian](https://git.eden-emu.dev/cr1stian), [dopper](https://git.eden-emu.dev/dopper), [drew2388](https://git.eden-emu.dev/drew2388), [endSly](https://git.eden-emu.dev/endSly), [FrenklinFish](https://git.eden-emu.dev/FrenklinFish), [huahuahuahuahuahuahuahua](https://github.com/huahuahuahuahuahuahuahua), [iH8Ecchi](https://git.eden-emu.dev/iH8Ecchi), [inazuma2k8](https://git.eden-emu.dev/inazuma2k8), [ishtiaq156](https://github.com/ishtiaq156), [ligne12](https://github.com/ligne12), [loganrennick](https://git.eden-emu.dev/loganrennick), [lsmsmx](https://github.com/lsmsmx), [miol7s.h](https://git.eden-emu.dev/miol7s.h), [mleo2003](https://github.com/mleo2003), [MOHAMM3DX](https://git.eden-emu.dev/MOHAMM3DX), [nebadasSwifty](https://git.eden-emu.dev/nebadasSwifty), [nevercholt](https://git.eden-emu.dev/nevercholt), [Omnicrash](https://git.eden-emu.dev/Omnicrash), [P1R4N351](https://git.eden-emu.dev/P1R4N351), [parsifal295](https://github.com/parsifal295), [pyrodonkey](https://git.eden-emu.dev/pyrodonkey), [racerx](https://git.eden-emu.dev/racerx), [Raphix91](https://github.com/Raphix91), [sabogalc](https://git.eden-emu.dev/sabogalc), [ts-miller](https://git.eden-emu.dev/ts-miller), [v0lumehi](https://github.com/v0lumehi), [vscunha](https://git.eden-emu.dev/vscunha), [Wick3dPhant0m](https://git.eden-emu.dev/Wick3dPhant0m), [wraphs](https://git.eden-emu.dev/wraphs)
<!-- contributors:end -->

## Licence and credits

The Android app is **GPL-3.0-or-later** as a whole ([android/NOTICE.md](android/NOTICE.md)), because it includes frame
generation ported from [Eden](https://git.eden-emu.dev/eden-emu/eden) / [lsfg-vk](https://github.com/PancakeTAS/lsfg-vk)
and task and mesh shader lowering from [switch2mac](https://github.com/azmasm/switch2mac) /
[Eglantine](https://github.com/djihads80/eglantine). Each release is built from its tagged commit. nxnative's own files
keep their MIT licence ([LICENSE](LICENSE)); third-party code keeps its own ([dm/third_party](dm/third_party/README.md)),
and the shader translator built from it is GPL-3.0-or-later ([dm/third_party/ryujinx](dm/third_party/ryujinx/README.md)).
A few shader translator fixes are adapted from [nx2android](https://github.com/shirai91/nx2android) (MIT), credited in
[android/NOTICE.md](android/NOTICE.md).

Built on **[nxnative](https://github.com/seedds/nxnative)** by seedds (MIT) and everything it credits in its
[acknowledgements](docs/nxnative.md#acknowledgements), among them [d2r-mobile](https://github.com/jhaizhou-ops/d2r-mobile)
and [Ryujinx](https://github.com/Ryujinx/Ryujinx)'s shader translator. Mario Kart World (`0400C3F00006E000`) findings
from [kartnative](https://github.com/pahorema/kartnative) (pahorema) and switch2mac (azmasm). Thanks to all of them and
to everyone who reported issues or sent pull requests.

Only use games you own. Don't ask for games, keys or dumps.
