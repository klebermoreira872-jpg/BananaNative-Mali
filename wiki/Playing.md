# Playing

How to start a game, stop it, start it from a launcher or frontend, and where its settings are. The settings themselves are on their own pages ([Settings overview](Settings-Overview)).

## Start and stop

- Tap **Play** on the game's card once it says it is ready. If something is missing (pack, shaders, file access) the app says so before it starts, with the reason.
- Stop with the in-game panel > **Stop the game** ([Side panel in game](Side-Panel-In-Game)). Stop the game before you back up, restore or import a save.
- Games with a recommendation for your phone show it at the top of their ... page: one tap applies it.
- Game language follows the phone (Polish and Thai too, where the game has them) or can be set per game.

## Settings

- **Options for a game**: press and hold a game on Home (on a controller, hold **X** on it). The menu has **Move**, **Set cover image**, **Rename game** and **Remove game…**. With a controller, a strip at the bottom of Home shows the buttons.
- **Move** lifts the game: move it with the arrows (a grid also moves up and down) or drag it, **A** or a tap puts it down, **B** cancels. The order is kept.
- **Set cover image** picks a picture from your phone and lets you pan and zoom it under a frame (touch, or D-pad to move and the triggers to zoom, **A** confirms). The game's own picture comes back with **Reset cover**. The picture is kept inside the app only.
- **Rename game** gives the game your own name on Home and on its page (up to 60 characters). **Reset name** (in the same menu once you renamed it) brings back the game's own name. The name stays when you add the same game again.
- **Remove game…** takes the game off your list and deletes what the app made for it inside its own storage (the pack and shaders, Prepare's work files, logs, a copy made with Copy into the app, your cover). It first lists every folder with its size and asks. It never deletes your dump folder or a `.nup`, and never a save.
- **Home layout**: Settings > Appearance > **Home layout** picks a row of tiles (the default), a **grid with the game's name under each tile**, or a **list**.
- With no game added, Home shows "Add a game to start" and the round **+** button stays at the bottom right.
- **App language**: Settings > Appearance > Language (the app's own text; the game's language is set per game).
- **Settings** (the gear at the top of Home) holds the defaults for every game: overlay, on-screen controls, resolution, frame rate cap, frame generation, button mapping and more.
- A game's own settings (its ... button: **Performance** and **Game** tabs) override them. See [Settings overview](Settings-Overview).

## Controls

On-screen controls with a layout editor, gamepad support, and phone motion are available; a text box appears for games that ask you to type. Fold-aware layouts switch live between the outer and inner screen of a foldable. Details: [Settings: controls](Settings-Controls).

## Starting from a frontend or home screen

Banana Native starts a game for emulator frontends such as ES-DE, Daijisho, Beacon and Pegasus, which list your `.nup` files and send the one you pick to the app. All files access must be on.

- A game that is ready to play starts at once, with no launcher screen. When you stop it, the frontend comes back.
- If something needs you (no pack, Prepare, shaders to update, file access), Home opens with the game; fix it, then start again from the frontend.
- A game's menu on Home has **Add to home screen**, which pins a shortcut with its name and the game's picture: your own cover if you set one, else the game's own icon, else a plain tile with its first letter.
- Frontends need no change of their own, but until one ships Banana Native in its emulator list you add it once by hand with the component `dev.bananative.android/dev.bananative.android.Launch`. Examples for ES-DE are in the project's FRONTENDS note in the repository (`android/FRONTENDS.md`).

## First starts can be slow

Some games build GPU pipelines the first time they see each shader, so the first start can sit on the loading screen and the first minutes can stutter. Ocarina of Time (`0400486024DEC000`) is the clearest case; each start is faster. See [Games](Games) and [Getting higher FPS](Getting-Higher-FPS). A hot phone makes it slower ([Heat and battery](Heat-and-Battery)).

## Frame generation

Lossless Scaling's frame generation is built in (2x, 3x, 4x, or a target of 60 / 90 / 120 fps), with some added latency. It needs your own `Lossless.dll`, put in `Download/` or picked in Settings > Frame generation. Not included and not provided by the project.

<!-- TODO screenshot: Home with a ready game card -->
