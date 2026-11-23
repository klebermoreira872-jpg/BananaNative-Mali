# The in-game menu

The in-game menu is a drawer that slides in from the left over a running game, with the game going on behind it. Its left side is a menu: the game's name and GPU driver, **Pause the game** (**Resume the game** while the game is paused), the four sections **Performance**, **Display**, **Controls** and **General**, and **Stop the game**. Pick a section and its settings show to the right of the menu, in the same drawer; the menu marks which section shows. On a phone held upright the section takes the menu's place. Almost every change applies at once and is kept for the next start. The only exceptions are marked "next start".

<!-- TODO screenshot: the in-game menu open over a game, Performance section -->

## Open and close it

| Action | Opens | Closes |
|---|---|---|
| The phone's Back (button or edge swipe) | the menu | one step back: from a section to the menu, from the menu to the game |
| A controller: Home, or hold - and + for half a second (Settings > Controller: in-game panel changes this) | the menu | the same again; the controller's B goes one step back |
| Swipe in from the right edge | the last section | |
| A long press on the on-screen controls' show / hide button (top centre) | the last section | |
| A tap beside the drawer | | yes |

A hint at the right edge shows how, once after install. With a controller: in the menu, up and down move the yellow pill and A (or right) picks; in a section, the D-pad or left stick moves the focus, left and right step a slider or radio group, A presses, B goes back to the menu, L and R switch sections; a yellow frame marks the focused row.

## The four sections

### Performance
- **Frame rate cap**: the same choices as on the game page ([Settings: Performance](Settings-Performance#frame-rate-cap)), applied now. A game's frame limit list is 60, 45, 40, 30, 20 fps; other games: The game's own, 60, 30, 20, 15 fps.
- **Full game speed at low frame rates** (games whose speed follows their frame rate) and **Hold 60 fps: never drop to 30, no frame holds** (Mario Kart World).
- **Upscaler** (and **FSR sharpness**): for a game whose upscaler the app replaces, or a game on the DLSS stand-in (its own modes and sliders); applies from the next frame. Hidden for a game with Resolution presets unless Settings > Help > Tester settings is on.
- **Game upscaler (DLSS)** and right under it **Screen scaling** (with **Screen sharpness** under FSR 1): a game on the DLSS stand-in (Fire Emblem: Fortune's Weave, Star Fox, Fast Fusion). The first turns the game's 3D picture into its frame, the second scales that frame to your screen; the same choices as on the game page.
- **Upscaling quality** and **Graphics quality** (Fire Emblem: Fortune's Weave), under the Upscaler.
- **Dynamic resolution**: a slider from Off to 30 % (Donkey Kong Bananza).
- **Frame generation**: the on switch, target, multiplier and motion estimation resolution ([Settings: Performance](Settings-Performance#frame-generation)).
- The game's own **live** switches, if its profile has any. Ocarina of Time has four sliders here, each starting at Auto: **Draw distance**, **Shadow range**, **Foliage distance** and **Model detail distance** ([the game's page](Game-Zelda-Ocarina-of-Time)). They apply at once and are saved for the next start.

The live lines in this section (the frame rate now) refresh twice a second while it shows.

### Display
- **Resolution**: the same choice as on the game page. For some games the window changes at once and the 3D picture at the next start; a line says which. Fire Emblem: Fortune's Weave shows Resolution alone here (its Upscaling quality and Graphics quality are on Performance).
- **Picture**: **Fit** or **Stretch**, **Size** 50 to 100 % in 5 % steps (the picture shrinks with its shape kept and black around it), and **Position (this screen)**: Top, Centre, Bottom.
- **Overlay**: the master switch and one switch per item.

### Controls
- **Controllers > Player 1** (while a gamepad is connected).
- **On-screen controls**: Auto / On / Off, opacity, size, vibration on press, the log, the show / hide button, **Reset the controls**, **Edit the controls layout…**.
- **Rumble (the game's vibration)**.
- **Motion sensitivity**: a slider, Slower to Faster.
- **Next start**: the game's own switches that need a restart, and **Button mapping** (a shortcut to the game's mapping; it applies at the next start).

See [Settings: Controls](Settings-Controls).

### General
- **Panel**: **Size** and **Text size**, each Small / Normal / Large, for every game, applied at once.
- **Cheats** (only for a game with cheats and with Game settings > Cheats on): one switch per cheat, grouped by section, live. See [Cheats](Cheats).
- **Hide everything (clean picture)**: one tap hides the stats, the build tag, the log, the on-screen controls and the panel's edge strip, for a clean screenshot or recording. The panel still opens with Back, a controller or the controls' top-centre button, where the same button reads **Show everything** and brings back what you had before (a log that was off stays off). Kept for the next start. (From a contribution by racerx.)
- **Pause when the game comes back from the background** (on by default): coming back from another app shows the game paused until a tap.

### In the menu
- **Pause the game**: freezes the game until you tap the screen (or press A or Start on a gamepad), or pick **Resume the game** in the menu. While paused, the game's clock, graphics, threads and audio are suspended.
- **Stop the game**: asks "Stop the game?"; unsaved progress is lost, and the log stays for **Share log**. A game that has not saved keeps its progress only in memory, also while paused or in the background, so stopping it then loses it.

## Notes

- The menu's changes are the same settings as the game page's: a change in one shows in the other.
- If a game was started without live control (a test setting), the rows say the change applies at the next start. A normal start has it.

## Sources

`SidePanel.java`, `PadPanel.java`, `TouchControls.java`, `PanelLook.java`, `Overlay.java`, `Lsfg.java`, `GameUpscaler.java`, `android/README.md` (In-game panel, Pause).
