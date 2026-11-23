# The Legend of Zelda: Ocarina of Time (`0400486024DEC000`)

Experimental. It plays, and the foliage is drawn on every driver. The first start is slow because the GPU driver builds its pipelines as it meets each shader; later starts are faster. Kokiri Forest runs at about 26-30 fps on Qualcomm's driver, and indoors about 50. The profile recommends a short list of settings that the app applies automatically.

<!-- TODO screenshot: Ocarina of Time gameplay (the gallery file shows Pokopia) -->

## At a glance

| | |
|---|---|
| Status | Experimental |
| Version | 2.0 (only version 2.0 is tested; other versions get a warning, and you can try them) |
| Frame rate | The game's own limit is 60 fps. About 30 fps in Kokiri Forest on Qualcomm's driver and about 50 indoors; Castle Town on Turnip is slow on its first visits |
| Driver | System (Qualcomm) recommended when its version is 0x80320000 or newer; Turnip also works |
| Game-specific settings | Resolution presets, Draw distance, Fog at the cut, Shadow range, Foliage distance, Model detail distance, Full vegetation, Max resolution, Texture pool x2, Unlocked frame rate, Keep cave walls, Aspect ratio, Cheats |

## Slow first starts

The GPU driver builds its pipelines the first time it sees each shader. The first start can sit on the loading screen for minutes, and the first minutes of play (especially right after the main menu) can run at 1-20 fps with black frames while it catches up. Let it run, or restart the game: each start is faster, and once the cache is full it runs at 30-60 fps. A hot phone makes this slower. Changing the GPU driver starts the cache again for that driver. See [First start and Prepare](First-Start-and-Prepare).

## Recommended settings

Tap **Recommended** at the top of the game's page. On Qualcomm phones it selects the system driver (from driver version 0x80320000), the **Performance** resolution preset and **Full vegetation** off. Older Qualcomm drivers get no driver recommendation: two players with an AYN Thor (Adreno 740, driver 0x802a4035) crashed on the system driver and Turnip worked there.

## Settings that matter for this game

