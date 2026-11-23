# Settings: Advanced

**Settings > Advanced** lists the switches the game host offers, each with a plain name and a line that says when to try it. The same rows appear on a game's page, under **Advanced switches** in its Advanced section, for that game only; the page opens in place of the game page. Every row starts at **Auto**: nothing is written and the app or the game's profile decides. Pick another value only when the row's "Try this if" line matches what you see. A change applies at the next start.

<!-- TODO screenshot: Settings > Advanced with the search box and the area sections -->

## How the page is laid out

Each row has its name, a line "Try this if ...", a line "Auto: ..." that says what happens when you set nothing, and a row of chips: **Auto**, then the values. One tap sets one. A number with a few useful values is also chips; the other numbers open a small box.

- **Search** at the top finds a row by its name, its "Try this if" line or its `DM_` name.
- **Experimental** adds the rows that are not measured on every game, with a warning: they may look wrong or crash.
- **Developer** lists every other switch by area, with its `DM_` name and what it does, and the rows a Settings control already sets. These are for bug hunting; set one when a maintainer asks.
- **Reset all** undoes every row you set. **Back** returns to Settings or to the game's page.
- A line in `env.txt` or in a game's **Extra environment** wins over this page.

Rows you set are written into the log of the next run (`[adv]` lines), so a shared log shows what you changed.

## Rows you may want

### Graphics quality
- **What it does:** the graphics quality of a game with a render configuration (Fire Emblem: Fortune's Weave): Performance or Quality.
- **When to toggle:** Quality when the game looks too plain, Performance when it is too slow.
- **Default:** Auto, which is Performance.

### Render size
- **What it does:** the size the game draws at, as a share of the output its upscaler takes it to: 33, 50, 59, 67 or 100 %.
- **When to toggle:** raise it when the picture is too soft, lower it when the game is too slow.
- **Default:** Auto, which is 50 %.

### Mesh prepass workaround
- **What it does:** draws some depth-only model passes another way, a workaround for spikes and flicker on models with Qualcomm's driver.
- **When to toggle:** when the picture shows spikes or flicker on models.
- **Default:** Auto: on with Qualcomm's driver when its mesh shaders are on (`DM_VK_MESH=1`), off otherwise. Qualcomm's driver draws mesh shaders through compute by default, where this workaround is not needed.

### Draw distance
- **What it does:** Ocarina of Time only. Caps how far the game draws: Long (300), Medium (150), Short (80) or Very short (40). Also a slider in the in-game panel's Performance tab, applied at once.
- **When to toggle:** when a field or town is slow. In one walk through Hyrule Field on one phone the game drew about 2,600 objects a frame at Auto and about 1,400 at Medium. Frame rate rose less and the numbers moved between runs when the phone got hot.
- **What to expect:** far scenery is cut off and appears as you walk, and fields show a plain horizon where the cut is.
- **Default:** Auto, the game's own distance.

### Fog at the cut
- **What it does:** Ocarina of Time only. With a Draw distance set, pulls the game's own distance fog in so the cut ends in haze instead of a hard horizon. Off (Auto), Light, Medium or Strong. Also an in-game slider.
- **When to toggle:** when a short Draw distance shows a plain line at the horizon.
- **What to expect:** Light: the far half of the range fades into the sky's haze. Medium and Strong start the haze nearer and make it thicker: distant hills turn bluish and hazy, and reflections are fogged too. Tried on one phone at distance 100 in Hyrule Field, standing still; not checked on every area, driver or cutscene.
- **Default:** Auto (off).

### Shadow range
- **What it does:** Ocarina of Time only. Shortens the range of the moving shadows: Long (500), Medium (200), Short (100) or Very short (50). Also an in-game slider.
- **When to toggle:** the game is slow in a field or town. It drew about 10 to 20 % fewer objects at Short and Very short in one test.
- **What to expect:** shadows end nearer Link; at Short and Very short distant shadows stop at a line, and the title screen and viewer show a line at any value.
- **Default:** Auto.

### Foliage distance
- **What it does:** Ocarina of Time only. Scales how far grass, bushes and small trees are drawn: 75, 50 or 35 % of the game's distances. Also an in-game slider.
- **When to toggle:** the game is slow where there is a lot of vegetation. Not measured to lower the object count in the first test; tell us what you see.
- **What to expect:** vegetation ends nearer and appears as you walk, with its shadows.
- **Default:** Auto.

### Model detail distance
- **What it does:** Ocarina of Time only. Makes people, buildings and props switch to simpler models nearer: 0.75, 0.5 or 0.3 of the game's distance. Also an in-game slider.
- **When to toggle:** the game is slow in a town or field. It does not lower the object count, so a gain would show as GPU time only; not confirmed yet.
- **What to expect:** distant models look simpler and may change as you walk closer.
- **Default:** Auto.

## Rows for memory and speed

These are in the Advanced group, collapsed. None is measured on every game.

| Row | Try this if | Default |
|---|---|---|
| **Memory pressure guard** | textures reload and stutter although the phone has free memory (Off gives the older behaviour) | On |
| **Texture cache limit** | the game is killed for memory (lower it) or textures keep reloading (raise it) | measured from free memory |
| **Soft textures** | the game runs out of memory; large textures lose their finest level | the game's profile |
| **Soft texture levels** | the game still runs out of memory with Soft textures on | 1 level |
| **Frame generation floor** | generated frames look bad when the game runs slowly | 30 fps |
| **Skipped-work notice** | the notice "Part of the picture is not drawn" appears and you want it off (0) or only for larger gaps | 5 % |

Rows that a launcher control sets (**Frame rate cap**, **Keep GPU clock up**, **Instanced draws**, **Classic render passes**, **Background pipelines**, **RAM saver**, **Motion sensitivity**, **Full vegetation**, **Game language**, **GPU timing**, **GPU driver**, **Rumble**) are described on [Settings: Performance](Settings-Performance), [Settings: Game](Settings-Game) and [Settings: Controls](Settings-Controls).

## Developer switches new in 0.3.40

Behind **Show developer options**; raw names.

| Switch | What it does |
|---|---|
| `DM_VK_LAYER` | `0` turns the run-time shader layer off ([Live shader building](Live-Shader-Building)) |
| `DM_VK_LAYER_DIR` | the layer's folder (the app sets it) |
| `DM_VK_LAYER_DROP` | test: pretend a share of the library's shaders are missing |
| `DM_VK_SPEC_MAPS_PCT` | background shader builds wait from this percent (default 50) of Android's memory-map limit |
| `DM_SHADER_SAMPLE` | size of the quick check that lets an older shader library stand as this version's (default 300; `0` turns the check off) ([Live shader building](Live-Shader-Building#after-an-app-update)) |
| `DM_SHADER_SAMPLE_SEED` | diagnostic: the seed of that check's random draw, to repeat a run |
| `DM_VK_TS_TICK` | `0` keeps the driver's GPU timestamp period; by default a period that is more than 2 % off the measured one is replaced (community change #345 by nevercholt, for Turnip T30 on an Adreno 740) |
| `DM_VK_TSCAL` | diagnostic: logs host and GPU times for the next n submissions |
| `DM_MOVIE_LETTERBOX` | `0` turns off the movie letterbox of the Fire Emblem 4:3 variant |
| `DM_OOT_FOG_AT_CUT` and the Ocarina of Time distance switches | the rows described above |

## Limits

- The list grows with each release; a row you set stays until you reset it, even when a later version makes it the default.
- Wrong values in a developer row can stop a game from starting. Reset all clears them.
