# Updates

How the app updates itself, what happens to your game's shaders afterwards, and where updates come from. Updates come only from the project's official releases.

## Updating the app

Since v0.1.4 the app offers a newer release at start (**Update** or **Later**), downloads it from the project's [releases](https://git.eden-emu.dev/moceure/BananaNative/releases) and installs it after you confirm. Settings > **Updates** > **Check for updates** checks at any time. Updates download from the official site only.

An update keeps the app's storage, so your saves, packs and copied games stay.

### Back up saves before updating

Settings > **Updates** > **Back up saves before updating** (on by default): before an update installs, the app copies every save that changed since its last backup to `save-backups/<title ID>/` next to your games, outside the app's storage, and says how many games it backed up. Saves that did not change, and games never played, are skipped. A save of a game that is running is skipped too, and named. When a backup cannot go outside the app's storage (All files access is off, or a game copied into the app or a `.nup` used where it is), the app says so before updating and offers **Open settings**, **Update without backup** or **Cancel**. If a backup fails, it names the game and the reason and offers **Update anyway** or **Cancel**. Backups are never deleted by the app.

### Update channels: Stable and Hotfix

Every release says what kind it is in its notes: **major** (the weekly release with new things, the default), **hotfix** (a small fix between weekly releases, optional) or **critical** (a small fix everyone should take). Settings > **Updates** > **Update channel** decides which releases the app offers:

- **Stable:** the weekly releases and critical fixes. Small fixes are skipped; the next weekly release always carries every small fix before it, so nothing is lost.
- **Hotfix:** every release, also the small fixes between the weekly ones. Pick it when a fix you are waiting for comes out as a hotfix.
- **Preview:** everything on Hotfix, plus early builds of bigger changes (a new shader version, a large engine change) about a week before they reach Stable. A preview may break a game: pick it only if you want to test, and report what you find. Preview releases are tagged `vX.Y.Z-preview`; the release X.Y.Z that follows is offered to you as a normal update. Leaving Preview takes you back at the next weekly release; your saves stay as they are.

The app also tells you which kind it is: a **Preview** or **Hotfix** chip beside the logo on Home, and a line under **Update channel** in Settings > **Updates** (a weekly release shows neither). A preview moves you to the stable release of the same number when it ships, whatever channel you picked.

The check at start and **Check for updates** both follow the channel. When an update of your channel is waiting (you tapped **Later**), Home's Settings button shows a dot until you open Settings, and **Check for updates** names the version there; a critical fix keeps its dot until you install it. When another channel has something newer, the **Update channel** row names it (for example "v0.3.51 is out on the Hotfix channel"); nothing changes until you pick that channel. The **Update channel** list shows, under each channel, what it offers and the version it would bring you now (after the app's check at start). Picking **Preview** asks first. When the channel you pick has a newer version, its release page opens right away, so you read what it is before you tap **Update**; **Later** keeps the new channel without installing. Release pages say **Small fix** for a hotfix, **Preview build** for a preview and **Important fix** for a critical fix. On Stable, when only a newer small fix is out, **Check for updates** says so and names its version. **Stable is the default.** If you never changed the older **Small fix updates** switch (0.3.42 to 0.3.45), you are on Stable from this version on. If you did change it, the app keeps your choice: on is Hotfix, off is Stable.

Going back to an older version is not offered in the app: Android installs an older version only after the app is uninstalled, which removes the app's storage (your saves and packs) unless you back up the saves first. See [Going back to an older version](Going-Back-to-an-Older-Version), and the release notes of each version for what changed.

## After an app update

A new version may come with new shaders. What you see depends on what changed:

- **No shader changes:** the pack's shaders are taken over at once.
- **Some shaders changed:** the card says **Ready · updating shaders ...** with the count and time left. Only the changed shaders are translated, in the background, from your dump on the phone, and you can keep playing with the old shaders meanwhile. Pause stops it. When more than a quarter of a game's shaders changed and the game plays on its older shaders, nothing starts by itself: the card says **Ready · update** and the game's page offers the update (below).
- **A quick check first:** when an update changes how shaders are made, the app first checks a sample of a game's existing shaders in the background. If they come out the same, nothing is rebuilt and a short **Shaders up to date** note appears. While it runs, the game's tile shows a small ring and its page has a **Checking shaders** card with a bar and **Skip**. A skipped check is not asked again for 7 days (or until the app updates); the page then shows **Shader check skipped**, and tapping it checks again. The game plays throughout.
- **The app cannot update them itself:** the card says **Ready · update** and the game plays as before. Open the game's page: a small **Shaders can be updated** row has an **Update shaders** button (or its button reads **Prepare shaders**, or **Storage > Prepare again**). The update is optional. A pack made on a computer can be made again there and imported instead ([First start and Prepare](First-Start-and-Prepare)).
- **A small optional row (0.3.40):** when your pack's shaders come from an older version of the app that this version still plays, and the game is a Switch 2 title, the game's page shows a small row, **Shaders: older, built while playing**, with **Update shaders** and **Not now**, instead of the big card (also when the older shaders come from other shader tables). **Not now** hides it for that game until the shaders change again. The game plays either way.

