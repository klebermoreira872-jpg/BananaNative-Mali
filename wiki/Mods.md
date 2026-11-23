# Mods

Pokémon Pokopia (`0400A3A01EE4C000`) can load **mods**: folders of replacement files laid over the game's data at the start, such as a text or texture mod or a translation. The game's dump is never changed, and a mod you turn off or remove leaves the game as it was. This is experimental: it has not been run on a phone yet.

## Add a mod

1. Get the mod as a **.zip** from its author. Nothing is bundled with Banana Native.
2. Open the game's page (the **...** on its card), tab **Game**, section **Game options**, row **Mods**.
3. Tap **Import mod (.zip)...** and pick the file. The launcher unpacks it into its own storage. One outer folder (the zip's own name, a version such as `2.0.1`, or `romfs`) is dropped, so the files inside sit as the game's data folders do.
4. Start the game. The change applies at the next start.

## Turn a mod off or remove it

Open the **Mods** row, tap the mod, and choose **Turn off** (it stays on this phone) or **Remove** (its files are deleted; the game's own files stay). A mod that is earlier in the list (by name) wins where two mods replace the same file.

## Limits

- A mod that replaces files with shaders in them is not supported yet: the game would ask for shaders the library does not have.
- Only data mods. Mods that change the game's code are not supported.
- Link Play: this phone's mods are not checked against another player's; keep them the same on both sides.
- If nothing changes, the zip may have the wrong folder level: the files should sit where the game's own RomFS has them.
