# Pokémon Shield (01008DB008C2C000): the rewriter's patches of this game's own builds, keyed by the NSO build ID (dm/tools/patch_nso.py, "Registered patches").
# Patches of Nintendo SDK module builds are in dm/tools/sdk_patches.py.
# The cuts are nx2android's for this build (shirai91/nx2android, its dm/games/01008DB008C2C000/patches.py, MIT), by way of Peanuts Native: not seen on an AYN Thor, taken as a guard
CUTS = {
  # 1.3.2 (v458752) main. With a save, the title screen builds the player's character in their outfit. The dress-up manager's function at main+0xcaaf00 hands each outfit
  # part's handle from its slot table to main+0x64f970, which reads the handle's object at main+0x64fa78 without a check. The slots fill as the parts load: on the Switch
  # they are there by then; nx2android measured an empty slot in 2 of 12 cold boots on an AYN Odin 2 with Pokémon Sword (SIGSEGV at main+0x64fa78, address 0x58, 1.5 s in).
  # Each call site already skips the handle's reference count for an empty slot (cbz x0); its branch now goes past the call too, to the reload of the slot after it:
  # a part that has not loaded yet is not applied this time, instead of the null read
  'a16802625e7826bf83b6f9708e475b91': [
    (0xcab14c, '800000b4', '000100b4', 'dress-up slot (part index + 7) empty: skip main+0x64f970 (cbz x0 → main+0xcab16c instead of main+0xcab15c)'),
    (0xcab198, '800000b4', '000100b4', 'dress-up slot (part index) empty: skip main+0x64f970 (cbz x0 → main+0xcab1b8 instead of main+0xcab1a8)'),
    (0xcab224, '800000b4', '000100b4', 'dress-up slot (part index) empty: skip main+0x64f970 (cbz x0 → main+0xcab244 instead of main+0xcab234)'),
    (0xcab274, '800000b4', '000100b4', 'dress-up slot (part index + 7) empty: skip main+0x64f970 (cbz x0 → main+0xcab294 instead of main+0xcab284)'),
  ],
}
BINDING = [
    {'what': 'dress-up slots: an empty slot skips the call that reads its handle', 'now': 'build', 'goal': 'game', 'purpose': 'race',
     'why': "the game's own dress-up function: its four call sites can be found by the function's fingerprint in another build"},
]
