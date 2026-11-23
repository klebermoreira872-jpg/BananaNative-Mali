# Live shader building

New in 0.3.40. A game draws with shaders. Until now Prepare had to find and translate all of them before the first start. Now, for Switch 2 games, the app can build the shaders a game needs while you play.

## What you will see

- **Prepare is shorter and optional for shaders.** For a game the feature covers, Prepare only rewrites the game's code and makes the pack, with no shader library. The card then says **Ready · shaders build as you play** and Play is on at once. Prepare shaders (a full library, up front) stays as an optional row on the game's page.
- **In the game:** a small see-through label at the very top of the screen while shaders are built: by default only the number N, or **Building shaders (N)** if you choose **Full text** (**Settings > Building shaders label**; **Off** hides it, the build goes on). The part of the picture that needs a missing shader is not drawn (missing geometry), usually for a few seconds; then it appears. The first minutes of a new game can show this often. The in-game panel's General tab shows the state in words (built, waiting, paused, all ready).
- **The built shaders are kept** in the game's pack (`shaders/layer`; Settings > **Storage** lists it as "Shader cache built while playing"), so later runs do not build them again.
- **Cost:** the phone does extra work in the background and can get warmer. Heat never stops the build: a warm or hot phone builds with one worker and the label says "phone is warm" or "phone is hot: 1 worker"; at the highest heat level Android itself may close the app, and the next start goes on where the build stopped. The build waits only while the battery is under 15 % and not charging ("Shader build paused (battery low)", shown whichever label you chose). It is limited by a quota (at least 2 GB, and never below 1 GB or 5 % free space); the game's page says so if the limit is reached. Frame rate during building is not measured.

## The first start with no library (starter sets)

A game with no shader library at all (code-only Prepare) asks for hundreds of shaders in its first minutes. For eight games the app ships a short list of the shaders a first start asks for, in the order it asks (a starter set: Ocarina of Time 547, Donkey Kong Bananza 556, Mario Kart World 1,376, Mario Tennis Fever 336, Fire Emblem: Fortune's Weave 232, Star Fox 201, Pokopia 118, Fast Fusion 391). At that first start the app reads those shaders from your own game file and starts building them while the title loads, so the ones needed first are ready first. The lists hold shader keys only, no game data. A game without a list builds in the order the game asks.

**What to expect, honestly:** this shortens the wait; it does not remove it. A first start with no library still shows a black or half-empty picture for a while, and a big game such as Ocarina of Time still takes several sessions of play before the pop-in stops (every shader is built once and kept). A library made on a computer, or **Build all**, skips this. The starter sets were made from phone runs; none has been compared against a whole-library start yet. [ ]

## How it works

When the game asks for a shader the pack does not have, the app notes it (a `[shaders-missing]` line in the log), writes a request and builds that shader in its packer process into a small library of its own (the layer). The game picks it up within seconds. Nothing leaves the phone. A shader from a library made on a PC, Mac or Linux machine and imported or prepared on the phone still wins over the layer's, key by key.

## Shaders while playing (setting)

A per-game switch, **Shaders while playing**, on the game's page under **Advanced**. On by default for Switch 2 games. It is read when the game starts, so a change applies at the next start. Off means the old behaviour: Play waits for a complete shader library, and the card says **Shaders needed** with the reason and the ways forward (**Turn on and play**, **Prepare shaders** from a dump, **Import a library**).

Also on the game's page: **Build all** (build the whole set now), **Import a library** (pick a `dmsh_vk.lib` made on a computer; it is checked before it is used), and a row **Shaders: built while playing (N built)**. **Export pack** leaves the layer out; it is built again where the pack goes.

## After an app update

If your pack's shaders are from an older app version that this version still plays, the game page shows a small row **Shaders: older, built while playing** with **Update shaders** and **Not now** (never a big card). The game plays either way and the layer fills in what is missing; shaders the older library already has stay as they were made until you update ([Updates](Updates)). **Update shaders** asks you to confirm first, because it builds the whole set again.

When the app has no ready list of what changed, it also tries a quick check at idle time (card: "Ready · checking shaders…", one to three minutes): it translates a random sample of 300 shaders from your older library again with this version and compares them. If all are the same, the older library is kept as this version's and the row never appears. If any differ, nothing is taken over and the row stays. The check never runs during a game; the in-game build later re-verifies a few kept shaders in the background and uses the new one where it differs.

## Turning it off

`DM_VK_LAYER=0` (Extra environment) turns the layer off for a game: missing shaders are only logged and their draws stay skipped. `DM_VK_LAYER_DIR` names the layer's folder (the app sets it).

## Limits (0.3.40)

- Not run on a phone by us when this page was written; tell us what you see and share the log ([Troubleshooting](Troubleshooting#share-a-log)).
- A game without the needed shader information (a Maxwell title) gets the list of missing shaders but no layer and keeps **Shaders needed**.
- Games with many shaders take a while to build all of them; keep playing, they appear as you go.