| Setting | What it does | When to toggle | What to expect | Default |
|---|---|---|---|---|
| Resolution | One setting, three choices, in Game settings and the in-game Display tab. **Quality**: window 1920x1080, the game's own dynamic resolution. **Balanced**: 1920x1080 window, fixed 1280x720 scene. **Performance**: 1280x720 window, fixed about 960x540 scene. | Quality if your phone has GPU headroom; Performance otherwise. | The window changes at once; the 3D scene at the next start. In Kokiri Forest on an Adreno 840 and the system driver the GPU time was 42.7 ms at Quality and 39.0 ms at Performance, so the scene size is not the main cost. | Performance (until you choose) |
| Keep GPU clock up | Keeps the phone's system from lowering the GPU's top clock in a menu (game page, Performance tab, Speed). | The game starts play at 20 fps after the main menu and stays there, while other starts run at 30 (seen on an AYN Odin 3, Qualcomm's driver, 1 start of 6). | Fixes that case; the phone runs warmer in menus. Not recommended automatically: no fact the driver reports tells such a phone apart. | Off |
| Draw distance | Caps how far the game draws (Long 300, Medium 150, Short 80, Very short 40). A live slider in the in-game Performance tab and a row under Game settings > Advanced. | When a field or town is slow. | The biggest saving of the four: about 2,600 objects drawn a frame at Auto against about 1,400 at Medium in one field walk. Far scenery is cut off and appears as you walk; fields show a plain horizon. | Auto (the game's own) |
| Fog at the cut | With a Draw distance set, pulls the game's own distance fog in so the cut ends in haze: Off, Light, Medium or Strong. Live slider (Auto is off). | When a short Draw distance shows a plain line at the horizon. | Light: the hard horizon band becomes a fade into the sky. Medium and Strong: thicker haze from nearer, distant hills bluish; reflections are fogged too. Tried at distance 100 on one phone; not checked on every area, driver or cutscene. | Auto (off) |
| Shadow range | Shortens the moving shadows (Long 500, Medium 200, Short 100, Very short 50). Live slider. | When it is slow. | About 10 to 20 % fewer objects at Short and Very short. Distant shadows stop at a line at the short values. | Auto |
| Foliage distance | Grass, bushes and small trees end at 75, 50 or 35 % of the game's distance. Live slider. | In vegetation-heavy places. | Not measured to lower the object count yet. | Auto |
| Model detail distance | Models switch to simpler versions nearer (0.75, 0.5, 0.3). Live slider. | In towns and fields. | Does not lower the object count; any gain would be GPU time and is not confirmed. | Auto |
| Full vegetation | Turning it off removes some grass and foliage at the next launch. | On Qualcomm phones for speed. | In one comparison, 41.0 ms against 42.7 ms of GPU time. Foliage density changes visibly. | On in the app, off in the recommendation |
| Max resolution | Keeps the 3D scene at full size: sharper, more GPU work. Best with Quality. Switches on Texture pool x2. | If you have headroom. | More memory and GPU work. | Off |
| Texture pool x2 | Twice the game's starting graphics memory. Max resolution needs it. | With Max resolution. | More memory. | Off |
| Unlocked frame rate | Game logic follows real time, so speed holds when fps changes. Does not raise fps. | If the game runs slow when fps drops. | Not a speedup. | Off |
| Keep cave walls (Qualcomm) | Fixes walls and rocks that vanish on Death Mountain Trail with Qualcomm's driver. | If you see holes. | Costs GPU time on some phones. | Off |
| Frame rate cap (in-game panel) | 60 or 30. | 30 is steadier and cooler. | Measured in Link's house on Qualcomm's driver: 30.0 fps, frame time 33.3 ms, phone 51 to 62-64 degrees C over a run, where uncapped it ran 37-38 fps. | 60 |
| Aspect ratio | 21:9, 4:3, 10:9, 1:1 and Screen shape. | For a wide or square screen. | The 3D view fills the picture. The HUD, menus and movies stay in the middle 16:9; some pages (the journal's tapestry pictures) show extra edge content at 1:1. | 16:9 |
| Cheats | Rupees 999, ammunition and items 99, Gold Skulltula tokens 100, infinite health and magic (experimental). | If you want them. | Not phone-checked yet in the notes. See [Cheats](Cheats). | Off |

<!-- TODO screenshot: Game settings page of Ocarina of Time (Resolution presets and Game options) -->

Max resolution, Texture pool x2 and Unlocked frame rate patch the game's code, so after switching them on the app may say "Needs Prepare again". The distance rows and the fog row also need the game prepared with this version: a game prepared earlier shows "Needs Prepare again" once.

The distance sliders (and Fog at the cut) are independent: each changes only its own value, and none adjusts another. They are new and measured on one phone only; the phone warmed up during the tests, so frame-rate figures moved between runs. Tell us what you see on yours.

## Known issues

- **Cave walls and rocks can vanish** on Death Mountain Trail on Qualcomm's driver. Turn on **Keep cave walls**.
- **Castle Town** on Turnip is slow on its first visits (open in the notes).
- **Frame rate** in Kokiri Forest on Qualcomm's driver is about 26-30 fps; on Turnip V39 Patched the same spot ran 18 fps (GPU 53 ms) in the same test. The notes call the game GPU-bound.
- Other Qualcomm drivers: on 891.11 and 891.14 versions 16-49 % of draws were skipped in one test (foliage compute).
- **Crash at the opening with a phone language the game lacks** (Thai; [#290](https://git.eden-emu.dev/moceure/BananaNative/issues/290)): in 0.3.40 the game is given only a language it ships. Not run on a phone yet.
- **Crash with a bus error (SIGBUS) on a Snapdragon 888** ([#343](https://git.eden-emu.dev/moceure/BananaNative/issues/343)): the game does an atomic add on an odd address that older cores cannot do; 0.3.40 does it in software. Checked by a unit test only, not run on a Snapdragon 888.
- **Crashes after a while on some phones** ([#265](https://git.eden-emu.dev/moceure/BananaNative/issues/265), [#338](https://git.eden-emu.dev/moceure/BananaNative/issues/338), [#346](https://git.eden-emu.dev/moceure/BananaNative/issues/346), [#349](https://git.eden-emu.dev/moceure/BananaNative/issues/349)): the process ran out of memory areas. 0.3.40 pauses background shader building from half of the limit; this should help and is not proven.
- Frame generation and 60 fps: see [Getting higher FPS](Getting-Higher-FPS).