- **Game code updates keep your shaders:** when only the game's code needs rewriting (**Ready · game code update ...**, or **Prepare again**), the app rewrites the code and keeps the pack's shaders. If those shaders are from an older version, Prepare asks first: **Prepare again** rewrites the code only, and **Also build all shaders now** is there, recommended for smoother play. You can play right after the code is done.

Building shaders is always your choice while the game can play without them (on its older shaders, or building them as you play). Only a game with no shaders it can play, and no live shader building for it, needs them first (**Shaders needed**).

Shader updates can take a long time on a phone for games with many shaders (for example all 8,161 of Pokémon Pokopia `0400A3A01EE4C000` in the worst case); keep the phone charged.

## Shaders built while you play (0.3.40)

A game that asks for a shader your pack lacks gets it built on the phone while you play, with a **Building shaders (N)** label. See [Live shader building](Live-Shader-Building).

## What is new in 0.3.50

[Release notes](https://git.eden-emu.dev/moceure/BananaNative/releases/tag/v0.3.50). The first weekly release, a major update: install it over any earlier version or update in the app. Games, packs, saves and settings are kept. Shaders do not change; the app rewrites each game's code once in the background (**Ready · game code update ...** on the card; the game plays meanwhile).

- **Update channels:** Stable (the default), Hotfix and Preview ([above](#update-channels-stable-and-hotfix)). The channel list shows what each would bring you now; a dot on Home's Settings button tells you an update waits.
- **Saves backed up before every in-app update** ([Back up saves before updating](#back-up-saves-before-updating)); new page [Going back to an older version](Going-Back-to-an-Older-Version).
- **Startup log off by default:** one "starting…" line until the first frame; Settings > Display > Show startup log brings the log back.
- **Rename game** in a game's long-press menu on Home; Traditional Chinese for the launcher; shortcut icons use the game's cover.
- **Fixes:** a crash on Qualcomm's driver with Classic render passes on; saves written safely before they replace the old one; one task per game; frame generation, in-game menu, controller and packing changes from this week's pull requests.
- **Known issues:** Ocarina of Time is slow on Turnip drivers; Mario Kart World: play on Turnip.

## What is new in 0.3.44

[Release notes](https://git.eden-emu.dev/moceure/BananaNative/releases/tag/v0.3.44). A major update: install it over v0.3.43 or update in the app. Games, packs, saves and settings are kept. Your shaders are taken over as they are (the shader update is optional); the app rewrites each game's code once in the background (**Ready · game code update ...** on the card; the game plays meanwhile).

- **Pokopia native 4:3** (v2.0.1): Game settings > Aspect ratio > **4:3 (native)** ([Pokopia](Game-Pokemon-Pokopia)). Tested by its author only.
- **Donkey Kong Bananza:** the gameplay camera fills screens wider than 16:9 ([Donkey Kong Bananza](Game-Donkey-Kong-Bananza)).
- **Mario Tennis Fever:** a 30 fps cap keeps full game speed ([Mario Tennis Fever](Game-Mario-Tennis-Fever)). Tested by its author only.
- **GPU clock floor** through KGSL on Qualcomm phones. Tested by its author only.
- **Shaders:** shorter compiles for shaders built from now on (mostly Pokopia); compute shaders made in the background; prewarm list per GPU driver; prewarm skips a compile that did not finish before.
- **Fixes:** host services and NVN fixes, game code rewriter fixes, clearer message for a damaged `.nup` part, Ukrainian wording, Linux builds.
- **Switch 1 profiles** for several more games (community, not tried by us).
- Not tried on a phone yet: the latest host-service and rewriter changes and the release APK itself.
- **Known issues:** Mario Kart World on Turnip can lose the GPU after some minutes; Ocarina of Time on Turnip V39 can turn white, then green, after loading.

## What is new in 0.3.43

[Release notes](https://git.eden-emu.dev/moceure/BananaNative/releases/tag/v0.3.43). A major update: install it over v0.3.42 or update in the app. Games, packs, saves and settings are kept and nothing needs to be Prepared again.

- **Languages:** Korean, Ukrainian, German and Italian join the app's own language list (machine translated; tell us if a line reads wrong).
- **Screen scaling** (a game on the DLSS stand-in): Bicubic, SGSR 1 (default) or the device's own; see [Settings: Performance](Settings-Performance#upscaler).
- **Fast FP16** (Turnip drivers only, off by default): faster shader math; see [Settings: Performance](Settings-Performance).
- **Hide everything (clean picture):** one tap hides the controls and overlays ([The in-game panel](Side-Panel-In-Game)).
- **Pokopia Screen shape:** the world and the UI are laid out for your screen's shape ([Pokopia](Game-Pokemon-Pokopia)).
- **RAM saver: Strong** level, and a `[mem] rss:` log line with the app's RAM by category ([Settings: Performance](Settings-Performance)).
- **Games:** 60 fps caps and locks for several games, a Welcome Tour profile, Castlevania: Belmont's Curse no longer crashes at boot, and Donkey Kong Bananza takes the nearest size when its dynamic resolution lands between two.
- **Fixes:** Prepare works on exFAT, SD card and USB storage; save Back up, Restore and Import use the user the game starts with; audio keeps playing when another app makes sound, and no longer goes silent after a permanent focus loss on a dual-screen device; Pokopia add-ons (DLC) link when they sit beside the `.nup`; Fire Emblem: Fortune's Weave refuses a wrong RomFS and names the version needed.
- **Known issue:** Mario Kart World on Turnip can lose the GPU after some minutes ([Mario Kart World](Game-Mario-Kart-World)).
- Not tried on a phone yet: Screen scaling, Fast FP16, clean picture, Screen shape, the new frame caps, the languages, audio focus, exFAT Prepare and save import.

## What is new in 0.3.41

- **Fix:** Prepare stopped at "Finding the shaders" with `No module named 'pack_dump'` for games with add-ons (Ocarina of Time, Donkey Kong Bananza, others). Prepare again; nothing else needs doing.
- **Fix:** button prompts show pictures again instead of "?".
- **Fix:** with no game added, the **+** (Add game) button now stays on Home.
- **Home:** a layout choice (row, grid with names, list), an options menu for each game (hold it, or **X** on a controller: Move, Set cover image, Remove game), your own cover pictures with a crop screen, a hint strip at the bottom ([Playing](Playing)).
- **Pokopia (experimental):** Online events, Mods, Host a world ([Pokopia](Game-Pokemon-Pokopia)).

## What is new in 0.3.40

- **Shaders are built while you play**, and Prepare can skip them: [Live shader building](Live-Shader-Building). After an app update a quick sample check can keep your old shaders.
- **A new launcher look** (Switch 2 style): a row of game tiles on Home with a dock, a game page with Play in its top bar, Settings as a list of sections (wide screens: sections at the left, one at the right), a progress ring on a tile that is being prepared. Settings > Appearance > Language picks the app's language (Spanish, Turkish, Chinese, French, Arabic and Polish were machine translated and not yet reviewed).
- **Order of the games**: hold a game on Home, then Move left or Move right ([Playing](Playing)).
- **Ocarina of Time**: sliders for draw distance, model detail, shadow range, foliage distance and fog at the cut, live in the in-game panel ([Ocarina of Time](Game-Zelda-Ocarina-of-Time)); Keep cave walls switches live too.
- **Mario Tennis Fever**: an extended view for wide screens ([Mario Tennis Fever](Game-Mario-Tennis-Fever)). The frame-skip speed fix is not in this version.
- After this update every game asks to be **Prepared again**. This is the short code step only, because the game-code rewriter changed: shaders are not rebuilt in full (your existing shaders are kept or checked, missing ones are built while you play), and saves and settings are kept.

## Release history

The project's release notes are on the releases page. A short list is in the repository's `docs/players/history.md`.

## Safety

Download the APK only from the official releases page. Nobody connected to the project will ask for money, keys or game files.
